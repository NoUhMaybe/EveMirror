from datetime import UTC, datetime


class ServiceError(Exception):
    def __init__(self, code: str, message: str, details=None):
        self.code, self.message, self.details = code, message, details
        super().__init__(code)


def utc_now():
    return datetime.now(UTC)


def millis(instant: datetime) -> int:
    if instant.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    return int(instant.timestamp() * 1000)


def iso(value: int | None):
    return datetime.fromtimestamp(value / 1000, UTC).isoformat() if value is not None else None
