from enum import Enum
from typing import Tuple, Any, Optional, Dict
from nexus.core.domain.base import FrozenBaseModel
from nexus.core.domain.evaluation import Assertion
from nexus.core.domain.scenario import Scenario
from nexus.core.simulation.models import SimulationResult
from nexus.core.scheduling.models import CandidateSlot
from nexus.core.decision.actions import ActionType

class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"

class AssertionResult(FrozenBaseModel):
    assertion: Assertion
    passed: bool
    actual: Optional[Any] = None
    error: Optional[str] = None

class EvaluationReport(FrozenBaseModel):
    status: EvaluationStatus
    total: int
    passed: int
    failed: int
    assertions: Tuple[AssertionResult, ...]

def evaluate(
    scenario: Scenario, 
    simulation_result: SimulationResult,
    candidate_slots: Optional[Dict[str, CandidateSlot]] = None
) -> EvaluationReport:
    results = []
    
    action_record = simulation_result.action_record
    action = action_record.action if action_record else None
    
    for assertion in scenario.expected_evaluation.assertions:
        try:
            if assertion.type == "action_type_equals":
                actual = action.action_type if action else None
                passed = actual == assertion.expected
                results.append(AssertionResult(assertion=assertion, passed=passed, actual=actual))
                
            elif assertion.type == "selected_option_equals":
                if not action or action.action_type != ActionType.PROPOSE_TIMES:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="No PROPOSE_TIMES action taken"))
                    continue
                actual = getattr(action, "selected_option", None)
                passed = actual == assertion.expected
                results.append(AssertionResult(assertion=assertion, passed=passed, actual=actual))
                
            elif assertion.type == "ranked_options_equals":
                if not action or action.action_type != ActionType.PROPOSE_TIMES:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="No PROPOSE_TIMES action taken"))
                    continue
                actual = getattr(action, "ranked_options", None)
                passed = actual == assertion.expected
                results.append(AssertionResult(assertion=assertion, passed=passed, actual=actual))
                
            elif assertion.type == "public_reason_equals":
                if not action or action.action_type != ActionType.DECLINE:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="No DECLINE action taken"))
                    continue
                actual = getattr(action, "public_reason", None)
                passed = actual == assertion.expected
                results.append(AssertionResult(assertion=assertion, passed=passed, actual=actual))
                
            elif assertion.type == "communication_template_equals":
                if not action:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="No action taken"))
                    continue
                actual = getattr(action.communication, "template", None) if getattr(action, "communication", None) else None
                passed = actual == assertion.expected
                results.append(AssertionResult(assertion=assertion, passed=passed, actual=actual))
                
            elif assertion.type == "no_calendar_overlap":
                if not action or action.action_type != ActionType.PROPOSE_TIMES:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="Action was not PROPOSE_TIMES"))
                    continue
                
                selected_option = getattr(action, "selected_option", None)
                if not selected_option:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="No selected option present"))
                    continue
                    
                if not candidate_slots or selected_option not in candidate_slots:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="ERR_EVALUATION_FAILURE: Missing CandidateSlot temporal data to evaluate overlap"))
                    continue
                    
                slot = candidate_slots[selected_option]
                calendar = simulation_result.state_before.calendar
                
                has_overlap = False
                for event in calendar:
                    if slot.start < event.end and event.start < slot.end:
                        has_overlap = True
                        break
                        
                results.append(AssertionResult(assertion=assertion, passed=not has_overlap, actual="Overlap" if has_overlap else "No Overlap"))
                
            elif assertion.type == "calendar_unchanged":
                before = simulation_result.state_before.calendar
                after = simulation_result.state_after.calendar if simulation_result.state_after else None
                
                if after is None:
                    results.append(AssertionResult(assertion=assertion, passed=False, error="No state_after present"))
                    continue
                    
                passed = before == after
                results.append(AssertionResult(assertion=assertion, passed=passed, actual="Unchanged" if passed else "Changed"))
                
            else:
                results.append(AssertionResult(assertion=assertion, passed=False, error=f"ERR_EVALUATION_FAILURE: Unsupported assertion type {assertion.type}"))
                
        except Exception as e:
            results.append(AssertionResult(assertion=assertion, passed=False, error=f"ERR_EVALUATION_FAILURE: {str(e)}"))

    total = len(results)
    
    # Calculate statuses
    has_errors = any(r.error and "ERR_EVALUATION_FAILURE" in r.error for r in results)
    
    if has_errors:
        status = EvaluationStatus.ERROR
    else:
        has_failures = any(not r.passed for r in results)
        status = EvaluationStatus.FAIL if has_failures else EvaluationStatus.PASS
        
    passed_count = sum(1 for r in results if r.passed and not (r.error and "ERR_EVALUATION_FAILURE" in r.error))
    failed_count = total - passed_count
    
    return EvaluationReport(
        status=status,
        total=total,
        passed=passed_count,
        failed=failed_count,
        assertions=tuple(results)
    )
