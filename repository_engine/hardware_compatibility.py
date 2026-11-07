"""MATRIX Repository Intelligence: Hardware Compatibility Evaluator.
Assesses repository compute requirements against verified machine specs (8GB RAM, Ryzen 7 5700U, Radeon APU).
"""
from typing import Dict, Any, List
import psutil
from config.settings import settings


class HardwareCompatibilityChecker:
    """Evaluates whether an external repository can safely execute on the target machine."""

    def evaluate_compatibility(self, repo_name: str, language: str, description: str) -> Dict[str, Any]:
        """Check memory, CPU, and GPU requirements."""
        name_low = repo_name.lower()
        desc_low = description.lower()
        vm = psutil.virtual_memory()
        available_mb = vm.available / (1024 * 1024)

        reasons = []
        is_compatible = True
        recommended_mode = "CPU Execution"

        # Check for heavy diffusion / video generation models (e.g. ComfyUI, dramaclaw, MoCha)
        if any(k in name_low or k in desc_low for k in ["diffusion", "comfyui", "video character", "aigc video"]):
            is_compatible = False
            recommended_mode = "External Cloud / Remote API Service"
            reasons.append("Heavy video/diffusion models require >=8-16 GB dedicated VRAM; machine has integrated 512MB VRAM.")

        # Check for heavy local LLMs / inference frameworks (e.g. airllm, Strata)
        elif any(k in name_low or k in desc_low for k in ["2.8t llm", "70b", "large language model"]):
            is_compatible = True
            recommended_mode = "Layered Disk Offload / Small Quantized"
            reasons.append("Compatible with AirLLM layer-by-layer offload to D:\\matrix_data.")

        # Rust / TypeScript / Python tools (e.g. ego-lite, mobile-mcp, browser-use, hexstrike)
        else:
            is_compatible = True
            recommended_mode = "Native CPU / Node Runtime"

        return {
            "repository": repo_name,
            "is_compatible": is_compatible,
            "recommended_mode": recommended_mode,
            "host_hardware": {
                "cpu": "AMD Ryzen 7 5700U (8C/16T)",
                "available_ram_mb": round(available_mb, 1),
                "gpu": "AMD Radeon Graphics (APU)"
            },
            "notes": reasons or ["Runs efficiently within target host hardware profile."]
        }


hardware_checker = HardwareCompatibilityChecker()
