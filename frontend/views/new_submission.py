import streamlit as st

from api_client import get_api
from components.ui import page_header
from config import BACKEND_PUBLIC_URL
from state import go


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

    if st.button("← Back to submissions", key="back_to_submissions"):
        go("submissions", client_id=client_id)

    page_header(
        f"Firm Workspace / {client['name']} / New",
        "New Submission",
        "Add documents and any context. The agent will extract everything else.",
    )

    server_files: list[str] = []
    try:
        server_files = api.available_files()
    except Exception:  # noqa: BLE001
        server_files = []

    st.markdown("**Documents**")
    st.caption(
        "Upload documents on the upload page (works even when browser uploads are "
        "blocked by a proxy), then select them below."
    )

    col_link, col_refresh = st.columns([3, 1], vertical_alignment="bottom")
    with col_link:
        st.link_button(
            "Open upload page ↗",
            f"{BACKEND_PUBLIC_URL}/api/v1/uploads/",
            use_container_width=True,
        )
    with col_refresh:
        if st.button("Refresh list", use_container_width=True, key="refresh_files"):
            st.rerun()

    picked: list[str] = []
    if server_files:
        picked = st.multiselect(
            "Staged / server files", server_files, key="server_files_pick"
        )
    else:
        st.info("No staged files yet — upload some via the link above, then Refresh.")

    uploaded = []
    with st.expander("Or upload directly from this browser (may be blocked by a proxy)"):
        uploaded = st.file_uploader(
            "Upload files",
            type=None,
            accept_multiple_files=True,
            key="submission_files",
            label_visibility="collapsed",
        )
        if uploaded:
            st.markdown(
                f"<div class='bb-muted'>{len(uploaded)} file(s) ready</div>",
                unsafe_allow_html=True,
            )
            for f in uploaded:
                st.markdown(f"- 📎 {f.name}")

    st.write("")
    st.markdown("**Context**")
    raw_input = st.text_area(
        "Anything relevant",
        key="submission_input",
        placeholder=(
            "Optional. Write anything you know about this expense — what it was for, "
            "who paid, any total you spotted, notes from the client…"
        ),
        height=130,
        label_visibility="collapsed",
    )

    st.write("")
    submitted = st.button(
        "Submit & open review",
        type="primary",
        use_container_width=True,
        key="submit_submission",
    )

    if not submitted:
        return

    file_names = [f.name for f in (uploaded or [])] + list(picked)
    if not file_names:
        st.error("Add at least one document — upload one or pick a staged file.")
        return

    try:
        with st.spinner("Creating submission and queuing extraction…"):
            sub = api.create_submission(client_id, file_names, raw_input)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not create submission: {exc}")
        return

    if not sub or sub.get("error") or "id" not in sub:
        st.error(f"Could not create submission: {(sub or {}).get('error', 'unknown error')}")
        return

    go("chat", submission_id=sub["id"])