"""Transaction gốc đúng login module; handler/dịch vụ cùng dùng một tx.

Pool/factory được bootstrap cấp, trả context manager cho connection IDLE.
Thoát ``with`` thành công mới commit; mọi lỗi rollback. Không có commit trên
handle. Connection bẩn hoặc không dọn sạch được bị đóng trước khi trả pool.
Không lưu credential/DSN; engine không được bootstrap cửa transaction này.
"""

from contextlib import contextmanager
import logging
import re
import time
from types import SimpleNamespace

from ..core import mtq, phien, su_kien, tiep_nhan, viec
from .ngu_canh import NguCanh, _DA_KIEM, _xoa_loi


class LoiGiaoDich(RuntimeError):
    def __init__(self, ma='SDK_GIAO_DICH', http_status=500):
        self.ma, self.http_status = ma, http_status
        super().__init__('Transaction SDK thất bại (' + ma + ')')


_LOI_CORE = {su_kien.LoiSuKien: su_kien._LOI,
             tiep_nhan.LoiTiepNhan: tiep_nhan._LOI, viec.LoiViec: viec._LOI}
_MA_CORE = frozenset().union(*_LOI_CORE.values())
_MA_SDK = {'SDK_GIAO_DICH', 'SDK_TX_DA_DONG', 'SDK_LOGIN', 'SDK_NGU_CANH', 'SDK_UY_NHIEM'}
_LOG = logging.getLogger(__name__)


class _LoiCSDL(RuntimeError):
    """Giữ mã lỗi đã biết cho wrapper Core; bỏ message/diagnostic tự do."""

    def __init__(self, ma, sqlstate):
        super().__init__('Lệnh CSDL thất bại')
        self.diag = SimpleNamespace(message_primary=ma)
        self.sqlstate = sqlstate


_DON = """SELECT set_config('ktt.ma_phien','',false),
    set_config('ktt.module','',false), set_config('ktt.phap_nhan_id','',false),
    set_config('ktt.hanh_dong','',false), set_config('ktt.viec_id','',false),
    set_config('ktt.the_he','',false)"""


def _don(conn):
    if conn.info.transaction_status != 0:
        raise LoiGiaoDich()
    with conn.transaction():
        conn.execute(_DON)
        conn.execute('RESET ROLE')
        conn.execute('RESET search_path')
        conn.execute('RESET ALL')
        conn.execute('SELECT pg_advisory_unlock_all()')
        conn.execute('UNLISTEN *')


def _goi_csdl(goi, *tham_so):
    ma = sqlstate = None
    try:
        return goi(*tham_so)
    except Exception as exc:
        chinh = getattr(getattr(exc, 'diag', None), 'message_primary', None)
        if isinstance(chinh, str) and chinh in _MA_CORE:
            ma = chinh
        trang_thai = getattr(exc, 'sqlstate', None)
        if isinstance(trang_thai, str) and re.fullmatch('[0-9A-Z]{5}', trang_thai):
            sqlstate = trang_thai
        _xoa_loi(exc)
    goi = tham_so = chinh = trang_thai = None
    raise _LoiCSDL(ma, sqlstate)


class _ConTro:
    """Chỉ đọc kết quả, không chuyển tiếp thuộc tính tới cursor/connection."""

    __slots__ = ('__tx', '__cursor')

    def __init__(self, tx, cursor):
        self.__tx, self.__cursor = tx, cursor

    def __repr__(self):
        return 'ConTro(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize con trỏ SDK')

    @property
    def rowcount(self):
        self.__tx._kiem()
        return self.__cursor.rowcount

    def fetchone(self):
        self.__tx._kiem()
        return _goi_csdl(self.__cursor.fetchone)

    def fetchmany(self, size=1):
        self.__tx._kiem()
        return _goi_csdl(self.__cursor.fetchmany, size)

    def fetchall(self):
        self.__tx._kiem()
        return _goi_csdl(self.__cursor.fetchall)

    def __iter__(self):
        self.__tx._kiem()
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


class GiaoDich:
    __slots__ = ('_conn', '_ctx', '_mo')

    def __init__(self, conn, ctx):
        self._conn, self._ctx, self._mo = conn, ctx, True

    def __repr__(self):
        return 'GiaoDich(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize GiaoDich')

    def _kiem(self):
        if not self._mo or self._conn.info.transaction_status != 2:
            raise LoiGiaoDich('SDK_TX_DA_DONG')

    @property
    def info(self):
        self._kiem()
        return SimpleNamespace(transaction_status=self._conn.info.transaction_status)

    @property
    def ngu_canh(self):
        self._kiem()
        return self._ctx

    def execute(self, cau, tham_so=None):
        self._kiem()
        try:
            return _ConTro(self, _goi_csdl(self._conn.execute, cau, tham_so))
        finally:
            cau = tham_so = None


