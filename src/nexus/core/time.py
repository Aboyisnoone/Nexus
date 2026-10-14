from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

class NaiveDatetimeError(ValueError):
    pass

class NonexistentTimeError(ValueError):
    pass

def _require_aware(dt: datetime) -> None:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise NaiveDatetimeError("Datetime must be timezone-aware.")

class SimulatedClock:
    def __init__(self, simulated_time: datetime):
        _require_aware(simulated_time)
        super().__setattr__("_now_utc", simulated_time.astimezone(timezone.utc))
        
    def __setattr__(self, name, value):
        raise AttributeError("SimulatedClock is read-only")

    def now(self) -> datetime:
        return self._now_utc

    def now_in(self, tz_name: str) -> datetime:
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            raise ValueError(f"Invalid timezone identifier: {tz_name}")
        return self._now_utc.astimezone(tz)

def duration_between(start: datetime, end: datetime) -> timedelta:
    _require_aware(start)
    _require_aware(end)
    return end - start

def create_local_instant(
    year: int, month: int, day: int, 
    hour: int, minute: int, second: int = 0, 
    tz_name: str = "UTC", 
    fold: int = 0
) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        raise ValueError(f"Invalid timezone identifier: {tz_name}")
        
    dt = datetime(year, month, day, hour, minute, second, tzinfo=tz, fold=fold)
    
    # Explicitly reject nonexistent local times
    utc_dt = dt.astimezone(timezone.utc)
    local_rt = utc_dt.astimezone(tz)
    if local_rt.replace(tzinfo=None) != dt.replace(tzinfo=None):
        raise NonexistentTimeError(f"Local time {dt} does not exist in timezone {tz_name} due to DST transition.")
        
    return dt
