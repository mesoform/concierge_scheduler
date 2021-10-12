from abc import ABCMeta, abstractmethod


class CloudBackupInterface(metaclass=ABCMeta):
    _storage_location = NotImplemented

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'authenticate') and
                callable(subclass.authenticate) and
                hasattr(subclass, 'assemble_upload_list') and
                callable(subclass.assemble_upload_list) and
                hasattr(subclass, 'upload') and
                callable(subclass.upload) or
                NotImplemented)

    @abstractmethod
    def set_storage_location(self, location: str):
        """
        Set the location to backup files to
        :param location: location string
        """
        raise NotImplementedError

    @abstractmethod
    def authenticate(self) -> object:
        """
        Instantiate an authenticated client object to be used for uploading files
        :return: object
        """
        raise NotImplementedError

    @abstractmethod
    def assemble_upload_list(self) -> set:
        """
        Assemble a list of files or directories to be uploaded to Cloud provider
        :return: set
        """
        raise NotImplementedError

    @abstractmethod
    def upload(self, upload_list: set):
        """
        Upload files to a remote storage location
        :param upload_list: set: strings of fully qualified paths to file or directories to upload
        """
        raise NotImplementedError
