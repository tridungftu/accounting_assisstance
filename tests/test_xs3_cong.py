"""XS-3b: dữ liệu giả thuần bộ nhớ, không ABBYY/mạng/PG hoặc xóa tệp.

Không tạo file tạm nên từng test độc lập cả dưới CODEX_NO_DELETE_FILES.
"""

from copy import deepcopy
from dataclasses import replace
import io
import unittest
import zipfile

from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import TrangThaiEngine, hash_du_lieu
from kho_tri_thuc.ha_tang.engine_cong import (
    BANG_ANH_XA_LOI_OCR, BANG_ANH_XA_LY_DO_AI, BANG_ANH_XA_MAU_LY_DO_AI,
    BANG_ANH_XA_NGOAI_LE_AI,
    DauVaoOCR, EngineAI, EngineOCR, dang_ky_engine_cong,
)
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.tri_thuc.ai_cuc_bo import LocalAIUnavailable
from kho_tri_thuc.tri_thuc.cong_ai import (
    CloudLoi, KetQuaAI, MaskKhongGui, TruongAI, YeuCauAI,
)
from tests.test_xs3_engine import BoTestHopDongEngine, MauEngine, kiem_tra_mau_engine


def _docx_gia():
    bo_dem = io.BytesIO()
    with zipfile.ZipFile(bo_dem, "w") as tep:
        muc = zipfile.ZipInfo("word/document.xml", date_time=(2026, 10, 26, 0, 0, 0))
        tep.writestr(muc, b'<w:document xmlns:w="urn:demo"><w:p>DEMO</w:p></w:document>')
    return bo_dem.getvalue()


DOCX = _docx_gia()
OCR_VAO = DauVaoOCR(b"%PDF-DEMO", ".PDF")
AI_VAO = YeuCauAI("HOI_DAP_VAY", "Lãi suất DEMO 5%.", "Trích lãi suất.",
                  ("lai_suat",), (("DEMO", "CONG_TY"),), "PN-DEMO", "VIEC-DEMO", "DX-DEMO")
AI_RA = KetQuaAI("HOI_DAP_VAY", "VANG", {
    "lai_suat": TruongAI("lai_suat", "5%", "Lãi suất DEMO 5%.", "LOCAL"),
}, "LOCAL", "Đề xuất DEMO.", ("DUOI_NGUONG",), ("truong_demo",), "YC-DEMO")
BI_MAT = "NOI_DUNG_TEP_DEMO Traceback van_ban_gia"


class CongOCRGia:
    def __init__(self, ket_qua=DOCX, loi=None):
        self.ket_qua, self.loi = ket_qua, loi
        self.luot = []

    def ocr(self, raw, duoi, *, huy=None):
        self.luot.append((raw, duoi, huy))
        if self.loi is not None:
            raise self.loi
        return self.ket_qua


class CongAIGia:
    def __init__(self, ket_qua=AI_RA, loi=None):
        self.ket_qua, self.loi = ket_qua, loi
        self.luot = []

    def goi(self, yeu_cau, *, kiem_tra=None):
        self.luot.append((yeu_cau, kiem_tra))
        if self.loi is not None:
            raise self.loi
        return self.ket_qua


class OCRHopDongTests(BoTestHopDongEngine, unittest.TestCase):
    cac_mau = (MauEngine(OCR_VAO, TrangThaiEngine.XONG, "OCR_XONG",
                         "Đã nhận kết quả nhận dạng.", DOCX),)

    def tao_engine(self):
        return EngineOCR(CongOCRGia())


class AIHopDongTests(BoTestHopDongEngine, unittest.TestCase):
    cac_mau = (MauEngine(AI_VAO, TrangThaiEngine.XONG, "AI_XONG",
                         "Đã nhận kết quả từ cổng AI.", AI_RA),)

    def tao_engine(self):
        return EngineAI(CongAIGia())


