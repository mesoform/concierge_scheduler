"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
import os
from unittest import TestLoader, TestCase, TextTestRunner
from ast import literal_eval
import concierge_scheduler.concierge_zabbix

_TEST_DATA_DIR = './'
_TEST_TRIG_ACT_FILE = 'test_trigger_actions.json'
_TEST_REG_ACT_FILE = 'test_reg_actions.json'
_TEST_EXPECTED_ACTIONS_FILE = 'test_full_actions_list'


class ZabbixAdminImport(TestCase):
    # setUp ensures that for each test we start with a fresh instance of the
    # object rather than reusing the same object as a previous test. Which may
    # have had its state modified.
    def setUp(self):
        concierge_scheduler.concierge_zabbix._TRIGGER_ACTIONS_FILE =\
            _TEST_TRIG_ACT_FILE
        concierge_scheduler.concierge_zabbix._REG_ACTIONS_FILE = \
            _TEST_REG_ACT_FILE
        self.zbx_admin = concierge_scheduler.concierge_zabbix.\
            ZabbixAdmin(object, _TEST_DATA_DIR)

    def test_actions_list(self):
        self.zbx_admin._update_actions_list()
        with open(os.path.join(
                _TEST_DATA_DIR,
                _TEST_EXPECTED_ACTIONS_FILE)) as f:
            expected_actions = [list(literal_eval(line)) for line in f]
            self.assertListEqual(expected_actions, self.zbx_admin.actions)


class FullTest(TestCase):
    """
    class that performs full suite of tests
    """


def suite():
    return TestLoader().loadTestsFromTestCase(FullTest)


if __name__ == '__main__':
    suite = TestLoader().loadTestsFromTestCase(ZabbixAdminImport)
    TextTestRunner(verbosity=2).run(suite)
