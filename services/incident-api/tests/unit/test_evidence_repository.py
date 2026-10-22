from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.database.repositories import SqlEvidenceRepository
from app.errors import AppError


def settings(max_lookback_days: int = 7) -> Settings:
    return Settings(
        ENVIRONMENT="Development",
        DATABASE_URL="postgresql://example.invalid/aiops",
        JWT_SECRET="test-secret-with-at-least-32-characters",
        MAX_LOOKBACK_DAYS=max_lookback_days,
    )


def test_time_window_accepts_value_within_configured_limit() -> None:
    repository = SqlEvidenceRepository(Mock(), settings())

    assert repository._parse_time_window("last 2 hours") is not None


def test_missing_time_window_uses_configured_default() -> None:
    repository = SqlEvidenceRepository(Mock(), settings())
    before = datetime.now(UTC) - timedelta(minutes=31)
    after = datetime.now(UTC) - timedelta(minutes=29)

    since = repository._parse_time_window(None)

    assert before < since < after


def test_time_window_rejects_value_beyond_configured_limit() -> None:
    repository = SqlEvidenceRepository(Mock(), settings(max_lookback_days=1))

    with pytest.raises(AppError, match="timeWindow cannot exceed 1 days"):
        repository._parse_time_window("last 25 hours")


def test_time_window_rejects_unsupported_format() -> None:
    repository = SqlEvidenceRepository(Mock(), settings())

    with pytest.raises(AppError, match="timeWindow must use a format"):
        repository._parse_time_window("since deployment")
