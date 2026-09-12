from __future__ import annotations

import hashlib
from pathlib import Path

from avc.ignore import MAX_FILE_BYTES, is_ignored, load_ignore_patterns


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def scan_tree(root: Path) -> list[dict]:
    """Return list of {path, hash, size, skipped} for files under root."""
    patterns = load_ignore_patterns(root)
    files: list[dict] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        if is_ignored(root, p, patterns):
            continue
        rel = p.relative_to(root).as_posix()
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            files.append(
                {
                    "path": rel,
                    "hash": None,
                    "size": size,
                    "skipped": True,
                    "reason": "檔案超過 20MB，未納入紀錄",
                }
            )
            continue
        files.append(
            {
                "path": rel,
                "hash": file_sha256(p),
                "size": size,
                "skipped": False,
                "reason": None,
            }
        )
    return files


def working_fingerprint(root: Path) -> str:
    """Path + mtime + size only, so the webpage can notice folder edits without hashing files."""
    patterns = load_ignore_patterns(root)
    bits: list[str] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        if is_ignored(root, p, patterns):
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        rel = p.relative_to(root).as_posix()
        bits.append(f"{rel}:{st.st_mtime_ns}:{st.st_size}")
    raw = "\n".join(bits).encode("utf-8")
    return f"{len(bits)}:{hashlib.sha256(raw).hexdigest()}"
