from asterism.models import BasePackage
from django.db import models


class Package(BasePackage):
    BasePackage._meta.get_field("bag_identifier").blank = True
    BasePackage._meta.get_field("bag_identifier")._unique = False
    DOWNLOADED = 10
    STORED = 20
    DELIVERED = 25
    CLEANED_UP = 30
    PROCESS_STATUS_CHOICES = (
        (DOWNLOADED, 'Package downloaded'),
        (STORED, 'Package stored'),
        (DELIVERED, 'Package data delivered'),
        (CLEANED_UP, 'Package cleaned up')
    )
    internal_sender_identifier = models.CharField(max_length=60, null=True, blank=True)
    fedora_uri = models.CharField(max_length=255, null=True, blank=True)
    archivesspace_uri = models.CharField(max_length=255, null=True, blank=True)
