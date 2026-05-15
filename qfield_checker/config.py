from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# Edit these directly for now.
PROJECT_ID = "PUT-YOUR-QFIELD-PROJECT-ID-HERE"
READY_LAYER = "ready_for_upload"
READY_FLAG_COLUMN = "ready"


@dataclass
class Settings:
    qfield_url: str
    username: str
    password: str
    workdir: Path


def get_settings() -> Settings:
    return Settings(
        qfield_url=os.getenv("QFIELDCLOUD_URL", "https://app.qfield.cloud/api/v1/"),
        username=os.getenv("QFIELDCLOUD_USERNAME", ""),
        password=os.getenv("QFIELDCLOUD_PASSWORD", ""),
        workdir=Path(os.getenv("QFIELD_CHECKER_WORKDIR", ".workdir")),
    )


def validate_settings(settings: Settings) -> None:
    if PROJECT_ID == "PUT-YOUR-QFIELD-PROJECT-ID-HERE":
        raise ValueError("Set PROJECT_ID in qfield_checker/config.py first.")

    if not settings.username:
        raise ValueError("QFIELDCLOUD_USERNAME is missing.")

    if not settings.password:
        raise ValueError("QFIELDCLOUD_PASSWORD is missing.")
