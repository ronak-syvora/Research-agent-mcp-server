from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.types import TextContent, Tool

from research_agent.config import get_settings
from research_agent.logging_setup import get_logger

log = get_logger(__name__)


TOOL_RESEARCH_INTEGRATION = "research_integration"
TOOL_SCAN_CODEBASE = "scan_codebase"
TOOL_LIST_REPORTS = "list_reports"


def tool_definitions() -> list[Tool]:
    return [
        Tool(
            name=TOOL_RESEARCH_INTEGRATION,
            description=(
                "Generate a comprehensive integration research report tailored to the requester's "
                "role and skill level. State your role in the query (e.g. \"As an HR manager…\", "
                "\"I'm a DevOps engineer…\", \"speaking as a QA engineer…\") and the report is "
                "tailored to it — supported roles are developer, HR, sales, DevOps, QA, or general. "
                "If no role is stated, the agent infers one from the query. "
                "Skill level (beginner/intermediate/advanced) and tone are always inferred from the query. "
                "Examples: an HR person asking about Keka integration gets a plain-English guide "
                "with business value, process impact, and stakeholder contacts; a junior dev asking "
                "about EigenLayer gets prerequisites, step-by-step plan, code examples, and a "
                "troubleshooting guide; a DevOps engineer gets infrastructure requirements, "
                "pipeline changes, and a rollback plan. "
                "Researches official docs, web sources, and GitHub examples. Returns the full "
                "markdown and writes a copy to <reports_dir>/<slug>-<timestamp>.md "
                "(default ~/.research-agent/reports). Expect 60-180s runtime."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural-language integration request. Be specific about target tech, "
                            "source stack, and goal. Optionally state your role (developer, HR, "
                            "sales, devops, QA) for a role-tailored report."
                        ),
                    },
                    "codebase_path": {
                        "type": ["string", "null"],
                        "description": (
                            "Absolute path to a local repo to analyze for project-specific "
                            "recommendations. Omit for generic research."
                        ),
                        "default": None,
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["quick", "standard", "deep"],
                        "description": (
                            "quick=fewer sources, ~30s. standard=balanced, ~90s. "
                            "deep=more sources + larger retrieval, ~3min."
                        ),
                        "default": "standard",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name=TOOL_SCAN_CODEBASE,
            description=(
                "Analyze a local codebase: detect language(s), framework, package manifests, "
                "build tools, and high-level module structure. Returns structured JSON. Fast (<5s). "
                "Useful for previewing what research_integration will see before running it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to repo root.",
                    },
                    "max_files": {
                        "type": "integer",
                        "default": 5000,
                        "description": "Hard cap on files walked.",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name=TOOL_LIST_REPORTS,
            description=(
                "List previously generated research reports in the reports dir with title, slug, "
                "and timestamp. Useful for referencing prior runs in conversation."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == TOOL_LIST_REPORTS:
        return await _list_reports()
    if name == TOOL_SCAN_CODEBASE:
        return await _scan_codebase(arguments)
    if name == TOOL_RESEARCH_INTEGRATION:
        return await _research_integration(arguments)
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


async def _list_reports() -> list[TextContent]:
    settings = get_settings()
    reports_dir = Path(settings.reports_dir)
    reports: list[dict[str, Any]] = []

    if reports_dir.exists():
        for md in sorted(reports_dir.glob("*.md")):
            try:
                stat = md.stat()
                head = md.read_text(encoding="utf-8", errors="replace")[:1024]
                m = _TITLE_RE.search(head)
                title = m.group(1) if m else md.stem
                reports.append(
                    {
                        "slug": md.stem,
                        "path": str(md.resolve()),
                        "title": title,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size_bytes": stat.st_size,
                    }
                )
            except OSError as e:
                log.warning("Could not read report %s: %s", md, e)

    reports.sort(key=lambda r: r["created_at"], reverse=True)
    payload = {"count": len(reports), "reports_dir": str(reports_dir.resolve()), "reports": reports}
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def _scan_codebase(arguments: dict[str, Any]) -> list[TextContent]:
    import anyio

    from research_agent.tools import codebase_scanner

    path = arguments.get("path")
    if not isinstance(path, str) or not path:
        return [TextContent(type="text", text='Error: "path" is required and must be a string')]

    max_files = arguments.get("max_files", 5000)
    if not isinstance(max_files, int) or max_files <= 0:
        max_files = 5000

    result = await anyio.to_thread.run_sync(
        lambda: codebase_scanner.scan(path, max_files=max_files)
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def _research_integration(arguments: dict[str, Any]) -> list[TextContent]:
    from research_agent.graph import run_graph

    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        return [TextContent(type="text", text='Error: "query" is required and must be a non-empty string')]

    codebase_path = arguments.get("codebase_path")
    if codebase_path is not None and not isinstance(codebase_path, str):
        codebase_path = None

    depth = arguments.get("depth", "standard")
    if depth not in ("quick", "standard", "deep"):
        depth = "standard"

    log.info("research_integration starting: depth=%s codebase=%s", depth, bool(codebase_path))
    final = await run_graph(query, codebase_path=codebase_path, depth=depth)

    report_md = final.get("report_markdown", "_(no report generated)_")
    report_path = final.get("report_path", "")
    header = f"Report saved to: {report_path}\n\n---\n\n" if report_path else ""
    return [TextContent(type="text", text=header + report_md)]
