from __future__ import annotations

import difflib
from pathlib import Path

from avc.db import connect, db_path, init_db, is_initialized, utcnow
from avc.platform_util import AGENT_LABELS
from avc.scan import scan_tree, working_fingerprint
from avc.skillpack import (
    install_project_skill,
    install_user_skill,
    normalize_agent,
    sync_project_memory,
    write_bootstrap,
)

TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".json",
    ".yml",
    ".yaml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".py",
    ".rb",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".xml",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".zsh",
    ".bash",
    ".sql",
    ".svg",
    ".rtf",
    ".tex",
    ".rst",
    ".vue",
    ".scss",
    ".less",
}


class AvcError(Exception):
    pass


def require_project(root: Path) -> Path:
    root = root.resolve()
    if not is_initialized(root):
        raise AvcError(f"這個資料夾還沒開始使用時光本：{root}")
    return root


def get_state(root: Path) -> dict:
    conn = connect(root)
    try:
        row = conn.execute(
            "SELECT project_name, current_record_id, active_session_id, agent_kind FROM state WHERE id = 1"
        ).fetchone()
        if not row:
            raise AvcError("資料庫狀態不完整，請重新 init")
        return dict(row)
    finally:
        conn.close()


def snapshot_tree(root: Path, conn, record_id: int, files: list[dict]) -> None:
    for item in files:
        if item.get("skipped"):
            continue
        path = root / item["path"]
        content = path.read_bytes()
        conn.execute(
            "INSERT OR IGNORE INTO blobs (hash, size, content) VALUES (?, ?, ?)",
            (item["hash"], item["size"], content),
        )
        conn.execute(
            "INSERT INTO record_files (record_id, path, hash, size) VALUES (?, ?, ?, ?)",
            (record_id, item["path"], item["hash"], item["size"]),
        )


def create_record(
    root: Path,
    label: str,
    note: str = "",
    kind: str = "user",
    session_id: int | None = None,
    set_current: bool = True,
) -> dict:
    root = require_project(root)
    files = scan_tree(root)
    skipped = [f for f in files if f.get("skipped")]
    conn = connect(root)
    try:
        cur = conn.execute(
            "INSERT INTO records (label, note, kind, session_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (label, note, kind, session_id, utcnow()),
        )
        record_id = cur.lastrowid
        snapshot_tree(root, conn, record_id, files)
        if set_current:
            conn.execute(
                "UPDATE state SET current_record_id = ? WHERE id = 1", (record_id,)
            )
        conn.commit()
        return {
            "id": record_id,
            "label": label,
            "note": note,
            "kind": kind,
            "session_id": session_id,
            "file_count": sum(1 for f in files if not f.get("skipped")),
            "skipped": skipped,
        }
    finally:
        conn.close()


def init_project(root: Path, name: str, agent: str = "cursor") -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise AvcError(f"找不到資料夾：{root}")
    try:
        agent = normalize_agent(agent)
    except ValueError as e:
        raise AvcError(str(e)) from e
    existed = is_initialized(root)
    init_db(root, name, agent)
    write_bootstrap(root)
    skills = install_project_skill(root, agent)
    install_user_skill(agent)
    sync_project_memory(root, agent)
    if not existed:
        rec = create_record(root, "起始狀態", "開始使用時光本時的資料夾內容", kind="baseline")
        return {
            "created": True,
            "root": str(root),
            "name": name,
            "agent": agent,
            "skills": skills,
            "first_record": rec,
        }
    return {"created": False, "root": str(root), "name": name, "agent": agent, "skills": skills}


def clear_database(root: Path) -> dict:
    """Wipe tags, talks, and snapshots. Folder files on disk stay. Starts a fresh 起始狀態."""
    root = require_project(root)
    state = get_state(root)
    name = state["project_name"]
    agent = state["agent_kind"] or "cursor"
    path = db_path(root)
    for extra in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        extra.unlink(missing_ok=True)
    result = init_project(root, name, agent)
    return {
        "ok": True,
        "name": name,
        "first_record": result.get("first_record"),
    }


