import json
from os.path import basename

from pyfc4 import models as fcrepo
from pyfc4.plugins.pcdm import models as pcdm


class FedoraClientError(Exception):
    pass


class ArchivematicaClientError(Exception):
    pass


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
