"""M4-DL2 — repository bản chụp Review với hai kết nối được máy chủ tiêm.

Không mở DSN/SQLite/tệp, không tạo hồ sơ vận hành hay bản trích giả. Lớp đọc
tự kiểm XEM/REVIEW theo dự án HĐ trên kết nối phiên người dùng thường trước
khi đọc bảng chép bằng kết nối chủ bảng; không quyền/không thấy cùng lỗi 404.
Một nguon_id là một lần chụp đủ của cùng một CSDL Review, theo hợp đồng DL1b.
Lát này nhận đúng bốn bảng nguồn che_do/hop_dong/tham_so/tham_so_nguon
(mỗi bảng là list[dict], kể cả rỗng); các bảng Review khác thuộc lát sau.

Hash SHA-256 trên JSON UTF-8: khóa dict sắp xếp, separators=(',', ':'),
ensure_ascii=False, allow_nan=False; mỗi giá trị có nhãn kiểu để không lẫn
NULL/chuỗi/số. Chuỗi giữ nguyên cả Unicode/khoảng trắng/ngày TEXT. float
thành Decimal(repr(x)); Decimal hữu hạn viết dạng fixed, bỏ zero thập phân
thừa, -0 thành 0 (không dùng normalize phụ thuộc decimal context). Trước khi hash dòng
ghi, điền cột tùy chọn thiếu bằng NULL/default nguồn, chuẩn hóa numeric và
UUID ánh xạ; hash gồm mọi cột nguồn và hai UUID ánh xạ, không gồm nguon_id,
actor nạp, thời điểm nạp, chep_id hay hash. Metadata nguồn được đối chiếu
riêng vì review_chep_nguon không có cột dong_sha256. Không tự suy timezone.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

from ..ha_tang.primitives import DataError


# Integration owner dùng khi nối route, cùng quy ước ke_toan_nghiem_thu.
MA_HTTP = {"M4_REVIEW_KHONG_THAY": 404}


_COT = {
    "che_do": ("id", "sua"),
    "hop_dong": (
        "ma_hd", "so_hd", "phan_loai", "loai_gia", "ngay_ky", "goi_thau",
        "gia_tri_hd", "gom_vat", "vat", "file_nguon", "ngay_nap",
    ),
    "tham_so": (
        "ma_hd", "ma_ts", "ten", "gia_tri", "don_vi", "dieu_khoan",
        "trich_dan", "trang_thai",
    ),
    "tham_so_nguon": (
        "ma_hd", "ma_ts", "gia_tri_ai", "gia_tri", "kiem_tra", "muc", "nguon",
        "da_xac_nhan", "da_sua_tay", "nguoi_xac_nhan", "luc_xac_nhan",
        "ghi_chu_soat", "lich_su", "model", "may_ai", "luot", "file_hop_dong",
        "sha1_file", "luc_trich", "luc_nap",
    ),
}
_PK = {"che_do": ("id",), "hop_dong": ("ma_hd",),
       "tham_so": ("ma_hd", "ma_ts"), "tham_so_nguon": ("ma_hd", "ma_ts")}
_DEFAULT = {"sua": 0, "da_xac_nhan": 0, "da_sua_tay": 0}
_SO_NGUYEN = {"id", "sua", "muc", "da_xac_nhan", "da_sua_tay"}
_NUMERIC = {"gia_tri_hd", "vat"}
_HD_DTO = ("so_hd", "phan_loai", "loai_gia", "ngay_ky", "goi_thau",
           "gia_tri_hd", "gom_vat", "vat", "ngay_nap")
_TS_DTO = ("ma_ts", "ten", "gia_tri", "don_vi", "dieu_khoan", "trich_dan", "trang_thai")
_NGUON_DTO = ("ma_ts", "gia_tri_ai", "gia_tri", "kiem_tra", "muc", "nguon",
              "da_xac_nhan", "da_sua_tay", "nguoi_xac_nhan", "luc_xac_nhan",
              "ghi_chu_soat", "luc_trich", "luc_nap")


def _sai(message):
    raise DataError("M4_REVIEW_DU_LIEU_SAI", message)


def real_sang_decimal(value):
    """REAL → numeric bằng Decimal(repr); không đổi NULL, không nhận NaN/Inf."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        _sai("Số nguồn phải là INTEGER, REAL hoặc Decimal hữu hạn.")
    result = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    if not result.is_finite():
        _sai("Số nguồn NaN/Infinity chưa có quy tắc chuyển đổi; dừng lần chụp.")
    return result


