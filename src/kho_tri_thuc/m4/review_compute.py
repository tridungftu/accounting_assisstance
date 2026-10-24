"""M4-02A — tính Review L1/L2 trong TIẾN TRÌNH CON do máy chủ sở hữu (không DSN/PG/credential; chỉ đầu vào đã giữ lại + pin).

Chạy: `python -m kho_tri_thuc.m4.review_compute <thư mục lần chạy>` — đọc `vao.json` (basis đã chụp từ PG + đường dẫn bản XLSX content-addressed),
ghi `ket_qua.json` + báo cáo XLSX vào đúng thư mục đó (ghi một lần, không ghi đè, không xóa). Máy chủ đọc kết quả rồi công bố qua CAS.

Tái sử dụng NGUYÊN thuật toán/ngưỡng/ghép vendor qua bộ nạp ghim (`nguon_review._m`), không viết engine soát số mới:
- L1: `toan_ven.KiemTra(path, o_dich).chay()` (K1,K2,K3,K4,K5,K7,K6,K8) → `may_chu.nghiep_vu._lop1` (findings/bang_k/cay) → báo cáo `toan_ven.ghi`.
- L2: `csdl_hop_dong.tinh_doi_chieu_dot` trên projection :memory: (`nguon_review.projection_l2`) → `nghiep_vu._lop2`, `bang_kiem_lop2`, `_lop2b`
  (cùng trình tự `kiem_tra_dot` của nguồn nhưng KHÔNG gọi `cs.kiem_dot` — vốn ghi nhật ký + commit). Báo cáo L2 = builder của `kiem_dot` chuyển
  thành hàm thuần đọc kết quả đã tính + projection chỉ-đọc, ghi tệp mới; không nhật ký/commit, không đọc lại PG.
M4-02B: `vao.json` có `che_do == 'L3'` → nhánh Chứng từ L3 (`m4/chung_tu_adapter.tinh`) trong CÙNG tiến trình con/guard/ghi kết quả (không worker/queue thứ hai).
Companion coverage (bắt buộc §10): trạng thái từng quy tắc CHECKED / NOT_ELIGIBLE / LIMITED / NOT_AVAILABLE / INCOMPLETE / ERROR / KHONG_AP_DUNG dựa
trên căn cứ đầu vào + cấu trúc đầu ra thật (không chỉ số phát hiện). Finding gốc giữ nguyên; nhãn hiển thị tách khỏi kết quả nguồn. Ước tính tiền
của nguồn (float/tolerance) ghi đúng là ước tính, không phải số thanh toán được chấp nhận.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import traceback
from collections import Counter
from pathlib import Path

THU_TU = {"ERROR": 0, "INCOMPLETE": 1, "NOT_AVAILABLE": 2, "LIMITED": 3, "NOT_ELIGIBLE": 4, "KHONG_AP_DUNG": 5, "CHECKED": 6}
NHAN = {"CHECKED": None, "NOT_ELIGIBLE": "Không đủ điều kiện xét", "LIMITED": "Kiểm có giới hạn", "NOT_AVAILABLE": "Không có số liệu",
        "INCOMPLETE": "Chưa đủ căn cứ — chưa kiểm được", "ERROR": "Lỗi kiểm tra", "KHONG_AP_DUNG": "Không áp dụng (có căn cứ)"}
DAT_DU = ("CHECKED", "NOT_ELIGIBLE", "KHONG_AP_DUNG")
MA_L1 = ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8")
MA_L2 = ("GT", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8")
NGUONG = {"K2_toi_thieu_cong_thuc": 10, "K2_ty_le_mau_chinh": 0.7, "K3_toi_thieu_lien_ket_cap_sheet": 20, "K7_do_sau_toi_da": 14,
          "tim_so_tong_hop": "80 dòng × 12 cột, ≤6 ô bên phải nhãn, chỉ nhận |giá trị| > 1"}
# dòng bảng kiểm L2 (theo chuỗi `ten` nguồn) → (mã, phụ thuộc căn cứ, khóa số tổng hợp liên quan)
DONG_L2 = (
    ("GT hợp đồng ghi trong hồ sơ = GT HĐ hiệu lực", "GT", ("GT", "GOM_VAT", "VAT_NEU_CHUA_GOM", "PL_GT"), ("gt_hd",)),
    ("GT lũy kế thực hiện đến hết kỳ này ≤ GT HĐ hiệu lực", "GT", ("GT", "GOM_VAT", "VAT_NEU_CHUA_GOM", "PL_GT"), ("gt_lk",)),
    ("GT lũy kế hết kỳ trước + GT thực hiện kỳ này", "GT", (), ("gt_lk", "gt_lk_kt", "gt_kn")),
    ("GT lũy kế hết kỳ trước = lũy kế đợt trước đã duyệt", "GT", ("TRUOC",), ("gt_lk_kt",)),
    ("GT thực hiện kỳ này = Σ(KL kỳ này × đơn giá BOQ hiệu lực)", "GT", ("VAT", "BOQ", "PL_BOQ"), ("gt_kn",)),
    ("Lũy kế thanh toán (các đợt đã nạp CSDL + đề nghị kỳ này)", "GT", ("GT", "GOM_VAT", "VAT_NEU_CHUA_GOM", "PL_GT", "TRUOC"), ("tt_ky_nay",)),
    ("Hạng mục trong hồ sơ có trong BOQ hiệu lực", "B3", ("BOQ", "PL_BOQ"), ()),
    ("Đơn giá trong hồ sơ = đơn giá BOQ hiệu lực", "B2", ("BOQ", "PL_BOQ"), ()),
    ("KL hợp đồng ghi trong hồ sơ = KL BOQ hiệu lực", "B4", ("BOQ", "PL_BOQ"), ()),
    ("KL lũy kế đến hết kỳ này ≤ KL BOQ hiệu lực", "B1", ("BOQ", "PL_BOQ"), ()),
    ("KL kỳ trước = ", "B5", ("TRUOC",), ()),
    ("Hạng mục BOQ hiệu lực có trong hồ sơ", "B6", ("BOQ", "PL_BOQ"), ()),
    ("Đề nghị thanh toán kỳ này = tỷ lệ thanh toán HĐ (TT-20)", "B8", ("TT-20", "TT-10", "TT-11", "PL_THAM_SO"), ("tt_ky_nay", "gt_kn", "thu_hoi_tu")),
    ("Đề nghị kỳ này = GT thực hiện kỳ này − giữ lại − thu hồi tạm ứng", "B8", (), ("tt_ky_nay", "gt_kn", "giu_lai", "thu_hoi_tu")),
    ("Giữ lại = tỷ lệ giữ lại HĐ (TT-21)", "B8", ("TT-21", "PL_THAM_SO"), ("giu_lai", "gt_kn")),
    ("Thu hồi tạm ứng so với tạm ứng HĐ", "B8", ("TT-10", "TT-11", "PL_THAM_SO"), ("thu_hoi_tu", "gt_kn")),
    ("Hằng số và ô tham số gõ tay trên đường tính số đề nghị", "B7", ("VAT", "TT-20", "TT-21", "TT-10", "PL_THAM_SO", "CAY_K7"), ()),
)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _huu_han(o):
    """NaN/±inf (có thể đến từ ô Excel/float nguồn) → None khi tuần tự hóa: PG jsonb và canonical_json không nhận số không hữu hạn.
    Chỉ đổi biểu diễn của giá trị không biểu diễn được, không điền số."""
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    if isinstance(o, dict):
        return {k: _huu_han(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_huu_han(v) for v in o]
    return o


def _json(o):
    return _huu_han(json.loads(json.dumps(o, ensure_ascii=False, default=str)))


def _bytes_json(o) -> bytes:
    return json.dumps(_huu_han(o), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")


def _xau_nhat(ds):
    return min(ds, key=lambda t: THU_TU[t]) if ds else "CHECKED"


# ================================================================================================== phụ thuộc căn cứ (L2 preflight)
def phu_thuoc(co_so: dict) -> dict:
    """Căn cứ đầu vào L2 có/không theo TRẠNG THÁI typed (CO_GIA_TRI / KHONG_AP_DUNG / KHONG_QUY_DINH / CHUA_CO), không tự bù 0 hay chữ.
    Mỗi mục: {ok, ly_do}. Dùng cả ở máy chủ (hiện trước khi chạy) và trong worker (coverage)."""
    from . import nguon_review as NR
    cs = NR._m("csdl_hop_dong")
    out = {}

    def dat(k, ok, ly_do):
        out[k] = {"ok": bool(ok), "ly_do": ly_do}
    if co_so.get("che_do") != "L1_L2" or not co_so.get("hop_dong"):
        return out
    hd, dot = co_so["hop_dong"], co_so.get("dot") or {}
    ts = {t["ma"]: t for t in co_so.get("tham_so") or []}
    tt = lambda ma: (ts.get(ma) or {}).get("trang_thai", "CHUA_CO")  # noqa: E731
    gt = lambda ma: (ts.get(ma) or {}).get("gia_tri")  # noqa: E731
    ngay = (str(dot.get("ngay_nghiem_thu"))[:10] if dot.get("ngay_nghiem_thu") else None)
    dat("NGAY", ngay is not None, "Đợt có ngày nghiệm thu" if ngay else "Đợt chưa có ngày nghiệm thu — không xác định được PL/BOQ hiệu lực")
    xn = co_so.get("xac_nhan") or {}
    dat("XAC_NHAN", bool(xn.get("con_hieu_luc")), "Bộ tham số đã xác nhận, còn hiệu lực" if xn.get("con_hieu_luc")
        else "Bộ tham số chưa xác nhận hoặc đã đổi sau lần xác nhận")
    so = cs.tien(gt("TT-02")) if tt("TT-02") == "CO_GIA_TRI" else None
    dat("GT", so is not None, f"TT-02 {tt('TT-02')}" + ("" if so is not None else " — chưa có giá trị HĐ đọc được (không thay bằng 0)"))
    dat("GOM_VAT", tt("TT-03") == "CO_GIA_TRI", f"TT-03 {tt('TT-03')}")
    vat = cs.ty_le(gt("TT-04")) if tt("TT-04") == "CO_GIA_TRI" else None
    dat("VAT", vat is not None, f"TT-04 {tt('TT-04')}" + ("" if vat is not None else " — chưa có thuế suất (nguồn sẽ coi là 0; không chấp nhận)"))
    from_gom = str(gt("TT-03") or "")
    chua_gom = tt("TT-03") == "CO_GIA_TRI" and re.search(r"(?i)\b(không|khong|chưa|chua)\b", from_gom) is not None
    dat("VAT_NEU_CHUA_GOM", (not chua_gom) or vat is not None, "GT chưa gồm VAT cần TT-04" if chua_gom else "GT đã gồm VAT (theo TT-03) hoặc chưa rõ")
    for ma in ("TT-20", "TT-21", "TT-10"):
        dat(ma, tt(ma) in ("CO_GIA_TRI", "KHONG_AP_DUNG", "KHONG_QUY_DINH"), f"{ma} {tt(ma)}")
        out[ma]["trang_thai_tham_so"] = tt(ma)
        # FIX01 R1: CHỈ khai tường minh KHONG_AP_DUNG (đã xác nhận, có trích dẫn/lý do) mới là căn cứ "không áp dụng". KHONG_QUY_DINH = HĐ không
        # quy định → KHÔNG suy thành "không giữ lại/không tạm ứng" hay số 0; số thô vắng/NULL vẫn INCOMPLETE.
        out[ma]["tuong_minh_khong_ap_dung"] = tt(ma) == "KHONG_AP_DUNG" and bool(xn.get("con_hieu_luc"))
        if tt(ma) == "KHONG_QUY_DINH":
            out[ma]["ly_do"] += " — HĐ không quy định: không phải căn cứ 'không áp dụng', không suy 0"
    can_tt11 = tt("TT-10") == "CO_GIA_TRI"
    dat("TT-11", (not can_tt11) or tt("TT-11") in ("CO_GIA_TRI", "KHONG_AP_DUNG", "KHONG_QUY_DINH"),
        f"TT-11 {tt('TT-11')}" + (" (HĐ có tạm ứng — cần điều kiện thu hồi)" if can_tt11 else ""))
    khai = hd.get("trang_thai_pl")
    khai_ok = khai in ("KHONG_CO", "CO_DU")
    pls = [p for p in co_so.get("phu_luc") or [] if p["trang_thai"] == "DA_KY" and ngay and str(p["ngay_hieu_luc"])[:10] <= ngay]
    dat("PL_KHAI", khai_ok, f"Khai phụ lục: {khai}")
    dat("PL_GT", khai_ok and not pls, ("Không có phụ lục áp dụng" if not pls else
        f"{len(pls)} phụ lục áp dụng nhưng GT tăng/giảm theo PL chưa có kiểu ở M17 — chưa tính được GT hiệu lực") if khai_ok else f"Khai phụ lục {khai}")
    dat("PL_THAM_SO", khai_ok and not pls, ("Không có phụ lục áp dụng" if not pls else
        f"{len(pls)} phụ lục áp dụng nhưng thay đổi tham số theo PL chưa có kiểu ở M17") if khai_ok else f"Khai phụ lục {khai}")
    boq = co_so.get("boq") or []
    goc = next((b for b in boq if b["phu_luc_id"] is None), None)
    dat("BOQ", bool(goc and goc["trang_thai"] == "DA_MAP"), "BOQ gốc đã map" if goc and goc["trang_thai"] == "DA_MAP" else "Chưa có BOQ gốc hợp lệ")
    thieu_pl = [p["so_pl"] for p in pls if p["doi_boq"] and not any(b["phu_luc_id"] == p["id"] and b["trang_thai"] == "DA_MAP" for b in boq)]
    co_doi = [p["so_pl"] for p in pls if p["doi_boq"]]
    dat("PL_BOQ", khai_ok and not thieu_pl and not co_doi,
        ("Không có phụ lục đổi BOQ áp dụng" if not co_doi else
         (f"PL đổi BOQ chưa nhập BOQ hợp lệ: {', '.join(thieu_pl)}" if thieu_pl else
          f"PL {', '.join(co_doi)} đổi BOQ: THEM/THAY đã dùng, nhưng thao tác BO chưa có kiểu ở M17 — chưa đủ căn cứ")) if khai_ok else f"Khai phụ lục {khai}")
    # correction: số thứ tự đợt (vd 1) KHÔNG chứng minh "không có đợt trước"; provider lịch sử đợt đã được reviewer duyệt chưa nối ở gói này
    # → luôn INCOMPLETE (không tự tạo approval/provider, không coi vắng là 0)
    truoc = co_so.get("truoc_da_duyet") or {}
    dat("TRUOC", False, truoc.get("ly_do") or "Chưa có nguồn lịch sử đợt trước đã được reviewer duyệt (DA_NOP chỉ là đã nộp) — "
                                            "không suy từ số đợt hay vắng dữ liệu, không coi vắng là 0")
    out["TRUOC"]["so_dot_khai"] = dot.get("so_dot")
    return out


# ================================================================================================== L1 coverage
def coverage_l1(kt, tv, o_dich) -> dict:
    kq, ph = kt.kq, kt.ph
    loi = {x["kt"] for x in ph if str(x.get("mo_ta", "")).startswith("Kiểm tra lỗi:")}
    c = {}

    def dat(k, tt, ly_do, **kw):
        c[k] = {"trang_thai": "ERROR" if k in loi else tt, "ly_do": ("Nguồn bắt lỗi: " + next(x["mo_ta"] for x in ph if x["kt"] == k
                                                                  and str(x["mo_ta"]).startswith("Kiểm tra lỗi:"))) if k in loi else ly_do, **kw}
    sheets = kq.get("sheet")
    if sheets is None:
        dat("K1", "ERROR", "Không đọc được tổng quan workbook")
    else:
        n_ct, n_chua = sum(r[4] for r in sheets), sum(r[8] for r in sheets)
        if n_ct and n_chua == n_ct:
            dat("K1", "NOT_AVAILABLE", f"Toàn bộ {n_ct} công thức không có giá trị lưu (cache) — không tự tính lại", cong_thuc=n_ct, khong_cache=n_chua)
        elif n_chua:
            dat("K1", "LIMITED", f"{n_chua}/{n_ct} công thức không có giá trị lưu (cache) — giá trị đọc có thể sai", cong_thuc=n_ct, khong_cache=n_chua)
        else:
            dat("K1", "CHECKED", f"{len(sheets)} sheet, {n_ct} công thức có giá trị lưu", cong_thuc=n_ct, khong_cache=0)
    cot = kq.get("cot")
    if cot is None:
        dat("K2", "ERROR", "Không có bản đồ công thức (K1 lỗi)")
    else:
        # RC02: đúng điều kiện nguồn (toan_ven.py:349 `n < 10 or ty < 0.7` với ty = n / len(ds_) CHƯA làm tròn) — tính từ SỐ ĐẾM thật
        # (cột 5 = len(ds_), cột 6 = n), không dùng cột tỷ lệ hiển thị đã round(…, 3)
        du = [r for r in cot if r[5] >= NGUONG["K2_toi_thieu_cong_thuc"] and r[4] and r[5] / r[4] >= NGUONG["K2_ty_le_mau_chinh"]]
        dat("K2", "CHECKED" if du else "NOT_ELIGIBLE", f"{len(du)} cột có mẫu chính (≥10 công thức, ≥70%) trên {len(cot)} cột ≥10 công thức"
            if du else f"Không cột nào đủ ngưỡng nguồn (≥10 công thức không tính tổng, mẫu chính ≥70%); {len(cot)} cột ≥10 công thức", cot_du=len(du))
    if not hasattr(kt, "_ct"):
        dat("K3", "ERROR", "Không có danh sách công thức")
    else:
        cap = Counter()
        for (sh, _r, _c), f in kt._ct.items():
            for x in tv.tach_tham_chieu(f, sh):
                if x["sh"] != sh and x["ngoai"] is None and x["r1"] == x["r2"]:
                    cap[(sh, x["sh"])] += 1
        lon = max(cap.values(), default=0)
        dat("K3", "CHECKED" if lon >= NGUONG["K3_toi_thieu_lien_ket_cap_sheet"] else "NOT_ELIGIBLE",
            f"Cặp sheet nhiều liên kết dòng nhất: {lon} (ngưỡng nguồn ≥20)", lien_ket_lon_nhat=lon)
    dat("K4", "CHECKED" if "an" in kq else "ERROR", f"{len(kq.get('an') or [])} sheet ẩn" if "an" in kq else "Không có kết quả sheet ẩn")
    dat("K5", "CHECKED" if "chu" in kq else "ERROR", f"{len(kq.get('chu') or [])} ô số dạng chữ" if "chu" in kq else "Không có kết quả K5")
    cay = kq.get("cay") or []
    dich = kq.get("dich")
    nguon_dich = "NGUOI_CHON" if o_dich else ("TU_DONG" if dich else None)
    if dich is None:
        dat("K7", "INCOMPLETE", "Không có ô đích số đề nghị (không tự tìm được, chưa chọn) — cây truy vết rỗng, chưa kiểm được", dich=None, nguon_dich=None)
    elif any("dừng vì quá sâu" in str(r[1]) for r in cay):
        dat("K7", "LIMITED", f"Cây từ {dich} bị cắt ở độ sâu nguồn {NGUONG['K7_do_sau_toi_da']}; dải nhiều ô chỉ phân rã ô đại diện",
            dich=dich, nguon_dich=nguon_dich, so_nut=len(cay))
    else:
        dat("K7", "CHECKED", f"Cây truy vết từ {dich} ({len(cay)} nút; dải nhiều ô phân rã ô đại diện theo nguồn)", dich=dich, nguon_dich=nguon_dich,
            so_nut=len(cay))
    if "nhung" not in kq:
        dat("K6", "ERROR", "Không có kết quả K6")
    elif c["K7"]["trang_thai"] not in ("CHECKED", "LIMITED"):
        dat("K6", "LIMITED", "Không có cây truy vết: hằng số chỉ được liệt kê, không xác định được hằng số trên đường tính số đề nghị")
    else:
        dat("K6", "CHECKED", f"{len(kq['nhung'])} hằng số gõ cứng được xét")
    if "bang_sh" not in kq:
        dat("K8", "INCOMPLETE", "Không nhận được bảng chi tiết KL × đơn giá — nguồn KL từng hạng mục chưa kiểm được")
    elif not kq.get("nguon"):
        dat("K8", "NOT_ELIGIBLE", f"Bảng {kq['bang_sh']} không có hạng mục có ĐVT")
    else:
        dat("K8", "CHECKED", f"{len(kq['nguon'])} hạng mục ở bảng {kq['bang_sh']}")
    return {k: c[k] for k in MA_L1}


def _gan_bang_k(bang_k, cov):
    for r in bang_k:
        cv = cov.get(r["code"]) or {"trang_thai": "ERROR", "ly_do": "Không có coverage"}
        r["ket_qua_nguon"] = r["ket_qua"]
        r["trang_thai_kiem"] = cv["trang_thai"]
        r["ly_do_kiem"] = cv["ly_do"]
        r["ket_qua_hien_thi"] = r["ket_qua"] if cv["trang_thai"] == "CHECKED" else NHAN[cv["trang_thai"]]
    return bang_k


# ================================================================================================== L2 helpers
def trang_thai_tho(wv, tong, mh) -> dict:
    """§10.4 + RC01: trạng thái THÔ của từng số tổng hợp theo nhãn nguồn (`master_hd.LABELS`), quan sát trong ĐÚNG phạm vi của
    `tim_so_tong_hop` (sheet hiện, 80 dòng × 12 cột, ≤6 ô bên phải nhãn) mà KHÔNG đổi ngưỡng nguồn:
      RECOGNIZED      — parser nguồn đã nhận (có trong `tong`, |v|>1) — giữ ô/giá trị của nguồn;
      OBSERVED_ZERO   — nhãn có, ô số bên phải = 0 vật lý (parser nguồn không nhận);
      NOT_RECOGNIZED  — nhãn có, số 0<|v|≤1 (parser nguồn không nhận);
      RAW_NULL        — nhãn có, các ô bên phải trống/không phải số;
      MISSING         — không thấy nhãn trong phạm vi quét.
    Không tự điền số, không suy vắng thành 0."""
    out = {k: {"trang_thai": "RECOGNIZED", "o": v.get("o"), "gia_tri_tho": v.get("gia_tri")} for k, v in tong.items()}
    for ws in wv.worksheets:
        if ws.sheet_state != "visible":
            continue
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 80), max_col=min(ws.max_column, 12)):
            for cell in row:
                t = mh.bo_dau(cell.value) if isinstance(cell.value, str) else ""
                if not t or len(t) > 140:
                    continue
                for k, pat in mh.LABELS.items():
                    if k in tong or (out.get(k) or {}).get("trang_thai") in ("OBSERVED_ZERO", "NOT_RECOGNIZED") \
                            or not re.search(pat, t) or (k == "gt_hd" and "luy ke" in t):
                        continue
                    thay = None
                    for c in range(cell.column + 1, min(ws.max_column, cell.column + 6) + 1):
                        v = ws.cell(cell.row, c).value
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            thay = {"trang_thai": "OBSERVED_ZERO" if v == 0 else "NOT_RECOGNIZED", "o": f"{ws.title}!{ws.cell(cell.row, c).coordinate}",
                                    "gia_tri_tho": v, "nhan": str(cell.value)[:80]}
                            break
                    out[k] = thay or {"trang_thai": "RAW_NULL", "o": f"{ws.title}!{cell.coordinate}", "gia_tri_tho": None, "nhan": str(cell.value)[:80]}
    for k in mh.LABELS:
        out.setdefault(k, {"trang_thai": "MISSING", "o": None, "gia_tri_tho": None})
    return out


# số tổng hợp vắng mà HĐ khai TƯỜNG MINH không áp dụng tham số tương ứng → có căn cứ (khác CHUA_CO/vắng)
KHOA_KHONG_AP_DUNG = {"giu_lai": ("TT-21",), "thu_hoi_tu": ("TT-10",)}


def coverage_l2(bang_l2, pt, cov_l1, khong_nd, l2_loi=None) -> tuple[list, dict]:
    """Gắn companion cho TỪNG dòng bảng kiểm L2 (giữ ket_qua nguồn) và tổng hợp theo mã GT/B1–B8."""
    theo_ma = {m: [] for m in MA_L2}
    if l2_loi:
        for m in MA_L2:
            theo_ma[m].append(l2_loi)
    khong_nd = khong_nd or {}
    cay_ok = (cov_l1.get("K7") or {}).get("trang_thai") in ("CHECKED", "LIMITED")
    for r in bang_l2:
        spec = next((s for s in DONG_L2 if str(r.get("ten", "")).startswith(s[0])), None)
        r["ket_qua_nguon"] = r.get("ket_qua")
        if spec is None:
            tt, ly = "LIMITED", "Dòng nguồn chưa có ánh xạ phụ thuộc trong gói này — xem kết quả nguồn"
            ma = "GT" if r.get("nhom", "").startswith("Giá trị") else "B8"
        else:
            _, ma, can, khoa_so = spec
            thieu = []
            for d in can:
                if d == "CAY_K7":
                    if not cay_ok:
                        thieu.append("Cây truy vết K7 rỗng/chưa kiểm được")
                    continue
                x = pt.get(d)
                if x is None or not x["ok"]:
                    thieu.append((x or {}).get("ly_do") or d)
            # RC01: trạng thái THÔ của từng số tổng hợp mà dòng dùng — RECOGNIZED (parser nguồn nhận) / OBSERVED_ZERO / NOT_RECOGNIZED (|v|≤1 khác 0)
            # / RAW_NULL (nhãn có, ô bên phải trống) / MISSING (không thấy nhãn). Thiếu căn cứ không được coverage tốt hơn 0 vật lý quan sát được.
            tho = {kk: (khong_nd.get(kk) or {"trang_thai": "MISSING"}) for kk in khoa_so}
            xau_tho, ly_tho = "CHECKED", []
            for kk, x in tho.items():
                st = x["trang_thai"]
                if st == "RECOGNIZED":
                    continue
                if st in ("MISSING", "RAW_NULL") and kk in KHOA_KHONG_AP_DUNG and any(
                        (pt.get(p) or {}).get("tuong_minh_khong_ap_dung") for p in KHOA_KHONG_AP_DUNG[kk]):
                    xau_tho = _xau_nhat([xau_tho, "KHONG_AP_DUNG"])
                    ly_tho.append(f"{kk}: không có dòng trong hồ sơ, HĐ khai tường minh không áp dụng ({', '.join(KHOA_KHONG_AP_DUNG[kk])})")
                    continue
                if st in ("OBSERVED_ZERO", "NOT_RECOGNIZED"):
                    xau_tho = _xau_nhat([xau_tho, "LIMITED"])
                    ly_tho.append(f"{kk}: {st} tại {x.get('o')} = {x.get('gia_tri_tho')} (parser nguồn chỉ nhận |v|>1)")
                else:
                    xau_tho = _xau_nhat([xau_tho, "INCOMPLETE"])
                    ly_tho.append(f"{kk}: {st}" + (f" tại {x.get('o')}" if x.get("o") else "") + " — thiếu số trong hồ sơ, không thay bằng 0")
            if r.get("ket_qua") == "Không có số liệu":
                tt, ly = ("INCOMPLETE" if xau_tho == "INCOMPLETE" else "NOT_AVAILABLE"), ("; ".join(ly_tho) or "Không đọc được số tương ứng trong hồ sơ")
            elif thieu:
                tt, ly = "INCOMPLETE", "; ".join(dict.fromkeys(thieu + ly_tho))
            else:
                tt, ly = xau_tho, "; ".join(ly_tho)
                if "CAY_K7" in can and (cov_l1.get("K7") or {}).get("trang_thai") == "LIMITED" and THU_TU[tt] > THU_TU["LIMITED"]:
                    tt, ly = "LIMITED", "; ".join(x for x in (ly, "Cây K7 bị cắt độ sâu — giới hạn của K7 giữ cho B7") if x)
                if tt == "KHONG_AP_DUNG" and r.get("ket_qua") not in ("Không áp dụng", "Đạt"):
                    tt = "CHECKED"
        r["trang_thai_kiem"], r["ly_do_kiem"], r["ma_kiem"] = tt, ly, ma
        r["ket_qua_hien_thi"] = r.get("ket_qua") if tt == "CHECKED" else (NHAN[tt] + (f" · nguồn: {r.get('ket_qua')}" if tt in ("LIMITED", "INCOMPLETE") else ""))
        theo_ma[ma].append(tt)
    tong = {}
    for m in MA_L2:
        ds = theo_ma[m]
        tt = _xau_nhat(ds) if ds else "INCOMPLETE"
        ly = "; ".join(dict.fromkeys(r["ly_do_kiem"] for r in bang_l2 if r.get("ma_kiem") == m and r["trang_thai_kiem"] == tt and r["ly_do_kiem"]))
        if not ds:
            ly = "Nguồn không tạo bước kiểm cho mã này ở lần chạy (không có cột/hạng mục tương ứng)"
        if l2_loi and tt == l2_loi:
            ly = ly or "L2 không chạy được"
        tong[m] = {"trang_thai": tt, "ly_do": ly}
    return bang_l2, tong


# ================================================================================================== báo cáo
def _them_pham_vi(nguon: Path, dich: Path, dong: list, tieu_de: str) -> None:
    """Báo cáo cuối = báo cáo nguồn + sheet 'Pham vi kiem' (cùng coverage đã lưu/hiển thị). Tệp nguồn giữ nguyên bên cạnh."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.load_workbook(str(nguon))
    ws = wb.create_sheet("Pham vi kiem", 0)
    ws.cell(1, 1, tieu_de).font = Font(name="Arial", size=12, bold=True)
    ws.cell(2, 1, "Trạng thái kiểm theo căn cứ đầu vào + cấu trúc đầu ra thật. 'Chưa đủ căn cứ'/'Không có số liệu' KHÔNG phải Đạt. "
                  "Ảnh hưởng tiền là ước tính của thuật toán nguồn, không phải số thanh toán được chấp nhận.").font = Font(name="Arial", size=9, italic=True)
    hdr = ["Mã", "Nội dung", "Trạng thái kiểm", "Kết quả nguồn", "Hiển thị", "Lý do / phạm vi"]
    for j, h in enumerate(hdr, 1):
        c = ws.cell(4, j, h)
        c.font, c.fill = Font(name="Arial", bold=True, color="FFFFFF", size=10), PatternFill("solid", fgColor="1F4A7A")
    to = {"INCOMPLETE": "FFF2CC", "ERROR": "F8D7D3", "NOT_AVAILABLE": "EEEEEE", "LIMITED": "FFF2CC"}
    for i, d in enumerate(dong, 5):
        for j, v in enumerate(d, 1):
            c = ws.cell(i, j, v)
            if isinstance(v, str) and v.startswith("="):
                c.data_type = "s"
        if d[2] in to:
            for j in range(1, len(d) + 1):
                ws.cell(i, j).fill = PatternFill("solid", fgColor=to[d[2]])
    for j, w in enumerate([8, 60, 18, 18, 30, 90], 1):
        ws.column_dimensions[chr(64 + j)].width = w
    wb.save(str(dich))


