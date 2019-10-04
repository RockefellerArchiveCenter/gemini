import json
from os.path import basename, splitext, join, isfile
import py7zlib
import re
import requests
import shutil
import tarfile


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
    try:
        ext = splitext(archive)[1]
        if ext == '.7z':
            fp = open(archive, 'rb')
            a = py7zlib.Archive7z(fp)
            for name in a.getnames():
                if name.endswith(src):
                    outfile = open(dest, 'wb')
                    outfile.write(a.getmember(name).read())
                    outfile.close()
            fp.close()
        elif ext == '.tar':
            tf = tarfile.open(archive, mode="r")
            for member in tf.getmembers():
                if member.name.endswith(src):
                    outfile = open(dest, 'wb')
                    extracted = tf.extractfile(member)
                    outfile.write(extracted.read())
                    outfile.close()
            tf.close()
        else:
            print("Unrecognized archive extension")
            return False
        return dest
    except Exception as e:
        raise Exception("extract error: {}".format(e))


def extract_all(archive, dest, tmp):
    ext = splitext(archive)[1]
    if ext == '.tar':
        tf = tarfile.open(archive, 'r')
        tf.extractall(tmp)
        tf.close()
        # Archivematica creates DIPs with filenames that don't match their UUIDs, so we have to rename here
        shutil.move(join(tmp, tf.members[0].name), dest)
    else:
        print("Unrecognized archive extension")
        return False
    return dest


def send_post_request(url, data):
    try:
        response = requests.post(
            url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"})
    except Exception as e:
        raise Exception(e)
