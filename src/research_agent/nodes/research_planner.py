from __future__ import annotations

import json

from research_agent.llm import mistral_client
from research_agent.logging_setup import get_logger
from research_agent.prompts import PLANNER_SYSTEM
from research_agent.schemas import ResearchPlan
from research_agent.state import GraphState

log = get_logger(__name__)


_DEPTH_LIMITS: dict[str, dict[str, int]] = {
    "quick": {"sub": 3, "web": 3, "docs": 2, "github": 2},
    "standard": {"sub": 5, "web": 5, "docs": 3, "github": 3},
    "deep": {"sub": 7, "web": 7, "docs": 4, "github": 4},
}


async def research_planner(state: GraphState) -> dict:
    intent = state["intent"]
    depth = state.get("depth") or "standard"
    limits = _DEPTH_LIMITS.get(depth, _DEPTH_LIMITS["standard"])

    user = (
        f"<intent>\n{intent.model_dump_json(indent=2)}\n</intent>\n\n"
        f"<depth>{depth}</depth>\n\n"
        f"<original_query>{state['query']}</original_query>\n\n"
        f"Generate a research plan."
    )

    try:
        plan = await mistral_client.complete_json(
            system=PLANNER_SYSTEM,
            user=user,
            schema=ResearchPlan,
            temperature=0.2,
        )
    except Exception as exc:
        log.exception("research_planner failed; using minimal fallback plan")
        plan = ResearchPlan(
            sub_questions=[f"How to integrate {intent.target} with {intent.source_stack}?"],
            web_queries=[f"{intent.target} integration {intent.source_stack} tutorial"],
            docs_urls=[],
            github_queries=[f"{intent.target} {intent.source_stack} example"],
            notes="(fallback plan due to planner error)",
        )
        return {"plan": plan, "errors": [f"research_planner: {exc}"]}

    plan.sub_questions = plan.sub_questions[: limits["sub"]]
    plan.web_queries = plan.web_queries[: limits["web"]]
    plan.docs_urls = plan.docs_urls[: limits["docs"]]
    plan.github_queries = plan.github_queries[: limits["github"]]

    log.info(
        "research_planner ok: %d sub, %d web, %d docs, %d github",
        len(plan.sub_questions),
        len(plan.web_queries),
        len(plan.docs_urls),
        len(plan.github_queries),
    )
    log.debug("plan: %s", json.dumps(plan.model_dump(), indent=2))
    return {"plan": plan}
