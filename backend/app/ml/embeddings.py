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


_embedders: dict = {}


def set_embedder(e: Optional[Embedder]) -> None:
    """Inject an embedder (tests) - used for both the default and multilingual slots."""
    _embedders.clear()
    if e is not None:
        _embedders["default"] = _embedders["multilingual"] = e


def get_embedder(multilingual: bool = False) -> Embedder:
    key = "multilingual" if multilingual else "default"
    if key not in _embedders:
        _embedders[key] = SentenceTransformerEmbedder(settings.multilingual_model if multilingual else settings.embedding_model)
    return _embedders[key]


class HashingEmbedder:
    """Lexical BASELINE embedder (word + bigram hashing, 384-d). Not used by the pipeline - it exists so the Evaluation page can
    measure how much a semantic model (MiniLM) actually adds over a words-only baseline."""
    name = "lexical hashing baseline (not semantic)"
    mode = "fallback"

    def __init__(self):
        from sklearn.feature_extraction.text import HashingVectorizer
        self._v = HashingVectorizer(n_features=384, alternate_sign=False, norm="l2", ngram_range=(1, 2), stop_words="english")

    def encode(self, texts: List[str]) -> np.ndarray:
        return np.asarray(self._v.transform(texts).todense(), dtype=np.float32)
