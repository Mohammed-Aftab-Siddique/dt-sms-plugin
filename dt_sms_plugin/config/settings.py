from dt_sms_plugin.models.settings import (
    DynatraceSettings,
    EscalationLevelSettings,
    EscalationSettings,
    ExtensionSettings,
    SmsApiSettings,
    SyntheticSettings,
)


def _load_escalation_level(
    config: dict,
    level: str,
) -> EscalationLevelSettings:
    return EscalationLevelSettings(
        severities=[severity.strip().upper() for severity in config.get(f"{level}Severities", [])],
        recipients=[recipient["number"].strip() for recipient in config.get(f"{level}Recipients", [])],
    )


def _load_escalation(config: dict) -> EscalationSettings:
    return EscalationSettings(
        l1=_load_escalation_level(config, "l1"),
        l2=_load_escalation_level(config, "l2"),
        l3=_load_escalation_level(config, "l3"),
        l2_after_minutes=config["l2AfterMinutes"],
        l3_after_minutes=config["l3AfterMinutes"],
    )


def _copy_escalation_without_severities(settings: EscalationSettings) -> EscalationSettings:
    return EscalationSettings(
        l1=EscalationLevelSettings(recipients=list(settings.l1.recipients)),
        l2=EscalationLevelSettings(recipients=list(settings.l2.recipients)),
        l3=EscalationLevelSettings(recipients=list(settings.l3.recipients)),
        l2_after_minutes=settings.l2_after_minutes,
        l3_after_minutes=settings.l3_after_minutes,
    )


def _load_synthetic_escalation(config: dict) -> EscalationSettings:
    return EscalationSettings(
        l1=EscalationLevelSettings(
            recipients=[recipient["number"].strip() for recipient in config.get("syntheticL1Recipients", [])]
        ),
        l2=EscalationLevelSettings(
            recipients=[recipient["number"].strip() for recipient in config.get("syntheticL2Recipients", [])]
        ),
        l3=EscalationLevelSettings(
            recipients=[recipient["number"].strip() for recipient in config.get("syntheticL3Recipients", [])]
        ),
        l2_after_minutes=config.get("syntheticL2AfterMinutes", 30),
        l3_after_minutes=config.get("syntheticL3AfterMinutes", 60),
    )


def _load_sms_api(config: dict) -> SmsApiSettings:
    return SmsApiSettings(
        url=config["smsApiUrl"].strip(),
        username=config["smsApiUsername"].strip(),
        password=config["smsApiPassword"],
        timeout=config["smsApiTimeout"],
    )


def load_settings(config: dict) -> ExtensionSettings:
    escalation = _load_escalation(config)
    synthetic_enabled = config.get("syntheticEnabled", False)
    synthetic_use_same = config.get("syntheticUseSameEscalation", True)
    synthetic_escalation = (
        _copy_escalation_without_severities(escalation)
        if synthetic_use_same
        else _load_synthetic_escalation(config)
    )

    return ExtensionSettings(
        polling_interval=config["pollingInterval"],
        lookback_window=config["lookbackWindow"],
        max_problems_per_execution=config.get("maxProblemsPerExecution"),
        management_zone=str(config.get("managementZone", "")).strip(),
        dynatrace=DynatraceSettings(
            url=config["dynatraceUrl"].rstrip("/"),
            api_token=config["dynatraceApiToken"],
        ),
        escalation=escalation,
        synthetic=SyntheticSettings(
            enabled=synthetic_enabled,
            use_same_escalation=synthetic_use_same,
            escalation=synthetic_escalation,
        ),
        sms_api=_load_sms_api(config),
        dry_run=config["dryRun"],
        payload_logging=config["payloadLogging"],
    )
