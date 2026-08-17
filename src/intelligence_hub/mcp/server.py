"""FastMCP Server Entrypoint for intelligence-hub."""

import asyncio
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

from intelligence_hub.core.logger import get_logger
from intelligence_hub.mcp import tools

logger = get_logger(__name__)

mcp = FastMCP(
    name="intelligence-hub",
    instructions="Multi-domain intelligence intake, crossover synthesis and report generator.",
)


@mcp.tool()
async def fetch_intelligence_feed(
    category: Optional[str] = None,
    limit_per_channel: Optional[int] = None,
    force_fetch: bool = False,
) -> Dict[str, Any]:
    """Fetches the latest intelligence items across configured feeds (RSS, HN, arXiv) and saves them to LanceDB.
    
    Args:
        category: Optional category filter.
        limit_per_channel: Optional items per channel override.
        force_fetch: If True, forces fetch regardless of interval_hours.
    """
    return await tools.fetch_intelligence_feed(
        category=category, limit_per_channel=limit_per_channel, force_fetch=force_fetch
    )


@mcp.tool()
async def search_intelligence(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Searches stored intelligence records using semantic vector search in LanceDB."""
    return await tools.search_intelligence(query=query, category=category, limit=limit)


@mcp.tool()
async def list_intelligence_records(
    category: Optional[str] = None,
    is_serendipity: Optional[bool] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Lists stored intelligence records with optional category or serendipity filtering."""
    return await tools.list_intelligence_records(
        category=category, is_serendipity=is_serendipity, limit=limit
    )


@mcp.tool()
async def generate_crossover_digest(
    period: str = "daily",
    fetch_latest_first: bool = True,
) -> Dict[str, Any]:
    """Generates an interdisciplinary crossover report combining 80% core tracking and 20% serendipity with WIRED-style narrative Markdown."""
    return await tools.generate_crossover_digest(
        period=period, fetch_latest_first=fetch_latest_first
    )


@mcp.tool()
async def get_feed_status() -> Dict[str, Any]:
    """Returns the current registry of feed channels and LanceDB storage statistics."""
    return await tools.get_feed_status()


def main():
    """Main entrypoint for MCP server."""
    logger.info("Starting intelligence-hub MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
