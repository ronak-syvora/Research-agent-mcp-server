# Research Agent MCP Server

**An AI-powered integration architect that transforms developer requests into comprehensive implementation research documents.**

## Overview

The Research Agent MCP Server is a specialized tool that addresses a common developer pain point: the time-consuming process of researching and planning technical integrations. When a developer needs to integrate external infrastructure (e.g., Chainlink into a Solidity protocol, Stripe into a backend), they currently must manually:

1. Search official documentation
2. Read multiple blog posts and tutorials
3. Inspect GitHub repositories
4. Understand SDKs and API compatibility
5. Evaluate architecture fit
6. Document everything manually

**This project automates that entire workflow**, using AI to synthesize information from multiple sources and generate a polished research document.

## Problem Being Solved

- **Time Cost**: Simple integrations require 2–10 hours of research; complex ones take days
- **Information Fragmentation**: Knowledge scattered across docs, GitHub, blogs, Stack Overflow, Discord
- **Architecture Ambiguity**: Generic tutorials don't answer "how does this fit MY codebase?"
- **Risk of Incorrect Implementation**: Poor research leads to insecure or incompatible solutions

## How It Works

### Input
Developer provides a natural-language integration request:
```
I have a Solidity staking protocol built with Foundry.
I want to integrate EigenLayer AVS.
Create a complete integration implementation plan.
```

### Processing Pipeline
```
Intent Parser
  → Research Planner
    → Parallel Research Tools (web, docs, GitHub, codebase analysis)
      → RAG Retrieval (vector search over findings)
        → Synthesizer (3 LLM synthesis passes in parallel)
          → Report Writer (deterministic markdown generation)
            → Output Report
```

### Output
A comprehensive markdown research document containing:
- **Project Overview** — What the integration target is
- **Compatibility Analysis** — Can it integrate into your architecture?
- **Required Dependencies** — Packages, versions, installation commands
- **Architecture Changes** — What needs to be modified in your codebase
- **Integration Plan** — Step-by-step implementation roadmap
- **Code Examples** — Starter code and boilerplate patterns
- **Security Review** — Potential attack vectors and risks
- **Testing Plan** — Recommended test strategy
- **Deployment Checklist** — Production readiness tasks
- **References** — Links to official docs, GitHub repos, tutorials

## Tech Stack

### Core Technologies
| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Protocol** | Model Context Protocol (MCP) | Stdio-based tool exposure to Claude/agents |
| **Orchestration** | LangGraph | Multi-node async workflow orchestration |
| **Language** | Python 3.11+ | Clean async support, strong ML ecosystem |
| **LLM** | Mistral Large | Fast, capable, good for instruction-following |
| **Embeddings** | Mistral Embed (1024-dim) | Dense embeddings for RAG |
| **Web Search** | Tavily | Developer-friendly web search API |
| **Docs Extraction** | Trafilatura | HTML-to-markdown document extraction |
| **Vector Store** | Chroma (persistent local) | In-request RAG, automatic cleanup |
| **GitHub** | GitHub REST API | Repository discovery and analysis |
| **HTTP Client** | httpx | Async HTTP requests |
| **Package Manager** | uv | Fast, deterministic Python package management |

### Development Tools
- **Testing**: pytest, pytest-asyncio, respx (HTTP mocking)
- **Linting**: Ruff
- **Type Checking**: mypy
- **Configuration**: Pydantic, pydantic-settings

## Architecture

