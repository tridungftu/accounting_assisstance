"""MTQ-2: cấu hình qua SQL MTQ-1; chưa thay nguồn quyền nghiệp vụ.

Tái dùng CrmMauK2.danh_tinh/_tx (owner connection + GUC). Pháp nhân suy
từ bản/phòng/gán vai trong CSDL; khai phòng mới nhận pháp nhân đích.
Không nhận actor/diff từ HTTP. Bootstrap chỉ
thuộc công cụ lead. Biên nhận HTTP nằm trong sổ bất biến, cùng giao dịch
với cấu hình; kiểm Admin hiện hành trước replay. Chặn ghi ở giao dịch riêng
sau rollback; lỗi audit không được nuốt.
Khôi phục ghép được từ NHAP (sao chép bản đã công bố) + CONG_BO;
route khoi-phuc để lát sau.
"""

from __future__ import annotations

import json
import re
import uuid

from ..ha_tang.primitives import DataError
from .crm_mau import _v
from .sql_ma_tran_tham_quyen import _CATALOG

VAI = frozenset(('THUC_HIEN_1', 'THUC_HIEN_2', 'TRUONG_PHONG', 'CFO', 'NGUOI_XEM'))
O_HOP_LE = frozenset((m, man, a) for m, man, actions, _ in _CATALOG for a in actions.split())
# Mỗi lần lưu đúng một phòng: tối đa 5 vai, mỗi vai tối đa toàn bộ danh mục ô.
MAX_DONG_LUU = len(VAI)
MAX_O_LUU = MAX_DONG_LUU * len(O_HOP_LE)
GIOI_HAN_NHAT_KY = 200
MA_LOI_NHAT_KY = 'MTQ_NHAT_KY_LOI'
LOI_NHAT_KY = 'Chưa ghi được nhật ký thẩm quyền, thao tác không được thực hiện. Báo quản trị.'
MA_403 = frozenset(('MTQ_CHI_ADMIN', 'MTQ_DANH_TINH', 'DANH_TINH', 'DANH_TINH_MO_PHONG',
                    'CRM_PHIEN', 'SESSION_TOKEN', 'CROSS_ORIGIN', 'LOCAL_HOST_ONLY'))
MA_409 = frozenset(('MTQ_REVISION', 'MTQ_IDEMPOTENCY_KHAC', 'MTQ_BAT_BIEN',
                    'MTQ_DA_CAP',
                    'MTQ_THIEU_DONG', 'MTQ_CHUA_NOI_MTQ4', 'MTQ_ADMIN_CUOI',
                    'MTQ_CAN_RESOLVER_MTQ4', 'CRM_G_GIAO_DICH_NGOAI'))
LOI_CAU_HINH = 'Không thể áp dụng cấu hình thẩm quyền; kiểm tra lại phiên bản và điều kiện thực hiện.'
LOI_THAY_DOI = 'Dữ liệu đã thay đổi; tải lại trước khi thao tác.'
LOI_PHONG_NGUNG = 'Phòng đã ngừng hoạt động; chọn phòng đang hoạt động để cấp vai.'
THONG_BAO = {
    'MTQ_DA_CAP': 'Đã cấp trước đó; tải lại để xem bản hiện hành.',
    'MTQ_KHONG_THAY': 'Pháp nhân, phòng hoặc người dùng không tồn tại.',
    'MTQ_NGUOI_NHAN_NGUNG': 'Người được cấp không còn hoạt động.',
    'MTQ_DANH_TINH': 'Danh tính người thao tác không còn hoạt động; đăng nhập lại.',
    'MTQ_THIEU_DONG': 'Chưa đủ 5 vai cho mỗi phòng đang dùng; bổ sung trước khi công bố.',
    'MTQ_CHUA_NOI_MTQ4': 'Chưa bật được: các phân hệ chưa nối xong với ma trận.',
    'MTQ_REVISION': 'Bản nháp đã thay đổi; tải lại trước khi lưu.',
    'MTQ_ADMIN_CUOI': 'Không thể thu hồi Admin hoạt động cuối cùng; cấp thêm Admin trước khi thu hồi.',
    'MTQ_PHAM_VI': 'Phạm vi không hợp lệ, khác pháp nhân hoặc gán vai đã bị thu hồi; kiểm tra lại.',
    'MTQ_CHI_ADMIN': 'Chỉ Admin đang hoạt động được quản trị ma trận thẩm quyền.',
    'MTQ_BAT_BIEN': 'Bản đã công bố hoặc lịch sử cấp quyền không thể sửa; hãy tạo bản mới.',
    'MTQ_IDEMPOTENCY_KHAC': 'Yêu cầu này đã được gửi với nội dung khác; tải lại rồi thử lại.',
}
QUAN_TRI = frozenset(('PHONG', 'GAN_VAI', 'PHAM_VI', 'ADMIN'))


