import json

from research_agent.schemas import (
    Chunk,
    IntentSpec,
    ResearchFinding,
    ResearchPlan,
    RetrievedChunk,
    ScanResult,
)


def test_intent_spec_roundtrip():
    intent = IntentSpec(
        target="Chainlink",
        source_stack="Solidity",
        frameworks=["Foundry"],
        domain="DeFi",
        constraints=[],
    )
    raw = intent.model_dump_json()
    assert IntentSpec.model_validate_json(raw) == intent


def test_research_plan_defaults():
    plan = ResearchPlan()
    assert plan.sub_questions == []
    assert plan.web_queries == []


def test_research_finding_minimal():
    f = ResearchFinding(id="src_001", source_type="web")
    assert f.url == ""
    assert f.warnings == []


def test_retrieved_chunk():
    c = Chunk(id="c1", text="x", source_id="src_001")
    rc = RetrievedChunk(chunk=c, score=0.84, matched_query="q")
    j = rc.model_dump_json()
    assert json.loads(j)["score"] == 0.84


def test_scan_result_defaults():
    s = ScanResult(root_path="/x")
    assert s.languages == {}
    assert s.frameworks == []


def test_intent_invalid_task_type_rejected():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        IntentSpec(target="x", task_type="nope")  # type: ignore[arg-type]