def bao_cao_lop2(con, k, path: Path, out: Path, cs, mh) -> None:
    """Builder báo cáo L2 của nguồn (`csdl_hop_dong.kiem_dot` phần ghi workbook) chuyển thành hàm thuần: đọc kết quả `tinh_doi_chieu_dot` đã tính +
    projection chỉ-đọc (SELECT), ghi tệp MỚI. Không gọi lại tinh, không `ghi_nhat_ky`, không commit."""
    import openpyxl
    put, header = mh.put, mh.header
    BOLD, NUMF, QF, GREEN, RED, YELLOW = mh.BOLD, mh.NUMF, mh.QF, mh.GREEN, mh.RED, mh.YELLOW
    TITLE, GRAY, ngay_vn, tol_tien = cs.TITLE, cs.GRAY, cs.ngay_vn, cs.tol_tien
    (hd, ma, ngay, loai, pls, hl, bo, con_lai, bang, tong, dot, dot_truoc, kt, kt_chi_tiet, b1, rows, thieu, gt_kn, sum_kn, vat1) = (
        k[x] for x in ("hd", "ma", "ngay", "loai", "pls", "hl", "bo", "con_lai", "bang", "tong", "dot", "dot_truoc", "kt", "kt_chi_tiet", "b1",
                       "rows", "thieu", "gt_kn", "sum_kn", "vat1"))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tong hop"
    put(ws, 1, 1, "KIỂM TRA HỒ SƠ THANH TOÁN VỚI HỢP ĐỒNG + PHỤ LỤC HIỆU LỰC", TITLE)
    put(ws, 2, 1, f"{hd['so_hd']} - loại giá: {loai or '?'} - hồ sơ: {Path(path).name} - bảng: {bang['sheet']}")
    put(ws, 4, 1, f"Đợt kiểm tra: {dot or '?'}; đợt trước trong CSDL: {dot_truoc or 'không có'}"
                  + ("" if kt_chi_tiet or not dot_truoc else f" (đợt {dot_truoc} chỉ có số tổng, chưa có KL từng hạng mục: KL kỳ trước chưa đối chiếu được)"),
        GRAY)
    put(ws, 3, 1, f"Mốc áp dụng phụ lục = ngày nghiệm thu {ngay_vn(ngay)}. Phụ lục áp dụng: "
                  + (", ".join(f"{p['so_pl']} ({ngay_vn(p['ngay_hieu_luc'])})" for p in pls) or "không có")
                  + (". Chưa áp dụng: " + ", ".join(f"{p['so_pl']} ({p['trang_thai']}, {ngay_vn(p['ngay_hieu_luc'])})" for p in con_lai) if con_lai else ""),
        GRAY)
    header(ws, 6, ["Kiểm tra", "Theo hồ sơ", "Theo CSDL (hiệu lực)", "Chênh lệch", "Kết luận", "Ô trong hồ sơ"], [48, 18, 20, 16, 70, 26])
    r = 7
    put(ws, r, 1, "BƯỚC 1 - Giá trị hợp đồng", BOLD)
    r += 1
    for t, a, b, kl, o in b1:
        put(ws, r, 1, t)
        put(ws, r, 2, a, fmt=NUMF)
        put(ws, r, 3, b, fmt=NUMF)
        put(ws, r, 4, (a - b) if a is not None else None, fmt=NUMF)
        put(ws, r, 5, kl, fill=GREEN if kl == "ĐẠT" else RED, wrap=True)
        put(ws, r, 6, o)
        r += 1
    r += 1
    put(ws, r, 1, "BƯỚC 2 - BOQ hiệu lực", BOLD)
    r += 1
    put(ws, r, 1, "Số hạng mục BOQ hiệu lực / đã bỏ")
    put(ws, r, 2, len(hl))
    put(ws, r, 3, len(bo))
    r += 1
    put(ws, r, 1, "Hạng mục chịu tác động của phụ lục")
    put(ws, r, 2, sum(1 for d in hl.values() if d["nguon"] != "HĐ gốc"))
    r += 2
    put(ws, r, 1, f"BƯỚC 3 - Từng hạng mục (HĐ {loai})", BOLD)
    r += 1
    cnt = Counter(l.split(":")[0].split(" (")[0] for x in rows for l in x["loi"])
    if not cnt:
        put(ws, r, 1, "Không có lệch")
        put(ws, r, 5, "ĐẠT", fill=GREEN)
        r += 1
    for k_, n_ in cnt.most_common():
        put(ws, r, 1, k_)
        put(ws, r, 2, n_)
        put(ws, r, 5, "Xem sheet Hang muc", fill=RED)
        r += 1
    put(ws, r, 1, "Hạng mục BOQ hiệu lực không có trong hồ sơ")
    put(ws, r, 2, len(thieu))
    r += 1
    tong_ah = sum(x["anh_huong"] for x in rows) * vat1
    put(ws, r, 1, "Giá trị lũy kế chưa có căn cứ HĐ/phụ lục (sau VAT) - tạm chưa thanh toán", BOLD)
    put(ws, r, 3, round(tong_ah), fmt=NUMF, fill=RED if abs(tong_ah) > 1 else GREEN)
    put(ws, r, 5, "Chi tiết ở sheet Yeu cau phu luc")
    r += 2
    put(ws, r, 1, "Σ(KL kỳ này × đơn giá hiệu lực) × (1+VAT)")
    put(ws, r, 2, gt_kn, fmt=NUMF)
    put(ws, r, 3, round(sum_kn), fmt=NUMF)
    if gt_kn is not None:
        put(ws, r, 4, gt_kn - round(sum_kn), fmt=NUMF)
        put(ws, r, 5, "ĐẠT" if abs(gt_kn - sum_kn) <= tol_tien(gt_kn) else "Lệch - kiểm tra", fill=GREEN if abs(gt_kn - sum_kn) <= tol_tien(gt_kn) else RED)
        put(ws, r, 6, tong.get("gt_kn", {}).get("o", ""))
    r += 1
    if dot_truoc:
        lk_db = con.execute("SELECT gt_luy_ke FROM dot_thanh_toan WHERE ma_hd = ? AND dot = ?", (ma, dot_truoc)).fetchone()[0]
        a = tong.get("gt_lk_kt", {}).get("gia_tri")
        put(ws, r, 1, f"GT lũy kế hết kỳ trước = lũy kế đợt {dot_truoc} đã duyệt")
        put(ws, r, 2, a, fmt=NUMF)
        put(ws, r, 3, lk_db, fmt=NUMF)
        if a is not None and lk_db is not None:
            put(ws, r, 4, a - lk_db, fmt=NUMF)
            put(ws, r, 5, "ĐẠT" if abs(a - lk_db) <= 1 else "Lệch - kiểm tra", fill=GREEN if abs(a - lk_db) <= 1 else RED)
        put(ws, r, 6, tong.get("gt_lk_kt", {}).get("o", ""))
        r += 1
    w2 = wb.create_sheet("Hang muc")
    header(w2, 1, ["Dòng HS", "Mã HM", "Khớp bằng", "Tên công việc", "ĐVT", "KL HĐ hồ sơ", "KL hiệu lực", "Nguồn KL/ĐG", "Đơn giá hồ sơ",
                   "Đơn giá hiệu lực", "KL kỳ trước HS", f"Lũy kế đợt {dot_truoc or '-'}", "KL kỳ này", "KL lũy kế", "Ảnh hưởng đơn giá (× lũy kế)",
                   "Lịch sử BOQ", "Lệch"],
           [7, 8, 12, 50, 8, 12, 12, 9, 13, 13, 12, 12, 12, 12, 16, 40, 60])
    w2.freeze_panes = "E2"
    for i, x in enumerate(rows, 2):
        it, m = x["it"], x["m"] or {}
        vals = [it["dong"], it["ma_hm"], it["cach_khop"], it["ten"], it["dvt"], it["kl_hd"], m.get("kl"), m.get("nguon"), it["don_gia"], m.get("don_gia"),
                it["kl_kt"], kt.get(it["ma_hm"]) if it["ma_hm"] else None, it["kl_kn"], it["kl_lk"]]
        for j, v in enumerate(vals, 1):
            put(w2, i, j, v, fmt=QF if j in (6, 7, 11, 12, 13, 14) else (NUMF if j in (9, 10) else None), text=True)
        put(w2, i, 15, f'=IF(J{i}="","",(I{i}-J{i})*N{i})', fmt=NUMF)
        put(w2, i, 16, " → ".join(m.get("lich_su", [])), text=True)
        put(w2, i, 17, "; ".join(x["loi"]), text=True)
        if x["loi"]:
            w2.cell(i, 17).fill = RED
        if m.get("nguon") and m["nguon"] != "HĐ gốc":
            w2.cell(i, 8).fill = YELLOW
    wy = wb.create_sheet("Yeu cau phu luc")
    header(wy, 1, ["Mã HM", "Tên công việc (theo hồ sơ)", "ĐVT", "KL lũy kế hồ sơ", "KL hiệu lực", "Đơn giá hồ sơ", "Đơn giá hiệu lực", "Ảnh hưởng chưa VAT",
                   "Ảnh hưởng sau VAT", "Nội dung cần phụ lục / giải trình"], [8, 50, 8, 13, 13, 14, 14, 16, 16, 70])
    i = 2
    for x in rows:
        if not x["loi"]:
            continue
        it, m = x["it"], x["m"] or {}
        for j, v in enumerate([it["ma_hm"], it["ten"], it["dvt"], it["kl_lk"], m.get("kl"), it["don_gia"], m.get("don_gia"), x["anh_huong"],
                               round(x["anh_huong"] * vat1), "; ".join(x["loi"])], 1):
            put(wy, i, j, v, fmt=QF if j in (4, 5) else (NUMF if j in (6, 7, 8, 9) else None), text=True)
        i += 1
    put(wy, i, 2, "Cộng", BOLD)
    put(wy, i, 8, f"=SUM(H2:H{i - 1})" if i > 2 else 0, BOLD, NUMF)
    put(wy, i, 9, f"=SUM(I2:I{i - 1})" if i > 2 else 0, BOLD, NUMF)
    w3 = wb.create_sheet("Thieu trong ho so")
    header(w3, 1, ["Mã HM", "Tên công việc", "ĐVT", "KL hiệu lực", "Nguồn"], [9, 60, 9, 12, 10])
    for i, d in enumerate(thieu, 2):
        for j, v in enumerate([d["ma_hm"], d["ten"], d["dvt"], d["kl"], d["nguon"]], 1):
            put(w3, i, j, v, fmt=QF if j == 4 else None, text=True)
    w4 = wb.create_sheet("Phu luc")
    header(w4, 1, ["Số PL", "Ngày ký", "Ngày hiệu lực", "Trạng thái", "Áp dụng cho đợt này?", "GT tăng/giảm sau VAT", "Nội dung"], [8, 11, 12, 10, 18, 18, 60])
    for i, p in enumerate(con.execute("SELECT * FROM phu_luc WHERE ma_hd = ? ORDER BY ngay_hieu_luc, so_pl", (ma,)), 2):
        ad = "Có" if p["id"] in {q["id"] for q in pls} else "Không"
        for j, v in enumerate([p["so_pl"], ngay_vn(p["ngay_ky"]), ngay_vn(p["ngay_hieu_luc"]), p["trang_thai"], ad, p["gt_sau_vat"], p["noi_dung"]], 1):
            put(w4, i, j, v, fmt=NUMF if j == 6 else None, text=True)
    wb.save(str(out))


