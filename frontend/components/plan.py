import html

import streamlit as st


def render_plan(api, sub: dict) -> bool:
    labels = sub.get("plan_labels") or []
    if not labels:
        return False

    with st.container(border=True):
        st.markdown("**Pending plan**")
        st.markdown(
            "<div class='bb-muted'>Nothing is applied until you execute.</div>",
            unsafe_allow_html=True,
        )
        for item in labels:
            cols = st.columns([0.85, 0.15], vertical_alignment="center")
            with cols[0]:
                st.markdown(
                    f"<div class='bb-plan-item'>{html.escape(item['label'])}</div>",
                    unsafe_allow_html=True,
                )
            with cols[1]:
                if st.button("✕", key=f"rmop_{item['id']}"):
                    api.remove_plan_op(sub["id"], item["id"])
                    st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("▶ Execute plan", type="primary", use_container_width=True, key="execute_plan"):
                result = api.execute_plan(sub["id"])
                if result.get("error"):
                    st.toast(result["error"], icon="⚠️")
                st.rerun()
        with c2:
            if st.button("Discard", use_container_width=True, key="discard_plan"):
                api.discard_plan(sub["id"])
                st.rerun()
    return True