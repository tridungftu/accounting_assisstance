# -*- coding: utf-8 -*-
"""
lo.py — Chạy một LƯỢT trích xuất cho nhiều hợp đồng (dùng chung cho giao diện web và dòng lệnh).

    luot = LuotChay(files, out_dir, params, url, model, ra_lai=True, cloud=None)
    luot.chay()            # cập nhật luot.s (trạng thái để giao diện đọc) trong lúc chạy

- Kiểm tra kết nối máy AI + model trước; không có AI và chi_cau_truc=True → vẫn tách cấu trúc + dò vị trí.
- HĐ đã trích trước đây với CÙNG nội dung file, danh mục tham số, model, tuỳ chọn → dùng lại kết quả (nhanh),
  trừ khi chay_lai=True (biến môi trường HD_CHAY_LAI=1). HĐ có lỗi AI không được lưu để lần sau tự chạy lại.
- Mỗi HĐ xong → cập nhật DANH_MUC_HD\\DANH_MUC_HOP_DONG.xlsx; hết lượt → TONG_HOP_<lượt>_<model>.xlsx/.json.
- Nhật ký: nhat_ky_<lượt>.txt (tên file, token, thời gian, lỗi — KHÔNG ghi nội dung hợp đồng).
"""
import datetime
import hashlib
import json
import os
import shutil
import threading
import time

from .ai_local import AILoi, DaDung, MayAI
from .cau_hinh import MAU_DANH_MUC_HD, file_danh_muc_hd, thu_muc_ket_qua
from .quy_trinh import BUOC, TrichXuat, ten_an_toan
from .xuat import can_xem, ghi_danh_muc, ghi_tong_hop

CHO, DANG, XONG, XONG_VANG, LOI, BO_QUA, DUNG = ("Chờ", "Đang chạy", "Xong", "Xong có ô vàng", "Lỗi",
                                                  "Bỏ qua (dùng kết quả cũ)", "Đã dừng")


def _la_model_chat(name):
    import re
    return not re.search(r"bge|embed|minilm|nomic", name or "", re.I)


