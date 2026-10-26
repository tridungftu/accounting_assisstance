"""M4-01 — adapter tái sử dụng lõi Review hồ sơ xây dựng (bản sao byte-for-byte trong `review_goc/`, SHA pin từ manifest reference).

Dùng lại nguyên thuật toán nguồn, chỉ thích nghi biên lưu trữ/cấu hình/đường dẫn:
- Trích tham số HĐ: `trich_xuat.quy_trinh.TrichXuat(...).xu_ly()` (đọc .docx, tách Điều/Khoản, dò vị trí theo danh mục, tự kiểm trích dẫn)
  + `trich_xuat.danh_muc.load_params` trên DANH_MUC_THAM_SO.xlsx đã pin (37 mã, không dùng DS_THAM_SO 36 mã của csdl_hop_dong).
  Thông tin chung (TC-*) dùng quy tắc nguồn `master_hd.trich_xuat` (cùng cách nguồn dùng khi không gửi phần mở đầu ra ngoài).
  Không bật cloud, không đọc cau_hinh_may_ai.json/khóa API/biến môi trường của nguồn, không tự mở Word/LibreOffice/OCR: tệp còn Track Changes,
  .doc hoặc PDF → trạng thái KHONG_HO_TRO thật, không đánh dấu trích xong. Local AI chưa nối ở gói này (ai=None); kiểm thử có thể inject AI
  giả lập ĐÃ KHAI BÁO (che_do AI_GIA_LAP_KHAI_BAO), không gọi là Local AI thật.
- BOQ: `may_chu.nghiep_vu.boq_doc_file / boq_xem_sheet / boq_doc_dong` (đọc sheet, đoán tiêu đề, map cột, kiểm KL×ĐG).
- Phụ lục/BOQ hiệu lực theo ngày: `csdl_hop_dong.phu_luc_ap_dung / boq_hieu_luc` chạy trên projection `sqlite3.connect(':memory:')` mỗi lần,
  nạp từ snapshot K2 (không mo_csdl, không file DB, không master song song, không SQL translator); projection chỉ-đọc sau khi nạp.
- Checklist hồ sơ đợt: `app_kiem_tra_ho_so.core.load_checklist / classify` trên danh_muc_tai_lieu.csv đã pin.
Không gọi mạng, không đọc dữ liệu thật. Lõi nguồn chưa nạp/sai pin → DataError rõ (M4_NGUON_REVIEW_CHUA_NAP / M4_NGUON_REVIEW_SAI_PIN).
"""

from __future__ import annotations

import importlib
import io
import json
import re
import sqlite3
import sys
import threading
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..ha_tang.primitives import DataError, sha256
from ..ha_tang.store import write_immutable
from . import docx_an_toan as DOCX, nap_ghim
from .sql_m17 import DANH_MUC_HO_SO as _M4_DANH_MUC_HO_SO, DANH_MUC_THAM_SO as _M4_DANH_MUC_THAM_SO

GOC = Path(__file__).resolve().parent / "review_goc"
THAM_CHIEU = "docs/M4-REVIEW-REFERENCE-20261020"
CATALOG = "trich_xuat/DANH_MUC_THAM_SO.xlsx"
CHECKLIST = "app_kiem_tra_ho_so/danh_muc_tai_lieu.csv"
# SHA-256 theo manifest reference đã lọc (Root pin); mọi tệp được import/đọc phải khớp trước khi nạp
PIN = {
    "trich_xuat/__init__.py": "f200159d6de51d346ea40d0abc2efe3132ac679dc0c31e778c10aa266490be8b",
    "trich_xuat/ai_local.py": "5ee214ea442fc924bc60a871e1f4328cfc4ae74b859160904089430fdd7dba77",
    # AI-0 25/10/2026: tạm khóa Cloud (TL 48)
    "trich_xuat/ai_cloud.py": "4bd6857437a9fa72867ae427650e84314d80aa8710745df5bd6d4136a9a6617f",  # AI-3 26/10/2026: Cloud qua cổng AI dùng chung (TL 48)
    "trich_xuat/cau_hinh.py": "53defa8fc52859c2e14cc9a00701fbc055e8eb47e0bb69156ccd8cdcacc58d93",
    "trich_xuat/cau_truc.py": "2817a46ec2fc967d1e64eae1dd68e35047e687a7b654a9c8ce03f106b9aad5c6",
    "trich_xuat/cloud.py": "d084d961c99d852ecda58e46564504013fc082a2753fbe7cb56e40160d3727a3",  # AI-3 26/10/2026: Cloud qua cổng AI dùng chung (TL 48)
    "trich_xuat/danh_muc.py": "f0796984f7b18a4d0d3389b557a6324f3ad59ca488c29ad3284e11ca97ca2ff2",
    "trich_xuat/doc_hop_dong.py": "bbe8d9579ad9cce2c4b50e77fa734e7fc9826cd7933abe1aad2e5bf8b3d8a98b",
    "trich_xuat/kiem_tra.py": "47ee35567cb7b864a6b3d6825bc90f93a7a26c0c6872a326e99ead9160467f12",
    "trich_xuat/logic.py": "f7cfcf37ff2293d8f8ea994f1ae0a69f57d1d1d9a844f0620f018a3d285a4452",
    "trich_xuat/ocr_abbyy.py": "3bf9297f0d4a162cfe828d5a5946b24b9959f9f6c50149aa8efd23e2f31df95a",
    "trich_xuat/quy_trinh.py": "a76e95a55cb7253cc7446ead9e7fd495fb9c3ea457c612259bd062aa27b26264",
    "trich_xuat/xlsx_mini.py": "a29ed16811637daa756fcb2640557ec817734d3d2ee617c30deca51d3799857b",
    "trich_xuat/xuat.py": "d255b2d01b67283b3b5febfb6c3f5f937df80c5020531bd04862fc89ad969efb",
    CATALOG: "05846a2acd60f2cde708d13a163a137ee3fb0b4e08fd84f85a7e14e7ef861bcd",
    "master_hd.py": "2a63289f5daa73a2500fff59c547395a56d823da7f0fdadd02ecfe8506429648",
    "csdl_hop_dong.py": "ef4b7883b4e2f453a9ad5ac172a6f58647b324bd13101a818a6f78af95496ffd",
    "may_chu/__init__.py": "ceb33c212694f885b6ba3e7ac8fcc67cdb68ff6dcd3e905945a224cd8088aab0",
    "may_chu/nghiep_vu.py": "9bfdc45630470bb1b4a29d808912e63a45be3f8e061565badc58874f0a4b5f0b",
    "app_kiem_tra_ho_so/core.py": "9a450b4c5b40187a3aaa1dd20e522076b33d31e02db2e07f5109b0208d8b0793",
    CHECKLIST: "77e604b1d8fbf255b2b1b776304b37000f4eb2a23494097596b7dd615cbfe6ed",
    "toan_ven.py": "a97396de2be4cecfb060cd52689f4eec648f7904a7fd132089e10e3c897f6023",  # seam L1 cho gói 2 (pin, chưa gọi)
    # M4-02B: lõi Lớp 3 chứng từ (rules C01–C09, phân loại/số/ngày/dòng hàng) + matcher hạng mục nguồn — đúng bản vendor F19 (handoff §2)
    "may_chu/chung_tu.py": "31a4d04a5af84e65d2bc3c9a44463ccf871a96f9aa053d0c79aaf5246e034cd0",
    "may_chu/phu_luc_ai.py": "743168a158bebeb6e3cda25fb4b0b31e1f9d1fc78c495a4adc5aff3b98321caf",
}
FONT_PIN = {
    "fonts.css": "66eb5d024e66f85a7eee53f341008e1c9eb0318e181db5ccb775326f7d59e9c1",
    "OFL.txt": "6b7f8f73609a25ea78c891e34cf37b06f8a676b7ea986e941e43b009110f2a85",
    "be-vietnam-0.woff2": "dc085e2fba3414e5c5bf1e6172f921a9f81c5859946a4ed3d63c1e470d96a9e2",
    "be-vietnam-1.woff2": "f7a2811e471c2973a1179ce39da3ad6bb8082381aa8d1535ccfcbc3d6d78a052",
    "be-vietnam-2.woff2": "03d1b589cff172e1a670b3573e731d3380bc326f80cf83b0d3504e3188e2e074",
    "be-vietnam-3.woff2": "86341610cbe907eecf461c9159c168d5efb52bb1a33963813a08f520555d8e66",
    "be-vietnam-4.woff2": "947d592eb7676914507ff68fc11fcf2cfdecd6ebaf0fa2af6047f66a63ea7d0f",
    "be-vietnam-5.woff2": "b621f77d35f777023aa11ca524462d511b4b28a813adbc0e9d15a10fc61dfe4e",
    "be-vietnam-6.woff2": "97658c6f9a384f29a3005c3d96e2a0d1c810192cf68979071c290f5a377a9f99",
    "be-vietnam-7.woff2": "20cc75daeaaaa0fa8af2b616b2de2b2900f0ce14ae8e9faa47d272cedd93827f",
    "be-vietnam-8.woff2": "9503dec2a7c532c8331e9600bcafea287a4fd208573b8668d85ab8d8de1863c7",
    "be-vietnam-9.woff2": "4f58af2d1c3e28a9ba14c51c82db2751d78344b75bdcb34de24a1031ebe59da6",
    "be-vietnam-10.woff2": "33d57e5bd840b03921568e08d2be1082d453e55f1ba55f421e41a1aa54e12601",
    "be-vietnam-11.woff2": "a193dd87699bd2e18ddf72dc271493ea82a23dad9f5c334d9f2a257b1e05fc30",
}
PHIEN_BAN_TRICH = "2026-10-15a"  # trich_xuat.PHIEN_BAN của bản đã pin
ENGINE = f"review_xaydung.trich_xuat@{PHIEN_BAN_TRICH}+quy_trinh:{PIN['trich_xuat/quy_trinh.py'][:12]}+master_hd:{PIN['master_hd.py'][:12]}"
BO_DOC_BOQ = f"may_chu.nghiep_vu.boq_doc_dong@{PIN['may_chu/nghiep_vu.py'][:12]}"
MA_DANH_MUC = tuple(m for m, _, _ in _M4_DANH_MUC_THAM_SO)
MA_HO_SO = tuple(r[0] for r in _M4_DANH_MUC_HO_SO)

