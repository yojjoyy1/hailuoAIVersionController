from __future__ import annotations

from pathlib import Path

DEFAULT_IGNORE = [
    ".avc/",
    ".git/",
    ".svn/",
    ".hg/",
    ".DS_Store",
    "Thumbs.db",
    "__pycache__/",
    ".venv/",
    "venv/",
    "node_modules/",
    ".cursor/",
    ".claude/",
    ".agents/",
    ".codex/",
    "desktop.ini",
    ".idea/",
    ".vscode/",
    "*.pyc",
    "*.pyo",
    ".env",
    ".env.*",
]

MAX_FILE_BYTES = 20 * 1024 * 1024


def load_ignore_patterns(root: Path) -> list[str]:
    patterns = list(DEFAULT_IGNORE)
    extra = root / ".avcignore"
    if extra.is_file():
        for line in extra.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _match_segment(name: str, pat: str) -> bool:
    if pat.endswith("/"):
        pat = pat[:-1]
    if "*" in pat:
        from fnmatch import fnmatch

        return fnmatch(name, pat)
    return name == pat


def is_ignored(root: Path, path: Path, patterns: list[str]) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    parts = rel.parts
    if not parts:
        return True
    rel_posix = rel.as_posix()
    from fnmatch import fnmatch

    for pat in patterns:
        clean = pat.rstrip("/")
        dir_only = pat.endswith("/")
        if "/" in clean.strip("/"):
            if fnmatch(rel_posix, clean) or fnmatch(rel_posix, clean.lstrip("./")):
                if dir_only and path.is_file():
                    continue
                return True
            continue
        for i, part in enumerate(parts):
            if _match_segment(part, clean):
                if dir_only and i == len(parts) - 1 and path.is_file():
                    continue
                return True
    return False
