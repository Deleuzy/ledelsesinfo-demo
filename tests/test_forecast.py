import numpy as np

from lidemo.forecast import backtest, forecast, seasonal_naive


def test_seasonal_naive_repeats_last_year():
    y = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
    assert list(seasonal_naive(y, 6)) == [5, 6, 7, 8, 5, 6]


def test_backtest_prefers_seasonal_method_on_seasonal_data():
    y = np.tile([100.0, 140.0, 120.0, 90.0], 10)
    bt = backtest(y, holdout=8)
    assert bt["metode"].iloc[0] in {"Sæsonnaiv (samme kvartal sidste år)", "Holt-Winters (trend og sæson)"}
    assert bt["MAE"].iloc[0] < 1.0


def test_forecast_band_is_positive_and_length_matches():
    rng = np.random.default_rng(0)
    y = 500 + np.tile([0.0, 40, 20, -30], 12) + rng.normal(0, 10, 48)
    bt, fc, band = forecast(y, h=4)
    assert len(fc) == 4 and band > 0
    assert set(bt.columns) == {"metode", "MAE", "MAPE"}
