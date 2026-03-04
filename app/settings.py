from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_url: str
    prompt_version: str
    model_name: str
    generation_timeout_seconds: float


def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    default_db = f"sqlite+aiosqlite:///{project_root / 'esg_copilot.db'}"
    return Settings(
        db_url=os.getenv("ESG_DB_URL", default_db),
        prompt_version=os.getenv("PROMPT_VERSION", "stub_v1"),
        model_name=os.getenv("MODEL_NAME", "stub"),
        generation_timeout_seconds=float(os.getenv("GENERATION_TIMEOUT_SECONDS", "5")),
    )

