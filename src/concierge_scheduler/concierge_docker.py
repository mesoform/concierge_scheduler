import subprocess
import os
import sys
import logging

DOCKER_CERT_PATH = "/tmp/certs"
DOCKER_CLIENT_TIMEOUT = 800
COMPOSE_HTTP_TIMEOUT = 800


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


class DockerAdmin:
    """

    """

    def __init__(self,
                 zbx_client,
                 data_center,
                 project,
                 service_name,
                 current_scale=None,
                 delta=None):
        """

        :param service_name:
        """
        self.current_scale = current_scale
        self.delta = delta
        self.service_name = service_name
        self.project = project
        self.data_center = data_center
        self.zbx_client = zbx_client
        self.key_file = \
            self.create_pem_file('notes', 'key', self.service_name)
        self.cert_file = \
            self.create_pem_file('poc_1_notes', 'cert', self.service_name)
        self.ca_file = \
            self.create_pem_file('poc_1_notes', 'ca', self.service_name)
        self.service_cmd_template = \
            '/usr/local/bin/docker-compose ' \
            '--tlsverify ' \
            '--tlscert={} ' \
            '--tlscacert={} ' \
            '--tlskey={} ' \
            '--host={} ' \
            '--file /tmp/docker-compose.yml ' \
            '--project-name {} '.format(self.cert_file,
                                        self.key_file,
                                        self.ca_file,
                                        self.data_center,
                                        self.project)

    def create_pem_file(self, inv_property, filename, service_name):
        attribute = self.zbx_client.host.get(output=["host"],
                                             selectInventory=[inv_property],
                                             searchInventory={
                                                 "alias": service_name})
        with open('{}/{}.pem'.format(DOCKER_CERT_PATH, filename),
                  'w') as pem_file:
            pem_file.write(attribute[0]["inventory"][inv_property])
        return pem_file.name

    def del_pem_files(self):
        for f in [self.key_file, self.ca_file, self.cert_file]:
            os.remove(os.path.join(DOCKER_CERT_PATH, f))

    @staticmethod
    def run(action):
        action()

    def scale_service(self, desired_scale):
        subprocess.call(
            str(self.service_cmd_template + 'up -d --scale {}={}'.format(
                self.service_name,
                desired_scale)))
        self.del_pem_files()

    def scale_up(self):
        desired_scale = (self.current_scale + self.delta)
        self.scale_service(desired_scale)

    def scale_down(self):
        desired_scale = (self.current_scale - self.delta)
        self.scale_service(desired_scale)

    def list(self):
        """
        provide a list of containers running in a given project
        :return: list
        """
        container_list = subprocess.call(
            str(self.service_cmd_template + 'ps -q'))
        self.del_pem_files()
        return container_list
