"""Tests for LanceDB intelligence store."""

import tempfile
import pytest
from intelligence_hub.core.models import IntelligenceRecord
from intelligence_hub.storage.lancedb_store import IntelligenceStore
from intelligence_hub.storage.embedder import Embedder


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test_intel.db"
        # Use dummy embedder with 768 dim
        embedder = Embedder(dimension=768)
        store = IntelligenceStore(db_path=db_path, embedder=embedder)
        yield store


def test_save_and_search_records(temp_store):
    r1 = IntelligenceRecord(
        id="rec1",
        source_type="rss",
        channel_id="zenn_trend",
        channel_name="Zenn Tech",
        category="ai_engineering",
        is_serendipity=False,
        title="Building LLM Agent with Python",
        url="https://zenn.dev/articles/1",
        summary="A guide on building autonomous agents.",
        tags=["python", "llm"],
    )
    r2 = IntelligenceRecord(
        id="rec2",
        source_type="rss",
        channel_id="biorxiv_synthbio",
        channel_name="bioRxiv SynthBio",
        category="synthetic_biology",
        is_serendipity=False,
        title="CRISPR Protein Engineering Techniques",
        url="https://biorxiv.org/articles/2",
        summary="Novel computational methods for protein design.",
        tags=["crispr", "protein"],
    )

    saved = temp_store.save_records([r1, r2])
    assert saved == 2

    # Deduplication test
    saved_again = temp_store.save_records([r1])
    assert saved_again == 0

    # List records
    all_recs = temp_store.list_records()
    assert len(all_recs) == 2

    # Category filter
    ai_recs = temp_store.list_records(category="ai_engineering")
    assert len(ai_recs) == 1
    assert ai_recs[0].id == "rec1"

    # Stats
    stats = temp_store.get_stats()
    assert stats["total_records"] == 2
    assert stats["categories"]["ai_engineering"] == 1
