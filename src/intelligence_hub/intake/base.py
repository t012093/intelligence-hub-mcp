"""Abstract base fetcher for intelligence intake."""

from abc import ABC, abstractmethod
from typing import List
from intelligence_hub.core.models import FeedChannelConfig, IntelligenceRecord


class BaseFetcher(ABC):
    """Abstract base class for all intake fetchers."""

    @abstractmethod
    async def fetch(self, channel: FeedChannelConfig) -> List[IntelligenceRecord]:
        """Fetch items from the specified channel configuration."""
        pass
