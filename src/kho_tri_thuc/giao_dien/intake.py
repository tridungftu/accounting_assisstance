from __future__ import annotations

import json
import re
import threading
import unicodedata
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, date_iso, now_utc, sha256, text_id
from ..ha_tang.store import write_immutable

SOURCES = {
    "sao_ke": "Sao kê ngân hàng",
    "hoa_don_xml": "Hóa đơn XML",
    "hoa_don_bang_ke": "Bảng kê hóa đơn",
    "base": "Chứng từ Base",
    "junsky_xuat": "Dữ liệu Junsky",
}
EXTENSIONS = {".pdf", ".xlsx", ".xls", ".xml", ".csv", ".tsv", ".json", ".txt", ".zip"}
MAX_FILE_SIZE = 50 * 1024 * 1024


class Intake:
    """Raw real-source intake, separate from the fixture accounting database.

    Content-addressed bytes and receipts are published atomically, without
    claiming that a source adapter has parsed or validated accounting records.
    """
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def safe_path(self, relative):
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root) or path.is_symlink():
            raise DataError("UNSAFE_INTAKE_PATH", "Đường dẫn hồ sơ không hợp lệ.")
        return path

    def receive(self, content, metadata):
        if not content:
            raise DataError("EMPTY_FILE", "Tệp rỗng; chưa lưu hồ sơ.")
        if len(content) > MAX_FILE_SIZE:
            raise DataError("FILE_TOO_LARGE", "Mỗi tệp tối đa 50 MB.")
        if not isinstance(metadata, dict) or set(metadata) - {"name", "source", "period", "entity", "note", "relative_path", "modified_at"}:
            raise DataError("FILE_METADATA", "Thông tin tệp không hợp lệ.")
        source = metadata.get("source")
        if not isinstance(source, str) or source not in SOURCES:
            raise DataError("SOURCE_REQUIRED", "Chọn loại dữ liệu trước khi lưu.")
        name = unicodedata.normalize("NFC", text_id(metadata.get("name"), "Tên tệp"))
        if len(name) > 240 or any(c in name for c in '/\\\x00\r\n') or any(ord(c) < 32 for c in name) or name in {".", ".."}:
            raise DataError("FILE_NAME", "Tên tệp không hợp lệ; dùng tên không chứa đường dẫn.")
        if Path(name).suffix.lower() not in EXTENSIONS:
            raise DataError("FILE_TYPE", "Nhận PDF, Excel, XML, CSV, TSV, JSON, TXT hoặc ZIP. ZIP được giữ nguyên, chưa giải nén.")
        entity = text_id(metadata.get("entity"), "Pháp nhân")
        period = text_id(metadata.get("period"), "Kỳ dữ liệu")
        if len(entity) > 80 or not re.fullmatch(r"\d{4}-\d{2}", period):
            raise DataError("INTAKE_SCOPE", "Nhập pháp nhân và kỳ dữ liệu dạng năm-tháng.")
        date_iso(period + "-01")
        note, original_relative = metadata.get("note", ""), metadata.get("relative_path", "")
        if not isinstance(note, str) or len(note) > 2000 or not isinstance(original_relative, str) or len(original_relative) > 2048:
            raise DataError("FILE_METADATA", "Ghi chú hoặc đường dẫn gốc quá dài.")
        modified = metadata.get("modified_at")
        if modified is not None and (type(modified) is not int or not 0 <= modified <= 8640000000000000):
            raise DataError("FILE_METADATA", "Thời gian sửa tệp trên máy không hợp lệ.")
        # Explicit test data belongs in the demo workspace, not the real-source inbox.
        if Path(name).suffix.lower() == ".json":
            try:
                value = json.loads(content.decode("utf-8-sig"))
            except (ValueError, UnicodeError, RecursionError):
                value = None  # Raw malformed sources may be needed to implement an adapter.
            if isinstance(value, dict) and value.get("synthetic") is True:
                raise DataError("FIXTURE_IN_REAL_INBOX", "Đây là dữ liệu mô phỏng. Dùng mục Thử dữ liệu mẫu để giữ riêng với hồ sơ thật.")
        digest = sha256(content)
        identifier = sha256(canonical_json([entity, period, source, digest]).encode())
        with self.lock:
            # Resolve while receipt directories are stable during concurrent intake.
            receipt_path = self.safe_path(f"receipts/{identifier}.json")
            if receipt_path.exists():
                receipt = self.get(identifier)
                if self.download(identifier)[1] != content:
                    raise DataError("INTAKE_CHECKSUM", "Bản lưu không khớp; cần kiểm tra kho hồ sơ.")
                return {**receipt, "duplicate": True}
            write_immutable(self.safe_path(f"raw/{digest}.bin"), content)
            receipt = {"id": identifier, "name": name, "source": source, "source_label": SOURCES[source], "period": period,
                       "entity": entity, "note": note, "original_relative_path": original_relative, "bytes": len(content), "sha256": digest,
                       "received_at": now_utc(), "state": "RECEIVED_WAITING_ADAPTER", "state_label": "Đã nhận · chờ bộ đọc",
                       "known_at": None, "known_at_basis": None, "normalized": False, "posted": False,
                       "client_modified_at": metadata.get("modified_at"), "format": "ktt-local-intake-v1"}
            write_immutable(receipt_path, canonical_json(receipt).encode("utf-8"))
            return {**receipt, "duplicate": False}

    def get(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{64}", identifier):
            raise DataError("RECEIPT_ID", "Mã hồ sơ không hợp lệ.")
        path = self.safe_path(f"receipts/{identifier}.json")
        if not path.is_file():
            raise DataError("RECEIPT_NOT_FOUND", "Không tìm thấy hồ sơ.")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        required_text = ("id", "format", "name", "source", "source_label", "period", "entity", "note", "original_relative_path", "sha256", "received_at", "state")
        if (not isinstance(receipt, dict) or any(not isinstance(receipt.get(k), str) for k in required_text)
                or receipt.get("id") != identifier or receipt.get("format") != "ktt-local-intake-v1"
                or not re.fullmatch(r"[0-9a-f]{64}", receipt.get("sha256", ""))
                or type(receipt.get("bytes")) is not int or not 0 < receipt["bytes"] <= MAX_FILE_SIZE
                or receipt.get("state") != "RECEIVED_WAITING_ADAPTER" or receipt.get("normalized") is not False or receipt.get("posted") is not False):
            raise DataError("INTAKE_RECEIPT_CHANGED", "Phiếu tiếp nhận không hợp lệ.")
        expected_id = sha256(canonical_json([receipt["entity"], receipt["period"], receipt["source"], receipt["sha256"]]).encode())
        if expected_id != identifier:
            raise DataError("INTAKE_RECEIPT_CHANGED", "Phiếu tiếp nhận không khớp phạm vi và nội dung.")
        return receipt

    def listing(self):
        with self.lock:
            rows, damaged = [], 0
            for path in self.safe_path("receipts").glob("*.json"):
                try:
                    rows.append(self.get(path.stem))
                except (DataError, OSError, ValueError):
                    damaged += 1
            rows.sort(key=lambda r: (r["received_at"], r["id"]), reverse=True)
            unique_blobs = {r["sha256"]: r["bytes"] for r in rows}
            return {"files": rows, "damaged_receipts": damaged, "total": len(rows), "total_bytes": sum(unique_blobs.values())}

    def download(self, identifier):
        receipt = self.get(identifier)
        content = self.safe_path(f"raw/{receipt['sha256']}.bin").read_bytes()
        if sha256(content) != receipt["sha256"] or len(content) != receipt["bytes"]:
            raise DataError("INTAKE_CHECKSUM", "Tệp lưu trên máy không khớp checksum; chưa cho tải bản này.")
        return receipt, content
