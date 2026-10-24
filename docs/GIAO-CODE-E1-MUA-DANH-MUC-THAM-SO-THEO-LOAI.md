# E1-MUA — Danh mục tham số hợp đồng mua theo loại cho engine "#6 Trích tham số hợp đồng" (review xây dựng)

> **Quyết định bổ sung 21/10/2026 — ưu tiên áp dụng:** [Một engine #6 dùng chung](QUYET-DINH-ENGINE-TRICH-THAM-SO-DUNG-CHUNG.md) tại source qua API, không tạo/copy lõi riêng. Anh đã giao xếp hàng **CRM → M2-00 → E1-MUA**; các câu chờ lệnh bên dưới giữ làm lịch sử, không yêu cầu Anh cấp lại ủy quyền xếp hàng. Root vẫn bind/review trước dispatch; chưa có code/test/nghiệm thu mới. Loại/catalog/version còn phải triển khai theo API thật; không coi đã tồn tại.

**Handoff triển khai CODE — lập 21/10/2026, trạng thái SAN_SANG_GIAO khi anh Dũng ra lệnh code.** Thiết kế đã chốt 20/10 (TL 44 §7: cả 5 loại một đợt; kế toán tổng hợp tự quản danh mục; dịch vụ dùng bản gọn `DV`; bảng hạng mục trích và đối chiếu từng dòng). **Dùng chính engine #6 tại `D:\Claude\Ho tro review ho so xay dung\review_xaydung`, không viết engine mới, không chép engine sang kho tri thức; CRM/M2 gọi qua API trích (TL 41 §4, TL 40 nguyên tắc 11).** Không thuộc `IMPLEMENTATION_AUTHORIZED_M4_ONLY`; chỉ bắt đầu khi anh ra lệnh. Không chạy chung lượt ghi với gói M2-00 (một coder, tuần tự).

## 1. Căn cứ và pin

| Căn cứ | SHA-256 |
|---|---|
| [TL 44 Bộ tham số hợp đồng mua theo loại](../../44-bo-tham-so-hop-dong-mua-theo-loai.md) | `7051dd990a1af74aae72b140eabe319ff3b89dc9c487289cb238fa748d741d30` |
| TL 41 §4 (E1 danh mục theo loại, E2 quy tắc theo loại, E3 tham số dạng bảng, E4 output) | bản Project |
| Danh mục: `THIET-KE-MODULE-DE-CHOT-2026-10-20\tham-so-hop-dong\DANH_MUC_THAM_SO_{DV,MUA_HH,THUE_TS,NHAP_KHAU,DV_KY,DV_1L}.xlsx` + `MA-TRAN-THAM-SO-THEO-LOAI.xlsx` | `DV`: `16e9a167b280a6c0c64ea5eb4c4f329300683277f026ecddcbaf163827cbf422` |
| Đáp án: `tham-so-hop-dong\DAP_AN_DV_nhap_20261020.xlsx` (giá trị thật — chỉ trên máy anh, không vào git/test fixture) | `00c56fd60b44ec789b334f5464e8cd56275dedb606378fc8b39f930d7be5a65b` |
| #6 `trich_xuat\danh_muc.py` / `cau_hinh.py` / `quy_trinh.py` / `logic.py` / `DANH_MUC_THAM_SO.xlsx` | `f0796984…ca2ff2` / `53defa8f…c58d93` / `a76e95a5…b26264` / `f7cfcf37…c4452` / `05846a2a…861bcd` |
| Hàng đợi `HANG-DOI-YEU-CAU.md` #41; `HANG-CHO-CODE.md` gói E1-MUA | — |

Nếu SHA tệp #6 khác pin → dừng, báo Root (có thể M4-01x đã sửa song song).

## 2. Kết quả phải có và phần không làm

**Có:** (a) #6 nạp được **6 loại** (XD + DV, MUA_HH, THUE_TS, NHAP_KHAU; DV_KY/DV_1L là bản mở rộng, có trong kho nhưng không mặc định) qua một hàm `danh_muc_theo_loai(loai)`; (b) API trích nhận loại hợp đồng tường minh; `XD` chỉ là lựa chọn sẵn trên UI, adapter M4 phải gửi `XD` rõ ràng. Request API mới thiếu loại/danh mục/phiên bản hoặc có mã tham số lạ phải báo lỗi, không âm thầm fallback XD/bỏ mã; phân biệt không truyền tập mã, tập rỗng và chọn tất cả, chụp đúng danh mục/quy tắc cho từng lần trích; (c) output JSON thêm `loai_hop_dong` và `phien_ban_danh_muc` (E4); (d) tham số kiểu bảng cho TT-05 (bảng hạng mục) và TT-20 (lịch thanh toán) — E3, dùng lại bộ đọc bảng hiện có; (e) màn hình/lệnh **sửa danh mục** cho kế toán tổng hợp: sửa có hiệu lực ngay, mỗi lần sửa sao lưu bản cũ (`save_catalog` hiện đã sao lưu vào `danh_muc_sao_luu\`) và ghi nhật ký (trước/sau, người, giờ); (f) chạy `DV` trên **2 hợp đồng dịch vụ anh đã gửi**, chấm với `DAP_AN_DV_nhap_20261020.xlsx`, báo tỷ lệ đúng theo mức quan trọng; (g) `tests\test_trich_xuat.py` của xây dựng qua **nguyên trạng** (so kết quả trước/sau trên bộ master mẫu XD).

**Không:** viết engine/prompt mới ngoài cơ chế hiện có; đổi hành vi loại XD; đưa hợp đồng thật, MST, tên đối tác, số tiền vào `tests\`, git, báo cáo, chat; gọi AI cloud ngoài cổng/cấu hình #6 đang có (hợp đồng thật đi qua Mask theo TL 35 — nếu #6 hiện chưa Mask thì **dừng ở chế độ local/offline** và ghi `[CẦN ANH XÁC NHẬN]`); sinh nghĩa vụ/lịch vào master kho tri thức (thuộc gói CRM/M2 sau); tạo BOQ/nghiệm thu khối lượng cho dịch vụ.

## 3. Đường gọi actual — không bịa API

Theo mã đã đọc 20/10: `danh_muc.read_catalog(path)` khớp tiêu đề cột theo tiền tố (`mã`, `nhóm`, `mô tả`, `từ khoá tiêu đề`, `từ khoá nội dung`, `dùng`, `mức`, `từ khoá bắt buộc`, `từ khoá loại trừ`, `luôn hỏi`), đọc sheet đầu; `load_params(path, them)` trả list param theo thứ tự, bỏ dòng Dùng = Không; `save_catalog(rows, path)` kiểm trùng mã, sao lưu bản cũ; `cau_hinh.DANH_MUC_THAM_SO = THU_MUC_GOI / "DANH_MUC_THAM_SO.xlsx"` (dòng 17) là chỗ gắn cứng duy nhất của đường dẫn; `quy_trinh.TrichXuat(params, …)` nhận params làm đầu vào; `logic.py` gắn cứng L2/L3/L5 với mã TT-20/21/52/53/54 (TL 41 E2). API HTTP trích (`POST /api/trich_xuat/{luot}/chay` theo `API.md`) — coder **xác minh lại trong `API.md` và `__main__.py`/server của #6** trước khi thêm tham số; nếu tên khác, dùng tên thật và ghi vào báo cáo.

## 4. Thay đổi theo tệp

| Tệp (trong `review_xaydung\`) | Thay đổi |
|---|---|
| `trich_xuat\cau_hinh.py` | `DANH_MUC_THAM_SO` giữ cho XD; thêm `THU_MUC_DANH_MUC` và hàm `danh_muc_theo_loai(loai) -> Path` (`XD` → file cũ; loại khác → `DANH_MUC_THAM_SO_<loai>.xlsx` cùng thư mục); loại không có file → lỗi rõ, không fallback XD |
| `trich_xuat\danh_muc.py` | Không đổi bộ đọc; thêm `ghi_nhat_ky_sua(path, truoc, sau, nguoi)` ghi JSON-lines cạnh `danh_muc_sao_luu\` (hoặc vào `nhat_ky.su_kien` nếu #6 đã nối `giao_tiep` — TL 40) |
| `trich_xuat\quy_trinh.py` / API | Tham số `loai_hop_dong` xuyên suốt; output thêm `loai_hop_dong`, `phien_ban_danh_muc` (SHA-256 file danh mục) |
| `trich_xuat\logic.py` | Tách L2/L3/L5 thành bảng quy tắc theo loại (E2): XD giữ nguyên; DV/MUA_HH/THUE_TS/NHAP_KHAU: tổng % lịch ≤ 100% (vì có giữ lại), cọc (TT-13) không nằm trong lịch, DV/THUE_TS phải có TT-80 trước khi coi lịch hợp lệ; TT-55 kiểm "mức phạt × ngày vượt 8% phần vi phạm → cần rà soát" |
| `trich_xuat\DANH_MUC_THAM_SO_<loai>.xlsx` (5 + 2 file) | Chép từ `tham-so-hop-dong\` sau khi Root xác nhận SHA; không sửa nội dung trong gói này |
| Màn hình danh mục (nếu #6 có web) hoặc lệnh `python -m trich_xuat danh-muc sua …` | Kế toán tổng hợp sửa dòng → `save_catalog` + nhật ký; không cần CFO duyệt (anh chốt 20/10) |
| `tests\test_trich_xuat.py` + test mới | XD nguyên trạng; loại mới: nạp 6 loại, từ chối loại lạ, bảng TT-05/TT-20 đọc đúng số dòng từ fixture **giả**; nhật ký sửa danh mục |
| `README.md` / `API.md` của #6 | Mục "Danh mục theo loại" |
| Kho tri thức: `CHANGELOG.md`, `docs\BAO-CAO-E1-MUA.md`, `HANG-DOI-YEU-CAU.md` #41 | Số đo trước/sau; bảng chấm DV trên 2 hợp đồng; trạng thái #41 |

## 5. Chấm điểm DV trên hai hợp đồng thật (trên máy anh, không rời máy)

Đầu vào: hai file hợp đồng anh gửi 20/10 (bảo trì PCCC `.doc`; kiểm định quan trắc `.docx`) — Root đặt vào thư mục làm việc của #6 trên máy anh. Đáp án: `DAP_AN_DV_nhap_20261020.xlsx` (sheet `Dap_an` 30 mã × 2; sheet `TT-05_bang` 27 dòng). Báo cáo ghi: số tham số đúng/sai/thiếu theo mức quan trọng 3/2/1/0 cho từng hợp đồng; riêng TT-05 ghi số dòng đọc đúng/tổng; các dòng "Không quy định (để trống)" phải khớp đáp án. Chỉ ghi tỷ lệ, **không chép giá trị tham số thật vào báo cáo** (báo cáo nằm trong git). Dưới 80% đúng ở mức 3 → sửa từ khóa/mô tả danh mục DV → v0.2, chạy lại, ghi cả hai lần.

## 6. Điều kiện kết thúc và bàn giao

- Test #6 xanh (cũ + mới); so kết quả XD trước/sau trên bộ master mẫu: giống từng tham số.
- `docs\BAO-CAO-E1-MUA.md`: tệp sửa + SHA; bảng chấm DV; danh sách `[CẦN ANH XÁC NHẬN]` (Mask cho hợp đồng thật nếu #6 gọi cloud; tài khoản cọc/ký quỹ; policy miễn tiền thuê).
- Review độc lập trước `CHO_ANH_NGHIEM_THU`; anh chỉ xem bảng chấm và bấm thử màn hình danh mục.
