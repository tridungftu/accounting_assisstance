# -*- coding: utf-8 -*-
"""
quy_trinh.py — Xử lý MỘT hợp đồng theo 9 bước của phương pháp v3 (xem __init__.py).

    tx = TrichXuat(params, ai=MayAI(url, model), out_dir=..., ra_lai=True, cloud=None)
    kq = tx.xu_ly("hop_dong.docx")        # dict: bang (37 dòng), phieu, tom_tat, tep

tien_do(buoc, mo_ta, ty_le_trong_hd) được gọi ở mỗi mốc để giao diện hiện tiến độ; ghi_log(msg) ghi nhật ký
(không ghi nội dung hợp đồng). dung = threading.Event: bấm Dừng → DaDung.
"""
import copy as _copy                  # E3-01: alias — xu_ly có `import copy` cục bộ (khối meta) nên tên `copy` là biến cục bộ trong hàm
import datetime
import os
import re
import time

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

        # 1. đọc file
        self.tien_do(0, "Đọc file" + (" (.doc → chuyển bằng Word)" if path.lower().endswith(".doc") else ""), 0.01)
        ocr = None
        path_goc = path                       # E3-01: file đầu vào gốc (PDF trước OCR) cho bang_nguon
        if path.lower().endswith(".pdf"):
            path, ocr = self.ocr_pdf(path, file)
        info = read_contract(path)
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
        kq["tom_tat"]["so_can_xem"] = sum(1 for d in bang if not la_ok(d["kiem_tra"]))
        kq["tom_tat"]["so_da_xac_nhan"] = 0
        ghi_ket_qua_hd(kq, out)
        self.ghi_log(f"  xong {file} | {n_ok}/{len(bang)} OK" + (f" | đáp án {n_key}/{n_keyed}" if key else "")
                     + f" | {dt:.0f}s | lỗi AI: {n_err}")
        return kq
