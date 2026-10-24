# -*- coding: utf-8 -*-
"""
cau_hinh.py — Đường dẫn, cấu hình máy AI và khoá API cloud.

- Cấu hình chung: <thư mục dự án>\\cau_hinh_may_ai.json (không đẩy lên Git) — dùng chung với master_hd.py.
  Biến môi trường ghi đè: OLLAMA_URL, AI_MODEL, HD_RA_LAI, HD_CLOUD, HD_CLOUD_MODEL, HD_CLOUD_TY_LE, HD_OUT_DIR.
- Khoá API cloud: biến môi trường ANTHROPIC_API_KEY / OPENAI_API_KEY, hoặc %USERPROFILE%\\.trich_xuat_hd\\khoa_api.json.
  Khoá KHÔNG bao giờ ghi vào mã nguồn, nhật ký hay thư mục dự án.
"""
import json
import os
from pathlib import Path

THU_MUC_GOI = Path(__file__).resolve().parent              # .../review_xaydung/trich_xuat
GOC = THU_MUC_GOI.parent                                     # .../review_xaydung
FILE_CAU_HINH = GOC / "cau_hinh_may_ai.json"
DANH_MUC_THAM_SO = THU_MUC_GOI / "DANH_MUC_THAM_SO.xlsx"
MAU_DANH_MUC_HD = THU_MUC_GOI / "mau" / "MAU_DANH_MUC_HOP_DONG.xlsx"
THU_MUC_KHOA = Path(os.environ.get("HD_THU_MUC_KHOA") or (Path.home() / ".trich_xuat_hd"))
FILE_KHOA = THU_MUC_KHOA / "khoa_api.json"

CLOUD_MODEL_MAC_DINH = {"anthropic": "claude-sonnet-5", "openai": "gpt-4o-mini"}

MAC_DINH = {
    "may_ai": "http://localhost:11434",
    "model": "qwen3:8b",
    "api": "ollama",
    "an_danh": True,
    "gui_ca_hop_dong": False,
    "timeout_giay": 1800,
    "ra_lai": True,                     # bước 6: rà lại toàn HĐ cho ô vàng
    # nguồn AI: "local" = máy Local AI (Ollama); "claude" = Claude qua API (che định danh) khi máy AI không bật được
    "nguon_ai": "local",
    "cloud": {"bat": False, "nha_cung_cap": "anthropic", "model": "", "ty_le": 20},
    # OCR PDF scan bằng ABBYY Hot Folder trên máy này: che_do tu_dong (chỉ PDF scan) / luon / tat;
    # thu_muc = nơi cài module abbyy_hotfolder ('' = tự tìm)
    "ocr": {"che_do": "tu_dong", "thu_muc": "", "cho_toi_da": 1800},
}
NHOM = ("cloud", "ocr")   # khoá dạng nhóm: gộp từng trường


def _bool(s, mac_dinh):
    if s is None or str(s).strip() == "":
        return mac_dinh
    return str(s).strip().lower() not in ("0", "no", "khong", "không", "false", "tat", "tắt")


