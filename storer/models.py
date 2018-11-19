from django.contrib.postgres.fields import JSONField
from django.db import models


class Package(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    TYPE_CHOICES = (
        ('aip', 'Archival Information Package'),
        ('dip', 'Dissemination Information Package'),
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    data = JSONField()
    DOWNLOADED = 10
    STORED = 20
    CLEANED_UP = 30
    PROCESS_STATUS_CHOICES = (
        (DOWNLOADED, 'Package downloaded'),
        (STORED, 'Package stored'),
        (CLEANED_UP, 'Package cleaned up')
    )
    process_status = models.CharField(max_length=50, choices=PROCESS_STATUS_CHOICES, default=10)
    internal_sender_identifier = models.CharField(max_length=60, null=True, blank=True)
