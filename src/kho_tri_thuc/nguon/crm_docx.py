"""CRM-41-03 — renderer tối thiểu cho G2/G3: DOCX từ mẫu CFO đã duyệt (G1 `{{…}}`) + DOCX báo giá; DOCX → PDF bằng Word COM do chính tiến trình
này sở hữu; kiểm PDF bằng PDFium + pdfplumber. Không phải engine/renderer mới: dùng lại thuật toán đã biết từ 5 reference chỉ đọc
`docs/CRM-DOCGEN-REFERENCE-20261021/docgen/` (giữ byte-exact, không import/chạy reference):

- `mau.py` (H 9e74874f…5116294): load/save chỉ bằng bytes (python-docx `Document(BytesIO)` → `save(BytesIO)`) + thay theo bản đồ run TRONG MỘT
  đoạn, giữ định dạng của run chứa đầu ô (`_thay_trong_doan`). Adapter hữu hạn cho G1: KHÔNG regex `${}`/precheck của reference, KHÔNG thay
  toàn cục; chỉ thay ĐÚNG các lần xuất hiện mà facts G1 đã ghi (phần/đoạn/khoảng ký tự) theo bản đồ đã kiểm/duyệt. Không điều kiện/lặp/chữ
  ký/QR (ngoài ngữ pháp CRM đã duyệt).
- `loc.py` (H bb5eb168…eb91859a) + `so_chu.py` (H 989353b7…ded133aa): định dạng hiển thị SAU khi giá trị đã typed/validate — số tiền theo
  ĐÚNG scale của tiền tệ (không cắt phần lẻ làm rounding), bằng chữ từ đúng số tiền typed.
- `pdf.py` (H fb09237e…4a7e14e): chỉ khái niệm interface DOCX→PDF; thực thi bằng Word COM theo binding đã ghim (không LibreOffice, không
  TemporaryDirectory/cleanup, không wrapper tiến trình gốc).

Word COM chỉ được import trong worker (`python -m kho_tri_thuc.nguon.crm_docx --word-worker`), không ở import module/khởi động dịch vụ.
FIX02 (binding `CRM-41-03-WORD-OWNERSHIP-FIX02.md`): worker tạo WINWORD ghim bằng CreateProcessW(`/w`, SUSPENDED, SW_HIDE) → gán Job riêng + kiểm
danh tính TRƯỚC ResumeThread → chỉ sau đó mới import/khởi tạo COM, lấy Word.Window qua NativeOM của cửa sổ `_WwG` thuộc ĐÚNG PID, roundtrip
Window.Hwnd → PID. Không DispatchEx/GetObject/ROT/tiêu đề/so PID trước-sau làm bằng chứng. Mọi nhánh dừng bằng handle/Job đã sở hữu, có
bằng chứng dừng hữu hạn hoặc UNKNOWN.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from ..ha_tang.primitives import DataError

PHIEN_BAN_RENDERER = "crm.docx-runmap/1+word-com/2"  # FIX02: Word do worker tạo suspended + Job + chứng minh NativeOM (binding FIX02)
REFERENCE = {"mau.py": "9e74874ffaa92488f569a2d6c30f4013a9b762b0ff99b86f83f4a7e815116294",
             "pdf.py": "fb09237ec74eee67be911a3fc31861421a5dfa048fe9a5ac0c348abf64a7e14e",
             "loc.py": "bb5eb16884048415680c547e2a01ab8506dcb510661cc45248852ee7eb91859a",
             "so_chu.py": "989353b78bfb14a106f136787f0b490d46a77ef27e83a23a125c002fded133aa",
             "requirements.txt": "3947d743d7a6572e91c481237a8e253960aa2cda915dced301967d02f6bb0a24"}
WINWORD_GHIM = Path("C:/Program Files/Microsoft Office/root/Office16/WINWORD.EXE")
WINWORD_SHA256 = "0f96d6172dd6cc9eda5ddb786fee5d8f9c8b4bee96f56db2dab6f5888f3be882"
SCALE = {"VND": 0, "USD": 2}
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W_STRICT = "http://purl.oclc.org/ooxml/wordprocessingml/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
KIEU_WORKER_PID, KIEU_WORKER_XONG = "crm_word_pid/v1", "crm_word_xong/v1"


class LoiRender(DataError):
    """Lỗi render có cấu trúc (không bao giờ thành 'xuất thành công')."""


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ================================================================================================== định dạng hiển thị (sau typed/validate)
def _nhom_nghin(nguyen: int) -> str:
    return f"{nguyen:,}".replace(",", ".")


def so_hien_thi(gia_tri: Decimal | Fraction, le: int) -> str:
    """Số thập phân CHÍNH XÁC với đúng `le` chữ số lẻ (quy ước VN: nhóm nghìn '.', thập phân ','). Giá trị cần nhiều chữ số lẻ hơn → lỗi
    (không cắt/làm tròn như reference `dinh_dang_tien`)."""
    f = Fraction(gia_tri)
    if (f * 10 ** le).denominator != 1:
        raise LoiRender("CRM_GK_SO_KHONG_DUNG_SCALE", "Giá trị cần nhiều chữ số lẻ hơn scale của tiền tệ/định dạng — không làm tròn.")
    am, f = f < 0, abs(f)
    nguyen = f.numerator // f.denominator
    s = _nhom_nghin(nguyen)
    if le > 0:
        le_int = int((f - nguyen) * 10 ** le)
        s += "," + str(le_int).rjust(le, "0")
    return ("-" if am else "") + s


def tien_hien_thi(minor: int, tien_te: str, *, kem_ma: bool = True) -> str:
    if tien_te not in SCALE or type(minor) is not int:
        raise LoiRender("CRM_GK_TIEN_TE_KHONG_HO_TRO", "Tiền tệ chưa hỗ trợ hiển thị.")
    s = so_hien_thi(Fraction(minor, 10 ** SCALE[tien_te]), SCALE[tien_te])
    return f"{s} {tien_te}" if kem_ma else s


def ngay_hien_thi(iso: str, dinh_dang: str) -> str:
    if not isinstance(iso, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso):
        raise LoiRender("CRM_GK_NGAY_SAI", "Ngày phải là YYYY-MM-DD.")
    y, m, d = iso.split("-")
    if dinh_dang == "dd/MM/yyyy":
        return f"{d}/{m}/{y}"
    if dinh_dang == "NGAY_DU":
        return f"ngày {d} tháng {m} năm {y}"
    raise LoiRender("CRM_GK_DINH_DANG_KHONG_HO_TRO", f"Định dạng ngày '{dinh_dang}' chưa hỗ trợ.")


# --- bằng chữ: thuật toán của reference so_chu.py (đệ quy theo mốc tỷ), nhận ĐÚNG số tiền typed (đơn vị chính, chính xác)
_CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
_TY = 10 ** 9
_NHOM = ["", " nghìn", " triệu"]


def _ba(tram, chuc, dv, day_du):
    p = []
    if tram > 0:
        p.append(f"{_CHU_SO[tram]} trăm")
    elif day_du and (chuc > 0 or dv > 0):
        p.append("không trăm")
    if chuc > 1:
        p.append(f"{_CHU_SO[chuc]} mươi")
        p.append({1: "mốt", 4: "tư", 5: "lăm"}.get(dv, _CHU_SO[dv] if dv > 0 else ""))
    elif chuc == 1:
        p.append("mười")
        if dv == 5:
            p.append("lăm")
        elif dv > 0:
            p.append(_CHU_SO[dv])
    elif dv > 0:
        if tram > 0 or day_du:
            p.append("lẻ")
        p.append(_CHU_SO[dv])
    return " ".join(x for x in p if x)


def _duoi_ty(n, day_du):
    nhom, con = [], n
    while con > 0:
        nhom.append(con % 1000)
        con //= 1000
    p, cao = [], len(nhom) - 1
    for i in range(cao, -1, -1):
        if nhom[i] == 0:
            continue
        p.append(_ba(nhom[i] // 100, (nhom[i] // 10) % 10, nhom[i] % 10, day_du or i != cao) + _NHOM[i])
    return " ".join(p)


def _doc(n, day_du):
    if n < _TY:
        return _duoi_ty(n, day_du)
    chu = _doc(n // _TY, day_du) + " tỷ"
    if n % _TY:
        chu += " " + _duoi_ty(n % _TY, True)
    return chu


def bang_chu(minor: int, tien_te: str) -> str:
    if tien_te not in SCALE or type(minor) is not int or minor < 0 or minor >= 10 ** 21:
        raise LoiRender("CRM_GK_BANG_CHU", "Không đọc được số tiền thành chữ (tiền tệ/miền).")
    f = Fraction(minor, 10 ** SCALE[tien_te])
    nguyen = f.numerator // f.denominator
    chu = "không" if nguyen == 0 else re.sub(r"\s+", " ", _doc(nguyen, False)).strip()
    le = f - nguyen
    if le:
        s = str(int(le * 10 ** SCALE[tien_te])).rjust(SCALE[tien_te], "0").rstrip("0")
        chu += " phẩy " + " ".join(_CHU_SO[int(c)] for c in s)
    don_vi = {"VND": "đồng", "USD": "đô la Mỹ"}[tien_te]
    return chu[0].upper() + chu[1:] + " " + don_vi


# ================================================================================================== DOCX từ mẫu G1 (adapter run-map hữu hạn)
def _q(t: str) -> str:
    return f"{{{W}}}{t}"


def _doan_theo_thu_tu(goc, out: list) -> None:
    """Thứ tự đoạn GIỐNG bộ đọc G1 (`_quet_phan.di`): mọi w:p theo thứ tự tài liệu, kể cả trong bảng/bảng lồng; đoạn ghi trước khi đi vào con."""
    for con in goc:
        if not isinstance(con.tag, str):
            continue
        if con.tag == _q("p"):
            out.append(con)
        _doan_theo_thu_tu(con, out)


def _wt_cua_doan(p) -> list:
    """w:t có chữ thuộc CHÍNH đoạn (không vào đoạn lồng/hộp văn bản) — đúng traversal `_doan` của bộ đọc G1."""
    ds, ngan = [], [iter(list(p))]
    while ngan:
        el = next(ngan[-1], None)
        if el is None:
            ngan.pop()
            continue
        if not isinstance(el.tag, str) or el.tag in (_q("p"), _q("txbxContent")):
            continue
        if el.tag == _q("r"):
            ds.extend(t for t in el if isinstance(t.tag, str) and t.tag == _q("t") and t.text)
            continue
        ngan.append(iter(list(el)))
    return ds


def _thay_trong_doan(wts: list, bat_dau: int, ket_thuc: int, thay: str) -> None:
    """Reference mau._thay_trong_doan ở mức w:t: thay khoảng [bat_dau, ket_thuc) bằng `thay`, giữ định dạng của run chứa ĐẦU ô."""
    moc, vt = [], 0
    for t in wts:
        moc.append(vt)
        vt += len(t.text or "")
    i = next(k for k in range(len(wts)) if moc[k] <= bat_dau < moc[k] + len(wts[k].text or ""))
    j = next(k for k in range(len(wts)) if moc[k] <= ket_thuc - 1 < moc[k] + len(wts[k].text or ""))
    si, sj = wts[i].text, wts[j].text
    if i == j:
        wts[i].text = si[:bat_dau - moc[i]] + thay + si[ket_thuc - moc[i]:]
    else:
        wts[i].text = si[:bat_dau - moc[i]] + thay
        for k in range(i + 1, j):
            wts[k].text = ""
        wts[j].text = sj[ket_thuc - moc[j]:]
    for k in range(i, j + 1):
        wts[k].set(XML_SPACE, "preserve")


def dien_mau(raw: bytes, facts: dict, ban_do: list, gia_tri: dict) -> tuple[bytes, dict]:
    """Điền mẫu đã duyệt: mỗi lần xuất hiện (facts G1) → trường theo bản đồ đã kiểm (ban_do theo thu_tu, tên ô KHÔNG cần trùng mã trường) →
    chuỗi hiển thị đã typed trong `gia_tri[ma_truong]`. Kiểm lại văn bản đoạn/khoảng với facts trước khi thay; lệch/thiếu ánh xạ/phần chưa hỗ trợ
    → LoiRender (không xuất giả). Trả (bytes DOCX đã chuẩn bị, báo cáo)."""
    import docx  # python-docx (binding: 1.2.0)
    if facts.get("trang_thai") != "DU":
        raise LoiRender("CRM_GK_MAU_CHUA_DU", "Mẫu đọc chưa đủ (kênh chưa hỗ trợ/Track Changes) — không xuất.")
    occ = facts.get("occurrences") or []
    theo_thu_tu = {int(o["thu_tu"]): o for o in ban_do}
    if len(theo_thu_tu) != len(occ):
        raise LoiRender("CRM_GK_ANH_XA_LECH", "Bản đồ ánh xạ không khớp số lần xuất hiện của mẫu.")
    doc = docx.Document(io.BytesIO(raw))
    phan = {str(p.partname).lstrip("/"): p for p in doc.part.package.iter_parts()}
    doan_theo_chi_so, dem = {}, 0
    for pq in facts.get("phan_quet") or []:
        part = phan.get(pq["ten"])
        goc = getattr(part, "_element", None) if part is not None else None
        if goc is None:
            raise LoiRender("CRM_GK_PHAN_KHONG_HO_TRO", f"Phần {pq['ten']} không mở được bằng bộ ghi DOCX.")
        if not str(goc.tag).startswith("{" + W + "}"):
            raise LoiRender("CRM_GK_PHAN_KHONG_HO_TRO", "Mẫu dùng không gian tên OOXML chưa hỗ trợ (strict).")
        ds: list = []
        _doan_theo_thu_tu(goc, ds)
        for p in ds:
            dem += 1
            doan_theo_chi_so[dem] = (pq["ten"], p)
    van_ban_facts = {d["chi_so"]: d for d in facts.get("doan") or []}
    nhom: dict[int, list] = {}
    bao_cao = {"so_o": len(occ), "truong_trong": [], "renderer": PHIEN_BAN_RENDERER}
    for k, o in enumerate(occ, start=1):
        bd = theo_thu_tu.get(k)
        if bd is None or bd.get("ten") != o["ten"] or not bd.get("truong"):
            raise LoiRender("CRM_GK_O_CHUA_ANH_XA", f"Ô {{{{{o['ten']}}}}} (lần {k}) chưa ánh xạ đúng trường — không xuất.")
        if bd["truong"] not in gia_tri:
            raise LoiRender("CRM_GK_THIEU_GIA_TRI", f"Trường {bd['truong']} chưa có giá trị đã typed.")
        nhom.setdefault(int(o["doan"]), []).append((o, gia_tri[bd["truong"]], bd["truong"]))
    for chi_so, ds_o in nhom.items():
        if chi_so not in doan_theo_chi_so:
            raise LoiRender("CRM_GK_MAU_LECH_FACTS", "Không thấy đoạn mà facts G1 ghi nhận — tệp/facts lệch.")
        ten_phan, p = doan_theo_chi_so[chi_so]
        wts = _wt_cua_doan(p)
        van_ban = "".join(t.text for t in wts)
        f = van_ban_facts.get(chi_so)
        if f is None or f["phan"] != ten_phan or (not f.get("cat_bot") and f["van_ban"] != van_ban):
            raise LoiRender("CRM_GK_MAU_LECH_FACTS", "Văn bản đoạn khác facts G1 — không thay mù.")
        for o, gt, truong in sorted(ds_o, key=lambda x: x[0]["bat_dau"], reverse=True):
            if van_ban[o["bat_dau"]:o["ket_thuc"]] != o["van_ban_o"]:
                raise LoiRender("CRM_GK_MAU_LECH_FACTS", "Khoảng ô khác facts G1 — không thay mù.")
            if gt == "":
                bao_cao["truong_trong"].append(truong)
            _thay_trong_doan(wts, o["bat_dau"], o["ket_thuc"], gt)
    ra = io.BytesIO()
    doc.save(ra)
    out = ra.getvalue()
    bao_cao["kiem"] = kiem_docx_chuan_bi(out)
    bao_cao["truong_trong"] = sorted(set(bao_cao["truong_trong"]))
    return out, bao_cao


def kiem_docx_chuan_bi(raw: bytes) -> dict:
    """Kiểm OPC của DOCX ĐÃ chuẩn bị TRƯỚC Word bằng chính bộ đọc G1 (fail-closed macro/ActiveX/OLE/quan hệ ngoài/altChunk/DTD; trường
    DDE/LINK/INCLUDETEXT/fldSimple/hộp văn bản → INCOMPLETE): phải DU và không còn ô `{{…}}` nào."""
    from .mau_docx import doc_mau_docx
    f = doc_mau_docx(raw)
    if f["trang_thai"] != "DU":
        raise LoiRender("CRM_GK_DOCX_KENH_CHUA_HO_TRO", "DOCX đã chuẩn bị còn kênh chưa hỗ trợ: " + ", ".join(sorted({x["ma"] for x in f["ly_do_chua_du"]})))
    if f["placeholders"]:
        raise LoiRender("CRM_GK_DOCX_CON_O", "DOCX đã chuẩn bị còn ô chưa thay.")
    return {"raw_sha256": f["raw_sha256"], "byte_length": f["byte_length"], "phan": [p["ten"] for p in f["phan_quet"]]}


# ================================================================================================== DOCX báo giá cho khách (dữ liệu typed)
def tao_docx_bao_gia(nd: dict) -> bytes:
    """Bản báo giá cho khách: số/ngày/người lập, khách, đơn vị, giá theo tiền tệ khai, lịch 4 cột, câu tham chiếu FX (khi có), phí bảo trì (khi có),
    điều khoản tham chiếu đã khai theo loại hình. KHÔNG giá vốn/lãi/vết duyệt/mã nội bộ/định danh hệ thống."""
    import docx
    from docx.oxml.ns import qn
    from docx.shared import Pt
    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Times New Roman", Pt(12)
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rf)
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(k), "Times New Roman")

    def dong(*manh, dam=False):
        p = d.add_paragraph()
        for m in manh:
            r = p.add_run(m)
            r.bold = dam
        return p
    dong("BÁO GIÁ", dam=True)
    dong(f"Số: {nd['so_bao_gia']}")
    dong(f"Ngày: {nd['ngay']}")
    dong(f"Người lập: {nd['nguoi_lap']}")
    if nd.get("het_han"):
        dong(f"Hiệu lực báo giá đến: {nd['het_han']}")
    dong(f"Kính gửi: {nd['khach']}")
    for nhan, gt in nd.get("thong_tin") or []:
        dong(f"{nhan}: {gt}")
    dong("Lịch thanh toán", dam=True)
    t = d.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    for i, h in enumerate(("Lần", "Giá trị", "Mốc thời gian", "Ghi chú")):
        t.rows[0].cells[i].text = h
    for r in nd.get("lich") or []:
        o = t.add_row().cells
        for i in range(4):
            o[i].text = r[i]
    if nd.get("fx_cau"):
        dong(nd["fx_cau"])
    if nd.get("phi_bao_tri"):
        dong(nd["phi_bao_tri"])
    for dk in nd.get("dieu_khoan") or []:
        dong(dk)
    ra = io.BytesIO()
    d.save(ra)
    return ra.getvalue()


# ================================================================================================== DOCX → PDF bằng Word COM (worker sở hữu)
def _winword_ok(winword: Path) -> str | None:
    if os.name != "nt":
        return "KHONG_PHAI_WINDOWS"
    if not winword.is_file():
        return "WORD_KHONG_CO"
    h = hashlib.sha256()
    with open(winword, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return None if h.hexdigest() == WINWORD_SHA256 else "WORD_KHAC_BAN_GHIM"


_KHOA_WORD = threading.Lock()  # một lần chuyển Word mỗi tiến trình máy chủ: bằng chứng "PID mới duy nhất" không bị lần chuyển song song làm mơ hồ


def chuyen_pdf(thu_muc_lan: Path, docx_path: Path, *, han: float = 180.0, winword: Path = WINWORD_GHIM) -> dict:
    """DOCX đã chuẩn bị (nằm trong thư mục lần chạy riêng, tạo mới) → PDF mới cùng thư mục. Chỉ worker do lần gọi này sở hữu (Job gán TRƯỚC
    stdin) chạm Word, và chỉ Word instance nó chứng minh sở hữu. Trả {trang_thai: PDF_DA_TAO|PDF_CHUA_SAN_SANG|PDF_LOI, ly_do, pha, word}.
    Không xóa/ghi đè/đổi tên tệp nào; không giả PDF. Các lần chuyển trong cùng tiến trình được tuần tự hóa (hạn chờ hữu hạn)."""
    if not _KHOA_WORD.acquire(timeout=max(1.0, han)):
        return {"trang_thai": "PDF_CHUA_SAN_SANG", "ly_do": "WORD_DANG_BAN", "pha": "CHO_LUOT"}
    try:
        return _chuyen_pdf_mot(Path(thu_muc_lan), Path(docx_path), han, winword)
    finally:
        _KHOA_WORD.release()


def _chuyen_pdf_mot(thu_muc_lan: Path, docx_path: Path, han: float, winword: Path) -> dict:
    from .trich6_host import LoiHost, _JobWindows, _doc_dong, chung_cu_guard, env_con, guard_hop_le
    thu_muc_lan, docx_path = Path(thu_muc_lan), Path(docx_path)
    ly_do = _winword_ok(winword)
    if ly_do:
        return {"trang_thai": "PDF_CHUA_SAN_SANG", "ly_do": ly_do, "pha": "KIEM_NHA_CUNG_CAP"}
    ma_guard = guard_hop_le(chung_cu_guard())
    if ma_guard:
        return {"trang_thai": "PDF_CHUA_SAN_SANG", "ly_do": ma_guard, "pha": "KIEM_GUARD"}
    pdf = thu_muc_lan / (docx_path.stem + ".pdf")
    if pdf.exists() or docx_path.parent.resolve() != thu_muc_lan.resolve():
        return {"trang_thai": "PDF_LOI", "ly_do": "DUONG_DAN_LAN_KHONG_MOI", "pha": "KIEM_DUONG_DAN"}
    job = proc = None
    word, xong, pha, gan, loi = {}, None, "SPAWN", False, None
    try:
        try:
            job = _JobWindows()
            proc = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "kho_tri_thuc.nguon.crm_docx", "--word-worker"], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=str(thu_muc_lan), env=env_con(), close_fds=True,
                                    creationflags=0x08000000)
            pha = "GAN_JOB"
            job.gan(proc)  # Job TRƯỚC khi worker nhận đường dẫn/cấu hình; chưa gán → không ghi stdin
            gan = True
            pha = "CAU_HINH"
            cfg = {"goc": str(thu_muc_lan.resolve()), "vao": str(docx_path.resolve()), "vao_sha256": _sha(docx_path.read_bytes()),
                   "ra": str(pdf), "winword": str(winword), "winword_sha256": WINWORD_SHA256, "han_cua_so": max(5.0, min(60.0, han / 3))}
            proc.stdin.write((json.dumps(cfg, ensure_ascii=False) + "\n").encode("utf-8"))
            proc.stdin.flush()
            het = time.monotonic() + han
            pha = "CHO_WORKER"
            while time.monotonic() < het:
                dong = _doc_dong(proc.stdout, max(0.1, het - time.monotonic()))
                if not dong:
                    break  # EOF hoặc hết hạn
                kieu, v = _doc_giao_thuc(dong, da_co_pid=bool(word))  # FIX03 R4: kiểm kiểu/hình dạng — sai → LoiGiaoThuc (dừng cây, không đoán)
                if kieu == KIEU_WORKER_PID:
                    word = {"pid": v["pid"], "gan_job": True}
                else:
                    xong = v
                    break
            if xong is None:
                pha = "QUA_HAN_HOAC_EOF"
        except (OSError, LoiHost, subprocess.SubprocessError, ValueError, LoiGiaoThuc) as exc:
            loi = getattr(exc, "ma", None) or f"{pha}:{type(exc).__name__}"
        except Exception as exc:  # noqa: BLE001 — FIX03 R4: ngoại lệ BẤT NGỜ vẫn đi qua dừng có bằng chứng; kết quả LUÔN là lỗi có cấu trúc
            loi = f"{pha}:NGOAI_LE_BAT_NGO:{type(exc).__name__}"
        # FIX02: MỌI nhánh (thành công/lỗi/EOF/quá hạn/ngoại lệ) đều dừng ĐÚNG cây đã sở hữu và lấy bằng chứng hữu hạn trước khi kết luận
        dung = _dung_cay(job, proc, gan, ket_thuc=xong is None or loi is not None)
        if word.get("pid") and xong is None and dung is True:
            word["da_dung"] = True if word.get("gan_job") else None  # Word là con không breakaway của worker trong Job này → Job rỗng ⇒ đã dừng
        if dung is not True:
            return {"trang_thai": "PDF_LOI", "ly_do": loi or "WORKER_CHUA_DUNG", "pha": pha, "word": word, "dung": "UNKNOWN"}
        if loi is not None:
            return {"trang_thai": "PDF_LOI", "ly_do": loi, "pha": pha, "word": word, "dung": "DA_DUNG"}
        return _ket_luan(xong, word, proc.returncode, True, pdf, pha)
    finally:
        if proc is not None:
            for s in (proc.stdin, proc.stdout):
                try:
                    if s is not None:
                        s.close()
                except OSError:
                    pass
        if job is not None:
            job.dong()  # KILL_ON_CLOSE chỉ là lưới an toàn — KHÔNG phải bằng chứng dừng


class LoiGiaoThuc(Exception):
    """FIX03 R4 — dòng giao thức worker sai kiểu/hình dạng (mã ngắn có cấu trúc, không chứa dữ liệu)."""

    def __init__(self, ma: str):
        super().__init__(ma)
        self.ma = ma


def _doc_giao_thuc(dong: bytes, *, da_co_pid: bool) -> tuple[str, dict]:
    """Kiểm MỘT dòng giao thức worker: JSON object đúng `kieu`, đúng kiểu từng trường. PID: pid int > 0 (không bool), gan_job is True, chỉ một lần.
    XONG: trang_thai ∈ {PDF_DA_TAO, LOI}; ly_do/pha None|str; word None|object (pid int nếu có; da_dung True/False/None). Sai → LoiGiaoThuc."""
    try:
        v = json.loads(dong.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise LoiGiaoThuc("GIAO_THUC_KHONG_PHAI_JSON") from None
    if not isinstance(v, dict):
        raise LoiGiaoThuc("GIAO_THUC_SAI_KIEU")
    kieu = v.get("kieu")
    if kieu == KIEU_WORKER_PID:
        pid = v.get("pid")
        if da_co_pid or type(pid) is not int or pid <= 0 or v.get("gan_job") is not True:
            raise LoiGiaoThuc("GIAO_THUC_PID_SAI")
        return kieu, v
    if kieu == KIEU_WORKER_XONG:
        w = v.get("word")
        if v.get("trang_thai") not in ("PDF_DA_TAO", "LOI") or not isinstance(v.get("ly_do"), (str, type(None))) \
                or not isinstance(v.get("pha"), (str, type(None))) or not isinstance(w, (dict, type(None))) \
                or (isinstance(w, dict) and (("pid" in w and type(w["pid"]) is not int) or w.get("da_dung", None) not in (True, False, None))):
            raise LoiGiaoThuc("GIAO_THUC_XONG_SAI")
        return kieu, v
    raise LoiGiaoThuc("GIAO_THUC_KIEU_LA")


def _dung_cay(job, proc, gan: bool, *, ket_thuc: bool, cho: float = 30.0) -> bool | None:
    """FIX02 — dừng cây tiến trình ĐÃ SỞ HỮU và trả bằng chứng: True = worker kết thúc + Job (nếu đã gán) rỗng trong hạn; None = UNKNOWN.
    Chưa gán Job → chỉ dừng đúng handle đã spawn (worker chưa nhận stdin nên chưa tạo Word). Không quét/kill theo tên/PID.
    FIX03 R4: ngoại lệ bất ngờ trong wait/truy vấn/dừng → UNKNOWN (không che, không coi là đã dừng)."""
    try:
        return _dung_cay_trong(job, proc, gan, ket_thuc=ket_thuc, cho=cho)
    except Exception:  # noqa: BLE001
        return None


def _dung_cay_trong(job, proc, gan: bool, *, ket_thuc: bool, cho: float) -> bool | None:
    from .trich6_host import LoiHost
    if proc is None:
        return True  # chưa spawn gì

    def dung_ngay():
        try:
            if gan:
                job.ket_thuc()
            else:
                proc.kill()  # TerminateProcess trên ĐÚNG handle đã spawn
        except (OSError, LoiHost):
            pass
    if ket_thuc:
        dung_ngay()
    try:
        proc.wait(cho)
    except subprocess.TimeoutExpired:
        dung_ngay()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            return None
    if not gan:
        return True
    het = time.monotonic() + 10
    while True:
        try:
            if job.so_tien_trinh() == 0:
                return True
        except LoiHost:
            return None
        if time.monotonic() >= het:
            return None
        time.sleep(0.05)


def _ket_luan(xong: dict | None, word_pid: dict, ma_thoat, job_rong: bool, pdf: Path, pha: str) -> dict:
    """FIX01 #9 — kết luận THUẦN của parent (kiểm được bằng tiêm lỗi): PDF_DA_TAO CHỈ khi worker báo thành công VÀ thoát mã 0 VÀ Job sở hữu đã rỗng
    VÀ Word sở hữu ĐÃ xác nhận dừng (`da_dung is True`) VÀ PID trong báo cáo cuối khớp PID đã chứng minh/gán Job VÀ PDF tồn tại. Thiếu bất kỳ điều
    nào → không thành công (giữ DOCX/PDF làm bằng chứng, trạng thái trung thực). Không suy Word dừng từ Job Python rỗng."""
    if not job_rong:
        return {"trang_thai": "PDF_LOI", "ly_do": "WORKER_CHUA_DUNG", "pha": pha, "word": word_pid}
    if xong is None:
        return {"trang_thai": "PDF_LOI", "ly_do": "WORKER_QUA_HAN_HOAC_EOF", "pha": pha, "word": word_pid}
    w = {**(word_pid or {}), **(xong.get("word") or {})}
    if xong.get("trang_thai") == "PDF_DA_TAO":
        if ma_thoat == 0 and w.get("da_dung") is True and word_pid.get("pid") and word_pid.get("gan_job") \
                and (xong.get("word") or {}).get("pid") == word_pid.get("pid") and Path(pdf).is_file():
            return {"trang_thai": "PDF_DA_TAO", "pdf": str(pdf), "pha": xong.get("pha"), "word": w}
        return {"trang_thai": "PDF_LOI", "ly_do": "WORD_CHUA_XAC_NHAN_DUNG", "pha": xong.get("pha"), "word": w,
                "pdf_giu": str(pdf) if Path(pdf).is_file() else None}
    tt = "PDF_CHUA_SAN_SANG" if str(xong.get("ly_do", "")).startswith(("GUARD_", "WORD_", "KHONG_SO_HUU", "COM_")) else "PDF_LOI"
    return {"trang_thai": tt, "ly_do": xong.get("ly_do") or "PDF_KHONG_TAO", "pha": xong.get("pha"), "word": w}


def _pid_con_song(pid: int) -> bool:
    import ctypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x00100000, False, int(pid))
    if not h:
        return False
    try:
        return k.WaitForSingleObject(ctypes.c_void_p(h), 0) == 0x102
    finally:
        k.CloseHandle(ctypes.c_void_p(h))


def kiem_pdf(path: Path, mong_doi: list[str]) -> dict:
    """PDF thật: chữ ký `%PDF-`, số trang > 0, văn bản Unicode không rỗng ở mọi trang qua PDFium, đối chiếu chéo pdfplumber (NFC), các chuỗi kỳ
    vọng LẤY TỪ dữ liệu typed đã chụp (không từ output), phông chữ thực trong trang, render trang. Lỗi parse/render → validation thất bại."""
    import pdfplumber
    import pypdfium2 as pdfium
    path = Path(path)
    b = path.read_bytes()
    out = {"sha256": _sha(b), "len": len(b), "ok": False}
    if not b.startswith(b"%PDF-"):
        return {**out, "loi": "KHONG_PHAI_PDF"}
    try:
        pdf = pdfium.PdfDocument(str(path))
        try:
            so_trang, chu1, render_ok = len(pdf), [], True  # FIX03 R3: số TRANG (PDFium) — tách hẳn khỏi số LẦN xuất hiện kỳ vọng
            for i in range(so_trang):
                page = pdf.get_page(i)
                tp = None
                try:
                    tp = page.get_textpage()
                    chu1.append(tp.get_text_range(errors="strict"))
                    bm = page.render()
                    try:
                        render_ok = render_ok and bm.width > 0 and bm.height > 0
                    finally:
                        bm.close()
                finally:
                    if tp is not None:
                        tp.close()
                    page.close()
        finally:
            pdf.close()
        with pdfplumber.open(str(path), unicode_norm="NFC") as p2:
            so_trang2 = len(p2.pages)
            chu2 = [pg.extract_text() or "" for pg in p2.pages]
            phong = sorted({c.get("fontname", "") for pg in p2.pages for c in pg.chars} - {""})
    except Exception as exc:  # noqa: BLE001 — lỗi parse/render là thất bại kiểm, không fallback kích thước tệp
        return {**out, "loi": f"PARSE_LOI:{type(exc).__name__}"}

    def chuan(s):
        return re.sub(r"\s+", "", unicodedata.normalize("NFC", s or ""))
    t1, t2 = chuan("".join(chu1)), chuan("".join(chu2))
    # FIX01 #12: mỗi mục kỳ vọng (chuỗi, số lần tối thiểu) — số lần = số ô của trường trong mẫu (thân/header/footer…); không bỏ giá trị ngắn
    # FIX02: các mục có CÙNG văn bản sau chuẩn hóa (NFC + bỏ khoảng trắng) được CỘNG số lần (không max/không khử trùng): hai trường cùng "0",
    # mỗi trường một ô → PDF phải có ≥ 2 lần "0".
    tong, goc_txt = {}, {}  # văn bản đã chuẩn hóa → TỔNG số lần cần (không dùng chung tên biến với số trang)
    for x in mong_doi:
        s, can = (x, 1) if isinstance(x, str) else (x[0], int(x[1]))
        c = chuan(s)
        if c:
            tong[c] = tong.get(c, 0) + can
            goc_txt.setdefault(c, s)
    thieu1 = [goc_txt[c] for c, can in tong.items() if t1.count(c) < can]
    thieu2 = [goc_txt[c] for c, can in tong.items() if t2.count(c) < can]
    ok = so_trang > 0 and so_trang == so_trang2 and all(chuan(x) for x in chu1) and render_ok and not thieu1 and not thieu2 and bool(phong)
    return {**out, "ok": ok, "so_trang": so_trang, "so_trang_pdfplumber": so_trang2, "phong": phong[:30], "thieu_pdfium": thieu1, "thieu_pdfplumber": thieu2,
            "render_ok": render_ok, "loi": None if ok else "NOI_DUNG_KHONG_DAT",
            "muc_kiem": "VAN_BAN_CO_BAN"}  # chữ/số/số lần + trang + phông có mặt + render được; KHÔNG phải fidelity bố cục/glyph/thị giác


# ================================================================================================== worker (chỉ chạy trong tiến trình con)
def _pids_winword() -> set[int]:
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    arr = (wintypes.DWORD * 8192)()
    cb = wintypes.DWORD()
    if not psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(cb)):
        raise OSError("EnumProcesses")
    out = set()
    for pid in arr[: cb.value // ctypes.sizeof(wintypes.DWORD)]:
        if _anh_tien_trinh(int(pid), k).lower().endswith("\\winword.exe"):
            out.add(int(pid))
    return out


def _anh_tien_trinh(pid: int, k=None) -> str:
    import ctypes
    from ctypes import wintypes
    k = k or ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        return buf.value if k.QueryFullProcessImageNameW(ctypes.c_void_p(h), 0, buf, ctypes.byref(n)) else ""
    finally:
        k.CloseHandle(ctypes.c_void_p(h))


def _thoi_diem_tao(h) -> float:
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    c, e, kt, u = (wintypes.FILETIME() for _ in range(4))
    if not k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(u)):
        raise OSError("GetProcessTimes")
    return ((c.dwHighDateTime << 32) + c.dwLowDateTime) / 1e7 - 11644473600.0


# ================================================================================================== FIX02: Word do CHÍNH tiến trình này tạo + sở hữu
CLASS_CUA_SO_TAI_LIEU = "_WwG"  # cửa sổ tài liệu Word (NativeOM trả Word.Window)
OBJID_NATIVEOM = 0xFFFFFFF0
LENH_WORD = '"{ww}" /w'  # đúng binary + MỘT switch /w (instance mới với tài liệu trống); không đường dẫn tài liệu/shell/DDE/`/a`


def _k32():
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)  # đối tượng riêng: argtypes không ảnh hưởng mã khác
    k.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
    k.CreateProcessW.restype = wintypes.BOOL
    k.ResumeThread.argtypes, k.ResumeThread.restype = [wintypes.HANDLE], wintypes.DWORD
    k.TerminateProcess.argtypes, k.TerminateProcess.restype = [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL
    k.WaitForSingleObject.argtypes, k.WaitForSingleObject.restype = [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD
    k.IsProcessInJob.argtypes, k.IsProcessInJob.restype = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)], wintypes.BOOL
    k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    k.QueryFullProcessImageNameW.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    return k


def _anh_cua_handle(k, hp) -> str:
    import ctypes
    from ctypes import wintypes
    buf, n = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
    return buf.value if k.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(n)) else ""


def _pid_cua_hwnd(hwnd) -> int:
    import ctypes
    from ctypes import wintypes
    p = wintypes.DWORD(0)
    ctypes.WinDLL("user32", use_last_error=True).GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(p))
    return int(p.value)


def _cua_so_tai_lieu(pid: int) -> list:
    """CHỈ ĐỌC: cửa sổ lớp `_WwG` (con của cửa sổ top-level) thuộc ĐÚNG `pid`. Không tìm theo tiêu đề, không FindWindow toàn cục."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.WinDLL("user32", use_last_error=True)
    PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    out = []

    def lop(h):
        b = ctypes.create_unicode_buffer(64)
        u.GetClassNameW(wintypes.HWND(h), b, 64)
        return b.value

    def con(h, _):
        if h and lop(h) == CLASS_CUA_SO_TAI_LIEU and _pid_cua_hwnd(h) == pid:
            out.append(int(h))
        return True
    cb_con = PROC(con)

    def top(h, _):
        if h and _pid_cua_hwnd(h) == pid:
            u.EnumChildWindows(wintypes.HWND(h), cb_con, 0)
        return True
    cb_top = PROC(top)
    u.EnumWindows(cb_top, 0)
    return out


