import json
import logging
from os import listdir, makedirs, remove, access, W_OK
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
        self.am_client = ArchivematicaClient(settings.ARCHIVEMATICA['username'],
                                             settings.ARCHIVEMATICA['api_key'],
                                             settings.ARCHIVEMATICA['baseurl'])
        self.tmp_dir = dirs['tmp'] if dirs else settings.TMP_DIR
        if not isdir(self.tmp_dir):
            raise RoutineError('Directory does not exist', self.tmp_dir)
        if not access(self.tmp_dir, W_OK):
            raise RoutineError('Directory does not have write permissions', self.tmp_dir)

    def run(self):
        package_count = 0
        for package in self.am_client.retrieve_paged('file/'):
            self.uuid = package['uuid']
            if package['origin_pipeline'].split('/')[-2] == settings.ARCHIVEMATICA['pipeline_uuid']:
                if not Package.objects.filter(data__uuid=self.uuid).exists():
                    try:
                        self.download = self.download_package(package)
                    except Exception as e:
                        raise RoutineError("Error downloading data: {}".format(e))

                    Package.objects.create(
                        type=package['package_type'].lower(),
                        data=package,
                        process_status=Package.DOWNLOADED
                    )
                    package_count += 1
        return "{} packages downloaded.".format(package_count)

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
        self.fedora_client = FedoraClient(root=settings.FEDORA['baseurl'],
                                          username=settings.FEDORA['username'],
                                          password=settings.FEDORA['password'])
        self.tmp_dir = dirs['tmp'] if dirs else settings.TMP_DIR
        if not isdir(self.tmp_dir):
            raise RoutineError('Directory does not exist', self.tmp_dir)
        if not access(self.tmp_dir, W_OK):
            raise RoutineError('Directory does not have write permissions', self.tmp_dir)

    def run(self):
        package_count = 0
        for package in Package.objects.filter(process_status=Package.DOWNLOADED):
            self.uuid = package.data['uuid']
            try:
                container = self.fedora_client.create_container(self.uuid)
                getattr(self, 'store_{}'.format(package.type))(package.data, container)
            except Exception as e:
                raise RoutineError("Error storing data: {}".format(e))

            package.internal_sender_identifier = self.get_internal_sender_identifier()

            if self.url:
                try:
                    self.send_callback(container.uri_as_string(), package)
                except Exception as e:
                    raise RoutineError("Error sending callback: {}".format(e))

            package.process_status = package.STORED
            package.save()

            package_count += 1

        try:
            self.clean_up()
            return "{} packages stored.".format(package_count)
        except Exception as e:
            raise RoutineError("Error cleaning up: {}".format(e))

    def get_internal_sender_identifier(self):
        mets = helpers.extract_file(join(self.tmp_dir, "{}{}".format(self.uuid, self.extension)), self.mets_path, join(self.tmp_dir, "METS.{}.xml".format(self.uuid)))
        tree = ET.parse(mets)
        root = tree.getroot()
        ns = {'mets': 'http://www.loc.gov/METS/'}
        element = root.find("mets:amdSec/mets:sourceMD/mets:mdWrap[@OTHERMDTYPE='BagIt']/mets:xmlData/transfer_metadata/Internal-Sender-Identifier", ns)
        return element.text

    def send_callback(self, fedora_uri, package):
        response = requests.post(
            self.url,
            data=json.dumps({'identifier': package.internal_sender_identifier, 'uri': fedora_uri, 'package_type': package.type}),
            headers={"Content-Type": "application/json"})
        if response:
            return True
        else:
            raise RoutineError("Could not create execute callback for {} {}".format(package.type, self.uuid))

    def clean_up(self):
        for d in listdir(self.tmp_dir):
            filepath = join(self.tmp_dir, d)
            if isdir(filepath):
                shutil.rmtree(filepath)
            elif isfile(filepath):
                remove(filepath)

    def store_aip(self, package, container):
        """
        Stores an AIP as a single binary in Fedora and handles the resulting URI.
        Assumes AIPs are stored as a compressed package.
        """
        self.extension = '.7z'
        self.mets_path = "METS.{}.xml".format(self.uuid)
        self.fedora_client.create_binary(join(self.tmp_dir, "{}{}".format(self.uuid, self.extension)), container)

    def store_dip(self, package, container):
        """
        Stores a DIP as multiple binaries in Fedora and handles the resulting URI.
        """
        self.extension = '.tar'
        extracted = helpers.extract_all(join(self.tmp_dir, "{}.tar".format(self.uuid)), join(self.tmp_dir, self.uuid), self.tmp_dir)
        reserved_names = ['manifest-', 'bagit.txt', 'tagmanifest-', 'rights.csv', 'bag-info.txt']
        for f in listdir(extracted):
            if (basename(f).startswith('METS.') and basename(f).endswith('.xml')):
                self.mets_path = f
        for f in listdir(join(extracted, 'objects')):
            if not any(name in f for name in reserved_names):
                self.fedora_client.create_binary(join(self.tmp_dir, self.uuid, 'objects', f), container)


class CleanupRequester:
    def __init__(self, url):
        self.url = url

    def run(self):
        package_count = 0
        for package in Package.objects.filter(process_status=Package.STORED):
            r = requests.post(
                self.url,
                data=json.dumps({"identifier": package.internal_sender_identifier}),
                headers={"Content-Type": "application/json"},
            )
            if r.status_code != 200:
                raise CleanupError(r.status_code, r.reason)
            package.process_status = Package.CLEANED_UP
            package.save()
            package_count += 1
        return "Requests sent to cleanup {} Packages.".format(package_count)