class LuotChay:
    def __init__(self, files, out_dir, params, url, model, ra_lai=True, cloud=None, chay_lai=False, chi_cau_truc=False,
                 thu_muc_dap_an=None, timeout=1800, dung=None, ghi_danh_muc_hd=True, nhan_luot=None, nguon_ai=None):
        self.files = list(files)
        self.nguon_ai = nguon_ai                  # None = máy Local AI; {"nha_cung_cap","model"} = Claude (che định danh)
        self.out_dir = str(out_dir)
        self.params = params
        self.url, self.model = url, model
        self.ra_lai, self.cloud, self.chay_lai, self.chi_cau_truc = ra_lai, cloud, chay_lai, chi_cau_truc
        self.thu_muc_dap_an = thu_muc_dap_an
        self.timeout = timeout
        self.dung = dung or threading.Event()
        self.ghi_dm = ghi_danh_muc_hd
        self.nhan = nhan_luot or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.lock = threading.Lock()
        os.makedirs(self.out_dir, exist_ok=True)
        self.nhat_ky = os.path.join(self.out_dir, f"nhat_ky_{self.nhan}.txt")
        self.s = {"tt": "cho", "bat_dau": time.time(), "ket_thuc": None, "model": model, "may_ai": url,
                  "dung_ai": None, "thong_bao": "", "pct": 0.0, "buoc_ten": BUOC,
                  "hd": [{"file": os.path.basename(f), "tt": CHO, "pct": 0.0, "buoc": -1, "mo_ta": "", "bat_dau": None,
                          "thoi_gian": None, "so_ok": None, "so_vang": None, "dung_dap_an": "", "loi": "", "ten": "",
                          "canh_bao": []} for f in self.files],
                  "log": [], "tep": {}, "danh_muc": ""}

    # ---------------------------------------------------------------- nhật ký / tiến độ
    def log(self, msg):
        with self.lock:
            self.s["log"].append([time.time(), msg])
            self.s["log"] = self.s["log"][-400:]
        try:
            with open(self.nhat_ky, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now():%H:%M:%S} | {msg}\n")
        except OSError:
            pass

    def _cap_nhat(self, i, **kw):
        with self.lock:
            self.s["hd"][i].update(kw)
            n = len(self.files) or 1
            self.s["pct"] = round(sum(1.0 if h["tt"] in (XONG, XONG_VANG, LOI, BO_QUA) else h["pct"]
                                      for h in self.s["hd"]) / n, 4)

    def trang_thai(self):
        with self.lock:
            return json.loads(json.dumps(self.s, ensure_ascii=False))

    # ---------------------------------------------------------------- dùng lại kết quả cũ
    def _van_tay(self, path):
        h = hashlib.sha1()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        dm = json.dumps([[p["ma"], p["nhom"], p["mo_ta"], p["tieu_de_kws"], p["noi_dung_kws"], p["muc"], p["bat_buoc"],
                          p["loai_tru"], p.get("luon_cloud")] for p in self.params], ensure_ascii=False)
        h.update(dm.encode("utf-8"))
        h.update(f"|{self.model}|{bool(self.ra_lai)}|{bool(self.cloud)}".encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def _so_cache():
        return os.path.join(str(thu_muc_ket_qua()), "_da_xu_ly.json")

    def _doc_cache(self):
        try:
            with open(self._so_cache(), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _ghi_cache(self, fp, json_path):
        d = self._doc_cache()
        d[fp] = {"json": json_path, "luc": datetime.datetime.now().isoformat(timespec="seconds")}
        try:
            with open(self._so_cache(), "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def _dung_lai(self, fp, path):
        x = self._doc_cache().get(fp)
        if not x or not os.path.exists(x["json"]):
            return None
        src = os.path.dirname(x["json"])
        dst = os.path.join(self.out_dir, ten_an_toan(os.path.splitext(os.path.basename(path))[0]))
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        with open(os.path.join(dst, os.path.basename(x["json"])), encoding="utf-8") as f:
            kq = json.load(f)
        kq["bo_qua"] = x["luc"]
        return kq

    # ---------------------------------------------------------------- chạy
    def kiem_tra_ai(self):
        """Trả MayAI nếu dùng được; None nếu không có AI và được phép chỉ tách cấu trúc; lỗi thì AILoi."""
        if self.nguon_ai:
            from .ai_cloud import MayCloud
            ai = MayCloud(self.nguon_ai.get("nha_cung_cap"), self.nguon_ai.get("model"), ghi_log=self.log, dung=self.dung)
            ai.models()                           # chưa có API key → AILoi
            return ai
        ai = MayAI(self.url, self.model, timeout=self.timeout, ghi_log=self.log, dung=self.dung)
        try:
            tags = ai.models()
        except Exception as e:  # noqa: BLE001
            if self.chi_cau_truc:
                self.log(f"Không kết nối được máy AI {self.url} ({type(e).__name__}) → chỉ tách cấu trúc + dò vị trí")
                return None
            raise AILoi(f"Không kết nối được máy AI {self.url} ({type(e).__name__}). Kiểm tra máy AI đang bật, "
                        "Ollama đang chạy và địa chỉ IP trong Cài đặt.") from None
        if self.model not in tags and f"{self.model}:latest" not in tags:
            chat = [t for t in tags if _la_model_chat(t)]
            raise AILoi(f"Máy AI chưa có model {self.model}. Model hiện có: {', '.join(chat) or '(không có)'}")
        return ai

    def chay(self):
        ds_kq = []
        with self.lock:
            self.s["tt"] = "dang_chay"
            self.s["bat_dau"] = time.time()
        self.log(f"Bắt đầu lượt {self.nhan} | {len(self.files)} HĐ | {len(self.params)} tham số | model {self.model} | "
                 f"{self.url} | rà lại: {'có' if self.ra_lai else 'không'} | cloud: "
                 f"{(self.cloud or {}).get('nha_cung_cap', '') if self.cloud else 'tắt'}")
        try:
            plan = []
            for i, f in enumerate(self.files):
                fp = self._van_tay(f)
                old = None if (self.chay_lai or self.chi_cau_truc) else self._dung_lai(fp, f)
                plan.append((i, f, fp, old))
            ai = None
            if any(old is None for _, _, _, old in plan):
                self.log(f"Kiểm tra kết nối máy AI {self.url}…")
                ai = self.kiem_tra_ai()
            with self.lock:
                self.s["dung_ai"] = ai is not None
            for i, f, fp, old in plan:
                if self.dung.is_set():
                    raise DaDung()
                if old is not None:
                    self.log(f"HĐ {os.path.basename(f)}: không đổi so với lần trích {old['bo_qua']} → dùng lại kết quả")
                    ds_kq.append(old)
                    self._cap_nhat(i, tt=BO_QUA, pct=1.0, ten=old["ten"], so_ok=old["tom_tat"]["so_ok"],
                                   so_vang=sum(1 for d in old["bang"] if can_xem(d)),
                                   dung_dap_an=old["tom_tat"].get("dung_dap_an", ""),
                                   thoi_gian=old["tom_tat"]["thoi_gian_giay"])
                    self._danh_muc([old])
                    continue
                t0 = time.time()
                self._cap_nhat(i, tt=DANG, bat_dau=t0, pct=0.0)

                def td(buoc, mo_ta, pct, i=i):
                    self._cap_nhat(i, buoc=buoc, mo_ta=mo_ta, pct=round(pct, 4))
                tx = TrichXuat(self.params, ai=ai, out_dir=self.out_dir, ra_lai=self.ra_lai, cloud=self.cloud,
                               tien_do=td, ghi_log=self.log, dung=self.dung,
                               thu_muc_dap_an=self.thu_muc_dap_an or os.path.dirname(f))
                try:
                    kq = tx.xu_ly(f)
                except DaDung:
                    self._cap_nhat(i, tt=DUNG, thoi_gian=round(time.time() - t0))
                    raise
                except Exception as e:  # noqa: BLE001 — một file lỗi không làm dừng cả lượt
                    msg = f"{type(e).__name__}: {str(e)[:300]}"
                    self.log(f"  LỖI xử lý {os.path.basename(f)}: {msg}")
                    self._cap_nhat(i, tt=LOI, loi=msg, thoi_gian=round(time.time() - t0))
                    ds_kq.append({"hop_dong": os.path.basename(f), "loi": msg})
                    continue
                ds_kq.append(kq)
                tt = kq["tom_tat"]
                n_vang = sum(1 for d in kq["bang"] if can_xem(d))
                self._cap_nhat(i, tt=XONG_VANG if n_vang else XONG, pct=1.0, ten=kq["ten"], so_ok=tt["so_ok"],
                               so_vang=n_vang, dung_dap_an=tt["dung_dap_an"], thoi_gian=tt["thoi_gian_giay"],
                               canh_bao=kq["phieu_kiem_tra"].get("warnings", []), loi_ai=tt["loi_ai"])
                if tt["loi_ai"] == 0 and kq["che_do"] == "AI":
                    self._ghi_cache(fp, os.path.join(self.out_dir, kq["ten"], kq["tep"]["json"]))
                self._danh_muc([kq])
            with self.lock:
                self.s["tt"] = "xong"
                self.s["thong_bao"] = f"Xong {len(ds_kq)} hợp đồng"
        except DaDung:
            self.log("Người dùng bấm Dừng — lượt chạy dừng lại. HĐ đã xong vẫn giữ kết quả.")
            with self.lock:
                self.s["tt"] = "da_dung"
                self.s["thong_bao"] = "Đã dừng theo yêu cầu"
                for h in self.s["hd"]:
                    if h["tt"] in (CHO, DANG):
                        h["tt"] = DUNG
        except AILoi as e:
            self.log(f"DỪNG: {e}")
            with self.lock:
                self.s["tt"] = "loi"
                self.s["thong_bao"] = str(e)
        except Exception as e:  # noqa: BLE001
            self.log(f"DỪNG do lỗi: {type(e).__name__}: {str(e)[:300]}")
            with self.lock:
                self.s["tt"] = "loi"
                self.s["thong_bao"] = f"{type(e).__name__}: {str(e)[:300]}"
        finally:
            ok = [k for k in ds_kq if not k.get("loi")]
            if ds_kq:
                try:
                    xp, jp = ghi_tong_hop(ds_kq, self.params, self.out_dir, self.nhan,
                                          self.model if any(k.get("che_do") == "AI" for k in ok) else None)
                    with self.lock:
                        self.s["tep"] = {"tong_hop_xlsx": os.path.basename(xp), "tong_hop_json": os.path.basename(jp)}
                except OSError as e:
                    self.log(f"Không ghi được TONG_HOP: {e}")
            with self.lock:
                self.s["tep"]["nhat_ky"] = os.path.basename(self.nhat_ky)
                self.s["ket_thuc"] = time.time()
            self.log(f"Kết thúc lượt {self.nhan} | {time.time() - self.s['bat_dau']:.0f}s")
            self._ghi_trang_thai()
        return ds_kq

    def _danh_muc(self, ds):
        if not self.ghi_dm:
            return
        try:
            p, moi, sua = ghi_danh_muc(ds, str(file_danh_muc_hd()), str(MAU_DANH_MUC_HD))
            with self.lock:
                self.s["danh_muc"] = p
            self.log(f"  DANH_MUC_HOP_DONG.xlsx: thêm {moi}, cập nhật {sua} dòng")
        except PermissionError:
            self.log("  KHÔNG ghi được DANH_MUC_HOP_DONG.xlsx (file đang mở trong Excel?) — đóng file rồi bấm "
                     "'Ghi lại danh mục'")
        except ImportError:
            self.log("  Chưa có thư viện openpyxl → bỏ qua DANH_MUC_HOP_DONG.xlsx (pip install openpyxl)")
        except Exception as e:  # noqa: BLE001
            self.log(f"  Lỗi ghi DANH_MUC_HOP_DONG.xlsx: {type(e).__name__}: {str(e)[:200]}")

    def _ghi_trang_thai(self):
        try:
            with open(os.path.join(self.out_dir, "_luot.json"), "w", encoding="utf-8") as f:
                json.dump(self.trang_thai(), f, ensure_ascii=False, indent=1)
        except OSError:
            pass
