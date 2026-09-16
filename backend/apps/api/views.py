"""API views."""
import uuid as uuid_lib

from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.models import ClientAccount, Submission
from apps.core.services import get_default_firm

from .serializers import (
    ClientSerializer,
    SubmissionCreateSerializer,
    SubmissionDetailSerializer,
    SubmissionListSerializer,
)


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


class SubmissionListView(generics.ListCreateAPIView):
    """List and create submissions, optionally filtered by client and state."""

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SubmissionCreateSerializer
        return SubmissionListSerializer

    def get_queryset(self):
        queryset = Submission.objects.select_related("client").all()

        client_id = self.request.query_params.get("client")
        if client_id:
            try:
                uuid_lib.UUID(str(client_id))
            except (ValueError, TypeError):
                return Submission.objects.none()
            queryset = queryset.filter(client_id=client_id)

        state = self.request.query_params.get("state")
        if state:
            queryset = queryset.filter(state=state)

        return queryset


class SubmissionDetailView(generics.RetrieveAPIView):
    """Retrieve a single submission with its full workpaper data."""

    serializer_class = SubmissionDetailSerializer
    permission_classes = [AllowAny]
    queryset = Submission.objects.select_related("client").all()