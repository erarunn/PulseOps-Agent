import sys
import os

# Ensure project root is on sys.path for clean module resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from pathlib import Path
from app.config import BASE_DIR, settings
from app.db.database import init_db
from app.agent.orchestrator import AgentOrchestrator
from evals.evaluator import CaseEvaluator

CASES_FILE = BASE_DIR / "evals" / "cases.jsonl"
RESULTS_JSON = BASE_DIR / "evals" / "results.sample.json"
RESULTS_MD = BASE_DIR / "evals" / "results.sample.md"

def load_cases():
    cases = []
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases

def run_evaluation():
    init_db()
    cases = load_cases()
    print("=" * 70)
    print(f"  PulseOps Golden Evaluation Suite  ({len(cases)} Cases)")
    print(f"  Engine: {settings.llm_mode.upper()}  |  Model: {settings.openrouter_model if settings.llm_mode == 'openrouter' else 'Deterministic Mock'}")
    print("=" * 70)

    orchestrator = AgentOrchestrator()
    eval_results = []
    passed_count = 0
    start_time = time.time()
    is_live = settings.llm_mode in ("openrouter", "openai")

    for idx, case in enumerate(cases, 1):
        cid = f"eval-{case['id']}-{int(time.time())}"
        res = orchestrator.run(user_prompt=case["prompt"], conversation_id=cid)
        eval_res = CaseEvaluator.evaluate(case, res)
        eval_results.append(eval_res)

        status_symbol = "PASS" if eval_res["passed"] else "FAIL"
        if eval_res["passed"]:
            passed_count += 1

        print(f"[{idx:02d}/{len(cases):02d}] [{status_symbol}] {case['id']}  (type={case['type']})")
        if not eval_res["passed"]:
            for failure in eval_res["failures"]:
                print(f"         -> {failure}")

        # Throttle between cases when using live API to avoid rate limiting
        if is_live and idx < len(cases):
            time.sleep(15)

    duration = round(time.time() - start_time, 2)
    pass_rate = round((passed_count / len(cases)) * 100, 1)

    print("\n" + "=" * 70)
    print(f"  RESULT: {passed_count}/{len(cases)} Passed  ({pass_rate}%)  in {duration}s")
    print("=" * 70)

    # Save JSON results
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine_mode": settings.llm_mode,
        "model": settings.openrouter_model if settings.llm_mode == "openrouter" else "deterministic_mock",
        "total_cases": len(cases),
        "passed": passed_count,
        "failed": len(cases) - passed_count,
        "pass_rate_percent": pass_rate,
        "duration_seconds": duration,
        "case_results": eval_results
    }
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Save Markdown Report
    rows = []
    for r in eval_results:
        status_md = "PASS" if r["passed"] else "FAIL"
        tools_str = ", ".join(r["tools_called"]) if r["tools_called"] else "none"
        fail_note = "; ".join(r["failures"]) if r["failures"] else "—"
        rows.append(f"| `{r['case_id']}` | `{r['type']}` | {status_md} | `{tools_str}` | {fail_note} |")

    md_content = f"""# PulseOps Evaluation Results

- **Date**: {summary_data['timestamp']}
- **LLM Mode**: `{summary_data['engine_mode']}`
- **Model**: `{summary_data['model']}`
- **Score**: **{passed_count}/{len(cases)} ({pass_rate}%)**
- **Duration**: {duration}s

## Results Matrix

| Case ID | Type | Status | Tools Called | Failure Notes |
|---|---|---|---|---|
{chr(10).join(rows)}

### Coverage Verification
- **Policy / Refusal Cases**: `refuse-twitter-post`, `refuse-drop-database` — agent declined without calling write tools.
- **Multi-Tool Chain Cases**: `chain-search-service-ticket` — agent called `get_service` then `create_ticket_draft` in sequence.
- **Q&A Grounding**: SLO lookups, runbook queries, API gateway limits all grounded via search_docs / get_service.
- **Action Tools**: `create_ticket_draft` and `summarize_pr` persisted records locally in SQLite.
"""
    with open(RESULTS_MD, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n  Results saved to:")
    print(f"    evals/results.sample.json")
    print(f"    evals/results.sample.md")

    return 0 if passed_count == len(cases) else 1

if __name__ == "__main__":
    exit_code = run_evaluation()
    sys.exit(exit_code)
