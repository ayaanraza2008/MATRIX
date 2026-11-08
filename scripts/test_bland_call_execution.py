"""MATRIX Bland AI Outbound Call Execution Test.
Initiates exactly ONE test call to +919193002500.
Records call ID, status, and responses.
"""
import asyncio
import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from core.telephony.bland_client import (
    bland_client,
    DEFAULT_MATRIX_PHONE_TASK,
    DEFAULT_OPENING_SENTENCE
)

TARGET_NUMBER = "+919193002500"

async def run_call_test():
    print("=" * 80)
    print("MATRIX BLAND AI OUTBOUND CALL TEST")
    print(f"Target Number: {TARGET_NUMBER}")
    print(f"Bland API Base: {bland_client.base_url}")
    print(f"Masked API Key: {bland_client.get_masked_api_key()}")
    print("=" * 80)

    # 1. Check account info and credits
    account = await bland_client.get_account_info()
    print("1. Account Status:")
    print(json.dumps(account, indent=2))

    # 2. Check capabilities
    caps = await bland_client.verify_target_capabilities(TARGET_NUMBER)
    print("\n2. Target Capabilities Check:")
    print(json.dumps(caps, indent=2))

    # 3. Dispatch exactly ONE outbound call
    print(f"\n3. Dispatching ONE Outbound Call to {TARGET_NUMBER}...")
    res = await bland_client.send_call(
        phone_number=TARGET_NUMBER,
        first_sentence=DEFAULT_OPENING_SENTENCE,
        task=DEFAULT_MATRIX_PHONE_TASK,
        voice="ryan",
        max_duration=3,
        record=True,
        metadata={"caller": "MATRIX AI Workstation", "purpose": "telephony_verification"}
    )
    print("Dispatch Result:")
    print(json.dumps(res, indent=2))

    call_id = res.get("call_id")
    if call_id:
        print(f"\n4. Monitoring Call Lifecycle for Call ID: {call_id}")
        # Poll status for up to 30 seconds
        for i in range(6):
            await asyncio.sleep(5)
            details = await bland_client.get_call_details(call_id)
            status = details.get("status")
            length = details.get("call_length", 0)
            completed = details.get("completed", False)
            print(f"   [T+{(i+1)*5}s] Call Status: {status} | Length: {length}s | Completed: {completed}")
            if completed or status in ["completed", "failed", "no-answer", "busy", "canceled"]:
                print("\nFinal Call Details:")
                print(json.dumps(details, indent=2))
                break

    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_call_test())
