from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
import trafilatura

from research_agent.config import get_settings
from research_agent.logging_setup import get_logger

log = get_logger(__name__)


_USER_AGENT = "research-agent-mcp/0.1 (+https://github.com/)"

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


@dataclass
class DocsHit:
    url: str
    title: str
    content: str
    warnings: list[str] = field(default_factory=list)


async def fetch(url: str) -> DocsHit:
    settings = get_settings()
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as exc:
        log.warning("Docs fetch failed %s: %s", url, exc)
        return DocsHit(url=url, title="", content="", warnings=[f"fetch_error: {exc}"])

    title = ""
    m = _TITLE_RE.search(html)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()

    extracted = trafilatura.extract(
        html,
        include_links=True,
        include_tables=True,
        favor_recall=True,
        output_format="markdown",
    ) or ""

    warnings: list[str] = []
    if len(extracted) < 200:
        warnings.append("trafilatura returned thin content; using meta description fallback")
        meta = _META_DESC_RE.search(html)
        fallback = meta.group(1) if meta else ""
        extracted = (extracted + "\n\n" + fallback).strip()

    return DocsHit(url=url, title=title, content=extracted, warnings=warnings)
