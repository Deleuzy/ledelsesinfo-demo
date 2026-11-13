"""Turn the raw Statistikbanken files into tidy tables for the police district."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .fetch import EXTRA_AREAS, KREDS_KOMMUNER

TYPE_NAMES = {
    "TOT": "I alt",
    "1": "Straffelov i alt",
    "11": "Seksualforbrydelser",
    "12": "Voldsforbrydelser",
    "13": "Ejendomsforbrydelser",
    "14": "Andre straffelovsforbrydelser",
    "1000": "Uoplyst straffelov",
    "3": "Særlove",
}
AREA_NAMES = {**KREDS_KOMMUNER, **EXTRA_AREAS}
KREDS = "Nordjyllands Politikreds"


def read_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", dtype=str)
    df.columns = [c.lower().replace("å", "aa").replace("æ", "ae") for c in df.columns]
    df["indhold"] = pd.to_numeric(df["indhold"], errors="raise").astype(int)
    return df


def complete_grid(df: pd.DataFrame, keys: list[str], areas: list[str], types: list[str]) -> pd.DataFrame:
    """The BULK format leaves out cells that are zero. Rebuild the full grid and fill those with 0."""
    levels = {"omraade": areas, "overtraed": types, "tid": sorted(df["tid"].unique())}
    for k in keys:
        if k not in levels:
            levels[k] = sorted(df[k].unique())
    idx = pd.MultiIndex.from_product([levels[k] for k in levels], names=list(levels))
    full = df.set_index(list(levels))["indhold"].reindex(idx)
    out = full.fillna(0).astype(int).reset_index()
    out.attrs["filled_zero_cells"] = int(full.isna().sum())
    return out


def quarter_to_date(tid: pd.Series) -> pd.Series:
    year = tid.str[:4].astype(int)
    q = tid.str[-1].astype(int)
    return pd.PeriodIndex.from_fields(year=year, quarter=q, freq="Q").to_timestamp()


def add_kreds(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Add the police district as the sum of its 9 municipalities."""
    k = df[df["omraade"].isin(KREDS_KOMMUNER)].groupby(by, as_index=False)["indhold"].sum()
    k["omraade"] = "KREDS"
    return pd.concat([df, k], ignore_index=True)


def label(df: pd.DataFrame) -> pd.DataFrame:
    names = {**AREA_NAMES, "KREDS": KREDS}
    df = df.copy()
    df["omraade_navn"] = df["omraade"].map(names)
    df["type_navn"] = df["overtraed"].map(TYPE_NAMES)
    return df
