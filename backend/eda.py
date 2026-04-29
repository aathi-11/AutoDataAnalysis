"""
EDA Engine
Generates comprehensive exploratory data analysis statistics.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any


def _safe_val(v):
    """Convert numpy types to Python native for JSON serialisation."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.ndarray,)):
        return v.tolist()
    if pd.isna(v) if not isinstance(v, (list, dict)) else False:
        return None
    return v


def run_eda(df: pd.DataFrame) -> Dict[str, Any]:
    num_df = df.select_dtypes(include=[np.number])
    cat_df = df.select_dtypes(include=["object", "category"])
    dt_df  = df.select_dtypes(include=["datetime64"])

    eda = {}

    # ── Overview ──────────────────────────────────────────────────────────────
    eda["overview"] = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "numeric_columns": int(len(num_df.columns)),
        "categorical_columns": int(len(cat_df.columns)),
        "datetime_columns": int(len(dt_df.columns)),
        "total_cells": int(df.size),
        "missing_cells": int(df.isnull().sum().sum()),
        "missing_pct": round(df.isnull().sum().sum() / max(df.size, 1) * 100, 2),
        "memory_usage_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
        "duplicate_rows": int(df.duplicated().sum()),
    }

    # ── Column Details ────────────────────────────────────────────────────────
    col_details = []
    for col in df.columns:
        s = df[col]
        detail = {
            "name": col,
            "dtype": str(s.dtype),
            "missing": int(s.isnull().sum()),
            "missing_pct": round(s.isnull().sum() / len(df) * 100, 2),
            "unique": int(s.nunique()),
            "unique_pct": round(s.nunique() / max(len(df), 1) * 100, 2),
        }
        if s.dtype in [np.float64, np.int64, float, int]:
            detail.update({
                "mean": _safe_val(s.mean()),
                "std": _safe_val(s.std()),
                "min": _safe_val(s.min()),
                "q25": _safe_val(s.quantile(0.25)),
                "median": _safe_val(s.median()),
                "q75": _safe_val(s.quantile(0.75)),
                "max": _safe_val(s.max()),
                "skewness": _safe_val(s.skew()),
                "kurtosis": _safe_val(s.kurt()),
            })
        elif s.dtype == object:
            vc = s.value_counts().head(5)
            detail["top_values"] = {str(k): int(v) for k, v in vc.items()}
            detail["avg_length"] = _safe_val(s.dropna().astype(str).str.len().mean())
        col_details.append(detail)
    eda["columns"] = col_details

    # ── Numeric Statistics ────────────────────────────────────────────────────
    if not num_df.empty:
        desc = num_df.describe().T
        eda["numeric_summary"] = {
            col: {k: _safe_val(v) for k, v in desc.loc[col].items()}
            for col in desc.index
        }

    # ── Correlation Matrix ────────────────────────────────────────────────────
    if len(num_df.columns) >= 2:
        corr = num_df.corr()
        eda["correlation"] = {
            col: {c: _safe_val(v) for c, v in row.items()}
            for col, row in corr.to_dict().items()
        }

        # Top correlated pairs
        corr_pairs = []
        cols = corr.columns.tolist()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                val = _safe_val(corr.iloc[i, j])
                if val is not None:
                    corr_pairs.append({"col1": cols[i], "col2": cols[j], "corr": round(val, 4)})
        corr_pairs.sort(key=lambda x: abs(x["corr"]), reverse=True)
        eda["top_correlations"] = corr_pairs[:10]

    # ── Categorical Summary ───────────────────────────────────────────────────
    if not cat_df.empty:
        cat_summary = {}
        for col in cat_df.columns:
            vc = df[col].value_counts().head(10)
            cat_summary[col] = {
                "unique_count": int(df[col].nunique()),
                "top_values": {str(k): int(v) for k, v in vc.items()},
            }
        eda["categorical_summary"] = cat_summary

    # ── Insights / Flags ──────────────────────────────────────────────────────
    insights = []
    for col in num_df.columns:
        skew = num_df[col].skew()
        if abs(skew) > 1:
            direction = "positively" if skew > 0 else "negatively"
            insights.append(f"**{col}** is {direction} skewed (skewness={skew:.2f}). Consider log-transform.")
    if eda["overview"]["missing_pct"] > 5:
        insights.append(f"Dataset has {eda['overview']['missing_pct']}% missing data — review imputation strategy.")
    if eda["overview"]["duplicate_rows"] > 0:
        insights.append(f"{eda['overview']['duplicate_rows']} duplicate rows detected.")
    if len(num_df.columns) >= 2 and "top_correlations" in eda:
        top = eda["top_correlations"][0] if eda["top_correlations"] else None
        if top and abs(top["corr"]) > 0.8:
            insights.append(f"Strong correlation ({top['corr']}) between **{top['col1']}** and **{top['col2']}** — possible multicollinearity.")

    eda["insights"] = insights
    return eda
