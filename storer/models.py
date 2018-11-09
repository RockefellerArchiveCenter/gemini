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
    PROCESS_STATUS_CHOICES = (
        (10, 'Package downloaded'),
        (20, 'Package stored')
    )
    process_status = models.CharField(max_length=50, choices=PROCESS_STATUS_CHOICES, default=10)
