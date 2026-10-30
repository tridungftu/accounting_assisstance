# Review Opus — CONTRACT-NGHIEP-VU.md: quy tắc chung + 3 contract cốt lõi (CD-031 mục 5), 30/10/2026

**Kết luận: chưa gửi Anh — 2 Chặn**, cả hai sửa trong tài liệu, không cần hỏi Anh. Mọi số trong ví dụ đã cộng lại bằng tay, đều khớp. Số dòng không ghi tệp là dòng trong `CONTRACT-NGHIEP-VU.md` bản nháp đầu.

| # | Câu hỏi | Kết luận | Lý do |
|---|---|---|---|
| 1 | Quy tắc chung | Cần sửa | Hướng đúng: dùng lại → mở rộng → tạo mới; đặt tên; phiên bản bất biến; Anh duyệt; trùng nghĩa = đỏ. Thiếu tiêu chí máy phát hiện trùng nghĩa (S1); vỏ chung áp không đồng đều (C1). |
| 2 | `hop_dong_ban` | **Chặn** | Vỏ chung (C1); khóa đợt nối tiền lệch phiếu CSDL (C2). VAT đúng CD-024. Số ví dụ đúng:<br>• 100.000.000 + 340.000.000 + 660.000.000 = 1.100.000.000;<br>• VAT 0 + 40.000.000 + 60.000.000 = 100.000.000;<br>• Σ% = 100. |
| 3 | `dot_thanh_toan` | Cần sửa | Số đúng (110.000.000 − 5.500.000 − 11.000.000 = 93.500.000). Thiếu cơ sở VAT và các số đã được review xác nhận (S4). |
| 4 | `but_toan_de_xuat` | Cần sửa | Đã có: Nợ = Có, TK chi tiết, thiếu mã đối tượng thì chặn xuất, không có cờ tự khai `da_duyet`. Thiếu:<br>• bất biến "LLM không được Xanh";<br>• ràng buộc tiền;<br>• phiên bản hiện hành;<br>• Mức 2 và tự duyệt (S5). |
| 5 | Trường bịa / dữ liệu thật | Đạt | DEMO, UUID giả. Nguồn khớp (`ha_tang/pg_migrations.py:501-549`, `m4/sql_duyet.py:30,194-227`, `m4/sql_review_chep.py:145-163`). |

## Chặn

- **C1 – Vỏ chung không thống nhất.**
  - `vo_noi_dung` bắt buộc `nguon_tep_ids` ≥ 1 (`CONTRACT-DU-LIEU.md:131,136-139`). Chung/M4 có; 3 contract CRM không có.
  - `hop_dong_ban` dùng trường riêng `tep_nguon` (526; ví dụ 618-728) → ví dụ CRM sẽ đỏ ở bộ kiểm. Dòng 464 mới kiểm "parse được", chưa kiểm schema.
  - **Sửa:**
    - quy tắc chung ghi mọi contract dữ liệu công bố kế thừa `vo_noi_dung`, kèm cách làm khi dữ liệu nhập tay không có tệp nguồn (`bao_gia`, `du_an_dang_ban`);
    - thêm `nguon_tep_ids` vào CRM;
    - bỏ `tep_nguon` hoặc ghi rõ khác nghĩa.
- **C2 – Khóa đợt nghĩa vụ để nối tiền lệch phiếu CSDL đã duyệt.**
  - Phiếu CSDL trỏ nghĩa vụ bằng bộ ba `(module_nghia_vu, loai_nghia_vu, nghia_vu_id)` + ID và mã băm phiên bản (`DAC-TA-CSDL.md:250,387`).
  - `hop_dong_ban` có 3 khóa (`dong_id`, `nghia_vu_id`, `khoa_nghia_vu`, 583-585) nhưng không nói khóa nào là `nghia_vu_id`, không khai `loai_nghia_vu`.
  - Sự kiện `tien_da_noi_dot` dùng tên thứ tư `lich_thu_id` (293).
  - `ban.ma_bam` (538) chưa định nghĩa băm nội dung gì.
  - **Sửa:**
    - một tên duy nhất cho ID đợt, thống nhất contract / sự kiện / liên kết;
    - `loai_nghia_vu` là hằng;
    - định nghĩa đầu vào mã băm.

## Cần sửa (ưu tiên)

- **S1 – Quy tắc chung (448-462).** Để "lệch là đỏ" chạy được bằng máy:
  - (a) Mỗi contract khai rõ một dòng dữ liệu là gì và khóa dòng. Hai chủ khác nhau khai cùng loại dòng với cùng khóa → đỏ.
  - (b) **Từ điển trường dùng chung:** cùng tên thì cùng kiểu / rỗng / đơn vị. Đang lệch:
    - `so_hop_dong`: CRM cho rỗng (514), M4 bắt buộc (1070);
    - thuế suất: CRM `thue_suat` chuỗi danh mục (570), M4 `vat` số thập phân (1077).
  - (c) Contract khai bất biến tiền để Core tự kiểm: Σ đợt = tổng gồm VAT, Σ VAT, Σ% = 100, Nợ = Có, cùng `don_vi_tien`.
  - (d) Mỗi trường tiền nêu cơ sở VAT và thang làm tròn (`CONTRACT-DU-LIEU.md:67` giao việc này cho lớp nghiệp vụ).
  - (e) Tham chiếu chéo module ghim ID + mã băm, không lấy bản mới nhất (`DAC-TA-CSDL.md:366`).
  - (f) Câu "lát này không tự đặt khóa manifest mới" (458) đã lỗi thời. Manifest đã có `contract.{cong_bo, su_kien_phat, su_kien_nhan, dau_vao_nguon}` (`CONTRACT-DU-LIEU.md:1483-1491`) → dẫn sang đó.
