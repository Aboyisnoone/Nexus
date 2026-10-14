import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from nexus.core.domain.scenario import Scenario
from nexus.core.scenario_loader import load_scenario
from nexus.core.persistence.repository import NexusRepository
from nexus.core.runner.pipeline import DecisionPipeline, PipelineRunResult
from nexus.core.runner.llm import LLMClient
from nexus.core.evaluation.evaluator import EvaluationReport, evaluate, EvaluationStatus
from nexus.core.simulation.models import SimulationResult
from nexus.core.evaluation.regression import compare_evaluations, SuiteComparisonSummary, ComparisonStatus, ScenarioComparison

class SuiteResult(BaseModel):
    scenario_id: str
    run_id: str
    status: str
    total_assertions: int
    passed_assertions: int
    failed_assertions: int
    failure_code: Optional[str] = None
    error_message: Optional[str] = None

class SuiteSummary(BaseModel):
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    error_scenarios: int
    results: List[SuiteResult]

class CoreSuiteRunner:
    def __init__(self, repo: NexusRepository, llm_client: LLMClient, scenarios_dir: str = "scenarios/core_10"):
        self.repo = repo
        self.llm_client = llm_client
        self.scenarios_dir = scenarios_dir
        self.pipeline = DecisionPipeline(repo, llm_client)

    def discover_scenarios(self) -> List[Scenario]:
        scenarios = []
        if not os.path.exists(self.scenarios_dir):
            return scenarios
            
        for filename in sorted(os.listdir(self.scenarios_dir)):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(self.scenarios_dir, filename)
                scenario = load_scenario(filepath)
                scenarios.append(scenario)
        return scenarios

    def evaluate_run(self, scenario: Scenario, run_result: PipelineRunResult) -> EvaluationReport:
        if run_result.evaluation_report:
            return run_result.evaluation_report
        # Fallback if expected_evaluation was empty
        from nexus.core.evaluation.evaluator import EvaluationReport, EvaluationStatus
        return EvaluationReport(status=EvaluationStatus.PASS, total=0, passed=0, failed=0, assertions=())

    def run_suite_live(self, agent_version: str = "v0.1") -> SuiteSummary:
        return self._run_suite("LIVE", agent_version=agent_version)

    def run_suite_replay(self, live_run_ids: Dict[str, str]) -> SuiteSummary:
        return self._run_suite("REPLAY", live_run_ids=live_run_ids)

    def _run_suite(self, mode: str, agent_version: str = "v0.1", live_run_ids: Dict[str, str] = None) -> SuiteSummary:
        scenarios = self.discover_scenarios()
        results = []
        passed, failed, errors = 0, 0, 0
        
        for scenario in scenarios:
            self.repo.save_scenario(scenario)
            run_id = None
            error_message = None
            failure_code = None
            report = None
            
            try:
                if mode == "LIVE":
                    run_result = self.pipeline.run_live(scenario, agent_version)
                else:
                    if scenario.scenario_id not in live_run_ids:
                        raise ValueError(f"Missing live run ID to replay for {scenario.scenario_id}")
                    run_result = self.pipeline.run_replay(live_run_ids[scenario.scenario_id])
                
                run_id = run_result.run_id
                report = self.evaluate_run(scenario, run_result)
                
                for step in run_result.trace.steps:
                    if step.step_type == "FAILURE":
                        failure_code = step.error_code
                        
            except Exception as e:
                error_message = str(e)
                report = EvaluationReport(
                    status=EvaluationStatus.ERROR,
                    total=len(scenario.expected_evaluation.assertions),
                    passed=0,
                    failed=len(scenario.expected_evaluation.assertions),
                    assertions=()
                )
                
            if report:
                if report.status == EvaluationStatus.PASS:
                    passed += 1
                elif report.status == EvaluationStatus.FAIL:
                    failed += 1
                else:
                    errors += 1
                    
                results.append(SuiteResult(
                    scenario_id=scenario.scenario_id,
                    run_id=run_id or "UNKNOWN",
                    status=report.status.value,
                    total_assertions=report.total,
                    passed_assertions=report.passed,
                    failed_assertions=report.failed,
                    failure_code=failure_code,
                    error_message=error_message
                ))
                
        return SuiteSummary(
            total_scenarios=len(scenarios),
            passed_scenarios=passed,
            failed_scenarios=failed,
            error_scenarios=errors,
            results=results
        )

    def compare_suite(self, baseline_version: str, candidate_version: str) -> SuiteComparisonSummary:
        scenarios = self.discover_scenarios()
        results = []
        
        comparable = 0
        unchanged = 0
        improved = 0
        regressions = 0
        incompatible = 0
        errors = 0
        
        for scenario in scenarios:
            self.repo.save_scenario(scenario)
            # 1. Find live baseline run
            baseline_run = self.repo.get_latest_live_run(scenario.scenario_id, baseline_version)
            if not baseline_run:
                results.append(ScenarioComparison(
                    scenario_id=scenario.scenario_id,
                    status=ComparisonStatus.ERROR,
                    baseline_version=baseline_version,
                    candidate_version=candidate_version,
                    error_message=f"No LIVE baseline run found for version {baseline_version}"
                ))
                errors += 1
                continue
                
            baseline_run_id = baseline_run.id
            
            try:
                # 2. Replay for baseline
                baseline_result = self.pipeline.run_replay(baseline_run_id, override_agent_version=baseline_version)
                baseline_report = self.evaluate_run(scenario, baseline_result)
                
                # 3. Replay for candidate
                candidate_result = self.pipeline.run_replay(baseline_run_id, override_agent_version=candidate_version)
                candidate_report = self.evaluate_run(scenario, candidate_result)
                
                b_error = baseline_result.simulation_result.error if baseline_result.simulation_result else None
                c_error = candidate_result.simulation_result.error if candidate_result.simulation_result else None
                
                comparison = compare_evaluations(
                    scenario=scenario,
                    baseline_version=baseline_version,
                    candidate_version=candidate_version,
                    baseline_run_id=baseline_result.run_id,
                    candidate_run_id=candidate_result.run_id,
                    baseline_report=baseline_report,
                    candidate_report=candidate_report,
                    baseline_error=b_error,
                    candidate_error=c_error
                )
                
                results.append(comparison)
                
                if comparison.status != ComparisonStatus.INCOMPATIBLE_INPUT and comparison.status != ComparisonStatus.ERROR:
                    comparable += 1
                    
                if comparison.status == ComparisonStatus.UNCHANGED:
                    unchanged += 1
                elif comparison.status == ComparisonStatus.REGRESSION:
                    regressions += 1
                elif comparison.status == ComparisonStatus.IMPROVEMENT:
                    improved += 1
                elif comparison.status == ComparisonStatus.INCOMPATIBLE_INPUT:
                    incompatible += 1
                elif comparison.status == ComparisonStatus.ERROR:
                    errors += 1
                
            except Exception as e:
                results.append(ScenarioComparison(
                    scenario_id=scenario.scenario_id,
                    status=ComparisonStatus.ERROR,
                    baseline_version=baseline_version,
                    candidate_version=candidate_version,
                    error_message=str(e)
                ))
                errors += 1
                
        return SuiteComparisonSummary(
            total_scenarios=len(scenarios),
            comparable=comparable,
            unchanged=unchanged,
            improved=improved,
            regressions=regressions,
            incompatible=incompatible,
            errors=errors,
            results=results
        )
