from __future__ import annotations

import uuid

from research_agent.logging_setup import get_logger
from research_agent.schemas import ResearchFinding
from research_agent.state import GraphState
from research_agent.tools import web_search

log = get_logger(__name__)


async def web_researcher(state: GraphState) -> dict:
    query = state.get("sub_question", "").strip()
    if not query:
        return {"errors": ["web_researcher: empty sub_question"]}

    log.info("web_researcher: %r", query[:80])
    try:
        hits = await web_search.search(query, max_results=5)
    except Exception as exc:
        log.exception("web_researcher failed for %r", query)
        return {"errors": [f"web_researcher({query!r}): {exc}"]}

    findings: list[ResearchFinding] = []
    for hit in hits:
        body = (hit.raw_content or hit.snippet or "").strip()
        if not body and not hit.title:
            continue
        findings.append(
            ResearchFinding(
                id=f"web_{uuid.uuid4().hex[:8]}",
                source_type="web",
                url=hit.url,
                title=hit.title,
                snippet=hit.snippet,
                content=body[:8000],
                metadata={"query": query, "score": hit.score},
            )
        )
    log.info("web_researcher: %d findings for %r", len(findings), query[:60])
    return {"findings": findings}
