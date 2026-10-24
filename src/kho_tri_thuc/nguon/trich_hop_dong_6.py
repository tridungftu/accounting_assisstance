"""K1 · R_CRM — nhận `*_KET_QUA.json` của #6 Trích tham số hợp đồng (Local AI `hop_dong`), không chạy/không sửa #6.

Shape nguồn (docs/GIAO-VIEC-CRM-KE-TOAN-33.md §2): ngoài `hop_dong, che_do, model, tao_luc, tham_so[], phieu_kiem_tra` (+ số đo
lượt chạy); mỗi tham số `ma, nhom, tham_so, gia_tri, don_vi, dieu_khoan, trich_dan, ghi_chu, kiem_tra, vi_tri_do_duoc`
(+ `dap_an`, `so_voi_dap_an`, `doan_lien_quan`). `hop_dong` chỉ là tên/tham chiếu file — không phải khóa hợp đồng/pháp nhân.

Raw giữ nguyên bytes (hash); **envelope nội bộ tách khỏi raw**: version adapter, namespace, hash kết quả, hash Word gốc/văn bản
đối chiếu nếu có, lúc nhận, mapping (pháp nhân/loại hình/mã HĐ chung/ObjectID/dự án), bản gốc/phụ lục và quan hệ. Trường chưa biết
giữ NULL, không suy từ tên file hay model. Số đọc chính xác (Decimal), chặn khóa lặp/NaN — dùng lại bộ đọc của R_REV.
"""

from __future__ import annotations

from typing import Any

from ..ha_tang.primitives import DataError, canonical_json, natural_key, now_utc, sha256
from .fixture import Batch, Issue, Record
from .review_xay_dung import chuan_hoa_so, doc_json_chinh_xac

KIND = "HOP_DONG_TEP"
SOURCE = "trich_hop_dong_6"
ADAPTER_VERSION = "trich-hop-dong-6-ket-qua-v1"
NGOAI = ("hop_dong", "che_do", "model", "tao_luc", "tham_so", "phieu_kiem_tra")
THAM_SO_KEYS = ("ma", "nhom", "tham_so", "gia_tri", "don_vi", "dieu_khoan", "trich_dan", "ghi_chu", "kiem_tra", "vi_tri_do_duoc")
# word_hash: CHỈ sha256 của bytes tệp Word thật do bên nhận tính; word_tham_chieu: định danh tệp nguồn khi không có bytes (vd DEMO).
ENVELOPE_KEYS = ("namespace", "phap_nhan", "loai_hinh", "loai_ban", "hop_dong_goc", "ma_hop_dong_chung", "doi_tac_object_id", "du_an",
                 "word_hash", "word_tham_chieu", "van_ban_nguon_hash")


def doc_ket_qua(content: bytes) -> dict:
    value = doc_json_chinh_xac(content)
    if not isinstance(value, dict):
        raise DataError("TRICH6_SHAPE", "Kết quả #6 phải là một object JSON.")
    thieu = [k for k in ("hop_dong", "che_do", "tham_so") if k not in value]
    if thieu:
        raise DataError("TRICH6_SHAPE", "Kết quả #6 thiếu trường: " + ", ".join(thieu) + ".")
    if not isinstance(value["tham_so"], list):
        raise DataError("TRICH6_SHAPE", "`tham_so` của #6 phải là danh sách.")
    for i, p in enumerate(value["tham_so"]):
        if not isinstance(p, dict) or not isinstance(p.get("ma"), str) or not p["ma"].strip():
            raise DataError("TRICH6_SHAPE", f"Tham số #{i + 1} thiếu mã `ma`.")
    return value


def word_khoa(env: dict) -> str | None:
    """Khóa nhận diện cùng một tệp Word nguồn: hash bytes thật nếu có, nếu không là định danh tham chiếu (ghi rõ loại)."""
    if env.get("word_hash"):
        return "SHA256:" + env["word_hash"]
    return "THAM_CHIEU:" + env["word_tham_chieu"] if env.get("word_tham_chieu") else None


# CRM-41-01: metadata engine dùng chung (common/v1) đi kèm envelope — versioned, kiểm khóa/kiểu; raw nguồn #6 giữ hash RIÊNG với view.
COMMON_ENV_VERSION = "trich6-common-envelope-v1"
COMMON_ENV_KEYS = ("contract", "request_id", "luot", "raw_ket_qua_sha256", "source_sha256", "catalog_id", "catalog_sha256", "loai_hop_dong",
                   "implementation_sha256", "tham_so_yeu_cau", "tham_so_da_dung", "adapter")


