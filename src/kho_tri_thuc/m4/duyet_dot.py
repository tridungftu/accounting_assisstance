"""M4-02C — miền duyệt hồ sơ đợt (kết luận / chấp thuận DUYET / PDF hồ sơ đã duyệt / seal / KT chờ xác nhận / phiên bản kế tiếp) + provider lịch sử đợt
trước đã duyệt. `k2/xay_dung.py` chỉ là mặt tiền mỏng gọi vào đây; module này KHÔNG import xay_dung (nhận đối tượng XayDungK2 qua tham số).

Nguyên tắc:
- Máy chủ sở hữu mọi dữ kiện: đồ thị nguồn/review + SHA, hàng/đơn vị/số đề xuất, mã phát hiện, hash/độ dài PDF, ID, trạng thái. Trình duyệt chỉ gửi
  ID đã chọn + revision + expected_basis + số chấp nhận (chuỗi thập phân chuẩn hoặc null) + lý do + khóa.
- Quyền HIỆN HÀNH kiểm trước biên nhận/blob/bằng chứng (m4.duyet_kiem trong m4.duyet_khoa); khóa HĐ → đợt → phiên bản → biên nhận; CAS revision
  + đồ thị trong CSDL; seal dùng chung một hàm SQL cho hai thứ tự (duyệt→PDF, PDF→duyệt).
- Thiếu ≠ 0: tiền/khối lượng vắng là null và chặn chấp thuận; cảnh báo review được xử lý bằng lý do tường minh; DA_NOP/review đã công bố/số đề xuất
  nguồn KHÔNG phải chấp thuận. Không AP, không Request (gói M4-03/M4-04).
"""

from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext

from ..ha_tang.primitives import DataError, canonical_json, sha256
from ..ha_tang.store import write_immutable
from . import nguon_review as NR
from .sql_duyet import TIEN, VAI_PDF
from .review_dot_pg import doc_lich_su_chep

SCHEMA = "M4_DUYET_PDF_V1"
DO_THI = "m4.duyet.graph/1"
TRANG_THAI = ("CHO_KET_LUAN", "CHO_DUYET", "CHO_PDF", "DA_SEAL", "CAN_KIEM_LAI", "CHUA_NOP")  # CHUA_NOP: biến thể gắn thẻ chua_nop=true, không phiên bản
DAT_DU = ("CHECKED", "KHONG_AP_DUNG")  # cùng chung_tu_adapter.DAT_DU (không import adapter để không nạp lõi nguồn khi chỉ đọc DTO)
TIEN_RE = re.compile(r"(0|[1-9][0-9]{0,17})(\.[0-9]?[1-9])?")
KL_RE = re.compile(r"(0|[1-9][0-9]{0,17})(\.[0-9]{0,5}[1-9])?")
TIEN_TE_RE = re.compile(r"[A-Z]{3}")
HEX_RE = re.compile(r"[0-9a-f]{64}")
DONG_TOI_DA = 5000
LY_DO_TOI_DA = 2000
# hành động lệnh → (quyền SQL m4.duyet_kiem, hành động biên nhận)
LENH = {"KET_LUAN": ("KET_LUAN", "DUYET_KET_LUAN"), "CHAP_THUAN": ("CHAP_THUAN", "DUYET_CHAP_THUAN"), "PDF": ("PDF", "DUYET_PDF"),
        "PHIEN_BAN": ("PHIEN_BAN", "DUYET_PHIEN_BAN"), "PHIEN_BAN_NOP": ("PHIEN_BAN_NOP", "DUYET_PHIEN_BAN_NOP")}
ID_ACK = ("ket_luan_id", "quyet_dinh_id", "pdf_id", "seal_id", "kt_pending_id")


# ================================================================================================== kiểm đầu vào (chặt, không đoán)
def _sai(ten: str, ma: str = "M4_THAM_SO_SAI"):
    raise DataError(ma, f"Trường {ten} không hợp lệ.")


def _uuid(v, ten: str) -> str:
    if not isinstance(v, str):
        _sai(ten)
    try:
        return str(uuid.UUID(v))
    except ValueError:
        _sai(ten)


def _rev(v) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 10 ** 6:
        _sai("revision")
    return v


def _hex(v) -> str:
    if not isinstance(v, str) or not HEX_RE.fullmatch(v):
        raise DataError("M4_DUYET_CO_SO_SAI", "expected_basis phải là SHA-256 căn cứ của hồ sơ đang xem (lấy từ màn Duyệt & PDF).")
    return v


def _ly_do(v, *, bat_buoc: bool):
    if v is None or (isinstance(v, str) and not v.strip()):
        if bat_buoc:
            raise DataError("M4_THIEU_LY_DO", "Cần lý do/ý kiến.")
        return None
    if not isinstance(v, str) or len(v) > LY_DO_TOI_DA or any(ord(c) < 32 and c not in "\n\t" for c in v):
        _sai("ly_do")
    return v


def tien(v, ten: str, *, vnd: bool):
    """Tiền: chuỗi thập phân CHUẨN không âm (≤2 số lẻ, không số 0 thừa) hoặc null (= chưa có, KHÁC 0). VND không có phần lẻ. Không nhận số JS."""
    if v is None:
        return None
    if not isinstance(v, str) or not TIEN_RE.fullmatch(v):
        raise DataError("M4_DUYET_SO_SAI", f"{ten} phải là chuỗi thập phân chuẩn không âm (vd '1250000' hoặc '12.5') hoặc null — không nhận số/định dạng khác.")
    if vnd and "." in v:
        raise DataError("M4_DUYET_SO_SAI", f"{ten}: VND không có phần lẻ.")
    return v


def khoi_luong(v, ten: str):
    """Khối lượng chấp nhận: chuỗi thập phân chuẩn không âm ≤6 số lẻ hoặc null (chưa chấp nhận, KHÁC 0)."""
    if v is None:
        return None
    if not isinstance(v, str) or not KL_RE.fullmatch(v):
        raise DataError("M4_DUYET_SO_SAI", f"{ten} phải là chuỗi thập phân chuẩn không âm (≤6 số lẻ) hoặc null.")
    return v


def kiem_tien_te(v):
    if v is None:
        return None
    if not isinstance(v, str) or not TIEN_TE_RE.fullmatch(v):
        raise DataError("M4_DUYET_SO_SAI", "tien_te phải là mã ISO 4217 ba chữ in hoa (vd VND) hoặc null.")
    return v


def kiem_dong_nt(v) -> list:
    if not isinstance(v, list) or len(v) > DONG_TOI_DA:
        _sai("dong_nt")
    out, thay = [], set()
    for x in v:
        if not isinstance(x, dict) or set(x) != {"row_id", "khoi_luong_chap_nhan"}:
            raise DataError("M4_THAM_SO_SAI", "Mỗi dòng dong_nt chỉ gồm row_id, khoi_luong_chap_nhan.")
        rid = x["row_id"]
        if not isinstance(rid, str) or not 1 <= len(rid) <= 600 or rid in thay:
            _sai("dong_nt.row_id")
        thay.add(rid)
        out.append({"row_id": rid, "khoi_luong_chap_nhan": khoi_luong(x["khoi_luong_chap_nhan"], f"Khối lượng chấp nhận dòng {rid[:60]}")})
    return sorted(out, key=lambda r: r["row_id"])


def kiem_xu_ly(v) -> list:
    if not isinstance(v, list) or len(v) > DONG_TOI_DA:
        _sai("xu_ly_phat_hien")
    out, thay = [], set()
    for x in v:
        if not isinstance(x, dict) or set(x) != {"finding_id", "ly_do"}:
            raise DataError("M4_THAM_SO_SAI", "Mỗi xử lý phát hiện chỉ gồm finding_id, ly_do.")
        fid = x["finding_id"]
        if not isinstance(fid, str) or not 1 <= len(fid) <= 300 or fid in thay:
            _sai("xu_ly_phat_hien.finding_id")
        thay.add(fid)
        out.append({"finding_id": fid, "ly_do": _ly_do(x["ly_do"], bat_buoc=True)})
    return sorted(out, key=lambda r: r["finding_id"])


