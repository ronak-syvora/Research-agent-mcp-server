# Quick Start

## Setup
```bash
uv sync --extra dev
cp .env.example .env
# Fill .env: MISTRAL_API_KEY, TAVILY_API_KEY, GITHUB_TOKEN
```

## Tests
```bash
uv run pytest tests/unit -q
```

## Register with Claude Code
Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "research-agent": {
      "command": "uv",
      "args": ["--directory", "/Users/ronakkadam/Work/research-agent-mcp-server", "run", "research-agent-mcp"],
      "env": {"MISTRAL_API_KEY": "...", "TAVILY_API_KEY": "...", "GITHUB_TOKEN": "..."}
    }
  }
}
```

## Run
```bash
uv run research-agent-mcp
```

## Use
Call `research_integration(query, codebase_path?, depth?)` from Claude Code.

Reports save to `./reports/<slug>-<timestamp>.md`

**Example:** `"Add Chainlink price feeds to my Foundry Solidity vault."`

Runtime: 60–180s | Cost: ~$0.10–0.30
