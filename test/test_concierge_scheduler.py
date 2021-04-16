"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from unittest import TestLoader, TestCase, TextTestRunner
from concierge_scheduler import concierge_scheduler
from concierge_scheduler.concierge_scheduler import arg_parser
from mock import patch


class ConciergeSchedulerArgs(TestCase):
    # setUp ensures that for each test we start with a fresh instance of the
    # object rather than reusing the same object as a previous test. Which may
    # have had its state modified.
    def setUp(self):
        self.parser = arg_parser()

    @patch('concierge_scheduler.concierge_scheduler.ZabbixAPI')
    def test_initiate_zabbix_client(self, mock_zbx_api):
        mock_zbx_api.return_value.ok = True
        client = concierge_scheduler.initiate_zabbix_client()
        self.assertIsNotNone(client, msg='CLIENT: {}'.format(client))

    def test_scale_up_command(self):
        parsed = self.parser.parse_args(
            'container -u tcp://us-east-1.docker.joyent.com:2376 -p'
            ' apachefwdproxy scale -n consul -c 1 -s 1 up'.split())
        self.assertEqual(parsed.command, 'scale_up')


class FullTest(TestCase):
    """
    class that performs full suite of tests
    """


def suite():
    return TestLoader().loadTestsFromTestCase(FullTest)


if __name__ == '__main__':
    suite = TestLoader().loadTestsFromTestCase(ConciergeSchedulerArgs)
    TextTestRunner(verbosity=2).run(suite)
