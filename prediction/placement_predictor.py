import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import yaml

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Ensure thresholds are integers
SCALE_UP_THRESHOLD = int(config['scale_up_threshold'])
SCALE_DOWN_THRESHOLD = int(config['scale_down_threshold'])

print(f"SCALE_UP_THRESHOLD: {SCALE_UP_THRESHOLD}, Type: {type(SCALE_UP_THRESHOLD)}")
print(f"SCALE_DOWN_THRESHOLD: {SCALE_DOWN_THRESHOLD}, Type: {type(SCALE_DOWN_THRESHOLD)}")

TRAFFIC_HISTORY_FILE = 'data/traffic_history.json'

def predict_placement_actions(history, current_regions):
    # Calculate average traffic per region
    region_totals = defaultdict(int)
    region_counts = defaultdict(int)
    for data in history.values():
        for region, count in data.items():
            region_totals[region] += count
            region_counts[region] += 1
    
    average_traffic = {
        region: region_totals[region] / region_counts[region]
        for region in region_totals
    }
    print(f"Average traffic per region: {average_traffic}")
    
    # Determine placement actions
    regions_to_deploy = [
        region for region, avg in average_traffic.items()
        if avg > SCALE_UP_THRESHOLD and region not in current_regions
    ]
    regions_to_remove = [
        region for region, avg in average_traffic.items()
        if avg < SCALE_DOWN_THRESHOLD and region in current_regions
    ]
    
    return regions_to_deploy, regions_to_remove