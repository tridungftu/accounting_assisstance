# -*- coding: utf-8 -*-
"""
cloud.py — Kiểm tra chéo engine #6 qua cổng AI dùng chung (TL 48).
Giữ cách chọn ô và Python kiểm kết quả; Local trước, Cloud chỉ qua Mask v2.
Cổng quản lý khóa, che/mở che và nhật ký metadata, không ghi văn bản ra tệp.
"""
import json
import random
import re

from kho_tri_thuc.tri_thuc.cong_ai import BoGhiBoNho, CongAI

from .ai_local import SCHEMA_TRICH, AILoi
from .cau_hinh import doc_cau_hinh
from .cau_truc import nhan, than
from .kiem_tra import check, gan_dieu_khoan, giong_nhau, la_khong_co, la_ok, norm

GROUP_MAX = 8
# Giữ tên hằng để các module cũ import được; không còn đường Cloud trực tiếp.
CHO_NOI_MASK_V2 = "CONG_AI_BAT_BUOC"
CLOUD_TAM_KHOA = "Cloud phải đi qua cổng AI dùng chung (TL 48)."


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
    """Tương thích module/test cũ; không dùng cho Cloud. Mask v2 là bộ che duy nhất của cổng AI."""

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


# ------------------------------------------------------------------ cổng AI dùng chung
def tao_cong_ai(settings=None, bo_ghi=None):
    """Cài đặt local_ai/cong_ai cùng dạng source-settings.settings; không đọc khóa.

    Chưa có factory cổng ở tầng host: bên gọi có thể tiêm cổng đã gắn BoGhiPostgres.
    Mặc định đọc cấu hình nguồn không lấy biến HD_CLOUD; chỉ cong_ai.cloud_bat
    mới điều khiển Cloud. Bộ ghi bộ nhớ dành cho engine chạy thử độc lập.
    """
    if settings is None:
        settings = doc_cau_hinh(dung_env=False)
    if isinstance(settings, dict) and isinstance(settings.get("settings"), dict):
        settings = settings["settings"]
    settings = settings if isinstance(settings, dict) else {}
    return CongAI({"cong_ai": settings.get("cong_ai") or {}, "local_ai": settings.get("local_ai") or {}},
                  bo_ghi=bo_ghi if bo_ghi is not None else BoGhiBoNho())


def trang_thai_cloud(cong_ai, *, kiem_mask=False):
    st = dict(cong_ai.trang_thai(kiem_mask=kiem_mask)["cloud"])
    if st.get("ma") == "CLOUD_TAT":
        st["thong_bao"] = "Cloud đang tắt; phần mềm dùng Local AI."
    return st