- **S2 – Ranh giới với `danh_muc.hop_dong`.**
  - Định danh hợp đồng chung ở `danh_muc` (`DAC-TA-CSDL.md:380`), nhưng phần Chung không có contract cho nó. Hệ quả: CRM và M4 tự định nghĩa `so_hop_dong`, `doi_tuong_id`, `du_an_id` → trùng nghĩa theo chính quy tắc 7.
  - **Sửa tối thiểu:** ghi các trường này là "chiếu từ `danh_muc.hop_dong`" (V3), cùng kiểu cả hai phía.
- **S3 – `hop_dong_ban`.**
  - Thiếu `loai_khoan` của nghĩa vụ (thiết kế CRM §6, dòng 78).
  - Thiếu `phi`: `bao_gia` có `phi`, chuyển sang Soạn giữ nguyên báo giá nên phí bị mất.
  - Số ngày sau mốc nằm trong chuỗi `su_kien` (601) mà quy tắc 4 (613) cần để tính hạn → tách thành trường số nguyên.
  - "Chênh làm tròn dồn đợt cuối" chưa nêu thang (VND làm tròn đến đồng).
- **S4 – `dot_thanh_toan`.**
  - (a) Thiếu cơ sở VAT: khối lượng 10 × đơn giá 10.000.000 = 100.000.000 nhưng `gia_tri_ky_nguon` = 110.000.000 (1278, 1286-1288). Thêm `co_so_gia_tri` như `nghiem_thu` (1380).
  - (b) Kết luận review đã có `gia_tri_nt`, `tam_ung`, `thu_hoi`, `giu_lai`, `tien_te`, `revision`, `graph_sha256` (`m4/sql_duyet.py:30,201-207`); contract chỉ công bố `so_xin_thanh_toan_xac_nhan`. Thiết kế M4 §3 yêu cầu tạm ứng / thu hồi / giữ lại tách riêng → thêm các số này kèm revision + mã băm để bên nhận ghim kết luận.
- **S5 – `but_toan_de_xuat`.**
  - (a) Thêm `nguon_suy_luan` + bất biến "đề xuất từ LLM không được mức Xanh" (`pg_migrations.py:514,519`).
  - (b) `so_tien`: kiểu tiền chung cho âm và 6 số lẻ, còn nguồn là số nguyên VND ≥ 0 (`pg_migrations.py:532-533`). Bản 1: > 0, số nguyên VND, mọi dòng cùng đơn vị.
  - (c) Thiếu phiên bản và cờ hiện hành của đề xuất (`pg_migrations.py:504-505`); dòng 164 yêu cầu "chỉ xuất phiên bản đã Đồng ý, còn hiệu lực".
  - (d) Ghi rõ bên xuất đọc trạng thái ở đâu; payload tự kèm trường duyệt → Core từ chối.
  - (e) Mức 2 khóa ở máy chủ. Tự duyệt chỉ cho 4 loại đã chốt, chỉ khi Mức 2 mở, có nhật ký. Mức Xanh ≠ tự duyệt.
  - (f) `ma_doi_tuong` = `doi_tuong.v1.ma_junsky` đúng pháp nhân; `chu_trinh` do Core gắn theo module phát, module không tự khai.

## Để sau

- `bank_id`, `cashflow_id`, `entry_dm` có trong nguồn (`pg_migrations.py:527,535-536`), chờ nhà cung cấp Junsky.
- M1 nối khoản chi vào đợt M4 cần bộ ba `(M4, loại, dot_id)`.
- TL 50 không có ở thư mục cha: lead xác nhận trước khi phiếu ghi "trường lấy từ TL 50".
- Ký hiệu kiểu không đồng nhất (`id` và `chung.id`).

## Câu nên hỏi Anh (phiếu SDK bản 2)

1. **Phí trong lịch nghĩa vụ hợp đồng bán bản 1:** gồm cả phí (bảo trì, sử dụng hạ tầng…) hay chỉ tiền giá bán chia theo %? Câu trả lời quyết định có thêm `loai_khoan`/`phi` không, và Σ% = 100 áp cho phần nào.
2. **VAT cọc khi đợt cọc ở dòng cuối hoặc có nhiều dòng cọc:** dồn vào đâu? `bao_gia` đã ghi chờ Anh (844); áp chung cho `hop_dong_ban`.
