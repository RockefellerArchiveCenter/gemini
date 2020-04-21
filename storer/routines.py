from os import W_OK, access, listdir
from os.path import basename, isdir, join, splitext
from shutil import move
from xml.etree import ElementTree as ET

from amclient import AMClient, errors
from asterism.file_helpers import remove_file_or_dir
from gemini import settings
from storer import helpers
from storer.clients import FedoraClient
from storer.models import Package


class RoutineError(Exception):
    pass


class CleanupError(Exception):
    pass


class Routine:
    """
    Base class for routines which checks existence and permissions of tmp directory.
    """

    def __init__(self):
        self.tmp_dir = settings.TMP_DIR
        if not isdir(self.tmp_dir):
            raise RoutineError('Directory does not exist', self.tmp_dir)
        if not access(self.tmp_dir, W_OK):
            raise RoutineError('Directory does not have write permissions', self.tmp_dir)


class DownloadRoutine(Routine):
    """Downloads a package from Archivematica."""

    def __init__(self, identifier):
        super(DownloadRoutine, self).__init__()
        self.am_client = AMClient(
            ss_api_key=settings.ARCHIVEMATICA['api_key'],
            ss_user_name=settings.ARCHIVEMATICA['username'],
            ss_url=settings.ARCHIVEMATICA['baseurl'],
            directory=self.tmp_dir,
            package_uuid=identifier,
        )
        self.package = self.am_client.get_package_details()
        if isinstance(self.package, int):
            raise Exception(errors.error_lookup(self.package))

    def run(self):
        package = self.am_client.get_package_details()
        if self.is_downloadable(package):
            if not Package.objects.filter(data__uuid=self.am_client.package_uuid).exists():
                try:
                    download_path = self.am_client.download_package(self.am_client.package_uuid)
                    tmp_path = join(
                        self.tmp_dir, '{}{}'.format(self.am_client.package_uuid, self.get_extension(package)))
                    move(download_path, tmp_path)
                except Exception as e:
                    raise RoutineError("Error downloading data: {}".format(e), self.am_client.package_uuid)

                Package.objects.create(
                    type=package['package_type'].lower(),
                    data=package,
                    process_status=Package.DOWNLOADED
                )
                msg = "Package downloaded."
            else:
                msg = "Package already downloaded."
        else:
            msg = "Package not downloadable."
        return (msg, self.am_client.package_uuid)

    def get_extension(self, package):
        return (splitext(package['current_path'])[1]
                if splitext(package['current_path'])[1]
                else '.tar')

    def is_downloadable(self, package):
        pipeline = package['origin_pipeline'].split('/')[-2]
        return (pipeline == settings.ARCHIVEMATICA['pipeline_uuid'])


