ARCHITECTURE_SPEC_FOR_MVC.md
Target Audience: Next-Stage AI Software Engineer / Code Agent

Purpose: Full architectural blueprint, state machine specification, domain logic, Python code snippets, and execution roadmap to build the Minimum Viable Product (MVC) for an Agentic AI Bookkeeping platform tailored for multi-tenant CPA firms.

1. Executive Summary & Core Philosophy
1.1 Objective
Build an enterprise-grade, multi-tenant AI bookkeeping automation workspace for US-based CPA firms managing dozens to hundreds of business clients. The platform reduces manual bookkeeping friction by 95% while guaranteeing absolute double-entry mathematical rigor (∑Debits=∑Credits) and complete auditability.

1.2 Core Architectural Axioms
The Markdown Manifest is the Immutable Source of Truth (SoT): Unstructured client submissions (PDFs, JPEGs, emails, notes) are extracted once via Multimodal Vision-Language Models (VLMs) into a standardized, human-readable Markdown file (submission_sot.md). All downstream agentic operations read only this text manifest, dramatically lowering token costs and latency.

Deterministic Engine vs. Fuzzy AI Classifier: LLMs are never allowed to execute autonomous database writes or balance ledger math directly. The AI acts purely as a semantic classifier, contextual investigator, and proposal drafter. A deterministic Python middleware pipeline enforces strict accounting rules and double-entry invariants.

Agentic Drafting Workspace (Human-in-the-Loop): Instead of an opaque "black-box auto-poster," each submission instantiates an interactive "Session Agent." The Agent uses read-only tools to search bank feeds, check tax compliance, and generate a structured Proposed Action Plan. The CPA reviews, refines via natural language, and clicks "Approve" to commit.

Vector RAG over Model Fine-Tuning: Fine-tuning on chat logs is an anti-pattern. Learning is achieved using a multi-tenant pgvector store with two layers: Client-Specific Memory and Firm-Wide Shared Memory.

2. End-to-End System Architecture
[ Unstructured Ingestion ]
  PDFs, JPEGs, Form Notes, Emails
             │
             ▼
[ VLM Extraction Worker ] ──► Generates Immutable `submission_sot.md` (Stored in S3/Postgres)
             │
             ▼
[ Interactive Agentic Workspace ]
  ├── Reads `submission_sot.md`
  ├── Executes Read-Only Tools (Bank Feeds, W-9/W-8BEN Registry, Historical RAG)
  └── Generates `ProposedActionPlan` (Checklist for CPA)
             │
             ▼
[ Human-in-the-Loop CPA Review ]
  CPA chats with Agent to modify splits, apply overrides, or confirm plan
             │
             ▼ (CPA Clicks "Approve")
[ Deterministic Python Pipeline (SOLID) ]
  ├── CapEx Threshold Enforcement ($2,500 Safe Harbor)
  ├── Personal Expense Exclusion
  └── Double-Entry Invariant Check (Sum Debits == Sum Credits)
             │
             ▼
[ PostgreSQL Immutable Ledger ] ──► Syncs to QuickBooks / Xero API
3. The Lifecycle State Machine
Every submission operates as an isolated state machine sandboxed from other client data. If a CPA rolls back a transaction, only that single submission's state is mutated.

+---------------+      +-------------------+      +-----------------------+
|  1. RAW       | ──►  |  2. EXTRACTED     | ──►  |  3. NEEDS_REVIEW      |
|  (Files in S3)|      |  (SOT .md Created)|      |  (Agent Plan Drafted) |
+---------------+      +-------------------+      +-----------------------+
                                                              │
                     ┌────────────────────────────────────────┼────────────────────────────────────────┐
                     ▼                                        ▼                                        ▼
        +-------------------------+              +-------------------------+              +-------------------------+
        |  4a. PENDING_CLIENT     |              |  4b. BLOCKED_COMPLIANCE |              |  4c. COMMITTED / POSTED |
        |  (Awaiting Client Note) |              |  (Missing W-9/W-8BEN)   |              |  (Saved to Ledger DB)   |
        +-------------------------+              +-------------------------+              +-------------------------+