# ================================================================================================== tính một lần chạy
def tinh(vao: dict, thu_muc: Path) -> dict:
    """Một lần chạy L1 hoặc L1+L2 trên bản XLSX đã giữ lại. Không mạng/PG; ghi báo cáo vào thu_muc (tên cố định trong thư mục riêng của lần chạy)."""
    from . import nguon_review as NR
    thu_muc = Path(thu_muc)
    path = Path(vao["xlsx"])
    raw = path.read_bytes()
    if _sha(raw) != vao["raw_sha256"]:
        raise RuntimeError("Bản XLSX làm việc khác raw SHA đã chụp — dừng")
    co_so, che_do, o_dich = vao["basis"], vao["che_do"], vao.get("o_dich")
    tv, nv = NR._m("toan_ven"), NR._m("may_chu.nghiep_vu")
    kt = tv.KiemTra(str(path), o_dich or None).chay()
    ph1, bang_k, cay, dich = nv._lop1(kt, path.name)
    cov = coverage_l1(kt, tv, o_dich)
    _gan_bang_k(bang_k, cov)
    bao_cao = []
    nguon1, out1 = thu_muc / "lop1_nguon.xlsx", thu_muc / "lop1.xlsx"
    tv.ghi(kt, str(nguon1))
    _them_pham_vi(nguon1, out1, [[r["code"], r["ten"], r["trang_thai_kiem"], r["ket_qua_nguon"], r["ket_qua_hien_thi"], r["ly_do_kiem"]] for r in bang_k],
                  f"PHẠM VI KIỂM LỚP 1 · {path.name}")
    bao_cao += [{"loai": "REPORT_L1_NGUON", "tep": nguon1.name}, {"loai": "REPORT_L1", "tep": out1.name}]
    lop1 = {"phat_hien": ph1, "bang_k": bang_k, "cay": cay, "dich": dich, "nguon_dich": cov["K7"].get("nguon_dich"), "so_sheet": len(kt.sd.wb.sheetnames),
            "de_nghi": next((r["gia_tri"] for r in cay if r["cap"] == 0), None)}
    lop2, pt = None, {}
    ph2 = []
    if che_do == "L1_L2":
        pt = phu_thuoc(co_so)
        lop2 = {"chay": False, "phu_thuoc": pt}
        cs, mh = NR._m("csdl_hop_dong"), NR._m("master_hd")
        if not pt.get("NGAY", {}).get("ok"):
            lop2["ly_do"] = pt["NGAY"]["ly_do"]
            _, cov_l2 = coverage_l2([], pt, cov, [], l2_loi="INCOMPLETE")
        elif not pt.get("BOQ", {}).get("ok"):
            lop2["ly_do"] = pt["BOQ"]["ly_do"]
            _, cov_l2 = coverage_l2([], pt, cov, [], l2_loi="INCOMPLETE")
        else:
            import openpyxl
            con, ban_do = NR.projection_l2(co_so)
            try:
                wv = openpyxl.load_workbook(str(path), data_only=True)
                ngay = str(co_so["dot"]["ngay_nghiem_thu"])[:10]
                try:
                    k = cs.tinh_doi_chieu_dot(con, ban_do["ma_hd"], str(path), ngay, co_so["dot"]["so_dot"], wv=wv)
                    ph2, _ = nv._lop2(k)
                    ph_gt, bang_l2, doi_chieu_hm = nv.bang_kiem_lop2(k, ph2, cs, con)
                    ph2 += ph_gt
                    for i, f in enumerate(ph_gt, 1):
                        f["id"] = f"GT-{len([x for x in ph2 if x['code'] == 'GT']) - len(ph_gt) + i:02d}"
                    for h in bang_l2:
                        if isinstance(h["finding"], dict):
                            h["finding"] = h["finding"]["id"]
                    ph2 += nv._lop2b(kt, k, cs, con, bang=bang_l2)
                except (Exception, SystemExit) as exc:  # noqa: BLE001 — L2 lỗi: ghi ERROR thật, không coi là đạt
                    lop2["ly_do"] = f"Lớp 2 lỗi: {type(exc).__name__}: {str(exc)[:300]}"
                    _, cov_l2 = coverage_l2([], pt, cov, [], l2_loi="ERROR")
                    k = None
                if k is not None:
                    # RC01/§10.2: `_lop2b` nuốt lỗi provider tham số thành None; quan sát lại ĐÚNG lời gọi provider nguồn trên cùng projection
                    # chỉ-đọc để tách provider ERROR khỏi CHUA_CO / không áp dụng (không sửa vendor, không đổi kết quả nguồn)
                    for ma, khoa_pt in (("TT-04", "VAT"), ("TT-10", "TT-10"), ("TT-11", "TT-11"), ("TT-20", "TT-20"), ("TT-21", "TT-21")):
                        try:
                            cs.tham_so_hieu_luc(con, k["ma"], ma, k["ngay"])
                        except Exception as exc:  # noqa: BLE001 — ghi nhận lỗi provider thật
                            pt[khoa_pt] = {"ok": False, "ly_do": f"provider ERROR khi đọc {ma}: {type(exc).__name__} — nguồn coi là None"}
                    knd = trang_thai_tho(wv, k["tong"], mh)
                    bang_l2, cov_l2 = coverage_l2(bang_l2, pt, cov, knd)
                    nguon2, out2 = thu_muc / "lop2_nguon.xlsx", thu_muc / "lop2.xlsx"
                    bao_cao_lop2(con, k, path, nguon2, cs, mh)
                    _them_pham_vi(nguon2, out2, [[r.get("ma_kiem"), r["ten"], r["trang_thai_kiem"], r.get("ket_qua_nguon"), r["ket_qua_hien_thi"],
                                                  r["ly_do_kiem"]] for r in bang_l2], f"PHẠM VI KIỂM LỚP 2 · {path.name}")
                    bao_cao += [{"loai": "REPORT_L2_NGUON", "tep": nguon2.name}, {"loai": "REPORT_L2", "tep": out2.name}]
                    # FIX01 R6: nguồn BOQ của mã HM → ID PG ổn định của ĐÚNG dòng engine dùng (boq_hieu_luc nguồn trên cùng projection/ngày NT);
                    # mọi nguồn (gốc + PL) giữ riêng ở nguon_boq_tat_ca để truy vết — đích ghép tay chỉ lấy nguon_boq
                    hl_eng, _bo = cs.boq_hieu_luc(con, k["ma"], pls=k["pls"])

                    def nguon_hl(ma):
                        tat_ca = ban_do["nguon_boq"].get(ma) or []
                        d = hl_eng.get(ma)
                        if d is None:
                            return [], tat_ca
                        pl_pg = None
                        if d.get("nguon") != "HĐ gốc":
                            p = next((p for p in reversed(k["pls"]) if p["so_pl"] == d["nguon"]), None)
                            pl_pg = ban_do["phu_luc"].get(p["id"]) if p is not None else "?"
                        return [x for x in tat_ca if (x["phu_luc_id"] is None if pl_pg is None else str(x["phu_luc_id"]) == str(pl_pg))], tat_ca
                    for h in doi_chieu_hm:
                        h["nguon_boq"], h["nguon_boq_tat_ca"] = nguon_hl(h.get("ma_hm"))
                        for u in h.get("ung_vien") or []:
                            u["nguon_boq"], u["nguon_boq_tat_ca"] = nguon_hl(u["ma_hm"])
                    lop2.update(chay=True, phat_hien=ph2, bang_lop2=bang_l2, doi_chieu_hm=doi_chieu_hm, so_tong_hop_tho=knd,
                                tong_hop={kk: vv for kk, vv in k["tong"].items()}, bang_chi_tiet=k["bang"]["sheet"],
                                phu_luc_ap_dung=[{"so_pl": p["so_pl"], "ngay_hieu_luc": p["ngay_hieu_luc"]} for p in k["pls"]],
                                phu_luc_chua_ap_dung=[{"so_pl": p["so_pl"], "ngay_hieu_luc": p["ngay_hieu_luc"], "trang_thai": p["trang_thai"]}
                                                      for p in k["con_lai"]],
                                dot=k["dot"], dot_truoc=k["dot_truoc"], ngay_nghiem_thu=k["ngay"], gt_hieu_luc=k["gt_hl"], vat=k["vat"],
                                loai_gia=k["loai"], so_hang_muc=len(k["rows"]), de_nghi=(k["tong"].get("tt_ky_nay") or {}).get("gia_tri"),
                                o_de_nghi=(k["tong"].get("tt_ky_nay") or {}).get("o") or dich,
                                ghi_chu_tien="Ảnh hưởng là ước tính float/tolerance của thuật toán nguồn — không phải số thanh toán/NT/thuế được chấp nhận")
            finally:
                con.close()
        cov.update(cov_l2)
    ph = ph2 + ph1
    ph.sort(key=lambda f: ({"Cao": 0, "Trung bình": 1, "Thấp": 2}.get(f["level"], 3), f["layer"]))
    anh_huong = sum(f["amount"] for f in ph if f["layer"] == 2 and isinstance(f["amount"], (int, float)) and f["code"] != "GT")
    trang_thai = "SUCCEEDED" if all(c["trang_thai"] in DAT_DU for c in cov.values()) else "PARTIAL"
    return _json({"phien_ban": NR.REVIEW_PHIEN_BAN, "engine": NR.ENGINE_REVIEW, "engine_sha256": NR.ENGINE_REVIEW_SHA, "che_do": che_do,
                  "raw_sha256": vao["raw_sha256"], "basis_sha256": vao["basis_sha256"], "tep": path.name, "o_dich": o_dich,
                  "lop1": lop1, "lop2": lop2, "coverage": cov, "nguong_nguon": NGUONG, "phat_hien": ph,
                  "dem": dict(Counter(f["level"] for f in ph)), "so_phat_hien": len(ph), "anh_huong_uoc_tinh": anh_huong,
                  "trang_thai": trang_thai, "bao_cao": bao_cao})


