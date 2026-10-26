"""Cổng ABBYY dùng chung cho mọi module, một engine và sổ Review 5.000 trang/30 ngày.

Bên gọi truyền Hot Folder của Review, đường dẫn ocr_abbyy/so_trang.json trong
dữ liệu Review và thư mục đệm riêng; không import bản Review đóng băng.
Sổ chỉ gồm các cặp [epoch, số trang]. Giữ chỗ trước khi gửi, chỉ hoàn khi
chưa gửi hoặc rút được đầu vào. Khóa .lock bảo vệ các tiến trình dùng cổng.

QD-20261026-06 chấp nhận Review cũ không tham gia khóa sổ/khóa in: có thể
chen hàng, vượt hạn mức giữa hai lần kiểm và ghi đè trong khe đua còn lại.
Cổng đọc lại/gộp ngay trước replace, kiểm sau ghi và thử khôi phục một lần;
không thể bảo đảm giao dịch tuyệt đối với Review không khóa. Rủi ro này hết
khi chuyển hẳn sang M4 ở cổng B. Mỗi bên chỉ nhận/dọn đúng mã việc của mình.
Không gọi ABBYY, AI hay dịch vụ mạng; không log tài liệu hoặc đường dẫn.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import errno
import hashlib
import io
import json
import logging
import math
import os
from pathlib import Path
import re
import secrets
import threading
import time
import zipfile
import zlib

from kho_tri_thuc.ha_tang.primitives import DataError


HAN_MUC, CUA_SO_NGAY = 5000, 30
_DUOI = frozenset(("pdf", "jpg", "jpeg", "png", "tif", "tiff"))
_TU_LOI = ("error", "failed", "cannot", "unable", "lỗi", "không thể")
_KHOA: dict[tuple[str, str], threading.Lock] = {}
_KHOA_DANH_SACH = threading.Lock()
_LOG = logging.getLogger(__name__)
_MA_RE = re.compile(r"^(hd\d{14}_[0-9a-f]{6})(?:\.|$)")


def _khoa_cho(loai: str, thu_muc: Path) -> threading.Lock:
    key = loai, os.path.normcase(str(thu_muc.resolve()))
    with _KHOA_DANH_SACH:
        return _KHOA.setdefault(key, threading.Lock())


@contextmanager
def _khoa_tep(tep: Path, nghi: float, huy: threading.Event | None = None):
    """Giữ khóa byte đầu; giữ lock file để tránh khóa hai inode khác nhau."""
    khoa = _khoa_cho("tep", tep)
    while not khoa.acquire(timeout=nghi):
        _kiem_huy(huy)
    try:
        _kiem_huy(huy)
        tep.parent.mkdir(parents=True, exist_ok=True)
        with tep.open("a+b") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() == 0:
                f.write(b"\0")
                f.flush()
            if os.name == "nt":
                import msvcrt

                def khoa_os(mo=False):
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK if mo else msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                def khoa_os(mo=False):
                    f.seek(0)
                    fcntl.lockf(f.fileno(), fcntl.LOCK_UN if mo else fcntl.LOCK_EX | fcntl.LOCK_NB, 1)
            while True:
                _kiem_huy(huy)
                try:
                    khoa_os()
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    if huy is None:
                        time.sleep(nghi)
                    else:
                        huy.wait(nghi)
            try:
                _kiem_huy(huy)
                yield
            finally:
                khoa_os(mo=True)
    finally:
        khoa.release()


def _ma_moi() -> str:
    return "hd" + time.strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(3)


def _docx_hop_le(raw: bytes) -> bool:
    """Như bản gốc: phải có word/document.xml và mọi mục ZIP đúng CRC."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as tep:
            return "word/document.xml" in tep.namelist() and tep.testzip() is None
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError,
            NotImplementedError, EOFError, zlib.error):
        return False


def _xoa(tep: Path) -> None:
    if os.environ.get("CODEX_NO_DELETE_FILES", "").strip().lower() in ("1", "true", "yes", "on"):
        return
    try:
        tep.unlink()
    except OSError:
        pass