MEDIA_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MEDIA_PDF, MEDIA_PNG, MEDIA_JPEG = "application/pdf", "image/png", "image/jpeg"
DUOI_MEDIA = {".docx": MEDIA_DOCX, ".xlsx": MEDIA_XLSX, ".pdf": MEDIA_PDF, ".png": MEDIA_PNG, ".jpg": MEDIA_JPEG, ".jpeg": MEDIA_JPEG}
VAI_MEDIA = {"HOP_DONG": {MEDIA_DOCX, MEDIA_PDF}, "PHU_LUC": {MEDIA_DOCX, MEDIA_PDF}, "BOQ": {MEDIA_XLSX},
             "HO_SO_DOT": {MEDIA_PDF, MEDIA_DOCX, MEDIA_XLSX, MEDIA_PNG, MEDIA_JPEG}}
TEP_TOI_DA = 50 * 1024 * 1024
OOXML_TOI_DA_GIAI_NEN = 300 * 1024 * 1024
OOXML_TOI_DA_ENTRY = 5000
TRUONG_BOQ = ("stt", "ma_rieng", "ten", "dvt", "kl", "don_gia", "thanh_tien")
CHE_DO_AI_KHAI_BAO = ("AI_GIA_LAP_KHAI_BAO",)

_khoa = threading.Lock()
_da_nap = False


def _loi(code: str, message: str):
    raise DataError(code, message)


# ---------------------------------------------------------------------------------------------------------------- nạp lõi nguồn
GOI_GOC = ("trich_xuat", "master_hd", "csdl_hop_dong", "may_chu", "app_kiem_tra_ho_so", "toan_ven")
MODULE_CAN = ("trich_xuat", "trich_xuat.quy_trinh", "trich_xuat.danh_muc", "trich_xuat.kiem_tra", "trich_xuat.doc_hop_dong", "master_hd",
              "csdl_hop_dong", "may_chu.nghiep_vu", "app_kiem_tra_ho_so.core")


def nap() -> None:
    """B4: kiểm đủ tệp + SHA, chặn module trùng tên đã có trong tiến trình, cài bộ nạp ghim (origin + SHA kiểm TRƯỚC exec; không sys.path,
    không .pyc), rồi mới nạp các module cần. Lỗi → DataError rõ, không có dòng mã nguồn nào chạy trước khi xác minh."""
    global _da_nap
    with _khoa:
        if _da_nap:
            return
        if not GOC.is_dir():
            _loi("M4_NGUON_REVIEW_CHUA_NAP", "Chưa nạp lõi Review hồ sơ xây dựng vào phần mềm — Root chạy tools/nap_nguon_review_m4.py (sao chép đúng bản đã pin).")
        for rel, sha in PIN.items():
            p = GOC / rel
            if p.is_symlink() or not p.is_file():
                _loi("M4_NGUON_REVIEW_CHUA_NAP", f"Thiếu tệp lõi nguồn {rel} — chạy lại tools/nap_nguon_review_m4.py.")
            if sha256(p.read_bytes()) != sha:
                _loi("M4_NGUON_REVIEW_SAI_PIN", f"Tệp lõi nguồn {rel} khác bản đã pin — không dùng.")
        trung = nap_ghim.xung_dot(GOI_GOC)
        if trung:
            _loi("M4_NGUON_REVIEW_XUNG_DOT", "Tiến trình đã có module trùng tên lõi nguồn không do bộ nạp ghim nạp: " + ", ".join(trung[:5]))
        global _BO
        try:
            bo = nap_ghim.cai(nap_ghim.BoNapGhim(GOC, {k: v for k, v in PIN.items() if k.endswith(".py")}, GOI_GOC))
            for ten in MODULE_CAN:
                m = importlib.import_module(ten)
                if not bo.hop_le(ten, m):
                    _loi("M4_NGUON_REVIEW_XUNG_DOT", f"Module {ten} không do bộ nạp ghim nạp đúng pin/origin — dừng.")
        except nap_ghim.LoiNapGhim as exc:
            raise DataError(exc.code, str(exc)) from None
        sai = bo.sai_cache()
        if sai:
            _loi("M4_NGUON_REVIEW_XUNG_DOT", "Module lõi nguồn trong cache sai pin/origin: " + ", ".join(sai[:5]))
        if importlib.import_module("trich_xuat").PHIEN_BAN != PHIEN_BAN_TRICH:
            _loi("M4_NGUON_REVIEW_SAI_PIN", "Phiên bản lõi trích khác bản đã pin.")
        _BO = bo
        _da_nap = True


_BO = None


def _m(ten: str):
    """M4-01B2: lấy module lõi nguồn SAU khi xác minh lại toàn bộ cache (dấu ghim = PIN, origin = review_goc/<rel>, đúng instance loader).
    Cache giả/cũ/sai origin → DataError, không dùng; cache-miss vẫn đi qua kiểm SHA trước exec của bộ nạp ghim."""
    nap()
    sai = _BO.sai_cache()
    if sai:
        _loi("M4_NGUON_REVIEW_XUNG_DOT", "Module lõi nguồn trong cache sai pin/origin — không dùng: " + ", ".join(sai[:5]))
    try:
        m = importlib.import_module(ten)
    except nap_ghim.LoiNapGhim as exc:
        raise DataError(exc.code, str(exc)) from None
    if not _BO.hop_le(ten, m):
        _loi("M4_NGUON_REVIEW_XUNG_DOT", f"Module {ten} không đúng pin/origin — không dùng.")
    return m


def _tep_ghim(rel: str) -> Path:
    """Tệp dữ liệu đã pin (danh mục/checklist): kiểm lại SHA ngay trước khi dùng."""
    p = GOC / rel
    if p.is_symlink() or not p.is_file() or sha256(p.read_bytes()) != PIN[rel]:
        _loi("M4_NGUON_REVIEW_SAI_PIN", f"Tệp {rel} khác bản đã pin — không dùng.")
    return p


def tai_san_font(ten: str) -> bytes:
    """Font Be Vietnam Pro (OFL) của giao diện nguồn — chỉ đúng tên đã pin, kiểm SHA trước khi trả."""
    if ten not in FONT_PIN:
        _loi("NOT_FOUND", "Không có tài sản này.")
    p = GOC / "giao_dien" / "fonts" / ten
    if not p.is_file():
        _loi("M4_NGUON_REVIEW_CHUA_NAP", "Font giao diện nguồn chưa được nạp.")
    raw = p.read_bytes()
    if sha256(raw) != FONT_PIN[ten]:
        _loi("M4_NGUON_REVIEW_SAI_PIN", "Font khác bản đã pin.")
    return raw


def danh_muc_tham_so() -> list[dict]:
    """37 tham số đang dùng theo DANH_MUC_THAM_SO.xlsx đã pin (load_params nguồn); khác bộ mã của CSDL → dừng."""
    params = _m("trich_xuat.danh_muc").load_params(str(_tep_ghim(CATALOG)))
    ma = [p["ma"] for p in params]
    if len(ma) != len(MA_DANH_MUC) or sorted(ma) != sorted(MA_DANH_MUC):
        _loi("M4_DANH_MUC_LECH", "Danh mục tham số nguồn khác 37 mã đã chốt trong CSDL — không trích.")
    return params


def danh_muc_ho_so() -> list[dict]:
    rows = _m("app_kiem_tra_ho_so.core").load_checklist(_tep_ghim(CHECKLIST))
    if sorted(r["ma"] for r in rows) != sorted(MA_HO_SO):
        _loi("M4_DANH_MUC_HO_SO_LECH", "Danh mục tài liệu nguồn khác danh mục hồ sơ đợt trong CSDL.")
    return [{"ma": r["ma"], "nhom": r["nhom"], "ten": r["ten"], "bat_buoc_nguon": bool(r["bat_buoc"]), "muc_dich": r.get("muc_dich") or ""} for r in rows]


