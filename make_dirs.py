import os

from gemini import settings

if not os.path.isdir(settings.TMP_DIR):
    os.makedirs(dir)
