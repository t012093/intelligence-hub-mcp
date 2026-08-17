"""Unit tests for PaperExplainer and ProtocolExplainer."""

import pytest
from intelligence_hub.core.models import IntelligenceRecord
from intelligence_hub.analysis.paper_explainer import PaperExplainer
from intelligence_hub.analysis.protocol_explainer import ProtocolExplainer
from intelligence_hub.analysis.quality_gate import QualityGate


@pytest.fixture
def sample_paper_record():
    return IntelligenceRecord(
        id="arxiv_2408_12345",
        source_type="arxiv_query",
        channel_id="arxiv_ai",
        channel_name="arXiv AI",
        category="ai_engineering",
        title="Sparse Attention with State-Space Duality for Sub-quadratic Sequence Modeling",
        url="https://arxiv.org/abs/2408.12345",
        author="Tri Dao et al.",
        summary="Sub-quadratic sequence modeling combining Mamba and FlashAttention.",
        raw_content="Abstract: Transformers face quadratic scaling bottlenecks. We propose a sparse attention mechanism combined with SSD (State Space Duality), achieving 3.2X faster inference and reducing memory by 73%.",
    )


@pytest.fixture
def sample_protocol_record():
    return IntelligenceRecord(
        id="eth_zk_sharding",
        source_type="rss",
        channel_id="ethereum_research",
        channel_name="Ethereum Research",
        category="crypto",
        title="Stateless Block Verification via Recursive SNARKs",
        url="https://ethresear.ch/t/stateless-snarks/9999",
        author="Vitalik Buterin",
        summary="Proposal for stateless block verification using recursive zero-knowledge proofs.",
        raw_content="Discussion on recursive SNARKs to achieve constant-size witness proofs for execution state transitions, preventing MEV manipulation and reentrancy vectors.",
    )


@pytest.mark.asyncio
async def test_paper_explainer_generates_academic_article(sample_paper_record):
    explainer = PaperExplainer()
    payload = await explainer.explain(sample_paper_record, status="draft")

    assert payload.genre == "paper_digest"
    assert "論文" in payload.title
    assert "テクノロジー" in payload.themes
    assert len(payload.excerpt) <= 120

    content = payload.content
    assert "論文サマリー" in content
    assert "1. 研究の系譜" in content
    assert "2. 提案手法の数理" in content
    assert "3. 具体的データセット" in content
    assert "<table" in content
    assert "https://arxiv.org/abs/2408.12345" in content

    # Quality Gate check
    qg = QualityGate()
    is_valid, issues = qg.validate(payload)
    assert is_valid is True
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_protocol_explainer_generates_security_article(sample_protocol_record):
    explainer = ProtocolExplainer()
    payload = await explainer.explain(sample_protocol_record, status="draft")

    assert payload.genre == "protocol_security"
    assert "プロトコル" in payload.title
    assert "テクノロジー" in payload.themes
    assert len(payload.excerpt) <= 120

    content = payload.content
    assert "プロトコル概要" in content
    assert "1. 背景と設計動機" in content
    assert "2. 技術アーキテクチャ" in content
    assert "3. 脅威モデルと攻撃耐性" in content
    assert "<table" in content
    assert "https://ethresear.ch/t/stateless-snarks/9999" in content

    # Quality Gate check
    qg = QualityGate()
    is_valid, issues = qg.validate(payload)
    assert is_valid is True
    assert len(issues) == 0
