from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class MessageModel(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str

class ToolTraceModel(BaseModel):
    id: str
    conversation_id: str
    step: int
    tool_name: str
    args: Dict[str, Any]
    result: Any
    ok: bool
    created_at: str

class TicketDraftModel(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    labels: List[str]
    team: str
    source_conversation_id: Optional[str] = None
    created_at: str

class PRSummaryModel(BaseModel):
    id: str
    pr_number: int
    summary: Dict[str, Any]
    source_conversation_id: Optional[str] = None
    created_at: str

class ConversationDetail(BaseModel):
    id: str
    created_at: str
    user_label: Optional[str] = None
    messages: List[MessageModel] = []
    traces: List[ToolTraceModel] = []
