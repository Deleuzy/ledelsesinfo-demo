"""Simple, explainable forecasts for a quarterly series, judged on a backtest.

Each method is tried on the last `holdout` quarters as if they were unknown (rolling origin,
one step ahead), and the one with the lowest MAE is used for the next quarters.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def naive(y: np.ndarray, h: int) -> np.ndarray:
    return np.repeat(y[-1], h)


def seasonal_naive(y: np.ndarray, h: int, m: int = 4) -> np.ndarray:
    return np.array([y[-m + (i % m)] for i in range(h)], dtype=float)


def moving_average(y: np.ndarray, h: int, k: int = 4) -> np.ndarray:
    return np.repeat(y[-k:].mean(), h)


def holt_winters(y: np.ndarray, h: int, m: int = 4) -> np.ndarray:
    model = ExponentialSmoothing(y, trend="add", seasonal="add", seasonal_periods=m, initialization_method="estimated")
    return np.asarray(model.fit().forecast(h))


METHODS = {
    "Naiv (sidste kvartal)": naive,
    "Sæsonnaiv (samme kvartal sidste år)": seasonal_naive,
    "Glidende gennemsnit (4 kvartaler)": moving_average,
    "Holt-Winters (trend og sæson)": holt_winters,
}


def backtest(y: np.ndarray, holdout: int = 8) -> pd.DataFrame:
    rows = []
    for name, f in METHODS.items():
        errs, pct = [], []
        for i in range(len(y) - holdout, len(y)):
            pred = f(y[:i], 1)[0]
            errs.append(abs(y[i] - pred))
            pct.append(abs(y[i] - pred) / y[i])
        rows.append({"metode": name, "MAE": float(np.mean(errs)), "MAPE": float(np.mean(pct))})
    return pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)


def forecast(y: np.ndarray, h: int = 4, holdout: int = 8) -> tuple[pd.DataFrame, np.ndarray, float]:
    """Return the backtest table, the forecast of the best method and a rough ±band (1.96 × backtest MAE × 1.25)."""
    bt = backtest(y, holdout)
    best = bt["metode"].iloc[0]
    fc = METHODS[best](y, h)
    band = 1.96 * 1.25 * bt["MAE"].iloc[0]  # MAE × 1.25 ≈ standard deviation for normal errors
    return bt, fc, band
