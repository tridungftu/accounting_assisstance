# -*- coding: utf-8 -*-
"""
quy_trinh.py — Xử lý MỘT hợp đồng theo 9 bước của phương pháp v3 (xem __init__.py).

    tx = TrichXuat(params, ai=MayAI(url, model), out_dir=..., ra_lai=True, cloud=None)
    kq = tx.xu_ly("hop_dong.docx")        # dict: bang (37 dòng), phieu, tom_tat, tep

tien_do(buoc, mo_ta, ty_le_trong_hd) được gọi ở mỗi mốc để giao diện hiện tiến độ; ghi_log(msg) ghi nhật ký
(không ghi nội dung hợp đồng). dung = threading.Event: bấm Dừng → DaDung.

SOURCE6-G5-E5: meta.mode == 'doi_chieu_ban_ky' (che_do vẫn RULE_ONLY) → cùng xu_ly trên PDF ký gốc + `kq["g5"]` đối chiếu TYPED với expected/binding
đã chụp (doi_chieu_e5). Không dùng compare/so_voi_dap_an cũ (substring) để quyết định. PDF không đọc được/OCR không có → g5 CHUA_DOI_CHIEU_DUOC.
"""
import copy as _copy                  # E3-01: alias — xu_ly có `import copy` cục bộ (khối meta) nên tên `copy` là biến cục bộ trong hàm
import datetime
import decimal
import hashlib
import json
import os
import re
import time
import unicodedata

from .ai_local import CTX_MUC_LUC, AILoi, DaDung
from .cau_truc import build_structure, locate, nhan, save, than, vi_tri
from .cloud import kiem_tra_cloud
from .doc_hop_dong import bang_nguon_khong_ho_tro, read_contract
from .kiem_tra import (check, compare, gan_dieu_khoan, giong_nhau, la_khong_co, la_ok, load_key, loose, norm,
                       tim_dap_an)
from .logic import kiem_tra_logic

GROUP_MAX = 8
MAX_CTX_CHARS = 14000
MAX_MUC_LUC_CHARS = 40000
BUOC = ["Đọc file", "Tách Điều/Khoản", "Dò vị trí tham số", "Hỏi Local AI", "Tự kiểm tra trích dẫn",
        "Rà lại ô vàng", "Kiểm tra logic", "Kiểm tra chéo cloud", "Xuất kết quả"]
TRANG_THAI = ("Chưa xác nhận", "Đã xác nhận", "Đã sửa tay")


