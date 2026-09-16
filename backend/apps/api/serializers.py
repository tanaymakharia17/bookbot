"""API serializers."""
from rest_framework import serializers

from apps.core.models import ClientAccount


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
            "capex_threshold",
            "submission_count",
            "last_activity",
            "counts",
        ]

    def get_submission_count(self, obj) -> int:
        # Submissions are not modelled yet.
        return 0

    def get_last_activity(self, obj):
        return None

    def get_counts(self, obj) -> dict:
        return {}