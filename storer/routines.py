import logging
from structlog import wrap_logger
from uuid import uuid4

from gemini import settings

from storer.clients import FedoraClient, ArchivematicaClient
from storer.models import Package

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class StoreRoutineError(Exception): pass


class StoreRoutine:
    def __init__(self):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.am_client = ArchivematicaClient()
        self.fedora_client = FedoraClient()

    def run(self):
        url = 'file/?package_type={}'.format(self.package_type)
        for package in self.am_client.retrieve_paged(url):
            if not Package.objects.filter(type=self.package_type, data__uuid=package['uuid']).exists():
                container = self.store_package(package)
                if not container:
                    raise StoreRoutineError("Could not store {} with UUID {} in Fedora".format(self.package_type, package['uuid']))
                else:
                    Package.objects.create(
                        type=self.package_type.lower(),
                        data=package
                    )
                    response = self.send_callback(container)

    def store_package(self, package):
        # https://wiki.archivematica.org/AIP_structure
        # https://wiki.archivematica.org/DIP_structure
        download = self.download_package(package)
        container = self.store_container(package)
        if container:
            if self.package_type == 'DIP':
                for _file in package['objects']:
                    self.store_binary(_file)
            elif self.package_type == 'AIP':
                self.store_binary(download)
            return container
        else:
            raise StoreRoutineError("Could not create BasicContainer for DIP {}".format(package['uuid']))

    def download_package(self, package_json):
        # Get the actual binaries from Archivematica (download endpoint?)
        return True

    def store_container(self, package_json):
        # add metadata
        return True

    def store_binary(self, binary_file):
        # store binary file, add metadata
        return True

    def send_callback(self, fedora_uri):
        # figure out the bag identifier (or some piece of data that ties back to bag store)
        # POST the URI and bag identifier to Aquarius
        return True


class AIPStoreRoutine(StoreRoutine):
    """Stores an AIP in Fedora and handles the resulting URI."""
    package_type = 'AIP'


class DIPStoreRoutine(StoreRoutine):
    """Stores a DIP in Fedora and handles the resulting URI."""
    package_type = 'DIP'
