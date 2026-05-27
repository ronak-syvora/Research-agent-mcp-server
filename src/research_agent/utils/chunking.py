from __future__ import annotations

import re
import uuid

from research_agent.schemas import Chunk
from research_agent.utils.text import estimate_tokens

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown by headings. Returns list of (heading_path, body)."""
    if not text:
        return []

    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []

    if matches[0].start() > 0:
        head = text[: matches[0].start()].strip()
        if head:
            sections.append(("", head))

    heading_stack: list[tuple[int, str]] = []

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()

        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, title))

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        heading_path = " > ".join(h for _, h in heading_stack)
        sections.append((heading_path, body))

    return sections


def _split_paragraphs(body: str) -> list[str]:
    parts = re.split(r"\n\s*\n", body)
    return [p.strip() for p in parts if p.strip()]


def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in pieces if p.strip()]


def chunk_markdown(
    text: str,
    *,
    source_id: str,
    target_tokens: int = 500,
    overlap_tokens: int = 75,
    hard_max_tokens: int = 800,
) -> list[Chunk]:
    """Chunk markdown text into ~target_tokens chunks with overlap.

    Honors heading boundaries; falls back to paragraph then sentence splitting.
    """
    if not text or not text.strip():
        return []

    chunks: list[Chunk] = []
    sections = _split_sections(text)

    overlap_chars = overlap_tokens * 4

    for heading_path, body in sections:
        paragraphs = _split_paragraphs(body)

        buf: list[str] = []
        buf_tokens = 0

        def flush(_heading_path: str = heading_path) -> None:
            nonlocal buf, buf_tokens
            if not buf:
                return
            chunk_text = "\n\n".join(buf).strip()
            chunks.append(
                Chunk(
                    id=uuid.uuid4().hex,
                    text=chunk_text,
                    source_id=source_id,
                    heading_path=_heading_path,
                    token_estimate=estimate_tokens(chunk_text),
                )
            )
            tail = chunk_text[-overlap_chars:] if overlap_chars > 0 else ""
            buf = [tail] if tail else []
            buf_tokens = estimate_tokens(tail) if tail else 0

        for para in paragraphs:
            p_tokens = estimate_tokens(para)

            if p_tokens > hard_max_tokens:
                flush()
                sentences = _split_sentences(para)
                sbuf: list[str] = []
                sbuf_tokens = 0
                for sent in sentences:
                    st = estimate_tokens(sent)
                    if sbuf and sbuf_tokens + st > target_tokens:
                        chunks.append(
                            Chunk(
                                id=uuid.uuid4().hex,
                                text=" ".join(sbuf),
                                source_id=source_id,
                                heading_path=heading_path,
                                token_estimate=sbuf_tokens,
                            )
                        )
                        sbuf = []
                        sbuf_tokens = 0
                    sbuf.append(sent)
                    sbuf_tokens += st
                if sbuf:
                    chunks.append(
                        Chunk(
                            id=uuid.uuid4().hex,
                            text=" ".join(sbuf),
                            source_id=source_id,
                            heading_path=heading_path,
                            token_estimate=sbuf_tokens,
                        )
                    )
                continue

            if buf and buf_tokens + p_tokens > target_tokens:
                flush()
            buf.append(para)
            buf_tokens += p_tokens

        flush()

    return chunks
