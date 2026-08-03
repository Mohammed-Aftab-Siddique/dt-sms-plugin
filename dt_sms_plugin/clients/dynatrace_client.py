from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from dt_sms_plugin.models.problem import Problem
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
        management_zones: list[str],
        max_problems: int | None,
    ) -> list[Problem]:
        from_time = (datetime.now(UTC) - timedelta(minutes=lookback_minutes)).isoformat()

        params = {
            "from": from_time,
            "pageSize": 100,
        }

        if management_zones:
            params["managementZones"] = ",".join(management_zones)

        url = f"{self._base_url}/api/v2/problems"

        problems = []
        next_page_key = None

        while True:
            request_params = {"nextPageKey": next_page_key} if next_page_key else params

            try:
                response = self._session.get(
                    url,
                    params=request_params,
                    timeout=self._timeout,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise DynatraceClientError(f"Failed to fetch problems: {exc}") from exc

            payload = response.json()

            problems.extend(self._to_problem(problem) for problem in payload.get("problems", []))

            if max_problems is not None and len(problems) >= max_problems:
                return problems[:max_problems]

            next_page_key = payload.get("nextPageKey")

            if not next_page_key:
                break

        return problems

    def _to_problem(
        self,
        data: dict,
    ) -> Problem:
        return Problem(
            problem_id=data["problemId"],
            display_id=data.get("displayId", ""),
            title=data.get("title", ""),
            status=data.get("status", "").strip().upper(),
            severity=data.get(
                "severityLevel",
                "",
            )
            .strip()
            .upper(),
            impact_level=data.get(
                "impactLevel",
                "",
            ),
            entity_type=(data.get("affectedEntities", [{}])[0].get("entityId", {}).get("type", "")),
            management_zones=[mz["name"] for mz in data.get("managementZones", [])],
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
            affected_entities=[
                entity["name"]
                for entity in data.get(
                    "affectedEntities",
                    [],
                )
            ],
        )
