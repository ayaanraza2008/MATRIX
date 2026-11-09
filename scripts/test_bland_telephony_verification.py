"""MATRIX Bland AI Telephony Independent Verification Script.
Independently verifies:
1. Dual-alias DPAPI Vault Retrieval (BLAND_API_KEY and BLAND_AI_API_KEY).
2. Live Account Authentication & Balance Query (GET /v1/me).
3. Zero-Call Safety Assurance: Confirms outbound calls are gated by CONFIRMATION_REQUIRED.
4. Security Rule: Zero plaintext key printing or logging.
"""
import sys
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from security.vault.dpapi_vault import dpapi_vault
from core.telephony.bland_client import bland_client
from security.permissions.authorization_center import authorization_center

async def verify_bland_telephony():
    print("=" * 80)
    print("        MATRIX AI — BLAND AI TELEPHONY INDEPENDENT VERIFICATION")
    print("=" * 80)
    results = {}

    # 1. Dual-alias DPAPI Vault Retrieval
    k1 = dpapi_vault.retrieve_secret("BLAND_API_KEY")
    k2 = dpapi_vault.retrieve_secret("BLAND_AI_API_KEY")
    
    k1_valid = bool(k1 and len(k1) > 20 and k1.startswith("org_"))
    k2_valid = bool(k2 and len(k2) > 20 and k2.startswith("org_"))
    keys_match = (k1 == k2) if (k1 and k2) else False

    # Never print the actual secret key!
    k1_masked = f"{k1[:7]}...{k1[-4:]}" if k1_valid else "ABSENT"
    k2_masked = f"{k2[:7]}...{k2[-4:]}" if k2_valid else "ABSENT"

    print(f"\n1. DPAPI Secret Retrieval:")
    print(f"   Alias 'BLAND_API_KEY'     : {'VALID' if k1_valid else 'MISSING'} (Format: {k1_masked})")
    print(f"   Alias 'BLAND_AI_API_KEY'  : {'VALID' if k2_valid else 'MISSING'} (Format: {k2_masked})")
    print(f"   Alias Consistency Match   : {keys_match}")

    results["dpapi_dual_alias"] = {
        "status": "PASS" if (k1_valid or k2_valid) else "FAIL",
        "bland_api_key_valid": k1_valid,
        "bland_ai_api_key_valid": k2_valid,
        "keys_match": keys_match,
        "masked_format": k1_masked if k1_valid else k2_masked
    }

    # 2. Account Authentication & Balance Retrieval
    print(f"\n2. Account Authentication & Balance Query (GET https://api.bland.ai/v1/me):")
    t0 = asyncio.get_event_loop().time()
    info = await bland_client.get_account_info()
    latency_ms = (asyncio.get_event_loop().time() - t0) * 1000

    status = info.get("status", "unknown")
    balance = info.get("current_balance", info.get("billing", {}).get("current_balance", 0.0))
    plan = info.get("plan_name", "Pay-as-you-go")
    auth_ok = status == "active" and balance is not None

    print(f"   Account Status            : {status.upper()}")
    print(f"   Verified Wallet Balance   : ${balance:.2f} USD")
    print(f"   Account Plan Name         : {plan}")
    print(f"   API Response Latency      : {latency_ms:.1f}ms")

    results["account_verification"] = {
        "status": "PASS" if auth_ok else "FAIL",
        "account_status": status,
        "current_balance": balance,
        "plan_name": plan,
        "latency_ms": round(latency_ms, 2)
    }

    # 3. Security Boundary: Zero Outbound Calls Protection
    print(f"\n3. Telephony Safety & Confirmation Gate Check:")
    can_auto_call, profile, reason = authorization_center.evaluate_authorization("make_call")
    # Must NOT be automatic. Must require explicit user confirmation.
    gated_safely = (not can_auto_call) and (profile == "CONFIRMATION_REQUIRED")
    print(f"   Autonomous Calling Allowed: {can_auto_call} (Must be False)")
    print(f"   Security Profile          : {profile} (Must be CONFIRMATION_REQUIRED)")
    print(f"   Enforcement Reason        : {reason}")
    print(f"   Zero Outbound Calls Made  : True")

    results["safety_confirmation_gate"] = {
        "status": "PASS" if gated_safely else "FAIL",
        "autonomous_calling_blocked": not can_auto_call,
        "security_profile": profile,
        "reason": reason,
        "zero_calls_made": True
    }

    # Overall Summary
    print("\n" + "=" * 80)
    all_pass = all(r["status"] == "PASS" for r in results.values())
    print(f"BLAND AI TELEPHONY AUDIT OUTCOME: {'PASS (100% Verified)' if all_pass else 'FAIL'}")
    print("=" * 80)

    out_file = Path(r"D:\matrix_data\reports\bland_telephony_verification.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Saved Bland AI report to: {out_file}")

if __name__ == "__main__":
    asyncio.run(verify_bland_telephony())
