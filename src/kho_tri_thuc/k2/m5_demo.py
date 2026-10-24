"""Seed DEMO M0/M5 (chạy bằng tài khoản chủ CSDL sau `crm_demo.khoi_tao`): registry nguồn đã root pin + 8 actor MO_PHONG_* + năng lực nguồn.

CHỈ THÊM: không gọi lại seed CRM, không UPSERT/ghi đè người dùng/phân quyền/module có sẵn, không cấp M9/CRM, không reset CRM/M1/CFO_NTD.
Sửa 02 (SR5): actor/quyền/năng lực chỉ khởi tạo một lần (marker); mở lại chỉ kiểm/bổ sung registry bất biến, không cấp lại năng lực đã thu hồi.
Hàng bất biến đã có mà khác nội dung → từ chối (NGUON_SEED_XUNG_DOT), không sửa. Mọi digest được kiểm lại bằng canonical_json trước khi ghi:
registry SHA, profile/measurement payload digest, master raw bytes theo manifest. Alias DEMO_PN_A/B → PN_DEMO_A/B có sẵn (không tạo PN).
Không seed lịch sử/accepted/eligible/digest K01–K10 — kết quả do reader + repository + review thực tạo ra. Dữ liệu tổng hợp, không nguồn thật.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..ha_tang.primitives import DataError, sha256
from .nguon_chung import digest_payload

FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
M0M5 = FIXTURE / "m0_m5"
KHO10 = FIXTURE / "kho_10"
REGISTRY_SHA256 = "780180aaa8da3d135ada9693e1dcc9f5a32173f7fc05d22c92cd2c745d0b3883"
MANIFEST_SHA256 = "51b794ae55559c7245d99c163270fdb5fdd8405eb4a73b1d45c3e7a8ea2bbf5e"
PURE_MANIFEST_SHA256 = "5d680a1cd4a691fba5d6eca7056bdc94f9fbf558b80e2415d97f9808215c8e66"
MAU = tuple(f"K{i:02d}" for i in range(1, 11))
SEED_MAPPING = "ROOT_SEED_DEMO"
MARKER = "demo_seed_m5_actor"


def _doc_pin(path: Path, sha: str) -> bytes:
    raw = path.read_bytes()
    if sha256(raw) != sha:
        raise DataError("FIXTURE_PIN", f"Tệp fixture {path.name} không khớp SHA đã pin.")
    return raw


def doc_registry() -> dict:
    reg = json.loads(_doc_pin(M0M5 / "trusted-registry.json", REGISTRY_SHA256).decode("utf-8"))
    for p in reg["source_profiles"]:
        if digest_payload(p["payload"]) != p["sha256"]:
            raise DataError("NGUON_PROFILE_DIGEST", "Payload profile registry không khớp digest.")
    for f in reg["measurement_facts"]:
        if digest_payload(f["payload"]) != f["payload_sha256"]:
            raise DataError("DO_LUONG_DIGEST", "Payload facts đo lường registry không khớp digest.")
    for m in reg["master_content_catalog"]:
        raw = (M0M5 / m["raw_path"]).read_bytes()
        if sha256(raw) != m["raw_sha256"] or len(raw) != m["byte_length"]:
            raise DataError("MASTER_RAW_PIN", "Master raw registry không khớp SHA/độ dài.")
    if len(reg["actors"]) != 8:
        raise DataError("NGUON_SEED", "Registry DEMO phải có đúng 8 actor.")
    return reg


def doc_manifest() -> dict:
    return json.loads(_doc_pin(M0M5 / "manifest.json", MANIFEST_SHA256).decode("utf-8"))


def mau(ten: str) -> dict:
    """Mẫu DEMO đã pin: bytes native/master thực + coverage/lỗi capture do nguồn báo (K07 PARTIAL). Không phải authority/history."""
    if ten not in MAU:
        raise DataError("M5_MAU", "Không có mẫu DEMO này.")
    _doc_pin(KHO10 / "manifest.json", PURE_MANIFEST_SHA256)
    entry = next(e for e in doc_manifest()["entries"] if e["case_id"] == ten)
    native = _doc_pin((M0M5 / entry["native_path"]).resolve(), entry["native_sha256"])
    master = _doc_pin(M0M5 / entry["master_path"], entry["master_sha256"])
    ctx = json.loads(_doc_pin((M0M5 / entry["pure_context_path"]).resolve(), entry["pure_context_sha256"]).decode("utf-8"))
    return {"source_instance": entry["source_instance"], "native": native, "master": master, "coverage": entry["reported_coverage"],
            "reported_errors": list(ctx.get("reported_capture_errors") or []), "master_reference_id": entry["master_reference_id"]}


def _mot(conn, sql, params):
    row = conn.execute(sql, params).fetchone()
    return None if row is None else row


def _xung_dot(what):
    raise DataError("NGUON_SEED_XUNG_DOT", f"Dữ liệu bất biến đã có khác registry đã pin ({what}) — không ghi đè.")


def khoi_tao(admin_conn) -> dict:
    """admin_conn: psycopg autocommit, chủ CSDL, schema đã migrate đúng lineage. Idempotent, chỉ thêm. Trả số đếm."""
    reg = doc_registry()
    dem = {"instance": 0, "profile": 0, "pham_vi": 0, "master": 0, "do_luong": 0, "anh_xa": 0, "actor": 0, "phan_quyen": 0, "nang_luc": 0}
    with admin_conn.transaction():
        pn = {}
        for a in reg["phap_nhan_aliases"]:
            row = _mot(admin_conn, "SELECT id FROM master.phap_nhan WHERE ma = %s", (a["existing_phap_nhan_ma"],))
            if row is None:
                raise DataError("PHAP_NHAN", f"Thiếu pháp nhân {a['existing_phap_nhan_ma']} — chạy seed CRM DEMO trước, không tạo PN mới.")
            pn[a["existing_phap_nhan_ma"]] = row[0]
        profiles = {p["reference_id"]: p for p in reg["source_profiles"]}
        for s in reg["source_instances"]:
            dem["instance"] += admin_conn.execute("INSERT INTO master.nguon_instance (source_instance_id) VALUES (%s) ON CONFLICT DO NOTHING",
                                                  (s["source_instance"],)).rowcount
            p = profiles[s["profile_ref"]]
            if p["sha256"] != s["profile_sha256"]:
                _xung_dot("profile instance")
            dem["profile"] += admin_conn.execute("""INSERT INTO master.nguon_profile (source_instance_id, profile_ref, profile_sha256, payload)
                                                    VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""",
                                                 (s["source_instance"], p["reference_id"], p["sha256"], json.dumps(p["payload"], ensure_ascii=False))).rowcount
            row = _mot(admin_conn, "SELECT profile_sha256, payload FROM master.nguon_profile WHERE source_instance_id = %s AND profile_ref = %s",
                       (s["source_instance"], p["reference_id"]))
            if row[0] != p["sha256"] or digest_payload(row[1]) != p["sha256"]:
                _xung_dot("nguon_profile")
        for c in reg["configured_scopes"]:
            dem["pham_vi"] += admin_conn.execute("""INSERT INTO master.nguon_pham_vi (source_instance_id, profile_ref, profile_sha256, scope_ref, ma_kho, so_phieu,
                                                    sections, coverage_binding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                                 (c["source_instance"], c["profile_ref"], c["profile_sha256"], c["scope_ref"], c["MaKho"], c["SoPhieu"],
                                                  sorted(set(c["sections"])), c["coverage_binding"])).rowcount
            row = _mot(admin_conn, """SELECT profile_ref, profile_sha256, ma_kho, so_phieu, sections, coverage_binding FROM master.nguon_pham_vi
                                      WHERE source_instance_id = %s AND scope_ref = %s""", (c["source_instance"], c["scope_ref"]))
            if tuple(row) != (c["profile_ref"], c["profile_sha256"], c["MaKho"], c["SoPhieu"], sorted(set(c["sections"])), c["coverage_binding"]):
                _xung_dot("nguon_pham_vi")
        for m in reg["master_content_catalog"]:
            dem["master"] += admin_conn.execute("""INSERT INTO master.nguon_master_noi_dung (reference_id, raw_sha256, byte_length) VALUES (%s,%s,%s)
                                                   ON CONFLICT DO NOTHING""", (m["reference_id"], m["raw_sha256"], m["byte_length"])).rowcount
            row = _mot(admin_conn, "SELECT raw_sha256, byte_length FROM master.nguon_master_noi_dung WHERE reference_id = %s", (m["reference_id"],))
            if row is None or tuple(row) != (m["raw_sha256"], m["byte_length"]):
                _xung_dot("nguon_master_noi_dung")
        for f in reg["measurement_facts"]:
            dieu_kien = {"resolution_preconditions": f["resolution_preconditions"], "non_matching_resolution": f["non_matching_resolution"]}
            dem["do_luong"] += admin_conn.execute("""INSERT INTO master.nguon_su_kien_do_luong (source_instance_id, profile_ref, profile_sha256, declaration_ref,
                                                     payload_sha256, payload, dieu_kien) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) ON CONFLICT DO NOTHING""",
                                                  (f["source_instance"], f["profile_ref"], f["profile_sha256"], f["declaration_ref"], f["payload_sha256"],
                                                   json.dumps(f["payload"], ensure_ascii=False), json.dumps(dieu_kien, ensure_ascii=False))).rowcount
            row = _mot(admin_conn, """SELECT payload, dieu_kien FROM master.nguon_su_kien_do_luong WHERE source_instance_id = %s AND profile_ref = %s
                                      AND profile_sha256 = %s AND declaration_ref = %s AND payload_sha256 = %s""",
                       (f["source_instance"], f["profile_ref"], f["profile_sha256"], f["declaration_ref"], f["payload_sha256"]))
            if digest_payload(row[0]) != f["payload_sha256"] or row[1] != dieu_kien:
                _xung_dot("nguon_su_kien_do_luong")
        for m in reg["warehouse_mappings"]:
            row = _mot(admin_conn, """SELECT source_instance_id, profile_ref, profile_sha256, subject_kind, subject_key, phap_nhan_id, valid_from, nguon_quyet_dinh
                                      FROM master.anh_xa_nguon WHERE reference_id = %s AND revision = %s""", (m["reference_id"], m["revision"]))
            if row is None:
                admin_conn.execute("""INSERT INTO master.anh_xa_nguon (reference_id, revision, source_instance_id, profile_ref, profile_sha256, subject_kind,
                                      subject_key, phap_nhan_id, valid_from, valid_to, nguon_quyet_dinh, duyet_boi, ly_do)
                                      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                   (m["reference_id"], m["revision"], m["source_instance"], m["profile_ref"], m["profile_sha256"], m["subject_kind"], m["MaKho"],
                                    pn[m["phap_nhan_ma"]], m["valid_from"], m["valid_to"], SEED_MAPPING, SEED_MAPPING,
                                    f"{m['state']}; actual_mapping_verification={m['actual_mapping_verification']}"))
                dem["anh_xa"] += 1
            elif (row[0], row[1], row[2], row[3], row[4], str(row[5]), row[7]) != (m["source_instance"], m["profile_ref"], m["profile_sha256"], m["subject_kind"],
                                                                                   m["MaKho"], str(pn[m["phap_nhan_ma"]]), SEED_MAPPING):
                _xung_dot("anh_xa_nguon")
        # SR5: actor/phân quyền/năng lực nguồn chỉ khởi tạo MỘT LẦN; mở lại giữ nguyên quyền hiện hành (kể cả đã thu hồi), không cấp lại.
        da_co = admin_conn.execute("SELECT 1 FROM master.he_thong WHERE key = %s", (MARKER,)).fetchone() is not None or \
            admin_conn.execute("SELECT EXISTS (SELECT 1 FROM master.nguoi_dung WHERE dang_nhap = ANY(%s))", ([a["login"] for a in reg["actors"]],)).fetchone()[0]
        for a in ([] if da_co else reg["actors"]):
            dem["actor"] += admin_conn.execute("""INSERT INTO master.nguoi_dung (ten, dang_nhap, vai_tro, mo_phong) VALUES (%s,%s,%s,true)
                                                  ON CONFLICT (dang_nhap) DO NOTHING""", (a["login"], a["login"], a["role"])).rowcount
            row = _mot(admin_conn, "SELECT id, vai_tro, mo_phong, trang_thai FROM master.nguoi_dung WHERE dang_nhap = %s", (a["login"],))
            if (row[1], row[2], row[3]) != (a["role"], True, "HOAT_DONG"):
                _xung_dot("nguoi_dung " + a["login"])
            nd = row[0]
            for g in a["business_grants"]:
                module = {"M5": ["M5"], "M1": ["M1"]}[g["module"]]
                duyet = sorted(g["duyet_loai_viec"])
                dem["phan_quyen"] += admin_conn.execute("""INSERT INTO master.phan_quyen (nguoi_dung_id, phap_nhan_id, duyet_loai_viec, module)
                                                           VALUES (%s,%s,%s,%s) ON CONFLICT (nguoi_dung_id, phap_nhan_id) DO NOTHING""",
                                                        (nd, pn[g["phap_nhan_ma"]], duyet, module)).rowcount
                q = _mot(admin_conn, "SELECT duyet_loai_viec, module FROM master.phan_quyen WHERE nguoi_dung_id = %s AND phap_nhan_id = %s",
                         (nd, pn[g["phap_nhan_ma"]]))
                if (sorted(q[0]), sorted(q[1])) != (duyet, module):
                    _xung_dot("phan_quyen " + a["login"])
            for c in a["source_capabilities"]:
                targets = [pn[t] for t in c["allowed_target_pn_ma"]] or [None]
                for action in c["actions"]:
                    for t in (targets if action == "SOURCE_MAP" else [None]):
                        dem["nang_luc"] += admin_conn.execute("""INSERT INTO master.nang_luc_nguon (nguoi_dung_id, source_instance_id, profile_ref, profile_sha256,
                                                                 hanh_dong, target_phap_nhan_id) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                                              (nd, c["source_instance"], c["profile_ref"], c["profile_sha256"], action, t)).rowcount
        admin_conn.execute("INSERT INTO master.he_thong (key, value) VALUES (%s, 'v2') ON CONFLICT (key) DO NOTHING", (MARKER,))
    dem["mo_lai_giu_quyen_hien_hanh"] = da_co
    return dem


def dang_nhap_m5() -> list[str]:
    """Đúng 8 login DEMO M5 theo registry đã pin (bộ chọn vai M5; quyền thật vẫn do CSDL quyết)."""
    return [a["login"] for a in doc_registry()["actors"]]
