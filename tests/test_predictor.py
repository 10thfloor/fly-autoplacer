import unittest
from prediction.placement_predictor import predict_placement_actions

class TestTrafficPredictor(unittest.TestCase):
    def test_always_running_regions(self):
        history = {}
        current_regions = []
        ALWAYS_RUNNING_REGIONS = ['iad', 'cdg']
        
        regions_to_deploy, regions_to_remove = predict_placement_actions(history, current_regions)
        
        self.assertIn('iad', regions_to_deploy)
        self.assertIn('cdg', regions_to_deploy)
        self.assertEqual(len(regions_to_remove), 0)
    
    def test_conflicts_with_excluded_regions(self):
        history = {}
        current_regions = []
        EXCLUDED_REGIONS = ['cdg']
        ALWAYS_RUNNING_REGIONS = ['iad', 'cdg']
        
        regions_to_deploy, regions_to_remove = predict_placement_actions(history, current_regions)
        
        self.assertIn('iad', regions_to_deploy)
        self.assertNotIn('cdg', regions_to_deploy)  # Excluded region should not be deployed
        self.assertEqual(len(regions_to_remove), 0)

if __name__ == '__main__':
    unittest.main()