def goi_y_muc(ten_tep: str) -> list[dict]:
    """Gợi ý mục checklist theo tên tệp (classify nguồn, chỉ tên — không đọc nội dung); người dùng vẫn chọn mục."""
    core = _m("app_kiem_tra_ho_so.core")
    return [{"ma": m, "diem": float(d), "ly_do": l} for m, d, l in core.classify(ten_tep, "", core.load_checklist(_tep_ghim(CHECKLIST)))]


# ---------------------------------------------------------------------------------------------------------------- kiểm tệp tải lên
def kiem_ten(ten) -> str:
    if (not isinstance(ten, str) or not 1 <= len(ten) <= 200 or ten != ten.strip() or ten in (".", "..")
            or any(c in ten for c in '/\\:*?"<>|') or any(ord(c) < 32 for c in ten)):
        _loi("M4_TEN_TEP_SAI", "Tên tệp không hợp lệ (không đường dẫn, ký tự điều khiển hay ký tự đặc biệt; 1–200 ký tự).")
    return ten


def _kiem_ooxml(raw: bytes, phan: str) -> None:
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, ValueError, OSError, EOFError):
        _loi("M4_TEP_HONG", "Tệp Office không mở được (không phải gói OOXML hợp lệ).")
    with z:
        infos = z.infolist()
        if len(infos) > OOXML_TOI_DA_ENTRY or sum(i.file_size for i in infos) > OOXML_TOI_DA_GIAI_NEN:
            _loi("M4_TEP_NEN_QUA_LON", "Tệp Office có quá nhiều phần hoặc dung lượng giải nén quá lớn.")
        names = {i.filename for i in infos}
        for n in names:
            if n.startswith("/") or "\\" in n or ".." in n.split("/"):
                _loi("M4_TEP_DUONG_DAN_SAI", "Tệp Office chứa đường dẫn nội bộ không an toàn.")
            if n.lower().endswith("vbaproject.bin"):
                _loi("M4_TEP_CO_MACRO", "Tệp có macro — không nhận nội dung thực thi.")
        if "[Content_Types].xml" not in names or phan not in names:
            _loi("M4_TEP_HONG", "Tệp Office thiếu phần chính (không đúng loại tài liệu đã khai).")


def kiem_tep(raw, ten, media, vai_tro) -> dict:
    """Kiểm bytes thật trước khi lưu: rỗng/quá lớn/tên/đuôi ↔ media khai báo ↔ chữ ký tệp ↔ vai trò tài liệu. Không đọc đường dẫn từ trình duyệt."""
    if vai_tro not in VAI_MEDIA:
        _loi("M4_VAI_TRO_TAI_LIEU_SAI", "Vai trò tài liệu không hợp lệ.")
    if not isinstance(raw, (bytes, bytearray)):
        _loi("M4_TEP_RONG", "Không có nội dung tệp.")
    raw = bytes(raw)
    if not raw:
        _loi("M4_TEP_RONG", "Tệp rỗng (0 byte) — không lưu.")
    if len(raw) > TEP_TOI_DA:
        _loi("M4_TEP_QUA_LON", "Mỗi tệp tối đa 50 MB.")
    kiem_ten(ten)
    if DUOI_MEDIA.get(Path(ten).suffix.lower()) != media:
        _loi("M4_TEP_MEDIA_KHONG_KHOP", "Đuôi tệp và loại tệp khai báo không khớp.")
    if media not in VAI_MEDIA[vai_tro]:
        _loi("M4_TEP_SAI_LOAI", "Loại tệp này không dùng cho vai trò tài liệu đã chọn.")
    if media == MEDIA_PDF and not raw.startswith(b"%PDF-"):
        _loi("M4_TEP_MEDIA_KHONG_KHOP", "Nội dung không phải PDF.")
    if media == MEDIA_PNG and not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        _loi("M4_TEP_MEDIA_KHONG_KHOP", "Nội dung không phải PNG.")
    if media == MEDIA_JPEG and not raw.startswith(b"\xff\xd8\xff"):
        _loi("M4_TEP_MEDIA_KHONG_KHOP", "Nội dung không phải JPEG.")
    if media == MEDIA_DOCX:
        _kiem_ooxml(raw, "word/document.xml")
    if media == MEDIA_XLSX:
        _kiem_ooxml(raw, "xl/workbook.xml")
    return {"ten": ten, "media": media, "sha256": sha256(raw), "byte_length": len(raw)}


# ---------------------------------------------------------------------------------------------------------------- trích tham số
def _json_an_toan(v):
    return json.loads(json.dumps(v, ensure_ascii=False, default=str))


def ban_lam_viec(raw: bytes, thu_muc: Path, duoi: str) -> Path:
    """Bản làm việc content-addressed trong DataRoot M4 (ghi một lần, không ghi đè; giữ lại làm bằng chứng)."""
    p = Path(thu_muc) / f"{sha256(raw)}{duoi}"
    write_immutable(p, raw)
    return p


def kiem_docx_an_toan(raw: bytes) -> None:
    """B3 + M4-01B2 (sửa 4): chặn TRƯỚC mọi entrypoint đọc DOCX (read_contract/TrichXuat) — chỉ DOCX OOXML, không còn thay đổi chưa chốt theo
    namespace XML (m4/docx_an_toan.py; bộ đọc nguồn sẽ mở Word/LibreOffice rồi rmtree temp nếu có sửa đổi). XML hỏng/DOCTYPE → báo không đọc được.
    Không mở Office, không cleanup, không đánh dấu đã đọc; không phụ thuộc mã vendor."""
    if not isinstance(raw, (bytes, bytearray)) or not bytes(raw[:4]) == b"PK\x03\x04":
        _loi("M4_DOCX_KHONG_HO_TRO", "Chỉ đọc được tệp Word .docx trong gói này (PDF/.doc cần OCR/chuyển đổi — chưa bật).")
    try:
        kq = DOCX.dem_sua_doi_docx(bytes(raw))
    except DOCX.KhongDocDuoc as exc:
        _loi("M4_DOCX_KHONG_HO_TRO", f"Tệp Word không đọc được an toàn ({exc}).")
    if kq["so_sua_doi"]:
        _loi("M4_DOCX_CON_SUA_DOI", f"Tệp hợp đồng còn {kq['so_sua_doi']} chỗ Track Changes chưa chốt — cần Accept All bằng Word rồi tải lại; "
                                    "phần mềm không tự mở Word.")


def van_ban_hop_dong(raw: bytes, thu_muc: Path) -> str:
    """Văn bản HĐ theo đúng bộ đọc nguồn (read_contract) — dùng đối chiếu trích dẫn khi phòng dự án sửa tay. Kiểm an toàn DOCX trước (B3)."""
    kiem_docx_an_toan(raw)
    read_contract = _m("trich_xuat.doc_hop_dong").read_contract
    try:
        return read_contract(str(ban_lam_viec(raw, thu_muc, ".docx")))["text"]
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        raise DataError("M4_KHONG_DOC_DUOC_HOP_DONG", f"Bộ đọc nguồn không đọc được tệp hợp đồng ({type(exc).__name__}).") from None


def kiem_trich_dan(van_ban: str, gia_tri: str, trich_dan: str, dieu_khoan: str = "") -> str:
    """Tự kiểm của nguồn (kiem_tra.check): trích dẫn nguyên văn trong HĐ + số liệu nằm trong trích dẫn. Trả chuỗi 'OK…' hoặc 'KIỂM TRA: …'."""
    kt = _m("trich_xuat.kiem_tra")
    check, loose, norm = kt.check, kt.loose, kt.norm
    return check({"gia_tri": gia_tri, "trich_dan": trich_dan, "dieu_khoan": dieu_khoan or "", "ghi_chu": ""}, norm(van_ban), loose(van_ban))


def la_ok(ck: str) -> bool:
    return str(ck or "").startswith("OK")


RE_YC_TRICH = re.compile(r"[A-Za-z0-9_.:-]{1,200}")  # request_id ý định trích (engine #6 common/v1)


