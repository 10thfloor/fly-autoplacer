import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import random
from utils.config_loader import Config
from utils.state_manager import load_deployment_state
from utils import mock_traffic_generator
from utils.fancy_logger import get_logger

# Load configuration
config = Config.get_config()

# Set up logging
logger = get_logger(__name__)

class MetricsFetcher:

    def __init__(self, dry_run=None):
        load_dotenv()
        self.dry_run = dry_run if dry_run is not None else config['dry_run']
        
        self.api_url = os.environ.get('FLY_PROMETHEUS_URL')
        self.api_token = os.environ.get('FLY_API_TOKEN')
        self.real_app_name = os.environ.get('FLY_APP_NAME')

        if not self.dry_run:
            if not self.api_token:
                raise ValueError("API token not found. Set FLY_API_TOKEN environment variable.")
            if not self.real_app_name:
                raise ValueError("App name not found. Set FLY_APP_NAME environment variable.")
            self.headers = {'Authorization': f'Bearer {self.api_token}'}
    
    def get_app_name(self):
        if self.dry_run:
            return "mock-app"
        elif self.real_app_name:
            return self.real_app_name
        else:
            raise ValueError("App name not found. Set FLY_APP_NAME environment variable.")

    def fetch_region_traffic(self):
        app_name = self.get_app_name()
        if self.dry_run:
            traffic_data = self._generate_mock_traffic_data(app_name)
        else:
            traffic_data = self._fetch_real_traffic_data(app_name)
        
        logger.info(f"Traffic data for {app_name}:")
        for region, count in traffic_data.items():
            logger.info(f"  {region}: {count}")
        
        return traffic_data

    def _fetch_real_traffic_data(self, app_name):
        query = f'sum(fly_edge_http_responses_count{{app="{app_name}"}}[5m]) by (region)'

        response = requests.get(
            f'{self.api_url}/api/v1/query',
            params={'query': query},
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return self._parse_metrics(data)
    
    def _parse_metrics(self, data):
        result = {}
        for item in data.get('data', {}).get('result', []):
            region = item['metric'].get('region', 'unknown')
            value = float(item['value'][1])
            result[region] = value
        return result

    def _generate_mock_traffic_data(self, mock_app_name):
        mock_logs = mock_traffic_generator.generate_mock_logs(self.dry_run)
        return mock_traffic_generator.generate_mock_traffic_data(mock_logs)
