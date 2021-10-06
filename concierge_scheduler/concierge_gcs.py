import os
import sys
import logging
from google.cloud import storage
from google.oauth2 import service_account
from concierge_cloud import CloudInterface


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


class GCSAdmin(CloudInterface):
    def __init__(self, credential_file_path, config_dir):
        """
        :param credential_file_path: Path to GCP service account credential file
        :param config_dir: Path to directory containing configuration files
        """
        super().__init__(credential_file_path, config_dir)
        self.authenticate()

    def authenticate(self):
        _info('Connecting to Google Cloud Storage...')
        storage_credentials = service_account.Credentials.from_service_account_info(self.credential_file)
        self.client = storage.Client(project=self.credential_file['project_id'], credentials=storage_credentials)
        _info('Connected to Google Cloud Storage')

    def upload_local_dir(self, name, folder=''):
        """
        Upload contents of local directory to bucket/blob
        :param name: Name of the bucket to upload config_dir to
        :param folder: (optional) Folder within bucket to upload config_dir to
        """
        _info('Uploading files to {}', name)
        config_files = self._get_config_files()
        bucket = self.client.get_bucket(name)
        directory = os.path.basename(os.path.dirname(config_files[0]))
        for filename in config_files:
            file = os.path.basename(filename)
            _info('Uploading {}...', file)
            remote_path = os.path.join(folder, directory, file)
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(filename)
        _info('Files uploaded')
