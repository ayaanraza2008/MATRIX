"""Audit all integrations and their connection statuses."""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
from core.integrations.manager import integration_manager

async def audit():
    print("=" * 70)
    print("      MATRIX UNIVERSAL INTEGRATION AUDIT")
    print("=" * 70)
    integrations = integration_manager.list_integrations()
    print(f"Total cataloged integrations: {len(integrations)}")
    
    for item in integrations:
        iid = item.get("id")
        name = item.get("name")
        status = item.get("status")
        configured = item.get("is_configured")
        cat = item.get("category")
        print(f"[{status:14}] {name:30} ({iid}) | Category: {cat} | Configured: {configured}")

if __name__ == "__main__":
    asyncio.run(audit())
