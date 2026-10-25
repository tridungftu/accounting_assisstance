# -*- coding: utf-8 -*-
"""Engine #6: giao diện MayAI qua cổng AI dùng chung (TL 48).

Cổng quyết định Local/Cloud, che và mở che bằng Mask v2, kiểm trích dẫn trên
văn bản gốc và ghi metadata. Engine không giữ khóa hay nhật ký văn bản gửi ngoài.
"""
import re
import threading

from kho_tri_thuc.tri_thuc.cong_ai import YeuCauAI

from .ai_local import SYSTEM, AILoi, DaDung
from .cloud import tao_cong_ai, trang_thai_cloud

TEN = "AI qua cổng dùng chung"


class MayCloud:
    la_cloud = True

    def __init__(self, nha_cung_cap="anthropic", model="", ghi_log=None, dung=None, nhat_ky=None, timeout=300,
                 *, cong_ai=None, settings=None, bo_ghi=None):
        self.cong_ai = cong_ai if cong_ai is not None else tao_cong_ai(settings, bo_ghi)
        cfg = self.cong_ai.cai_dat
        self.ncc = cfg.get("nha_cung_cap") or nha_cung_cap
        self.model = cfg.get("model") or model
        self.url = "cong-ai"
        self.ten = TEN
        self.ghi_log = ghi_log or (lambda m: None)
        self.dung = dung
        self.timeout = timeout  # tương thích bên gọi; timeout thực tế do cổng quản lý
        self.nhat_ky = nhat_ky  # tương thích quy_trinh; không ghi GUI_RA_NGOAI_*.txt
        self.khong_think = True
        # KetQuaAI không trả token; không suy đoán usage từ nội dung hay nhật ký dùng chung.
        self.tok_vao = self.tok_ra = self.so_lan_goi = 0
        self.so_khong_gui = 0
        self.dinh_danh = ()

    def models(self, timeout=8):
        self._san_sang()
        return [self.model]

    def think(self):
        return None

    def dat_dinh_danh(self, thong_tin):
        """Chuyển nhãn nguồn sang nhóm Mask v2; không tự che hay giữ bảng bí danh."""
        nhom = {"BEN_A": "CONG_TY", "BEN_B": "CONG_TY", "SO_HD": "HOP_DONG", "SO_TK": "TAI_KHOAN",
                "MST": "MA_SO_THUE", "DIA_DIEM": "DIA_CHI", "DU_AN": "DU_AN", "GOI_THAU": "DU_AN",
                "TEN_NGUOI": "CA_NHAN", "SDT": "DIEN_THOAI", "EMAIL": "EMAIL"}
        self.dinh_danh = tuple((v.strip(), nhom.get(k, "KHAC"))
                              for k, vs in (thong_tin or {}).items() for v in (vs or [])
                              if isinstance(v, str) and v.strip())

    def _san_sang(self):
        if self.dung is not None and self.dung.is_set():
            raise DaDung()
        st = trang_thai_cloud(self.cong_ai)
        if not st["dung_duoc"]:
            raise AILoi(st["thong_bao"])

    def _goi(self, yeu_cau):
        """Chỉ gọi CongAI.goi; giữ nút Dừng như giao diện nguồn."""
        self._san_sang()
        if not isinstance(yeu_cau, YeuCauAI):
            raise AILoi("Yêu cầu AI phải đi qua cổng AI dùng chung.")
        kq = {}

        def chay():
            try:
                kq["ok"] = self.cong_ai.goi(yeu_cau)
            except BaseException as exc:  # noqa: BLE001 — chuyển lỗi về luồng chính
                kq["loi"] = exc

        t = threading.Thread(target=chay, daemon=True)
        t.start()
        while t.is_alive():
            t.join(0.5)
            if self.dung is not None and self.dung.is_set():
                raise DaDung()
        if "loi" in kq:
            # Không đưa chi tiết ngoại lệ có thể chứa văn bản/khóa vào GUI.
            raise AILoi("Cổng AI chưa xử lý được yêu cầu.") from None
        self.so_lan_goi += 1
        self.ket_qua_cuoi = kq["ok"]
        # Chỉ các mã chặn TRƯỚC nhà cung cấp mới là không gửi; phản hồi sai
        # hoặc mở che thất bại đều đã gửi Cloud, dù không còn trường hợp lệ.
        chan_truoc_gui = {"CLOUD_TAT", "LOAI_VIEC_KHONG_DUNG_CLOUD", "CAI_DAT_CLOUD_LOI",
                          "CHUA_CO_KHOA_API", "CHUA_CO_KHOA_MASK", "XML_HOA_DON_THO",
                          "QUA_NHIEU_DINH_DANH", "CON_SOT_DINH_DANH"}
        if any(ma in chan_truoc_gui or (ma.startswith("MASK_") and ma != "MASK_MO_CHE_LOI")
               for ma in self.ket_qua_cuoi.ly_do):
            self.so_khong_gui += 1
        if not self.ket_qua_cuoi.truong:
            raise AILoi(self.ket_qua_cuoi.thong_bao)
        return self.ket_qua_cuoi

    def chat_json(self, prompt, schema, key, num_ctx=None, what="AI"):
        """Thích nghi ket_qua/vi_tri sang truong; cổng trả các trường đã kiểm trên bản gốc."""
        self._san_sang()
        if key not in ("ket_qua", "vi_tri"):
            raise AILoi("Cổng AI chỉ hỗ trợ trích tham số hoặc tìm vị trí hợp đồng.")
        moc = "CÁC ĐOẠN HỢP ĐỒNG:" if key == "ket_qua" else "MỤC LỤC HỢP ĐỒNG:"
        dau, co_moc, van_ban = prompt.partition(moc)
        if not co_moc:
            dau, van_ban = "", prompt
        tham_so = re.findall(r"^- ([A-Z]+-\d+)\s*\|\s*(.+)$", dau, re.M)
        ma = tuple(dict.fromkeys(m for m, _ in tham_so))
        chi_dan = (SYSTEM + "\nTHAM SỐ:\n" + "\n".join(f"- {m} | {mt}" for m, mt in tham_so)
                   + "\nDùng định dạng truong của cổng AI; ten là mã tham số, không dùng ket_qua/vi_tri.")
        if key == "vi_tri":
            chi_dan += (" Với mỗi tham số chọn một ID mục phù hợp nhất làm gia_tri. "
                        "trich_dan là nguyên dòng mục lục chứa ID đó.")
        yc = YeuCauAI("BOC_TACH_HOP_DONG", van_ban.strip(), chi_dan, ma, self.dinh_danh)
        kq = self._goi(yc)
        if key == "vi_tri":
            # Chỉ nhận ID có thật ở đầu dòng, không nhận ID do model tự đặt.
            ids = set(re.findall(r"^([^\s|]+)\s*\|", van_ban, re.M))
            data = [{"ma": t.ten, "ids": [t.gia_tri]} for t in kq.truong.values() if t.gia_tri in ids]
        else:
            data = [{"ma": t.ten, "gia_tri": t.gia_tri, "trich_dan": t.trich_dan,
                     "don_vi": "", "dieu_khoan": "", "ghi_chu": ""} for t in kq.truong.values()]
        return {key: data}, 0, 0

    def hoi_trich(self, prompt, what="AI"):
        from .ai_local import CTX_TRICH, SCHEMA_TRICH
        data, tin, tout = self.chat_json(prompt, SCHEMA_TRICH, "ket_qua", CTX_TRICH, what)
        return data["ket_qua"], tin, tout


