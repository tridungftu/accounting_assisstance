# M4-KK — Kiểm kê chép Review hồ sơ xây dựng vào M4

Ngày kiểm: 26/10/2026 · nhánh `lat/m4-kk` · căn cứ CD-011, việc 1. **Chỉ đọc mã; chỉ ghi tài liệu này; không commit.**

## 1. Kết luận và phạm vi

**Có sẵn phần lớn mã gốc, nhưng chưa có đủ 8 màn hoạt động như bản gốc trong khung icon M4.** Bảy màn có chức năng tương ứng một phần; màn Cài đặt Review chưa nối. Không thể hoàn thành bằng việc đổi chuỗi kết nối SQLite: PostgreSQL còn thiếu dữ liệu và ngữ nghĩa để giữ nguyên nghiệp vụ phụ lục, BOQ bỏ hạng mục, nguồn gốc tham số và lịch sử đợt cũ.

Đã kiểm **8 màn, 68 mẫu API `/api/*`, 12 bảng SQLite**. Theo tiêu chí chức năng dưới đây: **8 API đã có, 23 khác, 37 thiếu**; 10 bảng có ánh xạ khác/một phần, 2 bảng nghiệp vụ chưa có nơi lưu tương đương đầy đủ (`thay_doi_tham_so`, `kl_thanh_toan`). Các con số không phải kết quả chạy nghiệm thu.

- Bản gốc **G** = `D:/Claude/Ho tro review ho so xay dung/review_xaydung/`; đọc README, API, giao diện, mã Python liên quan. **Không liệt kê/mở `G/co_so_du_lieu`, không kết nối DB, không chạy/import chương trình gốc.** Lược đồ lấy duy nhất từ `G/csdl_hop_dong.py:76`.
- Repo **S** = `src/kho_tri_thuc/`; **M** = `S/m4/`; **V** = `M/review_goc/`; **H** = `S/giao_dien/m4.py`; **K** = `S/k2/xay_dung.py`. Mọi `tệp:dòng` bên dưới dùng các tiền tố này; số dòng tại thời điểm kiểm.
- SQL đang dùng ở **`M/sql_m17.py`, `M/sql_review.py`, `M/sql_master_dung_chung.py`**, không có hai tệp `k2/sql_review.py`, `k2/sql_master_dung_chung.py` nêu trong gợi ý. Registry thật: `S/ha_tang/pg_migrations.py:9594`, `:10576`, `:11839`. Không lấy tuple M17 cũ `_M0017_M4_PARTIAL_M4_01` làm lược đồ hiện hành.
- “**Đã có**”: chức năng chính đã nối bằng API M4, có thể đổi URL/DTO/quyền. “**Khác**”: có đường tương ứng nhưng khác phạm vi, quy trình hoặc dữ liệu. “**Thiếu**”: chưa có đường nghiệp vụ tương ứng trong M4 đang được phục vụ. Mã nằm trong `review_goc` chưa được route phục vụ không tính là đã có.
- Đếm API bằng cặp **HTTP method + mẫu đường dẫn** trong `G/API.md`, bỏ query, gộp lần nhắc lại. `{kiem_tra_dot|toan_ven}` và `{anthropic|openai}` mỗi mẫu tính một; nếu bung lựa chọn là 71 endpoint. Ngoài 68 mẫu có `GET /tai/<đường dẫn>` dùng chung, kiểm riêng ở cuối §2.

## 2. Màn × nút/chức năng × API → M4

### 2.1. Khung chung và Tổng quan

Nguồn giao diện: `G/giao_dien/app.js:115` (việc), `:141` (AI), `:187` (Tổng quan), `:578` (khung); tài liệu `G/API.md:27–36`.

| Mã | Màn / nút, chức năng | API gốc theo API.md | M4: trạng thái, bằng chứng / chênh lệch |
|---|---|---|---|
| A01 | Khung: phiên bản, 9 bước, việc chạy | `GET /api/he_thong` | **Thiếu** DTO khung Review; `H:403` chỉ phục vụ tài sản M4 đã liệt kê, `H:502` trả tổng quan M4. |
| A02 | Thanh AI: trạng thái / làm mới | `GET /api/ai` | **Thiếu** bảng trạng thái AI của Review trong M4; shell hiện có cảnh báo chưa Local AI/OCR (`M/giao_dien/m4.js:485`). Cổng AI chung không tự tạo chức năng này. |
| A03–A05 | Khung: danh sách việc / chi tiết, log / Dừng | `GET /api/viec`; `GET /api/viec/{id}`; `POST /api/viec/{id}/dung` | **Thiếu** cả 3. M4 lưu run/result PG (`M/sql_review.py:44`, `:108`), chưa có giao thức việc + dừng chung như `G/giao_dien/api.js:36`. |
| A06 | Tổng quan: việc gần đây, Cần Anh xem xét, đợt chờ duyệt, thống kê | `GET /api/tong_quan` | **Khác**: `GET /api/m4` → `K:211`, UI `M/giao_dien/m4.js:476` là phạm vi, danh sách HĐ/đợt; thiếu feed, đếm cờ đỏ/ô vàng và thẻ việc của bản gốc. |

### 2.2. Trích tham số và danh mục tham số

Nguồn: `G/giao_dien/extraction.js:40`, `:281`, `:331`, `:340`, `:361`, `:383`; API `G/API.md:40–96`.

