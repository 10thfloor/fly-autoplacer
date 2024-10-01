"""
Module: auto_placer.py
Description: Automates the placement of machines in Fly.io regions based on traffic patterns.
"""

import logging
import os
import subprocess
import yaml
from datetime import datetime, timedelta
from monitoring.traffic_monitor import collect_region_traffic
from utils.history_manager import update_traffic_history
from prediction.placement_predictor import predict_placement_actions
from utils.state_manager import load_deployment_state, save_deployment_state
from utils.fancy_logger import get_logger, log_action
from dateutil.parser import isoparse  

logger = get_logger(__name__)

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

DRY_RUN = config['dry_run']
COOLDOWN_PERIOD = int(config['cooldown_period'])  # Ensure this is an integer

ALLOWED_REGIONS = config.get('allowed_regions', [])
EXCLUDED_REGIONS = config.get('excluded_regions', [])
ALWAYS_RUNNING_REGIONS = config.get('always_running_regions', [])

def get_current_regions():
    deployment_state = load_deployment_state()
    current_regions = [region for region in deployment_state]
    print(f"Current deployment regions: {current_regions}")
    return current_regions

def update_placements(regions_to_deploy, regions_to_remove):
    deployment_state = load_deployment_state()
    now = datetime.utcnow()

    # Deploy machines
    for region in regions_to_deploy:
        last_action_time_str = deployment_state.get(region)
        if last_action_time_str:
            last_action_time = isoparse(last_action_time_str)
            elapsed_time = (now - last_action_time).total_seconds()
            if elapsed_time < COOLDOWN_PERIOD:
                remaining = int(COOLDOWN_PERIOD - elapsed_time)
                logger.info(f"Skipping deployment to {region} due to cooldown period ({remaining} seconds remaining).")
                continue
        else:
            elapsed_time = None  # No previous action

        log_action("deploy", region, DRY_RUN)
        deployment_state[region] = now.isoformat()
        save_deployment_state(deployment_state)

        if DRY_RUN:
            print(f"[DRY RUN] Would deploy machine to region: {region}")
        else:
            logger.info(f"Deploying machine to region: {region}")
            subprocess.run(['bash', 'scripts/deploy_machine.sh', region, config.FLY_APP_NAME])

    # Remove machines
    for region in regions_to_remove:
        if region not in deployment_state:
            continue  # Not deployed

        if region in ALWAYS_RUNNING_REGIONS:
            logger.info(f"Skipping removal of always running region: {region}")
            continue

        last_action_time_str = deployment_state.get(region)
        if last_action_time_str:
            last_action_time = isoparse(last_action_time_str)
            elapsed_time = (now - last_action_time).total_seconds()
            if elapsed_time < COOLDOWN_PERIOD:
                remaining = int(COOLDOWN_PERIOD - elapsed_time)
                logger.info(f"Skipping removal from {region} due to cooldown period ({remaining} seconds remaining).")
                continue
        else:
            elapsed_time = None  # No previous action

        log_action("remove", region, DRY_RUN)
        del deployment_state[region]
        save_deployment_state(deployment_state)

        if DRY_RUN:
            print(f"[DRY RUN] Would remove machine from region: {region}")
        else:
            logger.info(f"Removing machine from region: {region}")
            subprocess.run(['bash', 'scripts/remove_machine.sh', region, config.FLY_APP_NAME])

def main():
    logger.info("Collecting current traffic data...")
    current_data = collect_region_traffic()
    logger.debug(f"Current traffic data: {current_data}")
    
    print("Updating traffic history...")
    history = update_traffic_history(current_data)
    
    print("Retrieving current deployment regions...")
    current_regions = get_current_regions()
    
    print("Predicting placement actions...")
    regions_to_deploy, regions_to_remove = predict_placement_actions(history, current_regions)
    
    print(f"Regions to deploy machines: {regions_to_deploy}")
    print(f"Regions to remove machines: {regions_to_remove}")
    
    print("Updating placements...")
    update_placements(regions_to_deploy, regions_to_remove)
    print("Update complete.")