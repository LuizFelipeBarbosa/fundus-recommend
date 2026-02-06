import numpy as np
from sentence_transformers import SentenceTransformer

from fundus_recommend.config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def make_embedding_text(title: str, body: str, title_en: str | None = None) -> str:
    """Combine title + first 400 chars of body for embedding input.

    Uses title_en (English translation) when available so non-English articles
    embed in the same semantic space as English ones.
    """
    effective_title = title_en if title_en else title
    snippet = body[:400] if body else ""
    return f"{effective_title}\n{snippet}"


def embed_texts(texts: list[str]) -> np.ndarray:
    """Encode a batch of texts into embedding vectors."""
    model = get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def embed_single(text: str) -> np.ndarray:
    """Encode a single text into an embedding vector."""
    return embed_texts([text])[0]
