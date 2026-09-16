import streamlit as st

from api_client import get_api
from components.status_badge import badge
from components.ui import empty_state, metric, page_header
from state import go

FILTERS = {
    "All": None,
    "Needs Review": "NEEDS_REVIEW",
    "Extracted": "EXTRACTED",
    "Processing": "RAW",
    "Blocked": "BLOCKED_COMPLIANCE",
    "Posted": "COMMITTED",
}


def render() -> None:
    client_id = st.session_state.get("client_id")
    if not client_id:
        go("clients")
        return

    api = get_api()
    client = api.get_client(client_id)

    if not client:
        st.error("That business could not be found.")
        if st.button("← Back to businesses"):
            go("clients")
        return

    if st.button("← All businesses", key="back_to_clients"):
        go("clients")

    page_header(
        f"Firm Workspace / {client['name']}",
        client["name"],
        "Submissions for this business.",
    )

    all_subs = api.list_submissions(client_id)
    counts = {state: 0 for state in ("NEEDS_REVIEW", "EXTRACTED", "RAW", "BLOCKED_COMPLIANCE", "COMMITTED")}
    for sub in all_subs:
        counts[sub["state"]] = counts.get(sub["state"], 0) + 1

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(metric("Submissions", str(len(all_subs))), unsafe_allow_html=True)
    with m2:
        st.markdown(metric("Needs Review", str(counts["NEEDS_REVIEW"])), unsafe_allow_html=True)
    with m3:
        st.markdown(metric("Blocked", str(counts["BLOCKED_COMPLIANCE"])), unsafe_allow_html=True)
    with m4:
        st.markdown(metric("Posted", str(counts["COMMITTED"])), unsafe_allow_html=True)

    st.write("")
    top_left, top_right = st.columns([3, 1])
    with top_left:
        choice = st.pills(
            "Filter",
            list(FILTERS.keys()),
            default="All",
            label_visibility="collapsed",
        )
    with top_right:
        if st.button("+ New Submission", type="primary", use_container_width=True):
            go("new_submission", client_id=client_id)

    if choice is None:
        choice = "All"
    state_filter = FILTERS[choice]

    submissions = api.list_submissions(client_id, state_filter=state_filter)

    if not submissions:
        if choice == "All":
            empty_state(
                "📥",
                "No submissions yet",
                "Click “New Submission” to upload receipts or invoices.",
            )
        else:
            empty_state("️", "Nothing here", f"No submissions in “{choice}”.")
        return

    st.write("")
    for sub in submissions:
        _submission_row(sub)


def _submission_row(sub: dict) -> None:
    approved = st.session_state.pop(f"approved_{sub['id']}", None)

    with st.container(border=True):
        cols = st.columns([3.2, 1.2, 1, 1.1, 1], vertical_alignment="center")

        with cols[0]:
            st.markdown(f"**{sub['vendor'] or sub['id']}**")
            st.markdown(
                f"<div class='bb-muted'>{sub.get('raw_input') or 'No context provided.'}</div>",
                unsafe_allow_html=True,
            )

        with cols[1]:
            st.markdown(badge(sub["state"]), unsafe_allow_html=True)

        with cols[2]:
            amount = sub.get("_total")
            if amount is None:
                amount = sum(li["amount"] for li in sub.get("line_items", []) if not li["personal"])
            st.markdown(f"**${amount:,.2f}**")

        with cols[3]:
            st.markdown(f"<span class='bb-muted'>{sub.get('created_at', '—')}</span>", unsafe_allow_html=True)

        with cols[4]:
            if st.button("Open", key=f"open_{sub['id']}", use_container_width=True):
                go("chat", submission_id=sub["id"])

        if approved == "error":
            st.error(st.session_state.pop(f"approve_error_{sub['id']}", "Approval failed."))
        elif approved == "ok":
            st.success("Posted to ledger.")

        if sub["state"] in ("EXTRACTED", "NEEDS_REVIEW"):
            if st.button("Approve & Post", key=f"approve_{sub['id']}", use_container_width=True):
                from api_client import get_api

                result = get_api().approve(sub["id"])
                if "error" in result:
                    st.session_state[f"approve_error_{sub['id']}"] = result["error"]
                    st.session_state[f"approved_{sub['id']}"] = "error"
                else:
                    st.session_state[f"approved_{sub['id']}"] = "ok"
                st.rerun()