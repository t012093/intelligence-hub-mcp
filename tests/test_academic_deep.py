"""Unit tests for AcademicDeepClient and rich PaperExplainer."""

import pytest
from intelligence_hub.core.models import IntelligenceRecord
from intelligence_hub.intake.academic_deep_client import AcademicDeepClient
from intelligence_hub.analysis.paper_explainer import PaperExplainer
from intelligence_hub.analysis.quality_gate import QualityGate


@pytest.mark.asyncio
async def test_academic_deep_client_identifier_extraction():
    client = AcademicDeepClient()
    id1 = client._extract_identifier("https://arxiv.org/abs/2408.12345")
    assert id1 == "ARXIV:2408.12345"

    id2 = client._extract_identifier("https://doi.org/10.1101/2024.08.01.123456")
    assert id2 == "DOI:10.1101/2024.08.01.123456"


@pytest.mark.asyncio
async def test_rich_paper_explainer_generation():
    record = IntelligenceRecord(
        id="arxiv_2408_99999",
        source_type="arxiv_query",
        channel_id="arxiv_ai",
        channel_name="arXiv AI",
        category="ai_engineering",
        title="Mamba-2: State Space Duality with Attention Matrix Equivalence",
        url="https://arxiv.org/abs/2408.99999",
        author="Tri Dao, Albert Gu",
        summary="State Space Duality theory connecting structured state space models to structured attention.",
        raw_content="Abstract: We introduce State Space Duality (SSD), proving exact equivalence between selective SSMs and structured masked attention, enabling 3.2X faster inference.",
    )

    explainer = PaperExplainer()
    payload = await explainer.explain(record, status="draft")

    assert payload.genre == "paper_digest"
    assert "Mamba-2" in payload.title or "論文" in payload.title
    assert "テクノロジー" in payload.themes

    content = payload.content
    # Must contain Bibliographic card, Executive summary, Lineage, Methodology, Benchmarks, MAD review
    assert "基本情報" in content
    assert "論文サマリー" in content
    assert "研究の系譜" in content
    assert "提案手法の数理" in content
    assert "実証結果" in content
    assert "MAD 査読分析" in content
    assert "Proponent" in content
    assert "Critic" in content
    assert "<table" in content
    assert "https://arxiv.org/abs/2408.99999" in content

    # Quality Gate check
    qg = QualityGate()
    is_valid, issues = qg.validate(payload)
    assert is_valid is True
    assert len(issues) == 0
