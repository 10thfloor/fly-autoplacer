# utils/state_manager.py

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_deployment_state_file(dry_run=False):
    return 'data/deployment_state_dry_run.json' if dry_run else 'data/deployment_state.json'

def load_deployment_state(dry_run=False):
    state_file = get_deployment_state_file(dry_run)
    logger.info(f"Loading deployment state from {state_file} (dry_run: {dry_run})")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    logger.info(f"Loaded deployment state with {len(data)} entries")
                    logger.debug(f"Deployment state: {data}")
                    return data
                else:
                    logger.warning("Deployment state file is empty. Returning empty dict.")
                    return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in deployment state file: {e}")
        except Exception as e:
            logger.error(f"Error reading deployment state file: {e}")
    else:
        logger.info("Deployment state file does not exist. Returning empty dict.")
    return {}

def save_deployment_state(state, dry_run=False):
    state_file = get_deployment_state_file(dry_run)
    logger.info(f"Saving deployment state to {state_file} (dry_run: {dry_run})")
    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Deployment state saved with {len(state)} entries")
        logger.debug(f"Saved deployment state: {state}")
    except Exception as e:
        logger.error(f"Error saving deployment state: {e}")
        raise

