from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import threading
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from .. import __version__
from ..ha_tang.config import Config
from ..ha_tang.primitives import DataError, canonical_json, now_utc, sha256
from ..ha_tang.store import Store, write_immutable
from ..kiem_chung.fixtures import bank_fixture, bundle_fixture
from ..nguon.fixture import FixtureAdapter, read_json
from .intake import Intake, MAX_FILE_SIZE, SOURCES
from .operations import Operations

ASSETS = Path(__file__).parent / "assets"


class LocalApp:
    def __init__(self, config_path, root):
        self.root = Path(root).resolve()
        self.root_id = sha256(str(self.root).casefold().encode("utf-8"))
        self.config_path = Path(config_path).resolve()
        loaded = Config.load(self.config_path)
        self.is_that = loaded.environment == "that"
        self.operations = Operations(self.config_path, self.root) if self.is_that else None
        self.intake = Intake(self.root / "ho-so-goc") if not self.is_that else None
        self.demo_config = Config.load(self.config_path, self.root / "mo-phong") if not self.is_that else None
        self.token = secrets.token_urlsafe(32)
        self.mutation_lock = threading.Lock()
        if not self.is_that:
            with Store(self.demo_config):
                pass

    def state(self):
        if self.is_that:
            return {**self.operations.state(), "storage_path": str(self.operations.config.data_dir), "max_file_bytes": MAX_FILE_SIZE,
                    "version": __version__, "real_processing": True, "junsky_export": False, "ai_required": False}
        listing = self.intake.listing()
        with Store(self.demo_config) as store:
            demo = store.status()
            attempts = [json.loads(r[0]) for r in store.conn.execute("SELECT report_json FROM attempts WHERE report_json IS NOT NULL ORDER BY rowid DESC LIMIT 12")]
        return {**listing, "sources": SOURCES, "demo": demo, "demo_attempts": attempts, "storage_path": str(self.intake.root),
                "max_file_bytes": MAX_FILE_SIZE, "version": __version__, "real_processing": False, "junsky_export": False, "ai_required": False}

    def demo_sample(self, source):
        if self.is_that:
            raise DataError("THAT_UI", "Bản vận hành không dùng dữ liệu mô phỏng.")
        if source not in {"sao_ke", "junsky_xuat"}:
            raise DataError("DEMO_SOURCE", "Mẫu tích hợp sẵn gồm sao kê và bộ Junsky giả lập.")
        return canonical_json(bank_fixture() if source == "sao_ke" else bundle_fixture()).encode("utf-8")

    def demo_import(self, raw, name, commit=False):
        if self.is_that:
            raise DataError("THAT_UI", "Bản vận hành không nạp dữ liệu mô phỏng.")
        # Fixture checks stay in the existing adapter. Never rewrite real data to synthetic.
        batch = FixtureAdapter().read(raw, self.demo_config)
        report = {"fixture_only": True, "valid": batch.valid, "source": batch.source, "input_records": len(batch.raw_records),
                  "control_totals_minor": batch.totals, "issues": [asdict(i) for i in batch.issues], "state": "VALIDATED" if batch.valid else "REJECTED"}
        if commit:
            name = name.replace("\\", "/").split("/")[-1]
            if not name or len(name) > 240:
                raise DataError("FILE_NAME", "Tên mẫu không hợp lệ.")
            folder = self.root / "mo-phong-upload" / sha256(raw)
            path = folder / name
            if not path.resolve().is_relative_to(self.root / "mo-phong-upload"):
                raise DataError("FILE_NAME", "Đường dẫn mẫu không hợp lệ.")
            write_immutable(path, raw)
            with Store(self.demo_config) as store:
                return store.ingest(path)
        return report


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, app, port=8766):
        self.app = app
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"


