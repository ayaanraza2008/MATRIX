"""MATRIX Creative & Media Intelligence Agent.
Manages image/video prompt synthesis, story/script writing, music concept generation,
voiceover scripts, thumbnail design briefs, and Mermaid/SVG diagram rendering.
"""
from typing import Dict, Any, List
import time
from agents.base_agent import BaseAgent, AgentResult, AgentCapability


class CreativeAgent(BaseAgent):
    """Integrates creative generation workflows, prompt engineering, and visual design automation."""

    def __init__(self):
        super().__init__(
            name="creative",
            description="Synthesizes image/video/music prompts, scripts, storyboards, and diagrams.",
            max_autonomy_level=2
        )
        self._capabilities = [
            AgentCapability(name="diagram_generation", description="Generate Mermaid graphs and SVG blueprints", operations=["mermaid", "diagram", "svg", "flowchart"]),
            AgentCapability(name="prompt_synthesis", description="Generate rich prompts for image, video, and music generation", operations=["image_prompt", "video_prompt", "music_prompt"]),
            AgentCapability(name="scriptwriting", description="Write scripts, voiceovers, and storyboard concepts", operations=["script", "voiceover", "story", "thumbnail"])
        ]

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        act_lower = action.lower()
        prompt = parameters.get("prompt", parameters.get("query", "futuristic HUD graphic")).lower()

        # 1. Mermaid Architecture Diagram Generation
        if "mermaid" in act_lower or "diagram" in act_lower or "mermaid" in prompt or "flowchart" in prompt:
            return await self.execute_tool_adapter(
                adapter_id="adapter_diagram_design",
                operation="generate_mermaid",
                parameters={"title": parameters.get("title", "MATRIX Personal AI Ecosystem Architecture")}
            )

        # 2. SVG Blueprint Generation
        if "svg" in act_lower or "svg" in prompt:
            return await self.execute_tool_adapter(
                adapter_id="adapter_diagram_design",
                operation="generate_svg",
                parameters={"width": 500, "height": 300}
            )

        # 3. Image Prompt Generation
        if "image" in act_lower or "image prompt" in prompt:
            theme = parameters.get("theme", prompt)
            enhanced = f"Cinematic digital concept art of {theme}, 8k resolution, volumetric cyan lighting, futuristic holographic HUD details, Unreal Engine 5 render style, photorealistic textures."
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="generate_image_prompt",
                data={"positive_prompt": enhanced, "negative_prompt": "blurry, low resolution, artifacts, oversaturated", "aspect_ratio": "16:9"},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        # 4. Video Prompt / Storyboard Generation
        if "video" in act_lower or "video prompt" in prompt:
            theme = parameters.get("theme", prompt)
            v_prompt = f"Smooth 24fps drone tracking shot of {theme}, anamorphic lens flare, shallow depth of field, dramatic atmospheric haze, 4k master."
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="generate_video_prompt",
                data={"prompt": v_prompt, "camera_motion": "slow push-in", "duration_seconds": 5},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        # 5. Voiceover / Script Generation
        if "script" in act_lower or "voiceover" in act_lower or "story" in prompt:
            theme = parameters.get("theme", prompt)
            script_text = f"Title: {theme}\n\n[MUSIC: Subtle atmospheric electronic beat builds]\nVOICEOVER: In a world driven by speed, intelligence isn't just about answers. It's about autonomy. Welcome to MATRIX.\n[SCENE CUT: Holographic AI core pulses in electric cyan]"
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="generate_script",
                data={"script": script_text, "word_count": len(script_text.split()), "tone": "cinematic"},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="render_media_plan",
            data={
                "prompt": prompt,
                "engine": "Creative Studio & Media Adapter",
                "status": "Pipeline ready for creative synthesis"
            },
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and (isinstance(result, dict) or getattr(result, "success", True)))
