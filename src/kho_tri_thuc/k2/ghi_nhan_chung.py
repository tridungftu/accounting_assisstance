"""M4-03B-01 — dịch vụ DÙNG CHUNG identity nguồn kinh tế M2–M4 + đối chiếu căn cứ (nghiệm thu đợt ↔ hóa đơn mua đã có) do kế toán xác nhận.

KHÔNG phải financial owner / claim / proposal / công nợ / AP / capacity: mọi kết quả `ghi_nhan.trang_thai = CHO_CAN_CU_GHI_NHAN`, `financial_owner = None`,
mọi bộ đếm claim/proposal/source_use/obligation/ap = 0; tiền M2 vẫn UNPROVEN_NO_MINOR, không đọc số tiền. Request luôn CHUA_NOI_M4_04.

Luồng (mọi quyết định ở SQL `k2/sql_ghi_nhan_chung.py`, service chỉ kiểm hình thức + chuyển):
- kiểm sớm trên login thường: NT → adapter (m4.kt_kiem XEM); hóa đơn → kho.dc_doc_hoa_don (M2_READ). Không lộ tồn tại khi thiếu quyền.
- MỘT giao dịch chủ bảng (`xd._tx_review`): refs của gốc (quyền đọc MỌI revision trước) → thứ tự NT (quyền trước) → adapter khóa + ghim producer 03A
  cho TỪNG NT (kho._dc_nt_ghi) → kho.dc_luu / kho.dc_xac_nhan / kho._dc_xem / kho._dc_lich_su (quyền → khóa hóa đơn → gốc → biên nhận → CAS → ghi thêm;
  trigger deferred dựng lại đồ thị lúc commit).
- Không matching: trình duyệt CHỈ gửi ref nguồn tường minh {kind, occurrence_id, source_version_id, part_id}; tên/ngày/tiền/"khớp"/điểm gợi ý là
  KHÔNG_NHAN. Phần "một phần" chỉ là khai báo thô (ty_le_khai, chưa scale) — thiếu thì PHAN_KHAI_THIEU, không suy.
- FIX01: thêm/bớt nguồn, đổi phần = revision mới của CÙNG gốc (doi_chieu_id ổn định). Closure = refs revision mới nhất ∪ refs yêu cầu: adapter khóa +
  ghim producer cho mọi NT của union (adapter không đổi), SQL kiểm quyền ghi + khóa hóa đơn trên union, rồi alias tập → gốc → revision (CAS). Tập đã
  thuộc gốc khác → 409 DC_TAP_THUOC_GOC_KHAC. Namespace biên nhận = module gốc lúc tạo (máy chủ ghi, trình duyệt không chọn).
"""

from __future__ import annotations

import json
import re
import uuid

from ..ha_tang.primitives import DataError
from .sql_ghi_nhan_chung import (CONTRACT_DO_THI, GHI_NHAN_TT, LOAI_NGUON, PHAN, THIEU, TOI_DA_TEP, TOI_DA_THANH_PHAN, TT_CAN_KIEM_LAI,
                                 TT_NHAP, TT_XAC_NHAN)

SCHEMA = "M4_03B_DOI_CHIEU_CAN_CU_V1"
GHI_NHAN = {"trang_thai": GHI_NHAN_TT, "financial_owner": None, "claim": 0, "proposal": 0, "source_use": 0, "obligation": 0, "ap": 0}
REQUEST = {"trang_thai": "CHUA_NOI_M4_04"}
TRANG_THAI = (TT_NHAP, TT_XAC_NHAN, TT_CAN_KIEM_LAI)

