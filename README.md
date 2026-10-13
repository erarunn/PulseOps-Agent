# PulseOps — Engineering Operations Agent

> A lightweight internal assistant that helps engineers answer questions about a knowledge base and take structured actions via LLM-powered tool calling.

---

## Quick Start

```bash
# 1. Clone and enter the project
cd PluseOps

# 2. Create .env from template
copy .env.example .env
# (Optionally) add your OPENROUTER_API_KEY and set LLM_MODE=openrouter

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Start the API + Web UI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 5. Open in browser
#    http://127.0.0.1:8000

# OR run the CLI demo (no server required)
python cli/demo.py

# OR run the CLI interactively
python cli/demo.py --interactive

# 6. Run the evaluation suite
python evals/run_evals.py
```

---

## Architecture Overview

```
pulseops/
├── app/
│   ├── main.py             # FastAPI entrypoint
│   ├── config.py           # Pydantic settings + env vars
│   ├── api/routes.py       # REST API endpoints
│   ├── agent/
│   │   ├── orchestrator.py # Multi-step tool loop (max 5 rounds)
│   │   ├── llm_client.py   # Live OpenRouter + Deterministic Mock engine
│   │   └── prompts.py      # System prompt + policy guardrails
│   ├── tools/
│   │   ├── registry.py     # OpenAI function-call schemas + dispatcher
│   │   ├── search.py       # Keyword + TF search over markdown docs
│   │   ├── service_tools.py# Service catalog lookup
│   │   ├── pr_tools.py     # PR listing, fetching, and summarization
│   │   └── ticket_tools.py # Ticket draft creator
│   └── db/
│       ├── database.py     # SQLite init and connection manager
│       ├── models.py       # Pydantic models
│       └── repository.py   # CRUD operations for all tables
├── data/
│   ├── docs/               # 8 Markdown knowledge base files
│   ├── services.json       # 6 synthetic services
│   ├── prs.json            # 4 synthetic pull requests
│   └── tickets.json        # 6 synthetic tickets / incidents
├── web/                    # Dark-mode web dashboard
├── cli/demo.py             # CLI demo runner
├── evals/
│   ├── cases.jsonl         # 14 golden test cases
│   ├── evaluator.py        # Deterministic grader
│   ├── run_evals.py        # Single-command runner
│   ├── results.sample.json # Committed sample results
│   └── results.sample.md   # Formatted results report
└── requirements.txt
```

---

## API Reference (with curl examples)

### POST /api/chat
```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the availability SLO for checkout-api?"}'
```

### GET /api/ticket-drafts
```bash
curl http://127.0.0.1:8000/api/ticket-drafts
```

### GET /api/pr-summaries
```bash
curl http://127.0.0.1:8000/api/pr-summaries
```

### GET /api/conversations/{id}
```bash
curl http://127.0.0.1:8000/api/conversations/conv-abc123
```

### GET /api/services
```bash
curl http://127.0.0.1:8000/api/services
```

### GET /api/health
```bash
curl http://127.0.0.1:8000/api/health
```

**Swagger API Docs**: http://127.0.0.1:8000/docs

---

## LLM Mode Configuration

| Mode | Set in `.env` | Notes |
|---|---|---|
| **Mock (default)** | `LLM_MODE=mock` | 100% offline, zero cost, deterministic. Best for evals and CI. |
| **OpenRouter (live)** | `LLM_MODE=openrouter` + `OPENROUTER_API_KEY=sk-or-...` | Uses `nvidia/nemotron-3-ultra-550b-a55b:free` by default. |
| **OpenAI (live)** | `LLM_MODE=openai` + `OPENAI_API_KEY=sk-...` | Uses `gpt-4o-mini` by default. |

---

## Demo Script — Key Scenarios

| # | Scenario | Expected Agent Behavior |
|---|---|---|
| 1 | `"What is the SLO for checkout-api?"` | Calls `get_service`, returns 99.9% / 350ms |
| 2 | `"Find who owns checkout-api and draft a P3 runbook ticket"` | Multi-step: `get_service` then `create_ticket_draft` |
| 3 | `"Summarize PR #101"` | Calls `summarize_pr`, returns structured risk record |
| 4 | `"Post to public Twitter"` | **Policy refusal** — no write tools called |

---

## Persistence Schema (SQLite)

| Table | Description |
|---|---|
| `conversations` | Chat sessions (id, label, timestamp) |
| `messages` | User and assistant messages per conversation |
| `tool_traces` | Per-step tool name, args, result, status |
| `ticket_drafts` | Locally persisted draft tickets (never pushed externally) |
| `pr_summaries` | Structured PR risk summary records |

---

## Known Limitations
- **Mock engine** uses deterministic keyword heuristics; does not generalize to arbitrary novel phrasings like a live LLM would.
- **Doc search** is BM25-style keyword; no semantic embedding / vector store.
- **Single conversation context**: conversation history is loaded from DB per turn but the mock engine doesn't leverage multi-turn context.

---

## Hours Spent
- **Architecture + Data Design**: ~1.5h
- **Agent + Tools + API**: ~3.5h
- **Web UI**: ~1.5h
- **Evals + Hardening**: ~2.0h
- **Documentation**: ~1.0h
- **Total**: ~9.5h

## LLM Mode Used
- Code generation: Antigravity AI Assistant (Google DeepMind)
- Default runtime: `mock` (deterministic)
- Live mode target: `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter
- Approximate API cost (mock mode only): **$0.00**
