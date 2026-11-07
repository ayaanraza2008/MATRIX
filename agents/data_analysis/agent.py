"""MATRIX Data Analysis Agent.
Performs tabular data extraction, statistical calculations, CSV processing, and numerical analysis.
"""
from typing import Dict, Any, List
import time
import csv
import statistics
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult


class DataAnalysisAgent(BaseAgent):
    """Processes datasets, calculates statistical summaries, and manipulates tabular files."""

    def __init__(self):
        super().__init__(
            name="data_analysis",
            description="Analyzes CSV/tabular data, computes descriptive statistics, and generates summaries.",
            max_autonomy_level=1
        )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        csv_path_str = parameters.get("csv_path", "")

        if csv_path_str and Path(csv_path_str).exists():
            summary = self._analyze_csv(Path(csv_path_str))
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="analyze_csv",
                data=summary,
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="data_status",
            data={"engine": "Python Built-in Statistics & CSV Engine", "ready": True},
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    def _analyze_csv(self, path: Path) -> Dict[str, Any]:
        """Compute statistical summary on numerical columns of a CSV file."""
        with open(path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return {"rows_count": 0, "columns": []}

        columns = list(rows[0].keys())
        stats_summary = {}

        for col in columns:
            num_vals = []
            for r in rows:
                try:
                    val = float(r[col])
                    num_vals.append(val)
                except (ValueError, TypeError):
                    pass

            if num_vals:
                stats_summary[col] = {
                    "count": len(num_vals),
                    "mean": round(statistics.mean(num_vals), 2),
                    "min": min(num_vals),
                    "max": max(num_vals)
                }

        return {
            "rows_count": len(rows),
            "columns": columns,
            "numerical_summary": stats_summary
        }

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
