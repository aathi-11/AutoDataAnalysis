"""
AutoML Predictor — Phase 1
Auto-detects the best target column, trains Classification or Regression models
using scikit-learn (+ XGBoost if available), returns metrics & feature importances.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from typing import Dict, Any, List

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    mean_absolute_error, mean_squared_error, r2_score
)

try:
    from xgboost import XGBClassifier, XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


def _safe(v):
    """Convert numpy types to JSON-serialisable Python."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


def _pick_target(df: pd.DataFrame):
    """
    Heuristically pick the best target column:
    - Prefer columns with low cardinality (<= 20 unique) for classification
    - Otherwise pick the numeric column with highest variance for regression
    Returns (target_col, task_type)
    """
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # Try categorical target first (classification)
    for col in cat_cols:
        n = df[col].nunique()
        if 2 <= n <= 20:
            return col, "classification"

    # Try low-cardinality numeric (classification)
    for col in num_cols:
        n = df[col].nunique()
        if 2 <= n <= 10:
            return col, "classification"

    # Fall back to regression on highest-variance numeric column
    if num_cols:
        variances = df[num_cols].var()
        target = variances.idxmax()
        return target, "regression"

    return None, None


def run_automl(df: pd.DataFrame) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    if len(df) < 20:
        return {"error": "Dataset too small for ML (need ≥ 20 rows)."}

    target_col, task = _pick_target(df)
    if target_col is None:
        return {"error": "No suitable target column found for ML."}

    result["target_column"] = target_col
    result["task_type"]     = task

    # ── Feature / Target split ────────────────────────────────────────────────
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_col]
    if not feature_cols:
        return {"error": "No numeric feature columns available after excluding target."}

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # Encode target for classification
    le = None
    if task == "classification":
        le = LabelEncoder()
        y = le.fit_transform(y.astype(str))
        class_labels = le.classes_.tolist()
        result["class_labels"] = class_labels
    else:
        y = pd.to_numeric(y, errors="coerce")
        X = X[y.notna()]
        y = y[y.notna()]

    # Drop rows with NaN target
    mask = pd.notna(y) if task == "regression" else np.ones(len(y), dtype=bool)
    X = X[mask]; y = np.array(y)[mask]

    if len(X) < 20:
        return {"error": "Not enough valid rows after cleaning for ML."}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ── Model zoo ─────────────────────────────────────────────────────────────
    if task == "classification":
        models: List = [
            ("Random Forest",       RandomForestClassifier(n_estimators=100, random_state=42)),
            ("Gradient Boosting",   GradientBoostingClassifier(n_estimators=100, random_state=42)),
            ("Logistic Regression", LogisticRegression(max_iter=1000, random_state=42)),
        ]
        if HAS_XGB:
            models.append(("XGBoost", XGBClassifier(n_estimators=100, random_state=42,
                                                      eval_metric="logloss", verbosity=0)))
    else:
        models = [
            ("Random Forest",     RandomForestRegressor(n_estimators=100, random_state=42)),
            ("Gradient Boosting", GradientBoostingRegressor(n_estimators=100, random_state=42)),
            ("Ridge Regression",  Ridge()),
        ]
        if HAS_XGB:
            models.append(("XGBoost", XGBRegressor(n_estimators=100, random_state=42, verbosity=0)))

    # ── Train & evaluate ──────────────────────────────────────────────────────
    preprocessor = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale",  StandardScaler()),
    ])
    X_train_p = preprocessor.fit_transform(X_train)
    X_test_p  = preprocessor.transform(X_test)

    model_results = []
    best_score   = -np.inf
    best_model   = None
    best_name    = ""

    for name, mdl in models:
        try:
            mdl.fit(X_train_p, y_train)
            preds = mdl.predict(X_test_p)

            if task == "classification":
                avg = "binary" if len(np.unique(y)) == 2 else "weighted"
                metrics = {
                    "accuracy":  round(_safe(accuracy_score(y_test, preds)), 4),
                    "f1_score":  round(_safe(f1_score(y_test, preds, average=avg, zero_division=0)), 4),
                    "precision": round(_safe(precision_score(y_test, preds, average=avg, zero_division=0)), 4),
                    "recall":    round(_safe(recall_score(y_test, preds, average=avg, zero_division=0)), 4),
                }
                score = metrics["accuracy"]
            else:
                mse = mean_squared_error(y_test, preds)
                metrics = {
                    "r2":   round(_safe(r2_score(y_test, preds)), 4),
                    "mae":  round(_safe(mean_absolute_error(y_test, preds)), 4),
                    "rmse": round(_safe(float(np.sqrt(mse))), 4),
                }
                score = metrics["r2"]

            model_results.append({"model": name, "metrics": metrics})
            if score > best_score:
                best_score = score
                best_model = mdl
                best_name  = name
        except Exception as e:
            model_results.append({"model": name, "error": str(e)})

    result["models"] = model_results
    result["best_model"] = best_name
    result["best_score"] = round(best_score, 4) if best_score > -np.inf else None

    # ── Feature Importances (from best model) ─────────────────────────────────
    if best_model is not None and hasattr(best_model, "feature_importances_"):
        imps = best_model.feature_importances_
        fi   = sorted(
            zip(feature_cols, imps.tolist()),
            key=lambda x: x[1], reverse=True
        )
        result["feature_importances"] = [
            {"feature": f, "importance": round(float(imp), 5)} for f, imp in fi
        ]

    result["feature_columns"] = feature_cols
    result["train_size"]      = int(len(X_train))
    result["test_size"]       = int(len(X_test))

    return result
