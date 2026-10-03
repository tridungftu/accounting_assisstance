from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .primitives import DataError, date_iso, sha256, text_id


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
        except (KeyError, TypeError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise DataError("INVALID_CONFIG", "Cấu hình TOML thiếu trường hoặc sai cấu trúc.") from exc
        return cls(entity, directory.resolve(), "VND", 0, raw, sha256(raw), environment, export_enabled, import_enabled, statuses, candidate_limit,
                   tax_id, float(quarantine_ratio), parsed_natures, include_non_taxable, dict(statuses_map), extend_journal_coverage,
                   catalog_valid_from, vat_threshold, approval_actor, entity_name)
