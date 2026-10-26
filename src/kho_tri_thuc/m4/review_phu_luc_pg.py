"""M4-DL3 — PL/tham số đổi/BOQ của cùng lần chụp đầy đủ Review.

Lớp đọc tự kiểm quyền XEM/REVIEW bằng conn phiên trước khi dùng conn chủ bảng;
dùng chung khối kiểm và phân biệt ba trạng thái NULL của DL2, không mở DSN/tệp.
DL2 chưa có hook: Cần lead nối công cụ nạp vào ghi_lan_chup bên dưới hoặc
gọi ghi_trong_giao_dich sau DL2 trên CÙNG conn/transaction; lỗi phải thoát
transaction ngoài để rollback cả lần chụp. Không nạp riêng một HĐ/dự án.
Replay phải truyền đủ ba bảng, kể cả []; không nối thêm vào lần chụp cũ.

Ngày nguồn vẫn TEXT nguyên văn; projection chỉ nhận ngày ISO YYYY-MM-DD.
THAY giữ ô cũ nếu ô mới NULL/rỗng, đúng csdl_hop_dong.boq_hieu_luc nguồn;
dữ liệu chép vẫn giữ NULL/rỗng riêng biệt. Không suy thứ tự PL cùng ngày,
không suy ngày/người hủy, không cộng/tính lại gt_hd_sau_pl.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import date

from ..ha_tang.primitives import DataError
from .review_data_pg import ReviewDataPG, dong_sha256, real_sang_decimal


_COT = {
    "phu_luc": (
        "id", "ma_hd", "so_pl", "ngay_ky", "ngay_hieu_luc", "loai", "doi_boq",
        "gt_truoc_vat", "gt_sau_vat", "gt_hd_sau_pl", "noi_dung", "can_cu",
        "file_nguon", "phieu", "trang_thai", "nguoi_nhap", "ngay_nap", "ly_do_huy",
    ),
    "thay_doi_tham_so": ("pl_id", "ma_ts", "gia_tri_cu", "gia_tri_moi", "trich_dan"),
    "boq_dong": (
        "id", "ma_hd", "pl_id", "thao_tac", "ma_hm", "stt", "nhom", "ten",
        "dvt", "kl", "don_gia", "thanh_tien_ghi", "khoa", "vi_tri_nguon",
        "ghi_chu", "ma_rieng",
    ),
}
_PK = {"phu_luc": ("id",), "thay_doi_tham_so": ("pl_id", "ma_ts"), "boq_dong": ("id",)}
_NUMERIC = {"gt_truoc_vat", "gt_sau_vat", "gt_hd_sau_pl", "kl", "don_gia", "thanh_tien_ghi"}
_INTEGER = {"id", "pl_id", "doi_boq"}
_PL_DTO = (
    "so_pl", "ngay_ky", "ngay_hieu_luc", "loai", "doi_boq", "gt_truoc_vat",
    "gt_sau_vat", "gt_hd_sau_pl", "noi_dung", "can_cu", "trang_thai", "ly_do_huy",
)
_TS_DTO = ("ma_ts", "gia_tri_cu", "gia_tri_moi", "trich_dan")
_BOQ_DTO = ("ma_hm", "stt", "nhom", "ten", "dvt", "kl", "don_gia", "thanh_tien_ghi", "ghi_chu", "ma_rieng")
_THAY = ("stt", "nhom", "ten", "dvt", "kl", "don_gia", "thanh_tien_ghi")


def _sai(message):
    raise DataError("M4_REVIEW_DU_LIEU_SAI", message)


def _khac(table):
    raise DataError("M4_REVIEW_REPLAY_KHAC", f"Tập khóa/dong_sha256 khác ở {table}; không ghi đè lần chụp.")


def _rows(conn, query, params=()):
    cur = conn.execute(query, params)
    names = [c.name for c in cur.description]
    return [dict(r) if isinstance(r, Mapping) else dict(zip(names, r)) for r in cur.fetchall()]


def _dto(row, columns):
    return {c: real_sang_decimal(row.get(c)) if c in _NUMERIC else row.get(c) for c in columns}


def _ngay(value):
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        except ValueError:
            pass
    _sai("Ngày đối chiếu/hiệu lực cần đúng YYYY-MM-DD, không tự đoán ngày nguồn.")


def _phu_luc_tai_ngay(phu_luc, ngay):
    cutoff = _ngay(ngay)
    active, reasons = [], []
    for pl in phu_luc:
        state = pl.get("trang_thai")
        if state in ("Đã hủy", "Dự thảo"):
            continue
        if state != "Đã ký":
            reasons.append("Trạng thái phụ lục chưa có quy tắc áp dụng.")
            continue
        try:
            effective = _ngay(pl.get("ngay_hieu_luc"))
        except DataError:
            reasons.append("Ngày hiệu lực phụ lục chưa xác định được.")
            continue
        if effective <= cutoff:
            active.append((effective, pl))
    if any(n > 1 for n in Counter(d for d, _ in active).values()):
        reasons.append("Hai phụ lục cùng ngày hiệu lực; cần chốt thứ tự áp dụng.")
    return [p for _, p in sorted(active, key=lambda item: item[0])], reasons


def boq_tai_ngay(phu_luc, boq_dong, ngay):
    """Projection thuần một HĐ; mơ hồ trả boq=None để không dùng kết quả dở.

    Chỉ PL Đã ký và đã hiệu lực được áp. Cờ không tiết lộ ID nội bộ.
    Danh sách đầu ra giữ thứ tự dòng GOC, dòng THEM nối theo thứ tự nguồn.
    """
    active, reasons = _phu_luc_tai_ngay(phu_luc, ngay)
    parents = {p["id"]: p for p in phu_luc}
    if len(parents) != len(phu_luc):
        reasons.append("Trùng khóa phụ lục nguồn.")
    lines, changes = {}, {}
    for row in sorted(boq_dong, key=lambda r: r["id"]):
        parent, op, code = row.get("pl_id"), row.get("thao_tac"), row["ma_hm"]
        if parent is None:
            if op != "GOC" or code in lines:
                reasons.append("BOQ gốc trùng mã hoặc sai thao tác.")
            else:
                lines[code] = dict(_dto(row, _BOQ_DTO), nguon="HĐ gốc")
        elif parent not in parents:
            reasons.append("BOQ thiếu phụ lục nguồn.")
        else:
            changes.setdefault(parent, []).append(row)
    for pl in active:
        seen = set()
        for row in changes.get(pl["id"], []):
            code, op = row["ma_hm"], row.get("thao_tac")
            if code in seen:
                reasons.append("Trùng mã hạng mục trong cùng phụ lục.")
                continue
            seen.add(code)
            if op == "THEM" and code not in lines:
                lines[code] = dict(_dto(row, _BOQ_DTO), nguon=pl["so_pl"])
            elif op == "THAY" and code in lines:
                patch = _dto(row, _THAY)
                lines[code].update({k: v for k, v in patch.items() if v not in (None, "")})
                lines[code]["nguon"] = pl["so_pl"]
            elif op == "BO" and code in lines:
                lines.pop(code)
            else:
                reasons.append("Thao tác BOQ không khớp hạng mục đang hiệu lực.")
    return {"boq": None if reasons else list(lines.values()),
            "can_xem_lai": bool(reasons), "ly_do": list(dict.fromkeys(reasons))}


def dto_phu_luc(phu_luc, thay_doi_tham_so, boq_dong, ngay):
    """Allowlist; thay đổi nằm trong từng phiên PL, kể cả PL đã hủy trùng số.

    Không xuất phieu JSON thô, file, vị trí/đường dẫn, actor nạp, ID/hash.
    gt_hd_sau_pl trên từng PL luôn là số nguồn; giá trị tại ngày là số của
    PL cuối có hiệu lực, kể cả NULL, không fallback/cộng lại.
    """
    projection = boq_tai_ngay(phu_luc, boq_dong, ngay)
    active, reasons = _phu_luc_tai_ngay(phu_luc, ngay)
    changes = {}
    for row in thay_doi_tham_so:
        changes.setdefault(row["pl_id"], []).append(_dto(row, _TS_DTO))
    result = []
    for row in phu_luc:
        value = _dto(row, _PL_DTO)
        value["thay_doi_tham_so"] = changes.get(row["id"], [])
        result.append(value)
    return dict(projection, phu_luc=result,
                gt_hd_sau_pl=real_sang_decimal(active[-1].get("gt_hd_sau_pl")) if active and not reasons else None)


def _chuan_bi(du_lieu, contracts):
    if not isinstance(du_lieu, Mapping) or set(du_lieu) != set(_COT):
        _sai("Phải truyền đủ đúng phu_luc, thay_doi_tham_so, boq_dong; [] cho bảng rỗng.")
    prepared = {}
    for table, columns in _COT.items():
        if not isinstance(du_lieu[table], (list, tuple)):
            _sai(f"{table} phải là danh sách dòng nguồn.")
        rows = {}
        for original in du_lieu[table]:
            if not isinstance(original, Mapping) or set(original) - set(columns):
                _sai(f"{table} có cột lạ; không bỏ chứng cứ âm thầm.")
            row = {c: original.get(c) for c in columns}
            for col, value in row.items():
                if col in _NUMERIC:
                    row[col] = real_sang_decimal(value)
                elif col in _INTEGER:
                    if value is not None and (type(value) is not int or not -(2**63) <= value < 2**63):
                        _sai(f"{table}.{col} cần INTEGER 64-bit hoặc NULL.")
                elif value is not None and not isinstance(value, str):
                    _sai(f"{table}.{col} cần TEXT hoặc NULL.")
            required = list(_PK[table])
            if table == "phu_luc":
                required += ["ma_hd", "so_pl", "ngay_ky", "ngay_hieu_luc", "doi_boq", "trang_thai"]
            if table == "boq_dong":
                required += ["ma_hd", "ma_hm", "thao_tac"]
                if row["thao_tac"] not in ("GOC", "THAY", "THEM", "BO"):
                    _sai("Thao tác BOQ ngoài hợp đồng nguồn.")
            if any(row[c] is None for c in required):
                _sai(f"{table} thiếu cột bắt buộc.")
            if table == "thay_doi_tham_so":
                parent = prepared["phu_luc"].get((row["pl_id"],))
                if parent is None:
                    _sai("Thay đổi tham số thiếu PL trong cùng lần chụp.")
                row["du_an_id"] = parent["du_an_id"]
            else:
                contract = contracts.get(row["ma_hd"])
                if contract is None:
                    raise DataError("M4_REVIEW_THIEU_ANH_XA", "Thiếu HĐ đã ánh xạ trong cùng lần chụp; dừng cả lần chụp.")
                row.update(hop_dong_id=str(contract["hop_dong_id"]), du_an_id=str(contract["du_an_id"]))
                if table == "boq_dong" and row["pl_id"] is not None:
                    parent = prepared["phu_luc"].get((row["pl_id"],))
                    if parent is None or parent["ma_hd"] != row["ma_hd"]:
                        _sai("BOQ thiếu PL cùng HĐ trong lần chụp.")
            key = tuple(row[c] for c in _PK[table])
            if key in rows:
                _sai(f"Trùng khóa nguồn {table}.")
            rows[key] = dict(row, dong_sha256=dong_sha256(row))
        prepared[table] = rows
    return prepared


class ReviewPhuLucPG:
    """Repository hai kết nối; tự kiểm quyền phiên trước mọi lần đọc owner."""

    def __init__(self, conn_tin_cay):
        if conn_tin_cay is None:
            _sai("Thiếu kết nối chủ bảng tin cậy.")
        self.conn = conn_tin_cay

    def ghi_lan_chup(self, du_lieu, *, du_lieu_dl2, **metadata):
        """Kết hợp public API DL2 và DL3 trong một transaction/savepoint.

        metadata giống ReviewDataPG.ghi_lan_chup. Trả tổng dòng mới (gồm
        nguồn); replay trả 0. Lỗi DL3 rollback cả dữ liệu DL2 vừa ghi.
        Chưa thay thế công cụ chụp đủ 12 bảng thuộc các lát khác.
        """
        with self.conn.transaction():
            added = ReviewDataPG(self.conn).ghi_lan_chup(du_lieu_dl2, **metadata)
            return added + self.ghi_trong_giao_dich(
                du_lieu, nguon_id=metadata["nguon_id"],
                nhap_boi=metadata["nhap_boi"], replay=(added == 0))

    def ghi_trong_giao_dich(self, du_lieu, *, nguon_id, nhap_boi, replay):
        """Không commit/mở transaction; DL2 đã ghi trên cùng conn đang mở.

        replay lấy từ số dòng mới DL2 == 0, BẮT BUỘC truyền rõ; replay so
        nguyên tập khóa/hash kể cả khi cả ba bảng rỗng. Caller phải để lỗi
        thoát transaction ngoài. Không dùng để bổ sung vào nguồn cũ DL2.
        """
        if getattr(getattr(self.conn, "info", None), "transaction_status", None) != 2:
            _sai("DL3 cần cùng conn trong transaction đang mở của lần chụp DL2.")
        if type(replay) is not bool:
            _sai("replay phải là bool từ kết quả ghi DL2.")
        self.conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (nguon_id,))
        source = _rows(self.conn, "SELECT nhap_boi FROM m4.review_chep_nguon WHERE id=%s FOR UPDATE", (nguon_id,))
        if not source or source[0]["nhap_boi"] != nhap_boi:
            _sai("Thiếu nguồn DL2 hoặc người nhập không khớp lần chụp.")
        contracts = _rows(self.conn, "SELECT ma_hd,hop_dong_id,du_an_id FROM m4.review_chep_hop_dong WHERE nguon_id=%s", (nguon_id,))
        prepared = _chuan_bi(du_lieu, {r["ma_hd"]: r for r in contracts})
        for table, rows in prepared.items():
            pk = _PK[table]
            existing = _rows(self.conn, f"SELECT {','.join(pk)},dong_sha256 FROM m4.review_chep_{table} WHERE nguon_id=%s", (nguon_id,))
            actual = {tuple(r[c] for c in pk): r["dong_sha256"] for r in existing}
            if (replay and actual != {k: r["dong_sha256"] for k, r in rows.items()}) or (not replay and actual):
                _khac(table)
        added = 0
        for table, rows in prepared.items():
            for row in rows.values():
                values = dict(row, nguon_id=nguon_id, nhap_boi=nhap_boi)
                cols = ",".join(values)
                placeholders = ",".join("%s" for _ in values)
                conflict = ",".join(("nguon_id", *_PK[table]))
                added += self.conn.execute(
                    f"INSERT INTO m4.review_chep_{table} ({cols}) VALUES ({placeholders}) ON CONFLICT ({conflict}) DO NOTHING",
                    tuple(values.values())).rowcount
        return added

    def doc_hien_hanh(self, hop_dong_id, *, ngay, conn_phien):
        """Ghim nguồn qua hàm DL1b; không lùi về lần chụp còn PL/HĐ cũ.

        Dùng kiểm XEM/REVIEW của DL2 theo master.hop_dong.du_an_id trên phiên;
        không thấy/không quyền/UUID sai cùng M4_REVIEW_KHONG_THAY (HTTP 404).
        Chấp nhận khe hở kiểm quyền phiên → đọc chủ bảng như DL2: quyền xét
        tại lúc kiểm, bản chụp chỉ đọc/bất biến; thu hồi đồng thời có hiệu lực
        từ lần kiểm tiếp theo. Không bảo đảm nguyên tử giữa hai kết nối.
        Ba trạng thái NULL được xác định trong cùng một SELECT của DL2.
        """
        reader = ReviewDataPG(self.conn)
        hop_dong_id = reader._kiem_quyen_doc(hop_dong_id, conn_phien=conn_phien)
        _ngay(ngay)
        with self.conn.transaction():
            source, state = reader._nguon_hien_hanh(hop_dong_id)
            if source is None:
                return dict(dto_phu_luc([], [], [], ngay), trang_thai=state)
            params = (source, str(hop_dong_id))
            pls = _rows(self.conn, "SELECT * FROM m4.review_chep_phu_luc WHERE nguon_id=%s AND hop_dong_id=%s::uuid ORDER BY id", params)
            changes = _rows(self.conn, """SELECT t.* FROM m4.review_chep_thay_doi_tham_so t
                JOIN m4.review_chep_phu_luc p ON (p.nguon_id,p.id)=(t.nguon_id,t.pl_id)
                WHERE p.nguon_id=%s AND p.hop_dong_id=%s::uuid ORDER BY t.pl_id,t.ma_ts""", params)
            lines = _rows(self.conn, "SELECT * FROM m4.review_chep_boq_dong WHERE nguon_id=%s AND hop_dong_id=%s::uuid ORDER BY id", params)
            return dict(dto_phu_luc(pls, changes, lines, ngay), trang_thai="HIEN_HANH")
