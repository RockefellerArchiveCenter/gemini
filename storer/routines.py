from os import listdir, access, W_OK
from os.path import basename, isdir, join, splitext
from shutil import move

from amclient import AMClient
from xml.etree import ElementTree as ET

from gemini import settings
from storer.clients import FedoraClient
from storer import helpers
from storer.models import Package


class RoutineError(Exception): pass
class CleanupError(Exception): pass


class Routine:
    """Base class for routines which checks existence and permissions of directories."""
    def __init__(self, dirs):
        self.tmp_dir = dirs['tmp'] if dirs else settings.TMP_DIR
        if not isdir(self.tmp_dir):
            raise RoutineError('Directory does not exist', self.tmp_dir)
        if not access(self.tmp_dir, W_OK):
            raise RoutineError('Directory does not have write permissions', self.tmp_dir)


class DownloadRoutine(Routine):
    """Downloads a package from Archivematica."""

    def __init__(self, dirs):
        super(DownloadRoutine, self).__init__(dirs)
        self.am_client = AMClient(
            ss_api_key=settings.ARCHIVEMATICA['api_key'],
            ss_user_name=settings.ARCHIVEMATICA['username'],
            ss_url=settings.ARCHIVEMATICA['baseurl'],
            directory=self.tmp_dir,
        )

    def run(self):
        package_ids = []
        for package in self.am_client.get_all_packages(params={}):
            self.uuid = package['uuid']
            if self.is_downloadable(package):
                if not Package.objects.filter(data__uuid=self.uuid).exists():
                    try:
                        download = self.am_client.download_package(self.uuid)
                        move(download, join(self.tmp_dir,
                             '{}{}'.format(self.uuid, self.get_extension(package))))
                    except Exception as e:
                        raise RoutineError("Error downloading data: {}".format(e), self.uuid)

                    Package.objects.create(
                        type=package['package_type'].lower(),
                        data=package,
                        process_status=Package.DOWNLOADED
                    )
                    package_ids.append(self.uuid)
                    break
        return ("All packages downloaded.", package_ids)

    def get_extension(self, package):
        return (splitext(package['current_path'])[1]
                if splitext(package['current_path'])[1]
                else '.tar')

    def is_downloadable(self, package):
        return (package['origin_pipeline'].split('/')[-2] == settings.ARCHIVEMATICA['pipeline_uuid'] and
               package['status'] == 'UPLOADED')


class StoreRoutine(Routine):
    """
    Uploads the contents of a package to Fedora.
    AIPS are uploaded as single 7z files. DIPs are extracted and each file is uploaded.
    """
    def __init__(self, url, dirs):
        super(StoreRoutine, self).__init__(dirs)
        self.url = url
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
                raise RoutineError("Unrecognized package type: {}".format(package.type), self.uuid)

            package.internal_sender_identifier, self.mimetypes, origin, archivesspace_uri = self.parse_mets()

            try:
                container = self.fedora_client.create_container(self.uuid)
                getattr(self, 'store_{}'.format(package.type))(package.data, container)
            except Exception as e:
                raise RoutineError("Error storing data: {}".format(e), self.uuid)

            if self.url:
                try:
                    helpers.send_post_request(
                        self.url,
                        {
                            'identifier': package.internal_sender_identifier,
                            'uri': container.uri_as_string(),
                            'package_type': package.type,
                            'origin': origin,
                            'archivesspace_uri': archivesspace_uri,
                        }
                    )
                except Exception as e:
                    raise RoutineError("Error sending post callback: {}".format(e), self.uuid)

            package.process_status = Package.STORED
            package.save()

            package_ids.append(self.uuid)

            try:
                self.clean_up(self.uuid)
            except Exception as e:
                raise RoutineError("Error cleaning up: {}".format(e), self.uuid)

            break

        return ("Packages stored.", package_ids)

    def parse_mets(self):
        """
        Parses Archivematica's METS file and returns the Internal-Sender-Identifier
        submitted in a bag-info.txt file, as well as a dict of filename UUIDs
        and mimetypes
        """
        try:
            mimetypes = {}
            mets = helpers.extract_file(join(self.tmp_dir, "{}{}".format(self.uuid, self.extension)), self.mets_path, join(self.tmp_dir, "METS.{}.xml".format(self.uuid)))
            tree = ET.parse(mets)
            root = tree.getroot()
            ns = {'mets': 'http://www.loc.gov/METS/', 'premis': 'info:lc/xmlns/premis-v2', 'fits': 'http://hul.harvard.edu/ois/xml/ns/fits/fits_output'}
            bagit_root = "mets:amdSec/mets:sourceMD/mets:mdWrap[@OTHERMDTYPE='BagIt']/mets:xmlData/transfer_metadata/"
            internal_sender_identifier = root.findtext("{}/Internal-Sender-Identifier".format(bagit_root), namespaces=ns)
            origin = root.findtext("{}/Origin".format(bagit_root), namespaces=ns)
            archivesspace_uri = root.findtext("{}/ArchivesSpace-URI".format(bagit_root), namespaces=ns)
            files = root.findall('mets:amdSec/mets:techMD/mets:mdWrap[@MDTYPE="PREMIS:OBJECT"]/mets:xmlData/premis:object', ns)
            for f in files:
                uuid = f.findtext('premis:objectIdentifier/premis:objectIdentifierValue', namespaces=ns)
                identity = f.find('premis:objectCharacteristics/premis:objectCharacteristicsExtension/', ns)
                mtype = identity.attrib.get('mimetype', 'application/octet-stream') if identity else 'application/octet-stream'
                mimetypes.update({uuid: mtype})
            return internal_sender_identifier, mimetypes, origin, archivesspace_uri
        except Exception as e:
            raise RoutineError("Error getting data from Archivematica METS file: {}".format(e), self.uuid)

    def clean_up(self, uuid):
        for d in listdir(self.tmp_dir):
            if uuid in d:
                helpers.remove_file_or_dir(join(self.tmp_dir, d))

    def store_aip(self, package, container):
        """
        Stores an AIP as a single binary in Fedora and handles the resulting URI.
        Assumes AIPs are stored as a compressed package.
        """
        self.fedora_client.create_binary(join(self.tmp_dir, "{}{}".format(self.uuid, self.extension)), container, 'application/x-7z-compressed')

    def store_dip(self, package, container):
        """
        Stores a DIP as multiple binaries in Fedora and handles the resulting URI.
        Matches the file UUID (the first 36 characters of the filename) against
        the mimetypes dictionary to find the relevant mimetype.
        """
        for f in listdir(join(self.extracted, 'objects')):
            mimetype = self.mimetypes[f[0:36]]
            self.fedora_client.create_binary(join(self.tmp_dir, self.uuid, 'objects', f), container, mimetype)


class CleanupRequester:
    def __init__(self, url):
        self.url = url

    def run(self):
        package_ids = []
        for package in Package.objects.filter(process_status=Package.STORED):
            try:
                helpers.send_post_request(self.url, {"identifier": package.internal_sender_identifier})
            except Exception as e:
                raise CleanupError("Error sending cleanup request: {}".format(e), package.internal_sender_identifier)
            package.process_status = Package.CLEANED_UP
            package.save()
            package_ids.append(package.internal_sender_identifier)
        return ("Requests sent to clean up Packages.", package_ids)
