import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dt_sms_plugin.cache.cache_manager import CacheManager
from dt_sms_plugin.clients.dynatrace_client import DynatraceClient
from dt_sms_plugin.config.settings import load_settings
from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.processing.sms_engine import SmsEngine
from dt_sms_plugin.processing.sms_formatter import SmsFormatter
from dt_sms_plugin.utils.constants import NOTIFICATION_CLOSED, NOTIFICATION_OPEN


class FakeSmsClient:
    def __init__(self):
        self.messages = []

    def send(self, sms):
        self.messages.append(sms)


def activation_config(**overrides):
    config = {
        "pollingInterval": 60,
        "lookbackWindow": 5,
        "maxProblemsPerExecution": 100,
        "managementZones": [],
        "dynatraceUrl": "https://example.live.dynatrace.com",
        "dynatraceApiToken": "token",
        "l1Recipients": [{"number": "1111111111"}],
        "l1Severities": ["INFO"],
        "l2Recipients": [{"number": "2222222222"}],
        "l2Severities": ["ERROR"],
        "l2AfterMinutes": 30,
        "l3Recipients": [{"number": "3333333333"}],
        "l3Severities": ["AVAILABILITY"],
        "l3AfterMinutes": 60,
        "smsApiUrl": "https://sms.example.com",
        "smsApiUsername": "user",
        "smsApiPassword": "password",
        "smsApiTimeout": 5,
        "dryRun": True,
        "payloadLogging": False,
        "syntheticEnabled": False,
        "syntheticUseSameEscalation": True,
        "syntheticL1Recipients": [{"number": "4444444444"}],
        "syntheticL2Recipients": [{"number": "5555555555"}],
        "syntheticL3Recipients": [{"number": "6666666666"}],
        "syntheticL2AfterMinutes": 10,
        "syntheticL3AfterMinutes": 20,
    }
    config.update(overrides)
    return config


def problem(*, entity_type="HOST", status="OPEN", start_time=None, end_time=None):
    return Problem(
        problem_id="P-1",
        display_id="P-1",
        title="Existing incident",
        status=status,
        severity="AVAILABILITY",
        impact_level="APPLICATION",
        entity_type=entity_type,
        management_zones=["FileNet"],
        start_time=start_time or datetime.now(UTC),
        end_time=end_time,
        affected_entities=["FileNet DocStore Flow"],
        monitor_name="FileNet DocStore Flow",
        synthetic_step_name="Error on Login Page - Click on Username",
    )


class SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.cache_path = Path(self.temp_dir.name)

    def make_engine(self, config):
        normal_cache = CacheManager(self.cache_path, "problem_cache.json")
        synthetic_cache = CacheManager(self.cache_path, "synthetic_problem_cache.json")
        sms = FakeSmsClient()
        instance = SmsEngine(
            settings=load_settings(config),
            cache=normal_cache,
            synthetic_cache=synthetic_cache,
            sms_client=sms,
        )
        return instance, normal_cache, synthetic_cache, sms

    def test_dynatrace_client_detects_synthetic_entity_and_step_name(self):
        payload = {
            "problemId": "P-1",
            "status": "OPEN",
            "severityLevel": "AVAILABILITY",
            "startTime": 1_700_000_000_000,
            "affectedEntities": [
                {"entityId": {"type": "HOST"}, "name": "Host"},
                {
                    "entityId": {"type": "SYNTHETIC_TEST"},
                    "name": "FileNet DocStore Flow",
                },
            ],
            "evidenceDetails": {
                "details": [
                    {
                        "data": [
                            {
                                "key": "dt.synthetic.step.name",
                                "value": "Error on Login Page - Click on Username",
                            }
                        ]
                    }
                ]
            },
        }

        parsed = DynatraceClient._to_problem(object.__new__(DynatraceClient), payload)

        self.assertTrue(parsed.is_synthetic)
        self.assertEqual(parsed.monitor_name, "FileNet DocStore Flow")
        self.assertEqual(parsed.synthetic_step_name, "Error on Login Page - Click on Username")

    def test_all_non_nullable_activation_properties_have_defaults(self):
        schema_path = Path(__file__).parents[1] / "extension" / "activationSchema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        missing_defaults = []

        for type_name, type_definition in schema["types"].items():
            for property_name, property_definition in type_definition.get("properties", {}).items():
                if property_definition.get("nullable") is False and "default" not in property_definition:
                    missing_defaults.append(f"{type_name}.{property_name}")

        self.assertEqual(missing_defaults, [])

    def test_disabled_synthetic_problem_is_ignored(self):
        instance, normal_cache, synthetic_cache, sms = self.make_engine(activation_config())

        instance.process([problem(entity_type="HTTP_CHECK")])

        self.assertEqual(sms.messages, [])
        self.assertEqual(normal_cache.cache, {})
        self.assertEqual(synthetic_cache.cache, {})
        self.assertFalse((self.cache_path / "synthetic_problem_cache.json").exists())

    def test_standard_problem_keeps_existing_routing_and_uses_normal_cache(self):
        instance, normal_cache, synthetic_cache, sms = self.make_engine(activation_config())

        instance.process([problem()])

        self.assertEqual(normal_cache.get("P-1").escalation_level, "L3")
        self.assertEqual(synthetic_cache.cache, {})
        self.assertEqual(sms.messages[0].recipients, ["3333333333"])
        self.assertIn("Incident: Existing incident", sms.messages[0].message)
        self.assertIn("Severity: AVAILABILITY", sms.messages[0].message)
        self.assertIn("Status: OPEN L3", sms.messages[0].message)
        self.assertIn("Entity: FileNet DocStore Flow", sms.messages[0].message)

    def test_synthetic_uses_dedicated_settings_and_starts_at_l1(self):
        config = activation_config(syntheticEnabled=True, syntheticUseSameEscalation=False)
        instance, normal_cache, synthetic_cache, sms = self.make_engine(config)

        instance.process([problem(entity_type="SYNTHETIC_TEST")])

        self.assertEqual(normal_cache.cache, {})
        self.assertEqual(synthetic_cache.get("P-1").escalation_level, "L1")
        self.assertEqual(sms.messages[0].recipients, ["4444444444"])
        self.assertIn("Incident: Error on Login Page - Click on Username", sms.messages[0].message)
        self.assertIn("Status: OPEN L1", sms.messages[0].message)
        self.assertIn("Flow Name: FileNet DocStore Flow", sms.messages[0].message)

    def test_synthetic_shared_settings_reuse_recipients_and_delays(self):
        started = datetime.now(UTC) - timedelta(minutes=35)
        config = activation_config(syntheticEnabled=True, syntheticUseSameEscalation=True)
        instance, _, synthetic_cache, sms = self.make_engine(config)
        synthetic_problem = problem(entity_type="HTTP_CHECK", start_time=started)

        instance.process([synthetic_problem])
        instance.process([synthetic_problem])

        self.assertEqual(synthetic_cache.get("P-1").escalation_level, "L2")
        self.assertEqual(
            [message.recipients for message in sms.messages],
            [["1111111111"], ["2222222222"]],
        )
        self.assertIn("Status: OPEN L2", sms.messages[1].message)

    def test_closed_synthetic_status_has_no_escalation_level(self):
        config = activation_config(syntheticEnabled=True, syntheticUseSameEscalation=False)
        instance, _, _, sms = self.make_engine(config)
        opened = problem(entity_type="SYNTHETIC_TEST")
        instance.process([opened])

        closed = problem(
            entity_type="SYNTHETIC_TEST",
            status="CLOSED",
            start_time=opened.start_time,
            end_time=datetime.now(UTC),
        )
        instance.process([closed])

        self.assertIn("Status: CLOSED", sms.messages[-1].message)
        self.assertNotIn("Status: CLOSED L1", sms.messages[-1].message)

    def test_existing_payload_includes_level_for_open_and_not_closed(self):
        open_message = SmsFormatter.build(problem(), NOTIFICATION_OPEN, "L3")
        closed_problem = problem(status="CLOSED", end_time=datetime.now(UTC))
        closed_message = SmsFormatter.build(closed_problem, NOTIFICATION_CLOSED, "L3")

        self.assertIn("Status: OPEN L3", open_message)
        self.assertIn("Status: CLOSED", closed_message)
        self.assertNotIn("Status: CLOSED L3", closed_message)


if __name__ == "__main__":
    unittest.main()
