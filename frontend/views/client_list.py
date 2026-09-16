import streamlit as st

from api_client import get_api
from components.status_badge import badge
from components.ui import empty_state, metric, page_header, section
from state import go


def render() -> None:
    api = get_api()

    try:
        clients = api.list_clients()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load clients: {exc}")
        return

    page_header(
        "Firm Workspace",
        "Client Businesses",
        "Select a business to review its submissions or start a new one.",
    )

    total_subs = sum(c.get("submission_count", 0) for c in clients)
    total_review = sum(c.get("counts", {}).get("NEEDS_REVIEW", 0) for c in clients)
    total_blocked = sum(c.get("counts", {}).get("BLOCKED_COMPLIANCE", 0) for c in clients)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(metric("Client Businesses", str(len(clients))), unsafe_allow_html=True)
    with m2:
        st.markdown(metric("Total Submissions", str(total_subs)), unsafe_allow_html=True)
    with m3:
        st.markdown(metric("Needs Review", str(total_review)), unsafe_allow_html=True)
    with m4:
        st.markdown(metric("Blocked", str(total_blocked)), unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([4, 1], vertical_alignment="bottom")
    with left:
        query = st.text_input(
            "Search clients", placeholder="Search businesses…", label_visibility="collapsed"
        )
    with right:
        if st.button("📒 General Ledger", use_container_width=True, key="open_ledger"):
            go("ledger")

    if query:
        clients = [c for c in clients if query.lower() in c["name"].lower()]

    section("Businesses")

    if not clients:
        empty_state("🔍", "No clients found", "Try a different search term.")
        return

    for client in clients:
        _client_row(client)


def _client_row(client: dict) -> None:
    counts = client.get("counts", {})

    with st.container(border=True):
        cols = st.columns([3, 2.2, 0.9, 1.1, 0.9], vertical_alignment="center")

        with cols[0]:
            st.markdown(f"<div class='bb-client-name'>{client['name']}</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='bb-muted'>Last activity {client.get('last_activity') or '—'}</div>",
                unsafe_allow_html=True,
            )

        with cols[1]:
            pills = ""
            for state in ("NEEDS_REVIEW", "BLOCKED_COMPLIANCE", "EXTRACTED", "RAW"):
                count = counts.get(state, 0)
                if count:
                    pills += f"{badge(state)} <span class='bb-muted'>×{count}</span> "
            st.markdown(pills or "<span class='bb-muted'>No open work</span>", unsafe_allow_html=True)

        with cols[2]:
            st.markdown(f"**{client.get('submission_count', 0)}**")
            st.markdown("<div class='bb-muted'>subs</div>", unsafe_allow_html=True)

        with cols[3]:
            st.markdown(f"<span class='bb-muted'>CapEx</span>", unsafe_allow_html=True)
            st.markdown(f"**${client.get('capex_threshold', 2500):,.0f}**")

        with cols[4]:
            if st.button("Open →", key=f"client_{client['id']}", use_container_width=True, type="primary"):
                go("submissions", client_id=client["id"])