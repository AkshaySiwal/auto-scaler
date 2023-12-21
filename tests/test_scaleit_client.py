import unittest
import sys
import pathlib
from unittest.mock import patch, Mock
parent_dir = str(pathlib.Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)
import modules.scaleit_client as scaleit_client
import modules.settings as settings
from modules.logger import get_logger

configs =  settings.settings(sys_config=parent_dir + '/etc/system_settings.file', user_config=parent_dir + '/etc/user_settings.file')
log =  get_logger(logger_name=__name__, settings=configs)
configs['log'] = log


class TestScaleitClient(unittest.TestCase):
    
    @patch('requests.get')
    def test_find_current_cpu_stats(self, mocked_get):
        mocked_response = Mock()
        mocked_response.status_code = 200
        mocked_response.json.return_value = { "cpu": { "highPriority": 0.74 }, "replicas": 10 }
        
        mocked_get.return_value = mocked_response
        cpu , replicas  = scaleit_client.find_current_cpu_stats(configs)
        self.assertEqual(cpu, 0.74)
        self.assertEqual(replicas, 10)
        
    @patch('requests.put')
    def test_update_app_replicas(self, mocked_put):
        mocked_response = Mock()
        mocked_response.status_code = 204
        
        mocked_put.return_value = mocked_response
        done = scaleit_client.update_app_replicas(replicas=2, settings=configs)
        self.assertEqual(done, True)
        
        
if __name__ == '__main__':
    unittest.main()
        
        
        