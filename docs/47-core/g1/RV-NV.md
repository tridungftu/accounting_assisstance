**BIÊN BẢN REVIEW CHÉO CONTRACT NGHIỆP VỤ — 30/10/2026**

**Kết luận: Cần sửa.** Có 5 phát hiện **Cần sửa**, 2 **Gợi ý**; không phát hiện dữ liệu thật trong các ví dụ đã kiểm. Không lặp các điểm Opus đã nêu.

Phạm vi: 12 contract dữ liệu và 5 sự kiện được giao. Chỉ đọc tài liệu/mã nguồn; không sửa tệp, không chạy ứng dụng, không đọc `var\`, kho thật, tệp bí mật hoặc `*.local.json`.

Quy ước: `NV` = `docs/47-core/g1/CONTRACT-NGHIEP-VU.md`; các ký hiệu nguồn `P`, `M17`, `CB`… giữ nguyên theo tài liệu.

**Bảng phát hiện**

| # | Phát hiện và hướng xử lý | Mức | Căn cứ |
|---|---|---|---|
| 1 | **`phu_luc.huy_boi_id` chưa có căn cứ ánh xạ UUID.** Contract khai `id`, nhưng nguồn lưu `huy_boi text`; thao tác hủy ghi giá trị `ai` vào cột này. Cần giữ đúng kiểu/ý nghĩa nguồn hoặc dẫn thiết kế đã chốt cho phép ánh xạ sang UUID người dùng; không mặc nhiên coi text là UUID. | **Cần sửa** | NV:1140; `m4/sql_m17.py:377,681`. |
| 2 | **Ví dụ dùng `null` trái kiểu đã khai.** Ba trường `huy_ly_do`, `huy_boi_id`, `huy_luc` của phụ lục chỉ được khai tùy chọn, chưa cho nullable; `ket_qua_kiem_dot.phu_luc_id` cũng vậy. Tùy chọn không đồng nghĩa nhận `null`. Cần sửa bảng kiểu hoặc bỏ khóa không áp dụng khỏi ví dụ. | **Cần sửa** | NV:1140 so với 1164–1166; NV:1314 so với 1340; quy ước nullable tại NV:1054. |
| 3 | **`ket_qua_kiem_dot` bắt buộc hợp đồng cho cả kiểm K độc lập.** Trường chung `hop_dong_id` bắt buộc trong sáu contract M4, trong khi nguồn cho phép review L1 không gắn hợp đồng. Như vậy kết quả K hợp lệ hiện có không biểu diễn được. Cần đặt điều kiện bắt buộc theo nhóm/chế độ kiểm. | **Cần sửa** | NV:1050,1308; `m4/sql_review.py:48,73–74`. |
| 4 | **Hai sự kiện chưa đủ định nghĩa để hoàn tất contract.** `ban_giao_da_duyet` chưa chốt chủ phát/bên nhận và định danh quyết định duyệt; `moc_da_xay_ra` chỉ mang `moc_id`, không xác định được lần lịch sử đã phát. Bản nháp đã nhận diện đúng và chặn kích hoạt; cần giữ các mục này là điểm chờ Anh, chưa đánh dấu hoàn tất. Không tự nhét số `lan` vào payload bus. | **Cần sửa** | NV:320–350,363–380; `k2/sql_crm_du_an_moc.py:29–43`; `ha_tang/bus_su_kien.py:35–38`. |
| 5 | **Thiếu đường đọc quan sát hóa đơn chính xác khi nhận sự kiện muộn.** Sự kiện yêu cầu đọc đúng `quan_sat_id/phien_ban_id`, nhưng contract công bố M2 lại theo `latest_observation_id`. Khi có quan sát mới trước lúc consumer xử lý, M0064 không trả bản đã phát. Cần mô tả phép đọc công bố theo tham chiếu chính xác, có kiểm quyền; không cho consumer đọc bảng riêng hoặc thay bằng latest. | **Cần sửa** | NV:425–446,1530; `k2/sql_cong_bo_hoa_don.py:57–63`; `DAC-TA-CSDL.md:363–366`. |
| 6 | **Quan hệ với contract M0064 cần rõ hơn theo CD-032.** `hoa_don_mua_vao.v1` dùng lại nhiều trường cùng nghĩa của `m2-hoa-don-cong-bo/v1`, nhưng chưa xác định rõ quan hệ mở rộng/chuyển đổi và phục vụ consumer cũ. Nên ghi ánh xạ và vòng đời hai mã, tránh hình thành hai định nghĩa độc lập cho cùng phần dữ liệu. Đây là điểm cần làm rõ, chưa đủ căn cứ kết luận toàn bộ hai contract trùng nghĩa. | **Gợi ý** | NV:1489–1538; `k2/sql_cong_bo_hoa_don.py:30,38–68`; CD-032 mục 3. |
| 7 | **Một số số dòng nguồn M2 dẫn sai.** `phien_ban_nguon` dẫn P:5264 nhưng cột ở 5260; `lan_tiep_nhan_id` dẫn P:5294 nhưng cột ở 5299; `trang_thai_can_cu_tien` dẫn P:5278 nhưng cột ở 5277. Các trường có thật, cần chỉnh tọa độ dẫn nguồn. | **Gợi ý** | NV:1500,1504,1513; `ha_tang/pg_migrations.py` tại các dòng tương ứng. |

**Kiểm mẫu nguồn: 20 trường**

| Contract và trường đã đối chiếu | Nguồn thực kiểm | Kết quả |
|---|---|---|
| `doi_tuong`: `ma_junsky`, `ten_phap_ly`; `du_an`: `ma_junsky`, `trang_thai` | P:109,90,151,155 | 4/4 |
| `tep_nhap_junsky`: `tong_no`, `sheet[].so_cot`; `bao_gia`: `nguon_lich`, `het_han` | P:646–648; `xuat/shadow.py:20–21`; GK:323,335 | 4/4 |
| `du_an_dang_ban`: `dang_ban`, `phi[].muc`; `hop_dong_thau`: `rev_tham_so`, `xac_nhan_tham_so_id` | SQL-DA:100; DA:155–157; M17:282,348–364 | 4/4 |
| `phu_luc`: `doi_boq`, `huy_boi_id`; `boq`: `dong[].thao_tac`; `ket_qua_kiem_dot`: `can_cu_sha256` | M17:373,377; `m4/sql_boq_bo.py:21`; REVIEW:54–55 | 3/4; sai ánh xạ tại #1 |
| `nghiem_thu`: `co_so_gia_tri`; `hoa_don_mua_vao`: `hoa_don_id`, `ma_bam_noi_dung`; `cong_no_phai_tra`: `so_tien_con_lai` | KT:32; CB:39,41; thiết kế M2 §4 | 4/4; trường công nợ đúng ở mức đề xuất, đã ghi “chờ Anh” |

**Tỉ lệ đúng của mẫu nguồn: 19/20 = 95%** về nghĩa/kiểu và trạng thái phê duyệt; không suy rộng thành tỉ lệ đúng toàn tài liệu.

**Các kiểm tra còn lại**

- **JSON:** 17/17 ví dụ trong phạm vi parse được. Đây là kiểm cú pháp, chưa phải chứng nhận schema; lỗi nullable ở #2 vẫn tồn tại.
- **Số học:** báo giá có tổng đợt **1.100.000.000**, VAT **100.000.000**, tỷ lệ **100%**; phụ lục giảm **11.000.000** từ **1.100.000.000** còn **1.089.000.000**; lô Junsky Nợ = Có **1.000.000**. Các số khớp.
- **Tiền và DEMO:** các giá trị tiền đã kiểm dùng chuỗi decimal và `don_vi_tien` phù hợp `chung.v1`; phần nhập tiền của lịch dùng biến thể `gia_tri`. Không phát hiện dữ liệu thật trong 17 ví dụ.
- **Sự kiện:** 5/5 payload hợp dạng tham chiếu UUID của bus; quy ước transaction, ACK và dedupe phù hợp mã hiện có. Bốn sự kiện nêu cụ thể module phát/nhận dự kiến; riêng bàn giao còn để ngỏ. Các thời điểm phát và khóa dự kiến đều được mô tả.
- **M2 và dùng chung:** các trường nghiệp vụ chỉ dựa trên bản 20/10 đã được ghi **“chờ Anh”**. CRM/M4/M2 dùng tham chiếu `doi_tuong`, `du_an`. `phien_ban` số nguyên của bus và semver của dữ liệu đã được phân biệt rõ, không phải lỗi kiểu.

**Kết luận cuối: Cần sửa trước khi trình duyệt hoàn tất; tiếp tục giữ các mục chờ Anh và chặn kích hoạt đã ghi trong bản nháp.**