"""MATRIX Reference Knowledge Engine.
Exposes searchable knowledge, developer free-tier catalogs, system prompt libraries,
and public REST APIs to MATRIX specialized agents.
"""
from typing import Dict, Any, Optional
from core.reference_knowledge.knowledge_store import reference_knowledge
from config.logging_config import get_logger

logger = get_logger("core.reference_knowledge.engine")


class ReferenceKnowledgeEngine:
    """Provides high-level search and capability lookup into reference repositories."""

    def query_reference_catalog(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Perform verified knowledge lookup into the 6 reference repositories."""
        results = reference_knowledge.search(query, category=category, limit=limit)
        return {
            "query": query,
            "category_filter": category,
            "total_matches": len(results),
            "results": [
                {
                    "id": r.entry_id,
                    "title": r.title,
                    "source_repo": r.source_repo,
                    "category": r.category,
                    "description": r.description,
                    "tags": r.tags,
                    "link": r.link,
                    "details": r.content
                }
                for r in results
            ]
        }

    def get_system_prompt_template(self, prompt_name: str) -> Optional[str]:
        """Retrieve verified system prompt from ERA-System-Prompts catalog."""
        entries = reference_knowledge.search(prompt_name, category="System Prompts", limit=1)
        if entries:
            return entries[0].description
        return None

    def get_public_api(self, domain: str) -> Optional[Dict[str, Any]]:
        """Look up verified public REST API by keyword/domain."""
        entries = reference_knowledge.search(domain, category="Public REST APIs", limit=1)
        if entries:
            e = entries[0]
            return {"name": e.title, "url": e.link, "description": e.description, "tags": e.tags}
        return None


# Global singleton
reference_engine = ReferenceKnowledgeEngine()
reference_knowledge_engine = reference_engine
