from dt_sms_plugin.models.settings import (
    DynatraceSettings,
    EscalationLevelSettings,
    EscalationSettings,
    ExtensionSettings,
    ManagementZone,
    SmsApiSettings,
)


def _load_management_zones(config: dict) -> list[ManagementZone]:
    return [ManagementZone(name=mz["name"]) for mz in config.get("managementZones", [])]


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


def _load_sms_api(config: dict) -> SmsApiSettings:
    return SmsApiSettings(
        url=config["smsApiUrl"].strip(),
        username=config["smsApiUsername"].strip(),
        password=config["smsApiPassword"],
        timeout=config["smsApiTimeout"],
    )


def load_settings(config: dict) -> ExtensionSettings:
    return ExtensionSettings(
        polling_interval=config["pollingInterval"],
        lookback_window=config["lookbackWindow"],
        max_problems_per_execution=config.get("maxProblemsPerExecution"),
        management_zones=_load_management_zones(config),
        dynatrace=DynatraceSettings(
            url=config["dynatraceUrl"].rstrip("/"),
            api_token=config["dynatraceApiToken"],
        ),
        escalation=_load_escalation(config),
        sms_api=_load_sms_api(config),
        dry_run=config["dryRun"],
        payload_logging=config["payloadLogging"],
    )
