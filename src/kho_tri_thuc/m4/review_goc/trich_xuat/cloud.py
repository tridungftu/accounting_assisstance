# -*- coding: utf-8 -*-
"""
cloud.py — Bước 8 (TUỲ CHỌN, mặc định TẮT): kiểm tra chéo một số ô trên cloud (Anthropic Claude / OpenAI).

Chọn ô gửi:  ô VÀNG mức quan trọng 2–3 + ô OK lấy ngẫu nhiên (mức 3: x%, mức 2: x/2%; x = tỷ lệ cài đặt, mặc định 20).
             KHÔNG gửi nhóm Thông tin chung, KHÔNG gửi Phần mở đầu; chỉ gửi các Khoản liên quan của ô đó.
Che thông tin: tên các Bên, dự án, gói thầu, địa điểm, số HĐ, MST, số tài khoản, điện thoại, email, tên người, tên công ty
             → [BEN_A], [DU_AN], [MST]… Số tiền và tỷ lệ GIỮ NGUYÊN. Che xong vẫn còn dấu vết định danh → KHÔNG gửi ô đó.
Nhật ký:     mọi nội dung gửi đi + trả về ghi vào GUI_RA_NGOAI_<giờ>.txt (không ghi khoá API).
Kết quả:     Python kiểm lại trích dẫn cloud trên văn bản gốc. Cột "Nguồn":
             Local | Local – cloud xác nhận | Local – cloud xác nhận (theo trích dẫn của Claude) |
             Local – cloud cùng: không quy định | Cloud sửa (local: …) | Local – cloud không xác nhận được
"""
import datetime
import json
import os
import random
import re
import urllib.error
import urllib.request

from .ai_local import SCHEMA_TRICH, SYSTEM, parse_json
from .cau_hinh import CLOUD_MODEL_MAC_DINH, doc_khoa
from .cau_truc import nhan, than
from .kiem_tra import check, gan_dieu_khoan, giong_nhau, la_khong_co, la_ok, norm

GROUP_MAX = 8
URL = {"anthropic": "https://api.anthropic.com/v1/messages", "openai": "https://api.openai.com/v1/chat/completions"}
CHO_NOI_MASK_V2 = "CHO_NOI_MASK_V2"
CLOUD_TAM_KHOA = CHO_NOI_MASK_V2 + ": Đường Cloud tạm khóa: chờ nối qua Mask file v2"


class CloudLoi(Exception):
    pass


# ------------------------------------------------------------------ chọn ô
def chon_o(ket_qua_bang, ty_le=20, rng=None, luon=()):
    """ket_qua_bang: list dòng (ma, nhom, muc, kiem_tra…). luon: mã tham số "Luôn hỏi Claude".
    Trả [(mã, lý do chọn)]. Không bao giờ chọn nhóm Thông tin chung."""
    rng = rng or random.Random()
    out = []
    for d in ket_qua_bang:
        ma, muc = d["ma"], int(d.get("muc") or 0)
        if ma.startswith("TC-") or (d.get("nhom") or "").lower().startswith("thông tin chung"):
            continue
        if ma in luon:
            out.append((ma, "tham số khó — luôn hỏi Claude"))
            continue
        if muc < 2:
            continue
        if not la_ok(d.get("kiem_tra")):
            out.append((ma, "ô vàng"))
        elif rng.random() * 100 < (ty_le if muc >= 3 else ty_le / 2):
            out.append((ma, f"lấy mẫu ngẫu nhiên mức {muc}"))
    return out


