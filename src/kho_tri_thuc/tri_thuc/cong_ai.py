"""Cổng AI dùng chung (AI-2a · TL 48 §1, Anh chốt 25/10/2026; TL 35 §3 dòng "Cổng AI").

Mọi nơi trong phần mềm cần gọi model AI đi qua MỘT cổng này (engine #6 chuyển sang ở AI-3):

1. **Định tuyến tĩnh theo loại việc** — bảng ``LOAI_VIEC`` khai báo một chỗ: mã → mô tả, có được dùng Cloud không,
   ngưỡng tin cậy. Cắm Jev Router sau (TL 34 §6.2).
2. **Luôn thử Local AI trước** (``ai_cuc_bo.ask_local``: LAN/Tailscale, không DNS/HTTPS/proxy). Dùng Cloud chỉ khi
   (a) Local không chạy, hoặc (b) Local không chắc: không đúng định dạng, thiếu/sai trích dẫn, không qua kiểm của
   Python, thiếu trường, độ tin cậy dưới ngưỡng. (c) Kiểm xác suất theo loại việc và cửa sổ nhật ký (AI-4a).
3. **Cloud chỉ qua Mask file v2** (chế độ API 2.7.x, chỉ ``127.0.0.1``): ``GET /api/v1/trang-thai`` phải có
   ``danh_muc == "da_mo"`` → ``POST /api/v1/che``; chỉ gửi khi HTTP 200 **và** ``gui_duoc is True`` **và**
   ``con_sot`` rỗng **và** danh mục đang mở, rồi cổng tự kiểm lại không còn định danh đã khai trong bản đã che.
   Mọi trường hợp khác → **không gửi**, quay về kết quả Local (hoặc "chưa có kết quả"). Nhận kết quả → mở che
   (``POST /api/v1/mo-che``, ``ket_thuc_luot``) → Python kiểm trích dẫn nguyên văn trên **văn bản gốc**.
   Định danh dạng số luôn được khai ``nhom`` khi gọi ``/che`` (MASK-2). Không gửi XML hóa đơn thô ra Cloud.
4. **Công tắc Cloud** ``cong_ai.cloud_bat`` mặc định TẮT: tắt → không bao giờ gọi Mask hay Cloud.
   Không có khóa API / tệp khóa Mask / Mask không chạy → coi như tắt, báo trạng thái tiếng Việt.
5. **Nhật ký mỗi lượt** qua giao diện ``BoGhiNhatKy`` (bản ghi ``BanGhiCongAI``): loại việc, đường Local/Cloud,
   model, số ký tự gửi/nhận, token, thời gian, chi phí ước tính, mã lượt Mask, lý do chuyển Cloud / không gửi —
   **không** ghi văn bản gốc, văn bản đã che, câu trả lời hay khóa. Bộ ghi PostgreSQL ``nhat_ky.cong_ai_goi`` làm ở
   AI-2b (bảng ánh xạ cột ở docstring ``BanGhiCongAI``).
6. Kết quả có LLM tối đa **Vàng**; trường LLM điền phải có trích dẫn nguyên văn (TL 48 §1.7).

**Ngoại lệ duy nhất của quy tắc "không code nào gọi thẳng api.anthropic.com / api.openai.com"** (CLAUDE.md §2,
TL 48 §1.3): lớp nhà cung cấp Cloud trong module này (``NhaCungCapAnthropic``, ``NhaCungCapOpenAI``). Chỉ cổng giữ
khóa API: khóa đọc từ biến môi trường lúc gọi (``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` hoặc tên khai trong cài
đặt; ``.env`` do tiến trình chạy nạp, module không đọc ``.env``), chỉ nằm trong biến cục bộ của lượt gọi, không
in, không ghi nhật ký, không đưa vào thông báo lỗi. Khóa Mask đọc từ tệp (đường dẫn cấu hình) cùng quy tắc.
"""
from __future__ import annotations

import http.client
import json
import logging
import os
import random
import re
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping, Protocol
from urllib.parse import urlparse

from . import ai_cuc_bo

_LOG = logging.getLogger(__name__)

MUC_VANG = "VANG"   # có đề xuất của AI — người duyệt xem trích dẫn (mức cao nhất cho kết quả có LLM)
MUC_DO = "DO"       # chưa có kết quả dùng được — người làm tay
DUONG_LOCAL = "LOCAL"
DUONG_CLOUD = "CLOUD"

HE_THONG = "Bạn là trợ lý kế toán. Chỉ trả lời đúng định dạng được yêu cầu."
HUONG_DAN_DINH_DANG = (
    "Trả lời DUY NHẤT một đối tượng JSON, không thêm chữ nào khác, theo mẫu:\n"
    '{"truong": [{"ten": "<tên trường>", "gia_tri": "<giá trị>", "trich_dan": "<đoạn trích>"}], '
    '"do_tin_cay": <số từ 0 đến 1>}\n'
    "- trich_dan: chép NGUYÊN VĂN một đoạn ngắn trong phần Văn bản có chứa giá trị, không sửa chữ nào.\n"
    "- gia_tri: ngắn gọn, giữ nguyên chữ và số liệu như trong văn bản.\n"
    "- Không tìm thấy thông tin thì bỏ trường đó, không đoán.\n"
    "- do_tin_cay: mức chắc chắn chung của câu trả lời.\n"
    "- Nhãn trong ngoặc vuông là bí danh: giữ nguyên khi chép."
)


# ---------------------------------------------------------------------------------------------------------------
# 1. Bảng loại việc (định tuyến tĩnh, khai báo một chỗ)
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class LoaiViec:
    ma: str
    mo_ta: str
    duoc_dung_cloud: bool
    nguong_tin_cay: float  # 0..1; Local trả độ tin cậy dưới ngưỡng → "không chắc"


LOAI_VIEC: dict[str, LoaiViec] = {item.ma: item for item in (
    # Đề xuất ban đầu (AI-2a); Cloud còn tắt toàn cục tới AI-4 — cờ và ngưỡng chốt lại khi đo độ chính xác Local.
    LoaiViec("BOC_TACH_HOP_DONG", "Bóc tách tham số hợp đồng từ PDF/văn bản tự do (engine #6 — M4 · Nghiệm thu & "
             "chi phí dự án, CRM)", True, 0.80),
    LoaiViec("BOC_TACH_NGHIEM_THU", "Bóc tách biên bản nghiệm thu từ văn bản tự do (M4 · Nghiệm thu & chi phí dự án)",
             True, 0.80),
    LoaiViec("DOC_NOI_DUNG_CHUYEN_KHOAN", "Đọc nội dung chuyển khoản tự do trên sao kê để điền trường còn trống "
             "(M1 · Tiền gửi ngân hàng)", True, 0.80),
    LoaiViec("CHON_UNG_VIEN", "Chọn một trong 2–5 ứng viên (đối tượng, loại nghiệp vụ) khi khóa cứng và lịch sử chưa "
             "quyết được — tên ứng viên bị che thành bí danh nên Cloud không giúp được", False, 0.90),
    LoaiViec("PHAN_TICH_TRA_LOI_ZALO", "Phân tích câu trả lời Zalo của người duyệt — chỉ Local AI", False, 0.80),
)}


def loai_viec(ma: str) -> LoaiViec:
    try:
        return LOAI_VIEC[ma]
    except KeyError:
        raise ValueError(f"Loại việc chưa khai báo trong bảng định tuyến cổng AI: {ma!r}") from None


# ---------------------------------------------------------------------------------------------------------------
# 2. Cài đặt (``settings.cong_ai``) — không bao giờ chứa khóa
# ---------------------------------------------------------------------------------------------------------------
NHA_CUNG_CAP_MAC_DINH = {
    "anthropic": {"model": "claude-opus-5-5", "bien_khoa": "ANTHROPIC_API_KEY"},
    "openai": {"model": "", "bien_khoa": "OPENAI_API_KEY"},  # model OpenAI phải khai trong cài đặt
}
# USD / 1 triệu token (bảng giá Anthropic ghi ngày 06/10/2026); cài đặt ``bang_gia`` ghi đè/bổ sung.
BANG_GIA_USD_MAC_DINH = {
    "claude-opus-5-5": {"vao": 4.00, "ra": 20.00},
    "claude-sonnet-5-5": {"vao": 2.00, "ra": 10.00},
    "claude-haiku-5-5": {"vao": 0.10, "ra": 0.50},
}
CAI_DAT_MAC_DINH = {
    "cloud_bat": False,                      # Công tắc Cloud — vẫn TẮT mặc định
    "nha_cung_cap": "anthropic",
    "model": "",                             # "" = model mặc định của nhà cung cấp
    "bien_khoa_api": "",                     # "" = ANTHROPIC_API_KEY / OPENAI_API_KEY
    "mask_url": "http://127.0.0.1:8017",     # Mask file v2 (8017, hoặc 8019 khi 8017 đang có bản cũ)
    "mask_tep_khoa": "",                     # đường dẫn tệp khóa API của Mask (config/mask-api.key)
    "mask_timeout_giay": 30,
    "cloud_timeout_giay": 180,
    "max_tokens": 16000,
    "fallback_khi_tu_choi": True,            # Anthropic: chạy lại trên model dự phòng khi bị từ chối (refusal)
    "bang_gia": {},
    "kiem_xac_suat": {},
}
# Cần Anh: toàn bộ con số dưới đây là mặc định tạm của AI-4a, chưa phải lịch đã duyệt.
# Giữ 0% khi chưa cấu hình; đề xuất TL 48 §1.6 là 20% khi Anh cho phép lấy mẫu.
# settings.cong_ai.kiem_xac_suat.ty_le_theo_loai = {"BOC_TACH_HOP_DONG": 0.20, ...}.
# Tỷ lệ dùng thang 0..1. Cùng một cửa sổ N cho mọi bậc; thiếu mẫu thì không giảm.
KIEM_XAC_SUAT_MAC_DINH = {
    "ty_le_ban_dau": 0.0,
    "ty_le_theo_loai": {},
    "cua_so": 100,
    "ty_le_san": 0.05,
    "nguong_tang_lai": 0.90,
    "bac_thang": ((50, 0.90, 0.10), (100, 0.95, 0.05)),  # (số kiểm, độ chính xác >, tỷ lệ)
}
LOCAL_DUNG = "KIEM_LOCAL_DUNG"
LOCAL_SAI = "KIEM_LOCAL_SAI"
_TEN_BIEN_KHOA = re.compile(r"[A-Z][A-Z0-9_]{0,60}_(?:API_)?KEY")


