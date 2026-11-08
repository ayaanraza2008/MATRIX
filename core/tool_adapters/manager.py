"""MATRIX Tool Adapter Manager.
Coordinates the lifecycle, discovery, execution, health checks, and self-healing
of all registered capability adapters across the 65 repositories.
"""
from typing import Dict, Any, List, Optional
import time
from core.tool_adapters.base_adapter import BaseAdapter, AdapterExecutionResult
from core.tool_adapters.browser_use_adapter import BrowserUseAdapter
from core.tool_adapters.hexstrike_adapter import HexStrikeAdapter
from core.tool_adapters.voice_studio_adapter import VoiceStudioAdapter
from core.tool_adapters.gravitas_adapter import GravitasCodeAdapter
from core.tool_adapters.mobile_mcp_adapter import MobileMcpAdapter
from core.tool_adapters.context_memory_adapter import ContextMemoryAdapter
from core.tool_adapters.free_llm_adapter import FreeLlmRouterAdapter
from core.tool_adapters.diagram_design_adapter import DiagramDesignAdapter
from core.tool_adapters.system_telemetry_adapter import SystemTelemetryAdapter
from core.tool_adapters.scientific_research_adapter import ScientificResearchAdapter
from core.tool_adapters.coding_dev_adapters import (
    HermesAgentAdapter,
    ReaReverseEngineeringAdapter,
    CapCaptureAdapter,
    OpenDesignAdapter,
    NotAiRuleAdapter,
    JcodeRunnerAdapter,
    OpenCluelySymbolsAdapter,
    AgencyAgentsAdapter,
)
from core.tool_adapters.browser_web_adapters import (
    EgoLiteWebAdapter,
    ObscuraCrawlerAdapter,
    FreeClaudeCodeAdapter,
    GodsEyeViewAdapter,
)
from core.tool_adapters.security_mcp_adapters import (
    NightcrawlerSecurityAdapter,
    EccCybersecurityAdapter,
    AnthropicSecuritySkillsAdapter,
    KaliGptDefenseAdapter,
)
from core.tool_adapters.voice_audio_adapters import (
    ChatterboxAcousticsAdapter,
    AtticusAudioAdapter,
    OpenWhisprAdapter,
    OmniVoiceSynthesisAdapter,
    HandyVoiceAssistantAdapter,
)
from core.tool_adapters.memory_llm_adapters import (
    AgentMemoryStorageAdapter,
    DshGodLlmAdapter,
    StrataProviderAdapter,
)
from core.tool_adapters.creative_media_adapters import (
    JarvisUltimateMediaAdapter,
    PenpotVectorDesignAdapter,
    ComfyUiWorkflowAdapter,
)
from core.tool_adapters.science_research_adapters import (
    GeoSleuthResearchAdapter,
)
from core.tool_adapters.workflow_productivity_adapters import (
    ImmichMediaAdapter,
    Harness2WorkflowAdapter,
    AutomatonWorkflowAdapter,
    SparkAutomationAdapter,
    RakazoFileOrganizerAdapter,
    HereticTextPipelineAdapter,
    YoutubeAutomationAdapter,
    ChatwootWebhookAdapter,
    CalDiySchedulerAdapter,
    OpenProjectTrackerAdapter,
    AppFlowyDocumentAdapter,
    OpenSeoAuditAdapter,
    HeyGemPresentationAdapter,
    PaperclipDocumentAdapter,
    OpenGenerativeAiAdapter,
)
from core.autonomy_policy.policy import autonomy_policy, ActionCategory
from core.repository_intelligence.resource_guard import resource_guard
from config.logging_config import get_logger

logger = get_logger("core.tool_adapters.manager")


