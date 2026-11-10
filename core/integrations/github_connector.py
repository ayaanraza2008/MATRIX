"""MATRIX GitHub Developer Integration Connector.
Connects to GitHub REST API v3 using Personal Access Tokens (classic or fine-grained).
Supports repository search, issues, pull requests, commit history, and release status.
"""
from typing import Dict, Any
import os
import httpx

from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.integrations.github")
GITHUB_API_BASE = "https://api.github.com"


class GitHubConnector:
    """Manages real GitHub API communications, token storage, and repository querying."""

    def __init__(self):
        self._creds_dir = settings.data_dir / "credentials"
        self._creds_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self._creds_dir / "github_token.txt"
        self._token = os.getenv("GITHUB_TOKEN", "")
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

    def disconnect(self):
        self._token = ""
        if self._token_file.exists():
            self._token_file.unlink()
        logger.info("GitHub integration disconnected and token removed.")

    def is_configured(self) -> bool:
        return bool(self._token)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MATRIX-Autonomous-Personal-AI"
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def verify_connection(self) -> Dict[str, Any]:
        """Test authentication and fetch user account information & rate limit."""
        if not self._token:
            return {
                "connected": False,
                "status": "NOT_CONFIGURED",
                "message": "GitHub Personal Access Token is not configured."
            }

        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.get(f"{GITHUB_API_BASE}/user", headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    remaining = res.headers.get("x-ratelimit-remaining", "unknown")
                    return {
                        "connected": True,
                        "status": "CONNECTED",
                        "username": data.get("login"),
                        "name": data.get("name"),
                        "public_repos": data.get("public_repos"),
                        "rate_limit_remaining": remaining
                    }
                else:
                    return {
                        "connected": False,
                        "status": "ERROR",
                        "status_code": res.status_code,
                        "error": res.text
                    }
            except Exception as e:
                return {"connected": False, "status": "ERROR", "error": str(e)}

    async def search_repositories(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search public and authorized private GitHub repositories."""
        if not self._token:
            return {"authenticated": False, "message": "GitHub token not configured."}

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{GITHUB_API_BASE}/search/repositories",
                headers=self._get_headers(),
                params={"q": query, "per_page": limit}
            )
            if res.status_code == 200:
                data = res.json()
                items = []
                for r in data.get("items", []):
                    items.append({
                        "name": r.get("full_name"),
                        "description": r.get("description"),
                        "stars": r.get("stargazers_count"),
                        "html_url": r.get("html_url"),
                        "language": r.get("language")
                    })
                return {"success": True, "total_count": data.get("total_count"), "repositories": items}
            return {"success": False, "error": res.text}

    async def list_issues(self, repo_full_name: str, state: str = "open", limit: int = 5) -> Dict[str, Any]:
        """List issues for a specific repository."""
        if not self._token:
            return {"authenticated": False, "message": "GitHub token not configured."}

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues",
                headers=self._get_headers(),
                params={"state": state, "per_page": limit}
            )
            if res.status_code == 200:
                issues = []
                for i in res.json():
                    issues.append({
                        "number": i.get("number"),
                        "title": i.get("title"),
                        "state": i.get("state"),
                        "user": i.get("user", {}).get("login"),
                        "html_url": i.get("html_url"),
                        "created_at": i.get("created_at")
                    })
                return {"success": True, "issues": issues}
            return {"success": False, "error": res.text}

    async def get_commits(self, repo_full_name: str, limit: int = 5) -> Dict[str, Any]:
        """Retrieve recent commit history for a repository."""
        if not self._token:
            return {"authenticated": False, "message": "GitHub token not configured."}

        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits",
                headers=self._get_headers(),
                params={"per_page": limit}
            )
            if res.status_code == 200:
                commits = []
                for c in res.json():
                    commit_obj = c.get("commit", {})
                    commits.append({
                        "sha": c.get("sha")[:7],
                        "message": commit_obj.get("message", "").splitlines()[0] if commit_obj.get("message") else "",
                        "author": commit_obj.get("author", {}).get("name"),
                        "date": commit_obj.get("author", {}).get("date")
                    })
                return {"success": True, "commits": commits}
            return {"success": False, "error": res.text}


# Global singleton instance
github_connector = GitHubConnector()
