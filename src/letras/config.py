"""Runtime configuration via pydantic-settings (LETRAS_ env vars / .env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LETRAS_", env_file=".env", extra="ignore"
    )

    base_url: str = "https://www.letras.mus.br"
    delay: float = 0.5
    max_workers: int = 8
    max_attempts: int = 3
