from datetime import UTC

from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.utils.constants import (
    NOTIFICATION_CLOSED,
)


class SmsFormatter:
    @staticmethod
    def build(
        problem: Problem,
        notification_type: str,
    ) -> str:

        entity_name = problem.affected_entities[0] if problem.affected_entities else "N/A"

        entity_type = problem.entity_type if problem.entity_type else "N/A"

        event_time = problem.end_time if notification_type == NOTIFICATION_CLOSED else problem.start_time

        time_text = event_time.astimezone(UTC).strftime("%d-%b-%Y %H:%M:%S UTC")

        return (
            f"Application: {entity_name}\n"
            f"Incident: {problem.title}\n"
            f"Severity: {problem.severity}\n"
            f"Status: {problem.status}\n"
            f"Entity: {entity_type}\n"
            f"Time: {time_text}\n"
            f"DT"
        )
