# -*- coding: utf-8 -*-
"""
doi_xls.py — file Excel 97-2003 (.xls) → .xlsx, để mọi bước đọc Excel (openpyxl) dùng chung một đường.

Thứ tự cách chuyển (giữ được công thức thì Lớp 1 — toàn vẹn công thức, liên kết, số gõ tay — mới có ý nghĩa):
  1. Microsoft Excel trên máy này (Windows, gọi qua PowerShell): giữ công thức, liên kết ngoài, sheet ẩn; tắt macro,
     không cập nhật liên kết, mở chỉ đọc;
  2. LibreOffice (soffice --headless) nếu có cài: giữ công thức;
  3. thư viện xlrd: CHỈ giá trị (mất công thức) — đủ cho Import BOQ, phiếu phụ lục, chứng từ; KHÔNG dùng cho kiểm tra
     đợt / toàn vẹn (sẽ báo lỗi, hướng dẫn mở bằng Excel rồi Lưu thành .xlsx).
File đuôi .xls nhưng thực chất là .xlsx (đổi đuôi) → chỉ đổi lại đuôi.
File .xlsx viết ra nằm cạnh file gốc (cùng thư mục tải lên), file .xls gốc giữ nguyên để truy vết.
"""
import base64
import os
import shutil
import subprocess
import tempfile

OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
DANH_DAU_CHI_GIA_TRI = "chuyen-tu-xls-chi-gia-tri"   # ghi vào thuộc tính keywords của file .xlsx do xlrd tạo


class LoiXls(Exception):
    pass


def la_xls(path):
    return str(path).lower().endswith(".xls")


def loai_that(path):
    with open(path, "rb") as f:
        dau = f.read(512)
    if dau.startswith(b"PK"):
        return "xlsx"
    if dau.startswith(OLE):
        return "xls"
    t = dau.lstrip(b"\xef\xbb\xbf \r\n\t").lower()
    if t.startswith((b"<", b"<?xml")) or b"<html" in t or b"<table" in t:
        return "html"
    return "khac"


def _dich(path):
    goc = os.path.splitext(path)[0]
    out, i = goc + ".xlsx", 1
    while os.path.exists(out):
        out, i = f"{goc}_{i}.xlsx", i + 1
    return out


def _hop_le(out):
    try:
        with open(out, "rb") as f:
            return f.read(2) == b"PK"
    except OSError:
        return False


_PS = r"""
$ErrorActionPreference = 'Stop'
$x = $null; $wb = $null
try {
  $x = New-Object -ComObject Excel.Application
  $x.Visible = $false; $x.DisplayAlerts = $false; $x.AskToUpdateLinks = $false; $x.EnableEvents = $false
  try { $x.AutomationSecurity = 3 } catch {}
  $wb = $x.Workbooks.Open($env:XLS_NGUON, 0, $true)
  $wb.SaveAs($env:XLS_DICH, 51)
  $wb.Close($false); $wb = $null
} finally {
  if ($wb -ne $null) { try { $wb.Close($false) } catch {} }
  if ($x -ne $null) { try { $x.Quit() } catch {}; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($x) }
}
"""


