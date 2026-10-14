import pytest
from datetime import datetime, timezone, timedelta
from nexus.core.time import (
    SimulatedClock, 
    NaiveDatetimeError, 
    NonexistentTimeError,
    duration_between, 
    create_local_instant
)

def test_clock_returns_scenario_time():
    simulated = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(simulated)
    assert clock.now() == simulated

def test_clock_is_immutable():
    simulated = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(simulated)
    
    with pytest.raises(AttributeError):
        clock._now_utc = datetime(2025, 1, 1, tzinfo=timezone.utc)

def test_naive_datetime_rejected():
    naive = datetime(2024, 11, 1, 9, 0)
    with pytest.raises(NaiveDatetimeError):
        SimulatedClock(naive)
        
    with pytest.raises(NaiveDatetimeError):
        duration_between(naive, datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc))

def test_invalid_timezone_rejected():
    simulated = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(simulated)
    with pytest.raises(ValueError, match="Invalid timezone identifier"):
        clock.now_in("Invalid/Timezone")
        
    with pytest.raises(ValueError, match="Invalid timezone identifier"):
        create_local_instant(2024, 11, 1, 9, 0, tz_name="Invalid/Timezone")

def test_utc_conversion_and_multiple_representations():
    simulated = datetime(2024, 11, 1, 14, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(simulated)
    
    ny_time = clock.now_in("America/New_York")
    tokyo_time = clock.now_in("Asia/Tokyo")
    
    assert ny_time == tokyo_time
    assert ny_time == clock.now()
    assert ny_time.hour == 10
    assert tokyo_time.hour == 23

def test_dst_spring_forward_and_nonexistent_time():
    # 2024-03-10 02:00 -> 03:00 in America/New_York
    # Nonexistent time: 02:30
    with pytest.raises(NonexistentTimeError):
        create_local_instant(2024, 3, 10, 2, 30, tz_name="America/New_York")

def test_dst_fall_back_and_ambiguous_time():
    # 2024-11-03 02:00 -> 01:00 in America/New_York
    dt_fold0 = create_local_instant(2024, 11, 3, 1, 30, tz_name="America/New_York", fold=0)
    dt_fold1 = create_local_instant(2024, 11, 3, 1, 30, tz_name="America/New_York", fold=1)
    
    clock0 = SimulatedClock(dt_fold0)
    clock1 = SimulatedClock(dt_fold1)
    
    assert clock0.now() == datetime(2024, 11, 3, 5, 30, tzinfo=timezone.utc) # EDT
    assert clock1.now() == datetime(2024, 11, 3, 6, 30, tzinfo=timezone.utc) # EST
    assert duration_between(clock0.now(), clock1.now()) == timedelta(hours=1)

def test_duration_between():
    dt1 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 1, 1, 14, 30, tzinfo=timezone.utc)
    assert duration_between(dt1, dt2) == timedelta(hours=2, minutes=30)