class AnhXaLoiTests(unittest.TestCase):
    def test_tung_dong_ocr_xong_cho_loi_va_khong_lo_noi_dung(self):
        mong_doi = {
            "OCR_HET_HAN_MUC": (TrangThaiEngine.CHO, "OCR_HET_HAN_MUC", "Chờ hạn mức trang nhận dạng."),
            "OCR_HUY": (TrangThaiEngine.CHO, "OCR_DA_HUY", "Yêu cầu nhận dạng đã được hủy."),
            "OCR_QUA_GIO": (TrangThaiEngine.CHO, "OCR_QUA_GIO", "Chưa nhận được kết quả trong thời gian chờ."),
            "OCR_KHONG_NHAN": (TrangThaiEngine.CHO, "OCR_KHONG_NHAN", "Cổng nhận dạng chưa nhận tài liệu."),
            "OCR_DINH_DANG": (TrangThaiEngine.LOI, "OCR_DINH_DANG", "Định dạng tài liệu chưa được hỗ trợ."),
            "OCR_LOI_ABBYY": (TrangThaiEngine.LOI, "OCR_LOI_ABBYY", "Cổng nhận dạng không hoàn tất xử lý."),
        }
        self.assertEqual(dict(BANG_ANH_XA_LOI_OCR), {(DataError, k): v for k, v in mong_doi.items()})
        self.assertEqual(len({v[1] for v in mong_doi.values()}), len(mong_doi))
        for ma, (tt, ma_ra, ly_do) in mong_doi.items():
            with self.subTest(ma=ma):
                cong = CongOCRGia(loi=DataError(ma, BI_MAT, BI_MAT))
                kq = kiem_tra_mau_engine(self, EngineOCR(cong), MauEngine(OCR_VAO, tt, ma_ra, ly_do))
                self.assertNotIn(BI_MAT, repr(kq))

    def test_tung_dong_ngoai_le_ai(self):
        mong_doi = {
            LocalAIUnavailable: (TrangThaiEngine.CHO, "AI_LOCAL_CHUA_SAN", "Local AI chưa sẵn sàng xử lý."),
            MaskKhongGui: (TrangThaiEngine.CHO, "AI_MASK_KHONG_GUI", "Cổng Mask chưa cho phép gửi yêu cầu."),
            CloudLoi: (TrangThaiEngine.LOI, "AI_CLOUD_LOI", "Cổng AI không hoàn tất xử lý Cloud."),
        }
        self.assertEqual(dict(BANG_ANH_XA_NGOAI_LE_AI), mong_doi)
        self.assertEqual(len({v[1] for v in mong_doi.values()}), len(mong_doi))
        for lop, (tt, ma, ly_do) in mong_doi.items():
            with self.subTest(lop=lop):
                kq = kiem_tra_mau_engine(self, EngineAI(CongAIGia(loi=lop(BI_MAT))),
                                        MauEngine(AI_VAO, tt, ma, ly_do))
                self.assertNotIn(BI_MAT, repr(kq))

    def test_tung_dong_ly_do_ai_giu_nguyen_dto(self):
        mong_doi = {
            "LOCAL_LOI": (TrangThaiEngine.LOI, "AI_LOCAL_LOI", "Local AI không hoàn tất xử lý."),
            "LOCAL_KHONG_CHAY": (TrangThaiEngine.CHO, "AI_LOCAL_CHUA_SAN", "Local AI chưa sẵn sàng xử lý."),
            "LOCAL_TAT": (TrangThaiEngine.CHO, "AI_LOCAL_TAT", "Local AI chưa được bật để xử lý."),
            "CLOUD_TAT": (TrangThaiEngine.CHO, "AI_CLOUD_TAT", "Đường Cloud chưa được bật để xử lý."),
            "LOAI_VIEC_KHONG_DUNG_CLOUD": (TrangThaiEngine.CHO, "AI_LOAI_VIEC_KHONG_DUNG_CLOUD", "Loại việc này chỉ được xử lý bằng Local AI."),
            "CAI_DAT_CLOUD_LOI": (TrangThaiEngine.LOI, "AI_CAI_DAT_CLOUD_LOI", "Cài đặt Cloud chưa hợp lệ."),
            "CHUA_CO_KHOA_API": (TrangThaiEngine.CHO, "AI_CHUA_CO_KHOA_API", "Chờ cấu hình khóa truy cập Cloud."),
            "CHUA_CO_KHOA_MASK": (TrangThaiEngine.CHO, "AI_CHUA_CO_KHOA_MASK", "Chờ cấu hình khóa truy cập Mask."),
            "XML_HOA_DON_THO": (TrangThaiEngine.LOI, "AI_XML_HOA_DON_THO", "Cổng AI không gửi XML hóa đơn thô ra Cloud."),
            "QUA_NHIEU_DINH_DANH": (TrangThaiEngine.LOI, "AI_QUA_NHIEU_DINH_DANH", "Số định danh vượt giới hạn của cổng AI."),
            "MASK_KHONG_CHAY": (TrangThaiEngine.CHO, "AI_MASK_KHONG_CHAY", "Mask chưa sẵn sàng xử lý."),
            "MASK_DANH_MUC_KHOA": (TrangThaiEngine.CHO, "AI_MASK_DANH_MUC_KHOA", "Chờ mở danh mục của Mask."),
            "MASK_DANH_MUC_CHUA_CO": (TrangThaiEngine.CHO, "AI_MASK_DANH_MUC_CHUA_CO", "Chờ danh mục bí danh của Mask."),
            "MASK_CON_SOT": (TrangThaiEngine.LOI, "AI_MASK_CON_SOT", "Mask chưa che hết định danh của yêu cầu."),
            "MASK_KHONG_CHO_GUI": (TrangThaiEngine.CHO, "AI_MASK_KHONG_CHO_GUI", "Mask chưa cho phép gửi yêu cầu."),
            "MASK_PHAN_HOI_LOI": (TrangThaiEngine.LOI, "AI_MASK_PHAN_HOI_LOI", "Mask trả kết quả chưa hợp lệ."),
            "MASK_API_CHUA_BAT": (TrangThaiEngine.CHO, "AI_MASK_API_CHUA_BAT", "Chờ bật chế độ API của Mask."),
            "MASK_SAI_KHOA": (TrangThaiEngine.LOI, "AI_MASK_SAI_KHOA", "Khóa truy cập Mask chưa hợp lệ."),
            "CON_SOT_DINH_DANH": (TrangThaiEngine.LOI, "AI_CON_SOT_DINH_DANH", "Cổng AI phát hiện định danh chưa được che."),
            "CLOUD_KHONG_KET_NOI": (TrangThaiEngine.CHO, "AI_CLOUD_KHONG_KET_NOI", "Chưa kết nối được Cloud qua cổng AI."),
            "CLOUD_TU_CHOI": (TrangThaiEngine.LOI, "AI_CLOUD_TU_CHOI", "Cloud từ chối xử lý yêu cầu."),
            "CLOUD_LOI": (TrangThaiEngine.LOI, "AI_CLOUD_LOI", "Cổng AI không hoàn tất xử lý Cloud."),
            "MASK_MO_CHE_LOI": (TrangThaiEngine.LOI, "AI_MASK_MO_CHE_LOI", "Mask không mở che được kết quả Cloud."),
        }
        self.assertEqual(dict(BANG_ANH_XA_LY_DO_AI), mong_doi)
        self.assertEqual(len({v[1] for v in mong_doi.values()}), len(mong_doi))
        for ma_goc, (tt, ma, ly_do) in mong_doi.items():
            with self.subTest(ma=ma_goc):
                dto = replace(AI_RA, muc="DO", truong={}, duong="KHONG",
                              ly_do=(ma_goc,), thong_bao=BI_MAT)
                kq = kiem_tra_mau_engine(self, EngineAI(CongAIGia(dto)),
                                        MauEngine(AI_VAO, tt, ma, ly_do, dto))
                self.assertIs(kq.du_lieu, dto)
                self.assertNotIn(BI_MAT, kq.ly_do)

    def test_ngoai_le_la_va_lop_con_noi_len_nguyen_ven(self):
        class DataErrorLa(DataError):
            pass

        class CloudLoiLa(CloudLoi):
            pass

        class LocalAILa(LocalAIUnavailable):
            pass

        class MaskLa(MaskKhongGui):
            pass

        for lop_engine, lop_cong, vao, cac_loi in (
            (EngineOCR, CongOCRGia, OCR_VAO, (
                DataError("OCR_MA_LA", BI_MAT), DataErrorLa("OCR_HUY", BI_MAT),
                RuntimeError(BI_MAT), ValueError(BI_MAT), TypeError(BI_MAT), OSError(BI_MAT))),
            (EngineAI, CongAIGia, AI_VAO, (
                CloudLoiLa(BI_MAT), LocalAILa(BI_MAT), MaskLa(BI_MAT),
                RuntimeError(BI_MAT), ValueError(BI_MAT),
                TypeError(BI_MAT), OSError(BI_MAT))),
        ):
            for loi in cac_loi:
                with self.subTest(engine=lop_engine, loi=type(loi)):
                    with self.assertRaises(type(loi)) as bat:
                        lop_engine(lop_cong(loi=loi)).chay(vao)
                    self.assertIs(bat.exception, loi)

    def test_nhieu_ly_do_uu_tien_loi_va_khong_phu_thuoc_thu_tu(self):
        cac_ma = ("LOCAL_KHONG_CHAY", "MASK_MO_CHE_LOI", "CLOUD_TAT")
        for ly_do in (cac_ma, tuple(reversed(cac_ma))):
            with self.subTest(ly_do=ly_do):
                dto = replace(AI_RA, muc="DO", truong={}, duong="KHONG", ly_do=ly_do)
                kq = EngineAI(CongAIGia(dto)).chay(AI_VAO)
                self.assertEqual((kq.trang_thai, kq.ma),
                                 (TrangThaiEngine.LOI, "AI_MASK_MO_CHE_LOI"))
                self.assertIs(kq.du_lieu, dto)

    def test_tung_dong_ma_http_do_cong_ma_hoa_trong_dto(self):
        mong_doi = {
            r"CLOUD_HTTP_[1-5][0-9]{2}": (
                TrangThaiEngine.LOI, "AI_CLOUD_LOI", "Cổng AI không hoàn tất xử lý Cloud."),
            r"MASK_HTTP_[1-5][0-9]{2}": (
                TrangThaiEngine.CHO, "AI_MASK_KHONG_GUI", "Cổng Mask chưa cho phép gửi yêu cầu."),
        }
        self.assertEqual(dict(BANG_ANH_XA_MAU_LY_DO_AI), mong_doi)
        for tien_to, mau in (("CLOUD", r"CLOUD_HTTP_[1-5][0-9]{2}"),
                              ("MASK", r"MASK_HTTP_[1-5][0-9]{2}")):
            for http in (400, 401, 429, 500, 503):
                with self.subTest(tien_to=tien_to, http=http):
                    dto = replace(AI_RA, muc="DO", truong={}, duong="KHONG",
                                  ly_do=(f"{tien_to}_HTTP_{http}",), thong_bao=BI_MAT)
                    tt, ma, ly_do = mong_doi[mau]
                    kq = kiem_tra_mau_engine(self, EngineAI(CongAIGia(dto)),
                                            MauEngine(AI_VAO, tt, ma, ly_do, dto))
                    self.assertIs(kq.du_lieu, dto)
                    self.assertNotIn(BI_MAT, kq.ly_do)

    def test_nhieu_ly_do_cung_trang_thai_co_uu_tien_on_dinh(self):
        for cac_ma, ma_ra in (
            (("LOCAL_TAT", "LOCAL_KHONG_CHAY", "CLOUD_TAT"), "AI_LOCAL_CHUA_SAN"),
            (("LOCAL_LOI", "CLOUD_LOI", "MASK_MO_CHE_LOI"), "AI_LOCAL_LOI"),
        ):
            for ly_do in (cac_ma, tuple(reversed(cac_ma))):
                with self.subTest(ly_do=ly_do):
                    dto = replace(AI_RA, muc="DO", truong={}, duong="KHONG", ly_do=ly_do)
                    kq = EngineAI(CongAIGia(dto)).chay(AI_VAO)
                    self.assertEqual(kq.ma, ma_ra)
                    self.assertIs(kq.du_lieu, dto)

    def test_ket_qua_co_truong_khong_bi_ha_trang_thai_vi_ly_do(self):
        for ma in BANG_ANH_XA_LY_DO_AI:
            with self.subTest(ma=ma):
                dto = replace(AI_RA, ly_do=(ma,))
                kq = EngineAI(CongAIGia(dto)).chay(AI_VAO)
                self.assertEqual(kq.trang_thai, TrangThaiEngine.XONG)
                self.assertIs(kq.du_lieu, dto)
        for ma in ("CLOUD_HTTP_500", "MASK_HTTP_503"):
            with self.subTest(ma=ma):
                dto = replace(AI_RA, ly_do=(ma,))
                kq = EngineAI(CongAIGia(dto)).chay(AI_VAO)
                self.assertEqual(kq.trang_thai, TrangThaiEngine.XONG)
                self.assertIs(kq.du_lieu, dto)

    def test_khong_phat_minh_loi_cho_ket_qua_binh_thuong_khong_co_truong(self):
        for ly_do in (("KHONG_CO_TRUONG",), ("THIEU_TRICH_DAN", "DUOI_NGUONG"),
                      ("MA_CHUA_KHAI_BAO",), ("CLOUD_HTTP_500_" + BI_MAT,),
                      ("MASK_MA_LA",)):
            with self.subTest(ly_do=ly_do):
                dto = replace(AI_RA, muc="DO", truong={}, duong="KHONG", ly_do=ly_do)
                kq = EngineAI(CongAIGia(dto)).chay(AI_VAO)
                self.assertEqual(kq.trang_thai, TrangThaiEngine.XONG)
                self.assertIs(kq.du_lieu, dto)

    def test_bang_anh_xa_cong_khai_khong_the_sua(self):
        for bang in (BANG_ANH_XA_LOI_OCR, BANG_ANH_XA_NGOAI_LE_AI,
                     BANG_ANH_XA_LY_DO_AI, BANG_ANH_XA_MAU_LY_DO_AI):
            with self.subTest(bang=tuple(bang)), self.assertRaises(TypeError):
                bang[next(iter(bang))] = (TrangThaiEngine.XONG, "SAI", "Sai.")


