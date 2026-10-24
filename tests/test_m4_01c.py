"""M4-01C — kiểm tĩnh/thuần Cổng hồ sơ GUI gói 1 (không cần PostgreSQL/browser). CODE_ONLY: coder viết, CHƯA CHẠY (NOT_RUN).

Kiểm trên tệp nguồn thật (không mô phỏng trình duyệt — ca bất đồng bộ ở tests/m4_01c_async.cjs, ca HTTP/PG ở tests/test_m4_01c_http.py):
- shell: index.html nạp /m4.js sau /app.js, có nav #m4 + section #page-m4; app.js khai trang m4, seam kttChung, đăng ký CRM/M5/M2/L11 vào cùng cổng
  đổi vai; CRM đổi vai qua hàng POST chung + barrier GET; M9 không bị đưa vào seam ở gói này.
- m4.js: chỉ gọi route POST có thật trong giao_dien/m4.py (TRUONG), không gửi khóa authority, không innerHTML/eval, đăng ký người tham gia "m4",
  dùng X-M4-Info cho tệp, tải bytes qua GET có token, hiển thị đủ cột tham số máy chủ trả.
- m4.css: mọi selector dưới .m4 (không rò style), font Be Vietnam Pro cục bộ, bảng màu Bàn kiểm soát.
- tệp mẫu DEMO: tên cố định, builder có sẵn, bytes qua được đúng bộ kiểm tệp của máy chủ (NR.kiem_tep) với vai/media khai.
- bootstrap: chuan_bi gọi m4_demo.khoi_tao bằng kết nối chủ sẵn có và trả m4_seed nguyên trạng.
- package data: khai báo đủ UI M4 + tệp không-phải-Python mà adapter đọc (PIN/FONT_PIN) — chỉ kiểm khai báo; build wheel/cài đặt là NOT_RUN.
"""

from __future__ import annotations

import fnmatch
import re
import tomllib
import unittest
from pathlib import Path

from kho_tri_thuc.giao_dien import m4 as M4HTTP
from kho_tri_thuc.m4 import nguon_review as NR

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "kho_tri_thuc"
INDEX = (SRC / "giao_dien" / "assets" / "index.html").read_text("utf-8")
APP = (SRC / "giao_dien" / "assets" / "app.js").read_text("utf-8")
M4JS = (SRC / "m4" / "giao_dien" / "m4.js").read_text("utf-8")
M4CSS = (SRC / "m4" / "giao_dien" / "m4.css").read_text("utf-8")


class Shell(unittest.TestCase):
    def test_index_nap_m4_sau_app(self):
        self.assertIn('src="/m4.js"', INDEX)
        self.assertIn('href="/m4.css"', INDEX)
        self.assertLess(INDEX.index('src="/app.js"'), INDEX.index('src="/m4.js"'))  # cả hai defer → m4.js chạy sau app.js
        self.assertIn('href="#m4" data-page="m4"', INDEX)
        self.assertIn('id="page-m4"', INDEX)
        self.assertEqual(INDEX.count('id="m4-title"'), 1)

    def test_app_khai_trang_va_seam(self):
        self.assertIn('pages.m4 = "Hồ sơ xây dựng (M4)"', APP)
        self.assertLess(APP.index("pages.m4 ="), APP.rindex("route();"))  # trang có trước lần route đầu tiên
        self.assertIn("window.kttChung = Object.freeze({", APP)
        for ten in ("crm", "m5", "m2", "l11"):
            self.assertRegex(APP, r'dangKyVai\("' + ten + r'", ')
        self.assertNotIn('dangKyVai("m9"', APP)  # M9 giữ nguyên trạng ở gói này
        self.assertIn("for (const p of vaiThanhVien.values()) p.xoa();", APP)
        self.assertIn("vaiThanhVien.get(t).nap()", APP)

    def test_crm_dung_cong_doi_vai_chung(self):
        self.assertIn('doiVaiTuanTu(() => crmPost("danh-tinh", {dang_nhap: login}), "crm-status", "crm")', APP)
        self.assertNotIn('crmAct("danh-tinh"', APP)
        than = APP[APP.index("async function crmLoad()"):APP.index('$("crm-refresh")')]
        self.assertIn('vaiDangChan("crm")', than)
        self.assertIn("crmGen", than)
        self.assertIn("crmTai(", APP)


def _cac_post(js: str) -> set[str]:
    return set(re.findall(r'gui\("([a-z\-/]+)"', js)) | set(re.findall(r'postJson\("([a-z\-/]+)"', js))


