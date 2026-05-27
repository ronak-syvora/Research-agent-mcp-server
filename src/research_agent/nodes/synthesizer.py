from __future__ import annotations

import asyncio
from collections.abc import Iterable

from pydantic import BaseModel, Field

from research_agent.llm import mistral_client
from research_agent.logging_setup import get_logger
from research_agent.prompts import (
    ROLE_SECTION_GROUPS,
    SECTION_GUIDELINES,
    SECTION_TITLES,
    build_synthesizer_system,
    get_role_key,
)
from research_agent.schemas import ReportSection, ResearchFinding, RetrievedChunk
from research_agent.state import GraphState

log = get_logger(__name__)


class _SynthesizerOutput(BaseModel):
    sections: list[ReportSection] = Field(default_factory=list)


_MAX_FINDING_CHARS_PER_SOURCE: dict[str, int] = {
    "docs": 4000,
    "github": 3000,
    "web": 2000,
    "codebase": 4000,
}

_TOP_N_PER_SOURCE: dict[str, int] = {
    "docs": 4,
    "github": 4,
    "web": 6,
    "codebase": 1,
}


def _select_findings(findings: Iterable[ResearchFinding]) -> list[ResearchFinding]:
    by_type: dict[str, list[ResearchFinding]] = {"web": [], "docs": [], "github": [], "codebase": []}
    for f in findings:
        by_type.setdefault(f.source_type, []).append(f)

    selected: list[ResearchFinding] = []
    for t, items in by_type.items():
        cap = _TOP_N_PER_SOURCE.get(t, 3)
        selected.extend(items[:cap])
    return selected


def _render_findings_block(findings: list[ResearchFinding]) -> str:
    if not findings:
        return "<findings>(no findings)</findings>"

    parts: list[str] = ["<findings>"]
    for f in findings:
        char_cap = _MAX_FINDING_CHARS_PER_SOURCE.get(f.source_type, 2000)
        body = (f.content or f.snippet or "").strip()[:char_cap]
        parts.append(
            f"[id={f.id} type={f.source_type} url={f.url}]\n"
            f"Title: {f.title}\n"
            f"---\n{body}\n---"
        )
    parts.append("</findings>")
    return "\n\n".join(parts)


def _render_retrieved_block(retrieved: list[RetrievedChunk], findings: list[ResearchFinding]) -> str:
    """Render the curated chunks (from RAG) plus a compact source map for citations."""
    if not retrieved:
        return ""

    source_map = {f.id: (f.source_type, f.url, f.title) for f in findings}

    parts: list[str] = ["<retrieved_context>"]
    for rc in retrieved:
        c = rc.chunk
        st, url, title = source_map.get(c.source_id, ("?", "", ""))
        head = c.heading_path or "(no heading)"
        parts.append(
            f"[chunk={c.id[:8]} source={c.source_id} type={st} score={rc.score:.2f} heading={head!r}]\n"
            f"Source title: {title}\n"
            f"---\n{c.text}\n---"
        )
    parts.append("</retrieved_context>")

    src_lines = ["<source_map>"]
    for sid, (st, url, title) in source_map.items():
        src_lines.append(f"{sid}: {st} | {title} | {url}")
    src_lines.append("</source_map>")

    return "\n\n".join(parts) + "\n\n" + "\n".join(src_lines)


def _render_section_request(section_ids: list[str]) -> str:
    lines = ["<sections_to_generate>"]
    for sid in section_ids:
        lines.append(
            f"- id: {sid}\n  title: {SECTION_TITLES[sid]}\n  guidelines: {SECTION_GUIDELINES[sid]}"
        )
    lines.append("</sections_to_generate>")
    return "\n".join(lines)


async def _generate_group(
    group_name: str,
    section_ids: list[str],
    intent_block: str,
    scan_block: str,
    findings_block: str,
    system_prompt: str,
) -> list[ReportSection]:
    user = "\n\n".join(
        [
            intent_block,
            scan_block,
            findings_block,
            _render_section_request(section_ids),
            (
                "Generate ALL requested sections. Return JSON with the 'sections' array. "
                "Each section's 'id' must exactly match one of the requested ids."
            ),
        ]
    )

    try:
        result = await mistral_client.complete_json(
            system=system_prompt,
            user=user,
            schema=_SynthesizerOutput,
            temperature=0.3,
            max_tokens=4000,
        )
        sections = list(result.sections)
        log.info("synthesizer group %s -> %d sections", group_name, len(sections))
        return sections
    except Exception as exc:
        log.exception("synthesizer group %s failed", group_name)
        return [
            ReportSection(
                id=sid,
                title=SECTION_TITLES.get(sid, sid.replace("_", " ").title()),
                body_markdown=f"_Section generation failed: {exc}_",
            )
            for sid in section_ids
        ]


async def synthesizer(state: GraphState) -> dict:
    intent = state["intent"]
    findings = list(state.get("findings", []))
    retrieved = list(state.get("retrieved", []))

    audience = state.get("audience")
    if audience is not None:
        role_key = get_role_key(audience.role, audience.skill_level)
        tone = audience.tone
    else:
        role_key = "developer_intermediate"
        tone = "technical"
    system_prompt = build_synthesizer_system(tone)
    group_a, group_b, group_c = ROLE_SECTION_GROUPS[role_key]
    log.info("synthesizer: role_key=%s tone=%s", role_key, tone)

    intent_block = (
        f"<intent>\n{intent.model_dump_json(indent=2)}\n</intent>"
    )

    scan = state.get("scan")
    if scan is not None:
        scan_summary = {
            "primary_language": scan.primary_language,
            "frameworks": scan.frameworks,
            "build_tools": scan.build_tools,
            "manifests": [
                {"kind": m.kind, "deps_sample": list(m.dependencies.keys())[:20]}
                for m in scan.manifests
            ],
            "directory_tree": scan.directory_tree,
            "readme_excerpt": (scan.readme_excerpt or "")[:1000],
        }
        scan_block = f"<codebase_scan>\n{scan_summary}\n</codebase_scan>"
    else:
        scan_block = "<codebase_scan>(no codebase provided)</codebase_scan>"

    if retrieved:
        findings_block = _render_retrieved_block(retrieved, findings)
        mode = "retrieved"
        n_used = len(retrieved)
    else:
        selected = _select_findings(findings)
        findings_block = _render_findings_block(selected)
        mode = "raw"
        n_used = len(selected)

    log.info(
        "synthesizer: mode=%s items=%d total_findings=%d codebase=%s",
        mode, n_used, len(findings), "yes" if scan else "no",
    )

    group_results = await asyncio.gather(
        _generate_group("A", group_a, intent_block, scan_block, findings_block, system_prompt),
        _generate_group("B", group_b, intent_block, scan_block, findings_block, system_prompt),
        _generate_group("C", group_c, intent_block, scan_block, findings_block, system_prompt),
    )

    sections: dict[str, ReportSection] = {}
    for group_sections in group_results:
        for sec in group_sections:
            sections[sec.id] = sec

    return {"sections": sections}
