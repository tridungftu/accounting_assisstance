# -*- coding: utf-8 -*-
"""
ai_cloud.py — Claude (hoặc OpenAI) thay máy Local AI khi máy AI không bật được — anh chọn trong Cài đặt → Nguồn AI.

Cùng giao diện với ai_local.MayAI (chat_json, hoi_trich, models, tok_vao/tok_ra…) để trích hợp đồng, phụ lục, chứng từ
chạy không phải sửa từng màn. Quy tắc gửi ra ngoài:
  • che thông tin định danh trước khi gửi (AnDanh: tên các bên, công ty, dự án, gói thầu, địa điểm, số HĐ, MST, số tài
    khoản, điện thoại, email, người đại diện); câu hỏi còn sót định danh sau khi che → KHÔNG gửi, báo lỗi cho câu đó;
  • kết quả trả về được mở che trên máy này rồi Python kiểm trích dẫn nguyên văn như với Local AI;
  • mỗi câu hỏi ghi vào nhật ký GUI_RA_NGOAI_*.txt (đúng văn bản đã gửi, không ghi khoá API);
  • bên gọi tự bảo đảm chỉ đưa vào các Khoản liên quan (không Phần mở đầu / toàn văn).
"""
import datetime
import json
import os
import threading

from .ai_local import JSON_NHAC, SYSTEM, AILoi, DaDung, parse_json
from .cau_hinh import CLOUD_MODEL_MAC_DINH, doc_khoa
from .cloud import CLOUD_TAM_KHOA, AnDanh, CloudLoi, goi_api

TEN = "Claude (che định danh)"
NHAC_CHE = ("\n\nMột số thông tin định danh đã được thay bằng nhãn trong ngoặc vuông như [BEN_A], [CONG_TY_1], [SO_HD_1] "
            "— giữ nguyên các nhãn đó khi trích dẫn, không đoán nội dung thật.")