class StoreRoutine(Routine):
    """
    Uploads the contents of a package to Fedora.
    AIPS are uploaded as single 7z files. DIPs are extracted and each file is uploaded.
    """

    def __init__(self):
        super(StoreRoutine, self).__init__()
        self.fedora_client = FedoraClient(root=settings.FEDORA['baseurl'],
                                          username=settings.FEDORA['username'],
                                          password=settings.FEDORA['password'])

    def run(self):
        package_ids = []
        for package in Package.objects.filter(process_status=Package.DOWNLOADED):
            self.uuid = package.data['uuid']
            if package.type == 'aip':
                self.extension = '.7z'
                self.mets_path = "METS.{}.xml".format(self.uuid)
            elif package.type == 'dip':
                self.extension = '.tar'
                self.extracted = helpers.extract_all(join(self.tmp_dir, "{}.tar".format(self.uuid)), join(self.tmp_dir, self.uuid), self.tmp_dir)
                self.mets_path = [f for f in listdir(self.extracted) if (basename(f).startswith('METS.') and basename(f).endswith('.xml'))][0]
            else:
                self.clean_up(self.uuid)
                raise RoutineError("Unrecognized package type: {}".format(package.type), self.uuid)

            mets_data = self.parse_mets()

            try:
                container = self.fedora_client.create_container(self.uuid)
                getattr(self, 'store_{}'.format(package.type))(package.data, container, mets_data['mimetypes'])
            except Exception as e:
                self.clean_up(self.uuid)
                raise RoutineError("Error storing data: {}".format(e), self.uuid)

            package.internal_sender_identifier = mets_data['internal_sender_identifier']
            package.fedora_uri = container.uri_as_string()
            package.origin = mets_data['origin']
            package.archivesspace_uri = mets_data['archivesspace_uri']
            package.process_status = Package.STORED
            package.save()

            package_ids.append(self.uuid)

            self.clean_up(self.uuid)

            break

        return ("Packages stored.", package_ids)

    def parse_mets(self):
        """
        Parses Archivematica's METS file and returns the Internal-Sender-Identifier
        submitted in a bag-info.txt file, as well as a dict of filename UUIDs
        and mimetypes
        """
        try:
            mets_data = {}
            mets = helpers.extract_file(join(self.tmp_dir, "{}{}".format(
                self.uuid, self.extension)), self.mets_path,
                join(self.tmp_dir, "METS.{}.xml".format(self.uuid)))
            ns = {'mets': 'http://www.loc.gov/METS/', 'fits': 'http://hul.harvard.edu/ois/xml/ns/fits/fits_output'}
            tree = ET.parse(mets)
            bagit_root = tree.find("mets:amdSec/mets:sourceMD/mets:mdWrap[@OTHERMDTYPE='BagIt']/mets:xmlData/transfer_metadata", ns)
            mets_data['internal_sender_identifier'] = self.findtext_with_exception(bagit_root, "Internal-Sender-Identifier", ns)
            mets_data['archivesspace_uri'] = bagit_root.findtext("ArchivesSpace-URI", namespaces=ns)
            mets_data['origin'] = bagit_root.findtext("Origin", default="aurora", namespaces=ns)
            files_root = tree.findall('mets:amdSec/mets:techMD/mets:mdWrap[@MDTYPE="PREMIS:OBJECT"]/mets:xmlData/', ns)
            mimetypes = {}
            for f in files_root:
                ns['premis'] = self.get_premis_schemalocation(f.attrib['version'])
                uuid = f.find('premis:objectIdentifier/premis:objectIdentifierValue', ns).text
                identity = f.find('premis:objectCharacteristics/premis:objectCharacteristicsExtension/fits:fits/fits:identification/fits:identity', ns)
                mtype = identity.attrib.get('mimetype', 'application/octet-stream') if identity else 'application/octet-stream'
                mimetypes.update({uuid: mtype})
            mets_data['mimetypes'] = mimetypes
            return mets_data
        except FileNotFoundError:
            raise RoutineError("No METS file found at {}".format(self.mets_path), self.uuid)
        except ValueError as e:
            raise RoutineError("Could not find element {} in METS file".format(e), self.uuid)
        except Exception as e:
            raise RoutineError("Error getting data from Archivematica METS file: {}".format(e), self.uuid)

    def findtext_with_exception(self, element, xpath, namespaces):
        ret = element.findtext(xpath, namespaces=namespaces)
        if not ret:
            raise ValueError(xpath)
        return ret

    def get_premis_schemalocation(self, version):
        """Returns a PREMIS schema URL based on the version number provided."""
        return 'http://www.loc.gov/premis/v3' if version.startswith("3.") else 'info:lc/xmlns/premis-v2'

    def clean_up(self, uuid):
        """Removes files and directories for a given transfer."""
        for d in listdir(self.tmp_dir):
            if uuid in d:
                remove_file_or_dir(join(self.tmp_dir, d))

    def store_aip(self, package, container, mimetypes):
        """
        Stores an AIP as a single binary in Fedora and handles the resulting URI.
        Assumes AIPs are stored as a compressed package.
        """
        self.fedora_client.create_binary(join(self.tmp_dir, "{}{}".format(
            self.uuid, self.extension)), container, 'application/x-7z-compressed')

    def store_dip(self, package, container, mimetypes):
        """
        Stores a DIP as multiple binaries in Fedora and handles the resulting URI.
        Matches the file UUID (the first 36 characters of the filename) against
        the mimetypes dictionary to find the relevant mimetype.
        """
        for f in listdir(join(self.extracted, 'objects')):
            mimetype = mimetypes[f[0:36]]
            self.fedora_client.create_binary(join(self.tmp_dir, self.uuid, 'objects', f), container, mimetype)


class PostRoutine:
    """Base Routine for sending POST requests to another service. Exposes a
    `get_data()` method for adding data into POST requests."""

    def run(self):
        package_ids = []
        for package in Package.objects.filter(process_status=self.start_status):
            try:
                data = self.get_data(package)
                helpers.send_post_request(self.url, data)
            except Exception as e:
                raise RoutineError(
                    "Error sending POST request to {}: {}".format(
                        self.url, e), package.internal_sender_identifier)
            package.process_status = self.end_status
            package.save()
            package_ids.append(package.internal_sender_identifier)
        return (self.success_message, package_ids)


class DeliverRoutine(PostRoutine):
    """Delivers package data to next service."""
    start_status = Package.STORED
    end_status = Package.DELIVERED
    url = settings.DELIVERY_URL
    success_message = "Package data delivered."

    def get_data(self, package):
        return {'identifier': package.internal_sender_identifier,
                'uri': package.fedora_uri,
                'package_type': package.type,
                'origin': package.origin,
                'archivesspace_uri': package.archivesspace_uri}


class CleanupRequester(PostRoutine):
    """Requests cleanup of packages from previous service."""
    start_status = Package.DELIVERED
    end_status = Package.CLEANED_UP
    url = settings.CLEANUP_URL
    success_message = "Requests sent to clean up Packages."

    def get_data(self, package):
        return {"identifier": package.internal_sender_identifier}
