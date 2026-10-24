"""K1 · R_REV — nhận kết quả kiểm đợt của #5 Review hồ sơ thanh toán xây dựng (bridge DEMO).

Đọc đúng shape JSON `kiem_tra_dot` mà #5 đã lưu (docs/TAI-SU-DUNG-REVIEW-XAY-DUNG.md §3.1); không chạy, không import
và không review lại #5. Mỗi kết quả thành một chứng từ ``NGHIEM_THU`` qua ``Store.ingest`` (raw bất biến, hash, staging,
evidence, giao dịch). Bảo toàn nghĩa trường nguồn:

- ``de_nghi`` là số **đề nghị**; ``tong_hop`` là số đọc theo nhãn (kỳ, lũy kế, giữ lại đợt, thu hồi tạm ứng, thanh toán kỳ).
  Không có trường nào là "số chấp nhận hạch toán" → ``amount_minor`` để NULL; không tính ``de_nghi - anh_huong``.
- Số không đọc được giữ NULL kèm giá trị gốc, không thành 0.
- ``da_nap`` chỉ là trạng thái nạp CSDL review, không phải duyệt kế toán.
- Khóa = instance nguồn (namespace) + ``ma_hd`` + ``dot`` + ID review ``ma`` + hash nội dung: nhận lại cùng nội dung không
  tạo chứng từ mới; nội dung khác (vd ``da_nap``/``anh_huong`` đổi) là phiên bản mới của cùng sự kiện — hồ sơ kế toán xử lý
  quan hệ thay thế (``de_xuat/nghiem_thu.py``), không ghi đè.

Production theo TL40 đi qua ``giao_tiep.v1_ghi_ket_qua_review`` với vai trò riêng — chưa có trong gói này; adapter từ chối
môi trường ``that``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from ..ha_tang.config import Config
from ..ha_tang.primitives import DataError, canonical_json, date_iso, instant_utc, money_minor, natural_key, sha256
from .fixture import Batch, Issue, Record, _unique_object

KIND = "NGHIEM_THU"
SOURCE = "review_xay_dung"
TONG_HOP_KEYS = ("gt_hd", "gt_lk_kt", "gt_kn", "gt_lk", "giu_lai", "thu_hoi_tu", "tt_ky_nay")
SNAPSHOT_KEYS = ("gt_hieu_luc", "loai_gia", "vat", "phu_luc_ap_dung")
THAM_CHIEU_KEYS = ("bang_k", "cay", "bang_lop2", "doi_chieu_hm")
DECIMAL_TAG = "$so_thap_phan"  # số JSON có phần lẻ: giữ chuỗi thập phân chính xác, không qua float


def doc_json_chinh_xac(content: bytes) -> Any:
    """JSON của #5 với số đọc **chính xác** (Decimal, không qua binary64); vẫn chặn khóa lặp và NaN/Infinity."""
    def bad_constant(_):
        raise DataError("INVALID_JSON", "JSON chứa NaN/Infinity.")
    try:
        return json.loads(content.decode("utf-8-sig"), object_pairs_hook=_unique_object, parse_float=Decimal, parse_constant=bad_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DataError("INVALID_JSON", "Không đọc được JSON UTF-8 hợp lệ.") from exc


def chuan_hoa_so(value: Any) -> Any:
    """Cây JSON → dạng serialize được, không mất nghĩa: Decimal nguyên → int; Decimal có phần lẻ → {DECIMAL_TAG: "chuỗi chính xác"}."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else {DECIMAL_TAG: str(value)}
    if isinstance(value, dict):
        return {k: chuan_hoa_so(v) for k, v in value.items()}
    if isinstance(value, list):
        return [chuan_hoa_so(v) for v in value]
    return value


def so_nguon(value: Any) -> dict:
    """Số đọc từ #5: {"minor": int|None, "goc": giá trị gốc chính xác}. Phần lẻ VND / không đọc chắc → minor None, không làm tròn, không thành 0."""
    minor = None
    if isinstance(value, Decimal):
        minor = int(value) if value == value.to_integral_value() else None
    elif type(value) is int:
        minor = value
    elif isinstance(value, str) and value.strip():
        try:
            minor = money_minor(value.strip(), 0)
        except DataError:
            minor = None
    return {"minor": minor, "goc": chuan_hoa_so(value)}


def kiem_da_nap(da_nap: Any, dot: str) -> list[str]:
    """Bằng chứng nạp CSDL review theo shape #5 `{luc,dot,so_hang_muc,khong_khop,ghi_chu,nap_lai}` (audit §3.1).
    Trả danh sách lỗi; rỗng = hợp lệ. Bắt buộc `luc` đọc được và `dot` khớp đợt; trường khác nếu có phải đúng kiểu."""
    if da_nap is False or da_nap is None:
        return ["chưa nạp CSDL review"]
    if not isinstance(da_nap, dict):
        return ["`da_nap` không phải object bằng chứng nạp"]
    errors = []
    try:
        _luc(da_nap.get("luc"))
    except DataError:
        errors.append("`da_nap.luc` thiếu hoặc không đọc được")
    nap_dot = da_nap.get("dot")
    if isinstance(nap_dot, bool) or not isinstance(nap_dot, (str, int)) or str(nap_dot).strip() != str(dot):
        errors.append("`da_nap.dot` thiếu hoặc không khớp đợt của kết quả review")
    for key in ("so_hang_muc", "khong_khop"):
        if key in da_nap and (type(da_nap[key]) is not int or da_nap[key] < 0):
            errors.append(f"`da_nap.{key}` phải là số nguyên không âm")
    if "nap_lai" in da_nap and type(da_nap["nap_lai"]) is not bool:
        errors.append("`da_nap.nap_lai` phải là true/false")
    if "ghi_chu" in da_nap and da_nap["ghi_chu"] is not None and not isinstance(da_nap["ghi_chu"], str):
        errors.append("`da_nap.ghi_chu` phải là chuỗi")
    return errors


def _luc(value: Any) -> tuple[str, str]:
    """Thời điểm review: ISO có offset dùng nguyên; không offset → coi giờ Việt Nam (+07:00) và ghi rõ căn cứ."""
    if not isinstance(value, str) or not value:
        raise DataError("REVIEW_MISSING_FIELD", "Kết quả review thiếu thời điểm `luc`.")
    try:
        return instant_utc(value), "luc của kết quả review #5"
    except DataError:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise DataError("REVIEW_TIME", "Thời điểm `luc` của review không đọc được.") from exc
        if parsed.tzinfo is not None:
            raise DataError("REVIEW_TIME", "Thời điểm `luc` của review không đọc được.")
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=7)))
        return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"), "luc của review #5 không có offset → +07:00"


