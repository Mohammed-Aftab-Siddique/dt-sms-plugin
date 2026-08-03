from dataclasses import dataclass


@dataclass(slots=True)
class SmsMessage:
    recipients: list[str]

    problem_id: str

    notification_type: str

    message: str
