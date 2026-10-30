# Phiếu duyệt 3/3 · SDK của Core — **bản 2** (CD-029 mục 2c, CD-031, CD-032, CD-033)

**Lập:** 30/10/2026, lead. **Trạng thái:** chờ Anh duyệt toàn phiếu.
**Đây là tài liệu, chưa lập trình.**
**Đã kiểm:**
- Đặc tả SDK: Codex soạn và review chéo; Opus 2 vòng, hết Chặn. 12/12 JSON Schema kỹ thuật hợp lệ.
- Contract nghiệp vụ: Codex soạn và review chéo (kiểm mẫu đúng 95%); Opus review quy tắc chung + 3 contract cốt lõi, 2 vòng, hết Chặn. 20/20 ví dụ JSON đọc được, tổng tiền khớp.

**Bản 2 khác bản 1:**
- ba câu cũ Anh đã chốt (CD-033);
- thêm **dữ liệu trao đổi là JSON hai lớp, có lớp nghiệp vụ theo module** (CD-031);
- thêm **quy tắc lớp dữ liệu giao tiếp và sổ contract** (CD-032);
- đề xuất **phạm vi CRM để thử Core**.

## 1. Kết luận (đề nghị Anh duyệt)

1. **SDK là bộ công cụ chung** để module và engine nói chuyện với Core. Module mới không tự viết lại phần đăng nhập, tệp, OCR, mã hóa… (CD-019).
   - **SDK Python có 12 dịch vụ:** danh tính, tài liệu, tệp, kết quả, dữ liệu riêng, dữ liệu công bố, sự kiện, engine, quy trình, việc, nhật ký, mã hóa cột nhạy cảm.
   - **SDK giao diện:** lỗi tiếng Việt; ô %, tiền có đơn vị, ngày dd/mm/yyyy; khung lưới icon.
2. **Dữ liệu trao đổi giữa module và Core là JSON**, chứa đủ thông tin nghiệp vụ. "Contract" (JSON Schema) là bản mô tả gói JSON phải có những thông tin gì, để Core kiểm tự động. Hai lớp:
   - **Lớp kỹ thuật** (Core định nghĩa, 9 contract): tệp, văn bản tài liệu, bảng, tham số, nội dung đã che, trả lời AI, hóa đơn đọc từ XML, lỗi, việc.
   - **Lớp nghiệp vụ** (module sở hữu định nghĩa, **Anh duyệt**). Bản nháp đầu gồm:

     | Module | Contract nghiệp vụ |
     |---|---|
     | CRM | `hop_dong_ban` (phiên bản, tham số, lịch thanh toán % · giá trị gồm VAT · trong đó VAT, mốc), `bao_gia`, `du_an_dang_ban` |
     | M4 | `hop_dong_thau`, `phu_luc`, `boq`, `dot_thanh_toan`, `ket_qua_kiem_dot`, `nghiem_thu` |
     | M2 | `hoa_don_mua_vao`, `cong_no_phai_tra` (một số trường chờ Anh chốt thiết kế M2) |
     | Chung | `doi_tuong`, `du_an`, `but_toan_de_xuat`, `tep_nhap_junsky` |
     | Sự kiện | `tien_da_noi_dot`, `ban_giao_da_duyet`, `moc_da_xay_ra`, `hop_dong_hieu_luc`, `hoa_don_da_nhan` |

     Mỗi contract có mục đích, module sở hữu, module được đọc, bảng trường (nghĩa, bắt buộc, đơn vị, **nguồn** trong thiết kế đã chốt) và một ví dụ JSON DEMO đầy đủ. Các tổng tiền trong ví dụ đã được cộng lại kiểm tra. Ví dụ báo giá: 1.000.000.000 VND trước VAT, 10%, 10/30/60%, đợt 1 cọc → 100.000.000 · 340.000.000 · 660.000.000.
