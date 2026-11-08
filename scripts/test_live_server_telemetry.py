"""MATRIX Live Server & Telemetry Comprehensive Verification Script.

Executes live HTTP requests and WebSocket transactions against the running MATRIX server:
1. GET /api/v1/system/telemetry (Comprehensive telemetry: CPU per-core, RAM, disks, host, uptime)
2. GET /api/v1/telemetry (Direct alias)
3. GET /api/v1/system/metrics (HUD live metrics)
4. GET /api/v1/system/info (Static hardware & OS specifications)
5. GET /api/v1/health (System and database readiness)
6. GET /openapi.json (OpenAPI route conformance)
7. WebSocket ws://127.0.0.1:8000/ws/events (Bidirectional event protocol)

Saves verified outputs and telemetry to docs/live_server_telemetry_raw.json.
"""
import sys
import time
import json
import asyncio
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/events"


class LiveServerTelemetryVerifier:
    def __init__(self):
        self.results = []

    def record(self, endpoint: str, status: str, latency_ms: float, evidence: str, data: dict = None):
        entry = {
            "endpoint": endpoint,
            "status": status,
            "latency_ms": round(latency_ms, 2),
            "evidence": evidence,
            "data": data or {}
        }
        self.results.append(entry)
        status_tag = f"[{status:<7}]"
        print(f"{status_tag} {endpoint:<35} ({latency_ms:6.1f}ms) -> {evidence[:70]}")

    async def run_all(self):
        print("=" * 90)
        print(" MATRIX — LIVE SERVER & TELEMETRY ACCEPTANCE TEST")
        print("=" * 90)

        # 1. Test /api/v1/system/telemetry
        self.test_system_telemetry()

        # 2. Test /api/v1/telemetry (alias)
        self.test_telemetry_alias()

        # 3. Test /api/v1/system/metrics
        self.test_system_metrics()

        # 4. Test /api/v1/system/info
        self.test_system_info()

        # 5. Test /api/v1/health
        self.test_health()

        # 6. Test OpenAPI routes match
        self.test_openapi_routes()

        # 7. Test WebSocket
        await self.test_websocket()

        self.save_raw_json()
        print("=" * 90)
        total_passed = sum(1 for r in self.results if r["status"] == "PASS")
        print(f" LIVE SERVER TESTS: {total_passed}/{len(self.results)} PASSED ({total_passed/len(self.results)*100:.1f}%)")
        print("=" * 90)

    def test_system_telemetry(self):
        url = f"{BASE_URL}/api/v1/system/telemetry"
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                dt = (time.perf_counter() - t0) * 1000
                data = json.loads(resp.read().decode())
                has_cpu = "cpu" in data and "percent" in data["cpu"] and "per_cpu_percent" in data["cpu"]
                has_mem = "memory" in data and "available_mb" in data["memory"]
                has_storage = "storage" in data and "C:" in data["storage"]
                passed = resp.status == 200 and has_cpu and has_mem and has_storage
                evidence = (
                    f"Status {resp.status}, CPU: {data['cpu']['percent']}%, "
                    f"Threads: {len(data['cpu']['per_cpu_percent'])}, RAM Avail: {data['memory']['available_mb']}MB, "
                    f"Uptime: {data.get('uptime_seconds')}s"
                )
                self.record("/api/v1/system/telemetry", "PASS" if passed else "FAIL", dt, evidence, data)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self.record("/api/v1/system/telemetry", "FAIL", dt, f"Request failed: {e}")

    def test_telemetry_alias(self):
        url = f"{BASE_URL}/api/v1/telemetry"
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                dt = (time.perf_counter() - t0) * 1000
                data = json.loads(resp.read().decode())
                passed = resp.status == 200 and "cpu" in data and "memory" in data
                evidence = f"Status {resp.status}, Alias correctly resolved; RAM Avail: {data['memory']['available_mb']}MB"
                self.record("/api/v1/telemetry (alias)", "PASS" if passed else "FAIL", dt, evidence, data)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self.record("/api/v1/telemetry (alias)", "FAIL", dt, f"Request failed: {e}")

    def test_system_metrics(self):
        url = f"{BASE_URL}/api/v1/system/metrics"
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                dt = (time.perf_counter() - t0) * 1000
                data = json.loads(resp.read().decode())
                passed = resp.status == 200 and "cpu" in data and "memory" in data and "status" in data
                evidence = f"Status {resp.status}, CPU: {data['cpu']['percent']}%, RAM: {data['memory']['percent']}%, Status: {data['status']}"
                self.record("/api/v1/system/metrics", "PASS" if passed else "FAIL", dt, evidence, data)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self.record("/api/v1/system/metrics", "FAIL", dt, f"Request failed: {e}")

    def test_system_info(self):
        url = f"{BASE_URL}/api/v1/system/info"
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                dt = (time.perf_counter() - t0) * 1000
                data = json.loads(resp.read().decode())
                has_hw = "hardware" in data and "AMD" in data["hardware"].get("cpu_name", "")
                passed = resp.status == 200 and has_hw
                evidence = f"Status {resp.status}, CPU: {data['hardware']['cpu_name']}, RAM: {data['hardware']['total_ram_gb']}GB"
                self.record("/api/v1/system/info", "PASS" if passed else "FAIL", dt, evidence, data)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self.record("/api/v1/system/info", "FAIL", dt, f"Request failed: {e}")

    def test_health(self):
        url = f"{BASE_URL}/api/v1/health"
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                dt = (time.perf_counter() - t0) * 1000
                data = json.loads(resp.read().decode())
                db_conn = data.get("database", {}).get("connected", False)
                passed = resp.status == 200 and data.get("status") in ("healthy", "degraded") and db_conn
                evidence = f"Status {resp.status}, Overall: {data.get('status')}, DB Connected: {db_conn}, Latency: {data.get('database', {}).get('latency_ms')}ms"
                self.record("/api/v1/health", "PASS" if passed else "FAIL", dt, evidence, data)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self.record("/api/v1/health", "FAIL", dt, f"Request failed: {e}")

    def test_openapi_routes(self):
        url = f"{BASE_URL}/openapi.json"
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                dt = (time.perf_counter() - t0) * 1000
                data = json.loads(resp.read().decode())
                paths = data.get("paths", {})
                expected = [
                    "/api/v1/system/telemetry",
                    "/api/v1/telemetry",
                    "/api/v1/system/metrics",
                    "/api/v1/system/info",
                    "/api/v1/health"
                ]
                missing = [p for p in expected if p not in paths]
                passed = resp.status == 200 and len(missing) == 0
                evidence = f"Status {resp.status}, Verified {len(paths)} routes in OpenAPI schema. Missing expected: {missing}"
                self.record("OpenAPI Route Conformance", "PASS" if passed else "FAIL", dt, evidence, {"total_routes": len(paths)})
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self.record("OpenAPI Route Conformance", "FAIL", dt, f"Request failed: {e}")

    async def test_websocket(self):
        t0 = time.perf_counter()
        try:
            import websockets
            async with websockets.connect(WS_URL, open_timeout=5) as ws:
                received_types = []
                frames = {}

                # 1. Receive initial server frames (handshake, telemetry)
                for _ in range(2):
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(msg)
                    mtype = data.get("type")
                    received_types.append(mtype)
                    frames[mtype] = data

                # 2. Send ping frame
                payload = json.dumps({"type": "ping", "client": "telemetry_test"})
                await ws.send(payload)

                # 3. Receive until ack is received
                while "ack" not in received_types:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(msg)
                    mtype = data.get("type")
                    received_types.append(mtype)
                    frames[mtype] = data

                dt = (time.perf_counter() - t0) * 1000
                has_handshake = "handshake" in received_types
                has_ack = "ack" in received_types
                has_telemetry = "telemetry_update" in received_types or "telemetry" in received_types

                passed = has_handshake and has_ack
                evidence = f"WebSocket protocol verified. Frames: {received_types}, Handshake: {has_handshake}, Telemetry: {has_telemetry}, Ack: {has_ack}"
                self.record("WebSocket /ws/events", "PASS" if passed else "FAIL", dt, evidence, frames)
        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000
            self.record("WebSocket /ws/events", "FAIL", dt, f"WebSocket test failed: {e}")

    def save_raw_json(self):
        out_path = WORKSPACE_ROOT / "docs" / "live_server_telemetry_raw.json"
        total_latency = sum(r["latency_ms"] for r in self.results)
        payload = {
            "test_suite": "live_server_telemetry_acceptance",
            "timestamp": time.time(),
            "total_endpoints": len(self.results),
            "passed": sum(1 for r in self.results if r["status"] == "PASS"),
            "failed": sum(1 for r in self.results if r["status"] == "FAIL"),
            "total_latency_ms": round(total_latency, 2),
            "results": self.results
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nSaved raw telemetry to: {out_path}")


if __name__ == "__main__":
    verifier = LiveServerTelemetryVerifier()
    asyncio.run(verifier.run_all())
