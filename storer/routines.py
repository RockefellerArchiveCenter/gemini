import tarfile
from os import W_OK, access, listdir
from os.path import basename, isdir, join
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

    def run(self):
        """Main method. Processes only one package at a time."""
        if not Package.objects.filter(process_status=self.in_process_status).exists():
            package = Package.objects.filter(process_status=self.start_status).first()
            if package:
                package.process_status = self.in_process_status
                package.save()
                try:
                    self.handle_package(package)
                    end_status = getattr(self, 'end_status') if hasattr(self, 'end_status') else self.get_end_status(package)
                    package.process_status = end_status
                    package.save()
                    message = self.success_message
                except Exception as e:
                    package.process_status = self.start_status
                    package.save()
                    raise Exception(str(e), package.archivematica_identifier)
            else:
                message = self.idle_message
        else:
            message = "Service currently running"
            package = None
        return (message, [package.archivematica_identifier] if package else None)

    def get_end_status(self, package):
        raise NotImplementedError('get_end_status has not been implemented on this class.')


class AddDataRoutine(Routine):
    start_status = Package.CREATED
    in_process_status = Package.ADDING_DATA
    success_message = "Data added to package."
    idle_message = "No packages waiting for data to be added."

    def get_end_status(self, package):
        """
        Dynamically determines end_status. If package location is not in
        expected list, bypasses download routine.
        """
        location = package.data['current_location'].split('/')[-2]
        return Package.DATA_ADDED if (location in settings.ARCHIVEMATICA['location_uuids']) else Package.DOWNLOADED

    def handle_package(self, package):
        """Gets information about a package from Archivematica."""
        am_client = AMClient(
            ss_api_key=settings.ARCHIVEMATICA['api_key'],
            ss_user_name=settings.ARCHIVEMATICA['username'],
            ss_url=settings.ARCHIVEMATICA['baseurl'],
            directory=self.tmp_dir)

        am_client.package_uuid = package.archivematica_identifier
        package_data = am_client.get_package_details()
        if isinstance(package_data, int):
            raise Exception(errors.error_lookup(package_data))

        package.type = package_data['package_type'].lower()
        package.fedora_uri = package_data['resource_uri']  # this gets overwritten if package is stored in Fedora
        package.data = package_data


class DownloadRoutine(Routine):
    """Downloads a package from Archivematica."""
    start_status = Package.DATA_ADDED
    in_process_status = Package.DOWNLOADING
    end_status = Package.DOWNLOADED
    success_message = "Package downloaded."
    idle_message = "No packages waiting to be downloaded."

    def handle_package(self, package):

        am_client = AMClient(
            ss_api_key=settings.ARCHIVEMATICA['api_key'],
            ss_user_name=settings.ARCHIVEMATICA['username'],
            ss_url=settings.ARCHIVEMATICA['baseurl'],
            directory=self.tmp_dir)

        if self.is_downloadable(package.data):
            try:
                download_path = am_client.download_package(package.archivematica_identifier)
                tmp_path = join(
                    self.tmp_dir, f"{package.archivematica_identifier}{self.get_extension(package.type)}")
                move(download_path, tmp_path)
            except Exception as e:
                raise RoutineError(f"Error downloading data: {e}")
        else:
            raise RoutineError(f"Package {package.archivematica_identifier} is not downloadable")

    def get_extension(self, package_type):
        return '.tar' if package_type == 'dip' else '.7z'

    def is_downloadable(self, package):
        pipeline = package['origin_pipeline'].split('/')[-2]
        return (pipeline in settings.ARCHIVEMATICA['pipeline_uuids'])


