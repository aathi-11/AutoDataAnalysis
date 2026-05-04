"""
Phase 2 AI features driven by a configurable LLM.
Produces correlation insights, chart recommendations, hypotheses, and a narrative report.
"""
import json
from typing import Any, Dict, List

from llm_client import generate_json, is_configured, provider_name


def _compact_columns(cols: List[Dict[str, Any]], limit: int = 25) -> List[Dict[str, Any]]:
    compact = []
    for col in cols[:limit]:
        compact.append({
            "name": col.get("name"),
            "dtype": col.get("dtype"),
            "missing_pct": col.get("missing_pct"),
            "unique": col.get("unique"),
            "mean": col.get("mean"),
            "std": col.get("std"),
            "min": col.get("min"),
            "max": col.get("max"),
        })
    return compact


def _summary_block(phase1: Dict[str, Any]) -> Dict[str, Any]:
    quality = phase1.get("quality") or {}
    ml = phase1.get("ml") or {}
    anomaly = phase1.get("anomaly") or {}
    ts = phase1.get("time_series") or {}

    return {
        "quality": {
            "overall_score": quality.get("overall_score"),
            "overall_grade": quality.get("overall_grade"),
            "issues": (quality.get("issues") or [])[:5],
        },
        "ml": {
            "task_type": ml.get("task_type"),
            "target_column": ml.get("target_column"),
            "best_model": ml.get("best_model"),
            "best_score": ml.get("best_score"),
            "error": ml.get("error"),
        },
        "anomaly": {
            "total_anomalies": anomaly.get("total_anomalies"),
            "anomaly_pct": anomaly.get("anomaly_pct"),
            "error": anomaly.get("error"),
        },
        "time_series": {
            "datetime_column": ts.get("datetime_column"),
            "inferred_frequency": ts.get("inferred_frequency"),
            "error": ts.get("error"),
        },
    }


def _build_prompt(context: Dict[str, Any]) -> str:
    schema_hint = (
        "Return JSON only with this schema:\n"
        "{\n"
        "  \"correlation_detective\": {\n"
        "    \"summary\": string,\n"
        "    \"pairs\": [\n"
        "      {\"pair\": string, \"corr\": number, \"insight\": string, \"risk\": string}\n"
        "    ]\n"
        "  },\n"
        "  \"chart_recommender\": {\n"
        "    \"recommendations\": [\n"
        "      {\"title\": string, \"chart_type\": string, \"columns\": [string],\n"
        "       \"why\": string, \"priority\": \"high\"|\"medium\"|\"low\"}\n"
        "    ]\n"
        "  },\n"
        "  \"hypothesis_tester\": {\n"
        "    \"hypotheses\": [\n"
        "      {\"hypothesis\": string, \"rationale\": string, \"test\": string,\n"
        "       \"required_columns\": [string]}\n"
        "    ]\n"
        "  },\n"
        "  \"auto_report\": {\n"
        "    \"executive_summary\": string,\n"
        "    \"key_findings\": [string],\n"
        "    \"risks\": [string],\n"
        "    \"recommendations\": [string]\n"
        "  }\n"
        "}\n"
        "Rules: Use concise language, 3-5 items per list, and no markdown or code fences.\n"
    )

    payload = json.dumps(context, indent=2)
    return (
        "You are a data analyst copilot. Use the dataset summary to produce insights.\n"
        f"{schema_hint}\n"
        "Dataset summary JSON:\n"
        f"{payload}\n"
    )


def run_phase2_ai(phase1: Dict[str, Any]) -> Dict[str, Any]:
    if not is_configured():
        provider = provider_name()
        if provider == "ollama":
            return {
                "error": "Ollama not available. Start Ollama or set OLLAMA_BASE_URL/OLLAMA_MODEL.",
            }
        if provider == "gemini":
            return {
                "error": "Gemini not configured. Set GEMINI_API_KEY and install google-generativeai.",
            }
        return {
            "error": f"Unsupported LLM provider: {provider}. Use LLM_PROVIDER=gemini or ollama.",
        }

    eda = phase1.get("eda") or {}
    context = {
        "overview": eda.get("overview"),
        "columns": _compact_columns(eda.get("columns") or []),
        "top_correlations": (eda.get("top_correlations") or [])[:8],
        "summary": _summary_block(phase1),
    }

    try:
        return generate_json(_build_prompt(context))
    except Exception as exc:
        return {"error": str(exc)}