class CuaGiaoDich:
    """Cấu hình tin cậy từ bootstrap; module không được chọn pool theo request.

    ``dang_nhap_csdl`` là login đã ghim, không phải role để SET ROLE. CSDL
    tiếp tục đối chiếu session_user của mã ủy nhiệm qua cửa G2-03/G2-06.
    """

    def __init__(self, *, module, dang_nhap_csdl, ket_noi, dong_ho=time.time):
        if (not isinstance(module, str) or not re.fullmatch('[a-z][a-z0-9_]{0,30}', module)
                or not isinstance(dang_nhap_csdl, str)
                or not re.fullmatch(r'(?:[a-z][a-z0-9_]*_)?dang_nhap_mod_' + module, dang_nhap_csdl)
                or len(dang_nhap_csdl) > 63 or not callable(ket_noi)):
            raise LoiGiaoDich('SDK_LOGIN', 403)
        self.module, self.dang_nhap_csdl = module, dang_nhap_csdl
        self._ket_noi, self._dong_ho = ket_noi, dong_ho

    def __repr__(self):
        return 'CuaGiaoDich(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize cửa transaction')

    @contextmanager
    def giao_dich(self, ctx):
        if (not isinstance(ctx, NguCanh) or ctx._da_kiem is not _DA_KIEM
                or ctx.module != self.module or self._dong_ho() >= ctx.hieu_luc_den):
            raise LoiGiaoDich('SDK_NGU_CANH', 401)
        loi = None
        tx = None
        thanh_cong = False
        da_commit = da_don = False
        try:
            with self._ket_noi() as conn:
                try:
                    _don(conn)
                    with conn.transaction():
                        login = conn.execute('SELECT session_user, current_user').fetchone()
                        if tuple(login) != (self.dang_nhap_csdl, self.dang_nhap_csdl):
                            raise LoiGiaoDich('SDK_LOGIN', 403)
                        identity = phien.xac_minh_phien(conn, ma=ctx.ma, module=ctx.module,
                            phap_nhan_id=ctx.phap_nhan_id, hanh_dong=ctx.hanh_dong)
                        if identity is None:
                            raise LoiGiaoDich('SDK_UY_NHIEM', 401)
                        if (identity.nguoi_dung_id != ctx.nguoi_dung_id
                                or identity.module != ctx.module or identity.phap_nhan_id != ctx.phap_nhan_id
                                or identity.hanh_dong != ctx.hanh_dong
                                or identity.viec_id is not None or identity.the_he is not None):
                            raise LoiGiaoDich('SDK_UY_NHIEM', 403)
                        mtq.dat_ngu_canh(conn, ma=ctx.ma, module=ctx.module,
                            phap_nhan_id=ctx.phap_nhan_id, hanh_dong=ctx.hanh_dong)
                        conn.execute("SELECT set_config('search_path',%s,true)",
                                     ('pg_catalog,mod_' + self.module + ',pg_temp',))
                        tx = GiaoDich(conn, ctx)
                        try:
                            yield tx
                            tx._kiem()
                        finally:
                            tx._mo = False
                    da_commit = True
                finally:
                    try:
                        _don(conn)
                        da_don = True
                    except BaseException:
                        conn.close()
                        raise
            thanh_cong = da_commit and da_don
        except Exception as exc:
            # Bao gồm lỗi handler/commit/pool; không giữ traceback driver có bind.
            if type(exc) is LoiGiaoDich and exc.ma in _MA_SDK:
                loi = (exc.ma, exc.http_status)
            elif type(exc) in _LOI_CORE and exc.ma in _LOI_CORE[type(exc)]:
                loi = (exc.ma, exc.http_status)
            elif isinstance(exc, mtq.LoiMTQ) and exc.ma == '42501':
                loi = ('42501', 403)
            elif isinstance(exc, phien.LoiPhien):
                loi = ('SDK_UY_NHIEM', 403 if getattr(exc, 'http_status', None) == 403 else 401)
            else:
                ma = getattr(exc, 'ma', None)
                status = getattr(exc, 'http_status', None)
                if (isinstance(ma, str) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}', ma)
                        and type(status) is int and 400 <= status <= 599):
                    loi = (ma, status)
            loai_loi = type(exc).__name__
            if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,79}', loai_loi):
                loai_loi = 'Exception'
            _LOG.warning('loai_loi=%s request_id=%s', loai_loi, ctx.request_id)
            _xoa_loi(exc)
        if tx is not None:
            tx._mo = False
            tx._conn = None
        if loi is not None:
            raise LoiGiaoDich(*loi) from None
        if not thanh_cong:
            raise LoiGiaoDich() from None
