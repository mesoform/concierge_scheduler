#!/usr/bin/env python
"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
import os
import sys
import logging
import argparse
import urllib3
from pyzabbix import ZabbixAPI
from concierge_docker import DockerAdmin
from concierge_zabbix import ZabbixAdmin
from concierge_gcs import GCSBackup
__DEFAULT_CONFIG_DIR = os.getenv('ZBX_CONFIG_DIR') or os.path.abspath(__file__)
STORAGE_LOCATION = os.getenv('STORAGE_LOCATION', '')
STORAGE_FOLDER = os.getenv('STORAGE_FOLDER', '')
GCP_CREDENTIAL_FILE = os.getenv('GCP_CREDENTIAL_FILE') or '~/.config/gcloud/application_default_credentials.json'
AWS_CREDENTIAL_FILE = os.getenv('AWS_CREDENTIAL_FILE') or '~/.aws/credentials'
ZBX_API_HOST = os.getenv('ZBX_API_HOST', 'zabbix-web')
ZBX_API_USER = os.getenv('ZBX_API_USER', 'Admin')
ZBX_API_PASS = os.getenv('ZBX_API_PASS', 'zabbix')
ZBX_TLS_VERIFY = os.getenv('ZBX_TLS_VERIFY', 'True')
ZBX_FORCE_TEMPLATES = os.getenv('ZBX_FORCE_TEMPLATES', 'False')
zbx_client = object
zbx_admin = object

container_administrators = {
    'docker': DockerAdmin
}
event_administrators = {
    'zabbix': ZabbixAdmin
}
cloud_administrators = {
    'gcp': GCSBackup
}
credential_files = {
    'gcp': GCP_CREDENTIAL_FILE,
    'aws': AWS_CREDENTIAL_FILE
}


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
            description='action we want to perform',
            dest='command')

    def add_event_parser(parser):
        e_parser = parser.add_parser(
            'event', help='commands to control our event management system',
            formatter_class=argparse.RawTextHelpFormatter)
        e_parser.add_argument(
            '--config-dir',
            help='directory containing the configuration for the event management system',
            default=__DEFAULT_CONFIG_DIR
        )
        e_parser.add_argument('--force-templates', action='store_true', default=ZBX_FORCE_TEMPLATES,
                              help='Forces template configuration to delete all current existing templates')
        return e_parser.add_argument(
            'command', choices=('backup_config', 'restore_config',
                                'get_simple_id_map'),
            help='\nbackup_config:\n'
                 'backup the event managers configuration.\n'
                 'restore_config:\n'
                 'restore the event managers configuration.\n'
                 'get_simple_id_map:\n'
                 'create a simple JSON file of the IDs to names of hostgroups'
                 ' and templates')

    def add_cloud_parser(parser):
        cl_parser = parser.add_parser(
            'cloud', help='commands to control cloud functionality')
        cl_parser.add_argument(
            '--storage-location',
            help='Remote storage location name/url to store configuration files in',
            default=STORAGE_LOCATION
        )
        cl_parser.add_argument(
            '--config-dir',
            help='directory containing the configuration for the event management system',
            default=__DEFAULT_CONFIG_DIR
        )
        cl_parser.add_argument(
            '--storage-folder',
            help='Folder in storage location to upload files to',
            default=STORAGE_FOLDER
        )
        return cl_parser.add_argument(
            'command', choices='upload',
            help='\nupload:\n'
                 'upload config files to cloud storage\n'
        )

    def add_container_list_parser(parser):
        ls_parser = parser.add_parser(
            'list', help='show the IDs of all container in a given project')
        ls_parser.add_argument(
            '-n', '--service-name',
            help='(required) name of the service we want to scale',
            default=None)

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
            'scale_up', aliases=['up'],
            help='horizontally scale service by adding containers.')
        up_parser.set_defaults(command='scale_up')
        down_parser = parser.add_parser(
            'scale_down', aliases=['down'],
            help='horizontally scale service by removing containers.')
        down_parser.set_defaults(command='scale_down')
        mem_parser = parser.add_parser(
            'memory', help='vertically scale the amount of memory for our '
                           'service. (EXPERIMENTAL)')
        mem_parser.set_defaults(command='scale_memory')

    root_parser = argparse.ArgumentParser(
        description='Script to construct and automate common actions on an'
                    ' event management system maintaining containers')
    root_parser.add_argument(
        '--event-engine',
        help='event management engine used for managing containers.'
             ' DEFAULT=zabbix',
        default='zabbix')
    root_parser.add_argument(
        '--container-engine',
        help='container engine used for managing containers. DEFAULT=docker',
        default='docker')
    root_parser.add_argument(
        '--cloud-engine',
        help='cloud engine used for cloud functionality. DEFAULT=gcp',
        default='gcp'
    )

    mgmt_parser = \
        root_parser.add_subparsers(help='management system to control')

    # capture arguments for managing containers
    container_parser = add_container_parser(mgmt_parser)
    add_container_list_parser(container_parser)
    scale_parser = add_container_scale_parser(container_parser)
    add_container_scale_command_parser(scale_parser)
    # capture arguments for managing our event manager
    add_event_parser(mgmt_parser)
    # capture arguments for managing cloud
    add_cloud_parser(mgmt_parser)

    return root_parser.parse_args()


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


