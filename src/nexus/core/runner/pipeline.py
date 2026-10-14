from typing import Optional
from pydantic import BaseModel
from nexus.core.simulation.models import SimulationResult
from nexus.core.trace.models import DecisionTrace

from nexus.core.evaluation.evaluator import EvaluationReport
class PipelineRunResult(BaseModel):
    run_id: str
    simulation_result: SimulationResult
    trace: DecisionTrace
    evaluation_report: Optional[EvaluationReport] = None
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import uuid

from nexus.core.domain.scenario import Scenario
from nexus.core.simulation.models import SimulationState
from nexus.core.trace.builder import DecisionTraceBuilder
from nexus.core.trace.models import TraceMetadata, DecisionTrace
from nexus.core.decision.validator import validate_and_wrap_action, validate_action, PolicyContext, ValidatedAction
from nexus.core.simulation.simulator import apply_action
from nexus.core.scheduling.engine import generate_valid_candidates
from nexus.core.time import SimulatedClock
from nexus.core.persistence.repository import NexusRepository
from nexus.core.runner.llm import (
    LLMClient, 
    compute_prompt_hash, 
    ReplayRecordingNotFoundError, 
    ReplayInputMismatchError
)

class DecisionPipeline:
    def __init__(self, repo: NexusRepository, llm_client: Optional[LLMClient] = None):
        self.repo = repo
        self.llm_client = llm_client

    def run_live(self, scenario: Scenario, agent_version: str) -> PipelineRunResult:
        run_id = str(uuid.uuid4())
        sim_result, candidate_dict = self._run_internal(
            run_id=run_id,
            scenario=scenario,
            agent_version=agent_version,
            mode="LIVE",
            replay_of_run_id=None
        )
        trace = self.repo.load_decision_trace(run_id)
        
        evaluation_report = None
        if scenario.expected_evaluation:
            from nexus.core.evaluation.evaluator import evaluate
            evaluation_report = evaluate(scenario, sim_result, candidate_dict)
            
        return PipelineRunResult(run_id=run_id, simulation_result=sim_result, trace=trace, evaluation_report=evaluation_report)

    def run_replay(self, source_run_id: str, override_agent_version: str = None) -> PipelineRunResult:
        source_run = self.repo.get_run(source_run_id)
        if not source_run:
            raise ValueError(f"Source run {source_run_id} not found")
        
        scenario = self.repo.load_scenario(source_run.scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {source_run.scenario_id} for run {source_run_id} not found")

        run_id = str(uuid.uuid4())
        sim_result, candidate_dict = self._run_internal(
            run_id=run_id,
            scenario=scenario,
            agent_version=override_agent_version or source_run.agent_version,
            mode="REPLAY",
            replay_of_run_id=source_run_id
        )
        trace = self.repo.load_decision_trace(run_id)
        evaluation_report = None
        if scenario.expected_evaluation:
            from nexus.core.evaluation.evaluator import evaluate
            evaluation_report = evaluate(scenario, sim_result, candidate_dict)
        return PipelineRunResult(run_id=run_id, simulation_result=sim_result, trace=trace, evaluation_report=evaluation_report)

    def _run_internal(
        self,
        run_id: str,
        scenario: Scenario,
        agent_version: str,
        mode: str,
        replay_of_run_id: Optional[str]
    ):
        self.repo.save_run(
            run_id=run_id,
            scenario_id=scenario.scenario_id,
            agent_version=agent_version,
            mode=mode,
            status="RUNNING",
            replay_of_run_id=replay_of_run_id
        )

        trace_meta = TraceMetadata(trace_id=run_id, scenario_id=scenario.scenario_id, agent_version=agent_version)
        trace_builder = DecisionTraceBuilder(trace_meta)
        
        # Ensure scenario memory seeding is run-isolated to prevent cross-run pollution
        run_isolated_memory = []
        for mem in scenario.initial_state.memory:
            isolated_mem = mem.model_copy(update={
                "id": f"{run_id}_{mem.id}",
                "context_id": f"{run_id}_{mem.context_id}"
            })
            self.repo.save_memory(isolated_mem)
            run_isolated_memory.append(isolated_mem)
            
        from nexus.core.memory.service import MemoryService
        mem_service = MemoryService(self.repo)
        
        # Retrieve active memories for the relevant run-isolated contexts
        context_ids = {m.context_id for m in run_isolated_memory}
        retrieved_memories = []
        for ctx in sorted(context_ids):
            retrieved_memories.extend(mem_service.retrieve(ctx))
        retrieved_memories.sort(key=lambda m: (m.context_id, m.key, m.version, m.id))
        
        # Strip the run_id isolation prefix so the domain models remain structurally identical across replays
        clean_memories = []
        prefix = f"{run_id}_"
        for m in retrieved_memories:
            clean_id = m.id[len(prefix):] if m.id.startswith(prefix) else m.id
            clean_ctx = m.context_id[len(prefix):] if m.context_id.startswith(prefix) else m.context_id
            clean_memories.append(m.model_copy(update={"id": clean_id, "context_id": clean_ctx}))

        simulated_time = scenario.simulated_time
        state = SimulationState(
            simulated_time=simulated_time,
            calendar=scenario.initial_state.calendar,
            memory=tuple(clean_memories),
            action_history=()
        )
        
        try:
            trace_builder.record_state_before(simulated_time, state)
            trace_builder.record_memory(simulated_time, state.memory)

            from nexus.core.runner.adapter import ScenarioSchedulingAdapter, MissingSchedulingConstraintsError
            constraints = ScenarioSchedulingAdapter.extract_constraints(scenario)
            
            clock = SimulatedClock(simulated_time)
            candidates = generate_valid_candidates(clock, constraints, state.calendar)
            candidate_dict = {f"slot_{i}": c for i, c in enumerate(candidates)}
            
            # Serialize candidates and inject deterministic slot_ids for LLM tracking
            candidates_json = []
            candidate_ids = []
            for i, c in enumerate(candidates):
                c_json = c.model_dump(mode="json")
                slot_id = f"slot_{i}"
                c_json["slot_id"] = slot_id
                candidates_json.append(c_json)
                candidate_ids.append(slot_id)
                
            candidate_ids = tuple(candidate_ids)
            trace_builder.record_valid_options(simulated_time, candidates)

            from nexus.core.decision.prompt import PromptBuilder
            prompt = PromptBuilder.build_decision_prompt(
                scenario=scenario,
                simulated_time=simulated_time,
                candidates=candidates,
                memories=list(state.memory)
            )
            prompt_hash = compute_prompt_hash(prompt)
            
            call_index = 0

            response_json, model_id = self._obtain_llm_response(
                run_id=run_id,
                mode=mode,
                replay_of_run_id=replay_of_run_id,
                call_index=call_index,
                prompt=prompt,
                prompt_hash=prompt_hash
            )

            from nexus.core.runner.policy_adapter import ScenarioPolicyAdapter
            policy_context = ScenarioPolicyAdapter.extract_policy_context(scenario, candidate_ids)
            
            action, validation_result = validate_action(response_json, policy_context)
            
            if action is None: # ERR_LLM_SCHEMA
                err_code = validation_result.errors[0].code.value
                trace_builder.record_failure(simulated_time, err_code, "Schema validation failed")
                self._fail_run(run_id, trace_builder)
                return SimulationResult(status="FAILED", action_type=None, state_before=state, error=err_code), candidate_dict if "candidate_dict" in locals() else {}
                
            trace_builder.record_llm_action(simulated_time, action)
            trace_builder.record_validation(simulated_time, validation_result)

            if not validation_result.valid:
                err_code = validation_result.errors[0].code.value
                trace_builder.record_failure(simulated_time, err_code, "Policy validation failed")
                self._fail_run(run_id, trace_builder)
                return SimulationResult(status="FAILED", action_type=None, state_before=state, error=err_code), candidate_dict if "candidate_dict" in locals() else {}
                
            validated_action = ValidatedAction(action=action)
            sim_result = apply_action(state, validated_action)
            trace_builder.record_state_transition(simulated_time, sim_result)
            trace_builder.record_state_after(simulated_time, sim_result.state_after)

            self.repo.save_decision_trace(trace_builder.finalize())
            self._update_run_status(run_id, "COMPLETED")
            return sim_result, candidate_dict

        except ReplayRecordingNotFoundError as e:
            trace_builder.record_failure(simulated_time, "ERR_MISSING_RECORDING", str(e))
            self._fail_run(run_id, trace_builder)
            return SimulationResult(status="FAILED", action_type=None, state_before=state, error="ERR_MISSING_RECORDING"), {}
        except ReplayInputMismatchError as e:
            trace_builder.record_failure(simulated_time, "ERR_REPLAY_INPUT_MISMATCH", str(e))
            self._fail_run(run_id, trace_builder)
            return SimulationResult(status="FAILED", action_type=None, state_before=state, error="ERR_REPLAY_INPUT_MISMATCH"), {}
        except MissingSchedulingConstraintsError as e:
            trace_builder.record_failure(simulated_time, "ERR_MISSING_CONSTRAINTS", str(e))
            self._fail_run(run_id, trace_builder)
            return SimulationResult(status="FAILED", action_type=None, state_before=state, error="ERR_MISSING_CONSTRAINTS"), {}
        except Exception as e:
            trace_builder.record_failure(simulated_time, "ERR_SYSTEM", str(e))
            self._fail_run(run_id, trace_builder)
            return SimulationResult(status="FAILED", action_type=None, state_before=state, error="ERR_SYSTEM"), {}


    def _obtain_llm_response(
        self,
        run_id: str,
        mode: str,
        replay_of_run_id: Optional[str],
        call_index: int,
        prompt: Dict[str, Any],
        prompt_hash: str
    ) -> Tuple[Dict[str, Any], str]:
        
        if mode == "LIVE":
            if not self.llm_client:
                raise RuntimeError("LLMClient is required for LIVE mode")
            
            response_json, model_id = self.llm_client.generate(prompt)
            
            # Ensure the raw output is a dictionary to honor the recording schema
            if not isinstance(response_json, dict):
                response_json = {"_raw_unparseable_output": response_json}
            
            self.repo.save_llm_recording(
                run_id=run_id,
                call_index=call_index,
                prompt_hash=prompt_hash,
                prompt_json=prompt,
                response_json=response_json
            )
            return response_json, model_id
            
        elif mode == "REPLAY":
            if not replay_of_run_id:
                raise ValueError("REPLAY mode requires replay_of_run_id")
                
            recording = self.repo.load_llm_recording(replay_of_run_id, call_index)
            if not recording:
                raise ReplayRecordingNotFoundError(f"Missing LLM recording for run {replay_of_run_id} at call {call_index}")
                
            if recording["prompt_hash"] != prompt_hash:
                raise ReplayInputMismatchError(
                    f"Replay input hash {prompt_hash} does not match recorded hash {recording['prompt_hash']}"
                )
                
            # Copy the recording into the new run
            self.repo.save_llm_recording(
                run_id=run_id,
                call_index=call_index,
                prompt_hash=prompt_hash,
                prompt_json=prompt,
                response_json=recording["response_json"]
            )
            
            return recording["response_json"], "replay-model"
            
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _fail_run(self, run_id: str, trace_builder: DecisionTraceBuilder):
        self.repo.save_decision_trace(trace_builder.finalize())
        self._update_run_status(run_id, "FAILED")
        
    def _update_run_status(self, run_id: str, status: str):
        run = self.repo.get_run(run_id)
        if run:
            self.repo.save_run(
                run_id=run_id,
                scenario_id=run.scenario_id,
                agent_version=run.agent_version,
                mode=run.mode,
                status=status,
                replay_of_run_id=run.replay_of_run_id
            )








