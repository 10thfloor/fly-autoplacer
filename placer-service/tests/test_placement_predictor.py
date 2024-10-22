import unittest
from unittest.mock import Mock
from prediction.placement_predictor import PlacementPredictor
from datetime import datetime, timezone

class TestPlacementPredictor(unittest.TestCase):
    def test_adaptive_thresholds_with_volatility(self):
        config = {'traffic_threshold': 100, 'deployment_threshold': 50}
        predictor = PlacementPredictor(config)
        
        # Simulate some traffic patterns
        averages = {'long': 75}
        
        # First call should use basic thresholds
        action = predictor.predict_placement_actions('test-region', averages)
        assert action is None  # Should be in the middle range
        
        # Simulate volatile traffic
        for traffic in [60, 90, 40, 100, 50]:
            averages = {'long': traffic}
            predictor.predict_placement_actions('test-region', averages)
        
        # Check that thresholds adapted to volatility
        final_thresholds = predictor.calculate_adaptive_thresholds(
            averages, config['traffic_threshold'], config['deployment_threshold']
        )
        assert final_thresholds[0] > config['traffic_threshold']  # Higher traffic threshold due to volatility

if __name__ == '__main__':
    unittest.main()