| Mã | Màn / nút, chức năng | API gốc | M4: trạng thái, bằng chứng / chênh lệch |
|---|---|---|---|
| A07 | Tạo lượt nhiều hợp đồng | `POST /api/trich_xuat` | **Thiếu** thực thể lượt/batch; `M/sql_m17.py:294` lưu lần trích theo một HĐ. |
| A08 | Thả/tải Word, PDF, đáp án TSV | `POST /api/trich_xuat/{luot}/tep` | **Khác**: `POST /api/m4/tep` rồi `hop-dong/gan-tep` (`H:547`, `H:26`). Chưa nhận `.doc`/TSV; PDF nhận tệp nhưng trích chưa hỗ trợ (`M/nguon_review.py:334`). |
| A09 | Bỏ một tệp khỏi lượt | `DELETE /api/trich_xuat/{luot}/tep/{ten}` | **Thiếu** lượt/tệp nháp kiểu nguồn; allowlist lệnh `H:20` không có lệnh tương ứng. |
| A10 | Chạy: chọn model, tham số, hỏi thêm, rà lại, 9 bước | `POST /api/trich_xuat/{luot}/chay` | **Khác**: `POST /api/m4/hop-dong/trich` (`H:27`, `K:430`); wrapper engine #6 `RULE_ONLY`, đủ catalog 37 mã, không chạy quy trình Local AI 9 bước (`M/nguon_review.py:322–374`). |
| A11 | Theo dõi tiến độ lượt | `GET /api/trich_xuat/{luot}` | **Khác**: chi tiết HĐ trả lịch sử lần trích đã ghi (`K:244`), chưa có tiến độ từng HĐ/9 bước/log của lượt. |
| A12 | Dừng lượt | `POST /api/trich_xuat/{luot}/dung` | **Thiếu**; không có trong `H:20`. |
| A13 | Chạy lại lượt lỗi/đã dừng | `POST /api/trich_xuat/{luot}/chay_lai` | **Khác**: có trích lại một HĐ bằng ý định/khóa mới (`K:430`); chưa chép đầu vào của lượt nhiều HĐ. |
| A14 | Xem bảng kết quả, nguồn, lịch sử, tải Excel/JSON | `GET /api/trich_xuat/{luot}/hd/{ten}` | **Khác**: `GET /api/m4/hop-dong/{uuid}` trả tham số hiện hành, lần trích (`H:520`, `K:244`); UI `M/giao_dien/m4.js:832`. Chưa có đầy đủ kết quả theo lượt/HĐ và bộ tệp xuất nguồn. |
| A15 | Sửa giá trị một tham số | `PATCH /api/trich_xuat/{luot}/hd/{ten}/o/{ma}` | **Đã có** sửa: `POST /api/m4/tham-so/sua` (`H:28`, `K:483`, `M/giao_dien/m4.js:863`), kèm revision/lý do/kiểm trích dẫn. Nhánh xác nhận riêng từng ô vẫn khác, xem A16/A25. |
| A16 | Xác nhận các ô đã chọn | `POST /api/trich_xuat/{luot}/hd/{ten}/xac_nhan` | **Khác**: `POST /api/m4/tham-so/xac-nhan` xác nhận **cả bộ** đủ 37 mã (`H:29`, `M/giao_dien/m4.js:881`); chưa xác nhận tập mã/bỏ xác nhận từng ô như nguồn. |
| A17 | Nạp CSDL; 409 nếu chưa xác nhận, nạp có cảnh báo, HĐ cũ chỉ báo lệch | `POST /api/trich_xuat/{luot}/hd/{ten}/nap_csdl` | **Khác**: trích ghi trực tiếp vào hồ sơ PG đã tạo, xác nhận là bước sau (`K:316`, `K:430`, `K:522`); chưa có vùng kết quả trước nạp và ngữ nghĩa `van_nap`/`lech[]`. |
| A18 | Ghi lại danh mục Excel khi tệp trước bị khóa | `POST /api/trich_xuat/{luot}/danh_muc` | **Thiếu**; `H:20` không có xuất danh mục lượt. |
| A19–A20 | Lịch sử các lượt / xóa lượt | `GET /api/trich_xuat`; `DELETE /api/trich_xuat/{luot}` | **Thiếu** cả 2; lịch sử lần trích theo HĐ (`K:244`) không thay được lịch sử lượt nhiều HĐ. |
| A21 | Xem danh mục tham số | `GET /api/tham_so` | **Khác**: danh mục cố định trả trong chi tiết HĐ (`K:246`, `M/nguon_review.py:193`); thiếu các trường cấu hình dò/từ khóa/mức/bắt buộc đầy đủ như nguồn. |
| A22 | Sửa danh mục, sao lưu bản cũ | `PUT /api/tham_so` | **Thiếu**; PG catalog seed cố định `M/sql_m17.py:159`; catalog nguồn được PIN (`M/nguon_review.py:57`). |

Lưu ý: phần docstring đầu `M/nguon_review.py:3` còn mô tả adapter trích cũ. Kết luận trên dựa **thân hàm hiện hành `:322`**, không dựa mô tả cũ.

### 2.3. Danh mục hợp đồng và Phụ lục

Nguồn: `G/giao_dien/contracts.js:251`, `:322`, `:400`, `:437`, `:950`; `G/giao_dien/phu_luc_ai.js:151`, `:168`, `:178`, `:242`; API `G/API.md:98–113`, `:123–136`.

| Mã | Màn / nút, chức năng | API gốc | M4: trạng thái, bằng chứng / chênh lệch |
|---|---|---|---|
| A23 | Danh mục HĐ: tìm/lọc, giá trị hiệu lực, cảnh báo | `GET /api/hop_dong` | **Khác**: `GET /api/m4` (`K:219`, `M/giao_dien/m4.js:502`) có danh sách HĐ theo quyền; thiếu đủ GT sau VAT/hiệu lực, đếm PL/BOQ/ô chưa xác nhận, cờ đỏ/vàng. |
| A24 | Chi tiết tại ngày: tham số gốc/hiệu lực, PL, đợt, Nguồn | `GET /api/hop_dong/{ma_hd}` | **Khác**: `GET /api/m4/hop-dong/{uuid}` (`K:233`); chưa có tham số hiệu lực theo ngày/PL và nguồn trích đầy đủ như nguồn. |
| A25 | Xác nhận riêng tham số đã nạp | `POST /api/hop_dong/{ma_hd}/tham_so/{ma_ts}/xac_nhan` | **Khác**: xác nhận cả bộ (`K:522`, `M/sql_m17.py:348`), chưa lưu xác nhận từng tham số độc lập. |
| A26 | BOQ hiệu lực theo ngày, dòng đã bỏ, lịch sử, tổng so HĐ | `GET /api/hop_dong/{ma_hd}/boq` | **Khác**: `GET /api/m4/dot/{uuid}` có hiệu lực tại ngày NT (`M/giao_dien/m4.js:1122`); Review có BASIS (`M/giao_dien/review.js:605`). Chưa là màn BOQ đầy đủ chọn ngày bất kỳ; thiếu thao tác `BO` typed (`M/sql_m17.py:417`). |
| A27 | Chi tiết PL: tham số đổi, BOQ, kiểm tra, lịch sử các lần nạp | `GET /api/hop_dong/{ma_hd}/phu_luc/{so_pl}` | **Khác**: `K:251` trả metadata PL qua chi tiết HĐ; UI `M/giao_dien/m4.js:893`; chưa có bảng tham số đổi/GT PL/lịch sử nạp như nguồn. |
| A28 | Tạo phiếu Excel phụ lục | `POST /api/hop_dong/{ma_hd}/phieu_phu_luc` | **Thiếu**; lõi `V/csdl_hop_dong.py:622` có nhưng chưa route M4. |
| A29–A30 | Chọn phiếu → kiểm P01–P18 / nạp sheet không CHẶN | `POST /api/phu_luc/kiem_tra`; `POST /api/phu_luc/nap` | **Thiếu** cả 2; `H:30–32` chỉ khai/thêm metadata/hủy, không phải kiểm/nạp phiếu. |
| A31 | Hủy PL kèm lý do, giữ lịch sử | `POST /api/hop_dong/{ma_hd}/phu_luc/{so_pl}/huy` | **Đã có**: `POST /api/m4/phu-luc/huy` (`H:32`, `K:567`, `M/giao_dien/m4.js:912`), dùng UUID/revision. |
| A32 | Kiểm đợt hai lớp từ file | `POST /api/hop_dong/{ma_hd}/kiem_dot` | **Khác**: `POST /api/m4/review/chay`, chế độ `L1_L2` (`H:40`, `M/giao_dien/review.js:343`); dùng tệp/đợt đã đăng ký, chưa đủ PL/historical data nguồn, xem §3. |
| A33–A34 | Xuất CSDL Excel / sao lưu CSDL | `POST /api/csdl/xuat_excel`; `POST /api/csdl/sao_luu` | **Thiếu** cả 2 trong M4. `G/may_chu/dich_vu.py:1711`, `:1723` gắn SQLite; tải báo cáo một run không phải xuất/sao lưu toàn CSDL. |
| A39–A40 | PL Word/PDF: tải nhiều file / chạy quy tắc + Local AI | `POST /api/phu_luc_ai/tai_len`; `POST /api/phu_luc_ai/chay` | **Thiếu** cả 2 luồng trích PL. Tải tệp PHU_LUC hiện có (`H:547`) chỉ là lưu tệp, chưa sinh bản trích/kiểm P20–P26. |
| A41–A42 | PL AI: danh sách / mở kết quả | `GET /api/phu_luc_ai`; `GET /api/phu_luc_ai/{id}` | **Thiếu** cả 2; mã nguồn đã chép `V/may_chu/phu_luc_ai.py`, chưa route tại `H:384`. |
| A43–A44 | PL AI: sửa/xác nhận/thêm/bỏ tham số, chọn chế độ BOQ / Hỏi lại AI | `POST /api/phu_luc_ai/{id}/cap_nhat`; `POST /api/phu_luc_ai/{id}/hoi_lai_ai` | **Thiếu** cả 2; thêm PL thủ công (`K:546`) không thực hiện các bước này. |
| A45–A46 | PL AI: nạp sau kiểm / xóa bản trích | `POST /api/phu_luc_ai/{id}/nap`; `DELETE /api/phu_luc_ai/{id}` | **Thiếu** cả 2; chưa có thực thể bản trích PL trong DDL M4 được rà. |

