"""Seed DEMO L11 số lượng R16 (chạy bằng chủ CSDL SAU crm_demo → m5_demo → m2_demo; docs/GIAO-CODE-L11-QUANTITY-01.md §1–§2, §5, §9).

CHỈ CẤU HÌNH + RAW, MỘT LẦN, CHỈ THÊM:
- instance/profile/scope bằng chứng chuyên dụng (`DEMO_L11_EVIDENCE_INSTANCE_A`, profile canonical SHA `3cc2d403…`, scope L11_EVIDENCE_SET PN_DEMO_A);
- hai tài liệu khai báo đơn vị (bytes thô + catalog + căn cứ `urn:demo:l11:unitdecl:<sha>`) và hai định nghĩa đơn vị với tuple đầy đủ
  (DEMO_UNIT_CAI_A, DEMO_M2_UNIT_THUNG_R16_V1) — CSDL tự đối chiếu bytes/locator/payload SHA/căn cứ/ngữ cảnh hỗ trợ;
- một ứng viên literal dòng THUNG (thêm vào 8 ứng viên R15, bảng M2 dùng chung) — KHÔNG mapping/tuyến;
- cấu hình phiếu tách sáu (scope/master catalog/khai báo đo lường) cho nguồn DEMO_KHO_A — capture/chấp nhận nguồn là thao tác thật sau;
- hai actor mới (LINK BOTH V2, PROOF_CFO BOTH V4 + năng lực nguồn chỉ trên instance bằng chứng) — một lần, không regrant.
KHÔNG seed approval/bằng chứng đã xác nhận/pool/mã hóa/child/DA_XAC_NHAN; không đọc expected/cases/upstream manifest inventory/đường dẫn private.
Chỉ đọc đúng các đường dẫn public có kiểu đã liệt kê trong handoff, kiểm SHA/độ dài theo manifest fixture đã pin.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..ha_tang.primitives import DataError, sha256
from .nguon_chung import digest_payload

FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "l11_quantity"
MANIFEST_SHA256 = "227980804428af52fb153b9c15a9142e5b261f2b50bbd4b8e873ba421b3081dd"
SEED = "ROOT_SEED_DEMO"
MARKER = "demo_seed_l11_actor"
PN_MA = "PN_DEMO_A"

EVIDENCE_INSTANCE = "DEMO_L11_EVIDENCE_INSTANCE_A"
EVIDENCE_PROFILE_REF = "DEMO_L11_QUANTITY_EVIDENCE_JSON_V1"
EVIDENCE_SCOPE = "DEMO_L11_EVIDENCE_SCOPE_A"
EVIDENCE_PROFILE_SHA256 = "3cc2d403d3ae7986c75fd21767763c2fe23678d59290618225463c870e3d9251"
# literal của handoff §2 (root-approved technical DEMO declaration; runtime KHÔNG parse docs)
EVIDENCE_PROFILE_PAYLOAD = {
    "artifact_roles": [{"media_type": "application/json", "required": True, "role": "NATIVE"}],
    "capture_contract": "m0-capture/v1", "contract": "m0-source-profile/v1",
    "coverage_values": ["COMPLETE_INPUT", "PARTIAL_INPUT", "UNKNOWN"], "encoding": "JSON_UTF8", "module": "M5",
    "native_detail_shape": "l11-quantity-proof-json/v1",
    "proof_references": [
        {"byte_length": 3927, "evidence_revision": 2, "kind": "GOODS_EQUIVALENCE",
         "raw_sha256": "aef5de224e04fd64ef67a272689f72a041097ae93c5160393ef2297640d2bb4f", "reference_id": "DEMO_M2_M5_GOODS_EQ_A_V1"},
        {"byte_length": 2968, "evidence_revision": 2, "kind": "CROSS_NATIVE_RATIO",
         "raw_sha256": "bf4d47208740e16ad6cb59bdade9aae015bc8e5031fa797371eadf29e55cc319", "reference_id": "DEMO_M2_M5_CAI_EQ_A_V1"},
        {"byte_length": 1722, "evidence_revision": 2, "kind": "NATIVE_ENCODING",
         "raw_sha256": "a860439cf802e9b21ea1fabc24c1d9d6b79d8ca7a0402fba4bd62416a979b60f", "reference_id": "DEMO_R16_THUNG_NATIVE_ENCODING_V1"},
        {"byte_length": 3038, "evidence_revision": 2, "kind": "CROSS_NATIVE_RATIO",
         "raw_sha256": "c6e2fa840efd2644816192c8b753e68ebad241987cf69623f09022a665e4181b", "reference_id": "DEMO_NEW_THUNG12CAI_PROOF_V1"}],
    "purpose": "L11_PROOF", "verification": "SYNTHETIC_DEMO_ONLY_NOT_PRODUCTION_VERIFIED"}
EVIDENCE_COVERAGE_BINDING = "ONE_PROOF_INPUT_PER_CAPTURE_NOT_PROOF_INVENTORY_OR_PERIOD"

# bằng chứng whitelisted cho nút nhận (fixture_ref → đường dẫn public); không nhận đường dẫn/URL từ trình duyệt
PROOF_FILES = {"GOODS_EQ_A": "proofs/goods-equivalence-A-v2.json", "CAI_EQ_A": "proofs/cai-crossunit-1to1-v2.json",
               "THUNG_ENCODING": "proofs/thung-native-unit-and-encoding-v2.json", "THUNG_12_CAI": "proofs/thung-to-cai-12to1-v2.json"}
NGUON_FILES = {"THUNG_XML": "native/new-thung-one.xml", "SPLIT_NATIVE": "warehouse_split/native/warehouse-split-six.json",
               "SPLIT_MASTER": "warehouse_split/master/master-raw.json"}

UNIT_DOCS = (
    {"path": "unit-declarations/m5-cai-unit-declaration.json", "reference_id": "DEMO_UNIT_CAI_A",
     "definition_sha256": "206b26eac399c240adf71f26c8daec5de13f8be45b4badc64523c7ae76b3977f", "locator": "/unit/payload",
     "support_raw_sha256": "3a806526917dac322ee9ba4c6f7ea5ed88e02b780ea282c0300465e980e16801", "support_byte_length": 548,
     "support_reference": "tests/fixtures/m0_m5/masterraw/K01.json", "support_locator": "/DM_HangHoa/0/DVT_Goc"},
    {"path": "unit-declarations/thung-unit-declaration.json", "reference_id": "DEMO_M2_UNIT_THUNG_R16_V1",
     "definition_sha256": "774d51c9017314e156e19729b64870d55a34187628fb6d21e2080ee90b83bdb1", "locator": "/unit/payload",
     "support_raw_sha256": "65ce193e68053e59d5b18e4a7fa6879fa31499fbc2cd1ca5d138a95a30883a7a", "support_byte_length": 480,
     "support_reference": "tests/fixtures/l11_quantity/native/new-thung-one.xml", "support_locator": "/HDon/DLHDon/NDHDon/DSHHDVu/HHDVu[1]/DVTinh"},
)
CANDIDATE_FACTS = "candidate-line-facts-r16-v2.json"
ACTORS = (
    {"login": "MO_PHONG_L11_LINK_A", "role": "KE_TOAN", "modules": ["M2", "M5"], "duyet": ["V2"], "source_actions": []},
    {"login": "MO_PHONG_L11_PROOF_CFO_A", "role": "CFO", "modules": ["M2", "M5"], "duyet": ["V4"],
     "source_actions": ["INTAKE", "READ_SOURCE", "SOURCE_MAP"]},
)


def _manifest() -> dict:
    raw = (FIXTURE / "manifest.json").read_bytes()
    if sha256(raw) != MANIFEST_SHA256:
        raise DataError("FIXTURE_PIN", "Manifest fixture L11 không khớp SHA đã pin.")
    return {f["path"]: f for f in json.loads(raw.decode("utf-8"))["files"]}


def doc(rel: str) -> bytes:
    """Bytes đúng SHA/độ dài theo manifest đã pin (chỉ thành viên liệt kê; không duyệt upstream manifest)."""
    f = _manifest().get(rel)
    if f is None:
        raise DataError("L11_MAU", "Không có tệp fixture L11 này trong manifest đã pin.")
    raw = (FIXTURE / rel).read_bytes()
    if sha256(raw) != f["sha256"] or len(raw) != f["bytes"]:
        raise DataError("FIXTURE_PIN", f"Tệp fixture {rel} không khớp SHA/độ dài.")
    return raw


def mau_bang_chung(ma: str) -> tuple[str, bytes]:
    if ma not in PROOF_FILES:
        raise DataError("L11_MAU", "Không có mẫu bằng chứng DEMO này.")
    return Path(PROOF_FILES[ma]).name, doc(PROOF_FILES[ma])


def mau_nguon(ma: str) -> tuple[str, bytes]:
    if ma not in NGUON_FILES:
        raise DataError("L11_MAU", "Không có mẫu nguồn DEMO L11 này.")
    return Path(NGUON_FILES[ma]).name, doc(NGUON_FILES[ma])


def dang_nhap_l11() -> list[str]:
    return [a["login"] for a in ACTORS]


def _xung_dot(what):
    raise DataError("NGUON_SEED_XUNG_DOT", f"Dữ liệu bất biến đã có khác cấu hình L11 đã pin ({what}) — không ghi đè.")


def _catalog(admin_conn, reference_id: str, raw_sha: str, length: int, dem: dict) -> None:
    """Catalog nội dung nguồn dùng chung: thêm nếu chưa có (cùng SHA có thể đã có dưới reference khác — chấp nhận, không đổi)."""
    dem["catalog"] += admin_conn.execute("""INSERT INTO master.nguon_master_noi_dung (reference_id, raw_sha256, byte_length) VALUES (%s,%s,%s)
                                            ON CONFLICT DO NOTHING""", (reference_id, raw_sha, length)).rowcount
    row = admin_conn.execute("SELECT byte_length FROM master.nguon_master_noi_dung WHERE raw_sha256 = %s", (raw_sha,)).fetchone()
    if row is None or row[0] != length:
        _xung_dot("nguon_master_noi_dung " + reference_id)


def khoi_tao(admin_conn) -> dict:
    """admin_conn: psycopg autocommit, chủ CSDL, schema 16. Idempotent, chỉ thêm. Trả số đếm."""
    if digest_payload(EVIDENCE_PROFILE_PAYLOAD) != EVIDENCE_PROFILE_SHA256:
        raise DataError("NGUON_PROFILE_DIGEST", "Payload profile bằng chứng L11 không khớp SHA canonical đã pin.")
    decl = json.loads(doc("declarations.json").decode("utf-8"))
    dem = {"instance": 0, "profile": 0, "pham_vi": 0, "catalog": 0, "tai_lieu": 0, "don_vi": 0, "ung_vien_dong": 0, "pham_vi_phieu": 0,
           "do_luong": 0, "actor": 0, "phan_quyen": 0, "nang_luc": 0}
    with admin_conn.transaction():
        row = admin_conn.execute("SELECT id FROM master.phap_nhan WHERE ma = %s", (PN_MA,)).fetchone()
        if row is None:
            raise DataError("PHAP_NHAN", "Thiếu PN_DEMO_A — chạy seed CRM DEMO trước, không tạo PN mới.")
        pn = row[0]
        # ---- nguồn bằng chứng chuyên dụng
        dem["instance"] += admin_conn.execute("INSERT INTO master.nguon_instance (source_instance_id) VALUES (%s) ON CONFLICT DO NOTHING",
                                              (EVIDENCE_INSTANCE,)).rowcount
        dem["profile"] += admin_conn.execute("""INSERT INTO master.nguon_profile (source_instance_id, profile_ref, profile_sha256, payload)
                                                VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""",
                                             (EVIDENCE_INSTANCE, EVIDENCE_PROFILE_REF, EVIDENCE_PROFILE_SHA256,
                                              json.dumps(EVIDENCE_PROFILE_PAYLOAD, ensure_ascii=False))).rowcount
        row = admin_conn.execute("SELECT profile_sha256, payload FROM master.nguon_profile WHERE source_instance_id = %s", (EVIDENCE_INSTANCE,)).fetchone()
        if row is None or row[0] != EVIDENCE_PROFILE_SHA256 or digest_payload(row[1]) != EVIDENCE_PROFILE_SHA256:
            _xung_dot("nguon_profile L11")
        dem["pham_vi"] += admin_conn.execute("""INSERT INTO master.nguon_pham_vi (source_instance_id, profile_ref, profile_sha256, scope_ref, ma_kho, so_phieu,
                                                sections, coverage_binding, scope_kind, company_keys, phap_nhan_id)
                                                VALUES (%s,%s,%s,%s,NULL,NULL,%s,%s,'L11_EVIDENCE_SET',NULL,%s) ON CONFLICT DO NOTHING""",
                                             (EVIDENCE_INSTANCE, EVIDENCE_PROFILE_REF, EVIDENCE_PROFILE_SHA256, EVIDENCE_SCOPE, ["L11_PROOF_JSON"],
                                              EVIDENCE_COVERAGE_BINDING, pn)).rowcount
        row = admin_conn.execute("""SELECT scope_kind, phap_nhan_id, sections FROM master.nguon_pham_vi WHERE source_instance_id = %s AND scope_ref = %s""",
                                 (EVIDENCE_INSTANCE, EVIDENCE_SCOPE)).fetchone()
        if row is None or (row[0], str(row[1]), list(row[2])) != ("L11_EVIDENCE_SET", str(pn), ["L11_PROOF_JSON"]):
            _xung_dot("nguon_pham_vi L11")
        # ---- hai tài liệu khai báo đơn vị + định nghĩa đơn vị (tuple đầy đủ; CSDL đối chiếu bytes)
        theo_path = {u["path"]: u for u in decl["unit_declaration_documents"]}
        for u in UNIT_DOCS:
            d = theo_path.get(u["path"])
            raw = doc(u["path"])
            raw_sha = sha256(raw)
            if d is None or d["raw_sha256"] != raw_sha or d["byte_length"] != len(raw) or d["payload_locator"] != u["locator"] \
                    or d["unit_reference_id"] != u["reference_id"] or d["definition_payload_sha256"] != u["definition_sha256"]:
                _xung_dot("khai báo tài liệu đơn vị " + u["path"])
            tl = json.loads(raw.decode("utf-8"))
            payload = tl["unit"]["payload"]
            if digest_payload(payload) != u["definition_sha256"]:
                _xung_dot("payload đơn vị " + u["reference_id"])
            ref_tl = "tests/fixtures/l11_quantity/" + u["path"]
            can_cu_tl = f"urn:demo:l11:unitdecl:{raw_sha}"
            if d["document_registry_basis_ref"] != can_cu_tl:
                _xung_dot("căn cứ tài liệu " + u["path"])
            _catalog(admin_conn, ref_tl, raw_sha, len(raw), dem)
            dem["tai_lieu"] += admin_conn.execute("""INSERT INTO master.tai_lieu_khai_bao_don_vi (reference_id, raw_sha256, byte_length, noi_dung, source_basis_ref)
                                                     VALUES (%s,%s,%s,%s,%s) ON CONFLICT (reference_id) DO NOTHING""",
                                                  (ref_tl, raw_sha, len(raw), raw, can_cu_tl)).rowcount
            row = admin_conn.execute("SELECT raw_sha256, source_basis_ref FROM master.tai_lieu_khai_bao_don_vi WHERE reference_id = %s", (ref_tl,)).fetchone()
            if row is None or (row[0], row[1]) != (raw_sha, can_cu_tl):
                _xung_dot("tai_lieu_khai_bao_don_vi " + u["path"])
            _catalog(admin_conn, u["support_reference"], u["support_raw_sha256"], u["support_byte_length"], dem)
            tuple_dv = (u["reference_id"], u["definition_sha256"], tl["unit"]["source_basis_ref"], payload["scope"], ref_tl, raw_sha, u["locator"],
                        tl["source_instance"], tl["profile_ref"], tl["profile_payload_sha256"], u["support_raw_sha256"], u["support_locator"])
            dem["don_vi"] += admin_conn.execute("""INSERT INTO master.dinh_nghia_don_vi_luong (reference_id, definition_sha256, payload, source_basis_ref,
                                                   declared_scope, declaration_ref, declaration_raw_sha256, declaration_locator, support_source_instance_id,
                                                   support_profile_ref, support_profile_sha256, support_raw_sha256, support_locator)
                                                   VALUES (%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (reference_id) DO NOTHING""",
                                                (tuple_dv[0], tuple_dv[1], json.dumps(payload, ensure_ascii=False)) + tuple_dv[2:]).rowcount
            row = admin_conn.execute("""SELECT reference_id, definition_sha256, source_basis_ref, declared_scope, declaration_ref, declaration_raw_sha256,
                                               declaration_locator, support_source_instance_id, support_profile_ref, support_profile_sha256,
                                               support_raw_sha256, support_locator FROM master.dinh_nghia_don_vi_luong WHERE reference_id = %s""",
                                     (u["reference_id"],)).fetchone()
            if row is None or tuple(row) != tuple_dv:
                _xung_dot("dinh_nghia_don_vi_luong " + u["reference_id"])
        # ---- ứng viên literal dòng THUNG (thêm vào bảng ứng viên M2; không mapping/tuyến)
        lf_raw = doc(CANDIDATE_FACTS)
        lf = json.loads(lf_raw.decode("utf-8"))
        if lf.get("record_count") != 1 or len(lf.get("rows") or []) != 1:
            raise DataError("NGUON_SEED", "Ứng viên dòng R16 phải đúng 1 hàng.")
        for f in lf["rows"]:
            h = digest_payload(f)
            dem["ung_vien_dong"] += admin_conn.execute("""INSERT INTO master.m2_ung_vien_dong (payload, fact_sha256, source_document_ref, source_document_sha256)
                                                          VALUES (%s::jsonb,%s,%s,%s) ON CONFLICT (mapping_ref, revision) DO NOTHING""",
                                                       (json.dumps(f, ensure_ascii=False), h, "tests/fixtures/l11_quantity/" + CANDIDATE_FACTS,
                                                        sha256(lf_raw))).rowcount
            row = admin_conn.execute("SELECT fact_sha256 FROM master.m2_ung_vien_dong WHERE mapping_ref = %s AND revision = %s",
                                     (f["mapping_ref"], f["revision"])).fetchone()
            if row is None or row[0] != h:
                _xung_dot("m2_ung_vien_dong " + f["mapping_ref"])
        # ---- cấu hình phiếu tách sáu cho nguồn DEMO_KHO_A (cùng profile M5 hiện có; capture/chấp nhận là thao tác thật)
        sc = json.loads(doc("warehouse_split/configuration/source-scope.json").decode("utf-8"))
        prof = admin_conn.execute("SELECT profile_ref, profile_sha256 FROM master.nguon_profile WHERE source_instance_id = %s", (sc["source_instance"],)).fetchone()
        if prof is None or (prof[0], prof[1]) != (sc["profile_ref"], sc["profile_sha256"]):
            raise DataError("NGUON_SEED", "Profile M5 của DEMO_KHO_A chưa có đúng ref/SHA — chạy seed M5 trước.")
        dem["pham_vi_phieu"] += admin_conn.execute("""INSERT INTO master.nguon_pham_vi (source_instance_id, profile_ref, profile_sha256, scope_ref, ma_kho,
                                                      so_phieu, sections, coverage_binding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                                   (sc["source_instance"], sc["profile_ref"], sc["profile_sha256"], sc["scope_ref"], sc["MaKho"], sc["SoPhieu"],
                                                    sorted(set(sc["sections"])), sc["coverage_binding"])).rowcount
        row = admin_conn.execute("""SELECT ma_kho, so_phieu, sections, scope_kind FROM master.nguon_pham_vi WHERE source_instance_id = %s AND scope_ref = %s""",
                                 (sc["source_instance"], sc["scope_ref"])).fetchone()
        if row is None or (row[0], row[1], sorted(row[2]), row[3]) != (sc["MaKho"], sc["SoPhieu"], sorted(set(sc["sections"])), "KHO10_PHIEU"):
            _xung_dot("nguon_pham_vi phiếu tách sáu")
        adm = json.loads(doc("warehouse_split/configuration/admission-proposal.json").decode("utf-8"))["new_master_catalog"]
        master_raw = doc("warehouse_split/master/master-raw.json")
        if sha256(master_raw) != adm["raw_sha256"] or len(master_raw) != adm["byte_length"]:
            _xung_dot("master raw phiếu tách sáu")
        _catalog(admin_conn, adm["reference_id"], adm["raw_sha256"], adm["byte_length"], dem)
        md = json.loads(doc("warehouse_split/declarations/measurement-declaration.json").decode("utf-8"))
        if digest_payload(md["payload"]) != md["payload_sha256"]:
            _xung_dot("khai báo đo lường phiếu tách sáu")
        dieu_kien = {"resolution_preconditions": md["resolution_preconditions"], "non_matching_resolution": md["non_matching_resolution"]}
        dem["do_luong"] += admin_conn.execute("""INSERT INTO master.nguon_su_kien_do_luong (source_instance_id, profile_ref, profile_sha256, declaration_ref,
                                                 payload_sha256, payload, dieu_kien) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) ON CONFLICT DO NOTHING""",
                                              (md["source_instance"], md["profile_ref"], md["profile_sha256"], md["declaration_ref"], md["payload_sha256"],
                                               json.dumps(md["payload"], ensure_ascii=False), json.dumps(dieu_kien, ensure_ascii=False))).rowcount
        row = admin_conn.execute("""SELECT payload, dieu_kien FROM master.nguon_su_kien_do_luong WHERE source_instance_id = %s AND profile_ref = %s
                                    AND profile_sha256 = %s AND declaration_ref = %s AND payload_sha256 = %s""",
                                 (md["source_instance"], md["profile_ref"], md["profile_sha256"], md["declaration_ref"], md["payload_sha256"])).fetchone()
        if row is None or digest_payload(row[0]) != md["payload_sha256"] or row[1] != dieu_kien:
            _xung_dot("nguon_su_kien_do_luong phiếu tách sáu")
        # ---- hai actor mới: MỘT LẦN (marker hoặc login đã có) → mở lại giữ quyền hiện hành, không cấp lại; không chạm 8 actor M2/8 actor M5
        da_co = admin_conn.execute("SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER,)).fetchone() is not None or \
            admin_conn.execute("SELECT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE dang_nhap = ANY(%s))", (dang_nhap_l11(),)).fetchone()[0]
        for a in ([] if da_co else ACTORS):
            dem["actor"] += admin_conn.execute("""INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true)
                                                  ON CONFLICT (dang_nhap) DO NOTHING""", (a["login"], a["login"], a["role"])).rowcount
            row = admin_conn.execute("SELECT id, vai_tro, mo_phong, trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (a["login"],)).fetchone()
            if (row[1], row[2], row[3]) != (a["role"], True, "HOAT_DONG"):
                _xung_dot("nguoi_dung " + a["login"])
            dem["phan_quyen"] += admin_conn.execute("""INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
                                                       VALUES (%s,%s,%s,%s) ON CONFLICT (nguoi_dung_id, phap_nhan_id) DO NOTHING""",
                                                    (row[0], pn, sorted(a["duyet"]), sorted(a["modules"]))).rowcount
            q = admin_conn.execute("SELECT duyet_loai_viec, module FROM master.phan_quyen WHERE nguoi_dung_id = %s AND phap_nhan_id = %s", (row[0], pn)).fetchone()
            if (sorted(q[0]), sorted(q[1])) != (sorted(a["duyet"]), sorted(a["modules"])):
                _xung_dot("phan_quyen " + a["login"])
            for action in a["source_actions"]:
                dem["nang_luc"] += admin_conn.execute("""INSERT INTO master.nang_luc_nguon (nguoi_dung_id, source_instance_id, profile_ref, profile_sha256,
                                                         hanh_dong, target_phap_nhan_id) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                                      (row[0], EVIDENCE_INSTANCE, EVIDENCE_PROFILE_REF, EVIDENCE_PROFILE_SHA256, action,
                                                       pn if action == "SOURCE_MAP" else None)).rowcount
        admin_conn.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, 'r16') ON CONFLICT (key) DO NOTHING", (MARKER,))
    dem["mo_lai_giu_quyen_hien_hanh"] = da_co
    return dem
