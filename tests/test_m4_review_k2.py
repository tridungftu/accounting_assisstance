"""M4-02A — kiểm PostgreSQL THẬT cho dịch vụ Review L1/L2 (XayDungK2.review_*). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Chạy khi Root cấp KHO_PG_DSN_TEST qua env lúc chạy (không đọc .env/var, không hardcode credentials). DB MỚI `kho_test_m4r_*` migrate mặc định (1–19),
seed CRM DEMO + M4 DEMO; login ứng dụng tạm (NOSUPERUSER NOBYPASSRLS IN ROLE app_web) + kết nối chủ bảng làm đường tin cậy (inject như factory).
Worker Review là tiến trình con thật (python -m kho_tri_thuc.m4.review_compute) — cần lõi nguồn đã nạp + openpyxl; thiếu → skip = NOT_RUN.
Không DROP/DELETE/TRUNCATE/cleanup — DB/role/thư mục giữ làm bằng chứng. Không probe DELETE.

R01 dựng hồ sơ: HĐ (oracle tham số thủ công của M4-01B) → BOQ gốc → đợt 1 có tệp hồ sơ .xlsx DEMO → Nộp; đợt 2 nháp có .xlsx; một .xlsx không gắn đợt.
R02 SOAN L1 (không đợt): chạy → kết quả + coverage K1–K8 + artifact; tải báo cáo đúng hash; replay đúng khóa/body trả FINAL TRƯỚC khi tính (worker bị cấm);
    đổi body cùng khóa → M4_IDEMPOTENCY_KHAC; 0 delta.
R03 SOAN L1+L2 đợt đã nộp: luôn PARTIAL ở gói này (B5/lũy kế đợt trước đã duyệt chưa có nguồn → INCOMPLETE), đủ 17 mã coverage, TRUOC không ok.
R04 reviewer CHỈ có REVIEW (không SOAN): chạy được trên đúng tệp của đợt đã nộp, replay FINAL; âm: đợt nháp, không đợt, tệp không gắn đợt → phạm vi,
    0 delta (run/biên nhận/thư mục chạy); reviewer không đọc được lần chạy L1 không đợt của A1.
R05 basis đổi trước chạy → M4_REVIEW_CO_SO_DOI (không tạo run); đổi trong lúc tính → STALE, không công bố, giữ artifact.
R06 ghép tay đúng HĐ/BOQ hiện hành → revision; replay; đích không hiệu lực/sai BOQ nguồn → DICH_KHONG_HIEU_LUC (0 delta); chạy lại cùng tệp gốc → run con mới, run/kết quả cũ nguyên hash.
R07 đồng thời hai kết nối cùng khóa/body → một run.
R08 thu hồi assignment REVIEW giữa lúc tính → CANCELLED (không công bố); sau đó replay/đọc/tải bị chặn theo quyền hiện hành; actor vẫn hoạt động.
FIX01 (docs/GIAO-SUA-M4-02A-01-KHEP-RUNTIME-VA-UI.md):
R1 trong R03 — TT-21 KHONG_QUY_DINH + giữ lại vắng → INCOMPLETE; TT-10 KHONG_AP_DUNG tường minh là đối chứng dương.
R2 trong R02/R07b — đầu vào/nhật ký worker không có DSN; guard yêu cầu mà không nạp → worker dừng mã 4, FAILED, không ket_qua.json.
R4 R07b — raw hỏng sau RUNNING → FAILED có bằng chứng (không RUNNING vĩnh viễn); thử lại đúng khóa/body đọc cùng FINAL.
R5 R07c — cùng actor+khóa khác hành động (Review↔M17) xung đột chính xác cả tuần tự lẫn đồng thời, không treo.
R6 R07d — đích ghép = dòng BOQ hiệu lực theo engine tại ngày NT (PL THAY/THEM đã ký vs PL tương lai), mã không hiệu lực bị từ chối.
FIX02 (docs/GIAO-SUA-M4-02A-02-GUARD-MOUNT-VA-RECEIPT.md):
F1 R07b — cha gửi dấu vân hook khác hook thật của con → dừng mã 4, FAILED (không gỡ/vá guard thật).
F3 R07b — worker thật exit 0 nhưng mã thoát báo 5 + JSON trông như thành công → FAILED, không công bố, giữ RESULT/LOG/INPUT/BASIS; retry cùng FINAL.
F4 R07e — rào có kiểm soát: lệnh M17 cùng khóa commit khi Review đã giữ chỗ và đang trong RR → M17 bị chặn, Review thắng duy nhất; ngược thứ tự
   → Review bị chặn ở giữ chỗ, 0 delta; đúng body → FINAL trước khi chụp basis.
FIX03 (docs/GIAO-SUA-M4-02A-03-GUARD-CHILD-VA-REFRESH.md): F1 trong R02 — worker thật (cwd riêng, khác cwd máy chủ) không bị từ chối guard.
FIX04 (docs/GIAO-SUA-M4-02A-04-PHAM-VI-VA-KIEM-THU.md):
R00 — DB riêng migrate tới 19 (trạng thái DEMO đã áp M19) + seed → nâng lên 20: lịch sử 1–19 (version/checksum/thời điểm) và dữ liệu nguyên
   trạng, ACL/chủ/SECURITY DEFINER/STABLE/search_path của review_quyen giữ nguyên, migrate lại không đổi. R01 — DB mới lên đúng 1–20.
R01b — mỗi ca trên cặp kết nối MỚI, không đợt: A1 soạn → SOAN; B1 ngoài dự án → M4_KHONG_CO_QUYEN_DU_AN; reviewer → M4_REVIEW_PHAM_VI (không
   SQLSTATE 55000); qua dịch vụ cũng 0 delta. R07d — khóa tải BOQ gốc/phụ lục khác khóa nhập BOQ của từng tệp.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import subprocess
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
try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nguon_review as NR
from kho_tri_thuc.m4 import review_compute as RC

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
A1, REVIEW = "MO_PHONG_DU_AN_A1", "MO_PHONG_REVIEW_M4"
BANG = ("review_run", "review_result", "review_artifact", "review_manual_map", "review_giu_khoa", "bien_nhan", "nhat_ky")


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


def ho_so_xlsx(nhan: str = "KY1") -> bytes:
    """Hồ sơ thanh toán DEMO (chỉ giá trị, không công thức): sheet tổng hợp có nhãn số đề nghị + bảng chi tiết KL × đơn giá theo BOQ gốc DEMO,
    thêm một dòng tên gần giống (ứng viên ghép tay). Dữ liệu DEMO viết tay, không lấy từ engine."""
    wb = openpyxl.Workbook()
    th = wb.active
    th.title = "TH"
    for i, (nhan_o, v) in enumerate((("Hồ sơ " + nhan, None), ("Giá trị hợp đồng", 1_000_000_000), ("Giá trị thực hiện kỳ này", 9_500_000),
                                     ("Đề nghị thanh toán kỳ này", 8_550_000)), 1):
        th.cell(i, 1, nhan_o)
        if v is not None:
            th.cell(i, 3, v)
    ct = wb.create_sheet("ChiTiet")
    for j, t in enumerate(("STT", "Nội dung công việc", "Đơn vị tính", "Khối lượng hợp đồng", "Khối lượng kỳ này", "Đơn giá", "Thành tiền"), 1):
        ct.cell(1, j, t)
    dong = ((1, "Đào đất hố móng", "m3", 100, 40, 50000, 2_000_000), (2, "Bê tông móng", "m3", 20, 5, 1_500_000, 7_500_000),
            (3, "Đào đất hố móng thủ công", "m3", 10, 0, 50000, 0), (4, "Vận chuyển đất", "m3", 30, 2, 25000, 50000))
    for i, r in enumerate(dong, 2):
        for j, v in enumerate(r, 1):
            ct.cell(i, j, v)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PG M4-02A không chạy (NOT_RUN, không tính đạt)")
class M4ReviewPG(unittest.TestCase):
    """Chạy theo thứ tự tên r01…r08 trên MỘT DB; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, m4_demo
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cls.db = "kho_test_m4r_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = m4_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m4r_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.web = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row)
        cls.chu = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row)
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_m4r_pg_"))  # giữ lại
        cls.svc = XayDungK2(cls.web, cls.goc / "m4-k2", conn_tin_cay=cls.chu)
        cls.XayDungK2 = XayDungK2
        cls.run_id = uuid.uuid4().hex[:8]
        cls.s = {}
        cls.ket_noi_phu = []

    @classmethod
    def tearDownClass(cls):
        for c in (cls.web, cls.chu, cls.admin, *cls.ket_noi_phu):
            c.close()  # chỉ đóng kết nối do test mở; giữ DB/role/thư mục làm bằng chứng

    # ------------------------------------------------------------------ helpers
    def setUp(self):
        if self._testMethodName == "test_r00_nang_19_len_20":  # DB riêng, chỉ migrate/seed — không cần lõi nguồn hay hồ sơ R01
            return
        if not (_nguon_da_nap() and openpyxl is not None):
            self.skipTest("Lõi nguồn Review chưa nạp hoặc thiếu openpyxl — NOT_RUN")
        if self._testMethodName != "test_r01_dung_ho_so" and "dot1" not in self.s:
            self.skipTest("R01 chưa dựng được hồ sơ — NOT_RUN")

    def K(self, ten: str) -> str:
        return f"m4r-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchone()[0]

    def du_an(self, ma):
        return str(self.q("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)))

    def rev(self, hd):
        return self.q("SELECT revision FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (hd,))

    def rev_dot(self, dot):
        return self.q("SELECT revision FROM m4.dot WHERE id = %s", (dot,))

    def dem(self) -> dict:
        thu_muc = self.goc / "m4-k2" / "m4-review-run"
        return {t: self.q(f"SELECT count(*) FROM m4.{t}") for t in BANG} | {"thu_muc_chay": len(list(thu_muc.iterdir())) if thu_muc.is_dir() else 0}

    def loi(self, fn, *a, **k) -> str:
        try:
            fn(*a, **k)
        except DataError as exc:
            return exc.code
        except psycopg.Error as exc:
            p = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
            return p if re.fullmatch(r"[A-Z][A-Z0-9_]*", p) else type(exc).__name__
        self.fail("thao tác không bị chặn")

    def tai(self, raw, ten, media, vai, khoa):
        return self.svc.tai_tep(A1, raw, du_an_id=self.du_an("DA_XD_A1"), vai_tro=vai, ten=ten, media_type=media, khoa=self.K(khoa))["tep_id"]

    def co_so(self, login, *, tep, dot=None, che_do=None, hd=None, o_dich=None):
        ds = self.svc.review_ds(login, hop_dong_id=hd, dot_id=dot, tep_id=tep, che_do=che_do, o_dich=o_dich)
        self.assertTrue(ds["co_so"]["san_sang"], ds["co_so"])
        return ds["co_so"]

    def chay(self, login, *, tep, dot=None, che_do="L1", khoa, o_dich=None, exp=None):
        exp = exp or self.co_so(login, tep=tep, dot=dot, che_do=che_do, o_dich=o_dich)["basis_sha256"]
        return self.svc.review_chay(login, du_an_id=self.du_an("DA_XD_A1"), tep_id=tep, mode=che_do, dot_id=dot, o_dich=o_dich, expected_basis=exp,
                                    khoa=self.K(khoa))

    # ------------------------------------------------------------------ R01
    def test_r01_dung_ho_so(self):
        from tests.test_m4_01b_pg import PHIEU_THAM_SO, VANG  # oracle thủ công từ DOCX nguồn + danh mục (không lấy từ parser)
        self.assertEqual(self.version, 20)  # FIX04: DB mới lên đúng 1–20 (M20 cuối)
        self.assertEqual([r[0] for r in self.admin.execute("SELECT version FROM master.schema_migrations ORDER BY version")], list(range(1, 21)))
        self.assertEqual(self.seed["trang_thai"], "DU", self.seed)
        sv, du_an = self.svc, self.du_an("DA_XD_A1")
        hd = sv.tao_hop_dong(A1, du_an_id=du_an, so_hop_dong=f"HDXD-RV-{self.run_id}", ten="Gói thầu Review DEMO", khoa=self.K("hd"))["hop_dong_id"]
        tep_hd = self.tai(F.hop_dong_docx(), "Hợp đồng DEMO.docx", F.MEDIA_DOCX, "HOP_DONG", "tep-hd")
        sv.gan_tep_hop_dong(A1, hop_dong_id=hd, revision=self.rev(hd), tep_id=tep_hd, khoa=self.K("gan"))
        tr = sv.trich(A1, hop_dong_id=hd, revision=self.rev(hd), khoa=self.K("trich"))
        self.assertEqual(tr["trang_thai"], "XONG", tr)
        for ma, (tt, gia_tri, don_vi, dieu, trich) in PHIEU_THAM_SO.items():
            sv.sua_tham_so(A1, hop_dong_id=hd, revision=self.rev(hd), ma=ma, trang_thai_tham_so=tt, gia_tri=gia_tri, don_vi=don_vi, dieu_khoan=dieu,
                           trich_dan=trich, ly_do=None if tt == "CO_GIA_TRI" else "HĐ Điều 3.1 ghi: Tạm ứng: Không áp dụng", khoa=self.K("sua-" + ma))
        for ma in VANG:
            sv.sua_tham_so(A1, hop_dong_id=hd, revision=self.rev(hd), ma=ma, trang_thai_tham_so="KHONG_QUY_DINH", ly_do="HĐ DEMO không có điều khoản này",
                           khoa=self.K("sua-" + ma))
        sv.xac_nhan(A1, hop_dong_id=hd, revision=self.rev(hd), ly_do="Phòng dự án đã soát", khoa=self.K("xn"))
        sv.khai_phu_luc(A1, hop_dong_id=hd, revision=self.rev(hd), khai="KHONG_CO", khoa=self.K("khai"))
        tep_boq = self.tai(F.boq_xlsx(F.BOQ_GOC), "BOQ.xlsx", F.MEDIA_XLSX, "BOQ", "tep-boq")
        boq = sv.boq_nhap(A1, hop_dong_id=hd, revision=self.rev(hd), tep_id=tep_boq, sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT), khoa=self.K("boq"))
        self.assertEqual(boq["trang_thai"], "DA_MAP", boq)
        # đợt 1: tệp hồ sơ .xlsx + đủ mục bắt buộc → Nộp
        dot1 = sv.tao_dot(A1, hop_dong_id=hd, so_dot=1, ngay_nghiem_thu="2026-03-01", khoa=self.K("dot1"))["dot_id"]
        x1 = self.tai(ho_so_xlsx("KY1"), "ho_so_ky1.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "x1")
        muc = [r[0] for r in self.admin.execute("SELECT ma FROM m4.danh_muc_ho_so_dot WHERE bat_buoc_dot_dau ORDER BY ma").fetchall()]
        sv.gan_tep_dot(A1, dot_id=dot1, revision=self.rev_dot(dot1), tep_id=x1, muc=muc[0], khoa=self.K("gan-x1"))
        for i, m in enumerate(muc):
            t = self.tai(F.pdf_demo(f"RV{i}"), f"hs-{i}.pdf", "application/pdf", "HO_SO_DOT", f"hs-{i}")
            sv.gan_tep_dot(A1, dot_id=dot1, revision=self.rev_dot(dot1), tep_id=t, muc=m, khoa=self.K(f"gan-{i}"))
        self.assertEqual(sv.chi_tiet_dot(A1, dot1)["thieu"], [])
        sv.nop(A1, dot_id=dot1, revision_ho_so=self.rev(hd), revision_dot=self.rev_dot(dot1), khoa=self.K("nop1"))
        self.assertEqual(self.q("SELECT trang_thai FROM m4.dot WHERE id = %s", (dot1,)), "DA_NOP")
        # đợt 2 nháp có .xlsx; một .xlsx cùng dự án không gắn đợt nào
        dot2 = sv.tao_dot(A1, hop_dong_id=hd, so_dot=2, ngay_nghiem_thu=None, khoa=self.K("dot2"))["dot_id"]
        x2 = self.tai(ho_so_xlsx("KY2"), "ho_so_ky2.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "x2")
        sv.gan_tep_dot(A1, dot_id=dot2, revision=self.rev_dot(dot2), tep_id=x2, muc=muc[0], khoa=self.K("gan-x2"))
        x3 = self.tai(ho_so_xlsx("LE"), "ho_so_le.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "x3")
        self.s.update(hd=hd, dot1=dot1, dot2=dot2, x1=x1, x2=x2, x3=x3, boq=boq["boq_id"])

    # ------------------------------------------------------------------ R01b FIX04: phạm vi KHÔNG đợt trên kết nối owner/app MỚI cho từng ca
    def _svc_moi(self):
        """Cặp kết nối thực sự MỚI (backend chưa từng chạy hàm Review nào có đợt) — không dùng lại backend của các ca trước."""
        web = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
        chu = psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)
        self.ket_noi_phu.extend([web, chu])
        return self.XayDungK2(web, self.goc / "m4-k2", conn_tin_cay=chu)

    def test_r01b_pham_vi_khong_dot_ket_noi_moi(self):
        du_an, x3 = self.du_an("DA_XD_A1"), self.s["x3"]

        def kiem(login, tep):
            sv = self._svc_moi()
            dt = sv.danh_tinh(login)
            with sv._tx_review(dt) as c:
                return sv._r1(c, "SELECT m4.review_kiem(%s::uuid, NULL::uuid, %s::uuid) AS q", (du_an, tep))["q"]
        # dương: actor soạn đúng dự án, không đợt → SOAN (kết nối mới)
        self.assertEqual(kiem(A1, x3), "SOAN")
        # âm: actor ngoài dự án (khác PN) → mã domain, KHÔNG phải SQLSTATE 55000 / lỗi chung
        self.assertEqual(self.loi(kiem, "MO_PHONG_DU_AN_B1", x3), "M4_KHONG_CO_QUYEN_DU_AN")
        # âm: reviewer không đợt → M4_REVIEW_PHAM_VI (kết nối mới)
        self.assertEqual(self.loi(kiem, REVIEW, self.s["x1"]), "M4_REVIEW_PHAM_VI")
        # cùng qua dịch vụ trên kết nối mới, trước mọi giữ chỗ/lần chạy (0 delta)
        d0 = self.dem()
        exp = "0" * 64
        for login, tep, ma in (("MO_PHONG_DU_AN_B1", x3, "M4_KHONG_CO_QUYEN_DU_AN"), (REVIEW, self.s["x1"], "M4_REVIEW_PHAM_VI")):
            sv = self._svc_moi()
            self.assertEqual(self.loi(sv.review_chay, login, du_an_id=du_an, tep_id=tep, mode="L1", expected_basis=exp, khoa=self.K("r01b-" + login)), ma)
        self.assertEqual(self.dem(), d0)
        # hàm thật trên DB là bản M20 (không còn record đợt chưa gán)
        dn = self.q("SELECT pg_get_functiondef('m4.review_quyen(uuid, uuid, uuid)'::regprocedure)")
        self.assertIn("%ROWTYPE", dn)
        self.assertNotIn("d record", dn)

    # ------------------------------------------------------------------ R00 FIX04: DB đã ở 19 nâng lên 20 — 1–19 và dữ liệu cũ nguyên trạng
    def test_r00_nang_19_len_20(self):
        from kho_tri_thuc.ha_tang import pg_migrations as PM
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.ha_tang.primitives import sha256
        from kho_tri_thuc.k2 import m4_demo
        db = "kho_test_m4r19_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{db}" ENCODING \'UTF8\' TEMPLATE template0')
        dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + db
        c = psycopg.connect(dsn, autocommit=True)
        self.ket_noi_phu.append(c)
        lich_su = lambda: [tuple(r) for r in c.execute("SELECT version, checksum, applied_at FROM master.schema_migrations ORDER BY version")]  # noqa: E731
        self.assertEqual(pg.migrate(c, 19), 19)  # trạng thái của DB DEMO đã áp M19
        self.assertEqual(pg.schema_version(c), 19)
        self.assertEqual([r[0] for r in lich_su()], list(range(1, 20)))
        # FIX05: KHÔNG gọi seed CRM (crm_demo.khoi_tao tự migrate mặc định lên 20 → baseline không còn là 19). Dựng đúng hai pháp nhân DEMO mà
        # m4_demo cần bằng schema hiện có (nhãn DEMO; không seed CRM/M9, không hồ sơ đã duyệt, không quyền giả), rồi gọi seed M4 THẬT.
        for ma, ten, don_vi in (("PN_DEMO_A", "Pháp nhân DEMO A — fixture nâng 19→20", "DEMO_A"),
                                ("PN_DEMO_B", "Pháp nhân DEMO B — fixture nâng 19→20", "DEMO_B")):
            c.execute("INSERT INTO master.phap_nhan (ma, ten, ma_don_vi_junsky) VALUES (%s,%s,%s) ON CONFLICT (ma) DO NOTHING", (ma, ten, don_vi))
        self.assertEqual(c.execute("SELECT count(*) FROM master.phap_nhan WHERE ma IN ('PN_DEMO_A','PN_DEMO_B')").fetchone()[0], 2)
        seed = m4_demo.khoi_tao(c)
        self.assertEqual(seed["trang_thai"], "DU", seed)
        # baseline nâng cấp THỰC SỰ dừng ở 19 sau seed, trước khi chụp lịch sử/số dòng/ACL
        self.assertEqual(pg.schema_version(c), 19)
        self.assertEqual([r[0] for r in lich_su()], list(range(1, 20)))
        dem = lambda: {t: c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in  # noqa: E731
                       ("master.nguoi_dung", "master.du_an", "m4.quyen_du_an", "m4.bien_nhan", "m4.nhat_ky", "m4.review_run", "m4.review_giu_khoa")}
        acl = lambda: c.execute("""SELECT p.proacl::text, p.proowner, p.prosecdef, p.provolatile, p.proconfig::text FROM pg_proc p
                                   WHERE p.oid = 'm4.review_quyen(uuid, uuid, uuid)'::regprocedure""").fetchone()  # noqa: E731
        ls19, dem19, acl19 = lich_su(), dem(), acl()
        self.assertEqual([r[:2] for r in ls19], [(i + 1, sha256("\n".join(PM.PG_MIGRATIONS[i]).encode())) for i in range(19)])
        self.assertEqual(pg.migrate(c), 20)
        ls20 = lich_su()
        self.assertEqual(ls20[:19], ls19)  # 1–19: version/checksum/thời điểm áp dụng nguyên trạng
        self.assertEqual(ls20[19][:2], (20, sha256("\n".join(PM.M0020_M4_REVIEW_QUYEN).encode())))
        self.assertEqual(dem(), dem19)  # dữ liệu/hồ sơ/lịch sử cũ không đổi
        self.assertEqual(acl(), acl19)  # chủ sở hữu/ACL/SECURITY DEFINER/STABLE/search_path giữ nguyên
        self.assertEqual(pg.migrate(c), 20)  # chạy lại: không đổi
        self.assertEqual(lich_su(), ls20)
        self.assertIn("%ROWTYPE", c.execute("SELECT pg_get_functiondef('m4.review_quyen(uuid, uuid, uuid)'::regprocedure)").fetchone()[0])

    # ------------------------------------------------------------------ R02
    def test_r02_soan_l1_replay_doi_body(self):
        x1 = self.s["x1"]
        truoc = self.dem()
        cs = self.co_so(A1, tep=x1, che_do="L1")
        self.assertEqual(cs["quyen"], "SOAN")
        r = self.chay(A1, tep=x1, che_do="L1", khoa="l1", exp=cs["basis_sha256"])
        self.assertFalse(r["lap_lai"])
        self.assertIn(r["trang_thai"], ("SUCCEEDED", "PARTIAL"), r)
        ct = self.svc.review_chi_tiet(A1, r["run_id"])
        kq = ct["ket_qua"]
        self.assertEqual(set(kq["coverage"]), set(RC.MA_L1))
        self.assertTrue(kq["cong_bo"])
        self.assertEqual(kq["ket_qua"]["raw_sha256"], self.q("SELECT raw_sha256 FROM m4.tep WHERE id = %s", (x1,)))
        self.assertEqual(kq["ket_qua"]["basis_sha256"], cs["basis_sha256"])
        loai = {a["loai"] for a in ct["artifact"]}
        self.assertTrue({"BASIS", "INPUT", "LOG", "RESULT", "REPORT_L1", "REPORT_L1_NGUON"} <= loai, loai)
        rep = next(a for a in ct["artifact"] if a["loai"] == "REPORT_L1")
        ten, media, raw = self.svc.review_tai(A1, r["run_id"], rep["id"])
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw), media), (rep["raw_sha256"], rep["byte_length"], NR.MEDIA_XLSX))
        wb = openpyxl.load_workbook(io.BytesIO(raw))
        self.assertEqual(wb.sheetnames[0], "Pham vi kiem")  # companion chi phối báo cáo tải về
        sau = self.dem()
        self.assertEqual((sau["review_run"], sau["review_result"], sau["thu_muc_chay"]), (truoc["review_run"] + 1, truoc["review_result"] + 1,
                                                                                        truoc["thu_muc_chay"] + 1))
        # replay đúng khóa/body: FINAL trả TRƯỚC mọi tính toán
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("replay không được tính lại")), \
                patch.object(self.XayDungK2, "_co_so", side_effect=AssertionError("replay không chụp lại basis")):
            lai = self.chay(A1, tep=x1, che_do="L1", khoa="l1", exp=cs["basis_sha256"])
        self.assertEqual((lai["lap_lai"], lai["run_id"], lai["trang_thai"]), (True, r["run_id"], r["trang_thai"]))
        self.assertEqual(self.dem(), sau)
        # đổi body cùng khóa → 409 trước khi tính
        self.assertEqual(self.loi(self.chay, A1, tep=x1, che_do="L1", khoa="l1", o_dich="TH!C4", exp=cs["basis_sha256"]), "M4_IDEMPOTENCY_KHAC")
        self.assertEqual(self.dem(), sau)
        # FIX01 R2: đầu vào/nhật ký worker không mang DSN/credential
        thu_muc = self.goc / "m4-k2" / "m4-review-run" / r["run_id"]
        for ten in ("vao.json", "worker.log", "co_so.json"):
            self.assertNotIn(b"postgresql://", (thu_muc / ten).read_bytes(), ten)
        # FIX03 F1: worker THẬT chạy với cwd = thư mục lần chạy (khác cwd máy chủ) vẫn được nhận guard (không bị dấu vân frozen-stdlib phụ thuộc CWD)
        self.assertNotIn(b"GUARD_KHONG_NAP", (thu_muc / "worker.log").read_bytes())
        self.assertNotEqual(str(thu_muc.resolve()), os.getcwd())
        self.s["run_l1"] = r["run_id"]

    # ------------------------------------------------------------------ R03
    def test_r03_soan_l1_l2_dot_da_nop(self):
        x1, dot1 = self.s["x1"], self.s["dot1"]
        cs = self.co_so(A1, tep=x1, dot=dot1, che_do="L1_L2")
        self.assertFalse(cs["phu_thuoc"]["TRUOC"]["ok"])
        self.assertTrue(cs["phu_thuoc"]["BOQ"]["ok"])
        r = self.chay(A1, tep=x1, dot=dot1, che_do="L1_L2", khoa="l2", exp=cs["basis_sha256"])
        # lũy kế đợt trước đã duyệt chưa có nguồn ở gói này → B5 INCOMPLETE → không bao giờ SUCCEEDED (dù là đợt 1)
        self.assertEqual(r["trang_thai"], "PARTIAL", r)
        kq = self.svc.review_chi_tiet(A1, r["run_id"])["ket_qua"]
        self.assertEqual(set(kq["coverage"]), set(RC.MA_L1) | set(RC.MA_L2))
        self.assertEqual(kq["coverage"]["B5"]["trang_thai"], "INCOMPLETE")
        l2 = kq["ket_qua"]["lop2"]
        self.assertTrue(l2["chay"], l2.get("ly_do"))
        for h in l2["bang_lop2"]:
            self.assertIn("ket_qua_nguon", h)
            self.assertIn(h["trang_thai_kiem"], RC.THU_TU)
        # FIX01 R1 trên dữ liệu thật: TT-21 = KHONG_QUY_DINH (HĐ DEMO không nói giữ lại) + hồ sơ không có dòng giữ lại → INCOMPLETE, không KHONG_AP_DUNG;
        # đối chứng: TT-10 KHONG_AP_DUNG tường minh (Điều 3.1, đã xác nhận) → dòng thu hồi tạm ứng vắng số có căn cứ
        self.assertFalse(l2["phu_thuoc"]["TT-21"]["tuong_minh_khong_ap_dung"])
        self.assertTrue(l2["phu_thuoc"]["TT-10"]["tuong_minh_khong_ap_dung"])
        self.assertEqual(l2["so_tong_hop_tho"]["giu_lai"]["trang_thai"], "MISSING")
        giu = [h for h in l2["bang_lop2"] if str(h.get("ten", "")).startswith("Giữ lại = tỷ lệ giữ lại HĐ (TT-21)")]
        for h in giu:
            self.assertEqual(h["trang_thai_kiem"], "INCOMPLETE", h)
        self.assertNotIn(kq["coverage"]["B8"]["trang_thai"], RC.DAT_DU)
        self.s["run_l2"] = r["run_id"]
        self.s["l2"] = l2

    # ------------------------------------------------------------------ R04
    def test_r04_reviewer_chi_review(self):
        x1, x2, x3, dot1, dot2 = (self.s[k] for k in ("x1", "x2", "x3", "dot1", "dot2"))
        cs = self.co_so(REVIEW, tep=x1, dot=dot1, che_do="L1_L2")
        self.assertEqual(cs["quyen"], "REVIEW")  # không có SOAN
        r = self.chay(REVIEW, tep=x1, dot=dot1, che_do="L1_L2", khoa="rv", exp=cs["basis_sha256"])
        self.assertIn(r["trang_thai"], ("SUCCEEDED", "PARTIAL"), r)
        self.assertEqual(self.q("SELECT quyen FROM m4.review_run WHERE id = %s", (r["run_id"],)), "REVIEW")
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("replay không được tính lại")):
            lai = self.chay(REVIEW, tep=x1, dot=dot1, che_do="L1_L2", khoa="rv", exp=cs["basis_sha256"])
        self.assertEqual((lai["lap_lai"], lai["run_id"]), (True, r["run_id"]))
        # âm: chính xác theo phạm vi, TRƯỚC biên nhận/raw; 0 delta
        truoc = self.dem()
        exp = cs["basis_sha256"]
        for tep, dot, che_do, khoa in ((x2, dot2, "L1_L2", "rv-nhap"), (x1, None, "L1", "rv-khong-dot"), (x3, dot1, "L1", "rv-tep-le")):
            self.assertEqual(self.loi(self.chay, REVIEW, tep=tep, dot=dot, che_do=che_do, khoa=khoa, exp=exp), "M4_REVIEW_PHAM_VI", khoa)
            # danh sách: tệp ngoài phạm vi đọc của reviewer bị RLS ẩn (không thấy tệp) hoặc chặn phạm vi Review — cả hai đều trước khi chụp basis
            self.assertIn(self.loi(self.svc.review_ds, REVIEW, tep_id=tep, dot_id=dot, che_do=che_do), ("M4_REVIEW_PHAM_VI", "M4_KHONG_THAY_TEP"), khoa)
        self.assertEqual(self.dem(), truoc)
        self.assertEqual(self.loi(self.svc.review_chi_tiet, REVIEW, self.s["run_l1"]), "M4_REVIEW_KHONG_THAY")  # L1 không đợt của A1
        ds = self.svc.review_ds(REVIEW, hop_dong_id=self.s["hd"])
        self.assertNotIn(self.s["run_l1"], {x["id"] for x in ds["runs"]})
        self.assertIn(r["run_id"], {x["id"] for x in ds["runs"]})
        self.s["run_rv"] = r["run_id"]

    # ------------------------------------------------------------------ R05
    def test_r05_basis_doi(self):
        x1, dot1, dot2 = self.s["x1"], self.s["dot1"], self.s["dot2"]
        cu = self.co_so(A1, tep=x1, dot=dot1, che_do="L1_L2")["basis_sha256"]
        self.svc.sua_dot(A1, dot_id=dot2, revision=self.rev_dot(dot2), ngay_nghiem_thu="2026-04-01", khoa=self.K("sua-dot2-a"))
        truoc = self.dem()
        self.assertEqual(self.loi(self.chay, A1, tep=x1, dot=dot1, che_do="L1_L2", khoa="cu", exp=cu), "M4_REVIEW_CO_SO_DOI")
        self.assertEqual(self.dem()["review_run"], truoc["review_run"])
        # đổi trong lúc tính: kết quả giữ làm bằng chứng nhưng STALE, không công bố
        moi = self.co_so(A1, tep=x1, dot=dot1, che_do="L1_L2")["basis_sha256"]
        goc = self.XayDungK2._review_tinh

        def tinh_roi_doi(svc, *a, **k):
            out = goc(svc, *a, **k)
            svc.sua_dot(A1, dot_id=dot2, revision=self.rev_dot(dot2), ngay_nghiem_thu="2026-04-02", khoa=self.K("sua-dot2-b"))
            return out
        with patch.object(self.XayDungK2, "_review_tinh", tinh_roi_doi):
            r = self.chay(A1, tep=x1, dot=dot1, che_do="L1_L2", khoa="stale", exp=moi)
        self.assertEqual(r["trang_thai"], "STALE", r)
        self.assertFalse(r["cong_bo"])
        ct = self.svc.review_chi_tiet(A1, r["run_id"])
        self.assertFalse(ct["ket_qua"]["cong_bo"])
        self.assertNotEqual(ct["ket_qua"]["basis_cong_bo_sha256"], moi)
        self.assertIn("RESULT", {a["loai"] for a in ct["artifact"]})

    # ------------------------------------------------------------------ R06
    def test_r06_ghep_tay_va_chay_lai(self):
        run, l2 = self.s.get("run_l2"), self.s.get("l2")
        if not run:
            self.skipTest("R03 chưa có lần chạy L1+L2 — NOT_RUN")
        dong = next((h for h in l2.get("doi_chieu_hm") or [] if h.get("khoa")), None)
        if dong is None:
            self.skipTest("Nguồn không tạo dòng đối chiếu hạng mục cho hồ sơ DEMO — ghép tay NOT_RUN")
        x1, dot1 = self.s["x1"], self.s["dot1"]
        truoc_kq = self.q("SELECT ket_qua_sha256 FROM m4.review_result WHERE run_id = %s", (run,))
        truoc_art = sorted(self.admin.execute("SELECT loai, raw_sha256 FROM m4.review_artifact WHERE run_id = %s", (run,)).fetchall())
        cs = self.co_so(A1, tep=x1, dot=dot1, che_do="L1_L2")
        g = dict(run_id=run, khoa_dong=dong["khoa"], boq_id=self.s["boq"], ma_hm="HM-01", expected_basis=cs["basis_sha256"], ly_do="Cùng công việc đào đất")
        truoc_map = self.dem()
        self.assertEqual(self.loi(self.svc.review_ghep, A1, **{**g, "ma_hm": "HM-KHONG-CO"}, khoa=self.K("ghep-sai")), "M4_REVIEW_DICH_KHONG_HIEU_LUC")
        self.assertEqual(self.loi(self.svc.review_ghep, A1, **{**g, "boq_id": str(uuid.uuid4())}, khoa=self.K("ghep-sai-boq")),
                         "M4_REVIEW_DICH_KHONG_HIEU_LUC")  # đúng mã nhưng sai BOQ nguồn hiệu lực
        self.assertEqual(self.dem(), truoc_map)  # từ chối trước map/nhật ký/biên nhận
        m = self.svc.review_ghep(A1, **g, khoa=self.K("ghep"))
        self.assertEqual((m["revision"], m["ma_hm"], m["lap_lai"]), (1, "HM-01", False))
        self.assertIn("CÙNG hợp đồng", m["pham_vi"])
        lai = self.svc.review_ghep(A1, **g, khoa=self.K("ghep"))
        self.assertEqual((lai["map_id"], lai["lap_lai"]), (m["map_id"], True))
        self.assertEqual(self.loi(self.svc.review_ghep, A1, **g, khoa=self.K("ghep-cu")), "M4_REVIEW_CO_SO_DOI")  # basis đã có map mới
        cs2 = self.co_so(A1, tep=x1, dot=dot1, che_do="L1_L2")
        self.assertEqual(cs2["so_ghep_tay"], 1)
        con = self.svc.review_chay_lai(A1, run_id=run, expected_basis=cs2["basis_sha256"], khoa=self.K("chay-lai"))
        self.assertNotEqual(con["run_id"], run)
        self.assertEqual(self.q("SELECT parent_run_id FROM m4.review_run WHERE id = %s", (con["run_id"],)), uuid.UUID(run))
        self.assertEqual(self.q("SELECT raw_sha256 FROM m4.review_run WHERE id = %s", (con["run_id"],)),
                         self.q("SELECT raw_sha256 FROM m4.review_run WHERE id = %s", (run,)))  # cùng tệp gốc
        self.assertEqual(self.q("SELECT ket_qua_sha256 FROM m4.review_result WHERE run_id = %s", (run,)), truoc_kq)
        self.assertEqual(sorted(self.admin.execute("SELECT loai, raw_sha256 FROM m4.review_artifact WHERE run_id = %s", (run,)).fetchall()), truoc_art)
        for loai, sha in truoc_art:
            self.assertEqual(hashlib.sha256((self.goc / "m4-k2" / "m4-review" / sha).read_bytes()).hexdigest(), sha, loai)

    # ------------------------------------------------------------------ R07
    def test_r07_dong_thoi_cung_khoa(self):
        x1 = self.s["x1"]
        web2 = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
        chu2 = psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)
        self.ket_noi_phu.extend([web2, chu2])
        svc2 = self.XayDungK2(web2, self.goc / "m4-k2", conn_tin_cay=chu2)
        exp = self.co_so(A1, tep=x1, che_do="L1")["basis_sha256"]
        truoc = self.dem()["review_run"]
        kq, loi = [], []

        def mot(svc):
            try:
                kq.append(svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("dong-thoi")))
            except Exception as exc:  # noqa: BLE001
                loi.append(exc)
        ts = [threading.Thread(target=mot, args=(s,)) for s in (self.svc, svc2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(1200)
        self.assertEqual(loi, [])
        self.assertEqual(len({r["run_id"] for r in kq}), 1, kq)
        self.assertEqual(sorted(r["lap_lai"] for r in kq), [False, True])
        self.assertEqual(self.dem()["review_run"], truoc + 1)

    # ------------------------------------------------------------------ R07b FIX01 R4/R2: lỗi dựng sau RUNNING và guard không nạp → FAILED kết thúc
    def test_r07b_loi_dung_va_guard(self):
        x1 = self.s["x1"]
        exp = self.co_so(A1, tep=x1, che_do="L1")["basis_sha256"]
        with patch.object(self.XayDungK2, "_raw", side_effect=DataError("M4_TEP_HONG_LUU_TRU", "giả lập raw hỏng trong kho")):
            r = self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("setup-loi"))
        self.assertEqual(r["trang_thai"], "FAILED", r)
        self.assertEqual(self.q("SELECT trang_thai FROM m4.review_run WHERE id = %s", (r["run_id"],)), "FAILED")  # không RUNNING vĩnh viễn
        self.assertIn("SETUP_LOI", self.q("SELECT ly_do FROM m4.review_run WHERE id = %s", (r["run_id"],)) or "")
        self.assertFalse(self.q("SELECT cong_bo FROM m4.review_result WHERE run_id = %s", (r["run_id"],)))
        self.assertIn("BASIS", {x[0] for x in self.admin.execute("SELECT loai FROM m4.review_artifact WHERE run_id = %s", (r["run_id"],)).fetchall()})
        # thử lại ĐÚNG khóa/body: đọc cùng FINAL đã kết thúc, không tính lại, không khóa mới
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("không tính lại")):
            lai = self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("setup-loi"))
        self.assertEqual((lai["run_id"], lai["trang_thai"], lai["lap_lai"]), (r["run_id"], "FAILED", True))
        # FIX02 F1: cha gửi dấu vân hook KHÁC hook thật của con (sai ràng buộc) → con dừng mã 4 trước mọi I/O → FAILED, không ket_qua.json.
        # Không gỡ/vá guard thật; chỉ đổi dữ kiện provenance mà máy chủ gửi.
        from kho_tri_thuc.m4.review_compute import ENV_GUARD_DAU, HAM_XOA
        sai = {"ham": {f"{m}.{t}": {"goc": False, "module": "hook_gia", "qualname": t, "tep": "/khong/phai/guard_goc.py"} for m, t in HAM_XOA},
               "khoi_dong": {}}
        goc_env = self.XayDungK2._env_worker
        with patch.object(self.XayDungK2, "_env_worker", classmethod(lambda cls, *a, **k: {**goc_env(*a, **k), ENV_GUARD_DAU: json.dumps(sai)})):
            g = self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("guard"))
        self.assertEqual(g["trang_thai"], "FAILED", g)
        self.assertIn("GUARD_KHONG_NAP", self.q("SELECT ly_do FROM m4.review_run WHERE id = %s", (g["run_id"],)) or "")
        self.assertFalse((self.goc / "m4-k2" / "m4-review-run" / g["run_id"] / "ket_qua.json").exists())
        # FIX02 F3: worker thật chạy xong (exit 0, JSON thành công đúng raw/basis) nhưng mã thoát báo khác 0 → KHÔNG công bố thành công;
        # JSON/stdout/stderr giữ làm bằng chứng; thử lại đúng khóa trả cùng FINAL
        goc_w = self.XayDungK2._chay_worker

        def exit_khac_0(svc, thu_muc):
            p = goc_w(svc, thu_muc)
            self.assertEqual(p.returncode, 0, p.stderr)  # đối chứng: tiến trình thật kết thúc bình thường, có ket_qua.json không rỗng
            return subprocess.CompletedProcess(p.args, 5, p.stdout, p.stderr)
        with patch.object(self.XayDungK2, "_chay_worker", exit_khac_0):
            n = self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("exit5"))
        self.assertEqual(n["trang_thai"], "FAILED", n)
        self.assertFalse(n["cong_bo"])
        self.assertIn("WORKER_EXIT_5", self.q("SELECT ly_do FROM m4.review_run WHERE id = %s", (n["run_id"],)) or "")
        kq_file = json.loads((self.goc / "m4-k2" / "m4-review-run" / n["run_id"] / "ket_qua.json").read_text(encoding="utf-8"))
        self.assertIn(kq_file["trang_thai"], ("SUCCEEDED", "PARTIAL"))  # JSON trông như thành công vẫn không được nhận
        self.assertEqual({x[0] for x in self.admin.execute("SELECT loai FROM m4.review_artifact WHERE run_id = %s", (n["run_id"],)).fetchall()}
                         & {"RESULT", "LOG", "INPUT", "BASIS"}, {"RESULT", "LOG", "INPUT", "BASIS"})
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("không tính lại")):
            lai = self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("exit5"))
        self.assertEqual((lai["run_id"], lai["trang_thai"], lai["lap_lai"]), (n["run_id"], "FAILED", True))

    # ------------------------------------------------------------------ R07c FIX01 R5: cùng actor+khóa khác hành động → xung đột chính xác, không deadlock
    def test_r07c_khoa_cheo_hanh_dong(self):
        x1, hd = self.s["x1"], self.s["hd"]
        so_dot = lambda: self.q("SELECT count(*) FROM m4.dot WHERE hop_dong_id = %s", (hd,))  # noqa: E731
        truoc = so_dot()
        # khóa đã được lần chạy Review dùng → lệnh M17 cùng khóa bị chặn trong cùng giao dịch hiệu lực (không tạo đợt)
        self.assertEqual(self.loi(self.svc.tao_dot, A1, hop_dong_id=hd, so_dot=90, ngay_nghiem_thu=None, khoa=self.K("l1")), "M4_IDEMPOTENCY_KHAC")
        self.assertEqual(so_dot(), truoc)
        # ngược lại: khóa đã dùng cho lệnh M17 → Review cùng khóa bị chặn trước khi tạo lần chạy
        self.svc.tao_dot(A1, hop_dong_id=hd, so_dot=91, ngay_nghiem_thu=None, khoa=self.K("m17-truoc"))
        n = self.dem()["review_run"]
        self.assertEqual(self.loi(self.chay, A1, tep=x1, che_do="L1", khoa="m17-truoc"), "M4_IDEMPOTENCY_KHAC")
        self.assertEqual(self.dem()["review_run"], n)
        # đồng thời trên hai cặp kết nối: Review và tạo đợt cùng khóa mới → đúng một bên hiệu lực, bên kia xung đột chính xác, không treo
        web2 = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
        chu2 = psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)
        self.ket_noi_phu.extend([web2, chu2])
        svc2 = self.XayDungK2(web2, self.goc / "m4-k2", conn_tin_cay=chu2)
        exp = self.co_so(A1, tep=x1, che_do="L1")["basis_sha256"]
        kq, loi = {}, {}

        def lam(ten, fn):
            try:
                kq[ten] = fn()
            except DataError as exc:
                loi[ten] = exc.code
            except psycopg.Error as exc:
                loi[ten] = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0] or type(exc).__name__
        ts = [threading.Thread(target=lam, args=("review", lambda: self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1",
                                                                                      expected_basis=exp, khoa=self.K("cheo")))),
              threading.Thread(target=lam, args=("dot", lambda: svc2.tao_dot(A1, hop_dong_id=hd, so_dot=92, ngay_nghiem_thu=None, khoa=self.K("cheo"))))]
        for t in ts:
            t.start()
        for t in ts:
            t.join(1200)
        self.assertFalse(any(t.is_alive() for t in ts), "treo — nghi vòng khóa")
        self.assertEqual(len(kq), 1, (kq, loi))
        self.assertEqual(list(loi.values()), ["M4_IDEMPOTENCY_KHAC"])

    # ------------------------------------------------------------------ R07e FIX02 F4: rào CÓ KIỂM SOÁT quanh snapshot RR (không dựa vào timing)
    def test_r07e_giu_cho_qua_snapshot_rr(self):
        x1, hd = self.s["x1"], self.s["hd"]
        web2 = psycopg.connect(self.app_dsn, autocommit=True, row_factory=dict_row)
        chu2 = psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)
        self.ket_noi_phu.extend([web2, chu2])
        svc2 = self.XayDungK2(web2, self.goc / "m4-k2", conn_tin_cay=chu2)  # lệnh M17 thường trên cặp kết nối khác
        so_dot = lambda: self.q("SELECT count(*) FROM m4.dot WHERE hop_dong_id = %s", (hd,))  # noqa: E731
        exp = self.co_so(A1, tep=x1, che_do="L1")["basis_sha256"]
        # (a) Review giữ chỗ rồi mở RR; ĐÚNG lúc đang trong RR (lần chụp basis đầu), lệnh M17 cùng actor+khóa chạy tới commit → bị chặn chính xác,
        #     Review thắng duy nhất, công bố FINAL bình thường (không xung đột khóa biên nhận lúc công bố, không RUNNING mồ côi)
        goc = self.XayDungK2._co_so
        ket = {}

        def co_so_rao(svc, c, **kw):
            out = goc(svc, c, **kw)
            if "m17" not in ket:
                try:
                    ket["m17"] = svc2.tao_dot(A1, hop_dong_id=hd, so_dot=93, ngay_nghiem_thu=None, khoa=self.K("rr-a"))
                except DataError as exc:
                    ket["m17"] = exc.code
                except psycopg.Error as exc:
                    ket["m17"] = (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
            return out
        truoc = so_dot()
        with patch.object(self.XayDungK2, "_co_so", co_so_rao):
            r = self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("rr-a"))
        self.assertEqual(ket["m17"], "M4_IDEMPOTENCY_KHAC")
        self.assertEqual(so_dot(), truoc)  # lệnh M17 không có hiệu lực
        self.assertIn(r["trang_thai"], ("SUCCEEDED", "PARTIAL"), r)
        self.assertEqual(self.q("SELECT hanh_dong FROM m4.bien_nhan WHERE khoa = %s", (self.K("rr-a"),)), "REVIEW_CHAY")
        # (b) ngược thứ tự: lệnh M17 commit biên nhận TRƯỚC; Review cùng khóa bị chặn ở bước giữ chỗ — 0 run/giữ chỗ/kết quả/tệp
        svc2.tao_dot(A1, hop_dong_id=hd, so_dot=94, ngay_nghiem_thu=None, khoa=self.K("rr-b"))
        d0 = self.dem()
        with patch.object(self.XayDungK2, "_co_so", side_effect=AssertionError("không được chụp basis khi khóa đã thuộc lệnh khác")):
            self.assertEqual(self.loi(self.svc.review_chay, A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp,
                                      khoa=self.K("rr-b")), "M4_IDEMPOTENCY_KHAC")
        self.assertEqual(self.dem(), d0)
        # (c) cùng hành động + body: FINAL trả TRƯỚC mọi kiểm độ mới/tính toán (không chụp basis)
        with patch.object(self.XayDungK2, "_co_so", side_effect=AssertionError("replay không chụp basis")):
            lai = self.svc.review_chay(A1, du_an_id=self.du_an("DA_XD_A1"), tep_id=x1, mode="L1", expected_basis=exp, khoa=self.K("rr-a"))
        self.assertEqual((lai["run_id"], lai["lap_lai"]), (r["run_id"], True))

    # ------------------------------------------------------------------ R07d FIX01 R6: đích ghép theo đúng dòng hiệu lực của engine (PL đã ký/tương lai/thêm)
    def test_r07d_dich_ghep_hieu_luc_pl(self):
        from tests.test_m4_01b_pg import PHIEU_THAM_SO, VANG
        sv, du_an = self.svc, self.du_an("DA_XD_A1")
        hd = sv.tao_hop_dong(A1, du_an_id=du_an, so_hop_dong=f"HDXD-RVPL-{self.run_id}", ten="Gói thầu PL Review", khoa=self.K("pl-hd"))["hop_dong_id"]
        sv.gan_tep_hop_dong(A1, hop_dong_id=hd, revision=self.rev(hd), tep_id=self.tai(F.hop_dong_docx(), "HĐ PL.docx", F.MEDIA_DOCX, "HOP_DONG", "pl-tep-hd"),
                            khoa=self.K("pl-gan"))
        sv.trich(A1, hop_dong_id=hd, revision=self.rev(hd), khoa=self.K("pl-trich"))
        for ma, (tt, gia_tri, don_vi, dieu, trich) in PHIEU_THAM_SO.items():
            sv.sua_tham_so(A1, hop_dong_id=hd, revision=self.rev(hd), ma=ma, trang_thai_tham_so=tt, gia_tri=gia_tri, don_vi=don_vi, dieu_khoan=dieu,
                           trich_dan=trich, ly_do=None if tt == "CO_GIA_TRI" else "HĐ Điều 3.1 ghi: Tạm ứng: Không áp dụng", khoa=self.K("pl-sua-" + ma))
        for ma in VANG:
            sv.sua_tham_so(A1, hop_dong_id=hd, revision=self.rev(hd), ma=ma, trang_thai_tham_so="KHONG_QUY_DINH", ly_do="HĐ DEMO không có điều khoản này",
                           khoa=self.K("pl-sua-" + ma))
        sv.xac_nhan(A1, hop_dong_id=hd, revision=self.rev(hd), ly_do="Đã soát", khoa=self.K("pl-xn"))
        sv.khai_phu_luc(A1, hop_dong_id=hd, revision=self.rev(hd), khai="CO_CHUA_DU", khoa=self.K("pl-khai1"))
        tpl = self.tai(F.pdf_demo("PLRV"), "PL01.pdf", "application/pdf", "PHU_LUC", "pl-tep-pl")
        pl = sv.them_phu_luc(A1, hop_dong_id=hd, revision=self.rev(hd), so_pl="PL-01", ngay_ky="2026-02-01", ngay_hieu_luc="2026-02-01",
                             trang_thai_phu_luc="DA_KY", doi_boq=True, noi_dung="Thay HM-02, thêm HM-04", tep_id=tpl, khoa=self.K("pl-pl"))["phu_luc_id"]
        # FIX04: khóa TẢI tệp (TAI_TEP) phải khác khóa NHẬP BOQ (NHAP_BOQ) của cùng tệp — cùng khóa khác hành động là xung đột idempotency đúng
        goc = sv.boq_nhap(A1, hop_dong_id=hd, revision=self.rev(hd), tep_id=self.tai(F.boq_xlsx(F.BOQ_GOC), "BOQ goc.xlsx", F.MEDIA_XLSX, "BOQ",
                                                                                      "pl-tep-boq-goc"),
                          sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT), khoa=self.K("pl-boq-goc"))
        bpl = sv.boq_nhap(A1, hop_dong_id=hd, revision=self.rev(hd), tep_id=self.tai(F.boq_xlsx(F.BOQ_PHU_LUC), "BOQ PL.xlsx", F.MEDIA_XLSX, "BOQ",
                                                                                      "pl-tep-boq-pl"),
                          phu_luc_id=pl, sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT), khoa=self.K("pl-boq-pl"))
        self.assertNotEqual(self.K("pl-tep-boq-goc"), self.K("pl-boq-goc"))
        self.assertEqual((goc["trang_thai"], bpl["trang_thai"]), ("DA_MAP", "DA_MAP"), (goc, bpl))
        sv.khai_phu_luc(A1, hop_dong_id=hd, revision=self.rev(hd), khai="CO_DU", khoa=self.K("pl-khai2"))
        sau = sv.tao_dot(A1, hop_dong_id=hd, so_dot=2, ngay_nghiem_thu="2026-03-01", khoa=self.K("pl-dot-sau"))["dot_id"]    # PL đã hiệu lực
        truoc = sv.tao_dot(A1, hop_dong_id=hd, so_dot=1, ngay_nghiem_thu="2026-01-15", khoa=self.K("pl-dot-truoc"))["dot_id"]  # PL chưa hiệu lực
        dt = sv.danh_tinh(A1)

        def co(dot):
            with sv._tx_review(dt, rr=True) as c:
                return sv._co_so(c, du_an=du_an, tep=self.s["x1"], dot=dot, che_do="L1_L2", o_dich=None)
        c_sau, c_truoc = co(sau), co(truoc)
        # sau ngày hiệu lực: HM-02 do PL-01 THAY → đích là dòng PL, không phải dòng gốc; HM-04 PL thêm; HM-01 gốc
        self.assertEqual(str(self.XayDungK2._dich_hieu_luc(c_sau, "HM-02")["boq_id"]), str(bpl["boq_id"]))
        self.assertEqual(str(self.XayDungK2._dich_hieu_luc(c_sau, "HM-04")["boq_id"]), str(bpl["boq_id"]))
        self.assertEqual(str(self.XayDungK2._dich_hieu_luc(c_sau, "HM-01")["boq_id"]), str(goc["boq_id"]))
        # trước ngày hiệu lực: HM-02 là dòng gốc; HM-04 (chỉ ở PL tương lai) không phải đích hợp lệ
        self.assertEqual(str(self.XayDungK2._dich_hieu_luc(c_truoc, "HM-02")["boq_id"]), str(goc["boq_id"]))
        self.assertEqual(self.loi(self.XayDungK2._dich_hieu_luc, c_truoc, "HM-04"), "M4_REVIEW_DICH_KHONG_HIEU_LUC")
        self.assertEqual(self.loi(self.XayDungK2._dich_hieu_luc, c_sau, "HM-KHONG-CO"), "M4_REVIEW_DICH_KHONG_HIEU_LUC")

    # ------------------------------------------------------------------ R08 (cuối: thu hồi không đảo ngược)
    def test_r08_thu_hoi_giua_luc_tinh(self):
        x1, dot1 = self.s["x1"], self.s["dot1"]
        q = self.q("""SELECT q.id FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                      WHERE n.dang_nhap = %s AND q.du_an_id = %s AND q.vai = 'REVIEW' AND q.thu_hoi_luc IS NULL""", (REVIEW, self.du_an("DA_XD_A1")))
        exp = self.co_so(REVIEW, tep=x1, dot=dot1, che_do="L1_L2")["basis_sha256"]
        goc = self.XayDungK2._review_tinh

        def tinh_roi_thu_hoi(svc, *a, **k):
            out = goc(svc, *a, **k)
            self.admin.execute("SELECT m4.thu_hoi_quyen_du_an(%s, 'MO_PHONG_QUAN_TRI_TEST', 'Kiểm thu hồi M4-02A')", (q,))
            return out
        with patch.object(self.XayDungK2, "_review_tinh", tinh_roi_thu_hoi):
            self.assertEqual(self.loi(self.chay, REVIEW, tep=x1, dot=dot1, che_do="L1_L2", khoa="rv-thu-hoi", exp=exp), "M4_KHONG_CO_QUYEN_DU_AN")
        run = self.q("SELECT id FROM m4.review_run WHERE khoa = %s", (self.K("rv-thu-hoi"),))
        self.assertEqual(self.q("SELECT trang_thai FROM m4.review_run WHERE id = %s", (run,)), "CANCELLED")
        self.assertFalse(self.q("SELECT cong_bo FROM m4.review_result WHERE run_id = %s", (run,)))
        truoc = self.dem()
        # sau thu hồi: replay đúng body cũ / đọc / tải bị chặn theo quyền hiện hành; actor vẫn hoạt động
        self.assertEqual(self.loi(self.chay, REVIEW, tep=x1, dot=dot1, che_do="L1_L2", khoa="rv", exp=exp), "M4_KHONG_CO_QUYEN_DU_AN")
        self.assertEqual(self.loi(self.svc.review_chi_tiet, REVIEW, self.s["run_rv"]), "M4_REVIEW_KHONG_THAY")
        art = self.q("SELECT id FROM m4.review_artifact WHERE run_id = %s AND loai = 'RESULT'", (self.s["run_rv"],))
        self.assertEqual(self.loi(self.svc.review_tai, REVIEW, self.s["run_rv"], str(art)), "M4_REVIEW_KHONG_THAY")
        self.assertEqual(self.dem(), truoc)
        self.assertEqual(self.q("SELECT trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (REVIEW,)), "HOAT_DONG")
        # A1 (SOAN) vẫn đọc được lần chạy của reviewer trên dự án mình
        self.assertEqual(self.svc.review_chi_tiet(A1, self.s["run_rv"])["run"]["quyen"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