REF_KEYS = ("kind", "occurrence_id", "source_version_id", "part_id")
THANH_PHAN_KEYS = ("nguon", "phan", "ty_le_khai")
TRUONG_LUU = ("doi_chieu_id", "thanh_phan", "can_cu_tep", "expected_graph", "expected_revision", "ly_do", "khoa")
TRUONG_XAC_NHAN = ("doi_chieu_id", "phien_ban_id", "expected_revision", "expected_graph", "khoa")
TRUONG_XEM = ("nguon",)
# thẩm quyền/định danh/trạng thái/tài chính/kết luận khớp do MÁY CHỦ quyết — trình duyệt gửi là sai vai trò (không bỏ qua im lặng)
KHONG_NHAN = frozenset({
    "actor", "nguoi_dung_id", "dang_nhap", "tao_boi", "tao_boi_id", "owner", "chu", "chu_bang", "vai", "vai_tro", "quyen", "role", "module",
    "phap_nhan_id", "du_an_id", "hop_dong_id", "doi_tac_id", "doi_tac_mst", "mst_ban", "dot_id", "seal_id", "version_id", "phong_bi_id",
    "context", "graph_sha256", "noi_dung_sha256", "semantic_sha256", "raw_sha256", "do_thi", "thieu", "khoa_goc_sha256",
    "tap_sha256", "module_bien_nhan",
    "trang_thai", "loai", "nhap_id", "revision", "pass", "dat", "approved", "da_xac_nhan", "receipt_id", "lap_lai",
    "ghi_nhan", "financial_owner", "claim", "proposal", "source_use", "obligation", "ap", "request", "cong_no", "so_cai", "but_toan",
    "tai_khoan", "account", "thue_suat", "tien_thue", "ty_gia", "fx", "so_tien", "tien", "gia_tri", "amount", "minor", "net_minor", "total_minor",
    "capacity", "suc_chua", "policy", "chinh_sach",
    "khop", "match", "matched", "diem", "score", "goi_y", "suggestion", "heuristic", "ten", "ngay", "ngay_lap", "ten_ben_ban"})
KHOA_RE = re.compile(r"[A-Za-z0-9_.:-]{1,200}")
HEX_RE = re.compile(r"[0-9a-f]{64}")
VAN_BAN_TOI_DA = 2000
TY_LE_TOI_DA = 100
REVISION_TOI_DA = 10 ** 6

# gợi ý HTTP cho integration owner (không sửa bảng mã giao diện/route trong gói này)
MA_HTTP = {
    "DC_YEU_CAU_SAI": 422, "DC_CLIENT_AUTHORITY": 422, "DC_THAM_SO_SAI": 422, "DC_KHOA_THAO_TAC": 422, "DC_PHAN_SAI": 422, "DC_CAN_CU_SAI": 422,
    "DC_KHAC_PN": 422,
    "DC_PHAM_VI": 403, "M4_KT_PHAM_VI": 403, "DC_KHONG_THAY": 404, "M4_KT_KHONG_THAY": 404, "DC_DANH_TINH": 401,
    "DC_NGUON_CU": 409, "DC_DO_THI_DOI": 409, "DC_CAN_KIEM_LAI": 409, "DC_REVISION_CU": 409, "DC_DA_CO_GOC": 409, "DC_CHO_BO_SUNG": 409,
    "DC_XAC_NHAN_KHAC_NHAP": 409, "DC_IDEMPOTENCY_KHAC": 409, "DC_TAP_THUOC_GOC_KHAC": 409,
    "M4_KET_QUA_CHUA_RO": 503,
    "DC_SAI_DTO": 500, "DC_CHI_MAY_CHU": 500, "DC_TOAN_VEN": 500, "DC_THANH_PHAN_SAI": 500, "DC_BAT_BIEN": 500, "DC_CHI_CHU": 500,
}


# ================================================================================================== kiểm đầu vào (chặt, không đoán)
def _yc_sai(msg: str):
    raise DataError("DC_YEU_CAU_SAI", msg)


def _dto_sai(msg: str):
    raise DataError("DC_SAI_DTO", f"Dữ liệu máy chủ không đúng hợp đồng {SCHEMA}: {msg}")


def _la_uuid(v) -> bool:
    if not isinstance(v, str):
        return False
    try:
        return str(uuid.UUID(v)) == v
    except ValueError:
        return False


def _la_sha(v) -> bool:
    return isinstance(v, str) and HEX_RE.fullmatch(v) is not None


