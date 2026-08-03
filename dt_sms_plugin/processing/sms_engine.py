from __future__ import annotations

from datetime import datetime

from dt_sms_plugin.cache.cache_manager import CacheManager
from dt_sms_plugin.clients.sms_client import SmsClient
from dt_sms_plugin.models.cache import CacheEntry
from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.models.settings import ExtensionSettings
from dt_sms_plugin.models.sms import SmsMessage
from dt_sms_plugin.processing.escalation import (
    get_current_level,
    get_initial_level,
    get_notification_levels,
)
from dt_sms_plugin.processing.sms_formatter import SmsFormatter
from dt_sms_plugin.utils.constants import (
    L1,
    L2,
    NOTIFICATION_CLOSED,
    NOTIFICATION_ESCALATED,
    NOTIFICATION_OPEN,
    STATUS_CLOSED,
)


class SmsEngine:
    def __init__(
        self,
        settings: ExtensionSettings,
        cache: CacheManager,
        sms_client: SmsClient,
    ):
        self._settings = settings
        self._cache = cache
        self._sms = sms_client

    def process(self, problems: list[Problem]) -> None:
        for problem in problems:
            cached = self._cache.get(problem.problem_id)

            if cached is None:
                self._handle_new(problem)
                continue

            if problem.status.upper() == STATUS_CLOSED:
                self._handle_closed(problem, cached)
                continue

            self._handle_existing(problem, cached)

        self._cache.save()

    def _handle_new(self, problem: Problem) -> None:
        level = get_initial_level(
            problem,
            self._settings.escalation,
        )

        self._send(problem, level, NOTIFICATION_OPEN)

        self._cache.put(
            CacheEntry(
                problem_id=problem.problem_id,
                status=problem.status,
                start_time=problem.start_time,
                escalation_level=level,
                last_notification_type=NOTIFICATION_OPEN,
                last_updated=datetime.now(problem.start_time.tzinfo),
            )
        )

    def _handle_existing(
        self,
        problem: Problem,
        cached: CacheEntry,
    ) -> None:
        level = get_current_level(
            cached,
            problem,
            self._settings.escalation,
        )

        if level == cached.escalation_level:
            return

        self._send(
            problem,
            level,
            NOTIFICATION_ESCALATED,
        )

        cached.escalation_level = level
        cached.last_notification_type = NOTIFICATION_ESCALATED
        cached.last_updated = datetime.now(problem.start_time.tzinfo)

        self._cache.put(cached)

    def _handle_closed(
        self,
        problem: Problem,
        cached: CacheEntry,
    ) -> None:
        self._send(
            problem,
            cached.escalation_level,
            NOTIFICATION_CLOSED,
            cumulative=True,
        )

        cached.status = STATUS_CLOSED
        cached.last_notification_type = NOTIFICATION_CLOSED
        cached.last_updated = datetime.now(problem.start_time.tzinfo)

        self._cache.put(cached)

    def _send(
        self,
        problem: Problem,
        level: str,
        notification_type: str,
        cumulative: bool = False,
    ) -> None:
        levels = get_notification_levels(level) if cumulative else [level]

        for current in levels:
            recipients = self._get_recipients(current)

            self._sms.send(
                SmsMessage(
                    recipients=recipients,
                    problem_id=problem.problem_id,
                    notification_type=notification_type,
                    message=SmsFormatter.build(
                        problem,
                        notification_type,
                    ),
                )
            )

    def _get_recipients(
        self,
        level: str,
    ) -> list[str]:
        escalation = self._settings.escalation

        if level == L1:
            return escalation.l1.recipients

        if level == L2:
            return escalation.l2.recipients

        return escalation.l3.recipients
