import unittest
from unittest.mock import patch
from prediction.placement_predictor import predict_placement_actions

class TestPlacementPredictor(unittest.TestCase):
    @patch('prediction.placement_predictor.config', {
        'traffic_threshold': 50,
        'deployment_threshold': 30,
        'allowed_regions': ['ams', 'fra', 'lhr'],
        'excluded_regions': ['sin', 'nrt'],
        'always_running_regions': ['iad', 'cdg']
    })
    def test_predict_placement_actions(self):
        history = {
            '2024-10-01T12:00:00Z': {'ams': 60, 'lhr': 25, 'sin': 70},
            '2024-10-01T12:05:00Z': {'ams': 55, 'lhr': 28, 'sin': 75}
        }
        current_regions = ['ams', 'lhr']

        # Expected behavior:
        # - 'ams' remains deployed (above deployment_threshold)
        # - 'lhr' remains deployed (above deployment_threshold)
        # - 'sin' not deployed (in excluded_regions)
        # - 'iad' and 'cdg' deployed (always_running_regions)
        regions_to_deploy, regions_to_remove = predict_placement_actions(history, current_regions)

        self.assertIn('iad', regions_to_deploy)
        self.assertIn('cdg', regions_to_deploy)
        self.assertNotIn('sin', regions_to_deploy)
        self.assertNotIn('ams', regions_to_remove)
        self.assertNotIn('lhr', regions_to_remove)

    @patch('prediction.placement_predictor.config', {
        'traffic_threshold': 50,
        'deployment_threshold': 30,
        'allowed_regions': ['ams', 'fra', 'lhr'],
        'excluded_regions': ['sin', 'nrt'],
        'always_running_regions': []
    })
    def test_allowed_and_excluded_regions(self):
        history = {
            '2024-10-01T12:00:00Z': {'fra': 60, 'nrt': 70, 'sin': 80},
            '2024-10-01T12:05:00Z': {'fra': 65, 'nrt': 75, 'sin': 85}
        }
        current_regions = []

        # Expected behavior:
        # - 'fra' deployed (in allowed_regions and above threshold)
        # - 'nrt' and 'sin' not deployed (in excluded_regions)
        # - 'fra' is in regions_to_deploy
        regions_to_deploy, regions_to_remove = predict_placement_actions(history, current_regions)

        self.assertIn('fra', regions_to_deploy)
        self.assertNotIn('nrt', regions_to_deploy)
        self.assertNotIn('sin', regions_to_deploy)
        self.assertEqual(len(regions_to_remove), 0)

    @patch('prediction.placement_predictor.config', {
        'traffic_threshold': 50,
        'deployment_threshold': 30,
        'allowed_regions': [],
        'excluded_regions': [],
        'always_running_regions': ['ams']
    })
    def test_always_running_regions(self):
        history = {}
        current_regions = []

        # Expected behavior:
        # - 'ams' deployed (always_running_region)
        # - No regions to remove
        regions_to_deploy, regions_to_remove = predict_placement_actions(history, current_regions)

        self.assertIn('ams', regions_to_deploy)
        self.assertEqual(len(regions_to_remove), 0)

if __name__ == '__main__':
    unittest.main()