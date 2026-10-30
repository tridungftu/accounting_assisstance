"""Bàn giao engine → Core; engine không gửi nguồn, phiên hay kết nối SQL.

G2-14/16/19 tiêm xac_minh_core để đối chiếu handle instance/lease đang sống.
Không có mặc định tin caller. engine_id ghim bản registry bất biến G2-05
(bao gồm so_phien_ban), không chọn bản engine mới nhất.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from . import tai_lieu
from .tep import _can_tx, LoiTep


@dataclass(frozen=True)
class NguonCore:
    module: str
    phap_nhan_id: UUID
    phien_ban_module: str
    engine_id: UUID
    ham: str
    phien_ban_ham: str
    viec_id: UUID
    the_he: int
    buoc_id: UUID
    lan_thu_id: UUID


class BanGiaoKetQua:
    def __init__(self, kho_tep, *, xac_minh_core):
        if not callable(xac_minh_core):
            raise ValueError('Cần cửa xác minh instance/lease của Core')
        self.kho_tep = kho_tep
        self._xac_minh = xac_minh_core

    def ghi(self, conn, *, giu_viec, tai_lieu_id, luong, ten, du_lieu,
            revision_tep_truoc, request_id, het_han_luc, **ctx):
        """Ghi tệp+kết quả trong tx caller; chưa cho engine giải phóng RAM.

        du_lieu chỉ là contract/trạng thái/revision và tham chiếu nguồn đầu vào.
        Không nhận tep_id đầu ra hay provenance từ engine. Core adapter truyền
        chính sách hết hạn đã duyệt; None dành cho kết quả không thuộc diện tạm.
        """
        _can_tx(conn)
        data = tai_lieu._truong(du_lieu, {'bien_the', 'ma_contract', 'phien_ban_contract',
            'trang_thai', 'ly_do', 'revision_truoc', 'nguon'}, {'goc_id'})
        source = self._xac_minh(conn, giu_viec)
        if (not isinstance(source, NguonCore) or source.module != ctx.get('module')
                or str(source.phap_nhan_id) != str(ctx.get('phap_nhan_id'))
                or type(source.the_he) is not int or source.the_he <= 0):
            raise ValueError('Nguồn Core không khớp ngữ cảnh đã xác minh')
        if any(k in ctx for k in ('viec_id', 'the_he')):
            raise ValueError('Việc phải lấy từ handle Core')
        for key in ('engine_id', 'viec_id', 'buoc_id', 'lan_thu_id'):
            UUID(str(getattr(source, key)))
        for key in ('phien_ban_module', 'ham', 'phien_ban_ham'):
            value = getattr(source, key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Thiếu phiên bản nguồn Core')
        ctx = {**ctx, 'viec_id': source.viec_id, 'the_he': source.the_he}
        with conn.transaction():
            ref = self.kho_tep.tai_len(conn, tai_lieu_id=tai_lieu_id, luong=luong, ten=ten,
                bien_the=data['bien_the'], revision_truoc=revision_tep_truoc,
                request_id=request_id, het_han_luc=het_han_luc, **ctx)
            core = {k: getattr(source, k) for k in ('phien_ban_module', 'engine_id', 'ham',
                'phien_ban_ham', 'buoc_id', 'lan_thu_id')}
            kq = tai_lieu.ghi_ket_qua_core(conn, tai_lieu_id=tai_lieu_id,
                du_lieu={**data, 'tep_id': ref['tep_id']}, thong_tin_core=core,
                request_id=request_id, **ctx)
        return dict(ket_qua_id=str(kq), tep=ref, da_ban_giao=False)

    def xac_nhan_da_commit(self, conn_doc, *, tai_lieu_id, ket_qua_id, bien_the, **ctx):
        """Gọi SAU commit bằng kết nối Core autocommit đang idle.

        Chỉ khi hàm này thành công mới ACK cho engine giải phóng RAM/drain.
        Không giữ ACK từ lời ghi trước commit. Không tự kết thúc việc/lease.
        """
        if not conn_doc.autocommit or conn_doc.info.transaction_status != 0:
            raise LoiTep('TEP_CAN_KET_NOI_DA_COMMIT')
        kid = str(UUID(str(ket_qua_id)))
        view = tai_lieu.lay(conn_doc, tai_lieu_id=tai_lieu_id, bien_the=bien_the, **ctx)
        for kq in view['ket_qua']:
            if kq['id'] == kid:
                with self.kho_tep.mo_doc(conn_doc, tai_lieu_id=tai_lieu_id, tep_id=kq['tep_id'],
                        bien_the=bien_the, **ctx):
                    return dict(ket_qua_id=kid, da_ban_giao=True)
        raise LoiTep('TEP_KHONG_THAY')
