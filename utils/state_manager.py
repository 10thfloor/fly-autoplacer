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
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {}

def save_deployment_state(state, dry_run=False):
    state_file = get_deployment_state_file(dry_run)
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def get_traffic_history_file(dry_run=False):
    return 'data/traffic_history_dry_run.json' if dry_run else 'data/traffic_history.json'

def load_traffic_history(dry_run=False):
    history_file = get_traffic_history_file(dry_run)
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
            return {datetime.fromisoformat(k): v for k, v in history.items()}
    return {}

def save_traffic_history(history, dry_run=False):
    history_file = get_traffic_history_file(dry_run)
    serializable_history = {k.isoformat(): v for k, v in history.items()}
    with open(history_file, 'w') as f:
        json.dump(serializable_history, f, indent=2)
