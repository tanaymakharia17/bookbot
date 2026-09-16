import streamlit as st

from api_client import get_api
from components.tables import balance_banner, journal_html
from components.ui import metric, page_header
from state import go


def render() -> None:
    entry_id = st.session_state.get("entry_id")
    if not entry_id:
        go("ledger")
        return

    api = get_api()
    entry = api.get_ledger_entry(entry_id)

    if not entry:
        st.error("That ledger entry could not be found.")
        if st.button("← Back to ledger"):
            go("ledger")
        return

    if st.button("← Back to ledger", key="entry_back"):
        go("ledger", client_id=entry.get("client_id"))

    page_header(
        f"Firm Workspace / General Ledger / {entry['id']}",
        f"{entry['vendor']}",
        f"{entry['client_name']} · {entry['transaction_date']}",
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(metric("Total debits", f"${entry['total_debits']:,.2f}"), unsafe_allow_html=True)
    m2.markdown(metric("Total credits", f"${entry['total_credits']:,.2f}"), unsafe_allow_html=True)
    m3.markdown(metric("Journal lines", str(len(entry["lines"]))), unsafe_allow_html=True)
    m4.markdown(metric("Balance", "Balanced" if entry["balanced"] else "Off"), unsafe_allow_html=True)

    st.write("")

    left, right = st.columns([1.75, 1], gap="large")

    with left:
        st.markdown("#### Journal lines")
        with st.container(border=True):
            st.markdown(journal_html(entry), unsafe_allow_html=True)
            st.markdown(balance_banner(entry), unsafe_allow_html=True)

    with right:
        st.markdown("#### Source")
        with st.container(border=True):
            st.markdown(f"**Submission**")
            st.markdown(f"<span class='bb-doc-id'>{entry['submission_id']}</span>", unsafe_allow_html=True)
            st.markdown("<hr class='bb-divider'/>", unsafe_allow_html=True)
            st.markdown(f"**Vendor**  \n{entry['vendor']}")
            st.markdown(f"**Payment method**  \n{entry.get('payment_method') or '—'}")
            st.markdown(f"**Posted**  \n{entry['transaction_date']}")
            st.write("")
            if st.button("Open source submission", key="open_source_sub", use_container_width=True):
                go("chat", submission_id=entry["submission_id"])