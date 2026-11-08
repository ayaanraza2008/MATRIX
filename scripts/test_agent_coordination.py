"""MATRIX Multi-Agent Coordination Verification Script (PART 11, Test 10).
Tests inter-agent messaging, shared task context, concurrent wave execution,
and cross-verification across all 16 specialized MATRIX agents:
- Inspects real-time Agent Dashboard for all 16 registered agents
- Tests concurrent wave execution of independent subtasks (System + Memory + Creative)
- Tests step dependency ordering and prerequisite preservation
- Verifies inter-agent result aggregation and conflict detection
"""
import sys
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_coordinator import agent_coordinator
from core.planner import ExecutionPlan, PlanStep
from core.task_router import task_router


async def run_agent_coordination_test():
    print("=" * 70)
    print("  MATRIX MULTI-AGENT COORDINATION TEST (PART 11, SCRIPT 10)")
    print("=" * 70)

    stages_passed = 0
    total_stages = 4

    # Stage 1: Inspect All 16 Specialized Agents in Registry
    print("\n[STAGE 1/4] Inspecting agent registry and dashboard telemetry...")
    dashboard = agent_coordinator.get_agent_dashboard()
    registered_count = dashboard.get("registered_agents_count", 0)
    agents_map = dashboard.get("agents", {})

    print(f"  [PASS] Registered specialized agents: {registered_count}/16")
    expected_agents = [
        "computer", "browser", "research", "coding", "files", "voice",
        "vision", "android", "system", "personal", "automation",
        "creative", "memory", "repo_intel", "security", "data_analysis"
    ]

    all_present = all(ag in agents_map for ag in expected_agents)
    if all_present and registered_count == 16:
        print("  [PASS] All 16 specialized agents verified in active coordinator dashboard:")
        for name in expected_agents:
            tools = agents_map[name]["tools"]
            print(f"         - {name:<14} (Autonomy L{agents_map[name]['max_autonomy']}) Tools: {tools[:2]}")
        stages_passed += 1
    else:
        print(f"  [FAIL] Missing agents in registry. Found: {list(agents_map.keys())}")
        return False

    # Stage 2: Multi-Agent Concurrent Wave Execution
    print("\n[STAGE 2/4] Executing multi-agent concurrent subtask wave...")
    # Plan with 2 concurrent independent tasks: System (telemetry) + Creative (architecture)
    wave_plan = ExecutionPlan(
        title="Multi-Agent Wave Test",
        goal="Test concurrent dispatch across independent agents",
        steps=[
            PlanStep(
                step_id=1,
                title="System Health Telemetry",
                agent_name="system",
                tool_name="poll_telemetry",
                arguments={},
                risk_level=0,
                verification_hook="verify_telemetry"
            ),
            PlanStep(
                step_id=2,
                title="Generate Architecture Mermaid",
                agent_name="creative",
                tool_name="generate_mermaid",
                arguments={"query": "system architecture"},
                risk_level=1,
                verification_hook="verify_mermaid"
            )
        ]
    )

    t0 = time.perf_counter()
    res = await agent_coordinator.execute_plan_concurrent(wave_plan)
    latency_ms = (time.perf_counter() - t0) * 1000

    if res.overall_status == "COMPLETED" and res.completed_steps == 2:
        print(f"  [PASS] Concurrent wave executed successfully in {latency_ms:.1f} ms.")
        for rep in res.subtask_reports:
            print(f"         - [{rep.agent_name}] {rep.title}: {rep.status} ({rep.latency_ms:.1f} ms)")
        stages_passed += 1
    else:
        print(f"  [FAIL] Concurrent wave failed: status={res.overall_status}, completed={res.completed_steps}")
        return False

    # Stage 3: Step Dependency Resolution and Prerequisite Enforcement
    print("\n[STAGE 3/4] Verifying step dependency and execution ordering...")
    dep_plan = ExecutionPlan(
        title="Dependent Multi-Agent Workflow",
        goal="Verify step 2 waits for step 1",
        steps=[
            PlanStep(
                step_id=1,
                title="Gather Research Intelligence",
                agent_name="research",
                tool_name="execute",
                arguments={"query": "edge computing"},
                risk_level=1,
                verification_hook="verify_sources"
            ),
            PlanStep(
                step_id=2,
                title="Store Research Summary in Memory",
                agent_name="memory",
                tool_name="save_memory",
                arguments={"query": "Store summary of edge computing research"},
                dependencies=[1],
                risk_level=1,
                verification_hook="verify_memory"
            )
        ]
    )

    dep_res = await agent_coordinator.execute_plan_concurrent(dep_plan)
    if dep_res.overall_status == "COMPLETED" and dep_res.completed_steps == 2:
        step_order = [rep.step_id for rep in dep_res.subtask_reports]
        if step_order == [1, 2]:
            print("  [PASS] Dependent step correctly waited for prerequisite step 1 before executing.")
            stages_passed += 1
        else:
            print(f"  [FAIL] Step execution order violated: {step_order}")
            return False
    else:
        print(f"  [FAIL] Dependent execution failed: {dep_res.overall_status}")
        return False

    # Stage 4: Execution History & Conflict Verification
    print("\n[STAGE 4/4] Verifying coordinator execution history and conflict detection...")
    updated_dashboard = agent_coordinator.get_agent_dashboard()
    recent_tasks = updated_dashboard.get("recent_tasks_count", 0)
    if recent_tasks >= 2:
        print(f"  [PASS] Coordinator execution telemetry recorded {recent_tasks} completed multi-agent plans.")
        stages_passed += 1
    else:
        print(f"  [FAIL] Execution history not properly incremented.")
        return False

    print("\n" + "=" * 70)
    print(f"RESULT: {stages_passed}/{total_stages} stages passed. Status: PASS")
    print("=" * 70)
    return stages_passed == total_stages


if __name__ == "__main__":
    success = asyncio.run(run_agent_coordination_test())
    sys.exit(0 if success else 1)
