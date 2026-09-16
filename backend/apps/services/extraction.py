"""Deterministic extraction heuristics (placeholder for the VLM extractor)."""
from __future__ import annotations

import re

from apps.core.constants import VENDOR_HINTS


def extract_amount(text: str) -> float | None:
    """Return the largest dollar-looking amount found in the text."""
    matches = re.findall(r"\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text)
    values: list[float] = []
    for match in matches:
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    values = [v for v in values if v >= 1]
    return max(values) if values else None


def detect_vendor(text: str) -> tuple[str, str]:
    """Return (vendor_name, category) guessed from the text."""
    lowered = text.lower()
    for hint, (vendor, category) in VENDOR_HINTS.items():
        if hint in lowered:
            return vendor, category
    return "Unknown Vendor", "Uncategorized"


def mock_extract(vendor: str, category: str, total: float) -> list[dict]:
    """Split a total into two placeholder line items."""
    first = round(total * 0.88, 2)
    second = round(total - first, 2)
    return [
        {"description": f"{vendor} — Primary item", "qty": 1, "unit_price": first,
         "amount": first, "category": category, "personal": False},
        {"description": f"{vendor} — Accessory / add-on", "qty": 1, "unit_price": second,
         "amount": second, "category": category, "personal": False},
    ]


def recompute_fields(
    fallback_vendor: str, fallback_category: str, text: str
) -> tuple[str, str, float, str]:
    """Recompute vendor/category/total/payment, keeping the prior vendor if undetected."""
    vendor, category = detect_vendor(text)
    if vendor == "Unknown Vendor" and fallback_vendor:
        vendor = fallback_vendor
        category = fallback_category or "Uncategorized"
    total = extract_amount(text) or 1250.00
    payment = "Cash" if "cash" in text.lower() else "Company Credit Card"
    return vendor, category, total, payment