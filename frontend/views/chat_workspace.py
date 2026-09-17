import streamlit as st

from api_client import get_api
from components import plan as plan_component
from components import sot_document, tasks as tasks_component
from components.status_badge import badge
from components.tables import balance_banner, journal_html, line_items_html
from components.ui import section
from config import DEFAULT_CAPEX_THRESHOLD
from state import go


def render() -> None:
    submission_id = st.session_state.get("submission_id")
    if not submission_id:
        go("submissions", client_id=st.session_state.get("client_id"))
        return

    api = get_api()
    sub = api.get_submission(submission_id)

    if not sub:
        st.error("That submission could not be found.")
        if st.button("← Back to submissions"):
            go("submissions", client_id=st.session_state.get("client_id"))
        return

    client = api.get_client(sub["client_id"])
    client_name = client["name"] if client else "Unknown"
    threshold = DEFAULT_CAPEX_THRESHOLD

    if st.button("← Back to submissions", key="back_to_subs_chat"):
        st.session_state.pop("_staged_files", None)
        go("submissions", client_id=sub["client_id"])

    _inject_locked_layout()
    _header(sub, client_name)

    if sub["state"] == "RAW":
        _render_processing(api, sub)
        return

    left, right = st.columns([2, 3], gap="medium")

    with left:
        _render_sot_pane(sub, client_name, threshold)
        _render_final_pane(api, sub, threshold)

    with right:
        _render_chat_pane(sub, api)
        _render_actions_pane(sub, api)


def _inject_locked_layout() -> None:
    st.markdown(
        """
<style>
  /* page fills the viewport exactly */
  .block-container:has(.st-key-sot_pane) {
      height: 100vh !important; box-sizing: border-box;
      overflow: auto !important;
      display: flex !important; flex-direction: column !important;
  }
  /* every wrapper on the path to a card fills the remaining height */
  .block-container:has(.st-key-sot_pane) div[data-testid="stLayoutWrapper"]:has(.st-key-sot_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stVerticalBlock"]:has(.st-key-sot_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stLayoutWrapper"]:has(.st-key-final_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stVerticalBlock"]:has(.st-key-final_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stLayoutWrapper"]:has(.st-key-chat_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stVerticalBlock"]:has(.st-key-chat_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stLayoutWrapper"]:has(.st-key-actions_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stVerticalBlock"]:has(.st-key-actions_card) {
      flex: 1 1 0 !important; min-height: 0 !important;
      display: flex !important; flex-direction: column !important;
  }
  /* direct wrapper of the chat/actions cards drives the 60/40 split */
  .block-container:has(.st-key-sot_pane) div[data-testid="stLayoutWrapper"]:has(> .st-key-chat_card) {
      flex: 3 1 0 !important;
  }
  .block-container:has(.st-key-sot_pane) div[data-testid="stLayoutWrapper"]:has(> .st-key-actions_card) {
      flex: 2 1 0 !important;
  }
  /* columns row */
  .block-container:has(.st-key-sot_pane) div[data-testid="stHorizontalBlock"]:has(.st-key-sot_card) {
      flex: 1 1 0 !important; min-height: 0 !important; align-items: stretch !important;
  }
  /* columns stretch and are flex columns */
  .block-container:has(.st-key-sot_pane) div[data-testid="stColumn"]:has(.st-key-sot_card),
  .block-container:has(.st-key-sot_pane) div[data-testid="stColumn"]:has(.st-key-chat_card) {
      align-self: stretch !important; height: auto !important; min-height: 0 !important;
      display: flex !important; flex-direction: column !important;
  }
  .block-container:has(.st-key-sot_pane) div[data-testid="stColumn"]:has(.st-key-sot_card) > div[data-testid="stVerticalBlock"],
  .block-container:has(.st-key-sot_pane) div[data-testid="stColumn"]:has(.st-key-chat_card) > div[data-testid="stVerticalBlock"] {
      flex: 1 1 0 !important; min-height: 0 !important;
      display: flex !important; flex-direction: column !important;
  }
  /* the four cards share their column */
  .block-container:has(.st-key-sot_pane) .st-key-sot_card,
  .block-container:has(.st-key-sot_pane) .st-key-final_card,
  .block-container:has(.st-key-sot_pane) .st-key-chat_card,
  .block-container:has(.st-key-sot_pane) .st-key-actions_card {
      flex: 1 1 0 !important; min-height: 200px !important;
      display: flex !important; flex-direction: column !important;
  }
  .block-container:has(.st-key-sot_pane) .st-key-chat_card { flex: 3 1 0 !important; }
  .block-container:has(.st-key-sot_pane) .st-key-actions_card { flex: 2 1 0 !important; }
  /* the wrapper holding a scroll region fills its card */
  .block-container:has(.st-key-sot_pane) .st-key-sot_card > div[data-testid="stLayoutWrapper"],
  .block-container:has(.st-key-sot_pane) .st-key-final_card > div[data-testid="stLayoutWrapper"],
  .block-container:has(.st-key-sot_pane) .st-key-chat_card > div[data-testid="stLayoutWrapper"],
  .block-container:has(.st-key-sot_pane) .st-key-actions_card > div[data-testid="stLayoutWrapper"] {
      flex: 1 1 0 !important; min-height: 0 !important; height: auto !important;
      display: flex !important; flex-direction: column !important;
  }
  /* scroll regions take the remaining space and scroll */
  .block-container:has(.st-key-sot_pane) .st-key-sot_pane,
  .block-container:has(.st-key-sot_pane) .st-key-final_pane,
  .block-container:has(.st-key-sot_pane) .st-key-chat_scroll,
  .block-container:has(.st-key-sot_pane) .st-key-actions_scroll {
      flex: 1 1 0 !important; min-height: 0 !important;
      height: auto !important; overflow: auto !important;
  }
</style>
""",
        unsafe_allow_html=True,
    )


