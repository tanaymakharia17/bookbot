"""In-memory mock backend.

Mirrors the contract of the future Django REST API. Swap by pointing
``config.USE_MOCK`` at a RealBackend that implements the same methods.

Model
-----
Each submission has *committed state* plus an optional *pending plan*.
Chat, file staging and task edits only build the plan. Nothing in the
committed state changes until ``execute_plan`` runs.
"""

from __future__ import annotations

import copy
import re
import time
import uuid
from datetime import date
from typing import Any

from config import DEFAULT_CAPEX_THRESHOLD


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _today() -> str:
    return date.today().isoformat()


CATEGORY_ACCOUNTS: dict[str, tuple[str, str]] = {
    "Fixed Assets":      ("1500", "Fixed Assets"),
    "IT Equipment":      ("6050", "IT Expenses"),
    "Office Supplies":   ("6120", "Office Supplies"),
    "Software":          ("6010", "Software Subscriptions"),
    "Meals":             ("6150", "Meals & Entertainment"),
    "Travel":            ("6200", "Travel"),
    "Professional Fees": ("6300", "Professional Fees"),
    "Uncategorized":     ("6999", "Uncategorized"),
}

PAYMENT_ACCOUNTS: dict[str, tuple[str, str]] = {
    "Company Credit Card": ("2010", "Company Credit Card"),
    "Company Debit Card":  ("2010", "Company Debit Card"),
    "Wire Transfer":       ("1010", "Cash — Bank"),
    "Cash":                ("1010", "Cash"),
}

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


def _li(desc: str, qty: int, unit: float, category: str = "Uncategorized", personal: bool = False) -> dict:
    return {
        "description": desc,
        "qty": qty,
        "unit_price": round(unit, 2),
        "amount": round(qty * unit, 2),
        "category": category,
        "personal": personal,
    }


def _new_task(title: str, source: str, done: bool = False) -> dict:
    return {"id": f"task_{_uid()}", "title": title, "done": done, "source": source}


def _empty_plan() -> dict:
    return {"save_files": [], "line_item_ops": [], "task_ops": []}


def _empty_client(client_id: str, name: str) -> dict:
    return {"id": client_id, "name": name, "submission_count": 0, "last_activity": ""}


CLIENTS = [
    _empty_client("c1a2b3", "Apex Retail Inc."),
    _empty_client("c2b3c4", "Coastal Cafe LLC"),
    _empty_client("c3c4d5", "Greenway Landscaping"),
    _empty_client("c4d5e6", "Brightside Marketing Co."),
    _empty_client("c5e6f7", "Urban Dental Group"),
]


