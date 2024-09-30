import logging
import os

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def log_action(action, region, dry_run):
    if dry_run:
        logging.info(f"[DRY RUN] Would {action} in region: {region}")
    else:
        logging.info(f"{action.capitalize()} in region: {region}")

def get_logger(name):
    return logging.getLogger(name)