"""Scheduler module for intelligence-hub periodic runs and external automation."""

import asyncio
from typing import Any, Dict
from intelligence_hub.mcp.tools import fetch_intelligence_feed, generate_crossover_digest


async def run_periodic_intake(period: str = "daily") -> Dict[str, Any]:
    """Runs a complete intake and crossover synthesis pass. Useful for cron/cli triggers."""
    fetch_res = await fetch_intelligence_feed()
    digest_res = await generate_crossover_digest(period=period, fetch_latest_first=False)
    return {
        "fetch_result": fetch_res,
        "digest_result": digest_res,
    }


def main():
    """CLI entrypoint for standalone background job runner."""
    asyncio.run(run_periodic_intake())


__all__ = ["run_periodic_intake", "main"]
