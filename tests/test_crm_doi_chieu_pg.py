"""CRM G5-B — PG thật trên bản sao DEMO SỞ HỮU (CODE_ONLY: coder viết, CHƯA CHẠY — WRITTEN_NOT_RUN).

Điều kiện (thiếu bất kỳ → FAIL ``NOT_VERIFIED``, không skip, không coi là đạt):
  * cổng ``test_crm_kiem_hd.cong_clone(can_ghi=True)`` (owner DSN + DSN login ứng dụng thường, provenance OWNED_DEMO_CLONE, registry + checksum,
    marker DEMO, quyền hiện hành) — KHÔNG tạo DB/vai, không SET ROLE, không seed/bootstrap, không M9;
  * Root ĐÃ append hằng ``CRM_G5_SQL`` thành migration trên bản sao này (gói không tự áp/đăng ký/đoán ordinal): kiểm ``master.crm_g5_viec`` +
    ``master.crm_g5_doc`` tồn tại;
  * G3 PDF_DAT thật (Word) + pypdfium2 để có bản ký G4 thật (helper luồng G2/G3/G4 mượn từ tests G6A/G3).

Luồng chạy theo thứ tự p00…p11 trên MỘT bản sao/một máy chủ (trạng thái qua cls.s). Worker KHÔNG chạy nền trong test: factory nhận
``HangDoiG5`` chưa khởi động (cùng lớp thật) để test tự gọi ``mot_luot()`` — tất định; đường đánh thức sau G4/lệnh vẫn qua route thật.
FIX01 (bổ sung p12…p15, WRITTEN_NOT_RUN): kết quả CHUA_DOI_CHIEU_DUOC giữ nghĩa vụ bắt buộc mở, không POST trùng cùng đăng ký; kết quả hoàn
tất (thủ công) đóng nghĩa vụ; đăng ký mới → thế hệ mới chạy tiếp; lease hết hạn → kết thúc/ý định/công bố không áp dụng.

NHÃN BẮT BUỘC:
  * client E5 ở đây là GIẢ (``test_crm_doi_chieu_tinh._E5`` — DEMO, dựng envelope từ đúng body) vì producer E5-A thật chưa ghép vào baseline
    này; KẾT QUẢ KHOP/LECH Ở ĐÂY KHÔNG PHẢI BẰNG CHỨNG PRODUCER, KHÔNG PHẢI NGHIỆM THU.
  * đăng ký engine/catalog do test (chủ CSDL) ghi CHỈ trên bản sao DEMO: một dòng nhãn DEMO_KIEM_THU và — để đo nhánh dương có điều kiện của
    G6 — một dòng nhãn VAN_HANH có ghi_chu "TEST-ONLY DEMO CLONE". Đó KHÔNG phải đăng ký vận hành; Root đăng ký vận hành sau proof producer.
  * loại hình DEMO là KCN; catalog KCN/NHAO thật của Source6 chưa có — catalog_id/sha ở đây là giá trị DEMO.
Không DROP/DELETE/cleanup — dữ liệu giữ làm bằng chứng. PG native / Word / GUI / full CRM acceptance vẫn OPEN tới khi Root có biên nhận độc lập.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import test_crm_doi_chieu_tinh as T
import test_crm_giao_ket_http as GKH  # chỉ mượn helper (không đưa lớp TestCase vào module này)
import test_crm_kiem_hd as TK
import test_crm_kiem_hd_http as HK
from test_crm_giao_ket import _co_word
from test_crm_ky_ket import pdf_tong_hop

from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.k2 import crm_doi_chieu as DC
from kho_tri_thuc.nguon.trich_chung_6 import ChuaRo

TAI, KT, CFO, BH = GKH.TAI, GKH.KT, GKH.CFO, GKH.BH
KT_NO_CRM, CFO_B = GKH.KT_NO_CRM, GKH.CFO_B
ngay = GKH.ngay
TRUONG_MAP = (("GIA_TRI_HD", "gia_tri_hop_dong", 3), ("SO_HD", "so_hop_dong", 1), ("NGAY_KY", "ngay_ky", 2))
LICH = [{"lan": "1", "loai": "PERCENT", "ty_le": "40", "moc_loai": "SU_KIEN", "moc_su_kien": "KY_HD"},
        {"lan": "2", "loai": "PERCENT", "ty_le": "60", "moc_loai": "NGAY", "moc_ngay": ngay(60)}]
VIEW_KHOA = {"kieu", "ky_id", "context_sha256", "bat_buoc", "khoi_tao", "quyen", "readiness", "current_job", "current_result", "history", "g6"}
ACK_KHOA = {"kieu", "ky_id", "context_sha256", "job_id", "request_id", "state", "current_result_id", "tao_moi", "replay"}


class _E5Moc(T._E5):
    """Client E5 GIẢ (DEMO) + móc chạy TRƯỚC khi trả (mô phỏng thu hồi/đổi đăng ký trong lúc engine chạy NGOÀI khóa)."""

    def __init__(self, *, moc=None, **kw):
        super().__init__(**kw)
        self.moc = moc

    def doi_chieu_ban_ky(self, raw, **kw):
        if self.moc is not None:
            self.moc()
        return super().doi_chieu_ban_ky(raw, **kw)


def _lech_gia_tri(y):
    return T._g5(y, "LECH", lech=[T._lech(y, "GIA_TRI_HD", {"so_tien": "100000000", "tien_te": "VND"},
                                         trich="Điều 3 (bản ký DEMO): giá trị hợp đồng 100.000.000 VND", vi_tri={"trang": 1, "doan": 3})])


class CrmDoiChieuBanSao(unittest.TestCase):
    _G = GKH.CrmGiaoKetHttp
    goi, sid, K, ok, loi, get, q, loai_a, du_an = _G.goi, _G.sid, _G.K, _G.ok, _G.loi, _G.get, _G.q, _G.loai_a, _G.du_an
    mau_hieu_luc, bao_gia = _G.mau_hieu_luc, _G.bao_gia
    khoa_may, _dung, _dong_ket_noi_app = _G.__dict__["khoa_may"], _G.__dict__["_dung"], _G.__dict__["_dong_ket_noi_app"]
    del _G
    _H = HK.CrmKiemHttpBanSao
    phan_cong, pham_vi_ky, pham_vi_kiem, thu_hoi = _H.phan_cong, _H.pham_vi_ky, _H.pham_vi_kiem, _H.thu_hoi
    del _H

    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.ly_do = TK.cong_clone(can_ghi=True)
        if not cls.ctx:
            return
        cls.addClassCleanup(TK._dong, cls.ctx["owner"], cls.ctx["app"])
        cls.admin = cls.ctx["owner"]
        co = cls.admin.execute("SELECT to_regclass('master.crm_g5_viec') IS NOT NULL AND to_regprocedure('master.crm_g5_doc(uuid)') IS NOT NULL").fetchone()[0]
        if not co:
            cls.ctx, cls.ly_do = None, "bản sao chưa có CRM_G5_SQL (Root chưa append migration G5-B) — gói không tự áp SQL"
            return
        from kho_tri_thuc.giao_dien import crm_g as CG
        from kho_tri_thuc.giao_dien.server import LocalApp, LocalServer
        env = {LocalApp.CRM_ENV: os.environ[TK.ENV_APP], LocalApp.CRM_ENV_ADMIN: os.environ[TK.ENV_OWNER]}
        if cls.ctx["kiem_thu"]:
            env[LocalApp.CRM_ENV_DB_KIEM_THU] = "1"
        cls.env = patch.dict(os.environ, env)
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        cls.tam = Path(tempfile.mkdtemp(prefix="ktt_crm_g5b_pg_"))  # giữ lại
        (cls.tam / "cau_hinh_fixture.toml").write_text(GKH.CAU_HINH_FIXTURE, encoding="utf-8")
        cls.app = LocalApp(cls.tam / "cau_hinh_fixture.toml", cls.tam / "web")
        cls.addClassCleanup(cls._dong_ket_noi_app)
        cls.s = {"client": None}
        # FIX01-C: factory G thường nay tự dựng + đánh thức worker G5 của app; trong setup chặn thread nền (bat_dau không chạy) rồi giữ bằng chứng
        # factory đã dựng đúng một worker, sau đó thay bằng service/hàng đợi THẬT do test tự drain (tất định)
        with patch.object(DC.HangDoiG5, "bat_dau", lambda self_: None):
            kiem = CG.dich_vu_kiem(cls.app)
        cls.s["hd_factory"] = cls.app.__dict__.get("_crm_g5_hang_doi")
        cls.s["loi_khoi_tao_g5"] = cls.app.__dict__.get("_crm_g5_loi_khoi_tao")
        cls.dv = DC.CrmDoiChieuK2(kiem, client_fn=lambda goc: cls.s["client"])
        cls.app.__dict__["_crm_g5"] = cls.dv
        cls.hd = DC.HangDoiG5(cls.dv, cls.app.mutation_lock, db=cls.app._crm_db)
        cls.app.__dict__["_crm_g5_hang_doi"] = cls.hd
        cls.server = LocalServer(cls.app, 0)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls._dung)
        cls.run_id = uuid.uuid4().hex[:8]
        cls.co_word = _co_word()

    def setUp(self):
        if not self.ctx:
            self.fail("NOT_VERIFIED: " + self.ly_do)

    def can(self, *khoa):
        thieu = [k for k in khoa if k not in self.s]
        if thieu:
            self.fail("NOT_VERIFIED: bước chuẩn bị trước chưa đạt (thiếu " + ", ".join(thieu) + ")")

    # ------------------------------------------------------------------ helpers
    def dung_hop_dong(self, tag, *, co_sua, pb):
        """Báo giá → soạn → xuất G3 (PDF_DAT THẬT) → G4 ký (BH) qua HTTP; khai Có/Không theo co_sua. Thiếu Word/pypdfium2 → NOT_VERIFIED."""
        r = self.ok(BH, "bao-gia/luu", {"bao_gia_id": None, "expected_revision": None, "khoa": self.K("bg-" + tag),
                                        "du_lieu": self.bao_gia(don_vi={"ma": f"LO-G5B-{tag}-{self.run_id}"}, lich=LICH)})
        a = self.ok(BH, "bao-gia/chuyen", {"bao_gia_id": r["bao_gia_id"], "expected_revision": 1, "mau_phien_ban_id": pb,
                                           "khoa": self.K("cv-" + tag)})
        soan = a["soan_id"]
        bg = dict(self.get(BH, "soan/" + soan)["du_lieu"]["bao_gia"])
        bg["fx"] = None
        gt = {"so_hop_dong": f"HĐ-DEMO-G5B-{tag}-{self.run_id}", "ngay_ky": ngay(0), "ten_hien_thi_demo": "NGƯỜI MUA DEMO",
              "gia_tri_hop_dong": {"so_tien": "1000000000", "tien_te": "VND"}}
        self.ok(BH, "soan/luu", {"soan_id": soan, "expected_revision": 1, "gia_tri_truong": gt, "bao_gia": bg, "khoa": self.K("so-" + tag)})
        x = self.ok(BH, "soan/xuat", {"soan_id": soan, "expected_revision": 2, "khoa": self.K("x-" + tag)})
        row = self.admin.execute("SELECT trang_thai FROM master.crm_gk_xuat WHERE id = %s", (x["xuat_id"],)).fetchone()
        if x.get("trang_thai") != "PDF_DAT" or row is None or row[0] != "PDF_DAT":
            self.fail(f"NOT_VERIFIED: chưa có bản xuất G3 PDF_DAT thật (trạng thái {x.get('trang_thai')}; probe Word={self.co_word}) — "
                      "không owner-forge PDF_DAT")
        pc, _ = self.phan_cong(BH, "CRM_KY_KET", soan)
        self.pham_vi_ky(pc, soan)
        raw = pdf_tong_hop(1, f"BAN KY G5B {tag}")
        info = {"soan_id": soan, "expected_revision": 2, "expected_xuat_id": x["xuat_id"], "ten_tep": "ban-da-ky.pdf", "ngay_ky": ngay(0),
                "co_sua": co_sua, "khoa": self.K("ky-" + tag)}
        if co_sua:
            info["mo_ta"] = "DEMO: khách sửa tay điều 3 trước khi ký"
        st, k, _ = self.goi("/api/crm/giao-ket/ky-ket", cookie=self.sid(BH), raw=raw,
                            headers={"X-CRM-G-Info": quote(json.dumps(info, ensure_ascii=False)), "Content-Type": "application/pdf"})
        self.assertEqual(st, 200, k)
        # ACK G4 GIỮ NGUYÊN: khởi tạo PENDING/NOT_SELECTED — không phải bằng chứng G5, không bị G5-B đổi
        self.assertEqual(k["g5"], {"trang_thai": "PENDING", "ly_do": "BAT_BUOC_KHAI_CO"} if co_sua
                         else {"trang_thai": "NOT_SELECTED", "ly_do": "CHUA_AP_DUNG_CHON_MAU"})
        return {"soan": soan, "hd": a["hop_dong_id"], "ky": k["ky_id"], "raw": raw}

    def view(self, login, ky, status=200):
        r = self.get(login, "giao-ket/doi-chieu/" + ky, status=status)
        if status == 200:
            self.assertEqual(set(r), VIEW_KHOA)
            self.assertEqual((r["kieu"], r["ky_id"], r["khoi_tao"]["la_bang_chung"]), ("CRM_G5_VIEW_V1", ky, False))
        return r

    def lenh(self, login, hanh, ky, ctx, khoa, status=200, ma=None):
        st, r, _ = self.goi("/api/crm/giao-ket/doi-chieu/" + hanh, {"ky_id": ky, "expected_context_sha256": ctx, "khoa": khoa}, self.sid(login))
        if status == 200:
            self.assertEqual(st, 200, r)
            self.assertEqual(set(r), ACK_KHOA)
            self.assertEqual((r["kieu"], r["ky_id"], r["context_sha256"]), ("CRM_G5_ACK_V1", ky, ctx))
            self.assertEqual(r["request_id"], f"crm-g5-{r['job_id']}-{self.viec(r['job_id'])['the_he']}")
        else:
            self.assertEqual((st, r.get("error") if isinstance(r, dict) else r), (status, ma), (login, hanh, r))
        return r

    def doi_soat(self, ky, tag):
        v = self.view(KT, ky)
        return self.lenh(KT, "doi-soat", ky, v["context_sha256"], self.K("ds-" + tag))

    def viec(self, viec_id):
        r = self.admin.execute("""SELECT id::text, loai, trang_thai, ly_do, the_he, so_lan, khoi_tao_loai, khoi_tao_boi, ket_qua_id::text
                                  FROM master.crm_g5_viec WHERE id = %s""", (viec_id,)).fetchone()
        return dict(zip(("id", "loai", "trang_thai", "ly_do", "the_he", "so_lan", "khoi_tao_loai", "khoi_tao_boi", "ket_qua_id"), r))

    def viec_bat_buoc(self, ky):
        r = self.admin.execute("SELECT id::text FROM master.crm_g5_viec WHERE ky_id = %s AND loai = 'BAT_BUOC'", (ky,)).fetchall()
        return [x[0] for x in r]

    def dem(self, bang, ky):
        return self.q(f"SELECT count(*) FROM master.{bang} WHERE ky_id = %s", (ky,))

    def su_kien(self, viec_id):
        return [tuple(x) for x in self.admin.execute("""SELECT loai, tac_nhan_loai, tac_nhan FROM master.crm_g5_su_kien WHERE viec_id = %s
                                                        ORDER BY thu_tu""", (viec_id,)).fetchall()]

    def drain(self):
        with patch.object(DC.HangDoiG5, "bat_dau", lambda self_: None):
            return self.hd.mot_luot()

    def dang_ky(self, ky, nhan, ghi_chu):
        """Đăng ký engine/catalog BẤT BIẾN do chủ CSDL ghi trên BẢN SAO DEMO (tham chiếu PN/loại hình/mẫu/danh mục/profile ĐÃ GHIM ở bản ký).
        Mapping chỉ gồm trường có trong danh mục đã ghim; thiếu → NOT_VERIFIED (không tự thêm trường/catalog)."""
        dm = {r[0]: r[1] for r in self.admin.execute("""SELECT t.khoa, t.kieu FROM master.crm_hd_ky k JOIN master.crm_hd_soan s ON s.id = k.soan_id
                                                        JOIN master.crm_danh_muc_truong t ON t.loai_hinh_id = s.loai_hinh_id
                                                             AND t.danh_muc_ref = k.danh_muc_ref AND t.revision = k.danh_muc_rev
                                                        WHERE k.id = %s""", (ky,)).fetchall()}
        mp = [{"ma": ma, "crm_truong": tr, "muc": muc} for ma, tr, muc in TRUONG_MAP if dm.get(tr) in ("text", "so", "ngay", "tien")]
        if not any(m["ma"] == "GIA_TRI_HD" for m in mp):
            self.fail("NOT_VERIFIED: danh mục DEMO đã ghim không có trường tiền gia_tri_hop_dong — không tự thêm trường")
        mp.append({"ma": "LICH_TT", "crm_truong": "crm.lich", "muc": 2})
        mj = json.dumps(mp, ensure_ascii=False)
        return str(self.q("""INSERT INTO master.crm_g5_dang_ky (phap_nhan_id, loai_hinh_id, mau_phien_ban_id, danh_muc_ref, danh_muc_rev, danh_muc_digest,
                                                                profile_sha256, loai_hop_dong, catalog_id, catalog_sha256, implementation_sha256,
                                                                capability, mapping, mapping_sha256, nhan, ghi_chu)
                             SELECT k.phap_nhan_id, s.loai_hinh_id, k.mau_phien_ban_id, k.danh_muc_ref, k.danh_muc_rev, k.danh_muc_digest, k.profile_sha256,
                                    'KCN_DEMO', 'demo.g5b.clone-test', %s, %s, 'doi_chieu_ban_ky', %s::jsonb,
                                    encode(sha256(convert_to(%s::jsonb::text, 'UTF8')), 'hex'), %s, %s
                             FROM master.crm_hd_ky k JOIN master.crm_hd_soan s ON s.id = k.soan_id WHERE k.id = %s RETURNING id""",
                          ("7" * 64, T.IMPL, mj, mj, nhan, ghi_chu, ky)))

    def nguoi_chay(self, pc):
        return str(self.q("""INSERT INTO master.crm_g5_nguoi_chay (phap_nhan_id, phan_cong_id, nguoi_dung_id, ghi_chu)
                             SELECT a.phap_nhan_id, a.id, a.nguoi_dung_id, 'TEST:CRM-G5-B người chạy cấu hình trên bản sao DEMO'
                             FROM master.phan_cong_hanh_dong a WHERE a.id = %s RETURNING id""", (pc,)))

    def thu_hoi_g5(self, loai, id_):
        self.admin.execute("INSERT INTO master.crm_g5_thu_hoi (loai, doi_tuong_id, ly_do) VALUES (%s, %s, 'TEST thu hồi G5-B')", (loai, id_))

    # ------------------------------------------------------------------ p00: chuẩn bị — 3 hợp đồng đã ký (N: khai Không; M1, M2: khai Có)
    def test_p00_chuan_bi_va_viec_bat_buoc_cung_giao_dich(self):
        try:
            import pypdfium2  # noqa: F401
        except ImportError:
            self.fail("NOT_VERIFIED: máy chủ thiếu pypdfium2 — G4 fail closed, không có bản ký")
        self.s["pb"], _ = self.mau_hieu_luc("HD_G5B_" + self.run_id, ngay(-2), "MAU G5B")
        # M2 dùng MẪU RIÊNG: đăng ký DEMO/VAN_HANH của mẫu N/M1 không khớp M2 (đăng ký khớp theo mẫu đã ghim) → việc bắt buộc M2 không bị
        # xử lý ngoài ý muốn khi đến hạn sớm; p11 đăng ký riêng cho mẫu M2
        self.s["pb2"], _ = self.mau_hieu_luc("HD_G5B2_" + self.run_id, ngay(-2), "MAU G5B2")
        for tag, co, pb in (("N", False, self.s["pb"]), ("M1", True, self.s["pb"]), ("M2", True, self.s["pb2"])):
            h = self.dung_hop_dong(tag.lower(), co_sua=co, pb=pb)
            vb = self.viec_bat_buoc(h["ky"])
            if co:
                self.assertEqual(len(vb), 1, "khai Có phải có ĐÚNG một việc bắt buộc bền")
                # cùng giao dịch ký: xmin hàng việc == xmin hàng bản ký (chưa ai cập nhật việc — worker chưa drain)
                cung = self.q("""SELECT v.xmin::text = k.xmin::text FROM master.crm_g5_viec v JOIN master.crm_hd_ky k ON k.id = v.ky_id
                                 WHERE v.id = %s""", (vb[0],))
                self.assertTrue(cung, "việc bắt buộc phải ghi trong CHÍNH giao dịch ký G4")
                v = self.viec(vb[0])
                self.assertEqual((v["loai"], v["trang_thai"], v["khoi_tao_loai"], v["khoi_tao_boi"], v["the_he"]),
                                 ("BAT_BUOC", "CHO", "HE_THONG", "G4_KY_KHAI_CO", 1))
                self.assertEqual(self.su_kien(vb[0]), [("TAO", "HE_THONG", "G4_KY_KHAI_CO")])
                h["viec_bb"] = vb[0]
            else:
                self.assertEqual(vb, [], "khai Không: không có việc bắt buộc (không sampler/không tự chọn mẫu)")
            g = self.admin.execute("SELECT trang_thai, ly_do FROM master.crm_hd_ky_g5 WHERE ky_id = %s", (h["ky"],)).fetchone()
            self.assertEqual(tuple(g), ("PENDING", "BAT_BUOC_KHAI_CO") if co else ("NOT_SELECTED", "CHUA_AP_DUNG_CHON_MAU"))
            self.s[tag] = h

    # ------------------------------------------------------------------ p01: quyền + phạm vi HIỆN HÀNH trước mọi đọc/lệnh
    def test_p01_quyen_truoc_doc_va_lenh(self):
        self.can("N", "M1", "M2")
        N = self.s["N"]
        nk = self.q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_G5_XEM' AND doi_tuong_id = %s", (N["ky"],))
        for login in (KT_NO_CRM, CFO_B, BH, TAI):  # ngoài PN/module/vai KT → 404 ẩn, kể cả người ký
            self.view(login, N["ky"], status=404)
            self.lenh(login, "chay", N["ky"], "0" * 64, self.K("ngoai-" + login), 404, "CRM_G_KHONG_THAY")
        pc, _ = self.phan_cong(KT, "CRM_HD_KIEM", N["soan"])
        self.s["pc_kt"] = pc
        self.view(KT, N["ky"], status=403)  # vai + phân công nhưng chưa phạm vi
        self.lenh(KT, "chay", N["ky"], "0" * 64, self.K("chua-pv"), 403, "CRM_KIEM_CHUA_CO_PHAM_VI")
        self.assertEqual(self.dem("crm_g5_viec", N["ky"]), 0)
        self.assertEqual(self.q("SELECT count(*) FROM nhat_ky.su_kien WHERE hanh_dong = 'CRM_G5_XEM' AND doi_tuong_id = %s", (N["ky"],)), nk)
        for tag in ("N", "M1", "M2"):
            self.s["pv_" + tag] = self.pham_vi_kiem(pc, self.s[tag]["ky"])
        v = self.view(KT, N["ky"])
        self.assertEqual((v["bat_buoc"], v["current_job"], v["current_result"], v["history"]), (False, None, None, []))
        self.assertEqual(v["quyen"], {"chay": True, "doi_soat": False})
        self.assertEqual(v["readiness"], {"san_sang": False, "ly_do": ["THIEU_DANG_KY"]})
        self.assertEqual((v["g6"]["trang_thai"], [c["ma"] for c in v["g6"]["chan"]]), ("HOLD", ["UNREGISTERED_G5_PROOF"]))
        m = self.view(KT, self.s["M1"]["ky"])
        self.assertEqual((m["bat_buoc"], m["current_job"]["loai"], m["current_job"]["trang_thai"], m["current_job"]["khoi_tao_loai"]),
                         (True, "BAT_BUOC", "CHO", "HE_THONG"))
        self.assertEqual(set(m["current_job"]), {"job_id", "loai", "trang_thai", "ly_do", "request_id", "the_he", "so_lan", "khoi_tao_loai",
                                                 "cap_nhat_luc"})
        self.assertEqual(set(m["readiness"]["ly_do"]), {"THIEU_DANG_KY", "THIEU_NGUOI_CHAY"})
        self.assertEqual(m["khoi_tao"], {"trang_thai": "PENDING", "ly_do": "BAT_BUOC_KHAI_CO", "la_bang_chung": False})
        with self.assertRaises(Exception) as cm:  # login ứng dụng thường: hàm/bảng G5 không gọi/đọc trực tiếp được
            with self.ctx["app"].transaction():
                self.ctx["app"].execute("SELECT master.crm_g5_doc(%s::uuid)", (N["ky"],))
        self.assertIn("permission denied", str(cm.exception))

    # ------------------------------------------------------------------ p02: việc bắt buộc thiếu người chạy cấu hình → CHO_CAU_HINH, giữ việc
    def test_p02_bat_buoc_cho_nguoi_chay(self):
        self.can("pv_M1", "pv_M2")
        self.s["client"] = T._E5()
        self.drain()
        for tag in ("M1", "M2"):
            v = self.viec(self.s[tag]["viec_bb"])
            self.assertEqual((v["trang_thai"], v["ly_do"], v["so_lan"]), ("CHO_CAU_HINH", "THIEU_NGUOI_CHAY", 0))
            self.assertIn(("CHO_CAU_HINH", "SYSTEM_JOB", "hang_doi"), self.su_kien(v["id"]))
            self.assertEqual(self.dem("crm_g5_y_dinh", self.s[tag]["ky"]), 0)
        self.assertEqual(self.s["client"].goi, [], "không có người chạy: không gọi engine, không mượn người tạo/ký/CFO")
        self.drain()  # chạy lại: việc chưa đến hạn → không đổi, không nhân sự kiện
        self.assertEqual(sum(1 for e in self.su_kien(self.s["M1"]["viec_bb"]) if e[0] == "CHO_CAU_HINH"), 1)

    # ------------------------------------------------------------------ p03: người chạy cấu hình, chưa đăng ký → CHO_CAU_HINH THIEU_DANG_KY
    def test_p03_nguoi_chay_chua_dang_ky(self):
        self.can("pc_kt", "M1")
        self.s["nc"] = self.nguoi_chay(self.s["pc_kt"])
        M1 = self.s["M1"]
        a = self.doi_soat(M1["ky"], "m1-1")
        self.assertEqual((a["job_id"], a["state"], a["tao_moi"], a["replay"]), (M1["viec_bb"], "CHO", False, False))
        self.drain()
        v = self.viec(M1["viec_bb"])
        self.assertEqual((v["trang_thai"], v["ly_do"]), ("CHO_CAU_HINH", "THIEU_DANG_KY"))
        self.assertIn(("CHO_CAU_HINH", "SYSTEM_JOB", KT), self.su_kien(M1["viec_bb"]))
        self.assertEqual(self.view(KT, M1["ky"])["readiness"]["ly_do"], ["THIEU_DANG_KY"])

    # ------------------------------------------------------------------ p04: đăng ký DEMO + client baseline (chưa E5) → CHO_CAU_HINH E5_CHUA_GHEP
    def test_p04_e5_chua_ghep_giu_y_dinh(self):
        self.can("nc", "M1")
        M1 = self.s["M1"]
        self.s["dk_demo"] = self.dang_ky(M1["ky"], "DEMO_KIEM_THU", "TEST-ONLY DEMO CLONE — đăng ký DEMO, không phải vận hành")
        self.s["client"] = T._Trich6Goc()  # hình dạng Trich6Client baseline: chỉ .trich, không doi_chieu_ban_ky
        self.doi_soat(M1["ky"], "m1-2")
        self.drain()
        v = self.viec(M1["viec_bb"])
        self.assertEqual((v["trang_thai"], v["ly_do"], v["the_he"], v["so_lan"]), ("CHO_CAU_HINH", "E5_CHUA_GHEP", 1, 1))
        y = self.admin.execute("""SELECT y.expected, y.expected_sha256, y.binding, y.binding_sha256, y.body, y.body_sha256, y.request_id, y.tac_nhan_loai,
                                         y.tac_nhan, k.soan_rev_id::text, r.du_lieu
                                  FROM master.crm_g5_y_dinh y JOIN master.crm_hd_ky k ON k.id = y.ky_id JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id
                                  WHERE y.viec_id = %s""", (M1["viec_bb"],)).fetchall()
        self.assertEqual(len(y), 1, "ý định bất biến ghi TRƯỚC engine, một lần cho thế hệ 1")
        exp, esha, bd, bsha, body, hsha, rid, tnl, tn, rev, du = y[0]
        self.assertEqual((rid, tnl, tn), (f"crm-g5-{M1['viec_bb']}-1", "SYSTEM_JOB", KT))  # audit: việc hệ thống, người chạy cấu hình
        self.assertEqual(exp["lineage"]["soan_rev_id"], rev)  # expected từ ĐÚNG revision đã ký (không bản nháp/latest)
        gt = {t["ma"]: t for t in exp["tham_so"]}
        self.assertEqual(gt["GIA_TRI_HD"]["gia_tri"], DC.chuan_hoa_truong("tien", du["gia_tri_truong"]["gia_tri_hop_dong"]))
        self.assertEqual(gt["GIA_TRI_HD"]["gia_tri"]["so_tien"], "1000000000")  # giá trị revision ĐÃ KÝ, không 100 / không quy đổi
        self.assertEqual(gt["LICH_TT"]["gia_tri"], DC.bang_lich(du["bao_gia"]["lich"]))
        self.assertEqual((esha, bsha, hsha), (DC.sha_obj(exp), DC.sha_obj(bd), DC.sha_body(body)))
        self.assertEqual(set(body), DC.E5_KHOA)
        self.assertNotEqual(body["signed_pdf_sha256"], exp["lineage"]["g3_pdf_sha256"])  # hai vai PDF riêng
        self.s["rid_m1"] = rid
        g6 = self.view(KT, M1["ky"])["g6"]
        self.assertEqual([c["ma"] for c in g6["chan"]], ["G5_BAT_BUOC_CHUA_CO_KET_QUA"])

    # ------------------------------------------------------------------ p05: mất ACK (CHUA_RO) → đối soát giữ request_id → client E5 GIẢ KHOP
    def test_p05_chua_ro_doi_soat_va_khop_demo(self):
        self.can("rid_m1")
        M1 = self.s["M1"]
        self.s["client"] = T._E5(loi=ChuaRo("TRICH6_CHUA_RO", "mất phản hồi (giả)"))
        self.doi_soat(M1["ky"], "m1-3")
        self.drain()
        v = self.viec(M1["viec_bb"])
        self.assertEqual((v["trang_thai"], v["ly_do"], v["the_he"]), ("CHUA_RO", "TRICH6_CHUA_RO", 1))
        self.assertEqual(self.view(KT, M1["ky"])["current_job"]["request_id"], self.s["rid_m1"])
        e5 = T._E5()
        self.s["client"] = e5
        self.doi_soat(M1["ky"], "m1-4")
        self.drain()
        self.assertEqual([g["request_id"] for g in e5.goi], [self.s["rid_m1"]])  # cùng ý định/request_id — đối soát, không ý định mới
        self.assertEqual(self.dem("crm_g5_y_dinh", M1["ky"]), 1)
        v = self.viec(M1["viec_bb"])
        self.assertEqual(v["trang_thai"], "XONG")
        x = self.admin.execute("SELECT trang_thai, tac_nhan_loai, tac_nhan, request_id, dang_ky_id::text FROM master.crm_g5_ket_qua WHERE id = %s",
                               (v["ket_qua_id"],)).fetchone()
        self.assertEqual(tuple(x), ("KHOP", "SYSTEM_JOB", KT, self.s["rid_m1"], self.s["dk_demo"]))
        w = self.view(KT, M1["ky"])
        self.assertEqual((w["current_result"]["trang_thai"], w["current_result"]["nhan_dang_ky"], w["current_result"]["tac_nhan_loai"]),
                         ("KHOP", "DEMO_KIEM_THU", "SYSTEM_JOB"))
        self.assertEqual(w["readiness"]["ly_do"], ["DANG_KY_DEMO"])
        self.assertEqual((w["g6"]["trang_thai"], [c["ma"] for c in w["g6"]["chan"]]), ("HOLD", ["G5_DANG_KY_DEMO"]))  # DEMO không là bằng chứng
        # việc hệ thống KHÔNG duyệt/kiểm/kích hoạt/ghi sổ
        self.assertEqual(tuple(self.dem(b, M1["ky"]) for b in ("crm_kiem_ho_so", "crm_kiem_check", "crm_kiem_quyet_dinh", "crm_kiem_hieu_luc")),
                         (0, 0, 0, 0))
        self.assertEqual(self.q("SELECT crm_giao_ket FROM master.hop_dong WHERE id = %s", (M1["hd"],)), "DA_KY")
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_hd_ky_g5 WHERE ky_id = %s", (M1["ky"],)), "PENDING")  # G4 bất biến

    # ------------------------------------------------------------------ p06: thủ công — CAS ngữ cảnh, replay, nhiều cú nhấp, đối soát không việc
    def test_p06_thu_cong_cas_replay(self):
        self.can("dk_demo", "N")
        N = self.s["N"]
        v0 = self.view(KT, N["ky"])
        self.lenh(KT, "doi-soat", N["ky"], v0["context_sha256"], self.K("n-ds-0"), 409, "CRM_G5_CHUA_CO_VIEC")
        self.assertEqual(self.dem("crm_g5_viec", N["ky"]), 0)
        self.lenh(KT, "chay", N["ky"], "f" * 64, self.K("n-cu"), 409, "CRM_G5_NGU_CANH_CU")
        a = self.lenh(KT, "chay", N["ky"], v0["context_sha256"], self.K("n-1"))
        self.assertEqual((a["state"], a["tao_moi"], a["replay"], a["current_result_id"]), ("CHO", True, False, None))
        b = self.lenh(KT, "chay", N["ky"], v0["context_sha256"], self.K("n-1"))  # cùng khóa + cùng thân → biên nhận cũ
        self.assertEqual((b["job_id"], b["replay"], b["tao_moi"]), (a["job_id"], True, True))
        self.lenh(KT, "chay", N["ky"], v0["context_sha256"], self.K("n-2"), 409, "CRM_G5_NGU_CANH_CU")  # cú nhấp thứ hai: ngữ cảnh đã đổi
        self.lenh(KT, "chay", N["ky"], "e" * 64, self.K("n-1"), 409, "CRM_G_IDEMPOTENCY_KHAC")  # cùng khóa, thân khác → 409 trước CAS
        self.assertEqual(self.dem("crm_g5_viec", N["ky"]), 1)
        st, r, _ = self.goi("/api/crm/giao-ket/doi-chieu/chay", {"ky_id": N["ky"], "expected_context_sha256": v0["context_sha256"],
                                                                  "khoa": self.K("n-3"), "nguoi_chay": KT}, self.sid(KT))
        self.assertEqual((st, r["error"]), (403, "CRM_G_CLIENT_AUTHORITY"))
        v = self.viec(a["job_id"])
        self.assertEqual((v["loai"], v["khoi_tao_loai"], v["khoi_tao_boi"]), ("THU_CONG", "NGUOI_DUNG", KT))
        self.s["viec_n"] = a["job_id"]

    # ------------------------------------------------------------------ p07: lease — hai worker, mất lease, khôi phục sau "crash"
    def test_p07_lease_hai_worker_va_khoi_phuc(self):
        self.can("viec_n")
        N = self.s["N"]
        muc = {"viec_id": self.s["viec_n"], "nguoi_chay": KT}
        a = DC.CrmDoiChieuK2(self.dv.kiem, client_fn=lambda goc: self.s["client"], lease_giay=60)
        b = DC.CrmDoiChieuK2(self.dv.kiem, client_fn=lambda goc: self.s["client"])
        with self.app.mutation_lock:
            pa = self.app._crm_db(a.nhan, muc)
            pb = self.app._crm_db(b.nhan, muc)
        self.assertEqual((pa["nhan"], pb["nhan"], pb["ly_do"]), (True, False, "KHONG_DEN_HAN"))
        with self.app.mutation_lock:
            with self.assertRaises(DataError) as cm:
                self.app._crm_db(b.chuan_bi, pa)  # worker B dùng lease của A → mất lease
            self.assertEqual(cm.exception.code, "CRM_G5_LEASE_MAT")
            pa = self.app._crm_db(a.chuan_bi, pa)
        # A "crash" sau khi ghi ý định (không công bố/kết thúc) → việc DANG_CHAY tới hết lease; khởi động lại = worker mới
        self.assertEqual(self.viec(self.s["viec_n"])["trang_thai"], "DANG_CHAY")
        time.sleep(62)
        e5 = T._E5()
        self.s["client"] = e5
        moi = DC.CrmDoiChieuK2(self.dv.kiem, client_fn=lambda goc: self.s["client"])
        hd = DC.HangDoiG5(moi, self.app.mutation_lock, db=self.app._crm_db)
        self.assertGreaterEqual(hd.mot_luot(), 1)
        v = self.viec(self.s["viec_n"])
        self.assertEqual((v["trang_thai"], v["the_he"], v["so_lan"]), ("XONG", 1, 2))
        self.assertEqual([g["request_id"] for g in e5.goi], [pa["request_id"]])  # cùng request_id của ý định đã ghi (remote có thể đã nhận)
        self.assertEqual(self.dem("crm_g5_y_dinh", N["ky"]), 1)
        with self.app.mutation_lock:
            with self.assertRaises(DataError) as cm:
                self.app._crm_db(a.cong_bo, pa, a.goi_engine(pa)[1])  # A tỉnh lại muộn: không công bố đè
        self.assertEqual(cm.exception.code, "CRM_G5_LEASE_MAT")
        self.assertEqual(self.dem("crm_g5_ket_qua", N["ky"]), 1)

    # ------------------------------------------------------------------ p08: thu hồi phạm vi / đổi đăng ký TRONG lúc engine chạy → không công bố
    def test_p08_thu_hoi_truoc_cong_bo(self):
        self.can("viec_n", "pv_N", "pc_kt")
        N = self.s["N"]
        trc = self.dem("crm_g5_ket_qua", N["ky"])
        self.s["client"] = _E5Moc(moc=lambda: self.thu_hoi("crm_kiem_pham_vi", self.s["pv_N"]))
        v = self.view(KT, N["ky"])
        a = self.lenh(KT, "chay", N["ky"], v["context_sha256"], self.K("n-thu-hoi"))
        self.drain()
        j = self.viec(a["job_id"])
        self.assertEqual((j["trang_thai"], j["ly_do"]), ("CHO_CAU_HINH", "CRM_KIEM_CHUA_CO_PHAM_VI"))
        self.assertEqual(self.dem("crm_g5_ket_qua", N["ky"]), trc)
        self.view(KT, N["ky"], status=403)
        self.lenh(KT, "doi-soat", N["ky"], v["context_sha256"], self.K("n-thu-hoi-ds"), 403, "CRM_KIEM_CHUA_CO_PHAM_VI")
        self.s["pv_N"] = self.pham_vi_kiem(self.s["pc_kt"], N["ky"])
        dk_cu = self.s["dk_demo"]
        self.s["dk_demo2"] = self.dang_ky(N["ky"], "DEMO_KIEM_THU", "TEST-ONLY DEMO CLONE — đăng ký DEMO thay thế")
        self.s["client"] = _E5Moc(moc=lambda: self.thu_hoi_g5("DANG_KY", self.s["dk_demo2"]))
        self.doi_soat(N["ky"], "n-dk-1")
        self.drain()
        j = self.viec(a["job_id"])
        # ý định thế hệ 1 ghi theo dk_demo ≠ đăng ký hiện hành dk_demo2 → thế hệ 2; dk_demo2 bị thu hồi trước công bố → chờ cấu hình, 0 kết quả
        self.assertEqual((j["trang_thai"], j["ly_do"], j["the_he"]), ("CHO_CAU_HINH", "CRM_G5_DANG_KY_DOI", 2))
        self.assertEqual(self.dem("crm_g5_ket_qua", N["ky"]), trc)
        self.s["client"] = T._E5()
        self.doi_soat(N["ky"], "n-dk-2")
        self.drain()  # đăng ký hiện hành quay về dk_demo → ý định thế hệ 2 (dk_demo2) khác đăng ký → THẾ HỆ 3, request_id mới
        j = self.viec(a["job_id"])
        self.assertEqual((j["trang_thai"], j["the_he"]), ("XONG", 3))
        self.assertEqual(self.q("SELECT request_id FROM master.crm_g5_ket_qua WHERE id = %s", (j["ket_qua_id"],)), f"crm-g5-{a['job_id']}-3")
        self.assertEqual(self.q("SELECT dang_ky_id::text FROM master.crm_g5_ket_qua WHERE id = %s", (j["ket_qua_id"],)), dk_cu)
        self.assertIn(("THE_HE_MOI", "NGUOI_DUNG", KT), self.su_kien(a["job_id"]))

    # ------------------------------------------------------------------ p09: đăng ký nhãn VAN_HANH (TEST-ONLY) + thủ công LECH → G6 xử lý lệch
    def test_p09_thu_cong_lech_g6_xu_ly(self):
        self.can("dk_demo", "M1", "pv_M1")
        M1 = self.s["M1"]
        self.s["dk_vh"] = self.dang_ky(M1["ky"], "VAN_HANH",
                                       "TEST-ONLY DEMO CLONE — nhãn VAN_HANH chỉ để đo nhánh dương có điều kiện; KHÔNG phải đăng ký vận hành")
        w = self.view(KT, M1["ky"])
        self.assertEqual([c["ma"] for c in w["g6"]["chan"]], ["G5_KET_QUA_CU"])  # kết quả DEMO cũ không tính cho đăng ký mới
        self.assertFalse(w["current_result"]["hien_hanh"])
        self.s["client"] = T._E5(tao=_lech_gia_tri)
        a = self.lenh(KT, "chay", M1["ky"], w["context_sha256"], self.K("m1-lech"))
        self.drain()
        j = self.viec(a["job_id"])
        self.assertEqual((j["loai"], j["trang_thai"]), ("THU_CONG", "XONG"))
        w = self.view(KT, M1["ky"])
        cr = w["current_result"]
        self.assertEqual((cr["trang_thai"], cr["hien_hanh"], cr["nhan_dang_ky"], cr["tac_nhan_loai"], cr["so_lech"]),
                         ("LECH", True, "VAN_HANH", "NGUOI_DUNG", 1))
        ts = {t["ma"]: t for t in cr["tham_so"]}
        self.assertEqual(set(ts["GIA_TRI_HD"]), {"ma", "crm_truong", "muc", "kieu", "gia_tri_ky_vong", "gia_tri_ban_ky", "trich_dan", "vi_tri_do_duoc",
                                                 "trang_thai"})
        self.assertEqual((ts["GIA_TRI_HD"]["trang_thai"], ts["GIA_TRI_HD"]["muc"], ts["GIA_TRI_HD"]["gia_tri_ban_ky"]),
                         ("LECH", 3, {"so_tien": "100000000", "tien_te": "VND"}))
        self.assertEqual(ts["LICH_TT"]["trang_thai"], "KHOP")
        self.assertEqual(len(w["history"]), 1)  # kết quả DEMO cũ chỉ ở lịch sử, tách khỏi hiện hành
        self.assertEqual((w["g6"]["trang_thai"], w["g6"]["lech"]), ("LECH", [{"ma": "GIA_TRI_HD", "khoa": "GIA_TRI_HD", "muc": 3}]))
        kq = cr["result_id"]
        r1 = self.ok(KT, "giao-ket/kiem/luu", HK._than_luu(ky_id=M1["ky"], khoa=self.K("m1-luu")))
        c1 = self.ok(KT, "giao-ket/kiem/check", {"ky_id": M1["ky"], "expected_revision": r1["revision"], "khoa": self.K("m1-c1")})
        chan = {(x["ma"], x.get("muc")) for x in c1["check"]["chan"]}
        self.assertIn(("G5_LECH_CHUA_XU_LY", "GIA_TRI_HD"), chan)
        self.assertNotIn("UNREGISTERED_G5_PROOF", {m for m, _ in chan})
        self.ok(KT, "giao-ket/kiem/xu-ly-lech", {"ky_id": M1["ky"], "expected_revision": r1["revision"], "loai": "G5_LECH", "muc_tieu_id": kq,
                                                  "ma_lech": "GIA_TRI_HD", "ly_do": "DEMO: bản ký là căn cứ (khách sửa tay)", "khoa": self.K("m1-xl")})
        c2 = self.ok(KT, "giao-ket/kiem/check", {"ky_id": M1["ky"], "expected_revision": r1["revision"], "khoa": self.K("m1-c2")})
        self.assertNotIn("G5_LECH_CHUA_XU_LY", {x["ma"] for x in c2["check"]["chan"]})
        self.assertIn("G5_LECH_THEO_BAN_KY", {x["ma"] for x in c2["check"]["canh_bao"]})
        self.s["m1_c2"], self.s["m1_rev"], self.s["m1_kq_lech"] = c2["check"], r1["revision"], kq

    # ------------------------------------------------------------------ p10: kết quả mới → check cũ bị từ chối; lệch cũ không còn xử lý được
    def test_p10_ket_qua_moi_check_cu_bi_tu_choi(self):
        self.can("m1_c2")
        M1 = self.s["M1"]
        self.s["client"] = T._E5()
        w = self.view(KT, M1["ky"])
        self.lenh(KT, "chay", M1["ky"], w["context_sha256"], self.K("m1-khop"))
        self.drain()
        w = self.view(KT, M1["ky"])
        self.assertEqual((w["current_result"]["trang_thai"], w["g6"]["trang_thai"], w["g6"]["chan"]), ("KHOP", "KHOP", []))
        st, r, _ = self.goi("/api/crm/giao-ket/kiem/hieu-luc", {"ky_id": M1["ky"], "expected_revision": self.s["m1_rev"],
                                                                 "check_id": self.s["m1_c2"]["check_id"], "do_thi_sha256": self.s["m1_c2"]["do_thi_sha256"],
                                                                 "khoa": self.K("m1-hl-cu")}, self.sid(KT))
        self.assertEqual(st, 409, r)
        self.assertIn(r["error"], ("CRM_KIEM_CHECK_CU", "CRM_KIEM_CHUA_DU_DIEU_KIEN"))
        self.assertEqual(self.dem("crm_kiem_hieu_luc", M1["ky"]), 0)
        self.loi(KT, "giao-ket/kiem/xu-ly-lech", {"ky_id": M1["ky"], "expected_revision": self.s["m1_rev"], "loai": "G5_LECH",
                                                   "muc_tieu_id": self.s["m1_kq_lech"], "ma_lech": "SO_HD", "ly_do": "DEMO", "khoa": self.K("m1-xl-cu")},
                 409, "CRM_KIEM_LECH_KHONG_CON")

    # ------------------------------------------------------------------ p11: việc BẮT BUỘC dương có điều kiện (người chạy cấu hình + đăng ký nhãn VAN_HANH)
    def test_p11_bat_buoc_duong_co_dieu_kien(self):
        self.can("nc", "M2", "pv_M2")
        M2 = self.s["M2"]
        v = self.viec(M2["viec_bb"])
        self.assertIn(v["trang_thai"], ("CHO_CAU_HINH",), "việc bắt buộc M2 phải còn mở (mẫu riêng chưa đăng ký)")
        self.assertEqual(self.dem("crm_g5_ket_qua", M2["ky"]), 0)
        self.s["dk_vh2"] = self.dang_ky(M2["ky"], "VAN_HANH",
                                        "TEST-ONLY DEMO CLONE — nhãn VAN_HANH chỉ để đo nhánh dương có điều kiện; KHÔNG phải đăng ký vận hành")
        self.thu_hoi_g5("NGUOI_CHAY", self.s["nc"])  # thu hồi cấu hình → chờ, giữ việc
        self.s["client"] = T._E5()
        self.doi_soat(M2["ky"], "m2-1")
        self.drain()
        v = self.viec(M2["viec_bb"])
        self.assertEqual((v["trang_thai"], v["ly_do"]), ("CHO_CAU_HINH", "THIEU_NGUOI_CHAY"))
        self.assertEqual(self.s["client"].goi, [])
        self.s["nc2"] = self.nguoi_chay(self.s["pc_kt"])
        self.doi_soat(M2["ky"], "m2-2")
        self.drain()
        v = self.viec(M2["viec_bb"])
        self.assertEqual(v["trang_thai"], "XONG")
        x = self.admin.execute("SELECT trang_thai, tac_nhan_loai, tac_nhan, dang_ky_id::text FROM master.crm_g5_ket_qua WHERE id = %s",
                               (v["ket_qua_id"],)).fetchone()
        self.assertEqual(tuple(x), ("KHOP", "SYSTEM_JOB", KT, self.s["dk_vh2"]))
        w = self.view(KT, M2["ky"])
        self.assertEqual((w["g6"]["trang_thai"], w["g6"]["chan"], w["readiness"]), ("KHOP", [], {"san_sang": True, "ly_do": []}))
        self.assertEqual(w["khoi_tao"]["trang_thai"], "PENDING")  # khởi tạo G4 giữ nguyên
        su = self.su_kien(M2["viec_bb"])
        self.assertTrue(all(tn in ("SYSTEM_JOB", "HE_THONG", "NGUOI_DUNG") for _, tn, _ in su))
        self.assertTrue(any(e == ("KET_QUA", "SYSTEM_JOB", KT) for e in su))  # audit việc hệ thống tách lệnh đối soát của người dùng
        self.assertTrue(any(e[0] == "DOI_SOAT" and e[1] == "NGUOI_DUNG" for e in su))
        self.assertEqual(self.dem("crm_kiem_ho_so", M2["ky"]), 0)  # người chạy KHÔNG bị đánh dấu đã kiểm/duyệt

    # ================================================================== FIX01 (bổ sung; WRITTEN_NOT_RUN)
    def y_dinh_viec(self, viec_id):
        return self.q("SELECT count(*) FROM master.crm_g5_y_dinh WHERE viec_id = %s", (viec_id,))

    # ------------------------------------------------------------------ p12: CHUA_DOI_CHIEU_DUOC công bố nhưng nghĩa vụ bắt buộc VẪN MỞ; cùng đăng ký không POST lại
    def test_p12_chua_doi_chieu_duoc_giu_nghia_vu(self):
        self.can("nc2", "pc_kt")
        hd_f = self.s.get("hd_factory")  # FIX01-C: factory G thường đã dựng đúng một worker G5 (không lỗi khởi tạo)
        self.assertIsInstance(hd_f, DC.HangDoiG5)
        self.assertIsNone(self.s.get("loi_khoi_tao_g5"))
        # mẫu RIÊNG pb3 cho M3/M4 (đăng ký khớp theo mẫu đã ghim) → không đụng việc/đăng ký của N/M1/M2
        self.s["pb3"], _ = self.mau_hieu_luc("HD_G5B3_" + self.run_id, ngay(-2), "MAU G5B3")
        for tag in ("M3", "M4"):
            h = self.dung_hop_dong(tag.lower(), co_sua=True, pb=self.s["pb3"])
            (h["viec_bb"],) = self.viec_bat_buoc(h["ky"])
            self.s["pv_" + tag] = self.pham_vi_kiem(self.s["pc_kt"], h["ky"])
            self.s[tag] = h
        M3, M4 = self.s["M3"], self.s["M4"]
        self.s["dk_vh3"] = self.dang_ky(M3["ky"], "VAN_HANH",
                                        "TEST-ONLY DEMO CLONE — nhãn VAN_HANH chỉ để đo FIX01-D; KHÔNG phải đăng ký vận hành")
        e5 = T._E5(tao=lambda y: T._g5(y, "CHUA_DOI_CHIEU_DUOC", coverage=[], thieu=[t["ma"] for t in y["expected"]["tham_so"]]))
        self.s["client"] = e5
        self.drain()
        self.assertEqual(sorted(g["request_id"] for g in e5.goi), sorted(f"crm-g5-{h['viec_bb']}-1" for h in (M3, M4)))
        for h in (M3, M4):
            v = self.viec(h["viec_bb"])
            self.assertEqual((v["trang_thai"], v["ly_do"], v["ket_qua_id"], v["the_he"], v["so_lan"]),
                             ("CHO_CAU_HINH", "G5_CHUA_DOI_CHIEU_DUOC", None, 1, 1))  # KHÔNG XONG
            x = self.admin.execute("""SELECT id::text, trang_thai, tac_nhan_loai, request_id, dang_ky_id::text FROM master.crm_g5_ket_qua
                                      WHERE ky_id = %s""", (h["ky"],)).fetchall()
            self.assertEqual([tuple(r)[1:] for r in x], [("CHUA_DOI_CHIEU_DUOC", "SYSTEM_JOB", f"crm-g5-{h['viec_bb']}-1", self.s["dk_vh3"])])
            h["kq_chua"] = x[0][0]  # kết quả/raw/ID CHUA vẫn công bố và giữ trong lịch sử
            su = self.su_kien(h["viec_bb"])
            self.assertIn(("KET_QUA", "SYSTEM_JOB", KT), su)
            self.assertIn(("CHO_CAU_HINH", "SYSTEM_JOB", KT), su)
            self.assertNotIn("XONG", [e[0] for e in su])
            w = self.view(KT, h["ky"])
            self.assertEqual((w["current_job"]["job_id"], w["current_job"]["ly_do"], w["current_result"]["trang_thai"]),
                             (h["viec_bb"], "G5_CHUA_DOI_CHIEU_DUOC", "CHUA_DOI_CHIEU_DUOC"))
            self.assertEqual((w["g6"]["trang_thai"], [c["ma"] for c in w["g6"]["chan"]]), ("HOLD", ["G5_CHUA_DOI_CHIEU_DUOC"]))
        # poll/restart cùng đăng ký: đối soát đưa về CHO, drain → chờ có căn cứ; 0 ý định/request/engine call/kết quả mới
        e5b = T._E5()
        self.s["client"] = e5b
        for h in (M3, M4):
            self.doi_soat(h["ky"], "chua-" + h["viec_bb"][:8])
        moi = DC.CrmDoiChieuK2(self.dv.kiem, client_fn=lambda goc: self.s["client"])  # worker mới (như sau restart)
        DC.HangDoiG5(moi, self.app.mutation_lock, db=self.app._crm_db).mot_luot()
        self.drain()
        self.assertEqual(e5b.goi, [])
        for h in (M3, M4):
            v = self.viec(h["viec_bb"])
            self.assertEqual((v["trang_thai"], v["ly_do"], v["the_he"], v["so_lan"]), ("CHO_CAU_HINH", "G5_CHUA_DOI_CHIEU_DUOC", 1, 1))
            self.assertEqual((self.y_dinh_viec(h["viec_bb"]), self.dem("crm_g5_ket_qua", h["ky"])), (1, 1))
            self.assertNotIn("NHAN", [e[0] for e in self.su_kien(h["viec_bb"])][-2:])  # không nhận/lease lại cùng thế hệ

    # ------------------------------------------------------------------ p13: kết quả HOÀN TẤT của đăng ký hiện hành (thủ công có kiểm soát) đóng nghĩa vụ
    def test_p13_ket_qua_hoan_tat_dong_nghia_vu(self):
        self.can("M3", "dk_vh3")
        M3 = self.s["M3"]
        e5 = T._E5()
        self.s["client"] = e5
        w = self.view(KT, M3["ky"])
        a = self.lenh(KT, "chay", M3["ky"], w["context_sha256"], self.K("m3-thu-cong"))
        self.assertNotEqual(a["job_id"], M3["viec_bb"])
        self.drain()  # việc bắt buộc chưa đến hạn (chờ 15 phút) → chỉ việc thủ công chạy
        j = self.viec(a["job_id"])
        self.assertEqual((j["loai"], j["trang_thai"]), ("THU_CONG", "XONG"))
        self.assertEqual([g["request_id"] for g in e5.goi], [f"crm-g5-{a['job_id']}-1"])
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_g5_ket_qua WHERE id = %s", (j["ket_qua_id"],)), "KHOP")
        self.doi_soat(M3["ky"], "m3-sau-thu-cong")
        self.drain()
        v = self.viec(M3["viec_bb"])
        self.assertEqual((v["trang_thai"], v["ly_do"], v["ket_qua_id"]), ("XONG", "DA_CO_KET_QUA_HIEN_HANH", j["ket_qua_id"]))
        self.assertEqual((len(e5.goi), self.y_dinh_viec(M3["viec_bb"])), (1, 1))  # đóng không gọi engine lần nữa
        self.assertEqual(self.q("SELECT trang_thai FROM master.crm_g5_ket_qua WHERE id = %s", (M3["kq_chua"],)), "CHUA_DOI_CHIEU_DUOC")
        w = self.view(KT, M3["ky"])
        self.assertEqual((w["current_job"], w["current_result"]["trang_thai"], w["g6"]["trang_thai"]), (None, "KHOP", "KHOP"))
        self.assertIn("CHUA_DOI_CHIEU_DUOC", [z["trang_thai"] for z in w["history"]])  # CHUA giữ trong lịch sử

    # ------------------------------------------------------------------ p14: đăng ký mới (implementation/catalog đổi) → thế hệ mới, request_id mới → hoàn tất
    def test_p14_dang_ky_moi_tiep_tuc(self):
        self.can("M4", "dk_vh3")
        M4 = self.s["M4"]
        self.assertEqual(self.viec(M4["viec_bb"])["ly_do"], "G5_CHUA_DOI_CHIEU_DUOC")
        self.s["dk_vh3b"] = self.dang_ky(M4["ky"], "VAN_HANH", "TEST-ONLY DEMO CLONE — đăng ký thay thế (catalog/implementation mới giả lập)")
        e5 = T._E5()
        self.s["client"] = e5
        self.doi_soat(M4["ky"], "m4-dk-moi")
        self.drain()
        v = self.viec(M4["viec_bb"])
        self.assertEqual((v["trang_thai"], v["the_he"]), ("XONG", 2))
        self.assertEqual([g["request_id"] for g in e5.goi], [f"crm-g5-{M4['viec_bb']}-2"])  # request_id mới, không lặp request thế hệ 1
        x = self.admin.execute("SELECT trang_thai, request_id, dang_ky_id::text FROM master.crm_g5_ket_qua WHERE id = %s",
                               (v["ket_qua_id"],)).fetchone()
        self.assertEqual(tuple(x), ("KHOP", f"crm-g5-{M4['viec_bb']}-2", self.s["dk_vh3b"]))
        self.assertIn(("THE_HE_MOI", "SYSTEM_JOB", KT), self.su_kien(M4["viec_bb"]))
        self.assertEqual(self.y_dinh_viec(M4["viec_bb"]), 2)

    # ------------------------------------------------------------------ p15: lease hết hạn → kết thúc/ý định/công bố KHÔNG áp dụng, kể cả chưa ai claim lại
    def test_p15_lease_het_han_khong_ap_dung(self):
        self.can("M3", "pv_M3")
        M3 = self.s["M3"]
        e5a, e5b = T._E5(), T._E5()
        w = self.view(KT, M3["ky"])
        j = self.lenh(KT, "chay", M3["ky"], w["context_sha256"], self.K("m3-lease"))["job_id"]
        muc = {"viec_id": j, "nguoi_chay": KT}
        a = DC.CrmDoiChieuK2(self.dv.kiem, client_fn=lambda goc: e5a, lease_giay=600)
        b = DC.CrmDoiChieuK2(self.dv.kiem, client_fn=lambda goc: e5b)
        with self.app.mutation_lock:
            pa = self.app._crm_db(a.nhan, muc)
            self.assertTrue(pa["nhan"])
            pa = self.app._crm_db(a.chuan_bi, pa)
        loai, kq_a = a.goi_engine(pa)  # engine của A trả xong NGOÀI khóa …
        self.assertEqual(loai, "KET_QUA")
        # … nhưng lease đã hết (chủ CSDL đặt lease_den về quá khứ trên bản sao DEMO thay vì ngủ 10 phút)
        self.admin.execute("UPDATE master.crm_g5_viec SET lease_den = now() - interval '1 second' WHERE id = %s", (j,))
        truoc = (self.viec(j), self.su_kien(j), self.dem("crm_g5_ket_qua", M3["ky"]), self.y_dinh_viec(j))
        with self.app.mutation_lock:
            r = self.app._crm_db(a.ket_thuc, pa, "CHUA_RO", "TEST_HET_LEASE", 120)
            self.assertEqual(r, {"ap_dung": False})
            for fn, args in ((a.cong_bo, (pa, kq_a)), (a.chuan_bi, (pa,))):
                with self.assertRaises(DataError) as cm:
                    self.app._crm_db(fn, *args)
                self.assertEqual(cm.exception.code, "CRM_G5_LEASE_MAT", fn.__name__)
        self.assertEqual((self.viec(j), self.su_kien(j), self.dem("crm_g5_ket_qua", M3["ky"]), self.y_dinh_viec(j)), truoc)  # 0 đổi trạng thái/lịch sử
        self.assertEqual(self.viec(j)["trang_thai"], "DANG_CHAY")
        # claim mới vẫn tiếp tục (cùng thế hệ/request_id của ý định đã ghi)
        with self.app.mutation_lock:
            pb = self.app._crm_db(b.nhan, muc)
        self.assertEqual((pb["nhan"], pb["the_he"], pb["request_id"]), (True, pa["the_he"], pa["request_id"]))
        self.assertEqual(self.viec(j)["so_lan"], truoc[0]["so_lan"] + 1)
        with self.app.mutation_lock:  # chủ cũ / thế hệ cũ vẫn bị chặn sau khi B giữ lease
            self.assertEqual(self.app._crm_db(a.ket_thuc, pa, "CHUA_RO", "TEST_CHU_CU", 120), {"ap_dung": False})
            self.assertEqual(self.app._crm_db(b.ket_thuc, {**pb, "the_he": pb["the_he"] + 1}, "CHUA_RO", "TEST_THE_HE_KHAC", 120), {"ap_dung": False})
            with self.assertRaises(DataError) as cm:
                self.app._crm_db(a.cong_bo, pa, kq_a)
            self.assertEqual(cm.exception.code, "CRM_G5_LEASE_MAT")
            pb = self.app._crm_db(b.chuan_bi, pb)
        self.assertEqual(self.viec(j)["trang_thai"], "DANG_CHAY")
        loai, kq_b = b.goi_engine(pb)
        with self.app.mutation_lock:
            r = self.app._crm_db(b.cong_bo, pb, kq_b)
        self.assertEqual((r["trang_thai"], r["viec_trang_thai"]), ("KHOP", "XONG"))
        self.assertEqual([g["request_id"] for g in e5b.goi], [pa["request_id"]])
        self.assertEqual(self.y_dinh_viec(j), 1)


if __name__ == "__main__":
    unittest.main()