State Name	Trigger	Next Allowed States
RAW	File uploaded via web portal or email ingest.	EXTRACTED
EXTRACTED	VLM finishes parsing; submission_sot.md saved.	NEEDS_REVIEW
NEEDS_REVIEW	Session Agent completes investigation tools and drafts plan.	COMMITTED, PENDING_CLIENT, BLOCKED_COMPLIANCE
PENDING_CLIENT	Agent flags ambiguity; magic link sent to client.	NEEDS_REVIEW
BLOCKED_COMPLIANCE	Vendor missing mandatory tax forms (e.g., W-8BEN-E).	NEEDS_REVIEW, COMMITTED
COMMITTED	CPA approves action plan; Python pipeline validates math.	Terminal State (Reversible only via reversing entry)
4. Markdown Source of Truth (submission_sot.md) Specification
The .md manifest must strictly conform to this structure upon extraction:

Markdown
# Submission Source of Truth: sub_9901
- Client ID: org_apex_retail
- Timestamp: 2026-09-16T10:00:00Z
- Channel: Portal Upload
- Processing VLM: Claude-3.5-Sonnet / GPT-4o Vision

## User/Client Context
- Form Note: Bought new laptop for lead engineer and an external display for store setup.
- Payment Method: Company Credit Card (Visa - 4412)
- Self-Reported Amount: $3,850.00

