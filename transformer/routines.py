import logging
from structlog import wrap_logger
from uuid import uuid4

from clients import ArchivesSpaceClient, FedoraClient
from transformer.models import AbstractObject
from transformer.transformers import ArchivesSpaceDataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class ObjectRoutine:
    def __init__(self, aspace_client, aurora_client):
        self.aspace_client = aspace_client if aspace_client else ArchivesSpaceClient()
        self.fedora_client = fedora_client if fedora_client else FedoraClient()
        self.transformer = ArchivesSpaceDataTransformer(aspace_client=self.aspace_client)
        self.log = logger

    def run(self, source_object):
        self.log.bind(request_id=str(uuid4()))
        self.source_object = source_object
        self.data = source_object.data
        if int(self.source_object.process_status) <= 10:
            if not self.create_grouping_component():
                self.log.error("Error creating grouping component", object=self.data['url'])
                return False
            self.source_object.process_status = 30
            self.source_object.save()

        if int(self.source_object.process_status) <= 30:
            # TODO: find a cleaner way to get the ArchivesSpace URI
            parent_object = ConsumerObject.objects.get(source_object=self.source_object, type='component')
            self.parent = Identifier.objects.get(consumer_object=parent_object, source='archivesspace').identifier
            self.collection = self.source_object.data['resource']
            for transfer in self.data['transfers']:
                if not self.create_component(transfer):
                    self.log.error("Error creating component", object=transfer['url'])
                    return False
            self.source_object.process_status = 50
            self.source_object.save()

    def create_grouping_component(self):
        self.log.bind(request_id=str(uuid4()))
        consumer_data = self.transformer.transform_grouping_component(self.data)
        aspace_identifier = self.aspace_client.create(consumer_data, 'component')
        if (consumer_data and aspace_identifier):
            ConsumerObject().initial_save(
                consumer_data=consumer_data, identifier=aspace_identifier,
                type='component', source_object=self.source_object)
            return True
        return False

    def update_identifier(self, identifiers, new_identifier):
        for identifier in identifiers:
            if identifier['source'] == 'archivesspace':
                identifier['identifier'] = new_identifier
                return True
        return False

    def create_component(self, data):
        self.log.bind(request_id=str(uuid4()))
        source_data = self.aurora_client.retrieve(data['url'])
        self.transformer.parent = self.parent
        self.transformer.collection = self.collection
        consumer_data = self.transformer.transform_component(source_data)
        aspace_identifier = self.aspace_client.create(consumer_data, 'component')
        IDENTIFIERS = (
            (source_data['parents'], self.parent),
            (source_data['collections'], self.collection),
            (source_data['external_identifiers'], aspace_identifier)
        )
        # If an ArchivesSpace identifier exists, update it. If not, add a new identifier.
        for t in IDENTIFIERS:
            if not self.update_identifier(t[0], t[1]):
                t[0].append({"identifier": t[1], "source": "archivesspace"})
        if self.aurora_client.update(data['url'], data=source_data):
            ConsumerObject().initial_save(
                consumer_data=consumer_data, identifier=aspace_identifier,
                type='component', source_data=source_data)
            return True
        return False
