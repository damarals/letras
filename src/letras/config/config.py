from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LETRAS_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    # Base settings
    base_url: str = Field("https://www.letras.mus.br")
    max_workers: int = Field(28, ge=1, le=50)
    timeout: int = Field(30, ge=1)
    delay: float = Field(0.5, ge=0)

    # Database settings
    db_host: str = Field("db")
    db_port: int = Field(5432)
    db_name: str = Field("letras")
    db_user: str = Field("letras")
    db_password: str = Field("letras")

    # Output settings
    release_dir: Path = Field("data")
    temp_dir: Path = Field("data/temp")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.release_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


class Config:
    _instance: Optional[Settings] = None

    @classmethod
    def get_settings(cls) -> Settings:
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance

    @classmethod
    def reload(cls) -> None:
        cls._instance = None