SEED_SUBMISSIONS: list[dict[str, Any]] = [
    {
        "id": "sub_9901",
        "client_id": "c1a2b3",
        "state": "COMMITTED",
        "vendor": "Apple Store",
        "payment_method": "Company Credit Card",
        "channel": "Portal Upload",
        "raw_input": "Bought new laptop for lead engineer and an external display for store setup. Total was $3,850.00 on the company Visa -4412.",
        "file_names": ["apple_invoice_9901.pdf"],
        "created_at": "2026-09-15",
        "line_items": [
            _li("MacBook Pro 16\" (M3 Max)", 1, 2899.00, "IT Equipment"),
            _li("Apple Studio Display 27\"", 1, 1599.00, "IT Equipment"),
            _li("AppleCare+ for MacBook Pro", 1, 399.00, "IT Equipment"),
        ],
        "journal_entry": {
            "id": "je_1001",
            "transaction_date": "2026-09-15",
            "lines": [
                {"account_code": "1500", "account_name": "Fixed Assets", "entry_type": "DEBIT", "amount": 2279.09, "description": "MacBook Pro (net of discount)"},
                {"account_code": "6050", "account_name": "IT Expenses", "entry_type": "DEBIT", "amount": 1570.91, "description": "Display + AppleCare"},
                {"account_code": "2010", "account_name": "Company Credit Card", "entry_type": "CREDIT", "amount": 3850.00, "description": "Total payment"},
            ],
        },
    },
    {
        "id": "sub_9902",
        "client_id": "c1a2b3",
        "state": "NEEDS_REVIEW",
        "vendor": "Target",
        "payment_method": "Company Credit Card",
        "channel": "Portal Upload",
        "raw_input": "Office supplies run plus a vacuum I bought for home. Total $542.30.",
        "file_names": ["target_receipt.pdf"],
        "created_at": "2026-09-12",
        "line_items": [
            _li("Printer Paper (10 reams)", 1, 89.00, "Office Supplies"),
            _li("Desk Organizer Set", 2, 35.00, "Office Supplies"),
            _li("Dyson Vacuum V15", 1, 350.00, "Uncategorized", personal=False),
        ],
        "journal_entry": None,
    },
    {
        "id": "sub_9903",
        "client_id": "c1a2b3",
        "state": "BLOCKED_COMPLIANCE",
        "vendor": "Apex Design Studio UK",
        "payment_method": "Wire Transfer",
        "channel": "Email Ingest",
        "raw_input": "Invoice from UK design agency for rebranding work, plus the international wire fee.",
        "file_names": ["uk_invoice_9903.pdf"],
        "created_at": "2026-09-08",
        "line_items": [
            _li("Brand Redesign Phase 1", 1, 3275.00, "Professional Fees"),
            _li("International Wire Fee", 1, 45.00, "Uncategorized"),
        ],
        "journal_entry": None,
        "blocker": "Missing Form W-8BEN-E for foreign vendor.",
    },
    {
        "id": "sub_9904",
        "client_id": "c2b3c4",
        "state": "COMMITTED",
        "vendor": "Sysco Foods",
        "payment_method": "Company Debit Card",
        "channel": "Portal Upload",
        "raw_input": "Monthly food supply order.",
        "file_names": ["sysco_invoice.pdf"],
        "created_at": "2026-09-14",
        "line_items": [
            _li("Coffee Beans (5 lb bags)", 10, 45.00, "Meals"),
            _li("Pastry Flour (50 lb)", 4, 38.00, "Meals"),
            _li("Dairy Mix", 20, 22.50, "Meals"),
            _li("Paper Cups (1000 ct)", 5, 89.00, "Office Supplies"),
        ],
        "journal_entry": {
            "id": "je_1002",
            "transaction_date": "2026-09-14",
            "lines": [
                {"account_code": "6150", "account_name": "Meals & Entertainment", "entry_type": "DEBIT", "amount": 1052.00, "description": "Coffee, flour, dairy"},
                {"account_code": "6120", "account_name": "Office Supplies", "entry_type": "DEBIT", "amount": 445.00, "description": "Paper cups"},
                {"account_code": "2010", "account_name": "Company Debit Card", "entry_type": "CREDIT", "amount": 1497.00, "description": "Total payment"},
            ],
        },
    },
    {
        "id": "sub_9905",
        "client_id": "c4d5e6",
        "state": "COMMITTED",
        "vendor": "Google LLC",
        "payment_method": "Company Credit Card",
        "channel": "Portal Upload",
        "raw_input": "Annual Google Workspace renewal for the team, 12 seats.",
        "file_names": ["google_invoice.pdf"],
        "created_at": "2026-09-16",
        "line_items": [
            _li("Workspace Business Plus (12 seats)", 12, 240.00, "Software"),
        ],
        "journal_entry": {
            "id": "je_1003",
            "transaction_date": "2026-09-16",
            "lines": [
                {"account_code": "1500", "account_name": "Fixed Assets", "entry_type": "DEBIT", "amount": 2880.00, "description": "Annual subscription above threshold"},
                {"account_code": "2010", "account_name": "Company Credit Card", "entry_type": "CREDIT", "amount": 2880.00, "description": "Total payment"},
            ],
        },
    },
    {
        "id": "sub_9906",
        "client_id": "c3c4d5",
        "state": "RAW",
        "vendor": "Home Depot",
        "payment_method": "Company Credit Card",
        "channel": "Portal Upload",
        "raw_input": "Lawn equipment purchase, paid in cash.",
        "file_names": ["homedepot_receipt.jpg"],
        "created_at": "2026-09-10",
        "line_items": [],
        "journal_entry": None,
        "processing_until": 0.0,
    },
]

AFFIRMATIVE = ("yes", "yep", "confirm", "apply", "go ahead", "do it", "sure",
               "okay", "ok", "proceed", "agreed", "correct", "sounds good")


