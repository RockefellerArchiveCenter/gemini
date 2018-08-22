from django.contrib.postgres.fields import JSONField
from django.db import models


class AbstractObject(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    TYPE_CHOICES = (
        ('agent', 'Agent'),
        ('collection', 'Collection'),
        ('file', 'File'),
        ('object', 'Object'),
        ('rights', 'Rights'),
        ('term', 'Term'),
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    STATUS_CHOICES = (
        ('10', 'Object updated in source'),
        ('50', 'Object updated in consumer'),
    )
    process_status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    data = JSONField()
