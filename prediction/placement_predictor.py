import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import yaml
import logging
from utils.config_loader import Config
from utils.fancy_logger import get_logger
import numpy as np

# Load configuration
config = Config.get_config()

# Set up logging
logger = get_logger(__name__)

# Global constants
traffic_threshold = int(config['traffic_threshold'])
deployment_threshold = int(config['deployment_threshold'])
ALLOWED_REGIONS = config.get('allowed_regions', [])
EXCLUDED_REGIONS = config.get('excluded_regions', [])
ALWAYS_RUNNING_REGIONS = config.get('always_running_regions', [])

TRAFFIC_HISTORY_FILE = 'data/traffic_history.json'

def predict_placement_actions(traffic_history, current_deployments):
    logger = logging.getLogger(__name__)
    logger.info("Starting placement prediction with advanced traffic analysis")
    
    config = Config.get_config()
    traffic_threshold = config['traffic_threshold']
    deployment_threshold = config['deployment_threshold']
    EXCLUDED_REGIONS = config.get('excluded_regions', [])
    ALLOWED_REGIONS = config.get('allowed_regions', [])
    ALWAYS_RUNNING_REGIONS = config.get('always_running_regions', [])

    regions_to_deploy = []
    regions_to_remove = []
    skipped_regions = []

    # Define parameters for calculating short-term and long-term traffic averages
    # These parameters are used to analyze recent trends and overall patterns in traffic data
    short_term_window = config['short_term_window']  # Number of recent data points to consider for short-term analysis
    long_term_window = config['long_term_window']  # Number of data points to consider for long-term analysis
    alpha_short = config['alpha_short']  # Exponential smoothing factor for short-term average (higher weight to recent data)
    alpha_long = config['alpha_long']  # Exponential smoothing factor for long-term average (more stable, less reactive)
    
    # These averages will be used to make more informed decisions about deploying or removing regions
    # Short-term average helps detect sudden spikes or drops in traffic
    # Long-term average provides a more stable baseline for overall traffic trends

    traffic_averages = defaultdict(lambda: {'short': 0, 'long': 0, 'count': 0})

    # Check if traffic_history is in the correct format
    if not isinstance(traffic_history, dict):
        logger.error(f"Invalid traffic_history format. Expected dict, got {type(traffic_history)}")
        return [], [], [{"region": "all", "action": "none", "reason": "Invalid traffic history data"}]

    # Sort and limit the history to the long_term_window
    sorted_history = sorted(traffic_history.items(), reverse=True)[:long_term_window]

    for timestamp, data in sorted_history:
        if not isinstance(data, dict):
            logger.warning(f"Invalid data format for timestamp {timestamp}. Skipping.")
            continue
        for region, traffic in data.items():
            if not isinstance(traffic, (int, float)):
                logger.warning(f"Invalid traffic data for region {region} at {timestamp}. Skipping.")
                continue
            if traffic_averages[region]['count'] == 0:
                traffic_averages[region] = {'short': traffic, 'long': traffic, 'count': 1}
            else:
                if traffic_averages[region]['count'] <= short_term_window:
                    traffic_averages[region]['short'] = (
                        alpha_short * traffic + (1 - alpha_short) * traffic_averages[region]['short']
                    )
                traffic_averages[region]['long'] = (
                    alpha_long * traffic + (1 - alpha_long) * traffic_averages[region]['long']
                )
                traffic_averages[region]['count'] += 1

    for region, averages in traffic_averages.items():
        if region in EXCLUDED_REGIONS:
            skipped_regions.append({
                "region": region,
                "action": "deploy",
                "reason": "Region is in excluded_regions list"
            })
            continue

        if ALLOWED_REGIONS and region not in ALLOWED_REGIONS:
            skipped_regions.append({
                "region": region,
                "action": "deploy",
                "reason": "Region is not in allowed_regions list"
            })
            continue

        # Adaptive thresholds
        adaptive_traffic_threshold = max(traffic_threshold, averages['long'] * 1.1)
        adaptive_deployment_threshold = min(deployment_threshold, averages['long'] * 0.9)

        # Use short-term average if available, otherwise use long-term average
        current_average = averages['short'] if averages['count'] >= short_term_window else averages['long']

        if current_average >= adaptive_traffic_threshold:
            if region not in current_deployments:
                regions_to_deploy.append(region)
            else:
                skipped_regions.append({
                    "region": region,
                    "action": "deploy",
                    "reason": f"Region is already deployed. Current avg: {current_average:.2f}, Long-term avg: {averages['long']:.2f}"
                })
        elif current_average <= adaptive_deployment_threshold:
            if region in current_deployments:
                if region in ALWAYS_RUNNING_REGIONS:
                    skipped_regions.append({
                        "region": region,
                        "action": "remove",
                        "reason": "Region is in always_running_regions list"
                    })
                else:
                    regions_to_remove.append(region)
            else:
                skipped_regions.append({
                    "region": region,
                    "action": "remove",
                    "reason": f"Region is not currently deployed. Current avg: {current_average:.2f}, Long-term avg: {averages['long']:.2f}"
                })
        else:
            skipped_regions.append({
                "region": region,
                "action": "none",
                "reason": f"Traffic does not meet adaptive thresholds. Current avg: {current_average:.2f}, Long-term avg: {averages['long']:.2f}"
            })

        logger.debug(f"Region {region}: Current avg: {current_average:.2f}, Long-term avg: {averages['long']:.2f}, Data points: {averages['count']}")

    # Ensure ALWAYS_RUNNING_REGIONS are deployed
    for region in ALWAYS_RUNNING_REGIONS:
        if region not in current_deployments and region not in regions_to_deploy:
            regions_to_deploy.append(region)
            logger.info(f"Adding always-running region {region} to deployment list")

    logger.info(f"Prediction complete. To deploy: {regions_to_deploy}, To remove: {regions_to_remove}, Skipped: {len(skipped_regions)}")
    return regions_to_deploy, regions_to_remove, skipped_regions
