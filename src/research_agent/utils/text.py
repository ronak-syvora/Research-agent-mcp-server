from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token). Good enough for budgeting."""
    if not text:
        return 0
    return max(1, len(text) // 4)
