from datetime import datetime
import logging
from structlog import wrap_logger
from uuid import uuid4

from django.shortcuts import render
from gemini import settings

from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.response import Response

from storer.models import Package
from storer.routines import AIPRoutine, DIPRoutine
from storer.serializers import PackageSerializer, PackageListSerializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class PackageViewSet(ReadOnlyModelViewSet):
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


class DownloadView(APIView):
    """Downloads AIPs and/or DIPs. Accepts POST requests only."""

    def post(self, request, format=None, *args, **kwargs):
        log = logger.new(transaction_id=str(uuid4()))
        package_type = self.kwargs.get('package')
        dirs = None
        if request.POST.get('test'):
            dirs = {'tmp': settings.TEST_TMP_DIR}
        try:
            if package_type == 'aips':
                AIPRoutine(dirs).download()
                return Response({"detail": "AIP download routine complete."}, status=200)
            elif package_type == 'dips':
                DIPRoutine(dirs).download()
                return Response({"detail": "DIP download routine complete."}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class StoreView(APIView):
    """Store AIPs and/or DIPs. Accepts POST requests only."""

    def post(self, request, format=None, *args, **kwargs):
        log = logger.new(transaction_id=str(uuid4()))
        package_type = self.kwargs.get('package')
        dirs = None
        if request.POST.get('test'):
            dirs = {'tmp': settings.TEST_TMP_DIR}
        try:
            if package_type == 'aips':
                AIPRoutine(dirs).store()
                return Response({"detail": "AIP store routine complete."}, status=200)
            elif package_type == 'dips':
                DIPRoutine(dirs).store()
                return Response({"detail": "DIP store routine complete."}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)
