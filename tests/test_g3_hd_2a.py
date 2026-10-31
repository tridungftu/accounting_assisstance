"""HD-2a: toàn bộ portal/Core giả, dữ liệu DEMO trong RAM."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import io
import unittest
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

from kho_tri_thuc.engines.e_hoa_don import doc, tai
from kho_tri_thuc.ha_tang.engine import TrangThaiEngine
from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.nguon import hoa_don_xml as parser
from test_g3_hd_1 import CTX, RAW


def tep(raw=RAW, context=CTX):
    if context is not None:
        context = replace(context, expected_raw_ref=parser.XmlRawRef(sha256(raw), len(raw)))
    return tai.TepTai(raw, context)


class PortalStub:
    def __init__(self, *, nhom=("DEMO_A", "DEMO_B"), outcomes=None, login=True):
        self.nhom = nhom
        self.outcomes = outcomes or {}
        self.login = login
        self.calls = []
        self.phien_login = []
        self.huong_nhom = []

    def nhom_truy_van(self, huong):
        self.huong_nhom.append(huong)
        return self.nhom

    def da_dang_nhap(self, phien):
        self.phien_login.append(phien)
        return self.login

    def tai_nhom(self, phien, ky, huong, nhom):
        self.calls.append((phien, ky, huong, nhom))
        value = self.outcomes.get((ky.nam, ky.thang, nhom), tai.NhomTai((tep(),)))
        if isinstance(value, BaseException):
            raise value
        return value


class CoreStub:
    """Biên nhận giả gắn phạm vi phiên; lưu đủ bộ tệp trước ACK."""
    def __init__(self, *sessions):
        self.allowed = {s.phien for s in sessions}
        self.refs = {}
        self.receipts = {}
        self.summaries = {}
        self.nhan_calls = 0
        self.summary_calls = 0
        self.ack_tep = True
        self.ack_phien = True
        self.mat_ack_tep = False
        self.mat_ack_phien = False
        self.mat_ref = False

    def _kiem(self, phien):
        if phien not in self.allowed:
            raise PermissionError("Phiên chưa được Core cấp")

    def cap_tham_chieu(self, phien, khoa):
        self._kiem(phien)
        key = (phien, khoa)
        if key not in self.refs:
            base = f"DEMO/{phien.phap_nhan_id}/{phien.phien_id}/{khoa}"
            self.refs[key] = tai.ThamChieu(str(uuid5(NAMESPACE_URL, base + "/xml")),
                                          str(uuid5(NAMESPACE_URL, base + "/detail")))
        if self.mat_ref:
            self.mat_ref = False
            raise ConnectionError("Mất phản hồi cấp tham chiếu DEMO")
        return self.refs[key]

    def nhan_hoa_don(self, phien, khoa, ket_qua):
        self._kiem(phien)
        self.nhan_calls += 1
        if not self.ack_tep:
            return False
        key = (phien, khoa)
        raw = ket_qua.chi_tiet_nguon.raw_xml
        assert sha256(raw) == khoa
        saved = (raw, parser.ra_json(ket_qua.chi_tiet_nguon), ket_qua.hoa_don)
        if key in self.receipts:
            assert self.receipts[key] == saved
        else:
            self.receipts[key] = saved
        if self.mat_ack_tep:
            self.mat_ack_tep = False
            raise ConnectionError("Đã commit DEMO, mất ACK")
        return True

    def nhan_phien(self, phien, coverage, ket_luan):
        self._kiem(phien)
        self.summary_calls += 1
        if not self.ack_phien:
            return False
        value = (coverage, ket_luan)
        if phien in self.summaries:
            assert self.summaries[phien] == value
        self.summaries[phien] = value
        if self.mat_ack_phien:
            self.mat_ack_phien = False
            raise ConnectionError("Đã lưu coverage DEMO, mất ACK")
        return True


def session(portal=None, **kwargs):
    args = dict(phap_nhan_id="PN_DEMO", nguon_id="NGUON_DEMO",
                tu_ngay="2024-02-01", den_ngay="2024-02-29", huong="mua_vao",
                portal=portal if portal is not None else PortalStub())
    args.update(kwargs)
    return tai.TaiHoaDonGia(**args)


class KyTests(unittest.TestCase):
    def test_thang_nhuan_thuong_va_nam_the_ky(self):
        for nam, day in ((2024, 29), (2025, 28), (2000, 29), (2100, 28)):
            with self.subTest(nam=nam):
                periods = tai.chia_ky(f"{nam}-02-01", f"{nam}-02-{day}")
                self.assertEqual(periods, (tai.KyThang(nam, 2),))
                self.assertEqual(periods[0].tu_ngay, f"{nam}-02-01")
                self.assertEqual(periods[0].den_ngay, f"{nam}-02-{day}")

    def test_doi_nam_khong_mat_thang(self):
        periods = tai.chia_ky("2023-12-01", "2024-03-31")
        self.assertEqual([(k.nam, k.thang) for k in periods],
                         [(2023, 12), (2024, 1), (2024, 2), (2024, 3)])
        self.assertEqual(periods[2].den_ngay, "2024-02-29")
        self.assertEqual(tai.chia_ky("9999-12-01", "9999-12-31"),
                         (tai.KyThang(9999, 12),))

    def test_tu_choi_ky_le_ngay_sai_va_dao_nguoc_truoc_goi_portal(self):
        cases = (("2024-02-02", "2024-02-29"), ("2024-02-01", "2024-02-28"),
                 ("2024-02-01", "2024-03-30"), ("2024-03-01", "2024-02-29"),
                 ("2023-02-01", "2023-02-29"), ("2024-2-01", "2024-02-29"),
                 (None, "2024-02-29"), ("2024-02-01", None))
        for dau, cuoi in cases:
            with self.subTest(dau=dau, cuoi=cuoi):
                portal = PortalStub()
                with self.assertRaises(DataError):
                    session(portal, tu_ngay=dau, den_ngay=cuoi)
                self.assertEqual(portal.huong_nhom, [])
                self.assertEqual(portal.calls, [])

    def test_anh_xa_tung_thang_va_huong_tuong_ung_portal(self):
        for huong in ("mua_vao", "ban_ra"):
            with self.subTest(huong=huong):
                portal = PortalStub(nhom=("DEMO_A",))
                s = session(portal, tu_ngay="2023-12-01", den_ngay="2024-02-29", huong=huong)
                s.tiep_tuc()
                self.assertEqual([(k.nam, k.thang, h) for _, k, h, _ in portal.calls],
                                 [(2023, 12, huong), (2024, 1, huong), (2024, 2, huong)])


class TaiTests(unittest.TestCase):
    def test_cho_dang_nhap_gia_khong_tai_som(self):
        portal = PortalStub(login=False)
        s = session(portal)
        for _ in range(3):
            progress = s.tiep_tuc()
            self.assertEqual(progress.trang_thai_viec, "waiting_input")
            self.assertIsNone(progress.ket_luan_tai)
            self.assertEqual(progress.coverage, ())
        self.assertEqual(portal.calls, [])
        portal.login = True
        progress = s.tiep_tuc()
        self.assertEqual(progress.trang_thai_viec, "running")
        self.assertEqual(progress.ket_luan_tai, "COMPLETE")
        self.assertFalse(progress.da_ack_phien)
        self.assertTrue(all(p == s.phien for p in portal.phien_login))

    def test_tu_choi_huong_va_nguon_rong(self):
        for kwargs in ({"huong": "purchase"}, {"huong": None}, {"nguon_id": ""},
                       {"phap_nhan_id": " "}):
            with self.subTest(kwargs=kwargs), self.assertRaises(DataError):
                session(**kwargs)

    def test_thieu_coverage_khong_duoc_tu_suy_thanh_cong(self):
        for groups in ((), ["DEMO_A"], ("DEMO_A", "DEMO_A"), ("",), (1,)):
            with self.subTest(groups=groups), self.assertRaises(DataError) as cm:
                session(PortalStub(nhom=groups))
            self.assertEqual(cm.exception.code, "HOADON_COVERAGE_THIEU")

    def test_loi_nhom_partial_giu_tep_va_coverage_day_du(self):
        portal = PortalStub(outcomes={(2024, 2, "DEMO_B"): RuntimeError("DEMO_TOKEN")})
        s = session(portal)
        progress = s.tiep_tuc()
        self.assertEqual(progress.ket_luan_tai, "PARTIAL")
        self.assertEqual(progress.so_tep_duy_nhat, 1)
        self.assertEqual([(c.nhom, c.trang_thai, c.so_tep_nhan) for c in progress.coverage],
                         [("DEMO_A", "COMPLETE", 1), ("DEMO_B", "FAILED", 0)])
        self.assertNotIn("DEMO_TOKEN", repr(progress))
        core = CoreStub(s)
        final = s.ban_giao(core)
        self.assertEqual(final.trang_thai_viec, "failed")
        self.assertEqual(len(core.receipts), 1)
        self.assertEqual(core.summaries[s.phien], (progress.coverage, "PARTIAL"))

    def test_nhom_tai_do_van_giu_tep_da_nhan(self):
        s = session(PortalStub(outcomes={
            (2024, 2, "DEMO_B"): tai.NhomTai((tep(RAW + b"\n"),), day_du=False)}))
        progress = s.tiep_tuc()
        self.assertEqual(progress.ket_luan_tai, "PARTIAL")
        self.assertEqual(progress.so_tep_duy_nhat, 2)
        self.assertEqual(progress.coverage[1].trang_thai, "PARTIAL")
        core = CoreStub(s)
        self.assertTrue(s.ban_giao(core).da_ack_phien)
        self.assertEqual(len(core.receipts), 2)

    def test_ngat_giua_phien_khong_tu_tai_lai_hoac_bao_xong(self):
        portal = PortalStub(outcomes={(2024, 2, "DEMO_B"): KeyboardInterrupt()})
        s = session(portal)
        with self.assertRaises(KeyboardInterrupt):
            s.tiep_tuc()
        for _ in range(2):
            progress = s.tiep_tuc()
            self.assertEqual(progress.trang_thai_viec, "interrupted")
            self.assertIsNone(progress.ket_luan_tai)
            self.assertFalse(progress.da_ack_phien)
            self.assertEqual(progress.so_tep_duy_nhat, 1)
        self.assertEqual(len(portal.calls), 2)
        with self.assertRaises(DataError):
            s.ban_giao(CoreStub(s))

    def test_khong_co_hoa_don_khac_voi_khong_truy_van_duoc(self):
        for value, ket_luan in ((tai.NhomTai(), "COMPLETE"), (RuntimeError(), "PARTIAL")):
            with self.subTest(value=value):
                s = session(PortalStub(nhom=("DEMO_A",), outcomes={(2024, 2, "DEMO_A"): value}))
                core = CoreStub(s)
                progress = s.tiep_tuc()
                self.assertEqual(progress.ket_luan_tai, ket_luan)
                final = s.ban_giao(core)
                self.assertTrue(final.da_ack_phien)
                self.assertEqual(final.so_tep_duy_nhat, 0)
                self.assertEqual(len(core.summaries), 1)

    def test_ket_qua_nhom_sai_kieu_khong_duoc_bao_day_du(self):
        for value in (None, {}, tai.NhomTai(day_du=1), tai.NhomTai([tep()]),
                      tai.NhomTai((tai.TepTai("DEMO"),))):
            with self.subTest(value=value):
                s = session(PortalStub(nhom=("DEMO_A",), outcomes={(2024, 2, "DEMO_A"): value}))
                progress = s.tiep_tuc()
                self.assertEqual(progress.ket_luan_tai, "PARTIAL")
                self.assertEqual(progress.coverage[0].ma_loi, "HOADON_NHOM_SAI_DINH_DANG")

    def test_dedupe_trong_nhom_giua_nhom_va_giua_thang(self):
        portal = PortalStub(outcomes={(2024, 2, "DEMO_A"): tai.NhomTai((tep(), tep()))})
        s = session(portal, tu_ngay="2024-01-01", den_ngay="2024-02-29")
        progress = s.tiep_tuc()
        self.assertEqual(sum(c.so_tep_nhan for c in progress.coverage), 5)
        self.assertEqual(progress.so_tep_duy_nhat, 1)
        self.assertEqual(len(portal.calls), 4)
        core = CoreStub(s)
        final = s.ban_giao(core)
        self.assertEqual(final.so_tep_da_ack, 1)
        self.assertEqual(len(core.receipts), 1)
        for _ in range(3):
            self.assertEqual(s.tiep_tuc(), final)
            self.assertEqual(s.ban_giao(core), final)
        self.assertEqual(len(portal.calls), 4)
        self.assertEqual(core.nhan_calls, 1)

    def test_cung_dinh_danh_nhung_khac_noi_dung_khong_mat_ban_nguon(self):
        raw2 = RAW.replace(b"100.010000", b"200.010000")
        s = session(PortalStub(outcomes={(2024, 2, "DEMO_B"): tai.NhomTai((tep(raw2),))}))
        s.tiep_tuc()
        core = CoreStub(s)
        s.ban_giao(core)
        values = list(core.receipts.values())
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0][2]["dinh_danh_nguon"], values[1][2]["dinh_danh_nguon"])
        self.assertNotEqual(values[0][2]["ma_bam_noi_dung"], values[1][2]["ma_bam_noi_dung"])

    def test_profile_rieng_cho_hai_phap_nhan_va_hai_phien_cung_phap_nhan(self):
        portal = PortalStub()
        sessions = (session(portal), session(portal), session(portal, phap_nhan_id="PN_DEMO_2"))
        core = CoreStub(*sessions)
        for s in sessions:
            s.tiep_tuc()
            s.ban_giao(core)
        self.assertEqual(len({s.phien.profile_id for s in sessions}), 3)
        self.assertEqual(len({s.phien.phien_id for s in sessions}), 3)
        self.assertEqual(len(core.receipts), 3)
        self.assertEqual(len({ref.tep_xml_id for ref in core.refs.values()}), 3)
        # Cùng bytes không được dùng biên nhận của pháp nhân/phiên khác.
        self.assertEqual({p for p, _, _, _ in portal.calls}, {s.phien for s in sessions})


class BanGiaoTests(unittest.TestCase):
    def test_dung_doc_hd1_giu_decimal_id_hash_va_chi_tiet_nguon(self):
        s = session()
        s.tiep_tuc()
        core = CoreStub(s)
        with patch.object(doc, "doc_xml", wraps=doc.doc_xml) as read:
            final = s.ban_giao(core)
        read.assert_called_once()
        self.assertEqual(final.trang_thai_viec, "succeeded")
        raw, detail, invoice = next(iter(core.receipts.values()))
        self.assertEqual(raw, RAW)
        self.assertEqual(detail, parser.ra_json(parser.doc_hoa_don_xml(RAW, CTX)))
        self.assertEqual(invoice["dau_hoa_don"]["so_hoa_don"], "000001")
        self.assertEqual(invoice["dong"][0]["tien_chuan"]["gia_tri"], "100.010000")
        ref = next(iter(core.refs.values()))
        self.assertEqual(invoice["tep_xml_id"], ref.tep_xml_id)
        self.assertEqual(invoice["chi_tiet_nguon_tep_id"], ref.chi_tiet_nguon_tep_id)
        self.assertNotEqual(ref.tep_xml_id, ref.chi_tiet_nguon_tep_id)
        self.assertEqual(invoice["ghi_nhan_nghiep_vu"], "NOT_PERFORMED")

    def test_chua_ack_giu_ket_qua_khong_tai_lai(self):
        portal = PortalStub()
        s = session(portal)
        s.tiep_tuc()
        core = CoreStub(s)
        core.ack_tep = False
        with patch.object(doc, "doc_xml", wraps=doc.doc_xml) as read:
            for _ in range(2):
                progress = s.ban_giao(core)
                self.assertEqual(progress.trang_thai_viec, "running")
                self.assertEqual(progress.so_tep_da_ack, 0)
                self.assertFalse(progress.da_ack_phien)
            core.ack_tep = True
            self.assertTrue(s.ban_giao(core).da_ack_phien)
            read.assert_called_once()
        self.assertEqual(core.summary_calls, 1)
        self.assertEqual(len(portal.calls), 2)

    def test_mat_ack_sau_commit_gui_lai_khong_nhan_doi_tep(self):
        portal = PortalStub()
        s = session(portal)
        s.tiep_tuc()
        core = CoreStub(s)
        core.mat_ack_tep = True
        with patch.object(doc, "doc_xml", wraps=doc.doc_xml) as read:
            with self.assertRaises(ConnectionError):
                s.ban_giao(core)
            self.assertEqual(len(core.receipts), 1)
            self.assertEqual(s.tiep_tuc().so_tep_da_ack, 0)
            final = s.ban_giao(core)
            read.assert_called_once()
        self.assertTrue(final.da_ack_phien)
        self.assertEqual(len(core.receipts), 1)
        self.assertEqual(core.nhan_calls, 2)
        self.assertEqual(len(portal.calls), 2)

    def test_mat_phan_hoi_cap_id_dung_lai_id_cu(self):
        s = session()
        s.tiep_tuc()
        core = CoreStub(s)
        core.mat_ref = True
        with self.assertRaises(ConnectionError):
            s.ban_giao(core)
        refs = dict(core.refs)
        self.assertTrue(s.ban_giao(core).da_ack_phien)
        self.assertEqual(core.refs, refs)

    def test_mat_ack_tep_sau_khong_gui_lai_tep_da_ack_truoc(self):
        raw2 = RAW.replace(b"100.010000", b"200.010000")
        portal = PortalStub(outcomes={(2024, 2, "DEMO_B"): tai.NhomTai((tep(raw2),))})
        s = session(portal)
        s.tiep_tuc()
        core = CoreStub(s)
        receive = core.nhan_hoa_don

        def mat_ack_thu_hai(phien, khoa, ket_qua):
            core.mat_ack_tep = ket_qua.chi_tiet_nguon.raw_xml == raw2
            return receive(phien, khoa, ket_qua)

        with patch.object(core, "nhan_hoa_don", side_effect=mat_ack_thu_hai):
            with self.assertRaises(ConnectionError):
                s.ban_giao(core)
        self.assertEqual(s.tiep_tuc().so_tep_da_ack, 1)
        self.assertEqual(len(core.receipts), 2)
        self.assertTrue(s.ban_giao(core).da_ack_phien)
        self.assertEqual(core.nhan_calls, 3)
        self.assertEqual(len(portal.calls), 2)

    def test_ack_coverage_la_buoc_rieng_ke_ca_khong_co_tep(self):
        for empty in (False, True):
            with self.subTest(empty=empty):
                portal = PortalStub(nhom=("DEMO_A",), outcomes={
                    (2024, 2, "DEMO_A"): tai.NhomTai() if empty else tai.NhomTai((tep(),))})
                s = session(portal)
                s.tiep_tuc()
                core = CoreStub(s)
                core.ack_phien = False
                progress = s.ban_giao(core)
                self.assertFalse(progress.da_ack_phien)
                self.assertEqual(progress.trang_thai_viec, "running")
                n = core.nhan_calls
                core.ack_phien = True
                core.mat_ack_phien = True
                with self.assertRaises(ConnectionError):
                    s.ban_giao(core)
                self.assertTrue(s.ban_giao(core).da_ack_phien)
                self.assertEqual(len(core.summaries), 1)
                self.assertEqual(core.nhan_calls, n)

    def test_xml_loi_context_thieu_khong_bien_thanh_doc_thanh_cong(self):
        for item, state in ((tep(b"<HDon>DEMO", None), TrangThaiEngine.LOI),
                            (tep(context=None), TrangThaiEngine.CHO)):
            with self.subTest(state=state):
                s = session(PortalStub(nhom=("DEMO_A",), outcomes={
                    (2024, 2, "DEMO_A"): tai.NhomTai((item,))}))
                s.tiep_tuc()
                core = CoreStub(s)
                with patch.object(core, "nhan_hoa_don", wraps=core.nhan_hoa_don) as receive:
                    final = s.ban_giao(core)
                parsed = receive.call_args.args[2]
                self.assertEqual(parsed.trang_thai, state)
                self.assertEqual(final.ket_luan_tai, "COMPLETE")
                self.assertEqual(parsed.chi_tiet_nguon.raw_xml, item.raw)

    def test_core_tu_choi_phien_khac_khong_danh_dau_ack(self):
        s = session()
        s.tiep_tuc()
        with self.assertRaises(PermissionError):
            s.ban_giao(CoreStub(session(phap_nhan_id="PN_DEMO_2")))
        progress = s.tiep_tuc()
        self.assertEqual(progress.so_tep_da_ack, 0)
        self.assertFalse(progress.da_ack_phien)

    def test_chua_tai_hoac_dang_cho_khong_duoc_ban_giao(self):
        s = session(PortalStub(login=False))
        for _ in range(2):
            with self.assertRaises(DataError) as cm:
                s.ban_giao(CoreStub(s))
            self.assertEqual(cm.exception.code, "HOADON_CHUA_TAI")
            s.tiep_tuc()

    def test_goi_dong_thoi_khong_nhan_doi_truy_van_va_ban_giao(self):
        portal = PortalStub()
        s = session(portal)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: s.tiep_tuc(), range(4)))
        core = CoreStub(s)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: s.ban_giao(core), range(4)))
        self.assertTrue(all(r.da_ack_phien for r in results))
        self.assertEqual(len(portal.calls), 2)
        self.assertEqual(core.nhan_calls, 1)
        self.assertEqual(core.summary_calls, 1)

    def test_khong_io_mang_tien_trinh_moi_truong_hoac_mat_khau(self):
        s = session()
        core = CoreStub(s)
        with (patch("builtins.open", side_effect=AssertionError("Đọc tệp")),
              patch("io.open", side_effect=AssertionError("Đọc tệp")),
              patch("socket.socket", side_effect=AssertionError("Mạng")),
              patch("subprocess.Popen", side_effect=AssertionError("Tiến trình")),
              patch("os.getenv", side_effect=AssertionError("Môi trường")),
              patch("sys.stdout", new_callable=io.StringIO) as stdout,
              patch("sys.stderr", new_callable=io.StringIO) as stderr):
            s.tiep_tuc()
            self.assertTrue(s.ban_giao(core).da_ack_phien)
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")
        self.assertNotIn("HDon", repr(tep()))


if __name__ == "__main__":
    unittest.main()
