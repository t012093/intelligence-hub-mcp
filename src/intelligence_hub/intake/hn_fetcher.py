"""Hacker News Firebase API fetcher."""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional
import httpx

from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import FeedChannelConfig, IntelligenceRecord
from intelligence_hub.intake.base import BaseFetcher

logger = get_logger(__name__)

BASE_URL = "https://hacker-news.firebaseio.com/v0"


class HackerNewsFetcher(BaseFetcher):
    """Fetches trending stories and discussions from Hacker News via Firebase API."""

    def __init__(self, timeout_sec: float = 10.0, max_concurrency: int = 5):
        self.timeout_sec = timeout_sec
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch(self, channel: FeedChannelConfig) -> List[IntelligenceRecord]:
        endpoint = channel.endpoint or "topstories"
        url = f"{BASE_URL}/{endpoint}.json"
        limit = channel.limit or 20

        logger.info(f"Fetching HN {endpoint} (limit={limit})")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                item_ids: List[int] = resp.json()[:limit]
        except Exception as e:
            logger.error(f"Failed to fetch HN story IDs from {url}: {e}")
            return []

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            tasks = [self._fetch_item(client, item_id, channel) for item_id in item_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        records: List[IntelligenceRecord] = []
        for res in results:
            if isinstance(res, IntelligenceRecord):
                records.append(res)
            elif isinstance(res, Exception):
                logger.debug(f"HN item fetch failed: {res}")

        logger.info(f"Successfully fetched {len(records)} stories from HN {endpoint}")
        return records

    async def _fetch_item(
        self, client: httpx.AsyncClient, item_id: int, channel: FeedChannelConfig
    ) -> Optional[IntelligenceRecord]:
        async with self.semaphore:
            url = f"{BASE_URL}/item/{item_id}.json"
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data or data.get("type") != "story":
                return None

            title = data.get("title", "").strip()
            item_url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
            score = data.get("score", 0)
            comments_count = data.get("descendants", 0)
            by = data.get("by")
            time_epoch = data.get("time")

            published_at = None
            if time_epoch:
                published_at = datetime.fromtimestamp(time_epoch, tz=timezone.utc).isoformat()

            text_content = data.get("text", "")

            return IntelligenceRecord(
                id=f"hn_{item_id}",
                source_type="hn_post",
                channel_id=channel.id,
                channel_name=channel.name,
                category=channel.category,
                is_serendipity=channel.is_serendipity,
                title=title,
                url=item_url,
                author=by,
                published_at=published_at,
                summary=f"[HN Score: {score}, Comments: {comments_count}] {text_content[:300]}",
                raw_content=text_content,
                tags=["hacker-news", channel.category],
                metrics={
                    "score": score,
                    "comments_count": comments_count,
                    "hn_id": item_id,
                },
            )
