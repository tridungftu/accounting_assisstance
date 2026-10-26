"""M4-CD1: chép đủ một lần chụp Review, nguồn chỉ đọc, đích một transaction.

Chỉ lead dùng với bản sao đã sao lưu theo CD-011. Không migrate/tạo CSDL,
không tạo HĐ vận hành. JSON kết nối nhận admin_dsn (owner) hoặc dsn.
--thu kiểm nguồn/ánh xạ và tính tổng, không kết nối PG; không xác nhận FK
master hay trạng thái replay ở đích. Báo cáo từng đợt dùng số thứ tự ẩn danh,
không xuất ma_hd, số HĐ, tên, payload hay exception từ driver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sqlite3
import sys
import uuid
from collections.abc import Mapping
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4.review_data_pg import ReviewDataPG, dong_sha256, real_sang_decimal
from kho_tri_thuc.m4.review_phu_luc_pg import ReviewPhuLucPG
from kho_tri_thuc.m4.review_doi_chieu import doi_chieu
from kho_tri_thuc.m4.sql_review_chep import BANG_NGUON


# DDL csdl_hop_dong.py của vendor; không import/chạy mo_csdl của nguồn.
COT = {
    "che_do": "id sua",
    "hop_dong": "ma_hd so_hd phan_loai loai_gia ngay_ky goi_thau gia_tri_hd gom_vat vat file_nguon ngay_nap",
    "tham_so": "ma_hd ma_ts ten gia_tri don_vi dieu_khoan trich_dan trang_thai",
    "phu_luc": "id ma_hd so_pl ngay_ky ngay_hieu_luc loai doi_boq gt_truoc_vat gt_sau_vat gt_hd_sau_pl noi_dung can_cu file_nguon phieu trang_thai nguoi_nhap ngay_nap ly_do_huy",
    "thay_doi_tham_so": "pl_id ma_ts gia_tri_cu gia_tri_moi trich_dan",
    "boq_dong": "id ma_hd pl_id thao_tac ma_hm stt nhom ten dvt kl don_gia thanh_tien_ghi khoa vi_tri_nguon ghi_chu ma_rieng",
    "dot_thanh_toan": "ma_hd dot ngay_nghiem_thu ngay_nhan_hs gt_ky gt_luy_ke giu_lai thu_hoi_tu gt_tt_ky file_nguon ngay_nap",
    "kl_thanh_toan": "ma_hd dot ma_hm kl_ky kl_luy_ke don_gia_tt vi_tri_nguon",
    "khop_hang_muc": "ma_hd khoa_hstt ma_hm cach_khop nguoi_xac_nhan ngay",
    "canh_bao": "id ma_hd pl_id dot ma_kt muc_do noi_dung thoi_diem",
    "nhat_ky": "id thoi_diem nguoi thao_tac ma_hd chi_tiet",
    "tham_so_nguon": "ma_hd ma_ts gia_tri_ai gia_tri kiem_tra muc nguon da_xac_nhan da_sua_tay nguoi_xac_nhan luc_xac_nhan ghi_chu_soat lich_su model may_ai luot file_hop_dong sha1_file luc_trich luc_nap",
}
COT = {t: tuple(c.split()) for t, c in COT.items()}
PK = {"che_do": ("id",), "hop_dong": ("ma_hd",),
      "tham_so": ("ma_hd", "ma_ts"), "phu_luc": ("id",),
      "thay_doi_tham_so": ("pl_id", "ma_ts"), "boq_dong": ("id",),
      "dot_thanh_toan": ("ma_hd", "dot"), "kl_thanh_toan": ("ma_hd", "dot", "ma_hm"),
      "khop_hang_muc": ("ma_hd", "khoa_hstt"), "canh_bao": ("id",),
      "nhat_ky": ("id",), "tham_so_nguon": ("ma_hd", "ma_ts")}
DL2 = ("che_do", "hop_dong", "tham_so", "tham_so_nguon")
DL3 = ("phu_luc", "thay_doi_tham_so", "boq_dong")
CON_LAI = ("dot_thanh_toan", "kl_thanh_toan", "khop_hang_muc", "canh_bao", "nhat_ky")
NUMERIC = set("gia_tri_hd vat gt_truoc_vat gt_sau_vat gt_hd_sau_pl kl don_gia thanh_tien_ghi gt_ky gt_luy_ke giu_lai thu_hoi_tu gt_tt_ky kl_ky kl_luy_ke don_gia_tt".split())
INTEGER = set("id sua pl_id doi_boq dot muc da_xac_nhan da_sua_tay".split())
NHAP_BOI = "CHUYEN_REVIEW_CD011"


def _loi(code, message, bang=None):
    raise DataError(code, message, locator=bang or "$")


def sha256_tep(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _khong_sidecar(path):
    # immutable không đọc WAL; từ chối bản sao chưa đóng/checkpoint thay vì mất dòng.
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            _loi("M4_REVIEW_NGUON_DANG_GHI", "Nguồn có WAL/journal; cần bản sao SQLite đã đóng nhất quán.")


def mo_nguon(path):
    """Không tạo file khi sai đường dẫn; URI escape cả dấu #, ? và Unicode."""
    path = Path(path).resolve(strict=True)
    _khong_sidecar(path)
    con = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def kiem_sha(path, expected):
    _khong_sidecar(path)
    if sha256_tep(path) != expected:
        _loi("M4_REVIEW_NGUON_DA_DOI", "SHA256 nguồn thay đổi; dừng và rollback cả lần chụp.")


