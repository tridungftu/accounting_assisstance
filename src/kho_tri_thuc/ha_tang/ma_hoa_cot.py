"""MH-1: khóa DPAPI CurrentUser và HMAC; chưa nối caller/CSDL.

Import/khởi tạo NguonKhoa không đọc đĩa. Lead truyền thư mục và phiên bản
tường minh khi tạo khóa; module không tự tạo khóa hay chọn phiên bản mới nhất.
Giữ một NguonKhoa suốt vòng đời worker để dùng lại khóa trong RAM.
Không log kết quả tham_so_* (có passphrase), tham số SQL hay exception của driver.
Chỉ dùng psycopg server-side binding; ACL, GUC/log và quyền đọc do lead cấu hình.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import hmac
import secrets
from pathlib import Path

from ..giao_dien.v9b import bank_account


THU_MUC_KHOA_COT = r"D:\DU-LIEU-KE-TOAN\bi-mat\cot"
THU_MUC_KHOA_TRA_CUU = r"D:\DU-LIEU-KE-TOAN\bi-mat\tra-cuu"
SQL_MA_HOA = "SELECT pgp_sym_encrypt(%s, %s, 'cipher-algo=aes256,compress-algo=0')"
SQL_GIAI_MA = "SELECT pgp_sym_decrypt(%s, %s)"

_MA_LOI = frozenset({
    "MH_THIEU_KHOA", "MH_PHIEN_BAN", "MH_LOAI_KHOA", "MH_KHOA_DA_TON_TAI",
    "MH_DOC_KHOA", "MH_GHI_KHOA", "MH_KHOA_KHONG_HOP_LE", "MH_KHONG_CO_DPAPI",
    "MH_BOC_DPAPI", "MH_GIAI_DPAPI", "MH_LOAI_DU_LIEU", "MH_GIA_TRI",
    "MH_LOI_NOI_BO",
})


class LoiMaHoaCot(Exception):
    """Chỉ mang mã cố định, không mang giá trị, đường dẫn hoặc lỗi Win32."""

    def __init__(self, code: str):
        self.code = code if code in _MA_LOI else "MH_LOI_NOI_BO"
        super().__init__(self.code)


def _kiem_phien_ban(phien_ban: int) -> int:
    if type(phien_ban) is not int or not 1 <= phien_ban <= 32767:
        raise LoiMaHoaCot("MH_PHIEN_BAN")
    return phien_ban


def _kiem_loai_khoa(loai: str) -> str:
    if loai not in ("cot", "tra-cuu"):
        raise LoiMaHoaCot("MH_LOAI_KHOA")
    return loai


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(du_lieu: bytes, *, boc: bool) -> bytes:
    """CRYPTPROTECT_UI_FORBIDDEN=1; không có cờ LOCAL_MACHINE (=4).

    Chỉ nạp Windows DLL lúc được gọi. LocalFree giải phóng output cả khi lỗi;
    xóa buffer ctypes sau dùng, không hứa xóa mọi bản sao bytes khỏi Python RAM.
    """
    if not hasattr(ctypes, "WinDLL"):
        raise LoiMaHoaCot("MH_KHONG_CO_DPAPI")
    try:
        crypt = ctypes.WinDLL("crypt32.dll", use_last_error=True, winmode=0x800)
        kernel = ctypes.WinDLL("kernel32.dll", use_last_error=True, winmode=0x800)
        protect = crypt.CryptProtectData
        protect.argtypes = [ctypes.POINTER(_Blob), ctypes.c_wchar_p,
                            ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                            ctypes.c_uint32, ctypes.POINTER(_Blob)]
        protect.restype = ctypes.c_int
        unprotect = crypt.CryptUnprotectData
        unprotect.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p,
                              ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                              ctypes.c_uint32, ctypes.POINTER(_Blob)]
        unprotect.restype = ctypes.c_int
        free = kernel.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        buffer = (ctypes.c_ubyte * len(du_lieu)).from_buffer_copy(du_lieu)
        source = _Blob(len(du_lieu), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
        target = _Blob()
        try:
            # Cùng chữ ký khi description và optional entropy đều NULL.
            operation = protect if boc else unprotect
            if not operation(ctypes.byref(source), None, None, None, None, 1,
                             ctypes.byref(target)):
                raise LoiMaHoaCot("MH_BOC_DPAPI" if boc else "MH_GIAI_DPAPI")
            return ctypes.string_at(target.pbData, target.cbData)
        finally:
            ctypes.memset(buffer, 0, len(du_lieu))
            if target.pbData:
                ctypes.memset(target.pbData, 0, target.cbData)
                free(ctypes.cast(target.pbData, ctypes.c_void_p))
    except LoiMaHoaCot:
        raise
    except Exception:
        raise LoiMaHoaCot("MH_BOC_DPAPI" if boc else "MH_GIAI_DPAPI") from None


def _dau_khoa(loai: str, phien_ban: int) -> bytes:
    # Metadata cũng nằm trong khối được DPAPI xác thực: đổi tên/copy sai loại bị chặn.
    return b"MH1\x00" + loai.encode("ascii") + b"\x00" + phien_ban.to_bytes(2, "big")


def tao_khoa_moi(thu_muc: str | Path, phien_ban: int, *, loai: str) -> int:
    """Sinh riêng 32 byte mỗi lần; v01.dpapi, v02.dpapi…; không ghi đè.

    Thư mục phải được lead tạo/cấp ACL trước. Lỗi ghi giữ nguyên tệp dở để
    lead kiểm tra, không xóa hay tự thử ghi đè. Không dùng thư mục mặc định.
    """
    _kiem_phien_ban(phien_ban)
    _kiem_loai_khoa(loai)
    wrapped = _dpapi(_dau_khoa(loai, phien_ban) + secrets.token_bytes(32), boc=True)
    try:
        path = Path(thu_muc) / f"v{phien_ban:02d}.dpapi"
        with path.open("xb") as handle:
            if handle.write(wrapped) != len(wrapped):
                raise LoiMaHoaCot("MH_GHI_KHOA")
    except FileExistsError:
        raise LoiMaHoaCot("MH_KHOA_DA_TON_TAI") from None
    except (OSError, TypeError, ValueError):
        raise LoiMaHoaCot("MH_GHI_KHOA") from None
    return phien_ban


class _Khoa:
    __slots__ = ("_bytes",)

    def __init__(self, gia_tri: bytes):
        self._bytes = gia_tri

    def __repr__(self) -> str:
        return "<Khoa: da che>"

    __str__ = __repr__


class NguonKhoa:
    """Cache theo (loại khóa, phiên bản); xoay cột và tra cứu độc lập.

    Không đọc tệp khi import/khởi tạo. Tệp đã cache không được đọc lại; khởi
    động worker mới khi thay tài khoản hoặc cần làm mới nguồn khóa.
    """

    __slots__ = ("_thu_muc", "_cache")

    def __init__(self, thu_muc_cot: str | Path = THU_MUC_KHOA_COT,
                 thu_muc_tra_cuu: str | Path = THU_MUC_KHOA_TRA_CUU):
        try:
            self._thu_muc = {"cot": Path(thu_muc_cot), "tra-cuu": Path(thu_muc_tra_cuu)}
        except (TypeError, ValueError):
            raise LoiMaHoaCot("MH_DOC_KHOA") from None
        self._cache: dict[tuple[str, int], _Khoa] = {}

    def __repr__(self) -> str:
        return "<NguonKhoa: da che>"

    __str__ = __repr__

    def _doc(self, loai: str, phien_ban: int) -> _Khoa:
        _kiem_phien_ban(phien_ban)
        cache_key = (loai, phien_ban)
        if cache_key not in self._cache:
            try:
                path = self._thu_muc[loai] / f"v{phien_ban:02d}.dpapi"
                with path.open("rb") as handle:
                    wrapped = handle.read(65537)
            except FileNotFoundError:
                raise LoiMaHoaCot("MH_THIEU_KHOA") from None
            except OSError:
                raise LoiMaHoaCot("MH_DOC_KHOA") from None
            if not wrapped or len(wrapped) > 65536:
                raise LoiMaHoaCot("MH_KHOA_KHONG_HOP_LE")
            clear = _dpapi(wrapped, boc=False)
            prefix = _dau_khoa(loai, phien_ban)
            if not clear.startswith(prefix) or len(clear) != len(prefix) + 32:
                raise LoiMaHoaCot("MH_KHOA_KHONG_HOP_LE")
            self._cache[cache_key] = _Khoa(clear[len(prefix):])
        return self._cache[cache_key]

    def tham_so_ma_hoa(self, key_ver: int) -> tuple[str, int]:
        """Trả (passphrase base64url, key_ver) để caller bind riêng, cấm log.

        SQL_MA_HOA nhận (plaintext, passphrase); key_ver lưu vào cột metadata.
        Không dùng ClientCursor/mogrify/nội suy SQL ở caller MH-3.
        """
        key = self._doc("cot", key_ver)
        return base64.urlsafe_b64encode(key._bytes).decode("ascii"), key_ver

    def tham_so_giai_ma(self, key_ver: int) -> tuple[str, int]:
        """SQL_GIAI_MA nhận (ciphertext, passphrase); chọn đúng version của dòng."""
        return self.tham_so_ma_hoa(key_ver)

    def tra_cuu(self, loai: str, gia_tri: str, lookup_ver: int) -> tuple[str, int]:
        kind = _loai_du_lieu(loai)
        normalized = chuan_hoa(kind, gia_tri)
        key = self._doc("tra-cuu", lookup_ver)
        # Miền theo loại, không tự thêm ngân hàng/pháp nhân làm đổi UNIQUE.
        message = kind.encode("utf-8") + b"\x00" + normalized.encode("utf-8")
        return hmac.new(key._bytes, message, hashlib.sha256).hexdigest(), lookup_ver


def _loai_du_lieu(loai: str) -> str:
    if not isinstance(loai, str):
        raise LoiMaHoaCot("MH_LOAI_DU_LIEU")
    kind = loai.strip().upper()
    aliases = {"BANK_ACCOUNT": "STK", "PHONE": "SDT", "SĐT": "SDT"}
    kind = aliases.get(kind, kind)
    if kind not in ("STK", "CCCD", "MST", "SDT", "EMAIL"):
        raise LoiMaHoaCot("MH_LOAI_DU_LIEU")
    return kind


def chuan_hoa(loai: str, gia_tri: str) -> str:
    """Chỉ nhận chuỗi để không mất số 0 trước khi chuẩn hóa.

    CCCD/MST bỏ khoảng trắng, dấu chấm/gạch; SĐT bỏ thêm ngoặc, giữ '+' đầu
    và mọi số 0 (không quy đổi +84/0). Email bỏ trắng hai đầu, casefold toàn
    địa chỉ; không gộp dấu chấm/plus alias. STK giữ đúng hợp đồng bank_account.
    """
    kind = _loai_du_lieu(loai)
    if not isinstance(gia_tri, str):
        raise LoiMaHoaCot("MH_GIA_TRI")
    raw = gia_tri.strip()
    if kind == "STK":
        result = bank_account(raw)
    elif kind == "EMAIL":
        result = raw.casefold()
        parts = result.split("@")
        if (len(parts) != 2 or not all(parts)
                or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in result)):
            raise LoiMaHoaCot("MH_GIA_TRI")
    else:
        separators = ".-()" if kind == "SDT" else ".-"
        result = "".join(ch for ch in raw if not ch.isspace() and ch not in separators)
        digits = result[1:] if kind == "SDT" and result.startswith("+") else result
        if not digits or any(ch not in "0123456789" for ch in digits):
            raise LoiMaHoaCot("MH_GIA_TRI")
    if not result:
        raise LoiMaHoaCot("MH_GIA_TRI")
    return result


def che_hien_thi(loai: str, gia_tri: str) -> str:
    """Chỉ che UI; không thay cổng Mask AI và không phải căn cứ cấp quyền."""
    kind = _loai_du_lieu(loai)
    value = chuan_hoa(kind, gia_tri)
    if kind == "EMAIL":
        local, domain = value.split("@")
        masked = local[0] + "***" + local[-1] if len(local) > 2 else "***"
        return masked + "@" + domain
    if kind == "SDT":
        return value[:3] + "***" + value[-3:] if len(value) > 6 else "***"
    return "*" * (len(value) - 4) + value[-4:] if len(value) > 4 else "*" * len(value)
