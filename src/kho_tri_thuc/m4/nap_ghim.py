"""M4-01B (B4) — bộ nạp module CÓ GHIM cho lõi Review đã vendor: xác minh origin + SHA-256 TRƯỚC khi thực thi bất kỳ dòng mã nguồn nào.

- Finder đứng đầu `sys.meta_path`, chỉ nhận các tên gốc của lõi nguồn (trich_xuat, master_hd, csdl_hop_dong, may_chu, app_kiem_tra_ho_so, toan_ven).
  Tên thuộc các gói đó nhưng không có trong bảng PIN → ImportError (không rơi xuống sys.path/site-packages, không lấy package trùng tên).
- Loader đọc bytes từ đúng `goc/<rel>`, so SHA-256 với PIN, rồi compile + exec từ CHÍNH bytes đó; không dùng `__pycache__`/.pyc, không thêm sys.path.
- Module đã có sẵn trong `sys.modules` với các tên gốc đó mà không do loader này nạp → từ chối trước khi nạp gì (chống collision/sentinel).
- M4-01B2: cache được xác minh lại trước MỖI lần dùng (`hop_le`/`sai_cache`): đúng instance loader, đúng tên, dấu ghim = PIN, origin = goc/<rel>.
  Không phải sandbox chống mã Python độc hại đã chạy trong tiến trình.
Không đọc cấu hình/khóa/DB của app nguồn; dependency stdlib/openpyxl nạp như thường.
"""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

DAU_GHIM = "__m4_ghim__"


class LoiNapGhim(ImportError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class BoNapGhim(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, goc: Path, pin: dict, goi_goc):
        self.goc = Path(goc).resolve()
        self.pin = dict(pin)
        self.goi_goc = frozenset(goi_goc)

    def _vi_tri(self, fullname: str):
        """(rel, la_goi) cho module thuộc tập ghim; ("", True) cho namespace package; None nếu không thuộc các gói gốc."""
        parts = fullname.split(".")
        if parts[0] not in self.goi_goc:
            return None
        base = "/".join(parts)
        if f"{base}/__init__.py" in self.pin:
            return f"{base}/__init__.py", True
        if f"{base}.py" in self.pin:
            return f"{base}.py", False
        if any(k.startswith(base + "/") for k in self.pin):
            return "", True
        raise LoiNapGhim("M4_NGUON_REVIEW_CHUA_GHIM", f"Module {fullname} của lõi nguồn chưa được ghim SHA — không nạp.")

    def find_spec(self, fullname, path=None, target=None):
        vt = self._vi_tri(fullname)
        if vt is None:
            return None
        rel, la_goi = vt
        thu_muc = self.goc / fullname.replace(".", "/")
        if rel == "":
            spec = importlib.machinery.ModuleSpec(fullname, self, is_package=True)
            spec.submodule_search_locations = [str(thu_muc)]
            return spec
        return importlib.util.spec_from_file_location(fullname, str(self.goc / rel), loader=self,
                                                      submodule_search_locations=[str(thu_muc)] if la_goi else None)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        rel, _ = self._vi_tri(module.__spec__.name)
        if rel == "":
            setattr(module, DAU_GHIM, "NAMESPACE")
            return
        p = self.goc / rel
        if p.is_symlink() or not p.is_file():
            raise LoiNapGhim("M4_NGUON_REVIEW_CHUA_NAP", f"Thiếu tệp lõi nguồn {rel}.")
        raw = p.read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.pin[rel]:
            raise LoiNapGhim("M4_NGUON_REVIEW_SAI_PIN", f"Tệp lõi nguồn {rel} khác bản đã ghim — không thực thi.")
        code = compile(raw, str(p), "exec", dont_inherit=True)
        setattr(module, DAU_GHIM, self.pin[rel])
        exec(code, module.__dict__)  # noqa: S102 — chỉ bytes đã khớp SHA ghim

    def hop_le(self, ten: str, module) -> bool:
        """M4-01B2: module trong cache chỉ hợp lệ khi gắn ĐÚNG bộ nạp này (identity), đúng tên, dấu ghim = PIN của đúng tệp và origin = goc/<rel>.
        Dấu khác None nhưng sai pin/origin/loader (giả, cũ, nạp nơi khác) → không hợp lệ."""
        try:
            vt = self._vi_tri(ten)
        except LoiNapGhim:
            return False
        if vt is None:
            return False
        rel, _ = vt
        spec = getattr(module, "__spec__", None)
        if spec is None or spec.loader is not self or spec.name != ten or getattr(module, "__loader__", None) is not self:
            return False
        dau = getattr(module, DAU_GHIM, None)
        if rel == "":
            return dau == "NAMESPACE"
        tep = getattr(module, "__file__", None)
        if dau != self.pin[rel] or not tep or spec.origin != tep:
            return False
        try:
            return Path(tep).resolve() == (self.goc / rel).resolve()
        except OSError:
            return False

    def sai_cache(self) -> list[str]:
        """Tên module thuộc các gói gốc đang có trong sys.modules nhưng không hợp lệ theo hop_le."""
        return sorted(n for n, m in list(sys.modules.items()) if n.split(".")[0] in self.goi_goc and not self.hop_le(n, m))


def xung_dot(goi_goc) -> list[str]:
    """Tên module thuộc các gói gốc đã có trong sys.modules mà KHÔNG do một bộ nạp ghim đang cài nạp hợp lệ (dấu giả/khác pin/origin cũng tính)."""
    goi = frozenset(goi_goc)
    bo = [f for f in sys.meta_path if isinstance(f, BoNapGhim)]
    return sorted(n for n, m in list(sys.modules.items()) if n.split(".")[0] in goi and not any(b.hop_le(n, m) for b in bo))


def cai(bo: BoNapGhim) -> BoNapGhim:
    """Đặt finder lên đầu sys.meta_path (một lần cho mỗi goc); trả về đúng instance đang cài (cache chỉ hợp lệ với instance này)."""
    for f in sys.meta_path:
        if isinstance(f, BoNapGhim) and f.goc == bo.goc:
            if f.pin != bo.pin or f.goi_goc != bo.goi_goc:
                raise LoiNapGhim("M4_NGUON_REVIEW_SAI_PIN", "Bộ nạp ghim đã cài với bảng PIN khác — không dùng chung.")
            return f
    sys.meta_path.insert(0, bo)
    return bo
