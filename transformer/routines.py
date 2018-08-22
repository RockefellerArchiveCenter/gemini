import logging
from structlog import wrap_logger
from uuid import uuid4

from transformer.clients import FedoraClient
from transformer.models import AbstractObject
from transformer.transformers import ObjectTransformer, CollectionTransformer, FileTransformer, AgentTransformer, TermTransformer, RightsTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class TransformRoutine:
    def __init__(self, fedora_client):
        self.fedora_client = fedora_client if fedora_client else FedoraClient()


class ObjectRoutine(TransformRoutine):
    def __init__(self):
        self.transformer = ObjectTransformer(fedora_client=self.fedora_client)


class CollectionRoutine(TransformRoutine):
    def __init__(self):
        self.transformer = CollectionTransformer(fedora_client=self.fedora_client)


class FileRoutine(TransformRoutine):
    def __init__(self):
        self.transformer = FileTransformer(fedora_client=self.fedora_client)


class AgentRoutine(TransformRoutine):
    def __init__(self):
        self.transformer = AgentTransformer(fedora_client=self.fedora_client)


class TermRoutine(TransformRoutine):
    def __init__(self):
        self.transformer = TermTransformer(fedora_client=self.fedora_client)


class RightsRoutine(TransformRoutine):
    def __init__(self):
        self.transformer = RightsTransformer(fedora_client=self.fedora_client)
