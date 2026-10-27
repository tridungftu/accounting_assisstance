"""XS-5a1: kiểm metadata/ngoại lệ bằng dữ liệu giả, không DB/server/file tạm.

Chạy: PYTHONPATH=src python -B -X utf8 -m unittest discover -s tests
      -p test_xs5_khai_bao.py -v
Không cần KHO_PG_DSN_TEST; không xóa/ghi tệp, dùng được dưới guard giữ tệp.
Đây chưa phải trace SQL thực của XS-5c hay kiểm quyền PostgreSQL XS-5b.
"""

from collections import Counter
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import re
import unittest

from kho_tri_thuc.ha_tang.khai_bao_module import (
    BangChuaRo, ChuTheoDong, DiemTruyCapDuLieu, DuLieuCongBo,
    KhaiBaoModule, KhaiBaoVungDuLieu, chu_bang, kiem_tra_vung_du_lieu,
    ve_khai_bao_crm,
)
from kho_tri_thuc.k2.vung_du_lieu import (
    CAC_VUNG_DU_LIEU, CHUA_RO, DIEM_CHEO_DANG_TON_TAI,
    kiem_tra_khai_bao, tra_chu_bang, tra_ten_nghiep_vu,
)


def diem_gia(**doi):
    return DiemTruyCapDuLieu(**{
        "module": "CRM", "tep": "k2/gia.py", "dong": 10,
        "dich": "master.hop_dong", "muc": "GHI", **doi,
    })


def vung_gia(**doi):
    return KhaiBaoVungDuLieu(**{"ma": "GIA", "ten_nghiep_vu": "Nghiệp vụ giả", **doi})


