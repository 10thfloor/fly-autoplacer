# utils/state_manager.py

import os
import json
import logging

logger = logging.getLogger(__name__)

def get_deployment_state_file(dry_run=False):
    if dry_run:
        return 'data/deployment_state_dry_run.json'
    else:
        return 'data/deployment_state.json'

def load_deployment_state(dry_run=False):
    logger.info(f"Loading deployment state (dry_run: {dry_run})")
    DEPLOYMENT_STATE_FILE = get_deployment_state_file(dry_run)
    if os.path.exists(DEPLOYMENT_STATE_FILE):
        try:
            with open(DEPLOYMENT_STATE_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, list):
                        data = {region: None for region in data}
                    logger.info(f"Loaded deployment state with {len(data)} regions")
                    logger.debug(f"Deployment state: {data}")
                    return data
                else:
                    logger.warning("Deployment state file is empty. Initializing with empty dict.")
                    return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in deployment state file: {e}")
            return {}
    else:
        logger.info("Deployment state file does not exist. Initializing with empty dict.")
        return {}

def save_deployment_state(state, dry_run=False):
    logger.info(f"Saving deployment state (dry_run: {dry_run})")
    DEPLOYMENT_STATE_FILE = get_deployment_state_file(dry_run)
    try:
        os.makedirs(os.path.dirname(DEPLOYMENT_STATE_FILE), exist_ok=True)
        with open(DEPLOYMENT_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Deployment state saved with {len(state)} regions")
        logger.debug(f"Saved deployment state: {state}")
    except Exception as e:
        logger.error(f"Error saving deployment state: {str(e)}")
        raise
