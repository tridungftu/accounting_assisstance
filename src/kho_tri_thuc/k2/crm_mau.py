"""CRM-41-02 — service G1 mẫu DOCX có phiên bản + G7 bộ chuẩn dự án tối thiểu trên K2 PostgreSQL (M0018_CRM_G).

- Danh tính do máy chủ giữ theo phiên (`dang_nhap`); trình duyệt không cấp actor/PN/facts/đường dẫn/duyệt.
- MỌI lệnh ghi và đọc chi tiết chạy trên MỘT kết nối chủ bảng đã cấu hình (`conn_tin_cay`, cùng seam `_m5_ket_noi_chu` của máy chủ): hàm SQL
  INVOKER chỉ chủ bảng gọi được, kiểm quyền HIỆN HÀNH của phiên (GUC danh tính) TRƯỚC tra biên nhận. Thiếu kết nối → CRM_G_CHUA_SAN_SANG
  (không fallback sang login ứng dụng).
- Replay: digest H của yêu cầu gốc (không gồm khóa); tra biên nhận TRƯỚC parse/ghi blob → cùng khóa+H trả FINAL cũ (0 delta), khác H → 409.
- Đọc chi tiết/ánh xạ/kiểm/lịch sử/năng lực/token trong MỘT giao dịch REPEATABLE READ; từ chối khi đang có giao dịch ngoài.
- Blob DOCX bất biến content-addressed `crm-mau/<sha>` (write_immutable, giữ staging); tải về chỉ sau khi quyền hiện hành cho phép.
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
from ..nguon.mau_docx import GIOI_HAN, PHIEN_BAN_BO_DOC, doc_mau_docx
from . import quyen

KHOA_RE = re.compile(r"[A-Za-z0-9_.:-]{1,200}")
MA_MAU_RE = re.compile(r"[A-Za-z0-9_.-]{1,80}")
GIAI_DOAN_RE = re.compile(r"[A-Za-z0-9_.-]{1,80}")
COT_G7 = ("Lần", "Giá trị", "Mốc thời gian", "Ghi chú")
TRUONG_DONG_G7 = {"lan", "gia_tri_loai", "gia_tri_thap_phan", "so_tien_minor", "tien_te", "moc_loai", "moc_ngay", "moc_su_kien", "ghi_chu"}


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
        if isinstance(v, str):
            return str(uuid.UUID(v))
    except ValueError:
        pass
    raise DataError("CRM_G_YEU_CAU_SAI", f"Trường {ten} không hợp lệ.")


def _chuoi(v, ten: str, toi_da: int, *, bat_buoc=True):
    if v is None or v == "":
        if bat_buoc:
            raise DataError("CRM_G_YEU_CAU_SAI", f"Thiếu {ten}.")
        return None
    if not isinstance(v, str) or len(v) > toi_da or any(ord(c) < 32 and c not in "\n\t" for c in v):
        raise DataError("CRM_G_YEU_CAU_SAI", f"Trường {ten} không hợp lệ.")
    return v


def _ngay(v, ten: str) -> str:
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise DataError("CRM_G_YEU_CAU_SAI", f"{ten} phải là ngày YYYY-MM-DD.")
    try:
        date.fromisoformat(v)
    except ValueError:
        raise DataError("CRM_G_YEU_CAU_SAI", f"{ten} không tồn tại.") from None
    return v


def _khoa(k) -> str:
    if not isinstance(k, str) or not KHOA_RE.fullmatch(k):
        raise DataError("CRM_G_KHOA", "Thiếu hoặc sai khóa thao tác.")
    return k


def _h(hanh_dong: str, than: dict) -> str:
    """Digest yêu cầu GỐC bất biến (không gồm khóa)."""
    return sha256(canonical_json({"hanh_dong": hanh_dong, "than": than}).encode("utf-8"))


def _ten_tep(v) -> str:
    v = _chuoi(v, "tên tệp", 200)
    if v != v.strip() or any(c in v for c in '/\\:*?"<>|') or not v.lower().endswith(".docx"):
        raise DataError("CRM_G_YEU_CAU_SAI", "Tên tệp mẫu phải là .docx, không đường dẫn/ký tự đặc biệt.")
    return v


def doc_tep_kho(root: Path, sha: str, dai: int) -> bytes:
    """CRM-41-03: đọc blob mẫu content-addressed `crm-mau/<sha>` và kiểm lại hash/độ dài (cùng quy tắc tep_mau). Chỉ gọi SAU khi quyền đã kiểm."""
    p = Path(root) / "crm-mau" / str(sha)
    if not re.fullmatch(r"[0-9a-f]{64}", str(sha)) or not p.is_file():
        raise DataError("CRM_G_TEP_KHONG_CO", "Tệp mẫu không có trong kho lưu trữ.")
    raw = p.read_bytes()
    if sha256(raw) != sha or len(raw) != int(dai):
        raise DataError("CRM_G_TEP_HONG", "Tệp mẫu trong kho khác hash đã ghi — không dùng.")
    return raw


class CrmMauK2:
    def __init__(self, app_conn, artifact_root: Path, *, conn_tin_cay=None, chi_mo_phong: bool = True, hom_nay=None):
        """app_conn: login ứng dụng (dict_row, autocommit) — chỉ dùng nạp danh tính phiên. conn_tin_cay: kết nối CHỦ BẢNG đã kiểm (dict_row,
        autocommit) do factory máy chủ cấp; None → mọi thao tác G báo chưa sẵn sàng (503)."""
        from psycopg.types.string import StrDumperUnknown
        self.conn, self.root, self.chi_mo_phong = app_conn, Path(artifact_root), chi_mo_phong
        self.conn_tin_cay = conn_tin_cay
        self.hom_nay = hom_nay or _hom_nay_vn
        app_conn.adapters.register_dumper(str, StrDumperUnknown)
        if conn_tin_cay is not None:
            conn_tin_cay.adapters.register_dumper(str, StrDumperUnknown)

    # ------------------------------------------------------------------ hạ tầng
    def danh_tinh(self, dang_nhap: str) -> dict:
        return quyen.nap_danh_tinh(self.conn, dang_nhap, chi_mo_phong=self.chi_mo_phong)

    def _c(self):
        if self.conn_tin_cay is None:
            raise DataError("CRM_G_CHUA_SAN_SANG", "Chưa cấu hình kết nối chủ bảng của máy chủ cho mẫu/bộ chuẩn — mở lại bằng MỞ BẢN DEMO.cmd.")
        c = self.conn_tin_cay
        import psycopg
        if c.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            raise DataError("CRM_G_GIAO_DICH_NGOAI", "Kết nối đang trong một giao dịch khác — không chạy lệnh G lồng.")
        return c

    @contextmanager
    def _tx(self, dt, *, rr: bool = False):
        c = self._c()
        with c.transaction():
            if rr:
                c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true), "
                      "set_config('ktt.ngay_hieu_luc', %s, true)", (dt["id"], dt["dang_nhap"], self.hom_nay().isoformat()))
            yield c

    @staticmethod
    def _mot(c, sql, params=()):
        row = c.execute(sql, params).fetchone()
        return None if row is None else _v(dict(row))

    @staticmethod
    def _nhieu(c, sql, params=()):
        return [_v(dict(r)) for r in c.execute(sql, params)]

    def _lenh(self, dt, sql: str, params) -> dict:
        with self._tx(dt) as c:
            r = _v(dict(c.execute(sql, params).fetchone()))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    @staticmethod
    def _tra_trong(c, hanh_dong: str, khoa: str, dich: str, h: str) -> dict | None:
        """Preflight TRONG giao dịch đang mở của người gọi (S01): ghim dòng quyền + quyền hiện hành + khóa namespace (giữ đến hết giao dịch)
        + biên nhận. Cùng H → FINAL cũ; khác H → CRM_G_IDEMPOTENCY_KHAC (409) — đều TRƯỚC parse/staging/blob."""
        r = _v(dict(c.execute("SELECT master.crm_g_tra(%s, %s, %s::uuid, %s) AS r", (hanh_dong, khoa, dich, h)).fetchone()))["r"]
        return None if r is None else {**r["ket_qua"], "lap_lai": True}

    # ------------------------------------------------------------------ đọc G1
    def danh_sach(self, dang_nhap: str, as_of: str | None = None) -> dict:
        """Danh sách theo quyền hiện hành: KT/KTT/CFO/người được phân công tải → mọi phiên bản; quyền CRM khác (vd BH) → chỉ phiên bản hiệu lực tại as_of."""
        dt = self.danh_tinh(dang_nhap)
        ngay = _ngay(as_of, "as_of") if as_of else self.hom_nay().isoformat()
        with self._tx(dt, rr=True) as c:
            mau = self._nhieu(c, """SELECT m.id AS mau_id, m.ma_mau, m.phap_nhan_id, p.ma AS phap_nhan, l.ma AS loai_hinh, l.phien_ban AS loai_hinh_phien_ban,
                                           v.id AS phien_ban_id, v.phien_ban, v.trang_thai, v.valid_from, v.valid_to, v.ten_tep, v.tai_boi, v.tai_luc,
                                           master.crm_g_mau_doc(v.phap_nhan_id, v.loai_hinh_id) AS quyen_doc
                                    FROM master.crm_mau m JOIN master.crm_mau_phien_ban v ON v.mau_id = m.id
                                    JOIN master.phap_nhan p ON p.id = m.phap_nhan_id JOIN master.loai_hinh_doanh_thu l ON l.id = m.loai_hinh_id
                                    ORDER BY p.ma, m.ma_mau, v.phien_ban""")
            loai = self._nhieu(c, """SELECT l.id, l.ma, l.phien_ban, p.ma AS phap_nhan, master.crm_g_duoc('CRM_MAU_TAI', l.phap_nhan_id, l.id) AS duoc_tai
                                     FROM master.loai_hinh_doanh_thu l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                                     WHERE l.valid_to IS NULL AND master.ktt_duoc(l.phap_nhan_id, 'CRM')
                                       AND EXISTS (SELECT 1 FROM master.crm_danh_muc_truong t WHERE t.loai_hinh_id = l.id) ORDER BY p.ma, l.ma""")
        ds = []
        for r in mau:
            q = r.pop("quyen_doc")
            if q == "DAY_DU":
                ds.append(r)
            elif q == "HIEU_LUC" and r["trang_thai"] == "HIEU_LUC" and r["valid_from"] <= ngay and (r["valid_to"] is None or ngay < r["valid_to"]):
                ds.append(r)
        return {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"]}, "as_of": ngay, "phien_ban": ds, "loai_hinh": loai,
                "ghi_nguon": {"san_sang": self.conn_tin_cay is not None}, "gioi_han_tep": GIOI_HAN["tep"]}

    def chi_tiet(self, dang_nhap: str, phien_ban_id) -> dict:
        """Một aggregate REPEATABLE READ: phiên bản + facts phát hiện + ánh xạ hiện hành + lịch sử ánh xạ/kiểm/sự kiện + danh mục + năng lực + token."""
        dt = self.danh_tinh(dang_nhap)
        pb = _uuid(phien_ban_id, "phien_ban_id")
        with self._tx(dt, rr=True) as c:
            v = self._mot(c, """SELECT v.*, m.ma_mau, master.crm_g_mau_doc(v.phap_nhan_id, v.loai_hinh_id) AS quyen_doc, master.crm_g_mau_token(v.id) AS token
                                FROM master.crm_mau_phien_ban v JOIN master.crm_mau m ON m.id = v.mau_id WHERE v.id = %s::uuid""", (pb,))
            hom_nay = self.hom_nay().isoformat()
            if v is None or v["quyen_doc"] is None or (v["quyen_doc"] == "HIEU_LUC" and not (
                    v["trang_thai"] == "HIEU_LUC" and v["valid_from"] <= hom_nay and (v["valid_to"] is None or hom_nay < v["valid_to"]))):
                # quyền CRM chỉ-hiệu-lực (vd bán hàng): chỉ phiên bản đang hiệu lực hôm nay; nháp/lịch sử/đã đóng → ẩn như không có
                raise DataError("CRM_G_KHONG_THAY", "Không thấy phiên bản mẫu (hoặc ngoài phạm vi).")
            day_du = v["quyen_doc"] == "DAY_DU"
            tep = self._mot(c, "SELECT raw_sha256, byte_length, bo_doc, facts, facts_sha256, trang_thai_doc FROM master.crm_mau_tep WHERE id = %s", (v["tep_id"],))
            danh_muc = self._nhieu(c, """SELECT khoa, nhan, nhom, kieu, dinh_dang, pii, bat_buoc FROM master.crm_danh_muc_truong
                                         WHERE loai_hinh_id = %s AND danh_muc_ref = %s AND revision = %s ORDER BY khoa""",
                                   (v["loai_hinh_id"], v["danh_muc_ref"], v["danh_muc_rev"]))
            anh_xa = self._mot(c, "SELECT * FROM master.crm_mau_anh_xa WHERE id = %s", (v["anh_xa_hien_hanh"],)) if v["anh_xa_hien_hanh"] else None
            lich_su = {}
            if day_du:
                lich_su = {
                    "anh_xa": self._nhieu(c, """SELECT id, revision, so_chua_anh_xa, so_sai_kieu, canh_bao, tao_boi, tao_luc FROM master.crm_mau_anh_xa
                                               WHERE phien_ban_id = %s ORDER BY revision""", (pb,)),
                    "kiem_tra": self._nhieu(c, """SELECT id, anh_xa_id, ket_qua, kiem_boi, kiem_luc FROM master.crm_mau_kiem_tra WHERE phien_ban_id = %s
                                                 ORDER BY kiem_luc""", (pb,)),
                    "su_kien": self._nhieu(c, """SELECT luc, nguoi, hanh_dong, ly_do, sau FROM nhat_ky.su_kien WHERE doi_tuong_bang = 'master.crm_mau_phien_ban'
                                                AND doi_tuong_id = %s ORDER BY id""", (pb,)),
                    "viec": self._mot(c, "SELECT id, trang_thai, ly_do_cho, kiem_boi, duyet_boi FROM kho.viec_can_duyet WHERE id = %s",
                                      (v["viec_id"],)) if v["viec_id"] else None,
                    "phien_ban_cung_mau": self._nhieu(c, """SELECT id, phien_ban, trang_thai, valid_from, valid_to FROM master.crm_mau_phien_ban
                                                           WHERE mau_id = %s ORDER BY phien_ban""", (v["mau_id"],)),
                }
            kha_nang = {a: bool(self._mot(c, "SELECT master.crm_g_duoc(%s, %s::uuid, %s::uuid) AS ok", (a, v["phap_nhan_id"], v["loai_hinh_id"]))["ok"])
                        for a in ("CRM_MAU_MAP", "CRM_MAU_GUI_KIEM", "CRM_MAU_KIEM", "CRM_MAU_TRA_LAI", "CRM_MAU_DUYET_V4", "CRM_MAU_TU_CHOI")}
        facts = tep["facts"] if day_du else None
        return {"phien_ban": {k: v[k] for k in ("id", "mau_id", "ma_mau", "phap_nhan_id", "loai_hinh_id", "phien_ban", "ten_tep", "trang_thai",
                                                "valid_from", "valid_to", "tai_boi", "tai_luc", "duyet_boi", "duyet_luc", "tu_choi_ly_do",
                                                "danh_muc_ref", "danh_muc_rev")},
                "token": v["token"], "quyen_doc": v["quyen_doc"],
                "tep": {"raw_sha256": tep["raw_sha256"], "byte_length": tep["byte_length"], "bo_doc": tep["bo_doc"], "trang_thai_doc": tep["trang_thai_doc"]},
                "phat_hien": None if facts is None else {"placeholders": facts.get("placeholders", []), "occurrences": facts.get("occurrences", []),
                                                         "phan_quet": facts.get("phan_quet", []), "ly_do_chua_du": facts.get("ly_do_chua_du", []),
                                                         "doan": facts.get("doan", []), "don_vi_khoang": facts.get("don_vi_khoang")},
                "danh_muc": danh_muc, "anh_xa": anh_xa, "lich_su": lich_su,
                "kha_nang": {k: bool(ok and day_du) for k, ok in kha_nang.items()}}

    def so_sanh(self, dang_nhap: str, a, b) -> dict:
        """So hai phiên bản cùng mẫu: placeholder/số lần và trường ánh xạ (chỉ đọc)."""
        ca, cb = self.chi_tiet(dang_nhap, a), self.chi_tiet(dang_nhap, b)
        if ca["phien_ban"]["mau_id"] != cb["phien_ban"]["mau_id"]:
            raise DataError("CRM_G_YEU_CAU_SAI", "Chỉ so sánh hai phiên bản của cùng một mẫu.")

        def tom(ct):
            ph = {p["ten"]: p["so_lan"] for p in ((ct["phat_hien"] or {}).get("placeholders") or [])}
            bd = {}
            for o in ((ct["anh_xa"] or {}).get("ban_do") or []):
                bd.setdefault(o["ten"], o.get("truong"))
            return ph, bd
        pa, ba = tom(ca)
        pb_, bb = tom(cb)
        ten = sorted(set(pa) | set(pb_))
        return {"a": ca["phien_ban"], "b": cb["phien_ban"], "khac_tep": ca["tep"]["raw_sha256"] != cb["tep"]["raw_sha256"],
                "dong": [{"ten": t, "so_lan_a": pa.get(t), "so_lan_b": pb_.get(t), "truong_a": ba.get(t), "truong_b": bb.get(t),
                          "khac": (pa.get(t), ba.get(t)) != (pb_.get(t), bb.get(t))} for t in ten]}

    def xem_thu(self, dang_nhap: str, phien_ban_id) -> dict:
        """Xem thử bằng DỮ LIỆU GIẢ của danh mục: thay placeholder trong văn bản đoạn bằng giá trị giả (chuỗi thuần — giao diện hiển thị
        bằng textContent). Không ghi, không Office/PDF, không PII thật."""
        ct = self.chi_tiet(dang_nhap, phien_ban_id)
        if ct["quyen_doc"] != "DAY_DU":
            raise DataError("CRM_G_KHONG_CO_QUYEN", "Xem thử dành cho người soạn/kiểm/duyệt mẫu.")
        dm = {t["khoa"]: t for t in ct["danh_muc"]}
        with self._tx(self.danh_tinh(dang_nhap), rr=True) as c:
            gia = {r["khoa"]: r["xem_thu"] for r in self._nhieu(c, """SELECT khoa, xem_thu FROM master.crm_danh_muc_truong WHERE loai_hinh_id = %s
                                                                      AND danh_muc_ref = %s AND revision = %s""",
                                                                  (ct["phien_ban"]["loai_hinh_id"], ct["phien_ban"]["danh_muc_ref"], ct["phien_ban"]["danh_muc_rev"]))}
        truong_cua = {o["ten"]: o.get("truong") for o in ((ct["anh_xa"] or {}).get("ban_do") or [])}

        def gia_tri(ten):
            k = truong_cua.get(ten)
            if not k:
                return "[[CHƯA ÁNH XẠ: " + ten + "]]"
            g = gia.get(k)
            if isinstance(g, dict) and "amount_minor" in g:
                return f"{g['amount_minor']} {g.get('currency', '')} (minor, DEMO)"
            return str(g) if g is not None else "[[" + dm.get(k, {}).get("nhan", k) + "]]"
        # thay theo KHOẢNG ký tự thực của từng lần xuất hiện trên văn bản ghép đầy đủ của đoạn (facts đã lưu) — không dò lại bằng tên
        theo_doan = {}
        for o in (ct["phat_hien"] or {}).get("occurrences", []):
            theo_doan.setdefault(o["doan"], []).append(o)
        doan = []
        for d in (ct["phat_hien"] or {}).get("doan", []):
            text, ra, vt = d["van_ban"], [], 0
            for o in sorted(theo_doan.get(d["chi_so"], []), key=lambda x: x["bat_dau"]):
                if o["ket_thuc"] > len(text):
                    break  # đoạn đã cắt bớt (INCOMPLETE): không thay ngoài phần văn bản đã giữ
                ra.append(text[vt:o["bat_dau"]])
                ra.append(gia_tri(o["ten"]))
                vt = o["ket_thuc"]
            ra.append(text[vt:])
            doan.append({"phan": d["phan"], "loai_phan": d["loai_phan"], "vi_tri": d["vi_tri"], "van_ban": "".join(ra), "cat_bot": d["cat_bot"]})
        return {"phien_ban_id": ct["phien_ban"]["id"], "du_lieu_gia": True, "doan": doan}

    def tep_mau(self, dang_nhap: str, phien_ban_id) -> tuple[str, bytes]:
        """DOCX gốc: quyền hiện hành (đầy đủ, hoặc chỉ phiên bản hiệu lực với quyền CRM khác) kiểm TRƯỚC khi tra đường dẫn/hash/đọc kho."""
        ct = self.chi_tiet(dang_nhap, phien_ban_id)
        sha, dai = ct["tep"]["raw_sha256"], ct["tep"]["byte_length"]
        p = self.root / "crm-mau" / sha
        if not re.fullmatch(r"[0-9a-f]{64}", sha) or not p.is_file():
            raise DataError("CRM_G_TEP_KHONG_CO", "Tệp mẫu không có trong kho lưu trữ.")
        raw = p.read_bytes()
        if sha256(raw) != sha or len(raw) != dai:
            raise DataError("CRM_G_TEP_HONG", "Tệp mẫu trong kho khác hash đã ghi — không trả.")
        return ct["phien_ban"]["ten_tep"], raw

    # ------------------------------------------------------------------ CRM-41-03: seam đọc mẫu ĐÃ GHIM của bản soạn (lịch sử hẹp)
    def mau_ghim_trong(self, c, soan_id: str, revision: int) -> dict:
        """Gọi TRONG giao dịch đang mở của người gọi (kết nối chủ bảng): quyền hiện hành trên ĐÚNG bản soạn/PN được hàm SQL kiểm trước; trả raw
        bytes + facts + bản đồ + danh mục của PHIÊN BẢN ĐÃ GHIM (kể cả khi đã có phiên bản mới hiệu lực). Không nới picker/đọc mọi mẫu lịch sử."""
        g = _v(dict(c.execute("SELECT master.crm_gk_mau_ghim(%s::uuid, %s) AS r", (_uuid(soan_id, "soan_id"), int(revision))).fetchone()))["r"]
        return {**g, "raw": doc_tep_kho(self.root, g["raw_sha256"], g["byte_length"])}

    # ------------------------------------------------------------------ lệnh G1
    def tai_mau(self, dang_nhap: str, raw: bytes, *, loai_hinh_id, ma_mau, ten_tep, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        loai = _uuid(loai_hinh_id, "loai_hinh_id")
        if not isinstance(ma_mau, str) or not MA_MAU_RE.fullmatch(ma_mau):
            raise DataError("CRM_G_YEU_CAU_SAI", "Mã mẫu chỉ gồm chữ/số/_ . - (1–80).")
        ten = _ten_tep(ten_tep)
        khoa = _khoa(khoa)
        if not isinstance(raw, (bytes, bytearray)) or not raw:
            raise DataError("CRM_MAU_TEP_RONG", "Tệp mẫu rỗng.")
        if len(raw) > GIOI_HAN["tep"]:
            raise DataError("CRM_G_TEP_QUA_LON", "Tệp mẫu vượt giới hạn kích thước.")
        raw = bytes(raw)
        sha = sha256(raw)
        h = _h("CRM_MAU_TAI", {"loai_hinh_id": loai, "ma_mau": ma_mau, "ten_tep": ten, "raw_sha256": sha, "byte_length": len(raw)})
        # S01: MỘT giao dịch trên MỘT kết nối chủ bảng từ preflight (ghim quyền + quyền hiện hành + khóa namespace + biên nhận) qua parse →
        # blob bất biến → lệnh → FINAL. Request cùng (PN, actor, action, khóa) chờ khóa namespace đến khi giao dịch này kết thúc rồi mới thấy
        # biên nhận: cùng H → FINAL cũ; khác H → 409 — cả hai TRƯỚC parse/staging/blob. Thu hồi quyền đã commit trước preflight → từ chối
        # trước filesystem; thu hồi đồng thời phải chờ dòng quyền đã ghim đến khi giao dịch này kết thúc (không còn khe preflight→lệnh).
        with self._tx(dt) as c:
            cu = self._tra_trong(c, "CRM_MAU_TAI", khoa, loai, h)
            if cu is not None:
                return cu
            facts = doc_mau_docx(raw)
            write_immutable(self.root / "crm-mau" / sha, raw)  # content-addressed, giữ staging; không xóa artifact khi lệnh sau đó lỗi
            r = _v(dict(c.execute("""SELECT master.crm_g_mau_tai(%s, %s, %s::uuid, %s, %s, %s, %s::bigint, %s, %s::jsonb, %s, %s) AS r""",
                                  (khoa, h, loai, ma_mau, ten, sha, len(raw), PHIEN_BAN_BO_DOC, json.dumps(facts, ensure_ascii=False),
                                   facts["facts_sha256"], facts["trang_thai"])).fetchone()))["r"]
        return {**r["ket_qua"], "lap_lai": bool(r["lap_lai"])}

    def luu_anh_xa(self, dang_nhap: str, *, version_id, map, expected_graph, khoa) -> dict:  # noqa: A002 — tên trường contract
        dt = self.danh_tinh(dang_nhap)
        pb = _uuid(version_id, "version_id")
        if not isinstance(map, dict) or len(map) > 500 or any(not isinstance(k, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,80}", k)
                                                                or not (v is None or (isinstance(v, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", v)))
                                                                for k, v in map.items()):
            raise DataError("CRM_G_YEU_CAU_SAI", "Ánh xạ phải là {placeholder: mã trường | null}.")
        tok, khoa = _chuoi(expected_graph, "expected_graph", 64), _khoa(khoa)
        h = _h("CRM_MAU_MAP", {"version_id": pb, "map": map, "expected_graph": tok})
        return self._lenh(dt, "SELECT master.crm_g_mau_anh_xa(%s, %s, %s::uuid, %s, %s::jsonb) AS r",
                          (khoa, h, pb, tok, json.dumps(map, ensure_ascii=False)))

    def _don_gian(self, dang_nhap, ham: str, hanh_dong: str, version_id, expected_graph, khoa, them=None, them_sql="") -> dict:
        dt = self.danh_tinh(dang_nhap)
        pb = _uuid(version_id, "version_id")
        tok, khoa = _chuoi(expected_graph, "expected_graph", 64), _khoa(khoa)
        than = {"version_id": pb, "expected_graph": tok, **(them or {})}
        h = _h(hanh_dong, than)
        return self._lenh(dt, f"SELECT master.{ham}(%s, %s, %s::uuid, %s{them_sql}) AS r", (khoa, h, pb, tok, *(them or {}).values()))

    def gui_kiem(self, dang_nhap: str, *, version_id, expected_graph, khoa) -> dict:
        return self._don_gian(dang_nhap, "crm_g_mau_gui_kiem", "CRM_MAU_GUI_KIEM", version_id, expected_graph, khoa)

    def kiem_mau(self, dang_nhap: str, *, version_id, expected_graph, khoa) -> dict:
        return self._don_gian(dang_nhap, "crm_g_mau_kiem", "CRM_MAU_KIEM", version_id, expected_graph, khoa)

    def tra_lai_mau(self, dang_nhap: str, *, version_id, ly_do, expected_graph, khoa) -> dict:
        ly_do = _chuoi(ly_do, "lý do trả lại", 1000)
        return self._don_gian(dang_nhap, "crm_g_mau_tra_lai", "CRM_MAU_TRA_LAI", version_id, expected_graph, khoa, {"ly_do": ly_do}, ", %s")

    def duyet_mau(self, dang_nhap: str, *, version_id, valid_from, expected_graph, khoa) -> dict:
        ngay = _ngay(valid_from, "Ngày hiệu lực")
        return self._don_gian(dang_nhap, "crm_g_mau_duyet", "CRM_MAU_DUYET_V4", version_id, expected_graph, khoa, {"valid_from": ngay}, ", %s::date")

    def tu_choi_mau(self, dang_nhap: str, *, version_id, ly_do, expected_graph, khoa) -> dict:
        ly_do = _chuoi(ly_do, "lý do từ chối", 1000)
        return self._don_gian(dang_nhap, "crm_g_mau_tu_choi", "CRM_MAU_TU_CHOI", version_id, expected_graph, khoa, {"ly_do": ly_do}, ", %s")

    # ------------------------------------------------------------------ G7
    @staticmethod
    def _dong_g7(dong) -> list[dict]:
        if not isinstance(dong, list) or not 1 <= len(dong) <= 200:
            raise DataError("CRM_G_CHUAN_SAI", "Bộ chuẩn cần 1–200 dòng.")
        out = []
        for d in dong:
            if not isinstance(d, dict) or set(d) - TRUONG_DONG_G7:
                raise DataError("CRM_G_CHUAN_SAI", "Dòng bộ chuẩn chỉ gồm lần/giá trị/mốc/ghi chú có kiểu.")
            r = {k: d.get(k) for k in sorted(TRUONG_DONG_G7)}
            for k, v in r.items():
                if v is not None and not isinstance(v, str):
                    raise DataError("CRM_G_CHUAN_SAI", f"Trường {k} phải là chuỗi (số giữ dạng chuỗi chính xác) hoặc null.")
            if not r["lan"]:
                raise DataError("CRM_G_CHUAN_SAI", "Mỗi dòng cần cột Lần.")
            if r["gia_tri_loai"] == "PERCENT" and not re.fullmatch(r"-?[0-9]{1,20}(\.[0-9]{1,12})?", r["gia_tri_thap_phan"] or ""):
                raise DataError("CRM_G_CHUAN_SAI", "Tỷ lệ phải là số thập phân chính xác dạng chuỗi.")
            if r["gia_tri_loai"] == "AMOUNT" and (not re.fullmatch(r"-?[0-9]{1,24}", r["so_tien_minor"] or "")
                                                 or not re.fullmatch(r"[A-Z]{3}", r["tien_te"] or "")):
                raise DataError("CRM_G_CHUAN_SAI", "Số tiền phải là số nguyên đơn vị nhỏ nhất + mã tiền tệ.")
            if r["moc_loai"] == "NGAY":
                _ngay(r["moc_ngay"], "Mốc ngày")
            out.append(r)
        return out

    def lap_bo_chuan(self, dang_nhap: str, *, du_an_id, giai_doan, dong, khoa) -> dict:
        dt = self.danh_tinh(dang_nhap)
        da = _uuid(du_an_id, "du_an_id")
        if not isinstance(giai_doan, str) or not GIAI_DOAN_RE.fullmatch(giai_doan):
            raise DataError("CRM_G_YEU_CAU_SAI", "Giai đoạn chỉ gồm chữ/số/_ . - (1–80).")
        rows, khoa = self._dong_g7(dong), _khoa(khoa)
        h = _h("CRM_CHUAN_LAP", {"du_an_id": da, "giai_doan": giai_doan, "dong": rows})
        return self._lenh(dt, "SELECT master.crm_g_chuan_lap(%s, %s, %s::uuid, %s, %s::jsonb) AS r",
                          (khoa, h, da, giai_doan, json.dumps(rows, ensure_ascii=False)))

    def gui_duyet_bo_chuan(self, dang_nhap: str, *, version_id, expected_graph, khoa) -> dict:
        return self._don_gian(dang_nhap, "crm_g_chuan_gui", "CRM_CHUAN_GUI_DUYET", version_id, expected_graph, khoa)

    def duyet_bo_chuan(self, dang_nhap: str, *, version_id, valid_from, expected_graph, khoa) -> dict:
        ngay = _ngay(valid_from, "Ngày hiệu lực")
        return self._don_gian(dang_nhap, "crm_g_chuan_duyet", "CRM_CHUAN_DUYET_V4", version_id, expected_graph, khoa, {"valid_from": ngay}, ", %s::date")

    def doc_bo_chuan(self, dang_nhap: str, project_id, giai_doan, as_of=None) -> dict:
        dt = self.danh_tinh(dang_nhap)
        da = _uuid(project_id, "project_id")
        if not isinstance(giai_doan, str) or not GIAI_DOAN_RE.fullmatch(giai_doan):
            raise DataError("CRM_G_YEU_CAU_SAI", "Giai đoạn không hợp lệ.")
        ngay = _ngay(as_of, "as_of") if as_of else self.hom_nay().isoformat()
        with self._tx(dt, rr=True) as c:
            r = self._mot(c, "SELECT master.crm_g_chuan_doc(%s::uuid, %s, %s::date) AS r", (da, giai_doan, ngay))["r"]
        return {**r, "as_of": ngay, "du_an_id": da, "giai_doan": giai_doan}

    def danh_sach_bo_chuan(self, dang_nhap: str) -> dict:
        """Tổng quan G7: dự án trong phạm vi CRM của phiên; KT/KTT/CFO thấy thêm mọi phiên bản (nháp/chờ/hiệu lực) kèm token và năng lực."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt, rr=True) as c:
            du_an = self._nhieu(c, """SELECT a.id, a.ma_junsky, a.ten, p.ma AS phap_nhan FROM master.du_an a JOIN master.phap_nhan p ON p.id = a.phap_nhan_id
                                      WHERE master.ktt_duoc(a.phap_nhan_id, 'CRM') ORDER BY p.ma, a.ma_junsky""")
            pb = self._nhieu(c, """SELECT v.id, v.phien_ban, v.trang_thai, v.so_dong, v.valid_from, v.valid_to, v.lap_boi, v.gui_boi, v.duyet_boi,
                                          b.du_an_id, b.giai_doan, master.crm_g_chuan_token(v.id) AS token,
                                          master.crm_g_duoc('CRM_CHUAN_GUI_DUYET', v.phap_nhan_id, NULL) AS duoc_gui,
                                          master.crm_g_duoc('CRM_CHUAN_DUYET_V4', v.phap_nhan_id, NULL) AS duoc_duyet,
                                          CASE WHEN v.trang_thai <> 'HIEU_LUC' THEN NULL
                                               WHEN EXISTS (SELECT 1 FROM master.crm_bo_chuan_ap_dung x WHERE x.phien_ban_id = v.id) THEN 'AP_DUNG_NGAY'
                                               ELSE 'CFO_DUYET' END AS nguon_hieu_luc
                                   FROM master.crm_bo_chuan_phien_ban v JOIN master.crm_bo_chuan b ON b.id = v.bo_chuan_id
                                   WHERE master.crm_g_chuan_doc_duoc(v.phap_nhan_id) ORDER BY b.giai_doan, v.phien_ban""")
            for v in pb:
                v["dong"] = self._nhieu(c, """SELECT thu_tu, lan, gia_tri_loai, gia_tri_thap_phan, so_tien_minor, tien_te, moc_loai, moc_ngay, moc_su_kien, ghi_chu
                                              FROM master.crm_bo_chuan_dong WHERE phien_ban_id = %s ORDER BY thu_tu""", (v["id"],))
            duoc_lap = {a["id"]: bool(self._mot(c, "SELECT master.crm_g_duoc('CRM_CHUAN_LAP', a.phap_nhan_id, NULL) AS ok FROM master.du_an a WHERE a.id = %s",
                                                (a["id"],))["ok"]) for a in du_an}
        for a in du_an:
            a["duoc_lap"] = duoc_lap[a["id"]]
        return {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"]}, "cot": list(COT_G7), "du_an": du_an, "phien_ban": pb,
                "ghi_nguon": {"san_sang": self.conn_tin_cay is not None}}
