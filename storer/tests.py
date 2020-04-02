import json
import random
from os import listdir, makedirs
from os.path import isdir
from shutil import rmtree

import vcr
from django.test import Client, TestCase
from django.urls import reverse
from gemini import settings
from rest_framework.test import APIRequestFactory

from .models import Package
from .routines import CleanupRequester, DownloadRoutine, StoreRoutine
from .views import (CleanupRequestView, DeliverView, DownloadView,
                    PackageViewSet, StoreView)

storer_vcr = vcr.VCR(
    serializer='yaml',
    cassette_library_dir='fixtures/cassettes',
    record_mode='once',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization'],
)


class PackageTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = Client()
        if isdir(settings.TMP_DIR):
            rmtree(settings.TMP_DIR)
        makedirs(settings.TMP_DIR)

    def process_packages(self):
        print('*** Downloading packages ***')
        with storer_vcr.use_cassette('download.yml'):
            download = DownloadRoutine("70588e68-7742-49aa-a0ef-774a46b17b0a").run()
            self.assertNotEqual(False, download, "Packages not downloaded correctly")
        self.assertEqual(len(listdir(settings.TMP_DIR)), 1, "Wrong number of packages downloaded")
        print('*** Storing packages ***')
        with storer_vcr.use_cassette('store.yml'):
            store = StoreRoutine().run()
            self.assertNotEqual(False, store, "Packages not stored correctly")

    def request_cleanup(self):
        print('*** Requesting cleanup ***')
        with storer_vcr.use_cassette('cleanup.yml'):
            cleanup = CleanupRequester().run()
            self.assertNotEqual(False, cleanup, "Cleanup request failed")

    def get_packages(self):
        print('*** Getting all packages ***')
        request = self.factory.get(reverse('package-list'))
        response = PackageViewSet.as_view(actions={"get": "list"})(request)
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        if response.data['count'] > 0:
            pk = random.choice(Package.objects.all()).pk
            request = self.factory.get(reverse('package-detail', args=[pk]), format='json')
            response = PackageViewSet.as_view(actions={"get": "retrieve"})(request, pk=pk)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def store_views(self):
        print('*** Testing endpoints to trigger routines ***')
        Package.objects.all().delete()
        with storer_vcr.use_cassette('download.yml'):
            request = self.factory.post(
                reverse('download-packages'),
                data=json.dumps({"identifier": "70588e68-7742-49aa-a0ef-774a46b17b0a", "action": "stored"}),
                content_type="application/json")
            response = DownloadView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Return error: {}".format(response.data))
        with storer_vcr.use_cassette('store.yml'):
            request = self.factory.post(reverse('store-packages'))
            response = StoreView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Return error: {}".format(response.data))
            self.assertEqual(response.data['count'], 1, "Wrong number of packages stored {}".format(response.data))
        with storer_vcr.use_cassette('store.yml'):
            request = self.factory.post(reverse('deliver-packages'))
            response = DeliverView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Return error: {}".format(response.data))
        with storer_vcr.use_cassette('cleanup.yml'):
            request = self.factory.post(reverse('request-cleanup'))
            response = CleanupRequestView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Return error: {}".format(response.data))

    def schema(self):
        print('*** Getting schema view ***')
        schema = self.client.get(reverse('schema'))
        self.assertEqual(schema.status_code, 200, "Wrong HTTP code")

    def health_check(self):
        print('*** Getting status view ***')
        status = self.client.get(reverse('api_health_ping'))
        self.assertEqual(status.status_code, 200, "Wrong HTTP code")

    def tearDown(self):
        if isdir(settings.TMP_DIR):
            rmtree(settings.TMP_DIR)

    def test_packages(self):
        self.process_packages()
        self.request_cleanup()
        self.store_views()
        self.get_packages()
        self.schema()
        self.health_check()