### Project Structure
```
src/research_agent/
├── server.py                    # MCP stdio entrypoint
├── mcp_tools.py                 # 3 tool definitions: research_integration, scan_codebase, list_reports
├── graph.py                     # LangGraph wiring (state machine + node connections)
├── state.py                     # GraphState TypedDict with Annotated reducers
├── schemas.py                   # Pydantic models (Intent, ResearchFinding, etc.)
├── config.py                    # Environment-based configuration
├── logging_setup.py             # stderr-only logging (stdio safety)
├── prompts.py                   # All prompt templates (intent, planner, synthesizer, report)
├── llm/
│   └── mistral_client.py        # Mistral API wrapper
├── nodes/                       # Graph nodes (individual async functions)
│   ├── intent_parser.py
│   ├── research_planner.py
│   ├── research_dispatcher.py
│   ├── web_researcher.py
│   ├── docs_researcher.py
│   ├── github_researcher.py
│   ├── codebase_researcher.py
│   ├── retrieval.py
│   ├── synthesizer.py
│   └── report_writer.py
├── tools/                       # External tool integrations
│   ├── web_search.py            # Tavily web search
│   ├── docs_fetcher.py          # trafilatura HTML extraction
│   ├── github.py                # GitHub REST API wrapper
│   ├── codebase_scanner.py      # Local filesystem analysis
│   ├── embeddings.py            # Mistral embedding wrapper
│   └── retrieval.py             # Chroma vector store operations
└── utils/                       # Utility functions
    ├── chunking.py              # Text chunking for embeddings
    ├── markdown.py              # Markdown formatting
    └── text.py                  # Text cleaning/normalization
```

### Data Flow

1. **Intent Parser** — Extracts structured intent from natural language
2. **Research Planner** — Decomposes request into research sub-tasks
3. **Research Dispatcher** — Sends tasks to parallel researcher nodes
4. **Researcher Nodes** (parallel):
   - **Web Researcher**: Tavily search per sub-question
   - **Docs Researcher**: trafilatura extraction for doc URLs
   - **GitHub Researcher**: GitHub search + README extraction
   - **Codebase Researcher**: Local filesystem scan (if codebase provided)
5. **Findings Merge** — Annotated reducers aggregate results
6. **Retrieval** — Chunk findings, embed with Mistral, store in Chroma, retrieve top-k per query
7. **Synthesizer** — 3 parallel LLM calls synthesize findings into sections
8. **Report Writer** — Deterministic markdown formatting + file write
9. **Output** — Report written to `./reports/<slug>-<timestamp>.md`

## Core MCP Tools

### `research_integration(query, codebase_path?, depth?)`
Run the full research workflow and return a markdown report.

**Parameters:**
- `query` (string, required): Integration request, e.g., "Add Chainlink to my ERC4626 vault"
- `codebase_path` (string, optional): Path to analyze user's codebase
- `depth` (enum: `quick|standard|deep`, optional): Research depth
  - `quick`: ~30 seconds, fewer sources
  - `standard`: ~90 seconds, balanced coverage
  - `deep`: ~3 minutes, comprehensive research

**Returns:** Markdown string + writes to `./reports/<slug>-<timestamp>.md`

**Example Cost**: ~$0.10–0.30 USD per standard run (Mistral Large usage)

### `scan_codebase(path, max_files?)`
Standalone codebase analysis without running full research.

**Returns:** 
```json
{
  "languages": ["Python", "TypeScript"],
  "frameworks": ["FastAPI", "React"],
  "manifests": ["pyproject.toml", "package.json"],
  "structure": { "src": [...], "tests": [...] },
  "summary": "FastAPI backend with React frontend"
}
```

### `list_reports()`
List all previously generated reports from `./reports/`.

**Returns:**
```json
[
  {
    "filename": "integrating-openai-sdk-into-python-20260518-111721.md",
    "timestamp": "2026-05-18T11:17:21Z",
    "query": "Integrate OpenAI SDK into Python project"
  }
]
```

## Setup & Usage

### Installation

```bash
# Clone repository
git clone <repo-url>
cd research-agent-mcp-server

# Install dependencies with uv
uv sync --extra dev
```

### Configuration

Copy `.env.example` to `.env` and fill in API keys:
```bash
MISTRAL_API_KEY=your-key-here
TAVILY_API_KEY=your-key-here
GITHUB_TOKEN=your-pat-here
```

Optional settings:
```bash
RESEARCH_AGENT_MAX_EMBED_CALLS=100        # Embedding cap (default)
RESEARCH_AGENT_DEPTH_MODE=standard        # quick|standard|deep
```

### Running Tests

```bash
uv run pytest tests/unit -q
```

### Register with Claude Code

