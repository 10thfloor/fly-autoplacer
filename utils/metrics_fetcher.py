import requests
import os
from dotenv import load_dotenv

class MetricsFetcher:
    def __init__(self):
        load_dotenv()
        self.api_url = os.environ.get('FLY_PROMETHEUS_URL')
        self.api_token = os.environ.get('FLY_API_TOKEN')

        if not self.api_token:
            raise ValueError("API token not found. Set FLY_API_TOKEN environment variable.")
        self.headers = {'Authorization': f'{self.api_token}'}
    
    def fetch_region_traffic(self, app_name):
        query = f'sum(fly_edge_http_responses_count{{app="{app_name}"}}[5m]) by (region)'

        response = requests.get(
            f'{self.api_url}/api/v1/query',
            params={'query': query},
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return self.parse_metrics(data)
    
    def parse_metrics(self, data):
        result = {}
        for item in data.get('data', {}).get('result', []):
            region = item['metric'].get('region', 'unknown')
            value = float(item['value'][1])
            result[region] = value
        return result