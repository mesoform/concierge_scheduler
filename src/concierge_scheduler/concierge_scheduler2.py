import os
import sys
import logging
import argparse
from pyzabbix import ZabbixAPI
from concierge_docker import DockerAdmin
from concierge_zabbix import ZabbixAdmin

# DOCKER_URL = "tcp://us-east-1.docker.joyent.com:2376"


def arg_parser():
    """
    parses arguments passed on command line when running program
    :return: list of arguments
    """

    def add_container_parser(parser):
        # capture arguments for managing containers
        c_parser = parser.add_parser(
            'container',
            help='commands to control our container management system')
        c_parser.add_argument(
            '-u', '--datacenter-url',
            help='(required) url endpoint of the Docker '
                 ' API for the services to be managed',
            required=True)
        c_parser.add_argument(
            '-p', '--project',
            help='(required) project namespace of services to be managed',
            required=True)
        return c_parser.add_subparsers(
            description='action we want to perform')

    def add_event_parser(parser):
        e_parser = parser.add_parser(
            'event', help='commands to control our event management system',
            formatter_class=argparse.RawTextHelpFormatter)
        return e_parser.add_argument(
            'command', choices=('backup_config', 'restore_config'),
            help='\nbackup_config:\n'
                 'backup the event managers configuration.\n'
                 'restore_config:\n'
                 'restore the event managers configuration.')

    def add_container_list_parser(parser):
        return parser.add_parser(
            'list', help='show the IDs of all container in a given project')

    def add_container_scale_parser(parser):
        cs_parser = parser.add_parser(
            'scale', help='scale up or down our service')
        cs_parser.add_argument(
            '-n', '--service-name',
            help='(required) name of the service we want to scale',
            required=True)
        cs_parser.add_argument(
            '-c', '--current-scale', type=int, default=None,
            help='(required) the number of containers currently running in the'
                 ' environment',
            required=True)
        cs_parser.add_argument(
            '-s', '--scale-delta', type=int, default=None,
            help='(required) the number of containers we want to add or remove',
            required=True)
        return cs_parser.add_subparsers(
            help='horizontally scale up or down the number of containers; or'
                 ' vertically scale the memory of the containers',
            dest='command')

    def add_container_scale_command_parser(parser):
        up_parser = parser.add_parser(
            'up', help='horizontally scale service by adding containers.')
        up_parser.set_defaults(command='scale_up')
        down_parser = parser.add_parser(
            'down', help='horizontally scale service by removing containers.')
        down_parser.set_defaults(command='scale_down')
        mem_parser = parser.add_parser(
            'memory', help='vertically scale the amount of memory for our '
                           'service. (EXPERIMENTAL)')
        mem_parser.set_defaults(command='scale_memory')

    root_parser = argparse.ArgumentParser(
        description='Script to construct and automate common actions on an'
                    ' event management system maintaining Docker containers')

    mgmt_parser = \
        root_parser.add_subparsers(help='management system to control')

    # capture arguments for managing containers
    container_parser = add_container_parser(mgmt_parser)
    add_container_list_parser(container_parser)
    scale_parser = add_container_scale_parser(container_parser)
    add_container_scale_command_parser(scale_parser)
    # capture arguments for managing our event manager
    add_event_parser(mgmt_parser)

    return root_parser.parse_args()


# logging
def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    stream = logging.StreamHandler()
    fmt = logging.Formatter('%(asctime)s [%(threadName)s] '
                            '[%(name)s] %(levelname)s: %(message)s')
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    return logger


__LOG = get_logger(__name__)


def __info(message, *args):
    __LOG.log(logging.INFO, message.format(*args))


def __log_error_and_fail(message, *args):
    __LOG.log(logging.ERROR, message.format(*args))
    sys.exit(-1)


def initiate_zabbix_client(zbx_host, zbx_user, zbx_password):
    zbx_url = 'http://{}'.format(zbx_host)
    __info('Logging in using url={} ...', zbx_url)
    return ZabbixAPI(zbx_url).login(user=zbx_user, password=zbx_password)


# main
if __name__ == '__main__':
    # Capture arguments passed to module
    cmd_args = arg_parser()
    config_dir = os.getenv('ZBX_CONFIG_DIR') or os.path.abspath(__file__)
    zbx_client = initiate_zabbix_client(
        os.getenv('ZBX_API_HOST'),
        os.getenv('ZBX_USER'),
        os.getenv('ZBX_PASS'))
    __info('Connected to Zabbix API Version {}', zbx_client.api_version())

    if cmd_args.command in ['scale_up', 'scale_down', 'list']:
        DockerAdmin(zbx_client, cmd_args.datacenter_url, cmd_args.project,
                    cmd_args.service_name, cmd_args.current_scale,
                    cmd_args.scale_delta).run(cmd_args.command)
    elif cmd_args.command in ['backup_config', 'restore_config']:
        ZabbixAdmin(zbx_client, config_dir).run(cmd_args.command)
    else:
        __log_error_and_fail('Unknown action {}', cmd_args.command)
