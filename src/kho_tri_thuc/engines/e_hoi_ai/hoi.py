"""AI-2: adapter hoi_ai.v1 qua CongAI.goi, cấu hình riêng từng request.

Core tiêm bộ kiểm schema offline (cùng chữ ký KiemSchema.kiem), metadata
nguồn đã xác thực và seam tra lượt che. Không đọc cấu hình/khóa từ đĩa/env.
Việc nối e_mask, cấp bí mật và vòng đời tiến trình thuộc AI-3/4b/5b.
"""

from copy import copy, deepcopy

from ...tri_thuc.cong_ai import CongAI, loai_viec
from .dto import YeuCauAI


HOI = 'urn:ktt:contract:hoi_ai.v1'
TRA_LOI = 'urn:ktt:contract:tra_loi_ai.v1'
CHUNG = 'urn:ktt:contract:chung.v1#/$defs/'


class _BoGhiTheoRequest:
    """Giữ metadata của đúng request; nhật ký/thống kê vẫn do Core quản lý."""

    def __init__(self, bo_ghi):
        self.goc = bo_ghi
        self.ban_ghi = []

    def ghi(self, ban_ghi):
        self.ban_ghi.append(ban_ghi)
        self.goc.ghi(ban_ghi)

    def thong_ke(self, cua_so):
        return self.goc.thong_ke(cua_so)


class AdapterHoiAI:
    def __init__(self, cong_ai, *, kiem_schema, tham_chieu_luot_che=None):
        """kiem_schema(schema, value) -> bool, bắt buộc do Core cấp.

        tham_chieu_luot_che(ma_luot, phap_nhan_id=..., viec_id=...) phải
        xác minh lượt che đúng việc/pháp nhân, còn hạn rồi trả UUID Core.
        Không có seam này thì không trả được kết quả có trường Cloud.
        """
        if not isinstance(cong_ai, CongAI) or not callable(kiem_schema):
            raise TypeError('Cần CongAI và bộ kiểm schema của Core.')
        if cong_ai._moi_truong is None or cong_ai._mask is None:
            raise ValueError('Cần mapping bí mật RAM và Mask được tiêm sẵn.')
        if tham_chieu_luot_che is not None and not callable(tham_chieu_luot_che):
            raise TypeError('Cần seam tham chiếu lượt che của Core.')
        self._cong = cong_ai
        self._kiem_schema = kiem_schema
        self._tham_chieu_luot_che = tham_chieu_luot_che

    def _kiem(self, ref, value):
        if not self._kiem_schema({'$ref': ref}, value):
            # Không phản chiếu văn bản/định danh vào lỗi.
            raise ValueError('Dữ liệu không đạt schema ' + ref.split('#')[0])

    def goi(self, dau_vao, *, revision, nguon_tep_ids, vi_tri,
            phap_nhan_id=None, viec_id=None, de_xuat_id=None, kiem_tra=None):
        """Metadata keyword chỉ nhận từ Core, không lấy từ payload module.

        vi_tri định vị phần văn bản đầu vào trong tệp nguồn. Không tự tạo
        trang/bbox hay câu trả lời tự do từ kết quả theo trường của cổng.
        """
        dau_vao = deepcopy(dau_vao)
        self._kiem(HOI, dau_vao)
        loai_viec(dau_vao['loai_viec'])
        vo = dict(contract='tra_loi_ai.v1', phien_ban='1.0.0',
                  revision=revision, nguon_tep_ids=deepcopy(nguon_tep_ids))
        vi_tri = deepcopy(vi_tri)
        self._kiem(CHUNG + 'vo_noi_dung', vo)
        self._kiem(CHUNG + 'vi_tri', vi_tri)
        if vi_tri['tep_id'] not in vo['nguon_tep_ids']:
            raise ValueError('Vị trí dẫn chứng phải thuộc tệp nguồn Core cấp.')
        for value in (phap_nhan_id, viec_id, de_xuat_id):
            if value is not None:
                self._kiem(CHUNG + 'id', value)
        yc = YeuCauAI(
            dau_vao['loai_viec'], dau_vao['van_ban'], dau_vao['chi_dan'],
            tuple(dau_vao.get('truong', [])),
            tuple(tuple(item) if isinstance(item, list) else item
                  for item in dau_vao.get('dinh_danh_da_biet', [])),
            phap_nhan_id, viec_id, de_xuat_id)

        # CongAI không có trạng thái lượt gọi ngoài cấu hình/client/bộ ghi.
        # Copy instance giữ nguyên seam và thuật toán, không ghi instance chung.
        cong = copy(self._cong)
        cong.cai_dat = deepcopy(self._cong.cai_dat)
        cong.local_ai = deepcopy(self._cong.local_ai)
        if dau_vao.get('chi_cuc_bo', False):
            cong.cai_dat['cloud_bat'] = False
        nhat_ky = _BoGhiTheoRequest(self._cong.bo_ghi)
        cong.bo_ghi = nhat_ky
        kq = cong.goi(yc, kiem_tra=kiem_tra)

        def gia_tri(value):
            return {'kieu': 'van_ban', 'gia_tri': value}

        truong = []
        for item in kq.truong.values():
            if not item.trich_dan or item.trich_dan not in yc.van_ban:
                raise ValueError('Dẫn chứng không khớp văn bản nguồn.')
            truong.append(dict(
                ten=item.ten, gia_tri=gia_tri(item.gia_tri), nguon=item.nguon,
                gia_tri_local=(None if item.gia_tri_local is None
                               else gia_tri(item.gia_tri_local)),
                dan_chung=[dict(vi_tri=deepcopy(vi_tri), trich_dan=item.trich_dan)]))
        records = [r for r in nhat_ky.ban_ghi if r.ma_yeu_cau == kq.ma_yeu_cau]
        models = [dict(duong=r.duong, ten=r.model or None, phien_ban=None,
                       can_cu=('thuc_te' if r.duong == 'CLOUD' else 'cau_hinh')
                       if r.model else 'chua_co')
                  for r in records if r.da_gui]
        co_cloud = any(t['nguon'] == 'CLOUD' for t in truong)
        out = dict(vo, cau_tra_loi=None, truong=truong, duong=kq.duong,
                   mo_hinh=models, muc=kq.muc, thong_bao=kq.thong_bao,
                   ly_do=list(kq.ly_do), truong_bi_loai=list(kq.truong_bi_loai),
                   ma_yeu_cau_nguon=kq.ma_yeu_cau,
                   kiem_tra=dict(trich_dan='dat' if truong else 'chua_kiem',
                                 mo_che='khong_ap_dung'))
        cloud = [r for r in records if r.duong == 'CLOUD' and r.da_gui]
        if co_cloud:
            if self._tham_chieu_luot_che is None:
                raise ValueError('Cần Core xác minh tham chiếu lượt che.')
            out['luot_che_id'] = self._tham_chieu_luot_che(
                cloud[-1].ma_luot_mask, phap_nhan_id=phap_nhan_id, viec_id=viec_id)
            # Cổng chỉ giữ trường Cloud sau mở che + kiểm dẫn chứng thành công.
            out['kiem_tra']['mo_che'] = 'dat'
        elif cloud:
            # Model Cloud của lượt lỗi nằm trong nhật ký, không phải nguồn kết quả.
            out['mo_hinh'] = [m for m in models if m['duong'] == 'LOCAL']
            out['kiem_tra']['mo_che'] = 'khong_dat'
        self._kiem(TRA_LOI, out)
        return out
