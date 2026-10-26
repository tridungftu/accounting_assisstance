"""MTQ-2: route mỏng cho dispatcher MTQ-3b; chưa nối server.py theo §7.

GET ma-tran/cua-toi/nhat-ky; POST cấu hình, phòng, vai, phạm vi, Admin. Không có
bootstrap hoặc lệnh SQL tùy ý. Gọi authorize của Handler hiện có, không tạo
server/router mới. Revision KICH_HOAT thuộc con trỏ (0 khi chưa có).
Khôi phục ghép được từ NHAP (sao chép bản đã công bố) + CONG_BO;
route khoi-phuc để lát sau.
"""

from contextlib import contextmanager
from urllib.parse import parse_qs, urlsplit

from ..ha_tang.primitives import DataError
from ..k2.ma_tran_tham_quyen import MA_403, MA_409, MA_LOI_NHAT_KY, QUAN_TRI, MaTranThamQuyenK2, _payload

PREFIX = '/api/tham-quyen/'
GET = frozenset(PREFIX + x for x in ('ma-tran', 'cua-toi', 'nhat-ky'))
POST = {PREFIX + 'luu-nhap': 'luu_nhap', PREFIX + 'cong-bo': 'cong_bo', PREFIX + 'kich-hoat': 'kich_hoat',
        PREFIX + 'phong': 'phong', PREFIX + 'gan-vai': 'gan_vai',
        PREFIX + 'pham-vi': 'pham_vi', PREFIX + 'admin': 'admin'}
ROUTE = GET | POST.keys()


def la_route(post, path):
    return path in (POST if post else GET)


@contextmanager
def dich_vu(app):
    # Không khởi tạo factory G có side effect đánh thức worker G5.
    from ..k2.crm_mau import CrmMauK2
    crm = app.crm()
    chu = app._m5_ket_noi_chu(crm.conn)
    if chu is None:
        raise DataError('CRM_G_CHUA_SAN_SANG', 'Chưa sẵn sàng quản lý thẩm quyền. Báo quản trị.')
    try:
        yield MaTranThamQuyenK2(CrmMauK2(crm.conn, app.root / 'crm-g', conn_tin_cay=chu, hom_nay=crm.hom_nay))
    finally:
        chu.close()


def dieu_huong(h, app, post, path, query):
    try:
        if not la_route(post, path):
            return h.send_content(404, {'error': 'NOT_FOUND', 'message': 'Không tìm thấy chức năng.'})
        h.authorize(private=True)
        if query or parse_qs(urlsplit(h.path).query, keep_blank_values=True):
            raise DataError('MTQ_DAU_VAO', 'Không nhận tham số truy vấn.')
        if post:
            command = POST[path].upper()
            body = _payload(h.json_body(), luu=command == 'LUU_NHAP',
                            quan_tri=command if command in QUAN_TRI else None)
        with app.mutation_lock:
            _, me, _ = app.crm_phien(h.crm_sid())
            with dich_vu(app) as svc:
                if post:
                    result = app._crm_db(getattr(svc, POST[path]), me, body)
                elif path.endswith('/nhat-ky'):
                    result = app._crm_db(svc.nhat_ky, me)
                else:
                    result = app._crm_db(lambda: svc.ma_tran(me, cua_toi=path.endswith('/cua-toi')))
        return h.send_content(200, result)
    except DataError as exc:
        status = (403 if exc.code in MA_403 else 409 if exc.code in MA_409 else
                  503 if exc.code in {MA_LOI_NHAT_KY, 'CRM_G_CHUA_SAN_SANG', 'PG_KHONG_KET_NOI', 'CRM_CHUA_CAU_HINH', 'CRM_SCHEMA_KHONG_KHOP'} else 400)
        # Service đã chọn câu theo thao tác; giữ cả gợi ý GET Quyền của tôi.
        return h.send_content(status, {'error': exc.code, 'message': str(exc)})
    except (ValueError, TypeError, KeyError, RecursionError):
        return h.send_content(400, {'error': 'MTQ_DAU_VAO', 'message': 'Thông tin gửi lên không hợp lệ.'})
