#!/usr/bin/env python
"""Idempotent dummy-data loader.

Lives outside the backend on purpose. Reads every ``seed/data/*.json`` file and
upserts rows. Run it via ``make seed`` (inside the backend container), or
directly with a Python that has Django installed.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent


def _find_backend() -> Path:
    """Locate the backend dir on host (../backend) or in the container (/app)."""
    candidates = []
    env = os.environ.get("BOOKBOT_BACKEND_DIR")
    if env:
        candidates.append(Path(env))
    candidates += [SEED_DIR.parent / "backend", Path("/app")]
    for candidate in candidates:
        if (candidate / "manage.py").exists():
            return candidate
    return SEED_DIR.parent / "backend"


BACKEND_DIR = _find_backend()

sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

from apps.core.models import ClientAccount, CpaFirm, Submission  # noqa: E402


def get_default_firm() -> CpaFirm:
    firm, _ = CpaFirm.objects.get_or_create(firm_name=settings.DEFAULT_FIRM_NAME)
    return firm


def seed_firms(data: dict) -> None:
    for row in data.get("firms", []):
        _, created = CpaFirm.objects.get_or_create(firm_name=row["name"])
        print(f"  firm   {'created' if created else 'exists '}  {row['name']}")


def seed_clients(data: dict) -> None:
    firm = get_default_firm()
    for row in data.get("clients", []):
        obj, created = ClientAccount.objects.get_or_create(
            firm=firm,
            client_name=row["name"],
        )
        print(f"  client {'created' if created else 'exists '}  {obj.client_name}")


def seed_submissions(data: dict) -> None:
    firm = get_default_firm()
    for row in data.get("submissions", []):
        client = ClientAccount.objects.filter(
            firm=firm, client_name=row["client"]
        ).first()
        if client is None:
            print(f"  submission skipped — unknown client '{row['client']}'")
            continue
        defaults = {
            "client": client,
            "state": row.get("state", "RAW"),
            "vendor": row.get("vendor", ""),
            "payment_method": row.get("payment_method", ""),
            "channel": row.get("channel", "Portal Upload"),
            "raw_input": row.get("raw_input", ""),
            "sot_markdown": row.get("sot_markdown", ""),
            "file_names": row.get("file_names", []),
            "reference_files": row.get("reference_files", []),
            "line_items": row.get("line_items", []),
            "tasks": row.get("tasks", []),
            "journal_entry": row.get("journal_entry"),
            "blocker": row.get("blocker", ""),
        }
        obj, created = Submission.objects.update_or_create(
            id=row["id"], defaults=defaults
        )
        label = obj.vendor or obj.state
        print(f"  submission {'created' if created else 'updated'}  {label}")


def main() -> None:
    files = sorted((SEED_DIR / "data").glob("*.json"))
    if not files:
        print("no seed data files found in seed/data/")
        return
    for path in files:
        print(f"seeding {path.name}")
        data = json.loads(path.read_text())
        seed_firms(data)
        seed_clients(data)
        seed_submissions(data)
    print("seed complete")


if __name__ == "__main__":
    main()