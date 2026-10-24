# -*- coding: utf-8 -*-
"""
nghiep_vu.py — Các chức năng nghiệp vụ cho giao diện "Bàn kiểm soát" (ngoài phần trích tham số):
  - Import BOQ gốc theo hợp đồng: đọc sheet, ánh xạ 6 cột, xem trước, kiểm tra Σ thành tiền × (1+VAT) = giá trị HĐ, ghi.
  - Kiểm tra đợt thanh toán 2 lớp (Lớp 1 toàn vẹn Excel + Lớp 2 đối chiếu HĐ/PL/BOQ hiệu lực tại ngày nghiệm thu),
    chuẩn hoá thành danh sách phát hiện có vị trí ô, bằng chứng, ảnh hưởng tiền và cây truy vết số đề nghị.
  - Chỉ toàn vẹn file (Lớp 1) — chế độ của màn Kiểm tra đợt khi hợp đồng chưa có trong CSDL.
  - Nguồn cho màn Tổng quan: việc gần đây, cảnh báo.
Kết quả kiểm tra lưu thành JSON trong ket_qua_AI\\kiem_tra_dot\\ và ket_qua_AI\\toan_ven\\ để mở lại sau.
"""
import datetime
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

from trich_xuat import cau_hinh as ch

TEN_K = {"K1": "Tổng quan workbook: sheet ẩn, file ngoài, ô lỗi", "K2": "Công thức lệch mẫu theo cột",
         "K3": "Liên kết dòng giữa các sheet", "K4": "Sheet ẩn", "K5": "Số lưu dạng chữ",
         "K6": "Tham số gõ cứng trong công thức", "K7": "Cây truy vết số đề nghị", "K8": "Nguồn khối lượng từng hạng mục"}
MUC_L1 = {"Cao": "Cao", "Trung bình": "Trung bình", "Kiểm soát": "Thấp"}


def _json(o):
    return json.loads(json.dumps(o, ensure_ascii=False, default=str))


def _bay_gio():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _cs():
    import csdl_hop_dong as cs
    return cs, cs.mo_csdl(str(ch.file_csdl()))


# ================================================================== IMPORT BOQ
TRUONG_BOQ = ["stt", "ma_rieng", "ten", "dvt", "kl", "don_gia", "thanh_tien"]
TEN_TRUONG = {"stt": "STT", "ma_rieng": "Mã hạng mục (phòng Dự án đặt)", "ten": "Tên công việc", "dvt": "Đơn vị tính",
              "kl": "Khối lượng", "don_gia": "Đơn giá", "thanh_tien": "Thành tiền"}
MAU_TIEU_DE = {  # mỗi trường: các mẫu theo thứ tự ưu tiên (mẫu đầu khớp chính xác hơn)
    "stt": [r"^(stt|tt|so tt)\.?$"],
    "ma_rieng": [r"^ma (hang muc|hm|cong viec|cv|boq)\b|^ma hm$"],   # KHÔNG nhận 'Mã hiệu' (mã định mức, lặp giữa các bể)
    "ten": [r"^ten cong (viec|tac)", r"^noi dung cong viec", r"^ten (hang muc|vat tu|thiet bi)", r"noi dung", r"cong viec",
            r"hang muc"],
    "dvt": [r"^(don vi|dvt|d\.? ?vi)"],
    "kl": [r"^khoi luong( hop dong| hd)?$", r"khoi luong|^kl\b"],
    "don_gia": [r"^don gia"],
    "thanh_tien": [r"^thanh tien", r"thanh tien|thanh gia", r"^gia tri"]}