class Handler(BaseHTTPRequestHandler):
    server_version = "KhoTriThucLocal"

    def log_message(self, *_):
        # No filenames, notes or source contents in console request logs.
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError):
            # Closing a browser or a readiness probe may close the socket early.
            # Atomic raw/receipt publication remains responsible for retry safety.
            pass

    def send_content(self, status, content, mime="application/json; charset=utf-8", headers=None):
        if not isinstance(content, bytes):
            content = canonical_json(content).encode("utf-8")
        self.send_response(status)
        for key, value in {
            "Content-Type": mime, "Content-Length": str(len(content)), "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            **(headers or {}),
        }.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(content)

    def authorize(self, private=False):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if host not in allowed:
            raise DataError("LOCAL_HOST_ONLY", "Chỉ mở giao diện bằng địa chỉ local của ứng dụng.")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise DataError("CROSS_ORIGIN", "Không nhận yêu cầu từ website khác.")
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://" + h for h in allowed}:
            raise DataError("CROSS_ORIGIN", "Không nhận yêu cầu từ website khác.")
        if private and not secrets.compare_digest(self.headers.get("X-KTT-Token", ""), self.server.app.token):
            raise DataError("SESSION_TOKEN", "Phiên giao diện đã đổi. Tải lại trang rồi thử lại.")

    def body(self, limit=MAX_FILE_SIZE):
        if self.headers.get("Transfer-Encoding"):
            raise DataError("REQUEST_LENGTH", "Cần khai báo độ dài nội dung.")
        value = self.headers.get("Content-Length", "")
        if not value.isdigit() or len(value) > 12:
            raise DataError("REQUEST_LENGTH", "Độ dài nội dung không hợp lệ.")
        length = int(value)
        if length > limit:
            raise DataError("FILE_TOO_LARGE", "Mỗi tệp tối đa 50 MB.")
        content = self.rfile.read(length)
        if len(content) != length:
            raise DataError("INCOMPLETE_UPLOAD", "Tệp chưa được truyền đủ; hãy thử lại.")
        return content

    def json_body(self, limit=1024 * 1024):
        raw = self.body(limit)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise DataError("INVALID_REQUEST", "Nội dung yêu cầu phải là JSON UTF-8 hợp lệ.") from exc
        if not isinstance(value, dict):
            raise DataError("INVALID_REQUEST", "Yêu cầu phải là một object JSON.")
        return value

    def that(self):
        if not self.server.app.is_that:
            raise DataError("THAT_UI", "Chức năng này chỉ có trong giao diện kho thật.")
        return self.server.app.operations

    def do_GET(self):
        self.handle_route(False)

    def do_POST(self):
        self.handle_route(True)

    def do_OPTIONS(self):
        self.send_content(403, {"error": "CROSS_ORIGIN", "message": "Giao diện chỉ dùng tại máy này."})

    def handle_route(self, post):
        try:
            path = urlsplit(self.path).path
            query = parse_qs(urlsplit(self.path).query)
            self.authorize(private=post or path.startswith("/api/") and path != "/api/health")
            app = self.server.app
            if not post:
                if path == "/api/health":
                    return self.send_content(200, {"application": "kho-tri-thuc-local", "version": __version__, "local_only": True, "root_id": app.root_id})
                if path in {"/", "/index.html"}:
                    raw = (ASSETS / ("that.html" if app.is_that else "index.html")).read_bytes().replace(b"__KTT_TOKEN__", app.token.encode())
                    return self.send_content(200, raw, "text/html; charset=utf-8")
                if path in {"/app.js", "/style.css", "/that.css", "/mark.svg"}:
                    mime = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}[Path(path).suffix]
                    asset = "that.js" if path == "/app.js" and app.is_that else path[1:]
                    return self.send_content(200, (ASSETS / asset).read_bytes(), mime)
                if path == "/api/state":
                    return self.send_content(200, app.state())
                if path == "/api/sample":
                    source = query.get("source", [""])[0]
                    return self.send_content(200, app.demo_sample(source), headers={"Content-Disposition": f'attachment; filename="{source}_MO_PHONG.json"'})
                if path.startswith("/api/files/") and path.endswith("/download"):
                    identifier = path.split("/")[3]
                    receipt, content = app.intake.download(identifier)
                    return self.send_content(200, content, "application/octet-stream", {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(receipt["name"], safe="")})
                if path == "/api/that/job":
                    return self.send_content(200, self.that().job(query.get("id", [""])[0]))
                if path == "/api/that/knowledge":
                    category = query.get("category", [None])[0]
                    return self.send_content(200, self.that().knowledge_rows(category, query.get("q", [""])[0], int(query.get("page", ["1"])[0])))
                if path == "/api/that/catalog":
                    return self.send_content(200, self.that().catalog(query.get("date", [""])[0], query.get("cutoff", [now_utc()])[0]))
                if path == "/api/that/source-settings":
                    return self.send_content(200, self.that().source_settings())
                if path == "/api/that/overview":
                    return self.send_content(200, self.that().overview())
                if path == "/api/that/runs":
                    return self.send_content(200, self.that().runs())
                if path == "/api/that/history":
                    return self.send_content(200, self.that().history())
                if path == "/api/that/knowledge-cards":
                    return self.send_content(200, self.that().knowledge_cards(query.get("q", [""])[0]))
                if path == "/api/that/report":
                    return self.send_content(200, self.that().report(query.get("attempt_id", [""])[0]))
                if path == "/api/that/proposals":
                    return self.send_content(200, self.that().proposal_rows(query.get("session_id", [""])[0], query.get("at", [now_utc()])[0]))
                if path.startswith("/api/that/quick/") and path.endswith("/download"):
                    parts = path.split("/")
                    if len(parts) != 6 or parts[:4] != ["", "api", "that", "quick"]:
                        raise DataError("QUICK_EXPORT_FILE", "Đường dẫn tải tệp xuất không hợp lệ.")
                    name, raw = self.that().quick_file(parts[4], query.get("file", [""])[0])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                             {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path == "/api/that/quick":
                    return self.send_content(200, self.that().quick_rows(query.get("run_id", [""])[0]))
                if path == "/api/that/outside-catalog/download":
                    raw = self.that().outside_catalog()
                    return self.send_content(200, raw, "application/json; charset=utf-8", {"Content-Disposition": "attachment; filename=MA-NGOAI-DANH-MUC.json"})
                if path.startswith("/api/that/shadow/") and path.endswith("/download"):
                    parts = path.split("/")
                    name, raw = self.that().shadow_file(parts[4], parts[5])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
            else:
                if path == "/api/upload":
                    encoded = self.headers.get("X-File-Info", "")
                    if len(encoded) > 20000:
                        raise DataError("FILE_METADATA", "Thông tin tệp quá dài.")
                    metadata = read_json(unquote(encoded).encode("utf-8"))
                    result = app.intake.receive(self.body(), metadata)
                    return self.send_content(200 if result["duplicate"] else 201, result)
                if path == "/api/that/source":
                    encoded = self.headers.get("X-Source-Info", "")
                    if len(encoded) > 20000:
                        raise DataError("SOURCE_UPLOAD_METADATA", "Thông tin tệp nguồn quá dài.")
                    metadata = json.loads(unquote(encoded))
                    return self.send_content(201, self.that().receive_source(self.body(), metadata))
                if path == "/api/that/quick/upload":
                    encoded = self.headers.get("X-Quick-Info", "")
                    metadata = json.loads(unquote(encoded))
                    raw = self.body()
                    operations = self.that()
                    return self.send_content(201, operations.start("dinh-khoan", lambda report: operations.quick_upload(raw, metadata.get("name"), metadata.get("relative_path", ""), progress=report), progress=True))
                if path == "/api/that/quick/repropose":
                    payload = self.json_body()
                    operations = self.that()
                    return self.send_content(202, operations.start("de-xuat-lai", lambda report: operations.quick_repropose(payload.get("run_id"), progress=report), progress=True))
                if path == "/api/that/quick/decide":
                    payload = self.json_body()
                    return self.send_content(200, self.that().quick_decide(payload.get("run_id"), payload.get("items"), payload.get("actor", "CFO_NTD"), payload.get("at", now_utc())))
                if path == "/api/that/quick/export":
                    payload = self.json_body()
                    return self.send_content(200, self.that().quick_export(payload.get("run_id"), junsky_files=payload.get("junsky_files", False) is True, actor=payload.get("actor", "CFO_NTD")))
                if path == "/api/that/reload":
                    self.json_body()
                    return self.send_content(202, self.that().reload_sources())
                if path == "/api/that/learning-settings":
                    return self.send_content(200, self.that().save_learning_settings(self.json_body()))
                if path == "/api/that/cash-mapping":
                    payload = self.json_body()
                    return self.send_content(200, self.that().set_cash_mapping(payload.get("bank_account"), payload.get("cash_account") or None))
                if path == "/api/that/open":
                    payload = self.json_body()
                    return self.send_content(200, self.that().open_export(payload.get("run_id"), payload.get("file") or None))
                if path == "/api/that/source-settings":
                    payload = self.json_body()
                    return self.send_content(200, self.that().save_source_settings(payload))
                if path == "/api/that/knowledge/import":
                    encoded = self.headers.get("X-Knowledge-Info", "")
                    metadata = json.loads(unquote(encoded))
                    return self.send_content(201, self.that().knowledge_upload(self.body(), metadata.get("name"), metadata.get("actor"), metadata.get("at"), metadata.get("catalog_valid_from")))
                if path == "/api/that/ingest":
                    payload = self.json_body()
                    return self.send_content(202, self.that().start("nap-nguon", lambda: self.that().ingest(payload)))
                if path == "/api/that/knowledge/decide":
                    payload = self.json_body()
                    return self.send_content(200, self.that().decide_knowledge(payload.get("items"), payload.get("actor"), payload.get("at")))
                if path == "/api/that/session/run":
                    payload = self.json_body()
                    return self.send_content(202, self.that().start("chay-de-xuat", lambda: self.that().run_session(payload)))
                if path == "/api/that/proposals/decide":
                    payload = self.json_body()
                    return self.send_content(200, self.that().decide_proposals(payload.get("session_id"), payload.get("items"), payload.get("actor"), payload.get("at")))
                if path == "/api/that/shadow/export":
                    payload = self.json_body()
                    return self.send_content(202, self.that().start("xuat-mo-phong", lambda: self.that().shadow_export(payload.get("session_id"), payload.get("actor"), payload.get("at"))))
                if path in {"/api/demo/validate", "/api/demo/ingest"}:
                    name = unquote(self.headers.get("X-File-Name", "fixture.json"))
                    with app.mutation_lock:
                        report = app.demo_import(self.body(), name, path.endswith("ingest"))
                    return self.send_content(200, report)
                if path == "/api/shutdown":
                    self.body(1024)
                    self.send_content(200, {"stopped": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
            self.send_content(404, {"error": "NOT_FOUND", "message": "Không tìm thấy chức năng này."})
        except DataError as exc:
            status = 403 if exc.code in {"LOCAL_HOST_ONLY", "CROSS_ORIGIN", "SESSION_TOKEN"} else 413 if exc.code == "FILE_TOO_LARGE" else 400
            self.send_content(status, {"error": exc.code, "message": str(exc)})
        except (ValueError, TypeError, KeyError, RecursionError):
            self.send_content(400, {"error": "INVALID_REQUEST", "message": "Thông tin gửi lên không hợp lệ; tệp chưa được xử lý."})
        except (OSError, sqlite3.Error):
            self.send_content(500, {"error": "LOCAL_STORAGE_ERROR", "message": "Không đọc/ghi được kho trên máy. Kiểm tra dung lượng, quyền và thử lại."})


def serve(config_path, root, port=8766, open_browser=True):
    if not 1 <= port <= 65535:
        raise DataError("INVALID_PORT", "Cổng phải từ 1 đến 65535.")
    app = LocalApp(config_path, root)
    with LocalServer(app, port) as server:
        print(f"Kho tri thức: {server.url} — chỉ trên máy này. Nhấn Ctrl+C để dừng.", flush=True)
        if open_browser:
            webbrowser.open(server.url)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description="Giao diện HTML nội bộ của Kho tri thức")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    serve(args.config, args.root, args.port, not args.no_browser)


if __name__ == "__main__":
    main()