def trich_hop_dong(raw: bytes, media: str, thu_muc: Path, *, client=None, request_id: str | None = None, ai=None, che_do_ai: str | None = None) -> dict:
    """CRM-41-01: wrapper MỎNG qua engine trích DÙNG CHUNG #6 (nguon/trich_chung_6, contract common/v1, RULE_ONLY, loại XD, catalog đã ghim,
    'ALL' → đủ 37 mã). Không còn chạy TrichXuat/master_hd chép trong review_goc và không fallback sang đó. Giữ nguyên kiểm an toàn DOCX/Track
    Changes TRƯỚC khi gửi bytes; engine chưa sẵn sàng/lỗi → trạng thái rõ (không trả XONG). Trả {che_do, engine, catalog_sha256, trang_thai,
    ly_do, phieu, ket_qua[37]} như trước: CO_GIA_TRI (giá trị + trích dẫn nguyên văn từ engine) / KHONG_AP_DUNG / KHONG_QUY_DINH / CHUA_CO."""
    from ..nguon import trich_chung_6 as T6
    if ai is not None or che_do_ai is not None:
        _loi("M4_AI_KHONG_HO_TRO", "Engine dùng chung chỉ chạy RULE_ONLY ở gói này — không nhận bộ AI (kể cả giả lập) và không dùng lõi chép.")
    if client is None or not RE_YC_TRICH.fullmatch(request_id or ""):
        _loi("M4_TRICH6_CHUA_CAU_HINH", "Thiếu client engine #6 hoặc mã ý định trích.")
    che_do = "QUY_TAC_KHONG_AI"
    base = {"che_do": che_do, "engine": "trich6.common/v1", "catalog_sha256": T6.CATALOG["XD"]["catalog_sha256"]}
    if media != MEDIA_DOCX:
        return {**base, "trang_thai": "KHONG_HO_TRO", "phieu": {}, "ket_qua": [],
                "ly_do": "Gói M4-01 chỉ trích tệp Word .docx; PDF cần lớp chữ/OCR — OCR chưa bật trong gói này. Tải bản Word hoặc nhập tay có trích dẫn sau khi có bản Word."}
    try:  # M4-01B2: kiểm theo namespace XML TRƯỚC khi tạo thư mục làm việc/gọi bộ đọc nguồn
        sd = DOCX.dem_sua_doi_docx(bytes(raw))
    except DOCX.KhongDocDuoc as exc:
        return {**base, "trang_thai": "LOI", "phieu": {}, "ket_qua": [], "ly_do": f"Tệp Word không đọc được an toàn ({exc})."}
    if sd["so_sua_doi"]:
        return {**base, "trang_thai": "KHONG_HO_TRO", "phieu": {"track_changes": sd["so_sua_doi"], "phan": sd["phan"]}, "ket_qua": [],
                "ly_do": f"Tệp còn {sd['so_sua_doi']} chỗ Track Changes chưa chốt — cần Accept All bằng Word rồi tải lại; phần mềm không tự mở Word."}
    try:
        r6 = client.trich(bytes(raw), ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id=request_id)
    except T6.ChuaRo:
        raise  # UNKNOWN: không ghi lần trích; thử lại cùng ý định sẽ đối soát lượt/kết quả đã biết
    except DataError as exc:
        if T6.Trich6Client._la_chua_ro(exc):  # FIX01 F2: mất kết nối/đọc dở/5xx không mã/lượt mồ côi → UNKNOWN, KHÔNG ghi FINAL LOI/revision/biên nhận
            raise T6.ChuaRo("TRICH6_CHUA_RO", f"Chưa rõ kết quả engine #6 ({exc.code}) — giữ nguyên khóa/lệnh để thử lại.") from None
        return {**base, "trang_thai": "LOI", "phieu": {}, "ket_qua": [], "ly_do": f"Engine trích dùng chung #6 báo lỗi ({exc.code}): {str(exc)[:300]}"}
    cm = r6["common"]
    impl = str((cm.get("implementation") or {}).get("sha256") or "")[:12]
    base["engine"] = f"trich6.common/v1@{impl}+catalog:{cm['catalog_sha256'][:12]}"
    if cm["catalog_sha256"] != PIN[CATALOG]:
        return {**base, "trang_thai": "LOI", "phieu": {}, "ket_qua": [], "ly_do": "Danh mục engine khác danh mục 37 mã đã ghim của M4."}
    view = T6.chieu_tham_so(r6["ket_qua"], raw_sha256=r6["raw_sha256"])
    rows = []
    for d in view["tham_so"]:
        tt = d["trang_thai"]
        nguon_rule = (d.get("nguon") or "") == "Quy tắc"
        row = {"ma": d["ma"], "trang_thai": "CHUA_CO", "gia_tri": None, "don_vi": (d.get("don_vi") or None), "dieu_khoan": (d.get("dieu_khoan") or None),
               "trich_dan": None, "kiem_tra": d.get("kiem_tra") or None, "ly_do": None, "vi_tri": (d.get("vi_tri_do_duoc") or "")[:2000] or None,
               "nguon": "CHUA_CO"}
        if tt in ("CO_GIA_TRI", "KHONG_AP_DUNG", "KHONG_QUY_DINH") and nguon_rule:
            v, q = str(d["gia_tri"]).strip(), str(d["trich_dan"]).strip()
            row.update(trang_thai=tt, trich_dan=q[:4000], nguon="QUY_TAC", **({"gia_tri": v[:2000]} if tt == "CO_GIA_TRI" else {"ly_do": v[:1000]}))
            if d.get("ghi_chu"):
                row["kiem_tra"] = f"{row['kiem_tra'] or ''} | {d['ghi_chu']}".strip(" |")
        elif tt == "CHUA_CO":
            row["kiem_tra"] = (row["kiem_tra"] or "") + " — engine RULE_ONLY chưa trích được; xem vị trí dò được và nhập tay có trích dẫn nguyên văn"
        rows.append(row)
    if sorted(r["ma"] for r in rows) != sorted(MA_DANH_MUC):  # SQL XONG cần đủ 37 — không đổi DDL để nhận tập con
        return {**base, "trang_thai": "LOI", "phieu": {}, "ket_qua": [], "ly_do": "Kết quả engine không đủ danh mục 37 mã."}
    thu_muc = Path(thu_muc)
    write_immutable(thu_muc / f"ket_qua_6_{r6['raw_sha256']}.json", r6["raw_ket_qua"])  # raw gốc giữ nguyên bytes (bằng chứng)
    phieu = _json_an_toan({"phieu_kiem_tra": r6["ket_qua"].get("phieu_kiem_tra"), "tom_tat": r6["ket_qua"].get("tom_tat"),
                           "che_do_nguon": r6["ket_qua"].get("che_do"), "luot_6": r6["luot"], "ket_qua_6_sha256": r6["raw_sha256"],
                           "adapter": view["adapter"], "common": view["common"],
                           "quy_tac_thong_tin_chung": sorted(r["ma"] for r in rows if r["nguon"] == "QUY_TAC")})
    return {**base, "trang_thai": "XONG", "ly_do": None, "phieu": phieu, "ket_qua": rows}


