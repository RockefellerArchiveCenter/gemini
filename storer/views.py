import urllib

from asterism.views import prepare_response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response

from gemini import settings
from storer.models import Package
from storer.routines import DownloadRoutine, StoreRoutine, CleanupRequester
from storer.serializers import PackageSerializer, PackageListSerializer


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

    def get_post_service_url(self, request):
        url = request.GET.get('post_service_url')
        return urllib.parse.unquote(url) if url else ''

    def post(self, request, format=None):
        args = self.get_args(request)
        try:
            response = self.routine(*args).run()
            return Response(prepare_response(response), status=200)
        except Exception as e:
            return Response(prepare_response(e), status=500)


class DownloadView(BaseRoutineView):
    """Downloads packages. Accepts POST requests only."""
    routine = DownloadRoutine

    def get_args(self, request):
        dirs = {'tmp': settings.TEST_TMP_DIR} if request.POST.get('test') else None
        return (dirs,)


class StoreView(BaseRoutineView):
    """Stores packages. Accepts POST requests only."""
    routine = StoreRoutine

    def get_args(self, request):
        dirs = {'tmp': settings.TEST_TMP_DIR} if request.POST.get('test') else None
        url = self.get_post_service_url(request)
        return (url, dirs)


class CleanupRequestView(BaseRoutineView):
    """Sends request to clean up finished packages. Accepts POST requests only."""
    routine = CleanupRequester

    def get_args(self, request):
        url = self.get_post_service_url(request)
        return (url,)
