"""AI-2a: cổng AI dùng chung — chỉ dữ liệu DEMO, không mạng thật, không đọc .env.

Local AI giả qua ``transport`` của ``ai_cuc_bo``; Mask file v2 giả và nhà cung cấp Cloud giả là máy chủ HTTP trên
127.0.0.1 (cổng ngẫu nhiên). Khóa API và khóa Mask là chuỗi DEMO do test tự đặt.
"""
from __future__ import annotations

import json
import logging
import re
import socket
import tempfile
import threading
import traceback
import unittest
from contextlib import ExitStack, contextmanager
from dataclasses import fields
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

from kho_tri_thuc.tri_thuc import ai_cuc_bo
from kho_tri_thuc.tri_thuc import cong_ai as ca

KHOA_CLOUD = "sk-ant-DEMO-khoa-bi-mat-0123456789abcdef"
KHOA_MASK = "DEMOmaskKHOAbimat_0123456789abcdefXYZ"
VAN_BAN = ("Hợp đồng DEMO số HĐ-DEMO-01 ký ngày 15/03/2026.\n"
           "Bên B: Công ty TNHH DEMO Beta, mã số thuế 0109999999.\n"
           "Giá trị hợp đồng: 1.250.000.000 đồng.")
DINH_DANH = (("Công ty TNHH DEMO Beta", "CONG_TY"), ("0109999999", "MA_SO_THUE"), ("HĐ-DEMO-01", "HOP_DONG"))
BI_MAT = ("Công ty TNHH DEMO Beta", "0109999999", "HĐ-DEMO-01")
TRUONG = ("ben_b", "gia_tri_hop_dong")
LOCAL_CFG = {"enabled": True, "url": "http://127.0.0.1:1234/v1/chat/completions", "model": "demo-local",
             "timeout_seconds": 2}


def tra_loi_json(do_tin_cay=0.95, ben_b_trich="Bên B: Công ty TNHH DEMO Beta, mã số thuế 0109999999."):
    truong = [{"ten": "ben_b", "gia_tri": "Công ty TNHH DEMO Beta", "trich_dan": ben_b_trich},
              {"ten": "gia_tri_hop_dong", "gia_tri": "1.250.000.000 đồng",
               "trich_dan": "Giá trị hợp đồng: 1.250.000.000 đồng."}]
    return json.dumps({"truong": truong, "do_tin_cay": do_tin_cay}, ensure_ascii=False)


LOCAL_CHAC = tra_loi_json(0.95)
LOCAL_KHONG_CHAC = tra_loi_json(0.40)


def yeu_cau(loai="BOC_TACH_HOP_DONG", van_ban=VAN_BAN, dinh_danh=DINH_DANH):
    return ca.YeuCauAI(loai, van_ban, "Trích bên B và giá trị hợp đồng DEMO.", TRUONG, dinh_danh)


def cloud_tra_loi(user: str, sua_trich_dan: bool = False) -> str:
    """Model Cloud giả: chép lại các dòng của văn bản ĐÃ CHE làm trích dẫn (kèm bí danh)."""
    dong_b = next(line for line in user.splitlines() if line.startswith("Bên B:"))
    bi_danh = re.search(r"\[[A-Z_]+_\d{3}\]", dong_b).group()
    dong_gt = next(line for line in user.splitlines() if line.startswith("Giá trị hợp đồng:"))
    data = {"truong": [{"ten": "ben_b", "gia_tri": bi_danh,
                        "trich_dan": dong_b.replace("Bên B", "Bên Bán") if sua_trich_dan else dong_b},
                       {"ten": "gia_tri_hop_dong", "gia_tri": "1.250.000.000 đồng", "trich_dan": dong_gt}],
            "do_tin_cay": 0.9}
    return "```json\n" + json.dumps(data, ensure_ascii=False) + "\n```"