### 2.4. BOQ

Nguồn: `G/giao_dien/contracts.js:507`, `:546`, `:593`, `:636`, `:691`, `:783`, `:834`; API `G/API.md:115–121`. Nạp cả loạt dùng lại 4 API này, không có API batch riêng.

| Mã | Màn / nút, chức năng | API gốc | M4: trạng thái, bằng chứng / chênh lệch |
|---|---|---|---|
| A35 | Import BOQ: tải Excel/Word/PDF, OCR, đoán HĐ; nhiều file | `POST /api/boq/tai_len` | **Khác**: `POST /api/m4/tep` + `boq/xem` (`H:33`, `H:547`); BOQ chỉ `.xlsx` (`M/nguon_review.py:95`). Chưa có Word/PDF/.xls, tự nhận HĐ, bảng ĐẠT/LỆCH chọn sẵn khi nạp loạt. |
| A36 | Chọn sheet, xem 40 dòng, đoán tiêu đề, ánh xạ cột/Mã HM | `POST /api/boq/sheet` | **Đã có**: `POST /api/m4/boq/xem` nhận `tep_id,sheet` (`K:587`, `M/giao_dien/m4.js:977–1017`); đọc lại lõi nguồn `M/nguon_review.py:401`. |
| A37 | Kiểm trước ghi: tổng làm tròn, VAT so HĐ, chặn thay BOQ | `POST /api/boq/kiem_tra` | **Khác**: đọc/kiểm dòng `M/nguon_review.py:475`, nhập `K:593`; tách lỗi chặn/phát hiện. Chưa có bước độc lập trả `gt_hd,lech,can_ly_do` theo API nguồn. |
| A38 | Ghi; thay BOQ cần lý do; cho nhận lệch có xác nhận | `POST /api/boq/ghi` | **Khác**: `POST /api/m4/boq/nhap` (`H:34`, `M/giao_dien/m4.js:1022`) tạo lần nhập có revision; chưa có `chap_nhan_lech` và quy trình thay BOQ gốc như nguồn. |

Xem BOQ hiệu lực/tìm hạng mục/xuất CSV ở client dùng A26 (`G/giao_dien/contracts.js:488`, `:507`). CSV và báo cáo nạp loạt cần giữ lại khi chép UI; không cộng API mới.

### 2.5. Kiểm tra đợt và Chứng từ

Nguồn: `G/giao_dien/checks.js:151`, `:173–338`, `:380`, `:448`; `G/giao_dien/chung_tu.js:49`, `:80`, `:122`, `:130`, `:165`; API `G/API.md:138–166`.

| Mã | Màn / nút, chức năng | API gốc | M4: trạng thái, bằng chứng / chênh lệch |
|---|---|---|---|
| A47 | Chứng từ: tải Word/Excel/PDF/ảnh; thêm vào bộ | `POST /api/chung_tu/tai_len` | **Khác**: nhận qua `POST /api/m4/tep`, `dot/gan-tep` (`H:37`, `H:547`); tệp thuộc đợt, chưa nhận đủ đuôi nguồn, OCR/AI provider chưa cấu hình (`M/nguon_review.py:669–676`). |
| A48 | Chạy C01–C09: theo kết quả đợt / chỉ HĐ + ngày / thêm bộ | `POST /api/chung_tu/chay` | **Khác**: `POST /api/m4/chung-tu/chay` (`H:44`, `K:1680`), bắt buộc đợt; Word/Excel native có, PDF/ảnh/form AI chưa đọc đầy đủ (`M/chung_tu_adapter.py:3–18`). |
| A49 | Lịch sử các bộ chứng từ | `GET /api/chung_tu` | **Khác**: `GET /api/m4/chung-tu?dot_id=` (`H:465`, `K:1600`); danh sách theo đợt, không phải danh sách bộ toàn cục/chỉ HĐ của nguồn. |
| A50 | Chi tiết: dòng hàng, bằng chứng, ma trận, phát hiện/ảnh hưởng | `GET /api/chung_tu/{id}` | **Khác**: `GET /api/m4/chung-tu/{run}` (`H:471`, `K:1645`), ma trận `M/giao_dien/chung_tu.js:364`; có coverage/ghép tay bổ sung, chưa đủ OCR/AI như nguồn. |
| A51 | Sửa loại/số/ngày/bỏ-dùng lại → đối chiếu lại | `POST /api/chung_tu/{id}/cap_nhat` | **Khác**: `POST /api/m4/chung-tu/sua` (`H:46`); ghi revision rồi **bấm Chạy lại**, không tự đối chiếu trong cùng lệnh (`M/giao_dien/chung_tu.js:245–259`). |
| A52 | Xóa bộ chứng từ, giữ file gốc | `DELETE /api/chung_tu/{id}` | **Thiếu**; M4 giữ chuỗi run/revision bất biến (`M/sql_chung_tu.py:59`, `:140`), chưa có thao tác ẩn/lưu trữ thay thế trên UI. |
| A53 | Chỉ toàn vẹn file, ô đích, K1–K8/cây truy vết | `POST /api/toan_ven` | **Đã có** với `.xlsx`: `POST /api/m4/review/chay`, `che_do=L1` (`H:40`, `M/giao_dien/review.js:385`, `M/review_compute.py:499`). Chưa có chuyển `.xls` như nguồn. |
| A54 | Xem lịch sử kiểm đợt / toàn vẹn | `GET /api/kiem_tra/{kiem_tra_dot\|toan_ven}` | **Đã có**: `GET /api/m4/review` có lọc chế độ/phạm vi (`H:481`, `K:1103`, `M/giao_dien/review.js:649`). |
| A55 | Mở kết quả: tổng quan, L1/L2, từng HM, bằng chứng, cây, báo cáo | `GET /api/kiem_tra/{kiem_tra_dot\|toan_ven}/{ma}` | **Đã có** bố cục/kết quả đã tính: `GET /api/m4/review/{run}` (`H:488`, `K:1141`), UI `M/giao_dien/review.js:412–552`, tải báo cáo `:641`. Độ đầy đủ dữ liệu L2 xét riêng A32/§3; không suy “đạt đủ” từ việc hiển thị được. |
| A56 | Ghép tay dòng hồ sơ với mã HM, nhớ cho đợt sau | `POST /api/kiem_tra/kiem_tra_dot/{ma}/ghep` | **Đã có**: `POST /api/m4/review/ghep` (`H:42`, `K:1036`, `M/giao_dien/review.js:360`), có lý do, kiểm BOQ hiệu lực và revision map. |
| A57 | Chạy lại trên file cũ sau ghép | `POST /api/kiem_tra/kiem_tra_dot/{ma}/chay_lai` | **Đã có**: `POST /api/m4/review/chay-lai` (`H:41`, `K:1025`, `M/giao_dien/review.js:353`), giữ run cha/con. |
| A58 | Nạp đợt đã duyệt, ngày nhận HS/ghi chú; nạp lại cần lý do | `POST /api/kiem_tra/kiem_tra_dot/{ma}/nap` | **Thiếu** luồng nạp lịch sử nguồn. M4 có tạo/nộp/duyệt/seal (`H:35–38`, `H:50–54`), nhưng không tương đương ghi `dot_thanh_toan/kl_thanh_toan`; không được biến đợt cũ thành quyết định duyệt M4 giả. |

