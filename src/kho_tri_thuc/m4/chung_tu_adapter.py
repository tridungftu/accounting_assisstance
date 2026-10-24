"""M4-02B — adapter Chứng từ L3: nhánh credential-free của `review_compute.main` khi `che_do == 'L3'` (tiến trình con do máy chủ sở hữu, không DSN/PG).

Tái sử dụng NGUYÊN lõi nguồn `review_goc/may_chu/chung_tu.py` (+ `phu_luc_ai.khop_hang_muc`, `ocr_abbyy`, `doc_hop_dong`, `master_hd`) qua bộ nạp ghim
`nguon_review._m` — không viết lại rules C01–C09, ngưỡng, phân loại/số/ngày/dòng hàng hay matcher:
- đọc từng tệp: `chung_tu.doc_mot_tai_lieu(path, ai=None)` (phan_loai/tim_ngay/tim_so/so_hop_dong/dong_hang trên bytes đã capture) — CHỈ sau admission
  OOXML/Track Changes (`nguon_review.l3_kiem_tep`); PDF/ảnh → NOT_CONFIGURED (không chạy OCR ABBYY/converter/AI của nguồn, không giả).
  FIX01 §8: cùng MÃ HÀM reader nguồn chạy trong namespace globals CỤC BỘ của worker, trong đó `_cot` được bọc bởi lớp tương thích mỏng: tiêu đề rõ
  nghĩa "Tên hàng"/"Tên hàng hóa" (có dấu, mà `_cot` nguồn xếp nhầm vào NSX vì mẫu `hang$`) → alias "Tên vật tư" mà chính `_cot` nguồn nhận là cột tên.
  Không alias "Hãng"/"Nhà sản xuất"/tiêu đề không dấu mơ hồ/tiêu đề gộp tên+NSX (fullmatch, không hậu tố tùy ý). L3 A2: dấu vết thích nghi ghi theo
  TỪNG VỊ TRÍ (raw hash/tệp, sheet/bảng, dòng tiêu đề, cột, ô vật lý); bản nguồn TRƯỚC alias (`_cot` nguyên) giữ riêng cạnh bản hiệu lực; raw/bản
  trích giữ nguyên; module nguồn không bị sửa.
- trạng thái đọc DÒNG HÀNG tách khỏi trạng thái đọc metadata (FIX01 §2.4): chứng từ dạng form/không bảng nhận được tiêu đề → dòng hàng NOT_CONFIGURED
  (nguồn cần Local AI — chưa cấu hình), không tạo dòng giả; tài liệu có mà chưa đọc được dòng KHÔNG bị coi là thiếu chắc chắn.
- locator vật lý: `nguon_review.l3_vi_tri_xlsx/l3_vi_tri_docx` song song với reader nguồn (trước khi nguồn nén dòng trống); không bịa vị trí từ
  "bảng i dòng r" — không ánh xạ được → NOT_AVAILABLE rõ.
- căn cứ hạng mục: kết quả L2 ĐÃ CÔNG BỐ VÀ CÒN KHỚP căn cứ hiện hành (máy chủ kiểm tương ứng, `l2.trang_thai == 'CO'`); L2 cũ (`'CU'`) → không dùng
  lượng, BOQ hiệu lực + CAN_CU INCOMPLETE kèm tham chiếu/lý do; không có → BOQ hiệu lực tại ngày NT qua `csdl_hop_dong.phu_luc_ap_dung/boq_hieu_luc`
  trên projection :memory: (`nguon_review.projection_l2`) — kl_kn/kl_lk NULL, không giả lượng/prior.
- đối chiếu: `chung_tu.doi_chieu` NGUYÊN trên deep copy (auto). Ghép tay: cùng MÃ HÀM `doi_chieu.__code__` với globals CỤC BỘ, `ghep_hang_muc` = callback.
  FIX01 §2.5: quyết định ghép tay đã lưu chỉ áp khi đích lưu (boq_id + dòng vật lý) TRÙNG đích BOQ hiệu lực hiện hành của mã đó tại ngày NT; khác/không
  xác định → CAN_XAC_NHAN_LAI, dòng rơi về kết quả auto (không âm thầm áp chỉ vì cùng ma_hm).
- coverage companion C01–C09 + TAI_LIEU/DONG_HANG/CAN_CU tách khỏi finding nguồn; so sánh TYPED theo hạng mục (C01/C03: toán hạng KL kỳ này/lũy kế
  của chính hạng mục + số lượng/ĐVT từng dòng) và theo cặp chứng từ (C06: GN ↔ CO/CQ/PL, ĐVT chuẩn hóa nguồn, lô/ngày tách riêng); ghi chú cho finding
  nguồn ở danh sách riêng (không sửa/xóa finding). Báo cáo XLSX L3.
Ước tính tiền của nguồn (float, VAT nếu có) chỉ là ước tính — không phải NT/thuế/công nợ được chấp nhận.
"""

from __future__ import annotations

import copy
import hashlib
import io
import re
import types
import unicodedata
from collections import Counter
from pathlib import Path

CHE_DO = "L3"
MA_L3 = ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09")
MA_PHU = ("TAI_LIEU", "DONG_HANG", "CAN_CU")
DAT_DU = ("CHECKED", "KHONG_AP_DUNG")
THU_TU = {"ERROR": 0, "INCOMPLETE": 1, "NOT_AVAILABLE": 2, "LIMITED": 3, "NOT_ELIGIBLE": 4, "KHONG_AP_DUNG": 5, "CHECKED": 6}
SO_SANH = ("SO_DUOC", "CHUA_SO_DUOC", "NGUON_KHONG_SO", "KHONG_AP_DUNG")  # so sánh typed theo hạng mục/cặp — không phải coverage tổng
LOAI_DONG = ("BB_NT", "BB_GN", "BB_LD", "PL", "CO", "CQ")
RE_VI_TRI = re.compile(r"^b[^\s\d]*ng (\d+) d[^\s\d]*ng (\d+)$")  # '<bảng> i <dòng> r' của chung_tu.dong_hang (chịu khác dạng chuẩn hóa Unicode)
RE_SO_HD = re.compile(r"\s*0*(\d+)\s*/\s*(\d{4})")  # đúng biểu thức nguồn doi_chieu dùng để tách số HĐ
# tiêu đề cột TÊN rõ nghĩa mà `_cot` nguồn xếp nhầm vào NSX (mẫu `\bhang\b$` sau khi bỏ dấu). CHỈ dạng có dấu "hàng" (không "hãng", không không dấu),
# TOÀN BỘ tiêu đề (fullmatch, chỉ chuẩn hóa NFC/hoa-thường/khoảng trắng). L3 A1: KHÔNG nhận hậu tố tùy ý — tiêu đề GỘP tên/NSX/model như
# "Tên hàng / Nhà sản xuất", "Tên hàng (Hãng sản xuất)" giữ quyết định nguồn (không bịa cột tên).
RE_TEN_HANG = re.compile(r"tên hàng(?: hóa| hoá)?")
ALIAS_TEN = "Tên vật tư"  # alias mà chính `_cot` nguồn nhận là "ten"
LY_DO_ALIAS = "Tiêu đề tên hàng rõ nghĩa bị mẫu NSX `hang$` của nguồn bắt nhầm — đọc bằng alias nguồn hỗ trợ"
TEN_BAO_CAO = "chung_tu_l3.xlsx"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def row_id(raw_sha256: str, khoa_vi_tri: str) -> str:
    """Định danh ổn định của MỘT dòng chứng từ: toàn bộ raw SHA-256 + vị trí (sheet/bảng/dòng vật lý, hoặc vị trí nguồn khi không ánh xạ được)."""
    return _sha(f"m4.chung_tu.row/1|{raw_sha256}|{khoa_vi_tri}".encode("utf-8"))


def duong_lam_viec(thu_muc: Path, ref: str) -> Path:
    """work_ref do máy chủ sinh: đường dẫn TƯƠNG ĐỐI dưới thư mục lần chạy; tuyệt đối/ổ đĩa/.. → từ chối."""
    if not isinstance(ref, str) or not ref or ref.startswith(("/", "\\")) or ":" in ref or ".." in ref.replace("\\", "/").split("/"):
        raise RuntimeError("work_ref không hợp lệ (phải là đường dẫn tương đối dưới thư mục lần chạy)")
    goc = Path(thu_muc).resolve()
    p = (goc / ref).resolve()
    if goc not in p.parents:
        raise RuntimeError("work_ref ra ngoài thư mục lần chạy")
    return p


# ================================================================================================== reader nguồn + tương thích tiêu đề (FIX01 §8)
def _cot_tuong_thich(goc, cho: list):
    """Bọc `_cot` nguồn: chỉ khi nguồn trả 'nsx' cho tiêu đề rõ nghĩa "Tên hàng[ hóa]" (có dấu, toàn bộ ô) mới hỏi lại nguồn bằng alias "Tên vật tư";
    mọi tiêu đề khác (kể cả "Hãng", "Nhà sản xuất", "Ten hang" không dấu, tiêu đề gộp tên/NSX) giữ nguyên quyết định của nguồn. Chuỗi tiêu đề đã
    thích nghi ghi vào `cho` (dòng tiêu đề đang xét) — bằng chứng theo VỊ TRÍ do `_theo_doi_tieu_de` dựng, không gộp theo chuỗi."""
    def cot(t):
        k = goc(t)
        if k == "nsx":
            s = " ".join(unicodedata.normalize("NFC", str(t or "")).lower().split())
            if RE_TEN_HANG.fullmatch(s):
                k2 = goc(ALIAS_TEN)
                if k2 == "ten":
                    cho.append(str(t))
                    return k2
        return k
    return cot


def _vi_tri_hang(bang, row) -> tuple:
    """(bảng nguồn 1-based, dòng nén 0-based) của đúng đối tượng dòng `row` trong các bảng nguồn đã chụp; không thấy → (None, None)."""
    for bi, b in enumerate(bang or [], 1):
        for h0, r in enumerate(b):
            if r is row:
                return bi, h0
    return None, None


def _theo_doi_tieu_de(f, bang_ref: dict, cho: list, ghi: list):
    """Bọc `_tieu_de` (cùng mã nguồn `f`): ghi lại MỖI dòng tiêu đề được nguồn nhận hoặc có alias — bảng/dòng nguồn (theo đối tượng dòng), ô tiêu đề
    nguyên, quyết định cột của nguồn và tiêu đề đã alias. Không đổi kết quả trả về."""
    def tieu_de(row):
        cho.clear()
        res = f(row)
        alias = sorted(set(cho))
        cho.clear()
        if res is not None or alias:
            bi, h0 = _vi_tri_hang(bang_ref.get("bang"), row)
            ghi.append({"bi": bi, "h0": h0, "cot": dict(res) if res else None, "alias": alias, "o": [str(x) for x in row]})
        return res
    return tieu_de


