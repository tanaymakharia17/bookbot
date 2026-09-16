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

from styles import inject_css  # noqa: E402

inject_css()

from state import current_view  # noqa: E402
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