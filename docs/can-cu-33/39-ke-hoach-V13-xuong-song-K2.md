# 39 · Kế hoạch V13 — xương sống K2: PostgreSQL, lớp dữ liệu, bộ chuyển (để anh ra lệnh code)

**Ngày lập:** 16/10/2026 · **Trạng thái:** chờ anh ra lệnh code (bảng chọn §9) · **Hàng đợi:** #23 (kho dữ liệu chung K2) · #26 (cài PostgreSQL) · #29 (schema TL 38) · chuẩn bị bảng cho #18 (liên kết) và #28 (việc cần duyệt).
**Căn cứ:** TL 35 (kiến trúc), 36 (bối cảnh), 37 (màn hình), 38 (schema) — đều đã chốt 16/10; tiêu chuẩn nội bộ (TL 31; CLAUDE.md): một V một đợt, test đi kèm, review độc lập cuối V, CHANGELOG có số đo trước/sau, không đụng kho thật khi chưa đạt.
**Nguyên tắc V13:** *đổi nền dữ liệu mà không đổi hành vi* — V12 chạy trên PostgreSQL phải cho **đúng kết quả** V12 trên SQLite (từng dòng T8), rồi mới xây tiếp K3/K5 trên nền mới.

---

## 0. Mục tiêu một câu
Sau V13, phần mềm chạy trên **PostgreSQL với 4 schema theo TL 38**, dữ liệu V12 đã chuyển sang đủ và đúng (số đếm trước/sau khớp), kết quả đề xuất T8 không đổi, kho thật vẫn an toàn (có công tắc quay về SQLite).

## 1. Phạm vi

