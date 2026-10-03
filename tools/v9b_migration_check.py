"""Exercise the V9b schema upgrade on an isolated SQLite backup.

The helper is deliberately aggregate-only: it does not query or print source
rows, transaction content, identifiers, or workstation paths.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path

from kho_tri_thuc.ha_tang.config import Config
from kho_tri_thuc.ha_tang.primitives import canonical_json, sha256
from kho_tri_thuc.ha_tang.store import Store


PROJECT = Path(__file__).resolve().parents[1]
SAFE_PARENT = (PROJECT / "var" / "vong-2" / "V9-giao-viec").resolve()


def _under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _snapshot(path: Path) -> dict[str, object]:
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        integrity = [str(row[0]) for row in conn.execute("PRAGMA integrity_check")]
        foreign_keys = sum(1 for _ in conn.execute("PRAGMA foreign_key_check"))
        return {
            "schema_version": int(conn.execute("PRAGMA user_version").fetchone()[0]),
            "integrity": integrity == ["ok"],
            "foreign_key_violations": foreign_keys,
        }


def _backup(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    uri = source.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as read, sqlite3.connect(target) as write:
        read.backup(write)


def run(config_path: Path, output: Path) -> dict[str, object]:
    config = Config.load(config_path)
    source = config.data_dir / "kho.sqlite"
    if not source.is_file() or not _under(source, PROJECT):
        raise RuntimeError("Nguồn kho không hợp lệ cho kiểm thử migration.")
    if not _under(output, SAFE_PARENT) or output == SAFE_PARENT:
        raise RuntimeError("Đích migration phải là thư mục con V9-giao-viec.")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    before_hash = sha256(source.read_bytes())
    source_before = _snapshot(source)
    copied = output / "data" / "kho.sqlite"
    _backup(source, copied)
    copied_before = _snapshot(copied)
    with Store(Config.load(config_path, output / "data")):
        pass
    after = _snapshot(copied)
    source_unchanged = before_hash == sha256(source.read_bytes())
    result = {
        "status": "OK",
        "source_unchanged": source_unchanged,
        "source_schema_version": source_before["schema_version"],
        "copy_schema_before": copied_before["schema_version"],
        "schema_version": after["schema_version"],
        "integrity": "ok" if after["integrity"] else "failed",
        "foreign_key_violations": after["foreign_key_violations"],
    }
    (output / "MIGRATION-CHECK.json").write_text(canonical_json(result), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="V9b isolated migration check")
    parser.add_argument("--config", type=Path, default=PROJECT / "cau_hinh.that.toml")
    parser.add_argument("--output", type=Path, default=SAFE_PARENT / "migration-v18-copy")
    args = parser.parse_args()
    try:
        result = run(args.config.resolve(), args.output.resolve())
    except Exception as exc:
        print(canonical_json({"status": "FAILED", "error_type": type(exc).__name__}))
        return 1
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
