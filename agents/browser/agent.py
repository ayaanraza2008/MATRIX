"""MATRIX Browser Agent.
Executes real browser automation via Playwright: website navigation, real web search,
page text extraction, form interaction, and DOM verification.
"""
from typing import Dict, Any, List
import time
import asyncio
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("agents.browser")


class BrowserAgent(BaseAgent):
    """Automates web browsing using Playwright headless Chromium."""

    def __init__(self):
        super().__init__(
            name="browser",
            description="Performs real web browsing, search queries, page extraction, and web snapshot verification.",
            max_autonomy_level=2
        )
        self.output_dir = settings.cache_dir / "browser"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("query", parameters.get("raw_prompt", "")).lower()

        # 1. Search Query
        if "search" in action_lower or any(w in raw_prompt for w in ["search", "find online", "look up"]):
            query = parameters.get("query", parameters.get("search_query", raw_prompt))
            return await self._search_web(query, start_time)

        # 2. Navigate URL
        target_url = parameters.get("url", "")
        if not target_url:
            # Extract URL from prompt if present
            import re
            urls = re.findall(r'https?://[^\s]+', raw_prompt)
            target_url = urls[0] if urls else "https://news.ycombinator.com"

        return await self._navigate_url(target_url, start_time)

    async def _navigate_url(self, url: str, start_time: float) -> AgentResult:
        """Navigate to real website using Playwright, extract title, text, and page screenshot."""
        logger.info(f"Navigating to {url} via Playwright...")
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                # Set reasonable timeout
                await page.goto(url, timeout=12000, wait_until="domcontentloaded")
                
                title = await page.title()
                # Extract main text
                text_content = await page.inner_text("body")
                # Clean up text
                cleaned_text = " ".join(text_content.split())[:2000]

                # Save page snapshot
                shot_path = self.output_dir / f"web_{int(time.time() * 1000)}.png"
                await page.screenshot(path=str(shot_path))

                await browser.close()
                latency = (time.perf_counter() - start_time) * 1000

                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="navigate_url",
                    data={
                        "url": url,
                        "title": title,
                        "text_sample": cleaned_text[:500],
                        "total_chars": len(text_content),
                        "screenshot": str(shot_path)
                    },
                    verification={"verified": True, "http_loaded": True, "title_found": bool(title)},
                    execution_time_ms=round(latency, 2)
                )
        except Exception as e:
            logger.warning(f"Playwright navigation failed ({e}); attempting resilient HTTP fallback...")
            # Fallback to httpx if browser context blocked
            try:
                import httpx
                async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 MATRIX Agent"})
                    title = "Web Resource"
                    if "<title>" in resp.text:
                        title = resp.text.split("<title>")[1].split("</title>")[0].strip()
                    latency = (time.perf_counter() - start_time) * 1000
                    return AgentResult(
                        success=(resp.status_code == 200),
                        agent_name=self.name,
                        action_taken="navigate_url_fallback",
                        data={"url": url, "title": title, "status_code": resp.status_code, "length": len(resp.text)},
                        verification={"verified": resp.status_code == 200},
                        execution_time_ms=round(latency, 2)
                    )
            except Exception as e2:
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="navigate_url",
                    error=f"Navigation failed: {e} | Fallback: {e2}",
                    verification={"verified": False},
                    execution_time_ms=round(latency, 2)
                )

    async def _search_web(self, query: str, start_time: float) -> AgentResult:
        """Execute real search query via Bing and extract top organic results with URLs and snippets."""
        logger.info(f"Executing web search for: '{query}' via Playwright...")
        encoded_query = query.replace(' ', '+')
        search_url = f"https://www.bing.com/search?q={encoded_query}"
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(search_url, timeout=12000, wait_until="domcontentloaded")

                results = []
                cards = await page.query_selector_all("li.b_algo")
                for card in cards[:5]:
                    a_elem = await card.query_selector("h2 a")
                    caption_elem = await card.query_selector(".b_caption")
                    
                    if a_elem:
                        title_text = (await a_elem.text_content()).strip()
                        raw_href = await a_elem.get_attribute("href") or ""
                        snippet_text = (await caption_elem.text_content()).strip() if caption_elem else ""
                        
                        # Clean up snippet
                        cleaned_snip = " ".join(snippet_text.split())[:300]
                        
                        if title_text:
                            results.append({
                                "title": title_text,
                                "url": raw_href,
                                "snippet": cleaned_snip
                            })

                await browser.close()
                latency = (time.perf_counter() - start_time) * 1000

                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="search_web",
                    data={
                        "query": query,
                        "results": results,
                        "count": len(results)
                    },
                    verification={"verified": True, "results_found": len(results) > 0},
                    execution_time_ms=round(latency, 2)
                )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="search_web",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def verify(self, action: str, result: Any) -> bool:
        """Verify web action result."""
        if isinstance(result, dict):
            return bool(result.get("title") or result.get("results") or result.get("count", 0) > 0)
        return bool(result)
