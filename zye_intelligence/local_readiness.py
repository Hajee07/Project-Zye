"""
ZYE AI — Hardware-Aware Local Inference Readiness
=================================================

Implements Section 08 & Section 27 of Master Engineering Specification.
Determines whether the local host has the hardware and runtime prerequisites
to execute local language models (Ollama, llama-cpp-python, or GGUF backends).

Enforces:
1. Strict ResourceGovernor gating (if RAM > 88%, reject local model loading).
2. Hardware inspection (RAM size, VRAM, CUDA capability).
3. Graceful fallback: when local inference is unconfigured or hardware is insufficient,
   Gemini Master Brain is always the active primary intelligence.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from zye_core.types import ResourceState
from zye_reliability.resource_governor import ResourceGovernor

logger = logging.getLogger("zye.intelligence.local_readiness")


@dataclass(slots=True)
class HardwareProfile:
    """Summary of local host hardware capabilities."""

    total_ram_gb: float
    available_ram_gb: float
    cpu_cores: int
    has_nvidia_gpu: bool
    vram_mb: float
    ollama_installed: bool
    ollama_endpoint: str
    llama_cpp_installed: bool
    is_ready_for_local_inference: bool
    status_reason: str


class LocalReadinessDetector:
    """
    Evaluates hardware and environment readiness for optional local model offloading.
    """

    def __init__(
        self,
        governor: Optional[ResourceGovernor] = None,
        ollama_endpoint: str = "http://127.0.0.1:11434",
    ) -> None:
        self.governor = governor or ResourceGovernor()
        self.ollama_endpoint = ollama_endpoint

    def check_nvidia_smi(self) -> Tuple[bool, float]:
        """Detect NVIDIA GPU and VRAM in megabytes via nvidia-smi."""
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                vram_str = res.stdout.strip().split("\n")[0]
                return True, float(vram_str)
        except Exception:
            pass
        return False, 0.0

    def check_ollama_runtime(self) -> bool:
        """Check if Ollama executable or daemon is installed/running."""
        if shutil.which("ollama") is not None:
            return True
        # Check default Windows installation path
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            ollama_path = os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe")
            if os.path.exists(ollama_path):
                return True
        return False

    def evaluate_readiness(self) -> HardwareProfile:
        """
        Inspect local machine and produce HardwareProfile.
        Strictly enforces memory limits via ResourceGovernor.
        """
        metrics = self.governor.sample_metrics()
        cpu_cores = os.cpu_count() or 4
        has_gpu, vram_mb = self.check_nvidia_smi()
        ollama_installed = self.check_ollama_runtime()

        llama_cpp_installed = False
        try:
            import llama_cpp  # type: ignore
            llama_cpp_installed = True
        except ImportError:
            llama_cpp_installed = False

        total_ram_gb = round(metrics.ram_total_mb / 1024, 1)
        avail_ram_gb = round(metrics.ram_available_mb / 1024, 1)

        # 1. Gate: RAM Pressure check (> 88%)
        permitted, perm_reason = self.governor.is_local_inference_permitted()
        if not permitted:
            return HardwareProfile(
                total_ram_gb=total_ram_gb,
                available_ram_gb=avail_ram_gb,
                cpu_cores=cpu_cores,
                has_nvidia_gpu=has_gpu,
                vram_mb=vram_mb,
                ollama_installed=ollama_installed,
                ollama_endpoint=self.ollama_endpoint,
                llama_cpp_installed=llama_cpp_installed,
                is_ready_for_local_inference=False,
                status_reason=f"REJECTED: {perm_reason}",
            )

        # 2. Gate: Minimum RAM required for local models (at least 6 GB available)
        if avail_ram_gb < 4.0:
            return HardwareProfile(
                total_ram_gb=total_ram_gb,
                available_ram_gb=avail_ram_gb,
                cpu_cores=cpu_cores,
                has_nvidia_gpu=has_gpu,
                vram_mb=vram_mb,
                ollama_installed=ollama_installed,
                ollama_endpoint=self.ollama_endpoint,
                llama_cpp_installed=llama_cpp_installed,
                is_ready_for_local_inference=False,
                status_reason=(
                    f"Insufficient available RAM ({avail_ram_gb} GB free; minimum 4.0 GB required). "
                    f"Relying on Gemini Master Brain."
                ),
            )

        # 3. Gate: Runtime availability
        if not (ollama_installed or llama_cpp_installed):
            return HardwareProfile(
                total_ram_gb=total_ram_gb,
                available_ram_gb=avail_ram_gb,
                cpu_cores=cpu_cores,
                has_nvidia_gpu=has_gpu,
                vram_mb=vram_mb,
                ollama_installed=False,
                ollama_endpoint=self.ollama_endpoint,
                llama_cpp_installed=False,
                is_ready_for_local_inference=False,
                status_reason="Neither Ollama nor llama-cpp is installed. Primary: Gemini Master Brain.",
            )

        return HardwareProfile(
            total_ram_gb=total_ram_gb,
            available_ram_gb=avail_ram_gb,
            cpu_cores=cpu_cores,
            has_nvidia_gpu=has_gpu,
            vram_mb=vram_mb,
            ollama_installed=ollama_installed,
            ollama_endpoint=self.ollama_endpoint,
            llama_cpp_installed=llama_cpp_installed,
            is_ready_for_local_inference=True,
            status_reason="Local runtime available and system memory within safe headroom.",
        )


__all__ = [
    "HardwareProfile",
    "LocalReadinessDetector",
]
