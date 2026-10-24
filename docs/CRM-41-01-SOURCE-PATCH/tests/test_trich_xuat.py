# -*- coding: utf-8 -*-
"""
Kiểm thử phần mềm trích xuất v3 + máy chủ API — KHÔNG cần GPU, KHÔNG gửi gì ra ngoài (AI & cloud đều giả lập).
    python -m unittest discover -s tests -v
Hợp đồng thật (du_lieu_mau\\HD_2903.docx, HD_0404.doc + DAP_AN_*.tsv — không có trên Git) → test tự bỏ qua nếu thiếu.
"""
import json
import os
import random
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "tests"))
TMP = tempfile.mkdtemp(prefix="test_trich_xuat_")
os.environ.update(HD_DU_LIEU=os.path.join(TMP, "du_lieu"), HD_CSDL=os.path.join(TMP, "du_lieu", "hop_dong.db"),
                  HD_THU_MUC_KHOA=os.path.join(TMP, "khoa"))
for k in ("OLLAMA_URL", "AI_MODEL", "HD_RA_LAI", "HD_CLOUD", "HD_OUT_DIR", "HD_DANH_MUC_HD", "ANTHROPIC_API_KEY",
          "OPENAI_API_KEY"):
    os.environ.pop(k, None)

import mau_gia_lap  # noqa: E402
import mock_cloud  # noqa: E402
import mock_ollama  # noqa: E402
from trich_xuat import cau_hinh as ch  # noqa: E402

ch.FILE_CAU_HINH = Path(TMP) / "cau_hinh_may_ai.json"       # KHÔNG đụng cấu hình thật của máy
ch.THU_MUC_KHOA = Path(TMP) / "khoa"
ch.FILE_KHOA = ch.THU_MUC_KHOA / "khoa_api.json"

from trich_xuat.ai_local import AILoi, DaDung, MayAI  # noqa: E402
from trich_xuat.cloud import AnDanh, chon_o  # noqa: E402
from trich_xuat.danh_muc import load_params, read_catalog  # noqa: E402
from trich_xuat.doc_hop_dong import read_contract  # noqa: E402
from trich_xuat.kiem_tra import check, la_ok, loose, norm, so_chuan  # noqa: E402
from trich_xuat.lo import LuotChay  # noqa: E402
from trich_xuat.logic import kiem_tra_logic  # noqa: E402
from trich_xuat.xlsx_mini import read_xlsx  # noqa: E402

MAU = GOC / "du_lieu_mau"
CO_MAU_THAT = (MAU / "HD_2903.docx").exists() and (MAU / "DAP_AN_HD_2903.tsv").exists()
PARAMS = load_params()


def _doc(p, mode="rb"):
    with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def _thu_muc(ten):
    d = os.path.join(TMP, ten + "_" + str(time.time_ns()))
    os.makedirs(d)
    return d


class TestDocBoq(unittest.TestCase):
    def test_cong_tron_khong_phai_dong_cong(self):
        """'CỐNG TRÒN' (bỏ dấu = 'cong') không được hiểu là dòng 'CỘNG'; tổng phụ giữa bảng bỏ qua; KL trống + TT 0 = 0."""
        import openpyxl
        from may_chu import nghiep_vu as nv
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOQ"
        ws.append(["STT", "Tên công tác", "Đơn vị", "Khối lượng", "Đơn giá", "Thành tiền"])
        ws.append(["A", "HẠNG MỤC: THOÁT NƯỚC", None, None, None, None])
        ws.append([1, "Đào móng", "m3", 10, 1000, 10000])
        ws.append([None, "CỐNG TRÒN BTCT", None, None, 0, None])
        ws.append([2, "Lắp đặt ống cống D600", "đoạn ống", 5, 2000, 10000])
        ws.append([3, "Thử áp lực đường ống", "100m", None, 1500, 0])
        ws.append([None, "Cộng hạng mục A", None, None, None, 20000])
        ws.append(["B", "HẠNG MỤC: ĐƯỜNG", None, None, None, None])
        ws.append([1, "Đắp đất", "m3", 2, 3000, 6000])
        ws.append([None, "CỘNG (Chưa VAT)", None, None, None, 26000])
        ws.append([None, "Thuế VAT (8%)", None, None, None, 2080])
        ws.append([9, "Dòng sau bảng tổng không được đọc", "m3", 1, 1, 1])
        p = os.path.join(_thu_muc("boq_cong"), "boq.xlsx")
        wb.save(p)
        cot = {"stt": "A", "ten": "B", "dvt": "C", "kl": "D", "don_gia": "E", "thanh_tien": "F"}
        items, loi = nv.boq_doc_dong(p, "BOQ", 1, cot)
        self.assertEqual(loi, [])
        self.assertEqual([i["ten"] for i in items], ["Đào móng", "Lắp đặt ống cống D600", "Thử áp lực đường ống", "Đắp đất"])
        self.assertEqual(items[1]["nhom"], "HẠNG MỤC: THOÁT NƯỚC / CỐNG TRÒN BTCT")
        self.assertEqual(items[2]["kl"], 0.0)
        self.assertEqual(sum(round(i["kl"] * i["don_gia"]) for i in items), 26000)


class TestDanhMuc(unittest.TestCase):
    def test_37_tham_so_co_muc(self):
        self.assertEqual(len(PARAMS), 37)
        by = {p["ma"]: p for p in PARAMS}
        self.assertEqual(by["TC-09"]["muc"], 0)
        self.assertEqual(by["TT-02"]["muc"], 3)
        self.assertEqual(by["TT-62"]["muc"], 1)
        self.assertIn("chất lượng", by["TT-51"]["bat_buoc"])
        self.assertIn("chậm thanh toán", by["TT-54"]["loai_tru"])
        self.assertIn("Không quy định", by["TT-55"]["mo_ta"])

    def test_doc_danh_muc_cu_6_cot(self):
        from trich_xuat.xlsx_mini import write_xlsx
        p = os.path.join(_thu_muc("dm"), "cu.xlsx")
        write_xlsx(p, {"Danh_muc": {"rows": [["Mã", "Nhóm", "Mô tả cho AI", "Từ khoá tiêu đề", "Từ khoá nội dung",
                                              "Dùng (Có/Không)"],
                                             ["TT-02", "Giá", "Giá trị HĐ", "giá", "", "Có"],
                                             ["TT-99", "Khác", "Thử", "", "", "Không"]]}})
        rows = read_catalog(p)
        self.assertEqual(rows[0]["muc"], 3)              # lấy mức mặc định theo mã
        ps = load_params(p, them=["Bảo hiểm | Loại bảo hiểm công trình"])
        self.assertEqual([x["ma"] for x in ps], ["TT-02", "Y-01"])