class GoiCongTests(unittest.TestCase):
    def test_ocr_dung_mot_loi_goi_bytes_va_duoi_nguyen_ven(self):
        cong = CongOCRGia()
        truc_tiep = cong.ocr(OCR_VAO.raw, OCR_VAO.duoi)
        cong.luot.clear()
        engine = EngineOCR(cong)
        kq = engine.chay(OCR_VAO)
        self.assertEqual(cong.luot, [(OCR_VAO.raw, ".PDF", None)])
        self.assertIs(kq.du_lieu, truc_tiep)
        self.assertEqual((engine.ma, engine.phien_ban, engine.khai_bao.dau_vao,
                          engine.khai_bao.dau_ra), ("E-OCR", "v1", DauVaoOCR, bytes))

    def test_ai_mot_loi_goi_khong_doi_loai_viec_va_giu_moi_truong(self):
        for duong in ("LOCAL", "CLOUD", "LOCAL+CLOUD"):
            with self.subTest(duong=duong):
                dto = replace(AI_RA, duong=duong, truong={
                    "lai_suat": replace(AI_RA.truong["lai_suat"], nguon="CLOUD", gia_tri_local="4%"),
                })
                cong = CongAIGia(dto)
                truc_tiep = cong.goi(AI_VAO)
                cong.luot.clear()
                truoc = deepcopy(AI_VAO)
                engine = EngineAI(cong)
                kq = engine.chay(AI_VAO)
                self.assertEqual(cong.luot, [(AI_VAO, None)])
                self.assertIs(cong.luot[0][0], AI_VAO)
                self.assertEqual(AI_VAO, truoc)
                self.assertEqual(cong.luot[0][0].loai_viec, "HOI_DAP_VAY")
                self.assertIs(kq.du_lieu, truc_tiep)
                self.assertEqual(hash_du_lieu(dto), hash_du_lieu(deepcopy(dto)))
                self.assertEqual((engine.ma, engine.phien_ban, engine.khai_bao.dau_vao,
                                  engine.khai_bao.dau_ra), ("E-AI", "v1", YeuCauAI, KetQuaAI))

    def test_sai_kieu_ra_la_loi_hop_dong(self):
        for engine, vao in ((EngineOCR(CongOCRGia("sai")), OCR_VAO),
                            (EngineAI(CongAIGia("sai")), AI_VAO)):
            with self.subTest(engine=engine.ma), self.assertRaises(ValueError):
                engine.chay(vao)

    def test_sai_kieu_vao_khong_goi_cong(self):
        for lop_engine, cong in ((EngineOCR, CongOCRGia()), (EngineAI, CongAIGia())):
            with self.subTest(engine=lop_engine), self.assertRaises(ValueError):
                lop_engine(cong).chay({})
            self.assertEqual(cong.luot, [])


