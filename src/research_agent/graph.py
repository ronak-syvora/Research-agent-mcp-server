from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from research_agent.logging_setup import get_logger
from research_agent.nodes.codebase_researcher import codebase_researcher
from research_agent.nodes.docs_researcher import docs_researcher
from research_agent.nodes.github_researcher import github_researcher
from research_agent.nodes.intent_parser import intent_parser
from research_agent.nodes.report_writer import report_writer
from research_agent.nodes.research_dispatcher import research_dispatcher
from research_agent.nodes.research_planner import research_planner
from research_agent.nodes.retrieval import retrieval
from research_agent.nodes.synthesizer import synthesizer
from research_agent.nodes.web_researcher import web_researcher
from research_agent.state import GraphState

log = get_logger(__name__)


_GRAPH = None


def build_graph():
    global _GRAPH
    if _GRAPH is not None:
        return _GRAPH

    builder = StateGraph(GraphState)
    builder.add_node("intent_parser", intent_parser)
    builder.add_node("research_planner", research_planner)
    builder.add_node("web_researcher", web_researcher)
    builder.add_node("docs_researcher", docs_researcher)
    builder.add_node("github_researcher", github_researcher)
    builder.add_node("codebase_researcher", codebase_researcher)
    builder.add_node("retrieval", retrieval)
    builder.add_node("synthesizer", synthesizer)
    builder.add_node("report_writer", report_writer)

    builder.add_edge(START, "intent_parser")
    builder.add_edge("intent_parser", "research_planner")
    builder.add_conditional_edges(
        "research_planner",
        research_dispatcher,
        ["web_researcher", "docs_researcher", "github_researcher", "codebase_researcher"],
    )
    builder.add_edge("web_researcher", "retrieval")
    builder.add_edge("docs_researcher", "retrieval")
    builder.add_edge("github_researcher", "retrieval")
    builder.add_edge("codebase_researcher", "retrieval")
    builder.add_edge("retrieval", "synthesizer")
    builder.add_edge("synthesizer", "report_writer")
    builder.add_edge("report_writer", END)

    _GRAPH = builder.compile()
    log.info("LangGraph compiled")
    return _GRAPH


async def run_graph(query: str, *, codebase_path: str | None = None,
                    depth: str = "standard") -> GraphState:
    graph = build_graph()
    initial: GraphState = {
        "query": query,
        "codebase_path": codebase_path,
        "depth": depth,
        "findings": [],
        "errors": [],
        "audience": None,
    }
    final: GraphState = await graph.ainvoke(initial)
    return final
