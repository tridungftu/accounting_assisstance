**Biên bản review chéo G0–AD: KS-A — Cần sửa; KS-D — Cần sửa.** Các mẫu kiểm đều đúng; yêu cầu sửa xuất phát từ nội dung còn thiếu, không phải phát hiện sai mã nguồn.

Review chỉ đọc, không chạy dịch vụ/test/migration, không mở đường dẫn cấm. Không phát hiện DSN, khóa, dữ liệu thật hoặc tên đối tác trong hai tài liệu.

Quy ước: đường dẫn mã KS-A tính từ `src/kho_tri_thuc/`, trừ `tools/`. Các ký hiệu `M`, `S`, `O`, `H`, `X`, `V`, `T` dùng đúng bảng đường dẫn của KS-D. “—” nghĩa là mẫu không có phát hiện cần phân mức.

### KS-A

| Phát hiện / kết quả kiểm | Mức | Căn cứ tệp:dòng |
|---|---|---|
| **A01 Đúng:** shell dùng menu tĩnh. **A02 Đúng:** danh tính và quyền pháp nhân lấy từ DB. | — | `giao_dien/assets/index.html:18–29`; `k2/quyen.py:88–100` |
| **A03 Đúng:** khai báo module có phần, thẻ, engine, công tắc và vùng dữ liệu. **A04 Đúng:** migration có transaction/checksum. | — | `ha_tang/khai_bao_module.py:350–403`; `ha_tang/postgres.py:217–259` |
| **A05 Đúng:** ghi file chống ghi đè. **A06 Đúng:** engine kiểm kiểu và tạo bằng chứng hash đầu vào/đầu ra. | — | `ha_tang/store.py:26–46`; `ha_tang/engine.py:165–191` |
| **A07 Đúng:** `workflow.py` là dispatch action cố định. **A08 Đúng:** worker ghi rõ chưa nối server/tự khởi động. | — | `workflow.py:15–47`; `ha_tang/chay_engine.py:1–16` |
| **A09 Đúng:** restore yêu cầu thư mục đích chưa tồn tại. **A10 Đúng:** bus giao ít nhất một lần, không bảo đảm exactly-once cho tác động ngoài PG. | — | `ha_tang/backup.py:120–147`; `k2/sql_bus_su_kien.py:14–18` |
| **A11 Đúng:** component MTQ không tự gắn vào shell. **A12 Đúng:** host #6 dùng factory cổng ngẫu nhiên rồi báo cổng về. | — | `giao_dien/assets/ma_tran_tham_quyen.js:1–7`; `nguon/trich6_host.py:607–617` |
| **Sót đối chiếu bắt buộc:** chưa mô tả/dẫn trực tiếp `ha_tang/hang_viec.py`. Cần bổ sung wrapper tạo/nhận việc, lease, retry/dừng và trách nhiệm caller xác định danh tính, pháp nhân/module. | **Cần sửa** | `KS-A.md:24,28–42`; `GIAO-G0.md:38`; `ha_tang/hang_viec.py:1–5,21–76` |
| Đủ 12 khối Core, đủ 8 nhóm giao diện và có bảng vị trí cần tách trong `server.py`. Không phát hiện kết luận “đã có đầy đủ” quá tay. | — | `KS-A.md:15–26,50–57,67–78`; TL54 `:294–307` |

**Tỉ lệ đúng: 12/12 = 100% mẫu kiểm; Sai: 0; Lệch dòng: 0.**  
**Kết luận: Cần sửa**, bổ sung phần wrapper hàng việc theo phạm vi đề giao.

### KS-D

| Phát hiện / kết quả kiểm | Mức | Căn cứ tệp:dòng |
|---|---|---|
| **D01 Đúng:** Mask chọn 8017/8019. **D02 Đúng:** Studio khởi động cổng 8766. | — | `M/start_all.py:67–100`; `S/start.bat:10–12` |
| **D03 Đúng:** Studio POST kiểm CSRF và Host/Origin. **D04 Đúng:** OCR dùng Bearer, `/healthz` được miễn. | — | `S/server.py:234–239`; `O/mask_ocr/api.py:110–123,145–147` |
| **D05 Đúng:** OCR mặc định 8 job, 64 MiB, TTL kết quả 600 giây. **D06 Đúng:** Local AI mặc định tắt, timeout 8 giây. | — | `O/mask_ocr/jobs.py:73–79`; `tri_thuc/ai_cuc_bo.py:26` |
| **D07 Đúng:** #7 nguồn có GET SSE `/api/events`. **D08 Đúng:** client M2 dùng POST cùng đường dẫn; nhận định lệch protocol có căn cứ. | — | `H/src/server.js:64–84`; `m2/tai_hoa_don/khach.py:150–156` |
| **D09 Đúng:** parser XML giới hạn 16 MiB/XML, 64 MiB/ZIP, 1.000 entry. **D10 Đúng:** common nguồn #6 chỉ nhận `RULE_ONLY`. | — | `nguon/hoa_don_xml.py:61–63`; `X/may_chu/dich_vu.py:1047,1060–1061` |
| **D11 Đúng:** khoản vay kiểm phòng/PIN và scope công ty. **D12 Đúng:** M4 được chọn làm module mẫu đầu tiên. | — | `V/apps-script-deploy/Code.js:160–184`; `T/55-ke-hoach-chuan-hoa-core-va-dung-lai-module-engine.md:61` |
| **Hồ sơ E1-MUA chưa đủ:** được ghép chung với #6/AnDanh nhưng chưa xác định rõ nguồn, entry point, API, lưu trữ và giới hạn riêng, hoặc chứng minh dùng chung hoàn toàn với #6. Cần bổ sung; phần chưa xác định ghi “không thấy/chờ Anh”. | **Cần sửa** | `KS-D.md:29–38,61–62,72`; `GIAO-G0.md`, mục KS-D “Với mỗi công cụ” và danh sách E1-MUA |
| **Thiếu kết luận readiness của #7 nguồn:** cần ghi rõ không thấy endpoint health/readiness chuyên dụng; `/api/config` chỉ phản ánh cấu hình và `running`, chưa chứng minh sẵn sàng tải. Không dùng readiness của bản vá M2 thay cho nguồn. | **Cần sửa** | `KS-D.md:58–59`; `H/src/server.js:25–37,109`; `m2/tai_hoa_don/khach.py:94–98` |
| Đường dẫn #7 đã tìm được nhưng thiếu dẫn nguồn tài liệu xác định vị trí theo yêu cầu TL31/`CLAUDE.md` thư mục cha. Bổ sung nguồn hoặc nói rõ vị trí được xác minh bằng cách nào. | **Gợi ý** | `KS-D.md:20,36`; `GIAO-G0.md`, mục KS-D “Bộ tải hóa đơn điện tử” |

**Tỉ lệ đúng: 12/12 = 100% mẫu kiểm; Sai: 0; Lệch dòng: 0.**  
**Kết luận: Cần sửa**, hoàn thiện hồ sơ E1-MUA và readiness của #7 nguồn. Không có phát hiện mức **Chặn**.

*Tỉ lệ trên chỉ áp dụng cho 12 khẳng định được chọn ở mỗi tài liệu, không đại diện cho toàn bộ khẳng định trong tài liệu.*