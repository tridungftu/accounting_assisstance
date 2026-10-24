"""CRM-01 — phần thuần không cần PostgreSQL: adapter shape #6, envelope tách raw, căn cứ trích dẫn (giá trị phải nằm trong trích
dẫn, "Suy ra", Điều/Khoản), typed theo profile (alias đơn vị tiền có provenance, %), tham số optional rỗng, lịch nghĩa vụ với
expected DEMO viết độc lập, phụ lục (đổi cơ sở/loại đợt đã thu), phiên CRM theo trình duyệt. Dữ liệu DEMO."""

from __future__ import annotations

import copy
import json
import unittest

from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, sha256
from kho_tri_thuc.k2.crm_phan_tich import co_token, so_sanh_phu_luc, tham_so_typed, tien_te_trong_trich, tong_hop, trang_thai_can_cu
from kho_tri_thuc.k2.loai_hinh_demo import KCN_THUE_DAT_DEMO, NHA_O_DEMO, profile_hash
from kho_tri_thuc.kiem_chung import fixtures_crm as F
from kho_tri_thuc.nguon.trich_hop_dong_6 import TrichHopDong6Adapter, doc_ket_qua, envelope, word_khoa

# Expected viết tay độc lập từ văn bản DEMO (không lấy từ output hệ thống hay `dap_an`)
EXPECTED_KCN = [
    {"khoa": "COC-1", "loai": "COC", "dot": 1, "so_tien_minor": 300_000_000, "tien_te": "VND", "han": "2026-09-15", "moc": None},
    {"khoa": "DOT-1", "loai": "DOT", "dot": 1, "so_tien_minor": 1_200_000_000, "tien_te": "VND", "han": "2026-10-15", "moc": None},
    {"khoa": "DOT-2", "loai": "DOT", "dot": 2, "so_tien_minor": 1_500_000_000, "tien_te": "VND", "han": None, "moc": "BAN_GIAO_DAT"},
]
EXPECTED_NHA = [
    {"khoa": "COC-1", "loai": "COC", "dot": 1, "so_tien_minor": 100_000_000, "tien_te": "VND", "han": "2026-09-10", "moc": None},
    {"khoa": "DOT-1", "loai": "DOT", "dot": 1, "so_tien_minor": 900_000_000, "tien_te": "VND", "han": "2026-11-10", "moc": None},
    {"khoa": "DOT-2", "loai": "DOT", "dot": 2, "so_tien_minor": 1_000_000_000, "tien_te": "VND", "han": None, "moc": "BAN_GIAO_CAN"},
]


def _lich(result):
    return [{k: r[k] for k in ("khoa", "loai", "dot", "so_tien_minor", "tien_te", "han", "moc")} for r in result["lich"]]


def _sua(fx, ma, **kw):
    next(p for p in fx["tham_so"] if p["ma"] == ma).update(kw)
    return fx


def _codes(fx, profile=KCN_THUE_DAT_DEMO, van_ban=F.VB_KCN, **kw):
    return [c["ma"] for c in tong_hop(tham_so_typed(fx, profile, van_ban), profile, **kw)["chan"]]


