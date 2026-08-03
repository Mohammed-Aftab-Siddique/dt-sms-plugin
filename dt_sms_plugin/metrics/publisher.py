from dynatrace_extension import Extension


class MetricsPublisher:
    def __init__(self, extension: Extension):
        self._extension = extension

    def processing_time(self, milliseconds: float) -> None:
        self._extension.report_metric(
            "custom.sms.processing.time",
            milliseconds,
        )

    def sms_sent(self, count: int = 1) -> None:
        self._extension.report_metric(
            "custom.sms.sent",
            count,
        )

    def problems_processed(self, count: int) -> None:
        self._extension.report_metric(
            "custom.sms.problems.processed",
            count,
        )

    def execution_health(self, healthy: bool) -> None:
        self._extension.report_metric(
            "custom.sms.health",
            1 if healthy else 0,
        )
