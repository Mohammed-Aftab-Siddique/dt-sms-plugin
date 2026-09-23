import time
from pathlib import Path

from dynatrace_extension import Extension, Status, StatusValue

from dt_sms_plugin.cache.cache_manager import CacheManager
from dt_sms_plugin.clients.dynatrace_client import DynatraceClient
from dt_sms_plugin.clients.sms_client import SmsClient
from dt_sms_plugin.config.settings import load_settings
from dt_sms_plugin.config.validator import validate_settings
from dt_sms_plugin.metrics.publisher import MetricsPublisher
from dt_sms_plugin.processing.sms_engine import SmsEngine
from dt_sms_plugin.utils.constants import NORMAL_CACHE_FILE_NAME, SYNTHETIC_CACHE_FILE_NAME
from dt_sms_plugin.utils.logger import log_error, log_info


class ExtensionImpl(Extension):
    def initialize(self) -> None:
        try:
            log_info(self.logger, "Initializing DT SMS Plugin...")

            self.settings = load_settings(self.activation_config)

            validate_settings(self.settings)

            self.metrics = MetricsPublisher(self)

            self.cache = CacheManager(Path(), NORMAL_CACHE_FILE_NAME)
            self.synthetic_cache = CacheManager(Path(), SYNTHETIC_CACHE_FILE_NAME)
            self.cache.load()
            self.synthetic_cache.load()

            self.dt_client = DynatraceClient(
                tenant_url=self.settings.dynatrace.url,
                api_token=self.settings.dynatrace.api_token,
            )

            self.sms_client = SmsClient(
                logger=self.logger,
                url=self.settings.sms_api.url,
                username=self.settings.sms_api.username,
                password=self.settings.sms_api.password,
                timeout=self.settings.sms_api.timeout,
                dry_run=self.settings.dry_run,
                payload_logging=self.settings.payload_logging,
            )

            self.engine = SmsEngine(
                settings=self.settings,
                cache=self.cache,
                synthetic_cache=self.synthetic_cache,
                sms_client=self.sms_client,
            )

            log_info(self.logger, "Initialization completed.")

        except Exception:
            self.logger.exception("Initialization failed")
            raise

    def query(self):
        start = time.perf_counter()

        try:
            log_info(self.logger, "Query started.")

            if self.dt_client is None:
                return

            problems = self.dt_client.fetch_problems(
                lookback_minutes=self.settings.lookback_window,
                management_zones=[mz.name for mz in self.settings.management_zones],
                max_problems=self.settings.max_problems_per_execution,
            )

            self.engine.process(problems)

            elapsed_ms = (time.perf_counter() - start) * 1000

            self.metrics.processing_time(elapsed_ms)
            self.metrics.problems_processed(len(problems))
            self.metrics.execution_health(True)

            log_info(
                self.logger,
                f"Processed {len(problems)} problems in {elapsed_ms:.2f} ms.",
            )

        except Exception as exc:
            self.metrics.execution_health(False)
            log_error(self.logger, str(exc))
            raise

    def fastcheck(self) -> Status:
        return Status(StatusValue.OK)


def main():
    ExtensionImpl(name="dt_sms_plugin").run()


if __name__ == "__main__":
    main()