class MayCloud:
    la_cloud = True

    def __init__(self, nha_cung_cap="anthropic", model="", ghi_log=None, dung=None, nhat_ky=None, timeout=300):
        self.ncc = (nha_cung_cap or "anthropic").lower()
        self.model = model or CLOUD_MODEL_MAC_DINH.get(self.ncc, "")
        self.url = f"cloud:{self.ncc}"
        self.ten = TEN if self.ncc == "anthropic" else f"{self.ncc} (che định danh)"
        self.ghi_log = ghi_log or (lambda m: None)
        self.dung = dung
        self.timeout = timeout
        self.nhat_ky = nhat_ky
        self.khong_think = True
        self.tok_vao = self.tok_ra = self.so_lan_goi = 0
        self.so_khong_gui = 0
        self.an = AnDanh({})
        self._khoa = None

    # ---------------------------------------------------------------- tương thích MayAI
    def models(self, timeout=8):
        # AI-0 25/10/2026 (TL 48): nguồn Cloud không khả dụng, không đọc khóa.
        raise AILoi(CLOUD_TAM_KHOA)

        if not doc_khoa(self.ncc):
            raise AILoi(f"Chưa có API key {self.ncc} — vào Cài đặt → Kiểm tra chéo cloud để nhập")
        return [self.model]

    def think(self):
        return None

    def dat_dinh_danh(self, thong_tin):
        """thong_tin: {nhãn: [chuỗi cần che]} — vd {'BEN_A': ['Công ty …'], 'SO_HD': ['12/2026/HĐXD/…']}."""
        self.an = AnDanh({k: [v for v in (vs or []) if v] for k, vs in (thong_tin or {}).items()})

    def _mo(self, x):
        if isinstance(x, str):
            return self.an.mo(x)
        if isinstance(x, list):
            return [self._mo(v) for v in x]
        if isinstance(x, dict):
            return {k: self._mo(v) for k, v in x.items()}
        return x

    def _ghi(self, what, van_ban, ghi_chu=""):
        if not self.nhat_ky:
            return
        try:
            os.makedirs(os.path.dirname(self.nhat_ky), exist_ok=True)
            moi = not os.path.exists(self.nhat_ky)
            with open(self.nhat_ky, "a", encoding="utf-8") as f:
                if moi:
                    f.write(f"NHẬT KÝ GỬI RA NGOÀI — nguồn AI: {self.ten}\nNhà cung cấp: {self.ncc} | model: {self.model}\n"
                            "Khoá API: (không ghi)\nMọi văn bản dưới đây đã được che định danh trước khi gửi.\n")
                f.write(f"\n===== {datetime.datetime.now():%d/%m/%Y %H:%M:%S} · {what}" + (f" · {ghi_chu}" if ghi_chu else "")
                        + " =====\n" + (van_ban or "(không gửi)") + "\n")
        except OSError:
            pass

    def _goi(self, prompt):
        """Gọi API trong luồng phụ để nút Dừng có hiệu lực ngay."""
        raise AILoi(CLOUD_TAM_KHOA)

        kq = {}

        def chay():
            try:
                kq["ok"] = goi_api(self.ncc, self.model, self._khoa, prompt, timeout=self.timeout,
                                   system=SYSTEM + NHAC_CHE, max_tokens=8192)
            except BaseException as e:  # noqa: BLE001
                kq["loi"] = e
        t = threading.Thread(target=chay, daemon=True)
        t.start()
        while t.is_alive():
            t.join(0.5)
            if self.dung is not None and self.dung.is_set():
                raise DaDung()
        if "loi" in kq:
            e = kq["loi"]
            raise AILoi(str(e)) if isinstance(e, CloudLoi) else e
        return kq["ok"]

    def chat_json(self, prompt, schema, key, num_ctx=None, what="AI"):
        """Trả (data đã mở che, token_vào, token_ra). Còn định danh sau khi che → AILoi (không gửi)."""
        # Chặn trước cả đọc khóa/che/ghi file; hoi_trich cũng đi qua điểm này.
        raise AILoi(CLOUD_TAM_KHOA)

        if self.dung is not None and self.dung.is_set():
            raise DaDung()
        self._khoa = self._khoa or doc_khoa(self.ncc)
        if not self._khoa:
            raise AILoi(f"Chưa có API key {self.ncc} — vào Cài đặt → Kiểm tra chéo cloud để nhập")
        che = self.an.che(prompt)
        vet = self.an.dau_vet(che)
        if vet:
            self.so_khong_gui += 1
            self._ghi(what, None, "KHÔNG GỬI — còn định danh: " + "; ".join(vet[:5]))
            raise AILoi(f"Không gửi {self.ten}: còn thông tin định danh sau khi che ({'; '.join(vet[:3])})")
        gui = che + NHAC_CHE + "\n\nTrả về DUY NHẤT một JSON đúng schema: " + json.dumps(schema, ensure_ascii=False)
        tin = tout = 0
        for lan in range(2):
            noi_dung = gui + (JSON_NHAC if lan else "")
            self._ghi(what + (" (hỏi lại)" if lan else ""), noi_dung)
            txt, pi, po, _ = self._goi(noi_dung)
            self.so_lan_goi += 1
            tin += pi or 0
            tout += po or 0
            self.tok_vao += pi or 0
            self.tok_ra += po or 0
            data = parse_json(txt, key)
            if data is not None:
                return self._mo(data), tin, tout
            self.ghi_log(f"{self.ten} trả JSON không hợp lệ ({what})" + (" — hỏi lại" if not lan else ""))
        raise AILoi(f"{self.ten} trả JSON không hợp lệ sau 2 lần")

    def hoi_trich(self, prompt, what="AI"):
        from .ai_local import CTX_TRICH, SCHEMA_TRICH
        data, tin, tout = self.chat_json(prompt, SCHEMA_TRICH, "ket_qua", CTX_TRICH, what)
        return [x for x in data["ket_qua"] if isinstance(x, dict)], tin, tout


def thong_tin_tu_tham_so(ts):
    """{mã TC: giá trị} (CSDL hoặc quy tắc) → thong_tin cho AnDanh."""
    g = lambda m: str(ts.get(m) or "").strip()  # noqa: E731
    return {"SO_HD": [g("TC-01")], "GOI_THAU": [g("TC-03")], "DU_AN": [g("TC-04")], "DIA_DIEM": [g("TC-05")],
            "BEN_A": [g("TC-06")], "BEN_B": [g("TC-07")]}


def dat_che_theo_hd(ai, con, ma_hd):
    """Nguồn AI là Claude: lấy số HĐ + thông tin chung (TC-xx) của hợp đồng trong CSDL để che trước khi gửi.
    Local AI (không có dat_dinh_danh) → bỏ qua."""
    if not hasattr(ai, "dat_dinh_danh") or not ma_hd:
        return
    ts = {r[0]: r[1] for r in con.execute("SELECT ma_ts, gia_tri FROM tham_so WHERE ma_hd = ? AND ma_ts LIKE 'TC-%'",
                                          (ma_hd,))}
    r = con.execute("SELECT so_hd FROM hop_dong WHERE ma_hd = ?", (ma_hd,)).fetchone()
    if r and r[0]:
        ts.setdefault("TC-01", r[0])
    ai.dat_dinh_danh(thong_tin_tu_tham_so(ts))
