"""MATRIX Notion Digital Workspace Integration Connector.
Real Notion API client (https://api.notion.com/v1) using internal integration secret tokens.
Supports searching pages/databases, reading pages, creating notes, and task synchronization.
"""
from typing import Dict, Any, List, Optional
import os
import json
import time
from pathlib import Path
import httpx

from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.integrations.notion")
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionConnector:
    """Manages real Notion API communications, token storage, and workspace querying."""

    def __init__(self):
        self._creds_dir = settings.data_dir / "credentials"
        self._creds_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self._creds_dir / "notion_token.txt"
        self._token = os.getenv("NOTION_API_KEY", "")
        self._load_token()

    def _load_token(self):
        if self._token_file.exists():
            try:
                t = self._token_file.read_text(encoding="utf-8").strip()
                if t:
                    self._token = t
            except Exception:
                pass

    def save_token(self, token: str):
        self._token = token.strip()
        self._token_file.write_text(self._token, encoding="utf-8")
        logger.info("Notion API token saved.")

    def disconnect(self):
        self._token = ""
        if self._token_file.exists():
            self._token_file.unlink()
        logger.info("Notion integration disconnected.")

    def is_configured(self) -> bool:
        return bool(self._token)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }

    async def verify_connection(self) -> Dict[str, Any]:
        """Test Notion API key validity using /v1/users/me."""
        if not self._token:
            return {
                "connected": False,
                "status": "NOT_CONFIGURED",
                "message": "Notion API token is not configured."
            }

        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.get(f"{NOTION_API_BASE}/users/me", headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    bot_info = data.get("bot", {})
                    owner = bot_info.get("owner", {})
                    return {
                        "connected": True,
                        "status": "CONNECTED",
                        "bot_name": data.get("name"),
                        "bot_id": data.get("id"),
                        "workspace_name": bot_info.get("workspace_name"),
                        "owner_type": owner.get("type")
                    }
                return {
                    "connected": False,
                    "status": "ERROR",
                    "status_code": res.status_code,
                    "error": res.text
                }
            except Exception as e:
                return {"connected": False, "status": "ERROR", "error": str(e)}

    async def search(self, query: str = "", filter_type: Optional[str] = None, page_size: int = 10) -> Dict[str, Any]:
        """Search pages and databases in the authorized Notion workspace."""
        if not self._token:
            return {"authenticated": False, "message": "Notion token not configured."}

        payload: Dict[str, Any] = {"page_size": min(page_size, 20)}
        if query:
            payload["query"] = query
        if filter_type in ("page", "database"):
            payload["filter"] = {"value": filter_type, "property": "object"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(f"{NOTION_API_BASE}/search", headers=self._get_headers(), json=payload)
                if res.status_code == 200:
                    data = res.json()
                    results = []
                    for item in data.get("results", []):
                        obj_type = item.get("object")
                        title = "Untitled"
                        if obj_type == "page":
                            # Extract title from properties
                            props = item.get("properties", {})
                            for prop in props.values():
                                if prop.get("type") == "title":
                                    title_parts = prop.get("title", [])
                                    if title_parts:
                                        title = "".join(t.get("plain_text", "") for t in title_parts)
                                    break
                        elif obj_type == "database":
                            title_parts = item.get("title", [])
                            if title_parts:
                                title = "".join(t.get("plain_text", "") for t in title_parts)

                        results.append({
                            "id": item.get("id"),
                            "type": obj_type,
                            "title": title,
                            "url": item.get("url"),
                            "last_edited_time": item.get("last_edited_time")
                        })
                    return {"success": True, "total": len(results), "items": results}
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve details of a specific Notion page."""
        if not self._token:
            return {"authenticated": False, "message": "Notion token not configured."}

        clean_id = page_id.replace("-", "")
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.get(f"{NOTION_API_BASE}/pages/{clean_id}", headers=self._get_headers())
                if res.status_code == 200:
                    return {"success": True, "page": res.json()}
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def create_page(self, parent_page_id: str, title: str, text_content: Optional[str] = None) -> Dict[str, Any]:
        """Create a new page under an existing parent page."""
        if not self._token:
            return {"authenticated": False, "message": "Notion token not configured."}

        clean_parent = parent_page_id.replace("-", "")
        children = []
        if text_content:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text_content}}]
                }
            })

        payload = {
            "parent": {"page_id": clean_parent},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
            "children": children
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(f"{NOTION_API_BASE}/pages", headers=self._get_headers(), json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return {"success": True, "page_id": data.get("id"), "url": data.get("url")}
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}


notion_connector = NotionConnector()
