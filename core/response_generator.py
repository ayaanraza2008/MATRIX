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

            if action == "inspect_screen":
                return data.get("visual_summary", f"Screen inspected: {data.get('resolution', 'display')}.")
            elif action == "capture_camera":
                summary = data.get("scene_summary", "")
                ocr = data.get("ocr_text", "")
                text = f"Camera frame captured ({data.get('width', 640)}x{data.get('height', 480)})."
                if summary:
                    text += f" {summary}"
                if ocr:
                    text += f" Text detected: {ocr[:150]}"
                return text
            elif action in ["capture_screenshot", "screenshot"]:
                return f"Screenshot captured: {data.get('filepath', 'saved to cache')}."
            elif action == "read_file":
                filename = data.get("filename", "file")
                snippet = data.get("text", "")[:400]
                return f"Read document '{filename}' ({data.get('size_bytes', 0)} bytes):\n\n{snippet}"
            elif action == "summarize_file":
                filename = data.get("filename", "file")
                summary = data.get("summary", "")
                return f"Executive Summary for '{filename}':\n\n{summary}"
            elif action == "search_web":
                count = data.get("count", 0)
                items = data.get("results", [])
                lines = [f"Found {count} web results for '{data.get('query')}':\n"]
                for i, it in enumerate(items[:4], 1):
                    lines.append(f"**[{i}] {it.get('title')}**")
                    if it.get('snippet'):
                        lines.append(f"> {it.get('snippet')}")
                    if it.get('url'):
                        lines.append(f"Source: {it.get('url')}\n")
                return "\n".join(lines)
            elif action == "launch_application":
                return f"Application '{data.get('application')}' is open and verified running."
            elif action == "execute_command":
                out = data.get("stdout", "").strip()
                return f"Command `{data.get('command')}` executed successfully:\n```\n{out}\n```"
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
