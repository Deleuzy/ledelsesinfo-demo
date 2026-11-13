"""Build the one page management memo (Danish) as .docx from the pipeline's own numbers."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Cm, Pt, RGBColor

from .pipeline import build

BLUE = RGBColor(0x1F, 0x4E, 0x79)


def n(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def pct(x: float, sign: bool = False) -> str:
    s = f"{x * 100:+.1f}" if sign else f"{x * 100:.1f}"
    return s.replace(".", ",").replace("-", "−") + " %"


def make(raw: Path, out: Path, figs: Path) -> Path:
    t = build(raw)
    ov = t["kommuner"].set_index("omraade_navn")
    k = ov.loc["Nordjyllands Politikreds"]
    q = t["kvartaler"]
    yr = q[q["omraade"] == "KREDS"].assign(aar=lambda d: d["tid"].str[:4]).groupby(["overtraed", "aar"])["indhold"].sum()
    a = t["aar"].set_index(["omraade", "overtraed", "tid"])["sigtelsesprocent"]
    fc = t["prognose"][t["prognose"]["type"] == "I alt"].iloc[0]
    bt = t["backtest"][t["backtest"]["type"] == "I alt"].iloc[0]
    p_last, p_prev = t["kommuner"].attrs["perioder"]

    d = Document()
    sec = d.sections[0]
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(1.3)
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(9.5)
    st.paragraph_format.space_after = Pt(2)

    def h(text: str, size: float = 11) -> None:
        p = d.add_paragraph()
        r = p.add_run(text)
        r.bold, r.font.size, r.font.color.rgb = True, Pt(size), BLUE
        p.paragraph_format.space_before = Pt(6)

    def b(lead: str, text: str) -> None:
        p = d.add_paragraph(style="List Bullet")
        p.add_run(lead + " ").bold = True
        p.add_run(text)

    h("Ledelsesnotat: anmeldte forbrydelser i Nordjyllands Politikreds", 14)
    sub = d.add_paragraph("Demo på åbne data fra Danmarks Statistik (STRAF11 og STRAF22). Ikke politiets egne data.")
    sub.runs[0].font.size, sub.runs[0].font.color.rgb = Pt(8.5), RGBColor(0x66, 0x66, 0x66)

    h("Kort fortalt")
    chg = (k["seneste"] - k["forrige"]) / k["forrige"]
    b("Lidt færre anmeldelser.", f"{n(k['seneste'])} anmeldte forbrydelser i de seneste fire kvartaler ({p_last}), {pct(abs(chg))} færre end de fire før.")
    v24, v25, e24, e25 = yr[("12", "2024")], yr[("12", "2025")], yr[("13", "2024")], yr[("13", "2025")]
    b(
        "Vold op, ejendom ned.",
        f"I 2025 blev der anmeldt {n(v25)} voldsforbrydelser, {pct((v25 - v24) / v24)} flere end i 2024. "
        f"Ejendomsforbrydelser faldt {pct((e24 - e25) / e24)} til {n(e25)}.",
    )
    b(
        "Sigtelsesprocenten er over landets, men faldende.",
        f"For straffeloven fik {pct(a[('KREDS', '1', '2025')])} af anmeldelserne i 2025 en sigtelse mod {pct(a[('000', '1', '2025')])} "
        f"på landsplan. I 2023 var tallet {pct(a[('KREDS', '1', '2023')])}.",
    )
    b(
        "Næste kvartal.",
        f"Prognosen for {fc['kvartal']} er ca. {n(fc['prognose'])} anmeldelser ({n(fc['nedre'])} til {n(fc['øvre'])}). "
        f"Metoden ({bt['metode'].split(' (')[0]}) ramte i snit {pct(bt['MAPE'])} ved siden af på de seneste otte kvartaler.",
    )
    d.add_picture(str(figs / "kreds_kvartaler.png"), width=Cm(15.5))

    h("Kommunerne")
    tab = d.add_table(rows=1, cols=4)
    tab.style, tab.alignment = "Light List Accent 1", WD_TABLE_ALIGNMENT.CENTER
    for c, txt in zip(tab.rows[0].cells, ["Kommune", p_prev, p_last, "Ændring"], strict=True):
        c.text = txt
    for name, r in ov.drop("Nordjyllands Politikreds").iterrows():
        cells = tab.add_row().cells
        for c, txt in zip(cells, [name, n(r["forrige"]), n(r["seneste"]), pct(r["ændring"], sign=True)], strict=True):
            c.text = txt
    for row in tab.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8.5)
    laeso = ov.loc["Læsø"]
    d.add_paragraph(
        f"Brønderslev er den eneste større kommune med flere anmeldelser. Læsøs stigning er {n(laeso['seneste'] - laeso['forrige'])} sager "
        "og bør ikke læses som en tendens."
    )

    h("Hvad tallene ikke kan bære")
    dq = t["datakvalitet"].set_index("tjek")
    b("Regionen er ikke kredsen.", dq.loc["Region Nordjylland = kreds + Thisted + Morsø", "note"] + " Kredsens tal er her summen af de 9 kommuner.")
    b("To tabeller, to tal.", dq.loc["Kvartaler (STRAF11) stemmer med årstal (STRAF22)", "note"])
    b(
        "Den seneste sigtelsesprocent kan stige.",
        "Sigtelser kan komme efter årets udgang, så faldet i 2024 og 2025 skal tjekkes mod Danmarks Statistiks dokumentation, før det bruges som et resultat.",
    )
    b("Kendt fejl i kilden.", "Danmarks Statistik oplyser, at ca. 1.700 anmeldelser om dyr og jagt mangler i 2023.")

    foot = d.add_paragraph(
        "Alle tal er beregnet af koden i github.com/Deleuzy/ledelsesinfo-demo og kan genskabes med én kommando. "
        "Datakvalitetstjek: delsummer giver totaler, ingen negative tal, sigtelser aldrig over anmeldelser, nul-celler som API'et udelader genskabt."
    )
    foot.runs[0].font.size, foot.runs[0].font.color.rgb = Pt(8), RGBColor(0x55, 0x55, 0x55)
    out.parent.mkdir(parents=True, exist_ok=True)
    d.save(out)
    return out


if __name__ == "__main__":
    print(make(Path("data/raw"), Path("memo/ledelsesnotat.docx"), Path("output")))