def _sai(message):
    raise DataError('MTQ_DAU_VAO', message)


def _object(value, fields, required=()):
    if not isinstance(value, dict) or set(value) - set(fields) or set(required) - set(value):
        _sai('Thiếu trường bắt buộc hoặc có tham số không được hỗ trợ.')
    return value


def _uuid(value):
    try:
        if isinstance(value, str):
            return str(uuid.UUID(value))
    except ValueError:
        pass
    _sai('Mã không hợp lệ')


def _yeu_cau(value):
    p = dict(value)
    rev = p['expected_revision']
    if type(rev) is not int or not 0 <= rev <= 9223372036854775807:
        _sai('Phiên bản phải là số nguyên không âm.')
    if not isinstance(p['ly_do'], str) or not p['ly_do'].strip() or len(p['ly_do']) > 2000:
        _sai('Cần lý do, tối đa 2.000 ký tự.')
    p['ly_do'] = p['ly_do'].strip()
    p['khoa'] = _uuid(p['khoa'])
    return p


def _payload(value, *, luu=False, quan_tri=None):
    if quan_tri is not None:
        return _payload_quan_tri(value, quan_tri)
    fields = {'phien_ban_id', 'expected_revision', 'ly_do', 'khoa'}
    if luu:
        fields |= {'nguon_id', 'dong'}
    _object(value, fields, {'expected_revision', 'ly_do', 'khoa'})
    p = _yeu_cau(value)
    rev = p['expected_revision']
    for key in ('phien_ban_id', 'nguon_id'):
        if p.get(key) is not None:
            p[key] = _uuid(p[key])
    if not luu and not p.get('phien_ban_id'):
        _sai('Cần phiên bản công bố/kích hoạt.')
    if luu:
        if p.get('phien_ban_id') and p.get('nguon_id'):
            _sai('Chỉ chọn bản nháp hoặc bản nguồn.')
        rows = p.get('dong', [])
        if not isinstance(rows, list) or len(rows) > MAX_DONG_LUU:
            _sai('Mỗi lần lưu tối đa 5 vai của một phòng.')
        seen = set()
        rooms = set()
        clean = []
        for row in rows:
            _object(row, {'phong_id', 'vai', 'gioi_han_vnd', 'o'}, {'phong_id', 'vai', 'gioi_han_vnd', 'o'})
            phong = _uuid(row['phong_id'])
            rooms.add(phong)
            if len(rooms) > 1:
                _sai('Mỗi lần lưu chỉ chọn một phòng.')
            if not isinstance(row['vai'], str) or row['vai'] not in VAI or (phong, row['vai']) in seen:
                _sai('Vai không hợp lệ hoặc bị lặp trong phòng.')
            seen.add((phong, row['vai']))
            money = row['gioi_han_vnd']
            if money == '' or money is None:
                money = None
            elif type(money) is int or isinstance(money, str):
                if not re.fullmatch(r'[0-9]{1,20}', str(money)):
                    _sai('Giới hạn VND phải nguyên không âm, tối đa 20 chữ số.')
                money = str(int(money))
            else:
                _sai('Giới hạn VND phải nguyên không âm hoặc để trống.')
            cells = row['o']
            if not isinstance(cells, list) or len(cells) > len(O_HOP_LE):
                _sai('Danh sách ô không hợp lệ.')
            keys = set()
            for cell in cells:
                _object(cell, {'module', 'man', 'hanh_dong', 'cho_phep'}, {'module', 'man', 'hanh_dong', 'cho_phep'})
                key = tuple(cell[k] for k in ('module', 'man', 'hanh_dong'))
                if not all(isinstance(x, str) for x in key) or key not in O_HOP_LE or key in keys or type(cell['cho_phep']) is not bool:
                    _sai('Ô không thuộc danh mục, bị lặp hoặc chưa chọn bật/tắt hợp lệ.')
                keys.add(key)
            clean.append({'phong_id': phong, 'vai': row['vai'], 'gioi_han_vnd': money, 'o': [dict(c) for c in cells]})
        p['dong'] = clean
        if not clean and not p.get('nguon_id'):
            _sai('Cần dòng thay đổi hoặc bản đang áp.')
        if not p.get('phien_ban_id') and rev != 0:
            _sai('Tạo nháp cần phiên bản 0.')
    return p


