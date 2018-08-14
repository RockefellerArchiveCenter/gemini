from django.contrib.postgres.fields import JSONField
from django.db import models


class DataObject(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    TYPE_CHOICES = (
        ('accession', 'Accession'),
        ('agent', 'Agent'),
        ('component', 'Component'),
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    data = JSONField()


class SourceObject(DataObject):
    SOURCE_CHOICES = (
        ('aurora', 'Aurora'),
    )
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    STATUS_CHOICES = (
        ('10', 'Object saved in ArchivesSpace'),
        ('30', 'Associated grouping component saved in ArchivesSpace'),
        ('50', 'Associated transfers saved in ArchivesSpace'),
    )
    process_status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    def __str__(self):
        return '{} {} {}'.format(self.source, self.type, self.id)


class ConsumerObject(DataObject):
    source_object = models.ForeignKey(SourceObject, on_delete=models.CASCADE, related_name='source_object')
    CONSUMER_CHOICES = (
        ('archivesspace', 'ArchivesSpace'),
        ('fedora', 'Fedora')
    )
    consumer = models.CharField(max_length=50, choices=CONSUMER_CHOICES)

    def __str__(self):
        return '{} {} {}'.format(self.consumer, self.type, self.id)

    def initial_save(self, consumer_data, identifier, type, source_object=None, source_data=None):
        if not source_object:
            source_object = SourceObject.objects.create(
                source='aurora',
                type=type,
                data=source_data,
                process_status=10,
            )
        consumer_object = ConsumerObject.objects.create(
            consumer='archivesspace',
            type=type,
            source_object=source_object,
            data=consumer_data,
        )
        identifier = Identifier.objects.create(
            source='archivesspace',
            identifier=identifier,
            consumer_object=consumer_object,
        )
        return consumer_object


class Identifier(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    SOURCE_CHOICES = (
        ('aurora', 'Aurora'),
        ('archivesspace', 'ArchivesSpace'),
        ('fedora', 'Fedora'),
    )
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    identifier = models.CharField(max_length=200)
    consumer_object = models.ForeignKey(ConsumerObject, on_delete=models.CASCADE, related_name='source_identifier')

    def __str__(self):
        return self.identifier