M4 đã tái dùng K1–K8/B1–B8 và C01–C09, đồng thời báo coverage thiếu căn cứ thay vì cho đạt giả (`M/review_compute.py:6–8`, `M/chung_tu_adapter.py:3–18`). **Có đường lịch sử đợt M4 đã seal**: `K:784` → `M/duyet_dot.py:161–208`; không kết luận M4 hoàn toàn chưa có lịch sử đã duyệt. Tuy nhiên projection SQLite đang để trống bảng đợt legacy (`M/nguon_review.py:604–608`), nên cần nguồn lịch sử nhập riêng.

### 2.6. Cài đặt

Nguồn: `G/giao_dien/app.js:269–520`; API `G/API.md:168–186`. Các API này **thiếu ở màn Cài đặt Review trong M4**; việc có cổng AI/backup chung ở hệ thống không chứng minh đã nối UI và DTO tương ứng.

| Mã | Màn / nút, chức năng | API gốc | M4: trạng thái, bằng chứng / chênh lệch |
|---|---|---|---|
| A59–A60 | Đọc / lưu AI, trích, cloud, OCR, đường dẫn dữ liệu | `POST /api/cai_dat`; `GET /api/cai_dat` | **Thiếu** cả 2; shell `M/giao_dien/m4.js:428` chưa có màn này; route `H:384` không có nhánh cài đặt Review. |
| A61 | Thử Cloud | `POST /api/cai_dat/thu_cloud` | **Thiếu** đường thử qua cổng AI trong M4; bản gốc đang khóa Cloud trực tiếp (`G/API.md:170–173`). Không chép cơ chế gọi trực tiếp cũ. |
| A62–A63 | Kiểm tra máy Local AI / tự tìm máy | `POST /api/cai_dat/kiem_tra_ai`; `POST /api/cai_dat/tim_may_ai` | **Thiếu** cả 2 trong M4; `M/nguon_review.py:322` vẫn là wrapper `RULE_ONLY`. |
| A64–A65 | Lưu / xóa API key | `POST /api/cai_dat/khoa`; `DELETE /api/cai_dat/khoa/{anthropic\|openai}` | **Thiếu** cả 2 trong M4. Khi chép phải dẫn sang quản trị cổng AI/Mask v2, không mở kho key độc lập của Review. |
| A66–A67 | OCR: trạng thái Hot Folder / chạy thử 1 trang | `GET /api/ocr/trang_thai`; `POST /api/ocr/chay_thu` | **Thiếu** cả 2; provider M4 hiện `NOT_CONFIGURED` (`M/nguon_review.py:674`). |
| A68 | Nhật ký gửi ngoài | `GET /api/cai_dat/nhat_ky_gui_ngoai` | **Thiếu** endpoint/khung xem của Review; cần ánh xạ nhật ký cổng AI hiện có thay vì nhật ký gửi thẳng cũ (`H:384`, `M/nguon_review.py:45–48`). |

**Tải tệp dùng chung:** `G/API.md:15` quy định `GET /tai/<đường dẫn>?xem=1`. M4 **khác**: tải theo ID (`H:520`, `H:488`, `H:471` → `K:309`, `K:1160`, `K:1663`), kiểm quyền/hash; không nhận đường dẫn client. Các nút xuất/tải phải giữ hành vi nhưng chuyển sang ID, không phục vụ thư mục gốc.

**Khung 8 icon:** `M/giao_dien/m4.js:428–467` hiện là danh sách trái và tab chi tiết, chưa là 8 icon của CD-011. HTTP chỉ phục vụ tài sản M4 đã chỉ định (`H:403–424`), không mount nguyên `V/giao_dien/index.html` hay máy chủ nguồn. Giữ điểm vào hiện có cho 02C, 03A, 03B, 04; 8 icon bổ sung không thay bỏ các màn đó.

## 3. SQLite ↔ PostgreSQL hiện có

Chỉ kiểm lược đồ trong mã, **không biết số dòng/giá trị thực tế**. Khóa nguồn phải được giữ trong bảng ánh xạ import; tên bảng đích dưới đây là hiện trạng, không phải khẳng định đã chuyển dữ liệu. `M/sql_master_dung_chung.py:86`, `:117` là căn cứ master/phiên bản, **không** thay bảng tham số/BOQ/đợt nguồn.

