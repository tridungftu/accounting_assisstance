"""CRM 42 S1: projection chỉ đọc, dùng giao dịch/danh tính và scope CRM-G có sẵn.

Không trả raw JSON, CCCD, STK, liên hệ hay bằng chứng bản ký. Tiền là chuỗi minor.
Thẻ tính sau bộ lọc thông thường, trước lọc thẻ và phân trang. W2 chỉ đếm CHO_KY
(chưa có n nhắc); W5 chỉ đếm lịch đến hạn 7 ngày (chưa có nguồn tiền chưa rõ).
Không cộng cột Junsky giữa các HĐ (số dư cấp khách).
Scope BH dùng binding CRM_KY_KET hiện hành, không suy quyền từ người tạo. HĐ
luồng B chưa có binding này sẽ ẩn với BH; KT/CFO/XEM đọc theo PN + module CRM.
Mốc riêng dự án đang dùng: hạn = ngày thực tế + n; chưa có thực tế chỉ trả
dot_ke_tiep.han_du_kien và trạng thái MOC_DU_KIEN, không đếm QUA_HAN/W5.
Hai bổ sung API này giữ nguyên nghĩa các trường cũ; mốc chuẩn không đổi.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from ..ha_tang.primitives import DataError
from . import quyen

TRANG_THAI = {
    "SOAN_THAO": "Soạn thảo", "CHO_KY": "Chờ ký", "DA_KY": "Đã ký — chờ kế toán kiểm",
    "DANG_KIEM": "Đang kế toán kiểm", "CHO_KIEM": "Chờ kiểm", "CHO_DUYET": "Chờ CFO duyệt tham số",
    "CHO_BO_SUNG": "Chờ bổ sung", "TRA_LAI_CHO_KY_LAI": "Trả lại — chờ quy trình ký lại",
    "HIEU_LUC": "Hiệu lực", "HUY": "Hủy", "TU_CHOI": "Từ chối", "HET_HIEU_LUC": "Hết hiệu lực",
}
CO = {"THIEU_CAN_CU", "LECH_BAN_KY", "QUA_HAN", "TRA_LAI", "CHO_BO_SUNG"}
THAM_SO = {"trang", "kich_thuoc_trang", "phap_nhan", "loai", "du_an", "trang_thai", "co", "nguoi_phu_trach",
           "ngay_ky_tu", "ngay_ky_den", "ngay_hieu_luc_tu", "ngay_hieu_luc_den", "tim", "the"}
_MOC_DU_AN_RE = (r"^SU_KIEN:(DAM-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                 r"[0-9a-f]{4}-[0-9a-f]{12})(?:_([1-9][0-9]*))?$")


def bo_loc(query: dict) -> dict:
    """Query parse_qs hoặc tham số service: một giá trị, có giới hạn, không authority."""
    def sai(noi_dung):
        raise DataError("CRM_S1_THAM_SO_SAI", noi_dung)

    if not isinstance(query, dict) or set(query) - THAM_SO:
        sai("Bộ lọc có tham số không được hỗ trợ.")
    out = {}
    for k, v in query.items():
        if isinstance(v, list):
            if len(v) != 1:
                sai(f"Tham số {k} không được lặp.")
            v = v[0]
        if not isinstance(v, str) or len(v) > (200 if k == "tim" else 100) or any(ord(c) < 32 for c in v):
            sai(f"Tham số {k} sai kiểu hoặc quá dài.")
        v = v.strip()
        if k in ("trang", "kich_thuoc_trang"):
            if not re.fullmatch(r"[0-9]{1,6}", v) or not 1 <= int(v) <= (100000 if k == "trang" else 100):
                sai(f"Tham số {k} phải là số nguyên dương trong giới hạn.")
            out[k] = int(v)
        elif k.startswith("ngay_"):
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                    raise ValueError
                out[k] = date.fromisoformat(v).isoformat()
            except ValueError:
                sai(f"Tham số {k} phải là ngày YYYY-MM-DD hợp lệ.")
        elif v:
            out[k] = v
    for k in ("ngay_ky", "ngay_hieu_luc"):
        if out.get(k + "_tu", "0001") > out.get(k + "_den", "9999"):
            sai("Ngày bắt đầu không được sau ngày kết thúc.")
    for k, tap in (("trang_thai", TRANG_THAI), ("co", CO), ("the", {"W1", "W2", "W3", "W4", "W5"}),
                   ("loai", {"XAY_DUNG", "THUE_DAT", "BAN_NHA", "DICH_VU", "KHAC"})):
        if k in out and out[k] not in tap:
            sai(f"Giá trị {k} không hợp lệ.")
    return {"trang": 1, "kich_thuoc_trang": 25, **out}


# Scope/metadata rẻ dùng chung hai bước; không gọi G5 hay dựng lịch/sổ ở bước đếm.
_PHAM_VI = """
WITH scoped AS MATERIALIZED (
    SELECT h.*, tt.trang_thai AS s1_trang_thai, hh.id AS hieu_luc_id,
           ((h.phap_nhan_id = ANY(%(pns_tien)s::uuid[])
             AND master.ktt_duoc(h.phap_nhan_id, 'M1')
             AND master.ktt_co_vai(h.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO'], NULL))
            OR master.ktt_co_vai(h.phap_nhan_id, ARRAY['BAN_HANG'], NULL)) AS xem_tien
    FROM master.hop_dong h
    JOIN master.phap_nhan p ON p.id = h.phap_nhan_id
    LEFT JOIN master.du_an a ON a.id = h.du_an_id AND a.phap_nhan_id = h.phap_nhan_id
    LEFT JOIN master.crm_kiem_ho_so ho ON ho.hop_dong_id = h.id AND ho.phap_nhan_id = h.phap_nhan_id
    LEFT JOIN LATERAL (SELECT v.trang_thai, v.kiem_luc FROM master.hop_dong_phien_ban v
                      WHERE v.hop_dong_id = h.id ORDER BY v.phien_ban DESC LIMIT 1) pb ON true
    LEFT JOIN master.hop_dong_phien_ban hh ON hh.id = master.crm_phien_ban_hieu_luc(h.id, %(ngay)s)
    CROSS JOIN LATERAL (SELECT coalesce(ho.trang_thai, h.crm_giao_ket,
        CASE WHEN pb.trang_thai = 'CHO_DUYET' AND pb.kiem_luc IS NULL THEN 'CHO_KIEM'
             WHEN pb.trang_thai = 'CHO_DUYET' THEN 'CHO_DUYET' ELSE h.trang_thai END) AS trang_thai) tt
    WHERE h.module_chu IS NULL AND h.loai NOT IN ('VAY','MUA')
      AND master.ktt_danh_tinh() IS NOT NULL AND master.ktt_duoc(h.phap_nhan_id, 'CRM')
      AND (master.ktt_co_vai(h.phap_nhan_id, ARRAY['KE_TOAN','KE_TOAN_TRUONG','CFO','XEM'], NULL)
           OR (master.ktt_co_vai(h.phap_nhan_id, ARRAY['BAN_HANG'], NULL)
               AND EXISTS (SELECT 1 FROM master.crm_hd_soan s WHERE s.hop_dong_id = h.id
                           AND s.phap_nhan_id = h.phap_nhan_id AND master.crm_ky_pham_vi_duoc(s.id))))
      {dieu_kien}
)
"""

_COT = """SELECT h.id, h.xem_tien, p.ma AS phap_nhan, h.ma_noi_bo, h.so_hop_dong, h.loai,
       lh.ma AS loai_hinh, d.ten_phap_ly AS khach, j.object_id_junsky AS ma_khach,
       a.ma_junsky AS du_an, a.ten AS du_an_ten,
       r.du_lieu #>> '{bao_gia,don_vi,ma}' AS lo_can,
       CASE WHEN h.doi_tac_id IS NULL THEN r.du_lieu #>> '{bao_gia,khach,du_thao,ten}' END AS khach_du_thao,
       CASE WHEN h.xem_tien THEN h.gia_tri_minor END AS gia_tri_minor, h.tien_te, h.ngay_ky, h.tao_luc,
       h.s1_trang_thai AS trang_thai,
       coalesce((SELECT array_agg(DISTINCT n.dang_nhap ORDER BY n.dang_nhap)
                 FROM master.crm_ky_pham_vi b JOIN master.phan_cong_hanh_dong pc ON pc.id = b.phan_cong_id
                 JOIN master.nguoi_dung n ON n.id = pc.nguoi_dung_id
                 WHERE b.hop_dong_id = h.id AND b.soan_id = s.id AND b.phap_nhan_id = h.phap_nhan_id
                   AND b.thu_hoi_luc IS NULL AND pc.thu_hoi_luc IS NULL AND pc.module = 'CRM'
                   AND pc.phap_nhan_id = h.phap_nhan_id AND pc.hanh_dong = 'CRM_KY_KET'
                   AND (pc.loai_hinh_id IS NULL OR pc.loai_hinh_id = s.loai_hinh_id)
                   AND b.du_an_id IS NOT DISTINCT FROM h.du_an_id
                   AND n.trang_thai = 'HOAT_DONG' AND n.vai_tro = 'BAN_HANG'), ARRAY[]::text[]) AS nguoi_phu_trach,
       mv.phien_ban AS mau_phien_ban,
       CASE WHEN s.id IS NOT NULL THEN 'MAU' ELSE pb.nguon END AS nguon,
       hh.phien_ban AS phien_ban_hieu_luc, hh.ngay_hieu_luc,
       EXISTS (SELECT 1 FROM master.hop_dong_phien_ban v WHERE v.hop_dong_id = h.id
               AND v.trang_thai = 'CHO_DUYET' AND v.kiem_luc IS NULL) AS pb_cho_kiem,
       EXISTS (SELECT 1 FROM kho.viec_can_duyet w WHERE w.phap_nhan_id = h.phap_nhan_id AND w.module = 'CRM'
               AND w.trang_thai = 'CHO_BO_SUNG'
               AND ((w.tham_chieu_bang = 'master.hop_dong' AND w.tham_chieu_id = h.id)
                    OR (w.tham_chieu_bang = 'master.hop_dong_phien_ban' AND EXISTS
                        (SELECT 1 FROM master.hop_dong_phien_ban v WHERE v.id = w.tham_chieu_id AND v.hop_dong_id = h.id)))) AS bo_sung_mo,
"""
_NOI = """FROM scoped h JOIN master.phap_nhan p ON p.id = h.phap_nhan_id
LEFT JOIN master.doi_tac d ON d.id = h.doi_tac_id
LEFT JOIN LATERAL (SELECT object_id_junsky FROM master.doi_tac_ma_junsky j
                   WHERE j.doi_tac_id = h.doi_tac_id AND j.phap_nhan_id = h.phap_nhan_id AND j.valid_to IS NULL
                   ORDER BY j.valid_from DESC, j.id LIMIT 1) j ON true
LEFT JOIN master.du_an a ON a.id = h.du_an_id AND a.phap_nhan_id = h.phap_nhan_id
LEFT JOIN master.loai_hinh_doanh_thu lh ON lh.id = h.loai_hinh_dt_id
LEFT JOIN master.crm_hd_soan s ON s.hop_dong_id = h.id AND s.phap_nhan_id = h.phap_nhan_id
LEFT JOIN master.crm_hd_soan_rev r ON r.soan_id = s.id AND r.revision = s.revision_hien_hanh
LEFT JOIN master.crm_mau_phien_ban mv ON mv.id = r.mau_phien_ban_id
LEFT JOIN master.crm_hd_ky k ON k.hop_dong_id = h.id AND k.phap_nhan_id = h.phap_nhan_id
LEFT JOIN master.crm_kiem_ho_so ho ON ho.hop_dong_id = h.id AND ho.phap_nhan_id = h.phap_nhan_id
LEFT JOIN LATERAL (SELECT v.nguon, v.trang_thai, v.kiem_luc FROM master.hop_dong_phien_ban v
                   WHERE v.hop_dong_id = h.id ORDER BY v.phien_ban DESC LIMIT 1) pb ON true
LEFT JOIN master.hop_dong_phien_ban hh ON hh.id = h.hieu_luc_id
"""

# Chỉ boolean/count cho thẻ/cờ. Cùng điều kiện với crm_kiem_g5_xet(VAN_HANH)
# nhưng không dựng graph/JSON bằng chứng; không nhận lech_mot_phan là LECH.
_TOM_TAT = """
       CASE WHEN h.xem_tien THEN h.gia_tri_minor IS NULL ELSE false END AS thieu_gia_tri,
       CASE WHEN h.xem_tien THEN coalesce(lc.thieu, false) ELSE false END AS thieu_lich,
       CASE WHEN h.xem_tien THEN coalesce(lc.qua_han, false) ELSE false END AS qua_han,
       CASE WHEN h.xem_tien THEN coalesce(lc.den_han, 0) ELSE 0 END AS den_han,
       EXISTS (SELECT 1 FROM jsonb_array_elements(gq.lech) e
               WHERE gd.nhan = 'VAN_HANH' AND gq.trang_thai = 'LECH'
                 AND NOT EXISTS (SELECT 1 FROM master.crm_kiem_xu_ly_lech x
                                 WHERE x.ky_id = k.id AND x.loai = 'G5_LECH'
                                   AND x.muc_tieu_id = gq.id AND x.ma_lech = e->>'ma')) AS lech
"""
# Dùng chung ở truy vấn đếm và chi tiết, trong snapshot RR của S1. Chỉ đọc
# mốc cùng dự án/pháp nhân, dòng đang mở và đã hiệu lực tại ngày máy chủ.
_NOI_MOC_DU_AN = """
    LEFT JOIN LATERAL (
        SELECT s.ngay_du_kien, s.ngay_thuc_te, coalesce(ma.phan[2], '0')::integer AS so_ngay
        FROM (SELECT regexp_match(l.moc, '""" + _MOC_DU_AN_RE + """') AS phan) ma
        JOIN master.crm_da_moc m ON m.ma = ma.phan[1] AND m.phap_nhan_id = h.phap_nhan_id
        JOIN master.crm_da_ban d ON d.id = m.da_ban_id AND d.phap_nhan_id = h.phap_nhan_id
        JOIN master.crm_da_moc_ls s ON s.moc_id = m.id AND s.phap_nhan_id = h.phap_nhan_id
        WHERE l.han IS NULL AND h.xem_tien AND d.du_an_id = h.du_an_id
          AND s.dang_dung AND s.hieu_luc_den IS NULL AND s.hieu_luc_tu <= %(ngay)s
    ) dm ON true
"""
_THU = """
, thu_nghia_vu AS MATERIALIZED (
    SELECT v.hop_dong_id, x.khoa_nghia_vu, sum(lk.so_tien_khop_minor) AS thu
    FROM scoped h JOIN master.hop_dong_phien_ban v ON v.hop_dong_id = h.id
    JOIN master.lich_thu x ON x.phien_ban_id = v.id
    JOIN kho.lien_ket_chung_tu lk ON lk.lich_thu_id = x.id AND lk.trang_thai <> 'HUY'
    GROUP BY v.hop_dong_id, x.khoa_nghia_vu
), lich_dem AS MATERIALIZED (
    SELECT h.id, bool_or(l.so_tien_minor IS NULL) AS thieu,
           bool_or(coalesce(l.han, dm.ngay_thuc_te + dm.so_ngay) < %(ngay)s
                   AND l.so_tien_minor > coalesce(t.thu, 0)) AS qua_han,
           count(*) FILTER (WHERE coalesce(l.han, dm.ngay_thuc_te + dm.so_ngay)
                                  BETWEEN %(ngay)s AND %(ngay)s + 7
                            AND l.so_tien_minor > coalesce(t.thu, 0)) AS den_han
    FROM scoped h JOIN master.lich_thu l ON l.phien_ban_id = h.hieu_luc_id AND l.trang_thai <> 'HUY'
    LEFT JOIN thu_nghia_vu t ON t.hop_dong_id = h.id AND t.khoa_nghia_vu = l.khoa_nghia_vu
""" + _NOI_MOC_DU_AN + """    GROUP BY h.id
)
"""
_NOI_TOM_TAT = """
LEFT JOIN LATERAL (
    SELECT x.id, x.nhan FROM master.crm_g5_dang_ky x
    WHERE x.phap_nhan_id = k.phap_nhan_id AND x.loai_hinh_id = s.loai_hinh_id
      AND x.mau_phien_ban_id = k.mau_phien_ban_id AND x.danh_muc_ref = k.danh_muc_ref
      AND x.danh_muc_rev = k.danh_muc_rev AND x.danh_muc_digest = k.danh_muc_digest
      AND x.profile_sha256 = k.profile_sha256
      AND NOT EXISTS (SELECT 1 FROM master.crm_g5_thu_hoi t WHERE t.loai = 'DANG_KY' AND t.doi_tuong_id = x.id)
    ORDER BY x.thu_tu DESC LIMIT 1
) gd ON true
LEFT JOIN LATERAL (
    SELECT x.id, x.trang_thai, x.lech FROM master.crm_g5_ket_qua x
    WHERE x.ky_id = k.id AND x.dang_ky_id = gd.id AND x.ky_pdf_sha256 = k.ky_pdf_sha256
    ORDER BY x.thu_tu DESC LIMIT 1
) gq ON true
LEFT JOIN lich_dem lc ON lc.id = h.id
"""

_JUNSKY = """
, khach_trang AS MATERIALIZED (
    SELECT DISTINCT h.phap_nhan_id, j.object_id_junsky AS ma_khach
    FROM scoped h JOIN master.doi_tac_ma_junsky j
      ON j.doi_tac_id = h.doi_tac_id AND j.phap_nhan_id = h.phap_nhan_id AND j.valid_to IS NULL
    WHERE h.xem_tien
), so_moi AS MATERIALIZED (
    SELECT DISTINCT ON (n.phap_nhan_id, n.doi_tac_junsky)
           n.phap_nhan_id, n.doi_tac_junsky, n.ngay_chup
    FROM kho.cong_no_mo n JOIN khach_trang kt
      ON kt.phap_nhan_id = n.phap_nhan_id AND kt.ma_khach = n.doi_tac_junsky
    WHERE n.tai_khoan LIKE '131%%'
    ORDER BY n.phap_nhan_id, n.doi_tac_junsky, n.ngay_chup DESC
), so_nhom AS (
    SELECT n.phap_nhan_id, n.doi_tac_junsky, n.ngay_chup, n.tai_khoan, n.tien_te,
           CASE WHEN count(n.con_lai_minor) = count(*) THEN sum(n.con_lai_minor) END AS so_du
    FROM kho.cong_no_mo n JOIN so_moi m USING (phap_nhan_id, doi_tac_junsky, ngay_chup)
    WHERE n.tai_khoan LIKE '131%%'
    GROUP BY n.phap_nhan_id, n.doi_tac_junsky, n.ngay_chup, n.tai_khoan, n.tien_te
), so_khach AS MATERIALIZED (
    SELECT phap_nhan_id, doi_tac_junsky,
           jsonb_agg(jsonb_build_object('ngay_so', ngay_chup, 'tai_khoan', tai_khoan,
                     'tien_te', tien_te, 'so_du_minor', so_du::text) ORDER BY tai_khoan, tien_te) AS so_junsky
    FROM so_nhom GROUP BY phap_nhan_id, doi_tac_junsky
)
"""
_CHI_TIET = """
       coalesce((SELECT jsonb_agg(jsonb_build_object('id', l.id, 'dot', l.dot, 'han', l.han, 'moc', l.moc,
                      'moc_ngay_du_kien', dm.ngay_du_kien, 'moc_ngay_thuc_te', dm.ngay_thuc_te,
                      'so_tien_minor', l.so_tien_minor::text, 'tien_te', l.tien_te,
                      'da_thu_minor', master.crm_da_lien_ket(h.id, l.khoa_nghia_vu)::text) ORDER BY l.dot, l.id)
                 FROM master.lich_thu l
""" + _NOI_MOC_DU_AN + """                 WHERE h.xem_tien AND l.phien_ban_id = h.hieu_luc_id
                   AND l.trang_thai <> 'HUY'), '[]'::jsonb) AS lich,
       CASE WHEN k.id IS NOT NULL THEN master.crm_kiem_g5_xet(k.id, 'VAN_HANH') END AS g5,
       coalesce((SELECT jsonb_agg(jsonb_build_object('muc_tieu_id', x.muc_tieu_id, 'ma_lech', x.ma_lech))
                 FROM master.crm_kiem_xu_ly_lech x WHERE x.ky_id = k.id AND x.loai = 'G5_LECH'), '[]'::jsonb) AS xu_ly,
       CASE WHEN h.xem_tien THEN coalesce(sj.so_junsky, '[]'::jsonb) ELSE '[]'::jsonb END AS so_junsky
"""
SQL = _PHAM_VI + _THU + _COT + _TOM_TAT + _NOI + _NOI_TOM_TAT + "ORDER BY h.tao_luc DESC, h.id"
SQL_TRANG = (_PHAM_VI + _JUNSKY + _COT + _CHI_TIET + _NOI +
             "LEFT JOIN so_khach sj ON sj.phap_nhan_id = h.phap_nhan_id AND sj.doi_tac_junsky = j.object_id_junsky " +
             "ORDER BY h.tao_luc DESC, h.id LIMIT 100")


def _sql(sql, loc, pns_tien, ngay, ids=None):
    params = {"ngay": ngay, "pns_tien": pns_tien}
    dieu_kien = []
    for k, cot in (("phap_nhan", "p.ma"), ("loai", "h.loai"), ("du_an", "a.ma_junsky"), ("trang_thai", "tt.trang_thai")):
        if k in loc:
            dieu_kien.append(f"AND {cot} = %({k})s")
            params[k] = loc[k]
    for k, cot in (("ngay_ky", "h.ngay_ky"), ("ngay_hieu_luc", "hh.ngay_hieu_luc")):
        for hau_to, dau in (("tu", ">="), ("den", "<=")):
            ten = k + "_" + hau_to
            if ten in loc:
                dieu_kien.append(f"AND {cot} {dau} %({ten})s::date")
                params[ten] = loc[ten]
    if ids is not None:
        dieu_kien.append("AND h.id = ANY(%(ids)s::uuid[])")
        params["ids"] = ids
    return sql.replace("{dieu_kien}", "\n      ".join(dieu_kien)), params


def _ngay(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _dong(r: dict, hom_nay: date) -> dict:
    """Whitelist tóm tắt S1, không phản chiếu trường tùy ý từ DB/mock ra HTTP."""
    xem_tien = bool(r.get("xem_tien"))
    lich = [dict(l) for l in r.get("lich") or []] if xem_tien else []
    for l in lich:
        moc = re.fullmatch(_MOC_DU_AN_RE, l.get("moc") or "")
        if not l.get("han") and moc:
            n = timedelta(days=int(moc[2] or 0))
            if l.get("moc_ngay_thuc_te"):
                l["han"] = (date.fromisoformat(_ngay(l["moc_ngay_thuc_te"])) + n).isoformat()
            elif l.get("moc_ngay_du_kien"):
                l["han_du_kien"] = (date.fromisoformat(_ngay(l["moc_ngay_du_kien"])) + n).isoformat()
    co, so_tien, da_thu, con_lai, den_han, qua_han = [], {}, {}, {}, 0, False
    thieu_tien_te = set()
    for l in lich:
        tt, tien = l["tien_te"], l["so_tien_minor"]
        if tien is None or l["da_thu_minor"] is None:
            co.append("THIEU_CAN_CU")
            thieu_tien_te.add(tt)
            continue
        tien, thu = int(tien), int(l["da_thu_minor"])
        so_tien[tt] = so_tien.get(tt, 0) + tien
        da_thu[tt] = da_thu.get(tt, 0) + thu
        con_lai[tt] = con_lai.get(tt, 0) + max(0, tien - thu)
        if l.get("han") and tien > thu:
            han = date.fromisoformat(_ngay(l["han"]))
            den_han += hom_nay <= han <= hom_nay + timedelta(days=7)
            qua_han |= han < hom_nay
    xu_ly = {(str(x["muc_tieu_id"]), x["ma_lech"]) for x in r.get("xu_ly") or []}
    g5 = r.get("g5") or {}
    lech = g5.get("trang_thai") == "LECH" and any(
        (str(g5.get("ket_qua_id")), e["ma"]) not in xu_ly for e in g5.get("lech") or [])
    if lech:
        co.append("LECH_BAN_KY")
    if qua_han:
        co.append("QUA_HAN")
    tt = r["trang_thai"]
    if tt == "TRA_LAI_CHO_KY_LAI":
        co.append("TRA_LAI")
    if tt == "CHO_BO_SUNG" or r.get("bo_sung_mo"):
        co.append("CHO_BO_SUNG")
    if xem_tien and r.get("gia_tri_minor") is None:
        co.append("THIEU_CAN_CU")
    ds_tien = [{"tien_te": t, "phai_thu_minor": None if t in thieu_tien_te else str(so_tien[t]),
                "da_thu_minor": None if t in thieu_tien_te else str(da_thu[t]),
                "con_lai_minor": None if t in thieu_tien_te else str(con_lai[t])} for t in sorted(set(so_tien) | thieu_tien_te)]
    chua_thu = [l for l in lich if l["so_tien_minor"] is None or l["da_thu_minor"] is None
                or int(l["so_tien_minor"]) > int(l["da_thu_minor"])]
    chua_thu.sort(key=lambda l: (not bool(l.get("han")), _ngay(l.get("han")) or "", l["dot"]))
    dot = chua_thu[0] if chua_thu else None
    junsky = [{"ngay_so": _ngay(z["ngay_so"]), "tai_khoan": z["tai_khoan"], "tien_te": z["tien_te"],
               "so_du_minor": None if z["so_du_minor"] is None else str(z["so_du_minor"])} for z in r.get("so_junsky") or []]
    viec = {"W1": int(tt in ("CHO_BO_SUNG", "TRA_LAI_CHO_KY_LAI") or bool(r.get("bo_sung_mo"))), "W2": int(tt == "CHO_KY"),
            "W3": int(tt in ("DA_KY", "DANG_KIEM", "CHO_KIEM") or bool(r.get("pb_cho_kiem"))),
            "W4": int(lech), "W5": den_han}
    out = {
        **{k: str(r[k]) if r.get(k) is not None else None for k in
           ("id", "phap_nhan", "ma_noi_bo", "so_hop_dong", "loai", "loai_hinh", "ma_khach", "du_an", "du_an_ten", "lo_can")},
        "nguoi_phu_trach": list(r.get("nguoi_phu_trach") or []),
        "khach": r.get("khach") or r.get("khach_du_thao"), "khach_chua_co_ma": not bool(r.get("ma_khach")),
        "gia_tri_minor": None if r.get("gia_tri_minor") is None else str(r["gia_tri_minor"]), "tien_te": r["tien_te"],
        "ngay_ky": _ngay(r.get("ngay_ky")), "ngay_hieu_luc": _ngay(r.get("ngay_hieu_luc")),
        "phien_ban_hieu_luc": r.get("phien_ban_hieu_luc"), "trang_thai": tt,
        "trang_thai_tieng_viet": TRANG_THAI.get(tt, "Chưa xác định"),
        "nguon": {"ma": r.get("nguon"), "mau_phien_ban": r.get("mau_phien_ban"),
                  "nhan": f"Mẫu v{r['mau_phien_ban']}" if r.get("mau_phien_ban") else
                          "Trích bản ký" if r.get("nguon") in ("TRICH_6", "BAN_HANG") else
                          "Nhập tay" if r.get("nguon") == "TAY" else "Chưa xác định"},
        "thu_crm": {"nhan": "Tình hình thu theo CRM", "trang_thai": "CHUA_CO_LICH" if not lich else
                    "THIEU_CAN_CU" if thieu_tien_te else "CO_LICH", "theo_tien_te": ds_tien},
        "cong_no_junsky": {"nhan": "Công nợ ghi sổ Junsky", "trang_thai": "CO_SO" if junsky else "CHUA_CO_SO",
                           "hien_thi": "Có sổ" if junsky else "chưa có sổ", "grain": "KHACH_TK_NGAY_CURRENCY", "so_du": junsky},
        "dot_ke_tiep": None if dot is None else {"dot": dot["dot"], "han": _ngay(dot.get("han")), "moc": dot.get("moc"),
                                                   "han_du_kien": _ngay(dot.get("han_du_kien")),
                                                   "trang_thai": "CO_NGAY" if dot.get("han") else
                                                   "MOC_DU_KIEN" if dot.get("han_du_kien") else "MOC_CHUA_CO_NGAY"},
        "chenh_crm_junsky": {"trang_thai": "KHONG_SO_SANH", "ly_do": "Khác grain: CRM theo hợp đồng, Junsky theo khách/TK/ngày sổ/tiền tệ."},
        "co": sorted(set(co)), "viec": viec,
    }
    out.update(khong_quyen_xem_tien=not xem_tien,
               nhan_tien=None if xem_tien else "Không có quyền xem tiền")
    if not xem_tien:
        for k in ("gia_tri_minor", "thu_crm", "cong_no_junsky", "chenh_crm_junsky", "dot_ke_tiep"):
            out[k] = None
        out["viec"]["W5"] = None
    return out


def _tom_tat(r, ngay):
    """Dùng scalar rẻ cho lọc/thẻ, không đưa lịch, G5 hay sổ của toàn tập vào Python."""
    out = _dong(r, ngay)
    co = set(out["co"])
    if r.get("xem_tien") and (r.get("thieu_gia_tri") or r.get("thieu_lich")):
        co.add("THIEU_CAN_CU")
    if r.get("xem_tien") and r.get("qua_han"):
        co.add("QUA_HAN")
    if r.get("lech"):
        co.add("LECH_BAN_KY")
    out["co"] = sorted(co)
    out["viec"]["W4"] = int(bool(r.get("lech")))
    out["viec"]["W5"] = int(r.get("den_han") or 0) if r.get("xem_tien") else None
    return out


def _khop(r, loc):
    if "nguoi_phu_trach" in loc and loc["nguoi_phu_trach"] not in r["nguoi_phu_trach"]:
        return False
    for k in ("phap_nhan", "loai", "du_an", "trang_thai"):
        if k in loc and loc[k] != r.get(k):
            return False
    if "co" in loc:
        if r["khong_quyen_xem_tien"] and loc["co"] in ("QUA_HAN", "THIEU_CAN_CU"):
            return False
        if loc["co"] not in r["co"]:
            return False
    if "tim" in loc and loc["tim"].casefold() not in " ".join(str(r.get(k) or "") for k in
                                                              ("so_hop_dong", "ma_noi_bo", "khach", "lo_can")).casefold():
        return False
    for k in ("ngay_ky", "ngay_hieu_luc"):
        v = r.get(k)
        if (k + "_tu" in loc and (v is None or v < loc[k + "_tu"])) or (k + "_den" in loc and (v is None or v > loc[k + "_den"])):
            return False
    return True


class CrmDanhSachK2:
    def __init__(self, mau):
        self.mau = mau

    def danh_sach(self, dang_nhap: str, query: dict | None = None) -> dict:
        loc = bo_loc({} if query is None else query)
        m = self.mau
        dt, ngay = m.danh_tinh(dang_nhap), m.hom_nay()
        pns_tien = quyen.pham_vi(dt, "XEM_TIEN")
        with m._tx(dt, rr=True) as c:
            c.execute("SET TRANSACTION READ ONLY")
            rows = [_tom_tat(dict(r), ngay) for r in c.execute(*_sql(SQL, loc, pns_tien, ngay))]
            rows = [r for r in rows if _khop(r, loc)]
            xem_tien = any(not r["khong_quyen_xem_tien"] for r in rows) if rows else bool(pns_tien) or dt["vai_tro"] == "BAN_HANG"
            the = {w: {"so_luong": sum(r["viec"][w] or 0 for r in rows), "trang_thai": "CO_DU_LIEU",
                       "don_vi": "dot" if w == "W5" else "hop_dong"} for w in ("W1", "W2", "W3", "W4", "W5")}
            if "the" in loc:
                rows = [r for r in rows if (r["viec"][loc["the"]] or 0) > 0]
            tong = len(rows)
            dau = (loc["trang"] - 1) * loc["kich_thuoc_trang"]
            trang = rows[dau:dau + loc["kich_thuoc_trang"]]
            chi_tiet = {str(r["id"]): _dong(dict(r), ngay) for r in
                        c.execute(*_sql(SQL_TRANG, loc, pns_tien, ngay, [r["id"] for r in trang]))} if trang else {}
            # Cờ/thẻ và chi tiết cùng snapshot, cùng điều kiện quyền xem tiền.
            trang = [{**chi_tiet[r["id"]], "co": r["co"], "viec": r["viec"]} for r in trang]
        the["W2"].update(trang_thai="MOT_PHAN", ly_do="Chỉ đếm HĐ chờ ký; chưa có ngưỡng n nhắc ký và nguồn báo giá sắp hết hạn.")
        the["W5"].update(trang_thai="MOT_PHAN", tien_chua_ro=None, ly_do="Đếm đợt còn phải thu có ngày từ hôm nay đến 7 ngày tới; chưa có nguồn tiền chưa rõ/thu thừa thiếu.")
        if not xem_tien:
            the["W5"].update(so_luong=None, trang_thai="KHONG_CO_QUYEN", khong_quyen=True, nhan="Không có quyền xem tiền")
        return {"hop_dong": trang, "tong": tong, "trang": loc["trang"], "khong_quyen": not bool(quyen.pham_vi(dt, "XEM")),
                "khong_quyen_xem_tien": not xem_tien,
                "kich_thuoc_trang": loc["kich_thuoc_trang"], "the_so": the, "bo_loc": loc,
                "ngay_nghiep_vu": ngay.isoformat(), "thong_bao": None if tong else "Không có hợp đồng trong phạm vi của bạn"}
