"""Bộ trộn dữ liệu vào mẫu Word — Mục 7.

CÚ PHÁP GIỮ NGUYÊN CỦA BASE. Công ty có 18 file mẫu .docx đang dùng; đặc tả
chốt "giữ nguyên cú pháp để tái sử dụng toàn bộ, không sửa một chữ".

--------------------------------------------------------------------------
VÌ SAO KHÔNG DÙNG docxtpl (quyết định Q6)

Mục 7 ghi công nghệ là docxtpl. Nhưng docxtpl là Jinja: cú pháp của nó là
{{ ten_truong }}, còn 18 mẫu của công ty viết ${ten_truong}. Dùng docxtpl
nghĩa là phải sửa lại toàn bộ 18 mẫu — đúng điều đặc tả cấm ở ngay đoạn trên.

Nên giữ bộ trộn tự viết, đã kiểm chứng trên mẫu thật ở Giai đoạn 0.

--------------------------------------------------------------------------
MỘT ĐIỂM WORD LÀM KHÓ: MÃ BỊ CẮT LÀM ĐÔI

docs/02 lỗi số 2: khi soạn thảo, Word ngầm chia ${du_an} thành nhiều "run"
nhỏ — ví dụ "${du" + "_an}" — dù nhìn trên màn hình vẫn liền một mạch.

Bản kiểm chứng ở Giai đoạn 0 xử lý bằng cách dồn cả đoạn văn vào run đầu tiên.
Cách đó làm MẤT ĐỊNH DẠNG: một dòng như "Kính gửi: <b>${creator_name}</b>, ..."
sẽ in đậm toàn bộ. Trái với nguyên tắc 2 của docs/02 — "định dạng thuộc về mã".

Bản này thay đúng chỗ, giữ nguyên định dạng của run chứa đầu mã trộn.
"""

from __future__ import annotations

import copy
import io
import re
from dataclasses import dataclass, field

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm

from .loc import GiaTriKhongHopLe, LocKhongHieu, ap_loc

MA_TRON = re.compile(r"\$\{([^}]*)\}")

RE_O_BANG = re.compile(r"^([a-z0-9_]+)-(\d+)-(\d+)$")
RE_COT_LAP = re.compile(r"^column\.([a-z0-9_]+)\.(\d+)$")
RE_CHU_KY = re.compile(r"^signer\.(title|name|action|datetime)$")
RE_IF = re.compile(r"\$\{if:([^}]*)\}")
RE_ENDIF = re.compile(r"\$\{endif\}")


@dataclass
class KetQuaTron:
    """Kết quả một lần trộn, kèm những gì không giải được để còn báo cho người dùng."""

    du_lieu: bytes
    ma_khong_giai_duoc: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)


# ====================================================== thay thế theo run

def _thay_trong_doan(doan, giai) -> None:
    """Thay mọi mã trộn trong một đoạn văn, giữ nguyên định dạng từng run.

    `giai(ma)` trả về chuỗi thay thế, hoặc None nếu không giải được (khi đó mã
    được giữ nguyên để người soạn mẫu nhìn thấy mà sửa).
    """
    runs = doan.runs
    if not runs:
        return

    toan_van = "".join(r.text for r in runs)
    if "${" not in toan_van:
        return

    # Bản đồ: vị trí ký tự trong toàn văn -> (chỉ số run, vị trí trong run)
    viTri = []
    for i, r in enumerate(runs):
        for j in range(len(r.text)):
            viTri.append((i, j))

    # Xử lý từ cuối lên đầu để các vị trí phía trước không bị xê dịch
    for m in reversed(list(MA_TRON.finditer(toan_van))):
        thay = giai(m.group(1))
        if thay is None:
            continue

        dau_run, dau_offset = viTri[m.start()]
        cuoi_run, cuoi_offset = viTri[m.end() - 1]

        if dau_run == cuoi_run:
            t = runs[dau_run].text
            runs[dau_run].text = t[:dau_offset] + thay + t[cuoi_offset + 1 :]
        else:
            # Đầu mã nằm ở run này: giữ định dạng của nó cho cả chuỗi thay thế
            runs[dau_run].text = runs[dau_run].text[:dau_offset] + thay
            for k in range(dau_run + 1, cuoi_run):
                runs[k].text = ""
            runs[cuoi_run].text = runs[cuoi_run].text[cuoi_offset + 1 :]