class KiemTraVungTests(unittest.TestCase):
    def test_hien_co_hop_le_nhung_khong_giau_canh_bao(self):
        kq = kiem_tra_khai_bao()
        self.assertTrue(kq.hop_le, kq.loi)
        self.assertEqual(kq.loi, ())
        self.assertEqual(sum(v.ma == "DANG_TON_TAI" for v in kq.canh_bao), len(DIEM_CHEO_DANG_TON_TAI))
        self.assertEqual(sum(v.ma == "CHUA_RO" for v in kq.canh_bao), len(CHUA_RO))

    def test_trung_chu_bang_do(self):
        kq = kiem_tra_vung_du_lieu(CAC_VUNG_DU_LIEU + (vung_gia(v1=("master.hop_dong",)),), chua_ro=CHUA_RO)
        self.assertFalse(kq.hop_le)
        self.assertIn("TRUNG_CHU", {v.ma for v in kq.loi})
        with self.assertRaisesRegex(ValueError, "đúng một chủ"):
            chu_bang("master.hop_dong", (vung_gia(v1=("master.hop_dong",)),
                                      vung_gia(ma="GIA2", v1=("master.hop_dong",))))

    def test_schema_ho_bang_va_bang_cu_the_khong_duoc_chong_chu(self):
        for a, b in (("m4.*", "m4.dot"), ("m4.*", "m4.*"),
                     ("master.module_*", "master.module_cong_*"),
                     ("master.module_*", "master.module_danh_muc")):
            with self.subTest(a=a, b=b):
                kq = kiem_tra_vung_du_lieu((vung_gia(v1=(a,)), vung_gia(ma="GIA2", v1=(b,))))
                self.assertFalse(kq.hop_le)
                self.assertIn("TRUNG_CHU", {v.ma for v in kq.loi})

    def test_ho_khong_khop_ten_gan_giong(self):
        cac_vung = (vung_gia(v1=("master.module_*",)), vung_gia(ma="GIA2", v1=("master.modulex",)))
        self.assertTrue(kiem_tra_vung_du_lieu(cac_vung).hop_le)
        self.assertEqual(chu_bang("master.module_cong_tac", cac_vung), "GIA")
        self.assertEqual(chu_bang("master.modulex", cac_vung), "GIA2")

    def test_trung_module_do(self):
        kq = kiem_tra_vung_du_lieu((vung_gia(), vung_gia()))
        self.assertIn("TRUNG_MODULE", {v.ma for v in kq.loi})

    def test_ghi_cheo_moi_do_du_v3_cho_doc(self):
        # master.hop_dong đã là V3 của M4, không biến thành quyền UPDATE.
        for module, bang in (("M4", "master.hop_dong"), ("M2", "master.phap_nhan"),
                             ("CRM", "m4.dot"), ("M9", "kho.chung_tu"), ("M0", "nhat_ky.su_kien")):
            with self.subTest(module=module, bang=bang):
                kq = kiem_tra_khai_bao((diem_gia(module=module, dich=bang),))
                self.assertEqual([v.ma for v in kq.loi], ["GHI_CHEO_MOI"])

    def test_ghi_rieng_khong_do(self):
        for module, bang in (("CRM", "master.crm_mau"), ("M4", "m4.dot"),
                             ("M0", "master.hop_dong"), ("XUONG_SONG", "bus.su_kien")):
            with self.subTest(module=module):
                self.assertTrue(kiem_tra_khai_bao((diem_gia(module=module, dich=bang),)).hop_le)

    def test_ton_tai_chi_canh_bao_va_khong_dem_lap(self):
        kq = kiem_tra_khai_bao(DIEM_CHEO_DANG_TON_TAI)
        self.assertTrue(kq.hop_le)
        cac_diem = [v.diem.khoa for v in kq.canh_bao if v.ma == "DANG_TON_TAI"]
        self.assertEqual(len(cac_diem), len(set(cac_diem)))
        self.assertEqual(len(cac_diem), len(DIEM_CHEO_DANG_TON_TAI))

    def test_ngoai_le_khong_mo_rong_module_tep_dong_bang_hoac_muc(self):
        cu = next(d for d in DIEM_CHEO_DANG_TON_TAI if d.nhom == "M4_M0")
        for doi in ({"module": "CRM"}, {"tep": "m4/gia.py"}, {"dong": cu.dong + 1}, {"dich": "master.du_an"}):
            with self.subTest(doi=doi):
                self.assertEqual([v.ma for v in kiem_tra_khai_bao((replace(cu, **doi),)).loi], ["GHI_CHEO_MOI"])
        doc_cu = next(d for d in DIEM_CHEO_DANG_TON_TAI if d.nhom == "CRM_M1")
        self.assertEqual([v.ma for v in kiem_tra_khai_bao((replace(doc_cu, muc="GHI"),)).loi], ["GHI_CHEO_MOI"])

    def test_thieu_chu_do_va_chua_ro_co_ly_do_chi_canh_bao(self):
        self.assertFalse(kiem_tra_khai_bao((diem_gia(dich="kho.bang_chua_khai"),)).hop_le)
        kq = kiem_tra_khai_bao((diem_gia(dich="giao_tiep.stage_tin_cay"),))
        self.assertTrue(kq.hop_le)
        self.assertTrue(any(v.ma == "CHUA_RO" and v.diem for v in kq.canh_bao))
        with self.assertRaises(ValueError):
            BangChuaRo("kho.gia", " ")

    def test_trung_chua_ro_va_chu_da_biet_do(self):
        kq = kiem_tra_vung_du_lieu((vung_gia(v1=("kho.gia",)),), chua_ro=(BangChuaRo("kho.gia", "Chờ lead."),))
        self.assertIn("TRUNG_CHU", {v.ma for v in kq.loi})

    def test_v3_thieu_chu_va_chu_dong_sai_do(self):
        self.assertFalse(kiem_tra_vung_du_lieu((vung_gia(v3=("master.gia",)),)).hop_le)
        cac_vung = (vung_gia(v1=("master.gia",)), vung_gia(ma="GIA2", chu_theo_dong=(
            ChuTheoDong("master.gia", ("loai",), "CRM", "loai = 'GIA'"),)))
        self.assertIn("CHU_DONG_SAI", {v.ma for v in kiem_tra_vung_du_lieu(cac_vung).loi})

    def test_trung_diem_ton_tai_do(self):
        d = diem_gia(module="GIA", dich="kho.gia")
        kq = kiem_tra_vung_du_lieu((vung_gia(v1=("kho.gia",), dang_ton_tai=(d, d)),))
        self.assertIn("TRUNG_DIEM", {v.ma for v in kq.loi})


