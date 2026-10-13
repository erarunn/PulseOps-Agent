# PROCESS.md — AI-Native Workflow Log

## 1. Decomposition

The work was broken into 8 sequential phases, starting with **contracts and data first**:

1. **Synthetic corpus design** — Service inventory, PR metadata, incident tickets, and 8 Markdown docs created before any code.
2. **Eval cases before implementation** — 14 golden cases written before the agent was built, making them honest tests rather than post-hoc rationalizations.
3. **Database schema** — All persistence tables modeled and initialized early to avoid retrofitting.
4. **Tool implementations** — Each tool independently implemented and unit-testable in isolation.
5. **Agent orchestrator** — Multi-step loop written after tools were stable.
6. **FastAPI layer** — Routes added after agent loop was proven via CLI.
7. **Web UI** — Built last, as a presentation layer over the working API.
8. **Hardening + docs** — Eval suite run, failures diagnosed and fixed, README/DESIGN/PROCESS written.

**Key pattern**: Eval cases were the contract. Implementation was done to satisfy those contracts, not to create post-hoc-passing tests.

---

## 2. Tools & Agents Used

- **Antigravity AI (Google DeepMind)**: Primary coding assistant. Used for all file generation, debugging, and iterative fixing.
- **Python 3.14 + FastAPI + SQLite**: Core runtime stack.
- **No Cursor, Copilot, or external Claude** usage — all AI assistance was through the Antigravity assistant.

**Rough AI vs hand-written split**:
- ~85% of code was AI-drafted (structure, boilerplate, initial implementations).
- ~15% was manual correction (fixing mock engine dispatch order, search snippet quality, encoding issues, import paths).

---

## 3. Prompt / System Design Highlights

### System Prompt Design (agent/prompts.py)
The system prompt is structured with explicit numbered operating rules:

```
1. GROUNDED ANSWERS: Always cite source documents.
2. MULTI-STEP REASONING: Search before acting.
3. WRITE SAFETY: Drafts are local only, never external.
4. POLICY REFUSAL: Decline unsafe/external requests WITHOUT calling write tools.
5. CONCISE & PROFESSIONAL: Engineering-quality responses.
```

Key design choice: Policy refusal is rule #4 with an explicit instruction to **not call write tools** under refusal — not just to say no.

### Tool Schema Example (registry.py)
```json
{
  "name": "create_ticket_draft",
  "description": "Create and persist a local draft ticket. Never writes to external Jira.",
  "parameters": {
    "priority": {
      "type": "string",
      "enum": ["P1", "P2", "P3", "P4"]
    }
  },
  "required": ["title", "description", "priority"]
}
```

The description explicitly names the safety boundary ("Never writes to external Jira") so the LLM can self-report this in answers.

---

## 4. Verification Loop

**What was self-verified**:
- Eval suite run after every significant mock engine change.
- CLI demo run to verify end-to-end UX.
- FastAPI health and chat endpoints tested via Python `urllib` (no Playwright available).
- Search engine tested in isolation with direct Python calls before running evals.

**What was AI-generated and then verified**:
- Tool registry schemas: AI-generated, manually reviewed for JSON correctness.
- DB repository: AI-generated, verified by running the evals which exercise all DB paths.
- Mock engine dispatch: Initially incorrect (loop bug, missed patterns) — caught by eval failures.

**Evals caught**: 6 distinct bugs in the mock engine, all fixed iteratively over 4 eval runs.

---

## 5. Iteration Story

**AI suggested X**: The initial mock engine `_handle_post_tool_step` used `"team" in str(tool_data)` as the guard for multi-tool chaining (dispatching `create_ticket_draft` after `get_service`).

**Problem found (X was wrong)**: This condition fired even when `create_ticket_draft` had just run (its result also contains `team`), causing an infinite loop that called `create_ticket_draft` 5 times and exhausted the step cap without producing a final answer.

**Why it failed**: `"team" in str(tool_data)` is a content-based heuristic — it can't distinguish between a service lookup result and a ticket draft result.

**Fix applied (Z)**: Changed the guard to check `last_tool_name == "get_service"` (explicit tool-name tracking via `tool_msg.get("name", "")`). The tool name in the message dict is reliable and unambiguous, unlike string content matching.

**Lesson**: Dispatch logic should be based on **tool identity** (which tool just ran), not **content similarity** (what the result looks like).

---

## 6. What Would Be Automated Next

With another half-day and AI agents, I would target:

1. **Vector search with Qdrant**: Point an agent at the corpus and `pip install qdrant-client`, have it embed all docs and rewrite `search_docs` to use cosine similarity. The keyword search fails on synonyms ("rollback" vs "revert").

2. **CI pipeline**: A GitHub Actions YAML that runs `python evals/run_evals.py` on every PR and fails the build if pass rate < 100%.

3. **Streaming responses**: Add FastAPI SSE endpoint (`/api/chat/stream`) and update the web UI to show tool calls appearing in real-time as they execute.

4. **Docker Compose**: One-command bring-up with `docker-compose up` exposing the app on port 8000.

5. **LLM-as-judge calibration**: Take 3–5 hand-labeled response quality samples and use an LLM to score new responses against them, extending the eval suite beyond substring matching.
