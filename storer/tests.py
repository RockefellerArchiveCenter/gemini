from os import listdir, makedirs
from os.path import isdir, join
from shutil import copyfile, rmtree
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from pyfc4 import models as fcrepo
from pyfc4.plugins.pcdm import models as pcdm
from rest_framework.test import APIRequestFactory

from gemini import settings

from .models import Package
from .routines import (AddDataRoutine, CleanupRequester, DeliverRoutine,
                       DownloadRoutine, ParseMETSRoutine, StoreRoutine)
from .views import PackageViewSet


class PackageRoutinesTestCase(TestCase):
    def setUp(self):
        if isdir(settings.TMP_DIR):
            rmtree(settings.TMP_DIR)
        makedirs(settings.TMP_DIR)
        self.aip_uuids = ["ddef17b8-0434-41d3-93d5-a89c63d38556", "56ce5517-dc77-4cb9-bb4d-97210476f89b"]
        self.dip_uuids = ["96c906b4-c8ec-4e82-abe6-e37db767f12f", "4d8fae2e-e840-444a-ab40-9f9a74a60522"]

    def create_packages_with_status(self, status, package_type='aip'):
        for uuid in getattr(self, f'{package_type}_uuids'):
            package = Package.objects.create(
                archivematica_identifier=uuid,
                process_status=status)
            if status >= Package.DATA_ADDED:
                package.data = {"current_full_path": "/mnt/nfs-archivematica/AIPsStore/7058/8e68/7742/49aa/a0ef/774a/46b1/7b0a/2a86a08d-7f7a-412d-8d86-5faf0c28b947-70588e68-7742-49aa-a0ef-774a46b17b0a.7z",
                                "current_location": "/api/v2/location/7662e69a-6b4f-4a83-825f-ce3b92006969/",
                                "current_path": "7058/8e68/7742/49aa/a0ef/774a/46b1/7b0a/2a86a08d-7f7a-412d-8d86-5faf0c28b947-70588e68-7742-49aa-a0ef-774a46b17b0a.7z",
                                "encrypted": False, "misc_attributes": {}, "origin_pipeline": "/api/v2/pipeline/b80b39f0-ab3d-406d-8efd-dd48b532c34f/",
                                "package_type": package_type.upper(), "related_packages": [], "replicas": [], "replicated_package":
                                None, "resource_uri": "/api/v2/file/70588e68-7742-49aa-a0ef-774a46b17b0a/",
                                "size": 446866, "status": "UPLOADED", "uuid": "70588e68-7742-49aa-a0ef-774a46b17b0a"}
                package.type = package_type
            if status >= Package.METS_PARSED:
                package.mimetypes = {
                    '18357d28-5f69-471e-8ef1-c706a8026e01': 'application/pdf',
                    '4a3b0944-7cd9-4fdc-8e69-35ea57c26152': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '5b937c1f-459a-4a06-8b29-3344205f2a21': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '5e503a0c-e5c8-4437-a99b-bfc0957bbf42': 'application/json',
                    '736dc7bc-5913-41f0-adc6-f868a7c84ea2': 'application/vnd.oasis.opendocument.text',
                    'aac7f3b4-eed3-4a8f-81bd-b9328a587dd5': 'application/rtf',
                    'f9472829-43b7-4ef5-b10a-1f974e6da337': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    '102672c7-bdfc-4728-b1b9-1945384e41d7': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '1511139c-564c-47de-a3f0-eb5ec20a5449': 'application/pdf',
                    '2c0e4f1b-11fd-4a3c-829d-20dedb6dd7ca': 'application/json',
                    '49d3d62a-42aa-4da6-8bfc-e48a784f9dfb': 'application/rtf',
                    'b643c661-47c5-4f9f-8803-9122f7a40394': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'eb562234-e73c-43cf-8ab7-1d12dc3d1d5f': 'application/vnd.oasis.opendocument.text',
                    'f209f58d-def9-48a6-8f48-b94022e5944b': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                }
                package.internal_sender_identifier = '12345'
                package.origin = 'aurora'
                package.archivesspace_uri = 'repositories/2/archival_objects/1'
            package.save()

    def copy_binaries(self, filter):
        for f in listdir(join('fixtures', 'binaries')):
            if f.endswith(filter):
                copyfile(join('fixtures', 'binaries', f), join(settings.TMP_DIR, f))

    @patch('amclient.AMClient.get_package_details')
    def test_add_data_routine(self, mock_details):
        """Tests that AddDataRoutine works as expected."""
        mock_details.return_value = {
            "package_type": "AIP",
            "resource_uri": "/api/v2/file/70588e68-7742-49aa-a0ef-774a46b17b0a/",
            "current_location": "/api/v2/location/7662e69a-6b4f-4a83-825f-ce3b92006969/"}
        self.create_packages_with_status(Package.CREATED)
        for _ in range(len(self.aip_uuids)):
            msg, count = AddDataRoutine().run()
            self.assertNotEqual(False, msg, "Data not added to packages correctly.")
            self.assertEqual("Data added to package.", msg)
        for package in Package.objects.all():
            self.assertEqual(package.process_status, Package.DATA_ADDED)
            self.assertEqual(package.type, 'aip')
            self.assertEqual(package.fedora_uri, '/api/v2/file/70588e68-7742-49aa-a0ef-774a46b17b0a/')
            self.assertTrue(isinstance(package.data, dict))

    def test_add_data_get_end_status(self):
        """Ensures end status is set as expected in AddDataRoutine."""
        for location, expected_status in [
            ('/api/v2/location/7662e69a-6b4f-4a83-825f-ce3b92006968/', Package.DOWNLOADED),
                ('/api/v2/location/7662e69a-6b4f-4a83-825f-ce3b92006969/', Package.DATA_ADDED)]:
            package = Package.objects.create(
                archivematica_identifier='b663b040-5718-427c-ac84-26fc48191072',
                process_status=Package.CREATED,
                data={'current_location': location}
            )
            end_status = AddDataRoutine().get_end_status(package)
            self.assertEqual(end_status, expected_status)

    @patch('amclient.AMClient.download_package')
    def test_download_routine(self, mock_download):
        """Ensures DownloadRoutine downloads files and sets status."""
        download_path = join(settings.TMP_DIR, '4d8fae2e-e840-444a-ab40-9f9a74a60522.tar')
        mock_download.return_value = download_path
        self.create_packages_with_status(Package.DATA_ADDED)
        for _ in range(len(self.aip_uuids)):
            copyfile(join('fixtures', 'binaries', '4d8fae2e-e840-444a-ab40-9f9a74a60522.tar'), download_path)
            msg, count = DownloadRoutine().run()
            self.assertNotEqual(False, msg, "Packages not downloaded correctly")
            self.assertEqual("Package downloaded.", msg)
        self.assertEqual(len(listdir(settings.TMP_DIR)), len(self.aip_uuids), "Wrong number of packages downloaded")
        self.assertEqual(len(Package.objects.filter(process_status=Package.DOWNLOADED)), len(self.aip_uuids))

    def test_download_routine_is_downloadable(self):
        """Ensures is_downloadable correctly parses package data."""
        for pipeline, expected_status in [
                ('/api/v2/pipeline/b80b39f0-ab3d-406d-8efd-dd48b532c34f/', True),
                ('/api/v2/pipeline/b80b39f0-ab3d-406d-8efd-dd48b532c34g/', False)]:
            package = Package.objects.create(
                archivematica_identifier='b663b040-5718-427c-ac84-26fc48191072',
                process_status=Package.DATA_ADDED,
                data={'origin_pipeline': pipeline}
            )
            downloadable = DownloadRoutine().is_downloadable(package.data)
            self.assertEqual(downloadable, expected_status)

    @patch('storer.routines.ParseMETSRoutine.parse_mets')
    def test_parse_routine_aip(self, mock_parse):
        """Ensures AIPs are correctly parsed."""
        self.copy_binaries(filter='.7z')
        internal_sender_identifier = '12345'
        archivesspace_uri = 'repositories/2/archival_objects/1'
        origin = 'aurora'
        mimetypes = {"foo": "bar"}
        mock_parse.return_value = {
            "internal_sender_identifier": internal_sender_identifier,
            "archivesspace_uri": archivesspace_uri,
            "origin": origin,
            "mimetypes": mimetypes, }
        self.create_packages_with_status(Package.DOWNLOADED)
        for _ in range(len(self.aip_uuids)):
            msg, count = ParseMETSRoutine().run()
            self.assertNotEqual(False, msg, "Packages not stored correctly")
            self.assertEqual("METS data parsed.", msg)
        for package in Package.objects.all():
            self.assertEqual(package.mimetypes, mimetypes)
            self.assertEqual(package.internal_sender_identifier, internal_sender_identifier)
            self.assertEqual(package.origin, origin)
            self.assertEqual(package.archivesspace_uri, archivesspace_uri)
        self.assertEqual(len(Package.objects.filter(process_status=Package.METS_PARSED)), len(self.aip_uuids))
        self.assertEqual(mock_parse.call_count, len(self.aip_uuids))
        # assert cleanup?

    @patch('storer.routines.ParseMETSRoutine.parse_mets')
    def test_parse_routine_dip(self, mock_parse):
        """Ensures DIPs are correctly parsed."""
        self.copy_binaries(filter='.tar')
        internal_sender_identifier = '12345'
        archivesspace_uri = 'repositories/2/archival_objects/1'
        origin = 'aurora'
        mimetypes = {"foo": "bar"}
        mock_parse.return_value = {
            "internal_sender_identifier": internal_sender_identifier,
            "archivesspace_uri": archivesspace_uri,
            "origin": origin,
            "mimetypes": mimetypes, }
        self.create_packages_with_status(Package.DOWNLOADED, package_type='dip')
        for _ in range(len(self.dip_uuids)):
            msg, count = ParseMETSRoutine().run()
            self.assertNotEqual(False, msg, "Packages not stored correctly")
            self.assertEqual("METS data parsed.", msg)
        for package in Package.objects.all():
            self.assertEqual(package.mimetypes, mimetypes)
            self.assertEqual(package.internal_sender_identifier, internal_sender_identifier)
            self.assertEqual(package.origin, origin)
            self.assertEqual(package.archivesspace_uri, archivesspace_uri)
        self.assertEqual(len(Package.objects.filter(process_status=Package.METS_PARSED)), len(self.dip_uuids))
        self.assertEqual(mock_parse.call_count, len(self.dip_uuids))
        # assert cleanup?

    @patch('storer.routines.ParseMETSRoutine.parse_mets')
    @patch('amclient.AMClient.extract_file')
    def test_parse_routine_remote(self, mock_extract, mock_parse):
        """Ensures remote packages are correctly parsed."""
        self.copy_binaries(filter='.7z')
        internal_sender_identifier = '12345'
        archivesspace_uri = 'repositories/2/archival_objects/1'
        origin = 'aurora'
        mimetypes = {"foo": "bar"}
        mock_parse.return_value = {
            "internal_sender_identifier": internal_sender_identifier,
            "archivesspace_uri": archivesspace_uri,
            "origin": origin,
            "mimetypes": mimetypes, }
        self.create_packages_with_status(Package.DOWNLOADED)
        for package in Package.objects.all():
            package.data['current_location'] = "/api/v2/location/7662e69a-6b4f-4a83-825f-ce3b92006968/"
            package.save()
        for _ in range(len(self.dip_uuids)):
            msg, count = ParseMETSRoutine().run()
            self.assertNotEqual(False, msg, "Packages not stored correctly")
            self.assertEqual("METS data parsed.", msg)
        for package in Package.objects.all():
            self.assertEqual(package.mimetypes, mimetypes)
            self.assertEqual(package.internal_sender_identifier, internal_sender_identifier)
            self.assertEqual(package.origin, origin)
            self.assertEqual(package.archivesspace_uri, archivesspace_uri)
        self.assertEqual(len(Package.objects.filter(process_status=Package.STORED)), len(self.aip_uuids))
        self.assertEqual(mock_parse.call_count, len(self.aip_uuids))
        self.assertEqual(mock_extract.call_count, len(self.aip_uuids))
        # assert cleanup?

    def test_parse_mets(self):
        """Ensures METS files are parsed correctly."""
        for mets_file, expected in [
            ('METS.56ce5517-dc77-4cb9-bb4d-97210476f89b.xml',
             {
                'internal_sender_identifier': '0c800188-f990-4502-b9d3-36e7dfb83a1d',
                'archivesspace_uri': None,
                'origin': 'aurora',
                'mimetypes': {
                    '736dc7bc-5913-41f0-adc6-f868a7c84ea2': 'application/octet-stream',
                    'f9472829-43b7-4ef5-b10a-1f974e6da337': 'application/octet-stream',
                    '12cded33-cc4f-44e2-be59-824c46e49bf3': 'application/octet-stream',
                    '18357d28-5f69-471e-8ef1-c706a8026e01': 'application/octet-stream',
                    'aac7f3b4-eed3-4a8f-81bd-b9328a587dd5': 'application/octet-stream',
                    '1ad164b5-91f5-412e-a41e-b31ba69e1d0b': 'application/octet-stream',
                    '68ca0426-62bb-44ca-a0f3-7427526d54ff': 'application/octet-stream',
                    '5e503a0c-e5c8-4437-a99b-bfc0957bbf42': 'application/octet-stream',
                    '4a3b0944-7cd9-4fdc-8e69-35ea57c26152': 'application/octet-stream',
                    '5b937c1f-459a-4a06-8b29-3344205f2a21': 'application/octet-stream',
                    '9912378b-b481-4022-b617-8433a1869e82': 'application/octet-stream'}}),
            ('METS.ddef17b8-0434-41d3-93d5-a89c63d38556.xml',
             {
                 'internal_sender_identifier': '6b3c7d3d-c037-4542-9951-f8db45a4e89b',
                 'archivesspace_uri': None,
                 'origin': 'aurora',
                 'mimetypes': {
                     '41c06bf0-6003-4c09-afea-ab15a769f198': 'application/octet-stream',
                     'b88e7081-f565-4d1b-b785-5c9cd0fd2e17': 'application/octet-stream',
                     '03246b9e-1616-4053-a33e-11c3581de328': 'application/octet-stream',
                     '1bed3fb6-b354-4377-9612-2c6dbe8648eb': 'application/octet-stream'}})
        ]:
            output = ParseMETSRoutine().parse_mets(join('fixtures', 'mets', mets_file))
            self.assertEqual(output, expected)

    def test_parse_routine_get_end_status(self):
        """Ensures end_status is correctly determined from packages."""
        for location, expected_status in [
            ('/api/v2/location/7662e69a-6b4f-4a83-825f-ce3b92006968/', Package.STORED),
                ('/api/v2/location/7662e69a-6b4f-4a83-825f-ce3b92006969/', Package.METS_PARSED)]:
            package = Package.objects.create(
                archivematica_identifier='b663b040-5718-427c-ac84-26fc48191072',
                process_status=Package.CREATED,
                data={'current_location': location}
            )
            end_status = ParseMETSRoutine().get_end_status(package)
            self.assertEqual(end_status, expected_status)

    @patch('storer.clients.FedoraClient.create_container')
    @patch('storer.clients.FedoraClient.create_binary')
    def test_store_routine_aip(self, mock_binary, mock_container):
        """Ensures AIPs are correctly stored."""
        repo = fcrepo.Repository(root=settings.FEDORA['baseurl'],
                                 username=settings.FEDORA['username'],
                                 password=settings.FEDORA['password'])
        mock_container.return_value = pcdm.PCDMObject(repo=repo)
        mock_binary.return_value = pcdm.PCDMFile(repo=repo)
        self.copy_binaries(filter='.7z')
        self.create_packages_with_status(Package.METS_PARSED)
        for _ in range(len(self.aip_uuids)):
            msg, count = StoreRoutine().run()
            self.assertNotEqual(False, msg, "Packages not stored correctly")
            self.assertEqual("Package stored.", msg)
        self.assertEqual(len(Package.objects.filter(process_status=Package.STORED)), len(self.aip_uuids))
        self.assertEqual(len(listdir(settings.TMP_DIR)), 0)
        self.assertEqual(mock_container.call_count, len(self.aip_uuids))
        self.assertEqual(mock_binary.call_count, len(self.aip_uuids))

    @patch('storer.clients.FedoraClient.create_container')
    @patch('storer.clients.FedoraClient.create_binary')
    def test_store_routine_dip(self, mock_binary, mock_container):
        """Ensures DIPs are correctly stored."""
        repo = fcrepo.Repository(root=settings.FEDORA['baseurl'],
                                 username=settings.FEDORA['username'],
                                 password=settings.FEDORA['password'])
        mock_container.return_value = pcdm.PCDMObject(repo=repo)
        mock_binary.return_value = pcdm.PCDMFile(repo=repo)
        self.copy_binaries(filter='.tar')
        self.create_packages_with_status(Package.METS_PARSED, package_type='dip')
        for _ in range(len(self.dip_uuids)):
            msg, count = StoreRoutine().run()
            self.assertNotEqual(False, msg, "Packages not stored correctly")
            self.assertEqual("Package stored.", msg)
        self.assertEqual(len(Package.objects.filter(process_status=Package.STORED)), len(self.dip_uuids))
        self.assertEqual(len(listdir(settings.TMP_DIR)), 0)
        self.assertEqual(mock_container.call_count, len(self.dip_uuids))
        self.assertEqual(mock_binary.call_count, 14)

    @patch('storer.helpers.send_post_request')
    def test_deliver_routine(self, mock_post):
        """Ensures packages are correctly stored."""
        self.create_packages_with_status(Package.STORED)
        msg, count = DeliverRoutine().run()
        self.assertEqual(len(count), len(self.aip_uuids))
        self.assertNotEqual(False, msg, "Packages not stored correctly")
        self.assertEqual("All package data delivered.", msg)
        self.assertEqual(len(Package.objects.filter(process_status=Package.DELIVERED)), len(self.aip_uuids))

    @patch('storer.helpers.send_post_request')
    def test_cleanup_routine(self, mock_post):
        """Ensures packages are correctly cleaned up."""
        mock_post.status_code = 200
        self.create_packages_with_status(Package.DELIVERED)
        msg, count = CleanupRequester().run()
        self.assertEqual(len(count), len(self.aip_uuids))
        self.assertNotEqual(False, msg, "Packages not stored correctly")
        self.assertEqual("Requests sent to clean up Packages.", msg)
        self.assertEqual(len(Package.objects.filter(process_status=Package.CLEANED_UP)), len(self.aip_uuids))

    def tearDown(self):
        if isdir(settings.TMP_DIR):
            rmtree(settings.TMP_DIR)


