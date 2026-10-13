import sys
import os
import json

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set stdout to UTF-8 for Windows compatibility
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.agent.orchestrator import AgentOrchestrator
from app.db.database import init_db

DEMO_SCENARIOS = [
    {
        "title": "Scenario 1: Grounded Architecture & SLO Lookup",
        "prompt": "What is the availability SLO and latency target for checkout-api?"
    },
    {
        "title": "Scenario 2: Multi-Tool Chain (Service Lookup + Ticket Drafting)",
        "prompt": "Find who owns checkout-api and open a P3 draft about missing runbook coverage for that service."
    },
    {
        "title": "Scenario 3: Structured Pull Request Risk Audit",
        "prompt": "Summarize PR #101 and note any operational risks."
    },
    {
        "title": "Scenario 4: Policy Refusal (Safety Guardrail)",
        "prompt": "Post this incident root cause to our public Twitter account immediately."
    }
]

def run_scenario(orchestrator: AgentOrchestrator, scenario: dict):
    print("\n" + "=" * 70)
    print(f">> {scenario['title']}")
    print(f"   User: \"{scenario['prompt']}\"")
    print("-" * 70)

    res = orchestrator.run(scenario['prompt'])

    traces = res.get("traces", [])
    if traces:
        print(f"   [Tools executed: {len(traces)}]")
        for idx, t in enumerate(traces, 1):
            status = "OK" if t.get("ok") else "FAIL"
            args_preview = json.dumps(t.get("args", {}))[:80]
            print(f"   [{idx}] {t.get('tool_name')} ({status}) -> {args_preview}")
        print("-" * 70)

    answer = res.get("answer", "")
    print(f"   PulseOps Response:\n{answer}")
    print("=" * 70)

def main():
    init_db()
    orchestrator = AgentOrchestrator()

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        print("\n[PulseOps] Interactive Terminal Session started. Type 'exit' or 'quit' to stop.")
        cid = None
        while True:
            try:
                user_input = input("\n[You]: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("[PulseOps] Session ended.")
                    break
                res = orchestrator.run(user_input, conversation_id=cid)
                cid = res["conversation_id"]
                traces = res.get("traces", [])
                if traces:
                    print(f"\n  [Tools used: {', '.join([t['tool_name'] for t in traces])}]")
                print(f"\n[PulseOps]:\n{res['answer']}")
            except (KeyboardInterrupt, EOFError):
                break
    else:
        print("\n=======================================================")
        print("  PulseOps Engineering Assistant - Automated CLI Demo  ")
        print("=======================================================")
        for s in DEMO_SCENARIOS:
            run_scenario(orchestrator, s)
        print("\n[DONE] Automated walkthrough completed successfully!")
        print("[TIP]  Run `python cli/demo.py --interactive` for an interactive shell session.")

if __name__ == "__main__":
    main()
