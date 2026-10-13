from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.config import settings
from app.agent.orchestrator import AgentOrchestrator
from app.db.repository import Repository
from app.tools.service_tools import get_services_catalog

router = APIRouter(prefix="/api")

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_label: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    steps_taken: int
    traces: List[Dict[str, Any]]

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    orchestrator = AgentOrchestrator()
    result = orchestrator.run(
        user_prompt=req.message.strip(),
        conversation_id=req.conversation_id,
        user_label=req.user_label
    )
    return ChatResponse(**result)

@router.get("/conversations/{conversation_id}")
def get_conversation_endpoint(conversation_id: str):
    detail = Repository.get_conversation_detail(conversation_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found.")
    return detail

@router.get("/traces/{conversation_id}")
def get_traces_endpoint(conversation_id: str):
    traces = Repository.get_traces(conversation_id)
    return {"conversation_id": conversation_id, "traces": [t.model_dump() for t in traces]}

@router.get("/ticket-drafts")
def list_ticket_drafts_endpoint():
    drafts = Repository.list_ticket_drafts()
    return {"count": len(drafts), "ticket_drafts": [d.model_dump() for d in drafts]}

@router.get("/pr-summaries")
def list_pr_summaries_endpoint():
    summaries = Repository.list_pr_summaries()
    return {"count": len(summaries), "pr_summaries": [s.model_dump() for s in summaries]}

@router.get("/services")
def list_services_endpoint():
    services = get_services_catalog()
    return {"count": len(services), "services": services}

@router.get("/health")
def health_endpoint():
    return {
        "status": "healthy",
        "service": "PulseOps Agent",
        "llm_mode": settings.llm_mode,
        "default_model": settings.openrouter_model if settings.llm_mode == "openrouter" else settings.openai_model,
        "database": str(settings.db_path)
    }
