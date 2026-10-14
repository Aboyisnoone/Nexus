import pytest
from nexus.core.decision import (
    validate_action,
    PolicyContext,
    ValidationErrorCode,
    ActionType,
    CommunicationTemplate,
    PublicReason,
    PreferenceBasis
)

@pytest.fixture
def policy_ctx():
    return PolicyContext(
        valid_candidate_ids=("slot_A", "slot_B", "slot_C"),
        authorized_templates=("PROPOSE_SELECTED_SLOTS", "UNAVAILABLE_PROPOSE_ALTERNATIVES"),
        authorized_public_reasons=("UNAVAILABLE",)
    )

def test_valid_propose_times_accepted(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_B", "slot_A"],
        "selected_option": "slot_B",
        "preference_basis": ["AFTERNOON_PREFERRED"],
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    action, result = validate_action(raw, policy_ctx)
    assert result.valid is True
    assert action is not None
    assert action.action_type == ActionType.PROPOSE_TIMES

def test_valid_decline_accepted(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "public_reason": "UNAVAILABLE",
        "preference_basis": ["PRIVATE_CONFLICT"],
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    action, result = validate_action(raw, policy_ctx)
    assert result.valid is True
    assert action is not None
    assert action.action_type == ActionType.DECLINE

def test_unknown_action_type_rejected(policy_ctx):
    raw = {"action_type": "HACK_THE_SYSTEM"}
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False
    assert result.errors[0].code == ValidationErrorCode.ERR_LLM_SCHEMA

def test_missing_required_field_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "selected_option": "slot_B"
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False
    assert any("ranked_options" in err.field for err in result.errors)

def test_wrong_field_type_rejected(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "public_reason": 123,
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_unknown_field_rejected(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "public_reason": "UNAVAILABLE",
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"},
        "hacked_field": True
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_numerical_confidence_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_A"],
        "selected_option": "slot_A",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"},
        "confidence": 0.99
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_invalid_public_reason_rejected(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "public_reason": "I_AM_TIRED",
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False
    assert result.errors[0].code == ValidationErrorCode.ERR_LLM_SCHEMA

def test_invalid_communication_template_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_A"],
        "selected_option": "slot_A",
        "communication": {"template": "MAKE_UP_A_TEMPLATE"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_invalid_discriminated_union_combination_rejected(policy_ctx):
    # Try passing propose fields into decline
    raw = {
        "action_type": "DECLINE",
        "ranked_options": ["slot_A"],
        "selected_option": "slot_A"
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_empty_ranking_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": [],
        "selected_option": "slot_A",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_duplicate_ranking_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_A", "slot_A"],
        "selected_option": "slot_A",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_selected_option_missing_from_ranking_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_A"],
        "selected_option": "slot_B",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_nonexistent_candidate_id_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_hallucinated"],
        "selected_option": "slot_hallucinated",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False
    assert result.errors[0].code == ValidationErrorCode.ERR_INVALID_ACTION

def test_proposal_template_mismatch_rejected(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_A"],
        "selected_option": "slot_A",
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False
    assert result.errors[0].code == ValidationErrorCode.ERR_LLM_SCHEMA

def test_decline_with_selected_option_rejected(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "selected_option": "slot_A",
        "public_reason": "UNAVAILABLE",
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False

def test_privacy_no_free_form_field(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "public_reason": "UNAVAILABLE",
        "communication": {
            "template": "UNAVAILABLE_PROPOSE_ALTERNATIVES",
            "message": "I am having therapy."
        }
    }
    _, result = validate_action(raw, policy_ctx)
    assert result.valid is False
    assert any("communication.message" in err.field or "communication" in err.field for err in result.errors)

def test_unauthorized_policy_reason(policy_ctx):
    # Schema might accept it if we added a new enum later, but policy rejects it.
    # To test policy layer, we must pass schema layer.
    # We will redefine context to NOT authorize UNAVAILABLE.
    strict_ctx = PolicyContext(
        valid_candidate_ids=(),
        authorized_templates=("UNAVAILABLE_PROPOSE_ALTERNATIVES",),
        authorized_public_reasons=()
    )
    raw = {
        "action_type": "DECLINE",
        "public_reason": "UNAVAILABLE",
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    action, result = validate_action(raw, strict_ctx)
    assert result.valid is False
    assert result.errors[0].code == ValidationErrorCode.ERR_POLICY_VIOLATION
