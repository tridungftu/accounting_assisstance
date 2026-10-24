# -*- coding: utf-8 -*-
"""
dich_vu.py — Các chức năng phía máy (back-end) mà giao diện gọi qua API. Không phụ thuộc HTTP.
Lỗi người dùng → LoiNguoiDung(mã HTTP, thông báo).
"""
import datetime
import json
import os
import re
import shutil
import zipfile
import sys
import time
from collections import Counter
from pathlib import Path

from trich_xuat import PHIEN_BAN as PHIEN_BAN_TRICH
from trich_xuat import cau_hinh as ch
from trich_xuat import may_ai
from trich_xuat.ai_local import MayAI
from trich_xuat.danh_muc import load_params, read_catalog, save_catalog
from trich_xuat.kiem_tra import la_ok
from trich_xuat.lo import LuotChay
from trich_xuat.quy_trinh import BUOC
from trich_xuat.xuat import _loai_hd, can_xem, cap_nhat_o, doc_ket_qua, ghi_danh_muc, tom_tat_review

from . import doi_xls as dx
from . import nghiep_vu as nv
from .viec import QuanLyViec

sys.path.insert(0, str(ch.GOC))           # csdl_hop_dong.py, toan_ven.py, master_hd.py ở thư mục gốc dự án

QLV = QuanLyViec()
LUOT = {}                                 # lượt trích xuất đang/đã chạy trong phiên này: nhãn → LuotChay
MAX_FILE = 60 * 1024 * 1024
RE_LUOT = re.compile(r"\d{8}_\d{6}(?:_\d+)?")


class LoiNguoiDung(Exception):
    def __init__(self, ma, thong_bao, chi_tiet=None):
        super().__init__(thong_bao)
        self.ma, self.thong_bao, self.chi_tiet = ma, thong_bao, chi_tiet


def _json_an_toan(o):
    return json.loads(json.dumps(o, ensure_ascii=False, default=str))


def duong_dan_tai(p):
    """Đường dẫn tải xuống (tương đối trong thư mục dữ liệu) cho giao diện: /tai/<...>."""
    try:
        rel = Path(p).resolve().relative_to(ch.thu_muc_du_lieu().resolve())
    except ValueError:
        return ""
    return "/tai/" + "/".join(rel.parts)


def file_tai(rel):
    goc = ch.thu_muc_du_lieu().resolve()
    p = (goc / rel).resolve()
    if goc not in p.parents or not p.is_file():
        raise LoiNguoiDung(404, "Không có file")
    return p


def ten_an_toan(name, duoi_ok):
    name = os.path.basename(str(name).replace("\\", "/")).strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    if not name or name.startswith((".", "~$")) or not name.lower().endswith(tuple(duoi_ok)):
        raise LoiNguoiDung(400, f"Chỉ nhận file {', '.join(duoi_ok)}: {name or '(trống)'}")
    return name


def luu_tai_len(thu_muc, ten, data, duoi_ok):
    ten = ten_an_toan(ten, duoi_ok)
    if not data or len(data) > MAX_FILE:
        raise LoiNguoiDung(400, f"File rỗng hoặc lớn hơn {MAX_FILE // 1024 // 1024} MB: {ten}")
    if ten.lower().endswith((".docx", ".xlsx", ".xlsm")) and not data.startswith(b"PK"):
        raise LoiNguoiDung(400, f"{ten} không phải file Office hợp lệ")
    if ten.lower().endswith(".xls") and not data.startswith((dx.OLE, b"PK")) and b"<" not in data[:512]:
        raise LoiNguoiDung(400, f"{ten} không phải file Excel hợp lệ")
    if ten.lower().endswith(".pdf") and not data.startswith(b"%PDF"):
        raise LoiNguoiDung(400, f"{ten} không phải file PDF hợp lệ")
    os.makedirs(thu_muc, exist_ok=True)
    p = os.path.join(thu_muc, ten)
    with open(p, "wb") as f:
        f.write(data)
    return p


def sang_xlsx(p, can_cong_thuc=False, trong_viec=False):
    """File .xls vừa tải lên → .xlsx (giữ công thức nếu máy có Excel / LibreOffice). Lỗi: trong việc nền → SystemExit
    (hiện nguyên câu), ngoài → 400."""
    try:
        return dx.chuan_hoa(p, can_cong_thuc)[0]
    except dx.LoiXls as e:
        if trong_viec:
            raise SystemExit(str(e)) from None
        raise LoiNguoiDung(400, str(e)) from None


def thu_muc_tai_len(loai):
    p = ch.thu_muc_du_lieu() / "tai_len" / loai / time.strftime("%Y%m%d_%H%M%S")
    i = 1
    while p.exists():
        p = p.with_name(time.strftime("%Y%m%d_%H%M%S") + f"_{i}")
        i += 1
    p.mkdir(parents=True)
    return p


# ================================================================== hệ thống / máy AI / cài đặt
_ai_cache = {"t": 0.0, "v": None}


def trang_thai_ai(lam_moi=False):
    if not lam_moi and _ai_cache["v"] and time.time() - _ai_cache["t"] < 15:
        return _ai_cache["v"]
    cfg = ch.doc_cau_hinh()
    if la_claude(cfg):
        n = _cloud_nguon(cfg)
        co = bool(ch.doc_khoa(n["nha_cung_cap"]))
        v = {"url": f"cloud:{n['nha_cung_cap']}", "ip": "Claude" if n["nha_cung_cap"] == "anthropic" else n["nha_cung_cap"],
             "cong": "", "model": n["model"], "ket_noi": co, "co_model": co, "models": [n["model"]], "nguon": "claude",
             "loi": "" if co else f"Nguồn AI là Claude nhưng chưa có API key {n['nha_cung_cap']} (Cài đặt → Kiểm tra chéo cloud)"}
        _ai_cache.update(t=time.time(), v=v)
        return v
    ip, cong = may_ai.tach_host(cfg["may_ai"])
    v = {"url": cfg["may_ai"], "ip": ip, "cong": cong, "model": cfg["model"], "ket_noi": False, "co_model": False,
         "models": [], "loi": "", "nguon": "local"}
    try:
        tags = MayAI(cfg["may_ai"], cfg["model"]).models(timeout=4)
        v["ket_noi"] = True
        v["models"] = [t for t in tags if not re.search(r"bge|embed|minilm|nomic", t, re.I)]
        v["co_model"] = cfg["model"] in tags or f"{cfg['model']}:latest" in tags
        if not v["co_model"]:
            v["loi"] = f"Máy AI chưa có model {cfg['model']}"
    except Exception as e:  # noqa: BLE001
        v["loi"] = f"Không kết nối được máy AI {ip}:{cong} ({type(e).__name__})"
    _ai_cache.update(t=time.time(), v=v)
    return v


def he_thong():
    return {"phien_ban": PHIEN_BAN_TRICH, "ai": trang_thai_ai(), "buoc": BUOC,
            "viec_dang_chay": len(QLV.dang_chay())}


def lay_cai_dat():
    cfg = ch.doc_cau_hinh()
    ip, cong = may_ai.tach_host(cfg["may_ai"])
    return {"may_ai": {"ip": ip, "cong": cong, "url": cfg["may_ai"], "model": cfg["model"],
                       "an_danh": cfg.get("an_danh", True), "timeout_giay": cfg.get("timeout_giay", 1800)},
            "trich_xuat": {"ra_lai": cfg["ra_lai"]},
            "nguon_ai": cfg.get("nguon_ai") or "local",
            "cloud": {**cfg["cloud"], "khoa": {n: ch.khoa_an(n) for n in ("anthropic", "openai")},
                      "model_mac_dinh": ch.CLOUD_MODEL_MAC_DINH},
            "du_lieu": {"csdl": str(ch.file_csdl()), "ket_qua": str(ch.thu_muc_ket_qua()),
                        "danh_muc_hd": str(ch.file_danh_muc_hd()), "khoa_api": str(ch.FILE_KHOA)},
            "ocr": _ocr_cai_dat(),
            "ip_may_nay": may_ai.ip_may_nay(),
            "bien_moi_truong": {k: os.environ[k] for k in ("OLLAMA_URL", "AI_MODEL", "HD_RA_LAI", "HD_CLOUD")
                                if os.environ.get(k)}}


