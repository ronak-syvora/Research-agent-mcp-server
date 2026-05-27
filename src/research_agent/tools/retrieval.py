from __future__ import annotations

import uuid
from dataclasses import dataclass

from research_agent.config import get_settings
from research_agent.logging_setup import get_logger
from research_agent.schemas import Chunk

log = get_logger(__name__)


_chroma_client = None


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        settings = get_settings()
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(settings.chroma_path))
        log.info("Chroma PersistentClient at %s", settings.chroma_path)
    return _chroma_client


@dataclass
class QueryHit:
    chunk: Chunk
    score: float
    matched_query: str


class ChromaIndex:
    """Per-request collection wrapper around chromadb.PersistentClient.

    All Chroma calls are sync; invoke this class via anyio.to_thread.run_sync.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = name or f"req-{uuid.uuid4().hex[:12]}"
        self._collection = None
        self._chunks_by_id: dict[str, Chunk] = {}

    def _ensure_collection(self):
        if self._collection is None:
            client = _get_client()
            self._collection = client.create_collection(
                name=self.name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        collection = self._ensure_collection()

        ids = [c.id for c in chunks]
        docs = [c.text for c in chunks]
        metas = [{"source_id": c.source_id, "heading_path": c.heading_path} for c in chunks]
        collection.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=metas)
        for c in chunks:
            self._chunks_by_id[c.id] = c
        log.info("ChromaIndex %s: added %d chunks", self.name, len(chunks))

    def query(self, query_texts_to_embeddings: list[tuple[str, list[float]]], *, k: int = 6) -> list[QueryHit]:
        if not query_texts_to_embeddings or self._collection is None:
            return []

        collection = self._collection
        seen: set[str] = set()
        out: list[QueryHit] = []

        n = min(k, collection.count() or k)
        if n <= 0:
            return []

        for q_text, q_emb in query_texts_to_embeddings:
            result = collection.query(query_embeddings=[q_emb], n_results=n)
            ids = (result.get("ids") or [[]])[0]
            distances = (result.get("distances") or [[]])[0]
            for chunk_id, dist in zip(ids, distances, strict=False):
                if chunk_id in seen:
                    continue
                seen.add(chunk_id)
                chunk = self._chunks_by_id.get(chunk_id)
                if chunk is None:
                    continue
                score = 1.0 - float(dist)
                out.append(QueryHit(chunk=chunk, score=score, matched_query=q_text))
        return out

    def close(self) -> None:
        if self._collection is None:
            return
        try:
            client = _get_client()
            client.delete_collection(name=self.name)
            log.info("ChromaIndex %s: deleted", self.name)
        except Exception as exc:
            log.warning("Failed to delete Chroma collection %s: %s", self.name, exc)
        finally:
            self._collection = None
            self._chunks_by_id.clear()
