"""CRM-41-01 — kiểm client chung engine #6 + projection + wiring hai consumer (M4, CRM). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN_CODE_ONLY).

Phân loại rõ:
- `ClientIoMockTests`, `ProjectionTests`: kiểm ĐƠN VỊ với transport giả lập (IO-mock) — chứng minh giao thức/đối soát/xung đột/UNKNOWN của
  client, KHÔNG chứng minh engine trích đúng.
- `WiringTests`: kiểm tĩnh + gọi thật hàm consumer với client giả (không PG) — đường M4/CRM đi qua client chung, không còn lõi chép.
- `ApiNguonThatTests`: gọi API engine #6 THẬT (đã áp patch) khi Root cấp KHO_TRICH6_URL lúc chạy; thiếu → skip = NOT_RUN. DOCX DEMO tổng hợp
  không rỗng (kiem_chung/fixtures_m4.hop_dong_docx). Chỉ là API nguồn/client — KHÔNG gọi XayDungK2/CrmK2/HTTP central/PG.
FIX01: F1 (gốc thật, ID 'm4:…'/'.'/'..' → thư mục băm trong gốc), F2 (IO-mock: mất ACK create/upload/start sau khi máy chủ đã xử lý, đứt GET/raw,
  ba caller cùng ý định → một lượt/một lần chạy; NR: chưa rõ → ChuaRo), F4 (UNIT trên đối tượng thay thế, quyền stub có ghi rõ: ý định CRM đầy đủ
  ở máy chủ), F5 (TĨNH trên app.js — chưa phải kiểm trình duyệt).
Không AI/cloud/OCR/mạng ngoài loopback; thư mục tạm giữ lại.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from kho_tri_thuc.ha_tang.primitives import DataError, sha256
from kho_tri_thuc.nguon import trich_chung_6 as T6

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "kho_tri_thuc"
CAT = T6.CATALOG["XD"]["catalog_sha256"]
MA4 = ["TC-01", "TC-02", "TT-02", "TT-10"]


def _bang(ma, *, rule=("TC-01",)):
    return [{"ma": m, "nhom": "N", "tham_so": m, "mo_ta": m, "gia_tri": ("HD-01" if m in rule else ""), "don_vi": "",
             "dieu_khoan": "", "trich_dan": ("Số: HD-01" if m in rule else ""), "ghi_chu": "", "kiem_tra": "OK" if m in rule else "CHƯA CHẠY AI",
             "vi_tri_do_duoc": "Điều 1", "nguon": "Quy tắc" if m in rule else "Chưa chạy AI"} for m in ma]


class NguonGia:
    """Engine #6 giả lập ở mức HTTP (IO-mock) — đúng hình dạng API nguồn; dùng để kiểm client, không kiểm thuật toán trích."""

    def __init__(self, ma=MA4):
        self.ma, self.goi, self.luot, self.tep, self.chay_body, self.dut = list(ma), [], 0, {}, {}, set()
        self.dut_sau = set()     # FIX01: mất ACK SAU khi máy chủ đã xử lý (tác động đã xảy ra)
        self.y_dinh = {}         # create common idempotent: request_id → (body, luot)
        self.khoa = __import__("threading").Lock()
        self.sua_tt = None       # FIX03: hook sửa trạng thái GET (bỏ common/seal, sai ý định/ref…) để kiểm cổng nhận của client
        # FIX04 R5: preflight typed đúng DTO nguồn (dich_vu.nang_luc_common) và hook sửa ACK create
        self.nang_luc = (200, {"kieu": "nang_luc_common/v1", "contract": T6.CONTRACT, "modes": ["RULE_ONLY"], "san_sang": True,
                               "loai": {"XD": {"catalog_id": "XD", "catalog_sha256": CAT, "san_sang": True, "ly_do": None}},
                               "implementation_sha256": "b" * 64, "implementation_thieu": [], "create_ack": ["luot", "lap_lai", "request_id"]})
        self.sua_ack = None

    def __call__(self, method, path, headers, body):
        with self.khoa:
            return self._xu_ly(method, path, headers, body)

    def _xu_ly(self, method, path, headers, body):
        self.goi.append((method, path.split("?")[0], headers.get("X-HD"), headers.get("Host")))
        k = (method, path.split("?")[0].rsplit("/", 1)[-1])
        if k in self.dut:
            self.dut.discard(k)
            raise ConnectionResetError("đứt trước khi tới máy chủ")
        kq = self._tra_loi(method, path, body)
        if k in self.dut_sau:
            self.dut_sau.discard(k)
            raise ConnectionResetError("đứt sau khi máy chủ đã xử lý")
        return kq

    def _tra_loi(self, method, path, body):
        if method == "GET" and path == "/api/trich_xuat/common":
            st, v = self.nang_luc
            return st, "application/json", (v if isinstance(v, bytes) else json.dumps(v).encode())
        if method == "POST" and path == "/api/trich_xuat":
            b = json.loads(body or b"{}")
            if "contract" in b:  # create common/v1 idempotent theo request_id + yêu cầu (đúng DTO route nguồn đã patch: luot, lap_lai, request_id)
                cu = self.y_dinh.get(b["request_id"])
                if cu is not None:
                    if cu[0] != b["yeu_cau"]:
                        return 409, "application/json", json.dumps({"loi": "x", "chi_tiet": {"ma": "COMMON_XUNG_DOT"}}).encode()
                    ack = {"luot": cu[1], "lap_lai": True, "request_id": b["request_id"]}
                else:
                    self.luot += 1
                    self.y_dinh[b["request_id"]] = (b["yeu_cau"], f"20261021_10000{self.luot}")
                    ack = {"luot": f"20261021_10000{self.luot}", "lap_lai": False, "request_id": b["request_id"]}
                if self.sua_ack is not None:
                    ack = self.sua_ack(ack)
                return 200, "application/json", json.dumps(ack).encode()
            self.luot += 1
            return 200, "application/json", json.dumps({"luot": f"20261021_10000{self.luot}"}).encode()
        if method == "GET" and path.startswith("/tai/"):
            return self._ket_qua(path.split("/")[3])
        m = re.fullmatch(r"/api/trich_xuat/(\d{8}_\d{6})(/.*)?", path.split("?")[0])
        if m is None:
            return 404, "application/json", b'{"loi": "khong co"}'
        lu, duoi = m.group(1), m.group(2) or ""
        if method == "POST" and duoi == "/tep" and lu not in self.chay_body:
            self.tep[lu] = body
            return 200, "application/json", b'{"ok": true}'
        if method == "POST" and duoi == "/chay":
            yc = json.loads(body)
            if lu in self.chay_body:
                if self.chay_body[lu] != yc:
                    return 409, "application/json", json.dumps({"loi": "x", "chi_tiet": {"ma": "COMMON_XUNG_DOT"}}).encode()
                return 200, "application/json", json.dumps({"lap_lai": True, "luot": lu}).encode()
            self.chay_body[lu] = yc
            return 200, "application/json", json.dumps({"lap_lai": False, "luot": lu}).encode()
        if method == "POST" and duoi == "/tep" and lu in self.chay_body:
            return 409, "application/json", b'{"loi": "Luot nay da chay"}'
        if method == "GET" and duoi == "":
            if lu not in self.chay_body:
                return 200, "application/json", json.dumps({"tt": "chua_chay", "tep_dau_vao": ["hop_dong.docx"] if lu in self.tep else [], "hd": []}).encode()
            # FIX03: hình dạng nguồn đã patch — 'xong' chỉ đi kèm common done + niêm phong sidecar typed (ref tương đối, SHA/độ dài raw thật)
            yc, raw = self.chay_body[lu], self._raw(lu)
            bh = T6.body_sha256(yc)
            s = {"tt": "xong", "tep_dau_vao": ["hop_dong.docx"], "hd": [{"tai": {"json": f"/tai/ket_qua/{lu}/x/x_KET_QUA.json"}}],
                 "common": {"tt": "done", "request_id": yc["request_id"], "body_sha256": bh,
                            "seal": {"kieu": "seal_common/v1", "ref": "x/x_KET_QUA.json", "sha256": sha256(raw), "byte_length": len(raw),
                                     "request_id": yc["request_id"], "body_sha256": bh, "request_sha256": "e" * 64, "meta_sha256": "f" * 64}}}
            if self.sua_tt is not None:
                s = self.sua_tt(lu, s)
            return 200, "application/json", json.dumps(s).encode()
        return 404, "application/json", b'{"loi": "khong co"}'

    def _raw(self, lu):
        yc = self.chay_body[lu]
        dung = self.ma if yc["tham_so"] == "ALL" else yc["tham_so"]
        kq = {"hop_dong": "x.docx", "ten": "x", "che_do": "RULE_ONLY", "tao_luc": "2026-10-21T10:00:00", "bang": _bang(dung),
              "phieu_kiem_tra": {}, "common": {**{k: yc[k] for k in ("contract", "request_id", "source_sha256", "catalog_sha256", "loai_hop_dong",
                                                                     "catalog_id", "mode")},
                                              "body_sha256": T6.body_sha256(yc), "tham_so_yeu_cau": yc["tham_so"], "tham_so_da_dung": dung,
                                              "implementation": {"sha256": "b" * 64}}}
        return json.dumps(kq, ensure_ascii=False).encode("utf-8")

    def _ket_qua(self, lu):
        if lu in self.chay_body:  # chỉ lượt đã nhận lệnh chạy mới có tệp kết quả (luồng client chỉ đọc sau khi lượt 'xong')
            return 200, "application/json", self._raw(lu)
        return 404, "application/json", b'{"loi": "khong co"}'