## Visual & Document Extraction (apple_invoice_9901.pdf)
Vendor: Apple Store (Retail Store #R102, Palo Alto, CA)
Date: September 15, 2026
Document ID: A-990123

| Line # | Description | Qty | Unit Price | Total Amount |
| :--- | :--- | :--- | :--- | :--- |
| 1 | MacBook Pro 16" (M3 Max, 36GB RAM) | 1 | $2,899.00 | $2,899.00 |
| 2 | Apple Studio Display 27" | 1 | $1,599.00 | $1,599.00 |
| 3 | AppleCare+ for MacBook Pro | 1 | $399.00 | $399.00 |

- Subtotal: $4,897.00
- Discount (Business Agreement): -$1,346.00
- Adjusted Subtotal: $3,551.00
- Estimated Tax (8.425%): $299.00
- Grand Total: $3,850.00
5. Python Rule Pipeline (SOLID Architecture)
Below is the concrete production pattern using Python dataclasses and Abstract Base Classes (abc) to enforce accounting logic deterministically.

Python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

# ------------------------------------------------------------------
# Data Models (Input Payload from LLM Classifier)
# ------------------------------------------------------------------

@dataclass
class ExtractedLineItem:
    description: str
    amount: float
    ai_flagged_personal: bool = False
    suggested_category: str = "Uncategorized"

@dataclass
class LedgerState:
    submission_id: str
    client_id: str
    lines: List[ExtractedLineItem]
    company_capex_threshold: float = 2500.00
    total_reimbursement_payable: float = 0.0
    cpa_warnings: List[str] = field(default_factory=list)
    posted_entries: List[Dict[str, Any]] = field(default_factory=list)

# ------------------------------------------------------------------
# SOLID Interface Definition
# ------------------------------------------------------------------

class LedgerRule(ABC):
    @abstractmethod
    def execute(self, state: LedgerState) -> LedgerState:
        """Processes the state and enforces a deterministic rule."""
        pass

# ------------------------------------------------------------------
# Concrete Rules Engine Implementations
# ------------------------------------------------------------------

class CapExThresholdRule(LedgerRule):
    """IRS Section 263(a) De Minimis Safe Harbor Rule."""
    def execute(self, state: LedgerState) -> LedgerState:
        for line in state.lines:
            if line.amount >= state.company_capex_threshold:
                line.suggested_category = "1500 - Fixed Assets (Depreciable)"
                state.cpa_warnings.append(
                    f"⚠️ CapEx Threshold (${state.company_capex_threshold}) exceeded for "
                    f"'{line.description}' (${line.amount:.2f}). Reclassified to Fixed Assets."
                )
        return state

class PersonalExpenseRule(LedgerRule):
    """Excludes personal items from employee payouts to prevent tax fraud."""
    def execute(self, state: LedgerState) -> LedgerState:
        valid_business_total = 0.0
        for line in state.lines:
            if line.ai_flagged_personal:
                state.cpa_warnings.append(
                    f"🛑 Excluded personal line item from reimbursement: '{line.description}' (${line.amount:.2f})."
                )
            else:
                valid_business_total += line.amount
        state.total_reimbursement_payable = valid_business_total
        return state

class DoubleEntryBalanceRule(LedgerRule):
    """Enforces mathematical balance: Total Debits must equal Total Credits."""
    def execute(self, state: LedgerState) -> LedgerState:
        total_debits = sum(entry["amount"] for entry in state.posted_entries if entry["type"] == "DEBIT")
        total_credits = sum(entry["amount"] for entry in state.posted_entries if entry["type"] == "CREDIT")
        
        if abs(total_debits - total_credits) > 0.001:
            raise ValueError(
                f"CRITICAL DOUBLE-ENTRY VIOLATION: Debits (${total_debits:.2f}) "
                f"do not equal Credits (${total_credits:.2f})."
            )
        return state

# ------------------------------------------------------------------
# Pipeline Orchestrator
# ------------------------------------------------------------------

class LedgerPipeline:
    def __init__(self):
        self.rules: List[LedgerRule] = []

    def add_rule(self, rule: LedgerRule) -> "LedgerPipeline":
        self.rules.append(rule)
        return self

    def process(self, initial_state: LedgerState) -> LedgerState:
        current_state = initial_state
        for rule in self.rules:
            current_state = rule.execute(current_state)
        return current_state
6. Agentic Workspace & Tool Calling System
The agent operates in a stateful chat session using predefined Python tool interfaces.

6.1 Python Agentic Session Engine
Python
class AccountingTools:
    """Read-only investigation tools available to the Session Agent."""

    @staticmethod
    def search_bank_statements(amount: float, date_range: str) -> Dict[str, Any]:
        # Connects to Plaid/Bank Webhook Cache in Postgres
        return {"status": "MATCH_FOUND", "txn_id": "tx_mercury_9921", "cleared_amount": amount}

    @staticmethod
    def check_vendor_tax_status(vendor_name: str) -> Dict[str, Any]:
        # Connects to Firm Compliance Storage
        if "uk agency" in vendor_name.lower():
            return {"has_w8ben": False, "is_foreign": True, "status": "BLOCKED"}
        return {"has_w9": True, "is_foreign": False, "status": "OK"}

@dataclass
class SessionAgent:
    submission_id: str
    sot_markdown: str
    tools: AccountingTools = field(default_factory=AccountingTools)

    def generate_action_plan(self) -> Dict[str, Any]:
        """Runs initial analysis and outputs a checklist for the CPA."""
        # Simulated LLM tool-calling output
        tax_info = self.tools.check_vendor_tax_status("Apex Design Studio UK")
        
        plan = {
            "submission_id": self.submission_id,
            "proposed_checklist": [
                {"action": "Match to Bank Wire #tx_mercury_9921", "status": "AUTO_MATCHED"},
                {"action": "Verify Form W-8BEN-E for foreign vendor", "status": tax_info["status"]}
            ],
            "requires_cpa_action": tax_info["status"] == "BLOCKED"
        }
        return plan
7. Multi-Tenant Database Schema (PostgreSQL)
To support isolation, dynamic chart of accounts, and vector memory retrieval, use the following schema design:

SQL
-- Enable Vector Extension for RAG Memory
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. CPA Firms (Top-Level Tenants)
CREATE TABLE cpa_firms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Client Accounts (Managed Businesses)
CREATE TABLE client_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_id UUID NOT NULL REFERENCES cpa_firms(id) ON DELETE CASCADE,
    client_name VARCHAR(255) NOT NULL,
    capex_threshold NUMERIC(10, 2) DEFAULT 2500.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Submissions (The Workpapers)
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES client_accounts(id) ON DELETE CASCADE,
    state VARCHAR(50) NOT NULL DEFAULT 'RAW', -- RAW, EXTRACTED, NEEDS_REVIEW, etc.
    sot_markdown_path TEXT,
    raw_file_s3_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Final Double-Entry General Ledger
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE RESTRICT,
    transaction_date DATE NOT NULL,
    posted_by_cpa_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    entry_type VARCHAR(10) NOT NULL CHECK (entry_type IN ('DEBIT', 'CREDIT')),
    amount NUMERIC(12, 2) NOT NULL,
    description TEXT
);

