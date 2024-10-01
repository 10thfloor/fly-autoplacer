import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from automation.auto_placer import update_placements

class TestCooldownPeriod(unittest.TestCase):
    @patch('automation.auto_placer.load_deployment_state')
    @patch('automation.auto_placer.save_deployment_state')
    @patch('automation.auto_placer.subprocess.run')
    def test_deploy_within_cooldown(self, mock_run, mock_save, mock_load):
        # Set up
        now = datetime.utcnow()
        region = 'ams'
        cooldown_period = 300  # 5 minutes
        mock_load.return_value = {region: (now - timedelta(seconds=100)).isoformat()}
        
        # Run
        update_placements([region], [])
        
        # Verify
        mock_run.assert_not_called()
    
    @patch('automation.auto_placer.load_deployment_state')
    @patch('automation.auto_placer.save_deployment_state')
    @patch('automation.auto_placer.subprocess.run')
    def test_deploy_after_cooldown(self, mock_run, mock_save, mock_load):
        # Set up
        now = datetime.utcnow()
        region = 'ams'
        cooldown_period = 300  # 5 minutes
        mock_load.return_value = {region: (now - timedelta(seconds=400)).isoformat()}
        
        # Run
        update_placements([region], [])
        
        # Verify
        mock_run.assert_called()
    
if __name__ == '__main__':
    unittest.main()