def list_records(root: Path, include_hidden: bool = False) -> list[dict]:
    root = require_project(root)
    conn = connect(root)
    try:
        sql = """
            SELECT r.id, r.label, r.note, r.kind, r.session_id, r.created_at,
                   (SELECT COUNT(*) FROM record_files rf WHERE rf.record_id = r.id) AS file_count
            FROM records r
        """
        if not include_hidden:
            sql += " WHERE r.kind = 'user' OR r.kind = 'baseline'"
        sql += " ORDER BY r.id DESC"
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def get_record(root: Path, record_id: int) -> dict:
    root = require_project(root)
    conn = connect(root)
    try:
        row = conn.execute(
            """
            SELECT r.id, r.label, r.note, r.kind, r.session_id, r.created_at,
                   (SELECT COUNT(*) FROM record_files rf WHERE rf.record_id = r.id) AS file_count
            FROM records r WHERE r.id = ?
            """,
            (record_id,),
        ).fetchone()
        if not row:
            raise AvcError(f"找不到紀錄 #{record_id}")
        rec = dict(row)
        rec["files"] = [
            dict(f)
            for f in conn.execute(
                "SELECT path, hash, size FROM record_files WHERE record_id = ? ORDER BY path",
                (record_id,),
            ).fetchall()
        ]
        return rec
    finally:
        conn.close()


def record_file_map(conn, record_id: int) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT path, hash, size FROM record_files WHERE record_id = ?",
        (record_id,),
    ).fetchall()
    return {r["path"]: dict(r) for r in rows}


def blob_bytes(conn, file_hash: str) -> bytes:
    row = conn.execute("SELECT content FROM blobs WHERE hash = ?", (file_hash,)).fetchone()
    if not row:
        raise AvcError("找不到檔案內容")
    return row["content"]


def working_map(root: Path) -> dict[str, dict]:
    return {
        f["path"]: f
        for f in scan_tree(root)
        if not f.get("skipped")
    }


def diff_maps(old: dict[str, dict], new: dict[str, dict]) -> dict:
    old_paths = set(old)
    new_paths = set(new)
    added = sorted(new_paths - old_paths)
    removed = sorted(old_paths - new_paths)
    modified = sorted(
        p for p in (old_paths & new_paths) if old[p]["hash"] != new[p]["hash"]
    )
    unchanged = len(old_paths & new_paths) - len(modified)
    return {
        "added": [{"path": p, "size": new[p]["size"]} for p in added],
        "removed": [{"path": p, "size": old[p]["size"]} for p in removed],
        "modified": [
            {"path": p, "old_size": old[p]["size"], "new_size": new[p]["size"]}
            for p in modified
        ],
        "unchanged": unchanged,
        "change_count": len(added) + len(removed) + len(modified),
    }


def status(root: Path) -> dict:
    root = require_project(root)
    state = get_state(root)
    conn = connect(root)
    try:
        current_id = state["current_record_id"]
        if not current_id:
            old = {}
            current_label = "尚無紀錄"
        else:
            old = record_file_map(conn, current_id)
            rec = conn.execute(
                "SELECT label FROM records WHERE id = ?", (current_id,)
            ).fetchone()
            current_label = rec["label"] if rec else f"#{current_id}"
        new = working_map(root)
        d = diff_maps(old, new)
        d["current_record_id"] = current_id
        d["current_label"] = current_label
        d["active_session_id"] = state["active_session_id"]
        d["project_name"] = state["project_name"]
        return d
    finally:
        conn.close()


