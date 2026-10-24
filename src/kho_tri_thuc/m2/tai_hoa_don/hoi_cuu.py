"""Hồi cứu CHỈ ĐỌC nguồn cũ; trả Path thư mục run chứa manifest bất biến.

run_id mã hóa digest thành dạng ngày của hợp đồng v1, không phải ngày tải.
Thời gian quan sát chỉ ở bat_dau/ket_thuc (mtime, xap_xi=true). UUID pháp
nhân/context là nhãn hồi cứu dẫn xuất, KHÔNG chứng thực registry hay quyền.
Không suy scope/ttxly, nhóm truy vấn hoặc ordinal ZIP từ tên file cũ.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from openpyxl import load_workbook

from ...ha_tang.primitives import DataError
from ...nguon.hoa_don_xml import doc_hoa_don_xml
from .cau_hinh import kiem_khong_reparse
from .manifest import (KHOA_HD, KHOA_IDENTITY, SCHEMA, XML_TOI_DA, ZIP_TOI_DA,
                       ZIP_ENTRIES_TOI_DA, _kiem_manifest, _ten_tep, doc_manifest)


def _loi(ma, tai="$"):
    raise DataError("M2_00_HOI_CUU_" + ma, "Không sinh hồi cứu: " + ma + ".", tai) from None


def _json(v):
    return (json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _chuoi(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return "" if v is None else str(v)


def _header(v):
    v = unicodedata.normalize("NFD", _chuoi(v).lower().replace("đ", "d"))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in v if not unicodedata.combining(c)))


_COT = {
    "khmshdon": ("khmshdon", "kyhieumauso", "mauso", "mausohoadon"),
    "khhdon": ("khhdon", "kyhieuhd", "kyhieu", "kyhieuhoadon"),
    "shdon": ("shdon", "sohd", "sohoadon"),
    "nbmst": ("nbmst", "mstnguoiban", "masothuenguoiban"),
    "tdlap": ("tdlap", "ngaylap", "ngaylaphoadon"),
    "dvtte_cong": ("dvtte", "donvitiente", "tiente"),
    "tthai_cong": ("tthai", "trangthai", "trangthaihoadon"),
}


def _doc_bang_ke(raw, ten_tep):
    """15 cột cũ (kể STT), đọc sheet đầu; không suy identity từ vị trí cột."""
    try:
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=False)
        try:
            rows = wb.worksheets[0].iter_rows(values_only=True)
            head = next(rows)
            if len(head) != 15:
                _loi("BANG_KE_KHONG_DUNG_15_COT", ten_tep)
            keys = [_header(x) for x in head]
            cot = {}
            for k, aliases in _COT.items():
                vi_tri = [i for i, v in enumerate(keys) if v in aliases]
                if len(vi_tri) != 1:
                    _loi("BANG_KE_HEADER_KHONG_RO", ten_tep)
                cot[k] = vi_tri[0]
            out = []
            for row in rows:
                if not any(x is not None and x != "" for x in row):
                    continue
                if any(isinstance(x, str) and x.startswith("=") for x in row):
                    _loi("BANG_KE_CO_CONG_THUC", ten_tep)
                h = {k: row[i] for k, i in cot.items()}
                out.append({k: (_chuoi(v) if k in KHOA_IDENTITY or isinstance(v, (date, datetime)) else v)
                            for k, v in h.items()})
            return out
        finally:
            wb.close()
    except DataError:
        raise
    except (OSError, ValueError, KeyError, IndexError, StopIteration, TypeError, BadZipFile, ParseError):
        _loi("BANG_KE_KHONG_DOC_DUOC", ten_tep)


def _tep(p, raw):
    return {"file": str(p), "sha256": _hash(raw), "bytes": len(raw)}


def _hoa_don(key, ordinal, bang_ke=None):
    h = dict.fromkeys(KHOA_HD)
    h.update(item_ordinal=ordinal, key_raw=key,
             key_canonical="|".join(_chuoi(key[k]) for k in KHOA_IDENTITY),
             key_thieu=[k for k in KHOA_IDENTITY if key[k] in (None, "")],
             scope="query", xml_tep=[], pdf_loi=False)
    if bang_ke:
        h.update({k: bang_ke[k] for k in ("tdlap", "tthai_cong", "dvtte_cong")})
    return h


def _chuan_key(key):
    # Chỉ dùng ghép bảng kê: Excel có thể lưu số HĐ dạng số mất zero đầu.
    p = [_chuoi(key[k]) for k in KHOA_IDENTITY]
    if re.fullmatch(r"[0-9]+", p[3]):
        p[3] = p[3].lstrip("0") or "0"
    return tuple(p)


def _danh_sach(goc):
    out = []
    def loi_duyet(_):
        _loi("KHONG_DUYET_DUOC")
    for parent, dirs, files in os.walk(goc, followlinks=False, onerror=loi_duyet):
        for ten in dirs:
            kiem_khong_reparse(Path(parent) / ten, la_thu_muc=True)
        for ten in files:
            p = kiem_khong_reparse(Path(parent) / ten, la_thu_muc=False)
            if p.suffix.lower() in (".xml", ".xlsx", ".pdf"):
                if not (p.suffix.lower() == ".xlsx" and p.name.startswith("~$")):
                    try:
                        _ten_tep(p.name, p.name)
                    except DataError:
                        _loi("TEN_TEP_KHONG_HOP_LE", p.name)
                out.append(p)
    return sorted(out, key=lambda p: p.relative_to(goc).as_posix())


def _goc(thu_muc_thang, chieu):
    p = kiem_khong_reparse(Path(os.path.abspath(thu_muc_thang)), la_thu_muc=True).resolve(strict=True)
    ten = {"purchase": "mua_vao", "sold": "ban_ra"}[chieu]
    # Hỗ trợ cả thư mục tháng phẳng lẫn thư mục tháng có hai chiều.
    if (p / ten).exists() or (p / ten).is_symlink():
        return kiem_khong_reparse(p / ten, la_thu_muc=True).resolve(strict=True)
    if any((p / khac).exists() for khac in ("mua_vao", "ban_ra")):
        _loi("THIEU_THU_MUC_CHIEU")
    return p


def sinh_manifest_hoi_cuu(thu_muc_thang, *, ma_phap_nhan, chieu, ky, thu_muc_ra):
    """Trả Path run ở <ra>/<PN>/<kỳ>/<chiều>/<run_id>/manifest.json.

    Thư mục ra phải tách khỏi nguồn. Nhiều bảng kê cùng chiều: dừng rõ để
    caller chọn bản, không tự chọn lịch sử tải hoặc bỏ dòng âm thầm.
    """
    if not isinstance(ma_phap_nhan, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,31}", ma_phap_nhan):
        _loi("MA_PHAP_NHAN_SAI")
    if chieu not in ("purchase", "sold") or not isinstance(ky, str) or not re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", ky):
        _loi("KY_CHIEU_SAI")
    goc_thang = kiem_khong_reparse(Path(os.path.abspath(thu_muc_thang)), la_thu_muc=True)
    goc = _goc(thu_muc_thang, chieu)
    ra = Path(os.path.abspath(thu_muc_ra))
    if ra.is_relative_to(goc_thang) or goc_thang.is_relative_to(ra):
        _loi("THU_MUC_RA_CHONG_NGUON")
    # Kiểm các thành phần đã tồn tại trước khi mkdir (không theo junction).
    for p in reversed((ra, *ra.parents)):
        if p.exists() or p.is_symlink():
            kiem_khong_reparse(p, la_thu_muc=True)
    files = _danh_sach(goc)
    if any(p.suffix.lower() == ".xlsx" and not p.name.startswith("~$") and
           re.search("sold" if chieu == "purchase" else "purchase", p.stem, re.I) for p in files):
        _loi("NGUON_TRON_HAI_CHIEU")
    # File có nhãn chiều phải khớp; các bản kèm giờ vẫn được phát hiện là trùng.
    excel = [p for p in files if p.suffix.lower() == ".xlsx" and not p.name.startswith("~$")
             and not re.search("sold" if chieu == "purchase" else "purchase", p.stem, re.I)]
    if len(excel) > 1:
        _loi("NHIEU_BANG_KE_CUNG_CHIEU")
    snapshots, inventory = {}, []
    for p in files:
        if p.suffix.lower() == ".xlsx" and p not in excel:
            continue
        before = p.stat()
        raw = p.read_bytes()
        after = p.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            _loi("TEP_DOI_KHI_DOC")
        snapshots[p] = raw
        inventory.append([p.relative_to(goc).as_posix(), _hash(raw), len(raw), after.st_mtime_ns])
    rows = _doc_bang_ke(snapshots[excel[0]], excel[0].name) if excel else []
    by_key = {}
    for row in rows:
        key = _chuan_key(row)
        if key in by_key and by_key[key] != row:
            _loi("BANG_KE_TRUNG_KHOA_KHAC_DU_LIEU")
        by_key[key] = row
    hd, da_co = [], set()
    for p, raw in snapshots.items():
        if p.suffix.lower() != ".xml":
            continue
        res = doc_hoa_don_xml(raw)
        key = {}
        for k, field in zip(KHOA_IDENTITY, ("NBan/MST", "KHMSHDon", "KHHDon", "SHDon")):
            f = res.header(field).duy_nhat if res.header_fields else None
            key[k] = f.lexeme if f is not None and f.state == "TEXT" else None
        lookup = _chuan_key(key)
        h = _hoa_don(key, len(hd) + 1, by_key.get(lookup))
        if not res.header_fields or len(raw) > XML_TOI_DA:
            code = res.issues[0].code if res.issues else "XML_KHONG_DOC_DUOC"
            h.update(xml_status="LOI", payload={**_tep(p, raw), "loai": "XML"},
                     loi={"code": code, "stage": "XML", "http_status": None})
        else:
            t = {**_tep(p, raw), "ordinal_zip": None, "ten_entry_zip": None}
            h.update(xml_status="OK", bang_chung="XML", file_xml=str(p), hash_xml=t["sha256"],
                     xml_bytes=t["bytes"], xml_tep=[t])
            da_co.add(lookup)
            pdf = p.with_suffix(".pdf")
            if pdf in snapshots:
                h.update(file_pdf=str(pdf), hash_pdf=_hash(snapshots[pdf]), vai_tro_pdf="XEM_LAI")
        hd.append(h)
    for lookup, row in by_key.items():
        if lookup not in da_co:
            h = _hoa_don({k: row[k] for k in KHOA_IDENTITY}, len(hd) + 1, row)
            h.update(xml_status="KHONG_XML_GOC", bang_chung="BANG_KE", can_cu="HOI_CUU_BANG_KE_KHONG_CO_XML")
            hd.append(h)
    digest = _hash(_json([str(goc), ma_phap_nhan, chieu, ky, inventory]))
    epoch = datetime(2000, 1, 1)
    seconds = (datetime(9999, 12, 31, 23, 59, 59) - epoch).days * 86400
    run_id = (epoch + timedelta(seconds=int(digest[:16], 16) % seconds)).strftime("%Y%m%d-%H%M%S")
    def thoi_diem(ns):
        return datetime.fromtimestamp(ns // 1_000_000_000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ns // 1_000_000 % 1000:03d}Z"
    mtimes = [x[3] for x in inventory] or [0]
    fact = {"trang_thai": "UNKNOWN", "gia_tri": None, "ly_do": "HOI_CUU_KHONG_QUAN_SAT"}
    ly_do = ["KHONG_CO_NHOM"] + (["XML_LOI"] if any(h["xml_status"] == "LOI" for h in hd) else [])
    m = {
        "schema": SCHEMA, "nguon": "HOI_CUU", "xap_xi": True, "thu_muc_tep_goc": str(goc), "run_id": run_id,
        "phap_nhan": {"ma": ma_phap_nhan, "uuid": str(uuid5(NAMESPACE_URL, "urn:hoi-cuu:" + ma_phap_nhan))},
        "ky": ky, "chieu": chieu, "thu_muc_chieu": "mua_vao" if chieu == "purchase" else "ban_ra",
        "bat_dau": thoi_diem(min(mtimes)), "ket_thuc": thoi_diem(max(mtimes)),
        "phien_ban_bo_tai": "hoi-cuu-v1", "nguoi_bam": "HOI_CUU",
        "context": {"digest": digest, "nonce": digest, "request_key_sha256": digest,
                    "selection_digest": digest, "profile_ref": ma_phap_nhan, "profile_revision": "HOI_CUU-v1",
                    "source_instance": "HOI_CUU-" + _hash(str(goc).encode("utf-8"))[:32], "scope_ref": "HOI_CUU",
                    "actor_nguon": "crm_phien", "quyet_dinh_quyen": "NGOAI_PRODUCER_CHUA_KIEM", "profile_khoa_bo_qua": []},
        "dang_nhap": {"captcha_da_go": dict(fact), "token_tai_su_dung": dict(fact),
                      "thoi_gian_cho_dang_nhap_giay": dict(fact), "do_luong": "PARTIAL"},
        "nhom": [], "hoa_don": hd, "loi_chung": [], "ly_do_partial": ly_do, "trang_thai": "PARTIAL",
        "tong": {"tong_hd": len(hd), "xml_ok": sum(h["xml_status"] == "OK" for h in hd),
                 "xml_loi": sum(h["xml_status"] == "LOI" for h in hd), "xml_khong_yeu_cau": 0,
                 "khong_xml_goc": sum(h["xml_status"] == "KHONG_XML_GOC" for h in hd),
                 "pdf_ok": sum(h["file_pdf"] is not None for h in hd), "pdf_loi": 0,
                 "bang_ke_trang_thai": "OK" if excel else "KHONG_YEU_CAU",
                 "bang_ke": {**_tep(excel[0], snapshots[excel[0]]), "so_cot": 15} if excel else None},
        "gioi_han": {"xml_bytes": XML_TOI_DA, "zip_bytes": ZIP_TOI_DA, "zip_entries": ZIP_ENTRIES_TOI_DA},
    }
    _kiem_manifest(m)  # Giữ nguyên quét credential và toàn bộ invariant M2b.
    run = ra / ma_phap_nhan / ky / m["thu_muc_chieu"] / run_id
    for p in reversed((run, *run.parents)):
        if p.exists() or p.is_symlink():
            kiem_khong_reparse(p, la_thu_muc=True)
    run.mkdir(parents=True, exist_ok=True)
    target, data = run / "manifest.json", _json(m)
    if target.exists() or target.is_symlink():
        kiem_khong_reparse(target, la_thu_muc=False)
        if target.read_bytes() != data:
            _loi("RUN_DA_CO_KHAC_NOI_DUNG")
    else:
        with target.open("xb") as f:
            f.write(data)
    doc_manifest(run)  # Kiểm lại bytes file nguồn, không công bố thành công nếu đã đổi.
    return run


def dem_doi_chieu(thu_muc_thang, manifest):
    """Chỉ trả số đếm, không log/in nội dung hay định danh hóa đơn."""
    m = doc_manifest(manifest) if isinstance(manifest, (str, os.PathLike)) else manifest
    goc = _goc(thu_muc_thang, m["chieu"])
    goc_manifest = m.get("thu_muc_tep_goc")
    if goc_manifest is None or kiem_khong_reparse(
        Path(goc_manifest), la_thu_muc=True
    ).resolve(strict=True) != goc:
        _loi("THU_MUC_MANIFEST_KHONG_KHOP")
    files = _danh_sach(goc)
    bang_ke = m["tong"]["bang_ke"]
    return {"file_xml_tren_dia": sum(p.suffix.lower() == ".xml" for p in files),
            "muc_trong_manifest": len(m["hoa_don"]),
            "dong_bang_ke": len(_doc_bang_ke(Path(bang_ke["file"]).read_bytes(),
                                             Path(bang_ke["file"]).name)) if bang_ke else 0,
            "khong_xml_goc": sum(h["xml_status"] == "KHONG_XML_GOC" for h in m["hoa_don"])}
