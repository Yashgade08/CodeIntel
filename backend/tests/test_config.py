"""
Unit tests for configuration module.
"""

from __future__ import annotations

from app.core.config import Settings, get_settings


def test_default_settings():
    """Settings should have sensible defaults."""
    settings = Settings()
    assert settings.APP_NAME == "CodeIntel"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.DB_POOL_SIZE == 20


def test_get_settings_cached():
    """get_settings() should return the same cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
