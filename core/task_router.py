"""MATRIX Task Router.
Maintains a registry of all 16 specialized agents and routes execution steps to the appropriate agent.
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent, AgentResult
from agents.computer.agent import ComputerAgent
from agents.browser.agent import BrowserAgent
from agents.research.agent import ResearchAgent
from agents.coding.agent import CodingAgent
from agents.files.agent import FileAgent
from agents.voice.agent import VoiceAgent
from agents.vision.agent import VisionAgent
from agents.android.agent import AndroidAgent
from agents.system.agent import SystemAgent
from agents.personal.agent import PersonalAgent
from agents.automation.agent import AutomationAgent
from agents.creative.agent import CreativeAgent
from agents.memory.agent import MemoryAgent
from agents.repo_intel.agent import RepoIntelAgent
from agents.security.agent import SecurityAgent
from agents.data_analysis.agent import DataAnalysisAgent
from config.logging_config import get_logger

logger = get_logger("core.router")


class TaskRouter:
    """Routes execution steps to the appropriate specialized agent."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {
            "computer": ComputerAgent(),
            "browser": BrowserAgent(),
            "research": ResearchAgent(),
            "coding": CodingAgent(),
            "files": FileAgent(),
            "voice": VoiceAgent(),
            "vision": VisionAgent(),
            "android": AndroidAgent(),
            "system": SystemAgent(),
            "personal": PersonalAgent(),
            "automation": AutomationAgent(),
            "creative": CreativeAgent(),
            "memory": MemoryAgent(),
            "repo_intel": RepoIntelAgent(),
            "security": SecurityAgent(),
            "data_analysis": DataAnalysisAgent(),
        }

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_name.lower())

    def list_agents(self) -> Dict[str, str]:
        return {name: agent.description for name, agent in self._agents.items()}

    async def dispatch(self, agent_name: str, action: str, parameters: Dict[str, Any]) -> AgentResult:
        agent = self.get_agent(agent_name)
        if not agent:
            logger.warning(f"No specialized agent found for '{agent_name}'. Falling back to system agent.")
            agent = self._agents["system"]

        logger.info(f"Dispatching action '{action}' to agent '{agent.name}'")
        return await agent.execute(action, parameters)


# Global Task Router singleton
task_router = TaskRouter()
