"""Directory reconciliation for a documented fixture envelope, no guessed Base layout."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path

from ..ha_tang.primitives import DataError, sha256, text_id
from .fixture import read_json


def scan_fixture_base(directory: Path, index_file: Path) -> dict:
    directory, index_file = directory.resolve(), index_file.resolve()
    index = read_json(index_file.read_bytes())
    if not isinstance(index, dict) or index.get("format") != "ktt-base-index-v1" or index.get("synthetic") is not True:
        raise DataError("FIXTURE_ONLY", "Chỉ nhận chỉ mục Base giả lập ktt-base-index-v1.")
    names = index.get("files")
    if not isinstance(names, list) or any(not isinstance(n, str) for n in names) or len(names) != len(set(names)):
        raise DataError("INVALID_BASE_INDEX", "Chỉ mục phải là danh sách tên file không trùng.")
    for name in names:
        if not name or "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts:
            raise DataError("UNSAFE_INDEX_PATH", "Tên file chỉ mục phải nằm trong thư mục Base.")
    if not directory.is_dir():
        raise DataError("MISSING_BASE_DIRECTORY", "Không có thư mục Base cần quét.")
    actual, items, issues, identities = set(), [], [], set()
    for path in sorted(directory.rglob("*.json")):
        if path.resolve() == index_file:
            continue
        name = path.relative_to(directory).as_posix()
        actual.add(name)
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(directory):
                raise DataError("UNSAFE_SOURCE_PATH", "File Base không được trỏ ra ngoài thư mục nguồn.")
            raw = path.read_bytes()
            item = read_json(raw)
            if not isinstance(item, dict) or item.get("format") != "ktt-base-item-v1" or item.get("synthetic") is not True:
                raise DataError("FIXTURE_ONLY", "File không phải Base fixture envelope.")
            encoded = text_id(item.get("payload_base64"), "payload_base64")
            try:
                decoded = read_json(base64.b64decode(encoded, validate=True))
            except (binascii.Error, ValueError) as exc:
                raise DataError("BASE_DECODE_ERROR", "Không giải mã được payload base64/JSON.") from exc
            if not isinstance(decoded, dict):
                raise DataError("INVALID_BASE_PAYLOAD", "Payload Base phải là object.")
            identity = (text_id(decoded.get("tenant")), text_id(decoded.get("request_id")))
            if identity in identities:
                raise DataError("DUPLICATE_BASE_ID", "Nhiều file có cùng tenant/request_id; cần xác minh revision.")
            identities.add(identity)
            items.append({"file": name, "hash": sha256(raw), "tenant": identity[0], "request_id": identity[1]})
        except DataError as exc:
            issues.append({"file": name, "code": exc.code, "message": str(exc)})
    missing, extra = sorted(set(names) - actual), sorted(actual - set(names))
    return {"fixture_only": True, "valid": not (missing or extra or issues),
            "files_found": len(actual), "index_count": len(names), "decoded_count": len(items),
            "missing": missing, "extra": extra, "issues": issues, "items": items}
