"""M4-02B — kiểm PostgreSQL THẬT cho dịch vụ Chứng từ L3 (XayDungK2.chung_tu_*). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Chạy khi Root cấp KHO_PG_DSN_TEST qua env lúc chạy (không đọc .env/var, không hardcode credentials). DB MỚI `kho_test_m4ct_*` migrate mặc định (1–22,
M22 là candidate của gói này), seed CRM DEMO + M4 DEMO; login ứng dụng tạm (NOSUPERUSER NOBYPASSRLS IN ROLE app_web) + kết nối chủ bảng làm đường tin
cậy (inject như factory). Worker là tiến trình con thật (python -m kho_tri_thuc.m4.review_compute, nhánh che_do='L3') — cần lõi nguồn đã nạp + openpyxl
+ python-docx; thiếu → skip = NOT_RUN. Mỗi tài nguyên đăng ký cleanup NGAY sau khi tạo (đóng kết nối do test mở). Không DROP/DELETE/TRUNCATE DB/role,
không xóa thư mục — DB/role/thư mục/biên nhận lỗi giữ làm bằng chứng. Dữ liệu là chứng từ DEMO tổng hợp viết tay trong test.

K01 dựng hồ sơ: HĐ đủ (trích qua engine #6 dùng chung, tham số, xác nhận, khai PL) → BOQ gốc → đợt 1 (NT 2026-03-01) gắn hồ sơ thanh toán .xlsx + mục
    bắt buộc + BB nghiệm thu DOCX + BB giao nhận XLSX + CO dạng PDF → NỘP; đợt 2 nháp (NT 2026-04-01) gắn BB NT/GN khác bytes.
K02 L2 thật: Review L1+L2 công bố trên hồ sơ đợt 1 → L3 thấy L2 'CO' (dù đợt còn tệp chứng từ khác); SOAN chạy L3 (sau nộp — phân tích, không duyệt):
    căn cứ L2, so sánh typed theo toán hạng của CHÍNH dòng L2 đã công bố; artifact + REPORT_L3 đúng H/độ dài; replay 0 delta; khác body → IDEMPOTENCY_KHAC.
K03 sửa metadata → revision 1; replay; basis cũ → CO_SO_DOI; revision cũ → REVISION_CU; tệp ngoài bộ → TEP_KHONG_THUOC; Chạy lại → run con; cha nguyên.
K04 ghép tay: dòng BOQ sai → DICH_KHONG_HIEU_LUC (0 delta); đúng → map revision 1; replay; Chạy lại → DA_AP, auto giữ riêng.
K05 nhập lại BOQ (cùng mã HM-01/HM-02, boq_id mới): L2 → 'CU' (khác ['boq', …]); Chạy lại → CAN_CU INCOMPLETE + tham chiếu L2 cũ; map cũ →
    CAN_XAC_NHAN_LAI (không âm thầm áp theo ma_hm), dòng dùng auto; lịch sử map/kết quả cũ nguyên.
K06 phạm vi: reviewer trên đợt NHÁP → 404/PHAM_VI; XEM-only → đọc được, chạy/sửa PHAM_VI; cùng PN khác dự án (A2) và khác PN (B1) → KHONG_THAY; 0 delta.
K07 basis đổi trước chạy → CO_SO_DOI (giữ chỗ được giữ — retained slot, không deadlock: gửi lại đúng body sau khi tải lại vẫn chạy được bằng khóa mới);
    khóa đã dùng cho lệnh M17 khác → IDEMPOTENCY_KHAC trước hiệu lực.
K08 worker exit ≠ 0 → FAILED có bằng chứng; ket_qua.json có NaN/hình dạng sai (exit 0) → FAILED (không RUNNING, không PASS); thử lại đúng khóa → cùng FINAL.
K08b commit chưa rõ: công bố mất kết nối (giả lập) → M4_KET_QUA_CHUA_RO, run còn RUNNING mồ côi; gửi lại cùng khóa → ĐỐI SOÁT bằng chứng (không tính
    lại worker) → trạng thái cuối, không 'đang chạy' vĩnh viễn.
K09 basis đổi TRONG lúc tính → STALE, cong_bo=false, giữ artifact.
K10 hai kết nối đồng thời cùng khóa/body → MỘT run; join có hạn + assert không còn sống; đóng kết nối trong finally.
K11 REVIEW dương trên đợt DA_NOP (quyen=REVIEW); không sửa được đợt nháp.
K12 (cuối) thu hồi REVIEW giữa lúc tính → CANCELLED, không công bố; sau thu hồi: replay/đọc/tải bị chặn theo quyền hiện hành.

M4-L3 (GIAO-SUA-M4-L3-BACKEND6) — CODE_ONLY, NOT_RUN_CODE_ONLY:
GATE #6 (setUpClass, TRƯỚC K01 dương): MỘT Trich6Host sở hữu (DataRoot DEMO `<goc>/trich6-demo`, nguồn37 chỉ đọc NGUON_MAC_DINH), đăng ký stop NGAY trước
    start; readiness thật + implementation bắt tay; client chung `host.client(<goc>/m4-k2)` (đúng scope như factory HTTP m4.py) preflight typed common/v1
    RULE_ONLY + catalog XD đã ghim + cùng implementation; DOCX DEMO thật qua CÙNG endpoint: request/source/catalog/mode/implementation + seal khớp bytes.
    Không đạt → SkipTest "NOT_READY/NOT_VERIFIED" (không phải PASS); KHÔNG mock host, KHÔNG lõi trích cũ, KHÔNG nới guard service.
    MỌI service (`_svc_moi`: chính, reopen, 2 kết nối K10) nhận ĐÚNG client chung đó (cùng object/host/scope).
K08c/K08d S1 (PG thật, gọi _chung_tu_cong_bo THẬT; chỉ bọc biên giao dịch `_tx_review` của MỘT instance): công bố đầu lỗi SQL thường THẬT (SELECT 1/0)
    → đóng FAILED dự phòng mất kết nối TRƯỚC commit (rollback thật) / SAU commit thật → ngoài thấy M4_KET_QUA_CHUA_RO; cùng body/khóa đối soát đúng run
    cũ, 0 worker/compute lại, 0 run/biên nhận trùng, bằng chứng/thư mục nguyên; thử lại sau FINAL → cùng FINAL.
M4CongBoS1Bien (KHÔNG cần PG — nhãn MOCK_BOUNDARY, KHÔNG phải bằng chứng PostgreSQL): kết nối giả chỉ ở biên giao dịch/commit, publish thật.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import subprocess
import tempfile
import threading
import unittest
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nguon_review as NR
from kho_tri_thuc.nguon import trich6_host as H
from kho_tri_thuc.nguon import trich_chung_6 as T6
from tests.test_m4_02b_pure import _docx, _docx_bytes, _hang, _xlsx_bytes, openpyxl

ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
A1, A2, B1, REVIEW, XEM = "MO_PHONG_DU_AN_A1", "MO_PHONG_DU_AN_A2", "MO_PHONG_DU_AN_B1", "MO_PHONG_REVIEW_M4", "MO_PHONG_XEM_M4"
BANG = ("chung_tu_run", "chung_tu_result", "chung_tu_artifact", "chung_tu_revision", "chung_tu_manual_map", "chung_tu_giu_khoa", "bien_nhan", "nhat_ky")
NT_DAU = ["BIÊN BẢN NGHIỆM THU KHỐI LƯỢNG", "Số: 01/BBNT-2026", "Hà Nội, ngày 01 tháng 03 năm 2026", "Căn cứ Hợp đồng số 123/2025"]
NT_BANG = [["STT", "Tên công việc", "ĐVT", "Khối lượng kỳ này"], ["1", "Đào đất hố móng", "m3", "40"], ["2", "Bê tông móng", "m3", "5"]]
GN = {(1, 1): "BIÊN BẢN GIAO NHẬN VẬT TƯ — Hợp đồng số 123/2025", (2, 1): "Số: 05/BBGN-2026", (3, 1): "Ngày 25/02/2026",
      **_hang(5, [["STT", "Tên vật tư", "Model", "ĐVT", "Số lượng", "Số lô"], [1, "Xi măng PC40 bao đặc chủng", "PC40", "m3", 10, "LOT-X"],
                  None, [2, "Bê tông móng", None, "m3", 5, "LOT-B"]])}


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PG M4-02B không chạy (NOT_RUN, không tính đạt)")
class M4ChungTuPG(unittest.TestCase):
    """Chạy theo thứ tự tên k01…k12 trên MỘT DB; trạng thái qua cls.s."""

    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.ha_tang import postgres as pg
        from kho_tri_thuc.k2 import crm_demo, m4_demo
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        cls.goc = Path(tempfile.mkdtemp(prefix="ktt_m4ct_pg_"))  # DataRoot DEMO của lượt — giữ lại
        cls.run_id = uuid.uuid4().hex[:8]
        cls.s = {}
        # GATE #6 TRƯỚC mọi tài nguyên PG/positive K01: không đạt → NOT_READY/NOT_VERIFIED (SkipTest, cleanup host vẫn chạy), không đi vòng
        cls.trich6, cls.gate = cls._gate_trich6()
        cls.db = "kho_test_m4ct_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        cls.addClassCleanup(cls.admin.close)  # đăng ký NGAY: raise ở bước sau vẫn đóng kết nối do test mở (không DROP DB)
        cls.version = pg.migrate(cls.admin)
        crm_demo.khoi_tao(cls.admin)
        cls.seed = m4_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m4ct_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        cls.XayDungK2 = XayDungK2
        cls.svc = cls._svc_moi()

    @classmethod
    def _gate_trich6(cls):
        """Gate THẬT engine #6 dùng chung (mẫu vòng đời tests/test_trich6_host.py:525–566 — mẫu seam, không phải bằng chứng K2 đã chạy).
        MỘT host sở hữu + MỘT client chung gắn scope DataRoot DEMO của service M4 (`<goc>/m4-k2`, như app.trich6_client(svc.root)).
        Trả (client, bằng chứng gate KHÔNG bí mật). Không đạt → unittest.SkipTest('NOT_READY…'/'NOT_VERIFIED…')."""
        host = H.Trich6Host(cls.goc / "trich6-demo", H.NGUON_MAC_DINH)
        cls.addClassCleanup(host.stop)  # đăng ký dừng (có xác nhận) NGAY trước start: start lỗi giữa chừng vẫn dọn đúng instance
        cls.trich6_host = host
        try:
            host.start()
        except H.LoiHost as exc:
            raise unittest.SkipTest(f"NOT_READY: host #6 không khởi động ({exc.ma}) — K2 dương không chạy (không mock/không lõi cũ)") from None
        sk = host.suc_khoe()
        impl = sk.get("implementation_sha256")
        if sk.get("san_sang") is not True or not (isinstance(impl, str) and H.RE_HEX64.fullmatch(impl)):
            raise unittest.SkipTest(f"NOT_READY: readiness #6 không đạt ({sk.get('ly_do')})")
        client = host.client(cls.goc / "m4-k2")
        if not client.san_sang:
            raise unittest.SkipTest("NOT_READY: client chung #6 chưa sẵn sàng")
        try:
            nl = client.nang_luc("XD")  # typed common/v1 + RULE_ONLY + catalog XD đã ghim (T6.CATALOG) + sẵn sàng — chỉ đọc, trước mọi POST
        except DataError as exc:
            raise unittest.SkipTest(f"NOT_READY: preflight capability #6 không đạt ({exc.code})") from None
        lech = []
        if nl.get("implementation_sha256") != impl:
            lech.append("implementation preflight ≠ bắt tay")
        if T6.MODE not in nl.get("modes", []) or T6.MODE != "RULE_ONLY":
            lech.append("mode RULE_ONLY")
        # DOCX DEMO thật qua CÙNG endpoint/client (request_id riêng của gate, không trùng ý định 'm4:…' của K01)
        docx = F.hop_dong_docx()
        rid = f"m4ct-gate-{cls.run_id}"
        try:
            r = client.trich(docx, ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id=rid)
        except DataError as exc:
            raise unittest.SkipTest(f"NOT_VERIFIED: DOCX DEMO qua endpoint #6 không xong ({exc.code})") from None
        cm, yc = r["common"], r["yeu_cau"]
        cat = T6.CATALOG["XD"]
        if (cm.get("request_id"), yc.get("request_id")) != (rid, rid):
            lech.append("request_id")
        if cm.get("source_sha256") != hashlib.sha256(docx).hexdigest():
            lech.append("source_sha256")
        if (cm.get("catalog_id"), cm.get("catalog_sha256")) != (cat["catalog_id"], cat["catalog_sha256"]):
            lech.append("catalog XD")
        if (cm.get("mode"), yc.get("mode"), r["ket_qua"].get("che_do")) != ("RULE_ONLY",) * 3:
            lech.append("mode kết quả")
        if (cm.get("implementation") or {}).get("sha256") != impl:
            lech.append("implementation kết quả")
        try:
            seal = (client.doc(r["luot"]).get("common") or {}).get("seal") or {}
        except DataError as exc:
            seal = {"loi": exc.code}
        if (seal.get("sha256"), seal.get("byte_length")) != (r["raw_sha256"], len(r["raw_ket_qua"])) \
                or hashlib.sha256(r["raw_ket_qua"]).hexdigest() != r["raw_sha256"]:
            lech.append("seal")
        if lech:
            raise unittest.SkipTest("NOT_VERIFIED: gate #6 lệch " + ", ".join(lech) + " — dừng K2 dương")
        return client, {"trang_thai": "READY", "instance": sk.get("instance"), "implementation_sha256": impl, "luot_gate": r["luot"]}

    @classmethod
    def _svc_moi(cls):
        """Factory DUY NHẤT của test cho service chính/reopen/đồng thời: mỗi lần kết nối riêng, CÙNG client #6 chung của gate (không clone/không None)."""
        web = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(web.close)
        chu = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row)
        cls.addClassCleanup(chu.close)
        return cls.XayDungK2(web, cls.goc / "m4-k2", conn_tin_cay=chu, trich6=cls.trich6)

    def so_luot_host(self) -> int:
        d = self.goc / "trich6-demo" / "du_lieu" / "ket_qua"  # thư mục lượt của host sở hữu (như test_trich6_host)
        return len([p for p in d.iterdir() if p.is_dir() and H.RE_LUOT.fullmatch(p.name)]) if d.is_dir() else 0

    def so_y_dinh(self) -> int:
        d = self.goc / "m4-k2" / "trich6-y-dinh"
        return len([p for p in d.iterdir() if p.is_dir()]) if d.is_dir() else 0

    def setUp(self):
        if not (_nguon_da_nap() and openpyxl is not None and _docx is not None):
            self.skipTest("Lõi nguồn Review chưa nạp hoặc thiếu openpyxl/python-docx — NOT_RUN")
        if self._testMethodName != "test_k01_dung_ho_so" and "dot1" not in self.s:
            self.skipTest("K01 chưa dựng được hồ sơ — NOT_RUN")

    # ------------------------------------------------------------------ helpers
    def K(self, ten):
        return f"m4ct-{self.run_id}-{ten}"

    def q(self, sql, params=()):
        return self.admin.execute(sql, params).fetchone()[0]

    def du_an(self, ma="DA_XD_A1"):
        return str(self.q("SELECT id FROM master.du_an WHERE ma_junsky = %s", (ma,)))

    def rev(self):
        return self.q("SELECT revision FROM m4.ho_so_hop_dong WHERE hop_dong_id = %s", (self.s["hd"],))

    def rev_dot(self, dot):
        return self.q("SELECT revision FROM m4.dot WHERE id = %s", (dot,))

    def dem(self) -> dict:
        tm = self.goc / "m4-k2" / "m4-chung-tu-run"
        return {t: self.q(f"SELECT count(*) FROM m4.{t}") for t in BANG} | {"thu_muc_chay": len(list(tm.iterdir())) if tm.is_dir() else 0}

    def khong_nhat_ky(self, d):
        return {k: v for k, v in d.items() if k != "nhat_ky"}

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
        return self.svc.tai_tep(A1, raw, du_an_id=self.du_an(), vai_tro=vai, ten=ten, media_type=media, khoa=self.K(khoa))["tep_id"]

    def gan(self, dot, tep, muc, khoa):
        self.svc.gan_tep_dot(A1, dot_id=dot, revision=self.rev_dot(dot), tep_id=tep, muc=muc, khoa=self.K(khoa))

    def ds(self, dot, login=A1):
        return self.svc.chung_tu_ds(login, dot_id=dot)

    def chay(self, dot, khoa, *, login=A1, svc=None, exp=None, rev=None):
        d = self.ds(dot, login)
        return (svc or self.svc).chung_tu_chay(login, dot_id=dot, revision=d["co_so"]["revision"] if rev is None else rev,
                                               expected_basis=exp or d["co_so"]["basis_sha256"], khoa=self.K(khoa))

    def chay_lai(self, run, khoa, dot, login=A1):
        cs = self.ds(dot, login)["co_so"]
        return self.svc.chung_tu_chay_lai(login, run_id=run, revision=cs["revision"], expected_basis=cs["basis_sha256"], khoa=self.K(khoa))

    def ket_qua(self, run_id, login=A1):
        return self.svc.chung_tu_chi_tiet(login, run_id)

    # ------------------------------------------------------------------ K01
    def test_k01_dung_ho_so(self):
        from tests.test_m4_01b_pg import PHIEU_THAM_SO, VANG  # oracle thủ công từ DOCX nguồn + danh mục (không lấy từ parser)
        from tests.test_m4_review_k2 import ho_so_xlsx
        self.assertEqual(self.version, 22)
        self.assertEqual([r[0] for r in self.admin.execute("SELECT version FROM master.schema_migrations ORDER BY version")], list(range(1, 23)))
        sv = self.svc
        hd = sv.tao_hop_dong(A1, du_an_id=self.du_an(), so_hop_dong=f"123/2025-{self.run_id}", ten="Gói thầu chứng từ DEMO", khoa=self.K("hd"))["hop_dong_id"]
        self.s["hd"] = hd
        tep_hd = self.tai(F.hop_dong_docx(), "Hợp đồng DEMO.docx", F.MEDIA_DOCX, "HOP_DONG", "tep-hd")
        sv.gan_tep_hop_dong(A1, hop_dong_id=hd, revision=self.rev(), tep_id=tep_hd, khoa=self.K("gan-hd"))
        # trích THẬT qua engine #6 dùng chung đã qua gate (không fake XONG): đúng client chung, đúng host, thêm đúng MỘT ý định + MỘT lượt
        self.assertEqual(self.gate["trang_thai"], "READY")
        self.assertIs(sv.trich6, self.trich6)
        self.assertTrue(self.trich6_host.suc_khoe()["san_sang"])
        luot0, yd0 = self.so_luot_host(), self.so_y_dinh()
        self.assertEqual(sv.trich(A1, hop_dong_id=hd, revision=self.rev(), khoa=self.K("trich"))["trang_thai"], "XONG")
        self.assertEqual((self.so_luot_host() - luot0, self.so_y_dinh() - yd0), (1, 1))
        self.assertEqual(self.trich6_host.suc_khoe()["implementation_sha256"], self.gate["implementation_sha256"])  # cùng implementation đã gate
        for ma, (tt, gia_tri, don_vi, dieu, trich) in PHIEU_THAM_SO.items():
            sv.sua_tham_so(A1, hop_dong_id=hd, revision=self.rev(), ma=ma, trang_thai_tham_so=tt, gia_tri=gia_tri, don_vi=don_vi, dieu_khoan=dieu,
                           trich_dan=trich, ly_do=None if tt == "CO_GIA_TRI" else "HĐ Điều 3.1 ghi: Tạm ứng: Không áp dụng", khoa=self.K("sua-" + ma))
        for ma in VANG:
            sv.sua_tham_so(A1, hop_dong_id=hd, revision=self.rev(), ma=ma, trang_thai_tham_so="KHONG_QUY_DINH", ly_do="HĐ DEMO không có điều khoản này",
                           khoa=self.K("sua-" + ma))
        sv.xac_nhan(A1, hop_dong_id=hd, revision=self.rev(), ly_do="Phòng dự án đã soát", khoa=self.K("xn"))
        sv.khai_phu_luc(A1, hop_dong_id=hd, revision=self.rev(), khai="KHONG_CO", khoa=self.K("khai"))
        tep_boq = self.tai(F.boq_xlsx(F.BOQ_GOC), "BOQ.xlsx", F.MEDIA_XLSX, "BOQ", "boq")
        boq = sv.boq_nhap(A1, hop_dong_id=hd, revision=self.rev(), tep_id=tep_boq, sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT), khoa=self.K("boq-nhap"))
        self.assertEqual(boq["trang_thai"], "DA_MAP", boq)
        self.s.update(tep_boq=tep_boq, boq=boq["boq_id"])
        # đợt 1: hồ sơ thanh toán .xlsx + mục bắt buộc (PDF) + bộ chứng từ L3 → NỘP
        dot1 = sv.tao_dot(A1, hop_dong_id=hd, so_dot=1, ngay_nghiem_thu="2026-03-01", khoa=self.K("dot1"))["dot_id"]
        x1 = self.tai(ho_so_xlsx("KY1"), "ho_so_ky1.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "x1")
        bb = [r[0] for r in self.admin.execute("SELECT ma FROM m4.danh_muc_ho_so_dot WHERE bat_buoc_dot_dau ORDER BY ma").fetchall()]
        muc = [r[0] for r in self.admin.execute("SELECT ma FROM m4.danh_muc_ho_so_dot ORDER BY ma").fetchall()]
        self.gan(dot1, x1, bb[0], "gan-x1")
        for i, m in enumerate(bb):
            self.gan(dot1, self.tai(F.pdf_demo(f"CT{i}"), f"hs-{i}.pdf", "application/pdf", "HO_SO_DOT", f"hs-{i}"), m, f"gan-hs-{i}")
        nt = self.tai(_docx_bytes(NT_DAU, NT_BANG), "bb_nghiem_thu.docx", F.MEDIA_DOCX, "HO_SO_DOT", "nt")
        gn = self.tai(_xlsx_bytes([("GiaoNhan", GN)]), "bb_giao_nhan.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "gn")
        co = self.tai(F.pdf_demo("CO_SCAN"), "co_scan.pdf", "application/pdf", "HO_SO_DOT", "co")
        for i, t in enumerate((nt, gn, co)):
            self.gan(dot1, t, muc[i], f"gan-ct-{i}")
        self.assertEqual(sv.chi_tiet_dot(A1, dot1)["thieu"], [])
        sv.nop(A1, dot_id=dot1, revision_ho_so=self.rev(), revision_dot=self.rev_dot(dot1), khoa=self.K("nop1"))
        self.assertEqual(self.q("SELECT trang_thai FROM m4.dot WHERE id = %s", (dot1,)), "DA_NOP")
        # đợt 2 nháp: bộ chứng từ khác bytes (số BB khác)
        dot2 = sv.tao_dot(A1, hop_dong_id=hd, so_dot=2, ngay_nghiem_thu="2026-04-01", khoa=self.K("dot2"))["dot_id"]
        nt2 = self.tai(_docx_bytes([NT_DAU[0], "Số: 02/BBNT-2026", "Hà Nội, ngày 01 tháng 04 năm 2026", NT_DAU[3]], NT_BANG), "bb_nt_ky2.docx",
                       F.MEDIA_DOCX, "HO_SO_DOT", "nt2")
        gn2 = self.tai(_xlsx_bytes([("GiaoNhan", {**GN, (2, 1): "Số: 06/BBGN-2026"})]), "bb_gn_ky2.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "gn2")
        for i, t in enumerate((nt2, gn2)):
            self.gan(dot2, t, muc[i], f"gan2-{i}")
        self.s.update(dot1=dot1, dot2=dot2, x1=x1, nt=nt, gn=gn, co=co, nt2=nt2, gn2=gn2, muc=muc)

    # ------------------------------------------------------------------ K02
    def test_k02_l2_that_va_soan_chay(self):
        dot1, x1 = self.s["dot1"], self.s["x1"]
        rv = self.svc.review_ds(A1, dot_id=dot1, tep_id=x1, che_do="L1_L2")["co_so"]
        l2run = self.svc.review_chay(A1, du_an_id=self.du_an(), tep_id=x1, mode="L1_L2", dot_id=dot1, o_dich=None, expected_basis=rv["basis_sha256"],
                                     khoa=self.K("l2"))
        self.assertIn(l2run["trang_thai"], ("SUCCEEDED", "PARTIAL"), l2run)
        l2_dong = self.q("SELECT ket_qua->'lop2'->'doi_chieu_hm' FROM m4.review_result WHERE run_id = %s", (l2run["run_id"],))
        self.assertTrue(isinstance(l2_dong, list) and l2_dong, "L2 công bố không có bảng hạng mục — ca L2 không kiểm được")
        d = self.ds(dot1)
        cs = d["co_so"]
        self.assertEqual((cs["quyen"], cs["revision"], cs["phu_thuoc"]["L2"]["ok"]), ("SOAN", 0, True))  # L2 khớp căn cứ dù đợt có thêm chứng từ
        self.assertEqual({t["tep_id"]: t["doc"] for t in d["tai_lieu"] if t["tep_id"] in (self.s["nt"], self.s["gn"], self.s["co"])},
                         {self.s["nt"]: "NATIVE", self.s["gn"]: "NATIVE", self.s["co"]: "PROVIDER"})
        r = self.chay(dot1, "chay-1", exp=cs["basis_sha256"])
        self.assertFalse(r["lap_lai"])
        self.assertEqual(r["trang_thai"], "PARTIAL", r)  # CO PDF chưa đọc được → không đủ phạm vi
        ct = self.ket_qua(r["run_id"])
        kq = ct["ket_qua"]["ket_qua"]
        self.assertTrue(ct["ket_qua"]["cong_bo"])
        self.assertEqual(ct["run"]["quyen"], "SOAN")
        self.assertEqual((kq["basis_sha256"], kq["provenance"]["nguon_hang_muc"], kq["provenance"]["l2"]["run_id"]),
                         (cs["basis_sha256"], "L2", l2run["run_id"]))
        self.assertEqual(kq["coverage"]["CAN_CU"]["trang_thai"], "CHECKED")
        # so sánh typed dùng ĐÚNG toán hạng của dòng L2 đã công bố (đọc từ review_result, không từ output L3)
        h1 = next(h for h in l2_dong if h.get("ma_hm") == "HM-01")
        ss1 = kq["so_sanh"]["HM-01"]["C01"]
        if isinstance(h1.get("kl_kn"), (int, float)) and h1["kl_kn"] > 0:
            self.assertEqual((ss1["trang_thai"], ss1["kl_kn"], ss1["nt"]), ("SO_DUOC", h1["kl_kn"], 40.0))
        else:
            self.assertNotEqual(ss1["trang_thai"], "SO_DUOC")
        doc = {x["tep_id"]: x for x in kq["tai_lieu"]}
        self.assertEqual((doc[self.s["nt"]]["loai"], doc[self.s["nt"]]["trang_thai_doc"], doc[self.s["nt"]]["trang_thai_dong"]), ("BB_NT", "CHECKED", "CHECKED"))
        self.assertEqual(doc[self.s["co"]]["trang_thai_doc"], "NOT_CONFIGURED")
        self.assertEqual([x["vi_tri_vat_ly"]["dong"] for x in doc[self.s["gn"]]["dong"]], [6, 8])  # dòng 7 trống: vị trí vật lý thật
        loai = {a["loai"]: a for a in ct["artifact"]}
        self.assertEqual(set(loai), {"BASIS", "INPUT", "LOG", "RESULT", "REPORT_L3"})
        ten, media, raw = self.svc.chung_tu_tai(A1, r["run_id"], loai["REPORT_L3"]["id"])
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw), media), (loai["REPORT_L3"]["raw_sha256"], loai["REPORT_L3"]["byte_length"], NR.MEDIA_XLSX))
        vao = (self.goc / "m4-k2" / "m4-chung-tu-run" / r["run_id"] / "vao.json").read_text(encoding="utf-8")
        self.assertNotIn(self.dsn.split("@", 1)[-1], vao)  # đầu vào worker không có DSN
        truoc = self.dem()
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("replay không được tính lại")):
            lai = self.chay(dot1, "chay-1", exp=cs["basis_sha256"])
        self.assertEqual((lai["lap_lai"], lai["run_id"]), (True, r["run_id"]))
        self.assertEqual(self.dem(), truoc)
        self.assertEqual(self.loi(self.svc.chung_tu_chay, A1, dot_id=dot1, revision=0, expected_basis="b" * 64, khoa=self.K("chay-1")), "M4_IDEMPOTENCY_KHAC")
        self.s.update(run1=r["run_id"], kq1_sha=ct["ket_qua"]["ket_qua_sha256"], l2run=l2run["run_id"])

    # ------------------------------------------------------------------ K03
    def test_k03_sua_metadata_revision_va_chay_lai(self):
        run1, dot1 = self.s["run1"], self.s["dot1"]
        cs = self.ds(dot1)["co_so"]
        body = dict(run_id=run1, revision=0, tai_lieu=[{"tep_id": self.s["nt"], "ngay": "2026-03-05"}], expected_basis=cs["basis_sha256"],
                    ly_do="BB nghiệm thu ký ngày 05/03 theo bản gốc")
        r = self.svc.chung_tu_sua(A1, **body, khoa=self.K("sua-1"))
        self.assertEqual((r["revision"], r["lap_lai"]), (1, False))
        self.assertTrue(self.svc.chung_tu_sua(A1, **body, khoa=self.K("sua-1"))["lap_lai"])  # replay
        self.assertEqual(self.loi(self.svc.chung_tu_sua, A1, **{**body, "ly_do": "khác"}, khoa=self.K("sua-2")), "M4_CHUNG_TU_CO_SO_DOI")
        cs2 = self.ds(dot1)["co_so"]
        self.assertEqual(cs2["revision"], 1)
        self.assertEqual(self.loi(self.svc.chung_tu_sua, A1, **{**body, "expected_basis": cs2["basis_sha256"]}, khoa=self.K("sua-3")), "M4_REVISION_CU")
        self.assertEqual(self.loi(self.svc.chung_tu_sua, A1, **{**body, "revision": 1, "expected_basis": cs2["basis_sha256"],
                                                                  "tai_lieu": [{"tep_id": str(uuid.uuid4()), "so": "x"}]}, khoa=self.K("sua-4")),
                         "M4_CHUNG_TU_TEP_KHONG_THUOC")
        self.assertEqual(self.loi(self.svc.chung_tu_sua, A1, **{**body, "revision": 1, "expected_basis": cs2["basis_sha256"],
                                                                  "tai_lieu": [{"tep_id": self.s["nt"], "raw_sha256": "a" * 64}]}, khoa=self.K("sua-5")),
                         "M4_CLIENT_AUTHORITY")
        con = self.chay_lai(run1, "lai-1", dot1)
        ct = self.ket_qua(con["run_id"])
        self.assertEqual(ct["run"]["parent_run_id"], run1)
        kq = ct["ket_qua"]["ket_qua"]
        nt = next(x for x in kq["tai_lieu"] if x["tep_id"] == self.s["nt"])
        self.assertEqual((nt["ngay"], nt["trich"]["ngay"]), ("2026-03-05", "2026-03-01"))
        self.assertTrue(any(f["code"] == "C02" for f in kq["phat_hien"]))
        self.assertEqual(self.ket_qua(run1)["ket_qua"]["ket_qua_sha256"], self.s["kq1_sha"])  # kết quả cha nguyên
        self.s.update(run2=con["run_id"])

    # ------------------------------------------------------------------ K04
    def test_k04_ghep_tay_dich_hieu_luc_chay_lai(self):
        run2, dot1 = self.s["run2"], self.s["dot1"]
        cs = self.ds(dot1)["co_so"]
        kq = self.ket_qua(run2)["ket_qua"]["ket_qua"]
        dong = next(x for d in kq["tai_lieu"] for x in d["dong"] if x["ten"].startswith("Xi măng"))
        self.assertIsNone(dong["khoa"])  # máy không ghép được
        bd = self.admin.execute("SELECT boq_id, dong FROM m4.boq_dong WHERE boq_id = %s AND ma_hm = 'HM-02'", (self.s["boq"],)).fetchone()
        truoc = self.dem()
        self.assertEqual(self.loi(self.svc.chung_tu_ghep, A1, run_id=run2, row_id=dong["row_id"], boq_id=str(bd[0]), boq_dong=bd[1] + 1, ma_hm="HM-02",
                                  revision=1, expected_basis=cs["basis_sha256"], ly_do="x", khoa=self.K("ghep-sai")), "M4_REVIEW_DICH_KHONG_HIEU_LUC")
        self.assertEqual(self.khong_nhat_ky(self.dem()), self.khong_nhat_ky(truoc))
        body = dict(run_id=run2, row_id=dong["row_id"], boq_id=str(bd[0]), boq_dong=bd[1], ma_hm="HM-02", revision=1, expected_basis=cs["basis_sha256"],
                    ly_do="Xi măng cho bê tông móng (nhà thầu ghi tên vật tư)")
        g = self.svc.chung_tu_ghep(A1, **body, khoa=self.K("ghep-1"))
        self.assertEqual((g["revision"], g["ma_hm"], g["lap_lai"]), (1, "HM-02", False))
        self.assertTrue(self.svc.chung_tu_ghep(A1, **body, khoa=self.K("ghep-1"))["lap_lai"])
        con = self.chay_lai(run2, "lai-2", dot1)
        kq3 = self.ket_qua(con["run_id"])["ket_qua"]["ket_qua"]
        ln = next(x for d in kq3["tai_lieu"] for x in d["dong"] if x["row_id"] == dong["row_id"])
        self.assertEqual((ln["khoa"], ln["ghep_tay"]), ("HM-02", True))
        self.assertEqual([x["trang_thai"] for x in kq3["provenance"]["ghep_tay"] if x["row_id"] == dong["row_id"]], ["DA_AP"])
        auto = {x["row_id"]: x["khoa"] for d in kq3["provenance"]["auto"]["tai_lieu"] for x in d["dong"]}
        self.assertIsNone(auto[dong["row_id"]])
        self.s.update(run3=con["run_id"], row_xi_mang=dong["row_id"])

    # ------------------------------------------------------------------ K05
    def test_k05_l2_cu_va_dich_ghep_tay_cu_sau_nhap_lai_boq(self):
        dot1 = self.s["dot1"]
        maps_truoc = self.q("SELECT count(*) FROM m4.chung_tu_manual_map")
        kq3_sha = self.ket_qua(self.s["run3"])["ket_qua"]["ket_qua_sha256"]
        b2 = self.svc.boq_nhap(A1, hop_dong_id=self.s["hd"], revision=self.rev(), tep_id=self.s["tep_boq"], sheet="BOQ", hang_tieu_de=1, cot=dict(F.BOQ_COT),
                               khoa=self.K("boq-nhap-lai"))
        self.assertEqual(b2["trang_thai"], "DA_MAP", b2)
        self.assertNotEqual(str(b2["boq_id"]), str(self.s["boq"]))  # cùng mã HM, BOQ hiện hành mới
        d = self.ds(dot1)
        self.assertFalse(d["co_so"]["phu_thuoc"]["L2"]["ok"])
        self.assertIn("boq", d["co_so"]["phu_thuoc"]["L2"]["ly_do"])
        con = self.chay_lai(self.s["run3"], "lai-3", dot1)
        kq = self.ket_qua(con["run_id"])["ket_qua"]["ket_qua"]
        self.assertEqual(kq["coverage"]["CAN_CU"]["trang_thai"], "INCOMPLETE")
        self.assertEqual(kq["provenance"]["l2_cu"]["run_id"], self.s["l2run"])
        self.assertIn("boq", kq["provenance"]["l2_cu"]["khac"])
        self.assertTrue(all(h["kl_kn"] is None for h in kq["hang_muc"]))  # không dùng lượng L2 cũ
        rid = self.s["row_xi_mang"]
        nk = [x for x in kq["provenance"]["ghep_tay"] if x["row_id"] == rid]
        self.assertEqual([x["trang_thai"] for x in nk], ["CAN_XAC_NHAN_LAI"])  # cùng ma_hm HM-02 nhưng đích lưu là BOQ cũ
        self.assertEqual((nk[0]["dich_luu"]["boq_id"], nk[0]["dich_hien_hanh"]["boq_id"]), (str(self.s["boq"]), str(b2["boq_id"])))
        ln = next(x for t in kq["tai_lieu"] for x in t["dong"] if x["row_id"] == rid)
        self.assertEqual((ln["khoa"], ln["ghep_tay"]), (None, False))
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_manual_map"), maps_truoc)  # lịch sử map không xóa/ghi đè
        self.assertEqual(self.ket_qua(self.s["run3"])["ket_qua"]["ket_qua_sha256"], kq3_sha)  # kết quả cũ nguyên
        self.s["boq2"] = str(b2["boq_id"])

    # ------------------------------------------------------------------ K06
    def test_k06_pham_vi(self):
        dot1, dot2 = self.s["dot1"], self.s["dot2"]
        r2 = self.chay(dot2, "dot2-soan")  # run trên đợt nháp để kiểm đọc
        self.s["run_dot2"] = r2["run_id"]
        truoc = self.dem()
        self.assertEqual(self.loi(self.svc.chung_tu_ds, REVIEW, dot_id=dot2), "M4_CHUNG_TU_KHONG_THAY")  # đợt nháp: reviewer không thấy
        self.assertEqual(self.loi(self.svc.chung_tu_chay, REVIEW, dot_id=dot2, revision=0, expected_basis="c" * 64, khoa=self.K("rv-chay")),
                         "M4_CHUNG_TU_PHAM_VI")
        self.assertEqual(self.loi(self.svc.chung_tu_chi_tiet, REVIEW, r2["run_id"]), "M4_CHUNG_TU_KHONG_THAY")
        x = self.ds(dot1, XEM)  # XEM-only: đọc được, không có basis/nút chạy, mọi lệnh PHAM_VI
        self.assertEqual((x["co_so"]["san_sang"], x["co_so"]["quyen"]), (False, None))
        self.assertEqual(self.loi(self.svc.chung_tu_chay, XEM, dot_id=dot1, revision=1, expected_basis="c" * 64, khoa=self.K("xem-chay")), "M4_CHUNG_TU_PHAM_VI")
        self.assertEqual(self.loi(self.svc.chung_tu_sua, XEM, run_id=self.s["run1"], revision=1, tai_lieu=[{"tep_id": self.s["nt"], "so": "x"}],
                                  expected_basis="c" * 64, ly_do="x", khoa=self.K("xem-sua")), "M4_CHUNG_TU_PHAM_VI")
        for login in (A2, B1):  # cùng PN khác dự án / khác PN: không lộ tồn tại
            self.assertEqual(self.loi(self.svc.chung_tu_ds, login, dot_id=dot1), "M4_CHUNG_TU_KHONG_THAY", login)
            self.assertEqual(self.loi(self.svc.chung_tu_chay, login, dot_id=dot1, revision=1, expected_basis="c" * 64, khoa=self.K("ngoai-" + login)),
                             "M4_CHUNG_TU_KHONG_THAY", login)
            self.assertEqual(self.loi(self.svc.chung_tu_chi_tiet, login, self.s["run1"]), "M4_CHUNG_TU_KHONG_THAY", login)
        self.assertEqual(self.khong_nhat_ky(self.dem()), self.khong_nhat_ky(truoc))

    # ------------------------------------------------------------------ K07
    def test_k07_basis_doi_va_khoa_cua_lenh_khac(self):
        dot2 = self.s["dot2"]
        cs = self.ds(dot2)["co_so"]
        them = self.tai(_xlsx_bytes([("CQ", {(1, 1): "CERTIFICATE OF QUALITY", (2, 1): "No.: CQ-77/2026"})]), "cq.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "cq")
        self.gan(dot2, them, self.s["muc"][3], "gan-cq")
        truoc = self.dem()
        self.assertEqual(self.loi(self.svc.chung_tu_chay, A1, dot_id=dot2, revision=0, expected_basis=cs["basis_sha256"], khoa=self.K("cu")),
                         "M4_CHUNG_TU_CO_SO_DOI")
        sau = self.dem()
        self.assertEqual((sau["chung_tu_run"], sau["thu_muc_chay"]), (truoc["chung_tu_run"], truoc["thu_muc_chay"]))
        # chỗ giữ của khóa 'cu' được GIỮ (retained slot, không xóa): gửi lại đúng body cũ vẫn chỉ CO_SO_DOI; ý định mới (basis mới) dùng khóa mới chạy được
        self.assertEqual(self.loi(self.svc.chung_tu_chay, A1, dot_id=dot2, revision=0, expected_basis=cs["basis_sha256"], khoa=self.K("cu")),
                         "M4_CHUNG_TU_CO_SO_DOI")
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_giu_khoa WHERE khoa = %s", (self.K("cu"),)), 1)
        self.assertIn(self.chay(dot2, "moi-sau-co-so-doi")["trang_thai"], ("SUCCEEDED", "PARTIAL"))
        self.svc.tao_dot(A1, hop_dong_id=self.s["hd"], so_dot=3, ngay_nghiem_thu=None, khoa=self.K("dung-chung"))  # biên nhận M17 với khóa này
        self.assertEqual(self.loi(self.chay, dot2, "dung-chung"), "M4_IDEMPOTENCY_KHAC")

    # ------------------------------------------------------------------ K08
    def test_k08_worker_loi_va_ket_qua_xau_failed(self):
        dot2 = self.s["dot2"]
        loi = subprocess.CompletedProcess(args=["x"], returncode=5, stdout=b"", stderr=b"loi gia lap")
        with patch.object(self.XayDungK2, "_chay_worker", return_value=loi):
            r = self.chay(dot2, "loi-1")
        self.assertEqual(r["trang_thai"], "FAILED")
        ct = self.ket_qua(r["run_id"])
        self.assertFalse(ct["ket_qua"]["cong_bo"])
        self.assertTrue({"BASIS", "INPUT", "LOG"} <= {a["loai"] for a in ct["artifact"]})
        self.assertNotIn("REPORT_L3", {a["loai"] for a in ct["artifact"]})
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("không tính lại")):
            lai = self.svc.chung_tu_chay(A1, dot_id=dot2, revision=ct["run"]["revision"], expected_basis=ct["run"]["basis_sha256"], khoa=self.K("loi-1"))
        self.assertEqual((lai["lap_lai"], lai["run_id"], lai["trang_thai"]), (True, r["run_id"], "FAILED"))

        def nan_exit0(_svc, thu_muc):  # worker "thành công" nhưng ket_qua.json có NaN (JSON không chuẩn) → máy chủ phải đóng FAILED, không RUNNING
            (Path(thu_muc) / "ket_qua.json").write_bytes(b'{"trang_thai": "PARTIAL", "che_do": "L3", "x": NaN}')
            return subprocess.CompletedProcess(args=["x"], returncode=0, stdout=b"", stderr=b"")
        with patch.object(self.XayDungK2, "_chay_worker", nan_exit0):
            r2 = self.chay(dot2, "nan-1")
        self.assertEqual(r2["trang_thai"], "FAILED")
        self.assertIn("không hợp lệ", self.q("SELECT ly_do FROM m4.chung_tu_run WHERE id = %s", (r2["run_id"],)))
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_run WHERE trang_thai = 'RUNNING' AND id = %s", (r2["run_id"],)), 0)

    # ------------------------------------------------------------------ K08b
    def test_k08b_commit_chua_ro_va_doi_soat(self):
        dot2 = self.s["dot2"]
        goc = self.XayDungK2._chung_tu_cong_bo

        def mat_ket_noi(_svc, *a, **k):  # giả lập công bố mất kết nối TRƯỚC commit: lần chạy còn RUNNING, kết quả chưa rõ với người gọi
            raise DataError("M4_KET_QUA_CHUA_RO", "giả lập mất kết nối khi công bố")
        cs = self.ds(dot2)["co_so"]
        with patch.object(self.XayDungK2, "_chung_tu_cong_bo", mat_ket_noi):
            self.assertEqual(self.loi(self.svc.chung_tu_chay, A1, dot_id=dot2, revision=cs["revision"], expected_basis=cs["basis_sha256"],
                                      khoa=self.K("chua-ro")), "M4_KET_QUA_CHUA_RO")
        run = str(self.q("SELECT id FROM m4.chung_tu_run WHERE khoa = %s", (self.K("chua-ro"),)))
        self.assertEqual(self.q("SELECT trang_thai FROM m4.chung_tu_run WHERE id = %s", (run,)), "RUNNING")
        self.assertIs(self.XayDungK2._chung_tu_cong_bo, goc)
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("đối soát không được tính lại")):
            lai = self.svc.chung_tu_chay(A1, dot_id=dot2, revision=cs["revision"], expected_basis=cs["basis_sha256"], khoa=self.K("chua-ro"))
        self.assertEqual((lai["run_id"], lai.get("doi_soat")), (run, True))
        self.assertIn(self.q("SELECT trang_thai FROM m4.chung_tu_run WHERE id = %s", (run,)), ("SUCCEEDED", "PARTIAL", "STALE", "FAILED"))
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("không tính lại")):
            lai2 = self.svc.chung_tu_chay(A1, dot_id=dot2, revision=cs["revision"], expected_basis=cs["basis_sha256"], khoa=self.K("chua-ro"))
        self.assertEqual((lai2["run_id"], lai2["lap_lai"]), (run, True))  # sau đối soát: FINAL bình thường, không 'đang chạy'
        self.assertFalse(lai2.get("dang_chay"))

    # ------------------------------------------------------------------ K08c/K08d — S1 tại biên giao dịch/commit THẬT
    def _tiem_bien_cong_bo(self, svc, *, sau_commit: bool):
        """Bọc `_tx_review` của MỘT instance (KHÔNG patch _chung_tu_cong_bo): mọi giao dịch đi qua _tx_review gốc trên kết nối PG thật.
        SQL công bố lần 1 → thay bằng `SELECT 1/0` THẬT (DivisionByZero, lỗi SQL thường, rollback thật). Lần 2 (đóng FAILED dự phòng) → chạy thật rồi
        OperationalError TRƯỚC commit (rollback thật) hoặc InterfaceError SAU khi commit thật (mất ACK). Lần ≥3 (đối soát) đi thẳng."""
        goc = svc._tx_review
        st = {"cong_bo": 0, "tham_so": []}

        class Bao:
            def __init__(self, c):
                self._c, self.da_cong_bo_du_phong = c, False

            def __getattr__(self, k):
                return getattr(self._c, k)

            def execute(self, sql, params=None, **kw):
                if "m4.chung_tu_cong_bo(" in str(sql):
                    st["cong_bo"] += 1
                    st["tham_so"].append(params[4])  # trạng thái công bố đề nghị (SUCCEEDED/PARTIAL rồi FAILED)
                    if st["cong_bo"] == 1:
                        return self._c.execute("SELECT 1/0")
                    if st["cong_bo"] == 2:
                        cur = self._c.execute(sql, params, **kw)
                        self.da_cong_bo_du_phong = True
                        if not sau_commit:
                            raise psycopg.OperationalError("MO_PHONG_BIEN: mất kết nối trước commit của lần đóng FAILED dự phòng")
                        return cur
                return self._c.execute(sql, params, **kw)

        @contextmanager
        def tx(dt, *, rr=False):
            with goc(dt, rr=rr) as c:
                b = Bao(c)
                yield b
            if b.da_cong_bo_du_phong and sau_commit:  # commit THẬT đã xong — chỉ ACK mất
                raise psycopg.InterfaceError("MO_PHONG_BIEN: mất ACK sau commit của lần đóng FAILED dự phòng")
        return patch.object(svc, "_tx_review", tx), st

    def _bang_chung_run(self, run) -> dict:
        tm = self.goc / "m4-k2" / "m4-chung-tu-run" / run
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tm.iterdir() if p.is_file()} if tm.is_dir() else {}

    def _dem_khoa(self, khoa) -> dict:
        return {"run": self.q("SELECT count(*) FROM m4.chung_tu_run WHERE khoa = %s", (khoa,)),
                "bien_nhan": self.q("SELECT count(*) FROM m4.bien_nhan WHERE khoa = %s", (khoa,))}

    def _s1(self, ten, *, sau_commit: bool):
        dot2 = self.s["dot2"]
        svc = self._svc_moi()
        self.assertIs(svc.trich6, self.trich6)
        cs = self.ds(dot2)["co_so"]
        khoa = self.K(ten)
        body = dict(dot_id=dot2, revision=cs["revision"], expected_basis=cs["basis_sha256"], khoa=khoa)
        truoc = self.dem()
        p, st = self._tiem_bien_cong_bo(svc, sau_commit=sau_commit)
        with p:
            ma = self.loi(svc.chung_tu_chay, A1, **body)
        # trước sửa S1: 'DivisionByZero' (lỗi SQL lần đầu che UNKNOWN của fallback); sau sửa: UNKNOWN thật ra ngoài
        self.assertEqual(ma, "M4_KET_QUA_CHUA_RO")
        self.assertEqual(st["cong_bo"], 2)
        self.assertIn(st["tham_so"][0], ("SUCCEEDED", "PARTIAL"))  # tiền đề: lần đầu là kết quả tốt → mới có nhánh dự phòng
        self.assertEqual(st["tham_so"][1], "FAILED")
        self.assertEqual(self._dem_khoa(khoa)["run"], 1)
        run = str(self.q("SELECT id FROM m4.chung_tu_run WHERE khoa = %s", (khoa,)))
        self.assertEqual(self.dem()["thu_muc_chay"] - truoc["thu_muc_chay"], 1)  # worker thật chạy đúng MỘT lần
        return svc, body, khoa, run, truoc

    def _final_lai(self, body, run, tt):
        """Thử lại sau FINAL: cùng FINAL, 0 tính lại, 0 delta (trừ nhật ký đọc)."""
        moc = self.dem()
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("không tính lại")), \
                patch.object(self.XayDungK2, "_chung_tu_tinh", side_effect=AssertionError("không tính lại")):
            lai = self._svc_moi().chung_tu_chay(A1, **body)
        self.assertEqual((lai["run_id"], lai["lap_lai"], lai["trang_thai"]), (run, True, tt))
        self.assertEqual(self.dem(), moc)

    def test_k08c_s1_fallback_mat_ket_noi_truoc_commit(self):
        svc, body, khoa, run, truoc = self._s1("s1-truoc", sau_commit=False)
        # fallback rollback THẬT: chưa ghi gì — run còn RUNNING, không result/artifact; biên nhận chưa FINAL
        self.assertEqual(self.q("SELECT trang_thai FROM m4.chung_tu_run WHERE id = %s", (run,)), "RUNNING")
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_result WHERE run_id = %s", (run,)), 0)
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_artifact WHERE run_id = %s", (run,)), 0)
        self.assertLessEqual(self._dem_khoa(khoa)["bien_nhan"], 1)
        bang_chung = self._bang_chung_run(run)
        self.assertIn("worker.log", bang_chung)
        # cùng body/khóa trên service REOPEN (cùng client #6): đối soát đúng run cũ, KHÔNG tính lại
        with patch.object(self.XayDungK2, "_chay_worker", side_effect=AssertionError("đối soát không được tính lại")), \
                patch.object(self.XayDungK2, "_chung_tu_tinh", side_effect=AssertionError("đối soát không được tính lại")):
            lai = self._svc_moi().chung_tu_chay(A1, **body)
        self.assertEqual((lai["run_id"], lai.get("doi_soat")), (run, True))
        tt = self.q("SELECT trang_thai FROM m4.chung_tu_run WHERE id = %s", (run,))
        self.assertIn(tt, ("SUCCEEDED", "PARTIAL", "STALE", "FAILED"))
        self.assertEqual(lai["trang_thai"], tt)
        self.assertEqual(self._dem_khoa(khoa), {"run": 1, "bien_nhan": 1})
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_result WHERE run_id = %s", (run,)), 1)
        loai = [r[0] for r in self.admin.execute("SELECT loai FROM m4.chung_tu_artifact WHERE run_id = %s", (run,)).fetchall()]
        self.assertEqual(len(loai), len(set(loai)))  # không artifact trùng
        sau = self._bang_chung_run(run)
        self.assertEqual({k: sau.get(k) for k in bang_chung}, bang_chung)  # bằng chứng thư mục lần chạy nguyên
        self.assertEqual(self.dem()["chung_tu_run"] - truoc["chung_tu_run"], 1)
        self._final_lai(body, run, tt)
        self._final_lai(body, run, tt)

    def test_k08d_s1_fallback_mat_ack_sau_commit(self):
        svc, body, khoa, run, truoc = self._s1("s1-sau", sau_commit=True)
        # fallback ĐÃ commit thật (FAILED có bằng chứng + biên nhận FINAL) dù người gọi chỉ thấy UNKNOWN — đúng lý do không được khẳng định lỗi cũ
        self.assertEqual(self.q("SELECT trang_thai FROM m4.chung_tu_run WHERE id = %s", (run,)), "FAILED")
        self.assertIn("Công bố kết quả lỗi", self.q("SELECT ly_do FROM m4.chung_tu_run WHERE id = %s", (run,)))
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_result WHERE run_id = %s", (run,)), 1)
        self.assertFalse(self.q("SELECT cong_bo FROM m4.chung_tu_result WHERE run_id = %s", (run,)))
        self.assertEqual(self._dem_khoa(khoa), {"run": 1, "bien_nhan": 1})
        bang_chung = self._bang_chung_run(run)
        art = self.q("SELECT count(*) FROM m4.chung_tu_artifact WHERE run_id = %s", (run,))
        # cùng body/khóa: biên nhận FINAL trả lại đúng run cũ (không đối soát lại, không tính lại, không run/biên nhận mới)
        self._final_lai(body, run, "FAILED")
        self._final_lai(body, run, "FAILED")
        self.assertEqual(self._dem_khoa(khoa), {"run": 1, "bien_nhan": 1})
        self.assertEqual(self.q("SELECT count(*) FROM m4.chung_tu_artifact WHERE run_id = %s", (run,)), art)
        self.assertEqual(self._bang_chung_run(run), bang_chung)
        self.assertEqual(self.dem()["chung_tu_run"] - truoc["chung_tu_run"], 1)

    # ------------------------------------------------------------------ K09
    def test_k09_basis_doi_trong_luc_tinh_stale(self):
        dot2 = self.s["dot2"]
        goc = self.XayDungK2._chay_worker
        t = self

        def chay_roi_doi(self_, thu_muc):
            p = goc(self_, thu_muc)
            h = uuid.uuid4().hex[:6]
            moi = t.tai(_xlsx_bytes([("PL", {(1, 1): "PACKING LIST", (2, 1): f"No.: PL-{h}"})]), f"pl-{h}.xlsx", F.MEDIA_XLSX, "HO_SO_DOT", "pl-" + h)
            t.gan(dot2, moi, t.s["muc"][4], "gan-pl-" + h)
            return p
        with patch.object(self.XayDungK2, "_chay_worker", chay_roi_doi):
            r = self.chay(dot2, "stale-1")
        self.assertEqual(r["trang_thai"], "STALE", r)
        ct = self.ket_qua(r["run_id"])
        self.assertFalse(ct["ket_qua"]["cong_bo"])
        self.assertIn("REPORT_L3", {a["loai"] for a in ct["artifact"]})

    # ------------------------------------------------------------------ K10
    def test_k10_dong_thoi_cung_khoa(self):
        dot2 = self.s["dot2"]
        d = self.ds(dot2)
        exp, rev = d["co_so"]["basis_sha256"], d["co_so"]["revision"]
        truoc = self.dem()["chung_tu_run"]
        kq, loi = [], []
        svcs = [self._svc_moi() for _ in range(2)]  # kết nối đăng ký cleanup ngay khi tạo
        self.assertTrue(all(sv.trich6 is self.trich6 for sv in svcs))  # hai kết nối đồng thời: CÙNG client #6 chung/host/scope

        def mot(sv):
            try:
                kq.append(sv.chung_tu_chay(A1, dot_id=dot2, revision=rev, expected_basis=exp, khoa=self.K("dong-thoi")))
            except BaseException as exc:  # noqa: BLE001
                loi.append(exc)
        ts = [threading.Thread(target=mot, args=(sv,), daemon=True) for sv in svcs]
        try:
            for x in ts:
                x.start()
        finally:
            for x in ts:
                x.join(1200)
        self.assertEqual([x.is_alive() for x in ts], [False, False], "luồng đồng thời không kết thúc trong hạn")
        self.assertEqual((loi, len(kq)), ([], 2))
        self.assertEqual(len({r["run_id"] for r in kq}), 1)
        self.assertEqual(self.dem()["chung_tu_run"] - truoc, 1)

    # ------------------------------------------------------------------ K11
    def test_k11_review_duong_tren_dot_da_nop(self):
        dot1 = self.s["dot1"]
        d = self.ds(dot1, REVIEW)
        self.assertEqual((d["co_so"]["san_sang"], d["co_so"]["quyen"]), (True, "REVIEW"))
        r = self.chay(dot1, "rv-1", login=REVIEW)
        self.assertIn(r["trang_thai"], ("SUCCEEDED", "PARTIAL"), r)
        ct = self.ket_qua(r["run_id"], REVIEW)
        self.assertEqual((ct["run"]["quyen"], ct["run"]["tao_boi"]), ("REVIEW", REVIEW))
        self.assertEqual(self.ket_qua(r["run_id"], A1)["run"]["id"], r["run_id"])  # SOAN đúng dự án đọc được lần chạy của reviewer
        self.s["run_rv"] = r["run_id"]

    # ------------------------------------------------------------------ K12 (cuối: thu hồi không đảo ngược)
    def test_k12_thu_hoi_giua_luc_tinh_va_sau_thu_hoi(self):
        if "run_rv" not in self.s:
            self.skipTest("K11 chưa có lần chạy reviewer — NOT_RUN")
        dot1 = self.s["dot1"]
        q = self.q("""SELECT q.id FROM m4.quyen_du_an q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                      WHERE n.dang_nhap = %s AND q.du_an_id = %s AND q.vai = 'REVIEW' AND q.thu_hoi_luc IS NULL""", (REVIEW, self.du_an()))
        cs = self.ds(dot1, REVIEW)["co_so"]
        goc = self.XayDungK2._chung_tu_tinh

        def tinh_roi_thu_hoi(svc, *a, **k):
            out = goc(svc, *a, **k)
            self.admin.execute("SELECT m4.thu_hoi_quyen_du_an(%s, 'MO_PHONG_QUAN_TRI_TEST', 'Kiểm thu hồi M4-02B')", (q,))
            return out
        with patch.object(self.XayDungK2, "_chung_tu_tinh", tinh_roi_thu_hoi):
            self.assertIn(self.loi(self.svc.chung_tu_chay, REVIEW, dot_id=dot1, revision=cs["revision"], expected_basis=cs["basis_sha256"],
                                   khoa=self.K("rv-thu-hoi")), ("M4_CHUNG_TU_KHONG_THAY", "M4_CHUNG_TU_PHAM_VI"))
        run = self.q("SELECT id FROM m4.chung_tu_run WHERE khoa = %s", (self.K("rv-thu-hoi"),))
        self.assertEqual(self.q("SELECT trang_thai FROM m4.chung_tu_run WHERE id = %s", (run,)), "CANCELLED")
        self.assertFalse(self.q("SELECT cong_bo FROM m4.chung_tu_result WHERE run_id = %s", (run,)))
        truoc = self.dem()
        # sau thu hồi: replay đúng body cũ (biên nhận) / đọc / tải bị chặn theo quyền hiện hành TRƯỚC tra biên nhận/registry
        cs_cu = self.ket_qua(self.s["run_rv"], A1)["run"]
        self.assertEqual(self.loi(self.svc.chung_tu_chay, REVIEW, dot_id=dot1, revision=cs_cu["revision"], expected_basis=cs_cu["basis_sha256"],
                                  khoa=self.K("rv-1")), "M4_CHUNG_TU_KHONG_THAY")
        self.assertEqual(self.loi(self.svc.chung_tu_chi_tiet, REVIEW, self.s["run_rv"]), "M4_CHUNG_TU_KHONG_THAY")
        art = self.q("SELECT id FROM m4.chung_tu_artifact WHERE run_id = %s AND loai = 'RESULT'", (self.s["run_rv"],))
        self.assertEqual(self.loi(self.svc.chung_tu_tai, REVIEW, self.s["run_rv"], str(art)), "M4_CHUNG_TU_KHONG_THAY")
        self.assertEqual(self.dem(), truoc)
        self.assertEqual(self.q("SELECT trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (REVIEW,)), "HOAT_DONG")


# ================================================================================================== S1 MOCK_BOUNDARY (không PG)
class _Cur:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _LoiMa(psycopg.DatabaseError if psycopg is not None else Exception):
    """Lỗi SQL có mã RAISE 'MA: …' như hàm CSDL (diag.message_primary) — dựng tay ở biên, không qua PG."""
    @property
    def diag(self):
        return SimpleNamespace(message_primary=str(self.args[0]) if self.args else "")


class _KetNoiBien:
    """Kết nối GIẢ chỉ mô phỏng biên giao dịch: transaction() vào/commit/rollback + execute; kịch bản lỗi theo (pha, số giao dịch).
    pha: 'vao' (BEGIN), 'cong_bo' (câu SQL công bố), 'huy' (câu SQL hủy), 'commit' (thoát giao dịch không lỗi)."""
    closed = broken = False

    def __init__(self, kich_ban):
        self.kich_ban, self.so_tx, self.tx = dict(kich_ban), 0, None
        self.sql, self.da_commit, self.rollback = [], [], []

    def transaction(self):
        kn = self

        class _GD:
            def __enter__(self_):
                kn.so_tx += 1
                kn.tx = kn.so_tx
                loi = kn.kich_ban.get(("vao", kn.tx))
                if loi is not None:
                    raise loi
                return self_

            def __exit__(self_, et, ev, tb):
                n = kn.tx
                if et is None:
                    loi = kn.kich_ban.get(("commit", n))
                    if loi is not None:
                        raise loi
                    kn.da_commit.append(n)
                else:
                    kn.rollback.append(n)
                return False
        return _GD()

    def execute(self, sql, params=()):
        self.sql.append((self.tx, " ".join(str(sql).split())[:60], params))
        for pha, mau in (("cong_bo", "m4.chung_tu_cong_bo("), ("huy", "m4.chung_tu_huy(")):
            if mau in str(sql):
                loi = self.kich_ban.get((pha, self.tx))
                if loi is not None:
                    raise loi
                if pha == "cong_bo":
                    return _Cur({"r": {"lap_lai": False, "ket_qua": {"run_id": _S1_RUN, "trang_thai": params[4]}}})
        return _Cur(None)

    def cong_bo(self):
        return [(tx, p[4]) for tx, s, p in self.sql if s.startswith("SELECT m4.chung_tu_cong_bo(")]


_S1_RUN, _S1_DOT = str(uuid.uuid4()), str(uuid.uuid4())


@unittest.skipUnless(psycopg is not None, "Không có psycopg — biên S1 không chạy (NOT_RUN)")
class M4CongBoS1Bien(unittest.TestCase):
    """MOCK_BOUNDARY (KHÔNG phải bằng chứng PostgreSQL): gọi `XayDungK2._chung_tu_cong_bo` THẬT; chỉ kết nối tin cậy là giả ở biên giao dịch/commit,
    cùng hai bước dựng basis (`_chung_tu_co_so`/`_sha_co_so`) được thay bằng hằng. Không compute/worker/run mới trong mọi nhánh."""

    def svc(self, kich_ban):
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        s = XayDungK2.__new__(XayDungK2)  # bỏ qua __init__ (đăng ký dumper psycopg trên kết nối thật)
        s.conn, s.conn_tin_cay = None, _KetNoiBien(kich_ban)
        s.root, s.chi_mo_phong, s.hom_nay, s.trich6 = Path(tempfile.gettempdir()), True, (lambda: date(2026, 3, 1)), None
        s._chung_tu_co_so = lambda c, dot: {"dot": dot}
        s._sha_co_so = lambda co: "a" * 64
        s._chay_worker = s._chung_tu_tinh = s._chung_tu_doi_soat = None  # gọi tới = lỗi kiểm thử (không tính lại/đối soát trong publish)
        return s

    def goi(self, s):
        return s._chung_tu_cong_bo({"id": str(uuid.uuid4()), "dang_nhap": A1}, _S1_RUN, {"trang_thai": "PARTIAL", "coverage": {}}, [], None, dot=_S1_DOT)

    def ma(self, s):
        try:
            self.goi(s)
        except DataError as exc:
            return exc.code
        except psycopg.Error as exc:
            return type(exc).__name__ + ":" + (getattr(exc.diag, "message_primary", "") or "").split(":", 1)[0]
        self.fail("không lỗi")

    LOI_SQL = staticmethod(lambda: psycopg.errors.DivisionByZero("division by zero"))

    def test_b1_fallback_mat_ket_noi_khi_mo_giao_dich(self):
        s = self.svc({("cong_bo", 1): self.LOI_SQL(), ("vao", 2): psycopg.OperationalError("mất kết nối")})
        self.assertEqual(self.ma(s), "M4_KET_QUA_CHUA_RO")  # trước sửa: DivisionByZero
        self.assertEqual((s.conn_tin_cay.rollback, s.conn_tin_cay.da_commit), ([1], []))
        self.assertEqual(s.conn_tin_cay.cong_bo(), [(1, "PARTIAL")])

    def test_b2_fallback_mat_ack_khi_commit(self):
        s = self.svc({("cong_bo", 1): self.LOI_SQL(), ("commit", 2): psycopg.InterfaceError("mất ACK commit")})
        self.assertEqual(self.ma(s), "M4_KET_QUA_CHUA_RO")
        self.assertEqual(s.conn_tin_cay.cong_bo(), [(1, "PARTIAL"), (2, "FAILED")])  # đúng MỘT lần dự phòng, không thêm
        self.assertEqual(s.conn_tin_cay.so_tx, 2)

    def test_b3_fallback_mat_ket_noi_giua_cau_cong_bo(self):
        s = self.svc({("cong_bo", 1): self.LOI_SQL(), ("cong_bo", 2): psycopg.OperationalError("đứt giữa câu")})
        self.assertEqual(self.ma(s), "M4_KET_QUA_CHUA_RO")
        self.assertEqual((s.conn_tin_cay.rollback, s.conn_tin_cay.da_commit), ([1, 2], []))

    def test_b4_fallback_thanh_cong_van_failed(self):
        s = self.svc({("cong_bo", 1): self.LOI_SQL()})
        kq = self.goi(s)
        self.assertEqual((kq["trang_thai"], kq["lap_lai"]), ("FAILED", False))
        self.assertEqual(s.conn_tin_cay.da_commit, [2])

    def test_b5_fallback_loi_sql_ro_giu_loi_ro(self):
        s = self.svc({("cong_bo", 1): self.LOI_SQL(), ("cong_bo", 2): psycopg.errors.DivisionByZero("lần 2")})
        self.assertEqual(self.ma(s).split(":")[0], "DivisionByZero")  # cả hai giao dịch rollback rõ → lỗi rõ, không UNKNOWN
        self.assertEqual((s.conn_tin_cay.rollback, s.conn_tin_cay.da_commit), ([1, 2], []))

    def test_b6_fallback_gap_quyen_doi_bao_loi_quyen(self):
        s = self.svc({("cong_bo", 1): self.LOI_SQL(), ("cong_bo", 2): _LoiMa("M4_CHUNG_TU_PHAM_VI: mất quyền")})
        self.assertEqual(self.ma(s), "_LoiMa:M4_CHUNG_TU_PHAM_VI")
        self.assertEqual(s.conn_tin_cay.da_commit, [3])  # giao dịch hủy (CANCELLED giữ bằng chứng) đã commit
        self.assertTrue(any(tx == 3 and q.startswith("SELECT m4.chung_tu_huy(") for tx, q, _ in s.conn_tin_cay.sql))

    def test_b7_fallback_quyen_doi_mat_ack_khi_huy(self):
        s = self.svc({("cong_bo", 1): self.LOI_SQL(), ("cong_bo", 2): _LoiMa("M4_CHUNG_TU_PHAM_VI: mất quyền"),
                      ("commit", 3): psycopg.OperationalError("mất ACK commit hủy")})
        self.assertEqual(self.ma(s), "M4_KET_QUA_CHUA_RO")

    def test_b8_loi_ket_noi_ngay_lan_dau_khong_du_phong(self):
        s = self.svc({("commit", 1): psycopg.OperationalError("mất ACK commit đầu")})
        self.assertEqual(self.ma(s), "M4_KET_QUA_CHUA_RO")
        self.assertEqual(s.conn_tin_cay.so_tx, 1)  # không mở lần dự phòng (commit đầu có thể đã có hiệu lực)


if __name__ == "__main__":
    unittest.main()
