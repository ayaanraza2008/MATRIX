"""MATRIX File Management API Route.
Explores, reads, and creates files strictly inside the approved MATRIX storage root.

All user-supplied paths are resolved through :func:`security.path_guard.resolve_within`,
which rejects ``..`` traversal, absolute paths, and drive-qualified paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from config.settings import settings
from security.authentication.api_access import require_authenticated_client
from security.path_guard import PathTraversalError, is_safe_name, resolve_within

router = APIRouter(
    prefix="/files",
    tags=["File Explorer"],
    dependencies=[Depends(require_authenticated_client)],
)


class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    size_bytes: int
    modified_at: float


class FileReadRequest(BaseModel):
    relative_path: str = Field(..., max_length=512)


class FileCreateRequest(BaseModel):
    filename: str = Field(..., max_length=128)
    content: str
    folder: Optional[str] = Field(default="documents", max_length=128)


@router.get("", response_model=List[FileItem])
async def list_files() -> List[FileItem]:
    """List files in the MATRIX storage root."""
    root = Path(settings.data_dir)
    root.mkdir(parents=True, exist_ok=True)

    items: List[FileItem] = []
    for p in root.iterdir():
        try:
            stat = p.stat()
        except OSError:
            continue
        items.append(
            FileItem(
                name=p.name,
                path=str(p),
                is_dir=p.is_dir(),
                size_bytes=stat.st_size if p.is_file() else 0,
                modified_at=stat.st_mtime,
            )
        )
    return sorted(items, key=lambda x: (not x.is_dir, x.name))


@router.post("/read")
async def read_file_content(payload: FileReadRequest) -> Dict[str, Any]:
    """Safely read content from a text/csv/json file inside the storage root."""
    try:
        target = resolve_within(settings.data_dir, payload.relative_path)
    except PathTraversalError:
        raise HTTPException(
            status_code=403, detail="Access denied: outside allowed data partition."
        )

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")
    return {
        "filename": target.name,
        "content": content[:8000],
        "size_bytes": target.stat().st_size,
        "truncated": len(content) > 8000,
    }


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_document(payload: FileCreateRequest) -> Dict[str, Any]:
    """Create a new text file inside the storage root."""
    folder = payload.folder or "documents"
    if not is_safe_name(folder):
        raise HTTPException(status_code=400, detail="Invalid folder name.")
    if not is_safe_name(payload.filename):
        raise HTTPException(status_code=400, detail="Invalid file name.")

    try:
        folder_path = resolve_within(settings.data_dir, folder)
        target = resolve_within(folder_path, payload.filename)
    except PathTraversalError:
        raise HTTPException(status_code=403, detail="Access denied: outside allowed data partition.")

    folder_path.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")

    return {
        "status": "CREATED",
        "path": str(target),
        "size_bytes": target.stat().st_size,
    }
