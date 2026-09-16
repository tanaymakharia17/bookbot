"""Seed deterministic agent action tasks from a submission's data."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Mapping

from django.conf import settings

from apps.core.constants import (
    ATTACH_DOCS_TASK,
    CAPITALIZE_TASK,
    CASH_BILL_TASK,
    EXCLUDE_PERSONAL_TASK,
    MISSING_CONTEXT_TASK,
    PERSONAL_KEYWORDS,
    POST_LEDGER_TASK,
    W8BEN_TASK,
)


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def agent_task(title: str, done: bool = False) -> dict[str, Any]:
    """Build an agent task with a deterministic id (stable across recomputes)."""
    return {"id": f"agent::{slug(title)}", "title": title, "done": done, "source": "agent"}


def seed_agent_tasks(sub: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Derive the agent's action checklist from a submission-like mapping."""
    titles: list[str] = []
    vendor = (sub.get("vendor") or "").lower()
    payment = sub.get("payment_method") or ""
    raw = (sub.get("raw_input") or "").lower()

    if sub.get("state") == "BLOCKED_COMPLIANCE" or "uk" in vendor or "foreign" in vendor:
        titles.append(W8BEN_TASK)
    if payment in ("", "Cash") or "cash" in raw:
        titles.append(CASH_BILL_TASK)

    items = sub.get("line_items") or []
    if any(
        li.get("personal")
        or any(k in (li.get("description") or "").lower() for k in PERSONAL_KEYWORDS)
        for li in items
    ):
        titles.append(EXCLUDE_PERSONAL_TASK)

    threshold = settings.CAPEX_THRESHOLD
    if any(
        (not li.get("personal")) and Decimal(str(li.get("amount", 0))) >= threshold
        for li in items
    ):
        titles.append(CAPITALIZE_TASK)

    titles.append(ATTACH_DOCS_TASK)
    if not (sub.get("raw_input") or "").strip():
        titles.append(MISSING_CONTEXT_TASK)
    titles.append(POST_LEDGER_TASK)

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for title in titles:
        if title not in seen:
            seen.add(title)
            out.append(agent_task(title))
    return out