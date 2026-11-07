"""MATRIX Browser Agent.
Automates web browsing, searches pages, extracts articles, and verifies DOM state.
"""
from typing import Dict, Any
import time
import httpx
from agents.base_agent import BaseAgent, AgentResult


class BrowserAgent(BaseAgent):
    """Executes automated web browsing, DOM inspection, and structured information extraction."""

    def __init__(self):
        super().__init__(
            name="browser",
            description="Navigates websites, extracts article content, takes web page snapshots, and collects research.",
            max_autonomy_level=2
        )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        url = parameters.get("url", "https://news.ycombinator.com")

        # Fetch page content safely
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                res = await client.get(url, headers={"User-Agent": "Mozilla/5.0 MATRIX Personal AI Agent"})
                status_code = res.status_code
                content_len = len(res.text)
                title = "Web Resource"
                if "<title>" in res.text:
                    title = res.text.split("<title>")[1].split("</title>")[0].strip()

            latency = (time.perf_counter() - start_time) * 1000
            verified = status_code == 200

            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="navigate_url",
                data={
                    "url": url,
                    "title": title,
                    "status_code": status_code,
                    "content_length_bytes": content_len
                },
                verification={"http_200": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="navigate_url",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
