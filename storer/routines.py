import logging
from structlog import wrap_logger
from uuid import uuid4

from storer.clients import FedoraClient, ArchivematicaClient
from storer.models import Package

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class StoreRoutineError(Exception): pass


class StoreRoutine:
    def __init__(self, fedora_client):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.am_client = ArchivematicaClient()

    def run(self):
        print('{}file/?package_type={}'.format(settings.ARCHIVEMATICA['baseurl']), self.package_type)
        for package in am_client.retrieve_paged(url):
            if not Package.objects.filter(type=self.package_type, data.uuid=package['uuid']).exists():
                fedora_uri = self.store_package(package)
                if not fedora_uri:
                    raise StoreRoutineError("Could not store {} with UUID {} in Fedora".format(self.package_type, package['uuid']))
                else:
                    Package.objects.create(
                        type=self.package_type.lower(),
                        data=package
                    )
                    response = self.send_callback(fedora_uri)

    def store_package(self, package):
        # https://wiki.archivematica.org/AIP_structure
        # https://wiki.archivematica.org/DIP_structure
        download = download_package(package)
        container = store_container(package)
        if container:
            if self.package_type == 'DIP:
                for _file in package['objects']:
                    store_binary(_file)
            elif self.package_type == 'AIP':
                store_binary(download)
            return container['uri']
        else:
            raise StoreRoutineError("Could not create BasicContainer for DIP {}".format(package['uuid']))

    def download_package(package_json):
        # Get the actual binaries from Archivematica (download endpoint?)
        pass

    def store_container(package_json):
        # add metadata
        pass

    def store_binary(binary_file):
        # store binary file, add metadata
        pass

    def send_callback(self, fedora_uri):
        # figure out the bag identifier (or some piece of data that ties back to bag store)
        # POST the URI and bag identifier to Aquarius
        pass


class AIPStoreRoutine(StoreRoutine):
    """Stores an AIP in Fedora and handles the resulting URI."""
    package_type = 'AIP'


class DIPStoreRoutine(StoreRoutine):
    """Stores a DIP in Fedora and handles the resulting URI."""
    package_type = 'DIP'