@contextmanager
def may_chu(xu_ly):
    """Máy chủ HTTP giả trên 127.0.0.1; ghi lại method, đường dẫn, header, thân yêu cầu."""
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def _do(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            body = json.loads(raw) if raw else None
            calls.append({"method": self.command, "path": self.path, "body": body,
                          "headers": {k.lower(): v for k, v in self.headers.items()}})
            status, payload = xu_ly(self.command, self.path, self.headers, body)
            data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = _do

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class MaskGia:
    """Mask file v2 (chế độ API 2.7.x) giả: che bằng định danh đã khai, mở che theo lượt."""

    def __init__(self, *, khoa=KHOA_MASK, danh_muc="da_mo", che_status=200, che_ma_loi="", gui_duoc=True,
                 con_sot=(), che_danh_muc="da_mo", ro_ri=False, mo_che_status=200, che_hong=False):
        self.khoa, self.danh_muc, self.che_status, self.che_ma_loi = khoa, danh_muc, che_status, che_ma_loi
        self.gui_duoc, self.con_sot, self.che_danh_muc, self.ro_ri = gui_duoc, list(con_sot), che_danh_muc, ro_ri
        self.mo_che_status, self.che_hong = mo_che_status, che_hong
        self.luot: dict[str, dict] = {}

    def xu_ly(self, method, path, headers, body):
        if headers.get("Authorization") != f"Bearer {self.khoa}":
            return 401, {"ma_loi": "khong_xac_thuc", "thong_bao": "sai khóa " + str(headers.get("Authorization")),
                         "gui_duoc": False}
        if path == "/api/v1/trang-thai":
            return 200, {"dich_vu": "local-mask", "phien_ban": "2.7.1", "danh_muc": self.danh_muc,
                         "mo_cho_api": self.danh_muc == "da_mo", "canh_bao": "", "so_luot_dang_giu": len(self.luot)}
        if path == "/api/v1/che":
            if self.che_hong:
                return 200, b"khong phai json"
            if self.che_status != 200:
                return self.che_status, {"ma_loi": self.che_ma_loi, "thong_bao": "DEMO", "gui_duoc": False,
                                         "con_sot": [{"cum": "DEMO cụm sót bí mật", "so_lan": 1}], "so_con_sot": 1}
            text, mapping = body["van_ban"], {}
            for i, item in enumerate(body["dinh_danh_da_biet"], 1):
                value, nhom = (item["gia_tri"], item["nhom"]) if isinstance(item, dict) else (item, "KHAC")
                token = f"[{nhom}_{i:03d}]"
                if not self.ro_ri and value in text:
                    text = text.replace(value, token)
                    mapping[token] = value
            ma_luot = f"luot{len(self.luot) + 1:04d}DEMO"
            self.luot[ma_luot] = mapping
            return 200, {"ma_luot": ma_luot, "van_ban_da_che": text, "con_sot": self.con_sot,
                         "gui_duoc": self.gui_duoc, "danh_muc": self.che_danh_muc, "het_han_sau_giay": 1800}
        if path == "/api/v1/mo-che":
            mapping = self.luot.get(body["ma_luot"])
            if self.mo_che_status != 200 or mapping is None:
                return 404, {"ma_loi": "luot_het_han", "thong_bao": "DEMO", "gui_duoc": False}
            text = re.sub(r"\[[A-Z][A-Z0-9_]{2,49}\]", lambda m: mapping.get(m.group(), m.group()), body["van_ban"])
            if body.get("ket_thuc_luot"):
                self.luot.pop(body["ma_luot"], None)
            return 200, {"van_ban": text, "so_cho_mo": 0, "bi_danh_khong_ro": [], "luot_con_giu": False}
        return 404, {"ma_loi": "khong_co_duong_dan", "gui_duoc": False}


class CloudGia:
    """Messages API giả (dạng Anthropic)."""

    def __init__(self, tra_loi=cloud_tra_loi, *, status=200, stop_reason="end_turn", model="claude-opus-5-5",
                 loi_body=None):
        self.tra_loi, self.status, self.stop_reason, self.model, self.loi_body = (
            tra_loi, status, stop_reason, model, loi_body)

    def xu_ly(self, method, path, headers, body):
        if self.status != 200:
            return self.status, self.loi_body or {"type": "error", "error": {"type": "api_error", "message": "DEMO"}}
        text = self.tra_loi(body["messages"][0]["content"])
        return 200, {"id": "msg_DEMO", "type": "message", "role": "assistant", "model": self.model,
                     "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": text}],
                     "stop_reason": self.stop_reason, "usage": {"input_tokens": 1200, "output_tokens": 300}}


def cong_dong() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class CongAICase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tep_khoa = Path(self.tmp.name) / "mask-api.key"
        self.tep_khoa.write_text(KHOA_MASK, encoding="utf-8")
        cache = patch.dict(ai_cuc_bo._CONNECTION_FAILURES, {}, clear=True)
        cache.start()
        self.addCleanup(cache.stop)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)

    def mo(self, mask: MaskGia | None = None, cloud: CloudGia | None = None):
        mask_url, mask_calls = self.stack.enter_context(may_chu((mask or MaskGia()).xu_ly))
        cloud_url, cloud_calls = self.stack.enter_context(may_chu((cloud or CloudGia()).xu_ly))
        return mask_url, mask_calls, cloud_url, cloud_calls

    def cong(self, mask_url, cloud_url, *, local_tra_loi=LOCAL_KHONG_CHAC, local=LOCAL_CFG, cloud_bat=True,
             env=None, cai_dat=None, bo_ghi=None, kiem_xac_suat=None, transport=None):
        self.local_calls = []

        def local_transport(url, body):
            self.local_calls.append(json.loads(body))
            if isinstance(local_tra_loi, Exception):
                raise local_tra_loi
            return local_tra_loi

        settings = {"local_ai": dict(local), "cong_ai": {"cloud_bat": cloud_bat, "mask_url": mask_url,
                                                         "mask_tep_khoa": str(self.tep_khoa), "mask_timeout_giay": 3,
                                                         **(cai_dat or {})}}
        nha = ca.NhaCungCapAnthropic(url=cloud_url + "/v1/messages", proxy_moi_truong=False)
        return ca.CongAI(settings, bo_ghi=bo_ghi or ca.BoGhiBoNho(), nha_cung_cap=nha,
                         local_transport=transport or local_transport,
                         moi_truong={"ANTHROPIC_API_KEY": KHOA_CLOUD} if env is None else env,
                         kiem_xac_suat=kiem_xac_suat)

    def dong(self, gate, duong):
        return [b for b in gate.bo_ghi.ban_ghi if b.duong == duong]


