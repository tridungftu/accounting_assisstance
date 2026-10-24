# CRM-01 — kiểm độc lập phiên HTTP DEMO

Ngày 19/10/2026, khoảng06:34. Bản Claude bàn giao đầu đã terminal. Agent chạy HTTP thật trên PostgreSQL DEMO bằng login thường; Codex đã đọc `result.json` để đối chiếu kết quả. Không mock service, không truy cập môi trường THAT, không lưu token/password, không chạy browser GUI.

**12 ca: 8 control đạt, 4 vi phạm, không setup error/skip.** Hai client có CookieJar riêng, cùng token của shell local, gửi request tuần tự. Đây là kiểm sự tách biệt danh tính của hai phiên, không phải kiểm xác thực production. GET CRM có mutation_lock; không có kết luận race kết nối từ probe này.

## Control đã đạt

- Không token bị403/SESSION_TOKEN; body tự truyền actor bị400/CRM_CLIENT_IDENTITY.
- A chọn MO_PHONG_KT_A, GET trả đúng vai và chỉ PN_DEMO_A; duyệt bị400/KHONG_CO_QUYEN_HANH_DONG.
- B chọn MO_PHONG_KT_B, GET B trả đúng vai và chỉ PN_DEMO_B.
- Sau khi đổi vai chung về KT_A, duyệt lại bị400 như control trước.
- Kết nối PG thực không superuser, không BYPASSRLS; guard giữ file bật. Hai CookieJar thật tách biệt.

## Bốn vi phạm tái hiện

| Ca | Expected | Thực tế |
|---|---|---|
| B chọn KT_B rồi A GET | A vẫn KT_A/PN_A | A trở thành KT_B, chỉ thấy PN_B |
| A kiểm hồ sơ B sau thao tác của B | A không có quyền PN_B | HTTP200, người kiểm ghi MO_PHONG_KT_B |
| B chọn CFO rồi A GET | A vẫn KT_A/PN_A | A thành MO_PHONG_CFO, thấy cả hai PN |
| A duyệt hồ sơ A sau thao tác của B | Kế toán bị từ chối | HTTP200, DB DA_DUYET, người duyệt MO_PHONG_CFO |

Nguyên nhân phù hợp code: `LocalApp.crm_nguoi` là thuộc tính dùng chung trong app, route danh-tinh thay thuộc tính này; GET/action đọc lại cùng thuộc tính. DEMO role chooser có chủ ý nhưng đầu bài yêu cầu danh tính do server gắn riêng phiên. Không cần coi trình chọn vai DEMO là login production để sửa sự lẫn cửa sổ này.

## Evidence và phạm vi

- `var/codex-dieu-phoi/crm-http-independent-20261019-063432-ed456a/result.json`; giữ DB DEMO và login role, không cleanup.
- Source trước/sau không đổi: server SHA256 `9fe88eca3ce3a6f5adff23e8c48062405154b777a1ce3c990bfe86549ff49b3f`; crm `6936db70742446a255ac865553012ac086b4beb0c4df6bef0176221eaf19965a`; app.js `9c60f968dde9a18bded06a71473a2a39dec4500b15b33d3fa840634e6fe0a23e`.
- Chưa kiểm GUI, production authentication/HTTPS hoặc toàn bộ các vai TL40. Không cộng HTTP pass thành đã bấm GUI. Review thiếu export/resolve/re-extraction nằm ở `REVIEW-CRM-PHAM-VI-VA-TAI-SU-DUNG-01.md`.
