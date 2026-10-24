"""M2-00B — điều phối tải hóa đơn #7 theo phiên + quyền HIỆN HÀNH (seam máy chủ nội bộ; route/cookie/nút ở wiring sau).

Không có hệ quyền/master/role riêng, không callback/fake auth mặc định. Mỗi thao tác:
1. `app.crm_phien(sid)` hiện hành → login (actor KHÔNG từ payload). Session ref = SHA-256 của sid (không lưu cookie thô).
2. RLock ngắn của B quanh phần DB/phiên/trạng thái điều phối (KHÔNG giữ suốt request Node/SSE). Trong giao dịch `HoaDonK2._tx` trên CHÍNH
   app connection (`app.m2().conn is app.crm().conn`): `master.ktt_danh_tinh()` phải đúng login, nạp lại `dt` trong giao dịch, rồi
   `nguon_chung.doc_profile/doc_pham_vi`, `quyen.kiem_nguon` INTAKE + READ_SOURCE, `HoaDonK2._cong_ty` (mapping COMPANY hiện hành → PN uuid +
   `fact.pn_alias`, kiểm lại `master.phap_nhan`), `quyen.kiem(dt, 'M2_READ', pn)` và `master.ktt_duoc(pn, 'M2')`. Thiếu bất kỳ → từ chối,
   0 credential/portal/artifact IO.
3. Context A `m2_00a.source7.run_context.v1` đúng schema `manifest.js:197–239`: profile.ref = mã PN đã resolve (tệp `<MA>.env`),
   profile.revision = SHA-256 canonical của source profile hiện hành; `binding.selection_digest` bind session ref + actor + PN + source
   profile + instance/scope/company/mapping + lựa chọn. Nhật ký `nhat_ky.su_kien` qua `CrmK2._su_kien` TRONG cùng giao dịch đã kiểm quyền.
4. Binding điều phối bất biến (`write_immutable`): chỉ context an toàn/hash/refs. Cùng khóa (actor, PN, client_key) → cùng nonce/run;
   phiên khác → CAN_DOI_SOAT, 0 start; lựa chọn khác → xung đột. Intent/receipt của producer A là nguồn quyết định replay/UNKNOWN.
5. Kiểm lại phiên + quyền trước VÀ sau mọi IO Node, trước mỗi chunk SSE; mất quyền/đổi vai/đổi profile → không trả kết quả, dừng hữu hạn
   công việc sở hữu đang chạy (giữ tệp/intent → UNKNOWN), không tự cấp lại/không chạy lại mù.
"""

from __future__ import annotations

import json
import re
import secrets
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from ...ha_tang.primitives import DataError, sha256
from ...ha_tang.store import write_immutable
from ...k2 import nguon_chung, quyen
from .cau_hinh import CauHinhTaiHoaDon
from .khach import LoiKhach
from .tien_trinh import LoiTienTrinh, TienTrinhNode

SCHEMA_CONTEXT = "m2_00a.source7.run_context.v1"
SCHEMA_SELECTION = "m2_00b.selection.v1"
SCHEMA_BINDING = "m2_00b.binding.v1"
MODULE = "M2"
LOAI_NHAT_KY = "NGUON_TU_DONG"
BANG_NHAT_KY = "m2_00b.tai_hoa_don"
KHOA_CHON = ("source_instance", "scope_ref", "company_key", "mode", "year", "month", "types", "formats", "client_key")
KHOA_BINDING = ("schema", "binding_key", "sid_ref", "actor_id", "phap_nhan", "source_instance", "scope_ref", "company_key", "client_key",
                "request", "selection_digest", "context", "context_digest", "tao_luc")
LOAI = ("purchase", "sold")
DINH_DANG = ("xml", "pdf", "excel")
RE_INSTANCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")
RE_COMPANY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
RE_KHOA = re.compile(r"[A-Za-z0-9_-]{8,64}")
RE_MA_PN = re.compile(r"[A-Z0-9][A-Z0-9_-]{0,31}")
RE_WIN_RESERVED = re.compile(r"(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])", re.I)
RE_HEX64 = re.compile(r"[0-9a-f]{64}")
RE_RUN_REL = re.compile(r"([A-Z0-9][A-Z0-9_-]{0,31})/(\d{4}-(?:0[1-9]|1[0-2]))/(mua_vao|ban_ra)/(\d{8}-\d{6})")
BINDING_TOI_DA = 64 * 1024
_VN = timezone(timedelta(hours=7))


def canon(v) -> str:
    """JSON chuẩn = `manifest.canonicalJson` của A cho miền ASCII/int/null/bool của context (khóa sắp xếp, không khoảng trắng)."""
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def bam(v) -> str:
    return sha256(canon(v).encode("utf-8"))


def context_digest(ctx: dict) -> str:
    return bam(ctx)


