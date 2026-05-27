from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from research_agent.schemas import (
    AudienceProfile,
    IntentSpec,
    ReportSection,
    ResearchFinding,
    ResearchPlan,
    RetrievedChunk,
    ScanResult,
)


class GraphState(TypedDict, total=False):
    query: str
    codebase_path: str | None
    depth: str

    intent: IntentSpec
    audience: AudienceProfile | None
    plan: ResearchPlan

    findings: Annotated[list[ResearchFinding], add]
    scan: ScanResult | None
    errors: Annotated[list[str], add]

    sub_question: str
    docs_url: str

    retrieved: list[RetrievedChunk]

    sections: dict[str, ReportSection]

    report_markdown: str
    report_path: str
