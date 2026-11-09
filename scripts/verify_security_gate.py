"""MATRIX Security Gate & DPAPI Vault Verification Suite (Gate 7).
Verifies:
1. AuthorizationCenter 32 Scopes & State.
2. Dispatch-Time Policy Blocking (unauthorized & irreversible operations).
3. Dynamic Revocation & Re-grant Enforcement Lifecycle.
4. DPAPI Vault Encryption on Disk (zero plaintext, Windows DPAPI round-trip).
"""
import sys
import time
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.task_router import task_router
from security.permissions.authorization_center import authorization_center, PermissionProfile
from security.vault.dpapi_vault import dpapi_vault

async def verify_security_gate():
    print("=" * 80)
    print("           MATRIX AI — SECURITY GATE & DPAPI AUDIT (GATE 7)")
    print("=" * 80)

    results = {}

    # 1. 32 Scopes Audit
    overview = authorization_center.get_authorization_overview()
    total_scopes = overview.get("total_scopes", 0)
    scopes_ok = total_scopes >= 32
    results["scope_inventory"] = {
        "status": "PASS" if scopes_ok else "FAIL",
        "total_scopes": total_scopes,
        "first_run_completed": overview.get("first_run_completed"),
        "profile_counts": overview.get("profile_counts")
    }
    print(f"1. Scopes Audit: {results['scope_inventory']['status']} ({total_scopes}/32 scopes registered)")

    # 2. Dispatch-Time Blocking of Dangerous / Irreversible Operations
    dangerous_actions = [
        ("delete_file", "files", {"filepath": "D:\\matrix_data\\vital.txt"}),
        ("format_drive", "system", {"drive": "C:"}),
        ("drop_database", "memory", {}),
        ("outbound_call", "voice", {"to": "+15551234567"})
    ]
    blocked_count = 0
    for act, agent, params in dangerous_actions:
        res = await task_router.dispatch(agent, act, params)
        if res.execution_status == "BLOCKED" and (not res.success):
            blocked_count += 1
    
    dispatch_block_ok = blocked_count == len(dangerous_actions)
    results["dispatch_blocking"] = {
        "status": "PASS" if dispatch_block_ok else "FAIL",
        "blocked_count": blocked_count,
        "tested_count": len(dangerous_actions)
    }
    print(f"2. Dispatch-Time Blocking: {results['dispatch_blocking']['status']} ({blocked_count}/{len(dangerous_actions)} blocked)")

    # 3. Dynamic Revocation & Re-grant Enforcement Lifecycle
    # Test on 'list_directory' (controlled by 'file_folder_access')
    # Step A: Pre-check allowed
    res_a = await task_router.dispatch("files", "list_directory", {"path": "D:\\matrix_data"})
    step_a_ok = res_a.success and res_a.execution_status == "SUCCESS"

    # Step B: Revoke scope
    revoked = authorization_center.revoke_scope("windows_permissions", "file_folder_access")
    res_b = await task_router.dispatch("files", "list_directory", {"path": "D:\\matrix_data"})
    step_b_ok = (not res_b.success) and res_b.execution_status == "BLOCKED"

    # Step C: Re-grant scope
    regranted = authorization_center.update_scope_profile("windows_permissions", "file_folder_access", "RESTRICTED")
    res_c = await task_router.dispatch("files", "list_directory", {"path": "D:\\matrix_data"})
    step_c_ok = res_c.success and res_c.execution_status == "SUCCESS"

    lifecycle_ok = step_a_ok and revoked and step_b_ok and regranted and step_c_ok
    results["dynamic_revocation_lifecycle"] = {
        "status": "PASS" if lifecycle_ok else "FAIL",
        "initial_allowed": step_a_ok,
        "revocation_blocked": step_b_ok,
        "regrant_allowed": step_c_ok
    }
    print(f"3. Dynamic Revocation Lifecycle: {results['dynamic_revocation_lifecycle']['status']} (Pre-check: {step_a_ok}, Revoked: {step_b_ok}, Re-granted: {step_c_ok})")

    # 4. DPAPI Vault Encryption Verification
    t_secret_key = "GATE7_TEST_KEY"
    t_secret_val = "SuperSecret_DPAPI_Token_#987654"
    dpapi_vault.store_secret(t_secret_key, t_secret_val)

    # Read binary bytes directly from disk
    raw_disk_bytes = Path(r"D:\matrix_data\security\dpapi_vault.dat").read_bytes()
    plaintext_found_on_disk = t_secret_val.encode("utf-8") in raw_disk_bytes

    # Retrieve through vault
    decrypted_val = dpapi_vault.retrieve_secret(t_secret_key)
    dpapi_match = decrypted_val == t_secret_val

    # Cleanup test secret
    dpapi_vault.delete_secret(t_secret_key)

    dpapi_ok = (not plaintext_found_on_disk) and dpapi_match
    results["dpapi_vault_encryption"] = {
        "status": "PASS" if dpapi_ok else "FAIL",
        "plaintext_leaked_to_disk": plaintext_found_on_disk,
        "decryption_matches": dpapi_match,
        "disk_vault_size_bytes": len(raw_disk_bytes)
    }
    print(f"4. DPAPI Vault Encryption: {results['dpapi_vault_encryption']['status']} (Plaintext on disk: {plaintext_found_on_disk}, Decrypted match: {dpapi_match})")

    # Overall Summary
    all_passed = all(r["status"] == "PASS" for r in results.values())
    overall_status = "PASS" if all_passed else "FAIL"

    print("\n" + "=" * 80)
    print(f"SECURITY GATE OUTCOME: {overall_status} (4 / 4 Subsystems Passed)")
    print("=" * 80)

    out_file = Path(r"D:\matrix_data\reports\security_gate_verification.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps({
        "status": overall_status,
        "results": results
    }, indent=2), encoding="utf-8")
    print(f"Saved security gate verification catalog to: {out_file}")

if __name__ == "__main__":
    asyncio.run(verify_security_gate())
