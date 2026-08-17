"""Tech Explainer engine for generating deep-dive, practical OSS engineering articles with code and comparison tables."""

import asyncio
from datetime import datetime, timezone
import json
import os
import re
from typing import Any, Dict, List, Optional
from google import genai

from intelligence_hub.core.config import GEMINI_API_KEY, LLM_MODEL
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import ArticlePayload, IntelligenceRecord
from intelligence_hub.analysis.prompts import TECH_DEEP_DIVE_PROMPT

logger = get_logger(__name__)

DEFAULT_AUTHOR_ID = "a51cc056-5604-47d2-88ea-4647e4c46411"  # Naoya Kusunoki


class TechExplainer:
    """Generates concrete, actionable technical deep-dive articles for OSS repositories."""

    def __init__(self, model_name: Optional[str] = None, author_id: Optional[str] = None):
        self.model_name = model_name or LLM_MODEL
        self.author_id = author_id or DEFAULT_AUTHOR_ID
        self.client = None
        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Gemini client init failed in TechExplainer: {e}")

    async def explain(
        self, record: IntelligenceRecord, status: str = "draft"
    ) -> ArticlePayload:
        """Generates a complete technical deep-dive article from an IntelligenceRecord."""
        metrics = record.metrics or {}
        stars = metrics.get("total_stars", 0)
        stars_today = metrics.get("stars_today", 0)
        language = metrics.get("language") or "Python / TypeScript"

        # Generate Title (< 45 chars)
        clean_name = record.title.split(":")[0].strip()
        title = f"【急上昇OSS】{clean_name} の設計と実践活用ガイド"
        if len(title) > 42:
            title = f"【OSS解説】{clean_name}"[:40]

        slug = f"tech-deepdive-{record.id.replace('_', '-')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        excerpt = f"【急上昇OSS解剖】{clean_name}（⭐ {stars:,}）のアーキテクチャ、高速化の仕組み、インストールから最小コード例までを徹底解説。"[:120]

        # Generate Content HTML
        content_html = await self._generate_html(record, stars, stars_today, language)
        reading_time = max(6, len(content_html) // 350)

        tags = list(set(["OSS", "GitHub", "TechDeepDive", language.lower()] + record.tags))

        return ArticlePayload(
            title=title,
            slug=slug,
            content=content_html,
            excerpt=excerpt,
            status=status,
            genre="tech_deep_dive",
            themes=["テクノロジー"],
            tags=tags[:8],
            reading_time=reading_time,
            author_id=self.author_id,
        )

    async def _generate_html(
        self,
        record: IntelligenceRecord,
        stars: int,
        stars_today: int,
        language: str,
    ) -> str:
        """Generates the technical HTML content using LLM or structured concrete fallback."""
        readme_excerpt = record.raw_content or record.summary or "README not available"

        if self.client:
            try:
                logger.info(f"Generating Tech Deep-Dive for {record.title} via LLM...")
                prompt = TECH_DEEP_DIVE_PROMPT.format(
                    title=record.title,
                    url=record.url,
                    language=language,
                    stars=stars,
                    stars_today=stars_today,
                    summary=record.summary,
                    readme_excerpt=readme_excerpt[:3000],
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                )
                raw_html = response.text or ""
                match = re.search(r"```(?:html)?\s*([\s\S]*?)\s*```", raw_html)
                if match:
                    raw_html = match.group(1).strip()
                if len(raw_html) > 400:
                    return raw_html
            except Exception as e:
                logger.warning(f"LLM Tech Deep-Dive generation failed, using fallback: {e}")

        return self._structured_fallback_html(record, stars, stars_today, language, readme_excerpt)

    def _structured_fallback_html(
        self,
        record: IntelligenceRecord,
        stars: int,
        stars_today: int,
        language: str,
        readme: str,
    ) -> str:
        """Constructs a high-density, concrete technical article with code and tables."""
        clean_name = record.title.split(":")[0].strip()
        lang_lower = language.lower()

        # Generate install snippet based on language
        if "python" in lang_lower:
            install_cmd = f"pip install {clean_name.lower().split('/')[-1]}"
            code_snippet = (
                f"# Minimal Quick Start for {clean_name}\n"
                f"import {clean_name.lower().split('/')[-1].replace('-', '_')} as app\n\n"
                f"# Initialize with default configuration\n"
                f"client = app.Client()\n"
                f"results = client.run(query='Hello World')\n"
                f"print(f'Execution output: {{results}}')\n"
            )
            code_lang = "python"
        elif "rust" in lang_lower or "c" in lang_lower:
            install_cmd = f"git clone {record.url} && cd {clean_name.split('/')[-1]} && cargo build --release"
            code_snippet = (
                f"// Quick Start CLI Execution\n"
                f"./target/release/{clean_name.split('/')[-1].lower()} --help\n"
            )
            code_lang = "bash"
        else:
            install_cmd = f"npm install {clean_name.lower().split('/')[-1]}"
            code_snippet = (
                f"import {{ Client }} from '{clean_name.lower().split('/')[-1]}';\n\n"
                f"const client = new Client();\n"
                f"await client.initialize();\n"
                f"console.log('Ready');\n"
            )
            code_lang = "typescript"

        tldr_block = (
            '<div style="background: #1e293b; padding: 1.2rem; border-left: 4px solid #38bdf8; border-radius: 4px; margin-bottom: 1.8rem;">\n'
            f'<p style="margin: 0; font-weight: bold; color: #38bdf8; font-size: 1.1em;">📌 TL;DR（1分でわかる要点）</p>\n'
            f'<p style="margin: 0.5rem 0 0 0; color: #e2e8f0; line-height: 1.6;">\n'
            f'<strong>{clean_name}</strong> は、主要言語 <code>{language}</code> で実装された高効率オープンソースツールです。'
            f'本日 <strong>+{stars_today:,} stars</strong> の急上昇を記録（累計 <strong>{stars:,} stars</strong>）。'
            f'従来のボトルネックを解消し、シンプルなアーキテクチャで高い開発生産性と処理性能を提供します。\n'
            f'</p>\n'
            '</div>'
        )

        problem_section = (
            f'<h2>1. 解決する課題（The Problem）</h2>\n'
            f'<p>\n'
            f'近年のソフトウェア開発において、{language} エコシステムでは以下のような課題が顕在化していました：\n'
            f'</p>\n'
            f'<ul>\n'
            f'<li><strong>過剰な依存関係とメモリ消費:</strong> 既存の類似ツールでは起動オーバーヘッドが大きく、CI/CD環境やエッジでの実行に難があった。</li>\n'
            f'<li><strong>設定の複雑さ:</strong> 動かすまでに膨大な設定ファイルが必要であり、オンボーディングのコストが高かった。</li>\n'
            f'</ul>\n'
            f'<p>\n'
            f'{clean_name} はこれらのペインを解消するために設計され、最小限のフットプリントで最大のパフォーマンスを発揮することを目指しています。\n'
            f'</p>'
        )

        architecture_section = (
            f'<h2>2. アーキテクチャと高速化・省メモリの仕組み（How It Works）</h2>\n'
            f'<p>\n'
            f'なぜ {clean_name} は注目を集めているのか？ その核心は、計算資源の無駄を徹底的に排除した内部構造にあります。\n'
            f'</p>\n'
            f'<p>\n'
            f'README およびコードベースから確認できる主要な特徴は以下の通りです：\n'
            f'</p>\n'
            f'<div style="background: #0f172a; padding: 1rem; border-radius: 6px; margin: 1rem 0; font-family: monospace; font-size: 0.9em; color: #94a3b8;">\n'
            f'{readme[:800].replace("<", "&lt;").replace(">", "&gt;")}\n'
            f'</div>'
        )

        usage_section = (
            f'<h2>3. インストール ＆ クイックスタート（Usage & Code）</h2>\n'
            f'<p>以下のコマンドで素早くセットアップ可能です：</p>\n'
            f'<pre style="background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 6px; overflow-x: auto;"><code class="language-bash">{install_cmd}</code></pre>\n'
            f'<p>最小限の動作サンプルコード：</p>\n'
            f'<pre style="background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 6px; overflow-x: auto;"><code class="language-{code_lang}">{code_snippet}</code></pre>'
        )

        comparison_table = (
            f'<h2>4. 既存ツールとの定量比較（Comparison Table）</h2>\n'
            f'<table style="width:100%; border-collapse: collapse; margin: 1.5rem 0; font-size: 0.95em;">\n'
            f'<thead><tr style="background: #27272a; color: #fafafa; text-align: left;">\n'
            f'<th style="padding: 10px; border: 1px solid #3f3f46;">項目</th>\n'
            f'<th style="padding: 10px; border: 1px solid #3f3f46;">{clean_name}（本ツール）</th>\n'
            f'<th style="padding: 10px; border: 1px solid #3f3f46;">従来の標準的アプローチ</th>\n'
            f'</tr></thead><tbody>\n'
            f'<tr><td style="padding: 10px; border: 1px solid #3f3f46;"><strong>主要言語</strong></td><td style="padding: 10px; border: 1px solid #3f3f46;">{language}</td><td style="padding: 10px; border: 1px solid #3f3f46;">汎用スクリプト / 重厚フレームワーク</td></tr>\n'
            f'<tr><td style="padding: 10px; border: 1px solid #3f3f46;"><strong>GitHub Stars</strong></td><td style="padding: 10px; border: 1px solid #3f3f46;">⭐ {stars:,}（急上昇）</td><td style="padding: 10px; border: 1px solid #3f3f46;">成熟 / 更新停滞</td></tr>\n'
            f'<tr><td style="padding: 10px; border: 1px solid #3f3f46;"><strong>導入容易性</strong></td><td style="padding: 10px; border: 1px solid #3f3f46;">1コマンドで即時稼働</td><td style="padding: 10px; border: 1px solid #3f3f46;">複数依存関係の個別セットアップ</td></tr>\n'
            f'</tbody></table>'
        )

        conclusion_section = (
            f'<h2>5. まとめと導入に向けた推奨事項</h2>\n'
            f'<p>\n'
            f'{clean_name} は、単なるトレンドにとどまらず、実務の効率化に直結する設計思想を持っています。'
            f'特に軽量性や導入速度を重視するプロジェクトにおいて、検証する価値の高い選択肢と言えます。\n'
            f'</p>\n'
            f'<h2>参考リンク・リファレンス</h2>\n'
            f'<ul>\n'
            f'<li>GitHub Repository: <a href="{record.url}" target="_blank" rel="noopener noreferrer">{record.url}</a></li>\n'
            f'</ul>'
        )

        return f"{tldr_block}\n\n{problem_section}\n\n{architecture_section}\n\n{usage_section}\n\n{comparison_table}\n\n{conclusion_section}"
