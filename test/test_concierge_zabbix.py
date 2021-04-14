"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
import json
import logging
import os
from unittest import TestLoader, TestCase, TextTestRunner
from ast import literal_eval
from unittest.mock import patch
import concierge_scheduler.concierge_zabbix
import concierge_scheduler.concierge_docker

_TEST_DATA_DIR = './'
_TEST_TRIG_ACT_FILE = 'test_trigger_actions.json'
_TEST_REG_ACT_FILE = 'test_reg_actions.json'
_TEST_EXPECTED_ACTIONS_FILE = 'test_full_actions_list'
_TEST_FORCE_TEMPLATE = False


class ZabbixAdminImport(TestCase):
    # setUp ensures that for each test we start with a fresh instance of the
    # object rather than reusing the same object as a previous test. Which may
    # have had its state modified.
    def setUp(self):
        concierge_scheduler.concierge_zabbix._TRIGGER_ACTIONS_FILE = \
            _TEST_TRIG_ACT_FILE
        concierge_scheduler.concierge_zabbix._REG_ACTIONS_FILE = \
            _TEST_REG_ACT_FILE
        self.zbx_admin = concierge_scheduler.concierge_zabbix. \
            ZabbixAdmin(object, _TEST_DATA_DIR, _TEST_FORCE_TEMPLATE)

    def test_actions_list(self):
        with open(os.path.join(
                _TEST_DATA_DIR,
                _TEST_EXPECTED_ACTIONS_FILE)) as f:
            expected_actions = [list(literal_eval(line)) for line in f]
            self.assertListEqual(expected_actions, self.zbx_admin.actions)


# @patch('concierge_scheduler.concierge_scheduler.ZabbixAPI')
class FullTest(TestCase):
    """
    class that performs full suite of tests
    """
    def setUp(self):
        patcher = patch('concierge_scheduler.concierge_scheduler.ZabbixAPI', return_value=True)
        self.mock_zbx_client = patcher.start()
        self.addCleanup(patcher.stop)
        concierge_scheduler.concierge_zabbix._TRIGGER_ACTIONS_FILE = \
            _TEST_TRIG_ACT_FILE
        concierge_scheduler.concierge_zabbix._REG_ACTIONS_FILE = \
            _TEST_REG_ACT_FILE
        self.zbx_admin = concierge_scheduler.concierge_zabbix. \
            ZabbixAdmin(self.mock_zbx_client, _TEST_DATA_DIR, _TEST_FORCE_TEMPLATE)

    def test_remove_keys(self):
        data = {'example': 'delete', 'key': 'value', 'example2': 'delete'}
        keys_to_remove = ['example', 'example2']
        returned_val = self.zbx_admin._remove_keys(data, keys_to_remove)
        log = logging.getLogger("ZabbixAdminImport.test_remove_keys")
        log.debug("this = %s", type(returned_val))
        self.assertDictEqual(self.zbx_admin._remove_keys(data, keys_to_remove), {'key': 'value'})

    def test_update_ids(self):
        """
        Tests if a autoregistration action is correctly updated if the templateid the item was imported from
        does not match the templateid in the destination server.
        If id does not match it should be updated to have the template id in the server
        :return:
        """
        self.zbx_admin.original_ids['templates'] = [{'templateid': '10108', 'host': "test"}]
        self.zbx_admin.original_ids['hostgroups'] = [{'groupid': '8', 'name': "first"},
                                                     {'groupid': '10', 'name': "second"},
                                                     {'groupid': '11', 'name': "third"}]
        self.zbx_admin.dest_ids['templates'] = [{'templateid': '10108', 'host': "something_else"},
                                                {'templateid': '10000', 'host': "test"}]
        self.zbx_admin.dest_ids['hostgroups'] = self.zbx_admin.original_ids['hostgroups'].copy()

        with open("./test_updated_id_reg_action.json") as expected_file:
            expected = json.load(expected_file)
        with open("./test_reg_actions.json") as file:
            reg_action = json.load(file)[0]
            returned_action = self.zbx_admin._update_ids(reg_action)
        self.assertDictEqual(expected, returned_action)

    def test_get_data(self):
        results = self.zbx_admin._get_data('test')
        self.assertIsNotNone(results)


def suite():
    return TestLoader().loadTestsFromTestCase(FullTest)


if __name__ == '__main__':
    suite = TestLoader().loadTestsFromTestCase(ZabbixAdminImport)
    TextTestRunner(verbosity=2).run(suite)
