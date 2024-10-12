import json
import os
from datetime import datetime

def get_traffic_history_file(dry_run):
    return 'data/traffic_history_dry_run.json' if dry_run else 'data/traffic_history.json'

def load_traffic_history(dry_run):
    history_file = get_traffic_history_file(dry_run)
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
            return {datetime.fromisoformat(k): v for k, v in history.items()}
    return {}

def save_traffic_history(history, dry_run):
    history_file = get_traffic_history_file(dry_run)
    serializable_history = {k.isoformat(): v for k, v in history.items()}
    with open(history_file, 'w') as f:
        json.dump(serializable_history, f, indent=2)

def update_traffic_history(current_traffic, dry_run):
    history = load_traffic_history(dry_run)
    now = datetime.utcnow()
    history[now] = current_traffic
    
    # Keep only the last 5 entries
    sorted_history = dict(sorted(history.items(), reverse=True)[:5])
    
    save_traffic_history(sorted_history, dry_run)