def _payload_quan_tri(value, command):
    """PHONG: TAO/SUA; các cấp quyền: CAP/THU_HOI.

    khoa là khóa yêu cầu; khoa_pham_vi là khóa đối tượng của phạm vi.
    Không nhận actor, diff, quan_he hoặc pháp nhân cho đối tượng đã có.
    """
    if command not in QUAN_TRI:
        _sai('Thao tác quản trị không được hỗ trợ.')
    common = {'expected_revision', 'ly_do', 'khoa', 'thao_tac'}
    if not isinstance(value, dict):
        _sai('Thông tin quản trị không hợp lệ.')
    operation = value.get('thao_tac')
    if not isinstance(operation, str):
        _sai('Cần chọn rõ thao tác cấp, thu hồi, tạo hoặc sửa.')
    if command == 'PHONG' and operation == 'TAO':
        required = fields = {'phap_nhan_id', 'ma', 'ten'}
    elif command == 'PHONG' and operation == 'SUA':
        fields, required = {'id', 'ten', 'hoat_dong'}, {'id'}
        if not {'ten', 'hoat_dong'} & value.keys():
            _sai('Cần tên phòng hoặc trạng thái cần sửa.')
    elif command != 'PHONG' and operation == 'THU_HOI':
        required = fields = {'id'}
    elif operation == 'CAP':
        required = fields = {
            'ADMIN': {'nguoi_dung_id'},
            'GAN_VAI': {'nguoi_dung_id', 'phong_id', 'vai'},
            'PHAM_VI': {'gan_vai_id', 'loai', 'khoa_pham_vi'},
        }.get(command, set())
        if not fields:
            _sai('Thao tác không phù hợp với chức năng đã chọn.')
    else:
        _sai('Thao tác không phù hợp với chức năng đã chọn.')
    _object(value, common | fields, common | required)
    p = _yeu_cau(value)
    for key in ('id', 'phap_nhan_id', 'nguoi_dung_id', 'phong_id', 'gan_vai_id'):
        if key in p:
            p[key] = _uuid(p[key])
    for key in ('ma', 'ten'):
        if key in p:
            if not isinstance(p[key], str) or not p[key].strip() or len(p[key]) > 2000:
                _sai('Mã và tên phòng không được để trống, tối đa 2.000 ký tự.')
            p[key] = p[key].strip()
    if 'hoat_dong' in p and type(p['hoat_dong']) is not bool:
        _sai('Trạng thái phòng phải chọn hoạt động hoặc ngừng hoạt động.')
    if 'vai' in p and (not isinstance(p['vai'], str) or p['vai'] not in VAI):
        _sai('Vai không thuộc năm vai nghiệp vụ.')
    if 'loai' in p:
        if not isinstance(p['loai'], str) or p['loai'] not in {'PHAP_NHAN', 'DU_AN', 'LOAI_HINH', 'HOP_DONG', 'KHACH', 'NGUON'}:
            _sai('Loại phạm vi không được hỗ trợ.')
        if p['loai'] == 'NGUON':
            if not isinstance(p['khoa_pham_vi'], str) or not p['khoa_pham_vi'].strip() or len(p['khoa_pham_vi']) > 2000:
                _sai('Cần mã phạm vi hợp lệ, tối đa 2.000 ký tự.')
        else:
            p['khoa_pham_vi'] = _uuid(p['khoa_pham_vi'])
    return p


