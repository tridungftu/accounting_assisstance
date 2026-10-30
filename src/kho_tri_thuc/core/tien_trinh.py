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
from ..nguon.trich6_host import Trich6Host, _JobWindows, _doc_dong, env_con
from ..sdk_core.bootstrap import (PROTOCOL, dinh_danh_lan_tao, doc_thong_diep,
                                  gui_thong_diep)
from ..sdk_core.ngu_canh import _xoa_loi


_KHOA = threading.Lock()
_CHU = {}


class LoiTienTrinh(RuntimeError):
    http_status = 503

    def __init__(self, ma):
        self.ma = ma
        super().__init__(ma)


def _job():
    if os.name != 'nt':
        raise LoiTienTrinh('CAN_WINDOWS')
    return _JobWindows()


class TienTrinhCore:
    """Mỗi dòng sổ cổng chỉ có một controller trong Core; khóa dùng cùng dispatch.

    Core giữ handle nhưng không accept khi con sở hữu. Không trả raw handle cho
    dispatch. thu_hoi không kill khi drain quá hạn; kiem_con thu hồi sau crash.
    """

    def __init__(self, *, so_cong_id, giao_dich, lenh, phien_ban, issuer, contracts,
                 tham_so=None, ma_chu=None, cho_khoi_dong=120, cho_dung=30, popen=subprocess.Popen,
                 job_factory=_job, doc_dong=_doc_dong, socket_factory=socket.socket,
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
        Trich6Host._don(don, self._proc, self._job)
        self._proc = self._job = None

    def khoi_dong(self):
        with self.khoa:
            if self.trang_thai == 'ready' and self._proc.poll() is None:
                return self.instance_id
            if self._proc is not None or self.trang_thai == 'dang_dung':
                raise LoiTienTrinh('TIEN_TRINH_DANG_DUNG')
            dong = self._so(so_cong.doc)
            if dong['trang_thai'] == 'LOI':
                raise LoiTienTrinh('KHOI_DONG_BI_KHOA')
            # Không suy diễn lease hết thành bằng chứng tiến trình cũ đã chết.
            if dong['giu_boi'] is not None:
                raise LoiTienTrinh('CONG_CAN_DOI_CHIEU')
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
                self._job = self._job_factory()
                self._proc = self._popen(self._lenh, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, env=env_con(), shell=False, close_fds=True,
                    creationflags=0x08000000 if os.name == 'nt' else 0)
                self._job.gan(self._proc)  # trước bất kỳ cấu hình/capability nào
                self._lan_tao = self._doc_lan_tao(self._proc)
                dong = self._so(so_cong.nhan, self.instance_id, dong['the_he'],
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
                self.trang_thai = 'ready'
                return self.instance_id
            except Exception as exc:
                if isinstance(exc, LoiTienTrinh):
                    ma = exc.ma
                _xoa_loi(exc)
            finally:
                cfg = dong_ready = None
            self.trang_thai = 'failed'
            # Ghi khóa lỗi ở transaction riêng, không rollback cùng lỗi bind/readiness.
            try:
                if self._da_nhan:
                    self._so(so_cong.loi_khoi_dong, self.instance_id, self.the_he, ma_loi=ma)
                    self._khoa_loi = True
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

    def _thu_sau_khi_chet(self):
        if (self._proc.poll() is None
                or not Trich6Host._cho_job_rong(self, self._job, min(self.cho_dung, 10))):
            raise LoiTienTrinh('DUNG_CHUA_XAC_NHAN')
        # Chỉ trả thế hệ sau khi con và toàn bộ Job hết quyền accept.
        if not self._khoa_loi:
            self._so(so_cong.tra, self.instance_id, self.the_he)
        self._job.dong()
        self._proc.stdin.close()
        self._proc.stdout.close()
        self._proc = self._job = self._nonce = None
        self._da_nhan = False
        self.trang_thai, self.chu_accept = 'stopped', 'core'
        # Vẫn giữ listener: lần sau dùng đúng socket/cổng, không có khoảng hở bind.
        return True

    def kiem_con(self):
        with self.khoa:
            if self._proc is None or self._proc.poll() is None:
                return False
            return self._thu_sau_khi_chet()

    def thu_hoi(self, *, timeout=300):
        if not 0 < timeout <= 300:
            raise ValueError('Hạn drain không hợp lệ')
        with self.khoa:
            if self._proc is None:
                return True
            if self._proc.poll() is not None:
                return self._thu_sau_khi_chet()
            if self.trang_thai == 'dang_dung':
                raise LoiTienTrinh('TIEN_TRINH_DANG_DUNG')
            # Khóa dispatch giữ suốt drain; gia hạn trước để không hết lease giữa
            # lúc chờ (gia_han không hồi sinh một lease vốn đã hết).
            self._so(so_cong.gia_han, self.instance_id, self.the_he,
                     lease_giay=max(120, math.ceil(timeout) + 30))
            self.trang_thai = 'dang_dung'
            try:
                self._gui('thu_hoi')
                # Đợi terminal (không chỉ ACK) và Job rỗng; không cưỡng bức drain.
                self._proc.wait(timeout)
            except (subprocess.TimeoutExpired, OSError):
                raise LoiTienTrinh('DUNG_CHUA_XAC_NHAN') from None
            return self._thu_sau_khi_chet()

    def accept(self, *, timeout=0):
        with self.khoa:
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
