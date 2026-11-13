"""Run everything: raw files -> clean tables -> quality checks -> forecasts -> Excel, CSV and charts."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import quality  # noqa: E402
from .clean import add_kreds, complete_grid, label, quarter_to_date, read_raw  # noqa: E402
from .fetch import EXTRA_AREAS, KREDS_KOMMUNER, TYPES, fetch_all  # noqa: E402
from .forecast import forecast  # noqa: E402

AREAS = list(KREDS_KOMMUNER) + list(EXTRA_AREAS)


def build(raw: Path) -> dict[str, pd.DataFrame]:
    q_raw = read_raw(raw / "STRAF11.csv")
    y_raw = read_raw(raw / "STRAF22.csv")
    q = complete_grid(q_raw, [], AREAS, TYPES)
    y = complete_grid(y_raw, ["anmsigt"], AREAS, TYPES)
    filled = {"STRAF11": q.attrs["filled_zero_cells"], "STRAF22": y.attrs["filled_zero_cells"]}

    findings = [
        quality.Finding(
            "Manglende celler udfyldt med 0",
            len(q) + len(y),
            0,
            f"API'et udelader nul-celler: {filled['STRAF11']} i STRAF11 og {filled['STRAF22']} i STRAF22 genskabt som 0.",
        ),
        quality.check_no_negatives(q),
        quality.check_parts_sum_to_total(q),
        quality.check_parts_sum_to_total(y, ["anmsigt"]),
        quality.check_region_vs_kreds(q),
        quality.check_charged_le_reported(y),
        quality.check_quarters_match_year(q, y),
    ]

    q = add_kreds(q, ["overtraed", "tid"])
    y = add_kreds(y, ["overtraed", "anmsigt", "tid"])
    findings.append(quality.check_latest_quarter(q))

    q = label(q)
    q["kvartal_start"] = quarter_to_date(q["tid"])
    y = label(y)

    # Charge rate per year: share of reported crimes with a charge.
    w = y.pivot_table(index=["omraade", "omraade_navn", "overtraed", "type_navn", "tid"], columns="anmsigt", values="indhold").reset_index()
    w["sigtelsesprocent"] = (w["SIG"] / w["ANM"].where(w["ANM"] > 0)).round(4)

    # Municipality overview: last 4 quarters vs the 4 before.
    tot = q[(q["overtraed"] == "TOT") & (q["omraade"].isin(list(KREDS_KOMMUNER) + ["KREDS"]))]
    periods = sorted(tot["tid"].unique())
    last4, prev4 = periods[-4:], periods[-8:-4]
    ov = (
        tot.assign(periode=tot["tid"].map(lambda t: "seneste" if t in last4 else ("forrige" if t in prev4 else None)))
        .dropna(subset=["periode"])
        .pivot_table(index="omraade_navn", columns="periode", values="indhold", aggfunc="sum")
    )
    ov["ændring"] = ((ov["seneste"] - ov["forrige"]) / ov["forrige"]).round(4)
    ov = ov.sort_values("seneste", ascending=False).reset_index()
    ov.attrs["perioder"] = (f"{last4[0]} til {last4[-1]}", f"{prev4[0]} til {prev4[-1]}")

    # Forecasts per crime type for the district.
    fc_rows, bt_rows = [], []
    for code in ["TOT", "12", "13", "3"]:
        s = q[(q["omraade"] == "KREDS") & (q["overtraed"] == code)].sort_values("tid")
        bt, fc, band = forecast(s["indhold"].to_numpy(float), h=4, holdout=8)
        bt.insert(0, "type", s["type_navn"].iloc[0])
        bt_rows.append(bt)
        last = pd.Period(s["tid"].iloc[-1].replace("K", "Q"), freq="Q")
        for i, v in enumerate(fc, start=1):
            p = last + i
            fc_rows.append(
                {
                    "type": s["type_navn"].iloc[0],
                    "kvartal": f"{p.year}K{p.quarter}",
                    "metode": bt["metode"].iloc[0],
                    "prognose": round(float(v)),
                    "nedre": round(float(v - band)),
                    "øvre": round(float(v + band)),
                }
            )

    dq = pd.DataFrame([{"tjek": f.check, "rækker": f.rows, "fejl": f.failures, "status": "OK" if f.ok else "SE NOTE", "note": f.note} for f in findings])
    return {
        "kvartaler": q,
        "aar": w,
        "kommuner": ov,
        "backtest": pd.concat(bt_rows, ignore_index=True),
        "prognose": pd.DataFrame(fc_rows),
        "datakvalitet": dq,
    }


def charts(t: dict[str, pd.DataFrame], out: Path) -> None:
    q = t["kvartaler"]
    k = q[(q["omraade"] == "KREDS") & (q["overtraed"] == "TOT")].sort_values("kvartal_start")
    fc = t["prognose"][t["prognose"]["type"] == "I alt"]
    fc_x = pd.PeriodIndex([p.replace("K", "Q") for p in fc["kvartal"]], freq="Q").to_timestamp()
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(k["kvartal_start"], k["indhold"], color="#1f4e79", lw=1.6, label="Anmeldte forbrydelser")
    ax.plot(fc_x, fc["prognose"], color="#c55a11", lw=1.6, ls="--", label="Prognose")
    ax.fill_between(fc_x, fc["nedre"], fc["øvre"], color="#c55a11", alpha=0.15, label="Usikkerhed")
    ax.set_title("Nordjyllands Politikreds: anmeldte forbrydelser pr. kvartal", fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out / "kreds_kvartaler.png", dpi=160)
    plt.close(fig)

    a = t["aar"]
    s = a[(a["overtraed"] == "1") & (a["omraade"].isin(["KREDS", "000"]))]
    fig, ax = plt.subplots(figsize=(8, 3.0))
    for code, name, color in [("KREDS", "Nordjyllands Politikreds", "#1f4e79"), ("000", "Hele landet", "#7f7f7f")]:
        r = s[s["omraade"] == code].sort_values("tid")
        ax.plot(r["tid"].astype(int), r["sigtelsesprocent"] * 100, color=color, lw=1.6, label=name)
    ax.set_title("Straffelov: andel anmeldelser med sigtelse (%)", fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out / "sigtelsesprocent.png", dpi=160)
    plt.close(fig)


def write(t: dict[str, pd.DataFrame], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    # Flat files for Power Query and Qlik.
    q = t["kvartaler"][["omraade", "omraade_navn", "overtraed", "type_navn", "tid", "kvartal_start", "indhold"]]
    q.to_csv(out / "anmeldelser_kvartal.csv", index=False, sep=";", encoding="utf-8")
    t["aar"].to_csv(out / "sigtelser_aar.csv", index=False, sep=";", encoding="utf-8")
    t["prognose"].to_csv(out / "prognose.csv", index=False, sep=";", encoding="utf-8")
    with pd.ExcelWriter(out / "ledelsesinformation_nordjylland.xlsx", engine="openpyxl") as xw:
        t["kommuner"].to_excel(xw, sheet_name="Kommuner", index=False)
        t["prognose"].to_excel(xw, sheet_name="Prognose", index=False)
        t["backtest"].to_excel(xw, sheet_name="Backtest", index=False)
        t["datakvalitet"].to_excel(xw, sheet_name="Datakvalitet", index=False)
        k = t["kvartaler"]
        piv = k[k["omraade"] == "KREDS"].pivot_table(index="tid", columns="type_navn", values="indhold").reset_index()
        piv.to_excel(xw, sheet_name="Kreds pr kvartal", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = max(12, min(60, max(len(str(c.value or "")) for c in col) + 2))
    charts(t, out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--fetch", action="store_true", help="download fresh raw files first")
    p.add_argument("--raw", default="data/raw")
    p.add_argument("--out", default="output")
    a = p.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    if a.fetch:
        fetch_all(raw)
    t = build(raw)
    write(t, out)
    pd.set_option("display.width", 200)
    print(t["datakvalitet"].to_string(index=False))
    print()
    print(t["kommuner"].to_string(index=False), t["kommuner"].attrs.get("perioder"))
    print()
    print(t["backtest"].to_string(index=False))
    print()
    print(t["prognose"].to_string(index=False))
    a_ = t["aar"]
    print(
        a_[(a_["overtraed"] == "1") & (a_["omraade"].isin(["KREDS", "000"]))][["omraade_navn", "tid", "ANM", "SIG", "sigtelsesprocent"]]
        .tail(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
