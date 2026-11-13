"""Data quality checks, written as plain functions that return a list of findings.

Each finding says what was checked, how many rows it covers and whether it passed,
so the checks can go straight into a sheet the reader can see.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .fetch import KREDS_KOMMUNER


@dataclass
class Finding:
    check: str
    rows: int
    failures: int
    note: str

    @property
    def ok(self) -> bool:
        return self.failures == 0


def check_no_negatives(df: pd.DataFrame) -> Finding:
    bad = int((df["indhold"] < 0).sum())
    return Finding("Ingen negative tal", len(df), bad, "Antal anmeldelser kan ikke være negative.")


def check_parts_sum_to_total(df: pd.DataFrame, extra_keys: list[str] | None = None) -> Finding:
    """TOT must equal straffelov (1) + særlove (3); straffelov must equal its parts."""
    keys = ["omraade", "tid"] + (extra_keys or [])
    w = df.pivot_table(index=keys, columns="overtraed", values="indhold", aggfunc="sum", fill_value=0)
    tot_bad = (w["TOT"] != w["1"] + w["3"]).sum()
    parts = [c for c in ["11", "12", "13", "14", "1000"] if c in w.columns]
    straf_bad = (w["1"] != w[parts].sum(axis=1)).sum()
    return Finding(
        "Delsummer giver totalen",
        len(w),
        int(tot_bad + straf_bad),
        "I alt = straffelov + særlove, og straffelov = summen af dens underkategorier.",
    )


def check_region_vs_kreds(df: pd.DataFrame) -> Finding:
    """Region Nordjylland is NOT the police district: it also holds Thisted and Morsø.

    Check: region = kreds + Thisted + Morsø, up to municipalities recorded as 'uoplyst'.
    Reported as the largest gap in percent, so a reader sees why the region total is the wrong number.
    """
    t = df[df["overtraed"] == "TOT"].pivot_table(index="tid", columns="omraade", values="indhold", aggfunc="sum")
    kreds = t[list(KREDS_KOMMUNER)].sum(axis=1)
    rest = t["787"] + t["773"]
    gap = (t["081"] - kreds - rest).abs() / t["081"]
    bad = int((gap > 0.01).sum())
    share = float((rest / t["081"]).mean())
    return Finding(
        "Region Nordjylland = kreds + Thisted + Morsø",
        len(t),
        bad,
        f"Regionstallet er ikke kredsens tal: Thisted og Morsø udgør i snit {share:.1%} af regionen.",
    )


def check_charged_le_reported(df22: pd.DataFrame) -> Finding:
    w = df22.pivot_table(index=["omraade", "overtraed", "tid"], columns="anmsigt", values="indhold", fill_value=0)
    bad = int((w["SIG"] > w["ANM"]).sum())
    return Finding("Sigtelser ≤ anmeldelser", len(w), bad, "Anmeldelser med sigtelse kan ikke overstige anmeldelser.")


def check_quarters_match_year(q: pd.DataFrame, y: pd.DataFrame) -> Finding:
    """Sample check across tables: the four quarters in STRAF11 should match the year in STRAF22."""
    qq = q[(q["overtraed"] == "TOT") & (q["omraade"].isin(KREDS_KOMMUNER))].copy()
    qq["aar"] = qq["tid"].str[:4]
    qsum = qq.groupby(["omraade", "aar"])["indhold"].sum()
    yy = y[(y["overtraed"] == "TOT") & (y["anmsigt"] == "ANM") & (y["omraade"].isin(KREDS_KOMMUNER))]
    ysum = yy.set_index(["omraade", "tid"])["indhold"]
    ysum.index.names = ["omraade", "aar"]
    both = pd.concat([qsum.rename("kvartaler"), ysum.rename("aar_tal")], axis=1).dropna()
    diff = (both["kvartaler"] - both["aar_tal"]) / both["aar_tal"].clip(lower=1)
    bad = int((diff.abs() > 0.02).sum())
    lower = float((diff < 0).mean())
    return Finding(
        "Kvartaler (STRAF11) stemmer med årstal (STRAF22)",
        len(both),
        bad,
        f"Summen af kvartaler ligger under årstallet i {lower:.0%} af kommune-år (median {diff.median():.1%}). "
        "Sandsynligvis sene registreringer i årstabellen; ikke bekræftet. Brug én tabel pr. nøgletal.",
    )


def check_latest_quarter(q: pd.DataFrame) -> Finding:
    """Flag a latest quarter that drops sharply versus the same quarter last year (possible late registrations)."""
    t = q[(q["omraade"] == "KREDS") & (q["overtraed"] == "TOT")].sort_values("tid")
    last, same_last_year = t["indhold"].iloc[-1], t["indhold"].iloc[-5]
    change = (last - same_last_year) / same_last_year
    return Finding(
        "Seneste kvartal ligner samme kvartal sidste år",
        1,
        int(change < -0.25),
        f"Seneste kvartal {t['tid'].iloc[-1]}: {change:+.1%} mod samme kvartal året før.",
    )
