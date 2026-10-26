"""XS-3A: mẫu giả độc lập; không DB, file tạm, mạng hay xóa file.

Lát sau dùng lại ``BoTestHopDongEngine`` cùng unittest.TestCase, cung cấp
``tao_engine()`` và ``cac_mau`` (tuple MauEngine). Hoặc gọi trực tiếp
``kiem_tra_mau_engine(self, engine, mau)`` trong bộ test riêng. Fixture phải
giả và đủ điều kiện chạy độc lập; khung kiểm cả kết quả mong đợi, bằng chứng,
tính lặp lại và việc giữ nguyên đầu vào, không chỉ kiểm hình dạng DTO.
"""

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
import unittest

from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import (
    Engine, KhaiBaoEngine, KetQuaEngine, KetQuaXuLy, TrangThaiEngine, hash_du_lieu,
)


_LUC = datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class MauEngine:
    dau_vao: Any
    trang_thai: TrangThaiEngine
    ma: str
    ly_do: str
    du_lieu: Any = None


def kiem_tra_mau_engine(test: unittest.TestCase, engine: Engine,
                       mau: MauEngine) -> KetQuaEngine:
    """Chạy một fixture và kiểm hợp đồng; không phụ thuộc engine cụ thể."""
    dau_vao = deepcopy(mau.dau_vao)
    ket_qua = engine.chay(dau_vao, thoi_diem=_LUC)
    test.assertIsInstance(ket_qua, KetQuaEngine)
    test.assertEqual(ket_qua.trang_thai, mau.trang_thai)
    test.assertEqual(ket_qua.ma, mau.ma)
    test.assertEqual(ket_qua.ly_do, mau.ly_do)
    test.assertEqual(ket_qua.du_lieu, mau.du_lieu)
    test.assertEqual(dau_vao, mau.dau_vao)
    bc = ket_qua.bang_chung
    test.assertEqual((bc.ma_engine, bc.phien_ban_engine), (engine.ma, engine.phien_ban))
    test.assertEqual(bc.hash_vao, hash_du_lieu(mau.dau_vao))
    test.assertEqual(bc.hash_ra, hash_du_lieu({
        "trang_thai": mau.trang_thai.value, "ma": mau.ma,
        "ly_do": mau.ly_do, "du_lieu": mau.du_lieu,
    }))
    test.assertEqual(bc.thoi_diem, _LUC)
    test.assertRegex(bc.hash_vao, r"^[0-9a-f]{64}$")
    test.assertRegex(bc.hash_ra, r"^[0-9a-f]{64}$")
    test.assertEqual(ket_qua, engine.chay(deepcopy(mau.dau_vao), thoi_diem=_LUC))
    return ket_qua


class BoTestHopDongEngine:
    """Mixin dùng lại: engine giả hoặc wrapper thật với cổng được giả lập.

    Chạy bằng runner unittest hiện có. Không là TestCase độc lập nên runner
    không thu thập lớp chưa có fixture; subclass phải cung cấp ít nhất một mẫu.
    """

    def tao_engine(self) -> Engine:
        raise NotImplementedError

    cac_mau: tuple[MauEngine, ...] = ()

    def test_hop_dong_cac_mau(self):
        self.assertTrue(self.cac_mau, "Cần ít nhất một fixture giả có kết quả mong đợi.")
        engine = self.tao_engine()
        for i, mau in enumerate(self.cac_mau):
            with self.subTest(mau=i, trang_thai=mau.trang_thai):
                kiem_tra_mau_engine(self, engine, mau)


class EngineGia(Engine):
    def __init__(self, ma="E-DEMO", phien_ban="v1"):
        super().__init__(KhaiBaoEngine(ma, phien_ban, dict, dict))

    def xu_ly(self, dau_vao):
        if dau_vao.get("sai"):
            return KetQuaXuLy(TrangThaiEngine.LOI, "DU_LIEU_SAI",
                              "Dữ liệu chưa đúng định dạng.")
        if "so" not in dau_vao:
            return KetQuaXuLy(TrangThaiEngine.CHO, "THIEU_DU_LIEU_M2",
                              "Chờ dữ liệu từ module M2.")
        return KetQuaXuLy(TrangThaiEngine.XONG, "DA_XU_LY",
                          "Đã xử lý dữ liệu.", {"tong": dau_vao["so"] + 1})


class EngineGiaHopDongTests(BoTestHopDongEngine, unittest.TestCase):
    cac_mau = (
        MauEngine({"so": 2}, TrangThaiEngine.XONG, "DA_XU_LY",
                  "Đã xử lý dữ liệu.", {"tong": 3}),
        MauEngine({}, TrangThaiEngine.CHO, "THIEU_DU_LIEU_M2",
                  "Chờ dữ liệu từ module M2."),
        MauEngine({"sai": True}, TrangThaiEngine.LOI, "DU_LIEU_SAI",
                  "Dữ liệu chưa đúng định dạng."),
    )

    def tao_engine(self):
        return EngineGia()


