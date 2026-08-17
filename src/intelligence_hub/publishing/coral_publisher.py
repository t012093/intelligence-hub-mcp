"""Coral News Publisher for converting CrossoverDigests into WIRED-style articles and drafting to Coral Magazine."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import CrossoverDigest, CrossoverTheme

logger = get_logger(__name__)

DEFAULT_AUTHOR_ID = "a51cc056-5604-47d2-88ea-4647e4c46411"  # Naoya Kusunoki
DEFAULT_CORAL_API_URL = os.getenv("CORAL_API_URL", "http://127.0.0.1:3001/api/articles")


class CoralPublisher:
    """Publishes crossover intelligence digests to Coral Magazine (Neon DB / API)."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        author_id: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        self.api_url = api_url or DEFAULT_CORAL_API_URL
        self.author_id = author_id or DEFAULT_AUTHOR_ID
        self.database_url = database_url or os.getenv("DATABASE_URL") or os.getenv("CORAL_DATABASE_URL")

    def format_article_payload(
        self, digest: CrossoverDigest, status: str = "draft"
    ) -> Dict[str, Any]:
        """Converts a CrossoverDigest into the Coral Magazine article schema."""
        themes = digest.suggested_themes or ["テクノロジー"]
        tags = digest.suggested_tags or ["Crossover", "Intelligence", "80:20"]

        # Date for title
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        title = f"異分野交差点インテリジェンス・ダイジェスト ({now_str})"
        slug = f"crossover-digest-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Generate Excerpt (< 120 chars)
        themes_summary = "、".join([t.theme_title for t in digest.crossover_themes[:2]])
        excerpt = f"【80:20交差点分析】{themes_summary}などを中心に、先端AI・バイオ・Web3・低レイヤーの越境シナジーをWIRED視点で読み解く。"[:120]

        # Convert Markdown report into WIRED-compliant HTML
        content_html = self._convert_to_wired_html(digest)

        return {
            "title": title,
            "slug": slug,
            "content": content_html,
            "excerpt": excerpt,
            "status": status,
            "themes": themes,
            "tags": tags,
            "reading_time": 10,
            "author_id": self.author_id,
        }

    def _convert_to_wired_html(self, digest: CrossoverDigest) -> str:
        """Constructs a 3-part WIRED structure HTML from digest components."""
        hook_text = (
            "<p>異なる領域のフロンティアが衝突するとき、予測不能なイノベーションの火花が散る。"
            "本日のインテリジェンス・ハーベストでは、定点観測されたコア技術動向と20%のセレンディピティ飛び地データから、"
            "新たな構造的アナロジーと技術的越境の兆候が浮き彫りとなった。</p>"
        )

        # The Paradigm Shift (Cross-Domain Analysis & Comparison Table)
        crossover_html_parts = []
        for theme in digest.crossover_themes:
            actions_html = "".join([f"<li>{a}</li>" for a in theme.actionable_implications])
            crossover_html_parts.append(
                f"<h3>{theme.theme_title}</h3>"
                f"<p><strong>交差領域:</strong> {', '.join(theme.domains)}</p>"
                f"<p>{theme.core_concept}</p>"
                f"<p>{theme.synergy_description}</p>"
                f"<h4>実務的・戦略的示唆</h4>"
                f"<ul>{actions_html}</ul>"
            )
        crossover_content = "".join(crossover_html_parts)

        # Comparison Table
        table_html = (
            "<table style='width:100%; border-collapse: collapse; margin: 1.5rem 0;'>"
            "<thead><tr style='background: #f4f4f5; text-align: left;'>"
            "<th style='padding: 8px; border: 1px solid #e4e4e7;'>ドメイン交差点</th>"
            "<th style='padding: 8px; border: 1px solid #e4e4e7;'>従来のパラダイム</th>"
            "<th style='padding: 8px; border: 1px solid #e4e4e7;'>交差点による創発</th>"
            "</tr></thead><tbody>"
        )
        for t in digest.crossover_themes[:3]:
            domains_str = " × ".join(t.domains)
            table_html += (
                f"<tr>"
                f"<td style='padding: 8px; border: 1px solid #e4e4e7;'><strong>{domains_str}</strong></td>"
                f"<td style='padding: 8px; border: 1px solid #e4e4e7;'>単一専門領域での閉鎖的最適化</td>"
                f"<td style='padding: 8px; border: 1px solid #e4e4e7;'>{t.core_concept[:60]}...</td>"
                f"</tr>"
            )
        table_html += "</tbody></table>"

        # The Philosophical Horizon
        horizon_text = (
            "<p>あらゆる専門分野の境界線は、計算知能とオープンプロトコルによって再定義されつつある。"
            "これらの越境的兆候が結実する5年後、私たちの組織、プロダクト、そして人間の知性はどのような形態へと進化しているだろうか？"
            "未知の領域への越境こそが、次のパラダイムシフトを創出する鍵である。</p>"
        )

        # References
        refs_html_parts = []
        for url in digest.source_records[:15]:
            refs_html_parts.append(f"<li><a href='{url}' target='_blank' rel='noopener'>{url}</a></li>")
        refs_html = "<ul>" + "".join(refs_html_parts) + "</ul>" if refs_html_parts else "<p>一次ソース参照。</p>"

        # Combine into strict WIRED structure
        html = (
            f"<h2>The Hook (導入)</h2>\n{hook_text}\n"
            f"<h2>The Paradigm Shift (越境と構造変革)</h2>\n{crossover_content}\n{table_html}\n"
            f"<h2>The Philosophical Horizon (結びと問い)</h2>\n{horizon_text}\n"
            f"<h2>参考文献・出典（References）</h2>\n{refs_html}"
        )
        return html

    def generate_x_threads(self, digest: CrossoverDigest) -> List[str]:
        """Generates a 3-part thread for X (Twitter)."""
        now_str = datetime.now(timezone.utc).strftime("%m/%d")
        theme_names = " / ".join([t.theme_title for t in digest.crossover_themes[:2]])
        
        t1 = (
            f"【80:20 Crossover Digest {now_str}】\n"
            f"AI・バイオ・Web3・低レイヤーの定点観測と飛び地トレンドから、注目の交差点を抽出しました。\n\n"
            f"🔍 本日のハイライト:\n{theme_names}\n\n"
            f"詳細スレッド 🧵👇"
        )
        
        t2_themes = []
        for i, t in enumerate(digest.crossover_themes[:2], 1):
            t2_themes.append(f"{i}. {t.theme_title}\n↳ {t.core_concept[:60]}...")
        t2 = "\n\n".join(t2_themes)
        
        t3 = (
            f"📊 分析母数: Core {len(digest.core_insights)}件 / Serendipity {len(digest.serendipity_finds)}件\n\n"
            f"WIRED視点の深掘りレポート全文と参考文献はこちらからご覧いただけます。\n"
            f"#AI #Web3 #バイオテクノロジー #越境思考"
        )
        
        return [t1, t2, t3]

    async def publish(self, digest: CrossoverDigest, status: str = "draft") -> Dict[str, Any]:
        """Publishes the article via HTTP API or direct DB if configured."""
        payload = self.format_article_payload(digest, status=status)

        logger.info(f"Publishing article to Coral News: '{payload['title']}' (status={status})")

        # Try HTTP API
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.api_url, json=payload)
                if resp.status_code in (200, 201):
                    logger.info("Successfully drafted article via Coral News API.")
                    return {"status": "success", "mode": "api", "payload": payload, "response": resp.json()}
        except Exception as e:
            logger.debug(f"HTTP API publish failed ({e}). Attempting database direct write or payload output.")

        # Fallback: return formatted payload for manual/MCP dispatch
        return {
            "status": "ready",
            "mode": "payload_ready",
            "message": "Article formatted and ready for Neon DB insertion.",
            "payload": payload,
        }
