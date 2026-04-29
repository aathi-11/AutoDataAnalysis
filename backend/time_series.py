"""
Time Series Analysis Engine — Phase 1
Auto-detects datetime columns, computes trend, seasonality patterns,
rolling stats, and stationarity tests using statsmodels.
No Prophet required — pure statsmodels + pandas.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


def _safe(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if (np.isnan(v) or np.isinf(v)) else float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, pd.Timestamp):
        return str(v)
    return v


def _find_datetime_cols(df: pd.DataFrame) -> List[str]:
    return df.select_dtypes(include=["datetime64", "datetime"]).columns.tolist()


def _adf_test(series: pd.Series) -> Dict:
    """Augmented Dickey-Fuller stationarity test."""
    try:
        from statsmodels.tsa.stattools import adfuller
        result = adfuller(series.dropna(), autolag="AIC")
        return {
            "adf_statistic": round(float(result[0]), 4),
            "p_value":       round(float(result[1]), 4),
            "is_stationary": bool(result[1] < 0.05),
            "critical_values": {k: round(float(v), 4) for k, v in result[4].items()},
        }
    except Exception as e:
        return {"error": str(e)}


def _decompose(series: pd.Series, period: int = 12) -> Optional[Dict]:
    """Seasonal decomposition using statsmodels."""
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
        if len(series.dropna()) < period * 2:
            return None
        decomp = seasonal_decompose(series.dropna(), model="additive", period=period)
        # Return sampled arrays (max 200 points)
        step = max(1, len(series) // 200)
        return {
            "trend":    [_safe(v) for v in decomp.trend.values[::step]],
            "seasonal": [_safe(v) for v in decomp.seasonal.values[::step]],
            "residual": [_safe(v) for v in decomp.resid.values[::step]],
        }
    except Exception:
        return None


def analyze_time_series(df: pd.DataFrame) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    dt_cols = _find_datetime_cols(df)
    if not dt_cols:
        return {"error": "No datetime columns detected. Ensure dates are parsed correctly."}

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return {"error": "No numeric columns to analyse over time."}

    dt_col = dt_cols[0]
    result["datetime_column"] = dt_col
    result["numeric_columns"] = num_cols

    # Sort by datetime
    df_ts = df[[dt_col] + num_cols].copy().sort_values(dt_col).set_index(dt_col)

    result["date_range"] = {
        "start": str(df_ts.index.min()),
        "end":   str(df_ts.index.max()),
        "total_points": int(len(df_ts)),
    }

    # ── Infer frequency ───────────────────────────────────────────────────────
    try:
        inferred_freq = pd.infer_freq(df_ts.index)
        result["inferred_frequency"] = inferred_freq or "Irregular"
    except Exception:
        result["inferred_frequency"] = "Unknown"

    # ── Per numeric column analysis ───────────────────────────────────────────
    col_analyses = {}
    for col in num_cols[:5]:  # Limit to 5 columns
        series = df_ts[col].dropna()
        if len(series) < 5:
            continue

        # Sample for frontend (max 300 points)
        step = max(1, len(series) // 300)
        sampled_values = series.iloc[::step].values
        sampled_dates  = [str(d) for d in series.index[::step]]

        analysis = {
            "dates":  sampled_dates,
            "values": [_safe(v) for v in sampled_values],
        }

        # Basic stats
        analysis["stats"] = {
            "mean":   _safe(series.mean()),
            "std":    _safe(series.std()),
            "min":    _safe(series.min()),
            "max":    _safe(series.max()),
            "trend":  "Increasing" if series.iloc[-1] > series.iloc[0] else "Decreasing",
            "change_pct": round(
                (float(series.iloc[-1]) - float(series.iloc[0])) /
                max(abs(float(series.iloc[0])), 1e-9) * 100, 2
            ) if not (np.isnan(series.iloc[0]) or np.isnan(series.iloc[-1])) else None,
        }

        # Rolling statistics (window = 10% of length or 7)
        window = max(3, min(30, len(series) // 10))
        rolling_mean = series.rolling(window).mean()
        rolling_std  = series.rolling(window).std()
        step2 = max(1, len(rolling_mean) // 200)
        analysis["rolling"] = {
            "window": window,
            "mean":   [_safe(v) for v in rolling_mean.values[::step2]],
            "std":    [_safe(v) for v in rolling_std.values[::step2]],
            "dates":  [str(d) for d in rolling_mean.index[::step2]],
        }

        # Stationarity test
        analysis["stationarity"] = _adf_test(series)

        # Autocorrelation (lag 1-20)
        try:
            lags = min(20, len(series) - 2)
            acf_vals = [_safe(series.autocorr(lag=i)) for i in range(1, lags + 1)]
            analysis["autocorrelation"] = acf_vals
        except Exception:
            analysis["autocorrelation"] = []

        # Decomposition (only if enough data)
        period = 12 if "M" in (result.get("inferred_frequency") or "") else \
                  7  if "D" in (result.get("inferred_frequency") or "") else 12
        decomp = _decompose(series, period=period)
        if decomp:
            analysis["decomposition"] = decomp

        col_analyses[col] = analysis

    result["columns"] = col_analyses

    # ── Cross-column correlations over time ───────────────────────────────────
    if len(num_cols) >= 2:
        corr = df_ts[num_cols].corr()
        pairs = []
        cols = num_cols
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                v = corr.iloc[i, j]
                if not np.isnan(v):
                    pairs.append({"col1": cols[i], "col2": cols[j], "corr": round(float(v), 4)})
        pairs.sort(key=lambda x: abs(x["corr"]), reverse=True)
        result["time_correlations"] = pairs[:5]

    return result
