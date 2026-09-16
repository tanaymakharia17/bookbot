import streamlit as st

DEFAULT_VIEW = "clients"


def current_view() -> str:
    return st.session_state.get("view", DEFAULT_VIEW)


def go(view: str, **params) -> None:
    """Navigate to a view, setting any context params, then rerun."""
    st.session_state["view"] = view
    for key, value in params.items():
        st.session_state[key] = value
    st.rerun()


def require(view: str, **params) -> bool:
    """Guard: if a required session key is missing, bounce to `view`.

    Returns True when the context is valid, False when a redirect happened.
    """
    missing = [k for k, v in params.items() if v is None]
    if missing:
        go(view)
        return False
    return True