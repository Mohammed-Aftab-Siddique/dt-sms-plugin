# =============================================================================
# Cache
# =============================================================================

CACHE_FILE_NAME = "problem_cache.json"
CACHE_VERSION = 1

CACHE_KEY_PROBLEMS = "problems"

CACHE_KEY_PROBLEM_ID = "problem_id"
CACHE_KEY_STATUS = "status"
CACHE_KEY_START_TIME = "start_time"
CACHE_KEY_LAST_UPDATE_TIME = "last_update_time"
CACHE_KEY_ESCALATION_LEVEL = "escalation_level"
CACHE_KEY_LAST_NOTIFICATION_TYPE = "last_notification_type"

# =============================================================================
# Problem Status
# =============================================================================

STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"

# =============================================================================
# Notification Types
# =============================================================================

NOTIFICATION_OPEN = "OPEN"
NOTIFICATION_ESCALATION = "ESCALATION"
NOTIFICATION_CLOSED = "CLOSED"

# =============================================================================
# Escalation Levels
# =============================================================================

LEVEL_L1 = "L1"
LEVEL_L2 = "L2"
LEVEL_L3 = "L3"

ESCALATION_LEVELS = (
    LEVEL_L1,
    LEVEL_L2,
    LEVEL_L3,
)

# =============================================================================
# Severity Levels
# =============================================================================

SEVERITY_CUSTOM = "CUSTOM"
SEVERITY_INFO = "INFO"
SEVERITY_ERROR = "ERROR"
SEVERITY_SLOWDOWN = "SLOWDOWN"
SEVERITY_AVAILABILITY = "AVAILABILITY"
SEVERITY_MONITORING_UNAVAILABLE = "MONITORING_UNAVAILABLE"

SEVERITIES = (
    SEVERITY_CUSTOM,
    SEVERITY_INFO,
    SEVERITY_ERROR,
    SEVERITY_SLOWDOWN,
    SEVERITY_AVAILABILITY,
    SEVERITY_MONITORING_UNAVAILABLE,
)

# =============================================================================
# Metric Keys
# =============================================================================

METRIC_PROCESSING_TIME = "custom.sms.processing.time"
METRIC_PROBLEMS_FETCHED = "custom.sms.problems.fetched"
METRIC_SMS_SENT = "custom.sms.sms.sent"
METRIC_HEALTH = "custom.sms.health"

# =============================================================================
# HTTP
# =============================================================================

DEFAULT_HTTP_TIMEOUT = 30

# =============================================================================
# Logging Components
# =============================================================================

LOG_CONFIG = "[CONFIG]"
LOG_CACHE = "[CACHE]"
LOG_DT = "[DT]"
LOG_SMS = "[SMS]"
LOG_ENGINE = "[ENGINE]"
LOG_ESCALATION = "[ESCALATION]"
LOG_METRICS = "[METRICS]"