class HopDongEngineTests(unittest.TestCase):
    def test_cho_la_ket_qua_hop_le_co_ma(self):
        kq = EngineGia().chay({})
        self.assertEqual(kq.trang_thai, TrangThaiEngine.CHO)
        self.assertEqual(kq.ma, "THIEU_DU_LIEU_M2")
        self.assertIsNone(kq.du_lieu)

    def test_hash_khong_phu_thuoc_thu_tu_khoa(self):
        engine = EngineGia()
        a = engine.chay({"so": 2, "nguon": {"b": 2, "a": 1}}, thoi_diem=_LUC)
        b = engine.chay({"nguon": {"a": 1, "b": 2}, "so": 2}, thoi_diem=_LUC)
        self.assertEqual(a, b)

    def test_hash_doi_khi_dau_vao_hoac_dau_ra_doi(self):
        a = EngineGia().chay({"so": 2}, thoi_diem=_LUC)
        b = EngineGia().chay({"so": 3}, thoi_diem=_LUC)
        self.assertNotEqual(a.bang_chung.hash_vao, b.bang_chung.hash_vao)
        self.assertNotEqual(a.bang_chung.hash_ra, b.bang_chung.hash_ra)

    def test_hash_ra_phan_biet_cho_va_loi_khong_co_du_lieu(self):
        cho = EngineGia().chay({})
        loi = EngineGia().chay({"sai": True})
        self.assertNotEqual(cho.bang_chung.hash_ra, loi.bang_chung.hash_ra)

    def test_thoi_diem_va_version_khong_lam_doi_hash_noi_dung(self):
        a = EngineGia().chay({"so": 2}, thoi_diem=_LUC)
        b = EngineGia(phien_ban="v2").chay({"so": 2}, thoi_diem=_LUC + timedelta(days=1))
        self.assertEqual(a.bang_chung.hash_vao, b.bang_chung.hash_vao)
        self.assertEqual(a.bang_chung.hash_ra, b.bang_chung.hash_ra)
        self.assertNotEqual(a.bang_chung, b.bang_chung)

    def test_thoi_diem_mac_dinh_va_chuan_hoa_utc(self):
        truoc = datetime.now(timezone.utc)
        bc = EngineGia().chay({}).bang_chung
        self.assertLessEqual(truoc, bc.thoi_diem)
        self.assertLessEqual(bc.thoi_diem, datetime.now(timezone.utc))
        gio_vn = _LUC.astimezone(timezone(timedelta(hours=7)))
        self.assertEqual(EngineGia().chay({}, thoi_diem=gio_vn).bang_chung.thoi_diem, _LUC)
        with self.assertRaises(ValueError):
            EngineGia().chay({}, thoi_diem=datetime(2026, 10, 26))

    def test_khai_bao_va_ly_do_khong_hop_le(self):
        for ma, version, vao, ra in (
            ("", "v1", dict, dict), ("E-DEMO", " ", dict, dict),
            ("E-DEMO", "v1", "dict", dict), ("E-DEMO", "v1", Any, dict),
        ):
            with self.subTest(ma=ma, version=version, vao=vao), self.assertRaises(ValueError):
                KhaiBaoEngine(ma, version, vao, ra)
        for tt, ma, ly_do in (
            ("KHAC", "CHO", "Chờ dữ liệu."), ("CHO", "", "Chờ dữ liệu."),
            ("LOI", "ma sai", "Dữ liệu chưa hợp lệ."), ("XONG", "OK", " "),
        ):
            with self.subTest(tt=tt, ma=ma), self.assertRaises(ValueError):
                KetQuaXuLy(tt, ma, ly_do)

    def test_sai_kieu_dau_vao_bi_chan_truoc_xu_ly(self):
        with self.assertRaises(ValueError):
            EngineGia().chay([])

    def test_sai_kieu_ket_qua_va_dau_ra_bi_chan(self):
        class EngineSai(EngineGia):
            def __init__(self, ket_qua):
                super().__init__()
                self.ket_qua = ket_qua

            def xu_ly(self, dau_vao):
                return self.ket_qua

        with self.assertRaisesRegex(ValueError, "phải trả KetQuaXuLy"):
            EngineSai("khong_phai_dto").chay({})
        for sai in (KetQuaXuLy("XONG", "OK", "Đã xử lý.", []),
                    KetQuaXuLy("CHO", "CHO_DU_LIEU", "Chờ dữ liệu.", []),
                    KetQuaXuLy("LOI", "SAI", "Dữ liệu chưa hợp lệ.", [])):
            with self.subTest(sai=sai), self.assertRaisesRegex(ValueError, "Đầu ra"):
                EngineSai(sai).chay({})

    def test_sua_dau_vao_bi_phat_hien(self):
        class EngineSua(EngineGia):
            def xu_ly(self, dau_vao):
                dau_vao["sua"] = True
                return super().xu_ly(dau_vao)

        with self.assertRaisesRegex(ValueError, "không được sửa đầu vào"):
            EngineSua().chay({})

    def test_khong_che_ngoai_le_lap_trinh(self):
        class EngineHong(EngineGia):
            def xu_ly(self, dau_vao):
                raise RuntimeError("Lỗi giả lập")

        with self.assertRaises(RuntimeError):
            EngineHong().chay({})

    def test_hash_kieu_thuan_va_khong_lan_kieu(self):
        @dataclass(frozen=True)
        class DauVaoGia:
            ngay: date
            tien: Decimal
            tep: bytes

        dau_vao = DauVaoGia(date(2026, 10, 26), Decimal("1234.50"), b"DEMO")
        self.assertEqual(hash_du_lieu(dau_vao), hash_du_lieu(deepcopy(dau_vao)))
        values = [None, True, 1, 1.0, "1", b"1", Decimal("1"), [1], (1,),
                  {"a": 1}, date(2026, 10, 26), _LUC]
        self.assertEqual(len({hash_du_lieu(v) for v in values}), len(values))
        for sai in (float("nan"), float("inf"), Decimal("NaN"),
                    Decimal("Infinity"), {1: "khóa không phải str"}, object()):
            with self.subTest(kieu=type(sai)), self.assertRaises(ValueError):
                hash_du_lieu(sai)

    def test_khung_mau_phat_hien_bang_chung_sai(self):
        class EngineBangChungSai(EngineGia):
            def chay(self, *args, **kwargs):
                kq = super().chay(*args, **kwargs)
                return replace(kq, bang_chung=replace(kq.bang_chung, hash_vao="0" * 64))

        with self.assertRaises(AssertionError):
            kiem_tra_mau_engine(self, EngineBangChungSai(), EngineGiaHopDongTests.cac_mau[0])


