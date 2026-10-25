"""Khai báo khung CRM (TL 49); quyền và số đều được quyết ở máy chủ.

Tái dùng S1 cho phạm vi hợp đồng/tiền, G2 cho báo giá, G1 cho mẫu.
Không khởi tạo factory ghi/worker G5. Không coi số bị giới hạn là tổng đầy đủ.
"""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import parse_qs, urlsplit

from ..ha_tang.primitives import DataError
from ..k2.crm_giao_ket import CrmGiaoKetK2
from ..k2.crm_s1 import CrmDanhSachK2

VAI = ["BAN_HANG", "KE_TOAN", "KE_TOAN_TRUONG", "CFO", "XEM"]
NGHIEP_VU = VAI[:-1]


def _phan(ma, ten, icon, mau, thu_tu, vai, dem=None):
    return {"ma": ma, "ten": ten, "icon": icon, "nhom_mau": mau, "thu_tu": thu_tu,
            "quyen": {"module": "CRM", "vai": vai}, "dem": dem,
            "duong_dan": "#crm/" + ma.replace("_", "-")}


def _the(ma, nhan, phan, tham_so, giai_thich, canh_bao=False):
    return {"ma": ma, "nhan": nhan, "dem": "danh_sach_loc", "giai_thich": giai_thich,
            "loc": {"phan": phan, "tham_so": tham_so},
            "canh_bao_khi_lon_hon": 0 if canh_bao else None}


DEN_HAN = _the("hd_dot_den_han", "Hợp đồng có đợt thu đến hạn 7 ngày", "hop_dong", {"the": "W5"},
               "Đếm hợp đồng có đợt còn phải thu từ hôm nay đến 7 ngày tới, trong phạm vi được xem tiền.")
QUA_HAN = _the("hd_dot_qua_han", "Hợp đồng có đợt thu quá hạn", "hop_dong", {"co": "QUA_HAN"},
               "Đếm hợp đồng có đợt còn phải thu đã quá ngày hạn xác định.", True)
HIEU_LUC = _the("hd_hieu_luc", "Hợp đồng hiệu lực", "hop_dong", {"trang_thai": "HIEU_LUC"},
                "Hợp đồng hiệu lực trong phạm vi được cấp.")
MAU_CHO_DUYET = _the("mau_cho_duyet", "Mẫu hợp đồng chờ duyệt", "mau", {"trang_thai": "CHO_CFO"},
                    "Phiên bản mẫu đã kiểm, chờ duyệt theo quyền hiện hành.", True)
THE_KE_TOAN = [_the("hd_cho_kiem", "Hợp đồng ký chờ kiểm", "hop_dong", {"the": "W3"},
                    "Hợp đồng đã ký hoặc phiên bản đang chờ kế toán kiểm."), QUA_HAN]

MODULE = {"crm": {
    "ma": "crm", "ten": "CRM · Hợp đồng bán hàng", "icon": "crm", "nhom_mau": "ban_hang",
    "thu_tu": 20, "tam_dung": False,
    "phan": [
        _phan("hop_dong", "Hợp đồng", "hop-dong", "ban_hang", 10, VAI, "hop_dong_cho"),
        _phan("bao_gia", "Báo giá", "bao-gia", "ban_hang", 20, NGHIEP_VU, "bao_gia_nhap"),
        _phan("mau", "Mẫu hợp đồng", "mau", "danh_muc", 30, NGHIEP_VU, "mau_cho"),
        _phan("tiep_nhan", "Tiếp nhận hợp đồng ký", "tiep-nhan", "tiep_nhan", 40, NGHIEP_VU),
        _phan("thu_tien", "Thu tiền", "thu-tien", "tien", 50, VAI, "thu_tien_cho"),
        _phan("bao_cao", "Báo cáo & file soát", "bao-cao", "bao_cao", 60, VAI),
    ],
    "the": {
        "BAN_HANG": [_the("bao_gia_nhap", "Báo giá đang nháp", "bao_gia", {"trang_thai": "NHAP"},
                          "Báo giá nháp trong danh sách được cấp quyền."), DEN_HAN],
        "KE_TOAN": THE_KE_TOAN, "KE_TOAN_TRUONG": THE_KE_TOAN,
        "CFO": [MAU_CHO_DUYET, QUA_HAN, HIEU_LUC], "XEM": [HIEU_LUC, DEN_HAN],
    },
}}


