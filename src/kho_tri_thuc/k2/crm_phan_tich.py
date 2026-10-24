"""Phân tích thuần (không I/O) cho CRM-01: căn cứ trích dẫn, giá trị typed theo profile, field chuẩn, lịch nghĩa vụ, so phụ lục.

Nguyên tắc: không có trích dẫn → "Không quy định", giá trị hiệu lực NULL (không 0, không mặc định). Trích dẫn có trong văn bản
KHÔNG tự chứng minh giá trị: giá trị phải xuất hiện trong chính trích dẫn; giá trị nguồn ghi "Suy ra" không phải căn cứ trực tiếp;
Điều/Khoản phải khớp vị trí khi có cấu trúc văn bản. Các trường hợp đó chỉ hiệu lực sau xác nhận thủ công có vết. Chỉ typed khi
parser cấu hình không mơ hồ; tham số optional rỗng không phải nghĩa vụ; % thiếu cơ sở → chờ; mốc chưa có ngày giữ ngày NULL;
so tổng chỉ khi cùng cơ sở/currency. Không suy tiền/VAT/ngày/căn cứ từ tên file, model, `kiem_tra`.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from ..ha_tang.primitives import DataError, money_minor, normalize_text

SCALE = {"VND": 0, "USD": 2}
HIEU_LUC_TRUC_TIEP = ("CO_CAN_CU",)
HIEU_LUC_NEU_KIEM_PHIEN_BAN = ("CHUA_DOI_CHIEU_NGUON", "CHUA_DOI_CHIEU_VI_TRI")
HIEU_LUC_NEU_XAC_NHAN_THAM_SO = ("SUY_RA", "GIA_TRI_KHONG_KHOP_TRICH_DAN")
DAU_HIEU_SUY_RA = ("SUY RA", "SUY LUAN", "UOC TINH", "NOI SUY")


def _chuan(text: str) -> str:
    return " ".join(str(text).split()).casefold()


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict) and "$so_thap_phan" in value:
        return value["$so_thap_phan"]
    text = str(value).strip()
    return text or None


def _cac_dieu(van_ban) -> list[tuple[str | None, str]]:
    """Văn bản đối chiếu: chuỗi phẳng hoặc danh sách mục {dieu_khoan, noi_dung} (cấu trúc do bộ đọc nguồn cung cấp)."""
    if van_ban is None:
        return []
    if isinstance(van_ban, str):
        return [(None, van_ban)]
    return [(_text(m.get("dieu_khoan")), str(m.get("noi_dung") or "")) for m in van_ban]


def _mau_token(gia_tri: str) -> re.Pattern:
    """Giá trị phải là MỘT token trọn vẹn trong trích dẫn: số không được là phần của số dài hơn (40.000.000 ⊄ 140.000.000),
    chữ không được là phần của từ khác. So sau khi chuẩn hóa khoảng trắng/chữ hoa."""
    g = re.escape(_chuan(gia_tri))
    if re.search(r"\d", gia_tri):
        return re.compile(rf"(?<![\w])(?<!\d[.,/]){g}(?!\d)(?![.,/]\d)")  # cho phép đơn vị dính liền (1.000.000đ, 30%)
    return re.compile(rf"(?<!\w){g}(?!\w)")


def co_token(gia_tri: str, trich: str) -> bool:
    return bool(_mau_token(gia_tri).search(_chuan(trich)))


def trang_thai_can_cu(p: dict, van_ban, che_do: str | None) -> str:
    """Căn cứ của một tham số #6. `kiem_tra` của nguồn không thay việc đối chiếu."""
    trich, gia_tri = _text(p.get("trich_dan")), _text(p.get("gia_tri"))
    if che_do == "chua_chay_AI" or not trich or gia_tri is None:
        return "KHONG_QUY_DINH"
    if any(d in normalize_text(_text(p.get("ghi_chu")) or "") for d in DAU_HIEU_SUY_RA):
        return "SUY_RA"
    if not co_token(gia_tri, trich):
        return "GIA_TRI_KHONG_KHOP_TRICH_DAN"
    muc = _cac_dieu(van_ban)
    if not muc:
        return "CHUA_DOI_CHIEU_NGUON"
    q, dieu = _chuan(trich), _text(p.get("dieu_khoan"))
    co_trong = [d for d, nd in muc if q in _chuan(nd)]
    if not co_trong:
        return "CAN_CU_KHONG_KHOP"
    if not dieu:
        return "CO_CAN_CU"
    if all(d is None for d, _ in muc):  # văn bản phẳng: có câu trích nhưng chưa đối chiếu được Điều/Khoản
        return "CHUA_DOI_CHIEU_VI_TRI"
    return "CO_CAN_CU" if any(d is not None and _chuan(d) == _chuan(dieu) for d in co_trong) else "VI_TRI_KHONG_KHOP"


