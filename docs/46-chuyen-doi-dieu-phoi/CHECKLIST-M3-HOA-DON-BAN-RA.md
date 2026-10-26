# M3 · Hóa đơn bán ra & doanh thu BĐS — checklist chốt thiết kế

**M3-CL · CD-009 §3d · 26/10/2026 · CHỜ ANH CHỐT · Chỉ soạn, chưa giao code.**

## 1. Phạm vi, nền có sẵn và khoảng thiếu

**Mục tiêu:** nối hóa đơn bán với hợp đồng, nghĩa vụ thu và căn cứ doanh thu; tạo bút toán **đề xuất** có dấu vết để kế toán duyệt. Phạm vi cuối gồm KCN và nhà ở; TL36 xác định PLHN chỉ có bốn loại hình KCN, không gán nhà ở cho pháp nhân này. [S1–S3]

| Checklist phạm vi | Nội dung cần giữ |
|---|---|
| ☐ Đầu vào | XML/ZIP hóa đơn điện tử bán ra qua bộ nhận M2-00; hợp đồng/phụ lục CRM đã duyệt đúng phiên bản; lịch nghĩa vụ thu. Bổ sung biên bản bàn giao thực tế, lịch doanh thu đã tính, căn cứ VAT/giá đất và giá vốn M4 khi áp dụng. |
| ☐ Dữ liệu tối thiểu | Pháp nhân; khóa hóa đơn gồm chiều, MST bán, mẫu, ký hiệu, số; khách/ObjectID; hợp đồng/phiên bản/khóa đợt; dự án; ngày nghiệp vụ, ngày nhận, hiệu lực; tiền tệ, tiền hàng/thuế/tổng; nguồn và phiên bản policy. Thiếu khác 0. |
| ☐ Phễu dùng chung | Nhận nguồn → nhận diện/mapping → đề xuất liên kết → kiểm căn cứ/policy → đề xuất doanh thu/VAT/công nợ → người có quyền duyệt ở K5 → file soát. Khóa cứng trước, các tầng suy luận chỉ gợi ý; Xanh không thay phê duyệt. AI nếu cần chỉ qua cổng AI chung. |
| ☐ Đầu ra | Hồ sơ thiếu/lệch; đề xuất theo mẫu đã duyệt: 131 hoặc tài khoản phải thu phù hợp, 511/3387, 3331; giá vốn khi đủ căn cứ; liên kết tiền M1, dữ liệu thuế M8, lịch đã tính chuyển M10. Nhóm TK là mô tả, phải có tiểu khoản/danh mục hợp lệ mới xuất. |
| ☐ Junsky | Đích cuối: Excel `CB_tmpEntry1/2`, đúng EntryID/EntryDM, đối tượng/dự án. **Mức 2 còn khóa ở UI và máy chủ**; hiện chỉ file soát. Mở mức 2 là cổng riêng: câu trả lời NCC, danh mục, thử 1 → 5 chứng từ và đối chiếu; chốt M3 không mở khóa. |

**Ranh giới:** lịch thu ≠ hóa đơn ≠ tiền về ≠ ghi nhận doanh thu/VAT. Không dựng lại CRM, bộ tải #7, bộ trích #6, engine tính doanh thu nguồn; không ghi sổ thay Junsky. Không lấy ngày thu/xuất hóa đơn làm ngày doanh thu mặc định; không tự phân bổ hợp đồng hoặc giá vốn tổng dự án. [S1–S2]

| Đã có để dùng lại — kiểm tĩnh trong worktree | Còn thiếu/chưa được chứng minh |
|---|---|
| `k2/crm.py`: hợp đồng/phiên bản, kiểm–duyệt V3/V4, `master.lich_thu` với khóa nghĩa vụ, nối/gỡ tiền M1, file soát. `crm_giao_ket.py`, `crm_kiem_hd.py`: luồng từ mẫu/kiểm hiệu lực có guard. | Chưa nối đủ hóa đơn–đợt–bàn giao–doanh thu. CRM không tạo doanh thu/VAT/giá vốn hay file Junsky; G6A còn HOLD khi thiếu bằng chứng G5 vận hành. Không lấy test CRM làm nghiệm thu M3. |
| `nguon/hoa_don_xml.py`, `m2/tai_hoa_don/{manifest,nhan}.py`, `k2/hoa_don.py`: đọc XML/ZIP, khóa hóa đơn, nguồn/hash, nhận theo manifest; có policy tiền tệ và đọc quan hệ liên quan. | Bán ra đang `SOURCE_CANDIDATE`, chưa tạo hồ sơ M3. `BANG_KE` còn giữ chờ K2; bằng chứng tiền tệ/điều chỉnh chưa thành quyết định kế toán. Thiếu đường lưu revision đầy đủ khi đổi bytes/trạng thái cổng. [S4] |
| K2/K5: danh mục, quyền/pháp nhân, liên kết, nhật ký và file chung; đã có binding M3, nền đối chiếu nguồn M2–M4. | Binding là contract, chưa là runtime. `ghi_nhan_chung.py` hiện đối chiếu căn cứ, **không** là engine financial recognition. Cần cơ chế chống ghi nhận trùng dùng chung, nguồn bàn giao/lịch tính/giá vốn, policy, UI và kiểm toàn luồng M3. |