class M4Js(unittest.TestCase):
    def test_chi_goi_route_that(self):
        post = _cac_post(M4JS)
        self.assertTrue(post, "không tìm thấy lời gọi POST nào")
        self.assertLessEqual(post, set(M4HTTP.TRUONG), post - set(M4HTTP.TRUONG))
        for can in ("hop-dong/tao", "hop-dong/gan-tep", "hop-dong/trich", "tham-so/sua", "tham-so/xac-nhan", "phu-luc/khai", "phu-luc/them", "phu-luc/huy",
                    "boq/xem", "boq/nhap", "dot/tao", "dot/sua", "dot/gan-tep", "dot/nop", "danh-tinh"):
            self.assertIn(can, post, can)
        for get in ('"/api/m4"', '"/api/m4/hop-dong/"', '"/api/m4/dot/"', '"/api/m4/tep/"', '"/api/m4/mau"', '"/api/m4/mau/"', '"/api/m4/tep"'):
            self.assertIn(get, M4JS, get)
        self.assertIn('"X-M4-Info": enc', M4JS)
        self.assertIn('"X-KTT-Token": TOKEN', M4JS)

    def test_khong_gui_authority_khong_html_tho(self):
        for cam in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(cam, M4JS, cam)
        for khoa in ("kiem_tra", "raw_sha256", "sha256", "actor", "phap_nhan_id", "snapshot", "digest", "xac_nhan_boi", "approved", "duyet", "receipt",
                     "bien_nhan", "object_key", "duong_dan", "url", "dsn", "trang_thai"):
            self.assertIsNone(re.search(r"[{,]\s*" + khoa + r"\s*:", M4JS), f"m4.js gửi khóa {khoa}")
        self.assertNotIn("kiem_tra", M4HTTP.TRUONG["tham-so/sua"])  # kết quả máy kiểm không phải trường trình duyệt gửi được

    def test_seam_va_fence(self):
        for can in ('K.dangKyVai("m4", m4Xoa, () => m4Nap())', 'K.vaiDangChan("m4")', 'K.doiVaiTuanTu(() => postJson("danh-tinh", {dang_nhap: login}), "m4-status", "m4")',
                    "function fence(", "if (!f()) return"):
            self.assertIn(can, M4JS, can)
        # tải bytes chỉ click khi fence còn đúng và bytes khác rỗng
        than = M4JS[M4JS.index("async function taiTep("):M4JS.index("async function taiLen(")]
        self.assertLess(than.index("if (!f()) return;"), than.index("a.click()"))
        self.assertIn("if (!blob.size)", than)

    def test_giu_khoa_va_body_goc(self):
        # C2: khóa theo bản ghi + vé sở hữu của từng lần gửi; chỉ dọn đúng bản ghi/vé của chính mình (hành vi race kiểm ở m4_01c_async.cjs)
        ban_ghi = M4JS[M4JS.index("function nhanBanGhi("):M4JS.index("async function gui(")]
        self.assertIn("if (rec && rec.chu) return null", ban_ghi)       # bấm lặp khi lần gửi còn bay: không gửi thêm
        self.assertIn("if (rec.chu === ve) rec.chu = null", ban_ghi)
        self.assertIn("if (xong && khoaMap.get(k) === rec) khoaMap.delete(k)", ban_ghi)  # chỉ bỏ khóa khi có kết quả thật và vẫn là bản ghi của mình
        than = M4JS[M4JS.index("async function gui("):M4JS.index("function xuLyLoi(")]
        self.assertLess(than.index("const r = await postJson"), than.index("xong = true"))
        self.assertIn("finally { traBanGhi(k, rec, ve, xong); }", than)
        self.assertNotIn("dangGui", M4JS)
        self.assertIn("Gửi lại y nguyên (cùng khóa)", M4JS)

    def test_cot_tham_so_may_chu(self):
        for cot in ("t.ma", "t.nhom", "t.ten", "t.trang_thai", "t.gia_tri", "t.gia_tri_may", "t.don_vi", "t.dieu_khoan", "t.trich_dan", "t.kiem_tra", "t.ly_do",
                    "t.vi_tri", "t.nguon"):
            self.assertIn(cot, M4JS, cot)
        self.assertNotIn("36", re.findall(r"tham số \((\d+)\)", M4JS))  # nhãn tab theo 37 mã, không bộ 36 legacy

    def test_nop_lay_hai_revision_tu_get(self):
        self.assertIn('{dot_id: d.id, revision_ho_so: d.revision_ho_so, revision_dot: d.revision}', M4JS)

    def test_khong_nut_gia_nhanh_sau(self):
        for cam in ("/api/m4/duyet", "/api/m4/pdf", "/api/m4/request", "/api/m4/ke-toan"):
            self.assertNotIn(cam, M4JS)
        self.assertIn('x.trang_thai === "CHUA_NOI" ? "Chưa nối"', M4JS)


