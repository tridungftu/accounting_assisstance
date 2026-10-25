"""BG-1c — CRM · Báo giá: bước kiểm khi Ký tính lịch theo CÙNG công thức VND với máy chủ (QD-20261025-02). CHỈ hằng SQL, export `CRM_BG1C_SQL`.

KHÔNG import/đăng ký/apply, KHÔNG đoán ordinal: integration owner append vào registry SAU mọi migration đã cấp (sau M0029). Không sửa M0025
(`k2/sql_crm_kiem_hd.py`): chỉ `CREATE OR REPLACE FUNCTION master.crm_kiem_lich_ky(uuid)` — cùng chữ ký, cùng kiểu trả, cùng hình dạng jsonb trả
về (tien_te, scale, tong_minor, tong_dong_minor, dong[], loi[], canh_bao[]); quyền/chủ sở hữu hàm giữ nguyên (CREATE OR REPLACE). Trigger/hàm
gọi nó (crm_kiem_hieu_luc_kiem, crm_kiem_hd_kich_hoat, crm_kiem_g7, crm_kiem_dieu_kien, kích hoạt) không đổi — plpgsql gọi theo tên lúc chạy.

Thay đổi so với thân M0025 (mọi kiểm khác GIỮ NGUYÊN — QD-20261024-02: ghi đè tổng / % không tròn vẫn chặn ở Ký):
  1. Dữ liệu báo giá v2 (`tien_chinh = 'VND'`, do máy chủ BG-1c đặt): tiền chính = VND cho tổng/lịch; tích = round(đơn giá × tỷ giá × diện tích, 0)
     — làm tròn đến đồng, đúng nửa làm tròn lên (số ≥ 0; trùng `lam_tron_nua_len` của `k2/crm_giao_ket.py`). Tỷ giá: báo giá VND = 1 (khác 1 →
     VND_TY_GIA_KHAC_1); báo giá USD = fx.ty_gia đã LƯU trong báo giá (thiếu/không dương → USD_THIEU_FX).
     Dữ liệu cũ (không `tien_chinh`): y nguyên M0025 (tiền chính = tiền tệ báo giá, đơn giá × diện tích chính xác, không làm tròn).
  2. Ghi đè tổng `tong_gia_tri_ghi_de` (chuỗi số kiểu Việt của BG-1a, đã được In/Chuyển chấp nhận) được ĐỌC làm tổng (ưu tiên trước `gia.tong`,
     như máy chủ): khác tích → TONG_LECH_DON_GIA_X_DIEN_TICH (chặn Ký, đúng QD-20261024-02); sai dạng → TONG_GIA_TRI_GHI_DE_SAI, không rơi về
     tổng khác. M0025 chưa đọc khóa này nên tổng ghi đè + lịch % đi qua Ký với tổng = tích.
"""

_RE_SO = "'^[0-9]{1,24}(\\.[0-9]{1,12})?$'"
_RE_SO_VN = "'^([0-9]+|[0-9]{1,3}(\\.[0-9]{3})+)(,[0-9]{1,12})?$'"