class BangLoaiViecVaCaiDatTests(unittest.TestCase):
    def test_bang_loai_viec_khai_bao_mot_cho(self):
        self.assertGreaterEqual(len(ca.LOAI_VIEC), 3)
        for ma, loai in ca.LOAI_VIEC.items():
            with self.subTest(ma=ma):
                self.assertEqual(ma, loai.ma)
                self.assertRegex(ma, r"^[A-Z][A-Z_]+$")
                self.assertTrue(loai.mo_ta.strip())
                self.assertTrue(0 <= loai.nguong_tin_cay <= 1)
        self.assertFalse(ca.LOAI_VIEC["PHAN_TICH_TRA_LOI_ZALO"].duoc_dung_cloud)
        with self.assertRaisesRegex(ValueError, "chưa khai báo"):
            ca.loai_viec("KHONG_CO")

    def test_cai_dat_mac_dinh_tat_cloud_va_khong_co_khoa(self):
        cfg = ca.cong_ai_settings({})
        self.assertFalse(cfg["cloud_bat"])
        self.assertEqual("", cfg["loi"])
        self.assertEqual("http://127.0.0.1:8017", cfg["mask_url"])
        self.assertEqual("ANTHROPIC_API_KEY", cfg["bien_khoa_api"])
        self.assertFalse(ca.cong_ai_settings({"cong_ai": {"cloud_bat": "true"}})["cloud_bat"])  # chỉ True thật

    def test_dia_chi_mask_chi_nhan_127_0_0_1(self):
        for url in ("http://localhost:8017", "http://127.0.0.2:8017", "https://127.0.0.1:8017", "http://127.0.0.1",
                    "http://127.0.0.1:8017/api", "http://user@127.0.0.1:8017", "http://127.0.0.1:8017?x=1",
                    "http://[::1]:8017", "http://10.0.0.5:8017", "http://127.0.0.1:8017\n"):
            with self.subTest(url=url):
                cfg = ca.cong_ai_settings({"cong_ai": {"mask_url": url}})
                self.assertIn("127.0.0.1", cfg["loi"])
                with self.assertRaises(ValueError):
                    ca.MaskV2(url, "")
        self.assertEqual("http://127.0.0.1:8019", ca.mask_base_url("http://127.0.0.1:8019/"))

    def test_bien_khoa_va_bang_gia(self):
        self.assertTrue(ca.cong_ai_settings({"cong_ai": {"bien_khoa_api": "PATH"}})["loi"])
        cfg = ca.cong_ai_settings({"cong_ai": {"bang_gia": {"demo-model": {"vao": 1, "ra": 2}, "hong": {"vao": "x"}}}})
        self.assertEqual({"vao": 1.0, "ra": 2.0}, cfg["bang_gia"]["demo-model"])
        self.assertNotIn("hong", cfg["bang_gia"])
        self.assertAlmostEqual(0.0108, ca.chi_phi_uoc_usd(cfg["bang_gia"], "claude-opus-5-5", 1200, 300))
        self.assertIsNone(ca.chi_phi_uoc_usd(cfg["bang_gia"], "model-khong-co-gia", 1200, 300))
        self.assertIsNone(ca.chi_phi_uoc_usd(cfg["bang_gia"], "claude-opus-5-5", None, 300))
        self.assertTrue(ca.cong_ai_settings({"cong_ai": {"nha_cung_cap": "openai"}})["loi"])  # phải chọn model

    def test_dinh_danh_so_luon_khai_nhom(self):
        out = ca.chuan_dinh_danh(["001.234.567.890", ("0109999999", "ma_so_thue"), "DEMO Gamma",
                                  {"gia_tri": "123 4567", "nhom": "KHAC"}, ("12", "")])
        self.assertEqual([{"gia_tri": "001.234.567.890", "nhom": "GIAY_TO"},
                          {"gia_tri": "0109999999", "nhom": "MA_SO_THUE"}, "DEMO Gamma",
                          {"gia_tri": "123 4567", "nhom": "GIAY_TO"}, "12"], out)
        with self.assertRaises(ValueError):
            ca.chuan_dinh_danh([("DEMO", "nhóm sai")])
        with self.assertRaises(ValueError):
            ca.chuan_dinh_danh([object()])

    def test_chi_mot_noi_goi_thang_nha_cung_cap_cloud(self):
        src = Path(ca.__file__).resolve().parents[1]
        cho_phep = {"tri_thuc/cong_ai.py",
                    "m4/review_goc/trich_xuat/cloud.py"}  # cloud.py của engine #6: khóa từ AI-0, bỏ ở AI-3
        thay = {p.relative_to(src).as_posix() for p in src.rglob("*.py")
                if re.search(r"api\.(anthropic|openai)\.com", p.read_text(encoding="utf-8", errors="replace"))}
        self.assertTrue(thay <= cho_phep, sorted(thay - cho_phep))
        self.assertIn("tri_thuc/cong_ai.py", thay)
        self.assertIn("NGOẠI LỆ DUY NHẤT", ca.__doc__.upper().replace("**", ""))


