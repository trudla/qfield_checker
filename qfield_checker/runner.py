from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from qfield_checker.checks import run_checks
from qfield_checker.columns import (
    ERROR_DESCRIPTION_COLUMN,
    ERROR_FLAG_COLUMN,
    L_LAYER_SUFFIX,
    ROW_ID_COLUMN,
    S_LAYER_SUFFIX,
    TARGET_GPKGS,
)
from qfield_checker.config import (
    PROJECT_ID,
    READY_FLAG_COLUMN,
    READY_LAYER,
    get_settings,
    validate_settings,
)
from qfield_checker.qfield import (
    download_project,
    ensure_project_access,
    make_client,
    upload_project,
)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def find_gpkgs(project_dir: Path) -> list[Path]:
    matches: list[Path] = []

    for gpkg_name in TARGET_GPKGS:
        found = list(project_dir.rglob(gpkg_name))
        if not found:
            raise FileNotFoundError(
                f"Could not find {gpkg_name!r} inside {project_dir}."
            )
        matches.append(found[0])

    return matches


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    cursor = conn.execute(f"PRAGMA table_info({quote_ident(table_name)})")
    return [row[1] for row in cursor.fetchall()]


def ensure_error_columns(conn: sqlite3.Connection, table_name: str) -> None:
    columns = set(get_table_columns(conn, table_name))

    if ERROR_FLAG_COLUMN not in columns:
        conn.execute(
            f"ALTER TABLE {quote_ident(table_name)} "
            f"ADD COLUMN {quote_ident(ERROR_FLAG_COLUMN)} INTEGER DEFAULT 0"
        )

    if ERROR_DESCRIPTION_COLUMN not in columns:
        conn.execute(
            f"ALTER TABLE {quote_ident(table_name)} "
            f"ADD COLUMN {quote_ident(ERROR_DESCRIPTION_COLUMN)} TEXT"
        )


def ready_flag_is_set(conn: sqlite3.Connection) -> bool:
    if not table_exists(conn, READY_LAYER):
        raise ValueError(
            f"Trigger layer/table {READY_LAYER!r} was not found in the GeoPackage."
        )

    columns = set(get_table_columns(conn, READY_LAYER))
    if READY_FLAG_COLUMN not in columns:
        raise ValueError(
            f"Trigger layer/table {READY_LAYER!r} does not have column {READY_FLAG_COLUMN!r}."
        )

    cursor = conn.execute(
        f"SELECT COUNT(*) FROM {quote_ident(READY_LAYER)} "
        f"WHERE {quote_ident(READY_FLAG_COLUMN)} = 1"
    )
    ready_count = cursor.fetchone()[0]
    return ready_count > 0


def clear_ready_flag(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"UPDATE {quote_ident(READY_LAYER)} "
        f"SET {quote_ident(READY_FLAG_COLUMN)} = 0 "
        f"WHERE {quote_ident(READY_FLAG_COLUMN)} = 1"
    )


def find_single_layer_by_suffix(conn: sqlite3.Connection, suffix: str) -> str:
    cursor = conn.execute(
        """
        SELECT table_name
        FROM gpkg_contents
        WHERE table_name LIKE ?
        ORDER BY table_name
        """,
        (f"%{suffix}",),
    )
    matches = [row[0] for row in cursor.fetchall()]

    if not matches:
        raise ValueError(
            f"No layer ending with {suffix!r} was found in this GeoPackage."
        )

    if len(matches) > 1:
        raise ValueError(
            f"More than one layer ends with {suffix!r}: {', '.join(matches)}. "
            "Hardcode the exact layer names next."
        )

    return matches[0]


def load_layer_df(conn: sqlite3.Connection, layer_name: str) -> pd.DataFrame:
    sql = (
        f"SELECT rowid AS {quote_ident(ROW_ID_COLUMN)}, * "
        f"FROM {quote_ident(layer_name)}"
    )
    return pd.read_sql_query(sql, conn)


def write_error_columns(
    conn: sqlite3.Connection,
    layer_name: str,
    df: pd.DataFrame,
) -> None:
    ensure_error_columns(conn, layer_name)

    required = {ROW_ID_COLUMN, ERROR_FLAG_COLUMN, ERROR_DESCRIPTION_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Cannot write results for layer {layer_name!r}; missing columns: "
            f"{', '.join(sorted(missing))}"
        )

    rows_to_update = []
    for row in df[
        [ROW_ID_COLUMN, ERROR_FLAG_COLUMN, ERROR_DESCRIPTION_COLUMN]
    ].itertuples(
        index=False,
        name=None,
    ):
        rowid, error_flag, error_description = row

        rows_to_update.append(
            (
                1 if bool(error_flag) else 0,
                None
                if pd.isna(error_description) or error_description == ""
                else str(error_description),
                int(rowid),
            )
        )

    conn.executemany(
        f"""
        UPDATE {quote_ident(layer_name)}
        SET {quote_ident(ERROR_FLAG_COLUMN)} = ?,
            {quote_ident(ERROR_DESCRIPTION_COLUMN)} = ?
        WHERE rowid = ?
        """,
        rows_to_update,
    )


def process_gpkg(gpkg_path: Path, upload: bool) -> bool:
    conn = sqlite3.connect(gpkg_path)

    try:
        if not ready_flag_is_set(conn):
            print(
                f"{gpkg_path.name}: {READY_LAYER}.{READY_FLAG_COLUMN} is not set. Skipping."
            )
            return False

        l_layer = find_single_layer_by_suffix(conn, L_LAYER_SUFFIX)
        s_layer = find_single_layer_by_suffix(conn, S_LAYER_SUFFIX)

        print(f"{gpkg_path.name}: using L layer {l_layer!r} and S layer {s_layer!r}")

        df_l = load_layer_df(conn, l_layer)
        df_s = load_layer_df(conn, s_layer)

        df_l_checked, df_s_checked = run_checks(df_l, df_s)

        write_error_columns(conn, l_layer, df_l_checked)
        write_error_columns(conn, s_layer, df_s_checked)

        if upload:
            clear_ready_flag(conn)
            print(f"{gpkg_path.name}: reset {READY_FLAG_COLUMN} in {READY_LAYER}.")
        else:
            print(f"{gpkg_path.name}: upload disabled, ready flag left unchanged.")

        conn.commit()
        print(f"{gpkg_path.name}: checks finished.")
        return True
    finally:
        conn.close()


def run(upload: bool = False) -> None:
    settings = get_settings()
    validate_settings(settings)

    client = make_client(settings)
    project = ensure_project_access(client)

    print(f"Connected to project: {project.get('name')} ({project.get('id')})")
    print(f"Using hardcoded project id: {PROJECT_ID}")

    project_dir = download_project(client, settings)
    print(f"Downloaded project into {project_dir}")

    gpkg_paths = find_gpkgs(project_dir)

    any_processed = False
    for gpkg_path in gpkg_paths:
        did_run = process_gpkg(gpkg_path, upload=upload)
        if did_run:
            any_processed = True

    if not any_processed:
        print("No GeoPackage had the ready flag set. Nothing was uploaded.")
        return

    if upload:
        print("Uploading updated project back to QField Cloud...")
        upload_project(client, project_dir)
        print("Upload finished.")
    else:
        print("Upload skipped. Use --upload when you are ready.")
