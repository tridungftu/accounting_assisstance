"""M4-04A FIX02 — ràng buộc tài chính nhóm (truongTongTien/truongPhapNhan tường minh), tổng tiền header bắt buộc đúng, và trường chính có kiểu
(tiền=number, pháp nhân=choice, tệp=attachment; đúng một lần) ở DOC đầu, GET trước tải, chờ quét/mất ACK. CODE_ONLY: coder viết, CHƯA CHẠY
(WRITTEN_NOT_RUN, self-test NOT_RUN).

Tái dùng NGUYÊN `CoSo`/`FakeRequest`/`KhoGia` của tests/test_m4_request_tinh.py (không sửa file cũ/FIX01/private). Không mạng/CSDL/Request thật.
Kỳ vọng literal theo nguồn Request (doc.ts: nhóm amountFieldCode/companyFieldCode, totalAmount header, kiểu trường) — không lấy đầu ra code.

G01 nhóm thiếu ràng buộc tiền / pháp nhân / cả hai → CAU_HINH_LECH, 0 POST, 0 intent (17 quan sát như private4: 3).
G02 tongTien None ở chi tiết → HOLD TONG_TIEN_LECH, 0 tải lên, không proof (1).
G03 danh sách trường rỗng / tiền, pháp nhân, tệp sai kiểu ở DOC đầu → HOLD TRUONG_LECH, 0 tải lên (4).
G04 đối chứng dương đầy đủ (1) + cùng 4 biến thể ở GET-trước-tải (0 tải lên) và lúc chờ quét (0 tải về, không proof) (8).
G05 thuần: truong_chinh_lech thiếu/kiểu lạ/None/trùng mã → lệch; trường thêm hợp lệ không chặn; kiem_nhom ràng buộc rỗng/khác.
G06 sau DA_DOI_SOAT: biến thể kiểu/tổng tiền chỉ báo QUAN_SAT_LECH, giữ proof lịch sử, không hạ trạng thái; mất ACK + trường sai kiểu → HOLD.
"""

from __future__ import annotations

import unittest

from kho_tri_thuc.m4 import request_api as RA
from kho_tri_thuc.m4 import request_nhap as RN
from tests import test_m4_request_tinh as T

CHINH = ((T.T_TIEN, "number"), (T.T_PN, "choice"), (T.T_TEP, "attachment"))
CH = {"truong_tien": T.T_TIEN, "truong_phap_nhan": T.T_PN, "truong_tep": T.T_TEP}


def bien_the_truong(nhan):
    """EMPTY = chi tiết không có dòng trường nào; mã trường chính = dòng đó đổi kiểu thành 'text'."""
    if nhan == "EMPTY":
        return lambda d: {**d, "truong": []}
    return lambda d: {**d, "truong": [{**t, "kieu": "text"} if t["ma"] == nhan else dict(t) for t in d["truong"]]}


BIEN_THE = ["EMPTY"] + [m for m, _ in CHINH]


class CoSoFix2(T.CoSo):
    def dem_tai_len(self) -> int:
        return self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep")

    def dem_tai_ve(self) -> int:
        return self.fake.dem("GET", r"/api/v1/tep/.*")

    def proof(self) -> bool:
        return (self.y() or {}).get("doi_soat_sha256") is not None


class G01RangBuocNhom(CoSoFix2):
    def test_nhom_thieu_rang_buoc_tai_chinh(self):
        for nhan, thieu, mong in (("AMOUNT", ("truongTongTien",), ["TRUONG_TIEN_LECH"]), ("COMPANY", ("truongPhapNhan",), ["TRUONG_PHAP_NHAN_LECH"]),
                                  ("BOTH", ("truongTongTien", "truongPhapNhan"), ["TRUONG_TIEN_LECH", "TRUONG_PHAP_NHAN_LECH"])):
            with self.subTest(rang_buoc=nhan):
                self.setUp()
                self.fake.quet_mac_dinh = "clean"
                for k in thieu:
                    self.fake.nhom[0][k] = None
                r = self.tao()
                self.assertEqual((r["trang_thai"], r["thieu"]), ("CAU_HINH_LECH", mong))
                self.assertEqual((self.ghi_io(), self.kho.y, self.kho.bien_nhan), ([], {}, {}))