def cai_dat_kiem_xac_suat(raw: object) -> dict:
    """Tham số tập trung, không nhận NaN/Infinity/bool hay tỷ lệ ngoài 0..1."""
    raw = raw if isinstance(raw, dict) else {}
    cfg = {**KIEM_XAC_SUAT_MAC_DINH, **raw}

    def ty_le(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError("Tỷ lệ kiểm và ngưỡng chính xác phải là số từ 0 đến 1.")
        return float(value)

    cfg["ty_le_ban_dau"] = ty_le(cfg["ty_le_ban_dau"])
    cfg["ty_le_san"] = ty_le(cfg["ty_le_san"])
    cfg["nguong_tang_lai"] = ty_le(cfg["nguong_tang_lai"])
    if not cfg["ty_le_san"] or cfg["nguong_tang_lai"] < 0.90:
        raise ValueError("Sàn kiểm phải lớn hơn 0; ngưỡng tăng lại tối thiểu 90%.")
    if type(cfg["cua_so"]) is not int or not 1 <= cfg["cua_so"] <= 10000:
        raise ValueError("Cửa sổ kiểm phải là số nguyên từ 1 đến 10000.")
    if not isinstance(cfg["ty_le_theo_loai"], dict):
        raise ValueError("Tỷ lệ theo loại việc phải là bảng mã loại việc → tỷ lệ.")
    cfg["ty_le_theo_loai"] = {loai_viec(ma).ma: ty_le(rate)
                              for ma, rate in cfg["ty_le_theo_loai"].items()}
    if not isinstance(cfg["bac_thang"], (tuple, list)):
        raise ValueError("Bậc kiểm phải là danh sách (số kiểm, ngưỡng, tỷ lệ).")
    bac = []
    for item in cfg["bac_thang"]:
        if not isinstance(item, (tuple, list)) or len(item) != 3:
            raise ValueError("Bậc kiểm phải gồm số kiểm, ngưỡng và tỷ lệ.")
        n, nguong, rate = item
        if type(n) is not int or n < 1:
            raise ValueError("Số lượt tối thiểu của bậc kiểm phải là số nguyên dương.")
        nguong, rate = ty_le(nguong), ty_le(rate)
        if nguong < cfg["nguong_tang_lai"]:
            raise ValueError("Ngưỡng giảm kiểm không được dưới ngưỡng tăng lại.")
        bac.append((n, nguong, rate))
    cfg["bac_thang"] = tuple(sorted(bac))
    return cfg


def ty_le_kiem_hien_hanh(cfg: dict, ma: str, tk: dict | None) -> float:
    """Tính lại từ cửa sổ hiện tại: giảm theo bậc, tụt dưới ngưỡng → về tỷ lệ ban đầu."""
    rate = cfg["ty_le_theo_loai"].get(ma, cfg["ty_le_ban_dau"])
    if rate == 0:
        return 0.0  # chỉ tắt lấy mẫu khi được cấu hình rõ, không do tự giảm
    rate = max(cfg["ty_le_san"], rate)
    if tk and tk["so_kiem_cua_so"]:
        chinh_xac = tk["so_dung_cua_so"] / tk["so_kiem_cua_so"]
        if chinh_xac >= cfg["nguong_tang_lai"]:
            for n, nguong, muc in cfg["bac_thang"]:
                if tk["so_kiem_cua_so"] >= n and chinh_xac > nguong:
                    rate = min(rate, max(cfg["ty_le_san"], muc))
    return rate


def cong_ai_settings(settings: dict | None) -> dict:
    """Chuẩn hóa ``settings["cong_ai"]`` (hoặc chính nhóm cong_ai). Trả thêm ``loi`` (tiếng Việt, rỗng nếu hợp lệ)."""
    raw = (settings or {}).get("cong_ai") if isinstance(settings, dict) and "cong_ai" in settings else settings
    raw = raw if isinstance(raw, dict) else {}
    value = {key: (dict(val) if isinstance(val, dict) else val) for key, val in CAI_DAT_MAC_DINH.items()}
    for key in CAI_DAT_MAC_DINH:
        if key in raw and raw[key] is not None:
            value[key] = raw[key]
    value["cloud_bat"] = value["cloud_bat"] is True
    value["fallback_khi_tu_choi"] = value["fallback_khi_tu_choi"] is not False
    loi = []
    ncc = str(value["nha_cung_cap"] or "").strip().lower()
    if ncc not in NHA_CUNG_CAP_MAC_DINH:
        loi.append("Nhà cung cấp Cloud chỉ nhận anthropic hoặc openai.")
        ncc = "anthropic"
    value["nha_cung_cap"] = ncc
    value["model"] = str(value["model"] or "").strip() or NHA_CUNG_CAP_MAC_DINH[ncc]["model"]
    if not value["model"]:
        loi.append("Chưa chọn model Cloud cho nhà cung cấp này.")
    bien = str(value["bien_khoa_api"] or "").strip() or NHA_CUNG_CAP_MAC_DINH[ncc]["bien_khoa"]
    if not _TEN_BIEN_KHOA.fullmatch(bien):
        loi.append("Tên biến môi trường giữ khóa API phải có dạng TEN_API_KEY.")
        bien = NHA_CUNG_CAP_MAC_DINH[ncc]["bien_khoa"]
    value["bien_khoa_api"] = bien
    try:
        value["mask_url"] = mask_base_url(str(value["mask_url"] or ""))
    except ValueError as exc:
        loi.append(str(exc))
    value["mask_tep_khoa"] = str(value["mask_tep_khoa"] or "").strip()
    for key, low, high in (("mask_timeout_giay", 1, 120), ("cloud_timeout_giay", 5, 600), ("max_tokens", 256, 64000)):
        try:
            value[key] = max(low, min(high, int(value[key])))
        except (TypeError, ValueError):
            value[key] = CAI_DAT_MAC_DINH[key]
    gia = {model: dict(price) for model, price in BANG_GIA_USD_MAC_DINH.items()}
    if isinstance(value["bang_gia"], dict):
        for model, price in value["bang_gia"].items():
            try:
                vao, ra = float(price["vao"]), float(price["ra"])
            except (TypeError, ValueError, KeyError):
                continue
            if vao >= 0 and ra >= 0:
                gia[str(model)] = {"vao": vao, "ra": ra}
    value["bang_gia"] = gia
    try:
        value["kiem_xac_suat"] = cai_dat_kiem_xac_suat(value["kiem_xac_suat"])
    except (ValueError, TypeError):
        loi.append("Cài đặt kiểm xác suất không hợp lệ; cần kiểm tỷ lệ, cửa sổ và bậc giảm.")
        value["kiem_xac_suat"] = cai_dat_kiem_xac_suat({})
    value["loi"] = " ".join(loi)
    return value


def mask_base_url(url: str) -> str:
    """Mask v2 chế độ API chỉ nhận Host ``127.0.0.1``: chỉ cho ``http://127.0.0.1:<cổng>``."""
    shape = "Địa chỉ Mask file v2 phải là http://127.0.0.1:<cổng> (Mask chỉ nhận máy này)."
    try:
        if any(c.isspace() or ord(c) < 32 for c in url):
            raise ValueError
        parsed = urlparse(url)
        port = parsed.port
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not port or parsed.username is not None
                or parsed.password is not None or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.params or parsed.netloc != f"127.0.0.1:{port}"):
            raise ValueError
    except ValueError:
        raise ValueError(shape) from None
    return f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------------------------------------------------------
# 3. Yêu cầu, kết quả, nhật ký
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class YeuCauAI:
    """Một yêu cầu gửi cổng AI.

    - ``van_ban``: dữ liệu cần đọc (trường đã bóc; KHÔNG gửi XML hóa đơn thô). Trích dẫn được kiểm trên văn bản này.
    - ``chi_dan``: việc cần làm (không đưa dữ liệu chứng từ vào đây). Ra Cloud thì cả chỉ dẫn lẫn văn bản đều qua Mask.
    - ``truong``: tên các trường cần điền (rỗng = nhận mọi trường AI trả).
    - ``dinh_danh_da_biet``: định danh đã biết để Mask che chắc chắn — chuỗi, ``(giá trị, nhóm)`` hoặc
      ``{"gia_tri", "nhom"}``; nhóm theo Mask v2 (CONG_TY, CA_NHAN, MA_SO_THUE, TAI_KHOAN, GIAY_TO, HOP_DONG,
      DIA_CHI, DU_AN, EMAIL, DIEN_THOAI). Chỉ đưa định danh, không đưa số tiền/ngày (không che số tiền, ngày).
    """
    loai_viec: str
    van_ban: str
    chi_dan: str
    truong: tuple[str, ...] = ()
    dinh_danh_da_biet: tuple = ()
    phap_nhan_id: str | None = None
    viec_id: str | None = None
    de_xuat_id: str | None = None


