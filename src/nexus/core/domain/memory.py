from enum import Enum
from typing import Tuple, Optional
from datetime import datetime
from pydantic import Field
from .base import FrozenBaseModel

class MemoryState(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    CONFIRMED = "CONFIRMED"

class Evidence(FrozenBaseModel):
    source_run_id: str
    detail: Optional[str] = None

class ConfirmationEvent(FrozenBaseModel):
    memory_id: str
    context_id: str
    source: str
    simulated_time: datetime
    evidence: Evidence

class Contradiction(FrozenBaseModel):
    observation_evidence: Evidence
    simulated_time: datetime
    detail: str

class MemoryItem(FrozenBaseModel):
    id: str
    context_id: str
    key: str
    value: str
    state: MemoryState
    simulated_time: datetime
    evidence: Tuple[Evidence, ...] = Field(default_factory=tuple)
    version: int = 1
    previous_version_id: Optional[str] = None
    contradictions: Tuple[Contradiction, ...] = Field(default_factory=tuple)
    confirmation_event: Optional[ConfirmationEvent] = None

class MemoryUpdateType(str, Enum):
    OBSERVE = "OBSERVE"
    INFER = "INFER"
    CONFIRM = "CONFIRM"
    RECORD_CONTRADICTION = "RECORD_CONTRADICTION"

class MemoryUpdate(FrozenBaseModel):
    update_type: MemoryUpdateType
    memory_id: Optional[str] = None # For updates to existing memory
    context_id: str
    key: str
    value: str
    simulated_time: datetime
    evidence: Evidence
    source: Optional[str] = None # Used for confirmation
    detail: Optional[str] = None # Used for contradiction