class DanhGiaTrichDanTests(unittest.TestCase):
    loai = ca.LOAI_VIEC["BOC_TACH_HOP_DONG"]

    def dg(self, data, kiem_tra=None):
        return ca.danh_gia(data, yeu_cau(), self.loai, ca.DUONG_LOCAL, kiem_tra)

    def test_trich_dan_nguyen_van_gop_khoang_trang_thi_dat(self):
        data = json.loads(tra_loi_json(0.9, "Bên B:   Công ty TNHH DEMO Beta,\n mã số thuế 0109999999."))
        result = self.dg(data)
        self.assertTrue(result.chac, result.ly_do)
        self.assertEqual({"ben_b", "gia_tri_hop_dong"}, set(result.truong))
        self.assertTrue(result.trich_dan_hop_le)

    def test_trich_dan_sai_thieu_hoac_gia_tri_ngoai_trich_dan_bi_loai(self):
        for trich, ma in (("Bên B: Công ty TNHH DEMO Bêta, mã số thuế 0109999999.", "TRICH_DAN_SAI"),
                          ("", "THIEU_TRICH_DAN"),
                          ("Giá trị hợp đồng: 1.250.000.000 đồng.", "GIA_TRI_NGOAI_TRICH_DAN")):
            with self.subTest(ma=ma):
                result = self.dg(json.loads(tra_loi_json(0.99, trich)))
                self.assertNotIn("ben_b", result.truong)
                self.assertEqual(ma, result.bi_loai["ben_b"])
                self.assertIn(ma, result.ly_do)
                self.assertIn("THIEU_TRUONG", result.ly_do)
                self.assertFalse(result.chac)
                self.assertFalse(result.trich_dan_hop_le)

    def test_dinh_dang_sai_nguong_va_kiem_python(self):
        self.assertEqual(("PHAN_HOI_KHONG_HOP_LE",), self.dg(ca.doc_json_tra_loi("không phải JSON")).ly_do)
        data = json.loads(LOCAL_CHAC)
        data.pop("do_tin_cay")
        self.assertIn("DUOI_NGUONG", self.dg(data).ly_do)
        self.assertIn("DUOI_NGUONG", self.dg(json.loads(LOCAL_KHONG_CHAC)).ly_do)
        result = self.dg(json.loads(LOCAL_CHAC), kiem_tra=lambda truong, goc: ["gia_tri_hop_dong"])
        self.assertEqual("KHONG_QUA_KIEM_PYTHON", result.bi_loai["gia_tri_hop_dong"])
        self.assertNotIn("gia_tri_hop_dong", result.truong)
        crash = self.dg(json.loads(LOCAL_CHAC), kiem_tra=Mock(side_effect=RuntimeError("DEMO")))
        self.assertEqual({}, crash.truong)
        self.assertIn("KHONG_CO_TRUONG", crash.ly_do)


