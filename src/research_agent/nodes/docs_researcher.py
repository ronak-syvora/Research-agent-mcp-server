from __future__ import annotations

import uuid

from research_agent.logging_setup import get_logger
from research_agent.schemas import ResearchFinding
from research_agent.state import GraphState
from research_agent.tools import docs_fetcher

log = get_logger(__name__)


async def docs_researcher(state: GraphState) -> dict:
    url = state.get("docs_url", "").strip()
    if not url:
        return {"errors": ["docs_researcher: empty docs_url"]}

    log.info("docs_researcher: %s", url)
    try:
        hit = await docs_fetcher.fetch(url)
    except Exception as exc:
        log.exception("docs_researcher failed for %s", url)
        return {"errors": [f"docs_researcher({url}): {exc}"]}

    if not hit.content.strip():
        return {"errors": [f"docs_researcher: empty content from {url}"]}

    finding = ResearchFinding(
        id=f"docs_{uuid.uuid4().hex[:8]}",
        source_type="docs",
        url=hit.url,
        title=hit.title,
        snippet=hit.content[:300],
        content=hit.content[:12000],
        warnings=hit.warnings,
    )
    return {"findings": [finding]}
