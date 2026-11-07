"""MATRIX Repository Intelligence: License Checker.
Inspects open-source SPDX license identifiers and classifies integration permissions.
"""
from typing import Dict, Any


class LicenseChecker:
    """Evaluates open source licenses for MATRIX integration compatibility."""

    PERMISSIVE = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0"]
    WEAK_COPYLEFT = ["MPL-2.0", "LGPL-2.1", "LGPL-3.0"]
    STRONG_COPYLEFT = ["GPL-2.0", "GPL-3.0", "AGPL-3.0"]

    def evaluate_license(self, spdx_id: str) -> Dict[str, Any]:
        """Classify license risk and permitted integration methods."""
        spdx_clean = (spdx_id or "Unknown").strip()

        if spdx_clean in self.PERMISSIVE:
            return {
                "license": spdx_clean,
                "tier": "Permissive",
                "compatible_for_native": True,
                "allowed_methods": ["native", "service", "adapter", "skill"],
                "notes": "Fully compatible with MATRIX core integration."
            }
        elif spdx_clean in self.WEAK_COPYLEFT:
            return {
                "license": spdx_clean,
                "tier": "Weak Copyleft",
                "compatible_for_native": False,
                "allowed_methods": ["service", "adapter"],
                "notes": "Must be integrated as separate service or adapter to avoid viral licensing."
            }
        elif spdx_clean in self.STRONG_COPYLEFT:
            return {
                "license": spdx_clean,
                "tier": "Strong Copyleft (GPL/AGPL)",
                "compatible_for_native": False,
                "allowed_methods": ["service", "reference"],
                "notes": "Must run as independent standalone process via HTTP/REST API; no direct code linking."
            }
        else:
            return {
                "license": spdx_clean,
                "tier": "Unspecified / Custom",
                "compatible_for_native": False,
                "allowed_methods": ["adapter", "reference"],
                "notes": "Requires manual inspection before direct installation."
            }


license_checker = LicenseChecker()
