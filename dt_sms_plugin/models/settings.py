from dataclasses import dataclass, field


@dataclass(frozen=True)
class DynatraceSettings:
    url: str
    api_token: str


@dataclass(slots=True)
class ManagementZone:
    name: str


@dataclass(slots=True)
class EscalationLevelSettings:
    severities: list[str] = field(default_factory=list)
    recipients: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EscalationSettings:
    l1: EscalationLevelSettings
    l2: EscalationLevelSettings
    l3: EscalationLevelSettings

    l2_after_minutes: int
    l3_after_minutes: int


@dataclass(slots=True)
class SmsApiSettings:
    url: str
    username: str
    password: str
    timeout: int


@dataclass(slots=True)
class ExtensionSettings:
    polling_interval: int
    lookback_window: int
    max_problems_per_execution: int | None

    management_zones: list[ManagementZone]

    dynatrace: DynatraceSettings

    escalation: EscalationSettings

    sms_api: SmsApiSettings

    dry_run: bool
    payload_logging: bool