def _text(obj: dict, key: str, label: str | None = None) -> str:
    value = obj.get(key)
    if isinstance(value, Decimal) and value == value.to_integral_value():
        value = str(int(value))
    elif type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        raise DataError("REVIEW_MISSING_FIELD", f"Kết quả review thiếu `{label or key}`.")
    return value.strip()


def chuan_hoa(payload: Any, instance: str) -> tuple[dict, dict]:
    """Payload `kiem_tra_dot` → (core chuẩn hóa, thông tin phụ). Trường thiếu ghi vào ``thieu``, không suy diễn."""
    if not isinstance(payload, dict):
        raise DataError("REVIEW_SHAPE", "Mỗi kết quả review phải là một object JSON.")
    if payload.get("loai") != "kiem_tra_dot":
        raise DataError("REVIEW_KIND", "Chỉ nhận kết quả loại `kiem_tra_dot` của #5 (chế độ chỉ toàn vẹn không đủ cho nghiệm thu).")
    hop_dong = payload.get("hop_dong")
    if not isinstance(hop_dong, dict):
        raise DataError("REVIEW_MISSING_FIELD", "Kết quả review thiếu `hop_dong`.")
    ma, ma_hd, dot = _text(payload, "ma"), _text(hop_dong, "ma_hd", "hop_dong.ma_hd"), _text(payload, "dot")
    ngay = date_iso(_text(payload, "ngay_nghiem_thu"))
    luc, luc_basis = _luc(payload.get("luc"))
    tong_hop_raw = payload.get("tong_hop") if isinstance(payload.get("tong_hop"), dict) else {}
    tong_hop = {}
    for key, entry in tong_hop_raw.items():
        entry = entry if isinstance(entry, dict) else {"gia_tri": entry}
        tong_hop[key] = {**so_nguon(entry.get("gia_tri")), "o": chuan_hoa_so(entry.get("o")), "nhan": chuan_hoa_so(entry.get("nhan"))}
    da_nap = chuan_hoa_so(payload.get("da_nap"))
    loi_nap = kiem_da_nap(da_nap, dot)
    thieu = [k for k in SNAPSHOT_KEYS if payload.get(k) in (None, "", [])]
    thieu += [f"tong_hop.{k}" for k in TONG_HOP_KEYS if k not in tong_hop or tong_hop[k]["minor"] is None]
    if "de_nghi" not in payload or so_nguon(payload.get("de_nghi"))["minor"] is None:
        thieu.append("de_nghi")
    core = {
        "kind": KIND, "nguon": {"instance": instance, "he_thong": "#5 Review hồ sơ thanh toán xây dựng", "ma_review": ma, "loai": "kiem_tra_dot",
                                "luc": luc, "luc_basis": luc_basis, "tep": chuan_hoa_so(payload.get("tep"))},
        "hop_dong": {"ma_hd": ma_hd, "so_hd": chuan_hoa_so(hop_dong.get("so_hd")), "phan_loai": chuan_hoa_so(hop_dong.get("phan_loai"))},
        "dot": dot, "dot_truoc": chuan_hoa_so(payload.get("dot_truoc")), "ngay_nghiem_thu": ngay,
        # snapshot căn cứ review tại ngày nghiệm thu, đúng như #5 cung cấp
        "can_cu": {k: chuan_hoa_so(payload.get(k)) for k in SNAPSHOT_KEYS},
        "de_nghi": so_nguon(payload.get("de_nghi")), "o_de_nghi": chuan_hoa_so(payload.get("o_de_nghi")),
        "tong_hop": tong_hop,
        "anh_huong": {"goc": chuan_hoa_so(payload.get("anh_huong")), "y_nghia": "ảnh hưởng/phát hiện của review (lũy kế, chưa VAT hoặc chưa định lượng) — không phải số điều chỉnh kỳ"},
        "so_phat_hien": len(payload["phat_hien"]) if isinstance(payload.get("phat_hien"), list) else None,
        "da_nap": da_nap if isinstance(da_nap, dict) else None,
        "da_nap_loi": [] if not loi_nap else loi_nap,
        "trang_thai_nguon": "DA_NAP_CSDL_REVIEW" if not loi_nap else ("CHUA_NAP_CSDL_REVIEW" if da_nap in (False, None) else "BANG_CHUNG_NAP_KHONG_HOP_LE"),
        "tai": chuan_hoa_so(payload.get("tai")) if isinstance(payload.get("tai"), dict) else None,
        "tham_chieu": {k: sha256(canonical_json(chuan_hoa_so(payload[k])).encode()) for k in THAM_CHIEU_KEYS if k in payload},
        "thieu": thieu,
    }
    return core, {"luc": luc, "luc_basis": luc_basis, "ma_hd": ma_hd, "dot": dot, "ma": ma}


