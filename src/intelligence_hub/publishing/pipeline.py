"""End-to-end publication pipeline orchestrating Intake, Genre Routing, Explainer Engines, and Coral News Publishing."""

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
from intelligence_hub.analysis.paper_explainer import PaperExplainer
from intelligence_hub.analysis.protocol_explainer import ProtocolExplainer
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
        self.paper_explainer = PaperExplainer()
        self.protocol_explainer = ProtocolExplainer()
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

        recent_records = self.store.list_records(limit=80)

        # 2. Routing & Generation
        if genre in ("tech", "tech_deep_dive"):
            # Genre ①: OSS Tech Deep-Dive
            oss_records = [
                r for r in recent_records if r.source_type == "github_trending" and r.raw_content
            ] or [r for r in recent_records if r.source_type == "github_trending"]

            target_record = oss_records[0] if oss_records else recent_records[0]
            logger.info(f"Selected target OSS for Tech Deep-Dive: {target_record.title}")

            payload = await self.tech_explainer.explain(target_record, status=publish_status)
            self.quality_gate.validate(payload)
            pub_result = await self.publisher.publish_payload(payload)
            x_threads = self.publisher.generate_x_threads_for_tech(payload)
            artifact_prefix = "tech"

        elif genre in ("paper", "paper_digest"):
            # Genre ②: Academic Paper Digest
            paper_records = [
                r for r in recent_records if r.source_type == "arxiv_query" or "biorxiv" in r.channel_id or "medrxiv" in r.channel_id
            ]
            target_record = paper_records[0] if paper_records else recent_records[0]
            logger.info(f"Selected target paper for Paper Digest: {target_record.title}")

            payload = await self.paper_explainer.explain(target_record, status=publish_status)
            self.quality_gate.validate(payload)
            pub_result = await self.publisher.publish_payload(payload)
            x_threads = self.publisher.generate_x_threads_for_paper(payload)
            artifact_prefix = "paper"

        elif genre in ("protocol", "protocol_security"):
            # Genre ③: Protocol & Security Architecture
            sec_records = [
                r for r in recent_records if r.category in ("crypto", "reverse_engineering") or "ethereum" in r.channel_id
            ]
            target_record = sec_records[0] if sec_records else recent_records[0]
            logger.info(f"Selected target protocol for Security Analysis: {target_record.title}")

            payload = await self.protocol_explainer.explain(target_record, status=publish_status)
            self.quality_gate.validate(payload)
            pub_result = await self.publisher.publish_payload(payload)
            x_threads = self.publisher.generate_x_threads_for_protocol(payload)
            artifact_prefix = "protocol"

        else:
            # Genre ④: Crossover Synthesis
            core_records = [r for r in recent_records if not r.is_serendipity]
            serendipity_records = [r for r in recent_records if r.is_serendipity]

            digest = await self.synthesizer.synthesize(
                core_records=core_records,
                serendipity_records=serendipity_records,
                period="daily",
            )

            pub_result = await self.publisher.publish(digest, status=publish_status)
            x_threads = self.publisher.generate_x_threads(digest)
            payload = ArticlePayload(**(pub_result.get("payload") or {}), genre="crossover_feature")
            self.quality_gate.validate(payload)
            artifact_prefix = "crossover"

        # Save artifacts locally
        output_dir = DATA_DIR / "publications"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        article_file = output_dir / f"{artifact_prefix}_{timestamp_slug}.json"
        with open(article_file, "w", encoding="utf-8") as f:
            json.dump(payload.model_dump(), f, ensure_ascii=False, indent=2)

        x_thread_file = output_dir / f"x_thread_{artifact_prefix}_{timestamp_slug}.txt"
        with open(x_thread_file, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(x_threads))

        elapsed_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"=== Pipeline Finished ({payload.genre}) in {elapsed_sec:.2f}s ===")

        return {
            "status": "success",
            "genre": payload.genre,
            "elapsed_seconds": elapsed_sec,
            "records_ingested": len(all_new_records),
            "title": payload.title,
            "coral_publish_result": pub_result,
            "x_threads": x_threads,
            "artifacts": {
                "article_json": str(article_file),
                "x_threads_txt": str(x_thread_file),
            },
        }


def main():
    """CLI runner for intelligence-hub-publish with multi-genre support."""
    parser = argparse.ArgumentParser(description="Intelligence Hub Publisher CLI")
    parser.add_argument(
        "--genre",
        choices=["tech", "paper", "protocol", "crossover"],
        default=os.getenv("PUBLISH_GENRE", "tech"),
        help="Article genre to generate (tech: OSS Deep-Dive, paper: Academic Digest, protocol: Protocol Security, crossover: WIRED Feature)",
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
    print(f"Title:            {res['title']}")
    print(f"Article File:     {res['artifacts']['article_json']}")
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
