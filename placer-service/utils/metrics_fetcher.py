"""Collect validated request counts over the most recent five minutes."""

import json
import math
import os
import re
import requests
from dotenv import load_dotenv
from utils.config_loader import Config
from utils import mock_traffic_generator


class MetricsFetcher:
    def __init__(self, dry_run=None, config=None):
        load_dotenv()
        self.config = Config.get_config() if config is None else config
        self.dry_run = self.config.get('dry_run', True) if dry_run is None else dry_run
        self.api_url = os.environ.get('FLY_PROMETHEUS_URL')
        self.api_token = os.environ.get('FLY_API_TOKEN')
        self.target_app_name = os.environ.get('PLACER_TARGET_APP')
        self.real_app_name = self.target_app_name
        if not self.dry_run:
            for variable, value in (('FLY_API_TOKEN', self.api_token),
                                    ('PLACER_TARGET_APP', self.real_app_name),
                                    ('FLY_PROMETHEUS_URL', self.api_url)):
                if not value:
                    raise ValueError(f'{variable} must be set for live metrics')
            self.headers = {'Authorization': f'Bearer {self.api_token}'}

    def get_app_name(self):
        if self.dry_run:
            return self.target_app_name or 'mock-app'
        if self.real_app_name:
            return self.real_app_name
        raise ValueError('PLACER_TARGET_APP must be set for live metrics')

    def fetch_region_traffic(self):
        if self.dry_run:
            return self._generate_mock_traffic_data(self.get_app_name())
        return self._fetch_real_traffic_data(self.get_app_name())

    def _fetch_real_traffic_data(self, app_name):
        query = ('sum(increase(fly_edge_http_responses_count{app='
                 + json.dumps(app_name) + '}[5m])) by (region)')
        try:
            response = requests.get(
                f'{self.api_url.rstrip("/")}/api/v1/query',
                params={'query': query}, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            raise RuntimeError('Unable to fetch traffic metrics') from None
        try:
            data = response.json()
        except (ValueError, TypeError):
            raise ValueError('Metrics endpoint returned invalid JSON') from None
        return self._parse_metrics(data)

    def _parse_metrics(self, data):
        if not isinstance(data, dict) or data.get('status') != 'success':
            raise ValueError('Metrics endpoint did not return a successful query')
        payload = data.get('data')
        if not isinstance(payload, dict) or payload.get('resultType') != 'vector':
            raise ValueError('Metrics endpoint must return an instant vector')
        items = payload.get('result')
        if not isinstance(items, list):
            raise ValueError('Metrics endpoint returned malformed results')
        result = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get('metric'), dict):
                raise ValueError('Metrics endpoint returned malformed series')
            region = item['metric'].get('region')
            if not isinstance(region, str) or re.fullmatch(r'[a-z]{3}', region) is None:
                raise ValueError('Metrics series is missing a valid region')
            if region in result:
                raise ValueError('Metrics query returned duplicate regions')
            sample = item.get('value')
            if not isinstance(sample, (list, tuple)) or len(sample) != 2:
                raise ValueError('Metrics series is missing an instant sample')
            if isinstance(sample[0], bool) or not isinstance(sample[0], (str, int, float)):
                raise ValueError('Metrics sample timestamp must be numeric')
            try:
                timestamp = float(sample[0])
            except (ValueError, TypeError, OverflowError):
                raise ValueError('Metrics sample timestamp must be numeric') from None
            if not math.isfinite(timestamp) or timestamp < 0:
                raise ValueError('Metrics sample timestamp must be finite and nonnegative')
            if isinstance(sample[1], bool) or not isinstance(sample[1], (str, int, float)):
                raise ValueError('Metrics counts must be numeric')
            try:
                value = float(sample[1])
            except (ValueError, TypeError, OverflowError):
                raise ValueError('Metrics counts must be numeric') from None
            if not math.isfinite(value) or value < 0:
                raise ValueError('Metrics counts must be finite and nonnegative')
            result[region] = value
        return result

    def _generate_mock_traffic_data(self, mock_app_name):
        logs = mock_traffic_generator.generate_mock_logs(self.dry_run)
        return mock_traffic_generator.generate_mock_traffic_data(logs)
