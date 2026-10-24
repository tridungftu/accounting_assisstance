# CRM-42-00 · Ma trận màn hình – dữ liệu – quyền – ca kiểm (artifact 1/2)

**Gói:** CRM-42-00 — DOCS_ONLY. Đây là tài liệu thiết kế thực thi, không phải code, migration hay test.
**Ngày:** 20/10/2026.
**Kết quả tối đa:** `SCREEN_SCHEMA_DELTA_READY_FOR_ROOT_REVIEW`.
- CRM theo 41/42 **chưa** được code, kiểm hay nghiệm thu.
- Không bảng/cột nào ở đây đã được migrate.
- M4 vẫn là PARTIAL_CODE: chưa có GUI đủ, chưa kiểm runtime.

**Artifact đi kèm:** `docs/CRM-42-00-DELTA-DU-LIEU-API-QUYEN.md` — hiện trạng có căn cứ, delta, contract API và handoff coding.

---

## 0. Căn cứ đã đọc (chỉ Read/Glob/Grep, không chạy gì)

### Tài liệu

| Căn cứ | Bản đọc | Ghi chú |
|---|---|---|
| Đầu bài | `docs/GIAO-CLAUDE-CRM-42-00-MA-TRAN-MAN-HINH.md` (92 dòng) | — |
| 41 — CRM-G và engine | `docs/CRM-41-42-REFERENCE-20261020/41-…md` (140 dòng) | Hash theo đầu bài `d192f99c…`; coder không tính lại |
| 42 — Màn hình CRM | `docs/CRM-41-42-REFERENCE-20261020/42-…md` (240 dòng) | Hash theo đầu bài `445fd2a1…` |
| CLAUDE.md | cùng thư mục reference | — |
| Hàng chờ | `docs/HANG-CHO-CRM-41-42.md` — **bản hiện hành 92 dòng**, Root xác nhận SHA256 `6c344ab8b9f9f7cfe61b2a611b9ea3218db5b94e9a7efd1e89fdb26eddaf4c15` | Đoạn "M4 và CRM được Anh yêu cầu triển khai dần" thay header cũ. Chi tiết bản 83 dòng và hash cũ **không** dùng làm căn cứ. |
| TL32 | `docs/can-cu-33/32-…md`, §0–§3 | — |
| TL35 | `docs/can-cu-33/35-…md`, §3A, §3 hạ tầng, §4, §5 | — |
| TL37 | bảng V1–V8 và nút | — |
| TL38 | chỉ dòng CCCD/STK/mã hóa | — |
| TL40 | §7 và `cong_no_mo` | — |

### Baseline source (đọc tĩnh)

- `k2/crm.py`: các đoạn 1–311 và 400–805.
- `k2/crm_phan_tich.py`: 200–300 + danh sách hàm.
- `k2/loai_hinh_demo.py` và `k2/quyen.py`: đọc toàn bộ.
- `nguon/trich_hop_dong_6.py`: 1–98.
- `giao_dien/server.py`: các hàm `crm_*` và route `/api/crm`.
- `giao_dien/assets/index.html`: trang `#hopdong` CRM DEMO hiện có.
- `ha_tang/pg_migrations.py`: các đoạn CRM — bảng 286–407, 550–589, 968–1010; trigger 2469–2558; guard liên kết 2964–2967.

**M4 là PARTIAL_FROZEN_NOT_ACCEPTED.** Root đã lưu snapshot 285 file và review tĩnh độc lập; chưa kiểm runtime hoặc nghiệm thu, interface cuối đang được sửa trong M4-01B. Vì vậy:
- Mọi điểm nối engine (E1–E5) mang nhãn `CHO_DAU_VAO: interface M4 được kiểm và chốt sau repair`; snapshot không đồng nghĩa interface đã đạt.
- Phần CRM không phụ thuộc engine vẫn giao được.

### Hai bộ nhãn dùng trong mọi bảng

**Mức xác nhận** (bản chất quyết định):

| Nhãn | Nghĩa |
|---|---|
| `DA_CHOT_42_4_DIEM` | Bốn điểm đã chốt ở 42 §16 |
| `DA_GHI_CHOT_41` | Ghi "anh đã chốt 20/10" ở 41 §0/§1/§3 |
| `GIU_HIEN_HANH` | Hành vi CRM/M1 đang chạy, giữ nguyên |
| `DE_XUAT_CAN_CHOT` | Cột, layout hay tham số mới chỉ là đề xuất, chưa là policy |
| `CAN_DAU_VAO` | Chờ mẫu, đáp án, quyết định hoặc baseline |

**Hiện thực** (đã có code hay chưa):

| Nhãn | Nghĩa |
|---|---|
| `HIEN_CO` | Có trong source baseline |
| `DE_XUAT` | Chưa có, là đề xuất |
| `CHO_DAU_VAO` | Chờ đầu vào |

---

## 1. Bốn quyết định đã chốt (42 §16) — giữ nguyên, không hỏi lại

| ID | Quyết định | Mức | Áp vào | Ca kiểm |
|---|---|---|---|---|
| D1 | Trang mở đầu là **Danh sách hợp đồng** (S1). **Không** có màn "Việc của tôi" trong CRM; CRM chỉ cung cấp loại việc cho K5 (§3). | DA_CHOT_42_4_DIEM | MENU-1, S1, §3 | UI-D1: menu "Hợp đồng bán hàng" mở thẳng S1; không có route hay menu "Việc của tôi" trong CRM. |
| D2 | Menu riêng **Hợp đồng bán hàng** với 6 mục con (MENU-1…6), ẩn theo quyền. | DA_CHOT_42_4_DIEM | §2 | UI-D2: không có menu con thứ 7; mục con ẩn đúng theo quyền. |
| D3 | Bán hàng thấy **cả hai** ô "Tình hình thu theo CRM" và "Công nợ ghi sổ Junsky" của khách trong quyền, hai nhãn, hai nền, có ngày sổ. | DA_CHOT_42_4_DIEM | S1 cột 9–10, S2-T4, V02, V06 | P-D3 |
| D4 | Chỉ máy tính 1280–1440 px, phong cách Bàn kiểm soát/K5. | DA_CHOT_42_4_DIEM | toàn bộ UI | UI-D4: dùng được ở 1280 và 1440; không có bố cục điện thoại. |

Đặc tả gộp hai ý (trang mở đầu + bỏ "Việc của tôi") vào điểm 1, nên tổng vẫn là **bốn** quyết định.

**Hiện trạng UI:** CRM DEMO hiện là **một trang** `#hopdong` "Hợp đồng & lịch thu" (`index.html:70–83`), có 4 khối:
1. Hồ sơ #6
2. Hợp đồng
3. Khoản thu
4. File soát

Trang này chưa có menu riêng, 6 mục con hay 9 màn. Toàn bộ khung D1/D2 là **DE_XUAT**.

---

## 2. Sáu menu ↔ màn

