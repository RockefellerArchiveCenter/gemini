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
from asterism.views import PingView
from django.contrib import admin
from django.urls import include, re_path
from rest_framework import routers

from storer.views import (AddDataView, CleanupRequestView, DeliverView,
                          DownloadView, PackageViewSet, ParseMETSView,
                          StoreView)

router = routers.DefaultRouter()
router.register(r'packages', PackageViewSet, 'package')

urlpatterns = [
    re_path(r'^', include(router.urls)),
    re_path(r'^add-data/', AddDataView.as_view(), name='add-data'),
    re_path(r'^download/', DownloadView.as_view(), name='download-package'),
    re_path(r'^parse-mets/', ParseMETSView.as_view(), name='parse-mets'),
    re_path(r'^store/', StoreView.as_view(), name='store-package'),
    re_path(r'^deliver/', DeliverView.as_view(), name='deliver-packages'),
    re_path(r'^request-cleanup/', CleanupRequestView.as_view(), name='request-cleanup'),
    re_path(r'^status/', PingView.as_view(), name='ping'),
    re_path(r'^admin/', admin.site.urls),
]
