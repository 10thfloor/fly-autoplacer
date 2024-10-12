import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import yaml
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Ensure thresholds are integers
SCALE_UP_THRESHOLD = int(config['scale_up_threshold'])
SCALE_DOWN_THRESHOLD = int(config['scale_down_threshold'])

ALLOWED_REGIONS = config.get('allowed_regions', [])
EXCLUDED_REGIONS = config.get('excluded_regions', [])
ALWAYS_RUNNING_REGIONS = config.get('always_running_regions', [])

TRAFFIC_HISTORY_FILE = 'data/traffic_history.json'

def predict_placement_actions(current_traffic, current_regions):
    logger.info("Starting placement prediction")
    
    region_totals = defaultdict(int)
    region_counts = defaultdict(int)

    for region, count in current_traffic.items():
        region_totals[region] += count
        region_counts[region] += 1
    
    average_traffic = {
        region: region_totals[region] / region_counts[region]
        for region in region_totals
    }
    logger.info(f"Calculated average traffic for {len(average_traffic)} regions")
    logger.debug(f"Average traffic per region: {average_traffic}")
    
    regions_to_deploy = [
        region for region, avg in average_traffic.items()
        if (
            avg > SCALE_UP_THRESHOLD
            and region not in EXCLUDED_REGIONS
            and (not ALLOWED_REGIONS or region in ALLOWED_REGIONS)
            and region not in current_regions
        )
    ]
    logger.info(f"Predicted {len(regions_to_deploy)} regions to deploy")
    logger.debug(f"Regions to deploy: {regions_to_deploy}")

    for region in ALWAYS_RUNNING_REGIONS:
        if region not in current_regions and region not in regions_to_deploy:
            regions_to_deploy.append(region)
            logger.info(f"Added always-running region {region} to deployment list")

    regions_to_remove = [
        region for region in current_regions
        if (
            (
                average_traffic.get(region, 0) < SCALE_DOWN_THRESHOLD
                and region not in ALWAYS_RUNNING_REGIONS
            )
            or (region in EXCLUDED_REGIONS and region not in ALWAYS_RUNNING_REGIONS)
            or (ALLOWED_REGIONS and region not in ALLOWED_REGIONS and region not in ALWAYS_RUNNING_REGIONS)
        )
    ]
    logger.info(f"Predicted {len(regions_to_remove)} regions to remove")
    logger.debug(f"Regions to remove: {regions_to_remove}")

    # Ensure regions are unique
    regions_to_deploy = list(set(regions_to_deploy))
    regions_to_remove = list(set(regions_to_remove))

    return regions_to_deploy, regions_to_remove
