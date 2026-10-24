"""M4 bridge DEMO — hồ sơ nghiệm thu từ kết quả #5 → xác nhận kế toán → đề xuất noncash → file soát.

Façade nhỏ trên **cùng Store**: dùng lại ``quick_runs``/``quick_items`` (source_kind ``NGHIEM_THU``), ``activity_log`` và
artifact/raw bất biến; không dựng kho, cơ chế duyệt hay tri thức thứ hai, không học STK/từ khóa. QuickPosting (tiền, Thu/Chi)
từ chối các run này (``quick.py``) nên hai luồng không lẫn.

Nguyên tắc bảo toàn nghĩa (docs/GIAO-VIEC-BRIDGE-REVIEW-XAY-DUNG-33.md):
- Số chấp nhận hạch toán, cơ sở VAT, giữ lại đợt, mapping pháp nhân/HĐ chung/ProjectID/ObjectID là **xác nhận kế toán riêng**,
  lưu ở ``decision_json`` + nhật ký; không sửa raw/core nguồn; chưa xác nhận là NULL, không thành 0.
- ``da_nap`` (trạng thái nạp CSDL review) là điều kiện nguồn, không phải duyệt kế toán; hai trạng thái độc lập.
- Mapping theo mã trong danh mục đã nạp (đúng mã, đúng hiệu lực tại ngày nghiệm thu), không ghép theo tên.
- Tài khoản/mẫu bút toán dưới đây là **cấu hình DEMO công khai**, không quyết thay chính sách 241/154/VAT thật.
- Bản thay của cùng sự kiện (instance + mã HĐ + đợt): bản chờ cũ → Bỏ qua có lý do. Điều kiện cấp sự kiện tính **động** trong
  giao dịch ở mỗi lần xác nhận/Đồng ý/xuất: có bản khác đã xuất → mọi bản khác bị chặn (cần quy trình điều chỉnh, chưa có trong
  gói DEMO); có bản khác Đã đồng ý → chặn; có bản mới hơn chưa bị bỏ qua → bản cũ không sống lại. Không sinh công nợ hai lần.
- Số giữ lại đợt và thu hồi tạm ứng phải xác nhận tường minh (0 hợp lệ); NULL không bao giờ thành 0.
- Tiền qua API là chuỗi số nguyên; file soát ghi số ≥ 10^15 dạng chữ để không mất chữ số.
- Server khóa actor ``MO_PHONG_*`` và môi trường fixture; mức 2 Junsky luôn khóa.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..ha_tang.primitives import DataError, canonical_json, instant_utc, money_minor, now_utc, sha256, text_id
from ..ha_tang.runtime import log, transaction, uid
from ..ha_tang.store import write_immutable
from ..nguon.review_xay_dung import KIND, kiem_da_nap
from ..xuat import excel

EXCEL_SO_CHINH_XAC = 10 ** 15  # Excel chỉ giữ 15 chữ số có nghĩa; từ đây ghi tiền dạng chữ để không mất số


def _tien(value):
    """Tiền qua API dạng chuỗi số nguyên (JSON.parse của trình duyệt làm tròn số > 2^53); NULL giữ NULL."""
    return None if value is None else str(value)


def _goc(value):
    return str(value) if type(value) is int else value


def _o_tien_excel(value):
    return value if abs(value) < EXCEL_SO_CHINH_XAC else str(value)

SOURCE_KIND = "NGHIEM_THU"
MODULE = "M4_NT"
VAT_HOP_LE = ("0", "5", "8", "10", "KCT", "KKKNT")
# Cấu hình DEMO công khai — KHÔNG phải chính sách hạch toán thật (241 hay 154, VAT, tài khoản giữ lại do CFO chốt riêng).
MAU_DEMO = {
    "ma": "MAU_NGHIEM_THU_DEMO_V1",
    "tk_chi_phi": "2412_DEMO",
    "tk_phai_tra": "331_DEMO",
    "tk_giu_lai": "3388_DEMO",
    "ghi_chu": "Cấu hình DEMO công khai: Nợ chi phí dự án = số chấp nhận trước VAT; Có phải trả nhà thầu = chấp nhận − giữ lại đợt; "
               "Có giữ lại theo đợt (TT-21 của hợp đồng, không phải bảo hành TT-31). VAT ghi theo hóa đơn nhà thầu (M2), không ở đây.",
}
NHAN_TONG_HOP = {"gt_hd": "Giá trị hợp đồng", "gt_lk_kt": "Lũy kế kỳ trước", "gt_kn": "Giá trị kỳ này", "gt_lk": "Lũy kế đến kỳ này",
                 "giu_lai": "Giữ lại đợt (nguồn)", "thu_hoi_tu": "Thu hồi tạm ứng (nguồn)", "tt_ky_nay": "Thanh toán kỳ này (nguồn)"}


def actor_mo_phong(actor) -> str:
    actor = text_id(actor, "actor")
    if not actor.startswith("MO_PHONG_"):
        raise DataError("ACTOR_MO_PHONG", "Gói DEMO chỉ nhận người thao tác mô phỏng (MO_PHONG_*); không dùng tài khoản thật.")
    return actor


def _so(value, field) -> int | None:
    if value is None or value == "":
        return None
    try:
        result = money_minor(value, 0)
    except DataError as exc:
        raise DataError("NT_SO_KHONG_HOP_LE", f"{field} phải là số nguyên VND (chuỗi hoặc số nguyên), không nhận số thực.") from exc
    if result < 0:
        raise DataError("NT_SO_AM", f"{field} không được âm.")
    return result


class NghiemThu:
    def __init__(self, store):
        if store.config.environment != "fixture":
            raise DataError("NT_DEMO_ONLY", "Hồ sơ nghiệm thu bridge chỉ chạy trong kho mô phỏng; kho thật đi qua giao_tiep (TL40), chưa tích hợp.")
        self.store, self.db = store, store.conn

    # ---------------------------------------------------------------- đồng bộ hồ sơ từ chứng từ NGHIEM_THU
    def _event(self, core: dict) -> str:
        return canonical_json([core["nguon"]["instance"], core["hop_dong"]["ma_hd"], core["dot"]])

    def dong_bo(self, actor: str = "MO_PHONG_KE_TOAN") -> int:
        """Tạo hồ sơ chờ cho chứng từ NGHIEM_THU chưa có hồ sơ; áp quan hệ bản thay theo thời điểm review. Chạy lại không trùng."""
        actor = actor_mo_phong(actor)
        created = 0
        with transaction(self.store):
            docs = self.db.execute("""SELECT d.id,d.core_json,d.first_attempt_id,a.original_name,a.artifact_hash FROM documents d
                JOIN attempts a ON a.id=d.first_attempt_id
                WHERE d.kind=? AND NOT EXISTS (SELECT 1 FROM quick_items i WHERE i.document_id=d.id)""", (KIND,)).fetchall()
            pending = sorted(((json.loads(r["core_json"]), r) for r in docs), key=lambda pair: (pair[0]["nguon"]["luc"], pair[0]["nguon"]["ma_review"]))
            for core, row in pending:
                run = self.db.execute("SELECT id FROM quick_runs WHERE source_attempt_id=? AND source_kind=?", (row["first_attempt_id"], SOURCE_KIND)).fetchone()
                run_id = run[0] if run else uid()
                if not run:
                    self.db.execute("INSERT INTO quick_runs(id,source_attempt_id,source_kind,created_at,actor,source_name,source_hash,source_info_json) VALUES (?,?,?,?,?,?,?,?)",
                                    (run_id, row["first_attempt_id"], SOURCE_KIND, now_utc(), actor, row["original_name"], row["artifact_hash"],
                                     canonical_json({"profile": "NGHIEM_THU_V1", "nguon": "#5 review", "instance": core["nguon"]["instance"]})))
                proposal = {"profile": "NGHIEM_THU_V1", "source_kind": SOURCE_KIND, "event": self._event(core), "business_date": core["ngay_nghiem_thu"],
                            "luc_review": core["nguon"]["luc"], "ma_review": core["nguon"]["ma_review"]}
                state, reason = "WAIT", ""
                prior = [p for p in self._event_items(proposal["event"])]
                newer = [p for p in prior if p["luc_review"] > proposal["luc_review"]]
                if newer:
                    state, reason = "SKIP", "Bản review cũ hơn bản đã có cho cùng hợp đồng/đợt; giữ làm bằng chứng."
                elif prior:
                    latest = max(prior, key=lambda p: (p["luc_review"], p["ma_review"]))
                    proposal["thay_cho"] = latest["id"]  # chỉ là quan hệ; điều kiện chặn tính động ở _chan_su_kien
                    for p in prior:
                        if p["state"] == "WAIT":
                            self.db.execute("UPDATE quick_items SET state='SKIP',reason=?,decided_at=?,actor=? WHERE id=?",
                                            ("Bị thay bởi review " + core["nguon"]["ma_review"], now_utc(), actor, p["id"]))
                            log(self.store, MODULE, "NT_BI_THAY", p["id"], actor, now_utc(), {"thay_boi_review": core["nguon"]["ma_review"]})
                item_id = uid()
                self.db.execute("INSERT INTO quick_items(id,run_id,document_id,proposal_json,state,reason) VALUES (?,?,?,?,?,?)",
                                (item_id, run_id, row["id"], canonical_json(proposal), state, reason))
                log(self.store, MODULE, "NT_NHAN", item_id, actor, now_utc(), {"ma_review": core["nguon"]["ma_review"], "trang_thai": state,
                                                                              "thay_cho": proposal.get("thay_cho")})
                created += 1
        return created

    def _event_items(self, event: str) -> list[dict]:
        """Mọi bản của cùng sự kiện (instance + HĐ + đợt), đọc lại trong giao dịch hiện tại — không dùng ảnh chụp lúc đồng bộ."""
        result = []
        for row in self.db.execute("""SELECT i.id,i.state,i.proposal_json FROM quick_items i JOIN quick_runs r ON r.id=i.run_id WHERE r.source_kind=?""", (SOURCE_KIND,)):
            proposal = json.loads(row["proposal_json"])
            if proposal.get("event") == event:
                result.append({"id": row["id"], "state": row["state"], "luc_review": proposal["luc_review"], "ma_review": proposal["ma_review"]})
        return result

    def _chan_su_kien(self, row) -> list[dict]:
        """Điều kiện cấp sự kiện, tính động: một sự kiện chỉ được xuất đầy đủ một lần; không hai bản cùng Đồng ý;
        bản cũ không sống lại khi đã có bản mới hơn chưa bị bỏ qua."""
        proposal = json.loads(row["proposal_json"])
        me = (proposal["luc_review"], proposal["ma_review"])
        out = []
        for other in self._event_items(proposal["event"]):
            if other["id"] == row["id"]:
                continue
            if other["state"] == "EXPORTED":
                out.append({"ma": "BAN_KHAC_DA_XUAT", "thong_diep": "Một bản của cùng hợp đồng/đợt đã xuất file soát — cần quy trình điều chỉnh có vết (chưa hỗ trợ trong gói DEMO), không xuất bản đầy đủ lần nữa."})
            elif other["state"] == "APPROVE":
                out.append({"ma": "BAN_KHAC_DANG_DUYET", "thong_diep": "Một bản khác của cùng hợp đồng/đợt đang Đã đồng ý — hoàn tác bản đó trước để không ghi công nợ hai lần."})
            elif other["state"] != "SKIP" and (other["luc_review"], other["ma_review"]) > me:
                out.append({"ma": "BAN_MOI_HON", "thong_diep": "Đã có bản review mới hơn của cùng hợp đồng/đợt — xử lý bản mới, hoặc Bỏ qua bản mới có lý do trước."})
        return list({c["ma"]: c for c in out}.values())

    # ---------------------------------------------------------------- đọc
    def _item(self, item_id) -> dict:
        row = self.db.execute("""SELECT i.*,d.core_json,d.id AS doc_id,d.first_attempt_id,a.artifact_hash,a.original_name,a.known_at AS attempt_known_at
            FROM quick_items i JOIN quick_runs r ON r.id=i.run_id JOIN documents d ON d.id=i.document_id JOIN attempts a ON a.id=d.first_attempt_id
            WHERE i.id=? AND r.source_kind=?""", (text_id(item_id, "id"), SOURCE_KIND)).fetchone()
        if not row:
            raise DataError("NT_ITEM", "Không thấy hồ sơ nghiệm thu.")
        return row

    def _catalog(self, kind: str, code: str, day: str) -> dict | None:
        for row in self.db.execute("SELECT core_json FROM documents WHERE kind=? AND json_extract(core_json,'$.code')=?", (kind, code)):
            core = json.loads(row[0])
            if core.get("valid_from", "0000") <= day and (core.get("valid_to") in (None, "") or day < core["valid_to"]):
                return core
        return None

    def _goi_y_mapping(self, core: dict) -> dict | None:
        """Mapping đã xác nhận gần nhất cho cùng instance + mã HĐ nguồn (chỉ gợi ý, người vẫn phải xác nhận)."""
        latest = None
        for row in self.db.execute("""SELECT i.decision_json,i.proposal_json,d.core_json FROM quick_items i JOIN quick_runs r ON r.id=i.run_id
            JOIN documents d ON d.id=i.document_id WHERE r.source_kind=? AND i.decision_json IS NOT NULL""", (SOURCE_KIND,)):
            other = json.loads(row["core_json"])
            if (other["nguon"]["instance"], other["hop_dong"]["ma_hd"]) == (core["nguon"]["instance"], core["hop_dong"]["ma_hd"]):
                decision = json.loads(row["decision_json"])
                if latest is None or decision.get("luc", "") > latest.get("luc", ""):
                    latest = decision
        return latest["mapping"] if latest else None

    def _lines(self, decision: dict, core: dict) -> list[dict]:
        so, mapping = decision["so"], decision["mapping"]
        accepted, retained = so.get("chap_nhan_truoc_vat"), so.get("giu_lai_dot")
        if accepted is None or retained is None:
            raise DataError("NT_SO_CHUA_XAC_NHAN", "Chưa xác nhận đủ số chấp nhận và giữ lại đợt; không dựng bút toán.")
        lines = [{"stt": 1, "no_co": "N", "tai_khoan": MAU_DEMO["tk_chi_phi"], "so_tien": accepted, "du_an": mapping["du_an"], "doi_tuong": mapping["doi_tuong"],
                  "dien_giai": f"Nghiệm thu đợt {core['dot']} · HĐ {mapping['ma_hd_chung']}"}]
        if accepted - retained > 0:
            lines.append({"stt": 2, "no_co": "C", "tai_khoan": MAU_DEMO["tk_phai_tra"], "so_tien": accepted - retained, "du_an": mapping["du_an"], "doi_tuong": mapping["doi_tuong"],
                          "dien_giai": "Phải trả nhà thầu theo nghiệm thu"})
        if retained > 0:
            lines.append({"stt": len(lines) + 1, "no_co": "C", "tai_khoan": MAU_DEMO["tk_giu_lai"], "so_tien": retained, "du_an": mapping["du_an"], "doi_tuong": mapping["doi_tuong"],
                          "dien_giai": "Giữ lại theo đợt (TT-21 hợp đồng) — không phải bảo hành"})
        return lines

    def chan(self, row) -> list[dict]:
        """Điều kiện chặn Đồng ý/xuất do server tính lại mỗi lần (không tin client)."""
        core, proposal = json.loads(row["core_json"]), json.loads(row["proposal_json"])
        decision = json.loads(row["decision_json"]) if row["decision_json"] else None
        out = []
        add = lambda code, message: out.append({"ma": code, "thong_diep": message})
        loi_nap = kiem_da_nap(core.get("da_nap"), core["dot"])
        if loi_nap:
            add("NGUON_CHUA_NAP", "Chưa có bằng chứng nạp CSDL review hợp lệ (#5): " + "; ".join(loi_nap) + ". Hồ sơ giữ chờ.")
        out.extend(self._chan_su_kien(row))
        if decision is None:
            add("CHUA_XAC_NHAN", "Chưa xác nhận mapping và số kế toán.")
            return out
        mapping, so = decision["mapping"], decision["so"]
        if mapping.get("phap_nhan") != self.store.config.entity_id:
            add("MAPPING_PHAP_NHAN", "Pháp nhân xác nhận không trùng pháp nhân của kho.")
        day = core["ngay_nghiem_thu"]
        if not self._catalog("PROJECT", mapping.get("du_an") or "", day):
            add("MAPPING_DU_AN", "Mã dự án không có trong danh mục hiệu lực tại ngày nghiệm thu.")
        if not self._catalog("COUNTERPARTY", mapping.get("doi_tuong") or "", day):
            add("MAPPING_DOI_TUONG", "Mã đối tượng nhà thầu không có trong danh mục hiệu lực tại ngày nghiệm thu (TK phải trả bắt buộc có đối tượng).")
        if not mapping.get("ma_hd_chung"):
            add("MAPPING_HOP_DONG", "Thiếu mã hợp đồng chung.")
        if not so.get("chap_nhan_truoc_vat"):
            add("SO_CHAP_NHAN", "Chưa có số chấp nhận hạch toán (trước VAT) đã xác nhận.")
        if so.get("co_so") != "TRUOC_VAT" or so.get("thue_suat_vat") not in VAT_HOP_LE:
            add("SO_VAT", "Chưa xác nhận cơ sở VAT (số trước VAT) và thuế suất.")
        if so.get("giu_lai_dot") is None:
            add("SO_GIU_LAI_CHUA_XAC_NHAN", "Chưa xác nhận số giữ lại đợt (nhập 0 nếu đúng là không giữ lại) — không tự lấy 0 hoặc chép số nguồn.")
        elif so.get("chap_nhan_truoc_vat") and so["giu_lai_dot"] >= so["chap_nhan_truoc_vat"]:
            add("SO_GIU_LAI", "Giữ lại đợt phải nhỏ hơn số chấp nhận.")
        if so.get("thu_hoi_tam_ung") is None:
            add("SO_THU_HOI_CHUA_XAC_NHAN", "Chưa xác nhận số thu hồi tạm ứng ghi nhận (nhập 0 nếu không thu hồi).")
        for tk in (MAU_DEMO["tk_chi_phi"], MAU_DEMO["tk_phai_tra"], MAU_DEMO["tk_giu_lai"]):
            if not self._catalog("ACCOUNT", tk, day):
                add("MAPPING_TAI_KHOAN", f"Tài khoản {tk} của mẫu DEMO chưa có trong danh mục — nạp danh mục DEMO nghiệm thu.")
        if not out:
            lines = self._lines(decision, core)
            no, co = sum(l["so_tien"] for l in lines if l["no_co"] == "N"), sum(l["so_tien"] for l in lines if l["no_co"] == "C")
            if no != co or no <= 0 or any(l["so_tien"] <= 0 for l in lines) or any(l["tai_khoan"] == MAU_DEMO["tk_phai_tra"] and not l["doi_tuong"] for l in lines):
                add("NO_CO_LECH", "Bút toán đề xuất không cân Nợ = Có hoặc thiếu đối tượng.")
        return out

    def _view(self, row) -> dict:
        core, proposal = json.loads(row["core_json"]), json.loads(row["proposal_json"])
        decision = json.loads(row["decision_json"]) if row["decision_json"] else None
        lines = json.loads(row["decision_lines_json"]) if row["decision_lines_json"] else None
        blockers = self.chan(row) if row["state"] in ("WAIT", "APPROVE") else []
        loi_nap = kiem_da_nap(core.get("da_nap"), core["dot"])
        if decision:  # tiền qua API dạng chuỗi — không mất chữ số ở JSON.parse của trình duyệt
            decision = {**decision, "so": {k: (_tien(v) if k in ("chap_nhan_truoc_vat", "giu_lai_dot", "thu_hoi_tam_ung") else v) for k, v in decision["so"].items()}}
        if lines:
            lines = [{**line, "so_tien": _tien(line["so_tien"])} for line in lines]
        return {"id": row["id"], "trang_thai": row["state"], "ly_do": row["reason"], "actor": row["actor"], "quyet_dinh_luc": row["decided_at"],
                "chung_tu_id": row["doc_id"], "tep_nguon": row["original_name"], "hash_raw": row["artifact_hash"], "hash_noi_dung": core["nguon"].get("hash_noi_dung"),
                "instance": core["nguon"]["instance"], "ma_review": core["nguon"]["ma_review"], "luc_review": core["nguon"]["luc"], "luc_basis": core["nguon"]["luc_basis"],
                "hop_dong": core["hop_dong"], "dot": core["dot"], "dot_truoc": core.get("dot_truoc"), "ngay_nghiem_thu": core["ngay_nghiem_thu"],
                "de_nghi": {"minor": _tien(core["de_nghi"]["minor"]), "goc": _goc(core["de_nghi"]["goc"])},
                "tong_hop": [{"khoa": k, "nhan": NHAN_TONG_HOP.get(k, v.get("nhan") or k), "nhan_nguon": v.get("nhan"), "minor": _tien(v.get("minor")), "goc": _goc(v.get("goc")), "o": v.get("o")}
                             for k, v in core["tong_hop"].items()],
                "anh_huong": {**core["anh_huong"], "goc": _goc(core["anh_huong"].get("goc"))}, "so_phat_hien": core.get("so_phat_hien"),
                "trang_thai_nguon": "DA_NAP_CSDL_REVIEW" if not loi_nap else core["trang_thai_nguon"] if core["trang_thai_nguon"] != "DA_NAP_CSDL_REVIEW" else "BANG_CHUNG_NAP_KHONG_HOP_LE",
                "da_nap": core.get("da_nap"), "da_nap_loi": loi_nap,
                "can_cu": core["can_cu"], "tai": core.get("tai"), "thieu": core["thieu"],
                "thay_cho": proposal.get("thay_cho"),
                "xac_nhan": decision, "goi_y_mapping": None if decision else self._goi_y_mapping(core), "but_toan": lines, "chan": blockers,
                "dong_y_duoc": row["state"] == "WAIT" and not blockers}

    def danh_sach(self) -> dict:
        rows = self.db.execute("""SELECT i.*,d.core_json,d.id AS doc_id,a.artifact_hash,a.original_name FROM quick_items i JOIN quick_runs r ON r.id=i.run_id
            JOIN documents d ON d.id=i.document_id JOIN attempts a ON a.id=d.first_attempt_id WHERE r.source_kind=? ORDER BY json_extract(i.proposal_json,'$.luc_review') DESC, i.id""",
                               (SOURCE_KIND,)).fetchall()
        exports = [dict(id=r["id"], luc=r["exported_at"], actor=r["actor"], so_dong=r["item_count"], tep=json.loads(r["files_json"]))
                   for r in self.db.execute("""SELECT e.* FROM quick_exports e JOIN quick_runs r ON r.id=e.run_id WHERE r.source_kind=? ORDER BY e.exported_at DESC""", (SOURCE_KIND,))]
        seen, unique_exports = set(), []
        for e in exports:
            key = e["tep"][0]["sha256"] if e["tep"] else e["id"]
            if key not in seen:
                seen.add(key); unique_exports.append(e)
        catalog = {kind: sorted({json.loads(r[0])["code"] for r in self.db.execute("SELECT core_json FROM documents WHERE kind=?", (kind,))}) for kind in ("PROJECT", "COUNTERPARTY", "ACCOUNT")}
        return {"ho_so": [self._view(r) for r in rows], "file_soat": unique_exports, "mau": MAU_DEMO, "vat_hop_le": list(VAT_HOP_LE), "danh_muc": catalog,
                "phap_nhan": self.store.config.entity_id, "muc_2": "KHOA", "production": "Chưa tích hợp giao_tiep.v1_ghi_ket_qua_review (TL40) — chỉ bridge DEMO K1."}

    # ---------------------------------------------------------------- ghi
    def xac_nhan(self, item_id, mapping, so, actor, at=None) -> dict:
        actor, at = actor_mo_phong(actor), instant_utc(at or now_utc())
        if not isinstance(mapping, dict) or not isinstance(so, dict):
            raise DataError("NT_XAC_NHAN", "Cần mapping và số kế toán dạng object.")
        allowed_mapping, allowed_so = {"phap_nhan", "ma_hd_chung", "du_an", "doi_tuong"}, {"chap_nhan_truoc_vat", "co_so", "thue_suat_vat", "giu_lai_dot", "thu_hoi_tam_ung", "ghi_chu"}
        if set(mapping) - allowed_mapping or set(so) - allowed_so:
            raise DataError("NT_TRUONG_LA", "Có trường ngoài hợp đồng xác nhận; không nhận âm thầm.")
        clean_mapping = {k: (mapping.get(k).strip() if isinstance(mapping.get(k), str) else None) for k in sorted(allowed_mapping)}
        if any(v is not None and len(v) > 80 for v in clean_mapping.values()):
            raise DataError("NT_MAPPING_DAI", "Mã mapping tối đa 80 ký tự.")
        clean_so = {"chap_nhan_truoc_vat": _so(so.get("chap_nhan_truoc_vat"), "Số chấp nhận"), "giu_lai_dot": _so(so.get("giu_lai_dot"), "Giữ lại đợt"),
                    "thu_hoi_tam_ung": _so(so.get("thu_hoi_tam_ung"), "Thu hồi tạm ứng"),
                    "co_so": so.get("co_so") if so.get("co_so") in ("TRUOC_VAT",) else None,
                    "thue_suat_vat": so.get("thue_suat_vat") if so.get("thue_suat_vat") in VAT_HOP_LE else None,
                    "ghi_chu": str(so.get("ghi_chu") or "")[:500]}
        with transaction(self.store):
            row = self._item(item_id)
            if row["state"] != "WAIT":
                raise DataError("NT_TRANG_THAI", "Chỉ xác nhận hồ sơ đang chờ.")
            if any(c["ma"] == "BAN_KHAC_DA_XUAT" for c in self._chan_su_kien(row)):
                raise DataError("NT_SU_KIEN_DA_XUAT", "Cùng hợp đồng/đợt đã có bản xuất file soát — cần quy trình điều chỉnh (chưa hỗ trợ trong gói DEMO); không xác nhận bản đầy đủ mới.")
            before = json.loads(row["decision_json"]) if row["decision_json"] else None
            decision = {"mapping": clean_mapping, "so": clean_so, "xac_nhan_boi": actor, "luc": at, "mau": MAU_DEMO["ma"],
                        "nguon_ma_review": json.loads(row["core_json"])["nguon"]["ma_review"]}
            self.db.execute("UPDATE quick_items SET decision_json=?,decision_lines_json=NULL WHERE id=?", (canonical_json(decision), row["id"]))
            row = self._item(item_id)
            if not self.chan(row):
                lines = self._lines(decision, json.loads(row["core_json"]))
                self.db.execute("UPDATE quick_items SET decision_lines_json=? WHERE id=?", (canonical_json(lines), row["id"]))
            log(self.store, MODULE, "NT_XAC_NHAN", row["id"], actor, at, {"truoc": before, "sau": decision})
            return self._view(self._item(item_id))

    def quyet_dinh(self, item_id, hanh_dong, actor, at=None, ly_do="") -> dict:
        actor, at = actor_mo_phong(actor), instant_utc(at or now_utc())
        if hanh_dong not in ("dong_y", "hoan_tac", "bo_qua"):
            raise DataError("NT_HANH_DONG", "Hành động chỉ nhận Đồng ý, Hoàn tác hoặc Bỏ qua.")
        ly_do = str(ly_do or "")[:500]
        with transaction(self.store):
            row = self._item(item_id)
            if hanh_dong == "dong_y":
                if row["state"] != "WAIT":
                    raise DataError("NT_TRANG_THAI", "Chỉ Đồng ý hồ sơ đang chờ.")
                blockers = self.chan(row)
                if blockers:
                    raise DataError("NT_CHUA_DU_DIEU_KIEN", "Chưa thể Đồng ý: " + "; ".join(b["thong_diep"] for b in blockers))
                decision = json.loads(row["decision_json"])
                lines = self._lines(decision, json.loads(row["core_json"]))
                self.db.execute("UPDATE quick_items SET state='APPROVE',decision_lines_json=?,decided_at=?,actor=?,reason='' WHERE id=?",
                                (canonical_json(lines), at, actor, row["id"]))
            elif hanh_dong == "hoan_tac":
                if row["state"] != "APPROVE":
                    raise DataError("NT_TRANG_THAI", "Chỉ hoàn tác hồ sơ Đã đồng ý chưa xuất; sau xuất phải lập điều chỉnh.")
                self.db.execute("UPDATE quick_items SET state='WAIT',decided_at=?,actor=? WHERE id=?", (at, actor, row["id"]))
            else:
                if row["state"] != "WAIT":
                    raise DataError("NT_TRANG_THAI", "Chỉ Bỏ qua hồ sơ đang chờ.")
                self.db.execute("UPDATE quick_items SET state='SKIP',reason=?,decided_at=?,actor=? WHERE id=?", (ly_do or "Bỏ qua", at, actor, row["id"]))
            log(self.store, MODULE, "NT_" + hanh_dong.upper(), row["id"], actor, at, {"truoc": row["state"], "ly_do": ly_do})
            return self._view(self._item(item_id))

    def xuat(self, actor, *, muc_2=False, at=None) -> dict:
        actor, at = actor_mo_phong(actor), instant_utc(at or now_utc())
        if muc_2 is not False:
            raise DataError("MUC_2_KHOA", "Mức 2 (file nhập Junsky) đang khóa; chỉ xuất file soát.")
        with transaction(self.store):
            rows = self.db.execute("""SELECT i.*,d.core_json,d.id AS doc_id,a.artifact_hash,a.original_name FROM quick_items i JOIN quick_runs r ON r.id=i.run_id
                JOIN documents d ON d.id=i.document_id JOIN attempts a ON a.id=d.first_attempt_id WHERE r.source_kind=? AND i.state='APPROVE' ORDER BY i.id""", (SOURCE_KIND,)).fetchall()
            if not rows:
                raise DataError("NT_XUAT_RONG", "Chưa có hồ sơ nghiệm thu Đã đồng ý để xuất file soát.")
            table, total = [], 0
            for row in rows:
                core, decision, lines = json.loads(row["core_json"]), json.loads(row["decision_json"]), json.loads(row["decision_lines_json"])
                if sum(l["so_tien"] for l in lines if l["no_co"] == "N") != sum(l["so_tien"] for l in lines if l["no_co"] == "C"):
                    raise DataError("NO_CO_LECH", "Bút toán đã duyệt không cân; không xuất.")
                # Kiểm lại toàn bộ điều kiện nghiệp vụ và cấp sự kiện trong cùng giao dịch, trước khi tạo file/đổi trạng thái.
                blockers = self.chan(row)
                if blockers:
                    raise DataError("NT_XUAT_CHAN", f"Không xuất: hồ sơ {core['nguon']['ma_review']} — " + "; ".join(b["thong_diep"] for b in blockers))
                if lines != self._lines(decision, core):
                    raise DataError("NT_BUT_TOAN_DOI", "Bút toán đã duyệt khác bút toán dựng lại từ xác nhận; không xuất.")
                total += decision["so"]["chap_nhan_truoc_vat"]
                for line in lines:
                    table.append(["Nghiệm thu — không phát sinh thu/chi tiền", core["ngay_nghiem_thu"], self.store.config.entity_id, decision["mapping"]["ma_hd_chung"],
                                  core["dot"], line["stt"], "Nợ" if line["no_co"] == "N" else "Có", line["tai_khoan"], _o_tien_excel(line["so_tien"]), line["doi_tuong"], line["du_an"],
                                  line["dien_giai"], decision["so"]["thue_suat_vat"], _o_tien_excel(decision["so"]["thu_hoi_tam_ung"]),
                                  f"#5 {core['nguon']['instance']} · review {core['nguon']['ma_review']} · HĐ nguồn {core['hop_dong']['ma_hd']}",
                                  row["artifact_hash"], decision["xac_nhan_boi"], row["actor"], row["decided_at"]])
            wb = excel.workbook()
            excel.table(wb, "FILE_SOAT_NGHIEM_THU", ["loai_chung_tu", "ngay_nghiem_thu", "phap_nhan", "ma_hd_chung", "dot", "dong", "no_co", "tai_khoan", "so_tien_vnd",
                                                     "doi_tuong", "du_an", "dien_giai", "thue_suat_vat_xac_nhan", "thu_hoi_tam_ung_xac_nhan", "nguon", "hash_raw_nguon",
                                                     "nguoi_xac_nhan_so", "nguoi_dong_y", "luc_dong_y"], table)
            excel.table(wb, "CANH_BAO", ["noi_dung"], [["DEMO — dữ liệu mô phỏng, không phải chứng từ thật"], ["File soát, KHÔNG phải file nhập Junsky; mức 2 khóa"],
                                                       [MAU_DEMO["ghi_chu"]], ["Nghiệm thu: không phát sinh thu/chi tiền ngân hàng, không có dòng tài khoản tiền"],
                                                       ["Số tiền từ 10^15 trở lên ghi dạng chữ để giữ đủ chữ số (Excel chỉ giữ 15 chữ số)"]])
            raw = excel.to_bytes(wb)
            digest, export_id = sha256(raw), uid()
            name = f"FILE-SOAT-NGHIEM-THU-{at[:10]}-{export_id[:8]}.xlsx"
            relative = f"xuat-nghiem-thu/{export_id}.xlsx"
            write_immutable(self.store.root / relative, raw)
            files = [{"ten": name, "duong_dan": relative, "sha256": digest}]
            for run_id in sorted({r["run_id"] for r in rows}):
                items = [r for r in rows if r["run_id"] == run_id]
                self.db.execute("INSERT INTO quick_exports(id,run_id,exported_at,actor,item_count,total_minor,files_json) VALUES (?,?,?,?,?,?,?)",
                                (export_id if run_id == rows[0]["run_id"] else uid(), run_id, at, actor, len(items),
                                 sum(json.loads(r["decision_json"])["so"]["chap_nhan_truoc_vat"] for r in items), canonical_json(files)))
            for row in rows:
                self.db.execute("UPDATE quick_items SET state='EXPORTED' WHERE id=?", (row["id"],))
            log(self.store, MODULE, "NT_XUAT_FILE_SOAT", export_id, actor, at, {"so_ho_so": len(rows), "sha256": digest, "muc_2": False})
            return {"id": export_id, "ten": name, "so_ho_so": len(rows), "tong_chap_nhan": _tien(total), "sha256": digest}

    def tep_xuat(self, export_id) -> tuple[str, bytes]:
        row = self.db.execute("""SELECT e.files_json FROM quick_exports e JOIN quick_runs r ON r.id=e.run_id WHERE e.id=? AND r.source_kind=?""",
                              (text_id(export_id, "id"), SOURCE_KIND)).fetchone()
        if not row:
            raise DataError("NT_FILE", "Không thấy file soát nghiệm thu.")
        info = json.loads(row[0])[0]
        path = (self.store.root / info["duong_dan"]).resolve()
        if not path.is_relative_to(self.store.root.resolve()):
            raise DataError("NT_FILE", "Đường dẫn file soát không hợp lệ.")
        raw = path.read_bytes()
        if sha256(raw) != info["sha256"]:
            raise DataError("ARTIFACT_CHANGED", "File soát đã bị thay đổi.")
        return info["ten"], raw
