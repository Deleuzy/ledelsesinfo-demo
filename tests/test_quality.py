import pandas as pd

from lidemo import quality
from lidemo.clean import complete_grid
from lidemo.fetch import KREDS_KOMMUNER


def _q(rows):
    return pd.DataFrame(rows, columns=["omraade", "overtraed", "tid", "indhold"])


def test_complete_grid_fills_missing_zero_cells():
    raw = _q([["851", "TOT", "2024K1", 10], ["825", "TOT", "2024K2", 3], ["851", "TOT", "2024K2", 12]])
    full = complete_grid(raw, [], ["851", "825"], ["TOT"])
    assert len(full) == 4
    assert full.attrs["filled_zero_cells"] == 1
    assert full.loc[(full.omraade == "825") & (full.tid == "2024K1"), "indhold"].item() == 0


def test_negative_is_caught():
    assert not quality.check_no_negatives(_q([["851", "TOT", "2024K1", -1]])).ok


def test_parts_must_sum_to_total():
    good = [["851", t, "2024K1", v] for t, v in [("TOT", 10), ("1", 7), ("3", 3), ("11", 1), ("12", 2), ("13", 3), ("14", 1), ("1000", 0)]]
    assert quality.check_parts_sum_to_total(_q(good)).ok
    bad = [r if r[1] != "3" else ["851", "3", "2024K1", 4] for r in good]
    assert quality.check_parts_sum_to_total(_q(bad)).failures == 1


def test_region_is_not_the_district():
    rows = [[k, "TOT", "2024K1", 100] for k in KREDS_KOMMUNER]
    rows += [["787", "TOT", "2024K1", 50], ["773", "TOT", "2024K1", 30], ["081", "TOT", "2024K1", 980]]
    f = quality.check_region_vs_kreds(_q(rows))
    assert f.ok
    assert "8.2%" in f.note  # (50 + 30) / 980


def test_charged_cannot_exceed_reported():
    y = pd.DataFrame(
        [["851", "TOT", "ANM", "2024", 10], ["851", "TOT", "SIG", "2024", 11]],
        columns=["omraade", "overtraed", "anmsigt", "tid", "indhold"],
    )
    assert quality.check_charged_le_reported(y).failures == 1


def test_latest_quarter_drop_is_flagged():
    vals = [100, 100, 100, 100, 100, 100, 100, 100, 50]
    tids = [f"{2022 + i // 4}K{i % 4 + 1}" for i in range(len(vals))]
    q = _q([["KREDS", "TOT", t, v] for t, v in zip(tids, vals, strict=True)])
    assert not quality.check_latest_quarter(q).ok
