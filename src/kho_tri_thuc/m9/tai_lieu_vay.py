"""Đọc DOCX và cắt điều khoản thuần, không suy diễn dữ liệu tài chính."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
import zlib
from xml.etree import ElementTree as ET

from kho_tri_thuc.ha_tang.primitives import DataError


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_LOAI_TAI_LIEU = frozenset({
    "HD_TIN_DUNG", "KHE_UOC_NHAN_NO", "PHU_LUC", "HD_BAO_DAM",
    "THONG_BAO_LAI_SUAT",
})
_DUOI_TIEU_DE = r"(?:\s*[.:]\s*|(?=\s+(?P<chu_dau>[^\W\d_]))|$)"
_CHUONG = re.compile(r"^Chương\s+(?:\d+|[IVXLCDM]+)" + _DUOI_TIEU_DE, re.IGNORECASE)
_DIEU = re.compile(r"^Điều\s+(\d+)" + _DUOI_TIEU_DE, re.IGNORECASE)
_NHAN_DIEU_CHUONG = r"(?:Điều\s+\d+|Chương\s+(?:\d+|[IVXLCDM]+))"
_NHAN_DUNG_RIENG = re.compile(r"^" + _NHAN_DIEU_CHUONG + r"\s*[.:]?\s*$", re.IGNORECASE)
_NHAN_DAU_DOAN = re.compile(
    r"^(?:" + _NHAN_DIEU_CHUONG + r"|Khoản\s+\d+(?:\.\d+)*|Điểm\s+[a-zđ])(?=[).:\s]|$)",
    re.IGNORECASE,
)
_KHOAN_CHU = re.compile(r"^Khoản\s+(\d+(?:\.\d+)*)(?:[.:])?(?=\s|$)\s*", re.IGNORECASE)
# Các nhóm ba chữ số có thể là số tiền: không nhận là nhãn khoản.
_KHOAN_SO = re.compile(r"^(\d+(?:\.\d{1,2})+\.?|\d+\.)(?=\s|$)\s*")
_DIEM = re.compile(r"^([a-zđ])[).](?=\s|$)\s*", re.IGNORECASE)


def _khop_tieu_de(mau: re.Pattern, van_ban: str):
    khop = mau.match(van_ban)
    if khop and (khop.group("chu_dau") is None or khop.group("chu_dau").isupper()):
        return khop
    return None


def _la_tieu_de_tach(van_ban: str) -> bool:
    return bool(
        van_ban and len(van_ban) <= 120
        and van_ban[-1] not in ".,;:!?…"
        and not _NHAN_DAU_DOAN.match(van_ban)
        and not _KHOAN_SO.match(van_ban)
        and not _DIEM.match(van_ban)
    )


def _doc(raw: bytes) -> tuple[list[dict], int]:
    try:
        if not isinstance(raw, bytes):
            raise ValueError("bytes")
        with zipfile.ZipFile(io.BytesIO(raw)) as tep:
            goc = ET.fromstring(tep.read("word/document.xml"))
        than = goc.find(_W + "body")
        if goc.tag != _W + "document" or than is None:
            raise ValueError("document")
    except (zipfile.BadZipFile, KeyError, ET.ParseError, ValueError,
            RuntimeError, NotImplementedError, OSError, EOFError,
            LookupError, zlib.error):
        raise DataError(
            "M9_TAI_LIEU_KHONG_DOC_DUOC",
            "Không đọc được tài liệu. Hãy tải lên tệp Word (.docx) hợp lệ.",
        ) from None

    ket_qua = []
    trang = 1
    da_ngat_trang = False

    def doc_khoi(khoi, la_bang=False):
        nonlocal trang, da_ngat_trang
        if khoi.tag != _W + "p":
            for con in khoi:
                doc_khoi(con, la_bang or khoi.tag == _W + "tbl")
            return

        chu = []

        def ghi():
            van_ban = " ".join("".join(chu).split())
            if van_ban:
                doan = {"trang": trang, "thu_tu": len(ket_qua) + 1, "van_ban": van_ban}
                if la_bang:
                    doan["la_bang"] = True
                ket_qua.append(doan)
            chu.clear()

        for nut in khoi.iter():
            if nut.tag == _W + "t":
                chu.append(nut.text or "")
                if (nut.text or "").strip():
                    da_ngat_trang = False
            elif (nut.tag == _W + "lastRenderedPageBreak"
                  or (nut.tag == _W + "br" and nut.get(_W + "type") == "page")):
                ghi()
                # Word có thể ghi lại cùng ngắt trang ở run/đoạn kế tiếp.
                if nut.tag == _W + "br" or not da_ngat_trang:
                    trang += 1
                da_ngat_trang = True
            elif nut.tag in (_W + "tab", _W + "br", _W + "cr"):
                chu.append(" ")
        ghi()

    doc_khoi(than)
    return ket_qua, trang


def doc_docx(raw: bytes) -> list[dict]:
    """Đọc theo thứ tự XML, ô bảng theo hàng; thu_tu bắt đầu từ 1.

    Đoạn vượt ngắt trang tường minh được chia thành các phần theo trang.
    Chỉ đếm w:br loại page và w:lastRenderedPageBreak, không đoán bố cục.
    """
    return _doc(raw)[0]


def _tach_cau(van_ban: str, dau_noi_dung: int = 0) -> list[str]:
    """Giữ dấu câu và chữ gốc; bỏ qua dấu chấm bên trong số/ngày."""
    cau = []
    dau = 0
    for i in range(dau_noi_dung, len(van_ban)):
        ky_tu = van_ban[i]
        if ky_tu not in ".;":
            continue
        if ky_tu == "." and 0 < i < len(van_ban) - 1:
            if van_ban[i - 1].isdigit() and van_ban[i + 1].isdigit():
                continue
        if i + 1 < len(van_ban) and not van_ban[i + 1].isspace():
            continue
        phan = van_ban[dau:i + 1].strip()
        if phan:
            cau.append(phan)
        dau = i + 1
    phan = van_ban[dau:].strip()
    if phan:
        cau.append(phan)
    return cau


def cat_doan(doan: list[dict]) -> list[dict]:
    """Gom văn bản liên tiếp cùng cấp; nhãn số ở đầu dòng mới là cấu trúc.

    dieu giữ số và tiêu đề sau chữ Điều; khoan/diem chỉ giữ nhãn số/chữ.
    chuong giữ số và tiêu đề sau chữ Chương. Ô bảng kế thừa cấp hiện tại.
    Nhãn đứng riêng lấy tiêu đề ngắn ở đoạn ngoài bảng kế tiếp nếu hợp lệ;
    nhãn và tiêu đề tách chỉ làm ngữ cảnh, không sinh câu nội dung.
    Không dựng lại đánh số tự động của Word hoặc sửa chữ do OCR nhận sai.
    """
    ket_qua = []
    cap = {"chuong": None, "dieu": "MO_DAU", "khoan": None, "diem": None}
    nguon = []
    cac_cau = []
    vi_tri_tieu_de = None

    def ghi():
        if not nguon:
            return
        vi_tri_noi_dung = json.dumps(nguon, ensure_ascii=False, separators=(",", ":"))
        ket_qua.append({
            **cap,
            "trang_dau": nguon[0][2], "trang_cuoi": nguon[-1][2],
            "cau": list(cac_cau),
            "ma_doan": hashlib.sha256(vi_tri_noi_dung.encode("utf-8")).hexdigest(),
        })
        nguon.clear()
        cac_cau.clear()

    for vi_tri, muc in enumerate(doan):
        van_ban = muc["van_ban"]
        if not van_ban.strip():
            continue
        if vi_tri == vi_tri_tieu_de:
            # Giữ nguồn gốc để mã/trang vẫn dựa trên văn bản thật, không thêm câu.
            nguon.append([vi_tri, muc["thu_tu"], muc["trang"], van_ban])
            continue
        moi = dict(cap)
        dau_noi_dung = 0
        co_nhan = False
        nhan_dung_rieng = False
        if not muc.get("la_bang"):
            chuong = _khop_tieu_de(_CHUONG, van_ban)
            dieu = _khop_tieu_de(_DIEU, van_ban)
            khoan = _KHOAN_CHU.match(van_ban) or _KHOAN_SO.match(van_ban)
            diem = _DIEM.match(van_ban)
            nhan = van_ban.split(maxsplit=1)[1] if chuong or dieu else None
            nhan_dung_rieng = bool((chuong or dieu) and _NHAN_DUNG_RIENG.fullmatch(van_ban))
            if nhan_dung_rieng:
                nhan = nhan.rstrip(".:").strip()
                # Chỉ xét đoạn ngoài bảng kế tiếp; không vượt qua đoạn bị loại.
                for i in range(vi_tri + 1, len(doan)):
                    ke_tiep = doan[i]
                    if ke_tiep.get("la_bang") or not ke_tiep["van_ban"].strip():
                        continue
                    tieu_de = ke_tiep["van_ban"].strip()
                    if _la_tieu_de_tach(tieu_de):
                        nhan += " " + tieu_de
                        vi_tri_tieu_de = i
                    break
            if chuong:
                moi.update(chuong=nhan, dieu="MO_DAU", khoan=None, diem=None)
                dau_noi_dung = chuong.end()
                co_nhan = True
            elif dieu:
                moi.update(dieu=nhan, khoan=None, diem=None)
                dau_noi_dung = dieu.end()
                co_nhan = True
            elif khoan:
                moi.update(khoan=khoan.group(1).rstrip("."), diem=None)
                dau_noi_dung = khoan.end()
                co_nhan = True
            elif diem:
                moi["diem"] = diem.group(1)
                dau_noi_dung = diem.end()
                co_nhan = True
        if co_nhan:
            ghi()
            cap = moi
        nguon.append([vi_tri, muc["thu_tu"], muc["trang"], van_ban])
        if not nhan_dung_rieng:
            cac_cau.extend(_tach_cau(van_ban, dau_noi_dung))
    ghi()
    return ket_qua


def nhan_thong_tin(raw: bytes, *, ten_tep: str, loai_tai_lieu: str) -> dict:
    """Nhận trong bộ nhớ; so_doan là số đoạn cấu trúc từ cat_doan.

    ten_tep dành cho bên gọi gắn nguồn trích dẫn; không lưu hoặc đưa vào lỗi.
    so_trang bao gồm cả trang trắng tạo bởi ngắt trang cuối tài liệu.
    """
    if not isinstance(loai_tai_lieu, str) or loai_tai_lieu not in _LOAI_TAI_LIEU:
        raise DataError("M9_LOAI_TAI_LIEU_KHONG_HOP_LE", "Loại tài liệu vay không hợp lệ.")
    doan, so_trang = _doc(raw)
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "so_trang": so_trang, "so_doan": len(cat_doan(doan)),
        "loai_tai_lieu": loai_tai_lieu,
    }
