from rest_framework import serializers
from storer.models import Package


class PackageSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Package
        fields = '__all__'


class PackageListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Package
        exclude = ('data',)
