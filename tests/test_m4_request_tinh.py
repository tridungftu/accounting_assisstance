"""M4-04A — kiểm thuần + transport cho Request nháp (request_api / request_nhap / m4_request._than). CODE_ONLY: coder viết, CHƯA CHẠY (WRITTEN_NOT_RUN).

KHÔNG mạng, KHÔNG CSDL, KHÔNG Request thật: transport là `FakeRequest` (TEST_ONLY) mô phỏng hợp đồng API #2 đã đọc từ nguồn (POST /de-xuat 201/200 +
Idempotency-Key 24h theo khóa API, KHÔNG dấu vân body; GET chi tiết; multipart tep+maTruong; GET /tep chỉ trả bytes khi clean, khác → 409).
Intent/biên nhận/lease mô phỏng bằng `KhoGia` — bản Python RÚT GỌN các luật nhận bước của m4.request_giu/request_ghi để kiểm máy trạng thái phía
dịch vụ; SQL thật được kiểm ở tests/test_m4_request_pg.py (env-gated). Golden value là literal/hashlib độc lập, không lấy đầu ra của chính code.

R01 dương: tạo → GET trạng thái thật → tải PDF đã seal → chờ quét → clean → tải bytes → khớp SHA/độ dài DUY NHẤT; người đứng tên ≠ chủ khóa API;
    số tiền/tiền tệ/trường/PDF đúng literal; không gọi danh sách, không gửi/duyệt/xóa.
R02 thiếu mapping/khóa/transport/retention → CHUA_CAU_HINH có cấu trúc, 0 IO, 0 biên nhận/intent.
R03 authority giả (actor/nguoiTao/PN/số tiền/URL/path/body lạ) bị chặn TRƯỚC IO; origin/path transport bị kiểm; transport tắt mặc định, repr không lộ khóa.
R04 mất ACK tạo → CHUA_RO_TAO; đối soát gửi lại ĐÚNG key + body → nguồn phát lại 200 cùng ID; tổng một Request.
R05 mất ACK tải lên → CHUA_RO_TAI; không tải lại; đối soát theo ứng viên → clean → khớp → DA_DOI_SOAT; tổng một tệp.
R06 phát lại đúng khóa (0 POST mới); cùng khóa khác hành động → M4_IDEMPOTENCY_KHAC; khóa mới → cùng intent, không Request thứ hai.
R07 đồng thời (lệnh thứ hai giữa lúc POST) → M4_REQUEST_DANG_XU_LY; khởi động lại khi lease còn → DANG_XU_LY; lease hết → CHUA_RO_TAO → gửi lại.
R08 quá cửa sổ 20h sau chưa rõ → HOLD CHUA_RO_QUA_HAN_IDEM, 0 POST; xoay khóa (khoa_ref đổi) → HOLD CAN_CU_DOI, 0 POST; đối chứng: nguồn quá 24h /
    khóa mới thật sự tạo bản trùng (lý do có cửa sổ).
R09 danh sách rỗng không phải bằng chứng; Request không còn draft → HOLD KHONG_CON_NHAP, 0 tải lên.
R10 drift nhóm/trường/danh mục → CAU_HINH_LECH 0 POST; drift chi tiết (số tiền định dạng khác) → HOLD SO_TIEN_LECH.
R11 quét pending/error/infected; hash sai; trùng khớp; lệch kích thước.
R12 thu hồi hiện hành giữa lúc xử lý → bằng chứng ghi, M4_REQUEST_PHAM_VI_DA_DOI; lệnh sau → CHUA_CAU_HINH/PHAM_VI không IO; mapping mới → HOLD.
R13 client: ánh xạ lỗi typed literal (429/503/500/422/3xx/JSON hỏng/đọc dở) + hằng SQL MỘT constant, không ordinal/registry.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest
import uuid
from pathlib import Path
from unittest import mock

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.m4 import duyet_dot as DD
from kho_tri_thuc.m4 import request_api as RA
from kho_tri_thuc.m4 import request_nhap as RN

GOC = Path(__file__).resolve().parents[1]
# ------------------------------------------------------------------ literal oracles (TEST_ONLY, DEMO)
NHOM_MA, PN_MA, DM_PN = "THANH_TOAN_HD", "PN_DEMO_A", "PHAP_NHAN"
T_TIEN, T_PN, T_TEP = "so_tien", "phap_nhan", "ho_so_duyet"
NV, CHU_KHOA, AI = "nv.request.a1", "chu.khoa.api", "MO_PHONG_DU_AN_A1"
SO_TIEN, TIEN_TE = "31500000", "VND"  # = F.KET_LUAN_VND.so_xin_thanh_toan (KHÔNG gia_tri_nt 35000000)
PDF_RAW = b"%PDF-1.4\n% M4-04A TEST_ONLY ho so dot da duyet\n" + bytes(range(256)) * 3 + b"\n%%EOF\n"
PDF_SHA = hashlib.sha256(PDF_RAW).hexdigest()
PDF_LEN = len(PDF_RAW)
ID = {k: str(uuid.UUID(int=i + 1)) for i, k in enumerate(("dot", "hd", "da", "pn", "pb", "seal", "qd", "kl", "pdf", "nv", "ax", "ax2"))}
SL_SHA, GR_SHA = "1" * 64, "2" * 64
BODY_MONG = {"nhom": NHOM_MA, "tieuDe": "Thanh toán HĐ 123/2025-DEMO — đợt 1", "nguoiTao": NV,
             "giaTri": {T_TIEN: {"amount": SO_TIEN, "currency": TIEN_TE}, T_PN: PN_MA}, "truongMayDien": [T_PN, T_TIEN]}
NGUON_MONG = {"dot_id": ID["dot"], "hop_dong_id": ID["hd"], "du_an_id": ID["da"], "phap_nhan_id": ID["pn"], "phien_ban_id": ID["pb"],
              "seal_id": ID["seal"], "quyet_dinh_id": ID["qd"], "ket_luan_id": ID["kl"], "graph_sha256": GR_SHA, "so_lieu_sha256": SL_SHA,
              "so_tien": SO_TIEN, "tien_te": TIEN_TE, "pdf_id": ID["pdf"], "pdf_sha256": PDF_SHA, "pdf_byte_length": PDF_LEN, "nhanh": "GOC"}


def nhom_json(**thay) -> dict:
    n = {"ma": NHOM_MA, "ten": "Thanh toán hợp đồng", "phienBan": 3, "truongTongTien": T_TIEN, "truongPhapNhan": T_PN,
         "truong": [{"ma": T_TIEN, "nhan": "Số tiền", "kieu": "number", "batBuoc": True, "cauHinh": {}, "danhMuc": None},
                    {"ma": T_PN, "nhan": "Pháp nhân", "kieu": "choice", "batBuoc": True, "cauHinh": {}, "danhMuc": DM_PN},
                    {"ma": T_TEP, "nhan": "Hồ sơ đã duyệt", "kieu": "attachment", "batBuoc": True, "cauHinh": {"maxFiles": 2}, "danhMuc": None}]}
    n.update(thay)
    return n


def cau_hinh(**thay) -> RN.CauHinhRequest:
    d = dict(origin="https://request.demo.invalid", khoa_ref="khoa-demo:1", khoa_chu_dang_nhap=CHU_KHOA, nhom=NHOM_MA, phien_ban=3,
             truong_tien=T_TIEN, truong_phap_nhan=T_PN, truong_tep=T_TEP, danh_muc_phap_nhan=DM_PN, phap_nhan_ma={ID["pn"]: PN_MA},
             luu_giu_da_kiem=True)
    d.update(thay)
    return RN.CauHinhRequest(**d)


def ho_so_seal(**thay) -> dict:
    hs = {"trang_thai": "DA_SEAL",
          "context": {"dot_id": ID["dot"], "hop_dong_id": ID["hd"], "du_an_id": ID["da"], "phap_nhan_id": ID["pn"], "version_id": ID["pb"]},
          "seal": {"id": ID["seal"], "version_id": ID["pb"], "pdf_id": ID["pdf"], "quyet_dinh_id": ID["qd"], "ket_luan_id": ID["kl"],
                   "graph_sha256": GR_SHA, "pdf_sha256": PDF_SHA, "so_lieu_sha256": SL_SHA,
                   "so_lieu": {"tien_te": "VND", "gia_tri_nt": "35000000", "so_xin_thanh_toan": SO_TIEN, "tam_ung": "0", "thu_hoi": "0",
                               "giu_lai": "1750000"}},
          "pdf_lich_su": [{"id": ID["pdf"], "name": "ho_so_da_duyet.pdf", "sha256": PDF_SHA, "byte_length": PDF_LEN}],
          "dot": {"so_dot": 1, "so_hop_dong": "123/2025-DEMO"}}
    hs.update(thay)
    return hs


# ================================================================================================== đồng hồ + fake Request (TEST_ONLY)
class DongHo:
    def __init__(self):
        self.gio = 0.0


class SapTienTrinh(Exception):
    """Mô phỏng tiến trình chết NGAY sau khi nguồn đã thực hiện (trước khi máy chủ ghi kết quả)."""


class FakeRequest:
    """TEST_ONLY — mô phỏng API #2 trong bộ nhớ; không socket. `tiem(op, *hanh)` tiêm lỗi FIFO cho một op:
    'MAT_ACK' (thực hiện rồi mất phản hồi), 'TIMEOUT' (mất phản hồi, KHÔNG thực hiện), 'KET_NOI' (chưa gửi), 'SAP' (thực hiện rồi tiến trình chết),
    ('HTTP', status, body, headers) (trả lỗi, không thực hiện), callable(fake) (chạy trước rồi thực hiện bình thường)."""

    NGUOI = {NV, CHU_KHOA}

    def __init__(self, dong_ho: DongHo, *, nhom=None, danh_muc=None, kich_hoat=True):
        self.dh, self.kich_hoat = dong_ho, kich_hoat
        self.nhom = [nhom or nhom_json()]
        self.danh_muc = {DM_PN: danh_muc or {"ma": DM_PN, "giaTri": [{"ma": PN_MA, "dangDung": True}, {"ma": "PN_CU", "dangDung": False}]}}
        self.de_xuat, self.tep, self.idem = {}, {}, {}
        self.khoa_api = "k1"
        self.quet_mac_dinh = "pending"
        self.bien_doi_chi_tiet = None
        self.loi: dict = {}
        self.nhat_ky: list = []  # (phương thức, đường dẫn, headers)

    # ---- điều khiển
    def tiem(self, op: str, *hanh):
        self.loi.setdefault(op, []).extend(hanh)

    def quet(self, tep_id: str, tt: str):
        self.tep[tep_id]["meta"]["trangThaiQuet"] = tt

    def dem(self, ph: str, mau: str) -> int:
        return sum(1 for p, d, _ in self.nhat_ky if p == ph and re.fullmatch(mau, d))

    # ---- transport
    def gui(self, phuong_thuc, duong_dan, headers, body, toi_da_byte):
        if not self.kich_hoat:
            raise RA.LoiRequest("REQUEST_TRANSPORT_TAT")
        assert RA.kiem_duong_dan(duong_dan), duong_dan
        assert "Authorization" not in headers and "authorization" not in {k.lower() for k in headers}, "client không được tự gắn khóa"
        self.nhat_ky.append((phuong_thuc, duong_dan, dict(headers)))
        op, fn = self._route(phuong_thuc, duong_dan)
        hanh = self.loi.get(op, [])
        a = hanh.pop(0) if hanh else None
        if a == "KET_NOI":
            raise RA.LoiTruyen(False, "KET_NOI")
        if a == "TIMEOUT":
            raise RA.LoiTruyen(True, "GUI_DO")
        if isinstance(a, tuple) and a[0] == "HTTP":
            return RA.PhanHoi(a[1], {k.lower(): v for k, v in (a[3] if len(a) > 3 else {}).items()}, json.dumps(a[2]).encode("utf-8"))
        if callable(a):
            a(self)
        r = fn(duong_dan, headers, body)
        if a == "MAT_ACK":
            raise RA.LoiTruyen(True, "GUI_DO")
        if a == "SAP":
            raise SapTienTrinh(op)
        if len(r.body) > toi_da_byte:
            raise RA.LoiTruyen(True, "QUA_LON")
        return r

    def _route(self, ph, d):
        p = d.split("?", 1)[0]
        if ph == "GET" and p == "/api/v1/nhom":
            return "GET_NHOM", lambda *_: self._ok(200, self.nhom)
        if ph == "GET" and p.startswith("/api/v1/danh-muc/"):
            return "GET_DANH_MUC", self._danh_muc
        if ph == "POST" and p == "/api/v1/de-xuat":
            return "POST_DE_XUAT", self._tao
        if ph == "GET" and p == "/api/v1/de-xuat":
            return "GET_DS", lambda *_: self._ok(200, [], tongSo=0)
        m = re.fullmatch(r"/api/v1/de-xuat/([0-9a-f-]{36})(/tep)?", p)
        if m and ph == "GET" and not m.group(2):
            return "GET_DE_XUAT", lambda *_: self._chi_tiet(m.group(1))
        if m and ph == "POST" and m.group(2):
            return "POST_TEP", lambda _d, h, b: self._tai(m.group(1), h, b)
        m = re.fullmatch(r"/api/v1/tep/([0-9a-f-]{36})", p)
        if m and ph == "GET":
            return "GET_TEP", lambda *_: self._tai_ve(m.group(1))
        raise AssertionError(f"route ngoài hợp đồng: {ph} {d}")

    @staticmethod
    def _ok(st, du_lieu, **them):
        return RA.PhanHoi(st, {"content-type": "application/json"}, json.dumps({"duLieu": du_lieu, **them}, ensure_ascii=False).encode("utf-8"))

    @staticmethod
    def _loi(st, loi, **them):
        return RA.PhanHoi(st, {"content-type": "application/json"}, json.dumps({"loi": loi, "chiTiet": "nguồn: câu lỗi thô", **them}).encode())

    def _danh_muc(self, d, h, b):
        dm = self.danh_muc.get(d.rsplit("/", 1)[1])
        return self._ok(200, dm) if dm else self._loi(404, "KHONG_THAY")

    def _tao(self, d, h, b):
        key = h.get("Idempotency-Key")
        x = json.loads(b.decode("utf-8"))
        cu = self.idem.get((self.khoa_api, key))
        if cu and self.dh.gio - cu[1] < 24:  # nguồn: replay theo khóa API + key trong 24h, KHÔNG so body; trangThai hard-code 'draft'
            return self._ok(200, {"id": cu[0], "ma": self.de_xuat[cu[0]]["ma"], "trangThai": "draft"})
        n = next((n for n in self.nhom if n["ma"] == x.get("nhom")), None)
        if n is None:
            return self._loi(422, "NHOM", loiTheoTruong={"nhom": "không có"})
        if x.get("nguoiTao") not in self.NGUOI:
            return self._loi(422, "NGUOI_TAO", loiTheoTruong={"nguoiTao": "không có"})
        rid = str(uuid.uuid4())
        self.de_xuat[rid] = {"id": rid, "ma": f"DX-{len(self.de_xuat) + 1:04d}", "tieuDe": x["tieuDe"], "nhom": n["ma"], "trangThai": "draft",
                             "nguoiTao": x["nguoiTao"], "giaTri": x.get("giaTri") or {}, "truongMayDien": x.get("truongMayDien") or [], "tep": []}
        if key:
            self.idem[(self.khoa_api, key)] = (rid, self.dh.gio)
        return self._ok(201, {"id": rid, "ma": self.de_xuat[rid]["ma"], "trangThai": "draft"})

    def _chi_tiet(self, rid):
        x = self.de_xuat.get(rid)
        if x is None:
            return self._loi(404, "KHONG_THAY")
        n = next(n for n in self.nhom if n["ma"] == x["nhom"])
        tt = n.get("truongTongTien")
        d = {"id": rid, "ma": x["ma"], "tieuDe": x["tieuDe"], "nhom": {"ma": x["nhom"]}, "trangThai": x["trangThai"],
             "nguoiTao": {"tenDangNhap": x["nguoiTao"]}, "tongTien": x["giaTri"].get(tt) if tt else None, "giaTri": copy.deepcopy(x["giaTri"]),
             "truong": [{"ma": t["ma"], "kieu": t["kieu"]} for t in n["truong"]], "truongMayDien": [{"ma": m} for m in x["truongMayDien"]],
             "taoQuaApi": True, "tep": [copy.deepcopy(self.tep[t]["meta"]) for t in x["tep"]]}
        if self.bien_doi_chi_tiet:
            d = self.bien_doi_chi_tiet(d)
        return self._ok(200, d)

    def _tai(self, rid, h, b):
        x = self.de_xuat.get(rid)
        if x is None:
            return self._loi(404, "KHONG_THAY")
        if x["trangThai"] != "draft":
            return self._loi(409, "KHONG_CON_NHAP")
        bd = re.fullmatch(r"multipart/form-data; boundary=(\S+)", h.get("Content-Type", "")).group(1).encode("ascii")
        truong, data, ten = None, None, None
        for phan in b.split(b"--" + bd)[1:-1]:
            dau, _, than = phan.lstrip(b"\r\n").partition(b"\r\n\r\n")
            than = than[:-2] if than.endswith(b"\r\n") else than
            ten_f = re.search(rb'name="([^"]+)"', dau).group(1)
            if ten_f == b"maTruong":
                truong = than.decode("utf-8")
            elif ten_f == b"tep":
                data, ten = than, re.search(rb'filename="([^"]*)"', dau).group(1).decode()
        tid = str(uuid.uuid4())
        meta = {"id": tid, "tenTep": ten, "maTruong": truong, "khuChung": False, "kichThuoc": len(data), "mime": "application/pdf",
                "trangThaiQuet": self.quet_mac_dinh}
        self.tep[tid] = {"meta": meta, "bytes": data}
        x["tep"].append(tid)
        return self._ok(201, {k: v for k, v in meta.items() if k != "mime"})

    def _tai_ve(self, tid):
        t = self.tep.get(tid)
        if t is None:
            return self._loi(404, "KHONG_THAY")
        if t["meta"]["trangThaiQuet"] != "clean":
            return self._loi(409, "CHUA_SACH")
        return RA.PhanHoi(200, {"content-type": "application/pdf"}, t["bytes"])


# ================================================================================================== kho intent giả (rút gọn luật SQL) + xd giả
class KhoGia:
    """Bản Python rút gọn của m4.request_giu/request_ghi (nhận bước, lease, chưa rõ, cửa sổ 20h, CAS, quyền còn). TEST_ONLY; SQL thật: test PG."""

    def __init__(self, dong_ho: DongHo):
        self.dh = dong_ho
        self.q = {"thay": True, "tai_pdf": True, "anh_xa": True, "anh_xa_id": ID["ax"], "anh_xa_revision": 1, "nguoi_tao": NV, "phap_nhan_id": ID["pn"]}
        self.bien_nhan, self.y, self.su_kien = {}, {}, []

    def quyen(self, dot) -> dict:
        q = dict(self.q) if dot == ID["dot"] else {"thay": False, "tai_pdf": False, "anh_xa": False}
        q["tao"] = bool(q.get("tai_pdf") and q.get("anh_xa"))
        return q

    @staticmethod
    def _loi(ma):
        raise DataError(ma, ma)

    def _sk(self, y, buoc, tu, den, ok=True):
        self.su_kien.append((y["id"], buoc, tu, den, ok))

    def giu(self, dt, khoa, hanh, yc, dot, seal, cj, csha, buoc, lease_giay) -> dict:
        q = self.quyen(dot)
        if not q["thay"]:
            self._loi("M4_REQUEST_KHONG_THAY")
        if not q["tai_pdf"]:
            self._loi("M4_REQUEST_PHAM_VI")
        if not q["anh_xa"]:
            self._loi("M4_REQUEST_CHUA_ANH_XA")
        lap = False
        b = self.bien_nhan.get((dt["id"], khoa))
        if b:
            if b[0] != hanh or b[1] != yc:
                self._loi("M4_IDEMPOTENCY_KHAC")
            lap = True
        if seal != ID["seal"]:
            self._loi("M4_REQUEST_KHONG_THAY")
        y, chan = self.y.get(seal), None
        if y is None:
            if hanh != RN.HANH_TAO or buoc != "TAO":
                self._loi("M4_REQUEST_CHUA_CO_Y_DINH")
            if cj["nguon"] != NGUON_MONG or cj["actor"] != {"id": dt["id"], "dang_nhap": dt["dang_nhap"]} \
                    or cj["anh_xa"] != {"id": q["anh_xa_id"], "revision": q["anh_xa_revision"], "nguoi_tao": q["nguoi_tao"]}:
                self._loi("M4_REQUEST_NGUON_LECH")
            if cj["body"]["nguoiTao"] != q["nguoi_tao"] or cj["body"]["giaTri"][cj["cau_hinh"]["truong_tien"]] != {"amount": SO_TIEN, "currency": TIEN_TE}:
                self._loi("M4_REQUEST_NGUON_LECH")
            nid = str(uuid.uuid4())
            y = {"id": nid, "trang_thai": "MOI", "hold_ma": None, "nhanh": "GOC", "parent_id": None, "seal_id": seal, "phien_ban_id": ID["pb"],
                 "dot_id": dot, "actor_id": dt["id"], "anh_xa_id": q["anh_xa_id"], "canonical": copy.deepcopy(cj), "canonical_sha256": csha,
                 "idem_key": "m4-request:" + nid, "so_tien": SO_TIEN, "tien_te": TIEN_TE, "nhom": cj["cau_hinh"]["nhom"],
                 "nhom_phien_ban": cj["cau_hinh"]["phien_ban"], "pdf_id": ID["pdf"], "pdf_sha256": PDF_SHA, "pdf_byte_length": PDF_LEN,
                 "remote_id": None, "remote_ma": None, "remote_trang_thai": None, "remote_tep_id": None, "tep_trang_thai_quet": None,
                 "doi_soat_sha256": None, "doi_soat_byte_length": None, "co_chua_ro": False, "lan_tao_dau": None, "so_lan_tao": 0, "so_lan_tai": 0,
                 "lease_id": None, "lease_buoc": None, "lease_het": None, "revision": 0}
            self.y[seal] = y
            self._sk(y, "Y_DINH", None, "MOI")
        else:
            if y["actor_id"] != dt["id"]:
                self._loi("M4_REQUEST_NGUOI_KHAC")
            if q["anh_xa_id"] != y["anh_xa_id"]:
                chan = "ANH_XA_DOI"
            elif csha != y["canonical_sha256"]:
                chan = "CAN_CU_DOI"
        if y["lease_id"] and y["lease_het"] > self.dh.gio and not chan:
            self._loi("M4_REQUEST_DANG_XU_LY")  # SQL: raise → rollback cả biên nhận trong giao dịch (nên chưa ghi biên nhận ở đây)
        if not lap:
            self.bien_nhan[(dt["id"], khoa)] = (hanh, copy.deepcopy(yc), y["id"])
        if chan:
            self._sk(y, "CHAN", y["trang_thai"], y["trang_thai"])
            return self._ra(lap, chan, None, y)
        if y["lease_id"]:
            tu = y["trang_thai"]
            if y["lease_buoc"] == "TAO":
                y.update(trang_thai="CHUA_RO_TAO", co_chua_ro=True)
            elif y["lease_buoc"] == "TAI":
                y["trang_thai"] = "CHUA_RO_TAI"
            y.update(lease_id=None, lease_buoc=None, lease_het=None, revision=y["revision"] + 1)
            self._sk(y, "LEASE_HET", tu, y["trang_thai"])
        tt = y["trang_thai"]
        if not ((buoc == "TAO" and tt in ("MOI", "CHUA_RO_TAO", "TU_CHOI_TAO")) or (buoc == "DOC" and y["remote_id"])
                or (buoc == "TAI" and tt == "DA_TAO_NHAP") or (buoc == "DOI_SOAT" and tt in ("CHUA_RO_TAI", "CHO_QUET"))):
            return self._ra(lap, "BUOC_KHONG_HOP", None, y)
        if buoc == "TAO" and y["co_chua_ro"] and y["lan_tao_dau"] <= self.dh.gio - 20:
            y.update(trang_thai="HOLD", hold_ma="CHUA_RO_QUA_HAN_IDEM", revision=y["revision"] + 1)
            self._sk(y, "CHAN", tt, "HOLD")
            return self._ra(lap, "CHUA_RO_QUA_HAN_IDEM", None, y)
        lid = str(uuid.uuid4())
        y.update(lease_id=lid, lease_buoc=buoc, lease_het=self.dh.gio + lease_giay / 3600, revision=y["revision"] + 1,
                 lan_tao_dau=(self.dh.gio if y["lan_tao_dau"] is None else y["lan_tao_dau"]) if buoc == "TAO" else y["lan_tao_dau"],
                 so_lan_tao=y["so_lan_tao"] + (buoc == "TAO"), so_lan_tai=y["so_lan_tai"] + (buoc == "TAI"))
        self._sk(y, "GIU_" + buoc, tt, tt)
        return self._ra(lap, None, lid, y)

    @staticmethod
    def _ra(lap, chan, lid, y):
        return json.loads(json.dumps({"lap_lai": lap, "chan": chan, "lease_id": lid, "y_dinh": y}))

    def ghi(self, dt, yid, lease, rev, kq) -> dict:
        kq = json.loads(json.dumps(kq))  # phải tuần tự hóa được như jsonb
        y = next((v for v in self.y.values() if v["id"] == yid), None)
        if y is None:
            self._loi("M4_REQUEST_KHONG_THAY")
        if y["lease_id"] != lease or y["revision"] != rev:
            self._loi("M4_REQUEST_LEASE_MAT")
        den, tu, bc = kq.get("den"), y["trang_thai"], y["lease_buoc"]
        if not ((bc == "TAO" and den in ("DA_TAO", "CHUA_RO_TAO", "TU_CHOI_TAO", "HOLD"))
                or (bc == "DOC" and (den == tu or (tu == "DA_TAO" and den in ("DA_TAO_NHAP", "HOLD"))))
                or (bc == "TAI" and den in ("CHO_QUET", "CHUA_RO_TAI", "DA_TAO_NHAP", "HOLD"))
                or (bc == "DOI_SOAT" and den in ("DA_DOI_SOAT", "CHO_QUET", "CHUA_RO_TAI", "HOLD"))):
            self._loi("M4_REQUEST_CHUYEN_SAI")
        for k in ("remote_id", "remote_tep_id"):
            if kq.get(k) and y[k] and kq[k] != y[k]:
                self._loi("M4_REQUEST_REMOTE_ID_KHAC")
        if den == "HOLD" and not re.fullmatch(r"[A-Z0-9_]{1,60}", kq.get("hold_ma") or y["hold_ma"] or ""):
            self._loi("M4_THAM_SO_SAI")
        if den == "DA_DOI_SOAT" and (kq.get("doi_soat_sha256") != y["pdf_sha256"] or kq.get("doi_soat_byte_length") != y["pdf_byte_length"]):
            self._loi("CHECK_VIOLATION")  # CHECK của bảng: đối soát phải đúng SHA/độ dài PDF seal
        q = self.quyen(y["dot_id"])
        ok = q["tao"] and q.get("anh_xa_id") == y["anh_xa_id"]
        y.update(trang_thai=den, hold_ma=(kq.get("hold_ma") or y["hold_ma"]) if den == "HOLD" else None,
                 remote_id=y["remote_id"] or kq.get("remote_id"), remote_ma=y["remote_ma"] or kq.get("remote_ma"),
                 remote_trang_thai=kq.get("remote_trang_thai") or y["remote_trang_thai"], remote_tep_id=y["remote_tep_id"] or kq.get("remote_tep_id"),
                 tep_trang_thai_quet=kq.get("tep_trang_thai_quet") or y["tep_trang_thai_quet"],
                 doi_soat_sha256=kq.get("doi_soat_sha256") if den == "DA_DOI_SOAT" else y["doi_soat_sha256"],
                 doi_soat_byte_length=kq.get("doi_soat_byte_length") if den == "DA_DOI_SOAT" else y["doi_soat_byte_length"],
                 co_chua_ro=y["co_chua_ro"] or den == "CHUA_RO_TAO", lease_id=None, lease_buoc=None, lease_het=None, revision=y["revision"] + 1)
        self._sk(y, "GHI_" + bc, tu, den, ok)
        return json.loads(json.dumps({"quyen_con": ok, "y_dinh": y}))


class XdGia:
    """Chỉ những gì RequestNhap dùng ngoài _quyen/_giu/_ghi: danh tính, khóa thao tác, tải PDF đã seal (đã kiểm quyền ở DuyetDot thật)."""

    def __init__(self, raw=PDF_RAW, media="application/pdf"):
        self.raw, self.media, self.so_lan_tai_pdf = raw, media, 0
        self.conn = self.conn_tin_cay = None

    @staticmethod
    def danh_tinh(dang_nhap):
        if dang_nhap != AI:
            raise DataError("DANH_TINH", "không có phiên")
        return {"id": ID["nv"], "dang_nhap": AI}

    @staticmethod
    def _khoa(khoa):
        if not isinstance(khoa, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", khoa):
            raise DataError("M4_KHOA_THAO_TAC", "khóa")
        return khoa

    def duyet_pdf_tai(self, dang_nhap, version_id, pdf_id):
        assert (dang_nhap, version_id, pdf_id) == (AI, ID["pb"], ID["pdf"])
        self.so_lan_tai_pdf += 1
        return "ho_so_da_duyet.pdf", self.media, self.raw

    @staticmethod
    def _ma_loi_pg(exc):
        return "X"

    @staticmethod
    def _loi_ket_noi(exc, c):
        return False


class RequestNhapThu(RN.RequestNhap):
    """RequestNhap thật; chỉ thay ba điểm chạm CSDL bằng KhoGia (quyền / giữ / ghi)."""

    def __init__(self, kho: KhoGia, *a, **k):
        super().__init__(*a, **k)
        self.kho = kho

    def _quyen(self, dt, dot):
        return self.kho.quyen(dot)

    def _giu(self, dt, khoa, hanh, yc, dot, seal_id, cj, csha, buoc):
        return self.kho.giu(dt, khoa, hanh, yc, dot, seal_id, cj, csha, buoc, self.lease_giay)

    def _ghi(self, dt, y, lease, kq):
        return self.kho.ghi(dt, y["id"], lease, y["revision"], kq)


class _DuyetGia:
    hs = None

    def __init__(self, xd):
        pass

    def xem(self, dang_nhap, *, dot_id, version_id=None):
        assert dang_nhap == AI
        return copy.deepcopy(_DuyetGia.hs)


# ================================================================================================== ca kiểm
class CoSo(unittest.TestCase):
    def setUp(self):
        self.dh = DongHo()
        self.fake = FakeRequest(self.dh)
        self.kho = KhoGia(self.dh)
        self.xd = XdGia()
        _DuyetGia.hs = ho_so_seal()
        p = mock.patch.object(DD, "DuyetDot", _DuyetGia)
        p.start()
        self.addCleanup(p.stop)
        self.n = 0

    def rq(self, ch=None, transport="mac_dinh") -> RequestNhapThu:
        return RequestNhapThu(self.kho, self.xd, cau_hinh() if ch is None else ch, self.fake if transport == "mac_dinh" else transport)

    def K(self, ten=None):
        self.n += 1
        return f"m4rq-thu-{ten or self.n}"

    def tao(self, khoa=None, rq=None):
        return (rq or self.rq()).tao(AI, dot_id=ID["dot"], version_id=ID["pb"], khoa=khoa or self.K())

    def doi_soat(self, khoa=None, rq=None):
        return (rq or self.rq()).doi_soat(AI, dot_id=ID["dot"], version_id=ID["pb"], khoa=khoa or self.K())

    def loi(self, fn, *a, **k) -> str:
        try:
            fn(*a, **k)
        except DataError as exc:
            return exc.code
        self.fail("không bị chặn")

    def y(self) -> dict:
        return self.kho.y.get(ID["seal"])

    def ghi_io(self) -> list:
        return [(p, d) for p, d, _ in self.fake.nhat_ky if p == "POST"]

    def mot_request(self) -> dict:
        self.assertEqual(len(self.fake.de_xuat), 1)
        return next(iter(self.fake.de_xuat.values()))


class R01Duong(CoSo):
    def test_tao_doc_tai_quet_doi_soat(self):
        r = self.tao(self.K("a"))
        self.assertEqual((r["trang_thai"], r["buoc"], r["lap_lai"], r["chan"]), ("CHO_QUET", ["TAO", "DOC", "TAI", "DOI_SOAT"], False, None))
        x = self.mot_request()
        y = self.y()
        # body POST đúng literal: người đứng tên mapping (≠ chủ khóa), số xin thanh toán + tiền tệ đúng chuỗi, pháp nhân, trường máy điền
        self.assertEqual({k: x[k] for k in ("nhom", "tieuDe", "nguoiTao", "giaTri", "truongMayDien")},
                         {"nhom": NHOM_MA, "tieuDe": "Thanh toán HĐ 123/2025-DEMO — đợt 1", "nguoiTao": NV,
                          "giaTri": {T_TIEN: {"amount": "31500000", "currency": "VND"}, T_PN: PN_MA}, "truongMayDien": [T_PN, T_TIEN]})
        self.assertNotEqual(x["nguoiTao"], CHU_KHOA)
        self.assertEqual(y["canonical"]["body"], BODY_MONG)
        post = [h for p, d, h in self.fake.nhat_ky if p == "POST" and d == "/api/v1/de-xuat"]
        self.assertEqual([h["Idempotency-Key"] for h in post], ["m4-request:" + y["id"]])
        self.assertEqual((y["remote_id"], y["remote_ma"]), (x["id"], "DX-0001"))
        self.assertEqual(len(x["tep"]), 1)
        t = self.fake.tep[x["tep"][0]]
        self.assertEqual((t["bytes"], t["meta"]["maTruong"], t["meta"]["khuChung"], t["meta"]["tenTep"]),
                         (PDF_RAW, T_TEP, False, "ho_so_da_duyet.pdf"))
        self.assertEqual((y["trang_thai"], y["remote_tep_id"], y["tep_trang_thai_quet"], y["doi_soat_sha256"]), ("CHO_QUET", t["meta"]["id"], "pending", None))
        self.assertEqual(self.fake.dem("GET", r"/api/v1/tep/.*"), 0, "chưa clean → không tải bytes")
        # quét xong → đối soát: GET metadata → clean → tải bytes → SHA/độ dài literal
        self.fake.quet(t["meta"]["id"], "clean")
        r2 = self.doi_soat(self.K("b"))
        self.assertEqual((r2["trang_thai"], r2["buoc"]), ("DA_DOI_SOAT", ["DOC", "DOI_SOAT"]))
        y = self.y()
        self.assertEqual((y["doi_soat_sha256"], y["doi_soat_byte_length"], y["tep_trang_thai_quet"], y["remote_trang_thai"]),
                         (PDF_SHA, PDF_LEN, "clean", "draft"))
        self.assertEqual(r2["y_dinh"]["so_tien"], "31500000")
        # không danh sách, không route gửi/duyệt/xóa, đúng một POST mỗi loại
        self.assertEqual(self.fake.dem("GET", r"/api/v1/de-xuat(\?.*)?"), 0)
        self.assertEqual(self.ghi_io(), [("POST", "/api/v1/de-xuat"), ("POST", f"/api/v1/de-xuat/{x['id']}/tep")])
        self.assertTrue(all(p in ("GET", "POST") for p, _, _ in self.fake.nhat_ky))
        self.assertEqual(self.xd.so_lan_tai_pdf, 1)
        # lần sau: đã xong → chỉ quan sát, không ghi
        r3 = self.doi_soat(self.K("c"))
        self.assertEqual((r3["trang_thai"], r3["buoc"]), ("DA_DOI_SOAT", ["DOC"]))
        self.assertEqual(len(self.ghi_io()), 2)

    def test_ket_qua_khong_lo_canonical_nguoi_tao(self):
        r = self.tao()
        self.assertNotIn("canonical", r["y_dinh"])
        self.assertNotIn("nguoi_tao", r["y_dinh"])
        self.assertNotIn("idem_key", r["y_dinh"])
        self.assertEqual(r["schema"], "m4.request.nhap/1")

    def test_nt_khac_so_xin_thanh_toan(self):
        hs = ho_so_seal()
        hs["seal"]["so_lieu"] = {"tien_te": "USD", "gia_tri_nt": "36000000", "so_xin_thanh_toan": "30000000", "tam_ung": "0", "thu_hoi": "0",
                                 "giu_lai": "0"}
        _DuyetGia.hs = hs
        NGUON = {**NGUON_MONG, "so_tien": "30000000", "tien_te": "USD"}
        with mock.patch.dict(globals(), {"NGUON_MONG": NGUON, "SO_TIEN": "30000000", "TIEN_TE": "USD"}):
            r = self.tao()
        self.assertEqual(r["trang_thai"], "CHO_QUET")
        self.assertEqual(self.mot_request()["giaTri"][T_TIEN], {"amount": "30000000", "currency": "USD"})


class R02ChuaCauHinh(CoSo):
    def kiem_khong_side_effect(self):
        self.assertEqual((self.fake.nhat_ky, self.kho.bien_nhan, self.kho.y), ([], {}, {}))

    def test_thieu_tung_muc(self):
        ca = [(dict(transport=None), ["khoa_api"]),
              (dict(transport=FakeRequest(DongHo(), kich_hoat=False)), ["transport_chua_kich_hoat"]),
              (dict(ch=cau_hinh(luu_giu_da_kiem=False)), ["luu_giu_tep_nhiem"]),
              (dict(ch=cau_hinh(phap_nhan_ma={})), ["ma_phap_nhan", "phap_nhan_ma"]),
              (dict(ch=cau_hinh(nhom=None, phien_ban=0)), ["nhom", "phien_ban"]),
              (dict(ch=RN.CauHinhRequest()), ["danh_muc_phap_nhan", "khoa_chu_dang_nhap", "khoa_ref", "luu_giu_tep_nhiem", "ma_phap_nhan", "nhom",
                                              "origin", "phap_nhan_ma", "phien_ban", "truong_phap_nhan", "truong_tep", "truong_tien"])]
        for kw, mong in ca:
            with self.subTest(mong=mong):
                r = self.tao(rq=self.rq(**kw))
                self.assertEqual((r["trang_thai"], r["thieu"], r["y_dinh"]), ("CHUA_CAU_HINH", mong, None))
                self.kiem_khong_side_effect()

    def test_mapping(self):
        self.kho.q.update(anh_xa=False, anh_xa_id=None, nguoi_tao=None)
        r = self.tao()
        self.assertEqual((r["trang_thai"], r["thieu"]), ("CHUA_CAU_HINH", ["anh_xa_nhan_vien"]))
        self.kiem_khong_side_effect()
        self.kho.q.update(anh_xa=True, anh_xa_id=ID["ax"], nguoi_tao="Chu.Khoa.API")  # trùng chủ khóa (không phân biệt hoa thường)
        r = self.tao()
        self.assertEqual((r["trang_thai"], r["thieu"]), ("CHUA_CAU_HINH", ["anh_xa_trung_chu_khoa"]))
        self.kiem_khong_side_effect()
        # đối chứng dương: mapping đủ → có IO
        self.kho.q.update(nguoi_tao=NV)
        self.assertEqual(self.tao()["trang_thai"], "CHO_QUET")

    def test_thieu_cau_hinh_theo_quyen(self):  # xem() đọc intent qua RLS thật — kiểm ở test PG/HTTP
        self.assertEqual(self.rq(transport=None).thieu_cau_hinh(self.kho.quyen(ID["dot"])), ["khoa_api"])
        self.assertEqual(self.rq().thieu_cau_hinh(self.kho.quyen(ID["dot"])), [])


class R03Authority(CoSo):
    def test_quyen_truoc_moi_io(self):
        self.kho.q.update(tai_pdf=False)
        self.assertEqual(self.loi(self.tao), "M4_REQUEST_PHAM_VI")
        self.assertEqual(self.loi(self.tao, rq=self.rq(transport=None)), "M4_REQUEST_PHAM_VI")  # quyền trước cả báo thiếu cấu hình
        self.assertEqual(self.loi(lambda: self.rq().tao(AI, dot_id=str(uuid.uuid4()), version_id=ID["pb"], khoa=self.K())), "M4_REQUEST_KHONG_THAY")
        self.assertEqual(self.loi(lambda: self.rq().tao("KE_GIA_MAO", dot_id=ID["dot"], version_id=ID["pb"], khoa=self.K())), "DANH_TINH")
        self.assertEqual(self.loi(self.tao, "khoa có dấu cách"), "M4_KHOA_THAO_TAC")
        self.assertEqual((self.fake.nhat_ky, self.kho.y), ([], {}))

    def test_chua_seal_hoac_sai_phien_ban(self):
        _DuyetGia.hs = ho_so_seal(trang_thai="CHO_PDF", seal=None)
        self.assertEqual(self.loi(self.tao), "M4_REQUEST_CHUA_SEAL")
        hs = ho_so_seal()
        hs["seal"]["version_id"] = str(uuid.uuid4())
        _DuyetGia.hs = hs
        self.assertEqual(self.loi(self.tao), "M4_REQUEST_CHUA_SEAL")
        hs = ho_so_seal()
        hs["pdf_lich_su"][0]["sha256"] = "3" * 64
        _DuyetGia.hs = hs
        self.assertEqual(self.loi(self.tao), "M4_REQUEST_NGUON_LECH")
        self.assertEqual((self.fake.nhat_ky, self.kho.y), ([], {}))

    def test_than_http_chan_authority(self):
        try:
            from kho_tri_thuc.giao_dien import m4_request as W
        except ImportError as exc:  # pragma: no cover
            self.skipTest(f"NOT_RUN: không nạp được giao_dien ({exc})")
        ok = {"dot_id": ID["dot"], "version_id": ID["pb"], "khoa": "k-1"}
        self.assertEqual(W._than(dict(ok), W.TRUONG_LENH), ok)
        for k in ("nguoiTao", "actor", "phap_nhan_id", "so_tien", "amount", "currency", "nhom", "endpoint", "origin", "api_key", "authorization",
                  "pdf", "pdf_id", "seal_id", "remote_id", "idem_key", "maTruong", "giaTri", "cau_hinh", "transport"):
            with self.subTest(k=k):
                with self.assertRaises(DataError) as cm:
                    W._than({**ok, k: "x"}, W.TRUONG_LENH)
                self.assertEqual(cm.exception.code, "M4_CLIENT_AUTHORITY")
        for bad in ({**ok, "la": "x"}, {**ok, "khoa": 1}, {**ok, "dot_id": None}):
            with self.assertRaises(DataError) as cm:
                W._than(bad, W.TRUONG_LENH)
            self.assertEqual(cm.exception.code, "M4_YEU_CAU_SAI")
        self.assertEqual([W._status_ket_qua({"trang_thai": t}) for t in ("CHUA_CAU_HINH", "CAU_HINH_LECH", "HOLD", "LOI_REQUEST", "CHO_QUET", "DA_DOI_SOAT")],
                         [503, 409, 409, 502, 200, 200])
        self.assertEqual(self.fake.nhat_ky, [])

    def test_origin_duong_dan_transport(self):
        self.assertEqual(RA.kiem_origin("https://req.example.vn"), ("https", "req.example.vn", 443))
        self.assertEqual(RA.kiem_origin("https://req.example.vn:8443/"), ("https", "req.example.vn", 8443))
        self.assertEqual(RA.kiem_origin("http://127.0.0.1:9001", cho_http_loopback=True), ("http", "127.0.0.1", 9001))
        for o in ("http://req.example.vn", "http://127.0.0.1:9001", "https://u:p@req.example.vn", "https://req.example.vn/api", "https://req.example.vn?x=1",
                  "https://req.example.vn#f", "ftp://req.example.vn", "https://", " https://req.example.vn", None, "https://req.example.vn:99999"):
            with self.subTest(o=o):
                with self.assertRaises(RA.LoiRequest) as cm:
                    RA.kiem_origin(o)
                self.assertEqual(cm.exception.ma, "REQUEST_THAM_SO_SAI")
        with self.assertRaises(RA.LoiRequest):
            RA.kiem_origin("http://req.example.vn", cho_http_loopback=True)
        u = str(uuid.UUID(int=7))
        for d in ("/api/v1/nhom", "/api/v1/danh-muc/PHAP_NHAN", "/api/v1/de-xuat", f"/api/v1/de-xuat/{u}", f"/api/v1/de-xuat/{u}/tep", f"/api/v1/tep/{u}",
                  "/api/v1/de-xuat?trang=1&soDong=50"):
            self.assertTrue(RA.kiem_duong_dan(d), d)
        for d in ("https://evil.example/api/v1/nhom", "//evil.example/api/v1/nhom", "/api/v1/../admin", "/api/v1/de-xuat/x/gui", f"/api/v1/de-xuat/{u}/duyet",
                  f"/api/v1/tep/{u}/xoa", "/api/v1/nhom\r\nX: y", "/api/v2/nhom", "/api/v1/danh-muc/..", None):
            self.assertFalse(RA.kiem_duong_dan(d), d)
        t = RA.HttpsTransport("https://req.example.vn", "BI-MAT-0123456789abcdef")
        self.assertFalse(t.kich_hoat)
        self.assertNotIn("BI-MAT", repr(t))
        with self.assertRaises(RA.LoiRequest) as cm:
            t.gui("GET", "/api/v1/nhom", {}, None, 100)
        self.assertEqual(cm.exception.ma, "REQUEST_TRANSPORT_TAT")
        for khoa in ("ngan", "co dau cach 0123456789", None):
            with self.assertRaises(RA.LoiRequest):
                RA.HttpsTransport("https://req.example.vn", khoa)

    def test_client_tu_choi_tham_so(self):
        c = RA.RequestClient(self.fake)
        for fn in (lambda: c.chi_tiet("../x"), lambda: c.tai_ve("x", 10), lambda: c.danh_muc("../a"),
                   lambda: c.tao_nhap(BODY_MONG, "key có cách"), lambda: c.tao_nhap({**BODY_MONG, "trangThai": "approved"}, "k1"),
                   lambda: c.tai_tep(str(uuid.UUID(int=9)), "a.pdf", PDF_RAW, ma_truong=T_TEP, mime="text/html"),
                   lambda: c.tai_tep(str(uuid.UUID(int=9)), "a.pdf", b"", ma_truong=T_TEP)):
            with self.assertRaises(RA.LoiRequest) as cm:
                fn()
            self.assertEqual(cm.exception.ma, "REQUEST_THAM_SO_SAI")
        self.assertEqual(self.fake.nhat_ky, [])
        self.assertEqual(RA.ten_an_toan('../../a"b\r\n.exe'), "a_b__.exe.pdf")
        self.assertEqual(RA.ten_an_toan(""), "ho-so.pdf")


class R04MatAckTao(CoSo):
    def test_mat_ack_roi_gui_lai_cung_key(self):
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        r = self.tao(self.K("a"))
        self.assertEqual((r["trang_thai"], r["buoc"], r["loi"][0]["ma"], r["loi"][0]["khong_ro"]), ("CHUA_RO_TAO", ["TAO"], "REQUEST_KHONG_RO", True))
        x = self.mot_request()  # nguồn ĐÃ tạo
        self.assertEqual((self.y()["remote_id"], self.y()["co_chua_ro"]), (None, True))
        r2 = self.doi_soat(self.K("b"))
        self.assertEqual((r2["trang_thai"], r2["buoc"][:2]), ("CHO_QUET", ["TAO", "DOC"]))
        self.assertEqual(self.mot_request()["id"], x["id"])
        self.assertEqual(self.y()["remote_id"], x["id"])
        keys = [h["Idempotency-Key"] for p, d, h in self.fake.nhat_ky if d == "/api/v1/de-xuat"]
        self.assertEqual(keys, ["m4-request:" + self.y()["id"]] * 2)
        self.assertEqual([e for e in self.kho.su_kien if e[1] == "GHI_TAO"][-1][3], "DA_TAO")
        self.assertEqual(self.y()["so_lan_tao"], 2)

    def test_timeout_chua_thuc_hien_van_la_chua_ro(self):
        self.fake.tiem("POST_DE_XUAT", "TIMEOUT")
        self.assertEqual(self.tao()["trang_thai"], "CHUA_RO_TAO")
        self.assertEqual(self.fake.de_xuat, {})
        self.assertEqual(self.doi_soat()["trang_thai"], "CHO_QUET")
        self.mot_request()

    def test_chac_chan_chua_tao(self):
        for hanh, mong in (("KET_NOI", "REQUEST_KET_NOI"), (("HTTP", 429, {"loi": "x"}, {"Retry-After": "30"}), "REQUEST_429"),
                           (("HTTP", 503, {"loi": "x"}), "REQUEST_503"), (("HTTP", 422, {"loi": "x", "loiTheoTruong": {"nguoiTao": "sai"}}), "REQUEST_422")):
            with self.subTest(mong=mong):
                self.setUp()
                self.fake.tiem("POST_DE_XUAT", hanh)
                r = self.tao()
                self.assertEqual((r["trang_thai"], r["loi"][0]["ma"], r["loi"][0]["khong_ro"], self.y()["co_chua_ro"]), ("TU_CHOI_TAO", mong, False, False))
                self.assertEqual(self.fake.de_xuat, {})
        self.assertEqual(r["loi"][0]["truong"], ["nguoiTao"])
        self.assertNotIn("sai", json.dumps(r["loi"]))

    def test_500_tren_post_la_chua_ro(self):
        self.fake.tiem("POST_DE_XUAT", ("HTTP", 500, {"loi": "x"}))
        r = self.tao()
        self.assertEqual((r["trang_thai"], r["loi"][0]["ma"], r["loi"][0]["khong_ro"]), ("CHUA_RO_TAO", "REQUEST_HTTP_500", True))

    def test_tu_choi_roi_chua_ro_khong_bi_che(self):
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK", "KET_NOI")
        self.assertEqual(self.tao()["trang_thai"], "CHUA_RO_TAO")
        r = self.doi_soat()
        self.assertEqual(r["trang_thai"], "TU_CHOI_TAO")
        self.assertTrue(self.y()["co_chua_ro"], "đã từng chưa rõ — cờ không được mất")
        self.dh.gio = 21
        self.assertEqual(self.doi_soat()["chan"], "CHUA_RO_QUA_HAN_IDEM")


class R05MatAckTai(CoSo):
    def test_mat_ack_tai_len_doi_soat_ung_vien(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        r = self.tao()
        self.assertEqual((r["trang_thai"], r["buoc"]), ("CHUA_RO_TAI", ["TAO", "DOC", "TAI", "DOI_SOAT"]))
        x = self.mot_request()
        self.assertEqual(len(x["tep"]), 1)
        tid = x["tep"][0]
        self.assertIsNone(self.y()["remote_tep_id"])
        r = self.doi_soat()
        self.assertEqual(r["trang_thai"], "CHUA_RO_TAI")  # pending: chưa xác nhận, KHÔNG tải lại
        self.fake.quet(tid, "clean")
        r = self.doi_soat()
        self.assertEqual(r["trang_thai"], "DA_DOI_SOAT")
        self.assertEqual((self.y()["remote_tep_id"], self.y()["doi_soat_sha256"]), (tid, PDF_SHA))
        self.assertEqual(self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep"), 1)
        self.assertEqual(len(self.fake.tep), 1)

    def test_mat_ack_ma_nguon_khong_luu(self):
        self.fake.tiem("POST_TEP", "TIMEOUT")
        self.assertEqual(self.tao()["trang_thai"], "CHUA_RO_TAI")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep")), ("CHUA_RO_TAI", 1))
        self.assertEqual(self.kho.su_kien[-1][1:4], ("GHI_DOI_SOAT", "CHUA_RO_TAI", "CHUA_RO_TAI"))  # không ứng viên → đối soát tay (giới hạn đã báo cáo)

    def test_tai_len_chua_gui(self):
        self.fake.tiem("POST_TEP", "KET_NOI")
        r = self.tao()
        self.assertEqual(r["trang_thai"], "DA_TAO_NHAP")
        self.assertEqual(self.fake.tep, {})
        r = self.doi_soat()
        self.assertEqual(r["trang_thai"], "CHO_QUET")
        self.assertEqual(len(self.fake.tep), 1)


class R06PhatLai(CoSo):
    def test_phat_lai_dung_khoa(self):
        k = self.K("cung")
        r1 = self.tao(k)
        r2 = self.tao(k)
        self.assertEqual((r1["lap_lai"], r2["lap_lai"]), (False, True))
        self.assertEqual(r2["y_dinh"]["id"], r1["y_dinh"]["id"])
        self.assertEqual(self.fake.dem("POST", "/api/v1/de-xuat"), 1)
        self.assertEqual(self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep"), 1)

    def test_cung_khoa_khac_hanh_dong(self):
        k = self.K("x")
        self.tao(k)
        n = len(self.fake.nhat_ky)
        self.assertEqual(self.loi(self.doi_soat, k), "M4_IDEMPOTENCY_KHAC")
        self.assertEqual(len(self.fake.nhat_ky) - n, 2, "chỉ GET nhóm/danh mục trước khi biên nhận chặn — không POST")
        self.assertEqual(self.fake.dem("POST", "/api/v1/de-xuat"), 1)

    def test_khoa_moi_cung_intent(self):
        r1 = self.tao(self.K("1"))
        r2 = self.tao(self.K("2"))
        self.assertEqual(r2["y_dinh"]["id"], r1["y_dinh"]["id"])
        self.assertEqual(len(self.kho.y), 1)
        self.mot_request()

    def test_doi_soat_chua_co_intent(self):
        self.assertEqual(self.loi(self.doi_soat), "M4_REQUEST_CHUA_CO_Y_DINH")
        self.assertEqual(self.ghi_io(), [])


class R07DongThoiKhoiDong(CoSo):
    def test_lenh_thu_hai_giua_luc_post(self):
        kq = {}

        def chen(_fake):
            kq["ma"] = self.loi(self.tao, self.K("song-song"))
        self.fake.tiem("POST_DE_XUAT", chen)
        r = self.tao(self.K("chinh"))
        self.assertEqual(kq["ma"], "M4_REQUEST_DANG_XU_LY")
        self.assertEqual(r["trang_thai"], "CHO_QUET")
        self.assertEqual(self.fake.dem("POST", "/api/v1/de-xuat"), 1)
        self.mot_request()

    def test_khoi_dong_lai(self):
        self.fake.tiem("POST_DE_XUAT", "SAP")
        with self.assertRaises(SapTienTrinh):
            self.tao(self.K("a"))
        self.assertEqual((self.y()["trang_thai"], self.y()["lease_buoc"], self.y()["remote_id"]), ("MOI", "TAO", None))
        x = self.mot_request()
        self.assertEqual(self.loi(self.doi_soat, self.K("b")), "M4_REQUEST_DANG_XU_LY")
        self.dh.gio += 1  # lease 180 giây đã hết
        rq_moi = self.rq()  # tiến trình mới
        r = self.doi_soat(self.K("c"), rq=rq_moi)
        self.assertIn(("LEASE_HET", "MOI", "CHUA_RO_TAO"), [e[1:4] for e in self.kho.su_kien])
        self.assertEqual(r["trang_thai"], "CHO_QUET")
        self.assertEqual(self.mot_request()["id"], x["id"])

    def test_lease_het_buoc_tai(self):
        self.fake.tiem("POST_TEP", "SAP")
        with self.assertRaises(SapTienTrinh):
            self.tao()
        self.dh.gio += 1
        r = self.doi_soat()
        self.assertIn(("LEASE_HET", "DA_TAO_NHAP", "CHUA_RO_TAI"), [e[1:4] for e in self.kho.su_kien])
        self.assertEqual((r["trang_thai"], self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep")), ("CHUA_RO_TAI", 1))

    def test_lease_mat_khong_ghi_de(self):
        y = None

        def cuop(_fake):
            nonlocal y
            y = self.y()
            y["revision"] += 1  # bước khác đã ghi
        self.fake.tiem("POST_DE_XUAT", cuop)
        self.assertEqual(self.loi(self.tao), "M4_REQUEST_LEASE_MAT")


class R08CuaSoXoayKhoa(CoSo):
    def test_qua_20h_hold(self):
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        self.tao()
        self.dh.gio = 20.5
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], r["chan"], self.y()["hold_ma"]), ("HOLD", "CHUA_RO_QUA_HAN_IDEM", "CHUA_RO_QUA_HAN_IDEM"))
        self.assertEqual(self.fake.dem("POST", "/api/v1/de-xuat"), 1)
        r = self.tao()
        self.assertEqual(self.fake.dem("POST", "/api/v1/de-xuat"), 1)
        self.assertEqual(r["trang_thai"], "HOLD")

    def test_trong_cua_so(self):
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        self.tao()
        self.dh.gio = 19.5
        self.assertEqual(self.doi_soat()["trang_thai"], "CHO_QUET")
        self.mot_request()

    def test_doi_chung_nguon_qua_24h_va_khoa_moi_tao_trung(self):
        c = RA.RequestClient(self.fake)
        a = c.tao_nhap(BODY_MONG, "m4-request:doi-chung")
        self.assertEqual(c.tao_nhap({**BODY_MONG, "tieuDe": "body khác"}, "m4-request:doi-chung"), RA.NhapTao(a.id, a.ma, "draft", False))  # không so body
        self.dh.gio = 24.5
        self.assertNotEqual(c.tao_nhap(BODY_MONG, "m4-request:doi-chung").id, a.id)
        self.fake.khoa_api = "k2"
        self.dh.gio = 25
        self.assertEqual(len({c.tao_nhap(BODY_MONG, "m4-request:doi-chung").id, a.id}), 2)
        self.assertEqual(len(self.fake.de_xuat), 3)

    def test_xoay_khoa_can_cu_doi(self):
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        self.tao()
        self.fake.khoa_api = "k2"
        r = self.doi_soat(rq=self.rq(ch=cau_hinh(khoa_ref="khoa-demo:2")))
        self.assertEqual((r["trang_thai"], r["chan"]), ("HOLD", "CAN_CU_DOI"))
        self.assertEqual(self.fake.dem("POST", "/api/v1/de-xuat"), 1)
        self.assertEqual(self.y()["trang_thai"], "CHUA_RO_TAO", "intent giữ nguyên bằng chứng; HOLD chỉ là kết quả lệnh")


class R09DanhSachNonDraft(CoSo):
    def test_danh_sach_rong(self):
        c = RA.RequestClient(self.fake)
        self.assertEqual(c.danh_sach(nhom=NHOM_MA), {"duLieu": [], "tongSo": 0})
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        self.tao()
        self.assertEqual(c.danh_sach(), {"duLieu": [], "tongSo": 0})  # fake trả rỗng dù đã tạo: danh sách không là bằng chứng
        self.assertEqual(self.doi_soat()["trang_thai"], "CHO_QUET")
        self.mot_request()

    def test_khong_con_draft(self):
        def doi(fake):
            next(iter(fake.de_xuat.values()))["trangThai"] = "in_review"
        self.fake.tiem("GET_DE_XUAT", doi)
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["remote_trang_thai"]), ("HOLD", "KHONG_CON_NHAP", "in_review"))
        self.assertEqual(self.fake.tep, {})
        self.assertEqual(self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep"), 0)

    def test_tra_lai_truoc_khi_tai(self):
        def doi(fake):
            next(iter(fake.de_xuat.values()))["trangThai"] = "returned"
        self.fake.tiem("GET_DE_XUAT", None, doi)  # GET thứ nhất (DOC) bình thường; GET trước tải đổi trạng thái
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "KHONG_CON_NHAP"))
        self.assertEqual(self.fake.tep, {})

    def test_404_sau_tao(self):
        self.fake.tiem("GET_DE_XUAT", ("HTTP", 404, {"loi": "KHONG_THAY"}))
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "REQUEST_KHONG_THAY"))


class R10Drift(CoSo):
    def test_nhom_truong_danh_muc(self):
        tt_text = nhom_json()
        tt_text["truong"][0]["kieu"] = "text"
        dm_sai = nhom_json()
        dm_sai["truong"][1]["danhMuc"] = "KHAC"
        tep0 = nhom_json()
        tep0["truong"][2]["cauHinh"] = {"maxFiles": 0}
        ca = [(nhom_json(phienBan=4), None, ["NHOM_PHIEN_BAN_DOI"]), (tt_text, None, ["TRUONG_TIEN_LECH"]), (dm_sai, None, ["TRUONG_PHAP_NHAN_LECH"]),
              (tep0, None, ["TRUONG_TEP_LECH"]), (nhom_json(ma="KHAC"), None, ["NHOM_KHONG_THAY"]),
              (nhom_json(), {"ma": DM_PN, "giaTri": [{"ma": PN_MA, "dangDung": False}]}, ["MA_PHAP_NHAN_KHONG_CO"])]
        for nhom, dm, mong in ca:
            with self.subTest(mong=mong):
                self.fake = FakeRequest(self.dh, nhom=nhom, danh_muc=dm)
                r = self.tao()
                self.assertEqual((r["trang_thai"], r["thieu"]), ("CAU_HINH_LECH", mong))
                self.assertEqual((self.ghi_io(), self.kho.y), ([], {}))

    def test_nhom_doi_sau_intent(self):
        self.fake.tiem("POST_DE_XUAT", "MAT_ACK")
        self.tao()
        n = nhom_json()
        n["truong"][0]["nhan"] = "Số tiền (đổi nhãn)"  # nhãn không thuộc dấu vân → vẫn cùng căn cứ
        self.fake.nhom = [n]
        self.assertEqual(self.doi_soat()["trang_thai"], "CHO_QUET")
        n2 = nhom_json()
        n2["truong"][0]["batBuoc"] = False  # định nghĩa đổi → dấu vân nhóm đổi → căn cứ đổi
        self.fake.nhom = [n2]
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], r["chan"]), ("HOLD", "CAN_CU_DOI"))

    def test_loi_doc_nhom(self):
        self.fake.tiem("GET_NHOM", ("HTTP", 401, {"loi": "x"}))
        r = self.tao()
        self.assertEqual((r["trang_thai"], r["loi"]), ("LOI_REQUEST", [{"buoc": "CAU_HINH", "ma": "REQUEST_401", "status": 401, "retry_after": None,
                                                                         "khong_ro": False, "truong": []}]))
        self.assertEqual((self.ghi_io(), self.kho.y), ([], {}))

    def test_chi_tiet_lech(self):
        ca = [(lambda d: {**d, "giaTri": {**d["giaTri"], T_TIEN: {"amount": "31500000.00", "currency": "VND"}}, "tongTien": None}, "SO_TIEN_LECH"),
              (lambda d: {**d, "tongTien": {"amount": "1", "currency": "VND"}}, "TONG_TIEN_LECH"),
              (lambda d: {**d, "nguoiTao": {"tenDangNhap": CHU_KHOA}}, "NGUOI_TAO_LECH"),
              (lambda d: {**d, "nhom": {"ma": "KHAC"}}, "NHOM_LECH"),
              (lambda d: {**d, "giaTri": {**d["giaTri"], T_PN: "PN_CU"}}, "PHAP_NHAN_LECH"),
              (lambda d: {**d, "truong": [t for t in d["truong"] if t["ma"] != T_TEP]}, "TRUONG_LECH"),
              (lambda d: {**d, "taoQuaApi": False}, "KHONG_TAO_QUA_API")]
        for bd, mong in ca:
            with self.subTest(mong=mong):
                self.setUp()
                self.fake.bien_doi_chi_tiet = bd
                r = self.tao()
                self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", mong))
                self.assertEqual(self.fake.tep, {})

    def test_kiem_nhom_thuan(self):
        n = RA.NhomRequest.tu(nhom_json())
        self.assertEqual(RN.kiem_nhom(cau_hinh(), n), [])
        self.assertEqual(RN.kiem_nhom(cau_hinh(), None), ["NHOM_KHONG_THAY"])
        self.assertEqual(RN.kiem_nhom(cau_hinh(truong_tep="khong_co", phien_ban=2), n), ["NHOM_PHIEN_BAN_DOI", "TRUONG_TEP_LECH"])
        self.assertEqual(RN.kiem_nhom(cau_hinh(), RA.NhomRequest.tu(nhom_json(truongTongTien="khac"))), ["TRUONG_TIEN_LECH"])
        self.assertEqual(n.truong_theo_ma(T_TEP).toi_da_tep, 2)
        self.assertEqual(RN.tieu_de("HĐ\n1", 2), "Thanh toán HĐ HĐ 1 — đợt 2")
        self.assertEqual(len(RN.tieu_de("x" * 400, 1)), 200)
        self.assertEqual([RN.buoc_tiep(t, set(), r) for t, r in (("MOI", False), ("CHUA_RO_TAO", False), ("DA_TAO", True), ("DA_TAO_NHAP", True),
                                                                  ("CHO_QUET", True), ("CHUA_RO_TAI", True), ("HOLD", True), ("HOLD", False))],
                         ["TAO", "TAO", "DOC", "TAI", "DOI_SOAT", "DOI_SOAT", "DOC", None])
        self.assertIsNone(RN.buoc_tiep("CHO_QUET", {"DOI_SOAT"}, True))


class R11QuetHash(CoSo):
    def tep_id(self):
        return self.mot_request()["tep"][0]

    def test_quet_loi_va_nhiem(self):
        self.tao()
        self.fake.quet(self.tep_id(), "error")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_QUET_LOI"))
        self.assertEqual(self.fake.dem("GET", r"/api/v1/tep/.*"), 0)
        self.setUp()
        self.tao()
        self.fake.quet(self.tep_id(), "infected")
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_NHIEM"))
        self.setUp()
        self.fake.quet_mac_dinh = "infected"
        self.assertEqual((self.tao()["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_NHIEM"))

    def test_hash_sai(self):
        self.tao()
        t = self.fake.tep[self.tep_id()]
        t["bytes"] = bytes([t["bytes"][0] ^ 1]) + t["bytes"][1:]  # cùng độ dài, khác nội dung
        self.fake.quet(t["meta"]["id"], "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["doi_soat_sha256"]), ("HOLD", "TEP_HASH_LECH", None))
        self.assertEqual(self.fake.dem("GET", r"/api/v1/tep/.*"), 1)

    def test_trung_khop(self):
        self.fake.tiem("POST_TEP", "MAT_ACK")
        self.tao()
        x = self.mot_request()
        goc = self.fake.tep[x["tep"][0]]
        tid2 = str(uuid.uuid4())  # bản thứ hai cùng bytes (vd người dùng tải tay) trong cùng ô
        self.fake.tep[tid2] = {"meta": {**goc["meta"], "id": tid2}, "bytes": goc["bytes"]}
        x["tep"].append(tid2)
        for t in x["tep"]:
            self.fake.quet(t, "clean")
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"], self.y()["remote_tep_id"]), ("HOLD", "TEP_TRUNG_KHOP", None))

    def test_lech_kich_thuoc_khi_tai(self):
        def lech(fake):
            orig = fake._tai

            def tai(rid, h, b):
                r = orig(rid, h, b)
                d = json.loads(r.body)
                d["duLieu"]["kichThuoc"] += 1
                return RA.PhanHoi(201, r.headers, json.dumps(d).encode())
            fake._tai = tai
        self.fake.tiem("POST_TEP", lech)
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_LECH"))

    def test_lech_kich_thuoc_khi_doi_soat(self):
        self.tao()
        t = self.fake.tep[self.tep_id()]
        t["meta"]["kichThuoc"] = PDF_LEN + 1
        t["meta"]["trangThaiQuet"] = "clean"
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_HASH_LECH"))
        self.assertEqual(self.fake.dem("GET", r"/api/v1/tep/.*"), 0, "kích thước lệch → không tải bytes")

    def test_tep_mat(self):
        self.tao()
        self.mot_request()["tep"].clear()
        self.assertEqual((self.doi_soat()["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_MAT"))

    def test_pdf_seal_hong(self):
        self.xd.raw = PDF_RAW[:-1] + b"X"
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "PDF_SEAL_LECH"))
        self.assertEqual(self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep"), 0)

    def test_tep_day(self):
        n = nhom_json()
        n["truong"][2]["cauHinh"] = {"maxFiles": 1}
        self.fake.nhom = [n]

        def co_san(fake):
            x = next(iter(fake.de_xuat.values()))
            tid = str(uuid.uuid4())
            fake.tep[tid] = {"meta": {"id": tid, "tenTep": "khac.pdf", "maTruong": T_TEP, "khuChung": False, "kichThuoc": 3, "mime": "application/pdf",
                                      "trangThaiQuet": "clean"}, "bytes": b"abc"}
            x["tep"].append(tid)
        self.fake.tiem("GET_DE_XUAT", lambda _f: None, co_san)
        r = self.tao()
        self.assertEqual((r["trang_thai"], self.y()["hold_ma"]), ("HOLD", "TEP_DAY"))


class R12ThuHoi(CoSo):
    def test_thu_hoi_giua_luc_post(self):
        def thu_hoi(_fake):
            self.kho.q.update(anh_xa=False, anh_xa_id=None, nguoi_tao=None)
        self.fake.tiem("POST_DE_XUAT", thu_hoi)
        self.assertEqual(self.loi(self.tao), "M4_REQUEST_PHAM_VI_DA_DOI")
        x = self.mot_request()
        self.assertEqual((self.y()["trang_thai"], self.y()["remote_id"]), ("DA_TAO", x["id"]))  # bằng chứng đã ghi
        self.assertEqual(self.kho.su_kien[-1][1:], ("GHI_TAO", "MOI", "DA_TAO", False))
        n = len(self.fake.nhat_ky)
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], r["thieu"]), ("CHUA_CAU_HINH", ["anh_xa_nhan_vien"]))
        self.assertEqual(len(self.fake.nhat_ky), n)
        self.kho.q.update(anh_xa=True, anh_xa_id=ID["ax2"], anh_xa_revision=2, nguoi_tao=NV)  # mapping mới (revision 2)
        r = self.doi_soat()
        self.assertEqual((r["trang_thai"], r["chan"]), ("HOLD", "ANH_XA_DOI"))
        self.assertEqual(self.fake.dem("POST", r"/api/v1/de-xuat/.*/tep"), 0)

    def test_mat_vai_giua_luc_tai(self):
        def mat(_fake):
            self.kho.q.update(tai_pdf=False)
        self.fake.tiem("POST_TEP", mat)
        self.assertEqual(self.loi(self.tao), "M4_REQUEST_PHAM_VI_DA_DOI")
        self.assertEqual(self.y()["trang_thai"], "CHO_QUET")
        n = len(self.fake.nhat_ky)
        self.assertEqual(self.loi(self.doi_soat), "M4_REQUEST_PHAM_VI")
        self.assertEqual(len(self.fake.nhat_ky), n)

    def test_nguoi_khac_khong_tiep_quan(self):
        self.tao()
        dt_khac = {"id": str(uuid.uuid4()), "dang_nhap": "MO_PHONG_KHAC"}
        with self.assertRaises(DataError) as cm:
            self.kho.giu(dt_khac, "k-khac", RN.HANH_TAO, {}, ID["dot"], ID["seal"], {}, "0" * 64, "TAO", 180)
        self.assertEqual(cm.exception.code, "M4_REQUEST_NGUOI_KHAC")


class R13ClientSql(unittest.TestCase):
    def goi(self, st, body=b"{}", headers=None, phuong="GET"):
        class T:
            kich_hoat = True

            def gui(self, *a):
                return RA.PhanHoi(st, {k.lower(): v for k, v in (headers or {}).items()}, body if isinstance(body, bytes) else json.dumps(body).encode())
        c = RA.RequestClient(T())
        try:
            if phuong == "POST":
                c.tao_nhap(BODY_MONG, "k")
            else:
                c.chi_tiet(str(uuid.UUID(int=5)))
        except RA.LoiRequest as exc:
            return exc.tom_tat()
        return None

    def test_anh_xa_loi(self):
        self.assertEqual(self.goi(429, {"loi": "x"}, {"Retry-After": "7"}), {"ma": "REQUEST_429", "status": 429, "retry_after": 7, "khong_ro": False, "truong": []})
        self.assertEqual(self.goi(503, {"loi": "x"}, {"Retry-After": "99999999"}, "POST"),
                         {"ma": "REQUEST_503", "status": 503, "retry_after": None, "khong_ro": False, "truong": []})
        self.assertEqual(self.goi(500, {"loi": "x"}, phuong="POST")["khong_ro"], True)
        self.assertEqual(self.goi(500, {"loi": "x"})["khong_ro"], False)
        self.assertEqual(self.goi(502, {"loi": "x"}, phuong="POST")["ma"], "REQUEST_HTTP_502")
        self.assertEqual(self.goi(422, {"loi": "x", "loiTheoTruong": {"b": "câu thô", "a": "x", "x y": "bỏ"}}, phuong="POST")["truong"], ["a", "b"])
        self.assertEqual(self.goi(302, b"", {"Location": "https://evil"})["ma"], "REQUEST_CHUYEN_HUONG")
        self.assertEqual(self.goi(200, b"<html>")["ma"], "REQUEST_PHAN_HOI_SAI")
        self.assertEqual(self.goi(201, {"khac": 1}, phuong="POST"), {"ma": "REQUEST_PHAN_HOI_SAI", "status": 201, "retry_after": None, "khong_ro": True,
                                                                    "truong": []})
        self.assertEqual(self.goi(200, {"duLieu": {"id": str(uuid.UUID(int=6)), "trangThai": "draft", "nhom": {"ma": "N"}}})["ma"], "REQUEST_PHAN_HOI_SAI")
        self.assertEqual(self.goi(202, {"duLieu": {"id": str(uuid.UUID(int=6))}}, phuong="POST")["khong_ro"], True)

    def test_truyen_va_doc_do(self):
        class T:
            def __init__(self, da_gui):
                self.da_gui = da_gui

            def gui(self, *a):
                raise RA.LoiTruyen(self.da_gui)
        for da_gui, mong in ((False, ("REQUEST_KET_NOI", False)), (True, ("REQUEST_KHONG_RO", True))):
            with self.assertRaises(RA.LoiRequest) as cm:
                RA.RequestClient(T(da_gui)).tao_nhap(BODY_MONG, "k")
            self.assertEqual((cm.exception.ma, cm.exception.khong_ro), mong)
        with self.assertRaises(RA.LoiRequest) as cm:
            RA.RequestClient(T(True)).tai_ve(str(uuid.UUID(int=5)), 10)
        self.assertEqual((cm.exception.ma, cm.exception.khong_ro), ("REQUEST_DOC_DO", False))

    def test_multipart(self):
        bd, raw = RA.multipart({"maTruong": T_TEP}, "tep", "a.pdf", "application/pdf", PDF_RAW)
        self.assertTrue(re.fullmatch(r"m4req[0-9a-f]{32}", bd))
        self.assertTrue(raw.startswith(f'--{bd}\r\nContent-Disposition: form-data; name="maTruong"\r\n\r\nho_so_duyet\r\n'.encode()))
        self.assertIn(b'name="tep"; filename="a.pdf"\r\nContent-Type: application/pdf\r\n\r\n' + PDF_RAW + f"\r\n--{bd}--\r\n".encode(), raw)

    def test_cau_hinh_sha_on_dinh(self):
        a, b = cau_hinh(), cau_hinh(khoa_chu_dang_nhap=CHU_KHOA.upper())
        self.assertEqual(a.sha256(), b.sha256())
        self.assertNotEqual(a.sha256(), cau_hinh(khoa_ref="khoa-demo:2").sha256())
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", a.sha256()))
        self.assertEqual(cau_hinh().thieu(), [])
        self.assertEqual(cau_hinh(khoa_ref="có dấu").thieu(), ["khoa_ref"])
        self.assertEqual(cau_hinh(truong_tep="../x").thieu(), ["truong_tep"])

    def test_hang_sql_mot_constant_khong_registry(self):
        from kho_tri_thuc.m4 import sql_request_nhap as S
        hang = [k for k, v in vars(S).items() if k.isupper() and isinstance(v, tuple) and v and all(isinstance(x, str) for x in v)
                and any("CREATE" in x for x in v)]
        self.assertEqual(hang, ["M4_REQUEST_NHAP"])
        sql = "\n".join(S.M4_REQUEST_NHAP)
        for cam in ("DROP ", "TRUNCATE", "DELETE FROM", "schema_migrations", "SET ROLE", "BYPASSRLS", "SUPERUSER"):
            self.assertNotIn(cam, sql.upper() if cam.isupper() else sql, cam)
        for bang in S.BANG:
            self.assertIn(f"CREATE TABLE m4.{bang} (", sql)
            self.assertIn(f"ALTER TABLE m4.{bang} ENABLE ROW LEVEL SECURITY", sql)
        self.assertIn("UNIQUE (seal_id, nhanh)", sql)
        from kho_tri_thuc.ha_tang import pg_migrations as PM
        raw = (GOC / "src" / "kho_tri_thuc" / "ha_tang" / "pg_migrations.py").read_bytes()
        self.assertGreaterEqual(len(raw), 973_783)
        self.assertEqual(hashlib.sha256(raw[:973_783]).hexdigest(), "682131e655ff7b15470ecac3c47e2b9a666645321ac558eca8d692718af51f89")
        self.assertEqual(PM.PG_SCHEMA_VERSION, len(PM.PG_MIGRATIONS))
        self.assertGreaterEqual(len(PM.PG_MIGRATIONS), 27)
        self.assertIs(PM.PG_MIGRATIONS[26], S.M4_REQUEST_NHAP)
        self.assertIs(PM.M0027_M4_REQUEST, S.M4_REQUEST_NHAP)
        self.assertIs(PM.M4_REQUEST_NHAP, S.M4_REQUEST_NHAP)
        self.assertEqual([i for i, m in enumerate(PM.PG_MIGRATIONS) if m is S.M4_REQUEST_NHAP], [26])
        self.assertEqual(S.CUA_SO_GUI_LAI_GIO, 20)
        self.assertLess(S.CUA_SO_GUI_LAI_GIO, 24)


if __name__ == "__main__":
    unittest.main()
