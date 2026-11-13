"""End to end on the committed raw snapshot: the numbers in the memo must come out of the code."""

from pathlib import Path

from lidemo.pipeline import build

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def test_pipeline_on_snapshot():
    t = build(RAW)
    dq = t["datakvalitet"].set_index("tjek")
    assert dq.loc["Ingen negative tal", "status"] == "OK"
    assert dq.loc["Region Nordjylland = kreds + Thisted + Morsø", "status"] == "OK"
    ov = t["kommuner"].set_index("omraade_navn")
    assert ov.loc["Nordjyllands Politikreds", "seneste"] == 25521
    assert ov.loc["Nordjyllands Politikreds", "forrige"] == 26271
    assert len(t["prognose"]) == 16