class LuongLocalCloudTests(CongAICase):
    def test_local_dat_thi_khong_goi_mask_hay_cloud(self):
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url, local_tra_loi=LOCAL_CHAC)
        result = gate.goi(yeu_cau())
        self.assertEqual(ca.MUC_VANG, result.muc)  # kết quả có LLM tối đa Vàng, kể cả khi Local chắc
        self.assertEqual("LOCAL", result.duong)
        self.assertEqual({"ben_b", "gia_tri_hop_dong"}, set(result.truong))
        self.assertEqual([], mask_calls)
        self.assertEqual([], cloud_calls)
        self.assertEqual(["LOCAL"], [b.duong for b in gate.bo_ghi.ban_ghi])
        self.assertEqual("DAT", gate.bo_ghi.ban_ghi[0].ket_qua)
        # Local nhận văn bản gốc (máy trong mạng nội bộ), có hướng dẫn định dạng.
        prompt = self.local_calls[0]["messages"][1]["content"]
        self.assertIn("Công ty TNHH DEMO Beta", prompt)
        self.assertIn("trich_dan", prompt)

    def test_local_tat_va_cloud_tat_khong_goi_gi_va_bao_ro(self):
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url, local={}, cloud_bat=False)
        result = gate.goi(yeu_cau())
        self.assertEqual(ca.MUC_DO, result.muc)
        self.assertEqual({}, result.truong)
        self.assertEqual("KHONG", result.duong)
        self.assertEqual(("LOCAL_TAT", "CLOUD_TAT"), result.ly_do)
        self.assertIn("Chưa có kết quả AI", result.thong_bao)
        self.assertIn("Cloud: đường Cloud đang tắt", result.thong_bao)
        self.assertEqual(([], [], []), (mask_calls, cloud_calls, self.local_calls))
        local_row, cloud_row = gate.bo_ghi.ban_ghi
        self.assertEqual(("LOCAL", False, "LOCAL_TAT"), (local_row.duong, local_row.da_gui, local_row.loi))
        self.assertEqual(("CLOUD", False, "CLOUD_TAT", ("LOCAL_TAT",)),
                         (cloud_row.duong, cloud_row.da_gui, cloud_row.ly_do_khong_gui, cloud_row.ly_do_chuyen_cloud))
        status = gate.trang_thai()
        self.assertFalse(status["cloud"]["dung_duoc"])
        self.assertIn("đang tắt", status["cloud"]["thong_bao"])

    def test_cloud_tat_khong_bao_gio_goi_mask_du_local_khong_chac(self):
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url, cloud_bat=False)
        result = gate.goi(yeu_cau())
        self.assertEqual(("VANG", "LOCAL"), (result.muc, result.duong))  # quay về kết quả Local
        self.assertIn("DUOI_NGUONG", result.ly_do)
        self.assertIn("CLOUD_TAT", result.ly_do)
        self.assertIn("Local AI: độ tin cậy dưới ngưỡng", result.thong_bao)
        self.assertEqual(([], []), (mask_calls, cloud_calls))

    def test_local_khong_chac_cloud_bat_che_goi_mo_che(self):
        mask = MaskGia()
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo(mask)
        gate = self.cong(mask_url, cloud_url)
        result = gate.goi(yeu_cau())
        self.assertEqual(["/api/v1/trang-thai", "/api/v1/che", "/api/v1/mo-che"], [c["path"] for c in mask_calls])
        self.assertEqual(1, len(cloud_calls))
        # Cloud chỉ nhận bản đã che: không còn định danh nào.
        sent = cloud_calls[0]["body"]["messages"][0]["content"]
        for value in BI_MAT:
            self.assertNotIn(value, sent)
        self.assertIn("[CONG_TY_001]", sent)
        self.assertIn("trich_dan", sent)
        # Định danh khai kèm nhóm; mở che kết thúc lượt.
        che = mask_calls[1]["body"]
        self.assertIn({"gia_tri": "0109999999", "nhom": "MA_SO_THUE"}, che["dinh_danh_da_biet"])
        mo_che = mask_calls[2]["body"]
        self.assertTrue(mo_che["ket_thuc_luot"])
        self.assertEqual({}, mask.luot)
        # Kết quả: giá trị gốc sau mở che, trích dẫn nguyên văn văn bản gốc, tối đa Vàng.
        self.assertEqual(("VANG", "CLOUD"), (result.muc, result.duong))
        self.assertEqual("Công ty TNHH DEMO Beta", result.truong["ben_b"].gia_tri)
        self.assertEqual("Bên B: Công ty TNHH DEMO Beta, mã số thuế 0109999999.", result.truong["ben_b"].trich_dan)
        self.assertEqual("CLOUD", result.truong["ben_b"].nguon)
        self.assertEqual(("DUOI_NGUONG",), result.ly_do)
        self.assertIn("Cloud AI (qua Mask file v2)", result.thong_bao)

    def test_local_khong_chay_thi_dung_cloud(self):
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url, local_tra_loi=ConnectionRefusedError("DEMO offline"))
        result = gate.goi(yeu_cau())
        self.assertEqual(("VANG", "CLOUD"), (result.muc, result.duong))
        self.assertEqual("LOCAL_KHONG_CHAY", result.ly_do[0])
        self.assertEqual(1, len(cloud_calls))
        self.assertEqual(("LOCAL_KHONG_CHAY",), self.dong(gate, "CLOUD")[0].ly_do_chuyen_cloud)
        # Khoảng nghỉ 15 giây dùng chung với Local AI: lượt sau không gọi lại máy AI.
        gate.goi(yeu_cau())
        self.assertEqual(1, len(self.local_calls))

    def test_khong_gui_khi_mask_khong_cho(self):
        cases = (
            ("con_sot_khong_rong", dict(con_sot=[{"cum": "DEMO cụm sót bí mật", "so_lan": 1}]), "MASK_CON_SOT"),
            ("http_422", dict(che_status=422, che_ma_loi="con_sot"), "MASK_CON_SOT"),
            ("http_423", dict(che_status=423, che_ma_loi="danh_muc_khoa"), "MASK_DANH_MUC_KHOA"),
            ("trang_thai_khoa", dict(danh_muc="khoa"), "MASK_DANH_MUC_KHOA"),
            ("trang_thai_chua_co", dict(danh_muc="chua_co"), "MASK_DANH_MUC_CHUA_CO"),
            ("gui_duoc_false", dict(gui_duoc=False), "MASK_KHONG_CHO_GUI"),
            ("che_tra_danh_muc_khac", dict(che_danh_muc="chua_co"), "MASK_DANH_MUC_KHOA"),
            ("sai_khoa_401", dict(khoa="KHOA_KHAC_DEMO_0123456789abcdefghijk"), "MASK_SAI_KHOA"),
            ("api_chua_bat_503", dict(che_status=503, che_ma_loi="api_chua_bat"), "MASK_API_CHUA_BAT"),
            ("phan_hoi_hong", dict(che_hong=True), "MASK_PHAN_HOI_LOI"),
            ("ro_ri_phia_cong", dict(ro_ri=True), "CON_SOT_DINH_DANH"),
        )
        for ten, cfg, ma in cases:
            with self.subTest(ten=ten), ExitStack() as stack:
                mask = MaskGia(**cfg)
                mask_url, mask_calls = stack.enter_context(may_chu(mask.xu_ly))
                cloud_url, cloud_calls = stack.enter_context(may_chu(CloudGia().xu_ly))
                gate = self.cong(mask_url, cloud_url)
                result = gate.goi(yeu_cau())
                self.assertEqual([], cloud_calls)  # không gửi
                self.assertEqual(("VANG", "LOCAL"), (result.muc, result.duong))  # quay về kết quả Local
                self.assertIn(ma, result.ly_do)
                row = self.dong(gate, "CLOUD")[0]
                self.assertEqual((False, ma, "KHONG_GUI"), (row.da_gui, row.ly_do_khong_gui, row.ket_qua))
                self.assertNotIn("DEMO cụm sót bí mật", repr(result) + repr(gate.bo_ghi.ban_ghi))
                if ten.startswith("trang_thai"):
                    self.assertEqual(["/api/v1/trang-thai"], [c["path"] for c in mask_calls])
                if ten == "ro_ri_phia_cong":  # lượt đã che bị bỏ thì dọn bảng ánh xạ trong Mask
                    self.assertEqual("/api/v1/mo-che", mask_calls[-1]["path"])
                    self.assertTrue(mask_calls[-1]["body"]["ket_thuc_luot"])
                    self.assertEqual({}, mask.luot)

    def test_mask_khong_chay_thi_khong_gui(self):
        cloud_url, cloud_calls = self.stack.enter_context(may_chu(CloudGia().xu_ly))
        gate = self.cong(f"http://127.0.0.1:{cong_dong()}", cloud_url, local_tra_loi=OSError("DEMO offline"))
        result = gate.goi(yeu_cau())
        self.assertEqual([], cloud_calls)
        self.assertEqual(("DO", "KHONG"), (result.muc, result.duong))
        self.assertEqual(("LOCAL_KHONG_CHAY", "MASK_KHONG_CHAY"), result.ly_do)
        self.assertIn("Mask file v2 không chạy", result.thong_bao)

    def test_khong_co_khoa_hoac_tep_khoa_mask_coi_nhu_tat(self):
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url, env={})
        result = gate.goi(yeu_cau())
        self.assertIn("CHUA_CO_KHOA_API", result.ly_do)
        self.assertIn("Coi như tắt Cloud", gate.trang_thai()["cloud"]["thong_bao"])
        self.tep_khoa.write_text("ngan", encoding="utf-8")
        gate = self.cong(mask_url, cloud_url)
        self.assertIn("CHUA_CO_KHOA_MASK", gate.goi(yeu_cau()).ly_do)
        self.tep_khoa.unlink()
        self.assertIn("CHUA_CO_KHOA_MASK", gate.goi(yeu_cau()).ly_do)
        self.assertIn("khóa của Mask", gate.trang_thai()["cloud"]["thong_bao"])
        self.assertEqual(([], []), (mask_calls, cloud_calls))

    def test_trang_thai_hoi_mask_khi_can(self):
        mask_url, mask_calls, cloud_url, _ = self.mo(MaskGia(danh_muc="khoa"))
        gate = self.cong(mask_url, cloud_url)
        self.assertTrue(gate.trang_thai()["cloud"]["dung_duoc"])
        self.assertEqual([], mask_calls)
        status = gate.trang_thai(kiem_mask=True)["cloud"]
        self.assertEqual((False, "MASK_DANH_MUC_KHOA"), (status["dung_duoc"], status["ma"]))

    def test_cai_dat_cloud_loi_thi_khong_goi_mang(self):
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url, cai_dat={"mask_url": "http://localhost:8017"})
        result = gate.goi(yeu_cau())
        self.assertIn("CAI_DAT_CLOUD_LOI", result.ly_do)
        self.assertEqual(([], []), (mask_calls, cloud_calls))

    def test_loai_viec_chi_local_va_xml_tho_khong_ra_cloud(self):
        mask_url, mask_calls, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url)
        self.assertIn("LOAI_VIEC_KHONG_DUNG_CLOUD", gate.goi(yeu_cau("CHON_UNG_VIEN")).ly_do)
        xml = ('<?xml version="1.0"?><HDon><DLHDon><NBan><Ten>DEMO</Ten></NBan>'
               '<TgTTTBSo>1250000000</TgTTTBSo></DLHDon></HDon>\n' + VAN_BAN)
        self.assertIn("XML_HOA_DON_THO", gate.goi(yeu_cau(van_ban=xml)).ly_do)
        self.assertEqual(([], []), (mask_calls, cloud_calls))

    def test_trich_dan_sai_sau_mo_che_thi_loai_ket_qua_cloud(self):
        cloud = CloudGia(lambda user: cloud_tra_loi(user, sua_trich_dan=True))
        mask_url, _, cloud_url, cloud_calls = self.mo(cloud=cloud)
        gate = self.cong(mask_url, cloud_url)
        result = gate.goi(yeu_cau())
        self.assertEqual(1, len(cloud_calls))
        self.assertEqual("LOCAL", result.truong["ben_b"].nguon)  # trường Cloud trích sai bị loại, giữ Local
        self.assertEqual("CLOUD", result.truong["gia_tri_hop_dong"].nguon)
        self.assertEqual("LOCAL+CLOUD", result.duong)
        row = self.dong(gate, "CLOUD")[0]
        self.assertEqual((False, 1), (row.trich_dan_hop_le, row.so_truong_bi_loai))
        self.assertIn("TRICH_DAN_SAI", row.ly_do)
        # Local không chạy: chỉ còn kết quả Cloud, trường trích sai không có trong kết quả.
        gate = self.cong(mask_url, cloud_url, local_tra_loi=OSError("DEMO offline"))
        result = gate.goi(yeu_cau())
        self.assertNotIn("ben_b", result.truong)
        self.assertIn("ben_b", result.truong_bi_loai)
        self.assertEqual("VANG", result.muc)

    def test_mo_che_loi_thi_bo_ket_qua_cloud(self):
        mask_url, _, cloud_url, cloud_calls = self.mo(MaskGia(mo_che_status=404))
        gate = self.cong(mask_url, cloud_url)
        result = gate.goi(yeu_cau())
        self.assertEqual(1, len(cloud_calls))
        self.assertEqual("LOCAL", result.duong)
        self.assertIn("MASK_MO_CHE_LOI", result.ly_do)
        self.assertEqual("MASK_MO_CHE_LOI", self.dong(gate, "CLOUD")[0].loi)

    def test_cloud_loi_thi_ket_thuc_luot_va_quay_ve_local(self):
        mask = MaskGia()
        mask_url, mask_calls, cloud_url, _ = self.mo(mask, CloudGia(status=500))
        gate = self.cong(mask_url, cloud_url)
        result = gate.goi(yeu_cau())
        self.assertEqual("LOCAL", result.duong)
        self.assertIn("CLOUD_HTTP_500", result.ly_do)
        self.assertTrue(mask_calls[-1]["body"]["ket_thuc_luot"])
        self.assertEqual({}, mask.luot)
        row = self.dong(gate, "CLOUD")[0]
        self.assertEqual((True, "LOI", "CLOUD_HTTP_500"), (row.da_gui, row.ket_qua, row.loi))

    def test_kiem_xac_suat_mac_dinh_0_va_moc_cho_ai4(self):
        mask_url, _, cloud_url, cloud_calls = self.mo()
        self.cong(mask_url, cloud_url, local_tra_loi=LOCAL_CHAC).goi(yeu_cau())
        self.assertEqual([], cloud_calls)
        chon = Mock(return_value=True)
        gate = self.cong(mask_url, cloud_url, local_tra_loi=LOCAL_CHAC, kiem_xac_suat=chon)
        result = gate.goi(yeu_cau())
        chon.assert_called_once_with(ca.LOAI_VIEC["BOC_TACH_HOP_DONG"])
        self.assertEqual(1, len(cloud_calls))
        self.assertEqual(("KIEM_XAC_SUAT",), self.dong(gate, "CLOUD")[0].ly_do_chuyen_cloud)
        self.assertEqual("VANG", result.muc)


