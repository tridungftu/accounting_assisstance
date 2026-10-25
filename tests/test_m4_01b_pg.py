"""M4-01B/B2 — kiểm PostgreSQL THẬT cho Cổng hồ sơ M4 (CODE_ONLY: coder viết, CHƯA CHẠY — NOT_RUN; Root chạy sau terminal).

Chạy khi Root cấp KHO_PG_DSN_TEST (DSN chủ CSDL, qua env lúc chạy — không đọc .env/var, không hardcode credentials). DB MỚI `kho_test_m4b_*`
migrate mặc định (prefix 1–16 + M17), seed CRM DEMO + M4 DEMO; login ứng dụng tạm (NOSUPERUSER NOBYPASSRLS, IN ROLE app_web) cho lệnh người dùng;
kết nối chủ CSDL riêng làm đường ghi nguồn tin cậy (inject như factory). Actor MO_PHONG_*. Không DROP/DELETE/TRUNCATE/cleanup — DB/role/thư mục
giữ làm bằng chứng. Thiếu driver/DSN → skip = NOT_RUN/NOT_VERIFIED, không tính đạt. Ca cần lõi nguồn đã nạp (review_goc) skip riêng khi chưa nạp.
Client #6 giả trong tiến trình trả đủ 37 mã CHUA_CO; DOCX/XLSX và kiểm căn cứ vẫn chạy thật. Không chứng minh độ chính xác engine/AI.

T01 migrate + seed đủ, seed chạy lại không thêm/không cấp lại.
T02 nhận tệp: thiếu đường tin cậy → chưa sẵn sàng, không ghi bytes; bytes thật → tệp + raw giữ; replay/đổi body/cùng bytes khóa khác; tên/media xấu bị chặn.
T03 giả mạo bằng app thường (actor CÓ quyền dự án): ghi tệp/trích XONG/BOQ DA_MAP/máy kiểm/biên nhận FINAL đều bị CSDL từ chối; đường tin cậy vẫn
    kiểm phạm vi actor của phiên.
T04 luồng đầy đủ (cần lõi nguồn): tệp HĐ → trích → nhập 37 tham số theo ORACLE THỦ CÔNG PHIEU_THAM_SO/VANG (21 mã có căn cứ nguyên văn +
    máy kiểm thật OK, gồm tạm ứng Không áp dụng; 16 mã thật sự vắng Không quy định) → xác nhận → PL khai/thêm/hủy → BOQ có phát hiện số học
    (DA_MAP) → đợt + hồ sơ → nộp thật. Sau đó replay ĐÚNG key/body/revision gốc mọi lệnh (sentinel: không parse/AI/ghi lại), đổi body → từ chối,
    không thêm hàng nghiệp vụ.
T05 đồng thời: hai kết nối cùng khóa/body → một kết quả, một hàng.
T06 Track Changes qua đường sửa tham số: chặn trước Office/cleanup, raw giữ (không cần lõi nguồn).
T07 BOQ số không đọc được (tên chứa mẫu số học) → CO_LOI, preflight chặn, nộp bị chặn (cần lõi nguồn).
T08 phạm vi: khác PN/dự án, reviewer không xác nhận tham số, KE_TOAN có PHU_TRACH, PN không module M4 — đều chặn; bit đã nộp theo phạm vi.
T09 thu hồi dự án (chỉ ghi thêm): replay/đọc/tệp/biên nhận/bit đã nộp bị chặn; actor vẫn hoạt động, module M4 còn; seed không cấp lại.
T10 factory máy chủ: có admin DSN → có đường tin cậy; không có → chưa sẵn sàng, không fallback.
"""

from __future__ import annotations

import os
import re
import secrets
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nguon_review as NR
from kho_tri_thuc.nguon import trich_chung_6 as T6

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
A1, A2, B1 = "MO_PHONG_DU_AN_A1", "MO_PHONG_DU_AN_A2", "MO_PHONG_DU_AN_B1"
REVIEW, KT_PT, KHONG_M4 = "MO_PHONG_REVIEW_M4", "MO_PHONG_KT_PHU_TRACH_M4", "MO_PHONG_DU_AN_KHONG_M4"
BANG = ("tep", "ho_so_hop_dong", "trich_xuat", "tham_so", "tham_so_lich_su", "xac_nhan_tham_so", "phu_luc", "boq", "boq_dong", "dot", "dot_tep",
        "nop", "bien_nhan", "nhat_ky")
