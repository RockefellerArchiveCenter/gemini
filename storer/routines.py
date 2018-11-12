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


class RoutineError(Exception): pass


class DownloadRoutine:
    def __init__(self, dirs):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.am_client = ArchivematicaClient()
        if dirs:
            self.tmp_dir = dirs['tmp']
        else:
            self.tmp_dir = settings.TMP_DIR
        if not isdir(self.tmp_dir):
            makedirs(self.tmp_dir)

    def run(self):
        for package in self.am_client.retrieve_paged('file/'):
            self.uuid = package['uuid']
            if package['origin_pipeline'].split('/')[-2] == settings.ARCHIVEMATICA['pipeline_uuid']:
                if not Package.objects.filter(data__uuid=self.uuid).exists():
                    try:
                        self.download = self.download_package(package)
                    except Exception as e:
                        raise RoutineError("Error downloading data: {}".format(e))

                    Package.objects.create(
                        type=self.package_type,
                        data=package,
                        process_status=10
                    )
        return True

    def download_package(self, package_json):
        response = self.am_client.retrieve('/file/{}/download/'.format(self.uuid), stream=True)
        extension = splitext(package_json['current_path'])[1]
        if not extension:
            extension = '.tar'
        with open(join(self.tmp_dir, '{}{}'.format(self.uuid, extension)), "wb") as package:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    package.write(chunk)
        return package


class StoreRoutine:
    def __init__(self, url, dirs):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.url = url
        self.fedora_client = FedoraClient()
        if dirs:
            self.tmp_dir = dirs['tmp']
        else:
            self.tmp_dir = settings.TMP_DIR
        if not isdir(self.tmp_dir):
            makedirs(self.tmp_dir)

    def run(self):
        for package in Package.objects.filter(process_status=10):
            self.uuid = package.data['uuid']
            try:
                container = self.fedora_client.create_container(self.uuid)
                if package.type == 'aip':
                    updated_container = self.store_aip(package.data, container)
                elif package.type == 'dip':
                    updated_container = self.store_dip(package.data, container)
            except Exception as e:
                raise RoutineError("Error storing data: {}".format(e))

            internal_sender_identifier = self.get_internal_sender_identifier()

            try:
                response = self.send_callback(container.uri_as_string(), internal_sender_identifier)
            except Exception as e:
                raise RoutineError("Error sending callback: {}".format(e))

            package.process_status = 20
            package.save()

        try:
            self.clean_up()
        except Exception as e:
            raise RoutineError("Error cleaning up: {}".format(e))

    def get_internal_sender_identifier(self):
        mets = helpers.extract_file(self.uuid, self.mets_path, join(self.tmp_dir, "METS.{}.xml".format(self.uuid)))
        tree = ET.parse(mets)
        root = tree.getroot()
        ns = {'mets': 'http://www.loc.gov/METS/'}
        element = root.find("mets:amdSec/mets:sourceMD/mets:mdWrap[@OTHERMDTYPE='BagIt']/mets:xmlData/transfer_metadata/Internal-Sender-Identifier", ns)
        return element.text if element else None

    def send_callback(self, fedora_uri, internal_sender_identifier):
        if settings.CALLBACK:
            response = requests.post(
                self.url,
                data={'identifier': internal_sender_identifier, 'uri': fedora_uri, 'package_type': self.package_type},
                headers={"Content-Type": "application/json"})
            if response:
                return True
            else:
                raise RoutineError("Could not create execute callback for {} {}".format(self, package_type, self.uuid))

    def clean_up(self):
        for d in listdir(self.tmp_dir):
            filepath = join(self.tmp_dir, d)
            if isdir(filepath):
                shutil.rmtree(filepath)
            elif isfile(filepath):
                remove(filepath)
        return True

    def store_aip(self, package, container):
        """
        Stores an AIP as a single binary in Fedora and handles the resulting URI.
        Assumes AIPs are stored as a compressed package.
        """
        self.mets_path = "METS.{}.xml".format(self.uuid)
        self.fedora_client.create_binary(self.uuid, container)
        return container

    def store_dip(self, package, container):
        """
        Stores a DIP as multiple binaries in Fedora and handles the resulting URI.
        """
        extracted = helpers.extract_all(self.uuid, join(self.tmp_dir, self.uuid), self.tmp_dir)
        reserved_names = ['manifest-', 'bagit.txt', 'tagmanifest-', 'rights.csv', 'bag-info.txt']
        for f in listdir(extracted):
            if (basename(f).startswith('METS.') and basename(f).endswith('.xml')):
                self.mets_path = f
        for f in listdir(join(extracted, 'objects')):
            if not any(name in f for name in reserved_names):
                self.fedora_client.create_binary(join(self.tmp_dir, self.uuid, 'objects', f), container)
        return container
