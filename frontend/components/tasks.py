import html

import streamlit as st

from mock_backend import TASK_CATALOG


def render_task_list(api, sub: dict) -> None:
    proj = sub["projected"]
    tasks = proj["tasks"]
    done = sum(1 for t in tasks if t["done"])
    read_only = sub["state"] == "COMMITTED"

    st.markdown(
        f"**Action checklist** <span class='bb-muted'>· {done}/{len(tasks)} done</span>",
        unsafe_allow_html=True,
    )

    if proj.get("has_pending"):
        st.markdown(
            "<div class='bb-muted'>Checkbox state is projected — it commits when you execute the plan.</div>",
            unsafe_allow_html=True,
        )

    pending_ids = _pending_task_ids(sub)

    if not tasks:
        st.caption("No action items yet.")
    for task in tasks:
        _task_row(api, sub, task, read_only, task["id"] in pending_ids)

    if read_only:
        return

    with st.expander("Add an action"):
        col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
        with col1:
            custom = st.text_input(
                "Custom task", key="new_task_title", label_visibility="collapsed",
                placeholder="Custom task…",
            )
        with col2:
            if st.button("Add", key="add_task_btn", use_container_width=True):
                if custom.strip():
                    _stage(api, sub, "stage_task_add", title=custom.strip())
        quick = st.selectbox("From catalog", ["— choose —"] + TASK_CATALOG, key="quick_task")
        if quick != "— choose —" and st.button("Add selected action", key="add_quick"):
            _stage(api, sub, "stage_task_add", title=quick)


def _task_row(api, sub: dict, task: dict, read_only: bool, pending: bool) -> None:
    cols = st.columns([0.12, 0.78, 0.1], vertical_alignment="center")

    with cols[0]:
        if read_only:
            st.markdown("☑" if task["done"] else "☐")
        else:
            if st.button("☑" if task["done"] else "☐", key=f"tgl_{task['id']}"):
                _stage(api, sub, "stage_task_toggle", task_id=task["id"], done=not task["done"])

    with cols[1]:
        title = html.escape(task["title"])
        if task["done"]:
            title = f"<span class='bb-task-done'>{title}</span>"
        source = "Agent" if task["source"] == "agent" else "Manual"
        pending_chip = "<span class='bb-chip bb-chip-pending'>pending</span>" if pending else ""
        st.markdown(
            f"<span class='bb-task-title'>{title}</span> "
            f"<span class='bb-chip bb-src-{task['source']}'>{source}</span> {pending_chip}",
            unsafe_allow_html=True,
        )

    with cols[2]:
        if not read_only and st.button("✕", key=f"rm_{task['id']}"):
            _stage(api, sub, "stage_task_remove", task_id=task["id"])


def _pending_task_ids(sub: dict) -> set[str]:
    ids: set[str] = set()
    plan = sub.get("pending_plan") or {}
    for op in plan.get("task_ops", []):
        if op["type"] == "add":
            ids.add(op["task"]["id"])
        elif op.get("task_id"):
            ids.add(op["task_id"])
    return ids


def _stage(api, sub: dict, method: str, **kwargs) -> None:
    result = getattr(api, method)(sub["id"], **kwargs)
    if isinstance(result, dict) and result.get("error"):
        st.toast(result["error"], icon="⚠️")
    st.rerun()