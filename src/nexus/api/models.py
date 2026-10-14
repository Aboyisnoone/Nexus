from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
from nexus.core.evaluation.evaluator import EvaluationReport
from nexus.core.domain.memory import MemoryItem
from nexus.core.trace.models import DecisionTrace

class RunRequest(BaseModel):
    # Empty for now, mode and replay_of are query params
    pass

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

class RunResponse(BaseModel):
    run_id: str
    scenario_id: str
    mode: Literal["LIVE", "REPLAY"]
    agent_version: Optional[str] = None
    status: str
    evaluation: Optional[EvaluationReport] = None
    error: Optional[str] = None

class TraceResponse(BaseModel):
    trace: DecisionTrace

class MemoryResponse(BaseModel):
    memories: List[MemoryItem]