| Có trong V13 | Không trong V13 (V sau) |
|---|---|
| Cài PostgreSQL trên máy anh (#26), CSDL `kho_tri_thuc`, 4 schema `master` · `kho` · `nhat_ky` · `bao_mat`, vai trò ứng dụng, mở rộng `unaccent` · `pg_trgm` · `pgcrypto` | Bộ lọc tri thức K3 mới (nhận diện – liên kết – định tuyến) → **V14** |
| Migration có số phiên bản (0001…) tạo **đủ bảng TL 38** — kể cả bảng chưa dùng (`viec_can_duyet`, `cau_hoi`, `lo_xuat`…) để V14+ không phải đổi schema | Màn hình duyệt chung K5 (TL 37) → **V14/V15** |
| **Bộ chuyển** `kho.sqlite` → PostgreSQL theo ánh xạ TL 38 §6; chạy lại được; bảng đối chiếu số đếm | Cổng AI, Mask, bối cảnh gửi cloud → **V15** |
| **Lớp truy cập dữ liệu** chung: lõi V12 (sao kê + hóa đơn) đọc/ghi qua một lớp, cấu hình `[storage] engine = sqlite | postgres`; mặc định kho thật **vẫn SQLite** đến khi nghiệm thu | CRM hợp đồng (#20, #21), M4, M9 → **V16+** |
| Nhật ký `su_kien` bắt đầu ghi mọi Đồng ý/Sửa/Bỏ qua/Hoàn tác (thay `activity_log`) | Mức 2 file nhập Junsky — vẫn khóa |
| Test: 258 test hiện có chạy xanh trên **cả hai** engine + test mới (migration, bộ chuyển, ràng buộc §7 TL 38) | Agent Zalo |
| Sao lưu `pg_dump` theo lịch vào `var\sao-luu\` | Phân quyền nhiều người (#16) — chỉ tạo bảng |

## 2. Các bước và sản phẩm của từng bước

| # | Bước | Ai | Sản phẩm | Kiểm tra xong bước |
|---|---|---|---|---|
| 1 | Sao lưu kho thật và mã: `var\sao-luu-truoc-V13-yyyymmdd\`, ghi hash | Codex | thư mục sao lưu + `HASH.txt` | hash khớp |
| 2 | **Cài PostgreSQL 16 trên máy anh** bằng `winget` (Codex chạy; Windows hỏi quyền quản trị **một lần** — anh bấm "Yes"); mật khẩu sinh ngẫu nhiên ghi vào `.env` (không vào mã, không vào git) | Codex + anh bấm 1 lần | dịch vụ PostgreSQL chạy, cổng chỉ `127.0.0.1` | `pg_isready` đạt; CSDL UTF-8, collation `vi` |
| 3 | Tạo CSDL, 4 schema, vai trò `app_ke_toan` (đọc/ghi master+kho, chỉ INSERT nhat_ky, không thấy bao_mat) · `app_cong_ai` (đọc bao_mat) · `app_doc` (chỉ đọc); migration 0001–000n theo TL 38 | Claude (mô hình mạnh nhất) | `src/kho/migrations/*.sql`, bảng `schema_migrations` | mọi bảng có `phap_nhan_id`; `REVOKE UPDATE/DELETE` trên nhat_ky; 10 ràng buộc TL 38 §7 có test |
| 4 | **Bộ chuyển** SQLite → PostgreSQL (chạy trên bản sao, idempotent, báo cáo số đếm từng bảng trước/sau, hash `core_json` → `du_lieu`) | Claude | `tools/chuyen_sqlite_sang_pg.py` + `docs/BAO-CAO-V13.md` mục "Chuyển dữ liệu" | 8.121 documents → `chung_tu`+danh mục đúng số; 20.382 dòng; 2.027 đối tác; 1.581 công nợ; 7.848 tri thức; 105 sao kê T8; 0 bản ghi mất |
| 5 | **Lớp truy cập dữ liệu** (repository) cho lõi V12: cùng hàm, hai engine; cấu hình `[storage]`; kho thử T8 trỏ PostgreSQL, kho thật giữ SQLite | Codex (lớp Sonnet) theo đặc tả Claude | `src/kho/storage/{sqlite,postgres}.py` | 258 test xanh ở cả hai engine |
| 6 | **Chạy song song T8**: đề xuất sao kê (105) và hóa đơn (75) trên PG so với SQLite **từng dòng** (mức, TK, đối tượng, dự án); thời gian đề xuất | Codex | `docs/BAO-CAO-V13.md` mục "Song song" + file so sánh | 180/180 dòng giống; thời gian ≤ 10 s cho 105 dòng (V10: 7–9 s) |
| 7 | **Review độc lập** bởi agent chưa thấy quá trình, theo checklist §4 | Claude (agent riêng) | mục "Review độc lập" trong báo cáo | 0 lỗi chặn |
| 8 | Bàn giao: CHANGELOG dòng V13 (số đo trước/sau), HANG-DOI cập nhật (#23 #26 #29 → Xong V13), hướng dẫn "chuyển kho thật sang PostgreSQL" = đổi một dòng cấu hình + bấm Nạp lại; `MỞ PHẦN MỀM.cmd` không đổi | Claude | CHANGELOG, HANG-DOI, báo cáo | anh bấm mở phần mềm, thấy thanh trên ghi "PostgreSQL · kho thử" |

Việc của anh trong V13: **bấm "Yes" một lần** khi Windows hỏi quyền cài PostgreSQL; đọc `docs/BAO-CAO-V13.md`; quyết chuyển kho thật sang PostgreSQL khi số đo đạt. Không gõ lệnh.

## 3. Tiêu chí nghiệm thu (có số đo — ghi vào CHANGELOG)

| Tiêu chí | Trước (V12) | Sau V13 phải đạt |
|---|---|---|
| Test tự động | 258/258 (Py 3.13, 3.11) | ≥ 258 + test mới, xanh trên **cả SQLite lẫn PostgreSQL** |
| Chuyển dữ liệu | — | số đếm từng bảng khớp 100%; hash dữ liệu bóc tách khớp; chạy lại lần 2 không tạo trùng |
| Kết quả đề xuất T8 sao kê (105 dòng) | Xanh/Vàng/Đỏ 41/52/12 (V11, học đến 30/06) | **giống từng dòng** trên PostgreSQL |
| Kết quả đề xuất T8 hóa đơn (75) | Bán ra 11/20/5 · Mua vào 0/22/17 | giống từng dòng |
| Thời gian đề xuất 105 dòng | 7–9 s | ≤ 10 s |
| Nhật ký | `activity_log` | mọi thao tác duyệt → `nhat_ky.su_kien` có trước/sau; thử UPDATE/DELETE bị từ chối |
| Bảo mật | — | `bao_mat` không đọc được bằng vai trò kế toán; STK/CCCD trong master mã hóa cột; không dữ liệu thật trong `tests\fixtures` (chỉ DEMO) |
| Quay lui | — | đổi `engine = sqlite` → phần mềm chạy lại như V12 trong 1 phút |

## 4. Checklist review độc lập (agent chưa thấy quá trình)
1. Schema khớp TL 38 §2–§4b: tên bảng, trường bắt buộc, khóa duy nhất, `phap_nhan_id`.
2. `nhat_ky.*` không thể UPDATE/DELETE với mọi vai trò ứng dụng (thử thật).
3. Ràng buộc §7 TL 38 (Nợ = Có, TK chi tiết, TK công nợ cần mã đối tượng, trích dẫn LLM, LLM ≤ Vàng, một đề xuất một lô) có test và test thất bại đúng khi vi phạm.
4. Bộ chuyển: số đếm, hash, chạy lại idempotent; không bỏ sót `OPEN_ITEM`, `COUNTERPARTY` có nhiều mã Junsky.
5. Không có mật khẩu/khóa trong mã, trong git, trong tài liệu; `.env` nằm ngoài git.
6. Kết quả T8 giống từng dòng; thời gian đạt.
7. Dữ liệu thật không rời `var\`; fixture chỉ DEMO; báo cáo chỉ số đếm.

## 5. Rủi ro và cách chặn

| Rủi ro | Chặn |
|---|---|
| Cài PostgreSQL trên Windows thiếu quyền / xung đột cổng | winget bản chính thức; cổng 5432 chỉ 127.0.0.1; nếu cổng bận → 5433 ghi `.env`; kiểm `pg_isready` trước mọi bước |
| Tiếng Việt lệch (collation, unaccent) khi so tên | CSDL `UTF8`, collation `vi-x-icu`; test so tên viết tắt (bảng D3 TL 25) trên cả hai engine |
| Khác biệt SQL giữa SQLite và PostgreSQL làm lệch kết quả | lớp truy cập dùng một bộ truy vấn chung đơn giản + test "song song từng dòng" (bước 6) là cổng bắt buộc |
| Chậm hơn SQLite | chỉ mục theo khóa nguồn, `pg_trgm` trên `ten_chuan_hoa`; ngưỡng 10 s là tiêu chí |
| Sao lưu | `pg_dump` hằng ngày vào `var\sao-luu\` + giữ SQLite làm bản sao chỉ đọc đến hết V14 |
| Mất kho thật | kho thật **không chuyển** trong V13; chỉ kho thử; chuyển kho thật là quyết định riêng của anh sau khi đọc báo cáo |

## 6. Phân công và model (theo CLAUDE.md)
- **Claude — mô hình mạnh nhất:** đặc tả lớp truy cập, migration SQL, bộ chuyển, review độc lập (agent riêng), báo cáo.
- **Codex / lớp Sonnet:** cài PostgreSQL bằng winget, lớp truy cập hai engine theo đặc tả, test, chạy song song, sao lưu.
- **Lớp Haiku:** script hash/sao lưu, so sánh file.
- **Anh:** bấm "Yes" một lần; đọc báo cáo; ra lệnh chuyển kho thật.

## 7. Ước lượng
Ba đến bốn phiên làm việc (ước, không cam kết): phiên 1 bước 1–3; phiên 2 bước 4; phiên 3 bước 5–6; phiên 4 bước 7–8. Mỗi phiên kết thúc bằng một mục trong `docs/BAO-CAO-V13.md` để anh theo dõi.

## 8. Lộ trình các V tiếp theo (để thấy V13 nằm đâu)

| V | Nội dung | Căn cứ |
|---|---|---|
| **V13** | Xương sống K2: PostgreSQL + schema + bộ chuyển + lớp truy cập (tài liệu này) | 35, 38 |
| V14 | K3 bộ lọc tri thức trên nền mới: `lien_ket_chung_tu` (#18), `viec_can_duyet` V1–V2, nhận diện theo tên/định danh dùng chung; màn hình K5 bản 1 (danh sách gộp, nút Hỏi chưa gửi) theo prompt Claude Design v2 | 34, 37 |
| V15 | Cổng AI: Mask bảy thứ, `bao_mat`, bối cảnh PLHN rút gọn theo loại việc, đáp án mẫu, nhật ký `cong_ai_goi`; agent Zalo thử nghiệm (#5) | 35 §3, 36 |
| V16 | CRM kế toán: #6 mở rộng cho thuê đất KCN, tham số có trích dẫn, `hop_dong_*`, `lich_thu`, CFO duyệt (V3) (#20, #21); CFO-03 vào JSON (#19) | 32, 36 §2.4 |
| V17+ | M4 · Nghiệm thu & chi phí dự án (#6 hàng đợi) → M9 · Vốn vay (#7) → M8 · Bảng kê thuế (#13); mức 2 khi 3 câu Junsky có trả lời (#9) | 29, 31 |

## 9. Lệnh code
Anh chọn ở bảng chọn: **"Ra lệnh code V13 theo tài liệu 39"** → Claude ghi vào hàng đợi (#23 #26 #29 → "Đang làm V13"), lập `docs/BAO-CAO-V13.md` mục 0 (kế hoạch), rồi bắt đầu bước 1. Mọi bước đều có thể dừng; dừng ở đâu cũng không ảnh hưởng kho thật.
