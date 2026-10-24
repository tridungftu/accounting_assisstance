"""Seed DEMO M2 bridge R15 (chạy bằng tài khoản chủ CSDL sau `crm_demo.khoi_tao` + `m5_demo.khoi_tao`): một source instance/profile hóa đơn XML,
scope INVOICE_SET (company A/B), mapping COMPANY → PN có sẵn, MỘT định nghĩa đơn vị CAI phía hóa đơn (bảng MASTER dùng chung) và 8 actor M2.

CHỈ THÊM, MỘT LẦN: không đổi/ghi đè 8 actor M5, quyền, thu hồi; không tạo PN mới (PN_DEMO_A/B có sẵn); không cấp M5/L11/FILE_SOAT/M9;
không cài proof R16 (goods/unit equivalence, THUNG). Mở lại: actor/quyền/năng lực đã có (marker hoặc bất kỳ login M2) → bỏ qua toàn khối, không cấp
lại năng lực đã thu hồi. Hàng bất biến đã có mà khác → NGUON_SEED_XUNG_DOT, không sửa. Mọi digest kiểm lại bằng canonical_json trước khi ghi:
declarations pin SHA, profile payload SHA `7e1779…`, unit payload SHA `923a98…`. Không đọc oracle/expected/workflow để tạo mapping dòng:
mapping INVOICE_LINE chỉ do CFO thật tạo trong workflow mapping_line.

Repair02 (R2): đúng 8 hàng literal của `line-facts.json` (SHA pin `2195792b…`, qua manifest bridge) được ADMIT nguyên văn làm ứng viên bằng chứng
thô bất biến (`master.m2_ung_vien_dong`, CSDL tính lại digest canonical và dẫn xuất cột từ payload). Giữ đủ 8 hàng kể cả delivery trùng; không
tạo mapping/dòng logic/UUID giả, không auto-approve; thêm-only, hàng đã có khác digest → NGUON_SEED_XUNG_DOT. Dữ liệu tổng hợp, không nguồn thật.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..ha_tang.primitives import DataError, sha256
from .nguon_chung import digest_payload

FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
M2_BRIDGE = FIXTURE / "m2_bridge"
M2_XML = FIXTURE / "m2_invoice_xml"
DECLARATIONS_SHA256 = "4fe4cffd7dca1ecca619fda5a637a41a95d5a22f9fce6536eaf9dc335e9e44f9"
BRIDGE_MANIFEST_SHA256 = "d65efac0b3c9b4018a56d30e55d2782b1ba24012027188d1935b846f6087e9e7"
XML_MANIFEST_SHA256 = "43ad28257ca646b9d43f45ed34a8c441131328cca1b576cf247b378224e2b177"
PROFILE_PAYLOAD_SHA256 = "7e17794151a7711317da3d9ab00d96427d2b1e1c688b132feb78ce540bb2188d"
UNIT_PAYLOAD_SHA256 = "923a98f25aaf80b5762d97c1f183e8432aa347c74ce4525c8ef82f1633c73f89"
LINE_FACTS_SHA256 = "2195792bef97a1c94773f7fbe3391192e0ed24e872dfd904ac90ed54ba3b41fd"
LINE_FACTS_AUTHORITY = "RAW_DEMO_EVIDENCE_REQUIRES_ACTUAL_CFO_MAPPING"
# R4 repair03: tuple khai báo đơn vị — tài liệu thô declarations.json (ref + raw SHA), locator payload, căn cứ nguyên văn gắn đúng tài liệu
DECLARATIONS_REF = "tests/fixtures/m2_bridge/declarations.json"
DECLARATIONS_BASIS = f"ROOT_SEED_DEMO:declarations.json:{DECLARATIONS_SHA256}"
UNIT_DECLARATION_LOCATOR = "/shared_master_unit_definition/payload"
SEED = "ROOT_SEED_DEMO"
MARKER = "demo_seed_m2_actor"
COMPANY_VALID_FROM = "2026-01-01T00:00:00+00:00"  # mốc DEMO cố định (không lấy giờ hiện tại để seed tái lập được)
COVERAGE_BINDING = "INPUT_BUNDLE_ONLY_PERIOD_COMPLETENESS_UNKNOWN"


def _doc_pin(path: Path, sha: str) -> bytes:
    raw = path.read_bytes()
    if sha256(raw) != sha:
        raise DataError("FIXTURE_PIN", f"Tệp fixture {path.name} không khớp SHA đã pin.")
    return raw


def doc_khai_bao() -> dict:
    """Declarations DEMO đã root pin; kiểm digest payload profile/đơn vị (canonical JSON), 8 actor, 2 công ty."""
    man = json.loads(_doc_pin(M2_BRIDGE / "manifest.json", BRIDGE_MANIFEST_SHA256).decode("utf-8"))
    pin = {f["path"]: f["sha256"] for f in man["files"]}
    if pin.get("declarations.json") != DECLARATIONS_SHA256:
        raise DataError("FIXTURE_PIN", "Manifest M2 bridge không pin đúng declarations.")
    d = json.loads(_doc_pin(M2_BRIDGE / "declarations.json", DECLARATIONS_SHA256).decode("utf-8"))
    if digest_payload(d["profile_payload"]) != PROFILE_PAYLOAD_SHA256 or d["profile_payload_sha256"] != PROFILE_PAYLOAD_SHA256:
        raise DataError("NGUON_PROFILE_DIGEST", "Payload profile M2 không khớp digest đã pin.")
    u = d["shared_master_unit_definition"]
    if digest_payload(u["payload"]) != UNIT_PAYLOAD_SHA256 or u["definition_payload_sha256"] != UNIT_PAYLOAD_SHA256:
        raise DataError("DON_VI_DIGEST", "Payload định nghĩa đơn vị M2 không khớp digest đã pin.")
    if d["profile_document_sha256"] == PROFILE_PAYLOAD_SHA256:
        raise DataError("NGUON_PROFILE_DIGEST", "Document SHA phải khác payload SHA.")
    if len(d["actors"]) != 8 or len(d["companies"]) != 2:
        raise DataError("NGUON_SEED", "Declarations M2 phải có đúng 8 actor và 2 công ty.")
    return d


def doc_ung_vien_dong(d: dict) -> list[dict]:
    """8 hàng literal đã pin (qua manifest bridge + declarations). Chỉ kiểm hình thức/khai báo; không đọc workflow/oracle, không suy mapping."""
    man = json.loads(_doc_pin(M2_BRIDGE / "manifest.json", BRIDGE_MANIFEST_SHA256).decode("utf-8"))
    pin = {f["path"]: f["sha256"] for f in man["files"]}
    art = d["line_crosswalk_source"]["literal_line_facts_artifact"]
    if pin.get("line-facts.json") != LINE_FACTS_SHA256 or art["sha256"] != LINE_FACTS_SHA256:
        raise DataError("FIXTURE_PIN", "Manifest/declarations M2 không pin đúng line-facts.")
    lf = json.loads(_doc_pin(M2_BRIDGE / "line-facts.json", LINE_FACTS_SHA256).decode("utf-8"))
    rows = lf.get("rows")
    if (lf.get("authority") != LINE_FACTS_AUTHORITY or lf.get("source_instance") != d["source_instance"] or not isinstance(rows, list)
            or len(rows) != lf.get("record_count") or len(rows) != art["record_count"]
            or len({(r.get("mapping_ref"), r.get("revision")) for r in rows}) != len(rows)):
        raise DataError("NGUON_SEED", "line-facts không đúng khai báo (authority/instance/số hàng/ref duy nhất).")
    for r in rows:
        if r.get("authority") != LINE_FACTS_AUTHORITY or r.get("profile_payload_sha256") != PROFILE_PAYLOAD_SHA256:
            raise DataError("NGUON_SEED", f"Hàng literal {r.get('mapping_ref')} sai authority/profile.")
    return rows


def mau_danh_sach() -> list[str]:
    """Đường dẫn artifact DEMO (XML/ZIP) theo manifest pure đã pin — chỉ phục vụ nút 'Nhận mẫu' của UI DEMO."""
    man = json.loads(_doc_pin(M2_XML / "manifest.json", XML_MANIFEST_SHA256).decode("utf-8"))
    return [f["path"] for f in man["files"] if f["path"].startswith("inputs/") and f["path"].endswith((".xml", ".zip"))]


def mau(rel: str) -> tuple[str, bytes]:
    """Bytes DEMO đúng SHA manifest (không oracle/expected). Trả (tên tệp, bytes)."""
    man = json.loads(_doc_pin(M2_XML / "manifest.json", XML_MANIFEST_SHA256).decode("utf-8"))
    f = next((x for x in man["files"] if x["path"] == rel and rel.startswith("inputs/") and rel.endswith((".xml", ".zip"))), None)
    if f is None:
        raise DataError("M2_MAU", "Không có mẫu DEMO này.")
    return Path(rel).name, _doc_pin(M2_XML / rel, f["sha256"])


def _xung_dot(what):
    raise DataError("NGUON_SEED_XUNG_DOT", f"Dữ liệu bất biến đã có khác declarations đã pin ({what}) — không ghi đè.")


def khoi_tao(admin_conn) -> dict:
    """admin_conn: psycopg autocommit, chủ CSDL, schema đã migrate tới M0015. Idempotent, chỉ thêm. Trả số đếm."""
    d = doc_khai_bao()
    facts = doc_ung_vien_dong(d)
    dem = {"instance": 0, "profile": 0, "pham_vi": 0, "tai_lieu": 0, "don_vi": 0, "anh_xa_cong_ty": 0, "ung_vien_dong": 0, "actor": 0, "phan_quyen": 0, "nang_luc": 0}
    inst, ref, prof = d["source_instance"], d["profile_ref"], d["profile_payload"]
    with admin_conn.transaction():
        pn = {}
        for c in d["companies"]:
            row = admin_conn.execute("SELECT id FROM master.phap_nhan WHERE ma = %s", (c["existing_master_phap_nhan_ma"],)).fetchone()
            if row is None:
                raise DataError("PHAP_NHAN", f"Thiếu pháp nhân {c['existing_master_phap_nhan_ma']} — chạy seed CRM DEMO trước, không tạo PN mới.")
            pn[c["existing_master_phap_nhan_ma"]] = row[0]
        dem["instance"] += admin_conn.execute("INSERT INTO master.nguon_instance (source_instance_id) VALUES (%s) ON CONFLICT DO NOTHING", (inst,)).rowcount
        dem["profile"] += admin_conn.execute("""INSERT INTO master.nguon_profile (source_instance_id, profile_ref, profile_sha256, payload)
                                                VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""",
                                             (inst, ref, PROFILE_PAYLOAD_SHA256, json.dumps(prof, ensure_ascii=False))).rowcount
        row = admin_conn.execute("SELECT profile_sha256, payload FROM master.nguon_profile WHERE source_instance_id = %s AND profile_ref = %s",
                                 (inst, ref)).fetchone()
        if row[0] != PROFILE_PAYLOAD_SHA256 or digest_payload(row[1]) != PROFILE_PAYLOAD_SHA256:
            _xung_dot("nguon_profile")
        s = d["scope"]
        dem["pham_vi"] += admin_conn.execute("""INSERT INTO master.nguon_pham_vi (source_instance_id, profile_ref, profile_sha256, scope_ref, ma_kho, so_phieu,
                                                sections, coverage_binding, scope_kind, company_keys) VALUES (%s,%s,%s,%s,NULL,NULL,%s,%s,'INVOICE_SET',%s)
                                                ON CONFLICT DO NOTHING""",
                                             (inst, ref, PROFILE_PAYLOAD_SHA256, s["ref"], sorted(set(s["sections"])), COVERAGE_BINDING,
                                              sorted(set(s["company_keys"])))).rowcount
        row = admin_conn.execute("""SELECT profile_sha256, sections, scope_kind, company_keys, ma_kho, so_phieu FROM master.nguon_pham_vi
                                    WHERE source_instance_id = %s AND scope_ref = %s""", (inst, s["ref"])).fetchone()
        if (row[0], sorted(row[1]), row[2], sorted(row[3] or []), row[4], row[5]) != (PROFILE_PAYLOAD_SHA256, sorted(set(s["sections"])), "INVOICE_SET",
                                                                                      sorted(set(s["company_keys"])), None, None):
            _xung_dot("nguon_pham_vi")
        # R4 repair03: admit BYTES THÔ của declarations.json (catalog nguồn dùng chung + tài liệu khai báo, căn cứ nguyên văn), rồi định nghĩa đơn
        # vị với tuple chính xác (tài liệu ref + raw SHA + locator payload + căn cứ + profile hỗ trợ). CSDL tự đối chiếu với bytes; thêm-only.
        raw_kb = _doc_pin(M2_BRIDGE / "declarations.json", DECLARATIONS_SHA256)
        dem["tai_lieu"] += admin_conn.execute("""INSERT INTO master.nguon_master_noi_dung (reference_id, raw_sha256, byte_length) VALUES (%s,%s,%s)
                                                 ON CONFLICT DO NOTHING""", (DECLARATIONS_REF, DECLARATIONS_SHA256, len(raw_kb))).rowcount
        row = admin_conn.execute("SELECT raw_sha256, byte_length FROM master.nguon_master_noi_dung WHERE reference_id = %s", (DECLARATIONS_REF,)).fetchone()
        if row is None or (row[0], row[1]) != (DECLARATIONS_SHA256, len(raw_kb)):
            _xung_dot("nguon_master_noi_dung declarations")
        admin_conn.execute("""INSERT INTO master.tai_lieu_khai_bao_don_vi (reference_id, raw_sha256, byte_length, noi_dung, source_basis_ref)
                              VALUES (%s,%s,%s,%s,%s) ON CONFLICT (reference_id) DO NOTHING""",
                           (DECLARATIONS_REF, DECLARATIONS_SHA256, len(raw_kb), raw_kb, DECLARATIONS_BASIS))
        row = admin_conn.execute("SELECT raw_sha256, byte_length, source_basis_ref FROM master.tai_lieu_khai_bao_don_vi WHERE reference_id = %s",
                                 (DECLARATIONS_REF,)).fetchone()
        if row is None or (row[0], row[1], row[2]) != (DECLARATIONS_SHA256, len(raw_kb), DECLARATIONS_BASIS):
            _xung_dot("tai_lieu_khai_bao_don_vi declarations")
        u = d["shared_master_unit_definition"]
        tuple_dv = (u["reference_id"], UNIT_PAYLOAD_SHA256, DECLARATIONS_BASIS, u["payload"]["scope"], DECLARATIONS_REF, DECLARATIONS_SHA256,
                    UNIT_DECLARATION_LOCATOR, inst, ref, PROFILE_PAYLOAD_SHA256, None, None)
        dem["don_vi"] += admin_conn.execute("""INSERT INTO master.dinh_nghia_don_vi_luong (reference_id, definition_sha256, payload, source_basis_ref,
                                               declared_scope, declaration_ref, declaration_raw_sha256, declaration_locator, support_source_instance_id,
                                               support_profile_ref, support_profile_sha256, support_raw_sha256, support_locator)
                                               VALUES (%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (reference_id) DO NOTHING""",
                                            (tuple_dv[0], tuple_dv[1], json.dumps(u["payload"], ensure_ascii=False)) + tuple_dv[2:]).rowcount
        row = admin_conn.execute("""SELECT reference_id, definition_sha256, source_basis_ref, declared_scope, declaration_ref, declaration_raw_sha256,
                                           declaration_locator, support_source_instance_id, support_profile_ref, support_profile_sha256, support_raw_sha256,
                                           support_locator, payload FROM master.dinh_nghia_don_vi_luong WHERE reference_id = %s""",
                                 (u["reference_id"],)).fetchone()
        if row is None or tuple(row[:12]) != tuple_dv or digest_payload(row[12]) != UNIT_PAYLOAD_SHA256:
            _xung_dot("dinh_nghia_don_vi_luong")
        for c in d["companies"]:
            row = admin_conn.execute("""SELECT subject_kind, subject_key, phap_nhan_id, nguon_quyet_dinh FROM master.anh_xa_nguon
                                        WHERE reference_id = %s AND revision = %s""", (c["mapping_ref"], c["revision"])).fetchone()
            if row is None:
                admin_conn.execute("""INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind,
                                      subject_key, phap_nhan_id, valid_from, nguon_quyet_dinh, duyet_boi, ly_do)
                                      VALUES (%s,%s,%s,%s,%s,'COMPANY',%s,%s,%s,%s,%s,%s)""",
                                   (c["mapping_ref"], c["revision"], inst, ref, PROFILE_PAYLOAD_SHA256, c["company_key"], pn[c["existing_master_phap_nhan_ma"]],
                                    COMPANY_VALID_FROM, SEED, SEED, f"{c['match']}; buyer={c['buyer_direction']}; seller={c['seller_direction']}"))
                dem["anh_xa_cong_ty"] += 1
            elif (row[0], row[1], str(row[2]), row[3]) != ("COMPANY", c["company_key"], str(pn[c["existing_master_phap_nhan_ma"]]), SEED):
                _xung_dot("anh_xa_nguon COMPANY")
        # ứng viên literal (R2): payload nguyên văn + digest canonical do seed khai; trigger CSDL tính lại digest, dẫn xuất cột, chủ bảng/chỉ thêm
        for f in facts:
            h = digest_payload(f)
            dem["ung_vien_dong"] += admin_conn.execute("""INSERT INTO master.m2_ung_vien_dong (payload, fact_sha256, source_document_ref, source_document_sha256)
                                                          VALUES (%s::jsonb,%s,%s,%s) ON CONFLICT (mapping_ref, revision) DO NOTHING""",
                                                       (json.dumps(f, ensure_ascii=False), h, "tests/fixtures/m2_bridge/line-facts.json",
                                                        LINE_FACTS_SHA256)).rowcount
            row = admin_conn.execute("SELECT fact_sha256, source_document_sha256 FROM master.m2_ung_vien_dong WHERE mapping_ref = %s AND revision = %s",
                                     (f["mapping_ref"], f["revision"])).fetchone()
            if row is None or (row[0], row[1]) != (h, LINE_FACTS_SHA256):
                _xung_dot("m2_ung_vien_dong " + f["mapping_ref"])
        # actor/phân quyền/năng lực nguồn: MỘT LẦN; mở lại giữ nguyên quyền hiện hành (kể cả đã thu hồi), không cấp lại; không chạm actor M5
        da_co = admin_conn.execute("SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER,)).fetchone() is not None or \
            admin_conn.execute("SELECT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE dang_nhap = ANY(%s))", ([a["login"] for a in d["actors"]],)).fetchone()[0]
        for a in ([] if da_co else d["actors"]):
            dem["actor"] += admin_conn.execute("""INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true)
                                                  ON CONFLICT (dang_nhap) DO NOTHING""", (a["login"], a["login"], a["role"])).rowcount
            row = admin_conn.execute("SELECT id, vai_tro, mo_phong, trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (a["login"],)).fetchone()
            if (row[1], row[2], row[3]) != (a["role"], True, "HOAT_DONG"):
                _xung_dot("nguoi_dung " + a["login"])
            nd = row[0]
            for g in a["business"]:
                modules, duyet = sorted(set(g["modules"])), sorted(set(g["work_types"]))
                if set(modules) - {"M1", "M2"}:
                    raise DataError("NGUON_SEED", "Seed M2 chỉ cấp module M1/M2 (không M5/M9/CRM).")
                dem["phan_quyen"] += admin_conn.execute("""INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
                                                           VALUES (%s,%s,%s,%s) ON CONFLICT (nguoi_dung_id, phap_nhan_id) DO NOTHING""",
                                                        (nd, pn[g["pn_ma"]], duyet, modules)).rowcount
                q = admin_conn.execute("SELECT duyet_loai_viec, module FROM master.phan_quyen WHERE nguoi_dung_id = %s AND phap_nhan_id = %s",
                                       (nd, pn[g["pn_ma"]])).fetchone()
                if (sorted(q[0]), sorted(q[1])) != (duyet, modules):
                    _xung_dot("phan_quyen " + a["login"])
            for action in a["source_actions"]:
                target = pn[a["source_target_pn_ma"]] if action == "SOURCE_MAP" else None
                dem["nang_luc"] += admin_conn.execute("""INSERT INTO master.nang_luc_nguon (nguoi_dung_id, source_instance_id, profile_ref, profile_sha256,
                                                         hanh_dong, target_phap_nhan_id) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                                      (nd, inst, ref, PROFILE_PAYLOAD_SHA256, action, target)).rowcount
        admin_conn.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, 'r15') ON CONFLICT (key) DO NOTHING", (MARKER,))
    dem["mo_lai_giu_quyen_hien_hanh"] = da_co
    return dem


def dang_nhap_m2() -> list[str]:
    """Đúng 8 login DEMO M2 theo declarations đã pin (bộ chọn vai M2; quyền thật vẫn do CSDL quyết)."""
    return [a["login"] for a in doc_khai_bao()["actors"]]
