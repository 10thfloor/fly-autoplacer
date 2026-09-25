import json
import subprocess
from unittest.mock import Mock

import pytest

from automation.fly_client import FlyClient, FlyError


def machine(region="iad", group="web", **config):
    return {"region": region, "state": "started",
            "config": {"metadata": {"fly_process_group": group, "fly_platform_version": "v2"}, **config}}


def test_every_command_pins_target_and_process(monkeypatch):
    run = Mock(return_value=Mock(stdout=json.dumps([machine()])))
    monkeypatch.setattr(subprocess, "run", run)
    client = FlyClient("customer-app", "web", timeout=30)
    assert client.regions() == {"iad"}
    client.scale_region("cdg", 1)
    client.scale_region("iad", 0)
    for call in run.call_args_list:
        command = call.args[0]
        assert command[-2:] == ["--app", "customer-app"]
        assert call.kwargs["timeout"] == 30
        assert call.kwargs["capture_output"] is True
    assert run.call_args_list[1].args[0] == [
        "fly", "scale", "count", "1", "--process-group", "web",
        "--region", "cdg", "--yes", "--app", "customer-app"]


def test_only_target_process_regions_are_reconciled(monkeypatch):
    data = [machine(), machine("cdg", "worker"),
            {**machine("sfo"), "state": "destroyed"}]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=Mock(stdout=json.dumps(data))))
    assert FlyClient("target", "web").regions() == {"iad"}


def test_unmanaged_machines_do_not_satisfy_placement(monkeypatch):
    data = [machine(), machine("fra", metadata={"fly_process_group": "web"})]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=Mock(stdout=json.dumps(data))))
    assert FlyClient("target", "web").regions() == {"iad"}


def test_legacy_explicit_group_is_supported(monkeypatch):
    data = [machine(metadata={"fly_platform_version": "v2", "process_group": "web"})]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=Mock(stdout=json.dumps(data))))
    assert FlyClient("target", "web").regions() == {"iad"}


@pytest.mark.parametrize("data", [[], {}, [None], [machine(mounts=[{"volume": "vol_1"}])]])
def test_invalid_or_stateful_inventory_fails_closed(data, monkeypatch):
    monkeypatch.setattr(subprocess, "run", Mock(return_value=Mock(stdout=json.dumps(data))))
    with pytest.raises(FlyError):
        FlyClient("target", "web").regions()


@pytest.mark.parametrize("error", [
    subprocess.CalledProcessError(1, "fly", stderr="TOKEN=secret"),
    subprocess.TimeoutExpired("fly", 30, output="TOKEN=secret"),
    FileNotFoundError("TOKEN=secret"),
])
def test_errors_do_not_expose_cli_output(error, monkeypatch):
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=error))
    with pytest.raises(FlyError) as caught:
        FlyClient("target").scale_region("iad", 1)
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("state", ["failed", "launch_failed", "creating", "starting", "destroying", "unknown", None])
def test_unhealthy_or_transitional_machines_cannot_satisfy_capacity_safeguards(state, monkeypatch):
    data = [machine("iad"), {**machine("fra"), "state": state}]
    monkeypatch.setattr(subprocess, "run", Mock(return_value=Mock(stdout=json.dumps(data))))
    with pytest.raises(FlyError, match="unhealthy or changing state"):
        FlyClient("target", "web").regions()
