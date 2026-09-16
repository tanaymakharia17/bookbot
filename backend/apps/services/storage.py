"""Local filesystem storage for submission documents.

Layout: ``<MEDIA_ROOT>/submissions/<submission_id>/<filename>``
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings


def submissions_root() -> Path:
    return Path(settings.MEDIA_ROOT) / "submissions"


def submission_dir(submission_id) -> Path:
    return submissions_root() / str(submission_id)


def ensure_submission_dir(submission_id) -> Path:
    path = submission_dir(submission_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_bytes(submission_id, name: str, content: bytes) -> Path:
    """Write raw bytes to the submission's folder."""
    path = ensure_submission_dir(submission_id) / name
    path.write_bytes(content)
    return path


def save_uploaded_file(submission_id, uploaded) -> Path:
    """Persist a Django ``UploadedFile`` to the submission's folder."""
    ensure_submission_dir(submission_id)
    path = submission_dir(submission_id) / uploaded.name
    with path.open("wb+") as destination:
        for chunk in uploaded.chunks():
            destination.write(chunk)
    return path


def list_files(submission_id) -> list[str]:
    path = submission_dir(submission_id)
    if not path.exists():
        return []
    return sorted(p.name for p in path.iterdir() if p.is_file())