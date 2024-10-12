import random
from datetime import datetime, timedelta
import os
import json
from collections import defaultdict
from utils.state_manager import load_deployment_state
from utils.config_loader import Config
from utils.metrics_fetcher import MetricsFetcher
import logging

logger = logging.getLogger(__name__)

TRAFFIC_LEVEL_WEIGHTS_DEPLOYED = [0.4, 0.4, 0.1, 0.1]
TRAFFIC_LEVEL_WEIGHTS_NON_DEPLOYED = [0.1, 0.1, 0.3, 0.5]
MAX_HISTORY_ENTRIES = 5

def collect_region_traffic():
    config = Config.get_config()
    metrics_fetcher = MetricsFetcher()

    app_name = metrics_fetcher.get_app_name()
    logger.info(f"Collecting {'mock' if config['dry_run'] else 'real'} traffic data for app: {app_name}")
    
    try:
        traffic_data = metrics_fetcher.fetch_region_traffic()
        logger.info(f"Successfully collected traffic data for {len(traffic_data)} regions of app: {app_name}")
        logger.debug(f"Collected traffic data for app {app_name}: {traffic_data}")
        return traffic_data
    except Exception as e:
        logger.error(f"Error collecting region traffic data for app {app_name}: {str(e)}")
        raise
