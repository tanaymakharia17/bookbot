"""Shared domain constants (pure, no Django)."""
from __future__ import annotations

PERSONAL_KEYWORDS = ("vacuum", "personal", "groceries", "clothing", "vacation")

TASK_CATALOG = [
    "Create a bill for the cash transaction",
    "Request Form W-9 from vendor",
    "Request Form W-8BEN-E from foreign vendor",
    "Exclude personal items from reimbursement",
    "Record capitalized asset in fixed-asset register",
    "Email client for missing receipt or context",
    "Attach source documents to the workpaper",
    "Post the journal entry to the ledger",
]

ACTION_FILE_HINTS = {
    "w-8ben": "Request Form W-8BEN-E from foreign vendor",
    "w8ben": "Request Form W-8BEN-E from foreign vendor",
    "w-9": "Request Form W-9 from vendor",
    "w9": "Request Form W-9 from vendor",
}

POST_LEDGER_TASK = "Post the journal entry to the ledger"

VENDOR_HINTS = {
    "apple": ("Apple Store", "IT Equipment"),
    "dell": ("Dell", "IT Equipment"),
    "target": ("Target", "Office Supplies"),
    "staples": ("Staples", "Office Supplies"),
    "google": ("Google LLC", "Software"),
    "adobe": ("Adobe", "Software"),
    "atlassian": ("Atlassian", "Software"),
    "home depot": ("Home Depot", "Uncategorized"),
    "sysco": ("Sysco Foods", "Meals"),
}

W8BEN_TASK = "Request Form W-8BEN-E from foreign vendor"
CASH_BILL_TASK = "Create a bill for the cash transaction"
EXCLUDE_PERSONAL_TASK = "Exclude personal items from reimbursement"
CAPITALIZE_TASK = "Record capitalized asset in fixed-asset register"
ATTACH_DOCS_TASK = "Attach source documents to the workpaper"
MISSING_CONTEXT_TASK = "Email client for missing receipt or context"