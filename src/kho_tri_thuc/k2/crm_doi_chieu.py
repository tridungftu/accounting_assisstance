"""CRM G5-B — đối chiếu bản ký ↔ bản sinh (thủ công + khai Có bắt buộc) trên CHÍNH chuỗi CrmKiemHdK2 → CrmKyKetK2 → CrmGiaoKetK2 → CrmMauK2:
cùng kho/kết nối chủ bảng/danh tính GUC/biên nhận. Hàm SQL ``CRM_G5_SQL`` (k2/sql_crm_doi_chieu.py) quyết định quyền/phạm vi/lease/CAS/công bố;
service chỉ dựng expected từ ĐÚNG revision đã ký (r.du_lieu của crm_hd_ky.soan_rev_id) + catalog/mapping đã đăng ký, gọi MỘT engine Source6
(client ``app.trich6_client`` — biến thể E5 ``doi_chieu_ban_ky``) NGOÀI giao dịch/khóa, và kiểm envelope niêm phong trước khi công bố.

- Trình duyệt chỉ gửi ky_id + expected_context_sha256 + khóa. KHÔNG expected/catalog/actor/PN/principal/kết quả/chế độ/đường dẫn.
- Việc bắt buộc chạy dưới người chạy CẤU HÌNH (crm_g5_nguoi_chay) — thiếu/thu hồi → CHO_CAU_HINH giữ việc; không fallback người tạo/ký/CFO.
- Chuỗi A (nhận + ghi ý định, ngắn, dưới khóa) → B (engine, ngoài khóa/giao dịch) → C (công bố, ngắn, dưới khóa + kiểm lại quyền/đăng ký).
- Engine chưa ghép E5 / chưa sẵn sàng / catalog chưa đăng ký → CHO_CAU_HINH có lý do; mất ACK → CHUA_RO giữ request_id (đối soát, không chạy lại).
- Việc hệ thống chỉ công bố bằng chứng G5 — không duyệt/kiểm/kích hoạt/ghi sổ.
"""

from __future__ import annotations

import json
import re
import secrets
import threading
from contextlib import contextmanager

from ..ha_tang.primitives import DataError, canonical_json, sha256
from ..ha_tang.store import write_immutable
from .crm_giao_ket import chuan_hoa_truong
from .crm_mau import _h, _khoa, _uuid, _v

CONTRACT = "trich-tham-so-common/v1"
MODE_E5 = "doi_chieu_ban_ky"
KIEU_EXPECTED = "CRM_G5_EXPECTED_V1"
KIEU_BINDING = "CRM_G5_CATALOG_BINDING_V1"
KIEU_G5 = "CRM_G5_COMPARE_RESULT_V1"
KIEU_VIEW = "CRM_G5_VIEW_V1"
KIEU_ACK = "CRM_G5_ACK_V1"
LICH = "crm.lich"
KIEU_THAM_SO = ("text", "so", "ngay", "tien", "bang")
TRANG_THAI_G5 = ("KHOP", "LECH", "CHUA_DOI_CHIEU_DUOC")
LINEAGE_KHOA = ("ky_id", "hop_dong_id", "soan_id", "soan_rev_id", "xuat_id", "mau_phien_ban_id", "anh_xa_id", "revision", "g3_input_sha256",
                "g3_docx_sha256", "g3_pdf_sha256", "ban_do_sha256", "danh_muc_ref", "danh_muc_rev", "danh_muc_digest", "profile_sha256",
                "du_lieu_sha256")
E5_KHOA = frozenset({"contract", "mode", "loai_hop_dong", "catalog_id", "catalog_sha256", "source_sha256", "request_id", "tham_so",
                     "signed_pdf_sha256", "expected", "expected_sha256", "catalog_binding", "catalog_binding_sha256"})
G5_KHOA = frozenset({"kieu", "signed_pdf_sha256", "source_sha256", "expected_sha256", "catalog_binding_sha256", "g3_pdf_sha256", "coverage",
                     "trang_thai", "lech", "thieu"})
