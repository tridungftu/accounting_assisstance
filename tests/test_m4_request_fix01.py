"""M4-04A FIX01 — hồi quy hữu hạn: canonical đầy đủ (lech_nhap) trước tải lên + khi đối soát; tệp đã biết phải đúng ô; bằng chứng hoàn tất giữ
nguyên khi đọc lại/phát lại. CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN, self-test NOT_RUN).

Tái dùng NGUYÊN `CoSo`/`FakeRequest`/`KhoGia` của tests/test_m4_request_tinh.py (không sửa file cũ, không monkeypatch runner). KHÔNG mạng/CSDL/Request
thật; TEST_ONLY DEMO. Golden là literal (mã lệch, PDF_SHA/PDF_LEN hashlib của test cũ), không lấy đầu ra của chính code.

F01 bản nháp đổi giữa DOC và GET-trước-tải (số tiền/tiền tệ/PN/người tạo/nhóm/trường) → HOLD đúng mã, 0 tải lên (ý nghĩa repro i01).
F02 đổi lúc chờ quét rồi tệp clean (cùng các loại lệch) → HOLD, không tải bytes, không bằng chứng (ý nghĩa repro i02).
F03 tệp đã biết ID chuyển ô/khu chung → HOLD TEP_LECH (repro i03); tệp lạ trong ô tệp → HOLD; tệp ở ô khác → vẫn hoàn tất (không chặn sai).
F04 mất ACK tải lên: một ứng viên đúng → hoàn tất; pending giữ CHUA_RO_TAI; ứng viên lạ cùng kích thước / trùng / sai bytes / lệch canonical → HOLD.
F05 dương lặp: hoàn tất → đối soát lại / phát lại đúng khóa / khóa mới: giữ bằng chứng + ID, 0 POST mới; đọc lỗi vẫn giữ bằng chứng; lệch sau hoàn tất
    chỉ báo QUAN_SAT_LECH, không hạ trạng thái.
F06 tĩnh: hằng SQL request_ghi coalesce bằng chứng thiếu + từ chối bằng chứng khác (M4_REQUEST_BANG_CHUNG_KHAC) — KHÔNG phải bằng chứng SQL native.
"""

from __future__ import annotations

import json
import re
import unittest
import uuid

from kho_tri_thuc.m4 import request_api as RA
from kho_tri_thuc.m4 import request_nhap as RN
from kho_tri_thuc.m4 import sql_request_nhap as S
from tests import test_m4_request_tinh as T

# biến đổi chi tiết Request (TEST_ONLY) → mã lệch literal mong đợi (thứ tự kiểm của lech_nhap: nhóm, người tạo, số tiền, tổng, PN, trường, API, tệp)
DRIFT = (
    ("so_tien", lambda d: {**d, "giaTri": {**d["giaTri"], T.T_TIEN: {"amount": "1", "currency": "VND"}}, "tongTien": None}, "SO_TIEN_LECH"),
    ("tien_te", lambda d: {**d, "giaTri": {**d["giaTri"], T.T_TIEN: {"amount": T.SO_TIEN, "currency": "USD"}}, "tongTien": None}, "SO_TIEN_LECH"),
    ("tong_tien", lambda d: {**d, "tongTien": {"amount": "1", "currency": "VND"}}, "TONG_TIEN_LECH"),
    ("phap_nhan", lambda d: {**d, "giaTri": {**d["giaTri"], T.T_PN: "PN_CU"}}, "PHAP_NHAN_LECH"),
    ("nguoi_tao", lambda d: {**d, "nguoiTao": {"tenDangNhap": T.CHU_KHOA}}, "NGUOI_TAO_LECH"),
    ("nhom", lambda d: {**d, "nhom": {"ma": "KHAC"}}, "NHOM_LECH"),
    ("truong", lambda d: {**d, "truong": [t for t in d["truong"] if t["ma"] != T.T_TEP]}, "TRUONG_LECH"),
    ("tao_qua_api", lambda d: {**d, "taoQuaApi": False}, "KHONG_TAO_QUA_API"),
)


