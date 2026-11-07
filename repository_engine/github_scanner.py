"""MATRIX Repository Intelligence: GitHub Scanner & Collector.
Scans and parses the verified 65 GitHub Starred Repositories inventory.
"""
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from pydantic import BaseModel
from config.logging_config import get_logger

logger = get_logger("repo_intel.scanner")


class StarredRepository(BaseModel):
    full_name: str
    html_url: str
    description: str
    language: str
    stars: int
    license: str
    topics: List[str] = []
    archived: bool = False
    updated_at: Optional[str] = None


class GitHubScanner:
    """Loads, paginates, and scans GitHub repository inventories."""

    def __init__(self, inventory_path: Optional[Path] = None):
        self.inventory_path = inventory_path or Path("starred_repos_inventory.json")

    def load_inventory(self) -> List[StarredRepository]:
        """Load and parse the verified starred repositories list."""
        if not self.inventory_path.exists():
            logger.warning(f"Inventory file '{self.inventory_path}' not found.")
            return []

        try:
            with open(self.inventory_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            repos = []
            for item in raw_data:
                repos.append(StarredRepository(
                    full_name=item.get("full_name", ""),
                    html_url=item.get("html_url", ""),
                    description=item.get("description") or "No description provided.",
                    language=item.get("language") or "N/A",
                    stars=item.get("stars", 0),
                    license=item.get("license") or "Unknown",
                    topics=item.get("topics", []),
                    archived=item.get("archived", False),
                    updated_at=item.get("updated_at")
                ))

            logger.info(f"Loaded {len(repos)} verified repositories from inventory.")
            return repos
        except Exception as e:
            logger.error(f"Error loading inventory: {e}")
            return []

    def find_by_name(self, name_query: str) -> List[StarredRepository]:
        """Search repository by owner or repo name."""
        all_repos = self.load_inventory()
        query_low = name_query.lower()
        return [r for r in all_repos if query_low in r.full_name.lower()]


# Global scanner singleton
github_scanner = GitHubScanner()
