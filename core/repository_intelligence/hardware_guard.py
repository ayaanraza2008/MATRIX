"""MATRIX Hardware Compatibility Guard & CPU Alternative Router.
Audits hardware requirements for GPU-heavy / high-VRAM repositories:
1. 3dlg-hcvc/diorama
2. Orange-3DV-Team/MoCha
3. dramaclaw/dramaclaw
4. lyogavin/airllm
5. wide-trace/open-higgsfield

Detects host AMD Ryzen 7 5700U with integrated Radeon Graphics (no discrete CUDA VRAM)
and maps tasks to verified CPU-compatible lightweight alternatives.
"""
from typing import Dict, Any, Optional
import psutil
from pydantic import BaseModel
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.repo_intel.hardware_guard")


class HardwareProfile(BaseModel):
    cpu_cores: int
    cpu_threads: int
    total_ram_mb: float
    available_ram_mb: float
    has_cuda: bool = False
    cuda_devices: int = 0
    gpu_name: str = "AMD Radeon Graphics (Integrated)"
    is_cpu_only: bool = True
    supports_avx2: bool = True


class IncompatibleRepoAssessment(BaseModel):
    repo_name: str
    required_hardware: str
    minimum_vram_gb: int
    incompatibility_reason: str
    cpu_alternative_method: str
    recommended_adapter: str
    is_supported_on_current_host: bool = False


class HardwareCompatibilityGuard:
    """Manages hardware profiling and CPU-compatible alternative fallbacks."""

    INCOMPATIBLE_REPOS: Dict[str, Dict[str, Any]] = {
        "3dlg-hcvc/diorama": {
            "required_hardware": "NVIDIA GPU with CUDA 11.8+ and PyTorch CUDA extensions",
            "minimum_vram_gb": 16,
            "reason": "Requires high-VRAM CUDA compute for dense 3D scene point-cloud reconstruction and NeRF volume rendering.",
            "cpu_alternative": "Generate 2D architectural blueprints, vector diagrams, and SVG layout models.",
            "recommended_adapter": "adapter_diagram_design"
        },
        "Orange-3DV-Team/MoCha": {
            "required_hardware": "NVIDIA CUDA GPU with SMPL mesh deformation shaders",
            "minimum_vram_gb": 12,
            "reason": "Requires CUDA-accelerated neural kinematic optimization for monocular 3D motion capture.",
            "cpu_alternative": "Lightweight 2D/3D pose estimation and landmark tracking via OpenCV CPU.",
            "recommended_adapter": "adapter_vision_ocr"
        },
        "dramaclaw/dramaclaw": {
            "required_hardware": "NVIDIA CUDA GPU with Tensor Cores and >24 GB VRAM",
            "minimum_vram_gb": 24,
            "reason": "Requires heavy diffusion video frame generation models that exhaust 8GB system RAM immediately.",
            "cpu_alternative": "Multi-scene script synthesis, visual storyboard blueprints, and video prompt planning.",
            "recommended_adapter": "adapter_creative_media"
        },
        "lyogavin/airllm": {
            "required_hardware": "High-speed NVMe disk swapping (>140 GB free space) with CUDA tensor offloading",
            "minimum_vram_gb": 8,
            "reason": "AirLLM layer-wise disk offloading for 70B models requires massive free disk space and crashes with low RAM thrashing on 8 GB systems.",
            "cpu_alternative": "Quantized GGUF 4-bit local CPU inference via llama-cpp (AVX2-accelerated) or Free Cloud LLM API routing.",
            "recommended_adapter": "adapter_free_llm"
        },
        "wide-trace/open-higgsfield": {
            "required_hardware": "NVIDIA GPU with CUDA acceleration for text-to-video diffusion",
            "minimum_vram_gb": 16,
            "reason": "Diffusion-based video generation exceeds available memory and cannot run on AMD integrated graphics.",
            "cpu_alternative": "Keyframe animation planning, SVG vector animations, and media storyline generation.",
            "recommended_adapter": "adapter_diagram_design"
        }
    }

    def __init__(self):
        self._profile = self._detect_hardware()

    def _detect_hardware(self) -> HardwareProfile:
        vm = psutil.virtual_memory()
        has_cuda = False
        cuda_count = 0
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            cuda_count = torch.cuda.device_count() if has_cuda else 0
        except Exception:
            has_cuda = False

        return HardwareProfile(
            cpu_cores=settings.cpu_cores,
            cpu_threads=settings.cpu_threads,
            total_ram_mb=round(vm.total / (1024 * 1024), 1),
            available_ram_mb=round(vm.available / (1024 * 1024), 1),
            has_cuda=has_cuda,
            cuda_devices=cuda_count,
            gpu_name="NVIDIA CUDA" if has_cuda else "AMD Radeon Graphics (Integrated)",
            is_cpu_only=not has_cuda,
            supports_avx2=True
        )

    @property
    def profile(self) -> HardwareProfile:
        return self._profile

    def assess_repository(self, repo_full_name: str) -> Optional[IncompatibleRepoAssessment]:
        """Check if repository is hardware-incompatible and provide CPU alternative."""
        info = self.INCOMPATIBLE_REPOS.get(repo_full_name)
        if not info:
            # Check short name match
            for k, v in self.INCOMPATIBLE_REPOS.items():
                if repo_full_name.lower() in k.lower():
                    info = v
                    repo_full_name = k
                    break

        if not info:
            return None

        return IncompatibleRepoAssessment(
            repo_name=repo_full_name,
            required_hardware=info["required_hardware"],
            minimum_vram_gb=info["minimum_vram_gb"],
            incompatibility_reason=info["reason"],
            cpu_alternative_method=info["cpu_alternative"],
            recommended_adapter=info["recommended_adapter"],
            is_supported_on_current_host=False
        )

    def get_all_incompatible_assessments(self) -> Dict[str, IncompatibleRepoAssessment]:
        return {
            repo: self.assess_repository(repo)
            for repo in self.INCOMPATIBLE_REPOS.keys()
        }


# Global singleton
hardware_guard = HardwareCompatibilityGuard()