-- 5. Multi-Tenant Vector Memory (pgvector)
CREATE TABLE firm_memory_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firm_id UUID NOT NULL REFERENCES cpa_firms(id) ON DELETE CASCADE,
    client_id UUID REFERENCES client_accounts(id) ON DELETE CASCADE, -- NULL means Firm-Wide memory
    vendor_pattern VARCHAR(255) NOT NULL,
    categorization_rule TEXT NOT NULL,
    embedding vector(1536) NOT NULL, -- OpenAI text-embedding-3-small vector
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
8. Real-World Edge Case Validation Matrix
Edge Case	Problem Scenario	System Behavior & Rule Enforcement	Final Journal Entry Schema Output
1. Apple Store Purchase	$3,850 total ($2,899 MacBook, $1,599 Display, $399 AppleCare, -$1,346 discount).	Proportional discount applied. Net MacBook ($2,279.09) < $2,500 threshold. Both expensed or capitalized per policy override.	Debit: 1500 Assets ($2,279.09)

Debit: 6050 IT Exp ($1,570.91)


Credit: 2010 Visa ($3,850.00) |
| 2. Target / Costco Receipt | $542 total ($159 business supplies + $350 personal vacuum + taxes). | PersonalExpenseRule excludes vacuum + tax ($382.36). Calculates exact business reimbursement ($170.39). | Debit: 6120 Supplies ($123.42)


Debit: 6150 Breakroom ($46.97)


Credit: 2020 AP Employee ($170.39) |
| 3. Foreign Contractor (UK) | £2,500 GBP invoice + $45 wire fee. Missing Form W-8BEN-E. | Flagged as BLOCKED_COMPLIANCE. Wire fee separated to bank fees. Drafts W-8BEN request. | Debit: 6200 Design Fees ($3,275.00)


Debit: 6800 Wire Fees ($45.00)


Credit: 2010 Cash ($3,320.00) |
| 4. Multi-Currency Split | $450 AUD Atlassian charge split 70% Engineering / 30% Marketing. | Matches $297.45 USD cleared bank feed line. Split rule executes exact percentages on USD total. | Debit: 6010 Eng Software ($208.21)


Debit: 6020 Mktg Software ($89.24)


Credit: 1010 Bank ($297.45) |

9. Competitor Feature Theft & UX Directives
Borrow from Keeper.app: Implement the PENDING_CLIENT magic-link loop. If information is missing, the AI generates a single-click SMS/email prompt for the client, routing their answer back into the submission context.

Borrow from Botkeeper: Enable cross-tenant learning via the firm_memory_embeddings vector table so the entire firm benefits when one CPA categorizes a recurring vendor.

Avoid Digits' Pitfall: Do not hide raw data behind flashiness. Maintain a dense, high-efficiency dashboard with side-by-side view (Raw File / Markdown SoT on left, Chat Workspace & Drafted Ledger on right) with full keyboard shortcut support.

10. Direct Instructions for the Executing AI Agent
When implementing this repository:

Backend Framework: FastAPI (Python 3.11+) with Pydantic v2 for payload validation.

Database Access: SQLAlchemy 2.0 (Async) + pgvector-python.

Pipeline Structure: Place rules under app/core/pipeline/rules/ inheriting from LedgerRule.

VLM Integration: Place vision prompts under app/services/vlm_extractor.py ensuring output strictly matches submission_sot.md.

Session Agent: Implement agent state handlers in app/agents/session_agent.py using function calling / tool definitions.