| Menu | Tên | Màn/dialog thuộc menu | Vai thấy (42 §1) | Truy ngược |
|---|---|---|---|---|
| MENU-1 | Hợp đồng (trang mở đầu) | S1; S2 (T1–T7); S4 Soạn HĐ (mở từ S1 hoặc từ S3 "Chuyển sang soạn"); S5 Hộp Ký kết (dialog trong S4/S2) | Bán hàng, KT, CFO, Người xem | D1, G3–G6 |
| MENU-2 | Báo giá | S3 (form + danh sách + bản in V09) | Bán hàng lập; KT/CFO xem | G2, G7 (đọc) |
| MENU-3 | Mẫu hợp đồng | S6 (danh sách mẫu, màn ánh xạ, so sánh phiên bản); **đề xuất** thêm tab "Bộ chuẩn dự án" (G7) | Pháp chế/người tải theo action assignment, KT, CFO; Bán hàng xem mẫu hiệu lực | G1, G7 |
| MENU-4 | Tiếp nhận hợp đồng ký | S7 (luồng B) | Bán hàng nộp; KT kiểm/mapping | B, E1–E5 |
| MENU-5 | Thu tiền | S8 (góc nhìn theo HĐ của V2) | KT nối/gỡ; Bán hàng/CFO/Người xem đọc | M1, D3 |
| MENU-6 | Báo cáo & file soát | S9 | Bán hàng (của mình), KT, CFO, Người xem | G8, F8 |

Không có trang duyệt CRM riêng. Mọi quyết định đi qua K5; nút ở S2/S6 chỉ là lối tắt ghi đúng dòng K5.

---

## 3. Loại việc CRM cung cấp cho K5 (42 §3) — đủ chín nhóm

Bảng `kho.viec_can_duyet` đã có sẵn (HIEN_CO, `pg_migrations.py:569–589`):
- `loai ~ '^V[1-8]$'`
- trạng thái CHO_DUYET / DANG_HOI / CHO_BO_SUNG / DA_DUYET / BO_QUA / DONG
- unique một việc mở trên mỗi đối tượng.

| ID | Loại việc CRM | Người nhận | K5 | Đối tượng | Mở đúng | Hiện thực | Ca kiểm |
|---|---|---|---|---|---|---|---|
| W1 | HĐ bị trả lại; yêu cầu bổ sung đang mở | Bán hàng | V4/V5 | revision dự thảo | S2-T2 | DE_XUAT | W1+: KT trả lại → mở việc cho người phụ trách, bấm vào mở T2. W1−: bán hàng của HĐ khác không thấy. |
| W2 | Chờ ký quá n ngày; báo giá sắp hết hạn | Bán hàng | V8 | HĐ CHO_KY / báo giá | S2-T1 / S3 | DE_XUAT; **n = CAN_DAU_VAO** (Q-UI) | W2: chưa có n thì không sinh nhắc, không tự chọn n. |
| W3 | Chờ kiểm (ngày tồn); PL chờ kiểm | KT | V3 | phiên bản | S2-T2 | Luồng B: HIEN_CO (`crm.py:194–195, 214`). Luồng A: DE_XUAT | W3: HĐ luồng A không sinh việc "CFO duyệt tham số". |
| W4 | Lệch bản ký chưa xử lý | KT | V3 | đối chiếu | S2-T6 | DE_XUAT | W4: còn DIFF chưa xử lý thì không Hiệu lực được. |
| W5 | Đợt đến hạn (chỉ đợt có ngày); tiền chưa rõ; thu thừa/thiếu | KT | V2 | `lich_thu` / BANK | S2-T4 / S8 | Một phần HIEN_CO (`lich_thu.han`, nối tiền); thẻ đếm là DE_XUAT | W5: mốc sự kiện chưa có ngày không tính là "đến hạn". |
| W6 | Đối tượng chưa có mã Junsky | KT | V4 | HĐ / đối tượng dự thảo | S2-T1 | B: HIEN_CO (V4 MAPPING, `crm.py:194`). A: DE_XUAT | W6: Hiệu lực luồng A bị chặn khi chưa có mã. |
| W7 | Mẫu chờ kiểm ánh xạ / chờ CFO duyệt | KT / CFO | V4 | version mẫu | S6 | DE_XUAT | W7: CFO thiếu V4 thì không có nút duyệt và DB từ chối. |
| W8 | HĐ luồng B chờ duyệt tham số | CFO | V3 | phiên bản | S2-T2 | HIEN_CO (`crm.py:490–533`) | GIU_HIEN_HANH |
| W9 | HĐ lệch bộ chuẩn đã hiệu lực | CFO | V8 | HĐ + version bộ chuẩn | S2-T3 | DE_XUAT, phụ thuộc G7 | W9: dự án chưa có chuẩn thì không đánh lệch. |

- Thẻ số đầu S1 lọc theo W1–W5 trong scope của vai.
- "Việc của tôi" cấp hệ thống thuộc web trung tâm (D1), không phải CRM.

---

## 4. Ma trận G1–G8 / E1–E6 ↔ màn ↔ dữ liệu ↔ API ↔ quyền ↔ gate ↔ ca kiểm

Quy ước cột API:
- `HIEN_CO`: route/hàm có trong baseline.
- `DE_XUAT`: contract ở artifact 2 §4, **chưa** có endpoint chạy.
- `CHO_DAU_VAO`: seam M4 đang pending.

