"""Structural Junsky shadow files.  They are never importable operational batches."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill

from ..ha_tang.primitives import DataError, canonical_json, instant_utc, money_minor, sha256, text_id
from ..ha_tang.runtime import artifact, artifact_bytes, document, log, source_bundle, transaction, uid
from ..ha_tang.store import write_immutable
from ..hoc.service import Learning, allocation_signature, observed
from ..trang_thai.service import Sessions


ENTRY1_HEADERS = ("EntryID", "EntryDate", "BankID", "AcctID", "OrglID", "OrglRate", "OrglAmt", "BaseAmt", "ObjectID", "PayerID", "PayerText", "BranchID", "Memo", "DocsNo", "MRowID", "PeriodID", "ErrorText")
ENTRY2_HEADERS = ("EntryID", "Offset", "AcctID", "BankID", "OrglID", "OrglRate", "OrglDeb", "OrglCrd", "BaseDeb", "BaseCrd", "ObjectID", "EntryDM", "CashflowID", "PrecostID", "ProjectID", "CenterID", "CostID", "Remark", "VatID", "VatAcctID", "BaseBefVat", "BaseAmtVat", "InvName", "InvAddr", "InvCode", "InvForm", "InvSeri", "InvNo", "InvDate", "InvMode", "InvText", "InvLook", "iRow", "DRowID", "MRowID", "DebtID", "ErrorText")


class ShadowJunskyExport:
    """Create exact 17/37-column workbooks in `that` for structural checking.

    All operational mappings are supplied explicitly.  No default maps a real
    account to BankID, a debt reference to EntryDM/DebtID, or a template to a
    CashflowID.  Missing mappings leave a proposed item in the local wait list.
    """

    def __init__(self, store):
        self.store, self.db, self.sessions = store, store.conn, Sessions(store)

    @staticmethod
    def _workbook(rows: list[dict], direction: str) -> bytes:
        wb = Workbook()
        default = wb.active
        wb.remove(default)
        wb.properties.title = "SHADOW — CHƯA NHẬP JUNSKY"
        wb.properties.subject = "Kiểm tra cấu trúc; không phải tệp nhập Junsky"
        for name, headers in (("CB_tmpEntry1", ENTRY1_HEADERS), ("CB_tmpEntry2", ENTRY2_HEADERS)):
            ws = wb.create_sheet(name)
            ws.append(list(headers))
            for cell in ws[1]:
                cell.fill = PatternFill("solid", fgColor="9C0006")
                cell.font = Font(color="FFFFFF", bold=True)
                cell.comment = Comment("SHADOW — CHƯA NHẬP JUNSKY. Chỉ kiểm tra cấu trúc cột.", "Kho tri thức")
            for row in rows:
                values = [row["entry1"]] if name == "CB_tmpEntry1" else row["entry2"]
                for value in values:
                    ws.append([value.get(header, "") for header in headers])
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str):
                        cell.data_type = "s"
                        cell.number_format = "@"
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
        from io import BytesIO
        output = BytesIO(); wb.save(output); wb.close()
        raw = output.getvalue()
        ShadowJunskyExport.assert_structure_bytes(raw)
        return raw

    @staticmethod
    def assert_structure_bytes(raw: bytes) -> dict:
        try:
            wb = load_workbook(__import__("io").BytesIO(raw), read_only=True, data_only=False, keep_links=False)
            try:
                if tuple(wb.sheetnames) != ("CB_tmpEntry1", "CB_tmpEntry2"):
                    raise DataError("SHADOW_SHEETS", "Tệp shadow phải chỉ có CB_tmpEntry1 và CB_tmpEntry2.")
                actual1 = tuple(cell.value for cell in next(wb["CB_tmpEntry1"].iter_rows(min_row=1, max_row=1)))
                actual2 = tuple(cell.value for cell in next(wb["CB_tmpEntry2"].iter_rows(min_row=1, max_row=1)))
                if actual1 != ENTRY1_HEADERS or actual2 != ENTRY2_HEADERS:
                    raise DataError("SHADOW_HEADERS", "Cấu trúc Junsky shadow phải đúng Entry1 17 cột và Entry2 37 cột, gồm ErrorText.")
                return {"entry1_columns": len(actual1), "entry2_columns": len(actual2), "valid": True}
            finally:
                wb.close()
        except DataError:
            raise
        except Exception as exc:
            raise DataError("SHADOW_WORKBOOK", "Không kiểm tra được workbook shadow.") from exc

    @staticmethod
    def compare_structure(shadow_path: Path, reference_path: Path) -> dict:
        """Compare headers only; reference workbook is not treated as import proof."""
        ours = ShadowJunskyExport.assert_structure_bytes(Path(shadow_path).read_bytes())
        try:
            wb = load_workbook(reference_path, read_only=True, data_only=False, keep_links=False)
            try:
                expected = {"CB_tmpEntry1": ENTRY1_HEADERS, "CB_tmpEntry2": ENTRY2_HEADERS}
                result = {}
                for name, headers in expected.items():
                    if name not in wb.sheetnames:
                        result[name] = False
                        continue
                    result[name] = tuple(cell.value for cell in next(wb[name].iter_rows(min_row=1, max_row=1))) == headers
            finally:
                wb.close()
        except Exception as exc:
            raise DataError("REFERENCE_STRUCTURE", "Không đọc được file mẫu để so cấu trúc.") from exc
        return {"reference_structure_only": True, "shadow": ours, "reference_headers_match": result,
                "valid": all(result.values()), "not_import_evidence": True}

    @staticmethod
    def _mapping(value: dict | None) -> dict:
        mapping = value or {}
        if not isinstance(mapping, dict):
            raise DataError("SHADOW_MAPPING", "Cấu hình mapping shadow phải là object.")
        bank_id = mapping.get("bank_id_by_source_account", {})
        bank_gl = mapping.get("bank_gl_by_source_account", {})
        if not isinstance(bank_id, dict) or not isinstance(bank_gl, dict):
            raise DataError("SHADOW_MAPPING", "Mapping BankID và tài khoản ngân hàng phải là object theo tài khoản nguồn.")
        branch = mapping.get("branch_id")
        if branch is not None and not isinstance(branch, str):
            raise DataError("SHADOW_MAPPING", "branch_id phải là chuỗi mã Junsky.")
        mode = mapping.get("entry2_mode", "DAY_DU")
        if mode not in {"DAY_DU", "DOI_UNG"}:
            raise DataError("SHADOW_MAPPING", "entry2_mode chỉ nhận DAY_DU hoặc DOI_UNG.")
        prefix = mapping.get("entry_id_prefix", "SHADOW")
        if not isinstance(prefix, str) or not prefix:
            raise DataError("SHADOW_MAPPING", "entry_id_prefix phải là chuỗi không rỗng.")
        cashflow = mapping.get("cashflow_by_template", {})
        if not isinstance(cashflow, dict):
            raise DataError("SHADOW_MAPPING", "cashflow_by_template phải là object.")
        return {"bank_id": bank_id, "bank_gl": bank_gl, "branch_id": branch or "", "entry2_mode": mode, "entry_id_prefix": prefix, "cashflow": cashflow}

    def export(self, session_id: str, actor: str, at: str, mapping: dict | None = None) -> dict:
        if self.store.config.environment != "that" or self.store.config.junsky_export_enabled or self.store.config.junsky_import_enabled:
            raise DataError("SHADOW_THAT_ONLY", "Shadow chỉ chạy ở kho that có cờ xuất/nhập Junsky tắt.")
        actor = text_id(actor, "actor")
        if not actor.startswith("MO_PHONG_"):
            raise DataError("SHADOW_ACTOR", "Actor shadow phải bắt đầu bằng MO_PHONG_ để không nhầm với kế toán duyệt.")
        at, profile = instant_utc(at), self._mapping(mapping)
        old = self.db.execute("SELECT * FROM shadow_exports WHERE session_id=?", (session_id,)).fetchone()
        if old:
            return self.recover(old["id"])
        with transaction(self.store):
            session = self.sessions.get(session_id, True)
            self.sessions.assert_current(session, at)
            rows = {"THU": [], "CHI": []}
            wait: dict[str, int] = {}
            for proposal in self.db.execute("SELECT * FROM proposals WHERE session_id=? ORDER BY bank_id", (session_id,)):
                decision = self.db.execute("SELECT * FROM decisions WHERE proposal_id=? AND action='APPROVE' ORDER BY revision DESC LIMIT 1", (proposal["id"],)).fetchone()
                if not decision:
                    wait["NO_SIMULATED_APPROVAL"] = wait.get("NO_SIMULATED_APPROVAL", 0) + 1
                    continue
                payload = json.loads(decision["payload_json"])
                bank = document(self.store, proposal["bank_id"], session["cutoff"])
                bank_id, bank_gl = profile["bank_id"].get(bank["account"]), profile["bank_gl"].get(bank["account"])
                missing = []
                if not bank_id:
                    missing.append("BANK_ID_MAPPING")
                if not bank_gl:
                    missing.append("BANK_GL_MAPPING")
                if not profile["branch_id"]:
                    missing.append("BRANCH_ID_MAPPING")
                if missing:
                    for reason in missing:
                        wait[reason] = wait.get(reason, 0) + 1
                    continue
                direction = "THU" if payload["amount_minor"] > 0 else "CHI"
                entry_id = f"{profile['entry_id_prefix']}-{direction}-{proposal['id'][:8]}"
                amount = abs(money_minor(payload["amount_minor"]))
                entry1 = {"EntryID": entry_id, "EntryDate": date.fromisoformat(payload["business_date"]), "BankID": bank_id, "AcctID": bank_gl,
                          "OrglID": "VND", "OrglRate": 1, "OrglAmt": amount, "BaseAmt": amount,
                          "ObjectID": payload["fields"].get("counterparty") or "", "PayerID": "", "PayerText": "", "BranchID": profile["branch_id"],
                          "Memo": "", "DocsNo": payload.get("bank_reference") or "", "MRowID": "", "PeriodID": "", "ErrorText": ""}
                lines = payload.get("lines") or self._default_lines(payload, bank_gl)
                entry2 = self._entry2(entry_id, lines, payload, bank_gl, bank_id, profile)
                rows[direction].append({"proposal_id": proposal["id"], "entry1": entry1, "entry2": entry2})
            raw_thu, raw_chi = self._workbook(rows["THU"], "THU"), self._workbook(rows["CHI"], "CHI")
            identifier = uid()
            manifest = {"format": "ktt-junsky-shadow-v1", "state": "SHADOW_CHUA_NHAP", "session_id": session_id,
                        "entry1_columns": 17, "entry2_columns": 37, "mapping_hash": sha256(canonical_json(profile).encode()),
                        "proposal_ids": [row["proposal_id"] for row in rows["THU"] + rows["CHI"]],
                        "counts": {"thu": len(rows["THU"]), "chi": len(rows["CHI"]), "wait": wait}, "no_junsky_import": True}
            manifest_hash, thu_hash, chi_hash = artifact(self.store, canonical_json(manifest).encode()), artifact(self.store, raw_thu), artifact(self.store, raw_chi)
            self.db.execute("INSERT INTO shadow_exports VALUES (?,?, 'SHADOW_PREPARED',?,?,?,?,?)", (identifier, session_id, manifest_hash, thu_hash, chi_hash, at, actor))
            log(self.store, "M6", "SHADOW_JUNSKY_STRUCTURE", identifier, actor, at, manifest)
        return self.recover(identifier)

    @staticmethod
    def _default_lines(payload: dict, bank_gl: str) -> list[dict]:
        amount = abs(money_minor(payload["amount_minor"]))
        if payload["amount_minor"] > 0:
            return [{"account": bank_gl, "debit_minor": amount, "credit_minor": 0}, {"account": payload["fields"]["credit_account"], "debit_minor": 0, "credit_minor": amount}]
        return [{"account": payload["fields"]["debit_account"], "debit_minor": amount, "credit_minor": 0}, {"account": bank_gl, "debit_minor": 0, "credit_minor": amount}]

    @staticmethod
    def _entry2(entry_id: str, lines: list[dict], payload: dict, bank_gl: str, bank_id: str, profile: dict) -> list[dict]:
        result = []
        for offset, line in enumerate(lines, 1):
            if profile["entry2_mode"] == "DOI_UNG" and line["account"] == bank_gl:
                continue
            debit, credit = money_minor(line.get("debit_minor", 0)), money_minor(line.get("credit_minor", 0))
            result.append({"EntryID": entry_id, "Offset": offset, "AcctID": line["account"], "BankID": bank_id if line["account"] == bank_gl else "",
                           "OrglID": "VND", "OrglRate": 1, "OrglDeb": debit, "OrglCrd": credit, "BaseDeb": debit, "BaseCrd": credit,
                           "ObjectID": payload["fields"].get("counterparty") or "", "EntryDM": "", "CashflowID": profile["cashflow"].get(payload.get("template_id"), ""),
                           "PrecostID": "", "ProjectID": payload["fields"].get("project") or "", "CenterID": "", "CostID": payload["fields"].get("expense") or "", "Remark": "",
                           "VatID": "", "VatAcctID": "", "BaseBefVat": "", "BaseAmtVat": "", "InvName": "", "InvAddr": "", "InvCode": "", "InvForm": "", "InvSeri": "", "InvNo": "", "InvDate": "", "InvMode": "", "InvText": "", "InvLook": "", "iRow": offset, "DRowID": "", "MRowID": "", "DebtID": "", "ErrorText": ""})
        if sum(money_minor(row["BaseDeb"]) for row in result) != sum(money_minor(row["BaseCrd"]) for row in result):
            raise DataError("SHADOW_UNBALANCED", "Dòng shadow không cân Nợ/Có; không tạo file.")
        return result

    def recover(self, identifier: str) -> dict:
        row = self.db.execute("SELECT * FROM shadow_exports WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise DataError("SHADOW_NOT_FOUND", "Không thấy lần xuất shadow.")
        root = self.store.root / "shadow" / row["id"]
        thu, chi = root / "SHADOW_JUNSKY-THU.xlsx", root / "SHADOW_JUNSKY-CHI.xlsx"
        write_immutable(thu, artifact_bytes(self.store, row["thu_hash"]))
        write_immutable(chi, artifact_bytes(self.store, row["chi_hash"]))
        manifest = json.loads(artifact_bytes(self.store, row["manifest_hash"]))
        write_immutable(root / "manifest.json", canonical_json(manifest).encode())
        return {"shadow_id": row["id"], "state": "SHADOW_CHUA_NHAP", "thu": str(thu), "chi": str(chi), "manifest": str(root / "manifest.json"),
                "entry1_columns": 17, "entry2_columns": 37, "counts": manifest["counts"], "no_junsky_import": True, "fixture_only": False}

    def reconcile(self, shadow_id: str, source_attempt_id: str, actor: str, at: str) -> dict:
        """Compare a shadow proposal with a later posted-ledger snapshot.

        A matching journal supports only individually evidenced learning fields.
        It never proves a Junsky import, because this application has no import
        capability and the shadow file is deliberately marked as non-importable.
        """
        if self.store.config.environment != "that":
            raise DataError("SHADOW_THAT_ONLY", "Đối soát shadow chỉ chạy ở kho that.")
        actor, at = text_id(actor, "actor"), instant_utc(at)
        if not actor.startswith("MO_PHONG_"):
            raise DataError("SHADOW_ACTOR", "Actor đối soát shadow phải bắt đầu bằng MO_PHONG_.")
        with transaction(self.store):
            shadow = self.db.execute("SELECT * FROM shadow_exports WHERE id=?", (shadow_id,)).fetchone()
            if not shadow:
                raise DataError("SHADOW_NOT_FOUND", "Không thấy lần xuất shadow.")
            bundle = source_bundle(self.store, source_attempt_id, at)
            if bundle["manifest"].get("posting_evidence_complete") is not True or bundle["manifest"]["exported_at"] <= shadow["prepared_at"]:
                raise DataError("STALE_VERIFICATION_SOURCE", "Cần sổ đã ghi sổ, xuất sau shadow và khai đầy đủ phạm vi kiểm chứng.")
            previous = self.db.execute("SELECT * FROM shadow_verification_runs WHERE shadow_id=? AND source_hash=?", (shadow_id, bundle["hash"])).fetchone()
            if previous:
                return {"run_id": previous["id"], **json.loads(previous["report_json"]), "replayed": True}
            manifest = json.loads(artifact_bytes(self.store, shadow["manifest_hash"]))
            journals = [doc for doc in bundle["documents"] if doc["kind"] == "JOURNAL" and doc.get("source_status") in self.store.config.posted_journal_statuses]
            items, label_requests, exported_pairs = [], [], set()
            for proposal_id in manifest["proposal_ids"]:
                proposal = self.db.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
                decision = self.db.execute("SELECT * FROM decisions WHERE proposal_id=? AND action='APPROVE' ORDER BY revision DESC LIMIT 1", (proposal_id,)).fetchone()
                if not proposal or not decision:
                    continue
                payload = json.loads(decision["payload_json"])
                exported_pairs.add((payload.get("bank_reference"), payload.get("bank_account")))
                matches = [journal for journal in journals if journal.get("bank_reference") == payload.get("bank_reference") and journal.get("bank_account") == payload.get("bank_account")]
                checks = {field: False for field in ("counterparty", "debit_account", "credit_account", "project", "expense")}
                identity = money = allocations = False
                evidence, actual = [], {}
                if len(matches) == 1:
                    journal = matches[0]
                    evidence = [journal["id"]]
                    actual, amount, balanced = observed(journal)
                    identity = journal.get("bank_reference") == payload.get("bank_reference") and journal.get("bank_account") == payload.get("bank_account") and journal["business_date"] == payload["business_date"] and journal["currency"] == payload["currency"]
                    money = journal.get("complete_voucher") is True and balanced and amount == abs(money_minor(payload["amount_minor"]))
                    checks = {field: actual.get(field) is not None and actual[field] == payload["fields"].get(field) for field in checks}
                    allocations = (not payload["allocations"] and not journal.get("invoice_allocations")) or ("invoice_allocations" in journal and allocation_signature(journal["invoice_allocations"]) == allocation_signature(payload["allocations"]))
                required = set(payload.get("required_fields", ())) | {field for field, value in payload["fields"].items() if value is not None}
                posting = len(matches) == 1 and identity and money and allocations and all(checks.get(field, False) for field in required)
                status = "MATCHED" if posting else "RECON_A" if not matches else "RECON_C" if len(matches) == 1 else "UNRESOLVED"
                if len(matches) == 1 and status == "RECON_C" and (matches[0].get("complete_voucher") is not True or not matches[0].get("lines")):
                    status = "UNRESOLVED"
                items.append({"proposal_id": proposal_id, "status": status, "verified_fields": checks, "identity_verified": identity,
                              "money_verified": money, "allocations_verified": allocations, "evidence": evidence})
                if status == "MATCHED":
                    label_requests.append((document(self.store, payload["bank_id"]), actual, checks, payload["context"], evidence))
            outside = [{"journal_id": journal["id"], "status": "RECON_B", "learning_eligible": False}
                       for journal in journals if journal.get("bank_reference") and (journal.get("bank_reference"), journal.get("bank_account")) not in exported_pairs]
            report = {"shadow_id": shadow_id, "source_attempt_id": source_attempt_id, "items": items, "outside_batch": outside,
                      "complete": bool(items) and all(item["status"] == "MATCHED" for item in items), "no_junsky_import": True, "fixture_only": False}
            identifier = uid()
            learner = Learning(self.store)
            report["label_ids"] = [learner._record(bank, fields, mask, context, evidence, bundle["manifest"]["known_at"], at, actor, "SHADOW_VERIFIED_LEDGER")
                                   for bank, fields, mask, context, evidence in label_requests]
            self.db.execute("INSERT INTO shadow_verification_runs VALUES (?,?,?,?,?,?,?)", (identifier, shadow_id, source_attempt_id, bundle["hash"], at, actor, canonical_json(report)))
            log(self.store, "M6", "SHADOW_RECONCILE", shadow_id, actor, at, {"run_id": identifier, "complete": report["complete"], "labels": report["label_ids"]})
        return {"run_id": identifier, **report, "replayed": False}
