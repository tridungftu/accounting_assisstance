"""M2 bridge R15 repair03 (R4 tuple tài liệu khai báo đơn vị: t17; phần còn lại giữ từ repair02) — service `HoaDonK2` + seed `m2_demo` + M0015 trên PostgreSQL thật — coder viết, CHƯA CHẠY (CODE_ONLY/UNRUN).

Chỉ chạy khi root cấp KHO_PG_DSN_TEST (DB DEMO mới; không DB thật). Kỳ vọng số đếm lấy từ `tests/fixtures/m2_bridge/workflow.json` (oracle test,
runtime KHÔNG đọc). 8 hàng literal được seed admit làm ứng viên bằng chứng thô; CFO thật chọn đúng ref/revision, CSDL đối chiếu lại với dòng thực.
Thứ tự: workflow tối thiểu G01 → CFO map dòng → CFO tuyến KHO → G03 ZIP; rồi G04/lifecycle/intercompany/thiếu ngày/đơn vị/STT/reorder/forgery/
crosswalk/sentinel/shape-NULL/đơn vị/thu hồi quyền. Replay dùng NGUYÊN body/token A (chỉ `lap_lai` False→True khác). Không DROP DB/role, không xóa
thư mục tạm, không DELETE dữ liệu: giữ làm bằng chứng (nhánh DELETE của guard core chỉ kiểm tĩnh ở test migration).
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import unittest
import uuid
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None

from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.k2 import m2_demo

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get("KHO_PG_DSN_TEST")
BRIDGE = ROOT / "tests" / "fixtures" / "m2_bridge"
XMLFIX = ROOT / "tests" / "fixtures" / "m2_invoice_xml"
INST, SCOPE = "DEMO_M2_XML_INSTANCE_A", "DEMO_M2_SCOPE_BOTH_COMPANIES_V1"
INTAKE, NOSRC, KTA, KTB = "MO_PHONG_M0_HD_INTAKE", "MO_PHONG_HD_NO_SOURCE", "MO_PHONG_KT_MUA_A", "MO_PHONG_KT_MUA_B"
CFOA, CFOB, VIEWA, M1A = "MO_PHONG_CFO_MUA_A", "MO_PHONG_CFO_MUA_B", "MO_PHONG_VIEW_MUA_A", "MO_PHONG_M1_ONLY_MUA_A"
M5_ACTORS = ("MO_PHONG_M0_KHO_A", "MO_PHONG_M0_KHO_B", "MO_PHONG_KT_KHO_A", "MO_PHONG_KT_KHO_B", "MO_PHONG_CFO_KHO_A", "MO_PHONG_CFO_KHO_B",
             "MO_PHONG_VIEW_KHO_A", "MO_PHONG_M1_ONLY_KHO_A")


def _pin(path: Path, sha: str) -> bytes:
    raw = path.read_bytes()
    assert sha256(raw) == sha, f"{path.name} khác pin"
    return raw


WORKFLOW = json.loads(_pin(BRIDGE / "workflow.json", "d559f07890608407834ff653124605d0bd6a9ce399e3f57ac0365a1f641d2ae0").decode("utf-8"))
LINE_FACTS = json.loads(_pin(BRIDGE / "line-facts.json", "2195792bef97a1c94773f7fbe3391192e0ed24e872dfd904ac90ed54ba3b41fd").decode("utf-8"))
XMAN = {f["path"]: f for f in json.loads(_pin(XMLFIX / "manifest.json", "43ad28257ca646b9d43f45ed34a8c441131328cca1b576cf247b378224e2b177")
                                          .decode("utf-8"))["files"]}


def artifact(rel: str) -> bytes:
    return _pin(XMLFIX / rel, XMAN[rel]["sha256"])


G01 = artifact("inputs/G01-wrapped-positive.xml") if (XMLFIX / "manifest.json").exists() else b""
F = LINE_FACTS["rows"]  # 0..3: G01/G03 tương đương; 4..7: G05 order-a/b


def ev(i: int) -> dict:
    """Tham chiếu ứng viên literal i (ref + revision) — chỉ bằng chứng; CSDL tự resolve/đối chiếu."""
    return {"evidence_ref": F[i]["mapping_ref"], "evidence_revision": F[i]["revision"]}


def bo_lap_lai(r: dict) -> dict:
    return {k: v for k, v in r.items() if k != "lap_lai"}


@unittest.skipUnless(psycopg is not None and ADMIN_DSN, "Không có psycopg hoặc KHO_PG_DSN_TEST — test PostgreSQL M2 không chạy (không tính đạt)")
class M2K2Pg(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kho_tri_thuc.k2 import crm_demo, m5_demo
        from kho_tri_thuc.k2.crm_khoi_dong import kiem_ket_noi_chu
        from kho_tri_thuc.k2.hoa_don import HoaDonK2
        cls.db = "kho_test_m2_" + uuid.uuid4().hex[:8]
        with psycopg.connect(ADMIN_DSN, autocommit=True) as a:
            a.execute(f'CREATE DATABASE "{cls.db}" ENCODING \'UTF8\' TEMPLATE template0')
        cls.dsn = ADMIN_DSN.rsplit("/", 1)[0] + "/" + cls.db
        cls.admin = psycopg.connect(cls.dsn, autocommit=True)
        crm_demo.khoi_tao(cls.admin)
        m5_demo.khoi_tao(cls.admin)
        cls.m5_truoc = cls.m5_snapshot()  # quyền/năng lực actor M5 hiện hành trước seed M2: seed M2 (và mở lại) không cấp thêm/không đổi
        pn = cls.admin.execute("SELECT id FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'").fetchone()[0]
        cls.old_m1 = cls.admin.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, so_tien_minor, hash)
                                          VALUES (%s,'HD_MUA','SENT-M1-HDMUA','2026-08-01','VND',1100,%s) RETURNING id""", (pn, "1" * 64)).fetchone()[0]
        cls.admin.execute("INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, mo_ta, no_minor, co_minor) VALUES (%s,1,'sentinel',1100,0)", (cls.old_m1,))
        cls.old_m1_json = cls.sentinel_m1()
        cls.seed1 = m2_demo.khoi_tao(cls.admin)
        cls.seed2 = m2_demo.khoi_tao(cls.admin)
        cls.role, pw = "ktt_test_m2_" + uuid.uuid4().hex[:8], secrets.token_hex(16)
        cls.admin.execute(f"CREATE ROLE {cls.role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE app_web")
        cls.app_dsn = f"postgresql://{cls.role}:{pw}@{cls.dsn.split('@', 1)[1]}"
        opts = "-c lock_timeout=20000 -c statement_timeout=60000"
        cls.app = psycopg.connect(cls.app_dsn, autocommit=True, row_factory=dict_row, options=opts)
        cls.chu = psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row, options=opts)
        kiem_ket_noi_chu(cls.chu, cls.app)
        cls.root = Path(tempfile.mkdtemp(prefix="ktt_m2_k2_"))
        cls.m2 = HoaDonK2(cls.app, cls.root, conn_chu=cls.chu)
        cls.state = {}

    @classmethod
    def tearDownClass(cls):
        for c in (cls.app, cls.chu, cls.admin):
            c.close()  # giữ DB/role/thư mục làm bằng chứng

    @classmethod
    def q(cls, sql, params=()):
        return cls.admin.execute(sql, params).fetchone()[0]

    @classmethod
    def m5_snapshot(cls):
        cua_m5 = """SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.id), '[]'::jsonb)::text FROM {t} x JOIN master.nguoi_dung n ON n.id = x.nguoi_dung_id
                    WHERE n.dang_nhap = ANY(%s)"""
        return {t: cls.q(cua_m5.format(t=t), (list(M5_ACTORS),)) for t in ("master.nang_luc_nguon", "master.phan_quyen")} | {
            t: cls.q(f"SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.id), '[]'::jsonb)::text FROM {t} x") for t in
            ("kho.phieu_kho_danh_tinh", "kho.phieu_kho_quan_sat")} | {
            "m5_nguoi_dung": cls.q("""SELECT jsonb_agg(to_jsonb(n) ORDER BY n.dang_nhap)::text FROM master.nguoi_dung n WHERE n.dang_nhap = ANY(%s)""",
                                   (list(M5_ACTORS),))}

    @classmethod
    def sentinel_m1(cls):
        return (cls.q("SELECT to_jsonb(x)::text FROM kho.chung_tu x WHERE x.id = %s", (cls.old_m1,)),
                cls.q("SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id)::text FROM kho.chung_tu_dong x WHERE x.chung_tu_id = %s", (cls.old_m1,)))

    def dem(self) -> dict:
        q = self.q
        return {"common_capture_receipts": q("SELECT count(*) FROM giao_tiep.lan_tiep_nhan_nguon WHERE source_instance_id = %s", (INST,)),
                "m2_identities": q("SELECT count(*) FROM kho.hoa_don_danh_tinh"),
                "m2_content_versions": q("SELECT count(*) FROM kho.hoa_don_phien_ban"),
                "core_headers_M2": q("SELECT count(*) FROM kho.chung_tu WHERE module_nghiep_vu = 'M2'"),
                "core_lines_M2": q("SELECT count(*) FROM kho.chung_tu_dong d JOIN kho.chung_tu c ON c.id = d.chung_tu_id WHERE c.module_nghiep_vu = 'M2'"),
                "typed_observations": q("SELECT count(*) FROM kho.hoa_don_quan_sat"),
                "logical_lines": q("SELECT count(*) FROM kho.hoa_don_dong_danh_tinh"),
                "approved_line_mappings": q("SELECT count(*) FROM master.anh_xa_nguon WHERE subject_kind = 'INVOICE_LINE' AND state = 'DA_DUYET'"),
                "version_line_bridges": q("SELECT count(*) FROM kho.hoa_don_dong_phien_ban"),
                "approved_routes": q("SELECT count(*) FROM kho.mua_dich_dong WHERE trang_thai = 'DA_DUYET'"),
                "business_receipts": q("SELECT count(*) FROM kho.bien_nhan_thao_tac WHERE module = 'M2'"),
                "source_rows": q("SELECT count(*) FROM kho.ban_ghi_nguon WHERE source_instance_id = %s", (INST,)),
                "native_source_snapshots": q("SELECT count(*) FROM kho.anh_chup_nguon WHERE source_instance_id = %s", (INST,))}

    def dem_phu(self) -> dict:
        """Delta phụ cho từ chối/replay: audit M2, stage, file nhận, tuyến/mapping mọi trạng thái."""
        q = self.q
        return {"audit": q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong LIKE 'M2_%%'"),
                "stage": q("SELECT count(*) FROM giao_tiep.stage_tin_cay"), "tep": q("SELECT count(*) FROM giao_tiep.tep_tiep_nhan"),
                "anh_xa": q("SELECT count(*) FROM master.anh_xa_nguon"), "tuyen": q("SELECT count(*) FROM kho.mua_dich_dong"),
                "ung_vien": q("SELECT count(*) FROM master.m2_ung_vien_dong")}

    def kiem_buoc(self, step: int):
        exp = {k: v for k, v in WORKFLOW["minimal_workflow"]["steps"][step - 1].items() if k not in ("step", "action")}
        self.assertEqual(self.dem(), exp, f"bước {step}")

    def core_m2(self, hd) -> str:
        return self.q("""SELECT jsonb_build_object('ct', (SELECT jsonb_agg(to_jsonb(c) ORDER BY c.id) FROM kho.chung_tu c
                                                      WHERE c.id IN (SELECT chung_tu_id FROM kho.hoa_don_phien_ban WHERE hoa_don_id = %s)),
                                'dong', (SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM kho.chung_tu_dong x
                                         WHERE x.chung_tu_id IN (SELECT chung_tu_id FROM kho.hoa_don_phien_ban WHERE hoa_don_id = %s)),
                                'nguon', (SELECT jsonb_agg(jsonb_build_array(b.id, b.derived_record_sha256) ORDER BY b.id) FROM kho.ban_ghi_nguon b
                                          WHERE b.snapshot_id IN (SELECT snapshot_id FROM kho.hoa_don_quan_sat WHERE hoa_don_id = %s)))::text""", (hd,) * 3)

    def nhan(self, actor, raw, khoa=None, **sua):
        tham = dict(source_instance=INST, scope_ref=SCOPE, coverage="COMPLETE_INPUT", client_key=khoa or "m2-" + uuid.uuid4().hex[:12], native=raw)
        tham.update(sua)
        return self.m2.nhan(actor, **tham)

    def raises(self, codes, fn):
        """codes: một mã hoặc tuple mã chấp nhận (vd RLS ẩn hàng → HOA_DON thay vì KHONG_CO_QUYEN — cả hai đều là từ chối trước ghi)."""
        with self.assertRaises((DataError, psycopg.Error)) as ctx:
            fn()
        msg = (getattr(ctx.exception, "code", "") or "") + " " + str(ctx.exception)
        self.assertTrue(any(c in msg for c in ((codes,) if isinstance(codes, str) else codes)), msg)

    def sql(self, login, sql, params=()):
        nd = self.q("SELECT id::text FROM master.nguoi_dung WHERE dang_nhap = %s", (login,))
        with self.app.transaction():
            self.app.execute("SELECT set_config('ktt.nguoi_dung_id', %s, true), set_config('ktt.nguoi_dung_dang_nhap', %s, true)", (nd, login))
            cur = self.app.execute(sql, params)
            return cur.fetchall() if cur.description else cur.rowcount

    def hd_g01(self):
        return self.q("""SELECT d.id::text FROM kho.hoa_don_danh_tinh d JOIN master.phap_nhan p ON p.id = d.phap_nhan_id
                         WHERE p.ma = 'PN_DEMO_A' AND d.mst_ban = 'DEMO_M2_SUPPLIER' AND d.ky_hieu = 'DEMO_SERIES_A' AND d.so_chuan = '1'""")

    def stable_ids(self, hd):
        return self.q("""SELECT jsonb_build_object('pb', (SELECT jsonb_agg(id ORDER BY id) FROM kho.hoa_don_phien_ban WHERE hoa_don_id = %s),
                                'core', (SELECT jsonb_agg(chung_tu_id ORDER BY chung_tu_id) FROM kho.hoa_don_phien_ban WHERE hoa_don_id = %s),
                                'logic', (SELECT jsonb_agg(id ORDER BY id) FROM kho.hoa_don_dong_danh_tinh WHERE hoa_don_id = %s),
                                'bridge', (SELECT jsonb_agg(id ORDER BY id) FROM kho.hoa_don_dong_phien_ban WHERE hoa_don_id = %s),
                                'map', (SELECT jsonb_agg(id ORDER BY id) FROM master.anh_xa_nguon WHERE target_hoa_don_id = %s),
                                'route', (SELECT jsonb_agg(id ORDER BY id) FROM kho.mua_dich_dong WHERE hoa_don_id = %s))::text""", (hd,) * 6)

    # ------------------------------------------------------------------ seed
    def test_t01_seed_mot_lan_khong_doi_m5(self):
        self.assertEqual((self.seed1["actor"], self.seed1["anh_xa_cong_ty"], self.seed1["tai_lieu"], self.seed1["don_vi"], self.seed1["ung_vien_dong"]),
                         (8, 2, 1, 1, 8))
        # 8 ứng viên literal giữ đủ (kể cả 4 delivery tương đương), digest canonical do CSDL kiểm; 0 mapping dòng/dòng logic do seed
        self.assertEqual(self.q("""SELECT count(*) FROM master.m2_ung_vien_dong WHERE source_document_sha256 = %s
                                   AND fact_sha256 = encode(sha256(convert_to(master.json_chuan(payload), 'UTF8')), 'hex')""",
                                (m2_demo.LINE_FACTS_SHA256,)), 8)
        self.assertEqual(self.q("SELECT count(*) FROM master.anh_xa_nguon WHERE subject_kind = 'INVOICE_LINE'"), 0)
        self.assertEqual(self.q("""SELECT count(*) FROM master.dinh_nghia_don_vi_luong
                                   WHERE definition_sha256 = encode(sha256(convert_to(master.json_chuan(payload), 'UTF8')), 'hex')
                                     AND definition_sha256 = %s""", (m2_demo.UNIT_PAYLOAD_SHA256,)), 1)  # canonical CSDL = canonical Python đã pin
        self.assertEqual({k: v for k, v in self.seed2.items() if k != "mo_lai_giu_quyen_hien_hanh"}, {k: 0 for k in self.seed2 if k != "mo_lai_giu_quyen_hien_hanh"})
        self.assertTrue(self.seed2["mo_lai_giu_quyen_hien_hanh"])
        self.assertEqual(self.m5_snapshot(), self.m5_truoc)  # actor/quyền/năng lực M5 (kể cả trạng thái đã thu hồi) không bị seed M2 cấp lại/đổi
        self.assertEqual(self.q("""SELECT count(*) FROM master.phan_quyen q JOIN master.nguoi_dung n ON n.id = q.nguoi_dung_id
                                   WHERE n.dang_nhap LIKE 'MO_PHONG_%%' AND ('M9' = ANY (q.module) OR (n.dang_nhap = ANY(%s) AND 'M5' = ANY (q.module)))""",
                                (m2_demo.dang_nhap_m2(),)), 0)
        self.assertEqual(self.q("SELECT count(*) FROM master.dinh_nghia_don_vi_luong WHERE reference_id = 'DEMO_M2_UNIT_CAI_V1'"), 1)
        self.assertNotEqual(self.q("SELECT profile_sha256 FROM master.nguon_profile WHERE source_instance_id = %s", (INST,)),
                            self.q("SELECT payload->>'profile_document_sha256' FROM master.nguon_profile WHERE source_instance_id = %s", (INST,)))
        self.assertEqual(self.dem(), {k: 0 for k in self.dem()})

    # ------------------------------------------------------------------ workflow tối thiểu
    def test_t02_g01_capture_khong_tu_map(self):
        r = self.nhan(INTAKE, G01, "m2-g01")
        self.state["g01"] = r
        self.assertEqual((r["lap_lai"], r["artifact_kind"], r["promote"]["module"], len(r["promote"]["items"])), (False, "XML", "M2", 1))
        self.kiem_buoc(1)
        self.assertEqual(self.q("""SELECT count(*) FROM kho.ban_ghi_nguon WHERE source_instance_id = %s AND (row_raw_sha256 IS NOT NULL OR hash_basis IS NULL
                                   OR derived_record_sha256 IS NULL)""", (INST,)), 0)  # không byte span giả; digest dẫn xuất do CSDL
        core = self.admin.execute("""SELECT c.loai, c.module_nghiep_vu, c.so_tien_minor, c.tien_te, c.trang_thai, c.ngay_nghiep_vu::text FROM kho.chung_tu c
                                     WHERE c.module_nghiep_vu = 'M2'""").fetchone()
        self.assertEqual(core, ("HD_MUA", "M2", None, None, "DANG_XU_LY", "2026-10-01"))
        self.assertEqual(self.admin.execute("""SELECT d.no_minor, d.co_minor, d.don_gia_minor, d.tai_khoan, d.so_luong::text FROM kho.chung_tu_dong d
                                               JOIN kho.chung_tu c ON c.id = d.chung_tu_id WHERE c.module_nghiep_vu = 'M2'""").fetchone()[:4],
                         (None, None, None, None))
        hd = self.hd_g01()
        self.assertIsNotNone(hd)
        ct = self.m2.chi_tiet(CFOA, hd)
        self.assertEqual(ct["dinh_danh"], F[0]["identity_tuple"])  # so tuple tự dẫn xuất với literal evidence (không nhận làm authority)
        self.assertEqual((len(ct["dong_nguon_hien_hanh"]), ct["cau_noi"], ct["tuyen"]), (1, [], []))
        # ứng viên khớp dòng hiện hành do CSDL lọc: fact01 (G01) + fact02 (G03 raw cùng bytes) — cùng dòng logic; không phải duyệt
        uv = ct["ung_vien_dong"]
        self.assertEqual(sorted((u["evidence_ref"], u["logical_line_key"]) for u in uv),
                         [(F[0]["mapping_ref"], "DEMO_LINE_G01_A"), (F[1]["mapping_ref"], "DEMO_LINE_G01_A")])
        self.assertEqual({u["source_row_id"] for u in uv}, {ct["dong_nguon_hien_hanh"][0]["source_row_id"]})
        self.assertEqual(ct["con_tro"]["accepted_source_observation_id"], ct["con_tro"]["latest_observation_id"])
        self.assertIsNotNone(ct["con_tro"]["eligible_content_id"])
        self.state["hd"], self.state["ct"] = hd, ct

    def test_t03_replay_va_409(self):
        truoc, blobs = self.dem(), sorted(p.name for p in (self.root / "m0-raw").iterdir())
        r = self.nhan(INTAKE, G01, "m2-g01")
        dau = self.state["g01"]
        self.assertEqual((r["lap_lai"], r["promote"], r["stage_id"], r["lan_tiep_nhan_id"]), (True, dau["promote"], dau["stage_id"], dau["lan_tiep_nhan_id"]))
        for sua in ({"coverage": "PARTIAL_INPUT"}, {"reported_errors": ["LOI_MOI"]}, {"native": artifact("inputs/G04-sale-a.xml")},
                    {"crosswalk": b'{"rows": []}'}):
            with self.subTest(sua=list(sua)):
                self.raises("CAPTURE_KHAC_NOI_DUNG", lambda: self.nhan(INTAKE, G01, "m2-g01", **sua))
        self.assertEqual((self.dem(), sorted(p.name for p in (self.root / "m0-raw").iterdir())), (truoc, blobs))

    def test_t04_truoc_mapping_bi_tu_choi_0_delta(self):
        hd, ct = self.state["hd"], self.m2.chi_tiet(CFOA, self.state["hd"])
        row = ct["dong_nguon_hien_hanh"][0]["source_row_id"]
        truoc, phu = self.dem(), self.dem_phu()
        body = dict(client_key="ml-x", hoa_don_id=hd, expected_graph=ct["expected_graph"], source_row_id=row, logical_line_key="DEMO_LINE_G01_A",
                    reason="DEMO", **ev(0))
        self.raises(("KHONG_CO_QUYEN", "HOA_DON"), lambda: self.m2.mapping_line(INTAKE, **body))  # intake actor không tự duyệt mapping
        self.raises(("KHONG_CO_QUYEN", "HOA_DON"), lambda: self.m2.mapping_line(CFOB, **body))  # CFO PN khác (RLS ẩn hoặc từ chối quyền)
        self.raises("KHONG_CO_QUYEN", lambda: self.m2.mapping_line(KTA, **body))
        sql_body = {"hoa_don_id": hd, "expected_graph": ct["expected_graph"], "source_row_id": row, "logical_line_key": "DEMO_LINE_G01_A",
                    "reason": "DEMO", "client_key": "ml-y", **ev(0)}
        self.raises("KHONG_CO_QUYEN_M2_MAP", lambda: self.sql(KTA, "SELECT kho.m2_mapping_dong(%s::jsonb)", (json.dumps(sql_body),)))
        self.raises("M2_VERSION_CHANGED", lambda: self.m2.mapping_line(CFOA, **(body | {"expected_graph": "0" * 64})))
        hdr = self.q("SELECT id::text FROM kho.ban_ghi_nguon WHERE source_instance_id = %s AND section = 'XML_HEADER'", (INST,))
        self.raises("M2_DONG_NGUON_KHONG_HIEN_HANH", lambda: self.m2.mapping_line(CFOA, **(body | {"source_row_id": hdr, "client_key": "ml-hdr"})))
        # R2: ứng viên literal phải resolve đúng ref/revision và khớp dòng/artifact/định danh thực + đúng dòng logic — mọi sai lệch từ chối cụ thể
        for i, (sua, ma) in enumerate((
                ({"evidence_ref": "DEMO_M2_LITERAL_LINE_FACT_99_V1"}, "M2_UNG_VIEN_KHONG_CO"),       # unknown ref
                ({"evidence_ref": "I-C-O:G01:1"}, "M2_UNG_VIEN_KHONG_CO"),                           # alias kiểu oracle không phải ref đã admit
                ({"evidence_revision": 2}, "M2_UNG_VIEN_KHONG_CO"),                                   # đúng ref sai revision
                (ev(4), "M2_UNG_VIEN_SAI_ARTIFACT"),                                                  # fact05 (G05) dùng cho dòng G01
                (ev(2), "M2_UNG_VIEN_SAI_ARTIFACT"),                                                  # fact03 (ZIP entry) cho XML trần
                ({"logical_line_key": "DEMO_LINE_TUY_Y"}, "M2_UNG_VIEN_SAI_DONG_LOGIC"),             # khóa logic tùy ý
                ({"logical_line_key": "DEMO_LINE_G05_A"}, "M2_UNG_VIEN_SAI_DONG_LOGIC"))):           # khóa logic của hóa đơn khác
            with self.subTest(sua=sua):
                self.raises(ma, lambda: self.m2.mapping_line(CFOA, **(body | sua | {"client_key": f"ml-r2-{i}"})))
                # gọi thẳng hàm definer (bỏ qua Python) cũng bị CSDL chặn
                self.raises(ma, lambda: self.sql(CFOA, "SELECT kho.m2_mapping_dong(%s::jsonb)",
                                                 (json.dumps(sql_body | sua | {"client_key": f"ml-r2-sql-{i}"}),)))
        self.raises("M2_YEU_CAU_SAI", lambda: self.sql(CFOA, "SELECT kho.m2_mapping_dong(%s::jsonb)",
                                                       (json.dumps({k: v for k, v in sql_body.items() if k not in ("evidence_ref", "evidence_revision")}
                                                                   | {"client_key": "ml-thieu"}),)))  # thiếu bằng chứng: không map tùy ý
        self.assertEqual(self.dem_phu(), phu)
        self.raises("M2_ROUTE_CHUA_CO_CAU_NOI", lambda: self.m2.route(CFOA, {"hoa_don_id": hd, "cau_noi_id": str(uuid.uuid4()), "dich": "KHO",
                                                                             "expected_route_id": None, "expected_graph": ct["expected_graph"],
                                                                             "ly_do": "trước mapping", "khoa": "rt-x"}))
        self.raises("M2_YEU_CAU_SAI", lambda: self.m2.route(CFOA, {"hoa_don_id": hd, "dich": "KHO", "khoa": "rt-thieu"}))  # thiếu cầu nối/token/lý do
        self.assertEqual(self.dem(), truoc)

    def test_t05_cfo_map_dong(self):
        hd, ct = self.state["hd"], self.m2.chi_tiet(CFOA, self.state["hd"])
        row = ct["dong_nguon_hien_hanh"][0]
        self.assertEqual((row["source_ordinal"], row["locator"], row["row_raw_sha256"]), (1, F[0]["source_locator"], None))
        body = dict(client_key="ml-g01", hoa_don_id=hd, expected_graph=ct["expected_graph"], source_row_id=row["source_row_id"],
                    logical_line_key=F[0]["logical_line_key"], reason="DEMO CFO map", **ev(0))
        r = self.m2.mapping_line(CFOA, **body)
        self.assertEqual((r["lap_lai"], r["logical_line_key"], r["evidence_ref"], r["evidence_ref_authority"]),
                         (False, "DEMO_LINE_G01_A", F[0]["mapping_ref"], "EVIDENCE_ONLY_NOT_APPROVAL"))
        self.kiem_buoc(2)
        phu = self.dem_phu()
        # R1: retry NGUYÊN body/token A (đồ thị đã đổi sang B do chính lần đầu) → cùng kết quả bất biến; chỉ lap_lai False→True
        lai = self.m2.mapping_line(CFOA, **body)
        self.assertTrue(lai["lap_lai"])
        self.assertEqual(bo_lap_lai(lai), bo_lap_lai(r))
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m2.mapping_line(CFOA, **(body | {"reason": "khác"})))  # khác H cùng khóa → 409 dù đồ thị đã đổi
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m2.mapping_line(CFOA, **(body | ev(1))))
        self.kiem_buoc(2)
        self.assertEqual(self.dem_phu(), phu)  # 0 audit/stage/file/mapping/route thêm khi retry/409
        m = self.admin.execute("""SELECT line_native_xml_sha256, line_source_locator, line_source_ordinal, line_identity_binding, nguon_quyet_dinh, duyet_boi,
                                         (SELECT f.mapping_ref FROM master.m2_ung_vien_dong f WHERE f.id = line_ung_vien_id)
                                  FROM master.anh_xa_nguon WHERE subject_kind = 'INVOICE_LINE'""").fetchone()
        f = F[0]
        self.assertEqual(m, (f["native_xml_sha256"], f["source_locator"], f["source_ordinal"], f["identity_tuple"], "CFO_V4", CFOA, f["mapping_ref"]))
        self.state["map"], self.state["map_body"] = r, body

    def test_t06_cfo_tuyen_kho_mot_thao_tac(self):
        hd, ct = self.state["hd"], self.m2.chi_tiet(CFOA, self.state["hd"])
        cau = ct["cau_noi"][0]["id"]
        body = {"hoa_don_id": hd, "cau_noi_id": cau, "dich": "KHO", "expected_route_id": None, "expected_graph": ct["expected_graph"], "ly_do": "DEMO KHO",
                "khoa": "rt-g01"}
        self.raises("KHONG_CO_QUYEN", lambda: self.m2.route(VIEWA, body))
        r = self.m2.route(CFOA, body)
        self.assertEqual((r["lap_lai"], r["dich"], r["phien_ban"], r["financial_or_inventory_approval"]), (False, "KHO", 1, False))
        self.kiem_buoc(3)
        phu = self.dem_phu()
        lai = self.m2.route(CFOA, body)  # R1: nguyên body/token A sau khi chính route đã đổi đồ thị
        self.assertTrue(lai["lap_lai"])
        self.assertEqual(bo_lap_lai(lai), bo_lap_lai(r))
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m2.route(CFOA, body | {"dich": "CHI_PHI"}))
        self.kiem_buoc(3)
        self.assertEqual(self.dem_phu(), phu)
        self.state["route"], self.state["ids3"] = r, self.stable_ids(hd)

    def test_t07_g03_zip_chi_them_quan_sat(self):
        hd = self.state["hd"]
        tok_truoc = self.m2.chi_tiet(CFOA, hd)["expected_graph"]
        r = self.nhan(INTAKE, artifact("inputs/G03-identical-members.zip"), "m2-g03")
        self.assertEqual((r["artifact_kind"], len(r["promote"]["items"])), ("ZIP", 2))
        self.kiem_buoc(4)
        self.assertEqual(self.stable_ids(hd), self.state["ids3"])  # invoice/PB/core/logic/bridge/map/route ổn định
        obs = self.admin.execute("""SELECT entry_ordinal, entry_name, container_sha256, native_xml_sha256 FROM kho.hoa_don_quan_sat
                                    WHERE container_sha256 IS NOT NULL ORDER BY entry_ordinal""").fetchall()
        self.assertEqual([(o[0], o[1]) for o in obs], [(1, "invoice-a.xml"), (2, "invoice-b.xml")])
        self.assertEqual({o[2] for o in obs} | {o[3] for o in obs}, {LINE_FACTS["rows"][2]["container_sha256"], LINE_FACTS["rows"][2]["native_xml_sha256"]})
        rt = self.state["route"]
        self.assertEqual(self.q("SELECT kho.m2_basis_tuyen_noi_bo(id) FROM kho.hoa_don_dong_phien_ban WHERE hoa_don_id = %s", (hd,)),
                         rt["source_graph_sha256"])  # delivery-only không đổi basis ngữ nghĩa tuyến
        ct = self.m2.chi_tiet(CFOA, hd)
        self.assertNotEqual(ct["expected_graph"], tok_truoc)  # token OP đổi theo quan sát
        self.assertIsNotNone(ct["con_tro"]["eligible_content_id"])  # A,A giữ eligible
        # ứng viên khớp quan sát mới nhất (ZIP entry 2) chỉ còn fact04 — bộ container/entry phải khớp đúng
        self.assertEqual([u["evidence_ref"] for u in ct["ung_vien_dong"]], [F[3]["mapping_ref"]])
        # retry mapping nguyên body/token A sau delivery mới vẫn trả kết quả cũ (biên nhận trước CAS)
        self.assertEqual(bo_lap_lai(self.m2.mapping_line(CFOA, **self.state["map_body"])), bo_lap_lai(self.state["map"]))

    def test_t08_tuyen_successor_va_bat_bien(self):
        hd, ct = self.state["hd"], self.m2.chi_tiet(CFOA, self.state["hd"])
        cau, cur = ct["cau_noi"][0]["id"], self.state["route"]["route_id"]
        core_truoc = self.core_m2(hd)
        self.assertIn('"so_luong"', core_truoc)  # core không rỗng
        self.raises("M2_ROUTE_STALE", lambda: self.m2.route(CFOA, {"hoa_don_id": hd, "cau_noi_id": cau, "dich": "CHI_PHI", "expected_route_id": None,
                                                                   "expected_graph": ct["expected_graph"], "ly_do": "stale", "khoa": "rt-stale"}))
        self.raises("M2_ROUTE_KHONG_DOI", lambda: self.m2.route(CFOA, {"hoa_don_id": hd, "cau_noi_id": cau, "dich": "KHO", "expected_route_id": cur,
                                                                       "expected_graph": ct["expected_graph"], "ly_do": "same", "khoa": "rt-same"}))
        r = self.m2.route(CFOA, {"hoa_don_id": hd, "cau_noi_id": cau, "dich": "CHI_PHI", "expected_route_id": cur, "expected_graph": ct["expected_graph"],
                                 "ly_do": "đổi tuyến", "khoa": "rt-v2"})
        self.assertEqual((r["phien_ban"], r["predecessor_route_id"]), (2, cur))
        self.assertEqual(self.admin.execute("SELECT trang_thai, hien_hanh FROM kho.mua_dich_dong WHERE id = %s", (cur,)).fetchone(), ("THAY_THE", False))
        self.assertEqual(self.q("SELECT count(*) FROM kho.mua_dich_dong WHERE hoa_don_id = %s AND hien_hanh", (hd,)), 1)
        self.raises("M2_BAT_BIEN", lambda: self.admin.execute("UPDATE kho.mua_dich_dong SET dich = 'KHO' WHERE id = %s", (r["route_id"],)))
        # R3: successor tuyến đúng, core/raw (ID/hash/số lượng/ngày/payload) giữ nguyên
        self.assertEqual(self.core_m2(hd), core_truoc)
        cts = "(SELECT chung_tu_id FROM kho.hoa_don_phien_ban WHERE hoa_don_id = %s)"
        for sql in (f"UPDATE kho.chung_tu_dong SET so_luong = 999 WHERE chung_tu_id IN {cts}",
                    f"UPDATE kho.chung_tu_dong SET mo_ta = 'sửa' WHERE chung_tu_id IN {cts}",
                    f"UPDATE kho.chung_tu_dong SET du_lieu = '{{}}'::jsonb WHERE chung_tu_id IN {cts}",
                    f"UPDATE kho.chung_tu SET ngay_nghiep_vu = '2026-10-02' WHERE id IN {cts}",
                    f"UPDATE kho.chung_tu SET hash = repeat('9', 64) WHERE id IN {cts}",
                    f"UPDATE kho.chung_tu SET du_lieu = '{{}}'::jsonb WHERE id IN {cts}",
                    f"UPDATE kho.chung_tu SET khoa_nguon = 'sua' WHERE id IN {cts}"):
            with self.subTest(sql=sql[:60]):  # chủ bảng đã cấu hình (owner) cũng bị chặn — không bypass trigger
                self.raises("M2_NGUON_BAT_BIEN", lambda: self.admin.execute(sql, (hd,)))
        self.raises(("M2_TIEN_CHUA_CAN_CU", "M2_NGUON_BAT_BIEN"), lambda: self.admin.execute(f"UPDATE kho.chung_tu_dong SET dich = 'KHO' WHERE chung_tu_id IN {cts}", (hd,)))
        for sql in (f"UPDATE kho.chung_tu_dong SET so_luong = 999 WHERE chung_tu_id IN {cts}", f"UPDATE kho.chung_tu SET hash = repeat('9', 64) WHERE id IN {cts}"):
            with self.subTest(app=sql[:40]):  # role ứng dụng thường: bị từ chối (quyền/RLS/guard) hoặc 0 hàng — không bao giờ sửa được
                try:
                    n = self.sql(CFOA, sql, (hd,))
                except (DataError, psycopg.Error) as exc:
                    self.assertTrue(any(c in str(exc) for c in ("permission denied", "M2_NGUON_BAT_BIEN", "CHUNG_TU_M2_CHI_CHU", "row-level security")), exc)
                else:
                    self.assertEqual(n, 0)
        self.assertEqual(self.core_m2(hd), core_truoc)

    # ------------------------------------------------------------------ G04 / lifecycle / intercompany
    def test_t09_g04_lifecycle_va_ban_ra(self):
        truoc = self.dem()
        a1 = self.nhan(INTAKE, artifact("inputs/G04-purchase-a-padded.xml"))
        hd = a1["promote"]["items"][0]["hoa_don_id"]
        a2 = self.nhan(INTAKE, artifact("inputs/G04-purchase-a-unpadded.xml"))
        self.assertEqual(a2["promote"]["items"][0]["hoa_don_id"], hd)  # đệm/không đệm 0 → cùng định danh
        ct = self.m2.chi_tiet(CFOA, hd)
        self.assertEqual((len(ct["phien_ban"]), ct["con_tro"]["eligible_content_id"]), (2, None))
        self.assertIn("CHANGED_CONTENT_HOLD", ct["quan_sat"][-1]["phan_loai"])
        self.assertEqual(ct["con_tro"]["accepted_source_observation_id"], ct["quan_sat"][0]["id"])  # A giữ làm vết
        b = self.nhan(INTAKE, artifact("inputs/G04-purchase-b-padded.xml"))
        self.assertNotEqual(b["promote"]["items"][0]["hoa_don_id"], hd)
        sale = self.nhan(INTAKE, artifact("inputs/G04-sale-a.xml"))
        self.assertEqual((sale["promote"]["items"], [c["state"] for c in sale["promote"]["candidates"]]), ([], ["SOURCE_CANDIDATE"]))
        sau = self.dem()
        self.assertEqual({k: sau[k] - truoc[k] for k in ("common_capture_receipts", "m2_identities", "m2_content_versions", "core_headers_M2",
                                                         "core_lines_M2", "typed_observations")},
                         {"common_capture_receipts": 4, "m2_identities": 2, "m2_content_versions": 3, "core_headers_M2": 3, "core_lines_M2": 3,
                          "typed_observations": 3})
        a3 = self.nhan(INTAKE, artifact("inputs/G04-purchase-a-padded.xml"))  # tổ tiên A xuất hiện lại sau B
        self.assertEqual(a3["promote"]["items"][0]["classification"][0], "ANCESTOR_REAPPEARANCE_HOLD")  # DTO là MẢNG mã (phần tử đầu = lifecycle)
        ct = self.m2.chi_tiet(CFOA, hd)
        self.assertIsNone(ct["con_tro"]["eligible_content_id"])
        cu = ct["quan_sat"][0]["id"]
        self.raises("M2_CHI_QUAN_SAT_MOI_NHAT", lambda: self.m2.xem_xet_nguon(CFOA, {"hoa_don_id": hd, "observation_id": cu, "expected_graph": ct["expected_graph"],
                                                                                   "ly_do": "chọn cũ", "khoa": "rv-cu"}))
        self.raises("KHONG_CO_QUYEN", lambda: self.m2.xem_xet_nguon(KTA, {"hoa_don_id": hd, "observation_id": ct["con_tro"]["latest_observation_id"],
                                                                         "expected_graph": ct["expected_graph"], "ly_do": "kt", "khoa": "rv-kt"}))
        rv = {"hoa_don_id": hd, "observation_id": ct["con_tro"]["latest_observation_id"], "expected_graph": ct["expected_graph"],
              "ly_do": "CFO chọn nguồn mới nhất", "khoa": "rv-g04"}
        r = self.m2.xem_xet_nguon(CFOA, rv)
        self.assertEqual((r["accepted_source_observation_id"], r["native_fiscal_status"]), (ct["con_tro"]["latest_observation_id"], "UNKNOWN"))
        self.assertIsNotNone(self.m2.chi_tiet(CFOA, hd)["con_tro"]["eligible_content_id"])
        phu = self.dem_phu()
        lai = self.m2.xem_xet_nguon(CFOA, rv)  # R1: source review cũng exact retry với token A dù con trỏ đã đổi
        self.assertTrue(lai["lap_lai"])
        self.assertEqual(bo_lap_lai(lai), bo_lap_lai(r))
        self.raises("IDEMPOTENCY_KHAC", lambda: self.m2.xem_xet_nguon(CFOA, rv | {"ly_do": "khác"}))
        self.assertEqual(self.dem_phu(), phu)
        self.raises(("KHONG_CO_QUYEN", "HOA_DON"), lambda: self.m2.chi_tiet(KTB, hd))  # PN khác không đọc

    def test_t10_intercompany_va_hai_phia(self):
        truoc = self.dem()
        ic = G01.replace(b"<NMua><MST>DEMO_M2_COMPANY_A</MST>", b"<NMua><MST>DEMO_M2_COMPANY_B</MST>").replace(
            b"<NBan><MST>DEMO_M2_SUPPLIER</MST>", b"<NBan><MST>DEMO_M2_COMPANY_A</MST>")
        self.assertNotEqual(ic, G01)
        r = self.nhan(INTAKE, ic)
        self.assertEqual([self.q("SELECT p.ma FROM master.phap_nhan p WHERE p.id = %s", (i["phap_nhan_id"],)) for i in r["promote"]["items"]], ["PN_DEMO_B"])
        self.assertEqual([(c["company_key"], c["state"]) for c in r["promote"]["candidates"]], [("DEMO_M2_COMPANY_A", "SOURCE_CANDIDATE")])
        hai = G01.replace(b"<NBan><MST>DEMO_M2_SUPPLIER</MST>", b"<NBan><MST>DEMO_M2_COMPANY_A</MST>")
        r2 = self.nhan(INTAKE, hai)
        self.assertEqual((r2["promote"]["items"], [c["reason"] for c in r2["promote"]["candidates"]]), ([], ["COMPANY_BOTH_SIDES"]))
        sau = self.dem()
        self.assertEqual((sau["m2_identities"] - truoc["m2_identities"], sau["core_headers_M2"] - truoc["core_headers_M2"]), (1, 1))

    def test_t11_thieu_ngay_va_don_vi_chua_co_fact(self):
        truoc = self.dem()
        thieu = G01.replace(b"<NLap>2026-10-01</NLap>", b"").replace(b"<SHDon>000001</SHDon>", b"<SHDon>000091</SHDon>")
        r = self.nhan(INTAKE, thieu)
        self.assertEqual((r["promote"]["items"], [c["reason"] for c in r["promote"]["candidates"]]), ([], ["CONTENT_OR_DATE_OR_CURRENCY_UNRESOLVED"]))
        sau = self.dem()
        self.assertEqual((sau["m2_identities"], sau["m2_content_versions"], sau["core_headers_M2"]),
                         (truoc["m2_identities"], truoc["m2_content_versions"], truoc["core_headers_M2"]))  # ứng viên thô, 0 typed/core
        u = self.nhan(INTAKE, artifact("inputs/G07-unit-no-fact.xml"))
        hd = u["promote"]["items"][0]["hoa_don_id"]
        lines = self.admin.execute("""SELECT d.so_luong FROM kho.chung_tu_dong d JOIN kho.hoa_don_phien_ban v ON v.chung_tu_id = d.chung_tu_id
                                      WHERE v.hoa_don_id = %s ORDER BY d.stt""", (hd,)).fetchall()
        self.assertEqual([x[0] for x in lines], [None, None])  # đơn vị chưa chứng minh → số chuẩn hóa NULL, định danh/core vẫn giữ
        self.assertEqual(self.q("""SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('kho','master')
                                   AND (table_name LIKE '%%pool%%' OR table_name LIKE '%%l11%%')"""), 0)

    def test_t12_stt_mo_ho_va_reorder_crosswalk_tuong_minh(self):
        amb = self.nhan(INTAKE, artifact("inputs/G05-stt-ambiguity.xml"))
        hd_amb = amb["promote"]["items"][0]["hoa_don_id"]
        self.assertEqual((self.q("SELECT count(*) FROM kho.hoa_don_dong_phien_ban WHERE hoa_don_id = %s", (hd_amb,)),
                          self.q("""SELECT count(*) FROM kho.chung_tu_dong d JOIN kho.hoa_don_phien_ban v ON v.chung_tu_id = d.chung_tu_id
                                    WHERE v.hoa_don_id = %s""", (hd_amb,))), (0, 4))  # giữ 4 dòng, 0 cầu nối tự động
        a = self.nhan(INTAKE, artifact("inputs/G05-order-a.xml"))
        hd = a["promote"]["items"][0]["hoa_don_id"]
        facts = {(r["native_xml_sha256"], r["source_ordinal"]): r for r in F[4:]}
        self.assertEqual(self.m2.chi_tiet(CFOA, hd_amb)["ung_vien_dong"], [])  # không có ứng viên literal → UI HOLD, không tự map

        def map_het(tag):
            ct = self.m2.chi_tiet(CFOA, hd)
            native = ct["quan_sat"][-1]["native_xml_sha256"]
            for row in ct["dong_nguon_hien_hanh"]:
                f = facts[(native, row["source_ordinal"])]
                self.assertEqual(ct["dinh_danh"], f["identity_tuple"])
                ct = self.m2.chi_tiet(CFOA, hd)
                self.assertIn((row["source_row_id"], f["mapping_ref"], f["logical_line_key"]),
                              [(u["source_row_id"], u["evidence_ref"], u["logical_line_key"]) for u in ct["ung_vien_dong"]])
                self.m2.mapping_line(CFOA, client_key=f"ml-{tag}-{row['source_ordinal']}", hoa_don_id=hd, expected_graph=ct["expected_graph"],
                                     source_row_id=row["source_row_id"], logical_line_key=f["logical_line_key"], evidence_ref=f["mapping_ref"],
                                     evidence_revision=f["revision"], reason="DEMO CFO map theo ứng viên literal đã admit")
        map_het("a")
        self.nhan(INTAKE, artifact("inputs/G05-order-b.xml"))
        ct = self.m2.chi_tiet(CFOA, hd)
        self.m2.xem_xet_nguon(CFOA, {"hoa_don_id": hd, "observation_id": ct["con_tro"]["latest_observation_id"], "expected_graph": ct["expected_graph"],
                                     "ly_do": "chọn B", "khoa": "rv-g05b"})
        map_het("b")
        self.assertEqual((self.q("SELECT count(*) FROM kho.hoa_don_dong_danh_tinh WHERE hoa_don_id = %s", (hd,)),
                          self.q("SELECT count(*) FROM kho.hoa_don_dong_phien_ban WHERE hoa_don_id = %s", (hd,))), (2, 4))

    # ------------------------------------------------------------------ forgery / quyền / crosswalk / sentinel
    def test_t13_forgery_va_quyen(self):
        hd = self.state["hd"]
        pn = self.q("SELECT id::text FROM master.phap_nhan WHERE ma = 'PN_DEMO_A'")
        for login, sql, params, ma in (
                (CFOA, "INSERT INTO kho.hoa_don_danh_tinh (phap_nhan_id, chieu, mst_ban, mau_so, ky_hieu, so_chuan, source_instance_id, created_by) "
                       "VALUES (%s,'MUA_VAO','X','1','S','1',%s,'x')", (pn, INST), "permission denied"),
                (CFOA, "INSERT INTO kho.bien_nhan_thao_tac (phap_nhan_id, module, operation, client_key, request_sha256, result_json, actor) "
                       "VALUES (%s,'M2','M2_ROUTE','prefill',%s,'{}',%s)", (pn, "0" * 64, CFOA), ("permission denied", "BIEN_NHAN_M2_CHI_CHU")),
                (INTAKE, "SELECT kho.m2_tieu_thu_quan_sat(gen_random_uuid(), %s)", ("0" * 64,), "STAGE_KHONG_HOP_LE"),
                (INTAKE, "SELECT giao_tiep.nguon_chot_ket_qua(gen_random_uuid(), %s, true, '{\"module\":\"M2\"}')", ("0" * 64,), "permission denied"),
                (CFOA, "UPDATE kho.mua_dich_dong SET dich = 'KHO'", (), "permission denied"),
                (KTA, "SELECT kho.m2_route(%s::jsonb)", (json.dumps({"hoa_don_id": hd, "client_key": "x", "dich": "KHO", "reason": "x"}),),
                 "KHONG_CO_QUYEN_M2_ROUTE")):
            with self.subTest(sql=sql[:50]):
                self.raises(ma, lambda: self.sql(login, sql, params))
        self.assertEqual(len(self.sql(VIEWA, "SELECT id FROM kho.hoa_don_danh_tinh WHERE id = %s", (hd,))), 1)
        self.assertEqual(len(self.sql(M1A, "SELECT id FROM kho.hoa_don_danh_tinh")), 0)
        self.assertEqual(len(self.sql(KTB, "SELECT id FROM kho.hoa_don_danh_tinh WHERE id = %s", (hd,))), 0)
        self.assertEqual(len(self.sql(M1A, "SELECT id FROM kho.chung_tu WHERE module_nghiep_vu = 'M2'")), 0)
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.nhan(NOSRC, G01, "m2-g01"))
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.nhan(CFOA, G01))  # SOURCE_MAP không phải INTAKE
        self.raises("NGUON_KHONG_CO_QUYEN", lambda: self.m2.nguon_raw(KTA, self.state["g01"]["lan_tiep_nhan_id"], "NATIVE"))
        _, raw = self.m2.nguon_raw(INTAKE, self.state["g01"]["lan_tiep_nhan_id"], "NATIVE")
        self.assertEqual(raw, G01)
        snap = self.q("SELECT snapshot_id::text FROM giao_tiep.lan_tiep_nhan_nguon WHERE id = %s", (self.state["g01"]["lan_tiep_nhan_id"],))
        self.raises("M2_DONG_NGUON_BASIS", lambda: self.admin.execute(
            """INSERT INTO kho.ban_ghi_nguon (snapshot_id, source_instance_id, vai_tro, section, locator, thu_tu, row_raw, row_raw_sha256, validation_state)
               VALUES (%s,%s,'NATIVE','XML_LINE','/forge',99,'{}',%s,'HOP_LE')""", (snap, INST, "0" * 64)))

    def test_t14_crosswalk_chi_la_bang_chung(self):
        truoc = self.dem()
        cw = _pin(BRIDGE / "line-facts.json", "2195792bef97a1c94773f7fbe3391192e0ed24e872dfd904ac90ed54ba3b41fd")
        r = self.nhan(INTAKE, G01, "m2-g01-cw", crosswalk=cw)
        sau = self.dem()
        self.assertEqual(self.q("""SELECT row_raw->>'record_count' FROM kho.ban_ghi_nguon WHERE section = 'CROSSWALK' AND source_instance_id = %s""", (INST,)), "8")
        self.assertEqual({k: sau[k] - truoc[k] for k in ("approved_line_mappings", "logical_lines", "version_line_bridges", "business_receipts")},
                         {"approved_line_mappings": 0, "logical_lines": 0, "version_line_bridges": 0, "business_receipts": 0})
        self.assertEqual(r["promote"]["items"][0]["classification"][0], "SAME_CONTENT_REPEAT")  # DTO mảng
        self.assertEqual(sau["approved_line_mappings"], truoc["approved_line_mappings"])
        self.assertEqual(self.q("SELECT count(*) FROM master.m2_ung_vien_dong"), 8)  # upload CROSSWALK không admit ứng viên mới

    def test_t15_sentinel_m5_m1_khong_doi(self):
        self.assertEqual(self.m5_snapshot(), self.m5_truoc)
        self.assertEqual(self.sentinel_m1(), self.old_m1_json)
        self.assertEqual(self.q("SELECT module_nghiep_vu FROM kho.chung_tu WHERE id = %s", (self.old_m1,)), "M1")
        self.assertEqual(self.q("""SELECT count(*) FROM kho.chung_tu_dong d JOIN kho.chung_tu c ON c.id = d.chung_tu_id WHERE c.module_nghiep_vu = 'M2'
                                   AND (d.no_minor IS NOT NULL OR d.co_minor IS NOT NULL)"""), 0)
        self.assertEqual(self.q("SELECT count(*) FROM kho.hoa_don_quan_sat WHERE native_fiscal_status <> 'UNKNOWN'"), 0)
        print("\nM2_K2_AGGREGATE", json.dumps({"db": self.db, "role": self.role, "dem": self.dem(), "seed": self.seed1}, ensure_ascii=False, sort_keys=True))

    # ------------------------------------------------------------------ S1 hình dạng NULL / R4 authority đơn vị / ứng viên bất biến
    def test_t16_hinh_dang_null_va_don_vi(self):
        from kho_tri_thuc.k2.nguon_chung import digest_payload
        # positive không rỗng: XML trần all NULL, ZIP all present
        self.assertGreaterEqual(self.q("SELECT count(*) FROM kho.hoa_don_quan_sat WHERE container_sha256 IS NULL AND entry_ordinal IS NULL AND entry_name IS NULL"), 1)
        self.assertGreaterEqual(self.q("""SELECT count(*) FROM kho.hoa_don_quan_sat WHERE container_sha256 IS NOT NULL AND entry_ordinal IS NOT NULL
                                          AND entry_name IS NOT NULL"""), 2)
        truoc = self.q("SELECT count(*) FROM kho.hoa_don_quan_sat")
        mau = """INSERT INTO kho.hoa_don_quan_sat (phap_nhan_id, hoa_don_id, phien_ban_id, lan_tiep_nhan_id, source_instance_id, snapshot_id, source_row_id,
                     native_xml_sha256, container_sha256, entry_ordinal, entry_name, locator, observation_key, thu_tu, classification, company_mapping_id)
                 SELECT phap_nhan_id, hoa_don_id, phien_ban_id, lan_tiep_nhan_id, source_instance_id, snapshot_id, source_row_id, native_xml_sha256,
                        %s::text, %s::integer, %s::text, locator, %s::text, 900 + %s::integer, classification, company_mapping_id
                 FROM kho.hoa_don_quan_sat WHERE hoa_don_id = %s ORDER BY thu_tu LIMIT 1"""
        for i, (c, o, n) in enumerate(((None, 1, "x.xml"), ("a" * 64, None, "x.xml"), ("a" * 64, 1, None), (None, None, "x.xml"), ("a" * 64, 1, ""))):
            with self.subTest(zip=(c, o, n)):  # chủ bảng ghi trực tiếp bộ ZIP thiếu một phần → CHECK hai trị từ chối
                with self.assertRaises(psycopg.errors.CheckViolation):
                    self.admin.execute(mau, (c, o, n, f"S1-{i}", i, self.state["hd"]))
        self.assertEqual(self.q("SELECT count(*) FROM kho.hoa_don_quan_sat"), truoc)
        # ứng viên literal: hình dạng ZIP thiếu một phần / digest khai sai / sửa sau admit đều bị từ chối
        base = dict(F[2]) | {"mapping_ref": "DEMO_M2_TEST_SHAPE_V1"}
        for sua, ma in (({"entry_name": None}, psycopg.errors.CheckViolation), ({"container_byte_length": None}, psycopg.errors.CheckViolation)):
            p = base | sua
            with self.subTest(fact=sua), self.assertRaises(ma):
                self.admin.execute("INSERT INTO master.m2_ung_vien_dong (payload, fact_sha256, source_document_ref, source_document_sha256) VALUES (%s::jsonb,%s,'t',%s)",
                                   (json.dumps(p), digest_payload(p), "0" * 64))
        self.raises("M2_UNG_VIEN_DIGEST", lambda: self.admin.execute(
            "INSERT INTO master.m2_ung_vien_dong (payload, fact_sha256, source_document_ref, source_document_sha256) VALUES (%s::jsonb,%s,'t',%s)",
            (json.dumps(base), digest_payload(F[2]), "0" * 64)))
        self.raises("M2_UNG_VIEN_BAT_BIEN", lambda: self.admin.execute("UPDATE master.m2_ung_vien_dong SET logical_line_key = 'X' WHERE mapping_ref = %s",
                                                                      (F[0]["mapping_ref"],)))
        self.assertEqual(self.q("SELECT count(*) FROM master.m2_ung_vien_dong"), 8)

    # ------------------------------------------------------------------ R4 repair03: đơn vị gắn ĐÚNG tuple tài liệu khai báo đã admit
    def owner_tu_choi(self, ma: str, sql: str, params=()):
        """Owner INSERT/UPDATE trong giao dịch chỉ-rollback. Bị từ chối đúng mã → đạt; được NHẬN (dù sau đó rollback) → VIOLATION (fail)."""
        nhan = False
        try:
            with self.admin.transaction():
                self.admin.execute(sql, params)
                nhan = True
                raise psycopg.Rollback()
        except (DataError, psycopg.Error) as exc:
            self.assertIn(ma, str(exc))
            return
        self.assertFalse(nhan, f"VIOLATION: CSDL nhận mutation lẽ ra bị từ chối ({ma}) — rollback không biến thành đạt")
        self.fail(f"không có lỗi cũng không có mutation ({ma})")

    INS_DV = """INSERT INTO master.dinh_nghia_don_vi_luong (reference_id, definition_sha256, payload, source_basis_ref, declared_scope, declaration_ref,
                    declaration_raw_sha256, declaration_locator, support_source_instance_id, support_profile_ref, support_profile_sha256)
                VALUES (%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s)"""

    def dv(self, payload, *, sha=None, basis=None, decl_ref=None, decl_sha=None, loc=None, inst=None):
        d = m2_demo.doc_khai_bao()
        from kho_tri_thuc.k2.nguon_chung import digest_payload
        return (payload["reference_id"], sha or digest_payload(payload), json.dumps(payload), basis or m2_demo.DECLARATIONS_BASIS, payload["scope"],
                decl_ref or m2_demo.DECLARATIONS_REF, decl_sha or m2_demo.DECLARATIONS_SHA256, loc or m2_demo.UNIT_DECLARATION_LOCATOR,
                inst or d["source_instance"], d["profile_ref"], m2_demo.PROFILE_PAYLOAD_SHA256)

    def dem_don_vi(self):
        return tuple(self.q(f"SELECT count(*) FROM {t}") for t in ("master.dinh_nghia_don_vi_luong", "master.tai_lieu_khai_bao_don_vi",
                                                                  "master.nguon_master_noi_dung"))

    def test_t17_don_vi_gan_tai_lieu_khai_bao(self):
        from kho_tri_thuc.k2.hoa_don import HoaDonK2
        from kho_tri_thuc.k2.nguon_chung import digest_payload
        d = m2_demo.doc_khai_bao()
        p0 = d["shared_master_unit_definition"]["payload"]
        # positive gốc không rỗng: hàng CAI seed khớp raw 4fe4 / canonical 923a98 / locator / căn cứ nguyên văn; consumer CSDL trả NULL
        goc = self.admin.execute("""SELECT reference_id, definition_sha256, source_basis_ref, declaration_ref, declaration_raw_sha256, declaration_locator,
                                           payload, declared_scope, support_source_instance_id, support_profile_ref, support_profile_sha256
                                    FROM master.dinh_nghia_don_vi_luong WHERE reference_id = %s""", (p0["reference_id"],)).fetchone()
        self.assertEqual(goc[:6], (p0["reference_id"], m2_demo.UNIT_PAYLOAD_SHA256, m2_demo.DECLARATIONS_BASIS, m2_demo.DECLARATIONS_REF,
                                   m2_demo.DECLARATIONS_SHA256, m2_demo.UNIT_DECLARATION_LOCATOR))
        self.assertEqual(m2_demo.DECLARATIONS_BASIS, "ROOT_SEED_DEMO:declarations.json:4fe4cffd7dca1ecca619fda5a637a41a95d5a22f9fce6536eaf9dc335e9e44f9")
        khop = "SELECT master.don_vi_khop_khai_bao(%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        self.assertIsNone(self.q(khop, (json.dumps(goc[6]), goc[1], goc[0], goc[7], goc[3], goc[4], goc[5], goc[2], goc[8], goc[9], goc[10])))
        truoc = self.dem_don_vi()
        xau = p0 | {"reference_id": "DEMO_M2_UNIT_TEST_PACK_V1", "meaning": "TWELVE_PIECES_PACK"}
        # negatives cụ thể (owner, rollback-only; mutation được nhận = VIOLATION)
        for ma, tham in (
                ("DON_VI_DIGEST_SAI", self.dv(xau, sha=m2_demo.UNIT_PAYLOAD_SHA256)),                          # claimed H sai
                ("DON_VI_KHONG_KHOP_TAI_LIEU", self.dv(xau)),                                                   # self-H đúng + ref/meaning mới + tài liệu/căn cứ CŨ
                ("DON_VI_TAI_LIEU_KHONG_CO", self.dv(xau, decl_ref="tests/fixtures/m2_bridge/khong-co.json")),   # tài liệu không tồn tại
                ("DON_VI_TAI_LIEU_SAI_HASH", self.dv(xau, decl_sha="a" * 64)),                                  # đúng ref, SHA trông hợp lệ nhưng sai
                ("DON_VI_VI_TRI_KHONG_CO", self.dv(xau, loc="/khong_co/payload")),                              # locator không tồn tại
                ("DON_VI_KHONG_KHOP_TAI_LIEU", self.dv(xau, loc="/shared_master_unit_definition")),            # sai subtree
                ("DON_VI_KHONG_KHOP_TAI_LIEU", self.dv(p0 | {"reference_id": "DEMO_M2_UNIT_TEST_NATIVE_V1", "native_unit_code": "THUNG"})),
                ("DON_VI_KHONG_KHOP_TAI_LIEU", self.dv(p0 | {"reference_id": "DEMO_M2_UNIT_TEST_SCOPE_V1", "scope": "SCOPE_KHAC"})),
                ("DON_VI_CAN_CU_SAI", self.dv(p0, basis="urn:demo:test:khong-gan")),                            # đúng payload, căn cứ không gắn tài liệu
                ("DON_VI_PHAM_VI_SAI", self.dv(p0, inst="DEMO_KHO_A"))):                                        # ngữ cảnh khác tài liệu khai
            with self.subTest(ma=ma, ref=tham[0]):
                self.owner_tu_choi(ma, self.INS_DV, tham)
        # tamper tuple/provenance đã admit
        for ma, sql in (("DON_VI_BAT_BIEN", "UPDATE master.dinh_nghia_don_vi_luong SET declaration_locator = '/x' WHERE reference_id = %s"),
                        ("DON_VI_BAT_BIEN", "UPDATE master.dinh_nghia_don_vi_luong SET source_basis_ref = 'urn:x' WHERE reference_id = %s")):
            with self.subTest(tamper=sql[40:80]):
                self.owner_tu_choi(ma, sql, (p0["reference_id"],))
        self.owner_tu_choi("DON_VI_TAI_LIEU_BAT_BIEN", "UPDATE master.tai_lieu_khai_bao_don_vi SET source_basis_ref = 'urn:x' WHERE reference_id = %s",
                           (m2_demo.DECLARATIONS_REF,))
        self.owner_tu_choi("BAN_GHI_BAT_BIEN", "UPDATE master.nguon_master_noi_dung SET byte_length = byte_length + 1 WHERE reference_id = %s",
                           (m2_demo.DECLARATIONS_REF,))
        # ứng dụng thường: không admit/prefill
        for sql, tham in ((self.INS_DV, self.dv(xau)),
                          ("INSERT INTO master.tai_lieu_khai_bao_don_vi (reference_id, raw_sha256, byte_length, noi_dung, source_basis_ref) VALUES (%s,%s,1,'\\x7b7d','b')",
                           ("x", "b" * 64))):
            with self.subTest(app=sql[12:50]):
                self.raises("permission denied", lambda: self.sql(CFOA, sql, tham))
        self.assertEqual(self.dem_don_vi(), truoc)
        # positive nghĩa MỚI: tài liệu tổng hợp DEMO RIÊNG (bytes khác) thật sự khai nghĩa đó; căn cứ URN mờ chỉ nhận khi gắn đúng
        moi = p0 | {"reference_id": "DEMO_M2_UNIT_TEST_PACK_V1", "meaning": "TEST_DECLARED_PACK_MEANING", "definition_kind": "TEST_PACK"}
        khai_trong = "urn:demo:test:unit-basis:pack-v1"
        tl = {"source_instance": d["source_instance"], "profile_ref": d["profile_ref"], "profile_payload_sha256": m2_demo.PROFILE_PAYLOAD_SHA256,
              "status": "TEST_SYNTHETIC_DEMO_DECLARATION_NOT_FIXTURE",
              "unit": {"reference_id": moi["reference_id"], "definition_payload_sha256": digest_payload(moi), "source_basis_ref": khai_trong, "payload": moi}}
        raw = json.dumps(tl, ensure_ascii=False, sort_keys=True).encode("utf-8")
        h = sha256(raw)
        ref_tl, can_cu_tl = "test:synthetic-unit-declaration-pack-v1", f"urn:demo:test:unitdecl:{h}"
        cat = "INSERT INTO master.nguon_master_noi_dung (reference_id, raw_sha256, byte_length) VALUES (%s,%s,%s)"
        doc = "INSERT INTO master.tai_lieu_khai_bao_don_vi (reference_id, raw_sha256, byte_length, noi_dung, source_basis_ref) VALUES (%s,%s,%s,%s,%s)"
        with self.subTest(don_vi="positive-nghia-moi"), self.admin.transaction():  # rollback-only: không để lại hàng, không DELETE
            self.admin.execute(cat, (ref_tl, h, len(raw)))
            self.raises("DON_VI_TAI_LIEU_CAN_CU_DA_DUNG", lambda: self._trong_savepoint(doc, (ref_tl, h, len(raw), raw, m2_demo.DECLARATIONS_BASIS)))
            self.raises("DON_VI_TAI_LIEU_CAN_CU_SAI", lambda: self._trong_savepoint(doc, (ref_tl, h, len(raw), raw, f"urn:x:{'c' * 64}")))
            self.admin.execute(doc, (ref_tl, h, len(raw), raw, can_cu_tl))
            # tài liệu khai căn cứ riêng cho đơn vị → căn cứ của tài liệu (dù đúng) KHÔNG được dùng thay; tài liệu cũ không nhận nghĩa mới
            self.raises("DON_VI_CAN_CU_SAI", lambda: self._trong_savepoint(self.INS_DV, self.dv(moi, basis=can_cu_tl, decl_ref=ref_tl, decl_sha=h, loc="/unit/payload")))
            self.raises("DON_VI_KHONG_KHOP_TAI_LIEU", lambda: self._trong_savepoint(self.INS_DV, self.dv(moi)))
            self.admin.execute(self.INS_DV, self.dv(moi, basis=khai_trong, decl_ref=ref_tl, decl_sha=h, loc="/unit/payload"))
            r = self.admin.execute("SELECT meaning FROM (SELECT payload->>'meaning' AS meaning FROM master.dinh_nghia_don_vi_luong WHERE reference_id = %s) x",
                                   (moi["reference_id"],)).fetchone()
            self.assertEqual(r[0], "TEST_DECLARED_PACK_MEANING")
            raise psycopg.Rollback()
        self.assertEqual(self.dem_don_vi(), truoc)
        # consumer CSDL độc lập (cùng hàm trước khi gắn cầu nối) và dịch vụ độc lập: tuple sửa → mã cụ thể; tuple gốc → khớp
        self.assertEqual(self.q(khop, (json.dumps(xau), digest_payload(xau), xau["reference_id"], xau["scope"], goc[3], goc[4], goc[5], goc[2],
                                       goc[8], goc[9], goc[10])), "DON_VI_KHONG_KHOP_TAI_LIEU")
        tai_lieu = self.admin.execute("SELECT raw_sha256, byte_length, noi_dung, source_basis_ref FROM master.tai_lieu_khai_bao_don_vi WHERE reference_id = %s",
                                      (m2_demo.DECLARATIONS_REF,)).fetchone()
        doc_d = {"raw_sha256": tai_lieu[0], "byte_length": tai_lieu[1], "noi_dung": tai_lieu[2], "source_basis_ref": tai_lieu[3]}
        unit_d = {"reference_id": goc[0], "definition_sha256": goc[1], "source_basis_ref": goc[2], "declaration_ref": goc[3], "declaration_raw_sha256": goc[4],
                  "declaration_locator": goc[5], "payload": goc[6], "declared_scope": goc[7], "support_source_instance_id": goc[8],
                  "support_profile_ref": goc[9], "support_profile_sha256": goc[10]}
        prof = (d["source_instance"], d["profile_ref"], m2_demo.PROFILE_PAYLOAD_SHA256)
        self.assertIsNone(HoaDonK2.kiem_don_vi_khai_bao(unit_d, doc_d, *prof))
        for ma, sua in (("DON_VI_KHONG_KHOP_TAI_LIEU", {"payload": xau, "definition_sha256": digest_payload(xau), "reference_id": xau["reference_id"]}),
                        ("DON_VI_DIGEST_SAI", {"definition_sha256": "b" * 64}),
                        ("DON_VI_CAN_CU_SAI", {"source_basis_ref": "urn:demo:test:khong-gan"}),
                        ("DON_VI_VI_TRI_KHONG_CO", {"declaration_locator": "/khong_co/payload"}),
                        ("DON_VI_TAI_LIEU_SAI_HASH", {"declaration_raw_sha256": "a" * 64})):
            with self.subTest(dich_vu=ma):
                self.assertEqual(HoaDonK2.kiem_don_vi_khai_bao(unit_d | sua, doc_d, *prof), ma)
        self.assertEqual(HoaDonK2.kiem_don_vi_khai_bao(unit_d, None, *prof), "DON_VI_TAI_LIEU_KHONG_CO")
        self.assertEqual(HoaDonK2.kiem_don_vi_khai_bao(unit_d, doc_d, "DEMO_KHO_A", prof[1], prof[2]), "DON_VI_NGOAI_PHAM_VI")
        # capture thật dùng authority đã gắn: G01 số lượng chuẩn hóa 10 và kết quả ghi BOUND
        self.assertEqual(self.state["g01"]["don_vi_khai_bao"], {"state": "BOUND", "reason": None})
        self.assertEqual(self.q("""SELECT d.so_luong::numeric FROM kho.chung_tu_dong d JOIN kho.hoa_don_phien_ban v ON v.chung_tu_id = d.chung_tu_id
                                   WHERE v.hoa_don_id = %s::uuid""", (self.state["hd"],)), 10)

    def _trong_savepoint(self, sql, params):
        with self.admin.transaction():  # savepoint lồng: lỗi chỉ hủy savepoint, giao dịch ngoài vẫn dùng được
            self.admin.execute(sql, params)

    # ------------------------------------------------------------------ thu hồi quyền hiện hành trước replay (chạy cuối: đổi trạng thái CFO A)
    def test_t99_thu_hoi_quyen_truoc_replay(self):
        body = self.state["map_body"]
        sql_body = {"hoa_don_id": body["hoa_don_id"], "expected_graph": body["expected_graph"], "source_row_id": body["source_row_id"],
                    "logical_line_key": body["logical_line_key"], "evidence_ref": body["evidence_ref"], "evidence_revision": body["evidence_revision"],
                    "reason": body["reason"], "client_key": body["client_key"]}
        phu, truoc = self.dem_phu(), self.dem()
        self.assertTrue(self.sql(CFOA, "SELECT kho.m2_mapping_dong(%s::jsonb) AS v", (json.dumps(sql_body),))[0]["v"]["lap_lai"])  # còn quyền: replay
        self.admin.execute("UPDATE master.nguoi_dung SET trang_thai = 'TAM_KHOA_TEST' WHERE dang_nhap = %s", (CFOA,))  # thu hồi (không xóa)
        self.raises("KHONG_CO_QUYEN_M2_MAP", lambda: self.sql(CFOA, "SELECT kho.m2_mapping_dong(%s::jsonb)", (json.dumps(sql_body),)))
        self.raises("DANH_TINH", lambda: self.m2.mapping_line(CFOA, **body))
        self.raises("DANH_TINH", lambda: self.m2.route(CFOA, {"hoa_don_id": body["hoa_don_id"], "cau_noi_id": self.state["map"]["cau_noi_id"], "dich": "KHO",
                                                               "expected_route_id": None, "expected_graph": "0" * 64, "ly_do": "x", "khoa": "rt-g01"}))
        self.assertEqual((self.dem_phu(), self.dem()), (phu, truoc))


if __name__ == "__main__":
    unittest.main()