def thong_tin_tu_tham_so(ts):
    """{mã TC: giá trị} (CSDL hoặc quy tắc) → định danh đã biết gửi cổng AI."""
    g = lambda m: str(ts.get(m) or "").strip()  # noqa: E731
    return {"SO_HD": [g("TC-01")], "GOI_THAU": [g("TC-03")], "DU_AN": [g("TC-04")], "DIA_DIEM": [g("TC-05")],
            "BEN_A": [g("TC-06")], "BEN_B": [g("TC-07")]}


def dat_che_theo_hd(ai, con, ma_hd):
    """Lấy định danh hợp đồng cho cổng; Local AI không có dat_dinh_danh thì bỏ qua."""
    if not hasattr(ai, "dat_dinh_danh") or not ma_hd:
        return
    ts = {r[0]: r[1] for r in con.execute("SELECT ma_ts, gia_tri FROM tham_so WHERE ma_hd = ? AND ma_ts LIKE 'TC-%'",
                                          (ma_hd,))}
    r = con.execute("SELECT so_hd FROM hop_dong WHERE ma_hd = ?", (ma_hd,)).fetchone()
    if r and r[0]:
        ts.setdefault("TC-01", r[0])
    ai.dat_dinh_danh(thong_tin_tu_tham_so(ts))
