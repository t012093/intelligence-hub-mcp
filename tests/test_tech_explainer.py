"""Unit tests for TechExplainer and QualityGate."""

import pytest
from intelligence_hub.core.models import IntelligenceRecord, ArticlePayload
from intelligence_hub.analysis.tech_explainer import TechExplainer
from intelligence_hub.analysis.quality_gate import QualityGate


@pytest.fixture
def sample_oss_record():
    return IntelligenceRecord(
        id="gh_unslothai_unsloth",
        source_type="github_trending",
        channel_id="gh_trending_ai",
        channel_name="GitHub Trending (AI)",
        category="ai_engineering",
        title="unslothai/unsloth: 5X faster 80% less memory LLM fine-tuning",
        url="https://github.com/unslothai/unsloth",
        summary="[⭐ Total: 28,000 / Forks: 2,100] 5X faster 80% less memory LLM fine-tuning",
        raw_content="## Features\n- 5X faster fine-tuning with custom Triton kernels\n- 80% less memory consumption\n## Usage\n```bash\npip install unsloth\n```\n```python\nfrom unsloth import FastLanguageModel\nmodel, tokenizer = FastLanguageModel.from_pretrained('unsloth/llama-3-8b')\n```",
        metrics={
            "stars_today": 450,
            "total_stars": 28000,
            "forks": 2100,
            "language": "Python",
        },
    )


@pytest.mark.asyncio
async def test_tech_explainer_generates_concrete_article(sample_oss_record):
    explainer = TechExplainer()
    payload = await explainer.explain(sample_oss_record, status="draft")

    assert payload.genre == "tech_deep_dive"
    assert "unsloth" in payload.title.lower()
    assert "テクノロジー" in payload.themes
    assert len(payload.excerpt) <= 120

    content = payload.content
    # Must contain TL;DR, Problem, How it works, Usage, Table
    assert "TL;DR" in content
    assert "1. 解決する課題" in content
    assert "2. アーキテクチャ" in content
    assert "3. インストール ＆ クイックスタート" in content
    assert "4. 既存ツールとの定量比較" in content
    assert "<table" in content
    assert "<code" in content
    assert "pip install" in content


def test_quality_gate_validation():
    qg = QualityGate()

    # Valid payload
    valid_payload = ArticlePayload(
        title="【急上昇OSS】Unsloth の実践解説",
        slug="tech-unsloth",
        content="<h2>TL;DR</h2><p>Overview</p><pre><code class=\"language-bash\">pip install unsloth</code></pre><table><tr><td>Metric</td></tr></table>" * 5,
        excerpt="Summary",
        status="draft",
        genre="tech_deep_dive",
        author_id="test_author",
    )
    is_valid, issues = qg.validate(valid_payload)
    assert is_valid is True
    assert len(issues) == 0

    # Invalid payload (missing code and table)
    invalid_payload = ArticlePayload(
        title="【急上昇OSS】Unsloth の実践解説",
        slug="tech-unsloth",
        content="<p>Just text without any code or tables.</p>" * 10,
        excerpt="Summary",
        status="draft",
        genre="tech_deep_dive",
        author_id="test_author",
    )
    is_valid, issues = qg.validate(invalid_payload)
    assert is_valid is False
    assert any("code snippet" in i for i in issues)
    assert any("comparison table" in i for i in issues)
