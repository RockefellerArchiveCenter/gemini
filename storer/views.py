import json

from asterism.views import BaseServiceView, RoutineView
from rest_framework.viewsets import ModelViewSet
from storer.models import Package
from storer.routines import (CleanupRequester, DeliverRoutine, DownloadRoutine,
                             StoreRoutine)
from storer.serializers import PackageListSerializer, PackageSerializer


class PackageViewSet(ModelViewSet):
    """
    Endpoint for packages.

    list:
    Returns a list of packages.

    retrieve:
    Returns a single package, identified by a primary key.
    """
    model = Package
    serializer_class = PackageSerializer
    queryset = Package.objects.all().order_by('-last_modified')

    def get_serializer_class(self):
        if self.action == 'list':
            return PackageListSerializer
        return PackageSerializer


class DownloadView(BaseServiceView):
    """Downloads packages. Accepts POST requests only."""

    def get_service_response(self, request):
        body_json = json.loads(request.body)
        identifier = body_json.get("identifier")
        return DownloadRoutine(identifier).run()


class StoreView(RoutineView):
    """Stores packages. Accepts POST requests only."""
    routine = StoreRoutine


class DeliverView(RoutineView):
    """Stores packages. Accepts POST requests only."""
    routine = DeliverRoutine


class CleanupRequestView(RoutineView):
    """Sends request to clean up finished packages. Accepts POST requests only."""
    routine = CleanupRequester
