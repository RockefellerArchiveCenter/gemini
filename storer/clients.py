import json
import mimetypes
from os.path import basename, join, splitext
from pyfc4 import models as fcrepo
from pyfc4.plugins.pcdm import models as pcdm
import requests


class FedoraClientError(Exception): pass


class ArchivematicaClientError(Exception): pass


class FedoraClient(object):
    def __init__(self, root, username, password):
        self.client = fcrepo.Repository(root, username, password, default_serialization="application/ld+json")

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
                container.create(specify_uri=specify_uri, auto_refresh=False)
            return container
        except Exception as e:
            raise FedoraClientError("Error creating object: {}".format(e))

    def create_binary(self, filepath, container, mimetype):
        # Uses PCDM plugin: https://github.com/ghukill/pyfc4/blob/master/pyfc4/plugins/pcdm/models.py
        with open(filepath, 'rb') as f:
            try:
                binary = pcdm.PCDMFile(repo=self.client, uri='{}/files/{}'.format(container.uri_as_string(), basename(filepath)))
                if binary.check_exists():
                    binary.delete(remove_tombstone=True)
                new_binary = pcdm.PCDMFile(repo=self.client, uri='{}/files/{}'.format(container.uri_as_string(), basename(filepath)), binary_data=f, binary_mimetype=mimetype)
                new_binary.create(specify_uri=True, auto_refresh=False)
                new_binary.add_triple(new_binary.rdf.prefixes.rdfs['label'], basename(filepath))
                new_binary.add_triple(new_binary.rdf.prefixes.dc['format'], mimetype)
                new_binary.update(auto_refresh=False)
                return new_binary
            except Exception as e:
                raise FedoraClientError("Error creating binary: {}".format(e))


class ArchivematicaClient(object):
    def __init__(self, username, api_key, baseurl):
        self.headers = {"Authorization": "ApiKey {}:{}".format(username, api_key)}
        self.baseurl = baseurl

    def retrieve(self, uri, *args, **kwargs):
        full_url = "/".join([self.baseurl.rstrip("/"), uri.lstrip("/")])
        response = requests.get(full_url, headers=self.headers, *args, **kwargs)
        if not response:
            raise ArchivematicaClientError("Could not return a valid response for {}".format(full_url))
        return response

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
        if not current_json.get('meta'):
            raise ArchivematicaClientError("retrieve_paged doesn't know how to handle {}".format(full_url))
        while current_json['meta']['offset'] <= current_json['meta']['total_count']:
            for obj in current_json['objects']:
                yield obj
            if not current_json['meta']['next']:
                break
            params['offset'] += limit
            current_page = requests.get(full_url, params=params, headers=self.headers, **kwargs)
            current_json = current_page.json()
