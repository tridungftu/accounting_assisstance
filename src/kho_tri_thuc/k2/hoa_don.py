"""M2 hóa đơn mua XML/ZIP — service K2 `HoaDonK2` (R15 bridge, docs/GIAO-CODE-M2-BRIDGE-01.md).

Luồng: nhận nguồn trước PN (capture `m0-capture/v1`, quyền INTAKE ở CSDL trước tra cứu; NATIVE xml|zip + CROSSWALK json tùy chọn) → máy chủ
resolve registry (profile M2/scope INVOICE_SET/mapping COMPANY hiện hành/định nghĩa đơn vị) → pure reader final `nguon/hoa_don_xml` (XML hoặc
từng entry ZIP, context theo TỪNG công ty cấu hình: XOR buyer/seller theo từng company key, không XOR toàn cục) → dòng nguồn dẫn xuất (XML_HEADER/
XML_LINE/ZIP_ENTRY, digest do CSDL tính, không byte span giả) → stage bất biến module M2 → consumer capture COMMON → consumer typed
`kho.m2_tieu_thu_quan_sat` (MUA_VAO vào M2: danh tính/phiên bản/core HD_MUA + dòng NULL tiền/Nợ/Có/quan sát; BAN_RA chỉ là ứng viên nguồn,
0 M3) → finalizer CSDL dẫn xuất kết quả cuối bất biến. Tất cả trong MỘT giao dịch trên kết nối chủ đã cấu hình.

Sau capture: 0 dòng logic/cầu nối. CFO thật (M2_MAP + V4 + SOURCE_MAP PN đích) map dòng → gốc dòng logic + mapping INVOICE_LINE + cầu nối dòng core
(`kho.m2_mapping_dong`); rồi MỘT thao tác CFO tạo+duyệt tuyến (`kho.m2_route`). Upload CROSSWALK/line-facts chỉ là bằng chứng, không cấp duyệt.
Repair02: map dòng BẮT BUỘC evidence_ref + evidence_revision của ứng viên literal đã admit (CSDL resolve + đối chiếu dòng/artifact/định danh thực
+ dòng logic); retry cùng body/token A trả biên nhận cũ (quyền hiện hành kiểm trước); registry đơn vị kiểm lại digest canonical/nghĩa trước khi
làm authority; giới hạn tải lên hữu hạn TAI_LEN_TOI_DA_BYTE.
Repair03 (R4): đơn vị chỉ làm authority khi khớp ĐỘC LẬP tuple tài liệu khai báo đã admit (bytes/raw SHA/locator/payload SHA tài liệu khai/căn cứ
nguyên văn/ngữ cảnh profile); thiếu hoặc mâu thuẫn → HOLD có mã trong `ket_qua.don_vi_khai_bao`, giữ raw, không gán hệ số.
Không số lượng còn lại/pool/L11/tiền/journal/M9 ở R15.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..ha_tang.primitives import DataError, date_iso, sha256
from ..nguon.hoa_don_xml import (LEXEME_BASIS, MEDIA_XML, CompanyFact, InvoiceMeasurementFacts, InvoiceReadContext, XmlRawRef,
                                 doc_goi_hoa_don_zip, doc_hoa_don_xml)
from . import nguon_chung, quyen

MODULE = "M2"
VAI_TRO_NATIVE, VAI_TRO_CROSSWALK = "NATIVE", "CROSSWALK"
MEDIA_ZIP, MEDIA_JSON = "application/zip", "application/json"
DICH = ("CHI_PHI", "XDCB_241", "TAI_SAN", "KHO")
L11_THONG_BAO = ("Liên kết số lượng hóa đơn ↔ phiếu kho (L11 R16, hai pool) thực hiện ở trang 'Liên kết số lượng' (cần quyền xem CẢ M2 và M5); "
                 "tuyến KHO chỉ là căn cứ định tuyến, không phải ghi nhận tồn/tiền.")
# Giới hạn hữu hạn mỗi lần nhận (NATIVE + CROSSWALK, bytes thật): base64 (4/3) + trường JSON vẫn dưới thân JSON 1 MiB của máy chủ. Không suy
# hỗ trợ tệp lớn từ giới hạn của pure reader.
TAI_LEN_TOI_DA_BYTE = 700_000
_DON_VI_NGHIA = ("reference_id", "scope", "native_unit_code", "definition_kind", "meaning", "label", "authority")


def _hom_nay_vn() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


def _s(v):
    return None if v is None else str(v)


def _occ(f) -> list[dict]:
    return [o.ra_dict() for o in f.occurrences]


def _duy_nhat_text(f) -> str | None:
    fv = f.duy_nhat
    return fv.lexeme if fv is not None and fv.state == "TEXT" else None


def _so(df) -> dict:
    return {"state": df.state, "exact_text": df.exact_text, "lexical_digits": df.lexical_digits, "scale": df.scale}


def _ma(issues) -> list[str]:
    return sorted({i.code for i in issues})


def _trang_thai(issues, mo_ho=False) -> str:
    if mo_ho:
        return "MO_HO"
    return "LOI" if any(i.severity == "ERROR" for i in issues) else "HOP_LE"


class HoaDonK2:
    def __init__(self, conn, root: Path, *, conn_chu=None, chi_mo_phong: bool = True, hom_nay=None):
        """conn: login ứng dụng (app_web, dict_row, autocommit) cho mọi route đọc/thao tác CFO qua hàm định nghĩa; conn_chu: kết nối CHỦ BẢNG
        đã cấu hình (cùng endpoint, kiểm owner) — CHỈ cho capture (stage bất biến + consumer trong một giao dịch)."""
        from psycopg.types.string import StrDumperUnknown
        self.conn, self.root, self.chi_mo_phong, self.conn_chu = conn, Path(root), chi_mo_phong, conn_chu
        self.hom_nay = hom_nay or _hom_nay_vn
        conn.adapters.register_dumper(str, StrDumperUnknown)
        if conn_chu is not None:
            conn_chu.adapters.register_dumper(str, StrDumperUnknown)

    # ------------------------------------------------------------------ hạ tầng phiên/giao dịch (cùng mẫu M5)
    def danh_tinh(self, dang_nhap: str) -> dict:
        return quyen.nap_danh_tinh(self.conn, dang_nhap, chi_mo_phong=self.chi_mo_phong)

    def _gan(self, conn, dt):
        return conn.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                            "set_config('ktt.ngay_hieu_luc', %s, true), master.ktt_danh_tinh() AS ai",
                            (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat())).fetchone()

    @contextmanager
    def _tx(self, dt):
        with self.conn.transaction():
            self._gan(self.conn, dt)
            yield

    @contextmanager
    def _tx_doc(self, dt):
        """Snapshot đọc nhất quán (REPEATABLE READ, READ ONLY) đặt bằng statement ĐẦU TIÊN; giao dịch ngoài đang mở → từ chối (không hạ cấp)."""
        from psycopg import pq
        if self.conn.info.transaction_status != pq.TransactionStatus.IDLE:
            raise DataError("M2_DOC_NHAT_QUAN", "Không mở được snapshot đọc nhất quán trong một giao dịch đang mở — thử lại.")
        with self.conn.transaction():
            self.conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            self._gan(self.conn, dt)
            yield

    @contextmanager
    def _tx_chu(self, dt):
        if self.conn_chu is None:
            raise DataError("M2_CHU_CHUA_CAU_HINH", "Chưa cấu hình kết nối máy chủ (chủ bảng) cho nhận nguồn M2 — mở lại bằng nút MỞ BẢN DEMO.")
        with self.conn_chu.transaction():
            row = self._gan(self.conn_chu, dt)
            if (row["ai"] if isinstance(row, dict) else row[3]) != dt["dang_nhap"]:
                raise DataError("DANH_TINH", "Danh tính phiên không còn hoạt động (ID + login).")
            yield self.conn_chu

    # ------------------------------------------------------------------ registry phía máy chủ (không từ trình duyệt)
    @staticmethod
    def _cong_ty(c, inst, profile, keys) -> tuple[dict, list[dict]]:
        """Mapping COMPANY hiện hành theo từng company key của scope: đúng MỘT → CompanyFact; 0/nhiều → HOLD (không chọn PN tùy ý)."""
        rows = c.execute("""SELECT m.id, m.reference_id, m.revision, m.subject_key, m.phap_nhan_id, p.ma FROM master.anh_xa_nguon m
                            JOIN master.phap_nhan p ON p.id = m.phap_nhan_id
                            WHERE m.source_instance_id = %s AND m.profile_ref = %s AND m.profile_sha256 = %s AND m.subject_kind = 'COMPANY'
                              AND m.subject_key = ANY(%s) AND m.state = 'DA_DUYET' AND m.valid_from <= now() AND (m.valid_to IS NULL OR m.valid_to > now())""",
                         (inst, profile["reference_id"], profile["sha256"], list(keys))).fetchall()
        theo, hold = {}, []
        for r in rows:
            theo.setdefault(r["subject_key"], []).append(r)
        out = {}
        for k in sorted(keys):
            ds = theo.get(k, [])
            if len(ds) != 1:
                hold.append({"company_key": k, "state": "HOLD", "reason": "PN_MAPPING_CONFLICT" if ds else "PN_MAPPING_ABSENT"})
                continue
            r = ds[0]
            out[k] = {"fact": CompanyFact(k, r["ma"], r["reference_id"], r["revision"], f"COMPANY:{k}"), "mapping_id": str(r["id"]),
                      "phap_nhan_id": str(r["phap_nhan_id"])}
        return out, hold

    @staticmethod
    def kiem_don_vi_khai_bao(unit: dict, doc: dict | None, inst: str, profile_ref: str, profile_sha: str) -> str | None:
        """R4 repair03 — kiểm ĐỘC LẬP phía dịch vụ (cùng quy tắc với master.don_vi_khop_khai_bao): giá trị kỳ vọng lấy từ BYTES tài liệu khai báo
        đã admit (không từ chính hàng đơn vị): payload tại locator, payload SHA tài liệu khai (`definition_payload_sha256`) = canonical tự tính,
        reference/scope, căn cứ nguyên văn, ngữ cảnh instance/profile hỗ trợ = profile hiện hành. Trả None khi khớp, ngược lại mã HOLD."""
        p = unit.get("payload")
        if not isinstance(p, dict) or nguon_chung.digest_payload(p) != unit.get("definition_sha256"):
            return "DON_VI_DIGEST_SAI"
        if not all(isinstance(p.get(k), str) and p.get(k) for k in _DON_VI_NGHIA) or isinstance(p.get("version"), bool) \
                or not isinstance(p.get("version"), int):
            return "DON_VI_NGHIA_THIEU"
        if doc is None:
            return "DON_VI_TAI_LIEU_KHONG_CO"
        raw = bytes(doc["noi_dung"])
        if doc["raw_sha256"] != unit.get("declaration_raw_sha256") or sha256(raw) != doc["raw_sha256"] or len(raw) != doc["byte_length"]:
            return "DON_VI_TAI_LIEU_SAI_HASH"
        try:
            tl = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return "DON_VI_TAI_LIEU_KHONG_DOC_DUOC"
        loc = unit.get("declaration_locator") or ""
        seg = loc[1:].split("/") if loc.startswith("/") else []
        if not seg or not all(s and all(ch.isascii() and (ch.isalnum() or ch == "_") for ch in s) for s in seg):
            return "DON_VI_VI_TRI_KHONG_CO"
        cha, sub = None, tl
        for s in seg:
            cha = sub
            if isinstance(sub, dict) and s in sub:
                sub = sub[s]
            elif isinstance(sub, list) and s.isdigit() and int(s) < len(sub):
                sub = sub[int(s)]
            else:
                return "DON_VI_VI_TRI_KHONG_CO"
        if not isinstance(sub, dict):
            return "DON_VI_VI_TRI_KHONG_CO"
        if nguon_chung.digest_payload(sub) != nguon_chung.digest_payload(p):
            return "DON_VI_KHONG_KHOP_TAI_LIEU"
        h = nguon_chung.digest_payload(sub)
        if not isinstance(cha, dict) or cha.get("definition_payload_sha256") != h or unit.get("definition_sha256") != h:
            return "DON_VI_DIGEST_SAI"
        if unit.get("reference_id") != sub.get("reference_id") or ("reference_id" in cha and cha["reference_id"] != unit.get("reference_id")) \
                or unit.get("declared_scope") != sub.get("scope"):
            return "DON_VI_KHONG_KHOP_TAI_LIEU"
        can_cu = cha["source_basis_ref"] if "source_basis_ref" in cha else doc["source_basis_ref"]
        if not isinstance(can_cu, str) or unit.get("source_basis_ref") != can_cu:
            return "DON_VI_CAN_CU_SAI"
        if isinstance(tl, dict) and any(k in tl and tl[k] != v for k, v in (("source_instance", unit.get("support_source_instance_id")),
                                                                             ("profile_ref", unit.get("support_profile_ref")),
                                                                             ("profile_payload_sha256", unit.get("support_profile_sha256")))):
            return "DON_VI_PHAM_VI_SAI"
        if (unit.get("support_source_instance_id"), unit.get("support_profile_ref"), unit.get("support_profile_sha256")) != (inst, profile_ref, profile_sha):
            return "DON_VI_NGOAI_PHAM_VI"
        return None

    @classmethod
    def _don_vi(cls, c, inst, profile) -> tuple[InvoiceMeasurementFacts | None, str | None]:
        """Fact đơn vị cho pure context. Thiếu/mâu thuẫn tuple khai báo → (None, mã HOLD): dòng giữ raw, số chuẩn hóa NULL/UNIT_UNPROVEN,
        lý do ghi rõ trong kết quả — không gán hệ số, không chặn capture raw."""
        payload = profile["payload"]
        uf, qe = payload.get("unit_fact") or {}, payload.get("quantity_encoding") or {}
        row = c.execute("""SELECT reference_id, payload, definition_sha256, declared_scope, source_basis_ref, declaration_ref, declaration_raw_sha256,
                                  declaration_locator, support_source_instance_id, support_profile_ref, support_profile_sha256
                           FROM master.dinh_nghia_don_vi_luong WHERE reference_id = %s""", (uf.get("canonical_definition_ref"),)).fetchone()
        if row is None:
            return None, "DON_VI_CHUA_KHAI_BAO"
        doc = c.execute("SELECT raw_sha256, byte_length, noi_dung, source_basis_ref FROM master.tai_lieu_khai_bao_don_vi WHERE reference_id = %s",
                        (row["declaration_ref"],)).fetchone()
        loi = cls.kiem_don_vi_khai_bao(dict(row), None if doc is None else dict(doc), inst, profile["reference_id"], profile["sha256"])
        if loi is not None:
            return None, loi
        return InvoiceMeasurementFacts(encoding_ref=qe["ref"], unit_definition_ref=row["reference_id"],
                                       profile_document_sha256=payload["profile_document_sha256"], raw_unit=uf["raw_unit"],
                                       canonical_unit=row["payload"]["native_unit_code"], numerator_text=uf["numerator_text"],
                                       denominator_text=uf["denominator_text"], max_lexical_digits=qe["max_lexical_digits"], max_scale=qe["max_scale"],
                                       declared_encoding_kind=qe["kind"]), None

    @staticmethod
    def _context(inst, profile, ref: XmlRawRef, company: CompanyFact | None, facts) -> InvoiceReadContext:
        p = profile["payload"]
        return InvoiceReadContext(source_instance=inst, source_profile_ref=profile["reference_id"], profile_document_sha256=p["profile_document_sha256"],
                                  profile_payload_sha256=profile["sha256"], profile_payload_binding="BOUND_REGISTRY_PAYLOAD", company=company,
                                  identity_profile_ref=p["identity_profile"]["ref"], expected_raw_ref=ref, resolved_invoice_measurement_facts=facts)

    # ------------------------------------------------------------------ dựng dòng nguồn dẫn xuất + kế hoạch promote
    @staticmethod
    def _dong_xml(res, *, prefix, artifact_sha, zip_meta) -> list[dict]:
        """XML_HEADER (1/kết quả XML) + XML_LINE (1/dòng thực). Không span/raw-row hash: basis decoded field states, digest do CSDL tính."""
        ref = res.raw_ref
        base = {"artifact_sha256": artifact_sha, "native_xml_sha256": ref.native_sha256, "byte_length": ref.byte_length, **zip_meta,
                "lexeme_basis": LEXEME_BASIS, "row_byte_span": None}
        hdr_loc = prefix + "/HDon"
        rows = [{"vai_tro": VAI_TRO_NATIVE, "section": "XML_HEADER", "locator": hdr_loc, "source_key": None, "hash_basis": "XML_DECODED_FIELD_STATES",
                 "quantity_json_kind": None, "quantity_text": None, "validation_state": _trang_thai(res.issues), "error_codes": _ma(res.issues),
                 "row_raw": {**base, "shape": res.shape, "header": {f.name: _occ(f) for f in res.header_fields},
                             "header_total_section": res.header_total_section.ra_dict(), "issues": _ma(res.issues)}}]
        for ln in res.lines:
            fd = {f.name: f for f in ln.fields}
            mo_ho = any(len(f.occurrences) > 1 or f.mixed_content for f in ln.fields)
            rows.append({"vai_tro": VAI_TRO_NATIVE, "section": "XML_LINE", "locator": prefix + ln.source_locator, "source_key": None,
                         "hash_basis": "XML_DECODED_FIELD_STATES", "quantity_json_kind": None, "quantity_text": None,
                         "validation_state": _trang_thai(ln.issues, mo_ho), "error_codes": _ma(ln.issues),
                         "row_raw": {**base, "header_locator": hdr_loc, "source_ordinal": ln.source_ordinal, "source_locator": ln.source_locator,
                                     "fields": {n: _occ(f) for n, f in fd.items()}, "quantity": _so(ln.quantity), "unit_price": _so(ln.unit_price),
                                     "amount": _so(ln.source_amount), "nature": ln.nature, "nature_raw": _duy_nhat_text(fd["TChat"]),
                                     "quantity_raw": _duy_nhat_text(fd["SLuong"]), "unit_raw": _duy_nhat_text(fd["DVTinh"]),
                                     "unitprice_raw": _duy_nhat_text(fd["DGia"]), "amount_raw": _duy_nhat_text(fd["ThTien"]),
                                     "normalized_quantity_text": ln.normalized_quantity_text, "unit_definition_ref": ln.unit_definition_ref,
                                     "issues": _ma(ln.issues)}})
        return rows

    @staticmethod
    def _ngay_tien(res) -> tuple[str | None, str | None]:
        ngay = _duy_nhat_text(res.header("NLap")) if res.header_fields else None
        try:
            ngay = date_iso(ngay) if ngay is not None else None
        except DataError:
            ngay = None
        tien = _duy_nhat_text(res.header("DVTTe")) if res.header_fields else None
        return ngay, tien

    def _ke_hoach(self, delivery_key, prefix, zip_meta, theo_cong_ty: dict, cong_ty: dict) -> tuple[list[dict], list[dict]]:
        """Một delivery: MUA_VAO đủ identity/content/ngày/tiền tệ → kế hoạch M2; BAN_RA → ứng viên nguồn (0 M3); cả hai phía/thiếu → HOLD."""
        plans, cands = [], []
        mua = []
        for key, res in sorted(theo_cong_ty.items()):
            codes = {i.code for i in res.issues}
            if "COMPANY_BOTH_SIDES" in codes:
                cands.append({"delivery_key": delivery_key, "company_key": key, "state": "HOLD", "reason": "COMPANY_BOTH_SIDES"})
                continue
            if res.canonical_identity is None:
                continue  # công ty không xuất hiện (COMPANY_UNMATCHED) hoặc định danh chưa đủ — không suy
            if res.canonical_identity[1] == "BAN_RA":
                cands.append({"delivery_key": delivery_key, "company_key": key, "state": "SOURCE_CANDIDATE", "direction": "BAN_RA",
                              "reason": "BAN_RA_NO_M2_NO_M3_PROMOTION_R15", "identity": list(res.canonical_identity)})
                continue
            mua.append((key, res))
        if len(mua) > 1:
            cands.append({"delivery_key": delivery_key, "state": "HOLD", "reason": "MULTIPLE_BUYER_COMPANIES"})
            return plans, cands
        for key, res in mua:
            ngay, tien = self._ngay_tien(res)
            if res.semantic_digest is None or ngay is None or tien is None:
                cands.append({"delivery_key": delivery_key, "company_key": key, "state": "HOLD", "identity": list(res.canonical_identity),
                              "reason": "CONTENT_OR_DATE_OR_CURRENCY_UNRESOLVED", "issues": _ma(res.issues)})
                continue
            env = res.semantic_envelope.ra_dict()
            lines = []
            for ln in res.lines:
                fd = {f.name: f for f in ln.fields}
                lines.append({"source_ordinal": ln.source_ordinal, "locator": prefix + ln.source_locator, "mo_ta": _duy_nhat_text(fd["THHDVu"]),
                              "so_luong_chuan_hoa": ln.normalized_quantity_text, "quantity_raw": _duy_nhat_text(fd["SLuong"]),
                              "unit_raw": _duy_nhat_text(fd["DVTinh"]), "nature": ln.nature})
            plans.append({"delivery_key": delivery_key, "header_locator": prefix + "/HDon", "native_xml_sha256": res.raw_ref.native_sha256,
                          **zip_meta, "company_key": key, "company_mapping_id": cong_ty[key]["mapping_id"], "direction": "MUA_VAO",
                          "identity": list(res.canonical_identity), "semantic_sha256": res.semantic_digest, "raw_header_states": env["header"],
                          "ngay_lap": ngay, "tien_te": tien,
                          "raw_components": {"lines": [{"source_ordinal": l["source_ordinal"], **{k: v for k, v in l["fields"].items()
                                                                                               if k in ("DGia", "ThTien", "TSuat")}} for l in env["lines"]],
                                             "basis": "RAW_DECODED_STATES_NO_MINOR_NO_TOTAL_CHECK"},
                          "issue_codes": _ma(res.issues), "lines": lines, "line_locators": [l["locator"] for l in lines]})
        return plans, cands

    def _doc_nguon(self, c, inst, profile, scope, native: bytes, media: str, crosswalk: bytes | None, coverage: str):
        cong_ty, hold_cty = self._cong_ty(c, inst, profile, scope["company_keys"])
        facts, don_vi_hold = self._don_vi(c, inst, profile)
        art_sha = sha256(native)
        rows, plans, cands = [], [], list(hold_cty)
        partial = False
        issues = []
        if media == MEDIA_XML:
            ref = XmlRawRef(art_sha, len(native), MEDIA_XML)
            base = doc_hoa_don_xml(native, self._context(inst, profile, ref, None, facts))
            meta = {"container_sha256": None, "entry_ordinal": None, "entry_name": None}
            rows += self._dong_xml(base, prefix="", artifact_sha=art_sha, zip_meta=meta)
            issues = _ma(base.issues)
            theo = {k: doc_hoa_don_xml(native, self._context(inst, profile, ref, v["fact"], facts)) for k, v in cong_ty.items()}
            p, cd = self._ke_hoach("XML", "", meta, theo, cong_ty)
            plans += p
            cands += cd
            kind = "XML"
        else:
            inv = doc_goi_hoa_don_zip(native)
            issues = _ma(inv.issues)
            partial = inv.artifact_coverage == "PARTIAL"
            slots = [(e.entry_ordinal, e.entry_name, XmlRawRef(e.raw_sha256, e.byte_length, MEDIA_XML, inv.container_sha256, e.entry_ordinal, e.entry_name))
                     for e in inv.entries if e.raw_sha256 is not None and e.result is not None]
            base = doc_goi_hoa_don_zip(native, tuple(self._context(inst, profile, r, None, facts) for _, _, r in slots))
            theo_zip = {k: doc_goi_hoa_don_zip(native, tuple(self._context(inst, profile, r, v["fact"], facts) for _, _, r in slots))
                        for k, v in cong_ty.items()}
            for e in base.entries:
                loc = f"zip!{e.entry_ordinal}:{e.entry_name}"
                rows.append({"vai_tro": VAI_TRO_NATIVE, "section": "ZIP_ENTRY", "locator": loc, "source_key": None, "hash_basis": "ZIP_ENTRY_INVENTORY",
                             "quantity_json_kind": None, "quantity_text": None,
                             "validation_state": "HOP_LE" if e.state == "PARSED" else "LOI", "error_codes": _ma(e.issues),
                             "row_raw": {"artifact_sha256": art_sha, "container_sha256": inv.container_sha256, "entry_ordinal": e.entry_ordinal,
                                         "entry_name": e.entry_name, "member_sha256": e.raw_sha256, "byte_length": e.byte_length, "read_state": e.state,
                                         "issues": _ma(e.issues), "row_byte_span": None}})
                if e.result is None:
                    continue  # non-XML/không đọc được: chỉ inventory, không dựng field giả
                meta = {"container_sha256": inv.container_sha256, "entry_ordinal": e.entry_ordinal, "entry_name": e.entry_name}
                rows += self._dong_xml(e.result, prefix=loc + "#", artifact_sha=art_sha, zip_meta=meta)
                theo = {k: z.entries[e.entry_ordinal - 1].result for k, z in theo_zip.items() if z.entries[e.entry_ordinal - 1].result is not None}
                p, cd = self._ke_hoach(f"ZIP_ENTRY:{e.entry_ordinal}", loc + "#", meta, theo, cong_ty)
                plans += p
                cands += cd
            kind = "ZIP"
        if crosswalk is not None:
            try:
                cw = json.loads(crosswalk.decode("utf-8"))
                n, parse = (len(cw.get("rows", [])) if isinstance(cw, dict) and isinstance(cw.get("rows"), list) else None), "JSON_OK"
            except (UnicodeDecodeError, ValueError):
                n, parse = None, "JSON_INVALID"
            rows.append({"vai_tro": VAI_TRO_CROSSWALK, "section": "CROSSWALK", "locator": "/crosswalk", "source_key": None,
                         "hash_basis": "CROSSWALK_METADATA", "quantity_json_kind": None, "quantity_text": None,
                         "validation_state": "HOP_LE" if parse == "JSON_OK" else "LOI", "error_codes": [] if parse == "JSON_OK" else ["CROSSWALK_JSON_INVALID"],
                         "row_raw": {"artifact_sha256": sha256(crosswalk), "byte_length": len(crosswalk), "parse": parse, "record_count": n,
                                     "authority": "RAW_EVIDENCE_ONLY_NOT_APPROVED_MAPPING", "row_byte_span": None}})
        for i, r in enumerate(rows):
            r["thu_tu"] = i
        cov_hl = "PARTIAL_INPUT" if (partial or coverage == "PARTIAL_INPUT") else coverage
        ket_qua = {"module": MODULE, "artifact_kind": kind, "artifact_sha256": art_sha, "so_dong_nguon": len(rows), "so_ke_hoach_m2": len(plans),
                   "ung_vien": cands, "issues": issues, "coverage_hieu_luc": cov_hl, "period_completeness": "UNKNOWN",
                   "native_fiscal_status": "UNKNOWN", "logical_bridges_created": 0,
                   "don_vi_khai_bao": {"state": "BOUND" if don_vi_hold is None else "HOLD", "reason": don_vi_hold}}
        return rows, plans, cands, cov_hl, ket_qua

    # ------------------------------------------------------------------ POST /api/m2/nhan
    def nhan(self, actor: str, *, source_instance: str, scope_ref: str, coverage: str, reported_errors=nguon_chung.VANG, client_key: str,
             native: bytes, artifact_name: str | None = None, crosswalk: bytes | None = None) -> dict:
        dt = self.danh_tinh(actor)
        nguon_chung.kiem_khoa(client_key)
        if not isinstance(source_instance, str) or not source_instance or not isinstance(scope_ref, str) or not scope_ref:
            raise DataError("NGUON_PHAM_VI", "Cần instance nguồn và phạm vi cấu hình trong registry.")
        if not isinstance(native, (bytes, bytearray)) or not native:
            raise DataError("NGUON_ARTIFACT", "Cần bytes thực của tệp NATIVE (XML hoặc ZIP).")
        if crosswalk is not None and not isinstance(crosswalk, (bytes, bytearray)):
            raise DataError("NGUON_ARTIFACT", "CROSSWALK phải là bytes thực.")
        if artifact_name is not None and not isinstance(artifact_name, str):
            raise DataError("NGUON_ARTIFACT", "Tên tệp chỉ là metadata chuỗi.")
        native = bytes(native)
        crosswalk = None if crosswalk is None else bytes(crosswalk)
        if len(native) + len(crosswalk or b"") > TAI_LEN_TOI_DA_BYTE:
            raise DataError("M2_TEP_QUA_LON", f"Tổng tệp hóa đơn + crosswalk tối đa {TAI_LEN_TOI_DA_BYTE} byte mỗi lần nhận.")
        loi_bao = nguon_chung.kiem_ma_loi(reported_errors)
        media = MEDIA_ZIP if native[:4] == b"PK\x03\x04" else MEDIA_XML  # theo bytes thực, không theo tên tệp
        with self._tx_chu(dt) as c:
            profile = nguon_chung.doc_profile(c, source_instance)
            if profile["payload"].get("module") != MODULE:
                raise DataError("NGUON_PROFILE", "Instance nguồn không phải profile hóa đơn M2.")
            quyen.kiem_nguon(c, source_instance, profile["reference_id"], profile["sha256"], "INTAKE")
            cu = nguon_chung.tim_lan_nhan(c, source_instance, profile, client_key)
            scope = nguon_chung.doc_pham_vi(c, source_instance, profile, scope_ref)
            if scope["scope_kind"] != "INVOICE_SET":
                raise DataError("NGUON_PHAM_VI", "Phạm vi không phải INVOICE_SET của M2.")
            arts = nguon_chung.artifacts(profile, {VAI_TRO_NATIVE: native, VAI_TRO_CROSSWALK: crosswalk},
                                         {VAI_TRO_NATIVE: media, VAI_TRO_CROSSWALK: MEDIA_JSON})
            env = nguon_chung.phong_bi_capture(source_instance, profile, scope, coverage, loi_bao, arts)
            h = nguon_chung.bam_capture(env)
            if cu is not None:
                if cu["capture_sha256"] != h:
                    raise DataError("CAPTURE_KHAC_NOI_DUNG", "Khóa capture đã dùng cho bytes/profile/scope/coverage/lỗi khác — không ghi artifact mới.")
                return self._phat_lai(cu, h)
            for a in arts:
                if a["co_mat"]:
                    nguon_chung.ghi_blob(self.root, a["raw"])
            rows, plans, cands, cov_hl, ket_qua = self._doc_nguon(c, source_instance, profile, scope, native, media, crosswalk, coverage)
            ket_qua.update(coverage=coverage, artifact_name=artifact_name)
            receipt_id = nguon_chung.receipt_id_moi()
            du = nguon_chung.du_lieu_stage_capture(receipt_id=receipt_id, scope=scope, coverage=coverage, coverage_hl=cov_hl, envelope=env, arts=arts,
                                                   rows=rows, ket_qua=ket_qua, promote=None)
            du.update(module=MODULE, promote_m2=plans, candidates_m2=cands)
            stage = nguon_chung.ghi_stage(c, dt, muc_dich="CAPTURE", client_key=client_key, h=h, source_instance=source_instance,
                                          profile_ref=profile["reference_id"], profile_sha256=profile["sha256"], du_lieu=du, module=MODULE)
            ghi = nguon_chung.tieu_thu_capture(c, stage, h)
            if not ghi["moi"]:
                cu = nguon_chung.tim_lan_nhan(c, source_instance, profile, client_key)
                if cu is None or cu["capture_sha256"] != h:
                    raise DataError("CAPTURE_KHAC_NOI_DUNG", "Khóa capture đã dùng cho nội dung khác.")
                return self._phat_lai(cu, h)
            c.execute("SELECT kho.m2_tieu_thu_quan_sat(%s::uuid, %s) AS v", (stage, h)).fetchone()
            cuoi = nguon_chung.chot_ket_qua(c, stage, h, bool(ghi["snapshot_moi"]), {"module": MODULE})
        return {**ket_qua, "lan_tiep_nhan_id": receipt_id, "capture_sha256": h, "lap_lai": False, **cuoi}

    @staticmethod
    def _phat_lai(cu: dict, h: str) -> dict:
        cuoi = cu.get("ket_qua_cuoi")
        if not isinstance(cuoi, dict) or set(cuoi) != {"stage_id", "snapshot_moi", "promote"}:
            raise DataError("KET_QUA_CUOI_THIEU", "Lần nhận đã có biên nhận nhưng thiếu kết quả cuối đã chốt — giữ nguyên, không tính lại.")
        return {**cu["ket_qua"], "lan_tiep_nhan_id": str(cu["id"]), "capture_sha256": h, "lap_lai": True,
                "stage_id": str(cuoi["stage_id"]), "snapshot_moi": cuoi["snapshot_moi"], "promote": cuoi["promote"]}

    # ------------------------------------------------------------------ nguồn (trước PN): danh sách / chi tiết / raw — quyền nguồn hiện hành
    def _instances_m2(self) -> set:
        return {r["source_instance_id"] for r in self.conn.execute("SELECT source_instance_id FROM master.nguon_profile WHERE payload->>'module' = 'M2'")}

    def nguon_danh_sach(self, actor) -> list[dict]:
        dt = self.danh_tinh(actor)
        with self._tx(dt):
            inst = self._instances_m2()
            return [r for r in nguon_chung.danh_sach_lan_nhan(self.conn) if r.get("source_instance_id") in inst]

    def nguon_chi_tiet(self, actor, receipt_id) -> dict:
        dt = self.danh_tinh(actor)
        with self._tx(dt):
            v = nguon_chung.doc_lan_nhan(self.conn, receipt_id)
            inst = self._instances_m2()
        if v is None or v.get("source_instance_id") not in inst:
            raise DataError("NGUON_KHONG_CO_QUYEN", "Không thấy lần nhận này hoặc phiên chưa có READ_SOURCE của nguồn.")
        return v

    def nguon_raw(self, actor, receipt_id, vai_tro) -> tuple[str, bytes]:
        dt = self.danh_tinh(actor)
        if vai_tro not in (VAI_TRO_NATIVE, VAI_TRO_CROSSWALK):
            raise DataError("NGUON_VAI_TRO_LA", "Vai trò artifact không hợp lệ.")
        with self._tx(dt):
            meta, raw = nguon_chung.doc_tep(self.conn, self.root, receipt_id, vai_tro)
        duoi = {"application/zip": "zip", "application/json": "json"}.get(meta["media_type"], "xml")
        return f"{vai_tro}-{meta['raw_sha256'][:12]}.{duoi}", raw

    def nang_luc_cua_toi(self, actor) -> list[dict]:
        dt = self.danh_tinh(actor)
        with self._tx(dt):
            return [dict(r) for r in self.conn.execute("""SELECT c.source_instance_id, c.profile_ref, c.hanh_dong, p.ma AS phap_nhan_dich
                                                          FROM master.nang_luc_nguon c LEFT JOIN master.phap_nhan p ON p.id = c.target_phap_nhan_id
                                                          JOIN master.nguon_profile np ON np.source_instance_id = c.source_instance_id
                                                           AND np.profile_ref = c.profile_ref AND np.profile_sha256 = c.profile_sha256
                                                          WHERE np.payload->>'module' = 'M2' ORDER BY 1, 3, 4""")]

    def pham_vi_cua_toi(self, actor) -> list[dict]:
        dt = self.danh_tinh(actor)
        with self._tx(dt):
            return [{"source_instance_id": r["source_instance_id"], "scope_ref": r["scope_ref"], "company_keys": list(r["company_keys"] or []),
                     "coverage_values": list(r["payload"].get("coverage_values") or [])}
                    for r in self.conn.execute("""SELECT s.source_instance_id, s.scope_ref, s.company_keys, p.payload FROM master.nguon_pham_vi s
                                                  JOIN master.nguon_profile p ON p.source_instance_id = s.source_instance_id AND p.profile_ref = s.profile_ref
                                                   AND p.profile_sha256 = s.profile_sha256 WHERE s.scope_kind = 'INVOICE_SET' ORDER BY 1, 2""")]

    # ------------------------------------------------------------------ nghiệp vụ M2: danh sách / chi tiết (snapshot nhất quán + token đồ thị)
    def _nguoi(self, dt) -> dict:
        return {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"],
                "phap_nhan": sorted(dt["quyen"][pn]["ma"] for pn in quyen.pham_vi(dt, "M2_READ")),
                "hanh_dong": sorted(h for h in ("M2_READ", "M2_MAP", "M2_ROUTE", "M2_SOURCE_REVIEW") if quyen.pham_vi(dt, h))}

    def danh_sach(self, actor, *, phap_nhan=None, ky=None, trang=1, co=50) -> dict:
        dt = self.danh_tinh(actor)
        pns = quyen.pham_vi(dt, "M2_READ")
        if not pns:
            raise DataError("KHONG_CO_QUYEN_MODULE", "Người dùng không có quyền xem M2 trên pháp nhân nào.")
        if ky is not None and (not isinstance(ky, str) or len(ky) != 7 or ky[4] != "-"):
            raise DataError("LOC_KY", "Kỳ phải dạng YYYY-MM.")
        trang, co = max(1, int(trang)), min(100, max(1, int(co)))
        with self._tx_doc(dt):
            rows = [dict(r) for r in self.conn.execute(
                """SELECT d.id, p.ma AS phap_nhan, d.chieu, d.mst_ban, d.mau_so, d.ky_hieu, d.so_chuan, d.latest_observation_id,
                          d.accepted_source_observation_id, d.eligible_content_id, v.ngay_lap, v.phien_ban, o.classification,
                          (SELECT count(*) FROM kho.hoa_don_quan_sat x WHERE x.hoa_don_id = d.id) AS so_quan_sat,
                          (SELECT count(*) FROM kho.hoa_don_phien_ban x WHERE x.hoa_don_id = d.id) AS so_phien_ban, count(*) OVER () AS tong
                   FROM kho.hoa_don_danh_tinh d JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
                   LEFT JOIN kho.hoa_don_quan_sat o ON o.id = d.latest_observation_id
                   LEFT JOIN kho.hoa_don_phien_ban v ON v.id = o.phien_ban_id
                   WHERE d.phap_nhan_id = ANY(%s::uuid[]) AND (%s::text IS NULL OR p.ma = %s::text)
                     AND (%s::text IS NULL OR to_char(v.ngay_lap, 'YYYY-MM') = %s::text)
                   ORDER BY v.ngay_lap DESC NULLS LAST, d.ky_hieu, d.so_chuan, d.id LIMIT %s OFFSET %s""",
                (pns, phap_nhan, phap_nhan, ky, ky, co, (trang - 1) * co))]
        hd = [{"id": str(r["id"]), "phap_nhan": r["phap_nhan"], "chieu": r["chieu"], "mst_ban": r["mst_ban"], "mau_so": r["mau_so"], "ky_hieu": r["ky_hieu"],
               "so_chuan": r["so_chuan"], "ngay_lap": r["ngay_lap"].isoformat() if r["ngay_lap"] else None, "phien_ban": r["phien_ban"],
               "phan_loai": list(r["classification"] or []), "latest_observation_id": _s(r["latest_observation_id"]),
               "accepted_source_observation_id": _s(r["accepted_source_observation_id"]), "eligible_content_id": _s(r["eligible_content_id"]),
               "so_quan_sat": r["so_quan_sat"], "so_phien_ban": r["so_phien_ban"]} for r in rows]
        return {"nguoi": self._nguoi(dt), "hoa_don": hd, "trang": trang, "co": co, "tong": rows[0]["tong"] if rows else 0, "l11": L11_THONG_BAO}

    def chi_tiet(self, actor, hoa_don_id) -> dict:
        """Display graph + token đồ thị OP từ CÙNG một snapshot; quyền/basis hiện hành vẫn kiểm lại tại lúc thao tác (CSDL)."""
        dt = self.danh_tinh(actor)
        with self._tx_doc(dt):
            d = self.conn.execute("""SELECT d.*, p.ma AS phap_nhan FROM kho.hoa_don_danh_tinh d JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
                                     WHERE d.id = %s""", (hoa_don_id,)).fetchone()
            if not d:
                raise DataError("HOA_DON", "Không thấy hóa đơn (hoặc ngoài quyền).")
            quyen.kiem(dt, "M2_READ", d["phap_nhan_id"])
            pbs = [dict(v) for v in self.conn.execute("SELECT * FROM kho.hoa_don_phien_ban WHERE hoa_don_id = %s ORDER BY phien_ban", (hoa_don_id,))]
            dong_core = [dict(r) for r in self.conn.execute(
                """SELECT x.id, x.chung_tu_id, x.stt, x.mo_ta, x.so_luong::text AS so_luong, x.no_minor, x.co_minor, x.du_lieu FROM kho.chung_tu_dong x
                   WHERE x.chung_tu_id IN (SELECT v.chung_tu_id FROM kho.hoa_don_phien_ban v WHERE v.hoa_don_id = %s) ORDER BY x.chung_tu_id, x.stt""",
                (hoa_don_id,))]
            obs = [dict(o) for o in self.conn.execute("SELECT * FROM kho.hoa_don_quan_sat WHERE hoa_don_id = %s ORDER BY thu_tu", (hoa_don_id,))]
            logic = [dict(x) for x in self.conn.execute("SELECT id, logical_line_key FROM kho.hoa_don_dong_danh_tinh WHERE hoa_don_id = %s ORDER BY 2",
                                                        (hoa_don_id,))]
            cau = [dict(b) for b in self.conn.execute(
                """SELECT b.id, b.hoa_don_phien_ban_id, b.source_dong_id, b.dong_danh_tinh_id, b.source_ordinal, b.quantity_raw, b.unit_raw,
                          b.quantity_exact::text AS quantity_exact, b.precision_state, b.nature, b.line_identity_mapping_id, b.field_state_sha256
                   FROM kho.hoa_don_dong_phien_ban b WHERE b.hoa_don_id = %s ORDER BY b.hoa_don_phien_ban_id, b.source_ordinal""", (hoa_don_id,))]
            tuyen = [dict(r) for r in self.conn.execute(
                """SELECT id, source_dong_id, phien_ban, dich, hien_hanh, trang_thai, predecessor_route_id, source_graph_sha256, reason, recorded_at
                   FROM kho.mua_dich_dong WHERE hoa_don_id = %s ORDER BY source_dong_id, phien_ban""", (hoa_don_id,))]
            anh_xa = [dict(m) for m in self.conn.execute(
                """SELECT id, reference_id, revision, subject_kind, state, valid_from, valid_to, nguon_quyet_dinh, duyet_boi, line_source_ordinal,
                          line_source_locator, line_native_xml_sha256, line_entry_ordinal FROM master.anh_xa_nguon WHERE target_hoa_don_id = %s
                   ORDER BY subject_key, revision""", (hoa_don_id,))]
            dong_nguon = [r["v"] for r in self.conn.execute("SELECT v FROM kho.m2_dong_nguon(%s::uuid) AS v", (hoa_don_id,))]
            # R2: ứng viên literal đã admitted khớp đúng dòng hiện hành (CSDL lọc theo hóa đơn/PN/dòng; chỉ ref/revision/dòng logic) — không phải duyệt
            ung_vien = [r["v"] for r in self.conn.execute("SELECT v FROM kho.m2_ung_vien_hien_hanh(%s::uuid) AS v", (hoa_don_id,))]
            token = self.conn.execute("SELECT kho.m2_co_so(%s::uuid) AS v", (hoa_don_id,)).fetchone()["v"]
            # R16: child số lượng L11 của hóa đơn — RLS chỉ trả khi phiên có CẢ M2 và M5 hiện hành (không lộ cho actor chỉ M2)
            l11 = [dict(r) for r in self.conn.execute(
                """SELECT c.id, c.lien_ket_id, c.cau_noi_id, c.trang_thai, c.hieu_luc, c.can_soat_ly_do, c.so_luong_hoa_don_nguon::text AS hoa_don_nguon,
                          c.so_luong_phieu_nguon::text AS phieu_nguon, c.so_luong_pool_hoa_don::text AS pool_hoa_don, c.so_luong_pool_phieu::text AS pool_phieu
                   FROM kho.lien_ket_dong c WHERE c.hoa_don_id = %s ORDER BY c.tao_luc, c.id""", (hoa_don_id,))]
        iso = lambda x: x.isoformat() if x is not None else None  # noqa: E731
        return {
            "id": str(d["id"]), "phap_nhan": d["phap_nhan"], "chieu": d["chieu"],
            "dinh_danh": [d["phap_nhan"], d["chieu"], d["mst_ban"], d["mau_so"], d["ky_hieu"], d["so_chuan"]],
            "con_tro": {"latest_observation_id": _s(d["latest_observation_id"]), "accepted_source_observation_id": _s(d["accepted_source_observation_id"]),
                        "eligible_content_id": _s(d["eligible_content_id"])},
            "expected_graph": (token or {}).get("graph_sha256"),
            "phien_ban": [{"id": str(v["id"]), "phien_ban": v["phien_ban"], "semantic_sha256": v["semantic_sha256"], "ngay_lap": iso(v["ngay_lap"]),
                           "tien_te": v["tien_te"], "header": v["raw_header_states"], "chung_tu_id": str(v["chung_tu_id"]),
                           "money_basis_state": v["money_basis_state"], "supersedes_id": _s(v["supersedes_id"])} for v in pbs],
            "dong_core": [{"id": str(r["id"]), "chung_tu_id": str(r["chung_tu_id"]), "stt": r["stt"], "mo_ta": r["mo_ta"], "so_luong": r["so_luong"],
                           "no_minor": r["no_minor"], "co_minor": r["co_minor"], "du_lieu": r["du_lieu"]} for r in dong_core],
            "quan_sat": [{"id": str(o["id"]), "thu_tu": o["thu_tu"], "phien_ban_id": str(o["phien_ban_id"]), "lan_tiep_nhan_id": str(o["lan_tiep_nhan_id"]),
                          "native_xml_sha256": o["native_xml_sha256"], "container_sha256": o["container_sha256"], "entry_ordinal": o["entry_ordinal"],
                          "entry_name": o["entry_name"], "phan_loai": list(o["classification"]), "native_fiscal_status": o["native_fiscal_status"],
                          "known_at_server": iso(o["known_at_server"])} for o in obs],
            "dong_nguon_hien_hanh": dong_nguon,
            "ung_vien_dong": ung_vien,
            "dong_logic": [{"id": str(x["id"]), "logical_line_key": x["logical_line_key"]} for x in logic],
            "cau_noi": [{**{k: _s(b[k]) for k in ("id", "hoa_don_phien_ban_id", "source_dong_id", "dong_danh_tinh_id", "line_identity_mapping_id")},
                         "source_ordinal": b["source_ordinal"], "quantity_raw": b["quantity_raw"], "unit_raw": b["unit_raw"],
                         "quantity_exact": b["quantity_exact"], "precision_state": b["precision_state"], "nature": b["nature"],
                         "field_state_sha256": b["field_state_sha256"]} for b in cau],
            "tuyen": [{"id": str(r["id"]), "source_dong_id": str(r["source_dong_id"]), "phien_ban": r["phien_ban"], "dich": r["dich"],
                       "hien_hanh": r["hien_hanh"], "trang_thai": r["trang_thai"], "predecessor_route_id": _s(r["predecessor_route_id"]),
                       "source_graph_sha256": r["source_graph_sha256"], "reason": r["reason"], "recorded_at": iso(r["recorded_at"])} for r in tuyen],
            "anh_xa_dong": [{**m, "id": str(m["id"]), "valid_from": iso(m["valid_from"]), "valid_to": iso(m["valid_to"])} for m in anh_xa],
            "l11": L11_THONG_BAO,
            "l11_lien_ket": [{**r, "id": str(r["id"]), "lien_ket_id": str(r["lien_ket_id"]), "cau_noi_id": str(r["cau_noi_id"]),
                              "can_soat_ly_do": list(r["can_soat_ly_do"] or [])} for r in l11],
            "duoc": {h: quyen.duoc(dt, h, d["phap_nhan_id"]) for h in ("M2_MAP", "M2_ROUTE", "M2_SOURCE_REVIEW")}}

    # ------------------------------------------------------------------ thao tác CFO: một đường kiểm ở CSDL (Python chỉ kiểm sớm cùng quy tắc)
    def _goi(self, dt, ham: str, than: dict) -> dict:
        with self._tx(dt):
            return self.conn.execute(f"SELECT kho.{ham}(%s::jsonb) AS v", (json.dumps(than, ensure_ascii=False),)).fetchone()["v"]

    def _pn_hoa_don(self, dt, hoa_don_id):
        with self._tx(dt):
            row = self.conn.execute("SELECT phap_nhan_id FROM kho.hoa_don_danh_tinh WHERE id = %s", (hoa_don_id,)).fetchone()
        if not row:
            raise DataError("HOA_DON", "Không thấy hóa đơn (hoặc ngoài quyền).")
        return row["phap_nhan_id"]

    def mapping_company(self, actor, request: dict) -> dict:
        dt = self.danh_tinh(actor)
        khoa = nguon_chung.kiem_khoa(request.get("khoa"))
        inst, key, pn_ma, ly_do, rev = (request.get(k) for k in ("source_instance", "company_key", "phap_nhan", "ly_do", "revision_hien_tai"))
        if not all(isinstance(x, str) and x for x in (inst, key, pn_ma, ly_do)) or isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
            raise DataError("M2_YEU_CAU_SAI", "Cần instance, company key, pháp nhân đích, revision cuối đã biết và lý do.")
        row = self.conn.execute("SELECT id FROM master.phap_nhan WHERE ma = %s", (pn_ma,)).fetchone()
        if not row:
            raise DataError("PHAP_NHAN", "Không có pháp nhân này.")
        quyen.kiem(dt, "M2_MAP", row["id"])
        return self._goi(dt, "m2_mapping_cong_ty", {"source_instance": inst, "company_key": key, "phap_nhan": pn_ma, "revision_hien_tai": rev,
                                                    "reason": ly_do, "client_key": khoa})

    def mapping_line(self, actor, *, client_key, hoa_don_id, expected_graph, source_row_id, logical_line_key, evidence_ref, evidence_revision,
                     reason) -> dict:
        """evidence_ref/evidence_revision: ứng viên literal đã admitted (bắt buộc); CSDL resolve và đối chiếu với dòng/artifact/định danh thực
        trước khi CFO duyệt — ứng viên không cấp quyền, không thay CFO."""
        dt = self.danh_tinh(actor)
        khoa = nguon_chung.kiem_khoa(client_key)
        if not all(isinstance(x, str) and x for x in (hoa_don_id, expected_graph, source_row_id, logical_line_key, reason, evidence_ref)):
            raise DataError("M2_YEU_CAU_SAI", "Cần hóa đơn, token đồ thị đang xem, dòng nguồn, khóa dòng logic, bằng chứng literal và lý do.")
        if isinstance(evidence_revision, bool) or not isinstance(evidence_revision, int) or evidence_revision < 1:
            raise DataError("M2_YEU_CAU_SAI", "evidence_revision phải là số nguyên ≥ 1 của ứng viên literal.")
        quyen.kiem(dt, "M2_MAP", self._pn_hoa_don(dt, hoa_don_id))
        return self._goi(dt, "m2_mapping_dong", {"hoa_don_id": hoa_don_id, "expected_graph": expected_graph, "source_row_id": source_row_id,
                                                 "logical_line_key": logical_line_key, "evidence_ref": evidence_ref, "evidence_revision": evidence_revision,
                                                 "reason": reason, "client_key": khoa})

    def xem_xet_nguon(self, actor, request: dict) -> dict:
        dt = self.danh_tinh(actor)
        khoa = nguon_chung.kiem_khoa(request.get("khoa"))
        than = {k: request.get(k) for k in ("hoa_don_id", "observation_id", "expected_graph", "ly_do")}
        if not all(isinstance(v, str) and v for v in than.values()):
            raise DataError("M2_YEU_CAU_SAI", "Cần hóa đơn, quan sát mới nhất, token đồ thị đang xem và lý do.")
        quyen.kiem(dt, "M2_SOURCE_REVIEW", self._pn_hoa_don(dt, than["hoa_don_id"]))
        return self._goi(dt, "m2_xem_xet_nguon", {"hoa_don_id": than["hoa_don_id"], "observation_id": than["observation_id"],
                                                  "expected_graph": than["expected_graph"], "reason": than["ly_do"], "client_key": khoa})

    def route(self, actor, request: dict) -> dict:
        dt = self.danh_tinh(actor)
        khoa = nguon_chung.kiem_khoa(request.get("khoa"))
        hd, cau, dich, ly_do, eg = (request.get(k) for k in ("hoa_don_id", "cau_noi_id", "dich", "ly_do", "expected_graph"))
        exp = request.get("expected_route_id")
        if not all(isinstance(x, str) and x for x in (hd, cau, ly_do, eg)) or dich not in DICH or (exp is not None and not isinstance(exp, str)):
            raise DataError("M2_YEU_CAU_SAI", "Cần hóa đơn, cầu nối dòng, đích hợp lệ, tuyến hiện hành mong đợi (hoặc null), token đồ thị và lý do.")
        quyen.kiem(dt, "M2_ROUTE", self._pn_hoa_don(dt, hd))
        return self._goi(dt, "m2_route", {"hoa_don_id": hd, "cau_noi_id": cau, "dich": dich, "expected_route_id": exp, "expected_graph": eg,
                                          "reason": ly_do, "client_key": khoa})

    @staticmethod
    def lien_ket(*_):
        raise DataError("M2_L11_CHUA_PHAT_HANH", L11_THONG_BAO)
