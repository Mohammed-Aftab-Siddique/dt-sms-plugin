from __future__ import annotations

import json

import requests

from dt_sms_plugin.models.sms import SmsMessage
from dt_sms_plugin.utils.exceptions import SmsClientError
from dt_sms_plugin.utils.logger import log_info


class SmsClient:
    def __init__(
        self,
        logger,
        url: str,
        username: str,
        password: str,
        timeout: int,
        dry_run: bool,
    ):
        self._url = url
        self._timeout = timeout
        self._dry_run = dry_run
        self._logger = logger
        self._username = username
        self._password = password

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        )

    def send(self, sms: SmsMessage) -> None:
        if self._dry_run:
            log_info(
                self._logger,
                f"DRY RUN\n{sms.message}",
            )
            return

        try:
            for recipient in sms.recipients:
                payload = self._build_payload(sms, recipient)

                response = self._session.post(
                    self._url,
                    data=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()

        except requests.RequestException as exc:
            raise SmsClientError(f"Failed to send SMS: {exc}") from exc

    def _build_payload(self, sms: SmsMessage, recipient: str) -> dict:
        auth = {
            "user": self._username,
            "password": self._password,
            "appName": "Ecamptest",
        }

        json_string = {
            "campaign": "Dynatrace",
            "dynParam": [
                sms.message,
                "",
                "",
                recipient,
            ],
        }

        return {
            "auth": json.dumps(auth, separators=(",", ":")),
            "jsonString": json.dumps(json_string, separators=(",", ":")),
        }