class ClientIoMockTests(unittest.TestCase):
    def client(self, nguon=None, goc=None):
        nguon = nguon or NguonGia()
        return nguon, T6.Trich6Client("http://127.0.0.1:18600", goc=goc, transport=nguon, ngu=lambda s: None)

    def test_url_tuong_minh_loopback(self):
        c = T6.Trich6Client("", transport=None)
        self.assertFalse(c.san_sang)  # thiếu URL → NOT_READY, không mặc định 8600
        with self.assertRaises(DataError) as cm:
            c.trich(b"PK", ten_tep="a.docx", loai_hop_dong="XD", tham_so="ALL", request_id="r1")
        self.assertEqual(cm.exception.code, "TRICH6_CHUA_SAN_SANG")
        for xau in ("http://10.0.0.5:8600", "https://127.0.0.1:1", "http://127.0.0.1", "http://127.0.0.1:1/api", "http://u:p@127.0.0.1:1"):
            with self.assertRaises(DataError, msg=xau):
                T6.Trich6Client(xau)

    def test_trich_all_va_header(self):
        nguon, c = self.client()
        r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="r-all")
        self.assertEqual(r["common"]["tham_so_da_dung"], MA4)
        self.assertEqual(r["raw_sha256"], sha256(r["raw_ket_qua"]))
        self.assertTrue(all(x == "1" and h == "127.0.0.1:18600" for _m, _p, x, h in nguon.goi))  # X-HD + Host khớp nguồn
        b = nguon.chay_body["20261021_100001"]
        self.assertEqual((b["contract"], b["mode"], b["loai_hop_dong"], b["catalog_sha256"], b["tham_so"]), (T6.CONTRACT, "RULE_ONLY", "XD", CAT, "ALL"))
        self.assertNotIn(("POST", "/api/trich_xuat/20261021_100001/dung", "1", "127.0.0.1:18600"), nguon.goi)  # không dừng ngoài ý định

    def test_loi_ro_truoc_khi_goi(self):
        nguon, c = self.client()
        for ts, ma in (([], "TRICH6_THAM_SO_RONG"), (["TC-01", "TC-01"], "TRICH6_THAM_SO_TRUNG"), ("TC-01", "TRICH6_THAM_SO_SAI_KIEU")):
            with self.assertRaises(DataError) as cm:
                c.trich(b"PK", ten_tep="a.docx", loai_hop_dong="XD", tham_so=ts, request_id="r")
            self.assertEqual(cm.exception.code, ma)
        with self.assertRaises(DataError) as cm:
            c.trich(b"PK", ten_tep="a.docx", loai_hop_dong="KCN", tham_so="ALL", request_id="r")
        self.assertEqual(cm.exception.code, "TRICH6_LOAI_CHUA_CO_DANH_MUC")  # không mượn XD
        self.assertEqual(nguon.goi, [])

    def test_y_dinh_ben_vung_doi_soat_va_xung_dot(self):
        goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_y_dinh_"))  # giữ lại
        nguon, c = self.client(goc=goc)
        nguon.dut.add(("POST", "chay"))  # mất kết nối SAU khi gửi lệnh chạy → UNKNOWN
        with self.assertRaises(T6.ChuaRo):
            c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="r-ud")
        so_luot = nguon.luot
        r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="r-ud")  # thử lại cùng ý định
        self.assertEqual(nguon.luot, so_luot)  # không tạo lượt mới
        self.assertEqual(sum(1 for m, p, *_ in nguon.goi if m == "POST" and p.endswith("/tep")), 1)  # không tải lại
        self.assertEqual(r["common"]["tham_so_da_dung"], ["TC-01"])
        with self.assertRaises(DataError) as cm:  # cùng ý định, khác yêu cầu
            c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-02"], request_id="r-ud")
        self.assertEqual(cm.exception.code, "TRICH6_XUNG_DOT")
        self.assertTrue((goc / "trich6-y-dinh" / sha256(b"r-ud") / f"30_ket_qua_{r['raw_sha256']}.json").is_file())  # FIX01 F1: tên băm

    # ------------------------------------------------------------------ FIX01 F1: thư mục ý định băm trên gốc THẬT (Windows)
    def test_f1_id_logic_co_dau_hai_cham_tren_goc_that(self):
        goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_f1_"))  # thư mục thật, giữ lại
        nguon, c = self.client(goc=goc)
        for rid in ("m4:0123456789abcdef", "crm:a.b-c_d:e", ".", "..", "a..b", "m4:..:x"):
            r = c.trich(b"PK\x03\x04demo-" + rid.encode(), ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id=rid)
            d = goc / "trich6-y-dinh" / sha256(rid.encode("utf-8"))
            self.assertTrue((d / "00_yeu_cau.json").is_file(), rid)
            self.assertEqual(json.loads((d / "00_yeu_cau.json").read_text(encoding="utf-8"))["request_id"], rid)  # ID logic giữ nguyên
            self.assertEqual(d.resolve().parent, (goc / "trich6-y-dinh").resolve())  # không ra ngoài gốc
            self.assertEqual(r["yeu_cau"]["request_id"], rid)
        self.assertEqual(sorted(p.name for p in (goc / "trich6-y-dinh").iterdir()),
                         sorted(sha256(x.encode()) for x in ("m4:0123456789abcdef", "crm:a.b-c_d:e", ".", "..", "a..b", "m4:..:x")))

    # ------------------------------------------------------------------ FIX01 F2: mất ACK / đứt kết nối theo vòng đời
    def test_f2_mat_ack_create_upload_start_va_doc_sau_start(self):
        for k in (("POST", "trich_xuat"), ("POST", "tep"), ("POST", "chay")):
            goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_f2_"))
            nguon, c = self.client(goc=goc)
            nguon.dut_sau.add(k)  # máy chủ ĐÃ thực hiện nhưng phản hồi mất
            with self.assertRaises(T6.ChuaRo, msg=k):
                c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f2")
            r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f2")
            self.assertEqual((nguon.luot, len(nguon.chay_body)), (1, 1), k)  # đúng MỘT lượt, MỘT lần chạy
            self.assertEqual(r["luot"], "20261021_100001")
        # GET (đọc trạng thái/poll) và tải raw đứt SAU create (lượt đã tồn tại ở nguồn; với raw: sau khi start đã được nhận) → UNKNOWN, không phải lỗi
        # cuối; thử lại đọc tiếp đúng lượt
        for k in (("GET", "20261021_100001"), ("GET", "x_KET_QUA.json")):
            nguon, c = self.client(goc=Path(tempfile.mkdtemp(prefix="ktt_trich6_f2g_")))
            c.tao_luot(T6.yeu_cau_common(source_sha256=sha256(b"PK\x03\x04demo"), loai_hop_dong="XD", tham_so="ALL", request_id="m4:g"))
            nguon.dut.add(k)
            with self.assertRaises(T6.ChuaRo, msg=k) as cm:
                c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:g")
            self.assertEqual(cm.exception.code, "TRICH6_CHUA_RO")
            r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:g")
            self.assertEqual((r["luot"], nguon.luot, len(nguon.chay_body)), ("20261021_100001", 1, 1))
        # 5xx không mã sau create → UNKNOWN; 4xx có mã → lỗi rõ
        self.assertTrue(T6.Trich6Client._la_chua_ro(T6.LoiNguon(500, "TRICH6_HTTP_500", "x")))
        self.assertTrue(T6.Trich6Client._la_chua_ro(T6.LoiNguon(409, "TRICH6_COMMON_MO_COI", "x")))
        self.assertFalse(T6.Trich6Client._la_chua_ro(T6.LoiNguon(400, "TRICH6_THAM_SO_LA", "x")))

    def test_r1_lich_nhan_qua_b_get_cu_a_upload_start_b_upload(self):
        """FIX02 R1 — CAUSAL IO-mock (không phải HTTP nguồn thật): B GET thấy chưa có đầu vào và bị GIỮ → A upload + start được nhận → B tiếp tục
        upload, nhận 409 KHÔNG mã (hành vi nguồn chưa patch) → B phải đối soát cùng ý định: cùng lượt, một start, cùng kết quả (hoặc UNKNOWN rồi
        thử lại hoàn tất). Thu đủ kết quả A, B lần đầu, B thử lại; không ngoại lệ chìm/thread sống."""
        import threading
        nguon = NguonGia()
        da_get_b, a_da_start = threading.Event(), threading.Event()

        def tb(method, path, headers, body):
            r = nguon(method, path, headers, body)
            # giữ GET TRẠNG THÁI lượt cũ của B (không phải preflight FIX04 — preflight chỉ đọc, không mang trạng thái lượt)
            if method == "GET" and path.startswith("/api/trich_xuat/") and path != "/api/trich_xuat/common" and not da_get_b.is_set():
                da_get_b.set()
                a_da_start.wait(30)  # B giữ phản hồi GET CŨ (chưa có đầu vào) tới khi A đã start
            return r

        def ta(method, path, headers, body):
            r = nguon(method, path, headers, body)
            if method == "POST" and path.endswith("/chay"):
                a_da_start.set()
            return r
        ca = T6.Trich6Client("http://127.0.0.1:18600", goc=Path(tempfile.mkdtemp(prefix="ktt_r1a_")), transport=ta, ngu=lambda s: None)
        cb = T6.Trich6Client("http://127.0.0.1:18600", goc=Path(tempfile.mkdtemp(prefix="ktt_r1b_")), transport=tb, ngu=lambda s: None)
        kq = {}

        def chay(ten, c):
            try:
                kq[ten] = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:r1")
            except BaseException as e:  # noqa: BLE001 — thu đủ, không để chìm
                kq[ten] = e
        th_b = threading.Thread(target=chay, args=("B", cb))
        th_b.start()
        self.assertTrue(da_get_b.wait(30))
        chay("A", ca)
        th_b.join(60)
        self.assertFalse(th_b.is_alive())
        self.assertNotIsInstance(kq["A"], BaseException, kq["A"])
        if isinstance(kq["B"], BaseException):  # chỉ chấp nhận UNKNOWN, không lỗi cuối
            self.assertIsInstance(kq["B"], T6.ChuaRo, kq["B"])
            kq["B2"] = cb.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:r1")
            b = kq["B2"]
        else:
            b = kq["B"]
        self.assertEqual((b["luot"], b["raw_sha256"]), (kq["A"]["luot"], kq["A"]["raw_sha256"]))
        self.assertEqual((nguon.luot, len(nguon.chay_body)), (1, 1))  # một lượt, một start
        # M4 không biến lịch này thành LOI cuối: lỗi upload 409 không mã chưa đối soát được → UNKNOWN
        self.assertTrue(T6.Trich6Client._la_chua_ro(T6.ChuaRo("TRICH6_CHUA_RO", "x")))

    def test_r3_ket_qua_lech_niem_phong_la_chua_ro(self):
        """FIX02 R3 — IO-mock: nguồn báo niêm phong (sha/độ dài) mà bytes tải về khác → UNKNOWN, không nhận kết quả."""
        nguon = NguonGia()
        goc_ket_qua = nguon._ket_qua

        def ket_qua_hong(lu):
            st, ct, b = goc_ket_qua(lu)
            return st, ct, b + b" "  # đọc dở/hỏng: khác bytes niêm phong
        nguon._ket_qua = ket_qua_hong   # niêm phong ở GET trạng thái vẫn tính trên bytes thật (nguon._raw) → lệch với bytes tải về
        _, c = self.client(nguon)
        with self.assertRaises(T6.ChuaRo):
            c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:seal")

    # ------------------------------------------------------------------ FIX03 R1: chỉ nhận khi common done + niêm phong hợp lệ đúng ý định
    def _client_het_han(self, nguon):
        t = [0.0]

        def dong_ho():  # đồng hồ giả tăng dần: hạn chờ hữu hạn, không ngủ thật
            t[0] += 1.0
            return t[0]
        return T6.Trich6Client("http://127.0.0.1:18600", transport=nguon, ngu=lambda s: None, dong_ho=dong_ho, cho_toi_da=5)

    def test_fix03_duong_tinh_niem_phong_hop_le_truoc(self):
        """Positive TRƯỚC negative (IO-mock): seal typed đúng request_id/body H, ref tương đối, raw đúng SHA/độ dài → nhận; bang không rỗng."""
        nguon = NguonGia()
        r = self._client_het_han(nguon).trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01", "TT-02"],
                                              request_id="m4:f3pos")
        self.assertEqual([d["ma"] for d in r["ket_qua"]["bang"]], ["TC-01", "TT-02"])
        self.assertEqual(r["ket_qua"]["bang"][0]["gia_tri"], "HD-01")
        self.assertEqual(r["raw_sha256"], sha256(nguon._raw(r["luot"])))
        self.assertEqual(r["common"]["body_sha256"], T6.body_sha256(r["yeu_cau"]))

    def test_fix03_xong_thieu_common_hoac_seal_la_chua_ro(self):
        """Top-level xong mà thiếu common / common chưa done / thiếu seal / seal sai kiểu-ý định-body-ref → ChuaRo (không nhận, không lỗi cuối);
        raw KHÔNG được tải. Seal ref hợp lệ nhưng không khớp đường tải → ChuaRo."""
        def bo(k):
            return lambda lu, s: {kk: v for kk, v in s.items() if kk != k}

        def sua_cm(**kw):
            return lambda lu, s: {**s, "common": {**s["common"], **kw}}

        def sua_seal(**kw):
            return lambda lu, s: {**s, "common": {**s["common"], "seal": {**s["common"]["seal"], **kw}}}
        for ten, hook in (("thieu_common", bo("common")), ("common_running", sua_cm(tt="running")), ("thieu_seal", sua_cm(seal=None)),
                          ("seal_kieu", sua_seal(kieu="x")), ("seal_request", sua_seal(request_id="khac")),
                          ("seal_body", sua_seal(body_sha256="d" * 64)), ("common_body", sua_cm(body_sha256="d" * 64)),
                          ("seal_ref_thoat", sua_seal(ref="../x/x_KET_QUA.json")), ("seal_ref_tuyet_doi", sua_seal(ref="/x/x_KET_QUA.json")),
                          ("seal_len_kieu", sua_seal(byte_length="12")), ("seal_sha_ngan", sua_seal(sha256="ab"))):
            nguon = NguonGia()
            nguon.sua_tt = hook
            with self.assertRaises(T6.ChuaRo, msg=ten):
                self._client_het_han(nguon).trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f3n")
            self.assertFalse(any(p.startswith("/tai/") for _m, p, *_ in nguon.goi), ten)  # chưa niêm phong hợp lệ → không tải raw
        nguon = NguonGia()
        nguon.sua_tt = sua_seal(ref="y/y_KET_QUA.json")  # ref khác tài nguyên đường tải → không chọn theo basename/vị trí
        with self.assertRaises(T6.ChuaRo):
            self._client_het_han(nguon).trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f3r")
        self.assertFalse(any(p.startswith("/tai/") for _m, p, *_ in nguon.goi))

    def test_fix03_loi_cuoi_chi_khi_common_khang_dinh(self):
        """Top-level 'loi' không có common → ChuaRo (không FINAL LOI); common khẳng định loi → DataError lỗi cuối có mã."""
        nguon = NguonGia()
        nguon.sua_tt = lambda lu, s: {"tt": "loi", "hd": [], "thong_bao": "x"}
        with self.assertRaises(T6.ChuaRo):
            self._client_het_han(nguon).trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f3l")
        nguon = NguonGia()
        nguon.sua_tt = lambda lu, s: {"tt": "loi", "hd": [], "thong_bao": "x", "common": {"tt": "loi", "loi": "x"}}
        with self.assertRaises(DataError) as cm:
            self._client_het_han(nguon).trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f3l2")
        self.assertNotIsInstance(cm.exception, T6.ChuaRo)
        self.assertEqual(cm.exception.code, "TRICH6_LUOT_LOI")

    # ------------------------------------------------------------------ FIX04 R5: preflight trước create; ACK đúng ý định trước upload/start
    def test_fix04_preflight_duong_tinh_va_thu_tu(self):
        """Positive TRƯỚC: preflight GET common là lệnh ĐẦU TIÊN, rồi create → GET trạng thái → upload → start; đúng một lượt/một start."""
        nguon, c = self.client(goc=Path(tempfile.mkdtemp(prefix="ktt_trich6_f4p_")))
        r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="m4:f4p")
        self.assertEqual([d["ma"] for d in r["ket_qua"]["bang"]], ["TC-01"])
        dau = [(m, p) for m, p, *_ in nguon.goi][:5]
        self.assertEqual(dau, [("GET", "/api/trich_xuat/common"), ("POST", "/api/trich_xuat"), ("GET", "/api/trich_xuat/20261021_100001"),
                               ("POST", "/api/trich_xuat/20261021_100001/tep"), ("POST", "/api/trich_xuat/20261021_100001/chay")])
        self.assertEqual((nguon.luot, len(nguon.chay_body)), (1, 1))

    def _khong_post(self, nguon):
        return [p for m, p, *_ in nguon.goi if m == "POST"]

    def test_fix04_preflight_khong_dat_khong_tac_dong(self):
        """Endpoint cũ (404 / trả HTML) / thiếu / sai kiểu / khác mode / chưa sẵn sàng / khác catalog → DataError TRICH6_KHONG_HO_TRO_COMMON
        (KHÔNG phải ChuaRo), ZERO POST create/upload/start, không ghi ý định cục bộ."""
        tot = NguonGia().nang_luc[1]
        ca = [("legacy_404", (404, {"loi": "Không có chức năng này"})), ("html", (200, b"<h1>x</h1>")), ("mang", (200, [1])),
              ("thieu_kieu", (200, {k: v for k, v in tot.items() if k != "kieu"})), ("contract", (200, {**tot, "contract": "khac/v1"})),
              ("mode", (200, {**tot, "modes": ["AI"]})), ("mode_kieu", (200, {**tot, "modes": "RULE_ONLY"})),
              ("chua_san_sang", (200, {**tot, "san_sang": False})), ("san_sang_chuoi", (200, {**tot, "san_sang": "true"})),
              ("loai_thieu", (200, {**tot, "loai": {}})), ("loai_chua_san_sang", (200, {**tot, "loai": {"XD": {**tot["loai"]["XD"], "san_sang": False}}})),
              ("catalog_sha", (200, {**tot, "loai": {"XD": {**tot["loai"]["XD"], "catalog_sha256": "0" * 64}}})),
              ("catalog_id", (200, {**tot, "loai": {"XD": {**tot["loai"]["XD"], "catalog_id": "KCN"}}})),
              ("ack_thieu", (200, {**tot, "create_ack": ["luot"]}))]
        for ten, nl in ca:
            goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_f4n_"))
            nguon, c = self.client(goc=goc)
            nguon.nang_luc = nl
            with self.assertRaises(DataError, msg=ten) as cm:
                c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f4n")
            self.assertNotIsInstance(cm.exception, T6.ChuaRo, ten)
            self.assertEqual(cm.exception.code, "TRICH6_KHONG_HO_TRO_COMMON", ten)
            self.assertEqual(self._khong_post(nguon), [], ten)                      # không create/upload/start, không thử API cũ
            self.assertEqual([(m, p) for m, p, *_ in nguon.goi], [("GET", "/api/trich_xuat/common")], ten)
            self.assertFalse((goc / "trich6-y-dinh").exists(), ten)                 # không ghi ý định trước khi preflight đạt

    def test_fix04_ack_sai_la_chua_ro_khong_upload_start(self):
        """ACK create thiếu request_id / khác ID / lap_lai không phải bool / DTO cũ chỉ {luot} / luot sai → ChuaRo; đúng MỘT POST create, ZERO
        upload/start, chưa lưu 10_luot. Thử lại cùng ID khi ACK đúng → cùng lượt/body/khóa ý định, một start, không tính lại."""
        for ten, sua in (("thieu_id", lambda a: {k: v for k, v in a.items() if k != "request_id"}), ("khac_id", lambda a: {**a, "request_id": "m4:khac"}),
                         ("lap_lai_chuoi", lambda a: {**a, "lap_lai": "false"}), ("lap_lai_so", lambda a: {**a, "lap_lai": 0}),
                         ("legacy", lambda a: {"luot": a["luot"]}), ("luot_sai", lambda a: {**a, "luot": "../x"})):
            goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_f4a_"))
            nguon, c = self.client(goc=goc)
            nguon.sua_ack = sua
            with self.assertRaises(T6.ChuaRo, msg=ten):
                c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="m4:f4a")
            self.assertEqual(self._khong_post(nguon), ["/api/trich_xuat"], ten)
            d = goc / "trich6-y-dinh" / sha256(b"m4:f4a")
            self.assertTrue((d / "00_yeu_cau.json").is_file(), ten)                # ý định giữ nguyên
            self.assertFalse((d / "10_luot.json").exists(), ten)
            body_dau = nguon.y_dinh["m4:f4a"][0]
            nguon.sua_ack = None
            r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="m4:f4a")
            self.assertEqual((r["luot"], nguon.luot, len(nguon.chay_body)), ("20261021_100001", 1, 1), ten)
            self.assertEqual(nguon.y_dinh["m4:f4a"][0], body_dau, ten)            # cùng body/khóa ý định
            self.assertEqual(sum(1 for p in self._khong_post(nguon) if p.endswith("/chay")), 1, ten)

    # ------------------------------------------------------------------ FIX05 R1: so sánh đường dẫn chuẩn Windows (tiền tố extended-length)
    def test_fix05_dang_chuan_duong_dan_xac_dinh(self):
        """Hàm thuần trên chuỗi (chạy được mọi OS): chỉ bỏ đúng tiền tố `\\\\?\\X:\\` và `\\\\?\\UNC\\`; tiền tố khác giữ nguyên → không bằng."""
        f = T6.dang_chuan_duong_dan
        self.assertEqual(f("\\\\?\\D:\\goc\\trich6-y-dinh"), f("D:\\goc\\trich6-y-dinh"))
        self.assertEqual(f("\\\\?\\UNC\\srv\\share\\goc"), f("\\\\srv\\share\\goc"))
        self.assertNotEqual(f("\\\\?\\Volume{1234}\\goc"), f("D:\\goc"))
        self.assertNotEqual(f("\\\\.\\D:\\goc"), f("D:\\goc"))
        self.assertNotEqual(f("\\\\?\\D:\\khac\\trich6-y-dinh"), f("D:\\goc\\trich6-y-dinh"))
        self.assertTrue(T6.cung_duong_dan("\\\\?\\D:\\goc", "D:\\goc"))

    @unittest.skipUnless(os.name == "nt", "biểu diễn \\\\?\\ chỉ có nghĩa trên Windows")
    def test_fix05_ba_caller_resolve_tien_to_xac_dinh(self):
        """Tái hiện XÁC ĐỊNH lỗi Root: resolve trả thư mục ý định đã tồn tại ở dạng `\\\\?\\D:\\…` trong khi gốc ở dạng thường. Ba caller đồng
        thời cùng ý định → đúng 3 kết quả, 1 lượt, 1 start, join đủ, không ngoại lệ. Đường thật sự ra ngoài gốc (cũng có tiền tố) vẫn bị chặn."""
        import pathlib
        import threading
        from unittest import mock
        goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_f5w_"))
        resolve_goc = pathlib.Path.resolve

        def resolve_tien_to(self_p, *a, **k):
            r = resolve_goc(self_p, *a, **k)
            s = str(r)
            if re.fullmatch(r"[0-9a-f]{64}", r.name) and r.exists() and not s.startswith("\\\\?\\"):
                return pathlib.Path("\\\\?\\" + s)   # cùng thư mục vật lý, biểu diễn extended-length
            return r
        nguon, c = self.client(goc=goc)
        kq, loi = [], []

        def mot():
            try:
                kq.append(c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f5w"))
            except BaseException as e:  # noqa: BLE001
                loi.append(e)
        with mock.patch.object(pathlib.Path, "resolve", resolve_tien_to):
            mot()                                                       # tạo thư mục ý định → các lần sau resolve trả dạng \\?\
            ts = [threading.Thread(target=mot) for _ in range(2)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(30)
            self.assertEqual([t.is_alive() for t in ts], [False, False])
            self.assertEqual(loi, [])
            self.assertEqual(len(kq), 3)
            self.assertEqual({r["luot"] for r in kq}, {"20261021_100001"})
            self.assertEqual((nguon.luot, len(nguon.chay_body)), (1, 1))
            ngoai = Path(tempfile.mkdtemp(prefix="ktt_trich6_f5ngoai_"))

            def resolve_thoat(self_p, *a, **k):
                r = resolve_goc(self_p, *a, **k)
                if re.fullmatch(r"[0-9a-f]{64}", r.name):
                    return pathlib.Path("\\\\?\\" + str(ngoai / r.name))  # junction/symlink trỏ ra ngoài gốc
                return r
            with mock.patch.object(pathlib.Path, "resolve", resolve_thoat):
                with self.assertRaises(DataError) as cm:
                    c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f5thoat")
                self.assertEqual(cm.exception.code, "TRICH6_DUONG_DAN_Y_DINH")

    @unittest.skipUnless(os.name == "nt", "đường dài Windows")
    def test_fix05_ba_caller_goc_duong_dai_that(self):
        """Gốc THẬT dài (> 260 ký tự) — đúng hoàn cảnh Root gặp; ba caller đồng thời → 3 kết quả/1 lượt/1 start. Máy không cho tạo đường dài → skip
        có lý do (ca xác định phía trên vẫn chạy)."""
        import threading
        goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_f5dai_"))
        for i in range(4):
            goc = goc / (f"thu_muc_rat_dai_{i}_" + "x" * 60)
        try:
            goc.mkdir(parents=True)
        except OSError as e:
            self.skipTest(f"không tạo được đường dài: {type(e).__name__}")
        nguon, c = self.client(goc=goc)
        kq, loi = [], []

        def mot():
            try:
                kq.append(c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:f5dai"))
            except BaseException as e:  # noqa: BLE001
                loi.append(e)
        ts = [threading.Thread(target=mot) for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        self.assertEqual([t.is_alive() for t in ts], [False] * 3)
        self.assertEqual(loi, [])
        self.assertEqual(len(kq), 3)
        self.assertEqual({r["luot"] for r in kq}, {"20261021_100001"})
        self.assertEqual((nguon.luot, len(nguon.chay_body)), (1, 1))

    # ------------------------------------------------------------------ FIX05 R2: ý định đã giữ + preflight lỗi → UNKNOWN, không POST thêm
    def test_fix05_y_dinh_da_giu_preflight_loi_la_chua_ro(self):
        goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_f5p_"))
        nguon, c = self.client(goc=goc)
        d = goc / "trich6-y-dinh" / sha256(b"m4:f5p")

        def anh_d():
            return sorted((p.relative_to(d).as_posix(), sha256(p.read_bytes())) for p in d.rglob("*") if p.is_file())

        def goi(ts=("TC-01",), rid="m4:f5p"):
            return c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=list(ts), request_id=rid)
        nguon.sua_ack = lambda a: {k: v for k, v in a.items() if k != "request_id"}  # create ĐÃ được nguồn nhận, ACK sai
        with self.assertRaises(T6.ChuaRo):
            goi()
        self.assertEqual(self._khong_post(nguon), ["/api/trich_xuat"])
        truoc, body_dau = anh_d(), nguon.y_dinh["m4:f5p"][0]
        self.assertIn("00_yeu_cau.json", [x for x, _ in truoc])
        tot = nguon.nang_luc
        for ten, nl in (("legacy_404", (404, {"loi": "x"})), ("chua_san_sang", (200, {**tot[1], "san_sang": False})),
                        ("catalog_khac", (200, {**tot[1], "loai": {"XD": {**tot[1]["loai"]["XD"], "catalog_sha256": "0" * 64}}}))):
            nguon.nang_luc = nl
            with self.assertRaises(T6.ChuaRo, msg=ten) as cm:
                goi()
            self.assertEqual(cm.exception.code, "TRICH6_CHUA_RO", ten)         # không phải lỗi cuối
            self.assertEqual(self._khong_post(nguon), ["/api/trich_xuat"], ten)  # không POST thêm
            self.assertEqual(anh_d(), truoc, ten)                               # không đổi bytes/body/khóa
        nguon.dut.add(("GET", "common"))                                        # endpoint mất kết nối khi preflight
        with self.assertRaises(T6.ChuaRo):
            goi()
        self.assertEqual((self._khong_post(nguon), anh_d()), (["/api/trich_xuat"], truoc))
        nguon.nang_luc = (404, {"loi": "x"})
        with self.assertRaises(DataError) as cm:                                # body khác vẫn là xung đột, không sinh khóa mới
            goi(ts=("TC-02",))
        self.assertEqual(cm.exception.code, "TRICH6_XUNG_DOT")
        with self.assertRaises(DataError) as cm:                                # ý định MỚI gặp preflight lỗi → lỗi rõ, zero POST/ghi
            goi(rid="m4:f5moi")
        self.assertEqual(cm.exception.code, "TRICH6_KHONG_HO_TRO_COMMON")
        self.assertFalse((goc / "trich6-y-dinh" / sha256(b"m4:f5moi")).exists())
        nguon.nang_luc, nguon.sua_ack = tot, None                              # phục hồi đúng preflight/ACK
        r = goi()
        self.assertEqual((r["luot"], nguon.luot, len(nguon.chay_body)), ("20261021_100001", 1, 1))
        self.assertEqual(nguon.y_dinh["m4:f5p"][0], body_dau)
        self.assertEqual(sum(1 for p in self._khong_post(nguon) if p.endswith("/chay")), 1)

    # ------------------------------------------------------------------ CRM-41-01-06: thiếu URL theo giai đoạn (IO-mock)
    def test_06_thieu_url_theo_giai_doan(self):
        """Fresh chưa cấu hình → TRICH6_CHUA_SAN_SANG rõ, zero POST, không tạo ý định. Ý định đã giữ (ACK sai) + mất URL → ChuaRo, không đổi
        bytes/body/khóa; body khác vẫn xung đột; cấu hình lại → đúng lượt cũ, một start."""
        goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_06_"))
        c0 = T6.Trich6Client("", goc=goc)                       # chế độ quản lý, engine chưa sẵn sàng (không rơi về biến môi trường)
        self.assertFalse(c0.san_sang)
        goi = lambda c, ts=("TC-01",): c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=list(ts),  # noqa: E731
                                               request_id="m4:g6")
        for f in (lambda: goi(c0), lambda: c0.kiem_giai_doan("m4:g6")):
            with self.assertRaises(DataError) as cm:
                f()
            self.assertNotIsInstance(cm.exception, T6.ChuaRo)
            self.assertEqual(cm.exception.code, "TRICH6_CHUA_SAN_SANG")
        self.assertFalse((goc / "trich6-y-dinh").exists())
        nguon, c = self.client(goc=goc)
        nguon.sua_ack = lambda a: {k: v for k, v in a.items() if k != "request_id"}
        with self.assertRaises(T6.ChuaRo):
            goi(c)
        d = goc / "trich6-y-dinh" / sha256(b"m4:g6")
        anh_d = lambda: sorted((p.relative_to(d).as_posix(), sha256(p.read_bytes())) for p in d.rglob("*") if p.is_file())  # noqa: E731
        truoc, so_goi = anh_d(), len(nguon.goi)
        with self.assertRaises(T6.ChuaRo):
            c0.kiem_giai_doan("m4:g6")
        with self.assertRaises(T6.ChuaRo) as cm:
            goi(c0)
        self.assertEqual(cm.exception.code, "TRICH6_CHUA_RO")
        self.assertEqual((anh_d(), len(nguon.goi)), (truoc, so_goi))
        with self.assertRaises(DataError) as cm:
            goi(c0, ("TC-02",))
        self.assertEqual(cm.exception.code, "TRICH6_XUNG_DOT")
        nguon.sua_ack = None
        r = goi(c)
        self.assertEqual((r["luot"], nguon.luot, len(nguon.chay_body)), ("20261021_100001", 1, 1))
        self.assertIsNone(c.kiem_giai_doan("m4:g6"))

    def test_06_token_chi_header_khong_lo(self):
        """Token engine sở hữu chỉ đi bằng header riêng; không trong path/query, repr hay thông báo lỗi."""
        nguon = NguonGia()
        tok = "k" * 43
        c = T6.Trich6Client("http://127.0.0.1:18600", transport=nguon, ngu=lambda s: None, token=tok)
        hd = []
        goc_call = nguon.__call__

        def tb(method, path, headers, body):
            hd.append((path, dict(headers)))
            return goc_call(method, path, headers, body)
        c._gui = tb
        r = c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="m4:tok")
        self.assertTrue(hd and all(h.get(T6.HEADER_TOKEN) == tok for _p, h in hd))
        self.assertFalse(any(tok in p for p, _h in hd))
        self.assertNotIn(tok, repr(c))
        self.assertNotIn(tok, json.dumps(r["yeu_cau"]) + json.dumps(r["common"], default=str))
        nguon.nang_luc = (404, {"loi": "x"})
        with self.assertRaises(DataError) as cm:
            c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01"], request_id="m4:tok2")
        self.assertNotIn(tok, str(cm.exception))

    def test_f2_hai_caller_cung_y_dinh_mot_luot(self):
        nguon, c = self.client(goc=Path(tempfile.mkdtemp(prefix="ktt_trich6_f2c_")))
        import threading
        kq, loi = [], []

        def mot():
            try:
                kq.append(c.trich(b"PK\x03\x04demo", ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="m4:cung"))
            except BaseException as e:  # noqa: BLE001 — thu MỌI ngoại lệ, không caller nào bị bỏ qua
                loi.append(e)
        ts = [threading.Thread(target=mot) for _ in range(3)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        self.assertEqual([t.is_alive() for t in ts], [False] * 3)  # join hữu hạn, không thread còn sống
        self.assertEqual(loi, [])
        self.assertEqual(len(kq), 3)  # FIX03: ĐÚNG ba kết quả cho ba caller
        self.assertEqual({r["luot"] for r in kq}, {"20261021_100001"})
        self.assertEqual(len({r["raw_sha256"] for r in kq}), 1)
        self.assertEqual((nguon.luot, len(nguon.chay_body)), (1, 1))

    def test_ket_qua_khac_yeu_cau_bi_chan(self):
        yc = T6.yeu_cau_common(source_sha256="a" * 64, loai_hop_dong="XD", tham_so=["TC-01"], request_id="r")
        kq = {"che_do": "RULE_ONLY", "bang": _bang(["TC-01"]), "common": {**{k: yc[k] for k in ("contract", "request_id", "source_sha256",
                                                                                              "catalog_sha256", "loai_hop_dong", "catalog_id", "mode")},
                                                                      "tham_so_da_dung": ["TC-01"], "body_sha256": T6.body_sha256(yc)}}
        T6.kiem_ket_qua(kq, yc)
        for sua in ({"request_id": "khac"}, {"catalog_sha256": "c" * 64}, {"tham_so_da_dung": ["TC-02"]}, {"body_sha256": "d" * 64}):
            with self.assertRaises(DataError):
                T6.kiem_ket_qua({**kq, "common": {**kq["common"], **sua}}, yc)
        with self.assertRaises(DataError):
            T6.kiem_ket_qua({**kq, "common": None}, yc)  # kết quả đường cũ không có bản chụp → không trộn


class ProjectionTests(unittest.TestCase):
    def test_chieu_mot_adapter_giu_raw_hash(self):
        kq = {"hop_dong": "x.docx", "che_do": "RULE_ONLY", "bang": _bang(["TC-01", "TT-02"]),
              "common": {"contract": T6.CONTRACT, "tham_so_da_dung": ["TC-01", "TT-02"], "tham_so_snapshot": [{"ma": "TC-01"}]}}
        raw = json.dumps(kq).encode()
        v = T6.chieu_tham_so(kq, raw_sha256=sha256(raw), danh_muc_ma=["TC-01", "TT-02", "TT-04"])
        tt = {d["ma"]: d["trang_thai"] for d in v["tham_so"]}
        self.assertEqual(tt, {"TC-01": "CO_GIA_TRI", "TT-02": "CHUA_CO", "TT-04": "NOT_REQUESTED"})  # chưa trích ≠ không yêu cầu; không điền 0
        self.assertEqual((v["adapter"], v["nguon_sha256"]), (T6.ADAPTER_VERSION, sha256(raw)))
        self.assertNotEqual(sha256(T6.view_bytes(v)), v["nguon_sha256"])  # hash view tách khỏi hash raw
        self.assertNotIn("tham_so_snapshot", v["common"])
        self.assertEqual(v["tham_so"][0]["trich_dan"], "Số: HD-01")  # giữ nguyên trích dẫn nguồn
        # view đọc được qua bộ đọc tham_so[] hiện có của CRM
        from kho_tri_thuc.nguon.trich_hop_dong_6 import doc_ket_qua
        self.assertEqual([p["ma"] for p in doc_ket_qua(T6.view_bytes(v))["tham_so"]], ["TC-01", "TT-02", "TT-04"])


class ClientGia:
    san_sang = True

    def __init__(self):
        self.goi = []

    def trich(self, raw, *, ten_tep, loai_hop_dong, tham_so, request_id):
        self.goi.append((ten_tep, loai_hop_dong, tham_so, request_id))
        nguon = NguonGia(ma=__import__("kho_tri_thuc.m4.nguon_review", fromlist=["MA_DANH_MUC"]).MA_DANH_MUC)
        c = T6.Trich6Client("http://127.0.0.1:18600", transport=nguon, ngu=lambda s: None)
        return c.trich(raw, ten_tep=ten_tep, loai_hop_dong=loai_hop_dong, tham_so=tham_so, request_id=request_id)


class WiringTests(unittest.TestCase):
    def test_m4_khong_con_loi_chep(self):
        src = (SRC / "m4" / "nguon_review.py").read_text(encoding="utf-8")
        f = src[src.index("def trich_hop_dong("):src.index("# ---------------------------------------------------------------------------------------------------------------- BOQ")]
        for cam in ("TrichXuat", "master_hd", "xu_ly(", "load_params", "danh_muc_tham_so("):
            self.assertNotIn(cam, f.split('"""', 2)[2], cam)  # không còn đường trích chạy lõi chép / fallback
        self.assertIn("client.trich(", f)
        self.assertIn('loai_hop_dong="XD", tham_so="ALL"', f)
        xd = (SRC / "k2" / "xay_dung.py").read_text(encoding="utf-8")
        t = xd[xd.index("    def trich(self"):xd.index("    def sua_tham_so(")]
        self.assertLess(t.index("self._ho_so(dt, hd)"), t.index("NR.trich_hop_dong("))  # SOAN + revision trước upload
        self.assertLess(t.index("NR.trich_hop_dong("), t.index("h2 = self._ho_so(dt, hd)"))  # kiểm lại sau lần gọi dài
        self.assertIn("m4.ghi_trich_xuat(", t)  # SQL CAS revision vẫn là chốt
        m4 = (SRC / "giao_dien" / "m4.py").read_text(encoding="utf-8")
        self.assertIn('LENH_RIENG = REVIEW_LENH | {"hop-dong/trich"}', m4)  # ngoài mutation lock, kết nối riêng

    def test_m4_wrapper_37_ma_qua_client(self):
        from kho_tri_thuc.kiem_chung import fixtures_m4 as F
        from kho_tri_thuc.m4 import nguon_review as NR
        c = ClientGia()
        kq = NR.trich_hop_dong(F.hop_dong_docx(), NR.MEDIA_DOCX, Path(tempfile.mkdtemp(prefix="ktt_m4_trich6_")), client=c, request_id="m4:abc")
        self.assertEqual(kq["trang_thai"], "XONG", kq.get("ly_do"))
        self.assertEqual(c.goi[0][1:3], ("XD", "ALL"))
        self.assertEqual(sorted(r["ma"] for r in kq["ket_qua"]), sorted(NR.MA_DANH_MUC))
        self.assertEqual(kq["che_do"], "QUY_TAC_KHONG_AI")
        self.assertTrue(kq["engine"].startswith("trich6.common/v1@"))
        r1 = next(r for r in kq["ket_qua"] if r["ma"] == "TC-01")
        self.assertEqual((r1["trang_thai"], r1["nguon"], r1["trich_dan"]), ("CO_GIA_TRI", "QUY_TAC", "Số: HD-01"))
        self.assertTrue(all(r["trang_thai"] == "CHUA_CO" and r["gia_tri"] is None for r in kq["ket_qua"] if r["ma"] != "TC-01"))
        with self.assertRaises(DataError):  # không nhận AI, không dùng lõi chép
            NR.trich_hop_dong(F.hop_dong_docx(), NR.MEDIA_DOCX, Path(tempfile.mkdtemp()), client=c, request_id="m4:x", ai=object())
        tc = NR.trich_hop_dong(F.hop_dong_docx(track_changes=True), NR.MEDIA_DOCX, Path(tempfile.mkdtemp()), client=c, request_id="m4:y")
        self.assertEqual(tc["trang_thai"], "KHONG_HO_TRO")  # an toàn DOCX kiểm TRƯỚC khi gửi bytes
        self.assertEqual(len(c.goi), 1)

    def test_crm_di_qua_client_chung(self):
        src = (SRC / "k2" / "crm.py").read_text(encoding="utf-8")
        f = src[src.index("    def trich_tu_docx("):src.index("    def nhan_ket_qua_6(")]
        self.assertLess(f.index('quyen.kiem(dt, "NOP_HOP_DONG", pn)'), f.index("client.trich("))  # quyền trước gọi engine
        self.assertLess(f.index("client.trich("), f.index("self.nhan_ket_qua_6("))  # nhan_ket_qua_6 kiểm quyền lại trước ghi
        self.assertIn("T6.chieu_tham_so(", f)
        self.assertIn('"word_hash": h_docx', f)
        sv = (SRC / "giao_dien" / "server.py").read_text(encoding="utf-8")
        r = sv[sv.index('if path == "/api/crm/trich6":'):sv.index('if path == "/api/crm/nhan":')]
        self.assertLess(r.index("with app.mutation_lock:"), r.index("app.crm_trich(me, raw, info)"))
        dong = r.splitlines()
        i = next(n for n, d in enumerate(dong) if "app.crm_trich(me, raw, info)" in d)
        j = max(n for n in range(i) if "with app.mutation_lock:" in dong[n])
        self.assertEqual(len(dong[i]) - len(dong[i].lstrip()), len(dong[j]) - len(dong[j].lstrip()))  # gọi engine NGOÀI lock
        self.assertIn("finally:\n            conn.close()", sv[sv.index("def crm_trich(self"):])
        js = (SRC / "giao_dien" / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn('"/api/crm/trich6"', js)
        self.assertIn("crmTrichYDinh", js)
        self.assertNotIn("innerHTML", js[js.index("function crmTrichForm("):js.index("function crmHoSo(")])

    def test_f2_m4_chua_ro_khong_thanh_loi_cuoi(self):
        """M4: lỗi chưa rõ theo vòng đời (đứt kết nối/đọc dở/5xx không mã/lượt mồ côi) → ChuaRo → XayDungK2 báo M4_TRICH6_CHUA_RO, KHÔNG ghi lần
        trích LOI/revision/biên nhận; lỗi rõ (4xx có mã) vẫn là LOI có lý do."""
        from kho_tri_thuc.kiem_chung import fixtures_m4 as F
        from kho_tri_thuc.m4 import nguon_review as NR

        class ClientLoi:
            san_sang = True

            def __init__(self, exc):
                self.exc = exc

            def trich(self, *a, **k):
                raise self.exc
        for exc in (DataError("TRICH6_KHONG_KET_NOI", "x"), T6.LoiNguon(502, "TRICH6_HTTP_502", "x"), T6.LoiNguon(409, "TRICH6_COMMON_MO_COI", "x"),
                    T6.ChuaRo("TRICH6_CHUA_RO", "x")):
            with self.assertRaises(T6.ChuaRo, msg=exc.code):
                NR.trich_hop_dong(F.hop_dong_docx(), NR.MEDIA_DOCX, Path(tempfile.mkdtemp()), client=ClientLoi(exc), request_id="m4:u")
        kq = NR.trich_hop_dong(F.hop_dong_docx(), NR.MEDIA_DOCX, Path(tempfile.mkdtemp()), client=ClientLoi(T6.LoiNguon(400, "TRICH6_THAM_SO_LA", "x")),
                               request_id="m4:r")
        self.assertEqual(kq["trang_thai"], "LOI")
        xd = (SRC / "k2" / "xay_dung.py").read_text(encoding="utf-8")
        self.assertIn('if exc.code in ("TRICH6_CHUA_RO", "TRICH6_CHUA_XONG")', xd)

    def test_f4_crm_y_dinh_day_du_o_may_chu(self):
        """UNIT (không PG, không HTTP): `CrmK2.trich_tu_docx` trên đối tượng thay thế; `quyen.kiem` được thay bằng no-op CHỈ để cô lập phần ràng buộc
        ý định — KHÔNG phải kiểm quyền PG thật. FIX02 R4: cùng ID logic mà đổi PN/dự án/loại hình/loại bản/tệp HOẶC actor → xung đột trước engine,
        0 tác động (so toàn bộ đường dẫn tương đối + SHA); actor B dùng ID MỚI là ca dương riêng, chủ là B."""
        from unittest.mock import patch
        from kho_tri_thuc.k2.crm import CrmK2
        from kho_tri_thuc.kiem_chung import fixtures_m4 as F

        class CrmGia:
            CRM_TRICH_ENV = CrmK2.CRM_TRICH_ENV

            def __init__(self, root):
                self.root, self.ghi = root, []

            def danh_tinh(self, dn):
                return {"id": {"A": "11111111-1111-4111-8111-111111111111", "B": "22222222-2222-4222-8222-222222222222"}[dn], "dang_nhap": dn}

            def _pn(self, ma):
                return "pn-" + ma

            def nhan_ket_qua_6(self, dn, raw, env, common=None):
                self.ghi.append((dn, env, common))
                return {"trung": False, "chung_tu_id": f"ct{len(self.ghi)}"}
        goc = Path(tempfile.mkdtemp(prefix="ktt_crm_f4_"))
        g, c, docx = CrmGia(goc), ClientGia(), F.hop_dong_docx()
        goi = lambda dn, info, raw=docx, rid="crm:1": CrmK2.trich_tu_docx(g, dn, raw, info, loai_hop_dong="XD", tham_so=["TC-01"],  # noqa: E731
                                                                         request_id=rid, client=c)

        def anh():  # toàn bộ đường dẫn tương đối + SHA-256 + độ dài của mọi TỆP dưới gốc (không chỉ đếm/basename)
            return sorted((p.relative_to(goc).as_posix(), sha256(p.read_bytes()), p.stat().st_size) for p in goc.rglob("*") if p.is_file())
        info = {"phap_nhan": "PN_DEMO_A", "loai_hinh": "KCN", "du_an": "DA1", "loai_ban": "GOC"}
        with patch("kho_tri_thuc.k2.crm.quyen.kiem", lambda *a, **k: None):
            goi("A", info)
            goi("A", dict(info))  # thử lại đúng ý định (đúng actor/nội dung): cùng ID nguồn
            self.assertEqual(c.goi[0][3], c.goi[1][3])
            n_engine, n_ghi, truoc = len(c.goi), len(g.ghi), anh()
            for dn, sua in (("A", {"phap_nhan": "PN_DEMO_B"}), ("A", {"du_an": "DA2"}), ("A", {"loai_hinh": "NHA_O"}), ("A", {"loai_ban": "PHU_LUC"}),
                            ("A", {"du_an": None}), ("B", {})):  # ("B", {}) = actor KHÁC, cùng ID, cùng nội dung → vẫn xung đột (R4)
                with self.assertRaises(DataError, msg=(dn, sua)) as cm:
                    goi(dn, {**info, **sua})
                self.assertEqual(cm.exception.code, "CRM_TRICH_XUNG_DOT", (dn, sua))
                self.assertNotIn("PN_DEMO_A", str(cm.exception))  # không lộ nội dung/chủ cũ
                self.assertNotIn("11111111-1111-4111-8111-111111111111", str(cm.exception))
            with self.assertRaises(DataError) as cm:
                goi("A", info, raw=F.hop_dong_docx(track_changes=True))  # cùng ID, bytes khác
            self.assertEqual(cm.exception.code, "CRM_TRICH_XUNG_DOT")
            self.assertEqual((len(c.goi), len(g.ghi), anh()), (n_engine, n_ghi, truoc))  # 0 engine, 0 ghi nghiệp vụ, 0 tệp mới/đổi
            goi("B", info, rid="crm:2")  # B dùng ID MỚI: ca dương riêng của B
            self.assertNotEqual(c.goi[-1][3], c.goi[0][3])
            self.assertEqual(g.ghi[-1][0], "B")
            with self.assertRaises(DataError) as cm:
                goi("A", {**info, "actor": "B"}, rid="crm:3")  # không nhận actor/trường lạ từ trình duyệt
            self.assertEqual(cm.exception.code, "CRM_ENVELOPE")
        # R5: chỉ đọc TỆP .json thường; thư mục staging do guard gốc giữ lại kiểm RIÊNG đúng loại/vị trí; không bỏ qua tệp lạ
        vung = goc / "crm-trich-y-dinh"
        tep = sorted(p for p in vung.iterdir() if p.is_file())
        khac = sorted(p.name for p in vung.iterdir() if not p.is_file())
        self.assertTrue(set(khac) <= {".ktt-staging"}, khac)
        for x in khac:
            self.assertTrue((vung / x).is_dir())
        self.assertEqual([p.name for p in tep], sorted(sha256(("crm-y-dinh|" + r).encode("utf-8")) + ".json" for r in ("crm:1", "crm:2")))
        yd = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in tep}
        a = yd[sha256(b"crm-y-dinh|crm:1") + ".json"]
        b = yd[sha256(b"crm-y-dinh|crm:2") + ".json"]
        self.assertEqual((a["dang_nhap"], a["actor_id"], a["request_id"]), ("A", "11111111-1111-4111-8111-111111111111", "crm:1"))
        self.assertEqual((b["dang_nhap"], b["actor_id"], b["request_id"]), ("B", "22222222-2222-4222-8222-222222222222", "crm:2"))
        self.assertEqual((a["envelope"]["phap_nhan"], a["envelope"]["loai_hinh"], a["envelope"]["du_an"], a["envelope"]["loai_ban"]),
                         ("PN_DEMO_A", "KCN", "DA1", "GOC"))  # loại hình tài chính tách khỏi loại trích
        self.assertEqual((a["loai_trich"], a["tham_so"], a["source_sha256"]), ("XD", ["TC-01"], sha256(docx)))

    def test_06_m4_giai_doan_truoc_nr_khong_ghi(self):
        """UNIT trên đối tượng thay thế (không PG/HTTP central): `XayDungK2.trich` với client chưa cấu hình — quyền/hồ sơ/revision HIỆN HÀNH kiểm
        TRƯỚC; fresh → M4_TRICH6_CHUA_SAN_SANG, ý định đã giữ → M4_TRICH6_CHUA_RO; cả hai KHÔNG gọi NR (không FINAL LOI), zero ghi K2, zero POST."""
        from unittest.mock import patch
        from kho_tri_thuc.ha_tang.primitives import canonical_json
        from kho_tri_thuc.k2.xay_dung import XayDungK2
        from kho_tri_thuc.kiem_chung import fixtures_m4 as F
        from kho_tri_thuc.m4 import nguon_review as NR
        goc = Path(tempfile.mkdtemp(prefix="ktt_m4_06_"))
        hd, raw = "11111111-1111-4111-8111-111111111111", F.hop_dong_docx()

        class XDGia:
            def __init__(self, loi_quyen=None):
                self.trich6, self.root, self.conn_tin_cay, self.thu_tu, self.k2, self.loi_quyen = T6.Trich6Client("", goc=goc), goc, object(), [], [], loi_quyen

            def danh_tinh(self, dn):
                self.thu_tu.append("danh_tinh")
                return {"id": "u-a", "dang_nhap": dn}

            def _tra_lai(self, *a):
                self.thu_tu.append("tra_lai")

            def _ho_so(self, dt, h):
                self.thu_tu.append("ho_so")
                if self.loi_quyen:
                    raise DataError(self.loi_quyen, "x")
                return {"tep_hop_dong_id": "t1", "raw_sha256": sha256(raw), "media_type": NR.MEDIA_DOCX}

            def _kiem_rev(self, h, rev):
                self.thu_tu.append("kiem_rev")

            def _raw(self, s):
                return raw

            def _goi(self, *a, **k):
                self.k2.append(a)
        goi = lambda g: XayDungK2.trich(g, "A", hop_dong_id=hd, revision=1, khoa="k-06")  # noqa: E731

        def cam_nr(*a, **k):
            raise AssertionError("không được gọi NR khi engine chưa sẵn sàng")
        with patch.object(NR, "trich_hop_dong", cam_nr):
            g = XDGia("KHONG_CO_QUYEN_PHAP_NHAN")
            with self.assertRaises(DataError) as cm:
                goi(g)
            self.assertEqual(cm.exception.code, "KHONG_CO_QUYEN_PHAP_NHAN")     # quyền trước mọi phân loại engine
            g = XDGia()
            with self.assertRaises(DataError) as cm:
                goi(g)
            self.assertEqual(cm.exception.code, "M4_TRICH6_CHUA_SAN_SANG")
            self.assertLess(g.thu_tu.index("ho_so"), len(g.thu_tu))
            self.assertEqual(g.k2, [])
            self.assertFalse((goc / "trich6-y-dinh").exists())
            yc_id = "m4:" + sha256(canonical_json(["u-a", "k-06", hd, 1, sha256(raw)]).encode("utf-8"))[:48]
            dd = goc / "trich6-y-dinh" / sha256(yc_id.encode("utf-8"))
            dd.mkdir(parents=True)
            (dd / "00_yeu_cau.json").write_bytes(b"{}")                          # dấu ý định DEMO đã giữ trước đó
            g = XDGia()
            with self.assertRaises(DataError) as cm:
                goi(g)
            self.assertEqual(cm.exception.code, "M4_TRICH6_CHUA_RO")
            self.assertEqual(g.k2, [])
            self.assertEqual(g.thu_tu[:3], ["danh_tinh", "tra_lai", "ho_so"])

    def test_06_crm_giai_doan_y_dinh_va_quyen(self):
        """UNIT (đối tượng thay thế, `quyen.kiem` thay thế ghi rõ): client chưa cấu hình — quyền hiện hành TRƯỚC; fresh → CRM_TRICH6_CHUA_SAN_SANG,
        không tạo ý định/raw; ý định đầy đủ đã có → xung đột kiểm trước, đúng nội dung → ChuaRo; zero engine/zero ghi nghiệp vụ/zero tệp mới."""
        from unittest.mock import patch
        from kho_tri_thuc.k2.crm import CrmK2
        from kho_tri_thuc.kiem_chung import fixtures_m4 as F

        class CrmGia:
            CRM_TRICH_ENV = CrmK2.CRM_TRICH_ENV

            def __init__(self, root):
                self.root, self.ghi = root, []

            def danh_tinh(self, dn):
                return {"id": "11111111-1111-4111-8111-111111111111", "dang_nhap": dn}

            def _pn(self, ma):
                return "pn-" + ma

            def nhan_ket_qua_6(self, dn, raw, env, common=None):
                self.ghi.append(dn)
                return {"trung": False, "chung_tu_id": "ct"}
        goc = Path(tempfile.mkdtemp(prefix="ktt_crm_06_"))
        g, docx, info = CrmGia(goc), F.hop_dong_docx(), {"phap_nhan": "PN_DEMO_A", "loai_hinh": "KCN", "du_an": "DA1", "loai_ban": "GOC"}
        chua = T6.Trich6Client("", goc=goc / "crm-k2")
        goi = lambda c, inf=info, rid="crm:06": CrmK2.trich_tu_docx(g, "A", docx, inf, loai_hop_dong="XD", tham_so=["TC-01"],  # noqa: E731
                                                                   request_id=rid, client=c)
        anh = lambda: sorted((p.relative_to(goc).as_posix(), sha256(p.read_bytes())) for p in goc.rglob("*") if p.is_file())  # noqa: E731

        def cam_quyen(*a, **k):
            raise DataError("KHONG_CO_QUYEN_PHAP_NHAN", "x")
        with patch("kho_tri_thuc.k2.crm.quyen.kiem", cam_quyen):
            with self.assertRaises(DataError) as cm:
                goi(chua)
            self.assertEqual(cm.exception.code, "KHONG_CO_QUYEN_PHAP_NHAN")
        self.assertEqual(anh(), [])
        with patch("kho_tri_thuc.k2.crm.quyen.kiem", lambda *a, **k: None):
            with self.assertRaises(DataError) as cm:
                goi(chua)
            self.assertNotIsInstance(cm.exception, T6.ChuaRo)
            self.assertEqual(cm.exception.code, "CRM_TRICH6_CHUA_SAN_SANG")
            self.assertEqual(anh(), [])                                          # không ý định/raw mới
            goi(ClientGia())                                                     # ý định đầy đủ được giữ qua engine sẵn sàng
            truoc, n_ghi = anh(), len(g.ghi)
            with self.assertRaises(DataError) as cm:
                goi(chua, {**info, "du_an": "DA2"})
            self.assertEqual(cm.exception.code, "CRM_TRICH_XUNG_DOT")            # xung đột kiểm trước phân loại
            with self.assertRaises(T6.ChuaRo) as cm:
                goi(chua)
            self.assertEqual(cm.exception.code, "TRICH6_CHUA_RO")
            self.assertEqual((anh(), len(g.ghi)), (truoc, n_ghi))

    def test_f5_ui_crm_ba_lich_tinh(self):
        """TĨNH (không trình duyệt): ba lịch F5 bám đúng điểm mã — định danh bytes, rào sau arrayBuffer/hash trước POST, form cố định qua làm mới."""
        js = (SRC / "giao_dien" / "assets" / "app.js").read_text(encoding="utf-8")
        t = js[js.index("async function crmTrich("):js.index("function crmHoSo(")]
        thu_tu = ["await f.arrayBuffer()", "if (!conDung()) return;", "await crmSha256Hex(buf)", "khoa = JSON.stringify([sha, pnGoc, loaiGoc, tham_so])",
                  'request("/api/crm/trich6"']
        vt = [t.index(x) for x in thu_tu]
        self.assertEqual(vt, sorted(vt))
        self.assertEqual(t[:t.index('request("/api/crm/trich6"')].count("if (!conDung()) return;"), 2)
        self.assertNotIn("lastModified", t)  # File B cùng tên/cỡ/thời gian ≠ File A
        self.assertIn("body: yd.bytes", t)  # gửi lại ĐÚNG bytes của ý định gốc
        f = js[js.index("function crmTrichForm("):js.index("async function crmSha256Hex(")]
        self.assertIn("if (crmTrichVung && crmTrichVung.ep === crmEpoch)", f)
        self.assertIn("return crmTrichVung.box;", f)  # làm mới nền gắn lại DOM cũ, không dựng lại → nháp B còn
        x = js[js.index("function crmXoaTrangThai("):js.index("async function crmTai(")]
        self.assertIn("crmTrichGen += 1", x)  # đổi vai bỏ nháp có chủ đích

    def test_envelope_common_tuong_thich_cu(self):
        from kho_tri_thuc.nguon.trich_hop_dong_6 import COMMON_ENV_KEYS, envelope
        cu = envelope(b"{}", {"namespace": "NS"})
        self.assertNotIn("common", cu)  # đường JSON cũ không đổi
        cm = {k: None for k in COMMON_ENV_KEYS}
        cm.update(contract=T6.CONTRACT, request_id="r", luot="20261021_100001", raw_ket_qua_sha256="a" * 64, source_sha256="b" * 64,
                  catalog_id="XD", catalog_sha256=CAT, loai_hop_dong="XD", implementation_sha256="c" * 64, tham_so_yeu_cau="ALL",
                  tham_so_da_dung=["TC-01"], adapter=T6.ADAPTER_VERSION)
        self.assertEqual(envelope(b"{}", {"namespace": "NS"}, common=cm)["common"]["phien_ban"], "trich6-common-envelope-v1")
        with self.assertRaises(DataError):
            envelope(b"{}", {"namespace": "NS"}, common={**cm, "la": 1})
        with self.assertRaises(DataError):
            envelope(b"{}", {"namespace": "NS"}, common={**cm, "implementation_sha256": None})


@unittest.skipUnless(os.environ.get(T6.ENV_URL), "Chưa có KHO_TRICH6_URL (engine #6 đã áp patch do Root dựng) — NOT_RUN")
class ApiNguonThatTests(unittest.TestCase):
    """API engine #6 THẬT (loopback do Root dựng bằng tao_may_chu(0) trên dữ liệu tạm). Không điền kết quả giả."""

    def test_m4_all_37_va_crm_tap_con_cung_engine(self):
        from kho_tri_thuc.kiem_chung import fixtures_m4 as F
        from kho_tri_thuc.m4 import nguon_review as NR
        goc = Path(tempfile.mkdtemp(prefix="ktt_trich6_that_"))
        c = T6.Trich6Client(goc=goc)
        raw = F.hop_dong_docx()
        a = c.trich(raw, ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so="ALL", request_id="that:m4:" + os.urandom(4).hex())
        self.assertEqual(sorted(a["common"]["tham_so_da_dung"]), sorted(NR.MA_DANH_MUC))
        self.assertEqual(a["common"]["catalog_sha256"], NR.PIN[NR.CATALOG])
        b = c.trich(raw, ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01", "TT-02"], request_id="that:crm:" + os.urandom(4).hex())
        self.assertEqual(sorted(d["ma"] for d in b["ket_qua"]["bang"]), ["TC-01", "TT-02"])
        self.assertEqual(a["common"]["implementation"]["sha256"], b["common"]["implementation"]["sha256"])  # cùng một implementation
        self.assertNotEqual(a["common"]["tham_so_da_dung"], b["common"]["tham_so_da_dung"])  # hai yêu cầu không lẫn bộ mã
        with self.assertRaises(T6.LoiNguon) as cm:
            c.trich(raw, ten_tep="hop_dong.docx", loai_hop_dong="XD", tham_so=["TC-01", "XX-99"], request_id="that:la:" + os.urandom(4).hex())
        self.assertEqual(cm.exception.code, "TRICH6_THAM_SO_LA")


if __name__ == "__main__":
    unittest.main()
