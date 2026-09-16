"""Submission lifecycle states."""
from django.db import models


class SubmissionState(models.TextChoices):
    RAW = "RAW", "Raw"
    EXTRACTED = "EXTRACTED", "Extracted"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
    PENDING_CLIENT = "PENDING_CLIENT", "Pending client"
    BLOCKED_COMPLIANCE = "BLOCKED_COMPLIANCE", "Blocked on compliance"
    COMMITTED = "COMMITTED", "Committed"