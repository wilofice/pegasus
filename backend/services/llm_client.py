"""Client for external LLM providers."""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/completions")
API_KEY = os.environ.get("LLM_API_KEY")


def generate(prompt: str) -> str:
    """Send the prompt to the LLM provider and return the answer."""
    if not API_KEY:
        raise RuntimeError("LLM_API_KEY not configured")

    headers = {"Authorization": f"Bearer {API_KEY}"}
    data: dict[str, Any] = {
        "model": "gpt-3.5-turbo",
        "prompt": prompt,
        "max_tokens": 256,
    }
    resp = requests.post(API_URL, json=data, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result.get("choices", [{}])[0].get("text", "")
