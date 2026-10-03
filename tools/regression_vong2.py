"""Run the August V1b slice as a technical regression without quality gates.

The original V1b scripts and their protected directories are read only.  This
runner writes only an aggregate two-column result in the target V2–V6 folder.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
V1B = PROJECT / "var" / "vong-2" / "V1b"
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(V1B))

from chuan_bi import SOURCE, prepare  # noqa: E402
from kho_tri_thuc.de_xuat.engine import Engine  # noqa: E402
from kho_tri_thuc.ha_tang.config import Config  # noqa: E402
from kho_tri_thuc.ha_tang.primitives import now_utc  # noqa: E402
from kho_tri_thuc.ha_tang.runtime import document  # noqa: E402
from kho_tri_thuc.ha_tang.store import Store  # noqa: E402
from kho_tri_thuc.tri_thuc.service import Knowledge  # noqa: E402
from kho_tri_thuc.trang_thai.service import Sessions  # noqa: E402
from kho_tri_thuc.xuat.service import ReviewExport  # noqa: E402


def _run(target: Path, leak_free: bool) -> dict:
    name = "khong_ro_ri" if leak_free else "hoi_cuu"
    run = target / (name + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run.mkdir(parents=True, exist_ok=False)
    catalogs, items, statuses, sidecar, _manifest = prepare(run / "chuan-bi", leak_free=leak_free)
    config = run / "config.toml"
    config.write_text("[app]\nenvironment='fixture'\nentity_id='PLHN_THU_NGHIEM_FIXTURE'\ndata_dir='kho'\n[money]\ncurrency='VND'\nscale=0\n", encoding="utf-8")

    class ReplayEngine(Engine):
        def preview(self, bank, bundle, cutoff, *args, **kwargs):
            extra = sidecar.get(bank.get("reference"))
            if extra and extra["known_at"] <= cutoff:
                bank = {**bank, "counterparty_name": extra["counterparty_name"]}
            return super().preview(bank, bundle, cutoff, *args, **kwargs)

    with Store(Config.load(config)) as store:
        knowledge, sessions, review = Knowledge(store), Sessions(store), ReviewExport(store)
        sessions.engine = ReplayEngine(store)
        attempts = {}
        for path in sorted(SOURCE.glob("*.json")):
            if path.name.startswith(("01-", "02-", "03-", "03b-", "04-", "05-")):
                attempts[path.name] = store.ingest(path)["attempt_id"]
        identifiers = knowledge.stage_many(catalogs + items, "MO_PHONG_KIEM_CHUNG", now_utc())
        banks = [document(store, row[0]) for row in store.conn.execute("SELECT id FROM documents WHERE kind='BANK' ORDER BY business_date,natural_key")]
        for identifier in identifiers:
            knowledge.approve(identifier, "MO_PHONG_KIEM_CHUNG", now_utc())
        session = sessions.open(attempts["05-junsky-2026-T1-T7.json"], [bank["id"] for bank in banks], now_utc(), "MO_PHONG_KIEM_CHUNG")
        sessions.propose(session["id"])
        review.review_workbook(session["id"], "MO_PHONG_KIEM_CHUNG", now_utc())
        sessions.cancel(session["id"], "MO_PHONG_KIEM_CHUNG", now_utc(), "Hồi quy kỹ thuật V2–V6; không xuất hay nhập Junsky")
        return {"da_chay": True, "integrity_ok": store.status()["integrity"]["ok"], "scenarios": ["C2"],
                "ket_luan": "Chỉ hồi quy kỹ thuật; không dùng làm cổng chất lượng."}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--vong", required=True)
    parser.add_argument("--che-do", choices=("hoi-cuu", "khong-ro-ri", "ca-hai"), default="ca-hai")
    args = parser.parse_args()
    result_path = args.target / "KET-QUA.json"
    result = {"vong": args.vong, "loai": "HOI_QUY_KY_THUAT_T8", "dung_nguong_chat_luong": False,
              "hoi_cuu": {"da_chay": False}, "khong_ro_ri": {"da_chay": False}}
    if result_path.is_file():
        try:
            previous = json.loads(result_path.read_text(encoding="utf-8"))
            if previous.get("vong") == args.vong:
                result.update({key: previous[key] for key in ("hoi_cuu", "khong_ro_ri") if key in previous})
        except (UnicodeError, json.JSONDecodeError):
            pass
    if args.che_do in {"hoi-cuu", "ca-hai"}:
        result["hoi_cuu"] = _run(args.target, False)
    if args.che_do in {"khong-ro-ri", "ca-hai"}:
        result["khong_ro_ri"] = _run(args.target, True)
    (args.target / "KET-QUA.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"vong": args.vong, "hoi_cuu": result["hoi_cuu"].get("integrity_ok"), "khong_ro_ri": result["khong_ro_ri"].get("integrity_ok")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
