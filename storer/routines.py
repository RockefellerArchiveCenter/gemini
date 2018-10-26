import logging
from os import listdir, makedirs, remove
from os.path import basename, isdir, isfile, join, splitext
import requests
import shutil
from structlog import wrap_logger
from uuid import uuid4
from xml.etree import ElementTree as ET
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
        if not isdir(self.tmp_dir):
            makedirs(self.tmp_dir)

    def run(self):
        url = 'file/?package_type={}'.format(self.package_type)
        for package in self.am_client.retrieve_paged(url):
            self.uuid = package['uuid']
            if package['origin_pipeline'].split('/')[-2] == settings.ARCHIVEMATICA['pipeline_uuid']:
                if not Package.objects.filter(type=self.package_type, data__uuid=self.uuid).exists():
                    self.download = self.download_package(package)
                    container = self.store_container(package)
                    if not container:
                        raise StoreRoutineError("Could not create BasicContainer for {} with UUID {} in Fedora".format(self.package_type, self.uuid))
                    else:
                        updated_container = self.store_package(package, container)
                    if not updated_container:
                        raise StoreRoutineError("Could not store binary for {} with UUID {} in Fedora".format(self.package_type, self.uuid))
                    else:
                        Package.objects.create(
                            type=self.package_type.lower(),
                            data=package
                        )
                        internal_sender_identifier = self.get_internal_sender_identifier()
                        response = self.send_callback(container.uri_as_string(), internal_sender_identifier)
                if not self.clean_up():
                    raise StoreRoutineError("Error cleaning up")
                    return False
        return True

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
        return container

    def store_binary(self, filepath, container):
        binary = self.fedora_client.create_binary(filepath, container)
        return binary

    def get_internal_sender_identifier(self):
        mets = helpers.extract_file(self.download.name, self.mets_path, join(self.tmp_dir, "METS.{}.xml".format(self.uuid)))
        tree = ET.parse(mets)
        root = tree.getroot()
        ns = {'mets': 'http://www.loc.gov/METS/'}
        element = root.find("mets:amdSec/mets:sourceMD/mets:mdWrap[@OTHERMDTYPE='BagIt']/mets:xmlData/transfer_metadata/Internal-Sender-Identifier", ns)
        return element.text

    def send_callback(self, fedora_uri, internal_sender_identifier):
        if settings.CALLBACK:
            print(fedora_uri)
            print(internal_sender_identifier)
            print(self.package_type)
            # response = requests.post(settings.CALLBACK['url'], data={'identifier': internal_sender_identifier, 'uri': fedora_uri, 'package_type': self.package_type})
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

    def store_package(self, package, container):
        """AIPS are stored as a single binary file. This assumes AIPs are stored as a compressed package."""
        self.mets_path = "METS.{}.xml".format(self.uuid)
        self.store_binary(self.download.name, container)
        return container


class DIPStoreRoutine(StoreRoutine):
    """Stores a DIP in Fedora and handles the resulting URI."""
    package_type = 'DIP'

    def store_package(self, package, container):
        extracted = helpers.extract_all(self.download.name, join(self.tmp_dir, self.uuid), self.tmp_dir)
        reserved_names = ['manifest-', 'bagit.txt', 'tagmanifest-', 'rights.csv', 'bag-info.txt']
        for f in listdir(extracted):
            if (basename(f).startswith('METS.') and basename(f).endswith('.xml')):
                self.mets_path = f
        for f in listdir(join(extracted, 'objects')):
            if not any(name in f for name in reserved_names):
                self.store_binary(join(self.tmp_dir, self.uuid, 'objects', f), container)
        return container
