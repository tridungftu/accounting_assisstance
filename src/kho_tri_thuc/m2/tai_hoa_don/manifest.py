"""Đọc hợp đồng m2_00a.source7.manifest.v1, kiểm bytes, không intake/ghi đĩa.

Tên trường theo tools/source7_m2_patch/src/manifest.js và job.js, đặc biệt
tong.bang_ke.sha256 và hoa_don[].xml_tep[].sha256. Không đọc nội dung Excel.
HOI_CUU dùng cùng cấu trúc, thêm xap_xi=true; việc sinh hồi cứu thuộc M2d.
Context chỉ được kiểm hình dạng, không phải quyết định quyền hay chứng thực nguồn.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ...ha_tang.primitives import DataError
from .cau_hinh import kiem_khong_reparse

SCHEMA = "m2_00a.source7.manifest.v1"
JSON_TOI_DA = 64 * 1024 * 1024
XML_TOI_DA, ZIP_TOI_DA, ZIP_ENTRIES_TOI_DA = 16 * 1024 * 1024, 64 * 1024 * 1024, 1000
SO_NGUYEN_TOI_DA = 2**53 - 1
KHOA_IDENTITY = ("nbmst", "khmshdon", "khhdon", "shdon")
KHOA_MANIFEST = (
    "schema nguon run_id phap_nhan ky chieu thu_muc_chieu bat_dau ket_thuc "
    "phien_ban_bo_tai nguoi_bam context dang_nhap nhom tong hoa_don loi_chung "
    "trang_thai ly_do_partial gioi_han"
).split()
KHOA_CONTEXT = (
    "digest nonce request_key_sha256 profile_ref profile_revision source_instance scope_ref "
    "selection_digest actor_nguon quyet_dinh_quyen profile_khoa_bo_qua"
).split()
KHOA_HD = (
    "item_ordinal key_raw key_canonical key_thieu scope ttxly nhom_thu_tu tthai_cong tdlap "
    "dvtte_cong xml_status bang_chung can_cu file_xml hash_xml xml_bytes ordinal_zip "
    "ten_entry_zip xml_tep zip payload file_pdf hash_pdf vai_tro_pdf pdf_loi loi"
).split()
KHOA_TONG = "tong_hd xml_ok khong_xml_goc xml_loi xml_khong_yeu_cau pdf_ok pdf_loi bang_ke bang_ke_trang_thai".split()
KHOA_TEP = "file sha256 bytes ordinal_zip ten_entry_zip".split()
KHOA_ZIP_ENTRY = "ordinal name declared_bytes read_state bytes sha256 loi trung_ten file".split()
RE_HASH = r"[0-9a-f]{64}"
RE_MA = r"[A-Z0-9][A-Z0-9_+]{1,79}"
RE_ACTOR = r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}"
RE_INSTANCE = r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}"
RE_CAM = re.compile(
    r"(?:mat[_ -]?khau|password|passwd|pwd|pass|secret|cookie|cookies|set-cookie|authorization|"
    r"bearer|token|access_token|refresh_token|id_token|jwt|captcha|captcha_text|captcha_value|"
    r"username|user_name|tax_username|tax_password)", re.I
)
RE_GIA_TRI_CAM = re.compile(
    r"[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|bearer\s+\S|"
    r"\b(?:mat[_ -]?khau|password|passwd|pwd|pass|token)\s*[:=]\s*\S", re.I
)


def _loi(ma: str, tai: str = "$"):
    # Không phản chiếu giá trị nguồn/JSON thô/mật khẩu vào exception/log/HTTP.
    raise DataError("M2_00_MANIFEST_" + ma, "Manifest bị từ chối: " + ma + ".", tai) from None


def _can(dieu_kien, tai: str, ma: str = "GIA_TRI_SAI"):
    if not dieu_kien:
        _loi(ma, tai)


def _doi_tuong(v, khoa, tai):
    _can(type(v) is dict, tai, "SAI_KIEU")
    _can(set(khoa) <= set(v), tai, "THIEU_TRUONG")
    _can(set(v) <= set(khoa), tai, "TRUONG_LA")


def _chuoi(v, mau, tai):
    _can(isinstance(v, str), tai, "SAI_KIEU")
    _can(re.fullmatch(mau, v) is not None, tai)


def _so(v, tai, nho=0, lon=SO_NGUYEN_TOI_DA):
    _can(type(v) is int, tai, "SAI_KIEU")
    _can(nho <= v <= lon, tai)


def _mang(v, tai):
    _can(type(v) is list, tai, "SAI_KIEU")


def _la_so_huu_han(v):
    if type(v) not in (int, float):
        return False
    try:
        return math.isfinite(v)
    except OverflowError:
        return False


def _raw(v, tai):
    _can(v is None or type(v) in (str, bool) or _la_so_huu_han(v), tai, "SAI_KIEU")


def _quet_bi_mat(v, do_sau=0):
    _can(do_sau <= 32, "$", "QUA_SAU")
    if isinstance(v, str):
        if RE_GIA_TRI_CAM.search(v):
            _loi("CO_BI_MAT")
    elif isinstance(v, dict):
        for k, x in v.items():
            if RE_CAM.fullmatch(k):
                _loi("CO_BI_MAT")
            _quet_bi_mat(x, do_sau + 1)
    elif isinstance(v, list):
        for x in v:
            _quet_bi_mat(x, do_sau + 1)


def _ten_tep(v, tai, goc=None):
    if goc is not None:
        _can(isinstance(v, str), tai, "SAI_KIEU")
        p = Path(v)
        _can(p.is_absolute() and ".." not in p.parts and p != goc and p.is_relative_to(goc),
             tai, "DUONG_DAN_SAI")
        _ten_tep(p.name, tai)  # Giữ nguyên kiểm basename, kể cả tên Windows cấm.
        _duong_dan(p, thu_muc=False)
        return
    _chuoi(v, r"[A-Za-z0-9_][A-Za-z0-9_.~-]{0,159}", tai)
    _can(".." not in v and not v.endswith((".", " ")) and not re.fullmatch(
        r"CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]", v.split(".")[0], re.I
    ), tai, "DUONG_DAN_SAI")


def _thoi_diem(v, tai):
    _chuoi(v, r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z", tai)
    try:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        _loi("THOI_DIEM_SAI", tai)


def _kiem_loi(v, tai):
    _doi_tuong(v, ("code", "stage", "http_status"), tai)
    _chuoi(v["code"], RE_MA, tai + ".code")
    _can(v["stage"] in ("RESERVE", "LOGIN", "LIST", "EXPORT_XML", "XML", "ZIP", "PDF", "EXCEL", "MANIFEST", "INTERNAL"), tai)
    if v["http_status"] is not None:
        _so(v["http_status"], tai + ".http_status", lon=999)


@dataclass(frozen=True)
class _Tep:
    file: str
    sha256: str
    bytes: int | None


class KetQuaDocManifest(dict):
    """Dict nguồn giữ nguyên; hai danh sách riêng để M2c phân luồng.

    hoa_don_thieu_khoa giữ toàn bộ hóa đơn, gồm key_raw và key_thieu, chỉ để
    đưa vào danh sách việc. hoa_don_du_khoa chưa phải đề xuất được duyệt.
    """

    @property
    def hoa_don_thieu_khoa(self) -> list[dict]:
        return [h for h in self["hoa_don"] if h["key_thieu"]]

    @property
    def hoa_don_du_khoa(self) -> list[dict]:
        return [h for h in self["hoa_don"] if not h["key_thieu"]]


def _tep(v, tai, tep, *, lon=SO_NGUYEN_TOI_DA, nho=1, goc=None):
    _ten_tep(v["file"], tai + ".file", goc)
    _chuoi(v["sha256"], RE_HASH, tai + ".sha256")
    _so(v["bytes"], tai + ".bytes", nho, lon)
    tep.append(_Tep(v["file"], v["sha256"], v["bytes"]))


def _kiem_zip(z, tai, tep, goc=None):
    _doi_tuong(z, "file sha256 bytes coverage entries loi".split(), tai)
    _chuoi(z["sha256"], RE_HASH, tai + ".sha256")
    _so(z["bytes"], tai + ".bytes")
    if z["file"] is not None:
        _tep(z, tai, tep, lon=ZIP_TOI_DA, nho=0, goc=goc)
    _can(z["coverage"] in ("COMPLETE", "PARTIAL"), tai + ".coverage")
    if z["loi"] is not None:
        _kiem_loi(z["loi"], tai + ".loi")
    _mang(z["entries"], tai + ".entries")
    _can(len(z["entries"]) <= ZIP_ENTRIES_TOI_DA, tai)
    for i, e in enumerate(z["entries"], 1):
        a = f"{tai}.entries[{i - 1}]"
        _doi_tuong(e, KHOA_ZIP_ENTRY, a)
        _so(e["ordinal"], a + ".ordinal", i, i)
        _can(isinstance(e["name"], str), a + ".name", "SAI_KIEU")
        if e["declared_bytes"] is not None:
            _so(e["declared_bytes"], a + ".declared_bytes")
        _can(e["read_state"] in ("READ_OK", "READ_ERROR", "IGNORED_NON_XML", "DIRECTORY"), a)
        _can(type(e["trung_ten"]) is bool, a + ".trung_ten", "SAI_KIEU")
        if e["read_state"] == "READ_OK":
            _tep(e, a, tep, lon=XML_TOI_DA, goc=goc)
            _can(e["loi"] is None, a)
        else:
            _can(all(e[k] is None for k in ("file", "sha256", "bytes")), a)
            if e["read_state"] == "READ_ERROR":
                _can(e["loi"] is not None, a)
            if e["loi"] is not None:
                _kiem_loi(e["loi"], a + ".loi")
    for e in z["entries"]:
        _can(e["trung_ten"] == (sum(x["name"] == e["name"] for x in z["entries"]) > 1), tai)
    if z["coverage"] == "COMPLETE":
        _can(z["loi"] is None and all(e["read_state"] != "READ_ERROR" for e in z["entries"]), tai)


def _chuoi_raw(v):
    """String(raw) theo producer cho các scalar identity; không bỏ số 0 đầu."""
    if v is None:
        return ""
    if type(v) is bool:
        return "true" if v else "false"
    if type(v) is float and v.is_integer():
        return str(int(v))
    return str(v)


def _kiem_hd(h, i, tep, goc=None):
    a = f"$.hoa_don[{i - 1}]"
    _doi_tuong(h, KHOA_HD, a)
    _so(h["item_ordinal"], a + ".item_ordinal", i, i)
    _doi_tuong(h["key_raw"], KHOA_IDENTITY, a + ".key_raw")
    for k in KHOA_IDENTITY:
        _raw(h["key_raw"][k], a + ".key_raw." + k)
    _can(isinstance(h["key_canonical"], str), a + ".key_canonical", "SAI_KIEU")
    phan = h["key_canonical"].split("|")
    _can(len(phan) == 4, a + ".key_canonical", "IDENTITY_THIEU")
    _can(h["key_canonical"] == "|".join(_chuoi_raw(h["key_raw"][k]) for k in KHOA_IDENTITY),
         a + ".key_canonical", "IDENTITY_KHONG_KHOP")
    _mang(h["key_thieu"], a + ".key_thieu")
    thieu = [k for k in KHOA_IDENTITY if h["key_raw"][k] is None or h["key_raw"][k] == ""]
    _can(h["key_thieu"] == thieu, a + ".key_thieu", "IDENTITY_THIEU")
    _can(h["scope"] in ("query", "sco-query"), a + ".scope")
    for k in ("ttxly", "tthai_cong", "tdlap", "dvtte_cong"):
        _raw(h[k], a + "." + k)
    if h["nhom_thu_tu"] is not None:
        _so(h["nhom_thu_tu"], a + ".nhom_thu_tu", 1, 1000)
    _can(h["xml_status"] in ("OK", "KHONG_XML_GOC", "LOI", "KHONG_YEU_CAU"), a + ".xml_status")
    _mang(h["xml_tep"], a + ".xml_tep")
    if h["zip"] is not None:
        _kiem_zip(h["zip"], a + ".zip", tep, goc)
    if h["xml_status"] == "OK":
        _can(bool(h["xml_tep"]), a + ".xml_tep")
        for j, t in enumerate(h["xml_tep"]):
            ta = f"{a}.xml_tep[{j}]"
            _doi_tuong(t, KHOA_TEP, ta)
            _tep(t, ta, tep, lon=XML_TOI_DA, goc=goc)
            _can(t["file"].lower().endswith(".xml"), ta + ".file")
            if t["ordinal_zip"] is None:
                _can(t["ten_entry_zip"] is None, ta)
            else:
                _so(t["ordinal_zip"], ta + ".ordinal_zip", 1, ZIP_ENTRIES_TOI_DA)
                z = h["zip"]
                _can(z is not None and t["ordinal_zip"] <= len(z["entries"]), ta, "ZIP_KHONG_KHOP")
                e = z["entries"][t["ordinal_zip"] - 1]
                _can(e["read_state"] == "READ_OK" and e["name"] == t["ten_entry_zip"] and
                     all(e[k] == t[k] for k in ("file", "sha256", "bytes")), ta, "ZIP_KHONG_KHOP")
        t = h["xml_tep"][0]
        _can(all(h[k] == t[v] and type(h[k]) is type(t[v]) for k, v in (
            ("file_xml", "file"), ("hash_xml", "sha256"), ("xml_bytes", "bytes"),
            ("ordinal_zip", "ordinal_zip"), ("ten_entry_zip", "ten_entry_zip")
        )), t["file"], "XML_CHINH_KHONG_KHOP")
        _can(h["bang_chung"] == "XML" and h["can_cu"] is None and h["loi"] is None, a)
    else:
        _can(not h["xml_tep"] and all(h[k] is None for k in (
            "file_xml", "hash_xml", "xml_bytes", "ordinal_zip", "ten_entry_zip"
        )), a, "TRANG_THAI_XML_SAI")
        if h["xml_status"] == "KHONG_XML_GOC":
            _can(h["bang_chung"] == "BANG_KE", a + ".bang_chung")
            _chuoi(h["can_cu"], RE_MA, a + ".can_cu")
            _can(h["loi"] is None and h["zip"] is None and h["payload"] is None, a)
        elif h["xml_status"] == "LOI":
            _can(h["bang_chung"] is None and h["can_cu"] is None, a)
            _kiem_loi(h["loi"], a + ".loi")
        else:
            _can(all(h[k] is None for k in ("bang_chung", "can_cu", "loi", "zip", "payload")), a)
    if h["payload"] is not None:
        p = h["payload"]
        _doi_tuong(p, "file sha256 bytes loai".split(), a + ".payload")
        _chuoi(p["sha256"], RE_HASH, a + ".payload.sha256")
        _so(p["bytes"], a + ".payload.bytes")
        _can(p["loai"] in ("XML", "UNKNOWN") and h["xml_status"] == "LOI", a)
        if p["file"] is not None:
            _tep(p, a + ".payload", tep, nho=0, goc=goc)
    _can(type(h["pdf_loi"]) is bool, a + ".pdf_loi", "SAI_KIEU")
    if h["file_pdf"] is None:
        _can(h["hash_pdf"] is None and h["vai_tro_pdf"] is None, a + ".file_pdf")
    else:
        _ten_tep(h["file_pdf"], a + ".file_pdf", goc)
        _can(h["file_pdf"].lower().endswith(".pdf"), a + ".file_pdf")
        _chuoi(h["hash_pdf"], RE_HASH, a + ".hash_pdf")
        _can(h["vai_tro_pdf"] == "XEM_LAI" and h["xml_status"] == "OK", a + ".vai_tro_pdf")
        tep.append(_Tep(h["file_pdf"], h["hash_pdf"], None))


def _kiem_manifest(m) -> list[_Tep]:
    _quet_bi_mat(m)
    hoi_cuu = isinstance(m, dict) and m.get("nguon") == "HOI_CUU"
    mo_rong = ["xap_xi"] if hoi_cuu else []
    if hoi_cuu and "thu_muc_tep_goc" in m:
        mo_rong.append("thu_muc_tep_goc")
    _doi_tuong(m, KHOA_MANIFEST + mo_rong, "$")
    goc = None
    if "thu_muc_tep_goc" in mo_rong:
        v = m["thu_muc_tep_goc"]
        _can(isinstance(v, str), "$.thu_muc_tep_goc", "SAI_KIEU")
        _can(".." not in Path(v).parts, "$.thu_muc_tep_goc", "DUONG_DAN_SAI")
        goc = _duong_dan(Path(v), thu_muc=True)
    _can(m["schema"] == SCHEMA, "$.schema")
    _can(m["nguon"] in ("TAI_MOI", "HOI_CUU"), "$.nguon")
    if m["nguon"] == "HOI_CUU":
        _can(m["xap_xi"] is True, "$.xap_xi")
    _chuoi(m["run_id"], r"[0-9]{8}-[0-9]{6}", "$.run_id")
    try:
        datetime.strptime(m["run_id"], "%Y%m%d-%H%M%S")
    except ValueError:
        _loi("THOI_DIEM_SAI", "$.run_id")
    _doi_tuong(m["phap_nhan"], ("uuid", "ma"), "$.phap_nhan")
    _chuoi(m["phap_nhan"]["uuid"], r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", "$.phap_nhan.uuid")
    _chuoi(m["phap_nhan"]["ma"], r"[A-Z0-9][A-Z0-9_-]{0,31}", "$.phap_nhan.ma")
    _chuoi(m["ky"], r"[0-9]{4}-(?:0[1-9]|1[0-2])", "$.ky")
    _can(m["chieu"] in ("purchase", "sold"), "$.chieu")
    _can(m["thu_muc_chieu"] == {"purchase": "mua_vao", "sold": "ban_ra"}[m["chieu"]], "$.thu_muc_chieu")
    bat_dau = _thoi_diem(m["bat_dau"], "$.bat_dau")
    _can(_thoi_diem(m["ket_thuc"], "$.ket_thuc") >= bat_dau, "$.ket_thuc")
    _chuoi(m["phien_ban_bo_tai"], r".+", "$.phien_ban_bo_tai")
    _chuoi(m["nguoi_bam"], RE_ACTOR, "$.nguoi_bam")
    c = m["context"]
    _doi_tuong(c, KHOA_CONTEXT, "$.context")
    for k in ("digest", "request_key_sha256", "selection_digest"):
        _chuoi(c[k], RE_HASH, "$.context." + k)
    for k, mau in (("nonce", r"[A-Za-z0-9_-]{22,128}"), ("profile_ref", r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"),
                   ("profile_revision", r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"),
                   ("source_instance", RE_INSTANCE), ("scope_ref", RE_INSTANCE)):
        _chuoi(c[k], mau, "$.context." + k)
    _can(c["actor_nguon"] == "crm_phien" and c["quyet_dinh_quyen"] == "NGOAI_PRODUCER_CHUA_KIEM", "$.context")
    _mang(c["profile_khoa_bo_qua"], "$.context.profile_khoa_bo_qua")
    _can(all(k == "DOWNLOAD_DIR" for k in c["profile_khoa_bo_qua"]), "$.context.profile_khoa_bo_qua")
    _doi_tuong(m["gioi_han"], ("xml_bytes", "zip_bytes", "zip_entries"), "$.gioi_han")
    for k, n in (("xml_bytes", XML_TOI_DA), ("zip_bytes", ZIP_TOI_DA), ("zip_entries", ZIP_ENTRIES_TOI_DA)):
        _so(m["gioi_han"][k], "$.gioi_han." + k, n, n)
    d = m["dang_nhap"]
    facts = ("captcha_da_go", "token_tai_su_dung", "thoi_gian_cho_dang_nhap_giay")
    _doi_tuong(d, (*facts, "do_luong"), "$.dang_nhap")
    for k in facts:
        f, a = d[k], "$.dang_nhap." + k
        _can(type(f) is dict, a, "SAI_KIEU")
        if f.get("trang_thai") == "OBSERVED":
            _doi_tuong(f, ("trang_thai", "gia_tri", "can_cu"), a)
            _chuoi(f["can_cu"], RE_MA, a + ".can_cu")
            v = f["gia_tri"]
            _can(type(v) is bool if k != facts[-1] else _la_so_huu_han(v) and v >= 0, a)
        else:
            _doi_tuong(f, ("trang_thai", "gia_tri", "ly_do"), a)
            _can(f["trang_thai"] == "UNKNOWN" and f["gia_tri"] is None, a)
            _chuoi(f["ly_do"], RE_MA, a + ".ly_do")
    _can(d["do_luong"] == ("COMPLETE" if all(d[k]["trang_thai"] == "OBSERVED" for k in facts) else "PARTIAL"), "$.dang_nhap.do_luong")
    _mang(m["nhom"], "$.nhom")
    for i, g in enumerate(m["nhom"], 1):
        a = f"$.nhom[{i - 1}]"
        _doi_tuong(g, "thu_tu path scope ttxly trang_thai so_ban_ghi so_moi loi".split(), a)
        _so(g["thu_tu"], a + ".thu_tu", i, i)
        _chuoi(g["path"], r"/api/[a-z0-9/-]+", a + ".path")
        _can(g["scope"] in ("query", "sco-query"), a + ".scope")
        _raw(g["ttxly"], a + ".ttxly")
        _can(g["trang_thai"] in ("OK", "LOI"), a + ".trang_thai")
        if g["trang_thai"] == "OK":
            _so(g["so_ban_ghi"], a + ".so_ban_ghi")
            _so(g["so_moi"], a + ".so_moi", lon=g["so_ban_ghi"])
            _can(g["loi"] is None, a + ".loi")
        else:
            _can(g["so_ban_ghi"] is None and g["so_moi"] is None, a)
            _kiem_loi(g["loi"], a + ".loi")
    _mang(m["hoa_don"], "$.hoa_don")
    tep = []
    for i, h in enumerate(m["hoa_don"], 1):
        _kiem_hd(h, i, tep, goc)
    _mang(m["loi_chung"], "$.loi_chung")
    for i, e in enumerate(m["loi_chung"]):
        _kiem_loi(e, f"$.loi_chung[{i}]")
    t = m["tong"]
    _doi_tuong(t, KHOA_TONG, "$.tong")
    dem = {"tong_hd": len(m["hoa_don"]), "pdf_ok": sum(h["file_pdf"] is not None for h in m["hoa_don"]),
           "pdf_loi": sum(h["pdf_loi"] for h in m["hoa_don"])}
    for k, s in (("xml_ok", "OK"), ("khong_xml_goc", "KHONG_XML_GOC"), ("xml_loi", "LOI"), ("xml_khong_yeu_cau", "KHONG_YEU_CAU")):
        dem[k] = sum(h["xml_status"] == s for h in m["hoa_don"])
    for k, n in dem.items():
        _so(t[k], "$.tong." + k, n, n)
    _can(t["bang_ke_trang_thai"] in ("OK", "LOI", "KHONG_YEU_CAU"), "$.tong.bang_ke_trang_thai")
    if t["bang_ke_trang_thai"] == "OK":
        _doi_tuong(t["bang_ke"], "file sha256 bytes so_cot".split(), "$.tong.bang_ke")
        _tep(t["bang_ke"], "$.tong.bang_ke", tep, goc=goc)
        _so(t["bang_ke"]["so_cot"], "$.tong.bang_ke.so_cot", 15 if hoi_cuu else 20, 20)
        _can(t["bang_ke"]["so_cot"] in (15, 20), "$.tong.bang_ke.so_cot")
    else:
        _can(t["bang_ke"] is None, "$.tong.bang_ke")
    ly_do = []
    if not m["nhom"]:
        ly_do.append("KHONG_CO_NHOM")
    if any(g["trang_thai"] != "OK" for g in m["nhom"]):
        ly_do.append("NHOM_LOI")
    if t["xml_loi"]:
        ly_do.append("XML_LOI")
    if any(h["zip"] is not None and h["zip"]["coverage"] != "COMPLETE" for h in m["hoa_don"]):
        ly_do.append("ZIP_PARTIAL")
    if t["bang_ke_trang_thai"] == "LOI":
        ly_do.append("BANG_KE_LOI")
    if m["loi_chung"]:
        ly_do.append("LOI_CHUNG")
    _mang(m["ly_do_partial"], "$.ly_do_partial")
    _can(m["ly_do_partial"] == ly_do, "$.ly_do_partial")
    _can(m["trang_thai"] in ("COMPLETE", "PARTIAL", "FAILED"), "$.trang_thai")
    _can(bool(m["loi_chung"]) if m["trang_thai"] == "FAILED" else
         m["trang_thai"] == ("PARTIAL" if ly_do else "COMPLETE"), "$.trang_thai")
    return tep


def _duong_dan(p: Path, *, thu_muc: bool) -> Path:
    try:
        return kiem_khong_reparse(p, la_thu_muc=thu_muc)
    except (DataError, OSError, ValueError):
        _loi("TEP_KHONG_AN_TOAN", p.name)


def _cap_json(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            _loi("KHOA_JSON_TRUNG")
        d[k] = v
    return d


def _hang_json_khong_hop_le(_):
    _loi("JSON_SAI")


def doc_manifest(duong_dan_run) -> KetQuaDocManifest:
    """Đọc/kiểm toàn bộ rồi trả dict raw kèm danh sách phân luồng cho M2c.

    Hash SHA-256 của bytes trên đĩa, không chuẩn hóa newline/XML trước khi băm.
    Lỗi hash mang tên file ở DataError.locator; thông báo không chứa dữ liệu thô.
    Hóa đơn thiếu khóa nằm ở hoa_don_thieu_khoa, không vào đề xuất; M2c chỉ
    xét tiếp hoa_don_du_khoa. Dict nguồn vẫn giữ đủ hóa đơn và số đếm gốc.
    """
    goc = _duong_dan(Path(os.path.abspath(duong_dan_run)), thu_muc=True)
    p = _duong_dan(goc / "manifest.json", thu_muc=False)
    try:
        with p.open("rb") as f:
            raw = f.read(JSON_TOI_DA + 1)
        _can(len(raw) <= JSON_TOI_DA, "manifest.json", "QUA_LON")
        m = json.loads(raw.decode("utf-8"), object_pairs_hook=_cap_json,
                       parse_constant=_hang_json_khong_hop_le)
    except DataError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError):
        _loi("JSON_SAI", "manifest.json")
    tep = _kiem_manifest(m)
    da_kiem = {}
    for t in tep:
        truoc = da_kiem.get(os.path.normcase(t.file))
        if truoc is not None:
            _can(truoc.sha256 == t.sha256 and (truoc.bytes is None or t.bytes is None or truoc.bytes == t.bytes),
                 t.file, "TEP_KHAI_BAO_MAU_THUAN")
        p = _duong_dan(goc / t.file, thu_muc=False)
        try:
            h, n = hashlib.sha256(), 0
            with p.open("rb") as f:
                while b := f.read(1024 * 1024):
                    h.update(b)
                    n += len(b)
                    if t.bytes is not None:
                        _can(n <= t.bytes, t.file, "BYTES_LECH")
        except OSError:
            _loi("TEP_KHONG_DOC_DUOC", t.file)
        _can(h.hexdigest() == t.sha256, t.file, "HASH_LECH")
        _can(t.bytes is None or n == t.bytes, t.file, "BYTES_LECH")
        da_kiem[os.path.normcase(t.file)] = t
    return KetQuaDocManifest(m)


def phan_loai_file_tren_dia(duong_dan_run, manifest) -> list[str]:
    """Danh sách đường dẫn tương đối XML/PDF CHUA_RO_NGUON, thứ tự ổn định.

    manifest phải qua doc_manifest trước khi caller dùng cho intake. Hàm này
    kiểm lại hình dạng nhưng không thay thế lần kiểm bytes ở doc_manifest.
    """
    tep = _kiem_manifest(dict(manifest) if isinstance(manifest, KetQuaDocManifest) else manifest)
    goc = _duong_dan(Path(manifest["thu_muc_tep_goc"]) if "thu_muc_tep_goc" in manifest
                    else Path(os.path.abspath(duong_dan_run)), thu_muc=True)
    da_khai_bao = {os.path.normcase((Path(t.file).relative_to(goc).as_posix()
                                  if "thu_muc_tep_goc" in manifest else t.file)) for t in tep}
    chua_ro = []

    def loi_duyet(_):
        _loi("KHONG_DUYET_DUOC")

    for thu_muc, ds_thu_muc, ds_file in os.walk(goc, followlinks=False, onerror=loi_duyet):
        for ten in ds_thu_muc:
            _duong_dan(Path(thu_muc) / ten, thu_muc=True)
        for ten in ds_file:
            p = Path(thu_muc) / ten
            if p.suffix.lower() in (".xml", ".pdf"):
                _duong_dan(p, thu_muc=False)
                rel = p.relative_to(goc).as_posix()
                if os.path.normcase(rel) not in da_khai_bao:
                    chua_ro.append(rel)
    return sorted(chua_ro)
