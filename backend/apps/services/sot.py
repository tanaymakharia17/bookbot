"""Build the Markdown Source of Truth from a submission."""
from __future__ import annotations


def build_sot_markdown(submission, client_name: str = "") -> str:
    items = submission.line_items or []
    rows = [
        "| Line # | Description | Qty | Unit Price | Total Amount | Category |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for i, li in enumerate(items, start=1):
        description = li["description"]
        category = li.get("category", "Uncategorized")
        if li.get("personal"):
            description = f"~~{description}~~"
            category = "Personal — excluded"
        rows.append(
            f"| {i} | {description} | {li.get('qty', 1)} | ${li.get('unit_price', 0):,.2f} | "
            f"${li.get('amount', 0):,.2f} | {category} |"
        )

    business_total = sum(li["amount"] for li in items if not li.get("personal"))
    excluded_total = sum(li["amount"] for li in items if li.get("personal"))

    lines = [
        f"# Submission Source of Truth: {submission.id}",
        f"- Client: {client_name or submission.client_id}",
        f"- Vendor: {submission.vendor or '—'}",
        f"- Created: {submission.created_at:%Y-%m-%d}" if submission.created_at else "- Created: —",
        f"- Channel: {submission.channel or '—'}",
        "",
        "## Client Input",
        f"- Notes: {submission.raw_input or '—'}",
        f"- Files: {', '.join(submission.file_names or []) or '—'}",
        "",
        "## Extracted Line Items",
        *rows,
        "",
        f"- Reimbursable Total: ${business_total:,.2f}",
    ]
    if excluded_total:
        lines.append(f"- Personal (excluded): ${excluded_total:,.2f}")
    return "\n".join(lines)