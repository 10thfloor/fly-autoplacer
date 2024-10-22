import json
from datetime import datetime, timedelta
from collections import defaultdict
import os
import yaml
import logging
from utils.config_loader import Config
from utils.fancy_logger import get_logger
import numpy as np
from datetime import timezone

# Load configuration
config = Config.get_config()

# Set up logging
logger = get_logger(__name__)

# Global constants
traffic_threshold = int(config['traffic_threshold'])
deployment_threshold = int(config['deployment_threshold'])
ALLOWED_REGIONS = config.get('allowed_regions', [])
EXCLUDED_REGIONS = config.get('excluded_regions', [])
ALWAYS_RUNNING_REGIONS = config.get('always_running_regions', [])

TRAFFIC_HISTORY_FILE = 'data/traffic_history.json'

class PlacementPredictor:
    def __init__(self, config, metrics_client=None):  # Make metrics_client optional for now
        self.config = config
        self.metrics_client = metrics_client
        self.threshold_history = {}  # Add this but won't use yet

    # Add new method but keep existing logic for now
    def calculate_adaptive_thresholds(self, region, averages, traffic_threshold, deployment_threshold):
        """Enhanced version with volatility consideration"""
        if not averages or 'long' not in averages:
            return traffic_threshold, deployment_threshold

        # Get current traffic value
        current_traffic = averages['long']
        
        # Store in history for future volatility calculation
        region_history = self.threshold_history.setdefault(region, [])
        region_history.append(current_traffic)
        # Keep last 10 values for history
        self.threshold_history[region] = region_history[-10:]
        
        # Calculate traffic variability
        traffic_values = self.threshold_history[region]
        mean_traffic = np.mean(traffic_values)
        std_traffic = np.std(traffic_values) if len(traffic_values) > 1 else 0
        
        traffic_variability = std_traffic / mean_traffic if mean_traffic > 0 else 0
        volatility_factor = 1 + traffic_variability

        # Calculate thresholds with volatility consideration
        adaptive_traffic_threshold = max(
            traffic_threshold,
            mean_traffic * (1.1 * volatility_factor)
        )
        
        adaptive_deployment_threshold = min(
            deployment_threshold,
            mean_traffic * (0.9 / volatility_factor)
        )

        # Add hysteresis
        hysteresis_gap = (adaptive_traffic_threshold - adaptive_deployment_threshold) * 0.1
        adaptive_deployment_threshold += hysteresis_gap

        return adaptive_traffic_threshold, adaptive_deployment_threshold

    # Modify existing predict_placement_actions to use new method
    def predict_placement_actions(self, region, averages):
        if not averages or 'long' not in averages:
            return None

        traffic_threshold = self.config.get('traffic_threshold', 100)
        deployment_threshold = self.config.get('deployment_threshold', 50)

        adaptive_traffic_threshold, adaptive_deployment_threshold = self.calculate_adaptive_thresholds(
            region,
            averages, 
            traffic_threshold, 
            deployment_threshold
        )

        current_average = averages['long']
        action = None

        if current_average > adaptive_traffic_threshold:
            action = 'scale_up'
        elif current_average < adaptive_deployment_threshold:
            action = 'scale_down'

        # Add metrics tracking if metrics client exists
        if self.metrics_client:
            metrics = {
                "region": region,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "current_traffic": current_average,
                "traffic_threshold": adaptive_traffic_threshold,
                "deployment_threshold": adaptive_deployment_threshold,
                "action": action or 'no_action',
                "threshold_gap": adaptive_traffic_threshold - adaptive_deployment_threshold,
                "distance_to_nearest_threshold": min(
                    abs(current_average - adaptive_traffic_threshold),
                    abs(current_average - adaptive_deployment_threshold)
                )
            }
            self.metrics_client.record_threshold_metrics(metrics)

        return action



