"""Sentence-embedding wrapper (all-MiniLM-L6-v2, 384-d). Lazy-loaded; raises a clear error if unavailable."""
from typing import List, Optional, Protocol

import numpy as np

from app.config import settings


class EmbeddingUnavailable(RuntimeError):
    pass


class Embedder(Protocol):
    name: str
    def encode(self, texts: List[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        self.name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.name)
            except Exception as exc:
                raise EmbeddingUnavailable(
                    "The embedding model could not be loaded. Run 'pip install sentence-transformers' and make "
                    "sure the model can be downloaded on first use."
                ) from exc
        return self._model

    def encode(self, texts: List[str]) -> np.ndarray:
        vecs = self._load().encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=64)
        return np.asarray(vecs, dtype=np.float32)


_embedder: Optional[Embedder] = None


def set_embedder(e: Optional[Embedder]) -> None:
    global _embedder
    _embedder = e


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformerEmbedder(settings.embedding_model)
    return _embedder
