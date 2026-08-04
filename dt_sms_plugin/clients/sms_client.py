from __future__ import annotations

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

        self._session = requests.Session()
        self._session.auth = (username, password)
        self._session.headers.update(
            {
                "Content-Type": "application/json",
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

        payload = self._build_payload(sms)

        try:
            response = self._session.post(
                self._url,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()

        except requests.RequestException as exc:
            raise SmsClientError(f"Failed to send SMS: {exc}") from exc

    @staticmethod
    def _build_payload(sms: SmsMessage) -> dict:
        """
        Temporary payload.

        Replace this once the SMS API contract is finalized.
        """
        return {
            "recipients": sms.recipients,
            "message": sms.message,
            "problemId": sms.problem_id,
            "notificationType": sms.notification_type,
        }
