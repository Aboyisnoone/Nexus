import pytest
import yaml
from pydantic import ValidationError

from nexus.core.scenario_loader import load_scenario
from nexus.core.domain.scenario import Scenario

def test_load_valid_scenario():
    scenario = load_scenario("scenarios/examples/happy_path.yaml")
    assert scenario.scenario_id == "happy_path_01"
    assert len(scenario.initial_state.calendar) == 1
    assert len(scenario.initial_state.memory) == 1
    assert len(scenario.events) == 1
    assert len(scenario.expected_evaluation.assertions) == 2

def test_invalid_simulated_time_naive(tmp_path):
    yaml_content = '''
    scenario_id: test
    simulated_time: "2024-11-01T09:00:00" # Naive
    initial_state:
      calendar: []
      memory: []
    expected_evaluation:
      assertions: []
    '''
    file_path = tmp_path / "test.yaml"
    file_path.write_text(yaml_content)
    
    with pytest.raises(ValidationError, match="simulated_time must be timezone-aware"):
        load_scenario(file_path)

def test_invalid_calendar_event_times(tmp_path):
    yaml_content = '''
    scenario_id: test
    simulated_time: "2024-11-01T09:00:00Z"
    initial_state:
      calendar:
        - id: evt_1
          title: Sync
          start: "2024-11-01T11:00:00Z"
          end: "2024-11-01T10:00:00Z" # end before start
          visibility: PUBLIC
      memory: []
    expected_evaluation:
      assertions: []
    '''
    file_path = tmp_path / "test.yaml"
    file_path.write_text(yaml_content)
    
    with pytest.raises(ValidationError, match="start time must be before end time"):
        load_scenario(file_path)

def test_invalid_memory_state(tmp_path):
    yaml_content = '''
    scenario_id: test
    simulated_time: "2024-11-01T09:00:00Z"
    initial_state:
      calendar: []
      memory:
        - id: mem_1
          context_id: user_1
          key: a
          value: b
          state: FORGOTTEN # Invalid
          evidence: []
    expected_evaluation:
      assertions: []
    '''
    file_path = tmp_path / "test.yaml"
    file_path.write_text(yaml_content)
    
    with pytest.raises(ValidationError):
        load_scenario(file_path)

def test_invalid_assertion(tmp_path):
    yaml_content = '''
    scenario_id: test
    simulated_time: "2024-11-01T09:00:00Z"
    initial_state:
      calendar: []
      memory: []
    expected_evaluation:
      assertions:
        - type: unknown_assertion
    '''
    file_path = tmp_path / "test.yaml"
    file_path.write_text(yaml_content)
    
    with pytest.raises(ValidationError):
        load_scenario(file_path)

def test_scenario_immutability():
    scenario = load_scenario("scenarios/examples/happy_path.yaml")
    
    with pytest.raises(Exception):
        scenario.description = "Mutated"
        
    with pytest.raises(Exception):
        scenario.initial_state.calendar.append("New Event")

def test_yaml_failure(tmp_path):
    yaml_content = '''
    scenario_id: test
    simulated_time: "2024-11-01T09:00:00Z"
      invalid_indent: true
    '''
    file_path = tmp_path / "test.yaml"
    file_path.write_text(yaml_content)
    
    with pytest.raises(yaml.YAMLError):
        load_scenario(file_path)

def test_serialization():
    scenario = load_scenario("scenarios/examples/happy_path.yaml")
    
    # Serialize to dict (simulating JSON/YAML dump)
    serialized_data = scenario.model_dump(mode='json')
    
    # Load back
    reloaded_scenario = Scenario.model_validate(serialized_data)
    
    assert scenario == reloaded_scenario
    assert reloaded_scenario.simulated_time.tzinfo is not None

def test_deep_immutability():
    scenario = load_scenario("scenarios/examples/happy_path.yaml")
    
    # 1. Event payload mutation
    event = scenario.events[0]
    with pytest.raises(TypeError, match="FrozenDict is immutable"):
        event.payload["new_key"] = "value"
        
    # 2. Calendar collection mutation
    with pytest.raises(AttributeError): # tuple has no attribute append
        scenario.initial_state.calendar.append("New Event")
        
    # 3. Memory evidence mutation
    memory = scenario.initial_state.memory[0]
    with pytest.raises(AttributeError): # tuple has no attribute append
        memory.evidence.append("new_evidence")
