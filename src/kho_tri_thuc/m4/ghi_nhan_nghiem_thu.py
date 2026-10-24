"""M4-03B-01 — adapter MỎNG nguồn nghiệm thu (NT) cho dịch vụ dùng chung `k2/ghi_nhan_chung.py`.

Không định nghĩa quyền/đồ thị/hiện hành mới: tái dùng ĐÚNG 03A —
- kiểm sớm: m4.kt_kiem(cho, 'XEM') trên login thường (ID+login hoạt động + M4 + KE_TOAN dự án + vai trò toàn cục KE_TOAN/KE_TOAN_TRUONG);
- trên giao dịch chủ bảng: khóa TẤT CẢ gốc trước (m4.kt_khoa(cho,'XEM') khi ghi = HĐ→đợt→phiên bản→gốc→revision KT FOR UPDATE; m4._kt_khoa_doc khi
  đọc = HĐ FOR SHARE), theo thứ tự (hop_dong_id, id) do SQL trả; rồi với TỪNG gốc: producer M24 qua `ke_toan_nghiem_thu._ghim_do_thi` → ngay sau đó
  `kho._dc_nt_ghi(cho)` chép kết quả m4._kt_hien_hanh của chứng thực vừa ghim vào bản đồ GUC giao dịch (chứng thực 03A chỉ giữ một gốc mỗi lúc).
NT-only không cần M2. Không đọc/ghi tiền, không AP/claim/proposal.
"""

from __future__ import annotations

from ..k2.ghi_nhan_chung import GhiNhanChungK2
from ..ha_tang.primitives import DataError
from . import ke_toan_nghiem_thu as KT


class NguonNghiemThu:
    def __init__(self, xd):
        self.xd = xd

    def kiem_som(self, dt, cho: str) -> None:
        xd = self.xd
        with xd._tx(dt):
            xd._mot("SELECT m4.kt_kiem(%s::uuid, 'XEM') AS q", (cho,))

    def khoa_ghim(self, c, dt, chos: list, ghi: bool) -> None:
        xd = self.xd
        if len(set(chos)) != len(chos):
            raise DataError("DC_THAM_SO_SAI", "Gốc nghiệm thu bị lặp.")
        for cho in chos:  # khóa hết trước (thứ tự SQL), rồi mới dựng đồ thị — không giữ ghim của gốc này khi chờ khóa gốc khác
            if ghi:
                xd._r1(c, "SELECT m4.kt_khoa(%s::uuid, 'XEM') AS q", (cho,))
            else:
                xd._r1(c, "SELECT m4._kt_khoa_doc(%s::uuid) AS q", (cho,))
        for cho in chos:
            KT._ghim_do_thi(xd, c, dt, cho)
            xd._r1(c, "SELECT kho._dc_nt_ghi(%s::uuid) AS h", (cho,))


def dich_vu(xd) -> GhiNhanChungK2:
    """Factory cho integration owner (route/UI KHÔNG nối trong gói này)."""
    return GhiNhanChungK2(xd, NguonNghiemThu(xd))


def ref_tu_kt(ct: dict) -> dict:
    """Ref NT từ DTO chi tiết 03A (context.kt_pending_id + context.phong_bi_id) — chỉ chép ID máy chủ đã trả, không suy."""
    ctx = (ct or {}).get("context") or {}
    if not ctx.get("kt_pending_id") or not ctx.get("phong_bi_id"):
        raise DataError("DC_THAM_SO_SAI", "DTO 03A thiếu kt_pending_id/phong_bi_id.")
    return {"kind": "NT", "occurrence_id": ctx["kt_pending_id"], "source_version_id": ctx["phong_bi_id"], "part_id": None}
