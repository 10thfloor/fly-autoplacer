import unittest
from prediction.placement_predictor import predict_scaling_actions

class TestTrafficPredictor(unittest.TestCase):
    def test_predict_scaling_actions(self):
        history = {
            '2023-10-01T12:00:00Z': {'CD': 120, 'IAD': 40},
            '2023-10-01T12:05:00Z': {'CD': 130, 'IAD': 35},
            # Add more data points as needed
        }
        regions_to_deploy, regions_to_remove = predict_scaling_actions(history)
        self.assertIn('CD', regions_to_deploy)
        self.assertIn('IAD', regions_to_remove)

if __name__ == '__main__':
    unittest.main()