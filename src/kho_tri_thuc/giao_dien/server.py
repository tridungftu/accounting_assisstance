from __future__ import annotations

import argparse
import json
import os
import secrets
import sqlite3
import threading
import time
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from .. import __version__
from ..ha_tang.config import Config
from ..ha_tang.primitives import DataError, canonical_json, now_utc, sha256
from ..ha_tang.store import Store, write_immutable
from ..de_xuat.nghiem_thu import NghiemThu
from ..kiem_chung.fixtures import bank_fixture, bundle_fixture, nghiem_thu_catalog_fixture, review_dot_fixture
from ..nguon.fixture import FixtureAdapter, read_json
from ..nguon.review_xay_dung import ReviewXayDungAdapter
from .intake import Intake, MAX_FILE_SIZE, SOURCES
from .operations import Operations

# start-web.ps1 restarts a server that started before the code on disk changed.
_STARTED_AT = int(time.time())

ASSETS = Path(__file__).parent / "assets"


class LocalApp:
    # CRM-41-01-06: engine #6 DEMO do serve()/CLI sở hữu. Constructor KHÔNG spawn (fixture tự tạo LocalApp); mặc định không quản lý → giữ seam
    # URL/transport bên ngoài cho fixture tường minh. serve() đánh dấu quản lý TRƯỚC khi spawn; sau đó không bao giờ rơi về biến môi trường.
    trich6_host = None
    trich6_quan_ly = False

    def trich6_client(self, goc):
        """Factory client engine #6 theo app: chế độ quản lý → client của host (host lỗi/chết/chưa có → NOT_READY, không fallback môi trường);
        không quản lý → seam cũ (KHO_TRICH6_URL do host cấp)."""
        from ..nguon.trich_chung_6 import Trich6Client
        if self.trich6_quan_ly:
            return self.trich6_host.client(goc) if self.trich6_host is not None else Trich6Client("", goc=goc)
        return Trich6Client(goc=goc)

    def trich6_suc_khoe(self):
        if not self.trich6_quan_ly:
            return {"quan_ly": False}
        if self.trich6_host is None:
            return {"quan_ly": True, "san_sang": False, "ly_do": "CHUA_CO_HOST"}
        return self.trich6_host.suc_khoe()

    def __init__(self, config_path, root):
        self.root = Path(root).resolve()
        self.root_id = sha256(str(self.root).casefold().encode("utf-8"))
        self.config_path = Path(config_path).resolve()
        loaded = Config.load(self.config_path)
        self.is_that = loaded.environment == "that"
        self.operations = Operations(self.config_path, self.root) if self.is_that else None
        self.intake = Intake(self.root / "ho-so-goc") if not self.is_that else None
        self.demo_config = Config.load(self.config_path, self.root / "mo-phong") if not self.is_that else None
        self.token = secrets.token_urlsafe(32)
        self.mutation_lock = threading.Lock()
        if not self.is_that:
            with Store(self.demo_config):
                pass

    def gan_request_nhap(self, cau_hinh, transport):
        """M4-6 · seam Request nháp (không bí mật, không đọc .env/khóa): máy chủ tiêm cấu hình + transport cho `giao_dien/m4_request.py`.
        Mặc định KHÔNG gắn gì = 503 CHUA_CAU_HINH, 0 mạng. Transport tự nó có thể đang TẮT (`kich_hoat=False`) — seam không bật hộ."""
        from ..m4.request_nhap import CauHinhRequest
        if not isinstance(cau_hinh, CauHinhRequest) or not callable(getattr(transport, "gui", None)):
            raise DataError("M4_REQUEST_CAU_HINH_SAI", "Cấu hình Request phải là CauHinhRequest và transport phải có phương thức gui.")
        self.__dict__["_m4_request"] = {"cau_hinh": cau_hinh, "transport": transport}

    def go_request_nhap(self):
        """Gỡ seam Request nháp: về mặc định vắng (CHUA_CAU_HINH). Gỡ khi chưa gắn là không việc gì."""
        self.__dict__.pop("_m4_request", None)

    def state(self):
        if self.is_that:
            return {**self.operations.state(), "storage_path": str(self.operations.config.data_dir), "max_file_bytes": MAX_FILE_SIZE,
                    "version": __version__, "real_processing": True, "junsky_export": False, "ai_required": False}
        listing = self.intake.listing()
        with Store(self.demo_config) as store:
            demo = store.status()
            attempts = [json.loads(r[0]) for r in store.conn.execute("SELECT report_json FROM attempts WHERE report_json IS NOT NULL ORDER BY rowid DESC LIMIT 12")]
        return {**listing, "sources": SOURCES, "demo": demo, "demo_attempts": attempts, "storage_path": str(self.intake.root),
                "max_file_bytes": MAX_FILE_SIZE, "version": __version__, "real_processing": False, "junsky_export": False, "ai_required": False}

    def demo_sample(self, source):
        if self.is_that:
            raise DataError("THAT_UI", "Bản vận hành không dùng dữ liệu mô phỏng.")
        if source not in {"sao_ke", "junsky_xuat"}:
            raise DataError("DEMO_SOURCE", "Mẫu tích hợp sẵn gồm sao kê và bộ Junsky giả lập.")
        return canonical_json(bank_fixture() if source == "sao_ke" else bundle_fixture()).encode("utf-8")

    def demo_import(self, raw, name, commit=False):
        if self.is_that:
            raise DataError("THAT_UI", "Bản vận hành không nạp dữ liệu mô phỏng.")
        # Fixture checks stay in the existing adapter. Never rewrite real data to synthetic.
        batch = FixtureAdapter().read(raw, self.demo_config)
        report = {"fixture_only": True, "valid": batch.valid, "source": batch.source, "input_records": len(batch.raw_records),
                  "control_totals_minor": batch.totals, "issues": [asdict(i) for i in batch.issues], "state": "VALIDATED" if batch.valid else "REJECTED"}
        if commit:
            name = name.replace("\\", "/").split("/")[-1]
            if not name or len(name) > 240:
                raise DataError("FILE_NAME", "Tên mẫu không hợp lệ.")
            folder = self.root / "mo-phong-upload" / sha256(raw)
            path = folder / name
            if not path.resolve().is_relative_to(self.root / "mo-phong-upload"):
                raise DataError("FILE_NAME", "Đường dẫn mẫu không hợp lệ.")
            write_immutable(path, raw)
            with Store(self.demo_config) as store:
                return store.ingest(path)
        return report

    # --- M4 bridge DEMO: hồ sơ nghiệm thu từ kết quả #5 (cùng Store mô phỏng) ---
    NT_INSTANCE = "REVIEW_XD_DEMO"   # namespace instance #5 của bản DEMO
    NT_ACTOR = "MO_PHONG_KE_TOAN"    # server khóa người thao tác; không nhận actor do trình duyệt gửi

    def _nt_store(self):
        if self.is_that:
            raise DataError("THAT_UI", "Hồ sơ nghiệm thu bridge chỉ có trong bản DEMO; kho thật nhận #5 qua giao_tiep (chưa tích hợp).")
        return Store(self.demo_config)

    @staticmethod
    def nt_actor(payload):
        if payload.get("actor") not in (None, LocalApp.NT_ACTOR):
            raise DataError("ACTOR_SERVER_LOCKED", "Người thao tác do máy chủ DEMO cố định (MO_PHONG_KE_TOAN); không nhận actor từ trình duyệt.")
        for key in ("state", "trang_thai", "but_toan", "lines"):
            if key in payload:
                raise DataError("NT_CLIENT_STATE", "Trạng thái và bút toán do máy chủ tính; không nhận từ trình duyệt.")
        return LocalApp.NT_ACTOR

    def nt_list(self):
        with self._nt_store() as store:
            facade = NghiemThu(store)
            facade.dong_bo(self.NT_ACTOR)
            return facade.danh_sach()

    def nt_sample(self, kind):
        if self.is_that:
            raise DataError("THAT_UI", "Bản vận hành không dùng dữ liệu mô phỏng.")
        samples = {"review": review_dot_fixture(), "review_chua_nap": review_dot_fixture(ma="KTD-DEMO-0002", dot="4", da_nap=False),
                   "review_ban_thay": review_dot_fixture(ma="KTD-DEMO-0001B", luc="2026-09-21T08:00:00+07:00", anh_huong=900_000),
                   "danh_muc": nghiem_thu_catalog_fixture()}
        if kind not in samples:
            raise DataError("NT_SAMPLE", "Mẫu DEMO gồm review, review_chua_nap, review_ban_thay, danh_muc.")
        return canonical_json(samples[kind]).encode("utf-8")

    def nt_receive(self, raw, name):
        name = (name or "review.json").replace("\\", "/").split("/")[-1]
        if not name or len(name) > 240:
            raise DataError("FILE_NAME", "Tên tệp không hợp lệ.")
        folder = self.root / "mo-phong-upload" / sha256(raw)
        path = folder / name
        if not path.resolve().is_relative_to(self.root / "mo-phong-upload"):
            raise DataError("FILE_NAME", "Đường dẫn tệp không hợp lệ.")
        write_immutable(path, raw)
        with self._nt_store() as store:
            report = store.ingest(path, ReviewXayDungAdapter(self.NT_INSTANCE))
            NghiemThu(store).dong_bo(self.NT_ACTOR)
            return report

    def nt_seed(self, kind):
        if kind == "danh_muc":
            return self.demo_import(self.nt_sample(kind), "danh_muc_nghiem_thu_MO_PHONG.json", commit=True)
        return self.nt_receive(self.nt_sample(kind), f"{kind}_MO_PHONG.json")

    def nt_confirm(self, payload):
        actor = self.nt_actor(payload)
        with self._nt_store() as store:
            return NghiemThu(store).xac_nhan(payload.get("id"), payload.get("mapping"), payload.get("so"), actor)

    def nt_decide(self, payload):
        actor = self.nt_actor(payload)
        with self._nt_store() as store:
            return NghiemThu(store).quyet_dinh(payload.get("id"), payload.get("hanh_dong"), actor, ly_do=payload.get("ly_do", ""))

    def nt_export(self, payload):
        actor = self.nt_actor(payload)
        with self._nt_store() as store:
            return NghiemThu(store).xuat(actor, muc_2=payload.get("muc_2", False))

    def nt_file(self, export_id):
        with self._nt_store() as store:
            return NghiemThu(store).tep_xuat(export_id)

    # --- CRM-01 DEMO: hợp đồng & lịch thu trên K2 PostgreSQL (typed), cùng shell/token/mutation lock ---
    CRM_ENV, CRM_ENV_ADMIN = "KHO_PG_DSN_CRM_DEMO", "KHO_PG_DSN_CRM_DEMO_ADMIN"
    CRM_COOKIE, CRM_MAC_DINH = "ktt_crm", "MO_PHONG_KT_A"  # danh tính DEMO theo phiên trình duyệt (không phải đăng nhập production)
    _crm = None

    def crm_phien(self, sid, *, tao=False):
        """Danh tính CRM của một phiên (cookie HttpOnly do máy chủ cấp). Trả (sid, dang_nhap, mới cấp?)."""
        phien = self.__dict__.setdefault("_crm_phien", {})
        if sid and sid in phien:
            return sid, phien[sid], False
        if not tao:
            raise DataError("CRM_PHIEN", "Phiên CRM chưa có hoặc đã hết — tải lại trang để nhận phiên mới.")
        sid = secrets.token_urlsafe(24)
        phien[sid] = self.CRM_MAC_DINH
        return sid, phien[sid], True

    def crm(self):
        """Dịch vụ CRM K2. DSN vai trò ứng dụng (app_web) lấy từ biến môi trường của tiến trình; không đọc kho thật."""
        if self.is_that:
            raise DataError("THAT_UI", "CRM-01 hiện chỉ có trong bản DEMO; kho thật chưa mở K2 (V14).")
        if self._crm is None:
            dsn, _ = self._crm_ket_noi()
            if not dsn:
                raise DataError("CRM_CHUA_CAU_HINH", "CRM DEMO chưa được cấu hình kết nối PostgreSQL cục bộ — mở lại bằng nút MỞ BẢN DEMO sau khi cài đặt cấu hình.")
            from ..k2.crm_khoi_dong import kiem_role_ung_dung, nap_driver
            psycopg = nap_driver()
            from psycopg.rows import dict_row
            from ..ha_tang import postgres as pg
            from ..k2.crm import CrmK2
            try:
                conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
            except psycopg.Error:
                raise DataError("PG_KHONG_KET_NOI", "Không kết nối được PostgreSQL CRM DEMO trên máy — mở lại bằng nút MỞ BẢN DEMO.") from None
            try:  # request thường chỉ dùng login ứng dụng (không superuser/BYPASSRLS/chủ bảng); migrate/seed ở bước chuẩn bị của nút mở
                kiem_role_ung_dung(conn)
                try:  # đúng lineage mặc định (prefix 1–12 + COMMON13 + M5 14) và bản mới nhất — không chỉ so max(version)
                    pg.kiem_lineage_ung_dung(conn)
                except DataError as exc:
                    if exc.code == "LEGACY_FULL_M9_LINEAGE":
                        raise
                    raise DataError("CRM_SCHEMA_KHONG_KHOP", "Schema CRM DEMO chưa nâng cấp hoặc lineage lạ — mở lại bằng nút MỞ BẢN DEMO.") from None
            except psycopg.Error as exc:
                conn.close()
                raise DataError("CRM_KIEM_KET_NOI_LOI", f"Không kiểm được login ứng dụng CRM DEMO (SQLSTATE {exc.sqlstate}).") from None
            except Exception:
                conn.close()
                raise
            self._crm = CrmK2(conn, self.root / "crm-k2")
        return self._crm

    CRM_ENV_DB_KIEM_THU = "KTT_CRM_CHO_PHEP_DB_KIEM_THU"  # "1": cho phép DB fixture kiểm thử kho_test_* (chỉ test tự dựng đặt)

    def _crm_ket_noi(self):
        """(DSN ứng dụng, DSN quản trị) ĐÃ CHUẨN HÓA + KIỂM (cùng validator với tệp cấu hình và bootstrap) TRƯỚC mọi kết nối.
        Nguồn: biến môi trường của tiến trình, hoặc tệp cấu hình cục bộ (k2/crm_khoi_dong.py). Chỉ DB DEMO kho_crm_demo*; DB fixture
        kho_test_* chỉ khi tiến trình đặt rõ KTT_CRM_CHO_PHEP_DB_KIEM_THU=1. Không log, không trả DSN ra trình duyệt."""
        from ..k2.crm_khoi_dong import TIEN_TO_DB, TIEN_TO_DB_KIEM_THU, doc_ket_noi, duong_dan_ket_noi, kiem_cap
        tien_to = TIEN_TO_DB + (TIEN_TO_DB_KIEM_THU if os.environ.get(self.CRM_ENV_DB_KIEM_THU) == "1" else ())
        app, admin = os.environ.get(self.CRM_ENV), os.environ.get(self.CRM_ENV_ADMIN)
        if app:
            cap = kiem_cap(app, admin, tien_to)
            return cap["app"]["conninfo"], cap["admin"]["conninfo"] if cap["admin"] else None
        if admin:
            raise DataError("KET_NOI_SAI_DINH_DANG", "Có kết nối quản trị nhưng thiếu kết nối ứng dụng CRM DEMO.")
        path = duong_dan_ket_noi(self.root)
        if path.is_file():
            kn = doc_ket_noi(path, tien_to)
            return kn["app_dsn"], kn["admin_dsn"]
        return None, None

    @staticmethod
    def crm_body(payload, *allowed):
        for key in ("actor", "nguoi", "dang_nhap_thuc_hien", "phap_nhan_id", "trang_thai", "nguoi_duyet", "kiem_boi"):
            if key in payload and key not in allowed:
                raise DataError("CRM_CLIENT_IDENTITY", "Danh tính, pháp nhân và trạng thái do máy chủ xác định; không nhận từ trình duyệt.")
        return payload

    def crm_state(self, me):
        try:
            crm = self.crm()
        except DataError as exc:
            if exc.code == "CRM_CHUA_CAU_HINH":
                return {"cau_hinh": False, "ly_do": str(exc)}
            raise
        demo = self._demo_vai_cu(crm.conn)
        from ..kiem_chung.fixtures_crm import MAU, SAO_KE_M1
        tien_mau = [f"{pn}:{dot}" for pn in sorted(SAO_KE_M1) for dot in SAO_KE_M1[pn]]
        try:
            data = self._crm_db(crm.danh_sach, me)
        except DataError as exc:  # người của phiên không có quyền xem CRM: vẫn cho đổi danh tính DEMO, không trả dữ liệu
            if exc.code not in {"KHONG_CO_QUYEN_MODULE", "KHONG_CO_QUYEN_PHAP_NHAN"}:
                raise
            data = {"nguoi": {"dang_nhap": me}, "khong_quyen": str(exc), "ho_so": [], "hop_dong": [], "tien": [], "file_soat": [], "danh_muc": {}}
        return {"cau_hinh": True, **data, "danh_tinh_demo": demo, "mau": sorted(MAU), "tien_mau": tien_mau,
                "m1_cau_hinh": bool(self._crm_ket_noi()[1])}

    @staticmethod
    def _demo_vai_cu(conn):
        # Chỉ lọc danh sách hiển thị; giữ nguyên registry/grant và ca âm legacy.
        return [dict(r) for r in conn.execute("""SELECT dang_nhap, vai_tro FROM master.nguoi_dung
            WHERE mo_phong AND trang_thai = 'HOAT_DONG'
              AND starts_with(dang_nhap, 'MO_PHONG_MTQ_') = false ORDER BY dang_nhap""")]

    def demo_vai(self, me):
        """DTO bộ chọn chung trang chủ/ma trận; CRM/M9/M5 giữ bộ chọn riêng.

        GET /api/demo/vai cấp cookie CRM như GET /api/crm. Giao diện dùng
        POST /api/crm/danh-tinh hiện có qua cổng đổi vai tuần tự để đổi vai.
        Nhãn/vai lấy từ seed; giao với danh tính mô phỏng đang hoạt động.
        """
        if self.is_that:
            raise DataError("THAT_UI", "Bản vận hành không có bộ chọn vai DEMO.")
        from ..k2.mtq_demo import ADMIN, NGUOI_DUNG
        try:
            crm = self.crm()
        except DataError as exc:
            if exc.code == "CRM_CHUA_CAU_HINH":
                return {"cau_hinh": False, "nhom": []}
            raise
        actors = [ADMIN, *(n[0] for n in NGUOI_DUNG)]
        active = {r["dang_nhap"] for r in crm.conn.execute("""SELECT dang_nhap FROM master.nguoi_dung
            WHERE mo_phong AND trang_thai = 'HOAT_DONG' AND dang_nhap = ANY(%s)""", (actors,))}
        return {"dang_nhap": me, "danh_tinh_demo_nhom": [
            {"ma": "MTQ", "ten": "Ma trận thẩm quyền (DEMO)", "vai": [
                {"dang_nhap": login, "ten": ten.removesuffix(" DEMO"), "cap": vai}
                for login, ten, vai, _ in NGUOI_DUNG if login in active]},
            {"ma": "QUAN_TRI", "ten": "Quản trị DEMO", "vai": [
                {"dang_nhap": ADMIN, "ten": "Admin DEMO"}] if ADMIN in active else []},
        ]}

    @staticmethod
    def _crm_db(fn, *args):
        import psycopg
        try:
            return fn(*args)
        except psycopg.Error as exc:  # lỗi ràng buộc CSDL (RLS/trigger) → mã rõ, không lộ chi tiết dòng
            import re
            primary = (getattr(getattr(exc, "diag", None), "message_primary", "") or "").split(":", 1)[0]
            # mã CSDL = định danh ASCII HOA neo hai đầu (cho phép chữ số, vd M2_/M5_); text khác (riêng tư/tự do) → mã chung, không lộ chi tiết
            code = primary if len(primary) <= 80 and re.fullmatch(r"[A-Z][A-Z0-9_]*", primary) else "CSDL_TU_CHOI"
            raise DataError(code, f"CSDL từ chối thao tác ({code}).") from None

    def crm_action(self, sid, path, payload):
        return self._crm_db(self._crm_action, sid, path, payload)

    def _crm_action(self, sid, path, payload):
        sid, me, _ = self.crm_phien(sid)
        crm = self.crm()
        payload = self.crm_body(payload)
        if path == "danh-tinh":
            dang_nhap = payload.get("dang_nhap")
            crm.danh_tinh(dang_nhap)  # chỉ danh tính mô phỏng hoạt động; chỉ đổi phiên của trình duyệt này
            self._crm_phien[sid] = dang_nhap
            return {"dang_nhap": dang_nhap}
        if path == "mau":
            from ..kiem_chung.fixtures_crm import MAU, mau
            if payload.get("mau") not in MAU:
                raise DataError("CRM_MAU", "Không có mẫu DEMO này.")
            raw, env, van_ban = mau(payload.get("mau"))
            return crm.nhan_ket_qua_6(me, raw, env, van_ban_nguon=van_ban)
        if path == "bo-sung":
            return crm.bo_sung_ho_so(me, payload.get("id"), payload.get("bo_sung") or {})
        if path == "trich-lai/doi-chieu":
            return crm.doi_chieu_trich_lai(me, payload.get("id"))
        if path == "trich-lai/xu-ly":
            return crm.xu_ly_trich_lai(me, payload.get("id"), payload.get("hanh_dong"), payload.get("ly_do"))
        if path == "xac-nhan-tham-so":
            return crm.xac_nhan_tham_so(me, payload.get("id"), payload.get("ma"), payload.get("ly_do"))
        if path == "kiem":
            return crm.kiem_truoc(me, payload.get("id"), xac_nhan_can_cu_thu_cong=payload.get("xac_nhan_can_cu_thu_cong") is True)
        if path == "duyet":
            return crm.duyet(me, payload.get("id"))
        if path == "duyet-v4":
            return crm.duyet_v4(me, payload.get("id"))
        if path == "tu-choi":
            return crm.tu_choi(me, payload.get("id"), payload.get("ly_do"))
        if path == "mapping":
            return crm.cap_nhat_mapping(me, payload.get("id"), payload.get("mapping") or {})
        if path == "m1-sao-ke":
            return self.crm_m1_sao_ke(crm, me, payload.get("mau"))
        if path == "lien-ket":
            return crm.lien_ket(me, payload.get("tien"), payload.get("lich"), payload.get("so_tien"), payload.get("khoa"))
        if path == "go-lien-ket":
            return crm.go_lien_ket(me, payload.get("id"), payload.get("ly_do"))
        if path == "file-soat":
            return crm.xuat_file_soat(me, payload.get("id"))
        raise DataError("NOT_FOUND", "Không có thao tác CRM này.")

    def crm_m1_sao_ke(self, crm, me, mau):
        """Tiền về qua đường M1 hiện có (Store.ingest + engine đề xuất) rồi bộ chiếu legacy→K2 — không tạo chứng từ tiền riêng của CRM."""
        from ..k2 import m1_demo
        from ..kiem_chung.fixtures_crm import SAO_KE_M1
        pn, _, dot = str(mau or "").partition(":")
        if dot not in SAO_KE_M1.get(pn, {}):
            raise DataError("CRM_TIEN_MAU", "Không có sao kê DEMO này.")
        admin = self._crm_ket_noi()[1]  # chỉ cho tiến trình con bộ chiếu (qua biến môi trường), không vào trình duyệt/log
        if not admin:
            raise DataError("CRM_M1_CHUA_CAU_HINH", "Chưa cấu hình tài khoản chủ CSDL DEMO cho bộ chiếu M1 → K2.")
        crm.kiem_nhan_tien(me, pn)
        doi_tac = {"PN_DEMO_A": "KH_DEMO.A01", "PN_DEMO_B": "KH_DEMO.B01"}[pn]
        facts = crm.fact_hop_dong_m1(me, pn)  # fact HĐ/lịch hiệu lực cho context engine M1 (TL32 §3.2)
        m1 = m1_demo.nhan_sao_ke(self.demo_config, self.root / "crm-m1", pn, SAO_KE_M1[pn][dot], me, doi_tac, hop_dong=facts)
        chieu = m1_demo.chieu_sang_k2(m1["sqlite"], admin)
        if not chieu["ok"]:
            raise DataError("CRM_M1_CHIEU_LOI", "Bộ chiếu M1 → K2 báo lệch/lỗi: " + json.dumps({k: v for k, v in chieu.items() if k != "ma_thoat"}, ensure_ascii=False))
        return {"m1": {k: v for k, v in m1.items() if k != "sqlite"}, "chieu": chieu}

    @staticmethod
    def _ghi_proof_tien(admin, pn):
        """Verifier proof encoding tiền (R4) bằng tài khoản chủ CSDL như bộ chiếu — chung cho BANK dùng ở CRM và M9."""
        from ..k2 import m1_demo
        from ..k2.crm_khoi_dong import nap_driver
        with nap_driver().connect(admin, autocommit=True) as conn:
            return m1_demo.ghi_proof_tien(conn, pn)

    # --- M9 DEMO: khoản vay typed trên cùng K2/phiên/cookie/khóa thao tác với CRM ---
    _m9 = None

    def m9(self):
        if self._m9 is None:
            from ..k2.vay import VayK2
            crm = self.crm()
            self._m9 = VayK2(crm.conn, self.root / "crm-k2", hom_nay=crm.hom_nay)
        return self._m9

    def m9_state(self, me, query=None):
        query = query or {}
        try:
            m9 = self.m9()
        except DataError as exc:
            if exc.code == "CRM_CHUA_CAU_HINH":
                return {"cau_hinh": False, "ly_do": str(exc)}
            raise
        from ..kiem_chung.fixtures_m9 import MAU, SAO_KE_M9
        demo = self._demo_vai_cu(m9.conn)
        try:
            data = self._crm_db(lambda: m9.danh_sach(me, ngay_xem=(query.get("ngay") or [None])[0], biet_den=(query.get("biet_den") or [None])[0]))
        except DataError as exc:
            if exc.code not in {"KHONG_CO_QUYEN_MODULE", "KHONG_CO_QUYEN_PHAP_NHAN"}:
                raise
            data = {"nguoi": {"dang_nhap": me}, "khong_quyen": str(exc), "khoan_vay": [], "snapshot": [], "anh_xa": [], "tien": [], "file_soat": [], "viec": []}
        return {"cau_hinh": True, **data, "danh_tinh_demo": demo, "mau": sorted(MAU),
                "tien_mau": [f"{pn}:{dot}" for pn in sorted(SAO_KE_M9) for dot in SAO_KE_M9[pn]], "m1_cau_hinh": bool(self._crm_ket_noi()[1])}

    def m9_action(self, sid, path, payload):
        return self._crm_db(self._m9_action, sid, path, payload)

    def _m9_action(self, sid, path, payload):
        sid, me, _ = self.crm_phien(sid)
        m9 = self.m9()
        payload = self.crm_body(payload)
        g = payload.get
        if path == "danh-tinh":
            m9.danh_tinh(g("dang_nhap"))
            self._crm_phien[sid] = g("dang_nhap")
            return {"dang_nhap": g("dang_nhap")}
        routes = {
            "mau": lambda: m9.nhan_mau(me, g("mau")),
            "anh-xa": lambda: m9.xac_nhan_anh_xa(me, g("kind"), g("cong_ty"), g("dich"), source_value=g("nguon"), ly_do=g("ly_do") or ""),
            "anh-xa/anh-huong": lambda: m9.anh_huong_anh_xa(me, g("id")),
            "anh-xa/dong": lambda: m9.dong_anh_xa(me, g("id"), g("ly_do")),
            "lap": lambda: m9.lap_phien_ban(me, g("snapshot"), g("phap_nhan")),
            "pham-vi": lambda: m9.xac_nhan_pham_vi(me, g("hop_dong"), g("lua_chon"), g("ly_do")),
            "kiem": lambda: m9.kiem(me, g("id")),
            "duyet": lambda: m9.duyet(me, g("id")),
            "duyet-v4": lambda: m9.duyet_v4(me, g("id")),
            "tu-choi": lambda: m9.tu_choi(me, g("id"), g("ly_do")),
            "m1-sao-ke": lambda: self.m9_m1_sao_ke(m9, me, g("mau")),
            "goi-y": lambda: m9.goi_y_noi(me, g("tien")),
            "xem-truoc": lambda: m9.xem_truoc_noi(me, g("tien"), g("phan_bo")),
            "xac-nhan": lambda: m9.xac_nhan_noi(me, g("tien"), g("phan_bo"), g("khoa"), g("xem_truoc_token")),
            "go": lambda: m9.go_noi(me, g("id"), g("ly_do"), g("khoa")),
            "file-soat": lambda: m9.xuat_file_soat(me, g("id")),
        }
        if path not in routes:
            raise DataError("NOT_FOUND", "Không có thao tác M9 này.")
        return routes[path]()

    def m9_m1_sao_ke(self, m9, me, mau):
        """Tiền đi/về của khoản vay qua đường M1 hiện có + bộ chiếu + proof encoding — không tạo SAO_KE/bút toán 112 từ M9."""
        from ..k2 import m1_demo
        from ..kiem_chung.fixtures_m9 import NGAN_HANG, SAO_KE_M9
        pn, _, dot = str(mau or "").partition(":")
        if dot not in SAO_KE_M9.get(pn, {}):
            raise DataError("M9_TIEN_MAU", "Không có sao kê DEMO khoản vay này.")
        admin = self._crm_ket_noi()[1]
        if not admin:
            raise DataError("CRM_M1_CHUA_CAU_HINH", "Chưa cấu hình tài khoản chủ CSDL DEMO cho bộ chiếu M1 → K2.")
        m9.kiem_nhan_tien(me, pn)
        m1 = m1_demo.nhan_sao_ke(self.demo_config, self.root / "crm-m1", pn, SAO_KE_M9[pn][dot], me, NGAN_HANG[pn])
        chieu = m1_demo.chieu_sang_k2(m1["sqlite"], admin)
        if not chieu["ok"]:
            raise DataError("CRM_M1_CHIEU_LOI", "Bộ chiếu M1 → K2 báo lệch/lỗi: " + json.dumps({k: v for k, v in chieu.items() if k != "ma_thoat"}, ensure_ascii=False))
        return {"m1": {k: v for k, v in m1.items() if k != "sqlite"}, "chieu": chieu, "proof": self._ghi_proof_tien(admin, pn)}

    def m9_file(self, sid, lo_id):
        sid, me, _ = self.crm_phien(sid)
        return self._crm_db(self.m9().tep_file_soat, me, lo_id)

    def crm_file(self, sid, lo_id):
        sid, me, _ = self.crm_phien(sid)
        return self._crm_db(self.crm().tep_file_soat, me, lo_id)

    def crm_receive(self, sid, raw, info):
        sid, me, _ = self.crm_phien(sid)
        allowed = {"phap_nhan", "loai_hinh", "loai_ban", "hop_dong_goc", "ma_hop_dong_chung", "doi_tac_object_id", "du_an"}
        if not isinstance(info, dict) or set(info) - allowed:
            raise DataError("CRM_ENVELOPE", "Thông tin nhận tệp #6 có trường ngoài phạm vi.")
        return self._crm_db(self.crm().nhan_ket_qua_6, me, raw, {"namespace": "TRICH_6_DEMO_UPLOAD", **info})

    # --- CRM-41-01: hồ sơ Word thô → engine trích DÙNG CHUNG #6 (common/v1) → đường nhận kết quả #6 hiện có
    CRM_TRICH_ENV = {"phap_nhan", "loai_hinh", "loai_ban", "hop_dong_goc", "ma_hop_dong_chung", "doi_tac_object_id", "du_an"}
    CRM_TRICH_YC = {"loai_hop_dong", "tham_so", "request_id"}

    def crm_trich_chuan_bi(self, sid, info):
        """Dưới mutation lock NGẮN: chụp danh tính phiên + kiểm hình thức envelope/yêu cầu (không nhận URL/đường dẫn/actor từ trình duyệt)."""
        sid, me, _ = self.crm_phien(sid)
        if not isinstance(info, dict) or set(info) - (self.CRM_TRICH_ENV | {"trich"}) or not isinstance(info.get("trich"), dict) \
                or set(info["trich"]) != self.CRM_TRICH_YC:
            raise DataError("CRM_ENVELOPE", "Thông tin trích hồ sơ Word có trường ngoài phạm vi hoặc thiếu yêu cầu trích.")
        self.crm()  # cấu hình + lineage CRM hợp lệ trước khi mở kết nối riêng
        return me

    def crm_trich(self, me, raw, info):
        """NGOÀI mutation lock: kết nối login ứng dụng RIÊNG cho thao tác dài (không dùng kết nối CRM đệm), đóng ở mọi nhánh."""
        from ..k2.crm import CrmK2
        from ..k2.crm_khoi_dong import kiem_role_ung_dung, nap_driver
        psycopg = nap_driver()
        from psycopg.rows import dict_row
        client = self.trich6_client(self.root / "crm-k2")  # CRM-41-01-06: factory theo app (engine DEMO sở hữu hoặc seam host cấp), không từ trình duyệt
        dsn, _ = self._crm_ket_noi()
        if not dsn:
            raise DataError("CRM_CHUA_CAU_HINH", "CRM DEMO chưa được cấu hình kết nối PostgreSQL cục bộ.")
        try:
            conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        except psycopg.Error:
            raise DataError("PG_KHONG_KET_NOI", "Không mở được kết nối riêng cho trích hồ sơ.") from None
        try:
            kiem_role_ung_dung(conn)
            rieng = CrmK2(conn, self.root / "crm-k2", hom_nay=self.crm().hom_nay)
            yc = info["trich"]
            env = {k: v for k, v in info.items() if k != "trich"}
            return self._crm_db(lambda: rieng.trich_tu_docx(me, raw, env, loai_hop_dong=yc["loai_hop_dong"], tham_so=yc["tham_so"],
                                                             request_id=yc["request_id"], client=client))
        finally:
            conn.close()

    # --- M5 DEMO: phiếu kho nguồn #10 (nhận nguồn trước PN → typed → lịch sử/review/file soát) trên cùng K2/phiên/cookie/khóa thao tác ---
    _m5 = None
    M5_TRINH_DUYET_KHONG_DUOC = ("actor", "nguoi", "dang_nhap_thuc_hien", "phap_nhan_id", "trusted", "PROVEN", "proven", "PN", "module", "resolved_measurement_facts",
                                 "quantity_evidence", "mapping_revision", "ratio", "approval", "trang_thai", "nguoi_duyet", "accepted", "eligible")

    def m5(self):
        if self._m5 is None:
            from ..k2.kho_so_luong import KhoSoLuongK2
            crm = self.crm()  # cùng kết nối login ứng dụng + cổng lineage của CRM cho mọi route đọc
            self._m5 = KhoSoLuongK2(crm.conn, self.root / "m5-k2", conn_chu=self._m5_ket_noi_chu(crm.conn), hom_nay=crm.hom_nay)
        return self._m5

    def _m5_ket_noi_chu(self, app_conn):
        """Kết nối máy chủ (chủ bảng) riêng cho intake/FILE_SOAT M5 — dùng lại admin DSN cục bộ đã qua validator loopback/endpoint (như bộ chiếu M1);
        kiểm đích thực + đúng chủ bảng. Không có admin DSN → None (intake/file báo chưa cấu hình; route đọc vẫn chạy). Không log/trả DSN."""
        admin = self._crm_ket_noi()[1]
        if not admin:
            return None
        from ..k2.crm_khoi_dong import kiem_ket_noi_chu, nap_driver
        psycopg = nap_driver()
        from psycopg.rows import dict_row
        try:
            chu = psycopg.connect(admin, autocommit=True, row_factory=dict_row)
        except psycopg.Error:
            raise DataError("PG_KHONG_KET_NOI", "Không kết nối được máy chủ PostgreSQL DEMO cho nhận nguồn M5.") from None
        try:
            kiem_ket_noi_chu(chu, app_conn)
        except Exception:
            chu.close()
            raise
        return chu

    def m5_body(self, payload):
        for key in self.M5_TRINH_DUYET_KHONG_DUOC:
            if key in payload:
                raise DataError("M5_CLIENT_AUTHORITY", "Danh tính, PN, quyền, facts đo lường/tỉ lệ/duyệt do máy chủ xác định; không nhận từ trình duyệt.")
        return payload

    def m5_state(self, me, query):
        try:
            m5 = self.m5()
        except DataError as exc:
            if exc.code == "CRM_CHUA_CAU_HINH":
                return {"cau_hinh": False, "ly_do": str(exc)}
            raise
        from ..k2.m5_demo import MAU, dang_nhap_m5
        # I3: bộ chọn vai M5 = đúng 8 login trong registry đã pin, giao với người dùng đang hoạt động do máy chủ tra (không mọi mo_phong)
        demo = [dict(r) for r in m5.conn.execute("""SELECT dang_nhap, vai_tro FROM master.nguoi_dung WHERE mo_phong AND trang_thai = 'HOAT_DONG'
                                                     AND dang_nhap = ANY(%s) ORDER BY dang_nhap""", (dang_nhap_m5(),))]
        q = lambda k: (query.get(k) or [None])[0] or None  # noqa: E731
        try:
            data = self._crm_db(lambda: m5.danh_sach(me, phap_nhan=q("phap_nhan"), ma_kho=q("ma_kho"), ky=q("ky"), trang_thai=q("trang_thai"),
                                                      trang=int(q("trang") or 1)))
        except DataError as exc:  # không có M5 nghiệp vụ: vẫn xem phần nguồn (nếu có năng lực) và đổi vai DEMO
            if exc.code not in {"KHONG_CO_QUYEN_MODULE", "KHONG_CO_QUYEN_PHAP_NHAN"}:
                raise
            data = {"nguoi": {"dang_nhap": me}, "khong_quyen": str(exc), "phieu": [], "viec": [], "file_soat": [], "tong": 0}
        return {"cau_hinh": True, **data, "nguon": self._crm_db(m5.nguon_danh_sach, me), "nang_luc_nguon": self._crm_db(m5.nang_luc_cua_toi, me),
                "pham_vi_nguon": self._crm_db(m5.pham_vi_cua_toi, me), "danh_tinh_demo": demo, "mau": list(MAU), "may_chu_nhan": m5.conn_chu is not None}

    def m5_get(self, sid, path, query):
        sid, me, _ = self.crm_phien(sid)
        m5 = self.m5()
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "phieu":
            return self._crm_db(m5.chi_tiet, me, parts[1])
        if path == "kiem-ke":
            return self._crm_db(m5.kiem_ke, me)
        if path == "ton-nguon":
            return self._crm_db(m5.ton_nguon, me)
        if len(parts) == 2 and parts[0] == "nguon":
            return self._crm_db(m5.nguon_chi_tiet, me, parts[1])
        raise DataError("NOT_FOUND", "Không có chức năng M5 này.")

    def m5_action(self, sid, path, payload):
        return self._crm_db(self._m5_action, sid, path, payload)

    def _m5_action(self, sid, path, payload):
        sid, me, _ = self.crm_phien(sid)
        m5 = self.m5()
        payload = self.m5_body(payload)
        g = payload.get
        if path == "danh-tinh":
            from ..k2.m5_demo import dang_nhap_m5
            if g("dang_nhap") not in dang_nhap_m5():  # I3: chỉ đúng 8 vai M5 của registry (selector CRM/M1 khác giữ nguyên)
                raise DataError("DANH_TINH_M5", "Vai mô phỏng không thuộc 8 vai M5 của registry DEMO.")
            m5.danh_tinh(g("dang_nhap"))  # chỉ danh tính mô phỏng hoạt động; đổi phiên của trình duyệt này
            self._crm_phien[sid] = g("dang_nhap")
            return {"dang_nhap": g("dang_nhap")}
        if path == "nhan":
            from ..k2.nguon_chung import VANG
            loi_bao = payload["reported_errors"] if "reported_errors" in payload else VANG  # I2: hiện diện phải là list, không ép `or []`
            if g("mau") is not None:
                if set(payload) - {"mau", "khoa"}:
                    raise DataError("M5_YEU_CAU_SAI", "Nhận mẫu chỉ gồm mẫu + khóa.")
                from ..k2.m5_demo import mau
                mm = mau(g("mau"))
                return m5.nhan(me, source_instance=mm["source_instance"], scope_ref=None, coverage=mm["coverage"], reported_errors=mm["reported_errors"],
                               client_key=g("khoa"), native=mm["native"], master=mm["master"])
            if set(payload) - {"source_instance", "scope_ref", "coverage", "reported_errors", "khoa", "native_b64", "master_b64"}:
                raise DataError("M5_YEU_CAU_SAI", "Thông tin nhận nguồn có trường ngoài phạm vi (không nhận đường dẫn/URL/token/facts).")
            import base64
            import binascii
            try:
                native = base64.b64decode(g("native_b64"), validate=True) if g("native_b64") is not None else None
                master = base64.b64decode(g("master_b64"), validate=True) if g("master_b64") is not None else None
            except (ValueError, TypeError, binascii.Error):
                raise DataError("M5_ARTIFACT", "Artifact phải là base64 hợp lệ của bytes tệp.") from None
            return m5.nhan(me, source_instance=g("source_instance"), scope_ref=g("scope_ref"), coverage=g("coverage"), reported_errors=loi_bao,
                           client_key=g("khoa"), native=native, master=master)
        if path == "mapping":
            return m5.cap_nhat_mapping(me, payload)
        if path == "nguon/kiem-lai":
            return m5.kiem_lai_nguon(me, payload)
        if path == "xuat-file-soat":
            # repair03 §4: body chỉ mang phiếu + khóa + expected (ba con trỏ + token basis do máy chủ trả ở chi tiết); không facts/đường dẫn
            if set(payload) - {"phieu_id", "khoa", "latest_truoc", "accepted_truoc", "eligible_truoc", "co_so_truoc"}:
                raise DataError("M5_YEU_CAU_SAI", "Yêu cầu file soát có trường ngoài phạm vi (chỉ phiếu, khóa, con trỏ và token basis đang xem).")
            return m5.xuat_file_soat(me, payload)
        if path.startswith("lien-ket/"):  # R16: liên kết số lượng thật (preview đọc 0 ghi / xác nhận / undo) — body do lien_ket_chung kiểm whitelist
            return m5.lien_ket(me, path[len("lien-ket/"):], payload)
        if path.startswith("l11/"):
            return self._l11_action(m5, sid, me, path[len("l11/"):], payload)
        raise DataError("NOT_FOUND", "Không có thao tác M5 này.")

    # --- L11 số lượng R16: bộ chọn vai đúng 2 login L11 đã seed; mọi authority (PN/kind/hệ số/owner/duyệt) do máy chủ/CSDL dẫn xuất
    def _l11_action(self, m5, sid, me, path, payload):
        g = payload.get
        if path == "danh-tinh":
            from ..k2.l11_demo import dang_nhap_l11
            if g("dang_nhap") not in dang_nhap_l11():
                raise DataError("DANH_TINH_L11", "Vai mô phỏng không thuộc 2 vai L11 DEMO.")
            m5.danh_tinh(g("dang_nhap"))
            self._crm_phien[sid] = g("dang_nhap")
            return {"dang_nhap": g("dang_nhap")}
        if path == "proof/nhan":
            from ..k2.nguon_chung import VANG
            if set(payload) - {"source_instance", "scope_ref", "coverage", "reported_errors", "khoa", "native_b64", "fixture_ref"}:
                raise DataError("L11_YEU_CAU_SAI", "Nhận bằng chứng chỉ gồm nguồn/phạm vi/coverage/lỗi báo/khóa và đúng một: bytes base64 hoặc mẫu DEMO.")
            native = None
            if g("native_b64") is not None:
                import base64
                import binascii
                try:
                    native = base64.b64decode(g("native_b64"), validate=True)
                except (ValueError, TypeError, binascii.Error):
                    raise DataError("M5_ARTIFACT", "Bằng chứng phải là base64 hợp lệ của bytes tệp.") from None
            return m5.l11_nhan_bang_chung(me, source_instance=g("source_instance"), scope_ref=g("scope_ref"), coverage=g("coverage"),
                                          reported_errors=payload["reported_errors"] if "reported_errors" in payload else VANG, client_key=g("khoa"),
                                          native=native, fixture_ref=g("fixture_ref"))
        if path == "proof/xac-nhan":
            return m5.l11_xac_nhan_bang_chung(me, payload)
        if path == "proof/huy":
            return m5.l11_huy_bang_chung(me, payload)
        if path == "ma-hoa":
            return m5.l11_ma_hoa(me, payload)
        if path == "file-soat":
            return m5.l11_xuat_file(me, payload)
        raise DataError("NOT_FOUND", "Không có thao tác L11 này.")

    def l11_state(self, me):
        try:
            m5 = self.m5()
        except DataError as exc:
            if exc.code == "CRM_CHUA_CAU_HINH":
                return {"cau_hinh": False, "ly_do": str(exc)}
            raise
        from ..k2.l11_demo import PROOF_FILES, dang_nhap_l11
        demo = [dict(r) for r in m5.conn.execute("""SELECT dang_nhap, vai_tro FROM master.nguoi_dung WHERE mo_phong AND trang_thai = 'HOAT_DONG'
                                                     AND dang_nhap = ANY(%s) ORDER BY dang_nhap""", (dang_nhap_l11(),))]
        try:
            # R4 repair02: toàn aggregate hiển thị (dòng/mã hóa/parent/token FILE/bằng chứng/ứng viên/phạm vi/hành động) từ MỘT snapshot RR
            data = self._crm_db(m5.l11_trang, me)
        except DataError as exc:
            if exc.code not in {"KHONG_CO_QUYEN_PHAP_NHAN", "DANH_TINH", "DANH_TINH_MO_PHONG"}:
                raise
            data = {"nguoi": {"dang_nhap": me}, "khong_quyen": str(exc), "dong_hoa_don": [], "dong_phieu": [], "ma_hoa": [], "lien_ket": [], "bang_chung": [],
                    "ung_vien": [], "pham_vi_bang_chung": []}
        return {"cau_hinh": True, **data, "danh_tinh_demo": demo, "mau_bang_chung": sorted(PROOF_FILES), "may_chu_nhan": m5.conn_chu is not None}

    def l11_proof(self, sid):
        """GET /api/m5/l11/proof: danh sách bằng chứng theo quyền nguồn/BOTH READ hiện hành, snapshot RR riêng của chính nó."""
        sid, me, _ = self.crm_phien(sid)
        return self._crm_db(self.m5().l11_bang_chung, me)

    def m5_file(self, sid, lo_id):
        sid, me, _ = self.crm_phien(sid)
        return self._crm_db(self.m5().tep_file_soat, me, lo_id)

    def m5_raw(self, sid, receipt_id, vai_tro):
        sid, me, _ = self.crm_phien(sid)
        return self._crm_db(self.m5().nguon_raw, me, receipt_id, vai_tro)

    # --- M2 DEMO R15: hóa đơn mua XML/ZIP → nguồn trước PN → M2 (danh tính/phiên bản/core) → CFO map dòng → CFO tuyến; cùng K2/phiên/cookie/khóa ---
    _m2 = None
    M2_TRINH_DUYET_KHONG_DUOC = M5_TRINH_DUYET_KHONG_DUOC + ("dsn", "path", "duong_dan", "url", "factor", "he_so", "proof", "approved", "identity",
                                                           "canonical_identity", "semantic_sha256", "mapping_id", "line_facts")

    def m2(self):
        if self._m2 is None:
            from ..k2.hoa_don import HoaDonK2
            crm = self.crm()
            self._m2 = HoaDonK2(crm.conn, self.root / "m2-k2", conn_chu=self._m5_ket_noi_chu(crm.conn), hom_nay=crm.hom_nay)
        return self._m2

    def m2_body(self, payload):
        for key in self.M2_TRINH_DUYET_KHONG_DUOC:
            if key in payload:
                raise DataError("M2_CLIENT_AUTHORITY", "Danh tính, PN, quyền, mapping/proof/hệ số/định danh do máy chủ xác định; không nhận từ trình duyệt.")
        return payload

    def m2_state(self, me, query):
        try:
            m2 = self.m2()
        except DataError as exc:
            if exc.code == "CRM_CHUA_CAU_HINH":
                return {"cau_hinh": False, "ly_do": str(exc)}
            raise
        from ..k2.hoa_don import TAI_LEN_TOI_DA_BYTE
        from ..k2.m2_demo import dang_nhap_m2, mau_danh_sach
        demo = [dict(r) for r in m2.conn.execute("""SELECT dang_nhap, vai_tro FROM master.nguoi_dung WHERE mo_phong AND trang_thai = 'HOAT_DONG'
                                                     AND dang_nhap = ANY(%s) ORDER BY dang_nhap""", (dang_nhap_m2(),))]
        q = lambda k: (query.get(k) or [None])[0] or None  # noqa: E731
        try:
            data = self._crm_db(lambda: m2.danh_sach(me, phap_nhan=q("phap_nhan"), ky=q("ky"), trang=int(q("trang") or 1)))
        except DataError as exc:  # không có M2 nghiệp vụ: vẫn xem phần nguồn (nếu có năng lực) và đổi vai DEMO
            if exc.code not in {"KHONG_CO_QUYEN_MODULE", "KHONG_CO_QUYEN_PHAP_NHAN"}:
                raise
            data = {"nguoi": {"dang_nhap": me}, "khong_quyen": str(exc), "hoa_don": [], "tong": 0}
        return {"cau_hinh": True, **data, "nguon": self._crm_db(m2.nguon_danh_sach, me), "nang_luc_nguon": self._crm_db(m2.nang_luc_cua_toi, me),
                "pham_vi_nguon": self._crm_db(m2.pham_vi_cua_toi, me), "danh_tinh_demo": demo, "mau": mau_danh_sach(), "may_chu_nhan": m2.conn_chu is not None,
                "gioi_han_tai_len_byte": TAI_LEN_TOI_DA_BYTE}

    def m2_get(self, sid, path, query):
        sid, me, _ = self.crm_phien(sid)
        m2 = self.m2()
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "hoa-don":
            return self._crm_db(m2.chi_tiet, me, parts[1])
        if len(parts) == 2 and parts[0] == "nguon":
            return self._crm_db(m2.nguon_chi_tiet, me, parts[1])
        raise DataError("NOT_FOUND", "Không có chức năng M2 này.")

    def m2_action(self, sid, path, payload):
        return self._crm_db(self._m2_action, sid, path, payload)

    def _m2_action(self, sid, path, payload):
        sid, me, _ = self.crm_phien(sid)
        m2 = self.m2()
        payload = self.m2_body(payload)
        g = payload.get
        if path == "danh-tinh":
            from ..k2.m2_demo import dang_nhap_m2
            if g("dang_nhap") not in dang_nhap_m2():  # chỉ đúng 8 vai M2 của declarations
                raise DataError("DANH_TINH_M2", "Vai mô phỏng không thuộc 8 vai M2 của declarations DEMO.")
            m2.danh_tinh(g("dang_nhap"))
            self._crm_phien[sid] = g("dang_nhap")
            return {"dang_nhap": g("dang_nhap")}
        if path == "nhan":
            from ..k2.nguon_chung import VANG
            loi_bao = payload["reported_errors"] if "reported_errors" in payload else VANG
            if g("mau") is not None:
                if set(payload) - {"mau", "khoa", "source_instance", "scope_ref", "coverage"}:
                    raise DataError("M2_YEU_CAU_SAI", "Nhận mẫu chỉ gồm mẫu + khóa + nguồn/phạm vi/coverage.")
                from ..k2.m2_demo import mau
                ten, raw = mau(g("mau"))
                return m2.nhan(me, source_instance=g("source_instance"), scope_ref=g("scope_ref"), coverage=g("coverage"), reported_errors=VANG,
                               client_key=g("khoa"), native=raw, artifact_name=ten)
            if set(payload) - {"source_instance", "scope_ref", "coverage", "reported_errors", "khoa", "native_b64", "crosswalk_b64", "artifact_name"}:
                raise DataError("M2_YEU_CAU_SAI", "Thông tin nhận nguồn có trường ngoài phạm vi (không nhận đường dẫn/URL/token/facts).")
            import base64
            import binascii
            try:
                native = base64.b64decode(g("native_b64"), validate=True) if g("native_b64") is not None else None
                crosswalk = base64.b64decode(g("crosswalk_b64"), validate=True) if g("crosswalk_b64") is not None else None
            except (ValueError, TypeError, binascii.Error):
                raise DataError("M2_ARTIFACT", "Artifact phải là base64 hợp lệ của bytes tệp.") from None
            return m2.nhan(me, source_instance=g("source_instance"), scope_ref=g("scope_ref"), coverage=g("coverage"), reported_errors=loi_bao,
                           client_key=g("khoa"), native=native, artifact_name=g("artifact_name"), crosswalk=crosswalk)
        if path == "mapping":
            if set(payload) - {"source_instance", "company_key", "phap_nhan", "revision_hien_tai", "ly_do", "khoa"}:
                raise DataError("M2_YEU_CAU_SAI", "Mapping công ty chỉ gồm nguồn, company key, PN đích, revision mong đợi, lý do, khóa.")
            return m2.mapping_company(me, payload)
        if path == "mapping-line":
            if set(payload) - {"hoa_don_id", "expected_graph", "source_row_id", "logical_line_key", "evidence_ref", "evidence_revision", "ly_do", "khoa"}:
                raise DataError("M2_YEU_CAU_SAI", "Mapping dòng chỉ gồm hóa đơn, token đồ thị, dòng nguồn, khóa dòng logic, bằng chứng literal + revision, lý do, khóa.")
            return m2.mapping_line(me, client_key=g("khoa"), hoa_don_id=g("hoa_don_id"), expected_graph=g("expected_graph"),
                                   source_row_id=g("source_row_id"), logical_line_key=g("logical_line_key"), evidence_ref=g("evidence_ref"),
                                   evidence_revision=g("evidence_revision"), reason=g("ly_do"))
        if path == "nguon/kiem-lai":
            if set(payload) - {"hoa_don_id", "observation_id", "expected_graph", "ly_do", "khoa"}:
                raise DataError("M2_YEU_CAU_SAI", "Chọn nguồn chỉ gồm hóa đơn, quan sát mới nhất, token đồ thị, lý do, khóa.")
            return m2.xem_xet_nguon(me, payload)
        if path == "route":
            if set(payload) - {"hoa_don_id", "cau_noi_id", "dich", "expected_route_id", "expected_graph", "ly_do", "khoa"}:
                raise DataError("M2_YEU_CAU_SAI", "Tuyến chỉ gồm hóa đơn, cầu nối, đích, tuyến mong đợi, token đồ thị, lý do, khóa.")
            return m2.route(me, payload)
        if path.startswith("lien-ket/"):
            return m2.lien_ket()
        raise DataError("NOT_FOUND", "Không có thao tác M2 này.")

    def m2_raw(self, sid, receipt_id, vai_tro):
        sid, me, _ = self.crm_phien(sid)
        return self._crm_db(self.m2().nguon_raw, me, receipt_id, vai_tro)


