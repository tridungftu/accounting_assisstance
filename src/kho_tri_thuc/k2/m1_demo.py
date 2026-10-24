"""Nối M1 thật cho DEMO CRM-01 — không viết engine/đề xuất mới.

1. Sao kê DEMO (định dạng nguồn V12 `ktt-fixture-v1/sao_ke`) → `Store.ingest` (raw/hash/staging/evidence) trong kho M1 DEMO riêng của
   pháp nhân → `QuickPosting.propose` (engine M1 hiện có, tri thức DEMO ở trạng thái CHỜ DUYỆT, không giả là policy đã duyệt).
2. Chiếu sang K2 bằng **bộ chiếu hiện có** `tools/chuyen_sqlite_sang_pg.py` (chạy bằng chủ CSDL như đồng bộ hằng đêm): BANK →
   `kho.chung_tu SAO_KE` (khóa nguồn = khóa tự nhiên V12, `du_lieu._sqlite_id`), quick_items → `kho.de_xuat/de_xuat_dong` + việc V1.
   Chạy lại không trùng (bộ chiếu idempotent). Một BANK logic = một chứng từ K2; CRM chỉ thêm liên kết lên chính chứng từ đó.
Không đọc/sửa kho thật, policy thật hay Junsky.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from ..ha_tang.primitives import now_utc
from ..ha_tang.store import Store, write_immutable

ROOT = Path(__file__).resolve().parents[3]
TK_NGAN_HANG_DEMO = "00009001"
TK_TIEN_DEMO = "1121"


def _knowledge(pn_ma: str, doi_tac: str) -> list[dict]:
    from ..kiem_chung.fixtures import knowledge_item
    known = "2026-08-01T00:00:00Z"
    items = [knowledge_item("CATALOG", "COUNTERPARTY:" + doi_tac, {"kind": "COUNTERPARTY", "code": doi_tac, "name": "Đối tác DEMO " + doi_tac}, known=known, start="2026-01-01")]
    for code in (TK_TIEN_DEMO, "344", "131"):
        items.append(knowledge_item("CATALOG", "ACCOUNT:" + code, {"kind": "ACCOUNT", "code": code, "name": "TK DEMO " + code}, known=known, start="2026-01-01"))
    # Mẫu DEMO theo quy tắc tiền về chưa rõ cọc/đợt (TL32 §3.2, TL37/39 gọi CFO-03): nhánh CHƯA có hợp đồng → 344. Ở trạng thái CHỜ DUYỆT,
    # có nhãn DEMO. Nhánh CÓ hợp đồng không phải policy riêng: engine dùng fact HĐ hiệu lực (Engine.contract_facts) → 131.
    items.append(knowledge_item("POLICY", "DEMO_CFO03_TIEN_VE_CHUA_RO_" + pn_ma, {
        "contract_version": 2, "template_id": "DEMO_CFO03_" + pn_ma, "partition": "DEMO_CFO03_" + pn_ma, "direction": "IN", "tier": 1, "order": 1,
        "needs_open_item": False, "required_fields": ["debit_account", "credit_account"], "trigger": {"mode": "REGEX", "regex": "DEMO"},
        "fields": {"credit_account": "344"}}, known=known, start="2026-01-01"))
    return items


def config_m1(demo_config, root: Path, pn_ma: str):
    return replace(demo_config, entity_id=pn_ma, data_dir=Path(root) / ("m1-" + pn_ma))


def nhan_sao_ke(demo_config, root: Path, pn_ma: str, giao_dich: list[tuple], actor: str, doi_tac: str, *, hop_dong: dict | None = None) -> dict:
    """Nạp sao kê DEMO qua đường M1 hiện có và chạy engine đề xuất. Trả số chứng từ mới/trùng và đường dẫn kho M1.

    `hop_dong`: fact hợp đồng/lịch hiệu lực từ K2 (CrmK2.fact_hop_dong_m1, theo quyền người thao tác) đưa vào CONTEXT của engine M1
    hiện có (TL32 §3.2: chưa có HĐ hiệu lực ngày tiền về → nhánh 344 của tri thức chờ duyệt; có HĐ → 131 đợt gần nhất, Vàng, có bằng
    chứng, không tự phân bổ). Tiền đã đề xuất trước đó không bị đề xuất lại khi HĐ đến sau."""
    from ..giao_dien.quick import QuickPosting
    from ..tri_thuc.service import Knowledge
    config = config_m1(demo_config, root, pn_ma)
    days = sorted(d for _, d, _, _ in giao_dich)
    records = [{"business_date": d, "currency": "VND", "amount": str(so), "bank": "BANK_DEMO", "account": TK_NGAN_HANG_DEMO, "id_scope": "crm-demo-v1",
                "reference": ma, "identity_verified": True, "description": mo_ta, "counterparty_name": "DOI TAC DEMO"} for ma, d, so, mo_ta in giao_dich]
    total = sum(so for _, _, so, _ in giao_dich)
    value = {"format": "ktt-fixture-v1", "synthetic": True, "source": "sao_ke",
             "manifest": {"entity_id": pn_ma, "source_system": "DEMO_SAO_KE_CRM", "as_of": days[-1], "coverage_from": days[0],
                          "coverage_to_exclusive": (date.fromisoformat(days[-1]) + timedelta(days=1)).isoformat(),
                          "exported_at": days[-1] + "T23:00:00Z", "known_at": days[-1] + "T23:00:00Z", "known_at_basis": "DEMO CLOCK", "scope": "sao kê DEMO CRM"},
             "controls": {"count": len(records), "totals": {"BANK/VND": str(total)}, "opening_balance": "0", "closing_balance": str(total)}, "records": records}
    path = config.data_dir / "nguon" / ("sao_ke_" + "_".join(r["reference"] for r in records) + ".json")
    write_immutable(path, json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))  # nạp lại cùng sao kê: không ghi đè tệp nguồn
    with Store(config) as store:
        quick = QuickPosting(store)
        if not store.conn.execute("SELECT 1 FROM knowledge_versions LIMIT 1").fetchone():
            Knowledge(store).stage_many(_knowledge(pn_ma, doi_tac), actor, "2026-08-01T00:00:00Z")  # chờ duyệt, không tự duyệt
            quick.set_cash_mapping(TK_NGAN_HANG_DEMO, TK_TIEN_DEMO, actor, source="MANUAL", evidence=["DEMO_CRM"])
        report = store.ingest(path)
        if report["state"] != "COMMITTED":
            raise ValueError("Sao kê DEMO không nạp được: " + json.dumps(report.get("issues"), ensure_ascii=False))
        rows = quick.propose(report["attempt_id"], "sao_ke", actor, cutoff=now_utc(), contract_facts=hop_dong)
    return {"moi": report["inserted_documents"], "trung": report["duplicate_documents"], "de_xuat": len(rows["rows"]), "sqlite": str(store.db_path)}


DUNG_CHUNG_MODULE_KHAC = ("COUNTERPARTY → master.doi_tac_ma_junsky", "PROJECT → master.du_an", "artifacts → kho.tep_goc")


def chieu_sang_k2(sqlite_path: str, admin_dsn: str) -> dict:
    """Chạy bộ chiếu legacy→K2 hiện có bằng tài khoản chủ CSDL (DSN qua biến môi trường của tiến trình con, không qua dòng lệnh).

    Bộ chiếu tự quyết đạt/không TRONG giao dịch và rollback khi không đạt (không ghi nửa chừng); hash nguồn sai bị từ chối trước mọi
    ghi. Pháp nhân K2 dùng chung đối tác/dự án/tệp với CRM nên chạy `--cho-phep-du-dung-chung`: đích nhiều hơn nguồn ở ba bảng đó
    chỉ đạt khi MỌI bản ghi nguồn có ở đích theo khóa ổn định; mọi ánh xạ khác và đối chiếu nội dung từng bản ghi phải khớp."""
    env = dict(os.environ, KHO_PG_DSN=admin_dsn, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "chuyen_sqlite_sang_pg.py"), "--sqlite", sqlite_path, "--cho-phep-du-dung-chung"],
                       env=env, capture_output=True, text=True)
    try:
        report = json.loads(r.stdout)
    except ValueError:
        return {"ma_thoat": r.returncode, "ok": False, "da_ghi": False, "loi": (r.stderr or "")[-300:]}
    dem = report.get("doi_chieu", [])
    out = {"ma_thoat": r.returncode, "da_ghi": bool(report.get("da_ghi")), "tu_choi": report.get("tu_choi"),
           "lech_dem": [x["bang"] for x in dem if not x["khop"]],
           "lech_dung_chung": [{k: x[k] for k in ("bang", "nguon", "dich")} for x in dem if x.get("du_dung_chung")],
           "dung_chung_tung_ban_ghi": report.get("dung_chung"),
           "lech_noi_dung": sorted(k for k, v in report.get("doi_chieu_noi_dung", {}).items() if not v.get("khop", True)),
           "bank_sao_ke": next((x["dich"] for x in dem if x["bang"].startswith("BANK")), None),
           "quick_de_xuat": next((x["dich"] for x in dem if x["bang"].startswith("quick_items")), None)}
    out["ok"] = r.returncode == 0 and out["da_ghi"] and not out["lech_dem"] and not out["lech_noi_dung"]
    return out


# R4: contract encoding của BANK chiếu từ kho M1 V12 — amount_minor INTEGER trong SQLite (Config V12 VND scale 0), bộ chiếu ghi |amount| +
# chiều. Proof chỉ cho chứng từ có khóa nguồn M1 (_sqlite_id) và loại tiền VND; còn lại không có proof (UNKNOWN → nối tiền M9 bị chặn).
PROOF_CONTRACT = {"id": "V12_STORE_VND_SCALE0", "version": "1", "encoding": "MINOR_INT64", "currency": "VND", "scale": 0,
                  "rule": "documents.amount_minor (SQLite INTEGER, đồng) → kho.chung_tu.so_tien_minor = |amount_minor|, chieu theo dấu (tools/chuyen_sqlite_sang_pg.py)"}


def ghi_proof_tien(admin_conn, pn_ma: str) -> dict:
    """Verifier (chủ CSDL, như bộ chiếu): gắn proof encoding lần đầu cho BANK M1 của pháp nhân chưa có proof hiệu lực. Bất biến; gọi lại
    không ghi thêm. Không đổi số tiền chứng từ."""
    from ..ha_tang.primitives import canonical_json, sha256
    contract_sha = sha256(canonical_json(PROOF_CONTRACT).encode())
    rows = admin_conn.execute("""SELECT c.id, c.du_lieu->>'_sqlite_id' AS sid FROM kho.chung_tu c JOIN master.phap_nhan p ON p.id = c.phap_nhan_id
                                 WHERE p.ma = %s AND c.loai = 'SAO_KE' AND c.du_lieu ? '_sqlite_id' AND rtrim(c.tien_te) = 'VND' AND c.so_tien_minor IS NOT NULL
                                   AND NOT EXISTS (SELECT 1 FROM kho.chung_tu_tien_encoding e WHERE e.chung_tu_id = c.id AND e.state = 'HIEU_LUC')""",
                              (pn_ma,)).fetchall()
    for r in rows:
        bank, sid = (r["id"], r["sid"]) if isinstance(r, dict) else (r[0], r[1])
        admin_conn.execute("SELECT kho.ghi_proof_tien_noi_bo(%s, 0::smallint, %s, %s, %s, %s, %s, 'PROVEN')",
                           (bank, PROOF_CONTRACT["id"], PROOF_CONTRACT["version"], contract_sha, f"m1-sqlite:documents/{sid}",
                            "documents.amount_minor→kho.chung_tu.so_tien_minor"))
    return {"proof_moi": len(rows), "contract": PROOF_CONTRACT["id"]}