class CoSoFix(T.CoSo):
    def dem_tai_len(self) -> int:
        return self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep")

    def dem_tai_ve(self) -> int:
        return self.fake.dem("GET", r"/api/v1/tep/.*")

    def them_tep(self, *, ma_truong=T.T_TEP, khu_chung=False, data=b"abc", quet="clean") -> str:
        x = self.mot_request()
        tid = str(uuid.uuid4())
        self.fake.tep[tid] = {"meta": {"id": tid, "tenTep": "khac.pdf", "maTruong": ma_truong, "khuChung": khu_chung, "kichThuoc": len(data),
                                       "mime": "application/pdf", "trangThaiQuet": quet}, "bytes": data}
        x["tep"].append(tid)
        return tid

    def cho_quet(self) -> str:
        r = self.tao()
        self.assertEqual(r["trang_thai"], "CHO_QUET")
        return self.mot_request()["tep"][0]

    def xong(self) -> dict:
        tid = self.cho_quet()
        self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual(r["trang_thai"], "DA_DOI_SOAT")
        return r


class F01TruocTaiLen(CoSoFix):
    def test_so_tien_doi_giua_doc_va_tai(self):  # ý nghĩa repro i01, không chạy/không sửa repro
        self.fake.quet_mac_dinh = "clean"

        def doi(fake):
            next(iter(fake.de_xuat.values()))["giaTri"][T.T_TIEN] = {"amount": "1", "currency": "VND"}
        self.fake.tiem("GET_DE_XUAT", None, doi)  # GET 1 (DOC) nguyên vẹn; GET 2 (trước tải) đã đổi
        r = self.tao()
        self.assertEqual((r["trang_thai"], r["buoc"], self.y()["hold_ma"]), ("HOLD", ["TAO", "DOC", "TAI"], "SO_TIEN_LECH"))
        self.assertEqual((self.fake.tep, self.dem_tai_len(), self.y()["remote_tep_id"], self.y()["doi_soat_sha256"]), ({}, 0, None, None))

    def test_moi_loai_lech_truoc_tai(self):
        for ten, bd, mong in DRIFT:
            with self.subTest(ten=ten):
                self.setUp()
                self.fake.tiem("GET_DE_XUAT", None, lambda f, bd=bd: setattr(f, "bien_doi_chi_tiet", bd))
                r = self.tao()
                self.assertEqual((r["trang_thai"], self.y()["trang_thai"], self.y()["hold_ma"]), ("HOLD", "HOLD", mong))
                self.assertEqual((self.fake.tep, self.dem_tai_len()), ({}, 0))

    def test_tep_la_xuat_hien_truoc_tai(self):
        def co_san(fake):
            x = next(iter(fake.de_xuat.values()))
            tid = str(uuid.uuid4())
            fake.tep[tid] = {"meta": {"id": tid, "tenTep": "la.pdf", "maTruong": T.T_TEP, "khuChung": False, "kichThuoc": 3, "mime": "application/pdf",
                                      "trangThaiQuet": "clean"}, "bytes": b"abc"}
            x["tep"].append(tid)
        self.fake.tiem("GET_DE_XUAT", None, co_san)  # maxFiles 2 còn chỗ — nhưng tệp không rõ nguồn trong ô tệp
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.dem_tai_len()), ("HOLD", "TEP_DA_CO_KHONG_RO", 0))


class F02KhiDoiSoat(CoSoFix):
    def test_so_tien_doi_luc_cho_quet(self):  # ý nghĩa repro i02
        tid = self.cho_quet()
        self.mot_request()["giaTri"][T.T_TIEN] = {"amount": "1", "currency": "VND"}
        self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["doi_soat_sha256"]), ("HOLD", "SO_TIEN_LECH", None))
        self.assertEqual(self.dem_tai_ve(), 0, "lệch canonical → không tải bytes; hash PDF đúng không cứu được")

    def test_moi_loai_lech_khi_doi_soat(self):
        for ten, bd, mong in DRIFT:
            with self.subTest(ten=ten):
                self.setUp()
                tid = self.cho_quet()
                self.fake.bien_doi_chi_tiet = bd
                self.fake.quet(tid, "clean")
                r = self.doi_soat()
                self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["doi_soat_sha256"], self.y()["doi_soat_byte_length"]),
                                 ("HOLD", mong, None, None))
                self.assertEqual((self.dem_tai_len(), self.dem_tai_ve()), (1, 0))

    def test_lech_khi_con_pending(self):
        self.cho_quet()
        self.fake.bien_doi_chi_tiet = DRIFT[0][1]
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "SO_TIEN_LECH"))


