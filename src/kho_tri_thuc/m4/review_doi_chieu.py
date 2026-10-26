"""M4-CD2: đối chiếu owner snapshot với SQLite chỉ đọc, độc lập công cụ nạp.

Không dùng hash, bộ chuyển kiểu hay tổng kiểm soát của CD1/DL2 làm bằng chứng.
So từng ô nguồn để bắt cả lệch bù trừ trong một HĐ/đợt. Tổng BOQ là số ghi
theo thao tác, không cộng thay đổi PL thành BOQ hiệu lực. NULL khác số 0.
Kết quả chỉ có thống kê và mã thay thế, không trả khóa/ngữ liệu nguồn.
Caller cấp owner connection sạch; mọi SELECT PG ở cùng snapshot read-only.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from collections.abc import Mapping
from contextlib import closing
from decimal import Decimal, localcontext
from pathlib import Path

from ..ha_tang.primitives import DataError
from .review_phu_luc_pg import boq_tai_ngay


# Hợp đồng schema tự khai báo theo DDL Review, không lấy từ công cụ nạp.
_COT = {
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
_COT = {t: tuple(c.split()) for t, c in _COT.items()}
_PK = {
    "che_do": ("id",), "hop_dong": ("ma_hd",),
    "tham_so": ("ma_hd", "ma_ts"), "phu_luc": ("id",),
    "thay_doi_tham_so": ("pl_id", "ma_ts"), "boq_dong": ("id",),
    "dot_thanh_toan": ("ma_hd", "dot"), "kl_thanh_toan": ("ma_hd", "dot", "ma_hm"),
    "khop_hang_muc": ("ma_hd", "khoa_hstt"), "canh_bao": ("id",),
    "nhat_ky": ("id",), "tham_so_nguon": ("ma_hd", "ma_ts"),
}
_SO = set("gia_tri_hd vat gt_truoc_vat gt_sau_vat gt_hd_sau_pl kl don_gia thanh_tien_ghi gt_ky gt_luy_ke giu_lai thu_hoi_tu gt_tt_ky kl_ky kl_luy_ke don_gia_tt".split())
_TIEN_DOT = ("gt_ky", "gt_luy_ke", "giu_lai", "thu_hoi_tu", "gt_tt_ky")


def _sai():
    raise DataError("M4_REVIEW_DOI_CHIEU_SAI", "Khong the doi chieu schema/so nguon.")


def _so(value):
    if value is None:
        return None
    if type(value) not in (int, float, Decimal):
        _sai()
    number = Decimal(str(value))
    if not number.is_finite():
        _sai()
    return number


def _tong(values):
    numbers = [_so(v) for v in values]
    valid = [v for v in numbers if v is not None]
    with localcontext() as ctx:
        ctx.prec = max(28, max((v.adjusted() for v in valid), default=0)
                       - min((v.as_tuple().exponent for v in valid), default=0)
                       + len(str(len(valid))) + 3)
        total = sum(valid, Decimal(0))
    text = format(total, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return {"tong": ("0" if total == 0 else text) if valid else None,
            "so_null": len(numbers) - len(valid)}


def _nhan(a, b):
    a, b = _so(a), _so(b)
    if a is None or b is None:
        return None
    with localcontext() as ctx:
        ctx.prec = max(28, len(a.as_tuple().digits) + len(b.as_tuple().digits))
        return a * b


def _doc_sqlite(path):
    path = Path(path).resolve(strict=True)
    # immutable không thấy WAL: từ chối bản sao chưa checkpoint/đóng.
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            _sai()
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as con:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        data = {}
        for table, columns in _COT.items():
            actual = {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
            missing = set(columns) - actual
            if actual - set(columns) or missing - ({"ma_rieng"} if table == "boq_dong" else set()):
                _sai()
            data[table] = [dict(r, **{c: None for c in missing})
                           for r in con.execute(f'SELECT * FROM "{table}"')]
    return data


def _doc_pg(con, query, params):
    cur = con.execute(query, params)
    names = [c.name for c in cur.description]
    return [dict(r) if isinstance(r, Mapping) else dict(zip(names, r)) for r in cur.fetchall()]


def _thong_ke(data, codes):
    contracts, dots = [], []
    for code in codes:
        hd = [r for r in data["hop_dong"] if r["ma_hd"] == code]
        boq = [r for r in data["boq_dong"] if r["ma_hd"] == code]
        contracts.append({"khoa": codes[code], "gia_tri_hd": _tong(r["gia_tri_hd"] for r in hd),
                          "boq": {op: {
                              "so_dong": sum(r["thao_tac"] == op for r in boq),
                              "thanh_tien_ghi": _tong(r["thanh_tien_ghi"] for r in boq if r["thao_tac"] == op),
                              "kl_nhan_don_gia": _tong(_nhan(r["kl"], r["don_gia"]) for r in boq if r["thao_tac"] == op),
                          } for op in ("GOC", "THAY", "THEM", "BO")}})
    for row in sorted(data["dot_thanh_toan"], key=lambda r: (r["ma_hd"], r["dot"])):
        lines = [r for r in data["kl_thanh_toan"] if (r["ma_hd"], r["dot"]) == (row["ma_hd"], row["dot"])]
        dots.append({"khoa": codes[row["ma_hd"]], "dot": row["dot"], "so_hang_muc": len(lines),
                     **{c: _tong([row[c]]) for c in _TIEN_DOT},
                     **{c + "_nhan_don_gia": _tong(_nhan(r[c], r["don_gia_tt"]) for r in lines)
                        for c in ("kl_ky", "kl_luy_ke")}})
    return {"gia_tri_hd": _tong(r["gia_tri_hd"] for r in data["hop_dong"]),
            "tung_hd": contracts, "tung_dot": dots}


def doi_chieu(nguon_sqlite, con, *, nguon_id):
    """Đọc hai phía độc lập; không ghi PG/SQLite. Trả báo cáo JSON an toàn.

    Cờ DL3 xét tại ngày chup_luc, ổn định khi chạy lại, không dùng ngày máy.
    Các mã HD/K chỉ có nghĩa trong báo cáo này; không xuất mã nguồn thô.
    """
    source = _doc_sqlite(nguon_sqlite)
    with con.transaction():
        con.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        metadata = _doc_pg(con, "SELECT chup_luc FROM m4.review_chep_nguon WHERE id=%s", (nguon_id,))
        if len(metadata) != 1:
            raise DataError("M4_REVIEW_KHONG_THAY", "Khong thay lan chup can doi chieu.")
        target = {t: _doc_pg(con, f"SELECT {','.join(cols)} FROM m4.review_chep_{t} WHERE nguon_id=%s", (nguon_id,))
                  for t, cols in _COT.items()}
    contracts = {r["ma_hd"] for data in (source, target) for r in data["hop_dong"]}
    all_codes = {r["ma_hd"] for data in (source, target) for rows in data.values()
                 for r in rows if r.get("ma_hd") not in (None, "")}
    codes = {code: f"HD{i:04d}" for i, code in enumerate(
        sorted(contracts) + sorted(all_codes - contracts), 1)}
    tables, errors = {}, []
    for table in _COT:
        indexes = [{tuple(r[c] for c in _PK[table]): r for r in data[table]} for data in (source, target)]
        left, right = indexes
        keys = sorted(left.keys() | right.keys())
        aliases = {k: {"khoa_dong": f"K{i:06d}"} for i, k in enumerate(keys, 1)}
        for key in keys:
            row = left.get(key, right.get(key))
            if row.get("ma_hd") not in (None, ""):
                aliases[key]["khoa"] = codes[row["ma_hd"]]
            if "dot" in row:
                if row["dot"] is not None and type(row["dot"]) is not int:
                    _sai()
                aliases[key]["dot"] = row["dot"]
        bad = []
        for key in keys:
            if key not in left or key not in right:
                bad.append({**aliases[key], "ma_loi": "THIEU_PG" if key in left else "THIEU_SQLITE"})
                continue
            columns = []
            for col in _COT[table]:
                a, b = left[key][col], right[key][col]
                if col in _SO:
                    try:
                        a, b = _so(a), _so(b)
                    except DataError:
                        columns.append(col)
                        continue
                if a != b:
                    columns.append(col)
            if columns:
                bad.append({**aliases[key], "ma_loi": "GIA_TRI_LECH", "cot": columns})
        # Trùng PK không được che bởi dict; báo số dòng lỗi ngay cả nguồn sai DDL.
        duplicate = sum(sum(n - 1 for n in Counter(tuple(r[c] for c in _PK[table])
                                                  for r in data[table]).values()) for data in (source, target))
        tables[table] = {"sqlite": len(source[table]), "pg": len(target[table]),
                         "thieu_pg": [aliases[k] for k in keys if k not in right],
                         "thieu_sqlite": [aliases[k] for k in keys if k not in left],
                         "so_dong_loi": len(bad) + duplicate, "so_trung_khoa": duplicate}
        errors.extend(dict(bang=table, **row) for row in bad)
    cutoff = metadata[0]["chup_luc"].date().isoformat()
    flagged = sum(boq_tai_ngay(
        [r for r in target["phu_luc"] if r["ma_hd"] == hd["ma_hd"]],
        [r for r in target["boq_dong"] if r["ma_hd"] == hd["ma_hd"]], cutoff)["can_xem_lai"]
        for hd in target["hop_dong"])
    count = sum(t["so_dong_loi"] for t in tables.values())
    return {"khop": count == 0, "don_vi_tien": "VND", "bang": tables,
            "so_dong_loi": count, "dong_loi": errors, "so_hd_can_xem_lai": flagged,
            "tong_sqlite": _thong_ke(source, codes), "tong_pg": _thong_ke(target, codes)}
