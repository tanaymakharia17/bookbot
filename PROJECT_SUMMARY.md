# Bookbot — Project Summary

> Agentic AI bookkeeping for CPA firms. Human-in-the-loop: AI drafts, Python enforces the math, the CPA approves.

---

## 1. Stack at a glance

```
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  Streamlit (FE)    │ HTTP│  Django + DRF (BE) │ SQL │  PostgreSQL 16     │
│  :8501             │────►│  :8000             │────►│  :5432             │
└────────────────────┘     └─────────┬──────────┘     └────────────────────┘
         ▲                           │
         │                  ┌────────▼────────┐     ┌────────────────────┐
   nginx gateway            │ Celery worker   │────►│  Redis 7  :6379    │
   :8500 (single entry)     │ (VLM extraction)│     └────────────────────┘
                            └────────┬────────┘
                                     │ HTTPS
                            ┌────────▼────────┐
                            │  OpenRouter     │  (vision + tool calling)
                            └─────────────────┘
```

| Piece | Tech |
|---|---|
| Frontend | Streamlit (single-page router, session state) |
| Backend | Django 5 + DRF, pure-Python rule pipeline |
| DB | PostgreSQL (3 tables — JSONFields for workpaper data) |
| Async | Celery + Redis (`core.extract_submission`) |
| LLM | OpenRouter — `qwen/qwen3.7-flash` (vision + tools, reasoning off) |
| Files | local disk: `media/submissions/<id>/` |
| Gateway | nginx — one port, routes `/`→FE, `/api/`→BE, upload-friendly |

---

## 2. Repository layout

```
bookbot/
├── backend/        Django project, apps: core · api · services · agents
├── frontend/       Streamlit app, views/ + components/
├── seed/           dummy data (JSON) + sample docs — loaded by make seed
├── media/          uploaded documents (gitignored)
├── infrastructure/ nginx.conf (gateway)
├── docker-compose.yml + Makefile
└── PROJECT_SUMMARY.md  ← this file
```

---

## 3. Database — 3 tables

```
┌──────────────────────┐
│ core_cpafirm         │
├──────────────────────┤
│ id            uuid PK│
│ firm_name     text   │
│ created_at    ts     │
└─────────┬────────────┘
          │ 1
          │
          │ *
┌─────────▼────────────┐          ┌──────────────────────────────┐
│ core_clientaccount   │ 1      * │ core_submission              │
├──────────────────────┤──────────├──────────────────────────────┤
│ id            uuid PK│          │ id               uuid PK     │
│ firm_id       FK     │          │ client_id        FK          │
│ client_name   text   │          │ state            enum*       │
│ created_at    ts     │          │ vendor, payment_method, …    │
└──────────────────────┘          │ file_names, reference_files  │
                                  │ line_items, document_context │
                                  │ tasks, pending_plan          │
                                  │ chat_messages, tokens_used   │
                                  │ journal_entry, blocker…      │
                                  └──────────────────────────────┘
(* state: RAW · EXTRACTED · NEEDS_REVIEW · PENDING_CLIENT · BLOCKED_COMPLIANCE · COMMITTED)
```

### `core_submission` fields

| Field | Type | Meaning |
|---|---|---|
| `state` | char | lifecycle state (above) |
| `vendor`, `payment_method`, `channel` | char | extracted metadata |
| `raw_input` | text | CPA's free-text context at upload |
| `sot_markdown` | text | generated Source of Truth |
| `document_context` | JSON | per-file digest `{file, vendor, date, total, text}` |
| `file_names` | JSON | saved documents |
| `reference_files` | JSON | attached but not saved (no recompute) |
| `line_items` | JSON | extracted/committed line items |
| `tasks` | JSON | action checklist `{id,title,done,source}` |
| `pending_plan` | JSON | **staged** ops `{save_files, line_item_ops, task_ops}` |
| `journal_entry` | JSON | posted double-entry (debit/credit lines) |
| `chat_messages` | JSON | full conversation `[{role: cpa\|agent, content}]` |
| `tokens_used` | int | cumulative LLM tokens for this submission |
| `blocker`, `blocker_resolved` | text/bool | compliance gate |
| `created_at`, `updated_at`, `approved_at` | ts | timestamps |

