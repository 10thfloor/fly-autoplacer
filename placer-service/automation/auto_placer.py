"""
Module: auto_placer.py
Description: Automates the placement of machines in Fly.io regions based on traffic patterns.
"""

import logging
import os
import subprocess
import yaml
import json
from datetime import datetime, timezone
from monitoring.traffic_monitor import collect_region_traffic
from utils.history_manager import update_traffic_history
from prediction.placement_predictor import PlacementPredictor
from utils.state_manager import load_deployment_state, save_deployment_state
from utils.fancy_logger import get_logger
from utils.history_manager import load_traffic_history
from dateutil.parser import isoparse
from utils.config_loader import Config
from logging.handlers import RotatingFileHandler
from utils.metrics_fetcher import MetricsFetcher
from metrics.metrics_client import MetricsClient

# Load configuration
config = Config.get_config()

# Set up logging
logger = get_logger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create file handler
file_handler = RotatingFileHandler(
    'data/logs/auto_placer.log',
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

DRY_RUN = config['dry_run']
COOLDOWN_PERIOD = int(config['cooldown_period'])
ALLOWED_REGIONS = config.get('allowed_regions', [])
EXCLUDED_REGIONS = config.get('excluded_regions', [])
ALWAYS_RUNNING_REGIONS = config.get('always_running_regions', [])

FLY_APP_NAME = os.getenv("FLY_APP_NAME")

# If it's a dry run, don't actually deploy or remove machines
if DRY_RUN:
    logger.info("Dry run mode is enabled. No changes will be applied.")
    # set the app name to the current directory name
    FLY_APP_NAME = os.path.basename(os.getcwd())

class AutoPlacer:
    def __init__(self, config):
        self.dry_run = config.get('dry_run', True)
        self.excluded_regions = config.get('excluded_regions', [])
        self.allowed_regions = config.get('allowed_regions', [])  # Add this line
        self.always_running_regions = config.get('always_running_regions', [])
        self.predictor = PlacementPredictor(config)
        self.logger = get_logger(__name__)

    async def process_traffic_data(self):
        """Main processing loop"""
        metrics_fetcher = MetricsFetcher(dry_run=self.dry_run)
        app_name = metrics_fetcher.get_app_name()
        
        self.logger.info(f"Starting auto-placer execution for app: {app_name}")
        
        # Collect and process traffic data
        current_data = collect_region_traffic()
        update_traffic_history(current_data, dry_run=self.dry_run)
        
        # Get current state
        current_state = load_deployment_state(dry_run=self.dry_run)
        current_regions = list(current_state.keys())
        
        # Load traffic history
        traffic_history = load_traffic_history(dry_run=self.dry_run)
        
        # Process each region
        actions_needed = []
        for region, traffic_stats in traffic_history.items():
            if self._should_process_region(region):
                action = self.predictor.predict_placement_actions(region, traffic_stats)
                if action:
                    actions_needed.append((region, action))

        # Execute the needed actions
        return await self._execute_actions(actions_needed, current_state)

    def _should_process_region(self, region: str) -> bool:
        """Determine if a region should be processed based on configuration."""
        if region in self.excluded_regions:
            return False
        if self.allowed_regions and region not in self.allowed_regions:
            return False
        return True

    async def _execute_actions(self, actions_needed, current_state):
        """Execute the required placement actions."""
        regions_to_deploy = []
        regions_to_remove = []
        
        for region, action in actions_needed:
            if action == 'scale_up' and region not in current_state:
                regions_to_deploy.append(region)
            elif action == 'scale_down' and region in current_state:
                regions_to_remove.append(region)
        
        updated_regions, action_results = update_placements(
            regions_to_deploy, 
            regions_to_remove
        )
        
        return {
            "actions_taken": action_results,
            "updated_regions": updated_regions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _is_in_cooldown(self, region: str, current_state: dict) -> bool:
        """Check if a region is in cooldown period"""
        last_action_time_str = current_state.get(region)
        if not last_action_time_str:
            return False

        last_action_time = isoparse(last_action_time_str)
        if last_action_time.tzinfo is None:
            last_action_time = last_action_time.replace(tzinfo=timezone.utc)
        
        elapsed_time = (datetime.now(timezone.utc) - last_action_time).total_seconds()
        return elapsed_time < self.cooldown_period

def update_placements(regions_to_deploy, regions_to_remove):
    """Update machine placements in Fly.io regions."""
    action_results = {
        "deployed": [],
        "removed": [],
        "skipped": [],
        "errors": []
    }
    updated_regions = []

    # Process deployments
    for region in regions_to_deploy:
        try:
            if not DRY_RUN:
                subprocess.run(['fly', 'scale', 'count', '1', '--region', region], check=True)
            action_results["deployed"].append(region)
            updated_regions.append(region)
        except Exception as e:
            action_results["errors"].append({"region": region, "action": "deploy", "error": str(e)})

    # Process removals
    for region in regions_to_remove:
        try:
            if not DRY_RUN:
                subprocess.run(['fly', 'scale', 'count', '0', '--region', region], check=True)
            action_results["removed"].append(region)
            updated_regions.append(region)
        except Exception as e:
            action_results["errors"].append({"region": region, "action": "remove", "error": str(e)})

    return updated_regions, action_results

def main():
    config = Config.get_config()
    metrics_client = MetricsClient()
    auto_placer = AutoPlacer(config, metrics_client)
    
    try:
        action_results = auto_placer.process_traffic_data()
        logger.info(f"Auto-placer execution completed. Results: {action_results}")
        return action_results
    except Exception as e:
        logger.error(f"Error during auto-placer execution: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
