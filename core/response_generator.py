"""MATRIX Response Generator.
Synthesizes agent execution results into concise, natural, professional replies in English, Hindi, or Hinglish.
"""
from typing import Dict, Any, List
from agents.base_agent import AgentResult


class ResponseGenerator:
    """Formats verified agent outcomes into natural JARVIS-style communication."""

    def format_agent_response(self, results: List[AgentResult], original_query: str) -> str:
        """Synthesize multiple agent execution results into a unified summary."""
        if not results:
            return "Task completed."

        # If single result
        if len(results) == 1:
            res = results[0]
            if not res.success:
                return f"Action encountered an impediment: {res.error or 'Verification check failed'}."

            action = res.action_taken
            data = res.data or {}

            if action == "capture_screenshot":
                return f"Screenshot captured and stored in cache ({data.get('filepath')})."
            elif action == "launch_application":
                return f"Application '{data.get('application')}' is open and verified running."
            elif action == "poll_telemetry":
                cpu = data.get("cpu", {}).get("percent", 0)
                ram = data.get("memory", {}).get("percent", 0)
                return f"Telemetry nominal: CPU at {cpu}%, RAM utilization at {ram}%."
            elif action == "query_inventory":
                count = data.get("total_cataloged", 0)
                matched = data.get("matched_count", 0)
                return f"Repository catalog scanned: {matched} relevant entries identified out of {count} verified repositories."
            elif action == "web_research":
                return data.get("report_markdown", f"Research completed for '{data.get('query')}'.")
            elif action == "run_tests":
                return f"Test suite execution completed: {'All tests PASSED' if data.get('passed') else 'Tests FAILED'}."
            elif action == "synthesize_speech":
                return f"Speech synthesized ({data.get('text')})."
            elif action == "evaluate_payload":
                return f"Security audit complete: {data.get('reason')} (Policy Level {data.get('policy_level')})."
            else:
                return f"Action '{action}' executed and verified by agent {res.agent_name}."

        # Multiple steps summary
        lines = [f"Workflow completed ({len(results)} steps verified):"]
        for r in results:
            status_icon = "✓" if r.success else "✗"
            lines.append(f"• {status_icon} [{r.agent_name.upper()}]: {r.action_taken}")
        return "\n".join(lines)


# Global Response Generator singleton
response_generator = ResponseGenerator()
