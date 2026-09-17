import streamlit as st

from state import is_collapsed, open_modal, toggle_collapsed


def page_header(crumbs: str, title: str, subtitle: str = "") -> None:
    sub = f"<div class='bb-page-sub'>{subtitle}</div>" if subtitle else ""
    st.markdown(
        f"<div class='bb-crumbs'>{crumbs}</div>"
        f"<div class='bb-page-title'>{title}</div>{sub}",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='bb-divider'/>", unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f"<div class='bb-section'>{title}</div>", unsafe_allow_html=True)


def section_bar(title: str, key: str) -> None:
    """Section title with collapse and full-size actions."""
    collapsed = is_collapsed(key)
    cols = st.columns([10, 1, 1], vertical_alignment="center")
    with cols[0]:
        st.markdown(f"<div class='bb-section'>{title}</div>", unsafe_allow_html=True)
    with cols[1]:
        st.button(
            "▸" if collapsed else "▾",
            key=f"collapse_{key}",
            help="Expand" if collapsed else "Collapse",
            on_click=toggle_collapsed,
            args=(key,),
            use_container_width=True,
        )
    with cols[2]:
        st.button(
            "⤢",
            key=f"fullsize_{key}",
            help="Open full size",
            on_click=open_modal,
            args=(key,),
            use_container_width=True,
        )


def metric(label: str, value: str) -> str:
    return (
        f"<div class='bb-metric'><div class='bb-metric-val'>{value}</div>"
        f"<div class='bb-metric-lab'>{label}</div></div>"
    )


def empty_state(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='bb-empty'><div class='bb-empty-icon'>{icon}</div>"
        f"<div class='bb-empty-title'>{title}</div>"
        f"<div class='bb-empty-sub'>{subtitle}</div></div>",
        unsafe_allow_html=True,
    )


def error_box(message: str) -> None:
    st.error(message)


def back_button(label: str, view: str, **params) -> None:
    from state import go

    if st.button(f"← {label}", key=f"back_{view}"):
        go(view, **params)