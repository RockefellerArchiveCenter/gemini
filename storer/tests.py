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
from .routines import (CleanupRequester, DeliverRoutine, DownloadRoutine,
                       StoreRoutine)
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

    def routines(self):
        with storer_vcr.use_cassette('download.yml'):
            download = DownloadRoutine("70588e68-7742-49aa-a0ef-774a46b17b0a").run()
            self.assertNotEqual(False, download, "Packages not downloaded correctly")
            self.assertEqual("Package downloaded.", download[0])
        self.assertEqual(len(listdir(settings.TMP_DIR)), 1, "Wrong number of packages downloaded")
        for cassette, routine, msg in [
                ('store.yml', StoreRoutine, "Packages not stored correctly"),
                ('store.yml', DeliverRoutine, "Package data not delivered"),
                ('cleanup.yml', CleanupRequester, "Cleanup request failed")]:
            with storer_vcr.use_cassette(cassette):
                res = routine().run()
                self.assertNotEqual(False, res, msg)

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

    def views(self):
        print('*** Testing endpoints to trigger routines ***')
        Package.objects.all().delete()
        with storer_vcr.use_cassette('download.yml'):
            request = self.factory.post(
                reverse('download-packages'),
                data=json.dumps({"identifier": "70588e68-7742-49aa-a0ef-774a46b17b0a", "action": "stored"}),
                content_type="application/json")
            response = DownloadView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Return error: {}".format(response.data))
        for cassette, view_str, view in [
                ("store.yml", "store-packages", StoreView),
                ("store.yml", "deliver-packages", DeliverView),
                ("cleanup.yml", "request-cleanup", CleanupRequestView)]:
            with storer_vcr.use_cassette(cassette):
                request = self.factory.post(reverse(view_str))
                response = view.as_view()(request)
                self.assertEqual(response.status_code, 200, "Return error: {}".format(response.data))
                if view_str in ["download-packages", "store-packages"]:
                    self.assertEqual(response.data['count'], 1, "Wrong number of packages processed by {}".format(view_str))

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
        self.routines()
        self.views()
        self.get_packages()
        self.schema()
        self.health_check()
