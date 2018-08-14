from rest_framework import serializers
from transformer.models import SourceObject, ConsumerObject, Identifier


class IdentifierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Identifier
        exclude = ('id', 'consumer_object')


class SourceObjectSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = SourceObject
        fields = ('url', 'type', 'source', 'process_status', 'data', 'created', 'last_modified')


class SourceObjectListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = SourceObject
        exclude = ('data',)


class ConsumerObjectSerializer(serializers.HyperlinkedModelSerializer):
    identifiers = IdentifierSerializer(source='source_identifier', many=True)

    class Meta:
        model = ConsumerObject
        fields = ('url', 'type', 'source_object', 'consumer', 'identifiers', 'data', 'created', 'last_modified')


class ConsumerObjectListSerializer(serializers.HyperlinkedModelSerializer):
    identifiers = IdentifierSerializer(source='source_identifier', many=True)

    class Meta:
        model = ConsumerObject
        exclude = ('data',)
