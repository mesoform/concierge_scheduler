import json
import os
from google.cloud import storage
from google.oauth2 import service_account
from concierge_cloud import CloudBackupInterface


class GCSBackup(CloudBackupInterface):

    def __init__(self, credential_file_path, config_dir):
        """
        :param credential_file_path: Path to GCP service account credential file
        :param config_dir: Path to directory containing configuration files
        """
        self.credential = credential_file_path
        self._client = self.authenticate()
        self.config_dir = config_dir

    def authenticate(self):
        with open(self.credential, 'r') as f:
            credential_file = json.load(f)
            if 'project_id' in credential_file:
                storage_credentials = service_account.Credentials.from_service_account_info(credential_file)
                client = storage.Client(project=credential_file['project_id'], credentials=storage_credentials)
                return client
            else:
                raise KeyError('Key "project_id" not found in credential file. Invalid credential File')

    def set_storage_location(self, location: str):
        self._storage_location = location

    def assemble_upload_list(self) -> set:
        assert os.path.isdir(self.config_dir)
        config_files = set()
        for root, dirs, files in os.walk(self.config_dir):
            for file in files:
                config_files.add(os.path.join(root, file))
        return config_files

    def upload(self, upload_list, folder=''):
        """
        Upload contents of local directory to bucket/blob
        :param upload_list: set of files/directories to upload to bucket
        :param folder: (optional) Folder within bucket to upload config_dir to
        """
        bucket = self._client.get_bucket(self._storage_location)
        directory = os.path.basename(self.config_dir)
        for filename in upload_list:
            file = os.path.basename(filename)
            remote_path = os.path.join(folder, directory, file)
            blob = bucket.blob(remote_path)
            blob.upload_from_filename(filename)