def _ocr_cai_dat():
    from trich_xuat import ocr_abbyy as ocr
    o = ocr.cau_hinh_ocr()
    d = ocr.thu_muc(o, tao=False)
    return {**o, "che_do_ds": [{"ma": k, "ten": v} for k, v in ocr.TEN_CHE_DO.items()],
            "mac_dinh_thu_muc": str(ocr.thu_muc_mac_dinh()), "input_dir": str(d["in"]), "output_dir": str(d["out"])}


def trang_thai_ocr(lam_moi=False):
    from trich_xuat import ocr_abbyy as ocr
    return _json_an_toan(ocr.trang_thai(lam_moi=lam_moi))


def chay_thu_ocr():
    from trich_xuat import ocr_abbyy as ocr

    def ham(v):
        v.tien_do(0.05, "Đưa PDF thử 1 trang vào thư mục in…")
        try:
            kq = ocr.chay_thu(tien_do=lambda m: v.tien_do(0.5, m), dung=v.dung)
        except ocr.LoiOCR as e:
            raise SystemExit(e.thong_diep) from None
        v.tien_do(1.0, f"ABBYY trả Word sau {kq['giay']:.0f} giây")
        return kq
    return QLV.tao("ocr_thu", "Chạy thử OCR ABBYY (1 trang)", ham).to_dict()


def luu_cai_dat(d):
    thay = {}
    o = d.get("ocr") or {}
    if o:
        from trich_xuat import ocr_abbyy as ocr
        oo = {}
        if "che_do" in o:
            if o["che_do"] not in ocr.CHE_DO:
                raise LoiNguoiDung(400, "Chế độ OCR không hợp lệ")
            oo["che_do"] = o["che_do"]
        if "thu_muc" in o:
            tm = str(o["thu_muc"] or "").strip().strip('"')
            if tm:
                if not os.path.isabs(tm):
                    raise LoiNguoiDung(400, f"Thư mục OCR phải là đường dẫn đầy đủ (vd D:\\...\\ocr): {tm}")
                try:
                    os.makedirs(tm, exist_ok=True)
                except OSError as e:
                    raise LoiNguoiDung(400, f"Không tạo được thư mục OCR {tm}: {e}") from None
            oo["thu_muc"] = tm
        for k, ten in (("cho_toi_da", "Thời gian chờ OCR"), ("cho_nhan", "Thời gian chờ Hot Folder nhận file")):
            if k in o:
                try:
                    oo[k] = max(60, min(7200, int(o[k])))
                except (TypeError, ValueError):
                    raise LoiNguoiDung(400, f"{ten} phải là số giây") from None
        thay["ocr"] = oo
        ocr._tt_cache["v"] = None
    m = d.get("may_ai") or {}
    if "ip" in m or "cong" in m:
        ip = str(m.get("ip", "")).strip()
        if not may_ai.ip_hop_le(ip):
            raise LoiNguoiDung(400, f"Địa chỉ máy AI không hợp lệ: {ip or '(trống)'}")
        try:
            cong = int(m.get("cong") or may_ai.CONG_MAC_DINH)
        except ValueError:
            raise LoiNguoiDung(400, "Cổng phải là số") from None
        thay["may_ai"] = may_ai.chuan_host(ip, cong)
    for k in ("model", "an_danh", "timeout_giay"):
        if k in m:
            thay[k] = m[k]
    if "ra_lai" in (d.get("trich_xuat") or {}):
        thay["ra_lai"] = bool(d["trich_xuat"]["ra_lai"])
    if "nguon_ai" in d:
        if d["nguon_ai"] not in ("local", "claude"):
            raise LoiNguoiDung(400, "Nguồn AI phải là local hoặc claude")
        if d["nguon_ai"] == "claude":
            ncc = ((d.get("cloud") or {}).get("nha_cung_cap") or ch.doc_cau_hinh()["cloud"].get("nha_cung_cap")
                   or "anthropic")
            if not ch.doc_khoa(ncc):
                raise LoiNguoiDung(400, f"Chưa có API key {ncc} — nhập ở mục Kiểm tra chéo cloud trước khi chọn Claude")
        thay["nguon_ai"] = d["nguon_ai"]
    c = d.get("cloud") or {}
    if c:
        cc = {}
        if "bat" in c:
            cc["bat"] = bool(c["bat"])
        if "nha_cung_cap" in c:
            if c["nha_cung_cap"] not in ("anthropic", "openai"):
                raise LoiNguoiDung(400, "Nhà cung cấp phải là anthropic hoặc openai")
            cc["nha_cung_cap"] = c["nha_cung_cap"]
        if "model" in c:
            cc["model"] = str(c["model"] or "").strip()
        if "ty_le" in c:
            try:
                cc["ty_le"] = max(0.0, min(100.0, float(c["ty_le"])))
            except (TypeError, ValueError):
                raise LoiNguoiDung(400, "Tỷ lệ kiểm ngẫu nhiên phải là số 0–100") from None
        thay["cloud"] = cc
    ch.luu_cau_hinh(thay)
    _ai_cache["v"] = None
    return lay_cai_dat()


def thu_cloud(d):
    from trich_xuat.cloud import thu_ket_noi
    ncc = str(d.get("nha_cung_cap") or ch.doc_cau_hinh()["cloud"].get("nha_cung_cap") or "anthropic").lower()
    if ncc not in ("anthropic", "openai"):
        raise LoiNguoiDung(400, "Nhà cung cấp phải là anthropic hoặc openai")
    model = str(d.get("model") or ch.doc_cau_hinh()["cloud"].get("model") or "").strip() or None
    return thu_ket_noi(ncc, model)


def kiem_tra_may_ai(d):
    cfg = ch.doc_cau_hinh()
    ip = str(d.get("ip") or may_ai.tach_host(cfg["may_ai"])[0]).strip()
    if not may_ai.ip_hop_le(ip):
        raise LoiNguoiDung(400, f"Địa chỉ không hợp lệ: {ip}")
    host = may_ai.chuan_host(ip, d.get("cong") or may_ai.CONG_MAC_DINH)
    kq = may_ai.kiem_tra(host, d.get("model") or None, thu_model=bool(d.get("thu_model", True)))
    kq["url"] = host
    kq["models"] = [t for t in kq["models"] if not re.search(r"bge|embed|minilm|nomic", t or "", re.I)]
    return kq


def tim_may_ai(cong=None):
    def ham(v):
        v.tien_do(0.01, "Đang dò các máy trong mạng LAN…")
        ds = may_ai.tim_may_ai(int(cong or may_ai.CONG_MAC_DINH),
                               tien_do=lambda a, b: v.tien_do(0.95 * a / max(1, b), f"Đã dò {a}/{b} địa chỉ"))
        v.tien_do(1.0, f"Tìm thấy {len(ds)} máy AI")
        return {"may": [{"ip": ip, "models": m} for ip, m in ds], "ip_may_nay": may_ai.ip_may_nay()}
    return QLV.tao("tim_may_ai", "Tự tìm máy AI trong mạng", ham).to_dict()


def luu_khoa(d):
    try:
        return ch.luu_khoa(d.get("nha_cung_cap"), d.get("khoa"))
    except ValueError as e:
        raise LoiNguoiDung(400, str(e)) from None


def xoa_khoa(ncc):
    ch.xoa_khoa(ncc)
    return ch.khoa_an(ncc)


def danh_sach_nhat_ky_gui_ngoai():
    out = []
    for p in sorted(ch.thu_muc_ket_qua().glob("*/*/GUI_RA_NGOAI_*.txt"), reverse=True)[:200]:
        out.append({"ten": p.name, "hop_dong": p.parent.name, "luot": p.parent.parent.name,
                    "luc": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
                    "tai": duong_dan_tai(p)})
    return out


# ================================================================== danh mục tham số
def lay_tham_so():
    return {"rows": read_catalog(), "cot": ["ma", "nhom", "mo_ta", "tk", "bk", "dung", "muc", "bat_buoc", "loai_tru"]}


def luu_tham_so(d):
    try:
        bak = save_catalog(d.get("rows") or [])
    except ValueError as e:
        raise LoiNguoiDung(400, str(e)) from None
    return {"ok": True, "sao_luu": os.path.basename(bak) if bak else "", "rows": read_catalog()}


