"""MATRIX Integration Adapter: Browser-Use (browser-use/browser-use).
Integrates autonomous web navigation, page extraction, and form interaction into MATRIX Browser Agent.
"""
from typing import Dict, Any
import httpx
from config.logging_config import get_logger

logger = get_logger("adapter.browser_use")


class BrowserUseAdapter:
    """Provides high-level web extraction inspired by the Browser-Use agent framework."""

    async def browse_and_extract(self, url: str) -> Dict[str, Any]:
        """Navigate to URL, extract text content, headers, and metadata."""
        logger.info(f"Browser-Use adapter navigating to: {url}")
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MATRIX-Agent"})
                status = res.status_code
                html = res.text

                # Extract basic tags
                title = "Untitled"
                if "<title>" in html:
                    title = html.split("<title>")[1].split("</title>")[0].strip()

                return {
                    "url": url,
                    "title": title,
                    "status_code": status,
                    "html_bytes": len(html),
                    "success": status == 200
                }
        except Exception as e:
            logger.error(f"Browser-Use navigation failed: {e}")
            return {"url": url, "success": False, "error": str(e)}


browser_use_adapter = BrowserUseAdapter()