Journal lines are **not** a table (MVP) — they live in `journal_entry` JSON.

---

## 4. APIs — what each one does

Base: `/api/v1/` · no auth yet · single default firm.

### 4.1 Health

```
GET /health/  ──►  {"status":"ok"}
```

### 4.2 Clients (companies)

```
GET  /clients/          ──►  list w/ aggregate counts
POST /clients/          ──►  create {name} (unique per firm)
GET  /clients/{id}/     ──►  one client
```

### 4.3 Submissions

```
POST /submissions/  {client_id, file_names[], raw_input}
        │
        ├─ save Submission(state=RAW)
        ├─ copy matching staged/seed files → media/submissions/<id>/
        └─ files on disk? ──yes──► Celery: extract_submission ──► EXTRACTED
                          └─no───► stays RAW (waiting for /documents/)

POST /submissions/{id}/documents/   (multipart files[])
        │
        ├─ save bytes → media/submissions/<id>/
        ├─ append names to file_names
        └─ Celery: extract_submission ──► EXTRACTED

GET  /submissions/            ?client=&state=   ──► list
GET  /submissions/{id}/                        ──► full workpaper + projected + plan_labels
```

### 4.4 Chat with the agent

```
GET  /submissions/{id}/chat/   ──► [{role, content}]  (full history)

POST /submissions/{id}/chat/  {message}
        │
        ├─ append "cpa" message
        ├─ build context: files + FULL document text + line items
        │                 + tasks + pending plan + ALL chat messages
        ├─ token guard: >60k this call OR >300k total?
        │        └─ yes ──► ⚠️ error + limit_reached (no LLM call)
        ├─ LLM tool loop (≤4 turns): inspect_document / add|update|remove_line_item
        │                            / exclude_personal / capitalize / discount / split
        │                            / add_task / complete_task
        ├─ tools STAGE ops into pending_plan (nothing applied yet)
        └─ append "agent" reply ──► {reply, submission}
```

### 4.5 Pending plan (staged changes)

```
POST /submissions/{id}/plan/files/  {files:[{name, save:bool}]}
        save=true  ──► stage save (will recompute)
        save=false ──► reference file only (no recompute)

POST /submissions/{id}/plan/tasks/  {title} | {task_id,done} | {task_id,remove}
DELETE /submissions/{id}/plan/ops/{op_id}/     ──► remove one staged op

POST /submissions/{id}/plan/execute/
        └─ apply: save files → recompute (VLM) → line ops → reseed agent tasks → task ops
           clear plan, state ──► NEEDS_REVIEW

POST /submissions/{id}/plan/discard/  ──► clear plan, nothing changes
```

### 4.6 Journal & approval

```
GET /submissions/{id}/journal_preview/
        │
        └─ rule pipeline: personal-exclude → capex → build debit/credit → balance check
           ──► {lines[], total_debits, total_credits, balanced, warnings[]}

POST /submissions/{id}/approve/
        guards: not RAW / not BLOCKED / no pending plan / has business items
        ──► build journal ──► DoubleEntryBalance ──► state=COMMITTED + journal_entry
           tokens post task done + agent chat note

POST /submissions/{id}/resolve_compliance/  ──► BLOCKED_COMPLIANCE → NEEDS_REVIEW
```

### 4.7 Ledger

```
GET /ledger/            ?client=   ──► posted entries (date, vendor, total, balanced)
GET /ledger/{entry_id}/            ──► entry + lines + totals (404 if missing)
```

### 4.8 Proxy-safe uploads

```
GET  /uploads/            ──► HTML upload page (bypasses Streamlit's upload endpoint)
POST /uploads/            ──► save to media/uploads/ (staging)
GET  /uploads/available/  ──► {files:[…]} seed + staged names
```

---

## 5. End-to-end flow (one submission)

