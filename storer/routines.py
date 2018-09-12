import logging
from os import listdir, makedirs, remove
from os.path import basename, isdir, isfile, join, splitext
import requests
import shutil
from structlog import wrap_logger
from uuid import uuid4
import zipfile

from gemini import settings

from storer.clients import FedoraClient, ArchivematicaClient
from storer import helpers
from storer.models import Package

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class StoreRoutineError(Exception): pass


class StoreRoutine:
    def __init__(self, dirs):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.am_client = ArchivematicaClient()
        self.fedora_client = FedoraClient()
        if dirs:
            self.tmp_dir = dirs['tmp']
        else:
            self.tmp_dir = settings.TMP_DIR

    def run(self):
        url = 'file/?package_type={}'.format(self.package_type)
        for package in self.am_client.retrieve_paged(url):
            self.uuid = package['uuid']
            if not Package.objects.filter(type=self.package_type, data__uuid=self.uuid).exists():
                container = self.store_package(package)
                if not container:
                    raise StoreRoutineError("Could not store {} with UUID {} in Fedora".format(self.package_type, self.uuid))
                else:
                    Package.objects.create(
                        type=self.package_type.lower(),
                        data=package
                    )
                    response = self.send_callback(container.uri_as_string())
            if not self.clean_up():
                raise StoreRoutineError("Error cleaning up")
                return False
        return True

    def store_package(self, package):
        # https://wiki.archivematica.org/AIP_structure
        # https://wiki.archivematica.org/DIP_structure
        if not isdir(self.tmp_dir):
            makedirs(self.tmp_dir)
        self.download = self.download_package(package)
        container = self.store_container(package)
        if container:
            if self.package_type == 'DIP':
                extracted = helpers.extract_all(self.download.name, join(self.tmp_dir, self.uuid), self.tmp_dir)
                reserved_names = ['manifest-', 'bagit.txt', 'tagmanifest-', 'rights.csv', 'bag-info.txt']
                for f in listdir(join(extracted, 'objects')):
                    if 'bag-info.txt' in f:
                        self.bag_info_path = join(extracted, 'objects', f)
                    if not any(name in f for name in reserved_names):
                        self.store_binary(join(self.tmp_dir, self.uuid, 'objects', f), container)
            elif self.package_type == 'AIP':
                self.bag_info_path = join(self.uuid, 'data', 'objects', 'bag-info.txt')
                self.store_binary(self.download.name, container)
            return container
        else:
            raise StoreRoutineError("Could not create BasicContainer for {} {}".format(self.package_type, self.uuid))

    def download_package(self, package_json):
        response = self.am_client.retrieve('/file/{}/download/'.format(self.uuid))
        extension = splitext(package_json['current_path'])[1]
        if not extension:
            extension = '.tar'
        package = open(join(self.tmp_dir, '{}{}'.format(self.uuid, extension)), "wb")
        package.write(response._content)
        package.close()
        return package

    def store_container(self, package_json):
        container = self.fedora_client.create_container(self.uuid)
        # container.add_triple(foo.rdf.prefixes.dc.subject, 'minty')
        # container.update()
        return container

    def store_binary(self, filepath, container):
        binary = self.fedora_client.create_binary(filepath, container)
        return binary

    def send_callback(self, fedora_uri):
        if settings.CALLBACK:
            if not isfile(self.bag_info_path):
                self.bag_info_path = helpers.extract_file(self.download.name, self.bag_info_path, join(self.tmp_dir, basename(self.bag_info_path)))
            bag_info = helpers.get_fields_from_file(self.bag_info_path)
            # response = requests.post(settings.CALLBACK['url'], data={'identifier': bag_info['Internal_Sender_Identifier'], 'uri': fedora_uri})
            # if response:
            #     return True
            # else:
            #     raise StoreRoutineError("Could not create execute callback for {} {}".format(self, package_type, self.uuid))

    def clean_up(self):
        for d in listdir(self.tmp_dir):
            filepath = join(self.tmp_dir, d)
            if isdir(filepath):
                shutil.rmtree(filepath)
            elif isfile(filepath):
                remove(filepath)
        return True


class AIPStoreRoutine(StoreRoutine):
    """Stores an AIP in Fedora and handles the resulting URI."""
    package_type = 'AIP'


class DIPStoreRoutine(StoreRoutine):
    """Stores a DIP in Fedora and handles the resulting URI."""
    package_type = 'DIP'