def _moi_doan(doc):
    """Mọi đoạn văn trong tài liệu: thân bài, bảng (lồng nhau), đầu và chân trang."""
    yield from doc.paragraphs
    for t in doc.tables:
        yield from _doan_trong_bang(t)
    for s in doc.sections:
        for phan in (s.header, s.footer, s.first_page_header, s.first_page_footer):
            if phan is None:
                continue
            yield from phan.paragraphs
            for t in phan.tables:
                yield from _doan_trong_bang(t)


def _doan_trong_bang(bang):
    for row in bang.rows:
        for cell in row.cells:
            yield from cell.paragraphs
            for t in cell.tables:
                yield from _doan_trong_bang(t)


def _van_ban_doan(doan) -> str:
    return "".join(r.text for r in doan.runs) or doan.text


# ================================================== khối điều kiện ${if:}

def _lay_so_de_so_sanh(v):
    from decimal import Decimal, InvalidOperation

    if isinstance(v, dict):
        v = v.get("amount")
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return None


def danh_gia_dieu_kien(bieu_thuc: str, ngu_canh: dict) -> bool:
    """Lượng giá biểu thức của ${if:...}.

    Cú pháp cố ý giữ nhỏ và dễ đoán — mẫu Word do người nghiệp vụ soạn, không
    phải nơi để có một ngôn ngữ lập trình:

        ${if:tong_thanh_tien>=50000000}
        ${if:hinh_thuc_thanh_toan==Chuyển khoản}
        ${if:so_hop_dong}            (có giá trị, khác rỗng)
    """
    bt = bieu_thuc.strip()
    if not bt:
        return False

    m = re.match(r"^([a-z0-9_.]+)\s*(>=|<=|==|!=|>|<)\s*(.*)$", bt, re.IGNORECASE)
    if not m:
        gt = ngu_canh.get(bt)
        if isinstance(gt, dict):
            gt = gt.get("amount")
        return bool(gt not in (None, "", [], {}))

    ten, toan_tu, ve_phai = m.group(1), m.group(2), m.group(3).strip()
    trai = ngu_canh.get(ten)

    so_trai = _lay_so_de_so_sanh(trai)
    so_phai = _lay_so_de_so_sanh(ve_phai)

    if so_trai is not None and so_phai is not None:
        return {
            ">=": so_trai >= so_phai,
            "<=": so_trai <= so_phai,
            ">": so_trai > so_phai,
            "<": so_trai < so_phai,
            "==": so_trai == so_phai,
            "!=": so_trai != so_phai,
        }[toan_tu]

    # So sánh chuỗi, bỏ qua hoa thường và khoảng trắng hai đầu
    if isinstance(trai, dict):
        trai = trai.get("amount")
    s_trai = str(trai if trai is not None else "").strip().lower()
    s_phai = ve_phai.strip().strip('"\'').lower()
    if toan_tu == "==":
        return s_trai == s_phai
    if toan_tu == "!=":
        return s_trai != s_phai
    return False


def _xu_ly_khoi_dieu_kien(doc, ngu_canh: dict, canh_bao: list[str]) -> None:
    """Xoá hoặc giữ các khối ${if:...} ... ${endif}.

    Khối được xét trong từng vùng chứa (thân bài, từng ô bảng) vì một khối
    không bao giờ bắc cầu giữa hai ô.
    """
    vung = [doc]
    for t in doc.tables:
        vung.extend(_o_trong_bang(t))

    for v in vung:
        _xu_ly_khoi_trong_vung(v, ngu_canh, canh_bao)


def _o_trong_bang(bang):
    for row in bang.rows:
        for cell in row.cells:
            yield cell
            for t in cell.tables:
                yield from _o_trong_bang(t)


def _xu_ly_khoi_trong_vung(vung, ngu_canh: dict, canh_bao: list[str]) -> None:
    doan = list(vung.paragraphs)
    i = 0
    while i < len(doan):
        van = _van_ban_doan(doan[i])
        mo = RE_IF.search(van)
        if not mo:
            i += 1
            continue

        # Tìm ${endif} tương ứng
        j = i
        sau = None
        while j < len(doan):
            if RE_ENDIF.search(_van_ban_doan(doan[j])):
                sau = j
                break
            j += 1

        if sau is None:
            canh_bao.append(
                f'Mẫu có ${{if:{mo.group(1)}}} nhưng thiếu ${{endif}} — khối này bị bỏ qua.'
            )
            _go_danh_dau(doan[i], RE_IF)
            i += 1
            continue

        giu = danh_gia_dieu_kien(mo.group(1), ngu_canh)

        if giu:
            # Giữ nội dung, chỉ xoá hai dòng đánh dấu
            _go_danh_dau(doan[i], RE_IF)
            _go_danh_dau(doan[sau], RE_ENDIF)
            i = sau + 1
        else:
            for k in range(i, sau + 1):
                p = doan[k]._p
                p.getparent().remove(p)
            doan = list(vung.paragraphs)
            i = 0  # chỉ số đã đổi, quét lại từ đầu vùng này


