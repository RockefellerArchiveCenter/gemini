from datetime import datetime
import logging
from structlog import wrap_logger
from uuid import uuid4

from django.shortcuts import render
from django.views.generic import View

from rest_framework import viewsets, generics, status
from rest_framework.response import Response

from transformer.models import AbstractObject
from transformer.serializers import AbstractObjectSerializer, AbstractObjectListSerializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class AbstractObjectViewSet(viewsets.ModelViewSet):
    """
    Endpoint for objects.

    list:
    Returns a list of objects. Accepts query parameters `type` and `updated_since`.

    retrieve:
    Returns a single object, identified by a primary key.
    """
    model = AbstractObject
    serializer_class = AbstractObjectSerializer

    def get_queryset(self):
        queryset = AbstractObject.objects.all()
        updated_since = self.request.GET.get('updated_since', "")
        type = self.request.GET.get('type', "")
        if updated_since != "":
            queryset = queryset.filter(last_modified__gte=datetime.fromtimestamp(int(updated_since)))
        if type != "":
            queryset = queryset.filter(type=type)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return AbstractObjectListSerializer
        return AbstractObjectSerializer
