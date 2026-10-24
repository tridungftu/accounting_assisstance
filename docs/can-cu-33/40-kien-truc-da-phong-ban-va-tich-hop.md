# 40 · Kiến trúc đa phòng ban & tích hợp — một CSDL chung, module theo quyền, phần mềm nối theo hai lớp

**Ngày lập:** 17/10/2026 · **Trạng thái:** **ĐÃ CHỐT 17/10/2026** — anh Dũng trả lời 4 câu tự do (§1) rồi chốt 4 lựa chọn (§11). Thiết kế, chưa lập trình; hiện thực theo lộ trình §9, **không đổi V13 đang làm**.
**Vị trí:** bổ sung cho TL 35 (kiến trúc tổng thể) — thêm **nguyên tắc kiến trúc 11** (tích hợp hai lớp) và chi tiết hóa dòng "Giao diện" của TL 35 §3; mở rộng TL 38 (thêm schema `giao_tiep`, vai trò CSDL theo phần mềm); không đổi TL 39.
**Bảo mật:** nội bộ — nêu tên dự án nội bộ và cấu trúc hệ thống; không đưa ra ngoài.

---

## 0. Kết luận trước

- **Có thể dùng một CSDL chung mà mỗi phòng chỉ dùng module mình cần**, vì PostgreSQL (V13) là CSDL máy chủ, không phải file như SQLite. Câu hỏi thật không phải "cài hết hay cài từng phần" mà là **"module chạy ở máy nào và nối CSDL chung bằng cách nào"**.
- **Mô hình chốt:** *web trung tâm cho module mới* (phòng ban mở trình duyệt, menu hiện theo quyền, không cài gì) + *phần mềm có sẵn giữ chỗ đang chạy* và nối vào CSDL chung; chuyển lên máy chủ khi có máy chủ thật. Máy chủ pilot = **máy anh** (TL 35 §3), sau đó máy chủ nội bộ bằng sao lưu – phục hồi.
- **Nguyên tắc kiến trúc 11 — tích hợp hai lớp:** *trong nhà* (phần mềm **anh giữ mã**) nối thẳng PostgreSQL bằng vai trò riêng, **chỉ thấy schema `giao_tiep`** (view + hàm có phiên bản) và hàng đợi sự kiện; *ngoài vào* (không phải mã của anh: Junsky, Base, Frappe HR, Google Sheets, nhà cung cấp sau này) **không bao giờ nối CSDL** — chỉ qua bộ tiếp nhận K1 (file/API có cấu trúc, mình chủ động đọc) hoặc một cổng API HTTP có token của mình khi họ cần đẩy vào.
- **CRM cho phòng bán hàng = CRM kế toán** (TL 32): nhập hợp đồng/phụ lục mới ở trạng thái **chờ duyệt**, xem lịch thu và công nợ; kế toán duyệt, CFO duyệt tham số (TL 37). Không mở pipeline bán hàng (vẫn ngoài phạm vi, TL 35 §7).
- **Không đổi V13.** Việc mới xếp vào V14 (đăng nhập, web đa người dùng, `giao_tiep` v1, vai trò theo phần mềm, RLS) và V16 (CRM kế toán cho phòng bán hàng, nối #5). Hàng đợi #30–#33.

## 1. Vấn đề anh đặt ra và bốn câu trả lời làm căn cứ (17/10/2026)

Anh: *"Các bộ phận cần từng module khác nhau — phòng dự án chủ yếu dùng module rà soát xây dựng + Base; phòng bán hàng module CRM. Có cách nào kết nối API giữa các phần mềm để CSDL được tạo chung nhưng các bước thực hiện ở từng máy theo từng module được cài, không phải cài hết tất cả?"*

| # | Câu hỏi của Claude | Trả lời của anh | Hệ quả thiết kế |
|---|---|---|---|
| 1 | Phòng bán hàng dùng CRM kế toán (hợp đồng – lịch thu – công nợ) hay CRM bán hàng (pipeline)? | "Chủ yếu như phòng kế toán, liên quan đến hợp đồng" | CRM kế toán, đúng TL 32/35; phòng bán hàng là **người dùng web** của cùng hệ thống |
| 2 | Phòng dự án dùng #5 Review thế nào? | "Chỉ 1 hoặc 2 máy chạy #5" | #5 **giữ chỗ đang chạy**, nối CSDL chung; không cần agent riêng; chuyển lên máy chủ khi có |
| 3 | Ai giữ mã các phần mềm Node (#7, #2)? | "Mã các phần mềm Node là tôi giữ" | #7, #2 thuộc lớp **trong nhà** |
| 4 | Ngại cho phần mềm khác nối thẳng CSDL kế toán không? | "Phần mềm của tôi thì không ngại; phần mềm khác thì ngại" | → **Nguyên tắc 11**: ranh giới là *ai giữ mã*, không phải ngôn ngữ hay phòng ban |

## 2. Ba nhóm module theo **nơi bắt buộc phải chạy** (không theo phòng ban)

Hiện trạng đã là web: #5 Review là web cổng 8600, #1 Kiểm tra đề xuất là HTML cục bộ, #7 Tải hóa đơn là `localhost:3456`, #2 Request là web 130 người dùng (TL 31). Mỗi "module" hôm nay là một tiến trình web chạy trên máy của một người; người khác muốn dùng thì mở trình duyệt vào máy đó — tức "web trung tâm" ở quy mô nhỏ.

| Nhóm | Module / phần mềm | Chạy ở | Phía người dùng |
|---|---|---|---|
| **1 · Chỉ cần người bấm + file tải lên** | Màn hình duyệt chung K5 (TL 37) · CRM kế toán (hợp đồng – lịch thu – công nợ) · #1 Kiểm tra đề xuất Base · #5 Review hồ sơ xây dựng (hiện 1–2 máy phòng dự án) · báo cáo đường ống | **Máy chủ** (pilot: máy anh); #5 giữ chỗ đang chạy đến khi có máy chủ thật | **Trình duyệt**, đăng nhập, menu theo quyền; **không cài gì** |
| **2 · Đụng tài khoản / thiết bị / file cục bộ** | #7 Tải hóa đơn (đăng nhập cổng thuế, Playwright) · #8 Backup Base (token, lịch chạy) · bộ đọc eFAST · OCR #12 · Local AI / Mask #13 | Máy chủ **hoặc một máy được chỉ định** | Một `.cmd` nhỏ ("agent tại chỗ") chỉ trên máy đó; kết quả vào CSDL chung qua `giao_tiep` hoặc xả file cho K1 |
| **3 · Nguồn nằm ở Google** | #9 Khoản vay · #10 Kho · #11 Nước thải (Sheets + Apps Script) | Google | Không cài; hệ thống **đọc** qua API Sheets (chốt 15/10, TL 31) |

"Cài theo module" khi đó có nghĩa: **mỗi module là một gói Python riêng (plugin) đăng ký với lõi**; máy chủ cài gói nào thì có module đó; menu người dùng hiện theo `master.phan_quyen`, **không theo máy**. Phòng dự án và phòng bán hàng không cài gì, trừ khi họ giữ một máy nhóm 2.

## 3. Mô hình triển khai: web trung tâm + module cắm thêm

```
 Phòng kế toán ──┐                     ┌─────────────── MÁY CHỦ (pilot: máy anh) ───────────────┐
 Phòng bán hàng ─┼─ trình duyệt ──────►│  Ứng dụng web (một tiến trình)                          │
 Phòng dự án ────┘   (đăng nhập)       │   ├─ lõi: đăng nhập · phân quyền · nhật ký · cổng AI/Mask│
                                       │   ├─ module K5 duyệt chung   [modules] bật/tắt           │
 #5 Review (1–2 máy) ─ vai trò riêng ─►│   ├─ module CRM kế toán                                  │
 #7 Tải HĐ · #8 Base ─ xả file / ─────►│   ├─ module báo cáo · K1 bộ tiếp nhận                    │
                       vai trò riêng   │   └─ (sau) module M4, M9, M8…                             │
 #2 Request (sau 31/12) ─ vai trò ────►│  PostgreSQL: master · kho · nhat_ky · bao_mat · giao_tiep │
 Google Sheets ◄── đọc API ────────────│                                                           │
 Junsky · Base · HR ── K1 file/API ───►│  (ngoài vào: không nối CSDL; cổng API HTTP khi cần)      │
                                       └───────────────────────────────────────────────────────────┘
```

- **Một tiến trình web, nhiều module**: module là gói Python đăng ký với lõi (`entry point`), bật/tắt bằng `[modules]` trong `cau_hinh.*.toml`. Pilot: tất cả module trên máy anh; sau này tách tiến trình nếu tải lớn — không đổi mã nghiệp vụ.
- **Menu theo quyền**: `master.nguoi_dung.vai_tro` mở rộng thêm `BAN_HANG`, `DU_AN` (bên cạnh KE_TOAN / KE_TOAN_TRUONG / CFO / NHAP_JUNSKY / XEM — TL 38); `phan_quyen` giữ `duyet_loai_viec[]` và thêm `module[]` được thấy. Một người có thể thuộc nhiều pháp nhân; CFO "Tất cả" (TL 37).
- **Máy chủ pilot = máy anh** (TL 35 §3, anh xác nhận lại 17/10): hệ quả là **máy anh phải bật khi phòng khác dùng**; đổi lại nâng cấp một chỗ, dữ liệu kế toán không rời máy chủ, phân quyền một chỗ. Chuyển máy chủ nội bộ = `pg_dump` → phục hồi → đổi `KHO_PG_DSN` trong `.env` và địa chỉ web.
- **Giao diện hiện nghe `127.0.0.1`** (TL 35 §3) → V14 mở ra mạng nội bộ: `[server] bind = 0.0.0.0` (hoặc địa chỉ LAN), HTTPS nội bộ, đăng nhập bắt buộc, chỉ mạng nội bộ (tường lửa Windows), nhật ký đăng nhập trong `nhat_ky.su_kien`.

## 4. Nguyên tắc kiến trúc 11 — tích hợp hai lớp (bổ sung TL 35 §5)

> **11. Trong nhà qua CSDL, ngoài vào qua cổng.** Phần mềm anh giữ mã nối thẳng PostgreSQL bằng vai trò riêng và chỉ thấy schema `giao_tiep` (view + hàm có phiên bản) cùng hàng đợi sự kiện — không chạm bảng thật, `bao_mat`, hay schema của phần mềm khác. Phần mềm không phải mã của anh không bao giờ nối CSDL: chỉ qua bộ tiếp nhận K1 (file/API có cấu trúc, mình chủ động đọc) hoặc một cổng API HTTP có token của mình khi họ cần đẩy vào.

Lý do chọn ranh giới "ai giữ mã": phần mềm của anh đổi được cùng nhịp với schema (Claude/Codex sửa cả hai bên), còn phần mềm người khác không kiểm soát được cách họ truy vấn, không ép được họ dùng view có phiên bản, và lỗi của họ có thể khóa bảng hoặc làm đầy nhật ký.

| Phần mềm (TL 31) | Mã của anh? | Lớp | Cách nối chốt | Khóa chung phải thống nhất | Khi nào |
|---|---|---|---|---|---|
| #5 Review hồ sơ thanh toán xây dựng (Python web 8600) | Có | Trong nhà | Ghi kết quả review vào schema riêng `du_an` qua hàm `giao_tiep.v1_ghi_ket_qua_review(...)`; kho đọc view `giao_tiep.v1_nghiem_thu_da_kiem` → M4 | **Mã hợp đồng thầu**, đợt thanh toán, mã dự án | V16 (cùng CRM) |
| #1 Kiểm tra đề xuất Base (Python, YAML) | Có | Trong nhà | **Đọc** danh mục loại chi phí dùng chung từ master qua `giao_tiep.v1_khoan_muc_phi` (vai trò chỉ đọc) | Ai là chủ danh mục loại chi phí (đang chờ, hàng đợi) | V14–V15 |
| #7 Tải hóa đơn điện tử (Node + Playwright) | Có | Trong nhà | **Giữ nguyên**: xả XML + bảng kê vào thư mục `paths.invoice`, K1 quét nạp (đang chạy từ V12). Không ghi CSDL — không cần đổi mã | Kỳ tải, MST pháp nhân | Đã có |
| #8 Backup Base Request (Python) | Có | Trong nhà | Như #7 (index Excel + file) ở pilot; khi tiện: ghi hàng đợi `giao_tiep.su_kien_cho` loại `RQ_MOI` | Mã RQ | Đã có; nâng ở V17+ |
| #2 Request thay Base (Node/TS, 130 người, go-live 31/12/2026) | Có | Trong nhà | Sau go-live: ghi `giao_tiep` (hàm `v1_ghi_rq`) hoặc gửi webhook → hàng đợi; theo **schema trung gian RQ** (TL 31: Dự án, Chi phí, nội dung, STK, nhóm G, hóa đơn) | Mã RQ, mã dự án, nhóm G | V17+ (sau 31/12) |
| Bot trợ lý → agent Zalo (#14) | Có | Trong nhà | Là một module của lõi (không phải phần mềm ngoài) | — | V15 |
| #9 Khoản vay · #10 Kho · #11 Nước thải (Google Sheets) | Có (Apps Script) nhưng **không nối được PostgreSQL** | Nguồn đọc | Hệ thống đọc qua API Sheets (service account chỉ đọc, `.env`) — chốt 15/10 | Mã hợp đồng vay, mã vật tư, mã khách | M9 / M5 / M3 |
| Junsky (ERP) | Không | Ngoài vào | File Excel nhập `CB_tmpEntry1/2` (mức 2) + bộ đọc sổ xuất (K1) | Mã đối tượng, mã dự án, TK | Đã có |
| Base (SaaS) | Không | Ngoài vào | Qua #8 Backup (API Base do mã của anh gọi) — Base không bao giờ thấy CSDL | Mã RQ | Đã có |
| Frappe HR (#4, WSL2) | Không (mã nguồn mở, không phải của anh) | Ngoài vào | Xuất CSV bảng lương/tạm ứng → K1 (M7, M2) | Mã nhân viên Junsky | Sau khảo sát E1 |
| OCR #12 · Local Mask #13 | Có | Dịch vụ nội bộ | Lõi gọi HTTP cục bộ (8017–8019, 8018) — chiều ngược: lõi là *khách*, không cấp quyền CSDL cho chúng | — | V15 |

## 5. Schema `giao_tiep` — "API trong CSDL" (bổ sung TL 38; hiện thực ở V14)

Mục đích: phần mềm trong nhà **không phụ thuộc cấu trúc bảng**. Đổi bảng → sửa view/hàm, phần mềm kia không biết.

| Thành phần | Quy ước | Ghi chú |
|---|---|---|
| **View chỉ đọc** `giao_tiep.v1_<tên>` | Tên cột ổn định, kiểu rõ; mỗi view ghi `COMMENT` mô tả + phiên bản; **không bao giờ đổi nghĩa cột của `v1_`** — thêm cột được, bỏ/đổi nghĩa thì tạo `v2_` song song và giữ `v1_` ít nhất 2 chu kỳ V | Ví dụ: `v1_hop_dong`, `v1_lich_thu`, `v1_cong_no_mo`, `v1_khoan_muc_phi`, `v1_du_an`, `v1_nghiem_thu_da_kiem` |
| **Hàm ghi** `giao_tiep.v1_ghi_<việc>(jsonb) → uuid` | `SECURITY DEFINER` (chủ `kho_app`), kiểm tra schema JSON đầu vào, ghi vào schema của phần mềm gọi (`du_an`, `rq`) **hoặc** vào hàng đợi; luôn ghi `nhat_ky.su_kien` (actor = tên vai trò gọi, ví dụ `APP_REVIEW`); trả về id để phần mềm gọi lưu đối chiếu | Phần mềm gọi **không có INSERT trực tiếp** vào bảng nào |
| **Hàng đợi** `giao_tiep.su_kien_cho` | `id uuid · phap_nhan_id · nguon (APP_REVIEW/APP_BASE/APP_REQUEST/CONG_API) · loai (NGHIEM_THU_DA_KIEM/RQ_MOI/HOP_DONG_MOI…) · khoa (mã hợp đồng/RQ) · noi_dung jsonb · trang_thai (CHO/DANG_XU_LY/DA_XU_LY/LOI) · loi_text · tao_luc · xu_ly_luc` · unique(nguon, loai, khoa, hash(noi_dung)) để chạy lại không trùng | Lõi đọc theo lịch (K1), bóc tách → `kho.chung_tu`/`master`; dòng lỗi hiện ở K5 loại V8 |
| **Schema riêng mỗi phần mềm ghi** | `du_an` (#5), `rq` (#8/#2) — thuộc sở hữu `kho_app`, phần mềm chỉ ghi qua hàm | "Mỗi bảng một chủ": module nào tạo bảng thì chỉ module đó ghi |
| **Vai trò CSDL theo phần mềm** | `app_review` (#5) · `app_kiem_tra_dx` (#1, chỉ đọc) · `app_base` (#8) · `app_request` (#2) — thay vai trò `app_doc` chung chung của V13 (giữ `app_doc` cho báo cáo chỉ đọc nội bộ). Mỗi vai trò: `GRANT USAGE ON SCHEMA giao_tiep` + `SELECT` đúng các view cần + `EXECUTE` đúng các hàm cần; **REVOKE mọi thứ khác**; `NOINHERIT`; mật khẩu riêng trong `.env` của phần mềm đó | Mẫu đã có ở migration 0008/0009 (REVOKE TRUNCATE, ALTER DEFAULT PRIVILEGES) |
| **Phân quyền theo pháp nhân** | RLS trên bảng thật theo `phan_quyen` (hàng đợi #16, V14); view `giao_tiep` kế thừa RLS (`security_invoker = true`) để #5 pháp nhân A không thấy B | PostgreSQL ≥ 15 có `security_invoker` |
| **Không có trong `giao_tiep`** | `bao_mat`, cột mã hóa (STK/CCCD), bút toán đề xuất, tri thức, nhật ký | Phần mềm trong nhà không cần |

Số đo kiểm tra khi hiện thực: với vai trò `app_review` đăng nhập, `SELECT` bảng thật phải bị từ chối (test như t15 của V13); hàm ghi hai lần cùng nội dung → một dòng hàng đợi.

## 6. Cổng API HTTP cho lớp "ngoài vào" — chỉ khi cần

- Không có ở V14. Chỉ dựng khi một phần mềm **không phải mã của anh** cần *đẩy* dữ liệu vào (ví dụ nhà cung cấp Request khác, hoặc phần mềm HR thương mại). Khi đó: một đầu `POST /v1/su-kien` nhận cùng cấu trúc với `giao_tiep.su_kien_cho`, token riêng từng đối tác trong `.env`, giới hạn tần suất, ghi `nhat_ky.cong_ai_goi`/`su_kien`; cổng chỉ ghi hàng đợi, **không** gọi nghiệp vụ.
- Phần mềm trong nhà **không** dùng cổng này (dùng `giao_tiep` thẳng) — tránh hai đường vào.

## 7. Module CRM kế toán cho phòng bán hàng (phạm vi chốt 17/10; hiện thực V16)

| Phòng bán hàng được | Cơ chế | Ai duyệt |
|---|---|---|
| **Nhập hợp đồng mới / phụ lục** (mẫu theo loại hình doanh thu, TL 32) kèm file PDF | `master.hop_dong` + `hop_dong_phien_ban` với `nguon = BAN_HANG` (thêm giá trị vào danh sách LLM/#5/#6/SHEET/TAY của TL 38), `trang_thai = CHO_DUYET` → việc **V4** (hợp đồng/danh mục mới) và **V3** (tham số) trên màn hình duyệt chung | Kế toán công nợ kiểm, **CFO duyệt tham số** (TL 37) |
| **Xem** hợp đồng đã duyệt, lịch thu, trạng thái thu tiền, công nợ của khách mình | View theo RLS pháp nhân + vai trò `BAN_HANG`; dữ liệu công nợ từ `kho.cong_no_mo` (sổ Junsky đã nạp) | — |
| **Gửi đề nghị / trả lời câu hỏi** (tiền về lệch đợt, khách đổi STK) | Qua agent Zalo (V5) hoặc nút "Đề nghị" trên web → việc V4/V5 | Kế toán |
| **Không được** | Sửa hợp đồng đã duyệt (phụ lục = phiên bản mới chờ duyệt); thấy bút toán, tri thức, `bao_mat`; thấy pháp nhân ngoài quyền | — |

Hệ quả schema: không thêm bảng; thêm giá trị liệt kê (`nguon = BAN_HANG`, `vai_tro = BAN_HANG/DU_AN`), thêm `phan_quyen.module[]`. Ghi vào bản cập nhật TL 38 cùng G12/G13 ở V14.

## 8. Bảo mật & vận hành khi lên nhiều người dùng (V14)

- **Đăng nhập**: tên + mật khẩu băm (argon2/bcrypt) trong `master.nguoi_dung`; khóa sau 5 lần sai; phiên có hạn; đổi mật khẩu lần đầu. SSO Google Workspace **[CẦN ANH XÁC NHẬN]** có dùng không — nếu có thì V15.
- **HTTPS nội bộ**: chứng chỉ nội bộ (mkcert hoặc CA của IT); không mở ra Internet; agent Zalo cần webhook → tunnel/reverse proxy riêng chỉ cho đường Zalo (TL 35 §3).
- **Tường lửa**: chỉ cổng web + 5432 trong mạng nội bộ; 5432 chỉ cho địa chỉ các máy chạy phần mềm trong nhà (`pg_hba.conf` theo địa chỉ + vai trò).
- **Sao lưu**: `pg_dump` hằng đêm vào `var\sao-luu-pg\` + bản ngoài máy (ổ khác/NAS) hằng tuần; thử phục hồi mỗi V (hàng đợi #26).
- **Nhật ký**: đăng nhập/đăng xuất/sai mật khẩu, mọi hàm `giao_tiep` gọi, mọi thay đổi quyền → `nhat_ky.su_kien` (chỉ ghi thêm, đã có trigger V13).
- **Dữ liệu ra ngoài**: không đổi — chỉ cổng AI sau Mask bảy thứ (TL 35 §3, TL 38 §4b); phần mềm trong nhà không gọi cổng AI thẳng.

## 9. Lộ trình (cập nhật TL 35 §9 / TL 39)

| V | Nội dung | Thêm từ TL 40 |
|---|---|---|
| **V13** (đang làm) | Xương sống K2: PostgreSQL 4 schema, bộ chuyển, lớp truy cập hai engine, chạy song song T8 | **Không đổi** |
| **V14** | K3 bộ lọc tri thức trên CSDL mới + K5 màn hình duyệt chung (web) | **Đăng nhập + phân quyền (#16) + RLS**; `[server] bind` ra LAN + HTTPS nội bộ; schema `giao_tiep` v1 (view đọc + hàng đợi + 2 hàm ghi đầu); vai trò theo phần mềm; `[modules]` bật/tắt; TL 38 cập nhật |
| **V15** | Cổng AI + Mask + agent Zalo | #1 đọc `v1_khoan_muc_phi`; (SSO nếu anh chốt) |
| **V16** | CRM kế toán từ hợp đồng (TL 32) | **Module CRM cho phòng bán hàng** (§7); **#5 nối `giao_tiep`** → M4 |
| **V17+** | M4 / M9 / M8 theo khảo sát | #2 Request ghi `giao_tiep` sau go-live 31/12; #8 nâng lên hàng đợi; cổng API HTTP chỉ khi có phần mềm ngoài |

## 10. Hệ quả cho tài liệu khác

- **TL 35**: §3 dòng "Giao diện" → web trung tâm, LAN + HTTPS ở V14; §5 thêm **nguyên tắc 11**; §6 thêm dòng 17/10; §7 giữ "CRM bán hàng (pipeline)" ngoài phạm vi, ghi rõ CRM kế toán *cho phòng bán hàng dùng* nằm trong.
- **TL 38**: thêm schema `giao_tiep` (§5 trên), vai trò `app_review/app_kiem_tra_dx/app_base/app_request`, giá trị liệt kê mới (§7) — làm cùng G12/G13 ở V14.
- **TL 39**: không đổi.
- **TL 30 khảo sát**: thêm phần cho phòng bán hàng — ai đang nhập/lưu hợp đồng, bao nhiêu hợp đồng + phụ lục mỗi tháng, mẫu hợp đồng theo loại hình doanh thu (nối TL 35 §8 điểm 7).
- **Hàng đợi**: #30 `giao_tiep` + vai trò theo phần mềm (V14) · #31 web đa người dùng: đăng nhập, LAN, HTTPS, `[modules]` (V14, gộp với #16) · #32 CRM kế toán cho phòng bán hàng (V16) · #33 cổng API HTTP lớp ngoài vào (khi cần).

## 11. Nhật ký quyết định 17/10/2026

| Giờ | Câu | Anh chốt |
|---|---|---|
| 12:07 | Anh nêu vấn đề (§1) | — |
| 12:40 | Bảng chọn lần 1: mô hình, tích hợp, máy chủ, ghi nhận | Máy chủ pilot = **máy anh**; mô hình và tích hợp: *trao đổi thêm*; chưa soạn TL 40 |
| 13:06 | 4 câu tự do (§1) | CRM kế toán · #5 trên 1–2 máy · anh giữ mã Node · ngại phần mềm *không phải của anh* nối CSDL |
| 13:20 | Bảng chọn lần 2 | **Web trung tâm cho module mới; phần mềm có sẵn giữ chỗ chạy, nối CSDL chung** · **Trong nhà qua CSDL (`giao_tiep`), ngoài vào qua K1/cổng API** · **Phòng bán hàng nhập hợp đồng/phụ lục chờ duyệt + xem lịch thu, công nợ** · **Soạn TL 40 + hàng đợi, V13 tiếp tục** |

## 12. Điểm còn mở (không chặn V13)

1. **SSO Google Workspace** cho đăng nhập web — có dùng không? [CẦN ANH XÁC NHẬN]
2. **Tên schema cho #5** (`du_an`) và cho RQ (`rq`) — đề xuất, chốt khi làm V14.
3. **Chủ danh mục loại chi phí** dùng chung với #1 (đang chờ từ TL 31) — quyết định trước khi mở `v1_khoan_muc_phi`.
4. **Chứng chỉ HTTPS nội bộ**: mkcert tự quản hay CA của IT — hỏi IT khi khảo sát (TL 30).
5. **#2 Request**: lịch nối sau go-live 31/12/2026; xác nhận schema trung gian RQ (TL 31) với đội làm #2 (anh).
