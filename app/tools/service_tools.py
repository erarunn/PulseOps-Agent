import json
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import DATA_DIR

def get_services_catalog() -> list:
    services_path = DATA_DIR / "services.json"
    if not services_path.exists():
        return []
    with open(services_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_service(name_or_id: str) -> Dict[str, Any]:
    """Look up a microservice by its name or ID in the service catalog."""
    query = name_or_id.strip().lower()
    services = get_services_catalog()
    
    for s in services:
        if s["id"].lower() == query or s["name"].lower() == query:
            return {"found": True, "service": s}

    # Partial match
    for s in services:
        if query in s["id"].lower() or query in s["name"].lower():
            return {"found": True, "service": s}

    return {
        "found": False,
        "error": f"Service '{name_or_id}' not found in catalog.",
        "available_services": [s["name"] for s in services]
    }