@dataclass(frozen=True)
class TruongAI:
    ten: str
    gia_tri: str
    trich_dan: str
    nguon: str                       # LOCAL | CLOUD
    gia_tri_local: str | None = None  # Cloud ghi đè một giá trị Local khác → giữ để người duyệt so


@dataclass(frozen=True)
class KetQuaAI:
    loai_viec: str
    muc: str                          # VANG (có đề xuất, người duyệt) | DO (chưa có kết quả dùng được)
    truong: dict                      # tên → TruongAI (chỉ trường có trích dẫn nguyên văn hợp lệ)
    duong: str                        # LOCAL | CLOUD | LOCAL+CLOUD | KHONG
    thong_bao: str                    # tiếng Việt cho người dùng
    ly_do: tuple[str, ...] = ()       # mã lý do (chuyển Cloud, không gửi, loại trường)
    truong_bi_loai: tuple[str, ...] = ()
    ma_yeu_cau: str = ""

    @property
    def co_ket_qua(self) -> bool:
        return bool(self.truong)


@dataclass(frozen=True)
class BanGhiCongAI:
    """Một bản ghi nhật ký cho MỘT đường (Local hoặc Cloud) của một yêu cầu. Không có văn bản nào trong bản ghi.

    Ánh xạ sang ``nhat_ky.cong_ai_goi`` (AI-2b; "mới" = cột cần thêm bằng migration):

    ======================  ==========================================================
    trường                  cột
    ======================  ==========================================================
    ma_yeu_cau              (mới) ma_yeu_cau text — nối các bản ghi của một yêu cầu
    luc                     luc
    loai_viec               loai_viec
    duong                   cloud = (duong = 'CLOUD'); (mới) duong text
    nha_cung_cap, model     nha_cung_cap, model ('' khi chưa gọi model)
    da_gui                  (mới) da_gui boolean — đã gửi tới model hay chưa
    so_ky_tu_gui/nhan       (mới) integer
    token_vao, token_ra     token_vao, token_ra
    thoi_gian_ms            thoi_gian_ms
    chi_phi_uoc_usd         chi_phi_uoc (USD)
    ma_luot_mask            (mới) text
    ly_do_chuyen_cloud      (mới) text[] — vì sao cần Cloud (chỉ dòng CLOUD)
    ly_do_khong_gui         (mới) text — mã khi không gửi được
    ket_qua                 (mới) text: DAT | KHONG_CHAC | KHONG_DUNG_DUOC | LOI | KHONG_GUI
    ly_do                   (mới) text[] — mã đánh giá câu trả lời
    trich_dan_hop_le        trich_dan_hop_le
    so_truong_bi_loai       (mới) integer
    ly_do (AI-4a)           mã KIEM_LOCAL_DUNG/SAI + SO_TRUONG_DUNG_n/SAI_n, không tên/giá trị trường
    loi                     loi (mã, không văn bản)
    phap_nhan_id, viec_id,  phap_nhan_id, viec_id, de_xuat_id
    de_xuat_id
    —                       dau_vao_mask_hash, ket_qua_tom_tat: để NULL (không ghi văn bản hay băm văn bản)
    ======================  ==========================================================
    """
    ma_yeu_cau: str
    luc: str
    loai_viec: str
    duong: str
    nha_cung_cap: str
    model: str
    da_gui: bool
    so_ky_tu_gui: int = 0
    so_ky_tu_nhan: int = 0
    token_vao: int | None = None
    token_ra: int | None = None
    thoi_gian_ms: int = 0
    chi_phi_uoc_usd: float | None = None
    ma_luot_mask: str | None = None
    ly_do_chuyen_cloud: tuple[str, ...] = ()
    ly_do_khong_gui: str | None = None
    ket_qua: str = ""
    ly_do: tuple[str, ...] = ()
    trich_dan_hop_le: bool | None = None
    so_truong_bi_loai: int = 0
    loi: str | None = None
    phap_nhan_id: str | None = None
    viec_id: str | None = None
    de_xuat_id: str | None = None

    def thanh_dict(self) -> dict:
        return asdict(self)


class BoGhiNhatKy(Protocol):
    """Giao diện ghi nhật ký cổng AI. AI-2b: bộ ghi PostgreSQL ``nhat_ky.cong_ai_goi`` (chỉ ghi thêm)."""

    def ghi(self, ban_ghi: BanGhiCongAI) -> None: ...

    def thong_ke(self, cua_so: int) -> dict[str, dict]: ...


def _thong_ke_rong() -> dict:
    return dict(so_luot=0, so_kiem=0, so_kiem_cua_so=0, so_dung_cua_so=0)


class BoGhiBoNho:
    """Bộ ghi trong bộ nhớ (test, chạy thử)."""

    def __init__(self) -> None:
        self.ban_ghi: list[BanGhiCongAI] = []

    def ghi(self, ban_ghi: BanGhiCongAI) -> None:
        self.ban_ghi.append(ban_ghi)

    def thong_ke(self, cua_so: int) -> dict[str, dict]:
        """Chỉ đọc; cùng cách tính với bộ PostgreSQL, chỉ chấm lượt Cloud kiểm đạt chuẩn."""
        out, kiem = {}, {}
        for i, b in enumerate(self.ban_ghi):
            tk = out.setdefault(b.loai_viec, _thong_ke_rong())
            if b.duong == DUONG_LOCAL:
                tk["so_luot"] += 1
            if (b.duong == DUONG_CLOUD and b.da_gui and b.ket_qua == "DAT"
                    and "KIEM_XAC_SUAT" in b.ly_do_chuyen_cloud
                    and ((LOCAL_DUNG in b.ly_do) != (LOCAL_SAI in b.ly_do))):
                kiem.setdefault(b.loai_viec, []).append((b.luc, i, LOCAL_DUNG in b.ly_do))
        for ma, rows in kiem.items():
            gan_nhat = sorted(rows, reverse=True)[:cua_so]
            out[ma].update(so_kiem=len(rows), so_kiem_cua_so=len(gan_nhat),
                           so_dung_cua_so=sum(r[2] for r in gan_nhat))
        return out


