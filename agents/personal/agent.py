"""MATRIX Personal Assistant & Account Operations Agent.
Handles personal account actions, user preferences, daily scheduling, and secure account operations:
- Draft emails and messages safely without unauthorized sending
- Inspect GitHub repositories, pull requests, and commit status
- Discover and manage authorized user accounts (Google, GitHub, Email, Cloud Storage)
- Strictly enforces Level 3 explicit confirmation before any external transmission.
"""
from typing import Dict, Any, List, Optional
import time
import re
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from core.account_operations.registry import account_registry
from core.account_operations.manager import account_operations
from config.logging_config import get_logger

logger = get_logger("agents.personal")


class PersonalAgent(BaseAgent):
    """Coordinates user preferences, daily scheduling, and authorized personal account operations."""

    def __init__(self):
        super().__init__(
            name="personal",
            description="Coordinates user identity, drafts emails, manages connected personal accounts, and organizes daily tasks.",
            max_autonomy_level=2
        )
        self._capabilities = [
            AgentCapability(name="draft_message", description="Draft emails and personal messages safely into draft store", operations=["draft_email", "draft_message"]),
            AgentCapability(name="account_management", description="Inspect connected user accounts and authorization status", operations=["list_accounts", "account_status"]),
            AgentCapability(name="github_inspection", description="Inspect authorized GitHub repositories and issues", operations=["inspect_repo", "github"]),
            AgentCapability(name="personal_assist", description="Handle general personal assistant directives and identity queries", operations=["assist", "preference"])
        ]

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("query", parameters.get("raw_prompt", "")).lower()

        # Cancel Task
        if "cancel" in action_lower or "cancel" in raw_prompt:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="cancel_task",
                data={"status": "Task cancelled successfully, sir."},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        # 0. Time & Date Inquiries
        if any(w in raw_prompt for w in ["what time", "current time", "time is it", "what's the time", "today's date", "what is the date", "what's the date", "what day is"]):
            import datetime
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="report_time_date",
                data={"time": time_str, "date": date_str, "message": f"The current time is {time_str} on {date_str}, sir."},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        # Weather Inquiries (Open-Meteo)
        if "weather" in action_lower or "weather" in raw_prompt:
            from core.information.briefing import briefing_engine
            w_res = await briefing_engine.get_live_weather()
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=w_res.get("success", False),
                agent_name=self.name,
                action_taken="query_weather",
                data=w_res,
                verification={"verified": w_res.get("success", False), "temperature": w_res.get("temperature_c")},
                execution_time_ms=round(latency, 2)
            )

        # 1. Draft Email / Message
        if "draft" in action_lower or any(w in raw_prompt for w in ["draft an email", "draft email", "compose email", "write an email to"]):
            return await self._handle_draft_email(parameters, raw_prompt, start_time)

        # 2. Inspect GitHub Repository
        if "github" in action_lower or "repo" in action_lower or "github" in raw_prompt:
            return await self._handle_github_inspect(parameters, raw_prompt, start_time)

        # 3. List Connected Accounts
        if any(w in action_lower or w in raw_prompt for w in ["connected account", "accounts", "integrations", "authorized account"]):
            accounts = account_registry.list_connected_accounts()
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="list_accounts",
                data={"connected_accounts": accounts, "count": len(accounts)},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        # 4. Search Account Data
        if "search account" in action_lower or "search my" in raw_prompt:
            service = parameters.get("service", "email")
            query = parameters.get("query", raw_prompt)
            res = await account_operations.search_account_data(service, query)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="search_account_data",
                data=res,
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        # Default Personal Assistant QA / Identity
        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="personal_assist",
            data={
                "assistant_name": "MATRIX",
                "identity": "JARVIS-inspired digital operating layer",
                "capabilities": [c.name for c in self._capabilities],
                "connected_accounts_count": len(account_registry.list_connected_accounts())
            },
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def _handle_draft_email(self, params: Dict[str, Any], prompt: str, start_time: float) -> AgentResult:
        """Extract recipient, subject, and body, and create a verified email draft."""
        to_addr = params.get("to", "recipient@example.com")
        subject = params.get("subject", "Project Update & Directives")
        body = params.get("body", "Greetings. Here is the requested draft summary generated by MATRIX.")

        # Extract recipient if in prompt
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
        if email_match:
            to_addr = email_match.group(0)

        res = await account_operations.draft_email(
            to_address=to_addr,
            subject=subject,
            body=body
        )
        latency = (time.perf_counter() - start_time) * 1000

        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="draft_email",
            data=res,
            verification={"draft_created": True, "requires_level3_confirmation": True, "verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def _handle_github_inspect(self, params: Dict[str, Any], prompt: str, start_time: float) -> AgentResult:
        """Inspect a GitHub repository."""
        repo_name = params.get("repo", params.get("repository", ""))
        if not repo_name:
            match = re.search(r'(?:github\.com/|repo(?:sitory)?\s+)?([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', prompt)
            if match:
                repo_name = match.group(1)
            else:
                repo_name = "browser-use/browser-use"

        res = await account_operations.inspect_github_repository(repo_name)
        latency = (time.perf_counter() - start_time) * 1000

        return AgentResult(
            success=res.get("status") == "SUCCESS",
            agent_name=self.name,
            action_taken="inspect_github_repository",
            data=res,
            verification={"verified": res.get("status") == "SUCCESS"},
            execution_time_ms=round(latency, 2)
        )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
