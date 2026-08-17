"""Tests for crossover analysis and synthesis."""

import pytest
from intelligence_hub.core.models import IntelligenceRecord
from intelligence_hub.analysis.crossover import CrossoverAnalyzer
from intelligence_hub.analysis.synthesizer import IntelligenceSynthesizer


@pytest.mark.asyncio
async def test_crossover_analyzer_heuristic_fallback():
    analyzer = CrossoverAnalyzer()
    # Force heuristic by testing with 2 records
    r1 = IntelligenceRecord(
        id="r1",
        source_type="rss",
        channel_id="c1",
        channel_name="AI News",
        category="ai_engineering",
        title="Diffusion Models in Optimization",
        url="https://example.com/1",
        summary="Using diffusion models for combinatorial search.",
    )
    r2 = IntelligenceRecord(
        id="r2",
        source_type="rss",
        channel_id="c2",
        channel_name="Bio News",
        category="synthetic_biology",
        title="DNA Sequence Synthesis Algorithms",
        url="https://example.com/2",
        summary="Fast sequence search in genomic spaces.",
    )

    themes = await analyzer.analyze([r1, r2])
    assert len(themes) >= 1
    assert "ai_engineering" in themes[0].domains or "synthetic_biology" in themes[0].domains


@pytest.mark.asyncio
async def test_synthesizer_creates_digest():
    synthesizer = IntelligenceSynthesizer()
    r1 = IntelligenceRecord(
        id="r1",
        source_type="rss",
        channel_id="c1",
        channel_name="AI News",
        category="ai_engineering",
        title="Neural Architecture Search",
        url="https://example.com/1",
        summary="Automated architecture search.",
    )
    r2 = IntelligenceRecord(
        id="r2",
        source_type="hn",
        channel_id="c2",
        channel_name="HN Show",
        category="serendipity",
        is_serendipity=True,
        title="Show HN: Rust-based Bio-Simulator",
        url="https://example.com/2",
        summary="High performance biology simulation.",
    )

    digest = await synthesizer.synthesize(
        core_records=[r1],
        serendipity_records=[r2],
        period="daily",
    )

    assert digest.digest_id.startswith("digest_")
    assert len(digest.markdown_report) > 100
    assert "Neural Architecture Search" in digest.markdown_report
    assert len(digest.suggested_themes) > 0
    assert len(digest.suggested_tags) > 0
