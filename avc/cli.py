from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from avc.db import is_initialized
from avc.registry import find_by_root, list_projects, register_project
from avc.platform_util import enable_utf8
from avc.store import (
    AvcError,
    add_message,
    clear_database,
    compare,
    end_session,
    file_at_record,
    get_record,
    get_session,
    init_project,
    list_records,
    list_sessions,
    project_info,
    restore,
    save_user_record,
    session_changes,
    set_agent,
    start_session,
    status,
    update_record,
)


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _root_from_args(args) -> Path:
    if getattr(args, "project", None):
        return Path(args.project).expanduser().resolve()
    return Path.cwd().resolve()


def cmd_init(args) -> int:
    root = _root_from_args(args)
    name = args.name or root.name
    result = init_project(root, name, args.agent)
    register_project(root, name)
    _print_json(result)
    return 0


def cmd_clear(args) -> int:
    if not args.yes:
        raise AvcError("這會刪掉所有標籤與對話。確定的話請加上 --yes")
    _print_json(clear_database(_root_from_args(args)))
    return 0


def cmd_info(args) -> int:
    _print_json(project_info(_root_from_args(args)))
    return 0


def cmd_status(args) -> int:
    _print_json(status(_root_from_args(args)))
    return 0


def cmd_save(args) -> int:
    rec = save_user_record(_root_from_args(args), args.label, args.note or "")
    _print_json(rec)
    return 0


def cmd_relabel(args) -> int:
    rec = update_record(_root_from_args(args), args.id, label=args.label, note=args.note)
    _print_json(rec)
    return 0


def cmd_list(args) -> int:
    _print_json(list_records(_root_from_args(args), include_hidden=args.all))
    return 0


def cmd_show(args) -> int:
    rec = get_record(_root_from_args(args), args.id)
    if not args.files:
        rec = {k: v for k, v in rec.items() if k != "files"}
        rec["file_count"] = rec.get("file_count")
    _print_json(rec)
    return 0


def cmd_diff(args) -> int:
    to_ref = args.to if args.to is not None else "working"
    data = compare(_root_from_args(args), args.a, to_ref)
    if args.summary:
        data = {
            "from_label": data["from_label"],
            "to_label": data["to_label"],
            "summary": data["summary"],
        }
    _print_json(data)
    return 0


def cmd_restore(args) -> int:
    result = restore(_root_from_args(args), args.id, force=args.force)
    _print_json(result)
    return 0


def cmd_file(args) -> int:
    data = file_at_record(_root_from_args(args), args.id, args.path)
    if args.meta:
        data = {k: v for k, v in data.items() if k != "text"}
    _print_json(data)
    return 0


def cmd_session_start(args) -> int:
    _print_json(
        start_session(
            _root_from_args(args),
            args.title,
            args.source or "",
            args.agent,
        )
    )
    return 0


def cmd_agent(args) -> int:
    _print_json(set_agent(_root_from_args(args), args.kind))
    return 0


def cmd_session_end(args) -> int:
    _print_json(end_session(_root_from_args(args), args.id))
    return 0


def cmd_session_list(args) -> int:
    _print_json(list_sessions(_root_from_args(args)))
    return 0


def cmd_session_show(args) -> int:
    _print_json(get_session(_root_from_args(args), args.id))
    return 0


def cmd_session_changes(args) -> int:
    data = session_changes(_root_from_args(args), args.id)
    if args.summary:
        data = {
            "from_label": data["from_label"],
            "to_label": data["to_label"],
            "summary": data["summary"],
        }
    _print_json(data)
    return 0


def cmd_note(args) -> int:
    content = args.content
    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    _print_json(add_message(_root_from_args(args), args.role, content, args.session))
    return 0


def cmd_projects(_args) -> int:
    _print_json(list_projects())
    return 0


