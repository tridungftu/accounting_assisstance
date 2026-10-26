"""XS-2b: API mỏng trên M0060/M0061, không tự quản lý giao dịch.

Caller cấp kết nối đã đặt danh tính ứng dụng. PN/module phải do máy chủ
xác định qua quyền phiên, không lấy trực tiếp từ body client. Không ghi log
tham chiếu, kết quả hay thông điệp SQL. Lỗi SQL truyền về caller nguyên vẹn.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID


def _goi(conn, sql, params):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row['r'] if isinstance(row, Mapping) else row[0]


def tao_viec(conn, loai: str, phien_ban: int, khoa_dedupe: str,
             tham_chieu_id: UUID, *, phap_nhan_id: UUID, module: str,
             co_tac_dong_ngoai: bool = False, toi_da_lan_thu: int = 3,
             thu_lai_giay: int = 60, giu_ngay: int | None = None) -> UUID:
    """Tạo/dedupe trong giao dịch nghiệp vụ của caller; tuyệt đối không commit."""
    return _goi(conn, 'SELECT viec.tao(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS r',
                (phap_nhan_id, module, loai, phien_ban, khoa_dedupe, tham_chieu_id,
                 co_tac_dong_ngoai, toi_da_lan_thu, thu_lai_giay, giu_ngay))


def nhan(conn, worker_id: UUID, *, phap_nhan_id: UUID, module: str,
         lease_giay: int = 120) -> dict | None:
    """Tối đa một việc; JSON không phụ thuộc row_factory, token giữ nguyên."""
    with conn.cursor() as cur:
        cur.execute('SELECT to_jsonb(v) AS r FROM viec.nhan(%s,%s,%s,%s) v',
                    (phap_nhan_id, module, worker_id, lease_giay))
        row = cur.fetchone()
        if row is None:
            return None
        return row['r'] if isinstance(row, Mapping) else row[0]


def gia_han(conn, viec_id: UUID, worker_id: UUID, token: UUID, *,
            phap_nhan_id: UUID, lease_giay: int = 120) -> bool:
    return _goi(conn, 'SELECT viec.gia_han(%s,%s,%s,%s,%s) AS r',
                (phap_nhan_id, viec_id, worker_id, token, lease_giay))


def tien_do(conn, viec_id: UUID, worker_id: UUID, token: UUID, muc: int, *,
            phap_nhan_id: UUID) -> bool:
    return _goi(conn, 'SELECT viec.tien_do(%s,%s,%s,%s,%s) AS r',
                (phap_nhan_id, viec_id, worker_id, token, muc))


def ket_thuc(conn, viec_id: UUID, worker_id: UUID, token: UUID, trang_thai: str,
             *, phap_nhan_id: UUID, ket_qua_id: UUID | None = None,
             ma_loi: str | None = None) -> bool:
    return _goi(conn, 'SELECT viec.ket_thuc(%s,%s,%s,%s,%s,%s,%s) AS r',
                (phap_nhan_id, viec_id, worker_id, token, trang_thai, ket_qua_id, ma_loi))


def thu_lai(conn, viec_id: UUID, worker_id: UUID, token: UUID, ma_loi: str, *,
            phap_nhan_id: UUID) -> bool:
    """Chỉ dùng khi kết quả LOI chứng minh lần thử thất bại an toàn."""
    return _goi(conn, 'SELECT viec.thu_lai(%s,%s,%s,%s,%s) AS r',
                (phap_nhan_id, viec_id, worker_id, token, ma_loi))


def yeu_cau_dung(conn, viec_id: UUID, *, phap_nhan_id: UUID) -> bool:
    return _goi(conn, 'SELECT viec.yeu_cau_dung(%s,%s) AS r',
                (phap_nhan_id, viec_id))


def trang_thai_lease(conn, viec_id: UUID, worker_id: UUID, token: UUID, *,
                     phap_nhan_id: UUID) -> dict:
    return _goi(conn, 'SELECT viec.trang_thai_lease(%s,%s,%s,%s) AS r',
                (phap_nhan_id, viec_id, worker_id, token))
