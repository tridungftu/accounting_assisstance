# Báo cáo điều phối chạy đêm 25→26/10/2026 (CD-008)

Lead: phiên Claude Code chính (Opus 5.5). Khung: nhận CD-008 22:25 → giao lát tới 05:30 → báo cáo 05:45. Nhật ký chi tiết từng lát: `TRANG-THAI.md` các mục "Nhật ký lát đêm" (23:37, 00:25, 01:35, cuối đêm).

## §1 Kết luận

1. **Sáng nay Anh kiểm được cổng A trên DEMO cổng 8798** (`http://127.0.0.1:8798/`). Phiếu: `docs\46-chuyen-doi-dieu-phoi\PHIEU-CONG-A-BAO-GIA-LAN-2.md`. Phiếu gồm Báo giá BG-18…24, Dự án đang bán, Mốc thanh toán theo dự án và Trang chủ hệ thống. Phiếu cũ trang chủ lưới icon vẫn dùng được trên cùng DEMO.
2. **CD-006 mục 1 xong:** đã gộp BG-1d + DA-2 vào nhánh hợp nhất. **CD-006 mục 2–4 + CD-007:** phần máy chủ mốc dự án đã gộp nhánh hợp nhất (M0035); phần giao diện nằm trên dòng giao diện `lat/ui-dem`, chờ Anh qua cổng A.
3. **Đã gộp vào nhánh hợp nhất 9 lần** (da-2, AI-3, mốc dự án, M4-5b, BG-e7s, M4-5c/5d, DS-3a, DS-4). **Nền test PostgreSQL v3:** 2433 đạt / 20 lỗi / 66 hỏng / 66 bỏ qua, **0 mã lỗi mới**.
4. **Lát bị dừng:** KY-DOCX (ký trên bản DOCX) dừng theo luật "đỏ 2 lần". Review Opus cho kết quả Đạt; chỗ đỏ là ca test k10 "đua", chưa sửa. Sáng nay sửa 1 ca test là gộp được.
5. **Cần Anh quyết 7 việc** (§4), quan trọng nhất là đường cho hợp đồng ký trên bản chỉ có DOCX được sang Hiệu lực.

## §2 Đã xong

| Khối | Lát (worker) | Commit / nhánh | Test so nền | Gộp |
|---|---|---|---|---|
| CD-006 mục 1 | gộp `lat/da-2` (BG-1d + DA-2) + T-DA2 sửa 2 test (Codex) | 6998a79 | PG cả bộ 0 mã mới (sau T-DA2) | **hợp nhất** |
| Ưu tiên 6 · Cổng AI | AI-3: engine #6 gọi Cloud qua cổng AI, cập nhật 2 băm PIN lõi Review (Codex, 3 vòng) | 30d5478 | thuần 0 mã mới | **hợp nhất** |
| CD-006/007 · máy chủ mốc | MDA-1a (SQL M0035, 2 vòng), 1b (dịch vụ/HTTP/seed), 3s (kiểm mã mốc khi lưu báo giá), 4a (hạn đợt gắn mốc trong danh sách hợp đồng), 5a (quy tắc "+ n ngày" 1–3650), 5b (dự án ngừng bán vẫn hiện mốc) — Codex | 7ce0344 | PG 265 đạt, 0 mã mới | **hợp nhất** |
| Ưu tiên 6 · M4 · Nghiệm thu & chi phí dự án | M4-5b: khối "Đối chiếu căn cứ với hóa đơn" 03B (2 vòng); M4-5c, 5d: câu lỗi, định dạng tiền, đợt cùng hợp đồng; DS-4: che lỗi 500, giờ Việt Nam (Codex) | 3b12e47, 646046c, d0baee2 | PG 170 + 41 đạt, 0 mã mới; node 03B 23/23 | **hợp nhất** |
| BG-22 bản in | BG-e7s: người lập trên bản in không in login (Codex) | 851b73e | thuần 104/113 | **hợp nhất** |
| CD-007 phần nhỏ | DS-3a: mốc ngừng dùng đã có ngày thực tế vẫn tính hạn (Codex) | dd06a08 | PG 64 đạt, 0 bỏ qua | **hợp nhất** |
| CD-005 · Báo giá BG-18…24 | BG-e1 (5 cột %↔Giá trị, chữ to), e2 (nhập nhanh), e3 (nút đầu màn, VND, lỗi mốc + danh sách), e4 (vai mô phỏng tiếng Việt), e5, e6s/u (tên pháp nhân trên nhãn vai), e7 (người lập) — Codex | dòng giao diện `lat/ui-dem` | node giao kết 47/47; PG 0 mã mới | **dòng giao diện** (chờ cổng A) |
| CD-006 mục 1 · lưới CRM | DA-4a/4b: ô thứ 7 "Dự án đang bán" mở thẳng màn; DA-5s: tên dự án thay mã, VND (Codex) | `lat/ui-dem` | khung 33/33 | dòng giao diện |
| CD-006/007 · giao diện mốc | MDA-2 (+2b): mục Mốc thanh toán; MDA-3u: Báo giá gõ `cndt`; MDA-4b: số việc chờ trên icon; MDA-4c: "dự kiến dd/mm/yyyy"; DS-2: icon tính cả dự án ngừng bán (Codex) | `lat/ui-dem` | node dự án 39/39 | dòng giao diện |
| Ưu tiên 5 · UI-3 | UI-3a (`/api/khung/he-thong`), 3b (trang chủ hệ thống), 3c, 3d (không phụ thuộc phiên CRM, M9 Tạm dừng hiện với mọi vai) (Codex) | `lat/ui-dem` | 45/45; khung 33/33 | dòng giao diện (**không gộp UI-1/UI-3** theo CD-008) |
| Ký trên DOCX · giao diện | KY-UI (2 vòng, Codex) | `lat/ky-ui` 15fc909 | node 4/4 bộ | chờ KY-DOCX |
| Test | T-WORD: test chỉ mở Word COM khi bật `KHO_TEST_WORD_THAT=1` (Codex) | `lat/t-pdf` | 62/64 | cùng KY-DOCX |
| DS-1 | Tab Bộ chuẩn không hiện login (Codex) | `lat/ui-dem` | node 4 bộ đạt | dòng giao diện |