def looks_text(path: str, raw: bytes) -> bool:
    suffix = Path(path).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return True
    if b"\x00" in raw[:8000]:
        return False
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def unified_diff(path: str, old_bytes: bytes | None, new_bytes: bytes | None) -> dict:
    if old_bytes is None:
        old_text = ""
        new_text = new_bytes.decode("utf-8", errors="replace") if new_bytes else ""
        if new_bytes is not None and not looks_text(path, new_bytes):
            return {"path": path, "binary": True, "kind": "added", "diff": ""}
        lines = list(
            difflib.unified_diff(
                [], new_text.splitlines(), fromfile="（沒有這個檔）", tofile=path, lineterm=""
            )
        )
        return {"path": path, "binary": False, "kind": "added", "diff": "\n".join(lines)}
    if new_bytes is None:
        if not looks_text(path, old_bytes):
            return {"path": path, "binary": True, "kind": "removed", "diff": ""}
        old_text = old_bytes.decode("utf-8", errors="replace")
        lines = list(
            difflib.unified_diff(
                old_text.splitlines(), [], fromfile=path, tofile="（已刪除）", lineterm=""
            )
        )
        return {"path": path, "binary": False, "kind": "removed", "diff": "\n".join(lines)}
    if not looks_text(path, old_bytes) or not looks_text(path, new_bytes):
        return {"path": path, "binary": True, "kind": "modified", "diff": ""}
    old_text = old_bytes.decode("utf-8", errors="replace")
    new_text = new_bytes.decode("utf-8", errors="replace")
    lines = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=f"較早 · {path}",
            tofile=f"較新 · {path}",
            lineterm="",
        )
    )
    return {"path": path, "binary": False, "kind": "modified", "diff": "\n".join(lines)}


def compare(root: Path, from_id: int | str, to_id: int | str) -> dict:
    """from_id / to_id: record id or 'working'."""
    root = require_project(root)
    conn = connect(root)
    try:
        def load(ref: int | str) -> tuple[str, dict[str, dict]]:
            if str(ref) == "working":
                return "現在資料夾", working_map(root)
            rid = int(ref)
            rec = conn.execute("SELECT label FROM records WHERE id = ?", (rid,)).fetchone()
            if not rec:
                raise AvcError(f"找不到紀錄 #{rid}")
            return rec["label"], record_file_map(conn, rid)

        from_label, old = load(from_id)
        to_label, new = load(to_id)
        summary = diff_maps(old, new)
        details = []
        for item in summary["added"]:
            p = item["path"]
            raw = (root / p).read_bytes() if str(to_id) == "working" else blob_bytes(conn, new[p]["hash"])
            details.append(unified_diff(p, None, raw))
        for item in summary["removed"]:
            p = item["path"]
            raw = blob_bytes(conn, old[p]["hash"]) if str(from_id) != "working" else (root / p).read_bytes()
            if str(from_id) == "working":
                raw = (root / p).read_bytes()
            else:
                raw = blob_bytes(conn, old[p]["hash"])
            details.append(unified_diff(p, raw, None))
        for item in summary["modified"]:
            p = item["path"]
            if str(from_id) == "working":
                old_raw = (root / p).read_bytes()
            else:
                old_raw = blob_bytes(conn, old[p]["hash"])
            if str(to_id) == "working":
                new_raw = (root / p).read_bytes()
            else:
                new_raw = blob_bytes(conn, new[p]["hash"])
            details.append(unified_diff(p, old_raw, new_raw))
        return {
            "from_id": from_id,
            "to_id": to_id,
            "from_label": from_label,
            "to_label": to_label,
            "summary": summary,
            "files": details,
        }
    finally:
        conn.close()


def file_at_record(root: Path, record_id: int, relpath: str) -> dict:
    root = require_project(root)
    conn = connect(root)
    try:
        row = conn.execute(
            "SELECT hash, size FROM record_files WHERE record_id = ? AND path = ?",
            (record_id, relpath),
        ).fetchone()
        if not row:
            raise AvcError("這筆紀錄裡沒有這個檔案")
        raw = blob_bytes(conn, row["hash"])
        text = None
        if looks_text(relpath, raw):
            text = raw.decode("utf-8", errors="replace")
        rec = conn.execute("SELECT label FROM records WHERE id = ?", (record_id,)).fetchone()
        return {
            "path": relpath,
            "size": row["size"],
            "label": rec["label"] if rec else "",
            "text": text,
            "binary": text is None,
        }
    finally:
        conn.close()


