"""M4-01 — service typed K2 cho Cổng hồ sơ xây dựng (phòng dự án): hợp đồng/tệp nguồn/trích/tham số/xác nhận/phụ lục/BOQ/đợt/preflight/nộp.

- Authority: K2 PostgreSQL schema `m4` + master.hop_dong (module_chu 'M4'), migration 17 (`m4/sql_m17.py`). CSDL kiểm lại danh tính phiên
  (ID + login), phạm vi dự án HIỆN HÀNH (master.m4_duoc, thu hồi chỉ ghi thêm), revision mong đợi, biên nhận và gate nộp (m4.thieu).
- M4-01B: hai kết nối, inject qua factory máy chủ (giao_dien/m4.py), không nhận DSN/đường dẫn/khóa từ request:
  * `conn` — login ứng dụng (app_web): đọc qua RLS và các lệnh người dùng thường.
  * `conn_tin_cay` — kết nối CHỦ BẢNG của máy chủ (cùng đường ghi nguồn M5/M2): chỉ dùng cho bước máy chủ đã xác minh bytes/kết quả xử lý thật
    (ghi tệp đã nhận, kết quả trích, kết quả đọc BOQ, sửa tham số kèm kết quả máy kiểm trích dẫn). Thiếu → M4_CHUA_SAN_SANG_GHI_NGUON, không fallback.
- Biên nhận (B2): tra biên nhận của chính phiên TRƯỚC kiểm revision/đọc tệp/parse/AI; cùng khóa + cùng yêu cầu gốc → kết quả cũ; khác → từ chối;
  kết quả FINAL do chính lệnh CSDL chốt trong cùng giao dịch (không có hàm cho caller tự chốt JSON).
- Danh tính do máy chủ giữ theo phiên; service không nhận actor/PN/cờ "đã trích/đã xác nhận/đã duyệt" từ trình duyệt.
- Lõi nguồn (trích/BOQ/hiệu lực/checklist) qua adapter `m4/nguon_review.py`; bytes tệp lưu bất biến `m4-raw/<sha256>` trong DataRoot riêng.
- Phòng dự án tự soát/xác nhận tham số M4 (không CFO); không ghi master.hop_dong_phien_ban/hop_dong_tham_so (authority CRM giữ nguyên).
- Chưa có ở gói này: review L1–L3, duyệt, PDF đợt, kế toán, Request (gói M4-02…04) — trả trạng thái CHUA_NOI, không tạo kết quả giả.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, date_iso, sha256
from ..ha_tang.store import write_immutable
from ..m4 import duyet_dot as DD
from ..m4 import nguon_review as NR
from . import quyen

MODULE = "M4"
KHOA_RE = re.compile(r"[A-Za-z0-9_.:-]{1,200}")
TRANG_THAI_SUA = ("CO_GIA_TRI", "KHONG_AP_DUNG", "KHONG_QUY_DINH")
KHAI_PHU_LUC = ("KHONG_CO", "CO_CHUA_DU", "CO_DU")
NHANH_SAU = (  # trạng thái thật của các nhánh sau nộp — chưa nối ở gói M4-01
    {"ma": "REVIEW", "ten": "Review L1–L3 & duyệt hồ sơ đợt", "trang_thai": "CHUA_NOI", "goi": "M4-02"},
    {"ma": "PDF", "ten": "PDF hồ sơ đợt được duyệt", "trang_thai": "CHUA_NOI", "goi": "M4-02"},
    {"ma": "KE_TOAN", "ten": "Kế toán xác nhận nghiệm thu/công nợ", "trang_thai": "CHUA_NOI", "goi": "M4-03"},
    {"ma": "REQUEST", "ten": "Tạo nháp Request thanh toán", "trang_thai": "CHUA_NOI", "goi": "M4-04"},
)


def _hom_nay_vn() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


def _v(x):
    if isinstance(x, uuid.UUID):
        return str(x)
    if isinstance(x, (date, datetime)):
        return x.isoformat()
    if isinstance(x, Decimal):
        return format(x, "f")
    if isinstance(x, dict):
        return {k: _v(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_v(v) for v in x]
    return x


def _uuid(v, ten: str) -> str:
    try:
        return str(uuid.UUID(str(v))) if isinstance(v, str) else _sai(ten)
    except ValueError:
        return _sai(ten)


def _sai(ten: str):
    raise DataError("M4_THAM_SO_SAI", f"Trường {ten} không hợp lệ.")


def _so_nguyen(v, ten: str, nho=0, lon=10 ** 9) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not nho <= v <= lon:
        _sai(ten)
    return v


def _chuoi(v, ten: str, toi_da: int, *, bat_buoc=True):
    if v is None or v == "":
        if bat_buoc:
            raise DataError("M4_THIEU_THONG_TIN", f"Thiếu {ten}.")
        return None
    if not isinstance(v, str) or len(v) > toi_da or any(ord(c) < 32 and c not in "\n\t" for c in v):
        _sai(ten)
    return v


def _ngay(v, ten: str, *, bat_buoc=False):
    if v in (None, ""):
        if bat_buoc:
            raise DataError("M4_THIEU_THONG_TIN", f"Thiếu {ten}.")
        return None
    return date_iso(v)


class XayDungK2:
    def __init__(self, conn, thu_muc: Path, *, conn_tin_cay=None, chi_mo_phong: bool = True, hom_nay=None, ai=None, che_do_ai: str | None = None,
                 trich6=None):
        """conn: psycopg autocommit=True, row_factory=dict_row, login ứng dụng (thành viên app_web, không superuser/BYPASSRLS).
        conn_tin_cay: kết nối chủ bảng của máy chủ (autocommit, dict_row) do factory đã kiểm (cùng đích/chủ bảng); None → đường ghi nguồn chưa sẵn sàng.
        ai/che_do_ai: CHỈ dùng trong kiểm thử với AI giả lập đã khai báo (AI_GIA_LAP_KHAI_BAO); bản chạy để None (chưa có Local AI ở gói này)."""
        from psycopg.types.string import StrDumperUnknown
        self.conn, self.root, self.chi_mo_phong = conn, Path(thu_muc), chi_mo_phong
        self.conn_tin_cay = conn_tin_cay
        self.hom_nay = hom_nay or _hom_nay_vn
        self.ai, self.che_do_ai = ai, che_do_ai
        self.trich6 = trich6  # CRM-41-01: client engine trích DÙNG CHUNG #6 (nguon/trich_chung_6.Trich6Client) do máy chủ tiêm; None → chưa sẵn sàng
        conn.adapters.register_dumper(str, StrDumperUnknown)
        if conn_tin_cay is not None:
            conn_tin_cay.adapters.register_dumper(str, StrDumperUnknown)

    # ------------------------------------------------------------------ hạ tầng
    def danh_tinh(self, dang_nhap: str) -> dict:
        return quyen.nap_danh_tinh(self.conn, dang_nhap, chi_mo_phong=self.chi_mo_phong)

    @contextmanager
    def _tx(self, dt):
        with self.conn.transaction():
            self.conn.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                              "set_config('ktt.ngay_hieu_luc', %s, true)", (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat()))
            yield

    def _mot(self, sql, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return None if row is None else _v(dict(row))

    def _nhieu(self, sql, params=()):
        return [_v(dict(r)) for r in self.conn.execute(sql, params)]

    @staticmethod
    def _khoa(khoa) -> str:
        if not isinstance(khoa, str) or not KHOA_RE.fullmatch(khoa):
            raise DataError("M4_KHOA_THAO_TAC", "Thiếu hoặc sai khóa thao tác (chống bấm lặp).")
        return khoa

    @contextmanager
    def _tx_tin_cay(self, dt):
        """Giao dịch trên kết nối chủ bảng với danh tính phiên của nhân viên (CSDL vẫn kiểm phạm vi hiện hành của chính nhân viên đó)."""
        c = self.conn_tin_cay
        if c is None:
            raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Đường ghi nguồn tin cậy của máy chủ chưa được cấu hình — chưa nhận tệp/kết quả xử lý "
                                                          "(không ghi bằng quyền người dùng thường).")
        with c.transaction():
            c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                      "set_config('ktt.ngay_hieu_luc', %s, true)", (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat()))
            yield c

    def _tra_lai(self, dt, hanh_dong: str, khoa, yc: dict) -> dict | None:
        """B2: tra biên nhận của phiên TRƯỚC mọi kiểm revision/đọc tệp/parse/AI. Quyền dự án hiện hành kiểm trong CSDL (thu hồi → chặn).
        Cùng hành động + yêu cầu gốc → kết quả cũ (lap_lai); khác → M4_IDEMPOTENCY_KHAC; chưa có → None (làm mới)."""
        khoa = self._khoa(khoa)
        with self._tx(dt):
            r = self._mot("SELECT m4.tra_bien_nhan(%s) AS r", (khoa,))["r"]
        if r is None:
            return None
        if r["hanh_dong"] != hanh_dong or r["yeu_cau"] != json.loads(json.dumps(yc, ensure_ascii=False)):
            raise DataError("M4_IDEMPOTENCY_KHAC", "Khóa thao tác đã dùng cho yêu cầu khác.")
        return {**r["ket_qua"], "lap_lai": True}

    def _goi(self, dt, sql: str, params, *, tin_cay: bool = False) -> dict:
        """Gọi lệnh CSDL trả {lap_lai, ket_qua}; CSDL tra lại biên nhận dưới khóa (đồng thời cùng khóa → một kết quả, không thêm hàng nghiệp vụ)."""
        if tin_cay:
            with self._tx_tin_cay(dt) as c:
                row = c.execute(sql, params).fetchone()
        else:
            with self._tx(dt):
                row = self.conn.execute(sql, params).fetchone()
        r = _v(dict(row))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    def _ho_so(self, dt, hd: str, *, soan=True) -> dict:
        with self._tx(dt):
            h = self._mot("""SELECT h.hop_dong_id, h.du_an_id, h.revision, h.rev_tham_so, h.tep_hop_dong_id, t.raw_sha256, t.media_type,
                                    master.m4_duoc(h.du_an_id, 'SOAN') AS soan
                             FROM m4.ho_so_hop_dong h LEFT JOIN m4.tep t ON t.id = h.tep_hop_dong_id WHERE h.hop_dong_id = %s::uuid""", (hd,))
        if h is None:
            raise DataError("M4_KHONG_THAY_HOP_DONG", "Không thấy hồ sơ hợp đồng (hoặc ngoài phạm vi dự án).")
        if soan and not h["soan"]:
            raise DataError("M4_KHONG_CO_QUYEN_DU_AN", "Cần quyền soạn hồ sơ (phòng dự án phụ trách) đúng dự án.")
        return h

    @staticmethod
    def _kiem_rev(h, rev, ten="revision"):
        _so_nguyen(rev, ten, 1)
        if h["revision"] != rev:
            raise DataError("M4_REVISION_CU", f"Hồ sơ đã đổi (revision hiện tại {h['revision']}) — tải lại rồi thao tác.")

    def _raw(self, sha: str, dai: int | None = None) -> bytes:
        p = self.root / "m4-raw" / sha
        if not re.fullmatch(r"[0-9a-f]{64}", sha or "") or not p.is_file():
            raise DataError("M4_TEP_KHONG_CO_TRONG_KHO", "Bytes tệp không có trong kho lưu trữ M4.")
        raw = p.read_bytes()
        if sha256(raw) != sha or (dai is not None and len(raw) != dai):
            raise DataError("M4_TEP_HONG_LUU_TRU", "Tệp trong kho khác hash đã ghi — không dùng.")
        return raw

    def _tep(self, dt, tep_id: str) -> dict:
        with self._tx(dt):
            t = self._mot("""SELECT t.*, master.m4_duoc(t.du_an_id, 'SOAN') AS soan FROM m4.tep t WHERE t.id = %s::uuid""", (tep_id,))
        if t is None:
            raise DataError("M4_KHONG_THAY_TEP", "Không thấy tệp (hoặc ngoài phạm vi).")
        return t

    # ------------------------------------------------------------------ đọc
    def tong_quan(self, dang_nhap: str) -> dict:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            pham_vi = self._nhieu("""SELECT q.du_an_id, q.vai, d.ten AS du_an, d.ma_junsky AS du_an_ma, p.ma AS phap_nhan,
                                            master.m4_duoc(q.du_an_id, 'SOAN') AS soan,
                                            (master.m4_duoc(q.du_an_id, 'XEM') OR master.m4_duoc(q.du_an_id, 'REVIEW')) AS xem
                                     FROM m4.quyen_du_an q JOIN master.du_an d ON d.id = q.du_an_id JOIN master.phap_nhan p ON p.id = q.phap_nhan_id
                                     ORDER BY p.ma, d.ma_junsky, q.vai""")
            hop_dong = self._nhieu("""SELECT h.hop_dong_id AS id, h.ten, hd.so_hop_dong, h.du_an_id, d.ten AS du_an, p.ma AS phap_nhan, h.revision,
                                             h.trang_thai_pl, h.tep_hop_dong_id IS NOT NULL AS co_tep, master.m4_duoc(h.du_an_id, 'SOAN') AS soan,
                                             (SELECT count(*) FROM m4.dot x WHERE x.hop_dong_id = h.hop_dong_id) AS so_dot
                                      FROM m4.ho_so_hop_dong h JOIN master.hop_dong hd ON hd.id = h.hop_dong_id
                                      JOIN master.du_an d ON d.id = h.du_an_id JOIN master.phap_nhan p ON p.id = h.phap_nhan_id
                                      ORDER BY p.ma, d.ma_junsky, hd.so_hop_dong""")
            dot = self._nhieu("""SELECT d.id, d.hop_dong_id, hd.so_hop_dong, d.so_dot, d.ngay_nghiem_thu, d.trang_thai, d.revision, n.nop_luc
                                 FROM m4.dot d JOIN master.hop_dong hd ON hd.id = d.hop_dong_id LEFT JOIN m4.nop n ON n.dot_id = d.id
                                 ORDER BY hd.so_hop_dong, d.so_dot""")
            danh_muc = self._nhieu("SELECT ma, ten, bat_buoc_dot_dau, bat_buoc_dot_sau, ghi_chu FROM m4.danh_muc_ho_so_dot ORDER BY ma")
        return {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"]}, "pham_vi": [p for p in pham_vi if p["xem"]],
                "hop_dong": hop_dong, "dot": dot, "danh_muc_ho_so": danh_muc, "nhanh_sau": list(NHANH_SAU),
                "tai_len_toi_da_byte": NR.TEP_TOI_DA}

    def chi_tiet(self, dang_nhap: str, hop_dong_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        with self._tx(dt):
            h = self._mot("""SELECT h.*, hd.so_hop_dong, d.ten AS du_an, p.ma AS phap_nhan, master.m4_duoc(h.du_an_id, 'SOAN') AS soan
                             FROM m4.ho_so_hop_dong h JOIN master.hop_dong hd ON hd.id = h.hop_dong_id JOIN master.du_an d ON d.id = h.du_an_id
                             JOIN master.phap_nhan p ON p.id = h.phap_nhan_id WHERE h.hop_dong_id = %s::uuid""", (hd,))
            if h is None:
                raise DataError("M4_KHONG_THAY_HOP_DONG", "Không thấy hồ sơ hợp đồng (hoặc ngoài phạm vi dự án).")
            tep = self._nhieu("""SELECT id, vai_tro_tai_lieu, ten_goc, media_type, byte_length, raw_sha256, tao_boi, tao_luc FROM m4.tep
                                 WHERE du_an_id = %s::uuid AND vai_tro_tai_lieu <> 'HO_SO_DOT' ORDER BY tao_luc, id""", (h["du_an_id"],))
            trich = self._nhieu("""SELECT id, lan, tep_id, raw_sha256, che_do, trang_thai, ly_do, engine, phieu->'tom_tat' AS tom_tat, tao_boi, tao_luc
                                   FROM m4.trich_xuat WHERE hop_dong_id = %s::uuid ORDER BY lan DESC""", (hd,))
            tham_so = self._nhieu("""SELECT c.ma, c.nhom, c.ten, s.trang_thai, s.gia_tri, s.don_vi, s.dieu_khoan, s.trich_dan, s.kiem_tra, s.ly_do, s.vi_tri,
                                            s.nguon, s.gia_tri_may, s.trich_xuat_id, s.cap_nhat_boi, s.cap_nhat_luc
                                     FROM m4.danh_muc_tham_so c LEFT JOIN m4.tham_so s ON s.ma = c.ma AND s.hop_dong_id = %s::uuid ORDER BY c.thu_tu""", (hd,))
            xn = self._mot("""SELECT x.*, m4.digest_tham_so(x.hop_dong_id) AS digest_hien_tai FROM m4.xac_nhan_tham_so x
                              WHERE x.hop_dong_id = %s::uuid ORDER BY x.rev_tham_so DESC LIMIT 1""", (hd,))
            phu_luc = self._nhieu("""SELECT id, so_pl, ngay_ky, ngay_hieu_luc, trang_thai, doi_boq, noi_dung, tep_id, huy_ly_do, tao_boi, tao_luc
                                     FROM m4.phu_luc WHERE hop_dong_id = %s::uuid ORDER BY ngay_hieu_luc, so_pl, tao_luc""", (hd,))
            boq = self._nhieu("""SELECT b.id, b.lan, b.phu_luc_id, b.tep_id, b.raw_sha256, b.sheet, b.hang_tieu_de, b.cot, b.so_dong, b.loi_chan, b.phat_hien,
                                        b.trang_thai, b.tao_boi, b.tao_luc
                                 FROM m4.boq b WHERE b.hop_dong_id = %s::uuid ORDER BY b.lan DESC""", (hd,))
            boq_goc = next((b for b in boq if b["phu_luc_id"] is None), None)
            dong = self._nhieu("""SELECT dong, ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien, ma_rieng, o_goc FROM m4.boq_dong
                                  WHERE boq_id = %s::uuid ORDER BY dong LIMIT 2000""", (boq_goc["id"],)) if boq_goc else []
            dot = self._nhieu("""SELECT d.id, d.so_dot, d.ngay_nghiem_thu, d.trang_thai, d.revision, n.nop_luc, n.revision_ho_so
                                 FROM m4.dot d LEFT JOIN m4.nop n ON n.dot_id = d.id WHERE d.hop_dong_id = %s::uuid ORDER BY d.so_dot""", (hd,))
            # MASTER-REUSE-02: căn cứ master/đối tác của hồ sơ; gói SQL chưa áp dụng → None (không tạo căn cứ giả)
            co_mc = self._mot("SELECT to_regprocedure('m4.master_can_cu_doc(uuid)') IS NOT NULL AS co")["co"]
            master_can_cu = self._mot("SELECT m4.master_can_cu_doc(%s::uuid) AS r", (hd,))["r"] if co_mc else None
        moi_nhat = trich[0] if trich else None
        xac_nhan = None
        if xn:
            hieu_luc = (moi_nhat is not None and xn["rev_tham_so"] == h["rev_tham_so"] and xn["trich_xuat_id"] == moi_nhat["id"]
                        and xn["tham_so_digest"] == xn["digest_hien_tai"])
            xac_nhan = {k: xn[k] for k in ("id", "rev_tham_so", "tep_id", "raw_sha256", "trich_xuat_id", "catalog_sha256", "xac_nhan_boi", "xac_nhan_luc", "ly_do")}
            xac_nhan["con_hieu_luc"] = hieu_luc
        for d in dot:
            d["can_cu_doi_sau_nop"] = d["revision_ho_so"] is not None and d["revision_ho_so"] != h["revision"]
        return {"ho_so": h, "tep": tep, "trich_xuat": trich, "tham_so": tham_so, "xac_nhan": xac_nhan, "phu_luc": phu_luc, "boq": boq,
                "boq_goc_dong": dong, "dot": dot, "danh_muc_sha256": NR.PIN[NR.CATALOG], "nhanh_sau": list(NHANH_SAU), "master_can_cu": master_can_cu}

    def chi_tiet_dot(self, dang_nhap: str, dot_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        di = _uuid(dot_id, "dot_id")
        with self._tx(dt):
            d = self._mot("""SELECT d.*, h.revision AS revision_ho_so, hd.so_hop_dong, master.m4_duoc(d.du_an_id, 'SOAN') AS soan
                             FROM m4.dot d JOIN m4.ho_so_hop_dong h ON h.hop_dong_id = d.hop_dong_id JOIN master.hop_dong hd ON hd.id = d.hop_dong_id
                             WHERE d.id = %s::uuid""", (di,))
            if d is None:
                raise DataError("M4_KHONG_THAY_DOT", "Không thấy đợt (hoặc ngoài phạm vi).")
            tep = self._nhieu("""SELECT k.muc, k.tep_id, t.ten_goc, t.media_type, t.byte_length, t.raw_sha256, k.tao_boi, k.tao_luc
                                 FROM m4.dot_tep k JOIN m4.tep t ON t.id = k.tep_id WHERE k.dot_id = %s::uuid ORDER BY k.muc, k.tao_luc""", (di,))
            thieu = self._mot("SELECT m4.thieu(%s::uuid) AS t", (di,))["t"]
            nop = self._mot("SELECT id, revision_ho_so, revision_dot, digest, nop_boi, nop_luc, snapshot FROM m4.nop WHERE dot_id = %s::uuid", (di,))
            danh_muc = self._nhieu("SELECT ma, ten, bat_buoc_dot_dau, bat_buoc_dot_sau, ghi_chu FROM m4.danh_muc_ho_so_dot ORDER BY ma")
            pls = self._nhieu("""SELECT id, so_pl, ngay_ky, ngay_hieu_luc, trang_thai, doi_boq FROM m4.phu_luc WHERE hop_dong_id = %s::uuid
                                 AND trang_thai <> 'DA_HUY'""", (d["hop_dong_id"],))
            boqs = self._nhieu("""SELECT b.id, b.phu_luc_id FROM m4.boq b WHERE b.hop_dong_id = %s::uuid AND b.trang_thai = 'DA_MAP'
                                  AND b.lan = (SELECT max(z.lan) FROM m4.boq z WHERE z.hop_dong_id = b.hop_dong_id AND z.phu_luc_id IS NOT DISTINCT FROM b.phu_luc_id)""",
                               (d["hop_dong_id"],))
            dong = {b["id"]: self._nhieu("""SELECT ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien FROM m4.boq_dong WHERE boq_id = %s::uuid
                                            ORDER BY dong""", (b["id"],)) for b in boqs}
        co = {}
        for t in tep:
            co.setdefault(t["muc"], []).append(t)
        checklist = [{**c, "bat_buoc": c["bat_buoc_dot_dau"] if d["so_dot"] == 1 else c["bat_buoc_dot_sau"], "tep": co.get(c["ma"], [])} for c in danh_muc]
        try:
            hl = NR.hieu_luc(pls, next((dong[b["id"]] for b in boqs if b["phu_luc_id"] is None), []),
                             {b["phu_luc_id"]: dong[b["id"]] for b in boqs if b["phu_luc_id"] is not None}, d["ngay_nghiem_thu"])
        except DataError as exc:
            hl = {"loi": exc.code, "thong_bao": str(exc)}
        return {"dot": d, "tep": tep, "checklist": checklist, "thieu": thieu, "du_can_cu": not thieu, "nop": nop, "hieu_luc": hl,
                "can_cu_doi_sau_nop": bool(nop) and nop["revision_ho_so"] != d["revision_ho_so"], "nhanh_sau": list(NHANH_SAU)}

    def tai_ve(self, dang_nhap: str, tep_id) -> tuple[str, str, bytes]:
        """Tải bytes gốc: quyền đọc theo RLS phạm vi dự án (người review chỉ tệp đợt đã nộp) kiểm TRƯỚC khi đọc kho."""
        dt = self.danh_tinh(dang_nhap)
        t = self._tep(dt, _uuid(tep_id, "tep_id"))
        return t["ten_goc"], t["media_type"], self._raw(t["raw_sha256"], t["byte_length"])

    # ------------------------------------------------------------------ hợp đồng & tệp
    def tao_hop_dong(self, dang_nhap: str, *, du_an_id, so_hop_dong, ten, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        du_an = _uuid(du_an_id, "du_an_id")
        so = _chuoi(so_hop_dong, "số hợp đồng", 100)
        ten = _chuoi(ten, "tên hợp đồng/gói thầu", 300)
        yc = {"du_an_id": du_an, "so_hop_dong": so, "ten": ten}
        cu = self._tra_lai(dt, "TAO_HOP_DONG", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.tao_hop_dong(%s, %s::uuid, %s, %s) AS r", (khoa, du_an, so, ten))

    # ------------------------------------------------------------------ master dùng chung (GIAO-CODE-M4-MASTER-REUSE-02, SQL m4/sql_master_dung_chung.py)
    # Chỉ kiểm hình dạng DTO; quyền SOAN/XEM hiện hành, PN/dự án/loại/trạng thái, CAS, khóa và biên nhận do hàm CSDL quyết định.
    @staticmethod
    def _tim(q, limit) -> tuple[str, int]:
        q = "" if q is None else q
        if not isinstance(q, str) or len(q) > 100 or any(ord(c) < 32 for c in q):
            _sai("q")
        if limit is None:
            limit = 25
        elif isinstance(limit, str):  # tham số truy vấn GET
            if not re.fullmatch(r"[0-9]{1,2}", limit):
                _sai("limit")
            limit = int(limit)
        return q, _so_nguyen(limit, "limit", 1, 50)

    @staticmethod
    def _sha(v, ten: str) -> str:
        if not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v):
            _sai(ten)
        return v

    def master_hop_dong(self, dang_nhap: str, *, du_an_id, q="", limit=25) -> dict:
        dt = self.danh_tinh(dang_nhap)
        du_an = _uuid(du_an_id, "du_an_id")
        q, limit = self._tim(q, limit)
        with self._tx(dt):
            return self._mot("SELECT m4.master_hop_dong_ds(%s::uuid, %s, %s) AS r", (du_an, q, limit))["r"]

    def master_doi_tac(self, dang_nhap: str, *, du_an_id, q="", limit=25) -> dict:
        dt = self.danh_tinh(dang_nhap)
        du_an = _uuid(du_an_id, "du_an_id")
        q, limit = self._tim(q, limit)
        with self._tx(dt):
            return self._mot("SELECT m4.master_doi_tac_ds(%s::uuid, %s, %s) AS r", (du_an, q, limit))["r"]

    def nhan_master_hop_dong(self, dang_nhap: str, *, du_an_id, hop_dong_id, ten, expected_master, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        du_an = _uuid(du_an_id, "du_an_id")
        hd = _uuid(hop_dong_id, "hop_dong_id")
        ten = _chuoi(ten, "tên hồ sơ hợp đồng/gói thầu", 300)
        exp = self._sha(expected_master, "expected_master")
        yc = {"du_an_id": du_an, "hop_dong_id": hd, "ten": ten, "expected_master": exp}
        cu = self._tra_lai(dt, "NHAN_MASTER_HOP_DONG", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.nhan_master_hop_dong(%s, %s::uuid, %s::uuid, %s, %s) AS r", (khoa, du_an, hd, ten, exp))

    def gan_doi_tac_hop_dong(self, dang_nhap: str, *, hop_dong_id, doi_tac_id, mapping_id, revision, expected_master, expected_mapping, ly_do,
                             khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        doi_tac = _uuid(doi_tac_id, "doi_tac_id")
        mapping = _uuid(mapping_id, "mapping_id")
        rev = _so_nguyen(revision, "revision", 1)
        exp = self._sha(expected_master, "expected_master")
        exp_map = self._sha(expected_mapping, "expected_mapping")
        ly_do = _chuoi(ly_do, "lý do gắn/sửa đối tác", 1000)
        if not ly_do.strip():
            raise DataError("M4_LY_DO_BAT_BUOC", "Cần lý do gắn/sửa đối tác.")
        yc = {"hop_dong_id": hd, "doi_tac_id": doi_tac, "mapping_id": mapping, "revision": rev, "expected_master": exp,
              "expected_mapping": exp_map, "ly_do": ly_do}
        cu = self._tra_lai(dt, "GAN_DOI_TAC_HOP_DONG", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.gan_doi_tac_hop_dong(%s, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s) AS r",
                         (khoa, hd, doi_tac, mapping, rev, exp, exp_map, ly_do))

    def tai_tep(self, dang_nhap: str, raw: bytes, *, du_an_id, vai_tro, ten, media_type, khoa) -> dict:
        """Nhận tệp: máy chủ kiểm bytes thật (rỗng/kích thước/tên/đuôi↔media↔chữ ký/OOXML), tính SHA; replay tra trước; quyền hiện hành kiểm trước
        khi ghi bytes; bytes ghi bất biến `m4-raw/<sha>` rồi mới ghi hàng qua đường tin cậy (caller thường không khai được hash/metadata)."""
        dt = self.danh_tinh(dang_nhap)
        du_an = _uuid(du_an_id, "du_an_id")
        self._khoa(khoa)
        meta = NR.kiem_tep(raw, ten, media_type, vai_tro)
        yc = {"du_an_id": du_an, "vai_tro": vai_tro, "ten": meta["ten"], "media_type": meta["media"], "sha256": meta["sha256"],
              "byte_length": meta["byte_length"]}
        kq = self._tra_lai(dt, "TAI_TEP", khoa, yc)
        if kq is None:
            if self.conn_tin_cay is None:
                raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Đường ghi nguồn tin cậy của máy chủ chưa được cấu hình — chưa nhận tệp.")
            with self._tx(dt):  # quyền kiểm TRƯỚC khi ghi bytes
                if not self._mot("SELECT master.m4_duoc(%s::uuid, 'SOAN') AS ok", (du_an,))["ok"]:
                    raise DataError("M4_KHONG_CO_QUYEN_DU_AN", "Cần quyền soạn hồ sơ (phòng dự án phụ trách) đúng dự án.")
            write_immutable(self.root / "m4-raw" / meta["sha256"], bytes(raw))
            kq = self._goi(dt, "SELECT m4.ghi_tep(%s, %s::uuid, %s, %s, %s::bigint, %s, %s) AS r",
                           (khoa, du_an, vai_tro, meta["sha256"], meta["byte_length"], meta["media"], meta["ten"]), tin_cay=True)
        if vai_tro == "HO_SO_DOT":
            try:
                kq["goi_y_muc"] = NR.goi_y_muc(meta["ten"])
            except DataError:
                kq["goi_y_muc"] = []
        return kq

    def gan_tep_hop_dong(self, dang_nhap: str, *, hop_dong_id, revision, tep_id, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd, tep = _uuid(hop_dong_id, "hop_dong_id"), _uuid(tep_id, "tep_id")
        _so_nguyen(revision, "revision", 1)
        yc = {"hop_dong_id": hd, "revision": revision, "tep_id": tep}
        cu = self._tra_lai(dt, "GAN_TEP_HOP_DONG", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.gan_tep_hop_dong(%s, %s::uuid, %s::integer, %s::uuid) AS r", (khoa, hd, revision, tep))

    def trich(self, dang_nhap: str, *, hop_dong_id, revision, khoa) -> dict:
        """Chạy lõi trích nguồn trên bytes thật của tệp HĐ hiện hành (máy chủ), rồi ghi kết quả qua đường tin cậy có revision mong đợi.
        Replay tra TRƯỚC (không chạy lại parse/AI, không tạo thư mục làm việc). Tệp không hỗ trợ/lỗi → lần trích KHONG_HO_TRO/LOI có lý do.
        Artifact mỗi lần chạy giữ ở m4-trich/<HĐ>/<lần>, không xóa."""
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        _so_nguyen(revision, "revision", 1)
        yc = {"hop_dong_id": hd, "revision": revision}
        cu = self._tra_lai(dt, "TRICH", khoa, yc)
        if cu is not None:
            return cu
        if self.conn_tin_cay is None:
            raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Đường ghi nguồn tin cậy của máy chủ chưa được cấu hình — chưa chạy trích.")
        h = self._ho_so(dt, hd)
        self._kiem_rev(h, revision)
        if h["tep_hop_dong_id"] is None:
            raise DataError("M4_THIEU_HOP_DONG", "Chưa có tệp hợp đồng nguồn — tải và gắn tệp hợp đồng trước.")
        raw = self._raw(h["raw_sha256"])
        # CRM-41-01: SOAN + revision đã kiểm ở _ho_so/_kiem_rev TRƯỚC khi gửi bytes; engine #6 dùng chung (ngoài giao dịch K2/khóa toàn cục);
        # ý định ổn định theo (actor, khóa, HĐ, revision, raw) → thử lại cùng khóa đối soát đúng lượt/kết quả; ghi qua SQL CAS revision hiện hành.
        if self.trich6 is None:
            raise DataError("M4_TRICH6_CHUA_SAN_SANG", "Engine trích dùng chung #6 chưa được máy chủ cấu hình — chưa trích (không dùng lõi chép).")
        yc_id = "m4:" + sha256(canonical_json([dt["id"], khoa, hd, revision, h["raw_sha256"]]).encode("utf-8"))[:48]
        # CRM-41-01-06: kiểm sẵn sàng THEO GIAI ĐOẠN, chỉ đọc, TRƯỚC NR (NR biến lỗi rõ thành lần trích LOI có ghi revision): ý định mới mà engine
        # chưa cấu hình → lỗi rõ; ý định đã giữ (có thể đã có hiệu lực) → UNKNOWN. Cả hai: zero POST, zero ghi K2, không FINAL LOI.
        kiem = getattr(self.trich6, "kiem_giai_doan", None)
        if kiem is None:
            if not getattr(self.trich6, "san_sang", False):
                raise DataError("M4_TRICH6_CHUA_SAN_SANG", "Engine trích dùng chung #6 chưa được máy chủ cấu hình — chưa trích (không dùng lõi chép).")
        else:
            try:
                kiem(yc_id)
            except DataError as exc:
                if exc.code == "TRICH6_CHUA_RO":
                    raise DataError("M4_TRICH6_CHUA_RO", str(exc)) from None
                if exc.code == "TRICH6_CHUA_SAN_SANG":
                    raise DataError("M4_TRICH6_CHUA_SAN_SANG", "Engine trích dùng chung #6 chưa được máy chủ cấu hình — chưa trích (không dùng lõi chép).") from None
                raise
        try:
            kq = NR.trich_hop_dong(raw, h["media_type"], self.root / "m4-trich" / hd / yc_id.replace(":", "_"), client=self.trich6, request_id=yc_id)
        except DataError as exc:
            if exc.code in ("TRICH6_CHUA_RO", "TRICH6_CHUA_XONG"):
                raise DataError("M4_TRICH6_CHUA_RO", str(exc)) from None  # UNKNOWN: không ghi; giữ nguyên khóa/body để thử lại
            raise
        h2 = self._ho_so(dt, hd)  # quyền + revision HIỆN HÀNH kiểm lại sau lần gọi dài (SQL CAS vẫn là chốt cuối)
        self._kiem_rev(h2, revision)
        if h2["tep_hop_dong_id"] != h["tep_hop_dong_id"] or h2["raw_sha256"] != h["raw_sha256"]:
            raise DataError("M4_REVISION_CU", "Tệp hợp đồng đã đổi trong lúc trích — không ghi kết quả cũ.")
        return self._goi(dt, """SELECT m4.ghi_trich_xuat(%s, %s::uuid, %s::integer, %s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb) AS r""",
                         (khoa, hd, revision, h["tep_hop_dong_id"], sha256(raw), kq["catalog_sha256"], kq["engine"], kq["che_do"], kq["trang_thai"],
                          kq["ly_do"], json.dumps(kq["phieu"], ensure_ascii=False), json.dumps(kq["ket_qua"], ensure_ascii=False)), tin_cay=True)

    # ------------------------------------------------------------------ tham số & xác nhận (phòng dự án, không CFO)
    def sua_tham_so(self, dang_nhap: str, *, hop_dong_id, revision, ma, trang_thai_tham_so, gia_tri=None, don_vi=None, dieu_khoan=None,
                    trich_dan=None, ly_do=None, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        self._khoa(khoa)
        if ma not in NR.MA_DANH_MUC:
            raise DataError("M4_MA_THAM_SO_SAI", "Mã tham số không thuộc danh mục 37 mã.")
        if trang_thai_tham_so not in TRANG_THAI_SUA:
            raise DataError("M4_TRANG_THAI_THAM_SO_SAI", "Chỉ Có giá trị / Không áp dụng / Không quy định.")
        gia_tri, don_vi = _chuoi(gia_tri, "giá trị", 2000, bat_buoc=False), _chuoi(don_vi, "đơn vị", 50, bat_buoc=False)
        dieu_khoan, trich_dan = _chuoi(dieu_khoan, "điều khoản", 300, bat_buoc=False), _chuoi(trich_dan, "trích dẫn", 4000, bat_buoc=False)
        ly_do = _chuoi(ly_do, "lý do", 1000, bat_buoc=False)
        if trang_thai_tham_so == "CO_GIA_TRI":
            if not gia_tri or not trich_dan:
                raise DataError("M4_THIEU_TRICH_DAN", "Giá trị phải kèm trích dẫn nguyên văn từ hợp đồng.")
        else:
            if gia_tri:
                raise DataError("M4_KHONG_AP_DUNG_KHONG_GIA_TRI", "Không áp dụng / Không quy định không mang giá trị (không ghi 0).")
            if not ly_do:
                raise DataError("M4_THIEU_LY_DO", "Cần lý do cho Không áp dụng / Không quy định.")
        _so_nguyen(revision, "revision", 1)
        yc = {"hop_dong_id": hd, "revision": revision, "ma": ma, "trang_thai": trang_thai_tham_so, "gia_tri": gia_tri, "don_vi": don_vi,
              "dieu_khoan": dieu_khoan, "trich_dan": trich_dan, "ly_do": ly_do}
        cu = self._tra_lai(dt, "SUA_THAM_SO", khoa, yc)
        if cu is not None:
            return cu
        if self.conn_tin_cay is None:
            raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Đường kiểm/ghi tin cậy của máy chủ chưa được cấu hình — chưa nhận sửa tham số.")
        h = self._ho_so(dt, hd)
        self._kiem_rev(h, revision)
        kiem = None
        if trich_dan:  # kết quả máy kiểm do MÁY CHỦ sinh từ văn bản nguồn thật (kiểm DOCX an toàn trước — B3), không nhận từ caller
            van_ban = NR.van_ban_hop_dong(self._raw(h["raw_sha256"]), self.root / "m4-lam-viec")
            kiem = NR.kiem_trich_dan(van_ban, gia_tri if trang_thai_tham_so == "CO_GIA_TRI" else "Không áp dụng", trich_dan, dieu_khoan or "")
            if not NR.la_ok(kiem):
                raise DataError("M4_TRICH_DAN_KHONG_KHOP", f"Trích dẫn/giá trị chưa khớp tệp hợp đồng hiện hành: {kiem}")
        return self._goi(dt, "SELECT m4.sua_tham_so(%s, %s::uuid, %s::integer, %s, %s, %s, %s, %s, %s, %s, %s) AS r",
                         (khoa, hd, revision, ma, trang_thai_tham_so, gia_tri, don_vi, dieu_khoan, trich_dan, ly_do, kiem), tin_cay=True)

    def xac_nhan(self, dang_nhap: str, *, hop_dong_id, revision, ly_do=None, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        ly_do = _chuoi(ly_do, "ghi chú xác nhận", 1000, bat_buoc=False)
        _so_nguyen(revision, "revision", 1)
        yc = {"hop_dong_id": hd, "revision": revision, "ly_do": ly_do}
        cu = self._tra_lai(dt, "XAC_NHAN_THAM_SO", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.xac_nhan_tham_so(%s, %s::uuid, %s::integer, %s, %s) AS r", (khoa, hd, revision, NR.PIN[NR.CATALOG], ly_do))

    # ------------------------------------------------------------------ phụ lục
    def khai_phu_luc(self, dang_nhap: str, *, hop_dong_id, revision, khai, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        if khai not in KHAI_PHU_LUC:
            raise DataError("M4_KHAI_PHU_LUC_SAI", "Chỉ Không có / Có nhưng chưa đủ / Có và đã cung cấp đủ.")
        _so_nguyen(revision, "revision", 1)
        yc = {"hop_dong_id": hd, "revision": revision, "khai": khai}
        cu = self._tra_lai(dt, "KHAI_PHU_LUC", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.khai_phu_luc(%s, %s::uuid, %s::integer, %s) AS r", (khoa, hd, revision, khai))

    def them_phu_luc(self, dang_nhap: str, *, hop_dong_id, revision, so_pl, ngay_ky, ngay_hieu_luc, trang_thai_phu_luc, doi_boq, noi_dung=None,
                     tep_id=None, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        so_pl = _chuoi(so_pl, "số phụ lục", 100)
        nk, nhl = _ngay(ngay_ky, "ngày ký", bat_buoc=True), _ngay(ngay_hieu_luc, "ngày hiệu lực", bat_buoc=True)
        if trang_thai_phu_luc not in ("DA_KY", "DU_THAO"):
            raise DataError("M4_PHU_LUC_SAI", "Phụ lục mới là Đã ký hoặc Dự thảo.")
        if not isinstance(doi_boq, bool):
            _sai("doi_boq")
        noi_dung = _chuoi(noi_dung, "nội dung", 2000, bat_buoc=False)
        tep = _uuid(tep_id, "tep_id") if tep_id not in (None, "") else None
        _so_nguyen(revision, "revision", 1)
        yc = {"hop_dong_id": hd, "revision": revision, "so_pl": so_pl, "ngay_ky": nk, "ngay_hieu_luc": nhl, "trang_thai": trang_thai_phu_luc,
              "doi_boq": doi_boq, "noi_dung": noi_dung, "tep_id": tep}
        cu = self._tra_lai(dt, "THEM_PHU_LUC", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.them_phu_luc(%s, %s::uuid, %s::integer, %s, %s::date, %s::date, %s, %s::boolean, %s, %s::uuid) AS r",
                         (khoa, hd, revision, so_pl, nk, nhl, trang_thai_phu_luc, doi_boq, noi_dung, tep))

    def huy_phu_luc(self, dang_nhap: str, *, phu_luc_id, revision, ly_do, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        pl = _uuid(phu_luc_id, "phu_luc_id")
        ly_do = _chuoi(ly_do, "lý do hủy", 1000)
        _so_nguyen(revision, "revision", 1)
        yc = {"phu_luc_id": pl, "revision": revision, "ly_do": ly_do}
        cu = self._tra_lai(dt, "HUY_PHU_LUC", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.huy_phu_luc(%s, %s::uuid, %s::integer, %s) AS r", (khoa, pl, revision, ly_do))

    # ------------------------------------------------------------------ BOQ
    def _tep_boq(self, dt, tep_id) -> tuple[dict, Path]:
        t = self._tep(dt, _uuid(tep_id, "tep_id"))
        if not t["soan"]:
            raise DataError("M4_KHONG_CO_QUYEN_DU_AN", "Cần quyền soạn hồ sơ đúng dự án.")
        if t["vai_tro_tai_lieu"] != "BOQ":
            raise DataError("M4_TEP_SAI_VAI_TRO", "Cần tệp BOQ (.xlsx).")
        return t, NR.ban_lam_viec(self._raw(t["raw_sha256"], t["byte_length"]), self.root / "m4-lam-viec", ".xlsx")

    def boq_xem(self, dang_nhap: str, *, tep_id, sheet=None) -> dict:
        """Xem trước sheet/dòng tiêu đề/map cột gợi ý bằng bộ đọc nguồn (chỉ đọc, chưa ghi)."""
        dt = self.danh_tinh(dang_nhap)
        _, path = self._tep_boq(dt, tep_id)
        return NR.boq_xem(path, _chuoi(sheet, "sheet", 100, bat_buoc=False))

    def boq_nhap(self, dang_nhap: str, *, hop_dong_id, revision, tep_id, sheet, hang_tieu_de, cot, phu_luc_id=None, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        pl = _uuid(phu_luc_id, "phu_luc_id") if phu_luc_id not in (None, "") else None
        tep = _uuid(tep_id, "tep_id")
        _so_nguyen(revision, "revision", 1)
        if not isinstance(cot, dict) or not isinstance(sheet, str) or isinstance(hang_tieu_de, bool) or not isinstance(hang_tieu_de, int):
            _sai("map BOQ")
        yc = {"hop_dong_id": hd, "revision": revision, "tep_id": tep, "phu_luc_id": pl, "sheet": sheet, "hang_tieu_de": hang_tieu_de, "cot": cot}
        cu = self._tra_lai(dt, "NHAP_BOQ", khoa, yc)
        if cu is not None:
            return cu
        if self.conn_tin_cay is None:
            raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Đường ghi nguồn tin cậy của máy chủ chưa được cấu hình — chưa nhận kết quả đọc BOQ.")
        h = self._ho_so(dt, hd)
        self._kiem_rev(h, revision)
        t, path = self._tep_boq(dt, tep)
        if t["du_an_id"] != h["du_an_id"]:
            raise DataError("M4_TEP_SAI_VAI_TRO", "Tệp BOQ không thuộc dự án của hợp đồng.")
        rows, loi_chan, phat_hien = NR.boq_doc(path, sheet, hang_tieu_de, cot)
        # FINAL (kể cả mảng loi_chan/phat_hien đầy đủ) do ghi_boq chốt trong biên nhận — fresh và replay trả cùng một hình dạng
        return self._goi(dt, """SELECT m4.ghi_boq(%s, %s::uuid, %s::integer, %s::uuid, %s, %s::uuid, %s, %s::integer, %s::jsonb, %s, %s::jsonb, %s::jsonb,
                                                %s::jsonb) AS r""",
                       (khoa, hd, revision, t["id"], t["raw_sha256"], pl, sheet, hang_tieu_de, json.dumps(cot, ensure_ascii=False), NR.BO_DOC_BOQ,
                        json.dumps(rows, ensure_ascii=False), json.dumps(loi_chan, ensure_ascii=False), json.dumps(phat_hien, ensure_ascii=False)),
                       tin_cay=True)

    # ------------------------------------------------------------------ đợt thanh toán
    def _dot(self, dt, dot_id) -> dict:
        with self._tx(dt):
            d = self._mot("SELECT id, hop_dong_id, du_an_id, revision, trang_thai FROM m4.dot WHERE id = %s::uuid", (dot_id,))
        if d is None:
            raise DataError("M4_KHONG_THAY_DOT", "Không thấy đợt (hoặc ngoài phạm vi).")
        return d

    def tao_dot(self, dang_nhap: str, *, hop_dong_id, so_dot, ngay_nghiem_thu=None, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id")
        so = _so_nguyen(so_dot, "số đợt", 1, 999)
        ngay = _ngay(ngay_nghiem_thu, "ngày nghiệm thu")
        yc = {"hop_dong_id": hd, "so_dot": so, "ngay_nghiem_thu": ngay}
        cu = self._tra_lai(dt, "TAO_DOT", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.tao_dot(%s, %s::uuid, %s::integer, %s::date) AS r", (khoa, hd, so, ngay))

    def sua_dot(self, dang_nhap: str, *, dot_id, revision, ngay_nghiem_thu, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        di = _uuid(dot_id, "dot_id")
        _so_nguyen(revision, "revision", 1)
        ngay = _ngay(ngay_nghiem_thu, "ngày nghiệm thu", bat_buoc=True)
        yc = {"dot_id": di, "revision": revision, "ngay_nghiem_thu": ngay}
        cu = self._tra_lai(dt, "SUA_DOT", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.sua_dot(%s, %s::uuid, %s::integer, %s::date) AS r", (khoa, di, revision, ngay))

    def gan_tep_dot(self, dang_nhap: str, *, dot_id, revision, tep_id, muc, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        di, tep = _uuid(dot_id, "dot_id"), _uuid(tep_id, "tep_id")
        _so_nguyen(revision, "revision", 1)
        if muc not in NR.MA_HO_SO:
            raise DataError("M4_MUC_HO_SO_SAI", "Mục hồ sơ không có trong danh mục.")
        yc = {"dot_id": di, "revision": revision, "tep_id": tep, "muc": muc}
        cu = self._tra_lai(dt, "GAN_TEP_DOT", khoa, yc)
        if cu is not None:
            return cu
        return self._goi(dt, "SELECT m4.gan_tep_dot(%s, %s::uuid, %s::integer, %s::uuid, %s) AS r", (khoa, di, revision, tep, muc))

    def nop(self, dang_nhap: str, *, dot_id, revision_ho_so, revision_dot, khoa) -> dict:
        """Nộp chính thức: CSDL tra biên nhận trước, rồi kiểm lại toàn bộ căn cứ dưới khóa + revision mong đợi, dựng snapshot/digest và chốt
        biên nhận FINAL trong cùng giao dịch; chưa tự duyệt/chuyển nhánh sau."""
        dt = self.danh_tinh(dang_nhap)
        di = _uuid(dot_id, "dot_id")
        _so_nguyen(revision_ho_so, "revision_ho_so", 1)
        _so_nguyen(revision_dot, "revision_dot", 1)
        yc = {"dot_id": di, "revision_ho_so": revision_ho_so, "revision_dot": revision_dot}
        kq = self._tra_lai(dt, "NOP", khoa, yc)
        if kq is None:
            kq = self._goi(dt, "SELECT m4.nop(%s, %s::uuid, %s::integer, %s::integer) AS r", (khoa, di, revision_ho_so, revision_dot))
        return {**kq, "nhanh_sau": list(NHANH_SAU)}

    # ================================================================== M4-02A Review L1/L2 (M19 m4.review_*)
    # Luồng: (1) quyền + phạm vi HIỆN HÀNH rồi tra biên nhận Review (cùng body/khóa → FINAL cũ, trước mọi việc tốn kém; khác → 409)
    #        (2) MỘT giao dịch REPEATABLE READ trên kết nối chủ bảng: chụp basis ĐẦY ĐỦ từ PG, so expected_basis, tạo lần chạy RUNNING — đóng ngay
    #        (3) tính trong TIẾN TRÌNH CON do máy chủ sở hữu (không DSN/PG/credential; chỉ bản XLSX đã giữ + basis) — không giữ khóa CSDL
    #        (4) công bố: khóa HĐ FOR SHARE, kiểm lại quyền/phạm vi hiện hành, chụp lại basis rồi so TOÀN token (đổi → STALE), chốt FINAL + biên nhận.
    #        Mất quyền trước công bố → CANCELLED giữ bằng chứng, không công bố. Lỗi/timeout tiến trình con → FAILED (không bao giờ thành PASS).
    REVIEW_TOI_DA_GIAY = 900
    REVIEW_CHE_DO = ("L1", "L1_L2")
    # allowlist KHÔNG bí mật: hệ thống + cờ khởi động giữ tệp của tiến trình cha (FIX01 R2). Không DSN/PG*/mật khẩu/phiên.
    _ENV_WORKER = ("SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL",
                   "PYTHONUSERBASE", "CODEX_NO_DELETE_FILES", "PYTHONUTF8")
    _ENV_CAM = re.compile(r"(?i)(DSN|PASSWORD|PASSWD|SECRET|TOKEN|^PG|CREDENTIAL)")

    @contextmanager
    def _tx_review(self, dt, *, rr: bool = False):
        c = self.conn_tin_cay
        if c is None:
            raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Review cần đường tin cậy của máy chủ (kết nối chủ bảng) — chưa cấu hình; không chạy bằng quyền "
                                                          "người dùng thường.")
        with c.transaction():
            if rr:
                c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                      "set_config('ktt.ngay_hieu_luc', %s, true)", (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat()))
            yield c

    @staticmethod
    def _r1(c, sql, params=()):
        row = c.execute(sql, params).fetchone()
        return None if row is None else _v(dict(row))

    @staticmethod
    def _rn(c, sql, params=()):
        return [_v(dict(r)) for r in c.execute(sql, params)]

    @staticmethod
    def _hex(v, ten: str) -> str:
        if not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v):
            raise DataError("M4_REVIEW_CO_SO_SAI", f"{ten} phải là SHA-256 của căn cứ đang xem (lấy từ danh sách Review).")
        return v

    @contextmanager
    def _khoa_phien(self, dt, khoa: str):
        """Khóa tư vấn MỨC PHIÊN trên kết nối chủ bảng theo (actor + khóa) suốt bước 1–4: request Review trùng khóa chờ đến khi FINAL được chốt
        rồi mới tra biên nhận (không tính hai lần, không chụp snapshot cũ). Không khóa HĐ/dữ liệu nghiệp vụ.
        FIX01 R5: namespace RIÊNG `m4:review:` — KHÔNG dùng namespace giao dịch `m4:bien_nhan:` của M17 (M17 khóa HĐ rồi mới lấy khóa biên nhận);
        thứ tự toàn cục: [m4:review phiên] → HĐ → [m4:bien_nhan giao dịch], trùng thứ tự M17 → không vòng khóa. Xung đột cùng actor+khóa khác hành
        động chặn chính xác ở m4.review_tra / trigger biên nhận M19 (trước hiệu lực), không dựa vào chờ khóa."""
        c = self.conn_tin_cay
        if c is None:
            raise DataError("M4_CHUA_SAN_SANG_GHI_NGUON", "Review cần đường tin cậy của máy chủ — chưa cấu hình.")
        k = f"m4:review:{dt['id']}:{khoa}"
        c.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (k,))
        try:
            yield
        finally:
            c.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (k,))

    def _co_so(self, c, *, du_an: str, tep: str, dot: str | None, che_do: str, o_dich) -> dict:
        """Basis ĐẦY ĐỦ chụp từ PG (gọi trong giao dịch của người gọi): tệp + raw, đợt + nộp, HĐ + revision/tham số 37 mã (trạng thái typed)/lần
        trích/xác nhận + digest hiện tại, mọi phụ lục, BOQ hiện hành từng nguồn (TẤT CẢ dòng, không LIMIT GUI), ghép tay hiện hành THẤY ĐƯỢC theo
        quyền phiên, các đợt của HĐ và trạng thái nguồn đợt trước đã duyệt (chưa có ở gói này). Không nhận dữ kiện máy từ trình duyệt."""
        t = self._r1(c, """SELECT id, du_an_id, phap_nhan_id, vai_tro_tai_lieu, raw_sha256, byte_length, ten_goc, media_type FROM m4.tep
                           WHERE id = %s::uuid""", (tep,))
        co = {"phien_ban": "m4.review.basis/1", "che_do": che_do, "o_dich": o_dich, "du_an_id": du_an, "phap_nhan_id": (t or {}).get("phap_nhan_id"),
              "engine_sha256": NR.ENGINE_REVIEW_SHA, "tep": t, "dot": None, "dot_tep": [], "hop_dong": None}
        if not dot:
            return co
        d = self._r1(c, """SELECT d.id, d.hop_dong_id, d.du_an_id, d.so_dot, d.ngay_nghiem_thu, d.trang_thai, d.revision, n.id AS nop_id,
                                  n.digest AS nop_digest, n.revision_ho_so AS nop_revision_ho_so
                           FROM m4.dot d LEFT JOIN m4.nop n ON n.dot_id = d.id WHERE d.id = %s::uuid""", (dot,))
        co["dot"] = d
        co["dot_tep"] = self._rn(c, "SELECT tep_id, muc FROM m4.dot_tep WHERE dot_id = %s::uuid ORDER BY muc, tep_id", (dot,))
        if d is None or che_do != "L1_L2":
            return co
        hd = d["hop_dong_id"]
        co["hop_dong"] = self._r1(c, """SELECT h.hop_dong_id AS id, hd.so_hop_dong, h.ten, h.revision, h.rev_tham_so, h.trang_thai_pl, h.tep_hop_dong_id,
                                               t.raw_sha256 AS tep_hop_dong_sha256
                                        FROM m4.ho_so_hop_dong h JOIN master.hop_dong hd ON hd.id = h.hop_dong_id LEFT JOIN m4.tep t ON t.id = h.tep_hop_dong_id
                                        WHERE h.hop_dong_id = %s::uuid""", (hd,))
        co["tham_so"] = self._rn(c, """SELECT c.ma, coalesce(s.trang_thai, 'CHUA_CO') AS trang_thai, s.gia_tri, s.don_vi, s.trich_xuat_id, s.nguon
                                       FROM m4.danh_muc_tham_so c LEFT JOIN m4.tham_so s ON s.ma = c.ma AND s.hop_dong_id = %s::uuid ORDER BY c.thu_tu""", (hd,))
        tx = self._r1(c, "SELECT id, lan, trang_thai, tep_id, raw_sha256, catalog_sha256 FROM m4.trich_xuat WHERE hop_dong_id = %s::uuid ORDER BY lan DESC LIMIT 1",
                      (hd,))
        co["trich_xuat"] = tx
        xn = self._r1(c, """SELECT id, rev_tham_so, trich_xuat_id, tham_so_digest, catalog_sha256 FROM m4.xac_nhan_tham_so WHERE hop_dong_id = %s::uuid
                            ORDER BY rev_tham_so DESC LIMIT 1""", (hd,))
        dg = self._r1(c, "SELECT m4.digest_tham_so(%s::uuid) AS d", (hd,))["d"]
        h = co["hop_dong"] or {}
        if xn:
            xn["digest_hien_tai"] = dg
            xn["con_hieu_luc"] = bool(tx and tx["trang_thai"] == "XONG" and tx["tep_id"] == h.get("tep_hop_dong_id") and xn["rev_tham_so"] == h.get("rev_tham_so")
                                      and xn["trich_xuat_id"] == tx["id"] and xn["tham_so_digest"] == dg)
        co["xac_nhan"] = xn
        co["phu_luc"] = self._rn(c, """SELECT id, so_pl, ngay_ky, ngay_hieu_luc, trang_thai, doi_boq, tep_id FROM m4.phu_luc WHERE hop_dong_id = %s::uuid
                                       ORDER BY ngay_hieu_luc, so_pl, tao_luc""", (hd,))
        boq = self._rn(c, """SELECT b.id, b.lan, b.phu_luc_id, b.tep_id, b.raw_sha256, b.sheet, b.hang_tieu_de, b.cot, b.so_dong, b.trang_thai, b.bo_doc
                             FROM m4.boq b WHERE b.hop_dong_id = %s::uuid
                               AND b.lan = (SELECT max(z.lan) FROM m4.boq z WHERE z.hop_dong_id = b.hop_dong_id AND z.phu_luc_id IS NOT DISTINCT FROM b.phu_luc_id)
                             ORDER BY b.lan""", (hd,))
        for b in boq:
            b["dong"] = self._rn(c, """SELECT dong, ma_hm, thao_tac, stt, nhom, ten, dvt, kl, don_gia, thanh_tien, ma_rieng FROM m4.boq_dong
                                       WHERE boq_id = %s::uuid ORDER BY dong""", (b["id"],))
        co["boq"] = boq
        co["manual_map"] = self._rn(c, """SELECT DISTINCT ON (m.khoa_hstt) m.id, m.khoa_hstt, m.revision, m.ma_hm, m.boq_id, m.boq_dong, m.run_id, m.tao_boi,
                                                 m.tao_luc
                                          FROM m4.review_manual_map m WHERE m.hop_dong_id = %s::uuid AND m4.review_doc_duoc(m.run_id)
                                          ORDER BY m.khoa_hstt, m.revision DESC""", (hd,))
        co["dot_hd"] = self._rn(c, "SELECT id, so_dot, trang_thai, ngay_nghiem_thu FROM m4.dot WHERE hop_dong_id = %s::uuid ORDER BY so_dot", (hd,))
        # M4-02C: provider quyết định ĐÃ SEAL của đợt trước (m4/duyet_dot.lich_su_da_duyet); chưa schema M24/chưa đợt trước nào seal → giữ nguyên lý do cũ
        co["truoc_da_duyet"] = DD.lich_su_da_duyet(self, c, d) or {
            "trang_thai": "CHUA_CO_NGUON",
            "ly_do": "Gói M4-02A chưa có lịch sử đợt trước đã được reviewer duyệt (DA_NOP chỉ là đã nộp) — không suy từ số đợt/vắng dữ "
                     "liệu, không coi vắng là 0; nối khi có quyết định duyệt bất biến"}
        return NR.chup_review_l2(co, c)

    @staticmethod
    def _sha_co_so(co: dict) -> str:
        return sha256(canonical_json(co).encode("utf-8"))

    @classmethod
    def _env_worker(cls, environ=None, modules=None, dau_cha=None) -> dict:
        """FIX01 R2/FIX02 F1 — môi trường tiến trình tính: giữ NGUYÊN chế độ khởi động giữ tệp của tiến trình cha (PYTHONUSERBASE, CODEX_NO_DELETE_FILES,
        thư mục sitecustomize nếu có) + đường dẫn phụ thuộc thật (PYTHONPATH launcher đặt, nguồn gốc openpyxl đang dùng) + không bytecode + dấu vân
        hook giữ tệp THẬT của cha (KTT_REVIEW_GUARD_DAU). Không truyền toàn bộ env; tên biến dạng DSN/mật khẩu/token bị loại. Con kiểm hook thật
        (review_compute.guard_dang_nap) trước mọi I/O."""
        import importlib.util
        from ..m4.review_compute import ENV_GUARD_DAU, dau_van_guard, hook_hoat_dong
        environ = os.environ if environ is None else environ
        modules = sys.modules if modules is None else modules
        env = {k: environ[k] for k in cls._ENV_WORKER if k in environ and not cls._ENV_CAM.search(k)}
        duong = [str(Path(__file__).resolve().parents[2])]
        them = lambda p: duong.append(p) if p and p not in duong and "://" not in p and "@" not in p else None  # noqa: E731 — chỉ đường dẫn
        for p in (environ.get("PYTHONPATH") or "").split(os.pathsep):  # phụ thuộc + thư mục guard do launcher runtime đặt
            them(p)
        g = modules.get("sitecustomize")  # provenance khởi động của cha (đường dẫn) — KHÔNG dùng làm bằng chứng hook
        gf = getattr(g, "__file__", None) if g else None
        if gf:
            them(str(Path(gf).resolve().parent))
        # FIX02 F1: bằng chứng là hook xóa/ghi đè THẬT đang cài trong tiến trình máy chủ (dau_van_guard), gửi cho con để so cùng provenance.
        # Cha yêu cầu giữ tệp (cờ bật) hoặc chính cha đang có hook → con bắt buộc chứng minh hook thật, không thì dừng trước mọi I/O.
        dau = dau_van_guard() if dau_cha is None else dau_cha
        bat = str(environ.get("CODEX_NO_DELETE_FILES") or "").strip().lower() in ("1", "true", "yes", "on")
        if bat or hook_hoat_dong(dau):
            env[ENV_GUARD_DAU] = json.dumps(dau, ensure_ascii=False, sort_keys=True)
        try:
            sp = importlib.util.find_spec("openpyxl")  # chỉ tra nguồn gốc, không thực thi module
        except (ImportError, ValueError):
            sp = None
        if sp is not None and sp.submodule_search_locations:
            them(str(Path(list(sp.submodule_search_locations)[0]).resolve().parent))
        env.update(PYTHONPATH=os.pathsep.join(duong), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        return env

    def _chay_worker(self, thu_muc: Path):
        """Tiến trình con do máy chủ sở hữu: môi trường `_env_worker` (KHÔNG DSN/PG/credential), cwd = thư mục lần chạy, timeout hữu hạn (hết giờ →
        subprocess.run kill + chờ con dừng hẳn rồi mới trả). Chỉ đọc vao.json + bản XLSX đã giữ; ghi kết quả/báo cáo vào đúng thư mục này."""
        return subprocess.run([sys.executable, "-m", "kho_tri_thuc.m4.review_compute", str(thu_muc)], cwd=str(thu_muc), env=self._env_worker(),
                              capture_output=True, timeout=self.REVIEW_TOI_DA_GIAY, check=False)

    def _luu_artifact(self, raw: bytes, loai: str, ten: str) -> dict:
        sha = sha256(raw)
        write_immutable(self.root / "m4-review" / sha, raw)
        return {"loai": loai, "ten": ten[:200], "raw_sha256": sha, "byte_length": len(raw)}

    def _review_tinh(self, run_id: str, co: dict, sha_co_so: str, che_do: str, o_dich) -> tuple[dict, list, str | None]:
        from ..m4.review_compute import MA_GUARD_KHONG_NAP
        thu_muc = self.root / "m4-review-run" / run_id
        tep = co["tep"]
        co_b = canonical_json(co).encode("utf-8")
        vao_b = None
        ly_do, log = None, b""
        # FIX01 R4: RUNNING đã commit → MỌI bước dựng (thư mục riêng, raw/hash, bản làm việc, đầu vào) nằm trong nhánh kết thúc có bằng chứng:
        # lỗi dựng → FAILED đúng nguyên nhân (giữ phần đã ghi), không để RUNNING vĩnh viễn, không tự thử lại/khóa mới.
        try:
            thu_muc.mkdir(parents=True, exist_ok=False)  # đường dẫn riêng, tạo mới cho đúng lần chạy này (không ghi đè lần khác)
            chep = co.get("review_chep") or {}
            if chep.get("can_xem_lai"):
                raise DataError("M4_REVIEW_CAN_XEM_LAI", "Cần xem lại nguồn phụ lục/BOQ: " + " ".join(chep["ly_do"]) + " Chưa tính.")
            raw = self._raw(tep["raw_sha256"], tep["byte_length"])
            xlsx = NR.ban_lam_viec(raw, self.root / "m4-lam-viec", ".xlsx")
            vao = {"run_id": run_id, "basis": co, "basis_sha256": sha_co_so, "xlsx": str(xlsx), "raw_sha256": tep["raw_sha256"], "che_do": che_do,
                   "o_dich": o_dich}
            vao_b = canonical_json(vao).encode("utf-8")
            write_immutable(thu_muc / "vao.json", vao_b)
            write_immutable(thu_muc / "co_so.json", co_b)
        except Exception as exc:  # noqa: BLE001 — lỗi dựng thật là bằng chứng FAILED, không nuốt thành đạt
            ma = getattr(exc, "code", None) or type(exc).__name__
            ly_do = f"SETUP_LOI: chưa khởi chạy tiến trình tính ({ma}: {str(exc)[:300]})"
            log = ly_do.encode("utf-8")
        if ly_do is None:
            try:
                p = self._chay_worker(thu_muc)
                log = (p.stdout or b"") + b"\n--- stderr ---\n" + (p.stderr or b"") + f"\n--- exit {p.returncode} ---\n".encode()
                if p.returncode == MA_GUARD_KHONG_NAP:
                    ly_do = "GUARD_KHONG_NAP: chế độ giữ tệp bật nhưng hook giữ tệp thật không cài trong tiến trình tính — dừng trước mọi I/O; không phải kết quả đạt"
                elif p.returncode != 0:  # FIX02 F3: chỉ exit 0 của chính tiến trình con đã kết thúc mới được xét kết quả thành công
                    ly_do = f"WORKER_EXIT_{p.returncode}: tiến trình tính kết thúc mã {p.returncode} — không nhận kết quả thành công dù có ket_qua.json"
            except subprocess.TimeoutExpired as exc:
                ly_do = f"TIMEOUT: tiến trình tính vượt {self.REVIEW_TOI_DA_GIAY}s — đã dừng tiến trình con; không phải kết quả đạt"
                log = (exc.stdout or b"") + b"\n--- stderr ---\n" + (exc.stderr or b"") + b"\n--- TIMEOUT ---\n"
            except OSError as exc:
                ly_do = f"Không khởi chạy được tiến trình tính ({type(exc).__name__})"
                log = ly_do.encode("utf-8")
        try:
            if thu_muc.is_dir():
                write_immutable(thu_muc / "worker.log", log or b"(trong)")
        except Exception:  # noqa: BLE001 — log đã có trong artifact LOG bên dưới
            pass
        p_kq = thu_muc / "ket_qua.json"
        try:  # kết quả (nếu có) luôn giữ làm bằng chứng, kể cả khi timeout/lỗi dựng — nhưng chỉ được dùng khi tiến trình kết thúc bình thường
            kq_b = p_kq.read_bytes() if p_kq.is_file() else None
        except OSError:
            kq_b = None
        kq = {"trang_thai": "FAILED"}
        if ly_do is None and kq_b is not None:
            try:
                kq = json.loads(kq_b.decode("utf-8"))
            except ValueError:
                ly_do = "ket_qua.json không đọc được"
            if not isinstance(kq, dict):
                kq, ly_do = {"trang_thai": "FAILED"}, "ket_qua.json không phải object"
        else:
            ly_do = ly_do or "Tiến trình tính không tạo ket_qua.json"
        if kq.get("trang_thai") in ("SUCCEEDED", "PARTIAL") and (kq.get("raw_sha256") != tep["raw_sha256"] or kq.get("basis_sha256") != sha_co_so):
            kq, ly_do = {"trang_thai": "FAILED", "loi": "Kết quả không khớp raw/basis đầu vào"}, "Kết quả không khớp raw/basis đầu vào"
        if kq.get("trang_thai") in ("SUCCEEDED", "PARTIAL") and not self._hinh_dang_ok(kq, che_do, o_dich):  # FIX02 F3: đúng phạm vi + hình dạng
            kq, ly_do = {"trang_thai": "FAILED", "loi": "Kết quả sai phạm vi/hình dạng"}, "Kết quả sai phạm vi/hình dạng (chế độ/ô đích/coverage/lớp)"
        if ly_do:
            kq = {**kq, "trang_thai": "FAILED", "loi": kq.get("loi") or ly_do}
        art = []

        def luu(raw_b, loai, ten):  # lỗi lưu một artifact không làm mất các bằng chứng khác hay để RUNNING treo
            nonlocal kq, ly_do
            try:
                art.append(self._luu_artifact(raw_b() if callable(raw_b) else raw_b, loai, ten))
            except Exception as exc:  # noqa: BLE001
                if loai.startswith("REPORT_") and kq.get("trang_thai") in ("SUCCEEDED", "PARTIAL"):
                    ly_do = f"Không lưu được báo cáo {loai} ({type(exc).__name__}) — không công bố kết quả thiếu báo cáo"
                    kq = {**kq, "trang_thai": "FAILED", "loi": ly_do}
        luu(co_b, "BASIS", f"review-{run_id[:8]}-co_so.json")
        if vao_b is not None:
            luu(vao_b, "INPUT", f"review-{run_id[:8]}-vao.json")
        luu(log or b"(trong)", "LOG", f"review-{run_id[:8]}-worker.log")
        if kq_b:
            luu(kq_b, "RESULT", f"review-{run_id[:8]}-ket_qua.json")
        if kq["trang_thai"] in ("SUCCEEDED", "PARTIAL"):
            for b in kq.get("bao_cao") or []:
                f = thu_muc / b["tep"]
                if b["loai"] in ("REPORT_L1", "REPORT_L2", "REPORT_L1_NGUON", "REPORT_L2_NGUON") and re.fullmatch(r"[a-z0-9_]+\.xlsx", b["tep"]) and f.is_file():
                    luu(f.read_bytes, b["loai"], f"review-{run_id[:8]}-{b['tep']}")
        return kq, art, ly_do

    @staticmethod
    def _hinh_dang_ok(kq: dict, che_do: str, o_dich) -> bool:
        """FIX02 F3 — kết quả thành công phải đúng chế độ/ô đích đã yêu cầu, đủ coverage K1–K8 (+GT/B1–B8 khi L1+L2) mỗi mã có trạng thái hợp lệ,
        trạng thái tổng khớp coverage, lớp 1 là object và lớp 2 có mặt đúng khi L1+L2."""
        from ..m4 import review_compute as RC
        cov = kq.get("coverage")
        ma = set(RC.MA_L1) | (set(RC.MA_L2) if che_do == "L1_L2" else set())
        if kq.get("che_do") != che_do or (kq.get("o_dich") or None) != (o_dich or None) or not isinstance(cov, dict) or set(cov) != ma:
            return False
        if any(not isinstance(v, dict) or v.get("trang_thai") not in RC.THU_TU for v in cov.values()):
            return False
        dung = "SUCCEEDED" if all(v["trang_thai"] in RC.DAT_DU for v in cov.values()) else "PARTIAL"
        if kq.get("trang_thai") != dung or not isinstance(kq.get("lop1"), dict):
            return False
        return (che_do == "L1_L2") == isinstance(kq.get("lop2"), dict)

    def _review_cong_bo(self, dt, run_id: str, kq: dict, art: list, ly_do, *, du_an, tep, dot, che_do, o_dich) -> dict:
        import psycopg
        tt = kq["trang_thai"] if kq.get("trang_thai") in ("SUCCEEDED", "PARTIAL") else "FAILED"
        kq_j = canonical_json(kq)
        kq_sha = sha256(kq_j.encode("utf-8"))
        art_j = json.dumps(art, ensure_ascii=False)
        try:
            with self._tx_review(dt) as c:
                if dot:  # ổn định basis trong giao dịch công bố: mọi lệnh M4 sửa HĐ/đợt/BOQ/PL/tham số/ghép tay đều cần FOR UPDATE hàng này
                    c.execute("""SELECT 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = (SELECT hop_dong_id FROM m4.dot WHERE id = %s::uuid) FOR SHARE""", (dot,))
                c.execute("SELECT m4.review_kiem(%s::uuid, %s::uuid, %s::uuid)", (du_an, dot, tep))
                # FAILED không công bố kết quả tính; không đọc lại nguồn đang lỗi
                # ở lần đóng dự phòng (NULL không được dùng như một basis đã kiểm).
                sha_nay = None if tt == "FAILED" else self._sha_co_so(self._co_so(c, du_an=du_an, tep=tep, dot=dot, che_do=che_do, o_dich=o_dich))
                r = self._r1(c, "SELECT m4.review_cong_bo(%s::uuid, %s::jsonb, %s, %s::jsonb, %s, %s, %s::jsonb, %s) AS r",
                             (run_id, kq_j, kq_sha, json.dumps(kq.get("coverage") or {}, ensure_ascii=False), tt, sha_nay, art_j, ly_do))["r"]
        except (psycopg.Error, DataError) as exc:
            ma = getattr(exc, "code", None) or ((getattr(getattr(exc, "diag", None), "message_primary", "") or "").split(":", 1)[0]).strip()
            if ma in ("M4_KHONG_CO_QUYEN_DU_AN", "M4_REVIEW_PHAM_VI", "M4_DANH_TINH"):
                with self._tx_review(dt) as c:
                    c.execute("SELECT m4.review_huy(%s::uuid, %s, %s::jsonb, %s::jsonb)",
                              (run_id, f"Quyền/phạm vi hiện hành đổi trước khi công bố ({ma}) — giữ bằng chứng, không công bố kết quả", kq_j, art_j))
                raise
            # FIX01 R4: lỗi công bố khác (vd kết quả không ghi được) → thử MỘT lần đóng FAILED kèm bằng chứng (cùng quyền hiện hành); vẫn lỗi → báo lỗi gốc
            if tt != "FAILED":
                try:
                    return self._review_cong_bo(dt, run_id, {"trang_thai": "FAILED", "loi": f"Công bố lỗi ({ma or type(exc).__name__})"}, art,
                                                f"Công bố kết quả lỗi ({ma or type(exc).__name__}) — đóng FAILED, giữ bằng chứng",
                                                du_an=du_an, tep=tep, dot=dot, che_do=che_do, o_dich=o_dich)
                except (psycopg.Error, DataError):
                    pass
            raise
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    def _review_khoi(self, dt, hanh: str, khoa: str, yc: dict, *, du_an: str, tep: str, dot, che_do: str, o_dich, exp: str, parent=None) -> dict:
        yc_j = json.dumps(yc, ensure_ascii=False)
        with self._khoa_phien(dt, khoa):
            # (1) FIX02 F4: giao dịch READ COMMITTED NGẮN — quyền/phạm vi hiện hành → khóa giao dịch biên nhận → FINAL cũ (đúng body) hoặc xung đột
            # (khác hành động/body) → GIỮ CHỖ (actor, khóa); COMMIT tại đây, TRƯỚC snapshot RR. Từ đó biên nhận khác hành động cùng khóa bị trigger chặn.
            with self._tx_review(dt) as c:
                g = self._r1(c, "SELECT m4.review_giu(%s, %s, %s::uuid, %s::uuid, %s::uuid, %s::jsonb) AS r", (khoa, hanh, du_an, dot, tep, yc_j))["r"]
            if g["lap_lai"]:
                return {**g["ket_qua"], "lap_lai": True}
            with self._tx_review(dt, rr=True) as c:  # (2) một snapshot RR: quyền → basis → CAS expected → tạo lần chạy
                c.execute("SELECT m4.review_kiem(%s::uuid, %s::uuid, %s::uuid)", (du_an, dot, tep))
                co = self._co_so(c, du_an=du_an, tep=tep, dot=dot, che_do=che_do, o_dich=o_dich)
                sha = self._sha_co_so(co)
                if sha != exp:
                    raise DataError("M4_REVIEW_CO_SO_DOI", "Căn cứ (tệp/đợt/HĐ/tham số/PL/BOQ/ghép tay) đã đổi so với lúc xem — tải lại danh sách Review rồi chạy.")
                hd = (co.get("dot") or {}).get("hop_dong_id")
                r = self._r1(c, """SELECT m4.review_tao_run(%s, %s, %s::jsonb, %s, %s::uuid, %s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s::jsonb, %s, %s, %s,
                                                            %s::uuid) AS r""",
                             (khoa, hanh, yc_j, sha256(canonical_json({"hanh": hanh, "yc": yc}).encode("utf-8")), du_an, hd, dot, tep, co["tep"]["raw_sha256"],
                              che_do, o_dich, canonical_json(co), sha, NR.ENGINE_REVIEW, NR.ENGINE_REVIEW_SHA, parent))["r"]
            if r["lap_lai"]:
                return {**r["ket_qua"], "lap_lai": True, "dang_chay": bool(r.get("dang_chay"))}
            run_id = r["ket_qua"]["run_id"]
            try:  # (3) không giao dịch/khóa CSDL nghiệp vụ; FIX01 R4: mọi lỗi sau RUNNING → FAILED có bằng chứng, không RUNNING vĩnh viễn
                kq, art, ly_do = self._review_tinh(run_id, co, sha, che_do, o_dich)
            except Exception as exc:  # noqa: BLE001
                ly_do = f"LOI_KHONG_LUONG_TRUOC: {type(exc).__name__}: {str(exc)[:300]}"
                kq, art = {"trang_thai": "FAILED", "loi": ly_do}, []
            return self._review_cong_bo(dt, run_id, kq, art, ly_do, du_an=du_an, tep=tep, dot=dot, che_do=che_do, o_dich=o_dich)  # (4)

    def review_chay(self, dang_nhap: str, *, du_an_id, tep_id, mode, dot_id=None, o_dich=None, expected_basis, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        du_an, tep = _uuid(du_an_id, "du_an_id"), _uuid(tep_id, "tep_id")
        dot = _uuid(dot_id, "dot_id") if dot_id not in (None, "") else None
        if mode not in self.REVIEW_CHE_DO:
            raise DataError("M4_REVIEW_CHE_DO_SAI", "Chế độ Review là L1 hoặc L1_L2.")
        if mode == "L1_L2" and dot is None:
            raise DataError("M4_REVIEW_CAN_DOT", "L1+L2 cần chọn đợt (ngày nghiệm thu) của hợp đồng.")
        o = NR.kiem_o_dich(o_dich)
        exp, khoa = self._hex(expected_basis, "expected_basis"), self._khoa(khoa)
        yc = {"du_an_id": du_an, "tep_id": tep, "che_do": mode, "dot_id": dot, "o_dich": o, "expected_basis": exp}
        return self._review_khoi(dt, "REVIEW_CHAY", khoa, yc, du_an=du_an, tep=tep, dot=dot, che_do=mode, o_dich=o, exp=exp)

    def _run_thay(self, dt, run: str) -> dict:
        """Lần chạy THẤY ĐƯỢC theo quyền hiện hành (RLS m4.review_doc_duoc trên login ứng dụng) — kiểm TRƯỚC mọi tra biên nhận/đọc kết quả."""
        with self._tx(dt):
            r = self._mot("""SELECT id, du_an_id, hop_dong_id, dot_id, tep_id, raw_sha256, che_do, o_dich, trang_thai, basis_sha256 FROM m4.review_run
                             WHERE id = %s::uuid""", (run,))
        if r is None:
            raise DataError("M4_REVIEW_KHONG_THAY", "Không thấy lần chạy Review (hoặc ngoài phạm vi hiện hành).")
        return r

    def review_chay_lai(self, dang_nhap: str, *, run_id, expected_basis, khoa) -> dict:
        """Chạy lại: CÙNG tệp gốc (raw) + đợt + chế độ + ô đích của lần chạy cha, trên basis hiện hành đã chọn (gồm ghép tay mới) → lần chạy CON
        mới; lần chạy/kết quả/báo cáo cũ giữ nguyên."""
        dt = self.danh_tinh(dang_nhap)
        run = _uuid(run_id, "run_id")
        exp, khoa = self._hex(expected_basis, "expected_basis"), self._khoa(khoa)
        p = self._run_thay(dt, run)
        yc = {"run_id": run, "expected_basis": exp}
        return self._review_khoi(dt, "REVIEW_CHAY_LAI", khoa, yc, du_an=p["du_an_id"], tep=p["tep_id"], dot=p["dot_id"], che_do=p["che_do"],
                                 o_dich=p["o_dich"], exp=exp, parent=run)

    def review_ghep(self, dang_nhap: str, *, run_id, khoa_dong, boq_id, ma_hm, expected_basis, ly_do, khoa) -> dict:
        """Ghép tay: giữ khoa_hstt gốc của dòng hồ sơ; đích là đúng MỘT dòng BOQ typed hiện hành cùng HĐ; ghi revision mới (không sửa kết quả lần
        chạy cũ). Phạm vi: các lần chạy SAU của cùng HĐ, dòng cùng khóa — không áp HĐ khác."""
        dt = self.danh_tinh(dang_nhap)
        run, boq = _uuid(run_id, "run_id"), _uuid(boq_id, "boq_id")
        khoa_dong = _chuoi(khoa_dong, "khóa dòng hồ sơ", 1000)
        ma_hm = _chuoi(ma_hm, "mã hạng mục BOQ", 500)
        ly_do = _chuoi(ly_do, "lý do ghép tay", 1000)
        exp, khoa = self._hex(expected_basis, "expected_basis"), self._khoa(khoa)
        p = self._run_thay(dt, run)
        with self._tx(dt):
            x = self._mot("""SELECT x.ket_qua->'lop2'->>'bang_chi_tiet' AS sheet,
                                    (SELECT e FROM jsonb_array_elements(coalesce(x.ket_qua->'lop2'->'doi_chieu_hm', '[]'::jsonb)) e WHERE e->>'khoa' = %s LIMIT 1) AS dong
                             FROM m4.review_result x WHERE x.run_id = %s::uuid""", (khoa_dong, run))
        dong = (x or {}).get("dong") or {}
        yc = {"run_id": run, "khoa_dong": khoa_dong, "boq_id": boq, "ma_hm": ma_hm, "expected_basis": exp, "ly_do": ly_do}
        yc_j = json.dumps(yc, ensure_ascii=False)
        with self._khoa_phien(dt, khoa):
            with self._tx_review(dt) as c:
                c.execute("SELECT m4.review_kiem(%s::uuid, %s::uuid, %s::uuid)", (p["du_an_id"], p["dot_id"], p["tep_id"]))  # quyền hiện hành trước hết
                if p["hop_dong_id"]:  # FIX01 R5: HĐ TRƯỚC, rồi mới khóa/tra biên nhận — cùng thứ tự M17 (không vòng khóa HĐ↔biên nhận)
                    c.execute("SELECT 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s::uuid FOR UPDATE", (p["hop_dong_id"],))
                cu = self._r1(c, "SELECT m4.review_tra(%s, 'REVIEW_GHEP', %s::uuid, %s::uuid, %s::uuid, %s::jsonb) AS r",
                              (khoa, p["du_an_id"], p["dot_id"], p["tep_id"], yc_j))["r"]
                if cu is not None:
                    return {**cu, "lap_lai": True}
                co = self._co_so(c, du_an=p["du_an_id"], tep=p["tep_id"], dot=p["dot_id"], che_do=p["che_do"], o_dich=p["o_dich"])
                if self._sha_co_so(co) != exp:
                    raise DataError("M4_REVIEW_CO_SO_DOI", "Căn cứ đã đổi so với lúc xem — tải lại rồi ghép.")
                dich = self._dich_hieu_luc(co, ma_hm)  # FIX01 R6: đúng dòng nguồn engine dùng tại ngày NT (cùng snapshot, trước mọi hiệu lực)
                if str(dich["boq_id"]) != boq:
                    raise DataError("M4_REVIEW_DICH_KHONG_HIEU_LUC", f"Mã {ma_hm} đang hiệu lực theo {dich['nguon']} (BOQ khác đích đã chọn) — chọn lại đích.")
                r = self._r1(c, "SELECT m4.review_ghi_map(%s, %s::jsonb, %s::uuid, %s, %s::uuid, %s::integer, %s, %s, %s::integer, %s, %s) AS r",
                             (khoa, yc_j, run, khoa_dong, boq, dich["dong"], ma_hm, ly_do, dong.get("dong"), (dong.get("ten") or "")[:500] or None,
                              (x or {}).get("sheet")))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    @staticmethod
    def _dich_hieu_luc(co: dict, ma_hm: str) -> dict:
        """FIX01 R6 — đích ghép = dòng BOQ mà CHÍNH engine nguồn dùng: `csdl_hop_dong.phu_luc_ap_dung` + `boq_hieu_luc` trên projection của basis vừa
        chụp (cùng snapshot, ngày NT của đợt). Trả nguồn PG ổn định {boq_id, dong, phu_luc_id, thao_tac, nguon}. Không có/đã bị bỏ/chỉ ở PL dự thảo,
        tương lai, hủy → từ chối; không đọc lời mô tả PL, không điền 0, không dựng PL master khác."""
        cs = NR._m("csdl_hop_dong")
        ngay = str((co.get("dot") or {}).get("ngay_nghiem_thu") or "")[:10]
        if not co.get("hop_dong") or not ngay:
            raise DataError("M4_REVIEW_CAN_DOT", "Ghép tay cần lần chạy L1+L2 có đợt và ngày nghiệm thu.")
        con, bd = NR.projection_l2(co)
        try:
            pls = cs.phu_luc_ap_dung(con, bd["ma_hd"], ngay)
            hl, _bo = cs.boq_hieu_luc(con, bd["ma_hd"], pls=pls)
            d = hl.get(ma_hm)
            pl_pg = None
            if d is not None and d.get("nguon") != "HĐ gốc":
                p = next((p for p in reversed(pls) if p["so_pl"] == d["nguon"]), None)
                pl_pg = bd["phu_luc"].get(p["id"]) if p is not None else None
                if pl_pg is None:
                    raise DataError("M4_REVIEW_DICH_MO_HO", f"Không xác định được phụ lục nguồn của mã {ma_hm}.")
        finally:
            con.close()
        if d is None:
            raise DataError("M4_REVIEW_DICH_KHONG_HIEU_LUC", f"Mã {ma_hm} không có trong BOQ hiệu lực tại ngày NT {ngay} (chưa có, đã bỏ, hoặc chỉ ở phụ lục "
                                                            "dự thảo/chưa hiệu lực/đã hủy).")
        ung = [x for x in bd["nguon_boq"].get(ma_hm) or [] if (x["phu_luc_id"] is None if pl_pg is None else str(x["phu_luc_id"]) == str(pl_pg))]
        if len(ung) != 1:
            raise DataError("M4_REVIEW_DICH_MO_HO", f"Mã {ma_hm} có {len(ung)} dòng nguồn ở {d['nguon']} — không chọn được đích duy nhất.")
        return {**ung[0], "nguon": d["nguon"]}

    def review_ds(self, dang_nhap: str, *, hop_dong_id=None, dot_id=None, tep_id=None, che_do=None, o_dich=None) -> dict:
        """Lịch sử lần chạy + tệp hồ sơ đợt .xlsx có thể Review + ghép tay thấy được; nếu chọn tệp: chụp basis hiện hành (token dùng cho
        expected_basis) + căn cứ L2 thiếu/có — chụp trên kết nối chủ bảng SAU khi kiểm quyền/phạm vi chính xác."""
        dt = self.danh_tinh(dang_nhap)
        hd = _uuid(hop_dong_id, "hop_dong_id") if hop_dong_id not in (None, "") else None
        dot = _uuid(dot_id, "dot_id") if dot_id not in (None, "") else None
        tep = _uuid(tep_id, "tep_id") if tep_id not in (None, "") else None
        if che_do not in (None, "", *self.REVIEW_CHE_DO):
            raise DataError("M4_REVIEW_CHE_DO_SAI", "Chế độ Review là L1 hoặc L1_L2.")
        o = NR.kiem_o_dich(o_dich)
        with self._tx(dt):
            runs = self._nhieu("""SELECT r.id, r.hop_dong_id, r.dot_id, r.tep_id, t.ten_goc, r.raw_sha256, r.che_do, r.o_dich, r.trang_thai, r.basis_sha256,
                                         r.parent_run_id, r.quyen, r.tao_boi, r.tao_luc, r.xong_luc, r.ly_do, x.cong_bo, x.coverage
                                  FROM m4.review_run r LEFT JOIN m4.review_result x ON x.run_id = r.id LEFT JOIN m4.tep t ON t.id = r.tep_id
                                  WHERE (%s::uuid IS NULL OR r.hop_dong_id = %s::uuid) AND (%s::uuid IS NULL OR r.dot_id = %s::uuid)
                                  ORDER BY r.tao_luc DESC LIMIT 200""", (hd, hd, dot, dot))
            tep_ds = self._nhieu("""SELECT k.tep_id, k.muc, t.ten_goc, t.raw_sha256, t.byte_length FROM m4.dot_tep k JOIN m4.tep t ON t.id = k.tep_id
                                    WHERE k.dot_id = %s::uuid AND t.media_type = %s ORDER BY k.muc, t.ten_goc""", (dot, NR.MEDIA_XLSX)) if dot else []
            maps = self._nhieu("""SELECT id, khoa_hstt, revision, ma_hm, boq_id, boq_dong, run_id, dong_hs, ten_hs, ly_do, tao_boi, tao_luc
                                  FROM m4.review_manual_map WHERE hop_dong_id = %s::uuid ORDER BY khoa_hstt, revision DESC""", (hd,)) if hd else []
            t = self._mot("SELECT id, du_an_id FROM m4.tep WHERE id = %s::uuid", (tep,)) if tep else None
        co_so = None
        if tep:
            if t is None:
                raise DataError("M4_KHONG_THAY_TEP", "Không thấy tệp (hoặc ngoài phạm vi).")
            if self.conn_tin_cay is None:
                co_so = {"san_sang": False, "ly_do": "Đường tin cậy của máy chủ chưa cấu hình — chưa chạy Review được"}
            else:
                from ..m4 import review_compute as RC
                mode = che_do or ("L1_L2" if dot else "L1")
                with self._tx_review(dt, rr=True) as c:
                    q = self._r1(c, "SELECT m4.review_kiem(%s::uuid, %s::uuid, %s::uuid) AS q", (t["du_an_id"], dot, tep))["q"]
                    co = self._co_so(c, du_an=t["du_an_id"], tep=tep, dot=dot, che_do=mode, o_dich=o)
                co_so = {"san_sang": True, "basis_sha256": self._sha_co_so(co), "quyen": q, "che_do": mode, "o_dich": o, "du_an_id": t["du_an_id"],
                         "phu_thuoc": RC.phu_thuoc(co) if mode == "L1_L2" else {}, "so_ghep_tay": len(co.get("manual_map") or []),
                         "ngay_nghiem_thu": (co.get("dot") or {}).get("ngay_nghiem_thu"), "engine": NR.ENGINE_REVIEW}
        return {"runs": runs, "tep": tep_ds, "manual_map": maps, "co_so": co_so, "nguong_nguon": None}

    def review_chi_tiet(self, dang_nhap: str, run_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        run = _uuid(run_id, "run_id")
        with self._tx(dt):
            r = self._mot("""SELECT r.id, r.phap_nhan_id, r.du_an_id, r.hop_dong_id, r.dot_id, r.tep_id, t.ten_goc, r.raw_sha256, r.che_do, r.o_dich,
                                    r.basis_sha256, r.engine, r.engine_sha256, r.hanh_dong, r.quyen, r.trang_thai, r.parent_run_id, r.ly_do, r.tao_boi, r.tao_luc,
                                    r.xong_luc
                             FROM m4.review_run r LEFT JOIN m4.tep t ON t.id = r.tep_id WHERE r.id = %s::uuid""", (run,))
            if r is None:
                raise DataError("M4_REVIEW_KHONG_THAY", "Không thấy lần chạy Review (hoặc ngoài phạm vi hiện hành).")
            x = self._mot("""SELECT ket_qua, ket_qua_sha256, coverage, cong_bo, basis_cong_bo_sha256, tao_luc FROM m4.review_result WHERE run_id = %s::uuid""",
                          (run,))
            art = self._nhieu("SELECT id, loai, ten, raw_sha256, byte_length, tao_luc FROM m4.review_artifact WHERE run_id = %s::uuid ORDER BY loai", (run,))
            con = self._nhieu("SELECT id, trang_thai, tao_luc FROM m4.review_run WHERE parent_run_id = %s::uuid ORDER BY tao_luc", (run,))
            maps = self._nhieu("""SELECT id, khoa_hstt, revision, ma_hm, boq_id, boq_dong, run_id, dong_hs, ten_hs, ly_do, tao_boi, tao_luc
                                  FROM m4.review_manual_map WHERE hop_dong_id = %s::uuid ORDER BY khoa_hstt, revision DESC""",
                               (r["hop_dong_id"],)) if r["hop_dong_id"] else []
        return {"run": r, "ket_qua": x, "artifact": art, "con": con, "manual_map": maps}

    def review_tai(self, dang_nhap: str, run_id, artifact_id) -> tuple[str, str, bytes]:
        """Tải báo cáo/bằng chứng: quyền đọc HIỆN HÀNH (RLS m4.review_doc_duoc) kiểm TRƯỚC khi tra registry/đọc kho; hash + độ dài kiểm lại."""
        dt = self.danh_tinh(dang_nhap)
        run, aid = _uuid(run_id, "run_id"), _uuid(artifact_id, "artifact_id")
        with self._tx(dt):
            a = self._mot("SELECT id, loai, ten, raw_sha256, byte_length FROM m4.review_artifact WHERE id = %s::uuid AND run_id = %s::uuid", (aid, run))
        if a is None:
            raise DataError("M4_REVIEW_KHONG_THAY", "Không thấy tệp của lần chạy (hoặc ngoài phạm vi hiện hành).")
        p = self.root / "m4-review" / a["raw_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", a["raw_sha256"]) or not p.is_file():
            raise DataError("M4_TEP_KHONG_CO_TRONG_KHO", "Tệp Review không có trong kho lưu trữ.")
        raw = p.read_bytes()
        if sha256(raw) != a["raw_sha256"] or len(raw) != a["byte_length"]:
            raise DataError("M4_TEP_HONG_LUU_TRU", "Tệp Review trong kho khác hash đã ghi — không trả.")
        media = NR.MEDIA_XLSX if a["ten"].endswith(".xlsx") else ("application/json" if a["ten"].endswith(".json") else "text/plain; charset=utf-8")
        return a["ten"], media, raw

    # ================================================================== M4-02B Chứng từ L3 (M22 m4.chung_tu_*)
    # Cùng giao thức Review: (1) quyền hiện hành + giữ chỗ/biên nhận (FINAL cũ trước mọi việc tốn kém) → (2) MỘT snapshot RR chụp basis L3 đầy đủ
    # (đợt/nộp, TẤT CẢ tệp gắn đợt + H/độ dài/media, HĐ/tham số/PL/BOQ, L2 đã công bố, revision metadata + ghép tay L3, provider) + CAS expected/revision
    # → tạo run → (3) tiến trình con credential-free (review_compute, nhánh che_do='L3') trên bản làm việc tương đối dưới thư mục lần chạy → (4) công
    # bố dưới khóa HĐ + quyền hiện hành + chụp lại toàn basis (đổi → STALE). Không gọi tao_bo/hang_muc_tu_*/luu/xoa/dich_vu/QLV/server của nguồn.
    CHUNG_TU_LOAI = ("BB_NT", "BB_GN", "PL", "CO", "CQ", "BB_LD", "KHAC")
    CHUNG_TU_TRUONG_SUA = frozenset({"tep_id", "loai", "so", "ngay", "bo"})
    CHUNG_TU_AUTHORITY = frozenset({"actor", "nguoi", "phap_nhan_id", "phap_nhan", "du_an_id", "quyen", "vai", "trang_thai", "trang_thai_doc", "duyet",
                                    "approved", "path", "duong_dan", "url", "work_ref", "raw_sha256", "sha256", "byte_length", "object_key", "trich",
                                    "dong", "row_id", "media_type"})

    def _chung_tu_co_so(self, c, dot: str) -> dict:
        """Basis L3 ĐẦY ĐỦ chụp từ PG trong giao dịch của người gọi. HĐ/tham số/PL/BOQ/ghép tay L2 dùng lại đúng phần chụp của `_co_so` (chế độ L1_L2,
        không tệp) — rồi THÊM phần riêng L3; không coi `_co_so` gốc là đã đủ cho L3. Danh sách tệp/dòng không LIMIT."""
        d = self._r1(c, """SELECT d.id, d.hop_dong_id, d.du_an_id, d.so_dot, d.ngay_nghiem_thu, d.trang_thai, d.revision, n.id AS nop_id, n.digest AS nop_digest,
                                  n.revision_ho_so AS nop_revision_ho_so, n.revision_dot AS nop_revision_dot
                           FROM m4.dot d LEFT JOIN m4.nop n ON n.dot_id = d.id WHERE d.id = %s::uuid""", (dot,))
        if d is None:
            raise DataError("M4_CHUNG_TU_KHONG_THAY", "Không thấy đợt (hoặc ngoài phạm vi hiện hành).")
        hd_part = self._co_so(c, du_an=d["du_an_id"], tep=None, dot=dot, che_do="L1_L2", o_dich=None)
        pn = self._r1(c, "SELECT phap_nhan_id FROM master.du_an WHERE id = %s::uuid", (d["du_an_id"],))
        tai_lieu = self._rn(c, """SELECT k.tep_id, string_agg(k.muc, ',' ORDER BY k.muc) AS muc, t.ten_goc, t.media_type, t.byte_length, t.raw_sha256,
                                         t.vai_tro_tai_lieu
                                  FROM m4.dot_tep k JOIN m4.tep t ON t.id = k.tep_id WHERE k.dot_id = %s::uuid
                                  GROUP BY k.tep_id, t.ten_goc, t.media_type, t.byte_length, t.raw_sha256, t.vai_tro_tai_lieu
                                  ORDER BY min(k.muc), t.ten_goc, k.tep_id""", (dot,))
        l2 = self._chung_tu_l2(c, d)
        rev = self._r1(c, """SELECT revision, tai_lieu, run_id FROM m4.chung_tu_revision WHERE dot_id = %s::uuid ORDER BY revision DESC LIMIT 1""", (dot,))
        lich_su = self._rn(c, """SELECT revision, parent_revision, run_id, thay_doi, ly_do, tao_boi, tao_luc FROM m4.chung_tu_revision WHERE dot_id = %s::uuid
                                 ORDER BY revision""", (dot,))
        # FIX01 §2.5: quyết định ghép tay hiện hành theo row_id kèm ĐÚNG đích đã chọn (boq_id + dòng vật lý), raw/vị trí và revision metadata lúc ghép —
        # worker so với đích BOQ hiệu lực hiện hành trước khi áp (khác → CAN_XAC_NHAN_LAI, không âm thầm áp theo ma_hm)
        maps = self._rn(c, """SELECT DISTINCT ON (m.row_id) m.id, m.row_id, m.revision, m.ma_hm, m.boq_id, m.boq_dong, m.tep_id, m.raw_sha256, m.locator,
                                     m.revision_chung_tu, m.run_id
                              FROM m4.chung_tu_manual_map m WHERE m.dot_id = %s::uuid ORDER BY m.row_id, m.revision DESC""", (dot,))
        return {"phien_ban": "m4.chung_tu.basis/1", "che_do": "L3", "du_an_id": d["du_an_id"], "phap_nhan_id": (pn or {}).get("phap_nhan_id"),
                "engine_sha256": NR.ENGINE_L3_SHA, "dot": d, "tai_lieu": tai_lieu, "hop_dong": hd_part.get("hop_dong"), "tham_so": hd_part.get("tham_so") or [],
                "trich_xuat": hd_part.get("trich_xuat"), "xac_nhan": hd_part.get("xac_nhan"), "phu_luc": hd_part.get("phu_luc") or [],
                "boq": hd_part.get("boq") or [], "manual_map_l2": hd_part.get("manual_map") or [], "l2": l2,
                "revision": rev or {"revision": 0, "tai_lieu": {}, "run_id": None}, "revision_lich_su": lich_su, "manual_map_l3": maps,
                "provider": NR.L3_PROVIDER}

    # phần basis Review L1+L2 mà KL kỳ này/lũy kế của L2 phụ thuộc (tệp hồ sơ + raw, HĐ/tham số/trích/xác nhận, PL, BOQ hiện hành, ghép tay L2, engine,
    # ô đích, ngày NT/HĐ của đợt). KHÔNG gồm danh sách tệp gắn đợt/trạng thái nộp — gắn thêm chứng từ L3 không làm L2 cũ đi.
    L2_PHU_THUOC = ("tep", "hop_dong", "tham_so", "trich_xuat", "xac_nhan", "phu_luc", "boq", "manual_map", "engine_sha256", "o_dich", "che_do", "review_chep")

    @classmethod
    def _l2_phan_phu_thuoc(cls, co: dict) -> dict:
        d = co.get("dot") or {}
        return {**{k: co.get(k) for k in cls.L2_PHU_THUOC}, "dot": {"id": d.get("id"), "hop_dong_id": d.get("hop_dong_id"),
                                                                      "ngay_nghiem_thu": d.get("ngay_nghiem_thu")}}

    def _chung_tu_l2(self, c, d: dict) -> dict:
        """FIX01 §2.1 — L2 đã công bố MỚI NHẤT của đợt chỉ được cấp `CO` khi phần căn cứ L2 phụ thuộc (đúng tệp hồ sơ/raw, HĐ/tham số/PL/BOQ/ghép tay,
        engine, ngày NT) chụp lại NGAY trong snapshot này trùng phần tương ứng trong basis bất biến của lần chạy L2 đó. Không khớp → `CU` (tham chiếu run/
        hash + các phần khác + lý do): L3 không dùng lượng L2, giữ BOQ-only/INCOMPLETE và yêu cầu chạy lại L2. Lần chạy/kết quả L2 lịch sử không sửa."""
        dot = d["id"]
        r = self._r1(c, """SELECT r.id AS run_id, r.tep_id, r.o_dich, r.basis, r.basis_sha256, r.engine_sha256, r.trang_thai AS trang_thai_run,
                                  x.ket_qua_sha256, x.ket_qua->'lop2'->'doi_chieu_hm' AS doi_chieu_hm,
                                  coalesce((x.ket_qua->'lop2'->>'chay')::boolean, false) AS chay
                           FROM m4.review_run r JOIN m4.review_result x ON x.run_id = r.id
                           WHERE r.dot_id = %s::uuid AND r.che_do = 'L1_L2' AND r.trang_thai IN ('SUCCEEDED','PARTIAL') AND x.cong_bo
                           ORDER BY r.xong_luc DESC, r.id LIMIT 1""", (dot,))
        if not (r and r["chay"] and isinstance(r.get("doi_chieu_hm"), list) and r["doi_chieu_hm"]):
            return {"trang_thai": "CHUA_CO", "ly_do": "Đợt chưa có lần chạy L1+L2 đã công bố có bảng hạng mục — L3 dùng BOQ hiệu lực (lượng NULL)"}
        ref = {k: r[k] for k in ("run_id", "tep_id", "basis_sha256", "trang_thai_run", "ket_qua_sha256")}
        cu = r.get("basis") if isinstance(r.get("basis"), dict) else {}
        if r.get("engine_sha256") != NR.ENGINE_REVIEW_SHA:
            khac = ["engine_sha256"]
        else:
            hien = self._co_so(c, du_an=d["du_an_id"], tep=r["tep_id"], dot=dot, che_do="L1_L2", o_dich=r.get("o_dich"))
            a, b = self._l2_phan_phu_thuoc(cu), self._l2_phan_phu_thuoc(hien)
            khac = sorted(k for k in a if canonical_json(a[k]) != canonical_json(b[k]))
        if khac:
            return {"trang_thai": "CU", **ref, "khac": khac,
                    "ly_do": "Căn cứ L2 đã đổi so với lần chạy L2 đã công bố (" + ", ".join(khac) + ") — chạy lại Review L1+L2 cho đợt rồi Chạy lại L3"}
        return {"trang_thai": "CO", **ref, "doi_chieu_hm": r["doi_chieu_hm"]}

    @staticmethod
    def _chung_tu_phu_thuoc(co: dict) -> dict:
        """Căn cứ L3 có/không (hiện trước khi chạy; worker vẫn tính coverage thật)."""
        tl = co.get("tai_lieu") or []
        ngay = (co.get("dot") or {}).get("ngay_nghiem_thu")
        so = str((co.get("hop_dong") or {}).get("so_hop_dong") or "")
        native = sum(1 for t in tl if t["media_type"] in NR.L3_DOC_NATIVE)
        return {"NGAY_NT": {"ok": bool(ngay), "ly_do": "Đợt có ngày nghiệm thu" if ngay else "Đợt chưa có ngày nghiệm thu (C02/C07 và BOQ hiệu lực chưa kiểm được)"},
                "L2": {"ok": (co.get("l2") or {}).get("trang_thai") == "CO",
                       "ly_do": "Có kết quả L2 đã công bố (KL kỳ này/lũy kế)" if (co.get("l2") or {}).get("trang_thai") == "CO" else (co.get("l2") or {}).get("ly_do")},
                "BOQ": {"ok": any(b.get("trang_thai") == "DA_MAP" for b in co.get("boq") or []), "ly_do": "BOQ đọc/map đủ" if any(
                    b.get("trang_thai") == "DA_MAP" for b in co.get("boq") or []) else "Chưa có BOQ đọc/map đủ"},
                "SO_HD": {"ok": re.match(r"\s*0*(\d+)\s*/\s*(\d{4})", so) is not None, "ly_do": f"Số HĐ chuẩn '{so}'"},
                "TAI_LIEU": {"ok": native > 0, "ly_do": f"{len(tl)} tệp gắn đợt; {native} Word/Excel đọc native; {len(tl) - native} PDF/ảnh cần provider (chưa cấu hình)"}}

    @staticmethod
    def _json_l3(b: bytes):
        """FIX01 §6 — ket_qua.json của worker: JSON chuẩn (NaN/Infinity/-Infinity bị từ chối khi parse) và MỌI nút của cây là kiểu JSON hữu hạn (dict
        khóa chuỗi/list/str/bool/None/int/float hữu hạn), độ sâu ≤ 64. Sai → ValueError (máy chủ đóng FAILED có bằng chứng, không để lỗi thoát sau RUNNING)."""
        def cam(x):
            raise ValueError(f"Giá trị số không hữu hạn trong kết quả worker: {x}")
        o = json.loads(b.decode("utf-8"), parse_constant=cam)
        ngan = [(o, 0)]
        while ngan:
            x, sau = ngan.pop()
            if sau > 64:
                raise ValueError("Kết quả worker lồng quá sâu")
            if isinstance(x, dict):
                if any(not isinstance(k, str) for k in x):
                    raise ValueError("Khóa object không phải chuỗi")
                ngan.extend((v, sau + 1) for v in x.values())
            elif isinstance(x, list):
                ngan.extend((v, sau + 1) for v in x)
            elif isinstance(x, float):
                if x != x or x in (float("inf"), float("-inf")):
                    raise ValueError("Số không hữu hạn trong kết quả worker")
            elif not (x is None or isinstance(x, (str, bool, int))):
                raise ValueError(f"Kiểu không hợp lệ trong kết quả worker: {type(x).__name__}")
        return o

    def _chung_tu_hinh_dang_ok(self, kq: dict, co: dict, sha: str) -> bool:
        """Kết quả L3 thành công phải đúng chế độ/basis/engine, đủ coverage C01–C09 + phụ (trạng thái hợp lệ, tổng khớp), đúng bộ tệp của basis; mỗi tài
        liệu/dòng/hạng mục/ma trận/phát hiện/so sánh/cặp C06/ghi chú/ghép tay đúng hình dạng (FIX01 §6: kiểm cả cây, không chỉ khóa đỉnh)."""
        from ..m4 import chung_tu_adapter as CA
        cov = kq.get("coverage")
        if (kq.get("che_do") != "L3" or kq.get("basis_sha256") != sha or kq.get("engine_sha256") != NR.ENGINE_L3_SHA or not isinstance(cov, dict)
                or set(cov) != set(CA.MA_L3) | set(CA.MA_PHU)):
            return False
        if any(not isinstance(v, dict) or v.get("trang_thai") not in CA.THU_TU or not isinstance(v.get("ly_do"), (str, type(None))) for v in cov.values()):
            return False
        dung = "SUCCEEDED" if all(v["trang_thai"] in CA.DAT_DU for v in cov.values()) else "PARTIAL"
        if kq.get("trang_thai") != dung:
            return False
        la = lambda x, *k: isinstance(x, dict) and all(i in x for i in k)  # noqa: E731
        ds = lambda x, f: isinstance(x, list) and all(f(i) for i in x)  # noqa: E731
        ss_ok = lambda s: la(s, "trang_thai") and s["trang_thai"] in CA.SO_SANH  # noqa: E731
        tl = kq.get("tai_lieu")
        if not ds(tl, lambda d: la(d, "tep_id", "trang_thai_doc", "dong", "raw_sha256") and ds(d["dong"], lambda ln: la(ln, "row_id", "vi_tri_vat_ly")
                                                                                                         and re.fullmatch(r"[0-9a-f]{64}", str(ln["row_id"])))):
            return False
        theo_basis = {str(t["tep_id"]): t for t in co["tai_lieu"]}
        if sorted(str(d["tep_id"]) for d in tl) != sorted(theo_basis) or any(d["raw_sha256"] != theo_basis[str(d["tep_id"])]["raw_sha256"] for d in tl):
            return False
        so_sanh = kq.get("so_sanh")
        if not (ds(kq.get("hang_muc"), lambda h: la(h, "khoa")) and ds(kq.get("phat_hien"), lambda f: la(f, "id", "code", "level") and f["code"] in CA.MA_L3)
                and ds(kq.get("ma_tran"), lambda r: la(r, "khoa", "nt_docs", "gn_docs")) and isinstance(so_sanh, dict)
                and all(la(v, "C01", "C03") and ss_ok(v["C01"]) and ss_ok(v["C03"]) for v in so_sanh.values())
                and set(so_sanh) == {h["khoa"] for h in kq["hang_muc"]}
                and ds(kq.get("c06_cap"), lambda x: la(x, "gn_row_id", "doi_row_id", "loai", "so_luong", "lo", "ngay") and ss_ok(x["so_luong"]))
                and ds(kq.get("chu_thich_phat_hien"), lambda x: la(x, "id", "ghi_chu"))
                and la(kq.get("provenance"), "auto", "ghep_tay") and ds(kq["provenance"]["ghep_tay"], lambda x: la(x, "row_id", "trang_thai"))):
            return False
        return isinstance(kq.get("bao_cao"), list)

    def _chung_tu_tinh(self, run_id: str, co: dict, sha_co_so: str) -> tuple[dict, list, str | None]:
        """Cùng vòng đời `_review_tinh`: RUNNING đã commit → mọi bước dựng nằm trong nhánh kết thúc có bằng chứng; worker = `_chay_worker` (cùng env
        không credential/guard/timeout); chỉ exit 0 + đúng hình dạng mới được xét thành công. Bản làm việc từng tệp = bytes raw đã kiểm H/độ dài, ghi
        một lần dưới `tai_lieu/NNN/<tên gốc>` của thư mục lần chạy (đường dẫn tương đối trong vao.json)."""
        from ..m4.review_compute import MA_GUARD_KHONG_NAP
        thu_muc = self.root / "m4-chung-tu-run" / run_id
        co_b = canonical_json(co).encode("utf-8")
        vao_b, ly_do, log = None, None, b""
        try:
            thu_muc.mkdir(parents=True, exist_ok=False)
            tl_vao = []
            for i, t in enumerate(co["tai_lieu"], 1):
                raw = self._raw(t["raw_sha256"], t["byte_length"])
                ref = f"tai_lieu/{i:03d}/{NR.kiem_ten(t['ten_goc'])}"
                write_immutable(thu_muc / ref, raw)
                tl_vao.append({"tep_id": t["tep_id"], "work_ref": ref, "raw_sha256": t["raw_sha256"], "byte_length": t["byte_length"],
                               "media_type": t["media_type"], "ten_goc": t["ten_goc"], "muc": t["muc"]})
            vao = {"run_id": run_id, "che_do": "L3", "basis": co, "basis_sha256": sha_co_so, "tai_lieu": tl_vao, "revision": co["revision"]["revision"]}
            vao_b = canonical_json(vao).encode("utf-8")
            write_immutable(thu_muc / "vao.json", vao_b)
            write_immutable(thu_muc / "co_so.json", co_b)
        except Exception as exc:  # noqa: BLE001 — lỗi dựng thật là bằng chứng FAILED
            ma = getattr(exc, "code", None) or type(exc).__name__
            ly_do = f"SETUP_LOI: chưa khởi chạy tiến trình tính ({ma}: {str(exc)[:300]})"
            log = ly_do.encode("utf-8")
        if ly_do is None:
            try:
                p = self._chay_worker(thu_muc)
                log = (p.stdout or b"") + b"\n--- stderr ---\n" + (p.stderr or b"") + f"\n--- exit {p.returncode} ---\n".encode()
                if p.returncode == MA_GUARD_KHONG_NAP:
                    ly_do = "GUARD_KHONG_NAP: chế độ giữ tệp bật nhưng hook giữ tệp thật không cài trong tiến trình tính — dừng trước mọi I/O"
                elif p.returncode != 0:
                    ly_do = f"WORKER_EXIT_{p.returncode}: tiến trình tính kết thúc mã {p.returncode} — không nhận kết quả thành công"
            except subprocess.TimeoutExpired as exc:
                ly_do = f"TIMEOUT: tiến trình tính vượt {self.REVIEW_TOI_DA_GIAY}s — đã dừng tiến trình con; không phải kết quả đạt"
                log = (exc.stdout or b"") + b"\n--- stderr ---\n" + (exc.stderr or b"") + b"\n--- TIMEOUT ---\n"
            except OSError as exc:
                ly_do = f"Không khởi chạy được tiến trình tính ({type(exc).__name__})"
                log = ly_do.encode("utf-8")
        return self._chung_tu_gom(thu_muc, run_id, co, co_b, vao_b, sha_co_so, ly_do, log)

    def _chung_tu_gom(self, thu_muc: Path, run_id: str, co: dict, co_b: bytes, vao_b, sha_co_so: str, ly_do, log: bytes) -> tuple[dict, list, str | None]:
        """Gom kết quả + bằng chứng của MỘT lần chạy đã dừng (bình thường, lỗi, hoặc đối soát sau khi tiến trình máy chủ mất dấu lần chạy): đọc
        ket_qua.json (JSON hữu hạn, kiểm cả cây), giữ mọi bằng chứng; chỉ exit 0 + đúng hình dạng mới được xét thành công."""
        try:
            if thu_muc.is_dir():
                write_immutable(thu_muc / "worker.log", log or b"(trong)")
        except Exception:  # noqa: BLE001 — log đã có trong artifact LOG bên dưới (đối soát: worker.log cũ giữ nguyên)
            pass
        p_kq = thu_muc / "ket_qua.json"
        try:
            kq_b = p_kq.read_bytes() if p_kq.is_file() else None
        except OSError:
            kq_b = None
        kq = {"trang_thai": "FAILED"}
        if ly_do is None and kq_b is not None:
            try:
                kq = self._json_l3(kq_b)
            except (ValueError, UnicodeDecodeError) as exc:
                kq, ly_do = {"trang_thai": "FAILED"}, f"ket_qua.json không hợp lệ ({str(exc)[:200]})"
            if not isinstance(kq, dict):
                kq, ly_do = {"trang_thai": "FAILED"}, "ket_qua.json không phải object"
        else:
            ly_do = ly_do or "Tiến trình tính không tạo ket_qua.json"
        if kq.get("trang_thai") in ("SUCCEEDED", "PARTIAL"):
            try:
                ok = self._chung_tu_hinh_dang_ok(kq, co, sha_co_so)
            except Exception:  # noqa: BLE001 — hình dạng lạ làm chính bước kiểm lỗi → coi là sai hình dạng, không để thoát sau RUNNING
                ok = False
            if not ok:
                kq, ly_do = {"trang_thai": "FAILED", "loi": "Kết quả L3 sai basis/phạm vi/hình dạng"}, "Kết quả L3 sai basis/phạm vi/hình dạng (coverage/tệp/trạng thái/cây)"
        if ly_do:
            kq = {**kq, "trang_thai": "FAILED", "loi": kq.get("loi") or ly_do}
        art = []

        def luu(raw_b, loai, ten):
            nonlocal kq, ly_do
            try:
                raw_x = raw_b() if callable(raw_b) else raw_b
                sha = sha256(raw_x)
                write_immutable(self.root / "m4-chung-tu" / sha, raw_x)
                art.append({"loai": loai, "ten": ten[:200], "raw_sha256": sha, "byte_length": len(raw_x)})
            except Exception as exc:  # noqa: BLE001
                if loai == "REPORT_L3" and kq.get("trang_thai") in ("SUCCEEDED", "PARTIAL"):
                    ly_do = f"Không lưu được báo cáo L3 ({type(exc).__name__}) — không công bố kết quả thiếu báo cáo"
                    kq = {**kq, "trang_thai": "FAILED", "loi": ly_do}
        luu(co_b, "BASIS", f"chung-tu-{run_id[:8]}-co_so.json")
        if vao_b is not None:
            luu(vao_b, "INPUT", f"chung-tu-{run_id[:8]}-vao.json")
        luu(log or b"(trong)", "LOG", f"chung-tu-{run_id[:8]}-worker.log")
        if kq_b:
            luu(kq_b, "RESULT", f"chung-tu-{run_id[:8]}-ket_qua.json")
        if kq["trang_thai"] in ("SUCCEEDED", "PARTIAL"):
            b = next((x for x in kq.get("bao_cao") or [] if x.get("loai") == "REPORT_L3" and x.get("tep") == "chung_tu_l3.xlsx"), None)
            f = thu_muc / "chung_tu_l3.xlsx"
            if b is None or not f.is_file():
                ly_do = "Thiếu báo cáo L3 — không công bố kết quả thiếu báo cáo"
                kq = {**kq, "trang_thai": "FAILED", "loi": ly_do}
            else:
                luu(f.read_bytes, "REPORT_L3", f"chung-tu-{run_id[:8]}-chung_tu_l3.xlsx")
        return kq, art, ly_do

    # FIX01 §6 — lần chạy L3 ĐANG TÍNH trong tiến trình máy chủ này (dùng chung mọi instance service): đối soát chỉ chạm lần chạy RUNNING không còn chủ
    _CT_DANG_TINH: set = set()
    _CT_KHOA = threading.Lock()

    @staticmethod
    def _loi_ket_noi(exc, c) -> bool:
        """Lỗi mức kết nối/commit (OperationalError/InterfaceError hoặc kết nối đã hỏng): CSDL có thể ĐÃ hoặc CHƯA commit — kết quả chưa rõ."""
        import psycopg
        return isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError)) or bool(getattr(c, "closed", False) or getattr(c, "broken", False))

    # mã lỗi quyền/phạm vi hiện hành (RAISE 'MA: …' của hàm CSDL) — lỗi RÕ, không phải UNKNOWN
    _MA_QUYEN_PHAM_VI = ("M4_KHONG_CO_QUYEN_DU_AN", "M4_CHUNG_TU_PHAM_VI", "M4_CHUNG_TU_KHONG_THAY", "M4_DANH_TINH")

    @staticmethod
    def _ma_loi_pg(exc) -> str:
        return ((getattr(getattr(exc, "diag", None), "message_primary", "") or "").split(":", 1)[0]).strip()

    def _chung_tu_cong_bo(self, dt, run_id: str, kq: dict, art: list, ly_do, *, dot: str, _lan: int = 0) -> dict:
        """(4) Công bố dưới khóa HĐ FOR SHARE + quyền hiện hành + chụp lại toàn basis (đổi → STALE). FIX01 §6: chuẩn hóa/hash kết quả lỗi → đóng FAILED có
        bằng chứng (không để ValueError thoát sau RUNNING); lỗi CSDL thường → thử ĐÚNG MỘT lần đóng FAILED; lỗi kết nối/commit chưa rõ → M4_KET_QUA_CHUA_RO
        (KHÔNG cam kết FAILED vì commit thật chưa biết) — gửi lại cùng khóa sẽ đối soát biên nhận/lần chạy trước khi làm gì tiếp.
        M4-L3 S1: UNKNOWN phát sinh ở lần đóng FAILED dự phòng (giao dịch/commit) được giữ nguyên ra ngoài, không bị lỗi SQL lần đầu che."""
        import psycopg
        try:
            kq_j = canonical_json(kq)
            cov_j = json.dumps(kq.get("coverage") or {}, ensure_ascii=False, allow_nan=False)
        except (ValueError, TypeError) as exc:
            ly_do = f"Kết quả không chuẩn hóa được ({type(exc).__name__}: {str(exc)[:200]}) — đóng FAILED, giữ bằng chứng"
            kq = {"trang_thai": "FAILED", "loi": ly_do}
            kq_j, cov_j = canonical_json(kq), "{}"
        tt = kq["trang_thai"] if kq.get("trang_thai") in ("SUCCEEDED", "PARTIAL") else "FAILED"
        kq_sha = sha256(kq_j.encode("utf-8"))
        art_j = json.dumps(art, ensure_ascii=False)
        c = self.conn_tin_cay
        try:
            with self._tx_review(dt) as c:
                c.execute("""SELECT 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = (SELECT hop_dong_id FROM m4.dot WHERE id = %s::uuid) FOR SHARE""", (dot,))
                c.execute("SELECT m4.chung_tu_kiem(%s::uuid)", (dot,))
                sha_nay = self._sha_co_so(self._chung_tu_co_so(c, dot))
                r = self._r1(c, "SELECT m4.chung_tu_cong_bo(%s::uuid, %s::jsonb, %s, %s::jsonb, %s, %s, %s::jsonb, %s) AS r",
                             (run_id, kq_j, kq_sha, cov_j, tt, sha_nay, art_j, ly_do))["r"]
        except psycopg.Error as exc:
            if self._loi_ket_noi(exc, c):
                raise DataError("M4_KET_QUA_CHUA_RO", f"Mất kết nối CSDL khi công bố lần chạy {run_id} — chưa rõ đã ghi hay chưa; bằng chứng giữ nguyên. "
                                                      "Gửi lại ĐÚNG yêu cầu (cùng khóa) để đối soát; không tạo khóa mới.") from None
            ma = self._ma_loi_pg(exc)
            if ma in self._MA_QUYEN_PHAM_VI:
                with self._tx_review(dt) as c:
                    c.execute("SELECT m4.chung_tu_huy(%s::uuid, %s, %s::jsonb, %s::jsonb)",
                              (run_id, f"Quyền/phạm vi hiện hành đổi trước khi công bố ({ma}) — giữ bằng chứng, không công bố kết quả", kq_j, art_j))
                raise
            if tt != "FAILED" and _lan == 0:
                try:
                    return self._chung_tu_cong_bo(dt, run_id, {"trang_thai": "FAILED", "loi": f"Công bố lỗi ({ma or type(exc).__name__})"}, art,
                                                  f"Công bố kết quả lỗi ({ma or type(exc).__name__}) — đóng FAILED, giữ bằng chứng", dot=dot, _lan=1)
                except DataError as exc2:
                    # M4-L3 S1: commit của lần đóng FAILED dự phòng CHƯA RÕ (mất kết nối/ACK ở giao dịch hoặc commit) → giữ nguyên UNKNOWN, KHÔNG che
                    # bằng lỗi SQL của lần công bố đầu (lỗi đó ngụ ý chưa ghi gì — sai khi fallback có thể đã commit). Không khóa/run/compute mới;
                    # gửi lại cùng khóa sẽ đối soát (FINAL đã ghi → trả lại; RUNNING mồ côi → _chung_tu_doi_soat).
                    if exc2.code == "M4_KET_QUA_CHUA_RO":
                        raise
                except psycopg.Error as exc2:
                    # quyền/phạm vi hiện hành đổi ngay ở lần dự phòng: lần gọi lồng đã hủy (CANCELLED, giữ bằng chứng) → báo lỗi quyền rõ đó
                    if self._ma_loi_pg(exc2) in self._MA_QUYEN_PHAM_VI:
                        raise
                    if self._loi_ket_noi(exc2, self.conn_tin_cay):  # (vd mất kết nối khi ghi hủy) → commit chưa rõ, không khẳng định lỗi cuối
                        raise DataError("M4_KET_QUA_CHUA_RO", f"Mất kết nối CSDL khi đóng lần chạy {run_id} — chưa rõ đã ghi hay chưa; bằng chứng giữ "
                                                              "nguyên. Gửi lại ĐÚNG yêu cầu (cùng khóa) để đối soát; không tạo khóa mới.") from None
            raise
        except DataError:
            raise
        except Exception as exc:  # noqa: BLE001 — lỗi ngoài CSDL khi dựng basis/công bố: thử ĐÚNG MỘT lần đóng FAILED có bằng chứng
            if _lan == 0:
                return self._chung_tu_cong_bo(dt, run_id, {"trang_thai": "FAILED", "loi": f"Công bố lỗi ({type(exc).__name__})"}, art,
                                              f"Công bố lỗi ngoài CSDL ({type(exc).__name__}: {str(exc)[:200]}) — đóng FAILED, giữ bằng chứng", dot=dot, _lan=1)
            raise
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    def _chung_tu_doi_soat(self, dt, run_id: str, *, dot: str) -> dict:
        """FIX01 §6 — gửi lại cùng khóa gặp lần chạy RUNNING mà tiến trình máy chủ này KHÔNG còn tính (mất kết nối khi công bố, máy chủ khởi động lại):
        đối soát bằng chứng trong thư mục lần chạy (worker.log có dòng exit → gom kết quả như lúc dừng; không có → FAILED 'DOI_SOAT'), rồi công bố qua
        đúng hàm CSDL (quyền hiện hành + chụp lại basis → STALE nếu đổi). Không tính lại, không khóa mới, không sửa lịch sử."""
        with self._tx_review(dt) as c:
            r = self._r1(c, "SELECT basis, basis_sha256 FROM m4.chung_tu_run WHERE id = %s::uuid", (run_id,))
        co, sha = r["basis"], r["basis_sha256"]
        thu_muc = self.root / "m4-chung-tu-run" / run_id
        co_b = canonical_json(co).encode("utf-8")
        try:
            vao_b = (thu_muc / "vao.json").read_bytes() if (thu_muc / "vao.json").is_file() else None
            log = (thu_muc / "worker.log").read_bytes() if (thu_muc / "worker.log").is_file() else None
        except OSError:
            vao_b, log = None, None
        m = re.search(rb"--- exit (-?\d+) ---\s*$", log or b"")
        if log is None:
            ly_do = "DOI_SOAT: tiến trình tính không còn chạy và không có nhật ký kết thúc — đóng FAILED, giữ bằng chứng (không tính lại)"
            log = ly_do.encode("utf-8")
        elif m is None or int(m.group(1)) != 0:
            ly_do = f"DOI_SOAT: lần chạy kết thúc không thành công ({m.group(0).decode().strip() if m else 'nhật ký không có mã exit'})"
        else:
            ly_do = None
        kq, art, ly_do = self._chung_tu_gom(thu_muc, run_id, co, co_b, vao_b, sha, ly_do, log)
        return self._chung_tu_cong_bo(dt, run_id, kq, art, ly_do, dot=dot)

    @contextmanager
    def _chua_ro(self):
        """Lệnh L3 gặp lỗi kết nối/commit chưa rõ → M4_KET_QUA_CHUA_RO (503): trình duyệt giữ khóa + body, gửi lại để CSDL đối soát biên nhận/lần chạy."""
        import psycopg
        try:
            yield
        except psycopg.Error as exc:
            if self._loi_ket_noi(exc, self.conn_tin_cay):
                raise DataError("M4_KET_QUA_CHUA_RO", "Mất kết nối CSDL giữa chừng — chưa rõ đã ghi hay chưa. Gửi lại ĐÚNG yêu cầu (cùng khóa) để đối soát.") from None
            raise

    def _chung_tu_khoi(self, dt, hanh: str, khoa: str, yc: dict, *, dot: str, revision: int, exp: str, parent=None) -> dict:
        with self._chua_ro():
            return self._chung_tu_khoi_(dt, hanh, khoa, yc, dot=dot, revision=revision, exp=exp, parent=parent)

    def _chung_tu_khoi_(self, dt, hanh: str, khoa: str, yc: dict, *, dot: str, revision: int, exp: str, parent=None) -> dict:
        yc_j = json.dumps(yc, ensure_ascii=False)
        with self._khoa_phien(dt, khoa):  # cùng namespace phiên với Review: trùng (actor, khóa) giữa L3 và Review tuần tự hóa
            with self._tx_review(dt) as c:  # (1) RC ngắn: quyền → khóa biên nhận → FINAL cũ (đúng body, TRƯỚC kiểm basis/revision) hoặc xung đột → giữ chỗ
                g = self._r1(c, "SELECT m4.chung_tu_giu(%s, %s, %s::uuid, %s::jsonb) AS r", (khoa, hanh, dot, yc_j))["r"]
            if g["lap_lai"]:
                return {**g["ket_qua"], "lap_lai": True}
            with self._tx_review(dt, rr=True) as c:  # (2) một snapshot RR: quyền → basis → CAS expected + revision → tạo run
                c.execute("SELECT m4.chung_tu_kiem(%s::uuid)", (dot,))
                co = self._chung_tu_co_so(c, dot)
                sha = self._sha_co_so(co)
                cu = self._r1(c, "SELECT id, trang_thai FROM m4.chung_tu_run WHERE tao_boi_id = %s::uuid AND khoa = %s", (dt["id"], khoa))
                if sha != exp and cu is None:  # cùng khóa đã có lần chạy → đối soát lần chạy đó, không đòi basis cũ còn nguyên
                    raise DataError("M4_CHUNG_TU_CO_SO_DOI", "Căn cứ (tệp/metadata/ghép tay/HĐ/BOQ/L2) đã đổi so với lúc xem — tải lại rồi chạy.")
                r = self._r1(c, """SELECT m4.chung_tu_tao_run(%s, %s, %s::jsonb, %s, %s::uuid, %s::integer, %s::jsonb, %s, %s, %s, %s::uuid) AS r""",
                             (khoa, hanh, yc_j, sha256(canonical_json({"hanh": hanh, "yc": yc}).encode("utf-8")), dot, revision, canonical_json(co), sha,
                              NR.ENGINE_L3, NR.ENGINE_L3_SHA, parent))["r"]
            if r["lap_lai"]:
                rid = str(r["ket_qua"]["run_id"])
                if r.get("dang_chay"):
                    with self._CT_KHOA:
                        dang = rid in self._CT_DANG_TINH
                    if not dang:  # RUNNING mồ côi: đối soát bằng chứng rồi đóng trạng thái cuối — retry không bao giờ kẹt 'đang chạy' vĩnh viễn
                        return {**self._chung_tu_doi_soat(dt, rid, dot=dot), "doi_soat": True}
                return {**r["ket_qua"], "lap_lai": True, "dang_chay": bool(r.get("dang_chay"))}
            run_id = str(r["ket_qua"]["run_id"])
            with self._CT_KHOA:
                self._CT_DANG_TINH.add(run_id)
            try:
                try:  # (3) không giao dịch/khóa CSDL nghiệp vụ trong lúc tính; mọi lỗi sau RUNNING → FAILED có bằng chứng
                    kq, art, ly_do = self._chung_tu_tinh(run_id, co, sha)
                except Exception as exc:  # noqa: BLE001
                    ly_do = f"LOI_KHONG_LUONG_TRUOC: {type(exc).__name__}: {str(exc)[:300]}"
                    kq, art = {"trang_thai": "FAILED", "loi": ly_do}, []
                return self._chung_tu_cong_bo(dt, run_id, kq, art, ly_do, dot=dot)  # (4)
            finally:
                with self._CT_KHOA:
                    self._CT_DANG_TINH.discard(run_id)

    @staticmethod
    def _rev_l3(v) -> int:
        return _so_nguyen(v, "revision", 0)

    def _ct_run_thay(self, dt, run: str) -> dict:
        """Lần chạy L3 THẤY ĐƯỢC theo quyền hiện hành (RLS m4.chung_tu_doc_duoc trên login ứng dụng) — kiểm TRƯỚC mọi tra biên nhận/đọc kết quả."""
        with self._tx(dt):
            r = self._mot("SELECT id, du_an_id, hop_dong_id, dot_id, revision, trang_thai, basis_sha256 FROM m4.chung_tu_run WHERE id = %s::uuid", (run,))
        if r is None:
            raise DataError("M4_CHUNG_TU_KHONG_THAY", "Không thấy lần chạy chứng từ L3 (hoặc ngoài phạm vi hiện hành).")
        return r

    def chung_tu_ds(self, dang_nhap: str, *, dot_id) -> dict:
        """Bộ chứng từ của MỘT đợt: đọc qua RLS (người xem/review chỉ thấy đúng phạm vi) TRƯỚC mọi đếm/tệp; basis hiện hành chụp trên kết nối chủ bảng
        SAU khi kiểm quyền chạy (SOAN/REVIEW) — vai chỉ xem không có basis/nút chạy."""
        dt = self.danh_tinh(dang_nhap)
        dot = _uuid(dot_id, "dot_id")
        with self._tx(dt):
            d = self._mot("""SELECT d.id, d.hop_dong_id, d.du_an_id, d.so_dot, d.ngay_nghiem_thu, d.trang_thai, d.revision, hd.so_hop_dong,
                                    m4.chung_tu_doc_dot(d.id) AS doc
                             FROM m4.dot d JOIN master.hop_dong hd ON hd.id = d.hop_dong_id WHERE d.id = %s::uuid""", (dot,))
            if d is None or not d.pop("doc"):
                raise DataError("M4_CHUNG_TU_KHONG_THAY", "Không thấy đợt (hoặc ngoài phạm vi hiện hành).")
            quyen = self._mot("SELECT m4.chung_tu_quyen(%s::uuid) AS q", (dot,))["q"]
            tai_lieu = self._nhieu("""SELECT k.tep_id, string_agg(k.muc, ',' ORDER BY k.muc) AS muc, t.ten_goc, t.media_type, t.byte_length, t.raw_sha256
                                      FROM m4.dot_tep k JOIN m4.tep t ON t.id = k.tep_id WHERE k.dot_id = %s::uuid
                                      GROUP BY k.tep_id, t.ten_goc, t.media_type, t.byte_length, t.raw_sha256 ORDER BY min(k.muc), t.ten_goc, k.tep_id""", (dot,))
            runs = self._nhieu("""SELECT r.id, r.revision, r.trang_thai, r.basis_sha256, r.parent_run_id, r.quyen, r.tao_boi, r.tao_luc, r.xong_luc, r.ly_do,
                                         x.cong_bo, x.coverage, x.ket_qua->'dem' AS dem
                                  FROM m4.chung_tu_run r LEFT JOIN m4.chung_tu_result x ON x.run_id = r.id WHERE r.dot_id = %s::uuid
                                  ORDER BY r.tao_luc DESC LIMIT 200""", (dot,))
            revs = self._nhieu("""SELECT revision, parent_revision, run_id, tai_lieu, thay_doi, ly_do, tao_boi, tao_luc FROM m4.chung_tu_revision
                                  WHERE dot_id = %s::uuid ORDER BY revision DESC""", (dot,))
            maps = self._nhieu("""SELECT id, row_id, revision, ma_hm, boq_id, boq_dong, run_id, tep_id, locator, ten_dong, revision_chung_tu, ly_do, tao_boi, tao_luc
                                  FROM m4.chung_tu_manual_map WHERE dot_id = %s::uuid ORDER BY row_id, revision DESC""", (dot,))
        for t in tai_lieu:
            t["doc"] = "NATIVE" if t["media_type"] in NR.L3_DOC_NATIVE else "PROVIDER"
        co_so = None
        if quyen is None:
            co_so = {"san_sang": False, "quyen": None, "ly_do": "Vai hiện hành chỉ xem — chạy/sửa chứng từ cần quyền soạn đúng dự án, hoặc review trên đợt đã nộp"}
        elif self.conn_tin_cay is None:
            co_so = {"san_sang": False, "quyen": quyen, "ly_do": "Đường tin cậy của máy chủ chưa cấu hình — chưa chạy chứng từ L3 được"}
        else:
            with self._tx_review(dt, rr=True) as c:
                q = self._r1(c, "SELECT m4.chung_tu_kiem(%s::uuid) AS q", (dot,))["q"]
                co = self._chung_tu_co_so(c, dot)
            co_so = {"san_sang": True, "basis_sha256": self._sha_co_so(co), "quyen": q, "revision": co["revision"]["revision"],
                     "phu_thuoc": self._chung_tu_phu_thuoc(co), "so_ghep_tay": len(co["manual_map_l3"]), "engine": NR.ENGINE_L3}
        try:
            loai = dict(NR._m("may_chu.chung_tu").LOAI)
        except DataError as exc:
            loai = {k: k for k in self.CHUNG_TU_LOAI}
            if co_so and co_so.get("san_sang"):
                co_so = {**co_so, "san_sang": False, "ly_do": f"Lõi chứng từ nguồn chưa nạp/sai pin ({exc.code}) — chưa chạy được"}
        return {"dot": d, "revision": revs[0]["revision"] if revs else 0, "tai_lieu": tai_lieu, "runs": runs, "revisions": revs, "manual_map": maps,
                "co_so": co_so, "loai": loai, "provider": NR.L3_PROVIDER}

    def chung_tu_chi_tiet(self, dang_nhap: str, run_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        run = _uuid(run_id, "run_id")
        with self._tx(dt):
            r = self._mot("""SELECT r.id, r.phap_nhan_id, r.du_an_id, r.hop_dong_id, r.dot_id, r.revision, r.basis_sha256, r.engine, r.engine_sha256, r.hanh_dong,
                                    r.quyen, r.trang_thai, r.parent_run_id, r.ly_do, r.tao_boi, r.tao_luc, r.xong_luc
                             FROM m4.chung_tu_run r WHERE r.id = %s::uuid""", (run,))
            if r is None:
                raise DataError("M4_CHUNG_TU_KHONG_THAY", "Không thấy lần chạy chứng từ L3 (hoặc ngoài phạm vi hiện hành).")
            x = self._mot("SELECT ket_qua, ket_qua_sha256, coverage, cong_bo, basis_cong_bo_sha256, tao_luc FROM m4.chung_tu_result WHERE run_id = %s::uuid", (run,))
            art = self._nhieu("SELECT id, loai, ten, raw_sha256, byte_length, tao_luc FROM m4.chung_tu_artifact WHERE run_id = %s::uuid ORDER BY loai", (run,))
            con = self._nhieu("SELECT id, trang_thai, tao_luc FROM m4.chung_tu_run WHERE parent_run_id = %s::uuid ORDER BY tao_luc", (run,))
            maps = self._nhieu("""SELECT id, row_id, revision, ma_hm, boq_id, boq_dong, run_id, tep_id, locator, ten_dong, revision_chung_tu, ly_do, tao_boi, tao_luc
                                  FROM m4.chung_tu_manual_map WHERE dot_id = %s::uuid ORDER BY row_id, revision DESC""", (r["dot_id"],))
            revs = self._nhieu("""SELECT revision, parent_revision, run_id, thay_doi, ly_do, tao_boi, tao_luc FROM m4.chung_tu_revision WHERE dot_id = %s::uuid
                                  ORDER BY revision DESC""", (r["dot_id"],))
        return {"run": r, "ket_qua": x, "artifact": art, "con": con, "manual_map": maps, "revisions": revs}

    def chung_tu_tai(self, dang_nhap: str, run_id, artifact_id) -> tuple[str, str, bytes]:
        """Tải báo cáo/bằng chứng L3: quyền đọc HIỆN HÀNH (RLS) TRƯỚC registry/kho; hash + độ dài kiểm lại."""
        dt = self.danh_tinh(dang_nhap)
        run, aid = _uuid(run_id, "run_id"), _uuid(artifact_id, "artifact_id")
        with self._tx(dt):
            a = self._mot("SELECT id, loai, ten, raw_sha256, byte_length FROM m4.chung_tu_artifact WHERE id = %s::uuid AND run_id = %s::uuid", (aid, run))
        if a is None:
            raise DataError("M4_CHUNG_TU_KHONG_THAY", "Không thấy tệp của lần chạy (hoặc ngoài phạm vi hiện hành).")
        p = self.root / "m4-chung-tu" / a["raw_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", a["raw_sha256"]) or not p.is_file():
            raise DataError("M4_TEP_KHONG_CO_TRONG_KHO", "Tệp chứng từ L3 không có trong kho lưu trữ.")
        raw = p.read_bytes()
        if sha256(raw) != a["raw_sha256"] or len(raw) != a["byte_length"]:
            raise DataError("M4_TEP_HONG_LUU_TRU", "Tệp chứng từ L3 trong kho khác hash đã ghi — không trả.")
        media = NR.MEDIA_XLSX if a["ten"].endswith(".xlsx") else ("application/json" if a["ten"].endswith(".json") else "text/plain; charset=utf-8")
        return a["ten"], media, raw

    def chung_tu_chay(self, dang_nhap: str, *, dot_id, revision, expected_basis, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        dot = _uuid(dot_id, "dot_id")
        rev = self._rev_l3(revision)
        exp, khoa = self._hex(expected_basis, "expected_basis"), self._khoa(khoa)
        yc = {"dot_id": dot, "revision": rev, "expected_basis": exp}
        return self._chung_tu_khoi(dt, "CHUNG_TU_CHAY", khoa, yc, dot=dot, revision=rev, exp=exp)

    def chung_tu_chay_lai(self, dang_nhap: str, *, run_id, revision, expected_basis, khoa) -> dict:
        """Chạy lại → lần chạy CON trên bộ raw hiện hành của đúng đợt + revision metadata được chọn; lần chạy/kết quả/báo cáo cha giữ nguyên.
        Đúng body/khóa → FINAL cũ trả TRƯỚC kiểm basis/revision."""
        dt = self.danh_tinh(dang_nhap)
        run = _uuid(run_id, "run_id")
        rev = self._rev_l3(revision)
        exp, khoa = self._hex(expected_basis, "expected_basis"), self._khoa(khoa)
        p = self._ct_run_thay(dt, run)
        yc = {"run_id": run, "revision": rev, "expected_basis": exp}
        return self._chung_tu_khoi(dt, "CHUNG_TU_CHAY_LAI", khoa, yc, dot=p["dot_id"], revision=rev, exp=exp, parent=run)

    def _chung_tu_chuan_sua(self, tai_lieu) -> list:
        if not isinstance(tai_lieu, list) or not 1 <= len(tai_lieu) <= 500:
            raise DataError("M4_THAM_SO_SAI", "Danh sách sửa chứng từ phải có 1–500 mục.")
        out, thay = [], set()
        for x in tai_lieu:
            if isinstance(x, dict) and set(x) & self.CHUNG_TU_AUTHORITY:  # dữ kiện máy/authority lồng trong mục sửa: 403 như cấp đỉnh, không nới allowlist
                raise DataError("M4_CLIENT_AUTHORITY", "Mục sửa chứng từ không được mang danh tính/hash/đường dẫn/kết quả trích/trạng thái — máy chủ xác định.")
            if not isinstance(x, dict) or set(x) - self.CHUNG_TU_TRUONG_SUA or "tep_id" not in x or len(x) < 2:
                raise DataError("M4_THAM_SO_SAI", "Mỗi mục sửa gồm tep_id và ít nhất một trong loai/so/ngay/bo.")
            t = _uuid(x["tep_id"], "tep_id")
            if t in thay:
                raise DataError("M4_THAM_SO_SAI", "Một tệp chỉ một mục sửa trong cùng yêu cầu.")
            thay.add(t)
            m = {"tep_id": t}
            if "loai" in x:
                if x["loai"] not in self.CHUNG_TU_LOAI:
                    raise DataError("M4_THAM_SO_SAI", "Loại chứng từ không hợp lệ.")
                m["loai"] = x["loai"]
            if "so" in x:
                m["so"] = (_chuoi(x["so"], "số chứng từ", 100, bat_buoc=False) or "").strip()
            if "ngay" in x:
                m["ngay"] = _ngay(x["ngay"], "ngày chứng từ")
            if "bo" in x:
                if not isinstance(x["bo"], bool):
                    raise DataError("M4_THAM_SO_SAI", "Trường bo phải là true/false.")
                m["bo"] = x["bo"]
            out.append(m)
        return out

    def chung_tu_sua(self, dang_nhap: str, *, run_id, revision, tai_lieu, expected_basis, ly_do, khoa) -> dict:
        """Sửa loại/số/ngày hoặc bỏ/khôi phục tệp khỏi bộ → revision metadata MỚI (không sửa raw/trích/kết quả cũ); người dùng bấm Chạy lại."""
        dt = self.danh_tinh(dang_nhap)
        run = _uuid(run_id, "run_id")
        rev = self._rev_l3(revision)
        tl = self._chung_tu_chuan_sua(tai_lieu)
        ly = _chuoi(ly_do, "lý do sửa", 1000)
        exp, khoa = self._hex(expected_basis, "expected_basis"), self._khoa(khoa)
        p = self._ct_run_thay(dt, run)
        yc = {"run_id": run, "revision": rev, "tai_lieu": tl, "expected_basis": exp, "ly_do": ly}
        yc_j = json.dumps(yc, ensure_ascii=False)
        with self._chua_ro(), self._khoa_phien(dt, khoa):
            with self._tx_review(dt) as c:
                c.execute("SELECT m4.chung_tu_kiem(%s::uuid)", (p["dot_id"],))  # quyền hiện hành trước hết
                c.execute("SELECT 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s::uuid FOR UPDATE", (p["hop_dong_id"],))  # HĐ TRƯỚC khóa biên nhận
                cu = self._r1(c, "SELECT m4.chung_tu_tra(%s, 'CHUNG_TU_SUA', %s::uuid, %s::jsonb) AS r", (khoa, p["dot_id"], yc_j))["r"]
                if cu is not None:
                    return {**cu, "lap_lai": True}
                if self._sha_co_so(self._chung_tu_co_so(c, p["dot_id"])) != exp:
                    raise DataError("M4_CHUNG_TU_CO_SO_DOI", "Căn cứ đã đổi so với lúc xem — tải lại rồi sửa.")
                r = self._r1(c, "SELECT m4.chung_tu_ghi_revision(%s, %s::jsonb, %s::uuid, %s::integer, %s::jsonb, %s) AS r",
                             (khoa, yc_j, run, rev, json.dumps(tl, ensure_ascii=False), ly))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    def chung_tu_ghep(self, dang_nhap: str, *, run_id, row_id, boq_id, boq_dong, ma_hm, revision, expected_basis, ly_do, khoa) -> dict:
        """Ghép tay dòng chứng từ (row_id do máy chủ cấp từ raw + vị trí) → đúng MỘT dòng BOQ hiệu lực tại ngày NT (phân giải bằng thuật toán nguồn trên
        basis vừa chụp, rồi SQL kiểm lại). Ghi revision map mới; lần chạy sau dùng (callback cục bộ của worker). Không sửa tên/lượng raw để ép khớp."""
        dt = self.danh_tinh(dang_nhap)
        run, boq = _uuid(run_id, "run_id"), _uuid(boq_id, "boq_id")
        if not isinstance(row_id, str) or not re.fullmatch(r"[0-9a-f]{64}", row_id):
            raise DataError("M4_THAM_SO_SAI", "Mã dòng chứng từ không hợp lệ (lấy từ kết quả lần chạy).")
        dong_boq = _so_nguyen(boq_dong, "boq_dong", 1)
        ma_hm = _chuoi(ma_hm, "mã hạng mục BOQ", 500)
        ly = _chuoi(ly_do, "lý do ghép tay", 1000)
        rev = self._rev_l3(revision)
        exp, khoa = self._hex(expected_basis, "expected_basis"), self._khoa(khoa)
        p = self._ct_run_thay(dt, run)
        with self._tx(dt):
            x = self._mot("""SELECT dd->>'tep_id' AS tep_id, l->'vi_tri_vat_ly' AS locator, l->>'ten' AS ten
                             FROM m4.chung_tu_result x, jsonb_array_elements(coalesce(x.ket_qua->'tai_lieu', '[]'::jsonb)) dd,
                                  jsonb_array_elements(coalesce(dd->'dong', '[]'::jsonb)) l
                             WHERE x.run_id = %s::uuid AND l->>'row_id' = %s LIMIT 1""", (run, row_id))
        if x is None:
            raise DataError("M4_CHUNG_TU_DONG_KHONG_CO", "Lần chạy không có dòng chứng từ với mã này.")
        yc = {"run_id": run, "row_id": row_id, "boq_id": boq, "boq_dong": dong_boq, "ma_hm": ma_hm, "revision": rev, "expected_basis": exp, "ly_do": ly}
        yc_j = json.dumps(yc, ensure_ascii=False)
        with self._chua_ro(), self._khoa_phien(dt, khoa):
            with self._tx_review(dt) as c:
                c.execute("SELECT m4.chung_tu_kiem(%s::uuid)", (p["dot_id"],))
                c.execute("SELECT 1 FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s::uuid FOR UPDATE", (p["hop_dong_id"],))
                cu = self._r1(c, "SELECT m4.chung_tu_tra(%s, 'CHUNG_TU_GHEP', %s::uuid, %s::jsonb) AS r", (khoa, p["dot_id"], yc_j))["r"]
                if cu is not None:
                    return {**cu, "lap_lai": True}
                co = self._chung_tu_co_so(c, p["dot_id"])
                if self._sha_co_so(co) != exp:
                    raise DataError("M4_CHUNG_TU_CO_SO_DOI", "Căn cứ đã đổi so với lúc xem — tải lại rồi ghép.")
                dich = self._dich_hieu_luc({"hop_dong": co["hop_dong"], "dot": co["dot"], "tham_so": co["tham_so"], "phu_luc": co["phu_luc"], "boq": co["boq"],
                                            "manual_map": co["manual_map_l2"]}, ma_hm)  # đúng dòng engine nguồn dùng tại ngày NT (cùng snapshot)
                if str(dich["boq_id"]) != boq or int(dich["dong"]) != dong_boq:
                    raise DataError("M4_REVIEW_DICH_KHONG_HIEU_LUC", f"Mã {ma_hm} đang hiệu lực theo {dich['nguon']} ở dòng BOQ khác đích đã chọn — chọn lại đích.")
                r = self._r1(c, """SELECT m4.chung_tu_ghi_map(%s, %s::jsonb, %s::uuid, %s, %s::uuid, %s::integer, %s, %s::integer, %s, %s::uuid, %s::jsonb, %s) AS r""",
                             (khoa, yc_j, run, row_id, boq, dong_boq, ma_hm, rev, ly, x["tep_id"], json.dumps(x.get("locator") or {}, ensure_ascii=False),
                              (x.get("ten") or "")[:500] or None))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    # ------------------------------------------------------------------ M4-02C duyệt hồ sơ đợt / PDF / seal / KT chờ (miền ở m4/duyet_dot.py)
    def duyet_xem(self, dang_nhap: str, *, dot_id, version_id=None) -> dict:
        return DD.DuyetDot(self).xem(dang_nhap, dot_id=dot_id, version_id=version_id)

    def duyet_ket_luan(self, dang_nhap: str, **kw) -> dict:
        return DD.DuyetDot(self).ket_luan(dang_nhap, **kw)

    def duyet_chap_thuan(self, dang_nhap: str, **kw) -> dict:
        return DD.DuyetDot(self).chap_thuan(dang_nhap, **kw)

    def duyet_pdf(self, dang_nhap: str, raw: bytes, **kw) -> dict:
        return DD.DuyetDot(self).pdf(dang_nhap, raw, **kw)

    def duyet_pdf_tai(self, dang_nhap: str, version_id, pdf_id) -> tuple[str, str, bytes]:
        return DD.DuyetDot(self).pdf_tai(dang_nhap, version_id, pdf_id)

    def duyet_phien_ban(self, dang_nhap: str, **kw) -> dict:
        return DD.DuyetDot(self).phien_ban(dang_nhap, **kw)

    def duyet_phien_ban_nop(self, dang_nhap: str, **kw) -> dict:
        return DD.DuyetDot(self).phien_ban_nop(dang_nhap, **kw)

    # ------------------------------------------------------------------ M4-03A kế toán nghiệm thu (miền ở m4/ke_toan_nghiem_thu.py — backend03A, compose sau)
    # Wrapper mỏng: lazy import ĐÚNG module backend khi gọi (không làm M4 import lỗi khi chưa compose). Chỉ vắng CHÍNH module đó / lớp
    # KeToanNghiemThuK2 → M4_KT_CHUA_NOI (503). Lỗi import khác, DataError nghiệp vụ, lỗi CSDL đi nguyên — không stub thành công, không nuốt lỗi.
    _KT_MODULE = __name__.rsplit(".", 2)[0] + ".m4.ke_toan_nghiem_thu"

    def _kt(self):
        # import_module (không `from ..m4 import x`): fromlist nuốt ModuleNotFoundError của chính submodule rồi IMPORT_FROM ném ImportError chung
        # → không phân biệt được "chưa compose" với lỗi khác. import_module ném ModuleNotFoundError có .name = tên module thiếu.
        import importlib
        try:
            KT = importlib.import_module(self._KT_MODULE)
        except ModuleNotFoundError as exc:
            if exc.name != self._KT_MODULE:
                raise
            raise DataError("M4_KT_CHUA_NOI", "Chưa nối backend kế toán nghiệm thu (M4-03A) — không có lệnh/dữ liệu KT nào chạy.") from None
        lop = getattr(KT, "KeToanNghiemThuK2", None)
        if lop is None:
            raise DataError("M4_KT_CHUA_NOI", "Backend kế toán nghiệm thu (M4-03A) chưa cung cấp KeToanNghiemThuK2.")
        return lop(self)

    def kt_danh_sach(self, dang_nhap: str) -> dict:
        return self._kt().danh_sach(dang_nhap)

    def kt_xem(self, dang_nhap: str, *, kt_pending_id, phong_bi_id=None) -> dict:
        return self._kt().xem(dang_nhap, kt_pending_id=kt_pending_id, phong_bi_id=phong_bi_id)

    def kt_tep_pdf(self, dang_nhap: str, kt_pending_id, phong_bi_id) -> tuple[str, str, bytes]:
        return self._kt().tep_pdf(dang_nhap, kt_pending_id=kt_pending_id, phong_bi_id=phong_bi_id)

    def kt_luu(self, dang_nhap: str, **kw) -> dict:
        return self._kt().luu(dang_nhap, **kw)

    def kt_xac_nhan(self, dang_nhap: str, **kw) -> dict:
        return self._kt().xac_nhan(dang_nhap, **kw)