**Review Opus đêm (`review-lat`):** 10 lượt — MDA-1a (lần 1 Không đạt vì chuẩn hóa tên mốc phụ thuộc locale C → sửa ở vòng 2), cụm Báo giá, AI-3, KY-DOCX, cụm mốc dự án, dòng giao diện (10 lát), M4-5b, lô 7 lát, lô DS. Không lát nào được gộp khi còn điểm Chặn. **Kiểm nhanh (Haiku):** 3 lượt.

## §3 Chưa xong / bị chặn

- **KY-DOCX** (`lat/t-pdf`): **dừng** theo CD-008 (2 lần đỏ PostgreSQL ở ca k10).
  - Review: Đạt; sản phẩm đúng QD-27.
  - Cách sửa sáng nay: k10 chấp nhận việc G5 ở trạng thái chờ cấu hình và kéo `thu_lai_sau` về quá khứ trước khi nhận việc (`review-ky-docx.md` điểm 1); khi gộp đổi số migration thành **M0036** (MDA đã dùng M0035).
  - KY-UI gộp cùng lúc với KY-DOCX.
- **T-NEN-c2 bị chặn:** `test_source6_lazy_excel` cần bản "candidate" `tools/source6_lazy_excel/master_hd.py` đã duyệt. Không nhánh git nào có bản này, tài liệu giao gốc cũng không có → Cần Anh.
- **T-NEN-a/b/c** (`lat/t-nen-*`): chưa gộp. a, b đã đạt kiểm nhanh và PG; c chờ T-NEN-c2.
- **Dòng giao diện `lat/ui-dem`** (UI-1/UI-3, BG-e, MDA giao diện, DA-4/5): chưa gộp nhánh hợp nhất, chờ Anh qua cổng A. PG cả bộ trên nhánh này (3ddad66, 02:38): 2474 đạt / 20 lỗi / 67 hỏng / 67 bỏ qua · 134 module; 2 mã mới đều ở `test_crm_41_02` (ghim băm tệp test do BG-e4 đổi) → T-UI41 sửa ghim, module 29/29 đạt (87c963c); node 14 bộ đạt.
- **Hàng đợi chưa làm:** AI-4, MASK-3, E1-4 giao diện, BG-2/BG-3 (chờ cổng A gói 1), UI-4 (chờ cổng A UI-1), C3b, M2k.
- **Ghi nhận ngoài lát:** sản phẩm `tools/source6_g5_e5/trich_xuat/danh_muc.py:280` còn xóa tệp rollback; M4 còn dùng Word COM (`m4/review_goc/master_hd.py:114`, `trich_xuat/doc_hop_dong.py:32`).

