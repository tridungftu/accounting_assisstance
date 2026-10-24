"""M5 phiếu kho — service K2 `KhoSoLuongK2` (binding M5 §2–§5, handoff GIAO-CODE-M0-M5-INTAKE-UI-01 §4–§6).

Luồng: nhận nguồn trước PN (capture `m0-capture/v1`, quyền INTAKE ở CSDL trước tra cứu) → context do MÁY CHỦ dựng từ bytes đã kiểm +
registry + repository → reader thuần final (`nguon/kho_10.doc_phieu_kho`, frozen DTO, `phan_loai_quan_sat`) → promote typed theo PN của
mapping đã duyệt (hàm định nghĩa CSDL dưới khóa danh tính) → danh sách/chi tiết/lịch sử → review nguồn V8 / mapping V4 / file soát.

Ba grain hash riêng: capture H (M0), reader semantic/request H (kho10-content/request), business request H (PN, M5, operation, key).
Quyền: trước PN dùng năng lực nguồn ở CSDL (`quyen.kiem_nguon`); nghiệp vụ dùng PN + module M5 + action (+ V4/V8) như ma trận DEMO;
mapping cần CẢ SOURCE_MAP đúng PN đích VÀ M5_MAP_V4. CSDL ép lại bằng RLS/trigger/definer. Không tính tồn/giá/sổ, không journal,
không L11/capacity giả, không duyệt/đảo phiếu tại nguồn #10. Thiếu ngày/graph/mapping → giữ candidate + lý do (0 dòng nghiệp vụ).

Sửa 02: intake và FILE_SOAT chạy trên MỘT giao dịch của kết nối chủ đã cấu hình (danh tính → quyền → khóa → biên nhận → stage bất biến → consumer
guarded); review/mapping chỉ qua hàm định nghĩa nhận expected refs/quyết định/lý do (hash/biên nhận/kết quả do CSDL dẫn xuất). Core PHIEU_KHO
quantity-only do consumer typed ghi (chủ M5 do DB suy). Route đọc giữ kết nối thường có RLS.

Sửa 03: kết quả cuối lần nhận chốt bất biến cùng giao dịch (replay trả đúng promote/HOLD/stage); FILE_SOAT bind token basis toàn graph do CSDL
dẫn xuất (chi_tiet → UI → HTTP → service → preflight → stage → consumer → lô/biên nhận → workbook), guard kỳ/basis hiện hành trước cached result;
namespace biên nhận (PN, M5, operation, key) khóa trước tra cứu; accepted ≠ eligible (cổng số lượng ở CSDL).
"""

from __future__ import annotations

import json
import re
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, sha256
from ..ha_tang.store import write_immutable
from ..nguon.kho_10 import (FrozenObject, KhoHistorySummary, KhoReadContext, doc_phieu_kho, phan_loai_quan_sat, ra_json)
from ..nguon.review_xay_dung import chuan_hoa_so, doc_json_chinh_xac
from . import nguon_chung, quyen

MODULE = "M5"
VAI_TRO_NATIVE, VAI_TRO_MASTER = "NATIVE_DETAIL", "MASTER_RAW"
MASTER_WHITELIST = {"DM_HangHoa": ("MaHang", ("MaHang", "DVT_Goc", "DVT_QuyDoi")), "DM_Kho": ("MaKho", ("MaKho", "TrangThai")),
                    "DM_DoiTac": ("MaDoiTac", ("MaDoiTac", "MaDoiTuong_KT"))}
SAME_UNIT = "SAME_VERIFIED_UNIT_ONLY"
CAPTURE_CLAIM = "SERVER_CAPTURE_OF_ROOT_PINNED_LEXICAL_FILES_NOT_NATIVE_ENDPOINT_GUARANTEE"
L11_THONG_BAO = "Chưa có bridge M2/contract liên kết số lượng đủ căn cứ (L11 dual-pool là gói kế tiếp) — không có số đã khớp/còn lại."
# giữ nguyên chuỗi trên: nó nằm trong workbook file soát nguồn M5 cũ (định dạng/bytes cũ không đổi); L11 thật ở trang liên kết số lượng riêng
KHONG_PRODUCER = ("Nguồn #10 chưa có producer snapshot tồn theo kho/kiểm kê đủ căn cứ (readonly-v1). Không tự cộng phiếu, "
                  "không tạo tồn/điều chỉnh; trạng thái: chưa biết.")
TRANG_THAI_TRUY_VAN = {"NHAP", "DA_DUYET", "DA_DAO", "CHUA_MAP"}
_SHA = re.compile(r"[0-9a-f]{64}")


def _hom_nay_vn() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


def _j(value):
    return None if value is None else json.dumps(chuan_hoa_so(value), ensure_ascii=False, default=str)


def _s(v):
    return None if v is None else str(v)


def _lay(obj, keys):
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def _ma_loi(issues) -> list[str]:
    return list(dict.fromkeys(i.code for i in issues))


