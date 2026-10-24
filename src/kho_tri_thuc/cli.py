"""M1–M6 offline CLI. All source mappings remain explicitly synthetic."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from zipfile import BadZipFile
from dataclasses import asdict
from pathlib import Path

from .ha_tang.backup import create_backup, restore_backup, verify_backup
from .ha_tang.config import Config
from .ha_tang.primitives import DataError
from .ha_tang.store import Store
from .nguon.base_inventory import scan_fixture_base
from .nguon.fixture import CATALOG, FixtureAdapter, check_junsky_bundle
from .nguon.that import SourceMetadata, ThatAdapter
from .nguon.fixture import read_json


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Kho tri thức M1–M6 — chỉ fixture, chưa vận hành Junsky.")
    command.add_argument("--config", type=Path, default=Path("cau_hinh.toml"))
    command.add_argument("--data-dir", type=Path, help="Kho fixture riêng, hữu ích khi demo/restore.")
    sub = command.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="Trạng thái adapter thực và fixture.")
    sub.add_parser("init", help="Khởi tạo/nâng schema SQLite fixture.")
    sub.add_parser("status", help="Thống kê và kiểm tra integrity.")
    for name in ("validate", "ingest"):
        item = sub.add_parser(name, help="Kiểm tra file fixture" if name == "validate" else "Nạp fixture, kiểm tra chống trùng xuyên file.")
        item.add_argument("file", type=Path)
    source = sub.add_parser("nap-nguon", help="Nạp nguồn PLHN offline vào kho that; chưa xuất/nhập Junsky.")
    source.add_argument("--nguon", choices=("sao_ke", "hoa_don", "bang_ke", "base", "junsky"), required=True)
    source.add_argument("--duong-dan", type=Path, required=True)
    source.add_argument("--as-of", required=True)
    source.add_argument("--exported-at", required=True)
    source.add_argument("--known-at")
    source.add_argument("--known-at-basis", required=True)
    source.add_argument("--coverage-from")
    source.add_argument("--coverage-to-exclusive")
    source.add_argument("--snapshot-id")
    source.add_argument("--reuse-root", type=Path, help="Thư mục script bản 1.2 đã kiểm kê, dùng cho XML/PDF.")
    source.add_argument("--posting-evidence-complete", action="store_true")
    source.add_argument("--scope-open-items-complete", action="store_true")
    source.add_argument("--lock-from")
    source.add_argument("--lock-to")
    source.add_argument("--lock-scope")
    source.add_argument("--hieu-luc-tu", help="Hiệu lực danh mục/cây hóa đơn; mặc định lấy operation.catalog_valid_from.")
    knowledge_import = sub.add_parser("nap-tri-thuc", help="Nạp workbook tri thức thành hàng chờ duyệt, không tự phê duyệt.")
    knowledge_import.add_argument("workbooks", type=Path, nargs="+")
    knowledge_import.add_argument("--actor", required=True)
    knowledge_import.add_argument("--at", required=True)
    knowledge_import.add_argument("--hieu-luc-tu", help="Hiệu lực danh mục/cây hóa đơn; không đổi ngày hiệu lực quy tắc/từ khóa.")
    knowledge_export = sub.add_parser("xuat-tri-thuc", help="Xuất workbook tri thức đọc/sửa được cho người duyệt.")
    knowledge_export.add_argument("--duong-dan", type=Path, required=True)
    knowledge_export.add_argument("--actor", required=True)
    knowledge_export.add_argument("--at", required=True)
    knowledge_review = sub.add_parser("nhap-yeu-cau-duyet", help="Nhập yêu cầu duyệt từ workbook; chưa tạo phê duyệt.")
    knowledge_review.add_argument("workbook", type=Path)
    knowledge_review.add_argument("--actor", required=True)
    knowledge_review.add_argument("--at", required=True)
    knowledge_decide = sub.add_parser("duyet-tri-thuc", help="Áp dụng APPROVE/REJECT do người duyệt đã điền trong workbook.")
    knowledge_decide.add_argument("workbook", type=Path)
    knowledge_decide.add_argument("--actor", required=True)
    knowledge_decide.add_argument("--at", required=True)
    knowledge_decide.add_argument("--chi-nhom", help="Danh sách sheet, ngăn cách bằng dấu phẩy.")
    knowledge_decide.add_argument("--kho-thu", action="store_true", help="Chỉ kiểm tra workbook, không ghi sự kiện.")
    quarantine = sub.add_parser("xem-cach-ly", help="Xuất các bản ghi bị cách ly của một lần nạp kho that.")
    quarantine.add_argument("--attempt-id", required=True)
    quarantine.add_argument("--output", type=Path, required=True)
    bank_list = sub.add_parser("liet-ke-sao-ke", help="Liệt kê ID sao kê kho that mà không in diễn giải.")
    bank_list.add_argument("--tu", required=True)
    bank_list.add_argument("--den", required=True)
    bank_list.add_argument("--chua-de-xuat", action="store_true")
    bank_list.add_argument("--output", type=Path, required=True)
    real_session = sub.add_parser("mo-phien-that", help="Mở phiên shadow từ sao kê kho that trong một khoảng ngày.")
    real_session.add_argument("--attempt-id", required=True)
    real_session.add_argument("--tu", required=True)
    real_session.add_argument("--den", required=True)
    real_session.add_argument("--cutoff", required=True)
    real_session.add_argument("--actor", required=True)
    real_session.add_argument("--mode", choices=("shadow",), default="shadow")
    real_session.add_argument("--output", type=Path)
    report = sub.add_parser("report")
    report.add_argument("--attempt-id")
    bundle = sub.add_parser("check-bundle", help="Kiểm tra vai trò Junsky giả lập, chưa mở phiên.")
    bundle.add_argument("files", type=Path, nargs="+")
    base = sub.add_parser("scan-base", help="Quét thư mục và giải mã Base fixture.")
    base.add_argument("directory", type=Path)
    base.add_argument("--index", type=Path, required=True)
    backup = sub.add_parser("backup")
    backup.add_argument("destination", type=Path)
    verify = sub.add_parser("verify-backup")
    verify.add_argument("directory", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("directory", type=Path)
    restore.add_argument("destination", type=Path)
    workflow = sub.add_parser("workflow", help="Thao tác M2–M6 bằng request JSON có actor/thời điểm rõ.")
    from .workflow import ACTIONS
    workflow.add_argument("action", choices=ACTIONS)
    workflow.add_argument("request", type=Path)
    workflow.add_argument("--output", type=Path)
    demo = sub.add_parser("demo-full", help="Tự chạy hai phiên M1–M6 bằng dữ liệu giả lập ở thư mục mới.")
    demo.add_argument("destination", type=Path)
    web = sub.add_parser("serve", help="Mở giao diện HTML cục bộ để nhận tệp gốc và thử dữ liệu mẫu.")
    web.add_argument("--root", type=Path, help="Kho giao diện; mặc định var/web cạnh cấu hình.")
    web.add_argument("--port", type=int, default=8766)
    web.add_argument("--no-browser", action="store_true")
    return command


def run(args: argparse.Namespace) -> tuple[dict, int]:
    if args.command == "serve":
        from .giao_dien.server import serve
        serve(args.config, args.root or args.config.resolve().parent / "var" / "web", args.port, not args.no_browser)
        return {"stopped": True}, 0
    if args.command == "catalog":
        return {"fixture_only": True, "sources": CATALOG}, 0
    if args.command == "verify-backup":
        return verify_backup(args.directory), 0
    if args.command == "restore":
        # V13 A3: cấu hình engine postgres → kiểm schema đích trống trước khi chép (sqlite: như cũ)
        restore_config = Config.load(args.config, args.destination) if args.config.is_file() else None
        return restore_backup(args.directory, args.destination, restore_config), 0
    if args.command == "scan-base":
        report = scan_fixture_base(args.directory, args.index)
        return report, 0 if report["valid"] else 2
    if args.command == "demo-full":
        from .kiem_chung.demo import run_demo
        return run_demo(args.config, args.destination), 0
    config = Config.load(args.config, args.data_dir)
    if args.command in ("validate", "check-bundle"):
        adapter = FixtureAdapter()
        if args.command == "check-bundle":
            report = check_junsky_bundle([adapter.read(path.read_bytes(), config) for path in args.files])
        else:
            batch = adapter.read(args.file.read_bytes(), config)
            report = {"fixture_only": True, "valid": batch.valid, "validation_scope": "file-only; chưa đối chiếu DB",
                      "source": batch.source, "record_count": len(batch.raw_records), "totals_minor": batch.totals,
                      "issues": [asdict(issue) for issue in batch.issues]}
        return report, 0 if report["valid"] else 2
    from .ha_tang.ket_noi import da_khoi_tao
    if args.command != "init" and not da_khoi_tao(config, config.data_dir / "kho.sqlite"):
        raise DataError("NOT_INITIALIZED", "Kho chưa khởi tạo; chạy init trước.")
    with Store(config) as store:
        if args.command in ("init", "status"):
            report = store.status()
            return report, 0 if report["integrity"]["ok"] else 2
        if args.command == "ingest":
            report = store.ingest(args.file)
            return report, 0 if report["state"] == "COMMITTED" else 2
        if args.command == "nap-nguon":
            as_of = args.as_of
            coverage_from = args.coverage_from or as_of
            coverage_to = args.coverage_to_exclusive or (date.fromisoformat(as_of) + timedelta(days=1)).isoformat()
            locks = ()
            if any((args.lock_from, args.lock_to, args.lock_scope)):
                if not all((args.lock_from, args.lock_to, args.lock_scope)):
                    raise DataError("LOCK_DECLARATION", "Khai kỳ khóa cần đủ lock-from, lock-to và lock-scope.")
                locks = ((args.lock_from, args.lock_to, args.lock_scope),)
            metadata = SourceMetadata(as_of, args.exported_at, args.known_at_basis, coverage_from, coverage_to, args.known_at,
                                      args.snapshot_id, "PLHN_" + args.nguon.upper(), posting_evidence_complete=args.posting_evidence_complete,
                                      scope_open_items_complete=args.scope_open_items_complete, catalog_valid_from=args.hieu_luc_tu)
            adapter = ThatAdapter(args.nguon, args.duong_dan, metadata, reuse_root=args.reuse_root, lock_periods=locks)
            report = store.ingest(args.duong_dan, adapter)
            return report, 0 if report["state"] == "COMMITTED" else 2
        if args.command == "nap-tri-thuc":
            from .tri_thuc.human_workbook import HumanKnowledgeWorkbook
            return HumanKnowledgeWorkbook(store).import_sources(args.workbooks, args.actor, args.at, args.hieu_luc_tu), 0
        if args.command == "xuat-tri-thuc":
            from .tri_thuc.human_workbook import HumanKnowledgeWorkbook
            return HumanKnowledgeWorkbook(store).export_human_workbook(args.duong_dan, args.actor, args.at), 0
        if args.command == "nhap-yeu-cau-duyet":
            from .tri_thuc.human_workbook import HumanKnowledgeWorkbook
            return HumanKnowledgeWorkbook(store).import_review_requests(args.workbook, args.actor, args.at), 0
        if args.command == "duyet-tri-thuc":
            from .tri_thuc.human_workbook import HumanKnowledgeWorkbook
            if config.environment != "that":
                raise DataError("THAT_REQUIRED", "Duyệt workbook vận hành chỉ chạy trong kho that.")
            sheets = set(filter(None, (args.chi_nhom or "").split(","))) or None
            return HumanKnowledgeWorkbook(store).apply_human_decisions(args.workbook, args.actor, args.at, sheets=sheets, dry_run=args.kho_thu), 0
        if args.command == "xem-cach-ly":
            report = store.quarantined(args.attempt_id)
            from .ha_tang.primitives import canonical_json
            from .ha_tang.store import write_immutable
            write_immutable(args.output, canonical_json(report).encode("utf-8"))
            return {"path": str(args.output), "count": report["count"], "environment": "that"}, 0
        if args.command == "liet-ke-sao-ke":
            report = store.bank_documents(args.tu, args.den, without_proposal=args.chua_de_xuat)
            from .ha_tang.primitives import canonical_json
            from .ha_tang.store import write_immutable
            write_immutable(args.output, canonical_json(report).encode("utf-8"))
            return {"path": str(args.output), "count": report["count"], "environment": "that"}, 0
        if args.command == "mo-phien-that":
            if config.environment != "that":
                raise DataError("THAT_REQUIRED", "Mở phiên vận hành chỉ chạy trong kho that.")
            banks = store.bank_documents(args.tu, args.den, without_proposal=True)["records"]
            if not banks:
                raise DataError("NO_BANK_DOCUMENTS", "Không có sao kê chưa đề xuất trong khoảng đã chọn.")
            from .trang_thai.service import Sessions
            try:
                session = Sessions(store).open(args.attempt_id, [item["id"] for item in banks], args.cutoff, args.actor, args.mode)
            except DataError as exc:
                if exc.code != "CATALOG_CHANGE_PENDING":
                    raise
                pending = store.conn.execute("""SELECT COUNT(*) FROM knowledge_versions k
                    WHERE NOT EXISTS (SELECT 1 FROM knowledge_events e WHERE e.version_id=k.id AND e.action='APPROVE')
                    AND NOT EXISTS (SELECT 1 FROM knowledge_events e WHERE e.version_id=k.id AND e.action='REVOKE')""").fetchone()[0]
                raise DataError("CATALOG_CHANGE_PENDING", f"Danh mục snapshot chưa khớp tri thức đã duyệt; còn {pending} phiên bản PENDING.") from exc
            result = {"session_id": session["id"], "bank_count": len(banks), "mode": args.mode, "environment": "that"}
            if args.output:
                from .ha_tang.primitives import canonical_json
                from .ha_tang.store import write_immutable
                write_immutable(args.output, canonical_json(result).encode("utf-8"))
                result["path"] = str(args.output)
            return result, 0
        if args.command == "report":
            return store.report(args.attempt_id), 0
        if args.command == "backup":
            return create_backup(store, args.destination), 0
        if args.command == "workflow":
            from .workflow import dispatch
            from .ha_tang.primitives import canonical_json
            from .ha_tang.store import write_immutable
            result = dispatch(store, args.action, read_json(args.request.read_bytes()))
            if args.output:
                write_immutable(args.output, canonical_json(result).encode("utf-8"))
            return result, 0
    raise DataError("UNKNOWN_COMMAND", "Lệnh không hỗ trợ.")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        result, status = run(args)
    except DataError as exc:
        result, status = {"error": exc.code, "message": str(exc), "locator": exc.locator}, 2
    except (KeyError, TypeError, ValueError, ArithmeticError, BadZipFile) as exc:
        result, status = {"error": "INVALID_REQUEST_CONTENT", "message": f"Nội dung đầu vào sai cấu trúc/kiểu ({type(exc).__name__}); xem hợp đồng và request mẫu."}, 2
    except (OSError, sqlite3.Error) as exc:
        # Do not print source data, account IDs, or SQL payloads in unhandled errors.
        result, status = {"error": "IO_OR_DATABASE_ERROR", "message": f"Lỗi {type(exc).__name__}; kiểm tra đường dẫn/quyền hoặc tình trạng DB."}, 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return status
