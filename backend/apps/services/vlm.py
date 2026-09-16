"""Vision/document extraction via OpenRouter (real VLM reading)."""
from __future__ import annotations

import base64
import io
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from django.conf import settings

CATEGORIES = [
    "Fixed Assets",
    "IT Equipment",
    "Office Supplies",
    "Software",
    "Meals",
    "Travel",
    "Professional Fees",
    "Uncategorized",
]

SYSTEM_PROMPT = (
    "You are an accounting document parser. Read the provided receipt, invoice, "
    "or document and extract its contents exactly. Never invent amounts."
)

USER_PROMPT = """Extract the document(s) into STRICT JSON with this shape:

{
  "vendor": "string",
  "payment_method": "string (e.g. Company Credit Card, Company Debit Card, Wire Transfer, Cash)",
  "date": "YYYY-MM-DD or empty",
  "currency": "USD",
  "line_items": [
    {"description": "string", "qty": number, "unit_price": number,
     "amount": number, "category": "one of CATEGORIES"}
  ],
  "subtotal": number,
  "tax": number,
  "total": number,
  "notes": "string"
}

CATEGORIES = %s

Rules:
- Use the numbers printed on the document. Do not guess.
- If a value is unknown, use 0 for numbers and "" for strings.
- Return ONLY the JSON object, no prose, no code fences.
""" % CATEGORIES


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:  # noqa: BLE001
        return ""


def _pdf_image_blocks(data: bytes, max_pages: int = 5) -> list[dict[str, Any]]:
    """Extract page images from a (scanned) PDF as vision blocks."""
    blocks: list[dict[str, Any]] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages[:max_pages]:
            for image in page.images:
                name = image.name or "page.png"
                mime, _ = mimetypes.guess_type(name)
                encoded = base64.b64encode(image.data).decode()
                blocks.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime or 'image/png'};base64,{encoded}"},
                })
    except Exception:  # noqa: BLE001
        return []
    return blocks


def _content_blocks(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    data = path.read_bytes()

    if suffix == ".pdf":
        text = _pdf_text(data)
        if text.strip():
            return [{"type": "text", "text": f"PDF text from {path.name}:\n{text[:20000]}"}]
        image_blocks = _pdf_image_blocks(data)
        if image_blocks:
            return image_blocks
        encoded = base64.b64encode(data).decode()
        return [{
            "type": "file",
            "file": {"filename": path.name, "file_data": f"data:application/pdf;base64,{encoded}"},
        }]

    mime, _ = mimetypes.guess_type(path.name)
    encoded = base64.b64encode(data).decode()
    return [{
        "type": "image_url",
        "image_url": {"url": f"data:{mime or 'image/png'};base64,{encoded}"},
    }]


def _parse_json(raw: str) -> dict | None:
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def read_documents(paths: list[Path]) -> dict[str, Any] | None:
    """Send documents to the VLM and return structured data (or None on failure)."""
    if not settings.OPENROUTER_API_KEY or not paths:
        return None

    from openai import OpenAI

    client = OpenAI(
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
    )

    content: list[dict[str, Any]] = [{"type": "text", "text": USER_PROMPT}]
    for path in paths:
        content.append({"type": "text", "text": f"--- document: {path.name} ---"})
        content.extend(_content_blocks(path))

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model=settings.VLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                temperature=0,
                max_tokens=2000,
            )
            return _parse_json(completion.choices[0].message.content or "")
        except Exception as exc:  # noqa: BLE001 - retry once on transient errors
            last_error = exc
    if last_error:
        raise last_error
    return None


def normalize_line_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in data.get("line_items") or []:
        try:
            qty = float(row.get("qty") or 1)
            unit = float(row.get("unit_price") or 0)
            amount = float(row.get("amount") or 0)
        except (TypeError, ValueError):
            continue
        if amount == 0 and unit:
            amount = round(qty * unit, 2)
        if not row.get("description") and amount == 0:
            continue
        category = row.get("category") or "Uncategorized"
        if category not in CATEGORIES:
            category = "Uncategorized"
        items.append({
            "description": str(row.get("description") or "Item"),
            "qty": int(qty) if float(qty).is_integer() else qty,
            "unit_price": round(unit, 2),
            "amount": round(amount, 2),
            "category": category,
            "personal": False,
        })
    return items


def normalize_payment(value: str) -> str:
    text = (value or "").lower()
    if "debit" in text:
        return "Company Debit Card"
    if "visa" in text or "master" in text or "amex" in text or "credit" in text or "card" in text:
        return "Company Credit Card"
    if "wire" in text or "transfer" in text:
        return "Wire Transfer"
    if "cash" in text:
        return "Cash"
    return value or "Company Credit Card"