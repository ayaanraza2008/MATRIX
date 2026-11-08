"""MATRIX Google Workspace Universal Connector.
Implements Google OAuth 2.0 PKCE flow, Gmail read/search/draft/send (with confirmation gate),
Google Calendar event retrieval/creation/modification, automatic token refresh,
and token revocation.
"""
from typing import Dict, Any, List, Optional, Tuple
import os
import json
import time
import base64
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx

from config.settings import settings
from config.logging_config import get_logger
from security.permissions.manager import security_manager

logger = get_logger("core.integrations.google")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events"
]


class GoogleWorkspaceConnector:
    """Manages real Google Workspace OAuth2 credentials and API operations."""

    def __init__(self):
        self._creds_dir = settings.data_dir / "credentials"
        self._creds_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self._creds_dir / "google_token.json"
        self._client_file = self._creds_dir / "google_credentials.json"
        self._client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self._client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self._load_client_secrets()

    def _load_client_secrets(self):
        if self._client_file.exists():
            try:
                data = json.loads(self._client_file.read_text(encoding="utf-8"))
                installed = data.get("installed") or data.get("web") or data
                self._client_id = installed.get("client_id", self._client_id)
                self._client_secret = installed.get("client_secret", self._client_secret)
            except Exception as e:
                logger.warning(f"Could not load google_credentials.json: {e}")

    def is_configured(self) -> bool:
        """Check if OAuth Client ID is configured."""
        return bool(self._client_id)

    def is_authenticated(self) -> bool:
        """Check if active, valid OAuth tokens exist."""
        if not self._token_file.exists():
            return False
        try:
            tokens = json.loads(self._token_file.read_text(encoding="utf-8"))
            return "access_token" in tokens
        except Exception:
            return False

    def get_token_data(self) -> Optional[Dict[str, Any]]:
        if not self._token_file.exists():
            return None
        try:
            return json.loads(self._token_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_tokens(self, tokens: Dict[str, Any]):
        tokens["updated_at"] = time.time()
        self._token_file.write_text(json.dumps(tokens, indent=2), encoding="utf-8")

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").replace("=", "")
        return verifier, challenge

    def get_authorization_url(self, redirect_uri: str = "http://localhost:8000/api/v1/integrations/google/callback") -> Dict[str, Any]:
        """Generate official OAuth 2.0 PKCE consent screen URL."""
        if not self.is_configured():
            return {
                "error": "Google Client ID is not configured. Add GOOGLE_CLIENT_ID or save google_credentials.json.",
                "url": None
            }

        verifier, challenge = self.generate_pkce_pair()
        state = secrets.token_urlsafe(16)

        # Store PKCE state temporarily
        state_file = self._creds_dir / f"pkce_{state}.json"
        state_file.write_text(json.dumps({
            "verifier": verifier,
            "redirect_uri": redirect_uri,
            "created_at": time.time()
        }), encoding="utf-8")

        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state
        }
        query_string = "&".join(f"{k}={httpx.URL('', params={k: v}).query.decode('utf-8')}" for k, v in params.items())
        auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{query_string}"

        return {
            "authorization_url": auth_url,
            "state": state,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri
        }

    def generate_auth_url(self, redirect_uri: str = "http://localhost:8000/api/v1/integrations/google/callback") -> Dict[str, Any]:
        """Alias for get_authorization_url."""
        return self.get_authorization_url(redirect_uri=redirect_uri)

    async def exchange_code(
        self,
        code: str,
        code_verifier: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens with automatic PKCE verifier resolution."""
        # Auto-resolve code_verifier and redirect_uri from PKCE state file if not provided
        if not code_verifier and state:
            state_file = self._creds_dir / f"pkce_{state}.json"
            if state_file.exists():
                try:
                    sdata = json.loads(state_file.read_text(encoding="utf-8"))
                    code_verifier = sdata.get("verifier")
                    if not redirect_uri:
                        redirect_uri = sdata.get("redirect_uri")
                    state_file.unlink(missing_ok=True)
                except Exception:
                    pass

        # If still no code_verifier, look for the latest pkce_*.json
        if not code_verifier:
            pkce_files = sorted(self._creds_dir.glob("pkce_*.json"), key=os.path.getmtime, reverse=True)
            if pkce_files:
                try:
                    sdata = json.loads(pkce_files[0].read_text(encoding="utf-8"))
                    code_verifier = sdata.get("verifier")
                    if not redirect_uri:
                        redirect_uri = sdata.get("redirect_uri")
                    pkce_files[0].unlink(missing_ok=True)
                except Exception:
                    pass

        redirect_uri = redirect_uri or "http://localhost:8000/api/v1/integrations/google/callback"
        code_verifier = code_verifier or ""

        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "client_id": self._client_id,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
            if self._client_secret:
                payload["client_secret"] = self._client_secret

            res = await client.post(GOOGLE_TOKEN_ENDPOINT, data=payload)
            if res.status_code == 200:
                tokens = res.json()
                self.save_tokens(tokens)
                logger.info("Successfully exchanged Google OAuth authorization code.")
                return {"success": True, "status": "CONNECTED"}
            else:
                logger.error(f"Google OAuth token exchange failed (HTTP {res.status_code}): {res.text}")
                return {"success": False, "error": res.text, "status_code": res.status_code}

    async def get_valid_access_token(self) -> Optional[str]:
        """Retrieve valid access token, automatically refreshing if expired."""
        tokens = self.get_token_data()
        if not tokens or "access_token" not in tokens:
            return None

        # Check token expiry (default expiry is 3600 seconds)
        updated_at = tokens.get("updated_at", 0)
        expires_in = tokens.get("expires_in", 3600)
        if time.time() - updated_at > (expires_in - 120):
            # Token expired or expiring in 2 min -> Refresh
            refresh_ok = await self.refresh_token()
            if not refresh_ok:
                return None
            tokens = self.get_token_data()

        return tokens.get("access_token")

    async def refresh_token(self) -> bool:
        """Refresh Google OAuth access token using refresh_token."""
        tokens = self.get_token_data()
        if not tokens or "refresh_token" not in tokens:
            return False

        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "client_id": self._client_id,
                "refresh_token": tokens["refresh_token"],
                "grant_type": "refresh_token"
            }
            if self._client_secret:
                payload["client_secret"] = self._client_secret

            res = await client.post(GOOGLE_TOKEN_ENDPOINT, data=payload)
            if res.status_code == 200:
                new_tokens = res.json()
                # Retain original refresh_token if Google does not return a new one
                if "refresh_token" not in new_tokens:
                    new_tokens["refresh_token"] = tokens["refresh_token"]
                self.save_tokens(new_tokens)
                logger.info("Successfully refreshed Google OAuth access token.")
                return True
            else:
                logger.warning(f"Failed to refresh Google token: {res.text}")
                return False

    async def revoke(self) -> bool:
        """Revoke current authorization and delete stored tokens."""
        tokens = self.get_token_data()
        token_to_revoke = tokens.get("refresh_token") or tokens.get("access_token") if tokens else None
        if token_to_revoke:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(GOOGLE_REVOKE_ENDPOINT, params={"token": token_to_revoke})
            except Exception:
                pass

        if self._token_file.exists():
            self._token_file.unlink()
        logger.info("Google Workspace authorization revoked.")
        return True

    # -------------------------------------------------------------
    # GMAIL OPERATIONS
    # -------------------------------------------------------------
    async def search_emails(self, query: str = "is:unread", max_results: int = 5) -> Dict[str, Any]:
        """Search Gmail inbox using standard Gmail search operators."""
        token = await self.get_valid_access_token()
        if not token:
            return {
                "authenticated": False,
                "status": "NOT_CONFIGURED",
                "message": "Google Workspace is not authenticated. Please authenticate in Integrations settings."
            }

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                f"{GMAIL_API_BASE}/messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": query, "maxResults": max_results}
            )
            if res.status_code != 200:
                return {"authenticated": True, "success": False, "error": res.text}

            data = res.json()
            messages = data.get("messages", [])
            headers_list = []

            for msg_meta in messages[:max_results]:
                mid = msg_meta.get("id")
                m_res = await client.get(
                    f"{GMAIL_API_BASE}/messages/{mid}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]}
                )
                if m_res.status_code == 200:
                    m_data = m_res.json()
                    hdrs = {h["name"]: h["value"] for h in m_data.get("payload", {}).get("headers", [])}
                    headers_list.append({
                        "id": mid,
                        "snippet": m_data.get("snippet", ""),
                        "from": hdrs.get("From", "Unknown"),
                        "subject": hdrs.get("Subject", "(No Subject)"),
                        "date": hdrs.get("Date", "")
                    })

            return {
                "authenticated": True,
                "success": True,
                "total_matched": len(messages),
                "messages": headers_list
            }

    async def draft_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Create a draft email in Gmail without sending."""
        token = await self.get_valid_access_token()
        if not token:
            return {"authenticated": False, "message": "Google Workspace is not authenticated."}

        raw_content = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
        encoded = base64.urlsafe_b64encode(raw_content.encode("utf-8")).decode("ascii")

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.post(
                f"{GMAIL_API_BASE}/drafts",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"message": {"raw": encoded}}
            )
            if res.status_code in (200, 201):
                return {"success": True, "draft_id": res.json().get("id"), "to": to, "subject": subject}
            return {"success": False, "error": res.text}

    async def send_email(self, to: str, subject: str, body: str, confirmation_token: Optional[str] = None) -> Dict[str, Any]:
        """Send an email via Gmail API. Enforces Level 4 Supervised confirmation gate."""
        # Check security policy
        eval_res = security_manager.evaluate_action(
            action="send_external_email",
            target=to,
            details={"to": to, "subject": subject}
        )
        if eval_res.get("requires_confirmation") and not confirmation_token:
            return {
                "success": False,
                "requires_confirmation": True,
                "request_id": eval_res.get("request_id"),
                "message": f"Action blocked by Level 4 Supervised Policy: Sending email to '{to}' requires user confirmation."
            }

        token = await self.get_valid_access_token()
        if not token:
            return {"authenticated": False, "message": "Google Workspace is not authenticated."}

        raw_content = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
        encoded = base64.urlsafe_b64encode(raw_content.encode("utf-8")).decode("ascii")

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{GMAIL_API_BASE}/messages/send",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"raw": encoded}
            )
            if res.status_code in (200, 201):
                return {"success": True, "sent": True, "message_id": res.json().get("id"), "to": to}
            return {"success": False, "error": res.text}

    # -------------------------------------------------------------
    # CALENDAR OPERATIONS
    # -------------------------------------------------------------
    async def list_calendar_events(self, max_results: int = 10, days_ahead: int = 7) -> Dict[str, Any]:
        """Retrieve upcoming events from Google Calendar."""
        token = await self.get_valid_access_token()
        if not token:
            return {
                "authenticated": False,
                "status": "NOT_CONFIGURED",
                "message": "Google Workspace is not authenticated. Please authenticate in Integrations settings."
            }

        now = datetime.now(timezone.utc).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                f"{CALENDAR_API_BASE}/calendars/primary/events",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin": now,
                    "timeMax": future,
                    "maxResults": max_results,
                    "singleEvents": "true",
                    "orderBy": "startTime"
                }
            )
            if res.status_code != 200:
                return {"authenticated": True, "success": False, "error": res.text}

            data = res.json()
            events = []
            for item in data.get("items", []):
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                events.append({
                    "id": item.get("id"),
                    "summary": item.get("summary", "(No Title)"),
                    "start": start,
                    "end": end,
                    "location": item.get("location"),
                    "html_link": item.get("htmlLink")
                })

            return {
                "authenticated": True,
                "success": True,
                "events_count": len(events),
                "events": events
            }

    async def create_calendar_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = ""
    ) -> Dict[str, Any]:
        """Create a new event on Google Calendar."""
        token = await self.get_valid_access_token()
        if not token:
            return {"authenticated": False, "message": "Google Workspace is not authenticated."}

        event_payload = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_time if "T" in start_time else f"{start_time}T09:00:00Z"},
            "end": {"dateTime": end_time if "T" in end_time else f"{end_time}T10:00:00Z"}
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.post(
                f"{CALENDAR_API_BASE}/calendars/primary/events",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=event_payload
            )
            if res.status_code in (200, 201):
                item = res.json()
                return {"success": True, "event_id": item.get("id"), "summary": summary, "html_link": item.get("htmlLink")}
            return {"success": False, "error": res.text}

    async def update_calendar_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update/modify an existing Google Calendar event."""
        token = await self.get_valid_access_token()
        if not token:
            return {"authenticated": False, "message": "Google Workspace is not authenticated."}

        patch_payload: Dict[str, Any] = {}
        if summary is not None:
            patch_payload["summary"] = summary
        if description is not None:
            patch_payload["description"] = description
        if location is not None:
            patch_payload["location"] = location
        if start_time is not None:
            patch_payload["start"] = {"dateTime": start_time if "T" in start_time else f"{start_time}T09:00:00Z"}
        if end_time is not None:
            patch_payload["end"] = {"dateTime": end_time if "T" in end_time else f"{end_time}T10:00:00Z"}

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.patch(
                f"{CALENDAR_API_BASE}/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=patch_payload
            )
            if res.status_code == 200:
                item = res.json()
                return {"success": True, "event_id": item.get("id"), "summary": item.get("summary"), "updated": True}
            return {"success": False, "error": res.text, "status_code": res.status_code}

    async def delete_calendar_event(self, event_id: str) -> Dict[str, Any]:
        """Delete an event from Google Calendar."""
        token = await self.get_valid_access_token()
        if not token:
            return {"authenticated": False, "message": "Google Workspace is not authenticated."}

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.delete(
                f"{CALENDAR_API_BASE}/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if res.status_code in (200, 204):
                return {"success": True, "event_id": event_id, "deleted": True}
            return {"success": False, "error": res.text, "status_code": res.status_code}

    async def check_upcoming_notifications(self, alert_window_minutes: int = 30) -> List[Dict[str, Any]]:
        """Inspect upcoming calendar events within next alert_window_minutes."""
        res = await self.list_calendar_events(max_results=10, days_ahead=1)
        if not res.get("success"):
            return []

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(minutes=alert_window_minutes)
        alerts_triggered = []

        for ev in res.get("events", []):
            start_str = ev.get("start")
            if not start_str:
                continue
            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if now <= start_dt <= cutoff:
                    alerts_triggered.append({
                        "event_id": ev.get("id"),
                        "summary": ev.get("summary"),
                        "start": start_str,
                        "location": ev.get("location"),
                        "minutes_until": round((start_dt - now).total_seconds() / 60)
                    })
            except Exception:
                pass

        return alerts_triggered

    def get_setup_wizard(self) -> Dict[str, Any]:
        """Return clear, actionable setup wizard instructions for Google Cloud Console OAuth setup."""
        return {
            "integration": "google_workspace",
            "name": "Google Workspace (Gmail & Calendar)",
            "status": "CONFIGURED" if self.is_configured() else "NOT_CONFIGURED",
            "authenticated": self.is_authenticated(),
            "credentials_file": str(self._client_file),
            "token_file": str(self._token_file),
            "step_1": "Go to Google Cloud Console: https://console.cloud.google.com/",
            "step_2": "Create or select project 'Matrix-AI-Workstation'",
            "step_3": "Enable 'Gmail API' and 'Google Calendar API' in APIs & Services > Library",
            "step_4": "Configure OAuth Consent Screen (External), add scopes: gmail.readonly, gmail.compose, gmail.send, calendar.events",
            "step_5": "Create Credentials > OAuth Client ID (Web Application)",
            "step_6": "Add Authorized Redirect URI: http://localhost:8000/api/v1/integrations/google/callback",
            "step_7": f"Save client credentials JSON to {self._client_file} or set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET env vars",
            "step_8": "Initiate authorization via GET /api/v1/integrations/google/auth-url and approve in browser"
        }


    async def verify_connection(self) -> dict:
        """Verify Google Workspace connection and token validity."""
        if not self.is_configured():
            return {
                "connected": False,
                "status": "NOT_CONFIGURED",
                "message": "Google Workspace OAuth2 credentials not configured."
            }
        if not self.is_authenticated():
            return {
                "connected": False,
                "status": "NEEDS_AUTH",
                "message": "Google Workspace is configured but not authenticated."
            }
        token = await self.get_valid_access_token()
        if token:
            return {
                "connected": True,
                "status": "CONNECTED",
                "message": "Google Workspace OAuth2 token verified and active."
            }
        return {
            "connected": False,
            "status": "EXPIRED",
            "message": "Google Workspace token expired and refresh failed."
        }

    async def list_messages(self, query: str = "is:unread", max_results: int = 5) -> dict:
        """Alias for search_emails to support message listing."""
        return await self.search_emails(query=query, max_results=max_results)


# Global singleton instance
google_workspace = GoogleWorkspaceConnector()