def doc_nguon(path, *, bao_truoc=None):
    path = Path(path).resolve(strict=True)
    before = sha256_tep(path)
    if bao_truoc is not None:
        bao_truoc({"sha256_truoc": before})
    data = {}
    try:
        with closing(mo_nguon(path)) as con:
            con.execute("BEGIN")
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in BANG_NGUON:
                if table not in tables:
                    _loi("M4_REVIEW_LUOC_DO_SAI", f"Thiếu bảng nguồn {table}; không nạp một phần.", table)
                columns = {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
                expected = set(COT[table])
                missing = expected - columns
                # Cột bổ sung duy nhất của nguồn trước 13/10; không ALTER nguồn.
                if columns - expected or missing - ({"ma_rieng"} if table == "boq_dong" else set()):
                    _loi("M4_REVIEW_LUOC_DO_SAI", f"Cột nguồn {table} không đúng DDL đã kiểm kê.", table)
                data[table] = [dict(r) for r in con.execute(f'SELECT * FROM "{table}"')]
                for row in data[table]:
                    for col in missing:
                        row[col] = None
            violation = con.execute("PRAGMA foreign_key_check").fetchone()
            if violation is not None:
                table = next((t for t in BANG_NGUON if t == violation[0]), None)
                _loi("M4_REVIEW_FK_SAI", "Khóa ngoại nguồn không hợp lệ; dừng cả lần chụp.", table)
    finally:
        kiem_sha(path, before)
    return data, before


def doc_anh_xa(path):
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["ma_hd", "hop_dong_id", "du_an_id"]:
            _loi("M4_REVIEW_ANH_XA_SAI", "CSV cần đúng cột ma_hd,hop_dong_id,du_an_id theo thứ tự.")
        for row in reader:
            code = row.get("ma_hd")
            if not code or code in result or None in row:
                _loi("M4_REVIEW_ANH_XA_SAI", "CSV có dòng thiếu/trùng khóa hoặc thừa cột.")
            try:
                result[code] = tuple(str(uuid.UUID(row[k])) for k in ("hop_dong_id", "du_an_id"))
            except (ValueError, TypeError, AttributeError):
                _loi("M4_REVIEW_ANH_XA_SAI", "CSV có UUID không hợp lệ.")
    return result


def kiem_du_lieu(data, mapping):
    """Kiểm đủ schema/kiểu/khóa/FK cả khi --thu, không đoán ngày TEXT cũ."""
    if set(data) != set(BANG_NGUON):
        _loi("M4_REVIEW_LUOC_DO_SAI", "Cần đủ 12 bảng của lần chụp.")
    required = {
        "che_do": ("sua",), "hop_dong": ("so_hd",),
        "phu_luc": ("ma_hd", "so_pl", "ngay_ky", "ngay_hieu_luc", "doi_boq", "trang_thai"),
        "boq_dong": ("ma_hd", "thao_tac", "ma_hm"),
        "khop_hang_muc": ("ma_hm",), "tham_so_nguon": ("da_xac_nhan", "da_sua_tay"),
    }
    keys = {}
    for table in BANG_NGUON:
        keys[table] = set()
        for row in data[table]:
            if set(row) != set(COT[table]):
                _loi("M4_REVIEW_LUOC_DO_SAI", f"Cột {table} không đúng DDL.", table)
            for col in COT[table]:
                value = row[col]
                if col in NUMERIC:
                    try:
                        real_sang_decimal(value)
                    except DataError as exc:
                        exc.locator = f"{table}.{col}"
                        raise
                elif col in INTEGER:
                    if value is not None and (type(value) is not int or not -(2**63) <= value < 2**63):
                        _loi("M4_REVIEW_KIEU_SAI", f"{table}.{col} cần INTEGER 64-bit hoặc NULL.", f"{table}.{col}")
                elif value is not None and not isinstance(value, str):
                    _loi("M4_REVIEW_KIEU_SAI", f"{table}.{col} cần TEXT hoặc NULL.", f"{table}.{col}")
            if any(row[c] is None for c in (*PK[table], *required.get(table, ()))):
                _loi("M4_REVIEW_KHOA_SAI", f"{table} thiếu giá trị bắt buộc.", table)
            key = tuple(row[c] for c in PK[table])
            if key in keys[table]:
                _loi("M4_REVIEW_KHOA_SAI", f"{table} trùng khóa nguồn.", table)
            keys[table].add(key)
    contracts = {r["ma_hd"] for r in data["hop_dong"]}
    # Chỉ HĐ còn trong lần chụp cần ánh xạ; log/cảnh báo giữ mã HĐ đã xóa.
    for code in contracts:
        if code not in mapping:
            _loi("M4_REVIEW_THIEU_ANH_XA", "Thiếu ánh xạ ma_hd đã chốt; không ghi gì.", "hop_dong.ma_hd")
        pair = mapping[code]
        try:
            if len(pair) != 2:
                raise ValueError
            for value in pair:
                uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            _loi("M4_REVIEW_ANH_XA_SAI", "Ánh xạ cần hai UUID hợp lệ.", "hop_dong.ma_hd")
    if len({str(mapping[c][0]) for c in contracts}) != len(contracts):
        _loi("M4_REVIEW_ANH_XA_SAI", "Nhiều mã nguồn trỏ cùng HĐ đích trong một lần chụp.", "hop_dong.ma_hd")
    for table in ("tham_so", "tham_so_nguon", "phu_luc", "boq_dong", "dot_thanh_toan"):
        if any(r["ma_hd"] not in contracts for r in data[table]):
            _loi("M4_REVIEW_FK_SAI", f"{table} thiếu HĐ cha trong lần chụp.", f"{table}.ma_hd")
    pls = {r["id"]: r for r in data["phu_luc"]}
    for r in data["thay_doi_tham_so"]:
        if r["pl_id"] not in pls:
            _loi("M4_REVIEW_FK_SAI", "Tham số thay đổi thiếu phụ lục cha.", "thay_doi_tham_so.pl_id")
    for r in data["kl_thanh_toan"]:
        if (r["ma_hd"], r["dot"]) not in keys["dot_thanh_toan"]:
            _loi("M4_REVIEW_FK_SAI", "Khối lượng thanh toán thiếu đợt cha.", "kl_thanh_toan.dot")
    for r in data["boq_dong"]:
        if r["thao_tac"] not in ("GOC", "THAY", "THEM", "BO"):
            _loi("M4_REVIEW_KHOA_SAI", "Thao tác BOQ chưa có quy tắc.", "boq_dong.thao_tac")
        if r["pl_id"] is not None and (r["pl_id"] not in pls or pls[r["pl_id"]]["ma_hd"] != r["ma_hd"]):
            _loi("M4_REVIEW_FK_SAI", "BOQ không cùng HĐ với phụ lục cha.", "boq_dong.pl_id")
    for table, group, rows in (
        ("hop_dong", lambda r: r["so_hd"], data["hop_dong"]),
        ("phu_luc", lambda r: (r["ma_hd"], r["so_pl"]), [r for r in data["phu_luc"] if r["trang_thai"] != "Đã hủy"]),
        ("boq_dong", lambda r: (r["ma_hd"], r["pl_id"] or 0, r["ma_hm"]), data["boq_dong"]),
    ):
        if len({group(r) for r in rows}) != len(rows):
            _loi("M4_REVIEW_KHOA_SAI", f"{table} vi phạm khóa UNIQUE nguồn.", table)
    if any(r["id"] != 1 for r in data["che_do"]):
        _loi("M4_REVIEW_KHOA_SAI", "che_do có id ngoài DDL.", "che_do.id")


def _tong(values):
    numbers = [real_sang_decimal(v) for v in values]
    valid = [v for v in numbers if v is not None]
    with localcontext() as ctx:
        ctx.prec = 1000
        total = sum(valid, Decimal(0))
    return {"tong": format(total, "f") if valid else None, "so_null": len(numbers) - len(valid)}


def tong_kiem_soat(data):
    """Số ghi nguồn; BOQ gốc và thay đổi tách riêng, không giả tổng hiệu lực."""
    boq = {}
    for operation in ("GOC", "THAY", "THEM", "BO"):
        rows = [r for r in data["boq_dong"] if r["thao_tac"] == operation]
        with localcontext() as ctx:
            ctx.prec = 1000
            products = [None if r["kl"] is None or r["don_gia"] is None else
                        real_sang_decimal(r["kl"]) * real_sang_decimal(r["don_gia"]) for r in rows]
        boq[operation] = {"so_dong": len(rows), "thanh_tien_ghi": _tong(r["thanh_tien_ghi"] for r in rows),
                          "kl_nhan_don_gia_chua_lam_tron": _tong(products)}
    dots = []
    for index, r in enumerate(sorted(data["dot_thanh_toan"], key=lambda r: (r["ma_hd"], r["dot"])), 1):
        quantities = [k for k in data["kl_thanh_toan"] if (k["ma_hd"], k["dot"]) == (r["ma_hd"], r["dot"])]
        item = {"thu_tu": index, "so_hang_muc": len(quantities)}
        item.update({c: _tong([r[c]]) for c in ("gt_ky", "gt_luy_ke", "giu_lai", "thu_hoi_tu", "gt_tt_ky")})
        with localcontext() as ctx:
            ctx.prec = 1000
            for quantity in ("kl_ky", "kl_luy_ke"):
                item[quantity + "_nhan_don_gia"] = _tong(
                    None if k[quantity] is None or k["don_gia_tt"] is None else
                    real_sang_decimal(k[quantity]) * real_sang_decimal(k["don_gia_tt"]) for k in quantities)
        dots.append(item)
    return {"don_vi_tien": "VND", "gia_tri_hd_goc": _tong(r["gia_tri_hd"] for r in data["hop_dong"]),
            "boq_theo_thao_tac": boq, "tung_dot": dots}


def _rows(con, query, params):
    cur = con.execute(query, params)
    names = [c.name for c in cur.description]
    return [dict(r) if isinstance(r, Mapping) else dict(zip(names, r)) for r in cur.fetchall()]


def _ghi_con_lai(con, data, mapping, nguon_id, replay):
    contracts = {r["ma_hd"] for r in data["hop_dong"]}
    for table in CON_LAI:
        prepared = {}
        for original in data[table]:
            row = {c: real_sang_decimal(v) if c in NUMERIC else v for c, v in original.items()}
            code = row.get("ma_hd")
            pair = tuple(str(uuid.UUID(str(v))) for v in mapping[code]) if code in contracts else (None, None)
            if table != "kl_thanh_toan":
                row["hop_dong_id"] = pair[0]
            row["du_an_id"] = pair[1]
            row["dong_sha256"] = dong_sha256(row)
            prepared[tuple(row[c] for c in PK[table])] = row
        actual = {tuple(r[c] for c in PK[table]): r["dong_sha256"] for r in _rows(
            con, f"SELECT {','.join(PK[table])},dong_sha256 FROM m4.review_chep_{table} WHERE nguon_id=%s", (nguon_id,))}
        if (replay and actual != {k: r["dong_sha256"] for k, r in prepared.items()}) or (not replay and actual):
            _loi("M4_REVIEW_REPLAY_KHAC", f"Cùng nguon_id nhưng tập khóa/dữ liệu {table} khác; dừng, không ghi đè.", table)
        if not replay:
            for row in prepared.values():
                row.update(nguon_id=nguon_id, nhap_boi=NHAP_BOI)
                con.execute(f"INSERT INTO m4.review_chep_{table} ({','.join(row)}) VALUES ({','.join('%s' for _ in row)})", tuple(row.values()))


def ghi_pg(con, data, mapping, *, nguon_id, chup_luc, sha256_nguon=None, truoc_commit=None):
    """Caller cấp owner connection sạch; lỗi thoát outer transaction để rollback."""
    kiem_du_lieu(data, mapping)
    with con.transaction():
        added = ReviewDataPG(con).ghi_lan_chup(
            {t: data[t] for t in DL2}, nguon_id=nguon_id, chup_luc=chup_luc,
            nhap_boi=NHAP_BOI, anh_xa=mapping,
            mo_ta=None if sha256_nguon is None else "sha256:" + sha256_nguon)
        replay = added == 0
        ReviewPhuLucPG(con).ghi_trong_giao_dich(
            {t: data[t] for t in DL3}, nguon_id=nguon_id, nhap_boi=NHAP_BOI, replay=replay)
        _ghi_con_lai(con, data, mapping, nguon_id, replay)
        counts = {}
        for table in BANG_NGUON:
            count = con.execute(f"SELECT count(*) FROM m4.review_chep_{table} WHERE nguon_id=%s", (nguon_id,)).fetchone()
            actual = count["count"] if isinstance(count, Mapping) else count[0]
            if actual != len(data[table]):
                _loi("M4_REVIEW_SO_DEM_LECH", f"Số đếm {table} không khớp; rollback.", table)
            counts[table] = {"da_ghi_moi": 0 if replay else actual, "da_co_dich": actual}
        if truoc_commit is not None:
            truoc_commit()
    return counts


def doc_dsn(path):
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        _loi("M4_REVIEW_KET_NOI_SAI", "Tệp kết nối cần JSON object.")
    dsn = config.get("admin_dsn", config.get("dsn"))
    if not isinstance(dsn, str) or not dsn.strip():
        _loi("M4_REVIEW_KET_NOI_SAI", "Tệp kết nối thiếu admin_dsn hoặc dsn chủ bảng.")
    return dsn


def main(argv=None):
    # Chặn warning rollback của driver trước khi import/kết nối psycopg.
    logger = logging.getLogger("psycopg")
    if not any(isinstance(handler, logging.NullHandler) for handler in logger.handlers):
        logger.addHandler(logging.NullHandler())
    logger.propagate = False
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("nguon", "dsn-tep", "nguon-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--anh-xa")
    parser.add_argument("--chup-luc")
    parser.add_argument("--thu", action="store_true")
    parser.add_argument("--doi-chieu", action="store_true",
                        help="Doi chieu sau nap; bo ca --anh-xa va --chup-luc de chi doi chieu lan chup da co.")
    args = parser.parse_args(argv)

    def emit(report):
        print(json.dumps(report, ensure_ascii=True, allow_nan=False), flush=True)

    try:
        if args.doi_chieu and args.thu:
            _loi("M4_REVIEW_METADATA_SAI", "Doi chieu can doc PG; khong dung cung --thu.")
        if args.doi_chieu and args.anh_xa is None and args.chup_luc is None:
            if not args.nguon_id.strip():
                _loi("M4_REVIEW_METADATA_SAI", "Can nguon_id khong rong.")
            dsn = doc_dsn(args.dsn_tep)
            import psycopg
            with psycopg.connect(dsn, autocommit=True) as con:
                report = doi_chieu(args.nguon, con, nguon_id=args.nguon_id)
            emit({"trang_thai": "DOI_CHIEU_KHOP" if report["khop"] else "DOI_CHIEU_LECH",
                  "doi_chieu": report})
            return 0 if report["khop"] else 2
        if args.anh_xa is None or args.chup_luc is None:
            _loi("M4_REVIEW_METADATA_SAI", "Nap can ca --anh-xa va --chup-luc.")
        moment = datetime.fromisoformat(args.chup_luc)
        if moment.tzinfo is None or moment.utcoffset() is None or not args.nguon_id.strip():
            _loi("M4_REVIEW_METADATA_SAI", "Cần nguon_id không rỗng và chup_luc ISO có múi giờ.")
        moment = moment.astimezone(timezone.utc)
        data, digest = doc_nguon(args.nguon, bao_truoc=emit)
        mapping = doc_anh_xa(args.anh_xa)
        kiem_du_lieu(data, mapping)
        dsn = doc_dsn(args.dsn_tep)
        totals = tong_kiem_soat(data)
        counts = {t: {"da_ghi_moi": 0, "da_co_dich": None} for t in BANG_NGUON}
        comparison = None
        if not args.thu:
            import psycopg
            with psycopg.connect(dsn, autocommit=True) as con:
                counts = ghi_pg(con, data, mapping, nguon_id=args.nguon_id, chup_luc=moment,
                                sha256_nguon=digest,
                                truoc_commit=lambda: kiem_sha(args.nguon, digest))
                if args.doi_chieu:
                    comparison = doi_chieu(args.nguon, con, nguon_id=args.nguon_id)
        else:
            kiem_sha(args.nguon, digest)
        contracts = {r["ma_hd"] for r in data["hop_dong"]}
        emit({"trang_thai": "THU_KHONG_GHI" if args.thu else "HOAN_TAT",
              "sha256_truoc": digest, "sha256_sau": digest,
              "bang": {t: dict(da_doc=len(data[t]), **counts[t],
                               so_dong_mo_coi=sum(r.get("ma_hd") not in contracts
                                                  for r in data[t] if r.get("ma_hd") not in (None, "")))
                       for t in BANG_NGUON},
              "tong_kiem_soat": totals})
        if comparison is not None:
            emit({"trang_thai": "DOI_CHIEU_KHOP" if comparison["khop"] else "DOI_CHIEU_LECH",
                  "doi_chieu": comparison})
            return 0 if comparison["khop"] else 2
        return 0
    except KeyboardInterrupt:
        try:
            sys.stderr.write("M4_REVIEW_CHUYEN_DUNG\n")
            sys.stderr.flush()
        except BaseException:
            pass
        return 130
    except BaseException as exc:
        # Không xuất str(exc), traceback, DSN/path hay nội dung driver/SQL.
        try:
            code = exc.code if isinstance(exc, DataError) and exc.code.startswith("M4_REVIEW_") else "M4_REVIEW_CHUYEN_LOI"
            message = ("Cùng nguon_id nhưng chup_luc, metadata hoặc dữ liệu khác; dừng, không ghi đè."
                       if code == "M4_REVIEW_REPLAY_KHAC" else
                       "Đối chiếu không hoàn tất; dữ liệu đã nạp trước đó vẫn được giữ. Cần Anh kiểm tra nguồn và cấu hình."
                       if args.doi_chieu else
                       "Lần chụp không hoàn tất; không ghi dữ liệu một phần. Cần Anh kiểm tra nguồn, ánh xạ và cấu hình.")
            report = {"trang_thai": "LOI", "ma_loi": code, "thong_bao": message}
            if isinstance(exc, DataError) and code.startswith("M4_REVIEW_"):
                # Không lấy tên từ message/giá trị dữ liệu hoặc locator tùy ý.
                allowed = {*COT, *(f"{t}.{c}" for t in COT for c in COT[t])}
                report["bang"] = next((name for name in allowed if name == exc.locator), None)
            emit(report)
        except BaseException:
            # Console hỏng/đóng cũng không được làm lộ exception gốc qua chaining.
            try:
                sys.stderr.write("M4_REVIEW_CHUYEN_LOI\n")
                sys.stderr.flush()
            except BaseException:
                pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
