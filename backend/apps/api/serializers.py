"""API serializers."""
from rest_framework import serializers

from apps.core.models import ClientAccount, Submission
from apps.core.services import get_default_firm
from apps.services.projection import empty_plan, plan_labels, project


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


class SubmissionListSerializer(serializers.ModelSerializer):
    """Submission summary for the submissions list."""

    class Meta:
        model = Submission
        fields = [
            "id",
            "client_id",
            "state",
            "vendor",
            "raw_input",
            "created_at",
            "file_names",
            "line_items",
        ]


class SubmissionCreateSerializer(serializers.ModelSerializer):
    """Create a submission (starts in the RAW state)."""

    client_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "client_id",
            "state",
            "vendor",
            "raw_input",
            "file_names",
            "created_at",
        ]
        read_only_fields = ["id", "state", "vendor", "created_at"]

    def validate_client_id(self, value):
        if not ClientAccount.objects.filter(id=value, firm=get_default_firm()).exists():
            raise serializers.ValidationError("Unknown company.")
        return value

    def validate_file_names(self, value):
        if not value:
            raise serializers.ValidationError("At least one file is required.")
        return value

    def create(self, validated_data):
        client = ClientAccount.objects.get(id=validated_data.pop("client_id"))
        return Submission.objects.create(
            client=client, pending_plan=empty_plan(), **validated_data
        )


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """Full submission detail, including the JSON workpaper fields."""

    projected = serializers.SerializerMethodField()
    plan_labels = serializers.SerializerMethodField()
    pending_plan = serializers.SerializerMethodField()
    token_budget = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "client_id",
            "state",
            "vendor",
            "payment_method",
            "channel",
            "raw_input",
            "sot_markdown",
            "file_names",
            "reference_files",
            "line_items",
            "tasks",
            "pending_plan",
            "journal_entry",
            "chat_messages",
            "tokens_used",
            "token_budget",
            "blocker",
            "blocker_resolved",
            "projected",
            "plan_labels",
            "created_at",
            "updated_at",
            "approved_at",
        ]

    def get_projected(self, obj) -> dict:
        return project(obj)

    def get_plan_labels(self, obj) -> list:
        return plan_labels(obj.pending_plan)

    def get_pending_plan(self, obj) -> dict:
        plan = obj.pending_plan or {}
        return {
            "save_files": plan.get("save_files", []),
            "line_item_ops": plan.get("line_item_ops", []),
            "task_ops": plan.get("task_ops", []),
        }

    def get_token_budget(self, obj) -> int:
        from django.conf import settings

        return settings.AGENT_SUBMISSION_TOKEN_BUDGET