| SQLite: bảng, cột chính, khóa (G/csdl_hop_dong.py) | PostgreSQL M4/master hiện có | Map / thiếu / khác kiểu, phần cần bảo toàn |
|---|---|---|
| `che_do` (`:78`): PK `id=1`, `sua INTEGER` | Ghi qua hàm, quyền/RLS, nhật ký và revision (`M/sql_m17.py:459`, `:1007`; `M/sql_master_dung_chung.py:115`) | **Khác** cơ chế; không chuyển cờ sửa toàn cục thành công tắc bỏ kiểm PG. Đối chiếu vẫn báo 1 dòng cấu hình nguồn và xử lý có chủ ý. |
| `hop_dong` (`:81`): PK `ma_hd TEXT`, UQ `so_hd`; `phan_loai,loai_gia,ngay_ky,goi_thau,gia_tri_hd REAL,gom_vat,vat REAL,file_nguon,ngay_nap` | `master.hop_dong`: UUID, PN/dự án/đối tác, `ngay_ky DATE,gia_tri_minor BIGINT,tien_te`; `m4.ho_so_hop_dong` PK/FK `hop_dong_id` (`S/ha_tang/pg_migrations.py:301`, `M/sql_m17.py:276`) | **Khác/map một phần**. UQ đích theo PN+loại+số HĐ, nguồn toàn cục. TT-01/02/03/04 có thể chứa loai_gia/GT/VAT nhưng không thay được mọi cột gốc; cần lưu phân loại/gói thầu/giá trị gốc/nguồn, map `ma_hd→UUID`. Không tự suy PN/dự án/đối tác. |
| `tham_so` (`:94`): PK/FK `(ma_hd,ma_ts)`; `ten,gia_tri,don_vi,dieu_khoan,trich_dan,trang_thai` | `m4.tham_so` PK `(hop_dong_id,ma)` + catalog/trích/lich_su/xác nhận (`M/sql_m17.py:314–364`) | **Khác/map một phần**. `gia_tri` vẫn TEXT; trạng thái nguồn là chuỗi AI/xác nhận, đích là 4 trạng thái nghiệp vụ, xác nhận ở cấp bộ. Catalog đích chỉ TC/TT (`:160`), nguồn cho cả Y-xx (`G/csdl_hop_dong.py:94`). Trích dẫn trống/dài có thể vi phạm CHECK, không cắt dữ liệu âm thầm. |
| `phu_luc` (`:99`): PK `id INTEGER`, FK `ma_hd`; `so_pl,ngay_ky,ngay_hieu_luc,loai,doi_boq,gt_truoc_vat,gt_sau_vat,gt_hd_sau_pl,noi_dung,can_cu,file_nguon,phieu,trang_thai,nguoi_nhap,ngay_nap,ly_do_huy`; UQ `(ma_hd,so_pl)` khi chưa hủy | `m4.phu_luc`: UUID, FK HĐ, ngày DATE, boolean, trạng thái enum text; UQ tương đương có điều kiện (`M/sql_m17.py:365–386`) | **Khác/map một phần**. Thiếu `loai`, 3 giá trị PL, `can_cu,phieu` và nguồn gốc lịch sử đầy đủ. PG bắt `ngay_hieu_luc>=ngay_ky`; nguồn không có CHECK đó. Không đổi ngày/lý do để ép nhập. |
| `thay_doi_tham_so` (`:115`): PK `(pl_id,ma_ts)`, FK PL; `gia_tri_cu,gia_tri_moi,trich_dan` | Chưa có bảng thay đổi tham số gắn PL; `m4.tham_so_lich_su` là sửa tham số hiện hành, không phải hiệu lực PL | **Thiếu**. Cần bảng PL→tham số để chạy đúng `tham_so_hieu_luc/gt_hd_hieu_luc` (`G/csdl_hop_dong.py:405`, `:428`); projection hiện chỉ nạp metadata PL (`M/nguon_review.py:631`). |
| `boq_dong` (`:120`): PK `id`, FK HĐ/PL nullable; UQ `(ma_hd,IFNULL(pl_id,0),ma_hm)`; `thao_tac GOC/THAY/THEM/BO`, `stt,nhom,ten,dvt,kl REAL,don_gia REAL,thanh_tien_ghi REAL,khoa,vi_tri_nguon,ghi_chu,ma_rieng` | `m4.boq` version/lần nhập + `m4.boq_dong` PK `(boq_id,dong)`; `kl,don_gia,thanh_tien TEXT`, `o_goc JSONB,ma_rieng` (`M/sql_m17.py:388–421`) | **Khác/map một phần**. Thiếu `BO`, khóa ID nguồn và bảo toàn `khoa/ghi_chu/vi_tri_nguon` đầy đủ. Đích bắt `ten,dvt NOT NULL`; số lưu chữ để phân biệt ô trống/0/sai kiểu. Không gộp các HM trùng tên; giữ thứ tự `id` nguồn khi dựng dòng. |
| `dot_thanh_toan` (`:133`): PK `(ma_hd,dot)`, FK HĐ; `ngay_nghiem_thu,ngay_nhan_hs,gt_ky,gt_luy_ke,giu_lai,thu_hoi_tu,gt_tt_ky,file_nguon,ngay_nap` | `m4.dot` UUID, UQ HĐ+số đợt, NT DATE, trạng thái NHAP/DA_NOP (`M/sql_m17.py:422`); tiền chấp thuận ở `m4.duyet_ket_luan`, seal (`M/sql_duyet.py:194`, `:290`) | **Khác/map một phần**. Chưa có nơi tương đương cho **toàn bộ lịch sử nguồn**/ngày nhận HS/GT kỳ/lũy kế. M4 đã có prior seal (`M/duyet_dot.py:161`); không gán lịch sử SQLite thành seal/DA_NOP giả. Số đợt đích 1–999, nguồn chỉ INTEGER. |
| `kl_thanh_toan` (`:140`): PK `(ma_hd,dot,ma_hm)`, FK `(ma_hd,dot)`; `kl_ky,kl_luy_ke,don_gia_tt REAL,vi_tri_nguon` | `m4.duyet_ket_luan_dong` PK `(ket_luan_id,row_id)` lưu lượng chấp nhận TEXT + đề xuất JSONB (`M/sql_duyet.py:228`); không có bảng lịch sử nguồn cùng ngữ nghĩa | **Thiếu** bảng lịch sử KL thanh toán legacy. Không dùng lượng được đề xuất thay lượng đã duyệt. Cần nối prior provider giữ đúng `ma_hm`, kỳ/lũy kế/đơn giá/nguồn và phân biệt với dữ liệu M4 đã seal. |
| `khop_hang_muc` (`:146`): PK `(ma_hd,khoa_hstt)`; `ma_hm,cach_khop,nguoi_xac_nhan,ngay` (không khai FK trong DDL nguồn) | `m4.review_manual_map`: UUID, UQ `(hop_dong_id,khoa_hstt,revision)`, FK BOQ+dòng/run, raw hash, lý do/actor (`M/sql_review.py:131`) | **Khác/map một phần**. Đích bắt run/tệp/BOQ hiện hành, nguồn không có những ID này. Cần lưu bản ghép nhập có provenance riêng, không tạo run/hash/actor giả để vượt FK. |
| `canh_bao` (`:151`): PK `id`, `ma_hd,pl_id,dot,ma_kt,muc_do,noi_dung,thoi_diem` (không khai FK) | `m4.review_result.ket_qua/coverage` (`M/sql_review.py:108`), phát hiện BOQ `M/sql_m17.py:401`, phát hiện L3 `M/sql_chung_tu.py:117` | **Khác/map một phần**: có nơi lưu phát hiện theo run, thiếu danh sách lịch sử cảnh báo PL/HĐ nguồn độc lập và ID gốc. Bảo toàn cảnh báo cũ, không buộc phải tái chạy mới có cảnh báo. |
| `nhat_ky` (`:155`): PK `id`, `thoi_diem,nguoi,thao_tac,ma_hd,chi_tiet`; cấm UPDATE/DELETE | `m4.nhat_ky`: UUID, `du_an_id NOT NULL,hop_dong_id,dot_id,hanh_dong,boi,luc TIMESTAMPTZ,chi_tiet JSONB` (`M/sql_m17.py:470`) | **Khác/map một phần**. Chuỗi chi tiết nguồn chưa chắc là JSON; thời gian không timezone; có log thiếu HĐ/actor. Giữ nguyên chuỗi/log gốc; người nhập hiện tại tách khỏi người lịch sử, không bịa liên kết. |
| `tham_so_nguon` (`:158`): PK/FK `(ma_hd,ma_ts)`; `gia_tri_ai,gia_tri,kiem_tra,muc,nguon,da_xac_nhan,da_sua_tay,nguoi_xac_nhan,luc_xac_nhan,ghi_chu_soat,lich_su,model,may_ai,luot,file_hop_dong,sha1_file,luc_trich,luc_nap` | `m4.trich_xuat.phieu/ket_qua JSONB`, `m4.tham_so.gia_tri_may/nguon`, `tham_so_lich_su`, `xac_nhan_tham_so` (`M/sql_m17.py:294–364`) | **Khác/map một phần**. Chưa bảo toàn một bản nguồn gốc **từng tham số** với mức, model/máy/lượt, xác nhận riêng và SHA-1 nguồn. SHA-256 tệp đích không thay chứng cứ SHA-1 cũ; cần giữ cả hai. |

**Không đồng nhất 36 với 37 mã:** `G/csdl_hop_dong.py:50–70` là danh sách chuẩn 36; danh mục trích đã ghim là 37 (`M/nguon_review.py:5`, `:193`). Kiểm theo catalog thực tế, giữ mã bổ sung nguồn khi import; không ép loại bỏ mã vì không có trong enum M17.

## 4. Phần chép nguyên và phần phải thích nghi/viết lại

