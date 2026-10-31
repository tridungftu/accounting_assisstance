"""Khung tiến trình G2-21, cổng cố định và CAS của G2-16.

giao_dich là context manager factory cấp kết nối Core và commit mỗi thao tác
sổ cổng trước khi trả về. Hồ sơ/lenh/tham_so đã được bên cài đặt kiểm duyệt.
Đây chưa phải launcher tài khoản riêng (G2-33/33b); không tự đổi quyền máy.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hmac
import math
import os
import re
import secrets
import socket
import subprocess
import threading
import time
from types import SimpleNamespace
from uuid import UUID, uuid4

from . import so_cong
from ..nguon.trich6_host import LoiHost, Trich6Host, _JobWindows, _doc_dong, env_con
from ..sdk_core.bootstrap import (PROTOCOL, dinh_danh_lan_tao, doc_thong_diep,
                                  gui_thong_diep)
from ..sdk_core.ngu_canh import _xoa_loi


_KHOA = threading.Lock()
_CHU = {}


class LoiTienTrinh(RuntimeError):
    http_status = 503

    def __init__(self, ma, retry_after=2):
        self.ma = ma
        self.headers = {'Retry-After': str(retry_after)}
        super().__init__(ma)


def _ten_job(so_id, instance):
    # Cùng namespace qua cả lần Core restart ở Windows session khác.
    return 'Global\\ktt-' + str(so_id) + '-' + str(instance)


def _job(ten):
    if os.name != 'nt':
        raise LoiTienTrinh('CAN_WINDOWS')
    job = _JobWindows()
    # Tái dùng cấu hình/thuật toán Job hiện có, thêm tên để Core mới đối chiếu.
    c, w, k = job._c, job._w, job._k
    h = None
    try:
        class Basic(c.Structure):
            _fields_ = [('user', c.c_int64), ('job', c.c_int64), ('flags', w.DWORD),
                        ('min', c.c_size_t), ('max', c.c_size_t), ('active', w.DWORD),
                        ('affinity', c.c_size_t), ('priority', w.DWORD), ('schedule', w.DWORD)]
        class Ext(c.Structure):
            _fields_ = [('basic', Basic), ('io', c.c_ulonglong * 6),
                        ('limits', c.c_size_t * 4)]
        info = Ext()
        if not k.QueryInformationJobObject(job._h, 9, c.byref(info), c.sizeof(info), None):
            raise LoiTienTrinh('JOB_TRUY_VAN_LOI')
        h = k.CreateJobObjectW(None, ten)
        if not h or c.get_last_error() == 183:
            raise LoiTienTrinh('JOB_TAO_LOI')
        if not k.SetInformationJobObject(h, 9, c.byref(info), c.sizeof(info)):
            raise LoiTienTrinh('JOB_CAU_HINH_LOI')
        job.dong()
        job._h, h = h, None
        return job
    except BaseException:
        if h:
            k.CloseHandle(h)
        job.dong()
        raise


def _phien_da_dung(phien, dong=None):
    """Đối chiếu OS/bind loại trừ; không kill PID/Job lạ, lỗi => chưa xác nhận."""
    if os.name != 'nt':
        return False
    import ctypes as c
    from ctypes import wintypes as w
    k = c.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes, k.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
    k.OpenJobObjectW.argtypes, k.OpenJobObjectW.restype = [w.DWORD, w.BOOL, w.LPCWSTR], w.HANDLE
    k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    k.CloseHandle.argtypes = [w.HANDLE]
    k.QueryInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p]
    # Giữ handle PID trong suốt đối chiếu, chống PID tái sử dụng giữa hai phép đọc.
    h = k.OpenProcess(0x100000 | 0x1000, False, phien['pid'])
    if not h and c.get_last_error() != 87:
        return False
    try:
        # PID goc da dung khong chung minh worker da het. Phien thieu ten
        # Job con can bind loai tru dung dia chi/cong truoc khi tra so.
        if phien.get('ten_job') is None:
            cu = phien.get('dinh_danh_lan_tao')
            if not isinstance(cu, str) or not re.fullmatch('[0-9]{1,20}', cu) or int(cu) <= 0:
                return False
            if h:
                tao = dinh_danh_lan_tao(SimpleNamespace(_handle=h))
                if not isinstance(tao, str) or not re.fullmatch('[0-9]{1,20}', tao):
                    return False
                if not (int(tao) > int(cu)
                        or (int(tao) == int(cu) and k.WaitForSingleObject(h, 0) == 0)):
                    return False
            if (not dong or dong.get('dia_chi_nghe') not in ('127.0.0.1', '::1')
                    or type(dong.get('cong')) is not int or not 1024 <= dong['cong'] <= 65535):
                return False
            try:
                with socket.socket(socket.AF_INET6 if dong['dia_chi_nghe'] == '::1'
                                   else socket.AF_INET, socket.SOCK_STREAM) as nghe:
                    nghe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    nghe.bind((dong['dia_chi_nghe'], dong['cong']))
                return True
            except OSError:
                return False
        if h:
            tao = dinh_danh_lan_tao(SimpleNamespace(_handle=h))
            if tao == phien['dinh_danh_lan_tao'] and k.WaitForSingleObject(h, 0) != 0:
                return False
        j = k.OpenJobObjectW(4, False, phien['ten_job'])  # JOB_OBJECT_QUERY
        if not j:
            return c.get_last_error() == 2  # không tồn tại, KHÔNG suy từ access denied
        try:
            # JOBOBJECT_BASIC_ACCOUNTING_INFORMATION: 4 LARGE_INTEGER + 4 DWORD.
            info = (c.c_ulonglong * 6)()
            if not k.QueryInformationJobObject(j, 1, c.byref(info), c.sizeof(info), None):
                return False
            active = c.cast(c.byref(info, 40), c.POINTER(w.DWORD))[0]
            return active == 0
        finally:
            k.CloseHandle(j)
    finally:
        if h:
            k.CloseHandle(h)


def _doc_phien(conn, so_id):
    return so_cong._goi(conn, 'so_cong_doc_phien', (so_id,))


def _doi_chieu(conn, so_id, instance, the_he, bang_chung):
    return so_cong._goi(conn, 'so_cong_doi_chieu', (so_id, instance, the_he, bang_chung))


def _ghi_job(conn, so_id, instance, the_he, ten):
    return so_cong._goi(conn, 'so_cong_ghi_job', (so_id, instance, the_he, ten))


def _loi_chua_nhan(conn, so_id, the_he, ma):
    return so_cong._goi(conn, 'so_cong_loi_chua_nhan', (so_id, the_he, ma))


def _xac_nhan_accept(conn, so_id, instance, the_he):
    return so_cong._goi(conn, 'so_cong_xac_nhan_accept', (so_id, instance, the_he))


def _nhan_co_job(conn, so_id, instance, the_he, *, ten_job, **kwargs):
    dong = so_cong.nhan(conn, so_id, instance, the_he, **kwargs)
    if ten_job is not None:
        _ghi_job(conn, so_id, instance, dong['the_he'], ten_job)
    return dong


class TienTrinhCore:
    """Mỗi dòng sổ cổng chỉ có một controller trong Core; khóa dùng cùng dispatch.

    Core giữ handle nhưng không accept khi con sở hữu. Không trả raw handle cho
    dispatch. thu_hoi không kill khi drain quá hạn; kiem_con thu hồi sau crash.
    """

    def __init__(self, *, so_cong_id, giao_dich, lenh, phien_ban, issuer, contracts,
                 tham_so=None, ma_chu=None, cho_khoi_dong=120, cho_dung=30, popen=subprocess.Popen,
                 job_factory=None, doc_dong=_doc_dong, socket_factory=socket.socket,
                 doc_lan_tao=dinh_danh_lan_tao):
        if (not isinstance(lenh, (tuple, list)) or not lenh
                or not all(isinstance(s, str) and s for s in lenh)
                or not isinstance(phien_ban, str) or not phien_ban
                or not isinstance(issuer, str) or not issuer
                or (ma_chu is not None and (not isinstance(ma_chu, str)
                    or not re.fullmatch('[a-z][a-z0-9_]{0,30}', ma_chu)))
                or not isinstance(contracts, (tuple, list))
                or not all(isinstance(s, str) and s for s in contracts)
                or not 1 <= cho_khoi_dong <= 120 or not 0 < cho_dung <= 300
                or (tham_so is not None and not isinstance(tham_so, dict))):
            raise ValueError('Cấu hình tiến trình không hợp lệ')
        self.id = UUID(str(so_cong_id))
        self._giao_dich, self._lenh = giao_dich, list(lenh)
        self._phien_ban, self._issuer = phien_ban, issuer
        self._ma_chu = ma_chu
        self._contracts, self._tham_so = list(contracts), dict(tham_so or {})
        self._popen, self._job_factory = popen, job_factory
        self._doc_dong, self._socket_factory, self._doc_lan_tao = doc_dong, socket_factory, doc_lan_tao
        self.cho_khoi_dong, self.cho_dung = cho_khoi_dong, cho_dung
        self._proc = self._job = self._nghe = None
        self._nonce = self._lan_tao = self.instance_id = self.the_he = None
        self._da_nhan = self._khoa_loi = False
        self._da_dung = set()
        self.trang_thai, self.chu_accept = 'stopped', 'core'
        with _KHOA:
            self.khoa = _CHU.setdefault(self.id, (threading.RLock(), None))[0]

    def __repr__(self):
        return 'TienTrinhCore(' + self.trang_thai + ')'

    def _so(self, ham, *args, **kwargs):
        with self._giao_dich() as conn:
            return ham(conn, self.id, *args, **kwargs)

    def _giu_chu(self):
        with _KHOA:
            khoa, chu = _CHU[self.id]
            if chu is not None and chu is not self:
                raise LoiTienTrinh('CONG_DA_CO_CHU')
            _CHU[self.id] = khoa, self

    def _bo_chu(self):
        with _KHOA:
            khoa, chu = _CHU[self.id]
            if chu is self:
                _CHU[self.id] = khoa, None

    def _gui(self, kieu):
        gui_thong_diep(self._proc.stdin, {'protocol': PROTOCOL, 'kieu': kieu})

    def _kiem_san_sang(self, hs, dong):
        p = self._proc
        if (not isinstance(hs, dict) or hs.get('protocol') != PROTOCOL
                or hs.get('kieu') != 'san_sang' or hs.get('san_sang') is not True
                or type(hs.get('pid')) is not int or hs['pid'] != p.pid
                or hs.get('dinh_danh_lan_tao') != self._lan_tao
                or self._doc_lan_tao(p) != self._lan_tao or p.poll() is not None
                or hs.get('instance_id') != str(self.instance_id)
                or hs.get('module') != self._module
                or type(hs.get('cong')) is not int or hs['cong'] != dong['cong']
                or type(hs.get('the_he')) is not int or hs['the_he'] != self.the_he
                or hs.get('phien_ban') != self._phien_ban
                or hs.get('contracts') != self._contracts
                or not isinstance(hs.get('nonce_khoi_dong'), str)
                or not hmac.compare_digest(hs['nonce_khoi_dong'], self._nonce)):
            raise LoiTienTrinh('TIEN_TRINH_KHONG_HOP_LE')

    def _don_loi(self):
        # Dùng nguyên thuật toán EOF -> grace -> Job -> xác nhận terminal của #6/M2.
        don = SimpleNamespace(cho_dung=self.cho_dung, cho_job=10)
        don._cho_job_rong = lambda job, han: Trich6Host._cho_job_rong(don, job, han)
        # Host luôn đóng Job trong finally. Giữ handle thật nếu chưa xác nhận
        # dừng để kiem_con còn kiểm được worker, không đoán Job đã rỗng.
        job = None if self._job is None else SimpleNamespace(
            so_tien_trinh=self._job.so_tien_trinh, ket_thuc=self._job.ket_thuc,
            dong=lambda: None)
        Trich6Host._don(don, self._proc, job)
        if self._job is not None:
            self._job.dong()
        if self._da_nhan:
            self._da_dung.add((str(self.instance_id), self.the_he))
        self._proc = self._job = None

    def doi_chieu(self):
        """Đối chiếu cả lease chưa hết; CAS không thay thế bằng chứng OS/Job."""
        with self.khoa:
            dong = self._so(so_cong.doc)
            if dong['giu_boi'] is None:
                return dong
            with _KHOA:
                chu = _CHU[self.id][1]
                if chu is not None and chu is not self:
                    raise LoiTienTrinh('CONG_CAN_DOI_CHIEU')
            if self._proc is not None:
                raise LoiTienTrinh('CONG_CAN_DOI_CHIEU')
            phien = self._so(_doc_phien)
            if (not phien or str(phien['id']) != str(dong['giu_boi'])
                    or phien['the_he'] != dong['the_he']):
                raise LoiTienTrinh('CONG_CAN_DOI_CHIEU')
            da_dung = (str(dong['giu_boi']), dong['the_he']) in self._da_dung
            if not da_dung:
                try:
                    da_dung = _phien_da_dung(phien, dong)
                except Exception as exc:
                    _xoa_loi(exc)
            if not da_dung:
                raise LoiTienTrinh('CONG_CAN_DOI_CHIEU')
            return self._so(_doi_chieu, UUID(str(dong['giu_boi'])), dong['the_he'], uuid4())

    def khoi_dong(self):
        with self.khoa:
            if self.trang_thai == 'ready' and self._proc.poll() is None:
                return self.instance_id
            if self._proc is not None or self.trang_thai == 'dang_dung':
                raise LoiTienTrinh('TIEN_TRINH_DANG_DUNG')
            dong = self._so(so_cong.doc)
            if dong['trang_thai'] == 'LOI':
                raise LoiTienTrinh('KHOI_DONG_BI_KHOA')
            if dong['giu_boi'] is not None:
                dong = self.doi_chieu()
            thu_lai = dong.get('thu_lai_sau')
            if thu_lai:
                if isinstance(thu_lai, str):
                    thu_lai = datetime.fromisoformat(thu_lai)
                con_lai = (thu_lai - datetime.now(timezone.utc)).total_seconds()
                if con_lai > 0:
                    raise LoiTienTrinh('KHOI_DONG_LOI', math.ceil(con_lai))
            if (dong['dia_chi_nghe'] not in ('127.0.0.1', '::1')
                    or type(dong['cong']) is not int or not 1024 <= dong['cong'] <= 65535):
                raise ValueError('Sổ cổng không hợp lệ')
            module = dong['module'] or self._ma_chu
            if (not isinstance(module, str) or not re.fullmatch('[a-z][a-z0-9_]{0,30}', module)
                    or (dong['module'] is not None and self._ma_chu not in (None, module))):
                raise ValueError('Cần mã chủ từ hồ sơ đã duyệt')
            self._giu_chu()
            self.trang_thai = 'starting'
            self.instance_id, self._nonce = uuid4(), secrets.token_urlsafe(32)
            self._module = module
            yeu_cau = datetime.now(timezone.utc)
            han = time.monotonic() + self.cho_khoi_dong
            ma = 'KHOI_DONG_LOI'
            try:
                self._job = (_job(_ten_job(self.id, self.instance_id))
                             if self._job_factory is None else self._job_factory())
                self._proc = self._popen(self._lenh, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, env=env_con(), shell=False, close_fds=True,
                    creationflags=0x08000000 if os.name == 'nt' else 0)
                self._job.gan(self._proc)  # trước bất kỳ cấu hình/capability nào
                self._lan_tao = self._doc_lan_tao(self._proc)
                # Danh tinh Job va claim phai commit cung nhau: restart ngay sau
                # claim khong de lai mot phien khong biet Job nao de doi chieu.
                dong = self._so(_nhan_co_job, self.instance_id, dong['the_he'],
                    ten_job=_ten_job(self.id, self.instance_id) if self._job_factory is None else None,
                    pid=self._proc.pid, dinh_danh_lan_tao=self._lan_tao,
                    phien_ban=self._phien_ban, nhan_yeu_cau_luc=yeu_cau,
                    bat_dau_luc=datetime.now(timezone.utc), lease_giay=240)
                self.the_he, self._da_nhan, self._khoa_loi = dong['the_he'], True, False
                if self._nghe is None:
                    nghe = self._socket_factory(socket.AF_INET6 if dong['dia_chi_nghe'] == '::1'
                                               else socket.AF_INET, socket.SOCK_STREAM)
                    self._nghe = nghe
                    nghe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                    try:
                        nghe.bind((dong['dia_chi_nghe'], dong['cong']))
                    except OSError:
                        ma = 'CONG_BI_CHIEM'
                        raise LoiTienTrinh(ma) from None
                    nghe.listen()
                cfg = dict(protocol=PROTOCOL, kieu='khoi_dong', issuer=self._issuer,
                    module=self._module, instance_id=str(self.instance_id), pid=self._proc.pid,
                    dinh_danh_lan_tao=self._lan_tao, nonce_khoi_dong=self._nonce,
                    the_he=self.the_he, phien_ban=self._phien_ban, tham_so=self._tham_so,
                    cong=dong['cong'], dia_chi_nghe=dong['dia_chi_nghe'],
                    socket=base64.b64encode(self._nghe.share(self._proc.pid)).decode('ascii'))
                self.chu_accept = 'con'
                gui_thong_diep(self._proc.stdin, cfg)
                cfg = None
                con_lai = han - time.monotonic()
                if con_lai <= 0:
                    raise LoiTienTrinh('KHOI_DONG_QUA_HAN')
                dong_ready = self._doc_dong(self._proc.stdout, con_lai)
                if dong_ready is None:
                    raise LoiTienTrinh('KHOI_DONG_QUA_HAN')
                self._kiem_san_sang(doc_thong_diep(dong_ready), dong)
                if time.monotonic() >= han:
                    raise LoiTienTrinh('KHOI_DONG_QUA_HAN')
                self._so(so_cong.san_sang, self.instance_id, self.the_he, bang_chung_id=uuid4())
                self._gui('nhan_accept')
                self._so(_xac_nhan_accept, self.instance_id, self.the_he)
                self.trang_thai = 'ready'
                return self.instance_id
            except Exception as exc:
                if isinstance(exc, LoiTienTrinh):
                    ma = exc.ma
                _xoa_loi(exc)
            finally:
                cfg = dong_ready = None
            self.trang_thai = 'failed'
            # Ghi số lỗi/hạn thử lại bền vững trước cleanup, không rollback cùng lỗi.
            try:
                if self._da_nhan:
                    self._so(so_cong.loi_khoi_dong, self.instance_id, self.the_he, ma_loi=ma)
                    self._khoa_loi = True
                    loi = self._so(so_cong.doc)
                else:
                    loi = self._so(_loi_chua_nhan, dong['the_he'], ma)
                if loi['trang_thai'] == 'LOI':
                    ma = 'KHOI_DONG_BI_KHOA'
            finally:
                try:
                    self._don_loi()
                except Exception as exc:
                    _xoa_loi(exc)
                    raise LoiTienTrinh('DUNG_CHUA_XAC_NHAN') from None
                if self._nghe is not None:
                    self._nghe.close()
                    self._nghe = None
                self.chu_accept, self._nonce = 'core', None
                self._da_nhan = False
                self._bo_chu()
            raise LoiTienTrinh(ma)

    def gia_han(self):
        with self.khoa:
            return self._so(so_cong.gia_han, self.instance_id, self.the_he)

    def _thu_sau_khi_chet(self, *, da_xac_minh=False):
        ma = 'DUNG_CHUA_XAC_NHAN'
        da_dung = False
        try:
            da_dung = da_xac_minh or (self._proc.poll() is not None
                and self._job.so_tien_trinh() == 0)
        except LoiHost as exc:
            ma = exc.ma
            _xoa_loi(exc)
        if not da_dung:
            raise LoiTienTrinh(ma)
        # Thu hồi quyền trong máy trước: lỗi sổ không được giữ _proc/accept cũ.
        self._job.dong()
        self._da_dung.add((str(self.instance_id), self.the_he))
        proc = self._proc
        self._proc = self._job = self._nonce = None
        self._da_nhan = False
        self.trang_thai, self.chu_accept = 'stopped', 'core'
        for kenh in (proc.stdin, proc.stdout):
            try:
                kenh.close()
            except OSError:
                pass
        if not self._khoa_loi:
            ma = None
            try:
                self._so(so_cong.tra, self.instance_id, self.the_he)
            except Exception as exc:
                ma = exc.ma if isinstance(exc, so_cong.LoiSoCong) else 'CONG_THAT_BAI'
                _xoa_loi(exc)
            if ma is not None:
                raise LoiTienTrinh(ma)
        # Vẫn giữ listener: lần sau dùng đúng socket/cổng, không có khoảng hở bind.
        return True

    def kiem_con(self):
        with self.khoa:
            if self._proc is None or self._proc.poll() is None:
                return False
            proc = self._proc
        return self._cho_thu_hoi(proc)

    def _cho_thu_hoi(self, proc):
        # Job có thể cập nhật accounting sau khi handle tiến trình đã terminal.
        # Chờ worker ở ngoài khóa; mỗi lần chỉ truy vấn/finalize dưới khóa.
        han = time.monotonic() + min(self.cho_dung, 10)
        while True:
            with self.khoa:
                if self._proc is not proc:
                    return True
                ma = None
                try:
                    rong = self._job.so_tien_trinh() == 0
                except LoiHost as exc:
                    ma = exc.ma
                    _xoa_loi(exc)
                if ma:
                    raise LoiTienTrinh(ma)
                if rong:
                    return self._thu_sau_khi_chet(da_xac_minh=True)
            if time.monotonic() >= han:
                raise LoiTienTrinh('DUNG_CHUA_XAC_NHAN')
            time.sleep(0.05)

    def thu_hoi(self, *, timeout=300):
        if not 0 < timeout <= 300:
            raise ValueError('Hạn drain không hợp lệ')
        with self.khoa:
            if self._proc is None:
                return True
            proc = self._proc
            if proc.poll() is None:
                if self.trang_thai == 'dang_dung':
                    raise LoiTienTrinh('TIEN_TRINH_DANG_DUNG')
                # Chỉ đổi trạng thái/gửi lệnh dưới khóa; chờ terminal ở ngoài khóa.
                self._so(so_cong.gia_han, self.instance_id, self.the_he,
                         lease_giay=max(120, math.ceil(timeout) + 30))
                self.trang_thai = 'dang_dung'
                try:
                    self._gui('thu_hoi')
                except OSError:
                    raise LoiTienTrinh('DUNG_CHUA_XAC_NHAN') from None
        try:
            proc.wait(timeout)
        except (subprocess.TimeoutExpired, OSError):
            raise LoiTienTrinh('DUNG_CHUA_XAC_NHAN') from None
        return self._cho_thu_hoi(proc)

    def accept(self, *, timeout=0):
        with self.khoa:
            if self.trang_thai == 'dang_dung':
                raise LoiTienTrinh('TIEN_TRINH_DANG_DUNG')
            if self.chu_accept != 'core' or self._proc is not None or self._nghe is None:
                raise LoiTienTrinh('CORE_KHONG_CO_QUYEN_ACCEPT')
            self._nghe.settimeout(timeout)
            try:
                return self._nghe.accept()
            finally:
                self._nghe.settimeout(None)

    def dong(self):
        """Đóng handle Core sau thu hồi; không ngầm dừng con đang bận."""
        with self.khoa:
            if self._proc is not None:
                raise LoiTienTrinh('TIEN_TRINH_DANG_DUNG')
            if self._nghe is not None:
                self._nghe.close()
                self._nghe = None
            self._bo_chu()