class F03TepDaBiet(CoSoFix):
    def test_tep_biet_chuyen_o(self):  # ý nghĩa repro i03
        tid = self.cho_quet()
        self.fake.tep[tid]["meta"]["maTruong"] = "khac"
        self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["remote_tep_id"]), ("HOLD", "TEP_LECH", tid))
        self.assertEqual(self.dem_tai_ve(), 0)

    def test_tep_biet_vao_khu_chung(self):
        tid = self.cho_quet()
        self.fake.tep[tid]["meta"]["khuChung"] = True
        self.fake.quet(tid, "clean")
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_LECH"))

    def test_tep_la_trong_o_tep(self):
        tid = self.cho_quet()
        self.them_tep()
        self.fake.quet(tid, "clean")
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_DA_CO_KHONG_RO"))

    def test_tep_cua_minh_pending_roi_clean_khong_bao_sai(self):  # đối chứng dương: không TEP_DA_CO_KHONG_RO cho chính tệp đã tải
        tid = self.cho_quet()
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["tep_trang_thai_quet"]), ("CHO_QUET", None, "pending"))
        self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["remote_tep_id"], self.y()["doi_soat_sha256"], self.y()["doi_soat_byte_length"]),
                         ("DA_DOI_SOAT", tid, T.PDF_SHA, T.PDF_LEN))

    def test_tep_o_khac_khong_chan(self):  # đối chứng dương: tệp ngoài ô tệp đã cấu hình không phải tệp lạ của ô
        tid = self.cho_quet()
        self.them_tep(ma_truong="phu_luc")
        self.them_tep(khu_chung=True)
        self.fake.quet(tid, "clean")
        self.assertEqual(self.doi_soat()["trang_thai"], "DA_DOI_SOAT")

    def test_lech_nhap_mien_dung_tep_rieng(self):
        tid = self.cho_quet()
        la = self.them_tep()
        x = self.mot_request()
        ct = RA.ChiTietRequest.tu(json.loads(self.fake._chi_tiet(x["id"]).body)["duLieu"])
        y = self.y()
        self.assertEqual(RN.RequestNhap.lech_nhap(y, ct), ["TEP_DA_CO_KHONG_RO"])
        self.assertEqual(RN.RequestNhap.lech_nhap(y, ct, tep_rieng={tid}), ["TEP_DA_CO_KHONG_RO"], "chỉ miễn đúng tệp riêng, không bỏ qua mọi tệp")
        self.assertEqual(RN.RequestNhap.lech_nhap(y, ct, tep_rieng={tid, la}), [])
        self.assertEqual(RN.RequestNhap.kiem_tep_biet(y, ct, tid)[1], None)
        self.assertEqual(RN.RequestNhap.kiem_tep_biet(y, ct, str(uuid.uuid4())), (None, "TEP_MAT"))


