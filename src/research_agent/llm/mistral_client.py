from __future__ import annotations

import asyncio
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from research_agent.config import get_settings
from research_agent.logging_setup import get_logger

log = get_logger(__name__)


T = TypeVar("T", bound=BaseModel)


_client = None


def _get_client():
    global _client
    if _client is None:
        from mistralai.client import Mistral

        settings = get_settings()
        if not settings.mistral_api_key:
            raise RuntimeError("MISTRAL_API_KEY is not set")
        _client = Mistral(api_key=settings.mistral_api_key)
    return _client


async def _chat(messages: list[dict], *, response_format: dict | None = None,
                temperature: float = 0.3, max_tokens: int | None = None,
                max_attempts: int = 3) -> str:
    client = _get_client()
    settings = get_settings()
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            resp = await client.chat.complete_async(
                model=settings.mistral_chat_model,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            retryable = (
                "429" in msg
                or "rate" in msg
                or "timeout" in msg
                or "temporarily" in msg
                or "503" in msg
                or "502" in msg
            )
            if attempt == max_attempts - 1 or not retryable:
                raise
            delay = 2.0 * (2**attempt)
            log.warning("Mistral chat retryable error (attempt %d/%d, sleep %.1fs): %s",
                        attempt + 1, max_attempts, delay, exc)
            await asyncio.sleep(delay)

    raise last_exc or RuntimeError("Mistral chat failed")


async def complete_json(system: str, user: str, schema: type[T], *,
                        temperature: float = 0.1, max_tokens: int | None = None) -> T:
    """Run a chat completion in JSON mode and validate against a pydantic schema.

    Retries once with the validation error appended to the prompt if the first
    response fails schema validation.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    raw = await _chat(
        messages,
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        return schema.model_validate_json(raw)
    except ValidationError as err:
        log.warning("JSON schema validation failed on first try: %s", err)
        retry_user = (
            f"{user}\n\n---\nYour previous response failed schema validation with these errors:\n"
            f"{err}\n\nReturn corrected JSON that strictly matches the requested schema."
        )
        retry_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": retry_user},
        ]
        raw2 = await _chat(
            retry_messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return schema.model_validate_json(raw2)


async def complete_text(system: str, user: str, *,
                        temperature: float = 0.3, max_tokens: int | None = None) -> str:
    return await _chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )


async def embed_batch(texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
    """Call mistral-embed in batches. Returns a flat list of embedding vectors."""
    client = _get_client()
    settings = get_settings()
    out: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        for attempt in range(3):
            try:
                resp = await client.embeddings.create_async(
                    model=settings.mistral_embed_model,
                    inputs=batch,
                )
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                delay = 2.0 * (2**attempt)
                log.warning("Mistral embeddings retry (attempt %d, sleep %.1fs): %s",
                            attempt + 1, delay, exc)
                await asyncio.sleep(delay)

        for item in resp.data:
            vec = list(item.embedding)
            if len(vec) != settings.embed_dim:
                raise RuntimeError(
                    f"Unexpected embedding dim {len(vec)} (expected {settings.embed_dim})"
                )
            out.append(vec)

    return out