LECH_KHOA = frozenset({"ma", "muc", "kieu", "gia_tri_ky_vong", "gia_tri_ban_ky", "trich_dan", "vi_tri_do_duoc"})
ENV_KHOA = frozenset({"luot", "raw_ket_qua", "raw_sha256", "ket_qua", "common", "yeu_cau", "g5"})
# bảng lịch đã ký: thứ tự dòng/cột giữ nguyên; ô giữ đúng giá trị đã lưu (0 ≠ null, tiền tệ tường minh từng dòng; không suy VAT/FX/%)
COT_LICH = ("dong_id", "lan", "loai", "ty_le", "so_tien", "tien_te", "moc_loai", "moc_ngay", "moc_su_kien", "ghi_chu")
# engine/cấu hình chưa sẵn sàng (trước side effect) → CHỜ CẤU HÌNH, không phải lỗi cuối
MA_CHUA_SAN_SANG = frozenset({"E5_CHUA_GHEP", "E5_IMPLEMENTATION_KHAC", "TRICH6_CHUA_SAN_SANG", "TRICH6_KHONG_HO_TRO_COMMON",
                              "TRICH6_LOAI_CHUA_CO_DANH_MUC", "TRICH6_KHONG_KET_NOI", "TRICH6_URL_SAI", "CRM_G5_BAN_KY_KHONG_CO"})
RE_SHA = re.compile(r"[0-9a-f]{64}")
RE_LUOT = re.compile(r"[A-Za-z0-9_.:-]{1,120}")
CHO_CHUA_RO = 300
CHO_CAU_HINH = 900


def _loi(ma: str, msg: str):
    raise DataError(ma, msg)


def sha_obj(x) -> str:
    """SHA-256 canonical JSON (sort_keys, không khoảng trắng, UTF-8) — cùng quy tắc helper Source6."""
    return sha256(canonical_json(x).encode("utf-8"))


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _o_lich(v):
    if v is None or isinstance(v, str) or _int(v):
        return v
    _loi("CRM_G5_EXPECTED_SAI", "Ô lịch đã ký có kiểu không hỗ trợ (chỉ chuỗi/số nguyên/null).")


def bang_lich(lich) -> dict:
    """Lịch đã ký → bảng typed {cot, dong}: giữ thứ tự dòng, đủ cột, 0 khác null, tiền tệ từng dòng tường minh. Không tính/suy giá trị."""
    if lich is None:
        lich = []
    if not isinstance(lich, list) or any(not isinstance(d, dict) for d in lich):
        _loi("CRM_G5_EXPECTED_SAI", "Lịch đã ký không đúng dạng danh sách dòng.")
    return {"cot": list(COT_LICH), "dong": [[_o_lich(d.get(c)) for c in COT_LICH] for d in lich]}


def dung_expected(ky: dict, du_lieu: dict, danh_muc: list, mapping: list) -> dict:
    """CRM_G5_EXPECTED_V1 từ ĐÚNG revision đã ký (r.du_lieu của soan_rev_id ghim ở bản ký) + danh mục đã ghim + mapping đăng ký."""
    if not isinstance(du_lieu, dict) or not isinstance(mapping, list) or not mapping:
        _loi("CRM_G5_EXPECTED_SAI", "Thiếu dữ liệu revision đã ký hoặc mapping đăng ký.")
    dm = {t["khoa"]: t for t in danh_muc or []}
    gt = du_lieu.get("gia_tri_truong") or {}
    bg = du_lieu.get("bao_gia") or {}
    ts = []
    for m in mapping:
        if m.get("crm_truong") == LICH:
            ts.append({"ma": m["ma"], "kieu": "bang", "gia_tri": bang_lich(bg.get("lich"))})
            continue
        t = dm.get(m.get("crm_truong"))
        if t is None or t["kieu"] not in ("text", "so", "ngay", "tien"):
            _loi("CRM_G5_MAPPING_SAI", "Mapping trỏ trường không thuộc danh mục đã ghim của bản ký.")
        ts.append({"ma": m["ma"], "kieu": t["kieu"], "gia_tri": chuan_hoa_truong(t["kieu"], gt.get(m["crm_truong"]))})
    return {"kieu": KIEU_EXPECTED, "lineage": {k: ky[k] for k in LINEAGE_KHOA}, "tham_so": ts}


