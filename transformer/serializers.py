from rest_framework import serializers
from transformer.models import AbstractObject


class AbstractObjectSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = AbstractObject
        fields = ('url', 'type', 'process_status', 'data', 'created', 'last_modified')


class AbstractObjectListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = AbstractObject
        exclude = ('data',)
