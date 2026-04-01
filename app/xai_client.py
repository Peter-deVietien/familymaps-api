import json
import os
import logging

import httpx

logger = logging.getLogger(__name__)

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"
MODEL = "grok-4-1-fast-non-reasoning"


def _parse_json_response(text: str) -> list | dict:
    """Extract the first JSON object or array from LLM output."""
    cleaned = text.strip()

    # Strip markdown fences
    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts[1:]:
            block = part.split("\n", 1)[-1] if "\n" in part else part
            block = block.strip()
            if block.startswith(("{", "[")):
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    pass

    # Try parsing the whole string
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first { or [ and use json.JSONDecoder to grab just the object/array
    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch in ("{", "["):
            try:
                obj, _ = decoder.raw_decode(cleaned, i)
                return obj
            except json.JSONDecodeError:
                continue

    raise ValueError(f"No JSON found in response: {cleaned[:200]}")


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