def restore(root: Path, record_id: int, force: bool = False) -> dict:
    root = require_project(root)
    st = status(root)
    if st["change_count"] and not force:
        raise AvcError("資料夾還有未紀錄的改動。請先紀錄，或在網頁確認放棄後再切換。")
    conn = connect(root)
    try:
        rec = conn.execute("SELECT id, label FROM records WHERE id = ?", (record_id,)).fetchone()
        if not rec:
            raise AvcError(f"找不到紀錄 #{record_id}")
        wanted = record_file_map(conn, record_id)
        current = working_map(root)
        # write / overwrite
        for path, meta in wanted.items():
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                dest.write_bytes(blob_bytes(conn, meta["hash"]))
            except PermissionError as e:
                raise AvcError(
                    f"無法寫入 {path}。在 Windows 上請先關閉正在打開這個檔案的程式再切換。"
                ) from e
        # delete extras
        for path in current:
            if path not in wanted:
                (root / path).unlink(missing_ok=True)
        conn.execute("UPDATE state SET current_record_id = ? WHERE id = 1", (record_id,))
        conn.commit()
        return {"id": record_id, "label": rec["label"], "file_count": len(wanted)}
    finally:
        conn.close()


def start_session(root: Path, title: str, source: str = "", agent: str | None = None) -> dict:
    root = require_project(root)
    conn = connect(root)
    try:
        state = conn.execute(
            "SELECT active_session_id, agent_kind FROM state WHERE id = 1"
        ).fetchone()
        if state and state["active_session_id"]:
            raise AvcError(f"已有進行中的對話 #{state['active_session_id']}，請先結束或繼續使用。")
        try:
            agent_kind = normalize_agent(agent or (state["agent_kind"] if state else "cursor"))
        except ValueError as e:
            raise AvcError(str(e)) from e
        files = scan_tree(root)
        cur = conn.execute(
            "INSERT INTO records (label, note, kind, session_id, created_at) VALUES (?, ?, 'session-start', NULL, ?)",
            (f"對話開始：{title}", "這次對話開始前的資料夾狀態", utcnow()),
        )
        baseline_id = cur.lastrowid
        snapshot_tree(root, conn, baseline_id, files)
        scur = conn.execute(
            "INSERT INTO sessions (title, source, agent, started_at, ended_at, baseline_record_id) VALUES (?, ?, ?, ?, NULL, ?)",
            (title, source, agent_kind, utcnow(), baseline_id),
        )
        session_id = scur.lastrowid
        conn.execute(
            "UPDATE records SET session_id = ? WHERE id = ?", (session_id, baseline_id)
        )
        conn.execute("UPDATE state SET active_session_id = ? WHERE id = 1", (session_id,))
        conn.commit()
        return {
            "id": session_id,
            "title": title,
            "source": source,
            "agent": agent_kind,
            "baseline_record_id": baseline_id,
        }
    finally:
        conn.close()


def end_session(root: Path, session_id: int | None = None) -> dict:
    root = require_project(root)
    conn = connect(root)
    try:
        state = conn.execute("SELECT active_session_id FROM state WHERE id = 1").fetchone()
        sid = session_id or (state["active_session_id"] if state else None)
        if not sid:
            raise AvcError("目前沒有進行中的對話")
        row = conn.execute("SELECT id, title FROM sessions WHERE id = ?", (sid,)).fetchone()
        if not row:
            raise AvcError(f"找不到對話 #{sid}")
        conn.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (utcnow(), sid))
        if state and state["active_session_id"] == sid:
            conn.execute("UPDATE state SET active_session_id = NULL WHERE id = 1")
        conn.commit()
        return {"id": sid, "title": row["title"]}
    finally:
        conn.close()


