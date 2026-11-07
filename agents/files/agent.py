"""MATRIX File & Document Intelligence Agent.
Parses, indexes, summarizes, and securely manages documents:
PDF (PyPDF2), DOCX (python-docx), XLSX (openpyxl), CSV, TXT, Markdown, and ZIP archives,
strictly bounded within permitted storage partitions (D:\\matrix_data and active workspace).
"""
from typing import Dict, Any, List
import time
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("agents.files")


class FileAgent(BaseAgent):
    """Handles multi-format document parsing, semantic search, and safe organization."""

    def __init__(self):
        super().__init__(
            name="files",
            description="Manages personal files, reads PDF/DOCX/XLSX/CSV/TXT/ZIP documents, and generates AI summaries.",
            max_autonomy_level=2
        )
        self.allowed_roots = [settings.data_dir, Path.cwd(), Path("D:/matrix_data")]

    def is_path_permitted(self, path: Path) -> bool:
        """Enforce sandbox: reject accesses outside approved workspaces."""
        try:
            resolved = path.resolve()
            for root in self.allowed_roots:
                try:
                    resolved.relative_to(root.resolve())
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("query", parameters.get("raw_prompt", "")).lower()

        # 1. Summarize File
        if "summarize" in action_lower or "summarize" in raw_prompt:
            filepath = parameters.get("filepath", "")
            return await self._summarize_file(Path(filepath), start_time)

        # 2. Read / Parse Document
        if "read" in action_lower or "parse" in action_lower or "open" in action_lower:
            filepath = parameters.get("filepath", "")
            return await self._read_file(Path(filepath), start_time)

        # 3. List / Search Files
        return await self._list_storage_files(start_time)

    def _parse_pdf(self, path: Path) -> str:
        """Extract text from PDF using PyPDF2."""
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(str(path))
            pages_text = []
            for idx, page in enumerate(reader.pages[:20]):
                p_text = page.extract_text() or ""
                if p_text.strip():
                    pages_text.append(f"--- Page {idx+1} ---\n{p_text.strip()}")
            return "\n\n".join(pages_text) or "PDF contains no extractable text."
        except Exception as e:
            return f"PDF parse error: {e}"

    def _parse_docx(self, path: Path) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            import docx
            doc = docx.Document(str(path))
            paras = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paras[:100]) or "DOCX document is empty."
        except Exception as e:
            return f"DOCX parse error: {e}"

    def _parse_xlsx(self, path: Path) -> str:
        """Extract text from Excel spreadsheet using openpyxl."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
            sheet_summaries = []
            for sheetname in wb.sheetnames[:5]:
                ws = wb[sheetname]
                rows = []
                for r_idx, row in enumerate(ws.iter_rows(values_only=True)):
                    if r_idx > 25:
                        break
                    row_vals = [str(v) if v is not None else "" for v in row]
                    if any(row_vals):
                        rows.append(" | ".join(row_vals[:10]))
                sheet_summaries.append(f"Sheet '{sheetname}':\n" + "\n".join(rows))
            wb.close()
            return "\n\n".join(sheet_summaries) or "Spreadsheet is empty."
        except Exception as e:
            return f"XLSX parse error: {e}"

    def _parse_zip(self, path: Path) -> str:
        """Inspect contents of a ZIP archive."""
        try:
            import zipfile
            with zipfile.ZipFile(str(path), 'r') as zf:
                infolist = zf.infolist()
                items = [f"{info.filename} ({info.file_size} bytes)" for info in infolist[:30]]
                return f"ZIP Archive Contents ({len(infolist)} total items):\n" + "\n".join(items)
        except Exception as e:
            return f"ZIP inspection error: {e}"

    async def _read_file(self, path: Path, start_time: float) -> AgentResult:
        """Safely read and parse any supported document type."""
        if not self.is_path_permitted(path):
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="read_file",
                error=f"Access denied: '{path}' is outside approved MATRIX partitions.",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

        if not path.exists():
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="read_file",
                error=f"File not found: '{path}'",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

        try:
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                text_content = self._parse_pdf(path)
            elif suffix in [".docx", ".doc"]:
                text_content = self._parse_docx(path)
            elif suffix in [".xlsx", ".xls"]:
                text_content = self._parse_xlsx(path)
            elif suffix == ".zip":
                text_content = self._parse_zip(path)
            elif suffix in [".txt", ".md", ".json", ".py", ".csv", ".toml", ".yml", ".yaml", ".log"]:
                text_content = path.read_text(encoding="utf-8", errors="replace")[:6000]
            else:
                text_content = f"File format {suffix} ({path.stat().st_size} bytes)."

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="read_file",
                data={
                    "filename": path.name,
                    "filepath": str(path),
                    "format": suffix,
                    "text": text_content[:3000],
                    "size_bytes": path.stat().st_size
                },
                verification={"verified": True, "read_chars": len(text_content)},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="read_file",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def _summarize_file(self, path: Path, start_time: float) -> AgentResult:
        """Extract text from file and use the local AI model to summarize its key points."""
        read_res = await self._read_file(path, start_time)
        if not read_res.success:
            return read_res

        doc_text = read_res.data.get("text", "")
        if not doc_text or len(doc_text.strip()) < 10:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="summarize_file",
                error="Document text was insufficient for summarization.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        try:
            from core.model_manager import model_manager
            summary_prompt = (
                f"Summarize the following document concisely in 3-5 bullet points:\n\n{doc_text[:1500]}"
            )
            model_res = await model_manager.generate_response(
                prompt=summary_prompt,
                system_prompt="You are an expert executive document analyst. Be concise and precise.",
                max_tokens=200
            )
            latency = (time.perf_counter() - start_time) * 1000

            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="summarize_file",
                data={
                    "filename": path.name,
                    "summary": model_res.content.strip(),
                    "model_used": model_res.model_name
                },
                verification={"verified": True, "summary_generated": bool(model_res.content)},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="summarize_file",
                error=f"Summarization error: {e}",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def _list_storage_files(self, start_time: float) -> AgentResult:
        """List files registered in D:\\matrix_data."""
        files = []
        if settings.data_dir.exists():
            for p in settings.data_dir.glob("*"):
                files.append({"name": p.name, "is_dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0})

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="list_storage_files",
            data={"partition": str(settings.data_dir), "files": files},
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
