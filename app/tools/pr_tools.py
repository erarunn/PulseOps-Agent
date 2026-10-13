import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.config import DATA_DIR
from app.db.repository import Repository

def get_prs_catalog() -> List[Dict[str, Any]]:
    prs_path = DATA_DIR / "prs.json"
    if not prs_path.exists():
        return []
    with open(prs_path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_open_prs() -> Dict[str, Any]:
    """List all open pull requests with summary metadata."""
    prs = get_prs_catalog()
    open_prs = [p for p in prs if p.get("status") == "OPEN"]
    return {
        "count": len(open_prs),
        "open_prs": [
            {
                "number": p["number"],
                "title": p["title"],
                "author": p["author"],
                "service": p["service"],
                "files_changed_count": len(p.get("files_changed", [])),
                "branch": p.get("branch")
            }
            for p in open_prs
        ]
    }

def get_pr(pr_number: int) -> Dict[str, Any]:
    """Retrieve full details, description, and diff of a pull request by PR number."""
    prs = get_prs_catalog()
    for p in prs:
        if p["number"] == pr_number:
            return {"found": True, "pr": p}
    return {
        "found": False,
        "error": f"Pull request #{pr_number} was not found."
    }

def summarize_pr(
    pr_number: int,
    focus_areas: str = "",
    source_conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Produce a structured PR summary with risk notes and persist the summary record locally."""
    pr_res = get_pr(pr_number)
    if not pr_res["found"]:
        return {"ok": False, "error": pr_res["error"]}

    pr = pr_res["pr"]
    title = pr.get("title", "")
    desc = pr.get("description", "")
    diff = pr.get("diff_summary", "")
    service = pr.get("service", "unknown")

    # Deterministic heuristics for risk evaluation
    risk_level = "LOW"
    risk_factors = []

    text_to_check = (title + " " + desc + " " + diff).lower()
    if "retry" in text_to_check or "timeout" in text_to_check or "exponential backoff" in text_to_check:
        risk_level = "MEDIUM"
        risk_factors.append("Modifies retry and timeout behavior under network failure; potential risk of connection accumulation if misconfigured.")
    if "cve" in text_to_check or "security" in text_to_check:
        risk_level = "LOW"
        risk_factors.append("Security patch / base image update with low regression risk if integration tests pass.")
    if "threshold" in text_to_check or "fraud" in text_to_check:
        risk_level = "MEDIUM"
        risk_factors.append("Adjusts risk evaluation scoring thresholds; could impact checkout fraud exposure or challenge drop-off.")
    if "cache" in text_to_check or "redis" in text_to_check:
        risk_level = "LOW"
        risk_factors.append("Performance refactor on caching layer; verify cache hit rates and memory boundaries.")

    if not risk_factors:
        risk_factors.append("Standard code modification within service bounds.")

    structured_summary = {
        "pr_number": pr_number,
        "title": title,
        "author": pr.get("author"),
        "service": service,
        "status": pr.get("status"),
        "overview": desc,
        "files_impacted": pr.get("files_changed", []),
        "risk_level": risk_level,
        "risk_notes": risk_factors,
        "recommended_reviewers": [f"{service}-owner", "platform-qa"],
        "focus_areas_noted": focus_areas if focus_areas else "Standard architectural review"
    }

    # Persist summary
    record = Repository.save_pr_summary(
        pr_number=pr_number,
        summary=structured_summary,
        source_conversation_id=source_conversation_id
    )

    return {
        "ok": True,
        "summary_id": record.id,
        "pr_number": pr_number,
        "summary": structured_summary
    }
