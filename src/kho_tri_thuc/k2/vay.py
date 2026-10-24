"""M9 — khoản vay typed trên K2 PostgreSQL (binding 28af9c1, proposal e3e9704f): nhận nguồn #9 qua adapter đã pin → snapshot/row →
mapping công ty/ngân hàng/dự án do CFO V4 duyệt → lập HĐ VAY/phiên bản typed theo từng pháp nhân → kế toán kiểm (vân tay toàn đồ thị)
→ CFO duyệt V3 (+V4 HĐ mới) → lịch trả nợ/khế ước hiệu lực → nối tiền BANK M1 (parent CHILD + child theo đích logic, biên nhận
idempotent, ngân sách BANK chung với CRM) → file soát.

Tái dùng: HĐ/PB/việc/nhật ký/lô xuất/export writer của CRM-01 (kế thừa CrmK2 cho danh tính phiên, giao dịch, nhật ký), lớp liên kết
chung `lien_ket_chung`. Không parser doanh thu CRM, không engine lãi, không tạo SAO_KE/bút toán 112, không đề xuất định khoản (chưa có
template/policy M9 — giữ task, xem `khoang_trong`). Mọi số tiền ra API/file là chuỗi (lossless).
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal

from ..ha_tang.primitives import DataError, canonical_json, now_utc, sha256
from ..ha_tang.store import write_immutable
from ..nguon import vay_9
from . import lien_ket_chung as lkc
from . import quyen
from .crm import CrmK2, _j, _s

MODULE = "M9"
INSTANCE_DEMO = "SHEET_VAY_DEMO_1"
LUA_CHON_PHAM_VI = {"DUNG_DRAW": "Lịch gốc theo khế ước (DRAW) là nghĩa vụ; dòng LOAN cùng kỳ chỉ là tổng tham chiếu",
                    "DUNG_LOAN": "Lịch gốc cấp HĐ (LOAN) là nghĩa vụ; dòng DRAW cùng kỳ chỉ là chi tiết tham chiếu"}
TRANSFORM = "M9_TACH_PN_V1"


def _iso(v):
    return v.isoformat() if isinstance(v, date) else (str(v) if isinstance(v, Decimal) else v)


def _so_nguyen_duong(v, ma="SO_TIEN") -> int:
    """Số tiền từ client: chuỗi/số nguyên dương (minor). Không nhận float/bool/phân cách."""
    if isinstance(v, bool) or not isinstance(v, (str, int)) or not str(v).strip().isdigit():
        raise DataError(ma, "Số tiền phải là số nguyên dương (đơn vị nhỏ nhất của loại tiền), dạng chữ số.")
    n = int(str(v).strip())
    if n <= 0 or n > vay_9.INT64:
        raise DataError(ma, "Số tiền phải dương và trong miền int64.")
    return n


class VayK2(CrmK2):
    """conn: psycopg autocommit, dict_row, login ứng dụng (thành viên app_web). Dùng chung danh tính/giao dịch/nhật ký với CrmK2."""

    # ------------------------------------------------------------------ hạ tầng riêng M9
    def _viec(self, pn, loai, bang, ref, tom_tat, ly_do_cho, *, vai_tro="CFO"):
        row = self.conn.execute("""SELECT id FROM kho.viec_can_duyet WHERE tham_chieu_bang = %s AND tham_chieu_id = %s
                                   AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG')""", (bang, ref)).fetchone()
        if row:
            self.conn.execute("UPDATE kho.viec_can_duyet SET ly_do_cho = %s, tom_tat = coalesce(%s, tom_tat), cap_nhat_luc = now() WHERE id = %s",
                              (list(ly_do_cho), tom_tat, row["id"]))
            return row["id"]
        return self.conn.execute("""INSERT INTO kho.viec_can_duyet (phap_nhan_id, loai, chu_trinh, module, tham_chieu_bang, tham_chieu_id, nguoi_duyet_vai_tro, tom_tat, ly_do_cho)
                                    VALUES (%s,%s,'M9',%s,%s,%s,%s,%s,%s) RETURNING id""",
                                 (pn, loai, MODULE, bang, ref, vai_tro, tom_tat, list(ly_do_cho))).fetchone()["id"]

    def _khoa_hd(self, hd_id) -> dict:
        lkc.khoa(self.conn, [hd_id])
        hd = self.conn.execute("SELECT * FROM master.hop_dong WHERE id = %s AND loai = 'VAY'", (hd_id,)).fetchone()
        if not hd:
            raise DataError("HOP_DONG_VAY", "Không thấy hợp đồng vay (hoặc ngoài quyền).")
        return hd

    def _pb(self, pb_id) -> dict:
        pb = self.conn.execute("""SELECT p.*, h.phap_nhan_id, h.loai AS loai_hd FROM master.hop_dong_phien_ban p JOIN master.hop_dong h ON h.id = p.hop_dong_id
                                  WHERE p.id = %s""", (pb_id,)).fetchone()
        if not pb or pb["loai_hd"] != "VAY":
            raise DataError("PHIEN_BAN", "Không thấy phiên bản hợp đồng vay (hoặc ngoài quyền).")
        return pb

    def _raw(self, s) -> bytes:
        path = (self.root / "m9-tep" / f"{s['raw_sha256']}.bin").resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            raise DataError("NGUON_RAW_THIEU", "Không thấy tệp nguồn đã nhận của snapshot.")
        raw = path.read_bytes()
        if sha256(raw) != s["raw_sha256"]:
            raise DataError("ARTIFACT_CHANGED", "Tệp nguồn đã bị thay đổi sau khi nhận.")
        return raw

    def _scale(self, cur) -> int | None:
        if cur is None:
            return None
        row = self.conn.execute("SELECT scale FROM master.don_vi_tien WHERE ma = %s ORDER BY phien_ban DESC LIMIT 1", (cur,)).fetchone()
        if row is None or row["scale"] != vay_9.TIEN_TE_SCALE.get(cur):
            raise DataError("TIEN_TE_REGISTRY_LECH", f"Scale {cur} của adapter khác registry CSDL — dừng, không đoán.")
        return row["scale"]

    # ------------------------------------------------------------------ M0/K1: nhận nguồn
    def nhan_mau(self, dang_nhap, mau: str) -> dict:
        from ..kiem_chung.fixtures_m9 import MAU, bytes_cua
        if mau not in MAU:
            raise DataError("M9_MAU", "Không có mẫu nguồn khoản vay DEMO này.")
        code, build = MAU[mau]
        return self.nhan_tep(dang_nhap, code, bytes_cua(build()), f"DEMO:{mau}")

    def nhan_tep(self, dang_nhap, profile_code: str, raw: bytes, object_key: str, *, instance: str = INSTANCE_DEMO) -> dict:
        """Raw giữ nguyên (content-addressed) TRƯỚC khi đọc; snapshot + row qua hàm integration (metadata raw không cấp app). PN của row do
        mapping COMPANY đã duyệt quyết định; công ty chưa map → row giữ không PN, tạo ứng viên mapping (không ép PN giả)."""
        dt = self.danh_tinh(dang_nhap)
        if not quyen.pham_vi(dt, "M9_INTAKE"):
            raise DataError("KHONG_CO_QUYEN_HANH_DONG", "Cần kế toán có module M9 để nhận nguồn khoản vay.")
        if profile_code not in vay_9.PROFILES:
            raise DataError("M9_PROFILE_KHONG_HO_TRO", "Profile nguồn khoản vay chưa được pin.")
        profile = vay_9.PROFILES[profile_code]
        raw_sha, bat_dau = sha256(raw), now_utc()
        write_immutable(self.root / "m9-tep" / f"{raw_sha}.bin", raw)
        snap = vay_9.doc(profile_code, raw)
        rows = [] if snap.state == "REJECTED" else [r.as_payload() for r in snap.rows]
        p = {"source_instance_id": instance, "object_key": object_key, "raw_sha256": raw_sha, "byte_length": len(raw), "media_type": "application/json",
             "profile_code": profile["code"], "profile_version": profile["version"], "profile_sha256": vay_9.profile_sha256(profile),
             "source_code_sha256": profile.get("source_code_sha256"), "ui_sha256": profile.get("ui_sha256"), "header_set_sha256": profile.get("header_set_sha256"),
             "transport": profile["transport"], "typed_sha256": snap.typed_sha256, "received_started_at": bat_dau, "received_finished_at": now_utc(),
             "exported_at_source": snap.exported_at, "coverage_kind": snap.coverage_kind, "coverage_manifest": snap.coverage_manifest, "state": snap.state,
             "error_code": snap.loi[0] if snap.loi else None, "loi": snap.loi, "rows": rows}
        with self._tx(dt):
            r = self.conn.execute("SELECT * FROM giao_tiep.ghi_anh_chup(%s::jsonb)", (json.dumps(p, ensure_ascii=False),)).fetchone()
            if r["moi"]:
                self._su_kien(None, dt, "NGUON_TU_DONG", "kho.anh_chup_nguon", r["snapshot_id"], "M9_NHAN_ANH_CHUP",
                              sau={"profile": profile["code"], "raw_sha256": raw_sha, "state": snap.state, "so_dong": len(rows), "object_key": object_key})
            for snap_id in self._snapshot_cho_map():  # công ty đã map từ trước: gán PN ngay cho row mới
                self.conn.execute("SELECT giao_tiep.gan_phap_nhan_theo_anh_xa(%s)", (snap_id,))
            cho_map = [x["source_company_key"] for x in self.conn.execute("SELECT * FROM giao_tiep.cong_ty_chua_map()")
                       if str(r["snapshot_id"]) in {str(i) for i in x["snapshot_ids"]}]
        dem: dict[str, int] = {}
        for x in snap.rows:
            dem[x.section] = dem.get(x.section, 0) + 1
        return {"snapshot_id": str(r["snapshot_id"]), "moi": r["moi"], "trang_thai": snap.state, "pham_vi": snap.coverage_kind, "loi": snap.loi,
                "raw_sha256": raw_sha, "so_dong": dem, "dong_loi": [{"section": x.section, "locator": x.locator, "loi": x.error} for x in snap.rows if x.state != "HOP_LE"],
                "cong_ty_cho_map": sorted(set(cho_map))}

    def _snapshot_cho_map(self) -> list[str]:
        out = set()
        for x in self.conn.execute("SELECT * FROM giao_tiep.cong_ty_chua_map()").fetchall():
            out.update(str(i) for i in x["snapshot_ids"])
        return sorted(out)

    # ------------------------------------------------------------------ mapping nguồn (CFO V4 + M9), retarget có impact
    def xac_nhan_anh_xa(self, dang_nhap, kind: str, source_company_key: str, dich: str, *, source_value: str | None = None, ly_do: str = "",
                        instance: str = INSTANCE_DEMO) -> dict:
        """COMPANY: dich = mã pháp nhân. BANK: source_value = tên ngân hàng nguồn, dich = ObjectID đối tác của PN. PROJECT: source_value =
        mã dự án nguồn, dich = mã dự án Junsky của PN. Không tự sinh mã; chồng lấn/identity khóa do CSDL kiểm."""
        dt = self.danh_tinh(dang_nhap)
        if kind not in ("COMPANY", "BANK", "PROJECT") or not source_company_key or not dich:
            raise DataError("ANH_XA_TRUONG", "Mapping cần loại (COMPANY/BANK/PROJECT), công ty nguồn và đích.")
        with self._tx(dt):
            if kind == "COMPANY":
                pn, value = self._pn(dich), source_company_key
            else:
                c = self.conn.execute("""SELECT phap_nhan_id FROM master.anh_xa_nguon WHERE source_instance_id = %s AND source_company_key = %s
                                         AND kind = 'COMPANY' AND state = 'DA_DUYET' AND valid_to IS NULL""", (instance, source_company_key)).fetchone()
                if not c or not source_value:
                    raise DataError("ANH_XA_THIEU_CONG_TY", "Công ty nguồn chưa map pháp nhân (hoặc ngoài quyền) / thiếu giá trị nguồn.")
                pn, value = str(c["phap_nhan_id"]), source_value
            quyen.kiem(dt, "M9_MAP_APPROVE", pn)
            doi_tac = du_an = None
            if kind == "BANK":
                row = self.conn.execute("SELECT doi_tac_id FROM master.doi_tac_ma_junsky WHERE phap_nhan_id = %s AND object_id_junsky = %s AND valid_to IS NULL",
                                        (pn, dich)).fetchone()
                if not row:
                    raise DataError("MAPPING_KHONG_CO_MA", "ObjectID không có trong danh mục của pháp nhân — tạo ở Junsky trước; không tự sinh mã.")
                doi_tac = row["doi_tac_id"]
            elif kind == "PROJECT":
                row = self.conn.execute("SELECT id FROM master.du_an WHERE phap_nhan_id = %s AND ma_junsky = %s AND valid_to IS NULL", (pn, dich)).fetchone()
                if not row:
                    raise DataError("MAPPING_KHONG_CO_MA", "Mã dự án không có trong danh mục của pháp nhân.")
                du_an = row["id"]
            rev = self.conn.execute("""SELECT coalesce(max(revision), 0) + 1 AS n FROM master.anh_xa_nguon WHERE source_instance_id = %s AND source_company_key = %s
                                       AND kind = %s AND source_value = %s""", (instance, source_company_key, kind, value)).fetchone()["n"]
            m = self.conn.execute("""INSERT INTO master.anh_xa_nguon (source_instance_id, source_company_key, kind, source_value, phap_nhan_id, doi_tac_id, du_an_id,
                                     revision, duyet_boi, ly_do) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                                  (instance, source_company_key, kind, value, pn, doi_tac, du_an, rev, dt["dang_nhap"], str(ly_do or "")[:500] or None)).fetchone()["id"]
            gan = 0
            if kind == "COMPANY":
                for snap_id in self._snapshot_cho_map():
                    gan += self.conn.execute("SELECT giao_tiep.gan_phap_nhan_theo_anh_xa(%s) AS n", (snap_id,)).fetchone()["n"]
            self._su_kien(pn, dt, "SUA_DANH_MUC", "master.anh_xa_nguon", m, "M9_DUYET_ANH_XA",
                          sau={"kind": kind, "cong_ty": source_company_key, "nguon": value, "dich": dich, "revision": rev, "so_dong_gan": gan})
        return {"id": str(m), "revision": rev, "so_dong_gan_phap_nhan": gan}

    def anh_huong_anh_xa(self, dang_nhap, mapping_id) -> dict:
        """Impact trước khi đóng/retarget: dữ liệu đã lập theo mapping này KHÔNG tự chuyển PN (row đã gán bất biến, alias giữ HĐ cũ);
        snapshot sau theo mapping mới; alias trùng khóa nguồn ở PN khác bị chặn ALIAS_THUOC_PHAP_NHAN_KHAC."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            m = self.conn.execute("SELECT * FROM master.anh_xa_nguon WHERE id = %s", (mapping_id,)).fetchone()
            if not m:
                raise DataError("ANH_XA", "Không thấy mapping (hoặc ngoài quyền).")
            quyen.kiem(dt, "M9_READ", m["phap_nhan_id"])
            return self._anh_huong(m)

    def _anh_huong(self, m) -> dict:
        q = lambda sql, *a: self.conn.execute(sql, a).fetchone()["n"]
        alias = """FROM master.vay_dinh_danh_nguon a WHERE a.source_instance_id = %s AND a.source_company_key = %s AND a.phap_nhan_id = %s"""
        base = (m["source_instance_id"], m["source_company_key"], m["phap_nhan_id"])
        return {"mapping_id": str(m["id"]), "kind": m["kind"], "so_dong_nguon": q("SELECT count(*) AS n FROM kho.ban_ghi_nguon WHERE mapping_revision_id = %s", m["id"]),
                "so_hop_dong": q("SELECT count(*) AS n " + alias, *base),
                "so_phien_ban_da_duyet": q("""SELECT count(*) AS n FROM master.hop_dong_phien_ban p WHERE p.trang_thai = 'DA_DUYET' AND p.hop_dong_id IN
                                              (SELECT a.hop_dong_id """ + alias + ")", *base),
                "so_lien_ket_tien_hieu_luc": q("""SELECT count(*) AS n FROM kho.lien_ket_chung_tu k WHERE k.loai = 'VAY_TIEN' AND k.trang_thai <> 'HUY'
                                                  AND k.hop_dong_id IN (SELECT a.hop_dong_id """ + alias + ")", *base),
                "quy_tac": "Đóng mapping không chuyển dữ liệu đã lập; snapshot sau map theo mapping mới; khóa nguồn đã có HĐ ở PN cũ bị chặn ở PN mới."}

    def dong_anh_xa(self, dang_nhap, mapping_id, ly_do: str) -> dict:
        dt = self.danh_tinh(dang_nhap)
        if not ly_do or not str(ly_do).strip():
            raise DataError("CAN_LY_DO", "Đóng mapping cần lý do.")
        with self._tx(dt):
            m = self.conn.execute("SELECT * FROM master.anh_xa_nguon WHERE id = %s", (mapping_id,)).fetchone()
            if not m:
                raise DataError("ANH_XA", "Không thấy mapping (hoặc ngoài quyền).")
            quyen.kiem(dt, "M9_MAP_APPROVE", m["phap_nhan_id"])
            impact = self._anh_huong(m)
            self.conn.execute("UPDATE master.anh_xa_nguon SET state = 'DONG', valid_to = now() WHERE id = %s", (mapping_id,))
            self._su_kien(m["phap_nhan_id"], dt, "SUA_DANH_MUC", "master.anh_xa_nguon", mapping_id, "M9_DONG_ANH_XA", ly_do=str(ly_do)[:500], sau=impact)
        return impact

    # ------------------------------------------------------------------ lập HĐ/phiên bản typed theo pháp nhân (KT, nguyên tử theo PN)
    def lap_phien_ban(self, dang_nhap, snapshot_id, pn_ma: str, *, quyet_dinh: dict | None = None) -> dict:
        dt = self.danh_tinh(dang_nhap)
        pn = self._pn(pn_ma)
        quyen.kiem(dt, "M9_STAGE", pn)
        with self._tx(dt):
            return self._lap(dt, pn, snapshot_id, quyet_dinh or {})

    def _lap(self, dt, pn, snapshot_id, quyet_dinh, chi_khoa=None) -> dict:
        s = self.conn.execute("SELECT * FROM kho.anh_chup_nguon WHERE id = %s", (snapshot_id,)).fetchone()
        if not s:
            raise DataError("SNAPSHOT", "Không thấy snapshot nguồn (hoặc ngoài quyền).")
        if s["profile_code"] != vay_9.PROFILE_NATIVE["code"]:
            raise DataError("M9_PROFILE_KHONG_LAP", "Chỉ snapshot native #9 lập hồ sơ vay; bảng lãi xác nhận đi kèm theo pháp nhân.")
        if s["state"] == "REJECTED":
            raise DataError("SNAPSHOT_TU_CHOI", "Snapshot bị từ chối theo profile — giữ raw, không lập hồ sơ: " + ",".join(s["loi"] or []))
        native = vay_9.doc_native(self._raw(s))
        if native.typed_sha256 != s["typed_sha256"]:
            raise DataError("ADAPTER_KHONG_TAI_LAP", "Đọc lại raw không ra đúng typed đã ghi — dừng.")
        rows = self.conn.execute("SELECT id, section, locator, source_company_key, row_raw_sha256 FROM kho.ban_ghi_nguon WHERE snapshot_id = %s AND phap_nhan_id = %s",
                                 (snapshot_id, pn)).fetchall()
        cty = {r["source_company_key"] for r in rows}
        if not cty:
            raise DataError("M9_CHUA_CO_CONG_TY_MAP", "Snapshot chưa có công ty nguồn nào map vào pháp nhân này — CFO duyệt mapping trước.")
        ids = {(r["section"], r["locator"]): r["id"] for r in rows}
        bl = self.conn.execute("""SELECT s.* FROM kho.anh_chup_nguon s WHERE s.profile_code = %s AND s.state = 'VALIDATED' AND s.source_instance_id = %s
                                  AND EXISTS (SELECT 1 FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = s.id AND b.phap_nhan_id = %s)
                                  ORDER BY s.known_at_server DESC LIMIT 1""", (vay_9.PROFILE_BANG_LAI["code"], s["source_instance_id"], pn)).fetchone()
        bang_lai = None
        if bl:
            bang_lai = vay_9.doc_bang_lai(self._raw(bl))
            for r in self.conn.execute("SELECT id, section, locator FROM kho.ban_ghi_nguon WHERE snapshot_id = %s AND phap_nhan_id = %s", (bl["id"], pn)):
                ids[(r["section"], r["locator"])] = r["id"]
        maps = {(m["kind"], m["source_company_key"], m["source_value"]): m for m in self.conn.execute(
            """SELECT * FROM master.anh_xa_nguon WHERE source_instance_id = %s AND phap_nhan_id = %s AND state = 'DA_DUYET' AND valid_to IS NULL""",
            (s["source_instance_id"], pn))}
        tep = self._phai_sinh(dt, s, pn, rows, maps)
        graphs = vay_9.do_thi(native, bang_lai, cty)
        out = []
        for khoa in sorted(graphs, key=lambda k: tuple(x or "" for x in k)):
            if chi_khoa is not None and "/".join(x or "-" for x in khoa) not in chi_khoa:
                continue
            if khoa[2] is None:
                out.append({"khoa": "/".join(x or "-" for x in khoa), "ket_qua": "THIEU_KHOA_NGUON"})
                continue
            out.append(self._lap_mot(dt, pn, s, khoa, graphs[khoa], ids, maps, tep, bl, quyet_dinh.get("/".join(khoa))))
        return {"snapshot_id": str(snapshot_id), "bang_lai_snapshot_id": _s(bl["id"]) if bl else None, "khoan_vay": out}

    def _phai_sinh(self, dt, s, pn, rows, maps) -> str:
        """Tệp dẫn xuất theo PN (derivative): chỉ row của PN + pin mapping; raw đa PN giữ ở intake, không nới hash global."""
        row_sha = sorted(r["row_raw_sha256"] for r in rows)
        map_pin = sorted(f"{m['kind']}|{m['source_company_key']}|{m['source_value']}|{m['revision']}|{m['id']}" for m in maps.values())
        noi_dung = canonical_json({"v": TRANSFORM, "raw_sha256": s["raw_sha256"], "profile_sha256": s["profile_sha256"], "phap_nhan_id": str(pn),
                                   "rows": row_sha, "mapping": map_pin}).encode()
        h = sha256(noi_dung)
        write_immutable(self.root / "m9-tach" / f"{h}.json", noi_dung)
        tep = self.conn.execute("""INSERT INTO kho.tep_goc (phap_nhan_id, loai_nguon, duong_dan, hash, kich_thuoc, nguon, nguoi)
                                   VALUES (%s,'M9_TACH_PN',%s,%s,%s,'M9_SNAPSHOT',%s) ON CONFLICT (hash) DO NOTHING RETURNING id""",
                                (pn, f"m9-tach/{h}.json", h, len(noi_dung), dt["dang_nhap"])).fetchone()
        tep = tep or self.conn.execute("SELECT id FROM kho.tep_goc WHERE hash = %s AND phap_nhan_id = %s", (h, pn)).fetchone()
        if not tep:
            raise DataError("TEP_THUOC_PHAP_NHAN_KHAC", "Tệp dẫn xuất trùng hash ở pháp nhân khác — không gộp.")
        self.conn.execute("""INSERT INTO giao_tiep.tep_tach_phap_nhan (tep_tiep_nhan_id, snapshot_id, phap_nhan_id, tep_goc_id, profile_sha256, mapping_revision_sha256,
                             selected_rows_sha256, transformation_profile) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                          (s["tep_tiep_nhan_id"], s["id"], pn, tep["id"], s["profile_sha256"], sha256(canonical_json(map_pin).encode()),
                           sha256(canonical_json(row_sha).encode()), TRANSFORM))
        return tep["id"]

    def _dich(self, pn, kind, hd, ku, nv_key, cau_phan, logical_key):
        row = self.conn.execute("SELECT id FROM kho.dich_phan_bo_tien WHERE phap_nhan_id = %s AND module_nghiep_vu = 'M9' AND logical_key = %s",
                                (pn, logical_key)).fetchone()
        if row:
            return row["id"]
        return self.conn.execute("""INSERT INTO kho.dich_phan_bo_tien (phap_nhan_id, module_nghiep_vu, target_kind, hop_dong_id, khe_uoc_id, nghia_vu_key, cau_phan, logical_key)
                                    VALUES (%s,'M9',%s,%s,%s,%s,%s,%s) RETURNING id""", (pn, kind, hd, ku, nv_key, cau_phan, logical_key)).fetchone()["id"]

    def _lap_mot(self, dt, pn, s, khoa, g, ids, maps, tep, bl, qd_moi) -> dict:
        import psycopg
        sec, cty, key = khoa
        ten = f"{sec}/{cty}/{key}"
        rid = lambda r: ids.get((r.section, r.locator))
        if rid(g["row"]) is None:
            raise DataError("NGUON_DONG_CHUA_GAN_PN", f"Dòng nguồn {ten} chưa gán pháp nhân — chạy lại sau mapping.")
        m_bank = maps.get(("BANK", cty, g["ngan_hang"])) if g["ngan_hang"] else None
        m_prj = maps.get(("PROJECT", cty, g["du_an"])) if g["du_an"] else None
        blockers = set(g["blockers"])
        if not g["ngan_hang"]:
            blockers.add("THIEU_NGAN_HANG_NGUON")
        elif not m_bank:
            blockers.add("MAPPING_NGAN_HANG_NGUON")
        if g["du_an"] and not m_prj:
            blockers.add("MAPPING_DU_AN_NGUON")
        if s["state"] != "VALIDATED":
            blockers.add("NGUON_" + s["state"])
        alias = self.conn.execute("""SELECT * FROM master.vay_dinh_danh_nguon WHERE source_instance_id = %s AND source_section = %s AND source_company_key = %s
                                     AND source_key = %s""", (s["source_instance_id"], sec, cty, key)).fetchone()
        hd = self._khoa_hd(alias["hop_dong_id"]) if alias else None
        cu = None
        if hd:
            cu = self.conn.execute("""SELECT p.id, p.trang_thai, p.tham_so, v.source_revision_sha256 FROM master.hop_dong_phien_ban p
                                      JOIN master.vay_phien_ban v ON v.phien_ban_id = p.id WHERE p.hop_dong_id = %s AND p.trang_thai IN ('CHO_DUYET','DA_DUYET')
                                      ORDER BY p.phien_ban DESC LIMIT 1""", (hd["id"],)).fetchone()
        qd = qd_moi or ((cu["tham_so"] or {}).get("quyet_dinh_pham_vi") if cu else None)  # quyết định phạm vi đã có được giữ qua revision
        lich, bo_qua = list(g["lich"]), []
        if qd:
            bo = "LOAN" if qd["lua_chon"] == "DUNG_DRAW" else "DRAW"
            bo_qua = sorted(x["nghia_vu_key"] for x in lich if x["pham_vi"] == bo and x["cau_phan"] == "GOC")
            lich = [x for x in lich if x["nghia_vu_key"] not in bo_qua]
        g2 = {**g, "lich": lich, "blockers": blockers}
        noi_dung = {"typed": vay_9.noi_dung_typed(g2), "bank": m_bank and str(m_bank["id"]), "project": m_prj and str(m_prj["id"]),
                    "pham_vi": qd and qd["lua_chon"], "bo_qua": bo_qua, "nguon": s["state"]}
        rev_sha = sha256(canonical_json(noi_dung).encode())
        if cu and cu["source_revision_sha256"] == rev_sha:
            return {"khoa": ten, "hop_dong_id": str(hd["id"]), "phien_ban_id": str(cu["id"]), "ket_qua": "KHONG_DOI"}
        doi_tac = m_bank["doi_tac_id"] if m_bank else None
        du_an = m_prj["du_an_id"] if m_prj else None
        cur = g["currency"]
        scale = self._scale(cur)
        moi = hd is None
        if moi:
            so_hd = g["facts"].get("so_hop_dong_nguon")
            if not so_hd:  # số HĐ tạm có nhãn khóa nguồn + blocker — không bịa số hợp đồng
                blockers.add("THIEU_SO_HOP_DONG_NGUON")
                so_hd = f"[{sec}:{key}]"
            elif self.conn.execute("SELECT 1 FROM master.hop_dong WHERE phap_nhan_id = %s AND loai = 'VAY' AND so_hop_dong = %s", (pn, so_hd)).fetchone():
                blockers.add("SO_HOP_DONG_TRUNG_NGUON")
                so_hd = f"{so_hd} [{sec}:{key}]"
            try:
                with self.conn.transaction():
                    hd_id = self.conn.execute("""INSERT INTO master.hop_dong (phap_nhan_id, loai, ma_noi_bo, so_hop_dong, doi_tac_id, du_an_id, gia_tri_minor, tien_te, trang_thai)
                                                 VALUES (%s,'VAY',%s,%s,%s,%s,%s,%s,'CHO_DUYET') RETURNING id""",
                                              (pn, f"VAY9:{s['source_instance_id']}:{sec}:{cty}:{key}", so_hd, doi_tac, du_an,
                                               g["facts"].get("han_muc_minor") if sec == "DaiHan" else g["facts"].get("so_vay_vnd_minor"), cur or "VND")).fetchone()["id"]
                    alias = self.conn.execute("""INSERT INTO master.vay_dinh_danh_nguon (phap_nhan_id, source_instance_id, source_section, source_company_key, source_key,
                                                 hop_dong_id, first_known_at, tao_boi) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                                              (pn, s["source_instance_id"], sec, cty, key, hd_id, s["known_at_server"], dt["dang_nhap"])).fetchone()
            except psycopg.errors.UniqueViolation:
                return {"khoa": ten, "ket_qua": "CHAN_ALIAS_PHAP_NHAN_KHAC",
                        "chan": ["ALIAS_THUOC_PHAP_NHAN_KHAC: khóa nguồn đã có HĐ ở pháp nhân khác (retarget) — không tự chuyển"]}
            hd = self._khoa_hd(hd_id)
        else:
            if cu and cu["trang_thai"] == "CHO_DUYET":  # bản chờ cũ bị thay bởi revision nguồn mới (giữ vết)
                self.conn.execute("UPDATE master.hop_dong_phien_ban SET trang_thai = 'THAY_THE', ly_do = %s WHERE id = %s",
                                  ("Nguồn đổi — thay bằng phiên bản mới từ snapshot " + str(s["id"]), cu["id"]))
                self._dong_viec("master.hop_dong_phien_ban", cu["id"], "DONG", dt)
            if (doi_tac, du_an) != (hd["doi_tac_id"], hd["du_an_id"]):
                if hd["phien_ban_hien_hanh"] is None:
                    self.conn.execute("UPDATE master.hop_dong SET doi_tac_id = %s, du_an_id = %s WHERE id = %s", (doi_tac, du_an, hd["id"]))
                else:
                    blockers.add("MAPPING_DOI_SAU_DUYET")
        hd_id, alias_id = hd["id"], alias["id"]
        n = self.conn.execute("SELECT coalesce(max(phien_ban), 0) + 1 AS n FROM master.hop_dong_phien_ban WHERE hop_dong_id = %s", (hd_id,)).fetchone()["n"]
        tham_so = {"profile": {"code": s["profile_code"], "version": s["profile_version"], "sha256": s["profile_sha256"]}, "snapshot_id": str(s["id"]),
                   "raw_sha256": s["raw_sha256"], "bang_lai_snapshot_id": _s(bl["id"]) if bl else None, "source_revision_sha256": rev_sha,
                   "quyet_dinh_pham_vi": qd, "lich_bo_qua": bo_qua, "precision_contract": vay_9.PRECISION_CONTRACT["id"]}
        pb = self.conn.execute("""INSERT INTO master.hop_dong_phien_ban (hop_dong_id, phien_ban, loai, tep_goc_id, nguon, trang_thai, thay_cho_id, tao_boi, tham_so)
                                  VALUES (%s,%s,'GOC',%s,'SHEET','CHO_DUYET',%s,%s,%s) RETURNING id""",
                               (hd_id, n, tep, hd["phien_ban_hien_hanh"], dt["dang_nhap"], _j(tham_so))).fetchone()["id"]
        f = g["facts"]
        cols = ("so_hop_dong_nguon", "han_muc_minor", "du_no_nguon_minor", "ngay_du_no_nguon", "ky_han_nguon", "an_han_nguon", "quy_uoc_lai_nguon",
                "source_status", "so_nhan_no", "so_lc", "ngay_mo_lc", "ngay_nhan_no", "ngay_den_han", "ngay_tra_no_thuc_te", "so_vay_vnd_minor",
                "so_da_tra_vnd_minor", "so_nguyen_te_minor", "nguyen_te_code", "nguyen_te_scale", "source_fx_rate", "source_fx_basis", "ma_lien_ket_nguon")
        prec = "PROVEN" if g["precision"] == "PROVEN" else "UNPROVEN"
        pin = {"bank": m_bank and {"id": str(m_bank["id"]), "revision": m_bank["revision"]},
               "project": m_prj and {"id": str(m_prj["id"]), "revision": m_prj["revision"]}}
        self.conn.execute(f"""INSERT INTO master.vay_phien_ban (phien_ban_id, phap_nhan_id, hop_dong_id, source_alias_id, snapshot_id, source_row_id, source_revision_sha256,
                              financing_kind, currency_code, currency_scale, {", ".join(cols)}, chi_tiet_raw, precision_contract_id, precision_contract_version,
                              precision_status, precision_fields, blockers, mapping_pin, known_at_server)
                              VALUES ({", ".join(["%s"] * (10 + len(cols) + 8))})""",
                          (pb, pn, hd_id, alias_id, s["id"], rid(g["row"]), rev_sha, g["kind"], cur, scale, *[f.get(c) for c in cols],
                           _j(f.get("chi_tiet_raw")), vay_9.PRECISION_CONTRACT["id"], vay_9.PRECISION_CONTRACT["version"], prec,
                           _j({"vay": g["precision"]}), sorted(blockers), _j(pin), s["known_at_server"]))
        ku_id, ku_rev = {}, {}
        for ma, d in sorted(g["draws"].items()):
            row = self.conn.execute("SELECT id FROM master.khe_uoc_vay WHERE source_alias_id = %s AND ma_khe_uoc_nguon = %s", (alias_id, ma)).fetchone()
            ku_id[ma] = row["id"] if row else self.conn.execute(
                """INSERT INTO master.khe_uoc_vay (phap_nhan_id, hop_dong_id, source_alias_id, ma_khe_uoc_nguon, first_known_at, tao_boi)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""", (pn, hd_id, alias_id, ma, s["known_at_server"], dt["dang_nhap"])).fetchone()["id"]
            dich = self._dich(pn, "GIAI_NGAN", hd_id, ku_id[ma], None, "GIAI_NGAN", f"DRAW:{alias_id}:{ma}")
            noi = {"ma": ma, "ngay": _iso(d["ngay"]), "so_tien": d["so_tien"], "cur": cur, "p": d["precision"]}
            ku_rev[ma] = self.conn.execute("""INSERT INTO master.khe_uoc_vay_phien_ban (phap_nhan_id, khe_uoc_id, hop_dong_id, hop_dong_phien_ban_id, source_row_id,
                                              ngay_giai_ngan_nguon, so_tien_minor, currency_code, currency_scale, revision_sha256, precision_status, dich_phan_bo_id, known_at_server)
                                              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                                           (pn, ku_id[ma], hd_id, pb, rid(d["row"]), d["ngay"], d["so_tien"], cur, scale, sha256(canonical_json(noi).encode()),
                                            d["precision"], dich, s["known_at_server"])).fetchone()["id"]
        for r in g["rates"]:
            if r["ma"] not in ku_rev:
                continue
            noi = {"ma": r["ma"], "tu": _iso(r["ap_dung_tu"]), "pct": str(r["pct"]), "p": r["precision"]}
            self.conn.execute("""INSERT INTO master.lai_suat_vay (phap_nhan_id, khe_uoc_phien_ban_id, hop_dong_phien_ban_id, source_row_id, ap_dung_tu, lai_suat_pct_nam,
                                 quy_uoc_nguon, precision_status, revision_sha256, known_at_server) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                              (pn, ku_rev[r["ma"]], pb, rid(r["row"]), r["ap_dung_tu"], r["pct"], f.get("quy_uoc_lai_nguon"), r["precision"],
                               sha256(canonical_json(noi).encode()), s["known_at_server"]))
        for x in sorted(lich, key=lambda x: x["nghia_vu_key"]):
            ku = ku_id.get(x["ma_khe_uoc"]) if x["pham_vi"] == "DRAW" else None
            if x["pham_vi"] == "DRAW" and ku is None:
                continue  # blocker LICH_KHE_UOC_KHONG_CO đã ghi ở vay_phien_ban
            if rid(x["row"]) is None:
                raise DataError("NGUON_DONG_CHUA_GAN_PN", "Dòng lịch/bảng lãi chưa gán pháp nhân.")
            dich = self._dich(pn, "NGHIA_VU", hd_id, ku, x["nghia_vu_key"], x["cau_phan"], f"OBL:{alias_id}:{x['nghia_vu_key']}")
            truoc = self.conn.execute("""SELECT t.id FROM master.lich_tra_no t JOIN master.hop_dong_phien_ban p ON p.id = t.phien_ban_id
                                         WHERE t.dich_phan_bo_id = %s AND p.trang_thai = 'DA_DUYET' ORDER BY p.phien_ban DESC LIMIT 1""", (dich,)).fetchone()
            basis = sha256(canonical_json({k: _iso(v) for k, v in x.items() if k != "row"}).encode())
            self.conn.execute("""INSERT INTO master.lich_tra_no (phien_ban_id, tien_te, so_khe_uoc, model_version, phap_nhan_id, hop_dong_id, pham_vi, khe_uoc_id, cau_phan,
                                 nghia_vu_key, ky_nguon, period_from, period_to, ngay_den_han, amount_minor, currency_code, currency_scale, amount_kind, precision_status,
                                 source_row_id, basis_revision_sha256, known_at_server, recorded_at, thay_cho_id, dich_phan_bo_id)
                                 VALUES (%s,%s,%s,'M9_TYPED',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s)""",
                              (pb, cur, x["ma_khe_uoc"], pn, hd_id, x["pham_vi"], ku, x["cau_phan"], x["nghia_vu_key"], x["ky"], x["period_from"], x["period_to"],
                               x["ngay_den_han"], x["amount"], cur if x["amount"] is not None else None, scale if x["amount"] is not None else None,
                               x["amount_kind"], x["precision"], rid(x["row"]), basis, s["known_at_server"], truoc and truoc["id"], dich))
        for e in g["events"]:
            payload = sha256(canonical_json({"ngay": _iso(e["ngay"]), "ct": e["so_chung_tu"], "ma": e["ma_khe_uoc"], "parts": {c: list(v) for c, v in e["parts"].items()},
                                             "cur": cur}).encode())
            prev = self.conn.execute("""SELECT id, revision, payload_sha256 FROM kho.su_kien_vay WHERE source_alias_id = %s AND source_event_key = %s
                                        ORDER BY revision DESC LIMIT 1""", (alias_id, e["key"])).fetchone()
            if prev and prev["payload_sha256"] == payload:
                continue  # sự kiện không đổi: giữ bản ghi cũ (bằng chứng), không nhân bản theo phiên bản
            ev = self.conn.execute("""INSERT INTO kho.su_kien_vay (phap_nhan_id, source_alias_id, hop_dong_phien_ban_id, khe_uoc_id, source_event_key, revision, source_row_id,
                                      loai_su_kien, ngay_nguon, so_chung_tu_nguon, payload_sha256, supersedes_id, trang_thai, known_at_server)
                                      VALUES (%s,%s,%s,%s,%s,%s,%s,'PHAT_SINH',%s,%s,%s,%s,%s,%s) RETURNING id""",
                                   (pn, alias_id, pb, ku_id.get(e["ma_khe_uoc"]), e["key"], (prev["revision"] + 1) if prev else 1, rid(e["row"]), e["ngay"],
                                    e["so_chung_tu"], payload, prev and prev["id"], "XUNG_DOT" if e["loi"] else "BANG_CHUNG", s["known_at_server"])).fetchone()["id"]
            for c, (amt, p) in sorted(e["parts"].items()):
                self.conn.execute("""INSERT INTO kho.su_kien_vay_phan (phap_nhan_id, su_kien_id, cau_phan, amount_minor, currency_code, currency_scale, precision_status)
                                     VALUES (%s,%s,%s,%s,%s,%s,%s)""", (pn, ev, c, amt, cur, scale, p))
        chan = list(self.conn.execute("SELECT master.m9_chan(%s, 'CHECK') AS c", (pb,)).fetchone()["c"] or [])
        if moi:
            self._viec(pn, "V4", "master.hop_dong", hd_id, f"Khoản vay mới {ten}", [c for c in chan if c.startswith("MAPPING")])
            self._su_kien(pn, dt, "SUA_DANH_MUC", "master.hop_dong", hd_id, "M9_TAO_HOP_DONG_VAY", sau={"khoa_nguon": ten, "kind": g["kind"]})
        self._viec(pn, "V3", "master.hop_dong_phien_ban", pb, f"Khoản vay {ten} — phiên bản {n}", chan)
        self._su_kien(pn, dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb, "M9_LAP_PHIEN_BAN",
                      sau={"phien_ban": n, "source_revision_sha256": rev_sha, "snapshot_id": str(s["id"]), "chan": chan})
        return {"khoa": ten, "hop_dong_id": str(hd_id), "phien_ban_id": str(pb), "phien_ban": n, "ket_qua": "TAO_MOI" if moi else "PHIEN_BAN_MOI",
                "financing_kind": g["kind"], "chan": chan}

    def xac_nhan_pham_vi(self, dang_nhap, hd_id, lua_chon: str, ly_do: str) -> dict:
        """Bổ sung hồ sơ S05: lịch gốc LOAN và DRAW cùng kỳ — kế toán chọn tầng nghĩa vụ (có lý do, ghi vết); lập lại phiên bản từ CÙNG
        snapshot của bản mới nhất, dòng tầng còn lại giữ làm tham chiếu (tham_so.lich_bo_qua), không xóa nguồn."""
        dt = self.danh_tinh(dang_nhap)
        if lua_chon not in LUA_CHON_PHAM_VI or not ly_do or not str(ly_do).strip():
            raise DataError("PHAM_VI_LUA_CHON", "Chọn DUNG_DRAW hoặc DUNG_LOAN, kèm lý do.")
        with self._tx(dt):
            hd = self._khoa_hd(hd_id)
            quyen.kiem(dt, "M9_STAGE", hd["phap_nhan_id"])
            a = self.conn.execute("SELECT * FROM master.vay_dinh_danh_nguon WHERE hop_dong_id = %s", (hd_id,)).fetchone()
            v = self.conn.execute("""SELECT v.snapshot_id FROM master.vay_phien_ban v JOIN master.hop_dong_phien_ban p ON p.id = v.phien_ban_id
                                     WHERE p.hop_dong_id = %s ORDER BY p.phien_ban DESC LIMIT 1""", (hd_id,)).fetchone()
            qd = {"lua_chon": lua_chon, "y_nghia": LUA_CHON_PHAM_VI[lua_chon], "boi": dt["dang_nhap"], "luc": now_utc(), "ly_do": str(ly_do)[:500]}
            self._su_kien(hd["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong", hd_id, "M9_XAC_NHAN_PHAM_VI_LICH", sau=qd, ly_do=qd["ly_do"])
            khoa = f"{a['source_section']}/{a['source_company_key']}/{a['source_key']}"
            ket = self._lap(dt, str(hd["phap_nhan_id"]), v["snapshot_id"], {khoa: qd}, chi_khoa={khoa})  # chỉ khoản vay được quyết định
        return {"quyet_dinh": qd, **ket}

    # ------------------------------------------------------------------ K5: kiểm / duyệt V3 / V4 / từ chối
    def kiem(self, dang_nhap, pb_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            pb0 = self._pb(pb_id)
            self._khoa_hd(pb0["hop_dong_id"])
            pb = self._pb(pb_id)
            quyen.kiem(dt, "M9_CHECK", pb["phap_nhan_id"])
            if pb["trang_thai"] != "CHO_DUYET":
                raise DataError("PHIEN_BAN_DA_CHOT", "Phiên bản không còn chờ duyệt.")
            chan = list(self.conn.execute("SELECT master.m9_chan(%s, 'CHECK') AS c", (pb_id,)).fetchone()["c"] or [])
            if chan:
                raise DataError("M9_CHUA_DU_DIEU_KIEN", "Chưa thể kiểm xong: " + ", ".join(chan))
            van_tay = self.conn.execute("SELECT master.m9_van_tay(%s) AS v", (pb_id,)).fetchone()["v"]
            self.conn.execute("UPDATE master.hop_dong_phien_ban SET kiem_boi = %s, kiem_luc = now(), kiem_van_tay = %s WHERE id = %s", (dt["dang_nhap"], van_tay, pb_id))
            self.conn.execute("""UPDATE kho.viec_can_duyet SET kiem_boi = %s, kiem_luc = now(), ly_do_cho = '{}' WHERE tham_chieu_id IN (%s, %s)
                                 AND trang_thai = 'CHO_DUYET'""", (dt["dang_nhap"], pb_id, pb["hop_dong_id"]))
            self._su_kien(pb["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb_id, "M9_KIEM", sau={"van_tay": van_tay})
        return {"kiem_boi": dt["dang_nhap"], "van_tay": van_tay}

    def duyet_v4(self, dang_nhap, hd_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            hd = self._khoa_hd(hd_id)
            quyen.kiem(dt, "M9_APPROVE_V4", hd["phap_nhan_id"])
            if not self.conn.execute("""SELECT 1 FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'master.hop_dong' AND tham_chieu_id = %s AND loai = 'V4'
                                        AND trang_thai = 'CHO_DUYET'""", (hd_id,)).fetchone():
                raise DataError("KHONG_CO_VIEC_V4", "Không có việc V4 đang chờ của khoản vay này.")
            if hd["doi_tac_id"] is None:
                raise DataError("M9_CHUA_DU_DIEU_KIEN", "Khoản vay mới chưa map ngân hàng cho vay (ObjectID của pháp nhân).")
            self._dong_viec("master.hop_dong", hd_id, "DA_DUYET", dt, loai="V4")
            self._su_kien(hd["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong", hd_id, "M9_DUYET_V4")
        return {"v4": "DA_DUYET"}

    def duyet(self, dang_nhap, pb_id) -> dict:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            pb0 = self._pb(pb_id)
            hd = self._khoa_hd(pb0["hop_dong_id"])  # serialize với nối tiền cùng HĐ; đọc lại đồ thị SAU khi khóa
            pb = self._pb(pb_id)
            pn = pb["phap_nhan_id"]
            quyen.kiem(dt, "M9_APPROVE", pn)
            if pb["trang_thai"] != "CHO_DUYET":
                raise DataError("PHIEN_BAN_DA_CHOT", "Phiên bản không còn chờ duyệt.")
            if pb["kiem_luc"] is None:
                raise DataError("CHUA_KIEM_TRUOC", "Kế toán chưa kiểm (hoặc lần kiểm hết hiệu lực).")
            if self.conn.execute("""SELECT 1 FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'master.hop_dong' AND tham_chieu_id = %s AND loai = 'V4'
                                    AND trang_thai = 'CHO_DUYET'""", (hd["id"],)).fetchone():
                if not quyen.duoc(dt, "M9_APPROVE_V4", pn):
                    raise DataError("KHONG_CO_QUYEN_LOAI_VIEC", "Khoản vay mới còn việc V4 — cần người có quyền V4 duyệt trước hoặc cùng lúc.")
                self._dong_viec("master.hop_dong", hd["id"], "DA_DUYET", dt, loai="V4")
                self._su_kien(pn, dt, "QUYET_DINH", "master.hop_dong", hd["id"], "M9_DUYET_V4")
            chan = list(self.conn.execute("SELECT master.m9_chan(%s, 'APPROVE') AS c", (pb_id,)).fetchone()["c"] or [])
            if chan:
                raise DataError("M9_CHUA_DU_DIEU_KIEN", "Chưa thể duyệt: " + ", ".join(chan))
            self.conn.execute("""UPDATE master.hop_dong_phien_ban SET trang_thai = 'DA_DUYET', nguoi_duyet = %s, duyet_luc = now(), valid_from = now() WHERE id = %s""",
                              (dt["dang_nhap"], pb_id))
            if pb["thay_cho_id"]:
                self.conn.execute("UPDATE master.hop_dong_phien_ban SET valid_to = now() WHERE id = %s AND trang_thai = 'DA_DUYET' AND valid_to IS NULL",
                                  (pb["thay_cho_id"],))
            self.conn.execute("UPDATE master.hop_dong SET phien_ban_hien_hanh = %s, trang_thai = 'HIEU_LUC' WHERE id = %s", (pb_id, hd["id"]))
            ho_so = self._ho_so_vay(pn, hd, pb)
            self._dong_viec("master.hop_dong_phien_ban", pb_id, "DA_DUYET", dt, loai="V3")
            self._su_kien(pn, dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb_id, "M9_DUYET_V3", sau={"ho_so_vay": ho_so, "thay_cho": _s(pb["thay_cho_id"])})
        return {"trang_thai": "DA_DUYET", "ho_so_vay_id": ho_so}

    def _ho_so_vay(self, pn, hd, pb):
        """Chứng từ bằng chứng HO_SO_VAY của HĐ (M9, một lần): neo phía B của liên kết tiền vay. Ngày nghiệp vụ = ngày nguồn sớm nhất
        (giải ngân/nhận nợ/mở LC) — không có ngày nguồn thì không tạo (nối tiền giữ chờ HO_SO_VAY_CHUA_CO), không lấy ngày hôm nay."""
        old = self.conn.execute("SELECT id FROM kho.chung_tu WHERE phap_nhan_id = %s AND loai = 'HO_SO_VAY' AND khoa_nguon = %s", (pn, f"VAY9:{hd['id']}")).fetchone()
        if old:
            return str(old["id"])
        v = self.conn.execute("""SELECT v.*, (SELECT min(r.ngay_giai_ngan_nguon) FROM master.khe_uoc_vay_phien_ban r WHERE r.hop_dong_phien_ban_id = v.phien_ban_id) AS gn
                                 FROM master.vay_phien_ban v WHERE v.phien_ban_id = %s""", (pb["id"],)).fetchone()
        ngay = v["gn"] or v["ngay_nhan_no"] or v["ngay_mo_lc"]
        if ngay is None:
            return None
        return str(self.conn.execute("""INSERT INTO kho.chung_tu (phap_nhan_id, loai, khoa_nguon, ngay_nghiep_vu, tien_te, mo_ta, du_lieu, hash, tep_goc_id, trang_thai)
                                        VALUES (%s,'HO_SO_VAY',%s,%s,%s,%s,%s,%s,%s,'DA_DUYET') RETURNING id""",
                                     (pn, f"VAY9:{hd['id']}", ngay, v["currency_code"], f"Hồ sơ khoản vay {hd['so_hop_dong']} (bằng chứng cho liên kết tiền vay)",
                                      _j({"hop_dong_id": str(hd["id"]), "ma_noi_bo": hd["ma_noi_bo"], "nguon_ngay": "GIAI_NGAN/NHAN_NO/MO_LC sớm nhất"}),
                                      sha256(f"VAY9:{hd['id']}".encode()), pb["tep_goc_id"])).fetchone()["id"])

    def tu_choi(self, dang_nhap, pb_id, ly_do: str) -> dict:
        dt = self.danh_tinh(dang_nhap)
        if not ly_do or not str(ly_do).strip():
            raise DataError("CAN_LY_DO", "Từ chối cần lý do.")
        with self._tx(dt):
            pb0 = self._pb(pb_id)
            self._khoa_hd(pb0["hop_dong_id"])
            pb = self._pb(pb_id)
            quyen.kiem(dt, "M9_APPROVE", pb["phap_nhan_id"])
            if pb["trang_thai"] != "CHO_DUYET":
                raise DataError("PHIEN_BAN_DA_CHOT", "Phiên bản không còn chờ duyệt.")
            self.conn.execute("UPDATE master.hop_dong_phien_ban SET trang_thai = 'TU_CHOI', nguoi_duyet = %s, duyet_luc = now(), ly_do = %s WHERE id = %s",
                              (dt["dang_nhap"], str(ly_do)[:500], pb_id))
            self._dong_viec("master.hop_dong_phien_ban", pb_id, "BO_QUA", dt)
            self._su_kien(pb["phap_nhan_id"], dt, "QUYET_DINH", "master.hop_dong_phien_ban", pb_id, "M9_TU_CHOI", ly_do=str(ly_do)[:500])
        return {"trang_thai": "TU_CHOI"}

    # ------------------------------------------------------------------ L8: nối tiền BANK M1 ↔ đích logic (preview → xác nhận → gỡ)
    def _chuan_hoa_phan_bo(self, phan_bo) -> list[tuple[str, int]]:
        if not isinstance(phan_bo, list) or not phan_bo or len(phan_bo) > 50:
            raise DataError("PHAN_BO", "Cần danh sách phân bổ (1–50 dòng: đích, số tiền).")
        out = []
        for p in phan_bo:
            if not isinstance(p, dict) or set(p) != {"dich", "so_tien"}:
                raise DataError("PHAN_BO", "Mỗi dòng phân bổ chỉ gồm đích và số tiền.")
            out.append((str(p["dich"]), _so_nguyen_duong(p["so_tien"])))
        if len({d for d, _ in out}) != len(out):
            raise DataError("PHAN_BO_TRUNG_DICH", "Một đích chỉ xuất hiện một lần trong một lần nối.")
        return sorted(out)

    def _xem_truoc(self, dt, bank_id, items) -> tuple[dict, str, dict]:
        bank = self.conn.execute("""SELECT id, phap_nhan_id, chieu, tien_te, so_tien_minor, ngay_nghiep_vu, du_lieu->>'reference' AS ref FROM kho.chung_tu
                                    WHERE id = %s AND loai = 'SAO_KE'""", (bank_id,)).fetchone()
        if not bank:
            raise DataError("TIEN_KHONG_THAY", "Không thấy khoản tiền BANK (hoặc ngoài quyền M1).")
        dichs = {}
        for d, _ in items:
            x = self.conn.execute("SELECT * FROM kho.dich_phan_bo_tien WHERE id = %s", (d,)).fetchone()
            if not x:
                raise DataError("DICH_KHONG_THAY", "Không thấy đích phân bổ (hoặc ngoài quyền M9).")
            dichs[d] = x
        hds = {str(x["hop_dong_id"]) for x in dichs.values()}
        if len(hds) != 1:
            raise DataError("PHAN_BO_NHIEU_HOP_DONG", "Một lần nối chỉ cho đích của một khoản vay (parent theo HĐ).")
        pn = str(bank["phap_nhan_id"])
        if any(str(x["phap_nhan_id"]) != pn for x in dichs.values()):
            raise DataError("LIEN_KET_KHAC_PHAP_NHAN", "Tiền và đích khác pháp nhân.")
        quyen.kiem(dt, "M9_MATCH", pn)
        quyen.kiem(dt, "M9_MATCH_M1", pn)
        hd = hds.pop()
        b = lkc.tien_con_lai(self.conn, bank_id)
        if b is None:
            raise DataError("TIEN_KHONG_THAY", "Không đọc được ngân sách khoản tiền (cần M1 trên pháp nhân).")
        chan = [b["blocked_reason"]] if b["blocked_reason"] else []
        tong = sum(so for _, so in items)
        if b["con_lai_minor"] is not None and tong > b["con_lai_minor"]:
            chan.append("VUOT_TIEN_KHA_DUNG")
        dong = []
        for d, so in items:
            x, c = dichs[d], lkc.dich_con_lai(self.conn, d, self.hom_nay())
            ly = c["blocked_reason"] if c else "DICH_KHONG_THAY"
            if not ly and so > c["con_lai_minor"]:
                ly = "VUOT_NGHIA_VU"
            if not ly and (c["currency_code"], c["currency_scale"]) != (b["currency_code"], b["currency_scale"]):
                ly = "KHAC_TIEN_TE"
            if not ly and (x["cau_phan"] == "GIAI_NGAN") != (bank["chieu"] == "THU"):
                ly = "SAI_CHIEU_TIEN"
            if ly:
                chan.append(f"{ly}:{x['logical_key']}")
            dong.append({"dich": d, "logical_key": x["logical_key"], "target_kind": x["target_kind"], "cau_phan": x["cau_phan"], "so_tien": str(so),
                         "suc_chua": _s(c and c["suc_chua_minor"]), "da_phan_bo": _s(c and c["da_phan_bo_minor"]), "con_lai": _s(c and c["con_lai_minor"]),
                         "revision_id": _s(c and c["revision_id"]), "basis": c and c["basis"], "currency": c and c["currency_code"]})
        ho_so = self.conn.execute("SELECT id FROM kho.chung_tu WHERE phap_nhan_id = %s AND loai = 'HO_SO_VAY' AND du_lieu->>'hop_dong_id' = %s", (pn, hd)).fetchone()
        if not ho_so:
            chan.append("HO_SO_VAY_CHUA_CO")
        preview = {"bank": {"id": str(bank_id), "ngay": bank["ngay_nghiep_vu"].isoformat(), "tham_chieu": bank["ref"], "chieu": bank["chieu"],
                            "so_tien": _s(b["so_tien_minor"]), "da_phan_bo": _s(b["da_phan_bo_minor"]), "con_lai": _s(b["con_lai_minor"]),
                            "currency": b["currency_code"], "scale": b["currency_scale"], "version_digest": b["version_digest"]},
                   "hop_dong_id": hd, "phan_bo": dong, "tong": str(tong), "chan": sorted(set(chan))}
        return preview, sha256(canonical_json(preview).encode()), {"pn": pn, "hd": hd, "bank": bank, "dichs": dichs, "ho_so": ho_so and ho_so["id"]}

    def xem_truoc_noi(self, dang_nhap, bank_id, phan_bo) -> dict:
        dt = self.danh_tinh(dang_nhap)
        items = self._chuan_hoa_phan_bo(phan_bo)
        with self._tx(dt):
            preview, token, _ = self._xem_truoc(dt, bank_id, items)
        return {**preview, "xem_truoc_token": token}

    def xac_nhan_noi(self, dang_nhap, bank_id, phan_bo, client_key: str, xem_truoc_token: str) -> dict:
        dt = self.danh_tinh(dang_nhap)
        items = self._chuan_hoa_phan_bo(phan_bo)
        req = lkc.bam_yeu_cau({"bank": str(bank_id), "phan_bo": [[d, str(so)] for d, so in items]})
        with self._tx(dt):
            # quyền trước mọi nhánh (kể cả trả biên nhận cũ); resolve HĐ/BANK rồi khóa theo thứ tự chung, rồi tính lại preview
            preview, token, ctx = self._xem_truoc(dt, bank_id, items)
            old = lkc.tim_bien_nhan(self.conn, ctx["pn"], MODULE, "NOI_TIEN_VAY", client_key, req)
            if old:
                return old
            lkc.khoa(self.conn, [ctx["hd"]], [bank_id])
            preview, token, ctx = self._xem_truoc(dt, bank_id, items)
            if token != xem_truoc_token:
                raise DataError("XEM_TRUOC_HET_HIEU_LUC", "Dữ liệu tiền/nghĩa vụ đã đổi sau khi xem trước — xem trước lại rồi xác nhận.")
            if preview["chan"]:
                raise DataError("NOI_TIEN_BI_CHAN", "Không nối được: " + ", ".join(preview["chan"]))
            lk_id = str(uuid.uuid4())
            ket_qua = {"lien_ket_id": lk_id, "hop_dong_id": ctx["hd"], "bank": str(bank_id), "tong": preview["tong"],
                       "phan_bo": [{"dich": x["dich"], "so_tien": x["so_tien"], "revision_id": x["revision_id"]} for x in preview["phan_bo"]], "trang_thai": "DA_KHOP"}
            bn = lkc.ghi_bien_nhan(self.conn, ctx["pn"], MODULE, "NOI_TIEN_VAY", client_key, req, ket_qua, dt["dang_nhap"])
            self.conn.execute("""INSERT INTO kho.lien_ket_chung_tu (id, phap_nhan_id, chung_tu_a_id, chung_tu_b_id, loai, so_tien_khop_minor, tien_te, trang_thai,
                                 nguon_suy_luan, nguoi_duyet, duyet_luc, hop_dong_id, tao_boi, bien_nhan_id, can_cu)
                                 VALUES (%s,%s,%s,%s,'VAY_TIEN',%s,%s,'DA_KHOP','NGUOI',%s,now(),%s,%s,%s,%s)""",
                              (lk_id, ctx["pn"], bank_id, ctx["ho_so"], int(preview["tong"]), ctx["bank"]["tien_te"], dt["dang_nhap"], ctx["hd"], dt["dang_nhap"], bn,
                               _j({"xem_truoc_token": token, "bank_version_digest": preview["bank"]["version_digest"]})))
            for x in preview["phan_bo"]:
                rev_col = "khe_uoc_phien_ban_id" if x["target_kind"] == "GIAI_NGAN" else "lich_tra_no_id"
                self.conn.execute(f"""INSERT INTO kho.lien_ket_phan_bo (phap_nhan_id, lien_ket_id, cau_phan, logical_target_id, {rev_col}, amount_minor, currency_code,
                                      currency_scale, basis_revision_sha256, bien_nhan_id, tao_boi) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                  (ctx["pn"], lk_id, x["cau_phan"], x["dich"], x["revision_id"], int(x["so_tien"]), x["currency"], preview["bank"]["scale"],
                                   x["basis"], bn, dt["dang_nhap"]))
            self._su_kien(ctx["pn"], dt, "QUYET_DINH", "kho.lien_ket_chung_tu", lk_id, "M9_NOI_TIEN", sau=ket_qua)
        return {**ket_qua, "bien_nhan_id": bn, "lap_lai": False}

    def go_noi(self, dang_nhap, lien_ket_id, ly_do: str, client_key: str) -> dict:
        """Gỡ cả parent (mọi child HUY có vết) — không gỡ một phần child; lịch sử giữ nguyên."""
        dt = self.danh_tinh(dang_nhap)
        if not ly_do or not str(ly_do).strip():
            raise DataError("CAN_LY_DO", "Gỡ liên kết cần lý do.")
        req = lkc.bam_yeu_cau({"lien_ket": str(lien_ket_id)})
        with self._tx(dt):
            k = self.conn.execute("SELECT * FROM kho.lien_ket_chung_tu WHERE id = %s AND loai = 'VAY_TIEN'", (lien_ket_id,)).fetchone()
            if not k:
                raise DataError("LIEN_KET", "Không thấy liên kết tiền vay (hoặc ngoài quyền).")
            quyen.kiem(dt, "M9_MATCH", k["phap_nhan_id"])
            quyen.kiem(dt, "M9_MATCH_M1", k["phap_nhan_id"])
            old = lkc.tim_bien_nhan(self.conn, k["phap_nhan_id"], MODULE, "GO_NOI_TIEN_VAY", client_key, req)
            if old:
                return old
            lkc.khoa(self.conn, [k["hop_dong_id"]], [k["chung_tu_a_id"]])
            k = self.conn.execute("SELECT * FROM kho.lien_ket_chung_tu WHERE id = %s", (lien_ket_id,)).fetchone()
            if k["trang_thai"] == "HUY":
                raise DataError("LIEN_KET_DA_HUY", "Liên kết đã gỡ trước đó.")
            n = self.conn.execute("""UPDATE kho.lien_ket_phan_bo SET trang_thai = 'HUY', huy_boi = %s, huy_luc = now(), ly_do_huy = %s
                                     WHERE lien_ket_id = %s AND trang_thai = 'HIEU_LUC'""", (dt["dang_nhap"], str(ly_do)[:500], lien_ket_id)).rowcount
            self.conn.execute("UPDATE kho.lien_ket_chung_tu SET trang_thai = 'HUY', huy_luc = now(), huy_boi = %s, ly_do_huy = %s WHERE id = %s",
                              (dt["dang_nhap"], str(ly_do)[:500], lien_ket_id))
            ket_qua = {"lien_ket_id": str(lien_ket_id), "so_child_huy": n, "trang_thai": "HUY"}
            bn = lkc.ghi_bien_nhan(self.conn, k["phap_nhan_id"], MODULE, "GO_NOI_TIEN_VAY", client_key, req, ket_qua, dt["dang_nhap"])
            self._su_kien(k["phap_nhan_id"], dt, "QUYET_DINH", "kho.lien_ket_chung_tu", lien_ket_id, "M9_GO_NOI_TIEN", ly_do=str(ly_do)[:500], sau=ket_qua)
        return {**ket_qua, "bien_nhan_id": bn, "lap_lai": False}

    def goi_y_noi(self, dang_nhap, bank_id) -> dict:
        """Gợi ý (KHÔNG ghi): tiền đi ↔ PhatSinh cùng số chứng từ → GOC/LAI/PHI của đúng khế ước/kỳ đến hạn; tiền về ↔ khế ước cùng ngày/số.
        Người dùng vẫn phải xem trước + xác nhận; không có policy tự phân bổ."""
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            bank = self.conn.execute("""SELECT id, phap_nhan_id, chieu, so_tien_minor, ngay_nghiep_vu, du_lieu->>'reference' AS ref FROM kho.chung_tu
                                        WHERE id = %s AND loai = 'SAO_KE'""", (bank_id,)).fetchone()
            if not bank:
                raise DataError("TIEN_KHONG_THAY", "Không thấy khoản tiền BANK (hoặc ngoài quyền M1).")
            quyen.kiem(dt, "M9_MATCH", bank["phap_nhan_id"])
            today, out = self.hom_nay(), []
            if bank["chieu"] == "CHI" and bank["ref"]:
                for e in self.conn.execute("""SELECT DISTINCT ON (e.source_alias_id, e.source_event_key) e.*, a.hop_dong_id FROM kho.su_kien_vay e
                                              JOIN master.vay_dinh_danh_nguon a ON a.id = e.source_alias_id
                                              WHERE e.phap_nhan_id = %s AND e.so_chung_tu_nguon = %s ORDER BY e.source_alias_id, e.source_event_key, e.revision DESC""",
                                           (bank["phap_nhan_id"], bank["ref"])).fetchall():
                    pb = self.conn.execute("SELECT master.m9_phien_ban_hieu_luc(%s, %s) AS v", (e["hop_dong_id"], today)).fetchone()["v"]
                    phan = []
                    for p in self.conn.execute("SELECT * FROM kho.su_kien_vay_phan WHERE su_kien_id = %s AND amount_minor > 0 ORDER BY cau_phan", (e["id"],)):
                        t = self.conn.execute("""SELECT dich_phan_bo_id FROM master.lich_tra_no WHERE phien_ban_id = %s AND cau_phan = %s
                                                 AND khe_uoc_id IS NOT DISTINCT FROM %s AND ngay_den_han = %s""",
                                              (pb, p["cau_phan"], e["khe_uoc_id"], e["ngay_nguon"])).fetchall()
                        phan.append({"cau_phan": p["cau_phan"], "so_tien": str(p["amount_minor"]), "dich": str(t[0]["dich_phan_bo_id"]) if len(t) == 1 else None,
                                     "ly_do": None if len(t) == 1 else ("KHONG_THAY_NGHIA_VU" if not t else "NHIEU_NGHIA_VU")})
                    tong = sum(int(x["so_tien"]) for x in phan)
                    out.append({"hop_dong_id": str(e["hop_dong_id"]), "can_cu": f"PhatSinh {e['source_event_key']} r{e['revision']} số CT {e['so_chung_tu_nguon']}",
                                "phan_bo": phan, "tong": str(tong), "khop_so_tien": tong == bank["so_tien_minor"], "du_dich": all(x["dich"] for x in phan)})
            elif bank["chieu"] == "THU":
                for r in self.conn.execute("""SELECT r.dich_phan_bo_id, r.so_tien_minor, k.ma_khe_uoc_nguon, k.hop_dong_id FROM master.khe_uoc_vay_phien_ban r
                                              JOIN master.khe_uoc_vay k ON k.id = r.khe_uoc_id
                                              WHERE r.phap_nhan_id = %s AND r.ngay_giai_ngan_nguon = %s AND r.so_tien_minor = %s
                                                AND r.hop_dong_phien_ban_id = master.m9_phien_ban_hieu_luc(k.hop_dong_id, %s)""",
                                           (bank["phap_nhan_id"], bank["ngay_nghiep_vu"], bank["so_tien_minor"], today)).fetchall():
                    out.append({"hop_dong_id": str(r["hop_dong_id"]), "can_cu": f"Khế ước {r['ma_khe_uoc_nguon']} giải ngân cùng ngày/số tiền",
                                "phan_bo": [{"cau_phan": "GIAI_NGAN", "so_tien": str(r["so_tien_minor"]), "dich": str(r["dich_phan_bo_id"]), "ly_do": None}],
                                "tong": str(r["so_tien_minor"]), "khop_so_tien": True, "du_dich": True})
        return {"bank": str(bank_id), "goi_y": out, "ghi_chu": "Gợi ý theo bằng chứng nguồn — chưa ghi gì; xem trước rồi xác nhận."}

    # ------------------------------------------------------------------ file soát M9 (export chung + sổ đăng ký lô)
    def xuat_file_soat(self, dang_nhap, hd_id) -> dict:
        from ..xuat import excel
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            hd = self.conn.execute("""SELECT h.*, p.ma AS pn_ma FROM master.hop_dong h JOIN master.phap_nhan p ON p.id = h.phap_nhan_id
                                      WHERE h.id = %s AND h.loai = 'VAY'""", (hd_id,)).fetchone()
            if not hd:
                raise DataError("HOP_DONG_VAY", "Không thấy hợp đồng vay (hoặc ngoài quyền).")
            quyen.kiem(dt, "M9_EXPORT", hd["phap_nhan_id"])
            xem_tien = quyen.duoc(dt, "XEM_TIEN", hd["phap_nhan_id"])
            ct = self._chi_tiet_hd(hd, self.hom_nay(), xem_tien)
            t = lambda v: None if v is None else str(v)
            ban = [[hd["pn_ma"], hd["ma_noi_bo"], hd["so_hop_dong"], v["phien_ban"], v["trang_thai"], "CÓ" if v["hieu_luc_hom_nay"] else "", v["vay"]["financing_kind"],
                    v["vay"]["currency_code"], v["vay"]["han_muc"], v["vay"]["du_no_nguon"], v["vay"]["ngay_du_no_nguon"], v["vay"]["so_vay_vnd"],
                    v["vay"]["so_nguyen_te"], v["vay"]["nguyen_te_code"], v["vay"]["source_fx_rate"], v["vay"]["precision_status"], ",".join(v["vay"]["blockers"]),
                    v["kiem_boi"], v["nguoi_duyet"], v["nguon"]["snapshot_id"], v["nguon"]["raw_sha256"], v["nguon"]["profile"], v["vay"]["source_revision_sha256"]]
                   for v in ct["phien_ban"]]
            draws = [[v["phien_ban"], d["ma"], d["ngay"], d["so_tien"], d["currency"], d["precision"], d["logical_key"], d["con_lai"]]
                     for v in ct["phien_ban"] for d in v["khe_uoc"]]
            rates = [[v["phien_ban"], r["ma"], r["ap_dung_tu"], r["pct_nam"], r["precision"]] for v in ct["phien_ban"] for r in v["lai_suat"]]
            lich = [[v["phien_ban"], x["nghia_vu_key"], x["pham_vi"], x["khe_uoc"], x["cau_phan"], x["ky"], x["tu"], x["den"], x["han"], x["so_tien"], x["currency"],
                     x["amount_kind"], x["precision"], x["logical_key"], x["da_phan_bo"], x["con_lai"]] for v in ct["phien_ban"] for x in v["lich"]]
            ev = [[v["phien_ban"], e["key"], e["revision"], e["ngay"], e["so_chung_tu"], e["khe_uoc"], e["parts"].get("GOC"), e["parts"].get("LAI"), e["parts"].get("PHI"),
                   e["trang_thai"]] for v in ct["phien_ban"] for e in v["phat_sinh"]]
            links = [[k["id"], k["bank"], k["tong"], k["trang_thai"], c["cau_phan"], c["logical_key"], c["so_tien"], c["trang_thai"], c["ly_do_huy"]]
                     for k in ct["lien_ket"] for c in k["child"]]
            wb = excel.workbook()
            excel.table(wb, "HOP_DONG_VAY", ["phap_nhan", "ma_noi_bo", "so_hop_dong", "phien_ban", "trang_thai", "hieu_luc_hom_nay", "loai_tai_tro", "tien_te",
                                             "han_muc", "du_no_nguon", "ngay_du_no_nguon", "so_vay_vnd", "so_nguyen_te", "nguyen_te", "ty_gia_nguon", "precision",
                                             "dieu_kien_chan", "ke_toan_kiem", "cfo_duyet", "snapshot", "raw_sha256", "profile", "source_revision"], ban)
            excel.table(wb, "KHE_UOC", ["phien_ban", "ma_khe_uoc", "ngay_giai_ngan", "so_tien", "tien_te", "precision", "dich_logic", "con_lai_noi_tien"], draws)
            excel.table(wb, "LAI_SUAT", ["phien_ban", "ma_khe_uoc", "ap_dung_tu", "lai_suat_pct_nam", "precision"], rates)
            excel.table(wb, "LICH_TRA_NO", ["phien_ban", "khoa_nghia_vu", "pham_vi", "khe_uoc", "cau_phan", "ky", "tu_ngay", "den_ngay", "den_han", "so_tien", "tien_te",
                                            "loai_so", "precision", "dich_logic", "da_phan_bo", "con_lai"], lich)
            excel.table(wb, "PHAT_SINH", ["phien_ban", "khoa", "revision", "ngay", "so_chung_tu", "khe_uoc", "goc", "lai", "phi", "trang_thai"], ev)
            excel.table(wb, "LIEN_KET_TIEN", ["lien_ket", "bank", "tong", "trang_thai", "cau_phan", "dich_logic", "so_tien", "trang_thai_child", "ly_do_huy"], links)
            excel.table(wb, "CANH_BAO", ["noi_dung"], [["DEMO — dữ liệu mô phỏng theo fixture contract M9"],
                                                       ["Hồ sơ khoản vay/lịch trả nợ/liên kết tiền — KHÔNG phải phiếu chi/thu, KHÔNG phải file nhập Junsky"],
                                                       ["Không tính lãi từ lãi suất; lãi/phí chỉ từ bảng lãi đã xác nhận (DEMO)"],
                                                       ["Mọi số tiền/tỷ lệ ghi dạng chữ để giữ đủ chữ số; ô chữ không thành công thức"]])
            raw = excel.to_bytes(wb)
            digest = sha256(raw)
            ma_lo = f"M9-{str(hd_id)[:8]}-{digest[:12]}"
            write_immutable(self.root / "m9-xuat" / f"{digest}.xlsx", raw)
            ten = f"FILE-SOAT-M9-{hd['so_hop_dong']}-{digest[:8]}.xlsx".replace("/", "_").replace("\\", "_").replace(" ", "_")
            lo = self.conn.execute("""INSERT INTO kho.lo_xuat (phap_nhan_id, ky, ma_lo, loai, duong_dan, hash, so_dong, nguoi, xuat_luc, trang_thai, du_lieu)
                                      VALUES (%s,%s,%s,'FILE_SOAT',%s,%s,%s,%s,now(),'DA_XUAT',%s) RETURNING id""",
                                   (hd["phap_nhan_id"], self.hom_nay().strftime("%Y-%m"), ma_lo, f"m9-xuat/{digest}.xlsx", digest, len(lich), dt["dang_nhap"],
                                    _j({"module": MODULE, "loai": "HO_SO_VAY", "hop_dong_id": str(hd_id), "ten": ten}))).fetchone()
            self._su_kien(hd["phap_nhan_id"], dt, "LO", "kho.lo_xuat", lo["id"], "M9_XUAT_FILE_SOAT", sau={"sha256": digest, "so_lich": len(lich)})
        return {"id": str(lo["id"]), "ten": ten, "sha256": digest}

    def tep_file_soat(self, dang_nhap, lo_id) -> tuple[str, bytes]:
        dt = self.danh_tinh(dang_nhap)
        with self._tx(dt):
            lo = self.conn.execute("SELECT * FROM kho.lo_xuat WHERE id = %s AND du_lieu->>'module' = %s", (lo_id, MODULE)).fetchone()
            if not lo:
                raise DataError("FILE_SOAT", "Không thấy file soát M9 (hoặc ngoài quyền).")
            quyen.kiem(dt, "M9_EXPORT", lo["phap_nhan_id"])
        path = (self.root / lo["duong_dan"]).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise DataError("FILE_SOAT", "Đường dẫn file soát không hợp lệ.")
        raw = path.read_bytes()
        if sha256(raw) != lo["hash"]:
            raise DataError("ARTIFACT_CHANGED", "File soát đã bị thay đổi.")
        return lo["du_lieu"]["ten"], raw

    # ------------------------------------------------------------------ tra cứu (M9_READ + RLS), as-of/known-cutoff
    def _chi_tiet_hd(self, h, ngay, xem_tien, biet_den=None) -> dict:
        hieu_luc = self.conn.execute("SELECT master.m9_phien_ban_hieu_luc(%s, %s) AS v", (h["id"], ngay)).fetchone()["v"]
        versions = []
        for p in self.conn.execute("""SELECT p.*, v.* FROM master.hop_dong_phien_ban p JOIN master.vay_phien_ban v ON v.phien_ban_id = p.id
                                      WHERE p.hop_dong_id = %s AND (%s::timestamptz IS NULL OR p.tao_luc <= %s::timestamptz) ORDER BY p.phien_ban""",
                                   (h["id"], biet_den, biet_den)).fetchall():
            hl = p["phien_ban_id"] == hieu_luc
            con = (lambda d: lkc.dich_con_lai(self.conn, d, ngay)) if hl else (lambda d: None)
            draws = []
            for d in self.conn.execute("""SELECT r.*, k.ma_khe_uoc_nguon, x.logical_key FROM master.khe_uoc_vay_phien_ban r JOIN master.khe_uoc_vay k ON k.id = r.khe_uoc_id
                                          JOIN kho.dich_phan_bo_tien x ON x.id = r.dich_phan_bo_id WHERE r.hop_dong_phien_ban_id = %s ORDER BY k.ma_khe_uoc_nguon""",
                                       (p["phien_ban_id"],)).fetchall():
                c = con(d["dich_phan_bo_id"])
                draws.append({"ma": d["ma_khe_uoc_nguon"], "ngay": _iso(d["ngay_giai_ngan_nguon"]), "so_tien": _s(d["so_tien_minor"]), "currency": d["currency_code"],
                              "precision": d["precision_status"], "dich": str(d["dich_phan_bo_id"]), "logical_key": d["logical_key"],
                              "da_phan_bo": _s(c and c["da_phan_bo_minor"]), "con_lai": _s(c and c["con_lai_minor"]), "chan_noi": c and c["blocked_reason"]})
            rates = [{"ma": r["ma_khe_uoc_nguon"], "ap_dung_tu": _iso(r["ap_dung_tu"]), "pct_nam": str(r["lai_suat_pct_nam"]), "precision": r["precision_status"]}
                     for r in self.conn.execute("""SELECT l.*, k.ma_khe_uoc_nguon FROM master.lai_suat_vay l JOIN master.khe_uoc_vay_phien_ban r ON r.id = l.khe_uoc_phien_ban_id
                                                   JOIN master.khe_uoc_vay k ON k.id = r.khe_uoc_id WHERE l.hop_dong_phien_ban_id = %s ORDER BY k.ma_khe_uoc_nguon, l.ap_dung_tu""",
                                                (p["phien_ban_id"],))]
            lich = []
            for x in self.conn.execute("""SELECT t.*, d.logical_key FROM master.lich_tra_no t JOIN kho.dich_phan_bo_tien d ON d.id = t.dich_phan_bo_id
                                          WHERE t.phien_ban_id = %s ORDER BY t.nghia_vu_key""", (p["phien_ban_id"],)).fetchall():
                c = con(x["dich_phan_bo_id"])
                lich.append({"nghia_vu_key": x["nghia_vu_key"], "pham_vi": x["pham_vi"], "khe_uoc": x["so_khe_uoc"], "cau_phan": x["cau_phan"], "ky": x["ky_nguon"],
                             "tu": _iso(x["period_from"]), "den": _iso(x["period_to"]), "han": _iso(x["ngay_den_han"]), "so_tien": _s(x["amount_minor"]),
                             "currency": x["currency_code"], "amount_kind": x["amount_kind"], "precision": x["precision_status"], "dich": str(x["dich_phan_bo_id"]),
                             "logical_key": x["logical_key"], "thay_cho": _s(x["thay_cho_id"]), "da_phan_bo": _s(c and c["da_phan_bo_minor"]),
                             "con_lai": _s(c and c["con_lai_minor"]), "chan_noi": c and c["blocked_reason"]})
            events = []
            for e in self.conn.execute("SELECT * FROM kho.su_kien_vay WHERE hop_dong_phien_ban_id = %s ORDER BY source_event_key, revision", (p["phien_ban_id"],)).fetchall():
                parts = {x["cau_phan"]: _s(x["amount_minor"]) for x in self.conn.execute("SELECT * FROM kho.su_kien_vay_phan WHERE su_kien_id = %s", (e["id"],))}
                events.append({"key": e["source_event_key"], "revision": e["revision"], "ngay": _iso(e["ngay_nguon"]), "so_chung_tu": e["so_chung_tu_nguon"],
                               "khe_uoc": _s(e["khe_uoc_id"]), "parts": parts, "trang_thai": e["trang_thai"]})
            ts = p["tham_so"] or {}
            versions.append({
                "id": str(p["phien_ban_id"]), "phien_ban": p["phien_ban"], "trang_thai": p["trang_thai"], "hieu_luc_hom_nay": hl, "thay_cho": _s(p["thay_cho_id"]),
                "kiem_boi": p["kiem_boi"], "kiem_van_tay": p["kiem_van_tay"], "nguoi_duyet": p["nguoi_duyet"], "duyet_luc": p["duyet_luc"].isoformat() if p["duyet_luc"] else None,
                "ly_do": p["ly_do"], "tao_luc": p["tao_luc"].isoformat() if p.get("tao_luc") else None,
                "chan": list(self.conn.execute("SELECT master.m9_chan(%s, 'CHECK') AS c", (p["phien_ban_id"],)).fetchone()["c"] or []) if p["trang_thai"] == "CHO_DUYET" else [],
                "nguon": {"snapshot_id": ts.get("snapshot_id"), "raw_sha256": ts.get("raw_sha256"), "profile": (ts.get("profile") or {}).get("code"),
                          "bang_lai_snapshot_id": ts.get("bang_lai_snapshot_id"), "quyet_dinh_pham_vi": ts.get("quyet_dinh_pham_vi"), "lich_bo_qua": ts.get("lich_bo_qua")},
                "vay": {"financing_kind": p["financing_kind"], "currency_code": p["currency_code"], "han_muc": _s(p["han_muc_minor"]), "du_no_nguon": _s(p["du_no_nguon_minor"]),
                        "ngay_du_no_nguon": _iso(p["ngay_du_no_nguon"]), "so_hop_dong_nguon": p["so_hop_dong_nguon"], "so_nhan_no": p["so_nhan_no"], "so_lc": p["so_lc"],
                        "ngay_mo_lc": _iso(p["ngay_mo_lc"]), "ngay_nhan_no": _iso(p["ngay_nhan_no"]), "ngay_den_han": _iso(p["ngay_den_han"]),
                        "so_vay_vnd": _s(p["so_vay_vnd_minor"]), "so_da_tra_vnd": _s(p["so_da_tra_vnd_minor"]), "so_nguyen_te": _s(p["so_nguyen_te_minor"]),
                        "nguyen_te_code": p["nguyen_te_code"], "source_fx_rate": _s(p["source_fx_rate"]), "source_status": p["source_status"],
                        "ky_han_nguon": p["ky_han_nguon"], "an_han_nguon": p["an_han_nguon"], "quy_uoc_lai_nguon": p["quy_uoc_lai_nguon"],
                        "precision_status": p["precision_status"], "blockers": list(p["blockers"]), "source_revision_sha256": p["source_revision_sha256"],
                        "mapping_pin": p["mapping_pin"]},
                "khe_uoc": draws, "lai_suat": rates, "lich": lich, "phat_sinh": events})
        links = []
        if xem_tien:
            for k in self.conn.execute("""SELECT k.*, c.du_lieu->>'reference' AS ref, c.ngay_nghiep_vu FROM kho.lien_ket_chung_tu k JOIN kho.chung_tu c ON c.id = k.chung_tu_a_id
                                          WHERE k.hop_dong_id = %s AND k.loai = 'VAY_TIEN' ORDER BY k.tao_luc""", (h["id"],)).fetchall():
                child = [{"cau_phan": c["cau_phan"], "dich": str(c["logical_target_id"]), "logical_key": c["logical_key"], "so_tien": _s(c["amount_minor"]),
                          "revision": _s(c["lich_tra_no_id"] or c["khe_uoc_phien_ban_id"]), "trang_thai": c["trang_thai"], "ly_do_huy": c["ly_do_huy"]}
                         for c in self.conn.execute("""SELECT c.*, d.logical_key FROM kho.lien_ket_phan_bo c JOIN kho.dich_phan_bo_tien d ON d.id = c.logical_target_id
                                                       WHERE c.lien_ket_id = %s ORDER BY d.logical_key""", (k["id"],))]
                links.append({"id": str(k["id"]), "bank": str(k["chung_tu_a_id"]), "bank_ref": k["ref"], "bank_ngay": _iso(k["ngay_nghiep_vu"]),
                              "tong": _s(k["so_tien_khop_minor"]), "trang_thai": k["trang_thai"], "tao_boi": k["tao_boi"], "huy_boi": k["huy_boi"],
                              "ly_do_huy": k["ly_do_huy"], "bien_nhan": _s(k["bien_nhan_id"]), "child": child})
        return {"hieu_luc": _s(hieu_luc), "phien_ban": versions, "lien_ket": links}

    def danh_sach(self, dang_nhap, *, ngay_xem=None, biet_den=None) -> dict:
        dt = self.danh_tinh(dang_nhap)
        pns = quyen.pham_vi(dt, "M9_READ")
        if not pns:
            raise DataError("KHONG_CO_QUYEN_MODULE", "Người dùng không có quyền xem M9 trên pháp nhân nào.")
        pns_tien = [p for p in pns if quyen.duoc(dt, "XEM_TIEN", p)]
        ngay = date.fromisoformat(ngay_xem) if isinstance(ngay_xem, str) and ngay_xem else self.hom_nay()
        with self._tx(dt):
            snaps = [{"id": str(s["id"]), "profile": s["profile_code"], "trang_thai": s["state"], "pham_vi": s["coverage_kind"], "loi": s["loi"],
                      "raw_sha256": s["raw_sha256"], "xuat_tu_nguon": s["exported_at_source"], "biet_luc": s["known_at_server"].isoformat(), "nguoi": s["nguoi"],
                      "so_dong_pn": s["n"]}
                     for s in self.conn.execute("""SELECT s.*, (SELECT count(*) FROM kho.ban_ghi_nguon b WHERE b.snapshot_id = s.id) AS n
                                                   FROM kho.anh_chup_nguon s ORDER BY s.known_at_server DESC""")]
            cho_map = [{"instance": x["source_instance_id"], "cong_ty": x["source_company_key"], "so_dong": x["so_dong"]}
                       for x in self.conn.execute("SELECT * FROM giao_tiep.cong_ty_chua_map()")]
            maps = [{"id": str(m["id"]), "kind": m["kind"], "cong_ty": m["source_company_key"], "nguon": m["source_value"], "phap_nhan": m["pn_ma"],
                     "doi_tac": m["object_id_junsky"], "du_an": m["du_an_ma"], "revision": m["revision"], "trang_thai": m["state"], "duyet_boi": m["duyet_boi"],
                     "tu": m["valid_from"].isoformat(), "den": m["valid_to"] and m["valid_to"].isoformat()}
                    for m in self.conn.execute("""SELECT m.*, p.ma AS pn_ma, d.object_id_junsky, a.ma_junsky AS du_an_ma FROM master.anh_xa_nguon m
                                                  JOIN master.phap_nhan p ON p.id = m.phap_nhan_id
                                                  LEFT JOIN master.doi_tac_ma_junsky d ON d.doi_tac_id = m.doi_tac_id AND d.phap_nhan_id = m.phap_nhan_id AND d.valid_to IS NULL
                                                  LEFT JOIN master.du_an a ON a.id = m.du_an_id ORDER BY m.recorded_at""")]
            ung_vien = [{"kind": u["kind"], "cong_ty": u["cong_ty"], "nguon": u["v"], "phap_nhan": u["pn_ma"]} for u in self.conn.execute(
                """SELECT DISTINCT x.kind, b.source_company_key AS cong_ty, x.v, p.ma AS pn_ma, s.source_instance_id FROM kho.ban_ghi_nguon b
                   JOIN kho.anh_chup_nguon s ON s.id = b.snapshot_id JOIN master.phap_nhan p ON p.id = b.phap_nhan_id
                   CROSS JOIN LATERAL (VALUES ('BANK', b.row_raw->>'nganHang'), ('PROJECT', b.row_raw->>'duAn')) AS x(kind, v)
                   WHERE b.section IN ('DaiHan','VayNganHan') AND coalesce(x.v, '') <> ''
                     AND NOT EXISTS (SELECT 1 FROM master.anh_xa_nguon m WHERE m.source_instance_id = s.source_instance_id AND m.source_company_key = b.source_company_key
                                     AND m.kind = x.kind AND m.source_value = x.v AND m.state = 'DA_DUYET' AND m.valid_to IS NULL)
                   ORDER BY 1, 2, 3""")]
            loans = []
            for h in self.conn.execute("""SELECT h.*, p.ma AS pn_ma, d.object_id_junsky, a.ma_junsky AS du_an_ma, al.source_section, al.source_company_key, al.source_key
                                          FROM master.hop_dong h JOIN master.phap_nhan p ON p.id = h.phap_nhan_id
                                          JOIN master.vay_dinh_danh_nguon al ON al.hop_dong_id = h.id
                                          LEFT JOIN master.doi_tac_ma_junsky d ON d.doi_tac_id = h.doi_tac_id AND d.phap_nhan_id = h.phap_nhan_id AND d.valid_to IS NULL
                                          LEFT JOIN master.du_an a ON a.id = h.du_an_id WHERE h.loai = 'VAY' AND h.phap_nhan_id = ANY(%s::uuid[]) ORDER BY h.tao_luc""",
                                       (pns,)).fetchall():
                v4 = self.conn.execute("""SELECT trang_thai FROM kho.viec_can_duyet WHERE tham_chieu_bang = 'master.hop_dong' AND tham_chieu_id = %s AND loai = 'V4'
                                          ORDER BY tao_luc DESC LIMIT 1""", (h["id"],)).fetchone()
                loans.append({"id": str(h["id"]), "phap_nhan": h["pn_ma"], "ma_noi_bo": h["ma_noi_bo"], "so_hop_dong": h["so_hop_dong"], "trang_thai": h["trang_thai"],
                              "khoa_nguon": f"{h['source_section']}/{h['source_company_key']}/{h['source_key']}", "ngan_hang": h["object_id_junsky"],
                              "du_an": h["du_an_ma"], "tien_te": h["tien_te"], "hien_hanh": _s(h["phien_ban_hien_hanh"]), "v4": v4 and v4["trang_thai"],
                              **self._chi_tiet_hd(h, ngay, str(h["phap_nhan_id"]) in pns_tien, biet_den)})
            tien = []
            if pns_tien:
                for c in self.conn.execute("""SELECT c.*, p.ma FROM kho.chung_tu c JOIN master.phap_nhan p ON p.id = c.phap_nhan_id
                                              WHERE c.loai = 'SAO_KE' AND c.phap_nhan_id = ANY(%s::uuid[]) ORDER BY c.ngay_nghiep_vu, c.khoa_nguon""", (pns_tien,)).fetchall():
                    b = lkc.tien_con_lai(self.conn, c["id"]) or {}
                    tien.append({"id": str(c["id"]), "phap_nhan": c["ma"], "ngay": c["ngay_nghiep_vu"].isoformat(), "chieu": c["chieu"], "tham_chieu": c["du_lieu"].get("reference"),
                                 "mo_ta": c["mo_ta"], "so_tien": _s(c["so_tien_minor"]), "tien_te": c["tien_te"], "da_phan_bo": _s(b.get("da_phan_bo_minor")),
                                 "con_lai": _s(b.get("con_lai_minor")), "chan": b.get("blocked_reason"), "nguon_m1": "_sqlite_id" in c["du_lieu"]})
            file_soat = [{"id": str(r["id"]), "phap_nhan": r["ma"], "ten": r["du_lieu"]["ten"], "hop_dong_id": r["du_lieu"]["hop_dong_id"], "luc": r["xuat_luc"].isoformat()}
                         for r in self.conn.execute("""SELECT l.*, p.ma FROM kho.lo_xuat l JOIN master.phap_nhan p ON p.id = l.phap_nhan_id
                                                       WHERE l.du_lieu->>'module' = 'M9' AND l.phap_nhan_id = ANY(%s::uuid[]) ORDER BY l.xuat_luc DESC""", (pns,))]
            viec = [self._viec_view(v) | {"tham_chieu": v["tham_chieu_bang"], "id_tham_chieu": str(v["tham_chieu_id"])}
                    for v in self.conn.execute("""SELECT * FROM kho.viec_can_duyet WHERE module = 'M9' AND phap_nhan_id = ANY(%s::uuid[])
                                                  AND trang_thai IN ('CHO_DUYET','DANG_HOI','CHO_BO_SUNG') ORDER BY tao_luc""", (pns,))]
        return {"nguoi": {"dang_nhap": dt["dang_nhap"], "vai_tro": dt["vai_tro"], "phap_nhan": sorted(dt["quyen"][p]["ma"] for p in pns), "xem_tien": bool(pns_tien),
                          "hanh_dong": sorted(a for a in quyen.HANH_DONG if a.startswith("M9_") and quyen.pham_vi(dt, a))},
                "ngay_xem": ngay.isoformat(), "biet_den": biet_den, "snapshot": snaps, "cong_ty_cho_map": cho_map, "anh_xa": maps, "ung_vien_anh_xa": ung_vien,
                "khoan_vay": loans, "tien": tien, "file_soat": file_soat, "viec": viec, "khoang_trong": khoang_trong(),
                "lua_chon_pham_vi": LUA_CHON_PHAM_VI,
                "gioi_han": "DEMO: danh tính mô phỏng theo phiên; nguồn #9 qua fixture contract đã pin (không gọi Google/app nguồn); bảng lãi là xác nhận DEMO."}


def khoang_trong() -> list[dict]:
    """Gap full M9/33 — work gate cụ thể theo nguồn/căn cứ thiếu (không tạo schema/bảng rỗng rồi gọi xong)."""
    return [
        {"ma": "C4D_DAU_TU", "nhanh": "C4d đầu tư/chứng khoán", "trang_thai": "WORK_GATE",
         "thieu": ["register danh mục đầu tư hiện hành có căn cứ", "phân loại công cụ (CK kinh doanh/nắm giữ đến đáo hạn/góp vốn)", "hồ sơ nguồn (sổ CK/xác nhận số dư)",
                   "chính sách định giá/dự phòng đã duyệt"], "khong_lam": "Không tạo schema chứng khoán/định giá khi chưa có nguồn — tìm nguồn ở bước điều phối."},
        {"ma": "GOOGLE_READONLY", "nhanh": "Đọc #9 trực tiếp", "trang_thai": "GATE",
         "thieu": ["deployment readonly đã pin", "credential được cấp"], "khong_lam": "Không gọi load/ensureSheet/exportToExcel/AppsScript mutation; DEMO dùng file đúng contract."},
        {"ma": "BAO_LANH", "nhanh": "Bảo lãnh (GUARANTEE)", "trang_thai": "WORK_GATE", "thieu": ["shape nguồn bảo lãnh", "template phí bảo lãnh/ký quỹ"],
         "khong_lam": "financing_kind GUARANTEE có trong schema nhưng adapter không suy từ dữ liệu khác."},
        {"ma": "LC_THANH_TOAN", "nhanh": "LC thanh toán/ký quỹ", "trang_thai": "WORK_GATE", "thieu": ["lịch ký quỹ/thanh toán LC có căn cứ", "template định khoản LC"],
         "khong_lam": "LC giữ fact nguồn; khi nhận nợ chuyển SHORT_TERM cùng alias (phiên bản mới)."},
        {"ma": "L7_LAI_DU_TRA", "nhanh": "L7 lãi dự trả/accrual", "trang_thai": "HOLD_POLICY",
         "thieu": ["daycount/cutoff đã duyệt", "template ghi nhận lãi"], "khong_lam": "Không tính lãi từ lãi suất/dư nợ; chỉ nhận bảng lãi đã xác nhận (DEMO)."},
        {"ma": "FX_DANH_GIA_LAI", "nhanh": "Tỷ giá/đánh giá lại nguyên tệ", "trang_thai": "HOLD_POLICY", "thieu": ["chính sách tỷ giá"],
         "khong_lam": "Nguyên tệ và VND nguồn giữ riêng; tỷ giá nguồn chỉ là metadata."},
        {"ma": "VON_HOA_LAI", "nhanh": "Vốn hóa lãi vay", "trang_thai": "HOLD_POLICY", "thieu": ["chính sách vốn hóa theo dự án"], "khong_lam": "Không phân bổ lãi vào dự án."},
        {"ma": "PHAN_LOAI_NGAN_DAI", "nhanh": "Phân loại ngắn/dài hạn (đến hạn trả)", "trang_thai": "HOLD_POLICY", "thieu": ["quy tắc kết chuyển + TK"],
         "khong_lam": "Không tự kết chuyển."},
        {"ma": "M10_GHI_NHAN", "nhanh": "M10 ghi nhận/định khoản", "trang_thai": "CONTRACT_ONLY",
         "thieu": ["template/policy M9 đã duyệt"], "khong_lam": "M9 không sinh đề xuất định khoản; khóa ghi nhận dùng (PN, đích logic, loại sự kiện, kỳ) — map tại k2/lien_ket_chung.py."},
        {"ma": "HDM_HAN_MUC_TYPED", "nhanh": "HĐ mua/hạn mức tín dụng", "trang_thai": "RAW_ONLY", "thieu": ["contract typed cho HopDongMua/HanMucTinDung"],
         "khong_lam": "Giữ raw row có PN; chưa typed."},
        {"ma": "CRM_DIRECT_PROOF", "nhanh": "Proof tiền cho link CRM DIRECT", "trang_thai": "GAP_DOCUMENTED",
         "thieu": ["áp proof encoding cho nhánh DIRECT"], "khong_lam": "CRM DIRECT giữ kiểm số cũ, dùng chung ngân sách BANK; child M9 bắt buộc proof."},
    ]
