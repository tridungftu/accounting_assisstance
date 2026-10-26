"""Adapter M9 cho cổng OCR chung; giữ API và mã lỗi M9_OCR_*.

thu_muc_du_lieu phải là thư mục dữ liệu Review để mặc định chọn sổ chung
ocr_abbyy/so_trang.json. Có thể truyền tep_so_trang tường minh khi dữ liệu
hai phần mềm ở hai nơi; thu_muc_dem luôn là đệm riêng của phần mềm này.
"""

from pathlib import Path

from kho_tri_thuc.ha_tang.cong_ocr import CongOCR
from kho_tri_thuc.ha_tang.primitives import DataError


def _loi_m9(loi: DataError) -> DataError:
    return DataError("M9_" + loi.code if loi.code.startswith("OCR_") else loi.code,
                     str(loi), loi.locator)


class HotFolderM9(CongOCR):
    def __init__(self, thu_muc_goc: Path, *, thu_muc_du_lieu: Path,
                 tep_so_trang: Path | None = None, thu_muc_dem: Path | None = None,
                 cho_nhan=300, cho_toi_da=1800, nghi=1.0, on_dinh=2.0):
        try:
            du_lieu = Path(thu_muc_du_lieu)
            super().__init__(
                thu_muc_goc,
                tep_so_trang=tep_so_trang if tep_so_trang is not None else du_lieu / "ocr_abbyy" / "so_trang.json",
                thu_muc_dem=thu_muc_dem if thu_muc_dem is not None else du_lieu / "ocr_hot_folder_m9",
                cho_nhan=cho_nhan, cho_toi_da=cho_toi_da, nghi=nghi, on_dinh=on_dinh,
            )
        except DataError as exc:
            raise _loi_m9(exc) from None
        except (OSError, ValueError, TypeError):
            raise DataError("M9_OCR_LOI_ABBYY", "Cấu hình nhận dạng chưa hợp lệ.") from None

    def ocr(self, raw: bytes, duoi: str, *, huy=None) -> bytes:
        try:
            return super().ocr(raw, duoi, huy=huy)
        except DataError as exc:
            raise _loi_m9(exc) from None
