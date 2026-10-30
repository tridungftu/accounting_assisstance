# Review Opus — DAC-TA-API.md (G1b), quy ước chung và nguyên tắc cổng, vòng 1 (30/10/2026)

**Kết luận: chưa gửi Anh được — 1 Chặn** (khóa chống trùng cho route module). Khung đúng hướng:
- dạng lỗi và bảng mã HTTP;
- cookie `__Host-`, CSRF cả tiền phiên;
- pháp nhân qua header, kiểm ở máy chủ, ngoài phạm vi trả 404;
- 202 chỉ sau khi ghi bền;
- token liên tiến trình ký, có đối tượng nhận, nonce, hash body;
- giữ cổng, khởi động một lần cho nhiều người gọi;
- không engine/module nào luôn chạy; chỉ Admin bấm áp dụng (CD-028).

`A` = `docs\47-core\g1\DAC-TA-API.md`.

| # | Kết luận | Lý do và chỗ sửa |
|---|---|---|
| 1 Lỗi, HTTP | Đạt (1 Cần sửa nhẹ) | Schema `Loi` khóa `additionalProperties: false` (A:1483–1486) nên 422 không chỉ ra trường sai, trái TL 54 §6.1 "chi tiết an toàn".<br>**Sửa:**<br>• thêm `chi_tiet` tùy chọn `[{truong, ma}]`, không chứa giá trị;<br>• mã lỗi module phải khai trong contract, chưa khai thì trả 502. |
| 2 Chống trùng, `row_version` | **Chặn** | Xem C1. `row_version` là chuỗi, lệch trả 409, giữ riêng `expected_revision`: đạt (A:111). |
| 3 Việc lâu 202 | Cần sửa | (a) Sau khi Core khởi động lại hoặc hết lease:<br>• việc `running` mất heartbeat → `interrupted`, không bao giờ thành `succeeded`;<br>• chỉ tự xếp lại việc khai "thử lại an toàn"; việc ghi/nhập không chạy lại mù (TL 54 §6.3).<br>Thêm vào A:125.<br>(b) "Quyền giám sát trong phạm vi" (A:159) chưa có mã quyền: ghi rõ là quyền MTQ theo pháp nhân + module; không quyền xem việc người khác → 404. |
| 4 Danh tính sang module | Cần sửa | Đạt: token ký TTL 30 giây, đối tượng nhận là instance, nonce, hash body (A:197–201).<br>(a) **Chưa khớp RV-G1A S1:** module có login CSDL riêng nên vẫn tự đặt GUC danh tính được. **Sửa A:203:**<br>• token mang **mã ủy nhiệm bí mật** (không phải SID), gắn module + pháp nhân + hạn;<br>• hàm CSDL băm rồi đối chiếu `loi.phien_xac_thuc`;<br>• việc nền dùng mã ủy nhiệm theo `viec_id`;<br>• ghi thẳng: engine và máy phụ không có login CSDL.<br>(b) "Gọi SDK liên tiến trình phải xác thực tiến trình module" (A:203) chưa có cơ chế. **Sửa:**<br>• mỗi instance nhận credential riêng qua kênh khởi động (cùng ống `fromshare`);<br>• gắn instance ID, thu hồi khi dừng;<br>• không qua biến môi trường hay dòng lệnh. |
| 5 Dispatcher, chuyển ổ nghe | Cần sửa | Đạt (A:187–222):<br>• khởi động một lần, khóa theo module;<br>• 503 khi request chưa được chuyển; 504 đối chiếu bằng cùng khóa;<br>• engine cũ đóng rồi mở lại, không tự dò cổng.<br>(a) Thiếu **`dang_dung`** (A:226 chỉ có 5 trạng thái): chưa có quy tắc cho request đến lúc drain. Quyết định đóng khi rảnh phải lấy cùng khóa với dispatch và đếm cả request đồng bộ đang chạy.<br>(b) Khởi động lỗi liên tiếp chưa giãn cách: n lần lỗi → giữ `failed`, trả 503 ngay, chờ Admin.<br>(c) Chuyển ổ nghe chỉ trên máy Core; máy phụ (CD-021) chỉ kéo việc, không có cổng. |
| 6 Tệp, phiên, CSRF, Origin | Đạt (2 Cần sửa nhẹ) | Đạt (A:127–129):<br>• tải xuống theo ID, kiểm quyền trước khi trả bytes;<br>• `no-store`, `nosniff`;<br>• tải lên có CSRF, khóa chống trùng, hash.<br>(a) Cookie `__Host-` bắt buộc `Secure` → qua `http://<IP LAN>` sẽ không đăng nhập được. Ghi rõ TLS là điều kiện phục vụ ngoài loopback (CD-019); DEMO loopback vẫn được (A:39).<br>(b) Tệp do module sinh ra (DOCX CRM, báo cáo M4): module ghi qua SDK vào kho tệp Core, người dùng tải qua `/tep/{id}/noi-dung`; Core không chuyển bytes thô từ module. |
| 7 Câu cho Anh | Cần sửa | • C2, C4 là kỹ thuật → chuyển thành "báo" (C4 phụ thuộc C1).<br>• C6 trùng phiếu CSDL câu 2 (hạn giữ dữ liệu tạm) → gộp sang phiếu đó.<br>• C1 trùng phiếu CSDL câu 3 → hỏi Anh một lần. |