```
 1 UPLOAD          CPA picks files + notes
                   │
 2 EXTRACT         Celery ─► OpenRouter VLM reads images/PDFs
                   │         writes: vendor, payment_method, line_items,
                   │                 document_context, SOT markdown, tasks, chat
                   ▼
 3 REVIEW          CPA chats; agent can re-read a file (inspect_document)
                   │         and stages corrections in pending_plan
                   ▼
 4 EXECUTE PLAN    staged ops applied to committed state
                   │
 5 JOURNAL         deterministic pipeline builds debits/credits + balance check
                   │
 6 APPROVE         state=COMMITTED, journal_entry saved
                   ▼
 7 LEDGER          entry visible in the general ledger
```

---

## 6. LLM usage

| Where | Model | Notes |
|---|---|---|
| Extraction (VLM) | `qwen/qwen3.7-flash` | vision + PDF text/page-images; strict JSON; reasoning **off** |
| Chat agent | `qwen/qwen3.7-flash` | tool calling; full history; reasoning **off** |
| Provider | OpenRouter (`OPENROUTER_API_KEY`) | any model via env |

- **Reasoning disabled** (`reasoning: {enabled:false}`) — otherwise the cheap reasoning models return empty content.
- **Prompt-cache hint**: `X-Session-Id: <submission id>` on agent calls.
- **Cost guard**: `AGENT_CONTEXT_MAX_TOKENS=60000` per call, `AGENT_SUBMISSION_TOKEN_BUDGET=300000` per submission → hard stop with a clear message.
- **Fallback**: no key / LLM error → deterministic keyword responder (with a ⚠️ notice in chat).

---

## 7. Deterministic rule pipeline

```
LedgerState(lines)
   ├─ PersonalExpenseRule   → exclude personal items, tot reimbursement
   ├─ CapExThresholdRule    → amount ≥ $2,500 → "Fixed Assets" (account 1500)
   ├─ JournalBuilderRule    → DR by category (1500/6050/6120/6010/6150/6200/6300/6400/6999)
   │                          CR total to payment account (2010 card / 1010 cash)
   └─ DoubleEntryBalanceRule → ΣDebits == ΣCredits else raise
```

Pure Python, no Django imports → unit-tested in isolation.

---

## 8. State machine

```
RAW ──► EXTRACTED ──► NEEDS_REVIEW ──┬──► COMMITTED   (terminal)
                          ▲           ├──► PENDING_CLIENT ──► NEEDS_REVIEW
                          │           └──► BLOCKED_COMPLIANCE ──► NEEDS_REVIEW / COMMITTED
                          └─────────────────────── (resolve / recompute)
```

---

## 9. Storage layout

```
media/
├── submissions/<submission_id>/<file>   ← saved documents (fed to the VLM)
└── uploads/<file>                       ← staging from the fallback upload page
seed/files/*.pdf                         ← sample docs copied in by `make seed`
```

---

## 10. Commands

```bash
make up          # start the stack
make seed        # load dummy companies + submissions + sample files
make migrate     # apply migrations
make logs        # tail logs
make test        # 41 tests (models, pipeline, FSM, APIs, agent tools)
make down        # stop
```

URLs: app **http://localhost:8500** (gateway) · FE direct `:8501` · API `:8000` · admin `/admin/`.

---

## 11. Current limits (next steps)

| Area | Status |
|---|---|
| Auth / multi-firm | ❌ single default firm, `AllowAny` |
| Journal storage | JSON on Submission (not normalised tables) |
| Vector memory (pgvector) | ❌ `FirmMemory` not built |
| Accounting sync | ❌ no QuickBooks/Xero |
| Long chats | hard token stop at 300k (no compaction) |
| VLM quality | cheap model — swap `VLM_MODEL` for better extraction |

---

## 12. Key files (where to look)

| Concern | File |
|---|---|
| Models | `backend/apps/core/models/` |
| State machine | `backend/apps/core/fsm.py` |
| Rule pipeline | `backend/apps/core/pipeline/` |
| APIs | `backend/apps/api/{urls,views,serializers}.py` |
| VLM extraction | `backend/apps/services/vlm.py` |
| Agent + tools | `backend/apps/services/agent.py`, `backend/apps/agents/tools.py` |
| Pending plan | `backend/apps/services/plan.py` |
| Projection | `backend/apps/services/projection.py` |
| Frontend routing | `frontend/app.py`, `frontend/state.py` |
| Review UI | `frontend/views/chat_workspace.py` |