def _native_window(hwnd, pythoncom):
    """AccessibleObjectFromWindow(hwnd, OBJID_NATIVEOM, IID_IDispatch) → PyIDispatch (Word.Window) hoặc None. Nhả tham chiếu thô OLEACC đã AddRef."""
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
    iid = GUID(0x00020400, 0, 0, (ctypes.c_ubyte * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))  # IID_IDispatch
    ptr = ctypes.c_void_p()
    if ctypes.WinDLL("oleacc").AccessibleObjectFromWindow(wintypes.HWND(hwnd), wintypes.DWORD(OBJID_NATIVEOM), ctypes.byref(iid),
                                                          ctypes.byref(ptr)) != 0 or not ptr.value:
        return None
    try:
        return pythoncom.ObjectFromAddress(ptr.value, pythoncom.IID_IDispatch)
    except Exception:  # noqa: BLE001
        return None
    finally:  # IUnknown::Release (vtable[2]) cho tham chiếu thô
        vt = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vt[0][2])(ptr)


class WordSoHuu:
    """Một WINWORD do CHÍNH tiến trình này tạo (CreateProcessW suspended) và sở hữu (Job riêng gán TRƯỚC ResumeThread). Dùng cho worker và
    control của native test. COM chỉ khởi tạo trong `chung_minh` (sau khi đã sở hữu + gán Job). `dung()` luôn gọi trong finally."""

    def __init__(self, winword: Path, cwd: Path):
        self.ww, self.cwd = Path(winword), Path(cwd)
        self.k = None
        self.job = self.hp = self.ht = self.pid = self.app = self.pythoncom = None
        self.gan = self.resumed = self.com = self.quit_da_goi = False

    def tao(self, t0: float) -> None:
        import ctypes
        from ctypes import wintypes
        from types import SimpleNamespace

        from .trich6_host import _JobWindows

        class SI(ctypes.Structure):  # STARTUPINFOW
            _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD), ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD),
                        ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p),
                        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

        class PI(ctypes.Structure):  # PROCESS_INFORMATION
            _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]
        self.k = _k32()
        self.job = _JobWindows()
        si, pi = SI(), PI()
        si.cb = ctypes.sizeof(SI)
        si.dwFlags, si.wShowWindow = 0x00000001, 0  # STARTF_USESHOWWINDOW + SW_HIDE (không lấy CREATE_NO_WINDOW làm bằng chứng ẩn)
        cmd = ctypes.create_unicode_buffer(LENH_WORD.format(ww=self.ww))
        if not self.k.CreateProcessW(str(self.ww), cmd, None, None, False, 0x00000004, None, str(self.cwd), ctypes.byref(si), ctypes.byref(pi)):
            raise RuntimeError(f"WORD_TAO_LOI:{ctypes.get_last_error()}")  # CREATE_SUSPENDED
        self.hp, self.ht, self.pid = pi.hProcess, pi.hThread, int(pi.dwProcessId)
        self.job.gan(SimpleNamespace(_handle=self.hp))  # Job TRƯỚC ResumeThread (handle do chính CreateProcessW trả)
        self.gan = True
        trong = wintypes.BOOL(0)
        if not self.k.IsProcessInJob(self.hp, self.job._h, ctypes.byref(trong)) or not trong.value:
            raise RuntimeError("KHONG_SO_HUU:JOB_KHONG_CHUA_WORD")
        if _thoi_diem_tao(ctypes.c_void_p(self.hp)) < t0 - 1.0 or \
                os.path.normcase(_anh_cua_handle(self.k, self.hp)) != os.path.normcase(str(self.ww.resolve())):
            raise RuntimeError("KHONG_SO_HUU:DANH_TINH_TIEN_TRINH")
        if self.k.ResumeThread(self.ht) == 0xFFFFFFFF:
            raise RuntimeError("WORD_RESUME_LOI")
        self.resumed = True

    def con_song(self) -> bool:
        return bool(self.hp) and self.k.WaitForSingleObject(self.hp, 0) == 0x102

    def cho_cua_so(self, han: float) -> list:
        het = time.monotonic() + max(0.0, han)
        while time.monotonic() < het:
            if not self.con_song():
                return []
            ds = _cua_so_tai_lieu(self.pid)
            if ds:
                return ds
            time.sleep(0.1)
        return []

    def chung_minh(self, hwnds: list) -> bool:
        """Chỉ sau khi đã sở hữu + gán Job: khởi tạo COM (STA) và lấy Word.Window từ `_WwG` của ĐÚNG PID; Window.Hwnd → PID phải khớp, tiến trình
        còn sống và vẫn trong Job. True → `self.app` = Window.Application. Không DispatchEx/GetObject/ROT."""
        import ctypes
        from ctypes import wintypes

        import pythoncom
        import win32com.client
        self.pythoncom = pythoncom
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        self.com = True
        for hwnd in hwnds:
            win = _native_window(hwnd, pythoncom)
            if win is None:
                continue
            try:
                w = win32com.client.Dispatch(win)
                if _pid_cua_hwnd(int(w.Hwnd)) != self.pid or not self.con_song():
                    continue
                trong = wintypes.BOOL(0)
                if not self.k.IsProcessInJob(self.hp, self.job._h, ctypes.byref(trong)) or not trong.value:
                    continue
                self.app = w.Application
                return True
            except Exception:  # noqa: BLE001
                continue
            finally:
                win = w = None
        return False

    def dung(self) -> bool | None:
        """Dừng bằng handle/Job ĐÃ SỞ HỮU, có hạn. True = handle Word signaled VÀ Job Word rỗng; None = UNKNOWN. Chưa tạo được → True (không có Word)."""
        from .trich6_host import LoiHost
        self.app = None
        if self.com:
            try:
                self.pythoncom.CoUninitialize()
            except Exception:  # noqa: BLE001
                pass
            self.com = False
        if not self.hp:
            if self.job is not None:
                self.job.dong()
            return True
        try:
            ok = self.quit_da_goi and self.k.WaitForSingleObject(self.hp, 30000) == 0
            if not ok:
                try:
                    if self.gan:
                        self.job.ket_thuc()  # đúng Job chỉ chứa Word này
                    else:
                        self.k.TerminateProcess(self.hp, 1)  # chưa gán Job: đúng handle do CreateProcessW trả
                except (OSError, LoiHost):
                    pass
                ok = self.k.WaitForSingleObject(self.hp, 10000) == 0
            rong = True
            if self.gan:
                het = time.monotonic() + 5
                while True:
                    try:
                        if self.job.so_tien_trinh() == 0:
                            break
                    except LoiHost:
                        rong = None
                        break
                    if time.monotonic() >= het:
                        rong = None
                        break
                    time.sleep(0.05)
            return True if ok and rong is True else None
        finally:
            for h in (self.ht, self.hp):
                if h:
                    self.k.CloseHandle(h)
            self.ht = self.hp = None
            if self.job is not None:
                self.job.dong()