# ------------------------------------------------------------------ che thông tin định danh
_HOA = "A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
_TU_HOA = rf"[{_HOA}][^\s,.;:()\[\]]*"
MAU = [  # (nhãn, regex, nhóm cần che: 0 = cả cụm, 1 = phần sau từ khoá)
    ("MST", re.compile(r"((?:mã số thuế|mã số doanh nghiệp|\bMST\b|\bMSDN\b)\s*(?:là|:)?\s*)([\d][\d\s.\-]{7,}\d)", re.I), 2),
    ("SO_TK", re.compile(r"((?:số tài khoản|tài khoản số|tài khoản|\bSTK\b|\bTK số\b|\bTK\b)\s*(?:là|:)?\s*)"
                         r"([\d][\d\s.\-]{5,}\d)", re.I), 2),
    ("SDT", re.compile(r"((?:điện thoại|\bĐT\b|\bĐTDĐ\b|di động|\btel\b|\bfax\b|hotline)\s*(?:là|:)?\s*)"
                       r"(\+?[\d][\d\s.\-()]{7,}\d)", re.I), 2),
    ("SDT", re.compile(r"(?<![\d.,])(0\d{2,3}[\s.]?\d{3}[\s.]?\d{3,4})(?![\d.,])"), 1),
    ("EMAIL", re.compile(r"([\w.+-]+@[\w-]+(?:\.[\w-]+)+)"), 1),
    ("SO_HD", re.compile(r"(\b\d{1,6}/\d{2,4}/[\w\-/.]*[A-ZĐa-zđ][\w\-/.]*)"), 1),
    ("SO_HD", re.compile(r"((?:hợp đồng|HĐ)\s*(?:số|so)\s*:?\s*)([\w\-/.]*\d[\w\-/.]*)", re.I), 2),
    ("CONG_TY", re.compile(r"\b((?:[A-Z][A-Z0-9&.'\-]*\s+){1,8}(?:CO\.?,?\s*LTD\.?|COMPANY\s+LIMITED|CORPORATION|CORP\.|"
                           r"JOINT\s+STOCK\s+COMPANY|JSC|INC\.|LIMITED|LLC|GMBH|PTE\.?\s*LTD\.?))"), 1),
    ("TEN_NGUOI", re.compile(rf"((?:Ông|Bà|Ông/Bà|Ông \(Bà\)|Mr\.?|Ms\.?)\s+)({_TU_HOA}(?:\s+{_TU_HOA}){{1,4}})"), 2),
]
_CONG_TY = re.compile(r"\b(Công ty|CÔNG TY|Tổng công ty|TỔNG CÔNG TY|Tập đoàn|TẬP ĐOÀN|Chi nhánh|CHI NHÁNH|Liên danh|LIÊN DANH)\s+")
_NOI = {"cổ", "phần", "trách", "nhiệm", "hữu", "hạn", "một", "thành", "viên", "và", "xây", "dựng", "đầu", "tư", "thương",
        "mại", "dịch", "vụ", "phát", "triển", "kỹ", "thuật", "công", "nghệ", "sản", "xuất", "tư", "vấn", "thiết", "kế",
        "môi", "trường", "cơ", "khí", "điện", "nước", "hạ", "tầng", "giao", "thông", "kinh", "doanh", "-", "&"}


def tim_cong_ty(text):
    """Các cụm tên công ty (Công ty + chuỗi từ viết hoa / từ nối loại hình) → list (đầu, cuối)."""
    out = []
    for m in _CONG_TY.finditer(text or ""):
        i, end, co_hoa, n = m.end(), m.end(), False, 0
        for t in re.finditer(r"\S+", text[m.end():m.end() + 200]):
            if t.start() + m.end() - end > 1:      # chỉ cách nhau 1 dấu cách
                break
            w = t.group(0)
            core = w.rstrip(",.;:)")
            if not core:
                break
            if re.match(rf"[{_HOA}0-9]", core) or core.lower() in _NOI or core.isupper():
                if re.match(rf"[{_HOA}]", core) and core not in ("Bên",):
                    co_hoa = True
                end = m.end() + t.start() + len(core)
                n += 1
                if core != w or n >= 15:
                    break
            else:
                break
        if co_hoa:
            out.append((m.start(), end))
    return out