| ID | Màn/tab | Dữ liệu thiết yếu | API | Quyền/scope | Phụ thuộc | Gate chính | Mức | Ca kiểm |
|---|---|---|---|---|---|---|---|---|
| G1 Mẫu có phiên bản | S6; K5 V4 | DOCX + hash; placeholder (tên, số lần, ngữ cảnh); field map (trường, kiểu, định dạng, bắt buộc); PN × loại HĐ; version; hiệu lực từ–đến; người tải/kiểm/duyệt | DE_XUAT `crm/mau/*` | Tải: **action `CRM_MAU_TAI` qua action assignment chung** (không thêm vai enum). Kiểm: KT. Duyệt: **CFO + V4** | danh mục trường | Placeholder chưa ánh xạ → **chặn duyệt**. Trường bắt buộc vắng trong mẫu → **cảnh báo** (không hard block). | DA_GHI_CHOT_41 | T-G1a–f |
| G2 Báo giá/lịch | S3; S1; S2-T3 | số/ngày/người lập; PN; dự án/lô/căn; khách hoặc đối tượng dự thảo; giá + currency; **FX nhập tay + ngày + người**; lịch 4 cột + %/tiền/currency/loại mốc; bản in + hash | DE_XUAT `crm/bao-gia/*` | Bán hàng trong scope dự án/khách; KT/CFO đọc | G7 nếu chọn "theo dự án" | % ≠ 100 hoặc USD thiếu FX → chặn **in**. Mốc trống → cảnh báo. **Không** tạo nghĩa vụ/công nợ. "Theo khách" không gắn nhãn chuẩn. | DA_GHI_CHOT_41 | T-G2a–c |
| G3 Soạn HĐ | S4; S2-T2/T3 | version mẫu đã pin; snapshot đầu vào; nguồn từng tham số (MAU v<n> / NHAP_TAY); lịch lấy từ báo giá; `revision_du_thao`; DOCX/PDF + hash | DE_XUAT `crm/soan/*` | Bán hàng trong scope; xuất tài liệu có PII theo Q-PII | G1, G2 | Trường bắt buộc trống → **chặn xuất**. Giữ version mẫu cũ. Tài liệu có PII → nhánh Q-PII. | DA_GHI_CHOT_41; Q-PII CAN_DAU_VAO | T-G3a–c |
| G4 Ký kết | S5; S2-T6 | PDF bản ký + hash; ngày ký; khai Có/Không sửa; revision bản in; người tải | DE_XUAT `crm/ky-ket` | Bán hàng phụ trách, ở CHO_KY | G3 | Thiếu PDF hoặc chưa khai → **không ký**. Replay cùng PDF → không sinh bản mới. Bản ký bất biến. | DA_GHI_CHOT_41 | T-G4a–d |
| G5 Đối chiếu bản ký | S2-T6; ngăn việc nền; K5 V3 | bộ kỳ vọng bất biến; facts bản ký; locator; mức quan trọng; kết quả NOT_SELECTED / PENDING / MATCH / DIFF / FAILED; quyết định KT riêng | DE_XUAT `crm/doi-chieu/*` + job | Hệ thống chạy; KT xử lý | E5 (pending); có nhánh đối chiếu tay độc lập | Khai Có hoặc được chọn → phải đối chiếu xong hoặc KT xử lý có căn cứ **trước** hiệu lực. PENDING/FAILED ≠ MATCH. Adaptive tách riêng (Q-SAMPLE). | DA_GHI_CHOT_41; tham số mẫu CAN_DAU_VAO | T-G5a–e |
| G6 Kiểm → hiệu lực | S2-T2/T3; K5 | lineage duyệt mẫu; mapping Junsky; graph/version; kết quả G5; lịch nghĩa vụ | A: DE_XUAT `crm/hieu-luc-a` (**path service/CSDL riêng**). B: HIEN_CO `crm/kiem` + `crm/duyet` | A: **KT** đủ gate. B: KT kiểm + **CFO V3** (trigger `master.phien_ban_kiem_duyet` `pg_migrations.py:2555–2558`) | G1–G5 | A: KT đủ gate. B: giữ CFO. Chưa hiệu lực → không sinh nghĩa vụ, không mở nối tiền. | A DA_GHI_CHOT_41; B GIU_HIEN_HANH (Q-B) | T-G6a–e |
| G7 Bộ chuẩn dự án | S3/S4 đọc; S2-T3 so lệch; quản trị **đề xuất** là tab trong S6 | PN/dự án/giai đoạn; version lịch chuẩn 4 cột; KT lập, CFO duyệt; ngày hiệu lực | DE_XUAT `crm/bo-chuan/*` | KT lập; CFO duyệt (V4) | — | Phần tối thiểu phải có trước nhánh "theo dự án" và so lệch ở G6. Chưa có chuẩn → "chưa có", không đánh lệch. | DA_GHI_CHOT_41; vị trí UI DE_XUAT_CAN_CHOT | T-G7a/b |
| G8 Báo cáo giao kết | S9; thẻ S1; S2-T1 | đếm trạng thái × dự án × PN; lệch chuẩn; cấu hình/tỷ lệ kiểm mẫu; drilldown; sheet file soát | DE_XUAT `crm/bao-cao`; file soát một HĐ HIEN_CO | theo scope | G5–G7 | Tổng cùng scope với danh sách. Nhánh chưa có dữ liệu → "—", không ghi 0. | DA_GHI_CHOT_41 (làm sau) | T-G8a/b |
| E1 Catalog theo loại | S7 chọn loại; S3/S4 chọn profile | catalog ID/version/hash; XD/KCN/Nhà ở; metadata output | CHO_DAU_VAO (seam M4) | — | M4 freeze; Q-INPUT | 37 mã là baseline **XD**, không ép cho KCN/Nhà ở. Giữ khóa nguồn cũ. | DA_GHI_CHOT_41 / CAN_DAU_VAO | T-E1a/b |
| E2 Logic theo loại | S7; S2-T2/T3/T6 | version quy tắc/profile; kiểm lịch/%/currency/FX basis | CHO_DAU_VAO | — | E1 | Giữ hành vi XD. Không suy VAT/FX/lịch từ tổng tiền. | DE_XUAT_CAN_CHOT | T-E2a |
| E3 Tham số dạng bảng | S7; S2-T3; S3/S4 | dòng lịch: lần, %, tiền, currency, ngày/sự kiện, ghi chú, thứ tự, locator mỗi dòng | CHO_DAU_VAO | — | E1 | Giữ raw/source state. Mốc chưa có ngày không quá hạn. Text TT-20 XD cũ vẫn đọc được. | DA_GHI_CHOT_41 | T-E3a/b |
| E4 Output tương thích | S7; S2-T2/T6 | loai_hop_dong, mau_id, phien_ban_mau, che_do; giữ `tham_so[]`, `phieu_kiem_tra` | Reader HIEN_CO (`trich_hop_dong_6.py:23–42`); trường mới DE_XUAT | — | E1 | Tách schema nguồn thực với DTO đề xuất. Không đổi khóa cũ. Metadata do browser gửi không là authority. | DE_XUAT_CAN_CHOT | T-E4a |
| E5 Đối chiếu kỳ vọng | G5; S2-T6 | bộ kỳ vọng bất biến; signed evidence; so typed/raw; `lech[]` | CHO_DAU_VAO | — | E4; M4 freeze | Không lấy output thực làm oracle. UNKNOWN/FAILED ≠ MATCH. Chấp nhận lệch không đổi DIFF thành MATCH. | DA_GHI_CHOT_41 | T-E5a/b |
| E6 Ranh giới engine | toàn module | CRM chỉ gọi trích/đối chiếu dùng chung | — | — | — | Không sửa app nguồn. Không mang BOQ / review đợt / K1–K8 / B1–B8 / P01–P18. Không race file M4. | DA_GHI_CHOT_41 | T-E6a |

### Lỗ hổng chỗ đặt (ghi rõ, không tự lấp bằng menu mới)

1. **G7 quản trị:** không có trong 9 màn đã chốt. Đề xuất làm tab "Bộ chuẩn dự án" trong S6/MENU-3 (DE_XUAT_CAN_CHOT, Q-UI).
2. **Thay bằng chứng (42 §13):** 42 §15 chưa có dialog. Đề xuất dùng lại S5 ở chế độ "Thay bằng chứng", chỉ sau khi chốt Q-RETURN.
3. **Pháp chế/người tải mẫu:** không có trong enum `master.nguoi_dung.vai_tro` (`pg_migrations.py:968`). Xử lý: action `CRM_MAU_TAI` qua **action assignment chung** (artifact 2 §3.3).
   - Cơ chế làm ngay.
   - Việc cấp grant thực cho tài khoản nào chờ quản trị, nhưng không chặn implementation.

---

## 5. Chín màn

### S1 · Danh sách hợp đồng (MENU-1, trang mở đầu)

- **Thẻ số:** Chờ kiểm · Chờ ký · Đến hạn 7 ngày · Lệch chưa xử lý · Tiền chưa rõ · Trả lại. Bấm thẻ để lọc.
- **13 cột** theo 42 §4 (DE_XUAT_CAN_CHOT, Q-UI):
  - Giá trị có căn cứ; thiếu thì hiện "—".
  - Trạng thái kèm nguồn (Mẫu v<n> / Trích / Nhập tay).
  - Cột 9 = CRM; cột 10 = Junsky kèm ngày sổ.
  - Mốc chưa có ngày không tính quá hạn.
  - Cờ chênh CRM↔Junsky.
