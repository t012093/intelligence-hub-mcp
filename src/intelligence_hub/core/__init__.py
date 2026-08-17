"""Core module for intelligence-hub-mcp."""

from intelligence_hub.core.models import (
    FeedChannelConfig,
    ChannelType,
    IntelligenceRecord,
    CrossoverTheme,
    CrossoverDigest,
)
from intelligence_hub.core.feed_loader import FeedRegistryLoader
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.config import LANCEDB_PATH, GEMINI_API_KEY, LLM_MODEL

__all__ = [
    "FeedChannelConfig",
    "ChannelType",
    "IntelligenceRecord",
    "CrossoverTheme",
    "CrossoverDigest",
    "FeedRegistryLoader",
    "get_logger",
    "LANCEDB_PATH",
    "GEMINI_API_KEY",
    "LLM_MODEL",
]
