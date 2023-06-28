from asterism.views import RoutineView, prepare_response
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from storer.models import Package
from storer.routines import (AddDataRoutine, CleanupRequester, DeliverRoutine,
                             DownloadRoutine, ParseMETSRoutine, StoreRoutine)
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

    def create(self, request):
        """Handles data from Archivematica post-store callbacks.

        Expects an `identifier` to be passed in the request data.
        """
        if "identifier" not in request.data:
            return Response(
                {"detail": "Expected `identifier` to be in request data, none found"},
                status=status.HTTP_400_BAD_REQUEST)
        archivematica_identifier = request.data["identifier"]
        if not Package.objects.filter(archivematica_identifier=archivematica_identifier).exists():
            Package.objects.create(
                archivematica_identifier=archivematica_identifier,
                process_status=Package.CREATED)
            message = prepare_response(("Package created.", archivematica_identifier))
            return Response(message, status=status.HTTP_201_CREATED)
        return Response(
            {"detail": f"A package with the identifier {archivematica_identifier} already exists."},
            status=status.HTTP_400_BAD_REQUEST)


class AddDataView(RoutineView):
    """Downloads packages. Accepts POST requests only."""
    routine = AddDataRoutine


class DownloadView(RoutineView):
    """Downloads packages. Accepts POST requests only."""
    routine = DownloadRoutine


class ParseMETSView(RoutineView):
    """Downloads packages. Accepts POST requests only."""
    routine = ParseMETSRoutine


class StoreView(RoutineView):
    """Stores packages. Accepts POST requests only."""
    routine = StoreRoutine


class DeliverView(RoutineView):
    """Stores packages. Accepts POST requests only."""
    routine = DeliverRoutine


class CleanupRequestView(RoutineView):
    """Sends request to clean up finished packages. Accepts POST requests only."""
    routine = CleanupRequester