def _so_viec(so, phan, loc):
    n = so(phan, loc)
    return {} if n is None else {"so_viec": n, "qua_han": loc.get("co") == "QUA_HAN" and n > 0}


def hop_dong_cho(so, vai):
    the = {"BAN_HANG": "W2", "KE_TOAN": "W3", "KE_TOAN_TRUONG": "W3"}.get(vai)
    return _so_viec(so, "hop_dong", {"the": the}) if the else {}


def bao_gia_nhap(so, vai):
    return _so_viec(so, "bao_gia", {"trang_thai": "NHAP"}) if vai == "BAN_HANG" else {}


def mau_cho(so, vai):
    tt = {"KE_TOAN": "CHO_KIEM", "KE_TOAN_TRUONG": "CHO_KIEM", "CFO": "CHO_CFO"}.get(vai)
    return _so_viec(so, "mau", {"trang_thai": tt}) if tt else {}


def thu_tien_cho(so, vai):
    if vai == "XEM":
        return {}
    return _so_viec(so, "hop_dong", {"the": "W5"} if vai == "BAN_HANG" else {"co": "QUA_HAN"})


DEM_PHAN = {f.__name__: f for f in (hop_dong_cho, bao_gia_nhap, mau_cho, thu_tien_cho)}


class CrmKhungK2:
    """Adapter chỉ đọc, dùng chính service danh sách; cache trong một lần đọc khung."""
    def __init__(self, mau):
        self.mau = mau

    def quyen(self, me):
        dt = self.mau.danh_tinh(me)
        vai = dt["vai_tro"]
        with self.mau._tx(dt, rr=True) as c:
            c.execute("SET TRANSACTION READ ONLY")
            r = c.execute("""SELECT EXISTS (SELECT 1 FROM master.phap_nhan p
                WHERE master.ktt_duoc(p.id, 'CRM')
                  AND master.ktt_co_vai(p.id, %s::text[], NULL)) AS duoc""", ([vai] if vai in VAI else [],)).fetchone()
        return vai, bool(r["duoc"])

    def danh_sach_loc(self, me, phan, tham_so):
        """G1/G2 chưa nhận lọc trạng thái: lọc trên đúng danh sách đã kiểm quyền.

        G2 có LIMIT 200: trả danh sách lọc như thường, nhưng đánh dấu không đủ
        để khung bỏ số tổng thay vì trình bày một tổng bị cắt cụt.
        """
        if phan == "hop_dong":
            return CrmDanhSachK2(self.mau).danh_sach(me, tham_so)
        if phan == "bao_gia" and tham_so == {"trang_thai": "NHAP"}:
            data = CrmGiaoKetK2(self.mau).danh_sach(me)
            day_du = len(data["bao_gia"]) < 200
            data["bao_gia"] = [r for r in data["bao_gia"] if r["trang_thai"] == "NHAP"]
            return {**data, "tong": len(data["bao_gia"]), "day_du": day_du}
        if phan == "mau" and tham_so.get("trang_thai") in ("CHO_CFO", "CHO_KIEM") and len(tham_so) == 1:
            data = self.mau.danh_sach(me)
            data["phien_ban"] = [r for r in data["phien_ban"] if r["trang_thai"] == tham_so["trang_thai"]]
            return {**data, "tong": len(data["phien_ban"]), "day_du": True}
        raise DataError("INVALID_REQUEST", "Bộ lọc danh sách không được hỗ trợ.")

    def module(self, me):
        khai_bao = MODULE["crm"]
        out = {"module": {k: khai_bao[k] for k in ("ma", "ten")}, "the": [], "phan": [], "lam_moi_sau_giay": 60}
        vai, duoc = self.quyen(me)
        if not duoc or vai not in VAI:
            return {**out, "khong_quyen": True}
        dem = {}

        def so(phan, loc):
            khoa = (phan, tuple(sorted(loc.items())))
            if khoa not in dem:
                if phan == "hop_dong":
                    # Trang cuối rỗng: S1 vẫn đếm toàn phạm vi, không đọc chi tiết nặng.
                    data = self.danh_sach_loc(me, phan, {**loc, "trang": "100000"})
                    loc_tien = loc.get("the") == "W5" or loc.get("co") == "QUA_HAN"
                    bi_chan = data["khong_quyen"] or (loc_tien and data["khong_quyen_xem_tien"])
                    dem[khoa] = None if bi_chan else data["tong"]
                else:
                    data = self.danh_sach_loc(me, phan, loc)
                    dem[khoa] = data["tong"] if data["day_du"] else None
            return dem[khoa]

        for the in khai_bao["the"][vai]:
            n = so(the["loc"]["phan"], the["loc"]["tham_so"])
            if n is not None:
                out["the"].append({**{k: deepcopy(the[k]) for k in ("ma", "nhan", "giai_thich", "loc")},
                                   "so": n, "canh_bao": the["canh_bao_khi_lon_hon"] is not None and n > the["canh_bao_khi_lon_hon"]})
        # Chỉ việc có nguồn, dành cho vai; không lấy hợp đồng hiệu lực làm việc chờ.
        for p in khai_bao["phan"]:
            if vai not in p["quyen"]["vai"]:
                continue
            item = {k: p[k] for k in ("ma", "ten", "icon", "nhom_mau", "duong_dan")}
            if p["dem"]:
                item.update(DEM_PHAN[p["dem"]](so, vai))
            out["phan"].append(item)
        return out


