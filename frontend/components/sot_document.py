import html

import streamlit as st

from components.tables import line_items_html


def _meta(label: str, value: str) -> str:
    return (
        f"<div class='bb-meta-item'><div class='k'>{html.escape(label)}</div>"
        f"<div class='v'>{html.escape(value)}</div></div>"
    )


def render(sub: dict, client_name: str, threshold: float) -> None:
    items = sub.get("line_items", [])
    business = sum(li["amount"] for li in items if not li["personal"])
    excluded = sum(li["amount"] for li in items if li["personal"])

    files = sub.get("file_names", [])
    files_html = "".join(
        f"<span class='bb-file'>📎 {html.escape(f)}</span>" for f in files
    ) or "—"
    reference = sub.get("reference_files", [])
    reference_html = "".join(
        f"<span class='bb-file'>🔖 {html.escape(f)}</span>" for f in reference
    )
    raw_input = sub.get("raw_input") or "No context provided."

    meta = "".join([
        _meta("Client", client_name),
        _meta("Vendor", sub.get("vendor") or "—"),
        _meta("Payment", sub.get("payment_method") or "To be confirmed"),
        _meta("Channel", sub.get("channel") or "—"),
        _meta("Created", sub.get("created_at") or "—"),
        _meta("Documents", str(len(files))),
    ])

    parts = [
        "<div class='bb-doc'>",
        "<div class='bb-doc-head'><div>",
        "<div class='bb-doc-title'>Submission Source of Truth</div>",
        f"<div class='bb-doc-id'>{html.escape(sub['id'])}</div>",
        "</div></div>",
        f"<div class='bb-meta-grid'>{meta}</div>",
        "<div class='bb-doc-section'>",
        "<div class='bb-doc-label'>Client input</div>",
        f"<div class='bb-doc-text'>{html.escape(raw_input)}</div>",
        f"<div class='bb-files'>{files_html}</div>",
        "</div>",
    ]
    if reference:
        parts += [
            "<div class='bb-doc-section'>",
            "<div class='bb-doc-label'>Reference documents (not saved)</div>",
            f"<div class='bb-files'>{reference_html}</div>",
            "</div>",
        ]
    parts += [
        "<div class='bb-doc-section'>",
        "<div class='bb-doc-label'>Extracted line items</div>",
        line_items_html(items, threshold),
        "</div>",
        "<div class='bb-totals'>",
        f"<div class='bb-total'><span>Reimbursable total</span><b>${business:,.2f}</b></div>",
        f"<div class='bb-total muted'><span>Personal excluded</span><b>${excluded:,.2f}</b></div>",
        "</div>",
        "</div>",
    ]
    st.markdown("".join(parts), unsafe_allow_html=True)