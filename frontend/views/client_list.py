import streamlit as st

from api_client import get_api
from components.status_badge import badge
from components.ui import empty_state, metric, page_header, section
from config import API_MODE
from state import go


def render() -> None:
    api = get_api()

    try:
        clients = api.list_clients()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load companies: {exc}")
        return

    page_header(
        "Firm Workspace",
        "Client Businesses",
        "Select a business to review its submissions, or add a new one.",
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
    left, mid, right = st.columns([3, 1, 1], vertical_alignment="bottom")
    with left:
        query = st.text_input(
            "Search clients", placeholder="Search businesses…", label_visibility="collapsed"
        )
    with mid:
        if st.button("📒 General Ledger", use_container_width=True, key="open_ledger"):
            go("ledger")
    with right:
        if st.button("+ New Company", type="primary", use_container_width=True, key="new_company"):
            st.session_state["_show_new_company"] = True

    flash = st.session_state.pop("_flash", None)
    if flash:
        st.success(flash)

    if query:
        clients = [c for c in clients if query.lower() in c["name"].lower()]

    section("Businesses")

    if not clients:
        empty_state("🏢", "No companies yet", "Click “+ New Company” to add your first business.")
        _maybe_open_dialog(api)
        return

    for client in clients:
        _client_row(client)

    _maybe_open_dialog(api)

    st.markdown(
        f"<div class='bb-muted' style='margin-top:24px'>Bookbot UI v2 · single-page · data: {API_MODE}</div>",
        unsafe_allow_html=True,
    )


def _client_row(client: dict) -> None:
    counts = client.get("counts", {})

    with st.container(border=True):
        cols = st.columns([3, 2.2, 1, 1], vertical_alignment="center")

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
            if st.button("Open →", key=f"client_{client['id']}", use_container_width=True, type="primary"):
                go("submissions", client_id=client["id"])


def _maybe_open_dialog(api) -> None:
    if st.session_state.get("_show_new_company"):
        _new_company_dialog(api)


@st.dialog("New company")
def _new_company_dialog(api) -> None:
    name = st.text_input("Company name", placeholder="e.g. Apex Retail Inc.")

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Create", type="primary", use_container_width=True, key="create_company"):
            if not name.strip():
                st.error("Company name is required.")
                return
            result = api.create_client(name.strip())
            if result.get("error"):
                st.error(result["error"])
                return
            st.session_state["_flash"] = f"Company “{result['name']}” created."
            st.session_state["_show_new_company"] = False
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True, key="cancel_company"):
            st.session_state["_show_new_company"] = False
            st.rerun()