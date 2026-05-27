from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

import httpx

from research_agent.config import get_settings
from research_agent.logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class RepoHit:
    full_name: str
    url: str
    description: str
    stars: int
    language: str | None
    readme_excerpt: str = ""
    topics: list[str] = field(default_factory=list)


def _headers() -> dict[str, str]:
    settings = get_settings()
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "research-agent-mcp/0.1",
    }
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _check_rate(resp: httpx.Response) -> None:
    rem = resp.headers.get("X-RateLimit-Remaining")
    if rem is not None:
        try:
            n = int(rem)
            if n < 5:
                log.warning("GitHub rate-limit remaining=%s", rem)
        except ValueError:
            pass


async def search_repositories(query: str, *, max_results: int = 5) -> list[RepoHit]:
    settings = get_settings()
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": max_results}

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            resp = await client.get(url, headers=_headers(), params=params)
            _check_rate(resp)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        log.warning("GitHub search failed for %r: %s", query, exc)
        return []

    items: list[dict[str, Any]] = payload.get("items", []) or []
    hits: list[RepoHit] = []
    for it in items[:max_results]:
        hits.append(
            RepoHit(
                full_name=it.get("full_name", ""),
                url=it.get("html_url", ""),
                description=it.get("description") or "",
                stars=int(it.get("stargazers_count") or 0),
                language=it.get("language"),
                topics=list(it.get("topics") or []),
            )
        )
    return hits


async def fetch_readme(full_name: str, *, max_chars: int = 8000) -> str:
    settings = get_settings()
    url = f"https://api.github.com/repos/{full_name}/readme"

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            resp = await client.get(url, headers=_headers())
            _check_rate(resp)
            if resp.status_code == 404:
                return ""
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        log.warning("GitHub readme fetch failed for %s: %s", full_name, exc)
        return ""

    content_b64 = (payload.get("content") or "").replace("\n", "")
    if not content_b64:
        return ""
    try:
        raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception as exc:
        log.warning("Decode readme failed for %s: %s", full_name, exc)
        return ""
    return raw[:max_chars]


async def enrich_with_readmes(hits: list[RepoHit], *, max_repos: int = 3) -> list[RepoHit]:
    for hit in hits[:max_repos]:
        readme = await fetch_readme(hit.full_name)
        if readme:
            hit.readme_excerpt = readme
    return hits
