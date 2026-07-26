"""Thin OpenAI-compatible LLM client wrapper."""

from __future__ import annotations

import json
import logging
from typing import Any

from self_healing_scraper.settings import Settings

logger = logging.getLogger(__name__)

KIMI_CODING_BASE_URL = "https://api.kimi.com/coding/v1"
MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"


def resolve_llm_base_url(api_key: str, configured: str) -> str | None:
    """Pick the right OpenAI-compatible base URL for the key type."""
    key = api_key.strip()
    base = configured.strip()
    if key.startswith("sk-kimi-"):
        # Kimi Code keys are rejected by api.moonshot.ai
        if not base or "moonshot.ai" in base:
            return KIMI_CODING_BASE_URL
        return base
    return base or None


def _default_headers(base_url: str | None) -> dict[str, str] | None:
    if base_url and "api.kimi.com" in base_url:
        # Coding endpoint gates access behind a recognized agent UA.
        return {"User-Agent": "KimiCLI/1.0"}
    return None


async def complete_json(
    *,
    system: str,
    user: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or Settings()
    if not cfg.llm_api_key:
        raise RuntimeError("LLM_API_KEY is required to create or repair parsers")

    from openai import AsyncOpenAI

    base_url = resolve_llm_base_url(cfg.llm_api_key, cfg.llm_base_url)
    headers = _default_headers(base_url)
    logger.info("LLM request model=%s base_url=%s", cfg.llm_model, base_url)

    client = AsyncOpenAI(
        api_key=cfg.llm_api_key,
        base_url=base_url,
        default_headers=headers,
    )
    create_kwargs: dict[str, Any] = {
        "model": cfg.llm_model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # Some models (e.g. kimi-k3) only accept temperature=1.
    if "kimi" in cfg.llm_model.lower():
        create_kwargs["temperature"] = 1
    else:
        create_kwargs["temperature"] = 0.2

    response = await client.chat.completions.create(**create_kwargs)
    content = response.choices[0].message.content or "{}"
    logger.debug("LLM raw response: %s", content[:500])
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("LLM did not return a JSON object")
    return data
