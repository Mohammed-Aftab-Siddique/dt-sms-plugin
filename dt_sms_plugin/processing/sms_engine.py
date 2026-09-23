from __future__ import annotations

from datetime import datetime

from dt_sms_plugin.cache.cache_manager import CacheManager
from dt_sms_plugin.clients.sms_client import SmsClient
from dt_sms_plugin.models.cache import CacheEntry
from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.models.settings import EscalationSettings, ExtensionSettings
from dt_sms_plugin.models.sms import SmsMessage
from dt_sms_plugin.processing.escalation import (
    get_current_level,
    get_initial_level,
    get_notification_levels,
)
from dt_sms_plugin.processing.sms_formatter import SmsFormatter
from dt_sms_plugin.utils.constants import (
    LEVEL_L1,
    LEVEL_L2,
    NOTIFICATION_CLOSED,
    NOTIFICATION_ESCALATION,
    NOTIFICATION_OPEN,
    STATUS_CLOSED,
)


class SmsEngine:
    def __init__(
        self,
        settings: ExtensionSettings,
        cache: CacheManager,
        synthetic_cache: CacheManager,
        sms_client: SmsClient,
    ):
        self._settings = settings
        self._cache = cache
        self._synthetic_cache = synthetic_cache
        self._sms = sms_client

    def process(self, problems: list[Problem]) -> None:
        for problem in problems:
            if problem.is_synthetic:
                if not self._settings.synthetic.enabled:
                    continue

                cache = self._synthetic_cache
                escalation = self._settings.synthetic.escalation
                synthetic = True
            else:
                cache = self._cache
                escalation = self._settings.escalation
                synthetic = False

            self._process_problem(problem, cache, escalation, synthetic)

        self._cache.save()

        if self._settings.synthetic.enabled:
            self._synthetic_cache.save()

    def _process_problem(
        self,
        problem: Problem,
        cache: CacheManager,
        escalation: EscalationSettings,
        synthetic: bool,
    ) -> None:
        cached = cache.get(problem.problem_id)

        if cached is None:
            self._handle_new(problem, cache, escalation, synthetic)
            return

        if problem.status.upper() == STATUS_CLOSED:
            self._handle_closed(problem, cached, cache, escalation, synthetic)
            return

        self._handle_existing(problem, cached, cache, escalation, synthetic)

    def _handle_new(
        self,
        problem: Problem,
        cache: CacheManager,
        escalation: EscalationSettings,
        synthetic: bool,
    ) -> None:
        level = LEVEL_L1 if synthetic else get_initial_level(problem, escalation)

        self._send(problem, level, NOTIFICATION_OPEN, escalation, synthetic)

        cache.put(
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
        cache: CacheManager,
        escalation: EscalationSettings,
        synthetic: bool,
    ) -> None:
        level = get_current_level(
            cached,
            problem,
            escalation,
        )

        if level == cached.escalation_level:
            return

        self._send(
            problem,
            level,
            NOTIFICATION_ESCALATION,
            escalation,
            synthetic,
        )

        cached.escalation_level = level
        cached.last_notification_type = NOTIFICATION_ESCALATION
        cached.last_updated = datetime.now(problem.start_time.tzinfo)

        cache.put(cached)

    def _handle_closed(
        self,
        problem: Problem,
        cached: CacheEntry,
        cache: CacheManager,
        escalation: EscalationSettings,
        synthetic: bool,
    ) -> None:
        self._send(
            problem,
            cached.escalation_level,
            NOTIFICATION_CLOSED,
            escalation,
            synthetic,
            cumulative=True,
        )

        cached.status = STATUS_CLOSED
        cached.last_notification_type = NOTIFICATION_CLOSED
        cached.last_updated = datetime.now(problem.start_time.tzinfo)

        cache.put(cached)

    def _send(
        self,
        problem: Problem,
        level: str,
        notification_type: str,
        escalation: EscalationSettings,
        synthetic: bool,
        cumulative: bool = False,
    ) -> None:
        levels = get_notification_levels(level) if cumulative else [level]

        for current in levels:
            recipients = self._get_recipients(escalation, current)

            self._sms.send(
                SmsMessage(
                    recipients=recipients,
                    problem_id=problem.problem_id,
                    notification_type=notification_type,
                    message=SmsFormatter.build(
                        problem,
                        notification_type,
                        level,
                        synthetic,
                    ),
                )
            )

    def _get_recipients(
        self,
        escalation: EscalationSettings,
        level: str,
    ) -> list[str]:
        if level == LEVEL_L1:
            return escalation.l1.recipients

        if level == LEVEL_L2:
            return escalation.l2.recipients

        return escalation.l3.recipients
