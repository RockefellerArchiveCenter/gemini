from os import listdir, access, W_OK
from os.path import basename, isdir, join, splitext
from xml.etree import ElementTree as ET
import zipfile

from gemini import settings

from storer.clients import FedoraClient, ArchivematicaClient
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
        self.am_client = ArchivematicaClient(settings.ARCHIVEMATICA['username'],
                                             settings.ARCHIVEMATICA['api_key'],
                                             settings.ARCHIVEMATICA['baseurl'])

    def run(self):
        package_ids = []
        for package in self.am_client.retrieve_paged('file/'):
            self.uuid = package['uuid']
            if (package['origin_pipeline'].split('/')[-2] == settings.ARCHIVEMATICA['pipeline_uuid'] and
               package['status'] == 'UPLOADED'):
                if not Package.objects.filter(data__uuid=self.uuid).exists():
                    try:
                        self.download = self.download_package(package)
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

    def download_package(self, package_json):
        response = self.am_client.retrieve('/file/{}/download/'.format(self.uuid), stream=True)
        extension = splitext(package_json['current_path'])[1]
        if not extension:
            extension = '.tar'
        with open(join(self.tmp_dir, '{}{}'.format(self.uuid, extension)), "wb") as package:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    package.write(chunk)
        return package


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

            mets_data = self.parse_mets()

            try:
                container = self.fedora_client.create_container(self.uuid)
                getattr(self, 'store_{}'.format(package.type))(package.data, container, mets_data['mimetypes'])
            except Exception as e:
                raise RoutineError("Error storing data: {}".format(e), self.uuid)

            if self.url:
                try:
                    helpers.send_post_request(
                        self.url,
                        {
                            'identifier': mets_data['internal_sender_identifier'],
                            'uri': container.uri_as_string(),
                            'package_type': package.type,
                            'origin': mets_data['origin'],
                            'archivesspace_uri': mets_data['archivesspace_uri'],
                        }
                    )
                except Exception as e:
                    raise RoutineError("Error sending POST request to {}: {}".format(self.url, e), self.uuid)

            package.internal_sender_identifier = mets_data['internal_sender_identifier']
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
            mets_data = {}
            mets = helpers.extract_file(join(self.tmp_dir, "{}{}".format(self.uuid, self.extension)), self.mets_path, join(self.tmp_dir, "METS.{}.xml".format(self.uuid)))
            ns = {'mets': 'http://www.loc.gov/METS/', 'premis': 'info:lc/xmlns/premis-v2', 'fits': 'http://hul.harvard.edu/ois/xml/ns/fits/fits_output'}
            tree = ET.parse(mets)
            bagit_root = tree.find("mets:amdSec/mets:sourceMD/mets:mdWrap[@OTHERMDTYPE='BagIt']/mets:xmlData/transfer_metadata", ns)
            mets_data['internal_sender_identifier'] = self.findtext_with_exception(bagit_root, "Internal-Sender-Identifier", ns)
            mets_data['archivesspace_uri'] = bagit_root.findtext("ArchivesSpace-URI", namespaces=ns)
            mets_data['origin'] = bagit_root.findtext("Origin", default="aurora", namespaces=ns)
            files_root = tree.findall('mets:amdSec/mets:techMD/mets:mdWrap[@MDTYPE="PREMIS:OBJECT"]/mets:xmlData/premis:object', ns)
            mimetypes = {}
            for f in files_root:
                uuid = self.findtext_with_exception(f, 'premis:objectIdentifier/premis:objectIdentifierValue', ns)
                identity = f.find('premis:objectCharacteristics/premis:objectCharacteristicsExtension/', ns)
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

    def clean_up(self, uuid):
        for d in listdir(self.tmp_dir):
            if uuid in d:
                helpers.remove_file_or_dir(join(self.tmp_dir, d))

    def store_aip(self, package, container, mimetypes):
        """
        Stores an AIP as a single binary in Fedora and handles the resulting URI.
        Assumes AIPs are stored as a compressed package.
        """
        self.fedora_client.create_binary(join(self.tmp_dir, "{}{}".format(self.uuid, self.extension)), container, 'application/x-7z-compressed')

    def store_dip(self, package, container, mimetypes):
        """
        Stores a DIP as multiple binaries in Fedora and handles the resulting URI.
        Matches the file UUID (the first 36 characters of the filename) against
        the mimetypes dictionary to find the relevant mimetype.
        """
        for f in listdir(join(self.extracted, 'objects')):
            mimetype = mimetypes[f[0:36]]
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
