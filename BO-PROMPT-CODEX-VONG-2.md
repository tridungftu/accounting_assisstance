# Bộ prompt Codex — Vòng 2: từ fixture sang dữ liệu thật PLHN

Ngày 18/09/2026 · Dùng sau khi đọc `var\thu-nghiem-claude-2026-09-18\BAO-CAO-CHAY-THU-CODEX.md`. Bộ này **bổ sung** `BO-PROMPT-CODEX.md` (vòng 1), không thay thế: Quy ước chung vòng 1 vẫn áp dụng, trừ các điểm nới rõ ở mục "Quy ước bổ sung".

## Cách dùng

1. Giao **V0** trước (kiểm kê, chưa code). Sau khi Anh duyệt phương án V0, giao **một prompt V1–V6 mỗi lần**, đúng thứ tự. Dùng **R1** ở cổng nghiệm thu vòng 2.
2. **Thứ tự cố ý:** V1 (máy đề xuất) và V2 (hợp đồng dữ liệu) làm trước và kiểm chứng ngay bằng bộ chạy thử JSON tháng 8 — chưa cần bộ đọc thật. V3 (bộ đọc thật) chỉ có giá trị khi máy đề xuất đã dùng được bộ quy tắc. V4–V6 sau đó.
3. **Hồ sơ tháng 08/2026 là lát cắt chạy thử thật, giữ nguyên:** sao kê `Sao kê NH T08.xls`, hóa đơn XML/bảng kê 2026-08, sổ và file nhập Junsky T8, tập chuẩn T8. Không sửa, không đổi thành fixture, không đặt `synthetic=true` cho bản gốc. Mọi prompt V1–V6 kết thúc bằng **chạy lại lát cắt tháng 8 và điền bảng so sánh trước/sau** (mẫu ở cuối tài liệu).
4. Sau vòng 2, Anh sẽ cấp thêm tri thức cho kỳ dài hơn (sao kê 09/2024–12/2025, sổ T1–T7/2026, Base 2023–2025). V3 và V4 phải chuẩn bị sẵn cho việc nạp theo lô, theo kỳ hiệu lực.

Trình tự: **V0 → V1 → V1b → V2 → V3 → V4 → V5 → V6 → R1** (V1b thêm ngày 18/09 sau kiểm tra độc lập V1). **Từ tối 18/09: V2→V6 lập trình liên tục, hoãn cổng đo chất lượng đến đợt nạp dữ liệu sau R1** — xem mục "Chỉ thị" đặt trước V2.

## Tài sản mới được cấp (Codex vòng 1 chưa được chỉ tới các thư mục này)

