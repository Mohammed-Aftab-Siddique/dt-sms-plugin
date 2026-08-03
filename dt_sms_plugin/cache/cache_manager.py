from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from dt_sms_plugin.models.cache import CacheEntry
from dt_sms_plugin.utils.constants import CACHE_FILE_NAME
from dt_sms_plugin.utils.exceptions import CacheError


class CacheManager:
    def __init__(self, cache_dir: Path):
        self._cache_file = cache_dir / CACHE_FILE_NAME
        self._cache: dict[str, CacheEntry] = {}

    @property
    def cache(self) -> dict[str, CacheEntry]:
        return self._cache

    def load(self) -> None:
        if not self._cache_file.exists():
            self._cache = {}
            return

        try:
            with self._cache_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            self._cache = {
                problem_id: CacheEntry(
                    problem_id=value["problem_id"],
                    status=value["status"],
                    start_time=datetime.fromisoformat(value["start_time"]),
                    escalation_level=value["escalation_level"],
                    last_notification_type=value["last_notification_type"],
                    last_updated=datetime.fromisoformat(value["last_updated"]),
                )
                for problem_id, value in data.items()
            }

        except Exception as exc:
            raise CacheError(f"Failed to load cache: {exc}") from exc

    def save(self) -> None:
        try:
            self._cache_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            data = {}

            for problem_id, entry in self._cache.items():
                item = asdict(entry)

                item["start_time"] = entry.start_time.isoformat()
                item["last_updated"] = entry.last_updated.isoformat()

                data[problem_id] = item

            with self._cache_file.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    data,
                    file,
                    indent=2,
                    sort_keys=True,
                )

        except Exception as exc:
            raise CacheError(f"Failed to save cache: {exc}") from exc

    def get(
        self,
        problem_id: str,
    ) -> CacheEntry | None:
        return self._cache.get(problem_id)

    def put(
        self,
        entry: CacheEntry,
    ) -> None:
        self._cache[entry.problem_id] = entry

    def remove(
        self,
        problem_id: str,
    ) -> None:
        self._cache.pop(problem_id, None)