M5_MA_409 = frozenset({"CAPTURE_KHAC_NOI_DUNG", "IDEMPOTENCY_KHAC", "KHO_VERSION_CHANGED", "ANH_XA_CHONG_LAN", "ANH_XA_REVISION_SAI", "ANH_XA_DA_CO",
                       "KHO_RETARGET_IMPACT", "KHO_SOURCE_REAPPROVAL_REVIEW", "KY_DA_KHOA",
                       # R16 L11: stale/vượt lượng/bằng chứng/nguồn không đủ điều kiện/khóa kỳ → 409 (legacy classifier)
                       "L11_VERSION_CHANGED", "L11_CLOSURE_MO_RONG", "L11_VUOT_SO_LUONG_HOA_DON", "L11_VUOT_SO_LUONG_PHIEU", "L11_TY_LE_XUNG_DOT",
                       "L11_BANG_CHUNG_DA_XAC_NHAN", "L11_BANG_CHUNG_DA_THU_HOI", "L11_BANG_CHUNG_HOLD", "L11_DA_HUY", "L11_MA_HOA_DA_CO",
                       "L11_POOL_HOA_DON_BI_CHAN", "L11_POOL_PHIEU_BI_CHAN", "L11_HOA_DON_KHONG_DU_DIEU_KIEN", "L11_PHIEU_KHONG_DU_DIEU_KIEN",
                       "L11_TUYEN_KHONG_PHAI_KHO", "L11_MAPPING_KHONG_HIEN_HANH", "L11_DON_VI_POOL_KHAC", "L11_MA_HOA_HOA_DON_KHONG_HIEN_HANH",
                       "L11_MA_HOA_PHIEU_KHONG_HIEN_HANH", "L11_CHA_KHONG_PHAI_L11",
                       # repair02: khóa closure/đo lường/miền bằng chứng — xung đột trạng thái hiện hành, thử lại sau khi xem lại
                       "L11_KHOA_GOC_THIEU", "L11_DO_LUONG_KHONG_HIEN_HANH", "L11_BANG_CHUNG_HANG_NGOAI_MIEN"})