class AnDanh:
    """Che thông tin định danh nhất quán trong một hợp đồng; nhớ bảng tra để mở lại khi nhận kết quả."""

    def __init__(self, thong_tin):
        # thong_tin: {nhãn: [chuỗi cần che]} — lấy từ kết quả local TC-01, TC-03…TC-07
        self.bang = {}          # placeholder → chuỗi gốc
        self.dem = {}
        self.cu_the = []        # (chuỗi gốc, placeholder) — che trước, dài trước
        for lab, vals in thong_tin.items():
            for v in vals:
                v = (v or "").strip()
                if len(v) >= 4 and not v.lower().startswith(("không", "theo ")):
                    self.cu_the.append((v, self._ph(lab, v)))
        self.cu_the.sort(key=lambda x: -len(x[0]))

    def _ph(self, lab, goc):
        for k, v in self.bang.items():
            if norm(v) == norm(goc) and k.startswith("[" + lab):
                return k
        self.dem[lab] = self.dem.get(lab, 0) + 1
        ph = f"[{lab}]" if lab in ("BEN_A", "BEN_B", "DU_AN", "GOI_THAU", "DIA_DIEM") and self.dem[lab] == 1 \
            else f"[{lab}_{self.dem[lab]}]"
        self.bang[ph] = goc
        return ph

    # placeholder được "bọc" bằng ký tự riêng (không phải chữ/số) trong lúc che, để các mẫu regex không che lồng vào nhau
    def _boc(self, ph):
        i = list(self.bang).index(ph)
        return "\ue000" + chr(0xE100 + i) + "\ue001"

    def _mo_boc(self, s):
        keys = list(self.bang)
        return re.sub("\ue000(.)\ue001", lambda m: keys[ord(m.group(1)) - 0xE100], s)

    def _boc_san(self, s):
        for ph in sorted(self.bang, key=len, reverse=True):
            s = s.replace(ph, self._boc(ph))
        return s

    def che(self, text):
        s = text or ""
        for goc, ph in self.cu_the:
            pat = re.escape(goc).replace(r"\ ", r"\s+")
            s = re.sub(pat, lambda m, ph=ph: self._boc(ph), s, flags=re.I)
        for lab, rx, grp in MAU:
            def rep(m, lab=lab, grp=grp):
                if grp == 2:
                    return m.group(1) + self._boc(self._ph(lab, m.group(2)))
                return self._boc(self._ph(lab, m.group(1)))
            s = rx.sub(rep, s)
        for a, b in reversed(tim_cong_ty(s)):
            s = s[:a] + self._boc(self._ph("CONG_TY", s[a:b].strip())) + s[b:]
        return self._mo_boc(s)

    def dau_vet(self, masked):
        """Thông tin định danh còn sót sau khi che (đã biết hoặc theo mẫu) → list mô tả; rỗng = an toàn."""
        con = []
        nm = norm(masked)
        for goc, ph in self.cu_the:
            if norm(goc) in nm:
                con.append(f"{ph} còn trong văn bản")
        sb = self._boc_san(masked)
        for lab, rx, grp in MAU:
            for m in rx.finditer(sb):
                con.append(f"{lab}: {m.group(grp if grp == 2 else 1)[:3]}…")
        for a, b in tim_cong_ty(sb):
            con.append(f"CONG_TY: {sb[a:a + 10]}…")
        return con

    def mo(self, s):
        for ph, goc in sorted(self.bang.items(), key=lambda x: -len(x[0])):
            s = (s or "").replace(ph, goc)
        return s


def thong_tin_dinh_danh(ket_qua):
    g = lambda ma: (ket_qua.get(ma) or {}).get("gia_tri") or ""  # noqa: E731
    return {"SO_HD": [g("TC-01")], "GOI_THAU": [g("TC-03")], "DU_AN": [g("TC-04")], "DIA_DIEM": [g("TC-05")],
            "BEN_A": [g("TC-06")], "BEN_B": [g("TC-07")]}