Add to `.mcp.json` (project-level) or `~/.claude.json` (user-level):

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
        "MISTRAL_API_KEY": "your-key",
        "TAVILY_API_KEY": "your-key",
        "GITHUB_TOKEN": "your-token"
      }
    }
  }
}
```

Then invoke from Claude Code:
```
Use the research_integration tool to generate a report for: "Integrate Stripe billing into my FastAPI backend"
```

## Key Features

### Graceful Degradation
If any single research tool fails (rate limits, missing API key, network error), it surfaces as a limitation in the report rather than aborting the run. Users still get value.

### Safe Stdio Channel
All logging goes to stderr; stdout is reserved exclusively for MCP JSON-RPC communication, ensuring protocol safety.

### Per-Request Isolation
Chroma vector store collections are scoped to each request (named `req-<uuid>`) and automatically cleaned up at the end.

### Embedding Cost Control
Embedding usage is capped via `RESEARCH_AGENT_MAX_EMBED_CALLS` (default 100 batches × 32 chunks = 3200 max embeddings per run).

### Smart Caching
- Research findings are cached in memory during a request
- RAG results are cached to avoid redundant retrievals
- Chroma collections are reused within a single request

## Example Workflows

### Scenario 1: Simple Integration
**Request:** "Add Stripe billing to my Flask API"
- Runtime: ~30 seconds (quick mode)
- Cost: ~$0.05
- Output: Integration plan with code examples

### Scenario 2: Complex Infrastructure
**Request:** "Integrate Kubernetes into my microservices architecture. Our stack is Node.js with PostgreSQL."
- Runtime: ~120 seconds (standard mode)
- Cost: ~$0.20
- Output: Comprehensive deployment strategy with codebase-specific recommendations

### Scenario 3: Blockchain Integration
**Request:** "I'm building a Solidity staking protocol with Foundry. Add EigenLayer AVS support. Here's my codebase."
- Runtime: ~180 seconds (deep mode with codebase analysis)
- Cost: ~$0.30
- Output: Security-reviewed implementation plan with contract architecture changes

## Performance Characteristics

| Metric | Value |
|--------|-------|
| **Min Runtime** | ~30s (quick mode) |
| **Standard Runtime** | ~90s (standard mode) |
| **Max Runtime** | ~180s (deep mode) |
| **Cost per Run** | $0.10–0.30 USD |
| **Max Embeddings** | 3200 per run |
| **Max Chroma Collections** | 1 per request (cleaned up) |
| **Parallel Researchers** | 4 concurrent (web, docs, GitHub, codebase) |

## Limitations & Future Work

### Current Limitations
- Single integration workflow (one request → one report)
- Markdown output only (no Notion, PDF, or diagrams)
- No interactive follow-up questioning
- No codebase modification or PR generation
- No authentication/multi-user support

### Planned Enhancements
- Notion page publishing
- Architecture diagrams (Mermaid/PlantUML)
- Implementation diffs and code suggestions
- Automatic PR generation
- Confidence scoring on recommendations
- Multi-provider comparisons (e.g., Stripe vs. Paddle)
- IDE plugin integration

## Security Considerations

- All API keys are environment variables (never hardcoded or logged)
- Logging goes to stderr only, avoiding stdout pollution
- Chroma collections are ephemeral per request (no persistent data leakage)
- No authentication layer (intended for Claude Code / Claude Desktop use only)
- GitHub API uses personal access tokens (no app auth flow)

## Contributing

### Code Quality Standards
- Python 3.11+ with type hints
- Ruff for linting (100-char line limit)
- mypy for type checking
- pytest + pytest-asyncio for testing
- Async/await patterns throughout

### Development Commands
```bash
# Run tests
uv run pytest tests/unit -q

# Run linter
uv run ruff check src/

# Format code
uv run ruff format src/

# Type check
uv run mypy src/
```

## License

Not yet specified in project files. See repository for licensing details.

## Contact & Questions

For questions or issues, refer to:
- **Project Repository**: See `.git` or README for repo URL
- **Owner**: piyush.gandhi@syvora.com
- **Status**: Active development (MVP complete, feature enhancements ongoing)
