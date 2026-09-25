"""Load a fresh, validated configuration for each placement cycle."""

import math
import os
from pathlib import Path
import re

import yaml


class ConfigError(ValueError):
    """Invalid controller configuration; messages contain no supplied values."""


class Config:
    DEFAULTS = {
        "dry_run": True,
        "cooldown_period": 10,
        "short_term_window": 5,
        "long_term_window": 20,
        "alpha_short": 0.3,
        "alpha_long": 0.1,
        "traffic_threshold": 50,
        "deployment_threshold": 10,
        "allowed_regions": [],
        "excluded_regions": [],
        "always_running_regions": [],
        "process_group": "app",
        "command_timeout": 120,
        "data_dir": "data",
        "min_regions": 1,
        "max_regions": None,
    }

    @classmethod
    def get_config(cls, filepath=None):
        path = Path(filepath or os.environ.get("PLACER_CONFIG_FILE", "config/config.yml"))
        try:
            with path.open(encoding="utf-8") as config_file:
                config = yaml.safe_load(config_file)
        except (OSError, UnicodeError, yaml.YAMLError):
            raise ConfigError("Configuration could not be read") from None
        return cls.validate(config)

    @classmethod
    def validate(cls, config):
        if not isinstance(config, dict) or not config:
            raise ConfigError("Configuration must be a nonempty mapping")
        if set(config) - cls.DEFAULTS.keys():
            raise ConfigError("Configuration contains unsupported keys")
        result = dict(cls.DEFAULTS)
        result.update(config)

        if not isinstance(result["dry_run"], bool):
            raise ConfigError("dry_run must be a boolean")

        for key in ("short_term_window", "long_term_window", "min_regions"):
            if type(result[key]) is not int or result[key] < 1:
                raise ConfigError(f"{key} must be a positive integer")
        if result["short_term_window"] > result["long_term_window"]:
            raise ConfigError("short_term_window must not exceed long_term_window")
        maximum = result["max_regions"]
        if maximum is not None and (type(maximum) is not int or maximum < result["min_regions"]):
            raise ConfigError("max_regions must be an integer at least min_regions")

        for key in ("cooldown_period", "traffic_threshold", "deployment_threshold", "command_timeout", "alpha_short", "alpha_long"):
            value = result[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ConfigError(f"{key} must be a finite number")
            if value < 0:
                raise ConfigError(f"{key} must not be negative")
        if result["command_timeout"] <= 0:
            raise ConfigError("command_timeout must be positive")
        if result["traffic_threshold"] <= result["deployment_threshold"]:
            raise ConfigError("traffic_threshold must exceed deployment_threshold")
        for key in ("alpha_short", "alpha_long"):
            if not 0 < result[key] <= 1:
                raise ConfigError(f"{key} must be greater than zero and at most one")

        for key in ("allowed_regions", "excluded_regions", "always_running_regions"):
            regions = result[key]
            if not isinstance(regions, list) or any(
                not isinstance(region, str) or re.fullmatch(r"[a-z]{3}", region) is None
                for region in regions
            ):
                raise ConfigError(f"{key} must be a list of three-letter region codes")
            if len(regions) != len(set(regions)):
                raise ConfigError(f"{key} must not contain duplicate regions")
            result[key] = list(regions)
        allowed = set(result["allowed_regions"])
        excluded = set(result["excluded_regions"])
        protected = set(result["always_running_regions"])
        if allowed & excluded:
            raise ConfigError("allowed_regions and excluded_regions must not overlap")
        if protected & excluded or (allowed and not protected <= allowed):
            raise ConfigError("always_running_regions must be allowed and not excluded")
        if allowed and len(allowed) < result["min_regions"]:
            raise ConfigError("allowed_regions must accommodate min_regions")
        if maximum is not None and len(protected) > maximum:
            raise ConfigError("max_regions must accommodate always_running_regions")
        if not result["dry_run"] and not protected:
            raise ConfigError("Live mode requires always_running_regions")

        if not isinstance(result["process_group"], str) or re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", result["process_group"]) is None:
            raise ConfigError("process_group must be a valid process name")
        if not isinstance(result["data_dir"], str) or not result["data_dir"].strip() or "\x00" in result["data_dir"]:
            raise ConfigError("data_dir must be a nonempty path")
        return result