def cmd_web(args) -> int:
    from pathlib import Path

    from avc.registry import list_projects
    from avc.skillpack import (
        install_project_skill,
        install_tool_repo_skills,
        refresh_existing_user_skills,
        write_bootstrap,
    )
    from avc.web import serve

    install_tool_repo_skills()
    # Keep already-installed user-level skills in sync with this build so the AI
    # never follows stale instructions (e.g. a missing `py` launcher on Windows).
    try:
        refresh_existing_user_skills()
    except Exception:
        pass
    for item in list_projects():
        root = Path(item["root"])
        try:
            write_bootstrap(root)
        except OSError:
            pass
        # Refresh each project's SKILL.md so the AI-side instructions match this
        # build (e.g. use .avc\avc.cmd instead of a missing `py` launcher).
        try:
            info = project_info(root)
            install_project_skill(root, info.get("agent") or "cursor")
        except Exception:
            pass
    serve(host=args.host, port=args.port, open_browser=not args.no_open)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="avc",
        description="AI 協作時光本：用資料庫記下資料夾狀態、對話與標籤，可切換與比對。",
    )
    p.add_argument("--project", "-p", help="專案資料夾路徑（預設為目前目錄）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="開始記錄這個資料夾")
    s.add_argument("--name", help="顯示名稱")
    s.add_argument("--agent", default="cursor", choices=["cursor", "claude", "codex"])
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("clear", help="清空這個資料夾的所有紀錄與對話（檔案不會刪）")
    s.add_argument("--yes", action="store_true", help="確認清空")
    s.set_defaults(func=cmd_clear)

    s = sub.add_parser("info", help="專案摘要")
    s.set_defaults(func=cmd_info)

    s = sub.add_parser("status", help="尚未紀錄的改動")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("save", help="把目前資料夾做成一筆有標籤的紀錄")
    s.add_argument("--label", "-l", required=True, help="標籤名稱，例如「藍色封面」")
    s.add_argument("--note", "-n", default="", help="說明")
    s.set_defaults(func=cmd_save)

    s = sub.add_parser("relabel", help="改一筆紀錄的標籤名稱")
    s.add_argument("id", type=int)
    s.add_argument("--label", "-l", required=True, help="新的標籤名稱")
    s.add_argument("--note", "-n", default=None, help="若有填，一併改說明")
    s.set_defaults(func=cmd_relabel)

    s = sub.add_parser("list", help="列出紀錄")
    s.add_argument("--all", action="store_true", help="包含對話開始時的隱藏快照")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="查看一筆紀錄")
    s.add_argument("id", type=int)
    s.add_argument("--files", action="store_true")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("diff", help="比對兩筆紀錄，或一筆記錄與現在資料夾")
    s.add_argument("a", help="較早的紀錄編號")
    s.add_argument("to", nargs="?", help="較新的紀錄編號，省略則比對現在資料夾")
    s.add_argument("--summary", action="store_true")
    s.set_defaults(func=cmd_diff)

    s = sub.add_parser("restore", help="把資料夾切換到某一筆紀錄")
    s.add_argument("id", type=int)
    s.add_argument("--force", action="store_true", help="放棄未紀錄改動")
    s.set_defaults(func=cmd_restore)

    s = sub.add_parser("switch", help="restore 的別名")
    s.add_argument("id", type=int)
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_restore)

    s = sub.add_parser("file", help="讀取某筆紀錄裡的一個檔案")
    s.add_argument("id", type=int)
    s.add_argument("path")
    s.add_argument("--meta", action="store_true")
    s.set_defaults(func=cmd_file)

    s = sub.add_parser("projects", help="列出已登記的專案")
    s.set_defaults(func=cmd_projects)

    s = sub.add_parser("web", help="開啟本機網頁")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--no-open", action="store_true", help="不要自動打開瀏覽器")
    s.set_defaults(func=cmd_web)

    sess = sub.add_parser("session", help="對話 session")
    ss = sess.add_subparsers(dest="session_cmd", required=True)
    s = ss.add_parser("start")
    s.add_argument("--title", required=True)
    s.add_argument("--source", default="", help="對話名稱或編號")
    s.add_argument("--agent", default=None, choices=["cursor", "claude", "codex"])
    s.set_defaults(func=cmd_session_start)
    s = ss.add_parser("end")
    s.add_argument("--id", type=int, default=None)
    s.set_defaults(func=cmd_session_end)
    s = ss.add_parser("list")
    s.set_defaults(func=cmd_session_list)
    s = ss.add_parser("show")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_session_show)
    s = ss.add_parser("changes")
    s.add_argument("id", type=int)
    s.add_argument("--summary", action="store_true")
    s.set_defaults(func=cmd_session_changes)

    s = sub.add_parser("agent", help="設定這個資料夾使用的 AI Agent")
    s.add_argument("kind", choices=["cursor", "claude", "codex"])
    s.set_defaults(func=cmd_agent)

    s = sub.add_parser("note", help="寫入一則對話內容到目前 session")
    s.add_argument("--role", required=True, choices=["user", "assistant", "system"])
    s.add_argument("--content", default="")
    s.add_argument("--file", help="從檔案讀取內容")
    s.add_argument("--session", type=int, default=None)
    s.set_defaults(func=cmd_note)

    return p


def main(argv: list[str] | None = None) -> None:
    enable_utf8()
    if argv is None:
        argv = sys.argv[1:]
    # Double-clicking the packaged .exe passes no arguments: default to the web UI.
    if not argv:
        argv = ["web"]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.cmd != "init" and args.cmd not in {"web", "projects"}:
            root = _root_from_args(args)
            if not is_initialized(root):
                raise AvcError(
                    f"這個資料夾還沒開始使用時光本，請先執行：python -m avc init -p \"{root}\""
                )
            if not find_by_root(root):
                info = project_info(root)
                register_project(root, info["name"])
        code = args.func(args)
        sys.exit(code)
    except AvcError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(130)
