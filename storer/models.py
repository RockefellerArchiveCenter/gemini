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