def _kiem_common_env(common: dict) -> dict:
    if not isinstance(common, dict) or set(common) != set(COMMON_ENV_KEYS):
        raise DataError("TRICH6_ENVELOPE_COMMON", "Metadata engine dùng chung sai khóa.")
    for k in ("raw_ket_qua_sha256", "source_sha256", "catalog_sha256", "implementation_sha256"):
        v = common[k]
        if not (isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)):
            raise DataError("TRICH6_ENVELOPE_COMMON", f"{k} phải là sha256 hex.")
    if common["contract"] != "trich-tham-so-common/v1" or not isinstance(common["tham_so_da_dung"], list) or not common["tham_so_da_dung"]:
        raise DataError("TRICH6_ENVELOPE_COMMON", "Metadata engine dùng chung không đúng contract/tập mã.")
    if common["tham_so_yeu_cau"] != "ALL" and not isinstance(common["tham_so_yeu_cau"], list):
        raise DataError("TRICH6_ENVELOPE_COMMON", "tham_so_yeu_cau phải là 'ALL' hoặc danh sách.")
    return {"phien_ban": COMMON_ENV_VERSION, **common}


def envelope(raw: bytes, thong_tin: dict, *, van_ban_nguon=None, common: dict | None = None) -> dict:
    """Envelope nội bộ (không ghi vào raw). Chỉ nhận khóa đã định; thiếu → NULL; loai_ban mặc định chưa biết (NULL).
    `common` (CRM-41-01, tùy chọn): metadata engine dùng chung đã kiểm; không truyền → envelope y như cũ (tương thích JSON cũ)."""
    if not isinstance(thong_tin, dict) or set(thong_tin) - set(ENVELOPE_KEYS):
        raise DataError("TRICH6_ENVELOPE", "Envelope có trường ngoài hợp đồng adapter.")
    loai_ban = thong_tin.get("loai_ban")
    if loai_ban not in (None, "GOC", "PHU_LUC"):
        raise DataError("TRICH6_ENVELOPE", "loai_ban chỉ nhận GOC hoặc PHU_LUC.")
    env = {k: (thong_tin.get(k).strip() if isinstance(thong_tin.get(k), str) and thong_tin.get(k).strip() else None) for k in ENVELOPE_KEYS}
    if not env["namespace"]:
        raise DataError("TRICH6_ENVELOPE", "Thiếu namespace/instance nguồn #6.")
    if env["word_hash"] and not (len(env["word_hash"]) == 64 and all(c in "0123456789abcdef" for c in env["word_hash"])):
        raise DataError("TRICH6_ENVELOPE", "word_hash phải là sha256 hex của bytes tệp Word.")
    env.update({"phien_ban_adapter": ADAPTER_VERSION, "hash_ket_qua": sha256(raw), "nhan_luc": now_utc()})
    if van_ban_nguon is not None:
        env["van_ban_nguon_hash"] = sha256((van_ban_nguon if isinstance(van_ban_nguon, str) else canonical_json(van_ban_nguon)).encode("utf-8"))
    if common is not None:
        env["common"] = _kiem_common_env(common)
    return env


class TrichHopDong6Adapter:
    """Adapter K1 dùng hợp đồng Record/Batch chung; lưu trữ do repository K2 thực hiện (Store V12 khóa một pháp nhân)."""

    version = ADAPTER_VERSION

    def __init__(self, env: dict):
        self.env = env

    def read(self, content: bytes, _config: Any = None) -> Batch:
        value = doc_ket_qua(content)
        exact = chuan_hoa_so(value)
        issues = []
        if value.get("che_do") == "chua_chay_AI":
            issues.append(Issue("TRICH6_CHUA_CHAY_AI", "Kết quả #6 chưa chạy AI: đoạn liên quan không phải giá trị đã trích/đã duyệt.", "$", "WARNING"))
        if value.get("che_do") == "RULE_ONLY":  # CRM-41-01: engine dùng chung chỉ quy tắc — mã CHUA_CO là chưa trích, không phải đã duyệt/0
            issues.append(Issue("TRICH6_RULE_ONLY", "Kết quả engine dùng chung chế độ RULE_ONLY: chỉ mã có trích dẫn quy tắc là giá trị máy; "
                                                    "mã CHUA_CO/NOT_REQUESTED cần nhập/soát tay.", "$", "WARNING"))
        for key in NGOAI:
            if key not in value:
                issues.append(Issue("TRICH6_THIEU_NGOAI", f"Thiếu `{key}` ở lớp ngoài kết quả #6.", "$", "WARNING"))
        key = natural_key(self.env["namespace"], self.env["hash_ket_qua"])
        record = Record(0, KIND, key, self.env["nhan_luc"][:10], None, None,
                        {"kind": KIND, "envelope": self.env, "ket_qua_6": exact, "tham_chieu_file": chuan_hoa_so(value.get("hop_dong"))})
        manifest = {"entity_id": self.env.get("phap_nhan"), "source_system": "TRICH_6:" + self.env["namespace"], "as_of": self.env["nhan_luc"][:10],
                    "exported_at": self.env["nhan_luc"], "known_at": self.env["nhan_luc"], "known_at_basis": "lúc kế toán nhận kết quả #6 (không dùng tao_luc nguồn)",
                    "scope": "một kết quả trích hợp đồng #6"}
        return Batch(SOURCE, manifest, [exact], [record], {}, issues)


def noi_dung_hash(value: dict) -> str:
    return sha256(canonical_json(chuan_hoa_so(value)).encode())
