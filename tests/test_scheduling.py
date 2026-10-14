import pytest
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from nexus.core.time import SimulatedClock
from nexus.core.domain.calendar import CalendarEvent, Visibility
from nexus.core.scheduling import (
    SchedulingConstraints,
    WorkingWindow,
    CandidateSlot,
    generate_valid_candidates,
    evaluate_slot
)

# Helpers
def dt(year, month, day, hour, minute, tz="UTC"):
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))

def make_clock(year, month, day, hour, minute):
    return SimulatedClock(dt(year, month, day, hour, minute))

def make_event(start, end, id="evt_1"):
    return CalendarEvent(id=id, title="Test", start=start, end=end, visibility=Visibility.PUBLIC)

def test_empty_calendar_generates_all_slots():
    clock = make_clock(2024, 1, 1, 0, 0)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0),
        window_end=dt(2024, 1, 1, 10, 0),
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=15)
    )
    # Expected slots: 09:00, 09:15, 09:30
    slots = generate_valid_candidates(clock, constraints, [])
    assert len(slots) == 3
    assert slots[0].start == dt(2024, 1, 1, 9, 0)
    assert slots[1].start == dt(2024, 1, 1, 9, 15)
    assert slots[2].start == dt(2024, 1, 1, 9, 30)

def test_single_event_removes_overlaps():
    clock = make_clock(2024, 1, 1, 0, 0)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0),
        window_end=dt(2024, 1, 1, 10, 0),
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=15)
    )
    # Event blocks 09:15-09:45
    events = [make_event(dt(2024, 1, 1, 9, 15), dt(2024, 1, 1, 9, 45))]
    slots = generate_valid_candidates(clock, constraints, events)
    # Only 09:00-09:30 is overlapping, 09:15-09:45 is overlapping, 09:30-10:00 is overlapping?
    # Wait: 
    # 09:00 - 09:30 -> overlaps with 09:15-09:45
    # 09:15 - 09:45 -> overlaps
    # 09:30 - 10:00 -> overlaps with 09:15-09:45 (at 09:30)
    # Actually, all slots overlap!
    assert len(slots) == 0

    # Let's make an event 09:30-10:00
    events = [make_event(dt(2024, 1, 1, 9, 30), dt(2024, 1, 1, 10, 0))]
    slots = generate_valid_candidates(clock, constraints, events)
    # 09:00 - 09:30 is VALID (ends exactly when event starts)
    # 09:15 - 09:45 overlaps
    # 09:30 - 10:00 overlaps
    assert len(slots) == 1
    assert slots[0].start == dt(2024, 1, 1, 9, 0)

def test_candidate_ending_exactly_when_event_starts_is_valid():
    clock = make_clock(2024, 1, 1, 0, 0)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0),
        window_end=dt(2024, 1, 1, 10, 0),
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=30)
    )
    events = [make_event(dt(2024, 1, 1, 9, 30), dt(2024, 1, 1, 10, 0))]
    slots = generate_valid_candidates(clock, constraints, events)
    assert len(slots) == 1
    assert slots[0].start == dt(2024, 1, 1, 9, 0)

def test_meeting_longer_than_window_produces_no_slots():
    with pytest.raises(ValueError, match="duration exceeds scheduling window"):
        SchedulingConstraints(
            window_start=dt(2024, 1, 1, 9, 0),
            window_end=dt(2024, 1, 1, 9, 15),
            duration=timedelta(minutes=30),
            granularity=timedelta(minutes=15)
        )

def test_meeting_exactly_fits_window():
    clock = make_clock(2024, 1, 1, 0, 0)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0),
        window_end=dt(2024, 1, 1, 9, 30),
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=15)
    )
    slots = generate_valid_candidates(clock, constraints, [])
    assert len(slots) == 1
    assert slots[0].start == dt(2024, 1, 1, 9, 0)

def test_working_hours():
    clock = make_clock(2024, 1, 1, 0, 0)
    ww = WorkingWindow(timezone="UTC", start_local=time(9, 0), end_local=time(17, 0))
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 8, 0),
        window_end=dt(2024, 1, 1, 18, 0),
        duration=timedelta(hours=1),
        granularity=timedelta(hours=1),
        working_window=ww
    )
    slots = generate_valid_candidates(clock, constraints, [])
    # 08:00 is invalid, 17:00 is invalid
    assert len(slots) == 8 # 9, 10, 11, 12, 13, 14, 15, 16
    assert slots[0].start.hour == 9
    assert slots[-1].start.hour == 16

