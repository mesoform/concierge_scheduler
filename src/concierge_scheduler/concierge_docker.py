import subprocess
import os
from pyzabbix import ZabbixAPI

DOCKER_CERT_PATH = "/tmp/certs"
DOCKER_HOST = "tcp://us-east-1.docker.joyent.com:2376"
DOCKER_CLIENT_TIMEOUT = 800
COMPOSE_HTTP_TIMEOUT = 800
ZABBIX_HOST = os.getenv('ZBX_API_HOST')
ZABBIX_USER = os.getenv('ZBX_USER')
ZABBIX_PASS = os.getenv('ZBX_PASS')


class DockerAdmin:
    """

    """

    def __init__(self, service_name):
        """

        :param service_name:
        """
        self.service_name = service_name
        self.zbx_url = 'http://{}'.format(ZABBIX_HOST)
        self.zbx_api = ZabbixAPI(self.zbx_url).login(
            user=ZABBIX_USER, password=ZABBIX_PASS)
        self.key_file = \
            self.create_pem_file('notes', 'key', self.service_name)
        self.cert_file = \
            self.create_pem_file('poc_1_notes', 'cert', self.service_name)
        self.ca_file = \
            self.create_pem_file('poc_1_notes', 'ca', self.service_name)

    def create_pem_file(self, inv_property, filename, service_name):
        attribute = self.zbx_api.host.get(output=["host"],
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

    def scale_service(self, desired_scale):
        subprocess.call(
            "/usr/local/bin/docker-compose "
            "--tlsverify "
            "--tlscert={} "
            "--tlscacert={} "
            "--tlskey={} "
            "--host={} "
            "--file /tmp/docker-compose.yml "
            "--project-name dockerlx "
            "up -d "
            "--scale {}={}".format(
                self.cert_file,
                self.key_file,
                self.ca_file,
                DOCKER_HOST,
                self.service_name,
                desired_scale).split())
        self.del_pem_files()

    def scale_up(self, current_scale, increment):
        desired_scale = (current_scale + increment)
        self.scale_service(desired_scale)

    def scale_down(self, current_scale, increment):
        desired_scale = (current_scale - increment)
        self.scale_service(desired_scale)

    def service_ps(self):
        subprocess.call(
            "/usr/local/bin/docker-compose "
            "--tlsverify "
            "--tlscert={}/cert.pem "
            "--tlscacert={}/ca.pem "
            "--tlskey={}/key.pem "
            "--host={} "
            "--file /tmp/docker-compose.yml "
            "--project-name dockerlx "
            "ps".format(
                DOCKER_CERT_PATH,
                DOCKER_CERT_PATH,
                DOCKER_CERT_PATH,
                DOCKER_HOST).split())
        self.del_pem_files()
