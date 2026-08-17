import asyncio
import json
import re
from typing import List, Optional
from google import genai

from intelligence_hub.core.config import GEMINI_API_KEY, LLM_MODEL
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import CrossoverTheme, IntelligenceRecord
from intelligence_hub.analysis.prompts import CROSSOVER_ANALYSIS_PROMPT

logger = get_logger(__name__)

CATEGORY_TO_CORAL_THEME = {
    "ai_engineering": "テクノロジー",
    "synthetic_biology": "バイオ・ヘルスケア",
    "neuroscience": "バイオ・ヘルスケア",
    "medicine": "バイオ・ヘルスケア",
    "crypto": "テクノロジー",
    "reverse_engineering": "テクノロジー",
    "serendipity": "テクノロジー",
}


class CrossoverAnalyzer:
    """Discovers cross-domain intersections among diverse intelligence records."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or LLM_MODEL
        self.client = None
        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Gemini client initialization failed in CrossoverAnalyzer: {e}")

    async def analyze(self, records: List[IntelligenceRecord]) -> List[CrossoverTheme]:
        """Analyzes a collection of multi-domain records and extracts crossover themes."""
        if len(records) < 2:
            logger.info("Not enough records for crossover analysis (need >= 2).")
            return []

        # Format records text
        formatted_records = []
        for r in records[:30]:  # Limit to 30 to avoid token explosion
            formatted_records.append(
                f"- [ID: {r.id}] [{r.category}] {r.title}\n"
                f"  Source: {r.channel_name} | URL: {r.url}\n"
                f"  Summary: {r.summary[:300]}\n"
            )
        records_text = "\n".join(formatted_records)

        prompt = CROSSOVER_ANALYSIS_PROMPT.format(records_text=records_text)

        if not self.client:
            logger.warning("No Gemini API key available. Generating heuristic crossover.")
            return self._heuristic_crossover(records)

        try:
            logger.info("Running LLM crossover analysis...")
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
            )
            raw_text = response.text or ""
            return self._parse_json_crossover(raw_text, records)
        except Exception as e:
            logger.error(f"LLM Crossover analysis failed: {e}")
            return self._heuristic_crossover(records)

    def _parse_json_crossover(
        self, raw_text: str, records: List[IntelligenceRecord]
    ) -> List[CrossoverTheme]:
        # Extract JSON from markdown codeblock
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        json_str = match.group(1) if match else raw_text

        try:
            data = json.loads(json_str)
            themes_raw = data.get("crossover_themes", [])
            themes: List[CrossoverTheme] = []
            for t in themes_raw:
                domains = t.get("domains", [])
                coral_themes = list(
                    {CATEGORY_TO_CORAL_THEME.get(d, "テクノロジー") for d in domains}
                )
                if not coral_themes:
                    coral_themes = ["テクノロジー"]

                tags = list({d for d in domains} | {"Crossover", "80:20 Analysis"})
                t["suggested_themes"] = t.get("suggested_themes") or coral_themes
                t["suggested_tags"] = t.get("suggested_tags") or tags

                themes.append(CrossoverTheme(**t))
            return themes
        except Exception as e:
            logger.error(f"Failed to parse crossover JSON: {e}\nRaw: {raw_text[:200]}")
            return self._heuristic_crossover(records)

    def _heuristic_crossover(self, records: List[IntelligenceRecord]) -> List[CrossoverTheme]:
        """Fallback heuristic crossover when LLM is unavailable."""
        categories = list({r.category for r in records})
        if len(categories) < 2:
            return []

        c1, c2 = categories[0], categories[1]
        r1 = next(r for r in records if r.category == c1)
        r2 = next(r for r in records if r.category == c2)

        coral_themes = list(
            {CATEGORY_TO_CORAL_THEME.get(c1, "テクノロジー"), CATEGORY_TO_CORAL_THEME.get(c2, "テクノロジー")}
        )

        return [
            CrossoverTheme(
                theme_title=f"{c1.capitalize()} と {c2.capitalize()} の構造的アナロジー",
                domains=[c1, c2],
                core_concept="異分野間におけるモデリング・最適化アプローチの共通性",
                synergy_description=f"{r1.title} の手法と {r2.title} の問題領域における潜在的なシナジー。",
                actionable_implications=[
                    f"{c1} の最新手法を {c2} のパイプラインに適用可能か検証する",
                    "共通のデータ構造による統合ベンチマークの作成",
                ],
                referenced_record_ids=[r1.id, r2.id],
                suggested_themes=coral_themes,
                suggested_tags=[c1, c2, "Crossover"],
            )
        ]