class F04MatAckTai(CoSoFix):
    def test_mot_ung_vien_dung(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.assertEqual(self.tao()["trang_thai"], "CHUA_RO_TAI")
        tid = self.mot_request()["tep"][0]
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["remote_tep_id"], self.y()["tep_trang_thai_quet"]), ("CHUA_RO_TAI", None, None))
        self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["remote_tep_id"], self.y()["doi_soat_sha256"]), ("DA_DOI_SOAT", tid, T.PDF_SHA))
        self.assertEqual(self.dem_tai_len(), 1)

    def test_ung_vien_la_cung_kich_thuoc(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.tao()
        tid = self.mot_request()["tep"][0]
        sai = bytes([T.PDF_RAW[0] ^ 1]) + T.PDF_RAW[1:]
        self.them_tep(data=sai)
        self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["remote_tep_id"]), ("HOLD", "TEP_DA_CO_KHONG_RO", None))

    def test_chi_bytes_sai(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.tao()
        t = self.fake.tep[self.mot_request()["tep"][0]]
        t["bytes"] = bytes([t["bytes"][0] ^ 1]) + t["bytes"][1:]
        t["meta"]["trangThaiQuet"] = "clean"
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_HASH_LECH"))

    def test_hai_ban_trung(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.tao()
        self.them_tep(data=T.PDF_RAW)
        for t in self.mot_request()["tep"]:
            self.fake.quet(t, "clean")
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"], self.y()["remote_tep_id"]), ("HOLD", "TEP_TRUNG_KHOP", None))

    def test_lech_canonical_sau_mat_ack(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.tao()
        self.fake.quet(self.mot_request()["tep"][0], "clean")
        self.fake.bien_doi_chi_tiet = DRIFT[3][1]
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"], self.dem_tai_ve()), ("HOLD", "PHAP_NHAN_LECH", 0))

    def test_khong_tai_lai_mu(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.tao()
        for _ in range(3):
            self.assertEqual(self.doi_soat()["trang_thai"], "CHUA_RO_TAI")
        self.assertEqual((self.dem_tai_len(), len(self.fake.tep)), (1, 1))


class F05DuongLap(CoSoFix):
    def test_hoan_tat_roi_doc_lai_phat_lai(self):
        k_tao = self.K("tao")
        r = self.tao(k_tao)
        self.assertEqual(r["trang_thai"], "CHO_QUET")
        x = self.mot_request()
        tid = x["tep"][0]
        self.fake.quet(tid, "clean")
        self.assertEqual(self.doi_soat()["trang_thai"], "DA_DOI_SOAT")
        n_post, n_tai_ve, yid = len(self.ghi_io()), self.dem_tai_ve(), self.y()["id"]
        lan = [self.doi_soat(), self.doi_soat(), self.tao(k_tao), self.tao()]  # đối soát lại ×2, phát lại đúng khóa, khóa mới (cùng intent)
        for i, r in enumerate(lan):
            with self.subTest(i=i):
                self.assertEqual((r["trang_thai"], r["buoc"], r["chan"]), ("DA_DOI_SOAT", ["DOC"], None))
                self.assertEqual((r["y_dinh"]["id"], r["y_dinh"]["remote_id"], r["y_dinh"]["remote_tep_id"], r["y_dinh"]["doi_soat_sha256"]),
                                 (yid, x["id"], tid, T.PDF_SHA))
                self.assertEqual([e for e in r["loi"] if e.get("ma") == "QUAN_SAT_LECH"], [])
        self.assertEqual(lan[2]["lap_lai"], True)
        y = self.y()
        self.assertEqual((y["doi_soat_sha256"], y["doi_soat_byte_length"], y["tep_trang_thai_quet"], y["remote_tep_id"]), (T.PDF_SHA, T.PDF_LEN, "clean", tid))
        self.assertEqual((len(self.ghi_io()), self.dem_tai_ve(), len(self.fake.de_xuat), len(self.fake.tep), len(self.kho.y)), (n_post, n_tai_ve, 1, 1, 1))
        self.assertEqual([e[1:4] for e in self.kho.su_kien if e[1] == "GHI_DOC"][-4:], [("GHI_DOC", "DA_DOI_SOAT", "DA_DOI_SOAT")] * 4)

    def test_doc_loi_van_giu_bang_chung(self):
        self.xong()
        self.fake.tiem("GET_DE_XUAT", ("HTTP", 500, {"loi": "x"}))
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], r["loi"][0]["ma"], self.y()["doi_soat_sha256"], self.y()["doi_soat_byte_length"]),
                         ("DA_DOI_SOAT", "REQUEST_HTTP_500", T.PDF_SHA, T.PDF_LEN))

    def test_lech_sau_hoan_tat_chi_bao(self):
        self.xong()
        self.mot_request()["giaTri"][T.T_TIEN] = {"amount": "1", "currency": "VND"}
        r = self.doi_soat()
        self.assertEqual(r["trang_thai"], "DA_DOI_SOAT", "bằng chứng lịch sử không bị hạ/undo")
        self.assertEqual([e for e in r["loi"] if e.get("ma") == "QUAN_SAT_LECH"],
                         [{"buoc": "DOC", "ma": "QUAN_SAT_LECH", "lech": ["SO_TIEN_LECH", "TONG_TIEN_LECH"]}])
        self.assertEqual(self.y()["doi_soat_sha256"], T.PDF_SHA)

    def test_tep_mat_sau_hoan_tat_chi_bao(self):
        self.xong()
        self.mot_request()["tep"].clear()
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], [e["lech"] for e in r["loi"] if e.get("ma") == "QUAN_SAT_LECH"]), ("DA_DOI_SOAT", [["TEP_MAT"]]))

    def test_bang_chung_xong_thuan(self):
        y = {"trang_thai": "DA_DOI_SOAT", "doi_soat_sha256": T.PDF_SHA, "doi_soat_byte_length": T.PDF_LEN}
        self.assertEqual(RN.RequestNhap._bang_chung_xong(y, {"den": "DA_DOI_SOAT"}),
                         {"den": "DA_DOI_SOAT", "doi_soat_sha256": T.PDF_SHA, "doi_soat_byte_length": T.PDF_LEN})
        khac = {"den": "DA_DOI_SOAT", "doi_soat_sha256": "9" * 64, "doi_soat_byte_length": 1}
        self.assertEqual(RN.RequestNhap._bang_chung_xong(y, dict(khac)), khac, "không ghi đè proof khác — để SQL từ chối rõ")
        self.assertEqual(RN.RequestNhap._bang_chung_xong({**y, "trang_thai": "CHO_QUET"}, {"den": "CHO_QUET"}), {"den": "CHO_QUET"})
        self.assertEqual(RN.ma_http("M4_REQUEST_BANG_CHUNG_KHAC"), 409)


