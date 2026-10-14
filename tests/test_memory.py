import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nexus.core.persistence.models import Base
from nexus.core.persistence.repository import NexusRepository

from nexus.core.domain.memory import (
    MemoryItem, MemoryState, MemoryUpdate, MemoryUpdateType, Evidence
)
from nexus.core.memory.service import MemoryService, MemoryTransitionError

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def repo(session):
    return NexusRepository(session)

def test_observe_to_inferred(repo):
    service = MemoryService(repo)
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    
    # 1. OBSERVED memory can be created
    update1 = MemoryUpdate(
        update_type=MemoryUpdateType.OBSERVE,
        context_id="ctx_1",
        key="pref_time",
        value="morning",
        simulated_time=sim_time,
        evidence=Evidence(source_run_id="run_1")
    )
    service.apply_post_run_updates([update1])
    
    mems = service.retrieve("ctx_1")
    assert len(mems) == 1
    assert mems[0].state == MemoryState.OBSERVED
    assert mems[0].version == 1
    
    # 6. OBSERVED -> INFERRED works
    update2 = MemoryUpdate(
        update_type=MemoryUpdateType.INFER,
        memory_id=mems[0].id,
        context_id="ctx_1",
        key="pref_time",
        value="morning",
        simulated_time=sim_time,
        evidence=Evidence(source_run_id="run_2")
    )
    service.apply_post_run_updates([update2])
    
    mems = service.retrieve("ctx_1")
    assert len(mems) == 1
    assert mems[0].state == MemoryState.INFERRED
    assert mems[0].version == 2
    assert len(mems[0].evidence) == 2

def test_confirmation_rules(repo):
    service = MemoryService(repo)
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    
    upd = MemoryUpdate(
        update_type=MemoryUpdateType.INFER,
        context_id="ctx_2",
        key="pref",
        value="afternoon",
        simulated_time=sim_time,
        evidence=Evidence(source_run_id="run_1")
    )
    service.apply_post_run_updates([upd])
    mems = service.retrieve("ctx_2")
    mem_id = mems[0].id
    
    conf_upd = MemoryUpdate(
        update_type=MemoryUpdateType.CONFIRM,
        memory_id=mem_id,
        context_id="ctx_2",
        key="pref",
        value="afternoon",
        simulated_time=sim_time,
        evidence=Evidence(source_run_id="run_2", detail="User confirmed via chat"),
        source="user"
    )
    service.apply_post_run_updates([conf_upd])
    
    mems = service.retrieve("ctx_2")
    assert len(mems) == 1
    assert mems[0].state == MemoryState.CONFIRMED
    assert mems[0].confirmation_event is not None
    
    contra_upd = MemoryUpdate(
        update_type=MemoryUpdateType.RECORD_CONTRADICTION,
        memory_id=mems[0].id,
        context_id="ctx_2",
        key="pref",
        value="morning",
        simulated_time=sim_time,
        evidence=Evidence(source_run_id="run_3"),
        detail="User scheduled a morning meeting"
    )
    service.apply_post_run_updates([contra_upd])
    
    mems = service.retrieve("ctx_2")
    assert len(mems) == 1
    assert mems[0].state == MemoryState.CONFIRMED
    assert mems[0].value == "afternoon"
    assert len(mems[0].contradictions) == 1
    assert mems[0].contradictions[0].observation_evidence.source_run_id == "run_3"
    
def test_invalid_transitions(repo):
    service = MemoryService(repo)
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    
    upd = MemoryUpdate(
        update_type=MemoryUpdateType.CONFIRM,
        context_id="ctx_3",
        key="pref",
        value="night",
        simulated_time=sim_time,
        evidence=Evidence(source_run_id="run_1")
    )
    service.apply_post_run_updates([upd])
    mems = service.retrieve("ctx_3")
    
    bad_upd = MemoryUpdate(
        update_type=MemoryUpdateType.OBSERVE,
        memory_id=mems[0].id,
        context_id="ctx_3",
        key="pref",
        value="night",
        simulated_time=sim_time,
        evidence=Evidence(source_run_id="run_2")
    )
    
    with pytest.raises(MemoryTransitionError):
        service.apply_post_run_updates([bad_upd])

def test_retrieval_isolation(repo):
    service = MemoryService(repo)
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    
    service.apply_post_run_updates([
        MemoryUpdate(update_type=MemoryUpdateType.OBSERVE, context_id="A", key="k1", value="v1", simulated_time=sim_time, evidence=Evidence(source_run_id="run1")),
        MemoryUpdate(update_type=MemoryUpdateType.OBSERVE, context_id="B", key="k1", value="v1", simulated_time=sim_time, evidence=Evidence(source_run_id="run1"))
    ])
    
    mems_A = service.retrieve("A")
    assert len(mems_A) == 1
    assert mems_A[0].context_id == "A"
