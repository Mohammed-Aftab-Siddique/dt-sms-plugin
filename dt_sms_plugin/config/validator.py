from dt_sms_plugin.models.settings import ExtensionSettings
from dt_sms_plugin.utils.constants import (
    ESCALATION_LEVELS,
    SEVERITIES,
)
from dt_sms_plugin.utils.exceptions import ConfigurationError


def _validate_polling(settings: ExtensionSettings) -> None:
    if settings.polling_interval <= 0:
        raise ConfigurationError("Polling interval must be greater than zero.")

    if settings.lookback_window <= 0:
        raise ConfigurationError("Lookback window must be greater than zero.")


def _validate_escalation(settings: ExtensionSettings) -> None:
    if settings.escalation.l2_after_minutes >= settings.escalation.l3_after_minutes:
        raise ConfigurationError("L2 escalation delay must be less than L3 escalation delay.")


def _validate_management_zones(settings: ExtensionSettings) -> None:
    if not settings.management_zones:
        return

    for mz in settings.management_zones:
        if not mz.name.strip():
            raise ConfigurationError("Management Zone name cannot be empty.")


def _validate_level(
    level_name: str,
    recipients: list[str],
    severities: list[str],
) -> None:
    if not recipients:
        raise ConfigurationError(f"{level_name} must contain at least one recipient.")

    if not severities:
        raise ConfigurationError(f"{level_name} must contain at least one severity.")

    invalid = [severity for severity in severities if severity not in SEVERITIES]

    if invalid:
        raise ConfigurationError(f"{level_name} contains invalid severities: {', '.join(invalid)}")


def _validate_recipients(settings: ExtensionSettings) -> None:
    levels = {
        "L1": settings.escalation.l1,
        "L2": settings.escalation.l2,
        "L3": settings.escalation.l3,
    }

    for level in ESCALATION_LEVELS:
        escalation = levels[level]

        _validate_level(
            level,
            escalation.recipients,
            escalation.severities,
        )


def _validate_sms_api(settings: ExtensionSettings) -> None:
    if not settings.sms_api.url:
        raise ConfigurationError("SMS API URL cannot be empty.")

    if not settings.sms_api.username:
        raise ConfigurationError("SMS API username cannot be empty.")

    if not settings.sms_api.password:
        raise ConfigurationError("SMS API password cannot be empty.")

    if settings.sms_api.timeout <= 0:
        raise ConfigurationError("SMS API timeout must be greater than zero.")


def validate_settings(settings: ExtensionSettings) -> None:
    _validate_polling(settings)
    _validate_management_zones(settings)
    _validate_escalation(settings)
    _validate_recipients(settings)
    _validate_sms_api(settings)
