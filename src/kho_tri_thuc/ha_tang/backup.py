"""SQLite-consistent backups with immutable source artifacts; never overwrite a restore target."""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from .database import APPLICATION_ID, SCHEMA_VERSION, integrity
from .primitives import DataError, canonical_json, now_utc, sha256
from .store import Store


def _readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _check_database(path: Path) -> tuple[dict, list[tuple]]:
    with closing(_readonly(path)) as conn:
        app = conn.execute("PRAGMA application_id").fetchone()[0]
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if app != APPLICATION_ID or not 1 <= version <= SCHEMA_VERSION:
            raise DataError("INVALID_BACKUP_DB", "Backup không thuộc schema hiện tại của ứng dụng.")
        result = integrity(conn)
        if not result["ok"]:
            raise DataError("BACKUP_INTEGRITY", "DB backup không qua integrity/foreign-key check.")
        artifacts = list(conn.execute("SELECT hash,relative_path,byte_length FROM artifacts"))
    return result, artifacts


def _file_entry(path: Path) -> dict:
    content = path.read_bytes()
    return {"sha256": sha256(content), "bytes": len(content)}


def create_backup(store: Store, destination: Path) -> dict:
    destination = destination.resolve()
    if destination.exists():
        raise DataError("DESTINATION_EXISTS", "Thư mục backup đã tồn tại; không ghi đè.")
    if store.conn.in_transaction:
        raise DataError("ACTIVE_TRANSACTION", "Hoàn tất transaction của kết nối trước khi backup.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + ".partial-" + uuid4().hex)
    staging.mkdir()
    if getattr(store, "engine", "sqlite") == "postgres":
        # V13: kho PostgreSQL sao lưu về file kho.sqlite cùng schema (cũng là đường lùi "engine = sqlite" của TL 39)
        from .database import connect as _connect_sqlite
        from .sao_chep_bang import chep_pg_sang_sqlite
        with closing(_connect_sqlite(staging / "kho.sqlite")) as target:
            chep_pg_sang_sqlite(store.conn, target)
    else:
        with closing(sqlite3.connect(staging / "kho.sqlite")) as target:
            store.conn.backup(target)
    _, artifacts = _check_database(staging / "kho.sqlite")
    files = {"kho.sqlite": _file_entry(staging / "kho.sqlite")}
    for digest, relative, size in artifacts:
        if relative != f"raw/{digest}.bin" or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise DataError("INVALID_ARTIFACT_PATH", "Đường dẫn artifact trong DB không hợp lệ.")
        source = store.root / relative
        if source.is_symlink() or not source.resolve().is_relative_to(store.root):
            raise DataError("UNSAFE_ARTIFACT_PATH", "Artifact trỏ ra ngoài kho.")
        entry = _file_entry(source)
        if entry != {"sha256": digest, "bytes": size}:
            raise DataError("ARTIFACT_CHANGED", "Artifact thiếu hoặc đã bị sửa; backup chưa hoàn tất.")
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if _file_entry(target) != entry:
            raise DataError("BACKUP_COPY_CHANGED", "Artifact thay đổi trong lúc sao lưu.")
        files[relative] = entry
    manifest = {"format": "ktt-backup-v1", "fixture_only": True, "created_at": now_utc(),
                "schema_version": SCHEMA_VERSION, "entity_id": store.config.entity_id,
                "config_storage": "config_history inside kho.sqlite", "files": files}
    (staging / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8")
    verify_backup(staging)
    if destination.exists():
        raise DataError("DESTINATION_EXISTS", "Đích backup vừa được tạo bởi tiến trình khác.")
    staging.rename(destination)
    return {"backup": str(destination), "files": len(files), "verified": True, "fixture_only": True}


def verify_backup(directory: Path) -> dict:
    directory = directory.resolve()
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DataError("INVALID_BACKUP_MANIFEST", "Không đọc được manifest backup.") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != "ktt-backup-v1" or manifest.get("fixture_only") is not True or not isinstance(manifest.get("files"), dict):
        raise DataError("INVALID_BACKUP_MANIFEST", "Manifest backup sai cấu trúc.")
    for relative, entry in manifest["files"].items():
        if relative != "kho.sqlite" and not re.fullmatch(r"raw/[0-9a-f]{64}\.bin", relative):
            raise DataError("UNSAFE_BACKUP_PATH", "Manifest chứa đường dẫn ngoài phạm vi backup.")
        path = directory / relative
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise DataError("UNSAFE_BACKUP_PATH", "File backup trỏ ra ngoài thư mục.")
        try:
            if _file_entry(path) != entry:
                raise DataError("BACKUP_CHECKSUM", "Checksum hoặc kích thước file backup không khớp.")
        except OSError as exc:
            raise DataError("MISSING_BACKUP_FILE", "Backup thiếu file đã khai báo.") from exc
    if "kho.sqlite" not in manifest["files"]:
        raise DataError("MISSING_BACKUP_DB", "Manifest không có DB.")
    result, artifacts = _check_database(directory / "kho.sqlite")
    expected = {"kho.sqlite"}
    for digest, relative, size in artifacts:
        if relative != f"raw/{digest}.bin" or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise DataError("INVALID_ARTIFACT_PATH", "DB backup có đường dẫn artifact không hợp lệ.")
        expected.add(relative)
        if manifest["files"].get(relative) != {"sha256": digest, "bytes": size}:
            raise DataError("MISSING_BACKUP_EVIDENCE", "Manifest chưa chứa đủ bằng chứng được DB tham chiếu.")
    if set(manifest["files"]) != expected:
        raise DataError("UNEXPECTED_BACKUP_FILE", "Danh sách file khác tập DB/bằng chứng tại mốc backup.")
    return {"verified": True, "files": len(expected), "integrity": result, "fixture_only": True}


def restore_backup(directory: Path, destination: Path, config=None) -> dict:
    """``config`` (tùy chọn): cấu hình sẽ mở thư mục phục hồi. Engine postgres → schema đích phải trống, nếu không
    từ chối trước khi chép (V13 A3); engine sqlite hoặc không truyền → như cũ."""
    directory, destination = directory.resolve(), destination.resolve()
    if destination.exists():
        raise DataError("DESTINATION_EXISTS", "Chỉ restore vào thư mục chưa tồn tại; không ghi đè DB đang dùng.")
    verify_backup(directory)
    from .ket_noi import kiem_dich_phuc_hoi
    schema_dich = kiem_dich_phuc_hoi(config, destination / "kho.sqlite")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + ".partial-" + uuid4().hex)
    staging.mkdir()
    for relative in manifest["files"]:
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(directory / relative, target)
    # Revalidate the copied set to detect a source changing between verification and copy.
    (staging / "manifest.json").write_text(canonical_json(manifest), encoding="utf-8")
    verify_backup(staging)
    (staging / "manifest.json").rename(staging / "restore-manifest.json")
    if destination.exists():
        raise DataError("DESTINATION_EXISTS", "Đích restore vừa được tạo bởi tiến trình khác.")
    staging.rename(destination)
    result = {"restored_to": str(destination), "verified": True, "fixture_only": True}
    if schema_dich:
        result["schema_dich"] = schema_dich  # lần mở đầu với cấu hình này nạp kho.sqlite vào schema trống đó
    return result
