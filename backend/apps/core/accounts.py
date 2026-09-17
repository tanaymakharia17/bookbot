"""Chart-of-accounts mappings (pure constants)."""
from __future__ import annotations

# category -> (account_code, account_name)
CATEGORY_ACCOUNTS: dict[str, tuple[str, str]] = {
    "Fixed Assets":      ("1500", "Fixed Assets"),
    "IT Equipment":      ("6050", "IT Expenses"),
    "Office Supplies":   ("6120", "Office Supplies"),
    "Software":          ("6010", "Software Subscriptions"),
    "Meals":             ("6150", "Meals & Entertainment"),
    "Travel":            ("6200", "Travel"),
    "Professional Fees": ("6300", "Professional Fees"),
    "Taxes":             ("6400", "Taxes & Licenses"),
    "Uncategorized":     ("6999", "Uncategorized"),
}

# payment method -> (account_code, account_name)
PAYMENT_ACCOUNTS: dict[str, tuple[str, str]] = {
    "Company Credit Card": ("2010", "Company Credit Card"),
    "Company Debit Card":  ("2010", "Company Debit Card"),
    "Wire Transfer":       ("1010", "Cash — Bank"),
    "Cash":                ("1010", "Cash"),
}

DEFAULT_PAYMENT_ACCOUNT = ("2010", "Accounts Payable")