import json
import os
import logging
import sys


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


def _info(message, *args):
    __LOG.log(logging.INFO, message.format(*args))


def _warn(message, *args):
    __LOG.log(logging.WARN, message.format(*args))


def _log_error_and_fail(message, *args):
    __LOG.log(logging.ERROR, message.format(*args))
    sys.exit(-1)


__LOG = get_logger(__name__)


class CloudInterface:
    def __init__(self, credential_file_path, config_dir):
        """
        :param credential_file_path: Path to credential file for cloud services
        :param config_dir: Path to directory containing configuration files
        """
        self._load_credential_file(credential_file_path)
        self.config_dir = config_dir
        self.client = None
        self.command_mapping = {
            'upload': self.upload_local_dir,
            'authenticate': self.authenticate
        }

    def run(self, action, **kwargs):
        self.command_mapping[action](**kwargs)

    def _load_credential_file(self, credential_file_path):
        """
        Loads credential file. If filetype is JSON/YAML will parse to JSON object
        otherwise will read as text.
        """
        with open(credential_file_path, 'r') as f:
            _info('Loading {} credential file...', credential_file_path)
            if credential_file_path.lower().endswith(('.json', '.yaml', '.yml')):
                try:
                    self.credential_file = json.load(f)
                except json.JSONDecodeError:
                    _log_error_and_fail('Decoding JSON failed for {}', credential_file_path)
            else:
                self.credential_file = f.read()

    def _get_config_files(self) -> list:
        """
        Get all the files in the config_dir directory
        :return: List of the paths for files in config_dir
        """
        assert os.path.isdir(self.config_dir)
        config_files = []
        for root, dirs, files in os.walk(self.config_dir):
            for file in files:
                config_files.append(os.path.join(root, file))
        return config_files

    def authenticate(self):
        """
        Authenticates using credentials from credential file
        """
        raise NotImplementedError

    def upload_local_dir(self, name, folder=''):
        """
        Upload contents of local directory to bucket/blob
        :param name: Name of the bucket/blob to upload config_dir to
        :param folder: (optional) Folder within bucket/blob to upload config_dir to
        """
        raise NotImplementedError


