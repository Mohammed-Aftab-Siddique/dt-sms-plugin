from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Problem:
    problem_id: str

    display_id: str
    title: str

    status: str
    severity: str

    impact_level: str
    entity_type: str

    management_zones: list[str]

    start_time: datetime
    end_time: datetime | None

    affected_entities: list[str]
