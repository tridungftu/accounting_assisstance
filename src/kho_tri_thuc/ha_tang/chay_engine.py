"""XS-2b: worker chủ động gọi, chưa nối vào server hay tự khởi động.

``mo_giao_dich()`` là context manager do máy chủ cấp: mỗi lần gọi dùng một
kết nối/giao dịch ngắn độc lập, cùng danh tính app_web đã xác thực, commit
khi thoát bình thường và rollback khi có lỗi. Phải dùng được ở luồng gia hạn;
không chia sẻ kết nối/transaction đang mở giữa các luồng.

Module đăng ký callback nạp đầu vào và lưu TOÀN BỘ KetQuaEngine (kể cả bằng
chứng, CHO/LOI). Callback chỉ thao tác PG trên conn được cấp, không tự commit
hay thực hiện tác động ngoài. Worker không biết bảng module. Lưu + CAS cùng
giao dịch; CAS thất bại rollback cả kết quả. SQL quyết định retry/giới hạn.

Các bước hợp tác: nạp → engine.chay → lưu. Không ngắt cưỡng bức một lời gọi
engine đang chạy; yêu cầu dừng được kiểm ở ranh giới bước. Mất lease/lỗi gia
hạn thì không lưu kết quả. Tác động ngoài không có bảo đảm exactly-once;
ngoại lệ không rõ sau khi bắt đầu engine có tác động ngoài giữ CHUA_RO.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import re
from threading import Event, Thread
from typing import Any, Callable, ContextManager
from uuid import UUID, uuid4

from kho_tri_thuc.ha_tang import hang_viec as hv
from kho_tri_thuc.ha_tang.danh_ba_engine import DanhBaEngine
from kho_tri_thuc.ha_tang.engine import KetQuaEngine, TrangThaiEngine


LOG = logging.getLogger(__name__)


class _MatLease(Exception):
    pass


class _DungHopTac(Exception):
    pass


@dataclass(frozen=True)
class _DangKy:
    ma_engine: str
    phien_ban_engine: str
    nap: Callable[[Any, dict], Any]
    luu: Callable[[Any, dict, KetQuaEngine], UUID]


class ChayEngine:
    def __init__(self, danh_ba: DanhBaEngine,
                 mo_giao_dich: Callable[[], ContextManager], *,
                 phap_nhan_id: UUID, module: str, worker_id: UUID | None = None,
                 lease_giay: int = 120, gia_han_giay: float | None = None):
        if type(lease_giay) is not int or not 1 <= lease_giay <= 3600:
            raise ValueError('Lease phải từ 1 đến 3600 giây.')
        nhip = lease_giay / 3 if gia_han_giay is None else gia_han_giay
        if not isinstance(nhip, (int, float)) or not math.isfinite(nhip) or not 0 < nhip < lease_giay:
            raise ValueError('Nhịp gia hạn phải dương và ngắn hơn lease.')
        self.danh_ba = danh_ba
        self.mo_giao_dich = mo_giao_dich
        self.pn = phap_nhan_id
        self.module = module
        self.worker_id = worker_id or uuid4()
        self.lease_giay = lease_giay
        self.gia_han_giay = nhip
        self._dang_ky: dict[tuple[str, int], _DangKy] = {}

    def dang_ky(self, loai: str, phien_ban: int, *, ma_engine: str,
                phien_ban_engine: str, nap_dau_vao: Callable,
                luu_ket_qua: Callable) -> None:
        """Cấu hình trước khi chạy; ánh xạ version SQL int → version engine str.

        Không suy 'v1' từ 1 hoặc chọn bản mới nhất. Không cho ghi đè đăng ký.
        ``luu_ket_qua(conn, viec, ket_qua)`` trả UUID bằng chứng/kết quả; hàng
        việc chỉ giữ UUID đó khi XONG, còn CHO/LOI giữ mã lý do trung tính.
        """
        if type(phien_ban) is not int or phien_ban < 1:
            raise ValueError('Phiên bản việc phải là số nguyên dương.')
        key = (loai, phien_ban)
        if key in self._dang_ky or not callable(nap_dau_vao) or not callable(luu_ket_qua):
            raise ValueError('Đăng ký trùng hoặc callback không hợp lệ.')
        self.danh_ba.tra_cuu(ma_engine, phien_ban_engine)
        self._dang_ky[key] = _DangKy(ma_engine, phien_ban_engine, nap_dau_vao, luu_ket_qua)

    def _args(self, viec):
        return (viec['id'], self.worker_id, viec['lease_token'])

    def _kiem(self, conn, viec, mat_lease):
        if mat_lease.is_set():
            raise _MatLease
        tt = hv.trang_thai_lease(conn, *self._args(viec), phap_nhan_id=self.pn)
        if not tt['con_giu']:
            mat_lease.set()
            raise _MatLease
        if tt['yeu_cau_dung']:
            raise _DungHopTac

    def _nhip(self, viec, xong, mat_lease):
        while not xong.wait(self.gia_han_giay):
            try:
                with self.mo_giao_dich() as conn:
                    ok = hv.gia_han(conn, *self._args(viec), phap_nhan_id=self.pn,
                                    lease_giay=self.lease_giay)
                if not ok:
                    mat_lease.set()
                    return
            except Exception:
                mat_lease.set()
                LOG.error('WORKER_GIA_HAN_LOI')
                return

    def _dong(self, viec, trang_thai, ma_loi, mat_lease):
        """Đóng lỗi/dừng; không bao giờ ghi khi không còn giữ lease."""
        if mat_lease.is_set():
            return
        with self.mo_giao_dich() as conn:
            tt = hv.trang_thai_lease(conn, *self._args(viec), phap_nhan_id=self.pn)
            if not tt['con_giu']:
                return
            # Tác động ngoài không rõ phải giữ CHUA_RO dù có yêu cầu dừng.
            if tt['yeu_cau_dung'] and trang_thai != 'CHUA_RO':
                trang_thai, ma_loi = 'DA_DUNG', None
            if not hv.ket_thuc(conn, *self._args(viec), trang_thai,
                              phap_nhan_id=self.pn, ma_loi=ma_loi):
                LOG.warning('WORKER_MAT_LEASE')

    def chay_mot(self) -> bool:
        """Nhận/chạy tối đa một việc; False = SQL không giao việc.

        True chỉ nghĩa đã nhận, không khẳng định XONG. Lỗi hạ tầng khi nhận
        hoặc đóng lỗi truyền ra caller; lỗi engine/callback ghi mã cố định
        và log mã, không log nội dung ngoại lệ/tham chiếu/kết quả.
        """
        with self.mo_giao_dich() as conn:
            viec = hv.nhan(conn, self.worker_id, phap_nhan_id=self.pn,
                           module=self.module, lease_giay=self.lease_giay)
        if viec is None:
            return False
        xong, mat_lease = Event(), Event()
        nhip = Thread(target=self._nhip, args=(viec, xong, mat_lease), daemon=True)
        nhip.start()
        da_goi_engine = False
        try:
            with self.mo_giao_dich() as conn:
                self._kiem(conn, viec, mat_lease)
                dk = self._dang_ky[(viec['loai'], viec['phien_ban'])]
                engine = self.danh_ba.tra_cuu(dk.ma_engine, dk.phien_ban_engine)
                dau_vao = dk.nap(conn, dict(viec))
            with self.mo_giao_dich() as conn:
                self._kiem(conn, viec, mat_lease)
                if not hv.tien_do(conn, *self._args(viec), 10, phap_nhan_id=self.pn):
                    raise _MatLease
            da_goi_engine = True
            ket_qua = engine.chay(dau_vao)  # Không giữ giao dịch trong lời gọi engine.
            with self.mo_giao_dich() as conn:
                self._kiem(conn, viec, mat_lease)
                ket_qua_id = dk.luu(conn, dict(viec), ket_qua)
                if not isinstance(ket_qua_id, UUID):
                    raise ValueError('Callback lưu phải trả UUID.')
                self._kiem(conn, viec, mat_lease)
                ma = ket_qua.ma
                if not re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', ma):
                    ma = 'ENGINE_MA_KHONG_HOP_LE'
                if ket_qua.trang_thai == TrangThaiEngine.LOI:
                    ok = hv.thu_lai(conn, *self._args(viec), ma, phap_nhan_id=self.pn)
                else:
                    ok = hv.ket_thuc(
                        conn, *self._args(viec), ket_qua.trang_thai.value,
                        phap_nhan_id=self.pn,
                        ket_qua_id=ket_qua_id if ket_qua.trang_thai == TrangThaiEngine.XONG else None,
                        ma_loi=ma if ket_qua.trang_thai == TrangThaiEngine.CHO else None)
                if not ok:
                    raise _MatLease  # Rollback cả callback lưu và bằng chứng.
        except _MatLease:
            LOG.warning('WORKER_MAT_LEASE')
        except _DungHopTac:
            self._dong(viec, 'DA_DUNG', None, mat_lease)
        except Exception:
            LOG.error('WORKER_NGOAI_LE')
            tt = 'CHUA_RO' if da_goi_engine and viec['co_tac_dong_ngoai'] else 'LOI'
            self._dong(viec, tt, 'WORKER_NGOAI_LE', mat_lease)
        finally:
            xong.set()
            nhip.join()
        return True

    def chay(self, dung: Event, *, cho_giay: float = 1) -> None:
        """Poll đến khi caller đặt Event; việc đã nhận chạy nốt theo S4."""
        if not math.isfinite(cho_giay) or cho_giay <= 0:
            raise ValueError('Thời gian poll phải dương.')
        while not dung.is_set():
            if not self.chay_mot():
                dung.wait(cho_giay)