class AdapterManager:
    """Central registry and execution manager for all repository tool adapters."""

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}
        self._repo_map: Dict[str, BaseAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self):
        """Instantiate and index all default core adapters."""
        default_list: List[BaseAdapter] = [
            # 10 Core Installed Integrations (Preserved)
            BrowserUseAdapter(),
            HexStrikeAdapter(),
            VoiceStudioAdapter(),
            GravitasCodeAdapter(),
            MobileMcpAdapter(),
            ContextMemoryAdapter(),
            FreeLlmRouterAdapter(),
            DiagramDesignAdapter(),
            SystemTelemetryAdapter(),
            ScientificResearchAdapter(),
            # 8 Coding & DevTools Adapters
            HermesAgentAdapter(),
            ReaReverseEngineeringAdapter(),
            CapCaptureAdapter(),
            OpenDesignAdapter(),
            NotAiRuleAdapter(),
            JcodeRunnerAdapter(),
            OpenCluelySymbolsAdapter(),
            AgencyAgentsAdapter(),
            # 4 Browser & Web Adapters
            EgoLiteWebAdapter(),
            ObscuraCrawlerAdapter(),
            FreeClaudeCodeAdapter(),
            GodsEyeViewAdapter(),
            # 4 Security & MCP Adapters
            NightcrawlerSecurityAdapter(),
            EccCybersecurityAdapter(),
            AnthropicSecuritySkillsAdapter(),
            KaliGptDefenseAdapter(),
            # 5 Voice & Audio Adapters
            ChatterboxAcousticsAdapter(),
            AtticusAudioAdapter(),
            OpenWhisprAdapter(),
            OmniVoiceSynthesisAdapter(),
            HandyVoiceAssistantAdapter(),
            # 3 Memory & LLM Provider Adapters
            AgentMemoryStorageAdapter(),
            DshGodLlmAdapter(),
            StrataProviderAdapter(),
            # 3 Creative & Media Adapters
            JarvisUltimateMediaAdapter(),
            PenpotVectorDesignAdapter(),
            ComfyUiWorkflowAdapter(),
            # 1 Research & Science Adapter
            GeoSleuthResearchAdapter(),
            # 15 Workflow & Productivity Adapters
            ImmichMediaAdapter(),
            Harness2WorkflowAdapter(),
            AutomatonWorkflowAdapter(),
            SparkAutomationAdapter(),
            RakazoFileOrganizerAdapter(),
            HereticTextPipelineAdapter(),
            YoutubeAutomationAdapter(),
            ChatwootWebhookAdapter(),
            CalDiySchedulerAdapter(),
            OpenProjectTrackerAdapter(),
            AppFlowyDocumentAdapter(),
            OpenSeoAuditAdapter(),
            HeyGemPresentationAdapter(),
            PaperclipDocumentAdapter(),
            OpenGenerativeAiAdapter(),
        ]
        for adp in default_list:
            self.register(adp)

    def register(self, adapter: BaseAdapter):
        """Register a new or dynamic adapter into the manager."""
        self._adapters[adapter.adapter_id] = adapter
        self._repo_map[adapter.source_repo] = adapter
        logger.info(f"Registered tool adapter '{adapter.name}' ({adapter.adapter_id}) for repo '{adapter.source_repo}'")

    def get_adapter(self, adapter_id: str) -> Optional[BaseAdapter]:
        return self._adapters.get(adapter_id)

    def get_by_repo(self, source_repo: str) -> Optional[BaseAdapter]:
        return self._repo_map.get(source_repo)

    def list_adapters(self) -> List[Dict[str, Any]]:
        return [
            {
                "adapter_id": adp.adapter_id,
                "name": adp.name,
                "description": adp.description,
                "source_repo": adp.source_repo,
                "category": adp.category,
                "version": adp.version,
                "supported_operations": adp.supported_operations,
                "health_status": adp.health_status,
                "resource_requirements": adp.resource_requirements,
                "permission_requirements": adp.permission_requirements,
                "test_results": adp.test_results
            }
            for adp in self._adapters.values()
        ]

    async def execute(
        self,
        adapter_id: str,
        operation: str,
        parameters: Dict[str, Any],
        is_user_confirmed: bool = False
    ) -> AdapterExecutionResult:
        """Execute operation through adapter with resource checks and safety policy gates."""
        start_time = time.perf_counter()
        adapter = self.get_adapter(adapter_id)
        if not adapter:
            return AdapterExecutionResult(
                success=False,
                adapter_id=adapter_id,
                operation=operation,
                error=f"Adapter '{adapter_id}' not found in active registry."
            )

        # 1. Resource Headroom Check
        req_ram = adapter.resource_requirements.get("ram_mb", 150)
        has_headroom, reason, _ = resource_guard.check_headroom(required_ram_mb=req_ram)
        if not has_headroom:
            return AdapterExecutionResult(
                success=False,
                adapter_id=adapter_id,
                operation=operation,
                error=f"Resource Guard: {reason}"
            )

        # 2. Autonomy Policy Gate
        action_cat = ActionCategory.RUN_APPROVED_TOOL
        verdict = autonomy_policy.evaluate(
            action_cat,
            details={"adapter": adapter_id, "operation": operation, **parameters},
            is_user_confirmed=is_user_confirmed
        )
        if not verdict.allowed:
            return AdapterExecutionResult(
                success=False,
                adapter_id=adapter_id,
                operation=operation,
                error=f"Policy Block: {verdict.reason}"
            )

        # 3. Execution with self-healing recovery retry
        max_attempts = 2
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                res = await adapter.execute(operation, parameters)
                if res.success:
                    # Update test result cache
                    adapter.test_results = {
                        "last_tested": time.time(),
                        "operation": operation,
                        "success": True,
                        "latency_ms": res.execution_time_ms
                    }
                    return res
                else:
                    last_error = res.error or "Operation failed"
                    logger.warning(f"Adapter '{adapter_id}' execution attempt {attempt} failed: {last_error}")
                    time.sleep(0.1)
            except Exception as ex:
                last_error = str(ex)
                logger.error(f"Adapter '{adapter_id}' exception on attempt {attempt}: {ex}")
                time.sleep(0.1)

        latency = (time.perf_counter() - start_time) * 1000
        adapter.health_status = "degraded"
        return AdapterExecutionResult(
            success=False,
            adapter_id=adapter_id,
            operation=operation,
            error=f"Execution failed after {max_attempts} attempts: {last_error}",
            execution_time_ms=round(latency, 2)
        )

    async def check_all_health(self) -> Dict[str, Any]:
        """Probe live health across all active adapters."""
        results = {}
        for aid, adp in self._adapters.items():
            results[aid] = await adp.check_health()
        return results


# Global adapter manager singleton
adapter_manager = AdapterManager()
