"""Tests for feed loader and hot reloading."""

import pytest
from pathlib import Path
from intelligence_hub.core.feed_loader import FeedRegistryLoader


def test_feed_loader_loads_channels():
    loader = FeedRegistryLoader()
    core = loader.get_core_channels()
    serendipity = loader.get_serendipity_channels()
    all_channels = loader.get_all_channels()

    assert len(core) >= 5
    assert len(serendipity) >= 2
    assert len(all_channels) == len(core) + len(serendipity)


def test_feed_loader_by_category():
    loader = FeedRegistryLoader()
    ai_channels = loader.get_channels_by_category("ai_engineering")
    synthbio_channels = loader.get_channels_by_category("synthetic_biology")

    assert len(ai_channels) > 0
    assert any(c.id == "zenn_trend" for c in ai_channels)
    assert len(synthbio_channels) > 0
