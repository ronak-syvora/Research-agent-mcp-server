from __future__ import annotations

from datetime import UTC, datetime

from slugify import slugify


def make_slug(text: str, *, max_length: int = 60) -> str:
    return slugify(text, max_length=max_length, separator="-") or "report"


def timestamp_suffix(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return now.strftime("%Y%m%d-%H%M%S")