- **Nguồn:**
  - HIEN_CO: `crm.danh_sach` (`crm.py:723–789`), trả HĐ / phiên bản / lịch / tiền.
  - Chưa có: trạng thái giao kết, người phụ trách, cột Junsky, phân trang, bộ lọc lưu theo người (DE_XUAT).
- **Nút:**
  - Bán hàng: Lập báo giá · Soạn hợp đồng.
  - KT: Tiếp nhận hợp đồng ký.
  - CFO: Xuất file soát.
  - Mọi vai: Xuất Excel danh sách (có nhật ký).
- **Trạng thái màn:**
  - Rỗng: "Không có hợp đồng trong phạm vi của bạn" — không lộ số đếm của PN khác.
  - Không quyền module: theo mẫu HIEN_CO `server.py crm_state` trả `khong_quyen` với 0 dữ liệu.
  - Lỗi tải: toast, giữ nguyên bộ lọc.
- **Ca kiểm:**
  - S1-a: Bán hàng chỉ thấy HĐ của khách/dự án mình; thẻ số đếm trong scope.
  - S1-b: chưa có sổ Junsky → "chưa có sổ", không hiện 0.

### S2 · Chi tiết hợp đồng (7 tab, xem §6)

- Đầu trang: số HĐ · khách · dự án/lô/căn · giá trị và currency · trạng thái + nguồn · phiên bản hiệu lực · nút chính theo §7.
- S2-a: mở HĐ ngoài scope → backend trả 404/403, không trả JSON một phần.

### S3 · Báo giá (MENU-2)

- Bố cục: form bên trái; lịch và xem trước bên phải.
- Danh sách: trạng thái nháp / đã in / đã chuyển / hủy / hết hạn.
- Nút: Lưu nháp · In cho khách · Chuyển sang soạn · Hủy (cần lý do).
- Chặn:
  - Tổng % ≠ 100 → nút In mờ.
  - USD thiếu FX → nút In mờ.
  - Lô/căn đang có HĐ hiệu lực → chỉ cảnh báo.
- Dự án ngoài scope: không chọn được, backend vẫn kiểm.
- Ca kiểm: V08, V09, T-G2.

### S4 · Soạn HĐ từ mẫu

- Ba cột: nhập liệu · xem trước · danh sách kiểm.
- Thanh mẫu: loại · version · hiệu lực; có nhắc khi xuất hiện mẫu mới (V11).
- Nút: Lưu nháp (Ctrl+S) · Xuất hợp đồng · Ký kết (chỉ ở CHO_KY) · Hủy.
- Sinh file là việc nền có tiến độ. Lỗi mẫu nêu đúng tên ô.
- Ca kiểm: V10, V11, T-G3.

### S5 · Hộp Ký kết (dialog)

- Đầu vào:
  - PDF bắt buộc, hiện tên / dung lượng / số trang / mã kiểm tra file.
  - Ngày ký; người ký phía khách.
  - Khai Có/Không (bắt buộc).
  - Tóm tắt khóa: số dòng lịch, tổng, mẫu v<n>, revision bản in.
- Nút Xác nhận mờ khi thiếu PDF hoặc chưa khai.
- Sau xác nhận: toast "Đã chuyển kế toán kiểm"; có việc nền đối chiếu nếu khai Có hoặc được chọn.
- Ca kiểm: V12, V13, T-G4.

### S6 · Mẫu hợp đồng / ánh xạ (MENU-3)

- Danh sách mẫu, trạng thái: Chờ kiểm ánh xạ / Chờ CFO / Hiệu lực / Hết hiệu lực; kèm số HĐ đã dùng.
- Màn ánh xạ:
  - Ô chưa ánh xạ tô vàng.
  - Trường bắt buộc vắng tô đỏ — chỉ cảnh báo.
  - Nút "Xem thử với dữ liệu giả" (không lưu).
  - So sánh hai version.
- Nút theo vai:
  - Người có `CRM_MAU_TAI`: Tải mẫu · Gửi KT kiểm.
  - KT: Đã kiểm, gửi CFO / Trả lại.
  - CFO: Duyệt, hiệu lực từ ngày / Từ chối.
- Ca kiểm: V14, T-G1.

### S7 · Tiếp nhận hợp đồng ký (MENU-4, luồng B)

- Nhận PDF/DOCX bản ký hoặc JSON #6; chọn loại HĐ.
- Tiến độ 9 bước + nhật ký + Dừng (V15).
- Bảng tham số; nhận trùng theo hash; mapping PN / loại / khách / dự án.
- Nút: Bổ sung & lập tiếp · Yêu cầu bổ sung · Gửi kiểm (→ V3, CFO GIU_HIEN_HANH).
- Nguồn:
  - HIEN_CO: nhận **JSON** #6 (`/api/crm/nhan`, `crm.nhan_ket_qua_6` `crm.py:112–150`); bổ sung/trích lại (311–400); mapping (402–427).
  - CHO_DAU_VAO (M4 freeze): nhận PDF/DOCX và chạy engine trên máy chủ.
- Ca kiểm: T-B1–3, V15.

### S8 · Thu tiền (MENU-5)

- Trái: HĐ có đợt đến hạn / tiền chưa rõ.
- Phải: BANK/proposal M1 cùng PN + currency, chưa nối hết. Kéo vào đợt → hộp xác nhận.
- Gỡ liên kết phải có lý do. Tiền chưa rõ hiện nhãn "Vàng theo CFO-03".
- Nguồn:
  - HIEN_CO: `lien_ket` / `go_lien_ket` (`crm.py:583–650`) + guard CSDL `VUOT_TIEN_KHA_DUNG` / `VUOT_NGHIA_VU` (`pg_migrations.py:2964–2967`).
  - DE_XUAT: kéo-thả, danh sách theo HĐ.
  - CAN_DAU_VAO: nút "Hỏi phòng kinh doanh" (agent Zalo).
- Ca kiểm: V16, T-M1.

### S9 · Báo cáo & file soát (MENU-6)

- Chọn PN · kỳ · phạm vi → tổng kiểm soát → Xuất file soát. Bấm số để drilldown.
- Nguồn:
  - HIEN_CO: file soát **một HĐ**, 4 sheet (`crm.py:661–705`).
  - DE_XUAT: file theo kỳ/phạm vi phủ sáu nhóm nghiệp vụ của 42 §12: Hợp đồng & phiên bản; Lịch nghĩa vụ; **Liên kết tiền**; Truy vết nguồn; Chênh CRM↔Junsky theo đối tượng; Giao kết. Bốn sheet code hiện hành là HOP_DONG_PHIEN_BAN, LICH_NGHIA_VU, THAM_SO_CAN_CU, CANH_BAO; chưa có Liên kết tiền. Giữ CANH_BAO và contract export một HĐ cũ; không lấy phép đếm “4+2” thay coverage nghiệp vụ của export kỳ mới.
- Ca kiểm: V17, T-G8; T-G8c đối chiếu sheet Liên kết tiền với link giữ lịch sử, đúng scope và tổng cùng currency, truy được nguồn.