def _go_danh_dau(doan, mau) -> None:
    """Xoá riêng chuỗi đánh dấu; nếu đoạn trở thành rỗng thì bỏ luôn cả đoạn."""
    for r in doan.runs:
        r.text = mau.sub("", r.text)
    if not _van_ban_doan(doan).strip():
        p = doan._p
        p.getparent().remove(p)


# ================================================ bảng tự nhân dòng

def _nhan_dong_bang(doc, bang_du_lieu: dict, giai_o, canh_bao: list[str]) -> None:
    """Nhân dòng mẫu chứa ${column.<bảng>.<cột>} ra bằng số dòng dữ liệu thật."""
    for bang in list(doc.tables):
        _nhan_dong_mot_bang(bang, bang_du_lieu, giai_o, canh_bao)


def _nhan_dong_mot_bang(bang, bang_du_lieu, giai_o, canh_bao) -> None:
    dong_mau = None
    ten_bang = None

    for row in bang.rows:
        van = " ".join(_van_ban_doan(p) for c in row.cells for p in c.paragraphs)
        # RE_COT_LAP neo hai đầu nên không dùng để quét giữa câu được
        m = re.search(r"column\.([a-z0-9_]+)\.\d+", van)
        if m:
            if dong_mau is not None:
                canh_bao.append(
                    f'Bảng "{m.group(1)}" có nhiều hơn một dòng mẫu — dữ liệu sẽ bị nhân đôi. '
                    f"Chỉ để lại đúng một dòng chứa ${{column....}}."
                )
                return
            dong_mau = row
            ten_bang = m.group(1)

    if dong_mau is None:
        return

    du_lieu = bang_du_lieu.get(ten_bang) or []
    tr_mau = dong_mau._tr
    mau_sao = copy.deepcopy(tr_mau)
    moc = tr_mau

    for chi_so, dong in enumerate(du_lieu):
        moi = copy.deepcopy(mau_sao)
        moc.addnext(moi)
        moc = moi
        row_moi = docx.table._Row(moi, bang)
        for cell in row_moi.cells:
            for p in cell.paragraphs:
                _thay_trong_doan(p, lambda ma, d=dong, i=chi_so: giai_o(ma, d, i))

    tr_mau.getparent().remove(tr_mau)

    # Bảng lồng trong ô
    for row in bang.rows:
        for cell in row.cells:
            for t in cell.tables:
                _nhan_dong_mot_bang(t, bang_du_lieu, giai_o, canh_bao)


# ============================================== khối chữ ký ${signer.*}

def _nhan_o_chu_ky(doc, nguoi_ky: list[dict], canh_bao: list[str]) -> None:
    """Nhân ô mẫu chứa ${signer.*} ra bằng đúng số người đã duyệt.

    docs/02 mục 4.2: thay cho việc phải có 6 file mẫu cho 2/3/4/5 người ký.
    Chỉ nhân CỘT nào có chứa ${signer.*}, các ô cố định giữ nguyên.
    """
    for bang in list(doc.tables):
        _nhan_o_chu_ky_mot_bang(bang, nguoi_ky, canh_bao)


def _tcPr(tc):
    pr = tc.find(qn("w:tcPr"))
    if pr is None:
        pr = OxmlElement("w:tcPr")
        tc.insert(0, pr)
    return pr


def _dat_be_rong(tc, twips: int) -> None:
    pr = _tcPr(tc)
    w = pr.find(qn("w:tcW"))
    if w is None:
        w = OxmlElement("w:tcW")
        pr.append(w)
    w.set(qn("w:w"), str(twips))
    w.set(qn("w:type"), "dxa")


def _gop_cot(tc, them: int) -> None:
    """Cho ô ở các hàng khác trải ngang đúng số cột vừa thêm, để bảng không lệch."""
    pr = _tcPr(tc)
    span = pr.find(qn("w:gridSpan"))
    if span is None:
        span = OxmlElement("w:gridSpan")
        span.set(qn("w:val"), "1")
        pr.append(span)
    span.set(qn("w:val"), str(int(span.get(qn("w:val")) or 1) + them))