class KhoSoLuongK2:
    def __init__(self, conn, thu_muc: Path, *, conn_chu=None, chi_mo_phong: bool = True, hom_nay=None):
        """conn: psycopg autocommit=True, row_factory=dict_row, login ứng dụng (thành viên app_web, không chủ bảng/BYPASSRLS) — mọi route đọc.
        conn_chu: kết nối CHỦ BẢNG đã cấu hình (admin_dsn riêng, cùng endpoint/DB đã kiểm loopback + đích thực + đúng owner role, xem
        crm_khoi_dong.kiem_ket_noi_chu) — CHỈ cho intake/FILE_SOAT: một giao dịch có danh tính phiên, ghi stage bất biến rồi consumer guarded."""
        from psycopg.types.string import StrDumperUnknown
        self.conn, self.root, self.chi_mo_phong = conn, Path(thu_muc), chi_mo_phong
        self.conn_chu = conn_chu
        self.hom_nay = hom_nay or _hom_nay_vn
        conn.adapters.register_dumper(str, StrDumperUnknown)
        if conn_chu is not None:
            conn_chu.adapters.register_dumper(str, StrDumperUnknown)

    # ------------------------------------------------------------------ hạ tầng (cùng mẫu phiên/giao dịch/audit với CRM)
    def danh_tinh(self, dang_nhap: str) -> dict:
        return quyen.nap_danh_tinh(self.conn, dang_nhap, chi_mo_phong=self.chi_mo_phong)

    @contextmanager
    def _tx(self, dt):
        with self.conn.transaction():
            self.conn.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                              "set_config('ktt.ngay_hieu_luc', %s, true)", (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat()))
            yield

    @contextmanager
    def _tx_doc(self, dt):
        """Repair04: MỘT snapshot đọc nhất quán (REPEATABLE READ, READ ONLY) đặt bằng statement ĐẦU TIÊN của giao dịch, trước GUC/SELECT nào —
        mọi SELECT hiển thị và token basis FILE cùng thấy một trạng thái CSDL (không ghép display cũ + token mới). Không mở được snapshot giữa
        một giao dịch đang có (outer/nested) → từ chối rõ, không hạ cấp thành savepoint READ COMMITTED."""
        from psycopg import pq
        if self.conn.info.transaction_status != pq.TransactionStatus.IDLE:
            raise DataError("M5_DOC_NHAT_QUAN", "Không mở được snapshot đọc nhất quán trong một giao dịch đang mở — thử lại.")
        with self.conn.transaction():
            self.conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            self.conn.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                              "set_config('ktt.ngay_hieu_luc', %s, true)", (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat()))
            yield

    @contextmanager
    def _tx_chu(self, dt):
        """MỘT giao dịch trên kết nối chủ: đặt + KIỂM danh tính phiên (ID + login hoạt động) trước mọi khóa/tra cứu; chủ không bỏ qua guard actor."""
        if self.conn_chu is None:
            raise DataError("M5_CHU_CHUA_CAU_HINH", "Chưa cấu hình kết nối máy chủ (chủ bảng) cho nhận nguồn/file soát M5 — mở lại bằng nút MỞ BẢN DEMO.")
        with self.conn_chu.transaction():
            row = self.conn_chu.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                                        "set_config('ktt.ngay_hieu_luc', %s, true), master.ktt_danh_tinh() AS ai",
                                        (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat())).fetchone()
            if (row["ai"] if isinstance(row, dict) else row[3]) != dt["dang_nhap"]:
                raise DataError("DANH_TINH", "Danh tính phiên không còn hoạt động (ID + login).")
            yield self.conn_chu

    def _su_kien(self, pn, dt, bang, doi_tuong_id, hanh_dong, *, sau=None, ly_do=None, can_cu=None):
        self.conn.execute("""INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, sau, ly_do, can_cu)
                             VALUES (%s,%s,'HE_THONG',%s,%s,%s,%s,%s,%s)""",
                          (pn, dt["dang_nhap"], bang, doi_tuong_id, hanh_dong, _j(sau), ly_do, _j(can_cu)))

    def _pn(self, ma: str) -> str:
        row = self.conn.execute("SELECT id FROM master.phap_nhan WHERE ma = %s", (ma,)).fetchone()
        if not row:
            raise DataError("PHAP_NHAN", "Không có pháp nhân này.")
        return str(row["id"])

    # ------------------------------------------------------------------ dựng context từ bytes đã kiểm + registry (không từ trình duyệt)
    @staticmethod
    def _doc_master(master_raw: bytes | None):
        """Master raw → hàng whitelist (chỉ cột đã khai báo) + dòng nguồn. Sai shape → None (reader giữ issue, không đoán)."""
        if master_raw is None:
            return None, [], "ARTIFACT_ROLE_ABSENT"
        try:
            value = doc_json_chinh_xac(master_raw)
        except DataError as exc:
            return None, [], exc.code
        if not isinstance(value, dict) or any(not isinstance(value.get(s), list) for s in MASTER_WHITELIST) or set(value) - set(MASTER_WHITELIST):
            return None, [], "MASTER_SHAPE"
        rows, nguon, loi = {}, [], None
        for section, (khoa, cot) in MASTER_WHITELIST.items():
            rows[section] = []
            for i, r in enumerate(value[section]):
                if not isinstance(r, dict):
                    return None, [], "MASTER_SHAPE"
                hop_le = KhoSoLuongK2._hang_master_hop_le(r, khoa, cot)
                rows[section].append({c: r[c] for c in cot if c in r})
                raw = chuan_hoa_so(r)
                nguon.append({"vai_tro": VAI_TRO_MASTER, "section": section, "locator": f"/{section}/{i}", "thu_tu": i,
                              "source_key": r.get(khoa) if isinstance(r.get(khoa), str) else None, "row_raw": raw,
                              "row_raw_sha256": sha256(canonical_json(raw).encode("utf-8")), "quantity_json_kind": None, "quantity_text": None,
                              "validation_state": "HOP_LE" if hop_le else "LOI", "error_codes": [] if hop_le else ["MASTER_ROW_INVALID"]})
                if not hop_le:
                    loi = "MASTER_ROW_INVALID"
        # hàng master sai kiểu: giữ dòng nguồn làm bằng chứng nhưng KHÔNG đưa vào context (reader báo master chưa resolve, semantic NULL)
        return (None if loi else rows), nguon, loi

    @staticmethod
    def _hang_master_hop_le(r: dict, khoa: str, cot: tuple) -> bool:
        k = r.get(khoa)
        if not isinstance(k, str) or not k or k != k.strip():
            return False
        for c in cot[1:]:
            v = r.get(c)
            if c == "DVT_QuyDoi":
                if v is not None and (isinstance(v, bool) or not isinstance(v, (str, int, Decimal))):
                    return False
            elif v is not None and not isinstance(v, str):
                return False
        return True

    @staticmethod
    def _dong_nguon_native(ket_qua) -> list[dict]:
        """Dòng nguồn native từ kết quả reader (exact native values + token số lượng + issue theo locator)."""
        out = []
        theo_loc = {}
        for i in ket_qua.issues:
            theo_loc.setdefault(i.locator, []).append(i.code)
        if ket_qua.native_header is not None:
            raw = chuan_hoa_so(ra_json(ket_qua.native_header))
            codes = sorted({c for loc, cs in theo_loc.items() if loc.startswith("/phieu") for c in cs})
            so = ket_qua.native_header.get("SoPhieu")
            out.append({"vai_tro": VAI_TRO_NATIVE, "section": "GD_Phieu", "locator": "/phieu", "thu_tu": 0, "source_key": so if isinstance(so, str) else None,
                        "row_raw": raw, "row_raw_sha256": sha256(canonical_json(raw).encode("utf-8")), "quantity_json_kind": None, "quantity_text": None,
                        "validation_state": "LOI" if codes else "HOP_LE", "error_codes": codes})
        for ln in ket_qua.lines:
            loc = f"/lines/{ln.source_ordinal}"
            raw = chuan_hoa_so(ra_json(ln.native_values))
            codes = sorted({c for l, cs in theo_loc.items() if l == loc or l.startswith(loc + "/") for c in cs})
            ma = ln.native_values.get("ID_Dong") if isinstance(ln.native_values, FrozenObject) else None
            out.append({"vai_tro": VAI_TRO_NATIVE, "section": "GD_Dong", "locator": loc, "thu_tu": ln.source_ordinal,
                        "source_key": ma if isinstance(ma, str) else None, "row_raw": raw, "row_raw_sha256": sha256(canonical_json(raw).encode("utf-8")),
                        "quantity_json_kind": ln.quantity_json_kind, "quantity_text": ln.quantity_text,
                        "validation_state": "XUNG_DOT" if "KHO_LINE_ID_CONFLICT" in codes else "LOI" if codes else "HOP_LE", "error_codes": codes})
        return out

    @staticmethod
    def _giai_do_luong(facts: list[dict], master_sha: str | None, master_rows, ket_qua) -> tuple[dict | None, list[str]]:
        """Chỉ resolve facts khi đúng điều kiện đã pin: master SHA thực, mọi hàng tham chiếu đúng UOM, ≥1 STRING và mọi số lượng non-null là
        STRING. Sai/thiếu → None + lý do (không default proof/1:1, không dùng DVT_QuyDoi)."""
        if not facts:
            return None, ["DO_LUONG_KHONG_CO_KHAI_BAO"]
        kinds = [ln.quantity_json_kind for ln in ket_qua.lines]
        ma_hang = {ln.native_values.get("MaHang") for ln in ket_qua.lines if isinstance(ln.native_values, FrozenObject)}
        hop = []
        ly_do = []
        for f in facts:
            dk = f["dieu_kien"]["resolution_preconditions"]
            lo = []
            if master_sha != dk["actual_master_sha256"]:
                lo.append("DO_LUONG_MASTER_KHAC")
            if master_rows is None:
                lo.append("DO_LUONG_MASTER_THIEU")
            else:
                for ma in ma_hang:
                    hit = [r for r in master_rows["DM_HangHoa"] if r.get("MaHang") == ma]
                    if len(hit) != 1 or hit[0].get("DVT_Goc") != dk["all_referenced_native_master_units"]:
                        lo.append("DO_LUONG_UOM_KHONG_KHOP")
                        break
            if dk.get("requires_at_least_one_quantity_string") and "STRING" not in kinds:
                lo.append("DO_LUONG_KHONG_CO_STRING")
            if any(k not in dk["all_present_nonnull_quantity_json_kinds"] for k in kinds if k != "NULL"):
                lo.append("DO_LUONG_LOAI_TOKEN_KHAC")
            (ly_do.extend(lo) if lo else hop.append(f))
        if len(hop) != 1:
            return None, sorted(set(ly_do or ["DO_LUONG_MO_HO"]))
        return hop[0]["payload"], []

    def _boi_canh(self, *, inst, profile, scope, coverage, errors, receipt_id, so_phieu, mapping, master_ref, master_sha, master_rows, facts):
        qe = None
        if facts is not None:
            r = facts["same_unit_ratio_evidence"]
            qe = {"profile_ref": facts["measurement_profile_ref"], "native_encoding_kind": facts["declared_encoding_kind"], "conversion_kind": SAME_UNIT,
                  "unit_definition_ref": facts["unit_definition"]["reference_id"], "approved_conversion_proof_ref": None, "prior_unit_definition_ref": None,
                  "master_revision_ref": None, "ratio_numerator_text": r["numerator_text"], "ratio_denominator_text": r["denominator_text"],
                  "authority_origin": facts["authority_origin"]}
        ctx = {
            "authority_ref": "urn:ktt:m0:server-registry", "authority_origin": "SERVER_REGISTRY_ROOT_PINNED_DEMO_SEED",
            "actual_source_verification": "NOT_VERIFIED",
            "logical_source_identity": {"source_instance": inst, "SoPhieu": so_phieu},
            "receipt_id": receipt_id, "profile_ref": profile["reference_id"], "source_code_sha256": profile["payload"].get("source_code_sha256"),
            "scope_ref": scope["scope_ref"],
            "scope": {"source_instance_id": inst, "SoPhieu": scope["SoPhieu"], "MaKho": scope["MaKho"], "sections": scope["sections"], "coverage": coverage},
            "capture_consistency_claim": CAPTURE_CLAIM,
            "mapping_revision": None if mapping is None else {
                "reference_id": mapping["reference_id"], "version": mapping["revision"], "source_instance": inst, "MaKho": scope["MaKho"],
                "phap_nhan": mapping["phap_nhan_ma"], "authority_origin": "SERVER_MAPPING_REGISTRY", "actual_mapping_verification": "NOT_VERIFIED"},
            "master_snapshot": None if master_sha is None else {
                "reference_id": master_ref, "raw_subtree_sha256": master_sha, "whitelist_rows": master_rows,
                "actual_master_history_verification": "NOT_VERIFIED"},
            "quantity_evidence": qe, "resolved_measurement_facts": facts, "actual_profile_proof_deployment": "NOT_VERIFIED",
            "capture_ref": f"urn:ktt:m0:capture:{receipt_id}", "reported_capture_errors": list(errors), "request_digest": None,
            "request_binding_state": "CURRENT_REQUEST_COMPUTE_FROM_INPUT_NOT_SUPPLIED"}
        return KhoReadContext.tu_dict(ctx)

    # ------------------------------------------------------------------ POST /api/m5/nhan — capture trước PN + promote (S01/S02, một giao dịch chủ)
    def nhan(self, dang_nhap: str, *, source_instance: str, scope_ref: str | None, coverage: str, reported_errors=nguon_chung.VANG, client_key: str,
             native: bytes | None, master: bytes | None) -> dict:
        """Thứ tự trong MỘT giao dịch trên kết nối chủ: kiểm danh tính → năng lực INTAKE hiện hành đúng instance/profile → khóa namespace +
        tra biên nhận (so H thực) → [mới] blob + reader + khóa logic/lịch sử + stage bất biến → consumer capture → consumer typed/core → commit.
        Không có writer free-JSON; replay cùng key/H = 0 delta; cùng key khác H = 409 trước mọi ghi stage/blob."""
        dt = self.danh_tinh(dang_nhap)
        nguon_chung.kiem_khoa(client_key)
        if not isinstance(source_instance, str) or not source_instance:
            raise DataError("NGUON_INSTANCE", "Cần instance nguồn trong registry.")
        for ten, raw in ((VAI_TRO_NATIVE, native), (VAI_TRO_MASTER, master)):
            if raw is not None and not isinstance(raw, (bytes, bytearray)):
                raise DataError("NGUON_ARTIFACT", f"{ten} phải là bytes thực.")
        loi_bao = nguon_chung.kiem_ma_loi(reported_errors)  # container sai bị từ chối TRƯỚC H/ghi
        with self._tx_chu(dt) as c:
            profile = nguon_chung.doc_profile(c, source_instance)
            quyen.kiem_nguon(c, source_instance, profile["reference_id"], profile["sha256"], "INTAKE")
            cu = nguon_chung.tim_lan_nhan(c, source_instance, profile, client_key)  # CSDL: INTAKE → khóa namespace → tra
            if scope_ref is None:
                scopes = c.execute("SELECT scope_ref FROM master.nguon_pham_vi WHERE source_instance_id = %s AND profile_ref = %s AND profile_sha256 = %s",
                                   (source_instance, profile["reference_id"], profile["sha256"])).fetchall()
                if len(scopes) != 1:
                    raise DataError("NGUON_PHAM_VI", "Instance có nhiều/không có phạm vi cấu hình — chọn phạm vi trong registry.")
                scope_ref = scopes[0]["scope_ref"]
            scope = nguon_chung.doc_pham_vi(c, source_instance, profile, scope_ref)
            arts = nguon_chung.artifacts(profile, {VAI_TRO_NATIVE: native, VAI_TRO_MASTER: master})
            env = nguon_chung.phong_bi_capture(source_instance, profile, scope, coverage, loi_bao, arts)
            h = nguon_chung.bam_capture(env)
            if cu is not None:
                if cu["capture_sha256"] != h:
                    raise DataError("CAPTURE_KHAC_NOI_DUNG", "Khóa capture đã dùng cho native/master/profile/scope/coverage/lỗi khác — không ghi artifact mới.")
                return self._phat_lai(cu, h)
            for a in arts:  # blob bất biến content-addressed; cùng bytes tái dùng cùng blob; lỗi giữ nguyên làm bằng chứng
                if a["co_mat"]:
                    nguon_chung.ghi_blob(self.root, a["raw"])
            cov_hl, ly_do_cov = nguon_chung.coverage_hieu_luc(coverage, arts, [])
            receipt_id = nguon_chung.receipt_id_moi()
            ket_qua, rows, ke_hoach = self._doc_va_lap_ke_hoach(c, source_instance, profile, scope, cov_hl, env["reported_errors"], receipt_id, native, master)
            ket_qua.update(coverage=coverage, coverage_hieu_luc=cov_hl, ly_do_coverage=ly_do_cov)
            promote = self._lap_promote(c, dt, scope, ke_hoach) if ke_hoach else None
            du_lieu = nguon_chung.du_lieu_stage_capture(receipt_id=receipt_id, scope=scope, coverage=coverage, coverage_hl=cov_hl, envelope=env, arts=arts,
                                                       rows=rows, ket_qua=ket_qua, promote=promote)
            stage = nguon_chung.ghi_stage(c, dt, muc_dich="CAPTURE", client_key=client_key, h=h, source_instance=source_instance,
                                          profile_ref=profile["reference_id"], profile_sha256=profile["sha256"], du_lieu=du_lieu)
            ghi = nguon_chung.tieu_thu_capture(c, stage, h)
            if not ghi["moi"]:  # namespace đã khóa từ tim_lan_nhan nên không xảy ra; nếu có thì đọc lại đúng kết quả cuối đã chốt
                cu = nguon_chung.tim_lan_nhan(c, source_instance, profile, client_key)
                if cu is None or cu["capture_sha256"] != h:
                    raise DataError("CAPTURE_KHAC_NOI_DUNG", "Khóa capture đã dùng cho nội dung khác.")
                return self._phat_lai(cu, h)
            if promote is None:
                chuyen = {"trang_thai": "GIU_CHO_UNG_VIEN", "ly_do": ket_qua["giu_cho"]}
            elif promote.get("hold"):
                c.execute("SELECT kho.m5_giu_cho_anh_huong(%s::uuid, %s, %s)", (stage, h, promote["hold"]))
                chuyen = {"trang_thai": "GIU_CHO_ANH_HUONG", "ly_do": [promote["hold"]], "phieu_id": promote.get("phieu_id")}
            else:
                out = c.execute("SELECT kho.m5_tieu_thu_quan_sat(%s::uuid, %s) AS v", (stage, h)).fetchone()["v"]
                chuyen = {**out, "phan_loai": promote["phan_loai"], "history_state": promote["history_state"], "can_xem_xet": promote["can_xem_xet"]}
            # SR02-1: chốt kết quả cuối BẤT BIẾN trong cùng giao dịch (sau typed/hold); trả đúng bản đã chốt để fresh = replay (trừ lap_lai)
            cuoi = nguon_chung.chot_ket_qua(c, stage, h, bool(ghi["snapshot_moi"]), chuyen)
        return {**ket_qua, "lan_tiep_nhan_id": receipt_id, "capture_sha256": h, "lap_lai": False, **cuoi}

    @staticmethod
    def _phat_lai(cu: dict, h: str) -> dict:
        """Replay cùng key/H: kết quả capture + kết quả cuối đã chốt (stage/snapshot_moi/promote/HOLD) — không tính lại reader/promote."""
        cuoi = cu.get("ket_qua_cuoi")
        if not isinstance(cuoi, dict) or set(cuoi) != {"stage_id", "snapshot_moi", "promote"}:
            raise DataError("KET_QUA_CUOI_THIEU", "Lần nhận đã có biên nhận nhưng thiếu kết quả cuối đã chốt — giữ nguyên, không tính lại.")
        return {**cu["ket_qua"], "lan_tiep_nhan_id": str(cu["id"]), "capture_sha256": h, "lap_lai": True,
                "stage_id": str(cuoi["stage_id"]), "snapshot_moi": cuoi["snapshot_moi"], "promote": cuoi["promote"]}

    def _doc_va_lap_ke_hoach(self, c, inst, profile, scope, coverage, errors, receipt_id, native, master):
        master_sha = sha256(master) if master is not None else None
        master_rows, master_nguon, master_loi = self._doc_master(master)
        master_ref = nguon_chung.doc_master_catalog(c, master_sha) if master_sha else None
        so_phieu = None
        if native is not None:
            try:
                v = doc_json_chinh_xac(native)
                sp = v.get("phieu", {}).get("SoPhieu") if isinstance(v, dict) and isinstance(v.get("phieu"), dict) else None
                so_phieu = sp if isinstance(sp, str) and sp and sp == sp.strip() else None
            except DataError:
                so_phieu = None
        mapping = nguon_chung.anh_xa_hien_hanh(c, inst, profile, scope["MaKho"])
        facts_all = nguon_chung.doc_su_kien_do_luong(c, inst, profile)
        tham_so = dict(inst=inst, profile=profile, scope=scope, coverage=coverage, errors=errors, receipt_id=receipt_id, so_phieu=so_phieu, mapping=mapping,
                       master_ref=master_ref, master_sha=master_sha, master_rows=master_rows)
        giu_cho, ly_do_do_luong = [], []
        if native is None:
            return ({"semantic_digest": None, "request_digest": None, "reader_issues": [], "giu_cho": ["ARTIFACT_NATIVE_VANG"], "so_dong": 0,
                     "master_loi": master_loi}, master_nguon, None)
        lan1 = doc_phieu_kho(native, self._boi_canh(**tham_so, facts=None))
        facts, ly_do_do_luong = self._giai_do_luong(facts_all, master_sha, master_rows, lan1)
        kq = doc_phieu_kho(native, self._boi_canh(**tham_so, facts=facts)) if facts is not None else lan1
        rows = self._dong_nguon_native(kq) + master_nguon
        if mapping is None:
            giu_cho.append("KHO_PN_MAPPING_PENDING")
        if kq.semantic_digest is None:
            giu_cho.append("KHO_GRAPH_CHUA_DU")
        if kq.request_digest is None:
            giu_cho.append("KHO_CONTEXT_UNRESOLVED")
        if kq.business_date is None:
            giu_cho.append("KHO_DATE_MISSING")
        ket_qua = {"semantic_digest": kq.semantic_digest, "request_digest": kq.request_digest, "raw_sha256": kq.raw_sha256,
                   "reader_issues": _ma_loi(kq.issues), "do_luong": {"da_giai": facts is not None, "ly_do": ly_do_do_luong},
                   "giu_cho": sorted(set(giu_cho)), "so_dong": len(kq.lines), "master_loi": master_loi,
                   "phap_nhan": mapping["phap_nhan_ma"] if mapping else None, "ngay_chung_tu": kq.business_date, "trang_thai_nguon": kq.source_state}
        ke_hoach = None if giu_cho else {"ket_qua_doc": kq, "mapping": mapping, "rows": rows, "master_sha": master_sha, "master_ref": master_ref,
                                          "master_rows": master_rows, "profile": profile}
        return ket_qua, rows, ke_hoach

    def _lap_promote(self, c, dt, scope, kh) -> dict:
        """Kế hoạch promote pin vào stage: khóa danh tính + đọc lịch sử repository DƯỚI khóa (thứ tự chung), phân loại bằng classifier frozen;
        facts typed/native/quantity/precision là kết quả reader — consumer CSDL chỉ đọc lại từ stage."""
        kq, mapping, profile = kh["ket_qua_doc"], kh["mapping"], kh["profile"]
        so_phieu, ma_kho = kq.native_header.get("SoPhieu"), kq.native_header.get("MaKho")
        khoa = c.execute("SELECT kho.m5_khoa_phieu(%s, %s, %s, %s, %s, %s, %s::uuid) AS v",
                         (kq.logical_source_identity.source_instance, profile["reference_id"], profile["sha256"], scope["scope_ref"], so_phieu, ma_kho,
                          str(mapping["id"]))).fetchone()["v"]
        if khoa["hold"]:
            return {"hold": khoa["hold"], "phieu_id": khoa["phieu_id"], "so_phieu": so_phieu}
        try:
            summary = KhoHistorySummary.tu_dict(khoa["summary"])
        except DataError:
            summary = None  # lịch sử repository không đúng hình dạng → classifier báo HISTORY_UNAVAILABLE/HOLD, không đoán
        loai = phan_loai_quan_sat(kq, summary)
        don_vi = {}
        for r in kh["master_rows"]["DM_HangHoa"]:
            don_vi.setdefault(r.get("MaHang"), []).append(r.get("DVT_Goc"))
        lines = []
        for ln in kq.lines:
            nv = ln.native_values
            dvt = don_vi.get(nv.get("MaHang"), [])
            lines.append({"id_dong": nv.get("ID_Dong"), "locator": f"/lines/{ln.source_ordinal}", "stt": ln.source_ordinal + 1, "source_ordinal": ln.source_ordinal,
                          "ma_hang": nv.get("MaHang") if isinstance(nv.get("MaHang"), str) else None, "native_values": chuan_hoa_so(ra_json(nv)),
                          "quantity_json_kind": ln.quantity_json_kind, "so_luong_raw": ln.quantity_text, "so_luong": ln.normalized_quantity_text,
                          "precision_state": ln.precision_state, "dvt_raw": dvt[0] if len(dvt) == 1 and isinstance(dvt[0], str) else None,
                          "unit_definition_ref": ln.unit_definition_ref})
        chon = sorted(((r["section"], r["locator"], r["row_raw_sha256"]) for r in kh["rows"]
                       if r["section"] in ("GD_Phieu", "GD_Dong") or r["source_key"] in self._ma_tham_chieu(kq)))
        content_id = str(uuid.uuid4())
        inst = kq.logical_source_identity.source_instance
        khoa_chieu = "KHO10_PHIEU:v1:" + sha256(canonical_json({"content_id": content_id, "logical_source_key": {"SoPhieu": so_phieu},
                                                                 "semantic_sha256": kq.semantic_digest, "source_instance": inst}).encode("utf-8"))
        h = kq.native_header
        p = {"hold": None, "mapping_revision_id": str(mapping["id"]), "ma_kho": ma_kho, "so_phieu": so_phieu,
             "ngay_chung_tu": kq.business_date, "summary_kind": khoa["summary"]["summary_kind"], "latest_truoc": khoa.get("latest_observation_id"),
             "semantic_sha256": kq.semantic_digest, "request_sha256": kq.request_digest, "native_header": chuan_hoa_so(ra_json(h)),
             "loai_phieu_raw": h.get("LoaiPhieu"), "trang_thai_raw": h.get("TrangThai"), "trang_thai_nguon": kq.source_state,
             "ma_doi_tac": h.get("MaDoiTac") if isinstance(h.get("MaDoiTac"), str) and h.get("MaDoiTac") else None,
             "nguoi_duyet_nguon": h.get("NguoiDuyet") or None, "thoi_diem_duyet_nguon": h.get("ThoiDiemDuyet") or None,
             "master_raw_sha256": kh["master_sha"], "master_reference_id": kh["master_ref"],
             "related_master_facts": chuan_hoa_so(ra_json(kq.semantic_envelope.get("related_master_facts"))),
             "content_id_moi": content_id, "khoa_nguon_chieu": khoa_chieu, "lines": lines,
             "selected_rows_sha256": sha256(canonical_json(chon).encode("utf-8")),
             "phan_loai": list(loai.reason_codes), "history_state": loai.history_state, "can_xem_xet": loai.needs_review}
        return p

    @staticmethod
    def _ma_tham_chieu(kq) -> set:
        rel = kq.semantic_envelope.get("related_master_facts")
        out = set()
        for section, (khoa, _) in MASTER_WHITELIST.items():
            arr = rel.get(section)
            for r in (arr.items if arr is not None else ()):
                out.add(r.get(khoa))
        return out

    # ------------------------------------------------------------------ đọc nguồn (trước PN): danh sách capture, chi tiết, raw
    def nguon_danh_sach(self, dang_nhap) -> list[dict]:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            return nguon_chung.danh_sach_lan_nhan(self.conn)

    def nguon_chi_tiet(self, dang_nhap, receipt_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            v = nguon_chung.doc_lan_nhan(self.conn, receipt_id)
        if v is None:
            raise DataError("NGUON_KHONG_CO_QUYEN", "Không thấy lần nhận này hoặc phiên chưa có READ_SOURCE của nguồn.")
        return v

    def nguon_raw(self, dang_nhap, receipt_id, vai_tro) -> tuple[str, bytes]:
        dt = self.danh_tinh(dang_nhap)
        if vai_tro not in (VAI_TRO_NATIVE, VAI_TRO_MASTER):
            raise DataError("NGUON_VAI_TRO_LA", "Vai trò artifact không hợp lệ.")
        with self._tx(dt):
            meta, raw = nguon_chung.doc_tep(self.conn, self.root, receipt_id, vai_tro)
        return f"{vai_tro}-{meta['raw_sha256'][:12]}.json", raw

    def nang_luc_cua_toi(self, dang_nhap) -> list[dict]:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            return [dict(r) for r in self.conn.execute("""SELECT c.source_instance_id, c.profile_ref, c.hanh_dong, p.ma AS phap_nhan_dich
                                                          FROM master.nang_luc_nguon c LEFT JOIN master.phap_nhan p ON p.id = c.target_phap_nhan_id
                                                          ORDER BY 1, 3, 4""")]

    def pham_vi_cua_toi(self, dang_nhap) -> list[dict]:
        """Phạm vi cấu hình + coverage cho form nhận file — chỉ nguồn mà phiên có năng lực hiện hành (RLS metadata theo năng lực nguồn)."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            return [{"source_instance_id": r["source_instance_id"], "scope_ref": r["scope_ref"], "ma_kho": r["ma_kho"], "so_phieu": r["so_phieu"],
                     "coverage_values": list(r["payload"].get("coverage_values") or [])}
                    for r in self.conn.execute("""SELECT s.source_instance_id, s.scope_ref, s.ma_kho, s.so_phieu, p.payload FROM master.nguon_pham_vi s
                                                  JOIN master.nguon_profile p ON p.source_instance_id = s.source_instance_id AND p.profile_ref = s.profile_ref
                                                   AND p.profile_sha256 = s.profile_sha256 ORDER BY 1, 2""")]

    # ------------------------------------------------------------------ nghiệp vụ M5: danh sách / chi tiết / lịch sử
    def danh_sach(self, dang_nhap, *, phap_nhan=None, ma_kho=None, ky=None, trang_thai=None, trang=1, co=50) -> dict:
        dt = self.danh_tinh(dang_nhap)
        pns = quyen.pham_vi(dt, "M5_READ")
        if not pns:
            raise DataError("KHONG_CO_QUYEN_MODULE", "Người dùng không có quyền xem M5 trên pháp nhân nào.")
        if trang_thai is not None and trang_thai not in TRANG_THAI_TRUY_VAN:
            raise DataError("LOC_TRANG_THAI", "Bộ lọc trạng thái nguồn không hợp lệ.")
        if ky is not None and (not isinstance(ky, str) or len(ky) != 7 or ky[4] != "-"):
            raise DataError("LOC_KY", "Kỳ phải dạng YYYY-MM.")
        trang, co = max(1, int(trang)), min(100, max(1, int(co)))
        with self._tx(dt):
            rows = [dict(r) for r in self.conn.execute(
                """SELECT d.id, p.ma AS phap_nhan, d.source_instance_id, d.so_phieu_key, d.ma_kho, d.latest_observation_id, d.accepted_source_observation_id,
                          d.eligible_content_id, o.trang_thai_nguon, o.phan_loai, o.history_state, o.can_xem_xet, o.known_at, v.ngay_chung_tu, v.version,
                          (SELECT count(*) FROM kho.phieu_kho_phien_ban x WHERE x.phieu_id = d.id) AS so_noi_dung,
                          (SELECT count(*) FROM kho.phieu_kho_quan_sat x WHERE x.phieu_id = d.id) AS so_quan_sat, count(*) OVER () AS tong
                   FROM kho.phieu_kho_danh_tinh d JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
                   LEFT JOIN kho.phieu_kho_quan_sat o ON o.id = d.latest_observation_id
                   LEFT JOIN kho.phieu_kho_phien_ban v ON v.id = o.content_id
                   WHERE d.phap_nhan_id = ANY(%s::uuid[]) AND (%s::text IS NULL OR p.ma = %s::text) AND (%s::text IS NULL OR d.ma_kho = %s::text)
                     AND (%s::text IS NULL OR to_char(v.ngay_chung_tu, 'YYYY-MM') = %s::text) AND (%s::text IS NULL OR o.trang_thai_nguon = %s::text)
                   ORDER BY v.ngay_chung_tu DESC NULLS LAST, d.so_phieu_key, d.id LIMIT %s OFFSET %s""",
                (pns, phap_nhan, phap_nhan, ma_kho, ma_kho, ky, ky, trang_thai, trang_thai, co, (trang - 1) * co))]
            viec = [dict(r) for r in self.conn.execute("""SELECT v.id, p.ma AS phap_nhan, v.loai, v.tham_chieu_id, v.tom_tat, v.ly_do_cho, v.trang_thai
                                                          FROM kho.viec_can_duyet v JOIN master.phap_nhan p ON p.id = v.phap_nhan_id
                                                          WHERE v.module = 'M5' AND v.trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG') ORDER BY v.tao_luc""")]
            file_soat = [dict(r) for r in self.conn.execute("""SELECT l.id, p.ma AS phap_nhan, l.du_lieu->>'ten' AS ten, l.hash, l.xuat_luc AS luc
                                                               FROM kho.lo_xuat l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                                                               WHERE l.du_lieu->>'module' = 'M5' ORDER BY l.xuat_luc DESC""")]
        tong = rows[0]["tong"] if rows else 0
        phieu = [{"id": str(r["id"]), "phap_nhan": r["phap_nhan"], "nguon": r["source_instance_id"], "so_phieu": r["so_phieu_key"], "ma_kho": r["ma_kho"],
                  "ngay": r["ngay_chung_tu"].isoformat() if r["ngay_chung_tu"] else None, "trang_thai_nguon": r["trang_thai_nguon"],
                  "phan_loai": list(r["phan_loai"] or []), "history_state": r["history_state"], "can_xem_xet": r["can_xem_xet"],
                  "latest_observation_id": _s(r["latest_observation_id"]), "accepted_source_observation_id": _s(r["accepted_source_observation_id"]),
                  "eligible_content_id": _s(r["eligible_content_id"]), "so_noi_dung": r["so_noi_dung"], "so_quan_sat": r["so_quan_sat"]} for r in rows]
        return {"nguoi": self._nguoi(dt), "phieu": phieu, "trang": trang, "co": co, "tong": tong,
                "viec": [{**v, "id": str(v["id"]), "tham_chieu_id": str(v["tham_chieu_id"]), "ly_do_cho": list(v["ly_do_cho"])} for v in viec],
                "file_soat": [{**f, "id": str(f["id"]), "luc": f["luc"].isoformat() if f["luc"] else None} for f in file_soat], "l11": L11_THONG_BAO}

    def _nguoi(self, dt) -> dict:
        return {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"],
                "phap_nhan": sorted(dt["quyen"][pn]["ma"] for pn in quyen.pham_vi(dt, "M5_READ")),
                "hanh_dong": sorted(h for h in ("M5_READ", "M5_FILE_SOAT", "M5_MAP_V4", "M5_SOURCE_REVIEW_V8") if quyen.pham_vi(dt, h))}

    def chi_tiet(self, dang_nhap, phieu_id) -> dict:
        """Display graph + token basis FILE từ CÙNG một snapshot (_tx_doc); quyền/kỳ/basis hiện hành vẫn kiểm lại tại lúc xuất file."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx_doc(dt):
            d = self.conn.execute("""SELECT d.*, p.ma AS phap_nhan FROM kho.phieu_kho_danh_tinh d JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
                                     WHERE d.id = %s""", (phieu_id,)).fetchone()
            if not d:
                raise DataError("PHIEU_KHO", "Không thấy phiếu kho (hoặc ngoài quyền).")
            quyen.kiem(dt, "M5_READ", d["phap_nhan_id"])
            versions = [dict(v) for v in self.conn.execute("SELECT * FROM kho.phieu_kho_phien_ban WHERE phieu_id = %s ORDER BY version", (phieu_id,))]
            lines = [dict(r) for r in self.conn.execute("""SELECT lv.*, dd.id_dong_nguon FROM kho.phieu_kho_dong_phien_ban lv
                                                          JOIN kho.phieu_kho_dong_danh_tinh dd ON dd.id = lv.dong_id
                                                          WHERE lv.phieu_id = %s ORDER BY lv.stt""", (phieu_id,))]
            obs = [dict(o) for o in self.conn.execute("SELECT * FROM kho.phieu_kho_quan_sat WHERE phieu_id = %s ORDER BY thu_tu", (phieu_id,))]
            maps = [dict(m) for m in self.conn.execute("""SELECT id, reference_id, revision, subject_key, state, valid_from, valid_to, nguon_quyet_dinh, duyet_boi
                                                          FROM master.anh_xa_nguon WHERE id = %s OR (source_instance_id = %s AND subject_key = %s)
                                                          ORDER BY revision""", (d["mapping_revision_id"], d["source_instance_id"], d["ma_kho"]))]
            viec = [dict(v) for v in self.conn.execute("SELECT id, loai, tom_tat, ly_do_cho, trang_thai FROM kho.viec_can_duyet WHERE tham_chieu_id = %s ORDER BY tao_luc",
                                                       (phieu_id,))]
            # token basis toàn graph do CSDL dẫn xuất trong CÙNG snapshot REPEATABLE READ với mọi SELECT hiển thị ở trên (UI gửi lại làm expected)
            co_so = self.conn.execute("SELECT kho.m5_co_so_file(%s::uuid) AS v", (phieu_id,)).fetchone()["v"]
        theo_ban = {}
        for r in lines:
            theo_ban.setdefault(str(r["phien_ban_id"]), []).append({
                "stt": r["stt"], "id_dong": r["id_dong_nguon"], "source_ordinal": r["source_ordinal"], "ma_hang": r["ma_hang_raw"], "native": r["native_values"],
                "loai_so_luong": r["quantity_json_kind"], "so_luong_nguon": r["so_luong_raw"],
                "so_luong_chuan_hoa": r["so_luong_raw"] if r["so_luong"] is not None else None, "do_chinh_xac": r["precision_state"], "dvt_nguon": r["dvt_raw"],
                "don_vi": r["unit_definition_ref"], "chung_tu_dong_id": _s(r["chung_tu_dong_id"])})
        return {
            "id": str(d["id"]), "phap_nhan": d["phap_nhan"], "nguon": d["source_instance_id"], "so_phieu": d["so_phieu_key"], "ma_kho": d["ma_kho"],
            "con_tro": {"latest_observation_id": _s(d["latest_observation_id"]), "accepted_source_observation_id": _s(d["accepted_source_observation_id"]),
                        "eligible_content_id": _s(d["eligible_content_id"])},
            "co_so_file": co_so,
            "noi_dung": [{"id": str(v["id"]), "version": v["version"], "semantic_sha256": v["semantic_sha256"], "header": v["native_header"],
                          "trang_thai_raw": v["trang_thai_raw"], "trang_thai_nguon": v["trang_thai_nguon"], "ngay": v["ngay_chung_tu"].isoformat(),
                          "master_raw_sha256": v["master_raw_sha256"], "master_reference_id": v["master_reference_id"], "master": v["related_master_facts"],
                          "khoa_nguon_chieu": v["khoa_nguon_chieu"], "chung_tu_id": _s(v["chung_tu_id"]), "dong": theo_ban.get(str(v["id"]), [])} for v in versions],
            "lich_su": [{"id": str(o["id"]), "thu_tu": o["thu_tu"], "content_id": str(o["content_id"]), "lan_tiep_nhan_id": str(o["lan_tiep_nhan_id"]),
                         "trang_thai_nguon": o["trang_thai_nguon"], "request_sha256": o["request_sha256"], "phan_loai": list(o["phan_loai"]),
                         "history_state": o["history_state"], "can_xem_xet": o["can_xem_xet"], "known_at": o["known_at"].isoformat(),
                         "predecessor": _s(o["predecessor_observation_id"])} for o in obs],
            "anh_xa": [{**m, "id": str(m["id"]), "valid_from": m["valid_from"].isoformat(), "valid_to": m["valid_to"].isoformat() if m["valid_to"] else None}
                       for m in maps],
            "viec": [{**v, "id": str(v["id"]), "ly_do_cho": list(v["ly_do_cho"])} for v in viec],
            "l11": L11_THONG_BAO,
            "duoc": {h: quyen.duoc(dt, h, d["phap_nhan_id"]) for h in ("M5_FILE_SOAT", "M5_SOURCE_REVIEW_V8", "M5_MAP_V4")}}

    # ------------------------------------------------------------------ POST /api/m5/nguon/kiem-lai — review nguồn V8 (expected graph)
    def kiem_lai_nguon(self, dang_nhap, yeu_cau: dict) -> dict:
        """Quyền hiện hành kiểm ở Python RỒI CSDL (CFO + M5 + V8) TRƯỚC tra biên nhận/replay; hash yêu cầu, khóa, expected pointers, chỉ quan sát mới
        nhất, biên nhận/kết quả/nhật ký đều do kho.m5_xem_xet_nguon dẫn xuất trong cùng giao dịch. Body chỉ mang expected refs/quyết định/lý do."""
        dt = self.danh_tinh(dang_nhap)
        khoa = nguon_chung.kiem_khoa(yeu_cau.get("khoa"))
        ly_do = yeu_cau.get("ly_do")
        if not isinstance(ly_do, str) or not ly_do.strip():
            raise DataError("LY_DO", "Cần lý do review nguồn.")
        if yeu_cau.get("quyet_dinh") not in ("CHAP_NHAN_NGUON", "GIU_CHO"):
            raise DataError("M5_QUYET_DINH_SAI", "Quyết định chỉ CHAP_NHAN_NGUON hoặc GIU_CHO.")
        than = {k: yeu_cau.get(k) for k in ("phieu_id", "observation_id", "quyet_dinh", "accepted_truoc", "eligible_truoc", "latest_truoc", "ly_do")}
        with self._tx(dt):
            d = self.conn.execute("SELECT phap_nhan_id FROM kho.phieu_kho_danh_tinh WHERE id = %s", (than["phieu_id"],)).fetchone()
            if not d:
                raise DataError("PHIEU_KHO", "Không thấy phiếu kho (hoặc ngoài quyền).")
            quyen.kiem(dt, "M5_SOURCE_REVIEW_V8", d["phap_nhan_id"])
            return self.conn.execute("SELECT kho.m5_xem_xet_nguon(%s::jsonb) AS v",
                                     (json.dumps({**than, "client_key": khoa}, ensure_ascii=False),)).fetchone()["v"]

    # ------------------------------------------------------------------ POST /api/m5/mapping — revision mapping WAREHOUSE (SOURCE_MAP + M5_MAP_V4)
    def cap_nhat_mapping(self, dang_nhap, yeu_cau: dict) -> dict:
        """S07: mọi ghi mapping qua kho.m5_anh_xa_v4 (ĐỒNG THỜI SOURCE_MAP đúng PN đích + CFO V4 + M5 kiểm trước replay; retarget đóng bản cũ với quyền
        trên PN cũ, mở việc ảnh hưởng, không chuyển danh tính). Python chỉ kiểm sớm cùng quy tắc; CSDL là cổng quyết định."""
        dt = self.danh_tinh(dang_nhap)
        khoa = nguon_chung.kiem_khoa(yeu_cau.get("khoa"))
        inst, ma_kho, pn_ma = yeu_cau.get("source_instance"), yeu_cau.get("ma_kho"), yeu_cau.get("phap_nhan")
        rev = yeu_cau.get("revision_hien_tai")
        ly_do = yeu_cau.get("ly_do")
        if not all(isinstance(x, str) and x for x in (inst, ma_kho, pn_ma, ly_do)) or isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
            raise DataError("M5_MAPPING_YEU_CAU", "Cần instance, kho nguồn, pháp nhân đích, revision cuối đã biết (expected) và lý do.")
        pn = self._pn(pn_ma)
        quyen.kiem(dt, "M5_MAP_V4", pn)
        with self._tx(dt):  # năng lực SOURCE_MAP đúng instance/profile/PN đích kiểm trong CSDL (không lộ metadata nguồn cho người không có năng lực)
            return self.conn.execute("SELECT kho.m5_anh_xa_v4(%s::jsonb) AS v",
                                     (json.dumps({"source_instance": inst, "ma_kho": ma_kho, "phap_nhan": pn_ma, "revision_hien_tai": rev, "ly_do": ly_do,
                                                  "client_key": khoa}, ensure_ascii=False),)).fetchone()["v"]

    # ------------------------------------------------------------------ kiểm kê / tồn nguồn: chỉ snapshot producer thật — hiện chưa có
    def kiem_ke(self, dang_nhap) -> dict:
        dt = self.danh_tinh(dang_nhap)
        if not quyen.pham_vi(dt, "M5_READ"):
            raise DataError("KHONG_CO_QUYEN_MODULE", "Người dùng không có quyền xem M5.")
        return {"trang_thai": "CHUA_CO_SNAPSHOT_PRODUCER", "du_lieu": [], "gioi_han": KHONG_PRODUCER}

    def ton_nguon(self, dang_nhap) -> dict:
        return {**self.kiem_ke(dang_nhap), "pham_vi": "UNKNOWN", "as_of": None}

    # ------------------------------------------------------------------ file soát M5 (SR2/SR3/I4): stage FILE_SOAT + receipt + registry cùng giao dịch
    def xuat_file_soat(self, dang_nhap, yeu_cau: dict) -> dict:
        """Một giao dịch trên kết nối chủ: danh tính → quyền FILE hiện hành (Python + CSDL) TRƯỚC tra biên nhận → khóa logic → expected
        latest/accepted/eligible + kỳ mở → snapshot nhất quán đọc dưới khóa → workbook (text/formula-safe) → ghi độc quyền m5-xuat/<sha>.xlsx +
        kiểm lại SHA/độ dài → stage FILE_SOAT bất biến → consumer CSDL dẫn xuất lô/biên nhận. Cùng khóa + cùng yêu cầu = cùng lô/file (0 delta)."""
        dt = self.danh_tinh(dang_nhap)
        khoa = nguon_chung.kiem_khoa(yeu_cau.get("khoa"))
        phieu_id = yeu_cau.get("phieu_id")
        if not isinstance(phieu_id, str) or not phieu_id:
            raise DataError("PHIEU_KHO", "Cần phiếu kho.")
        # repair03 §4: expected = ba con trỏ + TOKEN basis toàn graph do CSDL dẫn xuất lúc xem (chi_tiet.co_so_file); client không gửi facts
        mong = {k: yeu_cau.get(k) for k in ("latest_truoc", "accepted_truoc", "eligible_truoc", "co_so_truoc")}
        if not isinstance(mong["co_so_truoc"], str) or not _SHA.fullmatch(mong["co_so_truoc"]):
            raise DataError("M5_CO_SO_FILE", "Cần token basis file soát đang xem (mở lại chi tiết phiếu).")
        with self._tx_chu(dt) as c:
            d = c.execute("SELECT phap_nhan_id FROM kho.phieu_kho_danh_tinh WHERE id = %s", (phieu_id,)).fetchone()
            if not d or not quyen.duoc(dt, "M5_READ", d["phap_nhan_id"]):
                raise DataError("PHIEU_KHO", "Không thấy phiếu kho (hoặc ngoài quyền).")
            quyen.kiem(dt, "M5_FILE_SOAT", d["phap_nhan_id"])
            bd = c.execute("SELECT kho.m5_file_bat_dau(%s::jsonb) AS v",
                           (json.dumps({"phieu_id": phieu_id, "client_key": khoa, **mong}, ensure_ascii=False),)).fetchone()["v"]
            if bd["lap_lai"]:
                return {**bd["ket_qua"], "lap_lai": True}
            snap = bd["snapshot"]
            raw, so_dong = self._workbook(snap)
            digest = sha256(raw)
            path = self.root / "m5-xuat" / f"{digest}.xlsx"
            write_immutable(path, raw)
            if sha256(path.read_bytes()) != digest:
                raise DataError("ARTIFACT_CHANGED", "File soát sau khi ghi không khớp hash — giữ nguyên làm bằng chứng, không ghi lô.")
            ten = f"FILE-SOAT-M5-{snap['so_phieu']}-{digest[:8]}.xlsx"
            du_lieu = {"phieu_id": phieu_id, **mong, "ky": snap["ky"], "artifact_sha256": digest, "byte_length": len(raw), "ten": ten, "so_dong": so_dong,
                       "snapshot_sha256": sha256(canonical_json(snap).encode("utf-8")), "co_so_sha256": snap["co_so_sha256"]}
            stage = nguon_chung.ghi_stage(c, dt, muc_dich="FILE_SOAT", client_key=khoa, h=bd["h"], source_instance=snap["source_instance_id"],
                                          profile_ref=snap["profile_ref"], profile_sha256=snap["profile_sha256"], du_lieu=du_lieu,
                                          phap_nhan_id=snap["phap_nhan_id"])
            return c.execute("SELECT kho.m5_file_tieu_thu(%s::uuid, %s) AS v", (stage, bd["h"])).fetchone()["v"]

    @staticmethod
    def _workbook(snap: dict) -> tuple[bytes, int]:
        """Workbook từ snapshot CSDL đọc dưới khóa: mọi ô là text (formula-safe =,+,-,@), số lượng nguyên văn; NULL ≠ 0; không tiền/giá trị/bút toán."""
        from ..xuat import excel
        t = lambda v: None if v is None else str(v)  # noqa: E731
        phieu_rows = [[snap["phap_nhan"], snap["source_instance_id"], snap["so_phieu"], snap["ma_kho"], t(snap["latest_observation_id"]),
                       t(snap["accepted_source_observation_id"]), t(snap["eligible_content_id"]), L11_THONG_BAO]]
        dong_rows = [[t(v["version"]), v["semantic_sha256"], t(v["ngay_chung_tu"]), v["trang_thai_raw"], v["trang_thai_nguon"], t(l["stt"]), l["id_dong"],
                      t(l["source_ordinal"]), l["ma_hang"], l["loai_so_luong"], l["so_luong_nguon"], l["so_luong_nguon"] if l["co_chuan_hoa"] else None,
                      l["do_chinh_xac"], l["dvt_nguon"], l["don_vi"], v["khoa_nguon_chieu"], t(v["chung_tu_id"]), t(l["chung_tu_dong_id"])]
                     for v in snap["noi_dung"] for l in v["dong"]]
        obs_rows = [[t(o["thu_tu"]), t(o["id"]), t(o["lan_tiep_nhan_id"]), t(o["content_id"]), o["trang_thai_nguon"], o["request_sha256"],
                     ",".join(o["phan_loai"] or []), o["history_state"], "CÓ" if o["can_xem_xet"] else "", t(o["known_at"])] for o in snap["quan_sat"]]
        wb = excel.workbook()
        excel.table(wb, "PHIEU", ["phap_nhan", "nguon", "so_phieu", "ma_kho", "latest_observation", "accepted_source_observation", "eligible_content",
                                  "lien_ket_L11"], phieu_rows)
        excel.table(wb, "DONG_NGUON", ["phien_ban_noi_dung", "semantic_sha256", "ngay_chung_tu", "trang_thai_nguon_raw", "trang_thai_nguon", "stt", "ID_Dong",
                                       "thu_tu_nguon", "MaHang", "loai_so_luong", "so_luong_nguon_text", "so_luong_chuan_hoa_text", "do_chinh_xac", "DVT_nguon",
                                       "don_vi_dinh_nghia", "khoa_nguon_chieu", "chung_tu_core", "chung_tu_dong_core"], dong_rows)
        excel.table(wb, "LICH_SU_QUAN_SAT", ["thu_tu", "observation", "lan_tiep_nhan", "content", "trang_thai_nguon", "request_sha256", "ly_do_hold",
                                             "history_state", "can_xem_xet", "known_at"], obs_rows)
        # repair03 §4: provenance/basis đầy đủ (token + refs mapping/nội dung/quan sát/capture/bundle/vai trò/master/đo lường/kỳ) và dòng nguồn capture
        # (raw token/loại/validation/lỗi) để đối chiếu thực tế; mọi ô text, NULL để trống (không 0)
        excel.table(wb, "CO_SO", ["muc", "gia_tri"], KhoSoLuongK2._dong_co_so(snap.get("co_so") or {}, snap.get("co_so_sha256")))
        excel.table(wb, "DONG_NGUON_CAPTURE", ["vai_tro", "section", "locator", "thu_tu", "row_raw_sha256", "loai_so_luong", "so_luong_text",
                                               "validation_state", "ma_loi"],
                    [[b["vai_tro"], b["section"], b["locator"], t(b["thu_tu"]), b["row_raw_sha256"], b["quantity_json_kind"], b["quantity_text"],
                      b["validation_state"], ",".join(b["error_codes"] or [])] for b in (snap.get("co_so") or {}).get("dong_nguon") or []])
        excel.table(wb, "CANH_BAO", ["noi_dung"], [["DEMO — dữ liệu mô phỏng, nguồn chưa xác minh triển khai"],
                                                   ["Chỉ số lượng/chứng từ nguồn — KHÔNG tồn kho, KHÔNG giá trị/giá vốn, KHÔNG bút toán, KHÔNG file nhập Junsky"],
                                                   ["Số lượng giữ nguyên văn bản nguồn; chuẩn hóa chỉ khi đo lường đã chứng minh (DEMO); trống = NULL, không phải 0"],
                                                   [L11_THONG_BAO]])
        return excel.to_bytes(wb), len(dong_rows)

    @staticmethod
    def _dong_co_so(b: dict, token) -> list[list]:
        """Basis → cặp (mục, giá trị) text theo thứ tự cố định; giá trị NULL giữ None (ô trống), boolean → TRUE/FALSE."""
        def t(v):
            return None if v is None else ("TRUE" if v is True else "FALSE" if v is False else str(v))
        g = lambda *ks: _lay(b, ks)  # noqa: E731
        out = [["co_so_sha256", t(token)], ["contract", t(b.get("contract"))]]
        for k in ("id", "reference_id", "revision", "state", "dong", "phap_nhan_id", "nguon_quyet_dinh"):
            out.append([f"mapping.{k}", t(g("mapping", k))])
        out.append(["mapping_hien_hanh", t(",".join(str(m.get("id")) for m in b.get("mapping_hien_hanh") or []))])
        for k in ("id", "version", "semantic_sha256", "profile_ref", "profile_sha256", "mapping_revision_id", "first_snapshot_id", "master_raw_sha256",
                  "master_reference_id", "khoa_nguon_chieu", "chung_tu_id", "ngay_chung_tu", "trang_thai_raw", "trang_thai_nguon"):
            out.append([f"noi_dung_chon.{k}", t(g("noi_dung_chon", k))])
        for k in ("id", "thu_tu", "lan_tiep_nhan_id", "snapshot_id", "trang_thai_nguon", "request_sha256", "history_state", "can_xem_xet", "scope_ref"):
            out.append([f"quan_sat_chon.{k}", t(g("quan_sat_chon", k))])
        out.append(["quan_sat_chon.phan_loai", t(",".join(g("quan_sat_chon", "phan_loai") or []))])
        for k in ("id", "capture_sha256", "scope_ref", "profile_ref", "profile_sha256", "coverage", "coverage_hieu_luc", "snapshot_id", "bundle_sha256",
                  "bundle_state"):
            out.append([f"capture.{k}", t(g("capture", k))])
        out.append(["capture.reported_errors", t(",".join(g("capture", "reported_errors") or []))])
        for r in g("capture", "vai_tro") or []:
            out.append([f"capture.vai_tro.{r.get('vai_tro')}", t(f"co_mat={t(r.get('co_mat'))};raw_sha256={r.get('raw_sha256')};"
                                                                 f"byte_length={r.get('byte_length')};media_type={r.get('media_type')};"
                                                                 f"ly_do_vang={r.get('ly_do_vang')}")])
        for k in ("reference_id", "raw_sha256", "byte_length"):
            out.append([f"master.{k}", t(g("master", k))])
        for f in b.get("do_luong") or []:
            out.append([f"do_luong.{f.get('declaration_ref')}", t(f"id={f.get('id')};payload_sha256={f.get('payload_sha256')}")])
        out.append(["du_dieu_kien_so_luong", t(b.get("du_dieu_kien_so_luong"))])
        out.append(["ky", t(g("ky", "ky"))])
        out.append(["ky.da_khoa", t(g("ky", "da_khoa"))])
        out.append(["con_tro.latest", t(g("con_tro", "latest"))])
        out.append(["con_tro.accepted", t(g("con_tro", "accepted"))])
        out.append(["con_tro.eligible", t(g("con_tro", "eligible"))])
        return out

    def tep_file_soat(self, dang_nhap, lo_id) -> tuple[str, bytes]:
        """Tải ĐÚNG artifact đã xuất: lô M5 (chỉ consumer FILE_SOAT của chủ bảng tạo được), mục đích FILE_SOAT, đường dẫn đúng m5-xuat/<sha>.xlsx,
        SHA + độ dài khớp bytes; quyền FILE hiện hành trên PN. Không đọc đường dẫn khác (m0-raw/…) dù nằm trong thư mục gốc."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            lo = self.conn.execute("SELECT * FROM kho.lo_xuat WHERE id = %s AND du_lieu->>'module' = %s AND du_lieu->>'muc_dich' = 'FILE_SOAT'",
                                   (lo_id, MODULE)).fetchone()
            if not lo:
                raise DataError("FILE_SOAT", "Không thấy file soát M5 (hoặc ngoài quyền).")
            if lo["du_lieu"].get("che_do") == "L11_QUANTITY":  # chế độ do consumer chủ bảng ghi bất biến: file chéo cần BOTH READ + quyền file M5
                quyen.kiem_l11(dt, "FILE", lo["phap_nhan_id"])
            else:
                quyen.kiem(dt, "M5_FILE_SOAT", lo["phap_nhan_id"])
        sha, duong_dan = lo["hash"], lo["duong_dan"]
        if not isinstance(sha, str) or not _SHA.fullmatch(sha) or duong_dan != f"m5-xuat/{sha}.xlsx":
            raise DataError("FILE_SOAT", "Lô không trỏ đúng artifact file soát M5.")
        path = (self.root / duong_dan).resolve()
        if not path.is_relative_to((self.root / "m5-xuat").resolve()):
            raise DataError("FILE_SOAT", "Đường dẫn file soát không hợp lệ.")
        raw = path.read_bytes()
        if sha256(raw) != sha or len(raw) != int(lo["du_lieu"].get("byte_length", -1)):
            raise DataError("ARTIFACT_CHANGED", "File soát đã bị thay đổi.")
        return lo["du_lieu"]["ten"], raw

    # ================================================================== L11 SỐ LƯỢNG (R16, docs/GIAO-CODE-L11-QUANTITY-01.md)
    # Bằng chứng: COMMON capture (raw bytes/hash/độ dài → receipt) + stage L11_PROOF → candidate thô trong MỘT giao dịch chủ; CFO BOTH V4 xác nhận.
    # Mã hóa nguồn / preview / xác nhận / undo / FILE: hàm CSDL kho.l11_* (quyền hiện hành trước tra biên nhận, khóa gốc→pool, CAS, ngân sách).
    @staticmethod
    def _doc_json_bang_chung(raw: bytes):
        """JSON UTF-8 nghiêm: không BOM, không khóa trùng, số chỉ là số nguyên (float/NaN → không đọc được, giữ raw, CSDL HOLD)."""
        def cap(pairs):
            ket = {}
            for k, v in pairs:
                if k in ket:
                    raise ValueError("khóa trùng")
                ket[k] = v
            return ket

        def tu_choi(_):
            raise ValueError("số không nguyên")
        if raw.startswith(b"\xef\xbb\xbf"):
            return None, "L11_JSON_BOM"
        try:
            v = json.loads(raw.decode("utf-8"), object_pairs_hook=cap, parse_float=tu_choi, parse_constant=tu_choi)
        except (UnicodeDecodeError, ValueError):
            return None, "L11_JSON_KHONG_DOC_DUOC"
        if not isinstance(v, dict):
            return None, "L11_JSON_KHONG_PHAI_OBJECT"
        return v, None

    def l11_nhan_bang_chung(self, dang_nhap: str, *, source_instance: str, scope_ref: str, coverage: str, reported_errors=nguon_chung.VANG,
                            client_key: str, native: bytes | None = None, fixture_ref: str | None = None) -> dict:
        """Nhận MỘT bằng chứng (bytes thực hoặc fixture_ref whitelisted) vào nguồn bằng chứng L11: INTAKE hiện hành trước tra cứu; PN/kind/ref do cấu
        hình suy; raw candidate + biên nhận + kết quả cuối trong một giao dịch chủ. Không phải duyệt."""
        from . import l11_demo
        dt = self.danh_tinh(dang_nhap)
        nguon_chung.kiem_khoa(client_key)
        if (native is None) == (fixture_ref is None):
            raise DataError("L11_YEU_CAU_SAI", "Cần đúng một trong: bytes bằng chứng (base64) hoặc mẫu bằng chứng DEMO.")
        if fixture_ref is not None:
            _, native = l11_demo.mau_bang_chung(fixture_ref)
        if not isinstance(native, (bytes, bytearray)) or not native:
            raise DataError("NGUON_ARTIFACT", "Cần bytes thực của bằng chứng JSON.")
        native = bytes(native)
        loi_bao = nguon_chung.kiem_ma_loi(reported_errors)
        with self._tx_chu(dt) as c:
            profile = nguon_chung.doc_profile(c, source_instance)
            if profile["payload"].get("purpose") != "L11_PROOF":
                raise DataError("L11_PROFILE_SAI", "Instance không phải nguồn bằng chứng L11.")
            quyen.kiem_nguon(c, source_instance, profile["reference_id"], profile["sha256"], "INTAKE")
            cu = nguon_chung.tim_lan_nhan(c, source_instance, profile, client_key)
            scope = nguon_chung.doc_pham_vi(c, source_instance, profile, scope_ref)
            if scope["scope_kind"] != "L11_EVIDENCE_SET" or not scope["phap_nhan_id"]:
                raise DataError("L11_PHAM_VI_SAI", "Phạm vi không phải L11_EVIDENCE_SET có PN.")
            arts = nguon_chung.artifacts(profile, {"NATIVE": native})
            env = nguon_chung.phong_bi_capture(source_instance, profile, scope, coverage, loi_bao, arts)
            h = nguon_chung.bam_capture(env)
            if cu is not None:
                if cu["capture_sha256"] != h:
                    raise DataError("CAPTURE_KHAC_NOI_DUNG", "Khóa đã dùng cho bằng chứng/phạm vi/coverage/lỗi khác — không ghi artifact mới.")
                return self._phat_lai(cu, h)
            nguon_chung.ghi_blob(self.root, native)
            raw_sha = sha256(native)
            cau_hinh = next((r for r in profile["payload"]["proof_references"] if r.get("raw_sha256") == raw_sha), None)
            obj, loi_json = self._doc_json_bang_chung(native)
            rows = [] if obj is None else [{
                "vai_tro": "NATIVE", "section": "L11_PROOF_JSON", "locator": "/", "thu_tu": 0,
                "source_key": obj.get("reference_id") if isinstance(obj.get("reference_id"), str) else None, "row_raw": obj,
                "row_raw_sha256": nguon_chung.digest_payload(obj), "quantity_json_kind": None, "quantity_text": None, "validation_state": "HOP_LE",
                "error_codes": []}]
            cov_hl, ly_do_cov = nguon_chung.coverage_hieu_luc(coverage, arts, [])
            receipt_id = nguon_chung.receipt_id_moi()
            ket_qua = {"module": "L11", "raw_sha256": raw_sha, "byte_length": len(native), "coverage": coverage, "coverage_hieu_luc": cov_hl,
                       "ly_do_coverage": ly_do_cov, "json": "DOC_DUOC" if obj is not None else loi_json,
                       "tham_chieu_cau_hinh": cau_hinh["reference_id"] if cau_hinh else None, "kind": cau_hinh["kind"] if cau_hinh else None,
                       "ghi_chu": "Raw candidate — chưa phải duyệt; CFO hiện hành BOTH V4 xác nhận riêng."}
            du_lieu = nguon_chung.du_lieu_stage_capture(receipt_id=receipt_id, scope=scope, coverage=coverage, coverage_hl=cov_hl, envelope=env, arts=arts,
                                                       rows=rows, ket_qua=ket_qua, promote=None)
            du_lieu["l11_proof"] = True
            stage = nguon_chung.ghi_stage(c, dt, muc_dich="CAPTURE", client_key=client_key, h=h, source_instance=source_instance,
                                          profile_ref=profile["reference_id"], profile_sha256=profile["sha256"], du_lieu=du_lieu,
                                          phap_nhan_id=scope["phap_nhan_id"], module=profile["payload"].get("module"))
            ghi = nguon_chung.tieu_thu_capture(c, stage, h)
            if not ghi["moi"]:
                cu = nguon_chung.tim_lan_nhan(c, source_instance, profile, client_key)
                if cu is None or cu["capture_sha256"] != h:
                    raise DataError("CAPTURE_KHAC_NOI_DUNG", "Khóa capture đã dùng cho nội dung khác.")
                return self._phat_lai(cu, h)
            du_l11 = {"receipt_id": receipt_id, "raw_sha256": raw_sha, "reference_id": cau_hinh["reference_id"] if cau_hinh else None}
            h2 = sha256(canonical_json(du_l11).encode("utf-8"))
            stage2 = nguon_chung.ghi_stage(c, dt, muc_dich="L11_PROOF", client_key=client_key, h=h2, source_instance=source_instance,
                                           profile_ref=profile["reference_id"], profile_sha256=profile["sha256"], du_lieu=du_l11,
                                           phap_nhan_id=scope["phap_nhan_id"], module=profile["payload"].get("module"))
            c.execute("SELECT kho.l11_tieu_thu_bang_chung(%s::uuid, %s) AS v", (stage2, h2)).fetchone()
            cuoi = nguon_chung.chot_ket_qua(c, stage, h, bool(ghi["snapshot_moi"]), {"module": "L11"})
        return {**ket_qua, "lan_tiep_nhan_id": receipt_id, "capture_sha256": h, "lap_lai": False, **cuoi}

    def l11_bang_chung(self, dang_nhap) -> dict:
        """GET /api/m5/l11/proof — snapshot RR RIÊNG: approved (BOTH READ), raw candidate + facts chỉ khi có READ_SOURCE nguồn bằng chứng."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx_doc(dt):
            return self._l11_bang_chung_trong()

    def _l11_bang_chung_trong(self) -> dict:
        """Reader nội bộ — chạy TRONG snapshot đang mở của người gọi (không tự mở giao dịch). Phạm vi bằng chứng chỉ theo năng lực nguồn hiện hành."""
        ds = self.conn.execute("SELECT kho.l11_danh_sach_bang_chung() AS v").fetchone()["v"]
        pham_vi = [{"source_instance_id": r["source_instance_id"], "scope_ref": r["scope_ref"], "coverage_values": list(r["payload"].get("coverage_values") or [])}
                   for r in self.conn.execute("""SELECT s.source_instance_id, s.scope_ref, p.payload FROM master.nguon_pham_vi s
                                                 JOIN master.nguon_profile p ON p.source_instance_id = s.source_instance_id AND p.profile_ref = s.profile_ref
                                                  AND p.profile_sha256 = s.profile_sha256
                                                 WHERE s.scope_kind = 'L11_EVIDENCE_SET'
                                                   AND (master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'INTAKE', NULL)
                                                        OR master.ktt_nguon_duoc(s.source_instance_id, s.profile_ref, s.profile_sha256, 'READ_SOURCE', NULL))
                                                 ORDER BY 1, 2""")]
        return {"ung_vien": ds.get("ung_vien") or [], "bang_chung": ds.get("bang_chung") or [], "pham_vi_nguon": pham_vi}

    def l11_trang(self, dang_nhap) -> dict:
        """GET /api/m5/l11 (R4 repair02): TOÀN BỘ aggregate hiển thị (dòng/mã hóa/pool/parent/token FILE/bằng chứng/ứng viên/phạm vi/hành động) từ
        MỘT snapshot REPEATABLE READ trên MỘT kết nối; không ghép hai snapshot độc lập. Giữ từ chối mở trong giao dịch ngoài."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx_doc(dt):
            bc = self._l11_bang_chung_trong()
            try:
                tq = self._l11_tong_quan_trong(dt)
            except DataError as exc:  # thiếu BOTH READ: kiểm trước mọi SELECT (không lỗi CSDL trong giao dịch) → trang chỉ phần bằng chứng theo quyền nguồn
                if exc.code != "KHONG_CO_QUYEN_MODULE":
                    raise
                tq = {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"], "duoc": {k: False for k in ("READ", "LINK", "CFO", "FILE")}},
                      "khong_quyen": str(exc), "dong_hoa_don": [], "dong_phieu": [], "ma_hoa": [], "lien_ket": [], "bang_chung": []}
        return {**tq, "bang_chung": bc["bang_chung"] if "khong_quyen" not in tq else [], "ung_vien": bc["ung_vien"],
                "pham_vi_bang_chung": bc["pham_vi_nguon"]}

    def _l11_than(self, yeu_cau: dict, cho_phep: tuple) -> dict:
        from . import lien_ket_chung
        if not isinstance(yeu_cau, dict) or any(k in yeu_cau for k in lien_ket_chung.L11_KHONG_NHAN):
            raise DataError("L11_CLIENT_AUTHORITY", "PN/chủ sở hữu/hệ số/kind/duyệt do máy chủ dẫn xuất; không nhận từ trình duyệt.")
        if set(yeu_cau) - set(cho_phep):
            raise DataError("L11_YEU_CAU_SAI", "Yêu cầu L11 có trường ngoài phạm vi.")
        than = {k: yeu_cau.get(k) for k in cho_phep if k in yeu_cau}
        than["client_key"] = nguon_chung.kiem_khoa(than.pop("khoa", None))
        than["reason"] = than.pop("ly_do", None)
        return than

    def l11_xac_nhan_bang_chung(self, dang_nhap, yeu_cau: dict) -> dict:
        from . import lien_ket_chung
        dt = self.danh_tinh(dang_nhap)
        than = self._l11_than(yeu_cau, ("candidate_id", "expected_graph", "khoa", "ly_do"))
        with self._tx(dt):
            return lien_ket_chung.l11_goi(self.conn, "l11_xac_nhan_bang_chung", than)

    def l11_huy_bang_chung(self, dang_nhap, yeu_cau: dict) -> dict:
        from . import lien_ket_chung
        dt = self.danh_tinh(dang_nhap)
        than = self._l11_than(yeu_cau, ("proof_id", "expected_graph", "khoa", "ly_do"))
        with self._tx(dt):
            return lien_ket_chung.l11_goi(self.conn, "l11_huy_bang_chung", than)

    def l11_ma_hoa(self, dang_nhap, yeu_cau: dict) -> dict:
        from . import lien_ket_chung
        dt = self.danh_tinh(dang_nhap)
        than = self._l11_than(yeu_cau, ("side", "line_id", "proof_id", "expected_graph", "khoa", "ly_do"))
        if than.get("side") not in ("M2", "M5"):
            raise DataError("L11_YEU_CAU_SAI", "side chỉ M2 (dòng hóa đơn) hoặc M5 (dòng phiếu).")
        with self._tx(dt):
            return lien_ket_chung.l11_goi(self.conn, "l11_ma_hoa", than)

    def lien_ket(self, dang_nhap, hanh_dong: str, yeu_cau: dict) -> dict:
        """POST /api/m5/lien-ket/{preview,xac-nhan,huy}: preview đọc 0 ghi (snapshot nhất quán); xác nhận/undo qua hàm CSDL có guard."""
        from . import lien_ket_chung
        dt = self.danh_tinh(dang_nhap)
        than = lien_ket_chung.l11_yeu_cau(hanh_dong, yeu_cau)
        if hanh_dong == "preview":
            with self._tx_doc(dt):
                return lien_ket_chung.l11_goi(self.conn, "l11_xem_truoc", than)
        with self._tx(dt):
            return lien_ket_chung.l11_goi(self.conn, "l11_xac_nhan" if hanh_dong == "xac-nhan" else "l11_huy", than)

    def l11_tong_quan(self, dang_nhap) -> dict:
        """Picker DTO theo quyền BOTH READ hiện hành, một snapshot REPEATABLE READ: dòng hóa đơn có cầu nối + tuyến hiện hành, dòng phiếu của nội
        dung eligible, mã hóa/pool/token, bằng chứng approved, parent/child + token FILE. Không UUID nhập tay, không factor."""
        dt = self.danh_tinh(dang_nhap)
        if not [pn for pn in dt["quyen"] if quyen.duoc_l11(dt, "READ", pn)]:
            raise DataError("KHONG_CO_QUYEN_MODULE", "Liên kết số lượng cần quyền xem CẢ M2 và M5 trên cùng pháp nhân.")
        with self._tx_doc(dt):
            return self._l11_tong_quan_trong(dt)

    def _l11_tong_quan_trong(self, dt) -> dict:
        """Reader nội bộ — chạy TRONG snapshot RR của người gọi; quyền BOTH READ kiểm TRƯỚC mọi SELECT (lỗi quyền không làm hỏng giao dịch)."""
        pns = [pn for pn in dt["quyen"] if quyen.duoc_l11(dt, "READ", pn)]
        if not pns:
            raise DataError("KHONG_CO_QUYEN_MODULE", "Liên kết số lượng cần quyền xem CẢ M2 và M5 trên cùng pháp nhân.")
        hd = [dict(r) for r in self.conn.execute(
            """SELECT b.id AS cau_noi_id, p.ma AS phap_nhan, d.id AS hoa_don_id, d.mst_ban, d.ky_hieu, d.so_chuan, b.source_ordinal, b.quantity_raw,
                      b.unit_raw, b.field_states->'MHHDVu'->0->>'lexeme' AS ma_hang, r.dich, r.id AS tuyen_id,
                      (d.eligible_content_id = b.hoa_don_phien_ban_id) AS hien_hanh, kho.l11_co_so_ma_hoa('M2', b.id) AS ma_hoa
               FROM kho.hoa_don_dong_phien_ban b JOIN kho.hoa_don_danh_tinh d ON d.id = b.hoa_don_id JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
               LEFT JOIN kho.mua_dich_dong r ON r.source_dong_id = b.source_dong_id AND r.hien_hanh
               WHERE d.phap_nhan_id = ANY(%s::uuid[]) ORDER BY d.ky_hieu, d.so_chuan, b.source_ordinal""", (pns,))]
        pk = [dict(r) for r in self.conn.execute(
            """SELECT lw.id AS dong_phien_ban_id, p.ma AS phap_nhan, d.id AS phieu_id, d.so_phieu_key AS so_phieu, lw.stt, lw.source_ordinal, dd.id_dong_nguon,
                      lw.ma_hang_raw AS ma_hang, lw.so_luong_raw, lw.dvt_raw, lw.unit_definition_ref, (d.eligible_content_id = lw.phien_ban_id) AS hien_hanh,
                      kho.l11_co_so_ma_hoa('M5', lw.id) AS ma_hoa
               FROM kho.phieu_kho_dong_phien_ban lw JOIN kho.phieu_kho_danh_tinh d ON d.id = lw.phieu_id JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
               JOIN kho.phieu_kho_dong_danh_tinh dd ON dd.id = lw.dong_id
               WHERE d.phap_nhan_id = ANY(%s::uuid[]) ORDER BY d.so_phieu_key, lw.stt""", (pns,))]
        ma_hoa = [dict(r) for r in self.conn.execute(
            """SELECT e.id, e.owner_module, e.cau_noi_id, e.phieu_dong_phien_ban_id, e.pool_id, e.so_luong_nguon_text, e.don_vi_nguon_text, e.tu_so::text AS tu_so,
                      e.mau_so::text AS mau_so, kho.l11_text(e.suc_chua) AS suc_chua, e.can_cu, e.basis_revision, u.reference_id AS don_vi_pool,
                      (SELECT n.reference_id FROM master.dinh_nghia_don_vi_luong n WHERE n.id = e.don_vi_nguon_id) AS dinh_nghia_nguon,
                      e.do_luong_sha256, kho.luong_con_lai(e.pool_id) AS ngan_sach
               FROM kho.ma_hoa_luong_nguon e JOIN master.dinh_nghia_don_vi_luong u ON u.id = e.don_vi_pool_id
               WHERE e.phap_nhan_id = ANY(%s::uuid[]) ORDER BY e.tao_luc, e.id""", (pns,))]
        cha = [dict(r) for r in self.conn.execute(
            """SELECT k.id, p.ma AS phap_nhan, k.hoa_don_id, k.phieu_id, k.trang_thai, kho.l11_co_so_file(k.id) AS co_so
               FROM kho.lien_ket_chung_tu k JOIN master.phap_nhan p ON p.id = k.phap_nhan_id
               WHERE k.chu_so_huu_module = 'M5' AND k.phap_nhan_id = ANY(%s::uuid[]) ORDER BY k.tao_luc, k.id""", (pns,))]
        ds = self.conn.execute("SELECT kho.l11_danh_sach_bang_chung() AS v").fetchone()["v"]
        s = lambda v: None if v is None else str(v)  # noqa: E731
        return {
            "nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"],
                      "duoc": {k: any(quyen.duoc_l11(dt, k, pn) for pn in pns) for k in ("READ", "LINK", "CFO", "FILE")}},
            "dong_hoa_don": [{**r, "cau_noi_id": s(r["cau_noi_id"]), "hoa_don_id": s(r["hoa_don_id"]), "tuyen_id": s(r["tuyen_id"])} for r in hd],
            "dong_phieu": [{**r, "dong_phien_ban_id": s(r["dong_phien_ban_id"]), "phieu_id": s(r["phieu_id"])} for r in pk],
            "ma_hoa": [{**r, "id": s(r["id"]), "cau_noi_id": s(r["cau_noi_id"]), "phieu_dong_phien_ban_id": s(r["phieu_dong_phien_ban_id"]),
                        "pool_id": s(r["pool_id"])} for r in ma_hoa],
            "lien_ket": [{**r, "id": s(r["id"]), "hoa_don_id": s(r["hoa_don_id"]), "phieu_id": s(r["phieu_id"])} for r in cha],
            "bang_chung": ds.get("bang_chung") or []}

    def l11_xuat_file(self, dang_nhap, yeu_cau: dict) -> dict:
        """FILE chế độ L11_QUANTITY (server-derived, bất biến): BOTH READ + quyền file M5 hiện hành TRƯỚC tra cứu/replay; token toàn đồ thị số lượng;
        workbook text/formula-safe bốn lượng/đơn vị/mã hóa/bằng chứng/pool/held; m5-xuat/<sha>.xlsx; stage L11_FILE → consumer CSDL ghi lô/biên nhận."""
        dt = self.danh_tinh(dang_nhap)
        than = self._l11_than(yeu_cau, ("lien_ket_id", "co_so_truoc", "khoa", "ly_do"))
        if not isinstance(than.get("co_so_truoc"), str) or not _SHA.fullmatch(than["co_so_truoc"]):
            raise DataError("L11_YEU_CAU_SAI", "Cần token đồ thị số lượng đang xem (mở lại liên kết).")
        with self._tx_chu(dt) as c:
            k = c.execute("SELECT phap_nhan_id FROM kho.lien_ket_chung_tu WHERE id = %s AND chu_so_huu_module = 'M5'", (than.get("lien_ket_id"),)).fetchone()
            if not k or not quyen.duoc_l11(dt, "READ", k["phap_nhan_id"]):
                raise DataError("L11_FILE_KHONG_CO", "Không thấy liên kết số lượng (hoặc ngoài quyền).")
            quyen.kiem_l11(dt, "FILE", k["phap_nhan_id"])
            bd = c.execute("SELECT kho.l11_file_bat_dau(%s::jsonb) AS v", (json.dumps(than, ensure_ascii=False),)).fetchone()["v"]
            if bd["lap_lai"]:
                return {**bd["ket_qua"], "lap_lai": True}
            snap = bd["snapshot"]
            raw, so_dong = self._workbook_l11(snap)
            digest = sha256(raw)
            path = self.root / "m5-xuat" / f"{digest}.xlsx"
            write_immutable(path, raw)
            if sha256(path.read_bytes()) != digest:
                raise DataError("ARTIFACT_CHANGED", "File L11 sau khi ghi không khớp hash — giữ nguyên làm bằng chứng, không ghi lô.")
            ten = f"FILE-SOAT-L11-{str(than['lien_ket_id'])[:8]}-{digest[:8]}.xlsx"
            du_lieu = {"lien_ket_id": than["lien_ket_id"], "co_so_truoc": than["co_so_truoc"], "co_so_sha256": snap["co_so_sha256"], "ky": snap["ky"],
                       "artifact_sha256": digest, "byte_length": len(raw), "ten": ten, "so_dong": so_dong, "che_do": "L11_QUANTITY",
                       "snapshot_sha256": sha256(canonical_json(snap).encode("utf-8"))}
            stage = nguon_chung.ghi_stage(c, dt, muc_dich="L11_FILE", client_key=than["client_key"], h=bd["h"], source_instance=snap["source_instance_id"],
                                          profile_ref=snap["profile_ref"], profile_sha256=snap["profile_sha256"], du_lieu=du_lieu,
                                          phap_nhan_id=str(k["phap_nhan_id"]))
            return c.execute("SELECT kho.l11_file_tieu_thu(%s::uuid, %s) AS v", (stage, bd["h"])).fetchone()["v"]

    @staticmethod
    def _workbook_l11(snap: dict) -> tuple[bytes, int]:
        """Mọi ô là text exact (formula-safe), NULL để trống — bốn lượng native/pool, đơn vị, mã hóa, bằng chứng, pool, held, trạng thái child."""
        from ..xuat import excel
        t = lambda v: None if v is None else str(v)  # noqa: E731
        lk, hd, pk = snap.get("lien_ket") or {}, snap.get("hoa_don") or {}, snap.get("phieu") or {}
        dong_rows = []
        for c in snap.get("dong") or []:
            sl, dv = c.get("so_luong") or {}, c.get("don_vi") or {}
            dong_rows.append([t(c.get("child_id")), c.get("trang_thai"), c.get("hieu_luc"), ",".join(c.get("can_soat_ly_do") or []),
                              sl.get("hoa_don_nguon"), dv.get("hoa_don_nguon"), sl.get("phieu_nguon"), dv.get("phieu_nguon"),
                              sl.get("pool_hoa_don"), dv.get("pool_hoa_don"), sl.get("pool_phieu"), dv.get("pool_phieu"),
                              t(c.get("pool_hoa_don_id")), t(c.get("pool_phieu_id")), t(c.get("ma_hoa_hoa_don_id")), t(c.get("ma_hoa_phieu_id")),
                              ";".join(f"{b.get('kind')}:{b.get('ref')}@{b.get('rev')}={b.get('trang_thai')}" for b in c.get("bang_chung") or []),
                              t((c.get("tuyen") or {}).get("dich")), t(c.get("hoa_don_phien_ban_id")), t(c.get("phieu_phien_ban_id")),
                              c.get("tao_boi"), t(c.get("tao_luc")), c.get("huy_boi"), t(c.get("huy_luc")), c.get("huy_ly_do"),
                              dv.get("dinh_nghia_nguon_hoa_don"), dv.get("dinh_nghia_nguon_phieu")])
        pool_rows = [[t(n.get("pool_id")), n.get("owner_module"), n.get("don_vi"), n.get("suc_chua"), n.get("da_xac_nhan"), n.get("dang_giu"),
                      n.get("da_dung"), n.get("con_lai"), ",".join(n.get("ly_do_chan") or [])] for n in snap.get("ngan_sach") or [] if n]
        wb = excel.workbook()
        excel.table(wb, "LIEN_KET", ["lien_ket", "phap_nhan", "hoa_don", "dinh_danh_hoa_don", "eligible_hoa_don", "phieu", "so_phieu", "eligible_phieu",
                                     "trang_thai_parent", "co_so_sha256"],
                    [[t(lk.get("id")), snap.get("phap_nhan"), t(hd.get("id")), "|".join(str(x) for x in hd.get("dinh_danh") or []), t(hd.get("eligible")),
                      t(pk.get("id")), pk.get("so_phieu"), t(pk.get("eligible")), lk.get("trang_thai"), snap.get("co_so_sha256")]])
        excel.table(wb, "DONG_SO_LUONG", ["child", "trang_thai", "hieu_luc", "ly_do_can_soat", "so_luong_hoa_don_native", "don_vi_hoa_don_native",
                                          "so_luong_phieu_native", "don_vi_phieu_native", "so_luong_pool_hoa_don", "don_vi_pool_hoa_don", "so_luong_pool_phieu",
                                          "don_vi_pool_phieu", "pool_hoa_don", "pool_phieu", "ma_hoa_hoa_don", "ma_hoa_phieu", "bang_chung", "tuyen",
                                          "phien_ban_hoa_don", "phien_ban_phieu", "tao_boi", "tao_luc", "huy_boi", "huy_luc", "huy_ly_do",
                                          "dinh_nghia_don_vi_native_hoa_don", "dinh_nghia_don_vi_native_phieu"], dong_rows)
        excel.table(wb, "NGAN_SACH_POOL", ["pool", "phia", "don_vi", "suc_chua_hien_hanh", "da_xac_nhan", "dang_giu", "da_dung", "con_lai", "ly_do_chan"],
                    pool_rows)
        excel.table(wb, "CANH_BAO", ["noi_dung"], [["DEMO — dữ liệu mô phỏng; chỉ số lượng: KHÔNG tiền/giá vốn/331/BANK/bút toán/tồn kho"],
                                                   ["Lượng giữ nguyên dạng chuỗi chính xác; trống = NULL (không phải 0); CAN_SOAT = giữ lượng, chờ người xử lý"],
                                                   ["File chế độ L11_QUANTITY cần quyền xem CẢ M2 và M5 cùng quyền file soát M5 khi tải lại"]])
        return excel.to_bytes(wb), len(dong_rows)

    # tương thích tên cũ (route lien-ket/*) — nay là liên kết số lượng thật qua lien_ket(dang_nhap, hanh_dong, yeu_cau)