M5_MA_403 = frozenset({"NGUON_KHONG_CO_QUYEN", "KHONG_CO_QUYEN_PHAP_NHAN", "KHONG_CO_QUYEN_MODULE", "KHONG_CO_QUYEN_HANH_DONG", "KHONG_CO_QUYEN_LOAI_VIEC",
                       "KHONG_CO_QUYEN_SOURCE_REVIEW", "KHONG_CO_QUYEN_FILE_SOAT", "ANH_XA_KHONG_CO_QUYEN", "BIEN_NHAN_KHONG_CO_QUYEN",
                       "BIEN_NHAN_M5_CHI_CHU", "LO_M5_CHI_CHU", "STAGE_ACTOR_SAI", "STAGE_CHI_MAY_CHU", "M5_CLIENT_AUTHORITY", "DANH_TINH_M5",
                       "KET_QUA_CUOI_CHI_CHU",
                       "KHONG_CO_QUYEN_L11_LIEN_KET", "KHONG_CO_QUYEN_L11_BANG_CHUNG", "KHONG_CO_QUYEN_L11_MA_HOA", "KHONG_CO_QUYEN_L11_FILE",
                       "KHONG_CO_QUYEN_L11_XEM", "L11_CHI_CHU", "L11_CHA_CHI_CHU", "DANH_TINH_L11", "L11_CLIENT_AUTHORITY", "L11_CAP_KHAC_PHAP_NHAN"})