# ---------------------------------------------------------------------------------------------------------------- BOQ
def _so_text(x):
    """Số ô BOQ (openpyxl trả int/float) → chuỗi thập phân từ repr (không làm tròn thêm); None giữ None."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            return None
        try:
            return format(Decimal(repr(x)), "f")
        except InvalidOperation:
            return None
    return None


def boq_xem(path: Path, sheet: str | None = None) -> dict:
    nv = _m("may_chu.nghiep_vu")
    try:
        out = nv.boq_doc_file(str(path)) if sheet is None else nv.boq_xem_sheet(str(path), sheet)
    except DataError:
        raise
    except Exception as exc:  # noqa: BLE001 — openpyxl/tệp hỏng: báo rõ, giữ tệp
        raise DataError("M4_BOQ_KHONG_DOC_DUOC", f"Không đọc được BOQ bằng bộ đọc nguồn ({type(exc).__name__}).") from None
    return _json_an_toan(out)


TRUONG_SO_BOQ = ("kl", "don_gia", "thanh_tien")


def _la_so(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and x not in (float("inf"), float("-inf"))


def phan_loai_loi(x: dict, it: dict | None) -> tuple[str, str]:
    """M4-01B2 (sửa 3): phân loại một lỗi của parser nguồn (may_chu/nghiep_vu.py boq_doc_dong, bản ghim) theo DỮ LIỆU CÓ CẤU TRÚC của chính dòng
    (`it` = item cùng số dòng) + so KHỚP NGUYÊN VĂN với thông điệp mà nhánh nguồn tương ứng sinh ra cho đúng dòng đó — không tìm từ khóa tự do
    (tên hạng mục có thể chứa 'KL × ĐG' hay 'bị trùng').
    - KL hoặc ĐG không phải số (parser trả None) → CHAN BOQ_SO_KHONG_DOC_DUOC, bất kể tên hạng mục.
    - KL, ĐG, thành tiền đều là số, lệch vượt ngưỡng của nguồn, và thông điệp đúng mẫu số học của dòng → PHAT_HIEN BOQ_SO_HOC_LECH (không chặn).
    - Mã riêng trùng, thông điệp đúng mẫu trùng mã của dòng → CHAN BOQ_MA_TRUNG.
    - Còn lại (không khớp dòng/thông điệp lạ) → CHAN BOQ_LOI_KHAC (thận trọng)."""
    noi_dung = str(x.get("noi_dung") or "")
    if it is None:
        return "CHAN", "BOQ_LOI_KHAC"
    ten = str(it.get("ten") or "")
    kl, dg, tt = it.get("kl"), it.get("don_gia"), it.get("thanh_tien")
    if it.get("ma_rieng") and noi_dung == f"Mã hạng mục '{it['ma_rieng']}' bị trùng — mỗi hạng mục một mã riêng":
        return "CHAN", "BOQ_MA_TRUNG"
    if kl is None or dg is None:
        return "CHAN", "BOQ_SO_KHONG_DOC_DUOC"
    if _la_so(kl) and _la_so(dg) and _la_so(tt) and abs(kl * dg - tt) > max(1.0, abs(tt) * 1e-6) \
            and noi_dung == f"{ten[:60]}: KL × ĐG = {kl * dg:,.0f} khác thành tiền {tt:,.0f}":
        return "PHAT_HIEN", "BOQ_SO_HOC_LECH"
    return "CHAN", "BOQ_LOI_KHAC"


def _o(v) -> dict:
    """Ô gốc: giữ giá trị như trong tệp + loại ô. Trống (None/chuỗi rỗng) KHÁC số 0 tường minh."""
    if v is None:
        return {"tho": None, "kieu": "TRONG"}
    if isinstance(v, str):
        return {"tho": v, "kieu": "TRONG" if v.strip() == "" else "CHU"}
    if isinstance(v, bool):
        return {"tho": str(v), "kieu": "CHU"}
    if isinstance(v, (int, float)):
        return {"tho": _so_text(v), "kieu": "SO"}
    return {"tho": str(v), "kieu": "CHU"}


def _o_goc(path: Path, sheet: str, cot: dict, dong_can) -> dict:
    """Đọc lại đúng các ô số (KL/ĐG/thành tiền) của các dòng parser đã nhận, để không mất trạng thái trống/0 do legacy đổi trống thành 0."""
    import openpyxl
    from openpyxl.utils import column_index_from_string
    idx = {k: column_index_from_string(cot[k]) for k in TRUONG_SO_BOQ if cot.get(k)}
    can = set(dong_can)
    if not can:
        return {}
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        ws = wb[sheet]
        out = {}
        for r, row in enumerate(ws.iter_rows(min_row=1, max_row=max(can), values_only=True), 1):
            if r in can:
                out[r] = {k: {**_o(row[i - 1] if i - 1 < len(row) else None), "o": f"{cot[k]}{r}"} for k, i in idx.items()}
        return out
    finally:
        wb.close()


def boq_doc(path: Path, sheet, hang_tieu_de, cot) -> tuple[list[dict], list[dict], list[dict]]:
    """Đọc dòng BOQ theo map cột (boq_doc_dong nguồn). Trả (dòng, lỗi chặn, phát hiện).
    - Lỗi chặn: map/đọc số/mã trùng/khóa trùng/không có dòng — BOQ CO_LOI, chưa đủ căn cứ.
    - Phát hiện (vd KL×ĐG ≠ thành tiền): dòng đã đọc/map đủ — giữ cho review, KHÔNG chặn nộp.
    - Mỗi dòng giữ o_goc (giá trị ô + loại TRONG/SO/CHU + địa chỉ ô); số typed NULL khi ô trống (không lấy 0 do legacy tự gán)."""
    if not isinstance(sheet, str) or not 1 <= len(sheet) <= 100:
        _loi("M4_BOQ_MAP_SAI", "Cần chọn sheet BOQ.")
    if isinstance(hang_tieu_de, bool) or not isinstance(hang_tieu_de, int) or not 1 <= hang_tieu_de <= 10000:
        _loi("M4_BOQ_MAP_SAI", "Dòng tiêu đề phải là số nguyên 1–10000.")
    if not isinstance(cot, dict) or set(cot) - set(TRUONG_BOQ):
        _loi("M4_BOQ_MAP_SAI", "Map cột chỉ gồm STT, mã hạng mục, tên, ĐVT, khối lượng, đơn giá, thành tiền.")
    cot = {k: v for k, v in cot.items() if v not in (None, "")}
    if any(not isinstance(v, str) or not re.fullmatch(r"[A-Z]{1,3}", v) for v in cot.values()):
        _loi("M4_BOQ_MAP_SAI", "Cột phải là chữ cái cột Excel (A…ZZZ).")
    nv = _m("may_chu.nghiep_vu")
    try:
        items, loi = nv.boq_doc_dong(str(path), sheet, hang_tieu_de, cot)
    except ValueError as exc:
        raise DataError("M4_BOQ_MAP_SAI", str(exc)[:300]) from None
    except Exception as exc:  # noqa: BLE001
        raise DataError("M4_BOQ_KHONG_DOC_DUOC", f"Không đọc được BOQ bằng bộ đọc nguồn ({type(exc).__name__}).") from None
    try:
        goc = _o_goc(path, sheet, cot, [int(it["dong"]) for it in items])
    except Exception as exc:  # noqa: BLE001
        raise DataError("M4_BOQ_KHONG_DOC_DUOC", f"Không đọc lại được ô gốc BOQ ({type(exc).__name__}).") from None
    rows = []
    for it in items:
        dong = int(it["dong"])
        o_goc = goc.get(dong, {})
        ma_hm = (it.get("ma_rieng") or "|".join([it.get("nhom") or "", it.get("ten") or "", it.get("dvt") or ""]))[:500]
        so = {k: (None if o_goc.get(k, {}).get("kieu") == "TRONG" else _so_text(it.get(k))) for k in TRUONG_SO_BOQ}
        rows.append({"dong": dong, "ma_hm": ma_hm, "stt": it.get("stt") or None, "nhom": it.get("nhom") or None, "ten": it.get("ten") or "",
                     "dvt": it.get("dvt") or "", **so, "ma_rieng": it.get("ma_rieng") or None,
                     "o_goc": {k: o_goc.get(k, {"tho": None, "kieu": "KHONG_MAP"}) for k in TRUONG_SO_BOQ}})
    loi_chan, phat_hien = [], []
    theo_dong = {}
    for it in items:
        theo_dong.setdefault(int(it["dong"]), it)
    for x in loi:
        dong = int(x.get("dong") or 0)
        loai, ma = phan_loai_loi(x, theo_dong.get(dong))
        noi_dung = str(x.get("noi_dung") or "")[:300]
        muc = {"ma": ma, "dong": dong, "sheet": sheet, "noi_dung": noi_dung,
               "o": [f"{cot[k]}{dong}" for k in TRUONG_SO_BOQ if cot.get(k)] if dong else []}
        (phat_hien if loai == "PHAT_HIEN" else loi_chan).append(muc)
    for ma, n in Counter(r["ma_hm"] for r in rows).items():
        if n > 1:
            loi_chan.append({"ma": "BOQ_KHOA_TRUNG", "dong": 0, "sheet": sheet, "o": [],
                             "noi_dung": f"Hạng mục trùng khóa '{ma[:80]}' ({n} dòng) — cần mã hạng mục riêng"})
    if not rows:
        loi_chan.append({"ma": "BOQ_KHONG_CO_DONG", "dong": 0, "sheet": sheet, "o": [], "noi_dung": "Không đọc được dòng hạng mục nào với map cột này"})
    return rows, loi_chan, phat_hien


# ---------------------------------------------------------------------------------------------------------------- seam SQLite legacy (projection)
_TT_PL = {"DA_KY": "Đã ký", "DU_THAO": "Dự thảo", "DA_HUY": "Đã hủy"}


def hieu_luc(phu_luc: list[dict], boq_goc: list[dict], boq_pl: dict, ngay: str | None) -> dict:
    """PL/BOQ hiệu lực tại ngày bằng thuật toán nguồn (phu_luc_ap_dung/boq_hieu_luc) trên projection SQLite :memory: dựng từ snapshot K2.
    Projection chỉ-đọc sau khi nạp, đóng sau lần tính; không là authority (CSDL K2 vẫn quyết gate nộp)."""
    cs = _m("csdl_hop_dong")
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    try:
        con.executescript(cs.SCHEMA)
        con.execute("INSERT INTO hop_dong (ma_hd, so_hd) VALUES ('HD', 'HD')")
        so = {}
        for i, p in enumerate(phu_luc, 1):
            con.execute("INSERT INTO phu_luc (id, ma_hd, so_pl, ngay_ky, ngay_hieu_luc, doi_boq, trang_thai) VALUES (?,?,?,?,?,?,?)",
                        (i, "HD", p["so_pl"], str(p["ngay_ky"]), str(p["ngay_hieu_luc"]), 1 if p["doi_boq"] else 0, _TT_PL[p["trang_thai"]]))
            so[str(p["id"])] = i
        for r in boq_goc:
            con.execute("INSERT INTO boq_dong (ma_hd, pl_id, thao_tac, ma_hm, stt, nhom, ten, dvt, kl, don_gia, thanh_tien_ghi) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        ("HD", None, "GOC", r["ma_hm"], r.get("stt"), r.get("nhom"), r.get("ten"), r.get("dvt"), r.get("kl"), r.get("don_gia"), r.get("thanh_tien")))
        for pl_id, rows in boq_pl.items():
            if str(pl_id) not in so:
                continue
            for r in rows:
                con.execute("INSERT INTO boq_dong (ma_hd, pl_id, thao_tac, ma_hm, stt, nhom, ten, dvt, kl, don_gia, thanh_tien_ghi) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            ("HD", so[str(pl_id)], r["thao_tac"], r["ma_hm"], r.get("stt"), r.get("nhom"), r.get("ten"), r.get("dvt"), r.get("kl"),
                             r.get("don_gia"), r.get("thanh_tien")))
        con.commit()
        con.execute("PRAGMA query_only = ON")
        pls = cs.phu_luc_ap_dung(con, "HD", ngay)
        hl, bo = cs.boq_hieu_luc(con, "HD", ngay)
        return {"ngay": ngay, "phu_luc_ap_dung": [r["so_pl"] for r in pls], "so_hang_muc_hieu_luc": len(hl), "so_hang_muc_bo": len(bo),
                "hang_muc_do_phu_luc": sorted(k for k, v in hl.items() if v.get("nguon") != "HĐ gốc"),
                "cach_tinh": "csdl_hop_dong.phu_luc_ap_dung + boq_hieu_luc trên projection SQLite :memory: (chỉ hiển thị, không phải authority)"}
    finally:
        con.close()


# ---------------------------------------------------------------------------------------------------------------- M4-02A Review L1/L2
# Định danh engine Review = đúng các tệp vendor đã pin mà L1/L2 gọi (không phải engine mới). Thay đổi pin → engine_sha256 đổi → lần chạy khác basis.
REVIEW_PHIEN_BAN = "m4.review/1"
REVIEW_PIN = {k: PIN[k] for k in ("toan_ven.py", "master_hd.py", "csdl_hop_dong.py", "may_chu/nghiep_vu.py")}
ENGINE_REVIEW = (f"review_xaydung.L1L2@toan_ven:{PIN['toan_ven.py'][:12]}+master_hd:{PIN['master_hd.py'][:12]}"
                 f"+csdl:{PIN['csdl_hop_dong.py'][:12]}+nghiep_vu:{PIN['may_chu/nghiep_vu.py'][:12]}+{REVIEW_PHIEN_BAN}")
ENGINE_REVIEW_SHA = sha256(json.dumps({"engine": ENGINE_REVIEW, "pin": REVIEW_PIN}, sort_keys=True, ensure_ascii=False).encode("utf-8"))
# tên sheet không chứa ký tự Excel cấm (\ / ? * [ ] :) — chặn dạng đường dẫn/tham chiếu tệp ngoài ngay ở cú pháp
RE_O_DICH = re.compile(r"(?:'(?:[^'\\/?*\[\]:]|''){1,100}'|[^'!\s\\/?*\[\]:][^!\\/?*\[\]:]{0,99})!\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}")
_TT_PL_REVIEW = {"DA_KY": "Đã ký", "DU_THAO": "Dự thảo", "DA_HUY": "Đã hủy"}


def kiem_o_dich(v):
    """Ô đích cây truy vết do NGƯỜI chọn (tùy chọn): 'Sheet!D38' hoặc "'Tên sheet'!$D$38". Không nhận đường dẫn/công thức/tham chiếu file ngoài."""
    if v in (None, ""):
        return None
    if not isinstance(v, str) or len(v) > 150 or "[" in v or not RE_O_DICH.fullmatch(v.strip()):
        _loi("M4_REVIEW_O_DICH_SAI", "Ô đích phải dạng Sheet!Ô (vd \"'2. TH'!D38\"), không đường dẫn hay tham chiếu tệp ngoài.")
    return v.strip()


def _so_thuc(t):
    """Số typed của K2 (chuỗi thập phân chính xác) → float cho thuật toán nguồn; NULL giữ None (không thành 0)."""
    if t in (None, ""):
        return None
    try:
        return float(Decimal(str(t)))
    except (InvalidOperation, ValueError):
        return None


def ma_hd_projection(hop_dong_id: str) -> str:
    """Khóa HĐ chuẩn cục bộ của MỘT lần tính (không fuzzy search của nguồn): 'M4' + UUID viết hoa không gạch."""
    return "M4" + str(hop_dong_id).replace("-", "").upper()


def chup_review_l2(co_so: dict, conn_tin_cay, *, conn_phien):
    """Bổ sung basis nội bộ trong transaction RR của K2; không đọc nếu thiếu phiên.

    DTO DL3 cố ý bỏ ID/khóa/lịch sử thô nên compute đọc cột nguồn bằng cùng
    kiểm quyền và bộ chọn bản hiện hành DL2. Không đọc lại PG trong worker.
    Các dòng đánh dấu review_chep chỉ là dữ liệu tính, không là BOQ đã duyệt.
    """
    if conn_phien is None or not co_so.get("hop_dong"):
        return co_so
    from .review_data_pg import ReviewDataPG
    from .review_phu_luc_pg import _COT, _rows

    reader = ReviewDataPG(conn_tin_cay)
    hd = reader._kiem_quyen_doc(co_so["hop_dong"]["id"], conn_phien=conn_phien)
    with conn_tin_cay.transaction():
        source, _state = reader._nguon_hien_hanh(hd)
        if source is None:  # giữ nguyên cả basis/hash cũ cho ba trạng thái NULL
            return co_so
        data = {"nguon_id": source, "trang_thai": "HIEN_HANH"}
        for table, columns in _COT.items():
            if table == "thay_doi_tham_so":
                query = """SELECT t.* FROM m4.review_chep_thay_doi_tham_so t
                    JOIN m4.review_chep_phu_luc p ON (p.nguon_id,p.id)=(t.nguon_id,t.pl_id)
                    WHERE p.nguon_id=%s AND p.hop_dong_id=%s::uuid ORDER BY t.pl_id,t.ma_ts"""
            else:
                query = f"SELECT * FROM m4.review_chep_{table} WHERE nguon_id=%s AND hop_dong_id=%s::uuid ORDER BY id"
            data[table] = [{k: r[k] for k in columns} for r in _rows(conn_tin_cay, query, (source, hd))]
    return _basis_review_l2(co_so, data)


def _basis_review_l2(co_so, data):
    """Giữ metadata PL/BOQ trong basis để coverage cũ không bỏ qua PL chép.

    Khóa có namespace riêng; không coi khóa INTEGER nguồn là UUID vận hành.
    Bản thô bất biến giữ đủ cột/NULL cho projection; không hợp nhất khi trùng.
    """
    data = _json_an_toan(data)
    co_so = dict(co_so, review_chep=data)
    pls = list(co_so.get("phu_luc") or [])
    boq = list(co_so.get("boq") or [])
    reasons = []
    ngay = (co_so.get("dot") or {}).get("ngay_nghiem_thu")
    if ngay:
        from .review_phu_luc_pg import _phu_luc_tai_ngay
        operational = [dict(p, trang_thai=_TT_PL_REVIEW.get(p["trang_thai"], p["trang_thai"])) for p in pls]
        _, reasons = _phu_luc_tai_ngay(operational + data["phu_luc"], str(ngay)[:10])
    for p in data["phu_luc"]:
        if any(p["so_pl"].strip().casefold() == q["so_pl"].strip().casefold() for q in pls):
            reasons.append("Trùng số phụ lục chép Review và phụ lục vận hành.")
    if any(b.get("phu_luc_id") is None for b in boq) and any(r["pl_id"] is None for r in data["boq_dong"]):
        reasons.append("BOQ gốc có cả nguồn Review và nguồn vận hành; cần chốt nguồn.")
    co_so["review_chep"]["can_xem_lai"] = bool(reasons)
    co_so["review_chep"]["ly_do"] = reasons
    pl_ids = {p["id"]: f"review:{data['nguon_id']}:{p['id']}" for p in data["phu_luc"]}
    reverse_tt = {v: k for k, v in _TT_PL_REVIEW.items()}
    pls += [dict(p, id=pl_ids[p["id"]], trang_thai=reverse_tt.get(p["trang_thai"], "CHUA_RO"), review_chep=True)
            for p in data["phu_luc"]]
    groups = {}
    for r in data["boq_dong"]:
        groups.setdefault(r["pl_id"], []).append(dict(r, dong=r["id"], thanh_tien=r.get("thanh_tien_ghi")))
    for pl, rows in groups.items():
        boq.append({"id": f"review:{data['nguon_id']}:boq:{pl}", "phu_luc_id": pl_ids.get(pl),
                    "trang_thai": "DA_MAP", "sheet": "Review", "dong": rows, "review_chep": True})
    return dict(co_so, phu_luc=pls, boq=boq)


def projection_l2(co_so: dict):
    """L2: projection SQLite :memory: theo đúng SCHEMA nguồn, nạp từ MỘT basis đã chụp từ PG (không mo_csdl/nap_master/nap_dot, không DB nguồn,
    không SQL translator). Chỉ nạp phần có căn cứ typed: tham số CO_GIA_TRI; PL metadata (GT/tham số đổi theo PL CHƯA có kiểu ở M17 → NULL,
    coverage xử lý); BOQ gốc + BOQ PL đã map (THEM/THAY; BO chưa có kiểu); ghép tay hiện hành của HĐ. dot_thanh_toan/kl_thanh_toan để TRỐNG vì
    chưa có lịch sử đợt đã được reviewer duyệt (DA_NOP không phải 'đã duyệt'). Bản review_chep đã qua kiểm quyền phiên lúc chụp basis được nạp đủ
    PL/thay đổi tham số/BOQ theo schema nguồn. Không đọc lại PG ở bước tính. Nạp xong bật query_only; người gọi đóng sau khi tính + ghi báo cáo.
    Trả (con, ban_do) với ban_do = khóa HĐ cục bộ + nguồn từng mã HM về ID PG ổn định."""
    imported = co_so.get("review_chep") or {}
    if imported.get("can_xem_lai"):
        _loi("M4_REVIEW_CAN_XEM_LAI", "Cần xem lại: " + " ".join(imported["ly_do"]) + " Cần Anh/lead chốt nguồn; chưa tính.")
    cs, mh = _m("csdl_hop_dong"), _m("master_hd")
    hd = co_so["hop_dong"]
    ma_hd = ma_hd_projection(hd["id"])
    ts = {t["ma"]: t for t in co_so.get("tham_so") or []}

    def co(ma):
        t = ts.get(ma)
        return t["gia_tri"] if t and t["trang_thai"] == "CO_GIA_TRI" and t.get("gia_tri") not in (None, "") else None
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    try:
        con.executescript(cs.SCHEMA)
        con.execute("INSERT INTO hop_dong (ma_hd, so_hd, phan_loai, loai_gia, ngay_ky, gia_tri_hd, gom_vat, vat) VALUES (?,?,?,?,?,?,?,?)",
                    (ma_hd, hd["so_hop_dong"], None, co("TT-01"), None, cs.tien(co("TT-02")) if co("TT-02") else None, co("TT-03"),
                     cs.ty_le(co("TT-04")) if co("TT-04") else None))
        for t in co_so.get("tham_so") or []:
            if t["trang_thai"] == "CO_GIA_TRI" and t.get("gia_tri") not in (None, ""):
                con.execute("INSERT INTO tham_so (ma_hd, ma_ts, gia_tri, don_vi, trang_thai) VALUES (?,?,?,?,?)",
                            (ma_hd, t["ma"], t["gia_tri"], t.get("don_vi"), "CO_GIA_TRI"))
        pl_so = {}
        for i, p in enumerate((p for p in co_so.get("phu_luc") or [] if not p.get("review_chep")), 1):
            con.execute("INSERT INTO phu_luc (id, ma_hd, so_pl, ngay_ky, ngay_hieu_luc, doi_boq, trang_thai) VALUES (?,?,?,?,?,?,?)",
                        (i, ma_hd, p["so_pl"], str(p["ngay_ky"])[:10], str(p["ngay_hieu_luc"])[:10], 1 if p["doi_boq"] else 0, _TT_PL_REVIEW[p["trang_thai"]]))
            pl_so[str(p["id"])] = i
        nguon_boq = {}
        for b in co_so.get("boq") or []:
            if b.get("review_chep"):
                continue
            if b["trang_thai"] != "DA_MAP":
                continue
            pl = None if b["phu_luc_id"] is None else pl_so.get(str(b["phu_luc_id"]))
            if b["phu_luc_id"] is not None and pl is None:
                continue
            for r in b["dong"]:
                thao_tac = "GOC" if pl is None else r["thao_tac"]
                khoa = mh.khoa({"nhom": r.get("nhom") or "", "ten": r["ten"], "dvt": r["dvt"]})
                con.execute("""INSERT INTO boq_dong (ma_hd, pl_id, thao_tac, ma_hm, stt, nhom, ten, dvt, kl, don_gia, thanh_tien_ghi, khoa, vi_tri_nguon, ma_rieng)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (ma_hd, pl, thao_tac, r["ma_hm"], r.get("stt"), r.get("nhom"), r["ten"], r["dvt"], _so_thuc(r.get("kl")),
                             _so_thuc(r.get("don_gia")), _so_thuc(r.get("thanh_tien")), khoa, f"{b['sheet']}!dòng {r['dong']}", r.get("ma_rieng")))
                nguon_boq.setdefault(r["ma_hm"], []).append({"boq_id": b["id"], "dong": r["dong"], "phu_luc_id": b["phu_luc_id"], "thao_tac": thao_tac})
        if imported.get("trang_thai") == "HIEN_HANH":
            from .review_phu_luc_pg import _COT, _NUMERIC
            source_pl = {}
            for table in ("phu_luc", "thay_doi_tham_so", "boq_dong"):
                columns = _COT[table]
                for original in imported[table]:
                    row = {k: original.get(k) for k in columns}
                    if "ma_hd" in row:
                        row["ma_hd"] = ma_hd
                    if table == "phu_luc":
                        local_id = len(pl_so) + 1
                        source_pl[row["id"]] = local_id
                        identity = f"review:{imported['nguon_id']}:{row['id']}"
                        pl_so[identity] = row["id"] = local_id
                    elif row.get("pl_id") is not None:
                        row["pl_id"] = source_pl[row["pl_id"]]
                    if table == "boq_dong":
                        row.pop("id")  # PK cục bộ, vẫn giữ thứ tự dòng nguồn
                    for k in row.keys() & _NUMERIC:
                        row[k] = _so_thuc(row[k])
                    con.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))
        for m in co_so.get("manual_map") or []:
            con.execute("INSERT INTO khop_hang_muc (ma_hd, khoa_hstt, ma_hm, cach_khop, nguoi_xac_nhan, ngay) VALUES (?,?,?,?,?,?)",
                        (ma_hd, m["khoa_hstt"], m["ma_hm"], "ghép tay", m.get("tao_boi"), str(m.get("tao_luc") or "")[:19]))
        con.commit()
        con.execute("PRAGMA query_only = ON")
    except BaseException:
        con.close()
        raise
    return con, {"ma_hd": ma_hd, "nguon_boq": nguon_boq, "phu_luc": {v: k for k, v in pl_so.items()}}