class AdapterTests(unittest.TestCase):
    def test_shape_6_envelope_tach_raw_va_khong_suy_tu_ten_file(self):
        raw, info, van_ban = F.mau("kcn_goc")
        env = envelope(raw, info, van_ban_nguon=van_ban)
        self.assertEqual(env["hash_ket_qua"], sha256(raw))
        self.assertEqual(env["van_ban_nguon_hash"], sha256(canonical_json(van_ban).encode()))  # văn bản có cấu trúc: hash dạng chuẩn
        batch = TrichHopDong6Adapter(env).read(raw)
        [record] = batch.records
        self.assertEqual(record.kind, "HOP_DONG_TEP")
        self.assertEqual(record.core["ket_qua_6"], json.loads(raw))  # raw nguồn giữ nguyên nội dung, envelope tách riêng
        self.assertNotIn("envelope", record.core["ket_qua_6"])
        self.assertIsNone(record.amount_minor)
        bare = envelope(raw, {"namespace": "TRICH_6_DEMO"})
        self.assertEqual((bare["phap_nhan"], bare["loai_ban"], bare["ma_hop_dong_chung"]), (None, None, None))  # không suy từ tên file
        with self.assertRaises(DataError):
            envelope(raw, {"namespace": "X", "khong_co": 1})
        with self.assertRaises(DataError):
            doc_ket_qua(b'{"hop_dong":"x","che_do":"co_AI","tham_so":[{"gia_tri":"1"}]}')
        with self.assertRaises(DataError):
            doc_ket_qua(b'{"hop_dong":"x","hop_dong":"y","che_do":"c","tham_so":[]}')

    def test_word_hash_chi_nhan_sha256_word_tham_chieu_tach_rieng(self):
        raw = F.mau("kcn_goc")[0]
        with self.assertRaises(DataError):
            envelope(raw, {"namespace": "N", "word_hash": "DEMO-KHONG-PHAI-HASH"})
        h = sha256(b"bytes Word DEMO")
        self.assertEqual(word_khoa(envelope(raw, {"namespace": "N", "word_hash": h})), "SHA256:" + h)
        self.assertEqual(word_khoa(envelope(raw, {"namespace": "N", "word_tham_chieu": "DEMO:HD_01"})), "THAM_CHIEU:DEMO:HD_01")
        self.assertIsNone(word_khoa(envelope(raw, {"namespace": "N"})))

    def test_chua_chay_ai_canh_bao(self):
        value = F.ket_qua("x.docx", [{"ma": "TC-01", "doan_lien_quan": "Hợp đồng số ..."}], che_do="chua_chay_AI")
        raw = canonical_json(value).encode()
        batch = TrichHopDong6Adapter(envelope(raw, {"namespace": "N"})).read(raw)
        self.assertIn("TRICH6_CHUA_CHAY_AI", [i.code for i in batch.issues])
        [row] = tham_so_typed(value, KCN_THUE_DAT_DEMO, F.VB_KCN)
        self.assertEqual((row["trang_thai_can_cu"], row["gia_tri_typed"]), ("KHONG_QUY_DINH", None))

    def test_legacy_va_common_cung_adapter(self):
        """CRM-41-01: JSON #6 cũ vẫn nhận như trước (envelope không có `common`); view của engine dùng chung (RULE_ONLY) đi CÙNG adapter, mang
        metadata common có phiên bản và cảnh báo RULE_ONLY; hash view (hash_ket_qua) tách khỏi hash raw nguồn ghi trong common."""
        from kho_tri_thuc.nguon import trich_chung_6 as T6
        from kho_tri_thuc.nguon.trich_hop_dong_6 import COMMON_ENV_KEYS
        raw_cu = F.mau("kcn_goc")[0]
        env_cu = envelope(raw_cu, {"namespace": "TRICH_6_DEMO"})
        self.assertNotIn("common", env_cu)
        self.assertEqual(TrichHopDong6Adapter(env_cu).read(raw_cu).records[0].core["ket_qua_6"], json.loads(raw_cu))
        kq = {"hop_dong": "x.docx", "che_do": "RULE_ONLY", "tao_luc": "2026-10-21T10:00:00",
              "bang": [{"ma": "TC-01", "nhom": "Thông tin chung", "tham_so": "Số hợp đồng", "gia_tri": "HD-01", "trich_dan": "Số: HD-01",
                        "nguon": "Quy tắc", "kiem_tra": "OK"}],
              "common": {"contract": T6.CONTRACT, "tham_so_da_dung": ["TC-01"]}}
        raw6 = canonical_json(kq).encode()
        view = T6.view_bytes(T6.chieu_tham_so(kq, raw_sha256=sha256(raw6)))
        cm = {k: None for k in COMMON_ENV_KEYS}
        cm.update(contract=T6.CONTRACT, request_id="crm:r", luot="20261021_100001", raw_ket_qua_sha256=sha256(raw6), source_sha256="d" * 64,
                  catalog_id="XD", catalog_sha256=T6.CATALOG["XD"]["catalog_sha256"], loai_hop_dong="XD", implementation_sha256="e" * 64,
                  tham_so_yeu_cau=["TC-01"], tham_so_da_dung=["TC-01"], adapter=T6.ADAPTER_VERSION)
        env = envelope(view, {"namespace": "TRICH_6_COMMON_V1", "word_hash": "d" * 64}, common=cm)
        self.assertNotEqual(env["hash_ket_qua"], env["common"]["raw_ket_qua_sha256"])
        batch = TrichHopDong6Adapter(env).read(view)
        self.assertIn("TRICH6_RULE_ONLY", [i.code for i in batch.issues])
        self.assertEqual([p["ma"] for p in batch.records[0].core["ket_qua_6"]["tham_so"]], ["TC-01"])


