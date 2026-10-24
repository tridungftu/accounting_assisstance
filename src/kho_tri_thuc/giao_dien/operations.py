"""Local operational facade used by the V8 browser UI.

The HTTP layer calls this facade only.  Each mutation delegates to the same
Store, reader, knowledge, session, review and shadow services as the CLI; no
browser route contains SQL or accounting rules.
"""
from __future__ import annotations

import json
import re
import threading
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from ..ha_tang.config import Config
from ..ha_tang.primitives import DataError, canonical_json, date_iso, instant_utc, normalize_text, now_utc, sha256, text_id
from ..ha_tang.store import Store, write_immutable
from ..nguon.that import SourceMetadata, ThatAdapter
from ..trang_thai.service import Sessions
from ..tri_thuc.human_workbook import HumanKnowledgeWorkbook
from ..tri_thuc.service import Knowledge
from ..xuat.service import ReviewExport
from ..xuat.shadow import ShadowJunskyExport
from .quick import QuickPosting

SOURCES = {"sao_ke", "hoa_don", "bang_ke", "base", "junsky"}
SOURCE_LABELS = {"sao_ke": "Sao kê", "hoa_don": "Hóa đơn XML", "bang_ke": "Bảng kê hóa đơn", "base": "Đề nghị Base", "junsky": "Danh mục, công nợ và sổ Junsky"}
DOCUMENT_KINDS = {"BANK": "sao_ke", "INVOICE": "hoa_don", "BASE": "base"}
SOURCE_DEFAULTS = {
    "junsky_catalog": r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\DANH MỤC",
    "junsky_dgblist": r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\dgbList.xlsx",
    "junsky_ledger": r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\Ngân Hàng\Sổ NKC có đối ưng.xlsx",
    "bank": r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\Ngân Hàng",
    "invoice": r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\Hóa đơn",
    "base": r"D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\Base",
}
SETTING_DEFAULTS = {
    # These local values are intentionally parameterized.  They are not an
    # assertion that any bank, counterparty, template or Junsky import has
    # been approved.
    "object_learning_from": "2026-07-01",
    "description_similarity_threshold": 0.8,
    "own_counterparty_codes": [],
    "company_names": [],
    "export_mode": "DOI_UNG",
    "bank_ids": {},
    "template_thu": "",
    "template_chi": "",
    # V10: "" = learn from the whole ledger up to each bank date; a date
    # (yyyy-mm-dd) limits learning, e.g. 2026-06-30 for an August replay.
    "learning_cutoff": "",
    # Accounts that need a counterparty before approval (prefix match).
    # Awaiting the CFO's confirmation of the list.
    "debt_accounts": ["131", "331", "141", "344", "1388", "3388"],
    # V11: scoring replay — rows are never marked "đã có trong Junsky" and the
    # matched voucher is hidden from the proposal; "So với Junsky" grades it.
    "scoring_mode": False,
    # V11: optional local AI (OpenAI-compatible endpoint on this machine only).
    "local_ai": {},
    # V11.2: trial kho whose Junsky ledger was cut at the learning date — the
    # full ledger workbook used only as the answer by "So với Junsky".
    "answer_ledger": "",
}


# Rules Anh decided in conversation with Claude, kept next to the config file.
CFO_RULES_FILE = "TRI-THUC-CFO.json"


