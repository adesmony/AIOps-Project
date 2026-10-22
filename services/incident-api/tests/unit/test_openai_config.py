import pytest
from pydantic import ValidationError

from app.config import Settings


def settings(**overrides):
    return Settings(
        _env_file=None,
        ENVIRONMENT="Development",
        DATABASE_URL="postgresql://unused/unused",
        JWT_SECRET="test-secret-that-is-at-least-32-characters",
        **overrides,
    )


def test_local_default_is_offline(monkeypatch):
    monkeypatch.delenv("GPT_MODEL_API_KEY", raising=False)
    assert not settings().uses_openai


def test_openai_requires_key(monkeypatch):
    monkeypatch.delenv("GPT_MODEL_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="GPT_MODEL_API_KEY is required"):
        settings(AI_PROVIDER="openai")


def test_key_is_redacted():
    configured = settings(AI_PROVIDER="openai", GPT_MODEL_API_KEY="test-only-key")
    assert configured.uses_openai
    assert "test-only-key" not in repr(configured)
