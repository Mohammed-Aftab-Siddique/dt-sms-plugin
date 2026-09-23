from __future__ import annotations

from datetime import UTC, datetime

import requests

from dt_sms_plugin.models.problem import Problem
from dt_sms_plugin.utils.constants import SYNTHETIC_ENTITY_TYPES, SYNTHETIC_STEP_NAME_KEY
from dt_sms_plugin.utils.exceptions import DynatraceClientError


class DynatraceClient:
    def __init__(
        self,
        tenant_url: str,
        api_token: str,
        timeout: int = 30,
    ):
        self._base_url = tenant_url.rstrip("/")
        self._timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Api-Token {api_token}",
                "Accept": "application/json",
            }
        )

    def fetch_problems(
        self,
        lookback_minutes: int,
        management_zone: str,
        max_problems: int | None,
        fetch_synthetic_details: bool = False,
    ) -> list[Problem]:
        params = {
            "pageSize": 100,
            "from": f"-{lookback_minutes}m",
            "to": "now",
        }

        selectors = ['status("open")']

        selectors.append(f'managementZones("{management_zone}")')

        params["problemSelector"] = ",".join(selectors)

        url = f"{self._base_url}/api/v2/problems"

        problems: list[Problem] = []
        next_page_key = None

        while True:
            request_params = {"nextPageKey": next_page_key} if next_page_key else params

            try:
                response = self._session.get(
                    url,
                    params=request_params,
                    timeout=self._timeout,
                )

                if not response.ok:
                    raise DynatraceClientError(
                        f"HTTP {response.status_code}\nURL: {response.url}\nResponse: {response.text}"
                    )

            except requests.RequestException as exc:
                raise DynatraceClientError(f"Failed to fetch problems: {exc}") from exc

            payload = response.json()

            for problem_data in payload.get("problems", []):
                if max_problems is not None and len(problems) >= max_problems:
                    return problems

                if fetch_synthetic_details and self._is_synthetic_problem(problem_data):
                    problem_data = self._fetch_problem_details(problem_data["problemId"])

                problems.append(self._to_problem(problem_data))

            if max_problems is not None and len(problems) >= max_problems:
                return problems

            next_page_key = payload.get("nextPageKey")

            if not next_page_key:
                break

        return problems

    def _fetch_problem_details(self, problem_id: str) -> dict:
        url = f"{self._base_url}/api/v2/problems/{problem_id}"

        try:
            response = self._session.get(
                url,
                params={"fields": "evidenceDetails"},
                timeout=self._timeout,
            )

            if not response.ok:
                raise DynatraceClientError(
                    f"HTTP {response.status_code}\nURL: {response.url}\nResponse: {response.text}"
                )

        except requests.RequestException as exc:
            raise DynatraceClientError(f"Failed to fetch problem details: {exc}") from exc

        return response.json()

    @staticmethod
    def _is_synthetic_problem(data: dict) -> bool:
        return any(
            entity.get("entityId", {}).get("type", "").strip().upper() in SYNTHETIC_ENTITY_TYPES
            for entity in data.get("affectedEntities", [])
        )

    def _to_problem(
        self,
        data: dict,
    ) -> Problem:
        affected_entities = data.get("affectedEntities", [])
        synthetic_entity = next(
            (
                entity
                for entity in affected_entities
                if entity.get("entityId", {}).get("type", "").strip().upper() in SYNTHETIC_ENTITY_TYPES
            ),
            None,
        )
        primary_entity = synthetic_entity or (affected_entities[0] if affected_entities else {})

        return Problem(
            problem_id=data["problemId"],
            display_id=data.get("displayId", ""),
            title=data.get("title", ""),
            status=data.get("status", "").strip().upper(),
            severity=data.get("severityLevel", "").strip().upper(),
            impact_level=data.get("impactLevel", ""),
            entity_type=primary_entity.get("entityId", {}).get("type", "").strip().upper(),
            start_time=datetime.fromtimestamp(
                data["startTime"] / 1000,
                tz=UTC,
            ),
            end_time=(
                datetime.fromtimestamp(
                    data["endTime"] / 1000,
                    tz=UTC,
                )
                if data.get("endTime")
                else None
            ),
            affected_entities=[entity.get("name", "") for entity in affected_entities],
            monitor_name=primary_entity.get("name", "").strip(),
            synthetic_step_name=self._get_synthetic_step_name(data),
        )

    @staticmethod
    def _get_synthetic_step_name(data: dict) -> str:
        details = data.get("evidenceDetails", {}).get("details", [])

        for detail in details:
            evidence_data = detail.get("data", {})
            properties = (
                evidence_data.get("properties", []) if isinstance(evidence_data, dict) else evidence_data
            )

            for item in properties:
                if item.get("key") == SYNTHETIC_STEP_NAME_KEY:
                    return str(item.get("value", "")).strip()

        return ""
