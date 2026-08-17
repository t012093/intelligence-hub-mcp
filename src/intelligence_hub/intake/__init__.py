"""Intake module for intelligence data ingestion."""

from typing import Optional
from intelligence_hub.core.models import FeedChannelConfig
from intelligence_hub.intake.base import BaseFetcher
from intelligence_hub.intake.rss_fetcher import RSSFetcher
from intelligence_hub.intake.hn_fetcher import HackerNewsFetcher
from intelligence_hub.intake.academic_fetcher import AcademicFetcher
from intelligence_hub.intake.github_fetcher import GitHubFetcher

__all__ = [
    "BaseFetcher",
    "RSSFetcher",
    "HackerNewsFetcher",
    "AcademicFetcher",
    "GitHubFetcher",
    "get_fetcher_for_channel",
]


def get_fetcher_for_channel(channel: FeedChannelConfig) -> Optional[BaseFetcher]:
    """Returns the appropriate fetcher instance for the given channel type."""
    if channel.type == "rss":
        return RSSFetcher()
    elif channel.type == "api_hn":
        return HackerNewsFetcher()
    elif channel.type == "arxiv_query":
        return AcademicFetcher()
    elif channel.type == "github_trending":
        return GitHubFetcher()
    return None
