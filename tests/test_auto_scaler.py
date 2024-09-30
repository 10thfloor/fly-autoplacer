import unittest
from unittest.mock import patch
from automation.auto_placer import place_machines, DRY_RUN

class TestAutoScaler(unittest.TestCase):
    @patch('subprocess.run')
    def test_place_machines_dry_run(self, mock_run):
        regions_to_deploy = ['CD']
        regions_to_remove = ['IAD']
        place_machines(regions_to_deploy, regions_to_remove)
        # Ensure subprocess.run was not called due to DRY_RUN = True
        if DRY_RUN:
            mock_run.assert_not_called()
        else:
            mock_run.assert_called()

if __name__ == '__main__':
    unittest.main()