def _tien_te(don_vi: str | None, profile: dict) -> str | None:
    if not don_vi:
        return None
    alias = {_chuan(k): v for k, v in profile.get("don_vi_tien_alias", {}).items()}
    iso = alias.get(_chuan(don_vi), don_vi if don_vi in profile["tien_te_hop_le"] else None)
    return iso if iso in profile["tien_te_hop_le"] else None


def _parse(kieu: str, text: str, don_vi: str | None, spec: dict, profile: dict):
    """Giá trị typed hoặc DataError (mơ hồ/sai định dạng)."""
    nghin, thap_phan = profile["dinh_dang_so"]["nghin"], profile["dinh_dang_so"]["thap_phan"]
    if kieu == "text":
        return {"text": text}
    if kieu == "ngay":
        m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", text)
        if not m:
            raise DataError("PARSE_NGAY", "Ngày phải dạng dd/mm/yyyy theo profile.")
        try:
            return {"ngay": date(int(m[3]), int(m[2]), int(m[1])).isoformat()}
        except ValueError as exc:
            raise DataError("PARSE_NGAY", "Ngày không tồn tại.") from exc
    if kieu == "tien":
        iso = _tien_te(don_vi, profile)
        if iso is None:
            raise DataError("PARSE_TIEN_TE", f"Đơn vị tiền `{don_vi}` không có trong profile (ISO hoặc alias đã cấu hình).")
        return {"minor": money_minor(text, SCALE[iso], decimal_sep=thap_phan, group_sep=nghin), "tien_te": iso, "don_vi_nguon": don_vi,
                "alias_profile": f"{profile['ma']}@v{profile['phien_ban']}" if don_vi != iso else None}
    if kieu == "so":
        if spec.get("don_vi") and don_vi != spec["don_vi"]:
            raise DataError("PARSE_DON_VI", f"Đơn vị `{don_vi}` khác profile `{spec['don_vi']}`.")
        if not re.fullmatch(rf"\d{{1,3}}(?:{re.escape(nghin)}\d{{3}})*(?:{re.escape(thap_phan)}\d+)?|\d+(?:{re.escape(thap_phan)}\d+)?", text):
            raise DataError("PARSE_SO", "Số không đúng định dạng profile.")
        try:
            return {"so": str(Decimal(text.replace(nghin, "").replace(thap_phan, "."))), "don_vi": don_vi}
        except InvalidOperation as exc:
            raise DataError("PARSE_SO", "Số không hợp lệ.") from exc
    if kieu == "ty_le":
        m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(%?)", text)
        if not m or not (m[2] == "%" or (don_vi or "").strip() == "%") or (m[2] == "%" and don_vi not in (None, "", "%")):
            raise DataError("PARSE_TY_LE", "Tỷ lệ phải là n% (giá trị có % hoặc đơn vị %).")
        return {"ty_le": str(Decimal(m[1].replace(",", ".")))}
    if kieu == "moc":
        if text not in profile.get("moc_hop_le", {}):
            raise DataError("PARSE_MOC", "Mốc sự kiện không có trong profile.")
        return {"moc": profile["moc_hop_le"][text]}
    raise DataError("PARSE_KIEU", "Kiểu tham số chưa hỗ trợ.")


def _kieu_ma(profile: dict) -> dict:
    """mã nguồn → (field, kiểu, spec) theo profile (field chuẩn + tham số lịch)."""
    out = {}
    for spec in profile["truong"]:
        for ma in spec["ma_nguon"]:
            out[ma] = (spec["truong"], spec["kieu"], spec)
    for ob in profile["lich"]:
        for role, kieu in (("so_tien", "tien"), ("han", "ngay"), ("moc", "moc"), ("ty_le", "ty_le")):
            if ob.get(role):
                out[ob[role]] = (f"lich.{ob['khoa']}.{role}", kieu, ob)
    return out


