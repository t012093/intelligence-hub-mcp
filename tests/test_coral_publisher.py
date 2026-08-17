"""Unit tests for CoralPublisher and PublishingPipeline."""

import pytest
from unittest.mock import patch, MagicMock
from intelligence_hub.core.models import CrossoverDigest, CrossoverTheme
from intelligence_hub.publishing.coral_publisher import CoralPublisher, DEFAULT_AUTHOR_ID
from intelligence_hub.publishing.pipeline import PublishingPipeline


@pytest.fixture
def sample_digest():
    return CrossoverDigest(
        digest_id="test_digest_001",
        generated_at="2026-08-17T12:00:00Z",
        period="daily",
        core_insights=[{"id": "c1", "title": "Post-Quantum VRF"}],
        serendipity_finds=[{"id": "s1", "title": "Tiny LLM Needle"}],
        crossover_themes=[
            CrossoverTheme(
                theme_title="暗号分散検証とLLMサービングの越境融合",
                domains=["crypto", "ai_engineering"],
                core_concept="ゼロ知識証明によるエッジ推論の検証可能性担保",
                synergy_description="小型モデルの分散合意における安全性と信頼性の両立。",
                actionable_implications=["検証プロトコル仕様の策定", "PoC実装の構築"],
                referenced_record_ids=["c1", "s1"],
                suggested_themes=["テクノロジー"],
                suggested_tags=["Crypto", "AI", "Crossover"],
            )
        ],
        markdown_report="# Digest Report Markdown",
        suggested_themes=["テクノロジー"],
        suggested_tags=["Crypto", "AI", "Crossover"],
        source_records=["https://ethresear.ch/t/sample", "https://github.com/sample/repo"],
    )


def test_coral_publisher_payload_formatting(sample_digest):
    publisher = CoralPublisher()
    payload = publisher.format_article_payload(sample_digest, status="draft")

    assert "異分野交差点インテリジェンス・ダイジェスト" in payload["title"]
    assert payload["author_id"] == DEFAULT_AUTHOR_ID
    assert payload["status"] == "draft"
    assert "テクノロジー" in payload["themes"]
    assert "Crossover" in payload["tags"]
    assert len(payload["excerpt"]) <= 120

    # WIRED Structure check
    content = payload["content"]
    assert "<h2>The Hook (導入)</h2>" in content
    assert "<h2>The Paradigm Shift (越境と構造変革)</h2>" in content
    assert "<h2>The Philosophical Horizon (結びと問い)</h2>" in content
    assert "<h2>参考文献・出典（References）</h2>" in content
    assert "<table" in content
    assert "https://ethresear.ch/t/sample" in content


def test_generate_x_threads(sample_digest):
    publisher = CoralPublisher()
    threads = publisher.generate_x_threads(sample_digest)
    assert len(threads) == 3
    assert "【80:20 Crossover Digest" in threads[0]
    assert "暗号分散検証とLLMサービングの越境融合" in threads[0]
    assert "分析母数:" in threads[2]


@pytest.mark.asyncio
async def test_publish_api_fallback_to_ready(sample_digest):
    publisher = CoralPublisher(api_url="http://invalid-local-url:9999/api/articles")
    res = await publisher.publish(sample_digest, status="draft")
    assert res["status"] == "ready"
    assert res["mode"] == "payload_ready"
    assert "payload" in res
    assert res["payload"]["author_id"] == DEFAULT_AUTHOR_ID