def so_chuan(x):
    """Số ĐỀ XUẤT từ nguồn (L2/BOQ) → chuỗi thập phân chuẩn để hiển thị; không phải số chấp nhận. Không đọc được → null (không bịa 0)."""
    if x is None or isinstance(x, bool):
        return None
    try:
        if isinstance(x, float):
            if x != x or x in (float("inf"), float("-inf")):
                return None
            d = Decimal(repr(x))
        elif isinstance(x, (int, Decimal)):
            d = Decimal(x)
        elif isinstance(x, str) and x.strip():
            d = Decimal(x.strip())
        else:
            return None
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite():
        return None
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ================================================================================================== provider lịch sử đợt trước đã duyệt
def lich_su_da_duyet(xd, c, d: dict) -> dict | None:
    """Thay CHUA_CO_NGUON bằng quyết định ĐÃ SEAL của các đợt TRƯỚC cùng HĐ (bản sửa đổi mới nhất đã seal của mỗi đợt; số liệu chốt trong seal nên
    không đổi khi căn cứ hiện hành đổi về sau). DA_NOP/review đã công bố/số đề xuất nguồn KHÔNG phải đã duyệt. Đợt trước chưa seal, ngày NT thiếu/sau
    đợt này, hoặc dòng vắng trong một seal → INCOMPLETE (không 0). Chưa có schema M24 hoặc chưa đợt trước nào seal → None (giữ lý do cũ, byte cũ)."""
    if not d or not d.get("hop_dong_id") or d.get("so_dot") is None:
        return None
    if not xd._r1(c, "SELECT to_regclass('m4.duyet_seal') IS NOT NULL AS co")["co"]:
        return None
    truoc = xd._rn(c, """SELECT id, so_dot, ngay_nghiem_thu, trang_thai FROM m4.dot WHERE hop_dong_id = %s::uuid AND so_dot < %s ORDER BY so_dot""",
                   (d["hop_dong_id"], d["so_dot"]))
    if not truoc:
        return None
    seals = {s["dot_id"]: s for s in xd._rn(c, """SELECT DISTINCT ON (s.dot_id) s.id, s.dot_id, s.phien_ban_id, v.so AS phien_ban_so, s.so_lieu, s.so_lieu_sha256
                                                  FROM m4.duyet_seal s JOIN m4.duyet_phien_ban v ON v.id = s.phien_ban_id
                                                  WHERE s.hop_dong_id = %s::uuid AND s.dot_id = ANY(%s::uuid[])
                                                  ORDER BY s.dot_id, v.so DESC""", (d["hop_dong_id"], [t["id"] for t in truoc]))}
    if not seals:
        return None
    ngay = str(d.get("ngay_nghiem_thu") or "")[:10] or None
    dots, du, theo_dong = [], True, []
    for t in truoc:
        s = seals.get(t["id"])
        nt = str(t.get("ngay_nghiem_thu") or "")[:10] or None
        if s is None:
            du = False
            dots.append({"dot_id": t["id"], "so_dot": t["so_dot"], "ngay_nghiem_thu": nt, "trang_thai": "INCOMPLETE",
                         "ly_do": "Đợt trước chưa có hồ sơ được chấp thuận + PDF đã seal (DA_NOP chỉ là đã nộp)"})
            continue
        if not ngay or not nt or nt > ngay:
            du = False
            dots.append({"dot_id": t["id"], "so_dot": t["so_dot"], "ngay_nghiem_thu": nt, "trang_thai": "INCOMPLETE", "seal_id": s["id"],
                         "ly_do": "Thiếu ngày nghiệm thu hoặc đợt trước có ngày NT sau đợt này — không cộng dồn"})
            continue
        sl = s["so_lieu"] or {}
        theo_dong.append({x["row_id"]: x.get("khoi_luong_chap_nhan") for x in sl.get("dong") or []})
        dots.append({"dot_id": t["id"], "so_dot": t["so_dot"], "ngay_nghiem_thu": nt, "trang_thai": "DA_DUYET", "seal_id": s["id"],
                     "phien_ban_id": s["phien_ban_id"], "phien_ban_so": s["phien_ban_so"], "so_lieu_sha256": s["so_lieu_sha256"],
                     "tien": {k: sl.get(k) for k in ("tien_te", *TIEN)}})
    luy_ke = {}
    for rid in sorted({k for m in theo_dong for k in m}):
        vals = [m.get(rid) for m in theo_dong]
        if not du or any(v is None for v in vals):
            luy_ke[rid] = {"khoi_luong_chap_nhan": None, "trang_thai": "INCOMPLETE"}
        else:
            luy_ke[rid] = {"khoi_luong_chap_nhan": so_chuan(sum((Decimal(v) for v in vals), Decimal(0))), "trang_thai": "CO"}
    return {"trang_thai": "CO" if du else "INCOMPLETE", "nguon": "m4.duyet_seal", "dot": dots, "luy_ke": luy_ke,
            "ly_do": ("Lũy kế từ quyết định đã seal của mọi đợt trước cùng HĐ" if du else
                      "Có đợt trước chưa seal/thiếu ngày — lũy kế chưa đủ (INCOMPLETE, không coi vắng là 0)")}


def gom_lich_su_review_chep(chep, so_dot, dots_m4, dong_nt=(), ngay_nghiem_thu=None):
    """Projection chỉ để xem, độc lập hoàn toàn với prior/basis/kết luận.

    dots_m4 chứa seal mới nhất của từng đợt, số liệu kỳ trong seal (không
    cộng các số lũy kế). Mã HM lấy từ chính seal, không đoán theo row_id hiện
    hành. Chỉ cộng khi ĐVT rõ, khớp dòng hiện tại và ngày NT không sau
    đợt hiện tại. Thiếu mã/dòng/số hoặc ánh xạ mâu thuẫn là chưa đủ.
    """
    if chep is None:
        return None

    def decimal(v):
        s = so_chuan(v)
        return None if s is None else Decimal(s)

    def tong(vals):
        if not vals or any(v is None for v in vals):
            return None
        with localcontext() as ctx:
            ctx.prec = max(28, sum(len(v.as_tuple().digits) + abs(v.as_tuple().exponent) for v in vals) + 10)
            return sum(vals, Decimal(0))

    def don_vi(v):
        return (" ".join(v.split()).casefold() or None) if isinstance(v, str) else None

    def ngay(v):
        try:
            return date.fromisoformat(str(v or "")[:10])
        except ValueError:
            return None

    hien_tai = {r["ma_hm"]: don_vi(r.get("dvt")) for r in dong_nt if r.get("ma_hm")}
    dem_ma = Counter(r.get("ma_hm") for r in dong_nt if r.get("ma_hm"))
    ngay_nay = ngay(ngay_nghiem_thu)
    legacy = {d["dot"]: d for d in chep["dot"] if d["dot"] < so_dot}
    m4 = {d["so_dot"]: d for d in dots_m4 if d["so_dot"] < so_dot}
    rows_review = [r for r in chep["dong"] if r["dot"] in legacy]
    periods, maps, units, bo_qua = [], [], [], 0
    thieu_ngay = False
    thieu_ma = any(not r.get("ma_hm") or not r["ma_hm"].strip() for r in rows_review)
    codes = {ma for ma in hien_tai if ma.strip()}
    codes.update(r["ma_hm"] for r in rows_review if r.get("ma_hm") and r["ma_hm"].strip())
    for n in sorted(set(legacy) | set(m4)):
        l, m = legacy.get(n), m4.get(n)
        lech = l and l.get("m4_dot_id") is not None and (
            l.get("m4_so_dot") != n or m is None or str(l["m4_dot_id"]) != str(m["id"]))
        if lech or (m is not None and not m.get("seal_id")):
            nguon, rows = "CAN_XEM_LAI", []
        elif m is not None:
            nguon = "M4_SEAL"
            rows = (m.get("so_lieu") or {}).get("dong") or []
            bo_qua += int(l is not None)
        else:
            nguon = "REVIEW_CHEP"
            rows = [r for r in rows_review if r["dot"] == n]
        nt = ngay((m if nguon == "M4_SEAL" else l or {}).get("ngay_nghiem_thu"))
        thieu_ngay |= ngay_nay is None or nt is None or nt > ngay_nay
        mapping, dvt = {}, {}
        for r in rows:
            ma = r.get("ma_hm")
            if not ma or not ma.strip():
                thieu_ma = True
                continue
            codes.add(ma)
            val = decimal(r.get("khoi_luong_chap_nhan" if nguon == "M4_SEAL" else "kl_ky"))
            # Nhiều row_id seal cùng mã: chưa biết quan hệ, không tự gộp.
            mapping[ma] = None if ma in mapping else val
            dvt.setdefault(ma, set()).add(don_vi(r.get("dvt")))
        maps.append((nguon, mapping))
        units.append(dvt)
        periods.append({"so_dot": n, "nguon": nguon})
    luy_ke = {}
    for ma in sorted(codes):
        review = sorted((r for r in rows_review if r.get("ma_hm") == ma), key=lambda r: r["dot"])
        unit = hien_tai.get(ma)
        khac_dvt_review = not unit or any(don_vi(r.get("dvt")) != unit for r in review)
        khac_dvt = khac_dvt_review or any(u.get(ma) != {unit} for u in units)
        vals = [decimal(r.get("kl_ky")) for r in review]
        # Đối chiếu cũng không được cộng các số khác/thiếu ĐVT, kể cả legacy
        # đã được seal thay. Giữ số lũy kế gốc cuối để người xem đối chiếu.
        tong_review = None if khac_dvt_review else tong(vals)
        cuoi = decimal(review[-1].get("kl_luy_ke")) if review else None
        lech = tong_review is not None and cuoi is not None and tong_review != cuoi
        # Mọi NULL của Review vẫn được giữ cờ thiếu, kể cả đợt đã bị seal thay.
        incomplete = (thieu_ma or thieu_ngay or khac_dvt or not periods or any(src == "CAN_XEM_LAI" or mapping.get(ma) is None for src, mapping in maps)
                      or any(decimal(r.get(k)) is None for r in review for k in ("kl_ky", "kl_luy_ke")))
        trung_ma = dem_ma[ma] > 1
        value = None if incomplete or lech or trung_ma else tong([mapping[ma] for _, mapping in maps])
        luy_ke[ma] = {"kl_luy_ke_gom_lich_su": value,
                      "trang_thai": "CAN_XEM_LAI" if trung_ma else "INCOMPLETE" if incomplete else "LECH_LUY_KE_REVIEW" if lech else "CO",
                      "doi_chieu": {"trang_thai": "LECH_LUY_KE_REVIEW" if lech else "INCOMPLETE" if review and (tong_review is None or cuoi is None) else "CO" if review else "KHONG_CO",
                                    "tong_kl_ky_review": tong_review, "kl_luy_ke_review": cuoi}}
        if trung_ma:
            luy_ke[ma]["ly_do"] = "Mã hạng mục xuất hiện nhiều dòng trong đợt này"
        elif khac_dvt:
            luy_ke[ma]["ly_do"] = "Đơn vị tính khác nhau hoặc chưa rõ, không cộng"
        elif thieu_ngay:
            luy_ke[ma]["ly_do"] = "Thiếu ngày nghiệm thu hoặc đợt trước có ngày NT sau đợt này — không cộng dồn"
    incomplete = (thieu_ma or not periods or not luy_ke
                  or any(p["nguon"] == "CAN_XEM_LAI" for p in periods)
                  or any(x["trang_thai"] in ("INCOMPLETE", "CAN_XEM_LAI") for x in luy_ke.values()))
    return {"nhan": "Gồm lịch sử Review đã chép — chưa qua duyệt M4", "dot": periods, "bo_qua_trung": bo_qua,
            "trang_thai": "INCOMPLETE" if incomplete else "LECH_LUY_KE_REVIEW" if any(x["trang_thai"] == "LECH_LUY_KE_REVIEW" for x in luy_ke.values()) else "CO",
            "luy_ke": luy_ke}


