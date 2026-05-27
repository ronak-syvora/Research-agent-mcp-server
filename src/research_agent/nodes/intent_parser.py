from __future__ import annotations

from research_agent.llm import mistral_client
from research_agent.logging_setup import get_logger
from research_agent.prompts import INTENT_SYSTEM
from research_agent.schemas import IntentSpec
from research_agent.state import GraphState

log = get_logger(__name__)


async def intent_parser(state: GraphState) -> dict:
    query = state["query"]
    log.info("intent_parser: query=%r", query[:120])
    try:
        intent = await mistral_client.complete_json(
            system=INTENT_SYSTEM,
            user=query,
            schema=IntentSpec,
            temperature=0.1,
        )
        log.info(
            "intent_parser ok: target=%s source_stack=%s frameworks=%s",
            intent.target, intent.source_stack, intent.frameworks,
        )
        return {"intent": intent}
    except Exception as exc:
        log.exception("intent_parser failed; using fallback intent")
        return {
            "intent": IntentSpec(target=query, source_stack="", frameworks=[]),
            "errors": [f"intent_parser: {exc}"],
        }
