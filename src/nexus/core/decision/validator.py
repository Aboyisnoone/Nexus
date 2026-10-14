from enum import Enum
from typing import Tuple, Optional, Any, Dict
from pydantic import ValidationError, TypeAdapter, Field
from nexus.core.domain.base import FrozenBaseModel
from .actions import AgentAction, ActionType

class ValidationErrorCode(str, Enum):
    ERR_LLM_SCHEMA = "ERR_LLM_SCHEMA"
    ERR_INVALID_ACTION = "ERR_INVALID_ACTION"
    ERR_POLICY_VIOLATION = "ERR_POLICY_VIOLATION"

class ValidationErrorDetail(FrozenBaseModel):
    code: ValidationErrorCode
    field: Optional[str] = None
    detail: str

class ValidationResult(FrozenBaseModel):
    valid: bool
    errors: Tuple[ValidationErrorDetail, ...] = Field(default_factory=tuple)

class PolicyContext(FrozenBaseModel):
    valid_candidate_ids: Tuple[str, ...]
    authorized_templates: Tuple[str, ...]
    authorized_public_reasons: Tuple[str, ...]

class ValidatedAction(FrozenBaseModel):
    """A wrapper guaranteeing the contained action passed strict policy validation."""
    action: AgentAction

_action_adapter = TypeAdapter(AgentAction)

def validate_action(raw_json: Dict[str, Any], context: PolicyContext) -> Tuple[Optional[AgentAction], ValidationResult]:
    # Layer 1: Schema Validation
    try:
        action = _action_adapter.validate_python(raw_json)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = ".".join(str(l) for l in err["loc"]) if err["loc"] else "root"
            errors.append(ValidationErrorDetail(
                code=ValidationErrorCode.ERR_LLM_SCHEMA,
                field=loc,
                detail=err["msg"]
            ))
        return None, ValidationResult(valid=False, errors=tuple(errors))
        
    # Layer 2: Deterministic Policy Validation
    errors = []
    
    if action.action_type == ActionType.PROPOSE_TIMES:
        for opt in action.ranked_options:
            if opt not in context.valid_candidate_ids:
                errors.append(ValidationErrorDetail(
                    code=ValidationErrorCode.ERR_INVALID_ACTION,
                    field="ranked_options",
                    detail=f"Option '{opt}' is not a valid candidate ID."
                ))
                
        if action.communication.template not in context.authorized_templates:
            errors.append(ValidationErrorDetail(
                code=ValidationErrorCode.ERR_POLICY_VIOLATION,
                field="communication.template",
                detail=f"Template '{action.communication.template}' is not authorized."
            ))
            
    elif action.action_type == ActionType.DECLINE:
        if action.public_reason not in context.authorized_public_reasons:
            errors.append(ValidationErrorDetail(
                code=ValidationErrorCode.ERR_POLICY_VIOLATION,
                field="public_reason",
                detail=f"Public reason '{action.public_reason}' is not authorized."
            ))
            
        if action.communication.template not in context.authorized_templates:
            errors.append(ValidationErrorDetail(
                code=ValidationErrorCode.ERR_POLICY_VIOLATION,
                field="communication.template",
                detail=f"Template '{action.communication.template}' is not authorized."
            ))

    if errors:
        return action, ValidationResult(valid=False, errors=tuple(errors))
        
    return action, ValidationResult(valid=True)

def validate_and_wrap_action(raw_json: Dict[str, Any], context: PolicyContext) -> Tuple[Optional[ValidatedAction], ValidationResult]:
    action, result = validate_action(raw_json, context)
    if result.valid and action is not None:
        return ValidatedAction(action=action), result
    return None, result