class BanKhaiHienCoTests(unittest.TestCase):
    def test_ten_sau_module_va_fallback(self):
        ten = {
            "CRM": "Hợp đồng & báo giá", "M2": "Hóa đơn mua vào",
            "M3": "Hóa đơn bán ra & doanh thu BĐS", "M4": "Nghiệm thu & chi phí dự án",
            "M9": "Vốn vay & đầu tư tài chính", "M0": "Lõi",
        }
        for ma, mong_doi in ten.items():
            with self.subTest(ma=ma):
                self.assertEqual(tra_ten_nghiep_vu(ma), mong_doi)
        self.assertEqual(tra_ten_nghiep_vu("CHUA_KHAI"), "dữ liệu từ chức năng nguồn")

    def test_so_bang_rieng_khop_kk_m0_nhan_hop_dong_chung(self):
        cac_vung = {v.ma: v for v in CAC_VUNG_DU_LIEU}
        for ma, so in {"CRM": 46, "M2": 7, "M3": 3, "M4": 56, "M9": 8}.items():
            self.assertEqual(len(cac_vung[ma].v1), so, ma)
        for bang in ("master.hop_dong", "master.hop_dong_phien_ban", "master.hop_dong_tham_so", "master.lich_thu",
                     "kho.chung_tu", "kho.chung_tu_dong", "kho.cong_no_mo", "kho.tep_goc", "kho.viec_can_duyet",
                     "kho.lien_ket_chung_tu", "kho.lo_xuat", "kho.lo_xuat_dong", "kho.bien_nhan_thao_tac",
                     "kho.lien_ket_phan_bo", "kho.dich_phan_bo_tien", "master.phap_nhan", "master.du_an"):
            with self.subTest(bang=bang):
                self.assertEqual(tra_chu_bang(bang), "M0")
        with self.assertRaises(ValueError):
            tra_chu_bang("kho.bang_khong_co_trong_kiem_ke")

    def test_xuong_song_la_chu_rieng_va_chua_ro_khong_tu_gan(self):
        for bang in ("bus.su_kien", "bus.inbox", "viec.viec", "master.module_cong_tac", "master.mtq_phong",
                     "nhat_ky.su_kien", "nhat_ky.cong_ai_goi", "bao_mat.mask_bi_danh"):
            self.assertEqual(tra_chu_bang(bang), "XUONG_SONG", bang)
        for bang in ("kho.mua_doi_chieu_can_cu", "kho.lien_ket_dong", "giao_tiep.tep_tach_phap_nhan",
                     "knowledge_epoch", "knowledge_workbooks", "artifacts"):
            self.assertEqual(tra_chu_bang(bang), "CHUA_RO", bang)
        xs = next(v for v in CAC_VUNG_DU_LIEU if v.ma == "XUONG_SONG")
        self.assertEqual(set(xs.cong_ho_tro), {"cổng AI", "cổng OCR"})

    def test_chu_theo_dong_chi_metadata_khong_mien_ghi_cheo(self):
        m0 = next(v for v in CAC_VUNG_DU_LIEU if v.ma == "M0")
        qd03 = {q.module: q.dieu_kien for q in m0.chu_theo_dong if q.bang == "master.hop_dong"}
        self.assertEqual(qd03, {"CRM": "module_chu IS NULL AND loai NOT IN ('VAY','MUA')",
                               "M9": "loai = 'VAY'", "M4": "module_chu = 'M4'"})
        self.assertFalse(kiem_tra_khai_bao((diem_gia(module="M9"),)).hop_le)

    def test_v2_la_ham_v4_chua_gia_ten_cong_bo(self):
        m4 = next(v for v in CAC_VUNG_DU_LIEU if v.ma == "M4")
        self.assertIn("kho.dc_luu", m4.v2)
        self.assertNotIn("master.hop_dong", m4.v2)
        self.assertTrue(all(d.loai == "CHUA_CO" and d.doi_tuong is None for v in CAC_VUNG_DU_LIEU for d in v.v4))
        for v in CAC_VUNG_DU_LIEU:
            if v.ma in {"CRM", "M2", "M3", "M4", "M9", "M0"}:
                self.assertTrue(v.v2_can_bo_sung, v.ma)

    def test_dem_doc_70_va_ghi_rieng_khop_kk_muc_3(self):
        duong = Path(__file__).resolve().parents[1] / "docs/46-chuyen-doi-dieu-phoi/KK-VUNG-DU-LIEU.md"
        muc3 = duong.read_text(encoding="utf-8").split("## 3.", 1)[1].split("## 4.", 1)[0]
        hang = {
            "CRM → M1;": ("CRM_M1", "DOC"), "M3 → CRM/M2;": ("M3_CRM_M2", "DOC"),
            "M9 → M1;": ("M9_M1", "DOC"), "K2 đối chiếu → M4;": ("K2_M4", "DOC"),
            "K2 đối chiếu → M2;": ("K2_M2", "DOC"), "M4 → M0;": ("M4_M0", "GHI"),
            "CRM → vùng chung;": ("CRM_CHUNG", "GHI"), "M9 → vùng chung;": ("M9_CHUNG", "GHI"),
        }
        so_doc = 0
        for nhan, (nhom, muc) in hang.items():
            dong = next(d for d in muc3.splitlines() if d.startswith("| " + nhan))
            so = int(re.search(r"\*\*(\d+)", dong).group(1))
            cac_diem = [d for d in DIEM_CHEO_DANG_TON_TAI if d.nhom == nhom]
            self.assertEqual(len(cac_diem), so, nhan)
            self.assertEqual({d.muc for d in cac_diem}, {muc})
            so_doc += so if muc == "DOC" else 0
        self.assertEqual(so_doc, 70)
        self.assertEqual(Counter(d.muc for d in DIEM_CHEO_DANG_TON_TAI), {"DOC": 71, "GHI": 53})
        self.assertEqual(len({d.khoa for d in DIEM_CHEO_DANG_TON_TAI}), 124)

    def test_hai_bang_cung_dong_dem_hai_diem(self):
        tai184 = [d.dich for d in DIEM_CHEO_DANG_TON_TAI if d.tep == "k2/sql_ghi_nhan_chung.py" and d.dong == 184]
        self.assertEqual(set(tai184), {"m4.dot_tep", "m4.tep"})
        self.assertEqual(len(tai184), 2)

    def test_khong_that_lac_ghi_chung_sql_g6_va_cong_ho(self):
        g6 = [d for d in DIEM_CHEO_DANG_TON_TAI if d.tep == "k2/sql_crm_kiem_hd.py"]
        self.assertEqual({(d.dong, d.dich) for d in g6},
                         {(n, "kho.viec_can_duyet") for n in (1306, 1323, 1372, 1385, 1475, 1479)} | {(1437, "kho.chung_tu")})
        self.assertEqual(len(g6), 7)
        self.assertEqual({(d.tep, d.dong, d.dich, d.muc) for d in DIEM_CHEO_DANG_TON_TAI if d.nhom == "CONG_HO"}, {
            ("k2/hoa_don.py", 569, "kho.lien_ket_dong", "DOC"),
            ("k2/nguon_chung.py", 210, "giao_tiep.stage_tin_cay", "GHI"),
            ("k2/lien_ket_chung.py", 42, "kho.bien_nhan_thao_tac", "GHI"),
            ("k2/sql_m3.py", 149, "nhat_ky.su_kien", "GHI"),
            ("k2/ma_tran_tham_quyen.py", 366, "nhat_ky.mtq_thay_doi", "GHI"),
            ("k2/ma_tran_tham_quyen.py", 399, "nhat_ky.mtq_tu_choi", "GHI"),
            ("ha_tang/ket_noi.py", 585, "nhat_ky.su_kien", "GHI"),
        })