class NhatKyVaKhoaTests(CongAICase):
    TRUONG_NHAT_KY = {
        "ma_yeu_cau", "luc", "loai_viec", "duong", "nha_cung_cap", "model", "da_gui", "so_ky_tu_gui",
        "so_ky_tu_nhan", "token_vao", "token_ra", "thoi_gian_ms", "chi_phi_uoc_usd", "ma_luot_mask",
        "ly_do_chuyen_cloud", "ly_do_khong_gui", "ket_qua", "ly_do", "trich_dan_hop_le", "so_truong_bi_loai", "loi",
        "phap_nhan_id", "viec_id", "de_xuat_id"}

    def test_nhat_ky_du_truong_khong_chua_van_ban(self):
        mask_url, _, cloud_url, cloud_calls = self.mo()
        gate = self.cong(mask_url, cloud_url)
        result = gate.goi(yeu_cau())
        self.assertEqual(self.TRUONG_NHAT_KY, {f.name for f in fields(ca.BanGhiCongAI)})
        local_row, cloud_row = gate.bo_ghi.ban_ghi
        self.assertEqual(result.ma_yeu_cau, local_row.ma_yeu_cau)
        self.assertEqual(local_row.ma_yeu_cau, cloud_row.ma_yeu_cau)
        self.assertEqual(("LOCAL", "local", "demo-local", True, "KHONG_CHAC", ("DUOI_NGUONG",)),
                         (local_row.duong, local_row.nha_cung_cap, local_row.model, local_row.da_gui,
                          local_row.ket_qua, local_row.ly_do))
        self.assertGreater(local_row.so_ky_tu_gui, len(VAN_BAN))
        self.assertGreater(local_row.so_ky_tu_nhan, 0)
        self.assertIsNone(local_row.chi_phi_uoc_usd)
        self.assertEqual(("CLOUD", "anthropic", "claude-opus-5-5", True, "DAT"),
                         (cloud_row.duong, cloud_row.nha_cung_cap, cloud_row.model, cloud_row.da_gui,
                          cloud_row.ket_qua))
        self.assertEqual((1200, 300, 0.0108), (cloud_row.token_vao, cloud_row.token_ra, cloud_row.chi_phi_uoc_usd))
        self.assertTrue(cloud_row.ma_luot_mask)
        self.assertEqual(("DUOI_NGUONG",), cloud_row.ly_do_chuyen_cloud)
        self.assertIsNone(cloud_row.ly_do_khong_gui)
        self.assertTrue(cloud_row.trich_dan_hop_le)
        sent = cloud_calls[0]["body"]
        self.assertEqual(len(sent["system"]) + len(sent["messages"][0]["content"]), cloud_row.so_ky_tu_gui)
        self.assertGreater(cloud_row.so_ky_tu_nhan, 0)
        self.assertGreaterEqual(cloud_row.thoi_gian_ms, 0)
        dump = json.dumps([b.thanh_dict() for b in gate.bo_ghi.ban_ghi], ensure_ascii=False)
        for text in (*BI_MAT, "Bên B", "Giá trị hợp đồng", "1.250.000.000", "[CONG_TY_001]", "do_tin_cay",
                     "Văn bản", KHOA_CLOUD, KHOA_MASK):
            self.assertNotIn(text, dump)

    def test_khoa_khong_xuat_hien_trong_log_ngoai_le_va_ket_qua(self):
        records = []

        class Bat(logging.Handler):
            def emit(self, record):
                records.append(self.format(record))

        handler = Bat(level=logging.DEBUG)
        root = logging.getLogger()
        old_level = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        self.addCleanup(root.removeHandler, handler)
        self.addCleanup(root.setLevel, old_level)
        echo = {"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key " + KHOA_CLOUD}}
        scenarios = (
            ("cloud_401", MaskGia(), CloudGia(status=401, loi_body=echo), "CLOUD_HTTP_401"),
            ("mask_401", MaskGia(khoa="KHOA_KHAC_DEMO_0123456789abcdefghijk"), CloudGia(), "MASK_SAI_KHOA"),
            ("cloud_tu_choi", MaskGia(), CloudGia(stop_reason="refusal"), "CLOUD_TU_CHOI"),
        )
        for ten, mask, cloud, ma in scenarios:
            with self.subTest(ten=ten), ExitStack() as stack:
                mask_url, mask_calls = stack.enter_context(may_chu(mask.xu_ly))
                cloud_url, cloud_calls = stack.enter_context(may_chu(cloud.xu_ly))
                gate = self.cong(mask_url, cloud_url, bo_ghi=Mock(ghi=Mock(side_effect=RuntimeError(KHOA_CLOUD))))
                result = gate.goi(yeu_cau())
                self.assertIn(ma, result.ly_do)
                text = repr(result) + "\n".join(records) + repr(gate.cai_dat) + repr(gate.trang_thai())
                self.assertNotIn(KHOA_CLOUD, text)
                self.assertNotIn(KHOA_MASK, text)
                self.assertIn("Không ghi được nhật ký cổng AI (RuntimeError).", records)
                # Khóa nào đi đúng chỗ đó: Bearer Mask chỉ tới Mask, x-api-key chỉ tới Cloud.
                for call in mask_calls:
                    self.assertNotIn("x-api-key", call["headers"])
                for call in cloud_calls:
                    self.assertEqual(KHOA_CLOUD, call["headers"]["x-api-key"])
                    self.assertNotIn("authorization", call["headers"])
                    self.assertNotIn(KHOA_MASK, json.dumps(call["body"], ensure_ascii=False))
        # Ngoại lệ của lớp nhà cung cấp không mang khóa, kể cả chuỗi ngoại lệ gốc.
        with may_chu(CloudGia(status=401, loi_body=echo).xu_ly) as (cloud_url, _):
            for url in (cloud_url + "/v1/messages", f"http://127.0.0.1:{cong_dong()}/v1/messages"):
                nha = ca.NhaCungCapAnthropic(url, proxy_moi_truong=False)
                with self.assertRaises(ca.CloudLoi) as ctx:
                    nha.tra_loi("DEMO", "DEMO", model="claude-opus-5-5", khoa=KHOA_CLOUD, max_tokens=256, timeout=3)
                exc, chain = ctx.exception, []
                while exc is not None:
                    chain.append(repr(exc) + str(exc) + "".join(traceback.format_exception(exc)))
                    exc = exc.__cause__ or exc.__context__
                self.assertNotIn(KHOA_CLOUD, "\n".join(chain))

    def test_loi_ghi_nhat_ky_khong_lam_mat_ket_qua(self):
        mask_url, _, cloud_url, _ = self.mo()
        gate = self.cong(mask_url, cloud_url, local_tra_loi=LOCAL_CHAC,
                         bo_ghi=Mock(ghi=Mock(side_effect=RuntimeError("DEMO"))))
        with self.assertLogs("kho_tri_thuc.tri_thuc.cong_ai", level="ERROR"):
            result = gate.goi(yeu_cau())
        self.assertEqual("VANG", result.muc)


