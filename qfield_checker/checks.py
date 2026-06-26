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


def validate_duplicates(df_s: pd.DataFrame) -> pd.DataFrame:
    mask_duplicate_id = df_s["TREE_ID"].notna() & df_s.duplicated(
        subset=["TREE_ID", "STEM_ID"], keep=False
    )

    mask_duplicate_tag = df_s["TAG"].notna() & df_.duplicated(
        subset=["TAG"], keep=False
    )

    apply_error(df_s, mask_duplicate_id, "Duplicity ERROR: Tree ID + Stem ID!")

    apply_error(df_s, mask_duplicate_tag, "Duplicity ERROR: Tag!")

    return df_s


def validate_dbh(df_s: pd.DataFrame) -> pd.DataFrame:
    mask_dbh_increase = (
        df_s["DBH"].notna()
        & df_s["DBH_OLD"].notna()
        & ((df_s["DBH"] - df_s["DBH_OLD"]) >= 100)
    )

    mask_dbh_decrease = (
        df_s["DBH"].notna()
        & df_s["DBH_OLD"].notna()
        & ((df_s["DBH_OLD"] - df_s["DBH"]) >= df_s["DBH_OLD"] * 0.1)
    )

    mask_dbh_old_positive = df_s["DBH_OLD"] > 0

    apply_error(df_s, mask_dbh_increase, "DBH increase over 100!")

    apply_error(
        df_s, mask_dbh_decrease & mask_dbh_old_positive, "DBH decrease over 10%!"
    )

    return df_s


def validate_status_rules(df_s: pd.DataFrame) -> pd.DataFrame:
    status = df_s["STATUS"]

    mask_multistem = df_s["STEM_ID"] > 1
    mask_no_dbh = df_s["DBH"].isna() & df_s["DBH_OLD"].isna()

    mask_missing_height = df_s["HEIGHT"].isna()
    mask_under = df_s["HEIGHT"] <= 1.29
    mask_over = df_s["HEIGHT"] >= 1.30

    mask_decay_zero = df_s["DECAY"] == 0
    mask_decay_stump = df_s["DECAY"] >= 5

    mask_AL = status == "AI"
    mask_DI = status == "DI"
    mask_DB = status == "DB"
    mask_AB = status == "AB"
    mask_DP = status == "DP"

    apply_error(df_s, status.notna() & mask_no_dbh, "Missing DBH!")

    apply_error(
        df_s, mask_multistem & (df_s["MULTI_STEM"] == "SGL"), "Is not Single Stem!"
    )

    apply_error(df_s, mask_DI & mask_decay_zero, "Decay Error!")

    apply_error(df_s, mask_DB & mask_decay_zero, "Decay Error!")

    apply_error(
        df_s, mask_DP & mask_over & ~mask_missing_height, "Status DP over 1.3 m!"
    )

    apply_error(
        df_s, mask_DB & mask_under & ~mask_missing_height, "Status DB under 1.29 m!"
    )

    apply_error(df_s, mask_DB & mask_missing_height, "Missing Height!")

    apply_error(df_s, mask_AB & mask_missing_height, "Missing Height!")

    apply_error(df_s, mask_DP & mask_decay_stump, "Decay over >= 5: Stump gone!")

    return df_s


def validate_required_fields(df_s: pd.DataFrame) -> pd.DataFrame:
    apply_error(df_s, df_s["STATUS"].isna(), "Missing STATUS!")

    apply_error(df_s, df_s["SPECIES"].isna(), "Missing SPECIES!")

    return df_s


def validate_missing_lying_tree(df_s: pd.DataFrame, df_l: pd.DataFrame) -> pd.DataFrame:
    mask_status = df_s["STATUS"].isin(["DP", "DU", "BLS"])

    mask_has_tree = df_s["TREE_ID"].notna()

    key_L = set(zip(df_l["TREE_ID"], df_l["UUID_POINT"]))

    key_S = list(zip(df_s["TREE_ID"], df_s["UUID_POINT"]))

    mask_missing_line = (
        mask_status & mask_has_tree & ~pd.Series(key_S, index=df_s.index).isin(key_L)
    )

    apply_error(df_s, mask_missing_line, "Missing lying tree!")

    return df_s


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

    df_s = validate_duplicates(df_s)
    df_s = validate_dbh(df_s)
    df_s = validate_status_rules(df_s)
    df_s = validate_required_fields(df_s)
    df_s = validate_missing_lying_tree(df_s, df_l)

    return df_s


def run_checks(
    df_l: pd.DataFrame,
    df_s: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_l_checked = run_l_checks(df_l, df_s)
    df_s_checked = run_s_checks(df_s, df_l_checked)
    return df_l_checked, df_s_checked
