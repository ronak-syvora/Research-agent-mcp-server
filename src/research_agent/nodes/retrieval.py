from __future__ import annotations

import anyio

from research_agent.logging_setup import get_logger
from research_agent.schemas import Chunk, RetrievedChunk
from research_agent.state import GraphState
from research_agent.tools import embeddings as embeddings_tool
from research_agent.tools.retrieval import ChromaIndex
from research_agent.utils.chunking import chunk_markdown

log = get_logger(__name__)


_K_BY_DEPTH = {"quick": 3, "standard": 5, "deep": 8}
_MAX_QUERIES_BY_DEPTH = {"quick": 6, "standard": 10, "deep": 16}
_TOTAL_KEEP_BY_DEPTH = {"quick": 15, "standard": 25, "deep": 40}


def _build_section_queries(intent_target: str, source_stack: str) -> list[str]:
    base = intent_target.strip() or "this technology"
    stack = source_stack.strip()
    return [
        f"What is {base} and how does it work?",
        f"How to install and set up {base}",
        f"{base} integration steps and architecture",
        f"{base} security considerations and risks",
        f"{base} testing patterns and best practices",
        f"{base} dependencies and version requirements" + (f" with {stack}" if stack else ""),
    ]


async def retrieval(state: GraphState) -> dict:
    findings = list(state.get("findings", []))
    if not findings:
        log.info("retrieval: no findings, skipping")
        return {"retrieved": []}

    chunks: list[Chunk] = []
    for f in findings:
        body = (f.content or f.snippet or "").strip()
        if not body:
            continue
        chunks.extend(chunk_markdown(body, source_id=f.id))

    if not chunks:
        log.info("retrieval: 0 chunks after chunking, skipping")
        return {"retrieved": []}

    depth = state.get("depth") or "standard"
    k = _K_BY_DEPTH.get(depth, 5)
    max_queries = _MAX_QUERIES_BY_DEPTH.get(depth, 10)
    total_keep = _TOTAL_KEEP_BY_DEPTH.get(depth, 25)

    plan = state.get("plan")
    intent = state.get("intent")
    queries: list[str] = []
    if plan is not None:
        queries.extend(q for q in plan.sub_questions if q)
    if intent is not None:
        queries.extend(_build_section_queries(intent.target, intent.source_stack))

    seen_q: set[str] = set()
    deduped: list[str] = []
    for q in queries:
        qn = q.strip()
        if qn and qn not in seen_q:
            seen_q.add(qn)
            deduped.append(qn)
    queries = deduped[:max_queries]

    log.info("retrieval: %d chunks, %d queries, k=%d, target_keep=%d",
             len(chunks), len(queries), k, total_keep)

    try:
        chunk_embeddings = await embeddings_tool.embed_texts([c.text for c in chunks])
        query_embeddings = await embeddings_tool.embed_texts(queries) if queries else []
    except Exception as exc:
        log.warning("retrieval: embedding failed, falling back to raw findings: %s", exc)
        return {"retrieved": [], "errors": [f"retrieval(embed): {exc}"]}

    index = ChromaIndex()

    def _add() -> None:
        index.add(chunks, chunk_embeddings)

    def _query():
        return index.query(list(zip(queries, query_embeddings, strict=False)), k=k)

    def _close() -> None:
        index.close()

    try:
        await anyio.to_thread.run_sync(_add)
        hits = await anyio.to_thread.run_sync(_query)
    except Exception as exc:
        log.exception("retrieval: chroma operation failed")
        await anyio.to_thread.run_sync(_close)
        return {"retrieved": [], "errors": [f"retrieval(chroma): {exc}"]}
    finally:
        try:
            await anyio.to_thread.run_sync(_close)
        except Exception:
            pass

    hits.sort(key=lambda h: h.score, reverse=True)
    selected = hits[:total_keep]

    retrieved = [
        RetrievedChunk(chunk=h.chunk, score=h.score, matched_query=h.matched_query)
        for h in selected
    ]
    log.info("retrieval: %d retrieved chunks (top score=%.3f)",
             len(retrieved), retrieved[0].score if retrieved else 0.0)
    return {"retrieved": retrieved}