def _bang_excel(path, out, timeout):
    if os.name != "nt" or not shutil.which("powershell"):
        return "không phải Windows"
    lenh = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand",
            base64.b64encode(_PS.encode("utf-16-le")).decode("ascii")]
    env = dict(os.environ, XLS_NGUON=os.path.abspath(path), XLS_DICH=os.path.abspath(out))
    try:
        r = subprocess.run(lenh, env=env, capture_output=True, text=True, errors="replace", timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return f"Excel không chuyển xong trong {timeout} giây"
    except OSError as e:
        return f"không gọi được PowerShell ({e})"
    if _hop_le(out):
        return None
    loi = (r.stderr or r.stdout or "").strip().splitlines()
    return "máy không có Microsoft Excel" if any("80040154" in x or "ComObject" in x for x in loi) else \
        "Excel báo lỗi: " + (loi[0][:200] if loi else "không rõ")


def _tim_soffice():
    for ten in ("soffice", "soffice.com", "libreoffice"):
        p = shutil.which(ten)
        if p:
            return p
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.isfile(p):
            return p
    return None


def _bang_libreoffice(path, out, timeout):
    so = _tim_soffice()
    if not so:
        return "chưa cài LibreOffice"
    tam = tempfile.mkdtemp(prefix="xls_")
    ho_so = tempfile.mkdtemp(prefix="lo_")
    try:
        nguon = os.path.join(tam, "nguon.xls")
        shutil.copyfile(path, nguon)
        r = subprocess.run([so, f"-env:UserInstallation={'file:///' + ho_so.replace(os.sep, '/').lstrip('/')}",
                            "--headless", "--norestore", "--convert-to", "xlsx", "--outdir", tam, nguon],
                           capture_output=True, text=True, errors="replace", timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ra = os.path.join(tam, "nguon.xlsx")
        if _hop_le(ra):
            shutil.move(ra, out)
            return None
        return "LibreOffice báo lỗi: " + ((r.stderr or r.stdout or "").strip()[:200] or "không rõ")
    except subprocess.TimeoutExpired:
        return f"LibreOffice không chuyển xong trong {timeout} giây"
    except OSError as e:
        return f"không chạy được LibreOffice ({e})"
    finally:
        shutil.rmtree(tam, ignore_errors=True)
        shutil.rmtree(ho_so, ignore_errors=True)


def _bang_xlrd(path, out):
    try:
        import xlrd
    except ImportError:
        return "chưa có thư viện xlrd"
    import openpyxl
    try:
        book = xlrd.open_workbook(path, on_demand=True)
    except Exception as e:  # noqa: BLE001
        return f"xlrd không đọc được ({type(e).__name__}: {e})"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    try:
        for i in range(book.nsheets):
            sh = book.sheet_by_index(i)
            ws = wb.create_sheet(sh.name[:31])
            ws.sheet_state = {1: "hidden", 2: "veryHidden"}.get(getattr(sh, "visibility", 0), "visible")
            for r in range(sh.nrows):
                for c in range(sh.ncols):
                    loai, v = sh.cell_type(r, c), sh.cell_value(r, c)
                    if loai in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR):
                        continue
                    if loai == xlrd.XL_CELL_DATE:
                        try:
                            v = xlrd.xldate_as_datetime(v, book.datemode)
                        except Exception:  # noqa: BLE001
                            pass
                    elif loai == xlrd.XL_CELL_NUMBER and float(v).is_integer():
                        v = int(v)
                    elif loai == xlrd.XL_CELL_BOOLEAN:
                        v = bool(v)
                    ws.cell(r + 1, c + 1, v)
            book.unload_sheet(i)
    finally:
        book.release_resources()
    if not any(ws.sheet_state == "visible" for ws in wb.worksheets):
        wb.worksheets[0].sheet_state = "visible"
    wb.properties.keywords = DANH_DAU_CHI_GIA_TRI
    wb.save(out)
    return None


def chi_gia_tri(path):
    """File .xlsx này do xlrd chuyển từ .xls (không còn công thức)?"""
    if not str(path).lower().endswith(".xlsx"):
        return False
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        k = wb.properties.keywords or ""
        wb.close()
        return DANH_DAU_CHI_GIA_TRI in k
    except Exception:  # noqa: BLE001
        return False


def chuan_hoa(path, can_cong_thuc=False, timeout=180, ghi_log=None):
    """File .xls → đường dẫn .xlsx tương đương (file khác: trả nguyên). can_cong_thuc=True: bắt buộc giữ công thức
    (kiểm tra đợt / toàn vẹn) — không có Excel / LibreOffice thì báo lỗi thay vì chuyển chỉ giá trị.
    Trả (đường dẫn, cách chuyển | None)."""
    if not la_xls(path):
        return path, None
    log = ghi_log or (lambda m: None)
    loai = loai_that(path)
    out = _dich(path)
    if loai == "xlsx":                       # .xlsx bị đổi đuôi thành .xls
        shutil.copyfile(path, out)
        return out, "đổi đuôi (file thực chất là .xlsx)"
    if loai not in ("xls", "html"):
        raise LoiXls(f"{os.path.basename(path)} không phải file Excel hợp lệ")
    ly_do = []
    for ten, ham in (("Microsoft Excel", lambda: _bang_excel(path, out, timeout)),
                     ("LibreOffice", lambda: _bang_libreoffice(path, out, timeout))):
        log(f"Chuyển {os.path.basename(path)} sang .xlsx bằng {ten}…")
        loi = ham()
        if loi is None:
            return out, ten
        ly_do.append(f"{ten}: {loi}")
    if can_cong_thuc:
        raise LoiXls("Không chuyển được file .xls mà vẫn giữ công thức (" + "; ".join(ly_do) + "). Kiểm tra toàn vẹn cần "
                     "công thức gốc: mở file bằng Excel → File → Save As → Excel Workbook (.xlsx) rồi tải file .xlsx lên.")
    if loai == "xls":
        loi = _bang_xlrd(path, out)
        if loi is None:
            return out, "xlrd (chỉ giá trị, không còn công thức)"
        ly_do.append(f"xlrd: {loi}")
    raise LoiXls("Không đọc được file .xls (" + "; ".join(ly_do) + "). Mở file bằng Excel → Save As → Excel Workbook "
                 "(.xlsx) rồi tải lại.")