# ORACLE THỦ CÔNG cho T04 — lập bằng tay từ fixtures_m4.DONG_HOP_DONG (dòng nào, Điều nào) và tên 37 mã danh mục; KHÔNG lấy từ parser/CHUA_CO.
# mã → (trạng thái, giá trị, đơn vị, điều khoản, trích dẫn nguyên văn). Giá trị là chuỗi con nguyên văn của trích dẫn.
PHIEU_THAM_SO = {
    "TC-01": ("CO_GIA_TRI", "HDXD-DEMO-01", None, None, "Số: HDXD-DEMO-01"),
    "TC-02": ("CO_GIA_TRI", "ngày 05 tháng 01 năm 2026", None, None, "Hôm nay, ngày 05 tháng 01 năm 2026, chúng tôi gồm:"),
    "TC-03": ("CO_GIA_TRI", "Thi công hạ tầng DEMO", None, None, "Gói thầu: Thi công hạ tầng DEMO"),
    "TC-04": ("CO_GIA_TRI", "Khu công nghiệp DEMO A", None, None, "Dự án: Khu công nghiệp DEMO A"),
    "TC-05": ("CO_GIA_TRI", "Tỉnh DEMO", None, None, "Địa điểm: Tỉnh DEMO"),
    "TC-06": ("CO_GIA_TRI", "Công ty DEMO A", None, None, "Bên giao thầu (Bên A): Công ty DEMO A"),
    "TC-07": ("CO_GIA_TRI", "Nhà thầu DEMO B", None, None, "Bên nhận thầu (Bên B): Nhà thầu DEMO B"),
    "TC-08": ("CO_GIA_TRI", "có hiệu lực kể từ ngày ký", None, "Điều 6", "6.1 Hợp đồng này có hiệu lực kể từ ngày ký."),
    "TC-09": ("CO_GIA_TRI", "HỢP ĐỒNG THI CÔNG XÂY DỰNG", None, None, "HỢP ĐỒNG THI CÔNG XÂY DỰNG (DEMO)"),
    "TT-01": ("CO_GIA_TRI", "Hợp đồng trọn gói", None, "Điều 2", "2.2 Hợp đồng trọn gói."),
    "TT-02": ("CO_GIA_TRI", "1.000.000.000", "đồng", "Điều 2", "2.1 Giá trị hợp đồng là 1.000.000.000 đồng, đã bao gồm thuế VAT 8%."),
    "TT-03": ("CO_GIA_TRI", "đã bao gồm thuế VAT", None, "Điều 2", "2.1 Giá trị hợp đồng là 1.000.000.000 đồng, đã bao gồm thuế VAT 8%."),
    "TT-04": ("CO_GIA_TRI", "8%", "%", "Điều 2", "2.1 Giá trị hợp đồng là 1.000.000.000 đồng, đã bao gồm thuế VAT 8%."),
    "TT-05": ("CO_GIA_TRI", "giá trị khối lượng hoàn thành được nghiệm thu", None, "Điều 3",
              "3.2 Mỗi đợt thanh toán cho bên B tối đa 90% giá trị khối lượng hoàn thành được nghiệm thu."),
    "TT-10": ("KHONG_AP_DUNG", None, None, "Điều 3", "3.1 Tạm ứng: Không áp dụng."),
    "TT-11": ("KHONG_AP_DUNG", None, None, "Điều 3", "3.1 Tạm ứng: Không áp dụng."),
    "TT-12": ("KHONG_AP_DUNG", None, None, "Điều 3", "3.1 Tạm ứng: Không áp dụng."),
    "TT-20": ("CO_GIA_TRI", "tối đa 90%", "%", "Điều 3",
              "3.2 Mỗi đợt thanh toán cho bên B tối đa 90% giá trị khối lượng hoàn thành được nghiệm thu."),
    "TT-22": ("CO_GIA_TRI", "Tối đa 30 ngày kể từ ngày nhận đủ hồ sơ hợp lệ", None, "Điều 3",
              "3.3 Thời gian thanh toán: Tối đa 30 ngày kể từ ngày nhận đủ hồ sơ hợp lệ."),
    "TT-32": ("CO_GIA_TRI", "12 tháng", None, "Điều 4", "4.1 Thời hạn bảo hành là 12 tháng kể từ ngày nghiệm thu bàn giao."),
    "TT-50": ("CO_GIA_TRI", "180 ngày kể từ ngày khởi công", None, "Điều 5", "5.1 Tiến độ thực hiện: 180 ngày kể từ ngày khởi công."),
}
# mã THẬT SỰ vắng trong HĐ fixture (không suy: TT-21 giữ lại KHÔNG suy 100%−90% vì HĐ không nói) → KHONG_QUY_DINH có lý do
VANG = ("TT-21", "TT-30", "TT-31", "TT-33", "TT-40", "TT-41", "TT-42", "TT-51", "TT-52", "TT-53", "TT-54", "TT-55", "TT-56",
        "TT-60", "TT-61", "TT-62")
CAU_HINH_FIXTURE = """[app]
entity_id = "PLHN_FIXTURE"
environment = "fixture"
data_dir = "data"

[money]
currency = "VND"
scale = 0

[operation]
junsky_export_enabled = false
junsky_import_enabled = false

[storage]
engine = "sqlite"
"""


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


def _cam(*a, **k):
    raise AssertionError("Replay không được chạy lại xử lý/ghi tệp")


class _Trich6Gia:
    """Client #6 trong tiến trình; không suy giá trị thay oracle nhập tay, không mạng/AI."""
    san_sang = True

    def __init__(self):
        self.goi = []

    def trich(self, raw, *, ten_tep, loai_hop_dong, tham_so, request_id):
        if (ten_tep, loai_hop_dong, tham_so) != ("hop_dong.docx", "XD", "ALL"):
            raise AssertionError("Test M4 phải yêu cầu đủ danh mục XD trên DOCX")
        yc = T6.yeu_cau_common(source_sha256=sha256(raw), loai_hop_dong=loai_hop_dong, tham_so=tham_so, request_id=request_id)
        self.goi.append(yc)
        cm = {**yc, "body_sha256": T6.body_sha256(yc), "tham_so_da_dung": list(NR.MA_DANH_MUC),
              "implementation": {"sha256": sha256(b"T-M4a-client-gia")}}
        kq = {"che_do": T6.MODE, "common": cm,
              "bang": [{"ma": ma, "gia_tri": None, "trich_dan": None} for ma in NR.MA_DANH_MUC]}
        T6.kiem_ket_qua(kq, yc)
        raw_kq = canonical_json(kq).encode("utf-8")
        return {"luot": "gia-" + request_id, "raw_ket_qua": raw_kq, "raw_sha256": sha256(raw_kq),
                "ket_qua": kq, "common": cm, "yeu_cau": yc}