class MockBackend:
    def __init__(self) -> None:
        self.clients = {c["id"]: dict(c) for c in CLIENTS}
        self.submissions: dict[str, dict[str, Any]] = {}
        self.chats: dict[str, list[dict[str, str]]] = {}

        for seed in SEED_SUBMISSIONS:
            sub = copy.deepcopy(seed)
            sub.setdefault("file_names", [])
            sub.setdefault("reference_files", [])
            sub.setdefault("line_items", [])
            sub.setdefault("tasks", [])
            sub.setdefault("pending_plan", _empty_plan())
            self.submissions[sub["id"]] = sub

            if sub["state"] == "RAW":
                continue
            sub["tasks"] = self._seed_agent_tasks(sub)
            if sub["state"] == "COMMITTED":
                self._mark_posted_task(sub)
            self.chats[sub["id"]] = self._initial_chat(sub)

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------

    def list_clients(self) -> list[dict[str, Any]]:
        out = []
        for client in self.clients.values():
            c = dict(client)
            subs = self._client_submissions(c["id"])
            c["submission_count"] = len(subs)
            dates = [s["created_at"] for s in subs]
            if dates:
                c["last_activity"] = max(dates)
            states = [s["state"] for s in subs]
            c["counts"] = {st: states.count(st) for st in set(states)}
            out.append(c)
        return sorted(out, key=lambda c: c["name"])

    def get_client(self, client_id: str) -> dict[str, Any] | None:
        client = self.clients.get(client_id)
        return dict(client) if client else None

    def create_client(self, name: str) -> dict[str, Any]:
        name = (name or "").strip()
        if not name:
            return {"error": "Company name is required."}
        if any(c["name"].lower() == name.lower() for c in self.clients.values()):
            return {"error": "A company with this name already exists."}
        client_id = _uid()
        client = {
            "id": client_id,
            "name": name,
            "submission_count": 0,
            "last_activity": "",
            "counts": {},
        }
        self.clients[client_id] = client
        return client

    # ------------------------------------------------------------------
    # Submissions
    # ------------------------------------------------------------------

    def list_submissions(self, client_id: str, state_filter: str | None = None) -> list[dict[str, Any]]:
        subs = self._client_submissions(client_id)
        if state_filter and state_filter != "all":
            subs = [s for s in subs if s["state"] == state_filter]
        return sorted(subs, key=lambda s: s["created_at"], reverse=True)

    def get_submission(self, submission_id: str) -> dict[str, Any] | None:
        sub = self.submissions.get(submission_id)
        if not sub:
            return None
        self._advance_processing(sub)
        out = dict(sub)
        out["projected"] = self._projected(sub)
        out["plan_labels"] = self._plan_labels(sub["pending_plan"])
        return out

    def available_files(self) -> list[str]:
        return []

    def upload_documents(self, submission_id: str, files) -> dict[str, Any]:
        return {"files": [getattr(f, "name", str(f)) for f in (files or [])]}

    def create_submission(self, client_id: str, file_names: list[str], raw_input: str) -> dict[str, Any]:
        if not file_names:
            raise ValueError("At least one file is required.")

        sub_id = f"sub_{_uid()}"
        sub = {
            "id": sub_id,
            "client_id": client_id,
            "state": "RAW",
            "vendor": "",
            "payment_method": "",
            "channel": "Portal Upload",
            "raw_input": (raw_input or "").strip(),
            "file_names": list(file_names),
            "reference_files": [],
            "created_at": _today(),
            "line_items": [],
            "tasks": [],
            "pending_plan": _empty_plan(),
            "journal_entry": None,
            "processing_until": time.time() + 2.0,
        }
        self.submissions[sub_id] = sub
        return self.get_submission(sub_id)

    def _advance_processing(self, sub: dict[str, Any]) -> None:
        if sub["state"] != "RAW":
            return
        if time.time() < sub.get("processing_until", 0):
            return

        text = " ".join([sub.get("raw_input", ""), *sub.get("file_names", [])])
        vendor, category, total, payment = self._recompute_fields(sub.get("vendor", ""), "", text)

        sub["vendor"] = vendor
        sub["payment_method"] = payment
        sub["line_items"] = self._mock_extract(vendor, category, total)
        sub["state"] = "EXTRACTED"
        sub["tasks"] = self._seed_agent_tasks(sub)
        self.chats[sub["id"]] = self._initial_chat(sub)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat_history(self, submission_id: str) -> list[dict[str, str]]:
        sub = self.get_submission(submission_id)
        if sub and sub["state"] == "RAW":
            return []
        return list(self.chats.get(submission_id, []))

    def chat(self, submission_id: str, message: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        self._advance_processing(sub)
        if sub["state"] == "RAW":
            return {"error": "Extraction is still in progress. Try again shortly."}
        if not message.strip():
            return {"error": "Message cannot be empty."}
        if sub["state"] == "COMMITTED":
            return {"error": "This submission has been posted. Start a new submission for further work."}

        session = self.chats.setdefault(submission_id, [])
        session.append({"role": "cpa", "content": message.strip()})
        reply = self._respond(sub, message)
        session.append({"role": "agent", "content": reply})

        if sub["state"] == "EXTRACTED":
            sub["state"] = "NEEDS_REVIEW"
        return {"reply": reply, "submission": self.get_submission(submission_id)}

    def _respond(self, sub: dict[str, Any], message: str) -> str:
        m = message.lower()
        plan = sub["pending_plan"]
        proj = self._projected(sub)
        items = proj["line_items"]

        if any(w in m for w in ["exclude", "personal", "private", "vacuum"]):
            if not items:
                return "There's nothing to exclude yet."
            matches = [li for li in items if not li["personal"]
                       and any(k in li["description"].lower() for k in PERSONAL_KEYWORDS)]
            if not matches:
                matches = [items[-1]]
            plan["line_item_ops"].append({
                "id": f"op_{_uid()}",
                "type": "exclude_personal",
                "targets": [li["description"] for li in matches],
                "label": "Exclude personal: " + ", ".join(li["description"] for li in matches),
            })
            return f"Added to the plan: exclude {len(matches)} personal item(s). It applies when you execute the plan."

        if any(w in m for w in ["capitalize", "fixed asset", "reclass", "depreciat"]):
            threshold = DEFAULT_CAPEX_THRESHOLD
            matches = [li for li in items if not li["personal"] and li["amount"] >= threshold]
            if not matches:
                return f"No line items reach the ${threshold:,.2f} CapEx threshold."
            plan["line_item_ops"].append({
                "id": f"op_{_uid()}",
                "type": "capitalize",
                "threshold": threshold,
                "label": f"Capitalize items ≥ ${threshold:,.2f}",
            })
            return f"Added to the plan: capitalize {len(matches)} item(s)."

        if any(w in m for w in ["discount", "proportional", "reduce"]):
            plan["line_item_ops"].append({
                "id": f"op_{_uid()}", "type": "discount", "percent": 10,
                "label": "Apply a 10% discount across all lines",
            })
            return "Added to the plan: a 10% discount across all lines."

        if any(w in m for w in ["split", "percent", "%"]):
            if not items:
                return "There's nothing to split yet."
            target = max(items, key=lambda li: li["amount"])
            plan["line_item_ops"].append({
                "id": f"op_{_uid()}", "type": "split",
                "target": target["description"], "ratios": (70, 30),
                "label": f"Split {target['description']} 70 / 30",
            })
            return f"Added to the plan: split {target['description']} 70 / 30."

        if any(w in m for w in ["approve", "looks good", "finalize", "post"]):
            return ("Review the pending plan, click **Execute plan**, then **Approve & Post to Ledger** "
                    "to save it to the ledger.")

        return ("I can add changes to the plan: exclude personal items, capitalize above threshold, "
                "apply a discount, or split a line. Attach documents with the paperclip to stage them. "
                "Nothing changes until you execute the plan.")

    # ------------------------------------------------------------------
    # Plan staging
    # ------------------------------------------------------------------

    def stage_files(self, submission_id: str, files: list[dict[str, Any]]) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        self._advance_processing(sub)
        if sub["state"] == "RAW":
            return {"error": "Extraction is still in progress."}
        if sub["state"] == "COMMITTED":
            return {"error": "This submission is posted. Create a new submission to add documents."}

        plan = sub["pending_plan"]
        known = set(sub["file_names"]) | set(sub["reference_files"]) | set(plan["save_files"])
        staged_save, staged_ref = [], []

        for f in files:
            name = (f.get("name") or "").strip()
            if not name or name in known:
                continue
            if f.get("save"):
                plan["save_files"].append(name)
                staged_save.append(name)
            else:
                sub["reference_files"].append(name)
                staged_ref.append(name)
            known.add(name)

        proposed = self._propose_action_completions(sub, staged_save)

        lines = []
        if staged_save:
            lines.append(f"**Save {len(staged_save)} file(s)** → will recompute: " + ", ".join(staged_save))
        if staged_ref:
            lines.append(f"**{len(staged_ref)} reference file(s)** (context only, no recompute): " + ", ".join(staged_ref))
        for action in proposed:
            lines.append(f"**Complete action:** {action}")

        if lines:
            self.chats.setdefault(submission_id, []).append({
                "role": "agent",
                "content": "Added to the pending plan:\n\n- " + "\n- ".join(lines),
            })
        return {"submission": self.get_submission(submission_id), "proposed": proposed}

    def _propose_action_completions(self, sub: dict[str, Any], staged_save: list[str]) -> list[str]:
        plan = sub["pending_plan"]
        proj = self._projected(sub)
        open_actions = {t["title"]: t for t in proj["tasks"] if not t["done"]}
        proposed = []
        for name in staged_save:
            low = name.lower()
            for hint, action in ACTION_FILE_HINTS.items():
                if hint in low and action in open_actions:
                    task = open_actions[action]
                    already = any(o["type"] == "set_done" and o["task_id"] == task["id"]
                                  for o in plan["task_ops"])
                    if not already:
                        plan["task_ops"].append({
                            "id": f"op_{_uid()}", "type": "set_done",
                            "task_id": task["id"], "done": True,
                            "label": f"Complete action: {action}",
                        })
                        proposed.append(action)
        return proposed

    def stage_task_add(self, submission_id: str, title: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        if sub["state"] == "COMMITTED":
            return {"error": "This submission is posted."}
        title = title.strip()
        if not title:
            return {"error": "Task title cannot be empty."}
        proj = self._projected(sub)
        if any(t["title"].lower() == title.lower() for t in proj["tasks"]):
            return {"error": "That task already exists."}
        task = _new_task(title, "user")
        sub["pending_plan"]["task_ops"].append({
            "id": f"op_{_uid()}", "type": "add", "task": task,
            "label": f"Add task: {title}",
        })
        return {"submission": self.get_submission(submission_id)}

    def stage_task_toggle(self, submission_id: str, task_id: str, done: bool) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        if sub["state"] == "COMMITTED":
            return {"error": "This submission is posted."}
        plan = sub["pending_plan"]

        for op in plan["task_ops"]:
            if op["type"] == "add" and op["task"]["id"] == task_id:
                op["task"]["done"] = done
                return {"submission": self.get_submission(submission_id)}

        committed = next((t for t in sub["tasks"] if t["id"] == task_id), None)
        plan["task_ops"] = [o for o in plan["task_ops"]
                            if not (o["type"] == "set_done" and o["task_id"] == task_id)]
        if committed and committed["done"] == done:
            return {"submission": self.get_submission(submission_id)}
        title = committed["title"] if committed else task_id
        plan["task_ops"].append({
            "id": f"op_{_uid()}", "type": "set_done", "task_id": task_id, "done": done,
            "label": ("Complete action: " if done else "Reopen action: ") + title,
        })
        return {"submission": self.get_submission(submission_id)}

    def stage_task_remove(self, submission_id: str, task_id: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        if sub["state"] == "COMMITTED":
            return {"error": "This submission is posted."}
        plan = sub["pending_plan"]

        staged_add = next((o for o in plan["task_ops"]
                           if o["type"] == "add" and o["task"]["id"] == task_id), None)
        if staged_add:
            plan["task_ops"] = [o for o in plan["task_ops"] if o is not staged_add]
            return {"submission": self.get_submission(submission_id)}

        committed = next((t for t in sub["tasks"] if t["id"] == task_id), None)
        if not committed:
            return {"error": "Task not found."}
        plan["task_ops"] = [o for o in plan["task_ops"] if o.get("task_id") != task_id]
        plan["task_ops"].append({
            "id": f"op_{_uid()}", "type": "remove", "task_id": task_id,
            "label": f"Remove task: {committed['title']}",
        })
        return {"submission": self.get_submission(submission_id)}

    def discard_plan(self, submission_id: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        sub["pending_plan"] = _empty_plan()
        self.chats.setdefault(submission_id, []).append(
            {"role": "agent", "content": "Discarded the pending plan. Nothing was changed."}
        )
        return {"submission": self.get_submission(submission_id)}

    def execute_plan(self, submission_id: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        self._advance_processing(sub)
        if sub["state"] == "RAW":
            return {"error": "Extraction is still in progress."}
        if sub["state"] == "COMMITTED":
            return {"error": "This submission is posted."}

        plan = sub["pending_plan"]
        if self._plan_count(plan) == 0:
            return {"error": "There is no pending plan to execute."}

        saved = plan["save_files"]
        if saved:
            sub["file_names"] = self._dedup(sub["file_names"] + saved)
            text = " ".join([sub.get("raw_input", ""), *sub["file_names"]])
            category = (sub.get("line_items") or [{}])[0].get("category") if sub.get("line_items") else ""
            vendor, category, total, payment = self._recompute_fields(sub.get("vendor", ""), category, text)
            sub["vendor"] = vendor
            sub["payment_method"] = payment
            sub["line_items"] = self._mock_extract(vendor, category, total)

        for op in plan["line_item_ops"]:
            sub["line_items"] = self._apply_line_op(sub["line_items"], op)

        if saved:
            sub["tasks"] = [t for t in sub["tasks"] if t["source"] == "user"]
            sub["tasks"] += self._seed_agent_tasks(sub)

        for op in plan["task_ops"]:
            sub["tasks"] = self._apply_task_op(sub["tasks"], op)

        sub["pending_plan"] = _empty_plan()
        if sub["state"] in ("EXTRACTED", "PENDING_CLIENT"):
            sub["state"] = "NEEDS_REVIEW"

        self.chats.setdefault(submission_id, []).append({
            "role": "agent",
            "content": "Executed the plan. The Source of Truth, final data and action list are updated.",
        })
        return {"submission": self.get_submission(submission_id)}

    def _plan_labels(self, plan: dict[str, Any]) -> list[dict[str, str]]:
        labels = []
        for name in plan["save_files"]:
            labels.append({"id": f"file::{name}", "kind": "file", "label": f"Save file: {name}"})
        for op in plan["line_item_ops"]:
            labels.append({"id": op["id"], "kind": "line", "label": op["label"]})
        for op in plan["task_ops"]:
            labels.append({"id": op["id"], "kind": "task", "label": op["label"]})
        return labels

    def remove_plan_op(self, submission_id: str, op_id: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        plan = sub["pending_plan"]
        if op_id.startswith("file::"):
            name = op_id.split("::", 1)[1]
            plan["save_files"] = [n for n in plan["save_files"] if n != name]
        else:
            plan["line_item_ops"] = [o for o in plan["line_item_ops"] if o["id"] != op_id]
            plan["task_ops"] = [o for o in plan["task_ops"] if o["id"] != op_id]
        return {"submission": self.get_submission(submission_id)}

    # ------------------------------------------------------------------
    # Projection (committed + pending plan)
    # ------------------------------------------------------------------

    def _projected(self, sub: dict[str, Any]) -> dict[str, Any]:
        plan = sub.get("pending_plan") or _empty_plan()
        saved = plan["save_files"]

        if saved:
            text = " ".join([sub.get("raw_input", ""), *sub.get("file_names", []), *saved])
            category = (sub.get("line_items") or [{}])[0].get("category") if sub.get("line_items") else ""
            vendor, category, total, payment = self._recompute_fields(sub.get("vendor", ""), category, text)
            lines = self._mock_extract(vendor, category, total)
        else:
            vendor = sub.get("vendor")
            payment = sub.get("payment_method")
            lines = [copy.deepcopy(li) for li in sub.get("line_items", [])]

        for op in plan["line_item_ops"]:
            lines = self._apply_line_op(lines, op)

        if saved:
            tasks = [copy.deepcopy(t) for t in sub.get("tasks", []) if t["source"] == "user"]
            temp = {
                "vendor": vendor, "payment_method": payment, "line_items": lines,
                "state": sub.get("state"), "raw_input": sub.get("raw_input"),
                "client_id": sub["client_id"],
            }
            tasks += self._seed_agent_tasks(temp)
        else:
            tasks = [copy.deepcopy(t) for t in sub.get("tasks", [])]

        for op in plan["task_ops"]:
            tasks = self._apply_task_op(tasks, op)

        return {
            "vendor": vendor,
            "payment_method": payment,
            "line_items": lines,
            "tasks": tasks,
            "file_names": self._dedup(sub.get("file_names", []) + saved),
            "has_pending": self._plan_count(plan) > 0,
        }

    def _apply_line_op(self, lines: list[dict], op: dict[str, Any]) -> list[dict]:
        kind = op["type"]
        if kind == "exclude_personal":
            targets = set(op.get("targets", []))
            for li in lines:
                if li["description"] in targets:
                    li["personal"] = True
        elif kind == "capitalize":
            threshold = op.get("threshold", 2500.0)
            for li in lines:
                if not li.get("personal") and li["amount"] >= threshold:
                    li["category"] = "Fixed Assets"
        elif kind == "discount":
            factor = 1 - op.get("percent", 10) / 100
            for li in lines:
                li["amount"] = round(li["amount"] * factor, 2)
                li["unit_price"] = round(li["unit_price"] * factor, 2)
        elif kind == "split":
            target = op["target"]
            a, b = op.get("ratios", (70, 30))
            for li in lines:
                if li["description"] == target:
                    part_a = round(li["amount"] * a / 100, 2)
                    part_b = round(li["amount"] - part_a, 2)
                    li["amount"] = part_a
                    li["unit_price"] = part_a
                    li["category"] = "Software"
                    li["description"] = f"{target} ({a}%)"
                    lines.append(_li(f"{target} ({b}%)", 1, part_b, "Software"))
                    break
        return lines

    def _apply_task_op(self, tasks: list[dict], op: dict[str, Any]) -> list[dict]:
        kind = op["type"]
        if kind == "add":
            tasks = tasks + [copy.deepcopy(op["task"])]
        elif kind == "set_done":
            for task in tasks:
                if task["id"] == op["task_id"]:
                    task["done"] = op["done"]
        elif kind == "remove":
            tasks = [t for t in tasks if t["id"] != op["task_id"]]
        return tasks

    # ------------------------------------------------------------------
    # Journal + ledger
    # ------------------------------------------------------------------

    def preview_journal(self, submission_id: str) -> dict[str, Any] | None:
        sub = self.get_submission(submission_id)
        if not sub:
            return None
        proj = sub["projected"]
        business = [li for li in proj["line_items"] if not li["personal"]]
        if not business:
            return None
        threshold = DEFAULT_CAPEX_THRESHOLD
        lines, debit, credit = self._build_journal(proj, business, threshold)
        return {
            "lines": lines,
            "total_debits": debit,
            "total_credits": credit,
            "balanced": abs(debit - credit) < 0.001,
        }

    def list_ledger_entries(self, client_id: str | None = None) -> list[dict[str, Any]]:
        out = []
        for sub in self.submissions.values():
            entry = sub.get("journal_entry")
            if not entry:
                continue
            if client_id and sub["client_id"] != client_id:
                continue
            client = self.clients.get(sub["client_id"], {})
            debit = sum(l["amount"] for l in entry["lines"] if l["entry_type"] == "DEBIT")
            credit = sum(l["amount"] for l in entry["lines"] if l["entry_type"] == "CREDIT")
            out.append({
                "id": entry["id"],
                "submission_id": sub["id"],
                "date": entry.get("transaction_date", sub.get("created_at")),
                "client_id": sub["client_id"],
                "client_name": client.get("name", ""),
                "vendor": sub["vendor"],
                "total": round(debit, 2),
                "line_count": len(entry["lines"]),
                "balanced": abs(debit - credit) < 0.001,
            })
        return sorted(out, key=lambda e: (e["date"], e["id"]), reverse=True)

    def get_ledger_entry(self, entry_id: str) -> dict[str, Any] | None:
        for sub in self.submissions.values():
            entry = sub.get("journal_entry")
            if entry and entry["id"] == entry_id:
                client = self.clients.get(sub["client_id"], {})
                lines = entry["lines"]
                debit = sum(l["amount"] for l in lines if l["entry_type"] == "DEBIT")
                credit = sum(l["amount"] for l in lines if l["entry_type"] == "CREDIT")
                return {
                    "id": entry["id"],
                    "submission_id": sub["id"],
                    "transaction_date": entry.get("transaction_date", sub.get("created_at")),
                    "client_id": sub["client_id"],
                    "client_name": client.get("name", ""),
                    "vendor": sub["vendor"],
                    "payment_method": sub.get("payment_method", ""),
                    "lines": lines,
                    "total_debits": round(debit, 2),
                    "total_credits": round(credit, 2),
                    "balanced": abs(debit - credit) < 0.001,
                }
        return None

    def approve(self, submission_id: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        self._advance_processing(sub)
        if sub["state"] == "RAW":
            return {"error": "Extraction is still in progress."}
        if sub["state"] == "COMMITTED":
            return {"error": "Submission has already been posted."}
        if sub["state"] == "BLOCKED_COMPLIANCE":
            return {"error": sub.get("blocker", "Submission is blocked on compliance.")}
        if self._plan_count(sub["pending_plan"]) > 0:
            return {"error": "Execute or discard the pending plan before approving."}

        business = [li for li in sub["line_items"] if not li["personal"]]
        if not business:
            return {"error": "No business line items remain after exclusions."}

        threshold = DEFAULT_CAPEX_THRESHOLD
        lines, debit, credit = self._build_journal(sub, business, threshold)
        if abs(debit - credit) > 0.001:
            return {"error": f"Double-entry violation: debits {debit:.2f} ≠ credits {credit:.2f}."}

        entry = {"id": f"je_{_uid()}", "submission_id": submission_id,
                 "transaction_date": _today(), "lines": lines}
        sub["journal_entry"] = entry
        sub["state"] = "COMMITTED"
        sub["approved_at"] = _today()
        sub["pending_plan"] = _empty_plan()
        self._mark_posted_task(sub)

        self.chats.setdefault(submission_id, []).append({
            "role": "agent",
            "content": f"Posted to the ledger — {len(lines)} lines, debits = credits = ${debit:,.2f}.",
        })
        return {"submission": self.get_submission(submission_id), "journal_entry": entry}

    def resolve_compliance(self, submission_id: str) -> dict[str, Any]:
        sub = self.submissions.get(submission_id)
        if not sub:
            return {"error": "Submission not found."}
        if sub["state"] != "BLOCKED_COMPLIANCE":
            return {"error": "Submission is not blocked."}
        sub["blocker_resolved"] = True
        sub["state"] = "NEEDS_REVIEW"
        self.chats.setdefault(submission_id, []).append({
            "role": "agent",
            "content": "Compliance document received. The submission is unblocked and back in review.",
        })
        return {"submission": self.get_submission(submission_id)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client_submissions(self, client_id: str) -> list[dict[str, Any]]:
        return [s for s in self.submissions.values() if s["client_id"] == client_id]

    @staticmethod
    def _dedup(names: list[str]) -> list[str]:
        seen, out = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out

    @staticmethod
    def _plan_count(plan: dict[str, Any]) -> int:
        return len(plan.get("save_files", [])) + len(plan.get("line_item_ops", [])) + len(plan.get("task_ops", []))

    def _mark_posted_task(self, sub: dict[str, Any]) -> None:
        for task in sub.get("tasks", []):
            if task["title"] == POST_LEDGER_TASK:
                task["done"] = True

    def _seed_agent_tasks(self, sub: dict[str, Any]) -> list[dict]:
        titles: list[str] = []
        vendor = (sub.get("vendor") or "").lower()
        payment = sub.get("payment_method") or ""
        raw = (sub.get("raw_input") or "").lower()

        if sub.get("state") == "BLOCKED_COMPLIANCE" or "uk" in vendor or "foreign" in vendor:
            titles.append("Request Form W-8BEN-E from foreign vendor")
        if payment in ("", "Cash") or "cash" in raw:
            titles.append("Create a bill for the cash transaction")

        items = sub.get("line_items", [])
        if any(li.get("personal") or any(k in li["description"].lower() for k in PERSONAL_KEYWORDS)
               for li in items):
            titles.append("Exclude personal items from reimbursement")

        client_id = sub.get("client_id")
        threshold = DEFAULT_CAPEX_THRESHOLD
        if any((not li.get("personal")) and li["amount"] >= threshold for li in items):
            titles.append("Record capitalized asset in fixed-asset register")

        titles.append("Attach source documents to the workpaper")
        if not (sub.get("raw_input") or "").strip():
            titles.append("Email client for missing receipt or context")
        titles.append(POST_LEDGER_TASK)

        seen, out = set(), []
        for title in titles:
            if title not in seen:
                seen.add(title)
                out.append({"id": f"agent::{_slug(title)}", "title": title, "done": False, "source": "agent"})
        return out

    def _recompute_fields(self, fallback_vendor: str, fallback_category: str, text: str) -> tuple[str, str, float, str]:
        vendor, category = self._detect_vendor(text)
        if vendor == "Unknown Vendor" and fallback_vendor:
            vendor = fallback_vendor
            category = fallback_category or "Uncategorized"
        total = self._extract_amount(text) or 1250.00
        payment = "Cash" if "cash" in text.lower() else "Company Credit Card"
        return vendor, category, total, payment

    def _extract_amount(self, text: str) -> float | None:
        matches = re.findall(r"\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text)
        values = []
        for match in matches:
            try:
                values.append(float(match.replace(",", "")))
            except ValueError:
                continue
        values = [v for v in values if v >= 1]
        return max(values) if values else None

    def _detect_vendor(self, text: str) -> tuple[str, str]:
        lowered = text.lower()
        for hint, (vendor, category) in VENDOR_HINTS.items():
            if hint in lowered:
                return vendor, category
        return "Unknown Vendor", "Uncategorized"

    def _mock_extract(self, vendor: str, category: str, total: float) -> list[dict]:
        first = round(total * 0.88, 2)
        second = round(total - first, 2)
        return [
            _li(f"{vendor} — Primary item", 1, first, category),
            _li(f"{vendor} — Accessory / add-on", 1, second, category),
        ]

    def _initial_chat(self, sub: dict[str, Any]) -> list[dict[str, str]]:
        business = sum(li["amount"] for li in sub.get("line_items", []) if not li["personal"])
        personal = [li for li in sub.get("line_items", []) if li["personal"]]
        personal_note = (
            f"\n\n⚠️ I flagged {len(personal)} item(s) that look personal and excluded them "
            f"from the reimbursement total." if personal else ""
        )
        return [
            {"role": "agent", "content": f"Files received: {', '.join(sub['file_names']) or '—'}."},
            {
                "role": "agent",
                "content": (
                    f"I've extracted **{len(sub.get('line_items', []))} line items** from the "
                    f"{sub.get('vendor') or 'document'} file(s), totaling **${business:,.2f}**."
                    f"{personal_note}\n\n"
                    f"Tell me what to change and I'll add it to the pending plan — or attach more "
                    f"documents with the paperclip. Nothing is applied until you execute the plan."
                ),
            },
        ]

    def _build_journal(self, sub: dict[str, Any], business: list[dict], threshold: float) -> tuple[list[dict], float, float]:
        lines: list[dict] = []
        debit_total = 0.0
        for li in business:
            if li["amount"] >= threshold:
                code, name = CATEGORY_ACCOUNTS["Fixed Assets"]
            else:
                code, name = CATEGORY_ACCOUNTS.get(li["category"], CATEGORY_ACCOUNTS["Uncategorized"])
            lines.append({
                "account_code": code,
                "account_name": name,
                "entry_type": "DEBIT",
                "amount": round(li["amount"], 2),
                "description": li["description"],
            })
            debit_total += li["amount"]

        credit_total = round(sum(li["amount"] for li in business), 2)
        pay_code, pay_name = PAYMENT_ACCOUNTS.get(
            sub.get("payment_method", ""), ("2010", "Accounts Payable")
        )
        lines.append({
            "account_code": pay_code,
            "account_name": pay_name,
            "entry_type": "CREDIT",
            "amount": credit_total,
            "description": f"Payment — {sub.get('vendor') or 'vendor'}",
        })
        return lines, round(debit_total, 2), credit_total