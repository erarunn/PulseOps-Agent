# ASSUMPTIONS.md — Scope & Design Assumptions

## Synthetic Domain
- All data (services, PRs, tickets, documentation) is entirely fictional ("Northstar Checkout").
- No proprietary Robosoft or real client data has been used.

## LLM & API Keys
- No API keys are committed to the repository. All secrets must be set via `.env`.
- The system defaults to `LLM_MODE=mock` (fully offline, zero-cost, deterministic).
- When using OpenRouter, the project targets `nvidia/nemotron-3-ultra-550b-a55b:free` (free tier model).

## Write Safety
- `create_ticket_draft` and `summarize_pr` create **local SQLite records only**.
- No tool calls any external service (Jira, GitHub, Slack, PagerDuty, Twitter, etc.).
- All write-tool outputs include a `human_in_the_loop_notice` field explicitly stating the draft-only policy.

## Search
- The doc search is keyword-based (BM25-style TF with title boost), not semantic/vector-based.
- This is sufficient for the 8-file corpus defined in this project.

## Evaluation
- Golden cases are evaluated with deterministic substring / tool-name graders (no LLM-as-judge for the core suite).
- The 14 golden cases were written before the agent implementation to ensure honest evaluation.

## Conversation Scope
- Each evaluation run uses isolated conversation IDs (`eval-{case_id}-{timestamp}`) to avoid DB state contamination between test runs.

## Production Readiness
- This is a demonstration system. It is not hardened for multi-tenant use, authentication, or production deployment.
- Rate limiting, authentication, and input sanitization are out of scope for this submission.
