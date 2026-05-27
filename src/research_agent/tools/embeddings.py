from __future__ import annotations

from research_agent.config import get_settings
from research_agent.llm import mistral_client
from research_agent.logging_setup import get_logger

log = get_logger(__name__)


_call_count = 0


def reset_call_count() -> None:
    global _call_count
    _call_count = 0


def get_call_count() -> int:
    return _call_count


async def embed_texts(texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
    """Embed a list of texts with mistral-embed. Enforces a per-process call cap."""
    global _call_count
    settings = get_settings()
    if not texts:
        return []

    expected_batches = (len(texts) + batch_size - 1) // batch_size
    if _call_count + expected_batches > settings.max_embed_calls:
        raise RuntimeError(
            f"max_embed_calls ({settings.max_embed_calls}) would be exceeded; "
            f"current={_call_count}, requested={expected_batches}"
        )
    _call_count += expected_batches

    log.info("embed_texts: %d texts in %d batches", len(texts), expected_batches)
    return await mistral_client.embed_batch(texts, batch_size=batch_size)
