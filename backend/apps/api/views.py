"""API views."""
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.models import ClientAccount
from apps.core.services import get_default_firm

from .serializers import ClientSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness probe."""
    return Response({"status": "ok", "service": "bookbot-backend"})


class ClientListView(generics.ListCreateAPIView):
    """List and create managed companies for the default firm."""

    serializer_class = ClientSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return ClientAccount.objects.filter(firm=get_default_firm())

    def perform_create(self, serializer):
        serializer.save(firm=get_default_firm())


class ClientDetailView(generics.RetrieveAPIView):
    """Retrieve a single managed company."""

    serializer_class = ClientSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return ClientAccount.objects.filter(firm=get_default_firm())