class MaTranThamQuyenK2:
    def __init__(self, mau):
        self.mau = mau

    @staticmethod
    def _one(c, sql, params=()):
        row = c.execute(sql, params).fetchone()
        return _v(dict(row)) if row is not None else None

    @staticmethod
    def _many(c, sql, params=()):
        return [_v(dict(r)) for r in c.execute(sql, params)]

    @staticmethod
    def _admin(c):
        return bool(c.execute('SELECT master.mtq_la_admin() AS ok').fetchone()['ok'])

    def ma_tran(self, dang_nhap, *, cua_toi=False):
        dt = self.mau.danh_tinh(dang_nhap)
        with self.mau._tx(dt, rr=True) as c:
            la_admin = self._admin(c)
            admin = la_admin and not cua_toi
            if not cua_toi and not admin:
                raise DataError('MTQ_CHI_ADMIN', 'Chỉ quản trị xem được toàn bộ ma trận; xem Quyền của tôi.')
            if not admin:
                # Chỉ snapshot đang bật và đúng vai/phòng của mình; không lộ nháp.
                rows = self._many(c, """SELECT d.*, p.ten AS ten_phong FROM master.mtq_dong d
                    JOIN master.mtq_phong p ON p.id=d.phong_id AND p.hoat_dong
                    JOIN master.mtq_kich_hoat k ON k.phap_nhan_id=d.phap_nhan_id AND k.bat AND k.phien_ban_id=d.phien_ban_id
                    JOIN master.mtq_gan_vai g ON g.phap_nhan_id=d.phap_nhan_id AND g.phong_id=d.phong_id AND g.vai=d.vai
                    WHERE g.nguoi_dung_id=%s::uuid AND g.thu_hoi_luc IS NULL ORDER BY d.phap_nhan_id,d.phong_id,d.vai""", (dt['id'],))
                assignments = self._many(c, "SELECT * FROM master.mtq_gan_vai WHERE nguoi_dung_id=%s::uuid AND thu_hoi_luc IS NULL ORDER BY id", (dt['id'],))
                scopes = self._many(c, """SELECT s.* FROM master.mtq_pham_vi s JOIN master.mtq_gan_vai g ON g.id=s.gan_vai_id
                    WHERE g.nguoi_dung_id=%s::uuid AND g.thu_hoi_luc IS NULL AND s.thu_hoi_luc IS NULL ORDER BY s.id""", (dt['id'],))
                versions = self._many(c, """SELECT v.id,v.phap_nhan_id,v.so_phien_ban,v.revision,v.catalog_version,v.trang_thai
                    FROM master.mtq_phien_ban v JOIN master.mtq_kich_hoat k ON k.phien_ban_id=v.id AND k.bat
                    WHERE EXISTS (SELECT 1 FROM master.mtq_gan_vai g WHERE g.phap_nhan_id=v.phap_nhan_id
                        AND g.nguoi_dung_id=%s::uuid AND g.thu_hoi_luc IS NULL) ORDER BY v.phap_nhan_id""", (dt['id'],))
                activation = self._many(c, """SELECT k.* FROM master.mtq_kich_hoat k WHERE EXISTS
                    (SELECT 1 FROM master.mtq_gan_vai g WHERE g.phap_nhan_id=k.phap_nhan_id
                     AND g.nguoi_dung_id=%s::uuid AND g.thu_hoi_luc IS NULL) ORDER BY k.phap_nhan_id""", (dt['id'],))
                rooms = []
            else:
                rows = self._many(c, 'SELECT * FROM master.mtq_dong ORDER BY phien_ban_id,phong_id,vai')
                assignments = self._many(c, 'SELECT * FROM master.mtq_gan_vai ORDER BY id')
                scopes = self._many(c, 'SELECT * FROM master.mtq_pham_vi ORDER BY id')
                versions = self._many(c, 'SELECT * FROM master.mtq_phien_ban ORDER BY phap_nhan_id,so_phien_ban')
                activation = self._many(c, 'SELECT * FROM master.mtq_kich_hoat ORDER BY phap_nhan_id')
                rooms = self._many(c, 'SELECT * FROM master.mtq_phong ORDER BY phap_nhan_id,ma')
            # Lọc trong SQL trước khi đọc ô, không tải ma trận khác về Python.
            cells = self._many(c, '''SELECT dong_id,module,man,hanh_dong,cho_phep FROM master.mtq_o
                WHERE dong_id=ANY(%s::uuid[]) ORDER BY dong_id,module,man,hanh_dong''', ([r['id'] for r in rows],))
            by_row = {r['id']: [] for r in rows}
            for cell in cells:
                by_row[cell.pop('dong_id')].append(cell)
            for row in rows:
                row['o'] = by_row[row['id']]
            return {'admin': admin, 'la_admin': la_admin, 'dong': rows, 'phong': rooms, 'phien_ban': versions,
                    'gan_vai': assignments, 'pham_vi': scopes, 'kich_hoat': activation,
                    'danh_muc': self._many(c, 'SELECT * FROM master.mtq_danh_muc_hanh_dong ORDER BY module,man,hanh_dong'),
                    'chua_noi_mtq4': True}

    def nhat_ky(self, dang_nhap, *, gioi_han=GIOI_HAN_NHAT_KY):
        if type(gioi_han) is not int or not 1 <= gioi_han <= GIOI_HAN_NHAT_KY:
            _sai('Số dòng nhật ký phải từ 1 đến 200.')
        dt = self.mau.danh_tinh(dang_nhap)
        with self.mau._tx(dt, rr=True) as c:
            if not self._admin(c):
                raise DataError('MTQ_CHI_ADMIN', 'Chỉ quản trị được xem toàn bộ nhật ký.')
            return {'thay_doi': self._many(c, '''SELECT id,request_id,phap_nhan_id,doi_tuong_bang,doi_tuong,
                        phien_ban_id,revision,loai_su_kien,truoc,sau,actor_id,actor_login,luc,ly_do
                    FROM nhat_ky.mtq_thay_doi ORDER BY luc DESC,id DESC LIMIT %s''', (gioi_han,)),
                    'tu_choi': self._many(c, '''SELECT id,request_id,actor_id,actor_login,phap_nhan_id,phong_id,vai,
                        phien_ban_id,revision,gan_vai_id,gan_vai_revision,pham_vi_id,pham_vi_revision,
                        module,man,hanh_dong,lenh_ky_thuat,doi_tuong,ma,ly_do,gioi_han_vnd,so_tien_vnd,luc
                    FROM nhat_ky.mtq_tu_choi ORDER BY luc DESC,id DESC LIMIT %s''', (gioi_han,))}

    @staticmethod
    def _sql(c, request, command, data, revision, reason):
        try:
            return c.execute('SELECT master.mtq_cau_hinh_ghi(%s::uuid,%s,%s::jsonb,%s,%s) AS r',
                             (request, command, json.dumps(data, ensure_ascii=False), revision, reason)).fetchone()['r']
        except Exception as exc:
            # Lỗi trigger ghi nhật ký cũng phải là lỗi hệ thống, không phải dữ liệu nhập.
            diag = getattr(exc, 'diag', None)
            if 'mtq_ghi_vet()' in (getattr(diag, 'context', '') or ''):
                raise DataError(MA_LOI_NHAT_KY, LOI_NHAT_KY) from None
            raise

    def _version(self, c, pb):
        v = self._one(c, 'SELECT * FROM master.mtq_phien_ban WHERE id=%s::uuid', (pb,))
        if v is None:
            raise DataError('MTQ_REVISION', 'Phiên bản không tồn tại hoặc đã thay đổi.')
        return v

    def _save(self, c, p):
        source = p.get('phien_ban_id') or p.get('nguon_id')
        v = self._version(c, source) if source else None
        # CAS của cả lần lưu chỉ kiểm một lần, sau khóa cấu hình trong _write.
        if p.get('phien_ban_id') and (v['revision'] != p['expected_revision'] or v['trang_thai'] != 'NHAP'):
            raise DataError('MTQ_REVISION', 'Bản nháp đã thay đổi; tải lại trước khi lưu.')
        pn = v['phap_nhan_id'] if v else None
        if p['dong']:
            room = self._one(c, 'SELECT phap_nhan_id FROM master.mtq_phong WHERE id=%s::uuid AND hoat_dong', (p['dong'][0]['phong_id'],))
            if room is None or (pn is not None and pn != room['phap_nhan_id']):
                _sai('Phòng không hoạt động hoặc khác pháp nhân của phiên bản.')
            pn = room['phap_nhan_id']
        args = (p['khoa'], p['ly_do'])
        if not p.get('phien_ban_id'):
            v = self._sql(c, args[0], 'NHAP', {'phap_nhan_id': pn, 'phien_ban_id': p.get('nguon_id')}, 0, args[1])
        # Đọc một lần, kể cả bản vừa sao chép; ô chưa có mang nghĩa chưa tick.
        current = self._many(c, '''SELECT d.id,d.phong_id,d.vai,d.gioi_han_vnd,
                o.module,o.man,o.hanh_dong,o.cho_phep
            FROM master.mtq_dong d LEFT JOIN master.mtq_o o ON o.dong_id=d.id
            WHERE d.phien_ban_id=%s::uuid AND d.phong_id=ANY(%s::uuid[])''',
            (v['id'], [r['phong_id'] for r in p['dong']]))
        rows, cells = {}, {}
        for item in current:
            rows[(item['phong_id'], item['vai'])] = item
            if item['module'] is not None:
                cells[(item['id'], item['module'], item['man'], item['hanh_dong'])] = item['cho_phep']
        for row in p['dong']:
            d = rows.get((row['phong_id'], row['vai']))
            money = None if d is None or d['gioi_han_vnd'] is None else str(int(d['gioi_han_vnd']))
            if d is None or money != row['gioi_han_vnd']:
                r = self._sql(c, args[0], 'DONG', {'phien_ban_id': v['id'], **{k: row[k] for k in ('phong_id', 'vai', 'gioi_han_vnd')}}, v['revision'], args[1])
                v, d = r['phien_ban'], r['doi_tuong']
            for cell in row['o']:
                key = (d['id'], cell['module'], cell['man'], cell['hanh_dong'])
                if cells.get(key, False) == cell['cho_phep']:
                    continue
                r = self._sql(c, args[0], 'O', {'phien_ban_id': v['id'], 'dong_id': d['id'], **cell}, v['revision'], args[1])
                v = r['phien_ban']
        return v

    def _write(self, dang_nhap, command, p):
        dt = self.mau.danh_tinh(dang_nhap)
        try:
            with self.mau._tx(dt) as c:
                c.execute('SELECT pg_advisory_xact_lock(742601, 1)')
                if not self._admin(c):
                    raise DataError('MTQ_CHI_ADMIN', 'Chỉ quản trị đang hoạt động được sửa ma trận.')
                old = self._one(c, "SELECT actor_id,doi_tuong,loai_su_kien,sau FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid AND doi_tuong_bang='HTTP'", (p['khoa'],))
                if old:
                    if old['actor_id'] != dt['id'] or old['loai_su_kien'] != 'HTTP_' + command or old['doi_tuong'] != p:
                        raise DataError('MTQ_IDEMPOTENCY_KHAC', THONG_BAO['MTQ_IDEMPOTENCY_KHAC'])
                    return {**old['sau'], 'lap_lai': True}
                if c.execute('SELECT 1 FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid LIMIT 1', (p['khoa'],)).fetchone():
                    raise DataError('MTQ_IDEMPOTENCY_KHAC', THONG_BAO['MTQ_IDEMPOTENCY_KHAC'])
                if command == 'LUU_NHAP':
                    v = self._save(c, p)
                elif command in QUAN_TRI:
                    v = self._quan_tri(c, command, p)
                else:
                    v = self._version(c, p['phien_ban_id'])
                    data = {'phap_nhan_id': v['phap_nhan_id'], 'phien_ban_id': v['id']}
                    if command == 'KICH_HOAT':
                        data['bat'] = True  # Không nhận bat=false để quay lại legacy.
                    r = self._sql(c, p['khoa'], command, data, p['expected_revision'], p['ly_do'])
                    v = r['phien_ban'] if command == 'CONG_BO' else r
                result = {'ket_qua': _v(v), 'lap_lai': False}
                self._ghi_nhat_ky(c, """INSERT INTO nhat_ky.mtq_thay_doi
                    (request_id,phap_nhan_id,doi_tuong_bang,doi_tuong,phien_ban_id,revision,loai_su_kien,truoc,sau,actor_id,actor_login,ly_do)
                    VALUES (%s::uuid,%s::uuid,'HTTP',%s::jsonb,%s::uuid,%s,%s,NULL,%s::jsonb,%s::uuid,%s,%s)""",
                    (p['khoa'], v.get('phap_nhan_id'), json.dumps(p, ensure_ascii=False),
                     (None if command in QUAN_TRI else v['phien_ban_id'] if command == 'KICH_HOAT' else v['id']), v['revision'],
                     'HTTP_' + command, json.dumps(result, ensure_ascii=False), dt['id'], dt['dang_nhap'], p['ly_do']))
                return result
        except Exception as exc:
            # Chỉ lấy câu chính; DETAIL của lỗi khóa có thể chứa dữ liệu hồ sơ.
            primary = getattr(getattr(exc, 'diag', None), 'message_primary', '') or ''
            reason = primary or (str(exc) if isinstance(exc, DataError) else '')
            error = exc
            if not isinstance(error, DataError):
                code = primary.split(':', 1)[0]
                state = getattr(exc, 'sqlstate', None)
                if state in {'23505', '23503'}:
                    code = 'MTQ_DA_CAP' if state == '23505' else 'MTQ_KHONG_THAY'
                    error = DataError(code, THONG_BAO[code])
                elif re.fullmatch(r'MTQ_[A-Z0-9_]+', code):
                    error = DataError(code, THONG_BAO.get(code, LOI_CAU_HINH))
            if isinstance(error, DataError) and error.code == MA_LOI_NHAT_KY:
                raise error from None
            if isinstance(error, DataError) and error.code.startswith('MTQ_'):
                message = THONG_BAO.get(error.code, LOI_CAU_HINH)
                if error.code == 'MTQ_REVISION' and command != 'LUU_NHAP':
                    message = LOI_THAY_DOI
                elif error.code == 'MTQ_PHAM_VI' and str(error) == LOI_PHONG_NGUNG:
                    message = LOI_PHONG_NGUNG
                error = DataError(error.code, message)
                # Một số nhánh SQL cũ chỉ RAISE mã; dùng câu nghiệp vụ khi thiếu câu chính.
                reason = reason if reason and reason != error.code else message
                try:
                    with self.mau._tx(dt) as c:
                        self._ghi_nhat_ky(c, """INSERT INTO nhat_ky.mtq_tu_choi
                            (request_id,actor_id,actor_login,ma,ly_do) VALUES (%s::uuid,%s::uuid,%s,%s,%s)""",
                            (p['khoa'], dt['id'], dt['dang_nhap'], error.code, reason))
                except Exception:
                    raise DataError(MA_LOI_NHAT_KY, LOI_NHAT_KY) from None
                raise error from None
            raise

    def _quan_tri(self, c, command, p):
        data = {k: v for k, v in p.items() if k not in {'khoa', 'ly_do', 'expected_revision', 'thao_tac'}}
        sql_command = command
        if p['thao_tac'] == 'THU_HOI':
            sql_command = {'ADMIN': 'THU_HOI_ADMIN', 'GAN_VAI': 'THU_HOI_VAI',
                           'PHAM_VI': 'THU_HOI_PHAM_VI'}[command]
        if p['thao_tac'] == 'CAP' and command in {'ADMIN', 'GAN_VAI'}:
            # Giữ trạng thái người nhận tới hết lần cấp, dưới khóa cấu hình.
            recipient = self._one(c, 'SELECT trang_thai FROM master.nguoi_dung WHERE id=%s::uuid FOR SHARE',
                                  (p['nguoi_dung_id'],))
            if recipient is None:
                raise DataError('MTQ_KHONG_THAY', THONG_BAO['MTQ_KHONG_THAY'])
            if recipient['trang_thai'] != 'HOAT_DONG':
                raise DataError('MTQ_NGUOI_NHAN_NGUNG', THONG_BAO['MTQ_NGUOI_NHAN_NGUNG'])
        if p['thao_tac'] == 'CAP' and command in {'GAN_VAI', 'PHAM_VI'}:
            query = ('SELECT phap_nhan_id,hoat_dong FROM master.mtq_phong WHERE id=%s::uuid'
                     if command == 'GAN_VAI' else
                     'SELECT phap_nhan_id FROM master.mtq_gan_vai WHERE id=%s::uuid AND thu_hoi_luc IS NULL')
            parent = self._one(c, query, (p['phong_id'] if command == 'GAN_VAI' else p['gan_vai_id'],))
            if parent is None:
                code = 'MTQ_KHONG_THAY' if command == 'GAN_VAI' else 'MTQ_PHAM_VI'
                raise DataError(code, THONG_BAO[code])
            if command == 'GAN_VAI' and not parent['hoat_dong']:
                raise DataError('MTQ_PHAM_VI', LOI_PHONG_NGUNG)
            data['phap_nhan_id'] = parent['phap_nhan_id']
            if command == 'PHAM_VI':
                data['khoa'] = data.pop('khoa_pham_vi')
                data['quan_he'] = {}  # Các quan hệ được trigger M0039 xác minh.
        # M0039 kiểm CAS, ghi diff/actor và bảo vệ Admin cuối trong cùng khóa.
        return self._sql(c, p['khoa'], sql_command, data, p['expected_revision'], p['ly_do'])

    @staticmethod
    def _ghi_nhat_ky(c, sql, params):
        try:
            c.execute(sql, params)
        except Exception:
            raise DataError(MA_LOI_NHAT_KY, LOI_NHAT_KY) from None

    def luu_nhap(self, dang_nhap, payload):
        return self._write(dang_nhap, 'LUU_NHAP', _payload(payload, luu=True))

    def cong_bo(self, dang_nhap, payload):
        return self._write(dang_nhap, 'CONG_BO', _payload(payload))

    def kich_hoat(self, dang_nhap, payload):
        """Readiness MTQ-1 luôn false: không cho bật ở MTQ-2."""
        return self._write(dang_nhap, 'KICH_HOAT', _payload(payload))

    def phong(self, dang_nhap, payload):
        return self._write(dang_nhap, 'PHONG', _payload(payload, quan_tri='PHONG'))

    def gan_vai(self, dang_nhap, payload):
        return self._write(dang_nhap, 'GAN_VAI', _payload(payload, quan_tri='GAN_VAI'))

    def pham_vi(self, dang_nhap, payload):
        return self._write(dang_nhap, 'PHAM_VI', _payload(payload, quan_tri='PHAM_VI'))

    def admin(self, dang_nhap, payload):
        return self._write(dang_nhap, 'ADMIN', _payload(payload, quan_tri='ADMIN'))
