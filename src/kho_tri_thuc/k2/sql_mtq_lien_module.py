"""MTQ-4i-a: cấp/thu hồi NGUON qua cấu hình Admin và audit MTQ hiện có.

Khóa: LOAI|nguon_profile.id hoặc nguon_instance.source_instance_id|company/kho,
chữ hoa, trim từng phần và gộp whitespace thừa. Instance phải giải duy nhất một
profile; nếu mơ hồ Admin phải dùng UUID profile. Ánh xạ dùng chính bảng định
tuyến master.anh_xa_nguon (M2 COMPANY, M5 WAREHOUSE), ghim đủ instance/ref/SHA.
L11_EVIDENCE_SET đã typed PN, không cấp bằng NGUON.

Validator chỉ kiểm MỘT dòng phạm vi. Nguồn gộp nhiều PN cần từng dòng riêng;
caller MTQ-4i-c chịu trách nhiệm kiểm đủ MỌI PN trước đọc/ghi/replay/bytes và
kiểm lại mapping hiện hành khi sử dụng. Không nối caller hoặc bật readiness ở đây.
Thu hồi vẫn được khi mapping/instance đã hết hiệu lực hoặc gán vai đã thu hồi.
"""

from .sql_ma_tran_tham_quyen import MA_TRAN_THAM_QUYEN_SQL


_NGUON_CU = """                ELSE
                    -- NGUON cần instance/profile SHA/công ty nguồn được resolver
                    -- MTQ-4i xác minh; tuyệt đối không kế thừa capability cũ.
                    RAISE EXCEPTION 'MTQ_CAN_RESOLVER_MTQ4: phạm vi nguồn chưa được hỗ trợ';
                END IF;"""

_NGUON_MOI = """                ELSIF NEW.loai = 'NGUON' THEN
                    -- UPDATE chỉ thu hồi: guard bất biến/revision/Admin ở trên
                    -- vẫn áp dụng, không phụ thuộc mapping còn tồn tại hay không.
                    IF TG_OP = 'INSERT' THEN
                        DECLARE
                            parts text[]; pr record; mp record; n integer := 0;
                            inst text; ref text; sha text; kind text;
                        BEGIN
                            parts := string_to_array(NEW.khoa, '|');
                            IF cardinality(parts) <> 3 THEN
                                RAISE EXCEPTION 'MTQ_NGUON_KHOA: cần LOAI|profile hoặc instance|company hoặc kho';
                            END IF;
                            FOR n IN 1..3 LOOP
                                parts[n] := upper(btrim(regexp_replace(parts[n], '[[:space:]]+', ' ', 'g')));
                                IF parts[n] = '' THEN
                                    RAISE EXCEPTION 'MTQ_NGUON_KHOA: không để trống thành phần khóa';
                                END IF;
                            END LOOP;
                            kind := CASE parts[1] WHEN 'INVOICE_SET' THEN 'COMPANY'
                                WHEN 'KHO10_PHIEU' THEN 'WAREHOUSE' END;
                            IF kind IS NULL THEN
                                RAISE EXCEPTION 'MTQ_NGUON_LOAI: chỉ INVOICE_SET hoặc KHO10_PHIEU; L11 dùng phạm vi PN';
                            END IF;
                            IF g.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id OR NOT EXISTS (
                                SELECT 1 FROM master.mtq_phong p WHERE p.id = g.phong_id
                                    AND p.phap_nhan_id = NEW.phap_nhan_id) THEN
                                RAISE EXCEPTION 'MTQ_PHAM_VI: phòng/gán vai khác pháp nhân';
                            END IF;
                            -- Không chọn profile theo PN đích, không chọn dòng đầu.
                            n := 0;
                            FOR pr IN SELECT p.* FROM master.nguon_profile p
                                JOIN master.nguon_instance i ON i.source_instance_id = p.source_instance_id
                                WHERE (upper(p.id::text) = parts[2] OR upper(p.source_instance_id) = parts[2])
                                    AND i.trang_thai = 'HOAT_DONG'
                                ORDER BY p.id FOR SHARE OF p, i
                            LOOP
                                n := n + 1;
                                inst := pr.source_instance_id; ref := pr.profile_ref; sha := pr.profile_sha256;
                            END LOOP;
                            IF n <> 1 THEN
                                RAISE EXCEPTION 'MTQ_NGUON_PROFILE: cần đúng một profile của instance hoạt động';
                            END IF;
                            n := 0;
                            FOR mp IN SELECT m.* FROM master.anh_xa_nguon m
                                WHERE m.source_instance_id = inst AND m.profile_ref = ref AND m.profile_sha256 = sha
                                    AND m.subject_kind = kind
                                    AND upper(btrim(regexp_replace(m.subject_key, '[[:space:]]+', ' ', 'g'))) = parts[3]
                                    AND m.state = 'DA_DUYET' AND m.valid_from <= now()
                                    AND (m.valid_to IS NULL OR m.valid_to > now())
                                ORDER BY m.id FOR SHARE OF m
                            LOOP
                                n := n + 1;
                                IF mp.phap_nhan_id IS DISTINCT FROM NEW.phap_nhan_id THEN
                                    RAISE EXCEPTION 'MTQ_NGUON_ANH_XA: nguồn ánh xạ sang pháp nhân khác';
                                END IF;
                            END LOOP;
                            IF n <> 1 THEN
                                RAISE EXCEPTION 'MTQ_NGUON_ANH_XA: cần đúng một ánh xạ định tuyến hiện hành';
                            END IF;
                            NEW.khoa := array_to_string(parts, '|');
                        END;
                    END IF;
                ELSE
                    RAISE EXCEPTION 'MTQ_CAN_RESOLVER_MTQ4: phạm vi chưa được hỗ trợ';
                END IF;"""


def _validator_nguon() -> str:
    """Chỉ thay nhánh NGUON M0039; giữ nguyên guard khác, chữ ký và ACL."""
    ds = [s for s in MA_TRAN_THAM_QUYEN_SQL
          if s.startswith("CREATE FUNCTION master.mtq_kiem_ghi(")]
    if len(ds) != 1 or ds[0].count(_NGUON_CU) != 1:
        raise RuntimeError("MTQ-4i-a: không định vị duy nhất nhánh validator NGUON M0039")
    return ds[0].replace("CREATE FUNCTION ", "CREATE OR REPLACE FUNCTION ", 1).replace(
        _NGUON_CU, _NGUON_MOI, 1)


# CREATE OR REPLACE giữ OID/owner/ACL, trigger kiểm ghi và audit M0039 giữ nguyên.
MTQ_LMOD_A_SQL = (_validator_nguon(),)
