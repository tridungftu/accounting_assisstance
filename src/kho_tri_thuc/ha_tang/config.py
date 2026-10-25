from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .primitives import DataError, date_iso, sha256, text_id


_THD_CHUOI = ("goc_bo_tai", "node_exe", "phien_ban_bo_tai", "thu_muc_tai", "thu_muc_trinh_duyet", "thu_muc_profile", "thu_muc_dieu_phoi")
_THD_KHOA = frozenset(_THD_CHUOI) | {"node_sha256", "cong", "tep_pin", "goc_hoi_cuu_tin_cay"}
_RE_HEX64 = re.compile(r"[0-9a-f]{64}")


def doc_tai_hoa_don(v) -> dict:
    """[tai_hoa_don] (M2-00E): chỉ kiểm KIỂU/HÌNH DẠNG từng giá trị; đường dẫn tồn tại, hash khớp, gốc tách biệt do `CauHinhTaiHoaDon` kiểm lúc dựng.

    Vắng cả mục → Config.tai_hoa_don = None (tính năng "chưa cấu hình"). Mục có nhưng thiếu khóa vẫn đọc được: giao diện báo thiếu khóa nào,
    không làm hỏng việc mở phần mềm. Khóa lạ bị từ chối để lỗi gõ sai không thành cấu hình im lặng. Không mật khẩu/tài khoản cổng thuế ở đây.
    """
    if not isinstance(v, dict) or not set(v) <= _THD_KHOA:
        raise DataError("INVALID_TAI_HOA_DON", "[tai_hoa_don] phải là bảng và chỉ chứa các khóa đã định nghĩa.")
    out: dict = {}
    for k in _THD_CHUOI:
        if k in v:
            if not isinstance(v[k], str) or not v[k].strip() or len(v[k]) > 1024 or "\x00" in v[k]:
                raise DataError("INVALID_TAI_HOA_DON", f"[tai_hoa_don].{k} phải là chuỗi không rỗng.")
            out[k] = v[k]
    if "node_sha256" in v:
        if not isinstance(v["node_sha256"], str) or not _RE_HEX64.fullmatch(v["node_sha256"]):
            raise DataError("INVALID_TAI_HOA_DON", "[tai_hoa_don].node_sha256 phải là 64 ký tự hex thường.")
        out["node_sha256"] = v["node_sha256"]
    if "cong" in v:
        if type(v["cong"]) is not int or not (v["cong"] == 0 or 1024 <= v["cong"] <= 65535):
            raise DataError("INVALID_TAI_HOA_DON", "[tai_hoa_don].cong phải là 0 (hệ điều hành cấp) hoặc 1024–65535.")
        out["cong"] = v["cong"]
    if "tep_pin" in v:
        pin = v["tep_pin"]
        if not isinstance(pin, dict) or not pin or len(pin) > 32 or any(
                not isinstance(k, str) or not 0 < len(k) <= 200 or not isinstance(h, str) or not _RE_HEX64.fullmatch(h) for k, h in pin.items()):
            raise DataError("INVALID_TAI_HOA_DON", "[tai_hoa_don.tep_pin] phải là bảng đường dẫn tương đối → SHA-256 hex thường.")
        out["tep_pin"] = dict(pin)
    if "goc_hoi_cuu_tin_cay" in v:
        goc = v["goc_hoi_cuu_tin_cay"]
        if not isinstance(goc, list) or not 0 < len(goc) <= 8 or any(not isinstance(x, str) or not x.strip() or len(x) > 1024 for x in goc):
            raise DataError("INVALID_TAI_HOA_DON", "[tai_hoa_don].goc_hoi_cuu_tin_cay phải là danh sách 1–8 đường dẫn (gốc dữ liệu cũ được tin cậy cho manifest hồi cứu).")
        out["goc_hoi_cuu_tin_cay"] = list(goc)
    return out


