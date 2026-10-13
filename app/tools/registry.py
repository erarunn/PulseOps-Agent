from typing import Dict, Any, Callable, List, Optional
from app.tools.search import search_docs
from app.tools.service_tools import get_service
from app.tools.pr_tools import list_open_prs, get_pr, summarize_pr
from app.tools.ticket_tools import create_ticket_draft, list_tickets

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Keyword and semantic search over the Northstar engineering documentation (architecture, runbooks, oncall guides, policies).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or search phrase to look up in documentation (e.g. 'checkout-api 504 timeout', 'oncall schedule', 'circuit breaker')."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of documentation matching snippets to return.",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service",
            "description": "Look up service metadata by name or id (e.g. 'checkout-api', 'pricing-service', 'svc-fraud') including owner team, SLO, tier, and dependencies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_or_id": {
                        "type": "string",
                        "description": "The service name (e.g. 'checkout-api') or service id (e.g. 'svc-checkout-api')."
                    }
                },
                "required": ["name_or_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_open_prs",
            "description": "List all open pull requests across the Northstar checkout codebase.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pr",
            "description": "Fetch detailed metadata, description, and git diff summary for a specific pull request by number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "The PR number to inspect (e.g. 101, 102)."
                    }
                },
                "required": ["pr_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket_draft",
            "description": "Create and persist a local engineering ticket or incident draft. Drafts are safely stored locally and never pushed to external production ticketing systems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short descriptive title of the ticket or incident."
                    },
                    "description": {
                        "type": "string",
                        "description": "Comprehensive explanation of the issue, observed impact, and suggested investigation."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["P1", "P2", "P3", "P4"],
                        "description": "Priority severity level (P1 = critical outage, P2 = high degradation, P3 = medium, P4 = low/task)."
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional categorization tags (e.g. ['checkout', 'latency', 'oncall'])."
                    },
                    "team": {
                        "type": "string",
                        "description": "Suggested owner team (e.g. 'payments', 'core-platform', 'risk-engineering')."
                    }
                },
                "required": ["title", "description", "priority"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_pr",
            "description": "Generate and persist a structured PR summary containing change analysis, risk notes, affected services, and recommended reviewers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "The pull request number to summarize (e.g. 101, 102)."
                    },
                    "focus_areas": {
                        "type": "string",
                        "description": "Optional specific architectural concerns or risk vectors to highlight."
                    }
                },
                "required": ["pr_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tickets",
            "description": "Query sample engineering tickets and recent incidents with optional status or severity filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Optional filter: 'RESOLVED', 'INVESTIGATING', 'OPEN', 'IN_PROGRESS', 'BACKLOG'."
                    },
                    "severity": {
                        "type": "string",
                        "description": "Optional filter: 'P1', 'P2', 'P3', 'P4'."
                    }
                }
            }
        }
    }
]

def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    source_conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute tool by name and return standard result dict."""
    try:
        if name == "search_docs":
            return search_docs(
                query=arguments.get("query", ""),
                max_results=arguments.get("max_results", 3)
            )
        elif name == "get_service":
            return get_service(name_or_id=arguments.get("name_or_id", ""))
        elif name == "list_open_prs":
            return list_open_prs()
        elif name == "get_pr":
            return get_pr(pr_number=int(arguments.get("pr_number", 0)))
        elif name == "create_ticket_draft":
            return create_ticket_draft(
                title=arguments.get("title", ""),
                description=arguments.get("description", ""),
                priority=arguments.get("priority", "P3"),
                labels=arguments.get("labels", []),
                team=arguments.get("team", ""),
                source_conversation_id=source_conversation_id
            )
        elif name == "summarize_pr":
            return summarize_pr(
                pr_number=int(arguments.get("pr_number", 0)),
                focus_areas=arguments.get("focus_areas", ""),
                source_conversation_id=source_conversation_id
            )
        elif name == "list_tickets":
            return list_tickets(
                status=arguments.get("status", ""),
                severity=arguments.get("severity", "")
            )
        else:
            return {"error": f"Unknown tool '{name}'."}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