| Phần | Kết quả kiểm mã / hướng thực hiện |
|---|---|
| Thuật toán thuần, quy tắc, workbook report | So sánh byte trực tiếp cho thấy G và V giống ở `csdl_hop_dong.py`, `master_hd.py`, `toan_ven.py`, `may_chu/nghiep_vu.py`, `may_chu/phu_luc_ai.py`, `may_chu/chung_tu.py`. Dùng lại K1–K8, B1–B8, P01–P18/P20–P26, C01–C09, matcher, logic 37 tham số; không viết lại thuật toán/ngưỡng. Các hàm trộn SQL và nghiệp vụ phải tách biên dữ liệu, giữ cùng kết quả trên fixture giả. |
| Giao diện có thể chép phần hiển thị | `api.js`, `extraction.js`, `contracts.js`, `checks.js`, `chung_tu.js`, `phu_luc_ai.js`, `ui.js`, `chon_hd.js`, `index.html`, `styles.css` đã giống byte G↔V. Giữ bảng, bộ lọc, drawer Nguồn/bằng chứng, cây, ma trận, nạp loạt, CSV. Đây là mã đã chép, chưa phải các màn được mount. `app.js` **khác** (bản gốc đã thêm chặn Cloud AI-0a); không chép đè nguyên shell cũ vào hệ thống. |
| Nối UI/HTTP | Phải đổi `G/giao_dien/api.js:2` từ `X-HD`/đường dẫn file sang token+cookie phiên, ID/tệp được quản lý của M4 (`H:1–3`). Tách render từng màn khỏi router/sidebar nguồn; đưa vào icon, giữ ngữ cảnh PN/dự án/HĐ/đợt và hủy phản hồi trễ khi đổi vai như M4 hiện tại. Không iframe/server 8600 thứ hai, không mở route dữ liệu chỉ nhờ header `X-HD`. |
| `csdl_hop_dong.py` → PG | Viết repository PG phía ngoài vendor: `%s`/row mapping/transaction thay `?`, `sqlite3.Row`, `executescript`, PRAGMA, `INSERT OR IGNORE`, `lastrowid`, `IFNULL`, bảng `che_do`. Migration mới cho dữ liệu thiếu + khóa nguồn; RLS, FK, constraint, lý do và audit trong PG. `mo_csdl` (`G:197`) tự tạo thư mục/DB/DDL nên không được dùng cho đọc nguồn thật hay đường runtime PG. |
| Hàm nghiệp vụ đang nhận `con` SQLite | `G/csdl_hop_dong.py:352–437`, `:832`, `:1024`, `:1258`, `:1316`, `:1686` không phải hàm thuần hoàn toàn. Chọn seam repository/snapshot hẹp; bổ sung projection cho dữ liệu PL/BO/lịch sử còn thiếu. Projection `:memory:` hiện có chỉ là dữ liệu tính tạm (`M/nguon_review.py:604`), PG vẫn là nơi lưu chính. Nếu bỏ hoàn toàn SQLite cả trong compute phải là lát riêng có regression parity, không tráo âm thầm toàn bộ lõi ghim. |
| Dịch vụ, việc nền và tệp kết quả | `G/may_chu/dich_vu.py:1469` mở SQLite, các API còn dùng lượt/JSON trên đĩa và việc RAM. Cần adapter service theo repository PG, durable job/cancel, tải qua ID; chép GUI đơn thuần không đủ. Trích/PL AI/chứng từ/settings đều đi qua cổng AI chung, Local luôn có, Cloud qua Mask v2. |
| Dữ liệu ngoài SQLite | Lượt trích, bản trích PL AI, bộ chứng từ, báo cáo/file xuất còn được API mô tả trên đĩa (`G/API.md:57–91`, `:132`, `:147`, `:157`). Chuyển 12 bảng không tự khôi phục các lịch sử này. Lát này không đọc các thư mục kết quả; phải kiểm kê metadata/đính kèm ở lát được lead giao tiếp, trước tuyên bố “copy hết”. |

## 5. Đề xuất thứ tự lát (chỉ kế hoạch, chưa tạo/sửa code)

Mỗi dòng là **≤3 tệp**, gồm cả test; tên tệp mới là đề xuất. Các đường `m4/...`, `k2/...`, `giao_dien/...` trong bảng tương đối S; `tests/...`, `tools/...` tương đối repo. Tệp dùng chung phải khóa theo lead. Lát đủ chức năng có thể cần nhiều lượt nhỏ liên tiếp, không nhét cả 8 màn vào một lần sửa.

