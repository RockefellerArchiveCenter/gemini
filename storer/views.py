from datetime import datetime
import logging
from structlog import wrap_logger
from uuid import uuid4

from django.shortcuts import render

from rest_framework import viewsets, generics, status
from rest_framework.response import Response

from storer.models import Package
from storer.serializers import PackageSerializer, PackageListSerializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class PackageViewSet(viewsets.ModelViewSet):
    """
    Endpoint for packages.

    list:
    Returns a list of packages.

    retrieve:
    Returns a single package, identified by a primary key.
    """
    model = Package
    serializer_class = PackageSerializer
    queryset = Package.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return PackageListSerializer
        return PackageSerializer

    def create(self, request):
        type = 'aip'
        package = Package.objects.create(
            data=request.data['data'],
            type=type
        )
        serializer = PackageSerializer(package, context={'request': request})
        return Response(serializer.data)
