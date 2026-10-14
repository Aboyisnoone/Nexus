from datetime import datetime, timezone
from typing import List
from zoneinfo import ZoneInfo
from .models import SchedulingConstraints, CandidateSlot
from nexus.core.domain.calendar import CalendarEvent
from nexus.core.time import SimulatedClock

def _is_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    return start1 < end2 and start2 < end1

def evaluate_slot(
    clock: SimulatedClock,
    start_utc: datetime, 
    end_utc: datetime, 
    constraints: SchedulingConstraints, 
    events: List[CalendarEvent]
) -> CandidateSlot:
    violations = []
    
    if start_utc < clock.now():
        violations.append("PAST_TIME_VIOLATION")
        
    if start_utc < constraints.window_start.astimezone(timezone.utc) or end_utc > constraints.window_end.astimezone(timezone.utc):
        violations.append("WINDOW_CONTAINMENT_VIOLATION")

    if constraints.working_window:
        ww = constraints.working_window
        tz = ZoneInfo(ww.timezone)
        
        start_local = start_utc.astimezone(tz)
        end_local = end_utc.astimezone(tz)
        
        from datetime import time
        if start_local.date() != end_local.date():
            if not (end_local.time() == time(0, 0) and (end_local.date() - start_local.date()).days == 1):
                violations.append("WORKING_HOURS_VIOLATION")
                
        if "WORKING_HOURS_VIOLATION" not in violations:
            start_t = start_local.time()
            end_t = end_local.time()
            
            if start_local.date() != end_local.date() and end_local.time() == time(0,0):
                if ww.end_local < time(23, 59, 59):
                    violations.append("WORKING_HOURS_VIOLATION")
            else:
                if start_t < ww.start_local or end_t > ww.end_local:
                    violations.append("WORKING_HOURS_VIOLATION")

    buffered_start = start_utc - constraints.buffer_before
    buffered_end = end_utc + constraints.buffer_after
    
    for event in events:
        event_start_utc = event.start.astimezone(timezone.utc)
        event_end_utc = event.end.astimezone(timezone.utc)
        if _is_overlap(buffered_start, buffered_end, event_start_utc, event_end_utc):
            violations.append("CALENDAR_OVERLAP")
            break

    # Convert back to constraints timezone for result
    tz_out = constraints.window_start.tzinfo
    return CandidateSlot(
        start=start_utc.astimezone(tz_out),
        end=end_utc.astimezone(tz_out),
        valid=len(violations) == 0,
        violations=tuple(violations)
    )

def generate_valid_candidates(
    clock: SimulatedClock,
    constraints: SchedulingConstraints,
    events: List[CalendarEvent]
) -> List[CandidateSlot]:
    valid_candidates = []
    
    current_start_utc = constraints.window_start.astimezone(timezone.utc)
    window_end_utc = constraints.window_end.astimezone(timezone.utc)
    
    while current_start_utc + constraints.duration <= window_end_utc:
        current_end_utc = current_start_utc + constraints.duration
        
        slot = evaluate_slot(clock, current_start_utc, current_end_utc, constraints, events)
        if slot.valid:
            valid_candidates.append(slot)
            
        current_start_utc += constraints.granularity
        
    return valid_candidates
