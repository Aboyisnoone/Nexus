from typing import Any
from .base import FrozenBaseModel

class Event(FrozenBaseModel):
    actor: str
    intent: str
    payload: dict[str, Any] | None = None
