import unittest
from unittest.mock import mock_open, patch
from utils.state_manager import load_deployment_state, save_deployment_state
import json

class TestStateManager(unittest.TestCase):
    def test_load_deployment_state_dict_format(self):
        # Mock data in new dict format with timestamps
        mock_data = json.dumps({'iad': '2024-10-01T08:30:00Z', 'cdg': None})
        with patch('builtins.open', mock_open(read_data=mock_data)) as mocked_file:
            with patch('os.path.exists') as mocked_exists:
                mocked_exists.return_value = True
                state = load_deployment_state()
                self.assertEqual(state, {'iad': '2024-10-01T08:30:00Z', 'cdg': None})

    def test_load_deployment_state_list_format(self):
        # Mock data in old list format
        mock_data = json.dumps(['iad', 'cdg'])
        with patch('builtins.open', mock_open(read_data=mock_data)) as mocked_file:
            with patch('os.path.exists') as mocked_exists:
                mocked_exists.return_value = True
                state = load_deployment_state()
                self.assertEqual(state, {'iad': None, 'cdg': None})

    def test_load_deployment_state_no_file(self):
        with patch('os.path.exists') as mocked_exists:
            mocked_exists.return_value = False
            state = load_deployment_state()
            self.assertEqual(state, {})

    def test_save_deployment_state(self):
        test_state = {'iad': '2024-10-01T08:30:00Z', 'cdg': None}
        with patch('builtins.open', mock_open()) as mocked_file:
            with patch('os.makedirs') as mocked_makedirs:
                save_deployment_state(test_state)
                mocked_file.assert_called_with('data/deployment_state.json', 'w')
                file_handle = mocked_file()
                file_handle.write.assert_called_once_with(json.dumps(test_state, indent=2))

if __name__ == '__main__':
    unittest.main()