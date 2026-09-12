from __future__ import annotations

import json
import re
from pathlib import Path

from avc.registry import REGISTRY

DEFAULT_THEME = {
    "bg": "#f3ead8",
    "btn": "#b23a2f",
    "dialog": "#fff8ec",
    "text": "#2a2118",
}

THEME_KEYS = ("bg", "btn", "dialog", "text")
_HEX = re.compile(r"^#?([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


def theme_path() -> Path:
    return REGISTRY.parent / "theme.json"


def normalize_hex(value: str) -> str:
    raw = (value or "").strip()
    m = _HEX.match(raw)
    if not m:
        raise ValueError("請用色碼，例如 #b23a2f")
    hexpart = m.group(1)
    if len(hexpart) == 3:
        hexpart = "".join(ch * 2 for ch in hexpart)
    return "#" + hexpart.lower()


def sanitize_theme(data) -> dict:
    if not isinstance(data, dict):
        return dict(DEFAULT_THEME)
    out = dict(DEFAULT_THEME)
    for key in THEME_KEYS:
        if key not in data:
            continue
        try:
            out[key] = normalize_hex(str(data[key]))
        except ValueError:
            continue
    return out


def load_theme() -> dict:
    path = theme_path()
    if not path.is_file():
        return dict(DEFAULT_THEME)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_THEME)
    return sanitize_theme(raw)


def save_theme(colors: dict) -> dict:
    if not isinstance(colors, dict):
        raise ValueError("缺少顏色")
    merged = load_theme()
    for key in THEME_KEYS:
        if key in colors:
            merged[key] = normalize_hex(str(colors[key]))
    path = theme_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return merged


def reset_theme() -> dict:
    path = theme_path()
    if path.is_file():
        path.unlink()
    return dict(DEFAULT_THEME)