class PackageRoutineViewsTestCase(TestCase):
    def setUp(self):
        if isdir(settings.TMP_DIR):
            rmtree(settings.TMP_DIR)
        makedirs(settings.TMP_DIR)

    def assert_routine_called(self, patched_routine, view_str):
        """Helper to test routine views."""
        patched_routine.return_value = ("Success message", "uuid")
        self.client.post(reverse(view_str))
        patched_routine.assert_called_once()

    @patch('storer.routines.AddDataRoutine.run')
    def test_add_data_view(self, mock_routine):
        self.assert_routine_called(mock_routine, 'add-data')

    @patch('storer.routines.DownloadRoutine.run')
    def test_download_view(self, mock_routine):
        self.assert_routine_called(mock_routine, 'download-package')

    @patch('storer.routines.ParseMETSRoutine.run')
    def test_parse_view(self, mock_routine):
        self.assert_routine_called(mock_routine, 'parse-mets')

    @patch('storer.routines.StoreRoutine.run')
    def test_store_view(self, mock_routine):
        self.assert_routine_called(mock_routine, 'store-package')

    @patch('storer.routines.DeliverRoutine.run')
    def test_deliver_view(self, mock_routine):
        self.assert_routine_called(mock_routine, 'deliver-packages')

    @patch('storer.routines.CleanupRequester.run')
    def test_cleanup_request_view(self, mock_routine):
        self.assert_routine_called(mock_routine, 'request-cleanup')

    def tearDown(self):
        if isdir(settings.TMP_DIR):
            rmtree(settings.TMP_DIR)


class PackageViewsTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_create_view(self):
        """Ensures objects are correctly created via PackageViewSet."""
        for data, expected_status in [
                ({"uuid": "12345"}, 400), ({"identifier": "12345"}, 201), ({"identifier": "12345"}, 400)]:
            request = self.factory.post(reverse('package-list'), data, format="json")
            response = PackageViewSet.as_view(actions={"post": "create"})(request)
            self.assertEqual(response.status_code, expected_status, "Wrong HTTP code")

    def test_schema(self):
        schema = self.client.get(reverse('schema'))
        self.assertEqual(schema.status_code, 200, "Wrong HTTP code")

    def test_health_check(self):
        status = self.client.get(reverse('ping'))
        self.assertEqual(status.status_code, 200, "Wrong HTTP code")