class NhaCungCapTests(unittest.TestCase):
    def test_anthropic_dung_phien_ban_api_khong_gui_temperature_co_fallback(self):
        cloud = CloudGia(lambda user: "OK")
        with may_chu(cloud.xu_ly) as (url, calls):
            nha = ca.NhaCungCapAnthropic(url + "/v1/messages", proxy_moi_truong=False)
            out = nha.tra_loi("HE THONG", "NOI DUNG", model="claude-opus-5-5", khoa=KHOA_CLOUD, max_tokens=1000,
                              timeout=3)
            nha.tra_loi("HE THONG", "NOI DUNG", model="claude-haiku-5-5", khoa=KHOA_CLOUD, max_tokens=1000,
                        timeout=3)
        self.assertEqual(("OK", "claude-opus-5-5", 1200, 300), (out.van_ban, out.model, out.token_vao, out.token_ra))
        body, headers = calls[0]["body"], calls[0]["headers"]
        self.assertEqual("2026-10-21", headers["anthropic-version"])
        self.assertEqual("server-side-fallback-2026-07-01", headers["anthropic-beta"])
        self.assertEqual("default", body["fallbacks"])
        self.assertEqual("HE THONG", body["system"])
        self.assertEqual([{"role": "user", "content": "NOI DUNG"}], body["messages"])
        for key in ("temperature", "top_p", "top_k", "thinking"):
            self.assertNotIn(key, body)
        self.assertNotIn("fallbacks", calls[1]["body"])
        self.assertNotIn("anthropic-beta", calls[1]["headers"])

    def test_openai_dinh_dang_toi_thieu(self):
        def xu_ly(method, path, headers, body):
            return 200, {"model": body["model"], "choices": [{"message": {"content": "OK"}}],
                         "usage": {"prompt_tokens": 10, "completion_tokens": 2}}

        with may_chu(xu_ly) as (url, calls):
            out = ca.NhaCungCapOpenAI(url + "/v1/chat/completions", proxy_moi_truong=False).tra_loi(
                "HE THONG", "NOI DUNG", model="demo-openai", khoa=KHOA_CLOUD, max_tokens=1000, timeout=3)
        self.assertEqual(("OK", 10, 2), (out.van_ban, out.token_vao, out.token_ra))
        self.assertEqual(f"Bearer {KHOA_CLOUD}", calls[0]["headers"]["authorization"])
        self.assertEqual(["system", "user"], [m["role"] for m in calls[0]["body"]["messages"]])
        self.assertNotIn("temperature", calls[0]["body"])

    def test_cong_khong_tu_tao_ket_noi_khi_cloud_tat(self):
        with patch.object(ca, "NhaCungCapAnthropic") as factory, patch.object(ca, "MaskV2") as mask:
            gate = ca.CongAI({"local_ai": {}}, bo_ghi=ca.BoGhiBoNho())
            gate.goi(yeu_cau())
        factory.assert_not_called()
        mask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
