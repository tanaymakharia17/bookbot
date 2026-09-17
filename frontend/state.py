import streamlit as st

DEFAULT_VIEW = "clients"
DEFAULT_THEME = "light"


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


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

def get_theme() -> str:
    return st.session_state.get("_theme", DEFAULT_THEME)


def toggle_theme() -> None:
    """Flip the theme (use as a widget callback; Streamlit reruns after)."""
    new_theme = "dark" if get_theme() == "light" else "light"
    st.session_state["_theme"] = new_theme
    # Internal hint: applies Streamlit's native theme to future sessions/reloads.
    try:
        st._config.set_option("theme.base", new_theme)
    except Exception:  # noqa: BLE001 - unsupported in some versions
        pass


# ---------------------------------------------------------------------------
# Collapsible review sections
# ---------------------------------------------------------------------------

def is_collapsed(name: str) -> bool:
    return bool(st.session_state.get("_collapsed", {}).get(name))


def toggle_collapsed(name: str) -> None:
    state = dict(st.session_state.get("_collapsed", {}))
    state[name] = not state.get(name, False)
    st.session_state["_collapsed"] = state
    st.rerun()


# ---------------------------------------------------------------------------
# Full-size section modal
# ---------------------------------------------------------------------------

def open_modal(name: str) -> None:
    st.session_state["_modal"] = name
    st.rerun()


def close_modal() -> None:
    st.session_state.pop("_modal", None)


def current_modal() -> str | None:
    return st.session_state.get("_modal")