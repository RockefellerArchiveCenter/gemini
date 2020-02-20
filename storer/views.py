from asterism.views import prepare_response
from rest_framework.response import Response
from rest_framework.views import APIView
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


class BaseRoutineView(APIView):
    """Base view for routines."""

    def post(self, request, format=None):
        try:
            response = self.routine().run()
            return Response(prepare_response(response), status=200)
        except Exception as e:
            return Response(prepare_response(e), status=500)


class DownloadView(BaseRoutineView):
    """Downloads packages. Accepts POST requests only."""
    routine = DownloadRoutine


class StoreView(BaseRoutineView):
    """Stores packages. Accepts POST requests only."""
    routine = StoreRoutine


class CleanupRequestView(BaseRoutineView):
    """Sends request to clean up finished packages. Accepts POST requests only."""
    routine = CleanupRequester
