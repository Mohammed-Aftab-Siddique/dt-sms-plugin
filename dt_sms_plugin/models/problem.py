from dataclasses import dataclass
from datetime import datetime

from dt_sms_plugin.utils.constants import SYNTHETIC_ENTITY_TYPES


@dataclass(slots=True)
class Problem:
    problem_id: str

    display_id: str
    title: str

    status: str
    severity: str

    impact_level: str
    entity_type: str

    start_time: datetime
    end_time: datetime | None

    affected_entities: list[str]

    monitor_name: str
    synthetic_step_name: str

    @property
    def is_synthetic(self) -> bool:
        return self.entity_type in SYNTHETIC_ENTITY_TYPES
