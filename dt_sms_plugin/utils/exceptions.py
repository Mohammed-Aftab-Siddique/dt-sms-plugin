class ConfigurationError(Exception):
    """Raised when the extension configuration is invalid."""


class CacheError(Exception):
    """Raised when cache operations fail."""


class DynatraceClientError(Exception):
    """Raised when the Dynatrace API request fails."""


class SmsClientError(Exception):
    """Raised when the SMS API request fails."""
