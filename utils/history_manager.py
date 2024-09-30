from datetime import datetime
import json
import logging
import os

TRAFFIC_HISTORY_FILE = 'data/traffic_history.json'

logger = logging.getLogger(__name__)

def load_traffic_history():
    if os.path.exists(TRAFFIC_HISTORY_FILE):
        try:
            with open(TRAFFIC_HISTORY_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    logger.warning("Traffic history file is empty. Initializing with empty dict.")
                    return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in traffic history file: {e}")
            return {}
    else:
        logger.info("Traffic history file does not exist. Initializing with empty dict.")
        return {}
    

def save_traffic_history(history):
    with open(TRAFFIC_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def update_traffic_history(current_data):
    history = load_traffic_history()
    timestamp = datetime.utcnow().isoformat()
    history[timestamp] = current_data

    # Keep history for the last N entries
    max_entries = 5  # Adjust as needed
    sorted_history = dict(sorted(history.items(), reverse=True)[:max_entries])
    save_traffic_history(sorted_history)
    return sorted_history