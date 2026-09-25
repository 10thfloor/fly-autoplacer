import pytest
from utils.config_loader import Config, ConfigError


def test_configuration_is_reloaded_and_independent(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text("dry_run: true\ntraffic_threshold: 50\n")
    first = Config.get_config(path)
    first["allowed_regions"].append("iad")
    path.write_text("dry_run: false\ntraffic_threshold: 100\nalways_running_regions: [fra]\n")
    second = Config.get_config(path)
    assert second["dry_run"] is False
    assert second["traffic_threshold"] == 100
    assert second["allowed_regions"] == []


def test_configuration_path_can_be_set_in_environment(tmp_path, monkeypatch):
    path = tmp_path / "custom.yml"
    path.write_text("dry_run: true\nprocess_group: web\n")
    monkeypatch.setenv("PLACER_CONFIG_FILE", str(path))
    assert Config.get_config()["process_group"] == "web"


@pytest.mark.parametrize("override", [
    {"dry_run": "false"},
    {"dry_run": False},
    {"dryrun": True},
    {"cooldown_period": -1},
    {"cooldown_period": float("inf")},
    {"short_term_window": 0},
    {"long_term_window": 1},
    {"long_term_window": 20.5},
    {"short_term_window": True},
    {"alpha_short": 0},
    {"alpha_long": 1.01},
    {"alpha_long": float("nan")},
    {"traffic_threshold": 10},
    {"deployment_threshold": -1},
    {"traffic_threshold": "high"},
    {"command_timeout": 0},
    {"command_timeout": True},
    {"min_regions": 0},
    {"min_regions": True},
    {"min_regions": 2, "max_regions": 1},
    {"max_regions": 1.5},
    {"allowed_regions": "iad"},
    {"allowed_regions": ["iad", "iad"]},
    {"allowed_regions": ["iad; command"]},
    {"allowed_regions": ["iad"], "min_regions": 2},
    {"allowed_regions": ["iad"], "excluded_regions": ["iad"]},
    {"always_running_regions": ["fra"], "excluded_regions": ["fra"]},
    {"always_running_regions": ["fra"], "allowed_regions": ["iad"]},
    {"always_running_regions": ["fra", "iad"], "max_regions": 1},
    {"process_group": ""},
    {"data_dir": ""},
    {"data_dir": "\x00"},
])
def test_unsafe_configuration_is_rejected(override):
    with pytest.raises(ConfigError):
        Config.validate({"dry_run": True, **override})


def test_live_configuration_accepts_consistent_protection():
    config = Config.validate({
        "dry_run": False,
        "always_running_regions": ["fra"],
        "allowed_regions": ["fra", "iad"],
        "excluded_regions": ["nrt"],
        "max_regions": 2,
    })
    assert config["process_group"] == "app"
    assert config["command_timeout"] == 120
    assert config["min_regions"] == 1


@pytest.mark.parametrize("content", ["", "[]", "null", "broken: [secret-value"])
def test_bad_yaml_has_sanitized_errors(tmp_path, content):
    path = tmp_path / "config.yml"
    path.write_text(content)
    with pytest.raises(ConfigError) as exc:
        Config.get_config(path)
    assert "secret-value" not in str(exc.value)


def test_configuration_file_failure_is_not_a_default_config(tmp_path):
    with pytest.raises(ConfigError):
        Config.get_config(tmp_path / "missing.yml")
