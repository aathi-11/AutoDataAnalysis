"""
Anomaly Detection Engine — Phase 1
Uses Isolation Forest to detect anomalies in numeric data.
Returns anomaly scores, flags, and statistics.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from typing import Dict, Any

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


def _safe(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> Dict[str, Any]:
    """
    Run Isolation Forest anomaly detection on numeric columns.

    Returns:
        - total_anomalies: int
        - anomaly_pct: float
        - contamination_used: float
        - anomaly_rows: list of {row_index, anomaly_score, columns}
        - column_stats: per-column stats for anomalous rows vs normal rows
        - top_anomaly_cols: columns most responsible for anomalies
    """
    result: Dict[str, Any] = {}

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return {"error": "No numeric columns found for anomaly detection."}
    if len(df) < 10:
        return {"error": "Dataset too small for anomaly detection (need ≥ 10 rows)."}

    X = df[num_cols].copy()

    # Preprocess
    preprocessor = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale",  StandardScaler()),
    ])
    X_proc = preprocessor.fit_transform(X)

    # Fit Isolation Forest
    clf = IsolationForest(
        contamination=contamination,
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )
    preds  = clf.fit_predict(X_proc)    # -1 = anomaly, 1 = normal
    scores = clf.score_samples(X_proc)  # more negative = more anomalous

    is_anomaly = preds == -1
    anomaly_idx = np.where(is_anomaly)[0]

    result["total_anomalies"]     = int(is_anomaly.sum())
    result["total_rows"]          = int(len(df))
    result["anomaly_pct"]         = round(float(is_anomaly.mean() * 100), 2)
    result["contamination_used"]  = contamination
    result["numeric_cols_used"]   = num_cols

    # Top anomalous rows (max 50)
    sorted_idx = anomaly_idx[np.argsort(scores[anomaly_idx])][:50]
    anomaly_rows = []
    for i in sorted_idx:
        row = {"row_index": int(i), "anomaly_score": round(float(scores[i]), 4)}
        for col in num_cols:
            row[col] = _safe(df[num_cols].iloc[i][col])
        anomaly_rows.append(row)
    result["anomaly_rows"] = anomaly_rows

    # Per-column mean comparison: anomalous vs normal
    df_num = df[num_cols].copy()
    df_num["__anomaly__"] = is_anomaly
    col_stats = {}
    for col in num_cols:
        normal_mean    = _safe(df_num.loc[~df_num["__anomaly__"], col].mean())
        anomaly_mean   = _safe(df_num.loc[ df_num["__anomaly__"], col].mean())
        diff_pct = None
        if normal_mean and normal_mean != 0:
            diff_pct = round(abs((anomaly_mean - normal_mean) / normal_mean) * 100, 2) if anomaly_mean is not None else None
        col_stats[col] = {
            "normal_mean":  normal_mean,
            "anomaly_mean": anomaly_mean,
            "diff_pct":     diff_pct,
        }
    result["column_stats"] = col_stats

    # Top columns driving anomalies (by largest diff_pct)
    ranked = sorted(
        [(col, col_stats[col]["diff_pct"] or 0) for col in num_cols],
        key=lambda x: x[1], reverse=True
    )
    result["top_anomaly_cols"] = [{"col": c, "diff_pct": round(d, 2)} for c, d in ranked[:5]]

    # Anomaly score distribution summary
    result["score_summary"] = {
        "min":    round(float(scores.min()), 4),
        "max":    round(float(scores.max()), 4),
        "mean":   round(float(scores.mean()), 4),
        "threshold": round(float(np.percentile(scores, contamination * 100)), 4),
    }

    return result
