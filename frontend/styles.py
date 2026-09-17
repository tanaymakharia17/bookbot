import streamlit as st

LIGHT_VARS = """
:root {
    --bb-bg: #F5F7FA;
    --bb-surface: #FFFFFF;
    --bb-surface-2: #F2F4F7;
    --bb-border: #E4E7EC;
    --bb-border-subtle: #F2F4F7;
    --bb-border-strong: #D0D5DD;
    --bb-row-hover: #FAFBFC;
    --bb-text: #101828;
    --bb-text-2: #344054;
    --bb-muted: #667085;
    --bb-faint: #98A2B3;
    --bb-accent: #1570EF;
    --bb-accent-hover: #175CD3;
    --bb-accent-weak: #EFF8FF;
    --bb-accent-border: #B2DDFF;
    --bb-success: #067647;
    --bb-success-weak: #ECFDF3;
    --bb-success-border: #A6F4C5;
    --bb-warning: #B54708;
    --bb-warning-weak: #FFFAEB;
    --bb-warning-border: #FEDF89;
    --bb-danger: #B42318;
    --bb-danger-weak: #FEF3F2;
    --bb-danger-border: #FECDCA;
    --bb-purple: #5925DC;
    --bb-purple-weak: #F4F3FF;
    --bb-on-accent: #FFFFFF;
    --bb-code-bg: #F8FAFC;
}
"""

DARK_VARS = """
:root {
    --bb-bg: #0B1220;
    --bb-surface: #111A2B;
    --bb-surface-2: #16202F;
    --bb-border: #223046;
    --bb-border-subtle: #1A2434;
    --bb-border-strong: #33415A;
    --bb-row-hover: #141E2D;
    --bb-text: #E6EDF5;
    --bb-text-2: #C7D2DF;
    --bb-muted: #98A5B5;
    --bb-faint: #7A8798;
    --bb-accent: #4F8DF7;
    --bb-accent-hover: #6BA0FF;
    --bb-accent-weak: #152238;
    --bb-accent-border: #1E3A66;
    --bb-success: #34D399;
    --bb-success-weak: #0E2A1F;
    --bb-success-border: #14532D;
    --bb-warning: #FBBF24;
    --bb-warning-weak: #2B2110;
    --bb-warning-border: #5A4415;
    --bb-danger: #F87171;
    --bb-danger-weak: #2B1516;
    --bb-danger-border: #5A2224;
    --bb-purple: #A78BFA;
    --bb-purple-weak: #1E1B33;
    --bb-on-accent: #FFFFFF;
    --bb-code-bg: #0E1726;
}
"""

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
.stApp { background: var(--bb-bg); }

header[data-testid="stHeader"] { display: none; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
section[data-testid="stSidebar"] { display: none; }
div[data-testid="stToolbar"] { display: none; }

.block-container {
    padding-top: 0.8rem;
    padding-bottom: 1.5rem;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
    max-width: 100%;
}

div[data-testid="stVerticalBlock"] { gap: 0.6rem !important; min-width: 0 !important; }
div[data-testid="stHorizontalBlock"] > div { min-width: 0 !important; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bb-border-strong); border-radius: 6px; border: 2px solid transparent; background-clip: content-box; }
::-webkit-scrollbar-thumb:hover { background: var(--bb-muted); background-clip: content-box; }

h1, h2, h3, h4 { color: var(--bb-text); letter-spacing: -0.01em; }
p, span, label, div { color: var(--bb-text-2); }

.bb-muted { color: var(--bb-muted); font-size: 0.85rem; overflow-wrap: anywhere; }
.bb-warning-text { color: var(--bb-warning); font-size: 0.82rem; font-weight: 600; }
.bb-page-title { font-size: 1.45rem; font-weight: 700; margin: 0; color: var(--bb-text); line-height: 1.2; }
.bb-page-sub { color: var(--bb-muted); font-size: 0.85rem; margin-top: 1px; }
.bb-crumbs { color: var(--bb-faint); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; }
.bb-divider { height: 1px; background: var(--bb-border); margin: 0.7rem 0; border: none; }
.bb-strong { font-weight: 600; color: var(--bb-text); }

.bb-section { display: flex; align-items: center; gap: 8px; font-size: 0.92rem; font-weight: 700; color: var(--bb-text); margin: 0; }
.bb-section::before { content: ''; width: 4px; height: 15px; border-radius: 2px; background: var(--bb-accent); }

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bb-surface);
    border: 1px solid var(--bb-border) !important;
    border-radius: 12px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow: 0 4px 14px rgba(16, 24, 40, 0.07); }

.bb-client-name { font-size: 1.02rem; font-weight: 600; color: var(--bb-text); }

.bb-badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; white-space: nowrap; }
.bb-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }

.bb-chip { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; background: var(--bb-surface-2); color: var(--bb-text-2); white-space: nowrap; }
.bb-chip-capex { background: var(--bb-warning-weak); color: var(--bb-warning); }
.bb-chip-personal { background: var(--bb-danger-weak); color: var(--bb-danger); }
.bb-chip-ok { background: var(--bb-success-weak); color: var(--bb-success); }