def dung_binding(ky: dict, dang_ky: dict) -> dict:
    return {"kieu": KIEU_BINDING, "loai_hop_dong": dang_ky["loai_hop_dong"], "catalog_id": dang_ky["catalog_id"],
            "catalog_sha256": dang_ky["catalog_sha256"], "danh_muc_ref": ky["danh_muc_ref"], "danh_muc_rev": ky["danh_muc_rev"],
            "danh_muc_digest": ky["danh_muc_digest"], "mau_phien_ban_id": ky["mau_phien_ban_id"], "profile_sha256": ky["profile_sha256"],
            "mapping": dang_ky["mapping"]}


def body_e5(ky: dict, dang_ky: dict, request_id: str, expected: dict, binding: dict) -> dict:
    """Body E5 đúng 13 trường. source_sha256 = signed_pdf_sha256 = PDF BẢN KÝ gốc; PDF G3 chỉ nằm trong expected.lineage (vai riêng)."""
    return {"contract": CONTRACT, "mode": MODE_E5, "loai_hop_dong": dang_ky["loai_hop_dong"], "catalog_id": dang_ky["catalog_id"],
            "catalog_sha256": dang_ky["catalog_sha256"], "source_sha256": ky["ky_pdf_sha256"], "request_id": request_id,
            "tham_so": [m["ma"] for m in dang_ky["mapping"]], "signed_pdf_sha256": ky["ky_pdf_sha256"], "expected": expected,
            "expected_sha256": sha_obj(expected), "catalog_binding": binding, "catalog_binding_sha256": sha_obj(binding)}


def sha_body(body: dict) -> str:
    if set(body) != E5_KHOA:
        _loi("CRM_G5_Y_DINH_SAI", "Body E5 phải đúng 13 trường.")
    return sha_obj(body)


def kiem_g5(g5, y: dict) -> dict:
    """Kiểm kết quả g5 nghiêm ngặt so với ý định đã ghi (expected/binding/PDF). Sai cấu trúc → CRM_G5_KET_QUA_SAI (không công bố).
    KHOP chỉ khi phủ đủ + 0 lệch; LECH khi phủ đủ + ≥1 lệch có trích dẫn/vị trí thật; còn lại CHUA_DOI_CHIEU_DUOC (giữ lệch một phần)."""
    def sai(msg):
        _loi("CRM_G5_KET_QUA_SAI", msg)
    if not isinstance(g5, dict) or set(g5) != G5_KHOA:
        sai("g5 phải đúng 10 khóa CRM_G5_COMPARE_RESULT_V1.")
    exp, bd = y["expected"], y["binding"]
    if g5["kieu"] != KIEU_G5 or g5["signed_pdf_sha256"] != y["ky_pdf_sha256"] or g5["source_sha256"] != y["ky_pdf_sha256"] \
            or g5["expected_sha256"] != y["expected_sha256"] or g5["catalog_binding_sha256"] != y["binding_sha256"] \
            or g5["g3_pdf_sha256"] != y["g3_pdf_sha256"]:
        sai("g5 không khớp SHA bản ký/expected/binding/G3 của ý định.")
    if g5["trang_thai"] not in TRANG_THAI_G5:
        sai("Trạng thái g5 không hợp lệ.")
    ma = [t["ma"] for t in exp["tham_so"]]
    tham_so = {t["ma"]: t for t in exp["tham_so"]}
    muc = {m["ma"]: m["muc"] for m in bd["mapping"]}
    cov, thieu, lech = g5["coverage"], g5["thieu"], g5["lech"]
    for ds in (cov, thieu):
        if not isinstance(ds, list) or any(not isinstance(x, str) or x not in tham_so for x in ds) or len(set(ds)) != len(ds):
            sai("coverage/thieu phải là mã đã yêu cầu, không trùng.")
    if set(cov) & set(thieu):
        sai("coverage và thieu giao nhau.")
    if not isinstance(lech, list):
        sai("lech phải là danh sách.")
    da = set()
    for e in lech:
        if not isinstance(e, dict) or set(e) != LECH_KHOA:
            sai("Mỗi lệch phải đúng 7 khóa.")
        m = e["ma"]
        if not isinstance(m, str) or m not in cov or m in da:
            sai("Lệch phải thuộc mã đã phủ, không trùng.")
        da.add(m)
        if not _int(e["muc"]) or e["muc"] != muc[m]:
            sai("Mức lệch phải đúng mức catalog đã ghim.")
        if e["kieu"] != tham_so[m]["kieu"] or e["gia_tri_ky_vong"] != tham_so[m]["gia_tri"]:
            sai("Giá trị/kiểu kỳ vọng của lệch khác expected đã ghi.")
        if g5["trang_thai"] == "LECH":
            vt = e["vi_tri_do_duoc"]
            if not isinstance(e["trich_dan"], str) or not e["trich_dan"].strip() or not isinstance(vt, (str, dict, list)) or vt in ("", {}, []):
                sai("LECH cần trích dẫn + vị trí đo được thật từ bản ký.")
    du = set(cov) == set(ma) and not thieu
    if g5["trang_thai"] == "KHOP" and not (du and not lech):
        sai("KHOP chỉ khi phủ đủ và 0 lệch.")
    if g5["trang_thai"] == "LECH" and not (du and lech):
        sai("LECH chỉ khi phủ đủ và ít nhất một lệch.")
    return g5


