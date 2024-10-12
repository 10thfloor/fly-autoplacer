import random
from datetime import datetime, timedelta
from utils.state_manager import load_deployment_state
from utils.history_manager import update_traffic_history

MOCK_IP_REGION_MAP = {
    '203.0.113.5': 'cdg',
    '198.51.100.50': 'ams',
    '198.51.100.23': 'iad',
    '192.0.2.45': 'sin',
    '198.51.100.45': 'nrt',
    '198.51.100.55': 'lhr',
}

MOCK_TRAFFIC_LEVEL_RANGES = {
    'very_low': (0, 10),    # 0 to 10 requests
    'low': (11, 29),        # 11 to 29 requests
    'medium': (30, 70),     # 30 to 70 requests
    'high': (71, 100),      # 71 to 100 requests
}
# These weights determine the probability distribution of traffic levels for deployed and non-deployed regions
# For deployed regions, there's a higher chance of lower traffic (potentially triggering scale-down)
# For non-deployed regions, there's a higher chance of higher traffic (potentially triggering scale-up)
# This simulates a scenario where we might need to adjust our deployment based on changing traffic patterns

MOCK_TRAFFIC_LEVEL_WEIGHTS_DEPLOYED = [0.4, 0.3, 0.2, 0.1]  # very_low, low, medium, high
MOCK_TRAFFIC_LEVEL_WEIGHTS_NON_DEPLOYED = [0.1, 0.2, 0.3, 0.4]  # very_low, low, medium, high

def generate_mock_logs(dry_run):
    """
    Generate mock recent logs simulating traffic across different regions.
    """
    mock_logs = []
    now = datetime.utcnow()
    
    mock_current_state = load_deployment_state(dry_run)
    current_traffic = {}
    
    for region in MOCK_IP_REGION_MAP.values():
        is_deployed = region in mock_current_state
        
        weights = MOCK_TRAFFIC_LEVEL_WEIGHTS_DEPLOYED if is_deployed else MOCK_TRAFFIC_LEVEL_WEIGHTS_NON_DEPLOYED
        
        mock_traffic_level = random.choices(
            population=list(MOCK_TRAFFIC_LEVEL_RANGES.keys()),
            weights=weights,
            k=1
        )[0]
        
        min_requests, max_requests = MOCK_TRAFFIC_LEVEL_RANGES[mock_traffic_level]
        num_requests = random.randint(min_requests, max_requests)
        
        current_traffic[region] = num_requests
        
        mock_ip = next(ip for ip, r in MOCK_IP_REGION_MAP.items() if r == region)
        
        for _ in range(num_requests):
            mock_timestamp = now - timedelta(seconds=random.randint(0, 300))
            mock_logs.append({'ip': mock_ip, 'timestamp': mock_timestamp.isoformat()})
    
    # Update traffic history
    update_traffic_history(current_traffic, dry_run)
    
    return mock_logs

def generate_mock_traffic_data(mock_logs):
    """
    Generate mock traffic data from mock logs.

    Args:
        mock_logs (list): List of mock log entries.

    Returns:
        dict: A dictionary with regions as keys and request counts as values.
    """
    mock_traffic_data = {}
    for log in mock_logs:
        region = MOCK_IP_REGION_MAP.get(log['ip'])
        if region:
            mock_traffic_data[region] = mock_traffic_data.get(region, 0) + 1
    return mock_traffic_data

def get_mock_region(ip):
    """
    Get the region for a given IP address.

    Args:
        ip (str): The IP address to look up.

    Returns:
        str: The region corresponding to the IP address, or None if not found.
    """
    return MOCK_IP_REGION_MAP.get(ip)