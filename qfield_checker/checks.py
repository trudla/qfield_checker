from __future__ import annotations

import numpy as np
import pandas as pd

from qfield_checker.columns import (
    ERROR_DESCRIPTION_COLUMN,
    ERROR_FLAG_COLUMN,
)


def require_columns(df: pd.DataFrame, layer_name: str, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(
            f"Layer {layer_name!r} is missing expected columns: {', '.join(missing)}"
        )


def initialise_error_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[ERROR_FLAG_COLUMN] = False
    df[ERROR_DESCRIPTION_COLUMN] = None
    return df


def apply_error(df: pd.DataFrame, mask: pd.Series, message: str) -> None:
    df.loc[mask, ERROR_FLAG_COLUMN] = True

    current = df.loc[mask, ERROR_DESCRIPTION_COLUMN]
    df.loc[mask, ERROR_DESCRIPTION_COLUMN] = np.where(
        current.isna() | (current == ""),
        message,
        current.astype(str) + ", " + message,
    )


def run_l_checks(df_l: pd.DataFrame, df_s: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        df_l,
        "L",
        [
            "ALIVE",
            "DIAM_LOW",
            "DIAM_UP",
            "DECAY",
            "STEM_ID",
            "TREE_ID",
            "UUID_POINT",
        ],
    )
    require_columns(
        df_s,
        "S",
        [
            "STATUS",
            "TREE_ID",
            "UUID_POINT",
        ],
    )

    df_l = initialise_error_columns(df_l)
    df_s = df_s.copy()

    mask_alive = df_l["ALIVE"] == 1
    mask_dead = df_l["ALIVE"] == 0

    mask_diam_low = df_l["DIAM_LOW"].notna()
    mask_diam_up = df_l["DIAM_UP"].notna()
    mask_has_diam = mask_diam_low & mask_diam_up
    mask_has_tree = df_l["TREE_ID"].notna()

    df_s_alive = df_s[df_s["STATUS"].isin(["AI", "AU"])]

    apply_error(df_l, mask_alive & df_l["DIAM_UP"].isna(), "Missing DIAM_UP")
    apply_error(df_l, mask_alive & df_l["DIAM_LOW"].isna(), "Missing DIAM_LOW")
    apply_error(
        df_l,
        (mask_diam_low | mask_diam_up) & mask_dead & df_l["DECAY"].isna(),
        "Missing DECAY",
    )
    apply_error(
        df_l,
        (mask_diam_low | mask_diam_up) & df_l["STEM_ID"].isna(),
        "Missing STEM_ID",
    )

    apply_error(
        df_l,
        mask_alive & df_l["DECAY"].between(1, 7, inclusive="both"),
        "DECAY X ALIVE",
    )
    apply_error(
        df_l,
        df_l["DIAM_UP"] > df_l["DIAM_LOW"],
        "DIAM_UP > DIAM_LOW",
    )

    valid_diams = (df_l["DIAM_LOW"] > 0) & (df_l["DIAM_UP"] > 0) & (df_l["ALIVE"] == 0)
    invalid_decay = ~df_l["DECAY"].between(0, 7, inclusive="neither")
    apply_error(df_l, valid_diams & invalid_decay, "DECAY not in (0,6)")

    key_l = pd.Series(
        list(zip(df_l["TREE_ID"], df_l["UUID_POINT"])),
        index=df_l.index,
    )
    key_s = set(zip(df_s["TREE_ID"], df_s["UUID_POINT"]))
    mask_missing_gp = mask_has_diam & mask_has_tree & ~key_l.isin(key_s)
    apply_error(df_l, mask_missing_gp, "Missing growing point")

    key_s_alive = set(zip(df_s_alive["TREE_ID"], df_s_alive["UUID_POINT"]))
    mask_growing_not_alive = mask_alive & mask_has_tree & ~key_l.isin(key_s_alive)
    apply_error(df_l, mask_growing_not_alive, "Growing spot not alive")

    return df_l


def run_s_checks(df_s: pd.DataFrame, df_l: pd.DataFrame) -> pd.DataFrame:
    df_s = initialise_error_columns(df_s)

    # TODO: add direct S-layer checks later

    return df_s


def run_checks(
    df_l: pd.DataFrame,
    df_s: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_l_checked = run_l_checks(df_l, df_s)
    df_s_checked = run_s_checks(df_s, df_l_checked)
    return df_l_checked, df_s_checked
