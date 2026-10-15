# DESIGN.md — PulseOps Architecture Decision Record

## 1. Problem Statement

Build a lightweight Engineering Operations Agent that:
- Answers grounded questions from an internal knowledge base.
- Executes structured write-side actions (ticket drafting, PR summarization) as local drafts with no production side effects.
- Runs multi-step tool use in a controlled loop with explicit step caps.
- Is evaluable via a deterministic golden test suite.

---

## 2. Architecture Decisions

### 2.1 Agent Loop Design

**Decision**: Custom synchronous multi-step loop in `AgentOrchestrator` (not LangGraph or CrewAI).

**Rationale**:
- The tool set is small and sequential (5 tools, max 5 steps). Framework overhead from LangGraph is unjustified.
- A hand-rolled loop is simpler to audit, trace, and extend — critical for a security-sensitive internal tool.
- Explicit step cap (`max_agent_steps=5`) prevents infinite reasoning loops.

**Loop flow** (full diagram: [AGENT_GRAPH.md](AGENT_GRAPH.md)):
```
User Prompt
  -> Build context (system prompt + history)
  -> LLM Turn -> Tool Calls?
      Yes -> execute_tool() -> append result -> loop
      No  -> Final answer -> persist -> return
```

**Stopping rules**: Loop exits when (a) no tool calls are returned, (b) step cap reached, or (c) an exception occurs.

---

### 2.2 Dual LLM Engine (Live + Mock)

**Decision**: Two interchangeable clients behind a common `LLMResponse` interface.

| Engine | Class | When Used |
|---|---|---|
| Live | `LiveLLMClient` | When `LLM_MODE=openrouter` and valid API key is set |
| Mock | `MockLLMClient` | Default: `LLM_MODE=mock`; also used as fallback |

**Mock engine design**: Deterministic keyword-pattern dispatcher. Inspects user prompt and last tool name (`last_tool_name`) to route to the correct tool call. This enables 100% reproducible evals with zero API cost.

**Trade-off**: Mock engine doesn't generalize to arbitrary phrasings — acceptable for demonstration and CI but requires a live LLM for production usage.

---

### 2.3 Tool System & Schemas

**Decision**: OpenAI function-calling JSON schema format for all tool definitions.

- 7 tools total: `search_docs`, `get_service`, `list_open_prs`, `get_pr`, `create_ticket_draft`, `summarize_pr`, `list_tickets`.
- All tool schemas use `type: object` with typed properties and `required` arrays.
- Write tools (`create_ticket_draft`, `summarize_pr`) always persist to local SQLite only — never to external systems.

**Least-privilege principle**: No tool has the ability to delete, modify production records, or call external APIs with side effects.

---

### 2.4 Document Retrieval (Search)

**Decision**: Keyword/TF-based paragraph-level search over Markdown files.

**Rationale**:
- Corpus is tiny (8 docs, ~50KB total). Semantic embedding / vector store overhead is unnecessary.
- BM25-style term frequency with title boost is sufficient for the evaluation cases.
- `search_docs` returns document name, title, and the most relevant paragraph snippet (not the full doc), keeping context tight.

**Trade-off**: Won't handle synonym queries well (e.g. "rollback" vs "revert"). A vector store (Qdrant, sqlite-vss) would address this if the corpus grows.

---

### 2.5 Persistence Layer

**Decision**: SQLite via Python `sqlite3` standard library (no ORM).

**Schema**:
- `conversations` → `messages` → `tool_traces` (cascade)
- `ticket_drafts` and `pr_summaries` as standalone artifact tables

**Rationale**: SQLite is serverless, zero-config, and sufficient for a single-node demo. PostgreSQL + Docker Compose was considered and noted as a stretch goal.

---

### 2.6 Policy Guardrails

**Decision**: Guardrails enforced at two levels:

1. **System Prompt level**: Explicit instructions to decline out-of-scope requests (external writes, public postings, destructive commands).
2. **Mock engine level**: Keyword pattern matching for known unsafe phrases (e.g. "twitter", "drop database") returns a refusal content response without calling any write tools.

This dual enforcement ensures robustness even if the LLM partially ignores the system prompt.

---

## 3. Evaluation Strategy

**Decision**: Deterministic grader with 14 golden cases (no LLM-as-judge for core suite).

**Grader checks per case**:
- `must_call`: every listed tool must appear in `tool_traces`.
- `must_not_call`: listed tools must NOT appear (for policy/refusal cases).
- `must_call_any`: at least one of the listed tools must be called.
- `answer_contains`: substring checks on final answer (case-insensitive).
- `answer_declines`: refusal indicator words in answer.
- `ticket_priority`: validates exact priority argument in `create_ticket_draft` args.

**Why deterministic over LLM-as-judge?** Deterministic graders are reproducible, transparent, and zero-cost. LLM-as-judge was considered as a stretch goal.

---

## 4. Known Limitations & Future Work

| Limitation | Suggested Improvement |
|---|---|
| Mock engine is keyword-based | Replace with live LLM (OpenRouter) for production |
| No vector search | Add Qdrant or sqlite-vss for semantic retrieval |
| Single-node SQLite | Migrate to PostgreSQL + Docker Compose for multi-user |
| No streaming responses | Add SSE streaming to FastAPI for real-time UX |
| No multi-turn context in mock | Mock should replay message history for richer context |
