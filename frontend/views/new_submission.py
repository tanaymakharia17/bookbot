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
        "Upload the raw documents and add any context. The agent will extract everything else.",
    )

    st.markdown("**Documents**")
    uploaded = st.file_uploader(
        "Upload files",
        type=None,
        accept_multiple_files=True,
        key="submission_files",
        label_visibility="collapsed",
        help="Select one or several files — PDFs, images, spreadsheets, anything.",
    )
    if uploaded:
        st.markdown(
            f"<div class='bb-muted'>{len(uploaded)} file(s) ready</div>",
            unsafe_allow_html=True,
        )
        for f in uploaded:
            st.markdown(f"- 📎 {f.name}")

    # Fallback for browsers that block Streamlit's upload endpoint (e.g. Brave Shields)
    picked: list[str] = []
    with st.expander(
        "Upload blocked (Network Error / ERR_ACCESS_DENIED)? Use the fallback",
        expanded=True,
    ):
        server_files: list[str] = []
        try:
            server_files = api.available_files()
        except Exception:  # noqa: BLE001
            server_files = []
        st.markdown(
            f"1. Upload your files at **[{BACKEND_PUBLIC_URL}/api/v1/uploads/]"
            f"({BACKEND_PUBLIC_URL}/api/v1/uploads/)**<br>"
            "2. Come back and pick them below.",
            unsafe_allow_html=True,
        )
        if server_files:
            picked = st.multiselect("Staged files", server_files, key="server_files_pick")
        else:
            st.caption("No staged files yet — upload some using the link above.")

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
        with st.spinner("Uploading and queuing extraction…"):
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

    if uploaded:
        try:
            with st.spinner("Uploading documents for extraction…"):
                result = api.upload_documents(sub["id"], list(uploaded))
            if result.get("error"):
                st.error(f"Document upload failed: {result['error']}")
                return
        except Exception as exc:  # noqa: BLE001
            st.error(f"Document upload failed: {exc}")
            return

    go("chat", submission_id=sub["id"])