# ---------------------------------------------------------------------------------------------------------------- M4-02B Chứng từ L3
# Định danh engine L3 = đúng các tệp vendor mà L3 gọi (chung_tu rules C01–C09 + matcher phu_luc_ai + reader doc_hop_dong/ocr_abbyy bảng DOCX +
# master_hd bỏ dấu/tiêu đề cột). Thay đổi pin → engine_sha256 đổi → basis khác. Không bật trích tham số chép (HĐ vẫn qua engine #6 dùng chung).
L3_PHIEN_BAN = "m4.chung_tu/1"
L3_PIN = {k: PIN[k] for k in ("may_chu/chung_tu.py", "may_chu/phu_luc_ai.py", "trich_xuat/doc_hop_dong.py", "trich_xuat/ocr_abbyy.py",
                              "trich_xuat/cau_hinh.py", "master_hd.py", "csdl_hop_dong.py")}
ENGINE_L3 = (f"review_xaydung.L3@chung_tu:{PIN['may_chu/chung_tu.py'][:12]}+phu_luc_ai:{PIN['may_chu/phu_luc_ai.py'][:12]}"
             f"+doc_hop_dong:{PIN['trich_xuat/doc_hop_dong.py'][:12]}+ocr_abbyy:{PIN['trich_xuat/ocr_abbyy.py'][:12]}+{L3_PHIEN_BAN}")