class F06SqlTinh(unittest.TestCase):
    """STATIC trên hằng SQL — không phải bằng chứng PG native (Root kiểm riêng sau khi apply clone)."""

    def ham_ghi(self) -> str:
        return next(x for x in S.M4_REQUEST_NHAP if "CREATE OR REPLACE FUNCTION m4.request_ghi(" in x)

    def test_bang_chung_coalesce_va_tu_choi(self):
        g = self.ham_ghi()
        self.assertIn("coalesce(doi_soat_sha256, nullif(p_kq->>'doi_soat_sha256', ''))", g)
        self.assertIn("coalesce(doi_soat_byte_length, nullif(p_kq->>'doi_soat_byte_length', '')::bigint)", g)
        self.assertNotIn("THEN p_kq->>'doi_soat_sha256' ELSE", g)
        self.assertIn("M4_REQUEST_BANG_CHUNG_KHAC", g)
        self.assertLess(g.index("M4_REQUEST_BANG_CHUNG_KHAC"), g.index("UPDATE m4.request_y_dinh SET"), "từ chối TRƯỚC khi ghi")
        self.assertLess(g.index("M4_REQUEST_LEASE_MAT"), g.index("M4_REQUEST_BANG_CHUNG_KHAC"), "CAS lease/revision vẫn trước")
        self.assertIn("doi_soat_sha256", S.COT_MOT_LAN)
        self.assertIn("doi_soat_byte_length", S.COT_MOT_LAN)
        self.assertIn("CHECK (trang_thai <> 'DA_DOI_SOAT' OR (doi_soat_sha256 = pdf_sha256", "\n".join(S.M4_REQUEST_NHAP))

    def test_van_mot_constant(self):
        hang = [k for k, v in vars(S).items() if k.isupper() and isinstance(v, tuple) and v and all(isinstance(x, str) for x in v)
                and any("CREATE" in x for x in v)]
        self.assertEqual(hang, ["M4_REQUEST_NHAP"])
        sql = "\n".join(S.M4_REQUEST_NHAP)
        for cam in ("DROP ", "TRUNCATE", "DELETE FROM", "schema_migrations", "SET ROLE"):
            self.assertNotIn(cam, sql)
        self.assertEqual(len(re.findall(r"CREATE OR REPLACE FUNCTION m4\.request_ghi\(", sql)), 1)


if __name__ == "__main__":
    unittest.main()
