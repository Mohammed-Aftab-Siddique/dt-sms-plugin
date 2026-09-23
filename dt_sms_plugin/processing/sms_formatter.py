from zoneinfo import ZoneInfo

from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.utils.constants import (
    NOTIFICATION_CLOSED,
)


class SmsFormatter:
    @staticmethod
    def build(
        problem: Problem,
        notification_type: str,
        escalation_level: str,
        synthetic: bool = False,
        application_name: str = "N/A",
    ) -> str:
        event_time = problem.end_time if notification_type == NOTIFICATION_CLOSED else problem.start_time

        time_text = event_time.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d-%b-%Y %H:%M:%S IST")
        status_text = (
            problem.status
            if notification_type == NOTIFICATION_CLOSED
            else f"{problem.status} {escalation_level}"
        )

        if synthetic:
            return (
                f"Application: {application_name}\n"
                f"Incident: {problem.synthetic_step_name or 'N/A'}\n"
                f"Status: {status_text}\n"
                f"Flow Name: {problem.monitor_name or 'N/A'}\n"
                f"Time: {time_text}\n"
                f"DT"
            )

        entity_name = problem.affected_entities[0] if problem.affected_entities else "N/A"

        return (
            f"Application: {application_name}\n"
            f"Incident: {problem.title}\n"
            f"Severity: {problem.severity}\n"
            f"Status: {status_text}\n"
            f"Entity: {entity_name}\n"
            f"Time: {time_text}\n"
            f"DT"
        )
