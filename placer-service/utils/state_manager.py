"""Atomic placement state, isolated by target app, process group and run mode."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile


def scope_directory(data_dir, app_name=None, process_group="app"):
    directory = Path(data_dir)
    if app_name is not None:
        for value in (app_name, process_group):
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
                raise ValueError("Invalid placement state scope")
        directory = directory / app_name / process_group
    return directory


def get_deployment_state_file(dry_run=False, *, app_name=None, process_group="app", data_dir="data"):
    name = "deployment_state_dry_run.json" if dry_run else "deployment_state.json"
    return str(scope_directory(data_dir, app_name, process_group) / name)


def _timestamps(values):
    if not isinstance(values, dict):
        raise ValueError("Invalid placement state")
    result = {}
    for region, timestamp in values.items():
        if not isinstance(region, str) or not re.fullmatch(r"[a-z0-9]{3}", region):
            raise ValueError("Invalid region in placement state")
        if timestamp is not None:
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                timestamp = parsed.astimezone(timezone.utc).isoformat()
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError("Invalid timestamp in placement state") from exc
        result[region] = timestamp
    return result


def load_placement_state(dry_run=False, **scope):
    path = Path(get_deployment_state_file(dry_run, **scope))
    if not path.exists():
        return {"version": 1, "deployed": {}, "last_actions": {}}
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list):
            data = dict.fromkeys(data)
        if not isinstance(data, dict):
            raise ValueError("Invalid placement state")
        if "version" not in data:
            deployed = _timestamps(data)
            return {"version": 1, "deployed": deployed, "last_actions": dict(deployed)}
        if data["version"] != 1:
            raise ValueError("Unsupported placement state version")
        return {"version": 1, "deployed": _timestamps(data["deployed"]),
                "last_actions": _timestamps(data["last_actions"])}
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("Cannot read placement state; repair it before continuing") from exc


def save_placement_state(state, dry_run=False, **scope):
    payload = {"version": 1, "deployed": _timestamps(state["deployed"]),
               "last_actions": _timestamps(state["last_actions"])}
    path = Path(get_deployment_state_file(dry_run, **scope))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
            temporary = handle.name
            json.dump(payload, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def load_deployment_state(dry_run=False, **scope):
    return load_placement_state(dry_run, **scope)["deployed"]


def save_deployment_state(state, dry_run=False, **scope):
    previous = load_placement_state(dry_run, **scope)
    previous["deployed"] = state
    previous["last_actions"].update(state)
    save_placement_state(previous, dry_run, **scope)


@contextmanager
def placement_lock(dry_run=False, **scope):
    path = Path(get_deployment_state_file(dry_run, **scope) + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
