import random
from unittest.mock import Mock

import pytest
import requests

from utils.metrics_fetcher import MetricsFetcher
from utils.mock_traffic_generator import generate_mock_logs, generate_mock_traffic_data


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.setattr('utils.metrics_fetcher.load_dotenv', lambda: None)
    for variable in ('PLACER_TARGET_APP', 'FLY_APP_NAME', 'FLY_API_TOKEN', 'FLY_PROMETHEUS_URL'):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture
def live_fetcher(monkeypatch):
    monkeypatch.setenv('PLACER_TARGET_APP', 'target-app')
    monkeypatch.setenv('FLY_APP_NAME', 'controller-app')
    monkeypatch.setenv('FLY_API_TOKEN', 'secret-token')
    monkeypatch.setenv('FLY_PROMETHEUS_URL', 'https://metrics.example/org/')
    return MetricsFetcher(dry_run=False, config={})


def response_data(items):
    return {'status': 'success', 'data': {'resultType': 'vector', 'result': items}}


def sample(region='iad', value='125'):
    return {'metric': {'region': region}, 'value': [1700000000, value]}


def test_real_query_counts_requests_in_window_and_prefers_target(live_fetcher, monkeypatch):
    response = Mock()
    response.json.return_value = response_data([sample()])
    get = Mock(return_value=response)
    monkeypatch.setattr('utils.metrics_fetcher.requests.get', get)
    assert live_fetcher.fetch_region_traffic() == {'iad': 125}
    assert get.call_args.args[0] == 'https://metrics.example/org/api/v1/query'
    assert get.call_args.kwargs['params']['query'] == (
        'sum(increase(fly_edge_http_responses_count{app="target-app"}[5m])) by (region)')
    assert get.call_args.kwargs['timeout'] == 10
    response.raise_for_status.assert_called_once()


def test_dry_run_ignores_controller_app_name(monkeypatch):
    monkeypatch.setenv('FLY_APP_NAME', 'controller-app')
    assert MetricsFetcher(config={'dry_run': True}).get_app_name() == 'mock-app'
    monkeypatch.setenv('PLACER_TARGET_APP', 'target-app')
    assert MetricsFetcher(config={'dry_run': True}).get_app_name() == 'target-app'


def test_explicit_empty_success_is_distinct_from_error(live_fetcher):
    assert live_fetcher._parse_metrics(response_data([])) == {}
    with pytest.raises(ValueError):
        live_fetcher._parse_metrics({'status': 'error', 'error': 'secret-details'})


@pytest.mark.parametrize('payload', [
    {}, None, {'status': 'success'},
    {'status': 'success', 'data': {'resultType': 'matrix', 'result': []}},
    response_data(None), response_data([{}]),
    response_data([{'metric': {}, 'value': [0, '1']}]),
    response_data([sample(region='')]), response_data([sample(region=' iad ')]),
    response_data([sample(region='unknown')]), response_data([sample(region='IAD')]),
    response_data([sample(), sample()]),
    response_data([{'metric': {'region': 'iad'}, 'values': [[0, '1']]}]),
    response_data([{'metric': {'region': 'iad'}, 'value': [None, '1']}]),
    response_data([{'metric': {'region': 'iad'}, 'value': ['NaN', '1']}]),
    *[response_data([sample(value=value)]) for value in ('NaN', 'Inf', '-1', 'text', None, True)],
])
def test_invalid_metrics_never_become_empty_or_zero_traffic(live_fetcher, payload):
    with pytest.raises(ValueError):
        live_fetcher._parse_metrics(payload)


def test_network_errors_do_not_expose_credentials(live_fetcher, monkeypatch):
    monkeypatch.setattr('utils.metrics_fetcher.requests.get', Mock(
        side_effect=requests.RequestException('secret-token https://sensitive.example')))
    with pytest.raises(RuntimeError, match='Unable to fetch traffic metrics') as error:
        live_fetcher.fetch_region_traffic()
    assert 'secret' not in str(error.value)
    assert 'https' not in str(error.value)


def test_invalid_json_does_not_expose_response_body(live_fetcher, monkeypatch):
    response = Mock()
    response.json.side_effect = ValueError('secret-response-body')
    monkeypatch.setattr('utils.metrics_fetcher.requests.get', Mock(return_value=response))
    with pytest.raises(ValueError, match='invalid JSON') as error:
        live_fetcher.fetch_region_traffic()
    assert 'secret' not in str(error.value)


def test_mock_counts_match_generated_logs_without_creating_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    logs = generate_mock_logs(rng=random.Random(13))
    traffic = generate_mock_traffic_data(logs)
    assert sum(traffic.values()) == len(logs)
    assert traffic['iad'] == sum(entry['ip'] == '198.51.100.23' for entry in logs)
    MetricsFetcher(config={'dry_run': True}).fetch_region_traffic()
    assert list(tmp_path.iterdir()) == []


def test_live_metrics_do_not_fall_back_to_controller_name(monkeypatch):
    monkeypatch.setenv('FLY_APP_NAME', 'controller-app')
    monkeypatch.setenv('FLY_API_TOKEN', 'dummy-token')
    monkeypatch.setenv('FLY_PROMETHEUS_URL', 'https://metrics.example')
    with pytest.raises(ValueError, match='PLACER_TARGET_APP'):
        MetricsFetcher(dry_run=False, config={})
