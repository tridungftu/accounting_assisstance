"""G2-24: staging DEMO bằng bytes đã kiểm; chưa áp migration/kích hoạt.

Không xóa tệp khi lỗi: thư mục chưa hoàn tất được báo KHONG_DAT, không phải
gói có thể kích hoạt. G2-25 phải kiểm lại bytes/hash trước khi dùng báo cáo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import uuid

from .goi import (GioiHan, LoiGoi, _kiem_handle, doc_goi,
                  kiem_duong_dan)


THU_MUC_DU_AN = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class BaoCaoKiem:
    ket_luan: str
    ly_do: tuple[str, ...]
    thu_muc_staging: Path | None = None
    sha256_tung_tep: dict = field(default_factory=dict)
    sha256_goi: str | None = None


def dua_vao_staging(thu_muc_goi, *, ma_lat, phien_ban_core,
                    phien_ban_sdk_python='1.0.0', phien_ban_sdk_js='1.0.0',
                    module_da_co=None, gioi_han: GioiHan | None = None):
    """Chỉ ghi dưới <repo>/var/core-demo/<ma_lat>/goi/<mã>-<UUID>.

    Không nhận đường dẫn đích tùy ý; không ghi đè gói cũ. Báo cáo chỉ chứng
    minh phần kiểm tĩnh và staging của G2-24, không xác nhận đã được cài.
    """
    staged = None
    try:
        if not isinstance(ma_lat, str) or not re.fullmatch(r'g2_[a-z0-9_]+|g2-[a-z0-9-]+', ma_lat):
            raise LoiGoi('Mã lát staging DEMO không hợp lệ.')
        root = kiem_duong_dan(THU_MUC_DU_AN / 'var' / 'core-demo' / ma_lat / 'goi')
        package = doc_goi(thu_muc_goi, phien_ban_core=phien_ban_core,
                         phien_ban_sdk_python=phien_ban_sdk_python,
                         phien_ban_sdk_js=phien_ban_sdk_js,
                         module_da_co=module_da_co, gioi_han=gioi_han)
        root.mkdir(parents=True, exist_ok=True)
        kiem_duong_dan(root)
        staged = root / (package.manifest['ma'] + '-' + uuid.uuid4().hex)
        staged.mkdir()
        for name in package.cac_thu_muc:
            folder = kiem_duong_dan(staged / name)
            folder.mkdir(parents=True, exist_ok=True)
            kiem_duong_dan(folder)
        for name, raw in package.cac_tep.items():
            path = kiem_duong_dan(staged / name)
            path.parent.mkdir(parents=True, exist_ok=True)
            kiem_duong_dan(path)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            with os.fdopen(fd, 'wb') as stream:
                _kiem_handle(stream.fileno(), path)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        # Đọc lại chính đích, kiểm schema và hash, không tin copy thành công là đủ.
        copied = doc_goi(staged, phien_ban_core=phien_ban_core,
                         phien_ban_sdk_python=phien_ban_sdk_python,
                         phien_ban_sdk_js=phien_ban_sdk_js,
                         module_da_co=module_da_co, gioi_han=gioi_han)
        if copied.sha256_goi != package.sha256_goi:
            raise LoiGoi('SHA256 staging khác snapshot gói đã kiểm.')
        return BaoCaoKiem('DAT', ('Kiểm tĩnh và staging DEMO đạt; chưa cài hoặc kích hoạt.',),
                          staged, dict(copied.sha256_tung_tep), copied.sha256_goi)
    except LoiGoi as exc:
        return BaoCaoKiem('KHONG_DAT', (str(exc),), staged)
    except OSError:
        return BaoCaoKiem('KHONG_DAT', ('Không ghi/đọc được staging DEMO an toàn.',), staged)