class CanCuTests(unittest.TestCase):
    def test_gia_tri_phai_nam_trong_trich_dan(self):
        """Trích dẫn có trong văn bản không chứng minh giá trị: 4 tỷ với câu trích 3 tỷ không được hiệu lực."""
        fx = _sua(F.kcn_goc(), "TT-02", gia_tri="4.000.000.000")
        params = tham_so_typed(fx, KCN_THUE_DAT_DEMO, F.VB_KCN)
        tt02 = next(p for p in params if p["ma"] == "TT-02")
        self.assertEqual(tt02["trang_thai_can_cu"], "GIA_TRI_KHONG_KHOP_TRICH_DAN")
        self.assertEqual(tt02["gia_tri_typed"]["minor"], 4_000_000_000)  # vẫn đọc được để hiển thị, nhưng không hiệu lực
        result = tong_hop(params, KCN_THUE_DAT_DEMO)
        self.assertIsNone(result["fields"]["gia_tri_hop_dong"])
        self.assertTrue({"GIA_TRI_KHONG_KHOP_TRICH_DAN", "THIEU_CAN_CU"} <= {c["ma"] for c in result["chan"]})
        tt02["xac_nhan_thu_cong"] = {"boi": "MO_PHONG_KT_A", "ly_do": "DEMO đối chiếu bản cứng"}
        self.assertEqual(tong_hop(params, KCN_THUE_DAT_DEMO)["fields"]["gia_tri_hop_dong"]["minor"], 4_000_000_000)
        self.assertEqual(trang_thai_can_cu({"gia_tri": "45", "trich_dan": "thời hạn 40 năm"}, "thời hạn 40 năm", "co_AI"), "GIA_TRI_KHONG_KHOP_TRICH_DAN")

    def test_suy_ra_khong_phai_can_cu_truc_tiep(self):
        fx = _sua(F.kcn_goc(), "LT-D1-HAN", ghi_chu="Suy ra từ tiến độ Điều 4")
        params = tham_so_typed(fx, KCN_THUE_DAT_DEMO, F.VB_KCN)
        self.assertEqual(next(p for p in params if p["ma"] == "LT-D1-HAN")["trang_thai_can_cu"], "SUY_RA")
        codes = [c["ma"] for c in tong_hop(params, KCN_THUE_DAT_DEMO)["chan"]]
        self.assertIn("SUY_RA", codes)
        self.assertIn("LICH_THIEU_HAN_MOC", codes)
        self.assertNotIn("SUY_RA", _codes(F.kcn_goc(), da_xac_nhan_thu_cong=True))
        # xác nhận chung cấp phiên bản (chưa có văn bản) KHÔNG thay xác nhận từng tham số suy ra
        self.assertIn("SUY_RA", [c["ma"] for c in tong_hop(params, KCN_THUE_DAT_DEMO, da_xac_nhan_thu_cong=True)["chan"]])

    def test_dieu_khoan_phai_khop_vi_tri(self):
        fx = _sua(F.kcn_goc(), "TT-02", dieu_khoan="Điều 99")
        self.assertEqual(next(p for p in tham_so_typed(fx, KCN_THUE_DAT_DEMO, F.VB_KCN) if p["ma"] == "TT-02")["trang_thai_can_cu"], "VI_TRI_KHONG_KHOP")
        self.assertIn("VI_TRI_KHONG_KHOP", _codes(fx))
        phang = " ".join(m["noi_dung"] for m in F.VB_KCN)  # văn bản phẳng: có câu trích nhưng không kiểm được Điều/Khoản
        statuses = {p["ma"]: p["trang_thai_can_cu"] for p in tham_so_typed(F.kcn_goc(), KCN_THUE_DAT_DEMO, phang)}
        self.assertEqual(statuses["TT-02"], "CHUA_DOI_CHIEU_VI_TRI")
        self.assertIn("CHUA_DOI_CHIEU_VI_TRI", _codes(F.kcn_goc(), van_ban=phang))
        self.assertEqual(_codes(F.kcn_goc(), van_ban=phang, da_xac_nhan_thu_cong=True), [])

    @staticmethod
    def _hai_dot(d1_gia_tri, d1_don_vi, d1_trich, *, d2="60.000.000", tong="100.000.000"):
        """Fixture độc lập kiểu probe review 03: nguồn có cấu trúc Điều/Khoản, D1 + D2 = tổng, không cọc, không xác nhận thủ công."""
        p = F._p
        tham_so = [p("TC-01", "Số HĐ", "HD-TOKEN-DEMO/01", "Hợp đồng số HD-TOKEN-DEMO/01", dieu="Phần đầu"),
                   p("TC-02", "Ngày ký", "01/09/2026", "ký ngày 01/09/2026", dieu="Phần đầu"),
                   p("TT-02", "Giá trị", tong, f"Tổng tiền thuê đất là {tong} đồng", don_vi="đồng", dieu="Điều 3"),
                   p("LT-D1-TIEN", "Đợt 1", d1_gia_tri, d1_trich, don_vi=d1_don_vi, dieu="Điều 4"),
                   p("LT-D1-HAN", "Hạn đợt 1", "15/10/2026", "trước ngày 15/10/2026", dieu="Điều 4"),
                   p("LT-D2-TIEN", "Đợt 2", d2, f"Đợt 2 thanh toán {d2} đồng", don_vi="đồng", dieu="Điều 4"),
                   p("LT-D2-HAN", "Hạn đợt 2", "15/12/2026", "trước ngày 15/12/2026", dieu="Điều 4")]
        vb = [{"dieu_khoan": "Phần đầu", "noi_dung": "Hợp đồng số HD-TOKEN-DEMO/01 ký ngày 01/09/2026."},
              {"dieu_khoan": "Điều 3", "noi_dung": f"Tổng tiền thuê đất là {tong} đồng."},
              {"dieu_khoan": "Điều 4", "noi_dung": f"{d1_trich} trước ngày 15/10/2026. Đợt 2 thanh toán {d2} đồng trước ngày 15/12/2026."}]
        return F.ket_qua("HD_TOKEN_DEMO.docx", tham_so), vb

    def test_token_so_khong_phai_substring(self):
        fx, vb = self._hai_dot("40.000.000", "VND", "Đợt 1 thanh toán 140.000.000 đồng")
        params = tham_so_typed(fx, KCN_THUE_DAT_DEMO, vb)
        d1 = next(p for p in params if p["ma"] == "LT-D1-TIEN")
        self.assertEqual(d1["trang_thai_can_cu"], "GIA_TRI_KHONG_KHOP_TRICH_DAN")  # 40m không phải token trong 140m
        result = tong_hop(params, KCN_THUE_DAT_DEMO)
        self.assertNotIn("DOT-1", [r["khoa"] for r in result["lich"]])
        self.assertTrue({"GIA_TRI_KHONG_KHOP_TRICH_DAN", "LICH_THIEU_SO_TIEN"} <= {c["ma"] for c in result["chan"]})
        for gia_tri, trich in (("1.000", "phí 11.000 đồng"), ("000.000", "40.000.000 đồng"), ("15/10/2026", "ngày 15/10/20261"), ("12", "số 3,12 đồng")):
            self.assertFalse(co_token(gia_tri, trich), (gia_tri, trich))
        for gia_tri, trich in (("40.000.000", "thanh toán 40.000.000 đồng."), ("1.000.000", "1.000.000đ"), ("30%", "30% giá trị"), ("30", "30% giá trị"),
                               ("15/10/2026", "trước ngày 15/10/2026."), ("0", "phí 0 đồng"), ("Bàn giao đất", "khi bàn giao đất")):
            self.assertTrue(co_token(gia_tri, trich), (gia_tri, trich))
        self.assertFalse(co_token("Bàn giao", "khi bàn giaođất"))
        ok_fx, ok_vb = self._hai_dot("40.000.000", "VND", "Đợt 1 thanh toán 40.000.000 đồng")  # control dương: đúng token + alias đồng ≡ VND
        ok = tong_hop(tham_so_typed(ok_fx, KCN_THUE_DAT_DEMO, ok_vb), KCN_THUE_DAT_DEMO)
        self.assertEqual((ok["chan"], [r["so_tien_minor"] for r in ok["lich"]]), ([], [40_000_000, 60_000_000]))

    def test_loai_tien_trong_trich_dan_phai_khop(self):
        fx, vb = self._hai_dot("1.000.000", "VND", "Đợt 1 thanh toán 1.000.000 USD", d2="99.000.000")
        params = tham_so_typed(fx, KCN_THUE_DAT_DEMO, vb)
        d1 = next(p for p in params if p["ma"] == "LT-D1-TIEN")
        self.assertEqual((d1["trang_thai_can_cu"], d1["loi"]), ("GIA_TRI_KHONG_KHOP_TRICH_DAN", ["TIEN_TE_KHONG_KHOP_TRICH_DAN"]))
        self.assertEqual(d1["gia_tri_typed"]["tien_te"], "VND")  # không tự đổi nhãn sang USD
        d1["xac_nhan_thu_cong"] = {"boi": "MO_PHONG_KT_A", "ly_do": "DEMO"}  # xác nhận thủ công không vượt được lỗi loại tiền
        result = tong_hop(params, KCN_THUE_DAT_DEMO)
        self.assertNotIn("DOT-1", [r["khoa"] for r in result["lich"]])
        self.assertIn("TIEN_TE_KHONG_KHOP_TRICH_DAN", {c["ma"] for c in result["chan"]})
        # trích dẫn không nêu loại tiền → chưa chứng minh, giữ chờ (xác nhận thủ công có lý do thì hiệu lực)
        fx, vb = self._hai_dot("40.000.000", "VND", "Đợt 1 thanh toán 40.000.000")
        params = tham_so_typed(fx, KCN_THUE_DAT_DEMO, vb)
        d1 = next(p for p in params if p["ma"] == "LT-D1-TIEN")
        self.assertEqual((d1["trang_thai_can_cu"], d1["loi"]), ("GIA_TRI_KHONG_KHOP_TRICH_DAN", []))
        d1["xac_nhan_thu_cong"] = {"boi": "MO_PHONG_KT_A", "ly_do": "DEMO đối chiếu bản cứng"}
        self.assertEqual(tong_hop(params, KCN_THUE_DAT_DEMO)["chan"], [])
        # control dương: ISO trong trích dẫn, alias VNĐ, USD đúng scale 2 với locale profile
        for don_vi, trich in (("VND", "Đợt 1 thanh toán 40.000.000 VND"), ("đồng", "Đợt 1 thanh toán 40.000.000 VNĐ"), ("VND", "Đợt 1 thanh toán 40.000.000đ")):
            fx, vb = self._hai_dot("40.000.000", don_vi, trich)
            self.assertEqual(tong_hop(tham_so_typed(fx, KCN_THUE_DAT_DEMO, vb), KCN_THUE_DAT_DEMO)["chan"], [], trich)
        fx, vb = self._hai_dot("1.000,50", "USD", "Đợt 1 thanh toán 1.000,50 USD")
        d1 = next(p for p in tham_so_typed(fx, KCN_THUE_DAT_DEMO, vb) if p["ma"] == "LT-D1-TIEN")
        self.assertEqual((d1["trang_thai_can_cu"], d1["gia_tri_typed"]["minor"], d1["gia_tri_typed"]["tien_te"]), ("CO_CAN_CU", 100_050, "USD"))
        self.assertEqual(tien_te_trong_trich("1.000.000", "1.000.000 USD và 1.000.000 đồng", KCN_THUE_DAT_DEMO), {"USD", "VND"})

    def test_trich_dan_khong_co_trong_van_ban(self):
        fx = _sua(F.kcn_goc(), "LT-D1-TIEN", trich_dan="Đợt 1 trả 1.200.000.000 đồng")
        self.assertIn("CAN_CU_KHONG_KHOP", _codes(fx))