def _view_sub(sub: dict) -> dict:
    proj = sub["projected"]
    return {
        **sub,
        "vendor": proj["vendor"],
        "payment_method": proj["payment_method"],
        "line_items": proj["line_items"],
        "file_names": proj["file_names"],
        "reference_files": sub.get("reference_files", []),
    }


def _header(sub: dict, client_name: str) -> None:
    title = sub.get("vendor") or "Review submission"
    st.markdown(
        f"<div class='bb-crumbs'>Firm Workspace / {client_name} / {sub['id']}</div>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-top:1px'>"
        f"<span class='bb-page-title'>{title}</span>{badge(sub['state'])}</div>"
        f"<div class='bb-page-sub'>{client_name} · created {sub.get('created_at', '—')}</div>"
        "<hr class='bb-divider'/>",
        unsafe_allow_html=True,
    )


def _render_processing(api, sub: dict) -> None:
    with st.container(border=True):
        st.markdown("### ⏳ Reading documents")
        st.markdown(
            "<div class='bb-muted'>The vision model is reading your uploads and building the "
            "Source of Truth. This usually takes a few seconds.</div>",
            unsafe_allow_html=True,
        )
        st.write("")
        _watch_extraction(api, sub["id"])


@st.fragment(run_every=3)
def _watch_extraction(api, submission_id: str) -> None:
    latest = api.get_submission(submission_id)
    if latest and latest.get("state") != "RAW":
        st.rerun(scope="app")
        return
    st.caption("Extraction in progress — this page refreshes automatically.")
    if st.button("Refresh now", type="primary", key="refresh_processing"):
        st.rerun(scope="app")


def _render_sot_pane(sub: dict, client_name: str, threshold: float) -> None:
    with st.container(border=True, key="sot_card"):
        section("Source of Truth")
        if sub["projected"].get("has_pending"):
            _pending_banner("Projected result of the pending plan — not committed yet.")
        with st.container(key="sot_pane", height=320):
            sot_document.render(_view_sub(sub), client_name, threshold)


def _render_final_pane(api, sub: dict, threshold: float) -> None:
    proj = sub["projected"]
    with st.container(border=True, key="final_card"):
        section("Final data")
        if proj.get("has_pending"):
            _pending_banner("Projected result of the pending plan — not committed yet.")
        with st.container(key="final_pane", height=320):
            st.markdown("<div class='bb-doc-label'>Line items</div>", unsafe_allow_html=True)
            st.markdown(line_items_html(proj["line_items"], threshold), unsafe_allow_html=True)

            st.markdown("<div class='bb-doc-label' style='margin-top:18px'>Journal entry</div>",
                        unsafe_allow_html=True)
            entry = sub.get("journal_entry") or api.preview_journal(sub["id"])
            if not entry:
                st.info("No business line items to post yet.")
            else:
                st.markdown(journal_html(entry), unsafe_allow_html=True)
                st.markdown(balance_banner(entry), unsafe_allow_html=True)