---

## 6. Bảy tab S2

### T1 · Tổng quan

- **Field:** thẻ giá trị / đã thu / còn lại / đợt kế tiếp / cờ; dòng thời gian trạng thái (ai, lúc); chuỗi HĐ → Đợt → Hóa đơn M3 (chỉ đọc) → Tiền.
- **Nguồn:** HIEN_CO một phần (phiên bản, lịch, link). Timeline giao kết và tham chiếu M3 là DE_XUAT.
- **Rỗng / unknown / quyền:**
  - Chưa có hóa đơn M3 → "chưa có", không 0.
  - Không có quyền M3 → ẩn, không lộ số.
- **Nút:** không có.
- **Sau mutation:** tải lại thẻ.
- **Ca kiểm:** T1-a — đã thu = SUM link active theo chuỗi khóa (`crm_da_lien_ket`).

### T2 · Nguồn & tham số

- **Field:** mã · tên · giá trị hiệu lực · đơn vị/currency · Điều/Khoản · trích dẫn nguyên văn · nguồn · trạng thái kiểm · mức. Có lọc "chỉ thiếu căn cứ"; ngăn phải hiện trích dẫn + locator.
- **Nguồn:**
  - HIEN_CO: `master.hop_dong_tham_so` (`_tham_so_view` `crm.py:797–804`); trạng thái căn cứ ở `crm_phan_tich.py:200–289`.
  - DE_XUAT: nguồn MAU/NHAP_TAY theo từng tham số; mức quan trọng.
- **Rỗng / unknown / quyền:**
  - Thiếu trích dẫn → "—" + cờ.
  - "Không quy định" giữ nguyên chữ, không ghi 0.
  - PII chỉ hiện 4 số cuối, trừ KT/CFO.
- **Nút:**
  - KT: Yêu cầu bổ sung; Đánh dấu đã kiểm (B, HIEN_CO `crm/kiem`).
  - CFO (luồng B): Duyệt → K5 V3 (HIEN_CO `crm/duyet`).
  - Luồng A: KT bấm Hiệu lực (DE_XUAT).
- **Sau mutation:** lần kiểm hết hiệu lực khi mapping hoặc nội dung đổi (HIEN_CO `_vo_hieu_kiem` 300–308).
- **Ca kiểm:** V03; T-B3.

### T3 · Lịch nghĩa vụ

- **Field:** Lần · Giá trị · Mốc · Ghi chú + % · currency · ngày tính được · đã nối · còn lại · trạng thái đợt · phiên bản căn cứ. KCN hiện USD + VND quy đổi + FX tay. Có dòng tổng.
- **Nguồn:**
  - HIEN_CO: `master.lich_thu` (dot, moc, so_tien_minor, tien_te, han, co_so, khoa_nghia_vu, nguon_tham_so; `pg_migrations.py:349–361, 1004–1010`).
  - DE_XUAT: thêm %, ghi chú, thứ tự, loại mốc.
- **Rỗng / unknown:**
  - Mốc chưa có ngày: hiện mốc, không quá hạn, không tô đỏ.
  - Không có lịch: "Chưa có lịch tường minh" (HIEN_CO chặn `LICH_TRONG`).
- **Nút:**
  - Bán hàng (chỉ khi Soạn thảo): Sửa lịch.
  - KT: Mở việc.
- **Sau mutation:** sửa lịch → revision +1, file cũ còn giữ.
- **Ca kiểm:** V04, V05; T-L1.

### T4 · Thu tiền

- **Field:** khoản đã nối (ngày, BANK/proposal, số tiền, đợt, người nối, lý do gỡ); tổng theo đợt; hai ô "Tình hình thu theo CRM" và "Công nợ ghi sổ Junsky (sổ đến dd/mm)"; cờ chênh.
- **Nguồn:**
  - HIEN_CO: `kho.lien_ket_chung_tu` qua `danh_sach`, chỉ khi có XEM_TIEN.
  - DE_XUAT: ô Junsky từ `kho.cong_no_mo` (`pg_migrations.py:261–280`), cùng grain.
- **Rỗng / unknown:**
  - Chưa có sổ → "Chưa có sổ Junsky", **không ghi 0**.
  - Số dư 131 là theo đối tượng → hiện ở cấp đối tượng, không gán cho từng HĐ.
- **Nút:**
  - KT: Nối tiền (mở K5 V2 lọc theo HĐ); Gỡ liên kết (cần lý do).
  - Bán hàng: chỉ đọc hai ô.
- **Sau mutation:** cập nhật trạng thái đợt (HIEN_CO `_cap_nhat_trang_thai_lich`).
- **Ca kiểm:** V06; P-D3; T-J1.

### T5 · Phụ lục/phiên bản

- **Field:** gốc/PL · số/ngày · ngày hiệu lực · trạng thái · người kiểm/duyệt · tham số cũ → mới · lịch thêm/bớt/sửa; so sánh hai phiên bản.
- **Nguồn:** HIEN_CO `master.hop_dong_phien_ban` + `so_sanh_phu_luc` (`crm_phan_tich.py:297`); nhãn "sắp hiệu lực" (`crm.py:757`).
- **Rỗng:** "Chưa có phụ lục".
- **Nút:**
  - Bán hàng: Soạn PL từ mẫu (DE_XUAT); Nộp PL ký (B qua S7, HIEN_CO).
  - KT: Kiểm.
- **Sau mutation:** đợt đã có tiền nối mà bị đổi → chặn (HIEN_CO).
- **Ca kiểm:** T-P1.

### T6 · Bản ký & đối chiếu

- **Field:** PDF xem trong trang · mã kiểm tra file · ngày ký · người tải · khai có sửa · kết quả đối chiếu · bảng lệch (bản sinh / bản ký / trích dẫn / mức) · các bản xuất trước khi ký.
- **Nguồn:** DE_XUAT toàn bộ.
- **Rỗng / unknown / quyền:**
  - Chưa ký: "Chưa có bản ký".
  - FAILED: "Chưa đối chiếu được", không hiện xanh.
  - Không có quyền xem PDF → ẩn nút, backend trả 403.
- **Nút:**
  - KT: Xử lý lệch (chấp nhận có lý do / trả lại); Chạy đối chiếu tay.
  - Bán hàng: Thay bằng chứng — chỉ sau khi chốt Q-RETURN.
- **Sau mutation:** quyết định KT lưu riêng; DIFF vẫn giữ.
- **Ca kiểm:** V07; T-G5.

### T7 · Lịch sử

- **Field:** nhật ký chỉ thêm (ai, lúc, trước/sau, căn cứ, file); lượt gọi cổng AI (chỉ loại việc).
- **Nguồn:**
  - HIEN_CO: `nhat_ky.su_kien` (`crm.py:70–73`).
  - DE_XUAT: lọc theo HĐ; log truy cập PII/PDF.
- **Quyền:** chỉ hiện sự kiện trong scope.
- **Nút:** Xuất nhật ký (ghi lần tải).
- **Ca kiểm:** T-H1.

---

## 7. Ma trận hành động

Ba path **tách riêng**, không gộp thành "duyệt chung":

