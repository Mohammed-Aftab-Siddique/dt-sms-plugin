from datetime import datetime

from dt_sms_plugin.models.cache import CacheEntry
from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.models.settings import EscalationSettings
from dt_sms_plugin.utils.constants import (
    L1,
    L2,
    L3,
    STATUS_CLOSED,
)


def get_initial_level(
    problem: Problem,
    settings: EscalationSettings,
) -> str:
    severity = problem.severity.upper()

    if severity in settings.l3.severities:
        return L3

    if severity in settings.l2.severities:
        return L2

    return L1


def get_current_level(
    cache: CacheEntry,
    problem: Problem,
    settings: EscalationSettings,
) -> str:
    if problem.status.upper() == STATUS_CLOSED:
        return cache.escalation_level

    elapsed = (datetime.now(problem.start_time.tzinfo) - cache.start_time).total_seconds() / 60

    if cache.escalation_level == L1 and elapsed >= settings.l2_after_minutes:
        return L2

    if cache.escalation_level in (L1, L2) and elapsed >= settings.l3_after_minutes:
        return L3

    return cache.escalation_level


def get_notification_levels(
    level: str,
) -> list[str]:
    if level == L1:
        return [L1]

    if level == L2:
        return [L1, L2]

    return [L1, L2, L3]