class BoGhiPostgres:
    """Ghi metadata vào ``nhat_ky.cong_ai_goi`` (M0034), không giữ DSN/khóa.

    ``ket_noi`` là factory context manager cấp kết nối RIÊNG cho nhật ký, ví dụ
    ``lambda: psycopg.connect(dsn)`` hoặc ``pool.connection``. Không truyền kết nối
    đang dùng cho giao dịch nghiệp vụ. Mỗi dòng có giao dịch riêng, kể cả kết nối
    autocommit; lỗi INSERT/commit/kết nối chỉ log tên loại lỗi, không làm mất kết quả AI.
    """

    def __init__(self, ket_noi: Callable):
        self._ket_noi = ket_noi

    def thong_ke(self, cua_so: int) -> dict[str, dict]:
        """Một SELECT, cùng snapshot; chỉ metadata M0034, không cập nhật nhật ký.

        Lỗi đọc được chuyển lên cổng: không có số đo thì không tự giảm tỷ lệ kiểm.
        """
        with self._ket_noi() as conn:
            with conn.cursor() as cur:
                cur.execute("""WITH luot AS (
                    SELECT loai_viec, count(*) AS so_luot
                    FROM nhat_ky.cong_ai_goi WHERE duong = 'LOCAL' GROUP BY loai_viec
                ), kiem AS (
                    SELECT loai_viec, %s = ANY(ly_do) AS dung,
                           row_number() OVER (PARTITION BY loai_viec ORDER BY luc DESC, id DESC) AS stt
                    FROM nhat_ky.cong_ai_goi
                    WHERE duong = 'CLOUD' AND da_gui AND ket_qua = 'DAT'
                      AND 'KIEM_XAC_SUAT' = ANY(ly_do_chuyen_cloud)
                      AND ((%s = ANY(ly_do)) <> (%s = ANY(ly_do)))
                ), tong AS (
                    SELECT loai_viec, count(*) AS so_kiem,
                           count(*) FILTER (WHERE stt <= %s) AS so_kiem_cua_so,
                           count(*) FILTER (WHERE stt <= %s AND dung) AS so_dung_cua_so
                    FROM kiem GROUP BY loai_viec
                ) SELECT loai_viec, coalesce(so_luot, 0), coalesce(so_kiem, 0),
                         coalesce(so_kiem_cua_so, 0), coalesce(so_dung_cua_so, 0)
                  FROM luot FULL JOIN tong USING (loai_viec)""",
                            (LOCAL_DUNG, LOCAL_DUNG, LOCAL_SAI, cua_so, cua_so))
                rows = cur.fetchall()
        return {ma: dict(so_luot=luot, so_kiem=kiem, so_kiem_cua_so=n, so_dung_cua_so=dung)
                for ma, luot, kiem, n, dung in rows}

    def ghi(self, ban_ghi: BanGhiCongAI) -> None:
        try:
            with self._ket_noi() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO nhat_ky.cong_ai_goi (
                                ma_yeu_cau, luc, loai_viec, duong, cloud, nha_cung_cap, model,
                                da_gui, so_ky_tu_gui, so_ky_tu_nhan, token_vao, token_ra,
                                thoi_gian_ms, chi_phi_uoc, ma_luot_mask, ly_do_chuyen_cloud,
                                ly_do_khong_gui, ket_qua, ly_do, trich_dan_hop_le,
                                so_truong_bi_loai, loi, phap_nhan_id, viec_id, de_xuat_id,
                                dau_vao_mask_hash, ket_qua_tom_tat
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL
                            )""",
                            (ban_ghi.ma_yeu_cau, ban_ghi.luc, ban_ghi.loai_viec, ban_ghi.duong,
                             ban_ghi.duong == DUONG_CLOUD, ban_ghi.nha_cung_cap, ban_ghi.model,
                             ban_ghi.da_gui, ban_ghi.so_ky_tu_gui, ban_ghi.so_ky_tu_nhan,
                             ban_ghi.token_vao, ban_ghi.token_ra, ban_ghi.thoi_gian_ms,
                             ban_ghi.chi_phi_uoc_usd, ban_ghi.ma_luot_mask, list(ban_ghi.ly_do_chuyen_cloud),
                             ban_ghi.ly_do_khong_gui, ban_ghi.ket_qua, list(ban_ghi.ly_do),
                             ban_ghi.trich_dan_hop_le, ban_ghi.so_truong_bi_loai, ban_ghi.loi,
                             ban_ghi.phap_nhan_id, ban_ghi.viec_id, ban_ghi.de_xuat_id),
                        )
        except Exception as exc:  # noqa: BLE001 — không log thông báo/traceback có thể chứa dữ liệu hoặc DSN
            _LOG.error("Không ghi được nhật ký cổng AI (%s).", type(exc).__name__)


# ---------------------------------------------------------------------------------------------------------------
# 4. Thông báo tiếng Việt theo mã lý do
# ---------------------------------------------------------------------------------------------------------------
THONG_BAO = {
    "LOCAL_TAT": "chưa bật hoặc cài đặt Local AI chưa hợp lệ",
    "LOCAL_KHONG_CHAY": "không kết nối được máy AI",
    "LOCAL_LOI": "máy AI từ chối trả lời hoặc model chưa đúng",
    "PHAN_HOI_KHONG_HOP_LE": "câu trả lời của AI không đúng định dạng JSON yêu cầu",
    "THIEU_TRICH_DAN": "có trường AI điền mà không kèm trích dẫn",
    "TRICH_DAN_SAI": "có trích dẫn không khớp nguyên văn văn bản gốc",
    "GIA_TRI_NGOAI_TRICH_DAN": "có giá trị không nằm trong đoạn trích dẫn",
    "KHONG_QUA_KIEM_PYTHON": "có trường không qua kiểm tra của Python",
    "THIEU_TRUONG": "AI chưa điền đủ các trường cần",
    "DUOI_NGUONG": "độ tin cậy dưới ngưỡng của loại việc",
    "KHONG_CO_TRUONG": "AI không điền được trường nào hợp lệ",
    "KIEM_XAC_SUAT": "lấy mẫu kiểm xác suất",
    "CLOUD_TAT": "đường Cloud đang tắt (mặc định tới khi mở ở AI-4)",
    "LOAI_VIEC_KHONG_DUNG_CLOUD": "loại việc này chỉ dùng Local AI",
    "CAI_DAT_CLOUD_LOI": "cài đặt Cloud chưa hợp lệ",
    "CHUA_CO_KHOA_API": "chưa có khóa API của nhà cung cấp Cloud",
    "CHUA_CO_KHOA_MASK": "chưa đọc được tệp khóa của Mask file v2",
    "XML_HOA_DON_THO": "không gửi XML hóa đơn thô ra Cloud, hãy gửi các trường đã bóc",
    "QUA_NHIEU_DINH_DANH": "quá 500 định danh đã biết cho một lượt che",
    "MASK_KHONG_CHAY": "Mask file v2 không chạy hoặc không trả lời",
    "MASK_DANH_MUC_KHOA": "danh mục của Mask file v2 chưa mở cho phần mềm khác",
    "MASK_DANH_MUC_CHUA_CO": "Mask file v2 chưa có danh mục bí danh",
    "MASK_CON_SOT": "Mask báo còn sót định danh sau khi che",
    "MASK_KHONG_CHO_GUI": "Mask không cho gửi lượt này",
    "MASK_PHAN_HOI_LOI": "Mask trả dữ liệu không hợp lệ",
    "MASK_API_CHUA_BAT": "chế độ API của Mask file v2 chưa bật",
    "MASK_SAI_KHOA": "khóa API của Mask không đúng",
    "CON_SOT_DINH_DANH": "bản đã che vẫn còn định danh đã biết (cổng tự kiểm)",
    "CLOUD_KHONG_KET_NOI": "không kết nối được nhà cung cấp Cloud",
    "CLOUD_TU_CHOI": "nhà cung cấp Cloud từ chối trả lời",
    "CLOUD_LOI": "nhà cung cấp Cloud báo lỗi",
    "MASK_MO_CHE_LOI": "không mở che được kết quả Cloud nên bỏ kết quả Cloud",
}


def mo_ta_ly_do(ma: str) -> str:
    if ma in THONG_BAO:
        return THONG_BAO[ma]
    if ma.startswith("MASK_"):
        return "Mask file v2 từ chối lượt che"
    if ma.startswith("CLOUD_"):
        return THONG_BAO["CLOUD_LOI"]
    return ma


# ---------------------------------------------------------------------------------------------------------------
# 5. HTTP dùng chung (không theo chuyển hướng; không ghi nội dung)
# ---------------------------------------------------------------------------------------------------------------
class _KhongChuyenHuong(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _mo(proxy_moi_truong: bool):
    handlers = [_KhongChuyenHuong()]
    if not proxy_moi_truong:
        handlers.insert(0, urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


class _KhongKetNoi(Exception):
    pass


def _goi_json(opener, url: str, *, headers: dict, body: dict | None, timeout: float,
              gioi_han: int = 30_000_000) -> tuple[int, object]:
    """(mã HTTP, JSON hoặc None). Lỗi kết nối → ``_KhongKetNoi`` (không kèm chi tiết, không kèm header)."""
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="GET" if body is None else "POST")
    try:
        with opener.open(request, timeout=timeout) as response:
            status, raw = response.status, response.read(gioi_han + 1)
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            raw = exc.read(1_000_001)
        except Exception:  # noqa: BLE001 - chỉ cần mã lỗi
            raw = b""
        finally:
            exc.close()
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError):
        raise _KhongKetNoi() from None
    if len(raw) > gioi_han:
        return status, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        return status, None


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


# ---------------------------------------------------------------------------------------------------------------
# 6. Mask file v2 (chế độ API)
# ---------------------------------------------------------------------------------------------------------------
class MaskKhongGui(Exception):
    """Lượt này không được gửi Cloud. ``ma`` = mã lý do (không chứa văn bản)."""

    def __init__(self, ma: str):
        super().__init__(ma)
        self.ma = ma


_KHOA_MASK = re.compile(r"[A-Za-z0-9_-]{32,256}")
_MA_LOI_MASK = re.compile(r"[a-z0-9_]{1,40}")


def doc_khoa_mask(tep: str) -> str | None:
    """Đọc khóa Bearer của Mask từ tệp; None nếu không có/không hợp lệ. Không in, không log."""
    if not tep:
        return None
    try:
        khoa = Path(tep).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError, ValueError):
        return None
    return khoa if _KHOA_MASK.fullmatch(khoa) else None


@dataclass(frozen=True)
class LuotChe:
    ma_luot: str
    van_ban_da_che: str


class MaskV2:
    """Khách của chế độ API Mask file v2 (README 2.7, CHANGELOG 2.7.0/2.7.1). Chỉ ``http://127.0.0.1:<cổng>``."""

    def __init__(self, url: str, tep_khoa: str, *, timeout: float = 30):
        self.base = mask_base_url(url)
        self.tep_khoa = tep_khoa
        self.timeout = timeout
        self._opener = _mo(proxy_moi_truong=False)

    def co_khoa(self) -> bool:
        return doc_khoa_mask(self.tep_khoa) is not None

    def _goi(self, duong_dan: str, body: dict | None) -> dict:
        khoa = doc_khoa_mask(self.tep_khoa)
        if khoa is None:
            raise MaskKhongGui("CHUA_CO_KHOA_MASK")
        headers = {"Authorization": f"Bearer {khoa}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        try:
            status, data = _goi_json(self._opener, self.base + duong_dan, headers=headers, body=body,
                                     timeout=self.timeout)
        except _KhongKetNoi:
            raise MaskKhongGui("MASK_KHONG_CHAY") from None
        finally:
            del khoa, headers
        if status != 200:
            ma = data.get("ma_loi") if isinstance(data, dict) else None
            if status == 401:
                raise MaskKhongGui("MASK_SAI_KHOA")
            if isinstance(ma, str) and _MA_LOI_MASK.fullmatch(ma):
                raise MaskKhongGui("MASK_" + ma.upper())
            raise MaskKhongGui(f"MASK_HTTP_{int(status)}")
        if not isinstance(data, dict):
            raise MaskKhongGui("MASK_PHAN_HOI_LOI")
        return data

    def trang_thai(self) -> dict:
        return self._goi("/api/v1/trang-thai", None)

    def che(self, van_ban: str, dinh_danh: list) -> LuotChe:
        """Che một lượt; ném ``MaskKhongGui`` khi KHÔNG được gửi. Kiểm đủ điều kiện gửi (TL 48 §1.3)."""
        trang_thai = self.trang_thai()
        if trang_thai.get("danh_muc") != "da_mo":
            raise MaskKhongGui("MASK_DANH_MUC_CHUA_CO" if trang_thai.get("danh_muc") == "chua_co"
                               else "MASK_DANH_MUC_KHOA")
        data = self._goi("/api/v1/che", {"van_ban": van_ban, "dinh_danh_da_biet": dinh_danh})
        if data.get("gui_duoc") is not True:
            raise MaskKhongGui("MASK_KHONG_CHO_GUI")
        con_sot = data.get("con_sot")
        if not isinstance(con_sot, list) or con_sot:
            raise MaskKhongGui("MASK_CON_SOT")
        if data.get("danh_muc") != "da_mo":
            raise MaskKhongGui("MASK_DANH_MUC_KHOA")
        ma_luot, da_che = data.get("ma_luot"), data.get("van_ban_da_che")
        if not isinstance(ma_luot, str) or not ma_luot or len(ma_luot) > 64 or not isinstance(da_che, str) \
                or not da_che.strip():
            raise MaskKhongGui("MASK_PHAN_HOI_LOI")
        return LuotChe(ma_luot, da_che)

    def mo_che(self, ma_luot: str, van_ban: str, *, ket_thuc_luot: bool = True) -> str:
        data = self._goi("/api/v1/mo-che", {"ma_luot": ma_luot, "van_ban": van_ban, "ket_thuc_luot": ket_thuc_luot})
        text = data.get("van_ban")
        if not isinstance(text, str):
            raise MaskKhongGui("MASK_PHAN_HOI_LOI")
        return text

    def ket_thuc(self, ma_luot: str) -> None:
        """Dọn bảng ánh xạ của lượt trong RAM của Mask (cố gắng; lỗi bỏ qua)."""
        try:
            self.mo_che(ma_luot, "", ket_thuc_luot=True)
        except Exception:  # noqa: BLE001 - lượt tự hết hạn sau 30 phút trong RAM của Mask
            pass


# ---------------------------------------------------------------------------------------------------------------
# 7. Nhà cung cấp Cloud — NGOẠI LỆ DUY NHẤT được gọi api.anthropic.com / api.openai.com (xem docstring module)
# ---------------------------------------------------------------------------------------------------------------
class CloudLoi(Exception):
    """Lỗi nhà cung cấp Cloud; ``ma`` là mã, không chứa khóa hay văn bản."""

    def __init__(self, ma: str):
        super().__init__(ma)
        self.ma = ma


@dataclass(frozen=True)
class PhanHoiCloud:
    van_ban: str
    model: str
    token_vao: int | None
    token_ra: int | None


class NhaCungCapCloud(Protocol):
    ten: str

    def tra_loi(self, he_thong: str, noi_dung: str, *, model: str, khoa: str, max_tokens: int,
                timeout: float) -> PhanHoiCloud: ...


class NhaCungCapAnthropic:
    """Messages API qua HTTP thô (dự án chỉ phụ thuộc openpyxl, không thêm SDK)."""
    ten = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"
    PHIEN_BAN_API = "2026-10-21"   # không gửi temperature/top_p/top_k (bị từ chối từ phiên bản này)
    BETA_FALLBACK = "server-side-fallback-2026-07-01"
    MODEL_CO_FALLBACK = frozenset({"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"})

    def __init__(self, url: str = URL, *, proxy_moi_truong: bool = True, fallback_khi_tu_choi: bool = True):
        self.url = url
        self.fallback = fallback_khi_tu_choi
        self._opener = _mo(proxy_moi_truong)

    def tra_loi(self, he_thong, noi_dung, *, model, khoa, max_tokens, timeout) -> PhanHoiCloud:
        body = {"model": model, "max_tokens": max_tokens, "system": he_thong,
                "messages": [{"role": "user", "content": noi_dung}]}
        headers = {"x-api-key": khoa, "anthropic-version": self.PHIEN_BAN_API, "content-type": "application/json"}
        if self.fallback and model in self.MODEL_CO_FALLBACK:
            body["fallbacks"] = "default"
            headers["anthropic-beta"] = self.BETA_FALLBACK
        try:
            status, data = _goi_json(self._opener, self.url, headers=headers, body=body, timeout=timeout)
        except _KhongKetNoi:
            raise CloudLoi("CLOUD_KHONG_KET_NOI") from None
        finally:
            del khoa, headers
        if status != 200 or not isinstance(data, dict):
            raise CloudLoi(f"CLOUD_HTTP_{int(status)}")
        if data.get("stop_reason") == "refusal":
            raise CloudLoi("CLOUD_TU_CHOI")
        blocks = data.get("content") if isinstance(data.get("content"), list) else []
        text = "".join(str(b.get("text") or "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return PhanHoiCloud(text, str(data.get("model") or model), _int(usage.get("input_tokens")),
                            _int(usage.get("output_tokens")))


class NhaCungCapOpenAI:
    ten = "openai"
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, url: str = URL, *, proxy_moi_truong: bool = True):
        self.url = url
        self._opener = _mo(proxy_moi_truong)

    def tra_loi(self, he_thong, noi_dung, *, model, khoa, max_tokens, timeout) -> PhanHoiCloud:
        body = {"model": model, "messages": [{"role": "system", "content": he_thong},
                                             {"role": "user", "content": noi_dung}]}
        headers = {"Authorization": f"Bearer {khoa}", "Content-Type": "application/json"}
        try:
            status, data = _goi_json(self._opener, self.url, headers=headers, body=body, timeout=timeout)
        except _KhongKetNoi:
            raise CloudLoi("CLOUD_KHONG_KET_NOI") from None
        finally:
            del khoa, headers
        if status != 200 or not isinstance(data, dict):
            raise CloudLoi(f"CLOUD_HTTP_{int(status)}")
        try:
            text = str(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError):
            text = ""
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return PhanHoiCloud(text, str(data.get("model") or model), _int(usage.get("prompt_tokens")),
                            _int(usage.get("completion_tokens")))


def chi_phi_uoc_usd(bang_gia: dict, model: str, token_vao: int | None, token_ra: int | None) -> float | None:
    gia = bang_gia.get(model)
    if not gia or token_vao is None or token_ra is None:
        return None
    return round(token_vao * gia["vao"] / 1_000_000 + token_ra * gia["ra"] / 1_000_000, 6)


# ---------------------------------------------------------------------------------------------------------------
# 8. Kiểm câu trả lời: định dạng, trích dẫn nguyên văn, trường cần, ngưỡng
# ---------------------------------------------------------------------------------------------------------------
def _chuan(text: str) -> str:
    """NFC, bỏ ký tự điều khiển/định dạng (như ``normalize`` của Mask v2), gộp khoảng trắng."""
    text = unicodedata.normalize("NFC", text or "")
    text = "".join(c for c in text if c.isspace() or not unicodedata.category(c).startswith("C"))
    return " ".join(text.split())


def _bo_dau(text: str) -> str:
    text = unicodedata.normalize("NFD", _chuan(text).replace("Đ", "D").replace("đ", "d"))
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def doc_json_tra_loi(text: str) -> dict | None:
    """Lấy đối tượng JSON ``{"truong": [...], "do_tin_cay": …}`` trong câu trả lời (chấp nhận rào ```json)."""
    text = text or ""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("truong"), list):
        return None
    return data