def dieu_huong(h, app, path):
    """Khối route mỏng gọi từ crm_g, gồm drill-down G1/G2 đúng bộ lọc thẻ."""
    from . import crm_g
    with app.mutation_lock:
        _, me, _ = app.crm_phien(h.crm_sid())
    query = parse_qs(urlsplit(h.path).query, keep_blank_values=True, max_num_fields=10)
    if path.startswith("/api/khung/module/"):
        if path != "/api/khung/module/crm":
            return h.send_content(404, {"error": "NOT_FOUND", "message": "Không tìm thấy module này."})
        if query:
            raise DataError("INVALID_REQUEST", "Trang chủ module không nhận bộ lọc từ trình duyệt.")
        phan = None
    else:
        phan = {"/api/crm/bao-gia": "bao_gia", "/api/crm/mau": "mau"}[path]
        if set(query) != {"trang_thai"} or len(query["trang_thai"]) != 1:
            raise DataError("INVALID_REQUEST", "Bộ lọc danh sách không hợp lệ.")

    def doc():
        with crm_g.dich_vu_s1(app) as mau:
            svc = CrmKhungK2(mau)
            if phan is None:
                return svc.module(me)
            vai, duoc = svc.quyen(me)
            if not duoc or vai not in NGHIEP_VU:
                raise DataError("CRM_G_KHONG_CO_QUYEN", "Bạn không có quyền xem phần này.")
            return svc.danh_sach_loc(me, phan, {"trang_thai": query["trang_thai"][0]})

    try:
        data = app._crm_db(doc)
    except DataError as exc:
        if exc.code not in crm_g.MA_503 | {"CSDL_TU_CHOI", "CRM_G_GIAO_DICH_NGOAI"}:
            raise
        return h.send_content(503, {"error": "CRM_G_CHUA_SAN_SANG", "message": "Chưa đọc được dữ liệu CRM. Vui lòng thử lại sau."},
                              headers={"Cache-Control": "no-store"})
    return h.send_content(200, data, headers={"Cache-Control": "no-store"})
