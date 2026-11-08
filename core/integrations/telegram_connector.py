"""MATRIX Telegram Bot Integration Connector.
Real Telegram Bot API client for sending alerts, notifications, and receiving mobile commands.
Uses official Telegram Bot HTTP API (https://api.telegram.org/bot<TOKEN>/).
"""
from typing import Dict, Any, List, Optional
import os
import json
import time
from pathlib import Path
import httpx

from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.integrations.telegram")
TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramConnector:
    """Manages real Telegram Bot API communication, secure credential storage, and messaging."""

    def __init__(self):
        self._creds_dir = settings.data_dir / "credentials"
        self._creds_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self._creds_dir / "telegram_token.txt"
        self._chat_id_file = self._creds_dir / "telegram_chat_id.txt"
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._default_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self._load_credentials()

    def _load_credentials(self):
        if self._token_file.exists():
            try:
                t = self._token_file.read_text(encoding="utf-8").strip()
                if t:
                    self._token = t
            except Exception:
                pass
        if self._chat_id_file.exists():
            try:
                cid = self._chat_id_file.read_text(encoding="utf-8").strip()
                if cid:
                    self._default_chat_id = cid
            except Exception:
                pass

    def save_credentials(self, token: str, default_chat_id: Optional[str] = None):
        self._token = token.strip()
        self._token_file.write_text(self._token, encoding="utf-8")
        if default_chat_id:
            self._default_chat_id = default_chat_id.strip()
            self._chat_id_file.write_text(self._default_chat_id, encoding="utf-8")
        logger.info("Telegram Bot credentials saved.")

    def disconnect(self):
        self._token = ""
        self._default_chat_id = ""
        if self._token_file.exists():
            self._token_file.unlink()
        if self._chat_id_file.exists():
            self._chat_id_file.unlink()
        logger.info("Telegram Bot integration disconnected.")

    def is_configured(self) -> bool:
        return bool(self._token)

    def _get_api_url(self, method: str) -> str:
        return f"{TELEGRAM_API_BASE}/bot{self._token}/{method}"

    async def verify_connection(self) -> Dict[str, Any]:
        """Test bot token validity using getMe."""
        if not self._token:
            return {
                "connected": False,
                "status": "NOT_CONFIGURED",
                "message": "Telegram Bot token is not configured."
            }

        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.get(self._get_api_url("getMe"))
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        result = data.get("result", {})
                        return {
                            "connected": True,
                            "status": "CONNECTED",
                            "bot_id": result.get("id"),
                            "bot_username": result.get("username"),
                            "bot_name": result.get("first_name"),
                            "can_join_groups": result.get("can_join_groups"),
                            "can_read_all_group_messages": result.get("can_read_all_group_messages"),
                            "supports_inline_queries": result.get("supports_inline_queries")
                        }
                return {
                    "connected": False,
                    "status": "ERROR",
                    "status_code": res.status_code,
                    "error": res.text
                }
            except Exception as e:
                return {"connected": False, "status": "ERROR", "error": str(e)}

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
    ) -> Dict[str, Any]:
        """Send a real message via Telegram Bot API."""
        if not self._token:
            return {"success": False, "error": "Telegram Bot token is not configured."}

        target_chat_id = chat_id or self._default_chat_id
        if not target_chat_id:
            return {"success": False, "error": "No chat_id provided and no default chat_id configured."}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(
                    self._get_api_url("sendMessage"),
                    json={
                        "chat_id": target_chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": disable_web_page_preview
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        msg_info = data.get("result", {})
                        return {
                            "success": True,
                            "message_id": msg_info.get("message_id"),
                            "chat_id": target_chat_id,
                            "date": msg_info.get("date")
                        }
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def get_updates(self, offset: Optional[int] = None, limit: int = 10) -> Dict[str, Any]:
        """Fetch incoming updates (messages from users)."""
        if not self._token:
            return {"success": False, "error": "Telegram Bot token is not configured."}

        params: Dict[str, Any] = {"limit": limit}
        if offset is not None:
            params["offset"] = offset

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(self._get_api_url("getUpdates"), params=params)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        return {"success": True, "updates": data.get("result", [])}
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Register public HTTPS webhook for push events."""
        if not self._token:
            return {"success": False, "error": "Telegram Bot token is not configured."}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(
                    self._get_api_url("setWebhook"),
                    json={"url": webhook_url}
                )
                return {"success": res.status_code == 200, "data": res.json()}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def delete_webhook(self) -> Dict[str, Any]:
        """Remove existing webhook to revert to polling mode."""
        if not self._token:
            return {"success": False, "error": "Telegram Bot token is not configured."}

        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.post(self._get_api_url("deleteWebhook"))
                return {"success": res.status_code == 200, "data": res.json()}
            except Exception as e:
                return {"success": False, "error": str(e)}


telegram_connector = TelegramConnector()
