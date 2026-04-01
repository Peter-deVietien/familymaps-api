import json
import os
import logging

import httpx

logger = logging.getLogger(__name__)

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"
MODEL = "grok-4-1-fast-non-reasoning"


def _parse_json_response(text: str) -> list | dict:
    """Extract JSON from a response that may contain markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return json.loads(cleaned)


def _extract_text(response_json: dict) -> str:
    """Pull the assistant text out of a /v1/responses response."""
    for item in response_json.get("output", []):
        if item.get("type") == "message" and item.get("role") == "assistant":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    return block["text"]
    raise ValueError("No text output found in xAI response")


async def llm_call(prompt: str, system_prompt: str = "You are a helpful assistant. Return JSON only.") -> list | dict:
    """LLM completion without web search."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            XAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        text = _extract_text(resp.json())
        return _parse_json_response(text)


async def llm_web_search(prompt: str, system_prompt: str = "You are a web research assistant. Search the web and return JSON only.") -> list | dict:
    """LLM completion with web search tool enabled."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            XAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "input": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "tools": [
                    {"type": "web_search"},
                ],
            },
        )
        resp.raise_for_status()
        text = _extract_text(resp.json())
        return _parse_json_response(text)