# ================================================================== trích xuất hợp đồng
def _thu_muc_luot(luot):
    if not RE_LUOT.fullmatch(luot or ""):
        raise LoiNguoiDung(400, "Mã lượt không hợp lệ")
    return ch.thu_muc_ket_qua() / luot


def luot_moi():
    luot = time.strftime("%Y%m%d_%H%M%S")
    i = 1
    while (ch.thu_muc_ket_qua() / luot).exists():
        luot = time.strftime("%Y%m%d_%H%M%S") + f"_{i}"
        i += 1
    (ch.thu_muc_ket_qua() / luot / "dau_vao").mkdir(parents=True)
    return {"luot": luot}


def tai_len_hop_dong(luot, ten, data):
    d = _thu_muc_luot(luot)
    if not d.exists():
        raise LoiNguoiDung(404, "Lượt không tồn tại")
    if luot in LUOT:
        raise LoiNguoiDung(409, "Lượt này đã chạy — tạo lượt mới để thêm hợp đồng")
    p = luu_tai_len(str(d / "dau_vao"), ten, data, (".docx", ".doc", ".pdf", ".tsv"))
    return {"ok": True, "ten": os.path.basename(p), "kich_thuoc": len(data)}


def xoa_tep_luot(luot, ten):
    d = _thu_muc_luot(luot) / "dau_vao"
    p = d / ten_an_toan(ten, (".docx", ".doc", ".pdf", ".tsv"))
    if luot in LUOT:
        raise LoiNguoiDung(409, "Lượt này đã chạy")
    if p.exists():
        p.unlink()
    return {"ok": True}


def _ds_tep(luot):
    d = _thu_muc_luot(luot) / "dau_vao"
    if not d.exists():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_file())


def chay_luot(luot, opts):
    d = _thu_muc_luot(luot)
    if luot in LUOT:
        raise LoiNguoiDung(409, "Lượt này đã chạy")
    files = [str(d / "dau_vao" / f) for f in _ds_tep(luot) if f.lower().endswith((".docx", ".doc", ".pdf"))]
    if not files:
        raise LoiNguoiDung(400, "Chưa có hợp đồng .docx/.doc/.pdf nào được tải lên")
    cfg = ch.doc_cau_hinh()
    model = str(opts.get("model") or cfg["model"]).strip()
    params = load_params(them=opts.get("them") or [])
    chon = opts.get("tham_so")
    if chon:
        params = [p for p in params if p["ma"] in set(chon) or p["ma"].startswith("Y-")]
    if not params:
        raise LoiNguoiDung(400, "Chưa chọn tham số nào")
    c = opts.get("cloud")
    if c is None:
        c = cfg["cloud"]
    cloud = None
    if c and c.get("bat"):
        ncc = c.get("nha_cung_cap") or cfg["cloud"]["nha_cung_cap"]
        if not ch.doc_khoa(ncc):
            raise LoiNguoiDung(400, f"Chưa có API key {ncc} — vào Cài đặt → Kiểm tra chéo cloud để nhập")
        cloud = {"nha_cung_cap": ncc, "model": c.get("model") or cfg["cloud"]["model"],
                 "ty_le": float(c.get("ty_le", cfg["cloud"]["ty_le"]) or 0)}
    ra_lai = bool(opts["ra_lai"]) if "ra_lai" in opts else cfg["ra_lai"]
    nguon = None
    if la_claude(cfg):                 # Claude thay Local AI: không rà lại toàn HĐ, không kiểm tra chéo (đã là Claude)
        nguon = _cloud_nguon(cfg)
        if not ch.doc_khoa(nguon["nha_cung_cap"]):
            raise LoiNguoiDung(400, f"Nguồn AI là Claude nhưng chưa có API key {nguon['nha_cung_cap']}")
        model, ra_lai, cloud = nguon["model"], False, None
    lc = LuotChay(files, str(d), params, cfg["may_ai"], model, ra_lai=ra_lai, cloud=cloud, nguon_ai=nguon,
                  chay_lai=bool(opts.get("chay_lai")), chi_cau_truc=bool(opts.get("chi_cau_truc")),
                  thu_muc_dap_an=str(d / "dau_vao"), timeout=cfg.get("timeout_giay", 1800), nhan_luot=luot)
    LUOT[luot] = lc
    with open(d / "_tuy_chon.json", "w", encoding="utf-8") as f:
        json.dump({"model": model, "may_ai": "Claude (che định danh)" if nguon else cfg["may_ai"], "ra_lai": ra_lai,
                   "cloud": cloud, "nguon_ai": "claude" if nguon else "local",
                   "chay_lai": bool(opts.get("chay_lai")), "so_tham_so": len(params),
                   "tao_luc": datetime.datetime.now().isoformat(timespec="seconds")}, f, ensure_ascii=False, indent=1)

    def ham(v):
        lc.chay()
        if lc.s["tt"] == "loi":
            v.tt, v.loi = "loi", lc.s["thong_bao"]
        elif lc.s["tt"] == "da_dung":
            v.tt = "da_dung"
        return {"luot": luot}
    v = QLV.tao("trich_xuat", f"Trích {len(files)} hợp đồng ({model})", ham, dung_ai=True, id_=f"TX-{luot}",
                chi_tiet=lc.trang_thai, dung=lc.dung)
    _ai_cache["v"] = None
    return {"viec": v.to_dict(), "luot": luot, "so_hop_dong": len(files), "so_tham_so": len(params),
            "cloud": bool(cloud), "ra_lai": ra_lai, "model": model}


def chay_lai_luot(luot, opts):
    """Tạo lượt mới với cùng các file đầu vào của lượt cũ rồi chạy (dùng khi lượt cũ lỗi / đã dừng)."""
    d = _thu_muc_luot(luot) / "dau_vao"
    if not d.exists():
        raise LoiNguoiDung(404, "Không có lượt này")
    moi = luot_moi()["luot"]
    for f in d.iterdir():
        if f.is_file():
            shutil.copy2(f, _thu_muc_luot(moi) / "dau_vao" / f.name)
    return chay_luot(moi, opts)


def _bo_sung_tai(luot, s):
    d = _thu_muc_luot(luot)
    for h in s.get("hd", []):
        h["tai"] = {}
        if h.get("ten"):
            kq = d / h["ten"] / f"{h['ten']}_KET_QUA.json"
            if kq.exists():
                tep = doc_ket_qua(kq).get("tep", {})
                h["tai"] = {k: duong_dan_tai(d / h["ten"] / v) for k, v in tep.items() if (d / h["ten"] / v).exists()}
    s["tai"] = {k: duong_dan_tai(d / v) for k, v in (s.get("tep") or {}).items() if v and (d / v).exists()}
    if s.get("danh_muc"):
        s["tai"]["danh_muc_hd"] = duong_dan_tai(s["danh_muc"])
    return s


def chi_tiet_luot(luot):
    d = _thu_muc_luot(luot)
    if luot in LUOT:
        s = LUOT[luot].trang_thai()
    elif (d / "_luot.json").exists():
        s = json.loads((d / "_luot.json").read_text(encoding="utf-8"))
    elif d.exists():
        s = {"tt": "chua_chay", "hd": [{"file": f, "tt": "Chờ"} for f in _ds_tep(luot) if f.lower().endswith((".docx", ".doc", ".pdf"))],
             "log": []}
    else:
        raise LoiNguoiDung(404, "Không có lượt này")
    s["luot"] = luot
    s["tep_dau_vao"] = _ds_tep(luot)
    tc = d / "_tuy_chon.json"
    s["tuy_chon"] = json.loads(tc.read_text(encoding="utf-8")) if tc.exists() else {}
    s["viec_id"] = f"TX-{luot}"
    s["log"] = [[time.strftime("%H:%M:%S", time.localtime(t)), m] for t, m in s.get("log", [])][-200:]
    return _bo_sung_tai(luot, s)


