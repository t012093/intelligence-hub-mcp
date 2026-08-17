"""GitHub Trending fetcher with HTML scraping and Search API fallback."""

import asyncio
from datetime import datetime, timezone, timedelta
import os
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import httpx

from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import FeedChannelConfig, IntelligenceRecord
from intelligence_hub.intake.base import BaseFetcher

logger = get_logger(__name__)

TRENDING_BASE_URL = "https://github.com/trending"
SEARCH_API_URL = "https://api.github.com/search/repositories"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class GitHubFetcher(BaseFetcher):
    """Fetches trending repositories from GitHub via scraping with API fallback."""

    def __init__(self, timeout_sec: float = 12.0, max_concurrency: int = 2):
        self.timeout_sec = timeout_sec
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch(self, channel: FeedChannelConfig) -> List[IntelligenceRecord]:
        languages = channel.languages or [""]
        limit = channel.limit or 20

        tasks = [self._fetch_for_language(channel, lang) for lang in languages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_records: List[IntelligenceRecord] = []
        seen_urls = set()

        for res in results:
            if isinstance(res, list):
                for rec in res:
                    if rec.url not in seen_urls:
                        seen_urls.add(rec.url)
                        all_records.append(rec)
            elif isinstance(res, Exception):
                logger.warning(f"Error fetching GitHub trend for {channel.name}: {res}")

        logger.info(
            f"Fetched {len(all_records)} repos from GitHub for {channel.name} (limit={limit})"
        )
        return all_records[:limit]

    async def _fetch_for_language(
        self, channel: FeedChannelConfig, language: str
    ) -> List[IntelligenceRecord]:
        async with self.semaphore:
            # 1. Primary: HTML Trending Scraping
            records = await self._scrape_trending(channel, language)
            if records:
                return records

            # 2. Fallback: Search API
            logger.info(
                f"Falling back to GitHub Search API for channel {channel.name} (lang={language or 'all'})"
            )
            return await self._fetch_via_search_api(channel, language)

    async def _scrape_trending(
        self, channel: FeedChannelConfig, language: str
    ) -> List[IntelligenceRecord]:
        lang_path = f"/{language}" if language.strip() else ""
        url = f"{TRENDING_BASE_URL}{lang_path}?since=daily"
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_sec, follow_redirects=True
            ) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.debug(
                        f"GitHub Trending scraping returned status {resp.status_code} for {url}"
                    )
                    return []
                html_text = resp.text
        except Exception as e:
            logger.debug(f"GitHub Trending scraping failed for {url}: {e}")
            return []

        return self.parse_trending_html(html_text, channel, language)

    def parse_trending_html(
        self, html_text: str, channel: FeedChannelConfig, language: str
    ) -> List[IntelligenceRecord]:
        soup = BeautifulSoup(html_text, "html.parser")
        articles = soup.find_all("article")
        if not articles:
            # Try finding Box-row elements if article tags are missing
            articles = soup.find_all(class_=re.compile(r"Box-row"))

        records: List[IntelligenceRecord] = []
        for article in articles:
            rec = self._parse_article(article, channel, language)
            if rec:
                records.append(rec)

        return records

    def _parse_article(
        self, article: Any, channel: FeedChannelConfig, default_lang: str
    ) -> Optional[IntelligenceRecord]:
        h2 = article.find("h2") or article.find("h1")
        if not h2:
            return None

        a_tag = h2.find("a")
        if not a_tag or not a_tag.get("href"):
            return None

        repo_path = a_tag.get("href", "").strip().lstrip("/")
        parts = repo_path.split("/")
        if len(parts) < 2:
            return None

        owner, repo_name = parts[0].strip(), parts[1].strip()
        full_repo = f"{owner}/{repo_name}"
        repo_url = f"https://github.com/{full_repo}"

        # Description
        desc_elem = article.find("p")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Language
        lang_elem = article.find("span", {"itemprop": "programmingLanguage"})
        lang = lang_elem.get_text(strip=True) if lang_elem else default_lang

        # Stars today & total stars
        stars_today = 0
        total_stars = 0
        forks = 0

        # Look for "stars today" span / text
        article_text = article.get_text(" ", strip=True)
        today_match = re.search(r"([\d,]+)\s+stars\s+today", article_text, re.I)
        if today_match:
            stars_today = int(today_match.group(1).replace(",", ""))

        # Look for total stars / forks in links
        links = article.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            if href.endswith("/stargazers") or "/stargazers" in href:
                num_text = link.get_text(strip=True).replace(",", "")
                if num_text.isdigit():
                    total_stars = int(num_text)
            elif href.endswith("/forks") or "/forks" in href:
                num_text = link.get_text(strip=True).replace(",", "")
                if num_text.isdigit():
                    forks = int(num_text)

        title = f"{full_repo}: {description[:100]}" if description else full_repo
        summary = (
            f"[⭐ +{stars_today} stars today / Total: {total_stars:,}] {description}"
            if description
            else f"[⭐ +{stars_today} stars today / Total: {total_stars:,}]"
        )

        tags = [t for t in [lang.lower() if lang else "", channel.category, "github", "trending"] if t]

        metrics = {
            "stars_today": stars_today,
            "total_stars": total_stars,
            "forks": forks,
            "language": lang,
        }

        record_id = f"gh_{owner}_{repo_name}".lower().replace("-", "_")

        return IntelligenceRecord(
            id=record_id,
            source_type="github_trending",
            channel_id=channel.id,
            channel_name=channel.name,
            category=channel.category,
            is_serendipity=channel.is_serendipity,
            title=title,
            url=repo_url,
            author=owner,
            published_at=datetime.now(timezone.utc).isoformat(),
            summary=summary[:1000],
            raw_content=description,
            tags=tags,
            metrics=metrics,
        )

    async def _fetch_via_search_api(
        self, channel: FeedChannelConfig, language: str
    ) -> List[IntelligenceRecord]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": USER_AGENT,
        }
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        if language.strip():
            query = f"language:{language.strip()} stars:>20 pushed:>{days_ago}"
        else:
            query = f"stars:>50 pushed:>{days_ago}"

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": channel.limit or 20,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(SEARCH_API_URL, headers=headers, params=params)
                if resp.status_code != 200:
                    logger.warning(
                        f"GitHub Search API returned status {resp.status_code} for query {query}"
                    )
                    return []
                data = resp.json()
                items = data.get("items", [])
        except Exception as e:
            logger.error(f"GitHub Search API query failed: {e}")
            return []

        records: List[IntelligenceRecord] = []
        for item in items:
            rec = self._parse_api_item(item, channel, language)
            if rec:
                records.append(rec)

        return records

    def _parse_api_item(
        self, item: Dict[str, Any], channel: FeedChannelConfig, default_lang: str
    ) -> Optional[IntelligenceRecord]:
        full_name = item.get("full_name")
        if not full_name or "/" not in full_name:
            return None

        owner, repo_name = full_name.split("/", 1)
        html_url = item.get("html_url") or f"https://github.com/{full_name}"
        description = item.get("description") or ""
        lang = item.get("language") or default_lang
        stars = item.get("stargazers_count", 0)
        forks = item.get("forks_count", 0)
        pushed_at = item.get("pushed_at")

        title = f"{full_name}: {description[:100]}" if description else full_name
        summary = (
            f"[⭐ Total: {stars:,} / Forks: {forks:,}] {description}"
            if description
            else f"[⭐ Total: {stars:,} / Forks: {forks:,}]"
        )

        tags = [t for t in [lang.lower() if lang else "", channel.category, "github", "trending"] if t]

        record_id = f"gh_{owner}_{repo_name}".lower().replace("-", "_")

        return IntelligenceRecord(
            id=record_id,
            source_type="github_trending",
            channel_id=channel.id,
            channel_name=channel.name,
            category=channel.category,
            is_serendipity=channel.is_serendipity,
            title=title,
            url=html_url,
            author=owner,
            published_at=pushed_at or datetime.now(timezone.utc).isoformat(),
            summary=summary[:1000],
            raw_content=description,
            tags=tags,
            metrics={
                "stars_today": 0,
                "total_stars": stars,
                "forks": forks,
                "language": lang,
            },
        )