def goi_api(nha_cung_cap, model, khoa, prompt, timeout=180, system=None, max_tokens=4096):
    """Tên cũ chỉ để tương thích import; mọi lượt phải đi qua cổng AI."""
    raise CloudLoi(CLOUD_TAM_KHOA)


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
                   rng=None, dung=None, max_chars=14000, ung_vien=None, *, cong_ai=None):
    """bang: list dòng kết quả (sẽ được SỬA: gia_tri, trich_dan, kiem_tra, nguon…).
    sent: {mã: [rows đã gửi local AI]}; ung_vien: {mã: [rows ứng viên tìm được khi rà lại toàn HĐ]} — gửi kèm để
    Claude không phải đọc lại đúng chỗ local có thể đã đọc sai. cfg: {nha_cung_cap, model, ty_le}. Trả dict tóm tắt."""
    from .ai_cloud import MayCloud

    ung_vien = ung_vien or {}
    ghi_log = ghi_log or (lambda m: None)
    cong_ai = cong_ai if cong_ai is not None else tao_cong_ai(cfg.get("settings"), cfg.get("bo_ghi"))
    st = trang_thai_cloud(cong_ai)
    ncc = cong_ai.cai_dat["nha_cung_cap"]
    tom = {"bat": st["dung_duoc"], "nha_cung_cap": ncc, "model": cong_ai.cai_dat["model"], "so_o_chon": 0,
           "so_o_gui": 0, "khong_gui": [], "xac_nhan": 0, "sua": 0, "cung_khong_quy_dinh": 0, "khong_xac_nhan": 0,
           "loi": "", "nhat_ky": "", "token_vao": 0, "token_ra": 0}
    if not st["dung_duoc"]:
        tom.update(ma_loi=st["ma"], loi=st["thong_bao"])
        ghi_log("Bỏ qua kiểm tra chéo cloud: " + tom["loi"])
        return tom
    ai = MayCloud(cong_ai=cong_ai, dung=dung, ghi_log=ghi_log)
    ai.dat_dinh_danh(thong_tin_dinh_danh(ket_qua))
    by_ma = {d["ma"]: d for d in bang}
    p_by = {p["ma"]: p for p in params}
    chon = chon_o(bang, float(cfg.get("ty_le", 20) or 0), rng, {p["ma"] for p in params if p.get("luon_cloud")})
    tom["so_o_chon"] = len(chon)
    if not chon:
        ghi_log("Kiểm tra chéo cloud: không có ô nào cần gửi")
        return tom
    gui = []                      # (param, [khối gốc], lý do chọn)
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
            b = f"[{nhan(r)}]\n{than(r)}"
            if blocks and n + len(b) > max_chars:
                break
            blocks.append(b)
            n += len(b)
        gui.append((p_by[ma], blocks, ly_do))
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
            items, ti, to = ai.hoi_trich(prompt, "kiểm tra chéo hợp đồng")
        except AILoi as e:
            tom["loi"] = str(e)
            tom["khong_gui"].extend(f"{p['ma']}: bỏ nhóm vì cổng AI chưa có kết quả: {e}" for p, _, _ in g)
            ghi_log("Cổng AI chưa có kết quả kiểm tra chéo: " + str(e))
            continue
        # Cổng Local trước; không ghi nhầm kết quả Local thành Cloud xác nhận.
        cloud = {t.ten for t in ai.ket_qua_cuoi.truong.values() if t.nguon == "CLOUD"}
        if not cloud:
            tom["khong_gui"].extend(f"{p['ma']}: cổng AI dùng kết quả Local, chưa có kết quả Cloud"
                                   for p, _, _ in g)
            ghi_log("Cổng AI dùng kết quả Local; chưa có kết quả Cloud kiểm tra chéo.")
            continue
        model = ai.model
        tom["token_vao"] += ti
        tom["token_ra"] += to
        got = {x["ma"]: x for x in items if x["ma"] in cloud}
        tom["so_o_gui"] += len(got)
        for p, _, _ in g:
            d = by_ma[p["ma"]]
            c = got.get(p["ma"])
            if not c:
                d["nguon"] = "Local – cloud không trả lời"
                tom["khong_xac_nhan"] += 1
                continue
            c = {k: str(c.get(k) or "") for k in ("gia_tri", "don_vi", "dieu_khoan", "trich_dan", "ghi_chu")}
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


def thu_ket_noi(nha_cung_cap, model=None, timeout=60, *, cong_ai=None, settings=None, bo_ghi=None):
    """Hỏi trạng thái cổng/Mask, không tạo yêu cầu model giả để thử khóa."""
    cong_ai = cong_ai if cong_ai is not None else tao_cong_ai(settings, bo_ghi)
    # Công tắc tắt: cổng không kiểm Mask, không đọc khóa Cloud.
    st = trang_thai_cloud(cong_ai, kiem_mask=True)
    kq = {"ok": st["dung_duoc"], "model": cong_ai.cai_dat["model"], "giay": 0}
    if not kq["ok"]:
        kq.update(ma_loi=st["ma"], loi=st["thong_bao"])
    else:
        kq["tra_loi"] = st["thong_bao"]
    return kq