.bb-metric { background: var(--bb-surface); border: 1px solid var(--bb-border); border-radius: 10px; padding: 10px 13px; }
.bb-metric-val { font-size: 1.3rem; font-weight: 700; color: var(--bb-text); line-height: 1.1; }
.bb-metric-lab { font-size: 0.72rem; color: var(--bb-muted); font-weight: 500; margin-top: 2px; }

.bb-empty { text-align: center; padding: 40px 20px; background: var(--bb-surface); border: 1px dashed var(--bb-border-strong); border-radius: 12px; }
.bb-empty-icon { font-size: 2rem; }
.bb-empty-title { font-weight: 600; color: var(--bb-text-2); margin-top: 6px; }
.bb-empty-sub { color: var(--bb-faint); font-size: 0.86rem; }

div[data-testid="stChatMessage"] { background: var(--bb-surface); border: 1px solid var(--bb-border); border-radius: 10px; padding: 2px 4px; }

.stButton > button, .stButton > button p, .stButton > button div, .stButton > button span { font-weight: 600; }

button[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"] { background: var(--bb-accent) !important; border: none !important; }
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] div,
button[data-testid="stBaseButton-primary"] span,
.stButton > button[kind="primary"] p { color: var(--bb-on-accent) !important; fill: var(--bb-on-accent) !important; }
button[data-testid="stBaseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover { background: var(--bb-accent-hover) !important; }
button[data-testid="stBaseButton-primary"]:disabled,
button[data-testid="stBaseButton-primary"][disabled],
.stButton > button[kind="primary"]:disabled { background: var(--bb-border-strong) !important; cursor: not-allowed !important; }
button[data-testid="stBaseButton-primary"]:disabled p,
.stButton > button[kind="primary"]:disabled p { color: var(--bb-surface) !important; }

button[data-testid="stBaseButton-secondary"],
.stButton > button[kind="secondary"] { background: var(--bb-surface) !important; border: 1px solid var(--bb-border-strong) !important; }
button[data-testid="stBaseButton-secondary"] p,
.stButton > button[kind="secondary"] p { color: var(--bb-text-2) !important; }
button[data-testid="stBaseButton-secondary"]:hover,
.stButton > button[kind="secondary"]:hover { border-color: var(--bb-accent) !important; }
button[data-testid="stBaseButton-secondary"]:hover p { color: var(--bb-accent) !important; }

div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-selected="true"] { background: var(--bb-accent) !important; border-color: var(--bb-accent) !important; }
div[data-testid="stButtonGroup"] button[aria-checked="true"] p,
div[data-testid="stButtonGroup"] button[aria-selected="true"] p { color: var(--bb-on-accent) !important; }

div[data-testid="stAlert"] { border-radius: 10px; border: 1px solid var(--bb-border); background: var(--bb-surface); }
div[data-testid="stAlert"] p { color: var(--bb-text-2) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) { background: var(--bb-accent-weak); border-color: var(--bb-accent-border); }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) p { color: var(--bb-accent-hover) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) { background: var(--bb-success-weak); border-color: var(--bb-success-border); }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) p { color: var(--bb-success) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) { background: var(--bb-warning-weak); border-color: var(--bb-warning-border); }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) p { color: var(--bb-warning) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) { background: var(--bb-danger-weak); border-color: var(--bb-danger-border); }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) p { color: var(--bb-danger) !important; }

.bb-doc-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.bb-doc-title { font-size: 1rem; font-weight: 700; color: var(--bb-text); }
.bb-doc-id { font-size: 0.75rem; color: var(--bb-faint); font-family: 'SFMono-Regular', Menlo, monospace; margin-top: 1px; }

.bb-meta-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px 18px; padding: 12px 0; border-top: 1px solid var(--bb-border-subtle); border-bottom: 1px solid var(--bb-border-subtle); }
.bb-meta-item .k { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--bb-faint); font-weight: 600; }
.bb-meta-item .v { font-size: 0.9rem; color: var(--bb-text); font-weight: 500; margin-top: 1px; word-break: break-word; }

.bb-doc-section { margin-top: 14px; }
.bb-doc-label { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--bb-faint); font-weight: 600; margin-bottom: 6px; }
.bb-doc-text { font-size: 0.88rem; color: var(--bb-text-2); line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }
.bb-files { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.bb-file { font-size: 0.75rem; color: var(--bb-text-2); background: var(--bb-surface-2); border-radius: 6px; padding: 2px 8px; }

.bb-table-scroll { width: 100%; overflow-x: auto; }
.bb-table { width: 100%; min-width: max-content; border-collapse: collapse; font-size: 0.86rem; }
.bb-table th { text-align: left; font-weight: 600; color: var(--bb-muted); border-bottom: 1px solid var(--bb-border); padding: 7px 9px; font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap; }
.bb-table td { padding: 9px 9px; border-bottom: 1px solid var(--bb-border-subtle); color: var(--bb-text-2); vertical-align: top; }
.bb-table tbody tr:last-child td { border-bottom: none; }
.bb-table tr:hover td { background: var(--bb-row-hover); }
.bb-num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.bb-row-personal td { color: var(--bb-faint); }
.bb-row-personal td:nth-child(2) { text-decoration: line-through; }
.bb-row-total td { border-top: 2px solid var(--bb-border); font-weight: 700; color: var(--bb-text); }

.bb-totals { display: flex; gap: 28px; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--bb-border-subtle); }
.bb-total { display: flex; flex-direction: column; }
.bb-total span { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--bb-faint); font-weight: 600; }
.bb-total b { font-size: 1.15rem; color: var(--bb-text); margin-top: 1px; }
.bb-total.muted b { color: var(--bb-faint); font-size: 0.95rem; }

