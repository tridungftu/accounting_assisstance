"""M4-01B — kiểm tĩnh/thuần (không cần PostgreSQL). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN); Root chạy sau terminal.

Ca theo handoff docs/GIAO-CODE-M4-01B-SUA-GATE-VA-BO-SUNG-KIEM.md §3:
- (6) Lineage migration: prefix 1–16 là đúng các hằng cũ (identity), M17 là `m4.sql_m17.M0017_M4`; tùy chọn so SHA-256 của 715.854 byte đầu
  `pg_migrations.py` với giá trị Root cấp qua M4_PREFIX_SHA256 (không tự lấy đáp án từ code). Danh mục XD đủ 37 mã có TC-09; M4 chỉ cho HĐ XAY_DUNG.
- (1) Tĩnh M17: không còn chr(0), không còn m4.ket_thuc/m4.bat_dau; hàm ghi nguồn tin cậy không SECURITY DEFINER, có chốt chủ bảng, KHÔNG cấp cho app_web.
  Tên tệp: NUL/đường dẫn/giả media bị chặn trước khi ghi (kiểm thuần ở adapter).
- (3) Bộ nạp ghim: module sentinel sai SHA/chưa ghim/trùng tên KHÔNG được thực thi; DOCX Track Changes chặn trước Office/cleanup (cần lõi nguồn đã nạp).
- (4) BOQ XLSX thật (cần lõi nguồn đã nạp + openpyxl): lệch KL×ĐG là phát hiện không chặn; ô trống khác 0 tường minh; ô số không đọc được/map sai chặn.
- (6) Tool nạp nguồn: --kiem thiếu tệp → mã khác 0; nạp đủ → 0, bytes đúng; đích khác bytes → dừng, không ghi đè.
M4-01B2 phản ví dụ: cache có dấu ghim sai pin/origin/loader; DOCX alias prefix/xuống dòng/Strict/header; BOQ tên chứa mẫu số học + KL 'abc';
staging giữ lại khi thành công/lỗi/retry; tep_da_nop theo phạm vi; FINAL BOQ có đủ mảng. Prefix: first17 identity, cho phép nối migration.
Mọi thư mục tạm dùng mkdtemp và GIỮ LẠI làm bằng chứng (không TemporaryDirectory/cleanup).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import shutil
import sys
import tempfile
import types
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from kho_tri_thuc.ha_tang import pg_migrations as PM
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.kiem_chung import fixtures_m4 as F
from kho_tri_thuc.m4 import nap_ghim, nguon_review as NR, sql_m17 as S

ROOT = Path(__file__).resolve().parents[1]
PREFIX_BYTES = 715_854  # handoff M4-01B2 §1: độ dài prefix migrations 1–16 Root đã đối chiếu
PREFIX_SHA256 = "208a03354a989e2d1b469271ed3e324638e1dc0d1e0ae1db376c195d0d57de0a"  # handoff M4-01B2 §1
try:
    import openpyxl  # noqa: F401
except ImportError:  # pragma: no cover
    openpyxl = None


def _tam(ten: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=f"ktt_m4_01b_{ten}_"))  # giữ lại, không xóa


def _nguon_da_nap() -> bool:
    return NR.GOC.is_dir() and all((NR.GOC / rel).is_file() for rel in NR.PIN)


class LineageMigration(unittest.TestCase):
    def test_prefix_1_16_giu_nguyen_hang_cu(self):
        cu = (PM.M0001, PM.M0002, PM.M0003, PM.M0004, PM.M0005, PM.M0006, PM.M0007, PM.M0008, PM.M0009, PM.M0010, PM.M0011, PM.M0012,
              PM.M0013_COMMON, PM.M0014_M5, PM.M0015_M2_BRIDGE, PM.M0016_L11_QUANTITY)
        # first17 theo identity; cho phép migration tương lai nối thêm (không hardcode schema mới nhất = 17)
        self.assertGreaterEqual(len(PM.PG_MIGRATIONS), 17)
        for i, m in enumerate(cu):
            self.assertIs(PM.PG_MIGRATIONS[i], m, f"migration {i + 1}")
        self.assertIs(PM.PG_MIGRATIONS[16], S.M0017_M4)
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertNotIn(PM._M0017_M4_PARTIAL_M4_01, PM.PG_MIGRATIONS)  # bản partial chỉ giữ để đối chiếu

    def test_prefix_byte_khop_root(self):
        """715.854 byte đầu pg_migrations.py = prefix 1–16 Root đã chốt (SHA trong handoff M4-01B2 §1, không lấy từ code)."""
        raw = (ROOT / "src" / "kho_tri_thuc" / "ha_tang" / "pg_migrations.py").read_bytes()[:PREFIX_BYTES]
        self.assertEqual(hashlib.sha256(raw).hexdigest(), PREFIX_SHA256)

    def test_danh_muc_xay_dung_37_ma_co_tc09(self):
        ma = [m for m, _, _ in S.DANH_MUC_THAM_SO]
        self.assertEqual(len(ma), 37)
        self.assertEqual(len(set(ma)), 37)
        self.assertIn("TC-09", ma)
        # danh mục 37 mã chỉ gắn HĐ module M4 loại XAY_DUNG — không ép vào HĐ KCN/nhà ở
        self.assertIn("module_chu = 'M4' AND loai = 'XAY_DUNG'", "\n".join(S.M0017_M4))


def _ham(sql_all: str, sig_ten: str) -> str:
    """Thân CREATE FUNCTION của hàm (tên đầy đủ, vd m4.ghi_tep) — tới `END $$` (plpgsql) hoặc dòng `$$` đóng (LANGUAGE sql)."""
    m = re.search(r"CREATE OR REPLACE FUNCTION " + re.escape(sig_ten) + r"\(.*?(?:END \$\$|\n[ \t]*\$\$)", sql_all, re.S)
    assert m, sig_ten
    return m.group(0)


class TinhM17(unittest.TestCase):
    sql = "\n".join(S.M0017_M4)

    def test_khong_con_chr0_va_cua_tu_chot(self):
        self.assertNotIn("chr(0)", self.sql)
        for cam in ("m4.ket_thuc", "m4.bat_dau"):
            self.assertNotIn(cam, self.sql)

    def test_ham_tin_cay_khong_definer_co_chot_chu_bang_khong_cap_app_web(self):
        cap = [s for s in S.M0017_M4 if "GRANT EXECUTE ON FUNCTION" in s]
        self.assertEqual(len(cap), 1)
        for sig in S.HAM_TIN_CAY:
            ten = sig.split("(", 1)[0]
            than = _ham(self.sql, ten)
            dau = than.split("AS $$", 1)[0]
            self.assertNotIn("SECURITY DEFINER", dau, ten)
            self.assertTrue("M4_CHI_MAY_CHU_NGUON" in than or "M4_QUYEN_CHI_QUAN_TRI" in than, ten)
            self.assertNotIn(ten + "(", cap[0], ten)
        for sig in S.HAM_NOI_BO:
            self.assertNotIn(sig.split("(", 1)[0] + "(", cap[0], sig)
        self.assertIn("REVOKE EXECUTE ON FUNCTION", self.sql)

    def test_bien_nhan_rls_kiem_pham_vi_hien_hanh(self):
        m = re.search(r"CREATE POLICY bien_nhan_web.*?;", self.sql, re.S)
        self.assertIsNotNone(m)
        self.assertIn("master.m4_duoc(du_an_id", m.group(0))

    def test_thu_hoi_chi_ghi_them(self):
        self.assertIn("thu_hoi_luc", self.sql)
        self.assertIn("M4_QUYEN_BAT_BIEN", self.sql)
        self.assertNotRegex(self.sql, r"(?i)DELETE FROM m4\.quyen_du_an")
        self.assertIn("thu_hoi_luc IS NULL AND master.ktt_duoc", self.sql)  # m4_duoc chỉ tính quyền chưa thu hồi

    def test_lenh_tra_bien_nhan_truoc_revision(self):
        """Ở mỗi lệnh có revision: khối tra biên nhận đứng TRƯỚC khối kiểm revision."""
        for ten in ("m4.gan_tep_hop_dong", "m4.xac_nhan_tham_so", "m4.khai_phu_luc", "m4.them_phu_luc", "m4.huy_phu_luc", "m4.sua_dot",
                    "m4.gan_tep_dot", "m4.nop", "m4.ghi_trich_xuat", "m4.sua_tham_so", "m4.ghi_boq"):
            than = _ham(self.sql, ten)
            self.assertIn("m4._bn_tra(", than, ten)
            self.assertLess(than.index("m4._bn_tra("), than.index("M4_REVISION_CU"), ten)
            self.assertIn("m4._bn_ghi(", than, ten)  # FINAL do chính lệnh chốt trong cùng giao dịch


class TenVaMediaTep(unittest.TestCase):
    def test_ten_xau_bi_chan(self):
        for ten in ("a\x00.docx", "../hd.docx", "thu_muc/hd.docx", "C:hd.docx", " hd.docx", "..", "", "a\x01.docx"):
            with self.assertRaises(DataError) as cm:
                NR.kiem_tep(F.hop_dong_docx(), ten, F.MEDIA_DOCX, "HOP_DONG")
            self.assertEqual(cm.exception.code, "M4_TEN_TEP_SAI", repr(ten))

    def test_gia_media_bi_chan(self):
        ca = ((F.hop_dong_docx(), "hd.pdf", "application/pdf", "HOP_DONG"),       # bytes DOCX khai PDF
              (F.pdf_demo(), "hd.docx", F.MEDIA_DOCX, "HOP_DONG"),                # bytes PDF khai DOCX
              (F.hop_dong_docx(), "hd.docx", F.MEDIA_XLSX, "BOQ"))                # đuôi .docx khai XLSX
        for raw, ten, media, vai in ca:
            with self.assertRaises(DataError) as cm:
                NR.kiem_tep(raw, ten, media, vai)
            self.assertIn(cm.exception.code, ("M4_TEP_MEDIA_KHONG_KHOP", "M4_TEP_HONG"), ten)

    def test_tep_hop_le_tinh_sha_tu_bytes(self):
        raw = F.hop_dong_docx()
        kq = NR.kiem_tep(raw, "Hợp đồng DEMO.docx", F.MEDIA_DOCX, "HOP_DONG")
        self.assertEqual(kq["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(kq["byte_length"], len(raw))


class BoNapGhim(unittest.TestCase):
    """Gói thử tên riêng (không đụng tên lõi thật trong tiến trình). Sentinel ghi tệp nếu bị thực thi."""

    def _goi(self, noi_dung_init=None):
        """noi_dung_init None → __init__ là sentinel (ghi tệp DA_THUC_THI nếu bị exec)."""
        goc = _tam("nap")
        ten = "m4ghim_" + uuid.uuid4().hex[:8]
        (goc / ten).mkdir()
        # M4-01B5: bytes UTF-8/LF xác định (write_text trên Windows đổi \n thành CRLF → lệch SHA literal mong đợi)
        (goc / ten / "__init__.py").write_bytes((self._sentinel(goc) if noi_dung_init is None else noi_dung_init).encode("utf-8"))
        (goc / ten / "con.py").write_bytes("GIA_TRI = 2\n".encode("utf-8"))
        return goc, ten

    @staticmethod
    def _sentinel(goc: Path) -> str:
        return f"open({str(goc / 'DA_THUC_THI')!r}, 'w').close()\nGIA_TRI = 1\n"

    def test_dung_pin_nap_duoc(self):
        goc, ten = self._goi("GIA_TRI = 1\n")
        pin = {f"{ten}/__init__.py": hashlib.sha256(b"GIA_TRI = 1\n").hexdigest()}
        bo = nap_ghim.BoNapGhim(goc, pin, (ten,))
        spec = bo.find_spec(ten)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertEqual(m.GIA_TRI, 1)
        self.assertEqual(getattr(m, nap_ghim.DAU_GHIM), pin[f"{ten}/__init__.py"])

    def test_sai_pin_khong_thuc_thi(self):
        goc, ten = self._goi()
        bo =nap_ghim.BoNapGhim(goc, {f"{ten}/__init__.py": "0" * 64}, (ten,))
        spec = bo.find_spec(ten)
        with self.assertRaises(nap_ghim.LoiNapGhim) as cm:
            spec.loader.exec_module(importlib.util.module_from_spec(spec))
        self.assertEqual(cm.exception.code, "M4_NGUON_REVIEW_SAI_PIN")
        self.assertFalse((goc / "DA_THUC_THI").exists())

    def test_module_chua_ghim_bi_tu_choi(self):
        goc, ten = self._goi("GIA_TRI = 1\n")
        bo = nap_ghim.BoNapGhim(goc, {f"{ten}/__init__.py": hashlib.sha256(b"GIA_TRI = 1\n").hexdigest()}, (ten,))
        with self.assertRaises(nap_ghim.LoiNapGhim) as cm:
            bo.find_spec(f"{ten}.con")
        self.assertEqual(cm.exception.code, "M4_NGUON_REVIEW_CHUA_GHIM")
        self.assertIsNone(bo.find_spec("json"))  # ngoài gói gốc → để hệ thống nạp như thường

    def test_xung_dot_ten_trong_sys_modules(self):
        ten = "m4ghim_" + uuid.uuid4().hex[:8]
        with patch.dict(sys.modules, {ten: types.ModuleType(ten)}):
            self.assertEqual(nap_ghim.xung_dot((ten,)), [ten])

    @unittest.skipUnless(_nguon_da_nap(), "Lõi nguồn chưa nạp (Root chạy tools/nap_nguon_review_m4.py) — NOT_RUN")
    def test_module_trung_ten_tren_sys_path_khong_chay(self):
        """master_hd giả có sentinel đặt đầu sys.path: NR.nap phải nạp bản ghim từ review_goc, sentinel không chạy."""
        tam = _tam("trung_ten")
        (tam / "master_hd.py").write_text(self._sentinel(tam), encoding="utf-8")
        with patch.object(sys, "path", [str(tam)] + sys.path):
            NR.nap()
            import master_hd
        self.assertFalse((tam / "DA_THUC_THI").exists())
        self.assertEqual(Path(master_hd.__file__).resolve().parent, NR.GOC.resolve())
        self.assertEqual(getattr(master_hd, nap_ghim.DAU_GHIM), NR.PIN["master_hd.py"])


class _CamOffice:
    """Sentinel: bất kỳ lời gọi tiến trình ngoài/xóa cây thư mục nào đều làm test fail."""

    def __enter__(self):
        def cam(*a, **k):
            raise AssertionError(f"Không được gọi Office/cleanup: {a[:1]}")
        self._p = [patch.object(subprocess, "run", cam), patch.object(subprocess, "Popen", cam), patch.object(shutil, "rmtree", cam),
                   patch.object(os, "system", cam)]
        if hasattr(os, "startfile"):
            self._p.append(patch.object(os, "startfile", cam))
        for p in self._p:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self._p):
            p.stop()


class TrackChanges(unittest.TestCase):
    def test_khong_phai_docx_chan_truoc_khi_nap(self):
        with self.assertRaises(DataError) as cm:
            NR.kiem_docx_an_toan(F.pdf_demo())
        self.assertEqual(cm.exception.code, "M4_DOCX_KHONG_HO_TRO")

    @unittest.skipUnless(_nguon_da_nap(), "Lõi nguồn chưa nạp — NOT_RUN")
    def test_docx_con_sua_doi_khong_mo_office_khong_ghi(self):
        raw = F.hop_dong_docx(track_changes=True)
        lam = _tam("track")
        with _CamOffice():
            with self.assertRaises(DataError) as cm:
                NR.van_ban_hop_dong(raw, lam)
        self.assertEqual(cm.exception.code, "M4_DOCX_CON_SUA_DOI")
        self.assertEqual(list(lam.iterdir()), [])  # chưa tạo bản làm việc → read_contract chưa được gọi

    def test_trich_docx_con_sua_doi_khong_ho_tro(self):
        """CRM-41-01: trích đi qua engine dùng chung #6 (client tiêm) — kiểm an toàn DOCX vẫn chặn TRƯỚC khi gửi bytes: client sentinel không
        được gọi. (Đổi wiring phụ thuộc engine; không còn cần lõi nguồn chép đã nạp cho ca này.)"""
        class _ClientCam:
            san_sang = True

            def trich(self, *a, **k):
                raise AssertionError("DOCX còn Track Changes không được gửi tới engine")
        lam = _tam("track_trich") / "lan"
        with _CamOffice():
            kq = NR.trich_hop_dong(F.hop_dong_docx(track_changes=True), F.MEDIA_DOCX, lam, client=_ClientCam(), request_id="m4:test-track")
        self.assertEqual(kq["trang_thai"], "KHONG_HO_TRO")
        self.assertEqual(kq["ket_qua"], [])
        self.assertFalse(lam.exists())


@unittest.skipUnless(_nguon_da_nap() and openpyxl is not None, "Lõi nguồn chưa nạp hoặc thiếu openpyxl — NOT_RUN")
class BoqPhanLoai(unittest.TestCase):
    def _doc(self, dong):
        p = _tam("boq") / "boq.xlsx"
        p.write_bytes(F.boq_xlsx(dong))
        return NR.boq_doc(p, "BOQ", 1, dict(F.BOQ_COT))

    def test_lech_so_hoc_la_phat_hien_khong_chan(self):
        rows, chan, phat_hien = self._doc(F.BOQ_LOI_SO_HOC)
        self.assertEqual(chan, [])
        # HM-03 ở dòng Excel 4 (tiêu đề dòng 1): 10 × 20.000 = 200.000 ≠ 999
        self.assertTrue(any(p["dong"] == 4 and "G4" in p["o"] for p in phat_hien), phat_hien)
        self.assertTrue(all(p["ma"] == "BOQ_SO_HOC_LECH" for p in phat_hien))
        hm03 = [r for r in rows if r["ma_rieng"] == "HM-03"]
        self.assertEqual(len(hm03), 1)
        self.assertEqual(hm03[0]["o_goc"], {"kl": {"tho": "10", "kieu": "SO", "o": "E4"}, "don_gia": {"tho": "20000", "kieu": "SO", "o": "F4"},
                                            "thanh_tien": {"tho": "999", "kieu": "SO", "o": "G4"}})  # giữ nguyên ô trong tệp
        self.assertEqual(Decimal(hm03[0]["thanh_tien"]), Decimal(999))  # không sửa thành tiền theo KL×ĐG

    def test_boq_khong_phat_hien(self):
        _, chan, phat_hien = self._doc(F.BOQ_GOC)
        self.assertEqual((chan, phat_hien), ([], []))

    def test_trong_khac_0_tuong_minh(self):
        rows, _, _ = self._doc(F.BOQ_TRONG_VA_0)
        theo_ma = {r["ma_rieng"]: r for r in rows}
        self.assertIn("HM-01", theo_ma)
        self.assertIn("HM-02", theo_ma)
        self.assertEqual(theo_ma["HM-01"]["o_goc"]["kl"]["kieu"], "TRONG")
        self.assertIsNone(theo_ma["HM-01"]["kl"])
        self.assertEqual(theo_ma["HM-01"]["o_goc"]["kl"]["o"], "E3")
        self.assertEqual(theo_ma["HM-02"]["o_goc"]["kl"], {"tho": "0", "kieu": "SO", "o": "E4"})
        self.assertIsNotNone(theo_ma["HM-02"]["kl"])
        self.assertEqual(Decimal(theo_ma["HM-02"]["kl"]), 0)

    def test_so_khong_doc_duoc_chan(self):
        rows, chan, _ = self._doc(F.BOQ_SO_KHONG_DOC)
        self.assertTrue(chan, "ô Khối lượng là chữ phải là lỗi chặn")
        self.assertTrue(all(c["ma"] != "BOQ_SO_HOC_LECH" for c in chan))

    def test_map_cot_sai_chan(self):
        rong = {k: c for k, c in zip(NR.TRUONG_BOQ, ("T", "U", "V", "W", "X", "Y", "Z"))}  # các cột không có dữ liệu
        p = _tam("boq_map") / "boq.xlsx"
        p.write_bytes(F.boq_xlsx(F.BOQ_GOC))
        try:
            _, chan, _ = NR.boq_doc(p, "BOQ", 1, rong)
        except DataError as exc:
            self.assertIn(exc.code, ("M4_BOQ_MAP_SAI", "M4_BOQ_KHONG_DOC_DUOC"))
        else:
            self.assertTrue(chan)

    def test_map_truong_la_chan_truoc_khi_doc(self):
        with self.assertRaises(DataError) as cm:
            NR.boq_doc(Path("khong_ton_tai.xlsx"), "BOQ", 1, {"abc": "A"})
        self.assertEqual(cm.exception.code, "M4_BOQ_MAP_SAI")


def _cong_cu():
    spec = importlib.util.spec_from_file_location("m4_tool_nap_nguon_thu", ROOT / "tools" / "nap_nguon_review_m4.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class CongCuNapNguon(unittest.TestCase):
    """Reference giả tối thiểu trong thư mục tạm (giữ lại); PIN inject — không đụng review_goc thật."""

    TEP = {"goi/__init__.py": b"X = 1\n", "goi/du_lieu.csv": b"ma,ten\nA,B\n", "README.md": b"# bo qua\n", "tests/t.py": b"bo qua\n"}

    def _ref(self, sha_sai: bool = False) -> Path:
        nguon = _tam("ref")
        for rel, b in self.TEP.items():
            (nguon / rel).parent.mkdir(parents=True, exist_ok=True)
            (nguon / rel).write_bytes(b)
        manifest = [{"path": rel, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for rel, b in self.TEP.items()]
        if sha_sai:
            manifest[0]["sha256"] = "0" * 64
        (nguon / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return nguon

    def setUp(self):
        self.tool = _cong_cu()
        self.tep = self.TEP
        self.nguon = self._ref()
        self.pin = {"goi/__init__.py": hashlib.sha256(b"X = 1\n").hexdigest()}
        self.out = []

    def chay(self, kiem, dich, pin=None):
        return self.tool.chay(kiem, nguon=self.nguon, dich=dich, pin=self.pin if pin is None else pin, in_ra=lambda *a: self.out.append(a))

    def test_kiem_thieu_tep_khac_0_khong_ghi(self):
        dich = _tam("dich") / "review_goc"
        self.assertEqual(self.chay(True, dich), 1)
        self.assertFalse(dich.exists())

    def test_nap_du_roi_kiem_0_bytes_dung(self):
        dich = _tam("dich") / "review_goc"
        self.assertEqual(self.chay(False, dich), 0)
        for rel in ("goi/__init__.py", "goi/du_lieu.csv"):
            self.assertEqual((dich / rel).read_bytes(), self.tep[rel])
        self.assertFalse((dich / "README.md").exists())
        self.assertFalse((dich / "tests").exists())
        self.assertEqual(self.chay(True, dich), 0)
        self.assertEqual(self.chay(False, dich), 0)  # chạy lại: cùng bytes → bỏ qua

    def test_dich_khac_bytes_dung_khong_ghi_de(self):
        dich = _tam("dich") / "review_goc"
        (dich / "goi").mkdir(parents=True)
        (dich / "goi" / "__init__.py").write_bytes(b"KHAC = 1\n")
        self.assertEqual(self.chay(False, dich), 3)
        self.assertEqual((dich / "goi" / "__init__.py").read_bytes(), b"KHAC = 1\n")
        self.assertEqual(self.chay(True, dich), 3)

    def test_manifest_hoac_pin_lech_dung(self):
        dich = _tam("dich") / "review_goc"
        self.assertEqual(self.chay(False, dich, pin={"goi/__init__.py": "0" * 64}), 2)
        self.assertEqual(self.chay(False, dich, pin={"khong_co.py": "0" * 64}), 2)
        self.assertFalse(dich.exists())
        self.nguon = self._ref(sha_sai=True)  # reference khác manifest
        self.assertEqual(self.chay(False, dich, pin={}), 2)
        self.assertFalse(dich.exists())


# ===================================================================================================== M4-01B2: phản ví dụ cho sáu sửa
class CacheGhim(unittest.TestCase):
    """Sửa 2: dấu ghim khác None nhưng sai pin/origin/loader không được coi là module hợp lệ."""

    def _bo(self):
        goc = _tam("cache")
        ten = "m4ghim_" + uuid.uuid4().hex[:8]
        (goc / ten).mkdir()
        (goc / ten / "__init__.py").write_bytes(b"GIA_TRI = 1\n")
        bo = nap_ghim.BoNapGhim(goc, {f"{ten}/__init__.py": hashlib.sha256(b"GIA_TRI = 1\n").hexdigest()}, (ten,))
        spec = bo.find_spec(ten)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return bo, ten, spec, m

    def test_module_dung_hop_le(self):
        bo, ten, _, m = self._bo()
        self.assertTrue(bo.hop_le(ten, m))

    def test_dau_gia_sai_pin(self):
        bo, ten, spec, _ = self._bo()
        gia = types.ModuleType(ten)
        gia.__spec__, gia.__loader__, gia.__file__ = spec, bo, spec.origin
        setattr(gia, nap_ghim.DAU_GHIM, "0" * 64)
        self.assertFalse(bo.hop_le(ten, gia))
        with patch.dict(sys.modules, {ten: gia}):
            self.assertEqual(bo.sai_cache(), [ten])

    def test_dau_dung_pin_nhung_loader_hoac_origin_khac(self):
        bo, ten, spec, m = self._bo()
        khac_loader = types.ModuleType(ten)
        khac_loader.__dict__.update({k: v for k, v in m.__dict__.items() if k != "__loader__"})
        khac_loader.__loader__ = object()
        self.assertFalse(bo.hop_le(ten, khac_loader))
        bo2 = nap_ghim.BoNapGhim(bo.goc, bo.pin, bo.goi_goc)  # instance khác (vd cache còn từ lần nạp trước)
        self.assertFalse(bo2.hop_le(ten, m))
        noi_khac = _tam("cache_khac") / "__init__.py"
        noi_khac.write_bytes(b"GIA_TRI = 1\n")
        sai_origin = types.ModuleType(ten)
        sai_origin.__dict__.update(m.__dict__)
        sai_origin.__file__ = str(noi_khac)
        self.assertFalse(bo.hop_le(ten, sai_origin))


_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx_xml(document: str, them: dict | None = None) -> bytes:
    return F._zip({"[Content_Types].xml": F._CONTENT_TYPES, "_rels/.rels": F._RELS, "word/document.xml": document, **(them or {})})


def _doc(than: str, ns: str = _W_NS, prefix: str = "w") -> str:
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><{prefix}:document xmlns:{prefix}="{ns}"><{prefix}:body>{than}'
            f"</{prefix}:body></{prefix}:document>")


class TrackChangesNamespace(unittest.TestCase):
    """Sửa 4: nhận thẻ sửa đổi theo URI namespace, không theo chuỗi literal; không cần lõi nguồn, không Office."""

    def _chan(self, raw: bytes, ma: str):
        with _CamOffice():
            with self.assertRaises(DataError) as cm:
                NR.kiem_docx_an_toan(raw)
        self.assertEqual(cm.exception.code, ma)

    def test_prefix_khac_cung_namespace(self):
        raw = _docx_xml(_doc('<x:p><x:ins x:id="1" x:author="A"><x:r><x:t>them</x:t></x:r></x:ins></x:p>', prefix="x"))
        self._chan(raw, "M4_DOCX_CON_SUA_DOI")

    def test_xuong_dong_sau_qname(self):
        raw = _docx_xml(_doc('<w:p><w:del\nw:id="2"\nw:author="A"><w:r><w:delText>bo</w:delText></w:r></w:del></w:p>'))
        self._chan(raw, "M4_DOCX_CON_SUA_DOI")

    def test_namespace_strict_va_doi_dinh_dang(self):
        strict = "http://purl.oclc.org/ooxml/wordprocessingml/main"
        raw = _docx_xml(_doc('<w:p><w:pPr><w:pPrChange w:id="3" w:author="A"><w:pPr/></w:pPrChange></w:pPr></w:p>', ns=strict))
        self._chan(raw, "M4_DOCX_CON_SUA_DOI")

    def test_sua_doi_trong_header(self):
        header = (f'<?xml version="1.0" encoding="UTF-8"?><w:hdr xmlns:w="{_W_NS}"><w:p><w:ins w:id="4" w:author="A"><w:r><w:t>h</w:t></w:r>'
                  "</w:ins></w:p></w:hdr>")
        raw = _docx_xml(_doc("<w:p><w:r><w:t>sach</w:t></w:r></w:p>"), {"word/header1.xml": header})
        self._chan(raw, "M4_DOCX_CON_SUA_DOI")

    def test_the_ins_namespace_khac_khong_tinh(self):
        raw = _docx_xml(_doc('<w:p><o:ins xmlns:o="urn:khac"/><w:r><w:t>sach</w:t></w:r></w:p>'))
        with _CamOffice():
            NR.kiem_docx_an_toan(raw)  # không raise

    def test_fixture_sach_va_fixture_co_sua_doi(self):
        with _CamOffice():
            NR.kiem_docx_an_toan(F.hop_dong_docx())
        self._chan(F.hop_dong_docx(track_changes=True), "M4_DOCX_CON_SUA_DOI")

    def test_xml_hong_hoac_doctype_bao_khong_doc_duoc(self):
        self._chan(_docx_xml("<w:document"), "M4_DOCX_KHONG_HO_TRO")
        self._chan(_docx_xml(f'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY e "x">]><w:document xmlns:w="{_W_NS}"><w:body/></w:document>'),
                   "M4_DOCX_KHONG_HO_TRO")
        self._chan(F._zip({"[Content_Types].xml": F._CONTENT_TYPES}), "M4_DOCX_KHONG_HO_TRO")


class BoqPhanLoaiCauTruc(unittest.TestCase):
    """Sửa 3: thông điệp dựng ĐÚNG mẫu của parser nguồn (reference may_chu/nghiep_vu.py boq_doc_dong) cho từng ca thủ công."""
    TEN_GIA = "Lót móng KL × ĐG = 1 khác thành tiền 1"

    def test_ten_chua_mau_so_hoc_kl_khong_phai_so_van_chan(self):
        it = {"dong": 2, "ten": self.TEN_GIA, "kl": None, "don_gia": 50000, "thanh_tien": 999, "ma_rieng": "HM-01"}
        x = {"dong": 2, "noi_dung": f"{self.TEN_GIA}: khối lượng hoặc đơn giá không phải số — kiểm tra ánh xạ cột"}
        self.assertEqual(NR.phan_loai_loi(x, it), ("CHAN", "BOQ_SO_KHONG_DOC_DUOC"))

    def test_thong_diep_gia_so_hoc_tren_dong_khong_phai_so_van_chan(self):
        it = {"dong": 2, "ten": "X", "kl": None, "don_gia": 1, "thanh_tien": 1, "ma_rieng": None}
        self.assertEqual(NR.phan_loai_loi({"dong": 2, "noi_dung": "X: KL × ĐG = 0 khác thành tiền 1"}, it), ("CHAN", "BOQ_SO_KHONG_DOC_DUOC"))

    def test_lech_so_hoc_that_la_phat_hien(self):
        it = {"dong": 4, "ten": "Cốt thép", "kl": 10, "don_gia": 20000, "thanh_tien": 999, "ma_rieng": "HM-03"}
        x = {"dong": 4, "noi_dung": "Cốt thép: KL × ĐG = 200,000 khác thành tiền 999"}
        self.assertEqual(NR.phan_loai_loi(x, it), ("PHAT_HIEN", "BOQ_SO_HOC_LECH"))

    def test_mau_so_hoc_nhung_so_khop_la_loi_khac(self):
        it = {"dong": 3, "ten": "A", "kl": 2, "don_gia": 5, "thanh_tien": 10, "ma_rieng": None}
        self.assertEqual(NR.phan_loai_loi({"dong": 3, "noi_dung": "A: KL × ĐG = 10 khác thành tiền 10"}, it), ("CHAN", "BOQ_LOI_KHAC"))

    def test_trung_ma_va_khong_thay_dong(self):
        it = {"dong": 3, "ten": "bị trùng", "kl": 1, "don_gia": 1, "thanh_tien": 1, "ma_rieng": "HM-02"}
        self.assertEqual(NR.phan_loai_loi({"dong": 3, "noi_dung": "Mã hạng mục 'HM-02' bị trùng — mỗi hạng mục một mã riêng"}, it),
                         ("CHAN", "BOQ_MA_TRUNG"))
        self.assertEqual(NR.phan_loai_loi({"dong": 3, "noi_dung": "bị trùng"}, it), ("CHAN", "BOQ_LOI_KHAC"))
        self.assertEqual(NR.phan_loai_loi({"dong": 9, "noi_dung": "KL × ĐG"}, None), ("CHAN", "BOQ_LOI_KHAC"))

    @unittest.skipUnless(_nguon_da_nap() and openpyxl is not None, "Lõi nguồn chưa nạp hoặc thiếu openpyxl — NOT_RUN")
    def test_xlsx_that_ten_gia_va_kl_abc(self):
        p = _tam("boq_ten_gia") / "boq.xlsx"
        p.write_bytes(F.boq_xlsx(F.BOQ_TEN_GIA_LOI))
        rows, chan, phat_hien = NR.boq_doc(p, "BOQ", 1, dict(F.BOQ_COT))
        self.assertIn(("BOQ_SO_KHONG_DOC_DUOC", 2), [(c["ma"], c["dong"]) for c in chan])
        self.assertEqual([(x["ma"], x["dong"]) for x in phat_hien], [("BOQ_SO_HOC_LECH", 4)])
        hm01 = next(r for r in rows if r["ma_rieng"] == "HM-01")
        self.assertIsNone(hm01["kl"])
        self.assertEqual(hm01["o_goc"]["kl"], {"tho": "abc", "kieu": "CHU", "o": "E2"})
        self.assertEqual(hm01["o_goc"]["thanh_tien"], {"tho": "999", "kieu": "SO", "o": "G2"})


class GiuStaging(unittest.TestCase):
    """Sửa 1: write_immutable giữ mọi tệp staging (thành công/lỗi/retry); đích không bị ghi đè."""

    def test_thanh_cong_retry_loi_deu_giu(self):
        from kho_tri_thuc.ha_tang.store import STAGING_DIR, write_immutable
        d = _tam("staging")
        dich = d / "abc.bin"
        write_immutable(dich, b"mot")
        st = d / STAGING_DIR
        self.assertEqual(dich.read_bytes(), b"mot")
        self.assertEqual(sorted(p.read_bytes() for p in st.iterdir()), [b"mot"])
        write_immutable(dich, b"mot")  # retry cùng bytes
        self.assertEqual(sorted(p.read_bytes() for p in st.iterdir()), [b"mot", b"mot"])
        with self.assertRaises(DataError) as cm:
            write_immutable(dich, b"hai")
        self.assertEqual(cm.exception.code, "ARTIFACT_CHANGED")
        self.assertEqual(dich.read_bytes(), b"mot")
        self.assertEqual(sorted(p.read_bytes() for p in st.iterdir()), [b"hai", b"mot", b"mot"])

    def test_ban_lam_viec_giu_staging(self):
        from kho_tri_thuc.ha_tang.store import STAGING_DIR
        d = _tam("lam_viec")
        raw = F.hop_dong_docx()
        p = NR.ban_lam_viec(raw, d, ".docx")
        self.assertEqual(p.read_bytes(), raw)
        self.assertEqual([x.read_bytes() for x in (d / STAGING_DIR).iterdir()], [raw])


class TinhB2Sql(unittest.TestCase):
    sql = "\n".join(S.M0017_M4)

    def test_tep_da_nop_kiem_pham_vi(self):
        than = _ham(self.sql, "m4.tep_da_nop")
        self.assertIn("master.m4_duoc(f.du_an_id, 'XEM')", than)
        self.assertIn("master.m4_duoc(f.du_an_id, 'REVIEW')", than)

    def test_final_boq_co_mang_day_du(self):
        than = _ham(self.sql, "m4.ghi_boq")
        self.assertIn("'loi_chan', p_loi_chan", than)
        self.assertIn("'phat_hien', p_phat_hien", than)
        self.assertLess(than.index("'loi_chan', p_loi_chan"), than.index("m4._bn_ghi("))


class SeedMaTran(unittest.TestCase):
    def test_actor_mo_phong_va_reviewer_khong_soan(self):
        from kho_tri_thuc.k2 import m4_demo
        for dang_nhap, vai_tro, _, du_an_vai in m4_demo.NGUOI_DUNG:
            self.assertTrue(dang_nhap.startswith("MO_PHONG_"))
            if any(v == "REVIEW" for _, v in du_an_vai):
                self.assertFalse(any(v == "PHU_TRACH" for _, v in du_an_vai), dang_nhap)
                self.assertNotEqual(vai_tro, "DU_AN", dang_nhap)


if __name__ == "__main__":
    unittest.main()
