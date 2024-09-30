import random
from datetime import datetime, timedelta
import os
import json
from collections import defaultdict
from utils.state_manager import load_deployment_state

TRAFFIC_LEVEL_WEIGHTS_DEPLOYED = [0.4, 0.4, 0.1, 0.1]
TRAFFIC_LEVEL_WEIGHTS_NON_DEPLOYED = [0.1, 0.1, 0.3, 0.5]
MAX_HISTORY_ENTRIES = 5

IP_REGION_MAP = {
    '203.0.113.5': 'CDG',
    '198.51.100.50': 'AMS',
    '198.51.100.23': 'IAD',
    '192.0.2.45': 'SIN',
    '198.51.100.45': 'NRT',
    '198.51.100.55': 'LDN',
}

def get_recent_logs():
    """
    Simulates recent logs with dynamic traffic patterns to trigger placement actions.
    """
    simulated_logs = []
    now = datetime.utcnow()
    
    # Define possible traffic levels with probabilities
    traffic_levels = {
        'very_low': (0, 10),    # Well below remove threshold
        'low': (11, 29),        # Below remove threshold
        'medium': (30, 70),     # Around thresholds
        'high': (71, 100),      # Above deploy threshold
    }
    traffic_level_weights = {
        'very_low': 0.2,
        'low': 0.3,
        'medium': 0.3,
        'high': 0.2,
    }
    
    # Region list
    regions = list(IP_REGION_MAP.values())
    
    for region in regions:
        # Assign probabilities to generate low traffic for deployed regions
        if region in load_deployment_state():
            # Deployed regions have higher chance of low traffic
            traffic_level = random.choices(
                population=list(traffic_levels.keys()),
                weights=TRAFFIC_LEVEL_WEIGHTS_DEPLOYED,  # Increase chances of 'very_low' and 'low' traffic
                k=1
            )[0]
        else:
            # Non-deployed regions have higher chance of high traffic
            traffic_level = random.choices(
                population=list(traffic_levels.keys()),
                weights=TRAFFIC_LEVEL_WEIGHTS_NON_DEPLOYED,  # Increase chances of 'high' traffic
                k=1
            )[0]
        
        min_traffic, max_traffic = traffic_levels[traffic_level]
        num_requests = random.randint(min_traffic, max_traffic)
        
        ip = next(ip for ip, r in IP_REGION_MAP.items() if r == region)
        
        for _ in range(num_requests):
            timestamp = now - timedelta(seconds=random.randint(0, 300))
            simulated_logs.append({'ip': ip, 'timestamp': timestamp.isoformat()})
    
    return simulated_logs

def get_region(ip):
    return IP_REGION_MAP.get(ip)

def collect_region_traffic():
    logs = get_recent_logs()
    region_counts = defaultdict(int)

    for log in logs:
        ip = log['ip']
        region = get_region(ip)
        if region:
            region_counts[region] += 1

    print(f"Aggregated traffic per region: {dict(region_counts)}")
    return region_counts

