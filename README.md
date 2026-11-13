# ledelsesinfo-demo

Ledelsesinformation on open data: reported crime in **Nordjyllands Politikreds**, built the way a management information unit would. The data is fetched, every number is checked, there are forecasts with an honest error measure, the result goes out as Excel and as flat files for Power Query and Qlik, and there is a one page memo for management.

Data comes from Danmarks Statistik's open API (STRAF11: reported crimes per municipality per quarter; STRAF22: reported crimes and reports with a charge per year). It is **not** police data, and no personal data is involved.

## What it shows

| Output | What it is |
|---|---|
| `memo/ledelsesnotat.docx` | One page memo in Danish: development, crime types, municipalities, charge rate, forecast, and what the numbers cannot support |
| `output/ledelsesinformation_nordjylland.xlsx` | Sheets: municipalities (last 4 quarters vs the 4 before), forecast, backtest, data quality, district per quarter |
| `output/*.csv` | Flat files for Power Query and Qlik |
| `powerquery/*.pq` | Power Query (M): load the CSV, or fetch STRAF11 straight from the API |
| `qlik/load_script.qvs` | Qlik Sense load script with a calendar and master measures |

## Data quality findings

These came out of the checks on the real data:

* **The API leaves out zero cells.** 1,764 missing cells were rebuilt as 0, and the grid is complete afterwards.
* **Region Nordjylland is not the police district.** The region also contains Thisted and Morsø (about 8.6% of reports), which belong to Midt- og Vestjyllands Politi. The district is computed as the sum of its 9 municipalities, and a check confirms region = district + Thisted + Morsø.
* **The quarterly and yearly tables disagree.** The four quarters in STRAF11 usually add up to a few percent less than the year in STRAF22. Late registrations in the yearly table are the likely cause, but that is not confirmed. Each key figure therefore uses one table only.
* **The latest charge rates may rise.** Charges can be registered after the year ends, so a fall in the most recent years is flagged and not reported as a result.
* Parts add up to totals, there are no negative counts, and reports with a charge never exceed reports.

## Forecasts

Four simple methods (naive, seasonal naive, 4 quarter moving average, Holt-Winters) are each backtested one step ahead on the last 8 quarters. The method with the lowest MAE is used, with a rough band from the backtest error. For total reports in the district, Holt-Winters missed by 4.5% on average (MAPE).

## Run it

```bash
pip install -e ".[dev]"
python -m lidemo.pipeline          # uses the committed raw snapshot in data/raw
python -m lidemo.pipeline --fetch  # downloads fresh data first
python -m lidemo.memo
pytest -q
```

## What this is not

* Not police data and not the police's own key figures. Case flow, processing times and målopfyldelse live in internal systems.
* **The Power Query and Qlik files have been written but not yet run in Excel or Qlik Sense.** The Excel workbook is written by Python (openpyxl), not by Power Query.
* The forecasts are short term and simple on purpose. They show the method and its error, not a model of crime.
