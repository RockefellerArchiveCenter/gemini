import logging
from structlog import wrap_logger
from uuid import uuid4

from storer.clients import FedoraClient
from storer.models import Package

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class StoreRoutine:
    def __init__(self, fedora_client):
        self.log = logger.bind(transaction_id=str(uuid4()))


class AIPStoreRoutine(StoreRoutine):
    """Stores an AIP in Fedora and handles the resulting URI."""