# ------------------------------------------------------------------ gọi API
def goi_api(nha_cung_cap, model, khoa, prompt, timeout=180, system=None, max_tokens=4096):
    # AI-0 25/10/2026 (TL 48): chặn cả lời gọi trực tiếp, không phụ thuộc cấu hình/env.
    raise CloudLoi(CLOUD_TAM_KHOA)

    ncc = nha_cung_cap.lower()
    model = model or CLOUD_MODEL_MAC_DINH.get(ncc, "")
    url = os.environ.get(f"HD_CLOUD_URL_{ncc.upper()}") or URL.get(ncc)
    if not url:
        raise CloudLoi(f"Nhà cung cấp không hỗ trợ: {nha_cung_cap}")
    if ncc == "anthropic":
        # Không gửi "temperature": các model Claude mới (Opus 5.5, Sonnet 5…) báo lỗi 400 "temperature is deprecated".
        body = {"model": model, "max_tokens": max_tokens, "system": system or SYSTEM,
                "messages": [{"role": "user", "content": prompt}]}
        headers = {"x-api-key": khoa, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    else:
        body = {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system or SYSTEM}, {"role": "user", "content": prompt}]}
        headers = {"Authorization": f"Bearer {khoa}", "Content-Type": "application/json"}
    d = None
    for lan in range(2):
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            try:
                msg = e.read().decode("utf-8", "replace")[:300]
            except Exception:  # noqa: BLE001
                msg = ""
            # model không nhận temperature / response_format → bỏ tham số đó, hỏi lại đúng 1 lần
            bo = [k for k in ("temperature", "response_format") if k in body and k in msg]
            if e.code == 400 and lan == 0 and bo:
                for k in bo:
                    body.pop(k)
                continue
            raise CloudLoi(f"{ncc} báo lỗi HTTP {e.code}: {msg}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CloudLoi(f"Không kết nối được {ncc}: {type(e).__name__}") from None
    if ncc == "anthropic":
        txt = "".join(c.get("text", "") for c in d.get("content", []) if c.get("type") == "text")
        use = d.get("usage", {})
        return txt, use.get("input_tokens", 0), use.get("output_tokens", 0), model
    txt = ((d.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    use = d.get("usage", {})
    return txt, use.get("prompt_tokens", 0), use.get("completion_tokens", 0), model


def _prompt(params, blocks):
    ds = "\n".join(f"- {p['ma']} | {p['mo_ta']}" for p in params)
    schema = json.dumps(SCHEMA_TRICH, ensure_ascii=False)
    return (f"Trích các tham số sau từ các đoạn hợp đồng bên dưới. Một số thông tin định danh đã được thay bằng nhãn "
            f"trong ngoặc vuông như [BEN_A], [SO_HD_1] — giữ nguyên các nhãn đó khi trích dẫn.\n\nTHAM SỐ:\n{ds}\n\n"
            "QUY TẮC:\n- Mỗi tham số một phần tử trong 'ket_qua', giữ đúng mã.\n"
            "- gia_tri: ngắn gọn, giữ nguyên số liệu như trong hợp đồng. HĐ ghi 'Không áp dụng' thì ghi 'Không áp dụng'. "
            "Không có thông tin thì ghi 'Không quy định'.\n- don_vi: đồng, %, ngày, tháng, bộ, %/ngày… (trống nếu không có).\n"
            "- dieu_khoan: nhãn trong ngoặc vuông của đoạn chứa thông tin.\n"
            "- trich_dan: chép NGUYÊN VĂN một câu ngắn trong hợp đồng chứa giá trị, không sửa chữ nào.\n"
            "- ghi_chu: ghi 'Suy ra' nếu giá trị được tính ra chứ không ghi trực tiếp.\n\n"
            f"Trả về DUY NHẤT một JSON theo schema: {schema}\n\nCÁC ĐOẠN HỢP ĐỒNG:\n\n" + "\n\n".join(blocks))


# ------------------------------------------------------------------ bước 8
def kiem_tra_cloud(bang, params, ket_qua, sent, rows_by_id, full_norm, full_loose, out_dir, cfg, ghi_log=None,
                   rng=None, dung=None, max_chars=14000, ung_vien=None):
    """bang: list dòng kết quả (sẽ được SỬA: gia_tri, trich_dan, kiem_tra, nguon…).
    sent: {mã: [rows đã gửi local AI]}; ung_vien: {mã: [rows ứng viên tìm được khi rà lại toàn HĐ]} — gửi kèm để
    Claude không phải đọc lại đúng chỗ local có thể đã đọc sai. cfg: {nha_cung_cap, model, ty_le}. Trả dict tóm tắt."""
    # AI-0: bỏ qua bước 8 trước khi đọc khóa, che dữ liệu hoặc ghi nhật ký gửi ra ngoài.
    if ghi_log is not None:
        ghi_log("Bỏ qua kiểm tra chéo cloud: " + CLOUD_TAM_KHOA)
    return {"bat": False, "nha_cung_cap": cfg.get("nha_cung_cap") or "anthropic", "model": cfg.get("model") or "",
            "so_o_chon": 0, "so_o_gui": 0, "khong_gui": [], "xac_nhan": 0, "sua": 0, "cung_khong_quy_dinh": 0,
            "khong_xac_nhan": 0, "ma_loi": CHO_NOI_MASK_V2, "loi": CLOUD_TAM_KHOA, "nhat_ky": "",
            "token_vao": 0, "token_ra": 0}

    ung_vien = ung_vien or {}
    ghi_log = ghi_log or (lambda m: None)
    ncc = (cfg.get("nha_cung_cap") or "anthropic").lower()
    khoa = doc_khoa(ncc)
    tom = {"bat": True, "nha_cung_cap": ncc, "model": cfg.get("model") or CLOUD_MODEL_MAC_DINH.get(ncc, ""), "so_o_chon": 0,
           "so_o_gui": 0, "khong_gui": [], "xac_nhan": 0, "sua": 0, "cung_khong_quy_dinh": 0, "khong_xac_nhan": 0,
           "loi": "", "nhat_ky": "", "token_vao": 0, "token_ra": 0}
    if not khoa:
        tom["loi"] = f"Chưa có API key {ncc} (Cài đặt → Kiểm tra chéo cloud)"
        ghi_log("Bỏ qua kiểm tra chéo cloud: " + tom["loi"])
        return tom
    by_ma = {d["ma"]: d for d in bang}
    p_by = {p["ma"]: p for p in params}
    chon = chon_o(bang, float(cfg.get("ty_le", 20) or 0), rng, {p["ma"] for p in params if p.get("luon_cloud")})
    tom["so_o_chon"] = len(chon)
    if not chon:
        ghi_log("Kiểm tra chéo cloud: không có ô nào cần gửi")
        return tom
    an = AnDanh(thong_tin_dinh_danh(ket_qua))
    log_path = os.path.join(out_dir, f"GUI_RA_NGOAI_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt")
    tom["nhat_ky"] = log_path
    gui = []                      # (param, [khối đã che])
    for ma, ly_do in chon:
        rows, seen = [], set()
        for r in list(ung_vien.get(ma) or []) + list(sent.get(ma) or []):   # ứng viên rà lại trước, rồi vị trí dò
            if r["dieu"] != "0" and r["id"] not in seen:                     # không gửi Phần mở đầu / trang bìa
                seen.add(r["id"])
                rows.append(r)
        if not rows:
            tom["khong_gui"].append(f"{ma}: không có Khoản nào ngoài Phần mở đầu")
            continue
        blocks, n = [], 0
        for r in rows:
            b = an.che(f"[{nhan(r)}]\n{than(r)}")
            if blocks and n + len(b) > max_chars:
                break
            blocks.append(b)
            n += len(b)
        vet = an.dau_vet("\n".join(blocks))
        if vet:
            tom["khong_gui"].append(f"{ma}: còn thông tin định danh sau khi che ({'; '.join(vet[:3])})")
            continue
        gui.append((p_by[ma], blocks, ly_do))
    with open(log_path, "a", encoding="utf-8") as lf:
        lf.write(f"NHẬT KÝ GỬI RA NGOÀI — {datetime.datetime.now():%d/%m/%Y %H:%M:%S}\nNhà cung cấp: {ncc} | model: "
                 f"{cfg.get('model') or CLOUD_MODEL_MAC_DINH.get(ncc)}\nKhoá API: (không ghi)\n"
                 f"Ô được chọn: {', '.join(f'{m} ({l})' for m, l in chon)}\n"
                 + ("Không gửi: " + " | ".join(tom["khong_gui"]) + "\n" if tom["khong_gui"] else ""))
    nhom = []
    for p, blocks, ly in gui:     # gom ≤ 8 tham số / lần, gộp các khối trùng
        if not nhom or len(nhom[-1]) >= GROUP_MAX:
            nhom.append([])
        nhom[-1].append((p, blocks, ly))
    for gi, g in enumerate(nhom, 1):
        if dung is not None and dung.is_set():
            break
        blocks = []
        for _, bl, _ in g:
            for b in bl:
                if b not in blocks and sum(len(x) for x in blocks) + len(b) <= max_chars:
                    blocks.append(b)
        prompt = _prompt([p for p, _, _ in g], blocks)
        ghi_log(f"Kiểm tra chéo cloud ({ncc}) lần {gi}/{len(nhom)}: {', '.join(p['ma'] for p, _, _ in g)}")
        try:
            txt, ti, to, model = goi_api(ncc, cfg.get("model"), khoa, prompt)
        except CloudLoi as e:
            tom["loi"] = str(e)
            ghi_log(f"LỖI cloud: {e}")
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(f"\n===== LẦN {gi} — ĐÃ GỬI =====\n{prompt}\n===== LỖI =====\n{e}\n")
            break
        tom["token_vao"] += ti or 0
        tom["token_ra"] += to or 0
        tom["so_o_gui"] += len(g)
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"\n===== LẦN {gi} — ĐÃ GỬI ({model}) =====\n{prompt}\n===== NHẬN VỀ =====\n{txt}\n")
        data = parse_json(txt, "ket_qua") or {"ket_qua": []}
        got = {str(x.get("ma", "")).strip(): x for x in data["ket_qua"] if isinstance(x, dict)}
        for p, _, _ in g:
            d = by_ma[p["ma"]]
            c = got.get(p["ma"])
            if not c:
                d["nguon"] = "Local – cloud không trả lời"
                tom["khong_xac_nhan"] += 1
                continue
            c = {k: an.mo(str(c.get(k) or "")) for k in ("gia_tri", "don_vi", "dieu_khoan", "trich_dan", "ghi_chu")}
            gan_dieu_khoan(c, list(rows_by_id.values()))
            ck = check(c, full_norm, full_loose, None)
            d["cloud"] = {"gia_tri": c["gia_tri"], "trich_dan": c["trich_dan"], "kiem_tra": ck, "model": model}
            if not la_ok(ck):
                if la_khong_co(c["gia_tri"]) and la_khong_co(d.get("gia_tri")):
                    # hai model độc lập cùng kết luận HĐ không quy định (không có câu để kiểm nên vẫn cần anh xem)
                    d["nguon"] = "Local – cloud cùng: không quy định"
                    tom["cung_khong_quy_dinh"] += 1
                    continue
                # Claude ghi giá trị dài hơn (kèm diễn giải) nhưng câu trích đúng nguyên văn và chứa đúng giá trị local
                ck_l = check({**c, "gia_tri": d.get("gia_tri") or "", "ghi_chu": d.get("ghi_chu") or ""},
                             full_norm, full_loose, None)
                # chỉ khi Claude có câu trích, câu đó đúng nguyên văn (không tính "giá trị có nguyên văn") và Claude
                # không nói "không quy định"
                if (d.get("gia_tri") and (c["trich_dan"] or "").strip() and not la_khong_co(c["gia_tri"])
                        and ck_l in ("OK", "OK (khớp gần đúng)")):
                    d["nguon"] = "Local – cloud xác nhận (theo trích dẫn của Claude)"
                    if not la_ok(d.get("kiem_tra_tu")):
                        d.update(trich_dan=c["trich_dan"], dieu_khoan=c["dieu_khoan"] or d.get("dieu_khoan", ""),
                                 row_id=c.get("_row") or d.get("row_id", ""), kiem_tra_tu="OK (cloud xác nhận)")
                    d["kiem_tra"] = d.get("kiem_tra_tu") or d.get("kiem_tra")
                    tom["xac_nhan"] += 1
                    continue
                d["nguon"] = "Local – cloud không xác nhận được"
                tom["khong_xac_nhan"] += 1
                continue
            if giong_nhau(d.get("gia_tri") or "", c["gia_tri"]):
                d["nguon"] = "Local – cloud xác nhận"
                if not la_ok(d.get("kiem_tra_tu")):
                    d.update(trich_dan=c["trich_dan"], dieu_khoan=c["dieu_khoan"] or d.get("dieu_khoan", ""),
                             row_id=c.get("_row") or d.get("row_id", ""), kiem_tra_tu="OK (cloud xác nhận)")
                tom["xac_nhan"] += 1
            else:
                cu = d.get("gia_tri") or "(trống)"
                d["nguon"] = f"Cloud sửa (local: {cu[:80]})"
                d["gia_tri_local"] = d.get("gia_tri")
                d.update(gia_tri=c["gia_tri"], don_vi=c["don_vi"] or d.get("don_vi", ""), trich_dan=c["trich_dan"],
                         dieu_khoan=c["dieu_khoan"] or d.get("dieu_khoan", ""), row_id=c.get("_row") or "",
                         ghi_chu="; ".join(x for x in (c["ghi_chu"], "cloud sửa") if x),
                         kiem_tra_tu="KIỂM TRA: cloud sửa giá trị (trích dẫn khớp HĐ) — cần xác nhận")
                tom["sua"] += 1
            d["kiem_tra"] = d["kiem_tra_tu"]
    ghi_log(f"Kiểm tra chéo cloud xong: gửi {tom['so_o_gui']} ô, xác nhận {tom['xac_nhan']}, sửa {tom['sua']}, "
            f"cùng 'không quy định' {tom['cung_khong_quy_dinh']}, không xác nhận {tom['khong_xac_nhan']}, "
            f"không gửi {len(tom['khong_gui'])}")
    return tom


def thu_ket_noi(nha_cung_cap, model=None, timeout=60):
    """Gọi thử API bằng một câu ngắn (KHÔNG có dữ liệu hợp đồng) → {ok, model, giay, tra_loi | loi}."""
    # AI-0: nút thử kết nối cũng không được đọc khóa hoặc gọi nhà cung cấp.
    return {"ok": False, "model": model or "", "giay": 0, "ma_loi": CHO_NOI_MASK_V2, "loi": CLOUD_TAM_KHOA}

    import time
    ncc = (nha_cung_cap or "anthropic").lower()
    khoa = doc_khoa(ncc)
    m = model or CLOUD_MODEL_MAC_DINH.get(ncc, "")
    if not khoa:
        return {"ok": False, "model": m, "loi": f"Chưa có API key {ncc} — dán key rồi bấm Lưu key."}
    t0 = time.time()
    try:
        txt, ti, to, m = goi_api(ncc, m, khoa, 'Đây là lệnh kiểm tra kết nối. Trả về đúng JSON {"ket_qua": []}.',
                                 timeout=timeout)
    except CloudLoi as e:
        msg = str(e)
        goi_y = ""
        if "401" in msg or "authentication" in msg.lower():
            goi_y = " → API key sai hoặc đã bị thu hồi."
        elif "404" in msg or "not_found" in msg:
            goi_y = " → tên model không đúng hoặc tài khoản chưa được dùng model này."
        elif "429" in msg or "rate" in msg.lower():
            goi_y = " → vượt giới hạn gọi / hết hạn mức; thử lại sau."
        elif "400" in msg and "credit" in msg.lower():
            goi_y = " → tài khoản API hết tiền (credit balance)."
        elif "Không kết nối" in msg:
            goi_y = " → máy không ra được Internet tới api.anthropic.com (mạng / proxy / tường lửa)."
        return {"ok": False, "model": m, "giay": round(time.time() - t0, 1), "loi": msg + goi_y}
    return {"ok": True, "model": m, "giay": round(time.time() - t0, 1), "tra_loi": (txt or "")[:120],
            "token_vao": ti, "token_ra": to}
