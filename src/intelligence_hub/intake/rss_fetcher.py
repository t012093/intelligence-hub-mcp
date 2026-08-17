"""RSS and Atom feed fetcher."""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, List, Optional
import feedparser
import httpx
from bs4 import BeautifulSoup

from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import FeedChannelConfig, IntelligenceRecord
from intelligence_hub.intake.base import BaseFetcher

logger = get_logger(__name__)


class RSSFetcher(BaseFetcher):
    """Fetches articles from standard RSS / Atom feeds."""

    def __init__(self, timeout_sec: float = 15.0):
        self.timeout_sec = timeout_sec

    async def fetch(self, channel: FeedChannelConfig) -> List[IntelligenceRecord]:
        if not channel.url:
            logger.warning(f"No URL provided for RSS channel: {channel.id}")
            return []

        logger.info(f"Fetching RSS feed: {channel.name} ({channel.url})")
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_sec,
                headers={"User-Agent": "IntelligenceHub/1.0 (Research Crawler)"},
                follow_redirects=True,
            ) as client:
                response = await client.get(channel.url)
                response.raise_for_status()
                content = response.text
        except Exception as e:
            logger.error(f"Failed to fetch RSS from {channel.url}: {e}")
            return []

        # Parse with feedparser
        feed = feedparser.parse(content)
        records: List[IntelligenceRecord] = []

        entries = feed.entries[: channel.limit] if channel.limit else feed.entries
        for entry in entries:
            try:
                rec = self._parse_entry(entry, channel)
                if rec:
                    records.append(rec)
            except Exception as e:
                logger.warning(f"Error parsing RSS entry from {channel.id}: {e}")

        logger.info(f"Fetched {len(records)} items from {channel.name}")
        return records

    def _parse_entry(self, entry: Any, channel: FeedChannelConfig) -> Optional[IntelligenceRecord]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()

        if not title or not link:
            return None

        # Clean summary / content
        summary_raw = getattr(entry, "summary", "") or getattr(entry, "description", "")
        summary_clean = self._clean_html(summary_raw)

        # Generate deterministic ID
        item_id = hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]

        # Author
        author = getattr(entry, "author", None)

        # Published date
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published_at = dt.isoformat()
            except Exception:
                pass

        # Tags / Categories
        tags = []
        if hasattr(entry, "tags"):
            tags = [t.term for t in entry.tags if hasattr(t, "term")]

        return IntelligenceRecord(
            id=item_id,
            source_type="rss",
            channel_id=channel.id,
            channel_name=channel.name,
            category=channel.category,
            is_serendipity=channel.is_serendipity,
            title=title,
            url=link,
            author=author,
            published_at=published_at,
            summary=summary_clean[:1000],  # Keep reasonable summary length
            raw_content=summary_clean,
            tags=tags,
        )

    def _clean_html(self, raw_html: str) -> str:
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()