def _la_int(v, *, toi_thieu: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= toi_thieu


def _uuid(v, ten: str) -> str:
    if not _la_uuid(v):
        raise DataError("DC_THAM_SO_SAI", f"{ten} phải là UUID dạng chuẩn.")
    return v


def _khoa_body(body, cho_phep: tuple, cam: frozenset = KHONG_NHAN) -> dict:
    """Object có ĐÚNG các khóa cho phép (mọi khóa hiện diện; null ≠ thiếu). Khóa thẩm quyền/khớp/tài chính → DC_CLIENT_AUTHORITY."""
    if not isinstance(body, dict):
        _yc_sai("Yêu cầu phải là object JSON.")
    kh = set(body)
    xau = sorted(str(k) for k in kh if k in cam and k not in cho_phep)
    if xau:
        raise DataError("DC_CLIENT_AUTHORITY", "Trình duyệt không được gửi trường do máy chủ quyết định / kết luận khớp: " + ", ".join(xau[:10]))
    la = sorted(str(k)[:60] for k in kh if k not in cho_phep)
    if la:
        _yc_sai("Trường không thuộc hợp đồng: " + ", ".join(la[:10]))
    thieu = [k for k in cho_phep if k not in kh]
    if thieu:
        _yc_sai("Thiếu trường bắt buộc (gửi null nếu chưa có): " + ", ".join(thieu))
    return body


def _khoa(v) -> str:
    if not isinstance(v, str) or not KHOA_RE.fullmatch(v):
        raise DataError("DC_KHOA_THAO_TAC", "Thiếu hoặc sai khóa thao tác (chống bấm lặp).")
    return v


def _van_ban(v, ten: str, toi_da: int = VAN_BAN_TOI_DA) -> str:
    if not isinstance(v, str) or not v.strip() or len(v) > toi_da:
        _yc_sai(f"{ten} phải là chuỗi 1–{toi_da} ký tự, không rỗng.")
    return v


def _rev(v) -> int:
    if not _la_int(v, toi_thieu=0) or v > REVISION_TOI_DA:
        raise DataError("DC_THAM_SO_SAI", "expected_revision phải là số nguyên ≥ 0 (0 = tạo đối chiếu mới).")
    return v


def kiem_ref(r) -> dict:
    """Ref nguồn tường minh: {kind, occurrence_id, source_version_id, part_id}. NT chỉ phần toàn bộ (part_id null); hóa đơn part_id = dòng logic có
    thật hoặc null (toàn hóa đơn). source_version_id = phiên bản đang xem (phong bì / phiên bản hóa đơn) — máy chủ so CAS."""
    _khoa_body(r, REF_KEYS)
    if r["kind"] not in LOAI_NGUON:
        raise DataError("DC_THAM_SO_SAI", "kind phải là NT hoặc HOA_DON.")
    _uuid(r["occurrence_id"], "occurrence_id")
    _uuid(r["source_version_id"], "source_version_id")
    if r["part_id"] is not None:
        _uuid(r["part_id"], "part_id")
        if r["kind"] == "NT":
            raise DataError("DC_PHAN_SAI", "Nguồn nghiệm thu chỉ có phần TOAN_BO (part_id = null).")
    return {k: r[k] for k in REF_KEYS}


def _khoa_ref(r: dict) -> tuple:
    return (r["kind"], r["occurrence_id"], r.get("part_id") or "")


def hop_refs(a: list, b: list) -> list:
    """Closure FIX01 (gương kho._dc_hop): hợp theo (kind, occurrence, part), trùng khóa giữ mục của `a` (refs yêu cầu); sắp theo khóa.
    Chỉ dùng để khóa/ghim/kiểm quyền — đồ thị và tập revision mới vẫn là `a`."""
    m = {}
    for r in list(a or []) + list(b or []):
        m.setdefault(_khoa_ref(r), r)
    return [m[k] for k in sorted(m)]


def _kiem_tap(refs: list) -> None:
    ks = [_khoa_ref(r) for r in refs]
    if len(set(ks)) != len(ks):
        raise DataError("DC_THAM_SO_SAI", "Nguồn/phần bị lặp.")
    toan = {r["occurrence_id"] for r in refs if r["kind"] == "HOA_DON" and r["part_id"] is None}
    if any(r["kind"] == "HOA_DON" and r["part_id"] is not None and r["occurrence_id"] in toan for r in refs):
        raise DataError("DC_PHAN_SAI", "Không khai cả toàn bộ hóa đơn và dòng của chính hóa đơn đó.")


def kiem_thanh_phan(t) -> dict:
    _khoa_body(t, THANH_PHAN_KEYS)
    ref = kiem_ref(t["nguon"])
    if t["phan"] not in PHAN:
        raise DataError("DC_THAM_SO_SAI", "phan phải là TOAN_PHAN hoặc MOT_PHAN.")
    ty = t["ty_le_khai"]
    if t["phan"] == "TOAN_PHAN" and ty is not None:
        raise DataError("DC_PHAN_SAI", "TOAN_PHAN không kèm ty_le_khai.")
    if ty is not None:
        _van_ban(ty, "ty_le_khai", TY_LE_TOI_DA)
    return {"nguon": ref, "phan": t["phan"], "ty_le_khai": ty}


def yeu_cau_luu(body) -> dict:
    b = _khoa_body(body, TRUONG_LUU)
    goc = None if b["doi_chieu_id"] is None else _uuid(b["doi_chieu_id"], "doi_chieu_id")
    tps = b["thanh_phan"]
    if not isinstance(tps, list) or not 1 <= len(tps) <= TOI_DA_THANH_PHAN:
        raise DataError("DC_THAM_SO_SAI", f"thanh_phan phải là mảng 1–{TOI_DA_THANH_PHAN} nguồn.")
    tp = sorted((kiem_thanh_phan(t) for t in tps), key=lambda t: _khoa_ref(t["nguon"]))
    _kiem_tap([t["nguon"] for t in tp])
    tep = b["can_cu_tep"]
    if not isinstance(tep, list) or len(tep) > TOI_DA_TEP or len(set(map(str, tep))) != len(tep):
        raise DataError("DC_CAN_CU_SAI", f"can_cu_tep phải là mảng ≤{TOI_DA_TEP} UUID không lặp (id tệp; SHA lấy từ CSDL).")
    for x in tep:
        _uuid(x, "can_cu_tep[]")
    if not _la_sha(b["expected_graph"]):
        raise DataError("DC_THAM_SO_SAI", "expected_graph phải là SHA-256 đồ thị căn cứ đang xem.")
    rev = _rev(b["expected_revision"])
    if (goc is None) != (rev == 0):
        raise DataError("DC_THAM_SO_SAI", "Tạo mới: doi_chieu_id null + expected_revision 0; sửa: doi_chieu_id + revision hiện tại.")
    return {"doi_chieu_id": goc, "thanh_phan": tp, "can_cu_tep": sorted(tep), "expected_graph": b["expected_graph"],
            "expected_revision": rev, "ly_do": _van_ban(b["ly_do"], "ly_do"), "khoa": _khoa(b["khoa"])}


def yeu_cau_xac_nhan(body) -> dict:
    b = _khoa_body(body, TRUONG_XAC_NHAN, KHONG_NHAN | {"thanh_phan", "can_cu_tep", "ly_do", "nguon"})
    if not _la_sha(b["expected_graph"]):
        raise DataError("DC_THAM_SO_SAI", "expected_graph phải là SHA-256 đồ thị của bản nháp đã lưu.")
    rev = _rev(b["expected_revision"])
    if rev < 1:
        raise DataError("DC_THAM_SO_SAI", "expected_revision của bản nháp phải ≥ 1.")
    return {"doi_chieu_id": _uuid(b["doi_chieu_id"], "doi_chieu_id"), "phien_ban_id": _uuid(b["phien_ban_id"], "phien_ban_id"),
            "expected_revision": rev, "expected_graph": b["expected_graph"], "khoa": _khoa(b["khoa"])}


def yeu_cau_xem(body) -> list:
    b = _khoa_body(body, TRUONG_XEM)
    ns = b["nguon"]
    if not isinstance(ns, list) or not 1 <= len(ns) <= TOI_DA_THANH_PHAN:
        raise DataError("DC_THAM_SO_SAI", f"nguon phải là mảng 1–{TOI_DA_THANH_PHAN} ref.")
    refs = sorted((kiem_ref(r) for r in ns), key=_khoa_ref)
    _kiem_tap(refs)
    return refs


# ================================================================================================== gương Python của kho._dc_thieu (cùng mã, cùng thứ tự)
def thieu(do_thi: dict, thanh_phan: list | None) -> list:
    """Điều kiện căn cứ còn thiếu, dẫn từ dữ kiện nguồn/master trong đồ thị (không lời khẳng định của trình duyệt). Sắp ASCII = COLLATE "C"."""
    ns = (do_thi or {}).get("nguon") or []
    nt = [i for i in ns if i.get("kind") == "NT"]
    hd = [i for i in ns if i.get("kind") == "HOA_DON"]
    x = set()
    if not nt:
        x.add("THIEU_NT")
    if not hd:
        x.add("THIEU_HOA_DON")
    if any(i.get("hien_hanh") is not True or i.get("toan_ven") is not True for i in nt):
        x.add("NT_KHONG_HIEN_HANH")
    if any(i.get("kt_xac_nhan_id") is None for i in nt):
        x.add("NT_CHUA_KT_XAC_NHAN")
    hop_dong = {i.get("hop_dong_id") for i in nt if i.get("hop_dong_id") is not None}
    if len(hop_dong) > 1:
        x.add("NT_KHAC_HOP_DONG")
    elif nt and hd:
        mst = nt[0].get("doi_tac_mst")
        if mst is None:
            x.add("BEN_BAN_HD_THIEU")
        elif any(i.get("mst_ban") != mst for i in hd):
            x.add("BEN_BAN_KHAC")
    if any(i.get("current") is None for i in hd):
        x.add("HOA_DON_CHUA_CO_PHIEN_BAN")
    if any(i.get("part_kind") == "DONG_LOGIC" and not (i.get("cau_noi") or []) for i in hd):
        x.add("CHO_MAPPING_M2")
    if thanh_phan and any(t.get("phan") == "MOT_PHAN" and t.get("ty_le_khai") is None for t in thanh_phan):
        x.add("PHAN_KHAI_THIEU")
    assert x <= set(THIEU)
    return sorted(x)


# ================================================================================================== DTO (kiểm chặt dữ liệu máy chủ, không thêm suy luận)
def _ghi_nhan(g) -> dict:
    if g != GHI_NHAN:
        _dto_sai("ghi_nhan phải là CHO_CAN_CU_GHI_NHAN, financial_owner null, mọi bộ đếm tài chính = 0")
    return dict(GHI_NHAN)


def _do_thi(g) -> dict:
    if not isinstance(g, dict) or g.get("contract") != CONTRACT_DO_THI or not isinstance(g.get("nguon"), list):
        _dto_sai("do_thi sai hợp đồng")
    for i in g["nguon"]:
        if not isinstance(i, dict) or i.get("kind") not in LOAI_NGUON or not _la_uuid(i.get("occurrence_id")):
            _dto_sai("mục đồ thị sai")
        if i["kind"] == "HOA_DON" and i.get("money_basis_state") not in (None, "UNPROVEN_NO_MINOR"):
            _dto_sai("hóa đơn phải UNPROVEN_NO_MINOR")
        if any(k.endswith("_minor") or k in ("so_tien", "tien") for k in i):
            _dto_sai("đồ thị không được mang số tiền")
    return g


def trang_thai(loai: str, graph_luu: str, graph_hien_tai: str | None) -> str:
    """CAN_KIEM_LAI dẫn xuất (không lưu): đồ thị hiện hành khác đồ thị của revision. Không tự khôi phục ABA thành trạng thái cũ nếu không bằng SHA."""
    if graph_hien_tai is None or graph_hien_tai != graph_luu:
        return TT_CAN_KIEM_LAI
    return TT_XAC_NHAN if loai == "XAC_NHAN" else TT_NHAP


def xem_dto(r) -> dict:
    if not isinstance(r, dict) or not _la_sha(r.get("graph_sha256")) or not isinstance(r.get("thieu"), list):
        _dto_sai("xem")
    g = _do_thi(r.get("do_thi"))
    if r["thieu"] != thieu(g, None):
        _dto_sai("thieu của máy chủ khác gương kiểm căn cứ")
    lq = r.get("goc_lien_quan") or []
    return {"schema": SCHEMA,
            "nguon": g["nguon"],
            "doi_chieu": {"graph_sha256": r["graph_sha256"], "khoa_goc_sha256": r.get("khoa_goc_sha256"),
                          "goc_cua_tap": r.get("goc_cua_tap"),
                          "goc_lien_quan": [{**x, "trang_thai": trang_thai(x.get("loai"), x.get("graph_sha256"), r["graph_sha256"])} for x in lq]},
            "kt": {"thieu": r["thieu"], "duoc_ghi": r.get("duoc_ghi") is True},
            "ghi_nhan": dict(GHI_NHAN), "request": dict(REQUEST)}


def ack_dto(r, khoa: str) -> dict:
    if not isinstance(r, dict) or not isinstance(r.get("ket_qua"), dict) or not isinstance(r.get("lap_lai"), bool):
        _dto_sai("ack")
    k = r["ket_qua"]
    if not _la_uuid(k.get("doi_chieu_id")) or not _la_uuid(k.get("phien_ban_id")) or not _la_int(k.get("revision"), toi_thieu=1) \
            or k.get("trang_thai") not in (TT_NHAP, TT_XAC_NHAN) or not _la_sha(k.get("graph_sha256")):
        _dto_sai("ket_qua")
    if k["trang_thai"] == TT_XAC_NHAN and k.get("thieu") != []:
        _dto_sai("đã xác nhận nhưng còn thiếu căn cứ")
    hien = r.get("hien_tai") or {}
    return {"schema": SCHEMA, "khoa": khoa, "lap_lai": r["lap_lai"], "receipt_id": str(r.get("receipt_id")),
            "doi_chieu": {"doi_chieu_id": k["doi_chieu_id"], "phien_ban_id": k["phien_ban_id"], "revision": k["revision"],
                          "nhap_id": k.get("nhap_id"), "graph_sha256": k["graph_sha256"], "noi_dung_sha256": k.get("noi_dung_sha256"),
                          "tap_sha256": k.get("tap_sha256"),
                          "trung_xac_nhan": k.get("trung_xac_nhan") is True,
                          "trang_thai": trang_thai(k.get("loai"), k["graph_sha256"], hien.get("graph_sha256"))},
            "kt": {"thieu": k.get("thieu") or []},
            "ghi_nhan": _ghi_nhan(k.get("ghi_nhan")), "request": dict(REQUEST)}


def lich_su_dto(r) -> dict:
    if not isinstance(r, dict) or not _la_uuid(r.get("doi_chieu_id")) or not isinstance(r.get("phien_ban"), list):
        _dto_sai("lich_su")
    g = _do_thi(r.get("do_thi"))
    hien = r.get("graph_sha256")
    pbs = []
    for p in r["phien_ban"]:
        if p.get("financial_owner") is not None or p.get("ghi_nhan") != GHI_NHAN_TT:
            _dto_sai("phiên bản mang financial owner / ghi nhận khác")
        pbs.append({**p, "trang_thai": trang_thai(p.get("loai"), p.get("graph_sha256"), hien)})
    return {"schema": SCHEMA, "doi_chieu_id": r["doi_chieu_id"], "khoa_goc_sha256": r.get("khoa_goc_sha256"),
            "module_bien_nhan": r.get("module_bien_nhan"),
            "nguon": g["nguon"], "doi_chieu": {"graph_sha256": hien, "phien_ban": pbs, "bo_tap": list(r.get("bo_tap") or [])},
            "kt": {"thieu_hien_tai": thieu(g, None), "duoc_ghi": r.get("duoc_ghi") is True},
            "ghi_nhan": dict(GHI_NHAN), "request": dict(REQUEST)}


# ================================================================================================== dịch vụ
class GhiNhanChungK2:
    """`nt` = adapter nguồn nghiệm thu (m4/ghi_nhan_nghiem_thu.NguonNghiemThu): kiem_som(dt, cho) trên login thường; khoa_ghim(c, dt, chos, ghi)
    trên giao dịch chủ bảng (khóa 03A theo thứ tự đã sort → producer 03A → kho._dc_nt_ghi). Không có adapter thì nguồn NT bị từ chối."""

    def __init__(self, xd, nt=None):
        self.xd = xd
        self.nt = nt

    # ------------------------------------------------------------------ kiểm sớm (login thường; SQL kiểm lại dưới khóa)
    def _kiem_som(self, dt, refs: list) -> None:
        xd = self.xd
        for r in refs:
            if r["kind"] == "NT":
                if self.nt is None:
                    raise DataError("DC_PHAM_VI", "Chưa nối adapter nguồn nghiệm thu.")
                self.nt.kiem_som(dt, r["occurrence_id"])
            else:
                with xd._tx(dt):
                    ok = (xd._mot("SELECT kho.dc_doc_hoa_don(%s::uuid) AS ok", (r["occurrence_id"],)) or {}).get("ok")
                if not ok:
                    raise DataError("DC_KHONG_THAY", "Không thấy hóa đơn (hoặc ngoài phạm vi M2_READ hiện hành).")

    def _ghim(self, c, dt, refs_json: str, ghi: bool) -> None:
        """Quyền đọc mọi nguồn TRƯỚC (kho._dc_thu_tu_nt raise) → adapter khóa + ghim producer 03A từng NT theo thứ tự HĐ → gốc."""
        chos = (self.xd._r1(c, "SELECT kho._dc_thu_tu_nt(%s::jsonb) AS d", (refs_json,)) or {}).get("d") or []
        if chos:
            if self.nt is None:
                raise DataError("DC_PHAM_VI", "Chưa nối adapter nguồn nghiệm thu.")
            self.nt.khoa_ghim(c, dt, [str(x) for x in chos], ghi)

    def _refs_goc(self, c, goc: str, phien_ban: str | None) -> list:
        return (self.xd._r1(c, "SELECT kho._dc_nguon_cua(%s::uuid, %s::uuid) AS r", (goc, phien_ban)) or {}).get("r") or []

    # ------------------------------------------------------------------ đọc
    def xem_doi_chieu(self, dang_nhap: str, body=None, **kw) -> dict:
        refs = yeu_cau_xem(self._body(body, kw))
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        self._kiem_som(dt, refs)
        rj = json.dumps(refs, ensure_ascii=False)
        with xd._tx_review(dt) as c:
            self._ghim(c, dt, rj, False)
            r = xd._r1(c, "SELECT kho._dc_xem(%s::jsonb) AS r", (rj,))
        return xem_dto((r or {}).get("r"))

    def lich_su(self, dang_nhap: str, doi_chieu_id) -> dict:
        goc = _uuid(doi_chieu_id, "doi_chieu_id")
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        with xd._tx_review(dt) as c:
            refs = self._refs_goc(c, goc, None)
            self._ghim(c, dt, json.dumps(refs, ensure_ascii=False), False)
            r = xd._r1(c, "SELECT kho._dc_lich_su(%s::uuid) AS r", (goc,))
        return lich_su_dto((r or {}).get("r"))

    # ------------------------------------------------------------------ lệnh (MỘT giao dịch chủ bảng: refs → quyền → khóa/ghim → SQL)
    def luu_doi_chieu(self, dang_nhap: str, body=None, **kw) -> dict:
        yc = yeu_cau_luu(self._body(body, kw))
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        refs = [t["nguon"] for t in yc["thanh_phan"]]
        self._kiem_som(dt, refs)
        khoa = yc.pop("khoa")
        than = json.dumps(yc, ensure_ascii=False)
        with xd._chua_ro():
            with xd._tx_review(dt) as c:
                hop = refs
                if yc["doi_chieu_id"] is not None:  # quyền đọc mọi nguồn của mọi revision TRƯỚC; closure = revision mới nhất ∪ yêu cầu (SQL kiểm lại dưới khóa)
                    hop = hop_refs(refs, self._refs_goc(c, yc["doi_chieu_id"], None))
                self._ghim(c, dt, json.dumps(hop, ensure_ascii=False), True)
                r = xd._r1(c, "SELECT kho.dc_luu(%s, %s::jsonb) AS r", (khoa, than))
        return ack_dto((r or {}).get("r"), khoa)

    def xac_nhan_doi_chieu(self, dang_nhap: str, body=None, **kw) -> dict:
        yc = yeu_cau_xac_nhan(self._body(body, kw))
        xd = self.xd
        dt = xd.danh_tinh(dang_nhap)
        khoa = yc.pop("khoa")
        than = json.dumps(yc, ensure_ascii=False)
        with xd._chua_ro():
            with xd._tx_review(dt) as c:
                refs = hop_refs(self._refs_goc(c, yc["doi_chieu_id"], yc["phien_ban_id"]), self._refs_goc(c, yc["doi_chieu_id"], None))
                self._ghim(c, dt, json.dumps(refs, ensure_ascii=False), True)
                r = xd._r1(c, "SELECT kho.dc_xac_nhan(%s, %s::jsonb) AS r", (khoa, than))
        return ack_dto((r or {}).get("r"), khoa)

    @staticmethod
    def _body(body, kw) -> dict:
        if body is not None and kw:
            _yc_sai("Gửi body một lần (object hoặc tham số tên), không trộn.")
        return kw if body is None else body
