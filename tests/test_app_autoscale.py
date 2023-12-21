import unittest
import sys
import pathlib
parent_dir = str(pathlib.Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)
import modules.app_autoscale as app_autoscale
import modules.settings as settings
from modules.logger import get_logger

configs =  settings.settings(sys_config=parent_dir + '/etc/system_settings.file', user_config=parent_dir + '/etc/user_settings.file')
log =  get_logger(logger_name=__name__, settings=configs)
configs['log'] = log


class TestAppAutoScale(unittest.TestCase):
    
    def test_scale_app_replicas_min(self):
        min_replicas = configs.get('min_replicas')
        replicas = app_autoscale.scale_app_replicas(current_replica_count=min_replicas-1, current_cpu_utilization=0.40, settings=configs, dry_run=False)
        self.assertEqual(replicas, min_replicas)
        
    def test_scale_app_replicas_max(self):
        max_replicas = configs.get('max_replicas')
        replicas = app_autoscale.scale_app_replicas(current_replica_count=max_replicas, current_cpu_utilization=0.80, settings=configs, dry_run=False)
        self.assertEqual(replicas, max_replicas)
        
        
        
if __name__ == '__main__':
    unittest.main()
        
        
        