class ReviewXayDungAdapter:
    """Adapter K1 cho Store.ingest. ``instance`` = namespace nguồn (vd một máy #5 của phòng dự án)."""

    version = "review-xay-dung-kiem-tra-dot-v1"

    def __init__(self, instance: str):
        if not isinstance(instance, str) or not instance.strip():
            raise DataError("REVIEW_INSTANCE", "Cần định danh instance nguồn #5.")
        self.instance = instance.strip()

    def read(self, content: bytes, config: Config) -> Batch:
        if config.environment == "that":
            raise DataError("REVIEW_PRODUCTION_GATE", "Kho thật nhận kết quả #5 qua giao_tiep.v1_ghi_ket_qua_review (TL40) — chưa tích hợp; adapter này chỉ cho DEMO.")
        value = doc_json_chinh_xac(content)
        payloads = value if isinstance(value, list) else [value]
        if not payloads:
            raise DataError("EMPTY_SOURCE", "Tệp không có kết quả review.")
        records, issues, rows, lucs = [], [], [], []
        for ordinal, payload in enumerate(payloads):
            exact = chuan_hoa_so(payload)  # staging serialize được, giữ giá trị chính xác; artifact raw giữ nguyên bytes
            rows.append(exact)
            try:
                if config.environment == "fixture" and "DEMO" not in str(payload.get("ma", "") if isinstance(payload, dict) else ""):
                    raise DataError("DEMO_ONLY", "Kho mô phỏng chỉ nhận kết quả review DEMO (mã review chứa chữ DEMO).")
                core, info = chuan_hoa(payload, self.instance)
                content_hash = sha256(canonical_json(exact).encode())
                core["nguon"]["hash_noi_dung"] = content_hash
                key = natural_key(self.instance, info["ma_hd"], info["dot"], info["ma"], "noi_dung:" + content_hash)
                records.append(Record(ordinal, KIND, key, core["ngay_nghiem_thu"], None, None, core))
                lucs.append(info["luc"])
                for missing in core["thieu"]:
                    issues.append(Issue("REVIEW_FIELD_MISSING", f"Thiếu/không đọc được `{missing}` — giữ NULL, không suy diễn.", f"$.records[{ordinal}]", "WARNING"))
            except DataError as exc:
                issues.append(Issue(exc.code, str(exc), f"$.records[{ordinal}]"))
        known = max(lucs) if lucs else None
        days = sorted(r.business_date for r in records)
        manifest = {"entity_id": config.entity_id, "source_system": "REVIEW_XAY_DUNG:" + self.instance,
                    "as_of": known[:10] if known else (days[-1] if days else "1900-01-01"), "exported_at": known or "1900-01-01T00:00:00.000000Z",
                    "known_at": known, "known_at_basis": "max(luc) các kết quả review #5" if known else None, "scope": "kết quả kiem_tra_dot của #5"}
        return Batch(SOURCE, manifest, rows, records, {}, issues, allow_record_errors=True)
