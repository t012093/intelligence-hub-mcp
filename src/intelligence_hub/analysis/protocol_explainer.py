"""Protocol Explainer engine for generating deep Web3 protocol and security articles with EIP specs and threat models."""

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
from intelligence_hub.intake.protocol_spec_fetcher import ProtocolSpecFetcher
from intelligence_hub.analysis.prompts import PROTOCOL_SECURITY_PROMPT

logger = get_logger(__name__)

DEFAULT_AUTHOR_ID = "a51cc056-5604-47d2-88ea-4647e4c46411"  # Naoya Kusunoki


class ProtocolExplainer:
    """Generates rigorous protocol architecture and security analysis articles integrated with EIP specs."""

    def __init__(self, model_name: Optional[str] = None, author_id: Optional[str] = None):
        self.model_name = model_name or LLM_MODEL
        self.author_id = author_id or DEFAULT_AUTHOR_ID
        self.spec_fetcher = ProtocolSpecFetcher()
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

        # 1. Resolve Protocol Specs & Threat Cases
        spec_meta = await self.spec_fetcher.resolve_protocol_specs(record.title or record.url)

        title = f"【プロトコル解剖】{clean_title} の構造と攻撃耐性"
        if len(title) > 42:
            title = f"【プロトコル】{clean_title}"[:40]

        slug = f"protocol-sec-{record.id.replace('_', '-')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        excerpt = f"【プロトコル・セキュリティ構造論】{clean_title}。EIP仕様・暗号学的検証モデル・過去のハッキング脆弱性事例と防御策を徹底解剖。"[:120]

        content_html = await self._generate_html(record, spec_meta)
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

    async def _generate_html(
        self, record: IntelligenceRecord, spec_meta: Dict[str, Any]
    ) -> str:
        """Generates the protocol security HTML using LLM or structured architectural fallback."""
        details = spec_meta.get("specification_raw") or record.raw_content or record.summary or "Details not available"
        author = record.author or "Protocol Architect"

        if self.client:
            try:
                logger.info(f"Generating Protocol Security Analysis for {record.title} via LLM...")
                prompt = (
                    f"{PROTOCOL_SECURITY_PROMPT}\n\n"
                    f"【仕様・セキュリティメタデータ】\n"
                    f"・EIP番号/仕様: {spec_meta.get('eip_number', 'General Protocol')}\n"
                    f"・標準化ステータス: {spec_meta.get('status', 'Active')}\n"
                    f"・暗号プリミティブ: {', '.join(spec_meta.get('crypto_primitives', []))}\n"
                ).format(
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

        return self._structured_fallback_html(record, spec_meta, details, author)

    def _structured_fallback_html(
        self,
        record: IntelligenceRecord,
        spec_meta: Dict[str, Any],
        details: str,
        author: str,
    ) -> str:
        """Constructs a high-density protocol security article with EIP spec card and threat model."""
        clean_title = record.title.split(":")[0].strip()
        eip_num = spec_meta.get("eip_number") or "標準アーキテクチャ"
        status = spec_meta.get("status") or "Active"
        primitives = ", ".join(spec_meta.get("crypto_primitives") or ["BLS12-381", "Poseidon Hash"])

        # 1. Protocol Metadata Card
        spec_card = (
            '<div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem;">\n'
            '<h3 style="margin-top: 0; color: #f59e0b; font-size: 1.15em;">🔐 プロトコル仕様・標準化データ（Protocol Spec Card）</h3>\n'
            '<ul style="list-style: none; padding-left: 0; margin: 0.5rem 0; line-height: 1.8; color: #cbd5e1; font-size: 0.95em;">\n'
            f'<li><strong>仕様規格 / EIP番号:</strong> {eip_num}</li>\n'
            f'<li><strong>標準化ステータス:</strong> {status}</li>\n'
            f'<li><strong>中核暗号プリミティブ:</strong> <code>{primitives}</code></li>\n'
            f'<li><strong>公式リファレンス:</strong> <a href="{record.url}" target="_blank" rel="noopener noreferrer" style="color: #f59e0b;">{record.url}</a></li>\n'
            '</ul>\n'
            '</div>'
        )

        # 2. Executive Overview
        overview_block = (
            '<div style="background: #1e293b; padding: 1.2rem; border-left: 4px solid #f59e0b; border-radius: 4px; margin-bottom: 1.8rem;">\n'
            f'<p style="margin: 0; font-weight: bold; color: #f59e0b; font-size: 1.1em;">🛡️ プロトコル概要（Protocol Overview）</p>\n'
            f'<p style="margin: 0.5rem 0 0 0; color: #e2e8f0; line-height: 1.6;">\n'
            f'<strong>{clean_title}</strong> は、分散ネットワークおよび低レイヤー実行環境におけるステート遷移の完全性と検証可能性を担保するプロトコル設計です。'
            f'ゼロ知識暗号回路とステートハッシュ検証を組み合わせ、MEVや再入攻撃に対する数理的耐性を実現します。\n'
            f'</p>\n'
            '</div>'
        )

        # 3. Motivation & Context
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

        # 4. Technical Architecture
        architecture_section = (
            '<h2>2. 技術アーキテクチャと暗号学的仕組み（Technical Architecture）</h2>\n'
            '<p>\n'
            '本プロトコルは、ステート遷移の完全性をゼロ知識証明または暗号学的ハッシュチェーンによって保証します。\n'
            '</p>\n'
            f'<div style="background: #0f172a; padding: 1.2rem; border-radius: 6px; margin: 1rem 0; font-family: monospace; font-size: 0.9em; color: #94a3b8; line-height: 1.6;">\n'
            f'{details[:900].replace("<", "&lt;").replace(">", "&gt;")}\n'
            f'</div>'
        )

        # 5. Exploit Cases & Threat Model Comparison Table
        exploit_rows = ""
        for case in spec_meta.get("exploit_cases", []):
            exploit_rows += (
                f'<tr>\n'
                f'<td style="padding: 10px; border: 1px solid #3f3f46;"><strong>{case.get("vector")}</strong></td>\n'
                f'<td style="padding: 10px; border: 1px solid #3f3f46; color: #f87171;">{case.get("historical_case")}</td>\n'
                f'<td style="padding: 10px; border: 1px solid #3f3f46; color: #10b981;">{case.get("mitigation")}</td>\n'
                f'</tr>\n'
            )

        threat_section = (
            '<h2>3. 過去のハッキング・脆弱性事例（Exploit Cases）とプロトコル防御策</h2>\n'
            '<p>歴史的な攻撃事例に基づく脅威モデルと、本プロトコルにおける数理的防御機構：</p>\n'
            '<table style="width:100%; border-collapse: collapse; margin: 1.5rem 0; font-size: 0.95em;">\n'
            '<thead><tr style="background: #27272a; color: #fafafa; text-align: left;">\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">攻撃ベクトル</th>\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">過去の代表的被害事例</th>\n'
            '<th style="padding: 10px; border: 1px solid #3f3f46;">本プロトコルによる防御機構</th>\n'
            '</tr></thead><tbody>\n'
            f'{exploit_rows}\n'
            '</tbody></table>'
        )

        # 6. References
        reference_section = (
            '<h2>4. 仕様・実装リファレンス</h2>\n'
            '<ul>\n'
            f'<li>Primary Source: <a href="{record.url}" target="_blank" rel="noopener noreferrer">{record.url}</a></li>\n'
            f'<li>Specification Standard: {eip_num} ({status})</li>\n'
            f'<li>Author / Researcher: {author}</li>\n'
            '</ul>'
        )

        return f"{spec_card}\n\n{overview_block}\n\n{motivation_section}\n\n{architecture_section}\n\n{threat_section}\n\n{reference_section}"
