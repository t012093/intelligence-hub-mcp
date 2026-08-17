"""Academic fetcher for arXiv queries."""

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Optional
import httpx

from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import FeedChannelConfig, IntelligenceRecord
from intelligence_hub.intake.base import BaseFetcher

logger = get_logger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class AcademicFetcher(BaseFetcher):
    """Fetches academic paper preprints from arXiv."""

    def __init__(self, timeout_sec: float = 15.0):
        self.timeout_sec = timeout_sec

    async def fetch(self, channel: FeedChannelConfig) -> List[IntelligenceRecord]:
        categories = channel.categories or ["cs.AI"]
        limit = channel.limit or 15

        # Build query string: cat:cs.AI OR cat:cs.CL
        query = " OR ".join([f"cat:{cat}" for cat in categories])
        params = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": limit,
        }

        logger.info(f"Querying arXiv: {query} (max={limit})")
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_sec, follow_redirects=True
            ) as client:
                resp = await client.get(ARXIV_API_URL, params=params)
                resp.raise_for_status()
                xml_text = resp.text
        except Exception as e:
            logger.error(f"Failed to query arXiv: {e}")
            return []

        return self._parse_arxiv_response(xml_text, channel)

    def _parse_arxiv_response(
        self, xml_text: str, channel: FeedChannelConfig
    ) -> List[IntelligenceRecord]:
        records: List[IntelligenceRecord] = []
        try:
            root = ET.fromstring(xml_text)
            entries = root.findall("atom:entry", ATOM_NS)

            for entry in entries:
                rec = self._parse_entry(entry, channel)
                if rec:
                    records.append(rec)
        except Exception as e:
            logger.error(f"Error parsing arXiv XML: {e}")

        logger.info(f"Fetched {len(records)} papers from arXiv for {channel.name}")
        return records

    def _parse_entry(
        self, entry: ET.Element, channel: FeedChannelConfig
    ) -> Optional[IntelligenceRecord]:
        id_elem = entry.find("atom:id", ATOM_NS)
        title_elem = entry.find("atom:title", ATOM_NS)
        summary_elem = entry.find("atom:summary", ATOM_NS)
        published_elem = entry.find("atom:published", ATOM_NS)

        if id_elem is None or title_elem is None:
            return None

        paper_url = id_elem.text.strip() if id_elem.text else ""
        title = " ".join(title_elem.text.split()) if title_elem.text else ""
        summary = " ".join(summary_elem.text.split()) if summary_elem is not None and summary_elem.text else ""

        authors = []
        for author in entry.findall("atom:author", ATOM_NS):
            name_elem = author.find("atom:name", ATOM_NS)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())

        published_at = published_elem.text.strip() if published_elem is not None and published_elem.text else None

        # Tags
        tags = []
        for cat in entry.findall("atom:category", ATOM_NS):
            term = cat.get("term")
            if term:
                tags.append(term)

        # PDF URL
        pdf_url = paper_url.replace("abs", "pdf") if "abs" in paper_url else paper_url

        item_id = hashlib.sha256(paper_url.encode("utf-8")).hexdigest()[:16]

        return IntelligenceRecord(
            id=f"arxiv_{item_id}",
            source_type="arxiv",
            channel_id=channel.id,
            channel_name=channel.name,
            category=channel.category,
            is_serendipity=channel.is_serendipity,
            title=title,
            url=paper_url,
            author=", ".join(authors[:3]),
            published_at=published_at,
            summary=summary[:1000],
            raw_content=summary,
            tags=tags,
            metrics={"pdf_url": pdf_url, "primary_category": tags[0] if tags else ""},
        )
