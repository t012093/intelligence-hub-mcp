"""Unit tests for ProtocolSpecFetcher and rich ProtocolExplainer."""

import pytest
from intelligence_hub.core.models import IntelligenceRecord
from intelligence_hub.intake.protocol_spec_fetcher import ProtocolSpecFetcher
from intelligence_hub.analysis.protocol_explainer import ProtocolExplainer
from intelligence_hub.analysis.quality_gate import QualityGate


@pytest.mark.asyncio
async def test_protocol_spec_fetcher_extraction():
    fetcher = ProtocolSpecFetcher()
    eip_num = fetcher._extract_eip_number("EIP-4844: Shard Blob Transactions")
    assert eip_num == "4844"

    meta = await fetcher.resolve_protocol_specs("EIP-4844: Shard Blob Transactions")
    assert meta["eip_number"] == "4844"
    assert len(meta["exploit_cases"]) >= 3


@pytest.mark.asyncio
async def test_rich_protocol_explainer_generation():
    record = IntelligenceRecord(
        id="eth_eip_4844",
        source_type="rss",
        channel_id="ethereum_research",
        channel_name="Ethereum Research",
        category="crypto",
        title="EIP-4844: Proto-Danksharding for Rollup Scalability",
        url="https://eips.ethereum.org/EIPS/eip-4844",
        author="Vitalik Buterin et al.",
        summary="Introducing temporary blob-carrying transactions to scale Ethereum rollups.",
        raw_content="EIP-4844 introduces a new transaction format for blob-carrying transactions, using KZG commitments to verify data availability without burdening EVM execution state.",
    )

    explainer = ProtocolExplainer()
    payload = await explainer.explain(record, status="draft")

    assert payload.genre == "protocol_security"
    assert "プロトコル" in payload.title or "EIP-4844" in payload.title
    assert "テクノロジー" in payload.themes

    content = payload.content
    # Must contain Spec card, Protocol overview, Motivation, Architecture, Exploit table
    assert "プロトコル仕様" in content
    assert "プロトコル概要" in content
    assert "1. 背景と設計動機" in content
    assert "2. 技術アーキテクチャ" in content
    assert "3. 過去のハッキング・脆弱性事例" in content
    assert "MEV" in content
    assert "Reentrancy" in content
    assert "<table" in content
    assert "https://eips.ethereum.org/EIPS/eip-4844" in content

    # Quality Gate check
    qg = QualityGate()
    is_valid, issues = qg.validate(payload)
    assert is_valid is True
    assert len(issues) == 0