class DanhBaEngineTests(unittest.TestCase):
    def test_dang_ky_tra_cuu_va_liet_ke(self):
        db = DanhBaEngine()
        self.assertEqual(db.liet_ke(), ())
        b, a = EngineGia("E-B"), EngineGia("E-A")
        db.dang_ky(b)
        db.dang_ky(a)
        self.assertIs(db.tra_cuu("E-A", "v1"), a)
        self.assertEqual(db.liet_ke(), (a.khai_bao, b.khai_bao))

    def test_trung_bi_tu_choi_ke_ca_co_co_phien_ban_moi(self):
        db = DanhBaEngine()
        engine = EngineGia()
        db.dang_ky(engine)
        for trung in (engine, EngineGia()):
            for co in (False, True):
                with self.subTest(co=co), self.assertRaises(ValueError):
                    db.dang_ky(trung, phien_ban_moi=co)
        self.assertEqual(db.liet_ke(), (engine.khai_bao,))

    def test_version_khac_can_tuong_minh_va_giu_ban_cu(self):
        db = DanhBaEngine()
        v1, v2 = EngineGia(), EngineGia(phien_ban="v2")
        db.dang_ky(v1)
        with self.assertRaises(ValueError):
            db.dang_ky(v2)
        self.assertEqual(db.liet_ke(), (v1.khai_bao,))
        db.dang_ky(v2, phien_ban_moi=True)
        self.assertIs(db.tra_cuu("E-DEMO", "v1"), v1)
        self.assertIs(db.tra_cuu("E-DEMO", "v2"), v2)
        self.assertEqual(db.liet_ke(), (v1.khai_bao, v2.khai_bao))
        with self.assertRaises(KeyError):
            db.tra_cuu("E-DEMO", "v3")

    def test_khong_nhan_co_truthy_thay_cho_bool(self):
        with self.assertRaises(ValueError):
            DanhBaEngine().dang_ky(EngineGia(), phien_ban_moi="true")

    def test_danh_ba_khong_dung_chung_trang_thai(self):
        a, b = DanhBaEngine(), DanhBaEngine()
        a.dang_ky(EngineGia())
        self.assertEqual(b.liet_ke(), ())
        with self.assertRaises(KeyError):
            b.tra_cuu("E-DEMO", "v1")


if __name__ == "__main__":
    unittest.main()
