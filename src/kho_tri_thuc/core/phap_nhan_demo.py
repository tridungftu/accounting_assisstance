"""Cờ DEMO và phạm vi báo cáo; kết nối/transaction thuộc caller.

``pham_vi`` dùng RLS hiện hành (``mtq.dat_ngu_canh`` trong transaction).
Chỉ ``gom_demo=True`` mới chọn DEMO; hàm không mở rộng pháp nhân được cấp.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import UUID

from .mtq import _ma
from .tiep_nhan import _tx


class LoiPhapNhanDemo(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        self.http_status = (403 if ma == 'DEMO_CHI_ADMIN' else
                            409 if ma in {'DEMO_CAS', 'DEMO_DA_CO_DU_LIEU'} else 400)
        super().__init__('Thao tác pháp nhân DEMO thất bại (' + ma + ')')


_LOI = frozenset({'DEMO_CHI_ADMIN', 'DEMO_CAS', 'DEMO_DA_CO_DU_LIEU',
                 'DEMO_LIEN_KET_CHEO', 'DEMO_PHAP_NHAN', 'DEMO_DAU_VAO',
                 'DEMO_CAN_READ_COMMITTED', 'DEMO_SCHEMA_CHUA_BAO_VE'})


def _goi(conn, sql, tham_so, *, nhieu=False):
    ma_loi = 'DEMO_THAT_BAI'
    try:
        cursor = conn.execute(sql, tham_so)
        return cursor.fetchall() if nhieu else cursor.fetchone()[0]
    except Exception as exc:
        ma = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(ma, str) and ma in _LOI:
            ma_loi = ma
    tham_so = None
    raise LoiPhapNhanDemo(ma_loi)


def nhan_hien_thi(la_demo: bool) -> str:
    if type(la_demo) is not bool:
        raise ValueError('Cờ DEMO phải là boolean')
    return 'DEMO' if la_demo else ''


@dataclass(frozen=True)
class PhapNhanPhamVi:
    id: UUID
    ma: str
    ten: str
    la_demo: bool
    row_version: str

    @property
    def nhan(self) -> str:
        return nhan_hien_thi(self.la_demo)


def dat_demo(conn, *, ma, phap_nhan_id, la_demo: bool, row_version: str, request_id):
    _tx(conn)
    if type(la_demo) is not bool:
        raise ValueError('Cờ DEMO phải là boolean')
    if (not isinstance(row_version, str) or not re.fullmatch('[1-9][0-9]{0,18}', row_version)
            or int(row_version) > 9223372036854775807):
        raise ValueError('Cần row_version nguyên dương dạng chuỗi')
    return _goi(conn, 'SELECT loi.phap_nhan_dat_demo(%s,%s,%s,%s,%s)',
                (_ma(ma), UUID(str(phap_nhan_id)), la_demo, int(row_version), UUID(str(request_id))))


def pham_vi(conn, *, gom_demo: bool = False) -> list[PhapNhanPhamVi]:
    _tx(conn)
    if type(gom_demo) is not bool:
        raise ValueError('Cờ gồm DEMO phải là boolean')
    rows = _goi(conn, '''SELECT id,ma,ten,la_demo,phien_ban_dong::text
        FROM loi.phap_nhan_pham_vi(%s) ORDER BY ma,id''', (gom_demo,), nhieu=True)
    return [PhapNhanPhamVi(*row) for row in rows]