ENV_GUARD_DAU = "KTT_REVIEW_GUARD_DAU"  # dấu vân hook xóa/ghi đè THẬT của tiến trình máy chủ (JSON không bí mật: tên hàm/module/tệp mã nguồn)
MA_GUARD_KHONG_NAP = 4
# điểm vào xóa/ghi đè/di chuyển tệp mà guard giữ tệp gốc phải chặn — kiểm đối tượng ĐANG được cài trong tiến trình, không tin tên module/marker
HAM_XOA = (("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "removedirs"), ("os", "replace"), ("os", "rename"), ("os", "renames"),
           ("shutil", "rmtree"), ("shutil", "move"), ("pathlib", "Path.unlink"), ("pathlib", "Path.rmdir"), ("pathlib", "Path.replace"),
           ("pathlib", "Path.rename"))


def _chuan_duong(p):
    import os
    return os.path.normcase(os.path.normpath(os.path.abspath(p))) if p else None


def _nguon_ma(code, obj) -> tuple[str, str | None]:
    """FIX03 F1 — nguồn mã của một hàm TRƯỚC khi chuẩn hóa đường dẫn: ("frozen", "<frozen os>") chỉ khi sentinel trùng ĐÚNG module định nghĩa hàm
    và module đó thực sự được nạp từ bộ frozen (`__spec__.origin == "frozen"`); sentinel khác ("<string>", "<frozen x>" không khớp…) → ("sentinel",
    chuỗi gốc) — không abspath (không phụ thuộc CWD), không được coi là stdlib; còn lại ("tep", đường dẫn tuyệt đối đã chuẩn hóa)."""
    f = code.co_filename or ""
    if f.startswith("<") and f.endswith(">"):
        noi = f[1:-1]
        if noi.startswith("frozen "):
            ten_mod = noi[len("frozen "):]
            m = sys.modules.get(ten_mod)
            if m is not None and ten_mod == getattr(obj, "__module__", None) and getattr(getattr(m, "__spec__", None), "origin", None) == "frozen":
                return "frozen", f
        return "sentinel", f
    return "tep", _chuan_duong(f)


def dau_van_guard() -> dict:
    """FIX02 F1 — dấu vân hook THẬT đang cài: với mỗi điểm vào xóa/ghi đè, đối tượng hiện hành là bản gốc của Python (builtin trùng hàm của module
    C `nt`/`posix`, hoặc hàm Python định nghĩa trong thư viện chuẩn) hay đã được thay (hook) — kèm module/qualname/tệp mã nguồn của hook.
    Chỉ đọc thuộc tính đối tượng đang nạp (stdlib os/shutil/pathlib/sysconfig); không gọi hàm xóa, không nạp vendor/OpenPyXL, không đọc env bí mật.
    Module khởi động (sitecustomize/usercustomize) chỉ ghi làm provenance, KHÔNG phải bằng chứng hook đang hoạt động."""
    import importlib
    import os
    import sysconfig
    c = importlib.import_module("nt" if os.name == "nt" else "posix")
    stdlib = {_chuan_duong(sysconfig.get_paths().get(k)) for k in ("stdlib", "platstdlib")} - {None}

    def trong_stdlib(f):
        return bool(f) and "site-packages" not in f and any(f.startswith(s + os.sep) for s in stdlib)
    ham = {}
    for mod, ten in HAM_XOA:
        obj = importlib.import_module(mod)
        for phan in ten.split("."):
            obj = getattr(obj, phan, None)
        if obj is None:
            ham[f"{mod}.{ten}"] = None
            continue
        code = getattr(obj, "__code__", None)
        if code is not None:
            loai, f = _nguon_ma(code, obj)  # FIX03 F1: sentinel <frozen …> không đi qua abspath (trước đây thành CWD/<frozen os> → khác cha/con)
            goc = loai == "frozen" or (loai == "tep" and trong_stdlib(f))
        else:
            f, goc = None, (mod == "os" and obj is getattr(c, ten, object()))
        ham[f"{mod}.{ten}"] = {"goc": bool(goc), "module": getattr(obj, "__module__", None), "qualname": getattr(obj, "__qualname__", None),
                               "tep": None if goc else f}
    khoi_dong = {k: _chuan_duong(getattr(sys.modules[k], "__file__", None)) for k in ("sitecustomize", "usercustomize") if k in sys.modules}
    return {"ham": ham, "khoi_dong": khoi_dong}


def hook_hoat_dong(dau: dict) -> bool:
    """Có ít nhất một điểm vào xóa/ghi đè đang là hook (không phải bản gốc) VỚI tệp mã nguồn thật (đường dẫn tuyệt đối) — bằng chứng hook ĐANG cài.
    FIX03 F1: hàm stdlib frozen chưa bị thay không phải hook; sentinel ("<…>") hay không có nguồn không tự là bằng chứng guard."""
    import os

    def la_hook(v):
        tep = (v or {}).get("tep")
        return v is not None and not v.get("goc") and isinstance(tep, str) and not tep.startswith("<") and os.path.isabs(tep)
    return any(la_hook(v) for v in (dau or {}).get("ham", {}).values())


def guard_dang_nap(env=None, dau=None) -> tuple[bool, str]:
    """FIX02 F1: cha yêu cầu giữ tệp (CODEX_NO_DELETE_FILES hoặc gửi dấu vân hook của chính nó) → con PHẢI có hook giữ tệp THẬT đang cài, cùng
    provenance với cha; kiểm TRƯỚC mọi vendor/OpenPyXL/I-O báo cáo. Hook thật đang cài mà không có sitecustomize → KHÔNG bị từ chối; chỉ có
    module/marker mà hook không cài → từ chối; hook khác provenance của cha → từ chối. Không tự tạo/vá/tắt guard."""
    import os
    env = os.environ if env is None else env
    can = env.get(ENV_GUARD_DAU) or ""
    bat = str(env.get("CODEX_NO_DELETE_FILES") or "").strip().lower() in ("1", "true", "yes", "on")
    if not can and not bat:
        return True, "Không yêu cầu guard giữ tệp"
    dau = dau_van_guard() if dau is None else dau
    if not hook_hoat_dong(dau):
        return False, "Chế độ giữ tệp được yêu cầu nhưng không có hook xóa/ghi đè nào đang cài trong tiến trình tính"
    if can:
        try:
            cha = json.loads(can)
        except ValueError:
            return False, "Dấu vân guard của tiến trình máy chủ không đọc được"
        if cha.get("ham") != dau.get("ham"):
            return False, "Hook giữ tệp của tiến trình tính khác provenance hook của tiến trình máy chủ"
    return True, "Hook giữ tệp gốc đang cài, cùng provenance với tiến trình máy chủ"


def main(argv=None) -> int:
    """Điểm vào tiến trình con. Luôn cố ghi ket_qua.json (kể cả lỗi) — máy chủ quyết FAILED; lỗi không bao giờ thành PASS.
    Ngoại lệ duy nhất: guard giữ tệp được yêu cầu mà không nạp → dừng NGAY (mã 4), không ghi gì, không nạp vendor/OpenPyXL."""
    argv = list(sys.argv[1:] if argv is None else argv)
    ok, ly_do = guard_dang_nap()
    if not ok:
        sys.stderr.write("GUARD_KHONG_NAP: " + ly_do + "\n")
        return MA_GUARD_KHONG_NAP
    from ..ha_tang.store import write_immutable
    thu_muc = Path(argv[0])
    try:
        vao = json.loads((thu_muc / "vao.json").read_text(encoding="utf-8"))
        if isinstance(vao, dict) and vao.get("che_do") == "L3":  # M4-02B: nhánh Chứng từ L3 tường minh — cùng guard/tiến trình/ghi kết quả; L1/L1_L2 giữ nguyên
            from . import chung_tu_adapter
            kq = chung_tu_adapter.tinh(vao, thu_muc)
        else:
            kq = tinh(vao, thu_muc)
    except BaseException as exc:  # noqa: BLE001 — ghi lỗi thật làm bằng chứng
        kq = {"trang_thai": "FAILED", "loi": f"{type(exc).__name__}: {str(exc)[:500]}", "traceback": traceback.format_exc()[-4000:], "bao_cao": []}
    write_immutable(thu_muc / "ket_qua.json", _bytes_json(kq))
    return 0 if kq.get("trang_thai") != "FAILED" else 3


if __name__ == "__main__":
    sys.exit(main())  # guard kiểm ở đầu main(); mức module chỉ import thư viện chuẩn (không vendor/OpenPyXL)
