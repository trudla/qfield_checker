from __future__ import annotations

import shutil
from pathlib import Path

from qfieldcloud_sdk import sdk

from qfield_checker.config import PROJECT_ID, Settings


def make_client(settings: Settings) -> sdk.Client:
    client = sdk.Client(url=settings.qfield_url)
    client.login(settings.username, settings.password)
    return client


def ensure_project_access(client: sdk.Client) -> dict:
    projects = client.list_projects()
    for project in projects:
        if project.get("id") == PROJECT_ID:
            return project

    raise ValueError(f"Project {PROJECT_ID} was not found in your accessible projects.")


def download_project(client: sdk.Client, settings: Settings) -> Path:
    project_dir = settings.workdir / PROJECT_ID

    if project_dir.exists():
        shutil.rmtree(project_dir)

    project_dir.mkdir(parents=True, exist_ok=True)

    client.download_project(
        project_id=PROJECT_ID,
        local_dir=str(project_dir),
        filter_glob="*",
        throw_on_error=True,
        show_progress=True,
        force_download=True,
    )

    return project_dir


def upload_project(client: sdk.Client, project_dir: Path) -> None:
    client.upload_files(
        project_id=PROJECT_ID,
        upload_type=sdk.FileTransferType.PROJECT,
        project_path=str(project_dir),
        filter_glob="*",
        throw_on_error=True,
        show_progress=True,
        force=True,
    )
