from datetime import datetime


def _timestamp() -> str:
    """Return current local timestamp for console logging."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_debug(logger, message: str) -> None:
    """Log a DEBUG message to console and Dynatrace."""
    print(f"[{_timestamp()}] {message}")
    logger.debug(message)


def log_info(logger, message: str) -> None:
    """Log an INFO message to console and Dynatrace."""
    print(f"[{_timestamp()}] {message}")
    logger.info(message)


def log_warning(logger, message: str) -> None:
    """Log a WARNING message to console and Dynatrace."""
    print(f"[{_timestamp()}] {message}")
    logger.warning(message)


def log_error(logger, message: str) -> None:
    """Log an ERROR message to console and Dynatrace."""
    print(f"[{_timestamp()}] {message}")
    logger.error(message)
