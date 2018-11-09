import json
from os.path import join, isdir
from os import listdir
import random
from shutil import rmtree
import vcr

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from gemini import settings
from storer.routines import AIPRoutine, DIPRoutine
from storer.models import Package
from storer.views import PackageViewSet, DownloadView, StoreView

storer_vcr = vcr.VCR(
    serializer='yaml',
    cassette_library_dir='fixtures/cassettes',
    record_mode='new_episodes',
    match_on=['path', 'method', 'query'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization'],
)


class PackageTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = Client()

    def process_packages(self):
        print('*** Processing packages ***')
        print('*** Downloading AIPS ***')
        with storer_vcr.use_cassette('store_aips.yml'):
            store_aips = AIPRoutine(dirs={'tmp': settings.TEST_TMP_DIR}).download()
            self.assertNotEqual(False, store_aips, "AIPS not downloaded correctly")
        print('*** Downloading DIPS ***')
        with storer_vcr.use_cassette('store_dips.yml'):
            store_dips = DIPRoutine(dirs={'tmp': settings.TEST_TMP_DIR}).download()
            self.assertNotEqual(False, store_dips, "DIPS not downloaded correctly")
        print('*** Storing AIPS ***')
        with storer_vcr.use_cassette('store_aips.yml'):
            store_aips = AIPRoutine(dirs={'tmp': settings.TEST_TMP_DIR}).store()
            self.assertNotEqual(False, store_aips, "AIPS not stored correctly")
        print('*** Storing DIPS ***')
        with storer_vcr.use_cassette('store_dips.yml'):
            store_dips = DIPRoutine(dirs={'tmp': settings.TEST_TMP_DIR}).store()
            self.assertNotEqual(False, store_dips, "DIPS not stored correctly")

    def get_packages(self):
        print('*** Getting all packages ***')
        request = self.factory.get(reverse('package-list'))
        response = PackageViewSet.as_view(actions={"get": "list"})(request)
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        if len(response.data):
            pk = random.randrange(len(response.data))+1
            request = self.factory.get(reverse('package-detail', args=[pk]), format='json')
            response = PackageViewSet.as_view(actions={"get": "retrieve"})(request, pk=pk)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def store_views(self):
        print('*** Testing endpoints to trigger routines ***')
        with storer_vcr.use_cassette('store_aips.yml'):
            request = self.factory.post(reverse('download-packages', kwargs={"package": "aips"}), {"test": True})
            response = DownloadView.as_view()(request, package="aips")
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        with storer_vcr.use_cassette('store_dips.yml'):
            request = self.factory.post(reverse('download-packages', kwargs={"package": "dips"}), {"test": True})
            response = DownloadView.as_view()(request, package="dips")
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        with storer_vcr.use_cassette('store_aips.yml'):
            request = self.factory.post(reverse('store-packages', kwargs={"package": "aips"}), {"test": True})
            response = StoreView.as_view()(request, package="aips")
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        with storer_vcr.use_cassette('store_dips.yml'):
            request = self.factory.post(reverse('store-packages', kwargs={"package": "dips"}), {"test": True})
            response = StoreView.as_view()(request, package="dips")
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def schema(self):
        print('*** Getting schema view ***')
        schema = self.client.get(reverse('schema-json', kwargs={"format": ".json"}))
        self.assertEqual(schema.status_code, 200, "Wrong HTTP code")

    def health_check(self):
        print('*** Getting status view ***')
        status = self.client.get(reverse('api_health_ping'))
        self.assertEqual(status.status_code, 200, "Wrong HTTP code")

    def tearDown(self):
        if isdir(settings.TEST_TMP_DIR):
            rmtree(settings.TEST_TMP_DIR)

    def test_packages(self):
        self.process_packages()
        self.get_packages()
        self.store_views()
        self.schema()
        self.health_check()