ENGINE_L3_SHA = sha256(json.dumps({"engine": ENGINE_L3, "pin": L3_PIN}, sort_keys=True, ensure_ascii=False).encode("utf-8"))
# giới hạn đọc của nguồn `chung_tu.doc_file` (XLSX iter_rows max_row=400, max_col=30) — giữ nguyên, báo LIMITED khi tệp vượt
L3_XLSX_DONG, L3_XLSX_COT = 400, 30
# media hiện được nhận (admission M4-01) → cách đọc L3. PDF/ảnh cần lớp chữ/OCR/AI provider: chưa có provider được cấp phép/cấu hình → NOT_CONFIGURED.
L3_DOC_NATIVE = (MEDIA_DOCX, MEDIA_XLSX)
L3_CAN_PROVIDER = (MEDIA_PDF, MEDIA_PNG, MEDIA_JPEG)
L3_PROVIDER = {"OCR": {"trang_thai": "NOT_CONFIGURED", "ly_do": "Chưa có OCR được cấp phép/cấu hình trong ranh giới tiến trình sở hữu — không chạy ABBYY Hot Folder/"
                                                            "converter của nguồn, không giả kết quả"},
               "PDF_LOP_CHU": {"trang_thai": "NOT_CONFIGURED", "ly_do": "Đọc lớp chữ PDF không tách được bảng dòng hàng; nguồn cần Local AI cho phần này — chưa cấu hình"},
               "LOCAL_AI": {"trang_thai": "NOT_CONFIGURED", "ly_do": "Chưa có Local AI được cấu hình (ai=None) — không đọc dòng hàng chứng từ dạng form"}}


