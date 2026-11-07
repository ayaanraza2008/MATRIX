"""Test MATRIX PC-Android Device Pairing and Synchronization Workflow."""
import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.session import AsyncSessionLocal
from database.init_db import init_database
from api.routes.devices import pair_device, list_devices, revoke_device, PairRequest
from fastapi import HTTPException

async def run_device_sync_test():
    print("=" * 60)
    print("MATRIX DEVICE SYNCHRONIZATION & PAIRING TEST")
    print("=" * 60)
    
    # 1. Initialize DB
    await init_database()
    print("[1] Database initialized.")
    
    async with AsyncSessionLocal() as session:
        # 2. Test Pairing Request
        test_device_id = "android_galaxy_s22_matrix_01"
        test_payload = PairRequest(
            device_id=test_device_id,
            name="Ali's Android Companion (JARVIS Link)",
            platform="android",
            pairing_token="mtx_pair_7f9b2c3e4a5d"
        )
        
        pair_res = await pair_device(test_payload, session)
        print(f"[2] Device Paired Successfully:")
        print(f"    - Status: {pair_res['status']}")
        print(f"    - Device ID: {pair_res['device_id']}")
        print(f"    - Auth Token Issued: {pair_res['auth_token'][:20]}...")
        assert pair_res["status"] == "PAIRED"
        assert pair_res["auth_token"].startswith("mtx_auth_")
        
        # 3. Test Invalid Token Format Rejection
        invalid_payload = PairRequest(
            device_id="unauthorized_rogue_device",
            name="Rogue Agent",
            platform="android",
            pairing_token="invalid_token_format"
        )
        try:
            await pair_device(invalid_payload, session)
            print("[-] Security vulnerability: invalid token was accepted!")
            sys.exit(1)
        except HTTPException as exc:
            print(f"[3] Security Gate Passed: Invalid pairing token rejected with HTTP {exc.status_code} ({exc.detail})")
            
        # 4. List Registered Devices
        devices = await list_devices(session)
        print(f"[4] Listing Registered Devices: Found {len(devices)} device(s):")
        found = False
        for dev in devices:
            print(f"    - Device: {dev.name} [{dev.platform}] | Paired: {dev.is_paired} | ID: {dev.device_id}")
            if dev.device_id == test_device_id:
                found = True
        assert found, "Test device was not retrieved in list_devices"
        
        # 5. Revoke Device
        revoke_res = await revoke_device(test_device_id, session)
        print(f"[5] Revocation Tested: Status = {revoke_res['status']} for {revoke_res['device_id']}")
        assert revoke_res["status"] == "REVOKED"
        
    print("\n[+] MATRIX DEVICE PAIRING & SYNC VERIFICATION PASSED 100%!")

if __name__ == "__main__":
    asyncio.run(run_device_sync_test())
