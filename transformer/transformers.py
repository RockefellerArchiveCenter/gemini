import iso8601
import json
from pycountry import languages as langz
import time

from gemini import settings
from transformer.clients import FedoraClient


class TransformError(Exception): pass


class DataTransformer(object):
    def __init__(self, fedora_client=None):
        self.fedora_client = fedora_client if fedora_client else FedoraClient()
        self.transform_start_time = int(time.time())


class CollectionTransformer(DataTransformer):
    pass


class ObjectTransformer(DataTransformer):
    pass


class AgentTransformer(DataTransformer):
    pass


class FileTransformer(DataTransformer):
    pass


class RightsTransformer(DataTransformer):
    pass


class TermTransformer(DataTransformer):
    pass


class NoteTransformer(DataTransformer):
    pass


class LanguageTransformer(DataTransformer):
    pass


class ExtentTransformer(DataTransformer):
    pass