@dataclass(frozen=True)
class DanhGia:
    truong: dict                 # tên → TruongAI hợp lệ
    bi_loai: dict                # tên → mã lý do
    ly_do: tuple[str, ...]
    do_tin_cay: float | None

    @property
    def chac(self) -> bool:
        return not self.ly_do

    @property
    def ket_qua(self) -> str:
        return "DAT" if self.chac else "KHONG_CHAC" if self.truong else "KHONG_DUNG_DUOC"

    @property
    def trich_dan_hop_le(self) -> bool | None:
        if not self.truong and not self.bi_loai:
            return None
        return not any(ma in ("THIEU_TRICH_DAN", "TRICH_DAN_SAI", "GIA_TRI_NGOAI_TRICH_DAN")
                       for ma in self.bi_loai.values())


KiemTraThem = Callable[[dict, str], Iterable[str]]


def danh_gia(data: dict | None, yeu_cau: YeuCauAI, loai: LoaiViec, nguon: str,
             kiem_tra: KiemTraThem | None = None) -> DanhGia:
    """Python kiểm câu trả lời (đã mở che) trên văn bản gốc ``yeu_cau.van_ban``.

    Trường hợp lệ khi: có giá trị, có trích dẫn, trích dẫn nằm NGUYÊN VĂN trong văn bản gốc (chỉ gộp khoảng trắng),
    giá trị nằm trong trích dẫn, và qua ``kiem_tra`` (trả về tên các trường không đạt) nếu có.
    """
    if data is None:
        return DanhGia({}, {}, ("PHAN_HOI_KHONG_HOP_LE",), None)
    goc = _chuan(yeu_cau.van_ban)
    tot, bi_loai = {}, {}
    can = set(yeu_cau.truong)
    for muc in data.get("truong") or []:
        if not isinstance(muc, dict):
            continue
        ten = str(muc.get("ten") or "").strip()
        if not ten or (can and ten not in can) or ten in tot:
            continue
        gia_tri, trich = _chuan(str(muc.get("gia_tri") or "")), _chuan(str(muc.get("trich_dan") or ""))
        if not gia_tri:
            continue
        if not trich:
            bi_loai[ten] = "THIEU_TRICH_DAN"
        elif trich not in goc:
            bi_loai[ten] = "TRICH_DAN_SAI"
        elif gia_tri.casefold() not in trich.casefold():
            bi_loai[ten] = "GIA_TRI_NGOAI_TRICH_DAN"
        else:
            tot[ten] = TruongAI(ten, gia_tri, trich, nguon)
            bi_loai.pop(ten, None)
    if kiem_tra is not None and tot:
        try:
            khong_dat = {str(ten) for ten in kiem_tra(dict(tot), yeu_cau.van_ban)}
        except Exception:  # noqa: BLE001 - nguồn gợi ý không được làm hỏng đề xuất: coi như không đạt
            khong_dat = set(tot)
        for ten in khong_dat & set(tot):
            tot.pop(ten)
            bi_loai[ten] = "KHONG_QUA_KIEM_PYTHON"
    ly_do = list(dict.fromkeys(bi_loai.values()))
    if can and can - set(tot):
        ly_do.append("THIEU_TRUONG")
    try:
        tin_cay = float(data.get("do_tin_cay"))
        tin_cay = tin_cay if 0 <= tin_cay <= 1 else None
    except (TypeError, ValueError):
        tin_cay = None
    if loai.nguong_tin_cay > 0 and (tin_cay is None or tin_cay < loai.nguong_tin_cay):
        ly_do.append("DUOI_NGUONG")
    if not tot:
        ly_do.append("KHONG_CO_TRUONG")
    return DanhGia(tot, bi_loai, tuple(dict.fromkeys(ly_do)), tin_cay)


