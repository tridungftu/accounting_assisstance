"""XS-3A: danh bạ engine thuần bộ nhớ, không tự đăng ký engine thật.

Không đọc/ghi bảng của module hay TRANG-THAI.md. Lead dùng ``liet_ke`` để
ghi danh bạ vào tài liệu. Phiên bản là định danh, không tự chọn 'mới nhất'.
"""

from __future__ import annotations

from kho_tri_thuc.ha_tang.engine import Engine, KhaiBaoEngine


class DanhBaEngine:
    def __init__(self) -> None:
        self._engines: dict[tuple[str, str], Engine] = {}

    def dang_ky(self, engine: Engine, *, phien_ban_moi: bool = False) -> None:
        """Đăng ký lần đầu; thêm version cùng mã phải đặt phien_ban_moi=True.

        Luôn từ chối cặp trùng, kể cả cùng instance và có cờ phiên bản mới.
        Phiên bản cũ được giữ để caller tra đúng version đã ghim.
        """
        if not isinstance(engine, Engine) or not isinstance(engine.khai_bao, KhaiBaoEngine):
            raise ValueError("Chỉ đăng ký engine có hợp đồng hợp lệ.")
        if type(phien_ban_moi) is not bool:
            raise ValueError("Cờ phiên bản mới phải là bool tường minh.")
        key = (engine.ma, engine.phien_ban)
        if key in self._engines:
            raise ValueError("Mã và phiên bản engine đã được đăng ký.")
        if not phien_ban_moi and any(ma == engine.ma for ma, _ in self._engines):
            raise ValueError("Mã engine đã có; phải đăng ký phiên bản mới tường minh.")
        self._engines[key] = engine

    def tra_cuu(self, ma: str, phien_ban: str) -> Engine:
        """Trả đúng engine/version; thiếu thì KeyError, không fallback version."""
        engine = self._engines[(ma, phien_ban)]
        if (engine.ma, engine.phien_ban) != (ma, phien_ban):
            raise ValueError("Định danh engine đã thay đổi sau khi đăng ký.")
        return engine

    def liet_ke(self) -> tuple[KhaiBaoEngine, ...]:
        """Snapshot metadata bất biến, sắp theo mã/version (thứ tự chuỗi)."""
        return tuple(self.tra_cuu(*key).khai_bao for key in sorted(self._engines))
