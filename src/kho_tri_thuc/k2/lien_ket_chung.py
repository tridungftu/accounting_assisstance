"""Lớp liên kết/phân bổ tiền DÙNG CHUNG (binding M9 §6, R1–R4) — một chỗ cho CRM, M9 và consumer M2/M7 tiếp theo.

Không phải engine hạch toán: chỉ (1) biên nhận idempotent bền `kho.bien_nhan_thao_tac` (PN, module, operation, client_key) + hash yêu cầu
canonical — cùng khóa cùng nội dung trả biên nhận cũ (kể cả đã hủy), khác nội dung → 409; kiểm quyền TRƯỚC khi trả lại; (2) khóa theo thứ tự
chung HĐ UUID sorted → BANK UUID sorted → đích logic sorted → revision sorted; (3) đọc ngân sách BANK (`kho.tien_con_lai`, gồm mọi module,
cần proof encoding) và ngân sách đích logic xuyên revision (`kho.dich_tien_con_lai`). CSDL kiểm lại toàn bộ khi commit (trigger deferred).

Map contract cho consumer sau (để một registry dùng chung): M2 dùng cùng `kho.lien_ket_phan_bo` (thêm FK đích `mua_nghia_vu_phien_ban` vào
CHECK exactly-one-target), cùng `kho.dich_phan_bo_tien` (target_kind mới qua migration, khóa logic từ nghĩa vụ mua ổn định), cùng biên nhận và
`khoa(...)`; M10/recognition dùng khóa logic (PN, đích, loại sự kiện kế toán, kỳ) — không dùng ngân sách tiền thay khóa ghi nhận.

R16 (L11 số lượng): phần cuối file thêm lớp mỏng quantity-only (preview/xác nhận/undo/còn lại) gọi hàm CSDL kho.l11_*; KHÔNG dùng helper tiền ở trên.
"""

from __future__ import annotations

import json
import re
from typing import Iterable

from ..ha_tang.primitives import DataError, canonical_json, sha256


def bam_yeu_cau(payload: dict) -> str:
    return sha256(canonical_json(payload).encode())


def tim_bien_nhan(conn, pn: str, module: str, operation: str, client_key: str, request_sha256: str) -> dict | None:
    row = conn.execute("""SELECT id, request_sha256, result_json FROM kho.bien_nhan_thao_tac
                          WHERE phap_nhan_id = %s AND module = %s AND operation = %s AND client_key = %s""", (pn, module, operation, client_key)).fetchone()
    if row is None:
        return None
    r = dict(row) if not isinstance(row, dict) else row
    if r["request_sha256"] != request_sha256:
        raise DataError("IDEMPOTENCY_KHAC", "Khóa thao tác đã dùng cho yêu cầu khác nội dung.")
    return {**r["result_json"], "bien_nhan_id": str(r["id"]), "lap_lai": True}