| Thư mục / file | Nội dung | Dùng ở |
|---|---|---|
| `<dự án>\var\thu-nghiem-claude-2026-09-18\` | Báo cáo chạy thử; zip gồm `chuan_bi.py` (bộ chuyển đổi dữ liệu thật → `ktt-fixture-v1`), `chay_thu.py` (kịch bản chạy qua API nội bộ), 13 file `inputs\*.json` đã chuyển đổi, `ket_qua\` (đề xuất, đánh giá, workbook duyệt) | V0–V6 |
| `D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\bo_quy_tac\` | **Script khảo sát bản 1.2 thật sự tồn tại ở đây:** `15_doc_pdf_2nam.py` (sao kê PDF Vietinbank, 2 layout), `11_loc_sao_ke.py`, `12_loai_giao_dich.py`, `14_xuat_junsky.py` (xuất CB_tmpEntry1/2), `17_doi_chieu_2nam.py`, `20_doc_hoa_don_xml.py`, `kho_tri_thuc.py` + `kho_tri_thuc_data.zip`, `chung.py`; tài liệu `README.md`, `HUONG-DAN-TAO-FILE-NHAP-JUNSKY.md`, `HUONG-DAN-KHO-TRI-THUC.md`, `BASE-DE-NGHI-THANH-TOAN.md`, `CHOT-NHAN-DANG-GIAO-DICH.md`, `PHAN-HANH-VA-TRI-THUC.md` | V0, V3, V4, V6 |
| `…\bo_quy_tac\ket_qua\` | `TU-DIEN-NHOM-NGHIEP-VU.xlsx` (7 sheet, 431 từ khóa, 3 chỉ số), `BO-QUY-TAC.xlsx` (809 quy tắc sao kê, Ánh xạ STK, DM danh mục, Tập chuẩn 768 dòng 2026, Chứng từ · dòng), `HOA-DON-CAY-PHAN-NHANH.xlsx` (cây hóa đơn, 28 khoản mục ↔ nhóm, 149 NCC khóa cứng), `HOA-DON-KHAO-SAT.md`, `HUONG-DAN-CAP-NHAT-TRI-THUC.md`, `SAO-KE-2-NAM.xlsx`, `SAO-KE-THEO-THANG.xlsx`, `DOI-CHIEU-2-NAM.xlsx`, `NHAP-JUNSKY-T1…T8.xlsx`, `JUNSKY-CHI/THU-T1…T8.xlsx`, `NHOM-NGHIEP-VU-BASE-v2.xlsx`, `quy_tac_nhom_nghiep_vu_v2.py` | V1, V4, V6 |
| `…\bo_quy_tac\nguon\` và `…\Mang ngan hang\Ngân Hàng\` | Sao kê eFAST `Sao kê NH T01…T08.xls` (2026), PDF `du lieu 2 nam\Sao kê NH Vietinbank\*.pdf` (09/2024–08/2026), `Sổ NKC có đối ưng.xlsx`, mẫu `Phiếu chi/thu NH file mẫu junsix.xlsx` | V3, V6 |
| `…\Mang ngan hang\DANH MỤC\` | Kết xuất Junsky: `Danh mục khách hàng PLHN.xlsx`, `Khoản mục chi phí.xlsx`, `Mã dự án.xlsx`, `Trung tâm chi phí.xlsx`, `Bảng cân đối phát sinh.xlsx`, **`Danh sách chứng từ công nợ.xlsx`** (chứng từ công nợ theo đối tượng/TK/hóa đơn — nguồn OPEN_ITEM) | V2, V3 |
| `…\Mang ngan hang\dgbList.xlsx`, `GA_rpt12Ledger21.xls`, `So ngan hang 9.2024-12.2025*.xlsx` | Sổ nhật ký chung / sổ ngân hàng kết xuất từ Junsky | V3 |
| `D:\Claude\Claude outputs\hoa_don\` | `hoa_don.csv` (1.907 HĐ), `dong_hang.csv` (5.198 dòng), `bang_ke.csv` (2.716 HĐ) — kết quả đọc XML/bảng kê 01/2024–09/2026 | V2, V3 |
| `D:\Claude\Phan mem download hoa don\Download hoa don\PLHN\<yyyy-mm>\{mua_vao,ban_ra}\` | XML gốc TCT 2.1.0 + Excel bảng kê cổng thuế | V3 |
| `D:\Claude\Base back up module\backup\PLHN\` | Chỉ mục Excel + thư mục JSON từng đề nghị Base (≥1.283 thư mục, 1.115 trong chỉ mục) | V3 |

Lưu ý khi dùng lại `chuan_bi.py`: script viết trên máy khác nên đường dẫn là Linux (`/home/claude/...`, `/mnt/user-data/uploads/...`, `/tmp/*.pkl`). Ánh xạ: `bo_quy_tac/ket_qua/` → thư mục cùng tên ở trên; `Claude outputs/hoa_don/` → `D:\Claude\Claude outputs\hoa_don\`; `Sao kê NH T08.xls` → `…\Ngân Hàng\`; hai file pickle `base9.pkl`, `nkc2.pkl` **không có trên máy này** — thay bằng `NHOM-NGHIEP-VU-BASE-v2.xlsx` (Base) và `Danh sách chứng từ công nợ.xlsx` (công nợ). Không cần chạy lại `chuan_bi.py` để tái hiện kết quả: `inputs\*.json` đã có sẵn, chỉ cần trỏ `chay_thu.py` vào `src` của dự án.

## Quy ước bổ sung cho vòng 2

- **Hai chế độ tách riêng, chung một code:** giữ nguyên chế độ `fixture` (test, demo) và thêm chế độ **`that`** (`environment = "that"`, `entity_id = "PLHN"`, `data_dir` riêng, ví dụ `var\plhn-that\`). Chế độ `that` nhận bộ đọc nguồn thật, **vẫn chặn xuất/nhập Junsky** cho đến khi V6 được nghiệm thu. Không dùng chung SQLite giữa hai chế độ.
- **Bộ chạy thử tháng 8 là hồi quy bắt buộc:** trước khi báo xong bất kỳ V nào, chạy lại `chay_thu.py` (hoặc bản đã chuyển sang bộ đọc thật ở V3+) và điền bảng so sánh. Con số gốc ngày 18/09/2026: phủ 25/105 (C1) và 51/105 (C2); trên dòng FULL có đáp án: TK Nợ/Có 36/40, đối tượng 12/44, dự án 13/16; 19 giây/phiên 105 dòng, 25 giây/đánh giá 62 dòng ×2 với 133 mã đối tượng.
- **Dữ liệu thật nằm trong `var\` và các thư mục nguồn; không sao chép vào `tests\fixtures\`.** Test tự động dùng fixture như cũ; kiểm chứng trên dữ liệu thật báo cáo riêng, không in nội dung dòng sao kê, số tài khoản, MST hay số tiền vào phản hồi chat.
- **Không tự duyệt tri thức.** Máy chuyển tri thức từ Excel vào trạng thái chờ duyệt; trạng thái "đã duyệt" chỉ được đặt khi tôi xác nhận trong prompt, với actor ghi rõ.
- **Không sửa file nguồn, không sửa file trong `var\thu-nghiem-claude-2026-09-18\`.** Kết quả mới ghi vào thư mục `var\vong-2\<V>\`.
- Kết thúc mỗi prompt vẫn theo mẫu vòng 1 (đã làm; test thực chạy; lệnh; điểm chưa xác minh; điều kiện nghiệm thu) **cộng bảng so sánh tháng 8**.

---

## V0 — Kiểm kê tài sản mới và tiếp nhận báo cáo chạy thử (chưa code)

```text
Hãy tiếp nhận kết quả chạy thử độc lập và kiểm kê tài sản mới được cấp; chưa sửa code sản phẩm.

Đọc:
1. var\thu-nghiem-claude-2026-09-18\BAO-CAO-CHAY-THU-CODEX.md — toàn bộ, đặc biệt mục 6 (tám phát hiện) và mục 7 (đối chiếu kế hoạch).
2. Giải nén var\thu-nghiem-claude-2026-09-18\thu-nghiem-claude-2026-09-18.zip tại chỗ; đọc chuan_bi.py, chay_thu.py, inputs\00-ghi-chu-chuan-bi.json, ket_qua\TONG-HOP-CHAY-THU.json.
3. BO-PROMPT-CODEX-VONG-2.md — phần "Tài sản mới được cấp" và "Quy ước bổ sung".
4. D:\Claude\Phan mem ho tro ke toan\Mang ngan hang\bo_quy_tac\README.md, PHAN-HANH-VA-TRI-THUC.md, HUONG-DAN-TAO-FILE-NHAP-JUNSKY.md, ket_qua\HUONG-DAN-CAP-NHAT-TRI-THUC.md, ket_qua\HOA-DON-KHAO-SAT.md.

Yêu cầu:
- Kiểm kê bằng liệt kê file thực tế các thư mục trong bảng "Tài sản mới được cấp"; sửa lại mục 3 của docs\HIEN-TRANG.md: các script bản 1.2 (15_doc_pdf_2nam.py, 17_doi_chieu_2nam.py, 14_xuat_junsky.py, kho_tri_thuc.py, 20_doc_hoa_don_xml.py) và workbook nay đã tìm thấy; ghi đường dẫn, kích thước, ngày sửa. Với mỗi script: đọc phần đầu và hàm chính, ghi nó đọc gì, xuất gì, phụ thuộc gì; chưa kết luận "tái dùng được" khi chưa chạy.
- Chạy lại chay_thu.py trên máy này (trỏ sys.path vào src của dự án, dùng inputs\*.json có sẵn, ghi ra var\vong-2\V0\). Xác nhận tái hiện được các con số gốc trong báo cáo hoặc ghi rõ sai lệch và nguyên nhân.
- Với tám phát hiện ở mục 6 báo cáo: xác nhận hoặc bác bỏ từng điểm bằng cách chỉ ra file/dòng code; ghi vào docs\QUYET-DINH.md ở trạng thái "chờ quyết định" kèm phương án sửa tối thiểu và ảnh hưởng tới hợp đồng dữ liệu/schema.
- Lập kế hoạch V1–V6 theo BO-PROMPT-CODEX-VONG-2.md: với mỗi V ghi đầu vào có sẵn, thay đổi schema (nếu có, kèm migration), test bổ sung, và tiêu chí nghiệm thu đo trên lát cắt tháng 8. Không ước lượng ngày.
- Nêu tối đa 10 câu hỏi cần tôi hoặc kế toán trưởng trả lời trước V1; mỗi câu kèm phương án mặc định nếu không có câu trả lời.

Không sửa file trong var\thu-nghiem-claude-2026-09-18\. Không đưa dữ liệu thật vào tests\fixtures\. Cập nhật docs\TIEN-DO.md thêm mục "Vòng 2" với V0–V6.

Trả lời tiếng Việt, xưng tôi, gọi tôi là Anh. Dừng để tôi duyệt kế hoạch V1–V6 trước khi code.
```

---

## V1 — Máy đề xuất: khóa cứng dẫn tới mẫu định khoản, từ khóa regex, thứ tự xét, tầng ngoại lệ

```text
Triển khai V1 — nâng máy đề xuất (M3/M2) để dùng được bộ quy tắc sao kê thật. Đọc Quy ước chung vòng 1, Quy ước bổ sung vòng 2, docs\QUYET-DINH.md (các quyết định V0 đã duyệt), BAO-CAO-CHAY-THU-CODEX.md mục 5–6. Chỉ làm V1.

Bối cảnh đo được trên lát cắt tháng 8: máy chỉ dùng được 62/809 quy tắc (bậc 5 · từ khóa thuần); 747 quy tắc bậc 1–4 (số TK đối ứng / tên đối ứng + từ khóa) không biểu diễn được; đối tượng đúng 12/44 dòng; khớp từ khóa là chuỗi con không ranh giới từ.

Phạm vi:
1. Mở rộng POLICY (mẫu định khoản) để kích hoạt bằng một trong ba cách, đúng cấu trúc sheet Quy tắc của BO-QUY-TAC.xlsx: (a) khóa cứng — số TK đối ứng, MST, hoặc mã đối tượng đã nhận diện; (b) từ khóa; (c) khóa cứng + từ khóa. Trường của mẫu có thể để trống một phần: đối tượng lấy từ khóa cứng, TK từ từ khóa. Giữ nguyên nguyên tắc "khóa cứng đã xác minh thắng từ khóa".
2. Thay "ưu tiên số, hòa thì chặn" bằng thứ tự xét tường minh trong một phân vùng (bậc 1 → 2 → 3 → 4 → 5, trong bậc theo thứ tự đã duyệt), thắng đầu tiên. Vẫn chặn khi hai mẫu cùng thứ tự cùng khớp; validation từ chối nạp hai mẫu trùng thứ tự trong cùng phân vùng.
3. Từ khóa là biểu thức chính quy có ranh giới từ và loại trừ (negative lookahead), chuẩn hóa văn bản như normalize_text hiện có (Đ→D trước NFD). Viết unit test cho năm trường hợp đã biết: UNG HO không khớp "TAM UNG HOP DONG"; MUA HOA không khớp "MUA HOA CHAT"; DAU không khớp "DAU TU"; HOA CHAT không khớp "HOA CHAT NHUA"; PHI không khớp "PHIEU".
4. Tầng ngoại lệ (nhóm CASE): khóa chính xác theo số giao dịch, số chứng từ hoặc hash mô tả → quyết định cố định, xét trước mọi mẫu; có hiệu lực/known_at như tri thức khác.
5. Hạn dùng của quy tắc (cột han_dung trong sheet Quy tắc) ánh xạ vào valid_to; quy tắc hết hạn không được chọn nhưng vẫn báo "có mẫu hết hạn khớp" trong bằng chứng.
6. Đề xuất (chưa bắt buộc làm): mẫu nhiều dòng cho trường hợp phí ngân hàng có thuế (đáp án 1331|6427) — trình phương án ảnh hưởng tới export_items và Entry2 để tôi quyết định.

Dữ liệu thử: mở rộng chuan_bi.py (bản sao trong var\vong-2\V1\, đường dẫn Windows) để phát cả 809 quy tắc và 164 dòng Ánh xạ STK thành tri thức theo cấu trúc mới; tách hai tập: trạng thái DE_CU/CHAC_CHAN (duyệt) và NHAP (chờ duyệt) như hai mốc C1/C2 hiện có.

Kiểm thử và nghiệm thu:
- Toàn bộ test fixture cũ vẫn đạt; test mới cho 1–5.
- Chạy lại lát cắt tháng 8, điền bảng so sánh. Yêu cầu tối thiểu: đối tượng đúng trên dòng FULL tăng so với 12/44; TK Nợ/Có không giảm dưới 36/40; báo cáo số dòng bị chặn vì hòa thứ tự và vì mẫu hết hạn.
- Ghi từng dòng sai còn lại vào var\vong-2\V1\SAI-CON-LAI.json (bank_id, mẫu chọn, đề xuất, đáp án), không in nội dung ra chat.

Không sửa hợp đồng nguồn (để V2). Không tự duyệt tri thức NHAP.
```

---

## V1b — Bổ sung V1: đo không rò rỉ, hạn dùng, bậc 2/5, cache tri thức

```text
Tôi đã đọc BAO-CAO-V1.md và THIET-KE-MAU-NHIEU-DONG.md, đồng thời cho kiểm tra độc lập. Kết quả kiểm tra ở var\vong-2\V1\kiem-tra-doc-lap-claude\DANH-GIA-V1-CLAUDE.md (kèm KET-QUA-KHONG-RO-RI.json và chuan_bi_khong_ro_ri.py). Hãy đọc file đó trước.

Kết luận của tôi: code V1 đúng phạm vi và 138/138 test đạt, nhưng V1 CHƯA ĐẠT ngưỡng nghiệm thu. Con số 19/44 là do rò rỉ tương lai: 25/68 mẫu được chọn có lan_dau trong tháng 08/2026; 16/19 dòng đối tượng đúng là nhờ mẫu sinh trong chính tháng 8. Chạy lại cùng code V1 với 750 quy tắc có lan_dau < 01/08/2026: đối tượng 12/44 (không cải thiện), TK Có 32/40 (giảm so với 36/40), phủ theo tiền 17,5% (gốc 46,7%). Tôi không chấp nhận số đo có rò rỉ làm căn cứ qua cổng, kể cả khi đã ghi chú "hồi cứu".

Giao V1b — sửa và đo lại, chưa sang V2. Quyết định của tôi:

QĐ-V1b-1 · Chuẩn đo không rò rỉ (bắt buộc từ nay về sau):
- known_at của quy tắc khai thác từ lịch sử không được sớm hơn lan_dau; bộ chuyển đổi đặt known_at = max(lan_dau, thời điểm đọc file) và ghi cơ sở.
- Nghiệm thu lát cắt tháng 8 chỉ dùng tri thức có lan_dau < 01/08/2026 (bộ lọc như LEAK_FREE trong chuan_bi_khong_ro_ri.py). Bảng so sánh chuẩn có hai cột riêng: "hồi cứu (có rò rỉ)" và "không rò rỉ"; cột không rò rỉ là cột nghiệm thu.
- Số lần gặp/đúng của quy tắc có tính cả tháng 8 vẫn được ghi là hạn chế đã biết; không cần tính lại ở V1b.

QĐ-V1b-2 · Hạn dùng quy tắc:
- Thay han_dung = lần cuối + 90 ngày bằng tham số cấu hình theo loại: quy tắc có khóa STK (bậc 1, 2) và ánh xạ STK: 365 ngày kể từ lần cuối; ánh xạ STK trạng thái CHAC_CHAN: không hết hạn (valid_to = null); quy tắc từ khóa (bậc 3, 4, 5): 180 ngày.
- Giữ raw han_dung nguồn trong payload để đối chiếu; ghi tham số đã dùng vào manifest của lượt chạy. Đây là quyết định vận hành tạm cho pilot, có thể đổi khi kế toán trưởng duyệt tri thức ở V4.

QĐ-V1b-3 · Ngữ nghĩa bậc 2 và bậc 4 (không có từ khóa):
- Bậc 2 (STK) và bậc 4 (tên đối ứng) là mẫu dự phòng thuần theo khóa: trigger mode KEY, không có regex phủ định. Thứ tự xét bậc 1 → 2 → 3 → 4 → 5 đã bảo đảm mẫu có từ khóa thắng trước.
- Bỏ điều kiện "không chứa từ khóa nào" (empty_signature). Ghi vào QUYET-DINH.md là thay đổi cách diễn giải script nguồn, có lý do.

QĐ-V1b-4 · Mẫu bậc 5 không mang mã đối tượng:
- Với quy tắc từ khóa thuần (bậc 5), bộ chuyển đổi đặt fields.counterparty = null; đối tượng do định danh STK (bậc khóa cứng) điền. Chỉ bậc 1–4 mang mã đối tượng. Mục tiêu: không còn TEMPLATE_IDENTIFIER_CONFLICT do mã "phổ biến nhất" của mẫu từ khóa.
- Vẫn giữ required_fields có counterparty; dòng không có định danh thì PARTIAL, không đoán.

QĐ-V1b-5 · Kéo phần cache tri thức từ V5 lên V1b (chỉ phần cần để chạy được, không tối ưu toàn bộ):
- Knowledge.query và Knowledge.expired được cache trong một phiên/một lượt đánh giá theo (category, cutoff); cache vô hiệu khi có sự kiện tri thức. Kết quả phải giống hệt khi không cache (test so sánh).
- Kiểm tra va chạm thứ tự khi stage: thay vòng lặp đọc toàn bộ JSON bằng truy vấn theo (category, partition, tier, order) đã lưu thành cột hoặc chỉ mục; nếu cần cột mới thì thêm migration sau v8 có checksum.
- Mục tiêu đo trên máy này với 133 mã đối tượng: mở phiên < 15 s, đề xuất 105 dòng < 30 s. Chưa yêu cầu mục tiêu 2.027 mã (V5).

QĐ-V1b-6 · Mẫu nhiều dòng: tôi duyệt hướng thiết kế trong THIET-KE-MAU-NHIEU-DONG.md. Chưa triển khai ở V1b; sẽ đưa vào V2 cùng trường thuế của hóa đơn. Ở V1b chỉ bổ sung: dòng bị chặn MULTILINE_TEMPLATE_REQUIRES_REVIEW phải xuất ra danh sách riêng kèm mẫu nguồn và giá trị, để tôi thấy phần tiền đang chờ mẫu nhiều dòng.

Việc nhỏ kèm theo:
- Chuyển 4 loại trừ đang hard-code trong literal_pattern (UNG HO, MUA HOA, DAU, HOA CHAT) thành dữ liệu của mẫu (regex đầy đủ nằm trong payload nguồn), code chỉ còn hàm dựng regex chung; test 5 bẫy giữ nguyên.
- Danh mục đối tượng: 131.KH.ANQUAN và NCC.TSG có trong sổ 2026 nhưng không có trong DM Đối tượng. Tôi sẽ kết xuất lại danh mục từ Junsky; V1b ghi hai mã này vào danh sách "mã ngoài danh mục cần kết xuất lại", không tự thêm vào catalog.

Nghiệm thu V1b (đo ở cột không rò rỉ, cùng 105 dòng và 62 đáp án, danh mục 133 mã):
- Toàn bộ test cũ và mới đạt.
- Trên cohort FULL gốc (44/40/40/16): đối tượng > 12/44; TK Nợ ≥ 36/40; TK Có ≥ 36/40; dự án ≥ 13/16.
- Phủ theo tiền không thấp hơn 46,7% sau khi loại phần tiền đang chờ mẫu nhiều dòng (báo cả hai số: có và không có phần chờ nhiều dòng).
- Không còn dòng NO_UNIQUE_APPROVED_TEMPLATE do quy tắc bậc 2 hết hạn 90 ngày; báo lại bảng nguyên nhân 4 nhóm như mục 3 của DANH-GIA-V1-CLAUDE.md.
- 0 dòng TEMPLATE_IDENTIFIER_CONFLICT do mẫu bậc 5.
- Thời gian đạt mục tiêu QĐ-V1b-5, đo riêng pha.

Đầu ra: var\vong-2\V1b\ gồm KET-QUA-V1b.json (hai cột hồi cứu/không rò rỉ), SAI-CON-LAI.json, CHO-MAU-NHIEU-DONG.json, TESTS.json; cập nhật BAO-CAO-V1.md thành mục "V1b", QUYET-DINH.md (QĐ-V1b-1…6 ở trạng thái đã duyệt bởi tôi), TIEN-DO.md. Không sửa file trong var\thu-nghiem-claude-2026-09-18\ và var\vong-2\V1\. Không tự duyệt tri thức vận hành; actor mô phỏng vẫn là MO_PHONG_KIEM_CHUNG. Không sang V2 khi chưa có tin của tôi.
```

---

## Chỉ thị: lập trình liên tục V2 → V6, hoãn cổng đo chất lượng đến đợt nạp dữ liệu

```text
Tôi đã đọc phần V1b trong BAO-CAO-V1.md. Tiếp nhận V1b về mặt code: 152/152 test, cache tri thức, migration v9, bộ lọc không rò rỉ, hạn dùng theo loại, bậc 2/4 dự phòng theo khóa, bậc 5 không mang đối tượng — giữ nguyên tất cả.

Về số đo chất lượng tháng 8: tôi tạm dừng dùng ngưỡng làm cổng. Lý do: các chỉ số còn thiếu (đối tượng, TK, phủ theo tiền) phụ thuộc vào việc chưa có trong code — mẫu nhiều dòng, trường thuế hóa đơn, công nợ thật, ánh xạ STK được duyệt (mới 35/164 xác minh), danh mục đối tượng cập nhật. Đo lại sau mỗi V trên lát cắt tháng 8 lúc này chỉ cho số nhiễu. Kết luận "chưa đạt" của V1b được ghi nhận là trạng thái hiện hành, không phải lý do dừng.

Giao tiếp: thực hiện LIÊN TỤC V2 → V3 → V4 → V5 → V6 theo BO-PROMPT-CODEX-VONG-2.md và KE-HOACH-VONG-2.md, không chờ tôi giao từng V. Sau V6, dừng và làm R1. Đợt nạp dữ liệu và điều chỉnh (tri thức kỳ dài 09/2024–12/2025, sổ T1–T7/2026, Base 2023–2025, danh mục kết xuất lại) là lần giao việc riêng sau R1; các ngưỡng chất lượng sẽ được đo và chốt ở đợt đó.

Điều chỉnh so với bộ prompt gốc:
1. Bỏ yêu cầu "điền bảng so sánh và đạt ngưỡng" ở cuối mỗi V. Thay bằng: chạy lại lát cắt tháng 8 như hồi quy kỹ thuật (phải chạy thông, không lỗi, in hai cột hồi cứu/không rò rỉ vào var\vong-2\<V>\KET-QUA.json) — không so ngưỡng, không kết luận đạt/không đạt.
2. Mẫu nhiều dòng: thiết kế THIET-KE-MAU-NHIEU-DONG.md đã duyệt; triển khai trong V2 cùng trường thuế hóa đơn (lines[] trong proposal/decision, export_item_lines, migration mới có checksum). Căn cứ tách thuế lấy từ hóa đơn đã nối hoặc từ tỷ lệ thuế của mẫu; chưa có căn cứ thì dòng ở trạng thái chờ, không tự chia.
3. V3: được cài offline xlrd==2.0.2 (khóa phiên bản trong pyproject, ghi nguồn wheel). Nếu không có wheel offline, báo và đọc bản .xlsx tôi sẽ lưu lại từ .xls — không tự viết bộ đọc .xls.
4. V3/V4: danh mục đối tượng hiện thiếu mã (131.KH.ANQUAN, NCC.TSG). Bộ đọc danh mục đọc từ thư mục DANH MỤC\ theo file mới nhất tôi kết xuất; mã trong sổ/công nợ không có trong danh mục được ghi vào danh sách "mã ngoài danh mục", không chặn cả lô, không tự thêm mã.
5. V4: đọc TU-DIEN-NHOM-NGHIEP-VU.xlsx bản 9 sheet (có 0B và 3B · KHÓA CỨNG). Toàn bộ tri thức nhập vào trạng thái chờ duyệt; actor duyệt CFO_NTD chỉ dùng khi tôi ra lệnh duyệt.
6. V6: Entry1 đúng 17 cột (có ErrorText). Các file JUNSKY-CHI/THU-T8.xlsx là mẫu định dạng do script dựng, chưa có bằng chứng nhập thành công; đối chiếu với chúng chỉ để kiểm tra cấu trúc, không gọi là "chuẩn đã nhập". Vẫn không nhập Junsky.
7. Quyết định còn thiếu (mục 10 KE-HOACH-VONG-2: metadata snapshot/as_of/known_at, kỳ khóa, nghĩa mã công nợ/EntryID/Entry2, BankID/CashflowID, Base 2026): KHÔNG dừng để hỏi. Chọn phương án mặc định hợp lý, ghi vào docs\QUYET-DINH.md dưới dạng "GIẢ ĐỊNH-Vx-n: nội dung, lý do, cách đổi lại", tham số hóa trong cấu hình để đổi được mà không sửa code. Tôi rà toàn bộ giả định ở R1. Chỉ dừng khi gặp việc không thể tham số hóa hoặc trái Quy ước chung (tự duyệt, nhập Junsky, đưa dữ liệu thật vào tests\fixtures).

Những gì KHÔNG được bỏ dù không có cổng đo:
- Test tự động cho từng V; toàn bộ suite đạt trước khi sang V kế tiếp. Migration nối tiếp v9, có checksum, thử trên bản sao DB.
- Hai chế độ fixture/that tách kho; chế độ that chặn xuất/nhập Junsky.
- Không sửa file nguồn, file trong var\thu-nghiem-claude-2026-09-18\, var\vong-2\V1\, var\vong-2\V1b\.
- Không in dữ liệu thật vào chat; kết quả từng V ghi var\vong-2\<V>\; cập nhật TIEN-DO.md sau mỗi V; QUYET-DINH.md ghi mọi giả định.
- Cuối mỗi V vẫn có báo cáo ngắn theo mẫu vòng 1 (đã làm, test, lệnh, chưa xác minh, giả định), gộp vào docs\BAO-CAO-VONG-2.md theo mục V2…V6.

Kết thúc: sau V6 chạy R1 (review theo BO-PROMPT-CODEX-VONG-2.md) và dừng. Trả lời tiếng Việt, xưng tôi, gọi tôi là Anh. Bắt đầu V2 ngay.
```

---

## V2 — Hợp đồng dữ liệu nguồn: hóa đơn có thuế, hợp nhất XML↔bảng kê, Base đầy đủ, công nợ theo chứng từ, sổ có số giao dịch

```text
Triển khai V2 — sửa hợp đồng dữ liệu nguồn (M1) theo dữ liệu thật đã khảo sát. Đọc Quy ước chung vòng 1, Quy ước bổ sung vòng 2, docs\HOP-DONG-DU-LIEU.md, BAO-CAO-CHAY-THU-CODEX.md mục 3.1 và 6.3–6.4, ket_qua\HOA-DON-KHAO-SAT.md, bo_quy_tac\BASE-DE-NGHI-THANH-TOAN.md. Chỉ làm V2.

Phạm vi:
1. Hóa đơn: thêm tiền chưa thuế, tiền thuế, tổng thanh toán, tiền tệ; dòng hàng có thuế suất và tính chất dòng (hàng hóa/khuyến mại/chiết khấu/ghi chú theo XML TCT 2.1.0); ràng buộc tổng dòng = tiền chưa thuế với dung sai làm tròn khai báo (ghi rõ dung sai, mặc định đề xuất 1 VND/dòng); trạng thái nguồn cho hóa đơn điều chỉnh/thay thế/hủy và liên kết tới hóa đơn gốc; bảng kê chỉ header, giữ trạng thái xử lý cổng thuế (ttxly 1–6).
2. Hợp nhất XML và bảng kê cùng khóa (MST bán, ký hiệu, số, mẫu số): một chứng từ, hai bằng chứng, mỗi bằng chứng có known_at riêng. Lệch tiền vượt dung sai → chứng từ vào trạng thái "mâu thuẫn nguồn" và báo cáo, không từ chối cả file. Hóa đơn không mã (ký hiệu K…) chỉ có bảng kê là bình thường.
3. Base: theo BASE-DE-NGHI-THANH-TOAN.md và NHOM-NGHIEP-VU-BASE-v2.xlsx — mã đề nghị, tên, nhóm đề xuất, trạng thái, ngày duyệt, số tiền (đọc cả dạng "669600 vnd"), tài khoản thụ hưởng (nếu có trong JSON), mã dự án thô, danh sách file đính kèm. Không phân loại nhóm G ở tầng nguồn.
4. Công nợ mở (OPEN_ITEM) từ Danh sách chứng từ công nợ.xlsx: cột Chứng từ công nợ, Ngày, Đối tượng, Tài khoản, Số tiền (HT), Mã dự án, Ký hiệu hđ, Số hóa đơn, Ngày hóa đơn, Nội dung; as_of và snapshot_id lấy từ thời điểm kết xuất do người nạp khai báo, không suy từ mtime. Hợp đồng vay (cột Hợp đồng vay) giữ làm tham chiếu.
5. Sổ (JOURNAL): bổ sung số giao dịch ngân hàng từ cột "Số CT đính kèm"/DocsNo của kết xuất Junsky nếu có (kiểm tra trong Sổ NKC có đối ưng.xlsx, dgbList.xlsx, NHAP-JUNSKY-T8.xlsx), số hóa đơn, mã đối tượng, dự án, khoản mục, trung tâm chi phí. Trạng thái "đã ghi sổ" là giá trị cấu hình của nguồn, không hard-code POSTED_SOURCE_FIXTURE trong engine/đối soát/liên kết lịch sử.
6. Sao kê: thêm MTID/CITAD, mã định danh TK thụ hưởng, tên đối ứng, ngày phát sinh; số giao dịch có thể trống ở một số dòng (phí, lãi) → khóa dự phòng khai báo rõ (ví dụ tài khoản + ngày giờ + số tiền + số dư sau giao dịch), ghi mức tin cậy khóa.

Migration schema có kiểm tra checksum như các lần trước. Cập nhật docs\HOP-DONG-DU-LIEU.md.

Kiểm thử và nghiệm thu:
- Test fixture cho từng điểm 1–6, kể cả hóa đơn điều chỉnh âm, chiết khấu, lệch làm tròn trong/ngoài dung sai, XML rồi bảng kê, bảng kê rồi XML, cùng khóa khác tiền.
- Cập nhật chuan_bi.py (bản var\vong-2\V2\) để phát dữ liệu tháng 8 theo hợp đồng mới: 75 hóa đơn XML phải nạp được không cần dòng thuế bịa; 19 + 5 hóa đơn bảng kê (kể cả 5 hóa đơn cố ý trùng XML) phải nạp thành một chứng từ có hai bằng chứng; sổ T8 có số giao dịch từ nguồn Junsky thay vì từ Tập chuẩn nếu cột đó tồn tại — nếu không tồn tại, ghi rõ và giữ cách cũ có đánh dấu.
- Chạy lại lát cắt tháng 8, điền bảng so sánh (không được giảm so với V1).
```

---

## V3 — Bộ đọc nguồn thật và chế độ `that`

```text
Triển khai V3 — bộ đọc nguồn thật cho năm nhóm nguồn PLHN và chế độ chạy "that" tách riêng fixture. Đọc Quy ước chung vòng 1, Quy ước bổ sung vòng 2, hợp đồng V2, docs\QUYET-DINH.md. Chỉ làm V3.

Nguyên tắc: bộ đọc thật phát ra cùng bản ghi nội bộ như adapter fixture; mọi phần còn lại của phần mềm không phân biệt nguồn. Tái dùng script bản 1.2 khi đã đọc và thử được; ghi rõ phần giữ/bọc/viết lại.

Phạm vi:
1. Cấu hình chế độ that: environment = "that", entity_id = "PLHN" (MST 0700850958 làm khóa kiểm tra pháp nhân trong nguồn), data_dir riêng. Chế độ that chặn batch-export/import Junsky bằng cờ cấu hình cho đến V6.
2. Sao kê Vietinbank: (a) eFAST .xls — layout như chuan_bi.py đã đọc: sheet "LICH SU GIAO DICH", khối thông tin tài khoản ở các dòng đầu (số TK, số dư đầu/cuối kỳ, tổng ghi có/ghi nợ, số giao dịch, chu kỳ), tiêu đề bảng là dòng bắt đầu bằng "STT/No." với 12 cột, dữ liệu ngay sau; không cố định chỉ số dòng, tìm theo nhãn; (b) PDF — tái dùng 15_doc_pdf_2nam.py (2 layout, 24 file 09/2024–08/2026, đã kiểm tra tổng và số dư liên tục). Kiểm soát: đầu + có − nợ = cuối; số dòng = tổng số giao dịch ghi trên file; chống trùng giữa file (SAO-KE-2-NAM.xlsx sheet "Dòng trùng giữa file" có 236 trường hợp đã biết).
3. Hóa đơn: XML TCT 2.1.0 (tái dùng 20_doc_hoa_don_xml.py; cấu trúc thư mục PLHN\<yyyy-mm>\{mua_vao,ban_ra}); bảng kê Excel cổng thuế (cột như bang_ke.csv: Ky hieu mau so, Ky hieu HD, So HD, Ngay lap, MST/Ten nguoi ban, MST/Ten nguoi mua, Tien chua thue, Tien thue, Tong thanh toan, Don vi tien te, Trang thai). Đối chiếu số hóa đơn với hoa_don.csv/bang_ke.csv để kiểm tra bộ đọc: cùng số lượng và cùng tổng theo kỳ.
4. Base: chỉ mục Excel + thư mục JSON (BASE-DE-NGHI-THANH-TOAN.md). Quét thư mục thay vì tin chỉ mục; báo cáo chênh 1.283 thư mục / 1.115 chỉ mục; lấy tài khoản thụ hưởng khi JSON có.
5. Junsky: danh mục 6 file trong DANH MỤC\; sổ (dgbList.xlsx hoặc Sổ NKC có đối ưng.xlsx — chọn file có đủ cột theo V2 và ghi lý do); công nợ (Danh sách chứng từ công nợ.xlsx); kỳ khóa chưa có file kết xuất → nhập qua cấu hình có người khai và ngày khai, ghi rõ là khai báo tay.
6. Lệnh: nap-nguon --nguon <sao_ke|hoa_don|bang_ke|base|junsky> --duong-dan <file/thư mục> --as-of --exported-at --known-at-basis; báo cáo kiểm soát tổng/số dòng/trùng trước khi commit; nạp lại không tăng số chứng từ.

Kiểm thử và nghiệm thu:
- Test đơn vị cho từng bộ đọc trên file tháng 8 thật (đọc từ đường dẫn nguồn, không chép vào tests\fixtures): số dòng, tổng kiểm soát, khóa duy nhất, ngày.
- Nạp lát cắt tháng 8 bằng bộ đọc thật vào kho chế độ that; chạy đề xuất và đánh giá bằng tri thức của V1; kết quả 105 dòng sao kê phải trùng với đường JSON (cùng completeness, cùng trường) — lệch nào phải giải thích được.
- Nạp thử toàn bộ sao kê 09/2024–08/2026 (PDF + xls) và toàn bộ XML/bảng kê 01/2024–09/2026 vào một kho that riêng để đo thời gian, số trùng, số lỗi; chưa đề xuất trên các kỳ này. Đây là bước chuẩn bị cho đợt nạp tri thức kỳ dài mà tôi sẽ giao sau.
- Điền bảng so sánh tháng 8 (đường thật vs đường JSON).
```

---

## V4 — Tri thức: nhập từ Excel của người, Excel đọc được, ba chỉ số, vòng đời và kỳ hiệu lực

```text
Triển khai V4 — đưa tri thức thật vào kho và trả lại Excel mà kế toán đọc/sửa được. Đọc Quy ước chung vòng 1, Quy ước bổ sung vòng 2, ket_qua\HUONG-DAN-CAP-NHAT-TRI-THUC.md, bo_quy_tac\HUONG-DAN-KHO-TRI-THUC.md, docs\HOP-DONG-DU-LIEU.md mục tri thức. Chỉ làm V4.

Nguyên tắc: Excel là bản chủ của người; SQLite là bản máy. Máy chỉ đề cử; người duyệt. Không xóa tri thức, chỉ đổi trạng thái/hiệu lực.

Phạm vi:
1. Nhập tri thức từ ba workbook, mỗi dòng thành một phiên bản tri thức có valid_from, valid_to, known_at (= ngày lập ghi trong sheet hoặc ngày nhập, ghi cơ sở), bằng chứng (tên file, sheet, dòng):
   - TU-DIEN-NHOM-NGHIEP-VU.xlsx: sheet 1 NHÓM (33 nhóm G, TK Nợ đề xuất, thứ tự xét), 2 TỪ KHÓA (431 regex, nguồn áp dụng, trạng thái ĐANG DÙNG/NGỦ/ĐỀ CỬ, ba chỉ số khớp trong nhóm / chỉ mình nó bắt / khớp ngoài nhóm), 3 NGOẠI LỆ, 3B KHÓA CỨNG, 4 CHỜ DUYỆT, 5 NHẬT KÝ.
   - BO-QUY-TAC.xlsx: Quy tắc (809, bậc, khóa, chiều, TK, đối tượng, dự án, số lần gặp/đúng, ổn định, hạn dùng, trạng thái), Ánh xạ STK (164), Từ khóa, DM Đối tượng/TK/Khoản mục/Dự án/Trung tâm CP.
   - HOA-DON-CAY-PHAN-NHANH.xlsx: 149 NCC khóa cứng MST → nhóm/TK (cột Duyệt), 28 khoản mục phí ↔ nhóm G, cây MUA VÀO/BÁN RA.
   Ánh xạ trạng thái: ĐANG DÙNG/DE_CU/CHAC_CHAN → chờ duyệt có đề nghị "duyệt"; NHAP/ĐỀ CỬ → chờ duyệt; NGỦ → valid_to = ngày chuyển. Tôi sẽ duyệt bằng một lệnh riêng theo lô, có actor.
2. Xuất Excel cho người: một workbook với các sheet đọc được (nhóm, từ khóa, khóa cứng, mẫu định khoản, ngoại lệ, chờ duyệt, nhật ký) — mỗi dòng có mã, tên, biểu thức, TK, đối tượng, dự án, ba chỉ số, số lần đúng/gặp, hiệu lực, trạng thái, cột "Anh duyệt" và "Ghi chú". JSON kỹ thuật chỉ ở sheet ẩn. Nhập ngược từ workbook này: chỉ dòng có quyết định mới sinh sự kiện; phát hiện workbook cũ, dòng sửa tay không hợp lệ.
3. Ba chỉ số từ khóa tính lại từ dữ liệu trong kho (theo hợp đồng V2) tại thời điểm cutoff, có trọng số theo số chứng từ và theo tiền; dùng cho báo cáo kỳ, không tự đổi trạng thái.
4. Kỳ hiệu lực theo giai đoạn: hỗ trợ tri thức có valid_from/valid_to theo kỳ (ví dụ TK vốn hóa 24x trước 05/2025, chi phí sau đó) và nạp theo lô cho kỳ dài mà tôi sẽ giao sau (sao kê 09/2024–12/2025, sổ T1–T7/2026, Base 2023–2025): một lô = một known_at, một bằng chứng.
5. Nhật ký thay đổi tri thức xuất được thành "Báo cáo kỳ" theo mẫu sheet 6 của TU-DIEN.

Kiểm thử và nghiệm thu:
- Nhập ba workbook không lỗi; số phiên bản tri thức theo từng nhóm khớp số dòng nguồn (báo cáo chênh).
- Xuất workbook rồi nhập ngược không thay đổi gì → 0 sự kiện; sửa một trạng thái → đúng một sự kiện.
- Chạy lại lát cắt tháng 8 với tri thức nhập từ Excel (thay cho 07-tri-thuc.json): kết quả không kém V1/V2; điền bảng so sánh.
```

---

## V5 — Kỹ thuật: hiệu năng, workbook duyệt, chấm điểm, dọn chuỗi fixture

```text
Triển khai V5 — các sửa kỹ thuật đã đo được trong chạy thử. Đọc Quy ước bổ sung vòng 2 và BAO-CAO-CHAY-THU-CODEX.md mục 6.5–6.8. Chỉ làm V5.

Phạm vi:
1. Hiệu năng truy vấn tri thức: knowledge.query hiện duyệt toàn bộ phiên bản và chạy 2 truy vấn SQL cho mỗi phiên bản, được gọi 4–5 lần cho mỗi dòng sao kê. Thêm chỉ mục (category, logical_key, valid_from, valid_to), bảng/materialized view "tri thức có hiệu lực tại cutoff" hoặc cache trong phiên (không đổi kết quả, cache vô hiệu khi có sự kiện tri thức). Mục tiêu đo: 105 dòng sao kê với đủ 2.027 mã đối tượng dưới 10 giây đề xuất; đánh giá 62 dòng × 2 baseline dưới 30 giây. Ghi số đo trước/sau.
2. Workbook duyệt: sheet PHAN_BO chỉ liệt kê công nợ mở của đối tượng đã đề xuất và các ứng viên đã xếp hạng, tối đa N dòng mỗi đề xuất (N cấu hình); thêm sheet "CONG_NO_KHAC" cho phép chọn đối tượng khác bằng mã. Workbook 105 dòng phải dưới 500 KB.
3. Chấm điểm: tách rõ "không đề xuất" khỏi "đề xuất sai" trong mọi chỉ số; tiền sai chỉ tính trên dòng có đề xuất; thêm độ phủ theo tiền; không chấm trường của đề xuất completeness = NONE.
4. Loại bỏ chuỗi fixture khỏi logic nghiệp vụ (POSTED_SOURCE_FIXTURE, phân vùng PLHN_FIXTURE:*) → tham số cấu hình theo nguồn; fixture chỉ còn trong tests và kiem_chung.
5. Bộ đọc/ghi Excel: giữ đúng mã dạng chuỗi (không mất số 0 đầu như "00379227"), ngày ISO, không tự chuyển kiểu.

Kiểm thử và nghiệm thu: test fixture cũ đạt; test mới cho 2–5; bảng so sánh tháng 8 với danh mục đầy đủ 2.027 mã (không thu hẹp) — số liệu đề xuất phải trùng với V4, thời gian đạt mục tiêu.
```

---

## V6 — Chạy thật tháng 08/2026 (shadow): workbook cho kế toán, xuất CB_tmpEntry1/2 và đối chiếu với file đã nhập thật

```text
Triển khai V6 — chạy trọn một phiên shadow trên lát cắt tháng 08/2026 bằng bộ đọc thật và tri thức đã duyệt, kết thúc bằng file xuất Junsky đối chiếu với file đã nhập thành công của cùng tháng. Đọc Quy ước chung vòng 1, Quy ước bổ sung vòng 2, bo_quy_tac\HUONG-DAN-TAO-FILE-NHAP-JUNSKY.md, 14_xuat_junsky.py, docs\CHUYEN-SANG-VAN-HANH-THAT.md. Chỉ làm V6. Không nhập vào Junsky.

Phạm vi:
1. Phiên shadow tháng 8 trong kho chế độ that: nạp sao kê T08.xls, hóa đơn XML/bảng kê 2026-08, Base (nếu có kỳ 2026), gói Junsky (danh mục, sổ T1–T7 làm lịch sử, công nợ, kỳ khóa khai báo). Mở phiên cho 105 dòng, đề xuất, xuất workbook duyệt theo V5.
2. Duyệt mô phỏng bằng Tập chuẩn: dòng CHAC_CHAN (62) → APPROVE với trường từ sổ khi máy đúng, SỬA có lý do khi máy sai; dòng CHUA_GHEP/MO_HO → WAIT. Actor ghi rõ là mô phỏng từ sổ, không phải kế toán duyệt.
3. Xuất batch CB_tmpEntry1/2 theo mapping trong HUONG-DAN-TAO-FILE-NHAP-JUNSKY.md và mẫu NHAP-JUNSKY-T8.xlsx (Entry1 16 cột: EntryID, EntryDate, BankID, AcctID, OrglID, OrglRate, OrglAmt, BaseAmt, ObjectID, PayerID, PayerText, BranchID, Memo, DocsNo, MRowID, PeriodID; Entry2 37 cột bắt đầu EntryID, Offset, AcctID, BankID, OrglID, OrglRate, OrglDeb, OrglCrd, BaseDeb, BaseCrd, ObjectID, EntryDM, CashflowID, PrecostID, ProjectID, CenterID…). Chế độ that vẫn đánh dấu file "SHADOW — CHƯA NHẬP".
4. Đối chiếu tự động file máy xuất với JUNSKY-CHI-T8.xlsx và JUNSKY-THU-T8.xlsx (file đã nhập thật cùng tháng) theo số giao dịch (DocsNo): từng cột giống/khác, số chứng từ giống/khác, dòng Entry2 giống/khác; tổng tiền theo TK. Báo cáo lệch theo nhóm nguyên nhân: máy sai, quy ước đặt số chứng từ, cột chưa mapping, dòng chưa có đề xuất.
5. Đối soát ngược: nạp sổ T8 (đã ghi sổ thật) làm gói xác minh, chạy reconcile cho batch shadow; báo cáo RECON_A/B/C và nhãn học sinh ra (chỉ nhãn có bằng chứng từng trường).
6. Backup/restore kho that; batch-recover từ backup phải tái tạo đúng file.

Nghiệm thu: bảng so sánh tháng 8 cuối cùng (đường thật, tri thức Excel, danh mục đầy đủ); báo cáo đối chiếu Entry1/2; danh sách quyết định còn thiếu để chuyển sang pilot (theo mục 3 của CHUYEN-SANG-VAN-HANH-THAT.md). Không tuyên bố sẵn sàng vận hành; đó là quyết định của tôi và kế toán trưởng.
```

---

## R1 — Review vòng 2 trước khi nhận tri thức kỳ dài

```text
Review kết quả vòng 2 (V1–V6) của dự án kho tri thức. Đọc docs\QUYET-DINH.md, docs\TIEN-DO.md, các báo cáo trong var\vong-2\, và BAO-CAO-CHAY-THU-CODEX.md làm mốc gốc. Chỉ review và cập nhật docs\REVIEW-CONG.md; chưa sửa code.

Kiểm tra ưu tiên: tám phát hiện gốc đã đóng hay chưa, có bằng chứng file/dòng/test; bảng so sánh tháng 8 qua từng V có nhất quán không (cùng 105 dòng, cùng 62 đáp án); rò rỉ tương lai trong tri thức nhập từ Excel (known_at sau cutoff nhưng vẫn được dùng); dữ liệu thật lọt vào tests\fixtures hoặc vào phản hồi; chế độ that có thể xuất Junsky khi chưa được phép không; nạp lại nguồn có làm tăng chứng từ không; hiệu năng đo thật với danh mục đầy đủ.

Kết luận: sẵn sàng nhận đợt nạp tri thức kỳ dài (09/2024–12/2025 và T1–T7/2026) hay chưa; nếu chưa, việc phải làm trước, xếp theo mức ảnh hưởng.
```

---

## Bảng so sánh chuẩn lát cắt tháng 08/2026 (điền cuối mỗi V)

| Chỉ tiêu | Gốc 18/09 (JSON, 133 mã ĐT) | Sau V… |
|---|---|---|
| Dòng sao kê nạp / trùng khi nạp lại | 105 / 105 | |
| Hóa đơn XML nạp / bảng kê nạp / mâu thuẫn nguồn | 75 / 19 / (5 bị từ chối) | |
| Tri thức có hiệu lực: mẫu / khóa cứng / ngoại lệ | 52 / 35 / 0 | |
| Phủ FULL trên 105 dòng (số dòng · % tiền) | 51 · 47% | |
| Trên dòng FULL có đáp án: đối tượng · TK Nợ · TK Có · dự án | 12/44 · 36/40 · 36/40 · 13/16 | |
| Dòng bị chặn: không mẫu · hòa thứ tự · hết hạn · đã ghi sổ (gói có sổ T8) | 54 · 0 · — · 64 | |
| Thời gian: mở phiên · đề xuất 105 dòng · đánh giá 62×2 | ≈1 s · 19 s · 25 s (133 mã); 60 s · 159 s · ≈360 s (2.027 mã) | |
| Kích thước workbook duyệt | 3,1 MB (52.606 dòng PHAN_BO) | |
| Test tự động đạt / tổng | 111 / 111 | |

Nguồn số gốc: `var\thu-nghiem-claude-2026-09-18\ket_qua\TONG-HOP-CHAY-THU.json` và `BAO-CAO-CHAY-THU-CODEX.md`.
