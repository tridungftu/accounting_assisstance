"""XS-4c2: HTTP công tắc; Admin MTQ toàn hệ thống quản trị mọi pháp nhân."""

from contextlib import contextmanager
from urllib.parse import parse_qs, urlsplit

from ..ha_tang.primitives import DataError
from ..k2.ma_tran_tham_quyen import MA_403
from ..k2.module import CongTacModuleK2, _THONG_BAO, _payload
from . import ma_tran_tham_quyen as mtq_http
from .khung_khai_bao import VAI

PREFIX = '/api/cong-tac-module/'
GET = frozenset(PREFIX + x for x in ('trang-thai', 'nguoi-thu'))
POST = {PREFIX + 'che-do': 'doi_che_do',
        PREFIX + 'nguoi-thu/cap': 'cap_nguoi_thu',
        PREFIX + 'nguoi-thu/thu-hoi': 'thu_hoi_nguoi_thu'}
ROUTE = GET | POST.keys()
MA_503 = frozenset({'CRM_G_CHUA_SAN_SANG', 'PG_KHONG_KET_NOI',
                    'CRM_CHUA_CAU_HINH', 'CRM_SCHEMA_KHONG_KHOP',
                    'CRM_G_GIAO_DICH_NGOAI'})


def la_route(post, path):
    return path in (POST if post else GET)


class _CongTacHttpK2(CongTacModuleK2):
    def kiem_danh_muc(self, me, module):
        if not isinstance(module, str) or not module or module != module.strip():
            raise DataError('MODULE_DAU_VAO', 'Cần chọn chức năng trong danh mục.')

        def doc(conn):
            if conn.execute('SELECT ma FROM master.module_danh_muc WHERE ma = %s',
                            (module,)).fetchone() is None:
                raise DataError('MODULE_DAU_VAO', 'Chức năng chưa có trong danh mục.')

        self._run(me, doc)

    def phap_nhan(self, me, module, *, quan_tri=False):
        dt = self.mau.danh_tinh(me)
        with self.mau._tx(dt, rr=True) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            if quan_tri:
                # Kiểm cả khi danh sách PN rỗng; SQL M0056 kiểm lại từng lệnh.
                if not conn.execute('SELECT master.mtq_la_admin() AS duoc').fetchone()['duoc']:
                    raise DataError('MODULE_CHI_ADMIN', _THONG_BAO['MODULE_CHI_ADMIN'])
                rows = conn.execute('SELECT id, ten FROM master.phap_nhan ORDER BY ma, id')
            else:
                # Cùng nguồn/predicate với CrmKhungK2.quyen; khung chưa có hàm liệt kê PN.
                vai = dt['vai_tro']
                rows = conn.execute('''SELECT p.id, p.ten FROM master.phap_nhan p
                    WHERE master.ktt_duoc(p.id, %s)
                      AND master.ktt_co_vai(p.id, %s::text[], NULL)
                    ORDER BY p.ma, p.id''', (module, [vai] if vai in VAI else []))
            return [{'phap_nhan_id': str(r['id']), 'ten_phap_nhan': r['ten']} for r in rows]


@contextmanager
def dich_vu(app):
    # Tái dùng factory MTQ, không đánh thức worker hoặc mở kết nối khác.
    with mtq_http.dich_vu(app) as svc:
        yield _CongTacHttpK2(svc.mau)


def _tham_so(h, post, query):
    raw = parse_qs(urlsplit(h.path).query, keep_blank_values=True, max_num_fields=10)
    if post:
        if query or raw:
            raise DataError('MODULE_DAU_VAO', 'Lệnh quản trị không nhận tham số truy vấn.')
        return None
    if set(raw) != {'module'} or len(raw['module']) != 1 or query.keys() - {'module'}:
        raise DataError('MODULE_DAU_VAO', 'Chỉ nhận một chức năng; pháp nhân được xác định tại máy chủ.')
    return raw['module'][0]


def _lenh(h, path):
    p = h.json_body()
    if path == PREFIX + 'che-do':
        fields = {'module', 'phap_nhan_id', 'che_do', 'ly_do', 'revision'}
        if not isinstance(p, dict) or set(p) != fields:
            raise DataError('MODULE_DAU_VAO', 'Thiếu trường bắt buộc hoặc có tham số không được hỗ trợ.')
        p = {**p, 'expected_revision': p['revision']}
        p.pop('revision')
    return _payload(p, nguoi_thu=path != PREFIX + 'che-do')


def dieu_huong(h, app, post, path, query):
    try:
        if not la_route(post, path):
            return h.send_content(404, {'error': 'NOT_FOUND', 'message': 'Không tìm thấy chức năng.'})
        h.authorize(private=True)
        module = _tham_so(h, post, query)
        body = _lenh(h, path) if post else None
        with app.mutation_lock:
            _, me, _ = app.crm_phien(h.crm_sid())

            def thuc_hien():
                with dich_vu(app) as svc:
                    svc.kiem_danh_muc(me, body['module'] if post else module)
                    if post:
                        # PN đích là tham số quản trị; M0056 kiểm Admin toàn hệ thống và FK.
                        return getattr(svc, POST[path])(me, body)
                    quan_tri = path == PREFIX + 'nguoi-thu'
                    phap_nhan = svc.phap_nhan(me, module, quan_tri=quan_tri)
                    if quan_tri:
                        return [r for pn in phap_nhan for r in
                                svc.danh_sach_nguoi_thu(me, module, pn['phap_nhan_id'])]
                    return [{**svc.trang_thai(me, module, pn['phap_nhan_id']), **pn}
                            for pn in phap_nhan]

            result = app._crm_db(thuc_hien)
        return h.send_content(200, result)
    except DataError as exc:
        status = (403 if exc.code in MA_403 | {'MODULE_CHI_ADMIN'} else
                  409 if exc.code == 'MODULE_REVISION' else
                  503 if exc.code in MA_503 else 400)
        message = _THONG_BAO.get(exc.code, str(exc))
        if status == 503:
            message = 'Chưa đọc được dữ liệu công tắc. Vui lòng thử lại sau.'
        elif exc.code == 'CSDL_TU_CHOI':
            message = 'Chưa thực hiện được thao tác. Kiểm tra thông tin và thử lại.'
        return h.send_content(status, {'error': exc.code, 'message': message})
    except (ValueError, TypeError, KeyError, RecursionError):
        return h.send_content(400, {'error': 'MODULE_DAU_VAO', 'message': 'Thông tin gửi lên không hợp lệ.'})
