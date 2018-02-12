import os
import sys
import logging
from pyzabbix import ZabbixAPI
from concierge_docker import DockerAdmin
from concierge_zabbix import ZabbixAdmin

ACTION = sys.argv[1] if len(sys.argv) > 1 else 0
SERVICE_NAME = sys.argv[2] if len(sys.argv) > 2 else 0
CURRENT_SCALE = int(sys.argv[3]) if len(sys.argv) > 3 else 0
INCREMENT = int(sys.argv[4]) if len(sys.argv) > 4 else 0


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
    return ZabbixAPI(zbx_url).login(user=zbx_user, password=zbx_password)


# main
if __name__ == '__main__':
    config_dir = os.getenv('ZBX_CONFIG_DIR') or os.path.abspath(__file__)
    zbx_client = initiate_zabbix_client(
        os.getenv('ZBX_API_HOST'),
        os.getenv('ZBX_USER'),
        os.getenv('ZBX_PASS'))

    if ACTION in ['scale_up', 'scale_down', 'service_ps']:
        DockerAdmin(SERVICE_NAME, zbx_client).run(ACTION)
    elif ACTION in ['backup_app', 'import_app']:
        ZabbixAdmin(zbx_client).run(ACTION)
    else:
        __log_error_and_fail('Unknown action {}', ACTION)
