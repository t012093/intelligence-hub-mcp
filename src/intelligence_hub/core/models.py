"""Core data models for intelligence-hub-mcp."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ChannelType = Literal["rss", "api_hn", "github_trending", "arxiv_query"]

ArticleGenre = Literal[
    "tech_deep_dive",      # ① OSS・ツール徹底解剖
    "paper_digest",        # ② 先端論文・サイエンス解説
    "protocol_security",   # ③ プロトコル・セキュリティ構造論
    "crossover_feature",   # ④ 異分野交差点ナラティブ
]


class FeedChannelConfig(BaseModel):
    """Configuration for a single intake channel."""
    id: str
    category: str
    name: str
    type: ChannelType
    url: Optional[str] = None
    endpoint: Optional[str] = None
    languages: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    limit: int = 20
    interval_hours: int = 12
    is_serendipity: bool = False


class IntelligenceRecord(BaseModel):
    """A single normalized intelligence record (article, trend, paper, post)."""
    id: str
    source_type: str
    channel_id: str
    channel_name: str
    category: str
    is_serendipity: bool = False
    title: str
    url: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    summary: str
    raw_content: Optional[str] = None  # Deep Fetch: README or Full Abstract
    genre_hint: Optional[ArticleGenre] = None
    tags: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CrossoverTheme(BaseModel):
    """An intersection / crossover finding between two or more domains."""
    theme_title: str
    domains: List[str]
    core_concept: str
    synergy_description: str
    actionable_implications: List[str]
    referenced_record_ids: List[str] = Field(default_factory=list)
    suggested_themes: List[str] = Field(default_factory=list)
    suggested_tags: List[str] = Field(default_factory=list)


class CrossoverDigest(BaseModel):
    """Complete synthesized crossover digest."""
    digest_id: str
    generated_at: str
    period: str  # 'daily' | 'weekly'
    genre: ArticleGenre = "crossover_feature"
    core_insights: List[Dict[str, Any]] = Field(default_factory=list)
    serendipity_finds: List[Dict[str, Any]] = Field(default_factory=list)
    crossover_themes: List[CrossoverTheme] = Field(default_factory=list)
    markdown_report: str
    suggested_themes: List[str] = Field(default_factory=list)
    suggested_tags: List[str] = Field(default_factory=list)
    source_records: List[str] = Field(default_factory=list)


class ArticlePayload(BaseModel):
    """Normalized payload ready for Coral Magazine or CMS publication."""
    title: str
    slug: str
    content: str
    excerpt: str
    status: str = "draft"
    genre: ArticleGenre = "tech_deep_dive"
    themes: List[str] = Field(default_factory=lambda: ["テクノロジー"])
    tags: List[str] = Field(default_factory=list)
    reading_time: int = 8
    author_id: str
