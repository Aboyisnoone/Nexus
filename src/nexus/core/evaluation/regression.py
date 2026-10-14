from enum import Enum
from typing import Optional, List, Tuple, Any, Dict
from pydantic import BaseModel
from nexus.core.evaluation.evaluator import EvaluationReport, EvaluationStatus
from nexus.core.domain.scenario import Scenario

class ComparisonStatus(str, Enum):
    COMPARABLE = "COMPARABLE"
    UNCHANGED = "UNCHANGED"
    REGRESSION = "REGRESSION"
    IMPROVEMENT = "IMPROVEMENT"
    INCOMPATIBLE_INPUT = "INCOMPATIBLE_INPUT"
    ERROR = "ERROR"

class AssertionDifference(BaseModel):
    assertion_type: str
    expected_value: Any
    baseline_actual: Any
    candidate_actual: Any
    baseline_passed: bool
    candidate_passed: bool

class ScenarioComparison(BaseModel):
    scenario_id: str
    status: ComparisonStatus
    baseline_version: str
    candidate_version: str
    baseline_run_id: Optional[str] = None
    candidate_run_id: Optional[str] = None
    baseline_status: Optional[str] = None
    candidate_status: Optional[str] = None
    baseline_failure_code: Optional[str] = None
    candidate_failure_code: Optional[str] = None
    changed_assertions: Tuple[AssertionDifference, ...] = ()
    error_message: Optional[str] = None

class SuiteComparisonSummary(BaseModel):
    total_scenarios: int
    comparable: int
    unchanged: int
    improved: int
    regressions: int
    incompatible: int
    errors: int
    results: List[ScenarioComparison]

def compare_evaluations(
    scenario: Scenario,
    baseline_version: str,
    candidate_version: str,
    baseline_run_id: str,
    candidate_run_id: str,
    baseline_report: EvaluationReport,
    candidate_report: EvaluationReport,
    baseline_error: Optional[str] = None,
    candidate_error: Optional[str] = None
) -> ScenarioComparison:
    
    # 1. Check for infrastructure or input incompatibility errors
    if candidate_error == "ERR_REPLAY_INPUT_MISMATCH":
        return ScenarioComparison(
            scenario_id=scenario.scenario_id,
            status=ComparisonStatus.INCOMPATIBLE_INPUT,
            baseline_version=baseline_version,
            candidate_version=candidate_version,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            baseline_status=baseline_report.status.value,
            candidate_status=EvaluationStatus.ERROR.value,
            baseline_failure_code=baseline_error,
            candidate_failure_code=candidate_error
        )
    
    if baseline_error == "ERR_MISSING_RECORDING" or candidate_error == "ERR_MISSING_RECORDING":
        return ScenarioComparison(
            scenario_id=scenario.scenario_id,
            status=ComparisonStatus.ERROR,
            baseline_version=baseline_version,
            candidate_version=candidate_version,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            error_message="Missing recording for replay"
        )
        
    if baseline_report.status == EvaluationStatus.ERROR or candidate_report.status == EvaluationStatus.ERROR:
        # If there's an infrastructure error, it's an ERROR status, not necessarily a regression
        return ScenarioComparison(
            scenario_id=scenario.scenario_id,
            status=ComparisonStatus.ERROR,
            baseline_version=baseline_version,
            candidate_version=candidate_version,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            baseline_status=baseline_report.status.value,
            candidate_status=candidate_report.status.value,
            baseline_failure_code=baseline_error,
            candidate_failure_code=candidate_error,
            error_message="Evaluator returned ERROR"
        )

    # 2. Extract assertions deterministically
    baseline_assertions_dict = {i: a for i, a in enumerate(baseline_report.assertions)}
    candidate_assertions_dict = {i: a for i, a in enumerate(candidate_report.assertions)}
    
    changed_assertions = []
    
    # Compare matching indexes (scenario assertions are ordered)
    for i in range(len(scenario.expected_evaluation.assertions)):
        b_res = baseline_assertions_dict.get(i)
        c_res = candidate_assertions_dict.get(i)
        
        if b_res and c_res and b_res.passed != c_res.passed:
            expected_val = getattr(b_res.assertion, 'expected', None)
            changed_assertions.append(AssertionDifference(
                assertion_type=b_res.assertion.type,
                expected_value=expected_val,
                baseline_actual=b_res.actual,
                candidate_actual=c_res.actual,
                baseline_passed=b_res.passed,
                candidate_passed=c_res.passed
            ))
            
    # 3. Determine overall regression status based on EvaluationReport PASS/FAIL
    if baseline_report.status == EvaluationStatus.PASS and candidate_report.status == EvaluationStatus.PASS:
        status = ComparisonStatus.UNCHANGED
    elif baseline_report.status == EvaluationStatus.FAIL and candidate_report.status == EvaluationStatus.FAIL:
        status = ComparisonStatus.UNCHANGED
    elif baseline_report.status == EvaluationStatus.PASS and candidate_report.status == EvaluationStatus.FAIL:
        status = ComparisonStatus.REGRESSION
    elif baseline_report.status == EvaluationStatus.FAIL and candidate_report.status == EvaluationStatus.PASS:
        status = ComparisonStatus.IMPROVEMENT
    else:
        status = ComparisonStatus.ERROR
        
    return ScenarioComparison(
        scenario_id=scenario.scenario_id,
        status=status,
        baseline_version=baseline_version,
        candidate_version=candidate_version,
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        baseline_status=baseline_report.status.value,
        candidate_status=candidate_report.status.value,
        baseline_failure_code=baseline_error,
        candidate_failure_code=candidate_error,
        changed_assertions=tuple(changed_assertions)
    )
