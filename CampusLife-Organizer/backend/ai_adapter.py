from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib import error, request

from dotenv import load_dotenv

load_dotenv()


def get_ai_provider() -> str:
    return (os.getenv("AI_PROVIDER") or "mock").strip().lower()


def get_gemma_api_key() -> str | None:
    return os.getenv("GEMMA_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_gemma_model() -> str:
    return os.getenv("GEMMA_MODEL") or "gemma-3-27b-it"


def _extract_json(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|```\s*$", "", candidate, flags=re.IGNORECASE | re.DOTALL)
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _call_google_api(api_key: str, model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    }).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def _call_openrouter(api_key: str, model: str, prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    req = request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://localhost",
        "X-Title": "CampusOS",
    }, method="POST")
    with request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8")


def _mock_analysis(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {
            "check_name": "task_scope",
            "status": "passed",
            "explanation": "The request was scoped to the requested campus workflow.",
            "evidence": ["task"],
            "requires_review": False,
        },
        {
            "check_name": "human_review",
            "status": "needs_review",
            "explanation": "Institutional decisions still require human approval.",
            "evidence": ["final_decision"],
            "requires_review": True,
        },
    ]
    if task == "leave_validation":
        checks.append({
            "check_name": "document_consistency",
            "status": "passed",
            "explanation": "Validation is running in mock mode for local demo purposes.",
            "evidence": ["submitted_form"],
            "requires_review": False,
        })
    return {
        "status": "ok",
        "summary": "Mock AI verification completed. Set AI_PROVIDER=gemma and GEMMA_API_KEY to use a real model.",
        "checks": checks,
    }


def run_ai_verification(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    provider = get_ai_provider()
    if provider == "mock":
        return _mock_analysis(task, payload)

    if provider == "gemma":
        api_key = get_gemma_api_key()
        if not api_key:
            return {
                "status": "fallback",
                "summary": "Gemma provider selected but no GEMMA_API_KEY was defined. Falling back to mock mode.",
                "checks": [
                    {
                        "check_name": "api_key_present",
                        "status": "failed",
                        "explanation": "No API key configured for the Gemma provider.",
                        "evidence": ["GEMMA_API_KEY"],
                        "requires_review": True,
                    }
                ],
            }

        model = get_gemma_model()
        prompt = (
            "You are a cautious campus workflow assistant. Return only valid JSON with keys: "
            "status, summary, checks. Each check must include check_name, status, explanation, evidence, requires_review. "
            "Do not claim any institutional decision is final without human approval. "
            f"Task: {task}. Input: {json.dumps(payload, ensure_ascii=False)}"
        )

        attempts = [
            ("google", model, lambda: _call_google_api(api_key, model, prompt)),
            ("google", "gemini-2.0-flash", lambda: _call_google_api(api_key, "gemini-2.0-flash", prompt)),
            ("openrouter", "google/gemma-3-27b-it", lambda: _call_openrouter(api_key, "google/gemma-3-27b-it", prompt)),
            ("openrouter", "google/gemma-3-27b-it:free", lambda: _call_openrouter(api_key, "google/gemma-3-27b-it:free", prompt)),
        ]

        last_error = None
        for kind, candidate_model, caller in attempts:
            try:
                raw = caller()
                if kind == "google":
                    parsed = json.loads(raw)
                    text = parsed["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    parsed = json.loads(raw)
                    text = parsed["choices"][0]["message"]["content"]
                result = _extract_json(text)
                if not result:
                    raise ValueError("No JSON object found in model response")
                if "checks" not in result:
                    result["checks"] = []
                return result
            except (error.HTTPError, error.URLError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                continue

        details = str(last_error) if last_error else "Unknown API error"
        return {
            "status": "error",
            "summary": f"Gemma API request failed with the configured key/model pair: {details}",
            "checks": [{
                "check_name": "api_request",
                "status": "failed",
                "explanation": "The provided Gemma key did not work with the configured endpoint or model. Update the key or model in .env.",
                "evidence": ["GEMMA_API_KEY", "GEMMA_MODEL"],
                "requires_review": True,
            }],
        }

    return _mock_analysis(task, payload)