def lich_su_review_chep(xd, c, d, dong_nt=()):
    """Chỉ gọi ở DTO 02C, cùng snapshot phiên; không đi vào basis/seal."""
    if d.get("so_dot") is None or d["so_dot"] <= 1:
        return None
    chep = doc_lich_su_chep(c, d["hop_dong_id"])
    if chep is None:
        return None
    dots = xd._rn(c, """SELECT d.id,d.so_dot,s.id AS seal_id,s.so_lieu,d.ngay_nghiem_thu
        FROM m4.dot d LEFT JOIN LATERAL (
            SELECT s.id,s.so_lieu FROM m4.duyet_seal s
            JOIN m4.duyet_phien_ban v ON v.id=s.phien_ban_id
            WHERE s.dot_id=d.id ORDER BY v.so DESC LIMIT 1
        ) s ON true WHERE d.hop_dong_id=%s::uuid AND d.so_dot < %s ORDER BY d.so_dot""",
                  (d["hop_dong_id"], d["so_dot"]))
    lich_su = gom_lich_su_review_chep(chep, d["so_dot"], dots, dong_nt, d.get("ngay_nghiem_thu"))
    # Tính bằng Decimal; ở biên DTO dùng chuỗi thập phân/null như các số 02C
    # hiện có, để JSON không lỗi kiểu hoặc đi qua float làm mất chính xác.
    for row in lich_su["luy_ke"].values():
        row["kl_luy_ke_gom_lich_su"] = so_chuan(row["kl_luy_ke_gom_lich_su"])
        for col in ("tong_kl_ky_review", "kl_luy_ke_review"):
            row["doi_chieu"][col] = so_chuan(row["doi_chieu"][col])
    return lich_su


def _gan_lich_su_review_chep(dong, lich_su):
    lk = (lich_su or {}).get("luy_ke") or {}
    dem_ma = Counter(r.get("ma_hm") for r in dong if r.get("ma_hm"))
    out = []
    for r in dong:
        ma = r.get("ma_hm")
        history = lk.get(ma) if ma else None
        if ma and dem_ma[ma] > 1:
            history = {**(history or {}), "kl_luy_ke_gom_lich_su": None, "trang_thai": "CAN_XEM_LAI",
                       "ly_do": "Mã hạng mục xuất hiện nhiều dòng trong đợt này"}
        out.append({**r, "lich_su_review_chep": history})
    return out


# ================================================================================================== đồ thị nguồn/review của phiên bản
def _l3_cong_bo(xd, c, dot: str):
    return xd._r1(c, """SELECT r.id AS run_id, r.revision, r.trang_thai, r.basis_sha256, r.tao_boi_id, n.dang_nhap AS tao_dang_nhap,
                               x.ket_qua, x.ket_qua_sha256, x.basis_cong_bo_sha256
                        FROM m4.chung_tu_run r JOIN m4.chung_tu_result x ON x.run_id = r.id LEFT JOIN master.nguoi_dung n ON n.id = r.tao_boi_id
                        WHERE r.dot_id = %s::uuid AND r.trang_thai IN ('SUCCEEDED','PARTIAL') AND x.cong_bo
                        ORDER BY r.xong_luc DESC NULLS LAST, r.tao_luc DESC, r.id LIMIT 1""", (dot,))


def _dat_danh_tinh(c, nd_id, dang_nhap):
    c.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd_id or "", dang_nhap or ""))


def do_thi(xd, c, dt, d: dict, v: dict) -> tuple[dict, str, dict | None]:
    """Đồ thị căn cứ của phiên bản (gọi trong giao dịch chủ bảng đã kiểm quyền): phiên bản + kết quả Chứng từ L3 đã công bố MỚI NHẤT (CO khi basis lúc
    công bố = basis L3 chụp lại NGAY BÂY GIỜ, CU khi khác, CHUA_CO khi chưa có) + tham chiếu L2. Basis L3 hiện hành chụp theo ĐÚNG danh tính người công
    bố lần chạy đó (phần ghép tay L2 thấy được phụ thuộc quyền xem) để reviewer và duyệt viên ra cùng một SHA; danh tính phiên khôi phục ngay sau đó
    (quyền của người thao tác đã kiểm TRƯỚC, và vẫn là danh tính ghi). Trả (đồ thị, SHA, hàng L3 kèm ket_qua hoặc None)."""
    r = _l3_cong_bo(xd, c, d["id"])
    if r is not None and r.get("tao_dang_nhap"):
        _dat_danh_tinh(c, r["tao_boi_id"], r["tao_dang_nhap"])
        try:
            co = xd._chung_tu_co_so(c, d["id"])
        finally:
            _dat_danh_tinh(c, dt["id"], dt["dang_nhap"])
    else:
        co = xd._chung_tu_co_so(c, d["id"])
    sha_l3 = xd._sha_co_so(co)
    if r is None:
        l3 = {"trang_thai": "CHUA_CO", "run_id": None, "ly_do": "Đợt chưa có kết quả Chứng từ L3 đã công bố — chạy L3 sau khi nộp"}
    else:
        cb = r.get("basis_cong_bo_sha256") or r.get("basis_sha256")
        l3 = {"trang_thai": "CO" if cb == sha_l3 else "CU", "run_id": r["run_id"], "revision": r["revision"], "trang_thai_run": r["trang_thai"],
              "ket_qua_sha256": r["ket_qua_sha256"], "basis_sha256": cb}
        if cb != sha_l3:
            l3["ly_do"] = "Căn cứ (tệp/ghép tay/HĐ/BOQ/L2) đã đổi sau lần L3 đã công bố — Chạy lại L3 trước khi kết luận/duyệt"
    l2 = co.get("l2") or {}
    g = {"phien_ban": DO_THI, "dot_id": d["id"], "hop_dong_id": d["hop_dong_id"], "du_an_id": d["du_an_id"], "phap_nhan_id": d["phap_nhan_id"],
         "version": {k: v.get(k) for k in ("id", "so", "trang_thai", "parent_id", "digest", "revision_ho_so")},
         "vat_lieu": vat_lieu(d, v),
         "l3": l3, "l2": {k: l2.get(k) for k in ("trang_thai", "run_id", "basis_sha256", "ket_qua_sha256")}, "co_so_l3_sha256": sha_l3}
    return g, sha256(canonical_json(g).encode("utf-8")), r


def vat_lieu(d: dict, v: dict) -> dict:
    """Vật liệu hồ sơ của phiên bản còn đúng như lúc nộp? Mọi lệnh đổi HĐ/tham số/PL/BOQ tăng m4.ho_so_hop_dong.revision; tệp đợt khóa sau DA_NOP.
    Một L3 chạy lại trên căn cứ MỚI không làm phiên bản cũ áp dụng lại được — cần phiên bản kế tiếp + nộp/kiểm lại (CSDL chặn cùng điều kiện)."""
    nop, hien = v.get("revision_ho_so"), d.get("revision_ho_so_hien_hanh")
    return {"revision_ho_so_nop": nop, "revision_ho_so_hien_hanh": hien, "khop": nop is not None and nop == hien}