| Path | Ai | Làm gì |
|---|---|---|
| **TPL-APPROVE** | CFO | Duyệt version mẫu |
| **A-EFF** | KT | Làm hiệu lực HĐ luồng A |
| **B-APPROVE** | CFO | Duyệt luồng B (hiện hành) |

| Hành động | Vai (DB enforce) | Scope | Trạng thái | Dữ liệu bắt buộc | Căn cứ bất biến | Replay/khóa | Output | Lỗi chính | Ca +/− |
|---|---|---|---|---|---|---|---|---|---|
| Tải mẫu | action `CRM_MAU_TAI` (assignment) | PN × loại | — | DOCX hợp lệ, không macro | bytes + hash | replay cùng ý định trả bản cũ; blob trùng được dùng lại, đổi mapping sau duyệt cần version mới | version DRAFT + danh sách placeholder | MAU_TEP_SAI | T-G1a / T-G1e / T-G1g |
| Lưu ánh xạ | `CRM_MAU_TAI` / KT | PN × loại | DRAFT / CHO_KIEM | map đủ kiểu/định dạng | version mẫu | expected map revision | map revision | MAU_REVISION_CU | T-G1b |
| KT kiểm mẫu | KE_TOAN/KTT + CRM | PN | CHO_KIEM | map hiện hành | map digest | khóa client | CHO_CFO | MAU_CON_O_CHUA_ANH_XA | T-G1c |
| **TPL-APPROVE** | **CFO + V4** | PN | CHO_CFO | 0 ô chưa ánh xạ; ngày hiệu lực | version + map digest | khóa client | HIEU_LUC từ ngày; đóng V4 | MAU_CON_O_CHUA_ANH_XA, KHONG_CO_QUYEN_LOAI_VIEC | T-G1c / T-G1d |
| Lập/sửa báo giá | BAN_HANG | PN + dự án + khách | NHAP | FX khi currency ≠ VND (người/ngày) | — | expected revision | quote revision | BAO_GIA_REVISION_CU | T-G2a |
| In báo giá | BAN_HANG | như trên | NHAP | tổng 100%; đủ FX | quote revision → hash bản in | cùng revision → cùng bản in | bản in bất biến | BAO_GIA_TONG_PT, THIEU_FX | T-G2b |
| Chuyển sang soạn | BAN_HANG | như trên | NHAP / DA_IN | có mẫu hiệu lực cho loại | lịch theo quote revision | khóa client | HĐ SOAN_THAO + lịch copy | KHONG_CO_MAU_HIEU_LUC | T-G2c |
| Lưu nháp HĐ | BAN_HANG | như trên | SOAN_THAO / CHO_KY | — | version mẫu đã pin | expected draft revision | draft revision | DRAFT_REVISION_CU | T-G3a |
| Xuất hợp đồng | BAN_HANG | như trên | SOAN_THAO / CHO_KY | 0 trường bắt buộc trống; tổng 100% | snapshot + version + hash render | expected revision | DOCX/PDF + hash; revision +1; CHO_KY | XUAT_THIEU_TRUONG | T-G3b / T-G3c |
| Ký kết | BAN_HANG phụ trách | như trên | CHO_KY | PDF + ngày + khai Có/Không | revision bản in + hash PDF | cùng hash → không sinh bản mới | DA_KY → KE_TOAN_KIEM; quyết định chọn mẫu | KY_THIEU_PDF, KY_THIEU_KHAI | T-G4a–d |
| Đối chiếu | hệ thống / KT | PN | DA_KY | bộ kỳ vọng + PDF | signed revision | quyết định chọn đã lưu; retry không bốc lại | MATCH / DIFF / FAILED | DOI_CHIEU_FAILED | T-G5a–c |
| Xử lý lệch | KT | PN | DIFF / FAILED | lý do | id đối chiếu | khóa client | quyết định riêng; DIFF giữ | CAN_LY_DO | T-G5d |
| **A-EFF** | **KE_TOAN/KTT**, không cần CFO | PN + scope | KE_TOAN_KIEM, origin MAU | khách có mã Junsky; 0 lệch chưa xử lý; 0 tham số mức ≥ 2 thiếu căn cứ; version mẫu đã CFO duyệt | duyệt mẫu + signed revision + kết quả đối chiếu | expected graph/version | HIEU_LUC; sinh `lich_thu` | A_CHUA_DU_DIEU_KIEN, ORIGIN_KHONG_PHAI_MAU | T-G6a / T-G6b, T-G6c |
| Trả lại | KT | PN | KE_TOAN_KIEM | lý do | **giữ bản ký**; bản làm việc mới (Q-RETURN) | khóa client | W1 | CAN_LY_DO | T-R1 |
| KT kiểm (B) | KE_TOAN/KTT + CRM | PN | CHO_DUYET | 0 chặn | `kiem_van_tay` | trigger | kiem_boi / kiem_luc | CRM_CHUA_DU_DIEU_KIEN | HIEN_CO |
| **B-APPROVE** | **CFO + V3** (+V4 nếu HĐ mới) | PN | CHO_DUYET, đã kiểm | — | vân tay khớp | trigger `phien_ban_kiem_duyet` | DA_DUYET + `lich_thu` | KHONG_CO_QUYEN_DUYET, CHUA_KIEM_TRUOC | T-G6d / T-G6e |
| Nối tiền | KT + M1 | PN | đợt thuộc phiên bản hiệu lực hôm nay | cùng PN + currency; ≤ phần còn lại | link | `khoa_idempotency` | DA_KHOP | VUOT_TIEN_KHA_DUNG, VUOT_NGHIA_VU, LICH_KHONG_HIEU_LUC, IDEMPOTENCY_KHAC | T-M1a–d |
| Gỡ liên kết | KT + M1 | PN | DA_KHOP | lý do | link giữ trạng thái HUY | HUY lặp → lap_lai | HUY | CAN_LY_DO | T-M1e |
| Duyệt bộ chuẩn | CFO + V4 | PN + dự án | CHO_CFO | version lịch chuẩn | version | khóa client | HIEU_LUC | — | T-G7a |
| Hủy nháp | BAN_HANG | scope | nháp chưa ký | lý do | lịch sử giữ | khóa client | HUY | CAN_LY_DO | T-H2 |
| Hủy sau ký | CHO_Q-RETURN | scope | đã ký | chờ binding xử lý pháp lý/phần đã thu | bản ký bất biến | chưa mở mutation | CHO_Q-RETURN | chưa được giao code | T-H2b: chưa chốt không mở hủy sau ký |

**Quy tắc chung cho mọi mutation** (theo mẫu HIEN_CO `crm.py` `_tx` / `_khoa_hop_dong`):
- Danh tính phiên do máy chủ cấp.
- Kiểm quyền **trước** replay hay đọc tệp.
- Khóa HĐ trước khi động tới tiền/đợt.
- Nhật ký chỉ thêm.
- Không nhận actor / PN / trạng thái / cờ duyệt từ trình duyệt (HIEN_CO `crm_body` `server.py:229–234`).

---

## 8. Mười bảy trạng thái thiết kế (42 §15) — coverage thiết kế, chưa phải ca đã chạy

