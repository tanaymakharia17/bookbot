"""API serializers."""
from rest_framework import serializers

from apps.core.models import ClientAccount
from apps.core.services import get_default_firm


class ClientSerializer(serializers.ModelSerializer):
    """Client account, shaped to match the frontend contract."""

    name = serializers.CharField(source="client_name")
    submission_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()

    class Meta:
        model = ClientAccount
        fields = [
            "id",
            "name",
            "submission_count",
            "last_activity",
            "counts",
        ]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Company name is required.")
        queryset = ClientAccount.objects.filter(
            firm=get_default_firm(), client_name__iexact=name
        )
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A company with this name already exists.")
        return name

    def get_submission_count(self, obj) -> int:
        # Submissions are not modelled yet.
        return 0

    def get_last_activity(self, obj):
        return None

    def get_counts(self, obj) -> dict:
        return {}