"""
Data Cleaning Engine
Handles: missing values, duplicates, outliers, type inference
"""
import pandas as pd
import numpy as np
from typing import Dict, Any


def clean_data(df: pd.DataFrame) -> Dict[str, Any]:
    original_shape = df.shape
    report = {
        "original_rows": int(original_shape[0]),
        "original_cols": int(original_shape[1]),
        "steps": []
    }

    # ── 1. Standardise column names ───────────────────────────────────────────
    old_cols = df.columns.tolist()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )
    renamed = {o: n for o, n in zip(old_cols, df.columns.tolist()) if o != n}
    if renamed:
        report["steps"].append({
            "step": "Column Name Standardisation",
            "detail": f"Renamed {len(renamed)} column(s): {renamed}"
        })

    # ── 2. Infer & cast dtypes ────────────────────────────────────────────────
    type_changes = {}
    for col in df.columns:
        if df[col].dtype == object:
            # Try numeric
            converted = pd.to_numeric(df[col].str.replace(",", "", regex=False), errors="coerce")
            if converted.notna().mean() > 0.7:
                df[col] = converted
                type_changes[col] = "object → numeric"
                continue
            # Try datetime
            try:
                converted_dt = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
                if converted_dt.notna().mean() > 0.7:
                    df[col] = converted_dt
                    type_changes[col] = "object → datetime"
            except Exception:
                pass
    if type_changes:
        report["steps"].append({
            "step": "Data Type Inference",
            "detail": f"Updated {len(type_changes)} column(s): {type_changes}"
        })

    # ── 3. Remove duplicate rows ──────────────────────────────────────────────
    dupes = int(df.duplicated().sum())
    if dupes:
        df.drop_duplicates(inplace=True)
        report["steps"].append({
            "step": "Duplicate Removal",
            "detail": f"Removed {dupes} duplicate row(s)."
        })

    # ── 4. Missing value handling ─────────────────────────────────────────────
    missing_before = df.isnull().sum()
    missing_cols = missing_before[missing_before > 0]
    imputed = {}

    for col in missing_cols.index:
        pct = missing_before[col] / len(df) * 100
        if pct > 60:
            df.drop(columns=[col], inplace=True)
            imputed[col] = f"Dropped (>{60}% missing)"
        elif df[col].dtype in [np.float64, np.int64, float, int]:
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)
            imputed[col] = f"Filled with median ({median_val:.4g})"
        else:
            mode_val = df[col].mode()
            if not mode_val.empty:
                df[col].fillna(mode_val[0], inplace=True)
                imputed[col] = f"Filled with mode ('{mode_val[0]}')"

    if imputed:
        report["steps"].append({
            "step": "Missing Value Imputation",
            "detail": imputed
        })

    # ── 5. Outlier capping (IQR, numeric only) ────────────────────────────────
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    outlier_info = {}
    for col in num_cols:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        n_out = int(((df[col] < lower) | (df[col] > upper)).sum())
        if n_out > 0:
            df[col] = df[col].clip(lower, upper)
            outlier_info[col] = f"{n_out} outlier(s) capped to [{lower:.4g}, {upper:.4g}]"
    if outlier_info:
        report["steps"].append({
            "step": "Outlier Capping (IQR × 1.5)",
            "detail": outlier_info
        })

    report["cleaned_rows"] = int(len(df))
    report["cleaned_cols"] = int(len(df.columns))
    report["rows_removed"] = report["original_rows"] - report["cleaned_rows"]

    # Quality score: simple heuristic
    base = 100
    if report["rows_removed"]:
        base -= min(20, report["rows_removed"] / max(report["original_rows"], 1) * 100)
    if missing_cols.shape[0]:
        base -= min(20, missing_cols.shape[0] / max(original_shape[1], 1) * 100)
    if dupes:
        base -= min(10, dupes / max(original_shape[0], 1) * 100)
    report["quality_score"] = round(max(0, base), 1)

    return df, report
