"""MATRIX Autonomous Installer Package."""
from core.autonomous_installer.installer import (
    InstallResult,
    DependencyManifest,
    AutonomousInstaller,
    autonomous_installer,
)

__all__ = [
    "InstallResult",
    "DependencyManifest",
    "AutonomousInstaller",
    "autonomous_installer",
]
