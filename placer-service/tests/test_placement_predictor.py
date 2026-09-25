from unittest.mock import Mock

import pytest

from prediction.placement_predictor import PlacementPredictor


@pytest.mark.parametrize('traffic', [50, 51, 1000, 1000000])
def test_bootstrap_and_sustained_high_traffic_can_deploy(traffic):
    config = {'traffic_threshold': 50, 'deployment_threshold': 10}
    for _ in range(3):
        predictor = PlacementPredictor(config)
        assert predictor.predict_placement_actions('iad', {
            'short': traffic, 'long': traffic, 'baseline': traffic,
        }) == 'scale_up'


def test_recent_demand_can_deploy_despite_lower_long_term_average():
    predictor = PlacementPredictor({'traffic_threshold': 50, 'deployment_threshold': 10})
    assert predictor.predict_placement_actions('iad', {'short': 60, 'long': 20}) == 'scale_up'


@pytest.mark.parametrize('short,long,expected', [
    (10, 10, 'scale_down'), (0, 0, 'scale_down'),
    (0, 100, None), (20, 0, None), (30, 30, None),
])
def test_removal_requires_both_windows_below_threshold(short, long, expected):
    predictor = PlacementPredictor({'traffic_threshold': 50, 'deployment_threshold': 10})
    assert predictor.predict_placement_actions('iad', {'short': short, 'long': long}) == expected


def test_previous_traffic_spike_cannot_raise_removal_threshold():
    predictor = PlacementPredictor({'traffic_threshold': 50, 'deployment_threshold': 10})
    assert predictor.predict_placement_actions('iad', {
        'short': 40, 'long': 40, 'baseline': 1000000,
    }) is None


@pytest.mark.parametrize('averages', [{}, {'iad': 100}, {'long': 100}, {'short': 100}])
def test_incomplete_averages_do_not_cause_actions(averages):
    assert PlacementPredictor({}).predict_placement_actions('iad', averages) is None


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, True, '50'])
def test_invalid_averages_are_rejected(value):
    with pytest.raises(ValueError):
        PlacementPredictor({}).predict_placement_actions('iad', {'short': value, 'long': 10})


def test_metrics_record_actual_decision_and_thresholds():
    metrics = Mock()
    predictor = PlacementPredictor({'traffic_threshold': 50, 'deployment_threshold': 10}, metrics)
    predictor.predict_placement_actions('iad', {'short': 75, 'long': 25})
    record = metrics.record_threshold_metrics.call_args.args[0]
    assert record['action'] == 'scale_up'
    assert record['current_traffic'] == 75
    assert record['long_term_traffic'] == 25
    assert record['traffic_threshold'] == 50
