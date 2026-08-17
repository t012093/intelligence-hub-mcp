"""End-to-end publication pipeline orchestrating Intake, Genre Routing, Tech Explainer, and Coral News Publishing."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from intelligence_hub.core.config import DATA_DIR
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.feed_loader import FeedRegistryLoader
from intelligence_hub.core.models import ArticleGenre, ArticlePayload
from intelligence_hub.intake import get_fetcher_for_channel
from intelligence_hub.storage.lancedb_store import IntelligenceStore
from intelligence_hub.analysis.crossover import CrossoverAnalyzer
from intelligence_hub.analysis.synthesizer import IntelligenceSynthesizer
from intelligence_hub.analysis.tech_explainer import TechExplainer
from intelligence_hub.analysis.quality_gate import QualityGate
from intelligence_hub.publishing.coral_publisher import CoralPublisher

logger = get_logger(__name__)


class PublishingPipeline:
    """Orchestrates intake, genre routing, analysis, quality validation, and multi-channel publication."""

    def __init__(self):
        self.feed_loader = FeedRegistryLoader()
        self.store = IntelligenceStore()
        self.analyzer = CrossoverAnalyzer()
        self.synthesizer = IntelligenceSynthesizer()
        self.tech_explainer = TechExplainer()
        self.quality_gate = QualityGate()
        self.publisher = CoralPublisher()

    async def run(
        self,
        genre: str = "tech",
        force_fetch: bool = False,
        limit_per_channel: int = 15,
        publish_status: str = "published",
    ) -> Dict[str, Any]:
        """Runs the entire pipeline end-to-end with genre-specific routing."""
        start_time = datetime.now(timezone.utc)
        logger.info(f"=== Starting Hermes Publication Pipeline (genre={genre}) ===")

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

        # 2. Routing & Generation
        if genre in ("tech", "tech_deep_dive"):
            # Select top GitHub/OSS record with README
            recent_records = self.store.list_records(limit=60)
            oss_records = [
                r for r in recent_records if r.source_type == "github_trending" and r.raw_content
            ] or [r for r in recent_records if r.source_type == "github_trending"]

            target_record = oss_records[0] if oss_records else recent_records[0]
            logger.info(f"Selected target OSS repository for Tech Deep-Dive: {target_record.title}")

            # Generate Tech Deep-Dive
            payload = await self.tech_explainer.explain(target_record, status=publish_status)

            # Quality Gate
            is_valid, issues = self.quality_gate.validate(payload)
            if not is_valid:
                logger.warning(f"Quality Gate warnings: {issues}")

            # Publish
            pub_result = await self.publisher.publish_payload(payload)
            x_threads = self.publisher.generate_x_threads_for_tech(payload)

            output_dir = DATA_DIR / "publications"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

            article_file = output_dir / f"article_{timestamp_slug}.json"
            with open(article_file, "w", encoding="utf-8") as f:
                json.dump(payload.model_dump(), f, ensure_ascii=False, indent=2)

            x_thread_file = output_dir / f"x_thread_{timestamp_slug}.txt"
            with open(x_thread_file, "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(x_threads))

            elapsed_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"=== Tech Deep-Dive Pipeline Finished in {elapsed_sec:.2f}s ===")

            return {
                "status": "success",
                "genre": "tech_deep_dive",
                "elapsed_seconds": elapsed_sec,
                "records_ingested": len(all_new_records),
                "target_title": target_record.title,
                "coral_publish_result": pub_result,
                "x_threads": x_threads,
                "artifacts": {
                    "article_json": str(article_file),
                    "x_threads_txt": str(x_thread_file),
                },
            }

        else:
            # Default: Crossover Synthesis
            recent_records = self.store.list_records(limit=60)
            core_records = [r for r in recent_records if not r.is_serendipity]
            serendipity_records = [r for r in recent_records if r.is_serendipity]

            digest = await self.synthesizer.synthesize(
                core_records=core_records,
                serendipity_records=serendipity_records,
                period="daily",
            )

            pub_result = await self.publisher.publish(digest, status=publish_status)
            x_threads = self.publisher.generate_x_threads(digest)

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
            logger.info(f"=== Crossover Pipeline Finished in {elapsed_sec:.2f}s ===")

            return {
                "status": "success",
                "genre": "crossover_feature",
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
    """CLI runner for intelligence-hub-publish with --genre support."""
    parser = argparse.ArgumentParser(description="Intelligence Hub Publisher CLI")
    parser.add_argument(
        "--genre",
        choices=["tech", "crossover"],
        default=os.getenv("PUBLISH_GENRE", "tech"),
        help="Article genre to generate (tech: Tech Deep-Dive, crossover: WIRED Crossover)",
    )
    parser.add_argument(
        "--status",
        choices=["draft", "published"],
        default=os.getenv("PUBLISH_STATUS", "published"),
        help="Article status (published or draft)",
    )
    args = parser.parse_args()

    pipeline = PublishingPipeline()
    res = asyncio.run(pipeline.run(genre=args.genre, publish_status=args.status))
    print("\n" + "=" * 60)
    print(f"🚀 PUBLICATION PIPELINE COMPLETED (Genre: {res.get('genre')})")
    print("=" * 60)
    print(f"Ingested Records: {res['records_ingested']}")
    print(f"Article File:     {res['artifacts'].get('article_json') or res['artifacts'].get('digest_json')}")
    print(f"X Thread File:    {res['artifacts']['x_threads_txt']}")
    print("\n[Preview of Coral Article Payload]:")
    payload = res["coral_publish_result"].get("payload", {})
    print(f"Title:   {payload.get('title')}")
    print(f"Genre:   {payload.get('genre')}")
    print(f"Themes:  {payload.get('themes')}")
    print(f"Excerpt: {payload.get('excerpt')}")
    print("\n[Preview of X Thread (Post 1)]:")
    if res.get("x_threads"):
        print(res["x_threads"][0])
    print("=" * 60)


if __name__ == "__main__":
    main()
