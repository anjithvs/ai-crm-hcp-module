from typing import List, Optional

from pydantic import BaseModel


class InteractionSchema(BaseModel):
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: List[str] = []
    topics_discussed: Optional[str] = None
    materials_shared: List[str] = []
    samples_distributed: List[dict] = []
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    compliance_flag: Optional[str] = None
    logged: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    interaction: InteractionSchema