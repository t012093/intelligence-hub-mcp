"""Public MCP tools for intelligence-hub."""

import asyncio
from typing import Any, Dict, List, Optional

from intelligence_hub.core.feed_loader import FeedRegistryLoader
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import CrossoverDigest, IntelligenceRecord
from intelligence_hub.intake import get_fetcher_for_channel
from intelligence_hub.storage import IntelligenceStore
from intelligence_hub.analysis import IntelligenceSynthesizer

logger = get_logger(__name__)

# Singletons for orchestration
feed_loader = FeedRegistryLoader()
store = IntelligenceStore()
synthesizer = IntelligenceSynthesizer()


from datetime import datetime, timedelta, timezone

async def fetch_intelligence_feed(
    category: Optional[str] = None,
    limit_per_channel: Optional[int] = None,
    force_fetch: bool = False,
) -> Dict[str, Any]:
    """Fetches the latest intelligence items across configured feeds in parallel and saves them to LanceDB.

    Args:
        category: Optional category filter (e.g. 'ai_engineering', 'synthetic_biology', 'neuroscience').
        limit_per_channel: Optional limit override for items fetched per feed.
        force_fetch: If True, ignores interval_hours and forces fetching all matching channels.
    """
    channels = (
        feed_loader.get_channels_by_category(category)
        if category
        else feed_loader.get_all_channels()
    )

    if not channels:
        return {"status": "error", "message": f"No channels found for category: {category}"}

    # Check interval_hours if not force_fetch
    last_fetched_times = store.get_channel_last_fetched_times() if not force_fetch else {}
    now = datetime.now(timezone.utc)
    target_channels = []
    skipped_intervals = 0

    for ch in channels:
        if not force_fetch and ch.id in last_fetched_times:
            try:
                last_dt = datetime.fromisoformat(last_fetched_times[ch.id])
                if now - last_dt < timedelta(hours=ch.interval_hours):
                    skipped_intervals += 1
                    continue
            except Exception:
                pass
        target_channels.append(ch)

    if not target_channels:
        return {
            "status": "success",
            "message": f"All {len(channels)} channels are within their interval_hours. No fetch needed (use force_fetch=True to override).",
            "channels_scanned": len(channels),
            "channels_fetched": 0,
            "skipped_by_interval": skipped_intervals,
            "total_fetched": 0,
            "newly_saved_to_db": 0,
            "categories_updated": [],
        }

    async def _fetch_single(ch) -> List[IntelligenceRecord]:
        target_ch = ch.model_copy(update={"limit": limit_per_channel}) if limit_per_channel else ch
        fetcher = get_fetcher_for_channel(target_ch)
        if not fetcher:
            logger.info(f"No fetcher available for channel type: {target_ch.type} ({target_ch.id})")
            return []
        try:
            return await fetcher.fetch(target_ch)
        except Exception as e:
            logger.error(f"Error fetching channel {target_ch.id}: {e}")
            return []

    # Parallel fetch across target channels
    results = await asyncio.gather(*[_fetch_single(ch) for ch in target_channels], return_exceptions=True)

    all_records: List[IntelligenceRecord] = []
    for res in results:
        if isinstance(res, list):
            all_records.extend(res)
        elif isinstance(res, Exception):
            logger.error(f"Channel fetch exception: {res}")

    total_fetched = len(all_records)
    saved_count = store.save_records(all_records)

    return {
        "status": "success",
        "channels_scanned": len(channels),
        "channels_fetched": len(target_channels),
        "skipped_by_interval": skipped_intervals,
        "total_fetched": total_fetched,
        "newly_saved_to_db": saved_count,
        "categories_updated": list({r.category for r in all_records}),
    }


async def search_intelligence(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Searches stored intelligence records using semantic vector search.

    Args:
        query: Search query or conceptual description.
        category: Optional category filter.
        limit: Maximum results to return.
    """
    records = store.search(query=query, category=category, limit=limit)
    return [r.model_dump() for r in records]


async def list_intelligence_records(
    category: Optional[str] = None,
    is_serendipity: Optional[bool] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Lists recently fetched intelligence records with optional filtering.

    Args:
        category: Filter by specific category.
        is_serendipity: Filter for serendipity (True) or core (False) items.
        limit: Maximum items to list.
    """
    records = store.list_records(category=category, is_serendipity=is_serendipity, limit=limit)
    return [r.model_dump() for r in records]


async def generate_crossover_digest(
    period: str = "daily",
    fetch_latest_first: bool = True,
) -> Dict[str, Any]:
    """Generates an interdisciplinary crossover report combining 80% core tracking and 20% serendipity.

    Args:
        period: 'daily' or 'weekly'.
        fetch_latest_first: If True, triggers a quick feed intake before synthesis.
    """
    if fetch_latest_first:
        await fetch_intelligence_feed(limit_per_channel=5)

    core_records = store.list_records(is_serendipity=False, limit=20)
    serendipity_records = store.list_records(is_serendipity=True, limit=10)

    if not core_records and not serendipity_records:
        return {
            "status": "error",
            "message": "No records available in database. Please run fetch_intelligence_feed first.",
        }

    digest = await synthesizer.synthesize(
        core_records=core_records,
        serendipity_records=serendipity_records,
        period=period,
    )

    return {
        "status": "success",
        "digest_id": digest.digest_id,
        "period": digest.period,
        "crossover_themes_count": len(digest.crossover_themes),
        "crossover_themes": [t.model_dump() for t in digest.crossover_themes],
        "markdown_report": digest.markdown_report,
        "suggested_themes": digest.suggested_themes,
        "suggested_tags": digest.suggested_tags,
        "referenced_records_count": len(digest.source_records),
    }


async def get_feed_status() -> Dict[str, Any]:
    """Returns the current registry of feed channels and storage statistics."""
    all_channels = feed_loader.get_all_channels()
    stats = store.get_stats()

    return {
        "status": "success",
        "channels_configured": len(all_channels),
        "channels": [
            {
                "id": c.id,
                "name": c.name,
                "category": c.category,
                "type": c.type,
                "is_serendipity": c.is_serendipity,
            }
            for c in all_channels
        ],
        "database_stats": stats,
    }
