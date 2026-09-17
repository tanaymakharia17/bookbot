import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Bookbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from state import current_view, get_theme, toggle_theme  # noqa: E402
from styles import inject_css  # noqa: E402

inject_css(get_theme())

# Global theme toggle (top-right, every page)
_spacer, _theme_col = st.columns([8, 1], vertical_alignment="center")
with _theme_col:
    st.button(
        "🌙 Dark" if get_theme() == "light" else "☀️ Light",
        key="_theme_toggle",
        use_container_width=True,
        on_click=toggle_theme,
        help="Switch between light and dark mode",
    )

from views import (  # noqa: E402
    chat_workspace,
    client_list,
    ledger,
    ledger_entry,
    new_submission,
    submissions,
)

ROUTES = {
    "clients": client_list.render,
    "submissions": submissions.render,
    "new_submission": new_submission.render,
    "chat": chat_workspace.render,
    "ledger": ledger.render,
    "ledger_entry": ledger_entry.render,
}

view = current_view()
ROUTES.get(view, client_list.render)()