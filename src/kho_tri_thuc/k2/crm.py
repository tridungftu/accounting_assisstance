"""CRM-01 — repository/service typed K2 trên PostgreSQL (bốn schema TL38): hợp đồng/phiên bản/tham số, lịch thu, việc V3/V4,
liên kết tiền ↔ đợt qua `kho.lien_ket_chung_tu` chung, file soát qua sổ đăng ký `kho.lo_xuat` + export Excel chung.
Không dùng Store V12 (khóa một pháp nhân), không quick_items, không K2 SQLite. Tiền đến từ M1 hiện có qua bộ chiếu (k2/m1_demo.py).

Mỗi thao tác chạy trong một giao dịch có danh tính phiên (ID + login) và ngày hiệu lực do máy chủ đặt; RLS/trigger kiểm lại.
Thao tác chạm nghĩa vụ hoặc tiền của một hợp đồng khóa dòng hợp đồng TRƯỚC (cùng thứ tự với trigger liên kết), rồi tính lại.
Mọi thay đổi ghi `nhat_ky.su_kien` (chỉ ghi thêm). Không tạo bút toán doanh thu/VAT/giá vốn, hóa đơn, 131 hay file Junsky.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, now_utc, sha256
from ..ha_tang.store import write_immutable
from ..nguon.review_xay_dung import chuan_hoa_so
from ..nguon.trich_hop_dong_6 import KIND, TrichHopDong6Adapter, doc_ket_qua, envelope, word_khoa
from . import quyen
from .crm_phan_tich import so_sanh_phu_luc, tham_so_typed, tong_hop

MODULE = "CRM"
BO_SUNG_KEYS = ("loai_hinh", "loai_ban", "hop_dong_goc", "ma_hop_dong_chung", "doi_tac_object_id", "du_an")
EXCEL_SO_CHINH_XAC = 10 ** 15
# Quyết định CFO đã chốt (TL32 §3.2, dòng quyết định 102 trong PLAN): tiền về chưa rõ — chưa có HĐ → 344; có HĐ hiệu lực → 131 đợt gần nhất;
# tiền lệch → hỏi/chờ. Đây là căn cứ của đề xuất Vàng, không phải policy đã duyệt trong kho tri thức.
TK_PHAI_THU_HOP_DONG = "131"
QUY_TAC_TIEN_VE = "TL32 §3.2 (CFO): chưa có HĐ → 344; có HĐ hiệu lực → 131 đợt gần nhất; tiền lệch → hỏi/chờ"


def _s(v):
    """Tiền ra API dạng chuỗi (lossless)."""
    return None if v is None else str(v)


def _d(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def _j(value):
    return None if value is None else json.dumps(chuan_hoa_so(value), ensure_ascii=False, default=str)


def _hom_nay_vn() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


class CrmK2:
    def __init__(self, conn, thu_muc_tep: Path, *, chi_mo_phong: bool = True, hom_nay=None):
        """conn: psycopg connection autocommit=True, row_factory=dict_row, đăng nhập vai trò ứng dụng (thành viên app_web).
        hom_nay: đồng hồ nghiệp vụ (callable → date) để kiểm hiệu lực theo ngày; mặc định ngày Việt Nam hiện tại."""
        from psycopg.types.string import StrDumperUnknown
        self.conn, self.root, self.chi_mo_phong = conn, Path(thu_muc_tep), chi_mo_phong
        self.hom_nay = hom_nay or _hom_nay_vn
        conn.adapters.register_dumper(str, StrDumperUnknown)  # chuỗi để máy chủ suy kiểu (uuid/date/text) như lớp kết nối V13

    # ------------------------------------------------------------------ hạ tầng
    def danh_tinh(self, dang_nhap: str) -> dict:
        return quyen.nap_danh_tinh(self.conn, dang_nhap, chi_mo_phong=self.chi_mo_phong)

    @contextmanager
    def _tx(self, dt):
        request_id = str(uuid.uuid4())  # một lần/thao tác; không dùng request ID của trình duyệt
        try:
            with self.conn.transaction():
                self._dat_phien(dt)
                yield
        except quyen.TuChoiThamQuyen as exc:
            # __exit__ transaction ở trên đã rollback trước khi mở transaction audit.
            try:
                # Với ambient transaction, transaction() chỉ là savepoint; không
                # được báo đã ghi bền khi commit còn phụ thuộc caller bên ngoài.
                if getattr(getattr(self.conn, "info", None), "transaction_status", 0) != 0:
                    raise RuntimeError("Nhật ký cần transaction cấp cao nhất")
                with self.conn.transaction():
                    self._dat_phien(dt)
                    quyen.ghi_tu_choi_tham_quyen(self.conn, request_id, exc)
            except Exception:
                logging.getLogger(__name__).error("MTQ_NHAT_KY_LOI request_id=%s", request_id, exc_info=True)
                raise DataError("MTQ_NHAT_KY_LOI", "Chưa ghi được nhật ký thẩm quyền, thao tác không được thực hiện. Báo quản trị.") from None
            raise

    def _dat_phien(self, dt):
        self.conn.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                          "set_config('ktt.ngay_hieu_luc', %s, true)", (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat()))

    def _tien_mtq(self, hd_id, pb_id=None):
        """Chỉ MA_TRAN: tổng HĐ của đúng bản quyết định, khóa HĐ → bản → tham số.

        V4 không có khóa phiên bản ở API: chỉ dùng khi đúng một bản CHO_DUYET.
        Chưa có resolver ngoại tệ/tỷ giá ghim: trả thiếu tiền để lõi chặn.
        Không lấy tiền trên master.hop_dong, lịch thu hay payload trình duyệt.
        """
        self._khoa_hop_dong(hd_id)
        rows = self.conn.execute("""SELECT id FROM master.hop_dong_phien_ban WHERE hop_dong_id = %s
                                    AND ((%s::uuid IS NOT NULL AND id = %s::uuid)
                                      OR (%s::uuid IS NULL AND trang_thai = 'CHO_DUYET')) FOR UPDATE""",
                                 (hd_id, pb_id, pb_id, pb_id)).fetchall()
        if len(rows) != 1:
            return None
        pb_id = rows[0]["id"]
        self.conn.execute("SELECT id FROM master.hop_dong_tham_so WHERE phien_ban_id = %s ORDER BY ten FOR UPDATE",
                          (pb_id,)).fetchall()
        total = self._phan_tich_pb(pb_id)[2]["fields"].get("gia_tri_hop_dong")
        if not total or total.get("tien_te") != "VND":
            return None
        return total.get("minor")

    def _kiem_mtq_duyet(self, dt, hanh_dong_cu, hd_id, pn, *, pb_id=None):
        # hd_id lấy từ HĐ/bản đã đọc qua RLS trong transaction có GUC, không từ body.
        return quyen.kiem_tham_quyen(
            self.conn, "CRM:TIEP_NHAN:DUYET", {"bang": "master.hop_dong", "id": str(hd_id)},
            {"kiem_cu": lambda: quyen.kiem(dt, hanh_dong_cu, pn),
             "so_tien_vnd": lambda: self._tien_mtq(hd_id, pb_id),
             "khong_thay": ("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).") if pb_id
                           else ("HOP_DONG", "Không thấy hợp đồng (hoặc ngoài quyền).")})

    def _su_kien(self, pn, dt, loai, bang, doi_tuong_id, hanh_dong, *, truoc=None, sau=None, ly_do=None, can_cu=None):
        self.conn.execute("""INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, doi_tuong_id, hanh_dong, truoc, sau, ly_do, can_cu)
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                          (pn, dt["dang_nhap"], loai, bang, doi_tuong_id, hanh_dong, _j(truoc), _j(sau), ly_do, _j(can_cu)))

    def _pn(self, ma: str) -> str:
        row = self.conn.execute("SELECT id FROM master.phap_nhan WHERE ma = %s", (ma,)).fetchone()
        if not row:
            raise DataError("PHAP_NHAN", "Không có pháp nhân này.")
        return str(row["id"])

    def _profile(self, pn, ma=None, *, lh_id=None):
        if lh_id:
            return self.conn.execute("SELECT id, cau_hinh, phien_ban FROM master.loai_hinh_doanh_thu WHERE id = %s", (lh_id,)).fetchone()
        if not ma:
            return None
        return self.conn.execute("""SELECT id, cau_hinh, phien_ban FROM master.loai_hinh_doanh_thu WHERE phap_nhan_id = %s AND ma = %s AND valid_to IS NULL
                                    ORDER BY phien_ban DESC LIMIT 1""", (pn, ma)).fetchone()

    def _khoa_hop_dong(self, hd):
        """Khóa dòng hợp đồng (thứ tự khóa chung: hợp đồng → khoản tiền → đợt) cho mọi thao tác chạm nghĩa vụ/tiền."""
        row = self.conn.execute("SELECT * FROM master.hop_dong WHERE id = %s FOR UPDATE", (hd,)).fetchone()
        if not row:
            raise DataError("HOP_DONG", "Không thấy hợp đồng (hoặc ngoài quyền).")
        return row

    def _viec(self, pn, loai, bang, ref, tom_tat, ly_do_cho, *, vai_tro="CFO"):
        row = self.conn.execute("""SELECT id FROM kho.viec_can_duyet WHERE tham_chieu_bang = %s AND tham_chieu_id = %s
                                   AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')""", (bang, ref)).fetchone()
        if row:
            self.conn.execute("UPDATE kho.viec_can_duyet SET ly_do_cho = %s, tom_tat = coalesce(%s, tom_tat), cap_nhat_luc = now() WHERE id = %s",
                              (ly_do_cho, tom_tat, row["id"]))
            return row["id"]
        return self.conn.execute("""INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id, nguoi_duyet_vai_tro, tom_tat, ly_do_cho)
                                    VALUES (%s,%s,'M3',%s,%s,%s,%s,%s,%s) RETURNING id""", (pn, loai, MODULE, bang, ref, vai_tro, tom_tat, ly_do_cho)).fetchone()["id"]

    def _dong_viec(self, bang, ref, trang_thai, dt, *, loai=None):
        self.conn.execute("""UPDATE kho.viec_can_duyet SET trang_thai = %s, duyet_boi = %s, duyet_luc = now(), cap_nhat_luc = now()
                             WHERE tham_chieu_bang = %s AND tham_chieu_id = %s AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')
                               AND (%s::text IS NULL OR loai = %s::text)""", (trang_thai, dt["dang_nhap"], bang, ref, loai, loai))

    # ------------------------------------------------------------------ K1: nhận kết quả #6
    # ------------------------------------------------------------------ CRM-41-01: tiếp nhận DOCX thô → engine trích DÙNG CHUNG #6
    CRM_TRICH_ENV = ("phap_nhan", "loai_hinh", "loai_ban", "hop_dong_goc", "ma_hop_dong_chung", "doi_tac_object_id", "du_an")

    def trich_tu_docx(self, dang_nhap: str, docx: bytes, thong_tin: dict, *, loai_hop_dong: str, tham_so, request_id: str, client) -> dict:
        """Hồ sơ Word thô → engine #6 (common/v1, RULE_ONLY) → MỘT projection bang[]→tham_so[] → đường nhận kết quả #6 hiện có (kiểm/duyệt
        như cũ). Quyền PN/module kiểm TRƯỚC mọi tác động/gọi engine và kiểm LẠI trong nhan_ket_qua_6 trước khi ghi. Loại trích ≠ loại hình tài
        chính; loại chưa có danh mục → không hỗ trợ. Gọi ngoài giao dịch/khóa toàn cục (route dùng kết nối riêng)."""
        from ..nguon import trich_chung_6 as T6
        dt = self.danh_tinh(dang_nhap)
        if not isinstance(docx, (bytes, bytearray)) or bytes(docx[:4]) != b"PK\x03\x04":
            raise DataError("CRM_TRICH_CHI_DOCX", "Chỉ nhận tệp Word .docx cho trích tham số.")
        if not isinstance(thong_tin, dict) or not (thong_tin.get("phap_nhan") or "").strip():
            raise DataError("TRICH6_THIEU_PHAP_NHAN", "Chưa xác định pháp nhân của hồ sơ — không gọi engine (không đoán từ tên file).")
        la = sorted(set(thong_tin) - set(self.CRM_TRICH_ENV))
        if la:
            raise DataError("CRM_ENVELOPE", "Thông tin trích có trường ngoài phạm vi: " + ", ".join(la))
        pn = self._pn(thong_tin["phap_nhan"].strip())
        quyen.kiem(dt, "NOP_HOP_DONG", pn)  # trước mọi side effect / gọi engine
        T6.yeu_cau_common(source_sha256=sha256(bytes(docx)), loai_hop_dong=loai_hop_dong, tham_so=tham_so, request_id=request_id)  # lỗi rõ trước
        if client is None:
            raise DataError("CRM_TRICH6_CHUA_SAN_SANG", "Engine trích dùng chung #6 chưa được máy chủ cấu hình — chưa trích.")
        h_docx = sha256(bytes(docx))
        # FIX01 F4: ý định GỐC ĐẦY ĐỦ ở máy chủ — actor (danh tính phiên, không từ trình duyệt) + envelope đã chọn (PN/loại hình tài chính/dự án/
        # loại bản/…) + LOẠI TRÍCH (danh mục) + mã + SHA Word. Ghi bền một lần TRƯỚC mọi lưu tệp/gọi engine; cùng ID logic mà nội dung khác → xung đột,
        # không rơi vào TRUNG_RAW của envelope cũ. ID gửi engine dẫn xuất từ toàn bộ ý định (ổn định giữa các lần thử lại).
        env_chuan = {k: (str(thong_tin[k]).strip() or None) if thong_tin.get(k) is not None else None for k in sorted(self.CRM_TRICH_ENV)}
        y_dinh = {"phien_ban": "crm-trich6-y-dinh-v1", "actor_id": str(dt["id"]), "dang_nhap": dt["dang_nhap"], "request_id": request_id,
                  "loai_trich": loai_hop_dong, "tham_so": tham_so, "source_sha256": h_docx, "envelope": env_chuan}
        # FIX02 R4: bản ghi khóa theo ID LOGIC trong namespace CRM (KHÔNG tách theo actor). Actor có thẩm quyền nằm TRONG nội dung bất biến cùng PN/
        # loại hình/dự án/loại bản/tệp/loại trích/mã → cùng ID mà khác actor hoặc khác nội dung đều xung đột trước engine; thông báo không lộ chủ/nội
        # dung cũ. Quyền hiện hành đã kiểm ở trên (trước tra cứu/tác động). Tên tệp băm: an toàn Windows.
        p_yd = self.root / "crm-trich-y-dinh" / (sha256(("crm-y-dinh|" + request_id).encode("utf-8")) + ".json")
        b_yd = canonical_json(y_dinh).encode("utf-8")
        xung_dot = DataError("CRM_TRICH_XUNG_DOT", "Mã ý định trích đã được dùng cho một yêu cầu khác — không trích; tạo yêu cầu mới.")
        if not client.san_sang:
            # CRM-41-01-06: phân loại THEO GIAI ĐOẠN, chỉ đọc. Ý định CRM đầy đủ đã có → kiểm xung đột trước (quyền hiện hành đã kiểm ở trên), rồi
            # UNKNOWN (engine có thể đã nhận lệnh trước đó; cấu hình lại sẽ đối soát lượt cũ). Chưa có → lỗi cấu hình rõ, KHÔNG ghi ý định/raw mới.
            if p_yd.is_file():
                if p_yd.read_bytes() != b_yd:
                    raise xung_dot
                raise T6.ChuaRo("TRICH6_CHUA_RO", "Ý định trích đã giữ nhưng engine #6 hiện chưa sẵn sàng — chưa rõ; giữ nguyên ý định, thử lại sau.")
            raise DataError("CRM_TRICH6_CHUA_SAN_SANG", "Engine trích dùng chung #6 chưa được máy chủ cấu hình — chưa trích.")
        if p_yd.is_file():  # đối chiếu TRƯỚC khi ghi: lần thử xung đột không để lại tệp nào (kể cả staging của write_immutable)
            if p_yd.read_bytes() != b_yd:
                raise xung_dot
        else:
            try:
                write_immutable(p_yd, b_yd)
            except DataError as exc:  # hai yêu cầu cùng ID tạo đồng thời: bản kia thắng, khác nội dung → xung đột
                if exc.code == "ARTIFACT_CHANGED":
                    raise xung_dot from None
                raise
        rid_nguon = "crm:" + sha256(canonical_json(y_dinh).encode("utf-8"))[:48]
        write_immutable(self.root / "k2-tep" / f"{h_docx}.docx", bytes(docx))  # Word gốc giữ nguyên bytes
        r6 = client.trich(bytes(docx), ten_tep="hop_dong.docx", loai_hop_dong=loai_hop_dong, tham_so=tham_so, request_id=rid_nguon)
        write_immutable(self.root / "k2-tep" / f"{r6['raw_sha256']}.json", r6["raw_ket_qua"])  # raw nguồn #6 nguyên bytes, hash riêng
        view = T6.chieu_tham_so(r6["ket_qua"], raw_sha256=r6["raw_sha256"])
        cm = r6["common"]
        common = {"contract": cm["contract"], "request_id": rid_nguon, "luot": r6["luot"], "raw_ket_qua_sha256": r6["raw_sha256"],
                  "source_sha256": h_docx, "catalog_id": cm["catalog_id"], "catalog_sha256": cm["catalog_sha256"], "loai_hop_dong": cm["loai_hop_dong"],
                  "implementation_sha256": (cm.get("implementation") or {}).get("sha256"), "tham_so_yeu_cau": cm.get("tham_so_yeu_cau"),
                  "tham_so_da_dung": cm["tham_so_da_dung"], "adapter": view["adapter"]}
        env_info = {**{k: v for k, v in env_chuan.items() if v is not None}, "namespace": "TRICH_6_COMMON_V1", "word_hash": h_docx}
        out = self.nhan_ket_qua_6(dang_nhap, T6.view_bytes(view), env_info, common=common)  # quyền kiểm LẠI trước ghi
        return {**out, "luot_6": r6["luot"], "ket_qua_6_sha256": r6["raw_sha256"], "tham_so_da_dung": cm["tham_so_da_dung"]}

    def nhan_ket_qua_6(self, dang_nhap: str, raw: bytes, thong_tin: dict, *, van_ban_nguon=None, common: dict | None = None) -> dict:
        dt = self.danh_tinh(dang_nhap)
        env = envelope(raw, thong_tin, van_ban_nguon=van_ban_nguon, common=common)
        write_immutable(self.root / "k2-tep" / f"{env['hash_ket_qua']}.bin", raw)  # raw giữ nguyên trước mọi kiểm tra
        if van_ban_nguon is not None:
            vb = van_ban_nguon if isinstance(van_ban_nguon, str) else canonical_json(van_ban_nguon)
            write_immutable(self.root / "k2-tep" / f"{env['van_ban_nguon_hash']}.txt", vb.encode("utf-8"))
        ket_qua = doc_ket_qua(raw)
        if not env["phap_nhan"]:
            raise DataError("TRICH6_THIEU_PHAP_NHAN", "Chưa xác định pháp nhân của hồ sơ — không ghi vào kho (không đoán từ tên file).")
        pn = self._pn(env["phap_nhan"])
        quyen.kiem(dt, "NOP_HOP_DONG", pn)
        record = TrichHopDong6Adapter(env).read(raw)
        batch_issues = [i.code for i in record.issues]
        with self._tx(dt):
            tep = self.conn.execute("""INSERT INTO kho.tep_goc (phap_nhan_id, loai_nguon, duong_dan, hash, kich_thuoc, nguon, nguoi)
                                       VALUES (%s,'TRICH_6',%s,%s,%s,'TAY',%s) ON CONFLICT (hash) DO NOTHING RETURNING id""",
                                    (pn, f"k2-tep/{env['hash_ket_qua']}.bin", env["hash_ket_qua"], len(raw), dt["dang_nhap"])).fetchone()
            if tep is None:
                tep = self.conn.execute("SELECT id FROM kho.tep_goc WHERE hash = %s AND phap_nhan_id = %s", (env["hash_ket_qua"], pn)).fetchone()
                if tep is None:
                    raise DataError("TEP_THUOC_PHAP_NHAN_KHAC", "Tệp này đã được nhận cho pháp nhân khác hoặc ngoài quyền — không gộp.")
            profile = self._profile(pn, env["loai_hinh"])
            params = tham_so_typed(ket_qua, profile["cau_hinh"], van_ban_nguon) if profile else []
            du_lieu = {**record.records[0].core, "tham_so_typed": params, "van_ban_nguon": van_ban_nguon, "word_khoa": word_khoa(env)}
            ct = self.conn.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, mo_ta, du_lieu, hash, tep_goc_id, trang_thai)
                                      VALUES (%s,%s,%s,current_date,%s,%s,%s,%s,'CHO_DUYET')
                                      ON CONFLICT (phap_nhan_id, loai, khoa_nguon) DO NOTHING RETURNING id""",
                                   (pn, KIND, f"{env['namespace']}:{env['hash_ket_qua']}", "Kết quả trích hợp đồng #6 (ngày nghiệp vụ = ngày nhận tệp, không phải ngày ký)",
                                    json.dumps(du_lieu, ensure_ascii=False), env["hash_ket_qua"], tep["id"])).fetchone()
            if ct is None:
                old = self.conn.execute("SELECT id FROM kho.chung_tu WHERE phap_nhan_id = %s AND loai = %s AND khoa_nguon = %s",
                                        (pn, KIND, f"{env['namespace']}:{env['hash_ket_qua']}")).fetchone()
                return {"trung": True, "chung_tu_id": str(old["id"]), "ket_qua": "TRUNG_RAW", "issues": batch_issues,
                        "huong_dan": "Hồ sơ đã nhận; nếu đang chờ khóa/mapping, dùng Bổ sung hồ sơ trên đúng chứng từ này."}
            self._su_kien(pn, dt, "HE_THONG", "kho.chung_tu", ct["id"], "NHAN_KET_QUA_6",
                          sau={"hash": env["hash_ket_qua"], "namespace": env["namespace"], "loai_ban": env["loai_ban"]})
            result = self._lap_ho_so(dt, pn, ct["id"], du_lieu)
        return {"trung": False, "chung_tu_id": str(ct["id"]), **result, "issues": batch_issues}

    def _lap_ho_so(self, dt, pn, ct_id, du_lieu) -> dict:
        env = du_lieu["envelope"]
        profile = self._profile(pn, env["loai_hinh"])
        thieu = []
        if not profile:
            thieu.append("THIEU_LOAI_HINH")
        if env["loai_ban"] not in ("GOC", "PHU_LUC"):
            thieu.append("THIEU_LOAI_BAN")
        if thieu:
            self._viec(pn, "V4", "kho.chung_tu", ct_id, "Hồ sơ #6 thiếu mapping", thieu, vai_tro="KE_TOAN")
            return {"ket_qua": "CHO_MAPPING", "ly_do": thieu}
        cfg, params = profile["cau_hinh"], du_lieu["tham_so_typed"]
        if du_lieu.get("word_khoa"):  # cùng Word đã có phiên bản → bản trích lại, không tự là phụ lục/phiên bản pháp lý
            same = self.conn.execute("""SELECT p.id FROM master.hop_dong_phien_ban p JOIN kho.chung_tu c ON c.id = p.chung_tu_id
                                        JOIN master.hop_dong h ON h.id = p.hop_dong_id
                                        WHERE h.phap_nhan_id = %s AND c.du_lieu->>'word_khoa' = %s AND c.id <> %s AND p.trang_thai <> 'THAY_THE'
                                        ORDER BY p.phien_ban DESC LIMIT 1""", (pn, du_lieu["word_khoa"], ct_id)).fetchone()
            if same:
                self._viec(pn, "V3", "kho.chung_tu", ct_id, "Bản trích lại cùng Word — đối chiếu rồi chọn giữ bản cũ hoặc áp dụng", ["TRICH_LAI_CUNG_WORD"], vai_tro="KE_TOAN")
                return {"ket_qua": "TRICH_LAI", "phien_ban_doi_chieu": str(same["id"])}
        th = tong_hop(params, cfg, loai_ban=env["loai_ban"])
        if env["loai_ban"] == "GOC":
            so_hd = (th["fields"].get("so_hop_dong") or {}).get("text")
            ma = env.get("ma_hop_dong_chung")
            missing = [code for code, ok in (("THIEU_SO_HOP_DONG_CO_CAN_CU", so_hd), ("THIEU_MA_HOP_DONG_CHUNG", ma)) if not ok]
            if missing:
                self._viec(pn, "V4", "kho.chung_tu", ct_id, "Khóa hợp đồng chưa đủ", missing, vai_tro="KE_TOAN")
                return {"ket_qua": "CHO_KHOA", "ly_do": missing}
            clash = self.conn.execute("""SELECT id FROM master.hop_dong WHERE phap_nhan_id = %s AND (ma_noi_bo = %s OR (loai = %s AND so_hop_dong = %s))""",
                                      (pn, ma, cfg["loai_hop_dong"], so_hd)).fetchone()
            if clash:
                self._viec(pn, "V4", "kho.chung_tu", ct_id, "Hợp đồng đã có bản gốc — không tự gộp", ["HOP_DONG_DA_CO"], vai_tro="KE_TOAN")
                return {"ket_qua": "XUNG_DOT", "ly_do": ["HOP_DONG_DA_CO"]}
            doi_tac = self._map("master.doi_tac_ma_junsky", "object_id_junsky", "doi_tac_id", pn, env.get("doi_tac_object_id"))
            du_an = self._map("master.du_an", "ma_junsky", "id", pn, env.get("du_an"))
            total, ngay_ky = th["fields"].get("gia_tri_hop_dong"), th["fields"].get("ngay_ky")
            hd = self.conn.execute("""INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, doi_tac_id, du_an_id, loai_hinh_dt_id, ngay_ky,
                                      gia_tri_minor, tien_te, trang_thai) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'CHO_DUYET') RETURNING id""",
                                   (pn, cfg["loai_hop_dong"], ma, so_hd, doi_tac, du_an, profile["id"], _d(ngay_ky["ngay"]) if ngay_ky else None,
                                    total["minor"] if total else None, total["tien_te"] if total else "VND")).fetchone()["id"]
            pb = self._tao_phien_ban(dt, hd, 1, "GOC", ct_id, profile, params, None, ngay_ky["ngay"] if ngay_ky else None)
            chan = self.chan_phien_ban(pb)
            self._viec(pn, "V4", "master.hop_dong", hd, f"Hợp đồng mới {so_hd}", [c["ma"] for c in chan if c["ma"].startswith("MAPPING")])
            self._viec(pn, "V3", "master.hop_dong_phien_ban", pb, f"Tham số hợp đồng {so_hd} — phiên bản 1", [c["ma"] for c in chan])
            self._dong_viec_ho_so(ct_id, dt)
            self._su_kien(pn, dt, "SUA_DANH_MUC", "master.hop_dong", hd, "TAO_HOP_DONG_CHO_DUYET", sau={"ma_noi_bo": ma, "so_hop_dong": so_hd})
            return {"ket_qua": "HOP_DONG_CHO_DUYET", "hop_dong_id": str(hd), "phien_ban_id": str(pb), "chan": chan}
        base = self.conn.execute("""SELECT h.id, h.phien_ban_hien_hanh, p.trang_thai FROM master.hop_dong h LEFT JOIN master.hop_dong_phien_ban p ON p.id = h.phien_ban_hien_hanh
                                    WHERE h.phap_nhan_id = %s AND h.ma_noi_bo = %s""", (pn, env.get("hop_dong_goc"))).fetchone()
        if not base or base["trang_thai"] != "DA_DUYET":
            self._viec(pn, "V4", "kho.chung_tu", ct_id, "Phụ lục chưa xác định hợp đồng gốc đã duyệt", ["PHU_LUC_KHONG_CO_BAN_GOC"], vai_tro="KE_TOAN")
            return {"ket_qua": "CHO_BAN_GOC", "ly_do": ["PHU_LUC_KHONG_CO_BAN_GOC"]}
        self._khoa_hop_dong(base["id"])
        pending = self.conn.execute("SELECT id FROM master.hop_dong_phien_ban WHERE hop_dong_id = %s AND trang_thai = 'CHO_DUYET'", (base["id"],)).fetchone()
        if pending:
            self._viec(pn, "V4", "kho.chung_tu", ct_id, "Hợp đồng đang có phiên bản chờ duyệt", ["DANG_CO_PHIEN_BAN_CHO"], vai_tro="KE_TOAN")
            return {"ket_qua": "XUNG_DOT", "ly_do": ["DANG_CO_PHIEN_BAN_CHO"]}
        so = self.conn.execute("SELECT max(phien_ban) AS n FROM master.hop_dong_phien_ban WHERE hop_dong_id = %s", (base["id"],)).fetchone()["n"]
        ngay_hl = (th["fields"].get("ngay_hieu_luc_phu_luc") or {}).get("ngay")
        so_pl = (th["fields"].get("so_phu_luc") or {}).get("text")
        pb = self._tao_phien_ban(dt, base["id"], so + 1, "PHU_LUC", ct_id, profile, params, base["phien_ban_hien_hanh"], ngay_hl, so_phu_luc=so_pl)
        chan = self.chan_phien_ban(pb)
        self._viec(pn, "V3", "master.hop_dong_phien_ban", pb, f"Phụ lục {so_pl or '(chưa có số)'} — phiên bản {so + 1}", [c["ma"] for c in chan])
        self._dong_viec_ho_so(ct_id, dt)
        self._su_kien(pn, dt, "PHU_LUC", "master.hop_dong_phien_ban", pb, "NHAN_PHU_LUC_CHO_DUYET", sau={"phien_ban": so + 1})
        return {"ket_qua": "PHU_LUC_CHO_DUYET", "hop_dong_id": str(base["id"]), "phien_ban_id": str(pb), "chan": chan}

    def _dong_viec_ho_so(self, ct_id, dt):
        """Hồ sơ đã thành hợp đồng/phiên bản → đóng việc chờ khóa/mapping của chính chứng từ (không xóa, có người/thời điểm)."""
        self.conn.execute("""UPDATE kho.viec_can_duyet SET trang_thai = 'DONG', duyet_boi = %s, duyet_luc = now(), cap_nhat_luc = now()
                             WHERE tham_chieu_bang = 'kho.chung_tu' AND tham_chieu_id = %s AND loai = 'V4' AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')""",
                          (dt["dang_nhap"], ct_id))

    def _map(self, bang, cot, ra, pn, value):
        if not value:
            return None
        row = self.conn.execute(f"SELECT {ra} AS v FROM {bang} WHERE phap_nhan_id = %s AND {cot} = %s AND valid_to IS NULL", (pn, value)).fetchone()
        return row["v"] if row else None

    def _tao_phien_ban(self, dt, hd, so, loai, ct_id, profile, params, thay_cho, ngay_hl, *, so_phu_luc=None, them=None):
        nguon = "BAN_HANG" if dt["vai_tro"] == "BAN_HANG" else "TRICH_6"
        tep = self.conn.execute("SELECT tep_goc_id FROM kho.chung_tu WHERE id = %s", (ct_id,)).fetchone()["tep_goc_id"]
        pin = {"profile": {"ma": profile["cau_hinh"]["ma"], "phien_ban": profile["phien_ban"], "hash": sha256(canonical_json(profile["cau_hinh"]).encode())}, **(them or {})}
        pb = self.conn.execute("""INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, loai, so_phu_luc, tep_goc_id, nguon, trang_thai, thay_cho_id,
                                  ngay_hieu_luc, chung_tu_id, loai_hinh_dt_id, tao_boi, tham_so) VALUES (%s,%s,%s,%s,%s,%s,'CHO_DUYET',%s,%s,%s,%s,%s,%s) RETURNING id""",
                               (hd, so, loai, so_phu_luc, tep, nguon, thay_cho, _d(ngay_hl), ct_id, profile["id"], dt["dang_nhap"], _j(pin))).fetchone()["id"]
        moi = {p["ma"] for p in params}
        seen: dict[str, int] = {}
        if thay_cho:  # phụ lục: kế thừa tham số đã duyệt của bản hiện hành cho mã phụ lục không nêu (giữ nguồn/căn cứ cũ)
            for r in self.conn.execute("SELECT * FROM master.hop_dong_tham_so WHERE phien_ban_id = %s ORDER BY ten", (thay_cho,)).fetchall():
                if r["ma_nguon"] not in moi:
                    self._ghi_tham_so(pb, self._tu_dong(r), r["chung_tu_id"], seen, ke_thua=r["id"])
        for p in params:
            self._ghi_tham_so(pb, p, ct_id, seen)
        return pb

    def _ghi_tham_so(self, pb, p, ct_id, seen, *, ke_thua=None):
        n = seen[p["ma"]] = seen.get(p["ma"], 0) + 1  # mã lặp trong nguồn giữ đủ từng dòng (parser báo mâu thuẫn), không ghi đè
        hieu_luc = p["gia_tri_tho"] if p["trang_thai_can_cu"] == "CO_CAN_CU" or (p["trang_thai_can_cu"] in ("SUY_RA", "GIA_TRI_KHONG_KHOP_TRICH_DAN") and p.get("xac_nhan_thu_cong")) \
            or p["trang_thai_can_cu"] in ("CHUA_DOI_CHIEU_NGUON", "CHUA_DOI_CHIEU_VI_TRI") else None
        self.conn.execute("""INSERT INTO master.hop_dong_tham_so (phien_ban_id, ten, gia_tri, don_vi, trich_dan, nguon, ma_nguon, nhom, truong, gia_tri_tho, kieu,
                             gia_tri_typed, dieu_khoan, vi_tri, kiem_tra_nguon, ghi_chu_nguon, trang_thai_can_cu, loi, chung_tu_id, ke_thua_tu, xac_nhan_thu_cong)
                             VALUES (%s,%s,%s,%s,%s,'TRICH_6',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                          (pb, p["ma"] if n == 1 else f"{p['ma']}#{n}", hieu_luc if p["trang_thai_can_cu"] != "KHONG_QUY_DINH" else None, p["don_vi"], p["trich_dan"],
                           p["ma"], p["nhom"], p["truong"], p["gia_tri_tho"], p["kieu"], _j(p["gia_tri_typed"]), p["dieu_khoan"], p["vi_tri"], p["kiem_tra_nguon"],
                           p["ghi_chu_nguon"], p["trang_thai_can_cu"], list(p["loi"]), ct_id, ke_thua, _j(p.get("xac_nhan_thu_cong"))))

    @staticmethod
    def _tu_dong(r) -> dict:
        return {"ma": r["ma_nguon"], "nhom": r["nhom"], "tham_so": None, "gia_tri_tho": r["gia_tri_tho"], "don_vi": r["don_vi"], "dieu_khoan": r["dieu_khoan"],
                "trich_dan": r["trich_dan"], "vi_tri": r["vi_tri"], "kiem_tra_nguon": r["kiem_tra_nguon"], "ghi_chu_nguon": r["ghi_chu_nguon"],
                "trang_thai_can_cu": r["trang_thai_can_cu"], "truong": r["truong"], "kieu": r["kieu"], "gia_tri_typed": r["gia_tri_typed"], "loi": list(r["loi"]),
                "xac_nhan_thu_cong": r["xac_nhan_thu_cong"]}

    # ------------------------------------------------------------------ điều kiện chặn (tính lại từ bản ghi đã lưu)
    def _phan_tich_pb(self, pb_id):
        pb = self.conn.execute("""SELECT p.*, h.phap_nhan_id, h.doi_tac_id, h.du_an_id, h.ma_noi_bo, l.cau_hinh FROM master.hop_dong_phien_ban p
                                  JOIN master.hop_dong h ON h.id = p.hop_dong_id LEFT JOIN master.loai_hinh_doanh_thu l ON l.id = p.loai_hinh_dt_id WHERE p.id = %s""",
                               (pb_id,)).fetchone()
        if not pb:
            raise DataError("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")
        rows = self.conn.execute("SELECT * FROM master.hop_dong_tham_so WHERE phien_ban_id = %s ORDER BY ten", (pb_id,)).fetchall()
        params = [self._tu_dong(r) for r in rows]
        thu_cong = bool((pb["tham_so"] or {}).get("xac_nhan_can_cu_thu_cong"))
        th = tong_hop(params, pb["cau_hinh"], loai_ban=pb["loai"], da_xac_nhan_thu_cong=thu_cong)
        chan = list(th["chan"])
        if pb["doi_tac_id"] is None:
            chan.append({"ma": "MAPPING_DOI_TAC", "thong_diep": "Chưa có ObjectID Junsky của đối tác theo pháp nhân — tạo ở Junsky trước rồi mapping."})
        if pb["du_an_id"] is None:
            chan.append({"ma": "MAPPING_DU_AN", "thong_diep": "Chưa có mã dự án (ProjectID) của pháp nhân."})
        plan = None
        if pb["loai"] == "PHU_LUC" and pb["thay_cho_id"] and th["lich"]:
            plan, extra = so_sanh_phu_luc(self._lich_cu(pb["thay_cho_id"]), th["lich"])
            chan.extend(extra)
        return pb, rows, th, chan, plan

    def chan_phien_ban(self, pb_id) -> list[dict]:
        return self._phan_tich_pb(pb_id)[3]

    def _lich_cu(self, pb_id):
        """Lịch của bản được thay + phần đã có tiền nối theo chuỗi khóa (hàm CSDL, cùng một số cho mọi người, không phụ thuộc RLS M1)."""
        out = []
        for r in self.conn.execute("""SELECT l.*, master.crm_da_lien_ket(p.hop_dong_id, l.khoa_nghia_vu) AS da_lk FROM master.lich_thu l
                                      JOIN master.hop_dong_phien_ban p ON p.id = l.phien_ban_id WHERE l.phien_ban_id = %s""", (pb_id,)):
            out.append({"khoa": r["khoa_nghia_vu"], "id": r["id"], "so_tien_minor": r["so_tien_minor"], "tien_te": r["tien_te"], "loai": r["loai"], "dot": r["dot"],
                        "co_so": r["co_so"], "han": r["han"].isoformat() if r["han"] else None, "moc": r["moc"], "da_lien_ket_minor": int(r["da_lk"])})
        return out

    def _vo_hieu_kiem(self, pb, dt, ly_do):
        """Nội dung/mapping đổi sau lần kế toán kiểm → lần kiểm hết hiệu lực (giữ vết lần cũ trong nhật ký)."""
        if pb["kiem_boi"] is None:
            return
        self.conn.execute("UPDATE master.hop_dong_phien_ban SET kiem_boi = NULL, kiem_luc = NULL, kiem_van_tay = NULL WHERE id = %s", (pb["id"],))
        self.conn.execute("UPDATE kho.viec_can_duyet SET kiem_boi = NULL, kiem_luc = NULL WHERE tham_chieu_id IN (%s, %s) AND trang_thai = 'CHO_DUYET'",
                          (pb["id"], pb["hop_dong_id"]))
        self._su_kien(pb["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb["id"], "VO_HIEU_KIEM",
                      truoc={"kiem_boi": pb["kiem_boi"], "kiem_luc": pb["kiem_luc"], "kiem_van_tay": pb["kiem_van_tay"]}, ly_do=ly_do)

    # ------------------------------------------------------------------ K5: bổ sung hồ sơ, trích lại, mapping, kiểm, duyệt
    def bo_sung_ho_so(self, dang_nhap, ct_id, bo_sung: dict) -> dict:
        """Bổ sung khóa/profile/mapping cho đúng chứng từ CHO_KHOA/CHO_MAPPING rồi lập tiếp — không tạo raw/chứng từ lần 2, không đổi namespace."""
        dt = self.danh_tinh(dang_nhap)
        if not isinstance(bo_sung, dict) or not bo_sung or set(bo_sung) - set(BO_SUNG_KEYS):
            raise DataError("BO_SUNG_TRUONG_LA", "Chỉ bổ sung loại hình, loại bản, hợp đồng gốc, mã hợp đồng chung, ObjectID, mã dự án.")
        with self._tx(dt):
            ct = self.conn.execute("SELECT * FROM kho.chung_tu WHERE id = %s AND loai = %s FOR UPDATE", (ct_id, KIND)).fetchone()
            if not ct:
                raise DataError("HO_SO", "Không thấy hồ sơ (hoặc ngoài quyền).")
            quyen.kiem(dt, "BO_SUNG_HO_SO", ct["phap_nhan_id"])
            if self.conn.execute("SELECT 1 FROM master.hop_dong_phien_ban WHERE chung_tu_id = %s", (ct_id,)).fetchone():
                raise DataError("HO_SO_DA_LAP", "Hồ sơ đã thành hợp đồng/phiên bản; sửa mapping ở phiên bản chờ duyệt.")
            if not self.conn.execute("""SELECT 1 FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'kho.chung_tu' AND tham_chieu_id = %s AND loai = 'V4'
                                        AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')""", (ct_id,)).fetchone():
                raise DataError("HO_SO_KHONG_CHO_BO_SUNG", "Hồ sơ không ở trạng thái chờ khóa/mapping.")
            du_lieu = ct["du_lieu"]
            truoc = {k: du_lieu["envelope"].get(k) for k in BO_SUNG_KEYS}
            env = {**du_lieu["envelope"], **{k: (str(v).strip() or None) if v is not None else None for k, v in bo_sung.items()}}
            if env.get("loai_ban") not in (None, "GOC", "PHU_LUC"):
                raise DataError("BO_SUNG_TRUONG_LA", "loai_ban chỉ nhận GOC hoặc PHU_LUC.")
            profile = self._profile(ct["phap_nhan_id"], env["loai_hinh"])
            params = tham_so_typed(du_lieu["ket_qua_6"], profile["cau_hinh"], du_lieu.get("van_ban_nguon")) if profile else []
            du_lieu = {**du_lieu, "envelope": env, "tham_so_typed": params}
            self.conn.execute("UPDATE kho.chung_tu SET du_lieu = %s, cap_nhat_luc = now() WHERE id = %s", (json.dumps(du_lieu, ensure_ascii=False), ct_id))
            self._su_kien(ct["phap_nhan_id"], dt, "SUA_DANH_MUC", "kho.chung_tu", ct_id, "BO_SUNG_HO_SO", truoc=truoc, sau={k: env.get(k) for k in BO_SUNG_KEYS})
            self.conn.execute("""UPDATE kho.viec_can_duyet SET trang_thai = 'DONG', duyet_boi = %s, duyet_luc = now(), cap_nhat_luc = now()
                                 WHERE tham_chieu_bang = 'kho.chung_tu' AND tham_chieu_id = %s AND loai = 'V4' AND trang_thai = 'CHO_DUYET'""", (dt["dang_nhap"], ct_id))
            result = self._lap_ho_so(dt, ct["phap_nhan_id"], ct_id, du_lieu)
        return {"chung_tu_id": str(ct_id), **result}

    def doi_chieu_trich_lai(self, dang_nhap, ct_id) -> dict:
        """So bản trích lại (cùng Word) với phiên bản đang có: từng mã, giá trị, trích dẫn, căn cứ."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            ct, pb = self._trich_lai(dt, ct_id)
            cu = {r["ten"]: r for r in self.conn.execute("SELECT * FROM master.hop_dong_tham_so WHERE phien_ban_id = %s AND ke_thua_tu IS NULL", (pb["id"],))}
            moi, seen = {}, {}
            for p in ct["du_lieu"]["tham_so_typed"]:
                n = seen[p["ma"]] = seen.get(p["ma"], 0) + 1
                moi[p["ma"] if n == 1 else f"{p['ma']}#{n}"] = p
            rows = []
            for ten in sorted(set(cu) | set(moi)):
                a, b = cu.get(ten), moi.get(ten)
                ca = None if a is None else {"gia_tri_tho": a["gia_tri_tho"], "trich_dan": a["trich_dan"], "can_cu": a["trang_thai_can_cu"]}
                cb = None if b is None else {"gia_tri_tho": b["gia_tri_tho"], "trich_dan": b["trich_dan"], "can_cu": b["trang_thai_can_cu"]}
                rows.append({"ma": ten, "cu": ca, "moi": cb, "khac": ca != cb})
        return {"chung_tu_id": str(ct_id), "phien_ban_id": str(pb["id"]), "trang_thai_ban": pb["trang_thai"], "so_khac": sum(r["khac"] for r in rows),
                "dong": rows, "co_the_ap_dung": pb["trang_thai"] == "CHO_DUYET"}

    def _trich_lai(self, dt, ct_id):
        ct = self.conn.execute("SELECT * FROM kho.chung_tu WHERE id = %s AND loai = %s", (ct_id, KIND)).fetchone()
        if not ct:
            raise DataError("HO_SO", "Không thấy hồ sơ (hoặc ngoài quyền).")
        quyen.kiem(dt, "DOI_CHIEU_TRICH_LAI", ct["phap_nhan_id"])
        if not self.conn.execute("""SELECT 1 FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'kho.chung_tu' AND tham_chieu_id = %s AND loai = 'V3'
                                    AND trang_thai = 'CHO_DUYET'""", (ct_id,)).fetchone():
            raise DataError("KHONG_PHAI_TRICH_LAI_CHO", "Hồ sơ không phải bản trích lại đang chờ đối chiếu.")
        pb = self.conn.execute("""SELECT p.*, h.phap_nhan_id FROM master.hop_dong_phien_ban p JOIN kho.chung_tu c ON c.id = p.chung_tu_id JOIN master.hop_dong h ON h.id = p.hop_dong_id
                                  WHERE h.phap_nhan_id = %s AND c.du_lieu->>'word_khoa' = %s AND p.trang_thai <> 'THAY_THE' ORDER BY p.phien_ban DESC LIMIT 1""",
                               (ct["phap_nhan_id"], ct["du_lieu"]["word_khoa"])).fetchone()
        return ct, pb

    def xu_ly_trich_lai(self, dang_nhap, ct_id, hanh_dong: str, ly_do: str) -> dict:
        """GIU_BAN_CU: đóng việc, giữ phiên bản. AP_DUNG (chỉ khi bản đang chờ duyệt): bản cũ → THAY_THE có vết, phiên bản mới chờ duyệt
        từ bản trích lại (KT kiểm lại, CFO duyệt lại). Bản đã duyệt không bị thay bằng trích lại (cần phụ lục/điều chỉnh)."""
        dt = self.danh_tinh(dang_nhap)
        if hanh_dong not in ("GIU_BAN_CU", "AP_DUNG") or not ly_do or not str(ly_do).strip():
            raise DataError("TRICH_LAI_HANH_DONG", "Chọn Giữ bản cũ hoặc Áp dụng bản trích lại, kèm lý do.")
        with self._tx(dt):
            ct, pb = self._trich_lai(dt, ct_id)
            pn = ct["phap_nhan_id"]
            if hanh_dong == "GIU_BAN_CU":
                self._dong_viec("kho.chung_tu", ct_id, "DONG", dt)
                self._su_kien(pn, dt, "QUYET_DINH", "kho.chung_tu", ct_id, "TRICH_LAI_GIU_BAN_CU", ly_do=str(ly_do)[:500], can_cu={"phien_ban": str(pb["id"])})
                return {"ket_qua": "GIU_BAN_CU"}
            if pb["trang_thai"] != "CHO_DUYET":
                raise DataError("TRICH_LAI_BAN_DA_DUYET", "Bản đã duyệt không thay bằng bản trích lại; cần phụ lục hoặc điều chỉnh có căn cứ.")
            self._khoa_hop_dong(pb["hop_dong_id"])
            profile = self._profile(pn, lh_id=pb["loai_hinh_dt_id"])
            self.conn.execute("UPDATE master.hop_dong_phien_ban SET trang_thai = 'THAY_THE', ly_do = %s WHERE id = %s", (str(ly_do)[:500], pb["id"]))
            self._dong_viec("master.hop_dong_phien_ban", pb["id"], "DONG", dt)
            so = self.conn.execute("SELECT max(phien_ban) AS n FROM master.hop_dong_phien_ban WHERE hop_dong_id = %s", (pb["hop_dong_id"],)).fetchone()["n"]
            moi = self._tao_phien_ban(dt, pb["hop_dong_id"], so + 1, pb["loai"], ct_id, profile, ct["du_lieu"]["tham_so_typed"], pb["thay_cho_id"],
                                      pb["ngay_hieu_luc"].isoformat() if pb["ngay_hieu_luc"] else None, so_phu_luc=pb["so_phu_luc"],
                                      them={"thay_ban_trich": str(pb["id"])})
            chan = self.chan_phien_ban(moi)
            self._viec(pn, "V3", "master.hop_dong_phien_ban", moi, f"Phiên bản {so + 1} từ bản trích lại", [c["ma"] for c in chan])
            self._dong_viec("kho.chung_tu", ct_id, "DONG", dt)
            self._su_kien(pn, dt, "QUYET_DINH", "master.hop_dong_phien_ban", moi, "TRICH_LAI_AP_DUNG", ly_do=str(ly_do)[:500], truoc={"phien_ban": str(pb["id"])})
        return {"ket_qua": "AP_DUNG", "phien_ban_id": str(moi), "chan": chan}

    def cap_nhat_mapping(self, dang_nhap, pb_id, mapping: dict) -> dict:
        dt = self.danh_tinh(dang_nhap)
        if not isinstance(mapping, dict) or set(mapping) - {"doi_tac_object_id", "du_an"}:
            raise DataError("MAPPING_TRUONG_LA", "Mapping chỉ nhận ObjectID đối tác và mã dự án.")
        with self._tx(dt):
            pb0 = self.conn.execute("SELECT hop_dong_id FROM master.hop_dong_phien_ban WHERE id = %s", (pb_id,)).fetchone()
            if not pb0:
                raise DataError("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")
            hd = self._khoa_hop_dong(pb0["hop_dong_id"])
            pb = self._phan_tich_pb(pb_id)[0]
            quyen.kiem_tham_quyen(
                self.conn, "CRM:TIEP_NHAN:SUA", {"bang": "master.hop_dong", "id": str(pb["hop_dong_id"])},
                {"kiem_cu": lambda: quyen.kiem(dt, "MAPPING", pb["phap_nhan_id"]),
                 "khong_thay": ("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")})
            if pb["trang_thai"] != "CHO_DUYET" or pb["loai"] != "GOC" or hd["phien_ban_hien_hanh"] is not None:
                raise DataError("MAPPING_TRANG_THAI", "Chỉ mapping hợp đồng mới đang chờ duyệt.")
            doi_tac = self._map("master.doi_tac_ma_junsky", "object_id_junsky", "doi_tac_id", pb["phap_nhan_id"], mapping.get("doi_tac_object_id"))
            du_an = self._map("master.du_an", "ma_junsky", "id", pb["phap_nhan_id"], mapping.get("du_an"))
            if mapping.get("doi_tac_object_id") and doi_tac is None or mapping.get("du_an") and du_an is None:
                raise DataError("MAPPING_KHONG_CO_MA", "Mã không có trong danh mục của pháp nhân — tạo ở Junsky trước; không tự sinh mã.")
            new = (doi_tac or hd["doi_tac_id"], du_an or hd["du_an_id"])
            if new != (hd["doi_tac_id"], hd["du_an_id"]):
                self._vo_hieu_kiem(pb, dt, "Đổi mapping sau lần kiểm")
                self.conn.execute("UPDATE master.hop_dong SET doi_tac_id = %s, du_an_id = %s WHERE id = %s", (*new, hd["id"]))
            self._su_kien(pb["phap_nhan_id"], dt, "SUA_DANH_MUC", "master.hop_dong", hd["id"], "MAPPING",
                          truoc={"doi_tac_id": _s(hd["doi_tac_id"]), "du_an_id": _s(hd["du_an_id"])}, sau=mapping)
            chan = self.chan_phien_ban(pb_id)
            self._viec(pb["phap_nhan_id"], "V3", "master.hop_dong_phien_ban", pb_id, None, [c["ma"] for c in chan])
            return {"chan": chan}

    def xac_nhan_tham_so(self, dang_nhap, pb_id, ma: str, ly_do: str) -> dict:
        """Kế toán xác nhận thủ công rõ nghĩa một tham số SUY_RA/giá trị không có trong trích dẫn (ghi vết, vô hiệu lần kiểm cũ)."""
        dt = self.danh_tinh(dang_nhap)
        if not ly_do or not str(ly_do).strip():
            raise DataError("CAN_LY_DO", "Xác nhận thủ công cần lý do/căn cứ.")
        with self._tx(dt):
            pb0 = self.conn.execute("SELECT hop_dong_id FROM master.hop_dong_phien_ban WHERE id = %s", (pb_id,)).fetchone()
            if not pb0:
                raise DataError("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")
            self._khoa_hop_dong(pb0["hop_dong_id"])
            pb = self._phan_tich_pb(pb_id)[0]
            quyen.kiem_tham_quyen(
                self.conn, "CRM:TIEP_NHAN:KIEM", {"bang": "master.hop_dong", "id": str(pb["hop_dong_id"])},
                {"kiem_cu": lambda: quyen.kiem(dt, "KIEM_TRUOC", pb["phap_nhan_id"]),
                 "khong_thay": ("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")})
            n = self.conn.execute("""UPDATE master.hop_dong_tham_so SET xac_nhan_thu_cong = %s, gia_tri = gia_tri_tho WHERE phien_ban_id = %s AND ma_nguon = %s
                                     AND trang_thai_can_cu IN ('SUY_RA','GIA_TRI_KHONG_KHOP_TRICH_DAN')""",
                                  (_j({"boi": dt["dang_nhap"], "luc": now_utc(), "ly_do": str(ly_do)[:500]}), pb_id, ma)).rowcount
            if not n:
                raise DataError("THAM_SO_KHONG_CAN_XAC_NHAN", "Tham số không ở trạng thái cần xác nhận thủ công.")
            self._vo_hieu_kiem(pb, dt, "Xác nhận thủ công tham số " + ma)
            self._su_kien(pb["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb_id, "XAC_NHAN_THAM_SO", ly_do=str(ly_do)[:500], can_cu={"ma": ma})
            return {"chan": self.chan_phien_ban(pb_id)}

    def kiem_truoc(self, dang_nhap, pb_id, *, xac_nhan_can_cu_thu_cong: bool = False) -> dict:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            pb0 = self.conn.execute("SELECT hop_dong_id FROM master.hop_dong_phien_ban WHERE id = %s", (pb_id,)).fetchone()
            if not pb0:
                raise DataError("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")
            self._khoa_hop_dong(pb0["hop_dong_id"])
            pb = self._phan_tich_pb(pb_id)[0]
            quyen.kiem_tham_quyen(
                self.conn, "CRM:TIEP_NHAN:KIEM", {"bang": "master.hop_dong", "id": str(pb["hop_dong_id"])},
                {"kiem_cu": lambda: quyen.kiem(dt, "KIEM_TRUOC", pb["phap_nhan_id"]),
                 "khong_thay": ("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")})
            if pb["trang_thai"] != "CHO_DUYET":
                raise DataError("PHIEN_BAN_DA_CHOT", "Phiên bản không còn chờ duyệt.")
            if xac_nhan_can_cu_thu_cong:
                self.conn.execute("UPDATE master.hop_dong_phien_ban SET tham_so = tham_so || %s WHERE id = %s",
                                  (_j({"xac_nhan_can_cu_thu_cong": {"boi": dt["dang_nhap"], "luc": now_utc()}}), pb_id))
            chan = self._phan_tich_pb(pb_id)[3]
            if chan:
                raise DataError("CRM_CHUA_DU_DIEU_KIEN", "Chưa thể kiểm xong: " + "; ".join(c["thong_diep"] for c in chan))
            self.conn.execute("UPDATE master.hop_dong_phien_ban SET kiem_boi = %s, kiem_luc = now(), kiem_van_tay = master.crm_van_tay_phien_ban(id) WHERE id = %s",
                              (dt["dang_nhap"], pb_id))
            self.conn.execute("""UPDATE kho.viec_can_duyet SET kiem_boi = %s, kiem_luc = now(), ly_do_cho = '{}' WHERE tham_chieu_id IN (%s, %s)
                                 AND trang_thai = 'CHO_DUYET'""", (dt["dang_nhap"], pb_id, pb["hop_dong_id"]))
            self._su_kien(pb["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb_id, "KIEM_TRUOC", sau={"thu_cong": xac_nhan_can_cu_thu_cong})
        return {"kiem_boi": dt["dang_nhap"]}

    def duyet_v4(self, dang_nhap, hd_id) -> dict:
        """CFO có quyền V4 hoàn tất việc V4 (hợp đồng/danh mục mới) — tách khỏi quyền V3 tham số."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            hd = self._khoa_hop_dong(hd_id)
            self._kiem_mtq_duyet(dt, "DUYET_V4", hd["id"], hd["phap_nhan_id"])
            open_v4 = self.conn.execute("""SELECT id, ly_do_cho FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'master.hop_dong' AND tham_chieu_id = %s AND loai = 'V4'
                                           AND trang_thai = 'CHO_DUYET'""", (hd_id,)).fetchone()
            if not open_v4:
                raise DataError("KHONG_CO_VIEC_V4", "Không có việc V4 đang chờ của hợp đồng này.")
            if hd["doi_tac_id"] is None or hd["du_an_id"] is None:
                raise DataError("CRM_CHUA_DU_DIEU_KIEN", "Hợp đồng mới chưa đủ mapping đối tác/dự án.")
            self._dong_viec("master.hop_dong", hd_id, "DA_DUYET", dt, loai="V4")
            self._su_kien(hd["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong", hd_id, "DUYET_V4")
        return {"v4": "DA_DUYET"}

    def duyet(self, dang_nhap, pb_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            pb0 = self.conn.execute("SELECT hop_dong_id FROM master.hop_dong_phien_ban WHERE id = %s", (pb_id,)).fetchone()
            if not pb0:
                raise DataError("PHIEN_BAN", "Không thấy phiên bản hợp đồng (hoặc ngoài quyền).")
            self._khoa_hop_dong(pb0["hop_dong_id"])  # serialize với nối tiền cùng hợp đồng; tính lại kế hoạch SAU khi khóa
            pb, _, th, chan, plan = self._phan_tich_pb(pb_id)
            qd = self._kiem_mtq_duyet(dt, "DUYET", pb["hop_dong_id"], pb["phap_nhan_id"], pb_id=pb["id"])
            if pb["trang_thai"] != "CHO_DUYET":
                raise DataError("PHIEN_BAN_DA_CHOT", "Phiên bản không còn chờ duyệt.")
            if pb["kiem_luc"] is None:
                raise DataError("CHUA_KIEM_TRUOC", "Kế toán chưa kiểm trước (hoặc lần kiểm đã hết hiệu lực do nội dung/mapping đổi).")
            if chan:
                raise DataError("CRM_CHUA_DU_DIEU_KIEN", "Chưa thể duyệt: " + "; ".join(c["thong_diep"] for c in chan))
            pn = pb["phap_nhan_id"]
            if pb["loai"] == "GOC" and self.conn.execute("""SELECT 1 FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'master.hop_dong' AND tham_chieu_id = %s
                                                            AND loai = 'V4' AND trang_thai = 'CHO_DUYET'""", (pb["hop_dong_id"],)).fetchone():
                if qd["nguon"] == "CU" and not quyen.duoc(dt, "DUYET_V4", pn):
                    raise DataError("KHONG_CO_QUYEN_LOAI_VIEC", "Hợp đồng mới còn việc V4 — cần người có quyền V4 duyệt trước hoặc cùng lúc.")
                self._dong_viec("master.hop_dong", pb["hop_dong_id"], "DA_DUYET", dt, loai="V4")
                self._su_kien(pn, dt, "QUYET_DINH", "master.hop_dong", pb["hop_dong_id"], "DUYET_V4")
            hieu_luc = pb["ngay_hieu_luc"]
            self.conn.execute("""UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET', nguoi_duyet = %s, duyet_luc = now(),
                                 valid_from = coalesce(%s::date::timestamp AT TIME ZONE 'UTC', now()) WHERE id = %s""", (dt["dang_nhap"], hieu_luc, pb_id))
            if pb["thay_cho_id"]:  # mốc ngày lưu theo nửa đêm UTC — cùng quy ước với master.phien_ban_hieu_luc
                self.conn.execute("UPDATE master.hop_dong_phien_ban SET valid_to = coalesce(%s::date::timestamp AT TIME ZONE 'UTC', now()) WHERE id = %s",
                                  (hieu_luc, pb["thay_cho_id"]))
            rows = th["lich"] if plan is None else [dict(p["dong"], thay_cho=p.get("thay_cho")) for p in plan if p["hanh_dong"] != "BO"]
            for r in rows:
                self.conn.execute("""INSERT INTO master.lich_thu (phien_ban_id, phap_nhan_id, dot, moc, so_tien_minor, tien_te, han, loai, khoa_nghia_vu, thay_cho_id, nguon_tham_so, co_so)
                                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                  (pb_id, pn, r["dot"], r["moc"], r["so_tien_minor"], r["tien_te"], _d(r["han"]), r["loai"], r["khoa"], r.get("thay_cho"),
                                   r["nguon_tham_so"], r["co_so"]))
            total = th["fields"].get("gia_tri_hop_dong")
            self.conn.execute("""UPDATE master.hop_dong SET phien_ban_hien_hanh = %s, trang_thai = 'HIEU_LUC',
                                 gia_tri_minor = coalesce(%s, gia_tri_minor) WHERE id = %s""", (pb_id, total["minor"] if total else None, pb["hop_dong_id"]))
            self._cap_nhat_trang_thai_lich(pb["hop_dong_id"])
            self._dong_viec("master.hop_dong_phien_ban", pb_id, "DA_DUYET", dt, loai="V3")
            self._su_kien(pn, dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb_id, "DUYET_V3",
                          sau={"so_dot": len(rows), "hieu_luc_tu": hieu_luc.isoformat() if hieu_luc else None,
                               "ke_hoach_phu_luc": plan and [{k: v for k, v in p.items() if k != "dong"} for p in plan]}, can_cu={"so_tong": th["so_tong"]})
            return {"so_dot": len(rows), "hieu_luc_tu": hieu_luc.isoformat() if hieu_luc else None,
                    "ke_hoach": plan and [{"khoa": p["khoa"], "hanh_dong": p["hanh_dong"]} for p in plan]}

    def tu_choi(self, dang_nhap, pb_id, ly_do: str) -> dict:
        dt = self.danh_tinh(dang_nhap)
        if not ly_do or not str(ly_do).strip():
            raise DataError("CAN_LY_DO", "Từ chối cần lý do.")
        with self._tx(dt):
            pb = self._phan_tich_pb(pb_id)[0]
            self._kiem_mtq_duyet(dt, "DUYET", pb["hop_dong_id"], pb["phap_nhan_id"], pb_id=pb["id"])
            self.conn.execute("UPDATE master.hop_dong_phien_ban SET trang_thai = 'TU_CHOI', nguoi_duyet = %s, duyet_luc = now(), ly_do = %s WHERE id = %s",
                              (dt["dang_nhap"], str(ly_do)[:500], pb_id))
            self._dong_viec("master.hop_dong_phien_ban", pb_id, "BO_QUA", dt)
            self._su_kien(pb["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb_id, "TU_CHOI", ly_do=str(ly_do)[:500])
        return {"trang_thai": "TU_CHOI"}

    # ------------------------------------------------------------------ tiền (từ M1 qua bộ chiếu) và liên kết đợt
    def kiem_nhan_tien(self, dang_nhap, pn_ma: str) -> str:
        dt = self.danh_tinh(dang_nhap)
        pn = self._pn(pn_ma)
        quyen.kiem(dt, "NHAN_TIEN", pn)
        return pn

    def fact_hop_dong_m1(self, dang_nhap, pn_ma: str) -> dict:
        """Fact hợp đồng/lịch ĐÃ DUYỆT theo đối tượng Junsky của pháp nhân, cho context engine M1 (TL32 §3.2). Mỗi phiên bản đã duyệt
        một fact có khoảng hiệu lực [valid_from, valid_to) theo ngày UTC; phần còn phải thu theo chuỗi khóa nghĩa vụ (link đã nối hiện tại).
        Đọc bằng quyền người thao tác (XEM CRM + RLS); không ghi gì."""
        dt = self.danh_tinh(dang_nhap)
        pn = self._pn(pn_ma)
        quyen.kiem(dt, "XEM", pn)
        out: dict[str, list[dict]] = {}
        with self._tx(dt):
            for v in self.conn.execute("""SELECT p.id, p.phien_ban, p.hop_dong_id, p.nguoi_duyet, p.duyet_luc, p.tham_so, (p.valid_from AT TIME ZONE 'UTC')::date AS tu,
                                                 (p.valid_to AT TIME ZONE 'UTC')::date AS den, h.ma_noi_bo, h.so_hop_dong, h.tien_te, d.object_id_junsky, a.ma_junsky AS du_an
                                          FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id
                                          JOIN master.doi_tac_ma_junsky d ON d.doi_tac_id = h.doi_tac_id AND d.phap_nhan_id = h.phap_nhan_id AND d.valid_to IS NULL
                                          LEFT JOIN master.du_an a ON a.id = h.du_an_id
                                          WHERE h.phap_nhan_id = %s AND p.trang_thai = 'DA_DUYET' ORDER BY h.ma_noi_bo, p.phien_ban""", (pn,)).fetchall():
                dot = [{"lich_id": str(l["id"]), "khoa": l["khoa_nghia_vu"], "loai": l["loai"], "dot": l["dot"], "han": l["han"].isoformat() if l["han"] else None,
                        "moc": l["moc"], "so_tien_minor": l["so_tien_minor"], "con_lai_minor": max(0, l["so_tien_minor"] - int(l["da_lk"] or 0))}
                       for l in self.conn.execute("""SELECT l.*, master.crm_da_lien_ket(%s, l.khoa_nghia_vu) AS da_lk FROM master.lich_thu l
                                                     WHERE l.phien_ban_id = %s ORDER BY l.loai, l.dot""", (v["hop_dong_id"], v["id"]))]
                out.setdefault(v["object_id_junsky"], []).append({
                    "hop_dong_id": str(v["hop_dong_id"]), "phien_ban_id": str(v["id"]), "hieu_luc_tu": v["tu"].isoformat(),
                    "hieu_luc_den": v["den"].isoformat() if v["den"] else None, "currency": v["tien_te"].strip(), "tai_khoan": TK_PHAI_THU_HOP_DONG,
                    "du_an": v["du_an"], "dot": dot,
                    "provenance": {"nguon": "K2_CRM", "ma_noi_bo": v["ma_noi_bo"], "so_hop_dong": v["so_hop_dong"], "phien_ban": v["phien_ban"],
                                   "profile": (v["tham_so"] or {}).get("profile"), "nguoi_duyet": v["nguoi_duyet"],
                                   "duyet_luc": v["duyet_luc"].isoformat() if v["duyet_luc"] else None, "quy_tac": QUY_TAC_TIEN_VE}})
        return out

    def lien_ket(self, dang_nhap, tien_id, lich_id, so_tien, khoa: str) -> dict:
        dt = self.danh_tinh(dang_nhap)
        if not isinstance(khoa, str) or not khoa or len(khoa) > 120:
            raise DataError("KHOA_IDEMPOTENCY", "Cần khóa idempotency của thao tác.")
        try:
            so_tien = int(str(so_tien))
        except ValueError as exc:
            raise DataError("SO_TIEN", "Số tiền nối phải là số nguyên VND.") from exc
        with self._tx(dt):
            lich0 = self.conn.execute("SELECT l.phap_nhan_id, p.hop_dong_id FROM master.lich_thu l JOIN master.hop_dong_phien_ban p ON p.id = l.phien_ban_id WHERE l.id = %s",
                                      (lich_id,)).fetchone()
            if not lich0:
                raise DataError("LIEN_KET_THAM_CHIEU", "Không thấy khoản tiền hoặc đợt (hoặc ngoài quyền).")
            quyen.kiem(dt, "LIEN_KET_TIEN", lich0["phap_nhan_id"])  # quyền trước mọi nhánh, kể cả trả kết quả lặp
            self._khoa_hop_dong(lich0["hop_dong_id"])  # hai lần thử đồng thời cùng hợp đồng xếp hàng tại đây
            old = self.conn.execute("SELECT * FROM kho.lien_ket_chung_tu WHERE khoa_idempotency = %s", (khoa,)).fetchone()
            if old:
                return self._ket_qua_lap(old, tien_id, lich_id, so_tien)
            tien = self.conn.execute("SELECT id, phap_nhan_id FROM kho.chung_tu WHERE id = %s AND loai = 'SAO_KE'", (tien_id,)).fetchone()
            lich = self.conn.execute("""SELECT l.*, p.chung_tu_id AS ct_pb, p.hop_dong_id FROM master.lich_thu l JOIN master.hop_dong_phien_ban p ON p.id = l.phien_ban_id
                                        WHERE l.id = %s""", (lich_id,)).fetchone()
            if not tien or tien["phap_nhan_id"] != lich["phap_nhan_id"]:
                raise DataError("LIEN_KET_THAM_CHIEU", "Không thấy khoản tiền hoặc đợt (hoặc ngoài quyền).")
            hieu_luc = self.conn.execute("SELECT master.crm_phien_ban_hieu_luc(%s, %s) AS v", (lich["hop_dong_id"], self.hom_nay())).fetchone()["v"]
            if lich["phien_ban_id"] != hieu_luc:
                raise DataError("LICH_KHONG_HIEU_LUC", "Chỉ nối tiền vào đợt của phiên bản đang hiệu lực hôm nay.")
            if self.conn.execute("SELECT 1 FROM kho.lien_ket_chung_tu WHERE chung_tu_a_id = %s AND lich_thu_id = %s AND trang_thai <> 'HUY'", (tien_id, lich_id)).fetchone():
                raise DataError("LIEN_KET_DA_CO", "Khoản tiền đã nối đợt này; gỡ liên kết cũ trước nếu cần đổi số.")
            lk = self.conn.execute("""INSERT INTO kho.lien_ket_chung_tu (phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai, so_tien_khop_minor, tien_te, trang_thai,
                                      nguon_suy_luan, nguoi_duyet, duyet_luc, lich_thu_id, hop_dong_id, khoa_idempotency, tao_boi)
                                      VALUES (%s,%s,%s,'HOP_DONG_DOT_TIEN',%s,%s,'DA_KHOP','NGUOI',%s,now(),%s,%s,%s,%s)
                                      ON CONFLICT (khoa_idempotency) WHERE khoa_idempotency IS NOT NULL DO NOTHING RETURNING id""",
                                   (tien["phap_nhan_id"], tien_id, lich["ct_pb"], so_tien, lich["tien_te"], dt["dang_nhap"], lich_id, lich["hop_dong_id"], khoa,
                                    dt["dang_nhap"])).fetchone()
            if lk is None:  # cùng khóa từ hợp đồng khác đã ghi xong trước: trả đúng kết quả hoặc từ chối nếu khác nội dung
                return self._ket_qua_lap(self.conn.execute("SELECT * FROM kho.lien_ket_chung_tu WHERE khoa_idempotency = %s", (khoa,)).fetchone(),
                                         tien_id, lich_id, so_tien)
            self._cap_nhat_trang_thai_lich(lich["hop_dong_id"])
            self._su_kien(tien["phap_nhan_id"], dt, "QUYET_DINH", "kho.lien_ket_chung_tu", lk["id"], "XAC_NHAN_LK",
                          sau={"tien": str(tien_id), "lich": str(lich_id), "so_tien": str(so_tien), "khoa": khoa})
            return {"lien_ket_id": str(lk["id"]), "lap_lai": False, "trang_thai": "DA_KHOP"}

    @staticmethod
    def _ket_qua_lap(old, tien_id, lich_id, so_tien):
        """Cùng khóa thao tác: cùng nội dung → trả đúng liên kết đã ghi (kể cả đã hủy sau đó — không tự tạo lại); khác nội dung → từ chối."""
        if old is None or (str(old["chung_tu_a_id"]), str(old["lich_thu_id"]), old["so_tien_khop_minor"]) != (str(tien_id), str(lich_id), so_tien):
            raise DataError("IDEMPOTENCY_KHAC", "Khóa thao tác đã dùng cho liên kết khác.")
        return {"lien_ket_id": str(old["id"]), "lap_lai": True, "trang_thai": old["trang_thai"]}

    def go_lien_ket(self, dang_nhap, lk_id, ly_do: str) -> dict:
        dt = self.danh_tinh(dang_nhap)
        if not ly_do or not str(ly_do).strip():
            raise DataError("CAN_LY_DO", "Gỡ liên kết cần lý do.")
        with self._tx(dt):
            lk = self.conn.execute("SELECT * FROM kho.lien_ket_chung_tu WHERE id = %s", (lk_id,)).fetchone()
            if not lk:
                raise DataError("LIEN_KET", "Không thấy liên kết (hoặc ngoài quyền).")
            quyen.kiem(dt, "LIEN_KET_TIEN", lk["phap_nhan_id"])
            if lk["hop_dong_id"]:
                self._khoa_hop_dong(lk["hop_dong_id"])
            if lk["trang_thai"] == "HUY":
                return {"da_huy": True, "lap_lai": True}
            self.conn.execute("UPDATE kho.lien_ket_chung_tu SET trang_thai = 'HUY', huy_luc = now(), huy_boi = %s, ly_do_huy = %s WHERE id = %s",
                              (dt["dang_nhap"], str(ly_do)[:500], lk_id))
            if lk["hop_dong_id"]:
                self._cap_nhat_trang_thai_lich(lk["hop_dong_id"])
            self._su_kien(lk["phap_nhan_id"], dt, "QUYET_DINH", "kho.lien_ket_chung_tu", lk_id, "GO_LK", ly_do=str(ly_do)[:500])
        return {"da_huy": True, "lap_lai": False}

    def _cap_nhat_trang_thai_lich(self, hd):
        """Trạng thái thu theo chuỗi khóa nghĩa vụ (hàm CSDL, không phụ thuộc RLS của người thao tác); đợt cũ giữ link, không cộng hai lịch."""
        for r in self.conn.execute("""SELECT l.id, l.so_tien_minor, master.crm_da_lien_ket_dong(l.id) AS rieng, master.crm_da_lien_ket(%s, l.khoa_nghia_vu) AS chuoi
                                      FROM master.lich_thu l JOIN master.hop_dong_phien_ban p ON p.id = l.phien_ban_id WHERE p.hop_dong_id = %s""", (hd, hd)).fetchall():
            tt = "DA_THU" if r["chuoi"] >= r["so_tien_minor"] else "MOT_PHAN" if r["chuoi"] > 0 else "CHUA_THU"
            self.conn.execute("UPDATE master.lich_thu SET da_thu_minor = %s, trang_thai = %s WHERE id = %s AND (da_thu_minor, trang_thai) IS DISTINCT FROM (%s, %s)",
                              (int(r["rieng"]), tt, r["id"], int(r["rieng"]), tt))

    # ------------------------------------------------------------------ file soát CRM / lịch nghĩa vụ (export chung + sổ đăng ký lô)
    def xuat_file_soat(self, dang_nhap, hd_id) -> dict:
        from ..xuat import excel
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            hd = self.conn.execute("SELECT h.*, p.ma AS pn_ma FROM master.hop_dong h JOIN master.phap_nhan p ON p.id = h.phap_nhan_id WHERE h.id = %s", (hd_id,)).fetchone()
            if not hd:
                raise DataError("HOP_DONG", "Không thấy hợp đồng (hoặc ngoài quyền).")
            quyen.kiem(dt, "XUAT_FILE_SOAT", hd["phap_nhan_id"])
            versions = self.conn.execute("SELECT * FROM master.hop_dong_phien_ban WHERE hop_dong_id = %s ORDER BY phien_ban", (hd_id,)).fetchall()
            hieu_luc = self.conn.execute("SELECT master.crm_phien_ban_hieu_luc(%s, %s) AS v", (hd_id, self.hom_nay())).fetchone()["v"]
            tien = lambda v: None if v is None else (v if abs(v) < EXCEL_SO_CHINH_XAC else str(v))
            hop_dong_rows = [[hd["pn_ma"], hd["ma_noi_bo"], hd["so_hop_dong"], hd["loai"], tien(hd["gia_tri_minor"]), hd["tien_te"], v["phien_ban"], v["loai"],
                              v["so_phu_luc"], v["trang_thai"], v["ngay_hieu_luc"].isoformat() if v["ngay_hieu_luc"] else None, "CÓ" if v["id"] == hieu_luc else "",
                              v["kiem_boi"], v["nguoi_duyet"], (v["tham_so"] or {}).get("profile", {}).get("ma"), (v["tham_so"] or {}).get("profile", {}).get("phien_ban")]
                             for v in versions]
            lich_rows, ts_rows = [], []
            for v in versions:
                for l in self.conn.execute("SELECT * FROM master.lich_thu WHERE phien_ban_id = %s ORDER BY loai, dot", (v["id"],)):
                    lich_rows.append([v["phien_ban"], l["khoa_nghia_vu"], l["loai"], l["dot"], tien(l["so_tien_minor"]), l["tien_te"], l["han"].isoformat() if l["han"] else None,
                                      l["moc"], l["co_so"], l["trang_thai"], tien(l["da_thu_minor"]), ",".join(l["nguon_tham_so"]), "CÓ" if v["id"] == hieu_luc else ""])
                for t in self.conn.execute("SELECT * FROM master.hop_dong_tham_so WHERE phien_ban_id = %s ORDER BY ten", (v["id"],)):
                    ts_rows.append([v["phien_ban"], t["ma_nguon"], t["truong"], t["gia_tri_tho"], t["gia_tri"], t["don_vi"], t["trang_thai_can_cu"], t["trich_dan"],
                                    t["dieu_khoan"], "kế thừa" if t["ke_thua_tu"] else ""])
            wb = excel.workbook()
            excel.table(wb, "HOP_DONG_PHIEN_BAN", ["phap_nhan", "ma_hd_chung", "so_hop_dong", "loai", "gia_tri", "tien_te", "phien_ban", "loai_ban", "so_phu_luc",
                                                   "trang_thai", "ngay_hieu_luc", "hieu_luc_hom_nay", "ke_toan_kiem", "cfo_duyet", "profile", "profile_phien_ban"], hop_dong_rows)
            excel.table(wb, "LICH_NGHIA_VU", ["phien_ban", "khoa_nghia_vu", "loai", "dot", "so_tien", "tien_te", "han", "moc", "co_so", "trang_thai_thu",
                                              "da_thu_dot_nay", "tham_so_nguon", "hieu_luc_hom_nay"], lich_rows)
            excel.table(wb, "THAM_SO_CAN_CU", ["phien_ban", "ma", "truong", "gia_tri_nguon", "gia_tri_hieu_luc", "don_vi", "can_cu", "trich_dan", "dieu_khoan", "ghi_chu"], ts_rows)
            excel.table(wb, "CANH_BAO", ["noi_dung"], [["DEMO — dữ liệu mô phỏng"], ["Hồ sơ hợp đồng và lịch nghĩa vụ thu — KHÔNG phải phiếu thu/chi, KHÔNG phải file nhập Junsky"],
                                                       ["Không chứa bút toán doanh thu/VAT/giá vốn"], ["Số tiền từ 10^15 trở lên ghi dạng chữ để giữ đủ chữ số"]])
            raw = excel.to_bytes(wb)
            digest = sha256(raw)
            ma_lo = f"CRM-{hd['ma_noi_bo']}-{digest[:12]}"
            old = self.conn.execute("SELECT id, du_lieu FROM kho.lo_xuat WHERE ma_lo = %s", (ma_lo,)).fetchone()
            if old:
                return {"id": str(old["id"]), "ten": old["du_lieu"]["ten"], "sha256": digest, "lap_lai": True}
            write_immutable(self.root / "crm-xuat" / f"{digest}.xlsx", raw)
            ten = f"FILE-SOAT-CRM-{hd['ma_noi_bo']}-{digest[:8]}.xlsx"
            lo = self.conn.execute("""INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, duong_dan, hash, so_dong, nguoi, xuat_luc, trang_thai, du_lieu)
                                      VALUES (%s,%s,%s,'FILE_SOAT',%s,%s,%s,%s,now(),'DA_XUAT',%s) RETURNING id""",
                                   (hd["phap_nhan_id"], self.hom_nay().strftime("%Y-%m"), ma_lo, f"crm-xuat/{digest}.xlsx", digest, len(lich_rows), dt["dang_nhap"],
                                    _j({"module": MODULE, "loai": "LICH_NGHIA_VU", "hop_dong_id": str(hd_id), "ten": ten}))).fetchone()
            self._su_kien(hd["phap_nhan_id"], dt, "LO", "kho.lo_xuat", lo["id"], "XUAT_FILE_SOAT_CRM", sau={"sha256": digest, "so_dot": len(lich_rows)})
        return {"id": str(lo["id"]), "ten": ten, "sha256": digest, "lap_lai": False}

    def tep_file_soat(self, dang_nhap, lo_id) -> tuple[str, bytes]:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            lo = self.conn.execute("SELECT * FROM kho.lo_xuat WHERE id = %s AND du_lieu->>'module' = %s", (lo_id, MODULE)).fetchone()
            if not lo:
                raise DataError("FILE_SOAT", "Không thấy file soát CRM (hoặc ngoài quyền).")
            quyen.kiem(dt, "XUAT_FILE_SOAT", lo["phap_nhan_id"])
        path = (self.root / lo["duong_dan"]).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise DataError("FILE_SOAT", "Đường dẫn file soát không hợp lệ.")
        raw = path.read_bytes()
        if sha256(raw) != lo["hash"]:
            raise DataError("ARTIFACT_CHANGED", "File soát đã bị thay đổi.")
        return lo["du_lieu"]["ten"], raw

    # ------------------------------------------------------------------ tra cứu (quyền XEM/module + RLS)
    def danh_sach(self, dang_nhap) -> dict:
        dt = self.danh_tinh(dang_nhap)
        pns = quyen.pham_vi(dt, "XEM")
        if not pns:
            raise DataError("KHONG_CO_QUYEN_MODULE", "Người dùng không có quyền xem CRM trên pháp nhân nào.")
        pns_tien = quyen.pham_vi(dt, "XEM_TIEN")
        today = self.hom_nay()
        with self._tx(dt):
            ho_so = [{"id": str(r["id"]), "phap_nhan": r["ma"], "khoa": r["khoa_nguon"], "hash": r["hash"], "envelope": r["du_lieu"]["envelope"],
                      "tham_chieu_file": r["du_lieu"].get("tham_chieu_file"), "che_do": r["du_lieu"]["ket_qua_6"].get("che_do"),
                      "viec": [self._viec_view(v) for v in self.conn.execute("SELECT * FROM kho.viec_can_duyet WHERE tham_chieu_id = %s ORDER BY tao_luc", (r["id"],))]}
                     for r in self.conn.execute("""SELECT c.id, c.khoa_nguon, c.hash, c.du_lieu, p.ma FROM kho.chung_tu c JOIN master.phap_nhan p ON p.id = c.phap_nhan_id
                                                   WHERE c.loai = 'HOP_DONG_TEP' AND c.phap_nhan_id = ANY(%s::uuid[]) ORDER BY c.tao_luc""", (pns,))]
            hop_dong = []
            for h in self.conn.execute("""SELECT h.*, p.ma AS pn_ma, d.object_id_junsky, a.ma_junsky AS du_an_ma, master.crm_phien_ban_hieu_luc(h.id, %s) AS hieu_luc
                                          FROM master.hop_dong h JOIN master.phap_nhan p ON p.id = h.phap_nhan_id
                                          LEFT JOIN master.doi_tac_ma_junsky d ON d.doi_tac_id = h.doi_tac_id AND d.phap_nhan_id = h.phap_nhan_id
                                          LEFT JOIN master.du_an a ON a.id = h.du_an_id WHERE h.phap_nhan_id = ANY(%s::uuid[]) AND h.loai <> 'VAY'
                                          ORDER BY h.tao_luc""", (today, pns)).fetchall():  # HĐ VAY thuộc M9 (domain dispatch), không qua parser doanh thu
                versions = []
                xem_tien = str(h["phap_nhan_id"]) in pns_tien
                for pb in self.conn.execute("SELECT * FROM master.hop_dong_phien_ban WHERE hop_dong_id = %s ORDER BY phien_ban", (h["id"],)).fetchall():
                    _, rows, th, chan, _ = self._phan_tich_pb(pb["id"])
                    lich = []
                    for l in self.conn.execute("SELECT * FROM master.lich_thu WHERE phien_ban_id = %s ORDER BY loai, dot", (pb["id"],)).fetchall():
                        links = [{"id": str(k["id"]), "tien": str(k["chung_tu_a_id"]), "so_tien": _s(k["so_tien_khop_minor"]), "trang_thai": k["trang_thai"],
                                  "ly_do_huy": k["ly_do_huy"]} for k in self.conn.execute("SELECT * FROM kho.lien_ket_chung_tu WHERE lich_thu_id = %s ORDER BY tao_luc", (l["id"],))] \
                            if xem_tien else []
                        lich.append({"id": str(l["id"]), "khoa": l["khoa_nghia_vu"], "loai": l["loai"], "dot": l["dot"], "so_tien": _s(l["so_tien_minor"]),
                                     "tien_te": l["tien_te"], "han": l["han"].isoformat() if l["han"] else None, "moc": l["moc"], "co_so": l["co_so"],
                                     "trang_thai": l["trang_thai"], "da_thu": _s(l["da_thu_minor"]), "thay_cho": _s(l["thay_cho_id"]),
                                     "nguon_tham_so": list(l["nguon_tham_so"]), "lien_ket": links})
                    versions.append({"id": str(pb["id"]), "phien_ban": pb["phien_ban"], "loai": pb["loai"], "so_phu_luc": pb["so_phu_luc"], "trang_thai": pb["trang_thai"],
                                     "ngay_hieu_luc": pb["ngay_hieu_luc"].isoformat() if pb["ngay_hieu_luc"] else None, "kiem_boi": pb["kiem_boi"],
                                     "hieu_luc_hom_nay": pb["id"] == h["hieu_luc"], "sap_hieu_luc": pb["trang_thai"] == "DA_DUYET" and pb["ngay_hieu_luc"] is not None and pb["ngay_hieu_luc"] > today,
                                     "nguoi_duyet": pb["nguoi_duyet"], "thay_cho": _s(pb["thay_cho_id"]), "nguon": pb["nguon"], "profile": (pb["tham_so"] or {}).get("profile"),
                                     "chan": chan if pb["trang_thai"] == "CHO_DUYET" else [],
                                     "lich_du_kien": [{**r, "so_tien_minor": _s(r["so_tien_minor"])} for r in th["lich"]] if pb["trang_thai"] == "CHO_DUYET" else [],
                                     "tham_so": [self._tham_so_view(r) for r in rows], "lich": lich})
                v4 = self.conn.execute("""SELECT trang_thai FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'master.hop_dong' AND tham_chieu_id = %s AND loai = 'V4'
                                          ORDER BY tao_luc DESC LIMIT 1""", (h["id"],)).fetchone()
                hop_dong.append({"id": str(h["id"]), "phap_nhan": h["pn_ma"], "loai": h["loai"], "ma_noi_bo": h["ma_noi_bo"], "so_hop_dong": h["so_hop_dong"],
                                 "doi_tac_object_id": h["object_id_junsky"], "du_an": h["du_an_ma"], "gia_tri": _s(h["gia_tri_minor"]), "tien_te": h["tien_te"],
                                 "trang_thai": h["trang_thai"], "hien_hanh": _s(h["phien_ban_hien_hanh"]), "hieu_luc_hom_nay": _s(h["hieu_luc"]),
                                 "v4": v4["trang_thai"] if v4 else None, "phien_ban": versions})
            tien = [{"id": str(r["id"]), "phap_nhan": r["ma"], "khoa": r["khoa_nguon"], "tham_chieu": r["du_lieu"].get("reference"), "ngay": r["ngay_nghiep_vu"].isoformat(),
                     "so_tien": _s(r["so_tien_minor"]), "tien_te": r["tien_te"], "mo_ta": r["mo_ta"], "da_noi": _s(r["da_noi"]), "so_de_xuat": r["so_dx"],
                     "nguon_m1": "_sqlite_id" in r["du_lieu"]}
                    for r in self.conn.execute("""SELECT c.*, p.ma, (SELECT coalesce(sum(k.so_tien_khop_minor), 0) FROM kho.lien_ket_chung_tu k
                                                                     WHERE k.chung_tu_a_id = c.id AND k.trang_thai <> 'HUY') AS da_noi,""" + """
                                                   (SELECT count(*) FROM kho.de_xuat x WHERE x.chung_tu_id = c.id) AS so_dx
                                                   FROM kho.chung_tu c JOIN master.phap_nhan p ON p.id = c.phap_nhan_id
                                                   WHERE c.loai = 'SAO_KE' AND c.chieu = 'THU' AND c.phap_nhan_id = ANY(%s::uuid[]) ORDER BY c.ngay_nghiep_vu, c.khoa_nguon""", (pns_tien,))] \
                if pns_tien else []
            file_soat = [{"id": str(r["id"]), "phap_nhan": r["ma"], "ten": r["du_lieu"]["ten"], "hop_dong_id": r["du_lieu"]["hop_dong_id"], "luc": r["xuat_luc"].isoformat()}
                         for r in self.conn.execute("""SELECT l.*, p.ma FROM kho.lo_xuat l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                                                       WHERE l.du_lieu->>'module' = 'CRM' AND l.phap_nhan_id = ANY(%s::uuid[]) ORDER BY l.xuat_luc DESC""", (pns,))]
            danh_muc = {"doi_tac": [dict(phap_nhan=r["ma"], object_id=r["object_id_junsky"]) for r in self.conn.execute(
                            "SELECT p.ma, d.object_id_junsky FROM master.doi_tac_ma_junsky d JOIN master.phap_nhan p ON p.id = d.phap_nhan_id WHERE d.valid_to IS NULL AND d.phap_nhan_id = ANY(%s::uuid[]) ORDER BY 1, 2", (pns,))],
                        "du_an": [dict(phap_nhan=r["ma"], ma=r["ma_junsky"]) for r in self.conn.execute(
                            "SELECT p.ma, a.ma_junsky FROM master.du_an a JOIN master.phap_nhan p ON p.id = a.phap_nhan_id WHERE a.valid_to IS NULL AND a.phap_nhan_id = ANY(%s::uuid[]) ORDER BY 1, 2", (pns,))],
                        "loai_hinh": [dict(phap_nhan=r["ma"], ma=r["lh"]) for r in self.conn.execute(
                            "SELECT p.ma, l.ma AS lh FROM master.loai_hinh_doanh_thu l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id WHERE l.valid_to IS NULL AND l.phap_nhan_id = ANY(%s::uuid[]) ORDER BY 1, 2", (pns,))]}
        return {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"], "phap_nhan": sorted(dt["quyen"][p]["ma"] for p in pns),
                          "xem_tien": bool(pns_tien)}, "ngay_nghiep_vu": today.isoformat(),
                "ho_so": ho_so, "hop_dong": hop_dong, "tien": tien, "file_soat": file_soat, "danh_muc": danh_muc, "muc_2": "KHOA",
                "gioi_han": "DEMO: danh tính mô phỏng do máy chủ giữ theo phiên — không phải đăng nhập production; profile loại hình là giả định mô phỏng."}

    @staticmethod
    def _viec_view(v):
        return {"id": str(v["id"]), "loai": v["loai"], "trang_thai": v["trang_thai"], "tom_tat": v["tom_tat"], "ly_do_cho": list(v["ly_do_cho"]),
                "kiem_boi": v["kiem_boi"], "duyet_boi": v["duyet_boi"]}

    @staticmethod
    def _tham_so_view(r):
        typed = r["gia_tri_typed"]
        if isinstance(typed, dict) and "minor" in typed:
            typed = {**typed, "minor": _s(typed["minor"])}
        return {"ma": r["ma_nguon"], "ten": r["ten"], "truong": r["truong"], "gia_tri_tho": r["gia_tri_tho"], "gia_tri_hieu_luc": r["gia_tri"], "don_vi": r["don_vi"],
                "typed": typed, "dieu_khoan": r["dieu_khoan"], "trich_dan": r["trich_dan"], "vi_tri": r["vi_tri"], "kiem_tra_nguon": r["kiem_tra_nguon"],
                "ghi_chu_nguon": r["ghi_chu_nguon"], "can_cu": r["trang_thai_can_cu"], "loi": list(r["loi"]), "ke_thua": r["ke_thua_tu"] is not None,
                "xac_nhan_thu_cong": r["xac_nhan_thu_cong"]}
