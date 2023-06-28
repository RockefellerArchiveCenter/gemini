from asterism.models import BasePackage
from django.db import models


class Package(BasePackage):
    BasePackage._meta.get_field("bag_identifier").blank = True
    BasePackage._meta.get_field("bag_identifier")._unique = False
    CREATED = 0
    ADDING_DATA = 1
    DATA_ADDED = 2
    DOWNLOADING = 5
    DOWNLOADED = 10
    PARSING_METS = 11
    METS_PARSED = 12
    STORING = 15
    STORED = 20
    DELIVERED = 25
    CLEANED_UP = 30
    PROCESS_STATUS_CHOICES = (
        (CREATED, 'Package created'),
        (DOWNLOADING, 'Package being downloaded'),
        (DOWNLOADED, 'Package downloaded'),
        (STORING, 'Package being stored'),
        (STORED, 'Package stored'),
        (DELIVERED, 'Package data delivered'),
        (CLEANED_UP, 'Package cleaned up')
    )
    archivematica_identifier = models.CharField(max_length=255, null=True, blank=True)
    internal_sender_identifier = models.CharField(max_length=60, null=True, blank=True)
    fedora_uri = models.CharField(max_length=255, null=True, blank=True)
    archivesspace_uri = models.CharField(max_length=255, null=True, blank=True)
    mimetypes = models.JSONField(null=True, blank=True)
