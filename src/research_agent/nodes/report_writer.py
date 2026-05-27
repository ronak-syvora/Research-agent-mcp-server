from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import anyio

from research_agent.config import get_settings
from research_agent.logging_setup import get_logger
from research_agent.prompts import CANONICAL_SECTION_ORDER, SECTION_TITLES
from research_agent.schemas import ResearchFinding
from research_agent.state import GraphState
from research_agent.utils.markdown import make_slug, timestamp_suffix

log = get_logger(__name__)


def _render_references(findings: list[ResearchFinding]) -> str:
    if not findings:
        return "_No external sources gathered._"

    seen_urls: set[str] = set()
    lines: list[str] = []
    counter = 1
    for f in findings:
        if not f.url or f.url in seen_urls:
            continue
        seen_urls.add(f.url)
        title = f.title.strip() or f.url
        snippet = (f.snippet or "").strip().splitlines()
        teaser = snippet[0][:160] if snippet else ""
        tag = f.source_type
        lines.append(f"{counter}. [{title}]({f.url}) — *{tag}* — {teaser}")
        counter += 1

    return "\n".join(lines)


def _render_research_limitations(errors: list[str]) -> str:
    if not errors:
        return ""
    body = "\n".join(f"- {e}" for e in errors[:20])
    return f"\n\n## Research Limitations\n\nThe following non-fatal issues occurred during research:\n\n{body}\n"


async def report_writer(state: GraphState) -> dict:
    intent = state["intent"]
    sections = state.get("sections") or {}
    findings = list(state.get("findings", []))
    errors = list(state.get("errors", []))
    query = state.get("query", "")

    title = f"Integrating {intent.target}"
    if intent.source_stack:
        title += f" into {intent.source_stack}"

    now = datetime.now(UTC)
    slug = make_slug(title)
    filename = f"{slug}-{timestamp_suffix(now)}.md"

    body_parts: list[str] = [
        f"# {title}\n",
        f"> Generated {now.strftime('%Y-%m-%d %H:%M UTC')} by research-agent.  ",
        f"> Original query: _{query}_\n",
    ]

    for sid in CANONICAL_SECTION_ORDER:
        sec = sections.get(sid)
        title_line = f"## {SECTION_TITLES[sid]}"
        if sec is None or not sec.body_markdown.strip():
            body_parts.append(f"{title_line}\n\n_Section not generated._\n")
            continue
        body_parts.append(f"{title_line}\n\n{sec.body_markdown.strip()}\n")

    body_parts.append("## Reference Material\n\n" + _render_references(findings) + "\n")

    limitations = _render_research_limitations(errors)
    if limitations:
        body_parts.append(limitations)

    markdown = "\n".join(body_parts)

    settings = get_settings()
    reports_dir = Path(settings.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / filename

    def _write() -> None:
        out_path.write_text(markdown, encoding="utf-8")

    await anyio.to_thread.run_sync(_write)
    log.info("report_writer: wrote %s (%d bytes)", out_path, len(markdown))

    return {"report_markdown": markdown, "report_path": str(out_path)}
