"""MATRIX Intent Classification Engine.
Determines intent, target specialized agent, parameters, required autonomy level,
and extracts entities from natural language requests in English, Hindi, and Hinglish.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
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

    # Keyword mappings for high-accuracy intent routing
    INTENT_RULES = [
        # 1. High-Risk Destructive Commands (Mandatory Level 3 Safety Gate)
        (r"\b(format\s+[a-z]:|del\s+/[fsq]|rmdir\s+/[sq]|rm\s+-rf|drop\s+table|drop\s+database|reg\s+delete|delete\s+all\s+system\s+files)\b", IntentType.COMMAND, "computer", 3),

        # 2. Memory & Knowledge Storage / Retrieval
        (r"\b(memory|remember|save\s+.+\s+in\s+memory|store\s+.+\s+in\s+memory|retrieve\s+memory|recall|user\s+preference|favorite\s+\w+)\b", IntentType.MEMORY, "memory", 1),

        # 3. Creative & Diagram Blueprints
        (r"\b(diagram|mermaid|flowchart|architecture\s+diagram|svg|draw\s+architecture|render\s+diagram)\b", IntentType.CREATIVE, "creative", 1),

        # 4. Coding & AST Structural Analysis
        (r"\b(analyze\s+(?:the\s+)?(?:python\s+)?file|inspect\s+(?:the\s+)?(?:code|file|architecture)|verify\s+syntax|lint|ast|code\s+analysis|coding\s+capability)\b", IntentType.CODING, "coding", 2),
        (r"\b(code|script|program|debug|fix error|refactor|function|class|test|unit test|git|commit|pull request|typescript)\b", IntentType.CODING, "coding", 2),

        # 5. Research & Browser Automation
        (r"\b(search the web|research|find articles|look up online|compare sources|what is the latest|news on|browser\s+capability|using\s+(?:the\s+)?browser|browse\s+https?://|web\s+information)\b", IntentType.RESEARCH, "browser", 1),

        # 6. PC Control / Command
        (r"\b(open|launch|start|run|close|switch to|maximize|minimize|type|click|press)\b.*\b(notepad|calc|browser|chrome|terminal|cmd|powershell|window|app|code)\b", IntentType.COMMAND, "computer", 1),
        (r"\b(screenshot|capture screen|take a snap)\b", IntentType.COMMAND, "computer", 1),

        # 7. File & Document Intelligence
        (r"\b(pdf|docx|xlsx|csv|read document|summarize file|convert format|extract text from file|organize files|find files)\b", IntentType.FILES, "files", 1),

        # 8. Vision & Camera
        (r"\b(screen|camera|webcam|visible on my screen|what is on my screen|what is currently visible|read this image|ocr|look at this|scan this)\b", IntentType.VISION, "vision", 1),

        # 9. JARVIS Voice
        (r"\b(speak|say out loud|voice|volume|mute|listen|unmute|talk in hindi|bolna)\b", IntentType.VOICE, "voice", 0),

        # 10. System Telemetry
        (r"\b(cpu|ram|memory|specs|hardware|temperature|storage|disk space|usage|system monitor|system\s+telemetry)\b", IntentType.SYSTEM, "system", 0),

        # 11. Repository Intelligence
        (r"\b(starred repo|repositories|github|integrate repo|hexstrike|ego-lite|chatterbox|agentmemory|select\s+tool|capability\s+gap)\b", IntentType.REPO_INTEL, "repo_intel", 1),

        # 12. Security & Audit
        (r"\b(security|audit|permission|firewall|sandbox|mitre|vulnerability|risk)\b", IntentType.SECURITY, "security", 2),

        # 13. Multi-Step Workflows
        (r"\b(workflow|automate|schedule|recurring|every morning|pipeline|background task)\b", IntentType.WORKFLOW, "automation", 3),
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
intent_engine = IntentEngine()
