**Trả lời lead (Claude) cho MTQ-4b2b — làm theo, không hỏi lại (26/10 ~22:40):**

Biểu diễn phạm vi hẹp B3 trong `master.mtq_pham_vi.quan_he` cho các khóa `CRM:G3_G4_SOAN_KY:*` và `CRM:BAN_KY:XEM`. Bám đúng những gì `master.crm_ky_pham_vi` cũ đã ràng buộc: PN, HĐ, bản soạn, dự án, khách (`doi_tac_id`), mã băm khách dự thảo.

1. **Phạm vi `HOP_DONG`** (khóa = `hop_dong_id`): `quan_he` = `{"soan_id", "du_an_id", "doi_tac_id", "khach_du_thao_sha256"}`. Chỉ một trong hai trường khách có giá trị.
2. **Phạm vi `DU_AN`** (khóa = `du_an_id`): `quan_he` = `{"doi_tac_id"}` hoặc `{"khach_du_thao_sha256"}` (bắt buộc một). Phạm vi dự án luôn kèm đúng một khách.
3. **Máy chủ tự ghim, không tin dữ liệu Admin gõ:**
   - khi Admin cấp hai loại phạm vi trên cho các khóa CRM ký/bản ký, máy chủ đọc từ CSDL bản soạn hiện hành của HĐ, dự án, khách/mã băm khách dự thảo rồi ghi `quan_he`;
   - Admin gửi `quan_he` khác rỗng mà không khớp → từ chối có mã.
   - Làm bằng `CREATE OR REPLACE` hàm validator cấp phạm vi trong migration mới, **dựa trên thân hiện hành mới nhất** (đã có nhánh NGUON của M0049) — giữ nguyên các nhánh khác.
   - Không đổi bảng `mtq_pham_vi`, không thêm loại phạm vi mới.
4. **Khi kiểm (guard G4 ký, đọc metadata, tải bản ký):** chọn phạm vi khớp theo thứ tự hiện có. Với phạm vi HOP_DONG/DU_AN của các khóa trên, đối tượng S/K phải khớp **đúng** `quan_he` đã ghim. Lệch (bản soạn thay, khách đổi, mã băm khác) → chặn `MTQ_PHAM_VI_LECH`; Admin phải cấp lại.
   - Không suy rộng ra cả PN, không giữ assignment cũ làm nguồn quyền thứ hai khi PN bật.
   - Phiên bản: digest đúng revision ở bước ký vẫn do guard G4 hiện có kiểm, giữ nguyên.
5. Không chuyển dữ liệu `crm_ky_pham_vi` cũ sang MTQ ở lát này (B11: PN chỉ bật khi Admin đã cấp lại đủ).
6. Phần sửa thông báo từ chối (không lộ khóa) giữ như đề.

Tệp vẫn 3: `k2/sql_mtq_crm.py` (`MTQ_CRM_C_SQL`), `ha_tang/pg_migrations.py` (`M00xx_MTQ_CRM_C`), `tests/test_mtq_crm_sql.py`. **Ghi tệp bằng apply_patch, không qua chuỗi PowerShell nháy kép.**
