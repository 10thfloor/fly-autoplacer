# utils/state_manager.py

import os
import json

DEPLOYMENT_STATE_FILE = 'data/deployment_state.json'
os.makedirs('data', exist_ok=True)

def load_deployment_state():
    if os.path.exists(DEPLOYMENT_STATE_FILE):
        with open(DEPLOYMENT_STATE_FILE, 'r') as f:
            return json.load(f)
    else:
        return []

def save_deployment_state(state):
    with open(DEPLOYMENT_STATE_FILE, 'w') as f:
        json.dump(state, f)
