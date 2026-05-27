# Integration Research Agent — MCP Server

AI-powered "integration architect" that takes a natural-language integration request and produces a polished markdown research document covering compatibility, dependencies, architecture changes, integration plan, code examples, security review, testing, deployment, and references.

Exposed as a **stdio MCP server**, designed to be invoked from Claude Code / Claude Desktop.

## Stack

- **Python 3.11+** with [uv](https://docs.astral.sh/uv/)
- **MCP** via the official `mcp` Python SDK (stdio transport)
- **LangGraph** for the multi-node async workflow
- **Mistral AI** for LLM (`mistral-large-latest`) and embeddings (`mistral-embed`, 1024-dim)
- **Tavily** for web search
- **httpx + trafilatura** for documentation fetching/extraction
- **GitHub REST API** (authenticated via PAT) for repository discovery
- **Chroma** (persistent local) as the vector store for in-request RAG

## MCP tools

| Tool | Purpose |
|---|---|
| `research_integration(query, codebase_path?, depth?)` | Run the full graph and return a markdown report. Also writes `./reports/<slug>-<timestamp>.md`. |
| `scan_codebase(path, max_files?)` | Standalone codebase analysis (frameworks, manifests, structure). |
| `list_reports()` | List prior generated reports. |

`depth` is one of `quick` / `standard` / `deep`.

## Setup

1. Install deps:
   ```bash
   uv sync --extra dev
   ```
2. Copy `.env.example` to `.env` and fill in:
   ```
   MISTRAL_API_KEY=...
   TAVILY_API_KEY=...
   GITHUB_TOKEN=...
   ```
3. Run tests:
   ```bash
   uv run pytest tests/unit -q
   ```

## Register with Claude Code

Add to your `.mcp.json` (project-level) or `~/.claude.json` (user-level):

```json
{
  "mcpServers": {
    "research-agent": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/ronakkadam/Work/research-agent-mcp-server",
        "run",
        "research-agent-mcp"
      ],
      "env": {
        "MISTRAL_API_KEY": "...",
        "TAVILY_API_KEY": "...",
        "GITHUB_TOKEN": "..."
      }
    }
  }
}
```

Then invoke from Claude Code: ask it to run `research_integration` with your query.

## Example query

```
Add Chainlink price feeds to my Foundry Solidity ERC4626 vault.
```

Expected runtime: 60–180 seconds. Total Mistral cost per "standard" run: ~$0.10–0.30.

## Pipeline

```
intent_parser → research_planner → research_dispatcher (Send fan-out)
   ├── web_researcher (Tavily, per sub-question, in parallel)
   ├── docs_researcher (trafilatura, per docs URL)
   ├── github_researcher (GitHub search + READMEs)
   └── codebase_researcher (local scan, if codebase_path provided)
        ↓ (Annotated[list, add] reducers merge findings)
retrieval (chunk → mistral-embed → Chroma → top-k per query)
   ↓
synthesizer (3 grouped LLM calls in parallel)
   ↓
report_writer (deterministic markdown + file write)
```

## Project layout

```
src/research_agent/
  server.py          # MCP stdio entrypoint
  mcp_tools.py       # 3 tool definitions + dispatch
  graph.py           # LangGraph wiring
  state.py           # GraphState TypedDict with Annotated reducers
  schemas.py         # Pydantic models
  config.py          # pydantic-settings
  logging_setup.py   # stderr-only logging (stdio safety)
  prompts.py         # all prompt templates
  llm/mistral_client.py
  nodes/             # intent_parser, planner, dispatcher, *researchers, retrieval, synthesizer, report_writer
  tools/             # web_search, docs_fetcher, github, codebase_scanner, embeddings, retrieval
  utils/             # chunking, markdown, text
```

## Notes

- The graph degrades gracefully: if any single research tool fails (rate limits, missing API key, network error), it surfaces as an entry under "Research Limitations" in the report rather than aborting the run.
- All logging goes to stderr; stdout is reserved exclusively for the MCP JSON-RPC channel.
- Embedding usage is capped via `RESEARCH_AGENT_MAX_EMBED_CALLS` (default 100 batches × 32 chunks).
- Chroma collections are per-request (named `req-<uuid>`) and deleted at the end of each run.