def _gia_tri(row, key):
    return row[key] if isinstance(row, dict) else row[0]


def _tap_con(v, cho_phep) -> bool:
    return isinstance(v, list) and 0 < len(v) <= len(cho_phep) and all(isinstance(x, str) and x in cho_phep for x in v) and len(set(v)) == len(v)


def kiem_lua_chon(sel) -> tuple:
    """Body chọn ĐÓNG: đúng 9 khóa; actor/PN/ref/revision/đường dẫn/roots không bao giờ nhận từ trình duyệt."""
    if not isinstance(sel, dict) or set(sel) != set(KHOA_CHON):
        raise DataError("M2_00B_CHON_SAI", "Lựa chọn tải chỉ gồm instance/scope/company key/kỳ/chiều/định dạng/khóa thao tác.")
    inst, scope, cty, key = sel["source_instance"], sel["scope_ref"], sel["company_key"], sel["client_key"]
    if not (isinstance(inst, str) and RE_INSTANCE.fullmatch(inst) and isinstance(scope, str) and RE_INSTANCE.fullmatch(scope)
            and isinstance(cty, str) and RE_COMPANY.fullmatch(cty)):
        raise DataError("M2_00B_CHON_SAI", "Instance/scope/company key không hợp lệ.")
    if not isinstance(key, str) or not RE_KHOA.fullmatch(key):
        raise DataError("M2_00B_KHOA_SAI", "Khóa thao tác phải 8–64 ký tự [A-Za-z0-9_-].")
    mode, year, month = sel["mode"], sel["year"], sel["month"]
    if mode not in ("month", "year") or type(year) is not int or not 2020 <= year <= 2100:
        raise DataError("M2_00B_KY_SAI", "Chế độ/năm không hợp lệ.")
    if (mode == "month" and (type(month) is not int or not 1 <= month <= 12)) or (mode == "year" and month is not None):
        raise DataError("M2_00B_KY_SAI", "Tháng không hợp lệ cho chế độ đã chọn.")
    if not _tap_con(sel["types"], LOAI) or not _tap_con(sel["formats"], DINH_DANG):
        raise DataError("M2_00B_CHON_SAI", "Chiều/định dạng phải là tập con không lặp của danh sách cho phép.")
    request = {"mode": mode, "year": year, "month": month, "types": list(sel["types"]), "formats": list(sel["formats"])}
    return inst, scope, cty, request, key


