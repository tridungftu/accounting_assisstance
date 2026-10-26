"""XS-4c1: dịch vụ công tắc M0056 và cổng kiểm tra trong giao dịch nghiệp vụ.

Công tắc không thay kiểm quyền MTQ/phạm vi. Không tự mở kết nối, ghi log
hay nhận danh tính từ body; dùng hạ tầng phiên do máy chủ truyền vào.
"""

from __future__ import annotations

import uuid

from ..ha_tang.primitives import DataError
from .crm_mau import _v


_CO_CAN = {'xem': 'cho_xem', 'ghi': 'cho_ghi',
           'xuat_ngoai': 'cho_xuat_ngoai', 'cong_bo': 'cong_bo_chinh_thuc'}
_THONG_BAO = {
    'MODULE_TAT': 'Chức năng này đang tạm tắt ở pháp nhân này.',
    'MODULE_CHI_NGUOI_THU': 'Chức năng đang chạy thử, chỉ người được chọn thử dùng được.',
    'MODULE_THU_KHONG_XUAT': 'Đang chạy thử nên chưa được xuất ra ngoài.',
    'MODULE_THU_KHONG_CONG_BO': 'Đang chạy thử nên chưa được chuyển kết quả chính thức sang chức năng khác.',
    'MODULE_KHONG_CHO_PHEP': 'Chưa được thực hiện thao tác này ở pháp nhân này.',
    'MODULE_CHI_ADMIN': 'Chỉ quản trị viên đang hoạt động được quản lý công tắc và người thử.',
    'MODULE_CAN_LY_DO': 'Cần nhập lý do thực hiện.',
    'MODULE_DAU_VAO': 'Chức năng hoặc pháp nhân không hợp lệ.',
    'MODULE_CHE_DO': 'Cần chọn chế độ Tắt, Thử hoặc Vận hành.',
    'MODULE_REVISION': 'Công tắc đã thay đổi; tải lại trước khi lưu.',
    'MODULE_CHUA_DU_DIEU_KIEN_GO_LIVE': 'Chưa đủ điều kiện đưa chức năng vào vận hành.',
    'MODULE_NGUOI_THU': 'Cần chọn người dùng đang hoạt động để thử.',
    'MODULE_DA_CAP': 'Người dùng đã được chọn thử; tải lại danh sách.',
    'MODULE_CHUA_CAP': 'Người dùng chưa có lượt thử hiện hành để thu hồi.',
}


def _chan(ma):
    raise DataError(ma, _THONG_BAO[ma])


def _uuid(value):
    try:
        if isinstance(value, (str, uuid.UUID)):
            return str(uuid.UUID(str(value)))
    except ValueError:
        pass
    _chan('MODULE_DAU_VAO')


def _dich(module, phap_nhan_id):
    if not isinstance(module, str) or not module.strip() or module != module.strip():
        _chan('MODULE_DAU_VAO')
    return module, _uuid(phap_nhan_id)


def _trang_thai(conn, module, phap_nhan_id):
    args = _dich(module, phap_nhan_id)
    row = conn.execute('SELECT master.module_trang_thai(%s,%s::uuid) AS r', args).fetchone()
    if row is None or not isinstance(row['r'], dict):
        _chan('MODULE_KHONG_CHO_PHEP')
    return dict(row['r'])


def kiem_module(conn, module, phap_nhan_id, *, can):
    """Kiểm trước ghi/xuất/công bố, trên cùng conn/giao dịch của nghiệp vụ.

    Máy chủ PHẢI xác định PN từ đối tượng nghiệp vụ hoặc phiên tin cậy,
    không lấy PN/danh tính từ body client. Hàm không tự suy PN, không đặt
    lại GUC phiên, không commit/rollback; caller vẫn phải kiểm quyền MTQ.
    TẮT vẫn cho xem dữ liệu cũ theo S4. Việc nền đã chạy dùng luồng hoàn
    tất riêng của caller theo S4, không dùng cổng này để nhận việc mới.
    Trả cờ SQL nếu đạt; DataError chứa mã riêng và câu nghiệp vụ nếu chặn.
    """
    if not isinstance(can, str) or can not in _CO_CAN:
        raise DataError('MODULE_DAU_VAO', 'Thao tác kiểm tra chức năng không hợp lệ.')
    flags = _trang_thai(conn, module, phap_nhan_id)
    if flags.get(_CO_CAN[can]) is True:
        return flags
    if flags.get('che_do') == 'TAT':
        _chan('MODULE_TAT')
    if flags.get('che_do') == 'THU':
        if flags.get('cho_xem') is not True:
            _chan('MODULE_CHI_NGUOI_THU')
        if can == 'xuat_ngoai':
            _chan('MODULE_THU_KHONG_XUAT')
        if can == 'cong_bo':
            _chan('MODULE_THU_KHONG_CONG_BO')
    _chan('MODULE_KHONG_CHO_PHEP')


def _ten_module(module):
    # XS-4a hiện chỉ có adapter khai báo CRM, chưa có catalog chung.
    # Không đoán tên nghiệp vụ từ mã kỹ thuật của các module còn lại.
    if module == 'CRM':
        from ..ha_tang.khai_bao_module import tu_khai_bao_crm

        return tu_khai_bao_crm().ten
    return 'dữ liệu từ chức năng nguồn'


