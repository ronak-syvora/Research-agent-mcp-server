from __future__ import annotations

import anyio

from research_agent.logging_setup import get_logger
from research_agent.state import GraphState
from research_agent.tools import codebase_scanner

log = get_logger(__name__)


async def codebase_researcher(state: GraphState) -> dict:
    path = state.get("codebase_path")
    if not path:
        return {}

    log.info("codebase_researcher: scanning %s", path)
    try:
        scan = await anyio.to_thread.run_sync(lambda: codebase_scanner.scan(path))
    except Exception as exc:
        log.exception("codebase scan failed for %s", path)
        return {"errors": [f"codebase_researcher({path}): {exc}"]}

    log.info(
        "codebase scan: primary=%s frameworks=%s files=%d",
        scan.primary_language, scan.frameworks, scan.file_count,
    )
    return {"scan": scan}