def ten_an_toan(name, toi_da=60):
    """Tên thư mục/file ngắn, hợp lệ trên Windows (đường dẫn Windows tối đa 260 ký tự)."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return (s[:toi_da].rstrip(" .") or "hop_dong")


def build_prompt(params, rows_by_id, row_ids, used=None, max_chars=MAX_CTX_CHARS):
    ds = "\n".join(f"- {p['ma']} | {p['mo_ta']}" for p in params)
    blocks, total = [], 0
    for rid in row_ids:
        r = rows_by_id[rid]
        b = f"[{nhan(r)}]\n{than(r)}"
        if total + len(b) > max_chars and blocks:
            continue
        if len(b) > max_chars:                      # một Khoản dài hơn giới hạn → cắt (đã cảnh báo ở phiếu đầu vào)
            b = b[:max_chars]
        blocks.append(b)
        total += len(b)
        if used is not None:
            used.append(r)
    return (f"Trích các tham số sau từ các đoạn hợp đồng bên dưới.\n\nTHAM SỐ:\n{ds}\n\n"
            "QUY TẮC:\n"
            "- Mỗi tham số một phần tử trong 'ket_qua', giữ đúng mã.\n"
            "- gia_tri: ngắn gọn, giữ nguyên số liệu như trong hợp đồng (vd 7.915.563.292; 90; 0,15). "
            "Nếu hợp đồng ghi 'Không áp dụng' thì ghi 'Không áp dụng'. Không có thông tin thì ghi 'Không quy định'.\n"
            "- don_vi: đồng, %, ngày, tháng, bộ, %/ngày… (để trống nếu không có).\n"
            "- dieu_khoan: lấy từ nhãn trong ngoặc vuông của đoạn chứa thông tin (vd 'Điều 5 – Khoản 5.3').\n"
            "- trich_dan: chép NGUYÊN VĂN một câu ngắn trong hợp đồng chứa giá trị, không sửa chữ nào.\n"
            "- ghi_chu: ghi 'Suy ra' nếu giá trị được tính ra chứ không ghi trực tiếp (vd tỷ lệ giữ lại = 100% - tỷ lệ thanh toán).\n\n"
            "CÁC ĐOẠN HỢP ĐỒNG:\n\n" + "\n\n".join(blocks))


def chia_doan(rows, max_chars=MAX_CTX_CHARS):
    """Chia TOÀN BỘ HĐ thành các đoạn ≤ max_chars ký tự → list danh sách ID."""
    chunks, cur, n = [], [], 0
    for r in rows:
        size = len(nhan(r)) + len(than(r)) + 4
        if cur and n + size > max_chars:
            chunks.append(cur)
            cur, n = [], 0
        cur.append(r["id"])
        n += size
    if cur:
        chunks.append(cur)
    return chunks


def ghep_kiem_tra(ck, logic):
    """Kết quả tự kiểm + lỗi logic → nội dung cột Kiểm tra."""
    if not logic:
        return ck
    return ("KIỂM TRA: " + "; ".join(logic)) if la_ok(ck) else (ck + " | " + "; ".join(logic))


def _co_gia_tri(it):
    v = ((it or {}).get("gia_tri") or "").strip().lower()
    return bool(v) and not v.startswith(("không quy định", "không tìm thấy"))


class TrichXuat:
    def __init__(self, params, ai=None, out_dir=".", ra_lai=True, cloud=None, tien_do=None, ghi_log=None, dung=None,
                 thu_muc_dap_an=None, rng=None, che_do=None, meta=None):
        # common/v1 (CRM-41-01): che_do='RULE_ONLY' = KHÔNG AI/cloud/rà lại; TC-* theo quy tắc master_hd (llm=None) như đường Claude dùng cho phần
        # mở đầu; các mã khác giữ trạng thái chưa chạy AI + vị trí dò được. meta = bản chụp request/catalog/implementation ghi vào kết quả.
        if che_do not in (None, "RULE_ONLY"):
            raise ValueError(f"Chế độ trích không hỗ trợ: {che_do}")
        if che_do == "RULE_ONLY" and (ai is not None or cloud):
            raise ValueError("RULE_ONLY không nhận AI/cloud")
        # SOURCE6-G5-E5: biến thể đối chiếu bản ký chỉ chạy trên RULE_ONLY (không AI/cloud), có meta E5 đã chụp
        if isinstance(meta, dict) and meta.get("mode") == MODE_E5 and che_do != "RULE_ONLY":
            raise ValueError("Đối chiếu bản ký chỉ chạy RULE_ONLY")
        self.che_do = che_do
        self.meta = meta
        self.params = params
        self.ai = ai                              # None → chỉ tách cấu trúc + dò vị trí (không có Local AI)
        self.out_dir = out_dir
        self.ra_lai_bat = ra_lai
        self.cloud = cloud                        # None/{} = tắt; {"nha_cung_cap","model","ty_le"}
        self._tien_do = tien_do or (lambda *a: None)
        self.ghi_log = ghi_log or (lambda m: None)
        self.dung = dung
        self.thu_muc_dap_an = thu_muc_dap_an
        self.rng = rng
        self.ung_vien = {}                        # mã → ID các Khoản ứng viên tìm được khi rà lại toàn HĐ

    # ---------------------------------------------------------------- tiện ích
    def ocr_pdf(self, path, file):
        """PDF scan (hoặc Cài đặt: luôn OCR) → DOCX bằng ABBYY Hot Folder trên máy. Trả (đường dẫn đọc, info|None)."""
        from .ocr_abbyy import LoiOCR, chuan_bi_pdf, la_pdf_scan
        try:
            return chuan_bi_pdf(path, tien_do=lambda m: self.tien_do(0, m, 0.02), dung=self.dung, ghi_log=self.ghi_log)
        except LoiOCR as e:
            if la_pdf_scan(path):
                raise ValueError(f"{file} là PDF scan, cần OCR nhưng {e.thong_diep}") from None
            self.ghi_log(f"  OCR ABBYY lỗi ({e.ma}) → đọc lớp chữ của PDF")
            return path, None

    def tien_do(self, buoc, mo_ta, pct):
        if self.dung is not None and self.dung.is_set():
            raise DaDung()
        self._tien_do(buoc, mo_ta, pct)

    def tc_theo_quy_tac(self, text):
        """Thông tin chung (TC-01…) bằng quy tắc master_hd — dùng khi nguồn AI là Claude: phần mở đầu không gửi ra ngoài,
        và tên các bên lấy được ở đây để che trước khi gửi. Trả {mã: kết quả cùng dạng câu trả lời AI}."""
        try:
            from master_hd import trich_xuat as quy_tac
            hang = quy_tac([("", ln) for ln in text.split("\n") if ln.strip()], llm=None)
        except Exception as e:  # noqa: BLE001
            self.ghi_log(f"  quy tắc thông tin chung lỗi: {type(e).__name__}: {e}")
            return {}
        out = {}
        for r in hang:
            if not str(r.get("ma", "")).startswith("TC-") or r.get("gia_tri") in (None, ""):
                continue
            v = r["gia_tri"]
            if isinstance(v, (datetime.date, datetime.datetime)):
                v = v.strftime("%d/%m/%Y")
            out[r["ma"]] = {"ma": r["ma"], "gia_tri": str(v), "don_vi": r.get("don_vi") or "", "dieu_khoan": "",
                            "trich_dan": str(r.get("trich") or "")[:400],
                            "ghi_chu": "Quy tắc (thông tin chung không gửi ra ngoài)" + (f"; {r['ghi_chu']}" if r.get("ghi_chu") else "")}
        self.ghi_log(f"  quy tắc thông tin chung: {', '.join(out) or 'không bắt được mục nào'}")
        return out

    def ai_tim_vi_tri(self, params, rows):
        """Tham số chưa có vị trí → gửi AI mục lục (ID | nhãn | 120 ký tự đầu), AI chọn tối đa 3 ID mỗi tham số.
        Mục lục quá dài → chia phần (tránh vượt num_ctx)."""
        dong = [f"{r['id']} | {nhan(r)} | {r['noi_dung'][:120].replace(chr(10), ' ')}" for r in rows]
        phan, cur, n = [], [], 0
        for d in dong:
            if cur and n + len(d) > MAX_MUC_LUC_CHARS:
                phan.append(cur)
                cur, n = [], 0
            cur.append(d)
            n += len(d) + 1
        if cur:
            phan.append(cur)
        ds = "\n".join(f"- {p['ma']} | {p['mo_ta']}" for p in params)
        schema = {"type": "object", "properties": {"vi_tri": {"type": "array", "items": {"type": "object", "properties": {
            "ma": {"type": "string"}, "ids": {"type": "array", "items": {"type": "string"}}}, "required": ["ma", "ids"]}}},
            "required": ["vi_tri"]}
        valid = {x["id"] for x in rows}
        found = {}
        for i, ph in enumerate(phan, 1):
            prompt = (f"Dưới đây là MỤC LỤC HỢP ĐỒNG (ID | Điều/Khoản | đầu nội dung)"
                      + (f" — phần {i}/{len(phan)}" if len(phan) > 1 else "")
                      + ". Với mỗi tham số, chọn tối đa 3 ID của mục có khả năng chứa thông tin nhất. "
                      f"Không có thì để danh sách rỗng.\n\nTHAM SỐ:\n{ds}\n\nMỤC LỤC HỢP ĐỒNG:\n" + "\n".join(ph))
            data, tin, tout = self.ai.chat_json(prompt, schema, "vi_tri", CTX_MUC_LUC, "tìm vị trí qua mục lục")
            self.ghi_log(f"  AI tìm vị trí {len(params)} tham số (phần {i}/{len(phan)}) | token {tin:,}/{tout:,}")
            for x in data["vi_tri"]:
                if isinstance(x, dict):
                    ids = [j for j in x.get("ids", []) if j in valid]
                    found.setdefault(str(x.get("ma", "")), [])
                    found[str(x.get("ma", ""))] += [j for j in ids if j not in found[str(x.get("ma", ""))]]
        return {k: v[:3] for k, v in found.items()}

    # ---------------------------------------------------------------- bước 6: rà lại toàn HĐ
    def ra_lai(self, rows, rows_by_id, loc_by, results, sent, full_norm, full_loose):
        """Tham số chưa chắc sau lượt 1 → quét TOÀN BỘ HĐ theo đoạn, chỉ hỏi các tham số đó. Không 'thấy là bỏ':
        giữ mọi ứng viên qua được kiểm tra nguyên văn; lượt 1 đã có giá trị → lượt 2 chỉ XÁC NHẬN.
        ≥2 giá trị khác nhau cùng hợp lệ → vàng, liệt kê. Trả số lỗi AI."""
        def chac(it, ma):
            if not it or (it.get("gia_tri") or "") in ("", "Không tìm thấy trong HĐ"):
                return False
            return la_ok(check(it, full_norm, full_loose, sent.get(ma)))
        can = [p for p in self.params if not chac(results.get(p["ma"]), p["ma"])]
        if not can:
            self.ghi_log("  rà lại: không có ô vàng")
            return 0
        chunks = chia_doan(rows)
        batches = [can[i:i + GROUP_MAX] for i in range(0, len(can), GROUP_MAX)]
        total, k, n_err, t1 = len(chunks) * len(batches), 0, 0, time.time()
        cands = {p["ma"]: [] for p in can}
        self.ghi_log(f"  rà lại {len(can)} tham số × {len(chunks)} đoạn: {', '.join(p['ma'] for p in can)}")
        for ci, ids in enumerate(chunks):
            for b in batches:
                self.tien_do(5, f"Rà lại toàn HĐ: {len(can)} ô vàng — đoạn {ci + 1}/{len(chunks)}",
                             0.70 + 0.15 * k / max(1, total))
                k += 1
                used = []
                prompt = build_prompt(b, rows_by_id, ids, used)
                try:
                    items, _, _ = self.ai.hoi_trich(prompt, f"rà lại đoạn {ci + 1}")
                except AILoi as e:
                    n_err += 1
                    self.ghi_log(f"  LỖI rà lại đoạn {ci + 1}: {e}")
                    continue
                for it in items:
                    ma = (it.get("ma") or "").strip()
                    v = (it.get("gia_tri") or "").strip()
                    if ma not in cands or not v or la_khong_co(v):
                        continue
                    gan_dieu_khoan(it, used)
                    cands[ma].append((it, used, la_ok(check(it, full_norm, full_loose, used))))
                    if it.get("_row") and it["_row"] not in self.ung_vien.setdefault(ma, []):
                        self.ung_vien[ma].append(it["_row"])      # đoạn ứng viên → gửi kèm khi kiểm tra chéo cloud
        for p in can:
            ma = p["ma"]
            old = results.get(ma) or {"ma": ma, "gia_tri": ""}
            oks = [c for c in cands[ma] if c[2]]
            khac = []
            for it, _, _ in oks:
                if all(not giong_nhau(it["gia_tri"], x) for x in khac):
                    khac.append(it["gia_tri"])
            pref = set(loc_by[ma]["row_ids"])

            def tot(cs):
                return next((c for c in cs if c[0].get("_row") in pref), cs[0])

            def note(it, x):
                return "; ".join(y for y in ((it.get("ghi_chu") or "").strip(), x) if y)
            if _co_gia_tri(old):
                giong = [c for c in oks if giong_nhau(old["gia_tri"], c[0]["gia_tri"])]
                if giong:
                    best = tot(giong)
                    it = dict(best[0])
                    it["ghi_chu"] = note(it, "rà lại toàn HĐ: xác nhận")
                    results[ma], sent[ma] = it, best[1]
                else:
                    it = dict(old)
                    if oks:
                        it["_nhieu"] = " | ".join([old["gia_tri"]] + khac[:3])
                    it["ghi_chu"] = note(it, "đã rà toàn HĐ: không xác nhận được giá trị lượt 1")
                    results[ma] = it
            elif oks:
                best = tot(oks)
                it = dict(best[0])
                it["ghi_chu"] = note(it, "rà lại toàn HĐ")
                if len(khac) > 1:
                    it["_nhieu"] = " | ".join(khac[:4])
                elif best[0].get("_row") not in pref:
                    it["_xac_nhan"] = it.get("dieu_khoan", "")
                results[ma], sent[ma] = it, best[1]
            else:
                it = dict(old)
                it["ghi_chu"] = note(it, "đã rà toàn HĐ: không thấy giá trị chắc chắn")
                results[ma] = it
        n_fix = sum(1 for p in can if chac(results.get(p["ma"]), p["ma"]))
        self.ghi_log(f"  rà lại xong: {n_fix}/{len(can)} chắc chắn | {total} lần gọi | {time.time() - t1:.1f}s")
        return n_err

    # ---------------------------------------------------------------- một hợp đồng
    def xu_ly(self, path):
        t0 = time.time()
        file = os.path.basename(path)
        name = os.path.splitext(file)[0]
        ten = ten_an_toan(name)
        out = os.path.join(self.out_dir, ten)
        os.makedirs(out, exist_ok=True)
        dung_ai = self.ai is not None
        la_cloud = bool(getattr(self.ai, "la_cloud", False))     # Claude thay Local AI: che định danh, không gửi mở đầu
        ten_ai = getattr(self.ai, "ten", "Local AI") if dung_ai else "Local AI"
        if la_cloud:
            self.ai.nhat_ky = os.path.join(out, f"GUI_RA_NGOAI_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt")
        n_err = 0
        tok0 = (self.ai.tok_vao, self.ai.tok_ra) if dung_ai else (0, 0)
        self.ghi_log(f"HĐ {file}")
        self.ung_vien = {}
        e5 = isinstance(self.meta, dict) and self.meta.get("mode") == MODE_E5   # SOURCE6-G5-E5

        # 1. đọc file
        self.tien_do(0, "Đọc file" + (" (.doc → chuyển bằng Word)" if path.lower().endswith(".doc") else ""), 0.01)
        ocr = None
        path_goc = path                       # E3-01: file đầu vào gốc (PDF trước OCR) cho bang_nguon
        try:
            if path.lower().endswith(".pdf"):
                path, ocr = self.ocr_pdf(path, file)
            info = read_contract(path)
        except (ValueError, RuntimeError, OSError) as e:
            if not e5:
                raise
            # SOURCE6-G5-E5: PDF scan mà OCR tắt/không có, thiếu thư viện PDF, PDF hỏng → kết quả TRUNG THỰC chưa đối chiếu được (không ném → không LOI)
            return self._xu_ly_e5_khong_doc(path_goc, file, ten, out, t0, f"{type(e).__name__}: {str(e)[:300]}")
        # E3-01: bằng chứng bảng chụp NGAY từ đúng đầu vào đã đọc (bản sao bất biến); PDF qua OCR → KHONG_HO_TRO theo bytes PDF gốc
        bang_nguon = _copy.deepcopy(info["bang_nguon"]) if ocr is None else \
            bang_nguon_khong_ho_tro(path_goc, "E3_PDF_OCR_KHONG_HO_TRO", info["bang_nguon"])
        rep = info["report"]
        if ocr:
            rep["file"] = file
            rep["ocr"] = {k: ocr.get(k) for k in ("trang", "giay", "tu_luu_dem", "ly_do", "sha1")}
            rep["warnings"].insert(0, f"Văn bản lấy từ OCR ABBYY ({ocr.get('trang', '?')} trang"
                                      + (", dùng lại kết quả đã nhận dạng" if ocr.get("tu_luu_dem") else "")
                                      + ") — trích dẫn theo chữ đã nhận dạng; ô vàng nên đối chiếu bản scan")
        self.ghi_log(f"  đọc: {rep['words']:,} từ | {rep['articles']} Điều | {len(rep['warnings'])} cảnh báo")

        # 2. tách Điều/Khoản
        self.tien_do(1, f"Tách Điều/Khoản: {rep['words']:,} từ, {rep['articles']} Điều", 0.04)
        rows = build_structure(info)
        rows_by_id = {r["id"]: r for r in rows}
        tc_quy_tac = {}
        quy_tac_tc = self.che_do == "RULE_ONLY"
        if la_cloud:                          # thông tin chung (trong Phần mở đầu) đọc bằng quy tắc, không gửi ra ngoài
            tc_quy_tac = self.tc_theo_quy_tac(info["text"])
            from .ai_cloud import thong_tin_tu_tham_so
            self.ai.dat_dinh_danh(thong_tin_tu_tham_so({m: (v or {}).get("gia_tri") for m, v in tc_quy_tac.items()}))
        elif quy_tac_tc:                      # common RULE_ONLY: cùng quy tắc TC của nguồn, không AI
            ma_yc = {p["ma"] for p in self.params}
            tc_quy_tac = {m: v for m, v in self.tc_theo_quy_tac(info["text"]).items() if m in ma_yc}

        # 3. dò vị trí
        self.tien_do(2, f"Dò vị trí {len(self.params)} tham số theo từ khoá", 0.06)
        loc = locate(rows, self.params)
        loc_by = {x["ma"]: x for x in loc}
        missing = [p for p in self.params if not loc_by[p["ma"]]["row_ids"]]
        if missing and dung_ai:
            self.tien_do(2, f"{ten_ai} tìm vị trí {len(missing)} tham số không khớp từ khoá (qua mục lục)", 0.08)
            try:
                found = self.ai_tim_vi_tri(missing, [r for r in rows if r.get("dieu") != "0"] if la_cloud else rows)
            except AILoi as e:
                n_err += 1
                self.ghi_log(f"  LỖI tìm vị trí: {e}")
                found = {}
            for p in missing:
                ids = found.get(p["ma"], [])
                loc_by[p["ma"]]["row_ids"] = ids
                loc_by[p["ma"]]["vi_tri"] = [vi_tri(rows_by_id[i]) for i in ids]
                loc_by[p["ma"]]["tu_khoa"] += " | vị trí do AI tìm qua mục lục"
        save(os.path.join(out, ten), info, rows, loc)
        full_norm, full_loose = norm(info["text"]), loose(info["text"])

        # 4. hỏi AI theo nhóm
        groups = []
        for p in self.params:
            if not groups or groups[-1][0] != p["nhom"] or len(groups[-1][1]) >= GROUP_MAX:
                groups.append((p["nhom"], []))
            groups[-1][1].append(p)
        results, sent = {}, {}
        for gi, (grp, ps) in enumerate(groups):
            if la_cloud:
                for p in [p for p in ps if p["ma"].startswith("TC-")]:
                    results[p["ma"]] = tc_quy_tac.get(p["ma"]) or {
                        "ma": p["ma"], "gia_tri": "", "ghi_chu": "Thông tin chung không gửi ra ngoài; quy tắc không bắt được "
                                                                 "— nhập tay"}
                    sent[p["ma"]] = []
                ps = [p for p in ps if not p["ma"].startswith("TC-")]
                if not ps:
                    continue
            ids = []
            for rank in range(3):
                for p in ps:
                    r = loc_by[p["ma"]]["row_ids"]
                    if len(r) > rank and r[rank] not in ids:
                        ids.append(r[rank])
            if la_cloud:                      # không gửi Phần mở đầu / trang bìa ra ngoài
                ids = [i for i in ids if rows_by_id[i].get("dieu") != "0"]
            co_vi_tri = (lambda p: any(i in ids for i in loc_by[p["ma"]]["row_ids"])) if la_cloud else \
                (lambda p: bool(loc_by[p["ma"]]["row_ids"]))
            todo = [p for p in ps if co_vi_tri(p)]
            for p in ps:
                if la_cloud and loc_by[p["ma"]]["row_ids"] and not co_vi_tri(p):
                    results[p["ma"]] = {"ma": p["ma"], "gia_tri": "", "ghi_chu": "Chỉ có ở Phần mở đầu — không gửi ra "
                                                                                 "ngoài; xem đoạn và nhập tay"}
                elif not loc_by[p["ma"]]["row_ids"]:
                    results[p["ma"]] = {"ma": p["ma"], "gia_tri": "Không tìm thấy trong HĐ" if dung_ai else "",
                                        "ghi_chu": "Không xác định được vị trí"}
            if not todo:
                continue
            used = []
            prompt = build_prompt(todo, rows_by_id, ids, used)
            for p in todo:
                sent[p["ma"]] = used
            if not dung_ai:
                for p in todo:
                    results[p["ma"]] = {"ma": p["ma"], "gia_tri": "", "ghi_chu": "Chưa chạy AI — xem sheet Doan_lien_quan"}
                continue
            t1 = time.time()
            self.tien_do(3, f"Hỏi {ten_ai}: nhóm «{grp}» ({gi + 1}/{len(groups)}) — {len(todo)} tham số, {len(used)} đoạn",
                         0.10 + 0.55 * gi / len(groups))
            try:
                items, pi, po = self.ai.hoi_trich(prompt, f"nhóm {grp}")
            except AILoi as e:
                n_err += 1
                self.ghi_log(f"  LỖI nhóm {grp}: {e}")
                items, pi, po = [], 0, 0
            self.ghi_log(f"  nhóm {grp} | {len(todo)} tham số | {len(used)} đoạn | token {pi:,}/{po:,} | "
                         f"{time.time() - t1:.1f}s")
            got = {str(it.get("ma", "")).strip(): it for it in items}
            for p in todo:
                results[p["ma"]] = got.get(p["ma"], {"ma": p["ma"], "gia_tri": "", "ghi_chu": "AI không trả về"})
        if quy_tac_tc:                        # common RULE_ONLY: kết quả quy tắc TC thay ô "chưa chạy AI" của đúng mã đó
            for ma, it in tc_quy_tac.items():
                results[ma] = it

        # 5. tự kiểm: Điều/Khoản suy từ trích dẫn
        self.tien_do(4, "Tự kiểm tra trích dẫn và số liệu", 0.66)
        if dung_ai:
            for ma, it in results.items():
                gan_dieu_khoan(it, sent.get(ma))

        # 6. rà lại
        if dung_ai and self.ra_lai_bat and not la_cloud:     # rà lại = đọc cả HĐ → không làm khi dùng Claude
            n_err += self.ra_lai(rows, rows_by_id, loc_by, results, sent, full_norm, full_loose)

        # 7. logic
        self.tien_do(6, "Kiểm tra logic L1–L5", 0.86)
        logic = kiem_tra_logic(results, self.params, rows_by_id) if dung_ai else {}

        bang = []
        for p in self.params:
            it = results.get(p["ma"], {}) or {}
            if not dung_ai and quy_tac_tc and p["ma"] in tc_quy_tac:
                ck = check(it, full_norm, full_loose, None)        # tự kiểm trích dẫn quy tắc trên văn bản HĐ (nguồn)
            elif not dung_ai:
                ck = "CHƯA CHẠY AI" if loc_by[p["ma"]]["row_ids"] else "CHƯA CHẠY AI — chưa có vị trí"
            elif it.get("gia_tri") == "Không tìm thấy trong HĐ":
                ck = "KIỂM TRA: không tìm thấy vị trí"
            else:
                ck = check(it, full_norm, full_loose, sent.get(p["ma"]))
                if it.get("_nhieu"):
                    ck = "KIỂM TRA: nhiều giá trị khác nhau trong HĐ: " + it["_nhieu"]
                elif la_ok(ck) and it.get("_xac_nhan") is not None:
                    ck = f"KIỂM TRA: chỉ tìm thấy khi rà lại toàn HĐ ({it['_xac_nhan']}) — cần xác nhận"
            lg = logic.get(p["ma"], [])
            bang.append({"ma": p["ma"], "nhom": p["nhom"], "tham_so": p["ten"], "mo_ta": p["mo_ta"], "muc": p["muc"],
                         "gia_tri": it.get("gia_tri", ""), "don_vi": it.get("don_vi", ""),
                         "dieu_khoan": it.get("dieu_khoan", ""), "trich_dan": it.get("trich_dan", ""),
                         "ghi_chu": it.get("ghi_chu", ""), "kiem_tra": ghep_kiem_tra(ck, lg), "kiem_tra_tu": ck,
                         "logic": lg, "nguon": ("Quy tắc" if p["ma"] in tc_quy_tac and results.get(p["ma"]) is
                                                tc_quy_tac[p["ma"]] else ten_ai) if la_cloud else
                         (("Quy tắc" if p["ma"] in tc_quy_tac else "Chưa chạy AI") if quy_tac_tc else "Local"),
                         "trang_thai": TRANG_THAI[0], "row_id": it.get("_row", ""),
                         "vi_tri_do_duoc": "; ".join(loc_by[p["ma"]]["vi_tri"]), "lich_su": []})

        # 8. kiểm tra chéo cloud → sau đó chạy lại logic trên giá trị/trích dẫn mới
        tom_cloud = {"bat": False}
        if dung_ai and self.cloud and not la_cloud:
            self.tien_do(7, "Kiểm tra chéo trên cloud (đã che thông tin định danh)", 0.90)
            tom_cloud = kiem_tra_cloud(bang, self.params, results, sent, rows_by_id, full_norm, full_loose, out,
                                       self.cloud, self.ghi_log, self.rng, self.dung,
                                       ung_vien={m: [rows_by_id[i] for i in ids] for m, ids in self.ung_vien.items()})
            if tom_cloud.get("so_o_gui"):
                moi = {d["ma"]: {"gia_tri": d["gia_tri"], "trich_dan": d["trich_dan"], "_row": d.get("row_id")}
                       for d in bang}
                logic = kiem_tra_logic(moi, self.params, rows_by_id)
                for d in bang:
                    d["logic"] = logic.get(d["ma"], [])
                    d["kiem_tra"] = ghep_kiem_tra(d["kiem_tra_tu"], d["logic"])

        for d in bang:                       # giá trị máy trích (sau cloud) — luôn giữ lại khi người soát sửa
            d.update(gia_tri_ai=d["gia_tri"], da_xac_nhan=False, da_sua=False)

        # so đáp án (nếu có)
        key = load_key(tim_dap_an(name, self.thu_muc_dap_an)) if dung_ai else None
        n_key = n_keyed = 0
        if key:
            for d in bang:
                if d["ma"] in key:
                    n_keyed += 1
                    d["dap_an"] = key[d["ma"]]
                    d["so_voi_dap_an"] = compare(key[d["ma"]], d["gia_tri"])
                    n_key += d["so_voi_dap_an"] == "ĐÚNG"

        # 9. xuất
        self.tien_do(8, "Ghi Excel / JSON", 0.97)
        doan = {}
        if not dung_ai:
            for p in self.params:
                for rid in loc_by[p["ma"]]["row_ids"]:
                    r = rows_by_id[rid]
                    doan.setdefault(p["ma"], []).append({"vi_tri": vi_tri(r), "noi_dung": than(r)[:3000]})
        n_ok = sum(1 for d in bang if la_ok(d["kiem_tra"]))
        dt = time.time() - t0
        kq = {
            "hop_dong": file, "ten": ten, "che_do": "AI" if dung_ai else ("RULE_ONLY" if quy_tac_tc else "chua_chay_AI"),
            "model": self.ai.model if dung_ai else None, "may_ai": self.ai.url if dung_ai else None,
            "tao_luc": datetime.datetime.now().isoformat(timespec="seconds"),
            "tuy_chon": {"ra_lai": bool(self.ra_lai_bat and dung_ai and not la_cloud),
                         "cloud": bool(self.cloud and dung_ai and not la_cloud), "nguon_ai": ten_ai if dung_ai else "",
                         "gui_ra_ngoai": getattr(self.ai, "nhat_ky", "") if la_cloud else ""},
            "tom_tat": {"so_tham_so": len(bang), "so_ok": n_ok, "so_vang": len(bang) - n_ok,
                        "dung_dap_an": f"{n_key}/{n_keyed}" if key else "",
                        "token_vao": (self.ai.tok_vao - tok0[0]) if dung_ai else 0,
                        "token_ra": (self.ai.tok_ra - tok0[1]) if dung_ai else 0,
                        "thoi_gian_giay": round(dt), "loi_ai": n_err, "cloud": tom_cloud},
            "phieu_kiem_tra": rep, "bang": bang, "doan_lien_quan": doan,
            "bang_nguon": bang_nguon,         # E3-01: source6-docx-tables/v1 — ghi cùng raw JSON ngay lần ghi đầu, nằm trong SHA niêm phong
        }
        from .xuat import ghi_ket_qua_hd
        if self.meta is not None:             # common/v1: bản chụp request/catalog/rules/implementation đi cùng raw JSON ngay lần ghi đầu
            import copy
            kq["common"] = copy.deepcopy(self.meta)
            kq["common"]["tham_so_trong_ket_qua"] = [d["ma"] for d in bang]
        if e5:                                # SOURCE6-G5-E5: đối chiếu TYPED trên chính văn bản đã đọc (lớp chữ PDF/OCR) — không dùng compare cũ
            kq["g5"] = doi_chieu_e5(self.meta, self.params, path_goc, info, ocr, path, tc_quy_tac)
            self.ghi_log(f"  đối chiếu bản ký: {kq['g5']['trang_thai']} | khớp {len(kq['g5']['khop'])} | lệch {len(kq['g5']['lech'])} | "
                         f"thiếu {len(kq['g5']['thieu'])}")
        kq["tom_tat"]["so_can_xem"] = sum(1 for d in bang if not la_ok(d["kiem_tra"]))
        kq["tom_tat"]["so_da_xac_nhan"] = 0
        ghi_ket_qua_hd(kq, out)
        self.ghi_log(f"  xong {file} | {n_ok}/{len(bang)} OK" + (f" | đáp án {n_key}/{n_keyed}" if key else "")
                     + f" | {dt:.0f}s | lỗi AI: {n_err}")
        return kq

    def _xu_ly_e5_khong_doc(self, path_goc, file, ten, out, t0, loi):
        """SOURCE6-G5-E5: không đọc được PDF ký (scan khi OCR tắt/không có ABBYY, thiếu thư viện PDF, PDF hỏng) → kết quả ĐÚNG HÌNH legacy (bang theo
        tham số, phiếu đầu vào cùng khóa PDF, common) + g5 CHUA_DOI_CHIEU_DUOC cho MỌI mã; ghi qua cùng ghi_ket_qua_hd để niêm phong như thường.
        Không tạo trang/vị trí, không ném lỗi (để lượt niêm phong được trạng thái chưa đối chiếu thay vì LOI)."""
        self.ghi_log(f"  không đọc được PDF ký để đối chiếu: {loi}")
        ck = "CHƯA ĐỐI CHIẾU ĐƯỢC — không đọc được PDF ký"
        rep = {"file": file, "words": 0, "raw_words": 0, "pages": 0, "articles": 0, "article_range": "-", "numbered_paragraphs": 0, "tables": 0,
               "images": 0, "toc_skipped": 0, "track_changes_accepted": 0, "accept_by": "", "warnings": [f"Không đọc được PDF ký: {loi}"]}
        bang = [{"ma": p["ma"], "nhom": p["nhom"], "tham_so": p["ten"], "mo_ta": p["mo_ta"], "muc": p["muc"], "gia_tri": "", "don_vi": "",
                 "dieu_khoan": "", "trich_dan": "", "ghi_chu": "Không đọc được PDF ký", "kiem_tra": ck, "kiem_tra_tu": ck, "logic": [],
                 "nguon": "Chưa đọc được", "trang_thai": TRANG_THAI[0], "row_id": "", "vi_tri_do_duoc": "", "lich_su": [],
                 "gia_tri_ai": "", "da_xac_nhan": False, "da_sua": False} for p in self.params]
        dt = time.time() - t0
        kq = {
            "hop_dong": file, "ten": ten, "che_do": "RULE_ONLY", "model": None, "may_ai": None,
            "tao_luc": datetime.datetime.now().isoformat(timespec="seconds"),
            "tuy_chon": {"ra_lai": False, "cloud": False, "nguon_ai": "", "gui_ra_ngoai": ""},
            "tom_tat": {"so_tham_so": len(bang), "so_ok": 0, "so_vang": len(bang), "dung_dap_an": "", "token_vao": 0, "token_ra": 0,
                        "thoi_gian_giay": round(dt), "loi_ai": 0, "cloud": {"bat": False}},
            "phieu_kiem_tra": rep, "bang": bang, "doan_lien_quan": {},
            "bang_nguon": bang_nguon_khong_ho_tro(path_goc),
        }
        from .xuat import ghi_ket_qua_hd
        kq["common"] = _copy.deepcopy(self.meta)
        kq["common"]["tham_so_trong_ket_qua"] = [d["ma"] for d in bang]
        kq["g5"] = g5_khong_doc_duoc(self.meta, loi)
        kq["tom_tat"]["so_can_xem"] = len(bang)
        kq["tom_tat"]["so_da_xac_nhan"] = 0
        ghi_ket_qua_hd(kq, out)
        self.ghi_log(f"  xong {file} | đối chiếu bản ký: CHUA_DOI_CHIEU_DUOC | {dt:.0f}s")
        return kq


# ================================================================== SOURCE6-G5-E5 — đối chiếu bản ký TYPED (contract CRM_G5_*)
# Không dùng kiem_tra.compare (substring: 100 có thể 'ĐÚNG' với 1000) ở bất kỳ đâu trong E5. Chỉ dùng lại đọc PDF/OCR, quy tắc TC, bản chụp catalog,
# và chuẩn hoá KỸ THUẬT norm() (NFC, ngoặc, khoảng trắng, chữ thường) để so text NGUYÊN CHUỖI; số/tiền/ngày/bảng so canonical typed.
MODE_E5 = "doi_chieu_ban_ky"
KIEU_G5 = "CRM_G5_COMPARE_RESULT_V1"
KIEU_EXPECTED_E5, KIEU_BINDING_E5 = "CRM_G5_EXPECTED_V1", "CRM_G5_CATALOG_BINDING_V1"
NGUON_PDF, NGUON_OCR = "PDF_LOP_CHU", "OCR_DOCX"
KIEU_GIA_TRI_E5 = ("text", "so", "ngay", "tien", "bang")
_RE_HEX64 = re.compile(r"[0-9a-f]{64}")
_RE_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_RE_SO_E5 = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d*[1-9])?")
_RE_NGAY_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_RE_TIEN_TE = re.compile(r"[A-Z]{3}")
_LINEAGE_UUID = ("ky_id", "hop_dong_id", "soan_id", "xuat_id", "mau_phien_ban_id", "anh_xa_id")
_LINEAGE_HEX = ("g3_input_sha256", "g3_docx_sha256", "g3_pdf_sha256", "ban_do_sha256", "danh_muc_digest", "profile_sha256", "du_lieu_sha256")
_LINEAGE_INT = ("revision", "danh_muc_rev")
_KHOA_LINEAGE = frozenset(_LINEAGE_UUID + _LINEAGE_HEX + _LINEAGE_INT + ("danh_muc_ref",))
_BINDING_LINEAGE = ("danh_muc_ref", "danh_muc_rev", "danh_muc_digest", "mau_phien_ban_id", "profile_sha256")
_KHOA_BINDING = frozenset(("kieu", "loai_hop_dong", "catalog_id", "catalog_sha256", "mapping") + _BINDING_LINEAGE)
_KHOA_G5 = frozenset(("kieu", "source_sha256", "signed_pdf_sha256", "expected_sha256", "catalog_binding_sha256", "g3_pdf_sha256", "coverage",
                      "trang_thai", "khop", "lech", "thieu", "nguon_doc"))
_KHOA_G5_KHOP = frozenset(("ma", "muc", "kieu", "gia_tri", "trich_dan", "vi_tri_do_duoc"))
_KHOA_G5_LECH = frozenset(("ma", "muc", "kieu", "gia_tri_ky_vong", "gia_tri_ban_ky", "trich_dan", "vi_tri_do_duoc"))
_KHOA_G5_THIEU = frozenset(("ma", "muc", "kieu", "ly_do", "gia_tri_ky_vong", "mot_phan"))
_KHOA_NGUON_DOC = frozenset(("kieu", "pdf_sha256", "ocr_docx_sha256", "so_trang", "loi"))
_KHOA_VI_TRI = frozenset(("nguon", "pdf_sha256", "ocr_docx_sha256", "trang", "dong"))
# token số kiểu Việt Nam: nhóm nghìn '.', thập phân ','. Dạng mơ hồ như '10.5' KHÔNG thành token (không đoán).
_RE_SO_VN = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(?!\d|[.,]\d)")
_RE_NGAY_GACH = re.compile(r"(?<!\d)(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})(?!\d)")
_RE_NGAY_CHU = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})")
_TIEN_TE_HAU_TO = (("VND", re.compile(r"(?:đồng|vnđ|vnd|đ)(?!\w)")), ("USD", re.compile(r"(?:usd|đô la mỹ)(?!\w)")),
                   ("EUR", re.compile(r"(?:eur|euro)(?!\w)")))
_TIEN_TE = frozenset(m for m, _ in _TIEN_TE_HAU_TO)


class LoiE5(ValueError):
    """Lỗi hình thức E5 (expected/binding/g5): `ma` ngắn ổn định."""
    def __init__(self, ma, thong_bao):
        super().__init__(thong_bao)
        self.ma = ma


def _canon_e5(x):
    """Cùng quy tắc canonical của common (sort_keys, không khoảng trắng, UTF-8); NaN/Infinity bị từ chối."""
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _la_int(v, toi_thieu, toi_da=None):
    return isinstance(v, int) and not isinstance(v, bool) and v >= toi_thieu and (toi_da is None or v <= toi_da)


def _la_so_e5(s):
    return isinstance(s, str) and _RE_SO_E5.fullmatch(s) is not None and s != "-0"


def _gia_tri_don_e5(kieu, v):
    if kieu == "text":
        return isinstance(v, str) and v.strip() != ""
    if kieu == "ngay":
        if not isinstance(v, str) or not _RE_NGAY_ISO.fullmatch(v):
            return False
        try:
            datetime.date.fromisoformat(v)
        except ValueError:
            return False
        return True
    if kieu == "so":
        return isinstance(v, dict) and set(v) == {"so", "don_vi"} and _la_so_e5(v["so"]) and \
            (v["don_vi"] is None or (isinstance(v["don_vi"], str) and v["don_vi"] != "" and v["don_vi"] == v["don_vi"].strip()))
    if kieu == "tien":
        return isinstance(v, dict) and set(v) == {"so", "tien_te"} and _la_so_e5(v["so"]) and \
            isinstance(v["tien_te"], str) and _RE_TIEN_TE.fullmatch(v["tien_te"]) is not None
    return False


def gia_tri_e5_hop_le(kieu, v):
    """Giá trị typed của một mã E5 (cùng định nghĩa với client central): bang = {cot:[{ten,kieu}], dong:[[ô]]}, cột đầu text là khóa dòng không null,
    duy nhất; ô null = chưa có (khác 0)."""
    if kieu != "bang":
        return kieu in KIEU_GIA_TRI_E5 and _gia_tri_don_e5(kieu, v)
    if not isinstance(v, dict) or set(v) != {"cot", "dong"} or not isinstance(v["cot"], list) or not v["cot"] \
            or not isinstance(v["dong"], list) or not v["dong"]:
        return False
    cot = v["cot"]
    if any(not isinstance(c, dict) or set(c) != {"ten", "kieu"} or not isinstance(c["ten"], str) or not c["ten"].strip()
           or c["kieu"] not in ("text", "so", "ngay", "tien") for c in cot):
        return False
    if len({c["ten"] for c in cot}) != len(cot) or cot[0]["kieu"] != "text":
        return False
    khoa = []
    for r in v["dong"]:
        if not isinstance(r, list) or len(r) != len(cot) or r[0] is None:
            return False
        if any(x is not None and not _gia_tri_don_e5(c["kieu"], x) for c, x in zip(cot, r)):
            return False
        khoa.append(r[0])
    return len(set(khoa)) == len(khoa)


def kiem_expected_e5(expected):
    """expected CRM_G5_EXPECTED_V1 — hình thức typed (nguồn KHÔNG đọc CRM, chỉ kiểm cấu trúc và chụp)."""
    if not isinstance(expected, dict) or set(expected) != {"kieu", "lineage", "tham_so"} or expected.get("kieu") != KIEU_EXPECTED_E5:
        raise LoiE5("E5_EXPECTED_SAI", "expected phải đúng {kieu=CRM_G5_EXPECTED_V1, lineage, tham_so}")
    ln = expected["lineage"]
    if not isinstance(ln, dict) or set(ln) != _KHOA_LINEAGE:
        raise LoiE5("E5_LINEAGE_SAI", "expected.lineage thiếu/thừa trường")
    if any(not isinstance(ln[k], str) or not _RE_UUID.fullmatch(ln[k]) for k in _LINEAGE_UUID) or \
            any(not isinstance(ln[k], str) or not _RE_HEX64.fullmatch(ln[k]) for k in _LINEAGE_HEX) or \
            any(not _la_int(ln[k], 1) for k in _LINEAGE_INT) or not isinstance(ln["danh_muc_ref"], str) or not ln["danh_muc_ref"].strip() \
            or len(ln["danh_muc_ref"]) > 200:
        raise LoiE5("E5_LINEAGE_SAI", "expected.lineage sai kiểu (UUID/HEX64/int>=1/text)")
    ts = expected["tham_so"]
    if not isinstance(ts, list) or not ts:
        raise LoiE5("E5_EXPECTED_RONG", "expected.tham_so phải không rỗng")
    ma = []
    for t in ts:
        if not isinstance(t, dict) or set(t) != {"ma", "kieu", "gia_tri"} or not isinstance(t["ma"], str) or not t["ma"].strip() \
                or t["ma"] != t["ma"].strip():
            raise LoiE5("E5_EXPECTED_SAI", "mỗi expected.tham_so phải đúng {ma, kieu, gia_tri}")
        if t["kieu"] not in KIEU_GIA_TRI_E5:
            raise LoiE5("E5_KIEU_SAI", f"{t['ma']}: kiểu không hỗ trợ")
        if not gia_tri_e5_hop_le(t["kieu"], t["gia_tri"]):
            raise LoiE5("E5_GIA_TRI_SAI", f"{t['ma']}: giá trị không đúng kiểu canonical")
        ma.append(t["ma"])
    if len(set(ma)) != len(ma):
        raise LoiE5("E5_EXPECTED_TRUNG", "expected.tham_so có mã trùng")
    return expected


def kiem_binding_e5(binding, *, loai, catalog_id, catalog_sha256, lineage):
    """catalog_binding CRM_G5_CATALOG_BINDING_V1: loại/catalog khớp outer, danh mục/mẫu/profile khớp lineage (cùng kiểu), mapping {ma,crm_truong,muc 0..3}
    duy nhất. Mức so với catalog ghim kiểm riêng (muc_da_ghim) khi đã có bản chụp."""
    if not isinstance(binding, dict) or set(binding) != _KHOA_BINDING or binding.get("kieu") != KIEU_BINDING_E5:
        raise LoiE5("E5_BINDING_SAI", "catalog_binding phải đúng khóa CRM_G5_CATALOG_BINDING_V1")
    if (binding["loai_hop_dong"], binding["catalog_id"], binding["catalog_sha256"]) != (loai, catalog_id, catalog_sha256):
        raise LoiE5("E5_BINDING_CATALOG", "catalog_binding khác loại/catalog của yêu cầu")
    if any(type(binding[k]) is not type(lineage[k]) or binding[k] != lineage[k] for k in _BINDING_LINEAGE):
        raise LoiE5("E5_BINDING_LINEAGE", "catalog_binding khác expected.lineage (danh mục/mẫu/profile)")
    mp = binding["mapping"]
    if not isinstance(mp, list) or not mp or any(
            not isinstance(m, dict) or set(m) != {"ma", "crm_truong", "muc"} or not isinstance(m["ma"], str) or not m["ma"].strip()
            or not isinstance(m["crm_truong"], str) or not m["crm_truong"].strip() or not _la_int(m["muc"], 0, 3) for m in mp):
        raise LoiE5("E5_BINDING_MAPPING", "mapping phải không rỗng, mỗi mục {ma, crm_truong, muc 0..3}")
    if len({m["ma"] for m in mp}) != len(mp):
        raise LoiE5("E5_BINDING_TRUNG", "mapping có mã trùng")
    return binding


def _so_chuan_e5(d):
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _ngay_iso(ngay, thang, nam):
    try:
        return datetime.date(int(nam), int(thang), int(ngay)).isoformat()
    except ValueError:
        return None


def _token_e5_vt(dong_norm):
    """Như `_token_e5` nhưng giữ khoảng ký tự [đầu, cuối) của từng token (cuối gồm cả hậu tố %/tiền tệ/từ đơn vị) — để tách ô bảng theo vị trí."""
    ngay = []
    for rx in (_RE_NGAY_GACH, _RE_NGAY_CHU):
        for m in rx.finditer(dong_norm):
            ngay.append((m.start(), m.end(), _ngay_iso(m.group(1), m.group(2), m.group(3))))
    tok = [(a, b, "ngay", iso, None) for a, b, iso in ngay]
    for m in _RE_SO_VN.finditer(dong_norm):
        if any(a <= m.start() < b for a, b, _ in ngay):
            continue
        sau_tho = dong_norm[m.end():]
        sau = sau_tho.lstrip()
        dau = m.end() + len(sau_tho) - len(sau)
        cuoi = m.end()
        if sau.startswith("%"):
            hau, cuoi = "%", dau + 1
        else:
            tt = next(((ma, rx.match(sau)) for ma, rx in _TIEN_TE_HAU_TO if rx.match(sau)), None)
            if tt is not None:
                hau, cuoi = tt[0], dau + tt[1].end()
            else:
                w = re.match(r"[^\W\d_]+", sau)
                hau = w.group(0) if w else None
                if w:
                    cuoi = dau + w.end()
        so = _so_chuan_e5(decimal.Decimal(m.group(1).replace(".", "") + (("." + m.group(2)) if m.group(2) else "")))
        tok.append((m.start(), cuoi, "so", so, hau))
    return sorted(tok, key=lambda t: t[0])


def _token_e5(dong_norm):
    """Token typed THEO THỨ TỰ trong một dòng đã norm: ("ngay", iso|None, None) và ("so", số canonical, hậu tố) — hậu tố '%', mã tiền tệ
    VND/USD/EUR theo chữ liền sau, từ đơn vị liền sau (vd 'ngày'), hoặc None. Số nằm trong một ngày không tách riêng."""
    return [t[2:] for t in _token_e5_vt(dong_norm)]


_DAU_BIEN = " :;,.|"


def _tu_bang_e5(dong):
    """Từ của MỘT dòng bản ký: (từ gốc NFC đã gọn khoảng trắng, từ norm tương ứng 1:1). norm làm mất/tách từ → None (không tự ghép)."""
    goc = [w for w in re.sub(r"\s+", " ", unicodedata.normalize("NFC", dong or "")).strip().split(" ") if w]
    nn = [norm(w) for w in goc]
    if not goc or any(not x or " " in x for x in nn):
        return None
    return goc, nn


def _o_bang_e5(cot, con_goc, con_nn, mau):
    """Ô cột 2..n của MỘT dòng bảng, đọc từ phần SAU khóa dòng theo đúng thứ tự xuất hiện (không tìm chuỗi kỳ vọng). Trả (ô[], None) | (None, lý do).
    - Không có cột text ngoài khóa: chữ giữa các token là lời nối; số token typed phải BẰNG số cột typed, đổi theo thứ tự.
    - Có cột text: chuỗi đoạn [text | typed] phải khớp 1:1 nhóm cột (cột text liền nhau gom một nhóm); nhóm k>1 cột text chỉ tách được khi đoạn
      có đúng k từ. Thừa/thiếu từ, đoạn không khớp cấu trúc → O_KHONG_XAC_DINH (không đoán ranh giới ô)."""
    s = " ".join(con_nn)
    dau_tu, p = [], 0
    for w in con_nn:
        dau_tu.append(p)
        p += len(w) + 1

    def tu(c):
        return max(k for k, a in enumerate(dau_tu) if a <= c)
    seg, k = [], 0
    for a, b, *tk in (_token_e5_vt(s) if con_nn else []):
        w0, w1 = tu(a), tu(max(a, b - 1))
        if w0 > k:
            seg.append(("text", con_goc[k:w0]))
        seg.append(("typed", tuple(tk)))
        k = max(k, w1 + 1)
    if k < len(con_goc):
        seg.append(("text", con_goc[k:]))
    seg = [(x, v if x == "typed" else [w.strip(_DAU_BIEN) for w in v if w.strip(_DAU_BIEN)]) for x, v in seg]
    seg = [(x, v) for x, v in seg if x == "typed" or v]
    loai = [c["kieu"] for c in cot[1:]]
    o = [None] * len(loai)
    if "text" not in loai:
        typed = [v for x, v in seg if x == "typed"]
        if len(typed) != len(loai):
            return None, "O_KHONG_XAC_DINH"
        cap = [(j, tk) for j, tk in enumerate(typed)]
    else:
        nhom = []
        for j, l in enumerate(loai):
            if l == "text" and nhom and nhom[-1][0] == "text":
                nhom[-1][1].append(j)
            else:
                nhom.append(("text" if l == "text" else "typed", [j]))
        if len(nhom) != len(seg) or any(n[0] != x for n, (x, _v) in zip(nhom, seg)):
            return None, "O_KHONG_XAC_DINH"
        cap = []
        for (x, cs), (_x, v) in zip(nhom, seg):
            if x == "typed":
                cap.append((cs[0], v))
            elif len(cs) == 1:
                o[cs[0]] = " ".join(v)
            elif len(v) == len(cs):
                for j, w in zip(cs, v):
                    o[j] = w
            else:
                return None, "O_KHONG_XAC_DINH"
    for j, tk in cap:
        o[j] = _gia_tri_tu_token(loai[j], tk, mau[j])
        if o[j] is None:
            return None, "O_KHONG_DOC_DUOC"
    return o, None


def _gia_tri_tu_token(kieu, tk, ky_vong):
    """Token → giá trị typed của kiểu yêu cầu (None nếu token không phải kiểu đó). Tiền giữ ĐÚNG tiền tệ đọc được (không quy đổi); số giữ đơn vị đọc
    được ('%' hoặc đúng từ đơn vị kỳ vọng), từ đơn vị khác → không phải ứng viên."""
    if kieu == "ngay":
        return tk[1] if tk[0] == "ngay" and tk[1] else None
    if tk[0] != "so":
        return None
    so, hau = tk[1], tk[2]
    if kieu == "tien":
        return {"so": so, "tien_te": hau} if hau in _TIEN_TE else None
    if kieu == "so":
        if hau in _TIEN_TE:
            return None
        if hau == "%":
            return {"so": so, "don_vi": "%"}
        if hau is None:
            return {"so": so, "don_vi": None}
        dv = ky_vong.get("don_vi") if isinstance(ky_vong, dict) else None
        if dv is not None and norm(hau) == norm(dv):
            return {"so": so, "don_vi": dv}
    return None


def _dong_neo(dong_norm, p):
    """Chỉ số dòng neo của một tham số theo CHÍNH bản chụp catalog: chứa từ khoá nội dung, có từ khoá bắt buộc (nếu có), không chứa từ khoá loại trừ.
    Đây là ĐỊNH VỊ dòng; giá trị vẫn so typed nguyên vẹn (không substring trên giá trị)."""
    kws = [norm(k) for k in (p or {}).get("noi_dung_kws") or [] if norm(k)]
    bb = [norm(k) for k in (p or {}).get("bat_buoc") or [] if norm(k)]
    lt = [norm(k) for k in (p or {}).get("loai_tru") or [] if norm(k)]
    return [i for i, ln in enumerate(dong_norm) if kws and any(k in ln for k in kws) and (not bb or any(k in ln for k in bb))
            and not any(k in ln for k in lt)]


def _doc_ma_e5(bo, kieu, kv, p, lines, dong_norm, tc, ma):
    """Một mã qua bộ trích đã đăng ký → ("doc", giá trị bản ký typed, [chỉ số dòng], trích dẫn) | ("thieu", lý do, một phần[])."""
    if bo == "QUY_TAC_TC":
        it = tc.get(ma) or {}
        v = str(it.get("gia_tri") or "").strip()
        if not v:
            return "thieu", "KHONG_THAY_GIA_TRI", []
        td = str(it.get("trich_dan") or "")
        ix = [i for i, ln in enumerate(lines) if td and ln[:400] == td]
        if not ix:
            return "thieu", "KHONG_XAC_DINH_VI_TRI", [{"gia_tri_doc": v}]
        if kieu == "text":
            return "doc", (kv if norm(v) == norm(kv) else v), ix, lines[ix[0]]
        if kieu == "ngay":
            m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", v)
            iso = _ngay_iso(m.group(1), m.group(2), m.group(3)) if m else None
            if iso is None:
                return "thieu", "GIA_TRI_KHONG_DUNG_KIEU", [{"gia_tri_doc": v}]
            return "doc", iso, ix, lines[ix[0]]
        return "thieu", "KIEU_KHONG_HO_TRO_BO_TRICH", []
    if bo == "NEO_DONG":
        if kieu not in ("so", "tien", "ngay"):
            return "thieu", "KIEU_KHONG_HO_TRO_BO_TRICH", []
        ix = _dong_neo(dong_norm, p)
        if not ix:
            return "thieu", "KHONG_THAY_DONG_NEO", []
        gap = {}
        for i in ix:
            for tk in _token_e5(dong_norm[i]):
                v = _gia_tri_tu_token(kieu, tk, kv)
                if v is None or (kieu == "so" and (v["don_vi"] is None) != (kv["don_vi"] is None)):
                    continue
                g = gap.setdefault(_canon_e5(v), (v, []))
                if i not in g[1]:
                    g[1].append(i)
        if not gap:
            return "thieu", "KHONG_THAY_GIA_TRI", []
        if len(gap) > 1:
            return "thieu", "NHIEU_GIA_TRI", [{"gia_tri_doc": v, "dong": [i + 1 for i in d]} for v, d in gap.values()]
        v, d = next(iter(gap.values()))
        return "doc", v, d, lines[d[0]]
    if bo == "BANG_DONG":
        if kieu != "bang":
            return "thieu", "KIEU_KHONG_HO_TRO_BO_TRICH", []
        # FIX01: bảng đọc TỪ bản ký — vùng bảng = khối dòng liên tiếp mở đầu bằng nhãn dòng chung của khóa expected (vd 'Đợt'); khóa dòng, thứ tự
        # dòng và từng ô lấy từ chính dòng đọc được. Expected chỉ dùng làm schema (cột/kiểu/nhãn/đơn vị) và để đối chiếu; dòng thừa trong vùng giữ lại.
        cot = kv["cot"]
        if any(x is None for r in kv["dong"] for x in r):
            return "thieu", "KY_VONG_CO_O_NULL", []
        kn = [norm(r[0]).split(" ") for r in kv["dong"]]
        nhan = {k[0] for k in kn}
        if len(nhan) != 1 or any(len(k) < 2 for k in kn):
            return "thieu", "KHONG_XAC_DINH_VUNG_BANG", []   # không có nhãn dòng chung quan sát được → không định vùng
        nhan = nhan.pop()
        ung = [i for i, ln in enumerate(dong_norm) if len(ln.split(" ")) > 1 and ln.split(" ")[0].rstrip(_DAU_BIEN) == nhan]
        if ung and ung[-1] - ung[0] + 1 != len(ung):
            return "thieu", "NHIEU_VUNG_BANG", [{"dong_so": [i + 1 for i in ung]}]
        mau_cot = [next(x for x in (r[j] for r in kv["dong"]) if x is not None) for j in range(1, len(cot))]
        ky_vong = {" ".join(k): r for k, r in zip(kn, kv["dong"])}
        doc, chua, thay, ix_all = [], [], {}, []
        for i in ung:
            t = _tu_bang_e5(lines[i])
            if t is None:
                chua.append({"ly_do": "KHOA_DONG_KHONG_XAC_DINH", "dong_so": i + 1})
                continue
            goc_w, nn = t
            dai = max((len(k) for k in kn if len(nn) >= len(k) and nn[:len(k) - 1] == k[:-1] and nn[len(k) - 1].rstrip(_DAU_BIEN) == k[-1]),
                      default=2)
            if len(goc_w) < dai or not goc_w[dai - 1].strip(_DAU_BIEN):
                chua.append({"ly_do": "KHOA_DONG_KHONG_XAC_DINH", "dong_so": i + 1})
                continue
            khoa = " ".join(goc_w[:dai]).rstrip(_DAU_BIEN)
            kh = norm(khoa)
            thay.setdefault(kh, (khoa, []))[1].append(i)
            r_kv = ky_vong.get(kh)
            mau = list(r_kv[1:]) if r_kv is not None else mau_cot
            o, ly_do = _o_bang_e5(cot, goc_w[dai:], nn[dai:], mau)
            ix_all.append(i)
            if o is None:
                chua.append({"dong": khoa, "ly_do": ly_do, "dong_so": i + 1})
                continue
            doc.append(([khoa] + o, i, kh))
        for khoa, ds in thay.values():
            if len(ds) > 1:
                chua.append({"dong": khoa, "ly_do": "NHIEU_DONG", "dong_so": [i + 1 for i in ds]})
        for k, r in zip(kn, kv["dong"]):
            if " ".join(k) not in thay:
                chua.append({"dong": r[0], "ly_do": "KHONG_THAY_DONG"})
        quan_sat = [r for r, _i, _k in doc]
        if not chua and not gia_tri_e5_hop_le("bang", {"cot": cot, "dong": quan_sat}):
            chua.append({"ly_do": "BANG_DOC_KHONG_HOP_LE"})
        if chua:
            mot_phan = []
            for r, i, kh in doc:
                r_kv = ky_vong.get(kh)
                if r_kv is None:
                    mot_phan.append({"dong": r[0], "ly_do": "DONG_NGOAI_KY_VONG", "gia_tri_ban_ky": r, "dong_so": i + 1})
                elif _canon_e5(r) != _canon_e5(r_kv):
                    mot_phan.append({"dong": r[0], "gia_tri_ky_vong": r_kv, "gia_tri_ban_ky": r, "dong_so": i + 1})
            thu_tu = [kh for _r, _i, kh in doc if kh in ky_vong]
            if thu_tu != [k for k in (" ".join(x) for x in kn) if k in thu_tu]:
                mot_phan.append({"ly_do": "THU_TU_DONG_KHAC", "thu_tu_ban_ky": [r[0] for r, _i, kh in doc if kh in ky_vong]})
            return "thieu", "BANG_CHUA_DU", chua + mot_phan
        return "doc", {"cot": cot, "dong": quan_sat}, ix_all, "\n".join(lines[i] for i in ix_all)
    return "thieu", "CHUA_CO_BO_TRICH", []


def _trang_theo_dong(path, lines):
    """Trang (1-based) của TỪNG dòng văn bản read_pdf, đọc lại theo trang bằng CÙNG thư viện/chuẩn hoá. Ghép lại phải BẰNG đúng các dòng đã dùng;
    lệch/không đọc được → (None, n) — không bịa trang."""
    try:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                trang = [(pg.extract_text() or "") for pg in pdf.pages]
        except ImportError:
            import pypdf
            trang = [(pg.extract_text() or "") for pg in pypdf.PdfReader(path).pages]
    except Exception:  # noqa: BLE001 — không đọc được theo trang → không có vị trí trang
        return None, 0
    out = []
    for n, t in enumerate(trang, 1):
        for ln in t.split("\n"):
            ln = re.sub(r"[ \u00a0]+", " ", ln).strip()
            if not ln or re.fullmatch(r"(trang\s*)?\d{1,3}(\s*/\s*\d{1,3})?", ln, re.I):
                continue
            out.append((n, unicodedata.normalize("NFC", ln)))
    if [x[1] for x in out] != list(lines):
        return None, len(trang)
    return [x[0] for x in out], len(trang)


def _sha_tep_e5(p):
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _g5_tu(meta, nd, lines, trang, params, tc):
    exp = meta["expected"]
    muc = {m["ma"]: m["muc"] for m in meta["catalog_binding"]["mapping"]}
    bo_trich = meta.get("bo_trich") or {}
    p_by = {p["ma"]: p for p in params or []}
    dong_norm = [norm(ln) for ln in lines]

    def vt(i):
        return {"nguon": nd["kieu"], "pdf_sha256": meta["signed_pdf_sha256"], "ocr_docx_sha256": nd["ocr_docx_sha256"],
                "trang": trang[i] if nd["kieu"] == NGUON_PDF else None, "dong": i + 1}
    khop, lech, thieu = [], [], []
    for t in exp["tham_so"]:
        ma, kieu, kv = t["ma"], t["kieu"], t["gia_tri"]
        goc = {"ma": ma, "muc": muc[ma], "kieu": kieu}
        bt = bo_trich.get(ma)
        if nd["kieu"] is None:
            kq = ("thieu", "KHONG_DOC_DUOC_NGUON", [])
        elif not bt:
            kq = ("thieu", "CHUA_CO_BO_TRICH", [])
        elif bt[1] != kieu:
            kq = ("thieu", "KIEU_KHAC_BO_TRICH", [{"kieu_bo_trich": bt[1]}])
        else:
            try:
                kq = _doc_ma_e5(bt[0], kieu, kv, p_by.get(ma), lines, dong_norm, tc or {}, ma)
            except Exception as e:  # noqa: BLE001 — lỗi bộ trích của MỘT mã → chưa đối chiếu được mã đó, không KHỚP
                kq = ("thieu", "LOI_BO_TRICH", [{"loi": type(e).__name__}])
        if kq[0] == "thieu":
            thieu.append({**goc, "ly_do": kq[1], "gia_tri_ky_vong": kv, "mot_phan": kq[2]})
            continue
        _, v, ix, td = kq
        if _canon_e5(v) == _canon_e5(kv):
            khop.append({**goc, "gia_tri": kv, "trich_dan": td, "vi_tri_do_duoc": [vt(i) for i in ix]})
        else:
            lech.append({**goc, "gia_tri_ky_vong": kv, "gia_tri_ban_ky": v, "trich_dan": td, "vi_tri_do_duoc": [vt(i) for i in ix]})
    tt = "CHUA_DOI_CHIEU_DUOC" if thieu else ("LECH" if lech else "KHOP")
    return {"kieu": KIEU_G5, "source_sha256": meta["source_sha256"], "signed_pdf_sha256": meta["signed_pdf_sha256"],
            "expected_sha256": meta["expected_sha256"], "catalog_binding_sha256": meta["catalog_binding_sha256"],
            "g3_pdf_sha256": meta["g3_pdf_sha256"], "coverage": [t["ma"] for t in exp["tham_so"]], "trang_thai": tt,
            "khop": khop, "lech": lech, "thieu": thieu, "nguon_doc": nd}


def doi_chieu_e5(meta, params, path_goc, info, ocr, path_doc, tc):
    """g5 cho một PDF ký: nguồn đọc truy về ĐÚNG bytes PDF ký (SHA = signed_pdf_sha256); lớp chữ PDF → vị trí trang+dòng; OCR ABBYY → vị trí dòng trong
    DOCX OCR (ghi SHA DOCX OCR, KHÔNG có trang). Mỗi mã expected qua bộ trích đã đăng ký → khop/lech/thieu typed."""
    nd = {"kieu": None, "pdf_sha256": meta["signed_pdf_sha256"], "ocr_docx_sha256": None, "so_trang": None, "loi": None}
    lines = info["text"].split("\n")
    trang = None
    if _sha_tep_e5(path_goc) != meta["signed_pdf_sha256"]:
        nd["loi"] = "PDF_KHAC_SHA_BAN_KY"
    elif ocr is None:
        trang, so_trang = _trang_theo_dong(path_goc, lines)
        if trang is None or not _la_int(so_trang, 1):
            trang, nd["loi"] = None, "VI_TRI_TRANG_KHONG_TIN_CAY"
        else:
            nd.update(kieu=NGUON_PDF, so_trang=so_trang)
    else:
        h = _sha_tep_e5(path_doc)
        if h is None:
            nd["loi"] = "OCR_DOCX_KHONG_DOC_DUOC"
        else:
            nd.update(kieu=NGUON_OCR, ocr_docx_sha256=h, so_trang=ocr.get("trang") if _la_int(ocr.get("trang"), 1) else None)
    return _g5_tu(meta, nd, lines if nd["kieu"] else [], trang, params, tc)


def g5_khong_doc_duoc(meta, loi):
    """g5 khi không đọc được PDF ký: mọi mã CHUA_DOI_CHIEU_DUOC, không vị trí/trang."""
    nd = {"kieu": None, "pdf_sha256": meta["signed_pdf_sha256"], "ocr_docx_sha256": None, "so_trang": None, "loi": str(loi or "KHONG_DOC_DUOC")}
    return _g5_tu(meta, nd, [], None, [], {})


def kiem_g5_e5(g5, req):
    """Kiểm g5 của raw so với request.json đã chụp (nguồn dùng TRƯỚC niêm phong và khi kiểm lại seal): SHA vai trò, coverage = mã expected theo thứ tự,
    mỗi mã đúng một nhóm với kiểu = expected, mức = binding = catalog ghim, giá trị kỳ vọng = expected canonical, khop/lech có trích dẫn + vị trí truy
    về PDF ký, trạng thái nhất quán. Sai → LoiE5."""
    def sai(ly_do):
        return LoiE5("E5_G5_SAI", ly_do)
    if not isinstance(g5, dict) or set(g5) != _KHOA_G5 or g5.get("kieu") != KIEU_G5:
        raise sai("kiểu/khóa g5")
    if (g5["source_sha256"], g5["signed_pdf_sha256"], g5["expected_sha256"], g5["catalog_binding_sha256"], g5["g3_pdf_sha256"]) != \
            (req["source_sha256"], req["signed_pdf_sha256"], req["expected_sha256"], req["catalog_binding_sha256"], req["g3_pdf_sha256"]):
        raise sai("SHA vai trò")
    ky_vong = {t["ma"]: t for t in req["expected"]["tham_so"]}
    ma_exp = [t["ma"] for t in req["expected"]["tham_so"]]
    if g5["coverage"] != ma_exp:
        raise sai("coverage")
    muc = {m["ma"]: m["muc"] for m in req["catalog_binding"]["mapping"]}
    if any(req.get("muc_ghim", {}).get(m) != muc[m] for m in ma_exp):
        raise sai("mức binding khác catalog ghim")
    nd = g5["nguon_doc"]
    if not isinstance(nd, dict) or set(nd) != _KHOA_NGUON_DOC or nd["pdf_sha256"] != req["signed_pdf_sha256"] or \
            nd["kieu"] not in (None, NGUON_PDF, NGUON_OCR) or (nd["loi"] is not None and (not isinstance(nd["loi"], str) or not nd["loi"])):
        raise sai("nguon_doc")
    if nd["kieu"] == NGUON_PDF and (not _la_int(nd["so_trang"], 1) or nd["ocr_docx_sha256"] is not None):
        raise sai("nguon_doc PDF")
    if nd["kieu"] == NGUON_OCR and (not isinstance(nd["ocr_docx_sha256"], str) or not _RE_HEX64.fullmatch(nd["ocr_docx_sha256"])
                                    or (nd["so_trang"] is not None and not _la_int(nd["so_trang"], 1))):
        raise sai("nguon_doc OCR")
    if nd["kieu"] is None and (nd["so_trang"] is not None or nd["ocr_docx_sha256"] is not None or nd["loi"] is None):
        raise sai("nguon_doc không đọc được")

    def vi_tri_ok(v):
        return isinstance(v, list) and bool(v) and all(
            isinstance(x, dict) and set(x) == _KHOA_VI_TRI and x["nguon"] == nd["kieu"] and x["pdf_sha256"] == req["signed_pdf_sha256"]
            and x["ocr_docx_sha256"] == nd["ocr_docx_sha256"] and _la_int(x["dong"], 1)
            and (_la_int(x["trang"], 1, nd["so_trang"]) if nd["kieu"] == NGUON_PDF else x["trang"] is None) for x in v)
    da = []
    for nhom, khoa in (("khop", _KHOA_G5_KHOP), ("lech", _KHOA_G5_LECH), ("thieu", _KHOA_G5_THIEU)):
        if not isinstance(g5[nhom], list):
            raise sai(f"{nhom} không phải mảng")
        for it in g5[nhom]:
            if not isinstance(it, dict) or set(it) != khoa or not isinstance(it["ma"], str) or it["ma"] not in ky_vong or it["ma"] in da:
                raise sai(f"mục {nhom} sai khóa/mã lạ/trùng")
            m = it["ma"]
            da.append(m)
            kv = ky_vong[m]
            if it["kieu"] != kv["kieu"] or not _la_int(it["muc"], 0, 3) or it["muc"] != muc[m]:
                raise sai(f"{m}: kiểu/mức")
            if nhom == "khop":
                ok = nd["kieu"] is not None and gia_tri_e5_hop_le(kv["kieu"], it["gia_tri"]) and \
                    _canon_e5(it["gia_tri"]) == _canon_e5(kv["gia_tri"]) and isinstance(it["trich_dan"], str) and it["trich_dan"].strip() \
                    and vi_tri_ok(it["vi_tri_do_duoc"])
            elif nhom == "lech":
                ok = nd["kieu"] is not None and gia_tri_e5_hop_le(kv["kieu"], it["gia_tri_ban_ky"]) and \
                    gia_tri_e5_hop_le(kv["kieu"], it["gia_tri_ky_vong"]) and _canon_e5(it["gia_tri_ky_vong"]) == _canon_e5(kv["gia_tri"]) and \
                    _canon_e5(it["gia_tri_ban_ky"]) != _canon_e5(kv["gia_tri"]) and isinstance(it["trich_dan"], str) and \
                    it["trich_dan"].strip() and vi_tri_ok(it["vi_tri_do_duoc"])
            else:
                ok = isinstance(it["ly_do"], str) and it["ly_do"].strip() and gia_tri_e5_hop_le(kv["kieu"], it["gia_tri_ky_vong"]) and \
                    _canon_e5(it["gia_tri_ky_vong"]) == _canon_e5(kv["gia_tri"]) and isinstance(it["mot_phan"], list) and \
                    all(isinstance(x, dict) for x in it["mot_phan"])
            if not ok:
                raise sai(f"{m}: nội dung mục {nhom}")
    if sorted(da) != sorted(ma_exp):
        raise sai("coverage không đủ")
    if g5["trang_thai"] != ("CHUA_DOI_CHIEU_DUOC" if g5["thieu"] else ("LECH" if g5["lech"] else "KHOP")):
        raise sai("trang_thai không nhất quán")
    return g5