def ds_luot(gioi_han=50):
    out = []
    for d in sorted((p for p in ch.thu_muc_ket_qua().iterdir() if p.is_dir() and RE_LUOT.fullmatch(p.name)),
                    reverse=True)[:gioi_han]:
        luot = d.name
        if luot in LUOT:
            s = LUOT[luot].trang_thai()
        elif (d / "_luot.json").exists():
            try:
                s = json.loads((d / "_luot.json").read_text(encoding="utf-8"))
            except ValueError:
                s = {"tt": "loi", "hd": []}
        else:
            s = {"tt": "chua_chay", "hd": [{"file": f} for f in _ds_tep(luot) if f.lower().endswith((".docx", ".doc", ".pdf"))]}
        hd = s.get("hd", [])
        out.append({"luot": luot, "tt": s.get("tt"), "model": s.get("model"), "pct": s.get("pct", 0),
                    "so_hd": len(hd), "so_xong": sum(1 for h in hd if (h.get("tt") or "").startswith(("Xong", "Bỏ qua"))),
                    "so_vang": sum(h.get("so_vang") or 0 for h in hd), "bat_dau": s.get("bat_dau"),
                    "ket_thuc": s.get("ket_thuc"), "hop_dong": [h.get("file") for h in hd]})
    return out


def _json_hd(luot, ten):
    d = _thu_muc_luot(luot)
    if not ten or "/" in ten or "\\" in ten or ten.startswith("."):
        raise LoiNguoiDung(400, "Tên hợp đồng không hợp lệ")
    p = d / ten / f"{ten}_KET_QUA.json"
    if not p.exists():
        raise LoiNguoiDung(404, "Chưa có kết quả cho hợp đồng này")
    return p


def ket_qua_hd(luot, ten):
    p = _json_hd(luot, ten)
    kq = tom_tat_review(doc_ket_qua(p))
    for d in kq["bang"]:
        d["vang"] = not la_ok(d.get("kiem_tra"))
        d["can_xem"] = can_xem(d)
    kq["tai"] = {k: duong_dan_tai(p.parent / v) for k, v in kq.get("tep", {}).items() if (p.parent / v).exists()}
    if not kq.get("doan_lien_quan"):
        kq.pop("doan_lien_quan", None)
    return kq


def sua_o(luot, ten, ma, body):
    p = _json_hd(luot, ten)
    try:
        d = cap_nhat_o(str(p), ma, gia_tri=body.get("gia_tri"), xac_nhan=body.get("xac_nhan"),
                       ghi_chu=body.get("ghi_chu"), nguoi=_nguoi())
    except ValueError as e:
        raise LoiNguoiDung(404 if str(e).startswith("Không có") else 400, str(e)) from None
    d["vang"], d["can_xem"] = not la_ok(d.get("kiem_tra")), can_xem(d)
    return d


def xac_nhan_nhieu(luot, ten, body):
    ds = body.get("ma") or []
    out = [sua_o(luot, ten, ma, {"xac_nhan": body.get("xac_nhan", True)}) for ma in ds]
    return {"ok": True, "so_dong": len(out), "dong": out}


def ghi_lai_danh_muc(luot, ten=None):
    d = _thu_muc_luot(luot)
    tens = [ten] if ten else [p.name for p in d.iterdir() if p.is_dir() and (p / f"{p.name}_KET_QUA.json").exists()]
    ds = [doc_ket_qua(_json_hd(luot, t)) for t in tens]
    try:
        p, moi, sua = ghi_danh_muc(ds, str(ch.file_danh_muc_hd()), str(ch.MAU_DANH_MUC_HD))
    except PermissionError:
        raise LoiNguoiDung(409, "DANH_MUC_HOP_DONG.xlsx đang mở trong Excel — đóng file rồi thử lại") from None
    return {"ok": True, "moi": moi, "cap_nhat": sua, "tai": duong_dan_tai(p)}


# ================================================================== cơ sở dữ liệu hợp đồng
def _csdl():
    try:
        import csdl_hop_dong as cs
    except ImportError as e:
        raise LoiNguoiDung(500, f"Không mở được module CSDL ({e}). Cần: pip install openpyxl") from None
    return cs, cs.mo_csdl(str(ch.file_csdl()))


def _nguoi():
    return os.environ.get("USERNAME") or os.environ.get("USER") or ""


def _sha1(path):
    import hashlib
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    except OSError:
        return ""


def nap_csdl_tu_ket_qua(luot, ten, body):
    """Nạp kết quả trích xuất vào CSDL: tham_so (giá trị) + tham_so_nguon (nguồn gốc, trạng thái review, lịch sử).
    Còn ô chưa xác nhận → 409 kèm danh sách; giao diện hỏi lại rồi gửi van_nap=true (các ô đó giữ cờ cần xác nhận)."""
    p = _json_hd(luot, ten)
    kq = tom_tat_review(doc_ket_qua(p))
    chua = [d["ma"] for d in kq["bang"] if not d["da_xac_nhan"]]
    vang = [d["ma"] for d in kq["bang"] if can_xem(d)]
    if chua and not body.get("van_nap"):
        raise LoiNguoiDung(409, f"Còn {len(chua)} tham số chưa xác nhận ({len(vang)} ô vàng). Các ô này sẽ được đánh dấu "
                                "cần xác nhận trong CSDL.", {"chua_xac_nhan": chua, "o_vang": vang})
    vals = {d["ma"]: d for d in kq["bang"]}
    so_hd = (vals.get("TC-01") or {}).get("gia_tri", "").strip()
    if not so_hd or so_hd.lower().startswith("không"):
        raise LoiNguoiDung(400, "Chưa có Số hợp đồng (TC-01) — sửa ô TC-01 trước khi nạp")
    cs, con = _csdl()
    try:
        ts = {}
        for d in kq["bang"]:
            if d["da_xac_nhan"]:
                tt = "Đã sửa tay" if d["da_sua"] else "Đã xác nhận"
            else:
                tt = "AI - tự kiểm OK, chưa xác nhận" if la_ok(d.get("kiem_tra")) else "AI - CẦN XÁC NHẬN"
            ts[d["ma"]] = dict(ten=d.get("tham_so"), gia_tri=d.get("gia_tri"), don_vi=d.get("don_vi"),
                               dieu_khoan=d.get("dieu_khoan"), trich_dan=d.get("trich_dan"), trang_thai=tt)
        cu = con.execute("SELECT ma_hd FROM hop_dong WHERE so_hd = ?", (cs.nfc(so_hd),)).fetchone()
        if cu:
            lech = []
            for k, v in ts.items():
                r = con.execute("SELECT gia_tri FROM tham_so WHERE ma_hd = ? AND ma_ts = ?", (cu[0], k)).fetchone()
                if r is None:
                    continue
                a_, b_ = str(v["gia_tri"] or "").strip(), str(r[0] or "").strip()
                if cs.bo_dau(a_) != cs.bo_dau(b_):
                    lech.append({"ma": k, "ket_qua": a_, "csdl": b_})
            return {"ok": True, "ma_hd": cu[0], "moi": False,
                    "trang_thai": "Đã có trong CSDL — chỉ so sánh, không ghi đè", "lech": lech}
        ma = cs._them_hop_dong(con, cs.nfc(so_hd), ts, phan_loai=_loai_hd((vals.get("TC-09") or {}).get("gia_tri", "")),
                               file_nguon=kq["hop_dong"])
        luc = datetime.datetime.now().isoformat(timespec="seconds")
        src = _thu_muc_luot(luot) / "dau_vao" / kq["hop_dong"]
        for d in kq["bang"]:
            con.execute("INSERT INTO tham_so_nguon VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (ma, d["ma"], d.get("gia_tri_ai"), d.get("gia_tri"), d.get("kiem_tra"), d.get("muc"),
                         d.get("nguon"), int(d["da_xac_nhan"]), int(d["da_sua"]), d.get("nguoi_xac_nhan"),
                         d.get("luc_xac_nhan"), d.get("ghi_chu_soat"), json.dumps(d.get("lich_su", []), ensure_ascii=False),
                         kq.get("model"), kq.get("may_ai"), luot, kq["hop_dong"], _sha1(src), kq.get("tao_luc"), luc))
        cs.ghi_nhat_ky(con, "Nạp từ trích xuất AI", ma,
                       f"{kq['hop_dong']} (lượt {luot}, {kq.get('model')}): {len(ts)} tham số, {len(chua)} chưa xác nhận")
        con.commit()
        kq["csdl"] = {"ma_hd": ma, "luc_nap": luc}
        with open(str(p) + ".tmp", "w", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False, indent=1)
        os.replace(str(p) + ".tmp", p)
        return {"ok": True, "ma_hd": ma, "moi": True, "trang_thai": "Đã thêm vào CSDL", "lech": [],
                "chua_xac_nhan": chua}
    finally:
        con.close()