def doc_nguon_l3(ct, path: Path) -> tuple[dict, dict]:
    """`chung_tu.doc_mot_tai_lieu(path, ai=None)` NGUYÊN mã, chạy trong bản sao namespace của worker (module nguồn không đổi), với `_cot` bọc tương
    thích. `_tieu_de`/`dong_hang`/`doc_mot_tai_lieu` là cùng `__code__` nguồn gắn vào bản sao globals; `doc_file` nguồn được gọi nguyên, chỉ giữ tham
    chiếu bảng nó trả. Trả (kết quả nguồn, {tieu_de: dòng tiêu đề + alias theo vị trí, bang: bảng nguồn trước nén})."""
    cho, ghi, bang_ref = [], [], {}
    g = dict(ct.doc_mot_tai_lieu.__globals__)
    g["_cot"] = _cot_tuong_thich(ct._cot, cho)
    doc_file_nguon = g["doc_file"]

    def doc_file(*a, **k):
        doc = doc_file_nguon(*a, **k)
        bang_ref["bang"] = doc.get("bang")
        return doc
    g["doc_file"] = doc_file
    for ten in ("_tieu_de", "dong_hang", "doc_mot_tai_lieu"):
        f = getattr(ct, ten)
        f2 = types.FunctionType(f.__code__, g, ten, f.__defaults__, f.__closure__)
        f2.__kwdefaults__ = f.__kwdefaults__
        g[ten] = f2
    g["_tieu_de"] = _theo_doi_tieu_de(g["_tieu_de"], bang_ref, cho, ghi)
    d = g["doc_mot_tai_lieu"](str(path), ai=None)
    return d, {"tieu_de": ghi, "bang": bang_ref.get("bang") or []}


def doc_truoc_alias(ct, bang: list, loai) -> tuple[list, list]:
    """L3 A2 — bản nguồn TRƯỚC thích nghi: `chung_tu.dong_hang` cùng mã nguồn với `_cot` NGUYÊN của nguồn (không alias) trên bản sao bảng đã chụp
    từ chính lần đọc. Trả (dòng hàng nguồn, dòng tiêu đề nguồn đã nhận). Module nguồn không đổi."""
    b2 = copy.deepcopy(bang)
    ref, cho, ghi = {"bang": b2}, [], []
    g = dict(ct.dong_hang.__globals__)
    td = ct._tieu_de
    g["_tieu_de"] = _theo_doi_tieu_de(types.FunctionType(td.__code__, g, "_tieu_de", td.__defaults__, td.__closure__), ref, cho, ghi)
    dh = ct.dong_hang
    f = types.FunctionType(dh.__code__, g, "dong_hang", dh.__defaults__, dh.__closure__)
    return f(b2, loai), ghi