def trang_thai_cho(conn, module_nguon, phap_nhan_id):
    """S4: PN và GUC phiên do máy chủ xác định như kiem_module.

    Dữ liệu THỬ không được dùng làm kết quả chính thức ở module khác;
    TẮT vẫn xem nội bộ được nhưng bên nhận phải hiện Chờ.
    """
    flags = _trang_thai(conn, module_nguon, phap_nhan_id)
    if flags.get('cho_xem') is True and flags.get('cong_bo_chinh_thuc') is True:
        return None
    return {'ma': 'CHO_MODULE', 'ly_do': 'Chờ ' + _ten_module(module_nguon)}


def _payload(value, *, nguoi_thu=False):
    fields = {'module', 'phap_nhan_id', 'ly_do'} | (
        {'nguoi_dung_id'} if nguoi_thu else {'che_do', 'expected_revision'})
    if not isinstance(value, dict) or set(value) != fields:
        raise DataError('MODULE_DAU_VAO', 'Thiếu trường bắt buộc hoặc có tham số không được hỗ trợ.')
    p = dict(value)
    p['module'], p['phap_nhan_id'] = _dich(p['module'], p['phap_nhan_id'])
    if not isinstance(p['ly_do'], str) or not p['ly_do'].strip():
        _chan('MODULE_CAN_LY_DO')
    p['ly_do'] = p['ly_do'].strip()
    if nguoi_thu:
        p['nguoi_dung_id'] = _uuid(p['nguoi_dung_id'])
    else:
        if not isinstance(p['che_do'], str) or p['che_do'] not in {'TAT', 'THU', 'VAN_HANH'}:
            _chan('MODULE_CHE_DO')
        if type(p['expected_revision']) is not int or not 0 <= p['expected_revision'] <= 9223372036854775807:
            raise DataError('MODULE_DAU_VAO', 'Phiên bản công tắc phải là số nguyên không âm.')
    return p


class CongTacModuleK2:
    """Tái dùng mau.danh_tinh/_tx như MaTranThamQuyenK2.

    dang_nhap do máy chủ lấy từ phiên. Payload là lệnh nội bộ đã được
    máy chủ dựng: phap_nhan_id phải được xác định/xác minh từ đối tượng
    hoặc phiên, không truyền thẳng body client. expected_revision là
    revision cũ của công tắc; nguoi_dung_id là người nhận lượt thử,
    tuyệt đối không phải danh tính người thao tác. SQL kiểm Admin.
    """

    def __init__(self, mau):
        self.mau = mau

    def _run(self, dang_nhap, operation):
        dt = self.mau.danh_tinh(dang_nhap)
        try:
            with self.mau._tx(dt) as conn:
                return operation(conn)
        except Exception as exc:
            # Chỉ dịch mã lỗi nghiệp vụ đã biết, sau rollback của _tx.
            # Không ghi log danh sách người thử hay chuyển chi tiết SQL ra UI.
            primary = getattr(getattr(exc, 'diag', None), 'message_primary', '') or ''
            code = primary.split(':', 1)[0]
            if code in _THONG_BAO:
                raise DataError(code, _THONG_BAO[code]) from None
            raise

    def trang_thai(self, dang_nhap, module, phap_nhan_id):
        return self._run(dang_nhap, lambda conn: _trang_thai(conn, module, phap_nhan_id))

    def doi_che_do(self, dang_nhap, payload):
        p = _payload(payload)
        args = tuple(p[k] for k in ('module', 'phap_nhan_id', 'che_do', 'ly_do', 'expected_revision'))
        return self._run(dang_nhap, lambda conn: {
            'revision': conn.execute(
                'SELECT master.module_doi_che_do(%s,%s::uuid,%s,%s,%s::bigint) AS r',
                args).fetchone()['r']})

    def cap_nguoi_thu(self, dang_nhap, payload):
        p = _payload(payload, nguoi_thu=True)
        args = tuple(p[k] for k in ('module', 'phap_nhan_id', 'nguoi_dung_id', 'ly_do'))
        return self._run(dang_nhap, lambda conn: {
            'id': _v(conn.execute(
                'SELECT master.module_cap_nguoi_thu(%s,%s::uuid,%s::uuid,%s) AS r',
                args).fetchone()['r'])})

    def thu_hoi_nguoi_thu(self, dang_nhap, payload):
        p = _payload(payload, nguoi_thu=True)
        args = tuple(p[k] for k in ('module', 'phap_nhan_id', 'nguoi_dung_id', 'ly_do'))
        return self._run(dang_nhap, lambda conn: {
            'id': _v(conn.execute(
                'SELECT master.module_thu_hoi_nguoi_thu(%s,%s::uuid,%s::uuid,%s) AS r',
                args).fetchone()['r'])})

    def danh_sach_nguoi_thu(self, dang_nhap, module, phap_nhan_id):
        args = _dich(module, phap_nhan_id)
        return self._run(dang_nhap, lambda conn: [
            _v(dict(row)) for row in conn.execute(
                'SELECT * FROM master.module_danh_sach_nguoi_thu(%s,%s::uuid)', args)])
