import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bb-bg: #F5F7FA;
    --bb-surface: #FFFFFF;
    --bb-border: #E4E7EC;
    --bb-border-strong: #D0D5DD;
    --bb-text: #101828;
    --bb-text-2: #344054;
    --bb-muted: #667085;
    --bb-faint: #98A2B3;
    --bb-accent: #1570EF;
    --bb-accent-hover: #175CD3;
    --bb-accent-weak: #EFF8FF;
    --bb-success: #067647;
    --bb-success-weak: #ECFDF3;
    --bb-warning: #B54708;
    --bb-warning-weak: #FFFAEB;
    --bb-danger: #B42318;
    --bb-danger-weak: #FEF3F2;
    --bb-purple: #5925DC;
    --bb-purple-weak: #F4F3FF;
}

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

/* tighten default vertical rhythm so headers don't eat the viewport */
div[data-testid="stVerticalBlock"] { gap: 0.6rem !important; min-width: 0 !important; }
div[data-testid="stHorizontalBlock"] > div { min-width: 0 !important; }

/* nicer scrollbars */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D0D5DD; border-radius: 6px; border: 2px solid transparent; background-clip: content-box; }
::-webkit-scrollbar-thumb:hover { background: #98A2B3; background-clip: content-box; }

/* ---------- Typography ---------- */
h1, h2, h3, h4 { color: var(--bb-text); letter-spacing: -0.01em; }
p, span, label, div { color: var(--bb-text-2); }

.bb-muted { color: var(--bb-muted); font-size: 0.85rem; overflow-wrap: anywhere; }
.bb-page-title { font-size: 1.45rem; font-weight: 700; margin: 0; color: var(--bb-text); line-height: 1.2; }
.bb-page-sub { color: var(--bb-muted); font-size: 0.85rem; margin-top: 1px; }
.bb-crumbs { color: var(--bb-faint); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; }
.bb-divider { height: 1px; background: var(--bb-border); margin: 0.7rem 0; border: none; }
.bb-strong { font-weight: 600; color: var(--bb-text); }

.bb-section { display: flex; align-items: center; gap: 8px; font-size: 0.92rem; font-weight: 700; color: var(--bb-text); margin: 0 0 8px 0; }
.bb-section::before { content: ''; width: 4px; height: 15px; border-radius: 2px; background: var(--bb-accent); }

/* ---------- Cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bb-surface);
    border: 1px solid var(--bb-border) !important;
    border-radius: 12px;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 14px rgba(16, 24, 40, 0.07);
}

.bb-client-name { font-size: 1.02rem; font-weight: 600; color: var(--bb-text); }

/* ---------- Badges / chips ---------- */
.bb-badge { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; white-space: nowrap; }
.bb-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }

.bb-chip { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; background: #F2F4F7; color: var(--bb-text-2); white-space: nowrap; }
.bb-chip-capex { background: var(--bb-warning-weak); color: var(--bb-warning); }
.bb-chip-personal { background: var(--bb-danger-weak); color: var(--bb-danger); }
.bb-chip-ok { background: var(--bb-success-weak); color: var(--bb-success); }

/* ---------- Metric strip ---------- */
.bb-metric { background: var(--bb-surface); border: 1px solid var(--bb-border); border-radius: 10px; padding: 10px 13px; }
.bb-metric-val { font-size: 1.3rem; font-weight: 700; color: var(--bb-text); line-height: 1.1; }
.bb-metric-lab { font-size: 0.72rem; color: var(--bb-muted); font-weight: 500; margin-top: 2px; }

/* ---------- Empty state ---------- */
.bb-empty { text-align: center; padding: 40px 20px; background: var(--bb-surface); border: 1px dashed var(--bb-border-strong); border-radius: 12px; }
.bb-empty-icon { font-size: 2rem; }
.bb-empty-title { font-weight: 600; color: var(--bb-text-2); margin-top: 6px; }
.bb-empty-sub { color: var(--bb-faint); font-size: 0.86rem; }

/* ---------- Chat ---------- */
div[data-testid="stChatMessage"] { background: var(--bb-surface); border: 1px solid var(--bb-border); border-radius: 10px; padding: 2px 4px; }

/* ---------- Buttons (explicit contrast) ---------- */
.stButton > button,
.stButton > button p,
.stButton > button div,
.stButton > button span { font-weight: 600; }

button[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"] { background: var(--bb-accent) !important; border: none !important; }
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] div,
button[data-testid="stBaseButton-primary"] span,
.stButton > button[kind="primary"] p { color: #FFFFFF !important; fill: #FFFFFF !important; }
button[data-testid="stBaseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover { background: var(--bb-accent-hover) !important; }

button[data-testid="stBaseButton-primary"]:disabled,
button[data-testid="stBaseButton-primary"][disabled],
.stButton > button[kind="primary"]:disabled {
    background: #B2DDFF !important; cursor: not-allowed !important;
}
button[data-testid="stBaseButton-primary"]:disabled p,
.stButton > button[kind="primary"]:disabled p { color: #FFFFFF !important; }

button[data-testid="stBaseButton-secondary"],
.stButton > button[kind="secondary"] { background: var(--bb-surface) !important; border: 1px solid var(--bb-border-strong) !important; }
button[data-testid="stBaseButton-secondary"] p,
.stButton > button[kind="secondary"] p { color: var(--bb-text-2) !important; }
button[data-testid="stBaseButton-secondary"]:hover,
.stButton > button[kind="secondary"]:hover { border-color: var(--bb-accent) !important; }
button[data-testid="stBaseButton-secondary"]:hover p { color: var(--bb-accent) !important; }

/* ---------- Pills / segmented filter ---------- */
div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-selected="true"] { background: var(--bb-accent) !important; border-color: var(--bb-accent) !important; }
div[data-testid="stButtonGroup"] button[aria-checked="true"] p,
div[data-testid="stButtonGroup"] button[aria-selected="true"] p { color: #FFFFFF !important; }

/* ---------- Alerts (readable tinted surfaces) ---------- */
div[data-testid="stAlert"] { border-radius: 10px; border: 1px solid var(--bb-border); background: var(--bb-surface); }
div[data-testid="stAlert"] p { color: var(--bb-text-2) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) { background: var(--bb-accent-weak); border-color: #B2DDFF; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) p { color: var(--bb-accent-hover) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) { background: var(--bb-success-weak); border-color: #A6F4C5; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) p { color: var(--bb-success) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) { background: var(--bb-warning-weak); border-color: #FEDF89; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) p { color: var(--bb-warning) !important; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) { background: var(--bb-danger-weak); border-color: #FECDCA; }
div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) p { color: var(--bb-danger) !important; }

/* ---------- Source of Truth document ---------- */
.bb-doc-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.bb-doc-title { font-size: 1rem; font-weight: 700; color: var(--bb-text); }
.bb-doc-id { font-size: 0.75rem; color: var(--bb-faint); font-family: 'SFMono-Regular', Menlo, monospace; margin-top: 1px; }

.bb-meta-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px 18px; padding: 12px 0; border-top: 1px solid #F2F4F7; border-bottom: 1px solid #F2F4F7; }
.bb-meta-item .k { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--bb-faint); font-weight: 600; }
.bb-meta-item .v { font-size: 0.9rem; color: var(--bb-text); font-weight: 500; margin-top: 1px; word-break: break-word; }

.bb-doc-section { margin-top: 14px; }
.bb-doc-label { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--bb-faint); font-weight: 600; margin-bottom: 6px; }
.bb-doc-text { font-size: 0.88rem; color: var(--bb-text-2); line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }
.bb-files { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.bb-file { font-size: 0.75rem; color: var(--bb-text-2); background: #F2F4F7; border-radius: 6px; padding: 2px 8px; }

/* ---------- Data tables ---------- */
.bb-table-scroll { width: 100%; overflow-x: auto; }
.bb-table { width: 100%; min-width: max-content; border-collapse: collapse; font-size: 0.86rem; }
.bb-table th { text-align: left; font-weight: 600; color: var(--bb-muted); border-bottom: 1px solid var(--bb-border); padding: 7px 9px; font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap; }
.bb-table td { padding: 9px 9px; border-bottom: 1px solid #F2F4F7; color: var(--bb-text-2); vertical-align: top; }
.bb-table tbody tr:last-child td { border-bottom: none; }
.bb-table tr:hover td { background: #FAFBFC; }
.bb-num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.bb-row-personal td { color: var(--bb-faint); }
.bb-row-personal td:nth-child(2) { text-decoration: line-through; }
.bb-row-total td { border-top: 2px solid var(--bb-border); font-weight: 700; color: var(--bb-text); }

.bb-totals { display: flex; gap: 28px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #F2F4F7; }
.bb-total { display: flex; flex-direction: column; }
.bb-total span { font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--bb-faint); font-weight: 600; }
.bb-total b { font-size: 1.15rem; color: var(--bb-text); margin-top: 1px; }
.bb-total.muted b { color: var(--bb-faint); font-size: 0.95rem; }

/* ---------- Balance banner ---------- */
.bb-balance { display: flex; align-items: center; gap: 8px; margin-top: 12px; padding: 9px 12px; border-radius: 9px; font-weight: 600; font-size: 0.85rem; }
.bb-balance.ok { background: var(--bb-success-weak); color: var(--bb-success); }
.bb-balance.bad { background: var(--bb-danger-weak); color: var(--bb-danger); }

/* ---------- Pending plan ---------- */
.bb-pending-banner { background: var(--bb-warning-weak); color: var(--bb-warning); border: 1px solid #FEDF89; border-radius: 9px; padding: 7px 11px; font-size: 0.8rem; font-weight: 600; margin-bottom: 8px; }
.bb-plan-item { font-size: 0.84rem; color: var(--bb-text-2); padding: 2px 0; }

/* ---------- Action checklist ---------- */
.bb-task-title { font-size: 0.86rem; color: var(--bb-text); }
.bb-task-done { text-decoration: line-through; color: var(--bb-faint); }
.bb-src-agent { background: var(--bb-accent-weak); color: var(--bb-accent-hover); }
.bb-src-user { background: #F2F4F7; color: var(--bb-text-2); }
.bb-chip-pending { background: var(--bb-warning-weak); color: var(--bb-warning); margin-left: 2px; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)