class PhanTichTests(unittest.TestCase):
    def test_kcn_va_nha_o_lich_dung_expected_doc_lap(self):
        for fixture, van_ban, profile, expected, total, don_vi in ((F.kcn_goc(), F.VB_KCN, KCN_THUE_DAT_DEMO, EXPECTED_KCN, 3_000_000_000, "đồng"),
                                                                   (F.nha_goc(), F.VB_NHA, NHA_O_DEMO, EXPECTED_NHA, 2_000_000_000, "VND")):
            params = tham_so_typed(fixture, profile, van_ban)
            self.assertTrue(all(p["trang_thai_can_cu"] == "CO_CAN_CU" for p in params if p["gia_tri_tho"] is not None))
            result = tong_hop(params, profile)
            self.assertEqual(result["chan"], [])
            self.assertEqual(_lich(result), expected)
            self.assertEqual(result["so_tong"], {"da_so": True, "tong_lich": total, "tong_hop_dong": total})
            alias = f"{profile['ma']}@v{profile['phien_ban']}" if don_vi != "VND" else None
            self.assertEqual(result["fields"]["gia_tri_hop_dong"], {"minor": total, "tien_te": "VND", "don_vi_nguon": don_vi, "alias_profile": alias})

    def test_tham_so_optional_rong_khong_phai_nghia_vu(self):
        params = tham_so_typed(F.kcn_goc(), KCN_THUE_DAT_DEMO, F.VB_KCN)
        d3 = next(p for p in params if p["ma"] == "LT-D3-TYLE")
        self.assertEqual((d3["trang_thai_can_cu"], d3["gia_tri_typed"], d3["loi"]), ("KHONG_QUY_DINH", None, []))
        self.assertNotIn("DOT-3", [r["khoa"] for r in tong_hop(params, KCN_THUE_DAT_DEMO)["lich"]])
        empty_money = F.kcn_goc()
        empty_money["tham_so"].append({"ma": "LT-D3-HAN", "gia_tri": "", "don_vi": "đồng", "trich_dan": "", "kiem_tra": "THIẾU"})
        self.assertEqual(_codes(empty_money), [])

    def test_don_vi_tien_alias_va_ty_le(self):
        self.assertIn("PARSE_TIEN_TE", _codes(_sua(F.nha_goc(), "LT-D1-TIEN", don_vi="USD"), NHA_O_DEMO, F.VB_NHA))  # profile nhà ở chỉ VND
        self.assertIn("PARSE_TIEN_TE", _codes(_sua(F.kcn_goc(), "LT-D1-TIEN", don_vi="đô")))  # alias không cấu hình → không đoán
        for gia_tri, don_vi in (("30%", None), ("30", "%")):
            fx = F.kcn_goc()
            _sua(fx, "LT-D3-TYLE", gia_tri=gia_tri, don_vi=don_vi, trich_dan="Đợt 1 thanh toán", dieu_khoan="Điều 4")
            params = tham_so_typed(fx, KCN_THUE_DAT_DEMO, F.VB_KCN)
            self.assertEqual(next(p for p in params if p["ma"] == "LT-D3-TYLE")["loi"], [])
            self.assertIn("LICH_TY_LE_THIEU_CO_SO", [c["ma"] for c in tong_hop(params, KCN_THUE_DAT_DEMO)["chan"]])
        fx = _sua(F.kcn_goc(), "LT-D3-TYLE", gia_tri="30", don_vi=None, trich_dan="Đợt 1 thanh toán", dieu_khoan="Điều 4")
        self.assertIn("PARSE_TY_LE", _codes(fx))

    def test_thieu_can_cu_khong_thanh_0_va_chan(self):
        fx = _sua(F.kcn_goc(), "TT-02", trich_dan=None)
        params = tham_so_typed(fx, KCN_THUE_DAT_DEMO, F.VB_KCN)
        tt02 = next(p for p in params if p["ma"] == "TT-02")
        self.assertEqual((tt02["trang_thai_can_cu"], tt02["gia_tri_tho"]), ("KHONG_QUY_DINH", "3.000.000.000"))
        result = tong_hop(params, KCN_THUE_DAT_DEMO)
        self.assertIsNone(result["fields"]["gia_tri_hop_dong"])
        self.assertIn("THIEU_CAN_CU", [c["ma"] for c in result["chan"]])
        self.assertEqual(result["so_tong"], {"da_so": False})

    def test_parse_sai_trung_ma_ty_le_va_chua_doi_chieu(self):
        fx = F.kcn_goc()
        _sua(fx, "LT-D1-TIEN", trich_dan="Đợt 1 trả 1.200.000.000 đồng")
        _sua(fx, "KCN-01", gia_tri="khoảng mười nghìn")
        fx["tham_so"].append({**next(p for p in fx["tham_so"] if p["ma"] == "TC-01"), "gia_tri": "HD-KHAC-DEMO"})
        fx["tham_so"].append({"ma": "LT-D3-TYLE", "gia_tri": "30%", "trich_dan": "Đợt 1 thanh toán", "don_vi": None})
        codes = _codes(fx)
        for code in ("CAN_CU_KHONG_KHOP", "PARSE_SO", "THAM_SO_TRUNG_MA", "LICH_TY_LE_THIEU_CO_SO", "LICH_THIEU_SO_TIEN"):
            self.assertIn(code, codes)
        dup = F.kcn_goc()
        dup["tham_so"].append(copy.deepcopy(next(p for p in dup["tham_so"] if p["ma"] == "TC-01")))
        self.assertNotIn("THAM_SO_TRUNG_MA", _codes(dup))  # lặp cùng giá trị không phải mâu thuẫn
        self.assertIn("CHUA_DOI_CHIEU_NGUON", _codes(F.kcn_goc(), van_ban=None))  # `kiem_tra=OK` của nguồn không thay đối chiếu
        self.assertEqual(_codes(F.kcn_goc(), van_ban=None, da_xac_nhan_thu_cong=True), [])

    def test_moc_khong_co_ngay(self):
        dot2 = next(r for r in tong_hop(tham_so_typed(F.nha_goc(), NHA_O_DEMO, F.VB_NHA), NHA_O_DEMO)["lich"] if r["khoa"] == "DOT-2")
        self.assertEqual((dot2["han"], dot2["moc"]), (None, "BAN_GIAO_CAN"))  # không tự dùng ngày ký/nhận làm hạn

    def test_so_sanh_phu_luc(self):
        cu = [{**r, "id": i, "co_so": "TIEN_THUE_DAT_CHUA_VAT", "da_lien_ket_minor": lk}
              for i, (r, lk) in enumerate(zip(copy.deepcopy(EXPECTED_KCN), (300_000_000, 500_000_000, 0)))]
        moi = [{**r, "co_so": "TIEN_THUE_DAT_CHUA_VAT"} for r in copy.deepcopy(EXPECTED_KCN)]
        moi[2]["han"] = "2026-12-20"
        plan, chan = so_sanh_phu_luc(cu, moi)
        self.assertEqual(chan, [])
        self.assertEqual({p["khoa"]: p["hanh_dong"] for p in plan}, {"COC-1": "GIU", "DOT-1": "GIU", "DOT-2": "DOI"})
        for field, value in (("so_tien_minor", 800_000_000), ("co_so", "TIEN_THUE_DAT_GOM_VAT"), ("loai", "COC"), ("dot", 9)):
            changed = copy.deepcopy(moi)
            changed[1][field] = value  # đợt đã thu một phần: đổi tiền, cơ sở VAT, loại hay số đợt đều chặn
            _, chan = so_sanh_phu_luc(cu, changed)
            self.assertEqual([c["ma"] for c in chan], ["PHU_LUC_DOI_DOT_DA_THU"], field)
        _, chan = so_sanh_phu_luc(cu, moi[:1])
        self.assertIn("PHU_LUC_BO_DOT_DA_THU", [c["ma"] for c in chan])

    def test_profile_co_version_alias_va_hash(self):
        self.assertEqual((KCN_THUE_DAT_DEMO["phien_ban"], NHA_O_DEMO["phien_ban"]), (2, 2))
        self.assertEqual(KCN_THUE_DAT_DEMO["don_vi_tien_alias"]["đồng"], "VND")
        self.assertIn("giả định", KCN_THUE_DAT_DEMO["gia_dinh_mo_phong"])
        self.assertNotEqual(profile_hash(KCN_THUE_DAT_DEMO), profile_hash(NHA_O_DEMO))