# ---------------------------------------------------------------------------------------------------------------
# 9. Chuẩn bị nội dung gửi
# ---------------------------------------------------------------------------------------------------------------
_CHI_SO = re.compile(r"[\d\s.,\-/]+")
_NHOM = re.compile(r"[A-Z][A-Z_]{1,19}")
_THE_XML = re.compile(r"</?[A-Za-z][\w.:-]*(?:\s[^<>]*)?>")
_TACH = "\n@@--TACH-CONG-AI--@@\n"
GIOI_HAN_DINH_DANH = 500


def chuan_dinh_danh(items) -> list:
    """Định danh đã biết → danh sách gửi ``/che``. Định danh dạng số chưa khai nhóm được khai ``GIAY_TO`` (MASK-2:
    định danh dạng số phải khai ``nhom`` để Mask che cả cách viết khác và không nhầm với số tiền)."""
    out, seen = [], set()
    for item in items or ():
        if isinstance(item, str):
            gia_tri, nhom = item, ""
        elif isinstance(item, dict):
            gia_tri, nhom = item.get("gia_tri"), item.get("nhom")
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            gia_tri, nhom = item
        else:
            raise ValueError("Định danh đã biết phải là chuỗi, (giá trị, nhóm) hoặc {gia_tri, nhom}.")
        gia_tri, nhom = " ".join(str(gia_tri or "").split()), str(nhom or "").strip().upper()
        if nhom and not _NHOM.fullmatch(nhom):
            raise ValueError("Nhóm định danh phải là chữ in hoa kiểu CONG_TY, TAI_KHOAN (tối đa 20 ký tự).")
        if not 2 <= len(gia_tri) <= 300:
            continue
        if nhom in ("", "KHAC") and _CHI_SO.fullmatch(gia_tri) and sum(c.isdigit() for c in gia_tri) >= 6:
            nhom = "GIAY_TO"
        khoa = (gia_tri.casefold(), nhom)
        if khoa in seen:
            continue
        seen.add(khoa)
        out.append({"gia_tri": gia_tri, "nhom": nhom} if nhom else gia_tri)
    return out


def con_sot_dinh_danh(da_che: str, dinh_danh: list) -> bool:
    """Cổng tự kiểm (thêm, độc lập với Mask): còn định danh đã khai trong bản đã che → True."""
    thuong, khong_dau = _chuan(da_che).casefold(), _bo_dau(da_che)
    for item in dinh_danh:
        gia_tri = item["gia_tri"] if isinstance(item, dict) else item
        if _chuan(gia_tri).casefold() in thuong or _bo_dau(gia_tri) in khong_dau:
            return True
        so = re.sub(r"\D", "", gia_tri)
        if len(so) >= 6 and _CHI_SO.fullmatch(gia_tri):
            mau = r"(?<![0-9])" + r"[\s.,\-/]{0,3}".join(so) + r"(?![0-9])"
            if re.search(mau, da_che):
                return True
    return False


def giong_xml_tho(text: str) -> bool:
    return bool(re.search(r"<\?xml\b", text, re.I)) or len(_THE_XML.findall(text)) >= 6


def noi_dung_nguoi_dung(yeu_cau: YeuCauAI) -> str:
    """Phần do bên gọi cung cấp (chỉ dẫn + danh sách trường + văn bản) — ra Cloud thì toàn bộ phần này qua Mask."""
    phan = [yeu_cau.chi_dan.strip()]
    if yeu_cau.truong:
        phan.append("Các trường cần điền: " + ", ".join(yeu_cau.truong))
    phan.append("Văn bản:\n" + yeu_cau.van_ban)
    return "\n\n".join(p for p in phan if p)


def _luc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


