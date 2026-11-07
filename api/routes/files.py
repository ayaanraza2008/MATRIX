"""MATRIX File Management API Route.
Explores, reads, and creates files within the approved D:\\matrix_data partition.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from config.settings import settings

router = APIRouter(prefix="/files", tags=["File Explorer"])


class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    size_bytes: int
    modified_at: float


class FileReadRequest(BaseModel):
    relative_path: str


class FileCreateRequest(BaseModel):
    filename: str
    content: str
    folder: Optional[str] = "documents"


@router.get("", response_model=List[FileItem])
async def list_files():
    """List files in D:\\matrix_data storage root."""
    root = settings.data_dir
    root.mkdir(parents=True, exist_ok=True)

    items = []
    for p in root.iterdir():
        items.append(FileItem(
            name=p.name,
            path=str(p),
            is_dir=p.is_dir(),
            size_bytes=p.stat().st_size if p.is_file() else 0,
            modified_at=p.stat().st_mtime
        ))
    return sorted(items, key=lambda x: (not x.is_dir, x.name))


@router.post("/read")
async def read_file_content(payload: FileReadRequest):
    """Safely read content from a text/csv/json file in D:\\matrix_data."""
    target = (settings.data_dir / payload.relative_path).resolve()

    # Path traversal protection
    try:
        target.relative_to(settings.data_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: outside allowed data partition.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return {
            "filename": target.name,
            "content": content[:8000],
            "size_bytes": target.stat().st_size,
            "truncated": len(content) > 8000
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_document(payload: FileCreateRequest):
    """Create a new file in D:\\matrix_data."""
    folder = settings.data_dir / payload.folder
    folder.mkdir(parents=True, exist_ok=True)

    target = folder / payload.filename
    target.write_text(payload.content, encoding="utf-8")

    return {
        "status": "CREATED",
        "path": str(target),
        "size_bytes": target.stat().st_size
    }
