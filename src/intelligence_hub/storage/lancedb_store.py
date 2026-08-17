"""LanceDB persistence and vector search for intelligence records using pure PyArrow."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import lancedb
import pyarrow as pa

from intelligence_hub.core.config import LANCEDB_PATH
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import IntelligenceRecord
from intelligence_hub.storage.embedder import Embedder

logger = get_logger(__name__)

SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("source_type", pa.string()),
        pa.field("channel_id", pa.string()),
        pa.field("channel_name", pa.string()),
        pa.field("category", pa.string()),
        pa.field("is_serendipity", pa.bool_()),
        pa.field("title", pa.string()),
        pa.field("url", pa.string()),
        pa.field("author", pa.string()),
        pa.field("published_at", pa.string()),
        pa.field("summary", pa.string()),
        pa.field("raw_content", pa.string()),
        pa.field("tags_json", pa.string()),
        pa.field("metrics_json", pa.string()),
        pa.field("fetched_at", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), 768)),
    ]
)


class IntelligenceStore:
    """LanceDB-backed store for intelligence records using PyArrow."""

    TABLE_NAME = "intelligence_records"

    def __init__(self, db_path: Optional[str] = None, embedder: Optional[Embedder] = None):
        self.db_path = db_path or LANCEDB_PATH
        self.embedder = embedder or Embedder(dimension=768)
        self._db = lancedb.connect(self.db_path)
        self._table = self._init_table()

    def _init_table(self):
        try:
            return self._db.open_table(self.TABLE_NAME)
        except Exception:
            logger.info(f"Creating new LanceDB table '{self.TABLE_NAME}' at {self.db_path}")
            return self._db.create_table(self.TABLE_NAME, schema=SCHEMA)

    def save_records(self, records: List[IntelligenceRecord]) -> int:
        """Saves a batch of intelligence records, embedding text content."""
        if not records:
            return 0

        self._table = self._db.open_table(self.TABLE_NAME)

        # Existing IDs for deduplication
        existing_ids = set()
        try:
            tbl_arrow = self._table.search().select(["id"]).to_arrow()
            if "id" in tbl_arrow.column_names:
                existing_ids = set(tbl_arrow["id"].to_pylist())
        except Exception as e:
            logger.debug(f"Could not read existing IDs: {e}")

        new_records = [r for r in records if r.id not in existing_ids]
        if not new_records:
            logger.info("All records already exist in store. Skipping insert.")
            return 0

        # Generate embeddings
        texts = [f"{r.title}\n{r.summary}" for r in new_records]
        vectors = self.embedder.embed_batch(texts)

        data = []
        for r, vec in zip(new_records, vectors):
            data.append(
                {
                    "id": r.id,
                    "source_type": r.source_type,
                    "channel_id": r.channel_id,
                    "channel_name": r.channel_name,
                    "category": r.category,
                    "is_serendipity": r.is_serendipity,
                    "title": r.title,
                    "url": r.url,
                    "author": r.author or "",
                    "published_at": r.published_at or "",
                    "summary": r.summary,
                    "raw_content": r.raw_content or "",
                    "tags_json": json.dumps(r.tags, ensure_ascii=False),
                    "metrics_json": json.dumps(r.metrics, ensure_ascii=False),
                    "fetched_at": r.fetched_at,
                    "vector": vec,
                }
            )

        self._table.add(data)
        logger.info(f"Saved {len(data)} new intelligence records to LanceDB")
        return len(data)

    def search(
        self, query: str, category: Optional[str] = None, limit: int = 10
    ) -> List[IntelligenceRecord]:
        """Vector similarity search on stored records using PyArrow."""
        query_vec = self.embedder.embed(query)
        q = self._table.search(query_vec).limit(limit)

        if category:
            safe_cat = category.replace("'", "''")
            q = q.where(f"category = '{safe_cat}'")

        tbl = q.to_arrow()
        return self._arrow_to_records(tbl)

    def list_records(
        self,
        category: Optional[str] = None,
        is_serendipity: Optional[bool] = None,
        limit: int = 50,
    ) -> List[IntelligenceRecord]:
        """Lists recent records with optional filters using pure PyArrow."""
        try:
            filters = []
            if category:
                safe_cat = category.replace("'", "''")
                filters.append(f"category = '{safe_cat}'")
            if is_serendipity is not None:
                val = "true" if is_serendipity else "false"
                filters.append(f"is_serendipity = {val}")

            where_clause = " AND ".join(filters) if filters else None
            q = self._table.search()
            if where_clause:
                q = q.where(where_clause)
            
            tbl = q.to_arrow()
            if tbl.num_rows == 0:
                return []

            records = self._arrow_to_records(tbl)
            # Sort by fetched_at descending
            records.sort(key=lambda r: r.fetched_at, reverse=True)
            return records[:limit]
        except Exception as e:
            logger.error(f"Error listing records: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Returns storage statistics using PyArrow column projection."""
        try:
            tbl = self._table.search().select(["category", "source_type", "is_serendipity"]).to_arrow()
            if tbl.num_rows == 0:
                return {"total_records": 0, "serendipity_count": 0, "core_count": 0, "categories": {}, "sources": {}}

            pydict = tbl.to_pydict()
            categories: Dict[str, int] = {}
            sources: Dict[str, int] = {}
            serendipity_count = 0
            num_rows = tbl.num_rows

            cats = pydict.get("category", [])
            srcs = pydict.get("source_type", [])
            serens = pydict.get("is_serendipity", [])

            for i in range(num_rows):
                c = cats[i]
                categories[c] = categories.get(c, 0) + 1
                s = srcs[i]
                sources[s] = sources.get(s, 0) + 1
                if serens[i]:
                    serendipity_count += 1

            return {
                "total_records": num_rows,
                "serendipity_count": serendipity_count,
                "core_count": num_rows - serendipity_count,
                "categories": categories,
                "sources": sources,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"total_records": 0, "error": str(e)}

    def get_channel_last_fetched_times(self) -> Dict[str, str]:
        """Returns the latest fetched_at timestamp for each channel_id."""
        try:
            tbl = self._table.search().select(["channel_id", "fetched_at"]).to_arrow()
            if tbl.num_rows == 0:
                return {}
            pydict = tbl.to_pydict()
            channel_ids = pydict.get("channel_id", [])
            fetched_ats = pydict.get("fetched_at", [])
            last_times: Dict[str, str] = {}
            for ch_id, f_time in zip(channel_ids, fetched_ats):
                if not ch_id:
                    continue
                if ch_id not in last_times or f_time > last_times[ch_id]:
                    last_times[ch_id] = f_time
            return last_times
        except Exception as e:
            logger.debug(f"Error getting channel last fetched times: {e}")
            return {}

    def _arrow_to_records(self, tbl: pa.Table) -> List[IntelligenceRecord]:
        if tbl.num_rows == 0:
            return []

        pydict = tbl.to_pydict()
        records: List[IntelligenceRecord] = []
        num_rows = tbl.num_rows

        tags_list = pydict.get("tags_json", ["[]"] * num_rows)
        metrics_list = pydict.get("metrics_json", ["{}"] * num_rows)
        author_list = pydict.get("author", [""] * num_rows)
        pub_list = pydict.get("published_at", [""] * num_rows)
        raw_list = pydict.get("raw_content", [""] * num_rows)

        for i in range(num_rows):
            try:
                tags = json.loads(tags_list[i])
            except Exception:
                tags = []
            try:
                metrics = json.loads(metrics_list[i])
            except Exception:
                metrics = {}

            records.append(
                IntelligenceRecord(
                    id=pydict["id"][i],
                    source_type=pydict["source_type"][i],
                    channel_id=pydict["channel_id"][i],
                    channel_name=pydict["channel_name"][i],
                    category=pydict["category"][i],
                    is_serendipity=bool(pydict["is_serendipity"][i]),
                    title=pydict["title"][i],
                    url=pydict["url"][i],
                    author=author_list[i] or None,
                    published_at=pub_list[i] or None,
                    summary=pydict["summary"][i],
                    raw_content=raw_list[i] or None,
                    tags=tags,
                    metrics=metrics,
                    fetched_at=pydict["fetched_at"][i],
                )
            )
        return records
