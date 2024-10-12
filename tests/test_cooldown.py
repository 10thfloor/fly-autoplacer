import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from automation.auto_placer import update_placements

class TestCooldownPeriod(unittest.TestCase):
    @patch('automation.auto_placer.load_deployment_state')
    @patch('automation.auto_placer.save_deployment_state')
    @patch('automation.auto_placer.subprocess.run')
    def test_deploy_within_cooldown(self, mock_subprocess_run, mock_save_state, mock_load_state):
        now = datetime.now(timezone.utc)
        region = 'ams'
        # Mock the configuration
        with patch('automation.auto_placer.COOLDOWN_PERIOD', 300):
            # Mock deployment state with recent action
            mock_load_state.return_value = {region: (now - timedelta(seconds=100)).isoformat()}
            regions_to_deploy = [region]
            regions_to_remove = []

            update_placements(regions_to_deploy, regions_to_remove)

            # Should not deploy due to cooldown
            mock_subprocess_run.assert_not_called()
            mock_save_state.assert_not_called()

    @patch('automation.auto_placer.load_deployment_state')
    @patch('automation.auto_placer.save_deployment_state')
    @patch('automation.auto_placer.subprocess.run')
    def test_deploy_after_cooldown(self, mock_subprocess_run, mock_save_state, mock_load_state):
        now = datetime.now(timezone.utc)
        region = 'ams'
        with patch('automation.auto_placer.COOLDOWN_PERIOD', 300):
            # Mock deployment state with action outside cooldown
            mock_load_state.return_value = {region: (now - timedelta(seconds=400)).isoformat()}
            regions_to_deploy = [region]
            regions_to_remove = []

            update_placements(regions_to_deploy, regions_to_remove)

            # Should deploy since cooldown has passed
            mock_subprocess_run.assert_called_once()
            mock_save_state.assert_called_once()

    @patch('automation.auto_placer.load_deployment_state')
    @patch('automation.auto_placer.save_deployment_state')
    @patch('automation.auto_placer.subprocess.run')
    def test_remove_within_cooldown(self, mock_subprocess_run, mock_save_state, mock_load_state):
        now = datetime.now(timezone.utc)
        region = 'iad'
        with patch('automation.auto_placer.COOLDOWN_PERIOD', 300):
            # Mock deployment state with recent action
            mock_load_state.return_value = {region: (now - timedelta(seconds=100)).isoformat()}
            regions_to_deploy = []
            regions_to_remove = [region]

            update_placements(regions_to_deploy, regions_to_remove)

            # Should not remove due to cooldown
            mock_subprocess_run.assert_not_called()
            mock_save_state.assert_not_called()

    @patch('automation.auto_placer.load_deployment_state')
    @patch('automation.auto_placer.save_deployment_state')
    @patch('automation.auto_placer.subprocess.run')
    def test_remove_after_cooldown(self, mock_subprocess_run, mock_save_state, mock_load_state):
        now = datetime.now(timezone.utc)
        region = 'iad'
        with patch('automation.auto_placer.COOLDOWN_PERIOD', 300):
            with patch('automation.auto_placer.ALWAYS_RUNNING_REGIONS', []):
                # Mock deployment state with action outside cooldown
                mock_load_state.return_value = {region: (now - timedelta(seconds=400)).isoformat()}
                regions_to_deploy = []
                regions_to_remove = [region]

                update_placements(regions_to_deploy, regions_to_remove)

                # Should remove since cooldown has passed
                mock_subprocess_run.assert_called_once()
                mock_save_state.assert_called_once()

if __name__ == '__main__':
    unittest.main()