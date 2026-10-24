# -*- coding: utf-8 -*-
"""CRM-41-01 — kiểm API common/v1 (`trich-tham-so-common/v1`) của CHÍNH engine nguồn #6 sau khi Root áp patch (CODE_ONLY: coder viết, CHƯA CHẠY).

Chạy trong dự án nguồn #6 (tests/), dùng source thật — KHÔNG import từ docs/CRM-41-01-SOURCE-PATCH hay review_goc của central. Máy chủ nguồn
dựng bằng tao_may_chu(0) (cổng ngẫu nhiên loopback, không main(), không cổng 8600); dữ liệu/kết quả vào thư mục tạm riêng (HD_DU_LIEU/
HD_OUT_DIR/HD_DANH_MUC_HD/HD_CSDL/HD_THU_MUC_KHOA) đặt TRƯỚC import; giữ lại, không xóa. Không AI/cloud/OCR/Office/mạng ngoài; mọi thăm dò AI
bị chặn bằng sentinel (nếu nhánh common chạm AI/cấu hình → test hỏng). Hợp đồng DEMO tổng hợp không rỗng (tests/mau_gia_lap.py).

Ca: RULE_ONLY + ALL (37 mã, bản chụp, không AI) · tập con · lỗi phân biệt (thiếu/[]/sai kiểu/trùng/lạ/contract/loại/catalogH/sourceH) trước
compute · cùng ý định → lặp lại không chạy lại, khác ý định → xung đột · upload đóng sau giữ chỗ · thay tệp/đổi tham số giữa chừng không đổi
bản chụp · hai yêu cầu đồng thời một lượt → đúng một thắng · nhánh cũ (không contract) giữ hành vi.
"""
import hashlib
import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "tests"))
TMP = tempfile.mkdtemp(prefix="test_common_api_")  # giữ lại làm bằng chứng
# FIX01 F6: thư mục kết quả NẰM TRONG thư mục dữ liệu (duong_dan_tai chỉ cấp /tai/ cho đường dẫn dưới HD_DU_LIEU) — giữ toàn bộ tmp/DB/tệp
os.environ.update(HD_DU_LIEU=os.path.join(TMP, "du_lieu"), HD_OUT_DIR=os.path.join(TMP, "du_lieu", "ket_qua"),
                  HD_DANH_MUC_HD=os.path.join(TMP, "du_lieu", "danh_muc_hd"),
                  HD_CSDL=os.path.join(TMP, "du_lieu", "hop_dong.db"), HD_THU_MUC_KHOA=os.path.join(TMP, "khoa"))
for k in ("OLLAMA_URL", "AI_MODEL", "HD_RA_LAI", "HD_CLOUD", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "HD_PORT"):
    os.environ.pop(k, None)

import mau_gia_lap  # noqa: E402
from may_chu import dich_vu as dv  # noqa: E402
from may_chu import server as sv  # noqa: E402
from trich_xuat import danh_muc  # noqa: E402

CONTRACT = "trich-tham-so-common/v1"
CAT_SHA = "05846a2acd60f2cde708d13a163a137ee3fb0b4e08fd84f85a7e14e7ef861bcd"


def _cam(*a, **k):
    raise AssertionError("Nhánh common/v1 không được thăm dò AI/cloud/đọc cấu hình AI")


def anh(goc):
    """Oracle toàn vẹn: (đường dẫn tương đối đầy đủ, SHA-256, độ dài) của MỌI tệp dưới gốc — không basename/size/đếm đơn thuần."""
    goc = Path(goc)
    return sorted((p.relative_to(goc).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size) for p in goc.rglob("*") if p.is_file())


def lam_hong_cung_co(p, sao_luu_dir):
    """Hỏng dữ liệu DEMO cùng kích thước (đảo 1 byte giữa tệp) SAU khi sao lưu bytes bằng CreateNew — không xóa/tạo lại."""
    p = Path(p)
    b = p.read_bytes()
    os.makedirs(sao_luu_dir, exist_ok=True)
    with open(os.path.join(sao_luu_dir, hashlib.sha256(str(p).encode()).hexdigest() + "_" + p.name), "xb") as f:
        f.write(b)
    i = len(b) // 2
    p.write_bytes(b[:i] + bytes([b[i] ^ 0xFF]) + b[i + 1:])
    return b


class CommonApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = sv.tao_may_chu(0)
        cls.port = sv.PORT
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()
        cls.docx, _ = mau_gia_lap.tao_hop_dong(os.path.join(TMP, "mau"), "HD_COMMON")
        cls.raw = Path(cls.docx).read_bytes()
        cls.h = hashlib.sha256(cls.raw).hexdigest()
        cls.ma37 = [p["ma"] for p in danh_muc.load_params(str(danh_muc.CATALOG_COMMON["XD"]["path"]))]
        cls.cam = [patch("trich_xuat.ai_local.MayAI.models", _cam), patch("trich_xuat.cau_hinh.doc_cau_hinh", _cam),
                   patch.object(dv, "la_claude", _cam)]
        for p in cls.cam:
            p.start()

    @classmethod
    def tearDownClass(cls):
        for p in cls.cam:
            p.stop()
        cls.srv.shutdown()
        cls.srv.server_close()

    # ------------------------------------------------------------------ HTTP thật tới máy chủ nguồn
    def goi(self, method, path, body=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        h = {"Host": f"127.0.0.1:{self.port}", "X-HD": "1"}
        data = None
        if body is not None:
            data, h["Content-Type"] = json.dumps(body).encode("utf-8"), "application/json"
        elif raw is not None:
            data = raw
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = r.read()
        c.close()
        return r.status, (json.loads(out) if out[:1] in (b"{", b"[") else out)

    def luot(self, raw=None):
        st, r = self.goi("POST", "/api/trich_xuat", {})
        self.assertEqual(st, 200, r)
        st, u = self.goi("POST", f"/api/trich_xuat/{r['luot']}/tep?ten={urllib.parse.quote('hop_dong.docx')}", raw=raw or self.raw)
        self.assertEqual(st, 200, u)
        return r["luot"]

    def body(self, **sua):
        b = {"contract": CONTRACT, "mode": "RULE_ONLY", "loai_hop_dong": "XD", "catalog_id": "XD", "catalog_sha256": CAT_SHA,
             "source_sha256": self.h, "request_id": "test:" + os.urandom(6).hex(), "tham_so": "ALL"}
        b.update(sua)
        return {k: v for k, v in b.items() if v is not ...}

    def cho(self, luot, han=300):
        het = time.time() + han
        while time.time() < het:
            st, s = self.goi("GET", f"/api/trich_xuat/{luot}")
            self.assertEqual(st, 200, s)
            if s["tt"] in ("xong", "loi", "da_dung", "unknown"):  # FIX03: 'unknown' là kết thúc chưa rõ (không treo tới hết hạn)
                return s
            time.sleep(0.2)
        self.fail("lượt chưa xong")

    def goi_tho(self, path):
        """GET trả bytes THÔ (không parse) — để so SHA/độ dài đúng bytes tải thật."""
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        c.request("GET", path, headers={"Host": f"127.0.0.1:{self.port}", "X-HD": "1"})
        r = c.getresponse()
        out = r.read()
        c.close()
        return r.status, out

    def ket_qua_goc(self, s):
        # FIX03 R1: chỉ đọc khi common 'done' có niêm phong; đường tải đúng ref đầy đủ; bytes tải thật đúng SHA/độ dài niêm phong
        self.assertEqual((s["tt"], s["common"]["tt"]), ("xong", "done"), s.get("common"))
        seal = s["common"]["seal"]
        hd = [h for h in s["hd"] if (h.get("tai") or {}).get("json")]
        self.assertEqual(len(hd), 1, s["hd"])
        self.assertTrue(hd[0]["tai"]["json"].endswith(f"/{s['luot']}/{seal['ref']}"), (hd[0]["tai"], seal))
        st, raw = self.goi_tho(urllib.parse.quote(hd[0]["tai"]["json"], safe="/"))
        self.assertEqual(st, 200)
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)), (seal["sha256"], seal["byte_length"]))
        return json.loads(raw.decode("utf-8"))

    # ------------------------------------------------------------------ dương tính
    def test_c01_rule_only_all_xd_ban_chup(self):
        lu = self.luot()
        b = self.body()
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
        self.assertEqual(st, 200, r)
        self.assertEqual((r["contract"], r["lap_lai"], r["ban_chup"]["tham_so_da_dung"]), (CONTRACT, False, self.ma37))
        s = self.cho(lu)
        self.assertEqual(s["tt"], "xong", s.get("thong_bao"))
        kq = self.ket_qua_goc(s)
        self.assertEqual(kq["che_do"], "RULE_ONLY")
        cm = kq["common"]
        for k in ("contract", "request_id", "source_sha256", "catalog_sha256", "body_sha256"):
            self.assertIn(k, cm)
        self.assertEqual((cm["request_id"], cm["source_sha256"], cm["catalog_sha256"], cm["tham_so_yeu_cau"]), (b["request_id"], self.h, CAT_SHA, "ALL"))
        self.assertEqual(cm["tham_so_da_dung"], self.ma37)
        self.assertEqual([d["ma"] for d in kq["bang"]], self.ma37)
        self.assertEqual(len(cm["implementation"]["sha256"]), 64)
        # quy tắc TC của nguồn vẫn cho giá trị có trích dẫn trên DEMO; mã khác không AI → không bịa giá trị
        tc = [d for d in kq["bang"] if d["nguon"] == "Quy tắc"]
        self.assertTrue(tc, "RULE_ONLY phải giữ positive quy tắc TC của nguồn")
        for d in tc:
            self.assertTrue(d["ma"].startswith("TC-") and d["gia_tri"] and d["trich_dan"], d)
        for d in kq["bang"]:
            if d["nguon"] != "Quy tắc":
                self.assertEqual(d["gia_tri"], "", d["ma"])
        # bản chụp tồn tại trong lượt, đúng bytes
        snap = Path(os.environ["HD_OUT_DIR"]) / lu / "_common"
        self.assertEqual(hashlib.sha256((snap / f"{self.h}.docx").read_bytes()).hexdigest(), self.h)
        self.assertEqual(json.loads((snap / "request.json").read_text(encoding="utf-8"))["tham_so_da_dung"], self.ma37)

    def test_c02_tap_con(self):
        lu = self.luot()
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", self.body(tham_so=["TT-02", "TC-01"]))
        self.assertEqual(st, 200, r)
        kq = self.ket_qua_goc(self.cho(lu))
        self.assertEqual(sorted(d["ma"] for d in kq["bang"]), ["TC-01", "TT-02"])
        self.assertEqual(kq["common"]["tham_so_yeu_cau"], ["TT-02", "TC-01"])

    # ------------------------------------------------------------------ lỗi phân biệt, trước compute
    def test_c03_loi_ro_truoc_khi_tinh(self):
        ca = [(dict(tham_so=...), 400, "THAM_SO_THIEU"), (dict(tham_so=[]), 400, "THAM_SO_RONG"), (dict(tham_so="TC-01"), 400, "THAM_SO_SAI_KIEU"),
              (dict(tham_so=["TC-01", 3]), 400, "THAM_SO_SAI_KIEU"), (dict(tham_so=["TC-01", "TC-01"]), 400, "THAM_SO_TRUNG"),
              (dict(contract="trich-tham-so-common/v2"), 400, "COMMON_CONTRACT"), (dict(mode="AI"), 400, "COMMON_MODE"),
              (dict(loai_hop_dong="KCN"), 400, "COMMON_LOAI_KHONG_HO_TRO"), (dict(loai_hop_dong=...), 400, "COMMON_LOAI_THIEU"),
              (dict(catalog_id="KCN"), 400, "COMMON_CATALOG_ID"), (dict(catalog_sha256="0" * 64), 409, "COMMON_CATALOG_SHA_KHAC"),
              (dict(request_id="có dấu"), 400, "COMMON_REQUEST_ID"), (dict(them=["x"]), 400, "COMMON_TRUONG_LA")]
        for sua, ma_http, ma in ca:
            lu = self.luot()
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", self.body(**sua))
            self.assertEqual((st, (r.get("chi_tiet") or {}).get("ma")), (ma_http, ma), (sua, r))
            self.assertNotIn(lu, dv.LUOT, sua)  # chưa compute
        # mã lạ: phát hiện sau khi đọc bản chụp catalog — vẫn trước compute, trạng thái chụp ghi rõ
        lu = self.luot()
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", self.body(tham_so=["TC-01", "XX-99"]))
        self.assertEqual((st, r["chi_tiet"]["ma"]), (400, "THAM_SO_LA"))
        self.assertNotIn(lu, dv.LUOT)
        self.assertEqual(self.goi("GET", f"/api/trich_xuat/{lu}")[1]["common"]["tt"], "loi_capture")
        # sourceH khác bytes đã tải
        lu = self.luot()
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", self.body(source_sha256="a" * 64))
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_SOURCE_SHA_KHAC"))
        self.assertNotIn(lu, dv.LUOT)

    # ------------------------------------------------------------------ ý định, giữ chỗ, bản chụp
    def test_c04_lap_lai_xung_dot_va_upload_dong(self):
        lu = self.luot()
        b = self.body()
        st, r1 = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
        self.assertEqual(st, 200, r1)
        st, r2 = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
        self.assertEqual((st, r2["lap_lai"]), (200, True))  # không chạy lại
        st, r3 = self.goi("POST", f"/api/trich_xuat/{lu}/chay", {**b, "tham_so": ["TC-01"]})
        self.assertEqual((st, r3["chi_tiet"]["ma"]), (409, "COMMON_XUNG_DOT"))
        st, r4 = self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=khac.docx", raw=self.raw)
        self.assertEqual(st, 409, r4)  # upload đã đóng sau giữ chỗ
        self.assertEqual(self.cho(lu)["tt"], "xong")

    def test_c05_thay_doi_xen_ke_khong_doi_ban_chup(self):
        """Đổi tham số trả về (đối tượng dùng chung) và ghi đè tệp tải lên SAU khi chụp → kết quả vẫn theo bản chụp lúc nhận."""
        goc = danh_muc.load_params_ban_chup
        giu = {}

        def theo_doi(path):
            ps = goc(path)
            giu["ps"] = ps
            return ps
        lu = self.luot()
        with patch("trich_xuat.danh_muc.load_params_ban_chup", theo_doi):
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", self.body(tham_so=["TC-01", "TC-04"]))
        self.assertEqual(st, 200, r)
        for p in giu["ps"]:  # đổi đối tượng gốc sau khi nhận start
            p["mo_ta"] = "ĐÃ BỊ ĐỔI"
        (Path(os.environ["HD_OUT_DIR"]) / lu / "dau_vao" / "hop_dong.docx").write_bytes(b"PK\x03\x04 thay the")
        kq = self.ket_qua_goc(self.cho(lu))
        self.assertEqual(kq["common"]["source_sha256"], self.h)
        self.assertTrue(all(d["mo_ta"] != "ĐÃ BỊ ĐỔI" for d in kq["bang"]))
        self.assertTrue(all(p["mo_ta"] != "ĐÃ BỊ ĐỔI" for p in kq["common"]["tham_so_snapshot"]))

    def test_c06_dong_thoi_mot_luot_dung_mot_thang(self):
        lu = self.luot()
        kq = []

        def mot(rid):
            kq.append(self.goi("POST", f"/api/trich_xuat/{lu}/chay", self.body(request_id=rid)))
        ts = [threading.Thread(target=mot, args=(f"dong-thoi:{i}",)) for i in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(120)
        self.assertEqual(sorted(st for st, _ in kq), [200, 409], kq)
        self.assertEqual([r["chi_tiet"]["ma"] for st, r in kq if st == 409], ["COMMON_XUNG_DOT"])
        self.assertEqual(self.cho(lu)["tt"], "xong")

    # ------------------------------------------------------------------ FIX01: create bền/idempotent, giữ chỗ chung với legacy, khởi động lại
    def tao_common(self, b):
        return self.goi("POST", "/api/trich_xuat", {"contract": CONTRACT, "request_id": b["request_id"], "yeu_cau": b})

    def test_c08_create_common_mat_ack_va_dong_thoi(self):
        b = self.body(request_id="m4:0123456789abcdef")  # ID có ':' — registry dùng tên băm (Windows)
        st, r1 = self.tao_common(b)
        self.assertEqual((st, r1["lap_lai"]), (200, False), r1)
        st, r2 = self.tao_common(b)  # mất ACK lần đầu (máy chủ ĐÃ tạo) → gửi lại đúng ý định → đúng lượt cũ, không tạo lượt thứ hai
        self.assertEqual((st, r2["luot"], r2["lap_lai"]), (200, r1["luot"], True))
        st, r3 = self.tao_common({**b, "tham_so": ["TC-01"]})
        self.assertEqual((st, r3["chi_tiet"]["ma"]), (409, "COMMON_XUNG_DOT"))
        self.assertTrue((Path(os.environ["HD_OUT_DIR"]) / "_common_y_dinh" / (hashlib.sha256(b["request_id"].encode()).hexdigest() + ".json")).is_file())
        st, s = self.goi("POST", "/api/trich_xuat", {})  # body {} cũ giữ nguyên: lượt mới
        self.assertEqual(st, 200)
        self.assertNotEqual(s["luot"], r1["luot"])
        # đồng thời: cùng ý định → một lượt; hai ý định khác → hai lượt, không lỗi va nhãn thời gian
        cung, khac = self.body(), [self.body(), self.body()]
        kq, loi = [], []

        def mot(x):
            try:
                kq.append(self.tao_common(x))
            except BaseException as e:  # noqa: BLE001 — thu mọi ngoại lệ, không để chìm trong thread
                loi.append(e)
        ts = [threading.Thread(target=mot, args=(x,)) for x in (cung, cung, *khac)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        self.assertFalse(any(t.is_alive() for t in ts), "còn thread sống")  # FIX02 R5: đủ BỐN phản hồi, không thread sống/ngoại lệ chìm
        self.assertEqual((loi, len(kq)), ([], 4), (loi, kq))
        self.assertTrue(all(st == 200 for st, _ in kq), kq)
        luot = [r["luot"] for _, r in kq]
        self.assertEqual(len(set(luot)), 3)
        self.assertEqual(sum(1 for _, r in kq if r["request_id"] == cung["request_id"] and not r["lap_lai"]), 1)

    def test_c09_upload_theo_y_dinh_va_chay_tron_vong(self):
        b = self.body()
        st, r = self.tao_common(b)
        lu = r["luot"]
        st, x = self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=khac.docx", raw=b"PK\x03\x04 bytes khac")
        self.assertEqual((st, x["chi_tiet"]["ma"]), (409, "COMMON_SOURCE_SHA_KHAC"))
        for _ in range(2):  # mất ACK upload → gửi lại cùng bytes: idempotent, không thêm tệp thứ hai
            st, u = self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=hop_dong.docx", raw=self.raw)
            self.assertEqual(st, 200, u)
        self.assertEqual(len(self.goi("GET", f"/api/trich_xuat/{lu}")[1]["tep_dau_vao"]), 1)
        st, s1 = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
        st2, s2 = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)  # mất ACK start → gửi lại: lap_lai
        self.assertEqual((st, s1["lap_lai"], st2, s2["lap_lai"]), (200, False, 200, True))
        self.assertEqual(self.cho(lu)["tt"], "xong")
        self.assertEqual(self.ket_qua_goc(self.cho(lu))["common"]["request_id"], b["request_id"])

    def test_c10_legacy_va_common_cung_ranh_gioi_giu_cho(self):
        # (a) legacy đang giữ chỗ (đang đọc cấu hình NGOÀI khóa) → common start cùng lượt bị chặn, legacy không bị common ghi đè
        lu = self.luot()
        b = self.body()
        ket = {}

        def cau_hinh_cham():
            try:
                dv.chay_luot(lu, b)
            except dv.LoiNguoiDung as e:
                ket["common"] = (e.ma, (e.chi_tiet or {}).get("ma"))
            raise RuntimeError("dừng legacy trong kiểm thử (không gọi AI)")
        with patch("trich_xuat.cau_hinh.doc_cau_hinh", cau_hinh_cham), patch.object(dv.ch, "doc_cau_hinh", cau_hinh_cham):
            with self.assertRaises(RuntimeError):
                dv.chay_luot(lu, {})
        self.assertEqual(ket["common"], (409, "COMMON_LUOT_DA_CHAY"))
        self.assertNotIn(lu, dv.GIU_LEGACY)  # giữ chỗ legacy nhả khi legacy lỗi
        self.assertFalse((Path(os.environ["HD_OUT_DIR"]) / lu / "_common_giu.json").exists())
        # (b) common đã giữ chỗ → legacy start bị chặn (không nhận cấu hình/AI)
        lu = self.luot()
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", self.body())
        self.assertEqual(st, 200, r)
        with self.assertRaises(dv.LoiNguoiDung) as cm:
            dv.chay_luot(lu, {})
        self.assertEqual(cm.exception.ma, 409)
        self.cho(lu)

    def test_c11_khoi_dong_lai_lap_lai_dung_va_mo_coi(self):
        lu = self.luot()
        b = self.body()
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)[0], 200)
        self.assertEqual(self.cho(lu)["tt"], "xong")
        raw_truoc = anh(Path(os.environ["HD_OUT_DIR"]) / lu)  # FIX02 R5: đường dẫn tương đối đầy đủ + SHA + độ dài
        with dv._KHOA_LUOT:  # mô phỏng KHỞI ĐỘNG LẠI: mất trạng thái bộ nhớ, dữ kiện bền còn nguyên
            dv.COMMON.pop(lu, None)
            dv.LUOT.pop(lu, None)
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
        self.assertEqual((st, r["lap_lai"], r["trang_thai_common"]), (200, True, "done"), r)  # không mkdir lại/không 500/không chạy lại
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", {**b, "tham_so": ["TC-01"]})
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_XUNG_DOT"))
        self.assertEqual(anh(Path(os.environ["HD_OUT_DIR"]) / lu), raw_truoc)
        # mồ côi: đã giữ chỗ + chụp nhưng tiến trình sở hữu mất trước khi chạy → UNKNOWN, không tự chạy lại
        lu = self.luot()
        b2 = self.body()
        with patch.object(dv.QLV, "tao", lambda *a, **k: type("V", (), {"to_dict": lambda s: {"id": "khong-chay"}})()):
            self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/chay", b2)[0], 200)
        with dv._KHOA_LUOT:
            dv.COMMON.pop(lu, None)
            dv.LUOT.pop(lu, None)
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b2)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_MO_COI"))
        self.assertEqual(self.goi("GET", f"/api/trich_xuat/{lu}")[1]["common"]["tt"], "orphaned")
        st, u = self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=x.docx", raw=self.raw)
        self.assertEqual(st, 409)  # giữ chỗ bền: upload vẫn đóng sau khởi động lại

    # ------------------------------------------------------------------ FIX02
    def test_c12_upload_replay_sau_khi_da_chay(self):
        """R1: cùng bytes của ý định gửi lại khi lượt đã giữ chỗ/đã chạy/đã xong → replay đúng tệp cũ, không thêm/ghi đè; bytes khác → 409 có mã."""
        b = self.body()
        lu = self.tao_common(b)[1]["luot"]
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=hop_dong.docx", raw=self.raw)[0], 200)
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)[0], 200)
        dau_vao = anh(Path(os.environ["HD_OUT_DIR"]) / lu / "dau_vao")
        st, u = self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=hop_dong.docx", raw=self.raw)  # trong lúc đang chạy
        self.assertEqual((st, u["lap_lai"], u["ten"]), (200, True, "hop_dong.docx"))
        self.assertEqual(self.cho(lu)["tt"], "xong")
        st, u = self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=ten_khac.docx", raw=self.raw)  # sau khi xong
        self.assertEqual((st, u["lap_lai"], u["ten"]), (200, True, "hop_dong.docx"))
        st, x = self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=hop_dong.docx", raw=b"PK\x03\x04 khac")
        self.assertEqual((st, x["chi_tiet"]["ma"]), (409, "COMMON_SOURCE_SHA_KHAC"))
        self.assertEqual(anh(Path(os.environ["HD_OUT_DIR"]) / lu / "dau_vao"), dau_vao)
        lu2 = self.luot()  # legacy: upload sau start vẫn đóng
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu2}/chay", self.body())[0], 200)
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu2}/tep?ten=x.docx", raw=self.raw)[0], 409)
        self.cho(lu2)

    def test_c13_create_ben_qua_khe_ghi_va_registry_hong(self):
        """R2: lỗi giữa điểm giữ chỗ (registry) và liên kết per-run → thử lại khôi phục ĐÚNG lượt, một giữ chỗ; registry hỏng → UNKNOWN có lý do,
        không cấp lượt khác. Hỏng chỉ trên bản DEMO đã sao lưu CreateNew."""
        b = self.body(request_id="m4:khe-ghi-" + os.urandom(3).hex())
        goc_ghi, dem = dv._ghi_moi, {"n": 0}

        def ghi_loi_lien_ket(p, data):
            if Path(p).name == "_common_y_dinh.json" and dem["n"] == 0:
                dem["n"] += 1
                raise OSError("giả lập dừng giữa khe ghi")
            return goc_ghi(p, data)
        out = Path(os.environ["HD_OUT_DIR"])
        truoc = {p.name for p in out.iterdir() if p.is_dir()}
        with patch.object(dv, "_ghi_moi", ghi_loi_lien_ket):
            st, r = self.tao_common(b)
        self.assertEqual(st, 500, r)
        st, r = self.tao_common(b)  # thử lại: khôi phục từ điểm giữ chỗ
        self.assertEqual((st, r["lap_lai"]), (200, True), r)
        moi = {p.name for p in out.iterdir() if p.is_dir()} - truoc
        self.assertEqual(moi, {r["luot"]})  # MỘT lượt cho một ý định
        reg = out / "_common_y_dinh" / (hashlib.sha256(b["request_id"].encode()).hexdigest() + ".json")
        self.assertEqual((out / r["luot"] / "_common_y_dinh.json").read_bytes(), reg.read_bytes())
        # registry hỏng (cùng ý định DEMO khác) → UNKNOWN, không tạo lượt
        b2 = self.body()
        self.tao_common(b2)
        reg2 = out / "_common_y_dinh" / (hashlib.sha256(b2["request_id"].encode()).hexdigest() + ".json")
        lam_hong_cung_co(reg2, os.path.join(TMP, "sao_luu_r2"))
        truoc2 = anh(out)
        st, r = self.tao_common(b2)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"))
        self.assertEqual(anh(out), truoc2)

    def test_c14_rehydrate_kiem_toan_ven(self):
        """R3: replay sau mất bộ nhớ chỉ 'done' khi niêm phong khớp bytes; hỏng cùng kích thước ở kết quả/bản chụp HĐ/request → UNKNOWN; không chạy
        lại, không đổi tệp."""
        out = Path(os.environ["HD_OUT_DIR"])

        def mot_luot():
            lu, b = self.luot(), self.body()
            self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)[0], 200)
            s = self.cho(lu)
            self.assertEqual((s["tt"], s["common"]["tt"]), ("xong", "done"))
            seal = s["common"]["seal"]
            p = out / lu / seal["ref"]
            self.assertEqual((seal["sha256"], seal["byte_length"]), (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size))
            return lu, b, seal

        def quen(lu):
            with dv._KHOA_LUOT:
                dv.COMMON.pop(lu, None)
                dv.LUOT.pop(lu, None)
        lu, b, seal = mot_luot()
        quen(lu)
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
        self.assertEqual((st, r["trang_thai_common"], r["seal"]["sha256"]), (200, "done", seal["sha256"]))  # replay đúng tham chiếu/hash cũ
        for dich in (lambda lu, s: out / lu / s["ref"],                                     # kết quả gốc
                     lambda lu, s: next((out / lu / "_common").glob("*.docx")),            # bản chụp tệp HĐ
                     lambda lu, s: out / lu / "_common" / "request.json"):                 # request đã chụp
            lu, b, seal = mot_luot()
            lam_hong_cung_co(dich(lu, seal), os.path.join(TMP, "sao_luu_r3"))
            truoc = anh(out / lu)
            quen(lu)
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
            self.assertEqual(self.goi("GET", f"/api/trich_xuat/{lu}")[1]["common"]["tt"], "unknown")
            self.assertEqual(anh(out / lu), truoc)  # không chạy lại, không ghi đè

    # ------------------------------------------------------------------ FIX03
    def chua_cong_bo(self, lu, ly_do=None):
        """Mọi đường công bố của lượt common đều KHÔNG báo hoàn tất/kết quả: status, list, viec detail, raw download, view hd. Trả status."""
        out = Path(os.environ["HD_OUT_DIR"])
        st, s = self.goi("GET", f"/api/trich_xuat/{lu}")
        self.assertEqual(st, 200, s)                                    # không 500
        self.assertNotEqual(s["tt"], "xong", s)
        self.assertEqual(s.get("tai"), {}, s)
        self.assertFalse(any(h.get("tai") for h in s["hd"]), s["hd"])
        self.assertIsNone(s["common"].get("seal"), s["common"])
        if ly_do is not None:
            self.assertEqual(s["common"]["tt"], "unknown", s["common"])
            self.assertIn(ly_do, s["common"]["loi"] or "", s["common"])
        st, ds = self.goi("GET", "/api/trich_xuat?gioi_han=500")
        self.assertEqual(st, 200, ds)
        dong = [x for x in ds["ds"] if x["luot"] == lu]
        self.assertEqual(len(dong), 1)
        self.assertNotEqual(dong[0]["tt"], "xong", dong)
        self.assertEqual(dong[0]["so_xong"], 0, dong)
        try:
            v = dv.QLV.lay(f"TX-{lu}").to_dict(day_du=True)              # callback chi tiết của viec (cùng gate)
        except KeyError:
            v = None                                                    # khởi động lại: không còn việc trong bộ nhớ
        if v is not None:
            self.assertNotEqual(v["chi_tiet"]["tt"], "xong", v["chi_tiet"])
            self.assertFalse(v["chi_tiet"].get("tep"), v["chi_tiet"])
        kq = sorted(p for p in (out / lu).rglob("*_KET_QUA.json") if "_common" not in p.parts)
        for p in kq:
            rel = p.relative_to(Path(os.environ["HD_DU_LIEU"])).as_posix()
            st, r = self.goi("GET", "/tai/" + urllib.parse.quote(rel))
            self.assertEqual((st, (r.get("chi_tiet") or {}).get("ma") if isinstance(r, dict) else r), (409, "COMMON_CHUA_NIEM_PHONG"))
            st, r = self.goi("GET", f"/api/trich_xuat/{lu}/hd/{urllib.parse.quote(p.parent.name)}")
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_NIEM_PHONG"))
        return s

    def quen(self, lu):
        with dv._KHOA_LUOT:  # mô phỏng KHỞI ĐỘNG LẠI: mất trạng thái bộ nhớ, dữ kiện bền còn nguyên
            dv.COMMON.pop(lu, None)
            dv.LUOT.pop(lu, None)

    def test_c15_barrier_truoc_niem_phong(self):
        """R1 — barrier THẬT giữ callback ngay trước niêm phong sau khi worker đã ghi raw/native xong: trước khi thả, không đường nào công bố;
        thả → đúng bytes niêm phong. Sau đó cùng cửa sổ với niêm phong LỖI rồi KHỞI ĐỘNG LẠI → UNKNOWN, không chạy lại, không đổi tệp."""
        out = Path(os.environ["HD_OUT_DIR"])
        goc_np = dv._niem_phong
        for che_do in ("tha", "loi"):
            vao, tha = threading.Event(), threading.Event()

            def giu(*a, **k):
                vao.set()
                if not tha.wait(300):
                    raise AssertionError("barrier quá hạn")
                if che_do == "loi":
                    raise RuntimeError("giả lập niêm phong lỗi/tiến trình chết trước khi ghi seal")
                return goc_np(*a, **k)
            b = self.body()
            lu = self.tao_common(b)[1]["luot"]
            self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=hop_dong.docx", raw=self.raw)[0], 200)
            with patch.object(dv, "_niem_phong", giu):
                st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
                self.assertEqual(st, 200, r)
                try:
                    self.assertTrue(vao.wait(300), "callback không tới cửa sổ niêm phong")
                    self.assertEqual(dv.LUOT[lu].s["tt"], "xong")       # worker ĐÃ xong thật, raw/native đã có trên đĩa
                    self.assertTrue([p for p in (out / lu).rglob("*_KET_QUA.json") if "_common" not in p.parts])
                    self.assertFalse((out / lu / "_common" / "ket_qua_seal.json").exists())
                    truoc = anh(out / lu)
                    s = self.chua_cong_bo(lu)
                    self.assertEqual(s["common"]["tt"], "running")
                    self.assertEqual(anh(out / lu), truoc)              # đọc không ghi
                finally:
                    tha.set()
                het = time.time() + 120
                while dv.QLV.lay(f"TX-{lu}").ket_thuc is None and time.time() < het:
                    time.sleep(0.1)
                self.assertIsNotNone(dv.QLV.lay(f"TX-{lu}").ket_thuc)
            if che_do == "tha":
                s = self.cho(lu)
                kq = self.ket_qua_goc(s)                                 # chỉ SAU khi thả: done + đúng bytes niêm phong
                self.assertEqual(kq["common"]["request_id"], b["request_id"])
                seal = s["common"]["seal"]
                st, r = self.goi("GET", f"/api/trich_xuat/{lu}/hd/{urllib.parse.quote(seal['ref'].split('/')[0])}")
                self.assertEqual(st, 200, r)
                st, r = self.goi("PATCH", f"/api/trich_xuat/{lu}/hd/{urllib.parse.quote(seal['ref'].split('/')[0])}/o/TC-01", {"gia_tri": "x"})
                self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_BAT_BIEN"))  # raw đã niêm phong bất biến
                continue
            truoc = anh(out / lu)
            self.chua_cong_bo(lu, "Không niêm phong được")
            v = dv.QLV.lay(f"TX-{lu}").to_dict()
            self.assertEqual(v["tt"], "loi")
            self.assertIn("COMMON_CHUA_RO", v["loi"])                   # việc không báo hoàn tất
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)  # UNKNOWN đi trước, không chạy lại
            self.quen(lu)                                                # khởi động lại trong cửa sổ (chưa có seal, _luot.json đã 'xong')
            self.chua_cong_bo(lu, "chưa có niêm phong")
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
            self.assertNotIn(lu, dv.LUOT)                                # không tái compute
            self.assertEqual(anh(out / lu), truoc)

    def luot_niem_phong(self):
        b = self.body()
        lu = self.tao_common(b)[1]["luot"]
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/tep?ten=hop_dong.docx", raw=self.raw)[0], 200)
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)[0], 200)
        s = self.cho(lu)
        self.ket_qua_goc(s)                                              # positive trước negative
        return lu, b, s["common"]["seal"]

    def ghi_de(self, p, data, nhan):
        """Sửa dữ liệu DEMO: sao lưu bytes cũ bằng CreateNew rồi ghi đè (không xóa). Trả bytes cũ để khôi phục bằng ghi đè."""
        p = Path(p)
        cu = p.read_bytes() if p.exists() else None
        d = os.path.join(TMP, "sao_luu_f3", nhan)
        os.makedirs(d, exist_ok=True)
        if cu is not None:
            with open(os.path.join(d, hashlib.sha256(str(p).encode()).hexdigest() + "_" + p.name), "xb") as f:
                f.write(cu)
        p.write_bytes(data)
        return cu

    def test_c16_dto_sai_kieu_la_unknown_khong_500(self):
        """R1 — JSON HỢP LỆ nhưng DTO sai kiểu ở _luot.json/_tuy_chon.json của lượt common đã niêm phong (sau khởi động lại) → status/list/raw/
        view: UNKNOWN có lý do, không 500, không lộ kết quả; khôi phục bytes → công bố lại đúng niêm phong."""
        out = Path(os.environ["HD_OUT_DIR"])
        lu, b, seal = self.luot_niem_phong()
        for ten, v, ly_do in (("_luot.json", [], "trạng thái lượt"), ("_luot.json", {"tt": 1}, "sai kiểu tt"),
                              ("_luot.json", {"tt": "xong", "hd": "x"}, "sai kiểu hd"),
                              ("_luot.json", {"tt": "xong", "hd": [{"file": "a", "so_vang": "3"}]}, "trường hd"),
                              ("_luot.json", {"tt": "xong", "hd": [], "log": [["x", 1, 2]]}, "sai kiểu log"),
                              ("_tuy_chon.json", [1], "tùy chọn"), ("_tuy_chon.json", {"common": 5}, "tùy chọn")):
            self.quen(lu)
            cu = self.ghi_de(out / lu / ten, json.dumps(v).encode("utf-8"), f"c16_{ten}_{len(json.dumps(v))}")
            truoc = anh(out / lu)
            self.chua_cong_bo(lu, ly_do if ten == "_tuy_chon.json" else "trạng thái lượt")
            self.assertEqual(anh(out / lu), truoc)
            self.ghi_de(out / lu / ten, cu, f"c16_khoi_phuc_{ten}_{len(json.dumps(v))}")
        self.quen(lu)
        s = self.goi("GET", f"/api/trich_xuat/{lu}")[1]
        self.assertEqual(self.ket_qua_goc(s)["common"]["request_id"], b["request_id"])
        self.assertEqual(s["common"]["seal"], seal)

    def test_c17_dot_bien_json_hop_le_co_muc_tieu(self):
        """R2 — đột biến JSON HỢP LỆ từng trường, GIỮ hash/độ dài đối chiếu cũ (cập nhật seal cho khớp bytes mới) để chứng minh guard ngữ nghĩa
        bắt đúng lý do: request type/catalog/source, ALL→tập con, snapshot tham số, implementation SHA/map, native.common, seal ref, liên kết/giữ chỗ
        luot/source/body. Mỗi ca: UNKNOWN có lý do ở mọi đường công bố, replay 409 COMMON_CHUA_RO, không chạy lại, không đổi tệp."""
        out = Path(os.environ["HD_OUT_DIR"])

        def canon(x):
            return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

        def doc(p):
            return json.loads(Path(p).read_bytes().decode("utf-8"))

        def sua_request(f):
            def lam(lu, seal, nhan):
                p = out / lu / "_common" / "request.json"
                req = doc(p)
                f(req)
                self.ghi_de(p, canon(req), nhan)
                self.ghi_de(out / lu / "_common" / "ket_qua_seal.json",
                            canon({**seal, "request_sha256": hashlib.sha256(canon(req)).hexdigest(), "meta_sha256": hashlib.sha256(canon(req)).hexdigest()}),
                            nhan + "_seal")
            return lam

        def sua_native(f):
            def lam(lu, seal, nhan):
                p = out / lu / seal["ref"]
                kq = doc(p)
                f(kq)
                moi = json.dumps(kq, ensure_ascii=False, indent=1).encode("utf-8")
                self.ghi_de(p, moi, nhan)
                self.ghi_de(out / lu / "_common" / "ket_qua_seal.json",
                            canon({**seal, "sha256": hashlib.sha256(moi).hexdigest(), "byte_length": len(moi)}), nhan + "_seal")
            return lam

        def sua_ban_ghi(ten, **kw):
            def lam(lu, seal, nhan):
                p = out / lu / ten
                self.ghi_de(p, canon({**doc(p), **kw}), nhan)
            return lam

        def sua_seal_ref(lu, seal, nhan):
            req_b = (out / lu / "_common" / "request.json").read_bytes()
            self.ghi_de(out / lu / "_common" / "ket_qua_seal.json",
                        canon({**seal, "ref": "_common/request.json", "sha256": hashlib.sha256(req_b).hexdigest(), "byte_length": len(req_b)}), nhan)

        def impl_map(req):
            m = dict(req["implementation"]["tep_sha256"])
            m["trich_xuat/lo.py"] = "0" * 64
            req["implementation"] = {**req["implementation"], "tep_sha256": m,
                                     "sha256": hashlib.sha256(json.dumps(m, sort_keys=True).encode("utf-8")).hexdigest()}

        def body_doi(lu, seal, nhan):
            p = out / lu / "_common_y_dinh.json"
            v = doc(p)
            self.ghi_de(p, canon({**v, "body": {**v["body"], "tham_so": ["TC-01"]}}), nhan)  # body đổi, body_sha256 giữ nguyên

        ca = [("req_loai", sua_request(lambda r: r.update(loai_hop_dong="KCN")), "request.json lệch loai_hop_dong"),
              ("req_catalog", sua_request(lambda r: r.update(catalog_id="KCN")), "request.json lệch catalog_id"),
              ("req_source", sua_request(lambda r: r.update(source_sha256="a" * 64)), "request.json lệch source_sha256"),
              ("req_all_tap_con", sua_request(lambda r: r.update(tham_so_da_dung=r["tham_so_da_dung"][:5])), "request.json lệch tham_so_da_dung"),
              ("req_yeu_cau", sua_request(lambda r: r.update(tham_so_yeu_cau=list(r["tham_so_da_dung"]))), "request.json lệch tham_so_yeu_cau"),
              ("req_snapshot", sua_request(lambda r: r["tham_so_snapshot"][0].update(mo_ta="ĐÃ BỊ ĐỔI")), "request.json lệch tham_so_snapshot"),
              ("impl_sha", sua_request(lambda r: r["implementation"].update(sha256="0" * 64)), "implementation SHA không khớp"),
              ("impl_map", sua_request(impl_map), "native.common lệch implementation"),
              ("native_common", sua_native(lambda k: k["common"]["tham_so_snapshot"][0].update(mo_ta="ĐÃ BỊ ĐỔI")), "native.common lệch tham_so_snapshot"),
              ("native_bang", sua_native(lambda k: k["bang"].reverse()), "tập mã trong kết quả"),
              ("seal_ref", sua_seal_ref, "kết quả gốc sai cấu trúc"),
              ("lien_ket_luot", sua_ban_ghi("_common_y_dinh.json", luot="20000101_000000"), "trỏ lượt khác"),
              ("lien_ket_source", sua_ban_ghi("_common_y_dinh.json", source_sha256="a" * 64), "request_id/source_sha256"),
              ("lien_ket_body", body_doi, "body_sha256 không khớp"),
              ("lien_ket_thieu_truong", sua_ban_ghi("_common_y_dinh.json", body_sha256=None), "thiếu/sai kiểu body_sha256"),
              ("giu_luot", sua_ban_ghi("_common_giu.json", luot="20000101_000000"), "trỏ lượt khác"),
              ("giu_kieu", sua_ban_ghi("_common_giu.json", kieu="registry_common/v1"), "không đúng kiểu")]
        for nhan, lam, ly_do in ca:
            lu, b, seal = self.luot_niem_phong()
            self.quen(lu)
            lam(lu, seal, "c17_" + nhan)
            truoc = anh(out / lu)
            self.chua_cong_bo(lu, ly_do)
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), (nhan, r))  # UNKNOWN trước xung đột
            self.assertNotIn(lu, dv.LUOT, nhan)
            self.assertEqual(anh(out / lu), truoc, nhan)
        # đang chạy trong bộ nhớ (không khởi động lại): seal trên đĩa bị thay bằng bản khác → gate công bố bắt, không tin bản trên đĩa
        lu, b, seal = self.luot_niem_phong()
        sua_native(lambda k: k["common"].update(nhan_luc="2000-01-01T00:00:00"))(lu, seal, "c17_bo_nho")
        self.chua_cong_bo(lu, "niêm phong không còn khớp")

    def test_c18_registry_doi_luot_va_thieu_truong_o_khe_ghi(self):
        """R2 — registry toàn cục đổi luot sang lượt đã có dữ kiện / đổi source → UNKNOWN, không gắn ý định vào lượt khác; registry ghi THIẾU trường ở
        khe ghi → UNKNOWN, không cấp lượt; chụp bị cắt ở khe ghi danh mục (tiến trình chết) → mồ côi, không chạy lại."""
        out = Path(os.environ["HD_OUT_DIR"])

        def canon(x):
            return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        b = self.body()
        lu = self.tao_common(b)[1]["luot"]
        reg = out / "_common_y_dinh" / (hashlib.sha256(b["request_id"].encode()).hexdigest() + ".json")
        khac = self.luot()                                                # lượt legacy đã có tệp
        v = json.loads(reg.read_bytes())
        for nhan, sua in (("luot", {"luot": khac}), ("source", {"source_sha256": "a" * 64})):
            cu = self.ghi_de(reg, canon({**v, **sua}), "c18_" + nhan)
            truoc = anh(out)
            st, r = self.tao_common(b)
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), (nhan, r))
            self.assertEqual(anh(out), truoc, nhan)
            self.assertFalse((out / khac / "_common_y_dinh.json").exists())
            self.ghi_de(reg, cu, "c18_khoi_phuc_" + nhan)
        self.assertEqual(self.tao_common(b)[1]["luot"], lu)              # khôi phục bytes → đúng lượt cũ
        # registry ghi thiếu trường 'luot' ở khe ghi (JSON hợp lệ)
        goc_ghi = dv._ghi_moi

        def ghi_thieu(p, data):
            if Path(p).parent.name == "_common_y_dinh":
                v = json.loads(data)
                v.pop("luot")
                data = canon(v)
            return goc_ghi(p, data)
        b2 = self.body()
        truoc_dir = {p.name for p in out.iterdir() if p.is_dir()}
        with patch.object(dv, "_ghi_moi", ghi_thieu):
            st, r = self.tao_common(b2)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
        truoc = anh(out)
        st, r = self.tao_common(b2)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
        self.assertEqual(anh(out), truoc)
        self.assertEqual({p.name for p in out.iterdir() if p.is_dir()}, truoc_dir)  # không cấp lượt
        # tiến trình chết ở khe ghi bản chụp danh mục (sau HĐ, trước request.json) → mồ côi/UNKNOWN sau khởi động lại; không chạy lại

        class Chet(BaseException):
            pass

        def chet_o_danh_muc(p, data):
            if Path(p).name.startswith("DANH_MUC_"):
                raise Chet()
            return goc_ghi(p, data)
        lu3, b3 = self.luot(), self.body()
        with patch.object(dv, "_ghi_moi", chet_o_danh_muc), self.assertRaises(Chet):
            dv.chay_luot(lu3, b3)
        self.assertFalse((out / lu3 / "_common" / "request.json").exists())
        self.quen(lu3)
        truoc = anh(out / lu3)
        st, s = self.goi("GET", f"/api/trich_xuat/{lu3}")
        self.assertEqual((st, s["common"]["tt"], s["tai"]), (200, "orphaned", {}))
        st, r = self.goi("POST", f"/api/trich_xuat/{lu3}/chay", b3)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_MO_COI"), r)
        self.assertNotIn(lu3, dv.LUOT)
        self.assertEqual(anh(out / lu3), truoc)
        # danh mục engine thiếu ở khe ghi (ghi lỗi thường) → lỗi chụp RÕ, bền; không compute
        def loi_o_danh_muc(p, data):
            if Path(p).name.startswith("DANH_MUC_"):
                raise OSError("giả lập ghi bản chụp danh mục lỗi")
            return goc_ghi(p, data)
        lu4, b4 = self.luot(), self.body()
        with patch.object(dv, "_ghi_moi", loi_o_danh_muc):
            st, r = self.goi("POST", f"/api/trich_xuat/{lu4}/chay", b4)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (500, "COMMON_CHUP_LOI"), r)
        self.assertNotIn(lu4, dv.LUOT)
        self.quen(lu4)
        st, r = self.goi("POST", f"/api/trich_xuat/{lu4}/chay", b4)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUP_LOI"), r)
        self.assertNotIn(lu4, dv.LUOT)

    # ------------------------------------------------------------------ FIX04
    @staticmethod
    def canon(x):
        return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def reg_cua(self, b):
        return Path(os.environ["HD_OUT_DIR"]) / "_common_y_dinh" / (hashlib.sha256(b["request_id"].encode()).hexdigest() + ".json")

    def test_c19_registry_doi_luot_sang_ten_trong(self):
        """R1 — positive reserve/replay TRƯỚC; registry đổi `luot` sang tên HỢP LỆ còn trống (giữ body/hash) → 409 COMMON_CHUA_RO, tên mới không
        xuất hiện, không compute, lượt/registry/lịch sử gốc nguyên. Khe ghi thật sau đặt lượt (registry chưa ghi) → thử lại đúng lượt đã đặt."""
        out = Path(os.environ["HD_OUT_DIR"])
        b = self.body()
        st, r1 = self.tao_common(b)
        self.assertEqual((st, r1["lap_lai"], r1["request_id"]), (200, False, b["request_id"]), r1)
        st, r2 = self.tao_common(b)
        self.assertEqual((st, r2["luot"], r2["lap_lai"]), (200, r1["luot"], True), r2)
        dat = json.loads((out / "_common_dat_luot" / f"{r1['luot']}.json").read_bytes())
        self.assertEqual((dat["luot"], dat["request_id"]), (r1["luot"], b["request_id"]))
        reg = self.reg_cua(b)
        trong = "20000103_000000"
        self.assertFalse((out / trong).exists())
        v = json.loads(reg.read_bytes())
        cu = self.ghi_de(reg, self.canon({**v, "luot": trong}), "c19_luot_trong")
        truoc = anh(out)
        so_luot = len(dv.LUOT)
        st, r = self.tao_common(b)
        self.assertEqual((st, r["chi_tiet"]["ma"], r["chi_tiet"].get("ly_do")), (409, "COMMON_CHUA_RO", "dat_luot"), r)
        self.assertFalse((out / trong).exists())                         # không cấp/chuyển sang tên trống
        self.assertEqual(anh(out), truoc)
        self.assertEqual(len(dv.LUOT), so_luot)                          # không compute
        self.ghi_de(reg, cu, "c19_khoi_phuc")
        self.assertEqual(self.tao_common(b)[1]["luot"], r1["luot"])
        # khe ghi thật: đặt lượt đã ghi, registry lỗi → thử lại khôi phục ĐÚNG lượt đã đặt (một bản ghi đặt lượt cho ý định)
        b2 = self.body()
        goc_ghi = dv._ghi_moi

        def loi_registry(p, data):
            if Path(p).parent.name == "_common_y_dinh":
                raise OSError("giả lập dừng sau đặt lượt, trước registry")
            return goc_ghi(p, data)
        with patch.object(dv, "_ghi_moi", loi_registry):
            st, r = self.tao_common(b2)
        self.assertEqual(st, 500, r)
        dat2 = [p.stem for p in (out / "_common_dat_luot").glob("*.json") if json.loads(p.read_bytes())["request_id"] == b2["request_id"]]
        self.assertEqual(len(dat2), 1)
        st, r = self.tao_common(b2)
        self.assertEqual((st, r["luot"]), (200, dat2[0]), r)
        self.assertEqual(len([p for p in (out / "_common_dat_luot").glob("*.json") if json.loads(p.read_bytes())["request_id"] == b2["request_id"]]), 1)

    def test_c20_cached_done_kiem_ban_chup_hd_va_danh_muc(self):
        """R2 — lượt done CÒN trong COMMON (không pop): hỏng bytes bản chụp DOCX / danh mục (sao lưu CreateNew, cùng kích thước) → status/list/
        viec UNKNOWN có lý do, raw/view/tải không mở; replay 409 không chạy lại. Lặp ca đối ứng sau khởi động lại."""
        out = Path(os.environ["HD_OUT_DIR"])
        for ten, dich, ly_do in (("docx", lambda lu: next((out / lu / "_common").glob("*.docx")), "bản chụp tệp HĐ khác SHA"),
                                 ("catalog", lambda lu: next((out / lu / "_common").glob("DANH_MUC_*.xlsx")), "bản chụp danh mục khác SHA")):
            for khoi_dong_lai in (False, True):
                lu, b, seal = self.luot_niem_phong()
                self.assertEqual(dv.COMMON[lu]["tt"], "done")
                lam_hong_cung_co(dich(lu), os.path.join(TMP, f"sao_luu_c20_{ten}_{khoi_dong_lai}"))
                if khoi_dong_lai:
                    self.quen(lu)
                else:
                    self.assertIn(lu, dv.COMMON)                         # cache còn nguyên — gate phải tự phát hiện
                truoc = anh(out / lu)
                self.chua_cong_bo(lu, ly_do)
                st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
                self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), (ten, khoi_dong_lai, r))
                self.assertEqual(anh(out / lu), truoc)                   # không compute, không ghi đè
                if khoi_dong_lai:
                    self.assertNotIn(lu, dv.LUOT)

    def test_c21_dto_gia_tri_reachable_va_registry_sai_kieu(self):
        """R3 — JSON hợp lệ, từng đột biến ĐỘC LẬP trên `_luot.json` thật của lượt done (các trường khác giữ nguyên): tep giá trị list/đường dẫn
        thoát, log mốc 1e300/âm/thông điệp số, hd.ten thoát, danh_muc list → status 200 common UNKNOWN đúng lý do; raw/view 409 COMMON_CHUA_NIEM_PHONG;
        replay 409, không chạy lại, lịch sử nguyên. Registry ý định khác có luot sai kiểu → create ý định khác 409 COMMON_CHUA_RO (không generic)."""
        out = Path(os.environ["HD_OUT_DIR"])
        lu, b, seal = self.luot_niem_phong()
        p = out / lu / "_luot.json"
        s0 = json.loads(p.read_bytes())
        self.assertTrue(s0["hd"] and s0["log"])                          # positive thật không rỗng
        ca = [("tep_list", {**s0, "tep": {"x": ["bad"]}}, "sai kiểu tep"), ("tep_thoat", {**s0, "tep": {"x": "../../ngoai.txt"}}, "sai kiểu tep"),
              ("tep_tuyet_doi", {**s0, "tep": {"x": "C:/ngoai.txt"}}, "sai kiểu tep"),
              ("log_lon", {**s0, "log": [[1e300, "demo"]]}, "sai kiểu log"), ("log_am", {**s0, "log": [[-1, "demo"]]}, "sai kiểu log"),
              ("log_msg", {**s0, "log": [[1.0, 5]]}, "sai kiểu log"), ("log_bool", {**s0, "log": [[True, "demo"]]}, "sai kiểu log"),
              ("hd_ten", {**s0, "hd": [{**s0["hd"][0], "ten": "../x"}]}, "tên hợp đồng không an toàn"),
              ("danh_muc", {**s0, "danh_muc": ["x"]}, "sai kiểu danh_muc"),
              # FIX05 R3: số nguyên KHỔNG LỒ hợp lệ JSON (401 chữ số) — kiểm miền trước mọi chuyển float, không OverflowError/500
              ("log_so_nguyen_khong_lo", {**s0, "log": [[10 ** 400, "demo"]]}, "mốc thời gian ngoài miền"),
              ("log_so_nguyen_am_khong_lo", {**s0, "log": [[-(10 ** 400), "demo"]]}, "mốc thời gian ngoài miền")]
        for nhan, v, ly_do in ca:
            self.quen(lu)
            cu = self.ghi_de(p, json.dumps(v, ensure_ascii=False).encode("utf-8"), "c21_" + nhan)
            truoc = anh(out / lu)
            self.chua_cong_bo(lu, ly_do)
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), (nhan, r))
            self.assertNotIn(lu, dv.LUOT, nhan)
            self.assertEqual(anh(out / lu), truoc, nhan)
            self.ghi_de(p, cu, "c21_khoi_phuc_" + nhan)
        self.quen(lu)
        self.assertEqual(self.ket_qua_goc(self.goi("GET", f"/api/trich_xuat/{lu}")[1])["common"]["request_id"], b["request_id"])
        # FIX05 R3: lỗi CHUYỂN/ĐỊNH DẠNG có kiểm soát trên một mốc DEMO trong miền (như localtime Windows từ chối) — chỉ thay tên `time` bên trong
        # module dich_vu bằng proxy ủy quyền (không sửa module time toàn cục); mốc khác định dạng bình thường
        t_demo = 4102444800.5

        class TimeProxy:
            def __getattr__(self, k):
                return getattr(time, k)

            @staticmethod
            def localtime(t=None):
                if t == t_demo:
                    raise OSError(22, "giả lập localtime từ chối mốc DEMO")
                return time.localtime(t) if t is not None else time.localtime()
        self.quen(lu)
        cu = self.ghi_de(p, json.dumps({**s0, "log": s0["log"] + [[t_demo, "demo"]]}, ensure_ascii=False).encode("utf-8"), "c21_log_dinh_dang")
        truoc = anh(out / lu)
        with patch.object(dv, "time", TimeProxy()):
            self.chua_cong_bo(lu, "không định dạng được")
            st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", b)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
        self.assertNotIn(lu, dv.LUOT)
        self.assertEqual(anh(out / lu), truoc)
        self.ghi_de(p, cu, "c21_khoi_phuc_log_dinh_dang")
        self.quen(lu)
        self.assertEqual(self.ket_qua_goc(self.goi("GET", f"/api/trich_xuat/{lu}")[1])["common"]["request_id"], b["request_id"])
        # registry ý định A có luot sai kiểu (JSON hợp lệ) → create ý định B khác: 409 COMMON_CHUA_RO hữu hạn, không cấp lượt; API cũ không đổi
        a = self.body()
        self.assertEqual(self.tao_common(a)[0], 200)
        reg = self.reg_cua(a)
        cu = self.ghi_de(reg, self.canon({**json.loads(reg.read_bytes()), "luot": []}), "c21_reg_luot_list")
        truoc_dir = {x.name for x in out.iterdir()}
        bb = self.body()
        st, r = self.tao_common(bb)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
        self.assertIn("luot sai kiểu", r["chi_tiet"]["ly_do"])
        st, r = self.tao_common(a)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
        self.assertEqual({x.name for x in out.iterdir()}, truoc_dir)
        st, leg = self.goi("POST", "/api/trich_xuat", {})                # nhánh cũ tương thích (bỏ qua bản ghi sai kiểu như trước)
        self.assertEqual(st, 200, leg)
        self.ghi_de(reg, cu, "c21_reg_khoi_phuc")
        self.assertEqual(self.tao_common(bb)[0], 200)

    def test_c22_danh_muc_rong_bi_chan_truoc_workbook(self):
        """R4 — POST /danh_muc (không ten và có ten) trên lượt common vừa create/upload (chưa có kết quả) và lượt done → 409 COMMON_BAT_BIEN,
        KHÔNG chạm ghi_danh_muc/workbook, zero thay đổi dữ liệu. Đối chứng legacy non-common: route + forwarding tới writer SPY (FIX05; workbook I/O thật NOT_RUN)."""
        du_lieu = Path(os.environ["HD_DU_LIEU"])
        b = self.body()
        lu_cho = self.tao_common(b)[1]["luot"]
        self.assertEqual(self.goi("POST", f"/api/trich_xuat/{lu_cho}/tep?ten=hop_dong.docx", raw=self.raw)[0], 200)
        lu_xong = self.luot_niem_phong()[0]
        cham = []

        def cam_workbook(*a, **k):
            cham.append(a)
            raise AssertionError("lượt common không được chạm workbook danh mục")
        with patch.object(dv, "ghi_danh_muc", cam_workbook):
            for lu in (lu_cho, lu_xong):
                for duoi in ("", "?ten=" + urllib.parse.quote("hop_dong")):
                    truoc = anh(du_lieu)
                    st, r = self.goi("POST", f"/api/trich_xuat/{lu}/danh_muc{duoi}")
                    self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_BAT_BIEN"), (lu, duoi, r))
                    self.assertEqual(anh(du_lieu), truoc, (lu, duoi))
        self.assertEqual(cham, [])
        # FIX05: đối chứng legacy = kiểm ROUTE + FORWARDING (lượt không phải common, danh sách rỗng) bằng writer SPY sở hữu bởi test, template/đầu
        # ra DEMO trong TMP. KHÔNG gọi writer workbook thật (không đọc MAU_DANH_MUC_HD nguồn, không os.replace) → full workbook I/O = NOT_RUN ở ca
        # này; đây KHÔNG phải bằng chứng round-trip workbook.
        demo = Path(os.environ["HD_DU_LIEU"]) / "demo_c22"
        demo.mkdir(exist_ok=True)
        demo_mau, demo_out = demo / "MAU_DEMO.xlsx", demo / "DANH_MUC_DEMO.xlsx"
        goi_spy = []

        def spy(ds, out_path, mau_path):
            goi_spy.append((list(ds), out_path, mau_path))
            return out_path, 0, 0
        lu_leg = self.luot()                                             # đối chứng legacy: không phải common, danh sách rỗng
        truoc = anh(du_lieu)
        with patch.object(dv, "ghi_danh_muc", spy), patch.object(dv.ch, "file_danh_muc_hd", lambda: demo_out), \
                patch.object(dv.ch, "MAU_DANH_MUC_HD", demo_mau):
            st, r = self.goi("POST", f"/api/trich_xuat/{lu_leg}/danh_muc")
        self.assertEqual((st, r), (200, {"ok": True, "moi": 0, "cap_nhat": 0, "tai": dv.duong_dan_tai(str(demo_out))}), r)
        self.assertEqual(goi_spy, [([], str(demo_out), str(demo_mau))])  # đúng MỘT lần, đúng tham số chuyển tiếp
        self.assertEqual(anh(du_lieu), truoc)                            # spy không ghi; route không tạo tệp khác

    def test_c23_preflight_common_chi_doc(self):
        """R5 — GET /api/trich_xuat/common: typed common/v1, RULE_ONLY, XD đúng catalog đã ghim, sẵn sàng tính từ catalog/implementation thật; chỉ
        đọc (ảnh dữ liệu không đổi), không chạm cấu hình/AI (sentinel). Catalog đã ghim không có → chưa sẵn sàng có lý do (không 'luôn sẵn sàng')."""
        du_lieu = Path(os.environ["HD_DU_LIEU"])
        truoc = anh(du_lieu)
        st, v = self.goi("GET", "/api/trich_xuat/common")
        self.assertEqual(st, 200, v)
        self.assertEqual((v["kieu"], v["contract"], v["modes"], v["san_sang"]), ("nang_luc_common/v1", CONTRACT, ["RULE_ONLY"], True), v)
        self.assertEqual((v["loai"]["XD"]["catalog_id"], v["loai"]["XD"]["catalog_sha256"], v["loai"]["XD"]["san_sang"]), ("XD", CAT_SHA, True))
        self.assertEqual(len(v["implementation_sha256"]), 64)
        self.assertEqual(v["implementation_thieu"], [])
        self.assertTrue({"luot", "lap_lai", "request_id"} <= set(v["create_ack"]))
        self.assertEqual(anh(du_lieu), truoc)
        with patch.dict(danh_muc.CATALOG_COMMON["XD"], {"path": os.path.join(TMP, "khong_co_DANH_MUC.xlsx")}):
            st, v = self.goi("GET", "/api/trich_xuat/common")
        self.assertEqual((st, v["san_sang"], v["loai"]["XD"]["san_sang"], v["loai"]["XD"]["ly_do"]), (200, False, False, "CATALOG_THIEU"), v)
        self.assertEqual(anh(du_lieu), truoc)
        # ACK create đúng DTO mà client kiểm: request_id = ID logic, lap_lai bool, luot hợp lệ
        b = self.body(request_id="m4:ack-" + os.urandom(3).hex())
        st, r = self.tao_common(b)
        self.assertEqual((st, r["request_id"], type(r["lap_lai"]) is bool), (200, b["request_id"], True), r)

    def test_c23b_dat_luot_request_id_sai_dinh_dang(self):
        """CRM-41-01-06 — bản ghi đặt lượt JSON hợp lệ, đủ trường nhưng request_id rỗng / sai định dạng → không coi là ý định khác hợp lệ: create
        mới 409 COMMON_CHUA_RO có tên tệp, không cấp lượt/registry/link, ảnh không đổi. Positive trước; sau ca, bản ghi được ghi đè (đã sao lưu
        CreateNew) thành ý định khác HỢP LỆ để không ảnh hưởng ca sau — không xóa."""
        out = Path(os.environ["HD_OUT_DIR"])
        st, r = self.tao_common(self.body())
        self.assertEqual((st, r["lap_lai"]), (200, False), r)
        for nhan, rid in (("rong", ""), ("dinh_dang", "có dấu cách")):
            slot = out / "_common_dat_luot" / ("20000104_00000" + str(len(nhan) % 10) + ".json")
            self.assertFalse(slot.exists())
            with open(slot, "xb") as f:
                f.write(self.canon({"kieu": "dat_luot_common/v1", "luot": slot.stem, "request_id": rid, "body_sha256": "0" * 64}))
            truoc = anh(out)
            st, r = self.tao_common(self.body())
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), (nhan, r))
            self.assertIn(slot.name, r["chi_tiet"]["ly_do"])
            self.assertEqual(anh(out), truoc, nhan)
            self.ghi_de(slot, self.canon({"kieu": "dat_luot_common/v1", "luot": slot.stem, "request_id": "test:khoi-phuc-" + nhan,
                                          "body_sha256": "0" * 64}), "c23b_" + nhan)
            st, r = self.tao_common(self.body())
            self.assertEqual(st, 200, (nhan, r))

    # ------------------------------------------------------------------ FIX05
    def test_c24_dat_luot_ghi_do_la_unknown(self):
        """R4 — dừng GIỮA lúc ghi bản ghi đặt lượt (bytes dở, CreateNew) trước registry → thử lại cùng ý định: 409 COMMON_CHUA_RO có lý do, KHÔNG
        tạo registry/link/bản ghi đặt lượt/lượt khác, không compute; ảnh mọi path/hash/bytes không đổi. Bản ghi dở KHÔNG bị xóa/ghi đè.
        (Positive dừng SAU bản ghi đặt lượt hoàn chỉnh: c19.) Đặt CUỐI theo thứ tự tên: bản ghi dở được giữ nên create MỚI cũng UNKNOWN (fail closed)."""
        out = Path(os.environ["HD_OUT_DIR"])
        b = self.body()
        goc_ghi = dv._ghi_moi
        ghi_do = []

        def dung_giua_dat_luot(p, data):
            if Path(p).parent.name == "_common_dat_luot":
                goc_ghi(p, data[: len(data) // 2])                      # CreateNew, chỉ nửa bytes (ghi dở)
                ghi_do.append(Path(p))
                raise OSError("giả lập dừng giữa ghi bản ghi đặt lượt")
            return goc_ghi(p, data)
        with patch.object(dv, "_ghi_moi", dung_giua_dat_luot):
            st, r = self.tao_common(b)
        self.assertEqual(st, 500, r)
        self.assertEqual(len(ghi_do), 1)
        b_do = ghi_do[0].read_bytes()
        with self.assertRaises(ValueError):
            json.loads(b_do.decode("utf-8", "replace"))                 # thực sự ghi dở
        self.assertFalse(self.reg_cua(b).exists())
        self.assertFalse((out / ghi_do[0].stem).exists())
        truoc, so_luot = anh(out), len(dv.LUOT)
        for _ in range(2):
            st, r = self.tao_common(b)
            self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
            self.assertIn(ghi_do[0].name, r["chi_tiet"]["ly_do"])
            self.assertEqual(anh(out), truoc)                            # không registry/link/bản ghi đặt lượt/lượt mới
            self.assertEqual(len(dv.LUOT), so_luot)
        self.assertEqual(ghi_do[0].read_bytes(), b_do)                   # không xóa/ghi đè bản ghi cũ
        st, r = self.tao_common(self.body())                             # ý định khác: cũng UNKNOWN (không rõ bản ghi dở thuộc ai)
        self.assertEqual((st, r["chi_tiet"]["ma"]), (409, "COMMON_CHUA_RO"), r)
        self.assertEqual(anh(out), truoc)

    def test_c07_nhanh_cu_khong_doi(self):
        st, r = self.goi("POST", "/api/trich_xuat", {})
        lu = r["luot"]
        st, r = self.goi("POST", f"/api/trich_xuat/{lu}/chay", {"tham_so": []})  # API cũ: không contract → không đi nhánh common
        self.assertEqual(st, 400)
        self.assertIn("Chưa có hợp đồng", r["loi"])
        self.assertIsNone(r.get("chi_tiet"))


if __name__ == "__main__":
    unittest.main()
