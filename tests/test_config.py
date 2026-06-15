import pytest

from letras.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.base_url == "https://www.letras.mus.br"
    assert settings.delay == 0.0
    assert settings.max_workers == 32
    assert settings.max_attempts == 3


def test_settings_transport_and_rate_defaults() -> None:
    settings = Settings()
    assert settings.http2 is True
    assert settings.max_connections == 16
    assert settings.max_keepalive_connections == 16
    assert settings.keepalive_expiry == 30.0
    assert settings.requests_per_second == 12.0
    assert settings.min_requests_per_second == 1.0
    assert settings.max_requests_per_second == 40.0
    assert settings.backoff_factor == 0.5
    assert settings.jitter == 0.05


def test_settings_reads_letras_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LETRAS_DELAY", "1.5")
    monkeypatch.setenv("LETRAS_MAX_WORKERS", "4")
    monkeypatch.setenv("LETRAS_REQUESTS_PER_SECOND", "8")
    monkeypatch.setenv("LETRAS_HTTP2", "false")

    settings = Settings()

    assert settings.delay == 1.5
    assert settings.max_workers == 4
    assert settings.requests_per_second == 8.0
    assert settings.http2 is False
