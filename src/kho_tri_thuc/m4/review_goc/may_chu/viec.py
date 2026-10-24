# -*- coding: utf-8 -*-
"""
viec.py — Quản lý các việc chạy nền (trích hợp đồng, tìm máy AI, kiểm tra toàn vẹn, kiểm tra đợt…).

- Việc dùng máy AI (trích hợp đồng) xếp HÀNG, chạy lần lượt từng việc (máy AI chỉ có 1 GPU).
- Việc khác chạy ngay trong luồng riêng.
- Mỗi việc có: trạng thái (cho / dang_chay / xong / loi / da_dung), % tiến độ, thông báo, nhật ký, nút Dừng.
"""
import itertools
import queue
import threading
import time
import traceback

_dem = itertools.count(1)


class Viec:
    def __init__(self, loai, ten, ham, dung_ai=False, id_=None):
        self.id = id_ or f"{loai}-{time.strftime('%Y%m%d%H%M%S')}-{next(_dem)}"
        self.loai, self.ten, self.ham, self.dung_ai = loai, ten, ham, dung_ai
        self.tt, self.pct, self.thong_bao, self.loi = "cho", 0.0, "", ""
        self.ket_qua = None
        self.tao_luc, self.bat_dau, self.ket_thuc = time.time(), None, None
        self.dung = threading.Event()
        self.nhat_ky = []
        self.chi_tiet = None          # hàm trả trạng thái chi tiết (vd LuotChay.trang_thai)
        self.lock = threading.Lock()

    def log(self, msg):
        with self.lock:
            self.nhat_ky.append([time.time(), msg])
            self.nhat_ky = self.nhat_ky[-300:]

    def tien_do(self, pct, thong_bao=None):
        self.pct = max(0.0, min(1.0, float(pct)))
        if thong_bao is not None:
            self.thong_bao = thong_bao

    def chay(self):
        self.tt, self.bat_dau = "dang_chay", time.time()
        try:
            kq = self.ham(self)
            if self.dung.is_set() and self.tt == "dang_chay":
                self.tt = "da_dung"
            elif self.tt == "dang_chay":
                self.tt = "xong"
                self.pct = 1.0
            self.ket_qua = kq
        except SystemExit as e:              # csdl_hop_dong báo lỗi người dùng bằng SystemExit
            self.tt, self.loi = "loi", str(e)
        except Exception as e:  # noqa: BLE001
            self.tt, self.loi = "loi", f"{type(e).__name__}: {e}"
            self.log(traceback.format_exc()[-1500:])
        finally:
            self.ket_thuc = time.time()

    def to_dict(self, day_du=False):
        d = {"id": self.id, "loai": self.loai, "ten": self.ten, "tt": self.tt, "pct": round(self.pct, 4),
             "thong_bao": self.thong_bao, "loi": self.loi, "tao_luc": self.tao_luc, "bat_dau": self.bat_dau,
             "ket_thuc": self.ket_thuc, "dang_cho_ai": self.dung_ai and self.tt == "cho"}
        if self.chi_tiet:
            try:
                ct = self.chi_tiet()
                d["pct"] = ct.get("pct", d["pct"])
                if ct.get("thong_bao"):
                    d["thong_bao"] = ct["thong_bao"]
                if day_du:
                    d["chi_tiet"] = ct
            except Exception:  # noqa: BLE001
                pass
        if day_du:
            d["ket_qua"] = self.ket_qua
            with self.lock:
                d["nhat_ky"] = list(self.nhat_ky)
        return d


class QuanLyViec:
    def __init__(self):
        self.ds = {}
        self.lock = threading.Lock()
        self.hang_doi = queue.Queue()
        threading.Thread(target=self._tho_ai, daemon=True).start()

    def _tho_ai(self):
        while True:
            v = self.hang_doi.get()
            if v.dung.is_set():
                v.tt, v.ket_thuc = "da_dung", time.time()
                continue
            v.chay()

    def tao(self, loai, ten, ham, dung_ai=False, id_=None, chi_tiet=None, dung=None):
        v = Viec(loai, ten, ham, dung_ai, id_)
        v.chi_tiet = chi_tiet
        if dung is not None:
            v.dung = dung
        with self.lock:
            self.ds[v.id] = v
        if dung_ai:
            self.hang_doi.put(v)
        else:
            threading.Thread(target=v.chay, daemon=True).start()
        return v

    def lay(self, id_):
        v = self.ds.get(id_)
        if not v:
            raise KeyError(f"Không có việc {id_}")
        return v

    def danh_sach(self):
        with self.lock:
            return [v.to_dict() for v in sorted(self.ds.values(), key=lambda x: -x.tao_luc)]

    def dang_chay(self):
        return [v for v in self.ds.values() if v.tt in ("cho", "dang_chay")]

    def dung(self, id_):
        v = self.lay(id_)
        v.dung.set()
        if v.tt == "cho":
            v.tt = "da_dung"
        return v.to_dict()