def l3_kiem_tep(raw: bytes, media: str) -> dict:
    """Admission L3 cho MỘT tệp đã capture (bytes khớp SHA): trả {doc: 'NATIVE'|'PROVIDER'|'KHONG_HO_TRO', ly_do, track_changes}.
    DOCX/XLSX: kiểm gói OOXML an toàn (đường dẫn nội bộ, macro, bom nén) TRƯỚC reader; DOCX còn Track Changes → KHONG_HO_TRO (nguồn sẽ mở Word/
    LibreOffice Accept All — không chạy). PDF/ảnh → PROVIDER (NOT_CONFIGURED ở gói này). Không mở Office, không đọc đường dẫn ngoài."""
    raw = bytes(raw)
    if media in L3_CAN_PROVIDER:
        return {"doc": "PROVIDER", "ly_do": "PDF/ảnh cần lớp chữ/OCR/Local AI — provider chưa cấu hình (NOT_CONFIGURED); raw giữ nguyên", "track_changes": None}
    if media not in L3_DOC_NATIVE:
        return {"doc": "KHONG_HO_TRO", "ly_do": f"Loại tệp {media} chưa được nhận ở cổng hiện hành", "track_changes": None}
    try:
        _kiem_ooxml(raw, "word/document.xml" if media == MEDIA_DOCX else "xl/workbook.xml")
    except DataError as exc:
        return {"doc": "KHONG_HO_TRO", "ly_do": f"Gói Office không an toàn/không hợp lệ ({exc.code})", "track_changes": None}
    if media == MEDIA_DOCX:
        try:
            sd = DOCX.dem_sua_doi_docx(raw)
        except DOCX.KhongDocDuoc as exc:
            return {"doc": "KHONG_HO_TRO", "ly_do": f"Tệp Word không đọc được an toàn ({exc})", "track_changes": None}
        if sd["so_sua_doi"]:
            return {"doc": "KHONG_HO_TRO", "ly_do": f"Tệp Word còn {sd['so_sua_doi']} chỗ Track Changes chưa chốt — cần Accept All bằng Word rồi tải lại; "
                                                  "phần mềm không tự mở Word", "track_changes": sd["so_sua_doi"]}
    return {"doc": "NATIVE", "ly_do": None, "track_changes": 0}


def _gia_tri_o_l3(v) -> str:
    """ĐÚNG phép chuyển ô của `chung_tu.doc_file` (nhánh XLSX) — để đếm dòng không trống y như nguồn (không đổi số/không làm tròn)."""
    import datetime as _dt
    return "" if v is None else (v.strftime("%d/%m/%Y") if isinstance(v, (_dt.date, _dt.datetime)) else str(v)).strip()


def l3_vi_tri_xlsx(path: Path) -> dict:
    """Seam locator XLSX (chỉ đọc): song song với `chung_tu.doc_file`, ghi số dòng VẬT LÝ của từng dòng không trống TRƯỚC khi nguồn nén dòng trống,
    theo đúng thứ tự `wb.worksheets` và đúng giới hạn 400×30 cached values (data_only). Trả {bang: [{sheet, dong: [số dòng vật lý]}], gioi_han: [...],
    o_cong_thuc_khong_cache: n}. `bang` i (1-based) ↔ "bảng i" của nguồn (nguồn chỉ thêm sheet có dòng). Vượt giới hạn/công thức chưa có cache → ghi rõ.
    L3 A2: mỗi `bang` thêm `cot_dau` (cột vật lý của cột logic 0) và `o_gop` (vùng gộp trong vùng đọc; None nếu không đọc được, lý do ở `o_gop_ly_do`)."""
    import openpyxl
    out, gioi_han = [], []
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        for ws in wb.worksheets:
            dong = []
            for r, row in enumerate(ws.iter_rows(max_row=L3_XLSX_DONG, max_col=L3_XLSX_COT, values_only=True), 1):
                if any(_gia_tri_o_l3(v) for v in row):
                    dong.append(r)
            if dong:
                out.append({"sheet": ws.title, "dong": dong})
            vuot_dong = any(any(_gia_tri_o_l3(v) for v in row) for row in ws.iter_rows(min_row=L3_XLSX_DONG + 1, values_only=True))
            vuot_cot = any(any(_gia_tri_o_l3(v) for v in row[L3_XLSX_COT:]) for row in ws.iter_rows(max_row=L3_XLSX_DONG, values_only=True))
            if vuot_dong or vuot_cot:
                gioi_han.append({"sheet": ws.title, "vuot_dong": vuot_dong, "vuot_cot": vuot_cot,
                                 "ly_do": f"Sheet có dữ liệu ngoài vùng nguồn đọc ({L3_XLSX_DONG} dòng × {L3_XLSX_COT} cột) — phần ngoài vùng KHÔNG được kiểm"})
    finally:
        wb.close()
    # L3 A2: cột logic j (0-based) của dòng nguồn ↔ cột vật lý cot_dau + j (iter_rows nguồn bắt đầu từ cột A); ô gộp giao vùng đọc 400×30 (chế độ
    # read_only không có merged_cells → mở thêm một lần chỉ đọc). Không đọc được → o_gop None + lý do (locator ô báo LIMITED, không giả CHECKED).
    try:
        wm = openpyxl.load_workbook(str(path), data_only=True)
        try:
            gop = {ws.title: sorted(str(rg) for rg in ws.merged_cells.ranges if rg.min_row <= L3_XLSX_DONG and rg.min_col <= L3_XLSX_COT)
                   for ws in wm.worksheets}
        finally:
            wm.close()
        ly_gop = None
    except Exception as exc:  # noqa: BLE001 — chỉ mất bằng chứng ô gộp; vị trí dòng vẫn giữ
        gop, ly_gop = None, f"Không đọc được danh sách ô gộp ({type(exc).__name__}) — không xác nhận ô tiêu đề nằm ngoài vùng gộp"
    for b in out:
        b["cot_dau"] = 1
        b["o_gop"] = None if gop is None else gop.get(b["sheet"], [])
    khong_cache = 0
    wf = openpyxl.load_workbook(str(path), data_only=False, read_only=True)
    wv = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        for ws_f, ws_v in zip(wf.worksheets, wv.worksheets):
            for row_f, row_v in zip(ws_f.iter_rows(max_row=L3_XLSX_DONG, max_col=L3_XLSX_COT, values_only=True),
                                    ws_v.iter_rows(max_row=L3_XLSX_DONG, max_col=L3_XLSX_COT, values_only=True)):
                khong_cache += sum(1 for f, v in zip(row_f, row_v) if isinstance(f, str) and f.startswith("=") and v is None)
    finally:
        wf.close()
        wv.close()
    return {"bang": out, "gioi_han": gioi_han, "o_cong_thuc_khong_cache": khong_cache, "o_gop_ly_do": ly_gop}


def l3_vi_tri_docx(path: Path) -> dict:
    """Seam locator DOCX (chỉ đọc): song song với `ocr_abbyy.docx_bang` của nguồn — bảng cấp thân (top-level) theo thứ tự, dòng w:tr không trống
    (cùng quy tắc ô: `_chu_o` nguồn, gridSpan, vMerge continue = trống). Trả {bang: [{bang_vat_ly, dong: [chỉ số w:tr vật lý]}], bang_long: n}.
    `bang` i ↔ "bảng i" của nguồn. Bảng lồng trong ô: nguồn gộp chữ vào ô ngoài (không tách dòng) → ghi số lượng để coverage báo LIMITED.
    L3 A2: `o` song song `dong` — mỗi dòng giữ, mỗi CỘT LOGIC của nguồn (`ocr_abbyy._bang` trải gridSpan) → [w:tc vật lý 1-based, vị trí trong
    gridSpan 0-based, vMerge None|'restart'|'continue'] để ghi rõ cột logic khác ô vật lý."""
    import xml.etree.ElementTree as ET
    ocr = _m("trich_xuat.ocr_abbyy")
    w = ocr._W
    with zipfile.ZipFile(str(path)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{w}body")
    out, vat_ly, bang_long = [], 0, 0
    for el in (body if body is not None else []):
        if el.tag != f"{w}tbl":
            continue
        vat_ly += 1
        bang_long += len(el.findall(f".//{w}tc//{w}tbl"))
        dong, cot = [], []
        for ti, tr in enumerate(el.findall(f"{w}tr"), 1):
            o, logic = [], []
            for ci, tc in enumerate(tr.findall(f"{w}tc"), 1):
                pr = tc.find(f"{w}tcPr")
                vcont, span, vm_val = False, 1, None
                if pr is not None:
                    gs = pr.find(f"{w}gridSpan")
                    if gs is not None:  # đúng quy tắc trải gridSpan của `ocr_abbyy._bang`
                        try:
                            span = max(1, int(gs.get(f"{w}val") or 1))
                        except ValueError:
                            span = 1
                    vm = pr.find(f"{w}vMerge")
                    if vm is not None:
                        vm_val = vm.get(f"{w}val") or "continue"
                    vcont = vm_val == "continue"
                o.append("" if vcont else ocr._chu_o(tc))
                logic.extend([ci, k, vm_val] for k in range(span))
            if any(o):
                dong.append(ti)
                cot.append(logic)
        if dong:
            out.append({"bang_vat_ly": vat_ly, "dong": dong, "o": cot})
    return {"bang": out, "bang_long": bang_long}
