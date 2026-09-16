import streamlit as st

from api_client import get_api
from components.ui import empty_state, metric, page_header
from state import go


def render() -> None:
    api = get_api()
    clients = api.list_clients()
    client_map = {c["id"]: c["name"] for c in clients}

    highlighted = st.session_state.pop("highlighted", None)

    if st.button("← All businesses", key="ledger_back"):
        go("clients")

    page_header(
        "Firm Workspace / General Ledger",
        "General Ledger",
        "Every posted journal entry across your clients.",
    )

    options = ["All businesses"] + [c["name"] for c in clients]
    choice = st.selectbox("Filter by business", options, index=0)
    client_id = None
    if choice != "All businesses":
        client_id = next(c["id"] for c in clients if c["name"] == choice)

    entries = api.list_ledger_entries(client_id)

    total_value = sum(e["total"] for e in entries)
    balanced = sum(1 for e in entries if e["balanced"])

    m1, m2, m3 = st.columns(3)
    m1.markdown(metric("Posted entries", str(len(entries))), unsafe_allow_html=True)
    m2.markdown(metric("Total debits", f"${total_value:,.2f}"), unsafe_allow_html=True)
    m3.markdown(metric("Balanced", f"{balanced}/{len(entries)}"), unsafe_allow_html=True)

    st.write("")

    if not entries:
        empty_state("📒", "No ledger entries yet", "Approved submissions will appear here.")
        return

    for entry in entries:
        _entry_row(entry, client_map, highlighted)


def _entry_row(entry: dict, client_map: dict, highlighted: str | None) -> None:
    is_highlighted = entry["id"] == highlighted

    with st.container(border=True):
        if is_highlighted:
            st.success("Just posted.", icon="✅")

        cols = st.columns([2.2, 1.4, 1.2, 1, 1, 1])

        with cols[0]:
            st.markdown(f"**{entry['vendor']}**")
            st.markdown(
                f"<span class='bb-muted'>{client_map.get(entry['client_id'], '')}</span>",
                unsafe_allow_html=True,
            )

        with cols[1]:
            st.markdown(f"<span class='bb-muted'>{entry['date']}</span>", unsafe_allow_html=True)

        with cols[2]:
            st.markdown(f"**${entry['total']:,.2f}**")

        with cols[3]:
            st.markdown(f"<span class='bb-muted'>{entry['line_count']} lines</span>", unsafe_allow_html=True)

        with cols[4]:
            if entry["balanced"]:
                st.markdown("<span class='bb-badge' style='color:#067647;background:#ECFDF3'>Balanced</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='bb-badge' style='color:#B42318;background:#FEF3F2'>Unbalanced</span>", unsafe_allow_html=True)

        with cols[5]:
            if st.button("Details", key=f"detail_{entry['id']}", use_container_width=True):
                go("ledger_entry", entry_id=entry["id"])