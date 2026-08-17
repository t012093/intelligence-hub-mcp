import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from google import genai

from intelligence_hub.core.config import GEMINI_API_KEY, LLM_MODEL
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import CrossoverDigest, CrossoverTheme, IntelligenceRecord
from intelligence_hub.analysis.crossover import CrossoverAnalyzer
from intelligence_hub.analysis.prompts import WIRED_DIGEST_REPORT_PROMPT

logger = get_logger(__name__)


class IntelligenceSynthesizer:
    """Synthesizes core (80%), serendipity (20%) and crossover themes into a cohesive publication."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or LLM_MODEL
        self.analyzer = CrossoverAnalyzer(model_name=self.model_name)
        self.client = None
        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to init Gemini client in Synthesizer: {e}")

    async def synthesize(
        self,
        core_records: List[IntelligenceRecord],
        serendipity_records: List[IntelligenceRecord],
        period: str = "daily",
    ) -> CrossoverDigest:
        """Runs the full synthesis pipeline."""
        all_records = core_records + serendipity_records
        digest_id = f"digest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        logger.info(
            f"Starting synthesis for {len(core_records)} core and "
            f"{len(serendipity_records)} serendipity records"
        )

        # Step 1: Run crossover analysis
        crossover_themes = await self.analyzer.analyze(all_records)

        # Step 2: Generate Markdown Report
        markdown_report = await self._generate_report(
            core_records=core_records,
            serendipity_records=serendipity_records,
            crossover_themes=crossover_themes,
            period=period,
        )

        # Aggregate suggested themes and tags across crossover themes
        all_suggested_themes = list(
            {th for t in crossover_themes for th in t.suggested_themes}
        ) or ["テクノロジー"]
        all_suggested_tags = list(
            {tg for t in crossover_themes for tg in t.suggested_tags}
            | {r.category for r in all_records}
        )

        return CrossoverDigest(
            digest_id=digest_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            period=period,
            core_insights=[
                {"id": r.id, "title": r.title, "category": r.category, "url": r.url}
                for r in core_records[:15]
            ],
            serendipity_finds=[
                {"id": r.id, "title": r.title, "channel": r.channel_name, "url": r.url}
                for r in serendipity_records[:5]
            ],
            crossover_themes=crossover_themes,
            markdown_report=markdown_report,
            suggested_themes=all_suggested_themes,
            suggested_tags=all_suggested_tags,
            source_records=[r.id for r in all_records],
        )

    async def _generate_report(
        self,
        core_records: List[IntelligenceRecord],
        serendipity_records: List[IntelligenceRecord],
        crossover_themes: List[CrossoverTheme],
        period: str,
    ) -> str:
        core_text = "\n".join(
            [f"- [{r.category}] **{r.title}** ({r.url})\n  {r.summary[:200]}" for r in core_records[:15]]
        )
        serendipity_text = "\n".join(
            [f"- [{r.channel_name}] **{r.title}** ({r.url})\n  {r.summary[:200]}" for r in serendipity_records[:5]]
        )
        crossover_text = "\n".join(
            [
                f"### {t.theme_title} ({', '.join(t.domains)})\n"
                f"- **Core Concept**: {t.core_concept}\n"
                f"- **Synergy**: {t.synergy_description}\n"
                f"- **Actions**: {'; '.join(t.actionable_implications)}"
                for t in crossover_themes
            ]
        )

        prompt = WIRED_DIGEST_REPORT_PROMPT.format(
            core_text=core_text or "No core records",
            serendipity_text=serendipity_text or "No serendipity records",
            crossover_text=crossover_text or "No crossover themes identified",
        )

        if not self.client:
            return self._fallback_markdown(core_records, serendipity_records, crossover_themes, period)

        try:
            logger.info("Generating WIRED-style narrative digest with LLM...")
            res = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
            )
            return res.text or self._fallback_markdown(
                core_records, serendipity_records, crossover_themes, period
            )
        except Exception as e:
            logger.error(f"Error generating narrative report: {e}")
            return self._fallback_markdown(
                core_records, serendipity_records, crossover_themes, period
            )

    def _fallback_markdown(
        self,
        core_records: List[IntelligenceRecord],
        serendipity_records: List[IntelligenceRecord],
        crossover_themes: List[CrossoverTheme],
        period: str,
    ) -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = [
            f"# 🌐 Multi-Domain Intelligence Digest ({date_str})",
            "",
            "> 80:20 パレート分析 & 異分野交差点インテリジェンスレポート",
            "",
            "## 1. 異分野の交差点（Crossover Themes）",
        ]

        if not crossover_themes:
            lines.append("※現在検出された交差点はありません。")
        else:
            for t in crossover_themes:
                lines.extend(
                    [
                        f"### 🔬 {t.theme_title}",
                        f"- **対象領域**: `{', '.join(t.domains)}`",
                        f"- **中核概念**: {t.core_concept}",
                        f"- **シナジー**: {t.synergy_description}",
                        "- **アクション・応用可能性**:",
                    ]
                )
                for act in t.actionable_implications:
                    lines.append(f"  - {act}")
                lines.append("")

        lines.extend(["## 2. コアドメイン定点分析 (Core 80%)", ""])
        for r in core_records[:10]:
            lines.append(f"- **[{r.category}] [{r.title}]({r.url})**")
            lines.append(f"  - 出典: {r.channel_name} | {r.summary[:150]}...")

        lines.extend(["", "## 3. 今週のセレンディピティ (Serendipity 20%)", ""])
        for r in serendipity_records[:5]:
            lines.append(f"- **[{r.channel_name}] [{r.title}]({r.url})**")
            lines.append(f"  - {r.summary[:150]}...")

        lines.extend(["", "---", "### 📚 出典・リファレンス一覧"])
        for r in (core_records + serendipity_records)[:20]:
            lines.append(f"- [{r.title}]({r.url}) ({r.channel_name})")

        return "\n".join(lines)
