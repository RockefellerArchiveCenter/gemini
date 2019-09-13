"""gemini URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import url
from django.urls import include
from storer.views import PackageViewSet, DownloadView, StoreView, CleanupRequestView
from rest_framework import routers
from rest_framework.schemas import get_schema_view

router = routers.DefaultRouter()
router.register(r'packages', PackageViewSet, 'package')

schema_view = get_schema_view(
    title="Gemini API",
    description="Endpoints for Gemini microservice application.",
)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^store/', StoreView.as_view(), name='store-packages'),
    url(r'^download/', DownloadView.as_view(), name='download-packages'),
    url(r'^request-cleanup/', CleanupRequestView.as_view(), name='request-cleanup'),
    url(r'^status/', include('health_check.api.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^schema/', schema_view, name='schema'),
]
