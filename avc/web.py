from __future__ import annotations

import json
import mimetypes
import posixpath
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from avc.platform_util import pick_folder, platform_info
from avc.registry import get_project, list_projects, register_project, remove_project
from avc.theme import DEFAULT_THEME, load_theme, reset_theme, save_theme
from avc.store import (
    AvcError,
    add_message,
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
    project_pulse,
    save_user_record,
    session_changes,
    set_agent,
    start_session,
    status,
    update_record,
    clear_database,
)

WEB_DIR = Path(__file__).resolve().parent / "web"


def json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def send_json(handler: BaseHTTPRequestHandler, data, status_code: int = 200) -> None:
    payload = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(payload)


def send_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    data = path.read_bytes()
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def project_root(pid: int) -> Path:
    return Path(get_project(pid)["root"])


def dispatch(method: str, path: str, handler: BaseHTTPRequestHandler):
    parsed = urllib.parse.urlparse(path)
    parts = [p for p in parsed.path.split("/") if p]
    qs = urllib.parse.parse_qs(parsed.query)

    if method == "GET" and parts == ["api", "platform"]:
        return send_json(handler, platform_info())

    if method == "GET" and parts == ["api", "theme"]:
        return send_json(handler, {"colors": load_theme(), "defaults": dict(DEFAULT_THEME)})

    if method == "POST" and parts == ["api", "theme"]:
        body = json_body(handler)
        try:
            if body.get("reset"):
                colors = reset_theme()
            else:
                colors = save_theme(body.get("colors") or body)
        except ValueError as e:
            raise AvcError(str(e)) from e
        return send_json(handler, {"colors": colors, "defaults": dict(DEFAULT_THEME)})

    if method == "POST" and parts == ["api", "browse-folder"]:
        chosen = pick_folder("選擇要記錄的資料夾")
        if not chosen:
            return send_json(handler, {"cancelled": True, "path": None})
        return send_json(handler, {"cancelled": False, "path": chosen})

    if method == "GET" and parts == ["api", "projects"]:
        items = []
        for p in list_projects():
            try:
                info = project_info(Path(p["root"]))
                p["info"] = info
            except Exception as e:
                p["info"] = {"error": str(e)}
            items.append(p)
        return send_json(handler, items)

    if method == "POST" and parts == ["api", "projects"]:
        body = json_body(handler)
        root = Path(body["root"]).expanduser().resolve()
        name = body.get("name") or root.name
        agent = body.get("agent") or "cursor"
        result = init_project(root, name, agent)
        proj = register_project(root, name)
        result["project"] = proj
        return send_json(handler, result)

    if method == "DELETE" and len(parts) == 3 and parts[0] == "api" and parts[1] == "projects":
        remove_project(int(parts[2]))
        return send_json(handler, {"ok": True})

    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "projects":
        pid = int(parts[2])
        root = project_root(pid)
        rest = parts[3:]

        if method == "GET" and rest == []:
            return send_json(handler, {**get_project(pid), **project_info(root)})

        if method == "POST" and rest == ["agent"]:
            body = json_body(handler)
            return send_json(handler, set_agent(root, body.get("agent") or "cursor"))

        if method == "POST" and rest == ["clear"]:
            body = json_body(handler)
            if not body.get("confirm"):
                raise AvcError("請先確認要清空所有紀錄")
            return send_json(handler, clear_database(root))

        if method == "GET" and rest == ["status"]:
            return send_json(handler, status(root))

        if method == "GET" and rest == ["pulse"]:
            return send_json(handler, project_pulse(root))

        if method == "GET" and rest == ["records"]:
            hidden = qs.get("all", ["0"])[0] in {"1", "true"}
            return send_json(handler, list_records(root, include_hidden=hidden))

        if method == "POST" and rest == ["records"]:
            body = json_body(handler)
            return send_json(
                handler,
                save_user_record(root, body["label"], body.get("note") or ""),
            )

        if method == "GET" and rest[:1] == ["records"] and len(rest) == 2:
            return send_json(handler, get_record(root, int(rest[1])))

        if method in {"PATCH", "POST"} and rest[:1] == ["records"] and len(rest) == 3 and rest[2] == "meta":
            body = json_body(handler)
            return send_json(
                handler,
                update_record(
                    root,
                    int(rest[1]),
                    label=body.get("label"),
                    note=body.get("note"),
                ),
            )

        if method == "GET" and rest[:1] == ["records"] and len(rest) == 3 and rest[2] == "file":
            rel = qs.get("path", [""])[0]
            return send_json(handler, file_at_record(root, int(rest[1]), rel))

        if method == "POST" and rest[:1] == ["records"] and len(rest) == 3 and rest[2] == "restore":
            body = json_body(handler)
            return send_json(
                handler,
                restore(root, int(rest[1]), force=bool(body.get("force"))),
            )

        if method == "GET" and rest == ["diff"]:
            a = qs.get("from", [None])[0]
            b = qs.get("to", ["working"])[0]
            if a is None:
                raise AvcError("缺少 from")
            return send_json(handler, compare(root, a, b))

        if method == "GET" and rest == ["sessions"]:
            return send_json(handler, list_sessions(root))

        if method == "POST" and rest == ["sessions"]:
            body = json_body(handler)
            return send_json(
                handler,
                start_session(
                    root,
                    body.get("title") or "未命名對話",
                    body.get("source") or "",
                    body.get("agent"),
                ),
            )

        if method == "POST" and rest[:1] == ["sessions"] and len(rest) == 3 and rest[2] == "end":
            return send_json(handler, end_session(root, int(rest[1])))

        if method == "GET" and rest[:1] == ["sessions"] and len(rest) == 2:
            return send_json(handler, get_session(root, int(rest[1])))

        if method == "GET" and rest[:1] == ["sessions"] and len(rest) == 3 and rest[2] == "changes":
            return send_json(handler, session_changes(root, int(rest[1])))

        if method == "POST" and rest[:1] == ["sessions"] and len(rest) == 3 and rest[2] == "messages":
            body = json_body(handler)
            return send_json(
                handler,
                add_message(root, body["role"], body["content"], int(rest[1])),
            )

    raise AvcError("找不到這個操作")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys_stderr = __import__("sys").stderr
        print(f"[時光本] {self.address_string()} {fmt % args}", file=sys_stderr)

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PATCH(self) -> None:
        self._handle("PATCH")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            try:
                dispatch(method, self.path, self)
            except AvcError as e:
                send_json(self, {"error": str(e)}, 400)
            except KeyError:
                send_json(self, {"error": "找不到這個專案"}, 404)
            except Exception:
                send_json(self, {"error": traceback.format_exc()}, 500)
            return
        rel = path.lstrip("/") or "index.html"
        rel = posixpath.normpath(rel)
        if rel.startswith(".."):
            self.send_error(400)
            return
        file_path = WEB_DIR / rel
        if file_path.is_file():
            send_file(self, file_path)
            return
        if path == "/" or path == "/index.html":
            send_file(self, WEB_DIR / "index.html")
            return
        self.send_error(404)


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"時光本已在本機開啟：{url}")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已關閉")
        httpd.server_close()