class Operations:
    def __init__(self, config_path: Path, root: Path):
        self.config_path = Path(config_path).resolve()
        self.config = Config.load(self.config_path)
        if self.config.environment != "that":
            raise DataError("THAT_REQUIRED", "Giao diện vận hành chỉ mở bằng cau_hinh.that.toml.")
        self.root = Path(root).resolve()
        self.staging = self.root / "nguon-da-chon"
        self._mutation_lock = threading.RLock()
        self._jobs: dict[str, dict] = {}
        self._jobs_lock = threading.RLock()
        # Create/upgrade the explicitly configured that database before serving.
        with Store(self.config):
            pass
        self._sync_runtime_settings()
        self.bootstrap_job = None
        self.bootstrap_status: dict = {}
        if self.config.entity_id == "PLHN":
            # V9: the Junsky background is source data, not a human approval queue.
            self.bootstrap_job = self.start("nen-junsky", self.bootstrap)["job_id"]

    def bootstrap(self) -> dict:
        settings = self.source_settings()["paths"]
        root = Path(settings["junsky_catalog"]).parent
        catalog = Path(settings["junsky_catalog"])
        workbooks = root / "bo_quy_tac" / "ket_qua"
        now = now_utc(); today = now[:10]; result = {"junsky": "unchanged", "knowledge": 0, "partners": 0}
        journal_paths = (Path(settings["junsky_dgblist"]), Path(settings["junsky_ledger"]))
        signature = self._junsky_signature(catalog, journal_paths)
        signature_path = self.root / "junsky-source-signature.json"
        previous = signature_path.read_text(encoding="utf-8") if signature_path.is_file() else ""
        if catalog.is_dir():
            with self._mutation_lock, Store(self.config) as store:
                exists = store.conn.execute("SELECT 1 FROM attempts WHERE source='junsky_xuat' AND state='COMMITTED' LIMIT 1").fetchone()
                if not exists or previous != signature:
                    metadata = SourceMetadata(today, now, "Nền Junsky hệ thống", "1900-01-01", (date.fromisoformat(today) + timedelta(days=1)).isoformat(), now, "JUNSKY_AUTO", "PLHN_JUNSKY", "NEN_JUNSKY", True, True, self.config.catalog_valid_from)
                    report = store.ingest(catalog, ThatAdapter("junsky", catalog, metadata, journal_paths=journal_paths))
                    result["junsky"] = report["state"]
                    if report["state"] == "COMMITTED":
                        self._adopt_catalog(store, now)
                        signature_path.write_text(signature, encoding="utf-8")
        files = [workbooks / name for name in ("TU-DIEN-NHOM-NGHIEP-VU.xlsx", "BO-QUY-TAC.xlsx", "HOA-DON-CAY-PHAN-NHANH.xlsx")]
        files = [path for path in files if path.is_file()]
        if files:
            with self._mutation_lock, Store(self.config) as store:
                result["knowledge"] = HumanKnowledgeWorkbook(store).import_sources(files, "HE_THONG_JUNSKY", now, self.config.catalog_valid_from).get("pending", 0)
        partner_file = self.config_path.parent / "DANH MUC DOI TAC PLHN - BO SUNG STK VA DICH VU (nhap 24-09-2026).xlsx"
        if partner_file.is_file():
            with self._mutation_lock, Store(self.config) as store:
                result["partners"] = self._import_partner_directory(store, partner_file, now)
        cfo_file = self.config_path.parent / CFO_RULES_FILE
        if cfo_file.is_file():
            with self._mutation_lock, Store(self.config) as store:
                result["cfo_rules"] = self._import_cfo_rules(store, cfo_file, now)
        result["cash_accounts"] = self._apply_file_cash_accounts()
        missing = [label for label, path in (("Danh mục Junsky", catalog), ("Sổ Junsky", journal_paths[1]), ("Danh sách chứng từ công nợ", journal_paths[0])) if not path.exists()]
        self.bootstrap_status = {"finished_at": now_utc(), "result": result, "missing": missing}
        return result

    def _sync_runtime_settings(self) -> None:
        """Make settings written in source-settings.json effective for the engine."""
        try:
            current = self.source_settings()
            # V12: the invoice folder (paths.invoice) is read by quick posting.
            settings = {**current["settings"], "invoice_root": str(current["paths"].get("invoice") or "")}
            with self._mutation_lock, Store(self.config) as store:
                store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_runtime_settings',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (canonical_json(settings),))
                store.conn.commit()
        except (OSError, DataError, json.JSONDecodeError):
            pass

    def _apply_file_cash_accounts(self) -> int:
        """Apply ``settings.cash_accounts`` from source-settings.json as MANUAL mappings (V10 setup file)."""
        path = self.root / "source-settings.json"
        try:
            saved = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        except (OSError, UnicodeError, json.JSONDecodeError):
            return 0
        mappings = saved.get("settings", {}).get("cash_accounts") if isinstance(saved, dict) and isinstance(saved.get("settings"), dict) else None
        if not isinstance(mappings, list):
            return 0
        count = 0
        with self._mutation_lock, Store(self.config) as store:
            quick = QuickPosting(store)
            for mapping in mappings:
                if not isinstance(mapping, dict):
                    continue
                account = self._bank_account(mapping.get("bank_account"))
                existing = store.conn.execute("SELECT cash_account,source FROM cash_account_mappings WHERE bank_account=?", (account,)).fetchone()
                if existing and existing["source"] == "MANUAL":
                    continue
                try:
                    quick.set_cash_mapping(account, mapping.get("cash_account"), "CFO_NTD", "MANUAL", ["SOURCE_SETTINGS_FILE"])
                    count += 1
                except DataError:
                    continue
            store.conn.commit()
        return count

    @staticmethod
    def _junsky_signature(catalog: Path, journal_paths: tuple[Path, ...] = ()) -> str:
        roots = [catalog, *journal_paths, catalog.parent / "dgbList.xlsx", catalog.parent / "Sổ NKC có đối ưng.xlsx", catalog.parent / "Ngân Hàng" / "Sổ NKC có đối ưng.xlsx"]
        files = []
        for item in roots:
            if item.is_dir():
                files.extend(path for path in item.rglob("*.xlsx") if path.is_file())
            elif item.is_file():
                files.append(item)
        payload = {"reader_version": ThatAdapter.version,
                   "files": [{"path": str(path), "mtime_ns": path.stat().st_mtime_ns, "size": path.stat().st_size, "hash": sha256(path.read_bytes())} for path in sorted(set(files))]}
        return canonical_json(payload)

    def source_settings(self) -> dict:
        path = self.root / "source-settings.json"
        values, settings = dict(SOURCE_DEFAULTS), dict(SETTING_DEFAULTS)
        if path.is_file():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    # V9 stored a flat paths object.  Keep it readable while
                    # V9b writes an explicit {paths, settings} envelope.
                    saved_paths = saved.get("paths", saved)
                    saved_settings = saved.get("settings", {})
                    if isinstance(saved_paths, dict):
                        values.update({key: value for key, value in saved_paths.items() if key in values and isinstance(value, str)})
                    if isinstance(saved_settings, dict):
                        settings.update({key: value for key, value in saved_settings.items() if key in settings})
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass
        try:
            with Store(self.config) as store:
                row = store.conn.execute("SELECT value FROM workspace_meta WHERE key='v9b_runtime_settings'").fetchone()
                if row:
                    saved = json.loads(row[0])
                    if isinstance(saved, dict):
                        settings.update({key: value for key, value in saved.items() if key in settings})
                mappings = [dict(row) for row in store.conn.execute("SELECT bank_account,cash_account,source,evidence_json,updated_at FROM cash_account_mappings ORDER BY bank_account")]
        except (OSError, json.JSONDecodeError):
            mappings = []
        return {"paths": values, "settings": settings, "cash_accounts": mappings}

    def save_source_settings(self, values: dict) -> dict:
        if not isinstance(values, dict):
            raise DataError("SOURCE_SETTINGS", "Cấu hình nguồn không hợp lệ.")
        paths = values.get("paths", values)
        requested_settings = values.get("settings", {}) if "paths" in values else {}
        if not isinstance(paths, dict) or set(paths) != set(SOURCE_DEFAULTS):
            raise DataError("SOURCE_SETTINGS", "Cần khai đủ sáu đường dẫn nguồn dữ liệu.")
        clean = {}
        for key, value in paths.items():
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                raise DataError("SOURCE_SETTINGS", "Đường dẫn nguồn không hợp lệ.")
            clean[key] = str(Path(value).expanduser())
        if not isinstance(requested_settings, dict):
            raise DataError("SOURCE_SETTINGS", "Thiết lập vận hành không hợp lệ.")
        current = self.source_settings()["settings"]
        settings = {**current, **{key: value for key, value in requested_settings.items() if key in SETTING_DEFAULTS}}
        try:
            date_iso(settings["object_learning_from"])
            threshold = float(settings["description_similarity_threshold"])
        except (TypeError, ValueError, DataError) as exc:
            raise DataError("SOURCE_SETTINGS", "Ngày học đối tượng hoặc ngưỡng giống diễn giải không hợp lệ.") from exc
        if not 0.5 <= threshold <= 1:
            raise DataError("SOURCE_SETTINGS", "Ngưỡng giống diễn giải phải trong khoảng 0,50–1,00.")
        settings["description_similarity_threshold"] = threshold
        for key in ("own_counterparty_codes", "company_names"):
            if not isinstance(settings[key], list) or not all(isinstance(value, str) and value.strip() for value in settings[key]):
                raise DataError("SOURCE_SETTINGS", f"{key} phải là danh sách mã/tên hợp lệ.")
            settings[key] = sorted(set(value.strip() for value in settings[key]))
        if settings["export_mode"] not in {"DOI_UNG", "DAY_DU"}:
            raise DataError("SOURCE_SETTINGS", "Chế độ xuất chỉ nhận DOI_UNG hoặc DAY_DU.")
        if not isinstance(settings["bank_ids"], dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in settings["bank_ids"].items()):
            raise DataError("SOURCE_SETTINGS", "Ánh xạ BankID không hợp lệ.")
        normalized_bank_ids = {}
        for account, bank_id in settings["bank_ids"].items():
            normalized_account = self._bank_account(account)
            normalized_bank_id = bank_id.strip()
            if not normalized_account or not normalized_bank_id:
                raise DataError("SOURCE_SETTINGS", "Ánh xạ BankID cần STK nguồn và BankID không rỗng.")
            previous = normalized_bank_ids.get(normalized_account)
            if previous is not None and previous != normalized_bank_id:
                raise DataError("SOURCE_SETTINGS", "Một STK nguồn chỉ được ánh xạ đến một BankID.")
            normalized_bank_ids[normalized_account] = normalized_bank_id
        settings["bank_ids"] = dict(sorted(normalized_bank_ids.items()))
        cutoff_value = settings.get("learning_cutoff") or ""
        if cutoff_value:
            try:
                settings["learning_cutoff"] = date_iso(str(cutoff_value)[:10])
            except DataError as exc:
                raise DataError("SOURCE_SETTINGS", "Mốc học phải là ngày hợp lệ.") from exc
        else:
            settings["learning_cutoff"] = ""
        settings["scoring_mode"] = bool(settings.get("scoring_mode"))
        answer = settings.get("answer_ledger") or ""
        if not isinstance(answer, str) or len(answer) > 500:
            raise DataError("SOURCE_SETTINGS", "Đường dẫn sổ Junsky đầy đủ (đáp án chấm điểm) không hợp lệ.")
        settings["answer_ledger"] = answer.strip()
        local_ai = settings.get("local_ai")
        if local_ai is None:
            local_ai = {}
        if not isinstance(local_ai, dict):
            raise DataError("SOURCE_SETTINGS", "Thiết lập AI cục bộ phải là một nhóm khóa/giá trị.")
        from ..tri_thuc.ai_cuc_bo import local_ai_settings
        settings["local_ai"] = local_ai_settings({"local_ai": local_ai})
        debt = settings.get("debt_accounts")
        if not isinstance(debt, list) or not all(isinstance(value, str) and re.fullmatch(r"\d{3,10}", value.strip()) for value in debt):
            raise DataError("SOURCE_SETTINGS", "Danh sách tài khoản công nợ phải là các số tài khoản.")
        settings["debt_accounts"] = sorted(set(value.strip() for value in debt))
        for key in ("template_thu", "template_chi"):
            if not isinstance(settings[key], str) or len(settings[key]) > 500:
                raise DataError("SOURCE_SETTINGS", "Đường dẫn mẫu Junsky không hợp lệ.")
            settings[key] = settings[key].strip()
        mappings = requested_settings.get("cash_accounts")
        if mappings is not None and (not isinstance(mappings, list) or not all(isinstance(item, dict) for item in mappings)):
            raise DataError("SOURCE_SETTINGS", "Ánh xạ TK tiền không hợp lệ.")
        target = self.root / "source-settings.json"; target.parent.mkdir(parents=True, exist_ok=True)
        file_settings = dict(settings)
        try:
            previous = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
            if isinstance(previous, dict) and isinstance(previous.get("settings"), dict) and isinstance(previous["settings"].get("cash_accounts"), list):
                file_settings["cash_accounts"] = previous["settings"]["cash_accounts"]
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
        if mappings is not None:
            file_settings["cash_accounts"] = [{"bank_account": self._bank_account(item.get("bank_account")), "cash_account": str(item.get("cash_account") or "").strip()} for item in mappings]
        target.write_text(canonical_json({"paths": clean, "settings": file_settings}), encoding="utf-8")
        # V12: quick posting reads the invoice folder from the runtime settings.
        runtime = {**settings, "invoice_root": str(clean.get("invoice") or "")}
        with self._mutation_lock, Store(self.config) as store:
            store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_runtime_settings',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (canonical_json(runtime),))
            if mappings is not None:
                store.conn.execute("DELETE FROM cash_account_mappings WHERE source='MANUAL'")
                quick = QuickPosting(store)
                for mapping in mappings:
                    quick.set_cash_mapping(mapping.get("bank_account"), mapping.get("cash_account"), "CFO_NTD", "MANUAL", mapping.get("evidence", []))
            store.conn.commit()
        return self.source_settings()

    @staticmethod
    def _bank_account(value: object) -> str:
        """Normalize a standalone STK, otherwise retain its longest numeric run."""
        raw = str(value or "").strip()
        if re.fullmatch(r"[\d\s._()\-]+", raw):
            compact = "".join(re.findall(r"\d+", raw))
            return compact if len(compact) >= 6 else ""
        choices = re.findall(r"\d+", raw)
        value = max(choices, key=len, default="")
        return value if len(value) >= 6 else ""

    @staticmethod
    def _cell(row: dict, name: str) -> str:
        return str(row.get(name) or "").strip()

    @staticmethod
    def _read_cfo_rules(path: Path) -> list[dict]:
        try:
            document_value = json.loads(path.read_text(encoding="utf-8"))
            rules = document_value.get("rules") if isinstance(document_value, dict) else None
            if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
                raise ValueError("rules")
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise DataError("CFO_RULES", f"Tệp {path.name} không đọc được.") from exc
        return rules

    def _cfo_policy_payload(self, rule: dict, path: Path) -> tuple[str, dict]:
        code, regex = str(rule.get("ma") or "").strip(), str(rule.get("mau_dien_giai") or "")
        direction = {"CHI": "OUT", "THU": "IN"}.get(str(rule.get("chieu") or "").upper())
        decided = str(rule.get("ngay_duyet") or "")[:10]
        if not code or not regex or not direction or not decided:
            raise DataError("CFO_RULES", f"Quy tắc {code or '?'} trong {path.name} thiếu mã, chiều, mẫu diễn giải hoặc ngày duyệt.")
        fields = {}
        for source_key, field in (("no", "debit_account"), ("co", "credit_account"), ("doi_tuong", "counterparty"), ("du_an", "project"), ("khoan_muc", "expense")):
            if rule.get(source_key):
                fields[field] = str(rule[source_key]).strip()
        payload = {"contract_version": 2, "template_id": code, "partition": str(rule.get("phan_vung") or f"{self.config.entity_id}:PAYMENT"),
                   "direction": direction, "tier": 1, "order": 1, "needs_open_item": False, "required_fields": [],
                   "trigger": {"mode": "REGEX", "regex": regex}, "fields": fields, "source_status": "CFO_DUYET",
                   "source_row": {"ma_quy_tac": f"{code} (Anh duyệt {decided[8:10]}/{decided[5:7]}/{decided[:4]})", "ghi_chu": str(rule.get("mo_ta") or ""),
                                  "nguon": str(rule.get("nguon") or "")}}
        prefix = str(rule.get("doi_tuong_bat_dau") or "").strip()
        if prefix:
            payload["confirms_counterparty_prefix"] = prefix
        return decided, payload

    @staticmethod
    def _knowledge_state(store: Store, identifier: str) -> str:
        actions = {row[0] for row in store.conn.execute("SELECT action FROM knowledge_events WHERE version_id=?", (identifier,))}
        return "REVOKED" if "REVOKE" in actions else "APPROVED" if "APPROVE" in actions else "PENDING"

    def _import_cfo_rules(self, store: Store, path: Path, at: str) -> int:
        """Rules Anh decided in conversation (file next to the config), approved in his name.

        * ``loai`` QUY_TAC (default): a POLICY knowledge row (contract v2,
          regex trigger) with a fixed decision date.  An unchanged rule stages
          nothing; a changed one supersedes its previous version; ``"tat": true``
          revokes it, and switching it back on stages a fresh version.
        * ``loai`` LUU_Y: a caution shown on the screen, never a posting.
        A malformed file is reported, never half-applied.
        """
        rules = self._read_cfo_rules(path)
        actor = self.config.knowledge_approval_actor or "CFO_NTD"
        knowledge, applied, notes = Knowledge(store), 0, []
        for rule in rules:
            code = str(rule.get("ma") or "").strip()
            off = rule.get("tat") is True
            if str(rule.get("loai") or "QUY_TAC").upper() == "LUU_Y":
                if code and not off and rule.get("lich_su_tk") and rule.get("de_xuat_tk") and rule.get("noi_dung"):
                    notes.append({"ma": code, "lich_su_tk": str(rule["lich_su_tk"]).strip(), "de_xuat_tk": str(rule["de_xuat_tk"]).strip(),
                                  "noi_dung": str(rule["noi_dung"]).strip()})
                    applied += 1
                continue
            decided, payload = self._cfo_policy_payload(rule, path)
            key = "CFO:" + code
            prior = store.conn.execute("SELECT id,payload_json FROM knowledge_versions WHERE category='POLICY' AND logical_key=? ORDER BY revision DESC LIMIT 1", (key,)).fetchone()
            state = self._knowledge_state(store, prior["id"]) if prior is not None else None
            if off:
                if state == "APPROVED":
                    knowledge.revoke(prior["id"], actor, at, "Anh tắt quy tắc " + code)
                continue
            if prior is not None and state == "APPROVED" and json.loads(prior["payload_json"]) == payload:
                applied += 1
                continue  # unchanged and in use: nothing new to stage
            item = {"category": "POLICY", "logical_key": key, "valid_from": str(rule.get("hieu_luc_tu") or "2024-01-01"), "valid_to": None,
                    # A rule switched back on is known again from now on.
                    "known_at": at if state == "REVOKED" else decided + "T00:00:00Z", "payload": payload,
                    "evidence": ["CFO_RULES_FILE:" + path.name, "CFO_DECISION:" + decided]}
            if prior is not None:
                item["supersedes_id"] = prior["id"]
            identifier = knowledge.stage_many([item], actor, at)[0]
            knowledge.approve(identifier, actor, at)
            applied += 1
        store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('cfo_notes',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (canonical_json(notes),))
        store.conn.commit()
        return applied

    def cfo_rules(self) -> dict:
        """Tri thức CFO screen: the rules, whether each is in use, and how it fared."""
        path = self.config_path.parent / CFO_RULES_FILE
        if not path.is_file():
            return {"file": CFO_RULES_FILE, "rules": [], "missing": True}
        rules = self._read_cfo_rules(path)
        with Store(self.config) as store:
            versions, states = {}, {}
            for row in store.conn.execute("SELECT id,logical_key FROM knowledge_versions WHERE category='POLICY' AND logical_key LIKE 'CFO:%' ORDER BY revision"):
                versions.setdefault(row["logical_key"][4:], set()).add(row["id"])
                states[row["logical_key"][4:]] = self._knowledge_state(store, row["id"])
            stats: dict[str, dict[str, Counter]] = {}
            codes = [str(rule.get("ma") or "") for rule in rules]
            for row in store.conn.execute("SELECT state,proposal_json,decision_json FROM quick_items"):
                try:
                    payload = json.loads(row["proposal_json"])
                except (TypeError, json.JSONDecodeError):
                    continue
                why = str(payload.get("why") or "")
                used = [code for code in codes if code and ((payload.get("policy") or {}).get("template_id") == code
                                                           or payload.get("template_id") in versions.get(code, set())
                                                           or f"— {code})" in why)]
                if not used:
                    continue
                month = str(payload.get("business_date") or "")[:7]
                offset = "credit_account" if int(payload.get("amount_minor", 0) or 0) > 0 else "debit_account"
                if row["state"] in ("APPROVE", "EXPORTED"):
                    decided = json.loads(row["decision_json"]) if row["decision_json"] else {}
                    outcome = "giu_nguyen" if decided.get(offset, (payload.get("fields") or {}).get(offset)) == (payload.get("fields") or {}).get(offset) else "sua"
                elif row["state"] == "SKIP":
                    outcome = "bo_qua"
                else:
                    outcome = "cho"
                for code in used:
                    stats.setdefault(code, {}).setdefault(month, Counter())[outcome] += 1
                    stats[code][month]["ap_dung"] += 1
        result = []
        for rule in rules:
            code = str(rule.get("ma") or "")
            note = str(rule.get("loai") or "QUY_TAC").upper() == "LUU_Y"
            active = rule.get("tat") is not True and (note or states.get(code) == "APPROVED")
            months = [{"thang": month, **dict(counter)} for month, counter in sorted((stats.get(code) or {}).items(), reverse=True)]
            result.append({"ma": code, "loai": "LUU_Y" if note else "QUY_TAC", "dang_dung": active, "ngay_duyet": rule.get("ngay_duyet"),
                           "dieu_kien": rule.get("dieu_kien") or rule.get("mo_ta") or "", "ket_qua": rule.get("ket_qua") or rule.get("noi_dung") or "",
                           "mo_ta": rule.get("mo_ta") or "", "nguon": rule.get("nguon") or "", "thang": months})
        return {"file": CFO_RULES_FILE, "rules": result}

    def toggle_cfo_rule(self, code: object, enabled: object) -> dict:
        """Switch one rule on/off: the file records it, the kho follows at once."""
        code = text_id(code, "ma")
        if not isinstance(enabled, bool):
            raise DataError("CFO_RULES", "Trạng thái bật/tắt không hợp lệ.")
        path = self.config_path.parent / CFO_RULES_FILE
        if not path.is_file():
            raise DataError("CFO_RULES", f"Không thấy tệp {CFO_RULES_FILE}.")
        with self._mutation_lock:
            document_value = json.loads(path.read_text(encoding="utf-8"))
            found = [rule for rule in document_value.get("rules", []) if isinstance(rule, dict) and str(rule.get("ma") or "") == code]
            if not found:
                raise DataError("CFO_RULES", f"Không có quy tắc {code}.")
            for rule in found:
                if enabled:
                    rule.pop("tat", None)
                else:
                    rule["tat"] = True
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(document_value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            temporary.replace(path)
            with Store(self.config) as store:
                self._import_cfo_rules(store, path, now_utc())
        return self.cfo_rules()

    def _import_partner_directory(self, store: Store, path: Path, at: str) -> int:
        """Load the partner workbook as evidence, without creating catalog codes."""
        from openpyxl import load_workbook
        digest = sha256(path.read_bytes())
        previous = store.conn.execute("SELECT value FROM workspace_meta WHERE key='v9b_partner_directory_hash'").fetchone()
        if previous and previous[0] == digest:
            return 0
        workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
        try:
            sheets: dict[str, list[dict]] = {}
            for name in ("DOI TAC", "STK CHUA GAN", "TK NOI BO"):
                if name not in workbook.sheetnames:
                    continue
                iterator = workbook[name].iter_rows(values_only=True)
                headers = [str(value or "").strip() for value in next(iterator, ())]
                sheets[name] = [{headers[index]: value for index, value in enumerate(values) if index < len(headers)} for values in iterator]
        finally:
            workbook.close()
        parties = {row[0] for row in store.conn.execute("SELECT json_extract(payload_json,'$.code') FROM knowledge_versions WHERE category='CATALOG' AND json_extract(payload_json,'$.kind')='COUNTERPARTY'")}
        items = []
        def append(account: str, party: str, verified: bool, evidence: str, reliability: str, source_status: str):
            if not account or not party or party not in parties:
                return
            payload = {"kind": "IDENTIFIER", "code": "BANK_ACCOUNT:" + account, "identifier_type": "BANK_ACCOUNT", "value": account,
                       "counterparty": party, "verified": verified, "source_status": source_status, "reliability": reliability}
            items.append({"category": "CATALOG", "logical_key": "BANK_ACCOUNT:" + account + ":" + party, "valid_from": self.config.catalog_valid_from,
                          "valid_to": None, "known_at": at, "payload": payload, "evidence": [evidence]})
        for row in sheets.get("DOI TAC", []):
            party = self._cell(row, "Mã đối tượng")
            answer = self._cell(row, "Anh xác nhận (Đúng/Sửa/Bỏ)").casefold()
            if answer in {"bỏ", "sửa"}:
                continue
            raw_reliability = self._cell(row, "Độ tin cậy STK (1/2/3)").casefold()
            reliability = {"1": "HIGH", "2": "MEDIUM", "3": "LOW", "cao": "HIGH", "trung bình": "MEDIUM", "trung binh": "MEDIUM", "thấp": "LOW", "thap": "LOW"}.get(raw_reliability, "LOW")
            source_status = "DIRECTORY_CORRECT" if answer == "đúng" else "DIRECTORY_" + reliability
            for name in ("STK 1", "STK 2", "STK 3", "STK khác"):
                append(self._bank_account(row.get(name)), party, answer == "đúng", "DOI_TAC:" + name, reliability, source_status)
        for row in sheets.get("STK CHUA GAN", []):
            append(self._bank_account(row.get("STK")), self._cell(row, "Anh điền mã đối tượng"), True, "STK_CHUA_GAN", "HIGH", "DIRECTORY_ENTERED")
        if not items:
            store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_partner_directory_hash',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (digest,))
            return 0
        knowledge = Knowledge(store)
        identifiers = knowledge.stage_many(items, "HE_THONG_JUNSKY", at)
        for identifier, item in zip(identifiers, items):
            if item["payload"]["verified"]:
                knowledge.approve(identifier, "HE_THONG_JUNSKY", at)
        store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_partner_directory_hash',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (digest,))
        return len(identifiers)

    def _adopt_catalog(self, store: Store, at: str) -> None:
        """Junsky catalogues are authoritative in quick mode and get a system audit actor."""
        items = []
        for row in store.conn.execute("SELECT id,kind,natural_key FROM documents WHERE kind IN ('COUNTERPARTY','ACCOUNT','PROJECT','EXPENSE','COST_CENTER')"):
            core = __import__('kho_tri_thuc.ha_tang.runtime', fromlist=['document']).document(store, row["id"], at)
            code, name = core.get("code"), core.get("name")
            if isinstance(code, str) and isinstance(name, str) and code and name:
                payload = {"kind":row["kind"],"code":code,"name":name}
                if row["kind"] == "COUNTERPARTY" and core.get("tax_id"):
                    payload["tax_id"] = core["tax_id"]
                items.append({"category":"CATALOG", "logical_key":row["kind"] + ":" + code, "valid_from":self.config.catalog_valid_from, "valid_to":None, "known_at":at, "payload":payload, "evidence":["JUNSKY_CATALOG"]})
                if row["kind"] == "COUNTERPARTY" and core.get("tax_id"):
                    tax_id = str(core["tax_id"]).strip()
                    if tax_id:
                        items.append({"category": "CATALOG", "logical_key": "TAX_ID:" + tax_id + ":" + code,
                                      "valid_from": self.config.catalog_valid_from, "valid_to": None, "known_at": at,
                                      "payload": {"kind": "IDENTIFIER", "code": "TAX_ID:" + tax_id + ":" + code,
                                                  "identifier_type": "TAX_ID", "value": tax_id, "counterparty": code,
                                                  "verified": True, "source_status": "JUNSKY_CATALOG", "reliability": "HIGH"},
                                      "evidence": ["JUNSKY_CATALOG"]})
        # A reload ("Nạp lại" with a newer Junsky export) must not stage a
        # second, overlapping version of every catalogue row: an unchanged row
        # is kept, a changed one supersedes the current version.
        latest = {}
        for row in store.conn.execute("SELECT id,logical_key,payload_json,valid_from,valid_to FROM knowledge_versions WHERE category='CATALOG' ORDER BY logical_key,revision"):
            latest[row["logical_key"]] = row
        approved = {row[0] for row in store.conn.execute("""SELECT version_id FROM knowledge_events e WHERE action='APPROVE'
                                                            AND NOT EXISTS (SELECT 1 FROM knowledge_events r WHERE r.version_id=e.version_id AND r.action='REVOKE')""")}
        fresh = []
        for item in items:
            prior = latest.get(item["logical_key"])
            if prior is not None:
                try:
                    same = json.loads(prior["payload_json"]) == item["payload"] and prior["valid_from"] == item["valid_from"] and prior["valid_to"] is None
                except (TypeError, json.JSONDecodeError):
                    same = False
                if same and prior["id"] in approved:
                    continue
                item["supersedes_id"] = prior["id"]
            fresh.append(item)
        if fresh:
            knowledge = Knowledge(store)
            identifiers = knowledge.stage_many(fresh, "HE_THONG_JUNSKY", at)
            for identifier in identifiers: knowledge.approve(identifier, "HE_THONG_JUNSKY", at)
        self._derive_own_counterparty_codes(store)

    def _derive_own_counterparty_codes(self, store: Store) -> list[str]:
        """Derive entity codes from the current local catalogue, never from a rule."""
        names = set()
        try:
            saved = json.loads((self.root / "source-settings.json").read_text(encoding="utf-8")) if (self.root / "source-settings.json").is_file() else {}
            configured = saved.get("settings", {}).get("company_names", []) if isinstance(saved, dict) else []
            names.update(normalize_text(value) for value in configured)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        if self.config.entity_name:
            names.add(normalize_text(self.config.entity_name))
        result = set()
        for row in store.conn.execute("SELECT core_json FROM documents WHERE kind='COUNTERPARTY'"):
            try:
                core = json.loads(row[0])
            except json.JSONDecodeError:
                continue
            if (self.config.entity_tax_id and core.get("tax_id") == self.config.entity_tax_id) or (names and normalize_text(core.get("name", "")) in names):
                code = str(core.get("code") or "").strip()
                if code:
                    result.add(code)
        store.conn.execute("INSERT INTO workspace_meta(key,value) VALUES ('v9b_derived_own_codes',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (canonical_json(sorted(result)),))
        return sorted(result)

    @staticmethod
    def _quick_source(name: str) -> str:
        lower = name.casefold()
        if lower.endswith(".xml") or lower.endswith(".zip"):
            return "hoa_don"
        if "sao ke" in lower or "sao kê" in lower or lower.endswith(".xls"):
            return "sao_ke"
        if "bang ke" in lower or "bảng kê" in lower:
            return "bang_ke"
        return "hoa_don" if "hoa don" in lower or "hóa đơn" in lower else "sao_ke"

    def quick_upload(self, raw: bytes, name: str, relative_path: str = "", progress=None) -> dict:
        """Receive and propose immediately; it never opens a V8 session."""
        name = self._safe_name(name)
        source = self._quick_source(name)
        digest = sha256(raw) if raw else ""
        self._wait_bootstrap()
        with Store(self.config) as store:
            # The same file dropped again reopens its earlier run (and its
            # decisions) instead of producing an empty duplicate run.
            reused = QuickPosting(store).run_for_hash(digest) if digest else None
            if reused:
                return {"state": "READY", "source": source, "reused": True, **QuickPosting(store).rows(reused)}
            if not store.conn.execute("SELECT 1 FROM documents WHERE kind='COUNTERPARTY' LIMIT 1").fetchone():
                raise DataError("NO_CATALOG", "Chưa có danh mục đối tượng từ Junsky nên chưa đề xuất được. Việc cần làm: sang màn hình Nguồn dữ liệu, kiểm tra thư mục DANH MỤC rồi bấm Nạp lại.")
        receipt = self.receive_source(raw, {"source": source, "name": name, "relative_path": relative_path or name})
        today = now_utc()[:10]
        coverage_to = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
        request = {"source": source, "batch_id": receipt["batch_id"], "as_of": today,
                   "coverage_from": "1900-01-01", "coverage_to_exclusive": coverage_to,
                   "known_at_basis": "Tệp Anh thả vào Định khoản", "posting_evidence_complete": False,
                   "scope_open_items_complete": False}
        report = self.ingest(request)
        if report["state"] != "COMMITTED":
            return {"state": "REJECTED", "message": "Chưa đọc được tệp này. Kiểm tra đúng file sao kê Excel của ngân hàng rồi thả lại.", "technical": report}
        if not report.get("inserted_documents"):
            raise DataError("NO_NEW_RECORDS", "Các giao dịch trong tệp này đã có ở lần làm trước. Mở lại ở mục “Đã làm gần đây”.")
        bank = (report.get("controls") or {}).get("bank") or {}
        opening, closing = bank.get("opening_minor"), bank.get("closing_minor")
        info = {"name": name, "records": report.get("inserted_documents", 0), "period": bank.get("period") or "",
                "opening_minor": opening, "closing_minor": closing, "credit_minor": bank.get("credit_minor"), "debit_minor": bank.get("debit_minor"),
                "balance_ok": (opening + bank.get("credit_minor", 0) - bank.get("debit_minor", 0) == closing) if opening is not None and closing is not None else None,
                "warnings": [item["code"] for item in self._summary(report).get("issue_counts", []) if item.get("severity") == "WARNING"]}
        with self._mutation_lock, Store(self.config) as store:
            quick = QuickPosting(store).propose(report["attempt_id"], source, "NGUOI_VAN_HANH", source_name=name, source_hash=digest, source_info=info, progress=progress)
        return {"state": "READY", "source": source, "report": self._summary(report), **quick}

    def _wait_bootstrap(self, limit_seconds: int = 600) -> None:
        """A file dropped while Junsky data is still loading waits for it."""
        import time
        identifier = getattr(self, "bootstrap_job", None)
        deadline = time.monotonic() + limit_seconds
        while identifier and time.monotonic() < deadline:
            with self._jobs_lock:
                state = self._jobs.get(identifier, {}).get("state")
            if state != "RUNNING":
                return
            time.sleep(0.5)

    def invoice_months(self) -> dict:
        """V12: month folders of the invoice download tool, newest first."""
        from ..nguon.that import invoice_months
        root = Path(self.source_settings()["paths"].get("invoice") or "")
        settings = self.source_settings()["settings"]
        cutoff = str(settings.get("learning_cutoff") or "")
        months = invoice_months(root) if str(root) else []
        for item in months:
            item["learning"] = bool(cutoff) and item["month"] <= cutoff[:7]
        return {"root": str(root), "exists": root.is_dir(), "months": months, "learning_cutoff": cutoff}

    def quick_invoice_month(self, month: str, progress=None) -> dict:
        """V12: every XML of one month (mua vào + bán ra) as one run."""
        import io
        import zipfile
        from ..nguon.that import invoice_month_files
        root = Path(self.source_settings()["paths"].get("invoice") or "")
        files = invoice_month_files(root, str(month or ""))
        if not files:
            raise DataError("INVOICE_MONTH_EMPTY", f"Không thấy hóa đơn XML của tháng {month} trong thư mục hóa đơn.")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                # Fixed timestamps: the same month always yields the same file,
                # so a second click reopens the earlier run.
                info = zipfile.ZipInfo(path.parent.name + "/" + path.name, date_time=(1980, 1, 1, 0, 0, 0))
                archive.writestr(info, path.read_bytes())
        name = f"Hoa don {month}.zip"
        return self.quick_upload(buffer.getvalue(), name, name, progress=progress)

    def quick_repropose(self, run_id: str, progress=None) -> dict:
        with self._mutation_lock, Store(self.config) as store:
            return QuickPosting(store).repropose(text_id(run_id, "run_id"), "NGUOI_VAN_HANH", progress=progress)

    def quick_rows(self, run_id: str) -> dict:
        with Store(self.config) as store:
            return QuickPosting(store).rows(run_id)

    def quick_ai_note(self, run_id: str, item_id: str, note: str, actor: str = "CFO_NTD") -> dict:
        with self._mutation_lock, Store(self.config) as store:
            return QuickPosting(store).set_ai_note(run_id, item_id, note or "", actor)

    def quick_ai_context(self, run_id: str, item_ids: list | None = None) -> dict:
        """Write the Claude hand-off package next to the store and return it."""
        run_id = text_id(run_id, "run_id")
        with Store(self.config) as store:
            result = QuickPosting(store).ai_context(run_id, item_ids)
        folder = self.root / "ghi-chu-ai"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = now_utc()[:19].replace(":", "").replace("-", "").replace("T", "-")
        path = folder / f"{stamp}-{run_id[:8]}.md"
        path.write_text(result["markdown"], encoding="utf-8")
        latest = folder / "MOI-NHAT.md"
        latest.write_text(result["markdown"], encoding="utf-8")
        return {**result, "file": path.name, "folder_display": str(folder), "latest": latest.name}

    def quick_score(self, run_id: str) -> dict:
        """Grade a run against the Junsky vouchers and write the workbook."""
        run_id = text_id(run_id, "run_id")
        with Store(self.config) as store:
            quick = QuickPosting(store)
            scored = quick.score(run_id)
            folder = self.root / "xuat-junsky" / run_id
            path = quick.write_score_workbook(folder / "SO-VOI-JUNSKY.xlsx", scored)
        return {"run_id": run_id, "summary": scored["summary"], "rows": scored["rows"], "names": scored["names"],
                "answer_source": scored.get("answer_source", ""), "kind": scored.get("kind", "BANK"), "file": path.name, "folder_display": str(path.parent)}

    def quick_decide(self, run_id: str, items: list[dict], actor: str, at: str) -> dict:
        run_id = text_id(run_id, "run_id")
        with self._mutation_lock, Store(self.config) as store:
            quick = QuickPosting(store)
            result = quick.decide(run_id, items, actor, at)
            # "Ghi nhớ cho lần sau": rows still waiting with the same STK (or
            # name) get the new decision at once, not only next month.
            learned = [item for item in items if isinstance(item, dict) and ((item.get("action") == "APPROVE" and item.get("remember", True) is not False) or item.get("action") == "REOPEN")]
            similar = []
            for item in learned:
                row = store.conn.execute("SELECT document_id FROM quick_items WHERE id=? AND run_id=?", (item.get("id"), run_id)).fetchone()
                if row:
                    similar.extend(quick.similar_waiting(run_id, row[0]))
            similar = sorted(set(similar))
            refreshed = 0
            if similar and len(similar) <= 60:
                try:
                    result = quick.repropose(run_id, "NGUOI_VAN_HANH", document_ids=similar)
                    refreshed = len(similar)
                except (DataError, OSError, ValueError, KeyError, TypeError):
                    # The decision itself is already committed; a failed
                    # refresh of sibling rows only means they stay as they were.
                    result = quick.rows(run_id)
            result["refreshed"] = refreshed
            return result

    def quick_export(self, run_id: str, junsky_files: bool = False, actor: str = "CFO_NTD") -> dict:
        if junsky_files and not self.config.junsky_export_enabled:
            # Level 2 opens only after a successful test import (config switch).
            raise DataError("JUNSKY_EXPORT_LOCKED", "File nhập Junsky đang tạm khóa; chỉ xuất File soát (Excel).")
        with self._mutation_lock, Store(self.config) as store:
            result = QuickPosting(store).export(text_id(run_id, "run_id"), self.root, junsky_files=bool(junsky_files), actor=actor)
        # The browser only needs a filename to request a generated workbook.
        # Do not reveal the workstation's absolute export directory in an API
        # response (and keep the actual path inside this facade).
        return {**result,
                "files": [Path(value).name for value in result.get("files", [])],
                "review": Path(result["review"]).name if result.get("review") else "",
                # Shown to Anh on his own machine so he can find the file.
                "folder_display": str(Path(result["review"]).parent) if result.get("review") else ""}

    def quick_file(self, run_id: str, name: str) -> tuple[str, bytes]:
        """Return one workbook generated for a particular quick-export run.

        `name` is never a path supplied by the browser.  A request can only
        reach an .xlsx file directly below ``xuat-junsky/<run_id>``; this
        keeps the download route from becoming a general local-file reader.
        """
        run_id = text_id(run_id, "run_id")
        if len(run_id) > 128 or Path(run_id).name != run_id or run_id in {".", ".."}:
            raise DataError("QUICK_EXPORT_FILE", "Lần xuất tệp không hợp lệ.")
        name = self._safe_name(name)
        name_path = Path(name)
        if name_path.name != name or name_path.drive or name_path.root or name_path.suffix.casefold() != ".xlsx":
            raise DataError("QUICK_EXPORT_FILE", "Chỉ tải được workbook .xlsx do phần mềm vừa xuất.")
        export_root = (self.root / "xuat-junsky").resolve()
        run_root = (export_root / run_id).resolve()
        candidate = run_root / name
        path = candidate.resolve()
        if run_root.parent != export_root or run_root.is_symlink() or candidate.is_symlink() or path.parent != run_root or not path.is_file():
            raise DataError("QUICK_EXPORT_FILE", "Không tìm thấy tệp xuất của lần xử lý này.")
        return path.name, path.read_bytes()

    @staticmethod
    def _safe_name(value: str, field: str = "tên tệp") -> str:
        value = text_id(value, field).replace("\\", "/")
        if len(value) > 240 or "/" in value or value in {".", ".."}:
            raise DataError("FILE_NAME", "Tên tệp không hợp lệ.")
        return value

    @staticmethod
    def _safe_relative(value: str) -> Path:
        value = value.replace("\\", "/").strip("/")
        parts = [part for part in value.split("/") if part]
        if not parts or any(part in {".", ".."} or len(part) > 240 for part in parts):
            raise DataError("FILE_NAME", "Đường dẫn tệp đã chọn không hợp lệ.")
        return Path(*parts)

    @staticmethod
    def _summary(report: dict) -> dict:
        issue_counts = Counter((issue.get("severity", "ERROR"), issue.get("code", "UNKNOWN")) for issue in report.get("issues", []))
        return {"attempt_id": report.get("attempt_id"), "source": report.get("source"), "state": report.get("state"),
                "input_records": report.get("input_records", 0), "inserted_documents": report.get("inserted_documents", 0),
                "duplicate_documents": report.get("duplicate_documents", 0), "quarantine": report.get("quarantine", {}),
                "controls": report.get("controls", {}), "issue_counts": [{"severity": severity, "code": code, "count": count}
                 for (severity, code), count in sorted(issue_counts.items())],
                "meaning": report.get("meaning")}

    def state(self) -> dict:
        with Store(self.config) as store:
            status = store.status()
            pending = store.conn.execute("""SELECT COUNT(*) FROM knowledge_versions k
                WHERE NOT EXISTS (SELECT 1 FROM knowledge_events e WHERE e.version_id=k.id AND e.action='APPROVE')
                AND NOT EXISTS (SELECT 1 FROM knowledge_events e WHERE e.version_id=k.id AND e.action='REVOKE')""").fetchone()[0]
            attempts = []
            for row in store.conn.execute("""SELECT id,source,state,as_of,exported_at,finished_at,report_json
                FROM attempts WHERE report_json IS NOT NULL ORDER BY rowid DESC LIMIT 20"""):
                report = json.loads(row[6])
                attempts.append({"id": row[0], "source": row[1], "state": row[2], "as_of": row[3], "exported_at": row[4], "finished_at": row[5],
                                 "input_records": report.get("input_records", 0), "inserted_documents": report.get("inserted_documents", 0),
                                 "quarantine_count": report.get("quarantine", {}).get("count", 0)})
            outside = []
            for row in store.conn.execute("SELECT report_json FROM attempts WHERE source='junsky_xuat' AND state='COMMITTED' ORDER BY rowid DESC LIMIT 1"):
                outside = json.loads(row[0]).get("controls", {}).get("outside_catalog_codes", [])
            active = store.conn.execute("SELECT id,state,cutoff FROM sessions WHERE state='OPEN' ORDER BY opened_at DESC LIMIT 1").fetchone()
        source_until = {}
        with Store(self.config) as store:
            for kind, label in (("JOURNAL", "ledger"), ("OPEN_ITEM", "open_item"), ("COUNTERPARTY", "catalog")):
                source_until[label] = store.conn.execute("SELECT MAX(business_date) FROM documents WHERE kind=?", (kind,)).fetchone()[0]
        return {"environment": "that", "entity_id": self.config.entity_id, "schema_version": status["schema_version"], "status": status,
                "pending_knowledge": pending, "attempts": attempts, "outside_catalog_codes": outside,
                "active_session": dict(active) if active else None, "sources": SOURCE_LABELS,
                "source_until": source_until, "source_paths": self.source_settings()["paths"],
                "junsky_import_enabled": self.config.junsky_import_enabled, "junsky_export_enabled": self.config.junsky_export_enabled,
                "approval_actor": self.config.knowledge_approval_actor}

    def receive_source(self, raw: bytes, metadata: dict) -> dict:
        if not raw:
            raise DataError("EMPTY_FILE", "Tệp rỗng; chưa nạp.")
        if not isinstance(metadata, dict) or set(metadata) - {"source", "batch_id", "name", "relative_path"}:
            raise DataError("SOURCE_UPLOAD_METADATA", "Thông tin tệp nguồn không hợp lệ.")
        source = metadata.get("source")
        if source not in SOURCES:
            raise DataError("SOURCE_REQUIRED", "Chọn một trong năm nguồn trước khi tải tệp.")
        batch = metadata.get("batch_id") or sha256((source + now_utc()).encode())[:24]
        if not isinstance(batch, str) or not batch.isalnum() or not 8 <= len(batch) <= 64:
            raise DataError("SOURCE_BATCH", "Mã lượt chọn tệp không hợp lệ.")
        relative = self._safe_relative(metadata.get("relative_path") or self._safe_name(metadata.get("name")))
        target_root = self.staging / source / batch
        target = target_root / relative
        if not target.resolve().is_relative_to(target_root.resolve()):
            raise DataError("UNSAFE_SOURCE_PATH", "Đường dẫn nguồn nằm ngoài khu vực tạm của ứng dụng.")
        with self._mutation_lock:
            write_immutable(target, raw)
        return {"batch_id": batch, "source": source, "file": relative.name, "bytes": len(raw), "sha256": sha256(raw)}

    def _source_path(self, source: str, batch: str) -> Path:
        root = self.staging / source / batch
        if not root.is_dir() or not any(path.is_file() for path in root.rglob("*")):
            raise DataError("SOURCE_BATCH_EMPTY", "Chưa có tệp được chọn cho nguồn này.")
        files = [path for path in root.rglob("*") if path.is_file()]
        return files[0] if source in {"sao_ke", "hoa_don", "bang_ke"} and len(files) == 1 else root

    def start(self, label: str, callback, *, progress: bool = False) -> dict:
        identifier = sha256((label + now_utc() + str(id(callback))).encode())[:24]
        with self._jobs_lock:
            self._jobs[identifier] = {"id": identifier, "label": label, "state": "RUNNING", "started_at": now_utc(), "progress": None}
        def report(done, total):
            with self._jobs_lock:
                self._jobs[identifier]["progress"] = {"done": int(done), "total": int(total)}
        def work():
            try:
                result = callback(report) if progress else callback()
                payload = {"state": "COMPLETED", "result": result}
            except DataError as exc:
                payload = {"state": "FAILED", "error": exc.code, "message": str(exc)}
            except (OSError, ValueError, TypeError, KeyError) as exc:
                payload = {"state": "FAILED", "error": "OPERATION_FAILED", "message": f"Không hoàn tất thao tác ({type(exc).__name__})."}
            with self._jobs_lock:
                self._jobs[identifier].update(payload, finished_at=now_utc())
        threading.Thread(target=work, name="ktt-" + label, daemon=True).start()
        return {"job_id": identifier, "state": "RUNNING"}

    def job(self, identifier: str) -> dict:
        with self._jobs_lock:
            value = self._jobs.get(identifier)
            if not value:
                raise DataError("JOB_NOT_FOUND", "Không thấy thao tác nền; hãy tải lại trạng thái kho.")
            return dict(value)

    def ingest(self, request: dict) -> dict:
        if not isinstance(request, dict):
            raise DataError("INGEST_REQUEST", "Yêu cầu nạp nguồn không hợp lệ.")
        source = request.get("source")
        if source not in SOURCES:
            raise DataError("SOURCE_REQUIRED", "Chọn nguồn để nạp.")
        batch = text_id(request.get("batch_id"), "batch_id")
        as_of = date_iso(request.get("as_of"))
        coverage_from = date_iso(request.get("coverage_from") or as_of)
        coverage_to = date_iso(request.get("coverage_to_exclusive") or as_of)
        if coverage_to <= coverage_from:
            raise DataError("DATE_RANGE", "Phạm vi dữ liệu cần có ngày kết thúc sau ngày bắt đầu.")
        exported_at = instant_utc(request.get("exported_at") or now_utc())
        known_at = request.get("known_at") or None
        if known_at:
            known_at = instant_utc(known_at)
        metadata = SourceMetadata(as_of, exported_at, text_id(request.get("known_at_basis"), "known_at_basis"), coverage_from, coverage_to,
                                  known_at, request.get("snapshot_id") or None, "PLHN_" + source.upper(),
                                  posting_evidence_complete=bool(request.get("posting_evidence_complete", False)),
                                  scope_open_items_complete=bool(request.get("scope_open_items_complete", False)),
                                  catalog_valid_from=request.get("catalog_valid_from") or None)
        path = self._source_path(source, batch)
        with self._mutation_lock, Store(self.config) as store:
            report = store.ingest(path, ThatAdapter(source, path, metadata))
        return self._summary(report)

    def report(self, attempt_id: str) -> dict:
        with Store(self.config) as store:
            # The browser shows the immutable ingestion report, not a recreated
            # view.  It contains only reader diagnostics and control totals.
            return store.report(text_id(attempt_id, "attempt_id"))

    def quarantine(self, attempt_id: str) -> dict:
        with Store(self.config) as store:
            return store.quarantined(text_id(attempt_id, "attempt_id"))

    def knowledge_upload(self, raw: bytes, name: str, actor: str, at: str, catalog_valid_from: str | None = None) -> dict:
        name = self._safe_name(name)
        if not name.casefold().endswith(".xlsx"):
            raise DataError("KNOWLEDGE_SOURCE_FILE", "Workbook tri thức cần có đuôi .xlsx.")
        target = self.root / "tri-thuc-da-chon" / sha256(raw) / name
        write_immutable(target, raw)
        with self._mutation_lock, Store(self.config) as store:
            return HumanKnowledgeWorkbook(store).import_sources([target], actor, at, catalog_valid_from)

    def knowledge_rows(self, category: str | None = None, query: str = "", page: int = 1, size: int = 50) -> dict:
        if category is not None and not isinstance(category, str):
            raise DataError("KNOWLEDGE_FILTER", "Bộ lọc tri thức không hợp lệ.")
        if not isinstance(query, str) or not 1 <= page <= 100000 or not 1 <= size <= 100:
            raise DataError("KNOWLEDGE_FILTER", "Bộ lọc/phân trang tri thức không hợp lệ.")
        terms = "%" + query.strip().replace("%", "") + "%"
        with Store(self.config) as store:
            sql = """SELECT k.id,k.category,k.logical_key,k.valid_from,k.valid_to,k.known_at,k.payload_json,k.evidence_json,
                EXISTS(SELECT 1 FROM knowledge_events e WHERE e.version_id=k.id AND e.action='APPROVE') approved,
                EXISTS(SELECT 1 FROM knowledge_events e WHERE e.version_id=k.id AND e.action='REVOKE') rejected
                FROM knowledge_versions k WHERE (? IS NULL OR k.category=?) AND (k.logical_key LIKE ? OR k.category LIKE ?)
                ORDER BY k.created_at DESC,k.id DESC LIMIT ? OFFSET ?"""
            rows = [dict(row) for row in store.conn.execute(sql, (category, category, terms, terms, size, (page - 1) * size))]
            total = store.conn.execute("SELECT COUNT(*) FROM knowledge_versions WHERE (? IS NULL OR category=?) AND (logical_key LIKE ? OR category LIKE ?)", (category, category, terms, terms)).fetchone()[0]
        for row in rows:
            approved, rejected = bool(row.pop("approved")), bool(row.pop("rejected"))
            row["status"] = "Đã duyệt" if approved and not rejected else "Từ chối" if rejected else "Chờ duyệt"
            payload = json.loads(row.pop("payload_json")); row.pop("evidence_json")
            if payload.get("kind") == "IDENTIFIER":
                row["business_text"] = f"Khi gặp định danh đã lưu, thì dùng đối tượng {payload.get('counterparty', '')}. Vì sao: căn cứ danh mục hoặc quyết định trước đó."
            elif row["category"] == "POLICY":
                fields = payload.get("fields", {})
                row["business_text"] = f"Khi thỏa điều kiện mẫu, thì đề xuất Nợ {fields.get('debit_account') or 'chưa xác định'} / Có {fields.get('credit_account') or 'chưa xác định'}. Vì sao: tri thức có hiệu lực."
            else:
                row["business_text"] = "Khi điều kiện của tri thức có hiệu lực, thì dùng làm căn cứ đề xuất. Vì sao: nguồn tri thức đã nạp."
        return {"rows": rows, "page": page, "size": size, "total": total}

    def decide_knowledge(self, items: list[dict], actor: str, at: str) -> dict:
        if actor != self.config.knowledge_approval_actor:
            raise DataError("APPROVAL_ACTOR", f"Người duyệt phải là {self.config.knowledge_approval_actor}.")
        if not isinstance(items, list) or not items:
            raise DataError("EMPTY_KNOWLEDGE_DECISION", "Chọn ít nhất một phiên bản tri thức để duyệt hoặc từ chối.")
        with self._mutation_lock, Store(self.config) as store:
            knowledge = Knowledge(store); approved = rejected = 0
            for item in items:
                if not isinstance(item, dict) or set(item) - {"id", "action", "reason"} or item.get("action") not in {"APPROVE", "REJECT"}:
                    raise DataError("KNOWLEDGE_DECISION", "Quyết định tri thức cần ID và Duyệt hoặc Từ chối.")
                if item["action"] == "APPROVE":
                    knowledge.approve(text_id(item.get("id"), "knowledge_id"), actor, at); approved += 1
                else:
                    knowledge.revoke(text_id(item.get("id"), "knowledge_id"), actor, at, text_id(item.get("reason"), "reason"), allow_pending=True); rejected += 1
        return {"approved": approved, "rejected": rejected, "actor": actor}

    def catalog(self, business_date: str, cutoff: str) -> dict:
        business_date, cutoff = date_iso(business_date), instant_utc(cutoff)
        with Store(self.config) as store:
            rows = Knowledge(store).query(business_date, cutoff, "CATALOG")
        result: dict[str, list[dict]] = {kind: [] for kind in ("COUNTERPARTY", "ACCOUNT", "PROJECT", "EXPENSE", "COST_CENTER")}
        for row in rows:
            payload = row["payload"]
            kind, code = payload.get("kind"), payload.get("code")
            if kind in result and isinstance(code, str):
                result[kind].append({"code": code, "name": payload.get("name", "")})
        return {"business_date": business_date, "catalog": {kind: sorted(values, key=lambda value: value["code"]) for kind, values in result.items()}}

    def _records_for_session(self, store: Store, source_kind: str, start: str, end: str) -> tuple[str, list[str]]:
        if source_kind == "sao_ke":
            data = store.bank_documents(start, end, without_proposal=True)
            attempt = store.conn.execute("SELECT id FROM attempts WHERE source='junsky_xuat' AND state='COMMITTED' ORDER BY rowid DESC LIMIT 1").fetchone()
            if not attempt:
                raise DataError("JUNSKY_SNAPSHOT_REQUIRED", "Cần nạp snapshot Junsky hợp lệ trước khi mở phiên sao kê.")
            return attempt[0], [row["id"] for row in data["records"]]
        kind = {"hoa_don": "INVOICE", "base": "BASE"}.get(source_kind)
        if not kind:
            raise DataError("SESSION_SOURCE", "Chỉ mở phiên cho sao kê, hóa đơn hoặc Base.")
        rows = list(store.conn.execute("SELECT id,first_attempt_id FROM documents WHERE kind=? AND business_date>=? AND business_date<=? ORDER BY business_date,id", (kind, start, end)))
        if not rows:
            raise DataError("NO_SOURCE_DOCUMENTS", "Không có chứng từ trong khoảng ngày đã chọn.")
        return rows[0][1], [row[0] for row in rows]

    def run_session(self, request: dict) -> dict:
        source_kind = request.get("source_kind", "sao_ke")
        start, end = date_iso(request.get("from")), date_iso(request.get("to"))
        if end < start:
            raise DataError("DATE_RANGE", "Ngày kết thúc không được trước ngày bắt đầu.")
        actor = text_id(request.get("actor"), "actor")
        cutoff = instant_utc(request.get("cutoff") or now_utc())
        with self._mutation_lock, Store(self.config) as store:
            attempt_id, identifiers = self._records_for_session(store, source_kind, start, end)
            session = Sessions(store).open(attempt_id, identifiers, cutoff, actor, "shadow")
            proposals = Sessions(store).propose(session["id"])
        summary = Counter(proposal["completeness"] for proposal in proposals)
        constraints = Counter(code for proposal in proposals for code in proposal.get("constraints", []))
        warnings = Counter(code for proposal in proposals for code in proposal.get("warnings", []))
        return {"session_id": session["id"], "source_kind": source_kind, "document_count": len(identifiers), "proposals": dict(summary),
                "constraints": dict(sorted(constraints.items())), "warnings": dict(sorted(warnings.items()))}

    def proposal_rows(self, session_id: str, at: str) -> dict:
        with Store(self.config) as store:
            return {"session_id": session_id, "rows": ReviewExport(store).ui_rows(session_id, at)}

    def decide_proposals(self, session_id: str, items: list[dict], actor: str, at: str) -> dict:
        with self._mutation_lock, Store(self.config) as store:
            return ReviewExport(store).decide_from_ui(session_id, items, actor, at)

    def shadow_export(self, session_id: str, actor: str, at: str) -> dict:
        with self._mutation_lock, Store(self.config) as store:
            return ShadowJunskyExport(store).export(session_id, actor, at)

    def shadow_file(self, shadow_id: str, direction: str) -> tuple[str, bytes]:
        if direction not in {"thu", "chi"}:
            raise DataError("SHADOW_FILE", "Chỉ tải file mô phỏng thu hoặc chi.")
        with Store(self.config) as store:
            paths = ShadowJunskyExport(store).recover(text_id(shadow_id, "shadow_id"))
        path = Path(paths[direction])
        return path.name, path.read_bytes()

    def outside_catalog(self) -> bytes:
        with Store(self.config) as store:
            row = store.conn.execute("SELECT report_json FROM attempts WHERE source='junsky_xuat' AND state='COMMITTED' ORDER BY rowid DESC LIMIT 1").fetchone()
            rows = json.loads(row[0]).get("controls", {}).get("outside_catalog_codes", []) if row else []
        return canonical_json({"environment": "that", "records": rows, "meaning": "Mã xuất hiện trong sổ/công nợ nhưng chưa thấy trong danh mục; không tự bổ sung."}).encode("utf-8")

    # ------------------------------------------------------------------
    # V10 screen: overview, settings, mappings, knowledge cards, history
    # ------------------------------------------------------------------
    def overview(self) -> dict:
        """Everything the top bar and the 'Nguồn dữ liệu' screen show."""
        settings = self.source_settings()
        paths = settings["paths"]
        with Store(self.config) as store:
            conn = store.conn
            until = {label: conn.execute("SELECT MAX(business_date) FROM documents WHERE kind=?", (kind,)).fetchone()[0]
                     for kind, label in (("JOURNAL", "ledger"), ("OPEN_ITEM", "open_item"))}
            journals = conn.execute("SELECT COUNT(*) FROM documents WHERE kind='JOURNAL'").fetchone()[0]
            open_items = conn.execute("SELECT COUNT(*) FROM documents WHERE kind='OPEN_ITEM'").fetchone()[0]
            catalog = {kind: conn.execute("SELECT COUNT(*) FROM documents WHERE kind=?", (kind,)).fetchone()[0]
                       for kind in ("COUNTERPARTY", "ACCOUNT", "PROJECT", "EXPENSE", "COST_CENTER")}
            partners = conn.execute("""SELECT COUNT(DISTINCT json_extract(payload_json,'$.value')) FROM knowledge_versions
                                        WHERE category='CATALOG' AND json_extract(payload_json,'$.kind')='IDENTIFIER'
                                        AND json_extract(payload_json,'$.identifier_type')='BANK_ACCOUNT'""").fetchone()[0]
            junsky = conn.execute("SELECT finished_at FROM attempts WHERE source='junsky_xuat' AND state='COMMITTED' ORDER BY rowid DESC LIMIT 1").fetchone()
            decisions = conn.execute("SELECT COUNT(*) FROM quick_condition_learning WHERE active=1").fetchone()[0]
        job = None
        if self.bootstrap_job:
            with self._jobs_lock:
                value = self._jobs.get(self.bootstrap_job)
                job = {"id": value["id"], "state": value["state"], "message": value.get("message")} if value else None
        def exists(key):
            return Path(paths[key]).exists()
        def modified(key):
            path = Path(paths[key])
            try:
                stamps = [path.stat().st_mtime] if path.is_file() else [item.stat().st_mtime for item in path.rglob("*.xls*") if item.is_file()] if path.is_dir() else []
            except OSError:
                stamps = []
            if not stamps:
                return None
            from datetime import datetime, timezone
            return datetime.fromtimestamp(max(stamps), timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        partner_file = self.config_path.parent / "DANH MUC DOI TAC PLHN - BO SUNG STK VA DICH VU (nhap 24-09-2026).xlsx"
        return {"environment": self.config.environment, "entity_id": self.config.entity_id, "data_label": self.config.data_dir.name,
                "storage_engine": store.engine, "storage_schema": getattr(store.conn, "schema", None),  # V13: thanh trên ghi "PostgreSQL · kho thử"
                "ledger_to": until["ledger"], "open_item_to": until["open_item"], "journal_count": journals, "open_item_count": open_items,
                "catalog_counts": catalog, "partner_accounts": partners, "partner_file": partner_file.name if partner_file.is_file() else "",
                "junsky_loaded_at": junsky[0] if junsky else None, "anh_decisions": decisions,
                "paths_exist": {key: exists(key) for key in ("junsky_catalog", "junsky_dgblist", "junsky_ledger")},
                "files_modified": {key: modified(key) for key in ("junsky_catalog", "junsky_dgblist", "junsky_ledger")},
                "paths": {key: paths[key] for key in ("junsky_catalog", "junsky_dgblist", "junsky_ledger")},
                "learning_cutoff": settings["settings"].get("learning_cutoff") or "", "object_learning_from": settings["settings"].get("object_learning_from"),
                "debt_accounts": settings["settings"].get("debt_accounts"), "cash_accounts": settings["cash_accounts"],
                "scoring_mode": bool(settings["settings"].get("scoring_mode")), "local_ai": settings["settings"].get("local_ai") or {},
                "answer_ledger_name": Path(settings["settings"]["answer_ledger"]).name if settings["settings"].get("answer_ledger") else "",
                "bootstrap_job": job, "bootstrap_status": self.bootstrap_status, "junsky_import_enabled": False}

    def reload_sources(self) -> dict:
        """Nạp lại: re-read Junsky catalogue, ledger, open items, rule books and partners."""
        with self._jobs_lock:
            running = self.bootstrap_job and self._jobs.get(self.bootstrap_job, {}).get("state") == "RUNNING"
        if running:
            return {"job_id": self.bootstrap_job, "state": "RUNNING"}
        self.bootstrap_job = self.start("nen-junsky", self.bootstrap)["job_id"]
        return {"job_id": self.bootstrap_job, "state": "RUNNING"}

    def save_learning_settings(self, values: dict) -> dict:
        if not isinstance(values, dict) or set(values) - {"learning_cutoff", "object_learning_from", "debt_accounts", "scoring_mode", "local_ai"}:
            raise DataError("SOURCE_SETTINGS", "Thiết lập mốc học không hợp lệ.")
        current = self.source_settings()
        return self.save_source_settings({"paths": current["paths"], "settings": {**{key: value for key, value in values.items()}}})

    def set_cash_mapping(self, bank_account_value: str, cash_account: str | None) -> dict:
        account = self._bank_account(bank_account_value)
        if not account:
            raise DataError("CASH_ACCOUNT_MAPPING", "Số tài khoản ngân hàng cần ít nhất 6 chữ số.")
        with self._mutation_lock, Store(self.config) as store:
            if cash_account:
                catalog = {row["payload"]["code"] for row in Knowledge(store).query(now_utc()[:10], now_utc(), "CATALOG") if row["payload"].get("kind") == "ACCOUNT"}
                if cash_account not in catalog:
                    raise DataError("CASH_ACCOUNT_MAPPING", "TK kế toán không có trong danh mục tài khoản Junsky.")
                QuickPosting(store).set_cash_mapping(account, cash_account, "CFO_NTD", "MANUAL", ["MAN_HINH_NGUON_DU_LIEU"])
            else:
                store.conn.execute("DELETE FROM cash_account_mappings WHERE bank_account=?", (account,))
            store.conn.commit()
        # Keep the setup file in step so a rebuilt store gets the same mapping.
        path = self.root / "source-settings.json"
        try:
            saved = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"paths": self.source_settings()["paths"], "settings": {}}
            items = [item for item in saved.setdefault("settings", {}).get("cash_accounts", []) if isinstance(item, dict) and self._bank_account(item.get("bank_account")) != account]
            if cash_account:
                items.append({"bank_account": account, "cash_account": cash_account})
            saved["settings"]["cash_accounts"] = items
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(canonical_json(saved), encoding="utf-8")
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
        return self.source_settings()

    def knowledge_cards(self, query: str = "", limit: int = 60) -> dict:
        """Read-only 'Khi … / Thì … / Vì sao …' cards for the Tra cứu screen."""
        if not isinstance(query, str) or len(query) > 200:
            raise DataError("KNOWLEDGE_FILTER", "Từ khóa tìm không hợp lệ.")
        needle = normalize_text(query.strip()) if query.strip() else ""
        def words(fields):
            parts = []
            if fields.get("debit_account"): parts.append("Nợ " + str(fields["debit_account"]))
            if fields.get("credit_account"): parts.append("Có " + str(fields["credit_account"]))
            if fields.get("counterparty"): parts.append("đối tượng " + str(fields["counterparty"]))
            if fields.get("project"): parts.append("dự án " + str(fields["project"]))
            if fields.get("expense"): parts.append("khoản mục " + str(fields["expense"]))
            return " · ".join(parts) or "—"
        cards, total = [], 0
        with Store(self.config) as store:
            names = {}
            for row in store.conn.execute("SELECT payload_json FROM knowledge_versions WHERE category='CATALOG' AND json_extract(payload_json,'$.kind')='COUNTERPARTY'"):
                payload = json.loads(row[0]); names[payload.get("code")] = payload.get("name", "")
            sources = []
            for row in store.conn.execute("SELECT condition_type,condition_value,fields_json,created_at FROM quick_condition_learning WHERE active=1 ORDER BY created_at DESC"):
                fields = json.loads(row["fields_json"])
                label = {"BANK_ACCOUNT": "STK đối ứng", "COUNTERPARTY_NAME": "Tên đối ứng", "KEYWORD": "Từ khóa"}[row["condition_type"]]
                value = row["condition_value"]
                shown = ("•••• " + value[-4:]) if row["condition_type"] == "BANK_ACCOUNT" else value
                sources.append({"kind": "ANH", "when": f"{label} là “{shown}”", "then": words(fields), "why": "Anh đã duyệt ngày " + str(row["created_at"])[:10] + ".",
                                "tags": [value for value in (fields.get("debit_account"), fields.get("credit_account"), fields.get("counterparty"), names.get(fields.get("counterparty"))) if value],
                                "search": " ".join([value, words(fields), names.get(fields.get("counterparty"), "")])})
            rows = store.conn.execute("""SELECT k.payload_json FROM knowledge_versions k WHERE k.category='POLICY'
                AND NOT EXISTS (SELECT 1 FROM knowledge_events e WHERE e.version_id=k.id AND e.action='REVOKE') ORDER BY k.logical_key""").fetchall()
            for row in rows:
                payload = json.loads(row[0]); fields = payload.get("fields", {}); source = payload.get("source_row") or {}; trigger = payload.get("trigger") or {}
                key_type = trigger.get("key_type") or source.get("loai_khoa") or ""
                key_value = trigger.get("key_value") or source.get("tu_khoa") or trigger.get("regex") or ""
                if key_type == "BANK_ACCOUNT" and key_value:
                    when = "STK đối ứng là “•••• " + str(key_value)[-4:] + "”"
                elif key_type == "COUNTERPARTY_NAME" and key_value:
                    when = "Tên đối ứng là “" + str(key_value) + "”"
                else:
                    when = "Diễn giải có “" + str(source.get("tu_khoa") or key_value or "—") + "”"
                when += " · " + ("Thu" if payload.get("direction") == "IN" else "Chi" if payload.get("direction") == "OUT" else "Thu/Chi")
                seen, right = source.get("so_lan_gap"), source.get("so_lan_dung")
                why = (f"Gặp {seen} lần trong sổ, đúng {right} lần" if seen not in (None, "") else "Quy tắc học từ sổ") + (f" ({source.get('lan_dau')} → {source.get('lan_cuoi')})" if source.get("lan_dau") else "") + ". Chờ duyệt."
                if source.get("vi_du_dien_giai"):
                    why += " Ví dụ: “" + str(source["vi_du_dien_giai"])[:120] + "”."
                party = fields.get("counterparty")
                sources.append({"kind": "QUY_TAC", "code": source.get("ma_quy_tac") or "", "when": when, "then": words(fields), "why": why,
                                "tags": [value for value in (fields.get("debit_account"), fields.get("credit_account"), party, names.get(party), source.get("ma_quy_tac")) if value],
                                "search": " ".join(str(value) for value in (when, words(fields), names.get(party, ""), source.get("vi_du_dien_giai") or "", source.get("ma_quy_tac") or "", key_value))})
        for card in sources:
            if needle and needle not in normalize_text(card["search"]):
                continue
            total += 1
            if len(cards) < limit:
                cards.append({key: value for key, value in card.items() if key != "search"})
        return {"cards": cards, "total": total, "limit": limit}

    def history(self) -> dict:
        with Store(self.config) as store:
            return {"rows": QuickPosting(store).history(), "folder_display": str(self.root / "xuat-junsky")}

    def runs(self) -> dict:
        with Store(self.config) as store:
            return {"rows": QuickPosting(store).runs()}

    def open_ai_folder(self) -> dict:
        """Open the folder holding the Claude hand-off packages (V11)."""
        target = (self.root / "ghi-chu-ai").resolve()
        target.mkdir(parents=True, exist_ok=True)
        import os
        opener = getattr(os, "startfile", None)
        if opener is None:
            return {"opened": False, "path": str(target)}
        opener(str(target))
        return {"opened": True, "path": str(target)}

    def open_export(self, run_id: str, name: str | None = None) -> dict:
        """Open the export folder (or one workbook) in Windows Explorer on this machine."""
        run_id = text_id(run_id, "run_id")
        if len(run_id) > 128 or Path(run_id).name != run_id or run_id in {".", ".."}:
            raise DataError("QUICK_EXPORT_FILE", "Lần xuất tệp không hợp lệ.")
        target = (self.root / "xuat-junsky" / run_id).resolve()
        if name:
            self.quick_file(run_id, name)  # same containment checks as a download
            target = target / self._safe_name(name)
        if not target.exists() or not target.resolve().is_relative_to((self.root / "xuat-junsky").resolve()):
            raise DataError("QUICK_EXPORT_FILE", "Không tìm thấy tệp xuất của lần xử lý này.")
        import os
        opener = getattr(os, "startfile", None)
        if opener is None:
            return {"opened": False, "path": str(target)}
        opener(str(target))
        return {"opened": True, "path": str(target)}
