"""MATRIX Intent Classification Engine.
Determines intent, target specialized agent, parameters, required autonomy level,
and extracts entities from natural language requests in English, Hindi, and Hinglish.
"""
from enum import Enum
from typing import Dict, Any, List
import re
from pydantic import BaseModel
from config.logging_config import get_logger

logger = get_logger("core.intent")


class IntentType(str, Enum):
    COMMAND = "command"        # PC automation, app launch, mouse/keyboard
    QUERY = "query"            # Factual info, system specs, direct QA
    RESEARCH = "research"      # Web search, article scraping, deep comparative study
    CODING = "coding"          # Write code, debug, analyze file, run tests
    FILES = "files"            # Read, organize, summarize, convert documents
    WORKFLOW = "workflow"      # Multi-step recurring automation
    VOICE = "voice"            # Speech synthesis, microphone config
    VISION = "vision"          # Webcam, screenshot analysis, OCR
    SECURITY = "security"      # Audit, permission review, MITRE scan
    SYSTEM = "system"          # Hardware monitoring, telemetry, cleanup
    REPO_INTEL = "repo_intel"  # Inspect starred repos, generate skills
    MEMORY = "memory"          # Store, recall, and retrieve preferences/memories
    CREATIVE = "creative"      # Diagrams, Mermaid flowcharts, SVGs, media plans
    DATA_ANALYSIS = "data_analysis"  # Tabular, CSV, statistics, dataset
    ANDROID = "android"        # Phone pairing, mobile companion, push notification
    CHAT = "chat"              # General conversational dialog


class ParsedIntent(BaseModel):
    intent_type: IntentType
    confidence: float
    target_agent: str
    action: str
    parameters: Dict[str, Any]
    required_autonomy_level: int
    entities: List[str]
    raw_prompt: str