| Thứ tự / lát | Phạm vi, tệp dự kiến | Điều kiện xong |
|---|---|---|
| 1 · M4-DL1 | DDL bổ sung các trường/bảng thiếu, khóa nguồn/import, không sửa migration cũ: `m4/sql_review_chep.py` (mới), `ha_tang/pg_migrations.py`, `tests/test_m4_review_chep_schema.py` (mới) | Map đủ 12 bảng, giữ NULL/kiểu/khóa/hủy PL/BO/nguồn gốc; FK/RLS; không tạo CSDL thật. **Đây là lát đầu đề xuất.** |
| 2 · M4-DL2 | Repository HĐ/tham số/nguồn gốc: `m4/review_data_pg.py` (mới), `tests/test_m4_review_data_pg.py` (mới) | Đọc/ghi theo khóa nguồn; giữ xác nhận từng ô; không tạo trích giả. |
| 3 · M4-DL3 | Repository PL/tham số thay đổi/BOQ: `m4/review_data_pg.py`, `m4/review_phu_luc_pg.py` (mới), `tests/test_m4_review_phu_luc_pg.py` (mới) | Hiệu lực theo ngày/THAY-THEM-BO, GT PL, lịch sử hủy đúng bản gốc. |
| 4 · M4-DL4 | Repository đợt/KL/ghép/log legacy: `m4/review_data_pg.py`, `m4/review_dot_pg.py` (mới), `tests/test_m4_review_dot_pg.py` (mới) | Dữ liệu nguồn đủ, audit bất biến; không suy duyệt từ DA_NOP. |
| 5 · M4-DL5a | Nối PL/BO vào snapshot compute: `m4/nguon_review.py`, `k2/xay_dung.py`, `tests/test_m4_review_compute.py` | Regression parity P/B, không sửa vendor PIN; snapshot chứa đủ thay đổi PL. |
| 6 · M4-DL5b | Nối lịch sử đợt nhập với prior provider: `m4/duyet_dot.py`, `m4/review_dot_pg.py`, `tests/test_m4_review_dot_pg.py` | Không cộng trùng legacy + seal M4; dữ liệu thiếu không thành 0; đối chiếu theo mã HM. |
| 7 · M4-CD1 | Import idempotent: `tools/chuyen_review_sqlite_sang_pg.py` (mới), `m4/review_data_pg.py`, `tests/test_chuyen_review_pg.py` (mới) | Chạy lại không tăng bản ghi/trùng ID; nguồn chỉ đọc; lỗi dừng, không sửa tay. |
| 8 · M4-CD2 | Đối chiếu độc lập: `m4/review_doi_chieu.py` (mới), `tools/chuyen_review_sqlite_sang_pg.py`, `tests/test_chuyen_review_pg.py` | Số dòng từng bảng + tổng HĐ/BOQ/từng đợt + dòng lỗi; phát hiện lệch dù tổng chung triệt tiêu. |
| 9 · M4-CD3 | Metadata/tệp đính kèm và lịch sử trên đĩa, sau khi được giao phạm vi: `m4/review_tep_pg.py` (mới), `tools/chuyen_review_sqlite_sang_pg.py`, `tests/test_m4_review_tep_pg.py` (mới) | Map đường dẫn cũ→tệp ID/hash, báo tệp thiếu; không đọc thư mục dữ liệu chưa được phép. |
| 10 · M4-UI0 | Khung 8 icon: `m4/giao_dien/m4.js`, `m4/giao_dien/m4.css`, `tests/m4_icon_async.cjs` (mới) | 8 điểm vào độc lập; dùng phiên/quyền/PN/thanh trên; giữ 02C/03A/03B/04. Dùng khung icon chung đã chốt TL49. |
| 11 · M4-UI1a/b | Tổng quan: (a) `m4/review_tong_quan.py` (mới), `giao_dien/m4.py`, `tests/test_m4_review_tong_quan.py` (mới); (b) `m4/giao_dien/tong_quan_review.js` (mới), `m4/giao_dien/m4.js`, `tests/m4_tong_quan_async.cjs` (mới) | Feed/cờ đỏ/ô chưa xác nhận/đếm việc; API trước, mount UI sau. |
| 12 · M4-UI2a/b | Trích tham số: (a) `m4/review_trich.py` (mới), `giao_dien/m4.py`, `tests/test_m4_review_trich.py` (mới); (b) `m4/giao_dien/extraction.js` (mới, port nguồn), `m4/giao_dien/m4.js`, `tests/m4_extraction_async.cjs` (mới) | Batch/9 bước/chọn tham số/sửa-xác nhận/nạp/lịch sử; Local AI qua cổng chung, không chỉ RULE_ONLY. |
| 13 · M4-UI3a/b | Danh mục HĐ: (a) `m4/review_hop_dong.py` (mới), `giao_dien/m4.py`, `tests/test_m4_review_hop_dong.py` (mới); (b) `m4/giao_dien/contracts.js` (mới, port nguồn), `m4/giao_dien/m4.js`, `tests/m4_contracts_async.cjs` (mới) | Đủ cột/lọc, tại ngày, drawer Nguồn/PL/đợt, export. |
| 14 · M4-UI4a/b/c | Phụ lục: (a) phiếu/P01–P18: `m4/review_phu_luc_pg.py`, `giao_dien/m4.py`, `tests/test_m4_review_phu_luc_pg.py`; (b) PL AI: `m4/review_phu_luc_ai.py` (mới), `giao_dien/m4.py`, `tests/test_m4_review_phu_luc_ai.py` (mới); (c) UI: `m4/giao_dien/phu_luc_ai.js` (mới), `m4/giao_dien/contracts.js`, `tests/m4_phu_luc_async.cjs` (mới) | Hai đường phiếu và Word/PDF, duyệt tham số/BOQ, P20–P26, hỏi lại/nạp/hủy; icon đã đăng ký UI0. |
| 15 · M4-UI5a/b | BOQ: (a) `m4/review_boq.py` (mới), `giao_dien/m4.py`, `tests/test_m4_review_boq.py` (mới); (b) `m4/giao_dien/contracts.js`, `m4/giao_dien/m4.js`, `tests/m4_boq_async.cjs` (mới) | Ngày hiệu lực/dòng bỏ, tổng-VAT, single/batch, nhận HĐ/CSV, Word/PDF/.xls qua provider được cấu hình. |
| 16 · M4-UI6a/b | Kiểm tra đợt: (a) `m4/review_dot_pg.py`, `giao_dien/m4.py`, `tests/test_m4_review_dot_pg.py`; (b) `m4/giao_dien/review.js`, `m4/giao_dien/m4.js`, `tests/m4_02a_basis_async.cjs` | Giữ màn đã có; bổ sung dừng/nhập đợt, prior legacy và đủ tệp, không thay thuật toán K/B. |
| 17 · M4-UI7a/b | Chứng từ: (a) `m4/chung_tu_adapter.py`, `m4/nguon_review.py`, `tests/test_m4_02b_pure.py`; (b) `m4/giao_dien/chung_tu.js`, `m4/giao_dien/m4.js`, `tests/m4_02b_async.cjs` | Nối provider OCR/AI chung; đủ các mode HĐ/đợt/thêm bộ, sửa/rerun, ma trận; backend mode nếu cần tách lượt 3 tệp riêng trước UI. |
| 18 · M4-UI8a/b | Cài đặt: (a) `m4/review_cai_dat.py` (mới), `giao_dien/m4.py`, `tests/test_m4_review_cai_dat.py` (mới); (b) `m4/giao_dien/cai_dat.js` (mới), `m4/giao_dien/m4.js`, `tests/m4_cai_dat_async.cjs` (mới) | Local/OCR/nhật ký/xuất/sao lưu qua dịch vụ chung; Cloud/key thuộc cổng AI/Mask, không lập kho key mới. |

Nếu durable job/cancel, OCR/converter hay xuất/sao lưu không vừa lát màn: tách backend/provider thành lát ≤3 tệp (service + route/adapter + test) trước lát UI phụ thuộc. Không coi kiểm API tĩnh là hoàn thành các provider này. Test gốc của Review phải được chạy trên bản chép bằng dữ liệu giả, thay fixture kết nối bằng repository PG; giữ bộ test gốc chỉ đọc, không chạy chúng với đường dẫn mặc định DB thật.

### 5.1. Hợp đồng chuyển dữ liệu và đối chiếu bắt buộc

1. **Khóa idempotent:** nhận diện kho nguồn ổn định + tên bảng + PK gốc (kể cả composite), map sang UUID đích có UNIQUE; hash **từng dòng** để phân biệt không đổi/đổi. Không dùng SHA file DB làm duy nhất ID nguồn vì DB phát sinh thêm sẽ đổi SHA. Chạy lại không tạo trích/run/seal/audit nhập trùng; nhật ký riêng cho lần chạy vẫn được ghi. Hàng gốc đổi phải đi qua phiên bản/audit, không upsert đè chứng cứ bất biến.
2. **Nguồn đọc an toàn:** công cụ tương lai mở **bản sao** bằng URI SQLite `mode=ro`, không gọi `mo_csdl()`. Chụp schema version/cột có thực (nguồn cũ có thể thiếu `ma_rieng`, `G/csdl_hop_dong.py:203`); thiếu cột phải có quy tắc rõ, không tự ALTER nguồn. Chốt một snapshot nhất quán trước khi đếm/tính/nạp; FK nhập theo HĐ→PL/đợt→dòng con.
3. **Đối chiếu số dòng:** cả 12 bảng nguồn, số khóa đã map ở đích, số thành công/không đổi/lỗi; so theo tập khóa nguồn, không so tổng bảng master dùng chung. Bảng kỹ thuật `che_do` báo riêng “không sao chép cờ quyền”; nhật ký/cảnh báo giữ payload nguồn để truy ngược. Báo orphan/trùng khóa/giới hạn CHECK và danh sách dòng lỗi bằng bảng+PK+cột+mã lỗi; báo cáo dữ liệu thật đặt ngoài git.
4. **Tổng giá trị HĐ:** tổng `gia_tri_hd` gốc và tổng sau VAT theo `gom_vat/vat`; thêm giá trị hiệu lực tại cùng ngày chốt/PL đã ký. Đối chiếu từng HĐ rồi tổng, giữ dấu âm/NULL; tiền nguồn là đồng, ghi rõ **VND**, chưa mặc định BIGINT minor cũng bằng đồng nếu chưa xác nhận quy ước master.
5. **Tổng BOQ:** riêng BOQ gốc và BOQ hiệu lực tại ngày chốt/từng ngày NT; giữ số dòng GOC/THAY/THEM/BO. Đối chiếu cả `Σ thanh_tien_ghi`, `Σ round(kl×don_gia)` theo quy tắc nguồn, VAT và sau VAT; không cộng mọi dòng PL thành tổng BOQ hiệu lực. So từng HĐ/HM để phát hiện đảo mã hoặc lệch bù trừ.
6. **Tổng từng đợt `(ma_hd,dot)`:** đối chiếu đủ `gt_ky,gt_luy_ke,giu_lai,thu_hoi_tu,gt_tt_ky`; số HM; lượng kỳ/lũy kế và đơn giá từng HM, `Σ KL kỳ×đơn giá`, `Σ KL lũy kế×đơn giá`, trước/sau VAT theo cùng cơ sở nguồn. Không cộng lũy kế các đợt thành một tổng thanh toán, không cộng lượng khác ĐVT. Chênh lệch giữa số ghi và số tính vốn có phải được bảo toàn và trình bày ở cả hai bên.
7. **Tiêu chí:** đối chiếu 100% khóa/dòng/số tiền sau quy tắc chuyển kiểu đã chốt; tuyệt đối không dùng `tol_tien()` nghiệp vụ (`G/csdl_hop_dong.py:347`) để bỏ qua sai lệch chuyển đổi. `Decimal`/ngày chuẩn hóa phải có chính sách với REAL/rỗng/NaN/ngày sai và giữ giá trị nguồn để kiểm; chưa chốt được thì báo dòng lỗi và dừng.
8. **Chạy thật do lead sau review:** (a) backup SQLite + SHA256 vào `LUU-TRU`; (b) diễn tập trên bản sao vào PG tạm, khớp 100%; (c) tạo PG thật riêng **khác tên DB/role DEMO**, cấu hình `*.that.local.json` ngoài git, migrate→nạp→đối chiếu→`pg_dump`; (d) biên bản báo Anh. Trước chuyển hẳn ở cổng B, nạp delta lần cuối. Lệch ở bước nào dừng bước đó; worker kiểm kê này không thực hiện các thao tác trên.