class Trich6GiaTests(unittest.TestCase):
    def test_docx_qua_adapter_du_37_ma_va_giu_raw(self):
        client, raw = _Trich6Gia(), F.hop_dong_docx()
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4a_trich6_"))  # giữ bằng chứng
        kq = NR.trich_hop_dong(raw, F.MEDIA_DOCX, tam, client=client, request_id="m4:test-gia")
        self.assertEqual((kq["trang_thai"], kq["che_do"]), ("XONG", "QUY_TAC_KHONG_AI"))
        self.assertEqual([r["ma"] for r in kq["ket_qua"]], list(NR.MA_DANH_MUC))
        self.assertTrue(all(r["trang_thai"] == "CHUA_CO" and r["gia_tri"] is None for r in kq["ket_qua"]))
        h = kq["phieu"]["ket_qua_6_sha256"]
        self.assertEqual(sha256((tam / f"ket_qua_6_{h}.json").read_bytes()), h)
        self.assertEqual(len(client.goi), 1)
        self.assertEqual(client.goi[0]["source_sha256"], sha256(raw))

    def test_track_changes_chan_truoc_client(self):
        client = _Trich6Gia()
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4a_track_"))  # giữ bằng chứng
        kq = NR.trich_hop_dong(F.hop_dong_docx(track_changes=True), F.MEDIA_DOCX, tam,
                              client=client, request_id="m4:test-track")
        self.assertEqual(kq["trang_thai"], "KHONG_HO_TRO")
        self.assertEqual(list(tam.iterdir()), [])
        self.assertEqual(client.goi, [])


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PG M4-01B không chạy (NOT_RUN, không tính đạt)")
class M4PG(unittest.TestCase):
    """Chạy theo thứ tự tên t01…t10 trên MỘT DB; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cls.db = "kho_test_m4b_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)                      # setup/observer (hàng tuple)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m4b_" + uuid.uuid4().hex[:8], secrets.token_hex(16)  # bí mật chỉ trong bộ nhớ
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.web = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row)
        cls.chu = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row)  # đường ghi nguồn tin cậy (chủ bảng)
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_m4b_pg_"))                      # giữ lại
        cls.trich6 = _Trich6Gia()
        cls.svc = XayDungK2(cls.web, cls.goc / "m4-k2", conn_tin_cay=cls.chu, trich6=cls.trich6)
        cls.XayDungK2 = XayDungK2
        cls.run_id = uuid.uuid4().hex[:8]  # nonce của lần chạy — KHÔNG đặt tên `run` (che unittest.TestCase.run)
        cls.s = {"replay": []}

    @classmethod
    def tearDownClass(cls):
        for c in (cls.web, cls.chu, cls.admin):
            c.close()  # chỉ đóng kết nối; giữ DB/role/thư mục làm bằng chứng

    # ------------------------------------------------------------------ helpers
    def K(self, ten: str) -> str:
        return f"m4b-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchone()[0]

    def du_an(self, ma):
        return str(self.q("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)))

    def dem(self) -> dict:
        return {t: self.q(f"SELECT count(*) FROM m4.{t}") for t in BANG} | {"hop_dong": self.q("SELECT count(*) FROM master.hop_dong")}

    def loi(self, fn, *a, **k) -> str:
        try:
            fn(*a, **k)
        except DataError as exc:
            return exc.code
        except psycopg.Error as exc:
            p = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
            return p if re.fullmatch(r"[A-Z][A-Z0-9_]*", p) else type(exc).__name__
        self.fail("thao tác không bị chặn")

    def web_sql(self, login, sql, params=()):
        dt = self.svc.danh_tinh(login)
        with self.svc._tx(dt):
            return self.web.execute(sql, params).fetchall()

    def lam(self, login, ten_lenh, **kw):
        """Gọi lệnh lần đầu và ghi lại để replay sau (cùng key/body/revision gốc). `ten_lenh` = tên phương thức service; KHÔNG đặt `ten`
        (trùng business keyword `ten` của tao_hop_dong → TypeError trước khi gọi lệnh)."""
        r = getattr(self.svc, ten_lenh)(login, **kw)
        self.assertFalse(r["lap_lai"], (ten_lenh, r))
        self.s["replay"].append((login, ten_lenh, kw, r))
        return r

    def tai(self, login, raw, ten, media, vai, khoa, du_an=None):
        return self.svc.tai_tep(login, raw, du_an_id=du_an or self.du_an("DA_XD_A1"), vai_tro=vai, ten=ten, media_type=media, khoa=self.K(khoa))

    def rev(self, hd):
        return self.q("SELECT revision FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (hd,))

    def can_nguon(self):
        if not _nguon_da_nap():
            self.skipTest("Lõi nguồn chưa nạp (Root chạy tools/nap_nguon_review_m4.py) — NOT_RUN")

    # ------------------------------------------------------------------ T01
    def test_t01_migrate_va_seed(self):
        from kho_tri_thuc.k2 import m4_demo
        self.assertGreaterEqual(self.version, 17)
        self.assertIsNone(self.q("SELECT to_regprocedure('m4.ket_thuc(text, jsonb)')::text"))
        kq = m4_demo.khoi_tao(self.admin)
        self.assertEqual(kq["trang_thai"], "DU", kq)
        self.assertEqual(kq["dem"]["actor"], 8)
        lai = m4_demo.khoi_tao(self.admin)
        self.assertEqual(lai["trang_thai"], "DU", lai)
        self.assertTrue(lai["mo_lai_khong_them"])
        self.assertEqual((lai["dem"]["actor"], lai["dem"]["phan_quyen"], lai["dem"]["quyen_du_an"]), (0, 0, 0))

    # ------------------------------------------------------------------ T02
    def test_t02_nhan_tep(self):
        raw = F.hop_dong_docx()
        thieu = self.XayDungK2(self.web, self.goc / "khong-tin-cay")
        self.assertEqual(self.loi(thieu.tai_tep, A1, raw, du_an_id=self.du_an("DA_XD_A1"), vai_tro="HOP_DONG", ten="hd.docx",
                                  media_type=F.MEDIA_DOCX, khoa=self.K("t02-0")), "M4_CHUA_SAN_SANG_GHI_NGUON")
        self.assertFalse((self.goc / "khong-tin-cay" / "m4-raw").exists())
        truoc = self.dem()
        r = self.tai(A1, raw, "Hợp đồng DEMO.docx", F.MEDIA_DOCX, "HOP_DONG", "t02-1")
        self.assertTrue(r["hang_moi"])
        self.assertEqual((self.goc / "m4-k2" / "m4-raw" / r["sha256"]).read_bytes(), raw)
        with patch("kho_tri_thuc.k2.xay_dung.write_immutable", _cam):
            lai = self.tai(A1, raw, "Hợp đồng DEMO.docx", F.MEDIA_DOCX, "HOP_DONG", "t02-1")
        self.assertEqual({**lai, "lap_lai": False}, r)
        self.assertTrue(lai["lap_lai"])
        self.assertEqual(self.loi(self.tai, A1, raw, "Tên khác.docx", F.MEDIA_DOCX, "HOP_DONG", "t02-1"), "M4_IDEMPOTENCY_KHAC")
        khac = self.tai(A1, raw, "Hợp đồng DEMO.docx", F.MEDIA_DOCX, "HOP_DONG", "t02-2")
        self.assertEqual((khac["tep_id"], khac["hang_moi"]), (r["tep_id"], False))
        self.assertEqual(self.loi(self.tai, A1, raw, "../hd.docx", F.MEDIA_DOCX, "HOP_DONG", "t02-3"), "M4_TEN_TEP_SAI")
        self.assertEqual(self.loi(self.tai, A1, raw, "hd.pdf", "application/pdf", "HOP_DONG", "t02-4"), "M4_TEP_MEDIA_KHONG_KHOP")
        sau = self.dem()
        self.assertEqual(sau["tep"], truoc["tep"] + 1)
        self.assertEqual(sau["bien_nhan"], truoc["bien_nhan"] + 2)
        # CSDL tự chặn tên có ký tự điều khiển/đường dẫn kể cả trên đường tin cậy (CHECK, không dùng chr(0))
        dt = self.svc.danh_tinh(A1)
        for ten in ("a" + chr(1) + ".docx", "../a.docx"):
            def ghi(ten=ten):
                with self.svc._tx_tin_cay(dt) as c:
                    c.execute("SELECT m4.ghi_tep(%s, %s::uuid, 'HOP_DONG', %s, 10::bigint, %s, %s)",
                              (self.K("t02-sql-" + str(len(ten))), self.du_an("DA_XD_A1"), "b" * 64, F.MEDIA_DOCX, ten))
            self.assertEqual(self.loi(ghi), "CheckViolation", ten)
        self.s["tep_hd"] = r["tep_id"]

    # ------------------------------------------------------------------ T03
    def test_t03_gia_mao_bang_app_thuong(self):
        du_an = self.du_an("DA_XD_A1")
        truoc = self.dem()
        gia = (("SELECT m4.ghi_tep('k1', %s::uuid, 'HOP_DONG', repeat('a', 64), 1::bigint, 'application/pdf', 'x.pdf')", (du_an,)),
               ("SELECT m4.ghi_trich_xuat('k2', gen_random_uuid(), 1, gen_random_uuid(), repeat('a', 64), 'c', 'e', 'QUY_TAC_KHONG_AI', 'XONG', NULL, "
                "'{}'::jsonb, '[]'::jsonb)", ()),
               ("SELECT m4.ghi_boq('k3', gen_random_uuid(), 1, gen_random_uuid(), repeat('a', 64), NULL, 'BOQ', 1, '{}'::jsonb, 'b', '[]'::jsonb, "
                "'[]'::jsonb, '[]'::jsonb)", ()),
               ("SELECT m4.sua_tham_so('k4', gen_random_uuid(), 1, 'TT-32', 'CO_GIA_TRI', '1', NULL, NULL, 'x', NULL, 'OK giả')", ()),
               ("SELECT m4._bn_ghi(gen_random_uuid(), 'k5', 'NOP', %s::uuid, '{}'::jsonb, '{\"nop_id\": \"gia\"}'::jsonb)", (du_an,)),
               ("INSERT INTO m4.bien_nhan (nguoi_dung_id, du_an_id, hanh_dong, khoa, yeu_cau, body_sha256, ket_qua) "
                "SELECT id, %s::uuid, 'NOP', 'k6', '{}'::jsonb, repeat('a', 64), '{}'::jsonb FROM master.nguoi_dung LIMIT 1", (du_an,)),
               ("INSERT INTO m4.tep (phap_nhan_id, du_an_id, vai_tro_tai_lieu, raw_sha256, byte_length, media_type, ten_goc, object_key, tao_boi) "
                "SELECT phap_nhan_id, id, 'HOP_DONG', repeat('a', 64), 1, 'application/pdf', 'x.pdf', 'm4-raw/' || repeat('a', 64), 'gia' "
                "FROM master.du_an WHERE id = %s::uuid", (du_an,)),
               ("UPDATE m4.trich_xuat SET trang_thai = 'XONG'", ()),
               ("UPDATE m4.boq SET trang_thai = 'DA_MAP'", ()),
               ("UPDATE m4.tham_so SET kiem_tra = 'OK giả'", ()))
        for sql, params in gia:
            self.assertEqual(self.loi(self.web_sql, A1, sql, params), "InsufficientPrivilege", sql[:60])
        self.assertEqual(self.dem(), truoc)
        # đường tin cậy không thay quyền: actor của phiên (reviewer) không có SOAN → bị chặn dù kết nối là chủ bảng
        dt = self.svc.danh_tinh(REVIEW)

        def ghi():
            with self.svc._tx_tin_cay(dt) as c:
                c.execute("SELECT m4.ghi_tep(%s, %s::uuid, 'HOP_DONG', %s, 10::bigint, %s, 'r.docx')", (self.K("t03-rv"), du_an, "c" * 64, F.MEDIA_DOCX))
        self.assertEqual(self.loi(ghi), "M4_KHONG_CO_QUYEN_DU_AN")
        self.assertEqual(self.dem(), truoc)

    # ------------------------------------------------------------------ T04
    def test_t04_luong_day_du_va_replay(self):
        self.can_nguon()
        du_an = self.du_an("DA_XD_A1")
        hd = self.lam(A1, "tao_hop_dong", du_an_id=du_an, so_hop_dong=f"HDXD-01B-{self.run_id}", ten="Gói thầu DEMO 01B", khoa=self.K("hd"))["hop_dong_id"]
        self.s["hd"] = hd
        tep = self.s.get("tep_hd") or self.tai(A1, F.hop_dong_docx(), "Hợp đồng DEMO.docx", F.MEDIA_DOCX, "HOP_DONG", "t04-tep")["tep_id"]
        self.assertEqual(self.lam(A1, "gan_tep_hop_dong", hop_dong_id=hd, revision=1, tep_id=tep, khoa=self.K("gan"))["revision"], 2)
        tr = self.lam(A1, "trich", hop_dong_id=hd, revision=2, khoa=self.K("trich"))
        self.assertEqual((tr["trang_thai"], tr["che_do"], tr["revision"]), ("XONG", "QUY_TAC_KHONG_AI", 3), tr)
        # tham số: phòng dự án nhập theo ORACLE THỦ CÔNG (bảng PHIEU_THAM_SO, dựng từ fixtures_m4.DONG_HOP_DONG + danh mục 37 mã), KHÔNG theo
        # trạng thái CHUA_CO của parser. Giá trị có trong HĐ → CO_GIA_TRI + trích dẫn nguyên văn + máy kiểm thật OK; tạm ứng → KHONG_AP_DUNG có
        # trích dẫn Điều 3.1 (máy kiểm thật); chỉ mã thật sự vắng → KHONG_QUY_DINH có lý do.
        from kho_tri_thuc.m4.sql_m17 import DANH_MUC_THAM_SO
        ten_ma = {m: t for m, _, t in DANH_MUC_THAM_SO}
        self.assertEqual(set(PHIEU_THAM_SO) | set(VANG), set(ten_ma))          # partition độc lập: đủ 37 mã, không chồng
        self.assertEqual(set(PHIEU_THAM_SO) & set(VANG), set())
        for ma, (tt, gia_tri, don_vi, dieu, trich) in PHIEU_THAM_SO.items():  # oracle bám đúng câu chữ fixture
            self.assertTrue(any(trich in dong for dong in F.DONG_HOP_DONG), (ma, trich))
            if gia_tri is not None:
                self.assertIn(gia_tri, trich, ma)
        self.assertEqual(self.loi(self.svc.sua_tham_so, A1, hop_dong_id=hd, revision=3, ma="TT-32", trang_thai_tham_so="CO_GIA_TRI",
                                  gia_tri="18 tháng", trich_dan="Thời hạn bảo hành là 18 tháng", khoa=self.K("sua-sai")), "M4_TRICH_DAN_KHONG_KHOP")
        for ma, (tt, gia_tri, don_vi, dieu, trich) in PHIEU_THAM_SO.items():
            ly_do = None if tt == "CO_GIA_TRI" else "HĐ Điều 3.1 ghi: Tạm ứng: Không áp dụng"
            kq = self.lam(A1, "sua_tham_so", hop_dong_id=hd, revision=self.rev(hd), ma=ma, trang_thai_tham_so=tt, gia_tri=gia_tri, don_vi=don_vi,
                          dieu_khoan=dieu, trich_dan=trich, ly_do=ly_do, khoa=self.K(f"sua-{ma}"))
            self.assertTrue(str(kq["kiem_tra"]).startswith("OK"), (ma, kq))  # máy kiểm thật trên văn bản HĐ nguồn
        for ma in VANG:
            kq = self.lam(A1, "sua_tham_so", hop_dong_id=hd, revision=self.rev(hd), ma=ma, trang_thai_tham_so="KHONG_QUY_DINH",
                          ly_do=f"HĐ DEMO không có điều khoản về: {ten_ma[ma]}", khoa=self.K(f"sua-{ma}"))
            self.assertIsNone(kq["kiem_tra"], ma)
        luu = {r[0]: (r[1], r[2], r[3]) for r in self.admin.execute(
            "SELECT ma, trang_thai, gia_tri, trich_dan FROM m4.tham_so WHERE hop_dong_id = %s", (hd,))}
        mong = {ma: (tt, gia_tri, trich) for ma, (tt, gia_tri, _, _, trich) in PHIEU_THAM_SO.items()} | {ma: ("KHONG_QUY_DINH", None, None) for ma in VANG}
        self.assertEqual(luu, mong)
        xn = self.lam(A1, "xac_nhan", hop_dong_id=hd, revision=self.rev(hd), ly_do="Phòng dự án đã soát", khoa=self.K("xn"))
        self.assertIsNotNone(xn["xac_nhan_id"])
        # phụ lục: khai có-chưa-đủ → thêm dự thảo có tệp → hủy → khai không có
        self.lam(A1, "khai_phu_luc", hop_dong_id=hd, revision=self.rev(hd), khai="CO_CHUA_DU", khoa=self.K("khai-1"))
        tep_pl = self.tai(A1, F.pdf_demo("PL1"), "PL1.pdf", "application/pdf", "PHU_LUC", "t04-pl")["tep_id"]
        pl = self.lam(A1, "them_phu_luc", hop_dong_id=hd, revision=self.rev(hd), so_pl="PL-01", ngay_ky="2026-02-01", ngay_hieu_luc="2026-02-01",
                      trang_thai_phu_luc="DU_THAO", doi_boq=False, noi_dung="Dự thảo DEMO", tep_id=tep_pl, khoa=self.K("pl"))["phu_luc_id"]
        self.lam(A1, "huy_phu_luc", phu_luc_id=pl, revision=self.rev(hd), ly_do="Không ký", khoa=self.K("huy"))
        self.lam(A1, "khai_phu_luc", hop_dong_id=hd, revision=self.rev(hd), khai="KHONG_CO", khoa=self.K("khai-2"))
        # BOQ: đọc/map đủ, lệch KL×ĐG ở HM-03 (dòng Excel 4) → DA_MAP + phát hiện, giữ ô gốc
        tep_boq = self.tai(A1, F.boq_xlsx(F.BOQ_LOI_SO_HOC), "BOQ.xlsx", F.MEDIA_XLSX, "BOQ", "t04-boq")["tep_id"]
        boq = self.lam(A1, "boq_nhap", hop_dong_id=hd, revision=self.rev(hd), tep_id=tep_boq, sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT),
                       khoa=self.K("boq"))
        self.assertEqual((boq["trang_thai"], boq["loi_chan"], [p["dong"] for p in boq["phat_hien"]]), ("DA_MAP", [], [4]), boq)
        o = self.q("SELECT o_goc FROM m4.boq_dong WHERE boq_id = %s AND ma_rieng = 'HM-03'", (boq["boq_id"],))
        self.assertEqual(o["thanh_tien"], {"tho": "999", "kieu": "SO", "o": "G4"})
        # đợt + hồ sơ bắt buộc đợt 1 → nộp thật
        dot = self.lam(A1, "tao_dot", hop_dong_id=hd, so_dot=1, ngay_nghiem_thu="2026-03-01", khoa=self.K("dot"))["dot_id"]
        rev_dot = 1
        for i, (muc,) in enumerate(self.admin.execute("SELECT ma FROM m4.danh_muc_ho_so_dot WHERE bat_buoc_dot_dau ORDER BY ma").fetchall()):
            t = self.tai(A1, F.pdf_demo(f"HS{i}"), f"ho-so-{i}.pdf", "application/pdf", "HO_SO_DOT", f"t04-hs-{i}")["tep_id"]
            rev_dot = self.lam(A1, "gan_tep_dot", dot_id=dot, revision=rev_dot, tep_id=t, muc=muc, khoa=self.K(f"gan-dot-{i}"))["revision"]
            self.s["tep_dot"] = t
        rev_dot = self.lam(A1, "sua_dot", dot_id=dot, revision=rev_dot, ngay_nghiem_thu="2026-03-02", khoa=self.K("sua-dot"))["revision"]
        self.assertEqual(self.svc.chi_tiet_dot(A1, dot)["thieu"], [])
        nop = self.lam(A1, "nop", dot_id=dot, revision_ho_so=self.rev(hd), revision_dot=rev_dot, khoa=self.K("nop"))
        self.assertRegex(nop["digest"], r"^[0-9a-f]{64}$")
        snap = self.q("SELECT snapshot FROM m4.nop WHERE id = %s", (nop["nop_id"],))
        self.assertEqual([b["so_phat_hien"] for b in snap["boq"]], [1])
        self.assertEqual(snap["xac_nhan_id"], xn["xac_nhan_id"])
        self.s["dot_nop"] = dot
        # ---- replay sau các thay đổi hợp lệ về sau: đúng key/body/revision gốc → đúng kết quả cũ, không xử lý/ghi lại
        truoc = self.dem()
        with patch.object(self.trich6, "trich", _cam), patch.object(NR, "trich_hop_dong", _cam), \
                patch.object(NR, "boq_doc", _cam), patch.object(NR, "van_ban_hop_dong", _cam), \
                patch("kho_tri_thuc.k2.xay_dung.write_immutable", _cam):
            for login, ten_lenh, kw, r in self.s["replay"]:
                lai = getattr(self.svc, ten_lenh)(login, **kw)
                self.assertTrue(lai["lap_lai"], ten_lenh)
                self.assertEqual({**lai, "lap_lai": False}, r, ten_lenh)
        self.assertEqual(self.dem(), truoc)
        # cùng key, body khác → từ chối, không thêm hàng
        for login, ten_lenh, kw, _ in self.s["replay"]:
            doi = dict(kw)
            if "revision" in doi:
                doi["revision"] += 100
            elif "revision_dot" in doi:
                doi["revision_dot"] += 100
            elif "so_dot" in doi:
                doi["so_dot"] += 1
            else:
                doi["ten"] = doi["ten"] + " (khác)"
            self.assertEqual(self.loi(getattr(self.svc, ten_lenh), login, **doi), "M4_IDEMPOTENCY_KHAC", ten_lenh)
        self.assertEqual(self.dem(), truoc)

    # ------------------------------------------------------------------ T05
    def test_t05_dong_thoi_cung_khoa(self):
        hd = self.lam(A1, "tao_hop_dong", du_an_id=self.du_an("DA_XD_A1"), so_hop_dong=f"HDXD-DT-{self.run_id}", ten="Đồng thời", khoa=self.K("hd-dt"))
        hd = hd["hop_dong_id"]
        truoc = self.dem()
        ket, loi, rao = [], [], threading.Barrier(2)

        def chay():
            c = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
            try:
                svc = self.XayDungK2(c, self.goc / "m4-k2", conn_tin_cay=None)
                rao.wait(30)
                ket.append(svc.tao_dot(A1, hop_dong_id=hd, so_dot=1, ngay_nghiem_thu="2026-04-01", khoa=self.K("dot-dt")))
            except Exception as exc:  # noqa: BLE001 — ghi lại để assert, không nuốt
                loi.append(exc)
            finally:
                c.close()
        th = [threading.Thread(target=chay) for _ in range(2)]
        for t in th:
            t.start()
        for t in th:
            t.join(120)
        self.assertFalse(any(t.is_alive() for t in th), "treo/deadlock — không tính PASS")
        self.assertEqual(loi, [])
        self.assertEqual(ket[0]["dot_id"], ket[1]["dot_id"])
        self.assertEqual(sorted(k["lap_lai"] for k in ket), [False, True])
        sau = self.dem()
        self.assertEqual((sau["dot"], sau["bien_nhan"]), (truoc["dot"] + 1, truoc["bien_nhan"] + 1))

    # ------------------------------------------------------------------ T06
    def test_t06_track_changes_qua_sua_tham_so(self):
        import os as _os
        import shutil
        import subprocess
        du_an = self.du_an("DA_XD_A1")
        raw = F.hop_dong_docx(track_changes=True)
        hd = self.svc.tao_hop_dong(A1, du_an_id=du_an, so_hop_dong=f"HDXD-TC-{self.run_id}", ten="Track Changes", khoa=self.K("hd-tc"))["hop_dong_id"]
        tep = self.tai(A1, raw, "HĐ còn sửa đổi.docx", F.MEDIA_DOCX, "HOP_DONG", "t06-tep")
        self.svc.gan_tep_hop_dong(A1, hop_dong_id=hd, revision=1, tep_id=tep["tep_id"], khoa=self.K("gan-tc"))
        lam_viec = self.goc / "m4-k2" / "m4-lam-viec"
        truoc = sorted(p.name for p in lam_viec.iterdir()) if lam_viec.exists() else []
        cam = [patch.object(subprocess, "run", _cam), patch.object(subprocess, "Popen", _cam), patch.object(shutil, "rmtree", _cam),
               patch.object(_os, "system", _cam)] + ([patch.object(_os, "startfile", _cam)] if hasattr(_os, "startfile") else [])
        for p in cam:
            p.start()
        try:
            ma = self.loi(self.svc.sua_tham_so, A1, hop_dong_id=hd, revision=2, ma="TT-32", trang_thai_tham_so="CO_GIA_TRI", gia_tri="12 tháng",
                          trich_dan="Thời hạn bảo hành là 12 tháng", khoa=self.K("sua-tc"))
        finally:
            for p in reversed(cam):
                p.stop()
        self.assertEqual(ma, "M4_DOCX_CON_SUA_DOI")
        self.assertEqual(sorted(p.name for p in lam_viec.iterdir()) if lam_viec.exists() else [], truoc)
        self.assertEqual((self.goc / "m4-k2" / "m4-raw" / tep["sha256"]).read_bytes(), raw)
        self.assertEqual(self.rev(hd), 2)

    # ------------------------------------------------------------------ T07
    def test_t07_boq_so_khong_doc_duoc_chan_nop(self):
        self.can_nguon()
        du_an = self.du_an("DA_XD_A1")
        hd = self.svc.tao_hop_dong(A1, du_an_id=du_an, so_hop_dong=f"HDXD-BOQ-{self.run_id}", ten="BOQ lỗi", khoa=self.K("hd-boq"))["hop_dong_id"]
        t = self.tai(A1, F.boq_xlsx(F.BOQ_TEN_GIA_LOI), "BOQ lỗi.xlsx", F.MEDIA_XLSX, "BOQ", "t07-boq")["tep_id"]
        b = self.svc.boq_nhap(A1, hop_dong_id=hd, revision=1, tep_id=t, sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT), khoa=self.K("boq-loi"))
        self.assertEqual(b["trang_thai"], "CO_LOI")
        self.assertIn(("BOQ_SO_KHONG_DOC_DUOC", 2), [(x["ma"], x["dong"]) for x in b["loi_chan"]])
        self.assertEqual([(x["ma"], x["dong"]) for x in b["phat_hien"]], [("BOQ_SO_HOC_LECH", 4)])
        hm01 = self.q("SELECT jsonb_build_object('kl', kl, 'o', o_goc->'kl') FROM m4.boq_dong WHERE boq_id = %s AND ma_rieng = 'HM-01'", (b["boq_id"],))
        self.assertEqual(hm01, {"kl": None, "o": {"tho": "abc", "kieu": "CHU", "o": "E2"}})
        dot = self.svc.tao_dot(A1, hop_dong_id=hd, so_dot=1, ngay_nghiem_thu="2026-03-01", khoa=self.K("dot-boq"))["dot_id"]
        thieu = {x["ma"] for x in self.svc.chi_tiet_dot(A1, dot)["thieu"]}
        self.assertTrue({"BOQ_CO_LOI", "HD_CHUA_CO_TEP", "PL_CHUA_KHAI"} <= thieu, thieu)
        self.assertEqual(self.loi(self.svc.nop, A1, dot_id=dot, revision_ho_so=self.rev(hd), revision_dot=1, khoa=self.K("nop-boq")),
                         "M4_CHUA_DU_CAN_CU")

    # ------------------------------------------------------------------ T08
    def test_t08_pham_vi(self):
        du_an_a1 = self.du_an("DA_XD_A1")
        hd = self.svc.tao_hop_dong(A1, du_an_id=du_an_a1, so_hop_dong=f"HDXD-PV-{self.run_id}", ten="Phạm vi", khoa=self.K("hd-pv"))["hop_dong_id"]
        truoc = self.dem()
        self.assertEqual(self.loi(self.svc.chi_tiet, B1, hd), "M4_KHONG_THAY_HOP_DONG")
        self.assertEqual(self.loi(self.svc.chi_tiet, A2, hd), "M4_KHONG_THAY_HOP_DONG")
        for login in (B1, A2, KT_PT, KHONG_M4, REVIEW):
            self.assertEqual(self.loi(self.svc.tao_hop_dong, login, du_an_id=du_an_a1, so_hop_dong=f"X-{login}", ten="x", khoa=self.K(f"pv-{login}")),
                             "M4_KHONG_CO_QUYEN_DU_AN", login)
        self.assertEqual(self.loi(self.svc.khai_phu_luc, REVIEW, hop_dong_id=hd, revision=1, khai="KHONG_CO", khoa=self.K("pv-rv")),
                         "M4_KHONG_CO_QUYEN_DU_AN")
        self.assertEqual(self.dem(), truoc)
        if "dot_nop" in self.s:  # reviewer xác nhận tham số: bị chặn; bit đã nộp theo phạm vi
            self.assertEqual(self.loi(self.svc.xac_nhan, REVIEW, hop_dong_id=self.s["hd"], revision=self.rev(self.s["hd"]), khoa=self.K("pv-xn")),
                             "M4_KHONG_CO_QUYEN_DU_AN")
            sql = "SELECT m4.tep_da_nop(%s::uuid) AS b"
            self.assertTrue(self.web_sql(A1, sql, (self.s["tep_dot"],))[0]["b"])
            self.assertTrue(self.web_sql(REVIEW, sql, (self.s["tep_dot"],))[0]["b"])
            self.assertFalse(self.web_sql(B1, sql, (self.s["tep_dot"],))[0]["b"])
            self.assertFalse(self.web_sql(A2, sql, (self.s["tep_dot"],))[0]["b"])
            self.assertEqual(self.loi(self.svc.tai_ve, B1, self.s["tep_dot"]), "M4_KHONG_THAY_TEP")
            self.assertEqual(len(self.svc.tai_ve(REVIEW, self.s["tep_dot"])[2]) > 0, True)  # reviewer hợp lệ đọc được tệp đợt đã nộp

    # ------------------------------------------------------------------ T09
    def test_t09_thu_hoi_du_an(self):
        from kho_tri_thuc.k2 import m4_demo
        du_an = self.du_an("DA_XD_A2")
        k_hd = self.K("hd-a2")
        hd = self.svc.tao_hop_dong(A2, du_an_id=du_an, so_hop_dong=f"HDXD-A2-{self.run_id}", ten="A2", khoa=k_hd)["hop_dong_id"]
        tep = self.tai(A2, F.pdf_demo("A2"), "a2.pdf", "application/pdf", "HOP_DONG", "t09-tep", du_an=du_an)["tep_id"]
        self.assertEqual(self.web_sql(A2, "SELECT count(*) AS n FROM m4.bien_nhan")[0]["n"], 2)
        q = self.q("""SELECT q.id FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                      WHERE n.dang_nhap = %s AND q.du_an_id = %s AND q.vai = 'PHU_TRACH' AND q.thu_hoi_luc IS NULL""", (A2, du_an))
        so_quyen = self.q("SELECT count(*) FROM m4.quyen_du_an")
        self.admin.execute("SELECT m4.thu_hoi_quyen_du_an(%s, 'MO_PHONG_QUAN_TRI_TEST', 'Kiểm thu hồi dự án M4-01B')", (q,))
        self.assertEqual(self.loi(self.svc.tao_hop_dong, A2, du_an_id=du_an, so_hop_dong=f"HDXD-A2-{self.run_id}", ten="A2", khoa=k_hd),
                         "M4_KHONG_CO_QUYEN_DU_AN")  # replay đúng key/body bị chặn
        self.assertEqual(self.loi(self.svc.chi_tiet, A2, hd), "M4_KHONG_THAY_HOP_DONG")
        self.assertEqual(self.loi(self.svc.tai_ve, A2, tep), "M4_KHONG_THAY_TEP")
        self.assertEqual(self.web_sql(A2, "SELECT count(*) AS n FROM m4.bien_nhan")[0]["n"], 0)
        self.assertEqual(self.loi(self.web_sql, A2, "SELECT m4.tra_bien_nhan(%s) AS r", (k_hd,)), "M4_KHONG_CO_QUYEN_DU_AN")
        # actor vẫn hoạt động, module M4 còn; quyền giữ lịch sử, không xóa; không gỡ được dấu thu hồi
        self.assertEqual(self.q("SELECT trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (A2,)), "HOAT_DONG")
        self.assertTrue(self.q("""SELECT 'M4' = ANY(p.module) FROM master.phan_quyen p JOIN master.nguoi_dung n ON n.id = p.nguoi_dung_id
                                  WHERE n.dang_nhap = %s""", (A2,)))
        self.assertEqual(self.q("SELECT count(*) FROM m4.quyen_du_an"), so_quyen)
        self.assertIsNotNone(self.q("SELECT thu_hoi_luc FROM m4.quyen_du_an WHERE id = %s", (q,)))

        def go():
            self.admin.execute("UPDATE m4.quyen_du_an SET thu_hoi_luc = NULL, thu_hoi_boi = NULL, thu_hoi_ly_do = NULL WHERE id = %s", (q,))
        self.assertEqual(self.loi(go), "M4_QUYEN_BAT_BIEN")
        lai = m4_demo.khoi_tao(self.admin)
        a2 = next(a for a in lai["actor"] if a["dang_nhap"] == A2)
        self.assertEqual((lai["trang_thai"], a2["trang_thai"], a2["da_thu_hoi"]), ("THIEU", "DA_THU_HOI", ["DA_XD_A2:PHU_TRACH"]))
        self.assertEqual(self.q("SELECT count(*) FROM m4.quyen_du_an"), so_quyen)
        # reviewer thu hồi REVIEW trên A1 → bit đã nộp của tệp A1 không còn đọc được
        if "tep_dot" in self.s:
            qr = self.q("""SELECT q.id FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                           WHERE n.dang_nhap = %s AND q.du_an_id = %s AND q.vai = 'REVIEW' AND q.thu_hoi_luc IS NULL""", (REVIEW, self.du_an("DA_XD_A1")))
            self.admin.execute("SELECT m4.thu_hoi_quyen_du_an(%s, 'MO_PHONG_QUAN_TRI_TEST', 'Kiểm thu hồi review')", (qr,))
            self.assertFalse(self.web_sql(REVIEW, "SELECT m4.tep_da_nop(%s::uuid) AS b", (self.s["tep_dot"],))[0]["b"])
            self.assertEqual(self.loi(self.svc.tai_ve, REVIEW, self.s["tep_dot"]), "M4_KHONG_THAY_TEP")
            self.assertEqual(self.q("SELECT trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (REVIEW,)), "HOAT_DONG")

    # ------------------------------------------------------------------ T10
    def test_t10_factory_may_chu(self):
        from kho_tri_thuc.giao_dien import m4 as m4_http
        from kho_tri_thuc.giao_dien.server import LocalApp
        tam = Path(tempfile.mkdtemp(prefix="ktt_m4b_factory_"))
        cau_hinh = tam / "cau_hinh_fixture.toml"
        cau_hinh.write_text(CAU_HINH_FIXTURE, encoding="utf-8")
        with patch.dict(os.environ, {LocalApp.CRM_ENV: self.app_dsn, LocalApp.CRM_ENV_ADMIN: self.dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"}):
            app = LocalApp(cau_hinh, tam / "web-co")
            svc = m4_http.dich_vu(app)
            self.assertIsNotNone(svc.conn_tin_cay)
            self.assertIsNone(svc.ly_do_chua_san_sang)
        with patch.dict(os.environ, {LocalApp.CRM_ENV: self.app_dsn, LocalApp.CRM_ENV_DB_KIEM_THU: "1"}):
            os.environ.pop(LocalApp.CRM_ENV_ADMIN, None)  # patch.dict khôi phục khi ra khỏi khối
            app2 = LocalApp(cau_hinh, tam / "web-khong")
            svc2 = m4_http.dich_vu(app2)
            self.assertIsNone(svc2.conn_tin_cay)
            self.assertEqual(self.loi(svc2.tai_tep, A1, F.pdf_demo("F"), du_an_id=self.du_an("DA_XD_A1"), vai_tro="HOP_DONG", ten="f.pdf",
                                      media_type="application/pdf", khoa=self.K("t10")), "M4_CHUA_SAN_SANG_GHI_NGUON")
        self.assertFalse((tam / "web-khong" / "m4-k2" / "m4-raw").exists())


if __name__ == "__main__":
    unittest.main()