## §4 Cần Anh quyết

1. **Hợp đồng ký trên bản chỉ có DOCX hiện không sang Hiệu lực được**, vì G5 luôn ở trạng thái chờ. Anh chọn một trong hai:
   - (a) thêm đường "kế toán xác nhận đã kiểm tay G5";
   - (b) nới hợp đồng dữ liệu E5 để nhận mã hash DOCX.

   Kèm: xác nhận "PDF lỗi vẫn được Chờ ký".
2. **Mốc dự án — các mặc định lead đã chọn:**
   - việc chờ "Chỉnh ngày dự kiến" hiện cho vai Bán hàng (chưa có người phụ trách từng dự án);
   - mốc vẫn hiện khi dự án ngừng bán;
   - gõ tắt khớp theo tên tắt đã khai và chữ cái đầu của ≥ 2 từ liền nhau.
3. **Trang chủ hệ thống:**
   - chọn 4 mục cho thanh cố định (tạm: Nhập dữ liệu · CRM · Nghiệm thu & chi phí dự án · Hồ sơ đã nhận);
   - giữ hay bỏ tiền tố "M2 · / M4 ·" trong tên module;
   - M9 "Tạm dừng" hiện với mọi vai.
4. **Danh sách vai mô phỏng dài (~44 dòng):** rút gọn chỉ còn vai CRM trên trang CRM không?
5. **Báo giá USD:** cột "VND quy đổi" đang trùng số với cột Giá trị — giữ hay bỏ? Bằng chữ giữ "đồng" (khớp DOCX) — Anh đồng ý?
6. **`test_source6_lazy_excel`:** Anh có bản candidate lazy Excel đã duyệt không? Không có thì bỏ bộ test này khỏi nền.
7. **M4 03B:** tải tệp căn cứ mới hiện cần quyền phòng dự án (`SOAN`). Kế toán có cần đường tải riêng không?

## §5 Anh kiểm gì lúc 6h

- **DEMO cổng 8798** (CSDL DEMO riêng, không đụng DEMO của Anh): mở `http://127.0.0.1:8798/`.
  - Nếu trang báo "Phiên giao diện đã đổi" → tải lại trang (F5).
- **Phiếu cổng A lần 2** — `PHIEU-CONG-A-BAO-GIA-LAN-2.md`:
  - mục A: Báo giá (ca 26.500.000.000 VND, nhập nhanh 10/30/40/10%, gõ `cndt`);
  - mục B: Dự án đang bán + Mốc thanh toán;
  - mục C: Trang chủ hệ thống.
- **Phiếu cổng A trang chủ lưới icon** (`PHIEU-CONG-A-TRANG-CHU-LUOI-ICON.md`) — cùng DEMO 8798. Lưới CRM nay có 7 ô; nhãn vai có tên pháp nhân.
- Kết luận ghi vào hộp thư chỉ đạo (CD mới), hoặc trả lời trong phiên lead.

## §6 Số liệu

- **Thời gian chạy:** 22:25 nhận CD-008; 22:30–22:55 Claude chạm hạn mức (dừng 25 phút); 22:55 → <ĐIỀN> giao/kiểm/gộp.
- **Worker:** cao nhất 6 cùng lúc (4 Codex + 2 Claude, đúng mức CD-004).
- **Lát Codex:** ~45 commit lát trên các nhánh `lat/*`. **Lát Claude:** 1 (KY-DOCX, Opus).
- **Review Claude:** 10 lượt review Opus + 3 lượt kiểm nhanh Haiku. Vòng review: tối đa 2/lát.
- **Gộp:** 9 lần vào nhánh hợp nhất; ~20 lần vào dòng giao diện `lat/ui-dem`.
- **Test PostgreSQL:**
  - nền v2 2327/21/66/67 → **v3 2433/20/66/66** (hợp nhất 7e9b915, 0 mã mới);
  - node trên nhánh hợp nhất: 11 → 13 bộ đạt.
- **Hạn mức Claude** (`/usage`, 02:05):
  - khung 5 giờ dùng 42% (đặt lại 03:50);
  - khung tuần (mọi model) dùng **76%**;
  - ngữ cảnh phiên lead dùng 70%.
- **Codex:** không chạm hạn mức trong đêm.
