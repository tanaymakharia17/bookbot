"""Builds the Markdown Source of Truth from structured submission data."""

from __future__ import annotations


def build_sot_markdown(sub: dict, client_name: str = "", capex_threshold: float = 2500.0) -> str:
    items = sub.get("line_items", [])
    rows = [
        "| Line # | Description | Qty | Unit Price | Total Amount | Category |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for i, li in enumerate(items, start=1):
        desc = li["description"]
        category = li["category"]
        if li.get("personal"):
            desc = f"~~{desc}~~"
            category = "Personal — excluded"
        elif li["amount"] >= capex_threshold:
            category = f"{category} · capitalizable"
        rows.append(
            f"| {i} | {desc} | {li['qty']} | ${li['unit_price']:,.2f} | "
            f"${li['amount']:,.2f} | {category} |"
        )

    business_total = sum(li["amount"] for li in items if not li["personal"])
    excluded_total = sum(li["amount"] for li in items if li["personal"])

    parts = [
        f"# Submission Source of Truth: {sub['id']}",
        f"- Client: {client_name or sub.get('client_id', '')}",
        f"- Vendor: {sub.get('vendor') or '—'}",
        f"- Created: {sub.get('created_at', '—')}",
        f"- Channel: {sub.get('channel', '—')}",
        "",
        "## Client Input",
        f"- Notes: {sub.get('raw_input') or '—'}",
        f"- Files: {', '.join(sub.get('file_names', [])) or '—'}",
        "",
        "## Extracted Line Items",
        *rows,
        "",
        f"- Reimbursable Total: ${business_total:,.2f}",
    ]
    if excluded_total:
        parts.append(f"- Personal (excluded): ${excluded_total:,.2f}")
    return "\n".join(parts)