def doc_cau_hinh(dung_env=True):
    """Cấu hình đã gộp: mặc định ← file ← biến môi trường (nếu dung_env)."""
    cfg = json.loads(json.dumps(MAC_DINH))
    if FILE_CAU_HINH.exists():
        try:
            d = json.loads(FILE_CAU_HINH.read_text(encoding="utf-8-sig"))
            for k, v in d.items():
                if k in NHOM and isinstance(v, dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except (OSError, ValueError):
            pass
    if dung_env:
        if os.environ.get("OLLAMA_URL"):
            cfg["may_ai"] = os.environ["OLLAMA_URL"]
        if os.environ.get("AI_MODEL"):
            cfg["model"] = os.environ["AI_MODEL"]
        cfg["ra_lai"] = _bool(os.environ.get("HD_RA_LAI"), cfg["ra_lai"])
        cfg["cloud"]["bat"] = _bool(os.environ.get("HD_CLOUD"), cfg["cloud"]["bat"])
        if os.environ.get("HD_CLOUD_MODEL"):
            cfg["cloud"]["model"] = os.environ["HD_CLOUD_MODEL"]
        if os.environ.get("HD_CLOUD_TY_LE"):
            try:
                cfg["cloud"]["ty_le"] = float(os.environ["HD_CLOUD_TY_LE"])
            except ValueError:
                pass
    cfg["cloud"]["nha_cung_cap"] = (cfg["cloud"].get("nha_cung_cap") or "anthropic").lower()
    return cfg


def luu_cau_hinh(thay_doi):
    """Ghi các khoá được đổi vào cau_hinh_may_ai.json (giữ nguyên khoá khác). Không bao giờ ghi khoá API ở đây."""
    cu = {}
    if FILE_CAU_HINH.exists():
        try:
            cu = json.loads(FILE_CAU_HINH.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            cu = {}
    for k, v in thay_doi.items():
        if k in ("khoa", "api_key", "key"):
            continue
        if k in NHOM and isinstance(v, dict):
            c = dict(cu.get(k) or MAC_DINH[k])
            c.update({a: b for a, b in v.items() if a not in ("khoa", "api_key", "key")})
            cu[k] = c
        else:
            cu[k] = v
    for k, v in MAC_DINH.items():
        cu.setdefault(k, v)
    FILE_CAU_HINH.write_text(json.dumps(cu, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc_cau_hinh(dung_env=False)


def thu_muc_du_lieu():
    """Gốc dữ liệu kết quả (không đẩy lên Git): ket_qua_AI\ — mọi file tải xuống của giao diện nằm trong đây."""
    p = Path(os.environ.get("HD_DU_LIEU") or (GOC / "ket_qua_AI"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def thu_muc_ket_qua():
    p = Path(os.environ.get("HD_OUT_DIR") or (thu_muc_du_lieu() / "trich_xuat"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def file_danh_muc_hd():
    p = Path(os.environ.get("HD_DANH_MUC_HD") or (thu_muc_du_lieu() / "DANH_MUC_HD" / "DANH_MUC_HOP_DONG.xlsx"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def file_csdl():
    return Path(os.environ.get("HD_CSDL") or (GOC / "co_so_du_lieu" / "hop_dong.db"))


# ------------------------------------------------------------------ khoá API cloud
_ENV_KHOA = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def _doc_file_khoa():
    try:
        return json.loads(FILE_KHOA.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def doc_khoa(nha_cung_cap):
    """Khoá API: biến môi trường trước, rồi file khoa_api.json. Không có → ''."""
    ncc = (nha_cung_cap or "").lower()
    return (os.environ.get(_ENV_KHOA.get(ncc, "_")) or _doc_file_khoa().get(ncc) or "").strip()


def luu_khoa(nha_cung_cap, khoa):
    ncc = (nha_cung_cap or "").lower()
    if ncc not in _ENV_KHOA:
        raise ValueError("Nhà cung cấp phải là anthropic hoặc openai")
    khoa = (khoa or "").strip()
    if len(khoa) < 12 or any(c.isspace() for c in khoa):
        raise ValueError("Khoá API không hợp lệ")
    THU_MUC_KHOA.mkdir(parents=True, exist_ok=True)
    d = _doc_file_khoa()
    d[ncc] = khoa
    FILE_KHOA.write_text(json.dumps(d, indent=1), encoding="utf-8")
    try:
        os.chmod(FILE_KHOA, 0o600)
    except OSError:
        pass
    return khoa_an(ncc)


def xoa_khoa(nha_cung_cap):
    d = _doc_file_khoa()
    if d.pop((nha_cung_cap or "").lower(), None) is not None:
        FILE_KHOA.write_text(json.dumps(d, indent=1), encoding="utf-8")


def khoa_an(nha_cung_cap):
    """Thông tin hiển thị: có khoá chưa, nguồn, 4 ký tự cuối."""
    ncc = (nha_cung_cap or "").lower()
    env = os.environ.get(_ENV_KHOA.get(ncc, "_"))
    k = doc_khoa(ncc)
    return {"nha_cung_cap": ncc, "co_khoa": bool(k), "nguon": "biến môi trường" if env else ("file" if k else ""),
            "bon_ky_tu_cuoi": k[-4:] if k else ""}
