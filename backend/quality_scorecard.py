"""
Data Quality Scorecard — Phase 1
Computes a detailed, multi-dimensional quality score with grades per dimension.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any


def _safe(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    return v


def _grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


def compute_quality_scorecard(df: pd.DataFrame, clean_report: dict) -> Dict[str, Any]:
    """
    Computes a 7-dimension Data Quality Scorecard.

    Dimensions:
      1. Completeness   — how much data is present (not missing)
      2. Uniqueness     — absence of duplicates
      3. Consistency    — uniformity of dtypes and formatting
      4. Validity       — absence of outliers
      5. Timeliness     — presence of date columns (proxy)
      6. Conformity     — correct data types inferred
      7. Integrity      — low null rate + structural soundness
    """
    rows, cols = df.shape
    total_cells = rows * cols
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    dt_cols  = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # ── 1. Completeness ───────────────────────────────────────────────────────
    missing_cells = int(df.isnull().sum().sum())
    completeness  = max(0.0, (1 - missing_cells / max(total_cells, 1)) * 100)

    # ── 2. Uniqueness ─────────────────────────────────────────────────────────
    dup_rows   = int(df.duplicated().sum())
    uniqueness = max(0.0, (1 - dup_rows / max(rows, 1)) * 100)

    # ── 3. Consistency ────────────────────────────────────────────────────────
    # Penalty for mixed-type columns (object columns that should be numeric but aren't)
    inconsistent = 0
    for col in cat_cols:
        try:
            numeric_rate = pd.to_numeric(df[col], errors="coerce").notna().mean()
            if 0.2 < numeric_rate < 0.8:
                inconsistent += 1
        except Exception:
            pass
    consistency = max(0.0, 100 - (inconsistent / max(cols, 1)) * 50)

    # ── 4. Validity (outlier-based) ───────────────────────────────────────────
    total_outliers = 0
    for col in num_cols:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        if IQR > 0:
            n_out = int(((df[col] < Q1 - 3 * IQR) | (df[col] > Q3 + 3 * IQR)).sum())
            total_outliers += n_out
    outlier_rate = total_outliers / max(rows * max(len(num_cols), 1), 1)
    validity = max(0.0, (1 - outlier_rate) * 100)

    # ── 5. Timeliness ─────────────────────────────────────────────────────────
    # Proxy: presence of datetime columns, date recency
    if dt_cols:
        timeliness = 85.0  # has temporal data; can't truly assess without domain context
    else:
        timeliness = 50.0  # no time data → partial credit

    # ── 6. Conformity ─────────────────────────────────────────────────────────
    # Proportion of columns with correctly inferred types
    correctly_typed = len(num_cols) + len(dt_cols)
    total_cols_used = len(num_cols) + len(dt_cols) + len(cat_cols)
    # Penalise cat cols that look numeric
    conformity_penalty = sum(
        1 for col in cat_cols
        if pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.8
    )
    conformity = max(0.0, (correctly_typed / max(total_cols_used, 1)) * 100 - conformity_penalty * 5)

    # ── 7. Integrity ─────────────────────────────────────────────────────────
    null_rate   = missing_cells / max(total_cells, 1)
    dup_rate    = dup_rows / max(rows, 1)
    integrity   = max(0.0, 100 - null_rate * 50 - dup_rate * 30 - (inconsistent / max(cols, 1)) * 20)

    # ── Overall Weighted Score ────────────────────────────────────────────────
    weights = {
        "completeness":  0.25,
        "uniqueness":    0.15,
        "consistency":   0.15,
        "validity":      0.15,
        "timeliness":    0.10,
        "conformity":    0.10,
        "integrity":     0.10,
    }
    scores = {
        "completeness":  round(completeness, 1),
        "uniqueness":    round(uniqueness, 1),
        "consistency":   round(consistency, 1),
        "validity":      round(validity, 1),
        "timeliness":    round(timeliness, 1),
        "conformity":    round(conformity, 1),
        "integrity":     round(integrity, 1),
    }
    overall = sum(scores[dim] * weights[dim] for dim in weights)

    dimensions = []
    for dim, score in scores.items():
        dimensions.append({
            "name":        dim.capitalize(),
            "score":       score,
            "grade":       _grade(score),
            "weight":      int(weights[dim] * 100),
            "description": _dim_description(dim, score, df, clean_report),
        })

    # ── Column-level quality ──────────────────────────────────────────────────
    col_quality = []
    for col in df.columns:
        s = df[col]
        miss_pct  = round(s.isnull().mean() * 100, 1)
        unique_pct = round(s.nunique() / max(len(df), 1) * 100, 1)
        cq = {
            "column":     col,
            "dtype":      str(s.dtype),
            "missing_pct": miss_pct,
            "unique_pct":  unique_pct,
            "score":       round(max(0, 100 - miss_pct - (10 if unique_pct > 95 and str(s.dtype) == "object" else 0)), 1),
        }
        cq["grade"] = _grade(cq["score"])
        col_quality.append(cq)

    # ── Issues list ───────────────────────────────────────────────────────────
    issues = []
    if missing_cells > 0:
        issues.append(f"⚠ {missing_cells:,} missing cells ({round(null_rate*100,1)}% of data)")
    if dup_rows > 0:
        issues.append(f"⚠ {dup_rows:,} duplicate rows detected")
    if total_outliers > 0:
        issues.append(f"⚠ {total_outliers:,} extreme outliers found (3×IQR)")
    if inconsistent > 0:
        issues.append(f"⚠ {inconsistent} column(s) with inconsistent data types")
    if not dt_cols:
        issues.append("ℹ No datetime columns — timeliness cannot be fully assessed")

    recommendations = []
    if completeness < 80:
        recommendations.append("🔧 High missing data — review imputation or collection strategy")
    if uniqueness < 95:
        recommendations.append("🔧 Remove duplicate rows before modelling")
    if validity < 80:
        recommendations.append("🔧 Investigate extreme outliers — may skew model performance")
    if conformity < 70:
        recommendations.append("🔧 Convert categorical columns storing numbers to numeric dtype")

    return {
        "overall_score": round(overall, 1),
        "overall_grade": _grade(overall),
        "dimensions":    dimensions,
        "column_quality": col_quality,
        "issues":         issues,
        "recommendations": recommendations,
        "summary": {
            "total_rows":    rows,
            "total_cols":    cols,
            "missing_cells": missing_cells,
            "duplicate_rows": dup_rows,
            "outlier_cells": total_outliers,
            "numeric_cols":  len(num_cols),
            "categorical_cols": len(cat_cols),
            "datetime_cols": len(dt_cols),
        },
    }


def _dim_description(dim: str, score: float, df: pd.DataFrame, report: dict) -> str:
    msgs = {
        "completeness":  f"{round((1 - df.isnull().mean().mean()) * 100, 1)}% of all cells are filled.",
        "uniqueness":    f"{int(df.duplicated().sum())} duplicate rows detected.",
        "consistency":   f"Column type consistency evaluated across {len(df.columns)} columns.",
        "validity":      f"Outlier check using 3×IQR method on numeric columns.",
        "timeliness":    "Datetime columns presence used as timeliness proxy.",
        "conformity":    f"Data types: {df.select_dtypes(include=[np.number]).shape[1]} numeric, "
                        f"{df.select_dtypes(include='object').shape[1]} categorical, "
                        f"{df.select_dtypes(include='datetime64').shape[1]} datetime.",
        "integrity":     "Combined assessment of nulls, duplicates, and type inconsistencies.",
    }
    return msgs.get(dim, "")