M2_MA_409 = frozenset({"CAPTURE_KHAC_NOI_DUNG", "IDEMPOTENCY_KHAC", "M2_VERSION_CHANGED", "ANH_XA_CHONG_LAN", "ANH_XA_REVISION_SAI", "ANH_XA_DA_CO",
                       "M2_DONG_DA_MAP", "M2_LOGIC_DA_DUNG", "M2_ROUTE_STALE", "M2_ROUTE_KHONG_DOI", "M2_CHI_QUAN_SAT_MOI_NHAT",
                       "M2_DONG_NGUON_KHONG_HIEN_HANH", "M2_MAPPING_KHONG_HIEN_HANH", "M2_MAPPING_CONG_TY_DOI", "M2_ROUTE_CHUA_CO_CAU_NOI"})
M2_MA_403 = frozenset({"NGUON_KHONG_CO_QUYEN", "KHONG_CO_QUYEN_PHAP_NHAN", "KHONG_CO_QUYEN_MODULE", "KHONG_CO_QUYEN_HANH_DONG", "KHONG_CO_QUYEN_LOAI_VIEC",
                       "KHONG_CO_QUYEN_M2_MAP", "KHONG_CO_QUYEN_M2_ROUTE", "KHONG_CO_QUYEN_M2_SOURCE_REVIEW", "ANH_XA_KHONG_CO_QUYEN",
                       "BIEN_NHAN_KHONG_CO_QUYEN", "BIEN_NHAN_M2_CHI_CHU", "M2_CHI_CHU", "CHUNG_TU_M2_CHI_CHU", "STAGE_ACTOR_SAI", "STAGE_CHI_MAY_CHU",
                       "M2_CLIENT_AUTHORITY", "DANH_TINH_M2", "KET_QUA_CUOI_CHI_CHU"})


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, app, port=8766):
        self.app = app
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"