ISO_BIET = frozenset({"VND", "USD", "EUR", "JPY", "CNY", "KRW", "SGD", "GBP", "AUD", "THB", "HKD", "TWD", "CHF", "CAD"})
CAN_CU_CO_TRICH = ("CO_CAN_CU", "CHUA_DOI_CHIEU_NGUON", "CHUA_DOI_CHIEU_VI_TRI")


def tien_te_trong_trich(gia_tri: str, trich: str, profile: dict) -> set[str]:
    """Loại tiền ghi NGAY SAU token số trong câu trích (alias profile hoặc mã ISO). Rỗng = trích dẫn không nêu loại tiền."""
    alias = {_chuan(k): v for k, v in profile.get("don_vi_tien_alias", {}).items()}
    out = set()
    for m in _mau_token(gia_tri).finditer(_chuan(trich)):
        word = re.match(r"\s*([^\W\d_]+)", _chuan(trich)[m.end():])
        if not word:
            continue
        w = word.group(1)
        if w in alias:
            out.add(alias[w])
        elif w.upper() in ISO_BIET:
            out.add(w.upper())
    return out


def _kiem_tien_te(row: dict, profile: dict) -> None:
    """Giá trị tiền có kiểu = số + loại tiền: cả hai phải có trong trích dẫn. Khác loại tiền → chặn cứng (không quy đổi/đổi nhãn);
    trích dẫn không nêu loại tiền → chưa chứng minh, giữ chờ xác nhận thủ công."""
    typed = row["gia_tri_typed"]
    if row["kieu"] != "tien" or not isinstance(typed, dict) or row["trang_thai_can_cu"] not in CAN_CU_CO_TRICH:
        return
    found = tien_te_trong_trich(row["gia_tri_tho"], row["trich_dan"], profile)
    if found and found != {typed["tien_te"]}:
        row["trang_thai_can_cu"] = "GIA_TRI_KHONG_KHOP_TRICH_DAN"
        row["loi"].append("TIEN_TE_KHONG_KHOP_TRICH_DAN")
    elif not found:
        row["trang_thai_can_cu"] = "GIA_TRI_KHONG_KHOP_TRICH_DAN"


def tham_so_typed(ket_qua: dict, profile: dict, van_ban) -> list[dict]:
    """Mỗi tham số #6 → bản ghi giữ nguyên nội dung nguồn + căn cứ + typed (parse khi có giá trị; hiệu lực do căn cứ quyết)."""
    mapping, che_do, out = _kieu_ma(profile), ket_qua.get("che_do"), []
    for p in ket_qua["tham_so"]:
        ma = p["ma"].strip()
        status = trang_thai_can_cu(p, van_ban, che_do)
        truong, kieu, spec = mapping.get(ma, (None, None, None))
        row = {"ma": ma, "nhom": _text(p.get("nhom")), "tham_so": _text(p.get("tham_so")), "gia_tri_tho": _text(p.get("gia_tri")),
               "don_vi": _text(p.get("don_vi")), "dieu_khoan": _text(p.get("dieu_khoan")), "trich_dan": _text(p.get("trich_dan")),
               "vi_tri": _text(p.get("vi_tri_do_duoc")), "kiem_tra_nguon": _text(p.get("kiem_tra")), "ghi_chu_nguon": _text(p.get("ghi_chu")),
               "trang_thai_can_cu": status, "truong": truong, "kieu": kieu, "gia_tri_typed": None, "loi": [], "xac_nhan_thu_cong": None}
        if kieu and row["gia_tri_tho"] is not None and che_do != "chua_chay_AI":
            try:
                row["gia_tri_typed"] = _parse(kieu, row["gia_tri_tho"], row["don_vi"], spec, profile)
            except DataError as exc:
                row["loi"].append(exc.code)
            _kiem_tien_te(row, profile)
        out.append(row)
    return out


def hieu_luc(row: dict, da_xac_nhan_thu_cong: bool):
    status = row["trang_thai_can_cu"]
    ok = (status in HIEU_LUC_TRUC_TIEP or (status in HIEU_LUC_NEU_KIEM_PHIEN_BAN and da_xac_nhan_thu_cong)
          or (status in HIEU_LUC_NEU_XAC_NHAN_THAM_SO and row.get("xac_nhan_thu_cong")))
    return row["gia_tri_typed"] if ok and not row["loi"] else None