def xac_nhan_tham_so_csdl(ref, ma_ts, body):
    """Xác nhận trong CSDL một tham số đã nạp khi còn chưa xác nhận (ghi nhật ký, không đổi giá trị)."""
    cs, con = _csdl()
    try:
        hd = cs.tim_hd(con, ref)
        r = con.execute("SELECT * FROM tham_so_nguon WHERE ma_hd = ? AND ma_ts = ?", (hd["ma_hd"], ma_ts)).fetchone()
        if not r:
            raise LoiNguoiDung(404, "Tham số này không có thông tin nguồn trích xuất")
        if r["da_xac_nhan"]:
            return {"ok": True, "da_xac_nhan": True}
        luc = datetime.datetime.now().isoformat(timespec="seconds")
        ls = json.loads(r["lich_su"] or "[]") + [{"luc": luc, "thao_tac": "Xác nhận trong CSDL", "nguoi": _nguoi(),
                                                    "moi": r["gia_tri"], "cu": "", "ghi_chu": body.get("ghi_chu", "")}]
        with cs.che_do_sua(con, f"Xác nhận tham số {ma_ts} sau khi nạp", hd["ma_hd"]):
            con.execute("UPDATE tham_so_nguon SET da_xac_nhan = 1, nguoi_xac_nhan = ?, luc_xac_nhan = ?, lich_su = ? "
                        "WHERE ma_hd = ? AND ma_ts = ?", (_nguoi(), luc, json.dumps(ls, ensure_ascii=False),
                                                          hd["ma_hd"], ma_ts))
            con.execute("UPDATE tham_so SET trang_thai = 'Đã xác nhận' WHERE ma_hd = ? AND ma_ts = ?", (hd["ma_hd"], ma_ts))
        con.commit()
        return {"ok": True, "da_xac_nhan": True}
    finally:
        con.close()


def _hd_dict(r):
    return {k: r[k] for k in r.keys()}


def _nhom_tham_so():
    try:
        return {r["ma"]: (r["nhom"], r["mo_ta"].split("(")[0].strip()[:60], r["muc"]) for r in read_catalog()}
    except Exception:  # noqa: BLE001
        return {}


def ds_hop_dong():
    cs, con = _csdl()
    try:
        hom_nay = datetime.date.today().isoformat()
        out = []
        for r in con.execute("SELECT * FROM hop_dong ORDER BY ma_hd"):
            ma = r["ma_hd"]
            d = _hd_dict(r)
            g = lambda k: (con.execute("SELECT gia_tri FROM tham_so WHERE ma_hd = ? AND ma_ts = ?", (ma, k))  # noqa: E731
                           .fetchone() or [None])[0]
            d.update(ben_a=g("TC-06"), ben_b=g("TC-07"), du_an=g("TC-04"), goi_thau=d.get("goi_thau") or g("TC-03"))
            d["gt_sau_vat_goc"] = cs.gt_sau_vat_goc(r)
            d["gt_hieu_luc_hom_nay"] = cs.gt_hd_hieu_luc(con, ma, hom_nay)
            d["so_phu_luc"] = con.execute("SELECT COUNT(*) FROM phu_luc WHERE ma_hd = ? AND trang_thai <> 'Đã hủy'",
                                          (ma,)).fetchone()[0]
            d["so_dot"] = con.execute("SELECT COUNT(*) FROM dot_thanh_toan WHERE ma_hd = ?", (ma,)).fetchone()[0]
            d["so_boq"] = con.execute("SELECT COUNT(*) FROM boq_dong WHERE ma_hd = ? AND pl_id IS NULL", (ma,)).fetchone()[0]
            d["so_tham_so"] = con.execute("SELECT COUNT(*) FROM tham_so WHERE ma_hd = ?", (ma,)).fetchone()[0]
            cb = Counter(x[0] for x in con.execute("SELECT muc_do FROM canh_bao WHERE ma_hd = ?", (ma,)))
            d["co_do"], d["co_vang"] = cb.get("ĐỎ", 0) + cb.get("CHẶN", 0), cb.get("VÀNG", 0)
            d["chua_xac_nhan"] = con.execute(
                "SELECT COUNT(*) FROM tham_so_nguon WHERE ma_hd = ? AND da_xac_nhan = 0 AND (kiem_tra IS NULL OR "
                "kiem_tra NOT LIKE 'OK%')", (ma,)).fetchone()[0]
            out.append(d)
        return _json_an_toan(out)
    finally:
        con.close()


def chi_tiet_hop_dong(ref, ngay=None):
    cs, con = _csdl()
    try:
        hd = cs.tim_hd(con, ref)
        ma = hd["ma_hd"]
        try:
            ngay = cs.ngay_iso(ngay) if ngay else datetime.date.today().isoformat()
        except ValueError:
            raise LoiNguoiDung(400, f"Ngày không hợp lệ: {ngay}") from None
        ls = cs.lich_su_tham_so(con, ma, ngay)
        nhom = _nhom_tham_so()
        nguon = {r["ma_ts"]: _hd_dict(r) for r in con.execute("SELECT * FROM tham_so_nguon WHERE ma_hd = ?", (ma,))}
        ts = []
        for r in con.execute("SELECT * FROM tham_so WHERE ma_hd = ? ORDER BY ma_ts", (ma,)):
            v, ng = cs.tham_so_hieu_luc(con, ma, r["ma_ts"], ngay)
            n = nguon.get(r["ma_ts"]) or {}
            if n.get("lich_su"):
                try:
                    n["lich_su"] = json.loads(n["lich_su"])
                except ValueError:
                    pass
            g = nhom.get(r["ma_ts"], ("", "", None))
            ts.append({**_hd_dict(r), "nhom": g[0], "muc": n.get("muc", g[2]), "gia_tri_hieu_luc": v, "nguon_hieu_luc": ng,
                       "lich_su": [{"so_pl": a, "ngay_hieu_luc": b, "cu": c, "moi": d_, "trich_dan": e}
                                   for a, b, c, d_, e in ls.get(r["ma_ts"], [])], "nguon_trich": n or None})
        pls = [_hd_dict(p) for p in con.execute("SELECT * FROM phu_luc WHERE ma_hd = ? ORDER BY ngay_hieu_luc, so_pl", (ma,))]
        for p in pls:
            p["co_do"] = con.execute("SELECT COUNT(*) FROM canh_bao WHERE pl_id = ? AND muc_do IN ('ĐỎ','CHẶN')",
                                     (p["id"],)).fetchone()[0]
            p["co_vang"] = con.execute("SELECT COUNT(*) FROM canh_bao WHERE pl_id = ? AND muc_do = 'VÀNG'",
                                       (p["id"],)).fetchone()[0]
        dots = [_hd_dict(p) for p in con.execute("SELECT * FROM dot_thanh_toan WHERE ma_hd = ? ORDER BY dot", (ma,))]
        cb = [_hd_dict(p) for p in con.execute("SELECT * FROM canh_bao WHERE ma_hd = ? ORDER BY id DESC", (ma,))]
        g = lambda k: next((x["gia_tri"] for x in ts if x["ma_ts"] == k), None)  # noqa: E731
        return _json_an_toan({"hop_dong": {**_hd_dict(hd), "ben_b": g("TC-07"), "du_an": g("TC-04"), "ben_a": g("TC-06")},
                              "ngay": ngay, "gt_goc": cs.gt_sau_vat_goc(hd), "gt_hieu_luc": cs.gt_hd_hieu_luc(con, ma, ngay),
                              "tham_so": ts, "phu_luc": pls, "dot": dots, "canh_bao": cb,
                              "pl_ap_dung": [p["so_pl"] for p in cs.phu_luc_ap_dung(con, ma, ngay)]})
    finally:
        con.close()


