"""Kênh bootstrap riêng: JSON một dòng trên stdin/stdout, không args/env/tệp.

Runtime gọi bao_san_sang sau preflight thật, rồi mới mở vòng accept. Khi
cho_thu_hoi nhận lệnh, runtime ngừng accept và drain trước khi đóng bản socket.
Khóa ký không đi qua đây; kiem_chu_ky là bộ kiểm khóa công khai của runtime.
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import socket
import sys

from .ngu_canh import NhanRequest as BoDocNguCanh, _json_cac_cap, _xoa_loi


PROTOCOL = 'ktt.bootstrap.v1'
TOI_DA = 65536


class LoiBootstrap(RuntimeError):
    def __init__(self, ma='BOOTSTRAP_SAI'):
        self.ma = ma
        super().__init__(ma)


def dinh_danh_lan_tao(proc=None):
    """FILETIME tạo tiến trình từ OS, dùng handle Popen sở hữu, không tin PID con báo."""
    if os.name != 'nt':
        raise LoiBootstrap('CAN_WINDOWS')
    from ctypes import wintypes
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k.GetProcessTimes.restype = wintypes.BOOL
    handle = k.GetCurrentProcess() if proc is None else wintypes.HANDLE(int(proc._handle))
    tao, thoat, nhan, nguoi = (wintypes.FILETIME() for _ in range(4))
    if not k.GetProcessTimes(handle, *map(ctypes.byref, (tao, thoat, nhan, nguoi))):
        raise LoiBootstrap('KHONG_DOC_DUOC_LAN_TAO')
    return str((tao.dwHighDateTime << 32) | tao.dwLowDateTime)


def doc_thong_diep(dong):
    if not isinstance(dong, bytes) or not dong.endswith(b'\n') or len(dong) >= TOI_DA:
        raise LoiBootstrap()
    return json.loads(dong, object_pairs_hook=_json_cac_cap)


def gui_thong_diep(kenh, du_lieu):
    dong = (json.dumps(du_lieu, ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    if len(dong) >= TOI_DA:
        raise LoiBootstrap()
    kenh.write(dong)
    kenh.flush()


class Bootstrap:
    """Socket riêng của con; không serialize/repr cấu hình hoặc nonce."""

    def __repr__(self):
        return 'Bootstrap(<an>)'

    def __reduce__(self):
        raise TypeError('Không serialize bootstrap')

    @classmethod
    def nhan(cls, *, kiem_chu_ky, stdin=None, stdout=None):
        vao = sys.stdin.buffer if stdin is None else stdin
        ra = stdout
        cfg = raw = None
        nghe = None
        try:
            if stdout is None:
                # Giữ fd pipe riêng cho protocol; cả print, sys.__stdout__ và
                # os.write lên fd stdout của runtime đều không làm đầy pipe.
                sys.stdout.flush()
                fd = sys.stdout.fileno()
                ra = os.fdopen(os.dup(fd), 'wb', buffering=0)
                with open(os.devnull, 'wb') as bo:
                    os.dup2(bo.fileno(), fd)
            cfg = doc_thong_diep(vao.readline(TOI_DA))
            if (not isinstance(cfg, dict) or cfg.get('protocol') != PROTOCOL
                    or cfg.get('kieu') != 'khoi_dong' or type(cfg.get('pid')) is not int
                    or cfg['pid'] != os.getpid()
                    or cfg.get('dinh_danh_lan_tao') != dinh_danh_lan_tao()
                    or type(cfg.get('cong')) is not int or not 1024 <= cfg['cong'] <= 65535
                    or cfg.get('dia_chi_nghe') not in ('127.0.0.1', '::1')
                    or not isinstance(cfg.get('phien_ban'), str) or not cfg['phien_ban']
                    or type(cfg.get('the_he')) is not int or cfg['the_he'] < 1
                    or not isinstance(cfg.get('tham_so'), dict)):
                raise LoiBootstrap()
            bo_doc = BoDocNguCanh(issuer=cfg['issuer'], module=cfg['module'],
                instance_id=cfg['instance_id'], nonce_khoi_dong=cfg['nonce_khoi_dong'],
                kiem_chu_ky=kiem_chu_ky)
            raw = base64.b64decode(cfg.pop('socket'), validate=True)
            nghe = socket.fromshare(raw)
            if nghe.getsockname()[:2] != (cfg['dia_chi_nghe'], cfg['cong']):
                raise LoiBootstrap()
            obj = cls()
            obj._vao, obj._ra, obj._cfg = vao, ra, cfg
            obj.socket, obj.bo_doc = nghe, bo_doc
            obj._duoc_accept = False
            return obj
        except Exception as exc:
            _xoa_loi(exc)
            if nghe is not None:
                nghe.close()
            if stdout is None and ra is not None:
                ra.close()
        finally:
            raw = cfg = None
        raise LoiBootstrap()

    @property
    def tham_so(self):
        return self._cfg['tham_so']

    def bao_san_sang(self, *, phien_ban, contracts, kiem_san_sang):
        """Phiên bản/contracts là thực tế của runtime, không chép từ cấu hình Core."""
        if self._duoc_accept:
            raise LoiBootstrap()
        if (not isinstance(contracts, list) or not all(isinstance(c, str) and c for c in contracts)
                or kiem_san_sang() is not True):
            raise LoiBootstrap('CHUA_SAN_SANG')
        cfg = self._cfg
        gui_thong_diep(self._ra, {**{k: cfg[k] for k in (
            'module', 'instance_id', 'pid', 'dinh_danh_lan_tao', 'nonce_khoi_dong',
            'cong', 'the_he')}, 'protocol': PROTOCOL, 'kieu': 'san_sang',
            'phien_ban': phien_ban, 'contracts': contracts, 'san_sang': True})
        lenh = doc_thong_diep(self._vao.readline(TOI_DA))
        if lenh != {'protocol': PROTOCOL, 'kieu': 'nhan_accept'}:
            raise LoiBootstrap()
        self._duoc_accept = True

    def accept(self):
        if not self._duoc_accept:
            raise LoiBootstrap('CHUA_CO_QUYEN_ACCEPT')
        return self.socket.accept()

    def cho_thu_hoi(self, *, ngung_accept, drain):
        """Hết hạn do Core quyết định; drain chưa xong thì giữ socket/instance."""
        lenh = doc_thong_diep(self._vao.readline(TOI_DA))
        if lenh != {'protocol': PROTOCOL, 'kieu': 'thu_hoi'}:
            raise LoiBootstrap()
        self._duoc_accept = False
        ngung_accept()
        if drain() is not True:
            raise LoiBootstrap('DRAIN_CHUA_XONG')
        self.socket.close()
        gui_thong_diep(self._ra, {'protocol': PROTOCOL, 'kieu': 'da_thu_hoi'})