class TestDocHopDong(unittest.TestCase):
    def test_track_changes_accept_all(self):
        d = _thu_muc("tc")
        ins = '<w:p><w:ins w:id="1" w:author="a"><w:r><w:t>Giá trị hợp đồng là 9.000 đồng.</w:t></w:r></w:ins></w:p>'
        dele = ('<w:p><w:r><w:t xml:space="preserve">Tạm ứng </w:t></w:r><w:del w:id="2" w:author="a"><w:r>'
                '<w:delText>30%</w:delText></w:r></w:del><w:ins w:id="3" w:author="a"><w:r><w:t>15%</w:t></w:r></w:ins>'
                '<w:r><w:t xml:space="preserve"> giá trị.</w:t></w:r></w:p>')
        gop = ('<w:p><w:pPr><w:rPr><w:del w:id="4" w:author="a"/></w:rPr></w:pPr><w:r><w:t xml:space="preserve">'
               'Phần đầu </w:t></w:r></w:p><w:p><w:r><w:t>phần sau.</w:t></w:r></w:p>')
        hang_xoa = ('<w:tbl><w:tr><w:trPr><w:del w:id="5" w:author="a"/></w:trPr><w:tc><w:p><w:r><w:t>DÒNG ĐÃ XOÁ</w:t>'
                    '</w:r></w:p></w:tc></w:tr><w:tr><w:tc><w:p><w:r><w:t>DÒNG CÒN</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
        p = mau_gia_lap.tao_docx(os.path.join(d, "tc.docx"),
                                 ["Mở đầu", "Điều 1. Giá", ins, "Điều 2. Tạm ứng", dele, gop, hang_xoa])
        goc = _doc(p)
        info = read_contract(p)
        self.assertIn("Giá trị hợp đồng là 9.000 đồng.", info["text"])
        self.assertIn("Tạm ứng 15% giá trị.", info["text"])
        self.assertNotIn("30%", info["text"])
        self.assertIn("Phần đầu phần sau.", info["text"])
        self.assertNotIn("DÒNG ĐÃ XOÁ", info["text"])
        self.assertIn("DÒNG CÒN", info["text"])
        self.assertGreater(info["report"]["track_changes_accepted"], 0)
        self.assertTrue(any("Accept All" in w for w in info["report"]["warnings"]))
        self.assertEqual(_doc(p), goc)        # file gốc không đổi

    def test_hop_dong_gia_lap(self):
        docx, _ = mau_gia_lap.tao_hop_dong(_thu_muc("gl"))
        info = read_contract(docx)
        self.assertEqual(info["report"]["articles"], 8)


class TestKiemTra(unittest.TestCase):
    full = norm("Giá trị hợp đồng là 7.915.563.292 đồng. Bên nhận thầu: Công ty TNHH Xây dựng Thử Nghiệm.")

    def test_so_chuan(self):
        self.assertEqual(so_chuan("7.915.563.292"), "7915563292")
        self.assertEqual(so_chuan("0,15"), "0.15")

    def test_check(self):
        it = {"gia_tri": "7.915.563.292", "trich_dan": "Giá trị hợp đồng là 7.915.563.292 đồng."}
        self.assertEqual(check(it, self.full), "OK")
        it2 = {"gia_tri": "7.915.563.293", "trich_dan": "Giá trị hợp đồng là 7.915.563.292 đồng."}
        self.assertTrue(check(it2, self.full).startswith("KIỂM TRA: số liệu"))

    def test_gia_tri_nguyen_van(self):
        it = {"gia_tri": "Công ty TNHH Xây dựng Thử Nghiệm", "trich_dan": "câu không có"}
        self.assertEqual(check(it, self.full), "OK (giá trị có nguyên văn trong HĐ)")
        it2 = {"gia_tri": "Không áp dụng", "trich_dan": "câu không có"}
        self.assertFalse(la_ok(check(it2, self.full)))


def _kq(**kw):
    return {ma: {"gia_tri": v[0], "trich_dan": v[1]} for ma, v in kw.items()}


class TestLogic(unittest.TestCase):
    def test_l1(self):
        lg = kiem_tra_logic(_kq(**{"TT-10": ("Không áp dụng", "Tạm ứng 15% giá trị hợp đồng")}), PARAMS)
        self.assertTrue(lg["TT-10"][0].startswith("L1"))
        lg = kiem_tra_logic(_kq(**{"TT-10": ("Không áp dụng", "Điều 6. Tạm ứng: không áp dụng")}), PARAMS)
        self.assertNotIn("TT-10", lg)

    def test_l2(self):
        lg = kiem_tra_logic(_kq(**{"TT-20": ("90", "thanh toán 90%"), "TT-21": ("5", "giữ lại 5%")}), PARAMS)
        self.assertTrue(any(x.startswith("L2") for x in lg["TT-20"]))
        lg = kiem_tra_logic(_kq(**{"TT-20": ("90", "thanh toán 90%"), "TT-21": ("10", "giữ lại 10%")}), PARAMS)
        self.assertNotIn("TT-20", lg)

    def test_l3(self):
        lg = kiem_tra_logic(_kq(**{"TT-20": ("Giai đoạn 1: 80%; Giai đoạn 2: 90%", "thanh toán 80% ... 90%"),
                                   "TT-21": ("20", "giữ lại")}), PARAMS)
        self.assertTrue(any(x.startswith("L3") for x in lg["TT-20"]))
        self.assertFalse(any(x.startswith("L2") for x in lg.get("TT-20", [])))

    def test_l4(self):
        lg = kiem_tra_logic(_kq(**{"TT-54": ("0,05%/ngày", "Bên A chậm thanh toán thì chịu lãi 0,05%/ngày")}), PARAMS)
        self.assertTrue(any(x.startswith("L4") for x in lg["TT-54"]))
        lg = kiem_tra_logic(_kq(**{"TT-51": ("12%", "Phạt chậm tiến độ tối đa 12%")}), PARAMS)
        self.assertTrue(any("thiếu từ khoá" in x for x in lg["TT-51"]))

    def test_l5(self):
        q = "tạm giữ 0,1%/ngày trong 07 ngày đầu và 0,2%/ngày từ ngày thứ 08"
        lg = kiem_tra_logic(_kq(**{"TT-52": ("0,1%/ngày", q), "TT-53": ("Không quy định", "")}), PARAMS)
        self.assertTrue(any(x.startswith("L5") for x in lg["TT-53"]))
        lg = kiem_tra_logic(_kq(**{"TT-52": ("0,1", q), "TT-53": ("0,2", q)}), PARAMS)
        self.assertNotIn("TT-53", lg)


class TestAnDanh(unittest.TestCase):
    def test_che_va_mo(self):
        an = AnDanh({"BEN_A": ["Công ty Cổ phần Mẫu An"], "SO_HD": ["15/2026/HĐXD/MA-TN"]})
        t = ("Hợp đồng số 15/2026/HĐXD/MA-TN giữa Công ty Cổ phần Mẫu An và CÔNG TY TNHH XÂY DỰNG HOÀNG LONG; "
             "MST: 0101234567; điện thoại 0912 345 678; Ông Nguyễn Văn Thử; giá trị 7.915.563.292 đồng; 0,15%/ngày.")
        m = an.che(t)
        for x in ("Mẫu An", "0101234567", "0912", "HOÀNG LONG", "Nguyễn Văn", "15/2026"):
            self.assertNotIn(x, m)
        self.assertIn("7.915.563.292", m)        # giữ số tiền
        self.assertIn("0,15%/ngày", m)
        self.assertEqual(an.dau_vet(m), [])
        self.assertEqual(an.mo(m), t)

    def test_chon_o_luon_hoi(self):
        bang = [{"ma": "TT-11", "nhom": "Tạm ứng", "muc": 3, "kiem_tra": "OK"},
                {"ma": "TT-62", "nhom": "Hồ sơ", "muc": 1, "kiem_tra": "OK"},
                {"ma": "TC-03", "nhom": "Thông tin chung", "muc": 0, "kiem_tra": "OK"}]
        kq = chon_o(bang, 0, random.Random(1), luon={"TT-11", "TT-62", "TC-03"})
        self.assertEqual([m for m, _ in kq], ["TT-11", "TT-62"])     # TC không bao giờ gửi
        self.assertIn("luôn hỏi", kq[0][1])

    def test_chon_o(self):
        bang = [{"ma": "TC-01", "nhom": "Thông tin chung", "muc": 0, "kiem_tra": "KIỂM TRA: x"},
                {"ma": "TT-02", "nhom": "Giá", "muc": 3, "kiem_tra": "KIỂM TRA: x"},
                {"ma": "TT-62", "nhom": "Hồ sơ", "muc": 1, "kiem_tra": "KIỂM TRA: x"},
                {"ma": "TT-04", "nhom": "Giá", "muc": 3, "kiem_tra": "OK"},
                {"ma": "TT-01", "nhom": "Giá", "muc": 2, "kiem_tra": "OK"}]
        self.assertEqual([m for m, _ in chon_o(bang, 0)], ["TT-02"])
        self.assertEqual([m for m, _ in chon_o(bang, 100, random.Random(1))], ["TT-02", "TT-04"])
        self.assertEqual([m for m, _ in chon_o(bang, 200, random.Random(1))], ["TT-02", "TT-04", "TT-01"])


class TestMayAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = _thu_muc("ai")
        _, cls.tsv = mau_gia_lap.tao_hop_dong(d)
        cls.srv, cls.port = mock_ollama.start([cls.tsv], model="gemma3:12b")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def ai(self, **kw):
        return MayAI(f"http://127.0.0.1:{self.port}", "gemma3:12b", retry_waits=(0.1, 0.1), **kw)

    def test_think_500_hoi_lai(self):
        self.srv.ctl["think_500"] = True
        try:
            ai = self.ai()
            items, _, _ = ai.hoi_trich("- TT-02 | Giá trị\n")
            self.assertTrue(ai.khong_think)
            self.assertEqual(items[0]["ma"], "TT-02")
        finally:
            self.srv.ctl["think_500"] = False

    def test_loi_mang_thu_lai(self):
        self.srv.ctl["loi_mang"] = 2
        items, _, _ = self.ai().hoi_trich("- TT-02 | Giá trị\n")
        self.assertEqual(len(items), 1)
        self.srv.ctl["loi_mang"] = 5
        with self.assertRaises(AILoi):
            self.ai().hoi_trich("- TT-02 | Giá trị\n")
        self.srv.ctl["loi_mang"] = 0

    def test_json_hong_hoi_lai(self):
        self.srv.ctl["json_hong"] = 1
        items, _, _ = self.ai().hoi_trich("- TT-02 | Giá trị\n")
        self.assertEqual(len(items), 1)
        self.assertIn("CHỈ TRẢ VỀ JSON", self.srv.prompts[-1])

    def test_prompt_bi_cat(self):
        self.srv.ctl["ctx_day"] = True
        try:
            with self.assertRaises(AILoi) as cm:
                self.ai().hoi_trich("- TT-02 | Giá trị\n")
            self.assertIn("cắt", str(cm.exception))
        finally:
            self.srv.ctl["ctx_day"] = False

    def test_dung(self):
        ev = threading.Event()
        self.srv.ctl["cham"] = 3
        try:
            threading.Timer(0.3, ev.set).start()
            t = time.time()
            with self.assertRaises(DaDung):
                self.ai(dung=ev).hoi_trich("- TT-02 | Giá trị\n")
            self.assertLess(time.time() - t, 2)
        finally:
            self.srv.ctl["cham"] = 0


def _chay_luot(files, **kw):
    out = _thu_muc("luot")
    srv, port = mock_ollama.start(kw.pop("dap_an"), model="qwen3:8b")
    try:
        lc = LuotChay(files, out, PARAMS, f"http://127.0.0.1:{port}", "qwen3:8b", **kw)
        ds = lc.chay()
        return lc, ds, srv
    finally:
        srv.shutdown()


class TestLuongGiaLap(unittest.TestCase):
    def test_toan_luong(self):
        d = _thu_muc("gl")
        docx, tsv = mau_gia_lap.tao_hop_dong(d)
        lc, ds, srv = _chay_luot([docx], dap_an=[tsv], thu_muc_dap_an=d, chay_lai=True)
        s = lc.trang_thai()
        self.assertEqual(s["tt"], "xong", s["thong_bao"])
        kq = ds[0]
        self.assertEqual(kq["tom_tat"]["so_tham_so"], 37)
        self.assertEqual(kq["tom_tat"]["dung_dap_an"], "37/37")
        vang = [d["ma"] for d in kq["bang"] if not la_ok(d["kiem_tra"])]
        self.assertEqual(vang, [], [(d["ma"], d["kiem_tra"]) for d in kq["bang"] if not la_ok(d["kiem_tra"])])
        out = os.path.join(lc.out_dir, kq["ten"])
        rows = read_xlsx(os.path.join(out, kq["tep"]["excel"]))
        self.assertEqual(rows[0][:3], ["Mã", "Nhóm", "Tham số"])
        self.assertIn("Nguồn", rows[0])
        self.assertTrue(os.path.exists(os.path.join(lc.out_dir, s["tep"]["tong_hop_xlsx"])))
        nk = _doc(os.path.join(lc.out_dir, s["tep"]["nhat_ky"]), "r")
        self.assertNotIn("5.000.000.000", nk)         # nhật ký không chứa nội dung HĐ
        # danh mục HĐ đọc được bằng csdl_hop_dong.nap_danh_muc
        import csdl_hop_dong as cs
        con = cs.mo_csdl(os.path.join(TMP, f"dm_{time.time_ns()}.db"))
        r = cs.nap_danh_muc(con, s["danh_muc"])
        so = [x[0] for x in r]
        self.assertIn("15/2026/HĐXD/MA-TN", so)
        ma = [x[1] for x in r if x[0] == "15/2026/HĐXD/MA-TN"][0]
        hd = con.execute("SELECT * FROM hop_dong WHERE ma_hd = ?", (ma,)).fetchone()
        self.assertEqual(hd["phan_loai"], "Thi công xây dựng")
        self.assertEqual(hd["gia_tri_hd"], 5000000000)

    def test_dung_lai_ket_qua_cu(self):
        d = _thu_muc("gl2")
        docx, tsv = mau_gia_lap.tao_hop_dong(d)
        _chay_luot([docx], dap_an=[tsv], thu_muc_dap_an=d)
        lc, ds, srv = _chay_luot([docx], dap_an=[tsv], thu_muc_dap_an=d)
        self.assertEqual(srv.calls["http"], 0)
        self.assertTrue(ds[0].get("bo_qua"))
        self.assertTrue(lc.trang_thai()["hd"][0]["tt"].startswith("Bỏ qua"))

    def test_khong_co_ai(self):
        d = _thu_muc("gl3")
        docx, _ = mau_gia_lap.tao_hop_dong(d)
        lc = LuotChay([docx], _thu_muc("luot"), PARAMS, "http://127.0.0.1:9", "qwen3:8b", chay_lai=True)  # không dùng lại kết quả cũ
        lc.chay()
        self.assertEqual(lc.trang_thai()["tt"], "loi")
        self.assertIn("Không kết nối được máy AI", lc.trang_thai()["thong_bao"])
        lc = LuotChay([docx], _thu_muc("luot"), PARAMS, "http://127.0.0.1:9", "qwen3:8b", chi_cau_truc=True)
        ds = lc.chay()
        self.assertEqual(ds[0]["che_do"], "chua_chay_AI")
        self.assertTrue(ds[0]["doan_lien_quan"])

    def test_ra_lai_sua_trich_dan_sai(self):
        d = _thu_muc("gl4")
        docx, tsv = mau_gia_lap.tao_hop_dong(d)
        srv, port = mock_ollama.start([tsv], model="qwen3:8b")
        srv.ctl["sai_lan_dau"] = {"TT-31"}
        try:
            lc = LuotChay([docx], _thu_muc("luot"), PARAMS, f"http://127.0.0.1:{port}", "qwen3:8b", chay_lai=True)
            ds = lc.chay()
        finally:
            srv.shutdown()
        d31 = [x for x in ds[0]["bang"] if x["ma"] == "TT-31"][0]
        self.assertTrue(la_ok(d31["kiem_tra"]), d31["kiem_tra"])
        self.assertIn("rà lại", d31["ghi_chu"])


class TestOcrTieuDe(unittest.TestCase):
    def test_bang_ocr_sai_chu_tieu_de(self):
        """Tiêu đề cột bị OCR đọc sai ('Nội duug', 'Đơn qia', 'VÁT') vẫn nhận ra bảng KL / đơn giá của phụ lục."""
        from master_hd import bo_dau_tieu_de
        from may_chu import phu_luc_ai as pa
        self.assertEqual(bo_dau_tieu_de("Nội duug công việc"), "noi dung cong viec")
        self.assertEqual(bo_dau_tieu_de("Đơn qia (chưa VÁT)"), "don gia (chua vat)")
        self.assertEqual(bo_dau_tieu_de("Lot No"), "lot no")                  # từ tiếng Anh giữ nguyên
        bang = [[["TT", "Nội duug công việc", "Đơn vị", "Khối luợng", "Đơn qia (chưa VÁT)", "Thành tiến"],
                 ["1", "Đào đất nền", "100m2", "1.250,500", "500.000", "625.250.000"],
                 ["", "Tổng cộng", "", "", "", "625.250.000"]],
                [["STT", "Nội duug công việc", "Đơn giá cũ (VNĐ)", "Đơn qia mới (VNĐ)", "Ghi chú"],
                 ["1", "Đào đất nền", "500.000", "650.000", "chưa VÁT"]]]
        b = pa.doc_bang(bang[:1])
        self.assertEqual([(i["ten"], i["kl"], i["don_gia"]) for i in b["items"]], [("Đào đất nền", 1250.5, 500000.0)])
        b2 = pa.doc_bang(bang[1:])
        self.assertEqual((b2["loai"], b2["items"][0]["dg_cu"], b2["items"][0]["don_gia"]), ("doi_chieu", 500000.0, 650000.0))


class TestNguonClaude(unittest.TestCase):
    """Nguồn AI = Claude (khi máy Local AI không bật): che định danh, không gửi Phần mở đầu / TC, mở che kết quả."""
    def setUp(self):
        self.d = _thu_muc("nguon_claude")
        self.docx, self.tsv = mau_gia_lap.tao_hop_dong(self.d)
        self.srv, port = mock_ollama.start([self.tsv], model="qwen3:8b")
        os.environ["HD_CLOUD_URL_ANTHROPIC"] = f"http://127.0.0.1:{port}/v1/messages"
        ch.luu_khoa("anthropic", "sk-ant-THU-NGHIEM-1234")

    def tearDown(self):
        self.srv.shutdown()
        os.environ.pop("HD_CLOUD_URL_ANTHROPIC", None)

    def test_trich_hop_dong(self):
        out = _thu_muc("luot_claude")
        lc = LuotChay([self.docx], out, PARAMS, "http://127.0.0.1:1", "", chay_lai=True, ra_lai=True,
                      nguon_ai={"nha_cung_cap": "anthropic", "model": "claude-sonnet-5"})
        ds = lc.chay()
        self.assertEqual(lc.trang_thai()["tt"], "xong", lc.trang_thai()["thong_bao"])
        kq = ds[0]
        by = {x["ma"]: x for x in kq["bang"]}
        self.assertEqual(kq["tuy_chon"]["nguon_ai"], "Claude (che định danh)")
        self.assertFalse(kq["tuy_chon"]["ra_lai"])                         # không rà lại toàn HĐ khi dùng Claude
        self.assertEqual(by["TC-01"]["nguon"], "Quy tắc")                  # thông tin chung: quy tắc, không gửi
        self.assertTrue(by["TC-01"]["gia_tri"])
        self.assertEqual(by["TT-20"]["nguon"], "Claude (che định danh)")
        self.assertTrue(la_ok(by["TT-20"]["kiem_tra"]), by["TT-20"])
        self.assertGreaterEqual(sum(1 for x in kq["bang"] if la_ok(x["kiem_tra"])), 25)
        gui = "\n".join(self.srv.prompts)
        self.assertTrue(gui)
        for bi_mat in ("Mẫu An", "Thử Nghiệm", "0101234567", "15/2026/HĐXD", "Phần mở đầu"):
            self.assertNotIn(bi_mat, gui)
        self.assertNotIn("- TC-", gui)
        nk = kq["tuy_chon"]["gui_ra_ngoai"]
        self.assertTrue(os.path.exists(nk))
        with open(nk, encoding="utf-8") as f:
            log = f.read()
        self.assertIn("đã được che định danh", log)
        self.assertNotIn("sk-ant-THU", log)

    def test_che_mo_va_khong_gui(self):
        from trich_xuat.ai_cloud import MayCloud
        from trich_xuat.ai_local import AILoi
        ai = MayCloud("anthropic", "claude-sonnet-5", nhat_ky=os.path.join(self.d, "GUI_RA_NGOAI_thu.txt"))
        ai.dat_dinh_danh({"BEN_B": ["Công ty Cổ phần Mẫu Bình"], "SO_HD": ["15/2026/HĐXD/MA-TN"]})
        self.srv.ctl["phu_luc"] = {"thay_doi": [{"ma": "TT-50", "gia_tri_moi": "240 ngày", "dieu": "Điều 2",
                                                 "trich_dan": "[BEN_B] hoàn thành trong 240 ngày", "ghi_chu": ""}],
                                   "khac": []}
        data, tin, tout = ai.chat_json("PHỤ LỤC HỢP ĐỒNG CẦN PHÂN TÍCH: Công ty Cổ phần Mẫu Bình hoàn thành trong 240 "
                                       "ngày theo hợp đồng 15/2026/HĐXD/MA-TN.", {"type": "object"}, "thay_doi")
        gui = self.srv.prompts[-1]
        self.assertNotIn("Mẫu Bình", gui)
        self.assertNotIn("15/2026", gui)
        self.assertIn("[BEN_B]", gui)
        self.assertEqual(data["thay_doi"][0]["trich_dan"], "Công ty Cổ phần Mẫu Bình hoàn thành trong 240 ngày")  # mở che
        self.assertEqual((ai.so_lan_goi, tin > 0), (1, True))
        n = len(self.srv.prompts)                                         # còn sót định danh (tên lạ) → không gửi
        ai.an.dau_vet = lambda masked: ["CONG_TY: …"]
        with self.assertRaises(AILoi):
            ai.chat_json("PHỤ LỤC HỢP ĐỒNG CẦN PHÂN TÍCH: x", {"type": "object"}, "thay_doi")
        self.assertEqual(len(self.srv.prompts), n)

    def test_cai_dat_va_trang_thai(self):
        from may_chu import dich_vu as dv
        cu = ch.doc_cau_hinh(dung_env=False).get("nguon_ai", "local")
        try:
            dv.luu_cai_dat({"nguon_ai": "claude"})
            tt = dv.trang_thai_ai(lam_moi=True)
            self.assertEqual((tt["nguon"], tt["ket_noi"], tt["ip"]), ("claude", True, "Claude"))
            self.assertEqual(dv.lay_cai_dat()["nguon_ai"], "claude")
            with self.assertRaises(dv.LoiNguoiDung):
                dv.luu_cai_dat({"nguon_ai": "khac"})
        finally:
            dv.luu_cai_dat({"nguon_ai": cu})
            dv.trang_thai_ai(lam_moi=True)


class TestCloud(unittest.TestCase):
    def test_kiem_tra_cheo(self):
        d = _thu_muc("cl")
        docx, tsv = mau_gia_lap.tao_hop_dong(d)
        q20 = "Mỗi đợt thanh toán 90% giá trị khối lượng hoàn thành được nghiệm thu."
        q02 = "Giá trị hợp đồng là 5.000.000.000 đồng (đã bao gồm thuế VAT 8%)."
        csrv, cport = mock_cloud.start({"TT-20": ("90", q20), "TT-02": ("5.000.000.000", q02),
                                        "TT-10": ("15", "Bên A tạm ứng 15% giá trị hợp đồng sau khi ký."),
                                        "TT-04": ("8", q02)})
        os.environ["HD_CLOUD_URL_ANTHROPIC"] = f"http://127.0.0.1:{cport}/v1/messages"
        ch.luu_khoa("anthropic", "sk-ant-THU-NGHIEM-1234")
        osrv, oport = mock_ollama.start([tsv], model="qwen3:8b", wrong={"TT-20": "câu sai không có trong HĐ"})
        try:
            lc = LuotChay([docx], _thu_muc("luot"), PARAMS, f"http://127.0.0.1:{oport}", "qwen3:8b", chay_lai=True,
                          ra_lai=False, cloud={"nha_cung_cap": "anthropic", "model": "", "ty_le": 100})
            ds = lc.chay()
        finally:
            osrv.shutdown()
            csrv.shutdown()
            os.environ.pop("HD_CLOUD_URL_ANTHROPIC", None)
        kq = ds[0]
        by = {x["ma"]: x for x in kq["bang"]}
        self.assertEqual(by["TT-20"]["nguon"], "Local – cloud xác nhận")
        self.assertTrue(la_ok(by["TT-20"]["kiem_tra"]))
        self.assertEqual(by["TT-02"]["nguon"], "Local – cloud xác nhận")
        self.assertEqual(by["TC-01"]["nguon"], "Local")
        gui = "\n".join(b["messages"][-1]["content"] for _, b in csrv.requests)
        for bi_mat in ("Mẫu An", "Thử Nghiệm", "0101234567", "15/2026", "Phần mở đầu"):
            self.assertNotIn(bi_mat, gui)
        self.assertNotIn("- TC-", gui)
        self.assertIn("5.000.000.000", gui)
        nk = Path(lc.out_dir) / kq["ten"] / kq["tep"]["gui_ra_ngoai"]
        txt = nk.read_text(encoding="utf-8")
        self.assertNotIn("sk-ant-THU-NGHIEM-1234", txt)
        self.assertIn("ĐÃ GỬI", txt)
        self.assertEqual({k.lower(): v for k, v in csrv.requests[0][0].items()}.get("x-api-key"), "sk-ant-THU-NGHIEM-1234")

    def test_chu_to_hop_va_danh_gia_cloud(self):
        """HĐ có chữ tổ hợp (NFD, như file .doc cũ): trích dẫn dựng sẵn của AI vẫn khớp nguyên văn.
        Claude ghi giá trị kèm diễn giải nhưng câu trích đúng → xác nhận local; cùng 'không quy định' → tính riêng."""
        import unicodedata
        d = _thu_muc("cl_nfd")
        q20 = "Mỗi đợt thanh toán 90% giá trị khối lượng hoàn thành được nghiệm thu."
        cu = list(mau_gia_lap.DOAN)
        mau_gia_lap.DOAN[:] = [unicodedata.normalize("NFD", x) if x == q20 else x for x in cu]
        try:
            docx, tsv = mau_gia_lap.tao_hop_dong(d)
        finally:
            mau_gia_lap.DOAN[:] = cu
        info = read_contract(docx)
        self.assertIn(q20, info["text"])                                  # đã đưa về dạng dựng sẵn khi đọc
        self.assertEqual(check({"gia_tri": "90", "trich_dan": q20}, norm(unicodedata.normalize("NFD", q20))), "OK")
        csrv, cport = mock_cloud.start({"TT-20": ("90% giá trị khối lượng, tối đa 2 đợt mỗi tháng", q20)})
        os.environ["HD_CLOUD_URL_ANTHROPIC"] = f"http://127.0.0.1:{cport}/v1/messages"
        ch.luu_khoa("anthropic", "sk-ant-THU-NGHIEM-1234")
        osrv, oport = mock_ollama.start([tsv], model="qwen3:8b")
        try:
            lc = LuotChay([docx], _thu_muc("luot"), PARAMS, f"http://127.0.0.1:{oport}", "qwen3:8b", chay_lai=True,
                          ra_lai=False, cloud={"nha_cung_cap": "anthropic", "model": "claude-opus-5-5", "ty_le": 100})
            ds = lc.chay()
        finally:
            osrv.shutdown()
            csrv.shutdown()
            os.environ.pop("HD_CLOUD_URL_ANTHROPIC", None)
        kq = ds[0]
        by = {x["ma"]: x for x in kq["bang"]}
        self.assertTrue(la_ok(by["TT-20"]["kiem_tra"]), by["TT-20"]["kiem_tra"])          # local khớp dù HĐ là NFD
        self.assertEqual(by["TT-20"]["nguon"], "Local – cloud xác nhận (theo trích dẫn của Claude)")
        self.assertEqual(by["TT-20"]["cloud"]["model"], "claude-opus-5-5")
        cl = kq["tom_tat"]["cloud"]
        self.assertEqual(cl["model"], "claude-opus-5-5")
        # Claude trả "Không quy định" không kèm câu trích → KHÔNG được tính là xác nhận giá trị local
        sai = [x["ma"] for x in kq["bang"] if x["nguon"].startswith("Local – cloud xác nhận") and x["ma"] != "TT-20"]
        self.assertEqual(sai, [])

    def test_cung_khong_quy_dinh(self):
        from trich_xuat.cloud import kiem_tra_cloud
        row = {"id": "r1", "dieu": "9", "khoan": "9.1", "tieu_de_dieu": "Bảo hiểm", "tieu_de_khoan": "",
               "noi_dung": "Bên B tự mua bảo hiểm công trình.", "doan": None}
        bang = [{"ma": "TT-33", "nhom": "Quyết toán", "muc": 3, "gia_tri": "Không quy định", "trich_dan": "",
                 "kiem_tra": "KIỂM TRA: AI báo HĐ không quy định", "kiem_tra_tu": "KIỂM TRA: AI báo HĐ không quy định",
                 "nguon": "Local"}]
        csrv, cport = mock_cloud.start({})                       # Claude: "Không quy định"
        os.environ["HD_CLOUD_URL_ANTHROPIC"] = f"http://127.0.0.1:{cport}/v1/messages"
        ch.luu_khoa("anthropic", "sk-ant-THU-NGHIEM-1234")
        try:
            tom = kiem_tra_cloud(bang, [{"ma": "TT-33", "mo_ta": "Bảo lãnh thực hiện"}], {}, {"TT-33": [row]},
                                 {"r1": row}, norm(row["noi_dung"]), loose(row["noi_dung"]), _thu_muc("cl_k"),
                                 {"nha_cung_cap": "anthropic", "model": "", "ty_le": 100})
        finally:
            csrv.shutdown()
            os.environ.pop("HD_CLOUD_URL_ANTHROPIC", None)
        self.assertEqual((tom["cung_khong_quy_dinh"], tom["khong_xac_nhan"]), (1, 0))
        self.assertEqual(bang[0]["nguon"], "Local – cloud cùng: không quy định")
        self.assertFalse(la_ok(bang[0]["kiem_tra"]))            # vẫn để anh xem (không có câu để kiểm)

    def test_thu_ket_noi(self):
        from trich_xuat.cloud import thu_ket_noi
        csrv, cport = mock_cloud.start({})
        os.environ["HD_CLOUD_URL_ANTHROPIC"] = f"http://127.0.0.1:{cport}/v1/messages"
        ch.luu_khoa("anthropic", "sk-ant-THU-NGHIEM-1234")
        try:
            r = thu_ket_noi("anthropic", "claude-opus-5-5")
        finally:
            csrv.shutdown()
            os.environ.pop("HD_CLOUD_URL_ANTHROPIC", None)
        self.assertTrue(r["ok"], r)
        body = csrv.requests[0][1]
        self.assertNotIn("temperature", body)
        self.assertEqual(body["model"], "claude-opus-5-5")
        os.environ["HD_CLOUD_URL_ANTHROPIC"] = "http://127.0.0.1:9/v1/messages"
        try:
            r = thu_ket_noi("anthropic", "claude-opus-5-5", timeout=3)
        finally:
            os.environ.pop("HD_CLOUD_URL_ANTHROPIC", None)
        self.assertFalse(r["ok"])
        self.assertIn("Internet", r["loi"])

    def test_tham_so_kho_va_doan_ung_vien(self):
        d = _thu_muc("cl3")
        docx, tsv = mau_gia_lap.tao_hop_dong(d)
        q56 = "Tiền phạt được khấu trừ vào đợt thanh toán gần nhất."
        csrv, cport = mock_cloud.start({"TT-56": ("Khấu trừ vào đợt thanh toán gần nhất", q56)})
        os.environ["HD_CLOUD_URL_ANTHROPIC"] = f"http://127.0.0.1:{cport}/v1/messages"
        ch.luu_khoa("anthropic", "sk-ant-THU-NGHIEM-5678")
        osrv, oport = mock_ollama.start([tsv], model="qwen3:8b")
        osrv.ctl["sai_lan_dau"] = {"TT-56"}
        try:
            lc = LuotChay([docx], _thu_muc("luot"), PARAMS, f"http://127.0.0.1:{oport}", "qwen3:8b", chay_lai=True,
                          ra_lai=True, cloud={"nha_cung_cap": "anthropic", "model": "", "ty_le": 0})
            ds = lc.chay()
        finally:
            osrv.shutdown()
            csrv.shutdown()
            os.environ.pop("HD_CLOUD_URL_ANTHROPIC", None)
        kq = ds[0]
        gui = "\n".join(b["messages"][-1]["content"] for _, b in csrv.requests)
        self.assertIn("- TT-56 |", gui)                       # tham số khó: gửi dù local đã OK sau rà lại
        self.assertIn("Khoản 7.6", gui)                       # kèm đoạn ứng viên tìm được khi rà lại
        nk = (Path(lc.out_dir) / kq["ten"] / kq["tep"]["gui_ra_ngoai"]).read_text(encoding="utf-8")
        self.assertIn("luôn hỏi Claude", nk)
        d56 = [x for x in kq["bang"] if x["ma"] == "TT-56"][0]
        self.assertEqual(d56["nguon"], "Local – cloud xác nhận")

    def test_cloud_sua_gia_tri(self):
        d = _thu_muc("cl2")
        docx, tsv = mau_gia_lap.tao_hop_dong(d)
        q = "Bảo hành công trình bằng 5% giá trị hợp đồng."
        csrv, cport = mock_cloud.start({"TT-31": ("5", q)})
        os.environ["HD_CLOUD_URL_OPENAI"] = f"http://127.0.0.1:{cport}/v1/chat/completions"
        ch.luu_khoa("openai", "sk-openai-THU-1234")
        osrv, oport = mock_ollama.start([tsv], model="qwen3:8b", wrong={"TT-31": "câu sai"})
        try:
            lc = LuotChay([docx], _thu_muc("luot"), PARAMS, f"http://127.0.0.1:{oport}", "qwen3:8b", chay_lai=True,
                          ra_lai=False, cloud={"nha_cung_cap": "openai", "model": "gpt-x", "ty_le": 0})
            ds = lc.chay()
        finally:
            osrv.shutdown()
            csrv.shutdown()
            os.environ.pop("HD_CLOUD_URL_OPENAI", None)
        d31 = [x for x in ds[0]["bang"] if x["ma"] == "TT-31"][0]
        self.assertEqual(d31["nguon"], "Local – cloud xác nhận")      # cùng giá trị 5, trích dẫn cloud khớp HĐ
        self.assertEqual(d31["trich_dan"], q)
        self.assertEqual([m for _, b in csrv.requests for m in [b["model"]]], ["gpt-x"])


class TestPdf(unittest.TestCase):
    @unittest.skipUnless(shutil.which("soffice") and os.name != "nt", "cần LibreOffice để tạo PDF thử")
    def test_doc_pdf(self):
        import subprocess
        d = _thu_muc("pdf")
        docx, _ = mau_gia_lap.tao_hop_dong(d)
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", d, docx], check=True, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        info = read_contract(os.path.join(d, "HD_GIA_LAP.pdf"))
        self.assertEqual(info["report"]["articles"], 8)
        self.assertIn("5.000.000.000", info["text"])

    def test_pdf_scan_bao_loi(self):
        from trich_xuat.doc_hop_dong import read_pdf
        try:
            import pypdf  # noqa: F401
        except ImportError:
            self.skipTest("thiếu pypdf")
        w = pypdf.PdfWriter()
        for _ in range(3):
            w.add_blank_page(595, 842)
        p = os.path.join(_thu_muc("pdf2"), "scan.pdf")
        with open(p, "wb") as f:
            w.write(f)
        with self.assertRaises(ValueError) as cm:
            read_pdf(p)
        self.assertIn("scan", str(cm.exception))


# ------------------------------------------------------------------ OCR ABBYY (giả lập module cầu nối)
def _o(text, span=1):
    pr = f'<w:tcPr><w:gridSpan w:val="{span}"/></w:tcPr>' if span > 1 else ""
    return f"<w:tc>{pr}{mau_gia_lap.p(text)}</w:tc>"


def _tbl(rows):
    return "<w:tbl>" + "".join("<w:tr>" + "".join(_o(*c) if isinstance(c, tuple) else _o(c) for c in r) + "</w:tr>"
                               for r in rows) + "</w:tbl>"


TIEU_DE_BOQ = ["STT", "Tên công việc", "Đơn vị", "Khối lượng", "Đơn giá", "Thành tiền"]


def tao_boq_word(path, so_hd="15/2026/HĐXD/MA-TN"):
    """BOQ trong Word như ABBYY trả về: bảng ngắt sang trang 2 (lặp tiêu đề), số kiểu Việt Nam, ô gộp ngang."""
    return mau_gia_lap.tao_docx(path, [
        "BẢNG KHỐI LƯỢNG VÀ GIÁ TRỊ HỢP ĐỒNG", f"(Kèm theo hợp đồng số {so_hd})",
        _tbl([TIEU_DE_BOQ, ["A", ("PHẦN ĐƯỜNG", 5)], ["1", "Bê tông mặt đường", "m3", "100,00", "20.000.000", "2.000.000.000"]]),
        "Trang 2",
        _tbl([TIEU_DE_BOQ, ["2", "Hoàn thiện", "gói", "1", "2.629.629.630", "2.629.629.630"],
              ["", "Cộng", "", "", "", "4.629.629.630"]]),
    ])


class AbbyyGia(threading.Thread):
    """Giả lập task ABBYY Hot Folder: theo dõi in, xoá file gốc, ghi <tên>.pdf rồi <tên>.docx vào out (ghi tạm rồi đổi tên).
    loi=True: ghi dòng lỗi có mã file vào log thay vì kết quả."""
    def __init__(self, d_in, d_out, docx, tre=0.3, loi=False):
        super().__init__(daemon=True)
        self.d_in, self.d_out, self.docx, self.tre, self.loi = Path(d_in), Path(d_out), docx, tre, loi
        self.dung, self.da_lam = threading.Event(), []

    def run(self):
        while not self.dung.is_set():
            for f in sorted(self.d_in.glob("*.pdf")):
                time.sleep(self.tre)
                stem = f.stem
                f.unlink()
                if self.loi:
                    (self.d_out / "Hot Folder Log.txt").write_text(f"12:00 Error: cannot open {stem}.pdf\n", encoding="utf-16")
                    continue
                for duoi, data in (("pdf", b"%PDF-1.4 ket qua %%EOF"), ("docx", _doc(self.docx))):
                    tmp = self.d_out / f"~{stem}.tmp"
                    tmp.write_bytes(data)
                    os.replace(tmp, self.d_out / f"{stem}.{duoi}")
                self.da_lam.append(stem)
            time.sleep(0.05)

    def stop(self):
        self.dung.set()
        self.join(timeout=3)


def tao_phu_luc_word(path, so_hd="15/2026/HĐXD/MA-TN"):
    """Phụ lục giả lập (kiểu ABBYY trả về): đổi KL hạng mục 1 (tên có lỗi OCR), gia hạn tiến độ, BOQ toàn bộ sau PL."""
    return mau_gia_lap.tao_docx(path, [
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "PHỤ LỤC HỢP ĐÒNG SÓ 01",
        f"(Kèm theo Hợp đồng số {so_hd} ký ngày 10/02/2026)",
        "Hôm nay, ngày 05 tháng 05 năm 2026, tại văn phòng Bên A, chúng tôi gồm:",
        "Sau khi xem xét, hai bên thống nhất ký Phụ lục hợp đồng số 01 như sau:",
        "Điều 1: Điều chỉnh khối lượng, giá trị hợp đồng:", "Khối lượng và giá trị sau điều chỉnh như sau:",
        _tbl([["TT", "Nội dung công việc", "Đơn vị", "Khối lượng", "Đơn giá (chưa VAT)", "Thành tiền"],
              ["1", "Bê tông mặt đươug", "m3", "120,00", "20.000.000", "2.400.000.000"],
              ["2", "Hoàn thiện", "gói", "1", "2.629.629.630", "2.629.629.630"],
              ["", "Tổng cộng", "", "", "", "5.029.629.630"], ["", "Thuế VAT8%", "", "", "", "402.370.370"],
              ["", "Tổng cộng (đã bao gồm VAT)", "", "", "", "5.432.000.000"]]),
        "Điều 2: Gia hạn tiến độ:", "Thời gian thực hiện hợp đồng được gia hạn thành 240 ngày kể từ ngày khởi công.",
        "Điều 3: Điều khoản thi hành:", "Phụ lục hợp đồng này có hiệu lực kể từ ngày ký.",
    ])


class TestPhuLucRule(unittest.TestCase):
    def test_quy_tac(self):
        from may_chu import phu_luc_ai as pa
        ds = [("HD1", "0707/2025/HĐXD/AB-CD"), ("HD2", "0808/2026/HĐXD/AB-CD")]
        self.assertEqual(pa.nhan_hop_dong("(Kèm theo Hạp đồng số 0707/2025/PIĐXD/AB-CD)", "x.docx", ds)[:1], ("HD1",))
        self.assertEqual(pa.nhan_hop_dong("không có số", "PL01 kèm HĐ 0808.2026.pdf", ds)[2], "tên file")
        dong = ["PHU LỤC HỢP ĐÒNG số 02", "Hôm nay, ngày 05 tháng 02 năm 2026, tại trụ sở",
                "Điều 1: Điều chinh thông tin tài khoản của bên B:", "Điều 2: Điều khoán thi hành:",
                "- Phụ lục Họp dồng này có hiệu lục kể tù ngày ký, được lập thành 06 bán"]
        info, trich, nguon = pa.thong_tin_chung(dong, "05.02.2026-PL02.docx")
        self.assertEqual((info["so_pl"], info["ngay_ky"], info["ngay_hieu_luc"]), ("PL02", "05/02/2026", "05/02/2026"))
        self.assertEqual(info["noi_dung"], "Điều 1: Điều chinh thông tin tài khoản của bên B")
        th = pa.thoi_han_don_gia(["điều chỉnh don giá cho khói lượng thực hiện từ ngày 07/03/2026 đến ngày 02/04/2026 như sau:"])
        self.assertEqual((th["tu"], th["den"]), ("07/03/2026", "02/04/2026"))
        b = pa.doc_bang([[["STT", "Nội dung công việc", "Đơn giá cũ (VNĐ)", "Đơn giá mới (VNĐ)", "Ghi chú"],
                          ["1", "Đào, san gạt đất", "500.000", "650.000", "chưa VAT"]]])
        self.assertEqual((b["loai"], b["items"][0]["dg_cu"], b["items"][0]["don_gia"]), ("doi_chieu", 500000, 650000))
        hl = {"HM0001": {"ten": "Đào, san gạt đất phong hoá và vận chuyển", "dvt": "100m2", "stt": "1"},
              "HM0002": {"ten": "Đắp đất công trình K95", "dvt": "m3", "stt": "2"}}
        self.assertEqual(pa.khop_hang_muc({"ten": "Dào, san gạt dất phong hoá và vận chuyền", "dvt": "100m2"}, hl)[0], "HM0001")
        self.assertIsNone(pa.khop_hang_muc({"ten": "Lát gạch vỉa hè", "dvt": "m2"}, hl)[0])



class TestThamSoThanhToan(unittest.TestCase):
    def test_hang_so_va_khau_tru(self):
        from may_chu.nghiep_vu import doi_chieu_tham_so
        nhung = [["8%", "Thuế suất?", 2, 2, "TH!F10, TH!F12", ""], ["90%", "Tỷ lệ %", 1, 1, "TH!F14", ""],
                 ["1.1", "Thuế suất?", 1, 1, "TH!F20", ""], ["12%", "Tỷ lệ %", 1, 1, "TH!F22", ""],
                 ["2.5", "Hằng số khác (kích thước, hệ số kỹ thuật...)", 4, 4, "KL!C5", ""]]
        cay = [{"o": "TH!E9", "gia_tri": 0.05, "loai": "Nhập tay", "nhom": "6 Tham số HĐ", "ten": "Giữ lại bảo hành [Tỷ lệ]"},
               {"o": "TH!E8", "gia_tri": 0.1, "loai": "Nhập tay", "nhom": "6 Tham số HĐ", "ten": "Thuế VAT [Tỷ lệ]"}]
        tong = {"gt_kn": {"gia_tri": 1_000_000_000, "o": "TH!F5"}, "giu_lai": {"gia_tri": 30_000_000, "o": "TH!F9"},
                "thu_hoi_tu": {"gia_tri": 50_000_000, "o": "TH!F11"}, "tt_ky_nay": {"gia_tri": 870_000_000, "o": "TH!F16"}}
        ts = {"TT-04": "8%", "TT-10": "Không áp dụng", "TT-20": "90% giá trị khối lượng nghiệm thu",
              "TT-21": "5% giá trị thanh toán mỗi đợt"}
        ph = doi_chieu_tham_so(nhung, cay, tong, ts, 0.08)
        tit = {f["title"]: f for f in ph}
        cao = sorted(f["title"] for f in ph if f["level"] == "Cao")
        self.assertTrue(any("1.1" in x and "VAT" in x for x in cao), cao)                 # hệ số 1,1 ≠ 1 + 8%
        self.assertTrue(any("TH!E8" in x for x in cao), cao)                               # ô VAT 10% ≠ 8%
        self.assertTrue(any(x.startswith("Giữ lại = 3%") for x in cao), cao)              # 3% ≠ 5%
        self.assertTrue(any("thu hồi tạm ứng" in x.lower() and "không có tạm ứng" in x for x in cao), cao)
        g = next(f for f in ph if f["title"].startswith("Giữ lại = 3%"))
        self.assertEqual(g["amount"], 20_000_000)                                          # giữ thiếu 20 triệu
        self.assertTrue(any("12%" in f["title"] and f["level"] == "Trung bình" for f in ph))
        ok = next(f for f in ph if "khớp HĐ" in f["title"])
        self.assertIn("8% = TT-04", ok["detail"])
        self.assertIn("90% = TT-20", ok["detail"])
        self.assertIn("TH!E9 5% = TT-21", ok["detail"])
        self.assertFalse(any("2.5" in f["title"] for f in ph))                             # hằng số kỹ thuật bỏ qua
        self.assertEqual(len({f["id"] for f in ph}), len(ph))
        # CSDL lưu tỷ lệ đã chuẩn hoá (0.9, 0.1): 10% khớp giữ lại TT-21, không phải lệch VAT
        ph = doi_chieu_tham_so([["10%", "Thuế suất?", 1, 1, "TH!F9", ""], ["90%", "Tỷ lệ %", 1, 1, "TH!F14", ""]], [],
                               {"gt_kn": {"gia_tri": 100.0}, "giu_lai": {"gia_tri": 10.0}}, {"TT-20": "0.9", "TT-21": 0.1,
                                                                                          "TT-10": "Không áp dụng"}, 0.08)
        self.assertEqual([f["level"] for f in ph], ["Thấp"], ph)


class TestBangKiemLop2(unittest.TestCase):
    def test_gia_tri_ty_le_va_hang_muc(self):
        """Bảng kiểm Lớp 2 hiện cả bước đạt; bước số tổng lệch thì thành phát hiện (GT, B8)."""
        import sqlite3
        import csdl_hop_dong as cs
        from may_chu import nghiep_vu as nv
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE dot_thanh_toan(ma_hd TEXT, dot INTEGER, gt_luy_ke REAL, gt_tt_ky REAL)")
        con.execute("INSERT INTO dot_thanh_toan VALUES ('HD9', 1, 2000000000, 1800000000)")
        o = lambda v, c: {"gia_tri": v, "o": f"TH!{c}"}  # noqa: E731
        tong = {"gt_hd": o(5e9, "F12"), "gt_kn": o(1.08e9, "F13"), "gt_lk_kt": o(2e9, "D14"), "gt_lk": o(3.2e9, "D16"),
                "giu_lai": o(1.08e8, "D18"), "tt_ky_nay": o(1e9, "F16")}
        it = lambda ma, dg: {"dong": 9, "ma_hm": ma, "ten": "Bê tông", "dvt": "m3", "kl_hd": 100, "don_gia": dg,  # noqa: E731
                             "kl_kt": 10, "kl_kn": 50, "kl_lk": 60, "cach_khop": "khoá"}
        m = lambda ma: {"ma_hm": ma, "kl": 100, "don_gia": 10_000_000, "nguon": "HĐ gốc"}  # noqa: E731
        k = {"tong": tong, "gt_hl": 5e9, "vat1": 1.08, "b1": [("GT HĐ trong hồ sơ = GT HĐ hiệu lực", 5e9, 5e9, "ĐẠT", "")],
             "pls": [], "dot_truoc": 1, "ma": "HD9", "dot": 2, "sum_kn": 1.08e9, "kt_chi_tiet": True, "loai": "đơn giá cố định",
             "rows": [{"it": it("HM1", 10_000_000), "m": m("HM1"), "loi": [], "anh_huong": 0},
                      {"it": it("HM2", 10_500_000), "m": m("HM2"), "loi": ["Đơn giá khác BOQ hiệu lực"], "anh_huong": 30_000_000}],
             "thieu": [], "hl": {"HM1": {}, "HM2": {}}, "kt": {"HM1": 10, "HM2": 10}}
        ph2 = [{"id": "B2-01", "code": "B2"}]
        moi, bang, hm = nv.bang_kiem_lop2(k, ph2, cs, con)
        kq = {r["ten"][:30]: r["ket_qua"] for r in bang}
        self.assertEqual(kq["GT hợp đồng ghi trong hồ sơ = "], "Đạt")
        self.assertEqual(kq["GT lũy kế thực hiện đến hết kỳ"], "Đạt")
        self.assertEqual(kq["GT lũy kế hết kỳ trước + GT th"], "Lệch")             # 2 tỷ + 1,08 tỷ ≠ 3,2 tỷ
        self.assertEqual(kq["GT lũy kế hết kỳ trước = lũy k"], "Đạt")
        self.assertEqual(kq["GT thực hiện kỳ này = Σ(KL kỳ "], "Đạt")
        self.assertEqual(kq["Lũy kế thanh toán (các đợt đã "], "Đạt")
        dg = next(r for r in bang if r["ten"].startswith("Đơn giá"))
        self.assertEqual((dg["ket_qua"], dg["ho_so"], dg["finding"]), ("Lệch", "1/2 đạt", "B2-01"))
        self.assertEqual([f["title"][:20] for f in moi], ["Lũy kế hết kỳ này 3,"])
        self.assertEqual(moi[0]["amount"], 120_000_000)
        self.assertEqual(len(hm), 2)
        self.assertEqual((hm[1]["dg_hs"], hm[1]["dg_hd"], hm[1]["kl_kt_db"]), (10_500_000, 10_000_000, 10))
        # tỷ lệ thanh toán: đề nghị 1 tỷ ≠ 90% × 1,08 tỷ = 972 triệu
        b2 = []
        ph = nv.doi_chieu_tham_so([], [], tong, {"TT-04": 0.08, "TT-20": 0.9, "TT-21": 0.1, "TT-10": "Không áp dụng"},
                                  0.08, bang=b2)
        r = lambda dau: next(x for x in b2 if x["ten"].startswith(dau))  # noqa: E731
        tt = r("Đề nghị thanh toán kỳ này")
        self.assertEqual((tt["ket_qua"], tt["hd"], tt["chenh"]), ("Lệch", 972_000_000, 28_000_000))
        f = next(x for x in ph if x["id"] == tt["finding"])
        self.assertEqual((f["level"], f["amount"], f["cell"]), ("Cao", 28_000_000, "F16"))
        self.assertEqual(r("Đề nghị kỳ này = GT thực")["ket_qua"], "Lệch")       # 1,08 tỷ − 108 triệu ≠ 1 tỷ
        self.assertEqual(r("Giữ lại")["ket_qua"], "Đạt")
        self.assertEqual(r("Thu hồi tạm ứng")["ket_qua"], "Đạt")
        tong["tt_ky_nay"] = o(972_000_000, "F16")
        b3 = []
        nv.doi_chieu_tham_so([], [], tong, {"TT-20": "90% giá trị nghiệm thu", "TT-21": 0.1, "TT-10": "Không"}, 0.08, bang=b3)
        self.assertEqual([x["ket_qua"] for x in b3[:2]], ["Đạt", "Đạt"])


def _xlsx_bang(path, tieu_de, dong, sheet="GTHT"):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(["BẢNG XÁC ĐỊNH GIÁ TRỊ KHỐI LƯỢNG HOÀN THÀNH"])
    ws.append([])
    ws.append(tieu_de)
    for r in dong:
        ws.append(r)
    wb.save(path)
    return path


# hạng mục giả lập kiểu hệ thống xử lý nước thải: cùng thiết bị lặp ở nhiều bể; (nhóm, mã riêng, tên, ĐVT, KL, đơn giá)
BOQ_XLNT = [("A", "", "PHẦN THIẾT BỊ"), ("I.", "", "BỂ ĐIỀU HÒA (TK03)"),
            ("1.", "XL-01", "Bơm chìm", "Bộ", 2, 10_000_000), ("2.", "", "Khớp nối nhanh bơm nhúng chìm", "Bộ", 2, 6_800_000),
            ("3.", "", "Phao mực nước", "Bộ", 2, 770_000), ("4.", "", "Van xả khí", "cái", 1, 500_000),
            ("II.", "", "BỂ CHỨA BÙN (TK11)"),
            ("1.", "", "Khớp nối nhanh bơm nhúng chìm", "Bộ", 2, 6_800_000), ("2.", "", "Phao mực nước", "Bộ", 2, 770_000),
            ("3.", "", "Van xả khí", "cái", 1, 500_000),
            ("III.", "", "HỒ SỰ CỐ (TK13)"),
            ("1.", "", "Khớp nối nhanh bơm nhúng chìm", "Bộ", 2, 6_800_000),
            ("2.", "", "Khớp nối nhanh bơm nhúng chìm", "Bộ", 1, 5_200_000), ("3.", "", "Phao mực nước", "Bộ", 2, 770_000),
            ("B", "", "PHẦN XÂY DỰNG"), ("I.", "", "CÔNG TÁC BỔ SUNG"),
            ("1.", "", "Đắp gờ chỉ, chỉ nước", "md", 250, 36_000),
            ("2.", "", "Cấp nguồn cho biển tên và cổng điện (bao gồm ống D20)", "md", 35, 112_000),
            ("3.", "", "Đắp gờ chỉ, chỉ nước", "md", 30, 36_000)]


def tao_hd_xlnt(d, db):
    """CSDL giả lập: một HĐ đơn giá cố định + BOQ gốc đọc bằng đúng hàm nhập BOQ của giao diện."""
    import csdl_hop_dong as cs
    from master_hd import khoa
    from may_chu import nghiep_vu as nv
    boq = _xlsx_bang(os.path.join(d, "boq.xlsx"), ["STT", "Mã hạng mục", "Tên công việc", "Đơn vị", "Khối lượng", "Đơn giá"],
                     [list(r) if len(r) > 3 else list(r) + ["", "", ""] for r in BOQ_XLNT], sheet="BOQ")
    items, loi = nv.boq_doc_dong(boq, "BOQ", 3, {"stt": "A", "ma_rieng": "B", "ten": "C", "dvt": "D", "kl": "E",
                                                 "don_gia": "F"})
    assert not loi, loi
    con = cs.mo_csdl(db)
    ma = cs._them_hop_dong(con, "99/2026/HĐ-XLNT", {"TT-01": {"gia_tri": "Đơn giá cố định"},
                                                    "TT-02": {"gia_tri": 100_000_000}, "TT-04": {"gia_tri": 0.08}})
    for i, it in enumerate(items, 1):
        con.execute("INSERT INTO boq_dong(ma_hd, pl_id, thao_tac, ma_hm, stt, nhom, ten, dvt, kl, don_gia, khoa, ma_rieng) "
                    "VALUES (?,NULL,'GOC',?,?,?,?,?,?,?,?,?)",
                    (ma, f"HM{i:04d}", it["stt"], it["nhom"], it["ten"], it["dvt"], it["kl"], it["don_gia"],
                     khoa(dict(nhom=it["nhom"], ten=it["ten"], dvt=it["dvt"])), it["ma_rieng"] or None))
    con.commit()
    return con, ma


def tao_hstt_xlnt(path, them_dong=()):
    """Hồ sơ thanh toán: dòng thông số 'Kiểu:', 'Xuất xứ:', 'Model' dưới thiết bị; tên hơi khác BOQ; một 'Van xả khí'
    nằm ở cuối dưới nhóm không có trong BOQ (máy không đủ căn cứ chọn bể)."""
    def hm(stt, ten, dvt, kl, dg, ma=""):
        return [stt, ma, ten, dvt, kl, 0, kl, kl, dg, kl * dg]
    mo_ta = lambda t: ["", "", t]  # noqa: E731
    dong = [["A", "", "PHẦN THIẾT BỊ"], ["I.", "", "BỂ ĐIỀU HÒA (TK03)"],
            hm("1.", "Bơm chìm WP01-A/B", "Bộ", 2, 10_000_000, "XL-01"), mo_ta("Kiểu:"), mo_ta("Xuất xứ: Nhật"),
            hm("2.", "Khớp nối nhanh bơm nhúng chìm ", "Bộ", 2, 6_800_000), mo_ta("Xuất xứ: Việt Nam"),
            hm("3.", "Phao mực nước", "Bộ", 2, 770_000), mo_ta("Model"),
            ["II.", "", "BỂ CHỨA BÙN (TK11)"],
            hm("1.", "Khớp nối nhanh bơm nhúng chìm", "Bộ", 2, 6_800_000), mo_ta("Xuất xứ: Việt Nam"),
            hm("2.", "Phao mực nước", "Bộ", 2, 770_000), mo_ta("- Chiều dài cáp 10m"),
            ["III.", "", "HỒ SỰ CỐ (TK13)"],
            hm("1.", "Khớp nối nhanh bơm nhúng chìm", "Bộ", 2, 6_800_000), mo_ta("Xuất xứ: Việt Nam"),
            hm("2.", "Khớp nối nhanh bơm nhúng chìm", "Bộ", 1, 5_200_000), mo_ta("Xuất xứ: Việt Nam"),
            hm("3.", "Phao mực nước", "Bộ", 2, 770_000),
            ["B", "", "PHẦN XÂY DỰNG"], ["I.", "", "CÔNG TÁC BỔ SUNG"],
            hm("1.", "Đắp gờ chỉ, chỉ nước", "md", 250, 36_000),
            hm("2.", "Cấp nguồn cho bển tên và cổng điện (bao gồm ống D20)", "md", 35, 112_000),
            hm("3.", "Đắp gờ chỉ, chỉ nước", "md", 30, 36_000),
            ["C", "", "VAN BỔ SUNG"], hm("1.", "Van xả khí", "cái", 1, 500_000)] + list(them_dong)
    return _xlsx_bang(path, ["STT", "Mã HM", "Tên công việc", "Đơn vị", "Khối lượng hợp đồng", "Khối lượng kỳ trước",
                             "Khối lượng kỳ này", "Lũy kế đến hết kỳ này", "Đơn giá", "Giá trị kỳ này"], dong)


class TestGhepHangMuc(unittest.TestCase):
    """Ghép dòng hồ sơ thanh toán với BOQ khi tên thiết bị lặp ở nhiều bể (HĐ xử lý nước thải)."""

    def test_dong_mo_ta_khong_la_nhom(self):
        from master_hd import la_dong_mo_ta
        for t in ("Kiểu: ", "Xuất xứ: Ý", "Model", "- Chi phí cấu hình", "Trung tâm báo cháy", "Lưu lượng:"):
            self.assertTrue(la_dong_mo_ta("", t), t)
        for stt, t in (("", "CÔNG TÁC BỔ SUNG"), ("", "THEO PHỤ LỤC 05 KÝ NGÀY 12/05/2026"), ("I.", "Hố thu gom (TK01)"),
                       ("", "3.1.1 Camera xoay giám sát")):
            self.assertFalse(la_dong_mo_ta(stt, t), t)

    def test_ghep_ten_trung_nhieu_be(self):
        import csdl_hop_dong as cs
        from may_chu import nghiep_vu as nv
        d = _thu_muc("ghep")
        con, ma = tao_hd_xlnt(d, os.path.join(d, "hd.db"))
        k = cs.tinh_doi_chieu_dot(con, ma, tao_hstt_xlnt(os.path.join(d, "hstt.xlsx")), "2026-10-01", 1)
        r = {(x["it"]["ten"].strip()[:14], x["it"]["kl_hd"], x["it"]["don_gia"], x["it"]["nhom"].split(" / ")[-1]):
             (x["it"]["ma_hm"], x["it"]["cach_khop"]) for x in k["rows"]}
        boq = {(row["nhom"].split(" / ")[-1], row["ten"][:14], row["kl"], row["don_gia"]): row["ma_hm"]
               for row in con.execute("SELECT * FROM boq_dong WHERE ma_hd = ?", (ma,))}
        # mỗi dòng hồ sơ phải về đúng hạng mục của đúng bể (cùng nhóm cuối, cùng KL HĐ, cùng đơn giá)
        for (ten, kl, dg, nhom), (ma_hm, cach) in r.items():
            if ten.startswith("Van xả"):
                continue
            ky_vong = boq.get((nhom, ten if not ten.startswith(("Bơm", "Cấp")) else
                               next(b[1] for b in boq if b[1][:5] == ten[:5]), kl, dg))
            self.assertIsNotNone(ky_vong, (ten, nhom))
            self.assertEqual(ma_hm, ky_vong, (ten, nhom, cach))
        cach = {x["it"]["ten"].strip()[:14] + "|" + x["it"]["nhom"].split(" / ")[-1][:8]: x["it"]["cach_khop"] for x in k["rows"]}
        self.assertEqual(cach["Bơm chìm WP01-|BỂ ĐIỀU "], "mã HM")
        self.assertEqual(cach["Khớp nối nhanh|BỂ ĐIỀU "], "khoá")             # nhóm đúng nhờ bỏ qua dòng 'Xuất xứ:'
        self.assertTrue(cach["Cấp nguồn cho |CÔNG TÁC"].startswith("tên gần đúng"))
        self.assertTrue(all(x["it"]["cach_khop"] for x in k["rows"] if not x["it"]["ten"].startswith("Van")))
        # 'Van xả khí' cùng tên, cùng giá ở 2 bể, nằm ngoài vùng hai bể → máy không đoán, chờ ghép tay (Trung bình)
        van = next(x for x in k["rows"] if x["it"]["ten"].startswith("Van"))
        self.assertIsNone(van["it"]["ma_hm"])
        self.assertTrue(van["it"]["can_ghep"])
        self.assertEqual(len(van["it"]["ung_vien"]), 2)
        self.assertTrue(van["loi"][0].startswith("Cần ghép tay"))
        self.assertEqual(van["anh_huong"], 0)
        ph, _ = nv._lop2(k)
        f = next(x for x in ph if x["title"].startswith("Cần ghép tay"))
        self.assertEqual((f["code"], f["level"], f["amount"]), ("B3", "Trung bình", None))
        self.assertFalse([x for x in ph if x["code"] == "B3" and x["level"] == "Cao"])
        _, bang, hm = nv.bang_kiem_lop2(k, ph, cs, con)
        b3 = next(x for x in bang if x["ten"].startswith("Hạng mục trong hồ sơ có trong BOQ"))
        self.assertEqual(b3["ket_qua"], "Cần xem")
        h = next(x for x in hm if x["ten"].startswith("Van"))
        self.assertTrue(h["khoa"] and h["can_ghep"] and len(h["ung_vien"]) == 2)
        # ghép tay → lần sau máy dùng ngay ('đã xác nhận')
        con.execute("INSERT INTO khop_hang_muc VALUES (?,?,?,?,?,?)", (ma, h["khoa"], h["ung_vien"][1]["ma_hm"], "ghép tay", "",
                                                                         cs.bay_gio()))
        k2 = cs.tinh_doi_chieu_dot(con, ma, os.path.join(d, "hstt.xlsx"), "2026-10-01", 1)
        van = next(x for x in k2["rows"] if x["it"]["ten"].startswith("Van"))
        self.assertEqual((van["it"]["ma_hm"], van["it"]["cach_khop"], van["loi"]), (h["ung_vien"][1]["ma_hm"], "đã xác nhận", []))
        con.close()

    def test_ghep_tay_api(self):
        """nghiep_vu.kiem_tra_dot → ghep_hang_muc (lưu khop_hang_muc, đổi ghép phải qua chế độ sửa) → chạy lại hết B3."""
        import csdl_hop_dong as cs
        from may_chu import nghiep_vu as nv
        d = _thu_muc("ghep_api")
        db = os.path.join(d, "hd.db")
        cu = os.environ["HD_CSDL"]
        os.environ["HD_CSDL"] = db
        try:
            con, ma = tao_hd_xlnt(d, db)
            con.close()
            p = tao_hstt_xlnt(os.path.join(d, "hstt.xlsx"))

            class V:
                id = "kiem_dot-ghep-1"

                def tien_do(self, *a):
                    pass
            kq = nv.kiem_tra_dot(V(), ma, p, "2026-10-01", 1)
            h = next(x for x in kq["doi_chieu_hm"] if x["ten"].startswith("Van"))
            with self.assertRaises(ValueError):
                nv.ghep_hang_muc(V.id, h["dong"], "HM9999")
            m1, m2 = h["ung_vien"][0]["ma_hm"], h["ung_vien"][1]["ma_hm"]
            r = nv.ghep_hang_muc(V.id, h["dong"], m1.lower())
            self.assertEqual((r["ma_hm"], r["so_ghep_moi"]), (m1, 1))
            r = nv.ghep_hang_muc(V.id, h["dong"], m2)                # đổi ý: ghi nhật ký chế độ sửa
            con = cs.mo_csdl(db)
            self.assertEqual(con.execute("SELECT ma_hm, cach_khop FROM khop_hang_muc WHERE ma_hd = ? AND khoa_hstt = ?",
                                         (ma, h["khoa"])).fetchone()[:], (m2, "ghép tay"))
            self.assertTrue(con.execute("SELECT 1 FROM nhat_ky WHERE thao_tac = 'MỞ CHẾ ĐỘ SỬA' AND chi_tiet LIKE 'Ghép tay lại%'")
                            .fetchone())
            con.close()
            self.assertEqual(nv.doc_ket_qua_kiem_tra("kiem_tra_dot", V.id)["ghep_moi"], [str(h["dong"])])
            V.id = "kiem_dot-ghep-2"
            kq2 = nv.kiem_tra_dot(V(), ma, p, "2026-10-01", 1)
            self.assertFalse([f for f in kq2["phat_hien"] if f["code"] == "B3"])
            self.assertEqual(next(x for x in kq2["doi_chieu_hm"] if x["ten"].startswith("Van"))["ma_hm"], m2)
        finally:
            os.environ["HD_CSDL"] = cu


def _sang_xls(xlsx):
    """Tạo file .xls (Excel 97-2003) từ .xlsx bằng LibreOffice — chỉ để thử."""
    import shutil
    import subprocess
    from may_chu.doi_xls import _tim_soffice
    so = _tim_soffice()
    d = os.path.dirname(xlsx)
    ho_so = tempfile.mkdtemp()
    subprocess.run([so, f"-env:UserInstallation=file://{ho_so}", "--headless", "--convert-to", "xls", "--outdir", d, xlsx],
                   capture_output=True, timeout=120)
    shutil.rmtree(ho_so, ignore_errors=True)
    return os.path.splitext(xlsx)[0] + ".xls"


def _co_soffice():
    from may_chu.doi_xls import _tim_soffice
    return bool(_tim_soffice())


class TestFileXls(unittest.TestCase):
    """Nạp file Excel 97-2003 (.xls): chuyển sang .xlsx, giữ công thức khi máy có Excel / LibreOffice."""

    @unittest.skipUnless(_co_soffice(), "máy thử không có LibreOffice")
    def test_chuyen_giu_cong_thuc_va_chi_gia_tri(self):
        import openpyxl
        from may_chu import doi_xls as dx
        d = _thu_muc("xls")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tong hop"
        ws.append(["STT", "Nội dung", "Giá trị"])
        ws.append([1, "Giá trị hoàn thành", 1000000])
        ws.append([2, "Giữ lại 5%", "=ROUND(C2*5%,0)"])
        an = wb.create_sheet("An")
        an["A1"] = "sheet ẩn"
        an.sheet_state = "hidden"
        x = os.path.join(d, "ho so dot 2.xlsx")
        wb.save(x)
        xls = _sang_xls(x)
        os.remove(x)
        self.assertEqual(dx.loai_that(xls), "xls")
        out, cach = dx.chuan_hoa(xls, can_cong_thuc=True)          # LibreOffice: giữ công thức
        self.assertEqual((out.endswith(".xlsx"), cach), (True, "LibreOffice"))
        self.assertEqual(openpyxl.load_workbook(out)["Tong hop"]["C3"].value, "=ROUND(C2*5%,0)")
        self.assertEqual(openpyxl.load_workbook(out, data_only=True)["Tong hop"]["C3"].value, 50000)
        self.assertFalse(dx.chi_gia_tri(out))
        self.assertTrue(os.path.exists(xls))                           # file gốc giữ để truy vết
        # máy không có Excel / LibreOffice: xlrd chỉ giá trị — được cho BOQ / phiếu, KHÔNG cho kiểm tra toàn vẹn
        cu = dx._bang_excel, dx._bang_libreoffice
        dx._bang_excel = dx._bang_libreoffice = lambda *a: "không có"
        try:
            with self.assertRaises(dx.LoiXls) as e:
                dx.chuan_hoa(xls, can_cong_thuc=True)
            self.assertIn("Save As", str(e.exception))
            try:
                import xlrd  # noqa: F401
            except ImportError:
                return
            out2, cach2 = dx.chuan_hoa(xls)
            self.assertIn("xlrd", cach2)
            w2 = openpyxl.load_workbook(out2)
            self.assertEqual((w2["Tong hop"]["C3"].value, w2["An"].sheet_state), (50000, "hidden"))
            self.assertTrue(dx.chi_gia_tri(out2))
        finally:
            dx._bang_excel, dx._bang_libreoffice = cu
        # .xlsx bị đổi đuôi thành .xls
        gia = os.path.join(d, "doi duoi.xls")
        openpyxl.Workbook().save(gia)
        out3, cach3 = dx.chuan_hoa(gia)
        self.assertTrue(cach3.startswith("đổi đuôi") and out3.endswith(".xlsx"))
        with open(os.path.join(d, "rac.xls"), "wb") as f:
            f.write(b"khong phai excel")
        with self.assertRaises(dx.LoiXls):
            dx.chuan_hoa(os.path.join(d, "rac.xls"))

    @unittest.skipUnless(_co_soffice(), "máy thử không có LibreOffice")
    def test_tai_len_xls(self):
        """Import BOQ và kiểm tra đợt nhận .xls: kết quả như với .xlsx."""
        import csdl_hop_dong as cs
        from may_chu import dich_vu as dv
        d = _thu_muc("xls_tl")
        boq = _xlsx_bang(os.path.join(d, "boq.xlsx"), ["STT", "Tên công việc", "Đơn vị", "Khối lượng", "Đơn giá"],
                         [["1", "Bê tông móng", "m3", 10, 1_000_000], ["2", "Cốt thép", "tấn", 2, 20_000_000]], sheet="BOQ")
        kq = dv.boq_tai_len("boq.xls", _doc(_sang_xls(boq)))
        self.assertEqual((kq["tu_xls"], kq["goi_y"]["sheet"], kq["goi_y"]["hang_tieu_de"]), ("LibreOffice", "BOQ", 3))
        self.assertTrue(kq["tep"].endswith(".xlsx"))
        with self.assertRaises(dv.LoiNguoiDung):
            dv.luu_tai_len(d, "gia.xls", b"%PDF-1.4 khong phai excel", (".xls",))
        con, ma = tao_hd_xlnt(d, os.path.join(d, "hd.db"))
        x = tao_hstt_xlnt(os.path.join(d, "hstt.xlsx"))
        p = dv.sang_xlsx(_sang_xls(x), can_cong_thuc=True, trong_viec=True)
        a = cs.tinh_doi_chieu_dot(con, ma, x, "2026-10-01", 1)
        b = cs.tinh_doi_chieu_dot(con, ma, p, "2026-10-01", 1)
        self.assertEqual([(r["it"]["dong"], r["it"]["ma_hm"], r["it"]["cach_khop"]) for r in a["rows"]],
                         [(r["it"]["dong"], r["it"]["ma_hm"], r["it"]["cach_khop"]) for r in b["rows"]])
        con.close()


def tao_bo_chung_tu(d):
    """Bộ chứng từ giả lập của một đợt (như ABBYY trả về): BB nghiệm thu KL, BB giao nhận, CQ (bảng), CO (dạng form)."""
    hd = "(Kèm theo hợp đồng số 15/2026/HĐXD/MA-TN)"
    f = {}
    f["nt"] = mau_gia_lap.tao_docx(os.path.join(d, "BB nghiem thu dot 2.docx"), [
        "BIÊN BẢN NGHIỆM THU KHỐI LƯỢNG HOÀN THÀNH", "Số: 02/NTKL", hd, "Hôm nay, ngày 20 tháng 07 năm 2026, tại công trường",
        _tbl([["STT", "Nội dung công việc", "Đơn vị", "Khối lượng kỳ này", "Khối lượng lũy kế"],
              ["1", "Bê tông mặt đường", "m3", "30", "80"],
              ["2", "Cung cấp và lắp đặt ống HDPE D110", "m", "200", "200"]])])
    f["gn"] = mau_gia_lap.tao_docx(os.path.join(d, "BB giao nhan ong.docx"), [
        "BIÊN BẢN GIAO NHẬN VẬT TƯ", "Số: GN-07/2026", hd, "Hôm nay, ngày 10 tháng 07 năm 2026",
        _tbl([["STT", "Tên vật tư", "Model", "ĐVT", "Số lượng", "Số lô"],
              ["1", "Ống HDPE D110 PN10", "HD110-PN10", "m", "150", "L2607"]])])
    f["cq"] = mau_gia_lap.tao_docx(os.path.join(d, "CQ ong HDPE.docx"), [
        "CERTIFICATE OF QUALITY", "No: CQ-5521", "Date: 15/07/2026",
        _tbl([["No.", "Description", "Model", "Quantity", "Lot No"], ["1", "HDPE pipe", "HD110-PN10", "150", "L2699"]])])
    f["co"] = mau_gia_lap.tao_docx(os.path.join(d, "CO ong HDPE.docx"), [
        "CERTIFICATE OF ORIGIN", "No: VN-2026-0099", "Date: 01/07/2026",
        "Goods: HDPE pipe model HD110-PN10, quantity 150 m, made in Viet Nam."])
    return f


CT_AI = {"dong": [{"ten": "HDPE pipe", "model": "HD110-PN10", "quy_cach": "", "dvt": "m", "so_luong": "150", "lo": "",
                   "xuat_xu": "Viet Nam", "nsx": "", "trich_dan": "Goods: HDPE pipe model HD110-PN10, quantity 150 m"}]}


class TestChungTu(unittest.TestCase):
    def test_doi_chieu_bo_chung_tu(self):
        from may_chu import chung_tu as ct
        d = _thu_muc("ct")
        f = tao_bo_chung_tu(d)
        srv, port = mock_ollama.start([], model="qwen3:8b")
        srv.ctl["chung_tu"] = CT_AI
        try:
            ai = MayAI(f"http://127.0.0.1:{port}", "qwen3:8b")
            docs = [ct.doc_mot_tai_lieu(f[k], ai=ai) for k in ("nt", "gn", "cq", "co")]
        finally:
            srv.shutdown()
        by = {x["loai"]: x for x in docs}
        self.assertEqual(sorted(by), ["BB_GN", "BB_NT", "CO", "CQ"])
        self.assertEqual((by["BB_NT"]["ngay"], by["BB_NT"]["so"]), ("2026-07-20", "02/NTKL"))
        self.assertEqual((by["CQ"]["ngay"], by["CO"]["ngay"]), ("2026-07-15", "2026-07-01"))
        self.assertEqual((by["BB_GN"]["so"], by["CQ"]["so"], by["CO"]["so"]), ("GN-07/2026", "CQ-5521", "VN-2026-0099"))
        self.assertTrue(by["BB_NT"]["ly_do_loai"].startswith("tiêu đề: “BIÊN BẢN NGHIỆM THU"))
        self.assertEqual([(x["ten"], x["so_luong"]) for x in by["BB_NT"]["dong"]],
                         [("Bê tông mặt đường", 30.0), ("Cung cấp và lắp đặt ống HDPE D110", 200.0)])
        self.assertEqual((by["BB_GN"]["dong"][0]["model"], by["BB_GN"]["dong"][0]["lo"]), ("HD110-PN10", "L2607"))
        self.assertEqual(by["CO"]["dong"][0]["nguon"], "Local AI")
        self.assertEqual(by["CO"]["dong"][0]["kiem_tra"], "")               # trích dẫn có nguyên văn
        kq = {"so_hd": "15/2026/HĐXD/MA-TN", "ngay_nt": "2026-07-25", "ngay_ky_hd": "2026-02-10", "vat": 0.08,
              "hang_muc": [{"khoa": "HM0001", "ma_hm": "HM0001", "ten": "Bê tông mặt đường", "dvt": "m3", "kl_kn": 30,
                            "kl_lk": 80, "don_gia": 20_000_000},
                           {"khoa": "HM0003", "ma_hm": "HM0003", "ten": "Cung cấp và lắp đặt ống HDPE D110", "dvt": "m",
                            "kl_kn": 200, "kl_lk": 200, "don_gia": 100_000},
                           {"khoa": "HM0004", "ma_hm": "HM0004", "ten": "Lát gạch vỉa hè", "dvt": "m2", "kl_kn": 50,
                            "kl_lk": 50, "don_gia": 300_000}],
              "tai_lieu": docs}
        ct.doi_chieu(kq)
        ph = kq["phat_hien"]
        code = lambda c: [x for x in ph if x["code"] == c]  # noqa: E731
        self.assertTrue(any("Lát gạch" in x["title"] and x["level"] == "Cao" for x in code("C01")), code("C01"))
        self.assertFalse(any("Bê tông" in x["title"] for x in code("C01")))
        c03 = code("C03")
        self.assertEqual(len(c03), 1, ph)
        self.assertEqual(c03[0]["amount"], 5_400_000)                        # thiếu 50 m × 100.000 × 1,08
        self.assertTrue(any(x["level"] == "Cao" and "số lô" in x["title"] for x in code("C06")), code("C06"))
        self.assertTrue(any("sau ngày giao" in x["title"] for x in code("C07")), code("C07"))
        self.assertEqual(len(code("C02")), 1)                               # 20/07 ≠ ngày nghiệm thu đợt 25/07
        self.assertFalse(code("C08"))
        self.assertFalse(code("C09"), code("C09"))                           # đọc được số, ngày của mọi chứng từ
        self.assertFalse([x for x in code("C05") if "CO" in x["title"] or "CQ" in x["title"]])   # có đủ CO, CQ
        r = {m["khoa"]: m for m in kq["ma_tran"]}
        self.assertEqual((r["HM0003"]["gn"], bool(r["HM0003"]["co"]), bool(r["HM0003"]["cq"])), (150, True, True))
        kq["hang_muc"][0]["kl_kn"] = 0                                       # sửa: hạng mục không có KL kỳ này
        kq["tai_lieu"][1]["dong"][0]["lo"] = "L2699"
        ct.doi_chieu(kq)
        self.assertFalse([x for x in kq["phat_hien"] if x["code"] == "C06" and x["level"] == "Cao"])


class TestOcr(unittest.TestCase):
    def setUp(self):
        from trich_xuat import ocr_abbyy
        self.ocr = ocr_abbyy
        self._cbp_cu = ocr_abbyy.chuan_bi_pdf
        self.goc = _thu_muc("ocr_goc")
        ch.luu_cau_hinh({"ocr": {"che_do": "tu_dong", "thu_muc": self.goc}})
        self.d = ocr_abbyy.thu_muc()

    def tearDown(self):
        self.ocr.chuan_bi_pdf = self._cbp_cu
        ch.luu_cau_hinh({"ocr": {"che_do": "tu_dong", "thu_muc": ""}})

    def _pdf(self, ten="scan.pdf", trang=2):
        p = os.path.join(_thu_muc("ocr_pdf"), ten)
        trs = b"".join(b"%d 0 obj << /Type /Page >> endobj\n" % (i + 3) for i in range(trang))
        with open(p, "wb") as f:
            f.write(b"%PDF-1.4\n" + trs + os.urandom(6) + b"\n%%EOF")
        return p

    def _con_file(self):
        return [x.name for k in ("in", "tam", "nhan") for x in self.d[k].iterdir()]

    def test_so_vn(self):
        so = self.ocr.so_vn
        for s, v in [("1.250,560", 1250.56), ("975.120,80", 975120.8), ("512.300", 512300), ("4.312.765.432", 4312765432),
                     ("0,08", 0.08), ("12.5", 12.5), ("1,250,000", 1250000), ("(1.000)", -1000), ("-2,5", -2.5),
                     ("100", 100), (7, 7.0)]:
            self.assertEqual(so(s), v, s)
        for s in ("100m2", "1.1.2", "", "Cộng", None):
            self.assertIsNone(so(s), s)

    def test_boq_word_sang_excel(self):
        from may_chu import nghiep_vu as nv
        d = _thu_muc("ocr_boq")
        docx = tao_boq_word(os.path.join(d, "BOQ.docx"))
        xlsx = os.path.join(d, "BOQ_bang.xlsx")
        self.assertEqual(self.ocr.docx_sang_xlsx(docx, xlsx), 1)         # 2 bảng cùng 6 cột → gộp 1 sheet
        f = nv.boq_doc_file(xlsx)
        g = f["goi_y"]
        self.assertEqual(g["sheet"], "Bảng 1")
        self.assertIn("Kèm theo hợp đồng số 15/2026", " ".join(str(x) for x in g["dong"][1]))
        items, loi = nv.boq_doc_dong(xlsx, g["sheet"], g["hang_tieu_de"], g["cot"])
        self.assertEqual(loi, [])
        self.assertEqual([(i["ten"], i["kl"], i["don_gia"]) for i in items],
                         [("Bê tông mặt đường", 100.0, 20000000.0), ("Hoàn thiện", 1.0, 2629629630.0)])
        self.assertEqual(items[0]["nhom"], "PHẦN ĐƯỜNG")

    def test_ocr_qua_thu_muc_hot_folder(self):
        docx, _ = mau_gia_lap.tao_hop_dong(_thu_muc("ocr_hd0"))
        truoc = self.ocr.so_trang_da_dung()[0]
        ab = AbbyyGia(self.d["in"], self.d["out"], docx)
        ab.start()
        try:
            pdf = self._pdf(trang=3)
            moc = []
            p1, i1 = self.ocr.ocr_docx(pdf, tien_do=moc.append)
            p2, i2 = self.ocr.ocr_docx(pdf)
        finally:
            ab.stop()
        self.assertEqual(len(ab.da_lam), 1)                              # lần 2 dùng lại, không tốn trang
        self.assertEqual((i1["trang"], i1["tu_luu_dem"], i2["tu_luu_dem"]), (3, False, True))
        self.assertEqual(_doc(p1), _doc(docx))
        self.assertTrue(any("đã nhận file" in m for m in moc), moc)
        self.assertEqual(self._con_file(), [])                           # không để lại file nào
        self.assertEqual([x.name for x in self.d["out"].iterdir()], [])  # cả PDF kết quả thừa
        self.assertEqual(self.ocr.so_trang_da_dung()[0] - truoc, 3)

    def test_chung_tu_pdf_scan_qua_ocr(self):
        """BB giao nhận scan (PDF không có lớp chữ) → Hot Folder → đọc số, ngày, bảng dòng hàng như file Word."""
        from may_chu import chung_tu as ct
        f = tao_bo_chung_tu(_thu_muc("ct_ocr"))
        self.ocr.chuan_bi_pdf = lambda path, **k: self.ocr.ocr_docx(path, **k)   # PDF giả: bỏ bước dò lớp chữ
        ab = AbbyyGia(self.d["in"], self.d["out"], f["gn"])
        ab.start()
        try:
            x = ct.doc_mot_tai_lieu(self._pdf("BB giao nhan scan.pdf", trang=1))
        finally:
            ab.stop()
        self.assertEqual((x["loai"], x["so"], x["ngay"]), ("BB_GN", "GN-07/2026", "2026-07-10"))
        self.assertEqual(x["ocr"], 1)
        self.assertEqual([(d["model"], d["so_luong"], d["lo"]) for d in x["dong"]], [("HD110-PN10", 150.0, "L2607")])

    def test_khong_nhan_huy_va_loi_log(self):
        from trich_xuat.ai_local import DaDung
        o = {**self.ocr.cau_hinh_ocr(), "cho_nhan": 1, "cho_toi_da": 20}
        with self.assertRaises(self.ocr.LoiOCR) as cm:                   # task chưa chạy → rút file, báo rõ
            self.ocr._chay_hot_folder(b"%PDF-1.4 a", "pdf", o, nghi=0.1)
        self.assertEqual(cm.exception.ma, "PICKUP_TIMEOUT")
        self.assertIn(str(self.d["in"]), cm.exception.thong_diep)
        ev = threading.Event()
        threading.Timer(0.4, ev.set).start()
        with self.assertRaises(DaDung):
            self.ocr._chay_hot_folder(b"%PDF-1.4 b", "pdf", o, huy=ev, nghi=0.1)
        self.assertEqual(self._con_file(), [])
        ab = AbbyyGia(self.d["in"], self.d["out"], None, loi=True)
        ab.start()
        try:
            with self.assertRaises(self.ocr.LoiOCR) as cm:
                self.ocr._chay_hot_folder(b"%PDF-1.4 c", "pdf", {**o, "cho_nhan": 60}, nghi=0.1)
        finally:
            ab.stop()
        self.assertEqual(cm.exception.ma, "JOB_FAILED")

    def test_trang_thai_doc_log_task(self):
        st = self.ocr.trang_thai(lam_moi=True)
        self.assertEqual((st["input_dir"], st["loi"]), (str(self.d["in"]), ""))
        self.assertIn("Chưa thấy log", json.dumps(st["checks"], ensure_ascii=False))
        with open(self.d["out"] / "Hot Folder Log.txt", "w", encoding="utf-16") as f:
            f.write(f"INPUT FOLDER: \t{self.d['in']}\nOUTPUT FOLDER: \t{self.d['out']}\n"
                    "SAVE AS TYPE: \tMicrosoft Word Document (*.docx)\n")
        st = self.ocr.trang_thai(lam_moi=True)
        ck = {c["check"]: c["ok"] for c in st["checks"]}
        self.assertTrue(ck["Task theo dõi đúng thư mục in"])
        self.assertTrue(ck["Task lưu Microsoft Word (.docx)"])
        self.assertEqual(self.ocr.dinh_dang_task(self.d["out"]), ["docx"])

    def test_che_do(self):
        try:
            import pypdf
        except ImportError:
            self.skipTest("thiếu pypdf")
        w = pypdf.PdfWriter()
        w.add_blank_page(595, 842)
        pdf = os.path.join(_thu_muc("ocr_cd"), "scan.pdf")
        with open(pdf, "wb") as f:
            w.write(f)
        self.assertEqual(self.ocr.can_ocr_pdf(pdf)[0], True)             # tự động: PDF scan
        ch.luu_cau_hinh({"ocr": {"che_do": "tat"}})
        self.assertEqual(self.ocr.can_ocr_pdf(pdf)[0], False)
        self.assertEqual(self.ocr.can_ocr_pdf("a.docx")[0], False)

    def test_trich_hop_dong_pdf_scan(self):
        """PDF scan → OCR (giả lập) → cùng kết quả như bản Word: 37/37 đúng đáp án."""
        d = _thu_muc("ocr_hd")
        docx, tsv = mau_gia_lap.tao_hop_dong(d)
        pdf = os.path.join(d, "HD_GIA_LAP.pdf")
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.4 scan")
        goi = []

        def gia(path, tien_do=None, dung=None, ghi_log=None):
            goi.append(path)
            tien_do("OCR ABBYY: đang nhận dạng chữ…")
            return docx, {"trang": 9, "giay": 3.0, "tu_luu_dem": False, "ly_do": "PDF scan (không có lớp chữ)"}
        self.ocr.chuan_bi_pdf = gia
        lc, ds, srv = _chay_luot([pdf], dap_an=[tsv], thu_muc_dap_an=d, chay_lai=True)
        self.assertEqual(lc.trang_thai()["tt"], "xong", lc.trang_thai()["thong_bao"])
        self.assertEqual(goi, [pdf])
        self.assertEqual(ds[0]["tom_tat"]["dung_dap_an"], "37/37")


@unittest.skipUnless(CO_MAU_THAT, "thiếu hợp đồng thật trong du_lieu_mau\\")
class TestHopDongThat(unittest.TestCase):
    def test_hai_hop_dong_mau(self):
        files = [str(MAU / "HD_2903.docx")]
        if (MAU / "HD_0404.doc").exists() and shutil.which("soffice") or os.name == "nt":
            files.append(str(MAU / "HD_0404.doc"))
        keys = [str(p) for p in MAU.glob("DAP_AN_HD_*.tsv")]
        lc, ds, srv = _chay_luot(files, dap_an=keys, thu_muc_dap_an=str(MAU), chay_lai=True)
        for kq in ds:
            a, b = kq["tom_tat"]["dung_dap_an"].split("/")
            self.assertGreaterEqual(int(a), int(b) - 1, kq["hop_dong"])
            self.assertGreaterEqual(kq["tom_tat"]["so_ok"], 33, kq["hop_dong"])
            self.assertFalse(any(d["logic"] for d in kq["bang"]),           # đáp án đúng → không báo logic giả
                             [(d["ma"], d["logic"]) for d in kq["bang"] if d["logic"]])


class TestMayChu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = _thu_muc("mc")
        cls.docx, cls.tsv = mau_gia_lap.tao_hop_dong(d)
        cls.osrv, oport = mock_ollama.start([cls.tsv], model="qwen3:8b")
        ch.luu_cau_hinh({"may_ai": f"http://127.0.0.1:{oport}", "model": "qwen3:8b",
                         "cloud": {"bat": False, "nha_cung_cap": "anthropic", "model": "", "ty_le": 20}})
        from may_chu import server
        cls.server = server
        cls.ms = server.tao_may_chu(0)
        cls.P = server.PORT
        threading.Thread(target=cls.ms.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.ms.shutdown()
        cls.osrv.shutdown()

    def call(self, m, path, body=None, raw=None, headers=None):
        h = {"Host": f"localhost:{self.P}", "X-HD": "1"}
        h.update(headers or {})
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if m != "GET" and data is None:
            data = b"{}"
        r = urllib.request.Request(f"http://127.0.0.1:{self.P}{path}", data=data, headers=h, method=m)
        try:
            with urllib.request.urlopen(r) as x:
                b = x.read()
                return x.status, (json.loads(b) if x.headers.get_content_type() == "application/json" else b)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_luong_api(self):
        c, d = self.call("POST", "/api/trich_xuat")
        luot = d["luot"]
        for f in (self.docx, self.tsv):
            c, d = self.call("POST", f"/api/trich_xuat/{luot}/tep?ten={urllib.parse.quote(os.path.basename(f))}",
                             raw=_doc(f))
            self.assertEqual(c, 200, d)
        c, d = self.call("POST", f"/api/trich_xuat/{luot}/chay", {"ra_lai": True, "chay_lai": True})
        self.assertEqual(c, 200, d)
        self.assertEqual(d["so_tham_so"], 37)
        for _ in range(100):
            c, s = self.call("GET", f"/api/trich_xuat/{luot}")
            if s["tt"] in ("xong", "loi", "da_dung"):
                break
            time.sleep(0.2)
        self.assertEqual(s["tt"], "xong", s.get("thong_bao"))
        ten = s["hd"][0]["ten"]
        c, kq = self.call("GET", f"/api/trich_xuat/{luot}/hd/{urllib.parse.quote(ten)}")
        self.assertEqual(kq["tom_tat"]["dung_dap_an"], "37/37")
        c, d = self.call("PATCH", f"/api/trich_xuat/{luot}/hd/{ten}/o/TT-22", {"gia_tri": "15 ngày làm việc (sửa)"})
        self.assertEqual(d["trang_thai"], "Đã sửa tay, chưa xác nhận")
        self.assertFalse(d["da_xac_nhan"])
        self.assertEqual(d["gia_tri_ai"], "15 ngày làm việc")
        c, d = self.call("PATCH", f"/api/trich_xuat/{luot}/hd/{ten}/o/TT-22", {"xac_nhan": True})
        self.assertEqual(d["trang_thai"], "Đã sửa tay, đã xác nhận")
        c, d = self.call("PATCH", f"/api/trich_xuat/{luot}/hd/{ten}/o/TT-22", {"gia_tri": ""})
        self.assertEqual(c, 400)
        c, d = self.call("POST", f"/api/trich_xuat/{luot}/hd/{ten}/nap_csdl", {})
        self.assertEqual(c, 409)                                   # còn 36 tham số chưa xác nhận
        self.assertEqual(len(d["chi_tiet"]["chua_xac_nhan"]), 36)
        c, d = self.call("POST", f"/api/trich_xuat/{luot}/hd/{ten}/nap_csdl", {"van_nap": True})
        self.assertEqual(c, 200, d)
        self.assertEqual(d["trang_thai"], "Đã thêm vào CSDL")
        ma_hd = d["ma_hd"]
        import csdl_hop_dong as cs
        con = cs.mo_csdl(os.environ["HD_CSDL"])
        r = con.execute("SELECT * FROM tham_so_nguon WHERE ma_hd = ? AND ma_ts = 'TT-22'", (ma_hd,)).fetchone()
        self.assertEqual((r["gia_tri_ai"], r["gia_tri"], r["da_sua_tay"], r["da_xac_nhan"], r["model"]),
                         ("15 ngày làm việc", "15 ngày làm việc (sửa)", 1, 1, "qwen3:8b"))
        self.assertEqual(len(json.loads(r["lich_su"])), 2)
        self.assertTrue(r["sha1_file"])
        r2 = con.execute("SELECT * FROM tham_so_nguon WHERE ma_hd = ? AND ma_ts = 'TT-02'", (ma_hd,)).fetchone()
        self.assertEqual(r2["da_xac_nhan"], 0)
        with self.assertRaises(Exception):                         # bảng nguồn gốc bị khoá, không sửa tay được
            con.execute("UPDATE tham_so_nguon SET gia_tri = 'x' WHERE ma_hd = ?", (ma_hd,))
        con.close()
        c, d = self.call("POST", f"/api/hop_dong/{ma_hd}/tham_so/TT-02/xac_nhan", {})
        self.assertTrue(d["da_xac_nhan"])
        c, d = self.call("GET", f"/api/hop_dong/{ma_hd}")
        t02 = [x for x in d["tham_so"] if x["ma_ts"] == "TT-02"][0]
        self.assertEqual(t02["trang_thai"], "Đã xác nhận")
        self.assertEqual(t02["nguon_trich"]["da_xac_nhan"], 1)
        c, d = self.call("GET", "/api/hop_dong")
        self.assertEqual(d["ds"][0]["so_hd"], "15/2026/HĐXD/MA-TN")
        c, d = self.call("GET", f"/api/hop_dong/{d['ds'][0]['ma_hd']}")
        self.assertEqual({x["ma_ts"]: x["gia_tri"] for x in d["tham_so"]}["TT-22"], "15 ngày làm việc (sửa)")
        c, b = self.call("GET", s["tai"]["tong_hop_xlsx"])
        self.assertEqual(c, 200)
        self.assertTrue(b.startswith(b"PK"))
        c, d = self.call("GET", "/api/trich_xuat")
        self.assertIn(luot, [x["luot"] for x in d["ds"]])

    def test_bao_mat(self):
        c, _ = self.call("POST", "/api/trich_xuat", headers={"X-HD": ""})
        self.assertEqual(c, 403)
        c, _ = self.call("GET", "/api/he_thong", headers={"Host": "evil.example"})
        self.assertEqual(c, 403)
        c, _ = self.call("GET", "/api/he_thong", headers={"Origin": "http://evil.example"})
        self.assertEqual(c, 403)
        c, _ = self.call("GET", "/tai/../../etc/passwd")
        self.assertEqual(c, 404)
        c, d = self.call("POST", "/api/trich_xuat")
        c, d = self.call("POST", f"/api/trich_xuat/{d['luot']}/tep?ten=..%2F..%2Fx.exe", raw=b"MZ")
        self.assertEqual(c, 400)

    def test_cai_dat_va_khoa(self):
        c, d = self.call("POST", "/api/cai_dat", {"may_ai": {"ip": "khong hop le!"}})
        self.assertEqual(c, 400)
        c, d = self.call("POST", "/api/cai_dat/khoa", {"nha_cung_cap": "anthropic", "khoa": "sk-ant-abcdefgh1234"})
        self.assertEqual(d["bon_ky_tu_cuoi"], "1234")
        c, d = self.call("GET", "/api/cai_dat")
        self.assertNotIn("sk-ant-abcdefgh1234", json.dumps(d))
        cfg = json.loads(ch.FILE_CAU_HINH.read_text(encoding="utf-8"))
        self.assertNotIn("sk-ant", json.dumps(cfg))
        c, d = self.call("DELETE", "/api/cai_dat/khoa/anthropic")
        self.assertFalse(d["co_khoa"])

    def test_nhap_boq(self):
        import openpyxl
        c, d = self.call("POST", "/api/trich_xuat")
        luot = d["luot"]
        self.call("POST", f"/api/trich_xuat/{luot}/tep?ten=HD_BOQ.docx", raw=_doc(self.docx))
        self.call("POST", f"/api/trich_xuat/{luot}/chay", {"ra_lai": False, "chay_lai": True})
        for _ in range(100):
            c, s = self.call("GET", f"/api/trich_xuat/{luot}")
            if s["tt"] in ("xong", "loi"):
                break
            time.sleep(0.2)
        ten = s["hd"][0]["ten"]
        c, d = self.call("POST", f"/api/trich_xuat/{luot}/hd/{ten}/nap_csdl", {"van_nap": True})
        ma_hd = d["ma_hd"]                                           # (có thể đã nạp ở test khác — vẫn chưa có BOQ)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOQ"
        ws.append(["BẢNG KHỐI LƯỢNG"])
        ws.append(["STT", "Tên công việc", "Đơn vị", "Khối lượng", "Đơn giá", "Thành tiền"])
        ws.append(["A", "PHẦN ĐƯỜNG", None, None, None, None])
        ws.append([1, "Bê tông mặt đường", "m3", 100, 20000000, 2000000000])
        ws.append([2, "Hoàn thiện", "gói", 1, 2629629630, 2629629630])
        ws.append([None, "Cộng", None, None, None, 4629629630])
        p = os.path.join(_thu_muc("boq"), "BOQ.xlsx")
        wb.save(p)
        c, d = self.call("POST", "/api/boq/tai_len?ten=BOQ.xlsx", raw=_doc(p))
        self.assertEqual(c, 200, d)
        g = d["goi_y"]
        self.assertEqual((g["sheet"], g["hang_tieu_de"]), ("BOQ", 2))
        self.assertEqual(g["cot"], {"stt": "A", "ten": "B", "dvt": "C", "kl": "D", "don_gia": "E", "thanh_tien": "F"})
        body = {"tep": d["tep"], "sheet": "BOQ", "hang_tieu_de": 2, "cot": g["cot"], "ma_hd": ma_hd}
        c, k = self.call("POST", "/api/boq/kiem_tra", body)
        self.assertEqual((k["so_dong"], k["ket_luan"], k["chan"]), (2, "ĐẠT", []))
        c, k2 = self.call("POST", "/api/boq/kiem_tra", {**body, "cot": {**g["cot"], "kl": "F"}})
        self.assertEqual(c, 400)                                     # một cột dùng cho 2 trường
        c, r = self.call("POST", "/api/boq/ghi", body)
        self.assertEqual((c, r["so_dong"]), (200, 2), r)
        c, b = self.call("GET", f"/api/hop_dong/{ma_hd}/boq")
        self.assertTrue(b["khop"])
        self.assertEqual([x["ma_hm"] for x in b["dong"]], ["HM0001", "HM0002"])
        self.assertEqual(b["dong"][0]["nhom"], "PHẦN ĐƯỜNG")
        c, r = self.call("POST", "/api/boq/ghi", body)
        self.assertEqual(c, 409)                                     # đã có BOQ gốc → phải có lý do

    def test_nhap_boq_word(self):                # chạy sau test_nhap_boq (đã có hợp đồng 5 tỷ)
        c, ds = self.call("GET", "/api/hop_dong")
        hd = [h for h in ds["ds"] if h["so_hd"] == "15/2026/HĐXD/MA-TN"]
        if not hd:
            self.skipTest("chưa có hợp đồng mẫu trong CSDL")
        p = tao_boq_word(os.path.join(_thu_muc("boqw"), "BOQ goi 1.docx"))
        c, d = self.call("POST", "/api/boq/tai_len?ten=BOQ%20goi%201.docx", raw=_doc(p))
        self.assertEqual(c, 200, d)
        self.assertEqual((d["ten"], d["nguon"]["loai"], d["nguon"]["so_bang"]), ("BOQ goi 1.docx", "docx", 1))
        g = d["goi_y"]
        body = {"tep": d["tep"], "sheet": g["sheet"], "hang_tieu_de": g["hang_tieu_de"], "cot": g["cot"],
                "ma_hd": hd[0]["ma_hd"]}
        c, k = self.call("POST", "/api/boq/kiem_tra", body)
        self.assertEqual((c, k["so_dong"], k["tong_truoc_vat"], k["ket_luan"]), (200, 2, 4629629630, "ĐẠT"), k)
        ch.luu_cau_hinh({"ocr": {"che_do": "tat"}})
        c, d = self.call("POST", "/api/boq/tai_len?ten=x.pdf", raw=b"%PDF-1.4 scan")
        ch.luu_cau_hinh({"ocr": {"che_do": "tu_dong"}})
        self.assertEqual(c, 400)                     # OCR tắt → BOQ PDF báo rõ cần OCR
        self.assertIn("OCR", d["error"] if isinstance(d.get("error"), str) else json.dumps(d, ensure_ascii=False))
        c, o = self.call("GET", "/api/ocr/trang_thai?lam_moi=1")
        self.assertEqual(c, 200)
        self.assertIn("che_do", o)

    def test_phu_luc_ai(self):                   # chạy sau test_nhap_boq (HĐ mẫu đã có BOQ gốc 2 hạng mục)
        c, ds = self.call("GET", "/api/hop_dong")
        hd = [h for h in ds["ds"] if h["so_hd"] == "15/2026/HĐXD/MA-TN"]
        if not hd:
            self.skipTest("chưa có hợp đồng mẫu trong CSDL")
        ma = hd[0]["ma_hd"]
        c, b = self.call("GET", f"/api/hop_dong/{ma}/boq")
        if len(b["dong"]) != 2:
            self.skipTest("BOQ gốc khác mẫu")
        self.osrv.ctl["phu_luc"] = {"thay_doi": [
            {"ma": "TT-50", "gia_tri_moi": "240 ngày", "dieu": "Điều 2", "ghi_chu": "",
             "trich_dan": "Thời gian thực hiện hợp đồng được gia hạn thành 240 ngày kể từ ngày khởi công."},
            {"ma": "TT-10", "gia_tri_moi": "20%", "dieu": "Điều 2", "ghi_chu": "", "trich_dan": "Câu này không có trong phụ lục"},
            {"ma": "XX-99", "gia_tri_moi": "?", "dieu": "", "ghi_chu": "", "trich_dan": ""}],
            "khac": [{"noi_dung": "Đổi người đại diện bên B", "dieu": "Điều 3", "trich_dan": ""}]}
        p = tao_phu_luc_word(os.path.join(_thu_muc("plai"), "PL01 HĐ 15.2026.docx"))
        c, u = self.call("POST", "/api/phu_luc_ai/tai_len?ten=PL01%20H%C4%90%2015.2026.docx", raw=_doc(p))
        self.assertEqual(c, 200, u)
        c, v = self.call("POST", "/api/phu_luc_ai/chay", {"tep": [u["tep"]]})
        self.assertEqual(c, 200, v)
        v = self._cho_viec(v["id"])
        self.assertEqual(v["tt"], "xong", v.get("loi"))
        id_ = v["ket_qua"]["ds"][0]
        c, kq = self.call("GET", f"/api/phu_luc_ai/{id_}")
        self.assertEqual((kq["ma_hd"], kq["info"]["so_pl"], kq["info"]["ngay_ky"]), (ma, "PL01", "05/05/2026"))
        self.assertEqual(kq["info"]["gt_hd_sau_pl"], 5432000000)
        self.assertEqual(kq["boq"]["che_do"], "toan_bo")
        self.assertEqual([(d["thao_tac"], d["ma_hm"], d["kl"]) for d in kq["boq"]["dong"]], [("THAY", "HM0001", 120.0)])
        kt = {x[0]: x for x in kq["kiem_tra"]}
        self.assertEqual(kt["P10"][1], "ĐẠT", kt["P10"])                  # Σ thay đổi × 1,08 = +432.000.000
        self.assertEqual(kt["P11"][1], "ĐẠT", kt["P11"])
        self.assertIn("khớp gần đúng", json.dumps(kq["kiem_tra"], ensure_ascii=False))
        ts = {r["ma_ts"]: r for r in kq["tham_so"]}
        self.assertEqual(sorted(ts), ["TT-10", "TT-50"])                   # mã lạ bị bỏ
        self.assertEqual((ts["TT-50"]["cu"], ts["TT-50"]["moi"], ts["TT-50"]["kiem_tra_trich"]), ("180 ngày", "240 ngày", ""))
        self.assertIn("không khớp", ts["TT-10"]["kiem_tra_trich"])
        self.assertEqual(kq["khac"][0]["noi_dung"], "Đổi người đại diện bên B")
        c, d = self.call("POST", f"/api/phu_luc_ai/{id_}/nap")
        self.assertEqual(c, 409)                                           # còn tham số chưa xác nhận
        self.assertIn("chưa xác nhận", d["error"] if isinstance(d.get("error"), str) else json.dumps(d, ensure_ascii=False))
        c, kq = self.call("POST", f"/api/phu_luc_ai/{id_}/cap_nhat",
                          {"tham_so": [{"ma_ts": "TT-50", "trang_thai": "Đã xác nhận"}, {"ma_ts": "TT-10", "bo": True}]})
        self.assertEqual(c, 200, kq)
        c, s = self.call("GET", "/api/phu_luc_ai")
        self.assertEqual([x["chua_xac_nhan"] for x in s["ds"] if x["id"] == id_], [0])
        c, r = self.call("POST", f"/api/phu_luc_ai/{id_}/nap")
        self.assertEqual(c, 200, r)
        self.assertEqual(r["nap"]["so_pl"], "PL01")
        c, b = self.call("GET", f"/api/hop_dong/{ma}/boq?ngay=2026-06-01")
        self.assertEqual([x["kl"] for x in b["dong"] if x["ma_hm"] == "HM0001"], [120.0])
        c, b = self.call("GET", f"/api/hop_dong/{ma}/boq?ngay=2026-05-01")
        self.assertEqual([x["kl"] for x in b["dong"] if x["ma_hm"] == "HM0001"], [100.0])   # trước ngày hiệu lực
        c, d = self.call("GET", f"/api/hop_dong/{ma}?ngay=2026-06-01")
        self.assertIn("PL01", [p["so_pl"] for p in d["phu_luc"]])
        c, d = self.call("POST", f"/api/phu_luc_ai/{id_}/nap")
        self.assertEqual(c, 409)                                           # không nạp hai lần
        c, d = self.call("POST", f"/api/phu_luc_ai/{id_}/cap_nhat", {"boq_che_do": "khong"})
        self.assertEqual(c, 409)                                           # đã nạp: khoá sửa

    def test_zy_chung_tu_api(self):      # chạy sau test_luong_api (đã có hợp đồng mẫu)
        c, ds = self.call("GET", "/api/hop_dong")
        hd = [h for h in ds["ds"] if h["so_hd"] == "15/2026/HĐXD/MA-TN"]
        if not hd:
            self.skipTest("chưa có hợp đồng mẫu trong CSDL")
        self.osrv.ctl["chung_tu"] = CT_AI
        f = tao_bo_chung_tu(_thu_muc("ct_api"))
        teps = []
        for k in ("nt", "gn", "cq", "co"):
            c, u = self.call("POST", "/api/chung_tu/tai_len?ten=" + urllib.parse.quote(os.path.basename(f[k])), raw=_doc(f[k]))
            self.assertEqual(c, 200, u)
            teps.append(u["tep"])
        c, d = self.call("POST", "/api/chung_tu/chay", {"tep": teps})
        self.assertEqual(c, 400)                                         # chưa chọn đợt / hợp đồng
        c, v = self.call("POST", "/api/chung_tu/chay", {"tep": teps, "ma_hd": hd[0]["ma_hd"], "ngay_nt": "2026-07-25"})
        self.assertEqual(c, 200, v)
        v = self._cho_viec(v["id"])
        self.assertEqual(v["tt"], "xong", v.get("loi"))
        id_ = v["ket_qua"]["id"]
        c, kq = self.call("GET", f"/api/chung_tu/{id_}")
        self.assertEqual(sorted(x["loai"] for x in kq["tai_lieu"]), ["BB_GN", "BB_NT", "CO", "CQ"])
        codes = {x["code"] for x in kq["phat_hien"]}
        self.assertTrue({"C06", "C07"} <= codes, codes)
        c, s = self.call("GET", "/api/chung_tu")
        self.assertIn(id_, [x["id"] for x in s["ds"]])
        co = next(x for x in kq["tai_lieu"] if x["loai"] == "CO")
        c, kq2 = self.call("POST", f"/api/chung_tu/{id_}/cap_nhat", {"tai_lieu": [{"id": co["id"], "bo": True}]})
        self.assertEqual(c, 200, kq2)
        self.assertTrue(any(x["code"] == "C05" and "CO" in x["title"] for x in kq2["phat_hien"]))   # bỏ CO → thiếu CO
        c, d = self.call("DELETE", f"/api/chung_tu/{id_}")
        self.assertEqual(c, 200)

    def _cho_viec(self, id_):
        for _ in range(150):
            c, v = self.call("GET", f"/api/viec/{id_}")
            if v["tt"] not in ("cho", "dang_chay"):
                return v
            time.sleep(0.2)
        self.fail("việc chạy quá lâu")

    def test_zz_kiem_tra_api(self):          # chạy sau test_luong_api (đã có hợp đồng trong CSDL)
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tong hop"
        ws.append(["STT", "Nội dung", "Giá trị"])
        ws.append([1, "Giá trị hoàn thành", 1000000])
        ws.append([2, "Giữ lại 5%", "=ROUND(C2*5%,0)"])
        ws.append([3, "Giá trị đề nghị thanh toán kỳ này", "=C2-C3"])
        p = os.path.join(_thu_muc("kt"), "tv.xlsx")
        wb.save(p)
        c, v = self.call("POST", "/api/toan_ven?ten=tv.xlsx", raw=_doc(p))
        self.assertEqual(c, 200, v)
        v = self._cho_viec(v["id"])
        self.assertEqual(v["tt"], "xong", v.get("loi"))
        kq = v["ket_qua"]
        self.assertEqual(len(kq["bang_k"]), 8)
        c, ds = self.call("GET", "/api/kiem_tra/toan_ven")
        self.assertIn(kq["ma"], [x["ma"] for x in ds["ds"]])
        c, d = self.call("GET", f"/api/kiem_tra/toan_ven/{kq['ma']}")
        self.assertEqual((c, d["ma"]), (200, kq["ma"]))
        c, d = self.call("GET", "/api/kiem_tra/toan_ven/khong-co")
        self.assertEqual(c, 404)
        # kiểm tra đợt: route nhận đủ tham số (ngày nghiệm thu bắt buộc), lỗi file báo qua việc nền
        c, ds = self.call("GET", "/api/hop_dong")
        self.assertTrue(ds["ds"])
        if ds["ds"]:
            ma = ds["ds"][0]["ma_hd"]
            c, d = self.call("POST", f"/api/hop_dong/{ma}/kiem_dot?ten=tv.xlsx", raw=_doc(p))
            self.assertEqual(c, 400)
            c, v = self.call("POST", f"/api/hop_dong/{ma}/kiem_dot?ten=tv.xlsx&ngay_nghiem_thu=2026-07-25&dot=1",
                             raw=_doc(p))
            self.assertEqual(c, 200, v)
            v = self._cho_viec(v["id"])
            self.assertEqual(v["tt"], "loi")
            self.assertIn("bảng chi tiết", v["loi"])
        c, d = self.call("POST", "/api/kiem_tra/kiem_tra_dot/khong-co/nap", {"dot": 1})
        self.assertEqual(c, 404)

    def test_tham_so(self):
        c, d = self.call("GET", "/api/tham_so")
        self.assertEqual(len(d["rows"]), 37)

    def test_chua_xac_nhan_khong_nap(self):
        c, d = self.call("POST", "/api/trich_xuat")
        luot = d["luot"]
        self.call("POST", f"/api/trich_xuat/{luot}/tep?ten=HD_GIA_LAP.docx", raw=_doc(self.docx))
        self.osrv.ctl["sai_lan_dau"] = {"TT-04"}
        self.call("POST", f"/api/trich_xuat/{luot}/chay", {"ra_lai": False, "chay_lai": True})
        for _ in range(100):
            c, s = self.call("GET", f"/api/trich_xuat/{luot}")
            if s["tt"] in ("xong", "loi"):
                break
            time.sleep(0.2)
        ten = s["hd"][0]["ten"]
        c, d = self.call("POST", f"/api/trich_xuat/{luot}/hd/{ten}/nap_csdl", {})
        self.assertEqual(c, 409)
        self.assertIn("TT-04", d["chi_tiet"]["chua_xac_nhan"])


if __name__ == "__main__":
    unittest.main()