def _render_chat_pane(sub: dict, api) -> None:
    with st.container(border=True, key="chat_card"):
        section("Chat")
        pending = st.session_state.get("_pending_msg")

        with st.container(key="chat_scroll", height=360):
            _render_attach_staging(sub, api)

            history = api.chat_history(sub["id"])
            if not history and not pending:
                st.info("No conversation yet.")
            for msg in history:
                avatar = "🤖" if msg["role"] == "agent" else "🧑‍💼"
                with st.chat_message("assistant" if msg["role"] == "agent" else "user", avatar=avatar):
                    st.markdown(msg["content"])

            if pending:
                with st.chat_message("user", avatar="🧑‍💼"):
                    st.markdown(pending)
                with st.chat_message("assistant", avatar="🤖"):
                    with st.spinner("Agent is thinking…"):
                        try:
                            result = api.chat(sub["id"], pending)
                        except Exception as exc:  # noqa: BLE001
                            result = {"error": str(exc)}
                    if result.get("error"):
                        st.toast(result["error"], icon="⚠️")
                st.session_state.pop("_pending_msg", None)
                st.rerun()

            plan_component.render_plan(api, sub)

        if sub["state"] != "COMMITTED":
            value = st.chat_input(
                "Message the agent, or attach documents…",
                accept_file="multiple",
                disabled=bool(pending),
            )
            if value:
                text = getattr(value, "text", "") or ""
                files = list(getattr(value, "files", []) or [])
                if files:
                    st.session_state["_staged_files"] = files
                if text.strip():
                    st.session_state["_pending_msg"] = text.strip()
                st.rerun()


def _render_attach_staging(sub: dict, api) -> None:
    staged = st.session_state.get("_staged_files") or []
    if not staged:
        return

    with st.container(border=True):
        st.markdown("**Attached — choose what to save to the submission**")
        st.markdown(
            "<div class='bb-muted'>Unchecked files stay as chat reference only and won't recompute anything.</div>",
            unsafe_allow_html=True,
        )
        flags = {}
        for i, f in enumerate(staged):
            flags[i] = st.checkbox(f.name, value=True, key=f"savefile_{i}_{f.name}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Stage files", type="primary", use_container_width=True, key="stage_files_btn"):
                payload = [{"name": f.name, "save": flags[i]} for i, f in enumerate(staged)]
                result = api.stage_files(sub["id"], payload)
                if result.get("error"):
                    st.toast(result["error"], icon="⚠️")
                st.session_state.pop("_staged_files", None)
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="cancel_files_btn"):
                st.session_state.pop("_staged_files", None)
                st.rerun()


def _render_actions_pane(sub: dict, api) -> None:
    with st.container(border=True, key="actions_card"):
        section("Actions")
        with st.container(key="actions_scroll", height=240):
            tasks_component.render_task_list(api, sub)
        _render_actions(sub, api)


def _pending_banner(text: str) -> None:
    st.markdown(f"<div class='bb-pending-banner'>⏳ {text}</div>", unsafe_allow_html=True)


def _render_actions(sub: dict, api) -> None:
    state = sub["state"]
    has_pending = sub["projected"].get("has_pending")

    if state == "COMMITTED":
        st.success("Posted to the ledger.", icon="✅")
        if st.button("View in ledger →", use_container_width=True, key="go_ledger_from_chat"):
            entry = sub.get("journal_entry") or {}
            go("ledger", client_id=sub["client_id"], highlighted=entry.get("id"))
        return

    if state == "BLOCKED_COMPLIANCE":
        st.error(sub.get("blocker", "Blocked on compliance."))
        if st.button("Mark compliance resolved", use_container_width=True, key="resolve_compliance"):
            result = api.resolve_compliance(sub["id"])
            if result.get("error"):
                st.toast(result["error"], icon="⚠️")
            st.rerun()
        return

    if st.button(
        "✅ Approve & Post to Ledger",
        type="primary",
        use_container_width=True,
        key="approve_post",
        disabled=bool(has_pending),
    ):
        result = api.approve(sub["id"])
        if result.get("error"):
            st.error(result["error"])
        else:
            st.rerun()
    if has_pending:
        st.markdown(
            "<div class='bb-muted'>Execute or discard the pending plan to enable posting.</div>",
            unsafe_allow_html=True,
        )