.bb-balance { display: flex; align-items: center; gap: 8px; margin-top: 12px; padding: 9px 12px; border-radius: 9px; font-weight: 600; font-size: 0.85rem; }
.bb-balance.ok { background: var(--bb-success-weak); color: var(--bb-success); }
.bb-balance.bad { background: var(--bb-danger-weak); color: var(--bb-danger); }

.bb-pending-banner { background: var(--bb-warning-weak); color: var(--bb-warning); border: 1px solid var(--bb-warning-border); border-radius: 9px; padding: 7px 11px; font-size: 0.8rem; font-weight: 600; margin-bottom: 8px; }
.bb-plan-item { font-size: 0.84rem; color: var(--bb-text-2); padding: 2px 0; }

.bb-task-title { font-size: 0.86rem; color: var(--bb-text); }
.bb-task-done { text-decoration: line-through; color: var(--bb-faint); }
.bb-src-agent { background: var(--bb-accent-weak); color: var(--bb-accent-hover); }
.bb-src-user { background: var(--bb-surface-2); color: var(--bb-text-2); }
.bb-chip-pending { background: var(--bb-warning-weak); color: var(--bb-warning); margin-left: 2px; }

.bb-collapsed-note { font-size: 0.8rem; color: var(--bb-faint); margin: 2px 0 0 0; }
"""

# Extra overrides so Streamlit's native widgets follow the dark palette.
DARK_OVERRIDES = """
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--bb-bg) !important; }

div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="base-input"],
div[data-baseweb="select"] > div, div[data-baseweb="popover"] div[data-baseweb="menu"] {
    background-color: var(--bb-surface) !important;
    border-color: var(--bb-border-strong) !important;
}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] input, div[data-baseweb="select"] span {
    color: var(--bb-text) !important;
}
/* scoped by widget so base-web's own white wins don't leak through */
div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stTextInput"] div[data-baseweb="base-input"],
div[data-testid="stNumberInput"] div[data-baseweb="input"],
div[data-testid="stTextArea"] div[data-baseweb="textarea"],
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] div[data-baseweb="input"] {
    background-color: var(--bb-surface) !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea {
    background: transparent !important;
    color: var(--bb-text) !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stNumberInput"] input::placeholder {
    color: var(--bb-faint) !important;
}
div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
    background-color: var(--bb-surface) !important;
}
li[role="option"], div[role="option"] { color: var(--bb-text-2) !important; }
li[role="option"]:hover, div[role="option"]:hover { background: var(--bb-surface-2) !important; }

div[data-testid="stChatInput"], div[data-testid="stChatInput"] > div {
    background: var(--bb-surface) !important;
    border-color: var(--bb-border-strong) !important;
}
div[data-testid="stChatInput"] textarea { color: var(--bb-text) !important; background: transparent !important; }

section[data-testid="stFileUploaderDropzone"] {
    background: var(--bb-surface) !important;
    border-color: var(--bb-border-strong) !important;
}
section[data-testid="stFileUploaderDropzone"] span, section[data-testid="stFileUploaderDropzone"] small {
    color: var(--bb-text-2) !important;
}

div[data-testid="stDialog"] > div, div[role="dialog"] > div {
    background: var(--bb-surface) !important;
    color: var(--bb-text) !important;
}

pre, code, .stCode, div[data-testid="stCodeBlock"] { background: var(--bb-code-bg) !important; color: var(--bb-text) !important; }

button[data-baseweb="tab"] { color: var(--bb-text-2) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--bb-accent) !important; }
div[data-baseweb="tab-highlight"] { background-color: var(--bb-accent) !important; }
div[data-baseweb="tab-border"] { background-color: var(--bb-border) !important; }

label[data-baseweb="checkbox"] span { color: var(--bb-text-2) !important; }
div[data-testid="stSpinner"] p, div[data-testid="stSpinner"] i { color: var(--bb-text-2) !important; }
"""


def inject_css(theme: str = "light") -> None:
    palette = DARK_VARS if theme == "dark" else LIGHT_VARS
    overrides = DARK_OVERRIDES if theme == "dark" else ""
    st.markdown(f"<style>{palette}\n{BASE_CSS}\n{overrides}</style>", unsafe_allow_html=True)