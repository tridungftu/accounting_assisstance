"""MTQ-2: cấu hình qua SQL MTQ-1; chưa thay nguồn quyền nghiệp vụ.

Tái dùng CrmMauK2.danh_tinh/_tx (owner connection + GUC). Pháp nhân suy
từ bản/phòng trong CSDL, không nhận actor/pháp nhân từ HTTP. Bootstrap chỉ
thuộc công cụ lead. Biên nhận HTTP nằm trong sổ bất biến, cùng giao dịch
với cấu hình; kiểm Admin hiện hành trước replay. Chặn ghi ở giao dịch riêng
sau rollback; lỗi audit không được nuốt.
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
MA_403 = frozenset(('MTQ_CHI_ADMIN', 'MTQ_DANH_TINH', 'DANH_TINH', 'DANH_TINH_MO_PHONG',
                    'CRM_PHIEN', 'SESSION_TOKEN', 'CROSS_ORIGIN', 'LOCAL_HOST_ONLY'))
MA_409 = frozenset(('MTQ_REVISION', 'MTQ_IDEMPOTENCY_KHAC', 'MTQ_BAT_BIEN',
                    'MTQ_THIEU_DONG', 'MTQ_CHUA_NOI_MTQ4', 'CRM_G_GIAO_DICH_NGOAI'))


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
    _sai('Mã đối tượng/khóa yêu cầu phải là UUID.')


def _payload(value, *, luu=False):
    fields = {'phien_ban_id', 'expected_revision', 'ly_do', 'khoa'}
    if luu:
        fields |= {'nguon_id', 'dong'}
    _object(value, fields, {'expected_revision', 'ly_do', 'khoa'})
    p = dict(value)
    rev = p['expected_revision']
    if type(rev) is not int or not 0 <= rev <= 9223372036854775807:
        _sai('Revision phải là số nguyên không âm.')
    if not isinstance(p['ly_do'], str) or not p['ly_do'].strip() or len(p['ly_do']) > 2000:
        _sai('Cần lý do, tối đa 2.000 ký tự.')
    p['ly_do'] = p['ly_do'].strip()
    p['khoa'] = _uuid(p['khoa'])
    for key in ('phien_ban_id', 'nguon_id'):
        if p.get(key) is not None:
            p[key] = _uuid(p[key])
    if not luu and not p.get('phien_ban_id'):
        _sai('Cần phiên bản công bố/kích hoạt.')
    if luu:
        if p.get('phien_ban_id') and p.get('nguon_id'):
            _sai('Chỉ chọn bản nháp hoặc bản nguồn.')
        rows = p.get('dong', [])
        if not isinstance(rows, list) or len(rows) > 500:
            _sai('Danh sách tối đa 500 dòng.')
        seen = set()
        clean = []
        for row in rows:
            _object(row, {'phong_id', 'vai', 'gioi_han_vnd', 'o'}, {'phong_id', 'vai', 'gioi_han_vnd', 'o'})
            phong = _uuid(row['phong_id'])
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
                    _sai('Ô không thuộc danh mục, bị lặp hoặc tick không phải boolean.')
                keys.add(key)
            clean.append({'phong_id': phong, 'vai': row['vai'], 'gioi_han_vnd': money, 'o': [dict(c) for c in cells]})
        p['dong'] = clean
        if not clean and not p.get('nguon_id'):
            _sai('Cần dòng thay đổi hoặc snapshot nguồn.')
        if not p.get('phien_ban_id') and rev != 0:
            _sai('Tạo nháp cần revision 0.')
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
            admin = self._admin(c) and not cua_toi
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
            for row in rows:
                row['o'] = self._many(c, 'SELECT module,man,hanh_dong,cho_phep FROM master.mtq_o WHERE dong_id=%s::uuid ORDER BY module,man,hanh_dong', (row['id'],))
            return {'admin': admin, 'dong': rows, 'phong': rooms, 'phien_ban': versions,
                    'gan_vai': assignments, 'pham_vi': scopes, 'kich_hoat': activation,
                    'danh_muc': self._many(c, 'SELECT * FROM master.mtq_danh_muc_hanh_dong ORDER BY module,man,hanh_dong'),
                    'chua_noi_mtq4': True}

    def nhat_ky(self, dang_nhap):
        dt = self.mau.danh_tinh(dang_nhap)
        with self.mau._tx(dt, rr=True) as c:
            if not self._admin(c):
                raise DataError('MTQ_CHI_ADMIN', 'Chỉ Admin được xem toàn bộ nhật ký.')
            return {'thay_doi': self._many(c, 'SELECT * FROM nhat_ky.mtq_thay_doi ORDER BY luc,id'),
                    'tu_choi': self._many(c, 'SELECT * FROM nhat_ky.mtq_tu_choi ORDER BY luc,id')}

    @staticmethod
    def _sql(c, request, command, data, revision, reason):
        return c.execute('SELECT master.mtq_cau_hinh_ghi(%s::uuid,%s,%s::jsonb,%s,%s) AS r',
                         (request, command, json.dumps(data, ensure_ascii=False), revision, reason)).fetchone()['r']

    def _version(self, c, pb):
        v = self._one(c, 'SELECT * FROM master.mtq_phien_ban WHERE id=%s::uuid', (pb,))
        if v is None:
            raise DataError('MTQ_REVISION', 'Phiên bản không tồn tại hoặc đã thay đổi.')
        return v

    def _save(self, c, p):
        source = p.get('phien_ban_id') or p.get('nguon_id')
        v = self._version(c, source) if source else None
        pn = v['phap_nhan_id'] if v else None
        for row in p['dong']:
            room = self._one(c, 'SELECT phap_nhan_id FROM master.mtq_phong WHERE id=%s::uuid AND hoat_dong', (row['phong_id'],))
            if room is None or (pn is not None and pn != room['phap_nhan_id']):
                _sai('Phòng không hoạt động hoặc khác pháp nhân của phiên bản.')
            pn = room['phap_nhan_id']
        args = (p['khoa'], p['ly_do'])
        if not p.get('phien_ban_id'):
            v = self._sql(c, args[0], 'NHAP', {'phap_nhan_id': pn, 'phien_ban_id': p.get('nguon_id')}, 0, args[1])
        elif v['revision'] != p['expected_revision'] or v['trang_thai'] != 'NHAP':
            raise DataError('MTQ_REVISION', 'Bản nháp đã thay đổi; tải lại trước khi lưu.')
        for row in p['dong']:
            r = self._sql(c, args[0], 'DONG', {'phien_ban_id': v['id'], **{k: row[k] for k in ('phong_id', 'vai', 'gioi_han_vnd')}}, v['revision'], args[1])
            v, d = r['phien_ban'], r['doi_tuong']
            for cell in row['o']:
                r = self._sql(c, args[0], 'O', {'phien_ban_id': v['id'], 'dong_id': d['id'], **cell}, v['revision'], args[1])
                v = r['phien_ban']
        return v

    def _write(self, dang_nhap, command, p):
        dt = self.mau.danh_tinh(dang_nhap)
        try:
            with self.mau._tx(dt) as c:
                c.execute('SELECT pg_advisory_xact_lock(742601, 1)')
                if not self._admin(c):
                    raise DataError('MTQ_CHI_ADMIN', 'Chỉ Admin hoạt động được sửa ma trận.')
                old = self._one(c, 'SELECT actor_id,doi_tuong,loai_su_kien,sau FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid AND loai_su_kien LIKE \'HTTP_%%\'', (p['khoa'],))
                if old:
                    if old['actor_id'] != dt['id'] or old['loai_su_kien'] != 'HTTP_' + command or old['doi_tuong'] != p:
                        raise DataError('MTQ_IDEMPOTENCY_KHAC', 'Khóa yêu cầu đã dùng với nội dung/danh tính khác.')
                    return {**old['sau'], 'lap_lai': True}
                if c.execute('SELECT 1 FROM nhat_ky.mtq_thay_doi WHERE request_id=%s::uuid LIMIT 1', (p['khoa'],)).fetchone():
                    raise DataError('MTQ_IDEMPOTENCY_KHAC', 'Khóa yêu cầu đã dùng bởi công cụ quản trị.')
                if command == 'LUU_NHAP':
                    v = self._save(c, p)
                else:
                    v = self._version(c, p['phien_ban_id'])
                    data = {'phap_nhan_id': v['phap_nhan_id'], 'phien_ban_id': v['id']}
                    if command == 'KICH_HOAT':
                        data['bat'] = True  # Không nhận bat=false để quay lại legacy.
                    r = self._sql(c, p['khoa'], command, data, p['expected_revision'], p['ly_do'])
                    v = r['phien_ban'] if command == 'CONG_BO' else r
                result = {'ket_qua': _v(v), 'lap_lai': False}
                c.execute("""INSERT INTO nhat_ky.mtq_thay_doi
                    (request_id,phap_nhan_id,doi_tuong_bang,doi_tuong,phien_ban_id,revision,loai_su_kien,truoc,sau,actor_id,actor_login,ly_do)
                    VALUES (%s::uuid,%s::uuid,'HTTP',%s::jsonb,%s::uuid,%s,%s,NULL,%s::jsonb,%s::uuid,%s,%s)""",
                    (p['khoa'], v['phap_nhan_id'], json.dumps(p, ensure_ascii=False),
                     v['id'] if command != 'KICH_HOAT' else v['phien_ban_id'], v['revision'],
                     'HTTP_' + command, json.dumps(result, ensure_ascii=False), dt['id'], dt['dang_nhap'], p['ly_do']))
                return result
        except Exception as exc:
            # Không nuốt lỗi driver; chỉ chuyển mã MTQ đã whitelist từ SQL.
            error = exc
            if not isinstance(error, DataError):
                primary = getattr(getattr(exc, 'diag', None), 'message_primary', '') or ''
                code = primary.split(':', 1)[0]
                if re.fullmatch(r'MTQ_[A-Z0-9_]+', code):
                    error = DataError(code, f'CSDL từ chối cấu hình ({code}).')
            if isinstance(error, DataError) and error.code.startswith('MTQ_'):
                with self.mau._tx(dt) as c:
                    c.execute("""INSERT INTO nhat_ky.mtq_tu_choi
                        (request_id,actor_id,actor_login,ma,ly_do) VALUES (%s::uuid,%s::uuid,%s,%s,%s)""",
                        (p['khoa'], dt['id'], dt['dang_nhap'], error.code, str(error)))
                raise error from None
            raise

    def luu_nhap(self, dang_nhap, payload):
        return self._write(dang_nhap, 'LUU_NHAP', _payload(payload, luu=True))

    def cong_bo(self, dang_nhap, payload):
        return self._write(dang_nhap, 'CONG_BO', _payload(payload))

    def kich_hoat(self, dang_nhap, payload):
        """Readiness MTQ-1 luôn false: không cho bật ở MTQ-2."""
        return self._write(dang_nhap, 'KICH_HOAT', _payload(payload))
