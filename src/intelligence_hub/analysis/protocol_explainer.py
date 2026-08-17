"""Protocol Explainer engine for generating deep Web3 protocol and low-level security articles."""

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
from intelligence_hub.analysis.prompts import PROTOCOL_SECURITY_PROMPT

logger = get_logger(__name__)

DEFAULT_AUTHOR_ID = "a51cc056-5604-47d2-88ea-4647e4c46411"  # Naoya Kusunoki


class ProtocolExplainer:
    """Generates rigorous protocol architecture and security analysis articles."""

    def __init__(self, model_name: Optional[str] = None, author_id: Optional[str] = None):
        self.model_name = model_name or LLM_MODEL
        self.author_id = author_id or DEFAULT_AUTHOR_ID
        self.client = None
        if GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Gemini client init failed in ProtocolExplainer: {e}")

    async def explain(
        self, record: IntelligenceRecord, status: str = "draft"
    ) -> ArticlePayload:
        """Generates a complete protocol security article from an IntelligenceRecord."""
        clean_title = record.title.split(":")[0].strip()

        title = f"【プロトコル解剖】{clean_title} の構造と攻撃耐性"
        if len(title) > 42:
            title = f"【プロトコル】{clean_title}"[:40]

        slug = f"protocol-sec-{record.id.replace('_', '-')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        excerpt = f"【プロトコル・セキュリティ構造論】{record.title[:60]}。設計思想、暗号学的検証モデル、脅威ベクトルと耐性を徹底解剖。"[:120]

        content_html = await self._generate_html(record)
        reading_time = max(8, len(content_html) // 300)

        tags = list(set(["Security", "Protocol", "Crypto", "Architecture", record.category] + record.tags))

        return ArticlePayload(
            title=title,
            slug=slug,
            content=content_html,
            excerpt=excerpt,
            status=status,
            genre="protocol_security",
            themes=["テクノロジー"],
            tags=tags[:8],
            reading_time=reading_time,
            author_id=self.author_id,
        )

    async def _generate_html(self, record: IntelligenceRecord) -> str:
        """Generates the protocol security HTML using LLM or structured architectural fallback."""
        details = record.raw_content or record.summary or "Details not available"
        author = record.author or "Protocol Architect"

        if self.client:
            try:
                logger.info(f"Generating Protocol Security Analysis for {record.title} via LLM...")
                prompt = PROTOCOL_SECURITY_PROMPT.format(
                    title=record.title,
                    category=record.category,
                    author=author,
                    url=record.url,
                    details=details[:3000],
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
                if len(raw_html) > 500:
                    return raw_html
            except Exception as e:
                logger.warning(f"LLM Protocol Security generation failed, using fallback: {e}")

        return self._structured_fallback_html(record, details, author)

    def _structured_fallback_html(
        self, record: IntelligenceRecord, details: str, author: str
    ) -> str:
        """Constructs a high-density protocol security article with threat model."""
        clean_title = record.title.split(":")[0].strip()

        overview_block = (
            '<div style="background: #1e293b; padding: 1.2rem; border-left: 4px solid #f59e0b; border-radius: 4px; margin-bottom: 1.8rem;">\n'
            f'<p style="margin: 0; font-weight: bold; color: #f59e0b; font-size: 1.1em;">🛡️ プロトコル概要（Protocol Overview）</p>\n'
            f'<p style="margin: 0.5rem 0 0 0; color: #e2e8f0; line-height: 1.6;">\n'
            f'<strong>{clean_title}</strong> は、分散ネットワークおよび低レイヤーシステムにおける安全性と検証可能性を担保するプロトコル設計です。'
            f'単一障害点（SPOF）の排除とゼロ知識暗号/ステート検証機構を組み合わせ、高スループット環境下での耐改ざん性を実現します。\n'
            f'</p>\n'
            '</div>'
        )

        motivation_section = (
            '<h2>1. 背景と設計動機（Motivation & Context）</h2>\n'
            '<p>\n'
            '分散台帳および低レイヤー実行環境において、既存の合意・検証プロトコルは以下の限界に直面していました：\n'
            '</p>\n'
            '<ul>\n'
            '<li><strong>検証コストとスケーラビリティの二律背反:</strong> フルノードの検証負荷が増大し、ネットワークの分散性が損なわれる。</li>\n'
            '<li><strong>非同期通信環境下でのフォールトトレランス:</strong> ビザンチン障害やネットワーク分断時におけるファイナリティ遅延。</li>\n'
            '</ul>\n'
            f'<p>\n'
            f'{clean_title} は、検証ロジックを数理的に圧縮することで、これらの課題に対する抜本的な解を提供します。\n'
            f'</p>'
        )

        architecture_section = (
            '<h2>2. 技術アーキテクチャと暗号学的仕組み（Technical Architecture）</h2>\n'
            '<p>\n'
            '本プロトコルは、ステート遷移の完全性をゼロ知識証明または暗号学的ハッシュチェーンによって保証します。\n'
            '</p>\n'
            f'<div style="background: #0f172a; padding: 1rem; border-radius: 6px; margin: 1rem 0; font-family: monospace; font-size: 0.9em; color: #94a3b8;">\n'
            f'{details[:800].replace("<", "&lt;").replace(">", "&gt;")}\n'
            f'</div>'
        )

        threat_section = (
            '<h2>3. 脅威モデルと攻撃耐性（Threat Model & Security）</h2>\n'
            '<p>想定される攻撃ベクトルとプロトコルレベルの防御策：</p>\n'
            '<table style="width:100%; border-collapse: collapse; margin: 1.5rem 0; font-size: 0.95em;">\n'
            '<thead><tr style="background: #27272a; color: #fafafa; text-align: left;">\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">攻撃ベクトル</th>\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">潜在的影響</th>\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">プロトコルの防御機構</th>\n'
            '</tr></thead><tbody>\n'
            '<tr><td style="padding: 10px; border: 1px solid #3f3f46;"><strong>MEV / トランザクション順序操作</strong></td><td style="padding: 10px; border: 1px solid #3f3f46;">経済的搾取・フロントランニング</td><td style="padding: 10px; border: 1px solid #3f3f46;">閾値暗号による暗号化メンプール</td></tr>\n'
            '<tr><td style="padding: 10px; border: 1px solid #3f3f46;"><strong>51% 攻撃 / リオルグ</strong></td><td style="padding: 10px; border: 1px solid #3f3f46;">二重支払い・ステート巻き戻し</td><td style="padding: 10px; border: 1px solid #3f3f46;">スラッシングを伴うプルーフ・オブ・ステーク合意</td></tr>\n'
            '<tr><td style="padding: 10px; border: 1px solid #3f3f46;"><strong>DoS / メモリ枯渇攻撃</strong></td><td style="padding: 10px; border: 1px solid #3f3f46;">ノード停止・検証遅延</td><td style="padding: 10px; border: 1px solid #3f3f46;">厳格なガスMeteringとリソース境界制限</td></tr>\n'
            '</tbody></table>'
        )

        reference_section = (
            '<h2>4. 仕様・実装リファレンス</h2>\n'
            '<ul>\n'
            f'<li>Primary Source: <a href="{record.url}" target="_blank" rel="noopener noreferrer">{record.url}</a></li>\n'
            f'<li>Author / Source: {author}</li>\n'
            '</ul>'
        )

        return f"{overview_block}\n\n{motivation_section}\n\n{architecture_section}\n\n{threat_section}\n\n{reference_section}"