def _kiem_huy(huy: threading.Event | None) -> None:
    if huy is not None and huy.is_set():
        raise DataError("OCR_HUY", "Đã hủy nhận dạng tài liệu.")


class CongOCR:
    def __init__(self, thu_muc_goc: Path, *, tep_so_trang: Path, thu_muc_dem: Path,
                 cho_nhan=300, cho_toi_da=1800, nghi=1.0, on_dinh=2.0):
        try:
            self.cho_nhan, self.cho_toi_da, self.nghi, self.on_dinh = (
                float(x) for x in (cho_nhan, cho_toi_da, nghi, on_dinh)
            )
            if not all(math.isfinite(x) and x > 0 for x in (
                    self.cho_nhan, self.cho_toi_da, self.nghi, self.on_dinh)):
                raise ValueError
            self.thu_muc_goc = Path(thu_muc_goc).resolve()
            self.tep_so_trang = Path(tep_so_trang).resolve()
            self.thu_muc_dem = Path(thu_muc_dem).resolve()
            self._khoa = _khoa_cho("hot_folder", self.thu_muc_goc)
            self._giu_cho: dict[str, list] = {}
        except (OSError, ValueError, TypeError):
            raise DataError("OCR_LOI_ABBYY", "Cấu hình nhận dạng chưa hợp lệ.") from None

    def thu_muc(self) -> dict[str, Path]:
        d = {k: self.thu_muc_goc / k for k in ("in", "out", "tam", "nhan")}
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    def _doc_so(self) -> list:
        try:
            ds = json.loads(self.tep_so_trang.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        # Không đặt sổ hỏng về 0, không sửa định dạng hai cột của Review.
        if not isinstance(ds, list) or any(
            not isinstance(x, list) or len(x) != 2
            or type(x[0]) not in (int, float) or not math.isfinite(x[0])
            or type(x[1]) is not int or x[1] < 0
            for x in ds
        ):
            raise ValueError
        moc = time.time() - CUA_SO_NGAY * 86400
        return [x for x in ds if x[0] >= moc]

    def _ghi_so(self, ds: list, *, them: list | None = None,
                bot: list | None = None) -> None:
        """Gọi trong khóa sổ; gộp theo số lần xuất hiện để giữ cả cặp trùng."""
        tep = self.tep_so_trang
        tam = tep.with_name("." + tep.name + "." + secrets.token_hex(16) + ".tmp")
        try:
            for lan in range(2):
                with tam.open("w", encoding="utf-8") as f:
                    json.dump(ds, f, ensure_ascii=False, allow_nan=False)
                    f.flush()
                    os.fsync(f.fileno())
                # Review có thể vừa ghi sau lần đọc đầu, ngay cả khi ta giữ khóa.
                moi = self._doc_so()
                if bot is not None and bot in moi:
                    moi.remove(bot)  # Chỉ đúng cặp đã giữ chỗ của công việc này.
                dem = Counter(tuple(x) for x in ds) | Counter(tuple(x) for x in moi)
                gop = [list(x) for x, so in dem.items() for _ in range(so)]
                if them is not None and sum(x[1] for x in gop) > HAN_MUC:
                    raise DataError("OCR_HET_HAN_MUC", "Đã hết hạn mức trang nhận dạng trong 30 ngày.")
                if gop != ds:
                    with tam.open("w", encoding="utf-8") as f:
                        json.dump(gop, f, ensure_ascii=False, allow_nan=False)
                        f.flush()
                        os.fsync(f.fileno())
                os.replace(tam, tep)
                sau = self._doc_so()
                if (them is None or them in sau) and (bot is None or bot not in sau):
                    return
                _LOG.warning("Sổ trang OCR bị ghi đồng thời; kiểm tra và khôi phục có giới hạn.")
                # Một lần thử lại, vẫn gộp bản ghi Review mới ở lần đọc kế tiếp.
                ds = gop
            raise DataError("OCR_LOI_ABBYY", "Không xác nhận được cập nhật sổ trang nhận dạng.")
        finally:
            _xoa(tam)

    def _giu_trang(self, trang: int, ma: str, *, huy: threading.Event | None = None) -> None:
        with _khoa_tep(self.tep_so_trang.with_suffix(".lock"), self.nghi, huy):
            ds = self._doc_so()
            if sum(x[1] for x in ds) + trang > HAN_MUC:
                raise DataError("OCR_HET_HAN_MUC", "Đã hết hạn mức trang nhận dạng trong 30 ngày.")
            ban_ghi = [time.time(), trang]
            # Sổ không có mã việc: chọn cặp riêng để hoàn đúng một bản ghi.
            while ban_ghi in ds:
                ban_ghi[0] = math.nextafter(ban_ghi[0], math.inf)
            self._ghi_so(ds + [ban_ghi], them=ban_ghi)
            self._giu_cho[ma] = ban_ghi

    def _hoan_trang(self, ma: str) -> None:
        ban_ghi = self._giu_cho.get(ma)
        if ban_ghi is None:
            return
        with _khoa_tep(self.tep_so_trang.with_suffix(".lock"), self.nghi):
            ds = self._doc_so()
            if ban_ghi in ds:
                ds.remove(ban_ghi)
            self._ghi_so(ds, bot=ban_ghi)
            self._giu_cho.pop(ma, None)

    @staticmethod
    def _rut(d: dict[str, Path], ma: str, duoi: str) -> bool:
        dich = d["tam"] / f"{ma}.rut"
        try:
            os.replace(d["in"] / f"{ma}.{duoi}", dich)
        except OSError:
            return False
        _xoa(dich)
        return True

    @staticmethod
    def _don(d: dict[str, Path], ma: str) -> None:
        # Chỉ xóa file của chính mã ngẫu nhiên này, không xóa file người dùng.
        for thu_muc in d.values():
            try:
                for tep in thu_muc.iterdir():
                    if tep.name.startswith(ma + ".") and tep.is_file():
                        _xoa(tep)
            except OSError:
                pass

    @staticmethod
    def _don_sau(thu_muc: Path, ma: str) -> None:
        # Như bản gốc: dọn một lần kết quả đến muộn, chỉ đúng mã này.
        hen = threading.Timer(120, CongOCR._don, args=({"out": thu_muc}, ma))
        hen.daemon = True
        hen.start()

    @staticmethod
    def _loi_abbyy(thu_muc: Path, ma: str) -> bool:
        for tep in thu_muc.iterdir():
            ma_tep = _MA_RE.match(tep.name)
            if ma_tep is not None and ma_tep.group(1) != ma:
                continue
            if tep.suffix.lower() not in (".txt", ".log") or not tep.is_file():
                continue
            try:
                with tep.open("rb") as f:
                    f.seek(max(0, tep.stat().st_size - 200_000))
                    raw = f.read()
                enc = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else (
                    "utf-16-le" if raw.count(b"\0") > len(raw) // 4 else "utf-8-sig")
                chu = raw.decode(enc, errors="replace").lower()
            except OSError:
                continue
            if any(ma in dong and any(tu in dong for tu in _TU_LOI) for dong in chu.splitlines()):
                return True
        return False

    def _chay_hot_folder(self, raw: bytes, duoi: str, d: dict[str, Path],
                        ma: str, huy: threading.Event | None) -> bytes:
        vao, ra = d["in"] / f"{ma}.{duoi}", d["out"] / f"{ma}.docx"
        part, nhan = d["tam"] / f"{ma}.part", d["nhan"] / f"{ma}.docx"
        da_dua, da_nhan = False, False
        ky_cu, dung_tu = None, 0.0
        try:
            with part.open("wb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            _kiem_huy(huy)
            os.replace(part, vao)
            da_dua = True
            t0 = time.monotonic()
            while True:
                _kiem_huy(huy)
                now = time.monotonic()
                if now - t0 >= self.cho_toi_da:
                    raise DataError("OCR_QUA_GIO", "Đã quá thời gian chờ kết quả nhận dạng.")
                if not vao.exists():
                    da_nhan = True
                if not da_nhan and now - t0 >= self.cho_nhan:
                    if self._rut(d, ma, duoi):
                        da_dua = False
                        raise DataError("OCR_KHONG_NHAN", "ABBYY chưa nhận tài liệu trong thời gian chờ.")
                    da_nhan = True  # ABBYY có thể đang giữ file trên Windows.
                if self._loi_abbyy(d["out"], ma):
                    raise DataError("OCR_LOI_ABBYY", "ABBYY không hoàn tất nhận dạng tài liệu.")
                try:
                    st = ra.stat()
                except FileNotFoundError:
                    ky_cu = None
                else:
                    da_nhan = True
                    ky = st.st_size, st.st_mtime_ns
                    if ky != ky_cu:
                        ky_cu, dung_tu = ky, now
                    elif now - dung_tu >= self.on_dinh:
                        if _docx_hop_le(ra.read_bytes()):
                            try:
                                os.replace(ra, nhan)
                            except OSError:
                                pass  # ABBYY có thể vẫn giữ file.
                            else:
                                docx = nhan.read_bytes()
                                st_nhan = nhan.stat()
                                # Kiểm lại sau khi nhận để tránh đổi file giữa stat và rename.
                                if (st_nhan.st_size, st_nhan.st_mtime_ns) == ky and _docx_hop_le(docx):
                                    _kiem_huy(huy)
                                    return docx
                                os.replace(nhan, ra)
                                ky_cu = None
                if huy is None:
                    time.sleep(self.nghi)
                else:
                    huy.wait(self.nghi)
        finally:
            chua_nhan = not da_dua or self._rut(d, ma, duoi)
            self._don(d, ma)
            if da_dua:
                self._don_sau(d["out"], ma)
            if chua_nhan:
                self._hoan_trang(ma)

    def ocr(self, raw: bytes, duoi: str, *, huy: threading.Event | None = None) -> bytes:
        """PDF/ảnh → DOCX; đệm SHA256 bền vững, không ghi nội dung vào log.

        Lỗi và hủy sau khi ABBYY nhận vẫn tính trang. Kết quả đến muộn không
        được nhận; dọn thêm một lần sau 120 giây như bản gốc Review.
        """
        if not isinstance(duoi, str) or duoi.lower().lstrip(".") not in _DUOI or not isinstance(raw, bytes) or not raw:
            raise DataError("OCR_DINH_DANG", "Chỉ nhận tài liệu PDF hoặc ảnh scan được hỗ trợ.")
        duoi = duoi.lower().lstrip(".")
        _kiem_huy(huy)
        while not self._khoa.acquire(timeout=self.nghi):
            _kiem_huy(huy)
        try:
            _kiem_huy(huy)
            self.thu_muc_dem.mkdir(parents=True, exist_ok=True)
            dem = self.thu_muc_dem / (hashlib.sha256(raw).hexdigest() + ".docx")
            try:
                docx = dem.read_bytes()
            except FileNotFoundError:
                pass
            else:
                if _docx_hop_le(docx):
                    return docx
            with _khoa_tep(self.thu_muc_goc / "in.lock", self.nghi, huy):
                # Tiến trình khác có thể vừa ghi đệm trong lúc ta chờ khóa in.
                try:
                    docx = dem.read_bytes()
                except FileNotFoundError:
                    pass
                else:
                    if _docx_hop_le(docx):
                        return docx
                _kiem_huy(huy)
                d = self.thu_muc()
                trang = max(1, len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", raw))) if duoi == "pdf" else 1
                ma = _ma_moi()
                self._giu_trang(trang, ma, huy=huy)
                try:
                    docx = self._chay_hot_folder(raw, duoi, d, ma, huy)
                finally:
                    self._giu_cho.pop(ma, None)
                tam = dem.with_name(ma + ".tmp")
                try:
                    tam.write_bytes(docx)
                    os.replace(tam, dem)
                finally:
                    _xoa(tam)
                return docx
        except (OSError, ValueError, TypeError, OverflowError) as exc:
            if isinstance(exc, DataError):
                raise
            raise DataError("OCR_LOI_ABBYY", "Không hoàn tất xử lý nhận dạng tài liệu.") from None
        finally:
            self._khoa.release()