| ID | Màn | Mô tả | Dữ liệu giả cần có | G/E | Phải thấy |
|---|---|---|---|---|---|
| V01 | S1 KCN | Trang mở đầu, thẻ số, USD/VND, cờ | 3 HĐ KCN (1 HĐ USD); 1 lệch; 1 chờ kiểm | G6, G8, D1 | USD kèm VND + FX + ngày + người; thẻ bấm được để lọc |
| V02 | S1 nhà ở, vai Bán hàng | CCCD chỉ 4 số cuối; hai ô thu | 2 HĐ nhà ở; sổ Junsky có ngày | D3, Q-PII | JSON không chứa CCCD đầy đủ; hai nhãn, hai nền |
| V03 | S2-T2 | Ngăn trích dẫn mở | 1 tham số có locator trang | G3 / B | Đoạn văn + locator; nguồn |
| V04 | S2-T3 KCN | Lịch USD/VND | 4 đợt; 1 FX tay | G2, G6, E3 | Tổng 100% và tổng tiền; FX báo giá không phải căn cứ thanh toán |
| V05 | S2-T3 nhà ở | Mốc sự kiện chưa có ngày | đợt "bàn giao" chưa ngày | E3 | Hiện mốc; không quá hạn; không tô đỏ |
| V06 | S2-T4 | Hai ô thu + cờ chênh | link CRM + 131 theo đối tượng | D3 | Cờ chênh; grain đối tượng không gán cho HĐ |
| V07 | S2-T6 | Có lệch | DIFF mức 2 ở một đợt | G5, E5 | Lệch đúng đợt; nút Xử lý lệch |
| V08 | S3 KCN | Tổng % ≠ 100 | 3 dòng = 90% | G2 | Nút In mờ kèm lý do |
| V09 | Bản in báo giá | Dòng tham chiếu FX | quote USD | G2 | Số, ngày, người lập, FX + ngày + người; không có số liệu nội bộ |
| V10 | S4 | Ba cột, có lỗi | 2 trường bắt buộc trống | G3 | Xuất bị chặn; bấm lỗi nhảy tới ô |
| V11 | S4 | Nhắc mẫu mới | đang dùng v1; v2 đã hiệu lực | G1, G3 | Vẫn v1; chuyển = sinh lại có revision |
| V12 | S5 | Thiếu PDF | — | G4 | Nút Xác nhận mờ |
| V13 | S5 | Hoàn tất | PDF + khai Không | G4 | Toast; việc nền nếu được chọn kiểm |
| V14 | S6 | Ô chưa ánh xạ | 1 placeholder lạ | G1 | Tô vàng; không duyệt được; nêu đúng tên ô |
| V15 | S7 | Đang chạy 9 bước | 1 tệp bản ký | B / E1 | Tiến độ, nhật ký, Dừng (engine seam là CHO_DAU_VAO) |
| V16 | S8 | Kéo tiền vượt | BANK 100, đợt còn 60, kéo 80 | M1 | Chặn VUOT_NGHIA_VU; không ghi gì |
| V17 | S9 | Tổng kiểm soát | kỳ có cả USD và VND | G8 | Tổng tách theo currency; thiếu nguồn hiện "—" |

---

## 9. Vai × màn (42 §1) và scope backend

| Màn | Bán hàng | KT công nợ | CFO | Người xem | Pháp chế / người tải mẫu (action) |
|---|---|---|---|---|---|
| S1 | khách/dự án mình | theo PN | các PN được cấp | theo phạm vi | — |
| S2 | xem; sửa khi còn dự thảo | xem; kiểm; nối tiền | xem; duyệt B | xem | — |
| S3 | lập | xem | xem | — | — |
| S4 | lập, xuất, Ký kết | xem | xem | — | — |
| S5 | bấm | — | — | — | — |
| S6 | xem mẫu hiệu lực | kiểm ánh xạ | duyệt version | — | tải mẫu (`CRM_MAU_TAI`) |
| S7 | nộp file | kiểm, mapping, bổ sung | duyệt ở K5 (B) | — | — |
| S8 | đọc CRM + Junsky khách mình | nối/gỡ | xem | xem | — |
| S9 | của mình | ✔ | ✔ | theo phạm vi | — |

**Scope backend:**
- HIEN_CO: PN + module (`quyen.kiem`, RLS `ktt_duoc(pn,'CRM')`).
- DE_XUAT: thêm **dự án + khách/người phụ trách** cho Bán hàng/Người xem. Chưa có cột người phụ trách ở `master.hop_dong`.
- Lọc ở giao diện không thay được kiểm quyền backend.

**PII:**
- CCCD/STK đầy đủ chỉ cho KT/CFO khi mở chi tiết, có log.
- HIEN_CO cột mã hóa `master.doi_tac.cccd_mh/cccd_hash` (`pg_migrations.py:92–93`), `tai_khoan_ngan_hang.stk_mh`.
- PDF bản ký: quyền tệp riêng. Tài liệu sinh có PII: theo Q-PII.

---

## 10. Danh mục ca kiểm (mô tả, chưa chạy)

### Mẫu (G1)

- **T-G1a:** placeholder `{{ten_la}}` chưa ánh xạ tới trường hợp lệ → không gửi CFO được; báo đúng tên ô. Tên placeholder không bắt buộc trùng mã trường nếu có mapping hợp lệ.
- **T-G1b:** trường bắt buộc "ngày ký" vắng trong mẫu → cảnh báo, vẫn gửi kiểm được.
- **T-G1c:** CFO có V4 duyệt mẫu sạch → hiệu lực từ ngày.
- **T-G1d (âm):** KT, hoặc CFO thiếu V4, duyệt → DB từ chối.
- **T-G1e:** retry cùng ý định upload DOCX → không version mới. DOCX có macro → từ chối. Người không có `CRM_MAU_TAI` tải → 403 ở DB.
- **T-G1f:** v2 hiệu lực → HĐ đang soạn bằng v1 vẫn mở v1 (CRM-GA1).
- **T-G1g:** dùng lại cùng DOCX nhưng đổi map sau duyệt → version mới cần kiểm/duyệt; blob có thể dùng lại, version/map/check/HĐ cũ không đổi.

### Báo giá (G2)

- **T-G2a:** USD thiếu FX → không in. Có FX → in có dòng FX + ngày + người. Đổi FX → VND tính lại, USD giữ (CRM-GA2).
- **T-G2b:** tổng 90% → In mờ; 100% → In được. In lại cùng revision → cùng bản in. Sửa quote sau đó không đổi bản đã in.
- **T-G2c:** chuyển sang soạn → lịch giữ nguyên. Báo giá không tạo `lich_thu` hay link.

### Soạn (G3)

- **T-G3a:** lưu với expected revision cũ → `DRAFT_REVISION_CU`.
- **T-G3b:** trường bắt buộc trống → không xuất được.
- **T-G3c:** sửa đợt rồi xuất 2 lần → 2 file, 2 hash, revision 1 → 2, file cũ còn (CRM-GA3).

### Ký kết (G4)

- **T-G4a:** không có PDF → chặn.
- **T-G4b:** đủ PDF + khai → DA_KY; tham số khóa.
- **T-G4c:** cùng PDF lần 3 → không sinh bản mới (CRM-GA4).
- **T-G4d:** PDF khác sau khi ký → chỉ qua "Thay bằng chứng" (Q-RETURN); bản cũ giữ.

