import json
from os.path import join, isdir
from os import listdir
import vcr

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from gemini import settings
from storer.cron import StoreAIPs, StoreDIPs
from storer.models import Package
from storer.views import PackageViewSet

storer_vcr = vcr.VCR(
    serializer='yaml',
    cassette_library_dir='fixtures/cassettes',
    record_mode='once',
    match_on=['path', 'method', 'query'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization'],
)


class ComponentTest(TestCase):
    # def setUp(self):
    #     self.factory = APIRequestFactory()

    def process_packages(self):
        print('*** Processing packages ***')
        print('*** Storing AIPS ***')
        with storer_vcr.use_cassette('store_aips.yml'):
            StoreAIPs().do()
        print('*** Storing DIPS ***')
        # with storer_vcr.use_cassette('store_dips.yml'):
        StoreDIPs().do()

    def get_packages(self):
        print('*** Getting all packages ***')

    # def tearDown(self):
    #     for d in [settings.TEST_UPLOAD_DIR, settings.TEST_TRANSFER_SOURCE_DIR, settings.TEST_PROCESSING_DIR]:
    #         if isdir(d):
    #             shutil.rmtree(d)

    def test_packages(self):
        self.process_packages()
        # self.get_packages()
