from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from research_agent.config import get_settings
from research_agent.logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class WebHit:
    url: str
    title: str
    snippet: str
    score: float = 0.0
    raw_content: str = ""


_client = None


def _get_client():
    global _client
    if _client is None:
        from tavily import TavilyClient

        settings = get_settings()
        if not settings.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is not set")
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


async def search(query: str, *, max_results: int = 5, include_raw: bool = False) -> list[WebHit]:
    client = _get_client()

    def _run() -> dict[str, Any]:
        return client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_raw_content=include_raw,
        )

    try:
        result = await asyncio.to_thread(_run)
    except Exception as exc:
        log.warning("Tavily search failed for %r: %s", query, exc)
        return []

    hits: list[WebHit] = []
    for item in result.get("results", []) or []:
        hits.append(
            WebHit(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("content", "") or "",
                score=float(item.get("score", 0.0)),
                raw_content=item.get("raw_content", "") or "",
            )
        )
    return hits
