import json
import os
import sys
import logging
from google.cloud import storage
from google.oauth2 import service_account


class CloudBackupInterface:
    def __init__(self, bucket_name, credential_file, config_dir, bucket_folder=''):
        self.config_dir = config_dir
        self.bucket_name = bucket_name
        self.bucket_folder = bucket_folder
        self.credential_file_path = credential_file
        self.credential_file = None
        self.config_files = []
        self.client = None
        self.__LOG = self.get_logger(__name__)
        self.command_mapping = {
            'upload': self.upload_local_dir
        }

    def run(self, action):
        self.command_mapping[action]()

    # logging
    def get_logger(self, name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        stream = logging.StreamHandler()
        fmt = logging.Formatter('%(asctime)s [%(threadName)s] '
                                '[%(name)s] %(levelname)s: %(message)s')
        stream.setFormatter(fmt)
        logger.addHandler(stream)

        return logger

    def _info(self, message, *args):
        self.__LOG.log(logging.INFO, message.format(*args))

    def _warn(self, message, *args):
        self.__LOG.log(logging.WARN, message.format(*args))

    def _log_error_and_fail(self, message, *args):
        self.__LOG.log(logging.ERROR, message.format(*args))
        sys.exit(-1)

    def authenticate(self):
        """Load in the credential file for cloud backup"""
        f = open(self.credential_file_path, 'r')
        self._info('Authenticating with {} credentials...', self.credential_file_path)
        try:
            self.credential_file = json.load(f)
        except:
            self._warn('File {} not in JSON format, JSON format required for GCP authentication', self.credential_file_path)
            self.credential_file = f.read()
        f.close()

    def upload_local_dir(self):
        assert os.path.isdir(self.config_dir)
        for root, dirs, files in os.walk(self.config_dir):

            for file in files:
                self.config_files.append(os.path.join(root, file))


class GCSAdmin(CloudBackupInterface):
    def __init__(self, bucket_name, credential_file, config_dir, bucket_folder) -> None:
        super().__init__(bucket_name, credential_file, config_dir, bucket_folder)
        self.authenticate()

    def authenticate(self):
        super().authenticate()
        storage_credentials = service_account.Credentials.from_service_account_info(self.credential_file)
        self.client = storage.Client(project=self.credential_file['project_id'], credentials=storage_credentials)
        self._info('Connected to Google Cloud Storage')

    def upload_local_dir(self):
        super().upload_local_dir()
        self._info('Uploading files to {}/{}:', self.bucket_name, self.bucket_folder)
        bucket = self.client.get_bucket(self.bucket_name)
        directory = os.path.basename(os.path.dirname(self.config_files[0]))
        for filename in self.config_files:
            file = os.path.basename(filename)
            self._info('Uploading {}...', file)
            remote_path = os.path.join(self.bucket_folder, directory, file)
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(filename)
        self._info('Files uploaded')
