# -*- coding: utf-8 -*-
"""
ocr_abbyy.py — Nhận dạng chữ PDF scan bằng ABBYY FineReader Hot Folder chạy NGAY TRÊN MÁY (không gửi ra ngoài).

Phần mềm có thư mục OCR riêng (mặc định <thư mục phần mềm>\\ocr): tạo một task Hot Folder theo dõi `ocr\\in`,
lưu kết quả Microsoft Word (.docx) vào `ocr\\out`, chạy định kỳ (Recurring – every minute), Original files = Delete.

Mỗi lần OCR: ghi file vào `ocr\\tam` rồi chuyển nguyên khối sang `ocr\\in\\<mã>.pdf` (ABBYY không thấy file ghi dở) →
chờ `ocr\\out\\<mã>.docx` đứng yên và là DOCX hợp lệ → "nhận" bằng cách đổi tên sang `ocr\\nhan` (thất bại nếu ABBYY
còn ghi) → đọc → xoá mọi file của mã đó. Kết quả lưu đệm theo SHA-1 trong <dữ liệu>\\ocr_abbyy\\ để không tốn lại
trang (hạn mức giấy phép ABBYY 5.000 trang / 30 ngày). Không ghi nội dung tài liệu vào nhật ký.

    docx, info = ocr_docx("scan.pdf", tien_do=print)      # DOCX + {trang, giay, tu_luu_dem}
    can, ly_do = can_ocr_pdf("hop_dong.pdf")              # theo chế độ: tu_dong (chỉ PDF scan) / luon / tat
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time
import zipfile
from pathlib import Path

from . import cau_hinh as ch

CHE_DO = ("tu_dong", "luon", "tat")
TEN_CHE_DO = {"tu_dong": "Tự động — chỉ PDF scan (không có lớp chữ)", "luon": "Luôn OCR mọi file PDF",
              "tat": "Tắt"}
THU_MUC_CON = {"in": "in", "out": "out", "tam": "tam", "nhan": "nhan"}
HAN_MUC, CUA_SO_NGAY = 5000, 30
_TU_LOI = ("error", "failed", "cannot", "unable", "lỗi", "không thể")
_MA_RE = re.compile(r"^(hd\d{14}_[0-9a-f]{6})")

_KHOA = threading.Lock()          # mỗi lần chỉ đưa 1 tài liệu vào Hot Folder (đáng tin nhất)
_tt_cache = {"t": 0.0, "v": None}


class LoiOCR(Exception):
    def __init__(self, ma, thong_diep):
        super().__init__(thong_diep)
        self.ma = ma
        self.thong_diep = thong_diep


# ------------------------------------------------------------------ cấu hình, thư mục
def thu_muc_mac_dinh():
    return ch.GOC / "ocr"


def cau_hinh_ocr():
    o = dict(ch.doc_cau_hinh().get("ocr") or {})
    che_do = o.get("che_do") if o.get("che_do") in CHE_DO else "tu_dong"

    def so(k, md, lo, hi):
        try:
            return max(lo, min(hi, int(o.get(k) or md)))
        except (TypeError, ValueError):
            return md
    tm = str(o.get("thu_muc") or "").strip()
    return {"che_do": che_do, "thu_muc": tm or str(thu_muc_mac_dinh()), "mac_dinh": not tm,
            "cho_toi_da": so("cho_toi_da", 1800, 60, 7200), "cho_nhan": so("cho_nhan", 300, 60, 3600)}


def thu_muc(o=None, tao=True):
    o = o or cau_hinh_ocr()
    goc = Path(o["thu_muc"])
    d = {k: goc / v for k, v in THU_MUC_CON.items()}
    if tao:
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
    return d


def _ma_moi():
    return "hd" + time.strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(3)


def _xoa(p):
    try:
        os.unlink(p)
    except OSError:
        pass


def _quet(p):
    try:
        return list(os.scandir(p))
    except OSError:
        return []


# ------------------------------------------------------------------ sổ đếm trang (chỉ của phần mềm này)
def _file_so():
    return ch.thu_muc_du_lieu() / "ocr_abbyy" / "so_trang.json"


def so_trang_da_dung():
    try:
        ds = json.loads(_file_so().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ds = []
    moc = time.time() - CUA_SO_NGAY * 86400
    ds = [x for x in ds if x[0] >= moc]
    return sum(int(x[1]) for x in ds), ds


def _ghi_so(trang):
    _, ds = so_trang_da_dung()
    ds.append([time.time(), int(trang)])
    p = _file_so()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ds), encoding="utf-8")


def dem_trang(data):
    """Số trang PDF (pypdf / pdfplumber nếu có, không thì đếm /Type /Page). Ảnh: 1."""
    if not data.startswith(b"%PDF"):
        return 1
    try:
        import io
        import pypdf
        return len(pypdf.PdfReader(io.BytesIO(data)).pages)
    except Exception:  # noqa: BLE001
        pass
    return max(1, len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data)))


# ------------------------------------------------------------------ log Hot Folder
def _doc_chu(p):
    raw = Path(p).read_bytes()[-200_000:]
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or raw.count(b"\x00") > len(raw) // 4:
        if len(raw) % 2:
            raw = raw[1:]
        for enc in ("utf-16", "utf-16-le"):
            try:
                return raw.decode(enc, errors="replace")
            except UnicodeError:
                continue
    return raw.decode("utf-8-sig", errors="replace")


def _cac_log(output_dir):
    return sorted((e for e in _quet(output_dir) if e.is_file() and e.name.lower().endswith((".txt", ".log"))
                   and not _MA_RE.match(e.name.lower())), key=lambda e: e.stat().st_mtime)


def doc_log_task(output_dir):
    """Đọc khối cấu hình mới nhất trong log Hot Folder ở thư mục out:
    {input, output, luu: [docx, …]}. Không có log → {}."""
    for e in reversed(_cac_log(output_dir)):
        try:
            t = _doc_chu(e.path)
        except OSError:
            continue
        khoi = "INPUT FOLDER" + t.split("INPUT FOLDER")[-1] if "INPUT FOLDER" in t else t
        kq = {"input": "", "output": "", "luu": [], "log": e.name}
        for ln in khoi.splitlines():
            u = ln.upper()
            if "INPUT FOLDER" in u and ":" in ln:
                kq["input"] = ln.split(":", 1)[1].strip()
            elif "OUTPUT FOLDER" in u and ":" in ln:
                kq["output"] = ln.split(":", 1)[1].strip()
            elif "SAVE AS" in u:
                for x in re.findall(r"\(\*\.(\w+)\)", ln):
                    if x.lower() not in kq["luu"]:
                        kq["luu"].append(x.lower())
        if kq["input"] or kq["luu"]:
            return kq
    return {}


def dinh_dang_task(output_dir):
    return doc_log_task(output_dir).get("luu", [])


def _cung_thu_muc(a, b):
    na = os.path.normcase(os.path.normpath(str(a or "").strip().rstrip("\\/")))
    nb = os.path.normcase(os.path.normpath(str(b or "").strip().rstrip("\\/")))
    return bool(na) and na == nb


def hotfolder_dang_chay():
    if os.name != "nt":
        return None
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq HotFolder.exe", "/NH"], capture_output=True, text=True,
                           timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return "hotfolder.exe" in r.stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return None


# ------------------------------------------------------------------ trạng thái (Cài đặt)
def trang_thai(lam_moi=False):
    if not lam_moi and _tt_cache["v"] and time.time() - _tt_cache["t"] < 15:
        return _tt_cache["v"]
    o = cau_hinh_ocr()
    v = {"che_do": o["che_do"], "ten_che_do": TEN_CHE_DO[o["che_do"]], "thu_muc": o["thu_muc"], "mac_dinh": o["mac_dinh"],
         "cho_toi_da": o["cho_toi_da"], "cho_nhan": o["cho_nhan"], "input_dir": "", "output_dir": "", "task": {},
         "checks": [], "ok": False, "loi": "", "canh_bao": [],
         "usage": {"used_pages": 0, "limit": HAN_MUC, "window_days": CUA_SO_NGAY, "remaining": HAN_MUC}}

    def add(ten, ok, chi_tiet=""):
        v["checks"].append({"check": ten, "ok": ok, "detail": chi_tiet})
    try:
        d = thu_muc(o)
        v["input_dir"], v["output_dir"] = str(d["in"]), str(d["out"])
        for k in ("in", "out", "tam", "nhan"):
            try:
                pr = d[k] / f".thu_{secrets.token_hex(3)}"
                pr.write_bytes(b"ok")
                pr.unlink()
                add(f"Thư mục {k} ghi được", True)
            except OSError as e:
                add(f"Thư mục {k} ghi được", False, str(e))
        chay = hotfolder_dang_chay()
        add("ABBYY Hot Folder đang chạy", chay is not False,
            "Không kiểm tra được trên hệ điều hành này" if chay is None else
            "" if chay else "Không thấy HotFolder.exe — mở ABBYY Hot Folder, task phải ở trạng thái Watching / Scheduled")
        tk = doc_log_task(d["out"])
        v["task"] = tk
        if not tk:
            add("Task đã chạy lần nào (có log trong thư mục out)", None,
                "Chưa thấy log — bình thường khi mới tạo task; bấm Chạy thử 1 trang để kiểm tra")
        else:
            add("Task theo dõi đúng thư mục in", _cung_thu_muc(tk.get("input"), d["in"]),
                f"log: {tk.get('input') or '?'}")
            if tk.get("output"):
                add("Task lưu kết quả vào đúng thư mục out", _cung_thu_muc(tk["output"], d["out"]), f"log: {tk['output']}")
            if tk.get("luu"):
                add("Task lưu Microsoft Word (.docx)", "docx" in tk["luu"], f"đang lưu: {', '.join(tk['luu'])}")
        now = time.time()
        ket = [e.name for e in _quet(d["in"]) if e.is_file() and _MA_RE.match(e.name.lower())
               and now - e.stat().st_mtime > o["cho_nhan"]]
        add("Không có file kẹt trong thư mục in", not ket,
            f"{len(ket)} file chờ quá {o['cho_nhan']} giây → task có thể đang dừng" if ket else "")
        la = [e.name for e in _quet(d["in"]) if e.is_file() and not _MA_RE.match(e.name.lower())
              and not e.name.startswith(".")]
        if la:
            v["canh_bao"].append(f"Thư mục in có {len(la)} file không do phần mềm đưa vào — thư mục này chỉ để phần mềm dùng.")
        dung, _ = so_trang_da_dung()
        v["usage"] = {"used_pages": dung, "limit": HAN_MUC, "window_days": CUA_SO_NGAY, "remaining": max(0, HAN_MUC - dung)}
        if dung >= 0.9 * HAN_MUC:
            v["canh_bao"].append(f"Phần mềm đã OCR {dung} trang trong {CUA_SO_NGAY} ngày (hạn mức ABBYY {HAN_MUC} trang, "
                                 "tính chung cho mọi task trên máy).")
        v["ok"] = all(c["ok"] is not False for c in v["checks"])
    except Exception as e:  # noqa: BLE001
        v["loi"] = f"{type(e).__name__}: {e}"
    _tt_cache.update(t=time.time(), v=v)
    return v


# ------------------------------------------------------------------ quyết định OCR
def la_pdf_scan(path):
    """True nếu PDF không có lớp chữ đủ dùng (bản scan) hoặc máy chưa có thư viện đọc PDF."""
    from .doc_hop_dong import read_pdf
    try:
        read_pdf(path)
        return False
    except (ValueError, RuntimeError):
        return True


def can_ocr_pdf(path):
    """(có OCR không, lý do) theo chế độ trong Cài đặt."""
    if not str(path).lower().endswith(".pdf"):
        return False, ""
    o = cau_hinh_ocr()
    if o["che_do"] == "tat":
        return False, "OCR đang tắt"
    if o["che_do"] == "luon":
        return True, "Cài đặt: luôn OCR file PDF"
    if la_pdf_scan(path):
        return True, "PDF scan (không có lớp chữ)"
    return False, "PDF có lớp chữ"


def thu_muc_luu_dem():
    p = ch.thu_muc_du_lieu() / "ocr_abbyy"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _docx_hop_le(p):
    try:
        with zipfile.ZipFile(p) as z:
            return "word/document.xml" in z.namelist() and z.testzip() is None
    except (OSError, zipfile.BadZipFile, ValueError):
        return False


# ------------------------------------------------------------------ một lần OCR qua Hot Folder
def _rut(d, ma, duoi):
    """Rút file khỏi in nếu ABBYY chưa nhận. True = rút được (chưa tính trang)."""
    src, dst = d["in"] / f"{ma}.{duoi}", d["tam"] / f"{ma}.rut"
    try:
        os.replace(src, dst)
    except OSError:
        return False
    _xoa(dst)
    return True


def _don(d, ma):
    for k in ("in", "tam", "nhan", "out"):
        for e in _quet(d[k]):
            if e.name.lower().startswith(ma):
                _xoa(e.path)


def _don_sau(output_dir, ma, giay=120):
    """Xoá file kết quả đến muộn của mã (vd task lưu thêm PDF) — chỉ file mang đúng mã."""
    def don():
        for e in _quet(output_dir):
            if e.name.lower().startswith(ma):
                _xoa(e.path)
    tm = threading.Timer(giay, don)
    tm.daemon = True
    tm.start()


def _loi_trong_log(d, ma, t_bat_dau):
    for e in _cac_log(d["out"]):
        try:
            if e.stat().st_mtime < t_bat_dau - 5:
                continue
            t = _doc_chu(e.path)
        except OSError:
            continue
        for ln in t.splitlines():
            low = ln.lower()
            if ma in low and any(w in low for w in _TU_LOI):
                return ln.strip()[:300]
    return None


def _chay_hot_folder(data, duoi, o, tien_do=None, huy=None, nghi=1.0, on_dinh=2.0):
    """Đưa 1 tài liệu qua Hot Folder; trả (docx bytes, mã, số giây). Lỗi → LoiOCR."""
    from .ai_local import DaDung
    d = thu_muc(o)
    ma = _ma_moi()
    part = d["tam"] / f"{ma}.{duoi}.part"
    with open(part, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    vao = d["in"] / f"{ma}.{duoi}"
    try:
        os.replace(part, vao)
    except OSError:                                  # khác ổ đĩa
        tmp = d["in"] / f"{ma}.{duoi}.part"
        tmp.write_bytes(data)
        os.replace(tmp, vao)
        _xoa(part)
    t0 = time.time()
    da_nhan, theo_doi, quet_log = False, {}, 0.0
    try:
        while True:
            if huy is not None and huy.is_set():
                _rut(d, ma, duoi)
                raise DaDung()
            now = time.time()
            if not vao.exists() and not da_nhan:
                da_nhan = True
                if tien_do:
                    tien_do("OCR ABBYY: Hot Folder đã nhận file, đang nhận dạng chữ…")
            for e in _quet(d["out"]):
                ten = e.name.lower()
                if not (ten.startswith(ma) and ten.endswith(".docx") and e.is_file()):
                    continue
                if not da_nhan:
                    da_nhan = True
                try:
                    st = e.stat()
                except OSError:
                    continue
                ky = (st.st_size, st.st_mtime_ns)
                cu = theo_doi.get(e.path)
                if cu is None or cu[0] != ky:
                    theo_doi[e.path] = (ky, now)
                    continue
                if now - cu[1] < on_dinh or not _docx_hop_le(e.path):
                    continue
                dich = d["nhan"] / f"{ma}.docx"
                try:
                    os.replace(e.path, dich)         # Windows: thất bại nếu ABBYY còn mở file
                except OSError:
                    continue
                return dich.read_bytes(), ma, now - t0
            if vao.exists() and not da_nhan and now - t0 > o["cho_nhan"]:
                if _rut(d, ma, duoi):
                    raise LoiOCR("PICKUP_TIMEOUT",
                                 f"ABBYY Hot Folder không nhận file sau {o['cho_nhan']} giây. Kiểm tra: đã tạo task theo dõi "
                                 f"{d['in']} và lưu .docx vào {d['out']}, task đang chạy (Watching / mỗi phút), "
                                 "máy đang đăng nhập Windows, còn hạn mức trang của ABBYY.")
                da_nhan = True                           # ABBYY đang giữ file
            if now - quet_log >= 5:
                quet_log = now
                ln = _loi_trong_log(d, ma, t0)
                if ln:
                    raise LoiOCR("JOB_FAILED", f"ABBYY báo lỗi: {ln}")
            if now - t0 > o["cho_toi_da"]:
                _rut(d, ma, duoi)
                raise LoiOCR("JOB_TIMEOUT", f"Quá {o['cho_toi_da']} giây chưa có file Word kết quả trong {d['out']}. "
                                            "Kiểm tra task Hot Folder có bước Save results → Microsoft Word (.docx).")
            time.sleep(nghi)
    finally:
        _don(d, ma)
        _don_sau(d["out"], ma)


def ocr_docx(path, tien_do=None, dung=None, ghi_log=None):
    """PDF/ảnh → DOCX bằng ABBYY. Trả (đường dẫn DOCX, info). Lỗi → LoiOCR; bấm Dừng → DaDung."""
    from .ai_local import DaDung
    data = Path(path).read_bytes()
    sha = hashlib.sha1(data).hexdigest()
    dem = thu_muc_luu_dem()
    out, meta = dem / f"{sha}.docx", dem / f"{sha}.json"
    if out.exists() and _docx_hop_le(out):
        try:
            info = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        info.update(tu_luu_dem=True, sha1=sha)
        if tien_do:
            tien_do(f"OCR ABBYY: dùng lại kết quả đã nhận dạng ({info.get('trang', '?')} trang)")
        return str(out), info
    duoi = "pdf" if data.startswith(b"%PDF") else Path(path).suffix.lower().lstrip(".")
    if duoi not in ("pdf", "tif", "tiff", "jpg", "jpeg", "png", "bmp"):
        raise LoiOCR("INVALID_INPUT", "Chỉ OCR được PDF hoặc ảnh scan.")
    o = cau_hinh_ocr()
    trang = dem_trang(data)
    ten = os.path.basename(str(path))
    if tien_do and _KHOA.locked():
        tien_do("OCR ABBYY: chờ tài liệu khác OCR xong…")
    with _KHOA:
        if dung is not None and dung.is_set():
            raise DaDung()
        if tien_do:
            tien_do(f"OCR ABBYY: đã đưa {trang} trang vào thư mục Hot Folder — chờ ABBYY nhận (≤ 1 phút)")
        docx, ma, giay = _chay_hot_folder(data, duoi, o, tien_do=tien_do, huy=dung)
    tmp = out.with_suffix(".tmp")
    tmp.write_bytes(docx)
    os.replace(tmp, out)
    _ghi_so(trang)
    info = {"ten": ten, "trang": trang, "giay": round(giay, 1), "ma": ma, "ngay": time.strftime("%Y-%m-%d %H:%M:%S")}
    meta.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    if ghi_log:
        ghi_log(f"  OCR ABBYY: {trang} trang, {giay:.0f}s (mã {ma})")
    _tt_cache["v"] = None
    info.update(tu_luu_dem=False, sha1=sha)
    return str(out), info


def chuan_bi_pdf(path, tien_do=None, dung=None, ghi_log=None):
    """Hợp đồng/phụ lục PDF: cần OCR thì trả (DOCX, info); không thì (path, None)."""
    can, ly_do = can_ocr_pdf(path)
    if not can:
        return path, None
    if tien_do:
        tien_do(f"OCR ABBYY ({ly_do})")
    docx, info = ocr_docx(path, tien_do=tien_do, dung=dung, ghi_log=ghi_log)
    info["ly_do"] = ly_do
    return docx, info


def pdf_thu():
    """PDF 1 trang có chữ để chạy thử task (đúng cấu trúc: xref, font Helvetica)."""
    noi = b"BT /F1 28 Tf 72 720 Td (OCR TEST 2026 - Ban kiem soat) Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(noi) + noi + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % k for k in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    return out


def chay_thu(tien_do=None, dung=None):
    """Chạy thử task với PDF 1 trang (tốn 1 trang). Trả {giay, chu}."""
    o = cau_hinh_ocr()
    with _KHOA:
        docx, ma, giay = _chay_hot_folder(pdf_thu(), "pdf", o, tien_do=tien_do, huy=dung)
    _ghi_so(1)
    _tt_cache["v"] = None
    import io
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(io.BytesIO(docx)) as z:
        chu = "".join(ET.fromstring(z.read("word/document.xml")).itertext())
    return {"giay": round(giay, 1), "chu": chu[:120], "ma": ma}


# ------------------------------------------------------------------ DOCX → bảng (BOQ)
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _chu_o(el):
    out = []
    for x in el.iter():
        if x.tag == f"{_W}t" and x.text:
            out.append(x.text)
        elif x.tag in (f"{_W}tab", f"{_W}br", f"{_W}cr"):
            out.append(" ")
        elif x.tag == f"{_W}p" and out and out[-1] != " ":
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _bang(tbl):
    """Bảng Word → danh sách dòng (đã trải gridSpan; ô gộp dọc để trống)."""
    rows = []
    for tr in tbl.findall(f"{_W}tr"):
        r = []
        for tc in tr.findall(f"{_W}tc"):
            pr = tc.find(f"{_W}tcPr")
            span, vcont = 1, False
            if pr is not None:
                gs = pr.find(f"{_W}gridSpan")
                if gs is not None:
                    try:
                        span = max(1, int(gs.get(f"{_W}val") or 1))
                    except ValueError:
                        span = 1
                vm = pr.find(f"{_W}vMerge")
                vcont = vm is not None and (vm.get(f"{_W}val") or "continue") == "continue"
            r.append("" if vcont else _chu_o(tc))
            r.extend([""] * (span - 1))
        if any(r):
            rows.append(r)
    return rows


def docx_bang(docx):
    """(đoạn văn đầu tài liệu, [bảng]) — bảng là list dòng. Bảng lồng trong bảng bỏ qua."""
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(docx) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{_W}body")
    dau, bangs = [], []
    for el in (body if body is not None else []):
        if el.tag == f"{_W}p":
            t = _chu_o(el)
            if t and not bangs and len(dau) < 12:
                dau.append(t)
        elif el.tag == f"{_W}tbl":
            b = _bang(el)
            if b:
                bangs.append(b)
    return dau, bangs


def _khoa_dong(r):
    return re.sub(r"\W+", "", " ".join(r).lower())


def docx_sang_xlsx(docx, out_xlsx):
    """Ghi các bảng của DOCX ra Excel để dùng lại màn hình Import BOQ. Bảng liên tiếp cùng số cột (BOQ ngắt trang)
    gộp vào một sheet, bỏ dòng tiêu đề lặp lại. Đầu mỗi sheet chép các dòng đầu văn bản (để nhận số hợp đồng).
    Ô giữ nguyên chữ (đọc số kiểu 1.234,5 lúc import). Trả số sheet."""
    import openpyxl
    dau, bangs = docx_bang(docx)
    if not bangs:
        raise ValueError("Không thấy bảng nào trong file (sau OCR). Kiểm tra bản scan hoặc dùng file Excel.")
    nhom = []
    for b in bangs:
        n = max(len(r) for r in b)
        if nhom and nhom[-1]["n"] == n:
            tieu_de = _khoa_dong(nhom[-1]["dong"][0])
            nhom[-1]["dong"].extend(r for i, r in enumerate(b) if not (i == 0 and _khoa_dong(r) == tieu_de))
        else:
            nhom.append({"n": n, "dong": list(b)})
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for i, g in enumerate(nhom, 1):
        ws = wb.create_sheet(f"Bảng {i}")
        for t in dau[:8]:
            ws.append([t])
        if dau:
            ws.append([])
        for r in g["dong"]:
            ws.append([c if c != "" else None for c in r])
    wb.save(out_xlsx)
    return len(nhom)


def so_vn(v):
    """Số viết kiểu Việt Nam ('1.234.567', '5.221,560', '0,08', '(1.000)') → float; không phải số → None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    am = False
    if s.startswith("(") and s.endswith(")"):
        am, s = True, s[1:-1]
    if s[:1] in ("-", "–", "−"):
        am, s = True, s[1:]
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):
        x = float(s.replace(".", "").replace(",", "."))
    elif re.fullmatch(r"\d+,\d+", s):
        x = float(s.replace(",", "."))
    elif re.fullmatch(r"\d{1,3}(,\d{3}){2,}(\.\d+)?", s) or re.fullmatch(r"\d{1,3},\d{3}\.\d+", s):
        x = float(s.replace(",", ""))
    elif re.fullmatch(r"\d+(\.\d+)?", s):
        x = float(s)
    else:
        return None
    return -x if am else x
