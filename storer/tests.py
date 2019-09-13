import json
from os.path import join, isdir
from os import listdir, makedirs
import random
from shutil import rmtree
import vcr

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from gemini import settings
from storer.routines import DownloadRoutine, StoreRoutine, CleanupRequester
from storer.models import Package
from storer.views import PackageViewSet, DownloadView, StoreView, CleanupRequestView

storer_vcr = vcr.VCR(
    serializer='yaml',
    cassette_library_dir='fixtures/cassettes',
    record_mode='once',
    match_on=['path', 'method', 'query'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization'],
)


class PackageTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = Client()
        if not isdir(settings.TEST_TMP_DIR):
            makedirs(settings.TEST_TMP_DIR)

    def process_packages(self):
        print('*** Downloading packages ***')
        with storer_vcr.use_cassette('download.yml'):
            download = DownloadRoutine(dirs={'tmp': settings.TEST_TMP_DIR}).run()
            self.assertNotEqual(False, download, "Packages not downloaded correctly")
        print('*** Storing packages ***')
        with storer_vcr.use_cassette('store.yml'):
            store = StoreRoutine('http://aquarius-web:8002/packages/',
                                 dirs={'tmp': settings.TEST_TMP_DIR}).run()
            self.assertNotEqual(False, store, "Packages not stored correctly")

    def request_cleanup(self):
        print('*** Requesting cleanup ***')
        with storer_vcr.use_cassette('cleanup.yml'):
            cleanup = CleanupRequester('http://fornax-web:8003/cleanup/').run()
            self.assertNotEqual(False, cleanup, "Cleanup request failed")

    def get_packages(self):
        print('*** Getting all packages ***')
        request = self.factory.get(reverse('package-list'))
        response = PackageViewSet.as_view(actions={"get": "list"})(request)
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        if response.data['count'] > 0:
            pk = random.randrange(response.data['count'])+1
            request = self.factory.get(reverse('package-detail', args=[pk]), format='json')
            response = PackageViewSet.as_view(actions={"get": "retrieve"})(request, pk=pk)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def store_views(self):
        print('*** Testing endpoints to trigger routines ***')
        with storer_vcr.use_cassette('download.yml'):
            request = self.factory.post(reverse('download-packages'), {"test": True})
            response = DownloadView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        with storer_vcr.use_cassette('store.yml'):
            request = self.factory.post(reverse('store-packages'), {"test": True})
            response = StoreView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        with storer_vcr.use_cassette('cleanup.yml'):
            request = self.factory.post(reverse('request-cleanup'), {"test": True})
            response = CleanupRequestView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def schema(self):
        print('*** Getting schema view ***')
        schema = self.client.get(reverse('schema'))
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
        self.request_cleanup()
        self.store_views()
        self.get_packages()
        self.schema()
        self.health_check()
