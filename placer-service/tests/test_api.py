import asyncio
import logging
import socket
import threading

from fastapi.testclient import TestClient
import httpx
import pytest
import yaml

import main
from utils.config_loader import ConfigError
from utils.fancy_logger import configure_logging


AUTH = {"Authorization": "Bearer test-controller-token"}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    config = {"dry_run": True, "data_dir": str(tmp_path / "data")}
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(config))
    monkeypatch.setenv("PLACER_CONFIG_FILE", str(path))
    monkeypatch.setenv("PLACER_API_TOKEN", "test-controller-token")
    for key in ("PLACER_TARGET_APP", "FLY_APP_NAME", "FLY_API_TOKEN", "FLY_PROMETHEUS_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(main, "load_dotenv", lambda: None)
    return path, config


@pytest.fixture
def client(runtime):
    with TestClient(main.app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize("method,path", [("post", "/trigger"), ("get", "/metrics")])
@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "Basic test-controller-token"])
def test_unauthorized_requests_do_no_work(client, monkeypatch, method, path, authorization):
    def unexpected(*args):
        pytest.fail("Unauthorized request reached configuration or placement work")
    monkeypatch.setattr(main, "_load_runtime_config", unexpected)
    monkeypatch.setattr(main, "_run_placement", unexpected)
    monkeypatch.setattr(main, "_fetch_metrics", unexpected)
    headers = {"Authorization": authorization} if authorization else {}
    response = client.request(method, path, headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_startup_requires_auth_even_in_dry_run(runtime, monkeypatch):
    monkeypatch.delenv("PLACER_API_TOKEN")
    with pytest.raises(ConfigError, match="PLACER_API_TOKEN"):
        with TestClient(main.app):
            pass


def test_startup_rejects_invalid_configuration(runtime):
    path, _ = runtime
    path.write_text("dry_run: perhaps\n")
    with pytest.raises(ConfigError):
        with TestClient(main.app):
            pass


@pytest.mark.parametrize("missing", ["PLACER_TARGET_APP", "FLY_API_TOKEN", "FLY_PROMETHEUS_URL"])
def test_live_startup_requires_explicit_environment(runtime, monkeypatch, missing):
    path, config = runtime
    path.write_text(yaml.safe_dump({**config, "dry_run": False, "always_running_regions": ["fra"]}))
    monkeypatch.setenv("PLACER_TARGET_APP", "target-app")
    monkeypatch.setenv("FLY_APP_NAME", "controller-app")
    monkeypatch.setenv("FLY_API_TOKEN", "test-fly-token")
    monkeypatch.setenv("FLY_PROMETHEUS_URL", "https://example.test/prometheus/personal")
    monkeypatch.delenv(missing)
    with pytest.raises(ConfigError, match=missing):
        with TestClient(main.app):
            pass


def test_health_is_public_and_exposes_no_environment(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "config_loaded": True, "dry_run": True}


def test_routes_reload_configuration_without_restart(client, runtime, monkeypatch):
    path, config = runtime
    seen = []
    monkeypatch.setattr(main, "_run_placement", lambda config: seen.append(config["dry_run"]) or {"actions_taken": {"errors": []}})
    monkeypatch.setattr(main, "_fetch_metrics", lambda config: seen.append(config["dry_run"]) or {"fra": 1})
    assert client.post("/trigger", headers=AUTH).status_code == 200
    monkeypatch.setenv("PLACER_TARGET_APP", "target-app")
    monkeypatch.setenv("FLY_API_TOKEN", "test-fly-token")
    monkeypatch.setenv("FLY_PROMETHEUS_URL", "https://example.test/prometheus/personal")
    path.write_text(yaml.safe_dump({**config, "dry_run": False, "always_running_regions": ["fra"]}))
    assert client.post("/trigger", headers=AUTH).status_code == 200
    assert client.get("/metrics", headers=AUTH).json()["traffic_data"] == {"fra": 1}
    assert client.get("/health").json()["dry_run"] is False
    assert seen == [True, False, False]


def test_bad_config_reload_fails_closed(client, runtime, monkeypatch):
    path, _ = runtime
    path.write_text("dry_run: false\n")
    monkeypatch.setattr(main, "_run_placement", lambda config: pytest.fail("Invalid config triggered placement"))
    assert client.post("/trigger", headers=AUTH).status_code == 503
    assert client.get("/metrics", headers=AUTH).status_code == 503
    assert client.get("/health").status_code == 503


def test_overlapping_trigger_returns_conflict(client, monkeypatch):
    def locked(config):
        raise BlockingIOError("another cycle")
    monkeypatch.setattr(main, "_run_placement", locked)
    assert client.post("/trigger", headers=AUTH).status_code == 409


@pytest.mark.parametrize("method,path,helper", [
    ("post", "/trigger", "_run_placement"),
    ("get", "/metrics", "_fetch_metrics"),
])
def test_errors_do_not_leak_secrets(client, monkeypatch, caplog, method, path, helper):
    def failed(config):
        raise RuntimeError("secret-token-in-subprocess-or-upstream-body")
    monkeypatch.setattr(main, helper, failed)
    response = client.request(method, path, headers=AUTH)
    assert response.status_code == 502
    assert "secret-token" not in response.text
    assert "secret-token" not in caplog.text


def test_action_errors_preserve_useful_results_with_failure_status(client, monkeypatch):
    result = {"actions_taken": {"errors": [{"region": "iad", "action": "deploy", "error": "Machine operation failed"}]}}
    monkeypatch.setattr(main, "_run_placement", lambda config: result)
    response = client.post("/trigger", headers=AUTH)
    assert response.status_code == 502
    assert response.json() == {"status": "error", "results": result}


def test_trigger_work_does_not_block_health(runtime, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    def blocked(config):
        started.set()
        assert release.wait(timeout=5)
        return {"actions_taken": {"errors": []}}
    monkeypatch.setattr(main, "_run_placement", blocked)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
            trigger = asyncio.create_task(client.post("/trigger", headers=AUTH))
            try:
                assert await asyncio.to_thread(started.wait, 2)
                health = await asyncio.wait_for(client.get("/health"), timeout=1)
                assert health.status_code == 200
            finally:
                release.set()
            assert (await trigger).status_code == 200
    asyncio.run(exercise())


def test_startup_creates_logs_and_logging_is_idempotent(client, runtime):
    _, config = runtime
    configure_logging(config["data_dir"])
    handlers = [handler for handler in logging.getLogger().handlers if getattr(handler, "_autoplacer_file", False)]
    assert len(handlers) == 1
    assert (runtime[0].parent / "data" / "logs" / "auto_placer.log").is_file()


def test_entrypoint_runs_one_server_and_respects_host_override(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "load_dotenv", lambda: None)
    monkeypatch.setattr(main.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9000")
    main.main()
    assert calls == [{"host": "127.0.0.1", "port": 9000}]


def test_default_listener_accepts_both_ipv4_and_ipv6(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "load_dotenv", lambda: None)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.setenv("PORT", "0")
    def run(server, sockets):
        listener = sockets[0]
        calls.append(listener.getsockname()[1])
        assert listener.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY) == 0
        for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
            with socket.socket(family, socket.SOCK_STREAM) as client:
                client.settimeout(1)
                client.connect((address, calls[0]))
                accepted, _ = listener.accept()
                accepted.close()
    monkeypatch.setattr(main.uvicorn.Server, "run", run)
    main.main()
    assert len(calls) == 1
