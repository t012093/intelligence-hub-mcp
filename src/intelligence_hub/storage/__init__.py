"""Storage module for intelligence records and embeddings."""

from intelligence_hub.storage.embedder import Embedder
from intelligence_hub.storage.lancedb_store import IntelligenceStore

__all__ = ["Embedder", "IntelligenceStore"]
