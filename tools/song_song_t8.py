"""V13 bước 6 — chạy song song đề xuất sao kê trên SQLite và PostgreSQL, so từng dòng (chỉ in số đếm).

Cách làm: chép kho (kho.sqlite + raw/) ra hai thư mục tạm; thư mục A mở bằng engine sqlite, thư mục B mở bằng
engine postgres (schema tạm, tự nạp từ kho.sqlite khi mở lần đầu — ket_noi). Trên mỗi bên chạy
``QuickPosting.repropose`` cho lần đề xuất sao kê mới nhất rồi so ``rows()``: mức, trạng thái, 5 trường định khoản,
TTCP, các dòng bút toán, cash_account/cash_leg, constraints, why, tùy chọn. Sau đó ``score()`` (so với Junsky)
nếu kho cho phép. Báo cáo: var/v13/song-song-T8.json + .md — không có dòng giao dịch, số tài khoản, tên đối tác.

Chạy (trong thư mục phần mềm, có .env với KHO_PG_DSN_ADMIN):
    python tools/song_song_t8.py --config cau_hinh.thu-T8.toml
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kho_tri_thuc.giao_dien.quick import QuickPosting  # noqa: E402
from kho_tri_thuc.ha_tang.config import Config  # noqa: E402
from kho_tri_thuc.ha_tang.primitives import DataError, canonical_json, now_utc  # noqa: E402
from kho_tri_thuc.ha_tang.store import Store  # noqa: E402

ACTOR = "MO_PHONG_SONG_SONG"
KHOA_CHAT = ("proposal_level", "state", "fields", "cost_center", "entry_lines")
KHOA_RONG = ("level", "lines", "cash_account", "cash_leg", "constraints", "why", "missing", "basis", "potential_existing", "journal_match",
             "options", "account_options", "name_options", "suggest_accounts", "demoted_rule", "identifier_conflict", "group", "debt_accounts")


def _chep_kho(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{(src_dir / 'kho.sqlite').resolve().as_posix()}?mode=ro", uri=True) as src, sqlite3.connect(dst_dir / "kho.sqlite") as dst:
        src.backup(dst)
    if (src_dir / "raw").is_dir():
        shutil.copytree(src_dir / "raw", dst_dir / "raw", dirs_exist_ok=True)


def _chay(config: Config, nhan: str) -> dict:
    t0 = time.perf_counter()
    with Store(config) as store:
        t_mo = time.perf_counter() - t0
        qp = QuickPosting(store)
        run = store.conn.execute("SELECT id FROM quick_runs WHERE source_kind='sao_ke' ORDER BY rowid DESC LIMIT 1").fetchone()
        if not run:
            raise DataError("NO_RUN", "Kho chưa có lần đề xuất sao kê nào.")
        t1 = time.perf_counter()
        ket_qua = qp.repropose(run[0], ACTOR)
        t_de_xuat = time.perf_counter() - t1
        diem = None
        try:
            t2 = time.perf_counter()
            s = qp.score(run[0])
            diem = {"summary": {f"{k[0]}|{k[1]}": v for k, v in (s.get("summary") or {}).items()} if isinstance(s.get("summary"), dict) else s.get("summary"),
                    "giay": round(time.perf_counter() - t2, 2)}
        except DataError as exc:
            diem = {"loi": exc.code}
        rows = {row["document_id"]: row for row in ket_qua["rows"]}
        return {"nhan": nhan, "engine": store.engine, "so_dong": len(rows), "giay_mo": round(t_mo, 2), "giay_de_xuat": round(t_de_xuat, 2),
                "rows": rows, "diem": diem, "stats": ket_qua.get("stats"), "levels": ket_qua.get("levels"),
                "schema": getattr(store.conn, "schema", None)}


def _so(a: dict, b: dict) -> dict:
    chung = sorted(set(a) & set(b))
    chi_a, chi_b = len(set(a) - set(b)), len(set(b) - set(a))
    lech_chat, lech_rong = {}, {}
    giong_chat = 0
    for doc in chung:
        ra, rb = a[doc], b[doc]
        khac = [k for k in KHOA_CHAT if canonical_json(ra.get(k)) != canonical_json(rb.get(k))]
        if khac:
            for k in khac:
                lech_chat[k] = lech_chat.get(k, 0) + 1
        else:
            giong_chat += 1
        for k in KHOA_RONG:
            if canonical_json(ra.get(k)) != canonical_json(rb.get(k)):
                lech_rong[k] = lech_rong.get(k, 0) + 1
    muc = {}
    for nhan, rows in (("sqlite", a), ("postgres", b)):
        c = {}
        for r in rows.values():
            c[r.get("proposal_level") or "?"] = c.get(r.get("proposal_level") or "?", 0) + 1
        muc[nhan] = dict(sorted(c.items()))
    return {"dong_chung": len(chung), "chi_sqlite": chi_a, "chi_postgres": chi_b, "giong_chat": giong_chat,
            "lech_chat_theo_khoa": lech_chat, "lech_rong_theo_khoa": lech_rong, "muc": muc}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True, help="cấu hình kho thử (vd cau_hinh.thu-T8.toml)")
    ap.add_argument("--dsn-key", default="KHO_PG_DSN_ADMIN", help="khóa .env có quyền tạo/xóa schema tạm")
    ap.add_argument("--bao-cao", type=Path, default=None, help="thư mục ghi báo cáo (mặc định var/v13 cạnh cấu hình)")
    ap.add_argument("--data-dir", type=Path, default=None, help="thư mục kho thử (mặc định theo cấu hình)")
    ap.add_argument("--giu-schema", action="store_true", help="không xóa schema PostgreSQL tạm sau khi so")
    args = ap.parse_args()
    for key in ("KHO_STORAGE_ENGINE", "KHO_STORAGE_SCHEMA"):
        os.environ.pop(key, None)
    config = Config.load(args.config, args.data_dir)
    if not (config.data_dir / "kho.sqlite").is_file():
        print("Kho thử chưa có kho.sqlite — không có gì để so.", file=sys.stderr)
        return 2
    bao_cao_dir = args.bao_cao or (args.config.resolve().parent / "var" / "v13")
    bao_cao_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ktt-song-song-") as tmp:
        a_dir, b_dir = Path(tmp) / "A-sqlite", Path(tmp) / "B-postgres"
        _chep_kho(config.data_dir, a_dir)
        _chep_kho(config.data_dir, b_dir)
        ket_a = _chay(replace(config, data_dir=a_dir, storage_engine="sqlite"), "A")
        cfg_b = replace(config, data_dir=b_dir, storage_engine="postgres", storage_schema="auto", storage_dsn_key=args.dsn_key)
        ket_b = _chay(cfg_b, "B")
        if not args.giu_schema and ket_b.get("schema"):
            from kho_tri_thuc.ha_tang import postgres as pg
            import psycopg
            with psycopg.connect(pg.dsn_from_env(None, key=args.dsn_key), autocommit=True) as raw:
                raw.execute(f'DROP SCHEMA "{ket_b["schema"]}" CASCADE')
    so = _so(ket_a["rows"], ket_b["rows"])
    # chấm điểm lỗi ở một bên → "không so được", không tính là giống (review lần 2 #12)
    diem_so_duoc = not ("loi" in (ket_a["diem"] or {}) or "loi" in (ket_b["diem"] or {}))
    diem_giong = diem_so_duoc and canonical_json(ket_a["diem"]) == canonical_json(ket_b["diem"])
    dat = so["dong_chung"] == ket_a["so_dong"] == ket_b["so_dong"] and so["giong_chat"] == so["dong_chung"] and not so["chi_sqlite"] and not so["chi_postgres"]
    report = {
        "luc": now_utc(), "nguon_kho": str(config.data_dir), "so_dong": {"sqlite": ket_a["so_dong"], "postgres": ket_b["so_dong"]},
        "thoi_gian_giay": {"sqlite": {"mo": ket_a["giay_mo"], "de_xuat": ket_a["giay_de_xuat"]}, "postgres": {"mo": ket_b["giay_mo"], "de_xuat": ket_b["giay_de_xuat"]}},
        "so_sanh": so, "diem": {"sqlite": ket_a["diem"], "postgres": ket_b["diem"], "so_duoc": diem_so_duoc, "giong": diem_giong},
        "pham_vi": "chỉ đề xuất lại sao kê của lần đề xuất mới nhất; hóa đơn, duyệt và xuất file chưa so",
        "stats": {"sqlite": ket_a["stats"], "postgres": ket_b["stats"]},
        "dat_tieu_chi_giong_tung_dong": dat, "dat_tieu_chi_thoi_gian_10s": ket_b["giay_de_xuat"] <= 10,
    }
    (bao_cao_dir / "song-song-T8.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md = [
        "# Chạy song song T8 — SQLite ↔ PostgreSQL (V13 bước 6)", "",
        f"Lúc: {report['luc']} · Kho: `{config.data_dir.name}` · Dòng sao kê: SQLite {ket_a['so_dong']} · PostgreSQL {ket_b['so_dong']}", "",
        "| Chỉ tiêu | SQLite | PostgreSQL |", "|---|---|---|",
        f"| Mở kho (giây) | {ket_a['giay_mo']} | {ket_b['giay_mo']} |",
        f"| Đề xuất lại (giây) | {ket_a['giay_de_xuat']} | {ket_b['giay_de_xuat']} |",
        f"| Mức (Xanh/Vàng/Đỏ) | {so['muc']['sqlite']} | {so['muc']['postgres']} |",
        f"| Chấm điểm so Junsky | {ket_a['diem']} | {ket_b['diem']} |", "",
        f"- Chấm điểm: {'giống nhau' if diem_giong else ('KHÁC NHAU' if diem_so_duoc else 'không so được (lỗi ở ít nhất một bên — thường do chưa khai file Sổ NKC đáp án)')}",
        "- Phạm vi: chỉ đề xuất lại sao kê của lần đề xuất mới nhất; hóa đơn, duyệt và xuất file chưa so.",
        f"- Dòng chung: **{so['dong_chung']}** · giống hoàn toàn 5 khóa chặt (mức, trạng thái, 5 trường, TTCP, dòng bút toán): **{so['giong_chat']}**",
        f"- Lệch khóa chặt theo trường: {so['lech_chat_theo_khoa'] or 'không'}",
        f"- Lệch khóa rộng (why, tùy chọn, ràng buộc…): {so['lech_rong_theo_khoa'] or 'không'}",
        f"- Chỉ có ở một bên: SQLite {so['chi_sqlite']} · PostgreSQL {so['chi_postgres']}",
        f"- **Tiêu chí giống từng dòng: {'ĐẠT' if dat else 'CHƯA ĐẠT'}** · thời gian ≤ 10 s: {'ĐẠT' if report['dat_tieu_chi_thoi_gian_10s'] else 'CHƯA ĐẠT'}", "",
        "_Báo cáo chỉ có số đếm; không chứa dòng giao dịch, số tài khoản hay tên đối tác._",
    ]
    (bao_cao_dir / "song-song-T8.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("so_dong", "thoi_gian_giay", "dat_tieu_chi_giong_tung_dong", "dat_tieu_chi_thoi_gian_10s")}, ensure_ascii=False))
    print(json.dumps({"so_sanh": so, "diem_giong": diem_giong}, ensure_ascii=False))
    return 0 if dat else 1


if __name__ == "__main__":
    raise SystemExit(main())