## 6. Rủi ro và giới hạn cần giữ

| Rủi ro | Bằng chứng và xử lý đề xuất |
|---|---|
| PIN/định danh engine | `M/nguon_review.py:41–68`, `:117–176` kiểm SHA trước import; sửa `V/csdl_hop_dong.py` sẽ lỗi `M4_NGUON_REVIEW_SAI_PIN`. Lát này kiểm tĩnh 24 mục PIN: đủ tệp, khớp hash. Chỉ đổi adapter/migration ngoài vendor; nếu bắt buộc đổi vendor phải review+ghim và chấp nhận engine/basis đổi có chủ ý. Không sinh freeze/manifest mới. |
| Cloud bản chép và bản gốc khác thời điểm | `G/giao_dien/app.js` đã có chặn AI-0a; V/app.js chưa có phần đó. V/engine Cloud đã có thay đổi AI-3 qua cổng chung (`M/nguon_review.py:45`, `:48`); không lấy README nguồn nói “khóa Cloud” để kết luận runtime toàn repo vẫn chưa nối Mask. M4 trích hiện vẫn RULE_ONLY; UI mới chỉ bật AI qua cổng chung, Local luôn có/Cloud Mask v2. |
| Word COM và converter | `G/master_hd.py:100–117` có `win32com.client.Dispatch("Word.Application")`; `G/trich_xuat/doc_hop_dong.py:32` tạo Word COM cho chuyển/Accept All. Không chạy/chép nguyên đường thực thi này; giữ kiểm Track Changes OOXML của M4, trạng thái cần người xử lý hoặc provider được phép. `.xls` chuyển qua Excel/LibreOffice của nguồn (`G/README.md`, `G/API.md:155`) cũng là phụ thuộc riêng, không tự gọi COM. |
| Đường dẫn tuyệt đối/cấu hình cục bộ | `G/csdl_hop_dong.py:44` mặc định DB cạnh mã; `G/master_hd.py:104` hardcode LibreOffice; API settings cho nhập đường dẫn OCR (`G/API.md:177–182`). Chuyển về DataRoot/config hệ thống, tệp ID/hash, allowlist và quyền server. Không mang đường dẫn máy Anh sang client, không đọc config/key gốc trong lát này. |
| Tiền, ngày, NULL/0 | SQLite REAL có sai số, ngày TEXT không CHECK; PG DATE/TIMESTAMPTZ, BIGINT minor master và TEXT số M4 (`M/sql_duyet.py:27–30`). Giữ âm cho điều chỉnh PL; tiền chấp thuận M4 không âm/VND nguyên không phù hợp làm kho lưu mọi số lịch sử. Không dùng float roundtrip làm đối chiếu, không đổi rỗng thành 0, không đoán timezone cho log cũ. |
| Khóa/identity, hủy và sửa có lý do | SQLite INTEGER/TEXT PK khác UUID/khóa tổ hợp PG, UQ PL chỉ với bản chưa hủy. `G/csdl_hop_dong.py:175–193` khóa 8 bảng gốc, metadata PL và nhật ký; `:229` sửa có lý do. Phải bảo toàn cả phiên PL hủy, thứ tự dòng, audit và actor lịch sử; không sao chép cờ `che_do.sua` vào quyền ứng dụng. |
| Hồ sơ cũ thiếu tệp/căn cứ | PG bắt tệp/hash, lần trích, actor/PN/dự án mà bản gốc có thể không lưu đủ. Không tạo tệp rỗng/hash giả/trích giả/chấp thuận giả. Lưu provenance import và trạng thái thiếu rõ; phân quyền nhập lịch sử riêng; chặn duyệt mới khi chưa đủ căn cứ. |
| Nhầm đã nộp với đã duyệt | `M/sql_duyet.py:4–17` phân biệt nộp/quyết định/PDF/seal. `M/duyet_dot.py:161` đã có nguồn lịch sử seal M4. Lịch sử SQLite phải là dữ liệu nhập có chứng cứ riêng, không tạo seal để “đủ quy trình”; tránh tính trùng khi cùng đợt xuất hiện ở hai nguồn. |
| Dữ liệu/hiệu năng UI | GUI chi tiết HĐ hiện giới hạn 2.000 dòng BOQ (`K:257`), snapshot compute không giới hạn GUI (`K:733–776`). Chuyển dữ liệu/đối chiếu không dùng DTO bị cắt; giữ polling/job cancel hợp lý, chống phản hồi trễ đổi vai/HĐ. |
| Bảo toàn phạm vi 02C/03A/03B/04 | Route đã có tại `H:48–69`, `:387–399`, `:410–424`; không dựa các nhãn “CHƯA NỐI” cũ trong shell để xóa/viết lại. Giữ duyệt/PDF, kế toán nghiệm thu, đối chiếu/ghi nhận, Request; 03B không mở đường tải riêng cho kế toán (CD-010 mục 7). |

## 7. Tự kiểm và bàn giao

- Đã đọc AGENTS.md, CLAUDE.md và CD-011; đối chiếu API.md, mã 8 màn, 12 CREATE TABLE và constraint/trigger nguồn; rà DDL đăng ký hiện hành, route, service, UI và compute M4.
- Kiểm byte các tệp nguồn/chép nêu §4; kiểm đủ và khớp 24 mục PIN bằng đọc tệp, không import lõi. Không truy cập dữ liệu thật, không gọi mạng/COM, không chạy server/PostgreSQL/chương trình gốc.
- Đây là thay đổi tài liệu: **không chạy bộ test ứng dụng; không kết luận xanh so nền**. Kiểm cuối: chỉ một tệp thay đổi, UTF-8 không BOM, bảng API đủ A01–A68, số đếm trạng thái khớp, các tham chiếu mã nguồn tồn tại.
- Đề xuất commit để lead thực hiện ngoài sandbox: **`[M4-KK] Kiểm kê 8 màn Review và ánh xạ SQLite sang PostgreSQL M4`**.
