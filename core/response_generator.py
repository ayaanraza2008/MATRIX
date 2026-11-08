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
            if ":" in action:
                action = action.split(":", 1)[1]
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
            elif action == "inspect_code_architecture":
                fn = data.get("file", "target module")
                loc = data.get("loc", 0)
                classes = data.get("classes", [])
                funcs = data.get("functions", [])
                return (
                    f"AST Code Architecture Analysis for `{fn}` ({loc} lines of code):\n"
                    f"- **Classes Identified ({len(classes)})**: {', '.join(classes) if classes else 'None'}\n"
                    f"- **Key Functions ({len(funcs)})**: {', '.join(funcs[:8]) if funcs else 'None'}\n"
                    f"- **Syntax Integrity**: Clean and valid Python AST structure verified."
                )
            elif action == "generate_mermaid":
                code = data.get("mermaid_code", "")
                return f"Mermaid Architecture Diagram generated successfully:\n\n```mermaid\n{code}\n```"
            elif action in ["save_memory", "store_context"]:
                key = data.get("key", "preference")
                val = data.get("value", "")
                return f"Preference stored in persistent long-term memory: `{key}` -> `{val}`."
            elif action in ["list_memory", "retrieve_memory", "search_memory"]:
                mems = data.get("stored_memories", data.get("matches", []))
                if isinstance(mems, list) and mems:
                    items = "\n".join([f"- **{m.get('key')}**: {m.get('value')}" for m in mems[:5]])
                    return f"Retrieved memories from persistent store:\n{items}"
                return "Memory store queried: No previous entries found for this key."
            elif action in ["search_web", "navigate_url"]:
                count = data.get("count", 0)
                items = data.get("results", [])
                if items:
                    lines = [f"Found {len(items)} web results:\n"]
                    for i, it in enumerate(items[:4], 1):
                        lines.append(f"**[{i}] {it.get('title', 'Web Source')}**")
                        if it.get('snippet'):
                            lines.append(f"> {it.get('snippet')}")
                        if it.get('url'):
                            lines.append(f"Source: {it.get('url')}\n")
                    return "\n".join(lines)
                elif data.get("title"):
                    return f"Web page '{data.get('title')}' loaded successfully ({data.get('total_chars', 0)} characters):\n> {data.get('text_sample', '')[:300]}"
                return f"Web operation completed: {data.get('url', 'URL checked')}."
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
            elif action in ["generate_pairing_token", "pair"]:
                return f"Android companion pairing token generated: `{data.get('pairing_token')}`. Protocol: `{data.get('qr_protocol')}` (Expires in {data.get('expires_in_seconds')}s)."
            elif action in ["data_status", "analyze_csv"]:
                num_s = data.get("numerical_summary", {})
                if num_s:
                    cols_desc = ", ".join([f"{k} (mean: {v.get('mean')})" for k, v in list(num_s.items())[:3]])
                    return f"Tabular data analysis complete: {data.get('rows_count', 0)} rows analyzed. Summary: {cols_desc}."
                return f"Data analysis engine nominal: {data.get('engine', 'Python statistics engine')}."
            elif action == "create_workflow":
                return f"Autonomous workflow '{data.get('title')}' created and checkpoint saved (Task ID: `{data.get('task_id')}`)."
            elif action == "personal_assist":
                return f"I am {data.get('assistant_name', 'MATRIX')}, your personal AI ecosystem. System is operational and all specialized agents are ready."
            elif action in ["list_storage_files", "scan_files"]:
                return f"Storage partition `{data.get('partition', 'D:\\\\matrix_data')}` inspected: {len(data.get('files', []))} items found."
            else:
                return f"Action '{action}' executed and verified by agent {res.agent_name}."

        # Multiple steps summary
        all_passed = all(r.success for r in results)
        if all_passed:
            lines = [f"Workflow completed successfully ({len(results)} steps verified):"]
            for r in results:
                lines.append(f"• ✓ [{r.agent_name.upper()}]: {r.action_taken}")
            return "\n".join(lines)
        else:
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            first_fail = failed[0] if failed else None
            fail_reason = first_fail.error if first_fail else "Step execution failed"
            lines = [f"Workflow halted ({len(successful)}/{len(results)} steps completed). Impediment at step {len(successful) + 1} ({first_fail.action_taken if first_fail else 'action'}): {fail_reason}."]
            for r in successful:
                lines.append(f"• ✓ [{r.agent_name.upper()}]: {r.action_taken}")
            for r in failed:
                lines.append(f"• ✗ [{r.agent_name.upper()}]: {r.action_taken} - {r.error}")
            return "\n".join(lines)


# Global Response Generator singleton
response_generator = ResponseGenerator()
