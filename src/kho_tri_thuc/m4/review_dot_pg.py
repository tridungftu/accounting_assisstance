"""M4-DL4 — đợt/KL/ghép/cảnh báo/nhật ký legacy của bản chụp Review.

Chỉ nhận dòng đã đọc sẵn và connection do máy chủ tiêm; không mở tệp/DSN.
ghi_lan_chup nối public API DL3 → DL2 rồi DL4 trên cùng transaction, đủ
12 bảng (bảng rỗng vẫn phải truyền []). Công cụ nạp có transaction sẵn có
thể gọi ghi_trong_giao_dich; lỗi phải thoát transaction ngoài để rollback
cả lần chụp. Không nối thêm dữ liệu vào nguồn cũ, không sửa audit.

Ngày/JSON/nhật ký giữ TEXT nguyên văn, REAL thành Decimal(repr), NULL giữ
NULL. Ghép/cảnh báo/log mồ côi vẫn lưu, hai UUID ánh xạ đều NULL, chỉ owner
đọc được; không suy dự án từ ánh xạ của HĐ vắng trong lần chụp. Không tạo
actor lịch sử, run, đợt vận hành hay seal; DA_NOP không là chứng cứ duyệt.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..ha_tang.primitives import DataError
from .review_data_pg import ReviewDataPG, dong_sha256, real_sang_decimal
from .review_phu_luc_pg import ReviewPhuLucPG


_COT = {
    "dot_thanh_toan": (
        "ma_hd", "dot", "ngay_nghiem_thu", "ngay_nhan_hs", "gt_ky",
        "gt_luy_ke", "giu_lai", "thu_hoi_tu", "gt_tt_ky", "file_nguon", "ngay_nap",
    ),
    "kl_thanh_toan": (
        "ma_hd", "dot", "ma_hm", "kl_ky", "kl_luy_ke", "don_gia_tt", "vi_tri_nguon",
    ),
    "khop_hang_muc": ("ma_hd", "khoa_hstt", "ma_hm", "cach_khop", "nguoi_xac_nhan", "ngay"),
    "canh_bao": ("id", "ma_hd", "pl_id", "dot", "ma_kt", "muc_do", "noi_dung", "thoi_diem"),
    "nhat_ky": ("id", "thoi_diem", "nguoi", "thao_tac", "ma_hd", "chi_tiet"),
}
_PK = {
    "dot_thanh_toan": ("ma_hd", "dot"),
    "kl_thanh_toan": ("ma_hd", "dot", "ma_hm"),
    "khop_hang_muc": ("ma_hd", "khoa_hstt"),
    "canh_bao": ("id",), "nhat_ky": ("id",),
}
_NUMERIC = {"gt_ky", "gt_luy_ke", "giu_lai", "thu_hoi_tu", "gt_tt_ky",
            "kl_ky", "kl_luy_ke", "don_gia_tt"}
_INTEGER = {"id", "pl_id", "dot"}
_DTO = {
    "dot_thanh_toan": ("dot", "ngay_nghiem_thu", "ngay_nhan_hs", "gt_ky",
                       "gt_luy_ke", "giu_lai", "thu_hoi_tu", "gt_tt_ky", "ngay_nap"),
    "kl_thanh_toan": ("dot", "ma_hm", "kl_ky", "kl_luy_ke", "don_gia_tt"),
    "khop_hang_muc": ("ma_hm", "cach_khop", "nguoi_xac_nhan", "ngay"),
    "canh_bao": ("dot", "ma_kt", "muc_do", "noi_dung", "thoi_diem"),
    "nhat_ky": ("thoi_diem", "nguoi", "thao_tac", "chi_tiet"),
}


def _sai(message):
    raise DataError("M4_REVIEW_DU_LIEU_SAI", message)


def _khac(table):
    raise DataError("M4_REVIEW_REPLAY_KHAC",
                    f"Tập khóa/dong_sha256 khác ở {table}; không ghi đè lần chụp.")


def _rows(conn, query, params=()):
    cur = conn.execute(query, params)
    names = [c.name for c in cur.description]
    return [dict(r) if isinstance(r, Mapping) else dict(zip(names, r)) for r in cur.fetchall()]


def doc_lich_su_chep(conn_phien, hop_dong_id):
    """Đọc trên đúng connection/transaction bên gọi, không mở đường owner.

    02C đang dùng transaction chủ bảng có danh tính phiên: kiểm XEM tường
    minh cả khi owner bỏ qua RLS. Login thường vẫn chịu RLS. Metadata nguồn
    hiện chưa grant app_web: thiếu quyền SQL trả None, không thử đọc thay
    bằng connection khác. Ba trạng thái NULL của bản hiện hành đều là None.
    Không trả đường dẫn nguồn, không suy trạng thái đã duyệt.
    """
    allowed = _rows(conn_phien, """SELECT EXISTS (
        SELECT 1 FROM master.hop_dong h WHERE h.id=%s::uuid
          AND h.module_chu='M4' AND master.m4_duoc(h.du_an_id,'XEM')
        ) AS duoc""", (hop_dong_id,))
    if not allowed or not allowed[0]["duoc"]:
        return None
    tables = ("review_chep_nguon", "review_chep_hop_dong",
              "review_chep_dot_thanh_toan", "review_chep_kl_thanh_toan")
    for table in tables:
        access = _rows(conn_phien, """SELECT CASE WHEN to_regclass(%s) IS NULL THEN false
            ELSE has_table_privilege(to_regclass(%s), 'SELECT') END AS duoc""",
                       ("m4." + table, "m4." + table))
        if not access[0]["duoc"]:
            return None
    source = _rows(conn_phien, "SELECT m4.review_chep_hien_hanh(%s::uuid) AS nguon_id", (hop_dong_id,))
    if not source or source[0]["nguon_id"] is None:
        return None
    params = (source[0]["nguon_id"], hop_dong_id)
    dots = _rows(conn_phien, """SELECT d.dot, d.m4_dot_id, m.so_dot AS m4_so_dot
        FROM m4.review_chep_dot_thanh_toan d LEFT JOIN m4.dot m
          ON m.id=d.m4_dot_id AND m.hop_dong_id=d.hop_dong_id
        WHERE d.nguon_id=%s AND d.hop_dong_id=%s::uuid ORDER BY d.dot""", params)
    rows = _rows(conn_phien, """SELECT k.dot,k.ma_hm,k.kl_ky,k.kl_luy_ke
        FROM m4.review_chep_kl_thanh_toan k JOIN m4.review_chep_dot_thanh_toan d
          ON (d.nguon_id,d.ma_hd,d.dot)=(k.nguon_id,k.ma_hd,k.dot)
        WHERE d.nguon_id=%s AND d.hop_dong_id=%s::uuid ORDER BY k.dot,k.ma_hm""", params)
    return {"dot": dots, "dong": rows}


def chuan_bi_dong(du_lieu, contracts):
    """Chuẩn hóa đủ năm bảng, FK nguồn và hash; không sửa dict đầu vào.

    contracts là các HĐ DL2 đã ghi của chính lần chụp. Không nhận UUID/actor
    từ dòng nguồn; dòng không có FK nguồn được giữ kể cả ma_hd NULL/rỗng.
    """
    if not isinstance(du_lieu, Mapping) or set(du_lieu) != set(_COT):
        _sai("Phải truyền đủ đúng năm bảng DL4; [] cho bảng rỗng.")
    if not isinstance(contracts, Mapping):
        _sai("Thiếu các HĐ đã ánh xạ trong cùng lần chụp.")
    prepared = {}
    for table, columns in _COT.items():
        if not isinstance(du_lieu[table], (list, tuple)):
            _sai(f"{table} phải là danh sách dòng nguồn.")
        rows = {}
        for original in du_lieu[table]:
            if not isinstance(original, Mapping) or set(original) - set(columns):
                _sai(f"{table} có cột lạ hoặc không phải dict; không bỏ chứng cứ.")
            row = {c: original.get(c) for c in columns}
            for col, value in row.items():
                if col in _NUMERIC:
                    row[col] = real_sang_decimal(value)
                elif col in _INTEGER:
                    if value is not None and (type(value) is not int or not -(2**63) <= value < 2**63):
                        _sai(f"{table}.{col} cần INTEGER 64-bit hoặc NULL.")
                elif value is not None and not isinstance(value, str):
                    _sai(f"{table}.{col} cần TEXT hoặc NULL nguyên văn.")
            required = (*_PK[table], *(("ma_hm",) if table == "khop_hang_muc" else ()))
            if any(row[c] is None for c in required):
                _sai(f"{table} thiếu khóa/cột bắt buộc.")
            contract = contracts.get(row.get("ma_hd"))
            if table == "kl_thanh_toan":
                parent = prepared["dot_thanh_toan"].get((row["ma_hd"], row["dot"]))
                if parent is None:
                    _sai("Khối lượng thiếu đợt cùng HĐ trong lần chụp.")
                row["du_an_id"] = parent["du_an_id"]
            elif contract is not None:
                row.update(hop_dong_id=str(contract["hop_dong_id"]),
                           du_an_id=str(contract["du_an_id"]))
            elif table == "dot_thanh_toan":
                raise DataError("M4_REVIEW_THIEU_ANH_XA",
                                "Đợt thiếu HĐ đã ánh xạ trong cùng lần chụp; dừng cả lần chụp.")
            else:
                row.update(hop_dong_id=None, du_an_id=None)
            key = tuple(row[c] for c in _PK[table])
            if key in rows:
                _sai(f"Trùng khóa nguồn {table}.")
            rows[key] = dict(row, dong_sha256=dong_sha256(row))
        prepared[table] = rows
    return prepared


def dto_dot(dot_thanh_toan, kl_thanh_toan, khop_hang_muc, canh_bao, nhat_ky):
    """Allowlist, không tính lại số liệu hoặc suy trạng thái duyệt.

    dot/ma_hm/ma_kt là số/mã nghiệp vụ. Không xuất PK id/ma_hd/pl_id,
    khoa_hstt, UUID/hash, vị trí/tệp hay người nạp. Người xác nhận và người
    ghi nhật ký chỉ là TEXT lịch sử, không phải danh tính phiên hệ thống.
    chi_tiet giữ nguyên TEXT, không parse JSON, không suy timezone.
    """
    source = dict(zip(_COT, (dot_thanh_toan, kl_thanh_toan, khop_hang_muc, canh_bao, nhat_ky)))
    return {table: [{c: real_sang_decimal(r.get(c)) if c in _NUMERIC else r.get(c)
                     for c in _DTO[table]} for r in rows]
            for table, rows in source.items()}


class ReviewDotPG:
    """Hai connection như DL2/DL3; kiểm quyền trước mọi truy vấn owner đọc."""

    def __init__(self, conn_tin_cay):
        if conn_tin_cay is None:
            _sai("Thiếu kết nối chủ bảng tin cậy.")
        self.conn = conn_tin_cay

    def ghi_lan_chup(self, du_lieu, *, du_lieu_dl2, du_lieu_dl3, **metadata):
        """Ghi đủ 12 bảng trong một transaction/savepoint; replay trả 0.

        metadata theo public API ReviewDataPG.ghi_lan_chup. Lỗi bất kỳ
        lớp nào rollback cả nguồn/DL2/DL3/DL4, kể cả transaction lồng nhau.
        """
        with self.conn.transaction():
            added = ReviewPhuLucPG(self.conn).ghi_lan_chup(
                du_lieu_dl3, du_lieu_dl2=du_lieu_dl2, **metadata)
            return added + self.ghi_trong_giao_dich(
                du_lieu, nguon_id=metadata["nguon_id"],
                nhap_boi=metadata["nhap_boi"], replay=(added == 0))

    def ghi_trong_giao_dich(self, du_lieu, *, nguon_id, nhap_boi, replay):
        """DL2/DL3 đã ghi trên cùng conn; caller để lỗi thoát transaction.

        replay bắt buộc lấy từ số dòng mới của DL2 == 0 (DL3 cũng phải
        khớp), so cả năm tập khóa/hash kể cả bảng rỗng, không nạp bổ sung.
        """
        if getattr(getattr(self.conn, "info", None), "transaction_status", None) != 2:
            _sai("DL4 cần cùng conn trong transaction đang mở của lần chụp DL2/DL3.")
        if type(replay) is not bool:
            _sai("replay phải là bool từ kết quả ghi DL2.")
        self.conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (nguon_id,))
        source = _rows(self.conn, "SELECT nhap_boi FROM m4.review_chep_nguon WHERE id=%s FOR UPDATE", (nguon_id,))
        if not source or source[0]["nhap_boi"] != nhap_boi:
            _sai("Thiếu nguồn DL2 hoặc người nhập không khớp lần chụp.")
        contracts = _rows(self.conn, "SELECT ma_hd,hop_dong_id,du_an_id FROM m4.review_chep_hop_dong WHERE nguon_id=%s", (nguon_id,))
        prepared = chuan_bi_dong(du_lieu, {r["ma_hd"]: r for r in contracts})
        for table, rows in prepared.items():
            existing = _rows(self.conn, f"SELECT {','.join(_PK[table])},dong_sha256 FROM m4.review_chep_{table} WHERE nguon_id=%s", (nguon_id,))
            actual = {tuple(r[c] for c in _PK[table]): r["dong_sha256"] for r in existing}
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

    def doc_hien_hanh(self, hop_dong_id, *, conn_phien=None):
        """Chỉ cho XEM; lịch sử đợt chưa nộp không được mở cho REVIEW.

        Năm bảng DL1 chỉ cho XEM; REVIEW chỉ thấy đợt DA_NOP ở M4 hiện hành.
        Dùng kiểm chung và ba trạng thái NULL của DL2 như DL3.
        Thiếu phiên/không quyền/UUID sai: M4_REVIEW_KHONG_THAY (HTTP 404).
        Chấp nhận khe hở hai connection như DL2: quyền xét tại lần kiểm;
        thu hồi đồng thời có hiệu lực ở lần kiểm tiếp theo. Ghim đúng
        nguon_id toàn bộ mới nhất, không lùi về đợt còn ở bản cũ.
        """
        reader = ReviewDataPG(self.conn)
        hop_dong_id = reader._kiem_quyen_doc(hop_dong_id, conn_phien=conn_phien)
        allowed = conn_phien.execute("""SELECT EXISTS (
            SELECT 1 FROM master.hop_dong h
            WHERE h.id=%s::uuid AND h.module_chu='M4'
              AND master.m4_duoc(h.du_an_id, 'XEM')
            ) AS duoc""", (hop_dong_id,)).fetchone()
        if not (allowed["duoc"] if isinstance(allowed, Mapping) else allowed[0]):
            raise DataError("M4_REVIEW_KHONG_THAY", "Không tìm thấy hợp đồng.")
        with self.conn.transaction():
            source, state = reader._nguon_hien_hanh(hop_dong_id)
            if source is None:
                return dict(dto_dot([], [], [], [], []), trang_thai=state)
            params = (source, hop_dong_id)
            data = {}
            for table in _COT:
                if table == "kl_thanh_toan":
                    data[table] = _rows(self.conn, """SELECT k.* FROM m4.review_chep_kl_thanh_toan k
                        JOIN m4.review_chep_dot_thanh_toan d
                          ON (d.nguon_id,d.ma_hd,d.dot)=(k.nguon_id,k.ma_hd,k.dot)
                        WHERE d.nguon_id=%s AND d.hop_dong_id=%s::uuid
                        ORDER BY k.dot,k.ma_hm""", params)
                else:
                    order = {"dot_thanh_toan": "dot", "khop_hang_muc": "khoa_hstt",
                             "canh_bao": "id", "nhat_ky": "id"}[table]
                    data[table] = _rows(self.conn, f"SELECT * FROM m4.review_chep_{table} WHERE nguon_id=%s AND hop_dong_id=%s::uuid ORDER BY {order}", params)
            return dict(dto_dot(**data), trang_thai="HIEN_HANH")
