"""Xuất PDF bằng LibreOffice headless, và kiểm phông chữ — Mục 7.

LỖI THỰC TẾ SỐ 1 CỦA ĐẶC TẢ:

    "LibreOffice trên Linux không có Times New Roman -> bố cục lệch. Cài
     Liberation Serif (tương thích số đo) hoặc chép phông Microsoft lên máy chủ.
     Kiểm thử bằng chính mẫu của công ty ngay từ ngày đầu."

Lệch bố cục là loại lỗi tệ: tờ trình vẫn in ra, vẫn đọc được, chỉ là xuống dòng
sai chỗ và tràn sang trang thứ hai. Không ai báo lỗi, và người ta chỉ phát hiện
khi cầm bản in trên tay.

Nên ở đây có hai việc:
  · chạy LibreOffice đúng cách, mỗi lần một hồ sơ riêng (xem chú thích dưới)
  · soi trước mẫu xem nó cần phông gì, đối chiếu với phông máy chủ đang có
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# Phông Microsoft và phông thay thế tương thích SỐ ĐO — cùng chiều rộng ký tự
# nên xuống dòng và ngắt trang y hệt nhau.
THAY_THE_TUONG_THICH = {
    "times new roman": "Liberation Serif",
    "arial": "Liberation Sans",
    "courier new": "Liberation Mono",
    "cambria": "Caladea",
    "calibri": "Carlito",
}


# Windows đặt tên tệp phông viết tắt, không phải tên họ phông. Không có bảng
# này thì máy lập trình Windows báo thiếu Times New Roman dù rõ ràng có.
TEN_TEP_WINDOWS = {
    "times": ("times new roman",),
    "arial": ("arial",),
    "cour": ("courier new",),
    "calibri": ("calibri",),
    "cambria": ("cambria",),
    "tahoma": ("tahoma",),
    "verdana": ("verdana",),
    "segoeui": ("segoe ui",),
}


class KhongCoLibreOffice(RuntimeError):
    pass


class XuatPdfThatBai(RuntimeError):
    pass


@dataclass
class KetQuaKiemPhong:
    phong_trong_mau: list[str] = field(default_factory=list)
    thieu: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.thieu


def tim_soffice() -> str | None:
    """Tìm LibreOffice. Trên máy chủ Linux là `soffice` trong PATH."""
    if os.environ.get("SOFFICE"):
        return os.environ["SOFFICE"]
    for ten in ("soffice", "libreoffice"):
        duong = shutil.which(ten)
        if duong:
            return duong
    for ung_vien in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/lib/libreoffice/program/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if Path(ung_vien).exists():
            return ung_vien
    return None


# CHỈ lấy phông thật sự chạm tới chữ in ra. Ba tầng lọc, mỗi tầng chặn một kiểu
# cảnh báo sai — mà cảnh báo sai ở đây hại ngang bỏ sót: nó dạy người vận hành
# bỏ qua mọi cảnh báo về phông, đúng loại họ cần đọc nhất.
#
#  1. Chỉ đọc phần có chữ: document, header, footer, footnotes, endnotes. Quét
#     cả styles.xml thì vớ phải hàng chục kiểu Word mang theo mà tài liệu không
#     dùng — bốn mẫu thật của công ty khai .VnTime/.VnArial trong hai kiểu chết
#     (Heading5, BodyText), thân tài liệu chỉ dùng ListParagraph và NormalWeb.
#  2. Chỉ đọc thuộc tính bên trong <w:rFonts>. Thẻ <w:lang> cũng có eastAsia,
#     nhưng giá trị của nó là mã NGÔN NGỮ ("en-US", "ja-JP").
#  3. Chỉ lấy w:ascii và w:hAnsi — phông chữ Latinh, tức phông quyết định bề
#     rộng dòng. w:cs (chữ phức hợp) và w:eastAsia (SimSun...) không chạm tới
#     một tờ trình tiếng Việt.
RE_PHAN_CO_CHU = re.compile(
    r"^word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", re.IGNORECASE
)
RE_RFONTS = re.compile(r"<w:rFonts\b[^>]*>", re.IGNORECASE)
RE_THUOC_TINH_PHONG = re.compile(r'w:(?:ascii|hAnsi)="([^"]*)"')
RE_THAM_CHIEU_THEME = re.compile(r'w:(?:ascii|hAnsi)Theme="(major|minor)')
RE_KIEU_DUNG = re.compile(r'w:(?:p|r|tbl)Style w:val="([^"]+)"')
RE_MOT_KIEU = re.compile(r"<w:style\b([^>]*)>(.*?)</w:style>", re.DOTALL)
RE_MA_KIEU = re.compile(r'w:styleId="([^"]+)"')
RE_KE_THUA = re.compile(r'<w:basedOn w:val="([^"]+)"')
RE_DOC_DEFAULTS = re.compile(r"<w:docDefaults>.*?</w:docDefaults>", re.DOTALL)
RE_THEME_LATIN = re.compile(
    r"<a:(major|minor)Font>\s*<a:latin[^>]*typeface=\"([^\"]*)\"", re.DOTALL
)


def _phong_trong_the(xml: str) -> tuple[set[str], set[str]]:
    """Bóc tên phông và tham chiếu theme từ các thẻ <w:rFonts> trong một đoạn XML."""
    ten: set[str] = set()
    theme: set[str] = set()
    for the in RE_RFONTS.findall(xml):
        for m in RE_THUOC_TINH_PHONG.finditer(the):
            gia_tri = m.group(1).strip()
            if gia_tri.startswith("+"):
                # "+mj-lt" / "+mn-lt" là tham chiếu theme, không phải tên phông
                theme.add("major" if "mj" in gia_tri else "minor")
            elif gia_tri:
                ten.add(gia_tri)
        for m in RE_THAM_CHIEU_THEME.finditer(the):
            theme.add(m.group(1))
    return ten, theme


def phong_trong_mau(docx_bytes: bytes) -> list[str]:
    """Liệt kê phông chữ Latinh mà chữ in ra của mẫu thật sự dùng."""
    ten: set[str] = set()
    can_theme: set[str] = set()

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        co = set(z.namelist())

        # 1. Phông đặt thẳng lên chữ, và tên các kiểu mà chữ đó gọi
        kieu_can: set[str] = set()
        for muc in co:
            if not RE_PHAN_CO_CHU.match(muc):
                continue
            xml = z.read(muc).decode("utf-8", "ignore")
            a, b = _phong_trong_the(xml)
            ten |= a
            can_theme |= b
            kieu_can |= set(RE_KIEU_DUNG.findall(xml))

        # 2. Kiểu dáng: bảng mặc định của tài liệu, các kiểu mặc định, các kiểu
        #    được gọi tên — và cả chuỗi kiểu cha của chúng
        if "word/styles.xml" in co:
            xml = z.read("word/styles.xml").decode("utf-8", "ignore")

            mac_dinh = RE_DOC_DEFAULTS.search(xml)
            if mac_dinh:
                a, b = _phong_trong_the(mac_dinh.group(0))
                ten |= a
                can_theme |= b

            kho: dict[str, tuple[set[str], set[str], str | None]] = {}
            for m in RE_MOT_KIEU.finditer(xml):
                dau, than = m.group(1), m.group(2)
                ma = RE_MA_KIEU.search(dau)
                if not ma:
                    continue
                a, b = _phong_trong_the(than)
                cha = RE_KE_THUA.search(than)
                kho[ma.group(1)] = (a, b, cha.group(1) if cha else None)
                if 'w:default="1"' in dau:
                    kieu_can.add(ma.group(1))

            da_xet: set[str] = set()
            cho_xet = list(kieu_can)
            while cho_xet:
                k = cho_xet.pop()
                if k in da_xet or k not in kho:
                    continue
                da_xet.add(k)
                a, b, cha = kho[k]
                ten |= a
                can_theme |= b
                if cha:
                    cho_xet.append(cha)

        # 3. Phông theme: chỉ tính khi có chữ thật sự trỏ tới nó
        if can_theme and "word/theme/theme1.xml" in co:
            xml = z.read("word/theme/theme1.xml").decode("utf-8", "ignore")
            for m in RE_THEME_LATIN.finditer(xml):
                if m.group(1) in can_theme:
                    ten.add(m.group(2).strip())

    return sorted(t for t in ten if t and not t.startswith("+"))


def phong_da_cai() -> set[str]:
    """Phông đang có trên máy. Dùng fc-list trên Linux, thư mục Fonts trên Windows."""
    co: set[str] = set()

    fc = shutil.which("fc-list")
    if fc:
        try:
            ra = subprocess.run(
                [fc, ":", "family"], capture_output=True, text=True, timeout=20
            )
            for dong in ra.stdout.splitlines():
                for phan in dong.split(","):
                    co.add(phan.strip().lower())
        except Exception:
            pass

    for thu_muc in (
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
    ):
        if not thu_muc.exists():
            continue
        try:
            for f in thu_muc.rglob("*"):
                if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
                    stem = f.stem.lower().replace("-", " ")
                    co.add(stem)
                    # Windows đặt tên tệp viết tắt: times.ttf, cour.ttf, ariali.ttf
                    co.update(TEN_TEP_WINDOWS.get(re.sub(r"(bd|bi|i|b|z)$", "", stem), ()))
        except Exception:
            pass

    return co


def kiem_phong(docx_bytes: bytes) -> KetQuaKiemPhong:
    """Soi mẫu xem nó cần phông gì, và máy chủ có đủ không.

    Chạy lúc quản trị viên tải mẫu lên, để lệch bố cục lộ ra ngay ngày đầu chứ
    không phải lúc ai đó cần in gấp.
    """
    can = phong_trong_mau(docx_bytes)
    co = phong_da_cai()

    thieu: list[str] = []
    canh_bao: list[str] = []

    for p in can:
        thuong = p.lower()
        if thuong in co:
            continue
        thay = THAY_THE_TUONG_THICH.get(thuong)
        if thay and thay.lower() in co:
            canh_bao.append(
                f'Máy chủ không có phông "{p}" nhưng có "{thay}" — tương thích số đo, '
                f"bố cục giữ nguyên. Vẫn nên in thử một bản đối chiếu."
            )
        else:
            thieu.append(p)

    if thieu:
        canh_bao.append(
            "Thiếu phông thì LibreOffice tự thay bằng phông khác chiều rộng, "
            "làm xuống dòng và ngắt trang lệch đi — tờ trình vẫn in ra nên rất khó phát hiện."
        )

    return KetQuaKiemPhong(phong_trong_mau=can, thieu=thieu, canh_bao=canh_bao)


def sang_pdf(docx_bytes: bytes, timeout_giay: int = 120) -> bytes:
    """Đổi .docx sang PDF.

    MỖI LẦN GỌI DÙNG MỘT HỒ SƠ NGƯỜI DÙNG RIÊNG (-env:UserInstallation).

    LibreOffice khoá hồ sơ người dùng của nó. Hai yêu cầu in cùng lúc dùng chung
    hồ sơ thì cái thứ hai treo cho tới khi hết thời gian chờ — và với hệ thống
    duyệt chi, "treo" nghĩa là ai đó đang đứng ở máy in chờ một tờ trình không
    bao giờ ra.
    """
    soffice = tim_soffice()
    if not soffice:
        raise KhongCoLibreOffice(
            "Không tìm thấy LibreOffice trên máy chủ. Cài LibreOffice rồi thử lại, "
            "hoặc đặt biến môi trường SOFFICE trỏ tới tệp soffice."
        )

    with tempfile.TemporaryDirectory(prefix="totrinh-") as tmp:
        thu_muc = Path(tmp)
        vao = thu_muc / "to-trinh.docx"
        vao.write_bytes(docx_bytes)

        ho_so = thu_muc / "profile"
        lenh = [
            soffice,
            f"-env:UserInstallation=file:///{ho_so.as_posix().lstrip('/')}",
            "--headless",
            "--norestore",
            "--invisible",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(thu_muc),
            str(vao),
        ]

        try:
            ra = subprocess.run(
                lenh, capture_output=True, text=True, timeout=timeout_giay
            )
        except subprocess.TimeoutExpired as e:
            raise XuatPdfThatBai(
                f"LibreOffice không trả lời trong {timeout_giay} giây."
            ) from e

        pdf = thu_muc / "to-trinh.pdf"
        if not pdf.exists():
            raise XuatPdfThatBai(
                "LibreOffice không tạo được PDF. "
                f"Mã thoát {ra.returncode}. {(ra.stderr or ra.stdout or '').strip()[:500]}"
            )
        return pdf.read_bytes()


def sinh_qr(noi_dung: str, kich_thuoc: int = 8) -> bytes:
    """Ảnh QR tra cứu bản gốc — ${qrcode} của Mục 7.

    Mức sửa lỗi H (khôi phục được 30%) vì tờ trình in ra sẽ bị đóng dấu, ghim,
    photocopy — mã phải còn quét được sau tất cả những thứ đó.
    """
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=kich_thuoc, border=2)
    qr.add_data(noi_dung)
    qr.make(fit=True)
    anh = qr.make_image(fill_color="black", back_color="white")

    ra = io.BytesIO()
    anh.save(ra, format="PNG")
    return ra.getvalue()


def ma_theo_doi() -> str:
    """Định danh một lần in, để truy ngược bản in nào sinh lúc nào."""
    return uuid.uuid4().hex[:12]
