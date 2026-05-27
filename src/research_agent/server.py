from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from research_agent.logging_setup import configure_logging, get_logger
from research_agent.mcp_tools import dispatch_tool, tool_definitions

configure_logging()
log = get_logger(__name__)

app: Server = Server("research-agent")


@app.list_tools()
async def _list_tools() -> list[Tool]:
    return tool_definitions()


@app.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}
    log.info("call_tool name=%s args_keys=%s", name, sorted(args.keys()))
    try:
        return await dispatch_tool(name, args)
    except Exception as exc:
        log.exception("Tool %s raised", name)
        return [TextContent(type="text", text=f"Error in {name}: {type(exc).__name__}: {exc}")]


async def main() -> None:
    log.info("Starting research-agent MCP server (stdio)")
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
