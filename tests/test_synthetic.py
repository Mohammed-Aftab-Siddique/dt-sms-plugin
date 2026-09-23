import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dt_sms_plugin.cache.cache_manager import CacheManager
from dt_sms_plugin.clients.dynatrace_client import DynatraceClient
from dt_sms_plugin.config.settings import load_settings
from dt_sms_plugin.config.validator import validate_settings
from dt_sms_plugin.models.cache import CacheEntry
from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.processing.sms_engine import SmsEngine
from dt_sms_plugin.processing.sms_formatter import SmsFormatter
from dt_sms_plugin.utils.constants import NOTIFICATION_CLOSED, NOTIFICATION_OPEN
from dt_sms_plugin.utils.exceptions import ConfigurationError


class FakeSmsClient:
    def __init__(self):
        self.messages = []

    def send(self, sms):
        self.messages.append(sms)


class FakeResponse:
    def __init__(self, payload, url="https://example.live.dynatrace.com/api/v2/problems"):
        self._payload = payload
        self.url = url
        self.ok = True
        self.status_code = 200
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)


def activation_config(**overrides):
    config = {
        "pollingInterval": 60,
        "lookbackWindow": 5,
        "maxProblemsPerExecution": 100,
        "managementZone": "FileNet",
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


def problem(
    *,
    problem_id="P-1",
    entity_type="HOST",
    status="OPEN",
    severity="AVAILABILITY",
    start_time=None,
    end_time=None,
):
    return Problem(
        problem_id=problem_id,
        display_id=problem_id,
        title="Existing incident",
        status=status,
        severity=severity,
        impact_level="APPLICATION",
        entity_type=entity_type,
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
                        "data": {
                            "properties": [
                                {
                                    "key": "dt.synthetic.step.name",
                                    "value": "Error on Login Page - Click on Username",
                                }
                            ]
                        }
                    }
                ]
            },
        }

        parsed = DynatraceClient._to_problem(object.__new__(DynatraceClient), payload)

        self.assertTrue(parsed.is_synthetic)
        self.assertEqual(parsed.monitor_name, "FileNet DocStore Flow")
        self.assertEqual(parsed.synthetic_step_name, "Error on Login Page - Click on Username")

    def test_problem_list_fetches_details_only_for_synthetic_problems(self):
        standard_data = {
            "problemId": "STANDARD-1",
            "status": "OPEN",
            "severityLevel": "INFO",
            "startTime": 1_700_000_000_000,
            "affectedEntities": [{"entityId": {"type": "HOST"}, "name": "Host"}],
        }
        synthetic_data = {
            "problemId": "SYNTHETIC-1",
            "status": "OPEN",
            "severityLevel": "AVAILABILITY",
            "startTime": 1_700_000_000_000,
            "affectedEntities": [{"entityId": {"type": "SYNTHETIC_TEST"}, "name": "Synthetic Monitor"}],
        }
        synthetic_details = {
            **synthetic_data,
            "evidenceDetails": {
                "details": [
                    {
                        "data": {
                            "properties": [
                                {
                                    "key": "dt.synthetic.step.name",
                                    "value": "Login step",
                                }
                            ]
                        }
                    }
                ]
            },
        }
        session = FakeSession(
            [
                FakeResponse({"problems": [standard_data, synthetic_data]}),
                FakeResponse(synthetic_details),
            ]
        )
        client = object.__new__(DynatraceClient)
        client._base_url = "https://example.live.dynatrace.com"
        client._timeout = 30
        client._session = session

        problems = client.fetch_problems(5, "FileNet", 100, fetch_synthetic_details=True)

        self.assertEqual(len(problems), 2)
        self.assertEqual(problems[0].synthetic_step_name, "")
        self.assertEqual(problems[1].synthetic_step_name, "Login step")
        self.assertEqual(session.calls[0]["params"]["pageSize"], 100)
        self.assertNotIn("fields", session.calls[0]["params"])
        self.assertEqual(
            session.calls[0]["params"]["problemSelector"],
            'status("open"),managementZones("FileNet")',
        )
        self.assertEqual(
            session.calls[1],
            {
                "url": "https://example.live.dynatrace.com/api/v2/problems/SYNTHETIC-1",
                "params": {"fields": "evidenceDetails"},
                "timeout": 30,
            },
        )

    def test_disabled_synthetic_handling_makes_no_detail_request(self):
        synthetic_data = {
            "problemId": "SYNTHETIC-1",
            "status": "OPEN",
            "severityLevel": "AVAILABILITY",
            "startTime": 1_700_000_000_000,
            "affectedEntities": [{"entityId": {"type": "HTTP_CHECK"}, "name": "HTTP Monitor"}],
        }
        session = FakeSession([FakeResponse({"problems": [synthetic_data]})])
        client = object.__new__(DynatraceClient)
        client._base_url = "https://example.live.dynatrace.com"
        client._timeout = 30
        client._session = session

        problems = client.fetch_problems(5, "FileNet", 100, fetch_synthetic_details=False)

        self.assertEqual(len(problems), 1)
        self.assertEqual(len(session.calls), 1)
        self.assertNotIn("fields", session.calls[0]["params"])
        self.assertEqual(problems[0].synthetic_step_name, "")

    def test_all_non_nullable_activation_properties_have_defaults(self):
        schema_path = Path(__file__).parents[1] / "extension" / "activationSchema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        missing_defaults = []

        for type_name, type_definition in schema["types"].items():
            for property_name, property_definition in type_definition.get("properties", {}).items():
                if property_definition.get("nullable") is False and "default" not in property_definition:
                    missing_defaults.append(f"{type_name}.{property_name}")

        self.assertEqual(missing_defaults, [])

    def test_activation_schema_requires_one_management_zone_text_value(self):
        schema_path = Path(__file__).parents[1] / "extension" / "activationSchema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        for activation_type in ("pythonRemote", "pythonLocal"):
            properties = schema["types"][activation_type]["properties"]
            management_zone = properties["managementZone"]

            self.assertNotIn("managementZones", properties)
            self.assertEqual(management_zone["type"], "text")
            self.assertFalse(management_zone["nullable"])
            self.assertIn("default", management_zone)

    def test_management_zone_is_trimmed_and_required(self):
        settings = load_settings(activation_config(managementZone="  FileNet  "))
        self.assertEqual(settings.management_zone, "FileNet")

        empty_settings = load_settings(activation_config(managementZone="   "))
        with self.assertRaisesRegex(ConfigurationError, "Management Zone is required"):
            validate_settings(empty_settings)

        missing_config = activation_config()
        del missing_config["managementZone"]
        with self.assertRaisesRegex(ConfigurationError, "Management Zone is required"):
            validate_settings(load_settings(missing_config))

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
        self.assertIn("Application: FileNet", sms.messages[0].message)
        self.assertNotIn("Application: API Response Zone", sms.messages[0].message)
        self.assertIn("Severity: AVAILABILITY", sms.messages[0].message)
        self.assertIn("Status: OPEN L3", sms.messages[0].message)
        self.assertIn("Entity: FileNet DocStore Flow", sms.messages[0].message)

    def test_standard_initial_level_uses_severity(self):
        scenarios = (
            ("INFO", "L1", "1111111111"),
            ("ERROR", "L2", "2222222222"),
            ("AVAILABILITY", "L3", "3333333333"),
        )

        for severity, expected_level, expected_recipient in scenarios:
            with self.subTest(severity=severity):
                instance, normal_cache, _, sms = self.make_engine(activation_config())
                standard_problem = problem(problem_id=f"P-{expected_level}", severity=severity)

                instance.process([standard_problem])

                self.assertEqual(
                    normal_cache.get(standard_problem.problem_id).escalation_level,
                    expected_level,
                )
                self.assertEqual(sms.messages[0].recipients, [expected_recipient])
                self.assertIn(f"Status: OPEN {expected_level}", sms.messages[0].message)

    def test_standard_delay_escalation_waits_then_reaches_l2_and_l3(self):
        started = datetime.now(UTC) - timedelta(minutes=5)
        instance, normal_cache, _, sms = self.make_engine(activation_config())
        standard_problem = problem(severity="INFO", start_time=started)

        instance.process([standard_problem])
        instance.process([standard_problem])
        self.assertEqual(len(sms.messages), 1)
        self.assertEqual(normal_cache.get("P-1").escalation_level, "L1")

        normal_cache.get("P-1").start_time = datetime.now(UTC) - timedelta(minutes=35)
        instance.process([standard_problem])
        self.assertEqual(normal_cache.get("P-1").escalation_level, "L2")
        self.assertEqual(sms.messages[-1].recipients, ["2222222222"])

        normal_cache.get("P-1").start_time = datetime.now(UTC) - timedelta(minutes=65)
        instance.process([standard_problem])
        self.assertEqual(normal_cache.get("P-1").escalation_level, "L3")
        self.assertEqual(sms.messages[-1].recipients, ["3333333333"])

    def test_synthetic_uses_dedicated_settings_and_starts_at_l1(self):
        config = activation_config(syntheticEnabled=True, syntheticUseSameEscalation=False)
        instance, normal_cache, synthetic_cache, sms = self.make_engine(config)

        instance.process([problem(entity_type="SYNTHETIC_TEST")])

        self.assertEqual(normal_cache.cache, {})
        self.assertEqual(synthetic_cache.get("P-1").escalation_level, "L1")
        self.assertEqual(sms.messages[0].recipients, ["4444444444"])
        self.assertIn("Application: FileNet", sms.messages[0].message)
        self.assertIn("Incident: Error on Login Page - Click on Username", sms.messages[0].message)
        self.assertIn("Status: OPEN L1", sms.messages[0].message)
        self.assertIn("Flow Name: FileNet DocStore Flow", sms.messages[0].message)

    def test_synthetic_initial_level_ignores_severity(self):
        config = activation_config(syntheticEnabled=True, syntheticUseSameEscalation=False)

        for severity in ("INFO", "ERROR", "AVAILABILITY"):
            with self.subTest(severity=severity):
                instance, _, synthetic_cache, sms = self.make_engine(config)
                synthetic_problem = problem(
                    problem_id=f"S-{severity}",
                    entity_type="SYNTHETIC_TEST",
                    severity=severity,
                )

                instance.process([synthetic_problem])

                self.assertEqual(
                    synthetic_cache.get(synthetic_problem.problem_id).escalation_level,
                    "L1",
                )
                self.assertEqual(sms.messages[0].recipients, ["4444444444"])
                self.assertIn("Status: OPEN L1", sms.messages[0].message)

    def test_synthetic_dedicated_delays_wait_then_reach_l2_and_l3(self):
        started = datetime.now(UTC) - timedelta(minutes=5)
        config = activation_config(syntheticEnabled=True, syntheticUseSameEscalation=False)
        instance, _, synthetic_cache, sms = self.make_engine(config)
        synthetic_problem = problem(entity_type="HTTP_CHECK", start_time=started)

        instance.process([synthetic_problem])
        instance.process([synthetic_problem])
        self.assertEqual(len(sms.messages), 1)
        self.assertEqual(synthetic_cache.get("P-1").escalation_level, "L1")

        synthetic_cache.get("P-1").start_time = datetime.now(UTC) - timedelta(minutes=15)
        instance.process([synthetic_problem])
        self.assertEqual(synthetic_cache.get("P-1").escalation_level, "L2")
        self.assertEqual(sms.messages[-1].recipients, ["5555555555"])

        synthetic_cache.get("P-1").start_time = datetime.now(UTC) - timedelta(minutes=25)
        instance.process([synthetic_problem])
        self.assertEqual(synthetic_cache.get("P-1").escalation_level, "L3")
        self.assertEqual(sms.messages[-1].recipients, ["6666666666"])

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

    def test_closure_notifications_are_cumulative_for_both_problem_types(self):
        expected_recipients = {
            "L1": ["1111111111"],
            "L2": ["1111111111", "2222222222"],
            "L3": ["1111111111", "2222222222", "3333333333"],
        }

        for entity_type in ("HOST", "SYNTHETIC_TEST"):
            for level, recipients in expected_recipients.items():
                with self.subTest(entity_type=entity_type, level=level):
                    config = activation_config(syntheticEnabled=True, syntheticUseSameEscalation=True)
                    instance, normal_cache, synthetic_cache, sms = self.make_engine(config)
                    selected_cache = synthetic_cache if entity_type == "SYNTHETIC_TEST" else normal_cache
                    closed_problem = problem(
                        problem_id=f"C-{entity_type}-{level}",
                        entity_type=entity_type,
                        status="CLOSED",
                        end_time=datetime.now(UTC),
                    )
                    selected_cache.put(
                        CacheEntry(
                            problem_id=closed_problem.problem_id,
                            status="OPEN",
                            start_time=closed_problem.start_time,
                            escalation_level=level,
                            last_notification_type="OPEN",
                            last_updated=datetime.now(UTC),
                        )
                    )

                    instance.process([closed_problem])

                    self.assertEqual(
                        [message.recipients[0] for message in sms.messages],
                        recipients,
                    )
                    for message in sms.messages:
                        self.assertIn("Status: CLOSED", message.message)
                        self.assertNotIn("Status: CLOSED L", message.message)

    def test_existing_payload_includes_level_for_open_and_not_closed(self):
        open_message = SmsFormatter.build(problem(), NOTIFICATION_OPEN, "L3")
        closed_problem = problem(status="CLOSED", end_time=datetime.now(UTC))
        closed_message = SmsFormatter.build(closed_problem, NOTIFICATION_CLOSED, "L3")

        self.assertIn("Status: OPEN L3", open_message)
        self.assertIn("Status: CLOSED", closed_message)
        self.assertNotIn("Status: CLOSED L3", closed_message)


if __name__ == "__main__":
    unittest.main()
