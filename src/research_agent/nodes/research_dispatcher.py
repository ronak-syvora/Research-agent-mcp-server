from __future__ import annotations

from langgraph.types import Send

from research_agent.logging_setup import get_logger
from research_agent.state import GraphState

log = get_logger(__name__)


def research_dispatcher(state: GraphState) -> list[Send]:
    plan = state["plan"]
    sends: list[Send] = []

    for q in plan.web_queries:
        sends.append(Send("web_researcher", {**state, "sub_question": q}))
    for url in plan.docs_urls:
        sends.append(Send("docs_researcher", {**state, "docs_url": url}))
    sends.append(Send("github_researcher", state))
    if state.get("codebase_path"):
        sends.append(Send("codebase_researcher", state))

    log.info("dispatcher: %d branches (web=%d, docs=%d, github=1, codebase=%s)",
             len(sends), len(plan.web_queries), len(plan.docs_urls),
             "yes" if state.get("codebase_path") else "no")
    return sends
