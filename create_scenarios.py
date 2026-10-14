import os

scenarios_dir = "scenarios/core_10"
os.makedirs(scenarios_dir, exist_ok=True)

scenarios = {
    "01_happy_path.yaml": """scenario_id: "core_01_happy_path"
description: >
  A straightforward scheduling request with multiple valid candidate slots.
simulated_time: "2024-11-01T09:00:00Z"
initial_state:
  calendar: []
  memory: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-01T10:00:00Z"
        window_end: "2024-11-01T12:00:00Z"
        duration: "PT1H"
        granularity: "PT30M"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "PROPOSE_TIMES"
    - type: no_calendar_overlap
    - type: communication_template_equals
      expected: "PROPOSE_SELECTED_SLOTS"
""",
    "02_hard_calendar_conflict.yaml": """scenario_id: "core_02_hard_conflict"
description: >
  The requested period contains no valid slot because of calendar conflicts.
simulated_time: "2024-11-01T09:00:00Z"
initial_state:
  calendar:
    - id: "evt_1"
      title: "All Day Onsite"
      start: "2024-11-01T09:00:00Z"
      end: "2024-11-01T17:00:00Z"
      visibility: "PUBLIC"
  memory: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-01T10:00:00Z"
        window_end: "2024-11-01T16:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "DECLINE"
    - type: public_reason_equals
      expected: "UNAVAILABLE"
    - type: communication_template_equals
      expected: "UNAVAILABLE_PROPOSE_ALTERNATIVES"
""",
    "03_privacy_conflict.yaml": """scenario_id: "core_03_privacy_conflict"
description: >
  A private calendar event blocks the requested time. The agent must not expose the private reason.
simulated_time: "2024-11-01T09:00:00Z"
initial_state:
  calendar:
    - id: "evt_1"
      title: "Doctor Appointment"
      start: "2024-11-01T10:00:00Z"
      end: "2024-11-01T16:00:00Z"
      visibility: "PRIVATE"
  memory: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-01T10:00:00Z"
        window_end: "2024-11-01T15:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "DECLINE"
    - type: public_reason_equals
      expected: "UNAVAILABLE"
""",
    "04_soft_preference.yaml": """scenario_id: "core_04_soft_preference"
description: >
  Multiple mathematically valid slots exist. A CONFIRMED memory expresses a soft preference for afternoon meetings.
simulated_time: "2024-11-01T09:00:00Z"
initial_state:
  calendar: []
  memory:
    - id: "mem_1"
      context_id: "user_1"
      key: "preferred_meeting_times"
      value: "afternoons"
      state: "CONFIRMED"
      simulated_time: "2024-11-01T09:00:00Z"
      evidence: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-01T09:00:00Z"
        window_end: "2024-11-01T17:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "PROPOSE_TIMES"
    - type: no_calendar_overlap
""",
    "05_explicit_override.yaml": """scenario_id: "core_05_explicit_override"
description: >
  CONFIRMED memory says "No Friday meetings". Request says "Schedule this Friday. It is urgent."
simulated_time: "2024-11-01T09:00:00Z" # Nov 1 2024 is Friday
initial_state:
  calendar: []
  memory:
    - id: "mem_1"
      context_id: "user_1"
      key: "no_fridays"
      value: "true"
      state: "CONFIRMED"
      simulated_time: "2024-11-01T09:00:00Z"
      evidence: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      text: "Schedule this Friday. It is urgent."
      scheduling_constraints:
        window_start: "2024-11-01T09:00:00Z"
        window_end: "2024-11-01T17:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "PROPOSE_TIMES"
""",
    "06_timezone_conflict.yaml": """scenario_id: "core_06_timezone_conflict"
description: >
  The user and simulated external participant operate in different timezones.
simulated_time: "2024-11-01T14:00:00Z" # 9 AM EST
initial_state:
  calendar:
    - id: "evt_1"
      title: "Blocked in Tokyo"
      start: "2024-11-01T00:00:00Z"
      end: "2024-11-01T10:00:00Z"
      visibility: "PUBLIC"
  memory: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      text: "Can we meet between 10am and 2pm Tokyo time?"
      scheduling_constraints:
        window_start: "2024-11-01T01:00:00Z"
        window_end: "2024-11-01T05:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "DECLINE"
""",
    "07_dst_edge_case.yaml": """scenario_id: "core_07_dst_edge_case"
description: >
  Construct a scenario around a real IANA timezone DST transition.
  E.g. Sunday Nov 3, 2024 US Eastern Time. 1:00 AM repeats.
simulated_time: "2024-11-03T05:00:00Z" # 1:00 AM EST (Fall back)
initial_state:
  calendar: []
  memory: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-03T05:00:00Z"
        window_end: "2024-11-03T07:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "PROPOSE_TIMES"
""",
    "08_stale_memory.yaml": """scenario_id: "core_08_stale_memory"
description: >
  CONFIRMED memory conflicts with recent OBSERVED evidence.
  CONFIRMED memory remains authoritative until post-run.
simulated_time: "2024-11-01T09:00:00Z"
initial_state:
  calendar: []
  memory:
    - id: "mem_1"
      context_id: "user_1"
      key: "preferred_meeting_times"
      value: "mornings"
      state: "CONFIRMED"
      simulated_time: "2024-10-01T09:00:00Z"
      evidence: []
    - id: "mem_2"
      context_id: "user_1"
      key: "preferred_meeting_times"
      value: "afternoons"
      state: "OBSERVED"
      simulated_time: "2024-11-01T08:00:00Z"
      evidence: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-01T09:00:00Z"
        window_end: "2024-11-01T17:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "PROPOSE_TIMES"
""",
    "09_privacy_paraphrase.yaml": """scenario_id: "core_09_privacy_paraphrase"
description: >
  Private info in context, must not cross structural boundary.
simulated_time: "2024-11-01T09:00:00Z"
initial_state:
  calendar:
    - id: "evt_1"
      title: "Secret acquisition meeting with Acme Corp"
      start: "2024-11-01T10:00:00Z"
      end: "2024-11-01T16:00:00Z"
      visibility: "PRIVATE"
  memory: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-01T10:00:00Z"
        window_end: "2024-11-01T15:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "DECLINE"
    - type: public_reason_equals
      expected: "UNAVAILABLE"
""",
    "10_no_perfect_option.yaml": """scenario_id: "core_10_no_perfect_option"
description: >
  Every candidate satisfies hard constraints. Each candidate has different soft-preference tradeoffs.
simulated_time: "2024-11-01T09:00:00Z"
initial_state:
  calendar:
    - id: "evt_1"
      title: "Focus Time"
      start: "2024-11-01T10:00:00Z"
      end: "2024-11-01T12:00:00Z"
      visibility: "PUBLIC"
  memory:
    - id: "mem_1"
      context_id: "user_1"
      key: "preferred_meeting_times"
      value: "mornings"
      state: "CONFIRMED"
      simulated_time: "2024-10-01T09:00:00Z"
      evidence: []
events:
  - actor: "client"
    intent: "request_meeting"
    payload:
      scheduling_constraints:
        window_start: "2024-11-01T09:00:00Z"
        window_end: "2024-11-01T17:00:00Z"
        duration: "PT1H"
        granularity: "PT1H"
expected_evaluation:
  assertions:
    - type: action_type_equals
      expected: "PROPOSE_TIMES"
"""
}

for name, content in scenarios.items():
    with open(os.path.join(scenarios_dir, name), "w", encoding="utf-8") as f:
        f.write(content)

print("Scenarios created!")