3. **Quy tắc lớp dữ liệu giao tiếp** (CD-032, đã ghi vào `CLAUDE.md`):
   - Gói module **bắt buộc có thư mục `contract/`**, gồm dữ liệu công bố, sự kiện phát/nhận, đầu vào nguồn. Thiếu hoặc không hợp lệ → **không cài được**.
   - **Sổ đăng ký contract** ở Core: cài/nâng cấp module → Core kiểm và đăng ký thêm, **không sửa code Core**. Admin xem sổ trên màn quản trị.
   - **Trùng nghĩa → đỏ:**
     - contract mới trùng nghĩa contract đã có;
     - module đọc dữ liệu module khác ngoài contract đã đăng ký;
     - cùng tên trường mà khác kiểu.

     Có **từ điển trường dùng chung** để máy phát hiện.
   - Contract nghiệp vụ mới, hoặc phiên bản mới của contract đang dùng → **Anh duyệt trước khi kích hoạt** (xuất bảng để duyệt). Phiên bản cũ giữ cho module còn dùng.
4. **Gói module = thư mục + `module.json` + `contract/`.** Core tự suy tên khối dữ liệu, vai CSDL và cổng; module không tự khai, để không leo quyền. Đủ để **cài qua giao diện mà không sửa Core**.
5. **Khung chạy module/engine** (CD-028, đúng phiếu API đã duyệt):
   - nhận cổng do Core chuyển giao;
   - báo sẵn sàng;
   - dừng có kiểm soát;
   - Core đo RAM/CPU.
6. **Bộ kiểm tuân thủ tự động.** Chạy khi cài, mỗi lần kích hoạt và mỗi lần Core khởi động; lệch là đỏ. Thêm hai kiểm:
   - contract trùng nghĩa;
   - tiến trình module/engine không đọc được kho mật khẩu.

## 2. Ba câu Anh đã chốt (CD-033)

| Câu | Anh chọn | Áp dụng |
|---|---|---|
| 1. Module thử Core ở G2 | **CRM** (dữ liệu DEMO) | Phạm vi đề xuất ở mục 3 |
| 2. Tài khoản Windows | **A.** Core chạy tài khoản riêng (ví dụ `ktt_core`); module/engine chạy tài khoản máy hạn chế (ví dụ `ktt_module`) | Áp **ngay từ giai đoạn thử trên máy Anh**.<br>• Script tạo tài khoản + cấp quyền thư mục, chạy lại được khi chuyển máy chủ; Anh chỉ bấm đồng ý quyền quản trị.<br>• Engine cũ cần tài khoản riêng (ABBYY Hot Folder) → hỏi Anh, không tự nới quyền. |
| 3. Module tự đóng mà có việc chờ | **A.** Core bật ngay | Admin đổi theo số đo; không tự bật module Anh đã tắt |

## 3. Đề xuất phạm vi CRM tối thiểu để thử Core ở G2 (Anh xem)

Phạm vi này phải đi qua đủ các phần Core cần thử (CD-033): tệp, engine, việc lâu, công bố + sự kiện, `contract/`, cài/tắt, ma trận thẩm quyền, cổng do Core giữ/nhả.

| Phần CRM | Thử phần nào của Core |
|---|---|
| **Dự án đang bán**: khai báo một lượt (CD-022/023) | Dữ liệu riêng `mod_crm`, chống ghi trùng, hai người cùng sửa, ma trận thẩm quyền xem/sửa, **công bố** `du_an_dang_ban` |
| **Báo giá**: lịch thanh toán + VAT cọc (CD-024), **in DOCX** | Engine tính lịch dùng chung; in DOCX là **việc lâu** (202 + theo dõi), tệp lưu vào kho tệp Core, tải xuống có kiểm quyền |
| **Tải mẫu hợp đồng G1** → trích tham số | Tải lên ≤ 20 MB, engine **trích xuất/OCR** qua Core, kết quả có nguồn do Core gắn |
| **Sự kiện** `moc_da_xay_ra` (mốc dự án) | Bus sự kiện, đánh thức module đang tắt khi có việc chờ |
| **Cài/tắt CRM** qua màn quản trị | Module Manager, `module.json` + `contract/`, sổ contract, bộ kiểm tuân thủ, cổng giữ/nhả |

