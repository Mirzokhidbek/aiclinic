"""Pluggable embedding backends. M3 benchmarks several; pick by eval score."""

import asyncio
import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from app.config import EMBEDDING_DIM, get_settings


class Embedder(Protocol):
    dim: int

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """Local ONNX sentence-transformers model via fastembed (no external API)."""

    def __init__(self, model_name: str, dim: int = EMBEDDING_DIM) -> None:
        from fastembed import TextEmbedding

        self.dim = dim
        self._model = TextEmbedding(model_name=model_name)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._embed, texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self._embed, [text])
        return vectors[0]


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class HashingEmbedder:
    """Deterministic bag-of-words embedder for tests. Lexical overlap => similarity."""

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            vec[int.from_bytes(digest, "big") % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache
def get_embedder() -> Embedder:
    return FastEmbedEmbedder(get_settings().embedding_model)