@dataclass(frozen=True)
class Config:
    entity_id: str
    data_dir: Path
    currency: str
    scale: int
    source_bytes: bytes
    digest: str
    environment: str = "fixture"
    junsky_export_enabled: bool = False
    junsky_import_enabled: bool = False
    posted_journal_statuses: tuple[str, ...] = ("POSTED_SOURCE_FIXTURE",)
    review_candidate_limit: int = 10
    entity_tax_id: str | None = None
    quarantine_max_ratio: float = 0.2
    account_nature: dict[str, str] | None = None
    invoice_non_taxable_in_taxable_total: bool = False
    tax_gateway_statuses: dict[str, str] | None = None
    journal_history_extend_coverage: bool = True
    catalog_valid_from: str = "1900-01-01"
    vat_payment_evidence_threshold_minor: int = 0
    knowledge_approval_actor: str = "CFO_NTD"
    entity_name: str | None = None
    # V13 bước 5: [storage] engine = "sqlite" (mặc định, kho thật) | "postgres" (kho thử T8); dsn lấy từ .env theo dsn_key
    storage_engine: str = "sqlite"
    storage_dsn_key: str = "KHO_PG_DSN"
    storage_schema: str = "v12"
    # M2-00E: [tai_hoa_don] (bộ tải #7 sở hữu). None = vắng mục → tính năng hiện "chưa cấu hình"; dict = giá trị đã kiểm kiểu, chưa kiểm đường dẫn
    tai_hoa_don: dict | None = None

    @classmethod
    def load(cls, path: Path, data_dir: Path | None = None) -> Config:
        raw = path.read_bytes()
        try:
            values = tomllib.loads(raw.decode("utf-8-sig"))
            app, money = values["app"], values["money"]
            entity = text_id(app["entity_id"], "entity_id")
            environment = text_id(app["environment"], "environment")
            if environment not in {"fixture", "that"}:
                raise DataError("INVALID_ENVIRONMENT", "environment chỉ nhận fixture hoặc that.")
            if environment == "fixture" and not entity.endswith("_FIXTURE"):
                raise DataError("FIXTURE_ENTITY", "Môi trường fixture cần entity_id kết thúc _FIXTURE.")
            if environment == "that" and entity.endswith("_FIXTURE"):
                raise DataError("THAT_ENTITY", "Môi trường that không dùng entity fixture.")
            if money["currency"] != "VND" or type(money["scale"]) is not int or money["scale"] != 0:
                raise DataError("UNAPPROVED_CURRENCY", "Cấu hình fixture hiện chỉ nhận VND, scale 0.")
            directory = data_dir if data_dir is not None else path.parent / text_id(app["data_dir"], "data_dir")
            operation = values.get("operation", {})
            export_enabled = operation.get("junsky_export_enabled", False)
            import_enabled = operation.get("junsky_import_enabled", False)
            if type(export_enabled) is not bool or type(import_enabled) is not bool:
                raise DataError("INVALID_OPERATION_CONFIG", "Cờ Junsky phải là true/false.")
            if environment == "that" and (export_enabled or import_enabled):
                raise DataError("JUNSKY_OPERATION_BLOCKED", "Môi trường that chưa được phép bật xuất hoặc nhập Junsky.")
            statuses = operation.get("posted_journal_statuses", ["POSTED_SOURCE_FIXTURE"] if environment == "fixture" else ["POSTED"])
            if not isinstance(statuses, list) or not statuses or any(not isinstance(value, str) for value in statuses):
                raise DataError("INVALID_POSTING_STATUS", "posted_journal_statuses cần là danh sách trạng thái không rỗng.")
            statuses = tuple(text_id(value, "posted_journal_status") for value in statuses)
            candidate_limit = operation.get("review_candidate_limit", 10)
            if type(candidate_limit) is not int or not 1 <= candidate_limit <= 100:
                raise DataError("INVALID_REVIEW_LIMIT", "review_candidate_limit phải là số nguyên 1–100.")
            quarantine_ratio = operation.get("quarantine_max_ratio", 0.2)
            if type(quarantine_ratio) not in {int, float} or isinstance(quarantine_ratio, bool) or not 0 <= float(quarantine_ratio) <= 1:
                raise DataError("INVALID_QUARANTINE_RATIO", "quarantine_max_ratio phải nằm trong khoảng 0–1.")
            catalog_valid_from = date_iso(operation.get("catalog_valid_from", "1900-01-01"))
            vat_threshold = operation.get("vat_payment_evidence_threshold_minor", 0)
            if type(vat_threshold) is not int or vat_threshold < 0:
                raise DataError("INVALID_VAT_THRESHOLD", "vat_payment_evidence_threshold_minor phải là số nguyên không âm.")
            approval_actor = text_id(operation.get("knowledge_approval_actor", "CFO_NTD"), "knowledge_approval_actor")
            entity_data = values.get("entity", {})
            tax_id = entity_data.get("tax_id")
            if tax_id is not None:
                tax_id = text_id(tax_id, "entity.tax_id")
            entity_name = entity_data.get("name")
            if entity_name is not None:
                entity_name = text_id(entity_name, "entity.name")
            source_data = values.get("source", {})
            include_non_taxable = source_data.get("invoice_non_taxable_in_taxable_total", False)
            if type(include_non_taxable) is not bool:
                raise DataError("INVALID_INVOICE_TOTAL_CONFIG", "invoice_non_taxable_in_taxable_total phải là true/false.")
            extend_journal_coverage = source_data.get("journal_history_extend_coverage", True)
            if type(extend_journal_coverage) is not bool:
                raise DataError("INVALID_JOURNAL_COVERAGE_CONFIG", "journal_history_extend_coverage phải là true/false.")
            natures = values.get("account_nature", {})
            if not isinstance(natures, dict):
                raise DataError("INVALID_ACCOUNT_NATURE", "[account_nature] phải là bảng mã tài khoản.")
            parsed_natures = {}
            for code, nature in natures.items():
                code, nature = text_id(code, "account_nature.code"), text_id(nature, "account_nature.value").upper()
                if nature not in {"DEBIT", "CREDIT"}:
                    raise DataError("INVALID_ACCOUNT_NATURE", "Tính chất tài khoản chỉ nhận DEBIT hoặc CREDIT.")
                parsed_natures[code] = nature
            statuses_map = source_data.get("tax_gateway_statuses", {})
            if not isinstance(statuses_map, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in statuses_map.items()):
                raise DataError("INVALID_TAX_GATEWAY_STATUS", "Ánh xạ trạng thái cổng thuế phải là object chuỗi.")
            storage = values.get("storage", {})
            if not isinstance(storage, dict):
                raise DataError("INVALID_STORAGE", "[storage] phải là bảng.")
            storage_engine = storage.get("engine", "sqlite")
            if storage_engine not in {"sqlite", "postgres"}:
                raise DataError("INVALID_STORAGE", "[storage].engine chỉ nhận sqlite hoặc postgres.")
            storage_dsn_key = text_id(storage.get("dsn_key", "KHO_PG_DSN"), "storage.dsn_key")
            storage_schema = storage.get("schema", "v12")
            if not isinstance(storage_schema, str) or not (storage_schema == "auto" or re.fullmatch(r"[a-z_][a-z0-9_]{0,40}", storage_schema)):
                raise DataError("INVALID_STORAGE", "[storage].schema phải là tên schema chữ thường (a-z, 0-9, _) hoặc \"auto\".")
            if storage_schema != "auto":
                from .ket_noi import kiem_ten_schema
                kiem_ten_schema(storage_schema)  # cấm trùng schema K2/hệ thống (review lần 2 #10)
            tai_hoa_don = doc_tai_hoa_don(values["tai_hoa_don"]) if "tai_hoa_don" in values else None
        except (KeyError, TypeError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise DataError("INVALID_CONFIG", "Cấu hình TOML thiếu trường hoặc sai cấu trúc.") from exc
        return cls(entity, directory.resolve(), "VND", 0, raw, sha256(raw), environment, export_enabled, import_enabled, statuses, candidate_limit,
                   tax_id, float(quarantine_ratio), parsed_natures, include_non_taxable, dict(statuses_map), extend_journal_coverage,
                   catalog_valid_from, vat_threshold, approval_actor, entity_name, storage_engine, storage_dsn_key, storage_schema, tai_hoa_don)
