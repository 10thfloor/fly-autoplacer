import unittest
from unittest.mock import patch
from automation.auto_placer import update_placements, DRY_RUN
from datetime import datetime

class TestAutoPlacer(unittest.TestCase):
    @patch('automation.auto_placer.subprocess.run')
    @patch('automation.auto_placer.save_deployment_state')
    @patch('automation.auto_placer.load_deployment_state')
    def test_update_placements_dry_run(self, mock_load_state, mock_save_state, mock_subprocess_run):
        regions_to_deploy = ['cdg']
        regions_to_remove = ['iad']

        # Mock current time
        now = datetime.now(timezone.utc)

        # Mock deployment state with timestamps
        mock_load_state.return_value = {'iad': now.isoformat()}

        # Run the update_placements function
        update_placements(regions_to_deploy, regions_to_remove)

        # Since DRY_RUN is True, subprocess.run should not be called
        if DRY_RUN:
            mock_subprocess_run.assert_not_called()
        else:
            mock_subprocess_run.assert_called()

        # Verify that deployment state was updated correctly
        expected_state = {'cdg': now.isoformat()}  # 'iad' removed, 'cdg' added
        mock_save_state.assert_called_with(expected_state)

if __name__ == '__main__':
    unittest.main()