**Căn cứ:** [S1] thư mục `D:\Claude\Phan mem ho tro ke toan\`: `CLAUDE.md`; TL29 §4, TL31–32 (đặc biệt quyết định một nguồn CRM), TL33–38, TL40–43, TL45 — đọc các phần liên quan. [S2] `THIET-KE-MODULE-DE-CHOT-2026-10-20\`: bản M3 §§1–9, CRM, M2/M2-00, M8/M10, danh mục và hàng chờ code. [S3] [Hàng đợi](../../HANG-DOI-YEU-CAU.md), [binding M3](../BINDING-M3-DOANH-THU-SAU-CRM06.md). [S4] [Kế hoạch lead §1b](4-KE-HOACH-LEAD.md), nhất là khoảng thiếu M2c-2, và mã nguồn nêu trên dưới `src/kho_tri_thuc/`. Kế hoạch 24–25/10 mới hơn trạng thái hàng đợi lịch sử; không coi mọi mục “đã chốt” là đã nghiệm thu.

<div style="page-break-after: always;"></div>

## 2. Bảng câu hỏi để Anh chọn — 15 câu

**Cách chốt:** ghi `Q01=A…`; **★ là khuyến nghị, chưa được chọn thay Anh**. Với mỗi policy cần thêm tên tài liệu/mẫu, hiệu lực, người chịu trách nhiệm. Đây là lựa chọn thiết kế theo nguồn nội bộ, không xác nhận quy định thuế hiện hành; kế toán trưởng xác nhận căn cứ trước khi kích hoạt. Giữ nguyên các quyết định CRM/M2 đã chốt.

| Mã · Anh quyết định | Phương án và hệ quả | Chọn |
|---|---|---|
| Q01 · Luồng ưu tiên | **A★ KCN trước** → tận dụng PLHN; nhà ở làm sau. **B Nhà ở trước** → cần pháp nhân/policy riêng. **C Cùng đợt** → tăng mẫu và công kiểm. | … |
| Q02 · Thời điểm doanh thu nhà ở | **A★ Bàn giao thực tế đủ điều kiện** → cần biên bản/phần bàn giao. **B Thu tiền** hoặc **C Xuất hóa đơn** → chỉ xem xét nghiệp vụ có policy hợp lệ xác nhận; không dùng tiền/hóa đơn thay bằng chứng. Thiếu policy: chờ. | … |
| Q03 · Doanh thu định kỳ KCN | **A★ Nhận lịch đã tính, đã xác nhận** → M3/M10 cùng nghĩa vụ, không tính lại. **B Nhận bảng kỳ đã duyệt** → bổ sung mỗi kỳ. Cả hai cần cơ sở, kỳ, số tiền, phiên bản. | … |
| Q04 · Nguồn bàn giao | **A★ Bảng sự kiện + biên bản ký** → kinh doanh/dự án xác nhận ngày, căn/lô/phần. **B Kết quả hệ thống nguồn** → kiểm interface trước. **C Nhập hồ sơ kèm biên bản** → nhanh thí điểm, nhiều công kiểm. | … |
| Q05 · Hóa đơn ↔ hợp đồng ↔ đợt | **A★ Gợi ý theo khóa mapping, người xác nhận** → đúng pháp nhân/khách/phiên bản/đợt; mơ hồ chờ. **B Chọn tay** → nhiều thao tác. **C Thêm gợi ý nội dung/tiền** → cần chấm chất lượng; bằng tiền không chứng minh khớp. | … |
| Q06 · Nối nhiều–nhiều/từng phần | **A★ Nối phần có căn cứ** → tách tiền hàng/VAT/cọc/phí, giới hạn hai phía/phần còn lại. **B Đợt đầu chỉ 1–1** → nhanh hơn, ngoại lệ chờ. Không tự chia hoặc đặt dung sai. | … |
| Q07 · VAT, giá đất được trừ | **A★ Bảng cơ sở tính do kế toán thuế xác nhận** → giữ giá chuyển nhượng, đất được trừ, phần áp dụng, thuế suất/thuế, nguồn/hiệu lực; lệch XML thì chờ. **B Chỉ nhận VAT XML** → chưa xác nhận đủ căn cứ BĐS. Không tự suy tỷ lệ đất. | … |
| Q08 · Điều chỉnh/thay thế/hủy | **A★ Nối gốc, kiểm tác động, đề xuất theo mẫu** → giữ tăng/giảm; thay thế không ghi toàn bộ lần hai; bảo toàn nguồn/file cũ, xử lý kỳ khóa riêng. **B Chỉ nhận/cảnh báo trước** → kế toán xử lý ngoại lệ, chưa khép nhánh. | … |
| Q09 · Tiền trước hóa đơn chưa rõ khoản | **A★ Chờ xác minh** → giữ quy tắc CFO về cọc/đợt, không suy doanh thu. **B Phân loại ngay khi bổ sung đủ căn cứ** → nhanh hơn, lưu lý do. Cả hai nối tiền M1 cũ, không thêm BANK/112. | … |
| Q10 · Nhiều pháp nhân | **A★ Thí điểm một, kiến trúc tách pháp nhân** → giảm rủi ro; test thêm pháp nhân DEMO. **B Hai pháp nhân ngay** → cần đủ profile/danh mục/policy hai bên. Không nối công nợ chéo pháp nhân. | … |
| Q11 · Ai duyệt M3? | **A★ Kế toán duyệt V1, KTT/CFO duyệt policy/ngoại lệ** → chốt tên/vai và ngoại lệ. **B CFO duyệt tất cả giai đoạn đầu** → kiểm tập trung, chờ lâu hơn. Duyệt CRM không thay duyệt bút toán; không tự duyệt vì khớp. | … |
| Q12 · Mẫu TK/danh mục | **A★ KTT cấp bộ mẫu theo pháp nhân/loại hình/hiệu lực** → kiểm ObjectID, dự án, TK chi tiết. **B Chọn mẫu đã duyệt từng hồ sơ** → linh hoạt, nhiều thao tác. Giữ khác biệt phải thu TL36, không gom hết vào 131. | … |
| Q13 · Ngoại tệ, thu VND | **A★ Có bảng quy đổi xác nhận mới đề xuất** → giữ hai đồng tiền/tỷ giá/cơ sở; thiếu chờ. **B Chỉ làm hồ sơ, hoãn đề xuất** → kế toán xử lý trước. CRM nối tiền hiện nhận số nguyên VND; không mặc định tỷ giá báo giá. | … |
| Q14 · Từng phần/thiếu giá vốn | **A★ Phạm vi đủ căn cứ được duyệt riêng** → thiếu M4 thì giá vốn chờ, cảnh báo phần chưa hoàn tất. **B Chờ đủ cả doanh thu/giá vốn** → chặt hơn, có thể chậm kỳ. Phải định danh phần; không tự chia giá vốn. | … |
| Q15 · Màn hình/file soát | **A★ Đủ cột**: pháp nhân, HĐ/đợt/hóa đơn, bàn giao, doanh thu/VAT/công nợ, tiền nối, thiếu/lệch, người duyệt → kiểm trực tiếp. **B Ngoại lệ + mở chi tiết** → gọn hơn, vẫn đủ nguồn/tổng kiểm soát. Dùng K5 chung. | … |

<div style="page-break-after: always;"></div>

## 3. Chia lát sau khi chốt — chưa phải lệnh triển khai

**Cổng trước code:** Anh chọn phương án → chủ nguồn cấp mẫu DEMO và policy → chốt màn hình → chốt schema/binding theo code hiện hành → lead lập handoff đúng danh sách tệp. Không yêu cầu tiếp tục M9; phần common còn thiếu phải thành lát nền riêng. Chưa đủ policy vẫn chuẩn bị hồ sơ chờ, không gọi đó là M3 hoàn chỉnh.

Mỗi lát **3–5 tệp tổng cộng, gồm test/fixture**. Tên mới dưới đây là dự kiến (`m3/…` dưới `src/kho_tri_thuc/`, test dưới `tests/`), chưa tạo tệp hay đặt số migration. Nếu vượt hạn, lead tách lát trước khi giao; không thêm file ngoài handoff.

| Thứ tự · lát dự kiến | Phạm vi và ngân sách tệp | Điều kiện xong/rủi ro chính |
|---|---|---|
| 1 · M3-N1 Nền nguồn chung | 5 tệp: bộ nhận `nhan.py`, dịch vụ hóa đơn `hoa_don.py`, **1 tệp SQL chung**, `ha_tang/pg_migrations.py`, 1 test. Bổ sung revision/bằng chứng/quan hệ còn thiếu của M2c-2. | Cùng khóa nhận lại không nhân đôi; đổi nguồn/trạng thái hiện phiên bản; bảng kê không giả XML. Review tác động M2/M8; khóa file chung với lead. |
| 2 · M3-N2 Nền ghi nhận chung | 3–5 tệp: dịch vụ và SQL common hiện hành, đăng ký migration nếu cần, 1–2 test. Xác định sự kiện/phần đã ghi nhận và điều chỉnh dùng chung theo binding đã cập nhật. | Nền đối chiếu M2–M4 chưa đủ financial recognition. Không dựng engine ghi nhận riêng M3; phải chứng minh không trùng với nguồn/lô cũ trước khi mở đề xuất. |
| 3 · M3-HS Hồ sơ và đối chiếu | 4 tệp: `m3/ho_so.py`, `m3/doi_chieu.py`, 1 test, 1 fixture DEMO. Đọc CRM, ứng viên bán ra và nguồn bàn giao/lịch tính; báo thiếu/lệch. | Chốt Q04–06; đúng phiên bản/pháp nhân; 1–n/n–1 và nguồn đến khác thứ tự vẫn cùng hồ sơ. Cần thêm storage thì tách lát SQL 3–5 tệp trước. |
| 4 · M3-DX Đề xuất luồng ưu tiên | 4 tệp: `m3/de_xuat.py`, 1 tệp cấu hình policy/mẫu, 1 test, 1 fixture. Áp cơ chế common N2 cho doanh thu/VAT/công nợ; nhận giá vốn M4 đúng phạm vi. | Q02–03, Q07, Q11–14 đủ căn cứ; cân Nợ/Có, TK chi tiết, lineage và phần còn lại. Luồng nhà ở/KCN còn lại giao lát tương tự sau, không bỏ phạm vi. |
| 5 · M3-DC Ngoại lệ và sửa đổi | 4 tệp: `m3/dieu_chinh.py`, `m3/ho_so.py`, 1 test, 1 fixture. Hóa đơn điều chỉnh/thay thế, phụ lục, bàn giao từng phần, nguồn đổi sau duyệt. | Giữ lịch sử; kiểm lại quyết định cũ; kỳ khóa/file đã xuất đi quy trình điều chỉnh. Chống ghi cả giá trị thay thế như doanh thu mới. |
| 6 · M3-GD Màn làm việc/K5 | 5 tệp: `giao_dien/m3.py`, `giao_dien/server.py`, `assets/m3.js`, 1 tệp shell hiện hành, 1 test route/quyền. | Q15 và bố cục được duyệt; thao tác thiếu căn cứ bị chặn có lý do; thu hồi quyền vẫn chặn tải. Dùng shell/CSS chung; nếu cần sửa thêm phải tách lát. |
| 7 · M3-XL File và liên module | 4 tệp: `m3/xuat.py`, `m3/lien_module.py`, 1 test, 1 fixture. File soát, chuyển lịch đã tính sang M10 và dữ liệu bán ra sang M8; chuẩn bị mapping file mức 2. | M3/M10 không ghi nhận cùng nghĩa vụ hai lần; M1 giữ nguyên tiền đã ghi. File soát tải được, kiểm ô/số; đường xuất nhập Junsky vẫn bị khóa. |

**Checklist nghiệm thu bằng DEMO sau này:** ☐ nhà ở/KCN đủ căn cứ; ☐ thu trước nhưng chưa bàn giao không tự ghi doanh thu; ☐ hóa đơn/bàn giao/tiền đến mọi thứ tự và nhận lại không trùng; ☐ chia phần, VAT/giá đất thiếu hoặc lệch; ☐ điều chỉnh/thay thế sau duyệt/xuất/kỳ khóa; ☐ đúng/sai quyền và pháp nhân; ☐ ngoại tệ, số lớn, NULL/0; ☐ M1/M3/M10 dùng cùng nghĩa vụ, không thêm tiền/ghi nhận; ☐ tải file/mở lại giữ nguồn và người duyệt. Test theo lát, lỗi mới so [NEN-TEST.md](NEN-TEST.md) bằng 0; review contract không thay kiểm runtime.

**Phiếu chốt:** lựa chọn Q01–Q15: … · policy/mẫu và chủ nguồn: … · người duyệt/ngoại lệ: … · [ ] Chốt [ ] Sửa [ ] Để sau · ngày: … . Phần hoãn vẫn trong lộ trình M3. **Lát M3-CL chỉ tạo tài liệu này; không chạy test sản phẩm, không commit.**
