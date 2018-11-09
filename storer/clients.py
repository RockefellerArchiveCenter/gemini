import json
import logging
import mimetypes
from os.path import basename, join, splitext
from pyfc4 import models as fcrepo
from pyfc4.plugins.pcdm import models as pcdm
import requests
from structlog import wrap_logger
from uuid import uuid4

from gemini import settings


class FedoraClientError(Exception): pass


class ArchivematicaClientError(Exception): pass


class FedoraClient(object):
    def __init__(self):
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
        object = self.client.get_resource(identifier)
        if object is False:
            raise FedoraClientError("Error retrieving object {}".format(identifier))
        return json.loads(object.data)[0]

    def create_container(self, uri=None):
        # uses PCDM plugin: https://github.com/ghukill/pyfc4/blob/master/pyfc4/plugins/pcdm/models.py#L121
        specify_uri = True if uri else False
        try:
            container = pcdm.PCDMObject(repo=self.client, uri=uri)
            if not container.check_exists():
                container.create(specify_uri=specify_uri)
            return container
        except Exception as e:
            raise FedoraClientError("Error creating object: {}".format(e))

    def create_binary(self, filepath, container):
        # Uses PCDM plugin: https://github.com/ghukill/pyfc4/blob/master/pyfc4/plugins/pcdm/models.py
        mimetype = mimetypes.guess_type(filepath)[0]
        with open(filepath, 'rb') as f:
            try:
                binary = pcdm.PCDMFile(repo=self.client, uri='{}/files/{}'.format(container.uri_as_string(), basename(filepath)), binary_data=f, binary_mimetype=mimetype)
                if binary.check_exists():
                    current_binary = self.client.get_resource('{}/files/{}'.format(container.uri_as_string(), basename(filepath)))
                    current_binary.delete(remove_tombstone=True)
                binary.create(specify_uri=True)
                binary.add_triple(binary.rdf.prefixes.rdfs['label'], basename(filepath))
                binary.add_triple(binary.rdf.prefixes.dc['format'], mimetype)
                binary.update()
                return binary
            except Exception as e:
                raise FedoraClientError("Error creating binary: {}".format(e))


class ArchivematicaClient(object):
    def __init__(self):
        self.headers = {"Authorization": "ApiKey {}:{}".format(settings.ARCHIVEMATICA['username'], settings.ARCHIVEMATICA['api_key'])}
        self.baseurl = settings.ARCHIVEMATICA['baseurl']

    def retrieve(self, uri, *args, **kwargs):
        full_url = "/".join([self.baseurl.rstrip("/"), uri.lstrip("/")])
        response = requests.get(full_url, headers=self.headers, *args, **kwargs)
        if response:
            return response
        else:
            raise ArchivematicaClientError("Could not return a valid response for {}".format(full_url))

    def retrieve_paged(self, uri, *args, limit=10, **kwargs):
        full_url = "/".join([self.baseurl.rstrip("/"), uri.lstrip("/")])
        params = {"limit": limit, "offset": 0}
        if "params" in kwargs:
            params.update(**kwargs['params'])
            del kwargs['params']

        current_page = requests.get(full_url, params=params, headers=self.headers, **kwargs)
        if not current_page:
            raise ArchivematicaClientError("Authentication error while retrieving {}".format(full_url))
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
            raise ArchivematicaClientError("retrieve_paged doesn't know how to handle {}".format(full_url))