def _dong(kq) -> list:
    out = []
    for h in (kq or {}).get("hang_muc") or []:
        rid = str(h.get("khoa") or "")
        if not rid or len(rid) > 600:
            continue
        out.append({"row_id": rid, "ma_hm": (str(h.get("ma_hm"))[:500] or None) if h.get("ma_hm") else None,
                    "ten": str(h.get("ten") or "")[:1000] or None, "dvt": str(h.get("dvt") or "")[:100] or None,
                    "de_xuat": {"kl_kn": so_chuan(h.get("kl_kn")), "kl_lk": so_chuan(h.get("kl_lk")), "kl_hd": so_chuan(h.get("kl_hd")),
                                "don_gia": so_chuan(h.get("don_gia")), "dong_boq": h.get("dong") if isinstance(h.get("dong"), int) else None}})
    return out


def _phat_hien(kq) -> list:
    """Phát hiện L3 (id nguồn, hoặc 'L3:<thứ tự>:<mã>' khi nguồn không gán id — kết quả bất biến nên ổn định) + mục coverage chưa đạt ('COV:<mã>'):
    vắng/chưa chạy KHÔNG thành PASS — mỗi mục cần lý do xử lý tường minh trước khi chấp thuận."""
    out = []
    for i, f in enumerate((kq or {}).get("phat_hien") or []):
        if not isinstance(f, dict):
            continue
        fid = str(f["id"]) if f.get("id") not in (None, "") else f"L3:{i}:{f.get('code')}"
        out.append({"finding_id": fid[:300], "nguon": "L3", "code": f.get("code"), "level": f.get("level"), "title": f.get("title"),
                    "detail": f.get("detail"), "item": f.get("item"), "tai_lieu": f.get("tai_lieu"), "amount": so_chuan(f.get("amount"))})
    for ma, c in sorted(((kq or {}).get("coverage") or {}).items()):
        tt = (c or {}).get("trang_thai")
        if tt not in DAT_DU:
            out.append({"finding_id": f"COV:{ma}"[:300], "nguon": "COVERAGE", "code": ma, "level": tt, "title": f"Kiểm {ma}: {tt}",
                        "detail": (c or {}).get("ly_do"), "item": None, "tai_lieu": None, "amount": None})
    return out


def _pb_dto(v: dict, moi_nhat_id: str) -> dict:
    """Dòng lịch sử phiên bản (UI chọn theo version_id). Không trả snapshot đầy đủ — digest là định danh nội dung đã nộp."""
    return {"version_id": v["id"], "so": v["so"], "parent_version_id": v["parent_id"], "nop_id": v["nop_id"], "trang_thai": v["trang_thai"],
            "ly_do": v["ly_do"], "digest": v["digest"], "revision_ho_so": v["revision_ho_so"], "tao_boi": v["tao_boi"], "tao_luc": v["tao_luc"],
            "nop_boi": v["nop_boi"], "nop_luc": v["nop_luc"], "ket_luan_revision": v["ket_luan_revision"], "quyet_dinh_id": v["quyet_dinh_id"],
            "seal_id": v["seal_id"], "moi_nhat": v["id"] == moi_nhat_id}


def _kt(seal, goc, phong_bi: list) -> dict:
    """KT của PHIÊN BẢN ĐANG XEM: CHO_XAC_NHAN chỉ khi phiên bản này có seal (kèm phong bì của đúng seal đó); gốc logic của đợt (từ seal trước) vẫn
    trả ở goc_id/phong_bi làm lịch sử, KHÔNG coi là bàn giao của phiên bản chưa seal."""
    bi = next((b for b in phong_bi if seal and b["seal_id"] == seal["id"]), None)
    goc_id = goc["id"] if goc else None
    if bi:
        ly = None if bi["id"] == phong_bi[-1]["id"] else "Phong bì này đã có phong bì đính chính sau (cùng gốc KT)"
    else:
        ly = ("Phiên bản đang xem chưa seal — gốc KT của đợt (từ phiên bản đã seal trước) giữ nguyên, chưa có phong bì mới" if goc_id else
              "Chưa seal — chưa chuyển KT chờ xác nhận")
    return {"trang_thai": "CHO_XAC_NHAN" if bi else "CHUA_CHUYEN", "pending_id": goc_id if bi else None, "phong_bi_id": bi["id"] if bi else None,
            "phong_bi_hien_hanh": bool(bi) and bi["id"] == phong_bi[-1]["id"], "goc_id": goc_id, "phong_bi": phong_bi, "ly_do": ly}


def _id_hoac_none(v):
    if not isinstance(v, str):
        return None
    try:
        return str(uuid.UUID(v))
    except ValueError:
        return None


def _tep_can_cu(xd, c, d: dict, snap) -> list:
    """Metadata TỆP THẬT mà phiên bản đang xem đã chụp lúc nộp (snapshot m4.duyet_phien_ban), tách khỏi dữ kiện căn cứ có kiểu (can_cu). Chỉ tra
    m4.tep theo đúng id đã chụp trong đúng dự án — không mượn tệp hiện hành. Không gắn tệp → KHONG_GAN_TEP; không tra được → THIEU_METADATA (không
    coi là 0 tệp/0 byte); hash đã chụp khác hash lưu → KHONG_KHOP. Không bao giờ trả object_key."""
    s = snap if isinstance(snap, dict) else {}
    muc = []  # (vai, nhãn, tep_id, raw_sha256 đã chụp)
    hd = s.get("tep_hop_dong")
    muc.append(("HOP_DONG", "Hợp đồng", _id_hoac_none((hd or {}).get("id")) if isinstance(hd, dict) else None,
                (hd or {}).get("raw_sha256") if isinstance(hd, dict) else None))
    for p in s.get("phu_luc") or []:
        if isinstance(p, dict):
            muc.append(("PHU_LUC", f"Phụ lục {p.get('so_pl') or '(không số)'}", _id_hoac_none(p.get("tep_id")), None))
    for t in s.get("tai_lieu") or []:
        if isinstance(t, dict):
            muc.append(("HO_SO_DOT", f"Tài liệu đợt · {t.get('muc') or '(không mục)'}", _id_hoac_none(t.get("tep_id")), t.get("raw_sha256")))
    ids = sorted({m[2] for m in muc if m[2]})
    tep = {r["id"]: r for r in xd._rn(c, """SELECT id, vai_tro_tai_lieu, ten_goc, raw_sha256, byte_length FROM m4.tep
                                            WHERE du_an_id = %s::uuid AND id = ANY(%s::uuid[])""", (d["du_an_id"], ids))} if ids else {}
    boq_ids = sorted({x for x in (_id_hoac_none((q or {}).get("id")) for q in s.get("boq") or [] if isinstance(q, dict)) if x})
    boq = {r["boq_id"]: r for r in xd._rn(c, """SELECT q.id AS boq_id, q.raw_sha256 AS boq_sha256, t.id, t.vai_tro_tai_lieu, t.ten_goc, t.raw_sha256,
                                                       t.byte_length
                                                FROM m4.boq q LEFT JOIN m4.tep t ON t.id = q.tep_id AND t.du_an_id = q.du_an_id AND t.raw_sha256 = q.raw_sha256
                                                WHERE q.hop_dong_id = %s::uuid AND q.id = ANY(%s::uuid[])""", (d["hop_dong_id"], boq_ids))} if boq_ids else {}

    def mot(vai, nhan, tid, sha_chup, t, gan=None):
        if (tid is None) if gan is None else not gan:
            tt, ly = "KHONG_GAN_TEP", "Phiên bản không chụp tệp cho mục này"
        elif t is None or t.get("id") is None:
            tt, ly = "THIEU_METADATA", "Không tra được metadata của tệp đã chụp trong dự án — không mượn tệp hiện hành"
        elif sha_chup and sha_chup != t.get("raw_sha256"):
            tt, ly = "KHONG_KHOP", "SHA-256 tệp đã chụp khác SHA-256 tệp đang lưu — không coi là cùng tệp"
        else:
            tt, ly = "CO", None
        t = t or {}
        return {"vai": vai, "nhan": nhan, "tep_id": tid, "vai_tro_tai_lieu": t.get("vai_tro_tai_lieu"), "ten": t.get("ten_goc"),
                "raw_sha256": t.get("raw_sha256"), "byte_length": t.get("byte_length"), "raw_sha256_da_chup": sha_chup, "trang_thai": tt, "ly_do": ly}

    out = [mot(vai, nhan, tid, sha, tep.get(tid) if tid else None) for vai, nhan, tid, sha in muc]
    for q in s.get("boq") or []:
        if not isinstance(q, dict):
            continue
        bid = _id_hoac_none(q.get("id"))
        b = boq.get(bid) if bid else None
        # BOQ đã chụp luôn gắn một tệp (m4.boq.tep_id NOT NULL): không tra được dòng/tệp → THIEU_METADATA, không phải KHONG_GAN_TEP
        out.append(mot("BOQ", f"BOQ · {q.get('so_dong') if q.get('so_dong') is not None else '?'} dòng", (b or {}).get("id"),
                       (b or {}).get("boq_sha256"), b, gan=bid is not None))
    return out