CRM_BG1C_SQL = (
    """CREATE OR REPLACE FUNCTION master.crm_kiem_lich_ky(p_ky uuid) RETURNS jsonb
        LANGUAGE plpgsql STABLE SET search_path = master, pg_temp AS $$
        DECLARE v_bg jsonb; v_tt text; v_sc integer; v_m numeric; v_tong numeric; v_tich numeric; v_e jsonb; v_i integer := 0; v_tl numeric; v_n numeric;
                v_mi numeric; v_dl text[]; v_dong jsonb := '[]'::jsonb; v_loi jsonb := '[]'::jsonb; v_cb jsonb := '[]'::jsonb;
                v_pct numeric := 0; v_amt numeric := 0; v_tien numeric := 0; v_du boolean := true; v_moc text; v_han date; v_tl_suy text;
                v_max constant numeric := 9223372036854775807;
                v_moi boolean; v_tt_gia text; v_fx numeric; v_fx_s text; v_gd jsonb; v_gd_s text; v_gd_sai boolean := false;
        BEGIN
            SELECT r.du_lieu -> 'bao_gia' INTO v_bg FROM master.crm_hd_ky k JOIN master.crm_hd_soan_rev r ON r.id = k.soan_rev_id WHERE k.id = p_ky;
            v_tt_gia := v_bg -> 'gia' ->> 'tien_te';
            -- BG-1c: báo giá v2 → tiền chính VND; dữ liệu cũ → tiền chính = tiền tệ báo giá (như M0025)
            v_moi := coalesce(v_bg ->> 'tien_chinh', '') = 'VND' AND coalesce(v_tt_gia IN ('VND', 'USD'), false);
            v_tt := CASE WHEN v_moi THEN 'VND' ELSE v_tt_gia END;
            v_sc := CASE v_tt WHEN 'VND' THEN 0 WHEN 'USD' THEN 2 END;
            IF v_sc IS NULL THEN
                RETURN jsonb_build_object('tien_te', v_tt, 'scale', NULL, 'tong_minor', NULL, 'tong_dong_minor', NULL, 'dong', '[]'::jsonb,
                                          'loi', jsonb_build_array(jsonb_build_object('ma', 'THIEU_TIEN_TE')), 'canh_bao', '[]'::jsonb);
            END IF;
            v_m := CASE v_sc WHEN 0 THEN 1 ELSE 100 END;
            -- BG-1c: tỷ giá đã lưu trong báo giá (v2): VND = 1; USD = fx.ty_gia dương
            IF v_moi THEN
                v_fx_s := CASE WHEN jsonb_typeof(v_bg -> 'fx' -> 'ty_gia') = 'string' THEN v_bg -> 'fx' ->> 'ty_gia' END;
                IF v_tt_gia = 'VND' THEN
                    v_fx := 1;
                    IF jsonb_typeof(v_bg -> 'fx' -> 'ty_gia') IS NOT NULL AND jsonb_typeof(v_bg -> 'fx' -> 'ty_gia') <> 'null' THEN
                        IF v_fx_s IS NULL OR v_fx_s !~ """ + _RE_SO + """ THEN
                            v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'VND_TY_GIA_KHAC_1'));
                        ELSIF v_fx_s::numeric <> 1 THEN
                            v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'VND_TY_GIA_KHAC_1'));
                        END IF;
                    END IF;
                ELSE
                    IF v_fx_s IS NOT NULL AND v_fx_s ~ """ + _RE_SO + """ THEN
                        v_fx := v_fx_s::numeric;
                    END IF;
                    IF v_fx IS NULL OR v_fx <= 0 THEN
                        v_fx := NULL;
                        v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'USD_THIEU_FX'));
                    END IF;
                END IF;
            END IF;
            -- BG-1c: ghi đè tổng (chuỗi kiểu Việt, như máy chủ) được ưu tiên trước gia.tong; rỗng = không ghi đè; sai dạng → lỗi, không rơi về tổng khác
            v_gd := v_bg -> 'tong_gia_tri_ghi_de';
            IF v_gd IS NOT NULL AND jsonb_typeof(v_gd) <> 'null' THEN
                IF jsonb_typeof(v_gd) <> 'string' THEN
                    v_gd_sai := true;
                ELSE
                    v_gd_s := btrim(v_gd #>> '{}', ' ');
                    IF v_gd_s = '' THEN
                        v_gd_s := NULL;
                    ELSIF v_gd_s !~ """ + _RE_SO_VN + """ THEN
                        v_gd_sai := true;
                        v_gd_s := NULL;
                    ELSE
                        v_gd_s := replace(replace(v_gd_s, '.', ''), ',', '.');
                        IF v_gd_s !~ """ + _RE_SO + """ THEN
                            v_gd_sai := true;
                            v_gd_s := NULL;
                        END IF;
                    END IF;
                END IF;
                IF v_gd_sai THEN
                    v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_GIA_TRI_GHI_DE_SAI'));
                END IF;
            END IF;
            IF v_gd_s IS NOT NULL THEN
                v_tong := v_gd_s::numeric * v_m;
                IF v_tong <> trunc(v_tong) THEN
                    v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_KHONG_DUNG_SCALE'));
                    v_tong := NULL;
                END IF;
            ELSIF NOT v_gd_sai AND coalesce((v_bg -> 'gia' ->> 'tong') ~ """ + _RE_SO + """, false) THEN
                v_tong := (v_bg -> 'gia' ->> 'tong')::numeric * v_m;
                IF v_tong <> trunc(v_tong) THEN
                    v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_KHONG_DUNG_SCALE'));
                    v_tong := NULL;
                END IF;
            END IF;
            IF coalesce((v_bg -> 'gia' ->> 'don_gia') ~ """ + _RE_SO + """ AND (v_bg -> 'gia' ->> 'dien_tich') ~ """ + _RE_SO + """, false) THEN
                IF v_moi THEN
                    IF v_fx IS NOT NULL THEN
                        -- Tổng VND = đơn giá × tỷ giá × diện tích, làm tròn đến đồng (nửa lên; numeric chính xác, số ≥ 0)
                        v_tich := round((v_bg -> 'gia' ->> 'don_gia')::numeric * v_fx * (v_bg -> 'gia' ->> 'dien_tich')::numeric, 0);
                    END IF;
                ELSE
                    v_tich := (v_bg -> 'gia' ->> 'don_gia')::numeric * (v_bg -> 'gia' ->> 'dien_tich')::numeric * v_m;
                    IF v_tich <> trunc(v_tich) THEN
                        v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'DON_GIA_X_DIEN_TICH_KHONG_DUNG_SCALE'));
                        v_tich := NULL;
                    END IF;
                END IF;
            END IF;
            IF v_tong IS NULL AND v_tich IS NOT NULL AND NOT v_gd_sai THEN
                v_tong := v_tich;
            ELSIF v_tong IS NOT NULL AND v_tich IS NOT NULL AND v_tong <> v_tich THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_LECH_DON_GIA_X_DIEN_TICH'));
            END IF;
            IF v_tong IS NULL THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'THIEU_TONG_GIA_TRI'));
            ELSIF v_tong <= 0 OR v_tong > v_max THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_NGOAI_MIEN'));
                v_tong := NULL;
            END IF;
            FOR v_e IN SELECT x FROM jsonb_array_elements(CASE WHEN jsonb_typeof(v_bg -> 'lich') = 'array' THEN v_bg -> 'lich' ELSE '[]'::jsonb END) x LOOP
                v_i := v_i + 1;
                v_dl := '{}';
                v_mi := NULL;
                v_tl := NULL;
                v_tl_suy := NULL;
                IF v_e ->> 'loai' = 'PERCENT' THEN
                    IF NOT coalesce((v_e ->> 'ty_le') ~ """ + _RE_SO + """, false) THEN
                        v_dl := v_dl || 'CHUA_CO_TY_LE'::text;
                    ELSE
                        v_tl := (v_e ->> 'ty_le')::numeric;
                        v_pct := v_pct + v_tl;
                        IF v_tong IS NULL THEN
                            v_dl := v_dl || 'CHUA_CO_TONG'::text;
                        ELSE
                            v_n := v_tong * v_tl;
                            IF v_n <> trunc(v_n) OR mod(v_n, 100) <> 0 THEN
                                v_dl := v_dl || 'KHONG_BIEU_DIEN_DUNG_SCALE'::text;
                            ELSE
                                v_mi := v_n / 100;
                            END IF;
                        END IF;
                    END IF;
                ELSIF v_e ->> 'loai' = 'AMOUNT' THEN
                    IF (v_e ->> 'tien_te') IS NOT NULL AND (v_e ->> 'tien_te') <> v_tt THEN
                        v_dl := v_dl || 'KHAC_TIEN_TE'::text;
                    END IF;
                    IF (v_e ->> 'so_tien') IS NULL THEN
                        v_dl := v_dl || 'CHUA_CO_SO_TIEN'::text;
                    ELSIF NOT ((v_e ->> 'so_tien') ~ """ + _RE_SO + """) OR (v_e ->> 'so_tien')::numeric * v_m <> trunc((v_e ->> 'so_tien')::numeric * v_m) THEN
                        v_dl := v_dl || 'KHONG_DUNG_SCALE_TIEN_TE'::text;
                    ELSE
                        v_mi := (v_e ->> 'so_tien')::numeric * v_m;
                        v_amt := v_amt + v_mi;
                        IF coalesce(v_tong, 0) > 0 THEN
                            IF mod(v_mi * 100 * 1000000000000, v_tong) <> 0 THEN
                                v_dl := v_dl || 'TY_LE_SUY_RA_KHONG_HUU_HAN'::text;
                            ELSE
                                v_tl_suy := trim_scale(v_mi * 100 / v_tong)::text;
                            END IF;
                        ELSE
                            v_dl := v_dl || 'CHUA_CO_TONG'::text;
                        END IF;
                    END IF;
                ELSE
                    v_dl := v_dl || 'CHUA_CO_GIA_TRI'::text;
                END IF;
                IF v_mi IS NOT NULL AND (v_mi <= 0 OR v_mi > v_max) THEN
                    v_dl := v_dl || 'SO_TIEN_KHONG_DUONG'::text;
                END IF;
                IF v_mi IS NOT NULL THEN
                    v_tien := v_tien + v_mi;
                END IF;
                v_moc := CASE WHEN v_e ->> 'moc_loai' = 'NGAY' AND (v_e ->> 'moc_ngay') IS NOT NULL THEN 'NGAY:' || (v_e ->> 'moc_ngay')
                              WHEN v_e ->> 'moc_loai' = 'SU_KIEN' AND (v_e ->> 'moc_su_kien') IS NOT NULL THEN 'SU_KIEN:' || (v_e ->> 'moc_su_kien') END;
                v_han := CASE WHEN v_e ->> 'moc_loai' = 'NGAY' AND coalesce((v_e ->> 'moc_ngay') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$', false)
                              THEN (v_e ->> 'moc_ngay')::date END;
                IF v_moc IS NULL THEN
                    v_cb := v_cb || jsonb_build_array(jsonb_build_object('ma', 'MOC_TRONG', 'dong', v_i));
                END IF;
                IF cardinality(v_dl) > 0 THEN
                    v_du := false;
                END IF;
                v_dong := v_dong || jsonb_build_array(jsonb_build_object(
                    'dot', v_i, 'lan', left(coalesce(v_e ->> 'lan', v_i::text), 40), 'loai', v_e ->> 'loai',
                    'ty_le', CASE WHEN v_e ->> 'loai' = 'PERCENT' AND v_tl IS NOT NULL THEN trim_scale(v_tl)::text END, 'ty_le_suy_ra', v_tl_suy,
                    'so_tien_minor', CASE WHEN cardinality(v_dl) = 0 THEN v_mi::bigint::text END, 'moc', v_moc, 'han', v_han, 'loi', to_jsonb(v_dl)));
            END LOOP;
            IF v_i = 0 THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'THIEU_LICH'));
            ELSIF NOT v_du THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'LICH_CHUA_TINH_DUOC'));
            ELSIF v_tong IS NOT NULL AND v_pct * v_tong + 100 * v_amt <> 100 * v_tong THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_TY_LE_KHAC_100'));
            ELSIF v_tong IS NOT NULL AND v_tien <> v_tong THEN
                v_loi := v_loi || jsonb_build_array(jsonb_build_object('ma', 'TONG_TIEN_LECH'));
            END IF;
            RETURN jsonb_build_object('tien_te', v_tt, 'scale', v_sc, 'tong_minor', v_tong::bigint::text,
                                      'tong_dong_minor', CASE WHEN v_tien <= v_max THEN v_tien::bigint::text END,
                                      'dong', v_dong, 'loi', v_loi, 'canh_bao', v_cb);
        END $$""",
)
