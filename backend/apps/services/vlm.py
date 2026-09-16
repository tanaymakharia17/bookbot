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
- If several documents are provided, COMBINE every line item into this ONE object.
- Return exactly ONE JSON object (never an array), no prose, no code fences.
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

        # Not a real PDF (or unreadable): treat mislabeled text files as text.
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError:
            decoded = ""
        if decoded.strip():
            return [{"type": "text", "text": f"Document {path.name} (text):\n{decoded[:20000]}"}]

        encoded = base64.b64encode(data).decode()
        return [{
            "type": "file",
            "file": {"filename": path.name, "file_data": f"data:application/pdf;base64,{encoded}"},
        }]

    # images (and anything else) go to the model as vision input
    mime, _ = mimetypes.guess_type(path.name)
    encoded = base64.b64encode(data).decode()
    return [{
        "type": "image_url",
        "image_url": {"url": f"data:{mime or 'image/png'};base64,{encoded}"},
    }]


def _parse_json(raw: str):
    """Parse the model output into a dict. Tolerates code fences and arrays."""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

    for candidate in (text, _segment(text, "{", "}"), _segment(text, "[", "]")):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _segment(text: str, opener: str, closer: str) -> str | None:
    start, end = text.find(opener), text.rfind(closer)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start : end + 1]


def _coerce(data) -> dict[str, Any] | None:
    """Normalise a single object or a list of per-document objects into one."""
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        items: list[dict] = []
        vendors: list[str] = []
        payment = ""
        for entry in data:
            if not isinstance(entry, dict):
                continue
            items.extend(entry.get("line_items") or [])
            if entry.get("vendor"):
                vendors.append(str(entry["vendor"]).strip())
            if not payment and entry.get("payment_method"):
                payment = str(entry["payment_method"])
        unique = list(dict.fromkeys(vendors))
        vendor = unique[0] if len(unique) == 1 else ("Multiple vendors" if unique else "")
        if items:
            return {"vendor": vendor, "payment_method": payment, "line_items": items}
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
                max_tokens=4000,
                extra_body={"reasoning": {"effort": "low"}},
            )
            return _coerce(_parse_json(completion.choices[0].message.content or ""))
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