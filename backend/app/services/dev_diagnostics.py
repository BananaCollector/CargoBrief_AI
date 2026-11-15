import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock


_MAX_RECENT_ERRORS = 20
_recent_errors: deque[dict[str, str]] = deque(maxlen=_MAX_RECENT_ERRORS)
_lock = Lock()


class RecentErrorHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.WARNING:
            return
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        with _lock:
            _recent_errors.append(entry)


def get_recent_errors() -> list[dict[str, str]]:
    with _lock:
        return list(reversed(_recent_errors))


_handler = RecentErrorHandler(level=logging.WARNING)
logging.getLogger().addHandler(_handler)
