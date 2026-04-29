"""
FastAPI Backend - Autonomous Data Analyst (Phase 1 Upgraded)
"""
import io
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

from cleaner          import clean_data
from eda              import run_eda
from visualizer       import generate_charts
from ml_predictor     import run_automl
from anomaly_detector import detect_anomalies
from time_series      import analyze_time_series
from quality_scorecard import compute_quality_scorecard

app = FastAPI(title="Autonomous Data Analyst API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(content: bytes) -> pd.DataFrame:
    """Try common encodings, return parsed DataFrame."""
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(io.BytesIO(content), encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Cannot decode CSV with common encodings.")


def _serialise_preview(df: pd.DataFrame, n: int = 50):
    preview = df.head(n).to_dict(orient="records")
    for row in preview:
        for k, v in row.items():
            if hasattr(v, "item"):
                row[k] = v.item()
            elif str(v) in ("nan", "NaT"):
                row[k] = None
    return preview


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "message": "AutoAnalyst API v2.0 running (Phase 1 active)"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Original pipeline: clean → EDA → charts."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        content = await file.read()
        df_raw  = _read_csv(content)

        if df_raw is None or df_raw.empty:
            raise HTTPException(status_code=400, detail="CSV is empty or could not be parsed.")

        df_clean, clean_report = clean_data(df_raw.copy())
        eda_report             = run_eda(df_clean)
        charts                 = generate_charts(df_clean)
        preview                = _serialise_preview(df_clean)

        return JSONResponse({
            "filename":     file.filename,
            "cleaning":     clean_report,
            "eda":          eda_report,
            "charts":       charts,
            "preview":      preview,
            "preview_cols": df_clean.columns.tolist(),
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/phase1")
async def analyze_phase1(file: UploadFile = File(...)):
    """
    Full Phase 1 pipeline:
    clean → EDA → charts → AutoML → Anomaly Detection → Time Series → Quality Scorecard
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        content = await file.read()
        df_raw  = _read_csv(content)

        if df_raw is None or df_raw.empty:
            raise HTTPException(status_code=400, detail="CSV is empty or could not be parsed.")

        # ── Core pipeline ─────────────────────────────────────────────────────
        df_clean, clean_report = clean_data(df_raw.copy())
        eda_report             = run_eda(df_clean)
        charts                 = generate_charts(df_clean)
        preview                = _serialise_preview(df_clean)

        # ── Phase 1 additions ─────────────────────────────────────────────────
        ml_report       = run_automl(df_clean.copy())
        anomaly_report  = detect_anomalies(df_clean.copy())
        ts_report       = analyze_time_series(df_clean.copy())
        quality_report  = compute_quality_scorecard(df_clean.copy(), clean_report)

        return JSONResponse({
            "filename":     file.filename,
            "cleaning":     clean_report,
            "eda":          eda_report,
            "charts":       charts,
            "preview":      preview,
            "preview_cols": df_clean.columns.tolist(),
            # Phase 1
            "ml":           ml_report,
            "anomaly":      anomaly_report,
            "time_series":  ts_report,
            "quality":      quality_report,
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