class ParseMETSRoutine(Routine):
    """Parses data from a METS file."""
    start_status = Package.DOWNLOADED
    in_process_status = Package.PARSING_METS
    success_message = "METS data parsed."
    idle_message = "No packages waiting for METS parsing."

    def get_end_status(self, package):
        return Package.STORED if self.is_remote_package(package) else Package.METS_PARSED

    def handle_package(self, package):
        self.uuid = package.archivematica_identifier
        self.upload = True

        if self.is_remote_package(package):
            mets_path = self.get_remote_mets(package)
        else:
            mets_path = self.get_mets_from_package(package.type)

        mets_data = self.parse_mets(mets_path)

        package.mimetypes = mets_data['mimetypes']
        package.internal_sender_identifier = mets_data['internal_sender_identifier']
        package.origin = mets_data['origin']
        package.archivesspace_uri = mets_data['archivesspace_uri']
        # TODO do we need to clean up here?

    def is_remote_package(self, package):
        location = package.data['current_location'].split('/')[-2]
        return not (location in settings.ARCHIVEMATICA['location_uuids'])

    def get_remote_mets(self, package):
        mets_path = "METS.{}.xml".format(self.uuid)
        am_client = AMClient(
            ss_api_key=settings.ARCHIVEMATICA['api_key'],
            ss_user_name=settings.ARCHIVEMATICA['username'],
            ss_url=settings.ARCHIVEMATICA['baseurl'],
            package_uuid=self.uuid,
            relative_path=mets_path,
            saveas_filename=mets_path,
            directory=self.tmp_dir)
        am_client.extract_file()
        return join(self.tmp_dir, mets_path)

    def get_mets_from_package(self, package_type):
        if package_type == 'aip':
            extension = '.7z'
            mets_source_path = "METS.{}.xml".format(self.uuid)
        else:
            extension = '.tar'
            tf = tarfile.open(join(self.tmp_dir, "{}.tar".format(self.uuid)))
            mets_source_path = [f for f in tf.getnames() if (basename(f).startswith('METS.') and basename(f).endswith('.xml'))][0]
        return helpers.extract_file(
            join(self.tmp_dir, f"{self.uuid}{extension}"),
            mets_source_path,
            join(self.tmp_dir, "METS.{}.xml".format(self.uuid)))

    def parse_mets(self, mets_path):
        """
        Parses Archivematica's METS file and returns the Internal-Sender-Identifier
        submitted in a bag-info.txt file, as well as a dict of filename UUIDs
        and mimetypes
        """
        try:
            mets_data = {}
            ns = {'mets': 'http://www.loc.gov/METS/', 'fits': 'http://hul.harvard.edu/ois/xml/ns/fits/fits_output'}
            tree = ET.parse(mets_path)
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
            raise RoutineError("No METS file found at {}".format(mets_path))
        except ValueError as e:
            raise RoutineError("Could not find element {} in METS file".format(e))
        except Exception as e:
            raise RoutineError("Error getting data from Archivematica METS file: {}".format(e))

    def findtext_with_exception(self, element, xpath, namespaces):
        ret = element.findtext(xpath, namespaces=namespaces)
        if not ret:
            raise ValueError(xpath)
        return ret

    def get_premis_schemalocation(self, version):
        """Returns a PREMIS schema URL based on the version number provided."""
        return 'http://www.loc.gov/premis/v3' if version.startswith("3.") else 'info:lc/xmlns/premis-v2'

    def clean_up(self, uuid, src_file=False):
        """Removes directories for a given transfer. If `src_file` argument is
        true, removes source file and extracted METS matching the UUID as well."""
        for d in listdir(self.tmp_dir):
            if uuid in d and (src_file or isdir(join(self.tmp_dir, d))):
                remove_file_or_dir(join(self.tmp_dir, d))


class StoreRoutine(Routine):
    """Uploads the contents of a package to Fedora.

    AIPS are uploaded as single 7z files. DIPs are extracted and each file is
    uploaded. Only one package is processed at a time.
    """
    start_status = Package.METS_PARSED
    in_process_status = Package.STORING
    end_status = Package.STORED
    success_message = "Package stored."
    idle_message = "No packages to store."

    def handle_package(self, package):
        self.fedora_client = FedoraClient(root=settings.FEDORA['baseurl'],
                                          username=settings.FEDORA['username'],
                                          password=settings.FEDORA['password'])
        self.uuid = package.archivematica_identifier

        if package.type == 'dip':
            self.extracted = helpers.extract_all(join(self.tmp_dir, "{}.tar".format(self.uuid)), join(self.tmp_dir, self.uuid), self.tmp_dir)

        try:
            container = self.fedora_client.create_container(self.uuid)
            getattr(self, 'store_{}'.format(package.type))(package.data, container, package.mimetypes)
        except Exception as e:
            self.clean_up(self.uuid)
            raise RoutineError("Error storing data: {}".format(e))

        package.fedora_uri = container.uri_as_string()
        self.clean_up(self.uuid, True)

    def clean_up(self, uuid, src_file=False):
        """Removes directories for a given transfer. If `src_file` argument is
        true, removes source file and extracted METS matching the UUID as well."""
        for d in listdir(self.tmp_dir):
            if uuid in d and (src_file or isdir(join(self.tmp_dir, d))):
                remove_file_or_dir(join(self.tmp_dir, d))

    def store_aip(self, package, container, mimetypes):
        """
        Stores an AIP as a single binary in Fedora and handles the resulting URI.
        Assumes AIPs are stored as a compressed package.
        """
        self.fedora_client.create_binary(
            join(self.tmp_dir, f"{self.uuid}.7z"),
            container,
            'application/x-7z-compressed')

    def store_dip(self, package, container, mimetypes):
        """
        Stores a DIP as multiple binaries in Fedora and handles the resulting URI.
        Matches the file UUID (the first 36 characters of the filename) against
        the mimetypes dictionary to find the relevant mimetype.
        """
        for f in listdir(join(self.extracted, 'objects')):
            mimetype = mimetypes[f[0:36]]
            self.fedora_client.create_binary(
                join(self.tmp_dir, self.uuid, 'objects', f),
                container,
                mimetype)


class PostRoutine(object):
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
        msg = self.success_message if len(package_ids) else self.idle_message
        return (msg, package_ids)


class DeliverRoutine(PostRoutine):
    """Delivers package data to next service."""
    start_status = Package.STORED
    end_status = Package.DELIVERED
    url = settings.DELIVERY_URL
    success_message = "All package data delivered."
    idle_message = "No package data waiting to be delivered."

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
    idle_message = "No packages waiting for cleanup."

    def get_data(self, package):
        return {"identifier": package.internal_sender_identifier}
