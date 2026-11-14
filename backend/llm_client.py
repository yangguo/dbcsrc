"""Shared OpenAI-compatible client and model tiers.

Every module used to build its own openai.OpenAI instance, and only one had a
timeout or retry policy. This module owns the connection settings and the
model names so a timeout change is one edit.

Tiers:
    MODEL        heavy extraction and document understanding
    LIGHT_MODEL  classification, location, people, similarity
    VISION_MODEL OCR and image input

OPENAI_LIGHT_MODEL defaults to OPENAI_MODEL, so existing deployments keep
working until the lighter model is configured.
"""

import os
from typing import Optional

import openai

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_VISION_MODEL = "gpt-4-vision-preview"

MODEL = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
LIGHT_MODEL = os.getenv("OPENAI_LIGHT_MODEL", MODEL)
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", DEFAULT_VISION_MODEL)

_client: Optional[openai.OpenAI] = None


def get_client() -> openai.OpenAI:
    """Return one process-wide client with a bounded timeout and retries."""
    global _client
    if _client is None:
        _client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
            base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL),
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
        )
    return _client
