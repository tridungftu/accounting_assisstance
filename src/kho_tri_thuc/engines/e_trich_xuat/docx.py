"""TRICH-1a: bọc bộ đọc DOCX review xây dựng, phương pháp v3/2026-10-15a.

Nguồn: D:/Claude/Ho tro review ho so xay dung/review_xaydung/trich_xuat/
doc_hop_dong.py; bản trong repo: m4/review_goc/trich_xuat/doc_hop_dong.py.
Hai bản cùng SHA256 ghi dưới đây. Dùng lại parser, số tự động, cấu trúc và
phiếu kiểm tra; chỉ thay seam chuyển Word bằng đường XML Python trực tiếp.
Không sửa globals của nguồn, không tạo bản sao tạm, không chạy COM/LibreOffice.
Đây là văn bản hợp đồng, không phải capability trich.bang@1.
"""

from __future__ import annotations

import os
from types import FunctionType
import xml.etree.ElementTree as ET

from kho_tri_thuc.m4.review_goc.trich_xuat import doc_hop_dong as _goc

NGUON_SHA256 = "bbe8d9579ad9cce2c4b50e77fa734e7fc9826cd7933abe1aad2e5bf8b3d8a98b"
PHIEN_BAN_NGUON = "2026-10-15a"


def _word(*args, **kwargs):
    raise ValueError("TRICH_WORD_BI_CHAN: chỉ đọc DOCX bằng XML Python")


def kiem_docx(path):
    path = os.fspath(path)
    if os.path.splitext(path)[1].lower() != ".docx":
        raise ValueError("TRICH_CHI_DOCX: PDF phải qua e_ocr")
    return path


def _boc_ham(ham, **seam):
    """Dùng nguyên thân hàm với globals riêng; không monkeypatch nguồn dùng chung."""
    return FunctionType(ham.__code__, {**ham.__globals__, **seam}, ham.__name__,
                        ham.__defaults__, ham.__closure__)


def _dem_sua_doi(xml):
    # Nguồn đếm chuỗi '<w:ins ': bổ sung alias namespace và sửa định dạng thuần.
    root = ET.fromstring(xml)
    tags = _goc._XOA | _goc._MO_GOI
    return sum(el.tag in tags for el in root.iter())


_doc_xml = _boc_ham(_goc.read_docx, dem_sua_doi=_dem_sua_doi)
_doc_hop_dong = _boc_ham(
    _goc.read_contract,
    # Bỏ bước chuyển đổi/bản sao: read_docx luôn Accept All trong cây XML.
    _co_sua_doi=lambda path: 0,
    read_docx=_doc_xml,
    _word=_word,
    chuyen_docx=_word,
    _read_contract_pdf=_word,
)


def read_contract(path):
    """Chỉ DOCX; giữ text/preamble/articles/chunks/report của bộ đọc gốc."""
    return _doc_hop_dong(kiem_docx(path))