# ================================================================================================== dịch vụ
class DuyetDot:
    def __init__(self, xd):
        self.xd = xd

    # ------------------------------------------------------------------ đọc
    def _thay(self, dt, dot: str) -> dict:
        """Quyền xem HIỆN HÀNH qua login ứng dụng (hàm SECURITY DEFINER, không lộ tồn tại) TRƯỚC mọi đọc trên kết nối chủ bảng."""
        xd = self.xd
        with xd._tx(dt):
            r = xd._mot("SELECT m4.duyet_doc_dot(%s::uuid) AS ok, m4.duyet_quyen(%s::uuid) AS q", (dot, dot))
        if not r or not r["ok"]:
            raise DataError("M4_DUYET_KHONG_THAY", "Không thấy đợt (hoặc ngoài phạm vi hiện hành).")
        return r["q"]

    @staticmethod
    def _dot(xd, c, dot: str) -> dict:
        return xd._r1(c, """SELECT d.id, d.hop_dong_id, d.du_an_id, a.phap_nhan_id, d.so_dot, d.ngay_nghiem_thu, d.trang_thai, d.revision,
                                   hd.so_hop_dong, h.revision AS revision_ho_so_hien_hanh
                            FROM m4.dot d JOIN master.du_an a ON a.id = d.du_an_id JOIN master.hop_dong hd ON hd.id = d.hop_dong_id
                                 JOIN m4.ho_so_hop_dong h ON h.hop_dong_id = d.hop_dong_id
                            WHERE d.id = %s::uuid""", (dot,))

    @staticmethod
    def _phien_ban(xd, c, dot: str) -> list:
        return xd._rn(c, """SELECT v.id, v.so, v.parent_id, v.nop_id, v.trang_thai, v.ly_do, v.digest, v.revision_ho_so, v.tao_boi, v.tao_luc, v.nop_boi,
                                   v.nop_luc, (SELECT max(k.revision) FROM m4.duyet_ket_luan k WHERE k.phien_ban_id = v.id) AS ket_luan_revision,
                                   (SELECT q.id FROM m4.duyet_quyet_dinh q WHERE q.phien_ban_id = v.id) AS quyet_dinh_id,
                                   (SELECT s.id FROM m4.duyet_seal s WHERE s.phien_ban_id = v.id) AS seal_id
                            FROM m4.duyet_phien_ban v WHERE v.dot_id = %s::uuid ORDER BY v.so""", (dot,))

    def xem(self, dang_nhap: str, *, dot_id, version_id=None) -> dict:
        dt = self.xd.danh_tinh(dang_nhap)
        dot = _uuid(dot_id, "dot_id")
        pb = None if version_id in (None, "") else _uuid(version_id, "version_id")
        return self._xem(dt, dot, pb)

    def _xem(self, dt, dot: str, pb: str | None) -> dict:
        xd = self.xd
        quyen = self._thay(dt, dot)
        with xd._tx_review(dt, rr=True) as c:  # một snapshot: quyền kiểm lại trong cùng giao dịch → đồ thị/kết luận/PDF/seal/KT
            c.execute("SELECT m4.duyet_kiem(%s::uuid, 'XEM')", (dot,))
            d = self._dot(xd, c, dot)
            vs = self._phien_ban(xd, c, dot)
            if pb is not None and not any(v["id"] == pb for v in vs):
                raise DataError("M4_DUYET_KHONG_THAY", "Không thấy phiên bản hồ sơ của đợt.")
            ctx = {"dot_id": d["id"], "hop_dong_id": d["hop_dong_id"], "du_an_id": d["du_an_id"], "phap_nhan_id": d["phap_nhan_id"],
                   "version_id": None, "revision": 0, "basis_sha256": None}
            goc = xd._r1(c, "SELECT id FROM m4.duyet_kt_cho WHERE dot_id = %s::uuid", (dot,))
            phong_bi = xd._rn(c, """SELECT id, seal_id, phien_ban_id AS version_id, thu_tu, truoc_id, noi_dung_sha256, tao_luc AS luc FROM m4.duyet_kt_phong_bi
                                    WHERE dot_id = %s::uuid ORDER BY thu_tu""", (dot,))
            su_kien = xd._rn(c, """SELECT hanh_dong, boi AS actor, luc, chi_tiet FROM m4.nhat_ky
                                   WHERE dot_id = %s::uuid AND (hanh_dong LIKE 'DUYET%%' OR hanh_dong = 'NOP') ORDER BY luc, id""", (dot,))
            base = {"schema": SCHEMA, "quyen": {k: bool((quyen or {}).get(k)) for k in ("xem", "ket_luan", "duyet", "tai_pdf", "phien_ban")},
                    "dot": {k: d[k] for k in ("so_dot", "ngay_nghiem_thu", "trang_thai", "so_hop_dong")},
                    "phien_ban": [_pb_dto(x, vs[-1]["id"]) for x in vs], "lich_su": su_kien,
                    "lich_su_review_chep": None}
            if not vs:
                # biến thể gắn thẻ CHUA_NOP (chỉ khi GET không chọn phiên bản — có pb thì đã 404 ở trên): không phiên bản/căn cứ/hiệu lực; mọi cờ lệnh
                # false (quyền xem giữ nguyên); không mượn gốc KT/phong bì/PDF/kết luận. Lịch sử sự kiện thật của đợt vẫn trả.
                return {**base, "quyen": {"xem": base["quyen"]["xem"], "ket_luan": False, "duyet": False, "tai_pdf": False, "phien_ban": False},
                        "phien_ban": [], "context": ctx, "trang_thai": "CHUA_NOP", "chua_nop": True, "phien_ban_hien_hanh": False, "do_thi": None,
                        "ly_do_trang_thai": "Đợt chưa nộp chính thức (M17) — chưa có phiên bản hồ sơ để kết luận/duyệt/tải PDF",
                        "can_cu": [], "tep_can_cu": [], "tep_can_cu_ly_do": "Chưa nộp — chưa có snapshot tệp căn cứ",
                        "review_refs": [], "coverage": {}, "phat_hien": [], "dong_nt": [], "ket_luan": None, "ket_luan_lich_su": [], "quyet_dinh": None,
                        "pdf": None, "pdf_lich_su": [], "seal": None,
                        "kt": {"trang_thai": "CHUA_CHUYEN", "pending_id": None, "phong_bi_id": None, "phong_bi_hien_hanh": False, "goc_id": None,
                               "phong_bi": [], "ly_do": "Chưa nộp — chưa có chấp thuận/seal/KT chờ xác nhận"},
                        "request": {"trang_thai": "CHO_PDF", "ly_do": "Chưa nộp — chưa có hồ sơ được chấp thuận + PDF đã seal"}}
            v = next(x for x in vs if x["id"] == pb) if pb else vs[-1]
            moi_nhat = v["id"] == vs[-1]["id"]
            g, gsha, l3r = do_thi(xd, c, dt, d, v)
            # tệp căn cứ: CHỈ từ snapshot của ĐÚNG phiên bản đang xem (phiên bản nháp chưa có snapshot → không mượn tệp hiện hành)
            snap = (xd._r1(c, "SELECT snapshot FROM m4.duyet_phien_ban WHERE id = %s::uuid", (v["id"],)) or {}).get("snapshot")
            tep_cc = _tep_can_cu(xd, c, d, snap) if isinstance(snap, dict) else []
            kq = (l3r or {}).get("ket_qua") or {}
            truoc = lich_su_da_duyet(xd, c, d)
            base["lich_su_review_chep"] = lich_su_review_chep(xd, c, d, _dong(kq))
            kls = xd._rn(c, """SELECT id, revision, graph_sha256, l3_run_id, l2_run_id, tien_te, gia_tri_nt, so_xin_thanh_toan, tam_ung, thu_hoi, giu_lai,
                                      xu_ly_phat_hien, thieu, canh_bao, ly_do, quyen, tao_boi AS actor, tao_luc AS luc
                               FROM m4.duyet_ket_luan WHERE phien_ban_id = %s::uuid ORDER BY revision DESC""", (v["id"],))
            kl = kls[0] if kls else None
            if kl:
                kl["dong_nt"] = xd._rn(c, """SELECT row_id, khoi_luong_chap_nhan FROM m4.duyet_ket_luan_dong WHERE ket_luan_id = %s::uuid ORDER BY row_id""",
                                       (kl["id"],))
                kl["khop_co_so"] = kl["graph_sha256"] == gsha
            qd = xd._r1(c, """SELECT id, ket_luan_id, graph_sha256, ly_do, duyet_boi AS actor, duyet_luc AS luc FROM m4.duyet_quyet_dinh
                              WHERE phien_ban_id = %s::uuid""", (v["id"],))
            pdfs = xd._rn(c, """SELECT id, phien_ban_id AS version_id, ten AS name, media_type, raw_sha256 AS sha256, byte_length, ket_luan_id, ket_luan_revision,
                                       graph_sha256, tai_boi AS actor, tai_luc AS luc
                                FROM m4.duyet_pdf WHERE phien_ban_id = %s::uuid ORDER BY tai_luc DESC, id DESC""", (v["id"],))
            seal = xd._r1(c, """SELECT id, phien_ban_id AS version_id, pdf_id, quyet_dinh_id, ket_luan_id, graph_sha256, pdf_sha256, so_lieu, so_lieu_sha256,
                                       tao_boi AS actor, tao_luc AS luc FROM m4.duyet_seal WHERE phien_ban_id = %s::uuid""", (v["id"],))
        ctx.update(version_id=v["id"], revision=(kl or {}).get("revision") or 0, basis_sha256=gsha)
        tt, ly = self._trang_thai(v, moi_nhat, g, gsha, kl, qd, seal)
        # ứng viên PDF của phiên bản đang xem: PDF đã seal; hoặc PDF gắn ĐÚNG kết luận mới nhất khi kết luận đó khớp đồ thị hiện hành. Ứng viên gắn kết
        # luận/đồ thị khác chỉ còn trong pdf_lich_su (gan_hien_hanh=false) — không hiển thị như PDF sẵn sàng seal.
        ap_dung = bool(kl) and kl["khop_co_so"] and moi_nhat and v["trang_thai"] == "DA_NOP" and g["vat_lieu"]["khop"]
        pdfs = [{**p, "gan_hien_hanh": (p["id"] == seal["pdf_id"]) if seal else (ap_dung and p["ket_luan_id"] == kl["id"] and p["graph_sha256"] == gsha)}
                for p in pdfs]
        pdf = next((p for p in pdfs if p["gan_hien_hanh"]), None)
        xl = {x["finding_id"]: x["ly_do"] for x in (kl or {}).get("xu_ly_phat_hien") or []}
        ph = [{**f, "xu_ly": ({"ly_do": xl[f["finding_id"]]} if f["finding_id"] in xl else None)} for f in _phat_hien(kq)]
        chap = {x["row_id"]: x["khoi_luong_chap_nhan"] for x in (kl or {}).get("dong_nt") or []}
        lk = (truoc or {}).get("luy_ke") or {}
        dong = [{**r, "nguon": ((kq.get("provenance") or {}).get("nguon_hang_muc")), "khoi_luong_chap_nhan": chap.get(r["row_id"]),
                 "truoc_da_duyet": lk.get(r["row_id"])} for r in _dong(kq)]
        dong = _gan_lich_su_review_chep(dong, base["lich_su_review_chep"])
        # cong_bo TÁCH khỏi CO/CU/coverage: bộ chọn L3 (_l3_cong_bo) và L2 (_chung_tu_l2) chỉ lấy kết quả x.cong_bo → có run_id = đã công bố (cả CU);
        # không có run_id = chưa có kết quả phù hợp → null (chưa xác định), KHÔNG suy thành "chưa công bố"
        l2tt = g["l2"].get("trang_thai")
        refs = [{"loai": "L3", **{k: g["l3"].get(k) for k in ("trang_thai", "run_id", "ket_qua_sha256", "basis_sha256", "trang_thai_run")},
                 "cong_bo": True if g["l3"].get("run_id") else None, "ly_do": g["l3"].get("ly_do")},
                {"loai": "L2", **g["l2"], "cong_bo": True if g["l2"].get("run_id") else None,
                 "ly_do": (None if l2tt == "CO" else
                           "Căn cứ L2 đã đổi so với lần chạy L2 đã công bố — chạy lại Review L1+L2 rồi Chạy lại L3" if l2tt == "CU" else
                           "Chưa có lần chạy L1+L2 đã công bố có bảng hạng mục — hạng mục theo BOQ hiệu lực (KL đề xuất có thể null)")}]
        tr = truoc or {"trang_thai": "CHUA_CO_NGUON", "ly_do": "Chưa có đợt trước nào cùng HĐ được chấp thuận + seal", "dot": []}
        vl = g["vat_lieu"]
        can_cu = [
            {"loai": "PHIEN_BAN", "trang_thai": v["trang_thai"], "version_id": v["id"], "so": v["so"], "digest": v["digest"],
             "ly_do": None if moi_nhat else "Đã có phiên bản kế tiếp — phiên bản này chỉ còn là lịch sử"},
            {"loai": "VAT_LIEU", "trang_thai": "KHOP" if vl["khop"] else "DOI_SAU_NOP", **vl,
             "ly_do": None if vl["khop"] else "Hồ sơ HĐ/tham số/PL/BOQ khác lúc nộp phiên bản này — cần phiên bản kế tiếp + nộp/kiểm lại"},
            {"loai": "REVIEW_L3", "trang_thai": g["l3"]["trang_thai"], "run_id": g["l3"].get("run_id"), "basis_sha256": g["l3"].get("basis_sha256"),
             "ket_qua_sha256": g["l3"].get("ket_qua_sha256"), "ly_do": g["l3"].get("ly_do")},
            {"loai": "REVIEW_L2", "trang_thai": g["l2"].get("trang_thai") or "CHUA_CO", "run_id": g["l2"].get("run_id"),
             "basis_sha256": g["l2"].get("basis_sha256"), "ket_qua_sha256": g["l2"].get("ket_qua_sha256"), "ly_do": None},
            {"loai": "TRUOC_DA_DUYET", "trang_thai": tr["trang_thai"], "ly_do": tr.get("ly_do"), "dot": tr.get("dot") or []},
            {"loai": "THUE", "trang_thai": "CHO_GOI_M4_03", "ly_do": "Ghi nhận thuế/AP thuộc gói M4-03 — chưa nối"},
            {"loai": "DO_THI", "trang_thai": "HIEN_HANH", "sha256": gsha, "ly_do": None}]
        return {**base, "context": ctx, "trang_thai": tt, "ly_do_trang_thai": ly, "chua_nop": False, "phien_ban_hien_hanh": moi_nhat, "do_thi": g,
                "can_cu": can_cu, "tep_can_cu": tep_cc,
                "tep_can_cu_ly_do": (None if isinstance(snap, dict) else "Phiên bản nháp chưa chụp snapshot — chưa có tệp căn cứ đã nộp (không mượn tệp hiện hành)"),
                "review_refs": refs, "coverage": kq.get("coverage") or {}, "phat_hien": ph, "dong_nt": dong,
                "ket_luan": kl, "ket_luan_lich_su": [{k: x[k] for k in ("id", "revision", "graph_sha256", "quyen", "actor", "luc")} for x in kls],
                "quyet_dinh": None if qd is None else {**qd, "khop_co_so": qd["graph_sha256"] == gsha},
                "pdf": pdf, "pdf_lich_su": pdfs,
                "seal": None if seal is None else {**seal, "thue": (seal.get("so_lieu") or {}).get("thue")},
                "kt": _kt(seal, goc, phong_bi),
                "request": {"trang_thai": "DU_DIEU_KIEN_CHUA_NOI" if seal else "CHO_PDF",
                            "ly_do": ("Phiên bản đã seal duyệt + PDF — chỉ là căn cứ nguồn cho Request nháp; trạng thái/cấu hình/quyền tạo/đối soát xem tại mục Request nháp"
                                      if seal else
                                      "Phiên bản này chưa có chấp thuận + PDF hồ sơ đã duyệt đã seal")}}

    @staticmethod
    def _trang_thai(v, moi_nhat, g, gsha, kl, qd, seal) -> tuple[str, str]:
        if seal:
            return "DA_SEAL", "Đã chấp thuận + PDF hồ sơ đã duyệt — seal bất biến, đã chuyển KT chờ xác nhận"
        if v["trang_thai"] != "DA_NOP":
            return "CAN_KIEM_LAI", "Phiên bản kế tiếp đang nháp — nộp/kiểm lại phiên bản trước khi kết luận"
        if not moi_nhat:
            return "CAN_KIEM_LAI", "Phiên bản cũ đã có bản kế tiếp — chỉ còn là lịch sử"
        if not g["vat_lieu"]["khop"]:
            return "CAN_KIEM_LAI", "Hồ sơ HĐ/tham số/PL/BOQ đã đổi sau khi nộp phiên bản này — tạo phiên bản kế tiếp rồi nộp/kiểm lại"
        if qd:
            if qd["graph_sha256"] != gsha:
                return "CAN_KIEM_LAI", "Căn cứ/review đổi sau khi chấp thuận — chưa seal; tạo phiên bản kế tiếp để kết luận lại"
            return "CHO_PDF", "Đã chấp thuận — chờ PDF hồ sơ thanh toán đã duyệt (chưa có KT chờ xác nhận)"
        if g["l3"]["trang_thai"] != "CO":
            return "CAN_KIEM_LAI", g["l3"].get("ly_do") or "Chưa có Chứng từ L3 khớp căn cứ hiện hành"
        if kl:
            if kl["graph_sha256"] != gsha:
                return "CAN_KIEM_LAI", "Kết luận dựa trên căn cứ/review cũ — kết luận lại trên căn cứ hiện hành"
            if not kl["thieu"]:
                return "CHO_DUYET", "Đã có kết luận đủ số liệu bắt buộc — chờ người có quyền DUYET chấp thuận"
            return "CHO_KET_LUAN", f"Kết luận còn thiếu {len(kl['thieu'])} mục bắt buộc (tiền/khối lượng/xử lý phát hiện)"
        return "CHO_KET_LUAN", "Chưa có kết luận cho phiên bản này"

    def pdf_tai(self, dang_nhap: str, version_id, pdf_id) -> tuple[str, str, bytes]:
        """Tải PDF hồ sơ đã duyệt: quyền HIỆN HÀNH (RLS login ứng dụng + cờ tai_pdf: SOAN/DUYET trên đợt đã nộp — cùng cờ DTO) TRƯỚC kho; hash + độ dài
        kiểm lại; quyền kiểm lại SAU khi đọc blob. Không thấy đợt → 404; thấy nhưng không có quyền tải (XEM/REVIEW) → 403."""
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        pb, pid = _uuid(version_id, "version_id"), _uuid(pdf_id, "pdf_id")

        def kiem(dot):
            with xd._tx(dt):
                r = xd._mot("SELECT m4.duyet_doc_dot(%s::uuid) AS ok, m4.duyet_quyen(%s::uuid) AS q", (dot, dot))
            if not r or not r["ok"]:
                raise DataError("M4_DUYET_KHONG_THAY", "Không thấy PDF hồ sơ của phiên bản (hoặc ngoài phạm vi hiện hành).")
            if not (r["q"] or {}).get("tai_pdf"):
                raise DataError("M4_DUYET_PHAM_VI", "Vai hiện hành không được tải PDF hồ sơ đã duyệt (cần soạn/duyệt trên đợt đã nộp).")
        with xd._tx(dt):
            p = xd._mot("""SELECT id, dot_id, ten, raw_sha256, byte_length FROM m4.duyet_pdf WHERE id = %s::uuid AND phien_ban_id = %s::uuid""", (pid, pb))
        if p is None:
            raise DataError("M4_DUYET_KHONG_THAY", "Không thấy PDF hồ sơ của phiên bản (hoặc ngoài phạm vi hiện hành).")
        kiem(p["dot_id"])
        raw = xd._raw(p["raw_sha256"], p["byte_length"])
        kiem(p["dot_id"])
        return p["ten"], NR.MEDIA_PDF, raw

    # ------------------------------------------------------------------ lệnh
    def _ack(self, dt, r: dict, khoa: str) -> dict:
        kq = r["ket_qua"]
        ack = {"schema": SCHEMA, "hanh_dong": kq["hanh_dong"], "khoa": khoa, "context": kq["context"], "receipt_id": str(r["receipt_id"]),
               "lap_lai": bool(r["lap_lai"]), "trang_thai": kq.get("trang_thai"), "phien_ban_id": kq.get("phien_ban_id"),
               **{k: (None if kq.get(k) is None else str(kq[k])) for k in ID_ACK}}
        for k in ("ket_luan_revision", "phien_ban_so", "parent_id", "digest", "thieu"):
            if k in kq:
                ack[k] = kq[k]
        import psycopg
        try:  # hồ sơ mới — chỉ để hiển thị; ACK đã đủ dữ kiện bền (đọc lỗi không biến thành thất bại lệnh)
            ack["ho_so"] = self._xem(dt, kq["context"]["dot_id"], kq.get("phien_ban_id") or kq["context"]["version_id"])
        except (DataError, psycopg.Error):
            pass
        return ack

    def _lenh(self, dt, lenh: str, khoa: str, yc: dict, dot: str, pb: str, lam) -> dict:
        """Một giao dịch chủ bảng (READ COMMITTED, dưới khóa HĐ → đợt → phiên bản): quyền hiện hành → biên nhận (cùng khóa + đúng body → kết quả cũ +
        receipt_id; khác body → 409) → đồ thị hiện hành → hàm lệnh SQL (CAS revision/đồ thị + hiệu lực + seal dùng chung + biên nhận)."""
        xd = self.xd
        quyen, hanh = LENH[lenh]
        yc_j = json.dumps(yc, ensure_ascii=False)
        self._thay(dt, dot)
        with xd._chua_ro():
            with xd._tx_review(dt) as c:
                c.execute("SELECT m4.duyet_khoa(%s::uuid, %s::uuid, %s)", (dot, pb, quyen))
                r = xd._r1(c, "SELECT m4.duyet_tra(%s, %s, %s::uuid, %s::jsonb) AS r", (khoa, hanh, dot, yc_j))["r"]
                if r is None:
                    d = self._dot(xd, c, dot)
                    v = xd._r1(c, "SELECT id, so, parent_id, trang_thai, digest, revision_ho_so FROM m4.duyet_phien_ban WHERE id = %s::uuid", (pb,))
                    g, gsha, l3r = do_thi(xd, c, dt, d, v)
                    r = lam(c, yc_j, d, v, g, gsha, l3r)
        return self._ack(dt, r, khoa)

    def _chung(self, dang_nhap, dot_id, version_id, revision, expected_basis, khoa, *, ten_pb="version_id"):
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        return dt, _uuid(dot_id, "dot_id"), _uuid(version_id, ten_pb), _rev(revision), _hex(expected_basis), xd._khoa(khoa)

    def ket_luan(self, dang_nhap: str, *, dot_id, version_id, revision, expected_basis, gia_tri_nt, so_xin_thanh_toan, tam_ung, thu_hoi, giu_lai,
                 tien_te, dong_nt, xu_ly_phat_hien, ly_do, khoa) -> dict:
        """Lưu kết luận (REVIEW/DUYET, đợt đã nộp, phiên bản mới nhất chưa chấp thuận). NT (khối lượng chấp nhận theo dòng) và TT (số xin thanh toán)
        độc lập; mọi số là chuỗi thập phân chuẩn hoặc null. Dòng/phát hiện phải thuộc đồ thị hiện hành; dòng không gửi = null (chưa chấp nhận)."""
        dt, dot, pb, rev, exp, khoa = self._chung(dang_nhap, dot_id, version_id, revision, expected_basis, khoa)
        tt = kiem_tien_te(tien_te)
        vnd = tt == "VND"
        so = {"gia_tri_nt": gia_tri_nt, "so_xin_thanh_toan": so_xin_thanh_toan, "tam_ung": tam_ung, "thu_hoi": thu_hoi, "giu_lai": giu_lai}
        so = {k: tien(so[k], k, vnd=vnd) for k in TIEN}
        dn, xl, ly = kiem_dong_nt(dong_nt), kiem_xu_ly(xu_ly_phat_hien), _ly_do(ly_do, bat_buoc=False)
        yc = {"dot_id": dot, "version_id": pb, "revision": rev, "expected_basis": exp, **so, "tien_te": tt, "dong_nt": dn, "xu_ly_phat_hien": xl,
              "ly_do": ly}

        def lam(c, yc_j, d, v, g, gsha, l3r):
            kq = (l3r or {}).get("ket_qua") or {}
            rows = {r["row_id"]: r for r in _dong(kq)}
            ph = {f["finding_id"]: f for f in _phat_hien(kq)}
            # ID chỉ xét khi đồ thị + vật liệu đúng (khác → CSDL trả M4_DUYET_CO_SO_DOI/CHUA_CO_REVIEW/CAN_PHIEN_BAN_MOI chính xác, sau quyền + biên nhận)
            if g["l3"]["trang_thai"] == "CO" and g["vat_lieu"]["khop"] and gsha == exp:
                ngoai = [x["row_id"] for x in dn if x["row_id"] not in rows]
                if ngoai:
                    raise DataError("M4_DUYET_DONG_KHONG_THUOC", f"{len(ngoai)} dòng không thuộc đồ thị hồ sơ hiện hành — tải lại.")
                ngoai = [x["finding_id"] for x in xl if x["finding_id"] not in ph]
                if ngoai:
                    raise DataError("M4_DUYET_PHAT_HIEN_KHONG_THUOC", f"{len(ngoai)} phát hiện không thuộc đồ thị hồ sơ hiện hành — tải lại.")
            chap = {x["row_id"]: x["khoi_luong_chap_nhan"] for x in dn}
            dong = [{**r, "khoi_luong_chap_nhan": chap.get(rid)} for rid, r in sorted(rows.items())]
            thieu = ([{"ma": "TIEN_TE_THIEU"}] if tt is None else []) + [{"ma": "TIEN_THIEU", "truong": k} for k in TIEN if so[k] is None]
            thieu += [{"ma": "KHONG_CO_DONG"}] if not dong else [{"ma": "KL_THIEU", "row_id": r["row_id"]} for r in dong if r["khoi_luong_chap_nhan"] is None]
            da_xl = {x["finding_id"] for x in xl}
            thieu += [{"ma": "PHAT_HIEN_CHUA_XU_LY", "finding_id": f} for f in sorted(ph) if f not in da_xl]
            truoc = lich_su_da_duyet(self.xd, c, d)
            canh_bao = []
            if (truoc or {}).get("trang_thai") != "CO":
                canh_bao.append({"ma": "TRUOC_DA_DUYET_CHUA_DU", "ly_do": (truoc or {}).get("ly_do") or "Chưa có đợt trước nào được duyệt + seal"})
            if g["l2"].get("trang_thai") != "CO":
                canh_bao.append({"ma": "L2_KHONG_HIEN_HANH", "ly_do": "Hạng mục theo BOQ hiệu lực (không có L2 đã công bố khớp căn cứ) — KL đề xuất có thể null"})
            nd = {"tien_te": tt, **so, "dong": dong, "xu_ly_phat_hien": xl, "thieu": thieu, "canh_bao": canh_bao,
                  "l2_run_id": g["l2"].get("run_id") if g["l2"].get("trang_thai") == "CO" else None,
                  "de_xuat_nguon": {"l3_run_id": g["l3"].get("run_id"), "ket_qua_sha256": g["l3"].get("ket_qua_sha256"),
                                    "nguon_hang_muc": (kq.get("provenance") or {}).get("nguon_hang_muc"), "truoc_da_duyet": truoc}}
            return self.xd._r1(c, """SELECT m4.duyet_ghi_ket_luan(%s, %s::jsonb, %s::uuid, %s::uuid, %s::integer, %s, %s, %s::jsonb, %s::jsonb, %s) AS r""",
                               (khoa, yc_j, dot, pb, rev, exp, gsha, canonical_json(g), json.dumps(nd, ensure_ascii=False), ly))["r"]
        return self._lenh(dt, "KET_LUAN", khoa, yc, dot, pb, lam)

    def chap_thuan(self, dang_nhap: str, *, dot_id, version_id, revision, expected_basis, ket_luan_id, ly_do, khoa) -> dict:
        """Chấp thuận (CHỈ vai dự án DUYET): kết luận mới nhất của đúng phiên bản + đồ thị hiện hành + đủ số liệu bắt buộc; rồi seal dùng chung —
        chưa có PDF → CHO_PDF, không KT chờ."""
        dt, dot, pb, rev, exp, khoa = self._chung(dang_nhap, dot_id, version_id, revision, expected_basis, khoa)
        kl, ly = _uuid(ket_luan_id, "ket_luan_id"), _ly_do(ly_do, bat_buoc=True)
        yc = {"dot_id": dot, "version_id": pb, "revision": rev, "expected_basis": exp, "ket_luan_id": kl, "ly_do": ly}

        def lam(c, yc_j, d, v, g, gsha, l3r):
            return self.xd._r1(c, "SELECT m4.duyet_chap_thuan(%s, %s::jsonb, %s::uuid, %s::uuid, %s::integer, %s, %s, %s::uuid, %s) AS r",
                               (khoa, yc_j, dot, pb, rev, exp, gsha, kl, ly))["r"]
        return self._lenh(dt, "CHAP_THUAN", khoa, yc, dot, pb, lam)

    def pdf(self, dang_nhap: str, raw: bytes, *, dot_id, version_id, revision, expected_basis, ten, media_type, khoa) -> dict:
        """PDF hồ sơ thanh toán ĐÃ DUYỆT (không phải PDF HĐ/báo cáo): máy chủ kiểm bytes thật (chữ ký %PDF-, %%EOF cuối tệp, kích thước, tên/đuôi),
        tự tính hash/độ dài; quyền hiện hành + biên nhận kiểm TRƯỚC khi ghi bytes; bytes ghi bất biến m4-raw/<sha> TRƯỚC giao dịch (giữ cả khi CSDL
        lỗi); rồi lệnh SQL gắn phiên bản + seal dùng chung (đã chấp thuận → seal; chưa → giữ PDF, trạng thái theo đồ thị)."""
        xd = self.xd
        dt, dot, pb, rev, exp, khoa = self._chung(dang_nhap, dot_id, version_id, revision, expected_basis, khoa)
        if media_type != NR.MEDIA_PDF:
            raise DataError("M4_TEP_SAI_LOAI", "PDF hồ sơ thanh toán đã duyệt phải khai application/pdf (máy chủ vẫn kiểm nội dung thật).")
        meta = NR.kiem_tep(raw, ten, NR.MEDIA_PDF, "HO_SO_DOT")
        raw = bytes(raw)
        if b"%%EOF" not in raw[-1024:]:
            raise DataError("M4_TEP_MEDIA_KHONG_KHOP", "PDF không có dấu kết thúc %%EOF (tệp bị cắt/hỏng) — không lưu.")
        yc = {"dot_id": dot, "version_id": pb, "revision": rev, "expected_basis": exp, "ten": meta["ten"], "media_type": meta["media"],
              "sha256": meta["sha256"], "byte_length": meta["byte_length"], "vai": VAI_PDF}
        yc_j = json.dumps(yc, ensure_ascii=False)
        self._thay(dt, dot)
        with xd._chua_ro():
            with xd._tx_review(dt) as c:  # quyền hiện hành + replay TRƯỚC khi ghi bytes
                c.execute("SELECT m4.duyet_khoa(%s::uuid, %s::uuid, 'PDF')", (dot, pb))
                r = xd._r1(c, "SELECT m4.duyet_tra(%s, 'DUYET_PDF', %s::uuid, %s::jsonb) AS r", (khoa, dot, yc_j))["r"]
        if r is not None:
            return self._ack(dt, r, khoa)
        write_immutable(xd.root / "m4-raw" / meta["sha256"], raw)

        def lam(c, yc_j_, d, v, g, gsha, l3r):
            return self.xd._r1(c, "SELECT m4.duyet_ghi_pdf(%s, %s::jsonb, %s::uuid, %s::uuid, %s::integer, %s, %s, %s, %s::bigint, %s) AS r",
                               (khoa, yc_j_, dot, pb, rev, exp, gsha, meta["sha256"], meta["byte_length"], meta["ten"]))["r"]
        return self._lenh(dt, "PDF", khoa, yc, dot, pb, lam)

    def phien_ban(self, dang_nhap: str, *, dot_id, parent_version_id, revision, expected_basis, ly_do, khoa) -> dict:
        """Phiên bản kế tiếp (NHÁP) của cùng hồ sơ đợt — CHỈ SOAN; cha = bản mới nhất đã nộp; không tạo chấp thuận/seal/KT/AP/Request; lịch sử giữ nguyên."""
        dt, dot, pb, rev, exp, khoa = self._chung(dang_nhap, dot_id, parent_version_id, revision, expected_basis, khoa, ten_pb="parent_version_id")
        ly = _ly_do(ly_do, bat_buoc=True)
        yc = {"dot_id": dot, "parent_version_id": pb, "revision": rev, "expected_basis": exp, "ly_do": ly}

        def lam(c, yc_j, d, v, g, gsha, l3r):
            return self.xd._r1(c, "SELECT m4.duyet_tao_phien_ban(%s, %s::jsonb, %s::uuid, %s::uuid, %s::integer, %s, %s, %s) AS r",
                               (khoa, yc_j, dot, pb, rev, exp, gsha, ly))["r"]
        return self._lenh(dt, "PHIEN_BAN", khoa, yc, dot, pb, lam)

    def phien_ban_nop(self, dang_nhap: str, *, dot_id, version_id, revision, expected_basis, khoa) -> dict:
        """Nộp/kiểm lại phiên bản nháp — CHỈ SOAN; gate nộp thật (m4.thieu) + L3 đã công bố khớp căn cứ; snapshot cùng mẫu m4.nop (m4.nop/đợt không đổi)."""
        dt, dot, pb, rev, exp, khoa = self._chung(dang_nhap, dot_id, version_id, revision, expected_basis, khoa)
        yc = {"dot_id": dot, "version_id": pb, "revision": rev, "expected_basis": exp}

        def lam(c, yc_j, d, v, g, gsha, l3r):
            return self.xd._r1(c, "SELECT m4.duyet_nop_phien_ban(%s, %s::jsonb, %s::uuid, %s::uuid, %s::integer, %s, %s, %s::jsonb) AS r",
                               (khoa, yc_j, dot, pb, rev, exp, gsha, canonical_json(g)))["r"]
        return self._lenh(dt, "PHIEN_BAN_NOP", khoa, yc, dot, pb, lam)
