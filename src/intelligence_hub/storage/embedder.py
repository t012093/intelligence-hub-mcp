"""Text embedder using Gemini or fallback."""

from typing import List
from google import genai

from intelligence_hub.core.config import GEMINI_API_KEY, EMBEDDING_MODEL
from intelligence_hub.core.logger import get_logger

logger = get_logger(__name__)


class Embedder:
    """Generates embedding vectors for text search."""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.client = None
        self._warned_no_key = False
        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client for embeddings: {e}")

    def embed(self, text: str) -> List[float]:
        """Embeds a single text string."""
        if not text.strip():
            return [0.0] * self.dimension

        if self.client:
            try:
                result = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=text[:2000],
                )
                if result.embedding and result.embedding.values:
                    return list(result.embedding.values)
            except Exception as e:
                logger.error(f"Gemini embedding error: {e}")

        # Fallback dummy zero vector
        if not self._warned_no_key:
            logger.warning(
                "GEMINI_API_KEY is not set or client unavailable. Using zero vectors (vector search will be non-functional)."
            )
            self._warned_no_key = True
        return [0.0] * self.dimension

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds multiple texts."""
        return [self.embed(t) for t in texts]