### Đối chiếu (G5)

- **T-G5a:** khai Có → đối chiếu bắt buộc; lệch đúng đợt, đúng mức (CRM-GA5).
- **T-G5b:** OCR/trích FAILED → "chưa đối chiếu được", không MATCH; chặn hiệu lực cho tới khi KT xử lý có căn cứ.
- **T-G5c:** retry → không bốc thăm lại.
- **T-G5d:** KT chấp nhận DIFF có lý do → kết quả vẫn DIFF.
- **T-G5e (Q-SAMPLE):** chỉ chạy khi policy được chốt.

### Hiệu lực (G6)

- **T-G6a:** HĐ origin MAU, mẫu đã duyệt, đủ gate → KT Hiệu lực → `lich_thu` đúng số dòng/tiền/currency (CRM-GA7).
- **T-G6b (âm):** KT làm A-EFF cho HĐ origin TRICH → DB từ chối.
- **T-G6c (âm):** mẫu chưa duyệt / chưa có mã Junsky / còn DIFF chưa xử lý → chặn.
- **T-G6d:** luồng B: CFO V3 duyệt như hiện hành (regression).
- **T-G6e (âm):** KT gọi path B → trigger trả `KHONG_CO_QUYEN_DUYET`.

### Bộ chuẩn và báo cáo (G7, G8)

- **T-G7a:** HĐ khớp bộ chuẩn → không cảnh báo.
- **T-G7b:** dự án chưa có chuẩn → không đánh "lệch chuẩn".
- **T-G8a:** tổng ở S9 khớp số đếm của danh sách cùng scope.
- **T-G8b:** nhánh chưa có dữ liệu → "—".
- **T-G8c:** export kỳ đủ sáu nhóm nghiệp vụ, gồm Liên kết tiền; giữ cảnh báo và nguồn; số/tổng link khớp cùng scope/currency, không cộng trùng khi một tiền nối nhiều đợt.

### Engine (E1–E6)

- **T-E1a:** XD regression — 37 mã và khóa JSON cũ giữ nguyên.
- **T-E1b:** KCN không bị ép 37 mã.
- **T-E2a:** tổng % = 100 cho KCN/nhà ở; kết quả XD trước/sau như nhau.
- **T-E3a:** mỗi dòng lịch có locator.
- **T-E3b:** text TT-20 XD vẫn đọc được.
- **T-E4a:** thêm trường không đổi khóa cũ; metadata từ browser bị bỏ qua.
- **T-E5a:** bộ kỳ vọng tạo trước khi ký, không lấy output đối chiếu làm oracle.
- **T-E5b:** UNKNOWN ≠ MATCH.
- **T-E6a:** CRM không import BOQ / review đợt của M4.

### Luồng B (HIEN_CO)

- **T-B1:** cùng JSON → TRUNG_RAW.
- **T-B2:** phụ lục khi đang có phiên bản chờ → XUNG_DOT.
- **T-B3:** mapping đổi sau khi kiểm → lần kiểm hết hiệu lực.

### Nối tiền (M1)

- **T-M1a:** vượt số tiền BANK → VUOT_TIEN_KHA_DUNG.
- **T-M1b:** vượt nghĩa vụ đợt → VUOT_NGHIA_VU.
- **T-M1c:** khác PN/currency → chặn. BANK VND vào đợt USD khi chưa có căn cứ FX → chặn.
- **T-M1d:** cùng khóa, khác body → IDEMPOTENCY_KHAC.
- **T-M1e:** gỡ có lý do; lịch sử giữ.

### Junsky và quyền

- **T-J1:** 131 của đối tượng có 2 HĐ → hiện ở cấp đối tượng, không chia cho từng HĐ. Thiếu sổ → "Chưa có sổ". Khác ngày sổ hoặc currency → không so.
- **P-D3:** Bán hàng thấy hai ô cho khách mình; khách của người khác cùng PN → 403 từ backend.
- **P-PII:** JSON cho Bán hàng chỉ có 4 số cuối; KT mở chi tiết có log; người ngoài quyền tải PDF ký → 403 (CRM-GA8).
- **P-SCOPE:** cùng PN nhưng khác dự án/khách → không thấy HĐ; thẻ số không lộ.

### Khác

- **T-L1:** mốc chưa có ngày → không quá hạn.
- **T-P1:** PL đổi đợt đã nối tiền → chặn (HIEN_CO).
- **T-R1:** Trả lại không mở khóa bản ký.
- **T-H1:** nhật ký chỉ thêm.
- **T-H2:** Hủy giữ lịch sử; báo giá hủy không bị xóa.

---

## 11. Truy ngược hai chiều

### Yêu cầu → màn → trạng thái → ca kiểm

| Yêu cầu | Màn | Trạng thái V | Ca kiểm |
|---|---|---|---|
| G1 | S6 | V11, V14 | T-G1a–f |
| G2 | S3, S2-T3 | V04, V08, V09 | T-G2a–c |
| G3 | S4, S2-T2/T3 | V10, V11 | T-G3a–c |
| G4 | S5, S2-T6 | V12, V13 | T-G4a–d |
| G5 | S2-T6 | V07 | T-G5a–e |
| G6 | S2-T2/T3, K5 | V01 | T-G6a–e |
| G7 | S3/S4/S6 | V04 | T-G7a/b |
| G8 | S9, S1 | V01, V17 | T-G8a/b |
| E1 | S7 | V15 | T-E1a/b |
| E2 | — | — | T-E2a |
| E3 | S2-T3 | V04, V05 | T-E3a/b |
| E4 | S7, S2-T6 | — | T-E4a |
| E5 | S2-T6 | V07 | T-E5a/b |
| E6 | toàn module | — | T-E6a |

### Màn → yêu cầu

| Màn | Yêu cầu |
|---|---|
| S1 | D1, D3, G8, W1–W5 |
| S2-T1 | G8 |
| S2-T2 | G3, G6, B |
| S2-T3 | G2, G6, G7, E3 |
| S2-T4 | D3, M1 |
| S2-T5 | PL |
| S2-T6 | G4, G5, E5 |
| S2-T7 | nhật ký |
| S3 | G2, G7 |
| S4 | G1, G3 |
| S5 | G4 |
| S6 | G1, G7 |
| S7 | B, E1–E4 |
| S8 | M1, D3 |
| S9 | G8 |

### Menu → màn

| Menu | Màn |
|---|---|
| MENU-1 | S1, S2, S4, S5 |
| MENU-2 | S3 |
| MENU-3 | S6 |
| MENU-4 | S7 |
| MENU-5 | S8 |
| MENU-6 | S9 |

**Coverage:** đủ 8 G, 6 E, 9 màn, 7 tab, 17 trạng thái, 6 menu, 4 quyết định.

**Lỗ hổng đã ghi** (không tự lấp):
1. UI quản trị G7 chưa có chỗ trong 9 màn.
2. Chưa có dialog Thay bằng chứng.
3. Grant thực cho `CRM_MAU_TAI` chờ quản trị.
4. Hạn n ngày cho W2 chưa chốt.
5. Chưa có cột người phụ trách.
