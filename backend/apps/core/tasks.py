"""Celery tasks for the Bookbot backend."""
from __future__ import annotations

from celery import shared_task

from apps.core.models import Submission
from apps.services.extraction import extract


@shared_task(name="core.extract_submission")
def extract_submission(submission_id: str) -> str:
    """Extract a RAW submission into its Source of Truth (stub for the VLM)."""
    submission = Submission.objects.get(id=submission_id)
    extract(submission)
    return str(submission.id)