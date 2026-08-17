"""End-to-end publication pipeline orchestrating Intake, Crossover Analysis, and Coral News Publishing."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional

from intelligence_hub.core.config import DATA_DIR
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.feed_loader import FeedRegistryLoader
from intelligence_hub.intake import get_fetcher_for_channel
from intelligence_hub.storage.lancedb_store import IntelligenceStore
from intelligence_hub.analysis.crossover import CrossoverAnalyzer
from intelligence_hub.analysis.synthesizer import IntelligenceSynthesizer
from intelligence_hub.publishing.coral_publisher import CoralPublisher

logger = get_logger(__name__)


class PublishingPipeline:
    """Orchestrates intake, analysis, and multi-channel publication."""

    def __init__(self):
        self.feed_loader = FeedRegistryLoader()
        self.store = IntelligenceStore()
        self.analyzer = CrossoverAnalyzer()
        self.synthesizer = IntelligenceSynthesizer()
        self.publisher = CoralPublisher()

    async def run(
        self,
        force_fetch: bool = False,
        limit_per_channel: int = 15,
        publish_status: str = "draft",
    ) -> Dict[str, Any]:
        """Runs the entire pipeline end-to-end."""
        start_time = datetime.now(timezone.utc)
        logger.info("=== Starting Hermes Publication Pipeline ===")

        # 1. Intake
        channels = self.feed_loader.get_all_channels()
        fetch_tasks = []
        for ch in channels:
            ch_exec = ch.model_copy(update={"limit": limit_per_channel})
            fetcher = get_fetcher_for_channel(ch_exec)
            if fetcher:
                fetch_tasks.append(fetcher.fetch(ch_exec))

        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        all_new_records = []
        for res in fetch_results:
            if isinstance(res, list):
                all_new_records.extend(res)

        if all_new_records:
            self.store.save_records(all_new_records)
            logger.info(f"Ingested and saved {len(all_new_records)} records to LanceDB.")

        # 2. Synthesis
        recent_records = self.store.list_records(limit=60)
        core_records = [r for r in recent_records if not r.is_serendipity]
        serendipity_records = [r for r in recent_records if r.is_serendipity]

        digest = await self.synthesizer.synthesize(
            core_records=core_records,
            serendipity_records=serendipity_records,
            period="daily",
        )

        # 3. Format & Publish for Coral Magazine
        pub_result = await self.publisher.publish(digest, status=publish_status)
        x_threads = self.publisher.generate_x_threads(digest)

        # Save artifacts locally
        output_dir = DATA_DIR / "publications"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        digest_file = output_dir / f"digest_{timestamp_slug}.json"
        with open(digest_file, "w", encoding="utf-8") as f:
            json.dump(digest.model_dump(), f, ensure_ascii=False, indent=2)

        x_thread_file = output_dir / f"x_thread_{timestamp_slug}.txt"
        with open(x_thread_file, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(x_threads))

        elapsed_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"=== Pipeline Finished in {elapsed_sec:.2f}s ===")

        return {
            "status": "success",
            "elapsed_seconds": elapsed_sec,
            "records_ingested": len(all_new_records),
            "digest_id": digest.digest_id,
            "crossover_themes_count": len(digest.crossover_themes),
            "coral_publish_result": pub_result,
            "x_threads": x_threads,
            "artifacts": {
                "digest_json": str(digest_file),
                "x_threads_txt": str(x_thread_file),
            },
        }


def main():
    """CLI runner for intelligence-hub-publish."""
    pipeline = PublishingPipeline()
    res = asyncio.run(pipeline.run())
    print("\n" + "=" * 60)
    print("🚀 PUBLICATION PIPELINE COMPLETED")
    print("=" * 60)
    print(f"Ingested Records: {res['records_ingested']}")
    print(f"Crossover Themes: {res['crossover_themes_count']}")
    print(f"Digest File:      {res['artifacts']['digest_json']}")
    print(f"X Thread File:    {res['artifacts']['x_threads_txt']}")
    print("\n[Preview of Coral Article Payload]:")
    payload = res["coral_publish_result"].get("payload", {})
    print(f"Title:   {payload.get('title')}")
    print(f"Themes:  {payload.get('themes')}")
    print(f"Tags:    {payload.get('tags')}")
    print(f"Excerpt: {payload.get('excerpt')}")
    print("\n[Preview of X Thread (Post 1)]:")
    if res["x_threads"]:
        print(res["x_threads"][0])
    print("=" * 60)


if __name__ == "__main__":
    main()
