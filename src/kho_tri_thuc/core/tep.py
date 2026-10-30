"""Kho bytes DEMO bọc write_immutable; quyền luôn lấy lại qua G2-09.

Caller mở transaction Core trước tai_len/phuc_hoi; các hàm chỉ tạo savepoint.
Ý định và staging được giữ để đối chiếu cả khi rollback/crash, không giữ token.
Kích hoạt là bước filesystem riêng, có thể lặp; bytes chưa có metadata không
thể tải. G2-29 chịu trách nhiệm retention staging, không tự xóa tại đây.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import ntpath
from pathlib import Path
import re
import stat
import unicodedata
from uuid import UUID
import zipfile

from ..ha_tang.store import write_immutable
from ..giao_dien.intake import Intake
from . import tai_lieu

TOI_DA = 20 * 1024 * 1024


class LoiTep(RuntimeError):
    def __init__(self, ma):
        self.ma = ma
        super().__init__('Thao tác tệp thất bại (' + ma + ')')


def _cam(path):
    raw = str(path).replace('/', '\\')
    parts = ntpath.normcase(ntpath.normpath(raw)).split('\\')
    parts = [p.rstrip(' .') for p in parts]
    if (raw.startswith(('\\\\?\\', '\\\\.\\')) or 'du-lieu-ke-toan' in parts
            or any(a == 'var' and b in {'plhn-that', 'web-that'} for a, b in zip(parts, parts[1:]))
            or any(p in {'.env', 'cau_hinh.that.toml'} or p.endswith('.local.json') for p in parts)):
        raise LoiTep('TEP_DICH_KHONG_DEMO')


def _khong_chuyen_huong(path):
    _cam(path)
    for p in (path, *path.parents):
        if p.is_symlink() or (p.exists() and getattr(p.stat(), 'st_file_attributes', 0)
                              & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)):
            raise LoiTep('TEP_DUONG_DAN')
    resolved = path.resolve()
    _cam(resolved)
    return resolved


def _can_tx(conn):
    # psycopg TransactionStatus.INTRANS = 2; không tự mở/commit transaction gốc.
    if conn.info.transaction_status != 2:
        raise LoiTep('TEP_CAN_GIAO_DICH')


def _doc_luong(luong, gioi_han):
    if type(gioi_han) is not int or not 0 < gioi_han <= TOI_DA:
        raise ValueError('Giới hạn capability phải trong 1..20 MiB')
    data = bytearray()
    while True:
        # Chỉ xin thêm tối đa một byte để phát hiện vượt giới hạn ngay.
        chunk = luong.read(min(65536, gioi_han - len(data) + 1))
        if not isinstance(chunk, bytes):
            raise ValueError('Luồng phải trả bytes')
        if len(data) + len(chunk) > gioi_han:
            raise LoiTep('TEP_QUA_LON')
        if not chunk:
            return bytes(data)
        data.extend(chunk)


def _mime(content):
    """Nhận dạng bytes, không tin extension/MIME client; ZIP không giải nén."""
    if content.startswith(b'%PDF-'):
        return 'application/pdf'
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if content.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if zipfile.is_zipfile(io.BytesIO(content)):
        return 'application/zip'
    if content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        return 'application/x-ole-storage'
    try:
        text = content.decode('utf-8-sig')
    except UnicodeError:
        return 'application/octet-stream'
    if any(ord(c) < 32 and c not in '\r\n\t' for c in text):
        return 'application/octet-stream'
    try:
        json.loads(text)
        return 'application/json'
    except (ValueError, RecursionError):
        return 'text/plain'


def _ten(ten):
    if not isinstance(ten, str):
        raise ValueError('Tên tệp không hợp lệ')
    ten = unicodedata.normalize('NFC', ten)
    if (not ten.strip() or len(ten) > 240 or ten in {'.', '..'}
            or any(c in '/\\:' or ord(c) < 32 or ord(c) == 127 for c in ten)):
        raise ValueError('Tên tệp không hợp lệ')
    return ten


class KhoTep:
    def __init__(self, root):
        path = Path(root).absolute()
        _cam(path)
        if (len(path.parts) < 5 or path.parts[-1] != 'kho-file'
                or path.parts[-4:-2] != ('var', 'core-demo')
                or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,40}', path.parts[-2])):
            raise LoiTep('TEP_DICH_KHONG_DEMO')
        self.root = _khong_chuyen_huong(path)
        # Dùng lại bộ chứa/kiểm đường dẫn intake. Không gọi receive(): cửa đó
        # thuộc tiếp nhận nguồn cũ (metadata riêng và giới hạn 50 MiB).
        self._intake = Intake(self.root)

    def _path(self, relative):
        p = self._intake.safe_path(relative)
        if not _khong_chuyen_huong(p).is_relative_to(self.root):
            raise LoiTep('TEP_DUONG_DAN')
        return p

    def _ghi(self, relative, content):
        p = self._path(relative)
        # Hàm cũ còn dùng staging nội bộ; kiểm cả thư mục đó trước khi gọi.
        self._path(str(Path(relative).parent / '.ktt-staging'))
        write_immutable(p, content)

    def _doc_kiem(self, relative, bam, size):
        p = self._path(relative)
        with p.open('rb') as stream:
            content = stream.read(TOI_DA + 1)
        if len(content) != size or hashlib.sha256(content).hexdigest() != bam:
            raise LoiTep('TEP_HASH')
        return content

    def _kich_hoat(self, intent):
        meta = intent['thong_tin']
        if self._path(meta['khoa_luu_tru']).exists():
            self._doc_kiem(meta['khoa_luu_tru'], meta['sha256'], meta['kich_thuoc'])
            return
        rel = 'staging/' + intent['request_id'] + '/noi_dung'
        content = self._doc_kiem(rel, meta['sha256'], meta['kich_thuoc'])
        self._ghi(meta['khoa_luu_tru'], content)

    def _ghi_metadata(self, conn, intent, ctx):
        with conn.transaction():
            tep_id = tai_lieu.ghi_tep_da_kiem(conn, tai_lieu_id=intent['tai_lieu_id'],
                thong_tin=intent['thong_tin'], request_id=intent['request_id'], **ctx)
            tai_lieu.gan_bien_the(conn, tai_lieu_id=intent['tai_lieu_id'], tep_id=tep_id,
                bien_the=intent['bien_the'], revision_truoc=intent['revision_truoc'],
                request_id=intent['request_id'], **ctx)
            self._kich_hoat(intent)
        return self._tham_chieu(tep_id, intent['thong_tin'])

    @staticmethod
    def _tham_chieu(tep_id, meta):
        han = meta.get('het_han_luc')
        if han is not None:
            han = datetime.fromisoformat(han.replace('Z', '+00:00'))
            han = han.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        return dict(contract='tham_chieu_tep.v1', phien_ban='1.0.0', tep_id=str(tep_id),
            **{k: meta[k] for k in ('ten_tep', 'mime', 'kich_thuoc', 'sha256')},
            het_han_luc=han)

    def tai_len(self, conn, *, luong, ten, tai_lieu_id, bien_the, revision_truoc,
                request_id, het_han_luc=None, gioi_han=TOI_DA, **ctx):
        """Không nhận đường dẫn hay MIME caller; trả tham chiếu, chưa phải ACK commit.

        Bản gốc dùng het_han_luc=None. Caller Core áp chính sách retention tương
        ứng cho kết quả tạm; không có chính sách thì không gọi cửa này.
        """
        _can_tx(conn)
        tai_lieu._ngu_canh(**ctx)
        if ctx['hanh_dong'].split(':')[-1] not in {'LAP', 'SUA'}:
            raise ValueError('Cần hành động ghi')
        ten = _ten(ten)
        bien_the = tai_lieu._bien_the(bien_the)
        tai_lieu._so(revision_truoc)
        rid, tid = str(UUID(str(request_id))), str(UUID(str(tai_lieu_id)))
        if het_han_luc is not None:
            han = datetime.fromisoformat(het_han_luc.replace('Z', '+00:00'))
            if han.tzinfo is None or han <= datetime.now(timezone.utc):
                raise ValueError('Thời hạn tạm phải ở tương lai và có múi giờ')
            het_han_luc = han.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        content = _doc_luong(luong, gioi_han)
        bam = hashlib.sha256(content).hexdigest()
        intent = dict(request_id=rid, tai_lieu_id=tid, bien_the=bien_the,
            revision_truoc=revision_truoc, module=ctx['module'],
            phap_nhan_id=str(UUID(str(ctx['phap_nhan_id']))),
            thong_tin=dict(ten_tep=ten, sha256=bam, kich_thuoc=len(content), mime=_mime(content),
                khoa_luu_tru='raw/' + bam, het_han_luc=het_han_luc))
        self._ghi('staging/' + rid + '/y_dinh.json',
                  json.dumps(intent, ensure_ascii=False, sort_keys=True).encode('utf-8'))
        if self._path(intent['thong_tin']['khoa_luu_tru']).exists():
            self._doc_kiem(intent['thong_tin']['khoa_luu_tru'], bam, len(content))
        else:
            self._ghi('staging/' + rid + '/noi_dung', content)
        return self._ghi_metadata(conn, intent, ctx)

    def phuc_hoi(self, conn, *, request_id, **ctx):
        """Đối chiếu bằng phiên hiện tại; không retry mù hoặc tăng revision.

        Dùng lại ý định sau rollback hoặc sau commit mất response. Nếu bản ở
        revision dự kiến khác nội dung, dừng để lead đối chiếu, giữ staging.
        """
        _can_tx(conn)
        tai_lieu._ngu_canh(**ctx)
        rid = str(UUID(str(request_id)))
        intent = json.loads(self._path('staging/' + rid + '/y_dinh.json').read_text(encoding='utf-8'))
        if (intent['request_id'] != rid or intent['module'] != ctx['module']
                or intent['phap_nhan_id'] != str(UUID(str(ctx['phap_nhan_id'])))):
            raise LoiTep('TEP_PHAM_VI')
        meta = intent['thong_tin']
        if (not re.fullmatch('[0-9a-f]{64}', meta['sha256'])
                or meta['khoa_luu_tru'] != 'raw/' + meta['sha256']):
            raise LoiTep('TEP_HASH')
        view = tai_lieu.lay(conn, tai_lieu_id=intent['tai_lieu_id'], bien_the=intent['bien_the'],
            **{**ctx, 'hanh_dong': ctx['hanh_dong'].rsplit(':', 1)[0] + ':XEM'})
        for row in view['tep']:
            if row['so_phien_ban'] == intent['revision_truoc'] + 1:
                ref = row['tham_chieu']
                han_ref = ref.get('het_han_luc')
                han_meta = meta.get('het_han_luc')
                if han_ref is not None:
                    han_ref = datetime.fromisoformat(han_ref.replace('Z', '+00:00'))
                if han_meta is not None:
                    han_meta = datetime.fromisoformat(han_meta.replace('Z', '+00:00'))
                if (han_ref != han_meta or any(ref[k] != meta[k]
                        for k in ('sha256', 'kich_thuoc', 'mime', 'ten_tep'))):
                    raise LoiTep('TEP_XUNG_DOT_PHUC_HOI')
                self._kich_hoat(intent)
                return ref
        return self._ghi_metadata(conn, intent, ctx)

    def tham_chieu(self, conn, *, tai_lieu_id, tep_id, bien_the, **ctx):
        # G2-09 kiểm phiên + MTQ + quyền nội dung ngay mỗi lần, trước mở file.
        tep_id = str(UUID(str(tep_id)))
        view = tai_lieu.lay(conn, tai_lieu_id=tai_lieu_id, bien_the=bien_the, **ctx)
        for row in view['tep']:
            ref = row['tham_chieu']
            if ref['tep_id'] == tep_id:
                if ref['het_han_luc'] is not None and datetime.fromisoformat(
                        ref['het_han_luc'].replace('Z', '+00:00')) <= datetime.now(timezone.utc):
                    raise LoiTep('TEP_HET_HAN')
                if not re.fullmatch('[0-9a-f]{64}', ref['sha256']):
                    raise LoiTep('TEP_HASH')
                return ref
        raise LoiTep('TEP_KHONG_THAY')

    def mo_doc(self, conn, *, tai_lieu_id, tep_id, bien_the, **ctx):
        ref = self.tham_chieu(conn, tai_lieu_id=tai_lieu_id, tep_id=tep_id, bien_the=bien_the, **ctx)
        content = self._doc_kiem('raw/' + ref['sha256'], ref['sha256'], ref['kich_thuoc'])
        return io.BytesIO(content)
