import json
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.state_manager import (
    get_deployment_state_file, load_placement_state, save_placement_state,
    load_deployment_state, placement_lock,
)


def test_state_isolated_by_target_process_and_mode(tmp_path):
    scope = dict(data_dir=str(tmp_path), app_name="target", process_group="web")
    state = {"deployed": {"iad": None}, "last_actions": {"cdg": "2026-01-01T00:00:00Z"}}
    save_placement_state(state, True, **scope)
    assert load_deployment_state(True, **scope) == {"iad": None}
    assert load_placement_state(True, **scope)["last_actions"]["cdg"].endswith("+00:00")
    assert not load_deployment_state(False, **scope)
    assert not load_deployment_state(True, **{**scope, "app_name": "other"})
    assert not load_deployment_state(True, **{**scope, "process_group": "worker"})


def test_atomic_failure_preserves_previous_state(tmp_path):
    scope = dict(data_dir=str(tmp_path))
    old = {"deployed": {"iad": None}, "last_actions": {}}
    save_placement_state(old, **scope)
    with patch("utils.state_manager.os.replace", side_effect=OSError("disk error")):
        with pytest.raises(OSError):
            save_placement_state({"deployed": {}, "last_actions": {}}, **scope)
    assert load_deployment_state(**scope) == {"iad": None}
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("content", ["", "{", "null", '{"version": 2}', '{"iad": "invalid"}'])
def test_corrupt_state_fails_closed(tmp_path, content):
    Path(get_deployment_state_file(data_dir=tmp_path)).write_text(content)
    with pytest.raises(ValueError, match="Cannot read placement state"):
        load_placement_state(data_dir=tmp_path)


@pytest.mark.parametrize("legacy", [["iad"], {"iad": None}])
def test_legacy_membership_is_read(legacy, tmp_path):
    Path(get_deployment_state_file(data_dir=tmp_path)).write_text(json.dumps(legacy))
    assert load_deployment_state(data_dir=tmp_path) == {"iad": None}


def test_overlapping_cycles_are_rejected_and_lock_is_released(tmp_path):
    with placement_lock(data_dir=tmp_path):
        with pytest.raises(BlockingIOError):
            with placement_lock(data_dir=tmp_path):
                pytest.fail("Overlapping cycle acquired a lock")
    with placement_lock(data_dir=tmp_path):
        pass


@pytest.mark.parametrize("app_name", ["../app", "", "app/name"])
def test_invalid_scope_cannot_escape_data_directory(app_name, tmp_path):
    with pytest.raises(ValueError):
        load_placement_state(app_name=app_name, data_dir=tmp_path)
