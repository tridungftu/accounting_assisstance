"""CRM-41-02 G1 — đọc placeholder `{{ten_o}}` trong mẫu DOCX (thuần: không tệp/actor/I-O/Office/AI/mạng).

`doc_mau_docx(raw, *, limits=None) -> dict` trả facts phát hiện có cấu trúc:
- SHA-256 + độ dài của raw và của từng member; phiên bản bộ đọc;
- các phần đã quét theo thứ tự: thân văn bản (`word/document.xml`, gồm bảng và bảng lồng) rồi header/footer THỰC SỰ được tham chiếu
  (`w:headerReference`/`w:footerReference` → quan hệ của document);
- mỗi lần xuất hiện: tên, phần, vị trí (đường dẫn p/tbl/tr/tc trong phần), chỉ số đoạn, khoảng ký tự trong văn bản ghép của đoạn, các run
  chứa nó, khoảng ký tự thực trong từng run (`khoang_run`) và cờ tách run. Ghép `w:t` qua các run CHỈ trong cùng đoạn; không ghép giữa
  đoạn/ô/phần. `doan`: văn bản ghép ĐẦY ĐỦ (giới hạn `doan_ky_tu`, vượt → INCOMPLETE) + khoảng của mọi run cho đoạn có ô/ngoặc lẻ.
  Đơn vị khoảng: code point Unicode, nửa mở. Mọi XML giải mã theo một quy tắc (UTF-8/UTF-16) trước khi chặn DTD và phân tích.

Fail-closed TRƯỚC khi duyệt XML: không phải ZIP, member trùng tên, đường dẫn lạ, mã hóa, bom nén (kích thước/tỷ lệ/số member), macro
(vbaProject), nội dung chủ động (activeX/OLE nhúng/altChunk), DTD/ENTITY, quan hệ ngoài (TargetMode=External), loại nội dung macro.
Kênh hiển thị chưa hỗ trợ (hộp văn bản, trường; footnote/endnote/comment… có bất kỳ `{`/`}` trong văn bản đã phân tích) và Track Changes → `INCOMPLETE` có lý do
(lưu được nhưng chặn kiểm/duyệt), không bỏ sót lặng lẽ. Không tính byte-span giả hay hash từ ET.tostring.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
import zlib

from ..ha_tang.primitives import DataError

PHIEN_BAN_BO_DOC = "crm.mau_docx/2"  # /2: giải mã XML thống nhất (P01), kênh chưa quét phân tích XML (P02), văn bản đoạn + khoảng run (P03)
GIOI_HAN = {"tep": 20 * 1024 * 1024, "so_member": 400, "member": 30 * 1024 * 1024, "tong": 120 * 1024 * 1024, "ty_le": 120, "doan_ky_tu": 20000}
DON_VI_KHOANG = "UNICODE_CODE_POINT_NUA_MO"  # [bat_dau, ket_thuc) trên văn bản ghép w:t của MỘT đoạn
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W_STRICT = "http://purl.oclc.org/ooxml/wordprocessingml/main"
R_NS = ("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "http://purl.oclc.org/ooxml/officeDocument/relationships")
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
RE_O = re.compile(r"\{\{\s*([A-Za-z0-9_]{1,80})\s*\}\}")
RE_MO = re.compile(r"\{\{|\}\}")
SUA_DOI = {"ins", "del", "moveFrom", "moveTo", "rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "trPrChange", "tcPrChange", "numberingChange",
           "cellIns", "cellDel", "cellMerge"}
KENH_CHUA_HO_TRO = {"txbxContent": "HOP_VAN_BAN", "fldSimple": "TRUONG", "instrText": "TRUONG"}


def _loi(code: str, msg: str):
    raise DataError(code, msg)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ten_cuc_bo(tag) -> tuple[str | None, str]:
    if not isinstance(tag, str) or not tag.startswith("{"):
        return None, tag if isinstance(tag, str) else ""
    uri, _, ten = tag[1:].partition("}")
    return uri, ten


def _la_w(tag, ten: str) -> bool:
    uri, t = _ten_cuc_bo(tag)
    return uri in (W, W_STRICT) and t == ten


RE_KHAI_BAO = re.compile(r"\A<\?xml\s[^>]*?\?>")
RE_MA_KHAI_BAO = re.compile(r"""\bencoding\s*=\s*["']([A-Za-z0-9._-]+)["']""")
RE_DTD = re.compile(r"<!\s*(DOCTYPE|ENTITY|ELEMENT|ATTLIST|NOTATION)", re.I)


def _giai_ma_xml(raw: bytes, ten: str) -> str:
    """P01: giải mã XML THEO MỘT QUY TẮC trước mọi kiểm DTD/duyệt. OOXML chỉ dùng UTF-8/UTF-16 → nhận diện BOM/mẫu `<?` của UTF-16 LE/BE,
    còn lại UTF-8; giải mã strict; khai báo encoding (nếu có) phải cùng họ với mã đã nhận diện. Mã khác (UTF-32, Latin-1…) → không nhận."""
    raw = bytes(raw)
    if raw[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff") or raw[:4] in (b"<\x00\x00\x00", b"\x00\x00\x00<"):
        _loi("CRM_MAU_XML_HONG", f"Phần {ten} dùng mã UTF-32 — không nhận.")
    if raw[:3] == b"\xef\xbb\xbf":
        ho, ma, than = "utf-8", "utf-8", raw[3:]
    elif raw[:2] == b"\xff\xfe":
        ho, ma, than = "utf-16", "utf-16-le", raw[2:]
    elif raw[:2] == b"\xfe\xff":
        ho, ma, than = "utf-16", "utf-16-be", raw[2:]
    elif raw[:2] == b"<\x00":
        ho, ma, than = "utf-16", "utf-16-le", raw
    elif raw[:2] == b"\x00<":
        ho, ma, than = "utf-16", "utf-16-be", raw
    else:
        ho, ma, than = "utf-8", "utf-8", raw
    try:
        text = than.decode(ma)  # strict
    except UnicodeDecodeError:
        _loi("CRM_MAU_XML_HONG", f"Phần {ten} không giải mã được theo {ma}.")
    m = RE_KHAI_BAO.match(text)
    if m:
        k = RE_MA_KHAI_BAO.search(m.group(0))
        if k:
            khai = k.group(1).lower().replace("_", "-")
            hop = {"utf-8": {"utf-8", "utf8"}, "utf-16": {"utf-16", "utf16", "utf-16le", "utf-16be", "utf-16-le", "utf-16-be"}}[ho]
            if khai not in hop:
                _loi("CRM_MAU_XML_HONG", f"Phần {ten} khai báo mã {k.group(1)} không khớp/không hỗ trợ.")
    return text


def _parse(raw: bytes, ten: str):
    text = _giai_ma_xml(raw, ten)
    if RE_DTD.search(text):  # trên văn bản ĐÃ giải mã (mọi mã đã nhận), trước khi đưa cho bộ phân tích
        _loi("CRM_MAU_DTD", f"Phần {ten} có DOCTYPE/ENTITY — không nhận.")
    m = RE_KHAI_BAO.match(text)
    try:
        # phân tích CHÍNH chuỗi đã giải mã (bỏ khai báo đã kiểm) — không để bộ phân tích tự đoán mã khác với bước kiểm
        return ET.fromstring(text[m.end():] if m else text)
    except (ET.ParseError, ValueError, LookupError):
        _loi("CRM_MAU_XML_HONG", f"Phần {ten} không phải XML hợp lệ.")


def _kiem_zip(raw: bytes, gh: dict) -> tuple[zipfile.ZipFile, dict]:
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        _loi("CRM_MAU_TEP_RONG", "Tệp mẫu rỗng.")
    if len(raw) > gh["tep"]:
        _loi("CRM_MAU_TEP_QUA_LON", "Tệp mẫu vượt giới hạn kích thước.")
    if bytes(raw[:4]) != b"PK\x03\x04":
        _loi("CRM_MAU_TEP_SAI", "Không phải tệp Word .docx (gói ZIP/OOXML).")
    try:
        z = zipfile.ZipFile(io.BytesIO(bytes(raw)))
        infos = z.infolist()
    except (zipfile.BadZipFile, ValueError, OSError, EOFError):
        _loi("CRM_MAU_TEP_SAI", "Không mở được gói ZIP của tệp mẫu.")
    if len(infos) > gh["so_member"]:
        _loi("CRM_MAU_BOM_NEN", "Gói có quá nhiều phần.")
    ten_da = set()
    tong = 0
    for i in infos:
        n = i.filename
        if n in ten_da:
            _loi("CRM_MAU_TRUNG_PHAN", f"Gói có hai phần cùng tên {n}.")
        ten_da.add(n)
        if n.startswith(("/", "\\")) or "\\" in n or ".." in n.split("/") or re.match(r"^[A-Za-z]:", n) or "\x00" in n:
            _loi("CRM_MAU_DUONG_DAN", "Gói chứa đường dẫn nội bộ không an toàn.")
        if i.flag_bits & 0x1:
            _loi("CRM_MAU_MA_HOA", "Gói có phần được mã hóa — không nhận.")
        if i.file_size > gh["member"]:
            _loi("CRM_MAU_BOM_NEN", f"Phần {n} quá lớn sau giải nén.")
        if i.compress_size > 0 and i.file_size / i.compress_size > gh["ty_le"] and i.file_size > 1024 * 1024:
            _loi("CRM_MAU_BOM_NEN", f"Phần {n} có tỷ lệ nén bất thường.")
        tong += i.file_size
        thap = n.lower()
        if thap.endswith("vbaproject.bin") or thap.endswith("vbadata.xml"):
            _loi("CRM_MAU_MACRO", "Tệp có macro — không nhận.")
        if thap.startswith("word/activex/") or thap.startswith("word/embeddings/"):
            _loi("CRM_MAU_NOI_DUNG_CHU_DONG", "Tệp có nội dung chủ động/đối tượng nhúng — không nhận.")
    if tong > gh["tong"]:
        _loi("CRM_MAU_BOM_NEN", "Tổng dung lượng giải nén vượt giới hạn.")
    return z, {i.filename: i for i in infos}


def _doc_phan(z, infos, ten: str) -> bytes:
    if ten not in infos:
        _loi("CRM_MAU_THIEU_PHAN", f"Thiếu phần {ten}.")
    try:
        return z.read(ten)
    except (zipfile.BadZipFile, zlib.error, KeyError, ValueError, OSError, EOFError, RuntimeError, NotImplementedError):
        _loi("CRM_MAU_TEP_SAI", f"Không giải nén được phần {ten}.")


def _rels(z, infos, ten_rels: str) -> dict:
    """Quan hệ của một phần: Id → (Type, Target, External). Quan hệ ngoài (TargetMode=External) → fail-closed."""
    if ten_rels not in infos:
        return {}
    goc = _parse(_doc_phan(z, infos, ten_rels), ten_rels)
    out = {}
    for el in goc:
        if _ten_cuc_bo(el.tag)[1] != "Relationship":
            continue
        if (el.get("TargetMode") or "").lower() == "external":
            _loi("CRM_MAU_QUAN_HE_NGOAI", "Tệp có quan hệ tới tài nguyên bên ngoài (TargetMode=External) — không nhận.")
        out[el.get("Id")] = (el.get("Type") or "", el.get("Target") or "")
    return out


def _chuan_dich(goc_phan: str, target: str) -> str:
    """Target tương đối theo thư mục của phần nguồn → tên member chuẩn; không ra ngoài gói."""
    if target.startswith("/"):
        parts = target[1:].split("/")
    else:
        parts = goc_phan.rsplit("/", 1)[0].split("/") + target.split("/") if "/" in goc_phan else target.split("/")
    out = []
    for p in parts:
        if p in ("", "."):
            continue
        if p == "..":
            if not out:
                _loi("CRM_MAU_DUONG_DAN", "Quan hệ trỏ ra ngoài gói.")
            out.pop()
        else:
            out.append(p)
    return "/".join(out)


def _r_id(el, ten: str):
    for ns in R_NS:
        v = el.get(f"{{{ns}}}{ten}")
        if v is not None:
            return v
    return None


def _quet_phan(goc_xml, ten_phan: str, loai_phan: str, sha_phan: str, ly_do: list, dem_doan: list, ket: list, ds_doan: list, gh: dict) -> None:
    """Duyệt đoạn theo thứ tự tài liệu (kể cả bảng/bảng lồng); ghép w:t qua run trong CÙNG đoạn."""
    def di(el, duong: list):
        dem = {}
        for con in list(el):
            uri, t = _ten_cuc_bo(con.tag)
            if uri in (W, W_STRICT) and t in KENH_CHUA_HO_TRO:
                ly_do.append({"ma": "KENH_CHUA_HO_TRO", "kenh": KENH_CHUA_HO_TRO[t], "phan": ten_phan})
            if uri in (W, W_STRICT) and t in SUA_DOI:
                ly_do.append({"ma": "TRACK_CHANGES", "the": t, "phan": ten_phan})
            if uri in (W, W_STRICT) and t == "altChunk":
                _loi("CRM_MAU_NOI_DUNG_CHU_DONG", "Tệp nhúng nội dung ngoài (altChunk) — không nhận.")
            if uri in (W, W_STRICT) and t in ("p", "tbl", "tr", "tc"):
                dem[t] = dem.get(t, 0) + 1
                buoc = duong + [f"{t}[{dem[t]}]"]
                if t == "p":
                    _doan(con, "/".join(buoc))
                    di(con, buoc)  # đoạn có thể chứa hộp văn bản (đã ghi INCOMPLETE ở trên); không ghép vào đoạn ngoài
                else:
                    di(con, buoc)
            else:
                di(con, duong)

    def _doan(p, vi_tri: str):
        dem_doan[0] += 1
        chi_so = dem_doan[0]
        manh = []  # (run_index, text) — chỉ run thuộc CHÍNH đoạn này (không đi vào đoạn lồng/hộp văn bản)
        r_idx = 0
        ngan = [iter(list(p))]
        while ngan:
            el = next(ngan[-1], None)
            if el is None:
                ngan.pop()
                continue
            if _la_w(el.tag, "p") or _la_w(el.tag, "txbxContent"):
                continue
            if _la_w(el.tag, "r"):
                r_idx += 1
                for t in el:
                    if _la_w(t.tag, "t") and t.text:
                        manh.append((r_idx, t.text))
                continue
            ngan.append(iter(list(el)))
        if not manh:
            return
        van_ban = "".join(x for _, x in manh)
        # P03: khoảng ký tự THỰC của từng run trong văn bản ghép của đoạn (đơn vị: code point Unicode, nửa mở [bat_dau, ket_thuc)),
        # tính từ chính traversal — một run có thể gồm nhiều w:t liên tiếp
        moc, vt, khoang_run = [], 0, {}
        for idx, x in manh:
            moc.append(vt)
            a0, _ = khoang_run.get(idx, (vt, vt))
            khoang_run[idx] = (a0, vt + len(x))
            vt += len(x)
        co_o = False
        for m in RE_O.finditer(van_ban):
            co_o = True
            a, b = m.span()
            runs = sorted({manh[i][0] for i in range(len(manh)) if moc[i] < b and moc[i] + len(manh[i][1]) > a})
            khoang = [{"run": i, "bat_dau": max(a, khoang_run[i][0]), "ket_thuc": min(b, khoang_run[i][1]),
                       "bat_dau_trong_run": max(a, khoang_run[i][0]) - khoang_run[i][0], "ket_thuc_trong_run": min(b, khoang_run[i][1]) - khoang_run[i][0]}
                      for i in runs]
            ket.append({"ten": m.group(1), "phan": ten_phan, "loai_phan": loai_phan, "phan_sha256": sha_phan, "vi_tri": vi_tri, "doan": chi_so,
                        "bat_dau": a, "ket_thuc": b, "runs": runs, "khoang_run": khoang, "tach_run": len(runs) > 1,
                        "van_ban_o": van_ban[a:b], "ngu_canh": van_ban[:400]})
        con_lai = RE_O.sub("", van_ban)
        le = bool(RE_MO.search(con_lai))
        if le:
            ly_do.append({"ma": "NGOAC_LE", "phan": ten_phan, "vi_tri": vi_tri})
        if co_o or le:  # đoạn có ô hoặc ngoặc lẻ: giữ văn bản ghép đầy đủ (trong giới hạn) + khoảng của MỌI run để kiểm chứng lại
            cat = len(van_ban) > gh["doan_ky_tu"]
            if cat:
                ly_do.append({"ma": "DOAN_QUA_DAI", "phan": ten_phan, "vi_tri": vi_tri})
            ds_doan.append({"chi_so": chi_so, "phan": ten_phan, "loai_phan": loai_phan, "vi_tri": vi_tri, "do_dai": len(van_ban),
                            "van_ban": van_ban[:gh["doan_ky_tu"]], "cat_bot": cat,
                            "runs": [{"run": i, "bat_dau": s, "ket_thuc": e} for i, (s, e) in sorted(khoang_run.items())]})

    di(goc_xml, [])


# P02 (TIEP-02): căn cứ phân loại phần = LOẠI QUAN HỆ (đuôi URI, transitional/strict như nhau) → (phần tử gốc mong đợi, đuôi ContentType hợp lệ)
LOAI_QUAN_HE = {
    "header": ("hdr", ("header+xml",)), "footer": ("ftr", ("footer+xml",)),
    "footnotes": ("footnotes", ("footnotes+xml",)), "endnotes": ("endnotes", ("endnotes+xml",)), "comments": ("comments", ("comments+xml",)),
    "styles": ("styles", ("styles+xml",)), "stylesWithEffects": ("styles", ("stylesWithEffects+xml",)), "settings": ("settings", ("settings+xml",)),
    "webSettings": ("webSettings", ("webSettings+xml",)), "fontTable": ("fonts", ("fontTable+xml",)), "numbering": ("numbering", ("numbering+xml",)),
    "theme": ("theme", ("theme+xml",)), "glossaryDocument": ("glossaryDocument", ("document.glossary+xml",)),
}
GOC_KIEU: dict[str, tuple] = {"document": ("document.main+xml", "template.main+xml")}
for _goc, _duoi in LOAI_QUAN_HE.values():
    GOC_KIEU[_goc] = tuple(sorted(set(GOC_KIEU.get(_goc, ())) | set(_duoi)))


def _nguon_cua_rels(ten_rels: str) -> str:
    """`dir/_rels/name.rels` → `dir/name` (phần nguồn); `_rels/.rels` → "" (gói)."""
    if ten_rels == "_rels/.rels":
        return ""
    dau, _, duoi = ten_rels.rpartition("_rels/")
    return dau + duoi[: -len(".rels")]


def _ghi_de_kieu(ct_xml) -> dict:
    """ContentType override theo PartName (bỏ '/' đầu) từ [Content_Types].xml đã phân tích."""
    return {(el.get("PartName") or "").lstrip("/"): el.get("ContentType") or "" for el in ct_xml if _ten_cuc_bo(el.tag)[1] == "Override"}


def _kiem_sieu_du_lieu(ten: str, goc: str, qh_vao: dict, ghi_de: dict, ly_do: list, mong_goc: str | None = None) -> bool:
    """Gốc thực ↔ loại quan hệ trỏ vào ↔ ContentType override (↔ vai trò mong đợi) phải nhất quán. Mâu thuẫn → ghi lý do INCOMPLETE, trả True.
    Không dùng tên tệp/đường dẫn làm căn cứ."""
    chi_tiet = []
    if mong_goc is not None and goc != mong_goc:
        chi_tiet.append(f"goc {goc} khac vai tro {mong_goc}")
    loai_vao = sorted(l for l in qh_vao.get(ten, ()) if l in LOAI_QUAN_HE)
    for l in loai_vao:
        if LOAI_QUAN_HE[l][0] != goc:
            chi_tiet.append(f"quan he {l} khac goc {goc}")
    kieu = ghi_de.get(ten)
    if kieu:
        if goc in GOC_KIEU and not kieu.endswith(GOC_KIEU[goc]):
            chi_tiet.append(f"ContentType {kieu} khac goc {goc}")
        for l in loai_vao:
            if not kieu.endswith(LOAI_QUAN_HE[l][1]):
                chi_tiet.append(f"ContentType {kieu} khac quan he {l}")
    if chi_tiet:
        ly_do.append({"ma": "SIEU_DU_LIEU_MAU_THUAN", "phan": ten, "chi_tiet": chi_tiet})
        return True
    return False


def _van_ban_phan(goc_xml) -> str:
    """Ghép TOÀN BỘ văn bản hiển thị/trường của cả phần (w:t, w:delText, w:instrText, w:fldSimple@w:instr; transitional + strict)."""
    chu = []
    for el in goc_xml.iter():
        if _la_w(el.tag, "t") or _la_w(el.tag, "delText") or _la_w(el.tag, "instrText"):
            chu.append(el.text or "")
        if _la_w(el.tag, "fldSimple"):
            chu.append(el.get(f"{{{W}}}instr") or el.get(f"{{{W_STRICT}}}instr") or "")
    return "".join(chu)


def doc_mau_docx(raw: bytes, *, limits: dict | None = None) -> dict:
    gh = {**GIOI_HAN, **(limits or {})}
    z, infos = _kiem_zip(raw, gh)
    with z:
        ct = _doc_phan(z, infos, "[Content_Types].xml")
        ct_text = _giai_ma_xml(ct, "[Content_Types].xml")  # kiểm trên văn bản đã giải mã (UTF-16 không lách được)
        if "macroenabled" in ct_text.lower() or "vbaproject" in ct_text.lower():
            _loi("CRM_MAU_MACRO", "Loại nội dung cho thấy tệp có macro — không nhận.")
        _parse(ct, "[Content_Types].xml")
        goc_rels = _rels(z, infos, "_rels/.rels")
        chinh = None
        for typ, target in goc_rels.values():
            if typ.endswith("/officeDocument"):
                chinh = _chuan_dich("", target)
        if chinh is None:
            _loi("CRM_MAU_THIEU_PHAN", "Gói không có phần văn bản chính (officeDocument).")
        doc_raw = _doc_phan(z, infos, chinh)
        doc_xml = _parse(doc_raw, chinh)
        thu_muc = chinh.rsplit("/", 1)[0] if "/" in chinh else ""
        doc_rels = _rels(z, infos, (thu_muc + "/" if thu_muc else "") + "_rels/" + chinh.rsplit("/", 1)[-1] + ".rels")
        # quét mọi .rels trong gói: quan hệ ngoài ở bất kỳ phần nào đều fail-closed; đồng thời gom LOẠI quan hệ trỏ VÀO từng phần (căn cứ phân loại)
        qh_vao: dict[str, set] = {}
        for ten in infos:
            if ten.endswith(".rels"):
                nguon = _nguon_cua_rels(ten)
                for typ, target in _rels(z, infos, ten).values():
                    qh_vao.setdefault(_chuan_dich(nguon, target), set()).add(typ.rsplit("/", 1)[-1])
        ghi_de = _ghi_de_kieu(_parse(ct, "[Content_Types].xml"))
        ly_do, ket, dem_doan, ds_doan = [], [], [0], []
        _kiem_sieu_du_lieu(chinh, _ten_cuc_bo(doc_xml.tag)[1], qh_vao, ghi_de, ly_do, mong_goc="document")
        phan_quet = [{"ten": chinh, "loai": "THAN", "sha256": _sha(doc_raw)}]
        _quet_phan(doc_xml, chinh, "THAN", _sha(doc_raw), ly_do, dem_doan, ket, ds_doan, gh)
        # header/footer THỰC SỰ được tham chiếu từ sectPr của thân văn bản, theo thứ tự xuất hiện, mỗi phần một lần
        da = set()
        for el in doc_xml.iter():
            uri, t = _ten_cuc_bo(el.tag)
            if uri in (W, W_STRICT) and t in ("headerReference", "footerReference"):
                rid = _r_id(el, "id")
                if not rid or rid not in doc_rels:
                    _loi("CRM_MAU_QUAN_HE_HONG", "Tham chiếu header/footer không có quan hệ tương ứng.")
                typ, target = doc_rels[rid]
                ten = _chuan_dich(chinh, target)
                if ten in da:
                    continue
                da.add(ten)
                loai = "HEADER" if t == "headerReference" else "FOOTER"
                phan_raw = _doc_phan(z, infos, ten)
                phan_xml = _parse(phan_raw, ten)
                # phần được sectPr tham chiếu phải THỰC SỰ là header/footer (gốc + loại quan hệ + ContentType); mâu thuẫn → INCOMPLETE
                _kiem_sieu_du_lieu(ten, _ten_cuc_bo(phan_xml.tag)[1], qh_vao, ghi_de, ly_do, mong_goc="hdr" if loai == "HEADER" else "ftr")
                phan_quet.append({"ten": ten, "loai": loai, "sha256": _sha(phan_raw)})
                _quet_phan(phan_xml, ten, loai, _sha(phan_raw), ly_do, dem_doan, ket, ds_doan, gh)
        # P02 — mọi phần XML còn lại (và mọi phần có quan hệ loại văn bản/định dạng trỏ vào, bất kể đuôi) được PHÂN TÍCH XML (cùng bộ giải mã/chặn
        # DTD). Phân loại theo LOẠI QUAN HỆ trỏ vào + phần tử gốc thực + ContentType override — KHÔNG theo tên/đường dẫn: tên `styles.xml`,
        # `header1.xml`… không làm phần bị bỏ qua. Siêu dữ liệu mâu thuẫn → INCOMPLETE (SIEU_DU_LIEU_MAU_THUAN). Chỉ bỏ quét văn bản cho
        # header/footer KHÔNG được sectPr tham chiếu khi gốc là w:hdr/w:ftr và mọi căn cứ nhất quán (không hiển thị). Phần khác: ghép TOÀN BỘ
        # w:t/w:delText/w:instrText/thuộc tính w:instr của cả phần; có BẤT KỲ `{`/`}` → INCOMPLETE (KENH_CHUA_QUET), chặn kiểm/duyệt.
        quet = {p["ten"] for p in phan_quet}
        for ten in sorted(infos):
            if ten == "[Content_Types].xml" or ten.endswith(".rels") or ten in quet or ten.endswith("/"):
                continue
            loai_vao = qh_vao.get(ten, set())
            if not ten.lower().endswith(".xml") and not (loai_vao & set(LOAI_QUAN_HE)):
                continue  # media/nhị phân không được quan hệ văn bản trỏ vào
            goc_phan = _parse(_doc_phan(z, infos, ten), ten)
            goc = _ten_cuc_bo(goc_phan.tag)[1]
            mau_thuan = _kiem_sieu_du_lieu(ten, goc, qh_vao, ghi_de, ly_do)
            if not mau_thuan and goc in ("hdr", "ftr") and loai_vao <= {"header", "footer"}:
                continue  # header/footer nhất quán nhưng KHÔNG được sectPr tham chiếu: không hiển thị
            noi = _van_ban_phan(goc_phan)
            if "{" in noi or "}" in noi:
                ly_do.append({"ma": "KENH_CHUA_QUET", "phan": ten, "goc": goc, "quan_he": sorted(loai_vao)})
        members = [{"ten": i.filename, "sha256": _sha(_doc_phan(z, infos, i.filename)), "byte_length": i.file_size} for i in z.infolist()]
    dem = {}
    for o in ket:
        dem[o["ten"]] = dem.get(o["ten"], 0) + 1
    facts = {"bo_doc": PHIEN_BAN_BO_DOC, "raw_sha256": _sha(bytes(raw)), "byte_length": len(raw), "members": members, "phan_quet": phan_quet,
             "placeholders": [{"ten": k, "so_lan": dem[k]} for k in sorted(dem)], "occurrences": ket, "doan": ds_doan, "don_vi_khoang": DON_VI_KHOANG,
             "trang_thai": "INCOMPLETE" if ly_do else "DU", "ly_do_chua_du": ly_do}
    facts["facts_sha256"] = hashlib.sha256(json.dumps({k: v for k, v in facts.items()}, ensure_ascii=False, sort_keys=True,
                                                      separators=(",", ":")).encode("utf-8")).hexdigest()
    return facts
