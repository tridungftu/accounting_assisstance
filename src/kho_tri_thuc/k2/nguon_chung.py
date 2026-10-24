"""Intake nguồn TRUNG TÍNH (M0, contract M0-M5-SQL-VA-FIXTURE-01 §4–§5) — dùng chung cho mọi module nhận nguồn trước pháp nhân.

- Registry (instance/profile/scope/master/measurement) do máy chủ tra từ CSDL đã seed; profile được kiểm lại bằng canonical digest
  (`canonical_json` → SHA-256 UTF-8), không bằng SHA(jsonb::text). Trình duyệt chỉ gửi ID registry được phép, không gửi facts/PN/PROVEN.
- Capture H `m0-capture/v1` = SHA-256 canonical của: instance, profile {reference_id, sha256}, scope cấu hình (sections sorted unique),
  coverage, mã lỗi báo cáo (sorted unique), artifacts theo vai trò (sorted, chỉ vai trò có mặt) {role, raw_sha256, byte_length, media_type}
  từ BYTES THỰC. Actor/key/thời điểm/PN/mapping/review KHÔNG vào H (vẫn audit riêng). Khác reader semantic/request H và PN-operation H.
- Quyền nguồn (INTAKE/READ_SOURCE/SOURCE_MAP) kiểm ở CSDL TRƯỚC khi khóa/tra biên nhận/artifact; khóa namespace (instance, CAPTURE, key)
  bằng advisory lock giao dịch + UNIQUE — hai kết nối cùng key chỉ một occurrence (không mutex Python).
- Blob content-addressed `m0-raw/<sha>` ghi độc quyền + kiểm hash; lỗi giữ nguyên bằng chứng, không dọn để giả atomicity.
- Sửa 02: không còn writer free-JSON. Facts đã kiểm được pin vào stage bất biến `giao_tiep.stage_tin_cay` bằng kết nối CHỦ BẢNG đã cấu hình
  (cùng giao dịch với khóa/biên nhận); consumer CSDL chỉ nhận stage ID + expected H. `reported_errors` vắng = [], hiện diện phải là list mã.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, sha256
from ..ha_tang.store import write_immutable

CAPTURE_CONTRACT = "m0-capture/v1"
_MA_LOI = re.compile(r"[A-Z0-9_]{1,80}")
_KHOA = re.compile(r"[A-Za-z0-9_.:-]{1,200}")


def digest_payload(payload) -> str:
    """Digest canonical của payload registry (sort_keys, ensure_ascii=False, separators , :, không NaN, không newline cuối)."""
    return sha256(canonical_json(payload).encode("utf-8"))


def _gia_tri(row, key):
    return None if row is None else row[key]


def kiem_khoa(client_key) -> str:
    if not isinstance(client_key, str) or not _KHOA.fullmatch(client_key):
        raise DataError("KHOA_IDEMPOTENCY", "Khóa thao tác phải 1–200 ký tự [A-Za-z0-9_.:-].")
    return client_key


# ---------------------------------------------------------------- registry (đọc bằng login ứng dụng; seed do chủ CSDL)
def doc_profile(conn, source_instance: str) -> dict:
    """Profile bất biến duy nhất của instance (DEMO: một profile). Kiểm canonical digest; nhiều profile thì bắt buộc chọn tường minh."""
    rows = conn.execute("""SELECT p.profile_ref, p.profile_sha256, p.payload FROM master.nguon_profile p
                           JOIN master.nguon_instance i ON i.source_instance_id = p.source_instance_id
                           WHERE p.source_instance_id = %s AND i.trang_thai = 'HOAT_DONG' ORDER BY p.profile_ref""", (source_instance,)).fetchall()
    if len(rows) != 1:
        raise DataError("NGUON_PROFILE", "Instance nguồn chưa có đúng một profile đang hoạt động trong registry.")
    r = rows[0]
    if digest_payload(r["payload"]) != r["profile_sha256"]:
        raise DataError("NGUON_PROFILE_DIGEST", "Payload profile trong registry không khớp digest đã pin.")
    return {"reference_id": r["profile_ref"], "sha256": r["profile_sha256"], "payload": r["payload"]}


def doc_pham_vi(conn, source_instance: str, profile: dict, scope_ref: str) -> dict:
    """Phạm vi cấu hình bất biến. M0015: có `scope_kind` (KHO10_PHIEU cũ / INVOICE_SET mới với tập company key, MaKho/SoPhieu NULL).
    M0016: L11_EVIDENCE_SET có PN typed (`phap_nhan_id`) — PN của bằng chứng lấy từ đây, không từ trình duyệt."""
    row = conn.execute("""SELECT scope_ref, ma_kho, so_phieu, sections, coverage_binding, scope_kind, company_keys, phap_nhan_id FROM master.nguon_pham_vi
                          WHERE source_instance_id = %s AND scope_ref = %s AND profile_ref = %s AND profile_sha256 = %s""",
                       (source_instance, scope_ref, profile["reference_id"], profile["sha256"])).fetchone()
    if row is None:
        raise DataError("NGUON_PHAM_VI", "Phạm vi nguồn không có trong registry của instance/profile này.")
    return {"scope_ref": row["scope_ref"], "MaKho": row["ma_kho"], "SoPhieu": row["so_phieu"], "sections": sorted(set(row["sections"])),
            "coverage_binding": row["coverage_binding"], "scope_kind": row["scope_kind"], "company_keys": list(row["company_keys"] or []),
            "phap_nhan_id": None if row["phap_nhan_id"] is None else str(row["phap_nhan_id"])}


def doc_master_catalog(conn, raw_sha256: str) -> str | None:
    return _gia_tri(conn.execute("SELECT reference_id FROM master.nguon_master_noi_dung WHERE raw_sha256 = %s", (raw_sha256,)).fetchone(), "reference_id")


def doc_su_kien_do_luong(conn, source_instance: str, profile: dict) -> list[dict]:
    """Facts đo lường bất biến theo instance + profile ref/SHA (không tra declaration_ref một mình); kiểm digest payload."""
    out = []
    for r in conn.execute("""SELECT declaration_ref, payload_sha256, payload, dieu_kien FROM master.nguon_su_kien_do_luong
                             WHERE source_instance_id = %s AND profile_ref = %s AND profile_sha256 = %s ORDER BY declaration_ref, payload_sha256""",
                          (source_instance, profile["reference_id"], profile["sha256"])):
        if digest_payload(r["payload"]) != r["payload_sha256"]:
            raise DataError("DO_LUONG_DIGEST", "Payload facts đo lường không khớp digest đã pin.")
        out.append(dict(r))
    return out


# ---------------------------------------------------------------- artifacts / H
def artifacts(profile: dict, theo_vai_tro: dict, media_types: dict | None = None) -> list[dict]:
    """Bản ghi vai trò theo profile: có mặt → {role, raw, raw_sha256, byte_length, media_type}; vắng → {role, co_mat False, ly_do_vang}.
    Không bịa hash/độ dài/proof cho vai trò vắng; vai trò lạ bị từ chối. Vai trò khai `media_type` đơn (M5) giữ nguyên quy tắc cũ; vai trò khai
    `allowed_media_types` (M2: NATIVE xml|zip) cần media do máy chủ xác định từ bytes (`media_types`) và phải thuộc danh sách hữu hạn."""
    roles = {r["role"]: r for r in profile["payload"]["artifact_roles"]}
    la = sorted(set(theo_vai_tro) - set(roles))
    if la:
        raise DataError("NGUON_VAI_TRO_LA", "Vai trò artifact ngoài profile: " + ",".join(la))
    out = []
    for role in sorted(roles):
        raw = theo_vai_tro.get(role)
        if raw is None:
            out.append({"role": role, "co_mat": False, "ly_do_vang": "ARTIFACT_ROLE_ABSENT" + ("_REQUIRED" if roles[role]["required"] else "")})
            continue
        if not isinstance(raw, (bytes, bytearray)):
            raise DataError("NGUON_ARTIFACT", "Artifact phải là bytes thực.")
        raw = bytes(raw)
        if "allowed_media_types" in roles[role]:
            media = (media_types or {}).get(role)
            if media not in roles[role]["allowed_media_types"]:
                raise DataError("NGUON_MEDIA_SAI", f"Media của vai trò {role} ngoài danh sách profile cho phép.")
        else:
            media = roles[role]["media_type"]
        out.append({"role": role, "co_mat": True, "raw": raw, "raw_sha256": sha256(raw), "byte_length": len(raw), "media_type": media})
    return out


def _vai_tro_cong_khai(a: dict) -> dict:
    return {k: v for k, v in a.items() if k != "raw"}


def bundle_digest(arts: list[dict]) -> str:
    """Định danh nội dung bundle: mọi vai trò profile (có mặt với hash/độ dài/media; vắng với lý do) — master đổi thì bundle đổi."""
    return sha256(canonical_json(sorted((_vai_tro_cong_khai(a) for a in arts), key=lambda a: a["role"])).encode("utf-8"))


VANG = object()  # sentinel: trường reported_errors VẮNG (mặc định []); null/scalar/object hiện diện là container sai


def kiem_ma_loi(reported_errors=VANG) -> list[str]:
    """I2/SR7: vắng → []; hiện diện thì PHẢI là list các mã [A-Z0-9_] (không null/bool/0/chuỗi/object, không ép kiểu). Trả bản sao list."""
    if reported_errors is VANG:
        return []
    if not isinstance(reported_errors, list):
        raise DataError("NGUON_MA_LOI", "reported_errors phải là danh sách mã lỗi (vắng = rỗng); null/chuỗi/số/object bị từ chối.")
    if any(not isinstance(e, str) or not _MA_LOI.fullmatch(e) for e in reported_errors):
        raise DataError("NGUON_MA_LOI", "Mỗi mã lỗi capture báo cáo phải là chuỗi [A-Z0-9_]{1,80}.")
    return list(reported_errors)


def coverage_hieu_luc(coverage: str, arts: list[dict], ly_do_graph: list[str]) -> tuple[str, list[str]]:
    """Coverage đã kiểm (tách khỏi claim gốc trong H): thiếu vai trò bắt buộc hoặc graph/nguồn partial ⇒ PARTIAL kèm lý do; không sửa claim gốc."""
    ly_do = [a["ly_do_vang"] for a in arts if not a["co_mat"] and a["ly_do_vang"].endswith("_REQUIRED")] + list(ly_do_graph)
    return ("PARTIAL" if ly_do else coverage), sorted(set(ly_do))


def phong_bi_capture(source_instance: str, profile: dict, scope: dict, coverage: str, reported_errors, arts: list[dict]) -> dict:
    coverage_values = profile["payload"]["coverage_values"]
    if not isinstance(coverage, str) or coverage not in coverage_values:
        raise DataError("NGUON_COVERAGE", "Coverage báo cáo ngoài miền của profile.")
    errs = kiem_ma_loi(reported_errors)
    if scope.get("scope_kind") == "INVOICE_SET":  # M2: scope theo tập company key, không kho/phiếu giả; M5 giữ nguyên dạng cũ (H cũ không đổi)
        source_scope = {"scope_ref": scope["scope_ref"], "scope_kind": "INVOICE_SET", "company_keys": sorted(set(scope["company_keys"])),
                        "sections": sorted(set(scope["sections"]))}
    elif scope.get("scope_kind") == "L11_EVIDENCE_SET":  # L11: bằng chứng theo PN typed của scope (không kho/phiếu/company giả)
        source_scope = {"scope_ref": scope["scope_ref"], "scope_kind": "L11_EVIDENCE_SET", "phap_nhan_id": scope["phap_nhan_id"],
                        "sections": sorted(set(scope["sections"]))}
    else:
        source_scope = {"scope_ref": scope["scope_ref"], "MaKho": scope["MaKho"], "SoPhieu": scope["SoPhieu"], "sections": sorted(set(scope["sections"]))}
    return {"contract": CAPTURE_CONTRACT, "source_instance": source_instance,
            "source_profile": {"reference_id": profile["reference_id"], "sha256": profile["sha256"]},
            "source_scope": source_scope,
            "coverage": coverage, "reported_errors": sorted(set(errs)),
            "artifacts": sorted(({"role": a["role"], "raw_sha256": a["raw_sha256"], "byte_length": a["byte_length"], "media_type": a["media_type"]}
                                 for a in arts if a["co_mat"]), key=lambda a: a["role"])}


def bam_capture(envelope: dict) -> str:
    return sha256(canonical_json(envelope).encode("utf-8"))


def ghi_blob(root: Path, raw: bytes) -> str:
    """Ghi blob content-addressed độc quyền (không ghi đè); đọc lại kiểm hash. Trả object key."""
    digest = sha256(raw)
    path = Path(root) / "m0-raw" / digest
    write_immutable(path, raw)
    if sha256(path.read_bytes()) != digest:
        raise DataError("ARTIFACT_CHANGED", "Blob raw sau khi ghi không khớp hash — giữ nguyên làm bằng chứng.")
    return f"m0-raw/{digest}"


def doc_blob(root: Path, object_key: str, raw_sha256: str, byte_length: int) -> bytes:
    if object_key != f"m0-raw/{raw_sha256}":
        raise DataError("RAW_KEY", "Object key raw không hợp lệ.")
    path = (Path(root) / object_key).resolve()
    if not path.is_relative_to((Path(root) / "m0-raw").resolve()):
        raise DataError("RAW_KEY", "Đường dẫn raw không hợp lệ.")
    raw = path.read_bytes()
    if len(raw) != byte_length or sha256(raw) != raw_sha256:
        raise DataError("ARTIFACT_CHANGED", "Raw đã lưu không khớp hash/độ dài.")
    return raw


# ---------------------------------------------------------------- CSDL (hàm integration definer; quyền nguồn kiểm ở CSDL trước tra cứu)
def tim_lan_nhan(conn, source_instance: str, profile: dict, client_key: str) -> dict | None:
    row = conn.execute("SELECT * FROM giao_tiep.nguon_tim_lan_nhan(%s, %s, %s, %s)",
                       (source_instance, profile["reference_id"], profile["sha256"], client_key)).fetchone()
    return dict(row) if row else None


def du_lieu_stage_capture(*, receipt_id: str, scope: dict, coverage: str, coverage_hl: str, envelope: dict, arts: list[dict], rows: list[dict],
                          ket_qua: dict, promote: dict | None) -> dict:
    """Facts pin trong stage CAPTURE (do máy chủ tính từ bytes thực + reader frozen): consumer CSDL chỉ đọc từ đây, không nhận từ caller."""
    return {"receipt_id": receipt_id, "scope_ref": scope["scope_ref"], "coverage": coverage, "coverage_hieu_luc": coverage_hl, "envelope": envelope,
            "bundle_sha256": bundle_digest(arts), "roles": [_vai_tro_cong_khai(a) for a in arts], "rows": rows, "ket_qua": ket_qua, "promote": promote}


def ghi_stage(conn_chu, dt: dict, *, muc_dich: str, client_key: str, h: str, source_instance: str, profile_ref: str, profile_sha256: str,
              du_lieu: dict, phap_nhan_id=None, module: str | None = None) -> str:
    """Ghi stage bất biến bằng kết nối CHỦ BẢNG đã cấu hình, trong giao dịch có danh tính phiên (trigger kiểm chủ bảng + actor). Trả stage ID.
    `module` (M0015): NULL cho M5 cũ, 'M2' cho capture hóa đơn — consumer/finalizer phân nhánh theo cột này."""
    row = conn_chu.execute("""INSERT INTO giao_tiep.stage_tin_cay (muc_dich, client_key, h, actor_id, actor, source_instance_id, profile_ref, profile_sha256,
                              phap_nhan_id, du_lieu, module) VALUES (%s,%s,%s,%s::uuid,%s,%s,%s,%s,%s::uuid,%s::jsonb,%s) RETURNING id""",
                           (muc_dich, client_key, h, dt["id"], dt["dang_nhap"], source_instance, profile_ref, profile_sha256, phap_nhan_id,
                            json.dumps(du_lieu, ensure_ascii=False), module)).fetchone()
    return str(row["id"] if isinstance(row, dict) else row[0])


def tieu_thu_capture(conn, stage_id: str, h: str) -> dict:
    row = conn.execute("SELECT * FROM giao_tiep.nguon_tieu_thu_capture(%s::uuid, %s)", (stage_id, h)).fetchone()
    return dict(row)


def chot_ket_qua(conn_chu, stage_id: str, h: str, snapshot_moi: bool, promote: dict) -> dict:
    """SR02-1: chốt kết quả cuối bất biến của lần nhận (chỉ kết nối CHỦ BẢNG, cùng giao dịch, sau typed/hold). CSDL đối chiếu refs/HOLD với facts
    thật rồi ghi một lần; trả đúng bản đã ghi {stage_id, snapshot_moi, promote} để fresh và replay giống nhau."""
    row = conn_chu.execute("SELECT giao_tiep.nguon_chot_ket_qua(%s::uuid, %s, %s, %s::jsonb) AS v",
                           (stage_id, h, snapshot_moi, json.dumps(promote, ensure_ascii=False, default=str))).fetchone()
    v = row["v"] if isinstance(row, dict) else row[0]
    return {"stage_id": str(v["stage_id"]), "snapshot_moi": v["snapshot_moi"], "promote": v["promote"]}


def anh_xa_hien_hanh(conn, source_instance: str, profile: dict, ma_kho: str) -> dict | None:
    rows = conn.execute("SELECT * FROM giao_tiep.nguon_anh_xa_hien_hanh(%s, %s, %s, 'WAREHOUSE', %s)",
                        (source_instance, profile["reference_id"], profile["sha256"], ma_kho)).fetchall()
    if len(rows) > 1:
        raise DataError("ANH_XA_CHONG_LAN", "Có nhiều mapping hiện hành cho cùng kho nguồn — giữ chờ, không chọn.")
    return dict(rows[0]) if rows else None


def doc_lan_nhan(conn, receipt_id: str) -> dict | None:
    row = conn.execute("SELECT giao_tiep.nguon_doc_lan_nhan(%s::uuid) AS v", (receipt_id,)).fetchone()
    return row["v"] if row else None


def danh_sach_lan_nhan(conn) -> list[dict]:
    return [r["v"] for r in conn.execute("SELECT v FROM giao_tiep.nguon_danh_sach_lan_nhan() AS v")]


def doc_tep(conn, root: Path, receipt_id: str, vai_tro: str) -> tuple[dict, bytes]:
    row = conn.execute("SELECT * FROM giao_tiep.nguon_doc_tep(%s::uuid, %s)", (receipt_id, vai_tro)).fetchone()
    if row is None:
        raise DataError("NGUON_KHONG_CO_QUYEN", "Không có raw này hoặc phiên chưa có READ_SOURCE của nguồn.")
    return dict(row), doc_blob(root, row["object_key"], row["raw_sha256"], row["byte_length"])


def receipt_id_moi() -> str:
    return str(uuid.uuid4())