class DangKyCongTests(unittest.TestCase):
    def test_chi_dang_ky_cong_truyen_vao(self):
        for ocr, ai in ((None, None), (CongOCRGia(), None),
                        (None, CongAIGia()), (CongOCRGia(), CongAIGia())):
            with self.subTest(ocr=ocr is not None, ai=ai is not None):
                db = DanhBaEngine()
                dang_ky_engine_cong(db, cong_ocr=ocr, cong_ai=ai)
                mong_doi = ({"E-OCR"} if ocr is not None else set()) | ({"E-AI"} if ai is not None else set())
                self.assertEqual({k.ma for k in db.liet_ke()}, mong_doi)
                if ocr is not None:
                    db.tra_cuu("E-OCR", "v1").chay(OCR_VAO)
                    self.assertEqual(len(ocr.luot), 1)
                if ai is not None:
                    db.tra_cuu("E-AI", "v1").chay(AI_VAO)
                    self.assertEqual(len(ai.luot), 1)

    def test_dang_ky_trung_bi_tu_choi_va_giu_engine_cu(self):
        for ten, cong in (("cong_ocr", CongOCRGia()), ("cong_ai", CongAIGia())):
            with self.subTest(ten=ten):
                db = DanhBaEngine()
                dang_ky_engine_cong(db, **{ten: cong})
                truoc = db.liet_ke()
                engine_cu = db.tra_cuu(truoc[0].ma, "v1")
                with self.assertRaises(ValueError):
                    dang_ky_engine_cong(db, **{ten: cong})
                self.assertEqual(db.liet_ke(), truoc)
                self.assertIs(db.tra_cuu(truoc[0].ma, "v1"), engine_cu)


if __name__ == "__main__":
    unittest.main()
