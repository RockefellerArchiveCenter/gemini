from asterism.views import RoutineView
from rest_framework.viewsets import ModelViewSet
from storer.models import Package
from storer.routines import CleanupRequester, DownloadRoutine, StoreRoutine
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


class DownloadView(RoutineView):
    """Downloads packages. Accepts POST requests only."""
    routine = DownloadRoutine


class StoreView(RoutineView):
    """Stores packages. Accepts POST requests only."""
    routine = StoreRoutine


class CleanupRequestView(RoutineView):
    """Sends request to clean up finished packages. Accepts POST requests only."""
    routine = CleanupRequester
