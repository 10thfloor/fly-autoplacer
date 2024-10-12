"""
Module: auto_placer.py
Description: Automates the placement of machines in Fly.io regions based on traffic patterns.
"""

import logging
import os
import subprocess
import yaml
import json
from datetime import datetime, timedelta
from monitoring.traffic_monitor import collect_region_traffic
from utils.history_manager import update_traffic_history
from prediction.placement_predictor import predict_placement_actions
from utils.state_manager import load_deployment_state, save_deployment_state
from utils.fancy_logger import get_logger, log_action
from dateutil.parser import isoparse
from utils.config_loader import Config
from logging.handlers import RotatingFileHandler
from utils.metrics_fetcher import MetricsFetcher

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create file handler
file_handler = RotatingFileHandler(
    'logs/auto_placer.log',
    maxBytes=1024 * 1024,  # 1 MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load configuration
config = Config.get_config()

DRY_RUN = config['dry_run']
COOLDOWN_PERIOD = int(config['cooldown_period'])  # Ensure this is an integer

ALLOWED_REGIONS = config.get('allowed_regions', [])
EXCLUDED_REGIONS = config.get('excluded_regions', [])
ALWAYS_RUNNING_REGIONS = config.get('always_running_regions', [])

FLY_APP_NAME = os.getenv("FLY_APP_NAME")

# If it's a dry run, don't actually deploy or remove machines
if DRY_RUN:
    logger.info("Dry run mode is enabled. No changes will be applied.")
    # set the app name to the current directory name
    FLY_APP_NAME = os.path.basename(os.getcwd())

def get_current_regions():
    deployment_state = load_deployment_state(dry_run=DRY_RUN)
    current_regions = list(deployment_state.keys())
    print(f"Current deployment regions: {current_regions}")
    return current_regions

def update_placements(regions_to_deploy, regions_to_remove):
    current_state = load_deployment_state(dry_run=DRY_RUN)
    updated_state = current_state.copy()
    now = datetime.utcnow()
    action_results = {"deployed": [], "removed": [], "skipped": []}

    # Deploy machines
    for region in regions_to_deploy:
        if region not in updated_state:
            last_action_time_str = current_state.get(region)
            if last_action_time_str:
                last_action_time = isoparse(last_action_time_str)
                elapsed_time = (now - last_action_time).total_seconds()
                if elapsed_time < COOLDOWN_PERIOD:
                    remaining = int(COOLDOWN_PERIOD - elapsed_time)
                    logger.info(f"Skipping deployment to {region} due to cooldown period ({remaining} seconds remaining).")
                    action_results["skipped"].append({
                        "region": region,
                        "action": "deploy",
                        "reason": f"Cooldown period ({remaining} seconds remaining)"
                    })
                    continue
            
            if region in EXCLUDED_REGIONS:
                logger.info(f"Skipping deployment to {region} as it's in the excluded_regions list.")
                action_results["skipped"].append({
                    "region": region,
                    "action": "deploy",
                    "reason": "Region is in excluded_regions list"
                })
                continue
            
            if ALLOWED_REGIONS and region not in ALLOWED_REGIONS:
                logger.info(f"Skipping deployment to {region} as it's not in the allowed_regions list.")
                action_results["skipped"].append({
                    "region": region,
                    "action": "deploy",
                    "reason": "Region is not in allowed_regions list"
                })
                continue

            updated_state[region] = now.isoformat()

            if DRY_RUN:
                logger.info(f"[DRY RUN] Would deploy machine to region: {region}")
            else:
                logger.info(f"Deploying machine to region: {region}")
                # deploy_machine(region)
            
            action_results["deployed"].append(region)

    # Remove machines
    for region in regions_to_remove:
        if region in updated_state:
            if region in ALWAYS_RUNNING_REGIONS:
                logger.info(f"Skipping removal of {region} as it's in the always_running_regions list.")
                action_results["skipped"].append({
                    "region": region,
                    "action": "remove",
                    "reason": "Region is in always_running_regions list"
                })
                continue

            last_action_time_str = current_state.get(region)
            if last_action_time_str:
                last_action_time = isoparse(last_action_time_str)
                elapsed_time = (now - last_action_time).total_seconds()
                if elapsed_time < COOLDOWN_PERIOD:
                    remaining = int(COOLDOWN_PERIOD - elapsed_time)
                    logger.info(f"Skipping removal from {region} due to cooldown period ({remaining} seconds remaining).")
                    action_results["skipped"].append({
                        "region": region,
                        "action": "remove",
                        "reason": f"Cooldown period ({remaining} seconds remaining)"
                    })
                    continue

            del updated_state[region]

            if DRY_RUN:
                logger.info(f"[DRY RUN] Would remove machine from region: {region}")
            else:
                logger.info(f"Removing machine from region: {region}")
                # remove_machine(region)
            
            action_results["removed"].append(region)

    save_deployment_state(updated_state, dry_run=DRY_RUN)
    return list(updated_state.keys()), action_results

def main():
    metrics_fetcher = MetricsFetcher()
    app_name = metrics_fetcher.get_app_name()
    
    logger.info(f"Starting auto-placer execution for app: {app_name}")
    logger.info(f"Collecting current traffic data for app: {app_name}...")
    current_data = collect_region_traffic()
    logger.debug(f"Current traffic data for app {app_name}: {current_data}")
    
    logger.info("Updating traffic history...")
    update_traffic_history(current_data)
    
    logger.info("Retrieving current deployment regions...")
    current_state = load_deployment_state(dry_run=DRY_RUN)
    current_regions = list(current_state.keys())
    logger.info(f"Current deployment regions: {current_regions}")
    
    logger.info("Predicting placement actions...")
    regions_to_deploy, regions_to_remove = predict_placement_actions(current_data, current_regions)
    
    logger.info(f"Regions to deploy machines: {regions_to_deploy}")
    logger.info(f"Regions to remove machines: {regions_to_remove}")
    
    logger.info("Updating placements...")
    current_regions, action_results = update_placements(regions_to_deploy, regions_to_remove)
    logger.info(f"Update complete. Deployment state: {current_regions}")
    
    result = {
        "current_regions": current_regions,
        "action_results": action_results,
        "dry_run": DRY_RUN,
        "status": "Success"
    }
    
    logger.info("Auto-placer execution completed")
    return result