# ---------------------------------------------------------------------------------------------------------------
# 10. Cổng
# ---------------------------------------------------------------------------------------------------------------
class CongAI:
    """Cổng AI dùng chung. ``goi()`` không ném lỗi vận hành (mạng, Mask, Cloud): luôn trả ``KetQuaAI``.

    - ``settings``: nhóm cài đặt như ``source-settings.json`` → ``settings`` (``local_ai``, ``cong_ai``).
    - ``bo_ghi``: bắt buộc — mọi lượt đều được ghi (AI-2b: bộ ghi PostgreSQL).
    - ``kiem_xac_suat``: móc chọn mẫu thay thế cho test/bên gọi cũ; luôn chịu công tắc Cloud và bảng loại việc.
    - ``nha_cung_cap``, ``mask``, ``local_transport``, ``moi_truong``: thay được khi test (máy chủ giả, không mạng).
    """

    def __init__(self, settings: dict | None, *, bo_ghi: BoGhiNhatKy,
                 nha_cung_cap: NhaCungCapCloud | None = None, mask: MaskV2 | None = None,
                 local_transport=None, moi_truong: Mapping[str, str] | None = None,
                 kiem_xac_suat: Callable[[LoaiViec], bool] | None = None):
        settings = settings if isinstance(settings, dict) else {}
        self.local_ai = settings.get("local_ai") if isinstance(settings.get("local_ai"), dict) else {}
        self.cai_dat = cong_ai_settings(settings)
        self.bo_ghi = bo_ghi
        self._nha_cung_cap = nha_cung_cap
        self._mask = mask
        self._local_transport = local_transport
        self._moi_truong = moi_truong
        self._kiem_xac_suat = kiem_xac_suat

    def _doc_thong_ke(self) -> dict | None:
        try:
            return self.bo_ghi.thong_ke(self.cai_dat["kiem_xac_suat"]["cua_so"])
        except Exception as exc:  # noqa: BLE001 - không có số đo: giữ tỷ lệ ban đầu, không giảm
            _LOG.error("Không đọc được thống kê cổng AI (%s).", type(exc).__name__)
            return None

    def thong_ke(self) -> list[dict]:
        """Bảng chỉ đọc, không mạng: số lượt Local, số kiểm ĐÃ CHẤM, % khớp Cloud trên N kiểm gần nhất.

        Đúng = khớp toàn bộ giá trị theo trường với Cloud đã qua Python; chưa phải đáp án chuẩn/người duyệt.
        ``ty_le_kiem_hien_hanh`` là 0..1; ``phan_tram_chinh_xac`` là 0..100 hoặc None nếu chưa đo.
        Cloud tắt/loại việc cấm Cloud → tỷ lệ hiện hành 0. Không đọc khóa hay gọi kiểm trạng thái Mask.
        """
        rows = self._doc_thong_ke()
        cfg = self.cai_dat["kiem_xac_suat"]
        out = []
        for ma, loai in LOAI_VIEC.items():
            tk = (rows.get(ma) or _thong_ke_rong()) if rows is not None else None
            n = tk["so_kiem_cua_so"] if tk else 0
            rate = ty_le_kiem_hien_hanh(cfg, ma, tk)
            if not self.cai_dat["cloud_bat"] or self.cai_dat["loi"] or not loai.duoc_dung_cloud:
                rate = 0.0
            out.append({"loai_viec": ma, **(tk or {k: None for k in _thong_ke_rong()}),
                        "cua_so": cfg["cua_so"], "thong_ke_san_sang": rows is not None,
                        "phan_tram_chinh_xac": 100 * tk["so_dung_cua_so"] / n if n else None,
                        "canh_bao": "LOCAL_DUOI_NGUONG_CHINH_XAC"
                        if n and tk["so_dung_cua_so"] / n < cfg["nguong_tang_lai"] else None,
                        "ty_le_kiem_hien_hanh": rate})
        return out

    def _chon_kiem(self, loai: LoaiViec) -> bool:
        if not self.cai_dat["cloud_bat"] or self.cai_dat["loi"] or not loai.duoc_dung_cloud:
            return False
        if self._kiem_xac_suat is not None:
            return bool(self._kiem_xac_suat(loai))
        cfg = self.cai_dat["kiem_xac_suat"]
        # Không đọc nhật ký nếu loại việc này chưa cho phép lấy mẫu.
        if ty_le_kiem_hien_hanh(cfg, loai.ma, None) == 0:
            return False
        rows = self._doc_thong_ke()
        rate = ty_le_kiem_hien_hanh(cfg, loai.ma, rows.get(loai.ma) if rows is not None else None)
        return random.random() < rate

    # ---- trạng thái (không gọi mạng trừ khi kiem_mask) -----------------------------------------------------
    def _env(self) -> Mapping[str, str]:
        return self._moi_truong if self._moi_truong is not None else os.environ

    def _mask_client(self) -> MaskV2:
        if self._mask is None:
            self._mask = MaskV2(self.cai_dat["mask_url"], self.cai_dat["mask_tep_khoa"],
                                timeout=self.cai_dat["mask_timeout_giay"])
        return self._mask

    def _provider(self) -> NhaCungCapCloud:
        if self._nha_cung_cap is None:
            self._nha_cung_cap = (NhaCungCapAnthropic(fallback_khi_tu_choi=self.cai_dat["fallback_khi_tu_choi"])
                                  if self.cai_dat["nha_cung_cap"] == "anthropic" else NhaCungCapOpenAI())
        return self._nha_cung_cap

    def _ly_do_cloud_khong_dung(self) -> str | None:
        """Mã khi đường Cloud coi như tắt (không gọi mạng)."""
        if not self.cai_dat["cloud_bat"]:
            return "CLOUD_TAT"
        if self.cai_dat["loi"]:
            return "CAI_DAT_CLOUD_LOI"
        if not str(self._env().get(self.cai_dat["bien_khoa_api"]) or "").strip():
            return "CHUA_CO_KHOA_API"
        if self._mask is None and not doc_khoa_mask(self.cai_dat["mask_tep_khoa"]):
            return "CHUA_CO_KHOA_MASK"
        if self._mask is not None and not self._mask.co_khoa():
            return "CHUA_CO_KHOA_MASK"
        return None

    def trang_thai(self, *, kiem_mask: bool = False) -> dict:
        """Trạng thái tiếng Việt cho màn hình cài đặt. ``kiem_mask`` = hỏi thêm ``/api/v1/trang-thai`` của Mask."""
        local = ai_cuc_bo.local_ai_settings({"local_ai": self.local_ai})
        local_tb = ("Local AI đang bật." if local["enabled"]
                    else "Local AI chưa bật" + (f": {local['error']}" if local["error"] else "."))
        ma = self._ly_do_cloud_khong_dung()
        if ma is None and kiem_mask:
            try:
                st = self._mask_client().trang_thai()
                if st.get("danh_muc") != "da_mo":
                    ma = "MASK_DANH_MUC_CHUA_CO" if st.get("danh_muc") == "chua_co" else "MASK_DANH_MUC_KHOA"
            except MaskKhongGui as exc:
                ma = exc.ma
        if ma == "CLOUD_TAT":
            cloud_tb = "Đường Cloud đang tắt (mặc định); phần mềm chỉ dùng Local AI."
        elif ma == "CAI_DAT_CLOUD_LOI":
            cloud_tb = "Cài đặt Cloud chưa hợp lệ, coi như tắt Cloud: " + self.cai_dat["loi"]
        elif ma:
            cloud_tb = f"Coi như tắt Cloud: {mo_ta_ly_do(ma)}."
        else:
            cloud_tb = (f"Đường Cloud bật ({self.cai_dat['nha_cung_cap']}, {self.cai_dat['model']}); "
                        "chỉ gửi khi Mask file v2 che xong và không còn sót định danh.")
        return {"local": {"bat": bool(local["enabled"]), "thong_bao": local_tb},
                "cloud": {"dung_duoc": ma is None, "ma": ma, "thong_bao": cloud_tb}}

    # ---- ghi nhật ký --------------------------------------------------------------------------------------
    def _ghi(self, ban_ghi: BanGhiCongAI) -> None:
        try:
            self.bo_ghi.ghi(ban_ghi)
        except Exception as exc:  # noqa: BLE001 - lỗi ghi nhật ký không được làm mất kết quả đã trả tiền
            _LOG.error("Không ghi được nhật ký cổng AI (%s).", type(exc).__name__)

    # ---- đường Local --------------------------------------------------------------------------------------
    def _local(self, yc: YeuCauAI, loai: LoaiViec, ma_yc: str, prompt: str,
               kiem_tra: KiemTraThem | None) -> tuple[DanhGia | None, tuple[str, ...]]:
        cfg = ai_cuc_bo.local_ai_settings({"local_ai": self.local_ai})
        model = str(cfg.get("model") or "")
        base = dict(ma_yeu_cau=ma_yc, luc=_luc(), loai_viec=loai.ma, duong=DUONG_LOCAL, nha_cung_cap="local",
                    model=model, phap_nhan_id=yc.phap_nhan_id, viec_id=yc.viec_id, de_xuat_id=yc.de_xuat_id)
        if not cfg["enabled"]:
            self._ghi(BanGhiCongAI(**base, da_gui=False, ket_qua="KHONG_GUI", loi="LOCAL_TAT"))
            return None, ("LOCAL_TAT",)
        t0 = time.monotonic()
        try:
            answer = ai_cuc_bo.ask_local(self.local_ai, prompt, self._local_transport)
        except ai_cuc_bo.LocalAIUnavailable:
            self._ghi(BanGhiCongAI(**base, da_gui=False, ket_qua="LOI", loi="LOCAL_KHONG_CHAY",
                                   so_ky_tu_gui=0, thoi_gian_ms=int((time.monotonic() - t0) * 1000)))
            return None, ("LOCAL_KHONG_CHAY",)
        except Exception:  # noqa: BLE001 - model sai/máy AI từ chối: Local coi như không dùng được lượt này
            self._ghi(BanGhiCongAI(**base, da_gui=True, ket_qua="LOI", loi="LOCAL_LOI", so_ky_tu_gui=len(prompt),
                                   thoi_gian_ms=int((time.monotonic() - t0) * 1000)))
            return None, ("LOCAL_LOI",)
        ms = int((time.monotonic() - t0) * 1000)
        dg = danh_gia(doc_json_tra_loi(answer), yc, loai, DUONG_LOCAL, kiem_tra)
        self._ghi(BanGhiCongAI(**base, da_gui=True, so_ky_tu_gui=len(prompt), so_ky_tu_nhan=len(answer or ""),
                               thoi_gian_ms=ms, ket_qua=dg.ket_qua, ly_do=dg.ly_do,
                               trich_dan_hop_le=dg.trich_dan_hop_le, so_truong_bi_loai=len(dg.bi_loai)))
        return dg, dg.ly_do

    # ---- đường Cloud (chỉ qua Mask v2) ----------------------------------------------------------------------
    def _cloud(self, yc: YeuCauAI, loai: LoaiViec, ma_yc: str, ly_do_chuyen: tuple[str, ...],
               kiem_tra: KiemTraThem | None, local_kiem: DanhGia | None = None) -> tuple[DanhGia | None, str | None]:
        """(đánh giá kết quả Cloud hoặc None, mã lý do không gửi/không dùng được)."""
        base = dict(ma_yeu_cau=ma_yc, luc=_luc(), loai_viec=loai.ma, duong=DUONG_CLOUD,
                    nha_cung_cap=self.cai_dat["nha_cung_cap"], model=self.cai_dat["model"],
                    ly_do_chuyen_cloud=ly_do_chuyen, phap_nhan_id=yc.phap_nhan_id, viec_id=yc.viec_id,
                    de_xuat_id=yc.de_xuat_id)

        def khong_gui(ma: str, **extra) -> tuple[None, str]:
            self._ghi(BanGhiCongAI(**base, da_gui=False, ket_qua="KHONG_GUI", ly_do_khong_gui=ma, **extra))
            return None, ma

        if not self.cai_dat["cloud_bat"]:           # Công tắc tắt: không đọc khóa, không gọi Mask/Cloud
            return khong_gui("CLOUD_TAT")
        if not loai.duoc_dung_cloud:
            return khong_gui("LOAI_VIEC_KHONG_DUNG_CLOUD")
        ma = self._ly_do_cloud_khong_dung()
        if ma:
            return khong_gui(ma)
        if giong_xml_tho(yc.van_ban):
            return khong_gui("XML_HOA_DON_THO")
        dinh_danh = chuan_dinh_danh(yc.dinh_danh_da_biet)
        if len(dinh_danh) > GIOI_HAN_DINH_DANH:
            return khong_gui("QUA_NHIEU_DINH_DANH")
        mask = self._mask_client()
        t0 = time.monotonic()
        try:
            luot = mask.che(noi_dung_nguoi_dung(yc), dinh_danh)
        except Exception as exc:  # noqa: BLE001 - mọi lỗi khi che = không gửi
            ma = exc.ma if isinstance(exc, MaskKhongGui) else "MASK_PHAN_HOI_LOI"
            return khong_gui(ma, thoi_gian_ms=int((time.monotonic() - t0) * 1000))
        if con_sot_dinh_danh(luot.van_ban_da_che, dinh_danh):
            mask.ket_thuc(luot.ma_luot)
            return khong_gui("CON_SOT_DINH_DANH", ma_luot_mask=luot.ma_luot,
                             thoi_gian_ms=int((time.monotonic() - t0) * 1000))
        user = HUONG_DAN_DINH_DANG + "\n\n" + luot.van_ban_da_che
        so_gui = len(HE_THONG) + len(user)
        khoa = str(self._env().get(self.cai_dat["bien_khoa_api"]) or "").strip()
        try:
            phan_hoi = self._provider().tra_loi(HE_THONG, user, model=self.cai_dat["model"], khoa=khoa,
                                                max_tokens=self.cai_dat["max_tokens"],
                                                timeout=self.cai_dat["cloud_timeout_giay"])
        except Exception as exc:  # noqa: BLE001 - lỗi nhà cung cấp: bỏ lượt Cloud, không lộ chi tiết
            ma = exc.ma if isinstance(exc, CloudLoi) else "CLOUD_LOI"
            mask.ket_thuc(luot.ma_luot)
            self._ghi(BanGhiCongAI(**base, da_gui=True, so_ky_tu_gui=so_gui, ma_luot_mask=luot.ma_luot,
                                   ket_qua="LOI", loi=ma, thoi_gian_ms=int((time.monotonic() - t0) * 1000)))
            return None, ma
        finally:
            del khoa
        base.update(model=phan_hoi.model)
        chi_phi = chi_phi_uoc_usd(self.cai_dat["bang_gia"], phan_hoi.model, phan_hoi.token_vao, phan_hoi.token_ra)
        sent = dict(da_gui=True, so_ky_tu_gui=so_gui, so_ky_tu_nhan=len(phan_hoi.van_ban),
                    token_vao=phan_hoi.token_vao, token_ra=phan_hoi.token_ra, chi_phi_uoc_usd=chi_phi,
                    ma_luot_mask=luot.ma_luot)
        data = doc_json_tra_loi(phan_hoi.van_ban)
        try:
            data = self._mo_che_json(mask, luot.ma_luot, data)
        except Exception:  # noqa: BLE001 - không mở che được thì không dùng được kết quả Cloud
            self._ghi(BanGhiCongAI(**base, **sent, ket_qua="LOI", loi="MASK_MO_CHE_LOI",
                                   thoi_gian_ms=int((time.monotonic() - t0) * 1000)))
            return None, "MASK_MO_CHE_LOI"
        dg = danh_gia(data, yc, loai, DUONG_CLOUD, kiem_tra)
        diem = ()
        if local_kiem is not None and dg.chac:
            # So theo tên trường sau mở che, chuẩn khoảng trắng/hoa thường; không log tên/giá trị/trích dẫn.
            ten = set(local_kiem.truong) | set(dg.truong)
            dung = sum(1 for t in ten if t in local_kiem.truong and t in dg.truong
                       and _chuan(local_kiem.truong[t].gia_tri).casefold() == _chuan(dg.truong[t].gia_tri).casefold())
            sai = len(ten) - dung
            diem = (LOCAL_SAI if sai else LOCAL_DUNG, f"SO_TRUONG_DUNG_{dung}", f"SO_TRUONG_SAI_{sai}")
        self._ghi(BanGhiCongAI(**base, **sent, ket_qua=dg.ket_qua, ly_do=dg.ly_do + diem,
                               trich_dan_hop_le=dg.trich_dan_hop_le, so_truong_bi_loai=len(dg.bi_loai),
                               thoi_gian_ms=int((time.monotonic() - t0) * 1000)))
        return dg, None

    @staticmethod
    def _mo_che_json(mask: MaskV2, ma_luot: str, data: dict | None) -> dict | None:
        """Mở che từng chuỗi của JSON đã đọc (một lời gọi, kết thúc lượt) — không mở che chuỗi JSON thô, vì chữ
        gốc có thể chứa dấu nháy làm hỏng JSON."""
        if data is None:
            mask.ket_thuc(ma_luot)
            return None
        muc = [m for m in data.get("truong") or [] if isinstance(m, dict)]
        chuoi = [str(m.get(k) or "") for m in muc for k in ("ten", "gia_tri", "trich_dan")]
        if not chuoi:
            mask.ket_thuc(ma_luot)
            return {"truong": [], "do_tin_cay": data.get("do_tin_cay")}
        if any(_TACH.strip() in c for c in chuoi):
            mask.ket_thuc(ma_luot)
            raise MaskKhongGui("MASK_MO_CHE_LOI")
        mo = mask.mo_che(ma_luot, _TACH.join(chuoi), ket_thuc_luot=True).split(_TACH)
        if len(mo) != len(chuoi):
            raise MaskKhongGui("MASK_MO_CHE_LOI")
        it = iter(mo)
        return {"truong": [{"ten": next(it), "gia_tri": next(it), "trich_dan": next(it)} for _ in muc],
                "do_tin_cay": data.get("do_tin_cay")}

    # ---- lượt gọi -----------------------------------------------------------------------------------------
    def goi(self, yeu_cau: YeuCauAI, *, kiem_tra: KiemTraThem | None = None) -> KetQuaAI:
        """Một lượt: Local trước; Cloud (qua Mask) chỉ khi Local không chạy / không chắc / được chọn kiểm xác suất.

        ``kiem_tra(truong, van_ban_goc)`` (tùy chọn): kiểm thêm của Python, trả tên các trường KHÔNG đạt.
        """
        loai = loai_viec(yeu_cau.loai_viec)
        if not isinstance(yeu_cau.van_ban, str) or not yeu_cau.van_ban.strip():
            raise ValueError("Văn bản gửi cổng AI đang rỗng.")
        if not isinstance(yeu_cau.chi_dan, str) or not all(isinstance(t, str) and t for t in yeu_cau.truong):
            raise ValueError("Chỉ dẫn và tên trường gửi cổng AI phải là chuỗi.")
        chuan_dinh_danh(yeu_cau.dinh_danh_da_biet)  # kiểm hợp đồng ngay, kể cả khi Cloud tắt
        ma_yc = uuid.uuid4().hex
        prompt_local = HUONG_DAN_DINH_DANG + "\n\n" + noi_dung_nguoi_dung(yeu_cau)
        local, ly_do_local = self._local(yeu_cau, loai, ma_yc, prompt_local, kiem_tra)
        if local is not None and local.chac:
            if not self._chon_kiem(loai):
                return self._ket_qua(loai, ma_yc, local, None, (), None)
            ly_do_chuyen = ("KIEM_XAC_SUAT",)
        else:
            ly_do_chuyen = ly_do_local
        cloud, khong_dung = self._cloud(yeu_cau, loai, ma_yc, ly_do_chuyen, kiem_tra,
                                      local_kiem=local if ly_do_chuyen == ("KIEM_XAC_SUAT",) else None)
        return self._ket_qua(loai, ma_yc, local, cloud, ly_do_chuyen, khong_dung)

    @staticmethod
    def _ket_qua(loai: LoaiViec, ma_yc: str, local: DanhGia | None, cloud: DanhGia | None,
                 ly_do_chuyen: tuple[str, ...], khong_dung: str | None) -> KetQuaAI:
        truong = dict(local.truong) if local else {}
        if cloud and cloud.truong:
            for ten, moi in cloud.truong.items():
                cu = truong.get(ten)
                khac = cu.gia_tri if cu and cu.gia_tri.casefold() != moi.gia_tri.casefold() else None
                truong[ten] = TruongAI(ten, moi.gia_tri, moi.trich_dan, DUONG_CLOUD, khac)
        bi_loai = set(local.bi_loai) if local else set()
        if cloud:
            bi_loai |= set(cloud.bi_loai)
        bi_loai -= set(truong)
        nguon = {t.nguon for t in truong.values()}
        duong = ("LOCAL+CLOUD" if nguon == {DUONG_LOCAL, DUONG_CLOUD} else DUONG_CLOUD if nguon == {DUONG_CLOUD}
                 else DUONG_LOCAL if nguon else "KHONG")
        ly_do = list(ly_do_chuyen) + ([khong_dung] if khong_dung else []) + (list(cloud.ly_do) if cloud else [])
        if truong:
            thong_bao = {DUONG_LOCAL: "Đề xuất của Local AI",
                         DUONG_CLOUD: "Đề xuất của Cloud AI (qua Mask file v2)",
                         "LOCAL+CLOUD": "Đề xuất của Local AI, bổ sung bằng Cloud AI (qua Mask file v2)"}[duong]
            thong_bao += "; người duyệt xem trích dẫn trước khi dùng."
        else:
            thong_bao = "Chưa có kết quả AI, cần người làm."
        chi_tiet = []
        local_ly_do = [m for m in ly_do_chuyen if m != "KIEM_XAC_SUAT"]
        if local_ly_do and duong in (DUONG_LOCAL, "KHONG"):
            chi_tiet.append("Local AI: " + "; ".join(mo_ta_ly_do(m) for m in local_ly_do))
        if khong_dung:
            chi_tiet.append("Cloud: " + mo_ta_ly_do(khong_dung))
        elif cloud is not None and not cloud.truong:
            chi_tiet.append("Cloud: " + "; ".join(mo_ta_ly_do(m) for m in cloud.ly_do))
        if chi_tiet:
            thong_bao += " " + ". ".join(chi_tiet) + "."
        return KetQuaAI(loai.ma, MUC_VANG if truong else MUC_DO, truong, duong, thong_bao,
                        tuple(dict.fromkeys(ly_do)), tuple(sorted(bi_loai)), ma_yc)
