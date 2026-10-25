"""Dọn CSDL test cũ `kho_test_*` và vai trò test `ktt_test_*`/`kho_test_*` trên cụm PostgreSQL DEMO (Anh chạy tay, có hộp xác nhận).

Anh chốt 25/10/2026 (sự cố PostgreSQL DEMO, `docs/46-chuyen-doi-dieu-phoi/SU-CO-POSTGRES-DEMO.md`): 323 CSDL test cũ làm mỗi lần
phục hồi sau khi bị cắt ngang mất 20–30 phút (fsync ~270 nghìn tệp). Chỉ xóa đúng tên khớp mẫu test; không đụng CSDL DEMO của Anh
(`kho_crm_demo*`), `postgres`, template, kho thật (SQLite, không ở cụm này). Không dùng FORCE: CSDL còn phiên kết nối thì bỏ qua.
Kết nối lấy từ `var/web/crm-demo/ket-noi.local.json` (đọc bằng chương trình, không in DSN/mật khẩu); chỉ nhận máy chủ loopback.

Dùng: `python tools/don_csdl_test_cu.py --xem-truoc` (chỉ liệt kê) · không cờ → hỏi xác nhận rồi xóa.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import re
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "tools"))
from tao_ket_noi_demo_rieng import nap_tep, thay_ten_csdl  # noqa: E402

MAU_CSDL = re.compile(r"^kho_test_[a-z0-9_]+$")
MAU_VAI = re.compile(r"^(ktt_test_|kho_test_)[a-z0-9_]+$")
TEP_KET_NOI = GOC / "var" / "web" / "crm-demo" / "ket-noi.local.json"
THU_MUC_BIEN_NHAN = GOC.parent / "var"


def ket_noi():
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    _, dsn = thay_ten_csdl(nap_tep(TEP_KET_NOI)["admin_dsn"], "postgres")
    host = conninfo_to_dict(dsn).get("host", "")
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("Từ chối: tệp kết nối không trỏ máy này (chỉ dọn cụm DEMO trên máy).")
    return psycopg.connect(dsn, autocommit=True, connect_timeout=15)


def liet_ke(c) -> tuple[list[str], list[str], list[str]]:
    rows = c.execute("SELECT d.datname, (SELECT count(*) FROM pg_stat_activity a WHERE a.datname = d.datname) "
                     "FROM pg_database d WHERE NOT d.datistemplate ORDER BY 1").fetchall()
    xoa = [n for n, k in rows if MAU_CSDL.match(n) and k == 0]
    ban = [n for n, k in rows if MAU_CSDL.match(n) and k > 0]
    vai = [r[0] for r in c.execute("SELECT rolname FROM pg_roles ORDER BY 1").fetchall() if MAU_VAI.match(r[0])]
    return xoa, ban, vai


def hoi(thong_diep: str) -> bool:
    if sys.platform == "win32":
        return ctypes.windll.user32.MessageBoxW(None, thong_diep, "Dọn CSDL test cũ — cụm PostgreSQL DEMO", 0x4 | 0x30) == 6
    return input(thong_diep + " [co/khong]: ").strip().lower() == "co"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--xem-truoc", action="store_true", help="chỉ liệt kê, không xóa")
    a = ap.parse_args()
    from psycopg import sql

    with ket_noi() as c:
        xoa, ban, vai = liet_ke(c)
        print(f"CSDL test sẽ xóa: {len(xoa)} · đang có kết nối (bỏ qua): {len(ban)} · vai trò test: {len(vai)}")
        if a.xem_truoc or not (xoa or vai):
            return 0
        if not hoi(f"Sẽ xóa vĩnh viễn {len(xoa)} CSDL test (tên kho_test_…) và thử xóa {len(vai)} vai trò test "
                   f"(ktt_test_… / kho_test_…) trên cụm PostgreSQL DEMO.\n\nKhông đụng CSDL DEMO của Anh, không đụng kho thật.\n"
                   f"{len(ban)} CSDL đang có kết nối sẽ được giữ lại.\n\nTiếp tục?"):
            print("Anh đã chọn Không — không xóa gì.")
            return 0
        kq = {"luc": datetime.datetime.now().isoformat(timespec="seconds"), "csdl_da_xoa": [], "csdl_loi": {},
              "csdl_giu_vi_dang_ket_noi": ban, "vai_da_xoa": [], "vai_loi": {}}
        for i, ten in enumerate(xoa, 1):
            try:
                c.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(ten)))
                kq["csdl_da_xoa"].append(ten)
            except Exception as e:  # noqa: BLE001 — ghi lại, đi tiếp
                kq["csdl_loi"][ten] = type(e).__name__
            if i % 25 == 0:
                print(f"  đã xử lý {i}/{len(xoa)} CSDL")
        for ten in vai:
            try:
                c.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(ten)))
                kq["vai_da_xoa"].append(ten)
            except Exception as e:  # noqa: BLE001 — vai còn sở hữu đối tượng thì giữ
                kq["vai_loi"][ten] = type(e).__name__
    tep = THU_MUC_BIEN_NHAN / f"pg-don-csdl-test-{datetime.datetime.now():%Y%m%d-%H%M%S}.json"
    tep.write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Xong: xóa {len(kq['csdl_da_xoa'])} CSDL ({len(kq['csdl_loi'])} lỗi), "
          f"xóa {len(kq['vai_da_xoa'])} vai trò ({len(kq['vai_loi'])} giữ lại). Biên nhận: {tep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
