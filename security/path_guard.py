"""Constrained filesystem path resolution for MATRIX tools and API routes.

Every file operation that accepts user-supplied relative paths must go through
:func:`resolve_within` so that ``..`` segments, absolute paths, and Windows
drive-relative paths cannot escape the approved storage root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


class PathTraversalError(ValueError):
    """Raised when a requested path escapes its approved root directory."""


def resolve_within(root: PathLike, *parts: str) -> Path:
    """Resolve ``parts`` against ``root`` and guarantee the result stays inside it.

    Raises:
        PathTraversalError: if the resolved target is outside ``root``.
    """
    root_resolved = Path(root).resolve()
    candidate = Path(*parts)
    if candidate.is_absolute() or candidate.drive:
        # Absolute or drive-qualified inputs are never allowed to replace the root.
        raise PathTraversalError(f"Absolute paths are not permitted: {candidate}")
    target = (root_resolved / candidate).resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise PathTraversalError(f"Path escapes the approved storage root: {candidate}")
    return target


def is_within(root: PathLike, target: PathLike) -> bool:
    """Return True when ``target`` is ``root`` or lives underneath it."""
    root_resolved = Path(root).resolve()
    target_resolved = Path(target).resolve()
    return target_resolved == root_resolved or root_resolved in target_resolved.parents


SAFE_NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"


def is_safe_name(name: str) -> bool:
    """Validate a single path segment (filename, folder, project name)."""
    import re

    return bool(re.match(SAFE_NAME_PATTERN, name))