def boq_hieu_luc(ref, ngay=None):
    cs, con = _csdl()
    try:
        hd = cs.tim_hd(con, ref)
        try:
            ngay = cs.ngay_iso(ngay) if ngay else datetime.date.today().isoformat()
        except ValueError:
            raise LoiNguoiDung(400, f"Ngày không hợp lệ: {ngay}") from None
        hl, bo = cs.boq_hieu_luc(con, hd["ma_hd"], ngay)
        tong = sum(round((d["kl"] or 0) * (d["don_gia"] or 0)) for d in hl.values())
        vat = hd["vat"] or 0
        gt = cs.gt_hd_hieu_luc(con, hd["ma_hd"], ngay)
        return _json_an_toan({"ma_hd": hd["ma_hd"], "so_hd": hd["so_hd"], "ngay": ngay, "dong": list(hl.values()),
                              "da_bo": list(bo.values()), "tong_truoc_vat": tong, "vat": vat,
                              "tong_sau_vat": tong * (1 + vat), "gt_hieu_luc": gt,
                              "khop": bool(hl) and abs(tong * (1 + vat) - gt) <= cs.tol_tien(gt),
                              "pl_ap_dung": [p["so_pl"] for p in cs.phu_luc_ap_dung(con, hd["ma_hd"], ngay)]})
    finally:
        con.close()


def tao_phieu_phu_luc(ref):
    cs, con = _csdl()
    try:
        d = ch.thu_muc_du_lieu() / "phieu_phu_luc"
        d.mkdir(parents=True, exist_ok=True)
        hd = cs.tim_hd(con, ref)
        out, so_pl = cs.tao_phieu(con, ref, str(d / f"phieu_phu_luc_{hd['ma_hd']}_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"))
        return {"so_pl": so_pl, "tai": duong_dan_tai(out)}
    finally:
        con.close()


def nap_phieu_phu_luc(ten, data, chi_kiem_tra=True):
    p = sang_xlsx(luu_tai_len(str(thu_muc_tai_len("phu_luc")), ten, data, (".xlsx", ".xlsm", ".xls")))
    cs, con = _csdl()
    try:
        out = []
        for sh, pl, kq, tt in cs.nap_phu_luc(con, p, chi_kiem_tra=chi_kiem_tra):
            out.append({"sheet": sh, "phu_luc": _json_an_toan(dict(pl)) if pl else {}, "ket_qua": tt,
                        "kiem_tra": [{"ma": a, "muc": b, "noi_dung": c} for a, b, c in kq],
                        "co_chan": any(b == "CHẶN" for _, b, _ in kq)})
        return {"tep": os.path.basename(p), "phieu": out}
    finally:
        con.close()


def huy_phu_luc(ref, so_pl, ly_do):
    if not (ly_do or "").strip():
        raise LoiNguoiDung(400, "Huỷ phụ lục phải nhập lý do")
    cs, con = _csdl()
    try:
        cs.huy_phu_luc(con, ref, so_pl, ly_do)
        return {"ok": True}
    finally:
        con.close()


def xuat_csdl_excel(ref=None, ngay=None):
    cs, con = _csdl()
    try:
        d = ch.thu_muc_du_lieu() / "xuat_csdl"
        d.mkdir(parents=True, exist_ok=True)
        out = cs.xuat_excel(con, ref, ngay, str(d / f"CSDL_hop_dong_{(ref or 'tat_ca').replace('/', '-')}_"
                                                   f"{time.strftime('%Y%m%d_%H%M%S')}.xlsx"))
        return {"tai": duong_dan_tai(out)}
    finally:
        con.close()


def sao_luu_csdl():
    src = ch.file_csdl()
    if not src.exists():
        raise LoiNguoiDung(404, "Chưa có CSDL")
    d = src.parent / "sao_luu"
    d.mkdir(exist_ok=True)
    dst = d / f"hop_dong_{time.strftime('%Y%m%d_%H%M%S')}.db"
    import sqlite3
    with sqlite3.connect(str(src)) as a, sqlite3.connect(str(dst)) as b:
        a.backup(b)
    return {"ok": True, "file": str(dst)}


# ================================================================== đợt thanh toán / toàn vẹn / BOQ


def kiem_tra_dot(ref, ten, data, ngay_nt, dot=None):
    if not ngay_nt:
        raise LoiNguoiDung(400, "Phải nhập ngày nghiệm thu (mốc áp dụng phụ lục)")
    cs, con = _csdl()
    try:
        hd = cs.tim_hd(con, ref)
    finally:
        con.close()
    p = luu_tai_len(str(thu_muc_tai_len("dot_thanh_toan")), ten, data, (".xlsx", ".xlsm", ".xls"))

    def ham(v):
        if dx.la_xls(p):
            v.tien_do(0.02, "Chuyển file .xls sang .xlsx (giữ công thức)…")
        return nv.kiem_tra_dot(v, hd["ma_hd"], sang_xlsx(p, True, True), ngay_nt, dot, duong_dan_tai)
    return QLV.tao("kiem_dot", f"Kiểm tra đợt {dot or ''} · {hd['ma_hd']} · {os.path.basename(p)}".replace("  ", " "),
                   ham).to_dict()


def kiem_tra_toan_ven(ten, data, o_dich=None):
    p = luu_tai_len(str(thu_muc_tai_len("toan_ven")), ten, data, (".xlsx", ".xlsm", ".xls"))

    def ham(v):
        if dx.la_xls(p):
            v.tien_do(0.02, "Chuyển file .xls sang .xlsx (giữ công thức)…")
        return nv.toan_ven(v, sang_xlsx(p, True, True), o_dich, duong_dan_tai)
    return QLV.tao("toan_ven", f"Toàn vẹn file: {os.path.basename(p)}", ham).to_dict()


def ket_qua_kiem_tra(loai, ma=None):
    if loai not in ("kiem_tra_dot", "toan_ven"):
        raise LoiNguoiDung(404, "Không có loại kết quả này")
    if not ma:
        return {"ds": nv.ds_ket_qua_kiem_tra(loai)}
    try:
        return nv.doc_ket_qua_kiem_tra(loai, ma)
    except FileNotFoundError:
        raise LoiNguoiDung(404, "Không có kết quả này") from None
    except ValueError as e:
        raise LoiNguoiDung(400, str(e)) from None


def ghep_hang_muc(ma, body):
    try:
        return nv.ghep_hang_muc(ma, body.get("dong"), body.get("ma_hm"))
    except FileNotFoundError:
        raise LoiNguoiDung(404, "Không có kết quả kiểm tra này") from None
    except (ValueError, SystemExit) as e:
        raise LoiNguoiDung(400, str(e)) from None


def chay_lai_kiem_tra_dot(ma):
    """Chạy lại kiểm tra đợt trên đúng file đã tải lên (sau khi ghép tay hạng mục)."""
    try:
        d = nv.doc_ket_qua_kiem_tra("kiem_tra_dot", ma)
    except FileNotFoundError:
        raise LoiNguoiDung(404, "Không có kết quả kiểm tra này") from None
    except ValueError as e:
        raise LoiNguoiDung(400, str(e)) from None
    p = d.get("duong_dan_tep") or ""
    if not os.path.isfile(p):
        raise LoiNguoiDung(404, "Không còn file hồ sơ đã tải lên — chọn lại file và kiểm tra mới")
    ma_hd, ngay, dot = d["hop_dong"]["ma_hd"], d["ngay_nghiem_thu"], d.get("dot")

    def ham(v):
        return nv.kiem_tra_dot(v, ma_hd, p, ngay, dot, duong_dan_tai)
    return QLV.tao("kiem_dot", f"Kiểm tra lại đợt {dot or ''} · {ma_hd} · {os.path.basename(p)}".replace("  ", " "),
                   ham).to_dict()


def nap_dot_da_duyet(ma, body):
    try:
        return nv.nap_dot(ma, body.get("dot"), body.get("ngay_nhan_hs"), body.get("ly_do_nap_lai", ""), body.get("ghi_chu", ""))
    except SystemExit as e:
        raise LoiNguoiDung(409, str(e)) from None
    except FileNotFoundError:
        raise LoiNguoiDung(404, "Không có kết quả kiểm tra này") from None
    except ValueError as e:
        raise LoiNguoiDung(400, str(e)) from None


def _tep_tai_len(token):
    goc = (ch.thu_muc_du_lieu() / "tai_len").resolve()
    p = (ch.thu_muc_du_lieu() / str(token or "")).resolve()
    if goc not in p.parents or not p.is_file():
        raise LoiNguoiDung(404, "Không tìm thấy file đã tải lên — chọn lại file")
    return str(p)


