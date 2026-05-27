from pathlib import Path

import pytest

from research_agent.nodes.report_writer import report_writer
from research_agent.schemas import IntentSpec, ReportSection, ResearchFinding


@pytest.fixture(autouse=True)
def _isolate_reports_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_REPORTS_DIR", str(tmp_path))
    from research_agent import config

    config._settings = None
    yield
    config._settings = None


async def test_report_writer_renders_all_sections(tmp_path: Path):
    state = {
        "query": "Add Chainlink price feeds to my Foundry vault",
        "intent": IntentSpec(target="Chainlink", source_stack="Solidity", frameworks=["Foundry"]),
        "sections": {
            "project_overview": ReportSection(
                id="project_overview", title="Project Overview", body_markdown="Chainlink is an oracle network."
            ),
            "security_review": ReportSection(
                id="security_review", title="Security Review", body_markdown="- Stale prices\n- Decimals"
            ),
        },
        "findings": [
            ResearchFinding(
                id="docs_1", source_type="docs", url="https://docs.chain.link/", title="Chainlink docs",
                snippet="Chainlink oracles", content="content",
            ),
            ResearchFinding(
                id="docs_1", source_type="docs", url="https://docs.chain.link/", title="dup", snippet="x"
            ),
        ],
        "errors": ["web_researcher: timeout"],
    }

    out = await report_writer(state)  # type: ignore[arg-type]
    md = out["report_markdown"]
    path = Path(out["report_path"])

    assert path.exists()
    assert path.parent == tmp_path
    assert "Integrating Chainlink into Solidity" in md
    assert "## Project Overview" in md
    assert "Chainlink is an oracle network" in md
    assert "## Security Review" in md
    assert "## Compatibility Analysis" in md
    assert "_Section not generated._" in md
    assert "## Reference Material" in md
    assert "https://docs.chain.link/" in md
    assert md.count("https://docs.chain.link/") == 1
    assert "## Research Limitations" in md
    assert "timeout" in md
