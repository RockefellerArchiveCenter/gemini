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


class FedoraClientError(Exception): pass


class ArchivematicaClientError(Exception): pass


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

    def create_container(self, data):
        self.log = self.log.bind(request_id=str(uuid4()))
        object = fcrepo.BasicContainer(self.client)
        # object.add_triple(foo.rdf.prefixes.dc.subject, 'minty')
        # consider specifying URI:
        #   object = fcrepo.BasicContainer(self.client, 'uri')
        #   object.create(specify_uri=True)
        if object.create():
            self.log.debug("Object created in Fedora", object=component.uri_as_string())
            return object.uri_as_string()
        self.log.error("Could not create object in Fedora")
        return False

    def create_binary(self, data):
        # https://github.com/ghukill/pyfc4/blob/master/docs/basic_usage.md#create-nonrdf-binary-resources
        # baz2 = Binary(repo, 'foo/baz2')
        # baz2.binary.location = 'http://example.org/image.jpg'
        # baz2.binary.mimetype = 'image/jpeg'
        # baz2.create(specify_uri=True)
        pass

    def update(self, data, identifier):
        self.log = self.log.bind(request_id=str(uuid4()), object=identifier)
        object = self.client.get_resource(identifier)
        # component.add_triple(foo.rdf.prefixes.dc.subject, 'minty')
        if object.update():
            self.log.debug("Object updated in Fedora")
            return True
        self.log.error("Could not update object in Fedora")
        return False


class ArchivematicaClient(object):
    def __init__(self):
        self.log = logger.new(transaction_id=str(uuid4()))
        self.headers = {"Authorization": "ApiKey {}:{}".format(settings.ARCHIVEMATICA['username'], settings.ARCHIVEMATICA['api_key'])}
        self.params = {"username": settings.ARCHIVEMATICA['username'], "api_key": settings.ARCHIVEMATICA['api_key']}
        self.baseurl = settings.ARCHIVEMATICA['baseurl']

    def retrieve(self, uri, *args, **kwargs):
        full_url = "/".join([self.baseurl.rstrip("/"), uri.lstrip("/")])
        response = requests.get(full_url, headers=self.headers, **kwargs)
        if response:
            return response
        else:
            raise FedoraClientError("Could not return a valid response for {}".format(full_url))

    def retrieve_paged(self, uri, *args, limit=10, **kwargs):
        full_url = "/".join([self.baseurl.rstrip("/"), uri.lstrip("/")])
        params = {"limit": limit, "offset": 0}
        if "params" in kwargs:
            params.update(**kwargs['params'])
            del kwargs['params']

        current_page = requests.get(full_url, params=params, headers=self.headers, **kwargs)
        current_json = current_page.json()
        if current_json.get('meta'):
            while current_json['meta']['offset'] <= current_json['meta']['total_count']:
                for obj in current_json['objects']:
                    yield obj
                if not current_json['meta']['next']: break
                params['offset'] += limit
                current_page = requests.get(full_url, params=params, headers=self.headers, **kwargs)
                current_json = current_page.json()
        else:
            raise FedoraClientError("retrieve_paged doesn't know how to handle {}".format(full_url))
