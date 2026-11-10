"""MATRIX Tool Discovery Engine.
Catalogs, indexes, and searches executable tools across all 16 specialized agents,
43 repository tool adapters, and universal integrations.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from config.logging_config import get_logger

logger = get_logger("core.autonomy.tool_discovery")


class ToolDescriptor(BaseModel):
    tool_id: str
    name: str
    provider_type: str  # 'agent', 'tool_adapter', 'integration', 'native'
    provider_name: str
    description: str
    category: str
    risk_level: int = 1  # 1 to 4
    required_autonomy_level: int = 1
    input_parameters: Dict[str, Any] = Field(default_factory=dict)
    is_available: bool = True
    tags: List[str] = Field(default_factory=list)


class ToolDiscoveryEngine:
    """Discovers, registers, and searches capabilities dynamically across the MATRIX ecosystem."""

    def __init__(self):
        self._registry: Dict[str, ToolDescriptor] = {}
        self._initialize_builtins()
        self._index_tool_adapters()

    def _initialize_builtins(self):
        """Index all built-in tools across the 16 specialized agents."""
        builtins = [
            # Computer Agent
            ToolDescriptor(
                tool_id="computer.volume_control",
                name="Windows Audio Master Volume Control",
                provider_type="agent",
                provider_name="computer",
                description="Controls Windows 11 endpoint audio volume: up, down, mute, unmute, set percentage.",
                category="os_control",
                risk_level=1,
                required_autonomy_level=1,
                input_parameters={"action": "string (up/down/mute/unmute/set)", "level": "float (0.0 to 1.0)"},
                tags=["volume", "audio", "sound", "mute", "pycaw"]
            ),
            ToolDescriptor(
                tool_id="computer.open_url",
                name="Default Browser Web Navigation",
                provider_type="agent",
                provider_name="computer",
                description="Opens URLs and searches directly in the Windows default web browser.",
                category="web",
                risk_level=1,
                required_autonomy_level=2,
                input_parameters={"url": "string"},
                tags=["browser", "youtube", "google", "web", "url"]
            ),
            ToolDescriptor(
                tool_id="computer.app_management",
                name="Application Lifecycle Controller",
                provider_type="agent",
                provider_name="computer",
                description="Launches, switches, and closes Windows 11 applications with process PID verification.",
                category="os_control",
                risk_level=2,
                required_autonomy_level=2,
                input_parameters={"app_name": "string", "action": "open/close"},
                tags=["launch", "close", "notepad", "calculator", "chrome", "process"]
            ),
            ToolDescriptor(
                tool_id="computer.screen_capture",
                name="Desktop Surface Capture & OCR",
                provider_type="agent",
                provider_name="computer",
                description="Captures active desktop display buffer and performs native OCR.",
                category="vision",
                risk_level=1,
                required_autonomy_level=1,
                tags=["screenshot", "screen", "ocr", "display"]
            ),

            # File Agent
            ToolDescriptor(
                tool_id="files.create_folder",
                name="Safe Directory Creator",
                provider_type="agent",
                provider_name="files",
                description="Creates new directories on Desktop, Documents, or Downloads with collision checks.",
                category="filesystem",
                risk_level=1,
                required_autonomy_level=2,
                input_parameters={"folder_name": "string", "target_dir": "string"},
                tags=["folder", "directory", "mkdir", "create"]
            ),
            ToolDescriptor(
                tool_id="files.organize",
                name="Autonomous Folder Categorizer",
                provider_type="agent",
                provider_name="files",
                description="Sorts files into Documents, Images, Code, and Archives without overwriting data.",
                category="filesystem",
                risk_level=2,
                required_autonomy_level=3,
                tags=["organize", "downloads", "cleanup", "sort"]
            ),

            # Voice Agent
            ToolDescriptor(
                tool_id="voice.synthesize_speech",
                name="Neural Edge-TTS Synthesizer",
                provider_type="agent",
                provider_name="voice",
                description="Speaks natural responses in English, Hindi, and Hinglish with Christopher/Swara/Prabhat voices.",
                category="speech",
                risk_level=1,
                required_autonomy_level=1,
                tags=["speak", "tts", "voice", "hindi", "hinglish"]
            ),

            # Vision & AirTouch
            ToolDescriptor(
                tool_id="vision.airtouch_stream",
                name="AirTouch 3D Gesture & Eye Tracker",
                provider_type="agent",
                provider_name="vision",
                description="Real-time 21-joint hand tracking, touchless scroll, and GesturEye iris vectors.",
                category="vision",
                risk_level=1,
                required_autonomy_level=1,
                tags=["airtouch", "gesture", "scroll", "eye_tracking", "camera"]
            ),

            # Personal Agent
            ToolDescriptor(
                tool_id="personal.time_date",
                name="System Clock & Schedule Reporter",
                provider_type="agent",
                provider_name="personal",
                description="Provides real-time local date, time, and appointment status.",
                category="personal",
                risk_level=1,
                required_autonomy_level=1,
                tags=["time", "date", "clock", "today"]
            ),

            # System Agent
            ToolDescriptor(
                tool_id="system.telemetry",
                name="AMD Ryzen Hardware Telemetry Monitor",
                provider_type="agent",
                provider_name="system",
                description="Polls real-time CPU, RAM, disk space, and thermal metrics.",
                category="system",
                risk_level=1,
                required_autonomy_level=1,
                tags=["telemetry", "hardware", "cpu", "ram", "specs"]
            )
        ]

        for tool in builtins:
            self._registry[tool.tool_id] = tool

        # Also dynamically discover repository tool adapters
        self._index_tool_adapters()

    def _index_tool_adapters(self):
        """Index all tool adapters from core.tool_adapters.manager."""
        try:
            from core.tool_adapters.manager import adapter_manager
            adapters = adapter_manager.list_adapters()
            for ad in adapters:
                tid = f"adapter.{ad['adapter_id']}"
                desc = ToolDescriptor(
                    tool_id=tid,
                    name=ad.get("name", "Tool Adapter"),
                    provider_type="tool_adapter",
                    provider_name=ad.get("repository", "External Repo"),
                    description=ad.get("description", "Repository tool adapter"),
                    category=ad.get("category", "specialized"),
                    risk_level=1,
                    required_autonomy_level=2,
                    tags=[ad.get("category", ""), ad.get("adapter_id", "")]
                )
                self._registry[tid] = desc
            logger.info(f"Tool Discovery Engine indexed {len(adapters)} external tool adapters.")
        except Exception as e:
            logger.debug(f"Could not index tool adapters: {e}")

    def register_tool(self, tool: ToolDescriptor):
        """Register a new dynamic tool or integration."""
        self._registry[tool.tool_id] = tool

    def search_tools(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search available tools matching a natural language prompt or capability keyword."""
        q = query.lower().strip()
        tokens = [t for t in q.split() if len(t) > 2]
        matches = []

        for tool in self._registry.values():
            score = 0
            name_l = tool.name.lower()
            desc_l = tool.description.lower()
            tags_l = [t.lower() for t in tool.tags]
            cat_l = tool.category.lower()

            if q in name_l:
                score += 10
            if q in desc_l:
                score += 5

            for tok in tokens:
                if tok in name_l:
                    score += 4
                if tok in desc_l:
                    score += 2
                if any(tok in t or t in tok for t in tags_l):
                    score += 3
                if tok in cat_l:
                    score += 2

            if score > 0:
                matches.append((score, tool.model_dump()))

        matches.sort(key=lambda x: -x[0])
        return [m[1] for m in matches[:limit]]

    def list_all_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all indexed tools, optionally filtered by category."""
        results = []
        for t in self._registry.values():
            if category is None or t.category == category:
                results.append(t.model_dump())
        return results

    # Aliases
    discover_all = list_all_tools
    find_tools = search_tools


# Global singleton
tool_discovery = ToolDiscoveryEngine()