class KieuKhaiBaoTests(unittest.TestCase):
    def test_diem_khong_hop_le_khong_the_thanh_ngoai_le(self):
        for doi in ({"dong": 0}, {"dong": True}, {"dich": "master.*"}, {"muc": "UPDATE"},
                    {"tep": "../gia.py"}, {"tep": "C:/gia.py"}, {"tep": "k2\\gia.py"}):
            with self.subTest(doi=doi), self.assertRaises(ValueError):
                diem_gia(**doi)
        with self.assertRaises(ValueError):
            vung_gia(dang_ton_tai=(diem_gia(),))

    def test_vung_khong_nhan_wildcard_tuy_y_va_trung_bang(self):
        for v1 in (("*.gia",), ("master.g*ia",), ("master.gia", "master.gia"), ("master.gia; DROP TABLE x",)):
            with self.subTest(v1=v1), self.assertRaises(ValueError):
                vung_gia(v1=v1)
        with self.assertRaises(ValueError):
            vung_gia(v3=("master.*",))

    def test_cong_bo_va_chu_dong_thieu_metadata_bi_tu_choi(self):
        for tao in (lambda: DuLieuCongBo("M2", "Hóa đơn", doi_tuong="kho.gia"),
                    lambda: DuLieuCongBo("M2", "Hóa đơn", loai="VIEW"),
                    lambda: ChuTheoDong("master.hop_dong", (), "M9", "loai = 'VAY'")):
            with self.assertRaises(ValueError):
                tao()

    def test_ban_khai_bat_bien_va_sao_chep_tuple(self):
        nguon = ["master.gia"]
        v = vung_gia(v1=nguon)
        nguon.append("master.khac")
        self.assertEqual(v.v1, ("master.gia",))
        with self.assertRaises(FrozenInstanceError):
            v.ma = "KHAC"

    def test_module_cu_giu_api_va_khong_lam_mat_vung_khi_roundtrip(self):
        cu = KhaiBaoModule("CRM", "Tên giả", "gia", "gia", 1)
        self.assertIsNone(cu.vung_du_lieu)
        self.assertEqual(ve_khai_bao_crm(cu)["ma"], "CRM")
        vung = next(v for v in CAC_VUNG_DU_LIEU if v.ma == "CRM")
        moi = replace(cu, vung_du_lieu=vung)
        self.assertEqual(moi.vung_du_lieu, vung)
        with self.assertRaisesRegex(ValueError, "metadata mới"):
            ve_khai_bao_crm(moi)
        with self.assertRaises(ValueError):
            replace(cu, vung_du_lieu=vung_gia())


if __name__ == "__main__":
    unittest.main()
