from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, ForeignKey, MetaData, UniqueConstraint, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

class Base(DeclarativeBase):
    metadata = metadata

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

class ScenarioModel(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE)

class RunModel(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), index=True)
    agent_version: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)
    replay_of_run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("runs.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String)
    metrics_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)

class DecisionTraceModel(Base):
    __tablename__ = "decision_traces"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    step_name: Mapped[str] = mapped_column(String)
    trace_data_json: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE)

class MemoryModel(Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    context_id: Mapped[str] = mapped_column(String, index=True)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, default=1)
    previous_version_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    simulated_time_iso: Mapped[str] = mapped_column(String)
    evidence_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON_TYPE)
    contradictions_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON_TYPE, default=list)
    confirmation_event_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)

class LlmRecordingModel(Base):
    __tablename__ = "llm_recordings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    call_index: Mapped[int] = mapped_column(Integer)
    prompt_hash: Mapped[str] = mapped_column(String)
    prompt_json: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE)
    response_json: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE)

    __table_args__ = (
        UniqueConstraint("run_id", "call_index", name="uq_llm_recording_run_call"),
    )