def tong_hop(params: list[dict], profile: dict, *, loai_ban: str = "GOC", da_xac_nhan_thu_cong: bool = False) -> dict:
    """Field chuẩn + lịch + điều kiện chặn. Rerun được trên bản ghi đã lưu (params typed)."""
    chan: list[dict] = []
    add = lambda code, msg: chan.append({"ma": code, "thong_diep": msg})
    by_ma: dict[str, list[dict]] = {}
    for row in params:
        by_ma.setdefault(row["ma"], []).append(row)
    for ma, rows in by_ma.items():
        if len({(r["gia_tri_tho"], r["don_vi"]) for r in rows}) > 1:
            add("THAM_SO_TRUNG_MA", f"Tham số {ma} xuất hiện nhiều lần với giá trị khác nhau — không chọn dòng cuối.")
    for row in params:
        if row["gia_tri_tho"] is None or not row["truong"]:
            continue  # tham số optional rỗng / ngoài profile: không phải căn cứ, không chặn
        status = row["trang_thai_can_cu"]
        if status == "CAN_CU_KHONG_KHOP":
            add("CAN_CU_KHONG_KHOP", f"Trích dẫn của {row['ma']} không thấy trong văn bản đối chiếu.")
        elif status == "VI_TRI_KHONG_KHOP":
            add("VI_TRI_KHONG_KHOP", f"Trích dẫn của {row['ma']} không nằm ở {row['dieu_khoan']} như nguồn ghi.")
        elif status in HIEU_LUC_NEU_KIEM_PHIEN_BAN and not da_xac_nhan_thu_cong:
            add(status, f"{row['ma']} có trích dẫn nhưng chưa đối chiếu được văn bản/vị trí — kế toán phải xác nhận căn cứ.")
        elif status == "SUY_RA" and not row.get("xac_nhan_thu_cong"):
            add("SUY_RA", f"{row['ma']} là giá trị suy ra, không phải trích trực tiếp — cần xác nhận thủ công có lý do.")
        elif status == "GIA_TRI_KHONG_KHOP_TRICH_DAN" and not row.get("xac_nhan_thu_cong"):
            add("GIA_TRI_KHONG_KHOP_TRICH_DAN", f"Giá trị `{row['gia_tri_tho']}`{' ' + row['don_vi'] if row.get('don_vi') else ''} của {row['ma']} "
                                                "không có đủ (token số/loại tiền) trong câu trích dẫn.")
        for code in row["loi"]:
            add(code, f"{row['ma']}: câu trích dẫn ghi loại tiền khác `{row['don_vi']}` — không quy đổi/đổi nhãn." if code == "TIEN_TE_KHONG_KHOP_TRICH_DAN"
                else f"{row['ma']}: không đọc chắc giá trị `{row['gia_tri_tho']}` theo profile.")

    def value(ma: str):
        vals = [v for v in (hieu_luc(r, da_xac_nhan_thu_cong) for r in by_ma.get(ma, [])) if v is not None]
        return vals[0] if vals and all(v == vals[0] for v in vals) else None

    def co_gia_tri(ma: str) -> bool:
        return bool(ma) and any(r["gia_tri_tho"] is not None for r in by_ma.get(ma, []))

    fields: dict = {}
    for spec in profile["truong"]:
        if spec.get("chi_phu_luc") and loai_ban != "PHU_LUC":
            continue
        found = [v for v in (value(ma) for ma in spec["ma_nguon"]) if v is not None]
        if len({repr(v) for v in found}) > 1:
            add("THAM_SO_MAU_THUAN", f"Field {spec['truong']} có giá trị mâu thuẫn giữa các tham số.")
            continue
        fields[spec["truong"]] = found[0] if found else None
        if spec.get("bat_buoc") and not found:
            add("THIEU_CAN_CU", f"Field bắt buộc {spec['truong']} chưa có giá trị có căn cứ (Không quy định/chưa có căn cứ).")
    if loai_ban == "PHU_LUC" and not fields.get("ngay_hieu_luc_phu_luc"):
        add("PHU_LUC_THIEU_NGAY_HIEU_LUC", "Phụ lục chưa có ngày hiệu lực có căn cứ.")

    lich, co_so_set = [], set()
    for ob in profile["lich"]:
        roles = {r: ob.get(r) for r in ("so_tien", "han", "moc", "ty_le")}
        if not any(co_gia_tri(ma) for ma in roles.values()):
            continue  # dòng nghĩa vụ mẫu rỗng của catalog nguồn: không phải nghĩa vụ thực
        if co_gia_tri(roles["ty_le"]):
            add("LICH_TY_LE_THIEU_CO_SO", f"Đợt {ob['khoa']} theo % chưa có cơ sở tính/VAT/rounding — lưu tham số, không sinh lịch.")
            continue
        tien = value(roles["so_tien"]) if roles["so_tien"] else None
        han = value(roles["han"]) if roles["han"] else None
        moc = value(roles["moc"]) if roles["moc"] else None
        if tien is None:
            add("LICH_THIEU_SO_TIEN", f"Đợt {ob['khoa']} chưa có số tiền có căn cứ.")
            continue
        if han is None and moc is None:
            add("LICH_THIEU_HAN_MOC", f"Đợt {ob['khoa']} chưa có hạn hoặc mốc có căn cứ.")
            continue
        co_so_set.add((ob.get("co_so"), tien["tien_te"]))
        lich.append({"khoa": ob["khoa"], "loai": ob["loai"], "dot": ob["dot"], "so_tien_minor": tien["minor"], "tien_te": tien["tien_te"],
                     "han": han["ngay"] if han else None, "moc": moc["moc"] if moc else None, "co_so": ob.get("co_so"),
                     "nguon_tham_so": [roles[r] for r in ("so_tien", "han", "moc") if co_gia_tri(roles[r])]})
    if not lich and not any(c["ma"].startswith("LICH_") for c in chan):
        add("LICH_TRONG", "Không có đợt nghĩa vụ tường minh nào để sinh lịch.")
    kiem = profile.get("kiem_tong")
    so_tong = {"da_so": False}
    if kiem and lich and fields.get(kiem["truong"]):
        total = fields[kiem["truong"]]
        if co_so_set == {(kiem["co_so"], total["tien_te"])}:
            so_tong = {"da_so": True, "tong_lich": sum(r["so_tien_minor"] for r in lich), "tong_hop_dong": total["minor"]}
            if so_tong["tong_lich"] != total["minor"]:
                add("LICH_LECH_TONG", "Tổng lịch khác tổng hợp đồng trên cùng cơ sở tiền/currency.")
        else:
            so_tong = {"da_so": False, "ly_do": "khác cơ sở tiền hoặc currency — không so tổng"}
    return {"fields": fields, "lich": lich, "chan": chan, "so_tong": so_tong}