class DieuPhoiTaiHoaDon:
    def __init__(self, app, cau_hinh: CauHinhTaiHoaDon, *, tien_trinh=None, dong_ho=None, sinh_nonce=None, ngu=time.sleep):
        for ten in ("crm_phien", "m2", "crm"):
            if not callable(getattr(app, ten, None)):
                raise DataError("M2_00B_CHUA_CAU_HINH", "Thiếu app.crm_phien/app.m2/app.crm của máy chủ.")
        if not isinstance(cau_hinh, CauHinhTaiHoaDon):
            raise DataError("M2_00B_CHUA_CAU_HINH", "Cần CauHinhTaiHoaDon do máy chủ cấp.")
        self._app, self.cau_hinh = app, cau_hinh
        self._tt = tien_trinh if tien_trinh is not None else TienTrinhNode(cau_hinh)  # khởi tạo KHÔNG spawn
        self._dong_ho = dong_ho or (lambda: datetime.now(_VN))
        self._sinh_nonce = sinh_nonce or (lambda: secrets.token_urlsafe(24))
        self._ngu = ngu
        self._khoa = threading.RLock()
        self._binding: dict[str, dict] = {}
        self._dang_chay: str | None = None
        self._thu_hoi: set[str] = set()
        self._da_ghi_ket_thuc: set[str] = set()
        self._goc_binding = cau_hinh.goc_dieu_phoi / "m2-00b-binding"

    # ------------------------------------------------------------------ vòng đời Node (gọi tường minh từ wiring)
    def khoi_dong(self) -> dict:
        try:
            return self._tt.start()
        except LoiTienTrinh as e:
            raise DataError("M2_00B_" + e.ma, "Không khởi động được bộ tải #7 sở hữu.") from None

    def stop(self) -> dict:
        with self._khoa:
            self._dang_chay = None
        try:
            return self._tt.stop()
        except LoiTienTrinh as e:
            return {"trang_thai": "DUNG_CHUA_XAC_NHAN", "ma": e.ma, "chung_dung": self._tt.chung_dung}

    def _khach(self):
        try:
            return self._tt.khach()
        except LoiTienTrinh as e:
            raise DataError("M2_00B_" + e.ma, "Bộ tải #7 sở hữu chưa sẵn sàng (chưa cấu hình/khởi động).") from None

    # ------------------------------------------------------------------ phiên + giao dịch quyền hiện hành
    def _phien(self, sid) -> tuple[str, str]:
        if not isinstance(sid, str) or not sid:
            raise DataError("CRM_PHIEN", "Chưa có phiên.")
        _, login, moi = self._app.crm_phien(sid)
        if moi or not isinstance(login, str) or not login:
            raise DataError("CRM_PHIEN", "Phiên không hợp lệ.")
        return sha256(("m2-00b-sid|" + sid).encode("utf-8")), login

    def _dich_vu(self):
        m2, crm = self._app.m2(), self._app.crm()
        if crm.conn is not m2.conn:
            raise DataError("M2_00B_KET_NOI_KHAC", "Nhật ký K2 và kiểm quyền M2 phải dùng cùng app connection.")
        return m2, crm

    @contextmanager
    def _guard(self, login: str):
        """Một giao dịch trên app connection: danh tính phiên đặt + ktt_danh_tinh() đúng login + dt nạp lại trong giao dịch."""
        m2, crm = self._dich_vu()
        dt0 = m2.danh_tinh(login)
        with m2._tx(dt0):
            ai = _gia_tri(m2.conn.execute("SELECT master.ktt_danh_tinh() AS ai").fetchone(), "ai")
            if ai != login:
                raise DataError("DANH_TINH", "Danh tính phiên không còn hoạt động (ID + login).")
            dt = m2.danh_tinh(login)
            if dt["id"] != dt0["id"]:
                raise DataError("M2_00B_DANH_TINH_DOI", "Danh tính đổi trong lúc kiểm.")
            yield m2, crm, m2.conn, dt

    def _quyet_dinh(self, m2, conn, dt, inst: str, scope_ref: str, company_key: str) -> dict:
        """Quyền nguồn + PN + module trên registry dùng chung. Trả facts đã resolve (không gì từ trình duyệt ngoài ID registry)."""
        profile = nguon_chung.doc_profile(conn, inst)
        if not isinstance(profile["payload"], dict) or profile["payload"].get("module") != MODULE:
            raise DataError("NGUON_PROFILE", "Instance nguồn không phải profile hóa đơn M2.")
        quyen.kiem_nguon(conn, inst, profile["reference_id"], profile["sha256"], "INTAKE")
        quyen.kiem_nguon(conn, inst, profile["reference_id"], profile["sha256"], "READ_SOURCE")
        scope = nguon_chung.doc_pham_vi(conn, inst, profile, scope_ref)
        if scope["scope_kind"] != "INVOICE_SET" or company_key not in scope["company_keys"]:
            raise DataError("NGUON_PHAM_VI", "Company key không thuộc phạm vi INVOICE_SET đã đăng ký.")
        cong_ty, hold = m2._cong_ty(conn, inst, profile, [company_key])
        if company_key not in cong_ty:
            ly_do = hold[0]["reason"] if hold else "PN_MAPPING_ABSENT"
            raise DataError("M2_00B_" + ly_do, "Company key chưa có đúng một mapping COMPANY hiện hành.")
        v = cong_ty[company_key]
        pn, ma = v["phap_nhan_id"], v["fact"].pn_alias
        row = conn.execute("SELECT ma FROM master.phap_nhan WHERE id = %s", (pn,)).fetchone()
        if row is None or _gia_tri(row, "ma") != ma:
            raise DataError("M2_00B_PN_KHONG_KHOP", "Mapping PN không khớp master pháp nhân.")
        if not isinstance(ma, str) or not RE_MA_PN.fullmatch(ma) or RE_WIN_RESERVED.fullmatch(ma) or ma != ma.upper():
            raise DataError("M2_00B_MA_PN_KHONG_DUNG_DUOC", "Mã PN không dùng được làm tên profile #7.")
        quyen.kiem(dt, "M2_READ", pn)
        if not _gia_tri(conn.execute("SELECT master.ktt_duoc(%s::uuid, 'M2') AS ok", (pn,)).fetchone(), "ok"):
            raise DataError("KHONG_CO_QUYEN_MODULE", "CSDL không cho module M2 trên pháp nhân này.")
        if not RE_HEX64.fullmatch(str(profile["sha256"])):
            raise DataError("NGUON_PROFILE_DIGEST", "Source profile digest không đúng dạng.")
        return {"source_instance": inst, "scope_ref": scope_ref, "company_key": company_key, "phap_nhan": {"uuid": str(pn), "ma": ma},
                "source_profile": {"reference_id": profile["reference_id"], "sha256": profile["sha256"]},
                "mapping": {"id": str(v["mapping_id"]), "ref": v["fact"].mapping_ref, "revision": v["fact"].mapping_revision}}

    @staticmethod
    def _selection_digest(sid_ref, dt, facts, request, client_key) -> str:
        return bam({"schema": SCHEMA_SELECTION, "sid_ref": sid_ref, "actor": {"id": dt["id"], "dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"]},
                    "phap_nhan": facts["phap_nhan"], "profile": {"ref": facts["phap_nhan"]["ma"], "revision": facts["source_profile"]["sha256"]},
                    "source_profile": facts["source_profile"], "source_instance": facts["source_instance"], "scope_ref": facts["scope_ref"],
                    "company_key": facts["company_key"], "mapping": facts["mapping"], "request": request, "client_key": client_key})

    @contextmanager
    def _kiem_lai(self, sid, b: dict):
        """Re-resolve sid + login + toàn bộ quyền, so selection digest với binding. Yield (crm, conn, dt) TRONG giao dịch đã kiểm."""
        sid_ref, login = self._phien(sid)
        if sid_ref != b["sid_ref"]:
            raise DataError("M2_00B_CAN_DOI_SOAT", "Run thuộc phiên khác — cần đối soát, không trả kết quả cũ.")
        with self._khoa:
            with self._guard(login) as (m2, crm, conn, dt):
                if dt["id"] != b["actor_id"]:
                    raise DataError("M2_00B_NGU_CANH_DOI", "Actor của phiên đã đổi.")
                facts = self._quyet_dinh(m2, conn, dt, b["source_instance"], b["scope_ref"], b["company_key"])
                if self._selection_digest(sid_ref, dt, facts, b["request"], b["client_key"]) != b["selection_digest"]:
                    raise DataError("M2_00B_NGU_CANH_DOI", "Vai/phiên/profile/mapping/PN đã đổi — kết quả cũ không còn hợp lệ.")
                yield crm, conn, dt

    def _con_hop_le(self, sid, b) -> bool:
        try:
            with self._kiem_lai(sid, b):
                return True
        except Exception:  # mọi lỗi kiểm (DB/phiên/quyền) đều coi là không hợp lệ — fail closed
            return False

    # ------------------------------------------------------------------ nhật ký K2 dùng chung
    def _nhat_ky(self, crm, conn, dt, b: dict, hanh_dong: str, them: dict | None = None):
        """`CrmK2._su_kien` trên CÙNG connection/giao dịch đã kiểm quyền. Chỉ IDs/hash/kỳ/mã — không credential/token/nội dung hóa đơn."""
        if crm.conn is not conn:
            raise DataError("M2_00B_KET_NOI_KHAC", "Nhật ký phải đi trên connection đã kiểm quyền.")
        ctx = b["context"]
        sau = {"run_id": ctx["run"]["run_id"], "request_key_sha256": sha256(ctx["run"]["request_key"].encode("utf-8")),
               "context_digest": b["context_digest"], "company_key": b["company_key"], "source_instance": b["source_instance"],
               "scope_ref": b["scope_ref"], **{k: b["request"][k] for k in ("mode", "year", "month", "types", "formats")}, **(them or {})}
        try:
            crm._su_kien(b["phap_nhan"]["uuid"], dt, LOAI_NHAT_KY, BANG_NHAT_KY, None, hanh_dong, sau=sau,
                         can_cu={"selection_digest": b["selection_digest"], "binding_key": b["binding_key"]})
        except Exception:
            raise DataError("M2_00B_NHAT_KY_LOI", "Không ghi được nhật ký dùng chung.") from None

    def _nhat_ky_sau(self, sid, b, hanh_dong, them) -> str:
        """Nhật ký kết quả SAU IO: kiểm lại quyền trong cùng giao dịch; lỗi → 'UNKNOWN' trung thực (không che, không báo đã ghi)."""
        try:
            with self._kiem_lai(sid, b) as (crm, conn, dt):
                self._nhat_ky(crm, conn, dt, b, hanh_dong, them)
            return "DA_GHI"
        except DataError as e:
            if e.code == "M2_00B_NHAT_KY_LOI":
                return "UNKNOWN"
            raise

    # ------------------------------------------------------------------ binding điều phối bất biến
    def _ghi_binding(self, b: dict):
        write_immutable(self._goc_binding / f"{b['binding_key']}.json", (canon(b) + "\n").encode("utf-8"))
        self._binding[b["binding_key"]] = b

    def _doc_binding(self, key: str) -> dict | None:
        if not isinstance(key, str) or not RE_HEX64.fullmatch(key):
            raise DataError("M2_00B_RUN_HANDLE", "Run handle không hợp lệ.")
        if key in self._binding:
            return self._binding[key]
        p = self._goc_binding / f"{key}.json"
        if not p.is_file():
            return None
        if p.is_symlink() or p.stat().st_size > BINDING_TOI_DA:
            raise DataError("M2_00B_BINDING_HONG", "Binding điều phối không đọc an toàn được — cần đối soát.")
        try:
            b = json.loads(p.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise DataError("M2_00B_BINDING_HONG", "Binding điều phối hỏng — cần đối soát.") from None
        if not isinstance(b, dict) or set(b) != set(KHOA_BINDING) or b["schema"] != SCHEMA_BINDING or b["binding_key"] != key \
                or not isinstance(b["context"], dict) or context_digest(b["context"]) != b["context_digest"] \
                or b["context"].get("binding", {}).get("selection_digest") != b["selection_digest"]:
            raise DataError("M2_00B_BINDING_HONG", "Binding điều phối không khớp hash — cần đối soát.")
        self._binding[key] = b
        return b

    def _binding_cua_phien(self, sid, run_handle) -> dict:
        sid_ref, _ = self._phien(sid)  # phiên TRƯỚC mọi tra cache/tệp binding: phiên sai/hết hạn không đọc, không lộ run có tồn tại
        b = self._doc_binding(run_handle)
        if b is None:
            raise DataError("M2_00B_RUN_KHONG_CO", "Không có run này.")
        if sid_ref != b["sid_ref"]:
            raise DataError("M2_00B_CAN_DOI_SOAT", "Run thuộc phiên khác — cần đối soát.")
        return b

    def _tao_binding(self, sid_ref, dt, facts, request, client_key, sel_digest, key) -> dict:
        now = self._dong_ho()
        nonce = self._sinh_nonce()
        ctx = {"schema": SCHEMA_CONTEXT, "issued_by": "M2_COORDINATOR", "phap_nhan": dict(facts["phap_nhan"]),
               "profile": {"ref": facts["phap_nhan"]["ma"], "revision": facts["source_profile"]["sha256"]},
               "actor": {"id": dt["id"], "nguon": "crm_phien"}, "binding": {"selection_digest": sel_digest},
               "source_instance": facts["source_instance"], "scope_ref": facts["scope_ref"],
               "run": {"run_id": now.strftime("%Y%m%d-%H%M%S"), "nonce": nonce, "request_key": "m2b_" + key},
               "request": dict(request)}
        return {"schema": SCHEMA_BINDING, "binding_key": key, "sid_ref": sid_ref, "actor_id": dt["id"], "phap_nhan": dict(facts["phap_nhan"]),
                "source_instance": facts["source_instance"], "scope_ref": facts["scope_ref"], "company_key": facts["company_key"],
                "client_key": client_key, "request": dict(request), "selection_digest": sel_digest, "context": ctx,
                "context_digest": context_digest(ctx), "tao_luc": now.isoformat(timespec="seconds")}

    # ------------------------------------------------------------------ DTO
    @staticmethod
    def _tom_tat(kq: dict) -> dict:
        out = {"ket_qua": None, "doi_soat": None}
        rc = kq.get("receipt")
        if isinstance(rc, dict) and isinstance(rc.get("runs"), list):
            out["ket_qua"] = {"trang_thai": rc.get("trang_thai"), "receipt_sha256": kq.get("receipt_sha256"),
                              "runs": [{k: r.get(k) for k in ("ky", "chieu", "run_rel", "trang_thai", "loi")}
                                       for r in rc["runs"][:100] if isinstance(r, dict)]}
        rec = kq.get("reconciliation")
        if isinstance(rec, dict) and isinstance(rec.get("runs"), list):
            out["doi_soat"] = {"co_the_doi_soat": rec.get("co_the_doi_soat") is True, "hanh_dong": rec.get("hanh_dong"),
                               "runs": [{k: r.get(k) for k in ("ky", "chieu", "run_rel", "ton_tai", "manifest", "trang_thai_run")}
                                        for r in rec["runs"][:100] if isinstance(r, dict)]}
        return out

    def _dto(self, b: dict, trang_thai: str, kq: dict | None = None, **them) -> dict:
        return {"phien_ban": "m2_00b.run.v1", "run_handle": b["binding_key"], "trang_thai": trang_thai, "run_id": b["context"]["run"]["run_id"],
                "phap_nhan_ma": b["phap_nhan"]["ma"], "company_key": b["company_key"], "yeu_cau": dict(b["request"]),
                **self._tom_tat(kq or {}), **them}

    def _dung_vi_thu_hoi(self, key: str):
        """Mất quyền khi run SỞ HỮU đang chạy: dừng hữu hạn cây owned (A chưa có hủy từng job) — giữ intent/tệp, lần sau đối soát UNKNOWN."""
        with self._khoa:
            self._thu_hoi.add(key)
            if self._dang_chay != key:
                return
            self._dang_chay = None
        try:
            self._tt.stop()
        except LoiTienTrinh:
            pass  # witness giữ trong TienTrinhNode.chung_dung (UNKNOWN), không báo đã dừng

    # ------------------------------------------------------------------ thao tác
    def profiles(self, sid) -> dict:
        """PN/profile được phép của phiên hiện hành (+ sẵn sàng tệp profile do Node kiểm, không credential). Kiểm lại sau IO Node."""
        sid_ref, login = self._phien(sid)
        truoc = self._tap_profiles(login)
        san_sang = {}
        if truoc and self._tt.dang_chay():
            try:
                khach = self._tt.khach()
                cap = sorted({(m["phap_nhan"]["ma"], m["profile_revision"], m["phap_nhan"]["uuid"]) for m in truoc})
                while cap:
                    lo, con, thay = [], [], set()
                    for ma, rev, pn in cap:
                        (con if ma in thay else lo).append((ma, rev, pn))
                        thay.add(ma)
                    for p in khach.profiles([{"ref": ma, "revision": rev, "phap_nhan": {"uuid": pn, "ma": ma}} for ma, rev, pn in lo]):
                        san_sang[(p["ref"], p["revision"])] = (p["san_sang"], p["ly_do"])
                    cap = con
            except (LoiKhach, LoiTienTrinh) as e:
                san_sang = {"_loi": getattr(e, "ma", "NODE_LOI")}
        sid_ref2, login2 = self._phien(sid)
        if (sid_ref2, login2) != (sid_ref, login):
            raise DataError("M2_00B_PHIEN_DOI", "Phiên đổi trong lúc đọc — không trả dữ liệu cũ.")
        sau = self._tap_profiles(login)  # quyền hiện hành SAU IO: chỉ trả giao của hai lần kiểm
        khoa_sau = {(m["source_instance"], m["scope_ref"], m["company_key"], m["profile_revision"], m["phap_nhan"]["uuid"]) for m in sau}
        muc = []
        for m in truoc:
            if (m["source_instance"], m["scope_ref"], m["company_key"], m["profile_revision"], m["phap_nhan"]["uuid"]) not in khoa_sau:
                continue
            ss, ly_do = (False, "NODE_CHUA_SAN_SANG")
            if "_loi" in san_sang:
                ly_do = "NODE_" + san_sang["_loi"]
            elif (m["phap_nhan"]["ma"], m["profile_revision"]) in san_sang:
                ss, ly_do = san_sang[(m["phap_nhan"]["ma"], m["profile_revision"])]
            muc.append({"source_instance": m["source_instance"], "scope_ref": m["scope_ref"], "company_key": m["company_key"],
                        "phap_nhan_ma": m["phap_nhan"]["ma"], "profile_revision": m["profile_revision"], "san_sang": ss, "ly_do": ly_do})
        return {"phien_ban": "m2_00b.profiles.v1", "muc": muc}

    def _tap_profiles(self, login) -> list:
        """Chỉ company/PN đã resolve VÀ authorize hiện hành. Mapping thiếu/mơ hồ không phải quyền nhìn identifier → bỏ hẳn, không lộ key/số lượng."""
        muc = []
        with self._khoa:
            with self._guard(login) as (m2, crm, conn, dt):
                for inst in sorted(m2._instances_m2()):
                    if not isinstance(inst, str) or not RE_INSTANCE.fullmatch(inst):
                        continue
                    try:
                        profile = nguon_chung.doc_profile(conn, inst)
                        if not isinstance(profile["payload"], dict) or profile["payload"].get("module") != MODULE:
                            continue
                        quyen.kiem_nguon(conn, inst, profile["reference_id"], profile["sha256"], "INTAKE")
                        quyen.kiem_nguon(conn, inst, profile["reference_id"], profile["sha256"], "READ_SOURCE")
                    except DataError:
                        continue  # thiếu một phía quyền nguồn → instance không hiện (không lộ scope/PN)
                    scopes = conn.execute("""SELECT scope_ref FROM master.nguon_pham_vi WHERE source_instance_id = %s AND profile_ref = %s
                                             AND profile_sha256 = %s AND scope_kind = 'INVOICE_SET' ORDER BY scope_ref""",
                                          (inst, profile["reference_id"], profile["sha256"])).fetchall()
                    for s in scopes:
                        scope_ref = _gia_tri(s, "scope_ref")
                        if not isinstance(scope_ref, str) or not RE_INSTANCE.fullmatch(scope_ref):
                            continue
                        scope = nguon_chung.doc_pham_vi(conn, inst, profile, scope_ref)
                        cong_ty, _hold = m2._cong_ty(conn, inst, profile, scope["company_keys"])  # hold = chưa resolve PN → không hiện
                        for k in sorted(cong_ty):
                            try:
                                f = self._quyet_dinh(m2, conn, dt, inst, scope_ref, k)
                            except DataError:
                                continue  # PN/module ngoài quyền: không hiện (X không thấy B)
                            muc.append({"source_instance": inst, "scope_ref": scope_ref, "company_key": k, "phap_nhan": f["phap_nhan"],
                                        "profile_revision": f["source_profile"]["sha256"]})
        return muc

    def start(self, sid, selection):
        """Một lựa chọn → một job. Danh sách ('Tải tất cả') → hàng đợi tuần tự, kiểm quyền lại trước MỖI job."""
        if isinstance(selection, list):
            return self.chay_hang_doi(sid, selection)
        return self._start_mot(sid, selection)

    def _start_mot(self, sid, selection) -> dict:
        inst, scope_ref, company_key, request, client_key = kiem_lua_chon(selection)
        sid_ref, login = self._phien(sid)
        khach = self._khach()  # NOT_CONFIGURED/NOT_READY trước mọi DB/nhật ký
        with self._khoa:
            with self._guard(login) as (m2, crm, conn, dt):
                facts = self._quyet_dinh(m2, conn, dt, inst, scope_ref, company_key)
                sel = self._selection_digest(sid_ref, dt, facts, request, client_key)
                key = bam({"schema": "m2_00b.binding_key.v1", "actor": dt["id"], "phap_nhan": facts["phap_nhan"]["uuid"], "client_key": client_key})
                b = self._doc_binding(key)
                if b is not None and b["sid_ref"] != sid_ref:
                    return {"phien_ban": "m2_00b.run.v1", "run_handle": None, "trang_thai": "CAN_DOI_SOAT",
                            "ma": "M2_00B_BINDING_PHIEN_KHAC", "company_key": company_key}
                if b is not None and b["selection_digest"] != sel:
                    raise DataError("M2_00B_KHOA_DA_DUNG", "Khóa thao tác đã dùng cho lựa chọn/ngữ cảnh khác — không ghi đè.")
                moi = b is None
                if moi:
                    b = self._tao_binding(sid_ref, dt, facts, request, client_key, sel, key)
                self._nhat_ky(crm, conn, dt, b, "M2_00B_YEU_CAU_TAI", {"binding_moi": moi})
            if moi:
                self._ghi_binding(b)
        try:
            kq = khach.start(b["context"], b["context_digest"])
        except LoiKhach as e:
            if e.http_status is not None and 400 <= e.http_status < 500:
                self._nhat_ky_sau(sid, b, "M2_00B_START_TU_CHOI", {"ma": e.ma, "http_status": e.http_status})
                raise DataError("M2_00B_" + e.ma, "Bộ tải #7 từ chối yêu cầu.") from None
            nk = self._nhat_ky_sau(sid, b, "M2_00B_START_KHONG_RO", {"ma": e.ma})
            return self._dto(b, "UNKNOWN", None, ma=e.ma, can_doi_soat=True, nhat_ky=nk)
        try:
            with self._kiem_lai(sid, b):
                pass
        except DataError:
            if kq["status"] in ("STARTED", "RUNNING"):
                with self._khoa:
                    self._dang_chay = b["binding_key"]
                self._dung_vi_thu_hoi(b["binding_key"])
            raise
        if kq["status"] in ("STARTED", "RUNNING"):
            with self._khoa:
                self._dang_chay = b["binding_key"]
        nk = self._nhat_ky_sau(sid, b, "M2_00B_KET_QUA_START", {"trang_thai": kq["status"]})
        return self._dto(b, kq["status"], kq, nhat_ky=nk, can_doi_soat=kq["status"] == "UNKNOWN")

    def _sau_io(self, sid, b, fn):
        """Kiểm trước IO → IO Node → kiểm sau IO; mất quyền ở bất kỳ phía nào → dừng run sở hữu (nếu đang chạy) và không trả kết quả."""
        try:
            with self._kiem_lai(sid, b):
                pass
            kq = fn()
            with self._kiem_lai(sid, b):
                pass
            return kq
        except DataError:
            self._dung_vi_thu_hoi(b["binding_key"])
            raise

    def status(self, sid, run_handle) -> dict:
        b = self._binding_cua_phien(sid, run_handle)
        khach = self._khach()
        try:
            kq = self._sau_io(sid, b, lambda: khach.status(b["context"], b["context_digest"]))
        except LoiKhach as e:
            raise DataError("M2_00B_" + e.ma, "Không đọc được trạng thái run.") from None
        them = {}
        if kq["status"] != "RUNNING":
            with self._khoa:
                if self._dang_chay == b["binding_key"]:
                    self._dang_chay = None
                ghi = kq["status"] in ("REPLAY", "UNKNOWN") and b["binding_key"] not in self._da_ghi_ket_thuc
                if ghi:
                    self._da_ghi_ket_thuc.add(b["binding_key"])
            if ghi:
                rc = kq.get("receipt") if isinstance(kq.get("receipt"), dict) else {}
                them["nhat_ky"] = self._nhat_ky_sau(sid, b, "M2_00B_KET_THUC", {"trang_thai": kq["status"],
                                                                               "trang_thai_receipt": rc.get("trang_thai"),
                                                                               "so_run": len(rc.get("runs") or [])})
                if them["nhat_ky"] != "DA_GHI":
                    with self._khoa:
                        self._da_ghi_ket_thuc.discard(b["binding_key"])
        return self._dto(b, kq["status"], kq, can_doi_soat=kq["status"] == "UNKNOWN", **them)

    def reconcile(self, sid, run_handle) -> dict:
        b = self._binding_cua_phien(sid, run_handle)
        khach = self._khach()
        try:
            kq = self._sau_io(sid, b, lambda: khach.reconcile(b["context"], b["context_digest"]))
        except LoiKhach as e:
            raise DataError("M2_00B_" + e.ma, "Không đối soát được run.") from None
        nk = self._nhat_ky_sau(sid, b, "M2_00B_DOI_SOAT", {"trang_thai": kq["status"]})
        return self._dto(b, kq["status"], kq, can_doi_soat=kq["status"] == "UNKNOWN", nhat_ky=nk)

    def events(self, sid, run_handle, cursor: int = 0):
        """Generator sự kiện của đúng run; kiểm quyền hiện hành trước mỗi chunk. Mất quyền → dừng phát + dừng run sở hữu đang chạy."""
        b = self._binding_cua_phien(sid, run_handle)
        khach = self._khach()
        with self._kiem_lai(sid, b):
            pass
        try:
            for ev in khach.events(b["context"], b["context_digest"], cursor, con_hop_le=lambda: self._con_hop_le(sid, b)):
                if "ket_thuc" in ev:
                    if ev["ket_thuc"] == "QUYEN_THAY_DOI":
                        self._dung_vi_thu_hoi(b["binding_key"])
                    yield {"ket_thuc": ev["ket_thuc"]}
                    return
                yield ev
        except LoiKhach as e:
            yield {"ket_thuc": e.ma}

    def mo_thu_muc(self, sid, run_handle, run_rel) -> dict:
        b = self._binding_cua_phien(sid, run_handle)
        m = RE_RUN_REL.fullmatch(run_rel) if isinstance(run_rel, str) else None
        if m is None or m.group(1) != b["phap_nhan"]["ma"] or m.group(4) != b["context"]["run"]["run_id"]:
            raise DataError("M2_00B_RUN_REL_SAI", "Thư mục run không thuộc run này.")
        khach = self._khach()
        try:
            return self._sau_io(sid, b, lambda: khach.open_folder(b["context"], run_rel))
        except LoiKhach as e:
            raise DataError("M2_00B_" + e.ma, "Không mở được thư mục run.") from None

    def chay_hang_doi(self, sid, selections) -> dict:
        """'Tải tất cả': chỉ các lựa chọn đã authorize (cùng shape body), TUẦN TỰ; trước mỗi job kiểm quyền lại; producer A vẫn một job."""
        gh = self.cau_hinh.gioi_han
        if not isinstance(selections, list) or not selections or len(selections) > gh.hang_doi_toi_da:
            raise DataError("M2_00B_HANG_DOI_SAI", "Danh sách tải phải 1–giới hạn lựa chọn.")
        for s in selections:
            kiem_lua_chon(s)
        if len({s["client_key"] for s in selections}) != len(selections):
            raise DataError("M2_00B_HANG_DOI_SAI", "Mỗi lựa chọn cần khóa thao tác riêng.")
        muc, dung = [], False
        for s in selections:
            if dung:
                muc.append({"company_key": s["company_key"], "trang_thai": "CHUA_CHAY"})
                continue
            try:
                r = self._start_mot(sid, s)
                if r["trang_thai"] in ("STARTED", "RUNNING"):
                    r = self._cho_ket_thuc(sid, r["run_handle"])
            except DataError as e:
                muc.append({"company_key": s["company_key"], "trang_thai": "TU_CHOI", "ma": e.code})
                continue
            muc.append(r)
            if r["trang_thai"] in ("RUNNING", "CHUA_KET_THUC"):
                dung = True  # producer còn bận: không xếp chồng job kế tiếp
        return {"phien_ban": "m2_00b.hang_doi.v1", "muc": muc}

    def _cho_ket_thuc(self, sid, run_handle) -> dict:
        """Poll hữu hạn theo SỐ NHỊP (cho_moi_job_s / nhip_poll_s, tối thiểu 0.1 s/nhịp) — tất định, không phụ thuộc đồng hồ."""
        gh = self.cau_hinh.gioi_han
        r = None
        for _ in range(max(1, int(gh.cho_moi_job_s / max(gh.nhip_poll_s, 0.1)))):
            self._ngu(gh.nhip_poll_s)
            r = self.status(sid, run_handle)
            if r["trang_thai"] != "RUNNING":
                return r
        return {**(r or {"run_handle": run_handle}), "trang_thai": "CHUA_KET_THUC"}