Không đưa vào G2: soạn hợp đồng / ký kết / thu tiền (để G4). Thứ tự G4 giữ M4 → CRM → M2; phần CRM đã thử ở G2 dùng tiếp.

## 4. Câu cần Anh chọn (mới, ảnh hưởng tiền)

| # | Câu hỏi | A | B | Khuyến nghị |
|---|---|---|---|---|
| 1 | **Lịch nghĩa vụ hợp đồng bán bản đầu có gồm các khoản phí** (bảo trì, sử dụng hạ tầng…) không? | Chỉ tiền giá bán chia theo %. Phí theo dõi riêng, thêm sau mà không phá phiên bản | Gồm cả phí ngay từ đầu, mỗi đợt ghi loại khoản (giá bán / phí) | **A**: gọn cho bản đầu. Quy tắc Σ% = 100 áp cho phần giá bán |
| 2 | **VAT của đợt cọc khi cọc là đợt cuối, hoặc có nhiều đợt cọc** | Không cho phép: báo lỗi ngay ở ô cọc (lead đã chọn tạm cho Báo giá 27/10) | Cho phép; VAT cọc dồn vào đợt **không cọc** gần nhất phía sau, hết thì dồn ngược về đợt không cọc gần nhất phía trước | **A**: đơn giản, đúng ví dụ TL 45; Anh chọn B nếu thực tế có hợp đồng như vậy |

**Báo, không cần chọn:**
- M4 là module mẫu đầu tiên ở G4.
- Hạn giữ kết quả OCR tạm theo phiếu CSDL câu 2.
- Danh tính/mã hóa của SDK dựa trên mã phiên bí mật (phiếu CSDL câu 1 = A, Anh đã duyệt).

## 5. Anh duyệt bằng cách

Trả lời một dòng, ví dụ: **"Duyệt SDK bản 2; phạm vi CRM G2 đồng ý; câu 1 A, câu 2 A"**, hoặc ghi điểm cần đổi.

**Khi đã duyệt:** đủ 3 phiếu. Lập trình (G2) mở lại khi Anh ra CD mới.

## Phụ lục (chi tiết kỹ thuật)

- Đặc tả SDK: `docs\47-core\g1\DAC-TA-SDK.md` (12 dịch vụ, khung tiến trình, tài khoản Windows §4.4, `module.json` + `contract/` §6).
- Lớp kỹ thuật, bộ kiểm, sổ contract: `docs\47-core\g1\CONTRACT-DU-LIEU.md`.
- Lớp nghiệp vụ: `docs\47-core\g1\CONTRACT-NGHIEP-VU.md` (đủ bảng trường + ví dụ JSON từng contract).
- Biên bản review:
  - `g1\RV-G1C.md`, `g1\RV-G1C-OPUS.md`;
  - `g1\RV-NV.md`, `g1\RV-NV-OPUS.md`.

## Kết quả: ANH ĐÃ DUYỆT bản 2 (30/10/2026 17:30, CD-038)

- **Duyệt toàn phiếu** và phạm vi CRM thử Core ở G2 (mục 3).
- **Câu 1 – A:** lịch nghĩa vụ chỉ gồm giá bán chia %; phí theo dõi riêng.
- **Câu 2 – B:** cho phép cọc đợt cuối hoặc nhiều đợt cọc.
  - VAT cọc dồn vào đợt **không cọc gần nhất phía sau**; hết thì dồn ngược về đợt không cọc gần nhất phía trước.
  - Lịch toàn đợt cọc → lỗi.
