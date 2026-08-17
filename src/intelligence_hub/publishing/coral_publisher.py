"""Coral News Publisher for converting CrossoverDigests into WIRED-style long-form articles and drafting to Coral Magazine."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from google import genai

from intelligence_hub.core.config import GEMINI_API_KEY, LLM_MODEL
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import ArticlePayload, CrossoverDigest, CrossoverTheme
from intelligence_hub.analysis.prompts import CORAL_WIRED_ARTICLE_PROMPT

logger = get_logger(__name__)

DEFAULT_AUTHOR_ID = "a51cc056-5604-47d2-88ea-4647e4c46411"  # Naoya Kusunoki
DEFAULT_CORAL_API_URL = os.getenv("CORAL_API_URL", "http://127.0.0.1:3001/api/articles")
DEFAULT_CORAL_API_TOKEN = os.getenv(
    "CORAL_API_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJlbWFpbCI6ImFkbWluQGNvcmFsLmNvbSIsInJvbGUiOiJhZG1pbiIsImlhdCI6MTc4NjMzNzQ4NiwiZXhwIjoxODE3ODczNDg2LCJhdWQiOiJjb3JhbC1mcm9udGVuZCIsImlzcyI6ImNvcmFsLWJhY2tlbmQifQ.KxtBCDkpshKLGGiGc7fJRyeRifwIA6bzjZzVrQgulQg",
)


class CoralPublisher:
    """Publishes crossover intelligence digests to Coral Magazine (Neon DB / API) with WIRED long-form narrative standards."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        author_id: Optional[str] = None,
        database_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_url = api_url or DEFAULT_CORAL_API_URL
        self.api_token = api_token or DEFAULT_CORAL_API_TOKEN
        self.author_id = author_id or DEFAULT_AUTHOR_ID
        self.database_url = database_url or os.getenv("DATABASE_URL") or os.getenv("CORAL_DATABASE_URL")
        self.model_name = model_name or LLM_MODEL
        self.client = None
        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Gemini client init failed in CoralPublisher: {e}")

    async def format_article_payload(
        self, digest: CrossoverDigest, status: str = "draft"
    ) -> Dict[str, Any]:
        """Converts a CrossoverDigest into the full Coral Magazine article schema."""
        themes = digest.suggested_themes or ["テクノロジー"]
        tags = digest.suggested_tags or ["Crossover", "Intelligence", "80:20"]

        main_theme_title = digest.crossover_themes[0].theme_title if digest.crossover_themes else "越境する知性と計算パラダイム"
        # WIRED hook headline rule (concise, sharp, under 45 chars)
        title = f"境界線の融解：{main_theme_title}"
        if len(title) > 42:
            title = main_theme_title[:40]
        slug = f"crossover-digest-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Generate Excerpt (< 120 chars)
        excerpt = f"【80:20越境分析】{main_theme_title}。先端AI・バイオ・Web3・低レイヤーの衝突がもたらす新たな創発パラダイムを読み解く。"[:120]

        # Generate full WIRED-compliant HTML (via LLM or structured high-density fallback)
        content_html = await self._generate_wired_html(digest)
        reading_time = max(8, len(content_html) // 300)

        return {
            "title": title[:200],
            "slug": slug,
            "content": content_html,
            "excerpt": excerpt,
            "status": status,
            "themes": themes,
            "tags": tags,
            "reading_time": reading_time,
            "author_id": self.author_id,
        }

    async def _generate_wired_html(self, digest: CrossoverDigest) -> str:
        """Generates long-form WIRED narrative HTML using LLM or structured high-density fallback."""
        if self.client:
            try:
                logger.info("Generating long-form WIRED narrative HTML via LLM...")
                crossover_text = "\n".join(
                    [
                        f"- 【{t.theme_title}】 (領域: {', '.join(t.domains)})\n"
                        f"  中核概念: {t.core_concept}\n"
                        f"  シナジー: {t.synergy_description}\n"
                        f"  具体的示唆: {'; '.join(t.actionable_implications)}"
                        for t in digest.crossover_themes
                    ]
                )
                core_text = "\n".join(
                    [f"- [{r.get('category')}] {r.get('title')}: {r.get('summary', '')[:200]}" for r in digest.core_insights[:15]]
                )
                serendipity_text = "\n".join(
                    [f"- [{r.get('category')}] {r.get('title')}: {r.get('summary', '')[:200]}" for r in digest.serendipity_finds[:10]]
                )
                sources_text = "\n".join([f"- {url}" for url in digest.source_records[:20]])

                prompt = CORAL_WIRED_ARTICLE_PROMPT.format(
                    crossover_text=crossover_text,
                    core_text=core_text,
                    serendipity_text=serendipity_text,
                    sources_text=sources_text,
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                )
                raw_html = response.text or ""
                # Strip markdown code blocks if wrapped
                match = re.search(r"```(?:html)?\s*([\s\S]*?)\s*```", raw_html)
                if match:
                    raw_html = match.group(1).strip()
                if len(raw_html) > 500:
                    return raw_html
            except Exception as e:
                logger.warning(f"LLM WIRED article generation failed, using structured fallback: {e}")

        return self._structured_fallback_html(digest)

    def _structured_fallback_html(self, digest: CrossoverDigest) -> str:
        """Constructs a high-density, fully WIRED-compliant 3-part article without bare stubs."""
        main_theme = digest.crossover_themes[0] if digest.crossover_themes else None
        theme_title = main_theme.theme_title if main_theme else "計算知能と分散合意の越境"
        domains_str = " × ".join(main_theme.domains) if main_theme else "AI × 暗号プロトコル"

        # 1. Italic Scene-setting Lead
        lead_html = (
            '<p style="font-size: 1.15em; line-height: 1.8; color: #b0b0b0; font-style: italic;">\n'
            'サンフランシスコの片隅の研究所で、ある暗号理論家と機械学習エンジニアが同じホワイトボードを囲んでいた。'
            '一方は分散ネットワークにおけるゼロ知識検証のスケーラビリティに頭を抱え、もう一方は数千億パラメータを持つ言語モデルの分散推論検証に直面していた。'
            '互いに異なる専門用語で語り合いながらも、彼らが描いた計算グラフの幾何構造は、驚くほど完全に一致していた——。'
            '異なる専門領域のフロンティアが衝突するとき、予測不能なパラダイムシフトの火花が散る。\n'
            '</p>'
        )

        # 2. The Hook
        hook_body = (
            f'<h2>The Hook：{theme_title}が暴く「構造的共通項」</h2>\n'
            f'<p>\n'
            f'近年の情報幾何学と分散システム研究は、これまで独立して進化してきた分野の根底に共通する数理構造を浮き彫りにした。'
            f'本日の多層インテリジェンス・ハーベストでは、80%の定点観測コアデータ（先端AI、合成生物学、神経科学、暗号プロトコル、低レイヤー解析）と、'
            f'20%の飛び地セレンディピティデータから、<strong>{domains_str}</strong> の間に存在する明確なシナジーが観測された。\n'
            f'</p>\n'
            f'<p>\n'
            f'特に注目すべきは、{main_theme.core_concept if main_theme else "分散検証とモデル推論の融合"}だ。'
            f'単一の専門領域内での局所的最適化が限界に達しつつある現代において、異分野の手法をアナロジーとして借用する「越境アプローチ」こそが、'
            f'指数関数的なブレークスルーを生み出す原動力となっている。\n'
            f'</p>'
        )

        # 3. The Paradigm Shift (with Table and Deep Analysis)
        themes_detail_html = []
        for t in digest.crossover_themes:
            actions_li = "".join([f"<li><strong>実践的アプローチ:</strong> {a}</li>" for a in t.actionable_implications])
            themes_detail_html.append(
                f'<h3>{t.theme_title}</h3>\n'
                f'<p><strong>交差ドメイン:</strong> {", ".join(t.domains)}</p>\n'
                f'<p>{t.synergy_description}</p>\n'
                f'<ul>{actions_li}</ul>'
            )
        themes_section = "\n".join(themes_detail_html)

        table_html = (
            '<table style="width:100%; border-collapse: collapse; margin: 1.5rem 0; font-size: 0.95em;">\n'
            '<thead><tr style="background: #27272a; color: #fafafa; text-align: left;">\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">観測ドメイン</th>\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">従来の閉鎖的アプローチ</th>\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">越境による創発的パラダイム</th>\n'
            '</tr></thead><tbody>\n'
        )
        for t in digest.crossover_themes[:3]:
            d_str = " × ".join(t.domains)
            table_html += (
                f'<tr>\n'
                f'<td style="padding: 10px; border: 1px solid #3f3f46;"><strong>{d_str}</strong></td>\n'
                f'<td style="padding: 10px; border: 1px solid #3f3f46;">単一専門分野での計算資源投下・局所探索</td>\n'
                f'<td style="padding: 10px; border: 1px solid #3f3f46;">{t.core_concept}</td>\n'
                f'</tr>\n'
            )
        table_html += '</tbody></table>'

        shift_body = (
            f'<h2>The Paradigm Shift：既存構造の破綻と新たな創発</h2>\n'
            f'<p>\n'
            f'なぜ今、異分野の衝突が必要なのか。それは従来型の「巨大資本と計算資源の力任せのスケールアップ」が、'
            f'物理的・熱力学的・経済的な境界線に直面しているからに他ならない。\n'
            f'</p>\n'
            f'{table_html}\n'
            f'{themes_section}'
        )

        # 4. The Philosophical Horizon
        horizon_body = (
            '<h2>The Philosophical Horizon：10年後の知性と社会構造への問い</h2>\n'
            '<p>\n'
            'あらゆる計算プロトコルと生命科学の境界線が溶解した世界で、人間の知性の本質とは何だろうか？\n'
            '数理的なゼロ知識証明が真理の検証を担保し、生体模倣アルゴリズムが自律的に学習を継続する時代において、'
            '私たちが信じる「専門性」という概念そのものが解体されつつある。\n'
            '</p>\n'
            '<p>\n'
            '越境とは、単なる知識の足し算ではない。それは自らのドメインの「当たり前」を疑い、'
            '未知の他者との対話を通じて新たな認知フレームを獲得する行為だ。'
            'この地殻変動の先にある未来において、あなたはどのような新しい知性の形を描くだろうか？\n'
            '</p>'
        )

        # 5. References
        refs_li = []
        for url in digest.source_records[:20]:
            refs_li.append(f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a></li>')
        refs_section = f'<h2>参考文献・出典（References）</h2>\n<ul>\n{"".join(refs_li)}\n</ul>'

        return f"{lead_html}\n\n{hook_body}\n\n{shift_body}\n\n{horizon_body}\n\n{refs_section}"

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
            f"WIRED視点の長編深掘りレポート全文と参考文献はこちらからご覧いただけます。\n"
            f"#AI #Web3 #バイオテクノロジー #越境思考 #CoralMagazine"
        )

        return [t1, t2, t3]

    def generate_x_threads_for_tech(self, payload: ArticlePayload) -> List[str]:
        """Generates a 3-part technical thread for X (Twitter)."""
        clean_title = payload.title.replace("【急上昇OSS】", "").strip()

        t1 = (
            f"🔥【急上昇OSS解剖】{clean_title}\n\n"
            f"{payload.excerpt}\n\n"
            f"アーキテクチャ・使い方・比較スレッド 🧵👇"
        )

        t2 = (
            f"💡 主なポイント:\n"
            f"・高速化・省メモリの独自アーキテクチャ\n"
            f"・1コマンドで即時導入可能なクイックスタート\n"
            f"・既存ツールとの定量ベンチマーク比較"
        )

        t3 = (
            f"📖 詳細なコード例とアーキテクチャ解説はこちらからご覧いただけます。\n"
            f"#OSS #GitHub #開発トレンド #TechDeepDive #CoralMagazine"
        )

        return [t1, t2, t3]

    def generate_x_threads_for_paper(self, payload: ArticlePayload) -> List[str]:
        """Generates a 3-part academic paper thread for X (Twitter)."""
        clean_title = payload.title.replace("【最新論文解説】", "").strip()

        t1 = (
            f"🔬【先端論文速報】{clean_title}\n\n"
            f"{payload.excerpt}\n\n"
            f"先行研究の課題・提案手法・ベンチマークスレッド 🧵👇"
        )
        t2 = (
            f"📊 主要な貢献:\n"
            f"・既存モデルのボトルネックを打破する新規アルゴリズム\n"
            f"・定量ベンチマークにおける精度/効率の向上\n"
            f"・実世界応用への展望と課題"
        )
        t3 = (
            f"📄 詳細な実験比較テーブルと論文解説全文はこちら。\n"
            f"#arXiv #AI #サイエンス #論文解説 #CoralMagazine"
        )
        return [t1, t2, t3]

    def generate_x_threads_for_protocol(self, payload: ArticlePayload) -> List[str]:
        """Generates a 3-part protocol/security thread for X (Twitter)."""
        clean_title = payload.title.replace("【プロトコル解剖】", "").strip()

        t1 = (
            f"🛡️【プロトコル構造論】{clean_title}\n\n"
            f"{payload.excerpt}\n\n"
            f"暗号学的仕組み・脅威モデル・攻撃耐性スレッド 🧵👇"
        )
        t2 = (
            f"🔐 検証ポイント:\n"
            f"・分散合意 / ゼロ知識証明によるステート検証\n"
            f"・MEV / Reentrancy / DoS 攻撃耐性の数理的保証\n"
            f"・EIP / 実装リファレンスの構造"
        )
        t3 = (
            f"🔍 脅威モデル比較表とプロトコル仕様の全文はこちら。\n"
            f"#Web3 #Security #Crypto #低レイヤー #CoralMagazine"
        )
        return [t1, t2, t3]

    async def publish_payload(self, payload: ArticlePayload) -> Dict[str, Any]:
        """Publishes an ArticlePayload directly to Coral Magazine API."""
        payload_dict = payload.model_dump()
        logger.info(f"Publishing article to Coral News: '{payload.title}' (genre={payload.genre})")

        try:
            headers = {"Content-Type": "application/json"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.api_url, json=payload_dict, headers=headers)
                if resp.status_code in (200, 201):
                    logger.info("Successfully published article via Coral News API.")
                    return {"status": "success", "mode": "api", "payload": payload_dict, "response": resp.json()}
        except Exception as e:
            logger.debug(f"HTTP API publish failed ({e}). Returning ready payload.")

        return {
            "status": "ready",
            "mode": "payload_ready",
            "message": "Article formatted and ready for Neon DB insertion.",
            "payload": payload_dict,
        }

    async def publish(self, digest: CrossoverDigest, status: str = "draft") -> Dict[str, Any]:
        """Publishes the crossover article via HTTP API or direct DB if configured."""
        payload_dict = await self.format_article_payload(digest, status=status)
        payload = ArticlePayload(**payload_dict, genre="crossover_feature")
        return await self.publish_payload(payload)
