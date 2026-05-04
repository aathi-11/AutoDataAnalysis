"""
Gemini client helper.
Handles configuration, JSON-only generation, and safe parsing.
"""
import json
import os
import re
from typing import Any, Optional

try:
    from dotenv import load_dotenv, find_dotenv
except Exception:
    load_dotenv = None
    find_dotenv = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

if load_dotenv and find_dotenv:
    load_dotenv(find_dotenv(), override=True)


def is_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY")) and genai is not None


def _strip_code_fences(text: str) -> str:
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    return cleaned.replace("```", "").strip()


def _extract_json(text: str) -> Any:
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    obj_start = cleaned.find("{")
    obj_end = cleaned.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        return json.loads(cleaned[obj_start:obj_end + 1])

    arr_start = cleaned.find("[")
    arr_end = cleaned.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        return json.loads(cleaned[arr_start:arr_end + 1])

    raise ValueError("No JSON content found in model response.")


def generate_json(
    prompt: str,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1600,
) -> Any:
    if not is_configured():
        raise RuntimeError("Gemini not configured. Set GEMINI_API_KEY and install google-generativeai.")

    api_key = os.getenv("GEMINI_API_KEY")
    model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    genai.configure(api_key=api_key)
    client = genai.GenerativeModel(model)
    resp = client.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        },
    )

    text = getattr(resp, "text", "") or ""
    return _extract_json(text)
