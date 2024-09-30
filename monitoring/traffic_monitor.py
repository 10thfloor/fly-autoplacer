import random
from datetime import datetime, timedelta
import os
import json
from collections import defaultdict
from utils.state_manager import load_deployment_state

TRAFFIC_HISTORY_FILE = 'data/traffic_history.json'
os.makedirs('data', exist_ok=True)

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
    regions = ['CDG', 'AMS', 'IAD', 'SIN', 'NRT', 'LDN']
    
    # Map regions to IPs
    region_ips = {
        'CDG': '203.0.113.5',
        'AMS': '198.51.100.50',
        'IAD': '198.51.100.23',
        'SIN': '192.0.2.45',
        'NRT': '198.51.100.45',
        'LDN': '198.51.100.55',
    }
    
    # Load current deployment state
    deployment_state = load_deployment_state()
    
    for region in regions:
        # Assign probabilities to generate low traffic for deployed regions
        if region in deployment_state:
            # Deployed regions have higher chance of low traffic
            traffic_level = random.choices(
                population=list(traffic_levels.keys()),
                weights=[0.4, 0.4, 0.1, 0.1],  # Increase chances of 'very_low' and 'low' traffic
                k=1
            )[0]
        else:
            # Non-deployed regions have higher chance of high traffic
            traffic_level = random.choices(
                population=list(traffic_levels.keys()),
                weights=[0.1, 0.1, 0.3, 0.5],  # Increase chances of 'high' traffic
                k=1
            )[0]
        
        min_traffic, max_traffic = traffic_levels[traffic_level]
        num_requests = random.randint(min_traffic, max_traffic)
        
        ip = region_ips[region]
        
        for _ in range(num_requests):
            timestamp = now - timedelta(seconds=random.randint(0, 300))
            simulated_logs.append({'ip': ip, 'timestamp': timestamp.isoformat()})
    
    return simulated_logs

def get_region(ip):
    ip_region_map = {
        '203.0.113.5': 'CDG',
        '198.51.100.50': 'AMS',
        '198.51.100.23': 'IAD',
    }
    return ip_region_map.get(ip, None)

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

def load_traffic_history():
    if os.path.exists(TRAFFIC_HISTORY_FILE):
        with open(TRAFFIC_HISTORY_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_traffic_history(history):
    with open(TRAFFIC_HISTORY_FILE, 'w') as f:
        json.dump(history, f)

def update_traffic_history(current_data):
    """
    Updates the traffic history with the latest data and maintains a maximum number of entries.
    """
    history = load_traffic_history()

    # Keep only the latest N entries
    max_entries = 3
    timestamp = datetime.utcnow().isoformat()
    history[timestamp] = current_data
    if len(history) > max_entries:
        # Remove the oldest entries
        sorted_keys = sorted(history.keys())
        for key in sorted_keys[:-max_entries]:
            del history[key]

    save_traffic_history(history)
    return history