class G02TongTienHeader(CoSoFix2):
    def test_tong_tien_none(self):
        self.fake.quet_mac_dinh = "clean"
        self.fake.bien_doi_chi_tiet = lambda d: {**d, "tongTien": None}
        r = self.tao()
        self.assertEqual((r["trang_thai"], r["buoc"], self.y()["hold_ma"]), ("HOLD", ["TAO", "DOC"], "TONG_TIEN_LECH"))
        self.assertEqual((self.dem_tai_len(), self.proof()), (0, False))

    def test_thu_tu_ma_so_tien_body_truoc_header(self):
        self.fake.bien_doi_chi_tiet = lambda d: {**d, "giaTri": {**d["giaTri"], T.T_TIEN: {"amount": "1", "currency": "VND"}}, "tongTien": None}
        self.tao()
        self.assertEqual(self.y()["hold_ma"], "SO_TIEN_LECH")

    def test_tong_tien_khac_tien_te(self):
        self.fake.bien_doi_chi_tiet = lambda d: {**d, "tongTien": {"amount": T.SO_TIEN, "currency": "USD"}}
        self.tao()
        self.assertEqual((self.y()["hold_ma"], self.dem_tai_len()), ("TONG_TIEN_LECH", 0))


class G03KieuTruongDocDau(CoSoFix2):
    def test_rong_hoac_sai_kieu(self):
        for nhan in BIEN_THE:
            with self.subTest(truong=nhan):
                self.setUp()
                self.fake.quet_mac_dinh = "clean"
                self.fake.bien_doi_chi_tiet = bien_the_truong(nhan)
                r = self.tao()
                self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.dem_tai_len(), self.proof()), ("HOLD", "TRUONG_LECH", 0, False))

    def test_trung_ma_truong_chinh(self):
        self.fake.bien_doi_chi_tiet = lambda d: {**d, "truong": d["truong"] + [{"ma": T.T_TIEN, "kieu": "number"}]}
        self.tao()
        self.assertEqual((self.y()["hold_ma"], self.dem_tai_len()), ("TRUONG_LECH", 0))


class G04TaiKiem(CoSoFix2):
    def test_duong_day_du(self):
        self.fake.quet_mac_dinh = "clean"
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.dem_tai_len(), self.dem_tai_ve(), self.proof()), ("DA_DOI_SOAT", 1, 1, True))
        self.assertEqual((self.y()["doi_soat_sha256"], self.y()["doi_soat_byte_length"]), (T.PDF_SHA, T.PDF_LEN))

    def test_truoc_tai(self):
        for nhan in BIEN_THE:
            with self.subTest(truong=nhan):
                self.setUp()
                self.fake.quet_mac_dinh = "clean"
                self.fake.tiem("GET_DE_XUAT", None, lambda f, bd=bien_the_truong(nhan): setattr(f, "bien_doi_chi_tiet", bd))
                r = self.tao()
                self.assertEqual((r["trang_thai"], r["buoc"], self.y()["hold_ma"]), ("HOLD", ["TAO", "DOC", "TAI"], "TRUONG_LECH"))
                self.assertEqual((self.dem_tai_len(), self.dem_tai_ve(), self.proof()), (0, 0, False))

    def test_cho_quet(self):
        for nhan in BIEN_THE:
            with self.subTest(truong=nhan):
                self.setUp()
                self.assertEqual(self.tao()["trang_thai"], "CHO_QUET")
                self.fake.bien_doi_chi_tiet = bien_the_truong(nhan)
                for tid in self.fake.tep:
                    self.fake.quet(tid, "clean")
                r = self.doi_soat()
                self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TRUONG_LECH"))
                self.assertEqual((self.dem_tai_len(), self.dem_tai_ve(), self.proof()), (1, 0, False))

    def test_tong_tien_none_luc_cho_quet(self):
        self.tao()
        self.fake.bien_doi_chi_tiet = lambda d: {**d, "tongTien": None}
        for tid in self.fake.tep:
            self.fake.quet(tid, "clean")
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"], self.dem_tai_ve(), self.proof()), ("HOLD", "TONG_TIEN_LECH", 0, False))

    def test_mat_ack_tai_sai_kieu(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.assertEqual(self.tao()["trang_thai"], "CHUA_RO_TAI")
        self.fake.bien_doi_chi_tiet = bien_the_truong(T.T_TEP)
        for tid in self.fake.tep:
            self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["remote_tep_id"], self.dem_tai_ve(), self.proof()),
                         ("HOLD", "TRUONG_LECH", None, 0, False))
        self.assertEqual(self.dem_tai_len(), 1, "không tải lại / không khóa mới")


