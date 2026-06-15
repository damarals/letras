"""Runtime configuration via pydantic-settings (LETRAS_ env vars / .env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LETRAS_", env_file=".env", extra="ignore"
    )

    base_url: str = "https://www.letras.mus.br"
    # Sized so the rate limiter (below), not the worker count, governs throughput.
    max_workers: int = 32
    max_attempts: int = 3

    # Transport: HTTP/2 multiplexing + a warm keepalive pool means many requests
    # ride a few long-lived connections (faster and gentler on the source than
    # opening a socket per request).
    http2: bool = True
    max_connections: int = 16
    max_keepalive_connections: int = 16
    keepalive_expiry: float = 30.0

    # Rate governing (token bucket + AIMD). ``requests_per_second`` is the
    # starting ceiling; the limiter backs off on 429/503 and recovers on
    # success, settling at the fastest sustainable rate. ``jitter`` desynchs
    # bursts of worker threads. The legacy fixed ``delay`` is retained as a
    # fallback only (0 = disabled; the limiter governs pacing instead).
    requests_per_second: float = 12.0
    min_requests_per_second: float = 1.0
    max_requests_per_second: float = 40.0
    rate_increase_step: float = 0.5
    backoff_factor: float = 0.5
    jitter: float = 0.05
    delay: float = 0.0
