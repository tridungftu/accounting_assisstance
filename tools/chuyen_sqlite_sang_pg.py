#!/usr/bin/env python3
"""Bộ chuyển kho.sqlite (V12) → PostgreSQL (schema V13, tài liệu 38 §6).

- Chạy trên BẢN SAO kho.sqlite; không ghi gì vào SQLite.
- Chạy lại được (idempotent): mọi bảng upsert theo khóa nguồn; mỗi bản ghi giữ _sqlite_id trong du_lieu/bang_chung.
- Báo cáo số đếm nguồn/đích từng bảng (JSON + bảng Markdown) để ghi docs/BAO-CAO-V13.md. Chỉ số đếm, không in dữ liệu.

Dùng:
  python tools/chuyen_sqlite_sang_pg.py --sqlite var/plhn-that/kho.sqlite --dsn "$KHO_PG_DSN" --bao-cao var/v13/chuyen-doi.json
  thêm --kiem-tra để chỉ đếm, không ghi.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kho_tri_thuc.ha_tang import postgres as pg  # noqa: E402
from kho_tri_thuc.ha_tang.ket_noi import loi_sach  # noqa: E402,F401 — biên lỗi dùng chung (V13 A4)
from kho_tri_thuc.ha_tang.primitives import canonical_json, normalize_text, sha256  # noqa: E402

TK_CONG_NO = ("131", "141", "1388", "331", "338", "341", "344")
TK_TIEN = ("111", "112", "113")
TRANG_THAI_QUICK = {"WAIT": "CHO_DUYET", "APPROVE": "DA_DUYET", "SKIP": "BO_QUA", "EXISTING": "DA_CO_JUNSKY", "EXPORTED": "DA_XUAT"}  # đúng CHECK của quick_items (review C3)
NHOM_TRI_THUC = {"CATALOG": "DANH_MUC", "POLICY": "MAU_LICH_SU", "KEYWORD": "TU_KHOA", "HARD_KEY": "KHOA_CUNG",
                 "INVOICE_TREE": "CAY_HOA_DON", "GROUP": "NHOM_G", "RULE": "QUY_TAC", "EXCEPTION": "NGOAI_LE"}


def j(s):
    return json.loads(s) if s else {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True, type=Path)
    ap.add_argument("--dsn", default=os.environ.get("KHO_PG_DSN"))
    ap.add_argument("--bao-cao", type=Path)
    ap.add_argument("--kiem-tra", action="store_true", help="chỉ đếm, không ghi")
    ap.add_argument("--cho-phep-du-dung-chung", action="store_true",
                    help="pháp nhân K2 dùng chung với module khác: chấp nhận đích NHIỀU hơn nguồn ở đối tác/dự án/tệp gốc khi MỌI bản ghi nguồn có mặt ở đích")
    args = ap.parse_args(argv)  # sai cú pháp: argparse tự thoát mã 2 (không phải thành công)
    # Biên runtime (V13 A4): mở nguồn, kết nối/migrate PG, chuyển, đóng kết nối, ghi báo cáo — mọi lỗi chỉ in bản đã làm sạch,
    # mã thoát 3, không traceback/DSN/giá trị dòng; báo cáo và stdout chỉ ghi SAU khi mọi bước (kể cả đóng kết nối) đã xong.
    try:
        ma, ket_qua = _chay(args)
        if ket_qua is not None:
            out = json.dumps(ket_qua, ensure_ascii=False, indent=2)
            if args.bao_cao:
                args.bao_cao.parent.mkdir(parents=True, exist_ok=True)
                args.bao_cao.write_text(out, encoding="utf-8")
                if "doi_chieu" in ket_qua:
                    args.bao_cao.with_suffix(".md").write_text(_bang_md(ket_qua), encoding="utf-8")
            print(out)
        return ma
    except Exception as exc:
        print(json.dumps(loi_sach(exc), ensure_ascii=False), file=sys.stderr)
        return 3


def _chay(args) -> tuple[int, dict | None]:
    src = sqlite3.connect(Path(args.sqlite).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        src.row_factory = sqlite3.Row
        nguon = {t: src.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in (
            "documents", "document_lines", "source_records", "artifacts", "knowledge_versions", "knowledge_events",
            "quick_items", "quick_runs", "activity_log", "audit_events", "issues", "quarantine_records", "cash_account_mappings")}
        nguon_kind = dict(src.execute("SELECT kind, count(*) FROM documents GROUP BY kind").fetchall())
        if args.kiem_tra:
            return 0, {"nguon": nguon, "documents_theo_kind": nguon_kind}
        ket_qua = {"nguon": nguon, "documents_theo_kind": nguon_kind, "dich": {}, "ghi_chu": [], "da_ghi": False}
        # Kiểm nguồn TRƯỚC mọi ghi: core_hash sai → từ chối, đích không bị chạm (review CRM M1-02 F2/G12)
        sai = van_tay_nguon(src)["core_hash_sai"]
        if sai:
            ket_qua.update(doi_chieu=[], doi_chieu_noi_dung={"core_hash_nguon": {"sai": sai, "khop": False}}, tu_choi="CORE_HASH_NGUON_TRUOC_GHI")
            return 1, ket_qua
        conn = pg.connect(args.dsn, autocommit=True)  # autocommit + conn.transaction() = BEGIN/COMMIT rõ ràng cho toàn bộ lần chuyển
        try:
            _chuyen(src, conn, ket_qua, nguon, nguon_kind, cho_phep_du_dung_chung=args.cho_phep_du_dung_chung)
            ket_qua["da_ghi"] = True
        except _HoanTac:
            ket_qua["tu_choi"] = "DOI_CHIEU_KHONG_DAT_DA_HOAN_TAC"  # cả giao dịch rollback: không ghi nửa chừng
        finally:
            conn.close()
    finally:
        src.close()  # Windows: không giữ khóa file kho.sqlite sau khi chạy
    return (0 if ket_qua["da_ghi"] else 1), ket_qua


class _HoanTac(Exception):
    """Đối chiếu sau ghi không đạt → thoát khỏi conn.transaction() để PostgreSQL rollback toàn bộ lần chuyển."""


DUNG_CHUNG = {"COUNTERPARTY → master.doi_tac_ma_junsky": "COUNTERPARTY", "PROJECT → master.du_an": "PROJECT", "artifacts → kho.tep_goc": "artifacts"}


def _dung_chung_tung_ban_ghi(src, cur, pn) -> dict:
    """Ba bảng pháp nhân K2 dùng chung với module khác: mỗi bản ghi nguồn phải có ở đích theo khóa ổn định (mã Junsky / hash tệp)."""
    def ma(kind):
        return {str(j(r[0]).get("code") or "") for r in src.execute("SELECT core_json FROM documents WHERE kind=?", (kind,))}
    out = {}
    for kind, sql in (("COUNTERPARTY", "SELECT object_id_junsky FROM master.doi_tac_ma_junsky WHERE phap_nhan_id=%s"),
                      ("PROJECT", "SELECT ma_junsky FROM master.du_an WHERE phap_nhan_id=%s"),
                      ("artifacts", "SELECT hash FROM kho.tep_goc WHERE phap_nhan_id=%s")):
        nguon = {r[0] for r in src.execute("SELECT hash FROM artifacts")} if kind == "artifacts" else ma(kind)
        cur.execute(sql, (pn,))
        dich = {r[0] for r in cur.fetchall()}
        out[kind] = {"nguon": len(nguon), "thieu": len(nguon - dich)}
    return out


def _chuyen(src, conn, ket_qua, nguon, nguon_kind, *, cho_phep_du_dung_chung=False):
    if True:
        with conn.transaction():
            cur = conn.cursor()
            # Mốc thời gian không ghi múi giờ trong kho.sqlite hiểu là UTC — xác định, không phụ thuộc múi giờ máy chủ; đối chiếu dùng cùng quy ước
            cur.execute("SET LOCAL TIME ZONE 'UTC'")
            # Chuyển dữ liệu lịch sử: tạm tắt hai trigger nghiệp vụ (chạy bằng chủ CSDL), bật lại cuối giao dịch
            cur.execute("ALTER TABLE kho.chung_tu DISABLE TRIGGER chung_tu_trang_thai")
            cur.execute("ALTER TABLE kho.de_xuat_dong DISABLE TRIGGER de_xuat_dong_khoa")
            pn = _phap_nhan(src, cur, ket_qua)
            ma_dt = _danh_muc(src, cur, pn, ket_qua)
            _doi_tac(src, cur, pn, ket_qua)
            tep = _tep_goc(src, cur, pn, ket_qua)
            _chung_tu(src, cur, pn, tep, ket_qua)
            _cong_no_mo(src, cur, pn, ket_qua)
            _de_xuat(src, cur, pn, ket_qua)
            _tri_thuc(src, cur, pn, ket_qua)
            _nhat_ky(src, cur, pn, ket_qua)
            _canh_bao(src, cur, pn, ket_qua)
            _tk_ngan_hang(src, cur, pn, ket_qua)
            cur.execute(
                "INSERT INTO nhat_ky.su_kien (phap_nhan_id, nguoi, loai, doi_tuong_bang, hanh_dong, sau) VALUES (%s,'BO_CHUYEN_V13','CHUYEN_DOI','kho.sqlite','CHUYEN_DOI',%s)",
                (pn, json.dumps({"nguon": nguon, "documents_theo_kind": nguon_kind}, ensure_ascii=False)),
            )
            cur.execute("ALTER TABLE kho.chung_tu ENABLE TRIGGER chung_tu_trang_thai")
            cur.execute("ALTER TABLE kho.de_xuat_dong ENABLE TRIGGER de_xuat_dong_khoa")
            ket_qua["dich"] = _dem_dich(cur, pn, src)
            ket_qua["doi_chieu_noi_dung"] = doi_chieu_noi_dung(van_tay_nguon(src), van_tay_dich(doc_dich(cur, pn)))
            # Quyết định đạt/không TRONG giao dịch: không đạt → rollback (không commit rồi mới báo lỗi)
            ket_qua["doi_chieu"] = _doi_chieu(ket_qua)
            if cho_phep_du_dung_chung:
                ket_qua["dung_chung"] = tung = _dung_chung_tung_ban_ghi(src, cur, pn)
                for r in ket_qua["doi_chieu"]:
                    kind = DUNG_CHUNG.get(r["bang"])
                    if kind and not r["khop"] and r["dich"] > r["nguon"] and tung[kind]["thieu"] == 0:
                        r["khop"], r["du_dung_chung"] = True, r["dich"] - r["nguon"]
            if not (all(r["khop"] for r in ket_qua["doi_chieu"]) and all(r["khop"] for r in ket_qua["doi_chieu_noi_dung"].values())):
                raise _HoanTac()


# ---------------------------------------------------------------- từng phần
def _phap_nhan(src, cur, kq):
    meta = dict(src.execute("SELECT key, value FROM workspace_meta").fetchall())
    ma = json.loads(meta.get("entity_id", '"PLHN"')) if meta.get("entity_id", "").startswith('"') else meta.get("entity_id", "PLHN")
    row = src.execute("SELECT core_json FROM documents WHERE kind='JOURNAL' LIMIT 1").fetchone()
    ma_dv = j(row["core_json"]).get("unit_code") if row else None
    cur.execute(
        """INSERT INTO master.phap_nhan (ma, ten, ma_don_vi_junsky) VALUES (%s, %s, %s)
           ON CONFLICT (ma) DO UPDATE SET ma_don_vi_junsky = COALESCE(master.phap_nhan.ma_don_vi_junsky, EXCLUDED.ma_don_vi_junsky)
           RETURNING id""",
        (ma, ma, ma_dv),
    )
    pn = cur.fetchone()[0]
    kq["phap_nhan"] = {"ma": ma, "ma_don_vi_junsky": ma_dv}
    return pn


def _danh_muc(src, cur, pn, kq):
    """ACCOUNT → tai_khoan · EXPENSE → khoan_muc_phi · COST_CENTER → ttcp (dùng chung: phap_nhan_id NULL) · PROJECT → du_an."""
    n = defaultdict(int)
    for row in src.execute("SELECT id, kind, core_json, business_date FROM documents WHERE kind IN ('ACCOUNT','EXPENSE','COST_CENTER','PROJECT')"):
        d = j(row["core_json"]); code = str(d.get("code") or ""); name = str(d.get("name") or code)
        vf = d.get("valid_from") or row["business_date"]
        if row["kind"] == "ACCOUNT":
            cur.execute(
                """INSERT INTO master.tai_khoan (phap_nhan_id, ma_junsky, ten, cap, tk_cong_no, tk_tien, valid_from)
                   VALUES (NULL, %s, %s, %s, %s, %s, %s) ON CONFLICT (phap_nhan_id, ma_junsky) DO UPDATE SET ten = EXCLUDED.ten""",
                (code, name, len(code), code.startswith(TK_CONG_NO), code.startswith(TK_TIEN), vf),
            )
        elif row["kind"] == "EXPENSE":
            cur.execute(
                "INSERT INTO master.khoan_muc_phi (phap_nhan_id, ma_junsky, ten, valid_from) VALUES (NULL, %s, %s, %s) ON CONFLICT (phap_nhan_id, ma_junsky) DO UPDATE SET ten = EXCLUDED.ten",
                (code, name, vf),
            )
        elif row["kind"] == "COST_CENTER":
            cur.execute(
                "INSERT INTO master.ttcp (phap_nhan_id, ma_junsky, ten, valid_from) VALUES (NULL, %s, %s, %s) ON CONFLICT (phap_nhan_id, ma_junsky) DO UPDATE SET ten = EXCLUDED.ten",
                (code, name, vf),
            )
        else:
            cur.execute(
                "INSERT INTO master.du_an (phap_nhan_id, ma_junsky, ten, valid_from) VALUES (%s, %s, %s, %s) ON CONFLICT (phap_nhan_id, ma_junsky) DO UPDATE SET ten = EXCLUDED.ten",
                (pn, code, name, vf),
            )
        n[row["kind"]] += 1
    kq["danh_muc"] = dict(n)
    return n


def _doi_tac(src, cur, pn, kq):
    """COUNTERPARTY → doi_tac (một bản ghi cho mỗi MST; mã không MST → một bản ghi riêng) + doi_tac_ma_junsky + dinh_danh MST."""
    rows = [j(r["core_json"]) | {"_sqlite_id": r["id"], "_bd": r["business_date"]} for r in src.execute("SELECT id, core_json, business_date FROM documents WHERE kind='COUNTERPARTY'")]
    theo_mst: dict[str, list] = defaultdict(list)
    le = []
    for d in rows:
        mst = (d.get("tax_id") or "").strip()
        (theo_mst[mst] if mst else le).append(d)
    so_doi_tac = 0; so_ma = 0; gop = 0
    def upsert_doi_tac(ten, mst, loai, vai_tro, ghi_chu):
        nonlocal so_doi_tac
        ten_ch = normalize_text(ten or "") or "(KHONG TEN)"
        if mst:
            cur.execute("SELECT id FROM master.doi_tac WHERE mst = %s", (mst,))
            r = cur.fetchone()
            if r:
                return r[0]
        else:
            cur.execute("SELECT id FROM master.doi_tac WHERE mst IS NULL AND ghi_chu = %s", (ghi_chu,))
            r = cur.fetchone()
            if r:
                return r[0]
        cur.execute(
            "INSERT INTO master.doi_tac (ten_phap_ly, ten_chuan_hoa, mst, loai, vai_tro, ghi_chu) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (ten or ten_ch, ten_ch, mst or None, loai, vai_tro, ghi_chu),
        )
        so_doi_tac += 1
        return cur.fetchone()[0]
    def loai_cua(code):
        p = code.split(".")[0] if "." in code else code
        return {"NV": ("CN", ["NV"]), "NH": ("NGAN_HANG", ["NH"]), "02": ("NOI_BO", ["NOI_BO"])}.get(p, ("TC", ["KH"] if p in ("DVA1", "DVB1") else (["NCC"] if p == "331" else [])))
    for mst, ds in list(theo_mst.items()) + [("", [d]) for d in le]:
        dau = ds[0]; code0 = str(dau.get("code") or "")
        loai, vai_tro = loai_cua(code0)
        for d in ds[1:]:
            for v in loai_cua(str(d.get("code") or ""))[1]:
                if v not in vai_tro:
                    vai_tro.append(v)
        dt = upsert_doi_tac(dau.get("name"), mst, loai, vai_tro, f"_sqlite_id:{dau['_sqlite_id']}")
        if len(ds) > 1:
            gop += len(ds) - 1
        for d in ds:
            code = str(d.get("code") or "")
            cur.execute(
                """INSERT INTO master.doi_tac_ma_junsky (doi_tac_id, phap_nhan_id, object_id_junsky, tien_to, ten_junsky, valid_from)
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (phap_nhan_id, object_id_junsky) DO UPDATE SET ten_junsky = EXCLUDED.ten_junsky""",
                (dt, pn, code, code.split(".")[0] if "." in code else code, d.get("name"), d.get("valid_from") or d["_bd"]),
            )
            so_ma += 1
        if mst:
            cur.execute(
                """INSERT INTO master.doi_tac_dinh_danh (doi_tac_id, loai, gia_tri, gia_tri_hash, nguon, do_tin_cay)
                   VALUES (%s,'MST',%s,%s,'junsky','CAO') ON CONFLICT DO NOTHING""",
                (dt, mst, sha256(mst.encode())),
            )
    kq["doi_tac"] = {"ma_junsky": so_ma, "doi_tac_moi": so_doi_tac, "ma_gop_theo_mst": gop}


def _tep_goc(src, cur, pn, kq):
    tep = {}
    for r in src.execute("SELECT hash, relative_path, byte_length, received_at FROM artifacts"):
        cur.execute(
            """INSERT INTO kho.tep_goc (phap_nhan_id, loai_nguon, duong_dan, hash, kich_thuoc, nhan_luc, nguon)
               VALUES (%s,'V12_ARTIFACT',%s,%s,%s,%s,'TAY') ON CONFLICT (hash) DO UPDATE SET duong_dan = EXCLUDED.duong_dan RETURNING id""",
            (pn, r["relative_path"], r["hash"], r["byte_length"], r["received_at"]),
        )
        tep[r["hash"]] = cur.fetchone()[0]
    kq["tep_goc"] = len(tep)
    return tep


def _chung_tu(src, cur, pn, tep, kq):
    """JOURNAL → SO_JUNSKY (DA_NAP) · BANK → SAO_KE (trạng thái theo quick_items) · dòng → chung_tu_dong."""
    raw_by_doc = {}
    for r in src.execute("SELECT d.id, s.raw_json, s.artifact_hash FROM documents d JOIN evidence e ON e.document_id = d.id JOIN source_records s ON s.id = e.source_record_id WHERE d.kind IN ('JOURNAL','BANK') ORDER BY d.id, e.id"):
        raw_by_doc.setdefault(r["id"], (r["raw_json"], r["artifact_hash"]))
    trang_thai_bank = {}
    for r in src.execute("SELECT document_id, state FROM quick_items ORDER BY rowid"):
        trang_thai_bank[r["document_id"]] = TRANG_THAI_QUICK.get(r["state"], "CHO_DUYET")
    cur.execute("SELECT object_id_junsky, doi_tac_id FROM master.doi_tac_ma_junsky WHERE phap_nhan_id = %s", (pn,))
    ma_dt = dict(cur.fetchall())
    cur.execute("SELECT ma_junsky, id FROM master.du_an WHERE phap_nhan_id = %s", (pn,))
    ma_da = dict(cur.fetchall())
    n = defaultdict(int); id_map = {}
    for r in src.execute("SELECT id, kind, natural_key, business_date, currency, amount_minor, core_json, core_hash FROM documents WHERE kind IN ('JOURNAL','BANK')"):
        d = j(r["core_json"]); raw, ahash = raw_by_doc.get(r["id"], (None, None))
        du_lieu = dict(d); du_lieu["_sqlite_id"] = r["id"]
        if raw:
            du_lieu["_raw"] = json.loads(raw)
        if r["kind"] == "JOURNAL":
            loai, tt = "SO_JUNSKY", "DA_NAP"
            doi_tac_tho = d.get("counterparty"); mo_ta = d.get("description"); vt = d.get("voucher_type"); so = d.get("voucher_number"); chieu = None
        else:
            loai, tt = "SAO_KE", trang_thai_bank.get(r["id"], "CHO_DUYET")
            doi_tac_tho = d.get("counterparty_name") or None; mo_ta = d.get("description"); vt = None; so = None
            chieu = "THU" if (r["amount_minor"] or 0) > 0 else "CHI"
        cur.execute(
            """INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, so_tien_minor, chieu, doi_tac_id, doi_tac_tho,
                   du_an_id, mo_ta, du_lieu, hash, tep_goc_id, ky, trang_thai, voucher_type, so_chung_tu_junsky)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (phap_nhan_id, loai, khoa_nguon) DO UPDATE SET du_lieu = EXCLUDED.du_lieu, hash = EXCLUDED.hash,
                   trang_thai = CASE WHEN kho.chung_tu.loai = 'SAO_KE' THEN EXCLUDED.trang_thai ELSE kho.chung_tu.trang_thai END
               RETURNING id""",
            (pn, loai, r["natural_key"], r["business_date"], r["currency"], abs(r["amount_minor"]) if r["amount_minor"] is not None else None,
             chieu, ma_dt.get(doi_tac_tho), doi_tac_tho, ma_da.get(d.get("project")), mo_ta, json.dumps(du_lieu, ensure_ascii=False),
             r["core_hash"], tep.get(ahash), (r["business_date"] or "")[:7], tt, vt, so),
        )
        id_map[r["id"]] = cur.fetchone()[0]; n[loai] += 1
    kq["chung_tu"] = dict(n)
    # dòng
    m = 0
    for r in src.execute("SELECT document_id, line_key, amount_minor, core_json FROM document_lines"):
        ct = id_map.get(r["document_id"])
        if ct is None:
            continue
        l = j(r["core_json"])
        try:
            stt = int(str(r["line_key"]))
        except ValueError:
            stt = m + 1
        cur.execute(
            """INSERT INTO kho.chung_tu_dong (chung_tu_id, stt, tai_khoan, no_minor, co_minor, du_lieu)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (chung_tu_id, stt) DO UPDATE SET tai_khoan = EXCLUDED.tai_khoan, no_minor = EXCLUDED.no_minor,
                   co_minor = EXCLUDED.co_minor, du_lieu = EXCLUDED.du_lieu""",
            (ct, stt, str(l.get("account") or ""), int(l.get("debit_minor") or 0), int(l.get("credit_minor") or 0), json.dumps(l | {"line_key": r["line_key"]}, ensure_ascii=False)),
        )
        m += 1
    kq["chung_tu_dong"] = m
    kq["_id_map"] = id_map
    return id_map


def _cong_no_mo(src, cur, pn, kq):
    cur.execute("SELECT object_id_junsky, doi_tac_id FROM master.doi_tac_ma_junsky WHERE phap_nhan_id = %s", (pn,))
    ma_dt = dict(cur.fetchall())
    cur.execute("SELECT ma_junsky, id FROM master.du_an WHERE phap_nhan_id = %s", (pn,))
    ma_da = dict(cur.fetchall())
    n = 0
    for r in src.execute("SELECT id, natural_key, business_date, currency, amount_minor, core_json FROM documents WHERE kind='OPEN_ITEM'"):
        d = j(r["core_json"])
        cur.execute(
            """INSERT INTO kho.cong_no_mo (phap_nhan_id, ngay_chup, tai_khoan, doi_tac_id, doi_tac_junsky, item_key, loai, so_tien_minor, con_lai_minor,
                   tien_te, hoa_don_ref, du_an_id, du_an_junsky, ngay_chung_tu, ngay_hoa_don, du_lieu)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (phap_nhan_id, ngay_chup, item_key) DO UPDATE SET so_tien_minor = EXCLUDED.so_tien_minor, du_lieu = EXCLUDED.du_lieu""",
            (pn, r["business_date"], str(d.get("account") or ""), ma_dt.get(d.get("counterparty")), d.get("counterparty"), r["natural_key"],
             d.get("item_type") if d.get("item_type") in ("UNBILLED", "INVOICE") else "KHAC", int(r["amount_minor"] or 0), int(r["amount_minor"] or 0),
             r["currency"] or "VND", d.get("transaction_code"), ma_da.get(d.get("project")), d.get("project"), d.get("document_date"), d.get("invoice_date"),
             json.dumps(d | {"_sqlite_id": r["id"]}, ensure_ascii=False)),
        )
        n += 1
    kq["cong_no_mo"] = n


def _de_xuat(src, cur, pn, kq):
    """quick_items → de_xuat + de_xuat_dong + viec_can_duyet (V1). Mức tạm theo completeness; bản V12 giữ nguyên trong can_cu."""
    id_map = kq.pop("_id_map", {})
    n = 0; dong = 0; viec = 0; bo_qua_da_xuat = 0; lech = 0; thieu_dt = 0
    cur.execute("SELECT ma_junsky FROM master.tai_khoan WHERE tk_cong_no AND valid_to IS NULL")
    tk_cong_no = {row[0] for row in cur.fetchall()}
    for r in src.execute("SELECT id, document_id, proposal_json, state, decision_json, reason, ai_note, decided_at, actor FROM quick_items"):
        ct = id_map.get(r["document_id"])
        if ct is None:
            continue
        cur.execute("SELECT c.trang_thai, (SELECT count(*) FROM kho.de_xuat x WHERE x.chung_tu_id = c.id) FROM kho.chung_tu c WHERE c.id = %s", (ct,))
        tt_ct, da_co = cur.fetchone()
        if tt_ct in ("DA_XUAT", "DA_NAP", "DA_DOI_CHIEU") and da_co > 0:
            bo_qua_da_xuat += 1  # review G3: chứng từ đã xuất lô và đã có đề xuất → không đụng (chạy lại)
            continue
        p = j(r["proposal_json"]); f = p.get("fields") or {}
        muc = {"NONE": "DO"}.get(p.get("completeness"), "VANG")
        can_cu = {"_v12_quick_item_id": r["id"], "_v12_proposal": p, "_v12_decision": j(r["decision_json"]) if r["decision_json"] else None,
                  "_v12_reason": r["reason"], "_v12_ai_note": r["ai_note"], "_v12_muc_tam": True}
        cur.execute(
            """INSERT INTO kho.de_xuat (chung_tu_id, phien_ban, hien_hanh, chu_trinh, muc, vi_sao, can_cu, nguon_suy_luan, tao_boi)
               VALUES (%s,1,true,'M1',%s,%s,%s,'LICH_SU','BO_CHUYEN_V13')
               ON CONFLICT (chung_tu_id, phien_ban) DO UPDATE SET can_cu = EXCLUDED.can_cu, muc = EXCLUDED.muc RETURNING id""",
            (ct, muc, p.get("why") if isinstance(p.get("why"), str) else None, json.dumps(can_cu, ensure_ascii=False)),
        )
        dx = cur.fetchone()[0]; n += 1
        amt = abs(int(p.get("amount_minor") or 0))
        lines = p.get("lines") or []
        if lines:
            muon = []
            for i, l in enumerate(lines, 1):
                dims = l.get("dimensions") or {}
                deb = abs(int(l.get("debit_minor") or 0)); crd = abs(int(l.get("credit_minor") or 0))
                muon.append((i, "N" if deb > 0 else "C", str(l.get("account") or ""), deb, crd, dims.get("counterparty"), dims.get("project"), dims.get("expense"), dims.get("cost_center")))
        else:
            cash = (p.get("cash_leg") or {}).get("account")
            muon = [(i, side, str(acct), amt if side == "N" else 0, amt if side == "C" else 0, f.get("counterparty") if acct != cash else None, f.get("project"), f.get("expense"), None)
                    for i, (acct, side) in enumerate(((f.get("debit_account"), "N"), (f.get("credit_account"), "C")), 1) if acct]
        cur.execute("""SELECT "offset", no_co, acct_id, base_deb, base_crd, object_id_junsky, project_id, cost_id, center_id FROM kho.de_xuat_dong
                       WHERE de_xuat_id = %s ORDER BY "offset\"""", (dx,))
        if [tuple(r) for r in cur.fetchall()] != muon:  # chạy lại cùng nội dung: giữ nguyên dòng (và ID) đã có, không xóa-tạo lại
            cur.execute("DELETE FROM kho.de_xuat_dong WHERE de_xuat_id = %s", (dx,))
            for row in muon:
                cur.execute(
                    """INSERT INTO kho.de_xuat_dong (de_xuat_id, "offset", no_co, acct_id, base_deb, base_crd, object_id_junsky, project_id, cost_id, center_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (dx, *row))
        dong += len(muon)
        cur.execute("SELECT coalesce(sum(base_deb),0), coalesce(sum(base_crd),0), count(*) FILTER (WHERE acct_id = ANY(%s) AND (object_id_junsky IS NULL OR object_id_junsky = '')) FROM kho.de_xuat_dong WHERE de_xuat_id = %s", (list(tk_cong_no), dx))
        sno, sco, sthieu = cur.fetchone()
        if sno != sco or sno == 0:
            lech += 1
        thieu_dt += int(sthieu)
        tt = TRANG_THAI_QUICK.get(r["state"], "CHO_DUYET")
        if tt != "CHO_DUYET":
            # đồng bộ hằng đêm: dòng đã được quyết ở V12 → đóng việc còn mở (V13 kho.* chỉ phản chiếu V12)
            cur.execute(
                "UPDATE kho.viec_can_duyet SET trang_thai = %s, cap_nhat_luc = now() WHERE tham_chieu_bang = 'kho.de_xuat' AND tham_chieu_id = %s AND trang_thai = 'CHO_DUYET'",
                ({"DA_DUYET": "DA_DUYET", "BO_QUA": "BO_QUA"}.get(tt, "DONG"), dx),
            )
            kq.setdefault("_viec_dong", 0)
            kq["_viec_dong"] += cur.rowcount
        if tt in ("CHO_DUYET",):
            cur.execute(
                """INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, tham_chieu_bang, tham_chieu_id, muc, trang_thai, tom_tat, so_tien_minor, tien_te)
                   SELECT %s,'V1','M1','kho.de_xuat',%s,%s,'CHO_DUYET', c.mo_ta, c.so_tien_minor, c.tien_te FROM kho.chung_tu c WHERE c.id = %s
                   ON CONFLICT DO NOTHING""",
                (pn, dx, muc, ct),
            )
            viec += 1
    kq["de_xuat"] = {"de_xuat": n, "de_xuat_dong": dong, "viec_can_duyet": viec, "viec_dong_khi_dong_bo": kq.pop("_viec_dong", 0), "bo_qua_vi_da_xuat": bo_qua_da_xuat,
                     "de_xuat_lech_no_co": lech, "dong_tk_cong_no_thieu_doi_tuong": thieu_dt,
                     "muc_tam": "VANG/DO theo completeness — lõi tính lại ở bước 5 (review N3)"}


def _tri_thuc(src, cur, pn, kq):
    n = 0
    events = defaultdict(list)
    for e in src.execute("SELECT version_id, action, event_at, actor, reason FROM knowledge_events"):
        events[e["version_id"]].append(dict(e))
    id_map = {}
    rows = src.execute("SELECT id, category, logical_key, revision, payload_json, content_hash, valid_from, valid_to, known_at, evidence_json, supersedes_id, created_at, actor FROM knowledge_versions ORDER BY created_at, revision").fetchall()
    for r in rows:
        ev = sorted(events.get(r["id"], []), key=lambda e: (e["event_at"] or ""))
        cuoi = ev[-1]["action"] if ev else None
        trang_thai = {"APPROVE": "DA_DUYET", "REVOKE": "THU_HOI", "REJECT": "THU_HOI"}.get(cuoi, "CHO_DUYET")  # sự kiện cuối quyết định (review N5)
        bang_chung = {"_sqlite_id": r["id"], "evidence": j(r["evidence_json"]) if r["evidence_json"] else None, "events": ev}
        cur.execute(
            """INSERT INTO kho.tri_thuc (phap_nhan_id, nhom, khoa_logic, phien_ban, noi_dung, bang_chung, trang_thai, actor, valid_from, valid_to, known_at, content_hash, tao_luc)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (phap_nhan_id, nhom, khoa_logic, phien_ban) DO UPDATE SET noi_dung = EXCLUDED.noi_dung, bang_chung = EXCLUDED.bang_chung, trang_thai = EXCLUDED.trang_thai
               RETURNING id""",
            (pn, NHOM_TRI_THUC.get(r["category"], r["category"]), r["logical_key"], int(r["revision"]), r["payload_json"], json.dumps(bang_chung, ensure_ascii=False),
             trang_thai, r["actor"] or "HE_THONG", r["valid_from"], r["valid_to"], r["known_at"], r["content_hash"], r["created_at"]),
        )
        id_map[r["id"]] = cur.fetchone()[0]; n += 1
    for r in rows:
        if r["supersedes_id"] and r["supersedes_id"] in id_map:
            cur.execute("UPDATE kho.tri_thuc SET supersedes_id = %s WHERE id = %s", (id_map[r["supersedes_id"]], id_map[r["id"]]))
    kq["tri_thuc"] = n


def _nhat_ky(src, cur, pn, kq):
    """activity_log + audit_events → nhat_ky.su_kien, **tăng dần**: chỉ thêm dòng có id SQLite lớn hơn lần trước (theo pháp nhân).
    Chạy lại hằng đêm không trùng; dòng do móc ghi trực tiếp của engine postgres (không có _sqlite_id) không bị đếm lẫn."""
    def _max_id(bang_dieu_kien):
        cur.execute(
            f"SELECT coalesce(max((sau->>'_sqlite_id')::bigint), 0) FROM nhat_ky.su_kien WHERE phap_nhan_id = %s AND sau ? '_sqlite_id' AND {bang_dieu_kien}",
            (pn,),
        )
        return cur.fetchone()[0]
    tu_log, tu_audit = _max_id("doi_tuong_bang <> 'v12.audit'"), _max_id("doi_tuong_bang = 'v12.audit'")
    n = 0
    for r in src.execute("SELECT id, module, action, subject_id, actor, event_at, recorded_at, details_json FROM activity_log WHERE id > ? ORDER BY id", (tu_log,)):
        loai = "TRI_THUC" if r["module"] == "M2" and r["action"] in ("APPROVE", "IMPORT_KNOWLEDGE_PENDING") else ("GHI_CHU_AI" if r["action"] == "AI_NOTE" else "HE_THONG")
        cur.execute(
            "INSERT INTO nhat_ky.su_kien (phap_nhan_id, luc, nguoi, loai, doi_tuong_bang, hanh_dong, sau) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (pn, r["event_at"], r["actor"] or "HE_THONG", loai, f"v12.{r['module']}", r["action"], json.dumps({"subject_id": r["subject_id"], "details": j(r["details_json"]), "_sqlite_id": r["id"], "recorded_at": r["recorded_at"]}, ensure_ascii=False)),
        )
        n += 1
    for r in src.execute("SELECT id, at, action, attempt_id, details_json FROM audit_events WHERE id > ? ORDER BY id", (tu_audit,)):
        cur.execute(
            "INSERT INTO nhat_ky.su_kien (phap_nhan_id, luc, nguoi, loai, doi_tuong_bang, hanh_dong, sau) VALUES (%s,%s,'HE_THONG','HE_THONG','v12.audit',%s,%s)",
            (pn, r["at"], r["action"], json.dumps({"attempt_id": r["attempt_id"], "details": j(r["details_json"]), "_sqlite_id": r["id"]}, ensure_ascii=False)),
        )
        n += 1
    kq["nhat_ky"] = {"su_kien_them": n}


def _canh_bao(src, cur, pn, kq):
    n = 0
    for r in src.execute("SELECT id, locator, code, severity, message FROM issues"):
        cur.execute(
            "INSERT INTO kho.canh_bao (phap_nhan_id, ma, muc, thong_diep, viec_can_lam, trang_thai) SELECT %s,%s,%s,%s,%s,'MO' WHERE NOT EXISTS (SELECT 1 FROM kho.canh_bao WHERE ma=%s AND thong_diep=%s AND viec_can_lam IS NOT DISTINCT FROM %s)",
            (pn, r["code"], "CHAN" if r["severity"] == "ERROR" else "CANH_BAO", r["message"], f"v12:{r['id']}:{r['locator']}", r["code"], r["message"], f"v12:{r['id']}:{r['locator']}"),
        )
        n += 1
    for r in src.execute("SELECT code, message FROM quarantine_records"):
        cur.execute(
            "INSERT INTO kho.canh_bao (phap_nhan_id, ma, muc, thong_diep, viec_can_lam, trang_thai) SELECT %s,%s,'CHAN',%s,'v12:quarantine','MO' WHERE NOT EXISTS (SELECT 1 FROM kho.canh_bao WHERE ma=%s AND thong_diep=%s AND viec_can_lam='v12:quarantine')",
            (pn, r["code"], r["message"], r["code"], r["message"]),
        )
        n += 1
    kq["canh_bao"] = n


def _tk_ngan_hang(src, cur, pn, kq):
    n = 0
    for r in src.execute("SELECT bank_account, cash_account, source FROM cash_account_mappings"):
        stk = str(r["bank_account"] or "")
        cur.execute(
            """INSERT INTO master.tai_khoan_ngan_hang (phap_nhan_id, ngan_hang, stk_hash, tk_ke_toan, co_sao_ke, nguon_sao_ke)
               VALUES (%s,'(chưa ghi)',%s,%s,true,%s) ON CONFLICT (phap_nhan_id, tk_ke_toan) DO UPDATE SET stk_hash = EXCLUDED.stk_hash""",
            (pn, sha256(stk.encode()), r["cash_account"], r["source"]),
        )
        n += 1
    kq["tai_khoan_ngan_hang"] = n
    kq["ghi_chu"].append("STK ngân hàng chỉ lưu hash (chưa có khóa mã hóa trong .env); điền stk_mh khi cấu hình KHO_MA_HOA_KHOA.")


def _dem_dich(cur, pn, src):
    """Đếm ở đích theo đúng pháp nhân vừa chuyển (và theo mã nguồn với danh mục dùng chung) — để chạy được trên CSDL đã có dữ liệu khác."""
    def ma_nguon(kind):
        return [str(j(r[0]).get("code") or "") for r in src.execute("SELECT core_json FROM documents WHERE kind=?", (kind,))]
    dich = {}
    cur.execute("SELECT count(*) FROM master.phap_nhan WHERE id=%s", (pn,)); dich["master.phap_nhan"] = cur.fetchone()[0]
    for t, kind in (("master.tai_khoan", "ACCOUNT"), ("master.khoan_muc_phi", "EXPENSE"), ("master.ttcp", "COST_CENTER")):
        cur.execute(f"SELECT count(*) FROM {t} WHERE phap_nhan_id IS NULL AND ma_junsky = ANY(%s)", (ma_nguon(kind),)); dich[t] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM master.du_an WHERE phap_nhan_id=%s", (pn,)); dich["master.du_an"] = cur.fetchone()[0]
    cur.execute("SELECT count(DISTINCT doi_tac_id) FROM master.doi_tac_ma_junsky WHERE phap_nhan_id=%s", (pn,)); dich["master.doi_tac"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM master.doi_tac_ma_junsky WHERE phap_nhan_id=%s", (pn,)); dich["master.doi_tac_ma_junsky"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM master.doi_tac_dinh_danh d WHERE d.loai='MST' AND d.doi_tac_id IN (SELECT doi_tac_id FROM master.doi_tac_ma_junsky WHERE phap_nhan_id=%s)", (pn,)); dich["master.doi_tac_dinh_danh"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM master.tai_khoan_ngan_hang WHERE phap_nhan_id=%s", (pn,)); dich["master.tai_khoan_ngan_hang"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.tep_goc WHERE phap_nhan_id=%s", (pn,)); dich["kho.tep_goc"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.chung_tu WHERE phap_nhan_id=%s AND du_lieu ? '_sqlite_id'", (pn,)); dich["kho.chung_tu"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.chung_tu_dong d JOIN kho.chung_tu c ON c.id=d.chung_tu_id WHERE c.phap_nhan_id=%s AND c.du_lieu ? '_sqlite_id'", (pn,)); dich["kho.chung_tu_dong"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.cong_no_mo WHERE phap_nhan_id=%s", (pn,)); dich["kho.cong_no_mo"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.de_xuat x JOIN kho.chung_tu c ON c.id=x.chung_tu_id WHERE c.phap_nhan_id=%s AND x.can_cu ? '_v12_quick_item_id'", (pn,)); dich["kho.de_xuat"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.de_xuat_dong d JOIN kho.de_xuat x ON x.id=d.de_xuat_id JOIN kho.chung_tu c ON c.id=x.chung_tu_id WHERE c.phap_nhan_id=%s AND x.can_cu ? '_v12_quick_item_id'", (pn,)); dich["kho.de_xuat_dong"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.viec_can_duyet WHERE phap_nhan_id=%s AND tham_chieu_bang='kho.de_xuat'", (pn,)); dich["kho.viec_can_duyet"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.tri_thuc WHERE phap_nhan_id=%s AND bang_chung ? '_sqlite_id'", (pn,)); dich["kho.tri_thuc"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM kho.canh_bao WHERE phap_nhan_id=%s AND viec_can_lam LIKE 'v12:%%'", (pn,)); dich["kho.canh_bao"] = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM nhat_ky.su_kien WHERE phap_nhan_id=%s AND doi_tuong_bang LIKE 'v12.%%' AND sau ? '_sqlite_id'", (pn,)); dich["nhat_ky.su_kien"] = cur.fetchone()[0]
    cur.execute("SELECT loai, count(*) FROM kho.chung_tu WHERE phap_nhan_id=%s AND du_lieu ? '_sqlite_id' GROUP BY loai", (pn,))
    dich["kho.chung_tu theo loai"] = dict(cur.fetchall())
    cur.execute("SELECT count(*) FROM nhat_ky.su_kien WHERE phap_nhan_id=%s AND loai = 'CHUYEN_DOI'", (pn,))
    dich["so_lan_chuyen_doi"] = cur.fetchone()[0]
    return dich


# ---------------------------------------------------------------- đối chiếu nội dung (V13 A5)
# Không tin cột hash/JSON đã chép: với mỗi bản ghi, dựng lại TỪ NGUỒN mọi cột nghiệp vụ mà bộ chuyển ánh xạ (cột typed, JSON,
# khóa ngoại quy về khóa ổn định: đối tác → MST/_sqlite_id, dự án → mã Junsky, tệp gốc → hash, tri thức thay thế → _sqlite_id),
# dựng cùng bộ trường từ ĐÍCH, rồi so vân tay từng bản ghi theo khóa nguồn. Cột bộ chuyển không ghi phải còn NULL.
# Chỉ trả số đếm (thiếu/thừa/trùng/lệch), không in khóa hay giá trị.
KHOA_THEM_CHUNG_TU = ("_sqlite_id", "_raw")
COT_DONG_KHONG_ANH_XA = ("mo_ta", "so_luong", "don_gia_minor", "tien_truoc_thue_minor", "thue_suat", "tien_thue_minor", "doi_tac_id",
                         "doi_tac_junsky", "du_an_id", "du_an_junsky", "ttcp", "khoan_muc", "dich")


def _bam(obj) -> str:
    return sha256(canonical_json(obj).encode())


def _json(v):
    return json.loads(v) if isinstance(v, (str, bytes)) else v


def _chu(v):
    return None if v is None else str(v)


def _tien_te(v):
    return None if v is None else str(v).rstrip()  # char(3) của PostgreSQL đệm khoảng trắng


def _ngay(v):
    if v is None:
        return None
    return v.isoformat()[:10] if isinstance(v, (date, datetime)) else str(v)[:10]


def _thoi_diem(v):
    """Thời điểm quy về UTC; chuỗi không ghi múi giờ hiểu là UTC (cùng quy ước SET LOCAL TIME ZONE 'UTC' khi chuyển)."""
    if v is None:
        return None
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, date):
        dt = datetime(v.year, v.month, v.day)
    else:
        s = str(v).strip()
        try:
            dt = datetime.fromisoformat(s[:-1] + "+00:00" if s.endswith("Z") else s)
        except ValueError:
            return "?" + s  # không đọc được: giữ nguyên để báo lệch, không đoán
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _stt(line_key):
    try:
        return int(str(line_key))
    except ValueError:
        return "*"  # bộ chuyển đánh số dự phòng theo thứ tự — chỉ yêu cầu có dòng, không so số


def _khoa_doi_tac_dich(x):
    if not x["co_doi_tac"]:
        return None
    return "MST:" + x["dt_mst"] if x["dt_mst"] else "GC:" + (x["dt_ghi_chu"] or "")


def _vt_chung_tu(core, raw, x):
    return _bam({"core": _bam(core), "raw": None if raw is None else _bam(raw), **x})


def _vt_dong(core, x):
    return _bam({"core": _bam(core), **x})


def van_tay_nguon(src) -> dict:
    """{bảng đích: {khóa nguồn: vân tay}} dựng độc lập từ kho.sqlite (src.row_factory = sqlite3.Row).
    ``core_hash_sai``: số chứng từ nguồn mà core_hash ≠ hash tái tính."""
    out = {"kho.chung_tu": {}, "kho.chung_tu_dong": {}, "kho.cong_no_mo": {}, "kho.tri_thuc": {}}
    # khóa ổn định của đối tác theo đúng quy tắc gộp: có MST → một bản ghi theo MST; không MST → bản ghi riêng theo _sqlite_id
    ma_doi_tac = {}
    for r in src.execute("SELECT id, core_json FROM documents WHERE kind='COUNTERPARTY'"):
        d = j(r["core_json"]); mst = (d.get("tax_id") or "").strip()
        ma_doi_tac[str(d.get("code") or "")] = "MST:" + mst if mst else f"GC:_sqlite_id:{r['id']}"
    ma_du_an = {str(j(r[0]).get("code") or "") for r in src.execute("SELECT core_json FROM documents WHERE kind='PROJECT'")}

    def doi_tac(code):
        return ma_doi_tac.get(code) if isinstance(code, str) else None

    def du_an(code):
        return code if isinstance(code, str) and code in ma_du_an else None
    raw_by_doc = {}
    for r in src.execute("SELECT d.id, s.raw_json, s.artifact_hash FROM documents d JOIN evidence e ON e.document_id = d.id JOIN source_records s ON s.id = e.source_record_id WHERE d.kind IN ('JOURNAL','BANK') ORDER BY d.id, e.id"):
        raw_by_doc.setdefault(r[0], (r[1], r[2]))
    trang_thai_bank = {r[0]: TRANG_THAI_QUICK.get(r[1], "CHO_DUYET") for r in src.execute("SELECT document_id, state FROM quick_items ORDER BY rowid")}
    sai = 0
    for r in src.execute("SELECT id, kind, natural_key, business_date, currency, amount_minor, core_json, core_hash FROM documents WHERE kind IN ('JOURNAL','BANK','OPEN_ITEM')"):
        core = j(r["core_json"]); amt = r["amount_minor"]; bd = r["business_date"]
        sai += _bam(core) != r["core_hash"]
        if r["kind"] == "OPEN_ITEM":
            out["kho.cong_no_mo"][str(r["id"])] = _bam({
                "core": _bam(core), "ngay_chup": _ngay(bd), "tai_khoan": str(core.get("account") or ""), "doi_tac": doi_tac(core.get("counterparty")),
                "doi_tac_junsky": _chu(core.get("counterparty")), "item_key": _chu(r["natural_key"]),
                "loai": core.get("item_type") if core.get("item_type") in ("UNBILLED", "INVOICE") else "KHAC",
                "so_tien": int(amt or 0), "con_lai": int(amt or 0), "tien_te": _tien_te(r["currency"] or "VND"),
                "hoa_don_ref": _chu(core.get("transaction_code")), "du_an": du_an(core.get("project")), "du_an_junsky": _chu(core.get("project")),
                "ngay_chung_tu": _ngay(core.get("document_date")), "ngay_hoa_don": _ngay(core.get("invoice_date"))})
            continue
        journal = r["kind"] == "JOURNAL"
        raw, ahash = raw_by_doc.get(r["id"], (None, None))
        tho = core.get("counterparty") if journal else (core.get("counterparty_name") or None)
        out["kho.chung_tu"][str(r["id"])] = _vt_chung_tu(core, json.loads(raw) if raw else None, {
            "hash": r["core_hash"], "loai": "SO_JUNSKY" if journal else "SAO_KE", "khoa_nguon": _chu(r["natural_key"]), "ngay": _ngay(bd),
            "tien_te": _tien_te(r["currency"]), "so_tien": abs(amt) if amt is not None else None,
            "chieu": None if journal else ("THU" if (amt or 0) > 0 else "CHI"), "doi_tac": doi_tac(tho), "doi_tac_tho": _chu(tho),
            "du_an": du_an(core.get("project")), "mo_ta": _chu(core.get("description")), "tep_goc": ahash, "ky": (bd or "")[:7],
            "trang_thai": "DA_NAP" if journal else trang_thai_bank.get(r["id"], "CHO_DUYET"),
            "voucher_type": _chu(core.get("voucher_type")) if journal else None, "so_chung_tu_junsky": _chu(core.get("voucher_number")) if journal else None})
    for r in src.execute("SELECT l.document_id, l.line_key, l.core_json FROM document_lines l JOIN documents d ON d.id = l.document_id WHERE d.kind IN ('JOURNAL','BANK')"):
        l = j(r["core_json"])
        out["kho.chung_tu_dong"][(str(r["document_id"]), r["line_key"])] = _vt_dong(l | {"line_key": r["line_key"]}, {
            "stt": _stt(r["line_key"]), "tai_khoan": str(l.get("account") or ""), "no": int(l.get("debit_minor") or 0),
            "co": int(l.get("credit_minor") or 0), "khong_anh_xa": [None] * len(COT_DONG_KHONG_ANH_XA)})
    events = defaultdict(list)
    for e in src.execute("SELECT version_id, action, event_at, actor, reason FROM knowledge_events"):
        events[e["version_id"]].append(dict(e))
    versions = src.execute("SELECT id, category, logical_key, revision, payload_json, content_hash, valid_from, valid_to, known_at, evidence_json, supersedes_id, created_at, actor FROM knowledge_versions").fetchall()
    ids = {r["id"] for r in versions}
    for r in versions:
        ev = sorted(events.get(r["id"], []), key=lambda e: (e["event_at"] or ""))
        cuoi = ev[-1]["action"] if ev else None
        bang_chung = {"_sqlite_id": r["id"], "evidence": j(r["evidence_json"]) if r["evidence_json"] else None, "events": ev}
        out["kho.tri_thuc"][str(r["id"])] = _bam({
            "noi_dung": _bam(_json(r["payload_json"])), "bang_chung": _bam(bang_chung), "nhom": NHOM_TRI_THUC.get(r["category"], r["category"]),
            "khoa_logic": _chu(r["logical_key"]), "phien_ban": int(r["revision"]),
            "trang_thai": {"APPROVE": "DA_DUYET", "REVOKE": "THU_HOI", "REJECT": "THU_HOI"}.get(cuoi, "CHO_DUYET"),
            "actor": _chu(r["actor"] or "HE_THONG"), "valid_from": _thoi_diem(r["valid_from"]), "valid_to": _thoi_diem(r["valid_to"]),
            "known_at": _thoi_diem(r["known_at"]), "content_hash": _chu(r["content_hash"]), "tao_luc": _thoi_diem(r["created_at"]),
            "supersedes": _chu(r["supersedes_id"]) if r["supersedes_id"] in ids else None})
    out["core_hash_sai"] = sai
    return out


def doc_dich(cur, pn) -> dict:
    """Dòng đích (chỉ bản ghi có khóa nguồn _sqlite_id của pháp nhân) dạng dict, kèm khóa ổn định của khóa ngoại — đầu vào van_tay_dich."""
    def q(sql):
        cur.execute(sql, (pn,))
        names = [d.name for d in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]
    doi_tac = "dt.id IS NOT NULL AS co_doi_tac, dt.mst AS dt_mst, dt.ghi_chu AS dt_ghi_chu, da.ma_junsky AS du_an_ma"
    return {
        "kho.chung_tu": q(
            f"SELECT c.du_lieu, c.hash, c.loai, c.khoa_nguon, c.ngay_nghiep_vu, c.tien_te, c.so_tien_minor, c.chieu, c.doi_tac_tho, c.mo_ta, c.ky, "
            f"c.trang_thai, c.voucher_type, c.so_chung_tu_junsky, tg.hash AS tep_goc_hash, {doi_tac} FROM kho.chung_tu c "
            "LEFT JOIN master.doi_tac dt ON dt.id = c.doi_tac_id LEFT JOIN master.du_an da ON da.id = c.du_an_id LEFT JOIN kho.tep_goc tg ON tg.id = c.tep_goc_id "
            "WHERE c.phap_nhan_id=%s AND c.du_lieu ? '_sqlite_id'"),
        "kho.chung_tu_dong": q(
            "SELECT c.du_lieu->>'_sqlite_id' AS sid, d.stt, d.du_lieu, d.tai_khoan, d.no_minor, d.co_minor, "
            + ", ".join(f"d.{c}" for c in COT_DONG_KHONG_ANH_XA)
            + " FROM kho.chung_tu_dong d JOIN kho.chung_tu c ON c.id = d.chung_tu_id WHERE c.phap_nhan_id=%s AND c.du_lieu ? '_sqlite_id'"),
        "kho.cong_no_mo": q(
            f"SELECT n.du_lieu, n.ngay_chup, n.tai_khoan, n.doi_tac_junsky, n.item_key, n.loai, n.so_tien_minor, n.con_lai_minor, n.tien_te, n.hoa_don_ref, "
            f"n.du_an_junsky, n.ngay_chung_tu, n.ngay_hoa_don, {doi_tac} FROM kho.cong_no_mo n "
            "LEFT JOIN master.doi_tac dt ON dt.id = n.doi_tac_id LEFT JOIN master.du_an da ON da.id = n.du_an_id "
            "WHERE n.phap_nhan_id=%s AND n.du_lieu ? '_sqlite_id'"),
        "kho.tri_thuc": q(
            "SELECT t.bang_chung, t.noi_dung, t.nhom, t.khoa_logic, t.phien_ban, t.trang_thai, t.actor, t.valid_from, t.valid_to, t.known_at, "
            "t.content_hash, t.tao_luc, s.bang_chung->>'_sqlite_id' AS supersedes_sid FROM kho.tri_thuc t LEFT JOIN kho.tri_thuc s ON s.id = t.supersedes_id "
            "WHERE t.phap_nhan_id=%s AND t.bang_chung ? '_sqlite_id'"),
    }


def van_tay_dich(rows: dict) -> dict:
    """Tái tính vân tay từ dòng đích (dict theo tên cột của doc_dich), cùng bộ trường với van_tay_nguon. Khóa trùng → ``_trung``."""
    out = {t: {} for t in rows}
    trung = defaultdict(int)

    def them(t, k, v):
        if k in out[t]:
            trung[t] += 1
        out[t][k] = v
    for x in rows["kho.chung_tu"]:
        d = _json(x["du_lieu"])
        core = {k: v for k, v in d.items() if k not in KHOA_THEM_CHUNG_TU}
        them("kho.chung_tu", str(d["_sqlite_id"]), _vt_chung_tu(core, d.get("_raw"), {
            "hash": x["hash"], "loai": x["loai"], "khoa_nguon": _chu(x["khoa_nguon"]), "ngay": _ngay(x["ngay_nghiep_vu"]),
            "tien_te": _tien_te(x["tien_te"]), "so_tien": None if x["so_tien_minor"] is None else int(x["so_tien_minor"]), "chieu": x["chieu"],
            "doi_tac": _khoa_doi_tac_dich(x), "doi_tac_tho": _chu(x["doi_tac_tho"]), "du_an": x["du_an_ma"], "mo_ta": _chu(x["mo_ta"]),
            "tep_goc": x["tep_goc_hash"], "ky": x["ky"], "trang_thai": x["trang_thai"], "voucher_type": _chu(x["voucher_type"]),
            "so_chung_tu_junsky": _chu(x["so_chung_tu_junsky"])}))
    for x in rows["kho.chung_tu_dong"]:
        d = _json(x["du_lieu"]); stt = _stt(d.get("line_key"))
        them("kho.chung_tu_dong", (_chu(x["sid"]), d.get("line_key")), _vt_dong(d, {
            "stt": "*" if stt == "*" else int(x["stt"]), "tai_khoan": str(x["tai_khoan"] or ""), "no": int(x["no_minor"] or 0),
            "co": int(x["co_minor"] or 0), "khong_anh_xa": [_chu(x[c]) for c in COT_DONG_KHONG_ANH_XA]}))
    for x in rows["kho.cong_no_mo"]:
        d = _json(x["du_lieu"])
        them("kho.cong_no_mo", str(d["_sqlite_id"]), _bam({
            "core": _bam({k: v for k, v in d.items() if k != "_sqlite_id"}), "ngay_chup": _ngay(x["ngay_chup"]), "tai_khoan": _chu(x["tai_khoan"]),
            "doi_tac": _khoa_doi_tac_dich(x), "doi_tac_junsky": _chu(x["doi_tac_junsky"]), "item_key": _chu(x["item_key"]), "loai": x["loai"],
            "so_tien": int(x["so_tien_minor"]), "con_lai": None if x["con_lai_minor"] is None else int(x["con_lai_minor"]),
            "tien_te": _tien_te(x["tien_te"]), "hoa_don_ref": _chu(x["hoa_don_ref"]), "du_an": x["du_an_ma"], "du_an_junsky": _chu(x["du_an_junsky"]),
            "ngay_chung_tu": _ngay(x["ngay_chung_tu"]), "ngay_hoa_don": _ngay(x["ngay_hoa_don"])}))
    for x in rows["kho.tri_thuc"]:
        bang_chung = _json(x["bang_chung"])
        them("kho.tri_thuc", str(bang_chung["_sqlite_id"]), _bam({
            "noi_dung": _bam(_json(x["noi_dung"])), "bang_chung": _bam(bang_chung), "nhom": x["nhom"], "khoa_logic": _chu(x["khoa_logic"]),
            "phien_ban": int(x["phien_ban"]), "trang_thai": x["trang_thai"], "actor": _chu(x["actor"]), "valid_from": _thoi_diem(x["valid_from"]),
            "valid_to": _thoi_diem(x["valid_to"]), "known_at": _thoi_diem(x["known_at"]), "content_hash": _chu(x["content_hash"]),
            "tao_luc": _thoi_diem(x["tao_luc"]), "supersedes": _chu(x["supersedes_sid"])}))
    out["_trung"] = dict(trung)
    return out


def doi_chieu_noi_dung(nguon: dict, dich: dict) -> dict:
    out = {}
    for t in ("kho.chung_tu", "kho.chung_tu_dong", "kho.cong_no_mo", "kho.tri_thuc"):
        a, b = nguon[t], dich[t]
        thieu, thua = len(a.keys() - b.keys()), len(b.keys() - a.keys())
        lech = sum(1 for k in a.keys() & b.keys() if a[k] != b[k])
        trung = dich.get("_trung", {}).get(t, 0)
        out[t] = {"nguon": len(a), "dich": len(b) + trung, "thieu": thieu, "thua": thua, "trung": trung, "lech": lech,
                  "khop": thieu == thua == trung == lech == 0}
    out["core_hash_nguon"] = {"sai": nguon.get("core_hash_sai", 0), "khop": nguon.get("core_hash_sai", 0) == 0}
    return out


def _doi_chieu(kq):
    k = kq["documents_theo_kind"]; d = kq["dich"]; ct = d.get("kho.chung_tu theo loai", {})
    rows = [
        ("JOURNAL → kho.chung_tu SO_JUNSKY", k.get("JOURNAL", 0), ct.get("SO_JUNSKY", 0)),
        ("BANK → kho.chung_tu SAO_KE", k.get("BANK", 0), ct.get("SAO_KE", 0)),
        ("document_lines → kho.chung_tu_dong", kq["nguon"]["document_lines"], d["kho.chung_tu_dong"]),
        ("OPEN_ITEM → kho.cong_no_mo", k.get("OPEN_ITEM", 0), d["kho.cong_no_mo"]),
        ("COUNTERPARTY → master.doi_tac_ma_junsky", k.get("COUNTERPARTY", 0), d["master.doi_tac_ma_junsky"]),
        ("ACCOUNT → master.tai_khoan", k.get("ACCOUNT", 0), d["master.tai_khoan"]),
        ("EXPENSE → master.khoan_muc_phi", k.get("EXPENSE", 0), d["master.khoan_muc_phi"]),
        ("COST_CENTER → master.ttcp", k.get("COST_CENTER", 0), d["master.ttcp"]),
        ("PROJECT → master.du_an", k.get("PROJECT", 0), d["master.du_an"]),
        ("knowledge_versions → kho.tri_thuc", kq["nguon"]["knowledge_versions"], d["kho.tri_thuc"]),
        ("quick_items → kho.de_xuat", kq["nguon"]["quick_items"], d["kho.de_xuat"]),
        ("artifacts → kho.tep_goc", kq["nguon"]["artifacts"], d["kho.tep_goc"]),
        ("activity_log + audit_events → nhat_ky.su_kien", kq["nguon"]["activity_log"] + kq["nguon"]["audit_events"], d["nhat_ky.su_kien"]),
        ("issues + quarantine → kho.canh_bao", kq["nguon"]["issues"] + kq["nguon"]["quarantine_records"], d["kho.canh_bao"]),
    ]
    return [{"bang": a, "nguon": b, "dich": c, "khop": b == c} for a, b, c in rows]


def _bang_md(kq):
    out = ["| Ánh xạ | Nguồn (SQLite) | Đích (PostgreSQL) | Khớp |", "|---|---:|---:|---|"]
    for r in kq["doi_chieu"]:
        out.append(f"| {r['bang']} | {r['nguon']} | {r['dich']} | {'✓' if r['khop'] else '✗'} |")
    out.append("")
    out.append("| Nội dung (hash tái tính) | Nguồn | Đích | Thiếu | Thừa | Trùng | Lệch | Khớp |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for t, r in kq.get("doi_chieu_noi_dung", {}).items():
        if "nguon" in r:
            out.append(f"| {t} | {r['nguon']} | {r['dich']} | {r['thieu']} | {r['thua']} | {r['trung']} | {r['lech']} | {'✓' if r['khop'] else '✗'} |")
    out.append("")
    out.append(f"Đối tác: {kq['doi_tac']['ma_junsky']} mã Junsky → {kq['dich']['master.doi_tac']} bản ghi đối tác (gộp {kq['doi_tac']['ma_gop_theo_mst']} mã trùng MST); định danh MST: {kq['dich']['master.doi_tac_dinh_danh']}.")
    dx = kq['de_xuat']
    out.append(f"Đề xuất T8: {dx['de_xuat']} đề xuất · {dx['de_xuat_dong']} dòng · {dx['viec_can_duyet']} việc cần duyệt V1 · bỏ qua vì đã xuất: {dx['bo_qua_vi_da_xuat']} · lệch Nợ/Có: {dx['de_xuat_lech_no_co']} · dòng TK công nợ thiếu đối tượng: {dx['dong_tk_cong_no_thieu_doi_tuong']} (mức Xanh/Vàng/Đỏ là TẠM; bản V12 giữ trong can_cu).")
    for g in kq.get("ghi_chu", []):
        out.append(f"Ghi chú: {g}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.exit(main())
