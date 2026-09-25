"""Authenticated control API for a single placement cycle per trigger."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
import secrets
import socket
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool
import uvicorn

from utils.config_loader import Config, ConfigError
from utils.fancy_logger import configure_logging


logger = logging.getLogger(__name__)
bearer_auth = HTTPBearer(auto_error=False)


def _required_token():
    token = os.environ.get("PLACER_API_TOKEN", "")
    if not token.strip():
        raise ConfigError("PLACER_API_TOKEN is required")
    return token


def _load_runtime_config():
    config = Config.get_config()
    _required_token()
    if not config["dry_run"]:
        for name in ("PLACER_TARGET_APP", "FLY_API_TOKEN", "FLY_PROMETHEUS_URL"):
            if not os.environ.get(name, "").strip():
                raise ConfigError(f"{name} is required in live mode")
        try:
            url = urlparse(os.environ["FLY_PROMETHEUS_URL"])
            valid_url = (
                url.scheme in ("http", "https") and bool(url.hostname)
                and not url.username and not url.password and not url.query and not url.fragment
            )
        except ValueError:
            valid_url = False
        if not valid_url:
            raise ConfigError("FLY_PROMETHEUS_URL must be an HTTP endpoint without embedded credentials")
    return config


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer_auth)):
    try:
        expected = _required_token()
    except ConfigError:
        raise HTTPException(status_code=503, detail="Controller authentication is not configured") from None
    if (
        credentials is None or credentials.scheme.lower() != "bearer"
        or not secrets.compare_digest(credentials.credentials.encode(), expected.encode())
    ):
        raise HTTPException(
            status_code=401, detail="Valid bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    config = _load_runtime_config()
    configure_logging(config["data_dir"])
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logger.error("Request failed (%s)", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred"})


@app.get("/")
async def root():
    return {"service": "fly-autoplacer"}


@app.get("/health")
async def health_check():
    try:
        config = _load_runtime_config()
        return {"status": "healthy", "config_loaded": True, "dry_run": config["dry_run"]}
    except (ConfigError, OSError):
        raise HTTPException(status_code=503, detail="Controller configuration is invalid") from None


def _fetch_metrics(config):
    from utils.metrics_fetcher import MetricsFetcher
    return MetricsFetcher(dry_run=config["dry_run"], config=config).fetch_region_traffic()


def _run_placement(config):
    from automation.auto_placer import AutoPlacer
    return asyncio.run(AutoPlacer(config).process_traffic_data())


@app.get("/metrics", dependencies=[Depends(require_auth)])
async def get_metrics():
    try:
        config = _load_runtime_config()
        traffic_data = await run_in_threadpool(_fetch_metrics, config)
        return {"traffic_data": traffic_data, "timestamp": datetime.now(timezone.utc).isoformat(), "dry_run": config["dry_run"]}
    except ConfigError:
        raise HTTPException(status_code=503, detail="Controller configuration is invalid") from None
    except Exception as exc:
        logger.error("Metrics collection failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Traffic metrics could not be collected") from None


@app.post("/trigger", dependencies=[Depends(require_auth)])
async def trigger_auto_placer():
    try:
        config = _load_runtime_config()
        results = await run_in_threadpool(_run_placement, config)
        failed = bool(results.get("actions_taken", {}).get("errors"))
        return JSONResponse(
            status_code=502 if failed else 200,
            content={"status": "error" if failed else "success", "results": results},
        )
    except BlockingIOError:
        raise HTTPException(status_code=409, detail="A placement cycle is already running") from None
    except ConfigError:
        raise HTTPException(status_code=503, detail="Controller configuration is invalid") from None
    except Exception as exc:
        logger.error("Placement cycle failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Placement cycle failed; no further actions were attempted") from None


def main():
    load_dotenv()
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST")
    if host:
        uvicorn.run(app, host=host, port=port)
        return
    # asyncio's default IPv6 listener is IPv6-only. Bind explicitly so Fly's
    # private IPv6 network and Docker's published IPv4 port use the same server.
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        listener.bind(("::", port))
        listener.listen(socket.SOMAXCONN)
        server = uvicorn.Server(uvicorn.Config(app, host="::", port=port))
        server.run(sockets=[listener])


if __name__ == "__main__":
    main()