# ================================================================================================== locator
def _cot_chu(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _vung(rg: str) -> tuple | None:
    """'D4:E5' / 'D4' → (cột đầu, dòng đầu, cột cuối, dòng cuối); không đọc được → None."""
    m = re.fullmatch(r"([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?", str(rg or ""))
    if not m:
        return None

    def so(c):
        v = 0
        for ch in c:
            v = v * 26 + ord(ch) - 64
        return v
    c1, r1 = so(m.group(1)), int(m.group(2))
    c2, r2 = (so(m.group(3)), int(m.group(4))) if m.group(3) else (c1, r1)
    return c1, r1, c2, r2


def vi_tri_o(media: str, ban_do: dict | None, bi, h0, j, ly_do_khong: str | None = None) -> dict:
    """L3 A2 — vị trí VẬT LÝ của một Ô nguồn (bảng nguồn `bi` 1-based, dòng nén `h0` 0-based, cột logic `j` 0-based) qua bản đồ locator hiện có.
    XLSX: sheet + dòng + cột (cột đầu của nguồn) + ô gộp chứa ô. DOCX: bảng/w:tr vật lý + w:tc, gridSpan, vMerge, cột logic ≠ ô vật lý. Không xác định
    → NOT_AVAILABLE (không có dòng) hoặc LIMITED (có dòng, ô/cột không chắc) kèm lý do; không bao giờ giả CHECKED."""
    from . import nguon_review as NR
    nguon = {"bang_nguon": bi, "dong_nguon": None if h0 is None else h0 + 1, "cot_nguon": None if j is None else j + 1}
    if ban_do is None:
        return {"trang_thai": "NOT_AVAILABLE", "ly_do": ly_do_khong or "Không có bản đồ vị trí vật lý của tệp", **nguon}
    bang = ban_do.get("bang") or []
    if bi is None or h0 is None or j is None or not 1 <= bi <= len(bang) or not 0 <= h0 < len(bang[bi - 1]["dong"]):
        return {"trang_thai": "NOT_AVAILABLE", "ly_do": "Bảng/dòng nguồn không ánh xạ được sang bản đồ vị trí vật lý", **nguon}
    b = bang[bi - 1]
    dong = b["dong"][h0]
    if media == NR.MEDIA_XLSX:
        if b.get("cot_dau") is None:
            return {"trang_thai": "LIMITED", "loai": "XLSX", "sheet": b["sheet"], "dong": dong, **nguon,
                    "ly_do": "Bản đồ vị trí không có cột đầu của vùng đọc — cột vật lý không xác định"}
        cot = int(b["cot_dau"]) + j
        loc = {"trang_thai": "CHECKED", "loai": "XLSX", "sheet": b["sheet"], "dong": dong, "cot": cot, "o": f"{_cot_chu(cot)}{dong}", **nguon}
        gop = b.get("o_gop")
        if gop is None:
            loc.update(trang_thai="LIMITED", ly_do=ban_do.get("o_gop_ly_do") or "Không có danh sách ô gộp — không xác nhận ô nằm ngoài vùng gộp")
            return loc
        for rg in gop:
            v = _vung(rg)
            if v is None:
                loc.update(trang_thai="LIMITED", ly_do=f"Vùng gộp không đọc được ({str(rg)[:40]})")
                return loc
            c1, r1, c2, r2 = v
            if r1 <= dong <= r2 and c1 <= cot <= c2:
                loc["o_gop"] = rg
                if (r1, c1) != (dong, cot):
                    loc.update(trang_thai="LIMITED", ly_do=f"Ô nằm trong vùng gộp {rg} nhưng không phải ô trên-trái — giá trị nguồn đọc là trống")
                break
        return loc
    loc = {"trang_thai": "CHECKED", "loai": "DOCX", "bang": b["bang_vat_ly"], "dong": dong, **nguon}
    o = b.get("o")
    if o is None or h0 >= len(o) or not 0 <= j < len(o[h0]):
        loc.update(trang_thai="LIMITED", ly_do="Không ánh xạ được cột logic sang ô w:tc vật lý (dòng vật lý đã xác định)")
        return loc
    tc, k, vm = o[h0][j]
    loc.update(tc=tc, grid_span=sum(1 for x in o[h0] if x[0] == tc), v_merge=vm, logic_khac_vat_ly=tc != j + 1)
    if k:
        loc.update(trang_thai="LIMITED", ly_do=f"Cột logic {j + 1} là phần trải gridSpan thứ {k + 1} của ô w:tc {tc} — không phải ô vật lý riêng")
    elif vm == "continue":
        loc.update(trang_thai="LIMITED", ly_do=f"Ô w:tc {tc} là phần tiếp vMerge — nguồn đọc trống, giá trị nằm ở ô bắt đầu phía trên")
    return loc


def tieu_de_bang(ghi: list, media: str, ban_do: dict | None, ly_do_khong: str | None = None) -> list:
    """Dòng tiêu đề nguồn ĐÃ NHẬN (mỗi bảng một): bảng/dòng nguồn, ô tiêu đề nguyên, cột nguồn (1-based logic) và vị trí vật lý TỪNG cột đã nhận."""
    out = []
    for x in ghi:
        if not x["cot"]:
            continue
        cvl = {k: vi_tri_o(media, ban_do, x["bi"], x["h0"], j, ly_do_khong) for k, j in x["cot"].items()}
        out.append({"bang_nguon": x["bi"], "dong_tieu_de_nguon": None if x["h0"] is None else x["h0"] + 1,
                    "cot": {k: j + 1 for k, j in x["cot"].items()}, "o_tieu_de": list(x["o"]), "alias": list(x["alias"]),
                    "trang_thai_vi_tri": min((v["trang_thai"] for v in cvl.values()), key=THU_TU.get, default="NOT_AVAILABLE"), "cot_vat_ly": cvl})
    return out


def bang_chung_alias(ghi: list, media: str, ban_do: dict | None, raw_sha256: str, tep_id: str, ly_do_khong: str | None = None) -> list:
    """L3 A1/A2 — MỖI ô tiêu đề đã alias tại MỘT vị trí (không gộp cùng chuỗi ở hai sheet/bảng/cột): raw hash/tệp, bảng + dòng tiêu đề + cột nguồn,
    ô tiêu đề nguyên của dòng, có hiệu lực hay không (dòng được nguồn nhận làm tiêu đề và cột tên = ô này) và vị trí vật lý của ô."""
    out = []
    for x in ghi:
        if not x["alias"]:
            continue
        for j, t in enumerate(x["o"]):
            if t not in x["alias"]:
                continue
            out.append({"tieu_de": t, "nguon_xep": "nsx", "alias": ALIAS_TEN, "ap": "ten", "ly_do": LY_DO_ALIAS, "tep_id": tep_id, "raw_sha256": raw_sha256,
                        "bang_nguon": x["bi"], "dong_tieu_de_nguon": None if x["h0"] is None else x["h0"] + 1, "cot_nguon": j + 1,
                        "hieu_luc": bool(x["cot"]) and x["cot"].get("ten") == j, "o_tieu_de": list(x["o"]),
                        "vi_tri_vat_ly": vi_tri_o(media, ban_do, x["bi"], x["h0"], j, ly_do_khong)})
    return out


def _o_nguon(bang: list, vi_tri) -> list | None:
    """Ô nguyên của dòng nguồn 'bảng i dòng r' trong bảng đã chụp (trước nén/alias); không ánh xạ được → None."""
    m = RE_VI_TRI.match(str(vi_tri or ""))
    if not m:
        return None
    bi, r = int(m.group(1)), int(m.group(2))
    if 1 <= bi <= len(bang) and 1 <= r <= len(bang[bi - 1]):
        return [str(x) for x in bang[bi - 1][r - 1]]
    return None


def gan_vi_tri(dong: list, media: str, ban_do: dict | None, raw_sha256: str, tep_id: str, ly_do_khong: str | None = None,
               tieu_de: dict | None = None) -> None:
    """Gắn row_id + vị trí vật lý cho từng dòng nguồn (`vi_tri` = 'bảng i dòng r' của `chung_tu.dong_hang`) qua bản đồ song song của seam locator.
    `tieu_de` {bảng nguồn: dòng nén 0-based của tiêu đề} → thêm dòng tiêu đề vật lý (không đổi row_id/khóa vị trí)."""
    from . import nguon_review as NR
    for i, ln in enumerate(dong):
        loc = {"trang_thai": "NOT_AVAILABLE", "ly_do": ly_do_khong or "Không ánh xạ được vị trí nguồn sang ô/dòng vật lý", "nguon": ln.get("vi_tri")}
        m = RE_VI_TRI.match(str(ln.get("vi_tri") or ""))
        bang = (ban_do or {}).get("bang") or []
        if m and ban_do is not None:
            bi, r = int(m.group(1)), int(m.group(2))
            if 1 <= bi <= len(bang) and 1 <= r <= len(bang[bi - 1]["dong"]):
                b = bang[bi - 1]
                if media == NR.MEDIA_XLSX:
                    loc = {"trang_thai": "CHECKED", "loai": "XLSX", "sheet": b["sheet"], "dong": b["dong"][r - 1], "nguon": ln.get("vi_tri")}
                else:
                    loc = {"trang_thai": "CHECKED", "loai": "DOCX", "bang": b["bang_vat_ly"], "dong": b["dong"][r - 1], "nguon": ln.get("vi_tri")}
                h0 = (tieu_de or {}).get(bi)
                if h0 is not None and 0 <= h0 < len(b["dong"]):
                    loc["dong_tieu_de"] = b["dong"][h0]
        khoa = (f"{loc['loai']}|{loc.get('sheet') or loc.get('bang')}|{loc['dong']}" if loc["trang_thai"] == "CHECKED"
                else f"NGUON|{ln.get('vi_tri')}|{i}")
        ln["row_id"] = row_id(raw_sha256, khoa)
        ln["tep_id"] = tep_id
        ln["vi_tri_vat_ly"] = loc


# ================================================================================================== đọc tài liệu
def doc_tai_lieu(ct, tl: dict, path: Path, raw: bytes) -> dict:
    """MỘT tệp của bộ: admission → reader nguồn → locator. Lỗi/unsupported/provider chưa cấu hình → trạng thái rõ, vẫn nằm trong coverage."""
    from . import nguon_review as NR
    base = {"id": tl["tep_id"], "tep_id": tl["tep_id"], "ten": tl["ten_goc"], "raw_sha256": tl["raw_sha256"], "byte_length": tl["byte_length"],
            "media_type": tl["media_type"], "muc": tl.get("muc"), "dong": [], "bo": False, "canh_bao": [], "gioi_han": [], "thich_nghi_cot": [],
            "tieu_de_bang": [], "nguon_truoc_alias": None}
    adm = NR.l3_kiem_tep(raw, tl["media_type"])
    if adm["doc"] != "NATIVE":
        return {**base, "loai": None, "loai_ten": None, "so": "", "ngay": None, "hd_ref": [],
                "trang_thai_doc": "NOT_CONFIGURED" if adm["doc"] == "PROVIDER" else "KHONG_HO_TRO", "ly_do_doc": adm["ly_do"],
                "track_changes": adm.get("track_changes")}
    try:
        d, nguon = doc_nguon_l3(ct, path)
    except Exception as exc:  # noqa: BLE001 — lỗi reader nguồn: ghi ERROR thật (source catch-and-continue không biến thành đủ hồ sơ)
        return {**base, "loai": None, "loai_ten": None, "so": "", "ngay": None, "hd_ref": [], "trang_thai_doc": "ERROR",
                "ly_do_doc": f"Bộ đọc nguồn lỗi: {type(exc).__name__}: {str(exc)[:300]}"}
    gioi_han, ban_do, ly_khong = [], None, None
    try:
        if tl["media_type"] == NR.MEDIA_XLSX:
            ban_do = NR.l3_vi_tri_xlsx(path)
            gioi_han += [g["ly_do"] + f" (sheet {g['sheet']})" for g in ban_do["gioi_han"]]
            if ban_do["o_cong_thuc_khong_cache"]:
                gioi_han.append(f"{ban_do['o_cong_thuc_khong_cache']} ô công thức chưa có giá trị cache — nguồn đọc thành trống (NULL), không tính lại")
        else:
            ban_do = NR.l3_vi_tri_docx(path)
            if ban_do["bang_long"]:
                gioi_han.append(f"{ban_do['bang_long']} bảng lồng trong ô — nguồn gộp chữ vào ô ngoài, không tách dòng hàng của bảng lồng")
    except Exception as exc:  # noqa: BLE001 — không ánh xạ được vị trí: dòng vẫn giữ, vị trí NOT_AVAILABLE
        ban_do, ly_khong = None, f"Seam vị trí lỗi ({type(exc).__name__}) — vị trí vật lý không xác định"
    media, sha, tid = tl["media_type"], tl["raw_sha256"], tl["tep_id"]
    # L3 A2: hai lớp — bản nguồn TRƯỚC alias (`_cot` nguyên của nguồn, cùng bảng đã chụp từ CHÍNH bytes này) và bản hiệu lực (sau alias). So sánh trên
    # dict nguồn TRƯỚC khi gắn vị trí; bản trước alias không bao giờ bị ghép/sửa (giữ riêng khỏi provenance.auto).
    try:
        truoc_dong, truoc_td = doc_truoc_alias(ct, nguon["bang"], d["loai"])
        loi_truoc = None
    except Exception as exc:  # noqa: BLE001 — không dựng được lớp trước alias: ghi ERROR có lý do, không coi là giống hiệu lực
        truoc_dong, truoc_td, loi_truoc = None, [], f"Không dựng được bản nguồn trước alias: {type(exc).__name__}: {str(exc)[:200]}"
    giong = truoc_dong is not None and truoc_dong == d["dong"]
    td_truoc = {x["bi"]: x["h0"] for x in truoc_td if x["cot"] and x["bi"] is not None}
    dong_truoc = None
    if truoc_dong is not None and not giong:
        dong_truoc = copy.deepcopy(truoc_dong)
        for ln in dong_truoc:
            ln["o_nguon"] = _o_nguon(nguon["bang"], ln.get("vi_tri"))
        gan_vi_tri(dong_truoc, media, ban_do, sha, tid, ly_khong, tieu_de=td_truoc)
    truoc = {"tep_id": tid, "raw_sha256": sha, "trang_thai": "ERROR" if loi_truoc else "CHECKED", "ly_do": loi_truoc, "giong_hieu_luc": giong,
             "so_dong": None if truoc_dong is None else len(truoc_dong), "tieu_de_bang": tieu_de_bang(truoc_td, media, ban_do, ly_khong),
             "dong": dong_truoc}
    trich = {"loai": d["loai"], "so": d["so"], "ngay": d["ngay"], "ly_do_loai": d.get("ly_do_loai")}
    out = {**base, **{k: v for k, v in d.items() if k not in ("id",)}, "id": tid, "id_nguon": d.get("id"), "ten": d["ten"], "trich": trich,
           "trang_thai_doc": "LIMITED" if gioi_han else "CHECKED", "ly_do_doc": "; ".join(gioi_han) or None, "gioi_han": gioi_han, "bo": False,
           "thich_nghi_cot": bang_chung_alias(nguon["tieu_de"], media, ban_do, sha, tid, ly_khong),
           "tieu_de_bang": tieu_de_bang(nguon["tieu_de"], media, ban_do, ly_khong), "nguon_truoc_alias": truoc}
    gan_vi_tri(out["dong"], media, ban_do, sha, tid, ly_khong,
               tieu_de={x["bi"]: x["h0"] for x in nguon["tieu_de"] if x["cot"] and x["bi"] is not None})
    return out


def gan_trang_thai_dong(d: dict) -> None:
    """Trạng thái đọc DÒNG HÀNG của một chứng từ (tách khỏi metadata) — tính SAU metadata hiệu lực (loại người dùng chọn). Không tạo dòng."""
    from . import nguon_review as NR
    if d["trang_thai_doc"] not in ("CHECKED", "LIMITED"):
        d["trang_thai_dong"], d["ly_do_dong"] = d["trang_thai_doc"], d.get("ly_do_doc")
    elif d["dong"]:
        khong_vt = sum(1 for ln in d["dong"] if (ln.get("vi_tri_vat_ly") or {}).get("trang_thai") != "CHECKED")
        d["trang_thai_dong"] = "LIMITED" if khong_vt or d["trang_thai_doc"] == "LIMITED" else "CHECKED"
        d["ly_do_dong"] = (f"{khong_vt} dòng không ánh xạ được vị trí vật lý" if khong_vt else d.get("ly_do_doc")) if d["trang_thai_dong"] == "LIMITED" else None
    elif d.get("loai") == "KHAC":
        d["trang_thai_dong"], d["ly_do_dong"] = "KHONG_AP_DUNG", "Chứng từ chưa phân loại — nguồn không đối chiếu dòng hàng"
    else:
        d["trang_thai_dong"] = "NOT_CONFIGURED"
        d["ly_do_dong"] = ("Không có bảng dòng hàng nhận được tiêu đề (chứng từ dạng form/bảng khác mẫu) — nguồn cần Local AI để đọc, "
                           f"{NR.L3_PROVIDER['LOCAL_AI']['trang_thai']}; không tạo dòng giả, không coi là chứng từ thiếu")


def ap_metadata(ct, docs: list, rev: dict | None) -> list:
    """Metadata HIỆU LỰC = trích bất biến + revision người dùng (loại/số/ngày/bỏ) — cùng ngữ nghĩa `chung_tu.cap_nhat` nguồn nhưng không ghi đè bản trích."""
    hl = ((rev or {}).get("tai_lieu") or {})
    so_rev = (rev or {}).get("revision")
    sua = []
    for d in docs:
        o = hl.get(d["tep_id"]) or {}
        if not o:
            continue
        if o.get("loai") in ct.LOAI and d["trang_thai_doc"] in ("CHECKED", "LIMITED"):
            d["loai"], d["loai_ten"], d["ly_do_loai"] = o["loai"], ct.LOAI[o["loai"]], f"Người dùng chọn (revision {so_rev})"
        if "so" in o and d["trang_thai_doc"] in ("CHECKED", "LIMITED"):
            d["so"] = str(o["so"] or "").strip()
        if "ngay" in o and d["trang_thai_doc"] in ("CHECKED", "LIMITED"):
            d["ngay"] = o["ngay"] or None
        if "bo" in o:
            d["bo"] = bool(o["bo"])
        sua.append({"tep_id": d["tep_id"], "revision": so_rev, **{k: o[k] for k in ("loai", "so", "ngay", "bo") if k in o}})
    return sua


# ================================================================================================== căn cứ hạng mục
def _projection_co(basis: dict) -> dict:
    return {"hop_dong": basis.get("hop_dong"), "dot": basis.get("dot"), "tham_so": basis.get("tham_so") or [], "phu_luc": basis.get("phu_luc") or [],
            "boq": basis.get("boq") or [], "manual_map": basis.get("manual_map_l2") or []}


def hang_muc(basis: dict) -> tuple[list, dict]:
    """Hạng mục đối chiếu + ngữ cảnh. Ưu tiên kết quả L2 đã công bố VÀ còn khớp căn cứ hiện hành (máy chủ kiểm, `trang_thai == 'CO'`); L2 cũ (`'CU'`)
    hoặc không có → BOQ hiệu lực tại ngày NT (BOQ-only: kl_kn/kl_lk NULL). Không có HĐ/BOQ/ngày NT → [] và lý do. Mỗi hạng mục gắn nguồn BOQ hiệu
    lực (đích ghép tay) khi xác định được."""
    from . import nguon_review as NR
    cs = NR._m("csdl_hop_dong")
    ngay = str((basis.get("dot") or {}).get("ngay_nghiem_thu") or "")[:10] or None
    l2 = basis.get("l2") or {}
    ctx = {"nguon": None, "ly_do": None, "ngay_nt": ngay, "l2": None,
           "l2_cu": ({k: l2.get(k) for k in ("run_id", "basis_sha256", "ket_qua_sha256", "ly_do", "khac")} if l2.get("trang_thai") == "CU" else None)}
    hl, nguon_eff = {}, {}
    boq_map = [b for b in basis.get("boq") or [] if b.get("trang_thai") == "DA_MAP"]
    if basis.get("hop_dong") and ngay and boq_map:
        con, bd = NR.projection_l2(_projection_co(basis))
        try:
            pls = cs.phu_luc_ap_dung(con, bd["ma_hd"], ngay)
            hl, _bo = cs.boq_hieu_luc(con, bd["ma_hd"], pls=pls)
            for ma, v in hl.items():
                tat_ca = bd["nguon_boq"].get(ma) or []
                pl_pg = None
                if v.get("nguon") != "HĐ gốc":
                    p = next((p for p in reversed(pls) if p["so_pl"] == v["nguon"]), None)
                    pl_pg = bd["phu_luc"].get(p["id"]) if p is not None else "?"
                nguon_eff[ma] = [x for x in tat_ca if (x["phu_luc_id"] is None if pl_pg is None else str(x["phu_luc_id"]) == str(pl_pg))]
        finally:
            con.close()
    rows = l2.get("doi_chieu_hm") if l2.get("trang_thai") == "CO" else None
    hm = []
    if rows:
        for h in rows:
            khoa = h.get("ma_hm") or f"D{h.get('dong')}"
            hm.append({"khoa": khoa, "ma_hm": h.get("ma_hm") or "", "ten": h.get("ten") or "", "dvt": h.get("dvt") or "", "stt": "",
                       "kl_kn": h.get("kl_kn"), "kl_lk": h.get("kl_lk"), "kl_hd": h.get("kl_hd_hs"), "don_gia": h.get("dg_hd") or h.get("dg_hs"),
                       "dong": h.get("dong"), "nguon_boq": nguon_eff.get(h.get("ma_hm") or "", [])})
        ctx.update(nguon="L2", l2={k: l2.get(k) for k in ("run_id", "ket_qua_sha256", "basis_sha256", "tep_id", "trang_thai_run")})
    elif hl:
        for ma, v in hl.items():
            hm.append({"khoa": ma, "ma_hm": ma, "ten": v["ten"], "dvt": v["dvt"], "stt": str(v.get("stt") or ""), "kl_kn": None, "kl_lk": None,
                       "kl_hd": v.get("kl"), "don_gia": v.get("don_gia"), "dong": None, "nguon_boq": nguon_eff.get(ma, [])})
        ctx.update(nguon="BOQ", ly_do=("Kết quả L2 đã công bố không còn khớp căn cứ hiện hành (" + str(l2.get("ly_do") or "căn cứ L2 đổi") +
                                       ") — chỉ BOQ hiệu lực; chạy lại Review L1+L2 rồi Chạy lại L3" if ctx["l2_cu"] else
                                       "Chưa có kết quả L2 đã công bố cho đợt — chỉ BOQ hiệu lực tại ngày NT; KL kỳ này/lũy kế để NULL (không giả)"))
    else:
        ctx["ly_do"] = ("Chưa có căn cứ hạng mục: " + ("đợt chưa có ngày nghiệm thu" if not ngay else "chưa có BOQ đọc/map đủ" if not boq_map
                                                     else "BOQ hiệu lực rỗng"))
    return hm, ctx


def _thong_tin_hd(basis: dict) -> dict:
    from . import nguon_review as NR
    cs = NR._m("csdl_hop_dong")
    ts = {t["ma"]: t for t in basis.get("tham_so") or []}

    def co(ma):
        t = ts.get(ma)
        return t["gia_tri"] if t and t.get("trang_thai") == "CO_GIA_TRI" and t.get("gia_tri") not in (None, "") else None
    ngay_ky = vat = None
    try:
        ngay_ky = cs.ngay_iso(co("TC-02")) if co("TC-02") else None
    except Exception:  # noqa: BLE001 — không đọc được ngày ký: NULL (coverage C07 ghi), không đoán
        ngay_ky = None
    try:
        vat = cs.ty_le(co("TT-04")) if co("TT-04") else None
    except Exception:  # noqa: BLE001
        vat = None
    return {"so_hd": (basis.get("hop_dong") or {}).get("so_hop_dong"), "ngay_ky_hd": ngay_ky, "vat": vat}


# ================================================================================================== ghép tay: đích lưu ↔ đích hiện hành (FIX01 §2.5)
def kiem_ghep_tay(maps: list, hm: list) -> dict:
    """Mỗi quyết định ghép tay hiện hành (bản revision mới nhất theo row_id) → {khoa, hop_le, ly_do, dich_luu, dich_hien_hanh, ...}. Hợp lệ CHỈ khi mã
    có trong căn cứ của lần chạy và có ĐÚNG MỘT dòng BOQ hiệu lực tại ngày NT trùng (boq_id, dòng) đã lưu. Không đổi lịch sử map; không tự gán đích mới."""
    theo = {h["khoa"]: h for h in hm}
    out = {}
    for m in maps or []:
        dich_luu = {"boq_id": str(m.get("boq_id")) if m.get("boq_id") is not None else None,
                    "dong": int(m["boq_dong"]) if m.get("boq_dong") is not None else None}
        rec = {"khoa": m.get("ma_hm"), "revision": m.get("revision"), "id": m.get("id"), "dich_luu": dich_luu, "raw_sha256": m.get("raw_sha256"),
               "revision_chung_tu": m.get("revision_chung_tu"), "hop_le": False, "dich_hien_hanh": None, "ly_do": None}
        h = theo.get(m.get("ma_hm"))
        eff = (h or {}).get("nguon_boq") or []
        if h is None:
            rec["ly_do"] = "Mã hạng mục đích không có trong căn cứ hạng mục của lần chạy này"
        elif len(eff) != 1:
            rec["ly_do"] = (f"Mã {m.get('ma_hm')} có {len(eff)} dòng BOQ hiệu lực tại ngày NT — không xác nhận được đích đã lưu còn hiện hành"
                            if eff else f"Không xác định được dòng BOQ hiệu lực của mã {m.get('ma_hm')} (chưa có BOQ/ngày NT/đã bỏ)")
        else:
            hien = {"boq_id": str(eff[0]["boq_id"]), "dong": int(eff[0]["dong"]), "phu_luc_id": eff[0].get("phu_luc_id"), "thao_tac": eff[0].get("thao_tac")}
            rec["dich_hien_hanh"] = hien
            if (hien["boq_id"], hien["dong"]) == (dich_luu["boq_id"], dich_luu["dong"]):
                rec["hop_le"] = True
            else:
                rec["ly_do"] = (f"Đích đã lưu (BOQ {dich_luu['boq_id']} dòng {dich_luu['dong']}) khác dòng BOQ hiệu lực hiện hành của mã {m.get('ma_hm')} "
                                f"(BOQ {hien['boq_id']} dòng {hien['dong']}) — phụ lục thay/nhập lại BOQ; cần xác nhận lại")
        out[m["row_id"]] = rec
    return out


def doi_chieu_hai_ban(ct, kq_goc: dict, ghep_tay: dict) -> tuple[dict, dict, list]:
    """(auto, hiệu lực, nhật ký ghép tay). Auto = `chung_tu.doi_chieu` nguyên trên deep copy. Hiệu lực = cùng mã hàm với globals cục bộ có callback
    ghép tay theo row_id — CHỈ quyết định `hop_le` (đích lưu = đích hiện hành, mã có trong căn cứ) được áp; quyết định cũ không còn hiện hành →
    CAN_XAC_NHAN_LAI và dòng dùng kết quả auto của nguồn. Module nguồn không bị sửa."""
    auto = ct.doi_chieu(copy.deepcopy(kq_goc))
    if not ghep_tay:
        return auto, copy.deepcopy(auto), []
    goc = ct.ghep_hang_muc
    nhat_ky, gap = [], set()

    def ghep(dong, hm):
        rid = dong.get("row_id")
        quyet = ghep_tay.get(rid)
        if quyet is not None:
            gap.add(rid)
            chung = {"row_id": rid, "khoa": quyet["khoa"], "map_revision": quyet.get("revision"), "map_id": quyet.get("id"), "dich_luu": quyet.get("dich_luu"),
                     "dich_hien_hanh": quyet.get("dich_hien_hanh")}
            if quyet.get("hop_le") and quyet["khoa"] in hm:
                nhat_ky.append({**chung, "trang_thai": "DA_AP"})
                return quyet["khoa"], 1.0
            k, r = goc(dong, hm)
            nhat_ky.append({**chung, "trang_thai": "CAN_XAC_NHAN_LAI" if quyet.get("dich_hien_hanh") or quyet["khoa"] in hm else "KHONG_AP",
                            "ly_do": quyet.get("ly_do") or "Đích ghép tay không có trong căn cứ hạng mục của lần chạy này", "dung_auto": k})
            return k, r
        return goc(dong, hm)
    g = dict(ct.doi_chieu.__globals__)  # bản sao namespace — module chung_tu KHÔNG đổi
    g["ghep_hang_muc"] = ghep
    f = types.FunctionType(ct.doi_chieu.__code__, g, "doi_chieu", ct.doi_chieu.__defaults__, ct.doi_chieu.__closure__)
    hieu_luc = f(copy.deepcopy(kq_goc))
    for rid, q in ghep_tay.items():
        if rid not in gap:
            nhat_ky.append({"row_id": rid, "khoa": q["khoa"], "map_revision": q.get("revision"), "map_id": q.get("id"), "trang_thai": "KHONG_THAY_DONG",
                            "ly_do": "Dòng của quyết định ghép tay không có trong bộ đã đọc của lần chạy này (tệp bị bỏ/đổi raw/không đọc được)"})
    da_ap = {x["row_id"] for x in nhat_ky if x["trang_thai"] == "DA_AP"}
    for d in hieu_luc["tai_lieu"]:
        for ln in d["dong"]:
            ln["ghep_tay"] = ln.get("row_id") in da_ap
    return auto, hieu_luc, nhat_ky


# ================================================================================================== so sánh typed theo hạng mục / cặp chứng từ
def _dvt_trang_thai(pla, a, b) -> str:
    a, b = str(a or "").strip(), str(b or "").strip()
    if not a or not b:
        return "KHONG_RO"
    return "CUNG" if pla._dvt(a) == pla._dvt(b) else "KHAC"


def _la_so(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


def _ss(tt: str, ly_do: str | None = None, **kw) -> dict:
    return {"trang_thai": tt, "ly_do": ly_do, **kw}


def so_sanh_hang_muc(kq: dict, ctx: dict, pla) -> dict:
    """Theo TỪNG hạng mục: C01 (KL kỳ này ↔ Σ BB nghiệm thu) và C03 (KL lũy kế ↔ Σ giao nhận) có so được không, dựa trên đúng toán hạng nhánh nguồn
    dùng: kl_kn/kl_lk của chính hạng mục (NULL ≠ 0), số lượng + ĐVT từng dòng đã ghép (ĐVT chuẩn hóa nguồn, không quy đổi), chứng từ cùng loại chưa đọc
    dòng (tổng có thể thiếu). Không đòi hạng mục không liên quan có đủ lượng."""
    docs = [d for d in kq["tai_lieu"] if not d.get("bo")]
    hm = {h["khoa"]: h for h in kq["hang_muc"]}
    l2 = ctx.get("nguon") == "L2"
    ly_l2 = ctx.get("ly_do") or "Chưa có KL kỳ này/lũy kế đã công bố (L2 hiện hành)"
    theo = {t: [d for d in docs if d.get("loai") == t] for t in ("BB_NT", "BB_GN")}
    doc_chua_dong = {t: [d for d in theo[t] if d.get("trang_thai_dong") not in ("CHECKED", "LIMITED")] for t in theo}
    dong = {t: {} for t in theo}
    for t in theo:
        for d in theo[t]:
            for ln in d["dong"]:
                if ln.get("khoa") in hm:
                    dong[t].setdefault(ln["khoa"], []).append(ln)

    def kiem_dong(rows, h):
        null = sum(1 for ln in rows if ln.get("so_luong") is None)
        dv = Counter(_dvt_trang_thai(pla, ln.get("dvt"), h.get("dvt")) for ln in rows)
        return null, dv.get("KHAC", 0), dv.get("KHONG_RO", 0)
    out = {}
    for k, h in hm.items():
        # C01
        rows, kn = dong["BB_NT"].get(k, []), h.get("kl_kn")
        if not l2:
            c01 = _ss("CHUA_SO_DUOC", ly_l2)
        elif kn is not None and not _la_so(kn):
            c01 = _ss("CHUA_SO_DUOC", f"KL kỳ này của hạng mục không phải số ({str(kn)[:40]}) — không so")
        elif not theo["BB_NT"]:
            c01 = _ss("CHUA_SO_DUOC" if kn not in (None, 0) else "KHONG_AP_DUNG", "Không có BB nghiệm thu đã đọc trong bộ")
        elif kn is None:
            c01 = (_ss("CHUA_SO_DUOC", f"KL kỳ này của hạng mục NULL nhưng có {len(rows)} dòng BB nghiệm thu — nguồn coi NULL như 0, không so") if rows
                   else _ss("KHONG_AP_DUNG", "KL kỳ này trống (NULL), không có dòng nghiệm thu ghép vào", kl_null=True))
        elif kn <= 1e-9:
            c01 = (_ss("NGUON_KHONG_SO", f"KL kỳ này = {kn:g} tường minh nhưng có {len(rows)} dòng nghiệm thu — nhánh nguồn bỏ qua hạng mục KL ≤ 0") if rows
                   else _ss("SO_DUOC", f"KL kỳ này = {kn:g} tường minh, không có dòng nghiệm thu", kl_kn=kn, nt=None))
        else:
            null, khac, khong_ro = kiem_dong(rows, h)
            if null:
                c01 = _ss("CHUA_SO_DUOC", f"{null} dòng nghiệm thu không đọc được số lượng (NULL — nguồn cộng như 0)")
            elif khac or khong_ro:
                c01 = _ss("CHUA_SO_DUOC", f"{khac} dòng khác ĐVT, {khong_ro} dòng không rõ ĐVT so với hạng mục ({h.get('dvt') or '—'}) — không quy đổi")
            elif doc_chua_dong["BB_NT"]:
                c01 = _ss("CHUA_SO_DUOC", f"{len(doc_chua_dong['BB_NT'])} BB nghiệm thu chưa đọc được dòng hàng — tổng nghiệm thu có thể thiếu")
            else:
                c01 = _ss("SO_DUOC", None, kl_kn=kn, nt=sum(float(ln["so_luong"]) for ln in rows) if rows else None)
        # C03
        rows, lk = dong["BB_GN"].get(k, []), h.get("kl_lk")
        if not rows:
            c03 = (_ss("CHUA_SO_DUOC", f"{len(doc_chua_dong['BB_GN'])} BB giao nhận chưa đọc được dòng hàng — không biết hạng mục có được giao hay không")
                   if doc_chua_dong["BB_GN"] and lk not in (None, 0) and l2 else
                   _ss("KHONG_AP_DUNG", "Không có dòng giao nhận ghép vào hạng mục (C03 nguồn chỉ xét hạng mục có BB giao nhận)"))
        elif not l2:
            c03 = _ss("CHUA_SO_DUOC", ly_l2)
        elif lk is not None and not _la_so(lk):
            c03 = _ss("CHUA_SO_DUOC", f"KL lũy kế của hạng mục không phải số ({str(lk)[:40]}) — không so")
        elif lk is None:
            c03 = _ss("CHUA_SO_DUOC", f"KL lũy kế của hạng mục NULL nhưng có {len(rows)} dòng giao nhận — nguồn bỏ qua so sánh")
        else:
            null, khac, khong_ro = kiem_dong(rows, h)
            if null:
                c03 = _ss("CHUA_SO_DUOC", f"{null} dòng giao nhận không đọc được số lượng (NULL — nguồn cộng như 0)")
            elif khac or khong_ro:
                c03 = _ss("CHUA_SO_DUOC", f"{khac} dòng khác ĐVT, {khong_ro} dòng không rõ ĐVT so với hạng mục ({h.get('dvt') or '—'}) — không quy đổi")
            elif doc_chua_dong["BB_GN"]:
                c03 = _ss("CHUA_SO_DUOC", f"{len(doc_chua_dong['BB_GN'])} BB giao nhận chưa đọc được dòng hàng — tổng giao có thể thiếu")
            else:
                c03 = _ss("SO_DUOC", None, kl_lk=lk, gn=sum(float(ln["so_luong"]) for ln in rows))
        out[k] = {"C01": c01, "C03": c03}
    return out


def cap_c06(ct, kq: dict, pla) -> list:
    """Từng CẶP dòng GN ↔ dòng CO/CQ/PL mà nguồn coi là cùng hàng (`chung_tu._cung_hang` nguồn): số lượng so được CHỈ khi hai ĐVT có và trùng sau
    chuẩn hóa nguồn và cả hai số lượng có (NULL ≠ 0); không tự quy đổi. Số lô/serial (CO/CQ) và ngày kiểm riêng — vẫn kiểm được khi lượng chưa so được."""
    docs = [d for d in kq["tai_lieu"] if not d.get("bo")]
    gn = [d for d in docs if d.get("loai") == "BB_GN"]
    out = []
    for d in gn:
        for ln in d["dong"]:
            for t in ("CO", "CQ", "PL"):
                for d2 in (x for x in docs if x.get("loai") == t):
                    for l2 in d2["dong"]:
                        if not ct._cung_hang(ln, l2):
                            continue
                        dv = _dvt_trang_thai(pla, ln.get("dvt"), l2.get("dvt"))
                        thieu = [x for x, v in (("giao nhận", ln.get("so_luong")), (t, l2.get("so_luong"))) if v is None]
                        if dv == "CUNG" and not thieu:
                            sl = _ss("SO_DUOC")
                        else:
                            sl = _ss("CHUA_SO_DUOC", "; ".join(x for x in (
                                {"KHAC": f"ĐVT khác ({ln.get('dvt')} ↔ {l2.get('dvt')})", "KHONG_RO": "ĐVT thiếu ở một bên"}.get(dv, ""),
                                ("số lượng NULL ở " + ", ".join(thieu)) if thieu else "") if x) + " — nguồn so số lượng không theo ĐVT; không quy đổi")
                        if t in ("CO", "CQ"):
                            lo = (_ss("SO_DUOC") if ct._lo(ln.get("lo")) and ct._lo(l2.get("lo"))
                                  else _ss("CHUA_SO_DUOC", "Thiếu số lô/serial ở một bên"))
                        else:
                            lo = _ss("KHONG_AP_DUNG", "Nguồn chỉ so số lô với CO/CQ")
                        ngay = _ss("SO_DUOC") if d.get("ngay") and d2.get("ngay") else _ss("CHUA_SO_DUOC", "Thiếu ngày chứng từ ở một bên")
                        out.append({"gn_tep_id": d["tep_id"], "gn_tai_lieu": d["ten"], "gn_nhan": str(ln.get("model") or ln.get("ten") or ""),
                                    "gn_row_id": ln.get("row_id"), "gn_ten": ln.get("ten"), "gn_dvt": ln.get("dvt"),
                                    "gn_so_luong": ln.get("so_luong"), "loai": t, "doi_tep_id": d2["tep_id"], "doi_row_id": l2.get("row_id"),
                                    "doi_ten": l2.get("ten"), "doi_dvt": l2.get("dvt"), "doi_so_luong": l2.get("so_luong"), "dvt": dv,
                                    "so_luong": sl, "lo": lo, "ngay": ngay})
    return out


def chu_thich_phat_hien(kq: dict, so_sanh: dict, caps: list, chua_doc_dong: list) -> list:
    """Ghi chú L3 cho finding NGUỒN (danh sách riêng theo id — finding gốc không sửa/xóa): C01/C03 của hạng mục chưa so được; C06 số lượng của cặp
    khác/không rõ ĐVT hoặc NULL; C05 'thiếu' khi bộ còn chứng từ chưa đọc dòng hàng/tệp chưa đọc."""
    hm = {h["khoa"]: h for h in kq["hang_muc"]}
    theo_item = {}
    for k, h in hm.items():
        for x in {h.get("ma_hm"), str(h.get("ten") or "")[:60]} - {None, ""}:
            theo_item.setdefault(x, k)
    out = []
    for f in kq.get("phat_hien") or []:
        if f.get("code") in ("C01", "C03"):
            k = theo_item.get(f.get("item"))
            s = (so_sanh.get(k) or {}).get(f["code"]) if k else None
            if s and s["trang_thai"] != "SO_DUOC":
                out.append({"id": f.get("id"), "code": f["code"], "so_sanh": s["trang_thai"], "ghi_chu": "Toán hạng chưa so được: " + str(s.get("ly_do"))})
        elif f.get("code") == "C06" and ("số lượng trên" in str(f.get("title")) or "packing list" in str(f.get("title"))):
            # cùng nhãn nguồn dùng trong tiêu đề C06 (`model or ten`, 60 ký tự) + cùng BB giao nhận + đúng loại chứng từ đối chiếu
            tieu_de = str(f.get("title") or "")
            loai_f = "PL" if "packing list" in tieu_de else next((t for t in ("CO", "CQ", "PL") if f"trên {t} " in tieu_de), None)
            lien = [c for c in caps if c["gn_tai_lieu"] == f.get("tai_lieu") and c["loai"] == loai_f and tieu_de.startswith(f"'{c['gn_nhan'][:60]}'")]
            xau = [c for c in lien if c["so_luong"]["trang_thai"] != "SO_DUOC"]
            if xau:
                out.append({"id": f.get("id"), "code": "C06", "so_sanh": "CHUA_SO_DUOC",
                            "ghi_chu": f"{len(xau)} cặp liên quan chưa so được số lượng: " + "; ".join(sorted({c['so_luong']['ly_do'] for c in xau}))[:500]})
        elif f.get("code") == "C05" and chua_doc_dong:
            out.append({"id": f.get("id"), "code": "C05", "so_sanh": "CHUA_SO_DUOC",
                        "ghi_chu": f"{len(chua_doc_dong)} tệp/chứng từ trong bộ chưa đọc được dòng hàng — 'thiếu' của nguồn chưa chắc chắn"})
    return out


# ================================================================================================== coverage companion
def coverage_l3(kq: dict, tat_ca: list, ctx: dict, so_sanh: dict, caps: list) -> dict:
    """Trạng thái kiểm C01–C09 + TAI_LIEU/DONG_HANG/CAN_CU theo căn cứ THẬT (so sánh typed theo hạng mục/cặp + trạng thái đọc dòng). Vắng ≠ không áp
    dụng ≠ lỗi. Không Green khi thiếu BB NT/GN, dòng hàng, toán hạng lượng, ĐVT so được, ngày, phân loại, tham chiếu HĐ hoặc căn cứ L2 hiện hành."""
    cov = {}

    def dat(ma, tt, ly_do, **kw):
        cov[ma] = {"trang_thai": tt, "ly_do": ly_do, **kw}
    docs = [d for d in kq["tai_lieu"] if not d.get("bo")]
    chua_doc = [d for d in tat_ca if not d.get("bo") and d["trang_thai_doc"] in ("NOT_CONFIGURED", "KHONG_HO_TRO", "ERROR")]
    gioi_han = [d for d in docs if d["trang_thai_doc"] == "LIMITED"]
    theo = {t: [d for d in docs if d.get("loai") == t] for t in ("BB_NT", "BB_GN", "PL", "CO", "CQ", "BB_LD", "KHAC")}
    doc_dong = {t: [d for d in v if d.get("trang_thai_dong") in ("CHECKED", "LIMITED")] for t, v in theo.items()}
    chua_dong = [d for d in docs if d.get("loai") != "KHAC" and d.get("trang_thai_dong") not in ("CHECKED", "LIMITED")]
    hm = {h["khoa"]: h for h in kq["hang_muc"]}
    l2 = ctx.get("nguon") == "L2"
    ghi_chua_doc = f"; {len(chua_doc)} tệp chưa đọc được (provider/không hỗ trợ/lỗi) — có thể chứa chứng từ liên quan" if chua_doc else ""

    def dem_ss(ma):
        return Counter(v[ma]["trang_thai"] for v in so_sanh.values())

    def chua_ghep(ts):
        return sum(1 for t in ts for d in theo[t] for ln in d["dong"] if not ln.get("khoa"))
    # C01 / C03 theo toán hạng thật của từng hạng mục
    for ma, loai, ten in (("C01", "BB_NT", "BB nghiệm thu"), ("C03", "BB_GN", "BB giao nhận")):
        c = dem_ss(ma)
        xau = [f"{k}: {v[ma]['ly_do']}" for k, v in so_sanh.items() if v[ma]["trang_thai"] == "CHUA_SO_DUOC"]
        cg = chua_ghep([loai])
        if not theo[loai]:
            dat(ma, "INCOMPLETE", f"Không có {ten} đã đọc trong bộ" + ghi_chua_doc)
        elif not doc_dong[loai]:
            dat(ma, "INCOMPLETE", f"{len(theo[loai])} {ten} chưa đọc được dòng hàng (dạng form/không bảng) — cần Local AI (chưa cấu hình)")
        elif not l2:
            dat(ma, "INCOMPLETE", ctx.get("ly_do") or "Chưa có KL đã công bố (L2 hiện hành) — không so lượng")
        elif c.get("CHUA_SO_DUOC"):
            dat(ma, "INCOMPLETE", f"{c['CHUA_SO_DUOC']} hạng mục chưa so được lượng: " + " | ".join(xau[:5]), so_sanh=dict(c))
        elif ma == "C01" and not c.get("SO_DUOC") and not c.get("NGUON_KHONG_SO") and any(h.get("kl_kn") is None for h in hm.values()):
            dat(ma, "INCOMPLETE", "Không hạng mục nào có KL kỳ này để so (KL kỳ này NULL)", so_sanh=dict(c))
        elif not c.get("SO_DUOC") and not c.get("NGUON_KHONG_SO"):
            dat(ma, "LIMITED" if cg else "NOT_AVAILABLE", (f"{cg} dòng {ten} chưa ghép hạng mục; " if cg else "") + "không có hạng mục nào so được", so_sanh=dict(c))
        elif c.get("NGUON_KHONG_SO") or cg or chua_doc or gioi_han or len(doc_dong[loai]) < len(theo[loai]):
            dat(ma, "LIMITED", "; ".join(x for x in (f"{c['NGUON_KHONG_SO']} hạng mục KL ≤ 0 có dòng chứng từ (nguồn không so)" if c.get("NGUON_KHONG_SO") else "",
                                                     f"{cg} dòng {ten} chưa ghép hạng mục" if cg else "",
                                                     "có tệp giới hạn/chưa đọc" if (chua_doc or gioi_han) else "") if x) + ghi_chua_doc, so_sanh=dict(c))
        else:
            dat(ma, "CHECKED", f"{c.get('SO_DUOC', 0)} hạng mục so được lượng (cùng ĐVT, có số lượng, toán hạng có)", so_sanh=dict(c))
    # C02
    if not ctx.get("ngay_nt"):
        dat("C02", "INCOMPLETE", "Đợt chưa có ngày nghiệm thu")
    elif not theo["BB_NT"]:
        dat("C02", "INCOMPLETE", "Không có BB nghiệm thu đã đọc" + ghi_chua_doc)
    elif any(not d.get("ngay") for d in theo["BB_NT"]):
        dat("C02", "LIMITED", f"{sum(1 for d in theo['BB_NT'] if not d.get('ngay'))} BB nghiệm thu không có ngày — không so được")
    else:
        dat("C02", "CHECKED", "Ngày mọi BB nghiệm thu đã đọc được so với ngày nghiệm thu của đợt")
    # C04
    rows = [ln for t in ("BB_NT", "BB_GN") for d in theo[t] for ln in d["dong"]]
    if not hm:
        dat("C04", "INCOMPLETE", ctx.get("ly_do") or "Chưa có hạng mục căn cứ")
    elif not rows:
        dat("C04", "NOT_AVAILABLE", "Không có dòng hàng BB nghiệm thu/giao nhận đã đọc" + ghi_chua_doc)
    elif gioi_han or chua_doc or any(d not in doc_dong[t] for t in ("BB_NT", "BB_GN") for d in theo[t]):
        dat("C04", "LIMITED", f"Đã thử ghép {len(rows)} dòng; có tệp giới hạn/chưa đọc/chưa đọc dòng" + ghi_chua_doc)
    else:
        dat("C04", "CHECKED", f"Đã thử ghép {len(rows)} dòng với {len(hm)} hạng mục ({ctx.get('nguon')}) — ghép mờ không phải xác nhận")
    # C05
    if not theo["BB_GN"]:
        dat("C05", "INCOMPLETE", "Không có BB giao nhận đã đọc — không xác định được hàng đã giao cần CO/CQ/packing list" + ghi_chua_doc)
    elif not doc_dong["BB_GN"]:
        dat("C05", "INCOMPLETE", "BB giao nhận chưa đọc được dòng hàng — không xác định được hàng đã giao")
    elif chua_doc or chua_dong:
        dat("C05", "INCOMPLETE", f"{len(chua_doc) + len(chua_dong)} tệp/chứng từ chưa đọc được dòng hàng — CO/CQ/packing list có thể nằm trong đó; "
                                 "phát hiện 'thiếu' của nguồn chưa chắc chắn" + ghi_chua_doc)
    else:
        dat("C05", "CHECKED", "Mọi tệp trong bộ đã đọc dòng hàng; đối chiếu CO/CQ/PL/BB lắp đặt theo dòng giao nhận")
    # C06 theo cặp
    doi = [d for t in ("CO", "CQ", "PL") for d in theo[t]]
    doi_dong = [d for t in ("CO", "CQ", "PL") for d in doc_dong[t]]
    sl = Counter(c["so_luong"]["trang_thai"] for c in caps)
    lo = Counter(c["lo"]["trang_thai"] for c in caps)
    if not theo["BB_GN"]:
        dat("C06", "INCOMPLETE", "Không có BB giao nhận đã đọc" + ghi_chua_doc)
    elif not doc_dong["BB_GN"]:
        dat("C06", "INCOMPLETE", "BB giao nhận chưa đọc được dòng hàng")
    elif not doi:
        dat("C06", "NOT_AVAILABLE", "Không có CO/CQ/packing list đã đọc để đối chiếu chéo" + ghi_chua_doc)
    elif not doi_dong:
        dat("C06", "INCOMPLETE", f"{len(doi)} CO/CQ/packing list chưa đọc được dòng hàng (dạng form) — cần Local AI (chưa cấu hình)")
    elif not caps:
        dat("C06", "LIMITED", "Không có cặp dòng giao nhận ↔ CO/CQ/PL nào nguồn coi là cùng hàng" + ghi_chua_doc, cap={})
    elif sl.get("CHUA_SO_DUOC") and not sl.get("SO_DUOC"):
        dat("C06", "INCOMPLETE", f"{sl['CHUA_SO_DUOC']}/{len(caps)} cặp chưa so được số lượng (ĐVT khác/không rõ hoặc NULL); số lô so được "
                                 f"{lo.get('SO_DUOC', 0)} cặp", cap={"so_luong": dict(sl), "lo": dict(lo)})
    elif sl.get("CHUA_SO_DUOC") or len(doi_dong) < len(doi) or chua_doc or gioi_han:
        dat("C06", "LIMITED", "; ".join(x for x in (f"{sl['CHUA_SO_DUOC']}/{len(caps)} cặp chưa so được số lượng (ĐVT khác/không rõ hoặc NULL)"
                                                    if sl.get("CHUA_SO_DUOC") else "",
                                                    f"{len(doi) - len(doi_dong)} CO/CQ/PL chưa đọc dòng" if len(doi_dong) < len(doi) else "",
                                                    "có tệp giới hạn/chưa đọc" if (chua_doc or gioi_han) else "") if x)
            + f"; số lô so được {lo.get('SO_DUOC', 0)} cặp" + ghi_chua_doc, cap={"so_luong": dict(sl), "lo": dict(lo)})
    else:
        dat("C06", "CHECKED", f"{len(caps)} cặp so được số lượng cùng ĐVT; số lô so được {lo.get('SO_DUOC', 0)} cặp", cap={"so_luong": dict(sl), "lo": dict(lo)})
    # C07
    lien_quan = [d for d in docs if d.get("loai") in ("BB_NT", "BB_GN", "BB_LD", "CO", "CQ")]
    thieu_ngay = [d for d in lien_quan if not d.get("ngay")]
    if not lien_quan:
        dat("C07", "INCOMPLETE", "Không có chứng từ có mốc thời gian đã đọc" + ghi_chua_doc)
    elif thieu_ngay or not ctx.get("ngay_nt") or not ctx.get("ngay_ky_hd"):
        dat("C07", "LIMITED", "; ".join(x for x in (f"{len(thieu_ngay)} chứng từ không có ngày" if thieu_ngay else "",
                                                    "đợt chưa có ngày nghiệm thu" if not ctx.get("ngay_nt") else "",
                                                    "chưa có ngày ký HĐ typed (TC-02)" if not ctx.get("ngay_ky_hd") else "") if x))
    else:
        dat("C07", "CHECKED", "Mốc ngày các chứng từ, ngày nghiệm thu và ngày ký HĐ đều có")
    # C08
    if not RE_SO_HD.match(str(ctx.get("so_hd") or "")):
        dat("C08", "INCOMPLETE", f"Số HĐ chuẩn '{ctx.get('so_hd') or ''}' không tách được dạng NNNN/YYYY — không so số HĐ trên chứng từ (không coi là cùng HĐ)")
    elif not docs:
        dat("C08", "INCOMPLETE", "Không có chứng từ đã đọc")
    elif any(not d.get("hd_ref") for d in docs if d.get("loai") != "KHAC"):
        dat("C08", "LIMITED", f"{sum(1 for d in docs if d.get('loai') != 'KHAC' and not d.get('hd_ref'))} chứng từ không ghi số HĐ đọc được")
    else:
        dat("C08", "CHECKED", "Số HĐ ghi trên chứng từ đã đọc được so với số HĐ chuẩn")
    # C09
    if not docs:
        dat("C09", "INCOMPLETE", "Không có chứng từ nào đọc được" + ghi_chua_doc)
    elif chua_doc:
        dat("C09", "LIMITED", "Kiểm số/ngày/dòng hàng cho tệp đã đọc" + ghi_chua_doc)
    else:
        dat("C09", "CHECKED", f"Kiểm số/ngày/dòng hàng cho {len(docs)} chứng từ (chứng từ không đọc được dòng có phát hiện C09 của nguồn)")
    # phụ: tài liệu / dòng hàng / căn cứ
    tt_doc = Counter(d["trang_thai_doc"] for d in tat_ca if not d.get("bo"))
    khac = theo["KHAC"]
    if chua_doc:
        dat("TAI_LIEU", "INCOMPLETE", f"{len(chua_doc)} tệp chưa đọc được", dem=dict(tt_doc))
    elif gioi_han or khac or chua_dong:
        dat("TAI_LIEU", "LIMITED", "; ".join(x for x in (f"{len(gioi_han)} tệp đọc có giới hạn" if gioi_han else "",
                                                        f"{len(khac)} tệp chưa phân loại (KHAC)" if khac else "",
                                                        f"{len(chua_dong)} chứng từ chưa đọc được dòng hàng" if chua_dong else "") if x), dem=dict(tt_doc))
    else:
        dat("TAI_LIEU", "CHECKED", f"{len(docs)} tệp đọc native đầy đủ trong giới hạn nguồn", dem=dict(tt_doc))
    tat_dong = [ln for d in docs for ln in d["dong"]]
    khong_vt = [ln for ln in tat_dong if (ln.get("vi_tri_vat_ly") or {}).get("trang_thai") != "CHECKED"]
    if not tat_dong:
        dat("DONG_HANG", "NOT_AVAILABLE", "Không có dòng hàng nào đọc được" + (f"; {len(chua_dong)} chứng từ chưa đọc dòng" if chua_dong else ""))
    elif khong_vt or chua_dong:
        dat("DONG_HANG", "LIMITED", "; ".join(x for x in (f"{len(khong_vt)}/{len(tat_dong)} dòng không ánh xạ được vị trí vật lý" if khong_vt else "",
                                                         f"{len(chua_dong)} chứng từ chưa đọc dòng hàng" if chua_dong else "") if x))
    else:
        dat("DONG_HANG", "CHECKED", f"{len(tat_dong)} dòng có vị trí vật lý (sheet/bảng + dòng)")
    if l2:
        dat("CAN_CU", "CHECKED", "Hạng mục từ kết quả L2 đã công bố, còn khớp căn cứ hiện hành (máy chủ kiểm tương ứng)")
    elif ctx.get("l2_cu"):
        dat("CAN_CU", "INCOMPLETE", ctx.get("ly_do") or "Kết quả L2 đã công bố không còn khớp căn cứ hiện hành", l2_cu=ctx["l2_cu"])
    elif ctx.get("nguon") == "BOQ":
        dat("CAN_CU", "LIMITED", ctx.get("ly_do") or "Chỉ BOQ hiệu lực")
    else:
        dat("CAN_CU", "INCOMPLETE", ctx.get("ly_do") or "Chưa có căn cứ hạng mục")
    return cov


# ================================================================================================== báo cáo XLSX L3
TEN_SHEET = ("Tóm tắt", "Ma trận", "Phát hiện C01-C09", "Phạm vi kiểm", "Chứng từ", "Dòng hàng", "Đối chiếu chéo C06", "Ghép tay & lịch sử", "Giới hạn")


def bao_cao_xlsx(kq: dict) -> bytes:
    """Báo cáo L3 (KHÔNG phải PDF đợt được duyệt): tóm tắt, ma trận (+ so được/chưa so được theo hạng mục), phát hiện C01–C09 (+ ghi chú L3 riêng),
    phạm vi kiểm, chứng từ (+ đọc dòng/thích nghi cột), dòng hàng + vị trí, cặp C06, ghép tay & lịch sử, giới hạn. Giá trị chuỗi giữ nguyên; số là số
    nguồn; ước tính tiền ghi rõ là ước tính."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = TEN_SHEET[0]
    pv = kq.get("provenance") or {}
    for r in (["Báo cáo Chứng từ L3 — phát hiện kỹ thuật, KHÔNG phải duyệt/PDF đợt/nghiệm thu/công nợ"],
              ["Số HĐ", kq.get("so_hd")], ["Ngày nghiệm thu đợt", kq.get("ngay_nt")], ["Căn cứ hạng mục", pv.get("nguon_hang_muc")],
              ["Lý do căn cứ", pv.get("ly_do_can_cu")], ["L2 cũ (không dùng)", str(pv.get("l2_cu")) if pv.get("l2_cu") else None],
              ["Engine", kq.get("engine")], ["Basis SHA-256", kq.get("basis_sha256")], ["Revision metadata", kq.get("revision")],
              ["Trạng thái", kq.get("trang_thai")], ["Phát hiện Cao/TB/Thấp", ", ".join(f"{k}: {v}" for k, v in (kq.get("dem") or {}).items())],
              ["Ghi chú tiền", "Ảnh hưởng là ước tính float của thuật toán nguồn (VAT nếu có căn cứ) — không phải số NT/thuế/công nợ được chấp nhận"]):
        ws.append(r)
    m = wb.create_sheet(TEN_SHEET[1])
    m.append(["Khóa", "Mã HM", "Hạng mục", "ĐVT", "KL kỳ này", "KL lũy kế", "KL nghiệm thu", "BB nghiệm thu", "So C01", "Lý do C01", "Đã giao",
              "BB giao nhận", "So C03", "Lý do C03", "CO", "CQ", "Packing list", "BB lắp đặt"])
    for r in kq.get("ma_tran") or []:
        s = r.get("so_sanh") or {}
        m.append([r.get("khoa"), r.get("ma_hm"), r.get("ten"), r.get("dvt"), r.get("kl_kn"), r.get("kl_lk"), r.get("nt"), ", ".join(r.get("nt_docs") or []),
                  (s.get("C01") or {}).get("trang_thai"), (s.get("C01") or {}).get("ly_do"), r.get("gn"), ", ".join(r.get("gn_docs") or []),
                  (s.get("C03") or {}).get("trang_thai"), (s.get("C03") or {}).get("ly_do"), ", ".join(r.get("co") or []), ", ".join(r.get("cq") or []),
                  ", ".join(r.get("pl") or []), ", ".join(r.get("ld") or [])])
    p = wb.create_sheet(TEN_SHEET[2])
    p.append(["Mã", "Mức", "Tiêu đề", "Chi tiết", "Hạng mục", "Chứng từ", "Ảnh hưởng ước tính (đồng)", "Ghi chú L3 (riêng, không sửa finding)"])
    ghi = {}
    for x in kq.get("chu_thich_phat_hien") or []:
        ghi.setdefault(x.get("id"), []).append(x.get("ghi_chu"))
    for f in kq.get("phat_hien") or []:
        p.append([f.get("id"), f.get("level"), f.get("title"), f.get("detail"), f.get("item"), f.get("tai_lieu"), f.get("amount"),
                  " | ".join(ghi.get(f.get("id")) or []) or None])
    c = wb.create_sheet(TEN_SHEET[3])
    c.append(["Mã", "Trạng thái kiểm", "Lý do"])
    for ma, v in (kq.get("coverage") or {}).items():
        c.append([ma, v.get("trang_thai"), v.get("ly_do")])
    t = wb.create_sheet(TEN_SHEET[4])
    t.append(["Tệp", "tep_id", "raw SHA-256", "Byte", "Media", "Mục hồ sơ", "Trạng thái đọc", "Lý do", "Đọc dòng hàng", "Lý do dòng", "Loại (hiệu lực)",
              "Số", "Ngày", "Bỏ khỏi bộ", "Loại trích", "Số trích", "Ngày trích", "HĐ ghi trên chứng từ", "Số dòng hàng", "Thích nghi cột (alias)"])
    for d in kq.get("tai_lieu") or []:
        tr = d.get("trich") or {}
        t.append([d.get("ten"), d.get("tep_id"), d.get("raw_sha256"), d.get("byte_length"), d.get("media_type"), d.get("muc"), d.get("trang_thai_doc"),
                  d.get("ly_do_doc"), d.get("trang_thai_dong"), d.get("ly_do_dong"), d.get("loai"), d.get("so"), d.get("ngay"), bool(d.get("bo")),
                  tr.get("loai"), tr.get("so"), tr.get("ngay"), ", ".join("/".join(x) for x in d.get("hd_ref") or []), len(d.get("dong") or []),
                  "; ".join(f"{x.get('tieu_de')} → {x.get('alias')} ({x.get('ap')})" for x in d.get("thich_nghi_cot") or []) or None])
    dh = wb.create_sheet(TEN_SHEET[5])
    dh.append(["Tệp", "row_id", "Vị trí nguồn", "Sheet/Bảng vật lý", "Dòng vật lý", "Trạng thái vị trí", "Tên", "Model", "Quy cách", "ĐVT", "Số lượng",
               "Số lô", "Xuất xứ", "NSX", "Ghép (hiệu lực)", "Độ khớp", "Ghép tay", "Ghép auto"])
    auto = {(ln.get("row_id")): ln.get("khoa") for d in (pv.get("auto") or {}).get("tai_lieu") or [] for ln in d.get("dong") or []}
    for d in kq.get("tai_lieu") or []:
        for ln in d.get("dong") or []:
            vt = ln.get("vi_tri_vat_ly") or {}
            dh.append([d.get("ten"), ln.get("row_id"), ln.get("vi_tri"), vt.get("sheet") or vt.get("bang"), vt.get("dong"), vt.get("trang_thai"), ln.get("ten"),
                       ln.get("model"), ln.get("quy_cach"), ln.get("dvt"), ln.get("so_luong"), ln.get("lo"), ln.get("xuat_xu"), ln.get("nsx"), ln.get("khoa"),
                       ln.get("khop"), bool(ln.get("ghep_tay")), auto.get(ln.get("row_id"))])
    c6 = wb.create_sheet(TEN_SHEET[6])
    c6.append(["Dòng giao nhận", "ĐVT GN", "SL GN", "Loại", "Dòng đối chiếu", "ĐVT", "SL", "ĐVT so", "Số lượng", "Lý do số lượng", "Số lô", "Ngày"])
    for x in kq.get("c06_cap") or []:
        c6.append([x.get("gn_ten"), x.get("gn_dvt"), x.get("gn_so_luong"), x.get("loai"), x.get("doi_ten"), x.get("doi_dvt"), x.get("doi_so_luong"), x.get("dvt"),
                   (x.get("so_luong") or {}).get("trang_thai"), (x.get("so_luong") or {}).get("ly_do"), (x.get("lo") or {}).get("trang_thai"),
                   (x.get("ngay") or {}).get("trang_thai")])
    g = wb.create_sheet(TEN_SHEET[7])
    g.append(["Loại", "Mã/Revision", "Chi tiết", "Người", "Lúc"])
    for x in pv.get("ghep_tay") or []:
        g.append(["Ghép tay", x.get("map_revision"), f"{x.get('row_id')} → {x.get('khoa')} ({x.get('trang_thai')}) {x.get('ly_do') or ''} "
                                                      f"lưu={x.get('dich_luu')} hiện hành={x.get('dich_hien_hanh')}", None, None])
    for x in pv.get("lich_su_revision") or []:
        g.append(["Revision metadata", x.get("revision"), str(x.get("thay_doi")), x.get("tao_boi"), x.get("tao_luc")])
    for x in pv.get("metadata_sua") or []:
        g.append(["Metadata áp dụng", x.get("revision"), str(x), None, None])
    gh = wb.create_sheet(TEN_SHEET[8])
    gh.append(["Phạm vi", "Giới hạn / provider"])
    for d in kq.get("tai_lieu") or []:
        for x in d.get("gioi_han") or []:
            gh.append([d.get("ten"), x])
        if d.get("trang_thai_doc") in ("NOT_CONFIGURED", "KHONG_HO_TRO", "ERROR"):
            gh.append([d.get("ten"), f"{d.get('trang_thai_doc')}: {d.get('ly_do_doc')}"])
        elif d.get("trang_thai_dong") == "NOT_CONFIGURED":
            gh.append([d.get("ten"), f"Dòng hàng NOT_CONFIGURED: {d.get('ly_do_dong')}"])
    for k, v in (pv.get("provider") or {}).items():
        gh.append([f"Provider {k}", f"{v.get('trang_thai')}: {v.get('ly_do')}"])
    gh.append(["Ngưỡng nguồn", "Phân loại 30 dòng đầu; số 25 dòng; ngày 60–80 dòng; tiêu đề bảng 4 dòng; XLSX 400×30 ô cached; khớp hạng mục ≥0.80, cách biệt 0.04"])
    gh.append(["ĐVT", "Không quy đổi đơn vị; khác/không rõ ĐVT → chưa so được lượng (C01/C03/C06)"])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


# ================================================================================================== một lần chạy L3
def tinh(vao: dict, thu_muc: Path) -> dict:
    """Một lần chạy L3 trên bộ tệp đã giữ lại trong thư mục lần chạy. Không mạng/PG. Ghi báo cáo vào thu_muc (tên cố định, ghi một lần)."""
    from ..ha_tang.store import write_immutable
    from . import nguon_review as NR
    from . import review_compute as RC
    thu_muc = Path(thu_muc)
    if vao.get("che_do") != CHE_DO:
        raise RuntimeError("Đầu vào không phải chế độ L3")
    basis = vao["basis"]
    ct, pla = NR._m("may_chu.chung_tu"), NR._m("may_chu.phu_luc_ai")
    tat_ca = []
    for tl in sorted(vao.get("tai_lieu") or [], key=lambda x: (str(x.get("muc") or ""), str(x["ten_goc"]), str(x["tep_id"]))):
        path = duong_lam_viec(thu_muc, tl["work_ref"])
        raw = path.read_bytes()
        if _sha(raw) != tl["raw_sha256"] or len(raw) != int(tl["byte_length"]):
            raise RuntimeError(f"Bản làm việc của tệp {tl['tep_id']} khác raw SHA/độ dài đã chụp — dừng")
        tat_ca.append(doc_tai_lieu(ct, tl, path, raw))
    sua = ap_metadata(ct, tat_ca, basis.get("revision"))
    for d in tat_ca:
        gan_trang_thai_dong(d)
    hm, ctx = hang_muc(basis)
    hd = _thong_tin_hd(basis)
    ctx.update(hd)
    doc_duoc = [d for d in tat_ca if d["trang_thai_doc"] in ("CHECKED", "LIMITED")]
    kq_goc = {"hang_muc": hm, "tai_lieu": doc_duoc, "ngay_nt": ctx["ngay_nt"], "ngay_ky_hd": hd["ngay_ky_hd"], "vat": hd["vat"], "so_hd": hd["so_hd"]}
    ghep_tay = kiem_ghep_tay(basis.get("manual_map_l3") or [], hm)
    auto, hl, nhat_ky = doi_chieu_hai_ban(ct, kq_goc, ghep_tay)
    ss = so_sanh_hang_muc(hl, ctx, pla)
    caps = cap_c06(ct, hl, pla)
    for r in hl["ma_tran"]:
        r["so_sanh"] = ss.get(r["khoa"])
    cov = coverage_l3(hl, tat_ca, ctx, ss, caps)
    chua_dong = [d for d in tat_ca if not d.get("bo") and d.get("loai") != "KHAC" and d.get("trang_thai_dong") not in ("CHECKED", "LIMITED")]
    ghi_chu = chu_thich_phat_hien(hl, ss, caps, chua_dong)
    # tài liệu hiệu lực trả về = đã đọc (có dòng hàng, ghép) + chưa đọc (giữ trạng thái/lý do) theo đúng thứ tự bộ
    theo_id = {d["tep_id"]: d for d in hl["tai_lieu"]}
    tai_lieu = [theo_id.get(d["tep_id"], d) for d in tat_ca]
    dung_ma = all(c["trang_thai"] in DAT_DU for c in cov.values())
    kq = {"phien_ban": NR.L3_PHIEN_BAN, "engine": NR.ENGINE_L3, "engine_sha256": NR.ENGINE_L3_SHA, "che_do": CHE_DO, "run_id": vao.get("run_id"),
          "basis_sha256": vao["basis_sha256"], "revision": (basis.get("revision") or {}).get("revision", 0), "so_hd": hd["so_hd"], "ngay_nt": ctx["ngay_nt"],
          "tai_lieu": tai_lieu, "hang_muc": hl["hang_muc"], "ma_tran": hl["ma_tran"], "phat_hien": hl["phat_hien"], "dem": hl["dem"],
          "so_phat_hien": len(hl["phat_hien"]), "coverage": cov, "so_sanh": ss, "c06_cap": caps, "chu_thich_phat_hien": ghi_chu,
          "provenance": {"nguon_hang_muc": ctx.get("nguon"), "ly_do_can_cu": ctx.get("ly_do"), "l2": ctx.get("l2"), "l2_cu": ctx.get("l2_cu"),
                         "ngay_ky_hd": hd["ngay_ky_hd"], "vat": hd["vat"], "metadata_sua": sua, "ghep_tay": nhat_ky,
                         "lich_su_revision": basis.get("revision_lich_su") or [],
                         "thich_nghi_cot": [{"tep_id": d["tep_id"], **x} for d in tat_ca for x in d.get("thich_nghi_cot") or []],
                         # L3 A2: tóm tắt lớp nguồn TRƯỚC alias theo tệp (bản đầy đủ ở `tai_lieu[].nguon_truoc_alias`) — KHÔNG phải provenance.auto
                         "truoc_alias": [{k: d["nguon_truoc_alias"].get(k) for k in ("tep_id", "raw_sha256", "trang_thai", "ly_do", "giong_hieu_luc", "so_dong")}
                                         for d in tat_ca if d.get("nguon_truoc_alias")],
                         "auto": {"tai_lieu": [{"tep_id": d["tep_id"], "dong": [{"row_id": ln.get("row_id"), "khoa": ln.get("khoa"), "khop": ln.get("khop")}
                                                                                for ln in d["dong"]]} for d in auto["tai_lieu"]],
                                  "ma_tran": auto["ma_tran"], "phat_hien": auto["phat_hien"], "dem": auto["dem"]},
                         "provider": NR.L3_PROVIDER, "ai": None,
                         "ghi_chu_tien": "Ảnh hưởng là ước tính float/tolerance của thuật toán nguồn — không phải NT/thuế/công nợ/thanh toán được chấp nhận"},
          "trang_thai": "SUCCEEDED" if dung_ma else "PARTIAL", "bao_cao": []}
    kq = RC._json(kq)
    write_immutable(thu_muc / TEN_BAO_CAO, bao_cao_xlsx(kq))
    kq["bao_cao"] = [{"loai": "REPORT_L3", "tep": TEN_BAO_CAO}]
    return kq
