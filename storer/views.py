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
from storer.routines import DownloadRoutine, StoreRoutine
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
    """Downloads packages. Accepts POST requests only."""

    def post(self, request, format=None, *args, **kwargs):
        log = logger.new(transaction_id=str(uuid4()))
        dirs = None
        if request.POST.get('test'):
            dirs = {'tmp': settings.TEST_TMP_DIR}
        try:
            download = DownloadRoutine(dirs).run()
            return Response({"detail": download}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class StoreView(APIView):
    """Store packages. Accepts POST requests only."""

    def post(self, request, format=None, *args, **kwargs):
        log = logger.new(transaction_id=str(uuid4()))
        dirs = None
        url = request.GET.get('post_service_url', '')
        url = (urllib.parse.unquote(url) if url else '')
        if request.POST.get('test'):
            dirs = {'tmp': settings.TEST_TMP_DIR}
        try:
            store = StoreRoutine(url, dirs).run()
            return Response({"detail": store}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)
