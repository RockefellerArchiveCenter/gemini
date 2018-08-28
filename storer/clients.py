import json
import logging
from os.path import join
from pyfc4 import models as fcrepo
import requests
from structlog import wrap_logger
from uuid import uuid4

from gemini import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class FedoraClientAuthError(Exception): pass


class FedoraClientDataError(Exception): pass


class FedoraClient(object):
    def __init__(self):
        self.log = logger.new(transaction_id=str(uuid4()))
        self.client = fcrepo.Repository(
            root=settings.FEDORA['baseurl'],
            username=settings.FEDORA['username'],
            password=settings.FEDORA['password'],
            default_serialization="application/ld+json",
            # context (dict): dictionary of namespace prefixes and namespace URIs that propagate
            # 	to Resources
            # default_auto_refresh (bool): if False, resource create/update, and graph modifications
            # 	will not retrieve or parse updates automatically.  Dramatically improves performance.
        )

    def retrieve(self, identifier):
        self.log = self.log.bind(request_id=str(uuid4()), object=identifier)
        object = self.client.get_resource(identifier)
        if object is False:
            self.log.error("Could not retrieve object {} from Fedora".format(identifier))
        else:
            self.log.debug("Object retrieved from Fedora")
        return json.loads(object.data)[0]

    def create(self, data):
        self.log = self.log.bind(request_id=str(uuid4()))
        object = fcrepo.BasicContainer(self.client)
        # component.add_triple(foo.rdf.prefixes.dc.subject, 'minty')
        # consider specifying URI
        if object.create():
            self.log.debug("Object created in Fedora", object=component.uri_as_string())
            return object.uri_as_string()
        self.log.error("Could not create object in Fedora")
        return False

    def update(self, data, identifier):
        self.log = self.log.bind(request_id=str(uuid4()), object=identifier)
        object = self.client.get_resource(identifier)
        # component.add_triple(foo.rdf.prefixes.dc.subject, 'minty')
        if object.update():
            self.log.debug("Object updated in Fedora")
            return True
        self.log.error("Could not update object in Fedora")
        return False

    def delete(self, identifier):
        self.log = self.log.bind(request_id=str(uuid4()), object=identifier)
        object = self.client.get_resource(identifier)
        if object.delete():
            self.log.debug("Object deleted from Fedora")
            return True
        self.log.error("Could not delete object from Fedora")
        return False

    def get_or_create(self, type, field, value, last_updated, consumer_data):
        pass
