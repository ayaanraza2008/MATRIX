from pathlib import Path

path = Path("core/integrations/google_workspace.py")
text = path.read_text(encoding="utf-8")

methods = '''    async def verify_connection(self) -> dict:
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
'''

target = "# Global singleton instance"
text = text.replace(target, methods + "\n\n" + target)
path.write_text(text, encoding="utf-8")
print("Successfully patched google_workspace.py")
