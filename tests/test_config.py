import pytest

from letras.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.base_url == "https://www.letras.mus.br"
    assert settings.delay == 0.5
    assert settings.max_workers == 8
    assert settings.max_attempts == 3


def test_settings_reads_letras_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LETRAS_DELAY", "1.5")
    monkeypatch.setenv("LETRAS_MAX_WORKERS", "4")

    settings = Settings()

    assert settings.delay == 1.5
    assert settings.max_workers == 4
