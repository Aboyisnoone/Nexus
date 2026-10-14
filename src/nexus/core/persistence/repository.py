from sqlalchemy.orm import Session
from sqlalchemy import select, asc
from typing import Optional, List, Dict, Any
from pydantic import TypeAdapter

from .models import (
    ScenarioModel,
    RunModel,
    DecisionTraceModel,
    MemoryModel,
    LlmRecordingModel,
)

from nexus.core.domain.scenario import Scenario
from nexus.core.domain.memory import MemoryItem
from nexus.core.trace.models import DecisionTrace, TraceStep, TraceMetadata

class NexusRepository:
    def __init__(self, session: Session):
        self.session = session
        
    def save_scenario(self, scenario: Scenario):
        model = ScenarioModel(
            id=scenario.scenario_id,
            payload_json=scenario.model_dump(mode="json")
        )
        self.session.merge(model)
        self.session.commit()
        
    def load_scenario(self, scenario_id: str) -> Optional[Scenario]:
        model = self.session.execute(select(ScenarioModel).where(ScenarioModel.id == scenario_id)).scalar_one_or_none()
        if model:
            return Scenario.model_validate(model.payload_json)
        return None
        
    def save_run(self, run_id: str, scenario_id: str, agent_version: str, mode: str, status: str, replay_of_run_id: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None):
        model = RunModel(
            id=run_id,
            scenario_id=scenario_id,
            agent_version=agent_version,
            mode=mode,
            replay_of_run_id=replay_of_run_id,
            status=status,
            metrics_json=metrics
        )
        self.session.merge(model)
        self.session.commit()

    def get_latest_live_run(self, scenario_id: str, agent_version: str):
        from sqlalchemy import select
        from nexus.core.persistence.models import RunModel
        return self.session.execute(
            select(RunModel)
            .where(RunModel.scenario_id == scenario_id)
            .where(RunModel.agent_version == agent_version)
            .where(RunModel.mode == "LIVE")
        ).scalars().first()

    def get_run(self, run_id: str) -> Optional[RunModel]:
        return self.session.execute(select(RunModel).where(RunModel.id == run_id)).scalar_one_or_none()

    def save_decision_trace(self, trace: DecisionTrace):
        run_id = trace.metadata.trace_id
        for step in trace.steps:
            model = DecisionTraceModel(
                id=f"{run_id}_{step.step_index}",
                run_id=run_id,
                step_name=step.step_type.value,
                trace_data_json=step.model_dump(mode="json")
            )
            self.session.add(model)
        self.session.commit()

    def load_decision_trace(self, run_id: str) -> Optional[DecisionTrace]:
        run = self.get_run(run_id)
        if not run:
            return None
            
        models = self.session.execute(
            select(DecisionTraceModel)
            .where(DecisionTraceModel.run_id == run_id)
        ).scalars().all()
        
        if not models:
            return None
            
        # Reconstruct TraceMetadata from run
        metadata = TraceMetadata(
            trace_id=run.id,
            scenario_id=run.scenario_id,
            agent_version=run.agent_version
        )
        
        # Sort models by step_index embedded in JSONB, or just in Python
        # trace_data_json contains 'step_index'
        sorted_models = sorted(models, key=lambda m: m.trace_data_json.get("step_index", 0))
        
        adapter = TypeAdapter(TraceStep)
        steps = tuple(adapter.validate_python(m.trace_data_json) for m in sorted_models)
        
        return DecisionTrace(metadata=metadata, steps=steps)
        
    def save_memory(self, memory: MemoryItem):
        model = MemoryModel(
            id=memory.id,
            context_id=memory.context_id,
            key=memory.key,
            value=memory.value,
            state=memory.state.value if hasattr(memory.state, "value") else memory.state,
            version=memory.version,
            previous_version_id=memory.previous_version_id,
            simulated_time_iso=memory.simulated_time.isoformat(),
            evidence_json=[e.model_dump(mode="json") for e in memory.evidence],
            contradictions_json=[c.model_dump(mode="json") for c in memory.contradictions],
            confirmation_event_json=memory.confirmation_event.model_dump(mode="json") if memory.confirmation_event else None
        )
        self.session.merge(model)
        self.session.commit()
        
    def load_memories(self, context_id: str) -> List[MemoryItem]:
        models = self.session.execute(
            select(MemoryModel)
            .where(MemoryModel.context_id == context_id)
        ).scalars().all()
        
        from datetime import datetime
        return [
            MemoryItem.model_validate({
                "id": m.id,
                "context_id": m.context_id,
                "key": m.key,
                "value": m.value,
                "state": m.state,
                "version": m.version,
                "previous_version_id": m.previous_version_id,
                "simulated_time": datetime.fromisoformat(m.simulated_time_iso),
                "evidence": m.evidence_json,
                "contradictions": m.contradictions_json,
                "confirmation_event": m.confirmation_event_json
            }) for m in models
        ]

    def save_llm_recording(self, run_id: str, call_index: int, prompt_hash: str, prompt_json: Dict[str, Any], response_json: Dict[str, Any]):
        recording_id = f"{run_id}_{call_index}"
        model = LlmRecordingModel(
            id=recording_id,
            run_id=run_id,
            call_index=call_index,
            prompt_hash=prompt_hash,
            prompt_json=prompt_json,
            response_json=response_json
        )
        self.session.add(model)
        self.session.commit()
        
    def load_llm_recording(self, run_id: str, call_index: int) -> Optional[Dict[str, Any]]:
        model = self.session.execute(
            select(LlmRecordingModel)
            .where(LlmRecordingModel.run_id == run_id)
            .where(LlmRecordingModel.call_index == call_index)
        ).scalar_one_or_none()
        
        if model:
            return {
                "id": model.id,
                "run_id": model.run_id,
                "call_index": model.call_index,
                "prompt_hash": model.prompt_hash,
                "prompt_json": model.prompt_json,
                "response_json": model.response_json,
            }
        return None