class IntentEngine:
    """Classifies user prompts into structured execution directives."""

    INTENT_RULES = [
        # Master Windows Volume Control & Sound Level
        (r"\b(volume\s+(?:up|down|increase|decrease|raise|lower|reduce|to|set(?:\s+to)?|\d+)|turn\s+(?:the\s+)?volume(?:\s+(?:up|down))?|mute(?:\s+sound|\s+volume)?|unmute|sound\s+level|set\s+volume)\b", IntentType.COMMAND, "computer", 0),
        # 1. High-Risk Destructive Commands (Mandatory Level 3 Safety Gate)
        (r"\b(format\s+[a-z]:|del\s+/[fsq]|rmdir\s+/[sq]|rm\s+-rf|drop\s+table|drop\s+database|reg\s+delete|delete\s+all\s+system\s+files)\b", IntentType.COMMAND, "computer", 3),

        # 2. Voice Directives (Stop speaking, go to sleep, continuous listening)
        (r"\b(stop\s+speaking|be\s+quiet|shut\s+up|silence|mute\s+speech|stop\s+talking|stop|matrix\s+stop)\b", IntentType.VOICE, "voice", 0),
        (r"\b(go\s+to\s+sleep|sleep\s+mode|standby\s+mode|sleep\s+now|enter\s+sleep)\b", IntentType.VOICE, "voice", 0),
        (r"\b(continue\s+listening|keep\s+listening|hands[- ]free\s+mode|continuous\s+listening|continue\s+listening\s+after\s+answering)\b", IntentType.VOICE, "voice", 0),

        # 3. Core Task Cancellation
        (r"\b(cancel\s+(?:the\s+)?(?:current\s+|this\s+)?task|stop\s+(?:the\s+)?(?:current\s+|this\s+)?task|abort\s+task)\b", IntentType.COMMAND, "core", 0),

        # 4. Personal Account & Email Operations
        (r"\b(draft\s+(?:an?\s+)?email|compose\s+(?:an?\s+)?email|create\s+(?:an?\s+)?email\s+draft|write\s+(?:an?\s+)?email)\b", IntentType.COMMAND, "personal", 1),
        (r"\b(open\s+github\s+and\s+inspect\s+(?:my\s+)?repository|inspect\s+(?:my\s+)?github\s+repository|inspect\s+(?:my\s+)?repository)\b", IntentType.COMMAND, "personal", 1),

        # 5. File & Folder Organization
        (r"\b(create|make|new|mkdir)\s+(?:a\s+)?(?:folder|directory)\b", IntentType.FILES, "files", 1),
        (r"\b(list\s+(?:my\s+)?(?:files|desktop|downloads|documents)|show\s+(?:my\s+)?files|view\s+(?:my\s+)?files)\b", IntentType.FILES, "files", 1),
        (r"\b(organize\s+(?:my\s+)?downloads(?:\s+folder)?|organize\s+(?:my\s+)?(?:folder|files|documents))\b", IntentType.FILES, "files", 1),
        (r"\b(write\s+(?:a\s+)?file|read\s+(?:a\s+)?file|create\s+(?:a\s+)?file|delete\s+(?:a\s+)?file|open\s+(?:a\s+)?file|pdf|docx|xlsx|read document|summarize file|convert format|extract text from file|organize files|find files|personal files|storage files|list\s+files)\b", IntentType.FILES, "files", 1),

        # 6. System Diagnostics & Telemetry
        (r"\b(explain\s+what\s+you\s+are\s+(?:currently\s+)?doing|what\s+are\s+you\s+(?:currently\s+)?doing|current\s+status|system\s+status)\b", IntentType.SYSTEM, "system", 0),
        (r"\b(check\s+(?:my\s+)?computer|system\s+diagnos\w*|diagnose\s+(?:my\s+)?(?:pc|computer|system)|system\s+health)\b", IntentType.SYSTEM, "system", 0),
        (r"\b(cpu|ram|memory|specs|hardware|temperature|storage|disk space|usage|system monitor|telemetry|performance|system\s+performance|check\s+(?:my\s+)?(?:computer\s+)?performance)\b", IntentType.SYSTEM, "system", 0),

        # 7. Memory & Knowledge Storage / Retrieval
        (r"\b(memory|remember|save\s+.+\s+in\s+memory|store\s+.+\s+in\s+memory|retrieve\s+memory|recall|user\s+preference|favorite\s+\w+|remember\s+(?:this\s+)?preference)\b", IntentType.MEMORY, "memory", 1),

        # 8. Creative & Diagram Blueprints
        (r"\b(diagram|mermaid|flowchart|architecture\s+diagram|svg|draw\s+architecture|render\s+diagram|diagram\s+of\s+(?:your\s+)?architecture)\b", IntentType.CREATIVE, "creative", 1),

        # 9. Coding & AST Structural Analysis
        (r"\b(create\s+(?:a\s+)?(?:python\s+)?(?:application|app|script)\s+and\s+test\s+it|write\s+code\s+and\s+test)\b", IntentType.CODING, "coding", 2),
        (r"\b(analyze\s+(?:the\s+)?(?:python\s+)?file|inspect\s+(?:the\s+)?(?:code|file|architecture)|verify\s+syntax|lint|ast|code\s+analysis|coding\s+capability)\b", IntentType.CODING, "coding", 2),
        (r"\b(code|script|program|debug|fix error|refactor|function|class|unit test|pytest|test runner|test suite|git commit|pull request|typescript|create\s+(?:a\s+)?(?:python\s+)?(?:application|app|script)|python\s+application|test\s+it)\b", IntentType.CODING, "coding", 2),

        # 10. Research & Browser Automation
        (r"\b(deep\s+research|research\s+dossier|research\s+report|in-depth\s+research|research\s+paper|research\s+on\s+.+|research\s+(?:this\s+)?topic|prepare\s+a\s+report)\b", IntentType.RESEARCH, "research", 1),
        (r"\b(search the web|research|find articles|look up online|compare sources|what is the latest|news on|browser\s+capability|using\s+(?:the\s+)?browser|browse\s+https?://|web\s+information|web\s+search|find\s+relevant\s+information|open\s+(?:my\s+)?browser\s+and\s+find)\b", IntentType.RESEARCH, "research", 1),

        # 11. Android Companion
        (r"\b(android|pair\s+phone|pairing\s+token|pair\s+device|mobile\s+companion|push\s+notification)\b", IntentType.ANDROID, "android", 1),

        # 12. Data Analysis & Mathematical Calculation
        (r"\b(calculate|compute|solve|math\s+expression|\d+\s*[+\-*/%]\s*\d+)\b", IntentType.DATA_ANALYSIS, "data_analysis", 0),
        (r"\b(data\s+analysis|dataset|tabular|statistics|numerical\s+analysis|analyze\s+csv|calculate\s+stats)\b", IntentType.DATA_ANALYSIS, "data_analysis", 1),

        # 13. PC Control / Command
                (r"\b(open|launch|go\s+to|visit)\s+(?:https?://|www\.)?[a-zA-Z0-9-]+\.(?:com|org|net|io|edu|gov|co)\b", IntentType.COMMAND, "computer", 1),
        (r"\b(open|launch|go\s+to)\s+(youtube|google|github|reddit|twitter|wikipedia|spotify)\b", IntentType.COMMAND, "computer", 1),
        (r"\b(search\s+(?:for\s+)?(?:.+)\s+on\s+google|google\s+(?:for\s+)?.+)\b", IntentType.COMMAND, "computer", 1),
(r"\b(open|launch|start|run)\s+(chrome|google\s+chrome|browser)\b", IntentType.COMMAND, "computer", 1),
        (r"\b(open|launch|start|run|close|switch to|maximize|minimize|type|click|press)\b.*\b(notepad|calc|calculator|browser|chrome|terminal|cmd|powershell|window|app|application|code)\b", IntentType.COMMAND, "computer", 1),
        (r"\b(safe\s+task|perform\s+a\s+safe\s+task|safe\s+command|run\s+command|execute\s+command|whoami|hostname|ipconfig|systeminfo)\b", IntentType.COMMAND, "computer", 1),
        (r"\b(screenshot|capture screen|take a snap)\b", IntentType.COMMAND, "computer", 1),

        # AirTouch Vision, Gesture3D, Touchless Scroll & GesturEye
        (r"\b(airtouch|gesture\s+control|hand\s+control|eye\s+control|eye\s+tracking|gesture\s+scroll|scroll\s+down|scroll\s+up|scroll\s+speed|stop\s+scrolling|rotate\s+3d|reset\s+3d|calibrate\s+eye|what\s+am\s+i\s+looking\s+at|describe\s+(?:this\s+)?scene)\b", IntentType.VISION, "vision", 1),

        # 14. Vision & Camera
        (r"\b(find\s+the\s+error\s+on\s+(?:my\s+)?screen|inspect\s+(?:my\s+)?screen\s+for\s+errors?|error\s+on\s+(?:my\s+)?screen)\b", IntentType.VISION, "vision", 1),
        (r"\b(screen|camera|webcam|visible on my screen|what is on my screen|what is currently visible|read this image|ocr|look at this|scan this|inspect\s+(?:my\s+)?screen)\b", IntentType.VISION, "vision", 1),

        # 15. JARVIS Voice Synthesis
        (r"\b(speak|say out loud|voice synthesis|talk in hindi|bolna)\b", IntentType.VOICE, "voice", 0),

        # 16. Repository Intelligence
        (r"\b(starred repo|repositories|github|integrate repo|hexstrike|ego-lite|chatterbox|agentmemory|select\s+tool|capability\s+gap|repository\s+capability|best\s+available\s+capability|suitable\s+repository\s+capability|find\s+(?:a\s+)?(?:suitable\s+)?(?:repository\s+)?capability)\b", IntentType.REPO_INTEL, "repo_intel", 1),

        # 17. Security & Audit
        (r"\b(security|audit|permission|firewall|sandbox|mitre|vulnerability|risk|security\s+policy|evaluate\s+payload)\b", IntentType.SECURITY, "security", 2),

        # 18. Multi-Step Workflows
        (r"\b(workflow|automate|schedule|recurring|every morning|pipeline|background task)\b", IntentType.WORKFLOW, "automation", 2),
    ]

    def classify(self, prompt: str) -> ParsedIntent:
        """Parse natural language into a verified ParsedIntent."""
        cleaned = prompt.strip().lower()

        # Check regex intent rules
        for pattern, itype, agent, autonomy in self.INTENT_RULES:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                entities = self._extract_entities(prompt)
                action = match.group(1) if match.groups() else "execute"
                return ParsedIntent(
                    intent_type=itype,
                    confidence=0.92,
                    target_agent=agent,
                    action=action,
                    parameters={"query": prompt, "matched_pattern": pattern},
                    required_autonomy_level=autonomy,
                    entities=entities,
                    raw_prompt=prompt
                )

        # Fallback heuristic: question vs conversation
        if any(w in cleaned for w in ["how", "what", "why", "when", "where", "who", "which", "can you"]):
            return ParsedIntent(
                intent_type=IntentType.QUERY,
                confidence=0.75,
                target_agent="personal",
                action="answer",
                parameters={"query": prompt},
                required_autonomy_level=0,
                entities=[],
                raw_prompt=prompt
            )

        return ParsedIntent(
            intent_type=IntentType.CHAT,
            confidence=0.85,
            target_agent="core",
            action="dialog",
            parameters={"query": prompt},
            required_autonomy_level=0,
            entities=[],
            raw_prompt=prompt
        )

    def _extract_entities(self, text: str) -> List[str]:
        """Extract quoted strings, file extensions, URLs, or potential target entities."""
        entities = []
        # Quoted entities
        quotes = re.findall(r'["\']([^"\']+)["\']', text)
        entities.extend(quotes)

        # File paths or extensions
        files = re.findall(r'\b[\w-]+\.(?:pdf|docx|xlsx|csv|txt|py|ts|json|png|jpg)\b', text, re.IGNORECASE)
        entities.extend(files)

        # URLs
        urls = re.findall(r'https?://[^\s]+', text)
        entities.extend(urls)

        return list(set(entities))


# Global Intent Engine singleton
IntentEngine.parse = IntentEngine.classify
intent_engine = IntentEngine()
