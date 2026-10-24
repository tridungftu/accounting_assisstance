# -*- coding: utf-8 -*-
"""
xuat.py — Bước 9: ghi kết quả.
  <tên>_KET_QUA.json   nguồn dữ liệu chính (giao diện đọc/sửa file này) — khoá không dấu
  <tên>_KET_QUA.xlsx   sheet Tham_so (cột cũ giữ nguyên thứ tự, thêm Mức · Nguồn · Trạng thái), Phieu_kiem_tra,
                       Doan_lien_quan (khi chưa chạy AI)
  TONG_HOP_<giờ>_<model>.xlsx/.json   mỗi HĐ một dòng
  DANH_MUC_HD\\DANH_MUC_HOP_DONG.xlsx  mẫu MAU_DANH_MUC_HOP_DONG.xlsx, mỗi HĐ một dòng (cập nhật nếu đã có) —
                       nạp vào CSDL bằng: python csdl_hop_dong.py nap-danh-muc <file>
"""
import datetime
import json
import os
import re
import shutil
from decimal import Decimal

from .kiem_tra import la_ok, so_chuan
from .xlsx_mini import write_xlsx

COT = [("Mã", "ma", 8), ("Nhóm", "nhom", 18), ("Tham số", "mo_ta", 40), ("Giá trị", "gia_tri", 38),
       ("Đơn vị", "don_vi", 10), ("Điều khoản", "dieu_khoan", 22), ("Trích dẫn nguyên văn", "trich_dan", 60),
       ("Ghi chú", "ghi_chu", 24), ("Kiểm tra", "kiem_tra", 30), ("Vị trí dò được", "vi_tri_do_duoc", 26),
       ("Mức", "muc", 6), ("Nguồn", "nguon", 22), ("Trạng thái", "trang_thai", 16),
       ("Giá trị máy trích", "gia_tri_ai", 30), ("Ghi chú người soát", "ghi_chu_soat", 30)]
COT_DAP_AN = [("Đáp án", "dap_an", 30), ("So với đáp án", "so_voi_dap_an", 16)]


def chuan_hoa_dong(d):
    """Trạng thái review của một dòng: da_xac_nhan, da_sua, gia_tri_ai, trang_thai (đọc được cả JSON bản cũ)."""
    if "da_xac_nhan" not in d:
        tt = d.get("trang_thai") or "Chưa xác nhận"
        d["da_sua"] = tt == "Đã sửa tay"
        d["da_xac_nhan"] = tt in ("Đã xác nhận", "Đã sửa tay")
    if "gia_tri_ai" not in d:
        cu = [h for h in d.get("lich_su", []) if h.get("thao_tac") == "Sửa tay"]
        d["gia_tri_ai"] = cu[0]["cu"] if cu else d.get("gia_tri", "")
    d["trang_thai"] = (("Đã sửa tay, " + ("đã xác nhận" if d["da_xac_nhan"] else "chưa xác nhận")) if d["da_sua"]
                       else ("Đã xác nhận" if d["da_xac_nhan"] else "Chưa xác nhận"))
    return d


def can_xem(d):
    """Ô cần người soát xem: tự kiểm chưa OK (vàng) và người soát chưa xác nhận."""
    chuan_hoa_dong(d)
    return not la_ok(d.get("kiem_tra")) and not d["da_xac_nhan"]


def tom_tat_review(kq):
    for d in kq["bang"]:
        chuan_hoa_dong(d)
    kq["tom_tat"]["so_can_xem"] = sum(1 for d in kq["bang"] if can_xem(d))
    kq["tom_tat"]["so_da_xac_nhan"] = sum(1 for d in kq["bang"] if d["da_xac_nhan"])
    kq["tom_tat"]["so_vang"] = sum(1 for d in kq["bang"] if not la_ok(d.get("kiem_tra")))
    return kq


