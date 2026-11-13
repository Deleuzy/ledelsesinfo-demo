"""Fetch the two source tables from Statistikbanken's open API (no key needed).

STRAF11: reported crimes by municipality and type, per quarter.
STRAF22: reported crimes and reports with a charge, by municipality and type, per year.
Raw files are saved as they come, so every number can be traced back to a file.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

API = "https://api.statbank.dk/v1/data"

# The 9 municipalities Nordjyllands Politi covers (Thisted and Morsø are in Region Nordjylland
# but belong to Midt- og Vestjyllands Politi).
KREDS_KOMMUNER = {
    "851": "Aalborg",
    "810": "Brønderslev",
    "813": "Frederikshavn",
    "860": "Hjørring",
    "849": "Jammerbugt",
    "825": "Læsø",
    "846": "Mariagerfjord",
    "840": "Rebild",
    "820": "Vesthimmerland",
}
EXTRA_AREAS = {"000": "Hele landet", "081": "Region Nordjylland", "787": "Thisted", "773": "Morsø"}
TYPES = ["TOT", "1", "11", "12", "13", "14", "1000", "3"]


def _post(body: dict) -> str:
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (fixed public URL)
        return resp.read().decode("utf-8")


def fetch_all(raw_dir: Path) -> dict[str, Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    areas = list(KREDS_KOMMUNER) + list(EXTRA_AREAS)
    queries = {
        "STRAF11": [
            {"code": "OMRÅDE", "values": areas},
            {"code": "OVERTRÆD", "values": TYPES},
            {"code": "Tid", "values": ["*"]},
        ],
        "STRAF22": [
            {"code": "OMRÅDE", "values": areas},
            {"code": "OVERTRÆD", "values": TYPES},
            {"code": "ANMSIGT", "values": ["ANM", "SIG"]},
            {"code": "Tid", "values": ["*"]},
        ],
    }
    out = {}
    for table, variables in queries.items():
        text = _post({"table": table, "format": "BULK", "lang": "da", "valuePresentation": "Code", "variables": variables})
        path = raw_dir / f"{table}.csv"
        path.write_text(text, encoding="utf-8")
        out[table] = path
    return out


if __name__ == "__main__":
    for t, p in fetch_all(Path("data/raw")).items():
        print(t, p, sum(1 for _ in p.open()) - 1, "rows")