def _worker(stdin, kenh) -> int:
    """Một lần chuyển (binding FIX02): guard → kiểm đường dẫn/hash DOCX + binary ghim → CreateProcessW(WINWORD `/w`, SUSPENDED, SW_HIDE) → Job
    riêng + kiểm danh tính TRƯỚC ResumeThread → chờ hữu hạn `_WwG` của đúng PID → (mới) khởi tạo COM, NativeOM Window → Application, roundtrip
    Hwnd → PID → tùy chọn an toàn → mở chỉ-đọc đúng DOCX → ExportAsFixedFormat → đóng/khôi phục/Quit → dừng có bằng chứng (handle signaled + Job
    rỗng) hoặc UNKNOWN. Thành công chỉ khi Word đã xác nhận dừng. Không DispatchEx/GetObject/ROT, không đổi registry/Trust Center/Normal.dotm,
    không xóa tệp."""
    def bao(v):
        kenh.write(json.dumps(v, ensure_ascii=False) + "\n")
        kenh.flush()
    from .trich6_host import LoiHost, chung_cu_guard, guard_hop_le
    try:
        cfg = json.loads(stdin.readline(64 * 1024).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        bao({"kieu": KIEU_WORKER_XONG, "trang_thai": "LOI", "ly_do": "CAU_HINH_SAI", "pha": "CAU_HINH"})
        return 2
    ma_guard = guard_hop_le(chung_cu_guard())
    if ma_guard:
        bao({"kieu": KIEU_WORKER_XONG, "trang_thai": "LOI", "ly_do": ma_guard, "pha": "GUARD"})
        return 4
    sys.dont_write_bytecode = True
    goc, vao, ra, ww = Path(cfg["goc"]), Path(cfg["vao"]), Path(cfg["ra"]), Path(cfg["winword"])
    if goc.is_symlink() or vao.is_symlink() or goc.resolve() not in vao.resolve().parents or ra.parent.resolve() != goc.resolve() or ra.exists() \
            or _sha(vao.read_bytes()) != cfg["vao_sha256"] or _winword_ok(ww) is not None:
        bao({"kieu": KIEU_WORKER_XONG, "trang_thai": "LOI", "ly_do": "DUONG_DAN_HOAC_BINARY_SAI", "pha": "KIEM"})
        return 3
    pha, ly_do, trang_thai = "TAO_WORD", None, "LOI"
    w, doc, opt_cu, word = WordSoHuu(ww, goc), None, {}, {}
    try:
        w.tao(time.time())
        word = {"pid": w.pid, "gan_job": True}
        bao({"kieu": KIEU_WORKER_PID, "pid": w.pid, "gan_job": True})
        pha = "CHO_CUA_SO"
        hwnds = w.cho_cua_so(float(cfg.get("han_cua_so", 30)))
        if not hwnds:
            raise RuntimeError("KHONG_SO_HUU:KHONG_CO_CUA_SO_TAI_LIEU_TRONG_HAN")  # NOT_READY: không Open/COM vào đối tượng chưa chứng minh
        pha = "CHUNG_MINH_SO_HUU"
        if not w.chung_minh(hwnds):
            raise RuntimeError("KHONG_SO_HUU:CHUA_CHUNG_MINH_NATIVEOM")
        app = w.app
        pha = "TUY_CHON"
        opt_cu = {"Visible": app.Visible, "AutomationSecurity": app.AutomationSecurity, "DisplayAlerts": app.DisplayAlerts,
                  "UpdateLinksAtOpen": app.Options.UpdateLinksAtOpen}
        app.Visible = False
        app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
        app.DisplayAlerts = 0
        app.Options.UpdateLinksAtOpen = False
        pha = "MO"
        doc = app.Documents.Open(FileName=str(vao.resolve()), ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False, Visible=False,
                                 OpenAndRepair=False, NoEncodingDialog=True)
        pha = "XUAT"
        doc.ExportAsFixedFormat(OutputFileName=str(ra), ExportFormat=17, OpenAfterExport=False, Range=0, Item=0, IncludeDocProps=False)
        trang_thai = "PDF_DA_TAO" if ra.is_file() else "LOI"
        ly_do = None if ra.is_file() else "PDF_KHONG_TAO"
    except LoiHost as exc:
        ly_do = f"WORD_{exc.ma}"
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        ly_do = msg if msg.startswith(("KHONG_SO_HUU", "WORD_")) else f"COM_{pha}:{type(exc).__name__}"
    finally:
        if w.app is not None:  # CHỈ đối tượng đã chứng minh mới nhận Close/khôi phục/Quit (có thể treo → hạn của parent dừng đúng cây đã sở hữu)
            try:
                if doc is not None:
                    doc.Close(SaveChanges=0)  # chỉ Document vừa mở
                for ten, v in opt_cu.items():
                    if ten == "UpdateLinksAtOpen":
                        w.app.Options.UpdateLinksAtOpen = v
                    else:
                        setattr(w.app, ten, v)
                w.quit_da_goi = True
                w.app.Quit(SaveChanges=0)
            except Exception:  # noqa: BLE001
                pass
        doc = app = None
        da_dung = w.dung()
        if w.pid:
            word["da_dung"] = da_dung  # True = handle signaled + Job rỗng; None = UNKNOWN
    if trang_thai == "PDF_DA_TAO" and word.get("da_dung") is not True:  # FIX01 #9: PDF có nhưng chưa xác nhận Word dừng → KHÔNG thành công
        trang_thai, ly_do = "LOI", "WORD_CHUA_XAC_NHAN_DUNG"
    bao({"kieu": KIEU_WORKER_XONG, "trang_thai": trang_thai, "ly_do": ly_do, "pha": pha, "word": word})
    return 0 if trang_thai == "PDF_DA_TAO" else 5


KIEU_CONTROL = "crm_word_control/v1"


def _control(stdin, kenh) -> int:
    """CHỈ CHO NATIVE TEST: Word "người dùng" tổng hợp của chính test, tạo + sở hữu + chứng minh y như worker (không DispatchEx), mở tài liệu
    tổng hợp CHỈ-ĐỌC, báo SAN_SANG; chờ lệnh KIEM (báo số tài liệu/tên/còn sống) rồi DUNG/EOF → đóng/Quit + dừng có bằng chứng. Test cha giữ
    Job/hạn/dừng cây. Không đọc tài liệu nào khác."""
    def bao(v):
        kenh.write(json.dumps({"kieu": KIEU_CONTROL, **v}, ensure_ascii=False) + "\n")
        kenh.flush()
    from .trich6_host import chung_cu_guard, guard_hop_le
    try:
        cfg = json.loads(stdin.readline(64 * 1024).decode("utf-8"))
        goc, vao, ww = Path(cfg["goc"]), Path(cfg["vao"]), Path(cfg["winword"])
    except (ValueError, UnicodeDecodeError, KeyError, TypeError):
        bao({"buoc": "XONG", "loi": "CAU_HINH_SAI", "da_dung": True})
        return 2
    if guard_hop_le(chung_cu_guard()) or goc.resolve() not in vao.resolve().parents or _winword_ok(ww) is not None:
        bao({"buoc": "XONG", "loi": "GUARD_DUONG_DAN_HOAC_BINARY", "da_dung": True})
        return 3
    w, doc, loi = WordSoHuu(ww, goc), None, None
    try:
        w.tao(time.time())
        bao({"buoc": "PID", "pid": w.pid})
        hwnds = w.cho_cua_so(float(cfg.get("han_cua_so", 30)))
        if not hwnds or not w.chung_minh(hwnds):
            raise RuntimeError("KHONG_SO_HUU:CONTROL")
        w.app.AutomationSecurity = 3
        w.app.DisplayAlerts = 0
        doc = w.app.Documents.Open(FileName=str(vao.resolve()), ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False, Visible=False)
        bao({"buoc": "SAN_SANG", "pid": w.pid, "so_tai_lieu": int(w.app.Documents.Count), "ten": str(doc.Name)})
        if stdin.readline(64).strip() == b"KIEM":
            bao({"buoc": "KIEM", "so_tai_lieu": int(w.app.Documents.Count), "ten": str(doc.Name), "song": w.con_song()})
            stdin.readline(64)  # DUNG hoặc EOF
    except Exception as exc:  # noqa: BLE001
        loi = str(exc) if str(exc).startswith(("KHONG_SO_HUU", "WORD_")) else type(exc).__name__
    finally:
        if w.app is not None:
            try:
                if doc is not None:
                    doc.Close(SaveChanges=0)
                w.quit_da_goi = True
                w.app.Quit(SaveChanges=0)
            except Exception:  # noqa: BLE001
                pass
        doc = None
        da_dung = w.dung()
    bao({"buoc": "XONG", "loi": loi, "da_dung": da_dung, "pid": w.pid})
    return 0 if loi is None and da_dung is True else 5


if __name__ == "__main__":
    if sys.argv[1:] in (["--word-worker"], ["--word-control"]):
        _kenh = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
        sys.stdout = sys.stderr
        sys.exit((_worker if sys.argv[1] == "--word-worker" else _control)(sys.stdin.buffer, _kenh))
    sys.exit(2)
