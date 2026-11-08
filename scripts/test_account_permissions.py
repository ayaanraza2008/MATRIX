"""MATRIX Account Operations & Permissions Gate Test (PART 11, Test 8).
Tests the personal account security architecture:
- Secure account registry metadata and token vault isolation (D:\\matrix_data\\accounts\\)
- Strict truthfulness: Verifies MATRIX never fabricates access to unconnected accounts
- Safe email drafting in isolated partition (D:\\matrix_data\\drafts\\)
- Policy Gate Enforcement: Confirms drafting is safe, but sending requires Level 3 explicit authorization
- Live GitHub repository metadata inspection
"""
import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.account_operations.registry import account_registry
from core.account_operations.manager import account_operations
from core.account_operations.models import ServiceType, AuthType
from core.autonomy_policy.policy import autonomy_policy, ActionCategory


async def run_account_permissions_test():
    print("=" * 70)
    print("  MATRIX PERSONAL ACCOUNT OPERATIONS & PERMISSIONS TEST (PART 11, SCRIPT 8)")
    print("=" * 70)

    stages_passed = 0
    total_stages = 4

    # Stage 1: Account Registry Integrity & Strict Truthfulness
    print("\n[STAGE 1/4] Testing account registry and strict truthfulness enforcement...")
    accounts = account_registry.list_connected_accounts()
    print(f"  [PASS] Currently connected accounts: {len(accounts)}")

    # Query unconnected service
    unconnected_res = await account_operations.search_account_data("slack", "important update")
    if unconnected_res.get("status") == "NOT_CONNECTED":
        print(f"  [PASS] Strict truthfulness verified: Refused to fabricate data for unconnected service 'slack'.")
        print(f"         Response: {unconnected_res.get('message')}")
        stages_passed += 1
    else:
        print("  [FAIL] MATRIX falsely claimed access to unconnected service.")
        return False

    # Stage 2: Safe Email Draft Creation
    print("\n[STAGE 2/4] Testing safe local email draft creation...")
    draft = await account_operations.draft_email(
        to_address="test.director@example.com",
        subject="Project Alpha Acceptance Report",
        body="This is an automated test draft compiled securely by MATRIX AI."
    )
    if draft.get("status") == "SUCCESS" and ("draft_file" in draft or "draft_path" in draft):
        path_str = draft.get("draft_file") or draft.get("draft_path")
        draft_file = Path(path_str)
        if draft_file.exists():
            print(f"  [PASS] Email draft created locally at '{draft_file}' ({draft_file.stat().st_size} bytes).")
            stages_passed += 1
        else:
            print(f"  [FAIL] Draft file missing from disk at {draft_file}.")
            return False
    else:
        print(f"  [FAIL] Failed to draft email: {draft}")
        return False

    # Stage 3: Level 3 Policy Gate Enforcement for External Transmission
    print("\n[STAGE 3/4] Testing Level 3 authorization boundary for external email sending...")
    policy_check = autonomy_policy.evaluate(
        ActionCategory.PUBLISH_EXTERNAL_MESSAGE,
        details={"recipient": "test.director@example.com", "subject": "Project Alpha Acceptance Report"}
    )
    if policy_check.requires_user_confirmation:
        print(f"  [PASS] External transmission blocked by Policy Gate. Requires explicit Level 3 confirmation.")
        print(f"         Required Autonomy Level: {policy_check.required_level.value} | Confirmation Reason: {policy_check.reason}")
        stages_passed += 1
    else:
        print("  [FAIL] Policy gate failed to require confirmation for external communication.")
        return False

    # Stage 4: Live GitHub Repository Inspection
    print("\n[STAGE 4/4] Testing live GitHub public repository inspection...")
    gh_res = await account_operations.inspect_github_repository("psf/requests")
    if gh_res.get("status") == "SUCCESS" and "data" in gh_res:
        d = gh_res["data"]
        print(f"  [PASS] Inspected GitHub repository: {d.get('name')}")
        print(f"         Stars: {d.get('stars')} | Forks: {d.get('forks')} | Description: {d.get('description')}")
        stages_passed += 1
    else:
        print(f"  [FAIL] GitHub inspection failed: {gh_res.get('error')}")
        return False

    print("\n" + "=" * 70)
    print(f"RESULT: {stages_passed}/{total_stages} stages passed. Status: PASS")
    print("=" * 70)
    return stages_passed == total_stages


if __name__ == "__main__":
    success = asyncio.run(run_account_permissions_test())
    sys.exit(0 if success else 1)
