STATUS = {
    "RAW":                ("Processing",      "#475467", "#F2F4F7", "#98A2B3"),
    "EXTRACTED":          ("Extracted",       "#175CD3", "#EFF8FF", "#2E90FA"),
    "NEEDS_REVIEW":       ("Needs Review",    "#B54708", "#FFFAEB", "#F79009"),
    "PENDING_CLIENT":     ("Pending Client",  "#5925DC", "#F4F3FF", "#7A5AF8"),
    "BLOCKED_COMPLIANCE": ("Blocked",         "#B42318", "#FEF3F2", "#F04438"),
    "COMMITTED":          ("Posted",          "#067647", "#ECFDF3", "#12B76A"),
}

_STATE_ORDER = [
    "NEEDS_REVIEW",
    "BLOCKED_COMPLIANCE",
    "EXTRACTED",
    "RAW",
    "PENDING_CLIENT",
    "COMMITTED",
]


def badge(state: str) -> str:
    label, color, bg, dot = STATUS.get(state, STATUS["RAW"])
    return (
        f"<span class='bb-badge' style='color:{color};background:{bg}'>"
        f"<span class='bb-dot' style='background:{dot}'></span>{label}</span>"
    )


def status_label(state: str) -> str:
    return STATUS.get(state, STATUS["RAW"])[0]


def state_order() -> list[str]:
    return list(_STATE_ORDER)