def _ma_tep(p):
    return "/".join(Path(p).resolve().relative_to(ch.thu_muc_du_lieu().resolve()).parts)


def boq_tai_len(ten, data):
    """BOQ Excel; hoặc PDF / Word: lấy các bảng (PDF scan → OCR ABBYY trên máy) ghi ra Excel rồi dùng chung màn hình
    ánh xạ cột."""
    p = luu_tai_len(str(thu_muc_tai_len("boq")), ten, data, (".xlsx", ".xlsm", ".xls", ".pdf", ".docx"))
    nguon = None
    if p.lower().endswith((".pdf", ".docx")):
        p, nguon = _boq_tu_van_ban(p)
    tu_xls = None
    if dx.la_xls(p):
        try:
            p, tu_xls = dx.chuan_hoa(p)
        except dx.LoiXls as e:
            raise LoiNguoiDung(400, str(e)) from None
    try:
        d = nv.boq_doc_file(p)
    except Exception as e:  # noqa: BLE001
        raise LoiNguoiDung(400, f"Không đọc được file Excel: {type(e).__name__}: {e}") from None
    d["tep"] = _ma_tep(p)
    d["ten"] = ten_an_toan(ten, (".xlsx", ".xlsm", ".xls", ".pdf", ".docx"))
    d["nguon"] = nguon
    d["tu_xls"] = tu_xls
    return _json_an_toan(d)


def _boq_tu_van_ban(p):
    """PDF/DOCX → Excel các bảng. PDF: OCR ABBYY (chế độ Tắt thì vẫn OCR vì không có cách đọc bảng khác)."""
    from trich_xuat import ocr_abbyy as ocr
    info = None
    docx = p
    if p.lower().endswith(".pdf"):
        if ocr.cau_hinh_ocr()["che_do"] == "tat":
            raise LoiNguoiDung(400, "BOQ dạng PDF cần OCR ABBYY — bật OCR trong Cài đặt, hoặc dùng file Excel.")
        try:
            docx, info = ocr.ocr_docx(p)
        except ocr.LoiOCR as e:
            raise LoiNguoiDung(400, f"Không OCR được file PDF: {e.thong_diep}") from None
    out = os.path.splitext(p)[0] + "_bang.xlsx"
    try:
        n = ocr.docx_sang_xlsx(docx, out)
    except (ValueError, KeyError, zipfile.BadZipFile) as e:
        raise LoiNguoiDung(400, str(e)) from None
    return out, {"loai": "pdf_ocr" if info else "docx", "so_bang": n,
                 "trang": (info or {}).get("trang"), "tu_luu_dem": (info or {}).get("tu_luu_dem", False)}


def boq_xem_sheet(body):
    try:
        return _json_an_toan(nv.boq_xem_sheet(_tep_tai_len(body.get("tep")), body.get("sheet")))
    except ValueError as e:
        raise LoiNguoiDung(400, str(e)) from None


def _boq_tham_so(body):
    if not body.get("ma_hd"):
        raise LoiNguoiDung(400, "Chọn hợp đồng nhận BOQ")
    try:
        hang = int(body.get("hang_tieu_de") or 0)
    except ValueError:
        raise LoiNguoiDung(400, "Dòng tiêu đề phải là số") from None
    if hang < 1:
        raise LoiNguoiDung(400, "Chọn dòng tiêu đề của bảng")
    return _tep_tai_len(body.get("tep")), body.get("sheet"), hang, body.get("cot") or {}, body["ma_hd"]


def boq_kiem_tra(body):
    try:
        return nv.boq_kiem_tra(*_boq_tham_so(body))
    except ValueError as e:
        raise LoiNguoiDung(400, str(e)) from None


def boq_ghi(body):
    try:
        return nv.boq_ghi(*_boq_tham_so(body), ly_do=body.get("ly_do", ""),
                          chap_nhan_lech=bool(body.get("chap_nhan_lech")))
    except SystemExit as e:
        raise LoiNguoiDung(409, str(e)) from None
    except ValueError as e:
        raise LoiNguoiDung(409, str(e)) from None


def chi_tiet_phu_luc(ref, so_pl):
    cs, con = _csdl()
    try:
        hd = cs.tim_hd(con, ref)
        pls = con.execute("SELECT * FROM phu_luc WHERE ma_hd = ? AND so_pl = ? ORDER BY id DESC", (hd["ma_hd"], so_pl)).fetchall()
        if not pls:
            raise LoiNguoiDung(404, f"Không có {so_pl}")
        pl = pls[0]
        ts = [_hd_dict(r) for r in con.execute("SELECT * FROM thay_doi_tham_so WHERE pl_id = ?", (pl["id"],))]
        boq = [_hd_dict(r) for r in con.execute("SELECT * FROM boq_dong WHERE pl_id = ? ORDER BY id", (pl["id"],))]
        cb = [_hd_dict(r) for r in con.execute("SELECT * FROM canh_bao WHERE pl_id = ? ORDER BY id", (pl["id"],))]
        nk = [_hd_dict(r) for r in con.execute("SELECT * FROM nhat_ky WHERE ma_hd = ? AND chi_tiet LIKE ? ORDER BY id",
                                               (hd["ma_hd"], f"%{so_pl}%"))]
        return _json_an_toan({"phu_luc": _hd_dict(pl), "thay_doi_tham_so": ts, "boq": boq, "canh_bao": cb, "nhat_ky": nk,
                              "lan_truoc": [_hd_dict(p) for p in pls[1:]]})
    finally:
        con.close()


# ================================================================== tổng quan
def tong_quan():
    luot = ds_luot(20)
    out = {"ai": trang_thai_ai(), "viec_dang_chay": [v.to_dict() for v in QLV.dang_chay()],
           "viec_gan_day": nv.viec_gan_day(luot), "can_xem_xet": nv.can_xem_xet(),
           "so_o_can_xem": sum(x["so_vang"] for x in luot if x.get("tt") != "loi"), "csdl": None,
           "dot_cho_duyet": [d for d in nv.ds_ket_qua_kiem_tra("kiem_tra_dot", 10) if not d.get("da_nap")]}
    if ch.file_csdl().exists():
        try:
            cs, con = _csdl()
            try:
                thang = datetime.date.today().strftime("%Y-%m")
                out["csdl"] = {
                    "so_hop_dong": con.execute("SELECT COUNT(*) FROM hop_dong").fetchone()[0],
                    "moi_trong_thang": con.execute("SELECT COUNT(*) FROM hop_dong WHERE ngay_nap LIKE ?",
                                                   (thang + "%",)).fetchone()[0],
                    "so_phu_luc": con.execute("SELECT COUNT(*) FROM phu_luc WHERE trang_thai <> 'Đã hủy'").fetchone()[0],
                    "phu_luc_co_do": con.execute("SELECT COUNT(DISTINCT pl_id) FROM canh_bao WHERE muc_do = 'ĐỎ' AND "
                                                 "pl_id IS NOT NULL").fetchone()[0],
                    "so_dot": con.execute("SELECT COUNT(*) FROM dot_thanh_toan").fetchone()[0],
                    "tham_so_chua_xac_nhan": con.execute(
                        "SELECT COUNT(*) FROM tham_so_nguon WHERE da_xac_nhan = 0 AND (kiem_tra IS NULL OR "
                        "kiem_tra NOT LIKE 'OK%')").fetchone()[0]}
            finally:
                con.close()
        except LoiNguoiDung as e:
            out["csdl_loi"] = e.thong_bao
    return _json_an_toan(out)


def xoa_luot_bo_nho(luot):
    """Dọn lượt đã xong khỏi bộ nhớ (kết quả vẫn trên đĩa)."""
    lc = LUOT.get(luot)
    if lc and lc.s.get("tt") not in ("dang_chay", "cho"):
        LUOT.pop(luot, None)


def xoa_luot(luot):
    d = _thu_muc_luot(luot)
    if luot in LUOT and LUOT[luot].s.get("tt") in ("dang_chay", "cho"):
        raise LoiNguoiDung(409, "Lượt đang chạy — bấm Dừng trước")
    LUOT.pop(luot, None)
    if d.exists():
        shutil.rmtree(d)
    return {"ok": True}


