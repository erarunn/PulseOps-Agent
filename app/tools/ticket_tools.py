import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.config import DATA_DIR
from app.db.repository import Repository

def get_tickets_catalog() -> List[Dict[str, Any]]:
    tickets_path = DATA_DIR / "tickets.json"
    if not tickets_path.exists():
        return []
    with open(tickets_path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_tickets(status: str = "", severity: str = "") -> Dict[str, Any]:
    """List sample engineering tickets or incidents with optional filters."""
    tickets = get_tickets_catalog()
    results = tickets
    if status:
        results = [t for t in results if t.get("status", "").upper() == status.upper()]
    if severity:
        results = [t for t in results if t.get("severity", "").upper() == severity.upper()]
    return {
        "count": len(results),
        "tickets": results
    }

def create_ticket_draft(
    title: str,
    description: str,
    priority: str = "P3",
    labels: Optional[List[str]] = None,
    team: str = "unassigned",
    source_conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Persist a local draft ticket (title, description, priority, labels, team). Never writes directly to external Jira."""
    valid_priorities = ["P1", "P2", "P3", "P4"]
    clean_priority = priority.strip().upper() if priority else "P3"
    if clean_priority not in valid_priorities:
        clean_priority = "P3"

    safe_labels = labels or []
    safe_team = team.strip() if team else "payments"

    draft = Repository.save_ticket_draft(
        title=title.strip(),
        description=description.strip(),
        priority=clean_priority,
        labels=safe_labels,
        team=safe_team,
        source_conversation_id=source_conversation_id
    )

    return {
        "ok": True,
        "ticket_id": draft.id,
        "title": draft.title,
        "priority": draft.priority,
        "labels": draft.labels,
        "team": draft.team,
        "status": "LOCAL_DRAFT_CREATED",
        "human_in_the_loop_notice": "Draft created in local database only. No external ticketing write was performed."
    }
