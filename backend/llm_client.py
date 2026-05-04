"""
LLM client helper that supports Gemini or Ollama via config.
"""
import json
import os
import re
import urllib.request
import urllib.error
from typing import Any, Optional

try:
    from dotenv import load_dotenv, find_dotenv
except Exception:
    load_dotenv = None
    find_dotenv = None

if load_dotenv and find_dotenv:
    load_dotenv(find_dotenv(), override=True)


def provider_name() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").strip().lower()


def is_configured() -> bool:
    provider = provider_name()
    if provider == "ollama":
        return True
    if provider == "gemini":
        try:
            from gemini_client import is_configured as gemini_is_configured
            return gemini_is_configured()
        except Exception:
            return False
    return False


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


def _generate_ollama(
    prompt: str,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1600,
) -> Any:
    model = model_name or os.getenv("OLLAMA_MODEL", "phi3")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "temperature": temperature,
        "options": {
            "num_predict": max_output_tokens,
        },
    }

    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    data = json.loads(body)
    text = data.get("response", "") or ""
    return _extract_json(text)


def generate_json(
    prompt: str,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 1600,
) -> Any:
    provider = provider_name()
    if provider == "ollama":
        return _generate_ollama(prompt, model_name, temperature, max_output_tokens)
    if provider == "gemini":
        from gemini_client import generate_json as gemini_generate_json
        return gemini_generate_json(prompt, model_name, temperature, max_output_tokens)

    raise RuntimeError(f"Unsupported LLM provider: {provider}")
