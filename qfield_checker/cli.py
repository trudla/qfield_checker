from __future__ import annotations

import json

import click

from qfield_checker.config import PROJECT_ID, get_settings, validate_settings
from qfield_checker.qfield import ensure_project_access, make_client
from qfield_checker.runner import run


@click.group()
def cli() -> None:
    """Simple QField Cloud checker."""


@cli.command("print-config")
def print_config() -> None:
    settings = get_settings()
    payload = {
        "qfield_url": settings.qfield_url,
        "username": settings.username,
        "workdir": str(settings.workdir),
        "project_id": PROJECT_ID,
    }
    click.echo(json.dumps(payload, indent=2))


@cli.command("check-connection")
def check_connection() -> None:
    settings = get_settings()
    validate_settings(settings)

    client = make_client(settings)
    project = ensure_project_access(client)

    click.echo(
        f"Connection OK. Found project: {project.get('name')} ({project.get('id')})"
    )


@cli.command("list-projects")
def list_projects() -> None:
    settings = get_settings()
    validate_settings(settings)

    client = make_client(settings)
    projects = client.list_projects()

    for project in projects:
        marker = " <==" if project.get("id") == PROJECT_ID else ""
        click.echo(f"{project.get('id')} | {project.get('name')}{marker}")


@cli.command("run")
@click.option(
    "--upload", is_flag=True, help="Upload the changed files back to QField Cloud."
)
def run_command(upload: bool) -> None:
    run(upload=upload)
