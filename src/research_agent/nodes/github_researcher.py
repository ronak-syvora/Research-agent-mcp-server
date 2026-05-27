from __future__ import annotations

import uuid

from research_agent.logging_setup import get_logger
from research_agent.schemas import ResearchFinding
from research_agent.state import GraphState
from research_agent.tools import github

log = get_logger(__name__)


async def github_researcher(state: GraphState) -> dict:
    plan = state["plan"]
    intent = state["intent"]

    queries = list(plan.github_queries)
    if not queries:
        queries = [f"{intent.target} {intent.source_stack} example"]

    findings: list[ResearchFinding] = []
    seen: set[str] = set()
    errors: list[str] = []

    for q in queries[:3]:
        log.info("github_researcher: %r", q)
        try:
            hits = await github.search_repositories(q, max_results=5)
            await github.enrich_with_readmes(hits, max_repos=2)
        except Exception as exc:
            log.exception("github search failed for %r", q)
            errors.append(f"github_researcher({q!r}): {exc}")
            continue

        for hit in hits:
            if hit.full_name in seen:
                continue
            seen.add(hit.full_name)
            content_parts = [
                f"Repository: {hit.full_name} ({hit.stars} stars, language: {hit.language or 'unknown'})",
                f"URL: {hit.url}",
                f"Description: {hit.description}" if hit.description else "",
                f"Topics: {', '.join(hit.topics)}" if hit.topics else "",
                "",
                hit.readme_excerpt or "",
            ]
            content = "\n".join(p for p in content_parts if p is not None)
            findings.append(
                ResearchFinding(
                    id=f"gh_{uuid.uuid4().hex[:8]}",
                    source_type="github",
                    url=hit.url,
                    title=hit.full_name,
                    snippet=hit.description or "",
                    content=content[:10000],
                    metadata={"stars": hit.stars, "language": hit.language},
                )
            )

    log.info("github_researcher: %d total repos found", len(findings))
    out: dict = {"findings": findings}
    if errors:
        out["errors"] = errors
    return out