def _cj(x) -> str:
    try:
        return canonical_json(x)
    except (TypeError, ValueError):
        _loi("CRM_G5_KET_QUA_SAI", "Kết quả engine chứa giá trị không biểu diễn được bằng JSON chuẩn.")


def kiem_envelope(env, body: dict, y: dict, implementation_sha256: str) -> tuple[dict, bytes, str, str]:
    """Envelope client E5 (cùng dạng `.trich()` + g5): yêu cầu = body 13 trường đã ghi; raw đúng SHA và parse ra đúng ket_qua; g5 nhất quán;
    implementation niêm phong = đăng ký. Trả (g5, raw, raw_sha256, luot).
    g5 được kiểm là g5 BÊN TRONG raw niêm phong (bắt buộc có, object JSON) — không suy từ envelope ngoài; so canonical (1 ≠ 1.0, true ≠ 1)."""
    if not isinstance(env, dict) or set(env) != ENV_KHOA:
        _loi("CRM_G5_KET_QUA_SAI", "Envelope engine không đúng dạng E5.")
    if env["yeu_cau"] != body:
        _loi("CRM_G5_KET_QUA_SAI", "Envelope mang yêu cầu khác body đã ghi.")
    raw, h, luot = env["raw_ket_qua"], env["raw_sha256"], env["luot"]
    if not isinstance(raw, (bytes, bytearray)) or not raw or not isinstance(h, str) or sha256(bytes(raw)) != h:
        _loi("CRM_G5_KET_QUA_SAI", "Raw kết quả khác SHA niêm phong.")
    if not isinstance(luot, str) or not RE_LUOT.fullmatch(luot):
        _loi("CRM_G5_KET_QUA_SAI", "Mã lượt engine không hợp lệ.")
    try:
        kq = json.loads(bytes(raw).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        _loi("CRM_G5_KET_QUA_SAI", "Raw kết quả không phải JSON.")
    if not isinstance(kq, dict) or "g5" not in kq:
        _loi("CRM_G5_KET_QUA_SAI", "Raw niêm phong không phải object hoặc thiếu g5 — không suy g5 từ envelope ngoài.")
    if _cj(kq) != _cj(env["ket_qua"]) or _cj(kq["g5"]) != _cj(env["g5"]):
        _loi("CRM_G5_KET_QUA_SAI", "ket_qua/g5 khác raw đã niêm phong.")
    common = env["common"]
    if not isinstance(common, dict) or common.get("implementation_sha256") != implementation_sha256:
        _loi("E5_IMPLEMENTATION_KHAC", "Implementation niêm phong của engine khác implementation đã đăng ký — chưa công bố.")
    return kiem_g5(kq["g5"], y), bytes(raw), h, luot


def _goi(fn, *a):
    return fn(*a)


class CrmDoiChieuK2:
    """G5-B trên CHÍNH CrmKiemHdK2. ``client_fn(goc)`` = ``app.trich6_client`` (một client Source6 dùng chung); None → CHO_CAU_HINH."""

    def __init__(self, kiem, client_fn=None, *, lease_giay: int = 2400):
        self.kiem = kiem
        self.ky = kiem.ky
        self.mau = kiem.mau
        self.kho = self.ky.gk.kho / "doi-chieu"
        self.client_fn = client_fn
        self.lease_giay = lease_giay
        self.lease_boi = "g5w-" + secrets.token_hex(8)  # định danh worker của tiến trình này (lease hữu hạn; khởi động lại = định danh mới)

    # ------------------------------------------------------------------ lệnh/đọc người dùng (dưới mutation lock của caller)
    def doc(self, dang_nhap: str, ky_id) -> dict:
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            return _v(dict(c.execute("SELECT master.crm_g5_doc(%s::uuid) AS r", (_uuid(ky_id, "ky_id"),)).fetchone()))["r"]

    def _lenh(self, dang_nhap: str, ham: str, hanh: str, ky_id, ctx, khoa) -> dict:
        kid, khoa = _uuid(ky_id, "ky_id"), _khoa(khoa)
        if not isinstance(ctx, str) or not RE_SHA.fullmatch(ctx):
            _loi("CRM_G_YEU_CAU_SAI", "Thiếu expected_context_sha256 (lấy từ màn hình đối chiếu).")
        h = _h(hanh, {"ky_id": kid, "expected_context_sha256": ctx})
        m, dt = self.mau, self.mau.danh_tinh(dang_nhap)
        with m._tx(dt) as c:
            r = _v(dict(c.execute(f"SELECT master.{ham}(%s, %s, %s::uuid, %s) AS r", (khoa, h, kid, ctx)).fetchone()))["r"]
        return {**r["ket_qua"], "replay": bool(r["lap_lai"])}

    def chay(self, dang_nhap: str, *, ky_id, expected_context_sha256, khoa) -> dict:
        return self._lenh(dang_nhap, "crm_g5_chay", "CRM_G5_CHAY", ky_id, expected_context_sha256, khoa)

    def doi_soat(self, dang_nhap: str, *, ky_id, expected_context_sha256, khoa) -> dict:
        return self._lenh(dang_nhap, "crm_g5_doi_soat", "CRM_G5_DOI_SOAT", ky_id, expected_context_sha256, khoa)

    # ------------------------------------------------------------------ worker: pha A (ngắn, dưới khóa)
    def hang_doi(self, toi_da: int = 5) -> list:
        c = self.mau._c()
        with c.transaction():
            return _v(dict(c.execute("SELECT master.crm_g5_hang_doi(%s) AS r", (toi_da,)).fetchone()))["r"]

    @contextmanager
    def _tx_nguoi(self, dang_nhap):
        """Giao dịch dưới danh tính người chạy; danh tính không nạp được → giao dịch KHÔNG danh tính (SQL ghi CHO_CAU_HINH, không mượn ai khác)."""
        try:
            dt = self.mau.danh_tinh(dang_nhap) if dang_nhap else None
        except DataError:
            dt = None
        if dt is not None:
            with self.mau._tx(dt) as c:
                yield c
            return
        c = self.mau._c()
        with c.transaction():
            yield c

    def nhan(self, muc: dict) -> dict:
        with self._tx_nguoi(muc["nguoi_chay"]) as c:
            p = _v(dict(c.execute("SELECT master.crm_g5_nhan(%s::uuid, %s, %s) AS r",
                                  (muc["viec_id"], self.lease_boi, self.lease_giay)).fetchone()))["r"]
        return {**p, "nguoi_chay": muc["nguoi_chay"]}

    def chuan_bi(self, p: dict) -> dict:
        """Dựng expected/binding/body từ dữ liệu ĐÃ KÝ do SQL trả trong giao dịch nhận, rồi ghi ý định bất biến TRƯỚC khi gọi engine."""
        ky, dk = p["ky"], p["dang_ky"]
        exp = dung_expected(ky, p["du_lieu"], p["danh_muc"], dk["mapping"])
        bd = dung_binding(ky, dk)
        body = body_e5(ky, dk, p["request_id"], exp, bd)
        hb = sha_body(body)
        y = p.get("y_dinh")
        if y is not None and (y["expected_sha256"], y["binding_sha256"], y["body_sha256"]) != (body["expected_sha256"], body["catalog_binding_sha256"], hb):
            _loi("CRM_G5_Y_DINH_KHAC", "Ý định đã ghi khác yêu cầu dựng lại từ bản ký — không dùng lại khóa.")
        m, dt = self.mau, self.mau.danh_tinh(p["nguoi_chay"])
        with m._tx(dt) as c:
            r = _v(dict(c.execute("SELECT master.crm_g5_ghi_y_dinh(%s::uuid, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s) AS r",
                                  (p["viec_id"], p["the_he"], self.lease_boi, json.dumps(exp, ensure_ascii=False), body["expected_sha256"],
                                   json.dumps(bd, ensure_ascii=False), body["catalog_binding_sha256"], json.dumps(body, ensure_ascii=False), hb)
                                  ).fetchone()))["r"]
        return {**p, "expected": exp, "binding": bd, "body": body, "body_sha256": hb, "y_dinh_id": r["y_dinh_id"]}

    # ------------------------------------------------------------------ worker: pha B (engine NGOÀI khóa/giao dịch)
    def goi_engine(self, p: dict) -> tuple[str, object]:
        """('KET_QUA', (g5, raw, sha, luot)) | ('CHUA_RO', mã) | ('CHO_CAU_HINH', mã) | ('LOI', mã). Không giữ kết nối/khóa."""
        from ..nguon.trich_chung_6 import ChuaRo
        ky = p["ky"]
        try:
            pth = self.ky.kho_ky / ky["ky_pdf_sha256"]
            if not RE_SHA.fullmatch(ky["ky_pdf_sha256"]) or not pth.is_file():
                _loi("CRM_G5_BAN_KY_KHONG_CO", "PDF bản ký không có trong kho.")
            raw = pth.read_bytes()
            if sha256(raw) != ky["ky_pdf_sha256"] or len(raw) != int(ky["ky_pdf_len"]):
                return "LOI", "CRM_G_TEP_HONG"
            client = self.client_fn(self.kho) if self.client_fn is not None else None
            fn = getattr(client, "doi_chieu_ban_ky", None)
            if client is None or not callable(fn):
                _loi("E5_CHUA_GHEP", "Client Source6 chưa có biến thể E5 doi_chieu_ban_ky — chưa đối chiếu.")
            if not getattr(client, "san_sang", False):
                _loi("TRICH6_CHUA_SAN_SANG", "Engine Source6 chưa sẵn sàng.")
            b = p["body"]
            env = fn(raw, ten_tep=ky["ten_tep"], loai_hop_dong=b["loai_hop_dong"], tham_so=list(b["tham_so"]), request_id=b["request_id"],
                     expected=b["expected"], expected_sha256=b["expected_sha256"], catalog_binding=b["catalog_binding"],
                     catalog_binding_sha256=b["catalog_binding_sha256"])
            y = {"expected": b["expected"], "binding": b["catalog_binding"], "expected_sha256": b["expected_sha256"],
                 "binding_sha256": b["catalog_binding_sha256"], "ky_pdf_sha256": ky["ky_pdf_sha256"], "g3_pdf_sha256": ky["g3_pdf_sha256"]}
            return "KET_QUA", kiem_envelope(env, b, y, p["dang_ky"]["implementation_sha256"])
        except ChuaRo as exc:
            return "CHUA_RO", exc.code
        except DataError as exc:
            return ("CHO_CAU_HINH" if exc.code in MA_CHUA_SAN_SANG else "LOI"), exc.code
        except Exception as exc:  # lỗi không phân loại SAU khi có thể đã gửi → chưa rõ (giữ request_id, đối soát; không coi là lỗi chắc chắn)
            return "CHUA_RO", "LOI_KHONG_PHAN_LOAI_" + type(exc).__name__.upper()[:40]

    # ------------------------------------------------------------------ worker: pha C (ngắn, dưới khóa)
    def cong_bo(self, p: dict, kq: tuple) -> dict:
        g5, raw, h, luot = kq
        write_immutable(self.kho / "ket-qua" / f"{h}.json", raw)  # raw bất biến theo SHA — không chép vào master
        m, dt = self.mau, self.mau.danh_tinh(p["nguoi_chay"])
        with m._tx(dt) as c:
            return _v(dict(c.execute(
                "SELECT master.crm_g5_cong_bo(%s::uuid, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s) AS r",
                (p["viec_id"], p["the_he"], self.lease_boi, g5["trang_thai"], json.dumps(g5["coverage"], ensure_ascii=False),
                 json.dumps(g5["lech"], ensure_ascii=False), json.dumps(g5["thieu"], ensure_ascii=False), json.dumps(g5, ensure_ascii=False),
                 h, len(raw), luot)).fetchone()))["r"]

    def ket_thuc(self, p: dict, trang_thai: str, ly_do: str, cho_giay: int) -> dict:
        ly = re.sub(r"[^A-Z0-9_]", "_", str(ly_do or "KHONG_RO").upper())[:80] or "KHONG_RO"
        with self._tx_nguoi(p["nguoi_chay"]) as c:
            return _v(dict(c.execute("SELECT master.crm_g5_ket_thuc(%s::uuid, %s, %s, %s, %s, %s) AS r",
                                     (p["viec_id"], p["the_he"], self.lease_boi, trang_thai, ly, cho_giay)).fetchone()))["r"]

    def chay_mot(self, muc: dict, lock, db=_goi) -> dict:
        """Một việc: A (nhận + ý định, dưới khóa) → B (engine ngoài khóa) → C (công bố/kết thúc, dưới khóa). Lỗi CSDL qua ``db`` (app._crm_db)."""
        with lock:
            p = db(self.nhan, muc)
        if not p.get("nhan"):
            return p
        try:
            with lock:
                p = db(self.chuan_bi, p)
        except DataError as exc:
            if exc.code == "CRM_G5_LEASE_MAT":
                return {"nhan": True, "ket_thuc": "LEASE_MAT"}
            with lock:
                return db(self.ket_thuc, p, "LOI", exc.code, CHO_CAU_HINH)
        loai, kq = self.goi_engine(p)
        with lock:
            if loai == "KET_QUA":
                try:
                    return db(self.cong_bo, p, kq)
                except DataError as exc:
                    if exc.code == "CRM_G5_LEASE_MAT":
                        return {"nhan": True, "ket_thuc": "LEASE_MAT"}
                    # quyền/người chạy/đăng ký đổi trước công bố → chờ cấu hình (raw đã giữ; lần nhận sau đổi thế hệ nếu đăng ký đổi)
                    return db(self.ket_thuc, p, "CHO_CAU_HINH", exc.code, CHO_CAU_HINH)
            if loai == "CHUA_RO":
                return db(self.ket_thuc, p, "CHUA_RO", kq, CHO_CHUA_RO)
            if loai == "CHO_CAU_HINH":
                return db(self.ket_thuc, p, "CHO_CAU_HINH", kq, CHO_CAU_HINH)
            return db(self.ket_thuc, p, "LOI", kq, CHO_CAU_HINH)


class HangDoiG5:
    """Một worker nền trong tiến trình (daemon) cho hàng đợi BỀN ở CSDL: chu kỳ hữu hạn, lô nhỏ, đánh thức sau G4 commit/lệnh thủ công.
    Trạng thái nghĩa vụ nằm ở CSDL (không ở bộ nhớ/thread/trình duyệt); dừng/chết giữa chừng → lease hết hạn, khởi động lại đối soát tiếp."""

    def __init__(self, dv: CrmDoiChieuK2, lock, *, db=_goi, chu_ky: float = 30.0, lo: int = 5):
        self.dv, self.lock, self.db = dv, lock, db
        self.chu_ky, self.lo = chu_ky, lo
        self._ev = threading.Event()
        self._dung = threading.Event()
        self._t = None
        self.loi_cuoi = None

    def bat_dau(self) -> None:
        if self._t is None:
            self._t = threading.Thread(target=self._vong, name="crm-g5-hang-doi", daemon=True)
            self._t.start()

    def danh_thuc(self) -> None:
        self._ev.set()

    def dung(self, cho: float = 5.0) -> None:
        self._dung.set()
        self._ev.set()
        if self._t is not None:
            self._t.join(cho)

    def mot_luot(self) -> int:
        with self.lock:
            ds = self.db(self.dv.hang_doi, self.lo)
        for muc in ds:
            if self._dung.is_set():
                break
            self.dv.chay_mot(muc, self.lock, self.db)
        return len(ds)

    def _vong(self) -> None:
        while not self._dung.is_set():
            try:
                n = self.mot_luot()
                self.loi_cuoi = None
            except Exception as exc:  # hàng đợi bền: lỗi chu kỳ không mất việc; thử lại chu kỳ sau
                n, self.loi_cuoi = 0, getattr(exc, "code", type(exc).__name__)
            if n >= self.lo and not self._dung.is_set():
                continue  # còn việc đến hạn: xử lý tiếp lô kế
            self._ev.wait(self.chu_ky)
            self._ev.clear()