class NutMoDemoTests(unittest.TestCase):
    """Giao diện cấu hình cục bộ của nút mở DEMO — chỉ chuỗi giả không chứa mật khẩu; không kết nối CSDL ở đây."""

    def _tep(self, value):
        import tempfile
        from pathlib import Path
        path = Path(tempfile.mkdtemp(prefix="ktt-crm-ketnoi-")) / "ket-noi.local.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_doc_ket_noi_chi_localhost_db_demo(self):
        from kho_tri_thuc.k2.crm_khoi_dong import doc_ket_noi
        ok = {"phien_ban": 1, "app_dsn": "host=127.0.0.1 port=5432 dbname=kho_crm_demo_v1 user=demo_app",
              "admin_dsn": "host=localhost port=5432 dbname=kho_crm_demo_v1 user=demo_admin"}
        self.assertEqual(doc_ket_noi(self._tep(ok))["db"], "kho_crm_demo_v1")
        for sua, code in (({"app_dsn": "host=10.0.0.5 port=5432 dbname=kho_crm_demo_v1 user=x"}, "KET_NOI_KHONG_LOCAL"),
                          ({"app_dsn": "host=127.0.0.1 port=5432 dbname=kho_that user=x"}, "KET_NOI_DB_KHONG_DEMO"),
                          ({"admin_dsn": "host=127.0.0.1 port=5432 dbname=kho_crm_demo_khac user=x"}, "KET_NOI_KHAC_DB"),
                          ({"them": 1}, "KET_NOI_SAI_DINH_DANG"), ({"phien_ban": 2}, "KET_NOI_SAI_DINH_DANG")):
            with self.assertRaises(DataError) as ctx:
                doc_ket_noi(self._tep({**ok, **sua}))
            self.assertEqual(ctx.exception.code, code)
            self.assertNotIn("user=", str(ctx.exception))  # thông điệp không chứa chuỗi kết nối
        with self.assertRaises(DataError) as ctx:
            doc_ket_noi(self._tep(ok).parent / "khong-co.json")
        self.assertEqual(ctx.exception.code, "CRM_CHUA_CAU_HINH")

    def test_tool_chuan_bi_khi_chua_cau_hinh_va_launcher(self):
        import importlib.util
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("chuan_bi_crm_demo", root / "tools" / "chuan_bi_crm_demo.py")
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KTT_CRM_DEMO_KET_NOI", None)
            code, status = tool.chay(root / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt-crm-root-")))
        self.assertEqual((code, status["trang_thai"], status["ma"]), (2, "CHUA_CAU_HINH", "CRM_CHUA_CAU_HINH"))
        ps = (root / "start-web.ps1").read_text(encoding="utf-8")
        self.assertNotIn("'server-out.log'", ps)
        self.assertNotIn("'server-error.log'", ps)
        self.assertIn("'server-error-' + $kttRun + '-' + $kttTry", ps)  # log riêng mỗi lần khởi chạy/thử lại
        self.assertIn("Test-KttOwnProcess", ps)  # chỉ dừng đúng tiến trình của app/root
        self.assertIn("tools\\chuan_bi_crm_demo.py", ps)
        self.assertIn('environment\\s*=\\s*"that"', ps)  # bước PG CRM không chạy khi mở kho thật
        for cam in ("Remove-Item", "DROP ", "_dsn", "KHO_PG_DSN"):
            self.assertNotIn(cam, ps)


class ShellTests(unittest.TestCase):
    def test_shell_crm_phien_theo_trinh_duyet_va_khong_nhan_danh_tinh(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from kho_tri_thuc.giao_dien.server import LocalApp
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(LocalApp.CRM_ENV, None)
            app = LocalApp(root / "cau_hinh.toml", Path(tempfile.mkdtemp(prefix="ktt-crm-shell-")) / "web")
            self.assertEqual(app.crm_state(LocalApp.CRM_MAC_DINH)["cau_hinh"], False)
        with self.assertRaises(DataError) as ctx:
            app.crm_phien(None)
        self.assertEqual(ctx.exception.code, "CRM_PHIEN")
        with self.assertRaises(DataError):
            app.crm_phien("phien-do-trinh-duyet-tu-dat")  # không nhận sid lạ
        s1, me1, moi1 = app.crm_phien(None, tao=True)
        s2, _, _ = app.crm_phien(None, tao=True)
        self.assertTrue(moi1)
        self.assertNotEqual(s1, s2)
        app._crm_phien[s2] = "MO_PHONG_CFO"
        self.assertEqual((app.crm_phien(s1)[1], app.crm_phien(s2)[1]), (me1, "MO_PHONG_CFO"))  # đổi vai phiên này không đổi phiên khác
        for key in ("actor", "phap_nhan_id", "trang_thai", "nguoi_duyet", "kiem_boi"):
            with self.assertRaises(DataError) as ctx:
                LocalApp.crm_body({key: "CFO_NTD"})
            self.assertEqual(ctx.exception.code, "CRM_CLIENT_IDENTITY")
        html = (root / "src" / "kho_tri_thuc" / "giao_dien" / "assets" / "index.html").read_text(encoding="utf-8")
        script = (root / "src" / "kho_tri_thuc" / "giao_dien" / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Hợp đồng &amp; lịch thu", html)
        self.assertIn('id="crm-file-soat"', html)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn('crmAct("tien-mau"', script)  # không còn đường tạo khoản thu riêng của CRM
        self.assertIn('crmAct("m1-sao-ke"', script)


if __name__ == "__main__":
    unittest.main()
