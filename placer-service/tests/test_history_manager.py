from datetime import datetime, timedelta, timezone
import json

import pytest

from utils.history_manager import (
    calculate_region_averages, get_traffic_history_file, load_traffic_history,
    save_traffic_history, update_traffic_history,
)


def test_update_creates_storage_and_returns_observation(tmp_path):
    history = update_traffic_history({'iad': 100}, True, data_dir=tmp_path)
    assert len(history) == 1
    timestamp, observation = next(iter(history.items()))
    assert timestamp.tzinfo == timezone.utc
    assert observation == {'iad': 100}
    assert load_traffic_history(True, data_dir=tmp_path) == history


def test_load_normalizes_offsets_without_changing_instant(tmp_path):
    path = tmp_path / 'traffic_history.json'
    path.write_text(json.dumps({'2024-10-01T10:00:00+02:00': {'iad': 5}}))
    assert load_traffic_history(data_dir=tmp_path) == {
        datetime(2024, 10, 1, 8, tzinfo=timezone.utc): {'iad': 5}}


def test_history_is_scoped_by_app_process_and_mode(tmp_path):
    scope = dict(data_dir=tmp_path, app_name='target-app', process_group='web')
    saved = update_traffic_history({'iad': 25}, True, **scope)
    assert load_traffic_history(True, **scope) == saved
    assert load_traffic_history(False, **scope) == {}
    assert load_traffic_history(True, **dict(scope, app_name='another-app')) == {}
    assert load_traffic_history(True, **dict(scope, process_group='worker')) == {}
    assert load_traffic_history(True, data_dir=tmp_path) == {}


@pytest.mark.parametrize('app_name', ['../other', '/absolute', '..', 'a/b', ''])
def test_scope_rejects_unsafe_names(tmp_path, app_name):
    with pytest.raises(ValueError):
        get_traffic_history_file(app_name=app_name, data_dir=tmp_path)


def test_update_retains_newest_observations(tmp_path):
    now = datetime.now(timezone.utc)
    original = {now - timedelta(minutes=age): {'iad': age} for age in (1, 3, 2)}
    save_traffic_history(original, data_dir=tmp_path)
    history = update_traffic_history({'iad': 100}, data_dir=tmp_path, max_entries=3)
    assert len(history) == 3
    assert now - timedelta(minutes=3) not in history
    assert list(history.values())[-1] == {'iad': 100}


def test_failed_atomic_replace_preserves_existing_history(tmp_path, monkeypatch):
    original = {datetime(2024, 1, 1, tzinfo=timezone.utc): {'iad': 10}}
    save_traffic_history(original, data_dir=tmp_path)

    def fail_replace(*args):
        raise OSError('simulated storage failure')

    monkeypatch.setattr('utils.history_manager.os.replace', fail_replace)
    with pytest.raises(OSError):
        update_traffic_history({'iad': 100}, data_dir=tmp_path)
    assert load_traffic_history(data_dir=tmp_path) == original
    assert not list(tmp_path.glob('.traffic-*'))


@pytest.mark.parametrize('count', [float('nan'), float('inf'), -1, True, '10'])
def test_invalid_observation_does_not_replace_history(tmp_path, count):
    with pytest.raises(ValueError):
        update_traffic_history({'iad': count}, data_dir=tmp_path)
    assert load_traffic_history(data_dir=tmp_path) == {}


def test_averages_use_chronological_windows_and_previous_baseline():
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    history = {now + timedelta(minutes=index): {'iad': value}
               for index, value in reversed(list(enumerate([10, 20, 40, 80])))}
    averages = calculate_region_averages(history, {
        'short_term_window': 2, 'long_term_window': 3,
        'alpha_short': 0.5, 'alpha_long': 0.25,
    })
    assert averages['iad'] == {'short': 60, 'long': 38.75, 'baseline': 19.375}


def test_absent_regions_are_unknown_and_explicit_zero_is_a_sample():
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    history = {now: {'iad': 100, 'cdg': 50}, now + timedelta(minutes=1): {'cdg': 0}}
    averages = calculate_region_averages(history, {'alpha_short': 1, 'alpha_long': 1})
    assert averages == {'cdg': {'short': 0, 'long': 0, 'baseline': 50}}
    assert calculate_region_averages({}, {}) == {}


def test_first_observation_needs_no_baseline():
    history = {datetime.now(timezone.utc): {'iad': 1000}}
    assert calculate_region_averages(history, {}) == {'iad': {'short': 1000, 'long': 1000}}
