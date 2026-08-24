"""Resolve data roots for the app (local + Docker).

App code lives under ``src/`` (WORKDIR=/app in Docker). Corpus and
ops data are under ``data/`` at the repo root (mounted at ``/app/data``).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def backend_root() -> Path:
    """Repo / container root (parent of ``src/``)."""
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Monorepo root when present; otherwise same as backend_root."""
    root = backend_root()
    if (root / "data").is_dir() or (root / "docs").is_dir():
        return root
    return root


def _first_existing(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.is_dir():
            return path
    return None


@lru_cache(maxsize=1)
def data_root() -> Path:
    """Writable/runtime data directory (uploads, chroma, subject_data, mock_data)."""
    found = _first_existing(
        backend_root() / "data",
        repo_root() / "data",
        Path("/app/data"),
    )
    return found or (backend_root() / "data")


@lru_cache(maxsize=1)
def mock_documents_root() -> Path:
    """Markdown corpus used by StudentMockDataService (haianh seed)."""
    found = _first_existing(
        data_root() / "mock_data" / "documents",
        backend_root() / "mock_data" / "documents",
        repo_root() / "mock_data" / "documents",
    )
    return found or (data_root() / "mock_data" / "documents")


@lru_cache(maxsize=1)
def rag_cache_dir() -> Path:
    path = data_root() / "rag_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def subject_data_dir() -> Path:
    return data_root() / "subject_data"


@lru_cache(maxsize=1)
def uploads_dir() -> Path:
    path = data_root() / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path