# ================================================================== trích phụ lục từ file Word / PDF (Local AI)
def la_claude(cfg=None):
    return (cfg or ch.doc_cau_hinh()).get("nguon_ai") == "claude"


def _cloud_nguon(cfg):
    c = cfg["cloud"]
    ncc = (c.get("nha_cung_cap") or "anthropic").lower()
    return {"nha_cung_cap": ncc, "model": c.get("model") or ch.CLOUD_MODEL_MAC_DINH.get(ncc, "")}


def _may_cloud(v, loai):
    """Nguồn AI = Claude: MayCloud kèm nhật ký gửi ngoài (ket_qua/gui_ra_ngoai/<ngày>/GUI_RA_NGOAI_*.txt)."""
    from trich_xuat.ai_cloud import MayCloud
    cfg = ch.doc_cau_hinh()
    n = _cloud_nguon(cfg)
    if not ch.doc_khoa(n["nha_cung_cap"]):
        v.log(f"Nguồn AI là Claude nhưng chưa có API key {n['nha_cung_cap']}")
        return None
    d = ch.thu_muc_ket_qua() / "gui_ra_ngoai" / time.strftime("%Y%m%d")
    return MayCloud(n["nha_cung_cap"], n["model"], ghi_log=v.log, dung=v.dung,
                    nhat_ky=str(d / f"GUI_RA_NGOAI_{time.strftime('%Y%m%d_%H%M%S')}_{loai}.txt"))


def _may_ai_viec(v, loai="viec"):
    cfg = ch.doc_cau_hinh()
    if la_claude(cfg):
        return _may_cloud(v, loai)
    try:
        tags = MayAI(cfg["may_ai"], cfg["model"]).models(timeout=5)
        if cfg["model"] not in tags and f"{cfg['model']}:latest" not in tags:
            v.log(f"Máy AI chưa có model {cfg['model']}")
            return None
    except Exception as e:  # noqa: BLE001
        v.log(f"Không kết nối được máy AI: {type(e).__name__}")
        return None
    return MayAI(cfg["may_ai"], cfg["model"], timeout=cfg.get("timeout_giay", 1800), ghi_log=v.log, dung=v.dung)


def pl_ai_tai_len(ten, data):
    p = luu_tai_len(str(thu_muc_tai_len("phu_luc_file")), ten, data, (".docx", ".doc", ".pdf"))
    return {"tep": _ma_tep(p), "ten": os.path.basename(p)}


def pl_ai_chay(body):
    from . import phu_luc_ai as pa
    teps = [_tep_tai_len(t) for t in (body.get("tep") or [])]
    if not teps:
        raise LoiNguoiDung(400, "Chưa có file phụ lục nào được tải lên")

    def ham(v):
        ai = _may_ai_viec(v, "phu_luc")
        if ai is None:
            v.log("Chạy không có AI: chỉ trích theo quy tắc (thông tin chung, bảng, giá trị)")
        ds, loi = [], []
        for i, p in enumerate(teps):
            if v.dung.is_set():
                break
            ten = os.path.basename(p)
            v.tien_do(i / len(teps), f"{ten} ({i + 1}/{len(teps)})")
            try:
                kq = pa.trich_phu_luc(p, ai=ai, dung=v.dung, ghi_log=v.log,
                                      tien_do=lambda x, m, i=i: v.tien_do((i + x) / len(teps), m))
                ds.append(kq["id"])
            except Exception as e:  # noqa: BLE001
                from trich_xuat.ai_local import DaDung
                if isinstance(e, DaDung):
                    break
                msg = e.thong_diep if hasattr(e, "thong_diep") else f"{type(e).__name__}: {e}"
                loi.append({"ten": ten, "loi": msg})
                v.log(f"Lỗi {ten}: {msg}")
        v.tien_do(1.0, f"Xong {len(ds)}/{len(teps)} phụ lục" + (f" · {len(loi)} lỗi" if loi else ""))
        return {"ds": ds, "loi": loi}
    ten = os.path.basename(teps[0]) + (f" và {len(teps) - 1} file khác" if len(teps) > 1 else "")
    return QLV.tao("phu_luc", f"Trích phụ lục · {ten}", ham, dung_ai=True).to_dict()


def pl_ai_ds():
    from . import phu_luc_ai as pa
    return {"ds": pa.danh_sach(), "che_do_boq": pa.CHE_DO_BOQ}


def _pl_ai_goi(fn, *a):
    try:
        return _json_an_toan(fn(*a))
    except KeyError as e:
        raise LoiNguoiDung(404, str(e).strip("'\"")) from None
    except (ValueError, SystemExit) as e:
        raise LoiNguoiDung(409, str(e)) from None


def pl_ai_xem(id_):
    from . import phu_luc_ai as pa
    return _pl_ai_goi(pa.doc, id_)


def pl_ai_cap_nhat(id_, body):
    from . import phu_luc_ai as pa
    return _pl_ai_goi(pa.cap_nhat, id_, body)


def pl_ai_nap(id_):
    from . import phu_luc_ai as pa
    return _pl_ai_goi(pa.nap, id_)


def pl_ai_xoa(id_):
    from . import phu_luc_ai as pa
    _pl_ai_goi(pa.xoa, id_)
    return {"ok": True}


def pl_ai_hoi_lai(id_):
    from . import phu_luc_ai as pa
    _pl_ai_goi(pa.doc, id_)

    def ham(v):
        ai = _may_ai_viec(v, "phu_luc")
        if ai is None:
            raise SystemExit("Nguồn AI chưa sẵn sàng — kiểm tra Cài đặt → Máy AI / Nguồn AI")
        v.tien_do(0.2, f"Hỏi {getattr(ai, 'ten', 'Local AI')}: tham số phụ lục sửa đổi")
        try:
            kq = pa.hoi_lai_ai(id_, ai, ghi_log=v.log)
        except (ValueError, KeyError) as e:
            raise SystemExit(str(e).strip("'\"")) from None
        v.tien_do(1.0, f"Xong: {len(kq['tham_so'])} tham số, {len(kq['khac'])} thay đổi khác")
        return {"id": id_}
    return QLV.tao("phu_luc", "Hỏi lại AI · phụ lục", ham, dung_ai=True).to_dict()


# ================================================================== Lớp 3: chứng từ của đợt
def ct_tai_len(ten, data):
    from . import chung_tu as ct
    p = luu_tai_len(str(thu_muc_tai_len("chung_tu")), ten, data, ct.DUOI)
    return {"tep": _ma_tep(p), "ten": os.path.basename(p)}


def ct_chay(body):
    from . import chung_tu as ct
    teps = [_tep_tai_len(t) for t in (body.get("tep") or [])]
    if not teps:
        raise LoiNguoiDung(400, "Chưa có chứng từ nào được tải lên")
    if not (body.get("them_vao") or body.get("ma_kq") or (body.get("ma_hd") and body.get("ngay_nt"))):
        raise LoiNguoiDung(400, "Chọn một lần Kiểm tra đợt, hoặc hợp đồng + ngày nghiệm thu")

    def ham(v):
        ai = _may_ai_viec(v, "chung_tu")
        if ai is None:
            v.log("Chạy không có AI: chứng từ không có bảng sẽ không đọc được dòng hàng")
        try:
            kq = ct.tao_bo(body, teps, ai=ai, dung=v.dung, ghi_log=v.log, tien_do=lambda p, m: v.tien_do(p, m))
        except (ValueError, KeyError) as e:
            raise SystemExit(str(e).strip("'\"")) from None
        return {"id": kq["id"], "so_tai_lieu": len(kq["tai_lieu"]), "loi": kq.get("loi") or []}
    return QLV.tao("chung_tu", f"Chứng từ · {len(teps)} file", ham, dung_ai=True).to_dict()


def ct_ds():
    from . import chung_tu as ct
    return {"ds": ct.danh_sach(), "loai": ct.LOAI}


def ct_xem(id_):
    from . import chung_tu as ct
    return _pl_ai_goi(ct.doc, id_)


def ct_cap_nhat(id_, body):
    from . import chung_tu as ct
    return _pl_ai_goi(ct.cap_nhat, id_, body)


def ct_xoa(id_):
    from . import chung_tu as ct
    _pl_ai_goi(ct.xoa, id_)
    return {"ok": True}
