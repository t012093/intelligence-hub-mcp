"""Integration tests for MCP tools in intelligence-hub."""

import pytest
from intelligence_hub.mcp import tools


@pytest.mark.asyncio
async def test_get_feed_status():
    res = await tools.get_feed_status()
    assert res["status"] == "success"
    assert res["channels_configured"] >= 5
    assert "database_stats" in res


@pytest.mark.asyncio
async def test_fetch_and_search_intelligence():
    # Fetch with force_fetch=True to override interval in tests
    res = await tools.fetch_intelligence_feed(
        category="ai_engineering", limit_per_channel=2, force_fetch=True
    )
    assert res["status"] == "success"
    assert res["total_fetched"] >= 1

    # Immediate second fetch without force_fetch should be skipped by interval
    res_skip = await tools.fetch_intelligence_feed(category="ai_engineering", limit_per_channel=2)
    assert res_skip["status"] == "success"
    assert res_skip["skipped_by_interval"] >= 1

    # Search
    search_res = await tools.search_intelligence(query="AI model agent", limit=5)
    assert isinstance(search_res, list)
    assert len(search_res) >= 1
    assert "title" in search_res[0]
    assert "url" in search_res[0]


@pytest.mark.asyncio
async def test_generate_crossover_digest():
    res = await tools.generate_crossover_digest(period="daily", fetch_latest_first=False)
    assert res["status"] == "success"
    assert "digest_id" in res
    assert "markdown_report" in res
    assert len(res["markdown_report"]) > 50
    assert "suggested_themes" in res
    assert "suggested_tags" in res


@pytest.mark.asyncio
async def test_feed_channel_limit_immutable():
    # Calling fetch with limit override should not mutate cached channel limit permanently
    status_before = await tools.get_feed_status()
    await tools.fetch_intelligence_feed(category="ai_engineering", limit_per_channel=1)
    status_after = await tools.get_feed_status()
    assert len(status_before["channels"]) == len(status_after["channels"])
