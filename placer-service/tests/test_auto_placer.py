from datetime import datetime, timezone
from unittest.mock import Mock

from automation.auto_placer import AutoPlacer
from automation.fly_client import FlyError
from utils.state_manager import load_placement_state

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_placer(tmp_path, monkeypatch, **overrides):
    config = dict(dry_run=False, data_dir=str(tmp_path), always_running_regions=["fra"],
                  cooldown_period=300, min_regions=1, max_regions=5)
    config.update(overrides)
    metrics = Mock()
    metrics.get_app_name.return_value = "target"
    monkeypatch.setenv("PLACER_TARGET_APP", "target")
    fly = Mock()
    return AutoPlacer(config, metrics_fetcher=metrics, fly_client=fly, clock=lambda: NOW), fly


def test_executor_protects_required_and_filtered_regions(tmp_path, monkeypatch):
    placer, fly = make_placer(tmp_path, monkeypatch, allowed_regions=["fra", "iad"])
    state = {"deployed": {"fra": None, "iad": None}, "last_actions": {}}
    result = placer._execute_actions([("fra", "scale_down"), ("sfo", "scale_up")], state)
    assert len(result["actions_taken"]["skipped"]) == 2
    fly.scale_region.assert_not_called()


def test_successful_mutations_persist_membership_and_removal_timestamps(tmp_path, monkeypatch):
    placer, fly = make_placer(tmp_path, monkeypatch)
    state = {"deployed": {"fra": None, "iad": None}, "last_actions": {}}
    result = placer._execute_actions([("iad", "scale_down"), ("cdg", "scale_up")], state)
    assert fly.scale_region.call_args_list[0].args == ("cdg", 1)
    assert fly.scale_region.call_args_list[1].args == ("iad", 0)
    saved = load_placement_state(False, **placer.scope)
    assert set(saved["deployed"]) == {"fra", "cdg"}
    assert saved["last_actions"]["iad"] == NOW.isoformat()
    assert result["current_regions"] == ["cdg", "fra"]


def test_failed_deployment_defers_all_removals(tmp_path, monkeypatch):
    placer, fly = make_placer(tmp_path, monkeypatch)
    fly.scale_region.side_effect = FlyError("Fly command timed out")
    state = {"deployed": {"fra": None, "iad": None}, "last_actions": {}}
    result = placer._execute_actions([("iad", "scale_down"), ("cdg", "scale_up")], state)
    fly.scale_region.assert_called_once_with("cdg", 1)
    assert result["actions_taken"]["errors"]
    saved = load_placement_state(False, **placer.scope)
    assert set(saved["deployed"]) == {"fra", "iad"}
    assert saved["last_actions"]["cdg"] == NOW.isoformat()


def test_dry_run_never_calls_fly(tmp_path, monkeypatch):
    placer, fly = make_placer(tmp_path, monkeypatch, dry_run=True)
    result = placer._execute_actions([("fra", "scale_up")],
                                    {"deployed": {}, "last_actions": {}})
    assert result["actions_taken"]["deployed"] == ["fra"]
    fly.scale_region.assert_not_called()
    assert load_placement_state(True, **placer.scope)["deployed"]
    assert not load_placement_state(False, **placer.scope)["deployed"]


def test_minimum_and_maximum_regions_are_enforced(tmp_path, monkeypatch):
    placer, fly = make_placer(tmp_path, monkeypatch, min_regions=2, max_regions=2)
    state = {"deployed": {"fra": None, "iad": None}, "last_actions": {}}
    result = placer._execute_actions([("cdg", "scale_up"), ("iad", "scale_down")], state)
    assert len(result["actions_taken"]["skipped"]) == 2
    fly.scale_region.assert_not_called()