## Chặn

- **C1. Ai giữ biên nhận chống trùng cho `/module/*`.** A:101–108 mô tả biên nhận ở Core (24 giờ, phạm vi có người dùng, fingerprint có đường dẫn, "cùng transaction khi có thể"). Ba chỗ vỡ:
  - **Không cùng transaction được:** theo CD-028 module là tiến trình riêng với login riêng, nên biên nhận ở Core không thể nằm cùng transaction với lệnh ghi nghiệp vụ. Core sập giữa chừng → khóa kẹt "chưa xác định" (A:103).
  - **Mâu thuẫn mẫu K2:** biên nhận K2 vĩnh viễn, bất biến, phạm vi `(phap_nhan_id, module, operation, client_key)` (`src\kho_tri_thuc\ha_tang\pg_migrations.py:3385–3395`). K2 kiểm quyền rồi mới tra biên nhận; digest không gồm khóa (`k2\crm_mau.py:7`, `:160–163`). Mốc 24 giờ trái với mẫu này, và C4 dễ khiến Anh tưởng sau 24 giờ được ghi trùng.
  - **Fingerprint có đường dẫn** trái `ANH-XA-ROUTE.md:344–351`: route cũ và v1 phải dùng chung biên nhận.

  **Sửa §2.4:**
  - route do Core sở hữu: Core giữ biên nhận cùng transaction;
  - `/module/*`: Core chỉ khóa yêu cầu đang chạy và chuyển `Idempotency-Key` trong token; module (qua SDK) giữ biên nhận **vĩnh viễn** cùng transaction nghiệp vụ theo mẫu K2, là nguồn đối chiếu duy nhất khi 504;
  - fingerprint = mã operation + body chuẩn hóa, không gồm đường dẫn;
  - phạm vi thêm người tạo, hoặc phát lại thì kiểm người gọi có quyền đọc kết quả;
  - mốc 24 giờ chỉ áp biên nhận Core.

## Thứ tự Cần sửa

4a, 4b (nhất quán phiếu CSDL S1/S2) → 5a, 5b → 3a → 6a → 6b → 1 → 3b → 5c.

## Để sau

- `description` OpenAPI tiếng Việt không dấu.
- PUT `/quan-tri/engine/{ma}/ho-so-chay` (A:167) có audit như áp dụng đề xuất.
- Báo giá có hai CAS (A:361–362): mỗi operation khai rõ trường CAS bắt buộc.

## Câu chốt cho phiếu API (tối đa 3)

1. **Nguồn đăng nhập** (hỏi chung với phiếu CSDL):
   - A: tài khoản Core (khuyến nghị bản đầu);
   - B: danh tính sẵn có.
2. **Chờ khi mở module sau lúc rảnh.** Không module nào luôn chạy nếu Admin chưa áp dụng.
   - A (khuyến nghị, ít RAM): tự đóng sau 5 phút rảnh; lần mở sau màn hình hiện "đang khởi động" và tự thử lại;
   - B: giữ 30 phút.
3. **Giới hạn tệp tải lên:**
   - A: 20 MiB;
   - B: 50 MiB.

   Cần Anh cho biết hồ sơ scan M4 · Nghiệm thu & chi phí dự án thường nặng bao nhiêu.

Vòng 2 (nếu có) chỉ xem C1 + 4a/4b.
