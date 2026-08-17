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

CATEGORY_JA_LABELS = {
    "ai_engineering": "自律型AI・計算知能",
    "synthetic_biology": "合成生物学・遺伝子回路",
    "neuroscience": "脳神経科学・シナプス工学",
    "medicine": "先端分子医療",
    "crypto": "分散暗号プロトコル",
    "reverse_engineering": "低レイヤーバイナリ解析",
    "serendipity": "創発的オープンソース",
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

        ja1 = CATEGORY_JA_LABELS.get(c1, c1)
        ja2 = CATEGORY_JA_LABELS.get(c2, c2)

        coral_themes = list(
            {CATEGORY_TO_CORAL_THEME.get(c1, "テクノロジー"), CATEGORY_TO_CORAL_THEME.get(c2, "テクノロジー")}
        )

        theme_title = f"{ja1} と {ja2} の幾何学的共鳴"
        core_concept = f"異分野間（{ja1} × {ja2}）におけるモデリング・最適化アプローチの構造的同型性"

        return [
            CrossoverTheme(
                theme_title=theme_title,
                domains=[c1, c2],
                core_concept=core_concept,
                synergy_description=f"「{r1.title[:50]}」の数理的アプローチと「{r2.title[:50]}」の課題領域が交差することで生じる創発的パラダイム。",
                actionable_implications=[
                    f"{ja1} の最新アルゴリズムを {ja2} の処理パイプラインへ転用・検証する",
                    "共通のデータ表現構造に基づく統合ベンチマークの策定",
                ],
                referenced_record_ids=[r1.id, r2.id],
                suggested_themes=coral_themes,
                suggested_tags=[c1, c2, "Crossover", "80:20 Analysis"],
            )
        ]
