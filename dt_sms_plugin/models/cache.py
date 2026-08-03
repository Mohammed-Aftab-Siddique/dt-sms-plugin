from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CacheEntry:
    problem_id: str

    status: str

    start_time: datetime

    escalation_level: str

    last_notification_type: str

    last_updated: datetime
