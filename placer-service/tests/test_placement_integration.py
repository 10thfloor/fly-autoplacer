"""Exercise full placement cycles with real persistence and prediction."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from automation.auto_placer import AutoPlacer
from automation.fly_client import FlyError
from utils.history_manager import get_traffic_history_file, load_traffic_history
from utils.state_manager import get_deployment_state_file, load_placement_state


class Observations:
    def __init__(self, traffic):
        self.traffic = traffic

    def get_app_name(self):
        return 'integration-target'

    def fetch_region_traffic(self):
        if isinstance(self.traffic, Exception):
            raise self.traffic
        return dict(self.traffic)


class FakeFly:
    def __init__(self, regions=('fra',)):
        self.deployed = set(regions)
        self.calls = []
        self.failures = set()
        self.observation_calls = 0

    def regions(self):
        self.observation_calls += 1
        return set(self.deployed)

    def scale_region(self, region, count):
        self.calls.append((region, count))
        if (region, count) in self.failures:
            raise FlyError('Simulated Fly operation failure')
        if count:
            self.deployed.add(region)
        else:
            self.deployed.discard(region)


@pytest.fixture
def setup_cycle(tmp_path, monkeypatch):
    monkeypatch.setenv('PLACER_TARGET_APP', 'integration-target')
    config = {
        'dry_run': False, 'data_dir': str(tmp_path), 'always_running_regions': ['fra'],
        'traffic_threshold': 50, 'deployment_threshold': 10,
        'short_term_window': 2, 'long_term_window': 3,
        'alpha_short': 1, 'alpha_long': 1, 'cooldown_period': 60,
    }
    scope = {'app_name': 'integration-target', 'process_group': 'app', 'data_dir': str(tmp_path)}
    clock = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    metrics = Observations({})
    fly = FakeFly()

    def cycle(traffic, *, advance=0, dry_run=None, **overrides):
        clock[0] += timedelta(seconds=advance)
        metrics.traffic = traffic
        current_config = dict(config, **overrides)
        if dry_run is not None:
            current_config['dry_run'] = dry_run
        # A new controller per request exercises durable state rather than memory.
        controller = AutoPlacer(current_config, metrics_fetcher=metrics,
                                fly_client=fly, clock=lambda: clock[0])
        return asyncio.run(controller.process_traffic_data())

    return cycle, fly, scope, clock


def test_high_traffic_deploys_and_removal_tombstone_blocks_early_redeploy(setup_cycle):
    cycle, fly, scope, clock = setup_cycle
    first = cycle({'fra': 0, 'iad': 1000})
    assert first['actions_taken']['deployed'] == ['iad']
    assert first['current_regions'] == ['fra', 'iad']
    assert fly.calls == [('iad', 1)]

    early_drop = cycle({'fra': 0, 'iad': 0}, advance=10)
    assert early_drop['actions_taken']['removed'] == []
    assert any(item['region'] == 'iad' and 'cooldown' in item['reason']
               for item in early_drop['actions_taken']['skipped'])

    removed = cycle({'fra': 0, 'iad': 0}, advance=51)
    assert removed['actions_taken']['removed'] == ['iad']
    state = load_placement_state(False, **scope)
    assert 'iad' not in state['deployed']
    assert state['last_actions']['iad'] == clock[0].isoformat()

    early_return = cycle({'fra': 0, 'iad': 1000}, advance=1)
    assert early_return['actions_taken']['deployed'] == []
    assert early_return['current_regions'] == ['fra']

    restored = cycle({'fra': 0, 'iad': 1000}, advance=60)
    assert restored['actions_taken']['deployed'] == ['iad']
    assert fly.calls == [('iad', 1), ('iad', 0), ('iad', 1)]
    history = load_traffic_history(False, **scope)
    assert len(history) == 4  # Long window plus one previous-baseline sample.
    assert all(set(sample) == {'fra', 'iad'} for sample in history.values())


def test_missing_observation_never_becomes_zero_or_removes_region(setup_cycle):
    cycle, fly, scope, _ = setup_cycle
    cycle({'fra': 0, 'iad': 100})
    result = cycle({'fra': 0}, advance=61)
    assert result['current_regions'] == ['fra', 'iad']
    assert result['actions_taken']['removed'] == []
    assert fly.calls == [('iad', 1)]
    history = load_traffic_history(False, **scope)
    assert list(history.values())[-1] == {'fra': 0}


def test_empty_observations_preserve_history_state_and_all_placements(setup_cycle):
    cycle, fly, scope, _ = setup_cycle
    cycle({'fra': 0, 'iad': 100})
    state_path = Path(get_deployment_state_file(False, **scope))
    history_path = Path(get_traffic_history_file(False, **scope))
    original_state, original_history = state_path.read_bytes(), history_path.read_bytes()

    result = cycle({}, advance=61, always_running_regions=['fra', 'cdg'])
    assert result['current_regions'] == ['fra', 'iad']
    assert fly.calls == [('iad', 1)]
    assert state_path.read_bytes() == original_state
    assert history_path.read_bytes() == original_history
    assert result['actions_taken']['deployed'] == []
    assert result['actions_taken']['removed'] == []


def test_malformed_metrics_fail_before_history_or_infrastructure_changes(setup_cycle):
    cycle, fly, scope, _ = setup_cycle
    with pytest.raises(ValueError, match='malformed'):
        cycle(ValueError('malformed metrics'), always_running_regions=['fra', 'cdg'])
    assert fly.calls == []
    assert not Path(get_deployment_state_file(False, **scope)).exists()
    assert not Path(get_traffic_history_file(False, **scope)).exists()


def test_protected_regions_are_created_and_never_removed(setup_cycle):
    cycle, fly, _, _ = setup_cycle
    created = cycle({'fra': 0}, always_running_regions=['fra', 'cdg'])
    assert created['actions_taken']['deployed'] == ['cdg']
    result = cycle({'fra': 0, 'cdg': 0}, advance=61, always_running_regions=['fra', 'cdg'])
    assert result['current_regions'] == ['cdg', 'fra']
    assert result['actions_taken']['removed'] == []
    assert fly.calls == [('cdg', 1)]


def test_maximum_prioritizes_highest_demand_and_minimum_preserves_capacity(setup_cycle):
    cycle, fly, _, _ = setup_cycle
    first = cycle({'fra': 0, 'iad': 80, 'cdg': 100, 'lhr': 60}, max_regions=2)
    assert first['actions_taken']['deployed'] == ['cdg']
    assert first['current_regions'] == ['cdg', 'fra']
    assert len([item for item in first['actions_taken']['skipped']
                if 'Maximum region' in item['reason']]) == 2
    second = cycle({'fra': 0, 'cdg': 0}, advance=61, max_regions=2, min_regions=2)
    assert second['actions_taken']['removed'] == []
    assert second['current_regions'] == ['cdg', 'fra']
    assert fly.calls == [('cdg', 1)]


def test_protected_region_at_capacity_reports_error_without_removing_capacity(setup_cycle):
    cycle, fly, _, _ = setup_cycle
    fly.deployed = {'iad'}
    result = cycle({'iad': 0}, max_regions=1, min_regions=1)
    assert result['actions_taken']['errors']
    assert result['actions_taken']['errors'][0]['region'] == 'fra'
    assert result['actions_taken']['removed'] == []
    assert result['current_regions'] == ['iad']
    assert fly.calls == []


def test_failed_deploy_prevents_removal_and_next_success_adds_before_removing(setup_cycle):
    cycle, fly, scope, _ = setup_cycle
    fly.deployed = {'fra', 'iad'}
    fly.failures = {('cdg', 1)}
    first = cycle({'fra': 0, 'iad': 0, 'cdg': 100})
    assert first['actions_taken']['errors'][0]['region'] == 'cdg'
    assert first['actions_taken']['removed'] == []
    assert fly.deployed == {'fra', 'iad'}
    state = load_placement_state(False, **scope)
    assert 'cdg' in state['last_actions']
    assert 'cdg' not in state['deployed']

    fly.failures.clear()
    second = cycle({'fra': 0, 'iad': 0, 'cdg': 100}, advance=61)
    assert second['actions_taken']['deployed'] == ['cdg']
    assert second['actions_taken']['removed'] == ['iad']
    assert fly.calls == [('cdg', 1), ('cdg', 1), ('iad', 0)]


def test_dry_run_persists_simulation_without_observing_or_changing_fly(setup_cycle):
    cycle, fly, scope, _ = setup_cycle
    first = cycle({'fra': 0, 'iad': 100}, dry_run=True)
    assert first['current_regions'] == ['fra', 'iad']
    second = cycle({'fra': 0, 'iad': 0}, advance=61, dry_run=True)
    assert second['current_regions'] == ['fra']
    assert fly.calls == []
    assert fly.observation_calls == 0
    assert set(load_placement_state(True, **scope)['deployed']) == {'fra'}
    assert load_placement_state(False, **scope)['deployed'] == {}


def test_protected_deployment_failure_and_cooldown_both_preserve_existing_capacity(setup_cycle):
    cycle, fly, _, _ = setup_cycle
    fly.deployed = {'iad', 'cdg'}
    fly.failures = {('fra', 1)}
    first = cycle({'iad': 0, 'cdg': 0})
    assert first['actions_taken']['errors'][0]['region'] == 'fra'
    assert first['actions_taken']['removed'] == []

    second = cycle({'iad': 0, 'cdg': 0}, advance=1)
    assert second['current_regions'] == ['cdg', 'iad']
    assert second['actions_taken']['removed'] == []
    assert fly.calls == [('fra', 1)]
