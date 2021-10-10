import logging
import sys
from abc import ABCMeta, abstractmethod


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


class CloudBackupInterface(metaclass=ABCMeta):
    __remote_url = NotImplemented

    @property
    @abstractmethod
    def remote_url(self) -> str:
        return self.__remote_url

    @remote_url.setter
    @abstractmethod
    def remote_url(self, url: str):
        self.__remote_url = url

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
    def upload(self, upload_files_list: set):
        """
        Upload files to a remote storage location
        :param upload_files_list: set: strings of fully qualified paths to file or directories to upload
        """
        raise NotImplementedError

