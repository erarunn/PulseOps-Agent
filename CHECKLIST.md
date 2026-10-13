# PulseOps — Submission Checklist

## Status: COMPLETE ✅

| Check | Status | Notes |
|---|---|---|
| Fresh clone / clean env: app starts with documented commands | ✅ | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Ask a question and get a grounded answer with doc references | ✅ | All QA cases pass; citations included in answers |
| Create a ticket draft via agent and see it persisted | ✅ | `ticket_drafts` table in SQLite; returned in `/api/ticket-drafts` |
| Summarize a PR via agent and see it persisted | ✅ | `pr_summaries` table in SQLite; returned in `/api/pr-summaries` |
| Tool traces visible in DB | ✅ | `tool_traces` table; returned in `/api/conversations/{id}` |
| `evals` command runs; sample results committed | ✅ | `python evals/run_evals.py` → 14/14 (100%) |
| Golden set ≥ 12 cases, including ≥ 1 refusal and ≥ 1 multi-tool chain | ✅ | 14 cases: 2 refusal, 1 multi-tool chain |
| DESIGN.md + PROCESS.md present | ✅ | Both files complete |
| No API keys committed | ✅ | `.env.example` only; `.env` is in `.gitignore` |
| Hours logged; scope limits respected | ✅ | ~9.5 hours; all scope within spec |

## Eval Results (from `evals/results.sample.md`)

| Type | Cases | Passed |
|---|---|---|
| Q&A Grounding | 6 | 6 |
| Tool Actions | 5 | 5 |
| Policy Refusal | 2 | 2 |
| Multi-Tool Chain | 1 | 1 |
| **Total** | **14** | **14 (100%)** |