def __warn(message, *args):
    __LOG.log(logging.WARN, message.format(*args))


def __log_error_and_fail(message, *args):
    __LOG.log(logging.ERROR, message.format(*args))
    sys.exit(-1)


def process_password():
    password = ZBX_API_PASS
    if os.path.isfile(ZBX_API_PASS):
        with open(ZBX_API_PASS, 'r') as f:
            password = f.readline().strip()
    return password


def initiate_zabbix_client():
    """
    create an instance of Zabbix API client
    :return: object
    """
    __info('Logging in using url={} ...', ZBX_API_HOST)
    tls_verify = ZBX_TLS_VERIFY.lower() != 'false'
    detect_version = True
    if not tls_verify:
        __warn('TLS Verification disabled, HTTPS requests to host are unverified')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        if ZBX_API_HOST.startswith('https'):
            detect_version = False
    client = ZabbixAPI(ZBX_API_HOST, detect_version=detect_version)
    client.session.verify = tls_verify
    client.login(user=ZBX_API_USER, password=process_password())
    __info('Connected to Zabbix API Version {}', client.api_version())
    return client


if __name__ == '__main__':
    # Capture arguments passed to module
    cmd_args = arg_parser()
    container_admin = container_administrators[cmd_args.container_engine]
    if cmd_args.event_engine == 'zabbix' and cmd_args.command != 'upload':
        zbx_client = initiate_zabbix_client()
    event_admin = event_administrators[cmd_args.event_engine]

    if cmd_args.command in ['scale_up', 'scale_down']:
        container_admin(zbx_client, cmd_args.datacenter_url, cmd_args.project,
                        cmd_args.service_name, cmd_args.current_scale,
                        cmd_args.scale_delta).run(cmd_args.command)
    elif cmd_args.command in ['list']:
        container_admin(zbx_client, cmd_args.datacenter_url,
                        cmd_args.project,
                        cmd_args.service_name).run(cmd_args.command)
    elif cmd_args.command in ['backup_config', 'restore_config',
                              'get_simple_id_map']:
        force_templates = False if ZBX_FORCE_TEMPLATES.upper() == "FALSE" else cmd_args.force_templates
        event_admin(zbx_client, cmd_args.config_dir, cmd_args.force_templates).run(cmd_args.command)
    elif cmd_args.command in ['upload']:
        __info('Connecting to {}...', cmd_args.cloud_engine)
        cloud_admin = cloud_administrators[cmd_args.cloud_engine](
            credential_files[cmd_args.cloud_engine], cmd_args.config_dir, cmd_args.storage_location)
        __info('Authenticated with {}', cmd_args.cloud_engine)
        upload_list = cloud_admin.assemble_upload_list()
        __info('Uploading {} to {} ...', upload_list, cmd_args.storage_location)
        cloud_admin.upload(upload_list=upload_list, folder=cmd_args.storage_folder)
        __info('Finished uploading files.')

    else:
        __log_error_and_fail('Unknown action {}', cmd_args.command)
