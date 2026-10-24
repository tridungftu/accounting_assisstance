"""M2c: kế hoạch intake thuần, nhận qua capture/consumer K2 hiện hữu.

Không sửa XML để ép policy vào dữ liệu gốc. Kế hoạch chỉ có metadata,
không chứa bytes XML/manifest thô hay credential. Quyền/registry do K2 kiểm.
Các giới hạn của consumer R15 được trả tường minh, không giả là đã promote.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from ...ha_tang.primitives import DataError, canonical_json, sha256
from ...nguon.hoa_don_xml import doc_hoa_don_xml
from .cau_hinh import kiem_khong_reparse
from .chinh_sach_tien_te import ap_dung
from .manifest import RE_CAM, RE_GIA_TRI_CAM, doc_manifest, phan_loai_file_tren_dia

if TYPE_CHECKING:
    from ...k2.hoa_don import HoaDonK2


KHOANG_THIEU_K2 = (
    "K2_CHUA_NHAN_BANG_KE",
    "K2_REVISION_THEO_SEMANTIC_KHONG_THEO_HASH_BYTES",
    "K2_CHUA_REVISION_TTHAI_CONG",
    "K2_CHUA_PROMOTE_TIEN_TE_THEO_POLICY",
    "K2_CHUA_HOLD_XUNG_DOT_TIEN_TE_MANIFEST",
    "K2_CHUA_GHI_QUAN_HE_DIEU_CHINH_THAY_THE",
    "K2_BAN_RA_CHI_LA_UNG_VIEN_NGUON",
)


def _loi(ma):
    raise DataError("M2_00_NHAN_" + ma, "Không nhận nguồn: " + ma + ".") from None


def _text(res, ten):
    f = res.header(ten).duy_nhat
    if f is None:
        return None
    return f.lexeme if f.state == "TEXT" else None


def _ngoai_le(ma, *, ordinal=None, **them):
    return {"ma": ma, "item_ordinal": ordinal, **them}


def _file_chua_ro(goc, manifest):
    # M2b đã phân loại XML/PDF; bổ sung các loại tệp khác (kể cả bảng kê)
    # mà M2b không liệt kê. Chỉ kiểm metadata đường dẫn, không mở nội dung.
    out = phan_loai_file_tren_dia(goc, manifest)
    khai_bao = {os.path.normcase("manifest.json")}

    def ghi_ten(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k in ("file", "file_xml", "file_pdf") and isinstance(x, str):
                    khai_bao.add(os.path.normcase(x))
                else:
                    ghi_ten(x)
        elif isinstance(v, list):
            for x in v:
                ghi_ten(x)

    ghi_ten(manifest)
    for p in goc.rglob("*"):
        if p.is_file() and p.suffix.lower() not in (".xml", ".pdf"):
            kiem_khong_reparse(p, la_thu_muc=False)
            rel = p.relative_to(goc).as_posix()
            if os.path.normcase(rel) not in khai_bao:
                out.append(rel)
    return sorted(out)


def _bo_sung_xml(raw):
    """Chỉ bổ sung TGia/quan hệ chưa có trong DTO strict; không đọc tiền/dòng.

    Caller chỉ gọi sau khi reader đã chấp nhận encoding, DOCTYPE và cấu trúc
    header. Đọc đúng path, không strip namespace hay descendant search.
    TCHDon lưu raw: không suy quan hệ từ tthai của cổng.
    """
    root = ET.fromstring(raw)
    tt = root.find("./DLHDon/TTChung")
    tg = tt.findall("TGia")
    thong_tin = {}
    if tg:
        thong_tin["TGia"] = (tg[0].text or "") if len(tg) == 1 and not len(tg[0]) else None
    quan_he, mo_ho = [], False
    for i, el in enumerate(tt.findall("TTHDLQuan"), 1):
        fields = {}
        for k in ("TCHDon", "LHDCLQuan", "KHMSHDCLQuan", "KHHDCLQuan", "SHDCLQuan", "NLHDCLQuan"):
            ds = el.findall(k)
            if len(ds) == 1 and not len(ds[0]):
                fields[k] = ds[0].text or ""
        if not all(fields.get(k) for k in ("TCHDon", "KHMSHDCLQuan", "KHHDCLQuan", "SHDCLQuan")):
            mo_ho = True
            continue
        if RE_GIA_TRI_CAM.search(canonical_json(fields)):
            _loi("XML_CO_BI_MAT")
        quan_he.append({"locator": f"/HDon/DLHDon/TTChung/TTHDLQuan[{i}]", "raw": fields})
    return thong_tin, quan_he, mo_ho


def lap_ke_hoach_nhan(thu_muc_run, *, ma_phap_nhan: str) -> dict:
    """Đọc/kiểm bytes theo M2b, không CSDL/ghi đĩa/gọi cổng.

    ma_phap_nhan do caller lấy từ profile tin cậy, không phải tự lấy từ
    manifest. Chiều bắt buộc khớp thư mục cha mua_vao/ban_ra của run.
    Identity 6 phần theo binding hiện có (SHDon bỏ số 0 đầu); raw giữ riêng.
    Kế hoạch không phải quyết định duyệt hay bằng chứng quyền.
    """
    goc = Path(thu_muc_run).absolute()
    m = doc_manifest(goc)
    if ma_phap_nhan != m["phap_nhan"]["ma"]:
        _loi("PHAP_NHAN_KHONG_KHOP_PROFILE")
    # Hồi cứu giữ file tại chỗ: manifest có thể nằm ngay trong thư mục chiều
    # cũ. Không bắt M2d di chuyển dữ liệu vào một thư mục run mới.
    thu_muc_chieu = goc.name if m["nguon"] == "HOI_CUU" and goc.name in ("mua_vao", "ban_ra") else goc.parent.name
    if thu_muc_chieu != m["thu_muc_chieu"]:
        _loi("THU_MUC_RUN_KHONG_KHOP")
    if m["nguon"] == "TAI_MOI" and (
        goc.name != m["run_id"] or goc.parent.parent.name != m["ky"]
        or goc.parent.parent.parent.name != ma_phap_nhan
    ):
        _loi("THU_MUC_RUN_KHONG_KHOP")
    chieu = {"mua_vao": "MUA_VAO", "ban_ra": "BAN_RA"}[thu_muc_chieu]
    ngoai_le = [_ngoai_le("THIEU_KHOA", ordinal=h["item_ordinal"], key_thieu=h["key_thieu"])
                for h in m.hoa_don_thieu_khoa]
    for h in m["hoa_don"]:
        if h["xml_status"] == "LOI":
            ngoai_le.append(_ngoai_le("TAI_LOI", ordinal=h["item_ordinal"], loi=h["loi"]))
        if h["pdf_loi"]:
            ngoai_le.append(_ngoai_le("TAI_LOI_PDF", ordinal=h["item_ordinal"]))
    for g in m["nhom"]:
        if g["loi"]:
            ngoai_le.append(_ngoai_le("TAI_LOI_NHOM", nhom_thu_tu=g["thu_tu"], loi=g["loi"]))
    for e in m["loi_chung"]:
        ngoai_le.append(_ngoai_le("TAI_LOI_CHUNG", loi=e))
    if m["tong"]["bang_ke_trang_thai"] == "LOI":
        ngoai_le.append(_ngoai_le("TAI_LOI_BANG_KE"))
    if m["trang_thai"] != "COMPLETE":
        ngoai_le.append(_ngoai_le("RUN_" + m["trang_thai"]))
    muc = []
    for h in m.hoa_don_du_khoa:
        ordinal = h["item_ordinal"]
        if h["xml_status"] in ("LOI", "KHONG_YEU_CAU"):
            if h["xml_status"] == "KHONG_YEU_CAU":
                ngoai_le.append(_ngoai_le("XML_CHUA_YEU_CAU", ordinal=ordinal))
            continue
        parts = h["key_canonical"].split("|")
        if not re.fullmatch(r"[0-9]+", parts[3]) or any(
            not p.isascii() or not all(0x20 <= ord(c) < 0x7f for c in p) for p in parts[:3]
        ):
            ngoai_le.append(_ngoai_le("IDENTITY_KHONG_HOP_LE", ordinal=ordinal))
            continue
        identity = [ma_phap_nhan, chieu, *parts[:3], parts[3].lstrip("0") or "0"]
        base = {"item_ordinal": ordinal, "identity": identity, "key_canonical": h["key_canonical"],
                "key_raw": dict(h["key_raw"]), "tthai_cong": h["tthai_cong"],
                "xml_status": h["xml_status"], "scope": h["scope"], "ttxly": h["ttxly"],
                "tdlap": h["tdlap"], "dvtte_cong": h["dvtte_cong"],
                "container_sha256": None if h["zip"] is None else h["zip"]["sha256"]}
        if h["xml_status"] == "KHONG_XML_GOC":
            if m["tong"]["bang_ke_trang_thai"] != "OK" or m["tong"]["bang_ke"] is None:
                ngoai_le.append(_ngoai_le("BANG_KE_THIEU", ordinal=ordinal))
                continue
            muc.append({**base, "bang_chung": "BANG_KE", "can_cu": h["can_cu"],
                        "bang_ke": m["tong"]["bang_ke"], "tep_xml": [], "quan_he": [], "tien_te": None})
            continue
        for thu_tu_tep, t in enumerate(h["xml_tep"], 1):
            p = kiem_khong_reparse(goc / t["file"], la_thu_muc=False)
            raw = p.read_bytes()
            if sha256(raw) != t["sha256"] or len(raw) != t["bytes"]:
                _loi("XML_DOI_SAU_KIEM_HASH")
            res = doc_hoa_don_xml(raw)
            if not res.header_fields:
                ngoai_le.append(_ngoai_le("XML_KHONG_DOC_DUOC", ordinal=ordinal, file=t["file"]))
                continue
            xml_key = [_text(res, k) for k in ("NBan/MST", "KHMSHDon", "KHHDon", "SHDon")]
            # Manifest là authority của identity; XML khác → ngoại lệ, không chọn một bên.
            if (xml_key[:3] != parts[:3] or xml_key[3] is None
                    or not re.fullmatch(r"[0-9]+", xml_key[3])
                    or (xml_key[3].lstrip("0") or "0") != identity[-1]):
                ngoai_le.append(_ngoai_le("IDENTITY_XML_MANIFEST_KHAC", ordinal=ordinal, file=t["file"]))
                continue
            xml, quan_he, mo_ho = _bo_sung_xml(raw)
            xml.update(mst_ban=_text(res, "NBan/MST"), mst_mua=_text(res, "NMua/MST"))
            f = res.header("DVTTe").duy_nhat
            if f is None or f.state != "ABSENT":
                xml["DVTTe"] = None if f is None else f.lexeme
            tien_te = asdict(ap_dung(xml, {"dvtte_cong": h["dvtte_cong"]}))
            if tien_te["trang_thai"] in ("CHUA_RO", "XUNG_DOT"):
                ngoai_le.append(_ngoai_le("TIEN_TE_" + tien_te["trang_thai"], ordinal=ordinal, file=t["file"]))
            if mo_ho:
                ngoai_le.append(_ngoai_le("QUAN_HE_CHUA_RO", ordinal=ordinal, file=t["file"]))
            muc.append({**base, "bang_chung": "XML", "can_cu": None, "tep_xml": [dict(t)],
                        "thu_tu_tep": thu_tu_tep, "bang_ke": None, "quan_he": quan_he, "tien_te": tien_te,
                        "issues_xml": sorted({i.code for i in res.issues})})
        if h["zip"] is not None and h["zip"]["coverage"] != "COMPLETE":
            ngoai_le.append(_ngoai_le("TAI_LOI_ZIP_PARTIAL", ordinal=ordinal))
    return {"thu_muc_run": str(goc), "ma_phap_nhan": ma_phap_nhan, "run_id": m["run_id"],
            "nguon": m["nguon"], "ky": m["ky"], "chieu": chieu,
            "bat_dau": m["bat_dau"], "ket_thuc": m["ket_thuc"], "xap_xi": m.get("xap_xi", False),
            "context": {k: m["context"][k] for k in ("source_instance", "scope_ref", "profile_ref", "profile_revision")},
            "coverage": "COMPLETE_INPUT" if m["trang_thai"] == "COMPLETE" else "PARTIAL_INPUT",
            "muc": muc, "ngoai_le": ngoai_le,
            "chua_ro_nguon": [{"file": "TEP_DA_AN_TEN" if RE_CAM.search(f) or RE_GIA_TRI_CAM.search(f) else f,
                               "trang_thai": "CHUA_RO_NGUON", "vao_de_xuat": False}
                              for f in _file_chua_ro(goc, m)]}


def nhan_vao_k2(ke_hoach: dict, hoa_don_k2: HoaDonK2, *, actor: str,
                source_instance: str, scope_ref: str) -> dict:
    """Mỗi XML đi qua API công khai → stage/capture → m2_tieu_thu_quan_sat.

    Instance/scope/actor do caller tin cậy cung cấp; không cấp quyền bằng context
    manifest. Replay dùng key ổn định theo run + item + entry; không chứa hash
    nội dung để sửa cùng run không lách thành thao tác mới. CROSSWALK chỉ là
    provenance, không làm authority/promotion. BANG_KE giữ chờ vì API chưa nhận.
    """
    moi = lap_ke_hoach_nhan(ke_hoach["thu_muc_run"], ma_phap_nhan=ke_hoach["ma_phap_nhan"])
    if moi != ke_hoach:
        _loi("KE_HOACH_DA_DOI")
    if (source_instance, scope_ref) != (moi["context"]["source_instance"], moi["context"]["scope_ref"]):
        _loi("PHAM_VI_KHONG_KHOP")
    ket_qua = []
    for h in moi["muc"]:
        if h["bang_chung"] == "BANG_KE":
            ket_qua.append({"item_ordinal": h["item_ordinal"], "trang_thai": "GIU_CHO_K2",
                            "ly_do": "K2_CHUA_NHAN_BANG_KE"})
            continue
        if h["tien_te"]["trang_thai"] in ("CHUA_RO", "XUNG_DOT"):
            # Consumer hiện hữu không đọc policy/bảng kê. Gọi nhan với XML VND
            # ở đây có thể làm FIRST_OBSERVATION eligible dù bảng kê mâu thuẫn.
            ket_qua.append({"item_ordinal": h["item_ordinal"], "trang_thai": "GIU_CHO_K2",
                            "ly_do": "TIEN_TE_" + h["tien_te"]["trang_thai"]})
            continue
        t = h["tep_xml"][0]
        p = kiem_khong_reparse(Path(moi["thu_muc_run"]) / t["file"], la_thu_muc=False)
        raw = p.read_bytes()
        if sha256(raw) != t["sha256"] or len(raw) != t["bytes"]:
            _loi("XML_DOI_SAU_KIEM_HASH")
        provenance = {"schema": "m2c.intake.v1", "nguon": moi["nguon"], "run_id": moi["run_id"],
                      "ky": moi["ky"], "bat_dau": moi["bat_dau"], "ket_thuc": moi["ket_thuc"],
                      "xap_xi": moi["xap_xi"], "muc": h, "authority": "RAW_EVIDENCE_ONLY"}
        cw = canonical_json(provenance).encode("utf-8")
        token = canonical_json([moi["ma_phap_nhan"], moi["ky"], moi["chieu"], moi["run_id"],
                                h["item_ordinal"], h["thu_tu_tep"]]).encode("utf-8")
        try:
            r = hoa_don_k2.nhan_theo_manifest(
                actor, identity=h["identity"], source_instance=source_instance, scope_ref=scope_ref,
                coverage=moi["coverage"], reported_errors=sorted({e["ma"] for e in moi["ngoai_le"]}),
                client_key="M2c:" + sha256(token), native=raw, artifact_name=t["file"], crosswalk=cw)
        except DataError as e:
            ket_qua.append({"item_ordinal": h["item_ordinal"], "file": t["file"],
                            "trang_thai": "GIU_CHO_K2", "ly_do": e.code, "thong_bao": str(e)})
            continue
        # Chỉ trả whitelist biên nhận; không phản chiếu dict/log bất kỳ từ dịch vụ.
        promote = r.get("promote") or {}
        items = [{k: v for k, v in it.items() if k in (
            "observation_id", "hoa_don_id", "phien_ban_id", "phap_nhan_id", "classification", "phien_ban_moi"
        )} for it in promote.get("items", [])]
        ket_qua.append({"item_ordinal": h["item_ordinal"], "file": t["file"],
                        "trang_thai": "DA_GHI_QUAN_SAT" if items else "GIU_CHO_K2",
                        "lan_tiep_nhan_id": r["lan_tiep_nhan_id"], "lap_lai": r["lap_lai"], "items": items})
    return {"run_id": moi["run_id"], "ket_qua": ket_qua, "ngoai_le": moi["ngoai_le"],
            "giu_cho_k2": [h for h in ket_qua if h["trang_thai"] == "GIU_CHO_K2"],
            "chua_ro_nguon": moi["chua_ro_nguon"], "khoang_thieu_k2": list(KHOANG_THIEU_K2)}