class G05Thuan(unittest.TestCase):
    def test_truong_chinh_lech(self):
        dung = tuple(CHINH)
        self.assertEqual(RN.truong_chinh_lech(dung, CH), [])
        self.assertEqual(RN.truong_chinh_lech(dung + (("ghi_chu", "text"), ("phu_luc", "attachment")), CH), [], "trường thêm hợp lệ không chặn")
        self.assertEqual(RN.truong_chinh_lech((), CH), [T.T_TIEN, T.T_PN, T.T_TEP])
        self.assertEqual(RN.truong_chinh_lech(dung[1:], CH), [T.T_TIEN])
        self.assertEqual(RN.truong_chinh_lech(((T.T_TIEN, "kieu_la"),) + dung[1:], CH), [T.T_TIEN])
        self.assertEqual(RN.truong_chinh_lech(((T.T_TIEN, None),) + dung[1:], CH), [T.T_TIEN])
        self.assertEqual(RN.truong_chinh_lech(dung[:2] + ((T.T_TEP, "choice"),), CH), [T.T_TEP])
        self.assertEqual(RN.truong_chinh_lech(dung + ((T.T_PN, "choice"),), CH), [T.T_PN], "trùng mã trường chính, kể cả cùng kiểu")
        self.assertEqual(RN.TRUONG_CHINH_KIEU, (("truong_tien", "number"), ("truong_phap_nhan", "choice"), ("truong_tep", "attachment")))

    def test_kiem_nhom_rang_buoc(self):
        ch = T.cau_hinh()
        self.assertEqual(RN.kiem_nhom(ch, RA.NhomRequest.tu(T.nhom_json())), [])
        self.assertEqual(RN.kiem_nhom(ch, RA.NhomRequest.tu(T.nhom_json(truongTongTien=None))), ["TRUONG_TIEN_LECH"])
        self.assertEqual(RN.kiem_nhom(ch, RA.NhomRequest.tu(T.nhom_json(truongPhapNhan=None))), ["TRUONG_PHAP_NHAN_LECH"])
        self.assertEqual(RN.kiem_nhom(ch, RA.NhomRequest.tu(T.nhom_json(truongTongTien=""))), ["TRUONG_TIEN_LECH"])
        self.assertEqual(RN.kiem_nhom(ch, RA.NhomRequest.tu(T.nhom_json(truongPhapNhan=T.T_TIEN))), ["TRUONG_PHAP_NHAN_LECH"])
        n = T.nhom_json()
        del n["truongTongTien"], n["truongPhapNhan"]
        self.assertEqual(RN.kiem_nhom(ch, RA.NhomRequest.tu(n)), ["TRUONG_TIEN_LECH", "TRUONG_PHAP_NHAN_LECH"])


class G06SauHoanTat(CoSoFix2):
    def xong(self):
        self.fake.quet_mac_dinh = "clean"
        self.assertEqual(self.tao()["trang_thai"], "DA_DOI_SOAT")

    def test_lech_kieu_va_header_chi_bao(self):
        for ten, bd, mong in (("kieu", bien_the_truong(T.T_PN), ["TRUONG_LECH"]), ("rong", bien_the_truong("EMPTY"), ["TRUONG_LECH"]),
                              ("header", lambda d: {**d, "tongTien": None}, ["TONG_TIEN_LECH"])):
            with self.subTest(ten=ten):
                self.setUp()
                self.xong()
                n_post, n_ve = len(self.ghi_io()), self.dem_tai_ve()
                self.fake.bien_doi_chi_tiet = bd
                r = self.doi_soat()
                self.assertEqual((r["trang_thai"], r["buoc"]), ("DA_DOI_SOAT", ["DOC"]))
                self.assertEqual([e["lech"] for e in r["loi"] if e.get("ma") == "QUAN_SAT_LECH"], [mong], "quan sát mới không được coi là hợp lệ nhờ proof cũ")
                self.assertEqual((self.y()["doi_soat_sha256"], self.y()["doi_soat_byte_length"]), (T.PDF_SHA, T.PDF_LEN))
                self.assertEqual((len(self.ghi_io()), self.dem_tai_ve()), (n_post, n_ve))

    def test_quan_sat_dung_khong_bao(self):
        self.xong()
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], [e for e in r["loi"] if e.get("ma") == "QUAN_SAT_LECH"]), ("DA_DOI_SOAT", []))


if __name__ == "__main__":
    unittest.main()
