from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class SessionEvent(BaseModel):
    type: str
    timestamp: float
    data: Dict

class SessionData(BaseModel):
    session_id: str
    prompt: Optional[str] = None
    events: List[SessionEvent] = []
    compact_reasoning: Optional[str] = None

class DecisionRecord(BaseModel):
    commit_hash: str
    summary: str
    why: str
    alternatives_rejected: List[str]
    constraints: List[str]
    symbols: List[str]
    files: List[str]

class DistillContext(BaseModel):
    commit_hash: str
    diff: str
    symbols: List[str]
    files: List[str]
    sessions: List[SessionData]
    existing_decisions: List[DecisionRecord] = []
