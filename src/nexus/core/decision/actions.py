from enum import Enum
from typing import Literal, Optional, Tuple, Annotated, Union
from pydantic import Field, model_validator, ConfigDict
from nexus.core.domain.base import FrozenBaseModel

class ActionType(str, Enum):
    PROPOSE_TIMES = "PROPOSE_TIMES"
    DECLINE = "DECLINE"

class CommunicationTemplate(str, Enum):
    PROPOSE_SELECTED_SLOTS = "PROPOSE_SELECTED_SLOTS"
    UNAVAILABLE_PROPOSE_ALTERNATIVES = "UNAVAILABLE_PROPOSE_ALTERNATIVES"

class PublicReason(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"

class PreferenceBasis(str, Enum):
    AFTERNOON_PREFERRED = "AFTERNOON_PREFERRED"
    CLIENT_PRIORITY = "CLIENT_PRIORITY"
    PRIVATE_CONFLICT = "PRIVATE_CONFLICT"

class Communication(FrozenBaseModel):
    model_config = ConfigDict(extra='forbid')
    template: CommunicationTemplate

class BaseAction(FrozenBaseModel):
    model_config = ConfigDict(extra='forbid')
    preference_basis: Tuple[PreferenceBasis, ...] = Field(default_factory=tuple)

class ProposeTimesAction(BaseAction):
    action_type: Literal[ActionType.PROPOSE_TIMES]
    ranked_options: Tuple[str, ...]
    selected_option: str
    communication: Communication
    
    @model_validator(mode='after')
    def validate_proposal(self) -> 'ProposeTimesAction':
        if not self.ranked_options:
            raise ValueError("ranked_options must contain one or more option IDs")
        if len(set(self.ranked_options)) != len(self.ranked_options):
            raise ValueError("ranked_options must contain no duplicates")
        if self.selected_option not in self.ranked_options:
            raise ValueError("selected_option must be one of ranked_options")
        if self.communication.template != CommunicationTemplate.PROPOSE_SELECTED_SLOTS:
            raise ValueError("communication template must be an approved proposal template")
        return self

class DeclineAction(BaseAction):
    action_type: Literal[ActionType.DECLINE]
    ranked_options: Tuple[str, ...] = Field(default_factory=tuple)
    selected_option: Optional[str] = None
    public_reason: PublicReason
    communication: Communication
    
    @model_validator(mode='after')
    def validate_decline(self) -> 'DeclineAction':
        if self.ranked_options:
            raise ValueError("ranked_options MUST be empty")
        if self.selected_option is not None:
            raise ValueError("selected_option MUST be null")
        if self.communication.template != CommunicationTemplate.UNAVAILABLE_PROPOSE_ALTERNATIVES:
            raise ValueError("communication template must be an approved decline template")
        return self

AgentAction = Annotated[Union[ProposeTimesAction, DeclineAction], Field(discriminator='action_type')]
