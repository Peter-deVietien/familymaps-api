import json
import os
import logging

import httpx

logger = logging.getLogger(__name__)

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_BASE_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-3"


def _parse_json_response(text: str) -> list | dict:
    """Extract JSON from a response that may contain markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return json.loads(cleaned)


async def llm_call(prompt: str, system_prompt: str = "You are a helpful assistant. Return JSON only.") -> list | dict:
    """Standard LLM completion (no web search). Used for Stage 1."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            XAI_BASE_URL,
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_json_response(content)


async def llm_web_search(prompt: str, system_prompt: str = "You are a web research assistant. Search the web and return JSON only.") -> list | dict:
    """LLM completion with xAI web search enabled. Used for Stages 2 and 3."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            XAI_BASE_URL,
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "search_parameters": {
                    "mode": "on",
                },
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_json_response(content)
