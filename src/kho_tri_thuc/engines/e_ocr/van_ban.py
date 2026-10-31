"""OCR-2: ABBYY → DOCX → van_ban_tai_lieu.v1, không hiệu đính.

CD-036: dùng lại cổng/sổ trang ha_tang.cong_ocr.CongOCR (đã bọc HotFolder),
không tạo HotFolderClient/Config hay sổ thứ hai. Bọc extract_docx và
word_layout của D:/GPT/OCR/mask_ocr, local-mask-ocr 2.1.0, khảo sát 31/10/2026
(đường dẫn/SHA nguồn để chuẩn bị NGUON.md khi đóng gói CD-042):
extraction.py SHA256 f573bb79a436fd2e968a4e8376b3128a973e81bed28d8398f1abdf6c092589a8;
layout.py SHA256 ae8f1310dfc4698c559bb15f56aae7d31389a675fa4924235b2b956b2da29a33.
KTT_NGUON_OCR trỏ thư mục chứa mask_ocr; mặc định D:/GPT/OCR nếu tồn tại.
Chỉ thêm sys.path lúc import, không ghi bytecode vào nguồn. Không chép parser.
Hồ sơ chạy có thể cung cấp package nguồn hoặc hai seam hàm gốc.

Core cấp ba ID riêng: đầu vào, DOCX, phản hồi nguồn; phải lưu DOCX/phản hồi
trước khi công bố contract. Không tự gắn instance/lease/provenance hay ACK.
DOCX không có bản đồ trang vật lý: trang=[] theo contract §5; các định vị
logic và tọa độ dàn dòng chỉ nằm trong phản hồi nguồn được bảo vệ.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import os
from pathlib import Path
import re
import sys
from uuid import UUID

from kho_tri_thuc.ha_tang.primitives import DataError


MIME_DUOI = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}
MAX_BYTES = 20 * 1024**2
CANH_BAO_TRANG = "DOCX không có phân trang vật lý xác định; định vị logic nằm trong phản hồi nguồn."
_TRUONG_TEP = {"contract", "phien_ban", "tep_id", "ten_tep", "mime",
               "kich_thuoc", "sha256", "het_han_luc"}


@dataclass(frozen=True, repr=False)
class KetQuaVanBan:
    """Chỉ van_ban là payload contract; hai phần còn lại để Core lưu riêng."""

    van_ban: dict
    docx: bytes
    phan_hoi_nguon: dict


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value,
    ):
        raise DataError("OCR_ID_INVALID", "Cần UUID tệp do Core cấp.")
    return UUID(value)


def _kiem_dau_vao(raw, ref, tep_docx_id, phan_hoi_nguon_tep_id, revision):
    if type(revision) is not int or revision < 1:
        raise DataError("OCR_REVISION_INVALID", "Revision phải là số nguyên dương.")
    if not isinstance(ref, dict) or set(ref) != _TRUONG_TEP or (
        ref["contract"] != "tham_chieu_tep.v1" or ref["phien_ban"] != "1.0.0"
    ):
        raise DataError("OCR_THAM_CHIEU_INVALID", "Tham chiếu tệp sai contract.")
    ids = [_id(value) for value in (ref["tep_id"], tep_docx_id, phan_hoi_nguon_tep_id)]
    if len(set(ids)) != 3:
        raise DataError("OCR_FILE_REF_CONFLICT", "Đầu vào, DOCX và phản hồi nguồn cần ba tệp riêng.")
    ten = ref["ten_tep"]
    if not isinstance(ten, str) or not 1 <= len(ten) <= 255 or (
        any(c in ten for c in "/\\") or any(ord(c) < 32 for c in ten)
    ):
        raise DataError("OCR_TEN_TEP_INVALID", "Tên tệp không hợp lệ.")
    if not isinstance(ref["mime"], str) or ref["mime"] not in MIME_DUOI:
        raise DataError("OCR_DINH_DANG", "Chỉ nhận PDF, PNG hoặc JPEG.")
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise DataError("OCR_KICH_THUOC", "Cần bytes tài liệu không rỗng, tối đa 20 MiB.")
    if type(ref["kich_thuoc"]) is not int or ref["kich_thuoc"] != len(raw) or (
        ref["sha256"] != hashlib.sha256(raw).hexdigest()
    ):
        raise DataError("OCR_NGUON_KHONG_KHOP", "Hash hoặc kích thước không khớp nguồn Core cấp.")
    het_han = ref["het_han_luc"]
    if het_han is not None:
        try:
            if not isinstance(het_han, str) or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", het_han,
            ):
                raise ValueError
            moc = datetime.fromisoformat(het_han.replace("Z", "+00:00"))
        except ValueError:
            raise DataError("OCR_HET_HAN_INVALID", "Thời hạn tham chiếu không hợp lệ.") from None
        if moc <= datetime.now(timezone.utc):
            raise DataError("OCR_THAM_CHIEU_HET_HAN", "Tham chiếu tệp đã hết hạn.")


def _nhap_parser_nguon():
    """Import hai module nguồn chỉ đọc; khôi phục đường dẫn cả khi thiếu dependency."""
    nguon = os.environ.get("KTT_NGUON_OCR")
    if nguon:
        if not Path(nguon).is_dir():
            raise FileNotFoundError("KTT_NGUON_OCR không phải thư mục nguồn OCR.")
    elif Path("D:/GPT/OCR").is_dir():
        nguon = "D:/GPT/OCR"
    duong_dan_cu = sys.path[:]
    bytecode_cu = sys.dont_write_bytecode
    try:
        if nguon:
            sys.path.insert(0, nguon)
        sys.dont_write_bytecode = True
        return (importlib.import_module("mask_ocr.extraction"),
                importlib.import_module("mask_ocr.layout"))
    finally:
        sys.path[:] = duong_dan_cu
        sys.dont_write_bytecode = bytecode_cu


def trich_van_ban(
    raw: bytes, tham_chieu_tep: dict, *, cong_ocr, tep_docx_id: str,
    phan_hoi_nguon_tep_id: str, revision: int = 1, huy=None,
    extract_docx=None, word_layout=None,
) -> KetQuaVanBan:
    """Core đã kiểm quyền/MIME thực/giới hạn trang rồi cấp bytes theo việc.

    Gọi cổng đúng một lần, không retry/hoàn hạn mức khi kết quả chưa rõ.
    Hai seam tùy chọn là hàm nguồn, không phải đường OCR thay thế. Import
    mặc định chỉ package parser, không app.py/structured/load_config.
    """
    ref = deepcopy(tham_chieu_tep)
    _kiem_dau_vao(raw, ref, tep_docx_id, phan_hoi_nguon_tep_id, revision)
    if huy is not None and huy.is_set():
        raise DataError("OCR_HUY", "Đã hủy nhận dạng tài liệu.")
    # Kiểm parser trước khi gửi để thiếu package không tiêu hao hạn mức.
    if extract_docx is None or word_layout is None:
        extraction, layout_nguon = _nhap_parser_nguon()
        if extract_docx is None:
            extract_docx = extraction.extract_docx
        if word_layout is None:
            word_layout = layout_nguon.word_layout
    if not callable(extract_docx) or not callable(word_layout):
        raise TypeError("Cần hai hàm parser DOCX nguồn.")
    docx = cong_ocr.ocr(raw, MIME_DUOI[ref["mime"]], huy=huy)
    if huy is not None and huy.is_set():
        raise DataError("OCR_HUY", "Đã hủy nhận dạng tài liệu.")
    try:
        if not isinstance(docx, bytes) or not docx:
            raise ValueError
        # Callback rỗng chặn fallback image_text/Tesseract của extract_docx.
        legacy = extract_docx(docx, image_reader=lambda _data: "")
        layout = word_layout(docx, legacy, embedded_pages=[])
        khoi, seen = [], set()
        for unit in layout["units"]:
            ma = unit["id"]
            if not isinstance(ma, str) or not ma or ma in seen or not isinstance(unit["text"], str):
                raise ValueError
            seen.add(ma)
            khoi.append({"ma_nguon": ma, "van_ban": unit["text"], "vi_tri": {
                "tep_id": tep_docx_id, "dinh_vi": "word_layout/" + ma,
            }})
        if not isinstance(legacy.text, str) or not isinstance(legacy.warnings, list) or any(
            not isinstance(w, str) or not w for w in legacy.warnings
        ):
            raise ValueError
        canh_bao = list(dict.fromkeys([*legacy.warnings, CANH_BAO_TRANG]))
        if legacy.ocr_pages:
            canh_bao.append("Ảnh nhúng DOCX chưa được nhận dạng; không gọi backend OCR khác.")
    except Exception:
        raise DataError("OCR_DOCX_INVALID", "Không đọc được đầy đủ kết quả DOCX; cần kiểm tra nguồn.") from None
    return KetQuaVanBan(
        van_ban={
            "contract": "van_ban_tai_lieu.v1", "phien_ban": "1.0.0",
            "revision": revision, "nguon_tep_ids": [ref["tep_id"], tep_docx_id],
            "van_ban": legacy.text, "trang": [], "canh_bao": canh_bao,
            "soat_ocr": "can_soat", "da_doi_chieu": False,
            "phan_hoi_nguon_tep_id": phan_hoi_nguon_tep_id,
        },
        docx=docx,
        phan_hoi_nguon={
            "tham_chieu_tep": ref, "revision": revision,
            "docx": {"tep_id": tep_docx_id, "sha256": hashlib.sha256(docx).hexdigest(),
                     "kich_thuoc": len(docx)},
            "khoi": khoi, "layout": deepcopy(layout),
            "canh_bao": list(canh_bao),
        },
    )
