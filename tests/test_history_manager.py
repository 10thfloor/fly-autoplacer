import unittest
from unittest.mock import mock_open, patch
from utils.history_manager import load_traffic_history, save_traffic_history, update_traffic_history
import json
from datetime import datetime

class TestHistoryManager(unittest.TestCase):
    def test_load_traffic_history_with_data(self):
        mock_data = json.dumps({
            "2024-10-01T08:00:00Z": {
                "cdg": 9,
                "ams": 15
            }
        })
        with patch('builtins.open', mock_open(read_data=mock_data)) as mocked_file:
            with patch('os.path.exists') as mocked_exists:
                mocked_exists.return_value = True
                history = load_traffic_history()
                self.assertIn("2024-10-01T08:00:00Z", history)

    def test_load_traffic_history_no_file(self):
        with patch('os.path.exists') as mocked_exists:
            mocked_exists.return_value = False
            history = load_traffic_history()
            self.assertEqual(history, {})

    def test_save_traffic_history(self):
        history_to_save = {'2024-10-01T08:30:00Z': {'iad': 100, 'cdg': 50}}
        with patch('builtins.open', mock_open()) as mocked_file:
            with patch('os.makedirs') as mocked_makedirs:
                save_traffic_history(history_to_save)
                mocked_file.assert_called_with('data/traffic_history.json', 'w')
                file_handle = mocked_file()
                file_handle.write.assert_called_once_with(json.dumps(history_to_save, indent=2))

    @patch('utils.history_manager.load_traffic_history')
    @patch('utils.history_manager.save_traffic_history')
    def test_update_traffic_history(self, mock_save_history, mock_load_history):
        # Mock existing history
        mock_load_history.return_value = {
            "2024-10-01T08:00:00Z": {
                "cdg": 9,
                "ams": 15
            }
        }
        current_data = {'iad': 100, 'cdg': 50}
        updated_history = update_traffic_history(current_data)

        # Should have two entries in history now
        self.assertEqual(len(updated_history), 2)
        latest_timestamp = max(updated_history.keys())
        self.assertEqual(updated_history[latest_timestamp], current_data)
        mock_save_history.assert_called_once_with(updated_history)

if __name__ == '__main__':
    unittest.main()