def _chia_cot_luoi(bang, cot: int, so_phan: int) -> list[int]:
    """Tách một cột của <w:tblGrid> thành nhiều cột, GIỮ NGUYÊN bề rộng bảng.

    Thêm ô mà quên thêm <w:gridCol> thì Word còn đoán được, LibreOffice thì dồn
    các ô thừa về bề rộng mặc định — khối chữ ký in ra méo, mà bản .docx mở trên
    máy người soạn vẫn đẹp. Đúng loại lệch bố cục Mục 7 cảnh báo.
    """
    luoi = bang._tbl.find(qn("w:tblGrid"))
    if luoi is None:
        return []
    cot_luoi = luoi.findall(qn("w:gridCol"))
    if cot >= len(cot_luoi):
        return []

    goc = cot_luoi[cot]
    try:
        rong = int(goc.get(qn("w:w")))
    except (TypeError, ValueError):
        rong = 0

    phan = [rong // so_phan] * so_phan
    phan[-1] += rong - sum(phan)

    goc.set(qn("w:w"), str(phan[0]))
    moc = goc
    for r in phan[1:]:
        moi = copy.deepcopy(goc)
        moi.set(qn("w:w"), str(r))
        moc.addnext(moi)
        moc = moi
    return phan


def _nhan_o_chu_ky_mot_bang(bang, nguoi_ky, canh_bao) -> None:
    for row in bang.rows:
        # Đọc ô thô thay vì row.cells: row.cells trải ô đã gộp ra thành nhiều ô,
        # nên chỉ số của nó không khớp với chỉ số cột trong <w:tblGrid>.
        o_tho = row._tr.findall(qn("w:tc"))

        cot_mau = None
        for idx, tc in enumerate(o_tho):
            cell = docx.table._Cell(tc, row)
            van = " ".join(_van_ban_doan(p) for p in cell.paragraphs)
            if "${signer." in van:
                cot_mau = idx
                break

        if cot_mau is None:
            for cell in row.cells:
                for t in cell.tables:
                    _nhan_o_chu_ky_mot_bang(t, nguoi_ky, canh_bao)
            continue

        tc_mau = o_tho[cot_mau]

        if not nguoi_ky:
            canh_bao.append("Mẫu có ô chữ ký lặp nhưng chưa có ai duyệt — ô bị bỏ trống.")
            # Giữ lại ô, chỉ xoá mã: bỏ hẳn ô làm hàng thiếu cột so với lưới
            for p in docx.table._Cell(tc_mau, row).paragraphs:
                _thay_trong_doan(p, lambda ma: "" if RE_CHU_KY.match(ma.strip()) else None)
            return

        mau_sao = copy.deepcopy(tc_mau)
        phan = _chia_cot_luoi(bang, cot_mau, len(nguoi_ky))

        moc = tc_mau
        for i, ky in enumerate(nguoi_ky):
            moi = copy.deepcopy(mau_sao)
            moc.addnext(moi)
            moc = moi
            if i < len(phan):
                _dat_be_rong(moi, phan[i])
            o_moi = docx.table._Cell(moi, row)
            for p in o_moi.paragraphs:
                _thay_trong_doan(p, lambda ma, k=ky: _giai_chu_ky(ma, k))

        tc_mau.getparent().remove(tc_mau)

        # Các hàng còn lại của bảng phải trải ngang phần cột vừa thêm
        for r_khac in bang.rows:
            if r_khac._tr is row._tr:
                continue
            tcs = r_khac._tr.findall(qn("w:tc"))
            if cot_mau < len(tcs):
                _gop_cot(tcs[cot_mau], len(nguoi_ky) - 1)

        return  # mỗi bảng chỉ có một hàng chữ ký


def _giai_chu_ky(ma: str, ky: dict):
    m = RE_CHU_KY.match(ma.strip())
    if not m:
        return None
    return str(ky.get(m.group(1), "") or "")


# ====================================================== trộn toàn bộ

def tron(
    mau_bytes: bytes,
    ngu_canh: dict,
    bang: dict | None = None,
    nguoi_ky: list[dict] | None = None,
    qr_png: bytes | None = None,
) -> KetQuaTron:
    """Trộn dữ liệu vào mẫu .docx và trả về tệp kết quả.

    Thứ tự xử lý quan trọng:
      1. khối điều kiện  — có thể xoá hẳn cả đoạn, làm sớm để khỏi trộn thừa
      2. nhân dòng bảng  — sinh thêm dòng mới cần được trộn
      3. nhân ô chữ ký   — sinh thêm ô mới cần được trộn
      4. thay mã còn lại — kể cả trong những dòng và ô vừa sinh ra
      5. chèn ảnh QR     — làm cuối vì nó thay một đoạn văn bằng ảnh
    """
    bang = bang or {}
    nguoi_ky = nguoi_ky or []
    canh_bao: list[str] = []
    khong_giai_duoc: set[str] = set()

    doc = docx.Document(io.BytesIO(mau_bytes))

    _xu_ly_khoi_dieu_kien(doc, ngu_canh, canh_bao)
    _nhan_dong_bang(doc, bang, _giai_o_bang, canh_bao)
    _nhan_o_chu_ky(doc, nguoi_ky, canh_bao)

    def giai(ma: str):
        kq = _giai_ma(ma, ngu_canh, bang)
        if kq is None:
            if ma.strip() != "qrcode":
                khong_giai_duoc.add(ma)
            return None
        return kq

    for doan in _moi_doan(doc):
        _thay_trong_doan(doan, giai)

    if qr_png:
        _chen_qr(doc, qr_png)

    ra = io.BytesIO()
    doc.save(ra)
    return KetQuaTron(
        du_lieu=ra.getvalue(),
        ma_khong_giai_duoc=sorted(khong_giai_duoc),
        canh_bao=canh_bao,
    )


def _giai_o_bang(ma: str, dong: list | dict, chi_so: int):
    """Giải mã trong một dòng bảng đã nhân bản."""
    ma = ma.strip()
    if ma == "stt":
        return str(chi_so + 1)
    m = RE_COT_LAP.match(ma)
    if not m:
        return None
    cot = int(m.group(2)) - 1
    if isinstance(dong, dict):
        gia_tri = list(dong.values())
        return str(gia_tri[cot]) if 0 <= cot < len(gia_tri) else ""
    return str(dong[cot]) if 0 <= cot < len(dong) else ""


def _giai_ma(ma: str, ngu_canh: dict, bang: dict):
    """Giải một mã trộn thành chuỗi. Trả None nếu không nhận ra."""
    ma = ma.strip()
    if not ma:
        return None

    # Bộ lọc: ${ten|loc}
    if "|" in ma:
        goc, ten_loc = [x.strip() for x in ma.split("|", 1)]
        gia_tri = _tra_gia_tri(goc, ngu_canh, bang)
        if gia_tri is None:
            return None
        try:
            return ap_loc(ten_loc, gia_tri, ngu_canh)
        except LocKhongHieu as e:
            return f"[{e}]"
        except (GiaTriKhongHopLe, ValueError) as e:
            return f"[{goc}: {e}]"

    gia_tri = _tra_gia_tri(ma, ngu_canh, bang)
    if gia_tri is None:
        return None
    return _thanh_chuoi(gia_tri)


def _tra_gia_tri(ten: str, ngu_canh: dict, bang: dict):
    """Tra giá trị theo tên, kể cả ô bảng ${<bảng>-<dòng>-<cột>}."""
    if ten in ngu_canh:
        return ngu_canh[ten]

    m = RE_O_BANG.match(ten)
    if m:
        du_lieu = bang.get(m.group(1))
        if du_lieu is None:
            return None
        dong = int(m.group(2)) - 1
        cot = int(m.group(3)) - 1
        if not (0 <= dong < len(du_lieu)):
            return ""
        o = du_lieu[dong]
        if isinstance(o, dict):
            o = list(o.values())
        return o[cot] if 0 <= cot < len(o) else ""

    return None


def _thanh_chuoi(gia_tri) -> str:
    if gia_tri is None:
        return ""
    if isinstance(gia_tri, bool):
        return "Có" if gia_tri else "Không"
    if isinstance(gia_tri, dict):
        # Giá trị tiền chưa qua bộ lọc: in số kèm mã tiền tệ cho khỏi mơ hồ
        if "amount" in gia_tri:
            ma = gia_tri.get("currency")
            return f"{gia_tri['amount']} {ma}".strip() if ma else str(gia_tri["amount"])
        if "date" in gia_tri:
            return str(gia_tri["date"])
        return ""
    if isinstance(gia_tri, list):
        return ", ".join(_thanh_chuoi(x) for x in gia_tri)
    return str(gia_tri)


def _chen_qr(doc, qr_png: bytes) -> None:
    """Thay đoạn chứa ${qrcode} bằng ảnh QR tra cứu bản gốc."""
    for doan in _moi_doan(doc):
        van = _van_ban_doan(doan)
        if "${qrcode}" not in van:
            continue
        for r in doan.runs:
            r.text = r.text.replace("${qrcode}", "")
        run = doan.runs[0] if doan.runs else doan.add_run()
        run.add_picture(io.BytesIO(qr_png), width=Mm(25))