# ------------------------------------------------------------------ một hợp đồng
def ten_tep(kq):
    t = kq["ten"]
    tep = {"excel": f"{t}_KET_QUA.xlsx", "json": f"{t}_KET_QUA.json", "cau_truc_xlsx": f"{t}_cau_truc.xlsx",
           "cau_truc_json": f"{t}_cau_truc.json"}
    nk = ((kq.get("tom_tat") or {}).get("cloud") or {}).get("nhat_ky")
    if nk:
        tep["gui_ra_ngoai"] = os.path.basename(nk)
    return tep


def ghi_ket_qua_hd(kq, out):
    kq["tep"] = ten_tep(kq)
    with open(os.path.join(out, kq["tep"]["json"]), "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    ghi_excel_hd(kq, os.path.join(out, kq["tep"]["excel"]))
    return kq["tep"]


def ghi_excel_hd(kq, path):
    for d in kq["bang"]:
        chuan_hoa_dong(d)
    cot = COT + (COT_DAP_AN if any("dap_an" in d for d in kq["bang"]) else [])
    rows = [[c[0] for c in cot]] + [[d.get(k, "") for _, k, _ in cot] for d in kq["bang"]]
    tt = kq["tom_tat"]
    rep = kq.get("phieu_kiem_tra") or {}
    phieu = ([["Chỉ tiêu", "Giá trị"]] + [[k, "; ".join(v) if isinstance(v, list) else v] for k, v in rep.items()]
             + [["model", kq.get("model") or "(chưa chạy AI)"], ["máy AI", kq.get("may_ai") or ""],
                ["rà lại toàn HĐ", "Có" if kq["tuy_chon"].get("ra_lai") else "Không"],
                ["kiểm tra chéo cloud", _mo_ta_cloud(tt.get("cloud") or {})],
                ["số tham số / OK / vàng", f"{tt['so_tham_so']} / {tt['so_ok']} / {tt['so_vang']}"],
                ["token vào / ra", f"{tt['token_vao']:,} / {tt['token_ra']:,}"],
                ["thời gian (giây)", tt["thoi_gian_giay"]], ["lỗi AI", tt["loi_ai"]], ["tạo lúc", kq["tao_luc"]]])
    sheets = {"Tham_so": {"rows": rows, "widths": [c[2] for c in cot]},
              "Phieu_kiem_tra": {"rows": phieu, "widths": [26, 100]}}
    if kq.get("doan_lien_quan"):
        s = [["Mã", "Tham số", "Vị trí", "Nội dung đoạn (tự đọc để lấy giá trị)"]]
        ten = {d["ma"]: d["mo_ta"] for d in kq["bang"]}
        for ma, ds in kq["doan_lien_quan"].items():
            for x in ds:
                s.append([ma, ten.get(ma, ""), x["vi_tri"], x["noi_dung"]])
        sheets["Doan_lien_quan"] = {"rows": s, "widths": [8, 40, 22, 120]}
    ls = [["Lúc", "Mã", "Thao tác", "Giá trị cũ", "Giá trị mới", "Người"]]
    for d in kq["bang"]:
        for h in d.get("lich_su", []):
            ls.append([h.get("luc", ""), d["ma"], h.get("thao_tac", ""), h.get("cu", ""), h.get("moi", ""), h.get("nguoi", "")])
    if len(ls) > 1:
        sheets["Lich_su_soat"] = {"rows": ls, "widths": [20, 8, 16, 40, 40, 16]}
    tmp = path + ".tmp"
    write_xlsx(tmp, sheets)
    os.replace(tmp, path)


def _mo_ta_cloud(c):
    if not c.get("bat"):
        return "Không"
    s = (f"{c.get('nha_cung_cap')}: chọn {c.get('so_o_chon', 0)}, gửi {c.get('so_o_gui', 0)}, xác nhận {c.get('xac_nhan', 0)}, "
         f"sửa {c.get('sua', 0)}, không xác nhận {c.get('khong_xac_nhan', 0)}")
    if c.get("khong_gui"):
        s += " | không gửi: " + "; ".join(c["khong_gui"])
    if c.get("loi"):
        s += " | lỗi: " + c["loi"]
    return s


def doc_ket_qua(json_path):
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def cap_nhat_o(json_path, ma, gia_tri=None, xac_nhan=None, ghi_chu=None, nguoi=""):
    """Người soát sửa giá trị / xác nhận một ô. Sửa giá trị → bỏ xác nhận (phải xác nhận lại); giá trị máy trích
    luôn giữ trong gia_tri_ai. Ghi lịch sử, cập nhật JSON + Excel. Trả dòng sau khi sửa."""
    kq = doc_ket_qua(json_path)
    d = next((x for x in kq["bang"] if x["ma"] == ma), None)
    if d is None:
        raise ValueError(f"Không có tham số {ma}")
    chuan_hoa_dong(d)
    luc = datetime.datetime.now().isoformat(timespec="seconds")
    if gia_tri is not None:
        moi = str(gia_tri).strip()
        if not moi:
            raise ValueError("Giá trị tham số không được để trống")
        if moi != (d.get("gia_tri") or ""):
            d.setdefault("lich_su", []).append({"luc": luc, "thao_tac": "Sửa tay", "cu": d.get("gia_tri", ""),
                                                "moi": moi, "nguoi": nguoi})
            d["gia_tri"] = moi
            d["da_sua"] = moi != (d.get("gia_tri_ai") or "")
            d["da_xac_nhan"] = False
            d.pop("nguoi_xac_nhan", None)
            d.pop("luc_xac_nhan", None)
    if ghi_chu is not None and str(ghi_chu) != d.get("ghi_chu_soat", ""):
        d["ghi_chu_soat"] = str(ghi_chu)
        d.setdefault("lich_su", []).append({"luc": luc, "thao_tac": "Ghi chú", "cu": "", "moi": str(ghi_chu)[:300],
                                            "nguoi": nguoi})
    if xac_nhan is True and not d["da_xac_nhan"]:
        d.update(da_xac_nhan=True, nguoi_xac_nhan=nguoi, luc_xac_nhan=luc)
        d.setdefault("lich_su", []).append({"luc": luc, "thao_tac": "Xác nhận", "cu": "", "moi": d.get("gia_tri", ""),
                                            "nguoi": nguoi})
    elif xac_nhan is False and d["da_xac_nhan"]:
        d["da_xac_nhan"] = False
        d.setdefault("lich_su", []).append({"luc": luc, "thao_tac": "Bỏ xác nhận", "cu": "", "moi": "", "nguoi": nguoi})
    chuan_hoa_dong(d)
    tom_tat_review(kq)
    with open(json_path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    os.replace(json_path + ".tmp", json_path)
    ghi_excel_hd(kq, os.path.join(os.path.dirname(json_path), kq["tep"]["excel"]))
    return d


# ------------------------------------------------------------------ tổng hợp
def ghi_tong_hop(ds_kq, params, out_dir, nhan_luot, model):
    duoi = "_" + re.sub(r"[^A-Za-z0-9.]+", "-", model) if model else "_chua_chay_AI"
    xp = os.path.join(out_dir, f"TONG_HOP_{nhan_luot}{duoi}.xlsx")
    jp = xp[:-5] + ".json"
    head = ["Hợp đồng", "Số OK tự kiểm", "Số ô cần xem", "Đúng so đáp án", "Thời gian (giây)", "Lỗi AI", "Ghi chú"] + \
        [f"{p['ma']} {p['ten']}" for p in params]
    rows, js = [head], []
    for kq in ds_kq:
        if kq.get("loi"):
            rows.append([kq["hop_dong"], "LỖI", "", "", "", "", kq["loi"][:200]])
            js.append({"hop_dong": kq["hop_dong"], "loi": kq["loi"]})
            continue
        tt = kq["tom_tat"]
        vals = {d["ma"]: d["gia_tri"] for d in kq["bang"]}
        rows.append([kq["hop_dong"], f"{tt['so_ok']}/{tt['so_tham_so']}", sum(1 for d in kq["bang"] if can_xem(d)),
                     tt["dung_dap_an"], tt["thoi_gian_giay"], tt["loi_ai"], "Bỏ qua — dùng kết quả cũ" if kq.get("bo_qua") else ""]
                    + [vals.get(p["ma"], "") for p in params])
        js.append({"hop_dong": kq["hop_dong"], "ten": kq["ten"], "tom_tat": tt, "gia_tri": vals})
    write_xlsx(xp, {"Tong_hop": {"rows": rows, "widths": [34, 10, 10, 10, 10, 8, 20] + [26] * len(params)}})
    with open(jp, "w", encoding="utf-8") as f:
        json.dump({"luot": nhan_luot, "model": model, "tham_so": [{"ma": p["ma"], "nhom": p["nhom"], "mo_ta": p["mo_ta"],
                   "muc": p["muc"]} for p in params], "hop_dong": js}, f, ensure_ascii=False, indent=1)
    return xp, jp


# ------------------------------------------------------------------ DANH_MUC_HOP_DONG.xlsx
LOAI_HD = [("EPC (thiết kế – cung cấp – thi công)", ("epc", "thiet ke", "tong thau")),
           ("Cung cấp vật tư, thiết bị", ("cung cap", "vat tu", "thiet bi", "mua ban")),
           ("Tư vấn (thiết kế, giám sát, khảo sát)", ("tu van", "giam sat", "khao sat")),
           ("Thi công xây dựng", ("thi cong", "xay dung", "xay lap", "lap dat")),
           ("Dịch vụ", ("dich vu",)), ("Khác", ("khac",))]
PCT = {"TT-04", "TT-10", "TT-20", "TT-21", "TT-30", "TT-31", "TT-51", "TT-55", "TT-52", "TT-53", "TT-54"}


def _loai_hd(v):
    from .cau_truc import bo_dau
    s = bo_dau((v or "").lower())
    if not s.strip() or s.strip().startswith(("khong quy dinh", "khong tim thay", "khong ap dung")):
        return ""
    for ten, kws in LOAI_HD:
        if any(k in s for k in kws):
            return ten
    return "Khác"


def _ngay(v):
    m = re.search(r"(\d{1,2})\s*(?:/|-|\.|\s*tháng\s*)\s*(\d{1,2})\s*(?:/|-|\.|\s*năm\s*)\s*(\d{4})", v or "")
    if not m:
        return None
    try:
        return datetime.datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _tien(v):
    so = [so_chuan(x) for x in re.findall(r"\d[\d\.,]*\d|\d", v or "")]
    so = [Decimal(x) for x in so if re.fullmatch(r"\d+(\.\d+)?", x)]
    so = [x for x in so if x >= 1000]
    return int(max(so)) if so else None


def _ty_le(v):
    from .logic import ty_le
    t = ty_le(v)
    if len(t) == 1:
        return float(t[0] / 100)
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*", v or "")
    if m:
        return float(Decimal(so_chuan(m.group(1))) / 100)
    return None


def _so_dau(v):
    m = re.search(r"\d+(?:[.,]\d+)?", v or "")
    if not m:
        return None
    d = Decimal(so_chuan(m.group(0)))
    return int(d) if d == int(d) else float(d)


def ghi_danh_muc(ds_kq, path, mau):
    """Cập nhật DANH_MUC_HOP_DONG.xlsx (tạo từ mẫu nếu chưa có). Mỗi HĐ một dòng; HĐ đã có (cùng file nguồn hoặc cùng
    số HĐ) thì ghi đè các ô dữ liệu, giữ cột Ghi chú người soát. Trả (đường dẫn, số dòng mới, số dòng cập nhật)."""
    import openpyxl
    from openpyxl.comments import Comment
    if not os.path.exists(path):
        shutil.copy2(mau, path)
    wb = openpyxl.load_workbook(path)
    ws = wb["DANH_MUC_HD"]
    ma_cot, ten_cot = {}, {}
    for c in range(1, ws.max_column + 1):
        code = str(ws.cell(4, c).value or "").strip()
        ten = str(ws.cell(5, c).value or "").strip()
        ten_cot[ten] = c
        m = re.match(r"((?:TC|TT)-\d+|Y-\d+)", code)
        if m:
            ma_cot[m.group(1)] = c
        elif code.startswith("tách từ"):
            ma_cot["#" + code.split()[-1]] = c
    c_file = ten_cot.get("File hợp đồng nguồn")
    c_model = ten_cot.get("Model AI · ngày trích")
    c_vang = ten_cot.get("Số tham số cần kiểm tra (vàng)")
    c_ghichu = ten_cot.get("Ghi chú người soát")
    c_so = ma_cot.get("TC-01", 3)

    def la_cong_thuc(cell):
        return isinstance(cell.value, str) and cell.value.startswith("=")

    def xoa_dong(r):
        for c in range(2, ws.max_column + 1):
            cell = ws.cell(r, c)
            if not la_cong_thuc(cell):
                cell.value = None
                cell.comment = None

    moi = sua = 0
    for kq in ds_kq:
        if kq.get("loi") or kq.get("che_do") != "AI":
            continue
        vals = {d["ma"]: d for d in kq["bang"]}
        so_hd = (vals.get("TC-01") or {}).get("gia_tri", "").strip()
        dong = None
        for r in range(6, ws.max_row + 1):
            f = str(ws.cell(r, c_file).value or "") if c_file else ""
            s = str(ws.cell(r, c_so).value or "").strip()
            if (f and f == kq["hop_dong"]) or (so_hd and s == so_hd and not s.upper().startswith("VD-")):
                dong = r
                break
        if dong:
            sua += 1
        else:
            for r in range(6, ws.max_row + 2):
                s = str(ws.cell(r, c_so).value or "")
                gc = str(ws.cell(r, c_ghichu).value or "") if c_ghichu else ""
                if s.upper().startswith("VD-") or "VÍ DỤ" in gc.upper():
                    xoa_dong(r)
                    dong = r
                    break
                if not s and not (c_file and ws.cell(r, c_file).value):
                    dong = r
                    break
            moi += 1
        ghi_chu_cu = ws.cell(dong, c_ghichu).value if c_ghichu else None
        xoa_dong(dong)
        if c_ghichu:
            ws.cell(dong, c_ghichu).value = ghi_chu_cu
        for ma, c in ma_cot.items():
            if ma.startswith("#"):
                v = _so_dau((vals.get(ma[1:]) or {}).get("gia_tri", ""))
                ws.cell(dong, c).value = v
                continue
            d = vals.get(ma)
            if not d:
                continue
            v = d.get("gia_tri", "")
            cell = ws.cell(dong, c)
            out = v
            if ma == "TC-02":
                out = _ngay(v) or v
                if isinstance(out, datetime.datetime):
                    cell.number_format = "dd/mm/yyyy"
            elif ma == "TT-02":
                out = _tien(v) or v
                if isinstance(out, int):
                    cell.number_format = "#,##0"
            elif ma in PCT:
                t = _ty_le(v)
                if t is not None:
                    out = t
                    cell.number_format = "0.000%" if ma in ("TT-52", "TT-53", "TT-54") else "0.##%"
            cell.value = out if out != "" else None
            if can_xem(d):
                cell.comment = Comment(f"{d['kiem_tra'][:300]}\nTrích dẫn: {d.get('trich_dan', '')[:300]}", "Trích xuất AI")
        loai = _loai_hd((vals.get("TC-09") or {}).get("gia_tri", ""))
        if loai:
            ws.cell(dong, 2).value = loai
        if c_file:
            ws.cell(dong, c_file).value = kq["hop_dong"]
        if c_model:
            ws.cell(dong, c_model).value = f"{kq.get('model')} · {kq['tao_luc'][8:10]}/{kq['tao_luc'][5:7]}/{kq['tao_luc'][:4]}"
        if c_vang:
            ws.cell(dong, c_vang).value = sum(1 for d in kq["bang"] if can_xem(d))
    tmp = path + ".tmp.xlsx"
    wb.save(tmp)
    os.replace(tmp, path)
    return path, moi, sua
