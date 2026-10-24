# -*- coding: utf-8 -*-
"""
cau_truc.py — Chuyển hợp đồng thành CẤU TRÚC Điều → Khoản → Nội dung (mỗi đơn vị một ID R001…),
và dò VỊ TRÍ của từng tham số theo từ khoá (tiêu đề ×10, "@mo_dau" +20, nội dung ≤5) → 3 vị trí tốt nhất.
Ghi <tên>_cau_truc.json + .xlsx để người soát xem lại.
"""
import json
import os
import re
import unicodedata

KHOAN = re.compile(r"^(\d+(?:\.\d+)+)\.?\s+(.*)$")        # 5.3 / 5.3.1 / 16.2


def build_structure(info):
    rows = []

    def add(dieu, tieu_de_dieu, khoan, tieu_de_khoan, lines):
        body = "\n".join(lines).strip()
        if body or tieu_de_khoan:
            rows.append({"id": f"R{len(rows) + 1:03d}", "dieu": dieu, "tieu_de_dieu": tieu_de_dieu,
                         "khoan": khoan, "tieu_de_khoan": tieu_de_khoan, "noi_dung": body})

    if info.get("chunks"):          # không nhận diện được "Điều N" → mỗi đoạn ~3.000 ký tự là một đơn vị "Đoạn k"
        for k, c in enumerate(info["chunks"], 1):
            rows.append({"id": f"R{k:03d}", "dieu": "0", "tieu_de_dieu": f"Đoạn {k} (tự chia, không nhận diện được Điều)",
                         "khoan": "", "tieu_de_khoan": "", "noi_dung": c.strip(), "doan": k})
        return rows
    toc = re.compile(r"^(?:Điều|ĐIỀU)\s+\d+\s*[\.:].*\s\d{1,3}$")
    pre = [ln for ln in info["preamble"].split("\n") if not toc.match(ln.strip())]
    add("0", "Phần mở đầu (trước Điều 1)", "", "", pre)
    for n, art in info["articles"].items():
        lines = art["text"].split("\n")[1:]
        khoan, tieu, buf = "", "", []
        for ln in lines:
            m = KHOAN.match(ln.strip())
            if m and m.group(1).split(".")[0] == str(n):
                add(str(n), art["title"], khoan, tieu, buf)
                khoan, tieu, buf = m.group(1), m.group(2)[:200], []
                if len(m.group(2)) > 200:
                    buf.append(m.group(2))
            else:
                buf.append(ln)
        add(str(n), art["title"], khoan, tieu, buf)
    return rows


