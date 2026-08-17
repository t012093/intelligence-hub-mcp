"""Unit tests for GitHubFetcher with mocked HTML scraping and Search API."""

import pytest
from unittest.mock import patch, MagicMock
from intelligence_hub.core.models import FeedChannelConfig, IntelligenceRecord
from intelligence_hub.intake.github_fetcher import GitHubFetcher
from intelligence_hub.intake import get_fetcher_for_channel

SAMPLE_TRENDING_HTML = """
<!DOCTYPE html>
<html>
<body>
  <article class="Box-row">
    <h2 class="h3 lh-condensed">
      <a href="/vllm-project/vllm">
        vllm-project / vllm
      </a>
    </h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
      High-throughput and memory-efficient LLM serving engine.
    </p>
    <div class="f6 color-fg-muted mt-2">
      <span class="d-inline-block ml-0 mr-3">
        <span itemprop="programmingLanguage">Python</span>
      </span>
      <a href="/vllm-project/vllm/stargazers" class="Link--muted d-inline-block mr-3">
        32,500
      </a>
      <a href="/vllm-project/vllm/forks" class="Link--muted d-inline-block mr-3">
        4,200
      </a>
      <span class="d-inline-block float-sm-right">
        850 stars today
      </span>
    </div>
  </article>
  <article class="Box-row">
    <h2 class="h3 lh-condensed">
      <a href="/shadcn-ui/ui">
        shadcn-ui / ui
      </a>
    </h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
      Beautifully designed components that you can copy and paste into your apps.
    </p>
    <div class="f6 color-fg-muted mt-2">
      <span class="d-inline-block ml-0 mr-3">
        <span itemprop="programmingLanguage">TypeScript</span>
      </span>
      <a href="/shadcn-ui/ui/stargazers" class="Link--muted d-inline-block mr-3">
        65,000
      </a>
      <span class="d-inline-block float-sm-right">
        420 stars today
      </span>
    </div>
  </article>
</body>
</html>
"""

SAMPLE_SEARCH_API_RESPONSE = {
    "total_count": 1,
    "items": [
        {
            "full_name": "ollama/ollama",
            "html_url": "https://github.com/ollama/ollama",
            "description": "Get up and running with Llama 3, Mistral, Gemma, and other LLMs.",
            "language": "Go",
            "stargazers_count": 98000,
            "forks_count": 8500,
            "pushed_at": "2026-08-17T12:00:00Z",
        }
    ],
}


@pytest.mark.asyncio
async def test_github_fetcher_registration():
    channel = FeedChannelConfig(
        id="github_trending_ai",
        category="ai_engineering",
        name="GitHub Trending AI",
        type="github_trending",
        languages=["python", "typescript"],
    )
    fetcher = get_fetcher_for_channel(channel)
    assert isinstance(fetcher, GitHubFetcher)


def test_parse_trending_html():
    fetcher = GitHubFetcher()
    channel = FeedChannelConfig(
        id="github_trending_ai",
        category="ai_engineering",
        name="GitHub Trending AI",
        type="github_trending",
        languages=["python"],
    )

    records = fetcher.parse_trending_html(SAMPLE_TRENDING_HTML, channel, "python")
    assert len(records) == 2

    # First repo (vllm)
    r1 = records[0]
    assert r1.id == "gh_vllm_project_vllm"
    assert r1.url == "https://github.com/vllm-project/vllm"
    assert r1.author == "vllm-project"
    assert "High-throughput" in r1.summary
    assert r1.metrics["stars_today"] == 850
    assert r1.metrics["total_stars"] == 32500
    assert r1.metrics["forks"] == 4200
    assert r1.metrics["language"] == "Python"
    assert "ai_engineering" in r1.tags
    assert "github" in r1.tags
    assert "trending" in r1.tags

    # Second repo (shadcn)
    r2 = records[1]
    assert r2.id == "gh_shadcn_ui_ui"
    assert r2.metrics["stars_today"] == 420
    assert r2.metrics["total_stars"] == 65000


@pytest.mark.asyncio
async def test_fetch_primary_scraping_success():
    fetcher = GitHubFetcher()
    channel = FeedChannelConfig(
        id="github_trending_ai",
        category="ai_engineering",
        name="GitHub Trending AI",
        type="github_trending",
        languages=["python"],
        limit=5,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_TRENDING_HTML

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        records = await fetcher.fetch(channel)
        assert len(records) == 2
        assert records[0].id == "gh_vllm_project_vllm"


@pytest.mark.asyncio
async def test_fetch_fallback_to_search_api():
    fetcher = GitHubFetcher()
    channel = FeedChannelConfig(
        id="github_trending_ai",
        category="ai_engineering",
        name="GitHub Trending AI",
        type="github_trending",
        languages=["python"],
        limit=5,
    )

    # 1st call (scraping) returns 403, 2nd call (Search API) returns 200 with JSON
    mock_scrape_resp = MagicMock()
    mock_scrape_resp.status_code = 403

    mock_api_resp = MagicMock()
    mock_api_resp.status_code = 200
    mock_api_resp.json.return_value = SAMPLE_SEARCH_API_RESPONSE

    with patch("httpx.AsyncClient.get", side_effect=[mock_scrape_resp, mock_api_resp]):
        records = await fetcher.fetch(channel)
        assert len(records) == 1
        r = records[0]
        assert r.id == "gh_ollama_ollama"
        assert r.url == "https://github.com/ollama/ollama"
        assert r.metrics["total_stars"] == 98000
        assert r.metrics["language"] == "Go"
        assert r.published_at == "2026-08-17T12:00:00Z"


@pytest.mark.asyncio
async def test_fetch_limit_enforced():
    fetcher = GitHubFetcher()
    channel = FeedChannelConfig(
        id="github_trending_ai",
        category="ai_engineering",
        name="GitHub Trending AI",
        type="github_trending",
        languages=["python"],
        limit=1,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_TRENDING_HTML

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        records = await fetcher.fetch(channel)
        assert len(records) == 1