def _chuan_hash(value):
    if value is None:
        return ["null"]
    if isinstance(value, str):
        return ["text", value]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["integer", str(value)]
    if isinstance(value, (float, Decimal)):
        decimal = real_sang_decimal(value)
        number = "0" if decimal.is_zero() else format(decimal, "f")
        if "." in number:
            number = number.rstrip("0").rstrip(".")
        return ["decimal", number]
    if isinstance(value, Mapping) and all(isinstance(k, str) for k in value):
        return ["object", {k: _chuan_hash(v) for k, v in value.items()}]
    if isinstance(value, (list, tuple)):
        return ["array", [_chuan_hash(v) for v in value]]
    _sai("Kiểu dữ liệu không được hỗ trợ khi băm dòng nguồn.")


def dong_sha256(row: Mapping) -> str:
    """Băm ổn định theo hợp đồng đầu module; không sửa dữ liệu đầu vào."""
    raw = json.dumps(_chuan_hash(row), ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def dto_man_hinh(hop_dong, tham_so, tham_so_nguon, *, trang_thai=None):
    """Allowlist; mã tham số là mã nghiệp vụ, không xuất ma_hd/UUID/hash/login nạp.

    Nguồn gốc giữ riêng từng ô, kể cả ô chưa có dòng tham_so và ngược lại.
    nguoi_xac_nhan là nguyên văn chứng cứ nguồn, không lấy từ login phiên.
    Không trả lich_su JSON thô/model/máy/lượt vì có thể chứa định danh nội bộ.
    Không ép 36/37 mã, không điền ô giả khi nguồn thiếu.
    HĐ NULL phải có trạng thái do lớp đọc phân biệt sau kiểm quyền: chưa nạp,
    chưa từng có HĐ trong nguồn, hoặc đã xóa ở lần chụp mới nhất.
    """
    if hop_dong is None:
        messages = {
            "CHUA_CO_LAN_CHUP": "Chưa nạp dữ liệu Review.",
            "CHUA_CO_TRONG_NGUON": "Hợp đồng chưa có trong dữ liệu Review.",
            "DA_XOA_O_NGUON": "Hợp đồng đã bị xóa ở dữ liệu Review (lần chụp mới nhất).",
        }
        if trang_thai not in messages:
            _sai("HĐ nguồn NULL phải có trạng thái thiếu dữ liệu Review rõ ràng.")
        return {"trang_thai": trang_thai, "thong_bao": messages[trang_thai], "hop_dong": None,
                "tham_so": [], "tham_so_nguon": []}
    hd = {k: hop_dong.get(k) for k in _HD_DTO}
    for k in _NUMERIC:
        hd[k] = real_sang_decimal(hd[k])
    return {"trang_thai": "HIEN_HANH", "hop_dong": hd,
            "tham_so": [{k: r.get(k) for k in _TS_DTO} for r in tham_so],
            "tham_so_nguon": [{k: r.get(k) for k in _NGUON_DTO} for r in tham_so_nguon]}


def _thoi_diem(value):
    try:
        moment = datetime.fromisoformat(value) if isinstance(value, str) else value
        if not isinstance(moment, datetime) or moment.tzinfo is None or moment.utcoffset() is None:
            _sai("chup_luc bắt buộc là datetime/ISO có múi giờ rõ ràng.")
        return moment.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        _sai("chup_luc không hợp lệ.")


class ReviewDataPG:
    """conn_tin_cay: psycopg owner connection do máy chủ tiêm, không nhận DSN.

    Hỗ trợ tuple_row và dict_row. Không commit giao dịch bên ngoài nếu caller
    đã mở transaction; _tx khi đó là savepoint, lỗi rollback toàn bộ lần chụp.
    Caller không thay snapshot đồng thời qua SQL ngoài repository.
    """

    def __init__(self, conn_tin_cay):
        if conn_tin_cay is None:
            _sai("Thiếu kết nối chủ bảng tin cậy cho Review.")
        self.conn = conn_tin_cay

    @contextmanager
    def _tx(self):
        with self.conn.transaction():
            yield

    def _rows(self, query, params=()):
        cur = self.conn.execute(query, params)
        names = [c.name for c in cur.description]
        return [dict(r) if isinstance(r, Mapping) else dict(zip(names, r)) for r in cur.fetchall()]

    @staticmethod
    def _chuan_bi(du_lieu, anh_xa):
        if not isinstance(du_lieu, Mapping) or set(du_lieu) != set(_COT):
            _sai("Phải truyền đủ đúng bốn bảng che_do, hop_dong, tham_so, tham_so_nguon; dùng [] cho bảng rỗng.")
        if not isinstance(anh_xa, Mapping):
            _sai("Thiếu bảng ánh xạ ma_hd → (hop_dong_id, du_an_id) đã chốt.")
        result = {}
        hd_da_anh_xa = {}
        for table, columns in _COT.items():
            if not isinstance(du_lieu[table], (list, tuple)):
                _sai(f"Bảng {table} phải là danh sách dòng đã đọc sẵn.")
            rows = {}
            for original in du_lieu[table]:
                if not isinstance(original, Mapping) or set(original) - set(columns):
                    _sai(f"Dòng {table} có cột lạ hoặc không phải dict; không bỏ chứng cứ âm thầm.")
                row = {c: original.get(c, _DEFAULT.get(c)) for c in columns}
                for c, v in row.items():
                    if c in _NUMERIC:
                        row[c] = real_sang_decimal(v)
                    elif c in _SO_NGUYEN:
                        if v is not None and (type(v) is not int or not -(2**63) <= v < 2**63):
                            _sai(f"{table}.{c} phải là INTEGER 64-bit hoặc NULL.")
                    elif v is not None and not isinstance(v, str):
                        _sai(f"{table}.{c} phải giữ TEXT hoặc NULL của nguồn.")
                required = (*_PK[table], *(('so_hd',) if table == 'hop_dong' else ()))
                if any(row[k] is None for k in required):
                    _sai(f"Dòng {table} thiếu khóa hoặc so_hd bắt buộc.")
                if table != "che_do":
                    ma_hd = row["ma_hd"]
                    if ma_hd not in anh_xa:
                        raise DataError("M4_REVIEW_THIEU_ANH_XA", "Thiếu ánh xạ ma_hd đã chốt; dừng cả lần chụp.")
                    pair = anh_xa[ma_hd]
                    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                        _sai("Ánh xạ phải gồm đúng hop_dong_id, du_an_id.")
                    try:
                        row["hop_dong_id"], row["du_an_id"] = (str(uuid.UUID(str(v))) for v in pair)
                    except (ValueError, TypeError, AttributeError):
                        _sai("UUID trong bảng ánh xạ không hợp lệ.")
                    mapped = row["hop_dong_id"]
                    if mapped in hd_da_anh_xa and hd_da_anh_xa[mapped] != ma_hd:
                        _sai("Hai ma_hd ánh xạ vào cùng hop_dong_id; dừng cả lần chụp.")
                    hd_da_anh_xa[mapped] = ma_hd
                key = tuple(row[c] for c in _PK[table])
                if key in rows:
                    _sai(f"Trùng khóa nguồn trong bảng {table}.")
                rows[key] = dict(row, dong_sha256=dong_sha256(row))
            result[table] = rows
        contracts = {key[0] for key in result["hop_dong"]}
        for table in ("tham_so", "tham_so_nguon"):
            if any(key[0] not in contracts for key in result[table]):
                _sai(f"{table} trỏ tới HĐ không có trong cùng lần chụp.")
        return result

    def ghi_lan_chup(self, du_lieu, *, nguon_id, chup_luc, nhap_boi, anh_xa, mo_ta=None):
        """Ghi nguyên tử năm bảng; replay phải khớp cả tập khóa/hash/metadata.

        Không nối thêm/bớt dòng vào nguon_id đã có. Cột tùy chọn thiếu có
        nghĩa NULL (ba cờ INTEGER mặc định 0), khác với chuỗi rỗng. Không
        nhận m4_ma: không tự liên kết bản tham số vận hành. Trả số dòng mới
        (kể cả nguồn); replay trả 0. Lỗi DB được truyền lên sau rollback.
        """
        for name, value in (("nguon_id", nguon_id), ("nhap_boi", nhap_boi)):
            if not isinstance(value, str) or not value.strip():
                _sai(f"{name} phải là chuỗi không rỗng.")
        if mo_ta is not None and not isinstance(mo_ta, str):
            _sai("mo_ta phải là TEXT hoặc NULL.")
        moment = _thoi_diem(chup_luc)
        prepared = self._chuan_bi(du_lieu, anh_xa)
        with self._tx():
            # Cùng nguon_id được tuần tự hóa, kể cả trước khi hàng nguồn tồn tại.
            self.conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (nguon_id,))
            old = self._rows("SELECT mo_ta, chup_luc, nhap_boi FROM m4.review_chep_nguon WHERE id=%s FOR UPDATE", (nguon_id,))
            if old:
                metadata = {"mo_ta": mo_ta, "chup_luc": moment, "nhap_boi": nhap_boi}
                changed = [k for k, v in metadata.items() if old[0][k] != v]
                if changed:
                    self._khac("nguon", ", ".join(changed))
                for table, rows in prepared.items():
                    pk = _PK[table]
                    mapping = () if table == "che_do" else ("hop_dong_id", "du_an_id")
                    cols = (*pk, "dong_sha256", *mapping)
                    existing = self._rows(f"SELECT {','.join(cols)} FROM m4.review_chep_{table} WHERE nguon_id=%s", (nguon_id,))
                    actual = {tuple(r[c] for c in pk): r for r in existing}
                    if actual.keys() != rows.keys():
                        self._khac(table, "tập khóa nguồn (thêm/bớt dòng)")
                    for key, row in rows.items():
                        changed = [c for c in mapping if str(actual[key][c]) != row[c]]
                        if changed:
                            self._khac(table, "ánh xạ " + ", ".join(changed))
                        if actual[key]["dong_sha256"] != row["dong_sha256"]:
                            self._khac(table, "dong_sha256 (hash dòng)")
            added = self.conn.execute("""INSERT INTO m4.review_chep_nguon (id,mo_ta,chup_luc,nhap_boi)
                VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING""",
                (nguon_id, mo_ta, moment, nhap_boi)).rowcount
            for table, rows in prepared.items():
                for row in rows.values():
                    values = dict(row, nguon_id=nguon_id, nhap_boi=nhap_boi)
                    # Identifiers chỉ từ allowlist/cột hằng, mọi giá trị dùng placeholder.
                    cols = ",".join(values)
                    placeholders = ",".join("%s" for _ in values)
                    conflict = ",".join(("nguon_id", *_PK[table]))
                    added += self.conn.execute(f"INSERT INTO m4.review_chep_{table} ({cols}) VALUES ({placeholders}) ON CONFLICT ({conflict}) DO NOTHING", tuple(values.values())).rowcount
            return added

    @staticmethod
    def _khac(table, truong="dong_sha256 (hash dòng)"):
        raise DataError("M4_REVIEW_REPLAY_KHAC", f"Lần chụp đã có nhưng khác {truong} ở {table}; không ghi đè.")

    def _kiem_quyen_doc(self, hop_dong_id, *, conn_phien):
        """Dùng chung DL2/DL3; kiểm UUID trước SQL để không hỏng giao dịch phiên."""
        try:
            identity = str(uuid.UUID(str(hop_dong_id)))
        except (ValueError, TypeError, AttributeError):
            raise DataError("M4_REVIEW_KHONG_THAY", "Không tìm thấy hợp đồng.") from None
        if conn_phien is None or conn_phien is self.conn:
            raise DataError("M4_REVIEW_KHONG_THAY", "Không tìm thấy hợp đồng.")
        allowed = conn_phien.execute("""SELECT EXISTS (
            SELECT 1 FROM master.hop_dong h
            WHERE h.id=%s::uuid AND h.module_chu='M4'
              AND (master.m4_duoc(h.du_an_id, 'XEM')
                   OR master.m4_duoc(h.du_an_id, 'REVIEW'))
            ) AS duoc""", (identity,)).fetchone()
        if not (allowed["duoc"] if isinstance(allowed, Mapping) else allowed[0]):
            raise DataError("M4_REVIEW_KHONG_THAY", "Không tìm thấy hợp đồng.")
        return identity

    def _nguon_hien_hanh(self, hop_dong_id):
        """Caller đã kiểm quyền và mở transaction; ba giá trị cùng snapshot SQL."""
        current = self._rows("""SELECT m4.review_chep_hien_hanh(%s::uuid) AS nguon_id,
            EXISTS (SELECT 1 FROM m4.review_chep_nguon) AS co_nguon,
            EXISTS (SELECT 1 FROM m4.review_chep_hop_dong
                WHERE hop_dong_id=%s::uuid) AS co_hd""", (hop_dong_id, hop_dong_id))[0]
        state = ("CHUA_CO_LAN_CHUP" if not current["co_nguon"] else
                 "DA_XOA_O_NGUON" if current["co_hd"] else "CHUA_CO_TRONG_NGUON")
        return current["nguon_id"], state

    def doc_hien_hanh(self, hop_dong_id, *, conn_phien):
        """Ghim nguon_id từ hàm DL1b rồi đọc tất cả con của đúng bản bất biến.

        conn_phien là kết nối thường mang danh tính đã được máy chủ ghim.
        Kiểm XEM/REVIEW theo master.hop_dong.du_an_id TRƯỚC mọi đọc chủ bảng;
        không thấy/không quyền/UUID sai cùng M4_REVIEW_KHONG_THAY (HTTP 404).
        Khe hở giữa kiểm quyền trên kết nối phiên và đọc trên kết nối chủ bảng
        được chấp nhận cho lần đọc này: quyền xét tại thời điểm kiểm; bản chụp
        chỉ đọc, bất biến, không phát sinh ghi hay thay đổi quyền. Thu hồi quyền
        đồng thời có hiệu lực từ lần kiểm tiếp theo, không bảo đảm nguyên tử
        giữa hai kết nối.
        Hàm DL1b và hai EXISTS nằm trong một SELECT để ba trạng thái NULL
        nhất quán dưới READ COMMITTED. Không lùi về bản cũ hay tạo chứng cứ giả.
        """
        hop_dong_id = self._kiem_quyen_doc(hop_dong_id, conn_phien=conn_phien)
        with self._tx():
            source, state = self._nguon_hien_hanh(hop_dong_id)
            if source is None:
                return dto_man_hinh(None, [], [], trang_thai=state)
            contracts = self._rows("SELECT * FROM m4.review_chep_hop_dong WHERE nguon_id=%s AND hop_dong_id=%s::uuid", (source, str(hop_dong_id)))
            if len(contracts) != 1:
                _sai("Bản hiện hành thiếu HĐ nguồn; không thể dựng DTO.")
            params = (source, contracts[0]["ma_hd"])
            parameters = self._rows("SELECT * FROM m4.review_chep_tham_so WHERE nguon_id=%s AND ma_hd=%s ORDER BY ma_ts", params)
            origins = self._rows("SELECT * FROM m4.review_chep_tham_so_nguon WHERE nguon_id=%s AND ma_hd=%s ORDER BY ma_ts", params)
            return dto_man_hinh(contracts[0], parameters, origins)
