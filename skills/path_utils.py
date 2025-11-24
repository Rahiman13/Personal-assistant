"""Utility helpers for routing all assistant-generated files into a single sandbox."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_BASE_DIR: Optional[Path] = None


def _compute_base_dir() -> Path:
    """Determine (and create) the base directory for assistant files."""
    target = os.getenv("ASSISTANT_FILE_DIR") or os.getenv("ASSISTANT_OUTPUT_DIR")
    if target:
        base = Path(target)
    else:
        # Default sandbox inside the repo: ./testing_files
        base = Path.cwd() / "testing_files"

    if not base.is_absolute():
        base = (Path.cwd() / base).resolve()

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_base_output_dir() -> Path:
    """Return the absolute directory where assistant files should live."""
    global _BASE_DIR
    if _BASE_DIR is None:
        _BASE_DIR = _compute_base_dir()
    return _BASE_DIR


def _sanitize_relative_path(name: str) -> Path:
    """Strip unsafe segments and ensure we only use filenames/subpaths."""
    name = (name or "").strip()
    candidate = Path(name) if name else Path("output.txt")

    # Drop any parent references or root indicators
    safe_parts = [part for part in candidate.parts if part not in ("..", "", ".")]
    if not safe_parts:
        safe_parts = ["output.txt"]
    candidate = Path(*safe_parts)

    if candidate.is_absolute():
        candidate = Path(candidate.name)

    return candidate


def resolve_output_path(filename: str) -> Path:
    """Return an absolute path inside the sandbox for creating/updating a file."""
    relative = _sanitize_relative_path(filename)
    path = (get_base_output_dir() / relative).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_access_path(filename: str) -> Path:
    """Return the sandboxed path for an existing file (even if it doesn't exist yet)."""
    # Allow absolute paths explicitly provided by the user (for reading existing files)
    candidate = Path(filename)
    if candidate.is_absolute():
        return candidate

    relative = _sanitize_relative_path(filename)
    return (get_base_output_dir() / relative).resolve()


def resolve_directory_path(dirname: str) -> Path:
    """Return (and create) a directory path under the sandbox."""
    relative = _sanitize_relative_path(dirname)
    path = (get_base_output_dir() / relative).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path