class M4Css(unittest.TestCase):
    def test_moi_selector_duoi_m4(self):
        css = re.sub(r"/\*.*?\*/", "", M4CSS, flags=re.S)
        sel = [s.strip() for s in re.findall(r"([^{}]+)\{", css)]
        self.assertTrue(sel)
        for s in sel:
            if s.startswith("@"):
                continue
            for part in s.split(","):
                self.assertTrue(part.strip().startswith(".m4"), f"selector rò ngoài .m4: {part.strip()!r}")

    def test_font_va_mau(self):
        self.assertIn('@import url("/m4/fonts/fonts.css")', M4CSS)
        self.assertIn('"Be Vietnam Pro"', M4CSS)
        for mau in ("#19334d", "#f4f6f9", "#24364a", "#dfe5ec", "#895a14"):
            self.assertIn(mau, M4CSS)


class TepMau(unittest.TestCase):
    def test_ten_co_dinh_qua_bo_kiem_tep_may_chu(self):
        self.assertTrue(M4HTTP.MAU)
        for ma, (vai, media, tao, mo_ta) in M4HTTP.MAU.items():
            self.assertRegex(ma, r"^[a-z0-9_]+\.(docx|xlsx|pdf)$")
            self.assertTrue(mo_ta)
            raw = tao()
            self.assertIsInstance(raw, bytes)
            meta = NR.kiem_tep(raw, ma, media, vai)   # đúng bộ kiểm tệp của POST /api/m4/tep
            self.assertEqual(meta["byte_length"], len(raw))
        self.assertEqual({v[0] for v in M4HTTP.MAU.values()}, {"HOP_DONG", "BOQ", "PHU_LUC", "HO_SO_DOT"})

    def test_route_mau_can_phien_va_quyen_soan(self):
        src = (SRC / "giao_dien" / "m4.py").read_text("utf-8")
        than = src[src.index('if path == "/api/m4/mau"'):src.index('m = re.fullmatch(r"/api/m4/(hop-dong|dot|tep)/')]
        self.assertIn("app.crm_phien(h.crm_sid())", than)
        self.assertIn("_kiem_mau", than)
        self.assertNotIn("tao=True", than)       # không tự cấp phiên mới cho route tệp mẫu
        self.assertIn("if ma not in MAU", than)  # không nhận đường dẫn/tên tùy ý


class Bootstrap(unittest.TestCase):
    def test_chuan_bi_seed_m4_bang_ket_noi_chu(self):
        src = (SRC / "k2" / "crm_khoi_dong.py").read_text("utf-8")
        than = src[src.index("def chuan_bi("):]
        self.assertIn("m4 = m4_demo.khoi_tao(admin)", than)
        self.assertLess(than.index("l11 = l11_demo.khoi_tao(admin)"), than.index("m4 = m4_demo.khoi_tao(admin)"))
        self.assertLess(than.index("m4 = m4_demo.khoi_tao(admin)"), than.index("sau = pg.schema_version(admin)"))
        self.assertIn('"m4_seed": m4', than)


class PackageData(unittest.TestCase):
    def test_khai_bao_ui_va_tep_nguon(self):
        cfg = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))
        pd = cfg["tool"]["setuptools"]["package-data"]
        self.assertIn("kho_tri_thuc.giao_dien", pd)
        m4 = pd["kho_tri_thuc.m4"]
        # setuptools: "**/" khớp 0..n thư mục; fnmatch "*" khớp cả "/" → thử cả mẫu bỏ "**/"
        khop = lambda rel: any(fnmatch.fnmatch(rel, q) for p in m4 for q in {p, p.replace("**/", "")})
        for rel in ("giao_dien/m4.js", "giao_dien/m4.css"):
            self.assertTrue(khop(rel), rel)
        for rel in NR.PIN:
            self.assertTrue(khop("review_goc/" + rel), rel)
        for ten in NR.FONT_PIN:
            self.assertTrue(khop("review_goc/giao_dien/fonts/" + ten), ten)


if __name__ == "__main__":
    unittest.main()
