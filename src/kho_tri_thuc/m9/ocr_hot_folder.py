"""Bộ nối ABBYY Hot Folder riêng cho M9, chép và chỉnh từ Review CD-015 §6.

Không import bản gốc m4/review_goc/trich_xuat/ocr_abbyy.py hay cấu hình Review.
Giấy phép ABBYY có hạn mức dùng chung 5.000 trang / 30 ngày với phần mềm
Review, nhưng hai sổ đếm đang tách nhau. Cần Anh: có gộp sổ đếm không.
Sổ M9 giữ chỗ trước khi đưa file vào; chỉ hoàn trang khi chưa đưa vào hoặc
rút được file chưa nhận. PDF đếm /Type /Page đơn giản, ảnh tính một trang.
Khóa bảo vệ các instance trong cùng tiến trình; bên gọi cần dùng một tiến
trình điều phối cho mỗi Hot Folder. Không gọi ABBYY, AI hay dịch vụ mạng.
"""

from __future__ import annotations

import hashlib
import io
import json
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


def _khoa_cho(loai: str, thu_muc: Path) -> threading.Lock:
    key = loai, os.path.normcase(str(thu_muc.resolve()))
    with _KHOA_DANH_SACH:
        return _KHOA.setdefault(key, threading.Lock())


def _docx_hop_le(raw: bytes) -> bool:
    """Như bản gốc: phải có word/document.xml và mọi mục ZIP đúng CRC."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as tep:
            return "word/document.xml" in tep.namelist() and tep.testzip() is None
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError,
            NotImplementedError, EOFError, zlib.error):
        return False


def _xoa(tep: Path) -> None:
    try:
        tep.unlink()
    except OSError:
        pass


def _kiem_huy(huy: threading.Event | None) -> None:
    if huy is not None and huy.is_set():
        raise DataError("M9_OCR_HUY", "Đã hủy nhận dạng tài liệu.")


class HotFolderM9:
    def __init__(self, thu_muc_goc: Path, *, thu_muc_du_lieu: Path,
                 cho_nhan=300, cho_toi_da=1800, nghi=1.0, on_dinh=2.0):
        try:
            self.cho_nhan, self.cho_toi_da, self.nghi, self.on_dinh = (
                float(x) for x in (cho_nhan, cho_toi_da, nghi, on_dinh)
            )
            if not all(math.isfinite(x) and x > 0 for x in (
                    self.cho_nhan, self.cho_toi_da, self.nghi, self.on_dinh)):
                raise ValueError
            self.thu_muc_goc = Path(thu_muc_goc).resolve()
            self.thu_muc_du_lieu = Path(thu_muc_du_lieu).resolve() / "ocr_hot_folder_m9"
            self._khoa = _khoa_cho("hot_folder", self.thu_muc_goc)
            self._khoa_so = _khoa_cho("so_trang", self.thu_muc_du_lieu)
        except (OSError, ValueError, TypeError):
            raise DataError("M9_OCR_LOI_ABBYY", "Cấu hình nhận dạng chưa hợp lệ.") from None

    def thu_muc(self) -> dict[str, Path]:
        d = {k: self.thu_muc_goc / k for k in ("in", "out", "tam", "nhan")}
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    def _doc_so(self) -> list:
        try:
            ds = json.loads((self.thu_muc_du_lieu / "so_trang.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        # Không đặt lại sổ hỏng về 0 vì có thể bỏ qua hạn mức giấy phép.
        if not isinstance(ds, list) or any(
            not isinstance(x, list) or len(x) != 3
            or not isinstance(x[0], (int, float)) or not math.isfinite(x[0])
            or type(x[1]) is not int or x[1] < 0 or not isinstance(x[2], str)
            for x in ds
        ):
            raise ValueError
        moc = time.time() - CUA_SO_NGAY * 86400
        return [x for x in ds if x[0] >= moc]

    def _ghi_so(self, ds: list) -> None:
        tep = self.thu_muc_du_lieu / "so_trang.json"
        tam = tep.with_suffix(".tmp")
        try:
            tam.write_text(json.dumps(ds, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            os.replace(tam, tep)
        finally:
            _xoa(tam)

    def _giu_trang(self, trang: int, ma: str) -> None:
        with self._khoa_so:
            ds = self._doc_so()
            if sum(x[1] for x in ds) + trang > HAN_MUC:
                raise DataError("M9_OCR_HET_HAN_MUC", "Đã hết hạn mức trang nhận dạng trong 30 ngày.")
            ds.append([time.time(), trang, ma])
            self._ghi_so(ds)

    def _hoan_trang(self, ma: str) -> None:
        with self._khoa_so:
            self._ghi_so([x for x in self._doc_so() if x[2] != ma])

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
        hen = threading.Timer(120, HotFolderM9._don, args=({"out": thu_muc}, ma))
        hen.daemon = True
        hen.start()

    @staticmethod
    def _loi_abbyy(thu_muc: Path, ma: str) -> bool:
        for tep in thu_muc.iterdir():
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
                    raise DataError("M9_OCR_QUA_GIO", "Đã quá thời gian chờ kết quả nhận dạng.")
                if not vao.exists():
                    da_nhan = True
                if not da_nhan and now - t0 >= self.cho_nhan:
                    if self._rut(d, ma, duoi):
                        da_dua = False
                        raise DataError("M9_OCR_KHONG_NHAN", "ABBYY chưa nhận tài liệu trong thời gian chờ.")
                    da_nhan = True  # ABBYY có thể đang giữ file trên Windows.
                if self._loi_abbyy(d["out"], ma):
                    raise DataError("M9_OCR_LOI_ABBYY", "ABBYY không hoàn tất nhận dạng tài liệu.")
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
            raise DataError("M9_OCR_DINH_DANG", "Chỉ nhận tài liệu PDF hoặc ảnh scan được hỗ trợ.")
        duoi = duoi.lower().lstrip(".")
        _kiem_huy(huy)
        while not self._khoa.acquire(timeout=self.nghi):
            _kiem_huy(huy)
        try:
            _kiem_huy(huy)
            self.thu_muc_du_lieu.mkdir(parents=True, exist_ok=True)
            dem = self.thu_muc_du_lieu / (hashlib.sha256(raw).hexdigest() + ".docx")
            try:
                docx = dem.read_bytes()
            except FileNotFoundError:
                pass
            else:
                if _docx_hop_le(docx):
                    return docx
            d = self.thu_muc()
            trang = max(1, len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", raw))) if duoi == "pdf" else 1
            ma = "m9_" + secrets.token_hex(16)
            self._giu_trang(trang, ma)
            docx = self._chay_hot_folder(raw, duoi, d, ma, huy)
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
            raise DataError("M9_OCR_LOI_ABBYY", "Không hoàn tất xử lý nhận dạng tài liệu.") from None
        finally:
            self._khoa.release()