def bo_dau(s):
    """Bỏ dấu tiếng Việt: 'Tạm ứng Đợt' → 'Tam ung Dot'."""
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return unicodedata.normalize("NFC", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def _dem(k, text, text_kd, exact_kws=()):
    """Đếm từ khoá k. Từ khoá KHÔNG dấu → so trên bản bỏ dấu; CÓ dấu → so đúng dấu ('phạt' ≠ 'phát'),
    trừ khi đoạn HĐ viết không dấu. exact_kws: từ khoá không dấu có đúng nguyên dạng trong HĐ (vat, gtgt) → so chính xác."""
    if k in exact_kws:
        return text.count(k)
    if k == bo_dau(k) or text == text_kd:
        return text_kd.count(bo_dau(k))
    return text.count(k)


def vi_tri(r):
    """Nhãn ngắn: 'Điều 5 – Khoản 5.3' / 'Phần mở đầu' / 'Đoạn 3'."""
    if r.get("doan"):
        return f"Đoạn {r['doan']}"
    if r["dieu"] == "0":
        return "Phần mở đầu"
    return "Điều " + r["dieu"] + (f" – Khoản {r['khoan']}" if r["khoan"] else "")


def nhan(r):
    """Nhãn đầy đủ (kèm tiêu đề) dùng trong prompt: [Điều 5 – Khoản 5.3: Tạm ứng]."""
    if r["dieu"] == "0":
        return vi_tri(r)
    t = r["tieu_de_khoan"] or r["tieu_de_dieu"]
    return f"{vi_tri(r)}: {t}"[:160]


def than(r):
    """Nội dung một đơn vị (kèm tiêu đề Khoản nếu có)."""
    return (r["tieu_de_khoan"] + "\n" + r["noi_dung"]).strip() if r["tieu_de_khoan"] else r["noi_dung"]


def locate(rows, params, khong_dau=True):
    """Chấm điểm từng đơn vị theo từ khoá của mỗi tham số → 3 vị trí tốt nhất.
    Tham số không có từ khoá (hoặc không khớp) → row_ids rỗng → bước sau cho AI tự tìm qua mục lục."""
    texts = []
    for r in rows:
        title = (r["tieu_de_dieu"] + " | " + r["tieu_de_khoan"]).lower()
        body = r["noi_dung"].lower()
        texts.append((r, title, body, bo_dau(title) if khong_dau else title, bo_dau(body) if khong_dau else body))
    all_kws = {k for p in params for k in p["tieu_de_kws"] + p["noi_dung_kws"]}
    exact = ({k for k in all_kws if k == bo_dau(k) and any(k in t or k in b for _, t, b, _, _ in texts)}
             if khong_dau else all_kws)
    out = []
    for p in params:
        title_kws, body_kws = p["tieu_de_kws"], p["noi_dung_kws"]
        scored = []
        if body_kws or title_kws:
            for r, title, body, title_kd, body_kd in texts:
                s = 0
                if "@mo_dau" in title_kws and r["dieu"] == "0" and r.get("doan", 1) == 1:
                    s += 20
                s += 10 * sum(1 for k in title_kws if not k.startswith("@") and _dem(k, title, title_kd, exact))
                kws = body_kws or [k for k in title_kws if not k.startswith("@")]
                hits = sum(_dem(k, body, body_kd, exact) + _dem(k, title, title_kd, exact) for k in kws)
                if hits == 0 and not s:
                    continue
                scored.append((s + min(hits, 5), r))
        scored.sort(key=lambda x: -x[0])
        top = [r for _, r in scored[:3]]
        out.append({"ma": p["ma"], "nhom": p["nhom"], "tham_so": p["ten"],
                    "tu_khoa": "tiêu đề: " + ", ".join(title_kws) + " | nội dung: " + ", ".join(body_kws),
                    "vi_tri": [vi_tri(r) for r in top], "row_ids": [r["id"] for r in top]})
    return out


def save(base, info, rows, loc):
    """Ghi <base>_cau_truc.json và <base>_cau_truc.xlsx. base = đường dẫn không đuôi."""
    from .xlsx_mini import write_xlsx
    base = base + "_cau_truc"
    data = {"file": info["report"]["file"], "phieu_kiem_tra": info["report"], "cau_truc": rows, "vi_tri_tham_so": loc}
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    s1 = [["ID", "Điều", "Tiêu đề Điều", "Khoản", "Tiêu đề Khoản / Mục", "Nội dung", "Số ký tự"]]
    s1 += [[r["id"], int(r["dieu"]), r["tieu_de_dieu"], r["khoan"], r["tieu_de_khoan"], r["noi_dung"], len(r["noi_dung"])]
           for r in rows]
    s2 = [["Mã", "Nhóm", "Tham số", "Vị trí 1", "Vị trí 2", "Vị trí 3", "ID dòng", "Từ khoá dò"]]
    for x in loc:
        v = (x["vi_tri"] + ["", "", ""])[:3]
        s2.append([x["ma"], x["nhom"], x["tham_so"], *v, ", ".join(x["row_ids"]), x["tu_khoa"]])
    s3 = [["Chỉ tiêu", "Giá trị"]] + [[k, "; ".join(v) if isinstance(v, list) else v] for k, v in info["report"].items()]
    write_xlsx(base + ".xlsx", {"Cau_truc": {"rows": s1, "widths": [7, 6, 40, 9, 45, 110, 9]},
                                "Vi_tri_tham_so": {"rows": s2, "widths": [8, 20, 38, 22, 22, 22, 18, 50]},
                                "Phieu_kiem_tra": {"rows": s3, "widths": [24, 90]}})
    return base + ".json", base + ".xlsx"
