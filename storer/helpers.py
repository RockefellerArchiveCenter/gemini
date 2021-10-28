import json
import shutil
import tarfile
from os import rename
from os.path import join, splitext

import py7zr
import requests
from gemini import settings


def extract_file(archive, src, dest):
    ext = splitext(archive)[1]
    if ext == '.7z':
        with py7zr.SevenZipFile(archive, 'r') as archive:
            for name in archive.getnames():
                if name.endswith(src):
                    archive.extract(path=settings.TMP_DIR, targets=[name])
                    rename(join(settings.TMP_DIR, name), dest)
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


def extract_all(archive, dest, tmp):
    ext = splitext(archive)[1]
    if ext == '.tar':
        tf = tarfile.open(archive, 'r')
        tf.extractall(tmp)
        tf.close()
        # Archivematica creates DIPs with filenames that don't match their
        # UUIDs, so we have to rename here
        shutil.move(join(tmp, tf.members[0].name), dest)
    else:
        print("Unrecognized archive extension")
        return False
    return dest


def send_post_request(url, data):
    response = requests.post(
        url,
        data=json.dumps(data),
        headers={"Content-Type": "application/json"})
    response.raise_for_status()
