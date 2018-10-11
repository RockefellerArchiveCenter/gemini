import json
from os.path import join, isdir
from os import listdir
import random
from shutil import rmtree
import vcr

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from gemini import settings
from storer.cron import StoreAIPs, StoreDIPs
from storer.models import Package
from storer.views import PackageViewSet, StoreView

storer_vcr = vcr.VCR(
    serializer='yaml',
    cassette_library_dir='fixtures/cassettes',
    record_mode='once',
    match_on=['path', 'method', 'query'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization'],
)


class ComponentTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def process_packages(self):
        print('*** Processing packages ***')
        print('*** Storing AIPS ***')
        with storer_vcr.use_cassette('store_aips.yml'):
            store_aips = StoreAIPs().do(dirs={'tmp': settings.TEST_TMP_DIR})
            self.assertNotEqual(False, store_aips, "AIPS not stored correctly")
        print('*** Storing DIPS ***')
        with storer_vcr.use_cassette('store_dips.yml'):
            store_dips = StoreDIPs().do(dirs={'tmp': settings.TEST_TMP_DIR})
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
        print('*** Testing endpoints to trigger crons ***')
        with storer_vcr.use_cassette('store_aips.yml'):
            request = self.factory.post(reverse('store-packages', kwargs={"package": "aips"}))
            response = StoreView.as_view()(request, package="aips")
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        with storer_vcr.use_cassette('store_dips.yml'):
            request = self.factory.post(reverse('store-packages', kwargs={"package": "dips"}))
            response = StoreView.as_view()(request, package="dips")
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def tearDown(self):
        if isdir(settings.TEST_TMP_DIR):
            rmtree(settings.TEST_TMP_DIR)

    def test_packages(self):
        self.process_packages()
        self.get_packages()
        self.store_views()
