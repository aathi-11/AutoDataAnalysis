"""
FastAPI Backend - Autonomous Data Analyst
"""
import io
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

from cleaner    import clean_data
from eda        import run_eda
from visualizer import generate_charts

app = FastAPI(title="Autonomous Data Analyst API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "message": "Autonomous Data Analyst API running"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        content = await file.read()
        # Try different encodings
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                df_raw = pd.read_csv(io.BytesIO(content), encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        if df_raw is None or df_raw.empty:
            raise HTTPException(status_code=400, detail="CSV is empty or could not be parsed.")

        # ── Pipeline ──────────────────────────────────────────────────────────
        df_clean, clean_report = clean_data(df_raw.copy())
        eda_report             = run_eda(df_clean)
        charts                 = generate_charts(df_clean)

        # ── Assemble response ─────────────────────────────────────────────────
        # Send first 50 rows as preview
        preview = df_clean.head(50).to_dict(orient="records")
        # Convert any non-serialisable types
        for row in preview:
            for k, v in row.items():
                if hasattr(v, "item"):
                    row[k] = v.item()
                elif str(v) == "nan":
                    row[k] = None

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
