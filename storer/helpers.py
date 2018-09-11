from os.path import splitext, join, isfile
import py7zlib
import re
import shutil
import tarfile

from gemini import settings

# from Aurora files_helper.py
def get_fields_from_file(fpath):
    fields = {}
    try:
        patterns = [
            '(?P<key>[\w\-]+)',
            '(?P<val>.+)'
        ]
        with open(fpath, 'r') as f:
            for line in f.readlines():
                line = line.strip('\n')

                row_search = re.search(":?(\s)?".join(patterns), line)
                if row_search:
                    key = row_search.group('key').replace('-','_').strip()
                    val = row_search.group('val').strip()
                    if key in fields:
                        listval = [fields[key]]
                        listval.append(val)
                        fields[key] = listval
                    else:
                        fields[key] = val
    except Exception as e:
        print(e)

    return fields


def extract_file(archive, src, dest):
    ext = splitext(archive)[1]
    if ext == '.7z':
        fp = open(archive, 'rb')
        a = py7zlib.Archive7z(fp)
        for name in a.getnames():
            if name.endswith(src):
                outfile = open(dest, 'wb')
                outfile.write(a.getmember(name).read())
        outfile.close()
    elif ext == '.tar':
        tf = tarfile.open(archive, mode="r")
        for name in tf.getmembers():
            if name.endswith(src):
                tf.extract(name, path=dest)
        tf.close()
    return dest


def extract_all(archive, dest):
    ext = splitext(archive)[1]
    if ext == '.7z':
        pass
    elif ext == '.tar':
        tf = tarfile.open(archive, 'r')
        tf.extractall(settings.TMP_DIR)
        tf.close()
        # Archivematica creates DIPs with filenames that don't match their UUIDs, so we have to rename here
        shutil.move(join(settings.TMP_DIR, tf.members[0].name), dest)
    elif ext == '.zip':
        zip = zipfile.ZipFile(archive, 'r')
        zip.extractall(dest)
        zip.close()
    return dest
