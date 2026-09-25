"""Make placement decisions with configured thresholds and temporal smoothing."""

from datetime import datetime, timezone
import math


class PlacementPredictor:
    def __init__(self, config, metrics_client=None):
        self.config = config
        self.metrics_client = metrics_client

    def calculate_adaptive_thresholds(self, region, averages, traffic_threshold, deployment_threshold):
        """Keep configured limits stable so sustained demand can trigger placement.

        Smoothing and the gap between deployment and removal thresholds provide
        hysteresis. Historical baselines are diagnostic data, not a moving upper
        limit that a stable high-traffic region can never cross.
        """
        return traffic_threshold, deployment_threshold

    def predict_placement_actions(self, region, averages):
        if not averages or 'short' not in averages or 'long' not in averages:
            return None
        short = averages['short']
        long = averages['long']
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) or value < 0 for value in (short, long)):
            raise ValueError('Traffic averages must be finite, nonnegative numbers')
        traffic_threshold, deployment_threshold = self.calculate_adaptive_thresholds(
            region, averages, self.config.get('traffic_threshold', 100),
            self.config.get('deployment_threshold', 50))
        action = None
        if short >= traffic_threshold:
            action = 'scale_up'
        elif short <= deployment_threshold and long <= deployment_threshold:
            action = 'scale_down'
        if self.metrics_client:
            self.metrics_client.record_threshold_metrics({
                'region': region,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_traffic': short,
                'long_term_traffic': long,
                'baseline': averages.get('baseline'),
                'traffic_threshold': traffic_threshold,
                'deployment_threshold': deployment_threshold,
                'action': action or 'no_action',
                'threshold_gap': traffic_threshold - deployment_threshold,
                'distance_to_nearest_threshold': min(
                    abs(short - traffic_threshold), abs(short - deployment_threshold)),
            })
        return action