def ghi_bien_nhan(conn, pn: str, module: str, operation: str, client_key: str, request_sha256: str, ket_qua: dict, actor: str) -> str:
    if not isinstance(client_key, str) or not client_key.strip() or len(client_key) > 200:
        raise DataError("KHOA_IDEMPOTENCY", "Cần khóa thao tác 1–200 ký tự.")
    return str(conn.execute("""INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor)
                               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                            (pn, module, operation, client_key, request_sha256, json.dumps(ket_qua, ensure_ascii=False, default=str), actor)).fetchone()["id"])


def khoa(conn, hop_dong_ids: Iterable = (), bank_ids: Iterable = ()) -> None:
    """Thứ tự khóa chung (binding §6): HĐ sorted → BANK sorted; đích logic/revision khóa sau đó trong trigger CSDL (quyền chủ). Mỗi đích thuộc
    đúng một HĐ nên khóa HĐ tuần tự hóa mọi tiêu thụ đích; revision typed bất biến. Caller resolve đủ tập trước; thiếu thì rollback/retry."""
    for sql, ids in (("SELECT 1 FROM master.hop_dong WHERE id = %s FOR UPDATE", hop_dong_ids),
                     ("SELECT 1 FROM kho.chung_tu WHERE id = %s FOR UPDATE", bank_ids)):
        for i in sorted({str(x) for x in ids}):
            conn.execute(sql, (i,))


def tien_con_lai(conn, bank_id) -> dict | None:
    """Ngân sách BANK chung mọi module (wrapper CSDL kiểm ID/login + M1 + PN). None = ngoài quyền/không tồn tại."""
    row = conn.execute("SELECT * FROM kho.tien_con_lai(%s)", (bank_id,)).fetchone()
    return dict(row) if row else None


def dich_con_lai(conn, dich_id, valid_on=None) -> dict | None:
    row = conn.execute("SELECT * FROM kho.dich_tien_con_lai(%s, %s)", (dich_id, valid_on)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------------------------------------------------------------------------
# L11 SỐ LƯỢNG (R16, docs/GIAO-CODE-L11-QUANTITY-01.md §4–§6) — CHỈ số lượng, không tiền/331/BANK/stock engine. Hai lượng native, hai pool ổn định.
# Mọi quyết định (quyền hiện hành BOTH, namespace/H/replay, khóa gốc→pool, CAS, ngân sách full-domain confirmed+held, số học exact) nằm ở hàm
# CSDL kho.l11_*; lớp này chỉ kiểm hình thức sớm (chuỗi số exact, không Number/bool/float, không factor/kind/PN/owner từ trình duyệt) rồi gọi
# trên giao dịch đã đặt danh tính phiên. Không có helper khóa tiền nào được gọi ở nhánh này.
# ---------------------------------------------------------------------------------------------------------------------------------------------
L11_KHONG_NHAN = ("factor", "he_so", "tu_so", "mau_so", "ratio", "kind", "approved", "PROVEN", "proven", "phap_nhan", "phap_nhan_id", "owner",
                  "owner_module", "pool_id", "don_vi", "so_luong_pool_hoa_don", "so_luong_pool_phieu", "trang_thai", "hieu_luc", "path", "url", "duong_dan")
L11_LIEN_KET_TRUONG = {
    "preview": ("cau_noi_id", "dong_phien_ban_id", "ma_hoa_hoa_don_id", "ma_hoa_phieu_id", "bang_chung_hang_id", "bang_chung_ty_le_id",
                "so_luong_hoa_don", "so_luong_phieu"),
    "xac-nhan": ("cau_noi_id", "dong_phien_ban_id", "ma_hoa_hoa_don_id", "ma_hoa_phieu_id", "bang_chung_hang_id", "bang_chung_ty_le_id",
                 "so_luong_hoa_don", "so_luong_phieu", "expected_graph", "khoa", "ly_do"),
    "huy": ("child_id", "expected_graph", "khoa", "ly_do"),
}
_SO_NGUON = re.compile(r"(0|[1-9][0-9]{0,25})(\.[0-9]{1,12})?")


def l11_so_luong_text(v, ten: str) -> str:
    """Lượng native phải là CHUỖI thập phân dương exact (≤26 chữ số nguyên, ≤12 lẻ): không Number/bool/null, không mũ/khoảng trắng, không làm tròn."""
    if not isinstance(v, str) or not _SO_NGUON.fullmatch(v) or set(v.replace(".", "")) == {"0"}:
        raise DataError("L11_SO_LUONG_SAI", f"{ten} phải là chuỗi số thập phân dương chính xác (38,12) — không Number/làm tròn/mặc định.")
    return v


def l11_yeu_cau(hanh_dong: str, yeu_cau: dict) -> dict:
    """Chỉ đúng trường cho phép theo thao tác; không nhận authority từ trình duyệt. Trả body cho hàm CSDL (khóa → client_key, lý do → reason)."""
    if hanh_dong not in L11_LIEN_KET_TRUONG:
        raise DataError("NOT_FOUND", "Không có thao tác liên kết số lượng này.")
    if not isinstance(yeu_cau, dict):
        raise DataError("L11_YEU_CAU_SAI", "Yêu cầu phải là object.")
    if any(k in yeu_cau for k in L11_KHONG_NHAN):
        raise DataError("L11_CLIENT_AUTHORITY", "PN/chủ sở hữu/hệ số/kind/duyệt/pool/lượng pool do máy chủ dẫn xuất; không nhận từ trình duyệt.")
    if set(yeu_cau) - set(L11_LIEN_KET_TRUONG[hanh_dong]):
        raise DataError("L11_YEU_CAU_SAI", "Yêu cầu liên kết số lượng có trường ngoài phạm vi.")
    than = {k: yeu_cau.get(k) for k in L11_LIEN_KET_TRUONG[hanh_dong] if k in yeu_cau}
    for k in ("so_luong_hoa_don", "so_luong_phieu"):
        if k in than or hanh_dong == "xac-nhan":
            l11_so_luong_text(than.get(k), k)
    if "khoa" in than:
        than["client_key"] = than.pop("khoa")
    if "ly_do" in than:
        than["reason"] = than.pop("ly_do")
    return than


def l11_goi(conn, ham: str, than: dict) -> dict:
    """Gọi hàm CSDL L11 (definer có guard quyền hiện hành bên trong) trên giao dịch đã đặt danh tính phiên."""
    if ham not in ("l11_xem_truoc", "l11_xac_nhan", "l11_huy", "l11_ma_hoa", "l11_xac_nhan_bang_chung", "l11_huy_bang_chung"):
        raise DataError("NOT_FOUND", "Không có hàm L11 này.")
    row = conn.execute(f"SELECT kho.{ham}(%s::jsonb) AS v", (json.dumps(than, ensure_ascii=False),)).fetchone()
    return row["v"] if isinstance(row, dict) else row[0]


def luong_con_lai(conn, pool_id) -> dict | None:
    """Ngân sách pool số lượng (sức chứa hiện hành / confirmed / held / còn lại hoặc NULL bị chặn) theo quyền BOTH READ hiện hành."""
    row = conn.execute("SELECT kho.luong_con_lai(%s::uuid) AS v", (pool_id,)).fetchone()
    return row["v"] if isinstance(row, dict) else row[0]
