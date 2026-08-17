"""Genre-specific Quality Gate validator ensuring concrete technical depth, code snippets, and tables."""

import re
from typing import List, Tuple
from intelligence_hub.core.logger import get_logger
from intelligence_hub.core.models import ArticlePayload

logger = get_logger(__name__)

FORBIDDEN_ABSTRACT_WORDS = ["幾何学的共鳴", "構造的同型性", "境界線の融解が暴く"]


class QualityGate:
    """Validates article payload quality according to its specific genre requirements."""

    def validate(self, payload: ArticlePayload) -> Tuple[bool, List[str]]:
        """Validates payload and returns (is_valid, list_of_issues)."""
        issues: List[str] = []
        content = payload.content

        # 1. Minimum Length Check
        if len(content) < 500:
            issues.append(f"Content too short ({len(content)} chars, minimum 500 required)")

        # 2. Genre-Specific Validation
        if payload.genre == "tech_deep_dive":
            # Code snippet required
            if not ("<pre" in content or "<code>" in content or "```" in content):
                issues.append("Missing code snippet or CLI command (<pre><code> required)")

            # Comparison table required
            if "<table" not in content:
                issues.append("Missing comparison table (<table> required)")

            # Check for excessive abstract buzzwords
            for word in FORBIDDEN_ABSTRACT_WORDS:
                count = content.count(word)
                if count > 1:
                    issues.append(f"Excessive abstract buzzword '{word}' detected ({count} times)")

        elif payload.genre == "crossover_feature":
            # Table required
            if "<table" not in content:
                issues.append("Missing comparison table for Crossover synthesis")

            # Reference link required
            if "<a href=" not in content:
                issues.append("Missing primary source reference links")

        elif payload.genre == "paper_digest":
            # Reference link required
            if "<a href=" not in content:
                issues.append("Missing paper DOI/URL reference link")

        is_valid = len(issues) == 0
        if not is_valid:
            logger.warning(
                f"Quality Gate validation failed for '{payload.title}' ({payload.genre}): {issues}"
            )
        else:
            logger.info(f"Quality Gate PASS for '{payload.title}' ({payload.genre})")

        return is_valid, issues