def add_message(root: Path, role: str, content: str, session_id: int | None = None) -> dict:
    root = require_project(root)
    if role not in {"user", "assistant", "system"}:
        raise AvcError("role 只能是 user、assistant 或 system")
    if not content.strip():
        raise AvcError("對話內容不能是空的")
    conn = connect(root)
    try:
        state = conn.execute("SELECT active_session_id FROM state WHERE id = 1").fetchone()
        sid = session_id or (state["active_session_id"] if state else None)
        if not sid:
            raise AvcError("沒有進行中的對話，請先 session start")
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (sid, role, content, utcnow()),
        )
        conn.commit()
        return {"id": cur.lastrowid, "session_id": sid, "role": role}
    finally:
        conn.close()


def list_sessions(root: Path) -> list[dict]:
    root = require_project(root)
    conn = connect(root)
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.source, s.agent, s.started_at, s.ended_at, s.baseline_record_id,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count
            FROM sessions s
            ORDER BY s.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session(root: Path, session_id: int) -> dict:
    root = require_project(root)
    conn = connect(root)
    try:
        row = conn.execute(
            """
            SELECT s.id, s.title, s.source, s.agent, s.started_at, s.ended_at, s.baseline_record_id
            FROM sessions s WHERE s.id = ?
            """,
            (session_id,),
        ).fetchone()
        if not row:
            raise AvcError(f"找不到對話 #{session_id}")
        data = dict(row)
        data["messages"] = [
            dict(m)
            for m in conn.execute(
                "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        ]
        data["records"] = [
            dict(r)
            for r in conn.execute(
                "SELECT id, label, note, kind, created_at FROM records WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        ]
        # For an in-progress conversation, attach what has changed since it began
        # so the "對話" view can show the AI's edits directly (baseline → now).
        data["change_summary"] = None
        if data["ended_at"] is None and data["baseline_record_id"]:
            try:
                old = record_file_map(conn, data["baseline_record_id"])
                new = working_map(root)
                data["change_summary"] = diff_maps(old, new)
            except Exception:
                data["change_summary"] = None
        return data
    finally:
        conn.close()


def session_changes(root: Path, session_id: int) -> dict:
    sess = get_session(root, session_id)
    baseline = sess["baseline_record_id"]
    if not baseline:
        raise AvcError("這次對話沒有開始時的快照")
    return compare(root, baseline, "working")


def project_info(root: Path) -> dict:
    root = require_project(root)
    state = get_state(root)
    st = status(root)
    return {
        "root": str(root),
        "name": state["project_name"],
        "current_record_id": state["current_record_id"],
        "active_session_id": state["active_session_id"],
        "agent": state["agent_kind"],
        "agent_label": AGENT_LABELS.get(state["agent_kind"] or "cursor", "Cursor"),
        "status": st,
        "record_count": len(list_records(root, include_hidden=True)),
        "session_count": len(list_sessions(root)),
    }


def set_agent(root: Path, agent: str) -> dict:
    root = require_project(root)
    try:
        agent = normalize_agent(agent)
    except ValueError as e:
        raise AvcError(str(e)) from e
    conn = connect(root)
    try:
        conn.execute("UPDATE state SET agent_kind = ? WHERE id = 1", (agent,))
        conn.commit()
    finally:
        conn.close()
    write_bootstrap(root)
    skills = install_project_skill(root, agent)
    user_skills = install_user_skill(agent)
    memory = sync_project_memory(root, agent)
    return {
        "agent": agent,
        "agent_label": AGENT_LABELS[agent],
        "skills": skills,
        "user_skills": user_skills,
        "memory": memory,
    }


def save_user_record(root: Path, label: str, note: str = "") -> dict:
    root = require_project(root)
    state = get_state(root)
    rec = create_record(
        root,
        label=label,
        note=note,
        kind="user",
        session_id=state["active_session_id"],
        set_current=True,
    )
    return rec


def update_record(root: Path, record_id: int, label: str | None = None, note: str | None = None) -> dict:
    root = require_project(root)
    if label is not None:
        label = label.strip()
        if not label:
            raise AvcError("標籤名稱不能空白")
    conn = connect(root)
    try:
        row = conn.execute(
            "SELECT id, label, note, kind, session_id, created_at FROM records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            raise AvcError(f"找不到紀錄 #{record_id}")
        new_label = label if label is not None else row["label"]
        new_note = note if note is not None else row["note"]
        conn.execute(
            "UPDATE records SET label = ?, note = ? WHERE id = ?",
            (new_label, new_note, record_id),
        )
        conn.commit()
        rec = dict(row)
        rec["label"] = new_label
        rec["note"] = new_note
        return rec
    finally:
        conn.close()


def project_pulse(root: Path) -> dict:
    """Cheap fingerprint so the webpage can notice new talks / labels without a full reload."""
    root = require_project(root)
    state = get_state(root)
    conn = connect(root)
    try:
        row = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM records) AS records,
              (SELECT COALESCE(MAX(id), 0) FROM records) AS max_record,
              (SELECT COALESCE(GROUP_CONCAT(id || '=' || replace(label, '|', '/'), '|'), '') FROM (SELECT id, label FROM records ORDER BY id)) AS labels,
              (SELECT COUNT(*) FROM sessions) AS sessions,
              (SELECT COALESCE(MAX(id), 0) FROM sessions) AS max_session,
              (SELECT COUNT(*) FROM messages) AS messages,
              (SELECT COALESCE(MAX(id), 0) FROM messages) AS max_message
            """
        ).fetchone()
        data = dict(row)
    finally:
        conn.close()
    data["active_session_id"] = state["active_session_id"]
    data["current_record_id"] = state["current_record_id"]
    data["db_stamp"] = "|".join(
        [
            str(data["records"]),
            str(data["max_record"]),
            str(data["labels"]),
            str(data["sessions"]),
            str(data["max_session"]),
            str(data["messages"]),
            str(data["max_message"]),
            str(data["active_session_id"] or 0),
            str(data["current_record_id"] or 0),
        ]
    )
    data["working"] = working_fingerprint(root)
    data["stamp"] = data["db_stamp"] + "||" + data["working"]
    return data


# ---------------------------------------------------------------------------
# Claude Code hook 專用：讓「改檔就自動記錄」不再靠模型自己記得。
# 由 .claude/settings.json 的 SessionStart / Stop / SessionEnd 呼叫。
# 原則：無論如何都不要讓 Claude Code 中斷，任何錯誤都安靜吞掉、回傳 ok。
# ---------------------------------------------------------------------------

def _autosave(root: Path) -> dict:
    st = status(root)
    if not (st.get("added") or st.get("removed") or st.get("modified")):
        return {"ok": True, "saved": False}
    label = "自動記錄 " + utcnow()[:16].replace("T", " ")
    rec = save_user_record(root, label=label, note="Claude Code 自動記錄")
    return {"ok": True, "saved": True, "record_id": rec.get("id")}


def autohook(root: Path, event: str) -> dict:
    try:
        if not is_initialized(root):
            return {"ok": True, "skipped": "not-a-project"}
    except Exception:
        return {"ok": True, "skipped": "not-a-project"}
    try:
        if event == "session-begin":
            st = status(root)
            if not st.get("active_session_id"):
                title = "Claude Code " + utcnow()[:16].replace("T", " ")
                start_session(root, title=title, source="Claude Code", agent="claude")
            return {"ok": True}
        if event == "autosave":
            return _autosave(root)
        if event == "session-finish":
            _autosave(root)
            st = status(root)
            if st.get("active_session_id"):
                end_session(root)
            return {"ok": True}
        return {"ok": True, "skipped": "unknown-event"}
    except Exception as e:
        return {"ok": True, "error": str(e)}
