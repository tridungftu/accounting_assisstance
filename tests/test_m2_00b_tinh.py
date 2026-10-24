"""M2-00B tĩnh — DTO/context/selection/binding/idempotency/hàng đợi qua `quyen` + `nguon_chung` + `HoaDonK2`/`CrmK2` THẬT.

Trạng thái: AUTHORED_NOT_RUN (chưa chạy trong gói B). Không CSDL thật, không Node/portal/mạng: kết nối là fake literal đúng interface psycopg mà
code thật dùng (`adapters.register_dumper`, `transaction()`, `execute(...).fetchone/fetchall/iter`, dict row), điều phối SQL theo văn bản và
mô phỏng ngữ nghĩa `master.ktt_danh_tinh/ktt_nguon_duoc/ktt_duoc` + bảng registry. Không patch guard về True, không HOLD-all.
Node là router fake literal theo hợp đồng `tools/source7_m2_patch/src/server.js` phía sau `KhachNode` THẬT. Dữ liệu chỉ DEMO.
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2.crm import CrmK2
from kho_tri_thuc.k2.hoa_don import HoaDonK2
from kho_tri_thuc.m2.tai_hoa_don import CauHinhTaiHoaDon, DieuPhoiTaiHoaDon, GioiHan, KhachNode, LoiTienTrinh, TepPin
from kho_tri_thuc.m2.tai_hoa_don import dieu_phoi as dp
from kho_tri_thuc.m2.tai_hoa_don.cau_hinh import TEP_BAT_BUOC

# ---------------------------------------------------------------- dữ liệu DEMO literal
U_KT = "11111111-1111-4111-8111-111111111111"
U_XA = "22222222-2222-4222-8222-222222222222"
U_BH = "33333333-3333-4333-8333-333333333333"
U_KN = "44444444-4444-4444-8444-444444444444"
PN_A, MA_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "DEMO_A"
PN_B, MA_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "DEMO_B"
INST, SCOPE, REF = "demo.hddt.m2", "INV_SET_DEMO", "M2_HDDT_DEMO_PROFILE"
CTY_A, CTY_B = "MST_0100000001", "MST_0100000002"
PAYLOAD = {"module": "M2", "kind": "INVOICE_PORTAL_DEMO", "version": 1}
PAYLOAD_CANON = '{"kind":"INVOICE_PORTAL_DEMO","module":"M2","version":1}'
SHA = hashlib.sha256(PAYLOAD_CANON.encode("utf-8")).hexdigest()
SHA_MOI = hashlib.sha256(b'{"kind":"INVOICE_PORTAL_DEMO","module":"M2","version":2}').hexdigest()
SID_KT, SID_KT2, SID_XA = "sid-demo-ke-toan-0001", "sid-demo-ke-toan-0002", "sid-demo-xem-a-0001"
PHIEN_BAN = "source7-m2-00a-candidate-1"
PROTOCOL = "source7-m2-owned/v1"
CAP = "DEMOcapDEMOcapDEMOcapDEMOcapDEMOcapDEMOcap0"  # 43 ký tự, canary capability DEMO
CONG = 47001
COT_NHAT_KY = ("phap_nhan_id", "nguoi", "loai", "doi_tuong_bang", "doi_tuong_id", "hanh_dong", "truoc", "sau", "ly_do", "can_cu")
TYPE_DIR = {"purchase": "mua_vao", "sold": "ban_ra"}
_VN = timezone(timedelta(hours=7))


def canon(v) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- fake kết nối psycopg literal
class _Cur:
    def __init__(self, rows):
        self._rows = [dict(r) for r in rows]

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def __iter__(self):
        return iter(list(self._rows))


class _Adapters:
    def __init__(self):
        self.dumpers = []

    def register_dumper(self, cls, dumper):
        self.dumpers.append((cls, dumper))


class KetNoiGia:
    """Một app connection. Giao dịch: nhật ký đệm tới commit ngoài cùng; lỗi → rollback (mất đệm). set_config local theo giao dịch."""

    def __init__(self):
        self.adapters = _Adapters()
        self.nguoi_dung = {
            "MO_PHONG_KE_TOAN": {"id": U_KT, "dang_nhap": "MO_PHONG_KE_TOAN", "ten": "KT demo", "vai_tro": "KE_TOAN", "mo_phong": True, "trang_thai": "HOAT_DONG"},
            "MO_PHONG_XEM_A": {"id": U_XA, "dang_nhap": "MO_PHONG_XEM_A", "ten": "Xem A demo", "vai_tro": "XEM", "mo_phong": True, "trang_thai": "HOAT_DONG"},
            "MO_PHONG_BAN_HANG": {"id": U_BH, "dang_nhap": "MO_PHONG_BAN_HANG", "ten": "BH demo", "vai_tro": "BAN_HANG", "mo_phong": True, "trang_thai": "HOAT_DONG"},
            "MO_PHONG_KHONG_NGUON": {"id": U_KN, "dang_nhap": "MO_PHONG_KHONG_NGUON", "ten": "KN demo", "vai_tro": "KE_TOAN", "mo_phong": True, "trang_thai": "HOAT_DONG"},
        }
        self.phan_quyen = [
            {"nguoi_dung_id": U_KT, "phap_nhan_id": PN_A, "duyet_loai_viec": [], "module": ["M2"]},
            {"nguoi_dung_id": U_KT, "phap_nhan_id": PN_B, "duyet_loai_viec": [], "module": ["M2"]},
            {"nguoi_dung_id": U_XA, "phap_nhan_id": PN_A, "duyet_loai_viec": [], "module": ["M2"]},
            {"nguoi_dung_id": U_BH, "phap_nhan_id": PN_A, "duyet_loai_viec": [], "module": ["M2"]},
            {"nguoi_dung_id": U_KN, "phap_nhan_id": PN_A, "duyet_loai_viec": [], "module": ["M2"]},
        ]
        self.phap_nhan = {PN_A: MA_A, PN_B: MA_B}
        self.instance = {INST: "HOAT_DONG"}
        self.profile = [{"source_instance_id": INST, "profile_ref": REF, "profile_sha256": SHA, "payload": dict(PAYLOAD)}]
        self.pham_vi = [{"source_instance_id": INST, "scope_ref": SCOPE, "profile_ref": REF, "profile_sha256": SHA, "ma_kho": None, "so_phieu": None,
                         "sections": [], "coverage_binding": None, "scope_kind": "INVOICE_SET", "company_keys": [CTY_A, CTY_B], "phap_nhan_id": None}]
        self.anh_xa = [
            {"id": "a0000000-0000-4000-8000-00000000000a", "reference_id": "MAP_DEMO_A", "revision": 1, "subject_key": CTY_A, "phap_nhan_id": PN_A,
             "source_instance_id": INST, "profile_ref": REF, "profile_sha256": SHA, "state": "DA_DUYET"},
            {"id": "b0000000-0000-4000-8000-00000000000b", "reference_id": "MAP_DEMO_B", "revision": 1, "subject_key": CTY_B, "phap_nhan_id": PN_B,
             "source_instance_id": INST, "profile_ref": REF, "profile_sha256": SHA, "state": "DA_DUYET"},
        ]
        self.nguon_duoc = {(u, INST, REF, SHA, a) for u in (U_KT, U_XA, U_BH) for a in ("INTAKE", "READ_SOURCE")} | {(U_KN, INST, REF, SHA, "INTAKE")}
        self.nhat_ky: list[dict] = []
        self._tx: list[list] = []
        self._cfg = None
        self.loi_nhat_ky = False
        self.ai_ep = None  # mô phỏng ktt_danh_tinh() trả login khác (phiên DB lệch)
        self.sql: list[str] = []
        self.so_tx = 0

    @contextmanager
    def transaction(self):
        self._tx.append([])
        self.so_tx += 1
        ok = False
        try:
            yield self
            ok = True
        finally:
            buf = self._tx.pop()
            if ok:
                (self._tx[-1] if self._tx else self.nhat_ky).extend(buf)
            if not self._tx:
                self._cfg = None

    def _ai(self):
        if self.ai_ep is not None:
            return self.ai_ep
        if self._cfg is None:
            return None
        u = self.nguoi_dung.get(self._cfg[1])
        return u["dang_nhap"] if u and u["id"] == self._cfg[0] and u["trang_thai"] == "HOAT_DONG" else None

    def _uid(self):
        return self._cfg[0] if self._ai() is not None else None

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        self.sql.append(s)
        p = tuple(params or ())
        if s.startswith("INSERT INTO nhat_ky.su_kien"):
            if not self._tx:
                raise AssertionError("nhật ký ngoài giao dịch")
            if self.loi_nhat_ky:
                raise RuntimeError("DEMO fault-injected insert")
            self._tx[-1].append(dict(zip(COT_NHAT_KY, p)))
            return _Cur([])
        if s.startswith("SELECT set_config('ktt.nguoi_dung_id'"):
            if not self._tx:
                raise AssertionError("set_config local ngoài giao dịch")
            self._cfg = (p[0], p[1])
            return _Cur([{"ai": self._ai()}])
        if s == "SELECT master.ktt_danh_tinh() AS ai":
            return _Cur([{"ai": self._ai()}])
        if "FROM master.nguoi_dung WHERE dang_nhap = %s" in s:
            u = self.nguoi_dung.get(p[0])
            return _Cur([u] if u else [])
        if "FROM master.phan_quyen q" in s:
            return _Cur([{"phap_nhan_id": q["phap_nhan_id"], "ma": self.phap_nhan[q["phap_nhan_id"]], "duyet_loai_viec": list(q["duyet_loai_viec"]),
                          "module": list(q["module"])} for q in self.phan_quyen if q["nguoi_dung_id"] == p[0]])
        if "FROM master.nguon_profile p JOIN master.nguon_instance i" in s:
            return _Cur(sorted(({"profile_ref": r["profile_ref"], "profile_sha256": r["profile_sha256"], "payload": r["payload"]} for r in self.profile
                                if r["source_instance_id"] == p[0] and self.instance.get(p[0]) == "HOAT_DONG"), key=lambda r: r["profile_ref"]))
        if s == "SELECT source_instance_id FROM master.nguon_profile WHERE payload->>'module' = 'M2'":
            return _Cur([{"source_instance_id": r["source_instance_id"]} for r in self.profile if r["payload"].get("module") == "M2"])
        if s.startswith("SELECT master.ktt_nguon_duoc("):
            return _Cur([{"ok": self._uid() is not None and (self._uid(), *p[:4]) in self.nguon_duoc}])
        if s.startswith("SELECT scope_ref, ma_kho, so_phieu"):
            return _Cur([r for r in self.pham_vi if (r["source_instance_id"], r["scope_ref"], r["profile_ref"], r["profile_sha256"]) == p])
        if s.startswith("SELECT scope_ref FROM master.nguon_pham_vi"):
            return _Cur(sorted(({"scope_ref": r["scope_ref"]} for r in self.pham_vi if (r["source_instance_id"], r["profile_ref"], r["profile_sha256"]) == p
                                and r["scope_kind"] == "INVOICE_SET"), key=lambda r: r["scope_ref"]))
        if "FROM master.anh_xa_nguon m JOIN master.phap_nhan p" in s:
            inst, ref, sha, keys = p
            return _Cur([{**{k: m[k] for k in ("id", "reference_id", "revision", "subject_key", "phap_nhan_id")}, "ma": self.phap_nhan[m["phap_nhan_id"]]}
                         for m in self.anh_xa if (m["source_instance_id"], m["profile_ref"], m["profile_sha256"]) == (inst, ref, sha)
                         and m["subject_key"] in keys and m["state"] == "DA_DUYET"])
        if s == "SELECT ma FROM master.phap_nhan WHERE id = %s":
            return _Cur([{"ma": self.phap_nhan[p[0]]}] if p[0] in self.phap_nhan else [])
        if s == "SELECT master.ktt_duoc(%s::uuid, 'M2') AS ok":
            uid = self._uid()
            return _Cur([{"ok": uid is not None and any(q["nguoi_dung_id"] == uid and q["phap_nhan_id"] == p[0] and "M2" in q["module"]
                                                        for q in self.phan_quyen)}])
        raise AssertionError("SQL không mong đợi: " + s[:100])


class AppGia:
    """Literal theo `LocalApp.crm_phien/crm/m2` (server.py:184–193, 207, 702–707): CÙNG một app connection cho CRM và M2."""
    CRM_MAC_DINH = "MO_PHONG_KE_TOAN"

    def __init__(self, conn, root: Path):
        self.conn, self.root = conn, root
        self._crm = None
        self._m2 = None

    def crm_phien(self, sid, *, tao=False):
        phien = self.__dict__.setdefault("_crm_phien", {})
        if sid and sid in phien:
            return sid, phien[sid], False
        if not tao:
            raise DataError("CRM_PHIEN", "Phiên CRM chưa có hoặc đã hết — tải lại trang để nhận phiên mới.")
        raise AssertionError("B không bao giờ tự cấp phiên")

    def dat_phien(self, sid, login):
        self.__dict__.setdefault("_crm_phien", {})[sid] = login

    def bo_phien(self, sid):
        self.__dict__.setdefault("_crm_phien", {}).pop(sid, None)

    def crm(self):
        if self._crm is None:
            self._crm = CrmK2(self.conn, self.root / "crm")
        return self._crm

    def m2(self):
        if self._m2 is None:
            crm = self.crm()
            self._m2 = HoaDonK2(crm.conn, self.root / "m2-k2", hom_nay=crm.hom_nay)
        return self._m2


# ---------------------------------------------------------------- router Node fake literal (hợp đồng server.js)
class _PhanHoiGia:
    def __init__(self, status, ct, data: bytes):
        self.status, self._ct, self._b = status, ct, io.BytesIO(data)

    def getheader(self, k, d=None):
        return self._ct if k.lower() == "content-type" else d

    def read(self, n=-1):
        return self._b.read(n)

    def readline(self, n=-1):
        return self._b.readline(n)


class _HttpGia:
    def __init__(self, node, timeout):
        self.node, self.timeout, self._r = node, timeout, None

    def request(self, method, path, body=None, headers=None):
        if self.node.ngat:
            raise ConnectionRefusedError("DEMO ngắt")
        self._r = self.node.xu_ly(method, path, dict(headers or {}), body)

    def getresponse(self):
        return self._r

    def close(self):
        self.node.so_dong += 1


class NodeGia:
    def __init__(self, port=CONG, cap=CAP):
        self.port, self.cap = port, cap
        self.jobs: dict[str, dict] = {}
        self.running = None
        self.goi: list[tuple] = []
        self.than: list[tuple] = []
        self.san_sang: dict[str, tuple] = {}
        self.mo: list[str] = []
        self.so_start = 0
        self.so_dong = 0
        self.ngat = False
        self.loi_start = None  # (status, code) ép lỗi ở /api/start
        self.khi_goi = None  # callback(path) trước khi xử lý (mô phỏng thay đổi quyền trong lúc IO)

    def ket_noi(self, host, port, timeout=None):
        if host != "127.0.0.1" or port != self.port:
            raise AssertionError("khách gọi sai host/cổng")
        return _HttpGia(self, timeout)

    @staticmethod
    def _json(status, v):
        return _PhanHoiGia(status, "application/json; charset=utf-8", json.dumps(v).encode("utf-8"))

    def _loi(self, status, code):
        return self._json(status, {"ok": False, "code": code})

    def _base(self, ctx, digest, key, status):
        return {"ok": True, "status": status, "run_id": ctx["run"]["run_id"], "context_digest": digest, "request_key_sha256": key}

    def ket_thuc(self, key=None):
        key = key or self.running
        j = self.jobs[key]
        ctx = j["ctx"]
        r = ctx["request"]
        ky = f"{r['year']}-{r['month']:02d}"
        runs = [{"ky": ky, "chieu": t, "run_rel": "/".join([ctx["phap_nhan"]["ma"], ky, TYPE_DIR[t], ctx["run"]["run_id"]]), "trang_thai": "HOAN_TAT",
                 "loi": [], "manifest_sha256": "0" * 64} for t in r["types"]]
        j["receipt"] = {"trang_thai": "HOAN_TAT", "runs": runs}
        j["done"] = True
        self._su_kien(j, "done", {"trang_thai": "HOAN_TAT"})
        if self.running == key:
            self.running = None

    def _su_kien(self, j, loai, payload):
        j["events"].append({"seq": len(j["events"]) + 1, "type": loai, "payload": payload, "ts": "2026-10-23T02:30:00.000Z",
                            "run_id": j["ctx"]["run"]["run_id"], "context_digest": j["digest"]})

    def xu_ly(self, method, path, hd, body):
        self.goi.append((method, path))
        if self.khi_goi:
            self.khi_goi(path)
        if hd.get("Host") != f"127.0.0.1:{self.port}":
            return self._loi(403, "HOST_FORBIDDEN")
        if hd.get("X-Source7-M2-Cap") != self.cap:
            return self._loi(401, "CAPABILITY_INVALID")
        if path == "/api/config":
            return self._json(200, {"ok": True, "protocol": PROTOCOL, "version": PHIEN_BAN, "running": self.running is not None})
        v = json.loads(body.decode("utf-8"))
        self.than.append((path, v))
        if path == "/api/profiles":
            refs = [p["ref"] for p in v["profiles"]]
            if len(set(refs)) != len(refs):
                return self._loi(400, "PROFILES_DUPLICATE")
            return self._json(200, {"ok": True, "profiles": [{**p, "san_sang": self.san_sang.get(p["ref"], (False, "PROFILE_NOT_FOUND"))[0],
                                                              "ly_do": self.san_sang.get(p["ref"], (False, "PROFILE_NOT_FOUND"))[1]} for p in v["profiles"]]})
        ctx = v["context"]
        digest, key = h(canon(ctx)), h(ctx["run"]["request_key"])
        j = self.jobs.get(key)
        if path == "/api/start":
            if self.loi_start:
                return self._loi(*self.loi_start)
            if j is not None and j["digest"] != digest:
                return self._loi(409, "CONTEXT_MISMATCH")
            if j is None:
                if self.running is not None:
                    return self._loi(409, "JOB_BUSY")
                j = self.jobs[key] = {"ctx": ctx, "digest": digest, "events": [], "done": False, "receipt": None}
                self.running, self.so_start = key, self.so_start + 1
                self._su_kien(j, "phase", {"pha": "BAT_DAU"})
                self._su_kien(j, "log", {"thong_diep": "DEMO"})
                return self._json(200, self._base(ctx, digest, key, "STARTED"))
            if self.running == key:
                return self._json(200, self._base(ctx, digest, key, "RUNNING"))
            return self._json(200, {**self._base(ctx, digest, key, "REPLAY"), "receipt": j["receipt"], "receipt_sha256": h(canon(j["receipt"]))})
        if path in ("/api/status", "/api/reconcile"):
            if j is not None and j["digest"] != digest:
                return self._loi(409, "CONTEXT_MISMATCH")
            if self.running == key:
                return self._json(200, {**self._base(ctx, digest, key, "RUNNING"), "events_seq": len(j["events"])})
            if j is None:
                return self._json(200, self._base(ctx, digest, key, "NOT_FOUND"))
            return self._json(200, {**self._base(ctx, digest, key, "REPLAY"), "receipt": j["receipt"], "receipt_sha256": h(canon(j["receipt"]))})
        if path == "/api/events":
            if j is None:
                return self._loi(404, "EVENTS_NOT_FOUND")
            if j["digest"] != digest:
                return self._loi(409, "CONTEXT_MISMATCH")
            parts = [": open\n\n"]
            for ev in j["events"]:
                if ev["seq"] > v["cursor"]:
                    parts.append(": hb\n\n")
                    parts.append(f"id: {ev['seq']}\ndata: {json.dumps(ev)}\n\n")
            if j["done"]:
                parts.append('event: end\ndata: {"reason":"DONE"}\n\n')
            return _PhanHoiGia(200, "text/event-stream; charset=utf-8", "".join(parts).encode("utf-8"))
        if path == "/api/open-folder":
            if j is None or not j["receipt"] or v["run_rel"] not in [r["run_rel"] for r in j["receipt"]["runs"]]:
                return self._loi(404, "RUN_NOT_FOUND")
            self.mo.append(v["run_rel"])
            return self._json(200, {"ok": True, "run_rel": v["run_rel"]})
        return self._loi(404, "ROUTE_UNKNOWN")


class TienTrinhGia:
    """Thay TienTrinhNode ở tầng điều phối: trả `KhachNode` THẬT nối router fake; ghi nhận stop."""

    def __init__(self, node: NodeGia, gioi_han: GioiHan, san_sang=True):
        self.node, self.gh, self.san = node, gioi_han, san_sang
        self.so_dung = 0
        self.so_start = 0
        self.chung_dung = None

    def start(self):
        self.so_start += 1
        self.san = True
        return {"trang_thai": "SAN_SANG"}

    def stop(self):
        self.so_dung += 1
        self.san = False
        return {"trang_thai": "DA_DUNG"}

    def dang_chay(self):
        return self.san

    def khach(self):
        if not self.san:
            raise LoiTienTrinh("NODE_CHUA_SAN_SANG", "DEMO", "khach")
        return KhachNode(self.node.port, self.node.cap, self.gh, ket_noi=self.node.ket_noi)


def tao_cau_hinh(goc: Path, **gioi_han) -> CauHinhTaiHoaDon:
    node = goc / "node" / "node.exe"
    node.parent.mkdir(parents=True)
    node.write_bytes(b"DEMO-NODE-NOT-EXECUTED")
    g7 = goc / "s7"
    pins = []
    for rel in TEP_BAT_BUOC:
        p = g7.joinpath(*rel.split("/"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"// DEMO " + rel.encode("ascii"))
        pins.append(TepPin(rel, hashlib.sha256(p.read_bytes()).hexdigest()))
    goc_ds = {}
    for k in ("tai", "trinh_duyet", "profile", "dieu_phoi"):
        goc_ds[k] = goc / k
        goc_ds[k].mkdir()
    return CauHinhTaiHoaDon(node, hashlib.sha256(node.read_bytes()).hexdigest(), g7, tuple(pins), PHIEN_BAN, goc_ds["tai"], goc_ds["trinh_duyet"],
                            goc_ds["profile"], goc_ds["dieu_phoi"], gioi_han=GioiHan(**gioi_han))


class CoSoM2B(unittest.TestCase):
    """Dựng conn/app/router/cấu hình DEMO. Lớp con chọn giới hạn qua GIOI_HAN."""
    GIOI_HAN: dict = {}

    def setUp(self):
        self._tam = tempfile.TemporaryDirectory(prefix="m2-00b-", ignore_cleanup_errors=True)
        self.addCleanup(self._tam.cleanup)
        self.goc = Path(self._tam.name).resolve()
        self.conn = KetNoiGia()
        self.app = AppGia(self.conn, self.goc / "app")
        self.app.dat_phien(SID_KT, "MO_PHONG_KE_TOAN")
        self.app.dat_phien(SID_KT2, "MO_PHONG_KE_TOAN")
        self.app.dat_phien(SID_XA, "MO_PHONG_XEM_A")
        self.cfg = tao_cau_hinh(self.goc / "cfg", **self.GIOI_HAN)
        self.node = NodeGia()
        self.tt = TienTrinhGia(self.node, self.cfg.gioi_han)
        self.nonce = []
        self.ngu = []
        self.dp = self.dp_moi()

    def dp_moi(self, **kw):
        def sinh():
            self.nonce.append(f"DEMOnonce{len(self.nonce):04d}_abcdefghijklmn")
            return self.nonce[-1]
        return DieuPhoiTaiHoaDon(self.app, self.cfg, tien_trinh=kw.get("tt", self.tt),
                                 dong_ho=lambda: datetime(2026, 10, 23, 9, 30, 0, tzinfo=_VN), sinh_nonce=sinh,
                                 ngu=kw.get("ngu", lambda s: self.ngu.append(s)))

    @staticmethod
    def chon(cty=CTY_A, key="k-demo-0001", month=9, **kw):
        return {"source_instance": INST, "scope_ref": SCOPE, "company_key": cty, "mode": "month", "year": 2026, "month": month,
                "types": ["purchase"], "formats": ["xml"], "client_key": key, **kw}

    def hanh_dong(self):
        return [r["hanh_dong"] for r in self.conn.nhat_ky]

    def context_gui(self, i=-1):
        return [v for p, v in self.node.than if p == "/api/start"][i]["context"]


# ---------------------------------------------------------------- tests
class M2BTinh(CoSoM2B):
    def test_b01_import_va_khoi_tao_khong_spawn_khong_io(self):
        d = DieuPhoiTaiHoaDon(self.app, self.cfg)  # TienTrinhNode thật, chưa start
        self.assertFalse(d._tt.dang_chay())
        self.assertEqual(self.conn.sql, [])
        self.assertEqual(self.node.goi, [])
        with self.assertRaises(DataError) as e:
            d.start(SID_KT, self.chon())
        self.assertEqual(e.exception.code, "M2_00B_NODE_CHUA_SAN_SANG")
        self.assertEqual(self.conn.sql, [])  # NOT_READY trước mọi DB/nhật ký
        self.assertEqual(self.conn.nhat_ky, [])

    def test_b05_positive_qua_helper_that_cung_app_connection(self):
        self.dp.start(SID_KT, self.chon())
        self.assertIs(self.app.crm().conn, self.app.m2().conn)
        self.assertEqual(len(self.conn.adapters.dumpers), 2)  # CrmK2.__init__ + HoaDonK2.__init__ thật
        sql = " ".join(self.conn.sql)
        for mau in ("master.ktt_danh_tinh()", "master.ktt_nguon_duoc(", "master.anh_xa_nguon", "master.ktt_duoc(", "INSERT INTO nhat_ky.su_kien"):
            self.assertIn(mau, sql)

    def test_b04_context_A_tu_phien_va_registry_digest_khop(self):
        r = self.dp.start(SID_KT, self.chon())
        ctx = self.context_gui()
        self.assertEqual(set(ctx), {"schema", "issued_by", "phap_nhan", "profile", "actor", "binding", "source_instance", "scope_ref", "run", "request"})
        self.assertEqual(ctx["schema"], "m2_00a.source7.run_context.v1")
        self.assertEqual(ctx["issued_by"], "M2_COORDINATOR")
        self.assertEqual(ctx["phap_nhan"], {"uuid": PN_A, "ma": MA_A})
        self.assertEqual(ctx["profile"], {"ref": MA_A, "revision": SHA})
        self.assertEqual(ctx["actor"], {"id": U_KT, "nguon": "crm_phien"})
        self.assertEqual(ctx["run"], {"run_id": "20261023-093000", "nonce": self.nonce[0], "request_key": "m2b_" + r["run_handle"]})
        self.assertEqual(ctx["request"], {"mode": "month", "year": 2026, "month": 9, "types": ["purchase"], "formats": ["xml"]})
        self.assertEqual(dp.context_digest(ctx), h(canon(ctx)))  # = digest router (manifest.contextDigest miền ASCII)
        self.assertEqual(r["trang_thai"], "STARTED")

    def test_b06_selection_digest_bind_phien_actor_vai_pn_profile(self):
        self.dp.start(SID_KT, self.chon())
        sel = self.context_gui()["binding"]["selection_digest"]
        mong = h(canon({"schema": "m2_00b.selection.v1", "sid_ref": h("m2-00b-sid|" + SID_KT),
                        "actor": {"id": U_KT, "dang_nhap": "MO_PHONG_KE_TOAN", "vai_tro": "KE_TOAN"}, "phap_nhan": {"uuid": PN_A, "ma": MA_A},
                        "profile": {"ref": MA_A, "revision": SHA}, "source_profile": {"reference_id": REF, "sha256": SHA},
                        "source_instance": INST, "scope_ref": SCOPE, "company_key": CTY_A,
                        "mapping": {"id": "a0000000-0000-4000-8000-00000000000a", "ref": "MAP_DEMO_A", "revision": 1},
                        "request": {"mode": "month", "year": 2026, "month": 9, "types": ["purchase"], "formats": ["xml"]},
                        "client_key": "k-demo-0001"}))
        self.assertEqual(sel, mong)

    def test_b11_dto_run_dong_khong_lo_bi_mat(self):
        r = self.dp.start(SID_KT, self.chon())
        self.assertEqual(set(r), {"phien_ban", "run_handle", "trang_thai", "run_id", "phap_nhan_ma", "company_key", "yeu_cau", "ket_qua", "doi_soat",
                                  "nhat_ky", "can_doi_soat"})
        self.assertEqual(r["phien_ban"], "m2_00b.run.v1")
        txt = json.dumps(r)
        for bi_mat in (self.nonce[0], "m2b_", CAP, SID_KT, PN_A, U_KT, str(self.goc)):
            self.assertNotIn(bi_mat, txt)

    def test_b07_cung_khoa_cung_run_khong_sinh_nonce_moi(self):
        r1 = self.dp.start(SID_KT, self.chon())
        r2 = self.dp.start(SID_KT, self.chon())
        self.assertEqual(r1["run_handle"], r2["run_handle"])
        self.assertEqual(r2["trang_thai"], "RUNNING")
        self.assertEqual(len(self.nonce), 1)
        self.assertEqual(self.context_gui(0), self.context_gui(1))
        self.assertEqual(self.node.so_start, 1)
        self.node.ket_thuc()
        r3 = self.dp_moi().start(SID_KT, self.chon())  # điều phối mới (cache rỗng) đọc binding bất biến
        self.assertEqual(r3["trang_thai"], "REPLAY")
        self.assertEqual(len(self.nonce), 1)
        self.assertEqual(r3["ket_qua"]["runs"][0]["run_rel"], f"{MA_A}/2026-09/mua_vao/20261023-093000")

    def test_b07_khoa_da_dung_cho_lua_chon_khac_khong_start(self):
        self.dp.start(SID_KT, self.chon())
        with self.assertRaises(DataError) as e:
            self.dp.start(SID_KT, self.chon(month=8))
        self.assertEqual(e.exception.code, "M2_00B_KHOA_DA_DUNG")
        self.assertEqual(self.node.so_start, 1)
        self.assertEqual(len([p for p, _ in self.node.than if p == "/api/start"]), 1)

    def test_b04_phien_khac_cung_khoa_can_doi_soat_khong_start(self):
        self.dp.start(SID_KT, self.chon())
        r = self.dp.start(SID_KT2, self.chon())
        self.assertEqual(r["trang_thai"], "CAN_DOI_SOAT")
        self.assertIsNone(r["run_handle"])
        self.assertEqual(len([p for p, _ in self.node.than if p == "/api/start"]), 1)
        h1 = self.dp.start(SID_KT, self.chon())["run_handle"]
        with self.assertRaises(DataError) as e:
            self.dp.status(SID_KT2, h1)
        self.assertEqual(e.exception.code, "M2_00B_CAN_DOI_SOAT")

    def test_b07_binding_bat_bien_khong_chua_sid_tho(self):
        r = self.dp.start(SID_KT, self.chon())
        p = self.cfg.goc_dieu_phoi / "m2-00b-binding" / f"{r['run_handle']}.json"
        txt = p.read_text(encoding="utf-8")
        b = json.loads(txt)
        self.assertEqual(b["schema"], "m2_00b.binding.v1")
        self.assertEqual(b["context_digest"], h(canon(b["context"])))
        self.assertNotIn(SID_KT, txt)
        self.assertNotIn(CAP, txt)

    def test_b07_binding_hong_tren_dia_fail_closed(self):
        r = self.dp.start(SID_KT, self.chon())
        p = self.cfg.goc_dieu_phoi / "m2-00b-binding" / f"{r['run_handle']}.json"
        b = json.loads(p.read_text(encoding="utf-8"))
        b["context"]["request"]["month"] = 8  # bản sửa ngoài luồng (khóa khác) → hash context không khớp
        key_gia = "f" * 64
        (p.parent / f"{key_gia}.json").write_text(json.dumps({**b, "binding_key": key_gia}), encoding="utf-8")
        with self.assertRaises(DataError) as e:
            self.dp_moi().status(SID_KT, key_gia)
        self.assertEqual(e.exception.code, "M2_00B_BINDING_HONG")
        with self.assertRaises(DataError) as e:
            self.dp.status(SID_KT, "../" + "a" * 61)
        self.assertEqual(e.exception.code, "M2_00B_RUN_HANDLE")
        self.assertEqual(len([p for p, _ in self.node.than if p == "/api/status"]), 0)

    def test_b04_lua_chon_dong_pn_gia_bi_tu_choi_truoc_moi_db(self):
        for sai in (self.chon(phap_nhan=PN_A), self.chon(month=13), self.chon(types=["purchase", "purchase"]), self.chon(key="ngan"),
                    self.chon(formats=["exe"]), {**self.chon(), "mode": "year"}):
            with self.assertRaises(DataError):
                self.dp.start(SID_KT, sai)
        self.assertEqual(self.conn.sql, [])
        self.assertEqual(self.node.goi, [])

    def test_b12_nhat_ky_qua_crm_su_kien_trong_giao_dich(self):
        self.dp.start(SID_KT, self.chon())
        self.assertEqual(self.hanh_dong(), ["M2_00B_YEU_CAU_TAI", "M2_00B_KET_QUA_START"])
        for row in self.conn.nhat_ky:
            self.assertEqual((row["phap_nhan_id"], row["nguoi"], row["loai"], row["doi_tuong_bang"], row["doi_tuong_id"]),
                             (PN_A, "MO_PHONG_KE_TOAN", "NGUON_TU_DONG", "m2_00b.tai_hoa_don", None))
            for bi_mat in (self.nonce[0], '"m2b_', CAP, SID_KT):
                self.assertNotIn(bi_mat, (row["sau"] or "") + (row["can_cu"] or ""))
        self.assertNotIn("ghi_su_kien", Path(dp.__file__).read_text(encoding="utf-8"))

    def test_b04_profiles_theo_quyen_hien_hanh(self):
        self.node.san_sang = {MA_A: (True, None), MA_B: (False, "PROFILE_REVISION_MISMATCH")}
        r = self.dp.profiles(SID_KT)
        self.assertEqual(r["phien_ban"], "m2_00b.profiles.v1")
        self.assertEqual([(m["company_key"], m["phap_nhan_ma"], m["san_sang"], m["ly_do"]) for m in r["muc"]],
                         [(CTY_A, MA_A, True, None), (CTY_B, MA_B, False, "PROFILE_REVISION_MISMATCH")])
        gui = [v for p, v in self.node.than if p == "/api/profiles"][0]["profiles"]
        self.assertEqual({p["ref"] for p in gui}, {MA_A, MA_B})
        self.assertTrue(all(p["revision"] == SHA for p in gui))
        r2 = self.dp.profiles(SID_XA)  # X chỉ thấy PN A
        self.assertEqual([m["company_key"] for m in r2["muc"]], [CTY_A])
        self.assertNotIn(MA_B, json.dumps(r2))
        self.assertNotIn(PN_A, json.dumps(r))
        self.assertEqual(self.conn.nhat_ky, [])  # đọc danh sách không ghi nhật ký

    def test_b08_hang_doi_tuan_tu_kiem_quyen_tung_job(self):
        def ngu(_s):
            if self.node.running:
                self.node.ket_thuc()
        d = self.dp_moi(ngu=ngu)
        r = d.start(SID_KT, [self.chon(CTY_A, "k-demo-q001"), self.chon(CTY_B, "k-demo-q002")])
        self.assertEqual(r["phien_ban"], "m2_00b.hang_doi.v1")
        self.assertEqual([m["trang_thai"] for m in r["muc"]], ["REPLAY", "REPLAY"])
        ctxs = [v["context"]["phap_nhan"]["ma"] for p, v in self.node.than if p == "/api/start"]
        self.assertEqual(ctxs, [MA_A, MA_B])
        self.assertEqual(self.node.so_start, 2)
        r2 = self.dp_moi(ngu=ngu).start(SID_XA, [self.chon(CTY_A, "k-demo-x001"), self.chon(CTY_B, "k-demo-x002")])
        self.assertEqual(r2["muc"][1], {"company_key": CTY_B, "trang_thai": "TU_CHOI", "ma": "KHONG_CO_QUYEN_PHAP_NHAN"})
        self.assertEqual(r2["muc"][0]["trang_thai"], "REPLAY")

    def test_b08_hang_doi_sai_hinh_dang(self):
        for sai in ([], [self.chon(key="k-demo-dup1"), self.chon(CTY_B, key="k-demo-dup1")], [self.chon(extra=1)]):
            with self.assertRaises(DataError) as e:
                self.dp.start(SID_KT, sai)
            self.assertIn(e.exception.code, ("M2_00B_HANG_DOI_SAI", "M2_00B_CHON_SAI"))
        self.assertEqual(self.node.goi, [])

    def test_b10_open_folder_chi_run_rel_cua_run(self):
        r = self.dp.start(SID_KT, self.chon())
        self.node.ket_thuc()
        rel = f"{MA_A}/2026-09/mua_vao/20261023-093000"
        self.assertEqual(self.dp.mo_thu_muc(SID_KT, r["run_handle"], rel), {"ok": True})
        self.assertEqual(self.node.mo, [rel])
        for sai in (f"{MA_B}/2026-09/mua_vao/20261023-093000", f"{MA_A}/2026-09/mua_vao/20261023-093001", f"{MA_A}/../x/y", "C:/x"):
            with self.assertRaises(DataError) as e:
                self.dp.mo_thu_muc(SID_KT, r["run_handle"], sai)
            self.assertEqual(e.exception.code, "M2_00B_RUN_REL_SAI")
        self.assertEqual(self.node.mo, [rel])

    def test_b09_events_dung_run_ket_thuc_done(self):
        r = self.dp.start(SID_KT, self.chon())
        self.node.ket_thuc()
        evs = list(self.dp.events(SID_KT, r["run_handle"], 0))
        self.assertEqual([e.get("type") for e in evs[:-1]], ["phase", "log", "done"])
        self.assertEqual(evs[-1], {"ket_thuc": "DONE"})
        self.assertEqual(list(self.dp.events(SID_KT, r["run_handle"], 2))[0]["seq"], 3)

    def test_b12_status_ket_thuc_ghi_nhat_ky_mot_lan(self):
        r = self.dp.start(SID_KT, self.chon())
        self.assertEqual(self.dp.status(SID_KT, r["run_handle"])["trang_thai"], "RUNNING")
        self.node.ket_thuc()
        s1 = self.dp.status(SID_KT, r["run_handle"])
        s2 = self.dp.status(SID_KT, r["run_handle"])
        self.assertEqual((s1["trang_thai"], s1["nhat_ky"], s1["ket_qua"]["trang_thai"]), ("REPLAY", "DA_GHI", "HOAN_TAT"))
        self.assertNotIn("nhat_ky", s2)
        self.assertEqual(self.hanh_dong().count("M2_00B_KET_THUC"), 1)


class M2BHangDoiQuaHan(CoSoM2B):
    GIOI_HAN = {"cho_moi_job_s": 1, "nhip_poll_s": 0.5}

    def test_b08_qua_han_dung_hang_doi_khong_chay_tiep(self):
        r = self.dp.start(SID_KT, [self.chon(CTY_A, "k-demo-t001"), self.chon(CTY_B, "k-demo-t002")])
        self.assertEqual([m["trang_thai"] for m in r["muc"]], ["CHUA_KET_THUC", "CHUA_CHAY"])
        self.assertEqual(self.ngu, [0.5, 0.5])
        self.assertEqual(self.node.so_start, 1)


if __name__ == "__main__":
    unittest.main()
