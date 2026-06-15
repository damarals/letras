"""The admission policy: typed config loaded from filters.yaml."""

from pathlib import Path

import yaml
from pydantic import BaseModel

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "filters.yaml"


class AdmissionPolicy(BaseModel):
    language: str
    min_length: int
    max_length: int
    artist_excludes: list[str]
    title_excludes: list[str]
    content_excludes: list[str]


def load_policy(path: Path | None = None) -> AdmissionPolicy:
    source = path or _DEFAULT_PATH
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    return AdmissionPolicy.model_validate(data)