def test_buffers():
    clock = make_clock(2024, 1, 1, 0, 0)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0),
        window_end=dt(2024, 1, 1, 11, 0),
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=15),
        buffer_after=timedelta(minutes=15) # Meeting needs 15m after
    )
    # Event blocks 10:00-10:30
    events = [make_event(dt(2024, 1, 1, 10, 0), dt(2024, 1, 1, 10, 30))]
    slots = generate_valid_candidates(clock, constraints, events)
    
    # 09:15-09:45 -> valid (buffer_after goes to 10:00, fits exactly)
    # 09:30-10:00 -> invalid (buffer_after goes to 10:15, overlaps 10:00)
    slot_starts = [s.start for s in slots]
    assert dt(2024, 1, 1, 9, 15) in slot_starts
    assert dt(2024, 1, 1, 9, 30) not in slot_starts
    
    # After event: 10:30-11:00 -> valid (no buffer before needed)
    assert dt(2024, 1, 1, 10, 30) in slot_starts

def test_cross_timezone_calendar_conflicts():
    clock = make_clock(2024, 1, 1, 0, 0)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0, tz="America/New_York"),
        window_end=dt(2024, 1, 1, 11, 0, tz="America/New_York"),
        duration=timedelta(hours=1),
        granularity=timedelta(hours=1)
    )
    # Event expressed in UTC. 9AM NY is 14:00 UTC (Jan = EST = -5)
    # Block 14:00 - 15:00 UTC
    events = [make_event(dt(2024, 1, 1, 14, 0, tz="UTC"), dt(2024, 1, 1, 15, 0, tz="UTC"))]
    slots = generate_valid_candidates(clock, constraints, events)
    # 9-10 AM NY is blocked.
    # Only 10-11 AM NY should be valid
    assert len(slots) == 1
    assert slots[0].start == dt(2024, 1, 1, 10, 0, tz="America/New_York")

def test_past_candidates_rejected():
    clock = make_clock(2024, 1, 1, 10, 30)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0),
        window_end=dt(2024, 1, 1, 12, 0),
        duration=timedelta(hours=1),
        granularity=timedelta(minutes=30)
    )
    slots = generate_valid_candidates(clock, constraints, [])
    # 09:00, 09:30, 10:00 are rejected
    assert slots[0].start == dt(2024, 1, 1, 10, 30)

def test_dst_spring_forward_gap():
    clock = make_clock(2024, 1, 1, 0, 0)
    # NY gap: March 10, 2024, 02:00 -> 03:00
    constraints = SchedulingConstraints(
        window_start=dt(2024, 3, 10, 1, 0, tz="America/New_York"),
        window_end=dt(2024, 3, 10, 4, 0, tz="America/New_York"),
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=30)
    )
    # In UTC: 01:00 EST -> 06:00 UTC. 04:00 EDT -> 08:00 UTC.
    # Total duration is 2 hours. Slots: 1:00 EST (6:00 UTC), 1:30 EST (6:30 UTC), 3:00 EDT (7:00 UTC), 3:30 EDT (7:30 UTC).
    # Does the engine generate them cleanly since we iterate in UTC?
    # Our engine iterates by adding granularity to start (which is aware).
    slots = generate_valid_candidates(clock, constraints, [])
    assert len(slots) == 4
    # The gap itself (02:00 local) is entirely bypassed because we do UTC arithmetic
    assert slots[0].start == dt(2024, 3, 10, 6, 0, tz="UTC")
    assert slots[1].start == dt(2024, 3, 10, 6, 30, tz="UTC")
    assert slots[2].start == dt(2024, 3, 10, 7, 0, tz="UTC")
    assert slots[3].start == dt(2024, 3, 10, 7, 30, tz="UTC")

def test_dst_fall_back_overlap():
    clock = make_clock(2024, 1, 1, 0, 0)
    # NY fallback: Nov 3, 2024, 02:00 EDT -> 01:00 EST
    # Window 00:30 EDT to 02:30 EST
    window_start = datetime(2024, 11, 3, 0, 30, tzinfo=ZoneInfo("America/New_York"), fold=0)
    window_end = datetime(2024, 11, 3, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=1)
    
    constraints = SchedulingConstraints(
        window_start=window_start,
        window_end=window_end,
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=30)
    )
    slots = generate_valid_candidates(clock, constraints, [])
    # 00:30 EDT -> 04:30 UTC
    # 1:30 EST -> 06:30 UTC
    # Total duration = 2 hours = 4 slots
    assert len(slots) == 4
    assert slots[0].start.astimezone(timezone.utc) == dt(2024, 11, 3, 4, 30, tz="UTC")
    assert slots[3].start.astimezone(timezone.utc) == dt(2024, 11, 3, 6, 0, tz="UTC")

def test_deterministic_ordering():
    clock = make_clock(2024, 1, 1, 0, 0)
    constraints = SchedulingConstraints(
        window_start=dt(2024, 1, 1, 9, 0),
        window_end=dt(2024, 1, 1, 11, 0),
        duration=timedelta(minutes=30),
        granularity=timedelta(minutes=30)
    )
    slots = generate_valid_candidates(clock, constraints, [])
    for i in range(len(slots) - 1):
        assert slots[i].start < slots[i+1].start