def _chu(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.strftime("%d/%m/%Y")
    return str(v).strip()


def _col(i):
    from openpyxl.utils import get_column_letter
    return get_column_letter(i)


def boq_doc_file(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheets = []
    for ws in wb.worksheets:
        sheets.append({"ten": ws.title, "so_dong": ws.max_row or 0, "so_cot": ws.max_column or 0,
                       "an": ws.sheet_state != "visible"})
    wb.close()
    # sheet gợi ý: sheet hiện có nhiều dòng nhất mà tìm được tiêu đề
    goi_y = None
    for s in sorted(sheets, key=lambda x: (x["an"], -x["so_dong"])):
        xem = boq_xem_sheet(path, s["ten"])
        if xem["hang_tieu_de"]:
            goi_y = xem
            break
    return {"sheets": sheets, "goi_y": goi_y or (boq_xem_sheet(path, sheets[0]["ten"]) if sheets else None)}


def boq_xem_sheet(path, sheet, max_dong=40):
    """Xem trước sheet: các dòng đầu (chữ), dòng tiêu đề đoán được và ánh xạ cột gợi ý."""
    import openpyxl
    from master_hd import bo_dau, bo_dau_tieu_de
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if sheet not in wb.sheetnames:
        raise ValueError(f"Không có sheet {sheet}")
    ws = wb[sheet]
    rows = []
    for i, r in enumerate(ws.iter_rows(min_row=1, max_row=max_dong, max_col=min(ws.max_column or 1, 26),
                                       values_only=True), 1):
        rows.append([_chu(v) for v in r])
    wb.close()
    hang, cot = None, {}
    for i, r in enumerate(rows[:30], 1):
        tieu = [(j, bo_dau_tieu_de(v).strip()) for j, v in enumerate(r, 1) if v and len(str(v)) <= 60]  # chịu lỗi OCR
        m, dung = {}, set()
        for k, pats in MAU_TIEU_DE.items():
            for pat in pats:
                j = next((j for j, t in tieu if j not in dung and re.search(pat, t)), None)
                if j:
                    m[k] = j
                    dung.add(j)
                    break
        if len({"ten", "dvt", "don_gia"} & set(m)) == 3:
            hang, cot = i, m
            break
    so_cot = max((len(r) for r in rows), default=0)
    return {"sheet": sheet, "dong": rows, "so_cot": so_cot, "hang_tieu_de": hang,
            "cot": {k: _col(v) for k, v in cot.items()}, "truong": [{"ma": k, "ten": TEN_TRUONG[k]} for k in TRUONG_BOQ]}


def _so(v):
    """Số trong ô BOQ: số Excel, hoặc chữ kiểu Việt Nam '1.234.567' / '1.250,56' (bảng lấy từ Word / OCR)."""
    from master_hd import num
    from trich_xuat.ocr_abbyy import so_vn
    x = so_vn(v) if isinstance(v, str) else None
    if x is None:
        x = num(v)
    return x if isinstance(x, (int, float)) else None


def boq_doc_dong(path, sheet, hang_tieu_de, cot):
    """Đọc các dòng BOQ theo ánh xạ cột {truong: 'A'…}. Dòng không có ĐVT = tiêu đề nhóm. Dừng ở dòng Cộng/Tổng."""
    import openpyxl
    from openpyxl.utils import column_index_from_string
    from master_hd import bo_dau, nfc
    thieu = [TEN_TRUONG[k] for k in ("ten", "dvt", "kl", "don_gia") if not cot.get(k)]
    if thieu:
        raise ValueError("Chưa chọn cột: " + ", ".join(thieu))
    dung = [v for v in cot.values() if v]
    if len(dung) != len(set(dung)):
        raise ValueError("Một cột đang được dùng cho nhiều trường — mỗi trường cần một cột riêng")
    idx = {k: column_index_from_string(v) for k, v in cot.items() if v}
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[sheet]
    items, loi, nhom = [], [], []
    for r, row in enumerate(ws.iter_rows(min_row=int(hang_tieu_de) + 1, values_only=True), int(hang_tieu_de) + 1):
        g = {k: (row[i - 1] if i - 1 < len(row) else None) for k, i in idx.items()}
        ten = nfc(_chu(g.get("ten")))
        dvt = nfc(_chu(g.get("dvt")))
        if not ten and not dvt:
            continue
        # so khớp CÓ DẤU: "CỐNG TRÒN BTCT" (tiêu đề nhóm) không được nhầm với "CỘNG" (dòng tổng)
        low = ten.lower()
        if not dvt and re.match(r"^(tổng cộng|tổng giá trị|giá trị sau thuế|thuế|vat\b|cộng\s*[(:-]?\s*(chưa|trước|sau|đã)"
                                r"\s*(có\s*)?(vat|thuế))", low):
            break                                        # dòng tổng toàn bảng → hết BOQ
        if not dvt and re.match(r"^cộng\b", low):
            continue                                     # "Cộng hạng mục A"… (tổng phụ giữa bảng) → bỏ qua, đọc tiếp
        if re.fullmatch(r"[\[\]\-\d\s()]+", ten or "-"):
            continue                                     # dòng đánh số cột (1) (2) (3)…
        if not dvt:
            stt = _chu(g.get("stt"))
            nhom = [ten] if (re.match(r"^[A-Z]\.?$", stt) or not nhom) else nhom[:1] + [ten]
            continue
        kl, dg, tt = _so(g.get("kl")), _so(g.get("don_gia")), _so(g.get("thanh_tien")) if "thanh_tien" in g else None
        # ô khối lượng / đơn giá để TRỐNG và thành tiền trống hoặc 0 (hạng mục chưa có khối lượng) → coi là 0
        if kl is None and not _chu(g.get("kl")) and tt in (None, 0):
            kl = 0.0
        if dg is None and not _chu(g.get("don_gia")) and tt in (None, 0):
            dg = 0.0
        it = {"dong": r, "stt": _chu(g.get("stt")), "nhom": " / ".join(nhom), "ten": ten, "dvt": dvt, "kl": kl,
              "don_gia": dg, "thanh_tien": tt, "ma_rieng": nfc(_chu(g.get("ma_rieng")))}
        if kl is None or dg is None:
            loi.append({"dong": r, "noi_dung": f"{ten[:60]}: khối lượng hoặc đơn giá không phải số — kiểm tra ánh xạ cột"})
        elif tt is not None and abs(kl * dg - tt) > max(1.0, abs(tt) * 1e-6):
            loi.append({"dong": r, "noi_dung": f"{ten[:60]}: KL × ĐG = {kl * dg:,.0f} khác thành tiền {tt:,.0f}"})
        items.append(it)
    wb.close()
    trung = Counter(re.sub(r"\s+", "", bo_dau(it["ma_rieng"])).upper() for it in items if it["ma_rieng"])
    for it in items:
        if it["ma_rieng"] and trung[re.sub(r"\s+", "", bo_dau(it["ma_rieng"])).upper()] > 1:
            loi.append({"dong": it["dong"], "noi_dung": f"Mã hạng mục '{it['ma_rieng']}' bị trùng — mỗi hạng mục một mã riêng"})
    return items, loi


def boq_kiem_tra(path, sheet, hang_tieu_de, cot, ref):
    items, loi = boq_doc_dong(path, sheet, hang_tieu_de, cot)
    cs, con = _cs()
    try:
        hd = cs.tim_hd(con, ref)
        ma = hd["ma_hd"]
        vat = hd["vat"] or 0
        tong = sum(round((it["kl"] or 0) * (it["don_gia"] or 0)) for it in items if it["kl"] is not None
                   and it["don_gia"] is not None)
        sau_vat = tong * (1 + vat)
        gt = cs.gt_sau_vat_goc(hd)
        lech = sau_vat - gt
        dat = bool(gt) and abs(lech) <= cs.tol_tien(gt)
        co_boq = con.execute("SELECT COUNT(*) FROM boq_dong WHERE ma_hd = ? AND pl_id IS NULL", (ma,)).fetchone()[0]
        co_pl = con.execute("SELECT COUNT(*) FROM phu_luc WHERE ma_hd = ? AND trang_thai <> 'Đã hủy'", (ma,)).fetchone()[0]
        co_dot = con.execute("SELECT COUNT(*) FROM kl_thanh_toan WHERE ma_hd = ?", (ma,)).fetchone()[0]
        chan = []
        if not items:
            chan.append("Không đọc được dòng hạng mục nào — kiểm tra dòng tiêu đề và ánh xạ cột")
        if loi:
            chan.append(f"{len(loi)} dòng sai kiểu dữ liệu hoặc KL × ĐG ≠ thành tiền")
        if co_pl:
            chan.append(f"Hợp đồng đã có {co_pl} phụ lục — BOQ gốc không thay được (thay đổi BOQ phải qua phiếu phụ lục)")
        if co_boq and co_dot:
            chan.append("Hợp đồng đã có BOQ gốc và đã có đợt thanh toán nạp theo BOQ đó — không thay được")
        return _json({"ma_hd": ma, "so_hd": hd["so_hd"], "so_dong": len(items), "xem_truoc": items[:200], "loi": loi,
                      "tong_truoc_vat": tong, "vat": vat, "tong_sau_vat": sau_vat, "gt_hd": gt, "gom_vat": hd["gom_vat"],
                      "lech": lech, "ket_luan": "ĐẠT" if dat else "LỆCH", "boq_hien_co": co_boq, "chan": chan,
                      "can_ly_do": bool(co_boq)})
    finally:
        con.close()


def boq_ghi(path, sheet, hang_tieu_de, cot, ref, ly_do="", chap_nhan_lech=False):
    kt = boq_kiem_tra(path, sheet, hang_tieu_de, cot, ref)
    if kt["chan"]:
        raise ValueError("Không ghi được: " + "; ".join(kt["chan"]))
    if kt["ket_luan"] != "ĐẠT" and not chap_nhan_lech:
        raise ValueError(f"Tổng BOQ sau VAT lệch {kt['lech']:,.0f} đồng so với giá trị HĐ — kiểm tra trước khi ghi")
    if kt["boq_hien_co"] and not (ly_do or "").strip():
        raise ValueError(f"Hợp đồng đã có {kt['boq_hien_co']} dòng BOQ gốc — phải nhập lý do để thay")
    items, _ = boq_doc_dong(path, sheet, hang_tieu_de, cot)
    from master_hd import khoa
    cs, con = _cs()
    try:
        ma = kt["ma_hd"]
        if kt["boq_hien_co"]:
            with cs.che_do_sua(con, ly_do, ma):
                con.execute("DELETE FROM khop_hang_muc WHERE ma_hd = ?", (ma,))
                con.execute("DELETE FROM boq_dong WHERE ma_hd = ? AND pl_id IS NULL", (ma,))
        ten_file = Path(path).name
        dang = []
        for it in items:
            ma_hm = cs.ma_hm_moi(con, ma, dang)
            dang.append(ma_hm)
            x = dict(nhom=it["nhom"], ten=it["ten"], dvt=it["dvt"])
            con.execute("INSERT INTO boq_dong(ma_hd, pl_id, thao_tac, ma_hm, stt, nhom, ten, dvt, kl, don_gia, "
                        "thanh_tien_ghi, khoa, vi_tri_nguon, ghi_chu, ma_rieng) VALUES (?,NULL,'GOC',?,?,?,?,?,?,?,?,?,?,?,?)",
                        (ma, ma_hm, it["stt"] or None, it["nhom"] or None, it["ten"], it["dvt"], it["kl"], it["don_gia"],
                         it["thanh_tien"], khoa(x), f"{ten_file} {sheet}!dòng {it['dong']}", None, it.get("ma_rieng") or None))
        cs.ghi_nhat_ky(con, "Nhập BOQ gốc", ma, f"{ten_file} / {sheet}: {len(items)} hạng mục; Σ sau VAT "
                                                 f"{kt['tong_sau_vat']:,.0f}; {kt['ket_luan']}" + (f"; lý do: {ly_do}" if ly_do else ""))
        canh = cs.kiem_tra_boq_goc(con, ma)
        con.commit()
        return _json({"ok": True, "ma_hd": ma, "so_dong": len(items), "canh_bao": canh, "ket_luan": kt["ket_luan"]})
    finally:
        con.close()


# ================================================================== KIỂM TRA ĐỢT / TOÀN VẸN
def _tach_o(o):
    """'Sheet 1'!$A$5 → ('Sheet 1', 'A5'); 'Sheet!E' → ('Sheet', 'E'); không có '!' → ('', o)."""
    t = str(o or "").strip()
    if "!" not in t or t.startswith("["):
        return "", ("" if t == "-" else t)
    sh, c = t.rsplit("!", 1)
    return sh.strip("'"), c.replace("$", "")


def _lop1(kt, ten_file):
    """Phát hiện Lớp 1 (toan_ven.KiemTra) → danh sách chuẩn hoá + bảng K1–K8."""
    from openpyxl.utils import column_index_from_string
    out = []
    dem = Counter()
    for x in kt.ph:
        dem[x["kt"]] += 1
        sheet, cell = _tach_o(x["o"])
        cong_thuc = gia_tri = ""
        if sheet and re.fullmatch(r"[A-Z]+\d+", cell):
            try:
                m = re.match(r"([A-Z]+)(\d+)", cell)
                c, r = column_index_from_string(m.group(1)), int(m.group(2))
                f = kt.sd.f(sheet, c, r)
                cong_thuc = str(f) if f is not None else ""
                gia_tri = kt.sd.v(sheet, c, r)
            except Exception:  # noqa: BLE001
                pass
        mo_ta = x["mo_ta"]
        phan = re.split(r"(?<=[^\d])[.:;](?=\s)", mo_ta, maxsplit=1)
        tieu_de = phan[0][:140]
        if len(tieu_de) < 16 and len(phan) > 1:          # "1 ô: Trỏ tới dòng…" → lấy phần sau làm tiêu đề
            tieu_de = f"{phan[1].strip()[:120]} ({tieu_de})"
        out.append({"id": f"{x['kt']}-{dem[x['kt']]:02d}", "code": x["kt"], "layer": 1,
                    "level": MUC_L1.get(x["muc"], x["muc"]), "title": tieu_de, "detail": mo_ta if mo_ta != tieu_de else "",
                    "amount": None, "sheet": sheet, "cell": cell if sheet else (x["o"] if x["o"] != "-" else ""),
                    "item": "", "actual": cong_thuc or _chu(gia_tri), "expected": TEN_K.get(x["kt"], ""),
                    "source": ten_file, "formula": cong_thuc, "value": _chu(gia_tri), "so_o": x.get("so_o"),
                    "reference": x.get("tai_lieu") or "", "conclusion": x.get("tai_lieu") or mo_ta})
    bang_k = []
    for k, ten in TEN_K.items():
        ds = [f for f in out if f["code"] == k]
        cao = [f for f in ds if f["level"] in ("Cao", "Trung bình")]
        bang_k.append({"code": k, "ten": ten, "ket_qua": "Cần xem" if cao else "Đạt", "so": len(ds),
                       "chi_tiet": ds[0]["title"] if ds else "Không có phát hiện", "finding": ds[0]["id"] if ds else None})
    cay = [{"cap": r[0], "ten": str(r[1]).strip(), "o": r[2], "cong_thuc": r[3], "gia_tri": r[4], "loai": r[5],
            "nhom": r[6], "tai_lieu": r[7], "ghi": r[8]} for r in kt.kq.get("cay", [])]
    return out, bang_k, cay, kt.kq.get("dich")


def _lop2(k):
    """Kết quả csdl_hop_dong.tinh_doi_chieu_dot → phát hiện Lớp 2."""
    from master_hd import nfc
    out = []
    sheet = k["bang"]["sheet"]
    cols = k["bang"]["cols"]
    ngay = k["ngay"]
    for i, (t, a, b, kl, o) in enumerate(k["b1"], 1):
        if kl == "ĐẠT":
            continue
        sh, cell = _tach_o(o)
        out.append({"id": f"GT-{i:02d}", "code": "GT", "layer": 2, "level": "Cao", "title": t, "detail": kl,
                    "amount": (a - b) if (a is not None and b is not None) else None, "sheet": sh, "cell": cell,
                    "item": "Giá trị hợp đồng", "actual": a, "expected": b, "source": "CSDL: GT HĐ hiệu lực",
                    "formula": "", "reference": "Phụ lục áp dụng: " + (", ".join(p["so_pl"] for p in k["pls"]) or "không"),
                    "conclusion": kl})
    n = 0
    for x in k["rows"]:
        if not x["loi"]:
            continue
        n += 1
        it, m = x["it"], x["m"] or {}
        l0 = x["loi"][0]
        if l0.startswith("Lũy kế vượt"):
            code, level, key = "B1", "Cao", "kl_lk"
            actual, expected = f"{_so_vn(it['kl_lk'])} {it['dvt']} lũy kế", f"{_so_vn(m.get('kl'))} {it['dvt']} trong BOQ hiệu lực"
        elif l0.startswith("Đơn giá"):
            code, level, key = "B2", "Cao" if x["anh_huong"] else "Trung bình", "dg"
            actual, expected = f"{_so_vn(it['don_gia'])} đồng/{it['dvt']}", f"{_so_vn(m.get('don_gia'))} đồng/{it['dvt']}"
        elif l0.startswith("Cần ghép tay"):
            code, level, key = "B3", "Trung bình", "ten"
            actual = f"{it['ten'][:80]} ({it['dvt']})"
            expected = "Một trong các hạng mục BOQ cùng tên: " + (it.get("goi_y") or "")
        elif l0.startswith("Ghép theo mã HM"):
            code, level, key = "B3", "Trung bình", "ten"
            actual, expected = f"{it['ten'][:80]} ({it['dvt']})", f"{m.get('ten', '')[:80]} ({m.get('dvt', '')})"
        elif l0.startswith(("Không có trong BOQ", "Hạng mục đã bị bỏ", "Chỉ có trong")):
            code, level, key = "B3", "Cao", "ten"
            actual, expected = f"{it['ten'][:80]} ({it['dvt']})", "Không có trong BOQ hiệu lực tại ngày nghiệm thu"
        elif l0.startswith("KL HĐ"):
            code, level, key = "B4", "Trung bình", "kl_hd"
            actual, expected = f"{_so_vn(it['kl_hd'])} {it['dvt']}", f"{_so_vn(m.get('kl'))} {it['dvt']}"
        else:
            code, level, key = "B5", "Trung bình" if "kỳ trước" in l0 else "Thấp", "kl_kt"
            actual, expected = f"{_so_vn(it.get('kl_kt'))} {it['dvt']} kỳ trước", "Lũy kế đợt trước đã duyệt trong CSDL"
        col = cols.get(key) or cols.get("ten")
        cell = f"{_col(col)}{it['dong']}" if col else f"dòng {it['dong']}"
        amt = x["anh_huong"] or None
        out.append({"id": f"{code}-{n:02d}", "code": code, "layer": 2, "level": level, "title": l0,
                    "detail": "; ".join(x["loi"][1:]), "amount": amt, "sheet": sheet, "cell": cell,
                    "item": f"{(m.get('ma_hm') or it.get('ma_hm') or '')} · {nfc(it['ten'])[:80]}".strip(" ·"),
                    "actual": actual, "expected": expected,
                    "source": f"BOQ hiệu lực · {m.get('ma_hm', '—')} ({m.get('nguon', 'không có')})",
                    "formula": "", "reference": " → ".join(m.get("lich_su") or []) if m else "",
                    "conclusion": ("BOQ có nhiều hạng mục cùng tên (thiết bị lặp ở nhiều bể) và máy chưa chọn được hạng mục "
                                   "đúng. Chọn mã HM ở bảng 'Đối chiếu từng hạng mục' (nút Ghép) rồi Chạy lại; chưa tính ảnh "
                                   "hưởng tiền cho dòng này." if l0.startswith("Cần ghép tay") else
                                   f"Ảnh hưởng ước tính {_so_vn(amt)} đồng (chưa VAT) = giá trị lũy kế theo hồ sơ − giá trị "
                                   "được chấp nhận theo BOQ hiệu lực." if amt else "Chưa định lượng được ảnh hưởng tiền; cần "
                                   "đối chiếu căn cứ.")})
    if k["thieu"]:
        out.append({"id": "B6-01", "code": "B6", "layer": 2, "level": "Thấp",
                    "title": f"{len(k['thieu'])} hạng mục BOQ hiệu lực không có trong hồ sơ",
                    "detail": ", ".join(d["ma_hm"] for d in k["thieu"][:15]), "amount": None, "sheet": sheet, "cell": "",
                    "item": "", "actual": "Không có trong bảng chi tiết", "expected": "Có trong BOQ hiệu lực",
                    "source": "BOQ hiệu lực", "formula": "", "reference": "",
                    "conclusion": "Kiểm tra hạng mục chưa thực hiện hay bị bỏ sót khỏi hồ sơ."})
    return out, ngay


# ------------------------------------------------------------------ Lớp 2 · bảng kiểm: giá trị HĐ ↔ thanh toán, BOQ ↔ hồ sơ
NHOM_GT = "Giá trị hợp đồng so với giá trị thực hiện, thanh toán"
NHOM_HM = "Đơn giá và khối lượng: BOQ hiệu lực so với hồ sơ thanh toán"


def _ghi_vn(t):
    """1,684,661,368 → 1.684.661.368 (số tiền trong ghi chú bảng kiểm, cách viết Việt Nam)."""
    return re.sub(r"\b\d{1,3}(?:,\d{3}){2,}\b", lambda m: m.group(0).replace(",", "."), str(t or ""))


def bang_kiem_lop2(k, ph2, cs, con):
    """Các bước Lớp 2 đã so, kể cả bước đạt (để anh thấy đủ), + phát hiện cho các bước số tổng mà _lop2 chưa có.
    k: tinh_doi_chieu_dot; ph2: phát hiện Lớp 2 đã có (B1–B6, GT). Trả (phát hiện mới, dòng bảng kiểm, từng hạng mục)."""
    from master_hd import nfc
    tong, gt_hl, vat1 = k["tong"], k["gt_hl"], k["vat1"]
    g = lambda kk: (tong.get(kk) or {}).get("gia_tri")  # noqa: E731
    o_ = lambda kk: (tong.get(kk) or {}).get("o", "")  # noqa: E731
    tol = cs.tol_tien
    moi, hang = [], []

    def ph(level, title, detail, o, actual, expected, amount=None):
        sh, cell = _tach_o(o)
        moi.append(f := {"id": "", "code": "GT", "layer": 2, "level": level, "title": title, "detail": detail,
                         "amount": amount, "sheet": sh, "cell": cell, "item": "Giá trị hợp đồng / thanh toán",
                         "actual": actual, "expected": expected, "source": "CSDL: HĐ + phụ lục hiệu lực, các đợt đã nạp",
                         "formula": "", "reference": "", "conclusion": detail})
        return f

    def dong(nhom, ten, ho_so, hd, kq, o="", ghi="", f=None, chenh="tu_dong", don_vi="đồng"):
        if chenh == "tu_dong":
            chenh = (ho_so - hd) if isinstance(ho_so, (int, float)) and isinstance(hd, (int, float)) else None
        hang.append({"nhom": nhom, "ten": ten, "ho_so": ho_so, "hd": hd, "chenh": chenh, "don_vi": don_vi, "ket_qua": kq,
                     "o": o, "ghi": ghi, "finding": f})

    def tim(code):
        return next((f for f in ph2 if f["code"] == code), None)
    # A1. GT HĐ trong hồ sơ = GT HĐ hiệu lực
    t, a, b, kl, o = k["b1"][0]
    pls = ", ".join(p["so_pl"] for p in k["pls"]) or "không có phụ lục áp dụng"
    dong(NHOM_GT, "GT hợp đồng ghi trong hồ sơ = GT HĐ hiệu lực tại ngày nghiệm thu (gốc + phụ lục)", a, b,
         "Đạt" if kl == "ĐẠT" else "Không có số liệu" if a is None else "Lệch", o or o_("gt_hd"),
         f"Phụ lục áp dụng: {pls}" + ("" if kl == "ĐẠT" else f". {kl}"), tim("GT"))
    # A2. GT lũy kế thực hiện ≤ GT HĐ hiệu lực
    lk, lk_kt, kn = g("gt_lk"), g("gt_lk_kt"), g("gt_kn")
    ten = "GT lũy kế thực hiện đến hết kỳ này ≤ GT HĐ hiệu lực"
    if lk is None:
        dong(NHOM_GT, ten, None, gt_hl, "Không có số liệu", "", "Không đọc được GT lũy kế thực hiện trong hồ sơ.")
    elif lk <= gt_hl + tol(gt_hl):
        dong(NHOM_GT, ten, lk, gt_hl, "Đạt", o_("gt_lk"), chenh=None, ghi=f"Đã thực hiện {_pct(lk / gt_hl) if gt_hl else '—'} GT HĐ; "
             f"còn lại {gt_hl - lk:,.0f} đồng.")
    else:
        f = ph("Cao", f"GT lũy kế thực hiện {lk:,.0f} vượt GT HĐ hiệu lực {gt_hl:,.0f}",
               f"Vượt {lk - gt_hl:,.0f} đồng ({_pct(lk / gt_hl)} GT HĐ). Phần vượt cần phụ lục điều chỉnh giá trị HĐ "
               "trước khi thanh toán.", o_("gt_lk"), f"{lk:,.0f}", f"{gt_hl:,.0f}", amount=round(lk - gt_hl))
        dong(NHOM_GT, ten, lk, gt_hl, "Lệch", o_("gt_lk"), f"Vượt {_pct(lk / gt_hl - 1)} GT HĐ.", f)
    # A3. lũy kế kỳ trước + kỳ này = lũy kế kỳ này (cộng trong hồ sơ)
    if None not in (lk, lk_kt, kn):
        ten = "GT lũy kế hết kỳ trước + GT thực hiện kỳ này = GT lũy kế hết kỳ này (cộng trong hồ sơ)"
        if abs(lk_kt + kn - lk) <= 1000:
            dong(NHOM_GT, ten, lk, lk_kt + kn, "Đạt", o_("gt_lk"), f"{lk_kt:,.0f} + {kn:,.0f}")
        else:
            f = ph("Trung bình", f"Lũy kế hết kỳ này {lk:,.0f} ≠ lũy kế kỳ trước + kỳ này ({lk_kt + kn:,.0f})",
                   f"{lk_kt:,.0f} + {kn:,.0f} = {lk_kt + kn:,.0f}; bảng tổng hợp cộng sai hoặc có khoản khác.",
                   o_("gt_lk"), f"{lk:,.0f}", f"{lk_kt + kn:,.0f}", amount=round(lk - lk_kt - kn))
            dong(NHOM_GT, ten, lk, lk_kt + kn, "Lệch", o_("gt_lk"), f"{lk_kt:,.0f} + {kn:,.0f}", f)
    # A4. lũy kế hết kỳ trước = lũy kế đợt trước đã duyệt (CSDL)
    ten = "GT lũy kế hết kỳ trước = lũy kế đợt trước đã duyệt trong CSDL"
    if k["dot_truoc"]:
        r = con.execute("SELECT gt_luy_ke FROM dot_thanh_toan WHERE ma_hd = ? AND dot = ?", (k["ma"], k["dot_truoc"])).fetchone()
        db = r[0] if r else None
        if lk_kt is None or db is None:
            dong(NHOM_GT, ten, lk_kt, db, "Không có số liệu", o_("gt_lk_kt"), f"Đợt {k['dot_truoc']}")
        elif abs(lk_kt - db) <= 1000:
            dong(NHOM_GT, ten, lk_kt, db, "Đạt", o_("gt_lk_kt"), f"Đợt {k['dot_truoc']} đã nạp")
        else:
            f = ph("Trung bình", f"Lũy kế hết kỳ trước {lk_kt:,.0f} ≠ lũy kế đợt {k['dot_truoc']} đã duyệt ({db:,.0f})",
                   "Hồ sơ dùng số lũy kế kỳ trước khác số đã duyệt — kiểm tra đợt trước có bị sửa lại không.",
                   o_("gt_lk_kt"), f"{lk_kt:,.0f}", f"{db:,.0f}", amount=round(lk_kt - db))
            dong(NHOM_GT, ten, lk_kt, db, "Lệch", o_("gt_lk_kt"), f"Đợt {k['dot_truoc']} đã nạp", f)
    else:
        dong(NHOM_GT, ten, lk_kt, None, "Không áp dụng" if not lk_kt else "Cần xem", o_("gt_lk_kt"),
             "CSDL chưa có đợt trước của HĐ này" + (" — lũy kế kỳ trước chưa đối chiếu được" if lk_kt else ""))
    # A5. Σ(KL kỳ này × đơn giá hiệu lực) × (1 + VAT) = GT thực hiện kỳ này
    ten = "GT thực hiện kỳ này = Σ(KL kỳ này × đơn giá BOQ hiệu lực) × (1 + VAT)"
    sk = round(k["sum_kn"])
    if kn is None:
        dong(NHOM_GT, ten, None, sk, "Không có số liệu", "", "Không đọc được GT thực hiện kỳ này trong hồ sơ.")
    elif abs(kn - sk) <= tol(kn):
        dong(NHOM_GT, ten, kn, sk, "Đạt", o_("gt_kn"), f"VAT {_pct(vat1 - 1)}")
    else:
        f = ph("Cao", f"GT thực hiện kỳ này {kn:,.0f} ≠ Σ KL kỳ này × đơn giá HĐ × (1+VAT) = {sk:,.0f}",
               f"Chênh {kn - sk:,.0f} đồng (sau VAT). Xem bảng từng hạng mục: đơn giá / KL kỳ này lệch hoặc có hạng mục "
               "ngoài BOQ.", o_("gt_kn"), f"{kn:,.0f}", f"{sk:,.0f}", amount=round(kn - sk))
        dong(NHOM_GT, ten, kn, sk, "Lệch", o_("gt_kn"), f"VAT {_pct(vat1 - 1)}", f)
    # A6. lũy kế đề nghị thanh toán (các đợt đã nạp + kỳ này) ≤ GT HĐ
    tt = g("tt_ky_nay")
    if tt is not None:
        q = "SELECT COUNT(*), SUM(gt_tt_ky) FROM dot_thanh_toan WHERE ma_hd = ?" + (" AND dot < ?" if k["dot"] else "")
        n, da = con.execute(q, (k["ma"], k["dot"]) if k["dot"] else (k["ma"],)).fetchone()
        da = da or 0
        ten = "Lũy kế thanh toán (các đợt đã nạp CSDL + đề nghị kỳ này) ≤ GT HĐ hiệu lực"
        tong_tt = da + tt
        if tong_tt <= gt_hl + tol(gt_hl):
            dong(NHOM_GT, ten, tong_tt, gt_hl, "Đạt", o_("tt_ky_nay"), chenh=None,
                 ghi=f"{n} đợt đã nạp {da:,.0f} + kỳ này {tt:,.0f} = {_pct(tong_tt / gt_hl) if gt_hl else '—'} GT HĐ")
        else:
            f = ph("Cao", f"Lũy kế thanh toán {tong_tt:,.0f} vượt GT HĐ hiệu lực {gt_hl:,.0f}",
                   f"{n} đợt đã nạp {da:,.0f} + đề nghị kỳ này {tt:,.0f}.", o_("tt_ky_nay"), f"{tong_tt:,.0f}",
                   f"{gt_hl:,.0f}", amount=round(tong_tt - gt_hl))
            dong(NHOM_GT, ten, tong_tt, gt_hl, "Lệch", o_("tt_ky_nay"), f"{n} đợt đã nạp {da:,.0f} + kỳ này {tt:,.0f}", f)
    # C. từng hạng mục
    rows = k["rows"]
    co_boq = [x for x in rows if x["m"]]
    N = len(rows)

    def dem(chu):
        return sum(1 for x in rows if any(l.startswith(chu) for l in x["loi"]))

    def kq_dem(code, n_loi, tong_n, ten, ghi_ok, ghi_loi, khong=False):
        if khong:
            dong(NHOM_HM, ten, None, None, "Không áp dụng", "", ghi_ok, chenh=None, don_vi="hạng mục")
            return
        if not tong_n:
            dong(NHOM_HM, ten, None, None, "Không có số liệu", "", "Hồ sơ không có cột / hạng mục để so", chenh=None,
                 don_vi="hạng mục")
            return
        f = tim(code)
        dong(NHOM_HM, ten, f"{tong_n - n_loi}/{tong_n} đạt", f"{n_loi} lệch" if n_loi else "khớp",
             "Lệch" if n_loi else "Đạt", "", ghi_loi if n_loi else ghi_ok, f["id"] if (f and n_loi) else None,
             chenh=None, don_vi="hạng mục")
    ngoai = dem("Không có trong BOQ") + dem("Hạng mục đã bị bỏ") + dem("Chỉ có trong")
    cho_ghep = dem("Cần ghép tay") + dem("Ghép theo mã HM")
    can_xem = sum(1 for x in rows if x["it"].get("ma_hm") and x["it"].get("cach_khop", "").startswith(("tên trùng", "tên gần")))
    ten = "Hạng mục trong hồ sơ có trong BOQ hiệu lực"
    if not N:
        kq_dem("B3", 0, 0, ten, "", "")
    else:
        f = tim("B3")
        ghi = "; ".join(x for x in (
            f"{ngoai} hạng mục ngoài BOQ hiệu lực (phát sinh chưa có phụ lục hoặc đã bị bỏ)" if ngoai else "",
            f"{cho_ghep} hạng mục cần ghép tay (tên trùng nhiều hạng mục BOQ / mã HM lệch tên) — chọn mã ở bảng từng hạng "
            "mục" if cho_ghep else "",
            f"{can_xem} hạng mục máy ghép theo tên trùng / gần đúng (xem cột Khớp bằng)" if can_xem else "") if x) \
            or f"{N} hạng mục trong bảng chi tiết đều ghép được với BOQ hiệu lực"
        dong(NHOM_HM, ten, f"{N - ngoai - cho_ghep}/{N} ghép được", f"{ngoai + cho_ghep} chưa" if ngoai + cho_ghep else "khớp",
             "Lệch" if ngoai else "Cần xem" if cho_ghep else "Đạt", "", ghi, f["id"] if (f and (ngoai or cho_ghep)) else None,
             chenh=None, don_vi="hạng mục")
    ah_dg = sum(x["anh_huong"] for x in rows if any(l.startswith("Đơn giá") for l in x["loi"]))
    kq_dem("B2", dem("Đơn giá"), len(co_boq), "Đơn giá trong hồ sơ = đơn giá BOQ hiệu lực",
           "Mọi đơn giá khớp BOQ hiệu lực (chênh ≤ 0,5 đồng)", f"Ảnh hưởng đơn giá × KL lũy kế ≈ {ah_dg:,.0f} đồng chưa VAT")
    kq_dem("B4", dem("KL HĐ"), sum(1 for x in co_boq if x["it"].get("kl_hd") is not None),
           "KL hợp đồng ghi trong hồ sơ = KL BOQ hiệu lực", "Khớp", "Hồ sơ ghi KL HĐ khác BOQ hiệu lực")
    kq_dem("B1", dem("Lũy kế vượt"), len(co_boq), "KL lũy kế đến hết kỳ này ≤ KL BOQ hiệu lực",
           f"Không hạng mục nào vượt (HĐ {k['loai'] or '?'})", "Vượt KL HĐ: cần phụ lục / biên bản phát sinh")
    if k["kt_chi_tiet"]:
        kq_dem("B5", dem("KL kỳ trước") + dem("Có KL kỳ trước"), len(co_boq),
               f"KL kỳ trước = KL lũy kế đợt {k['dot_truoc']} đã duyệt", "Khớp từng hạng mục",
               "KL kỳ trước khác số đã duyệt")
    else:
        kq_dem("B5", 0, 0, "KL kỳ trước = KL lũy kế đợt trước đã duyệt", (
            f"Đợt {k['dot_truoc']} trong CSDL chỉ có số tổng, chưa có KL từng hạng mục" if k["dot_truoc"]
            else "CSDL chưa có đợt trước") + " — chưa đối chiếu được", "", khong=True)
    th = len(k["thieu"])
    f = tim("B6")
    dong(NHOM_HM, "Hạng mục BOQ hiệu lực có trong hồ sơ", f"{len(k['hl']) - th}/{len(k['hl'])} có",
         f"{th} thiếu" if th else "đủ", "Cần xem" if th else "Đạt", "",
         ", ".join(d["ma_hm"] for d in k["thieu"][:12]) if th else "Mọi hạng mục BOQ đều có trong bảng chi tiết",
         f["id"] if f else None, chenh=None, don_vi="hạng mục")
    for h in hang:
        h["ghi"] = _ghi_vn(h["ghi"])
    # bảng từng hạng mục (cả hạng mục đạt) cho giao diện
    kt = k["kt"] or {}
    hm = []
    for x in rows:
        it, m = x["it"], x["m"] or {}
        hm.append({"dong": it.get("dong"), "ma_hm": m.get("ma_hm") or it.get("ma_hm") or "", "ten": nfc(it.get("ten") or "")[:160],
                   "nhom": nfc(it.get("nhom") or "")[:80], "dvt": it.get("dvt"), "khop": it.get("cach_khop") or "",
                   "khoa": it.get("khoa") or "", "ma_rieng": it.get("ma_rieng") or "", "can_ghep": bool(it.get("can_ghep")),
                   "ung_vien": [dict(u, ten=nfc(u["ten"])[:120], nhom=nfc(u["nhom"])[:80]) for u in it.get("ung_vien") or []],
                   "kl_hd_hs": it.get("kl_hd"), "kl_hd": m.get("kl"), "dg_hs": it.get("don_gia"), "dg_hd": m.get("don_gia"),
                   "kl_kt": it.get("kl_kt"), "kl_kt_db": kt.get(m.get("ma_hm")) if m else None, "kl_kn": it.get("kl_kn"),
                   "kl_lk": it.get("kl_lk"), "nguon": m.get("nguon") or "", "anh_huong": x["anh_huong"], "loi": x["loi"]})
    return moi, hang, hm


# ------------------------------------------------------------------ Lớp 2 · B5: tham số thanh toán / khấu trừ ↔ HĐ
MA_TY_LE_TT = (("TT-10", "Tạm ứng"), ("TT-20", "Tỷ lệ thanh toán"), ("TT-21", "Giữ lại"), ("TT-30", "Thanh toán quyết toán"),
               ("TT-31", "Bảo hành"))


def _ty_le_trong(chu):
    """Các tỷ lệ trong giá trị tham số: số CSDL đã chuẩn hoá (0.9) hoặc chữ ('90% giá trị…; giữ lại 5%') → [0.9, 0.05]."""
    if isinstance(chu, (int, float)) or re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", str(chu or "")):
        try:
            x = float(str(chu).replace(",", "."))
        except ValueError:
            return []
        return [x] if 0 < x <= 1 else [x / 100] if 1 < x <= 100 else []
    out = []
    for m in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", str(chu or "")):
        try:
            out.append(float(m.replace(",", ".")) / 100)
        except ValueError:
            pass
    return out


def _ty_le_hang_so(s):
    """'8%' / '0.08' / '1.08' / '90%' → (tỷ lệ, kiểu) hoặc (None, '')."""
    t = str(s).strip().replace(",", ".")
    try:
        if t.endswith("%"):
            return float(t[:-1]) / 100, "%"
        x = float(t)
    except ValueError:
        return None, ""
    if 1 < x < 1.5:
        return round(x - 1, 6), "hệ số (1 + x)"
    if 0 < x <= 1:
        return x, "tỷ lệ"
    return None, ""


def _pct(x):
    return f"{x * 100:.3f}".rstrip("0").rstrip(".").replace(".", ",") + "%"


def doi_chieu_tham_so(nhung, cay, tong, ts, vat, bang=None):
    """Lớp 2 · B5 (quy trình mục 4): hằng số gõ cứng (K6), ô tham số nhập tay trên cây truy vết (nhóm 6) và các khoản
    giữ lại / thu hồi tạm ứng / thanh toán trong hồ sơ ↔ tham số HĐ hiệu lực tại ngày nghiệm thu.
    nhung: toan_ven kq['nhung']; cay: kq['cay']; tong: số tổng hợp theo nhãn; ts: {mã: giá trị}; vat: TT-04 (0.08).
    Trả danh sách phát hiện (B7 hằng số / tham số, B8 khấu trừ). bang (list): thêm các dòng bảng kiểm Lớp 2 nhóm
    "Tỷ lệ thanh toán và khấu trừ" (kể cả dòng đạt) để giao diện hiện đủ các bước đã so."""
    from master_hd import bo_dau
    ung = [("TT-04", "VAT", vat)] if vat is not None else []
    for ma, ten in MA_TY_LE_TT:
        for r in _ty_le_trong(ts.get(ma)):
            ung.append((ma, ten, r))
            if ma in ("TT-20", "TT-21") and 0 < r < 1:
                ung.append((ma, f"100% − {ten.lower()}", round(1 - r, 6)))
    mo_ta_hd = "; ".join(f"{m} {t} {_pct(r)}" for m, t, r in ung if not t.startswith("100%")) or "HĐ không ghi tỷ lệ nào"

    def khop(r, chi_vat=False):
        return [(m, t) for m, t, x in ung if abs(x - r) < 1e-6 and (not chi_vat or m == "TT-04")]
    out, khop_ok, da = [], [], set()

    def them(level, title, detail, o="", actual="", expected="", amount=None, code="B7", ref="A01 điều khoản hợp đồng"):
        sh, _, cell = (o or "").partition("!")
        out.append(f := {"id": "", "code": code, "layer": 2, "level": level, "title": title, "detail": detail, "amount": amount,
                    "sheet": sh if cell else "", "cell": cell or o, "item": "Tham số thanh toán", "actual": actual,
                    "expected": expected, "source": "CSDL: tham số HĐ hiệu lực tại ngày nghiệm thu", "formula": "",
                    "reference": ref, "conclusion": detail})
        return f
    so_lech = []
    # 1. hằng số gõ thẳng trong công thức thuộc cây truy vết
    for s, loai, n, n_cay, vd, f in nhung or []:
        if loai.startswith("Hằng số khác") or not n_cay:
            continue
        r, kieu = _ty_le_hang_so(s)
        if r is None or (s, "nhung") in da:
            continue
        da.add((s, "nhung"))
        # hệ số 1,08 / 1,1 chắc chắn là (1 + VAT); 8% / 10% chỉ "có thể" là thuế suất → so mọi tỷ lệ trước
        la_vat = loai.startswith("Thuế suất") and (kieu == "hệ số (1 + x)" or r <= 0.1)
        k = khop(r, chi_vat=kieu == "hệ số (1 + x)")
        o0 = vd.split(",")[0].strip()
        if k:
            khop_ok.append(f"{s} = " + " / ".join(f"{m} {tt}" for m, tt in dict.fromkeys(k)))
        elif la_vat:
            so_lech.append(them("Cao", f"Hằng số {s} trong công thức (thuế suất?) khác VAT của HĐ {_pct(vat or 0)}",
                 f"{n_cay} công thức trên đường tính số đề nghị dùng {s} ({kieu}). Thuế suất theo HĐ (TT-04) là "
                 f"{_pct(vat or 0)}. Yêu cầu nhà thầu giải trình hoặc sửa công thức.", o0, f"{s} ({kieu})",
                 f"TT-04 = {_pct(vat or 0)}"))
        else:
            so_lech.append(them("Trung bình", f"Hằng số {s} trong công thức không khớp tham số thanh toán nào của HĐ",
                 f"{n_cay} công thức trên đường tính số đề nghị dùng {s} ({kieu}); không trùng tỷ lệ nào trong HĐ "
                 f"({mo_ta_hd}). Kiểm tra căn cứ (phụ lục, biên bản thương thảo).", o0, f"{s} ({kieu})", mo_ta_hd))
    # 2. ô tham số nhập tay trên cây truy vết (nhóm 6)
    for row in cay or []:
        if row.get("loai") != "Nhập tay" or not str(row.get("nhom") or "").startswith("6"):
            continue
        v, o, nhan = row.get("gia_tri"), row.get("o") or "", str(row.get("ten") or "").strip()
        if not isinstance(v, (int, float)) or (o, "cay") in da:
            continue
        da.add((o, "cay"))
        r = v - 1 if 1 < v < 1.5 else (v / 100 if 1 < v <= 100 and "%" in nhan else v)
        if not 0 < r <= 1:
            continue
        b = bo_dau(nhan)
        chi = "TT-04" if re.search(r"thue|vat|gtgt", b) else "TT-21" if "giu lai" in b else \
              "TT-10" if "tam ung" in b else "TT-20" if "thanh toan" in b else None
        k = [x for x in khop(r) if not chi or x[0] == chi]
        if k:
            khop_ok.append(f"{o} {_pct(r)} = {k[0][0]} {k[0][1]}")
            continue
        exp = next(((f"{m} {t} {_pct(x)}") for m, t, x in ung if m == chi), None) if chi else None
        so_lech.append(them("Cao" if chi in ("TT-04", "TT-21") else "Trung bình",
             f"Ô tham số {o} = {_pct(r)} khác HĐ" + (f" ({exp})" if exp else ""),
             f"Ô nhập tay '{nhan[:80]}' nằm trên đường tính số đề nghị thanh toán. " +
             (f"HĐ: {exp}." if exp else f"Không trùng tỷ lệ nào trong HĐ ({mo_ta_hd}).") +
             " Yêu cầu nhà thầu giải trình hoặc sửa.", o, _pct(r), exp or mo_ta_hd))
    # 3. tỷ lệ thanh toán và các khoản khấu trừ trên bảng tổng hợp (tìm theo nhãn) — ghi cả dòng đạt vào bảng kiểm
    g = lambda kk: (tong.get(kk) or {}).get("gia_tri")  # noqa: E731
    o_ = lambda kk: (tong.get(kk) or {}).get("o", "")  # noqa: E731
    gt_kn, gl, th, tt = g("gt_kn"), g("giu_lai"), g("thu_hoi_tu"), g("tt_ky_nay")
    th = abs(th or 0)
    giu = _ty_le_trong(ts.get("TT-21"))
    ty_tt = [x for x in _ty_le_trong(ts.get("TT-20")) if 0 < x <= 1]
    tu = str(ts.get("TT-10") or "")
    khong_tu = re.search(r"^\s*(không|khong)\b", tu.lower()) is not None or not tu.strip()
    hang = []

    def dong(ten, ho_so, hd, kq, o="", ghi="", f=None, chenh=None, don_vi="đồng"):
        hang.append({"nhom": "Tỷ lệ thanh toán và khấu trừ so với tham số HĐ", "ten": ten, "ho_so": ho_so, "hd": hd,
                     "chenh": chenh, "don_vi": don_vi, "ket_qua": kq, "o": o, "ghi": ghi, "finding": f})
    # 3a. đề nghị thanh toán kỳ này = TT-20 × GT thực hiện kỳ này − thu hồi tạm ứng
    ten_tt = "Đề nghị thanh toán kỳ này = tỷ lệ thanh toán HĐ (TT-20) × GT thực hiện kỳ này − thu hồi tạm ứng"
    if tt is None or not gt_kn:
        dong(ten_tt, tt, None, "Không có số liệu", o_("tt_ky_nay") or o_("gt_kn"),
             "Không đọc được " + ("số đề nghị thanh toán kỳ này" if tt is None else "GT thực hiện kỳ này") + " trong hồ sơ.")
    elif not ty_tt:
        dong(ten_tt, tt, None, "Cần xem", o_("tt_ky_nay"),
             f"Hồ sơ đề nghị {_pct(tt / gt_kn)} GT kỳ này; CSDL chưa có tỷ lệ thanh toán TT-20 ({ts.get('TT-20') or 'trống'}).")
    else:
        exp, r = min(((round(x * gt_kn - th), x) for x in ty_tt), key=lambda c: abs(tt - c[0]))
        ghi = (f"{_pct(r)} × {gt_kn:,.0f}" + (f" − thu hồi tạm ứng {th:,.0f}" if th else "") + f" = {exp:,.0f}; "
               f"hồ sơ đề nghị {_pct(tt / gt_kn)} GT kỳ này. TT-20: {str(ts.get('TT-20'))[:160]}")
        if abs(tt - exp) <= 1000:
            dong(ten_tt, tt, exp, "Đạt", o_("tt_ky_nay"), ghi, chenh=tt - exp)
        else:
            f = them("Cao", f"Đề nghị thanh toán kỳ này {tt:,.0f} khác {_pct(r)} GT thực hiện kỳ này theo HĐ ({exp:,.0f})",
                     ghi + ". Yêu cầu nhà thầu giải trình hoặc điều chỉnh.", o_("tt_ky_nay"), f"{tt:,.0f}", f"{exp:,.0f}",
                     amount=round(tt - exp), code="B8")
            dong(ten_tt, tt, exp, "Lệch", o_("tt_ky_nay"), ghi, f, chenh=tt - exp)
    # 3b. số học trong hồ sơ: đề nghị = GT kỳ này − giữ lại − thu hồi tạm ứng
    if tt is not None and gt_kn and gl:
        exp2 = gt_kn - abs(gl) - th
        ten2 = "Đề nghị kỳ này = GT thực hiện kỳ này − giữ lại − thu hồi tạm ứng (cộng trừ trong hồ sơ)"
        ghi2 = f"{gt_kn:,.0f} − {abs(gl):,.0f}" + (f" − {th:,.0f}" if th else "") + f" = {exp2:,.0f}"
        if abs(tt - exp2) <= 1000:
            dong(ten2, tt, exp2, "Đạt", o_("tt_ky_nay"), ghi2, chenh=tt - exp2)
        else:
            f = them("Trung bình", f"Số đề nghị {tt:,.0f} ≠ GT kỳ này − khấu trừ ({exp2:,.0f})", ghi2 +
                     ". Bảng tổng hợp cộng trừ không khớp — kiểm tra các khoản khấu trừ khác.", o_("tt_ky_nay"),
                     f"{tt:,.0f}", f"{exp2:,.0f}", amount=round(tt - exp2), code="B8")
            dong(ten2, tt, exp2, "Lệch", o_("tt_ky_nay"), ghi2, f, chenh=tt - exp2)
    # 3c. giữ lại = TT-21 × GT kỳ này
    ten_gl = "Giữ lại = tỷ lệ giữ lại HĐ (TT-21) × GT thực hiện kỳ này"
    if gt_kn:
        if gl:
            r = abs(gl) / gt_kn
            if giu and not any(abs(r - x) <= 0.0005 for x in giu):
                f = them("Cao", f"Giữ lại = {_pct(r)} GT thực hiện kỳ này, HĐ quy định {', '.join(_pct(x) for x in giu)}",
                         f"Giữ lại {abs(gl):,.0f} / GT kỳ này {gt_kn:,.0f} = {_pct(r)}; TT-21: {ts.get('TT-21')}",
                         o_("giu_lai"), f"{abs(gl):,.0f} ({_pct(r)})",
                         f"{_pct(giu[0])} × {gt_kn:,.0f} = {giu[0] * gt_kn:,.0f}",
                         amount=round(giu[0] * gt_kn - abs(gl)), code="B8")
                dong(ten_gl, abs(gl), round(giu[0] * gt_kn), "Lệch", o_("giu_lai"),
                     f"Hồ sơ giữ lại {_pct(r)}; TT-21: {str(ts.get('TT-21'))[:120]}", f, chenh=abs(gl) - round(giu[0] * gt_kn))
            elif not giu:
                f = them("Trung bình", "Hồ sơ có khoản giữ lại nhưng HĐ không ghi tỷ lệ giữ lại (TT-21)",
                         f"Giữ lại {abs(gl):,.0f} = {_pct(r)} GT kỳ này; TT-21: {ts.get('TT-21') or 'không có'}",
                         o_("giu_lai"), f"{abs(gl):,.0f}", "TT-21", code="B8")
                dong(ten_gl, abs(gl), None, "Cần xem", o_("giu_lai"), f"Hồ sơ giữ lại {_pct(r)}; HĐ không ghi TT-21", f)
            else:
                khop_ok.append(f"giữ lại {_pct(r)} = TT-21")
                x = min(giu, key=lambda x: abs(r - x))
                dong(ten_gl, abs(gl), round(x * gt_kn), "Đạt", o_("giu_lai"),
                     f"{_pct(x)} × {gt_kn:,.0f}; TT-21: {str(ts.get('TT-21'))[:120]}", chenh=abs(gl) - round(x * gt_kn))
        elif giu and any(x > 0 for x in giu):
            f = them("Trung bình", f"Không thấy dòng giữ lại trong hồ sơ, HĐ quy định giữ lại {_pct(giu[0])}",
                     f"TT-21: {ts.get('TT-21')}. Số phải giữ ≈ {giu[0] * gt_kn:,.0f} đồng (trên GT thực hiện kỳ này).",
                     o_("gt_kn"), "không có", f"{_pct(giu[0])} × {gt_kn:,.0f}", amount=round(giu[0] * gt_kn), code="B8")
            dong(ten_gl, None, round(giu[0] * gt_kn), "Lệch", o_("gt_kn"), "Hồ sơ không có dòng giữ lại", f)
        else:
            dong(ten_gl, None, None, "Không áp dụng", "", f"HĐ không ghi tỷ lệ giữ lại (TT-21: {ts.get('TT-21') or 'trống'})")
    # 3d. thu hồi tạm ứng ↔ TT-10 / TT-11
    ten_th = "Thu hồi tạm ứng so với tạm ứng HĐ (TT-10, TT-11)"
    if th and khong_tu:
        f = them("Cao", "Hồ sơ có thu hồi tạm ứng nhưng HĐ không có tạm ứng (TT-10)",
                 f"Thu hồi {th:,.0f}; TT-10: {tu or 'không có'}", o_("thu_hoi_tu"), f"{th:,.0f}", "TT-10", code="B8")
        dong(ten_th, th, None, "Lệch", o_("thu_hoi_tu"), f"TT-10: {tu or 'không có'}", f)
    elif th and gt_kn:
        f = them("Thấp", f"Thu hồi tạm ứng kỳ này {th:,.0f} = {_pct(th / gt_kn)} GT thực hiện — đối chiếu TT-11",
                 f"TT-10: {tu[:160]}. TT-11: {str(ts.get('TT-11') or '—')[:240]}", o_("thu_hoi_tu"), f"{th:,.0f}",
                 str(ts.get("TT-11") or "")[:120], code="B8")
        dong(ten_th, th, None, "Cần xem", o_("thu_hoi_tu"), f"= {_pct(th / gt_kn)} GT kỳ này. TT-11: "
             f"{str(ts.get('TT-11') or '—')[:160]}", f)
    elif not khong_tu and gt_kn:
        f = them("Thấp", "Không thấy dòng thu hồi tạm ứng trong hồ sơ — kiểm tra điều kiện thu hồi (TT-11)",
                 f"TT-10: {tu[:160]}. TT-11: {str(ts.get('TT-11') or '—')[:240]}", "", "không có",
                 str(ts.get("TT-11") or "")[:120], code="B8")
        dong(ten_th, 0, None, "Cần xem", "", f"HĐ có tạm ứng: {tu[:120]}", f)
    else:
        dong(ten_th, th or 0, 0, "Đạt" if not th else "Cần xem", o_("thu_hoi_tu"),
             f"HĐ không có tạm ứng (TT-10: {tu or 'trống'}); hồ sơ không thu hồi")
    # 3e. hằng số / ô tham số gõ tay trên đường tính số đề nghị
    ten_b7 = "Hằng số và ô tham số gõ tay trên đường tính số đề nghị = tham số HĐ (VAT, tỷ lệ)"
    if so_lech:
        dong(ten_b7, f"{len(khop_ok)} khớp · {len(so_lech)} lệch", mo_ta_hd, "Lệch", "", "; ".join(khop_ok[:8]),
             so_lech[0], don_vi="")
    else:
        dong(ten_b7, f"{len(khop_ok)} khớp" if khop_ok else "không có", mo_ta_hd, "Đạt" if khop_ok else "Không áp dụng",
             "", "; ".join(khop_ok[:8]) or "Không có hằng số / ô tỷ lệ nào trên đường tính", don_vi="")
    if khop_ok:
        them("Thấp", f"{len(khop_ok)} tham số trong hồ sơ khớp HĐ", "; ".join(khop_ok[:12]), "", "khớp", mo_ta_hd)
    for i, f in enumerate(out, 1):
        f["id"] = f"{f['code']}-{i:02d}"
    for h in hang:
        h["finding"] = h["finding"]["id"] if h["finding"] else None
        h["ghi"] = _ghi_vn(h["ghi"])
    if bang is not None:
        bang.extend(hang)
    return out


def _lop2b(kt, k, cs, con, bang=None):
    ts = {}
    for ma in ("TT-04", "TT-10", "TT-11", "TT-20", "TT-21", "TT-30", "TT-31"):
        try:
            ts[ma], _ = cs.tham_so_hieu_luc(con, k["ma"], ma, k["ngay"])
        except Exception:  # noqa: BLE001
            ts[ma] = None
    cay = [{"o": r[2], "gia_tri": r[4], "loai": r[5], "nhom": r[6], "ten": r[1]} for r in kt.kq.get("cay", [])]
    return doi_chieu_tham_so(kt.kq.get("nhung"), cay, k["tong"], ts, k["vat"], bang=bang)


def _so_vn(v):
    if v is None:
        return "—"
    if abs(v - round(v)) < 1e-9:
        return f"{v:,.0f}".replace(",", ".")
    return f"{v:,.3f}".rstrip("0").replace(",", "X").replace(".", ",").replace("X", ".")


def _thu_muc_kq(loai):
    p = ch.thu_muc_du_lieu() / loai
    p.mkdir(parents=True, exist_ok=True)
    return p


def _luu(loai, ma, d):
    p = _thu_muc_kq(loai) / f"{ma}.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, default=str)
    return p


def doc_ket_qua_kiem_tra(loai, ma):
    if not re.fullmatch(r"[\w\-]+", ma or ""):
        raise ValueError("Mã kết quả không hợp lệ")
    p = _thu_muc_kq(loai) / f"{ma}.json"
    if not p.exists():
        raise FileNotFoundError(ma)
    return json.loads(p.read_text(encoding="utf-8"))


def ds_ket_qua_kiem_tra(loai, gioi_han=30):
    out = []
    for p in sorted(_thu_muc_kq(loai).glob("*.json"), key=lambda x: -x.stat().st_mtime)[:gioi_han]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        out.append({k: d.get(k) for k in ("ma", "loai", "tep", "luc", "hop_dong", "dot", "ngay_nghiem_thu", "dem",
                                          "de_nghi", "anh_huong", "da_nap", "so_phat_hien")})
    return out


def toan_ven(v, path, o_dich=None, duong_dan_tai=None):
    import toan_ven as tv
    v.tien_do(0.05, "Đọc cấu trúc file…")
    kt = tv.KiemTra(path, o_dich or None)
    v.tien_do(0.15, "Kiểm tra công thức, liên kết và truy vết số đề nghị…")
    kt.chay()
    v.tien_do(0.85, "Tổng hợp báo cáo…")
    ma = v.id
    out = _thu_muc_kq("toan_ven") / f"{ma}.xlsx"
    tv.ghi(kt, out)
    ph, bang_k, cay, dich = _lop1(kt, Path(path).name)
    de_nghi = next((r["gia_tri"] for r in cay if r["cap"] == 0), None)
    d = {"ma": ma, "loai": "toan_ven", "tep": Path(path).name, "luc": _bay_gio(), "dich": dich, "de_nghi": de_nghi,
         "phat_hien": ph, "bang_k": bang_k, "cay": cay, "dem": dict(Counter(f["level"] for f in ph)),
         "so_phat_hien": len(ph), "so_sheet": len(kt.sd.wb.sheetnames),
         "tai": duong_dan_tai(out) if duong_dan_tai else ""}
    _luu("toan_ven", ma, _json(d))
    return _json(d)


def kiem_tra_dot(v, ref, path, ngay_nt, dot=None, duong_dan_tai=None):
    import openpyxl
    import toan_ven as tv
    cs, con = _cs()
    try:
        hd = cs.tim_hd(con, ref)
        v.tien_do(0.05, "Lớp 1 — đọc cấu trúc file và công thức…")
        kt = tv.KiemTra(path).chay()
        ph1, bang_k, cay, dich = _lop1(kt, Path(path).name)
        v.tien_do(0.45, "Lớp 2 — đối chiếu BOQ, đơn giá và phụ lục hiệu lực tại ngày nghiệm thu…")
        wv = openpyxl.load_workbook(path, data_only=True)
        k = cs.tinh_doi_chieu_dot(con, ref, path, ngay_nt, dot, wv=wv)
        ph2, ngay = _lop2(k)
        ph_gt, bang_l2, doi_chieu_hm = bang_kiem_lop2(k, ph2, cs, con)
        ph2 += ph_gt
        for i, f in enumerate(ph_gt, 1):
            f["id"] = f"GT-{len([x for x in ph2 if x['code'] == 'GT']) - len(ph_gt) + i:02d}"
        for h in bang_l2:
            if isinstance(h["finding"], dict):
                h["finding"] = h["finding"]["id"]
        ph2 += _lop2b(kt, k, cs, con, bang=bang_l2)
        v.tien_do(0.80, "Ghi báo cáo Excel…")
        out_dir = _thu_muc_kq("kiem_tra_dot")
        out = cs.kiem_dot(con, ref, path, ngay_nt, str(out_dir / f"{v.id}_lop2.xlsx"), dot)[0]
        out1 = out_dir / f"{v.id}_lop1.xlsx"
        tv.ghi(kt, out1)
        tong = k["tong"]
        de_nghi = (tong.get("tt_ky_nay") or {}).get("gia_tri")
        if de_nghi is None:
            de_nghi = next((r["gia_tri"] for r in cay if r["cap"] == 0), None)
        ph = ph2 + ph1
        thu_tu = {"Cao": 0, "Trung bình": 1, "Thấp": 2}
        ph.sort(key=lambda f: (thu_tu.get(f["level"], 3), f["layer"]))
        anh_huong = sum(f["amount"] for f in ph if f["layer"] == 2 and isinstance(f["amount"], (int, float))
                        and f["code"] != "GT")
        d = {"ma": v.id, "loai": "kiem_tra_dot", "tep": Path(path).name, "duong_dan_tep": str(path), "luc": _bay_gio(),
             "hop_dong": {"ma_hd": hd["ma_hd"], "so_hd": hd["so_hd"], "phan_loai": hd["phan_loai"]},
             "ben_b": (con.execute("SELECT gia_tri FROM tham_so WHERE ma_hd = ? AND ma_ts = 'TC-07'", (hd["ma_hd"],))
                       .fetchone() or [""])[0],
             "dot": k["dot"], "dot_truoc": k["dot_truoc"], "ngay_nghiem_thu": ngay, "gt_hieu_luc": k["gt_hl"],
             "loai_gia": k["loai"], "vat": k["vat"],
             "phu_luc_ap_dung": [{"so_pl": p["so_pl"], "ngay_hieu_luc": p["ngay_hieu_luc"]} for p in k["pls"]],
             "phu_luc_chua_ap_dung": [{"so_pl": p["so_pl"], "ngay_hieu_luc": p["ngay_hieu_luc"], "trang_thai": p["trang_thai"]}
                                      for p in k["con_lai"]],
             "de_nghi": de_nghi, "o_de_nghi": (tong.get("tt_ky_nay") or {}).get("o") or dich, "anh_huong": anh_huong,
             "tong_hop": {kk: vv for kk, vv in tong.items()}, "bang_chi_tiet": k["bang"]["sheet"],
             "so_hang_muc": sum(1 for x in k["rows"]), "phat_hien": ph, "bang_k": bang_k, "cay": cay,
             "bang_lop2": bang_l2, "doi_chieu_hm": doi_chieu_hm,
             "dem": dict(Counter(f["level"] for f in ph)), "so_phat_hien": len(ph),
             "dem_lop": {"1": len(ph1), "2": len(ph2)}, "da_nap": False,
             "tai": {"lop2": duong_dan_tai(out) if duong_dan_tai else "", "lop1": duong_dan_tai(out1) if duong_dan_tai else ""}}
        _luu("kiem_tra_dot", v.id, _json(d))
        return _json(d)
    finally:
        con.close()


def nap_dot(ma_kq, dot, ngay_hs=None, ly_do="", ghi_chu=""):
    """Nạp đợt đã duyệt. ly_do CHỈ dùng khi cố ý nạp lại (thay) một đợt đã có; ghi_chu = ghi chú duyệt (ghi nhật ký)."""
    d = doc_ket_qua_kiem_tra("kiem_tra_dot", ma_kq)
    if d.get("da_nap"):
        raise ValueError("Đợt này đã được nạp vào CSDL")
    if not dot:
        dot = d.get("dot")
    if not dot:
        raise ValueError("Chưa có số đợt")
    cs, con = _cs()
    try:
        cu = con.execute("SELECT file_nguon FROM dot_thanh_toan WHERE ma_hd = ? AND dot = ?",
                         (d["hop_dong"]["ma_hd"], int(dot))).fetchone()
        if cu and not (ly_do or "").strip():      # báo ngay, khỏi đọc lại file Excel (chậm)
            raise SystemExit(f"Đợt {dot} đã có trong CSDL (nguồn: {(cu[0] or '')[:160]}).")
        ok, miss = cs.nap_dot(con, d["hop_dong"]["ma_hd"], d["duong_dan_tep"], int(dot), d["ngay_nghiem_thu"], ngay_hs,
                              ly_do)
        if ghi_chu or d.get("so_phat_hien"):
            cs.ghi_nhat_ky(con, "Duyệt đợt", d["hop_dong"]["ma_hd"],
                           f"Đợt {dot} ({d.get('tep')}): {d.get('so_phat_hien', 0)} phát hiện khi kiểm tra; ghi chú duyệt: "
                           f"{ghi_chu or '(không)'}" + (f"; nạp lại thay đợt cũ: {ly_do}" if ly_do else ""))
            con.commit()
    finally:
        con.close()
    d["da_nap"] = {"luc": _bay_gio(), "dot": int(dot), "so_hang_muc": ok, "khong_khop": len(miss), "ghi_chu": ghi_chu,
                   "nap_lai": ly_do}
    _luu("kiem_tra_dot", ma_kq, d)
    return _json({"ok": True, "so_hang_muc": ok, "khong_khop": miss[:50]})


def ghep_hang_muc(ma_kq, dong, ma_hm):
    """Ghép tay một dòng hồ sơ thanh toán với một Mã HM của BOQ (bảng khop_hang_muc). Máy dùng lại cho lần chạy lại và các
    đợt sau của cùng hợp đồng. Đổi ghép đã có → ghi nhật ký chế độ sửa."""
    d = doc_ket_qua_kiem_tra("kiem_tra_dot", ma_kq)
    row = next((h for h in d.get("doi_chieu_hm") or [] if str(h.get("dong")) == str(dong)), None)
    if not row:
        raise ValueError(f"Không có dòng {dong} trong kết quả kiểm tra này")
    if not row.get("khoa"):
        raise ValueError("Kết quả này chạy bằng bản cũ (chưa có khoá dòng) — bấm Chạy lại trước khi ghép tay")
    ma_hm = str(ma_hm or "").strip().upper()
    ma_hd = d["hop_dong"]["ma_hd"]
    cs, con = _cs()
    try:
        b = con.execute("SELECT ten, dvt FROM boq_dong WHERE ma_hd = ? AND ma_hm = ? ORDER BY id DESC", (ma_hd, ma_hm)).fetchone()
        if not b:
            raise ValueError(f"{ma_hm or '(trống)'} không có trong BOQ của {ma_hd}")
        cu = con.execute("SELECT ma_hm FROM khop_hang_muc WHERE ma_hd = ? AND khoa_hstt = ?", (ma_hd, row["khoa"])).fetchone()
        mo_ta = f"dòng {dong} '{row['ten'][:60]}' → {ma_hm} ({b['ten'][:60]}, {b['dvt']}) · {d.get('tep', '')}"
        if cu and cu[0] == ma_hm:
            pass
        elif cu:
            with cs.che_do_sua(con, f"Ghép tay lại {mo_ta} (trước: {cu[0]})", ma_hd):
                con.execute("UPDATE khop_hang_muc SET ma_hm = ?, cach_khop = 'ghép tay', nguoi_xac_nhan = ?, ngay = ? "
                            "WHERE ma_hd = ? AND khoa_hstt = ?", (ma_hm, cs._nguoi(), cs.bay_gio(), ma_hd, row["khoa"]))
        else:
            con.execute("INSERT INTO khop_hang_muc VALUES (?,?,?,?,?,?)",
                        (ma_hd, row["khoa"], ma_hm, "ghép tay", cs._nguoi(), cs.bay_gio()))
        cs.ghi_nhat_ky(con, "Ghép tay hạng mục", ma_hd, mo_ta)
        con.commit()
    finally:
        con.close()
    row["ghep_tay"] = ma_hm
    d["ghep_moi"] = sorted(set(d.get("ghep_moi") or []) | {str(dong)})
    _luu("kiem_tra_dot", ma_kq, d)
    return _json({"ok": True, "dong": dong, "ma_hm": ma_hm, "ten_boq": b["ten"], "so_ghep_moi": len(d["ghep_moi"])})


# ================================================================== TỔNG QUAN
def viec_gan_day(ds_luot, gioi_han=12):
    out = []
    for l in ds_luot:
        if not l.get("bat_dau"):
            continue
        tt = l.get("tt")
        kind = "danger" if tt == "loi" else ("warning" if l.get("so_vang") else ("info" if tt == "dang_chay" else "success"))
        out.append({"t": l["bat_dau"], "loai": "trich_xuat", "ten": f"Trích {l['so_hd']} hợp đồng",
                    "phu": "; ".join(x for x in l.get("hop_dong", [])[:2] if x),
                    "ket_qua": {"loi": "Lỗi", "dang_chay": "Đang chạy", "da_dung": "Đã dừng"}.get(tt) or
                               ("Có ô cần xem" if l.get("so_vang") else "Xong"),
                    "kind": kind, "ghi_chu": f"{l.get('so_vang', 0)} ô cần xác nhận" if l.get("so_vang") else
                    f"{l.get('so_xong', 0)}/{l.get('so_hd', 0)} hợp đồng", "route": "extraction", "ma": l["luot"]})
    for loai, route in (("kiem_tra_dot", "payments"), ("toan_ven", "integrity")):
        for d in ds_ket_qua_kiem_tra(loai, 10):
            cao = (d.get("dem") or {}).get("Cao", 0)
            t = datetime.datetime.fromisoformat(d["luc"]).timestamp() if d.get("luc") else 0
            hd = d.get("hop_dong") or {}
            out.append({"t": t, "loai": loai,
                        "ten": (f"Kiểm tra đợt {d.get('dot') or ''}".strip() if loai == "kiem_tra_dot" else "Kiểm tra toàn vẹn file (HĐ chưa có trong CSDL)"),
                        "phu": (f"{hd.get('ma_hd', '')} · {d.get('tep', '')}" if hd else d.get("tep", "")),
                        "ket_qua": "Có cảnh báo" if d.get("so_phat_hien") else "Xong",
                        "kind": "warning" if d.get("so_phat_hien") else "success",
                        "ghi_chu": f"{d.get('so_phat_hien', 0)} phát hiện" + (f", {cao} mức cao" if cao else ""),
                        "route": route, "ma": d["ma"]})
    if ch.file_csdl().exists():
        cs, con = _cs()
        try:
            for r in con.execute("SELECT * FROM nhat_ky WHERE thao_tac IN ('Nạp phụ lục','Huỷ phụ lục','Nhập BOQ gốc',"
                                 "'Nạp từ trích xuất AI','Nạp master','Nạp đợt') ORDER BY id DESC LIMIT 15"):
                try:
                    t = datetime.datetime.strptime(r["thoi_diem"], "%Y-%m-%d %H:%M:%S").timestamp()
                except (TypeError, ValueError):
                    continue
                route = {"Nạp phụ lục": "appendices", "Huỷ phụ lục": "appendices", "Nhập BOQ gốc": "boq"}.get(
                    r["thao_tac"], "contracts")
                out.append({"t": t, "loai": "csdl", "ten": r["thao_tac"], "phu": r["ma_hd"] or "",
                            "ket_qua": "Xong", "kind": "success", "ghi_chu": (r["chi_tiet"] or "")[:90], "route": route,
                            "ma": r["ma_hd"]})
        finally:
            con.close()
    out.sort(key=lambda x: -x["t"])
    return out[:gioi_han]


def can_xem_xet():
    """Khối 'Cần Anh xem xét' trên Tổng quan."""
    out = []
    kq = ds_ket_qua_kiem_tra("kiem_tra_dot", 5)
    for d in kq:
        if d.get("da_nap"):
            continue
        cao = (d.get("dem") or {}).get("Cao", 0)
        if cao:
            hd = d.get("hop_dong") or {}
            out.append({"loai": "dot", "tieu_de": f"{cao} phát hiện mức cao trong hồ sơ đợt {d.get('dot') or ''}".strip(),
                        "noi_dung": f"{hd.get('ma_hd', '')} · {d.get('tep', '')}", "anh_huong": d.get("anh_huong"),
                        "route": "payments", "ma": d["ma"], "nut": "Xem phát hiện"})
    if ch.file_csdl().exists():
        cs, con = _cs()
        try:
            for r in con.execute("SELECT c.*, p.so_pl FROM canh_bao c LEFT JOIN phu_luc p ON p.id = c.pl_id "
                                 "WHERE c.muc_do IN ('ĐỎ','CHẶN') ORDER BY c.id DESC LIMIT 4"):
                out.append({"loai": "canh_bao", "tieu_de": f"{r['so_pl'] or r['ma_kt']} có cờ đỏ" if r["so_pl"] else
                            f"Cờ đỏ {r['ma_kt']}", "noi_dung": f"{r['ma_hd']} · {r['noi_dung'][:120]}",
                            "route": "appendices" if r["so_pl"] else "contracts", "ma": r["ma_hd"], "nut": "Xem"})
            for r in con.execute("SELECT ma_hd, COUNT(*) n FROM tham_so_nguon WHERE da_xac_nhan = 0 AND "
                                 "(kiem_tra IS NULL OR kiem_tra NOT LIKE 'OK%') GROUP BY ma_hd ORDER BY n DESC LIMIT 4"):
                out.append({"loai": "tham_so", "tieu_de": f"{r['n']} tham số chưa xác nhận",
                            "noi_dung": f"{r['ma_hd']} · ô vàng đã nạp nhưng chưa xác nhận", "route": "contracts",
                            "ma": r["ma_hd"], "nut": "Mở hợp đồng"})
        finally:
            con.close()
    return out


def tho_gian_epoch(s):
    try:
        return time.mktime(datetime.datetime.fromisoformat(s).timetuple())
    except (TypeError, ValueError):
        return 0
