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


class DownloadView(APIView):
    """Downloads packages. Accepts POST requests only."""

    def post(self, request, format=None, *args, **kwargs):
        dirs = {'tmp': settings.TEST_TMP_DIR} if request.POST.get('test') else None

        try:
            response = DownloadRoutine(dirs).run()
            return Response(prepare_response(response), status=200)
        except Exception as e:
            return Response(prepare_response(e), status=500)


class StoreView(APIView):
    """Stores packages. Accepts POST requests only."""

    def post(self, request, format=None, *args, **kwargs):
        dirs = {'tmp': settings.TEST_TMP_DIR} if request.POST.get('test') else None
        url = request.GET.get('post_service_url')
        url = (urllib.parse.unquote(url) if url else '')
        try:
            response = StoreRoutine(url, dirs).run()
            return Response(prepare_response(response), status=200)
        except Exception as e:
            return Response(prepare_response(e), status=500)


class CleanupRequestView(APIView):
    """Sends request to clean up finished packages. Accepts POST requests only."""

    def post(self, request):
        url = request.GET.get('post_service_url')
        url = (urllib.parse.unquote(url) if url else '')
        try:
            response = CleanupRequester(url).run()
            return Response(prepare_response(response), status=200)
        except Exception as e:
            return Response(prepare_response(e), status=500)
