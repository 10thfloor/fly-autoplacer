from datetime import timedelta
from test_auto_placer import make_placer, NOW
from utils.state_manager import load_placement_state


def test_recent_deployment_cannot_be_removed(tmp_path, monkeypatch):
    placer, fly = make_placer(tmp_path, monkeypatch)
    state = {"deployed": {"fra": None, "iad": NOW.isoformat()},
             "last_actions": {"iad": NOW.isoformat()}}
    result = placer._execute_actions([("iad", "scale_down")], state)
    assert result["actions_taken"]["skipped"][0]["reason"] == "Region is in cooldown"
    fly.scale_region.assert_not_called()


def test_removed_region_keeps_cooldown_across_instances(tmp_path, monkeypatch):
    placer, fly = make_placer(tmp_path, monkeypatch)
    state = {"deployed": {"fra": None, "iad": None}, "last_actions": {}}
    placer._execute_actions([("iad", "scale_down")], state)
    second, second_fly = make_placer(tmp_path, monkeypatch)
    saved = load_placement_state(False, **second.scope)
    result = second._execute_actions([("iad", "scale_up")], saved)
    assert result["actions_taken"]["skipped"][0]["reason"] == "Region is in cooldown"
    second_fly.scale_region.assert_not_called()
    second.clock = lambda: NOW + timedelta(seconds=300)
    second._execute_actions([("iad", "scale_up")], saved)
    second_fly.scale_region.assert_called_once_with("iad", 1)
