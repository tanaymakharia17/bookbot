import uuid

from django.db import models

from ..state import SubmissionState
from .client import ClientAccount


class Submission(models.Model):
    """A client submission (workpaper) with its extracted source of truth."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        ClientAccount,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    state = models.CharField(
        max_length=50,
        choices=SubmissionState.choices,
        default=SubmissionState.RAW,
        db_index=True,
    )

    vendor = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=100, default="Portal Upload")
    raw_input = models.TextField(blank=True)
    sot_markdown = models.TextField(blank=True)
    document_context = models.JSONField(default=list, blank=True)

    file_names = models.JSONField(default=list, blank=True)
    reference_files = models.JSONField(default=list, blank=True)
    line_items = models.JSONField(default=list, blank=True)
    tasks = models.JSONField(default=list, blank=True)
    pending_plan = models.JSONField(default=dict, blank=True)
    journal_entry = models.JSONField(null=True, blank=True)
    chat_messages = models.JSONField(default=list, blank=True)
    blocker = models.TextField(blank=True)
    blocker_resolved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["client", "state"])]
        verbose_name = "submission"
        verbose_name_plural = "submissions"

    def __str__(self) -> str:
        return f"{self.client.client_name} · {self.get_state_display()}"