def chu_ky(r: dict) -> tuple:
    """Định danh nội dung một nghĩa vụ: số tiền, currency, hạn, mốc, loại, đợt và cơ sở tiền."""
    return (r["so_tien_minor"], r["tien_te"], r["han"], r["moc"], r.get("loai"), r.get("dot"), r.get("co_so"))


def so_sanh_phu_luc(cu: list[dict], moi: list[dict]) -> tuple[list[dict], list[dict]]:
    """cu: [{khoa, id, so_tien_minor, tien_te, han, moc, loai, dot, co_so, da_lien_ket_minor}]; moi: lịch phiên bản mới.
    Trả (kế hoạch, chặn). Đợt đã có tiền nối mà bị đổi bất kỳ thành phần nào (kể cả cơ sở VAT, loại cọc/đợt) hoặc bị bỏ → chặn."""
    old = {r["khoa"]: r for r in cu}
    new = {r["khoa"]: r for r in moi}
    plan, chan = [], []
    for khoa in sorted(set(old) | set(new)):
        o, n = old.get(khoa), new.get(khoa)
        if o and not n:
            if o["da_lien_ket_minor"]:
                chan.append({"ma": "PHU_LUC_BO_DOT_DA_THU", "thong_diep": f"Phụ lục bỏ đợt {khoa} đã có tiền nối — chờ đối chiếu."})
            else:
                plan.append({"khoa": khoa, "hanh_dong": "BO", "thay_cho": o["id"]})
        elif n and not o:
            plan.append({"khoa": khoa, "hanh_dong": "THEM", "dong": n})
        elif chu_ky(o) == chu_ky(n):
            plan.append({"khoa": khoa, "hanh_dong": "GIU", "dong": n, "thay_cho": o["id"]})
        elif o["da_lien_ket_minor"]:
            chan.append({"ma": "PHU_LUC_DOI_DOT_DA_THU", "thong_diep": f"Phụ lục đổi đợt {khoa} đã thu (một phần/toàn bộ) — chưa rõ cách chuyển nghĩa vụ, chờ xác nhận."})
        else:
            plan.append({"khoa": khoa, "hanh_dong": "DOI", "dong": n, "thay_cho": o["id"]})
    return plan, chan
