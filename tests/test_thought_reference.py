"""Unit tests for ThoughtReferenceClient and rich Crossover synthesis."""

import pytest
from intelligence_hub.analysis.thought_reference_client import ThoughtReferenceClient
from intelligence_hub.publishing.coral_publisher import CoralPublisher
from intelligence_hub.core.models import CrossoverDigest, CrossoverTheme
from intelligence_hub.analysis.quality_gate import QualityGate


def test_thought_reference_selection():
    client = ThoughtReferenceClient()
    t1 = client.get_thought_injection(["ai_engineering", "crypto"])
    assert "Hofstadter" in t1["author"] or "GEB" in t1["book"]

    t2 = client.get_thought_injection(["ai_engineering", "synthetic_biology"])
    assert "Neumann" in t2["author"]

    t3 = client.get_thought_injection(["crypto"])
    assert "Shannon" in t3["author"]


@pytest.mark.asyncio
async def test_rich_crossover_html_includes_thought_card():
    digest = CrossoverDigest(
        digest_id="test_digest_thought",
        generated_at="2026-08-17T12:00:00Z",
        period="daily",
        genre="crossover_feature",
        crossover_themes=[
            CrossoverTheme(
                theme_title="AIエージェントと暗号合意の自己組織化",
                domains=["ai_engineering", "crypto"],
                core_concept="状態機械の自己言及ループ",
                synergy_description="AIエージェントによる経済ゲームの自律検証。",
                actionable_implications=["スマートコントラクト監査へのLLM導入"],
            )
        ],
        markdown_report="# Digest",
        suggested_themes=["テクノロジー"],
        suggested_tags=["AI", "Crypto"],
        source_records=["https://sample.com/source"],
    )

    publisher = CoralPublisher()
    payload_dict = await publisher.format_article_payload(digest)

    content = payload_dict["content"]
    assert "科学思想・古典からの示唆" in content
    assert "ゲーデル、エッシャー、バッハ" in content or "Norbert Wiener" in content or "Claude Shannon" in content
    assert "The Philosophical Horizon" in content
    assert "<table" in content
