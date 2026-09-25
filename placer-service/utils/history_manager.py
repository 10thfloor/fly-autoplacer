"""Persist scoped traffic observations and calculate chronological averages."""

import json
import math
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone


def _scope_component(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', value):
        raise ValueError(f'Invalid {label} for traffic history')
    return value


def get_traffic_history_file(dry_run=False, *, app_name=None, process_group='app', data_dir='data'):
    directory = Path(data_dir)
    if app_name is not None:
        directory /= _scope_component(app_name, 'app name')
        directory /= _scope_component(process_group, 'process group')
    filename = 'traffic_history_dry_run.json' if dry_run else 'traffic_history.json'
    return str(directory / filename)


def _timestamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime):
        raise ValueError('Traffic history timestamps must be datetimes or ISO timestamps')
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _traffic_observation(observation):
    if not isinstance(observation, dict):
        raise ValueError('Traffic observations must map regions to counts')
    result = {}
    for region, count in observation.items():
        if not isinstance(region, str) or not region or region.strip() != region:
            raise ValueError('Traffic observations must contain nonempty region names')
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            raise ValueError('Traffic counts must be numbers')
        if not math.isfinite(count) or count < 0:
            raise ValueError('Traffic counts must be finite and nonnegative')
        result[region] = count
    return result


def load_traffic_history(dry_run=False, *, app_name=None, process_group='app', data_dir='data'):
    history_file = Path(get_traffic_history_file(
        dry_run, app_name=app_name, process_group=process_group, data_dir=data_dir))
    if not history_file.exists():
        return {}
    with history_file.open() as stream:
        history = json.load(stream)
    if not isinstance(history, dict):
        raise ValueError('Traffic history must be a timestamp-keyed mapping')
    return {_timestamp(timestamp): _traffic_observation(value) for timestamp, value in history.items()}


def save_traffic_history(history, dry_run=False, *, app_name=None, process_group='app', data_dir='data'):
    history_file = Path(get_traffic_history_file(
        dry_run, app_name=app_name, process_group=process_group, data_dir=data_dir))
    serializable = {_timestamp(timestamp).isoformat(): _traffic_observation(value)
                    for timestamp, value in history.items()}
    history_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=history_file.parent,
                                         prefix='.traffic-', suffix='.json', delete=False) as stream:
            temporary_path = stream.name
            json.dump(serializable, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, history_file)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def update_traffic_history(current_traffic, dry_run=False, *, app_name=None,
                           process_group='app', data_dir='data', max_entries=20):
    if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
        raise ValueError('max_entries must be a positive integer')
    scope = dict(app_name=app_name, process_group=process_group, data_dir=data_dir)
    history = load_traffic_history(dry_run, **scope)
    history[datetime.now(timezone.utc)] = _traffic_observation(current_traffic)
    history = dict(sorted(history.items())[-max_entries:])
    save_traffic_history(history, dry_run, **scope)
    return history


def _ema(values, alpha):
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result


def calculate_region_averages(history, config):
    """Use the newest observation's regions; absent historical values are unknown.

    Only explicit zero samples establish that a region had no traffic. Missing
    regions are unknown and are not assigned synthetic zero observations.
    """
    if not history:
        return {}
    short_window = config.get('short_term_window', 5)
    long_window = config.get('long_term_window', 20)
    alpha_short = config.get('alpha_short', 0.3)
    alpha_long = config.get('alpha_long', 0.1)
    for window in (short_window, long_window):
        if isinstance(window, bool) or not isinstance(window, int) or window < 1:
            raise ValueError('Traffic averaging windows must be positive integers')
    for alpha in (alpha_short, alpha_long):
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0 < alpha <= 1:
            raise ValueError('Traffic smoothing factors must be in (0, 1]')
    observations = [value for _, value in sorted(
        (_timestamp(timestamp), _traffic_observation(value)) for timestamp, value in history.items())]
    averages = {}
    for region in observations[-1]:
        values = [observation[region] for observation in observations if region in observation]
        averages[region] = {
            'short': _ema(values[-short_window:], alpha_short),
            'long': _ema(values[-long_window:], alpha_long),
        }
        if len(values) > 1:
            averages[region]['baseline'] = _ema(values[:-1][-long_window:], alpha_long)
    return averages
