"""Generate mock observations without reading or writing application state."""

import random
from datetime import datetime, timedelta, timezone

MOCK_IP_REGION_MAP = {
    '203.0.113.5': 'cdg',
    '198.51.100.50': 'ams',
    '198.51.100.23': 'iad',
    '192.0.2.45': 'sin',
    '198.51.100.45': 'nrt',
    '198.51.100.55': 'lhr',
    '198.51.100.65': 'fra',
    '198.51.100.75': 'sfo',
}
MOCK_TRAFFIC_LEVEL_RANGES = {
    'very_low': (0, 10), 'low': (11, 29), 'medium': (30, 70), 'high': (71, 100),
}
MOCK_TRAFFIC_LEVEL_WEIGHTS_DEPLOYED = [0.4, 0.3, 0.2, 0.1]
MOCK_TRAFFIC_LEVEL_WEIGHTS_NON_DEPLOYED = [0.1, 0.2, 0.3, 0.4]


def generate_mock_logs(dry_run=True, *, current_deployments=None, rng=None):
    """Return the actual log sample that will be counted by the mock fetcher."""
    generator = rng if rng is not None else random
    deployments = current_deployments or {}
    now = datetime.now(timezone.utc)
    logs = []
    for ip, region in MOCK_IP_REGION_MAP.items():
        weights = (MOCK_TRAFFIC_LEVEL_WEIGHTS_DEPLOYED if region in deployments
                   else MOCK_TRAFFIC_LEVEL_WEIGHTS_NON_DEPLOYED)
        level = generator.choices(list(MOCK_TRAFFIC_LEVEL_RANGES), weights=weights, k=1)[0]
        lower, upper = MOCK_TRAFFIC_LEVEL_RANGES[level]
        for _ in range(generator.randint(lower, upper)):
            timestamp = now - timedelta(seconds=generator.randint(0, 300))
            logs.append({'ip': ip, 'timestamp': timestamp.isoformat()})
    return logs


def generate_mock_traffic_data(mock_logs):
    traffic = {region: 0 for region in MOCK_IP_REGION_MAP.values()}
    for entry in mock_logs:
        region = get_mock_region(entry.get('ip'))
        if region is not None:
            traffic[region] += 1
    return traffic


def get_mock_region(ip):
    return MOCK_IP_REGION_MAP.get(ip)
