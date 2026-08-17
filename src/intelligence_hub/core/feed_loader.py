"""Feed loader with mtime polling for hot-reloading feeds.yaml."""

import os
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import ValidationError

from intelligence_hub.core.config import CONFIG_DIR
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import FeedChannelConfig

logger = get_logger(__name__)


class FeedRegistryLoader:
    """Loads and caches feed channel configurations with automatic hot-reloading."""

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or (CONFIG_DIR / "feeds.yaml")
        self._last_mtime: float = -1.0
        self._cached_core: List[FeedChannelConfig] = []
        self._cached_serendipity: List[FeedChannelConfig] = []

    def get_all_channels(self) -> List[FeedChannelConfig]:
        """Returns all channels (core + serendipity)."""
        self._ensure_fresh()
        return self._cached_core + self._cached_serendipity

    def get_core_channels(self) -> List[FeedChannelConfig]:
        """Returns core 80% channels."""
        self._ensure_fresh()
        return list(self._cached_core)

    def get_serendipity_channels(self) -> List[FeedChannelConfig]:
        """Returns serendipity 20% channels."""
        self._ensure_fresh()
        return list(self._cached_serendipity)

    def get_channels_by_category(self, category: str) -> List[FeedChannelConfig]:
        """Filters channels by category."""
        return [c for c in self.get_all_channels() if c.category == category]

    def reload(self) -> None:
        """Forces reload regardless of mtime."""
        self._last_mtime = -1.0
        self._ensure_fresh()

    def _ensure_fresh(self) -> None:
        if not self._config_path.exists():
            logger.warning(f"Config file not found: {self._config_path}")
            return

        try:
            current_mtime = os.path.getmtime(self._config_path)
            if current_mtime > self._last_mtime:
                self._load_from_yaml()
                self._last_mtime = current_mtime
        except Exception as e:
            logger.error(f"Failed to check mtime for {self._config_path}: {e}")

    def _load_from_yaml(self) -> None:
        logger.info(f"Loading feed channels from {self._config_path}")
        with open(self._config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        core_raw = data.get("core_channels", [])
        serendipity_raw = data.get("serendipity_channels", [])

        core_channels: List[FeedChannelConfig] = []
        for raw in core_raw:
            try:
                raw["is_serendipity"] = False
                core_channels.append(FeedChannelConfig(**raw))
            except ValidationError as e:
                logger.error(f"Invalid core channel config: {raw.get('id')}: {e}")

        serendipity_channels: List[FeedChannelConfig] = []
        for raw in serendipity_raw:
            try:
                raw["is_serendipity"] = True
                if "category" not in raw:
                    raw["category"] = "serendipity"
                serendipity_channels.append(FeedChannelConfig(**raw))
            except ValidationError as e:
                logger.error(f"Invalid serendipity channel config: {raw.get('id')}: {e}")

        self._cached_core = core_channels
        self._cached_serendipity = serendipity_channels
        logger.info(
            f"Successfully loaded {len(self._cached_core)} core channels and "
            f"{len(self._cached_serendipity)} serendipity channels"
        )
