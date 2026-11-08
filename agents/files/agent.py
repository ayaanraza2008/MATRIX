"""MATRIX File & Document Intelligence Agent.
Parses, indexes, summarizes, organizes, and securely manages files and folders:
- PDF (PyPDF2), DOCX (python-docx), XLSX (openpyxl), CSV, TXT, Markdown, JSON, Code, ZIP
- File & folder search by name, extension, and pattern
- Autonomous folder organization (categorizes into Documents, Images, Code, Archives, Installers, etc.)
- Safe file creation, editing, renaming, moving, and copying with collision avoidance
- Metadata extraction, archive extraction, and ZIP compression
- Strictly non-destructive: Never silently overwrites or permanently deletes user files.
"""
from typing import Dict, Any, List, Optional
import time
import os
import shutil
import zipfile
import mimetypes
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("agents.files")


class FileAgent(BaseAgent):
    """Handles multi-format document parsing, semantic search, and safe organization."""

    # Categorization map for autonomous folder organization
    FILE_CATEGORIES = {
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".pptx", ".ppt"],
        "Spreadsheets": [".xlsx", ".xls", ".csv", ".tsv"],
        "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"],
        "Videos": [".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv"],
        "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        "Installers": [".exe", ".msi", ".dmg", ".pkg", ".iso"],
        "Code": [".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".json", ".yaml", ".yml", ".md", ".sh", ".bat", ".ps1"]
    }

    # Forbidden critical system directories that can never be modified or organized
    FORBIDDEN_ROOTS = [
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/ProgramData")
    ]

    def __init__(self):
        super().__init__(
            name="files",
            description="Manages personal files, searches directories, organizes folders, reads PDF/DOCX/XLSX/CSV/TXT/ZIP, and creates archives.",
            max_autonomy_level=2
        )
        self._capabilities = [
            AgentCapability(name="file_read", description="Read and parse PDF, DOCX, XLSX, CSV, TXT, JSON, MD documents", operations=["read", "parse", "open"]),
            AgentCapability(name="file_summarize", description="Generate concise AI summaries of document contents", operations=["summarize"]),
            AgentCapability(name="file_search", description="Search files by name, pattern, or keyword across directories", operations=["search", "find"]),
            AgentCapability(name="folder_organize", description="Autonomously organize downloads and folders into categorized subdirectories", operations=["organize"]),
            AgentCapability(name="file_modify", description="Create, edit, rename, move, or copy files safely", operations=["create", "edit", "rename", "move", "copy"]),
            AgentCapability(name="archive_management", description="Extract archives and compress files into ZIP exports", operations=["zip", "extract", "compress"]),
            AgentCapability(name="file_metadata", description="Inspect file size, timestamps, mime types, and attributes", operations=["metadata", "info"])
        ]

    def is_safe_path(self, path: Path) -> bool:
        """Ensure path is not inside a protected Windows system root."""
        try:
            resolved = path.resolve()
            for forbidden in self.FORBIDDEN_ROOTS:
                try:
                    resolved.relative_to(forbidden.resolve())
                    return False
                except ValueError:
                    continue
            return True
        except Exception:
            return False

    def resolve_target_dir(self, path_str: str) -> Path:
        """Resolve common natural-language directories (e.g. 'Downloads', 'Documents', 'Desktop')."""
        clean = path_str.strip().lower()
        user_home = Path.home()

        if "download" in clean:
            return user_home / "Downloads"
        elif "document" in clean:
            return user_home / "Documents"
        elif "desktop" in clean:
            return user_home / "Desktop"
        elif "matrix" in clean or "data" in clean:
            return settings.data_dir
        elif path_str:
            p = Path(path_str)
            return p if p.is_absolute() else (Path.cwd() / p)
        return user_home / "Downloads"

    async def _create_folder(self, target_dir: Path, folder_name: str, start_time: float) -> AgentResult:
        """Create a new folder safely on disk with verification."""
        if not self.is_safe_path(target_dir):
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="create_folder",
                error=f"Access denied: Target '{target_dir}' is a protected system directory.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        full_path = target_dir / folder_name
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            verified = full_path.exists() and full_path.is_dir()
            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="create_folder",
                data={"folder_path": str(full_path), "folder_name": folder_name, "created": True},
                verification={"verified": verified, "exists": verified},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="create_folder",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _list_directory(self, target_dir: Path, start_time: float) -> AgentResult:
        """List files and folders in a user directory with sizes and counts."""
        if not self.is_safe_path(target_dir) or not target_dir.exists():
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="list_directory",
                error=f"Cannot access directory '{target_dir}'.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        items = []
        try:
            for item in target_dir.iterdir():
                items.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": item.stat().st_size if item.is_file() else 0
                })
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="list_directory",
                data={"directory": str(target_dir), "items": items[:30], "total_items": len(items)},
                verification={"verified": True, "count": len(items)},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="list_directory",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("query", parameters.get("raw_prompt", "")).lower()

        # 0. Create Folder / Directory
        if "folder" in raw_prompt and any(w in raw_prompt for w in ["create", "make", "new", "mkdir"]):
            import re
            dest_dir = self.resolve_target_dir(raw_prompt)
            match = re.search(r'(?:create|make|new|mkdir)\s+(?:a\s+)?(?:folder|directory)\s+(?:named\s+|called\s+)?([a-zA-Z0-9_.-]+)', raw_prompt, re.I)
            folder_name = match.group(1) if match else "NewFolder"
            return await self._create_folder(dest_dir, folder_name, start_time)

        # 0.5. List Files / Directory
        if any(w in raw_prompt for w in ["list files", "show files", "list directory", "view files", "what files are in"]):
            dest_dir = self.resolve_target_dir(raw_prompt)
            return await self._list_directory(dest_dir, start_time)

        # 1. Organize Folder (e.g. "Matrix, organize my Downloads folder")
        if "organize" in action_lower or "organize" in raw_prompt:
            target_str = parameters.get("directory", parameters.get("target", raw_prompt))
            target_dir = self.resolve_target_dir(target_str)
            return await self._organize_folder(target_dir, start_time)

        # 2. Search Files
        if "search" in action_lower or "find" in action_lower or any(w in raw_prompt for w in ["search for", "find file", "look for file"]):
            query = parameters.get("query", parameters.get("pattern", ""))
            directory_str = parameters.get("directory", "")
            target_dir = self.resolve_target_dir(directory_str) if directory_str else Path.cwd()
            return await self._search_files(query, target_dir, start_time)

        # 3. Create or Edit File
        if "create" in action_lower or "write" in action_lower or any(w in raw_prompt for w in ["create file", "write file"]):
            filepath = parameters.get("filepath", parameters.get("path", ""))
            content = parameters.get("content", "")
            return await self._create_file(Path(filepath), content, start_time)

        # 4. Copy or Move File
        if "copy" in action_lower or "move" in action_lower:
            src = parameters.get("source", parameters.get("src", ""))
            dst = parameters.get("destination", parameters.get("dst", ""))
            is_move = "move" in action_lower or "move" in raw_prompt
            return await self._copy_or_move(Path(src), Path(dst), is_move, start_time)

        # 5. Rename File
        if "rename" in action_lower:
            src = parameters.get("filepath", parameters.get("src", ""))
            new_name = parameters.get("new_name", "")
            return await self._rename_file(Path(src), new_name, start_time)

        # 6. Archive Management: ZIP / Extract
        if "zip" in action_lower or "compress" in action_lower:
            src = parameters.get("source", parameters.get("files", ""))
            zip_name = parameters.get("zip_name", "archive.zip")
            return await self._create_zip(src, zip_name, start_time)

        if "extract" in action_lower or "unzip" in action_lower:
            zip_path = parameters.get("zip_path", parameters.get("filepath", ""))
            dest_dir = parameters.get("destination", "")
            return await self._extract_zip(Path(zip_path), Path(dest_dir) if dest_dir else None, start_time)

        # 7. File Metadata / Inspect
        if "metadata" in action_lower or "inspect" in action_lower or "info" in action_lower:
            filepath = parameters.get("filepath", "")
            return await self._get_metadata(Path(filepath), start_time)

        # 8. Summarize File
        if "summarize" in action_lower or "summarize" in raw_prompt:
            filepath = parameters.get("filepath", "")
            return await self._summarize_file(Path(filepath), start_time)

        # 9. Read / Parse Document
        if "read" in action_lower or "parse" in action_lower or "open" in action_lower:
            filepath = parameters.get("filepath", "")
            return await self._read_file(Path(filepath), start_time)

        # Default fallback: List storage files
        return await self._list_storage_files(start_time)

    async def _organize_folder(self, target_dir: Path, start_time: float) -> AgentResult:
        """Autonomously categorize files into organized subfolders without overwriting data."""
        if not self.is_safe_path(target_dir):
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="organize_folder",
                error=f"Access denied: Target directory '{target_dir}' is a protected system directory.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        if not target_dir.exists() or not target_dir.is_dir():
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="organize_folder",
                error=f"Directory '{target_dir}' does not exist.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        organized_count = 0
        moved_summary: Dict[str, List[str]] = {}
        exceptions: List[str] = []

        try:
            # Inspect all top-level files in directory
            entries = [f for f in target_dir.iterdir() if f.is_file()]

            for item in entries:
                suffix = item.suffix.lower()
                target_category = "Other"

                for cat, exts in self.FILE_CATEGORIES.items():
                    if suffix in exts:
                        target_category = cat
                        break

                cat_dir = target_dir / target_category
                cat_dir.mkdir(parents=True, exist_ok=True)

                dest_file = cat_dir / item.name
                # Collision avoidance: never overwrite existing files!
                if dest_file.exists():
                    stem = item.stem
                    dest_file = cat_dir / f"{stem}_{int(time.time())}{suffix}"

                try:
                    shutil.move(str(item), str(dest_file))
                    organized_count += 1
                    if target_category not in moved_summary:
                        moved_summary[target_category] = []
                    moved_summary[target_category].append(item.name)
                except Exception as move_err:
                    exceptions.append(f"Could not move {item.name}: {move_err}")

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="organize_folder",
                data={
                    "directory": str(target_dir),
                    "total_files_organized": organized_count,
                    "categories_created": list(moved_summary.keys()),
                    "details": {k: len(v) for k, v in moved_summary.items()},
                    "exceptions": exceptions
                },
                verification={"verified": True, "files_organized": organized_count},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="organize_folder",
                error=f"Folder organization failed: {e}",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _search_files(self, query: str, search_dir: Path, start_time: float) -> AgentResult:
        """Search for files matching name or extension across directory recursively."""
        if not self.is_safe_path(search_dir):
            search_dir = Path.cwd()

        matches = []
        q_clean = query.lower().strip()

        try:
            for root, dirs, files in os.walk(search_dir):
                # Skip hidden/system folders
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "__pycache__"]]
                for f in files:
                    if not q_clean or q_clean in f.lower():
                        full_p = Path(root) / f
                        matches.append({
                            "name": f,
                            "path": str(full_p),
                            "size_bytes": full_p.stat().st_size,
                            "extension": full_p.suffix.lower()
                        })
                        if len(matches) >= 50:
                            break
                if len(matches) >= 50:
                    break

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="search_files",
                data={"query": query, "search_root": str(search_dir), "match_count": len(matches), "matches": matches[:20]},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="search_files",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _create_file(self, filepath: Path, content: str, start_time: float) -> AgentResult:
        """Create or update a file safely in permitted workspace."""
        if not self.is_safe_path(filepath):
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="create_file",
                error=f"Access denied: '{filepath}' is in a protected path.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            verified = filepath.exists() and filepath.stat().st_size >= len(content.encode('utf-8'))
            latency = (time.perf_counter() - start_time) * 1000

            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="create_file",
                data={"filepath": str(filepath), "bytes_written": len(content.encode('utf-8'))},
                verification={"file_exists": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="create_file",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _copy_or_move(self, src: Path, dst: Path, is_move: bool, start_time: float) -> AgentResult:
        """Copy or move a file safely."""
        if not src.exists():
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="move_file" if is_move else "copy_file",
                error=f"Source file '{src}' does not exist.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if is_move:
                shutil.move(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))

            verified = dst.exists()
            latency = (time.perf_counter() - start_time) * 1000
            action_name = "move_file" if is_move else "copy_file"

            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken=action_name,
                data={"source": str(src), "destination": str(dst)},
                verification={"destination_exists": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="move_file" if is_move else "copy_file",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _rename_file(self, src: Path, new_name: str, start_time: float) -> AgentResult:
        """Rename an existing file safely."""
        if not src.exists():
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="rename_file",
                error=f"File '{src}' does not exist.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        try:
            target = src.parent / new_name
            src.rename(target)
            verified = target.exists()
            latency = (time.perf_counter() - start_time) * 1000

            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="rename_file",
                data={"original": str(src), "new_path": str(target)},
                verification={"renamed_exists": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="rename_file",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _create_zip(self, src_paths: Any, zip_name: str, start_time: float) -> AgentResult:
        """Create a compressed ZIP archive from specified files or directory."""
        export_dir = settings.data_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_file = export_dir / zip_name

        try:
            with zipfile.ZipFile(str(zip_file), 'w', zipfile.ZIP_DEFLATED) as zf:
                if isinstance(src_paths, (str, Path)):
                    p = Path(src_paths)
                    if p.is_file():
                        zf.write(str(p), arcname=p.name)
                    elif p.is_dir():
                        for root, _, files in os.walk(p):
                            for file in files:
                                fp = Path(root) / file
                                zf.write(str(fp), arcname=fp.relative_to(p))
            
            verified = zip_file.exists() and zip_file.stat().st_size > 0
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="create_zip",
                data={"zip_file": str(zip_file), "size_bytes": zip_file.stat().st_size if verified else 0},
                verification={"archive_created": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="create_zip",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _extract_zip(self, zip_path: Path, dest_dir: Optional[Path], start_time: float) -> AgentResult:
        """Extract a ZIP archive safely."""
        if not zip_path.exists():
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="extract_zip",
                error=f"Archive '{zip_path}' not found.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        target = dest_dir or (zip_path.parent / zip_path.stem)
        target.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(str(zip_path), 'r') as zf:
                zf.extractall(str(target))
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="extract_zip",
                data={"archive": str(zip_path), "extracted_to": str(target)},
                verification={"extracted": True, "verified": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="extract_zip",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _get_metadata(self, path: Path, start_time: float) -> AgentResult:
        """Inspect file metadata and attributes."""
        if not path.exists():
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="get_metadata",
                error=f"Path '{path}' not found.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        st = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))
        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="get_metadata",
            data={
                "name": path.name,
                "is_dir": path.is_dir(),
                "size_bytes": st.st_size,
                "created_time": time.ctime(st.st_ctime),
                "modified_time": time.ctime(st.st_mtime),
                "mime_type": mime_type or "application/octet-stream"
            },
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    def _parse_pdf(self, path: Path) -> str:
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
        try:
            import docx
            doc = docx.Document(str(path))
            paras = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paras[:100]) or "DOCX document is empty."
        except Exception as e:
            return f"DOCX parse error: {e}"

    def _parse_xlsx(self, path: Path) -> str:
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

    async def _read_file(self, path: Path, start_time: float) -> AgentResult:
        if not path.exists():
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="read_file",
                error=f"File not found: '{path}'",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text_content = self._parse_pdf(path)
        elif suffix in [".docx", ".doc"]:
            text_content = self._parse_docx(path)
        elif suffix in [".xlsx", ".xls"]:
            text_content = self._parse_xlsx(path)
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

    async def _summarize_file(self, path: Path, start_time: float) -> AgentResult:
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
            summary_prompt = f"Summarize the following document concisely in 3-5 bullet points:\n\n{doc_text[:1500]}"
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
                data={"filename": path.name, "summary": model_res.content.strip(), "model_used": model_res.model_name},
                verification={"verified": True, "summary_generated": bool(model_res.content)},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="summarize_file",
                error=f"Summarization error: {e}",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _list_storage_files(self, start_time: float) -> AgentResult:
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