class Handler(BaseHTTPRequestHandler):
    server_version = "KhoTriThucLocal"

    def log_message(self, *_):
        # No filenames, notes or source contents in console request logs.
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError):
            # Closing a browser or a readiness probe may close the socket early.
            # Atomic raw/receipt publication remains responsible for retry safety.
            pass

    def send_content(self, status, content, mime="application/json; charset=utf-8", headers=None):
        if not isinstance(content, bytes):
            content = canonical_json(content).encode("utf-8")
        self.send_response(status)
        for key, value in {
            "Content-Type": mime, "Content-Length": str(len(content)), "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            **(headers or {}),
        }.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(content)

    def authorize(self, private=False):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if host not in allowed:
            raise DataError("LOCAL_HOST_ONLY", "Chỉ mở giao diện bằng địa chỉ local của ứng dụng.")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise DataError("CROSS_ORIGIN", "Không nhận yêu cầu từ website khác.")
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://" + h for h in allowed}:
            raise DataError("CROSS_ORIGIN", "Không nhận yêu cầu từ website khác.")
        if private and not secrets.compare_digest(self.headers.get("X-KTT-Token", ""), self.server.app.token):
            raise DataError("SESSION_TOKEN", "Phiên giao diện đã đổi. Tải lại trang rồi thử lại.")

    def body(self, limit=MAX_FILE_SIZE):
        if self.headers.get("Transfer-Encoding"):
            raise DataError("REQUEST_LENGTH", "Cần khai báo độ dài nội dung.")
        value = self.headers.get("Content-Length", "")
        if not value.isdigit() or len(value) > 12:
            raise DataError("REQUEST_LENGTH", "Độ dài nội dung không hợp lệ.")
        length = int(value)
        if length > limit:
            raise DataError("FILE_TOO_LARGE", "Mỗi tệp tối đa 50 MB.")
        content = self.rfile.read(length)
        if len(content) != length:
            raise DataError("INCOMPLETE_UPLOAD", "Tệp chưa được truyền đủ; hãy thử lại.")
        return content

    def json_body(self, limit=1024 * 1024):
        raw = self.body(limit)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise DataError("INVALID_REQUEST", "Nội dung yêu cầu phải là JSON UTF-8 hợp lệ.") from exc
        if not isinstance(value, dict):
            raise DataError("INVALID_REQUEST", "Yêu cầu phải là một object JSON.")
        return value

    def crm_sid(self):
        for part in self.headers.get("Cookie", "").split(";"):
            key, _, value = part.strip().partition("=")
            if key == self.server.app.CRM_COOKIE:
                return value
        return None

    def that(self):
        if not self.server.app.is_that:
            raise DataError("THAT_UI", "Chức năng này chỉ có trong giao diện kho thật.")
        return self.server.app.operations

    def do_GET(self):
        self.handle_route(False)

    def do_POST(self):
        self.handle_route(True)

    def do_OPTIONS(self):
        self.send_content(403, {"error": "CROSS_ORIGIN", "message": "Giao diện chỉ dùng tại máy này."})

    def handle_route(self, post):
        try:
            path = urlsplit(self.path).path
            query = parse_qs(urlsplit(self.path).query)
            self.authorize(private=post or path.startswith("/api/") and path != "/api/health")
            app = self.server.app
            if path.startswith("/api/tham-quyen/"):
                from . import ma_tran_tham_quyen as mtq_http
                # Module tự lấy mutation_lock; chuyển cả đường lạ để trả 404.
                return mtq_http.dieu_huong(self, app, post, path, query)
            if path.startswith("/api/m4-request"):  # M4-6: ĐÚNG ba route Request nháp, TRƯỚC dispatcher /api/m4* chung; route lạ cùng tiền tố rơi xuống đó → 404
                from . import m4_request as m4_request_http
                if path in m4_request_http.ROUTE:  # query THÔ giữ giá trị rỗng (x=, version_id=, lặp có rỗng) để dieu_huong từ chối 400 — parse_qs mặc định sẽ nuốt chúng
                    return m4_request_http.dieu_huong(self, app, post, path, parse_qs(urlsplit(self.path).query, keep_blank_values=True))
            if path.startswith(("/api/m4", "/m4")):  # M4-01: HTTP mỏng riêng (giao_dien/m4.py), cùng token/phiên/mutation lock
                from . import m4 as m4_http
                return m4_http.dieu_huong(self, app, post, path, query)
            from . import crm_g as crm_g_http  # CRM-41-02: G1 mẫu/G7 bộ chuẩn — trước route CRM cũ; POST /api/crm/mau (#6) giữ handler cũ
            if crm_g_http.la_route(post, path):
                return crm_g_http.dieu_huong(self, app, post, path, query)
            from . import m2_tai_hoa_don as m2_thue_http  # M2-00E: nút "Tải từ cổng thuế" — trước route /api/m2/ chung
            if m2_thue_http.la_route(post, path):
                return m2_thue_http.dieu_huong(self, app, post, path, query)
            if not post:
                if path == "/api/health":
                    return self.send_content(200, {"application": "kho-tri-thuc-local", "version": __version__, "local_only": True, "root_id": app.root_id,
                                                    "started_at": _STARTED_AT, "pid": os.getpid(),
                                                    "trich6": app.trich6_suc_khoe()})  # CRM-41-01-06: readiness KHÔNG bí mật (không URL/cổng/token)
                if path in {"/", "/index.html"}:
                    raw = (ASSETS / ("that.html" if app.is_that else "index.html")).read_bytes().replace(b"__KTT_TOKEN__", app.token.encode())
                    return self.send_content(200, raw, "text/html; charset=utf-8")
                if path in {"/app.js", "/style.css", "/that.css", "/mark.svg", "/crm_g.js"} or path in {"/m2_tai_hoa_don.js", "/ma_tran_tham_quyen.js"}:  # Tài sản riêng; giữ whitelist CRM đã ghim trong test.
                    mime = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}[Path(path).suffix]
                    asset = "that.js" if path == "/app.js" and app.is_that else path[1:]
                    return self.send_content(200, (ASSETS / asset).read_bytes(), mime)
                if path == "/api/state":
                    return self.send_content(200, app.state())
                if path == "/api/sample":
                    source = query.get("source", [""])[0]
                    return self.send_content(200, app.demo_sample(source), headers={"Content-Disposition": f'attachment; filename="{source}_MO_PHONG.json"'})
                if path.startswith("/api/files/") and path.endswith("/download"):
                    identifier = path.split("/")[3]
                    receipt, content = app.intake.download(identifier)
                    return self.send_content(200, content, "application/octet-stream", {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(receipt["name"], safe="")})
                if path == "/api/that/job":
                    return self.send_content(200, self.that().job(query.get("id", [""])[0]))
                if path == "/api/that/knowledge":
                    category = query.get("category", [None])[0]
                    return self.send_content(200, self.that().knowledge_rows(category, query.get("q", [""])[0], int(query.get("page", ["1"])[0])))
                if path == "/api/that/catalog":
                    return self.send_content(200, self.that().catalog(query.get("date", [""])[0], query.get("cutoff", [now_utc()])[0]))
                if path == "/api/that/source-settings":
                    return self.send_content(200, self.that().source_settings())
                if path == "/api/that/overview":
                    return self.send_content(200, self.that().overview())
                if path == "/api/that/runs":
                    return self.send_content(200, self.that().runs())
                if path == "/api/that/history":
                    return self.send_content(200, self.that().history())
                if path == "/api/that/cfo-rules":
                    return self.send_content(200, self.that().cfo_rules())
                if path == "/api/that/invoice-months":
                    return self.send_content(200, self.that().invoice_months())
                if path == "/api/that/knowledge-cards":
                    return self.send_content(200, self.that().knowledge_cards(query.get("q", [""])[0]))
                if path == "/api/that/report":
                    return self.send_content(200, self.that().report(query.get("attempt_id", [""])[0]))
                if path == "/api/that/proposals":
                    return self.send_content(200, self.that().proposal_rows(query.get("session_id", [""])[0], query.get("at", [now_utc()])[0]))
                if path.startswith("/api/that/quick/") and path.endswith("/download"):
                    parts = path.split("/")
                    if len(parts) != 6 or parts[:4] != ["", "api", "that", "quick"]:
                        raise DataError("QUICK_EXPORT_FILE", "Đường dẫn tải tệp xuất không hợp lệ.")
                    name, raw = self.that().quick_file(parts[4], query.get("file", [""])[0])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                             {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path == "/api/that/quick":
                    return self.send_content(200, self.that().quick_rows(query.get("run_id", [""])[0]))
                if path == "/api/that/outside-catalog/download":
                    raw = self.that().outside_catalog()
                    return self.send_content(200, raw, "application/json; charset=utf-8", {"Content-Disposition": "attachment; filename=MA-NGOAI-DANH-MUC.json"})
                if path == "/api/crm":
                    with app.mutation_lock:
                        sid, me, moi = app.crm_phien(self.crm_sid(), tao=True)
                        headers = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
                        return self.send_content(200, app.crm_state(me), headers=headers)
                if path == "/api/demo/vai":
                    if app.is_that:
                        raise DataError("THAT_UI", "Bản vận hành không có bộ chọn vai DEMO.")
                    if parse_qs(urlsplit(self.path).query, keep_blank_values=True):
                        raise DataError("INVALID_REQUEST", "Bộ chọn vai DEMO không nhận tham số truy vấn.")
                    with app.mutation_lock:
                        sid, me, moi = app.crm_phien(self.crm_sid(), tao=True)
                        headers = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
                        return self.send_content(200, app._crm_db(app.demo_vai, me), headers=headers)
                if path.startswith("/api/crm/file-soat/"):
                    with app.mutation_lock:
                        name, raw = app.crm_file(self.crm_sid(), path.split("/")[-1])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                             {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path == "/api/m9":
                    with app.mutation_lock:
                        sid, me, moi = app.crm_phien(self.crm_sid(), tao=True)
                        headers = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
                        return self.send_content(200, app.m9_state(me, query), headers=headers)
                if path.startswith("/api/m9/file-soat/"):
                    with app.mutation_lock:
                        name, raw = app.m9_file(self.crm_sid(), path.split("/")[-1])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                             {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path == "/api/m5":
                    with app.mutation_lock:
                        sid, me, moi = app.crm_phien(self.crm_sid(), tao=True)
                        headers = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
                        return self.send_content(200, app.m5_state(me, query), headers=headers)
                if path == "/api/m5/l11":  # R16: trang liên kết số lượng (tạo phiên cookie như /api/m5)
                    with app.mutation_lock:
                        sid, me, moi = app.crm_phien(self.crm_sid(), tao=True)
                        headers = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
                        return self.send_content(200, app.l11_state(me), headers=headers)
                if path == "/api/m5/l11/proof":  # R4 repair02: GET bằng chứng thật (handoff01 §6), không suy từ aggregate
                    with app.mutation_lock:
                        return self.send_content(200, app.l11_proof(self.crm_sid()))
                if path.startswith("/api/m5/file-soat/"):
                    with app.mutation_lock:
                        name, raw = app.m5_file(self.crm_sid(), path.split("/")[-1])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                             {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path.startswith("/api/m5/nguon/") and path.count("/") == 6 and path.split("/")[5] == "raw":
                    parts = path.split("/")
                    with app.mutation_lock:
                        name, raw = app.m5_raw(self.crm_sid(), parts[4], parts[6])
                    return self.send_content(200, raw, "application/octet-stream", {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path.startswith("/api/m5/"):
                    with app.mutation_lock:
                        return self.send_content(200, app.m5_get(self.crm_sid(), path[len("/api/m5/"):], query))
                if path == "/api/m2":
                    with app.mutation_lock:
                        sid, me, moi = app.crm_phien(self.crm_sid(), tao=True)
                        headers = {"Set-Cookie": f"{app.CRM_COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict"} if moi else None
                        return self.send_content(200, app.m2_state(me, query), headers=headers)
                if path.startswith("/api/m2/nguon/") and path.count("/") == 6 and path.split("/")[5] == "raw":
                    parts = path.split("/")
                    with app.mutation_lock:
                        name, raw = app.m2_raw(self.crm_sid(), parts[4], parts[6])
                    return self.send_content(200, raw, "application/octet-stream", {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path.startswith("/api/m2/"):
                    with app.mutation_lock:
                        return self.send_content(200, app.m2_get(self.crm_sid(), path[len("/api/m2/"):], query))
                if path == "/api/nghiem-thu":
                    with app.mutation_lock:
                        return self.send_content(200, app.nt_list())
                if path == "/api/nghiem-thu/sample":
                    kind = query.get("kind", [""])[0]
                    return self.send_content(200, app.nt_sample(kind), headers={"Content-Disposition": f'attachment; filename="nghiem_thu_{quote(kind, safe="")}_MO_PHONG.json"'})
                if path.startswith("/api/nghiem-thu/file-soat/"):
                    name, raw = app.nt_file(path.split("/")[-1])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                             {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
                if path.startswith("/api/that/shadow/") and path.endswith("/download"):
                    parts = path.split("/")
                    name, raw = self.that().shadow_file(parts[4], parts[5])
                    return self.send_content(200, raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name, safe="")})
            else:
                if path == "/api/upload":
                    encoded = self.headers.get("X-File-Info", "")
                    if len(encoded) > 20000:
                        raise DataError("FILE_METADATA", "Thông tin tệp quá dài.")
                    metadata = read_json(unquote(encoded).encode("utf-8"))
                    result = app.intake.receive(self.body(), metadata)
                    return self.send_content(200 if result["duplicate"] else 201, result)
                if path == "/api/that/source":
                    encoded = self.headers.get("X-Source-Info", "")
                    if len(encoded) > 20000:
                        raise DataError("SOURCE_UPLOAD_METADATA", "Thông tin tệp nguồn quá dài.")
                    metadata = json.loads(unquote(encoded))
                    return self.send_content(201, self.that().receive_source(self.body(), metadata))
                if path == "/api/that/quick/upload":
                    encoded = self.headers.get("X-Quick-Info", "")
                    metadata = json.loads(unquote(encoded))
                    raw = self.body()
                    operations = self.that()
                    return self.send_content(201, operations.start("dinh-khoan", lambda report: operations.quick_upload(raw, metadata.get("name"), metadata.get("relative_path", ""), progress=report), progress=True))
                if path == "/api/that/quick/invoice-month":
                    payload = self.json_body()
                    operations = self.that()
                    return self.send_content(201, operations.start("hoa-don-thang", lambda report: operations.quick_invoice_month(payload.get("month"), progress=report), progress=True))
                if path == "/api/that/quick/repropose":
                    payload = self.json_body()
                    operations = self.that()
                    return self.send_content(202, operations.start("de-xuat-lai", lambda report: operations.quick_repropose(payload.get("run_id"), progress=report), progress=True))
                if path == "/api/that/quick/decide":
                    payload = self.json_body()
                    return self.send_content(200, self.that().quick_decide(payload.get("run_id"), payload.get("items"), payload.get("actor", "CFO_NTD"), payload.get("at", now_utc())))
                if path == "/api/that/quick/ai-note":
                    payload = self.json_body()
                    return self.send_content(200, self.that().quick_ai_note(payload.get("run_id"), payload.get("id"), payload.get("note", ""), payload.get("actor", "CFO_NTD")))
                if path == "/api/that/quick/ai-context":
                    payload = self.json_body()
                    return self.send_content(200, self.that().quick_ai_context(payload.get("run_id"), payload.get("ids")))
                if path == "/api/that/quick/score":
                    payload = self.json_body()
                    return self.send_content(200, self.that().quick_score(payload.get("run_id")))
                if path == "/api/that/quick/export":
                    payload = self.json_body()
                    return self.send_content(200, self.that().quick_export(payload.get("run_id"), junsky_files=payload.get("junsky_files", False) is True, actor=payload.get("actor", "CFO_NTD")))
                if path == "/api/that/reload":
                    self.json_body()
                    return self.send_content(202, self.that().reload_sources())
                if path == "/api/that/learning-settings":
                    return self.send_content(200, self.that().save_learning_settings(self.json_body()))
                if path == "/api/that/cfo-rules/toggle":
                    payload = self.json_body()
                    return self.send_content(200, self.that().toggle_cfo_rule(payload.get("ma"), payload.get("bat")))
                if path == "/api/that/cash-mapping":
                    payload = self.json_body()
                    return self.send_content(200, self.that().set_cash_mapping(payload.get("bank_account"), payload.get("cash_account") or None))
                if path == "/api/that/open":
                    payload = self.json_body()
                    if payload.get("ai_folder") is True:
                        return self.send_content(200, self.that().open_ai_folder())
                    return self.send_content(200, self.that().open_export(payload.get("run_id"), payload.get("file") or None))
                if path == "/api/that/source-settings":
                    payload = self.json_body()
                    return self.send_content(200, self.that().save_source_settings(payload))
                if path == "/api/that/knowledge/import":
                    encoded = self.headers.get("X-Knowledge-Info", "")
                    metadata = json.loads(unquote(encoded))
                    return self.send_content(201, self.that().knowledge_upload(self.body(), metadata.get("name"), metadata.get("actor"), metadata.get("at"), metadata.get("catalog_valid_from")))
                if path == "/api/that/ingest":
                    payload = self.json_body()
                    return self.send_content(202, self.that().start("nap-nguon", lambda: self.that().ingest(payload)))
                if path == "/api/that/knowledge/decide":
                    payload = self.json_body()
                    return self.send_content(200, self.that().decide_knowledge(payload.get("items"), payload.get("actor"), payload.get("at")))
                if path == "/api/that/session/run":
                    payload = self.json_body()
                    return self.send_content(202, self.that().start("chay-de-xuat", lambda: self.that().run_session(payload)))
                if path == "/api/that/proposals/decide":
                    payload = self.json_body()
                    return self.send_content(200, self.that().decide_proposals(payload.get("session_id"), payload.get("items"), payload.get("actor"), payload.get("at")))
                if path == "/api/that/shadow/export":
                    payload = self.json_body()
                    return self.send_content(202, self.that().start("xuat-mo-phong", lambda: self.that().shadow_export(payload.get("session_id"), payload.get("actor"), payload.get("at"))))
                if path == "/api/crm/trich6":  # CRM-41-01: lock chỉ bao bước chụp danh tính; engine/kết nối riêng chạy ngoài lock
                    encoded = self.headers.get("X-CRM-Info", "")
                    if len(encoded) > 4000:
                        raise DataError("CRM_ENVELOPE", "Thông tin trích quá dài.")
                    info = json.loads(unquote(encoded) or "{}")
                    raw = self.body()
                    with app.mutation_lock:
                        me = app.crm_trich_chuan_bi(self.crm_sid(), info)
                    return self.send_content(200, app.crm_trich(me, raw, info))
                if path == "/api/crm/nhan":
                    encoded = self.headers.get("X-CRM-Info", "")
                    if len(encoded) > 4000:
                        raise DataError("CRM_ENVELOPE", "Thông tin nhận tệp quá dài.")
                    info = json.loads(unquote(encoded) or "{}")
                    raw = self.body()
                    with app.mutation_lock:
                        return self.send_content(200, app.crm_receive(self.crm_sid(), raw, info))
                if path.startswith("/api/crm/"):
                    payload = self.json_body()
                    with app.mutation_lock:
                        return self.send_content(200, app.crm_action(self.crm_sid(), path[len("/api/crm/"):], payload))
                if path.startswith("/api/m9/"):
                    payload = self.json_body()
                    with app.mutation_lock:
                        return self.send_content(200, app.m9_action(self.crm_sid(), path[len("/api/m9/"):], payload))
                if path.startswith("/api/m5/"):
                    payload = self.json_body()
                    with app.mutation_lock:
                        return self.send_content(200, app.m5_action(self.crm_sid(), path[len("/api/m5/"):], payload))
                if path.startswith("/api/m2/"):
                    try:  # JSON 1 MiB chứa đủ base64 (4/3) của TAI_LEN_TOI_DA_BYTE + trường; vượt → thông báo đúng giới hạn M2 (không phải "50 MB")
                        payload = self.json_body()
                    except DataError as exc:
                        if exc.code != "FILE_TOO_LARGE":
                            raise
                        from ..k2.hoa_don import TAI_LEN_TOI_DA_BYTE
                        raise DataError("M2_TEP_QUA_LON", f"Yêu cầu M2 vượt giới hạn: tổng tệp hóa đơn + crosswalk tối đa {TAI_LEN_TOI_DA_BYTE} byte mỗi lần nhận.") from None
                    with app.mutation_lock:
                        return self.send_content(200, app.m2_action(self.crm_sid(), path[len("/api/m2/"):], payload))
                if path == "/api/nghiem-thu/nhan":
                    name = unquote(self.headers.get("X-File-Name", "review.json"))
                    raw = self.body()
                    with app.mutation_lock:
                        return self.send_content(200, app.nt_receive(raw, name))
                if path in {"/api/nghiem-thu/mau", "/api/nghiem-thu/xac-nhan", "/api/nghiem-thu/quyet-dinh", "/api/nghiem-thu/xuat"}:
                    payload = self.json_body()
                    with app.mutation_lock:
                        if path.endswith("/mau"):
                            return self.send_content(200, app.nt_seed(payload.get("mau")))
                        if path.endswith("/xac-nhan"):
                            return self.send_content(200, app.nt_confirm(payload))
                        if path.endswith("/quyet-dinh"):
                            return self.send_content(200, app.nt_decide(payload))
                        return self.send_content(200, app.nt_export(payload))
                if path in {"/api/demo/validate", "/api/demo/ingest"}:
                    name = unquote(self.headers.get("X-File-Name", "fixture.json"))
                    with app.mutation_lock:
                        report = app.demo_import(self.body(), name, path.endswith("ingest"))
                    return self.send_content(200, report)
                if path == "/api/shutdown":
                    self.body(1024)
                    self.send_content(200, {"stopped": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
            self.send_content(404, {"error": "NOT_FOUND", "message": "Không tìm thấy chức năng này."})
        except DataError as exc:
            status = 403 if exc.code in {"LOCAL_HOST_ONLY", "CROSS_ORIGIN", "SESSION_TOKEN"} else 413 if exc.code in {"FILE_TOO_LARGE", "M2_TEP_QUA_LON"} else 400
            if status == 400 and urlsplit(self.path).path.startswith("/api/m5"):  # M5: 403 phạm vi / 409 xung đột / 501 L11 chưa phát hành
                status = 409 if exc.code in M5_MA_409 else 403 if exc.code in M5_MA_403 else 501 if exc.code == "M5_L11_CHUA_PHAT_HANH" else 400
            if status == 400 and urlsplit(self.path).path.startswith("/api/m2"):  # M2: cùng phân loại, mã riêng của M2
                status = 409 if exc.code in M2_MA_409 else 403 if exc.code in M2_MA_403 else 501 if exc.code == "M2_L11_CHUA_PHAT_HANH" else 400
            self.send_content(status, {"error": exc.code, "message": str(exc)})
        except (ValueError, TypeError, KeyError, RecursionError):
            self.send_content(400, {"error": "INVALID_REQUEST", "message": "Thông tin gửi lên không hợp lệ; tệp chưa được xử lý."})
        except (OSError, sqlite3.Error):
            self.send_content(500, {"error": "LOCAL_STORAGE_ERROR", "message": "Không đọc/ghi được kho trên máy. Kiểm tra dung lượng, quyền và thử lại."})


def _mo_trich6(host):
    """Khởi động engine DEMO NGOÀI luồng phục vụ (health trả DANG_KHOI_DONG trong lúc chờ). Lỗi chỉ in mã ngắn — không token/đường dẫn."""
    try:
        host.start()
        print("Engine trích #6 DEMO: sẵn sàng (instance " + host.instance_id + ").", flush=True)
    except Exception as exc:  # noqa: BLE001
        print("Engine trích #6 DEMO chưa sẵn sàng (" + str(getattr(exc, "ma", type(exc).__name__)) + ").", flush=True)


def serve(config_path, root, port=8766, open_browser=True, trich6_nguon=None):
    if not 1 <= port <= 65535:
        raise DataError("INVALID_PORT", "Cổng phải từ 1 đến 65535.")
    app = LocalApp(config_path, root)
    host = None
    if not app.is_that:  # CRM-41-01-06: chỉ đường serve()/CLI DEMO sở hữu engine; kho THẬT không tự mở engine
        from ..nguon.trich6_host import NGUON_MAC_DINH, Trich6Host
        host = Trich6Host(app.root / "trich6-demo", Path(trich6_nguon) if trich6_nguon else NGUON_MAC_DINH)
        app.trich6_host, app.trich6_quan_ly = host, True   # đánh dấu quản lý TRƯỚC spawn
    try:
        with LocalServer(app, port) as server:
            print(f"Kho tri thức: {server.url} — chỉ trên máy này. Nhấn Ctrl+C để dừng.", flush=True)
            if host is not None:
                threading.Thread(target=_mo_trich6, args=(host,), daemon=True).start()
            if open_browser:
                webbrowser.open(server.url)
            try:
                server.serve_forever(poll_interval=0.2)
            except KeyboardInterrupt:
                pass
    finally:
        if host is not None:
            host.stop()   # dừng đúng engine của instance này (central bị buộc dừng: Job đóng → engine chết theo)
        from . import m2_tai_hoa_don
        m2_tai_hoa_don.dung(app)   # M2-00E: đóng M2 thì tắt bộ tải #7 sở hữu (nếu đã mở)


def main():
    parser = argparse.ArgumentParser(description="Giao diện HTML nội bộ của Kho tri thức")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--trich6-source", type=Path, default=None, help="Thư mục mã nguồn engine #6 (host tin cậy; mặc định theo quyết định engine chung)")
    args = parser.parse_args()
    serve(args.config, args.root, args.port, not args.no_browser, args.trich6_source)


if __name__ == "__main__":
    main()
