"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from unittest import TestLoader, TestCase, TextTestRunner
from concierge_scheduler.concierge_scheduler import arg_parser


class ConciergeSchedulerArgs(TestCase):
    # setUp ensures that for each test we start with a fresh instance of the
    # object rather than reusing the same object as a previous test. Which may
    # have had its state modified.
    def setUp(self):
        self.parser = arg_parser()

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
