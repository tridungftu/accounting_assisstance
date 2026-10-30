# CHUẨN CORE — SDK

**Tệp:** `CHUAN-CORE-SDK-v1.0.md`  
**Phiên bản:** v1.0  
**Ngày Anh duyệt phiếu SDK bản 2:** 30/10/2026, 17:30 — CD-038  
**Văn bản chuẩn:** chờ Anh xem (CD-034 mục 4); đã qua review Opus (Đạt) và sửa 5 điểm nhỏ.

**Đối tượng:** Người lập trình module, engine, adapter và giao diện kết nối Core; áp dụng cho lập trình viên nội bộ và AI worker.

**Phạm vi:** SDK Python, SDK JavaScript, khung tiến trình, manifest gói, lớp dữ liệu giao tiếp `contract/`, sổ contract và bộ kiểm tuân thủ.

**Căn cứ đã duyệt:**

- `docs\47-core\PHIEU-DUYET-SDK.md`, bản 2: duyệt toàn phiếu và phạm vi CRM thử Core ở G2; câu 1 **A**, câu 2 **B**.
- `docs\47-core\engine\PHIEU-CAU-HOI-ENGINE.md`: câu 1 **C**, câu 2 **A**, câu 3 **A**.
- `docs\47-core\g1\DAC-TA-SDK.md`.
- `docs\47-core\g1\CONTRACT-DU-LIEU.md`.
- `docs\47-core\g1\CONTRACT-NGHIEP-VU.md`.
- `docs\47-core\chuan\CHUAN-CORE-CSDL-v1.0.md`.
- `docs\47-core\chuan\CHUAN-CORE-API-v1.0.md`.
- CD-026 đến CD-038 trong `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md`, trong phạm vi liên quan.

Đây là chuẩn thiết kế đích tập hợp quyết định đã duyệt, không xác nhận SDK hoặc các chức năng mô tả đã được triển khai. Các chữ ký dưới đây là giao diện đích của SDK; không được suy ra đường dẫn import, hàm SQL hoặc endpoint chưa có.

Kết quả phê duyệt CD-038 được áp dụng tại những chỗ đặc tả trước đó còn ghi “chờ Anh” về phạm vi phí, VAT cọc và ba câu engine. Những điểm khác chưa được chốt vẫn giữ trạng thái chờ.

## 1. Thay đổi

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| v1.0 | 30/10/2026 | Bản đầu; tập hợp SDK Python/JS, khung tiến trình, manifest, contract và bộ kiểm. Áp dụng SDK 1A/2B và engine 1C/2A/3A theo CD-038. |

Mọi thay đổi sau v1.0 phải tăng phiên bản và ghi rõ trong mục này.

## 2. Kết luận

1. Module dùng dịch vụ chung qua SDK; giữ nghiệp vụ và dữ liệu riêng đúng phạm vi.
2. SDK Python có 12 dịch vụ; engine chỉ nhận giao tiếp việc, tệp và trạng thái được cấp.
3. Giao diện chỉ gọi Core qua SDK JS; không gọi trực tiếp cổng module/engine.
4. Mỗi module/engine chạy tiến trình riêng; Core cấp cổng, xác minh sẵn sàng và điều phối dừng.
5. Core dùng tài khoản máy riêng; module dùng tài khoản hạn chế; engine giữ bí mật có tài khoản riêng từng engine.
6. Bí mật nhận qua stdin/handle có giới hạn quyền; không qua biến môi trường, dòng lệnh hoặc manifest.
7. Gói module bắt buộc có `module.json` và `contract/`; thiếu hoặc sai thì không cài.
8. Dữ liệu giao tiếp là JSON hai lớp; contract nghiệp vụ mới hoặc bản mới đang dùng phải được Anh duyệt.
9. Lịch giá bán chia đủ 100%; cho phép nhiều đợt cọc và cọc cuối, dồn VAT theo CD-038; toàn cọc là lỗi.
10. Thành phần chỉ được phát hành khi các kiểm C0/C1 áp dụng đã đạt và không thêm lỗi so với nền test.

## 3. Bắt buộc

Nhãn trách nhiệm:

- **[Core]**: Core cung cấp và cưỡng chế.
- **[Module]**: người lập trình module phải thực hiện.
- **[Engine]**: người lập trình engine/adapter phải thực hiện.

Các ví dụ dùng `mau_demo`, một module giả định với dữ liệu **DEMO**. Đây không phải module thử G2 đã chọn; module thử G2 là **CRM với dữ liệu DEMO**.

### 3.1. Ranh giới SDK, dữ liệu và quyền

**[Core] [Module] [Engine]**

- Core quản lý danh tính, quyền, tài liệu, tệp, kết quả, điều phối và vòng đời tiến trình.
- Module giữ quy tắc nghiệp vụ và dữ liệu riêng trong `mod_<ma>`.
- Module đọc dữ liệu module khác qua contract công bố đã đăng ký **và** được cấp quyền.
- Engine không có login PostgreSQL, không nhận dịch vụ `du_lieu_rieng`, không gọi SQL để nhận việc hoặc ghi kết quả.
- Khai báo quyền trong manifest là yêu cầu cấp quyền, không phải quyền đã được cấp.
- SDK kiểm khai báo để phát hiện sai sót; ranh giới an ninh thực là role/ACL, RLS, hàm Core xác minh ủy nhiệm và cách ly tiến trình.

**[Module]** Khai báo bốn vùng truy cập:

| Vùng | Phạm vi |
|---|---|
| V1 — riêng | Bảng/hàm của chính `mod_<ma>`. |
| V2 — ghi chung | Hàm Core được cấp; không DML trực tiếp bảng chung. |
| V3 — danh mục | Chỉ đọc phần danh mục chung được cấp. |
| V4 — công bố | Đọc đúng contract và phiên bản tại `cong_bo_<nguon>`; sự kiện qua bus Core. |

Không khai bảng riêng của module khác thành danh mục chung; không dùng view/hàm trung gian để che truy cập chéo.

### 3.2. Kiểu và quy ước SDK Python

**[Core] [Module] [Engine]**

| Kiểu/quy ước | Cách dùng |
|---|---|
| `ctx: NguCanh` | Bất biến, do SDK dựng sau xác thực Core; chứa người, module, pháp nhân, operation và trace. Bí mật không xuất qua `repr`, JSON hoặc log. |
| `tx: GiaoDich` | Transaction đúng login, role, schema và pháp nhân; ngữ cảnh được xác minh bằng mã phiên/ủy nhiệm. |
| `Ma` | UUID; ngoại lệ khóa kiểm toán hiện hữu giữ dạng chuỗi theo đặc tả. |
| `Trang[T]` | `danh_sach`, `con_tiep`, `con_tro_tiep`. |
| `ThamChieuTep` | Contract `tham_chieu_tep.v1`; không chứa đường dẫn vật lý hoặc URL tùy ý. |
| `BienNhanViec` | `viec_id`, `trang_thai`, `request_id`; địa chỉ theo dõi ở header `Location`; chỉ trả sau commit. |
| `GiuViec` | Handle bảo vệ gắn `viec_id`, thế hệ lease và mã ủy nhiệm riêng của lease; không serialize hoặc log. |
| Tiền, tỷ lệ | Python dùng `Decimal`; JSON dùng chuỗi decimal. |
| Ngày, thời điểm | Ngày nghiệp vụ `YYYY-MM-DD`; thời điểm response RFC 3339 UTC, kết thúc `Z`. |
| `row_version` | Chuỗi số nguyên trên JSON; khác revision nội dung, phiên bản nghiệp vụ và mã băm căn cứ. |

Lỗi SDK:

```text
LoiSDK(
    ma,
    thong_diep,
    request_id,
    thu_lai_duoc,
    http_status,
    chi_tiet=None
)
```

`chi_tiet` chỉ chứa các cặp `{truong, ma}` đã đăng ký, không chứa giá trị đầu vào hoặc nội dung nguồn.

| Tình huống | HTTP |
|---|---|
| Thiếu/sai xác thực | `401` |
| Thiếu quyền | `403` |
| Đối tượng không thuộc phạm vi được thấy | `404` |
| Xung đột CAS, chống trùng hoặc trạng thái | `409` |
| Dữ liệu tạm hết hạn | `410` |
| Schema hoặc dữ liệu không hợp lệ | `422` |
| Phụ thuộc chưa sẵn sàng | `503` |

Các lỗi riêng của dịch vụ bổ sung cho bảng này.

### 3.3. SDK Python — 12 dịch vụ

**[Core]** cung cấp các dịch vụ dưới đây. **[Module]** dùng theo quyền được cấp. **[Engine]** chỉ dùng phần giao tiếp được Core cấp cho công việc, không nhận toàn bộ SDK backend module.

Các tên biến trong ví dụ như `ctx`, `tx`, `khoa`, `tep_id`, `contract_da_ghim` và `tham_so` đại diện cho dữ liệu đã được xác thực hoặc kiểm schema. Ví dụ không khai thêm operation, quyền hay hàm SQL.

| # | Dịch vụ và hàm chính | Ví dụ dùng ngắn |
|---|---|---|
| 1 | **`danh_tinh`** — `hien_tai(ctx) -> DanhTinh`; `kiem_quyen(ctx, hanh_dong, doi_tuong) -> None`; `nhan_request(request, instance) -> NguCanh`. | `ctx = danh_tinh.nhan_request(request, instance)` |
| 2 | **`tai_lieu`** — `liet_ke(ctx, loc, con_tro=None) -> Trang[TaiLieu]`; `lay(ctx, tai_lieu_id) -> TaiLieu`; `tao(ctx, tep_id, thong_tin, khoa) -> TaiLieu`. | `ho_so = tai_lieu.lay(ctx, tai_lieu_id)` |
| 3 | **`tep`** — `tai_len(ctx, luong, ten, mime, khoa) -> ThamChieuTep`; `tham_chieu(ctx, tep_id) -> ThamChieuTep`; `mo_doc(ctx, tep_id) -> BinaryIO`. | `tham_chieu = tep.tai_len(ctx, luong, ten, mime, khoa)` |
| 4 | **`ket_qua`** — `lay(ctx, ket_qua_id) -> KetQua`; `ghi(tx, tep_id, contract, khoa, giu_viec=None) -> Ma`; `tao_revision(tx, ket_qua_id, revision_truoc, tep_id, ly_do, khoa) -> KetQua`. | `ket_qua_id = ket_qua.ghi(tx, tep_id, contract_da_ghim, khoa)` |
| 5 | **`du_lieu_rieng`** — `giao_dich(ctx) -> ContextManager[GiaoDich]`; `doc(tx, ma_truy_van, tham_so) -> Trang[dict]`; `ghi(tx, ma_lenh, tham_so, row_version, khoa) -> BienNhan`. | `trang = du_lieu_rieng.doc(tx, ma_truy_van_da_dang_ky, tham_so)` |
| 6 | **`cong_bo`** — `liet_ke(ctx) -> list[KhaiBaoCongBo]`; `doc(tx, contract, tham_so) -> KetQuaCongBo`; `kiem_phien_ban(tx, contract, doi_tuong_id, phien_ban, ma_bam) -> CanCu`. | `nguon = cong_bo.doc(tx, contract_da_ghim, tham_so)` |
| 7 | **`su_kien`** — `phat(tx, loai, phien_ban, tham_chieu, khoa) -> Ma`; `nhan(tx, loai=None, gioi_han=100) -> list[SuKien]`; `xac_nhan(tx, su_kien_id) -> bool`. | `da_ack = su_kien.xac_nhan(tx, su_kien_id)` |
| 8 | **`engine`** — `liet_ke(ctx) -> list[KhaNang]`; `kha_nang(ctx, capability) -> KhaNang`; `gui_viec(ctx, capability, dau_vao, khoa) -> BienNhanViec`. | `bien_nhan = engine.gui_viec(ctx, "ocr.trich_van_ban@1", dau_vao, khoa)` |
| 9 | **`quy_trinh`** — `liet_ke(ctx) -> list[QuyTrinh]`; `bat_dau(ctx, ma, phien_ban, dau_vao, khoa) -> BienNhanViec`; `tiep_tuc(ctx, lan_chay_id, buoc, revision_truoc, du_lieu, khoa) -> BienNhanViec`. | `bien_nhan = quy_trinh.bat_dau(ctx, ma, phien_ban_da_ghim, dau_vao, khoa)` |
| 10 | **`viec`** — `lay(ctx, viec_id) -> Viec`; `ket_qua(ctx, viec_id) -> list[KetQua]`; `huy(ctx, viec_id, khoa) -> BienNhanViec`; `bao_tien_do(tx, giu_viec, muc) -> bool`. | `trang_thai = viec.lay(ctx, bien_nhan.viec_id)` |
| 11 | **`kiem_toan`** — `ghi(tx, hanh_dong, doi_tuong, ket_luan) -> str`; `tra_cuu(ctx, loc, con_tro=None) -> Trang[BanGhiKiemToan]`; `ghi_so_do(ctx_tien_trinh, so_do) -> BienNhan`. | `ma_audit = kiem_toan.ghi(tx, hanh_dong, doi_tuong, ket_luan)` |
| 12 | **`ma_hoa`** — `ma_hoa(ctx, cot, gia_tri) -> BanMa`; `tra_hmac(ctx, cot, gia_tri) -> DauTraCuu`; `hien_thi_rut_gon(ctx, cot, ban_ma) -> str`; `giai_ma(ctx, cot, doi_tuong_id, ly_do) -> str`. | `ban_ma = ma_hoa.ma_hoa(ctx, cot_da_dang_ky, gia_tri_demo)` |

Các ràng buộc theo dịch vụ:

**[Module] Tài liệu và tệp**

- Tệp đi qua File Store Core; không mở trực tiếp kho tệp máy chủ.
- Kiểm quyền trước khi trả bytes. Cùng hash không đồng nghĩa cùng quyền.
- Mỗi tệp tải lên không quá 20 MB theo phiếu API: **20 MiB = 20.971.520 byte** trong OpenAPI. Giới hạn nhỏ hơn của capability vẫn áp dụng.
- `tep.mo_doc` đóng luồng khi thoát phạm vi sử dụng.
- Lỗi tệp có thể gồm `413`, `415`, `422`, `409`, `404`, `410`.

**[Core] [Module] [Engine] Kết quả**

- Core tự gắn module/engine/function/version, việc, bước và lần thử từ instance/lease đã xác minh.
- Caller chỉ gửi tham chiếu nguồn; Core kiểm quyền, hash và revision.
- Không nhận provenance OCR do module tự khai làm bằng chứng.
- `ket_qua.ghi` có thể từ chối khi sai schema, sai tham chiếu hoặc mất lease.
- Kết quả chạy thành công không tự trở thành kết quả đã được duyệt.

**[Module] Dữ liệu riêng và công bố**

- Mã truy vấn/lệnh phải được đăng ký; tham số khớp schema.
- `CHO` nghĩa thiếu nguồn hoặc chưa đủ điều kiện công bố; không thay lỗi thiếu quyền.
- Đọc dữ liệu công bố bền vững không đòi tiến trình module nguồn đang chạy.
- Căn cứ đã đổi phải được phát hiện bằng kiểm phiên bản/hash; không lấy bản mới nhất để thay thế ngầm.

**[Module] Sự kiện**

- Bus giao ít nhất một lần; handler phải chịu được giao lại.
- Payload bus chỉ chứa tham chiếu UUID theo contract, không nhúng toàn văn nghiệp vụ.
- Ghi nghiệp vụ và ACK trong cùng transaction.
- ACK lặp trả `False`; ACK khi chưa nhận là xung đột.

**[Core] [Module] [Engine] Engine và quy trình**

- Ghim đúng capability, engine, adapter, contract và phiên bản quy trình.
- Không tự chọn engine hoặc phiên bản mới nhất.
- Backend được chọn chưa sẵn sàng phải trả lỗi phù hợp, không tự đổi backend.
- Việc có tác động ngoài chưa rõ giữ trạng thái `CHUA_RO`, không tự retry.

**[Core] [Module] Kiểm toán và mã hóa**

- Core tự gắn actor, trace và thời điểm.
- Metadata audit theo danh mục cho phép; không ghi nội dung nhạy cảm.
- Cột nhóm A phải đăng ký; khóa do Core giữ và chọn.
- Hiển thị rút gọn tối đa bốn số cuối; xem đủ cần quyền và audit trước khi trả.
- Module không nhận khóa mã hóa, không truyền khóa qua SQL/GUC, không sao chép bộ mã hóa hoặc Mask vào module.
- Thuật toán/adapter mã hóa và JSON path cụ thể còn chờ chốt theo chuẩn CSDL; không tự chọn thêm trong module.

### 3.4. Transaction, chống trùng và việc nền

**[Core] [Module]**

Các hàm nhận `tx` không tự commit. Lời gọi HTTP tới Core có transaction riêng.

Khi cần ghi nghiệp vụ cùng biên nhận, hàng việc hoặc bus trong một transaction, SDK phải gọi cửa hàm CSDL được cấp trên **chính `tx` và cùng kết nối**. Không mô phỏng nguyên tử bằng hai lời gọi HTTP.

Biên nhận operation module:

- Ghi qua V2 vào `loi_tai_lieu.bien_nhan_thao_tac`.
- Bất biến, giữ vĩnh viễn.
- Cùng commit với nghiệp vụ hoặc tạo việc; rollback không có biên nhận hoàn tất.
- Khóa duy nhất: `(phap_nhan_id, module, operation, client_key)`.
- Lưu người tạo, fingerprint và kết quả hoặc `viec_id`.
- Core chỉ giữ khóa request đang chạy, không có biên nhận hoàn tất thứ hai cho operation module.

Fingerprint gồm operation ổn định và body logic chuẩn hóa, bao gồm ID đích, pháp nhân, hash bytes tệp nếu có; không gồm route, method hoặc khóa chống trùng. Alias cũ/v1 dùng chung operation, body logic và khóa.

| Tình huống | Xử lý |
|---|---|
| Cùng khóa, cùng fingerprint, đã hoàn tất | Kiểm quyền hiện tại rồi phát lại kết quả/việc cũ. |
| Cùng khóa, khác fingerprint | `409 KHOA_CHONG_TRUNG_KHAC_NOI_DUNG`. |
| Request đang xử lý | `409 YEU_CAU_DANG_XU_LY`, `Retry-After: 2`. |
| Không còn quyền thấy kết quả | `404`. |
| Crash sau commit, trước response; restart; replay sau 24 giờ | Dùng biên nhận module đã lưu, không tạo tác động mới. |

Thời hạn 24 giờ của biên nhận operation Core không áp dụng cho biên nhận nghiệp vụ module.

**[Core] [Engine]** Worker nhận và giữ việc qua kênh Core:

```text
nhan_viec(instance) -> GiuViec | None
gia_han(giu_viec) -> GiuViec
ket_thuc(giu_viec, ket_qua) -> bool
```

Core cấp mã ủy nhiệm riêng theo `viec_id` và thế hệ lease. Không lưu token HTTP ngắn hạn để chạy việc nền. Mất lease, restart hoặc thu hồi quyền làm mã cũ mất hiệu lực; chỉ cấp mã mới sau kiểm quyền, đối chiếu tác động và nhận lease mới.

Mất lease phải từ chối cập nhật, rollback phần lưu kết quả liên quan. Không tuyên bố exactly-once cho tác động ngoài CSDL chưa được đối chiếu.

### 3.5. SDK JavaScript

#### 3.5.1. Gọi API và xử lý lỗi

**[Core] [Module]**

| Thành phần | Hành vi |
|---|---|
| `api.goi({phuong_thuc, duong_dan, phap_nhan_id, module, du_lieu, khoa, signal})` | Chỉ gọi cùng nguồn `/api/v1/`; tự gắn CSRF, ngữ cảnh pháp nhân/module và trace. |
| `thong_bao.loi(root, loi)` | Thông báo tiếng Việt, có hành động phục hồi; `request_id` nằm trong phần chi tiết để sao chép. |
| `khung.dung(root, khai_bao_da_loc_quyen)` | Dựng khung lưới, phần, thẻ tổng quan và thanh icon theo khai báo đã lọc quyền. |
| `bang.dung(root, {cot, dong, row_version, khi_sua})` | Bảng nhập liệu chung, giữ nháp khi vẽ lại và kiểm theo schema trường. |

Ví dụ gọi operation đã khai trong manifest `mau_demo`:

```javascript
try {
  const bienNhan = await api.goi({
    phuong_thuc: "POST",
    duong_dan: "/api/v1/module/mau_demo/nhan-dang",
    phap_nhan_id,
    module: "mau_demo",
    du_lieu: du_lieu_nhan_dang_da_kiem,
    khoa: khoa_cua_y_dinh_ghi,
    signal
  });

  viec.theo_doi(bienNhan.viec_id, { khi_doi, signal });
} catch (loi) {
  thong_bao.loi(root, loi);
}
```

Ví dụ thể hiện giao diện đích; schema đầu vào và handler phải có trong gói trước khi sử dụng.

Mỗi ý định ghi giữ nguyên khóa, body và ngữ cảnh đến khi biết kết quả:

- Mất mạng/timeout không tạo khóa mới.
- CAS cũ: giữ nháp, tải bản mới để người dùng đối chiếu.
- Khóa khác nội dung: dừng gửi lại.
- Request đang xử lý: chờ theo `Retry-After`.
- Đổi người, pháp nhân hoặc màn: hủy theo dõi và bỏ phản hồi cũ; không tự gửi lại bằng ngữ cảnh mới.

Lỗi trường dùng `chi_tiet[].truong` để gắn đúng ô. Không phản chiếu giá trị nguồn trong lỗi. Mã lỗi/HTTP/tên trường phải được đăng ký. Phản hồi sai contract bị Core đổi thành `502 PHAN_HOI_SAI_CONTRACT`.

Frontend giữ khóa không thay thế biên nhận bền vững ở backend.

#### 3.5.2. Việc lâu

**[Core] [Module]**

```text
viec.theo_doi(viec_id, {khi_doi, signal})
viec.huy(viec_id, khoa)
```

- Việc lâu trả `202` sau commit, body theo `urn:ktt:contract:viec.v1#/$defs/da_nhan`.
- Poll theo `Retry-After`; dừng theo dõi khi kết thúc, rời màn hoặc đổi ngữ cảnh.
- `waiting_input` phải hiển thị yêu cầu bổ sung.
- Hủy là đề nghị; tiếp tục theo dõi đến khi có trạng thái xác nhận.
- Không suy timeout, mất heartbeat hoặc mất kết nối thành thành công.

Trạng thái việc:

```text
queued / running / waiting_input / cancel_requested /
cancelled / succeeded / failed / interrupted
```

`succeeded` không đồng nghĩa kết quả đã được phê duyệt. Việc mất heartbeat sau restart hoặc hết lease phải thể hiện `interrupted`, không tự chạy lại mù.

#### 3.5.3. Ô nhập và khung giao diện chuẩn

**[Module]**

| Loại | Quy tắc |
|---|---|
| Tiền | Chuỗi decimal kèm đơn vị; không đi qua `Number`/float. `_minor` cũ chuyển theo số chữ số đơn vị đã khai báo. |
| Tỷ lệ | Khai rõ đơn vị; nhập `12,5%` gửi chuỗi `"12.5"` với đơn vị `%`/`phan_tram` theo schema tương ứng; không tự đổi sang tỷ phần. |
| Ngày | Nhập/hiện `dd/mm/yyyy`; kiểm ngày lịch thực rồi gửi `YYYY-MM-DD`. |
| Giá trị thiếu | Giữ đúng nghĩa thiếu/`null`/chưa rõ; không tự điền `0`. |
| Lỗi ô | Hiện tại ô, có nhãn truy cập, giữ nháp; không tự làm tròn để vượt kiểm. |

Khung dùng hai cấp lưới. Trang module có 2–4 thẻ mở đúng danh sách đã lọc. Badge chỉ đếm việc chờ của người đăng nhập; số 0 ẩn; quá hạn có màu kèm chữ. Server lọc quyền và trả số; tổng chưa đầy đủ phải thể hiện tình trạng đó.

Giữ breadcrumb, tìm nhanh, mục hay dùng và thanh icon trái theo khung chung. Không dùng quyền hiển thị giao diện để thay kiểm quyền backend.

### 3.6. Khung chạy module/engine

#### 3.6.1. Nhận cổng và báo sẵn sàng

**[Core]**

1. Khóa phối hợp theo chủ chạy/máy chủ; lấy cổng cố định và thế hệ sở hữu từ sổ cổng.
2. Bind loopback với `SO_EXCLUSIVEADDRUSE` trước bind; không dùng `SO_REUSEADDR`.
3. Các request đồng thời dùng chung một lần khởi động.
4. Khởi chạy từ hồ sơ đã duyệt; chỉ chuyển request sau khi xác minh readiness.

**[Module] [Engine]**

- Nhận cấu hình và bí mật qua stdin hoặc handle riêng có giới hạn quyền.
- Python hỗ trợ chuyển giao nhận dữ liệu `socket.share(pid)` bằng `socket.fromshare`.
- Core giữ bản handle để thu hồi; chỉ một bên có quyền accept theo trạng thái bàn giao.
- Engine cũ chưa nhận socket có thể dùng nhánh chuyển tiếp: Core đóng listener rồi truyền đúng cổng bằng tham số. Nhánh này có khoảng hở, phải kiểm khi triển khai.
- Bind thất bại báo `CONG_BI_CHIEM`; không dò cổng khác, không dừng ứng dụng lạ.

Thông điệp sẵn sàng gồm mã chủ, instance, PID và định danh lần tạo tiến trình, nonce khởi động, phiên bản, capability/contract thực có, cổng và kết quả kiểm readiness.

**[Module]** Chỉ báo sẵn sàng khi:

- Login runtime, role và ngữ cảnh hợp lệ.
- `phien_ban_du_lieu` cùng checksum gói khớp `loi.lich_su_doi_cau_truc`.
- Không tự migrate khi khởi động.

**[Engine]** Kiểm model/capability thực; không thử login CSDL.

Listener hoạt động hoặc `/healthz` thành công chưa chứng minh capability sẵn sàng.

#### 3.6.2. Xác thực từng request

**[Core] [Module]**

`danh_tinh.nhan_request` chạy trước mọi handler, kể cả request từ loopback. Phải kiểm:

- Chữ ký bằng khóa kiểm chứng nhận khi bootstrap; khóa ký chỉ Core giữ.
- Issuer/audience đúng module và instance hiện hành.
- Thời điểm phát hành, hết hạn và TTL tối đa 30 giây.
- Operation, hash method/path/body bytes thực nhận và khóa chống trùng.
- Nonce tiêu thụ nguyên tử một lần trong instance, giữ đến hết hạn.

Thiếu token, sai chữ ký/instance, hết hạn, TTL vượt giới hạn, nonce lặp hoặc hash lệch đều trả `401` trước handler. Hai request cạnh tranh cùng nonce chỉ một request được vào.

Nonce vận chuyển khác khóa chống trùng nghiệp vụ. Retry dùng token/nonce mới nhưng giữ khóa và fingerprint cũ.

Core lọc header nội bộ do client gửi. Module/frontend không tự dựng `ctx`. CSDL vẫn xác minh mã bí mật theo login, module, pháp nhân, hành động và lease.

#### 3.6.3. Tài khoản máy và nhận bí mật

**[Core] [Module] [Engine]**

| Tiến trình | Tài khoản và phạm vi |
|---|---|
| Core | Tài khoản Windows riêng, ví dụ `ktt_core`. |
| Module | Tài khoản máy hạn chế, ví dụ `ktt_module`, khác tài khoản Core. |
| Engine thông thường | Tài khoản máy hạn chế; không nhận login CSDL. |
| Engine giữ bí mật | Mask, AI Cloud, tải hóa đơn, ABBYY: **mỗi engine một tài khoản máy riêng**, khác tài khoản module. |
| Engine cần màn hình | Tải hóa đơn: phiên Windows riêng có màn hình (CD-038 engine 2A). ABBYY: tài khoản riêng (CD-038 engine 3A); quyền/phiên cụ thể ghi ngoại lệ, hỏi Anh (CD-033). Không tự mở rộng quyền cho engine khác. |

Không chạy chung tài khoản Core rồi chỉ hạn chế token của tiến trình con để coi là đã cách ly.

Bộ khởi chạy:

- Chỉ kế thừa allowlist handle bootstrap/listener.
- Không truyền handle kho bí mật hoặc process Core đặc quyền.
- Bỏ quyền debug/impersonate và khả năng thoát Windows Job.
- Chặn tiến trình con mở/đọc/ghi bộ nhớ Core, duplicate handle/token hoặc sửa ACL để lấy lại quyền.

Kho bí mật `D:\DU-LIEU-KE-TOAN\bi-mat\` chỉ cho tài khoản dịch vụ Core đọc ở lớp runtime. Bí mật bọc DPAPI phạm vi **người dùng của tài khoản Core**, không dùng `CRYPTPROTECT_LOCAL_MACHINE`.

Credential và bí mật được lấy từ két Core rồi chuyển qua stdin/handle được bảo vệ:

- Mỗi module chỉ nhận credential runtime của chính mình.
- Mỗi instance nhận credential SDK riêng cùng instance ID qua stdin hoặc handle kế thừa được bảo vệ, cùng kênh bootstrap nhận listener; Core kiểm credential và instance còn sống trên mỗi lời gọi SDK, thu hồi khi dừng hoặc crash (CHUAN-CORE-API §3.11c).
- Runtime không nhận credential migration.
- Engine chỉ nhận bí mật cần cho phạm vi được giao.
- Không truyền qua biến môi trường, dòng lệnh, manifest, tệp cấu hình gói hoặc log.
- Không dựng DSN chứa mật khẩu; truyền `password=` riêng cho driver và không log tham số kết nối.
- SDK đặt ngữ cảnh theo transaction và làm sạch khi trả kết nối về pool.

Phải có script tạo tài khoản/cấp quyền thư mục chạy lại được trên máy Anh và khi chuyển máy chủ; chạy lại không cấp rộng thêm. Anh chỉ đồng ý quyền quản trị cho bước thiết lập; runtime không giữ quyền quản trị.

Ngoại lệ engine cũ như ABBYY phải ghi rõ tài khoản, quyền và lý do; không tự nới quyền ngoài ngoại lệ đã duyệt.

Kiểm cách ly dùng bí mật DEMO từ chính tiến trình module/engine. Không đạt cách ly thì không kích hoạt; không dùng kho thật để kiểm.

#### 3.6.4. Dừng có kiểm soát và đánh thức

**[Core] [Module] [Engine]**

Trạng thái tiến trình:

```text
stopped / starting / ready / busy / dang_dung / failed
```

Trạng thái này độc lập với công tắc nghiệp vụ `TAT/THU/VAN_HANH` và trạng thái việc.

Khi Core yêu cầu dừng:

1. Ngừng nhận việc/request mới.
2. Tiếp tục heartbeat cho việc đang giữ.
3. Chờ hoàn tất hoặc điểm dừng an toàn.
4. Bàn giao kết quả.
5. Xác nhận dừng và đóng handle của tiến trình con.

Với listener chia sẻ, không gọi `shutdown` làm hỏng listener Core giữ. Core giữ cổng cố định khi tiến trình dừng.

`dang_dung` trả `503 TIEN_TRINH_DANG_DUNG`, `Retry-After: 2`. Quá 300 giây vẫn drain, giữ cổng cho Admin xử lý; không tự coi việc đã hủy hoặc cưỡng bức hủy để đóng rảnh.

Mặc định tự kích hoạt và tự đóng sau **5 phút rảnh**. “Rảnh” đòi hỏi đồng thời:

- Không request hoặc luồng tải.
- Không kết quả chưa bàn giao hoặc lượt Mask đang dùng.
- Không lease.
- Hộp nhận rỗng.
- Không việc chờ được phép nhận.

Quyết định đóng và dispatch dùng cùng khóa phối hợp.

Có việc `queued` hoặc sự kiện chờ thì Core **khởi động ngay** module đang được phép hoạt động; không cần chờ HTTP. Module `TAT` hoặc chưa kích hoạt giữ hàng chờ, không bị tự bật.

**Ngoại lệ Mask theo CD-038:** Anh mở khóa danh mục tại máy chủ; Mask **không tự đóng khi danh mục đang mở**.

Core quản lý cây tiến trình bằng Windows Job với `KILL_ON_JOB_CLOSE`. Cơ chế này xử lý Core crash/đóng Job, không thay drain thông thường. Core chỉ xử lý tiến trình đã xác minh thuộc mình. Ba lỗi khởi động đưa thành phần vào trạng thái chờ Admin; không tự đổi cổng hoặc dừng tiến trình lạ.

#### 3.6.5. Số đo vận hành

**[Core]**

Ghi từng lần khởi động: giờ yêu cầu, bắt đầu, sẵn sàng/thất bại, thời gian xử lý, thời gian rảnh trước đóng, số lần khởi động/ngày, RAM và CPU kèm cửa sổ đo.

RAM/CPU và giới hạn lấy từ Windows Job accounting do Core đo; số tự khai của module/engine chỉ bổ trợ. Thiếu số đo ghi “chưa đo”.

Hệ thống chỉ đề xuất đổi chế độ theo số đo; **Admin bấm áp dụng**, có CAS và audit. Không tự đổi sang luôn chạy.

### 3.7. Quy tắc riêng cho engine

**Bắt buộc (CD-036):** chỉ chép code gốc khi bắt buộc, ghi nguồn + SHA256 + phiên bản; không sửa bản gốc khi chưa hỏi Anh (Mask v2 theo `CLAUDE.md` của Mask v2); test gốc phải đạt khi chạy qua engine với dữ liệu giả.

**[Engine]**

- Ưu tiên dùng lại code gốc đang hoạt động; bọc adapter và khung vận hành theo Core.
- Giữ kiểu vào/ra, bất biến đầu vào, bằng chứng và trạng thái `XONG/CHO/LOI`.
- Tách trạng thái engine, trạng thái việc và trạng thái duyệt.
- AI chỉ đi qua cổng AI chung của phần mềm. Luôn có đường Local; Cloud chỉ qua Mask file v2.
- Không gọi thẳng máy AI, API Anthropic/OpenAI hoặc tạo cổng/bộ che riêng.
- Chỉ công bố capability thực đạt; OCR văn bản không tự đồng nghĩa trích bảng.

**Trích xuất — CD-038 câu engine 1C**

- Chép phần trích xuất vào `e_trich_xuat`, ghi nguồn và SHA; không sửa bản gốc review đang đóng băng.
- Đổi câu hỏi sang mẫu của cổng AI chung.
- Đo trước/sau trên bộ đáp án hiện có `DAP_AN_*.tsv`, 37 tham số.
- Độ chính xác không được thấp hơn bản gốc. Thấp hơn thì dừng, báo Anh kèm số liệu.
- Test gốc được sửa phải ghi rõ ca nào đổi và vì sao.

**Tải hóa đơn — CD-038 câu engine 2A**

- Phần tải chạy trong phiên Windows riêng có màn hình để người dùng nhập CAPTCHA.
- Mỗi pháp nhân một hồ sơ trình duyệt; xóa hồ sơ sau phiên.
- Mật khẩu lấy từ két Core.
- Gọi cổng thuế thật chỉ khi Anh ra lệnh riêng.

### 3.8. Gói module và `module.json` mẫu đầy đủ

**[Module]**

Gói module là thư mục có `module.json`, `contract/` và các tệp được khai báo. Ví dụ bố cục:

```text
mau_demo/
  module.json
  contract/
  schema/
  migration/
  quy_trinh/
  giao_dien/
  goi/
```

Đây là bố cục minh họa. Các tệp được manifest tham chiếu phải có nội dung thực, đúng phiên bản và hash trước khi nộp gói.

Schema manifest:

- Module: `urn:ktt:manifest:module.v1`.
- Engine: `urn:ktt:manifest:engine.v1`.
- Phiên bản schema: `1.0.0`, draft 2020-12.

Mẫu dưới đây dùng cùng cấu trúc đặc tả SDK, đổi mã module minh họa thành `mau_demo`. Các contract DEMO không mặc nhiên được duyệt hoặc đăng ký.

```json
{
  "phien_ban_manifest": 1,
  "loai": "module",
  "ma": "mau_demo",
  "ten": "Tra cứu tài liệu DEMO",
  "phien_ban": "0.1.0-demo.1",
  "tuong_thich": {
    "core": ">=1.0.0 <2.0.0",
    "api": "v1",
    "sdk_python": ">=1.0.0 <2.0.0",
    "sdk_js": ">=1.0.0 <2.0.0",
    "contract": [
      "tham_chieu_tep.v1",
      "van_ban_tai_lieu.v1",
      "viec.v1"
    ]
  },
  "goi": {
    "tep_kiem_ke": "goi/kiem_ke.json",
    "thuat_toan_ma_bam": "sha256",
    "phu_thuoc_module": []
  },
  "contract": {
    "cong_bo": [
      {
        "ma": "ghi_chu",
        "phien_ban": "1",
        "module_so_huu": "mau_demo",
        "tep_mo_ta": "contract/cong_bo_ghi_chu.v1.json",
        "schema": "contract/cong_bo_ghi_chu.v1.schema.json",
        "vi_du": "contract/cong_bo_ghi_chu.v1.vi_du.json"
      }
    ],
    "su_kien_phat": [
      {
        "ma": "mau_demo.ghi_chu_doi",
        "phien_ban": "1",
        "module_so_huu": "mau_demo",
        "tep_mo_ta": "contract/ghi_chu_doi.v1.json",
        "schema": "contract/ghi_chu_doi.v1.schema.json",
        "vi_du": "contract/ghi_chu_doi.v1.vi_du.json"
      }
    ],
    "su_kien_nhan": [
      {
        "ma": "tai_lieu.cap_nhat",
        "phien_ban": "1",
        "module_so_huu": "loi",
        "tep_mo_ta": "contract/tai_lieu_cap_nhat.v1.json",
        "schema": "contract/tai_lieu_cap_nhat.v1.schema.json",
        "vi_du": "contract/tai_lieu_cap_nhat.v1.vi_du.json"
      }
    ],
    "dau_vao_nguon": [
      {
        "ma": "tham_chieu_tep.v1",
        "phien_ban": "1.0.0",
        "module_so_huu": "loi",
        "tep_mo_ta": "contract/tham_chieu_tep.v1.json",
        "schema": "contract/tham_chieu_tep.v1.schema.json",
        "vi_du": "contract/tham_chieu_tep.v1.vi_du.json"
      },
      {
        "ma": "van_ban_tai_lieu.v1",
        "phien_ban": "1.0.0",
        "module_so_huu": "loi",
        "tep_mo_ta": "contract/van_ban_tai_lieu.v1.json",
        "schema": "contract/van_ban_tai_lieu.v1.schema.json",
        "vi_du": "contract/van_ban_tai_lieu.v1.vi_du.json"
      }
    ]
  },
  "backend": {
    "diem_vao": "mau_demo.chay"
  },
  "giao_dien": {
    "diem_vao": "giao_dien/chinh.js",
    "tai_nguyen": [
      "giao_dien/chinh.js",
      "giao_dien/chinh.css"
    ],
    "icon": "file",
    "nhom_mau": "bao_cao",
    "thu_tu": 100,
    "trang_dau": "#mau_demo/tai_lieu",
    "thao_tac_khung": "tong_quan",
    "phan": [
      {
        "ma": "tai_lieu",
        "ten": "Tài liệu",
        "icon": "folder",
        "thu_tu": 1,
        "duong_dan": "#mau_demo/tai_lieu",
        "quyen_xem": "mau_demo.tai_lieu.doc"
      },
      {
        "ma": "ket_qua",
        "ten": "Kết quả",
        "icon": "file",
        "thu_tu": 2,
        "duong_dan": "#mau_demo/ket_qua",
        "quyen_xem": "mau_demo.ket_qua.doc",
        "dem": "cho_kiem"
      }
    ],
    "the": [
      {
        "ma": "cho_kiem",
        "nhan": "Kết quả chờ kiểm",
        "dem": "cho_kiem",
        "loc": {
          "phan": "ket_qua",
          "tham_so": {
            "trang_thai_duyet": "cho_kiem"
          }
        }
      },
      {
        "ma": "co_ghi_chu",
        "nhan": "Tài liệu có ghi chú",
        "dem": "co_ghi_chu",
        "loc": {
          "phan": "tai_lieu",
          "tham_so": {
            "co_ghi_chu": true
          }
        }
      }
    ]
  },
  "thao_tac": [
    {
      "ma": "danh_sach",
      "phuong_thuc": "GET",
      "duong_dan": "/tai-lieu",
      "dau_vao": "schema/loc.v1.json",
      "dau_ra": "schema/danh_sach.v1.json",
      "quyen": "mau_demo.tai_lieu.doc",
      "kieu": "dong_bo",
      "chong_trung": false
    },
    {
      "ma": "tong_quan",
      "phuong_thuc": "GET",
      "duong_dan": "/tong-quan",
      "dau_vao": "schema/khung_vao.v1.json",
      "dau_ra": "schema/khung_ra.v1.json",
      "quyen": "mau_demo.tai_lieu.doc",
      "kieu": "dong_bo",
      "chong_trung": false
    },
    {
      "ma": "luu_ghi_chu",
      "phuong_thuc": "PUT",
      "duong_dan": "/ghi-chu/{id}",
      "dau_vao": "schema/ghi_chu_vao.v1.json",
      "dau_ra": "schema/ghi_chu_ra.v1.json",
      "quyen": "mau_demo.ghi_chu.sua",
      "kieu": "dong_bo",
      "chong_trung": true,
      "kiem_row_version": true
    },
    {
      "ma": "nhan_dang",
      "phuong_thuc": "POST",
      "duong_dan": "/nhan-dang",
      "dau_vao": "schema/nhan_dang_vao.v1.json",
      "dau_ra": "urn:ktt:contract:viec.v1#/$defs/da_nhan",
      "quyen": "mau_demo.engine.goi",
      "kieu": "viec",
      "chong_trung": true,
      "quy_trinh": "nhan_dang_demo@1"
    }
  ],
  "du_lieu_rieng": {
    "bang": ["ghi_chu"],
    "ham": ["giai_pham_vi_demo", "kiem_nghia_vu_demo"],
    "phan_vung": "phap_nhan_id",
    "goi_migration": {
      "ma": "mau_demo",
      "phien_ban_du_lieu": 1,
      "tep_kiem_ke": "migration/kiem_ke.json",
      "thu_muc": "migration"
    },
    "v2_ghi_chung": [
      "bien_nhan_thao_tac",
      "tao_viec",
      "ghi_ket_qua"
    ],
    "v3_danh_muc": [
      {
        "doi_tuong": "danh_muc.doi_tac",
        "truong": ["id", "ten"]
      }
    ],
    "v4_cong_bo_doc": [],
    "cot_nhom_a": [
      {
        "bang": "ghi_chu",
        "cot": "tai_khoan_demo",
        "cot_ban_ma": "tai_khoan_ban_ma",
        "cot_phien_ban_khoa": "tai_khoan_phien_ban_khoa",
        "cot_hmac": "tai_khoan_hmac",
        "mien_hmac": "mau_demo.ghi_chu.tai_khoan_demo",
        "chuan_hoa": "so_tai_khoan_v1",
        "quyen_xem_du": "mau_demo.tai_khoan.xem_du"
      }
    ]
  },
  "ham_core_goi": [
    {
      "loai_ham": "resolver_mtq",
      "phien_ban_contract": "1",
      "ham": "giai_pham_vi_demo",
      "chu_ky": "schema/resolver_mtq.v1.json"
    },
    {
      "loai_ham": "kiem_nghia_vu",
      "phien_ban_contract": "1",
      "ham": "kiem_nghia_vu_demo",
      "chu_ky": "schema/kiem_nghia_vu.v1.json"
    }
  ],
  "ma_loi": [
    {
      "ma": "DEMO_GHI_CHU_KHONG_HOP_LE",
      "http": 422,
      "truong": ["ghi_chu"]
    }
  ],
  "quyen_yeu_cau": [
    {
      "tai_nguyen": "tai_lieu",
      "hanh_dong": ["doc"],
      "truong": ["id", "ten"],
      "bien_the": [],
      "pham_vi": "phap_nhan_va_ho_so_duoc_cap"
    },
    {
      "tai_nguyen": "tep",
      "hanh_dong": ["doc", "tai_xuong"],
      "truong": ["id", "mime", "kich_thuoc", "ma_bam"],
      "bien_the": ["goc"],
      "pham_vi": "tep_cua_tai_lieu_duoc_cap"
    },
    {
      "tai_nguyen": "ket_qua",
      "hanh_dong": ["doc"],
      "truong": ["id", "contract", "nguon", "trang_thai_duyet"],
      "bien_the": ["ocr_tho"],
      "pham_vi": "ket_qua_duoc_cap"
    },
    {
      "tai_nguyen": "engine",
      "hanh_dong": ["goi"],
      "capability": ["ocr.trich_van_ban@1"],
      "pham_vi": "viec_cua_module"
    },
    {
      "tai_nguyen": "ghi_chu",
      "hanh_dong": ["doc", "sua"],
      "pham_vi": "du_lieu_rieng_cung_phap_nhan"
    },
    {
      "tai_nguyen": "su_kien",
      "hanh_dong": ["phat", "nhan"],
      "loai": [
        "mau_demo.ghi_chu_doi@1",
        "tai_lieu.cap_nhat@1"
      ],
      "pham_vi": "cung_phap_nhan_duoc_cap"
    }
  ],
  "engine_dung": [
    {
      "capability": "ocr.trich_van_ban@1",
      "bat_buoc": true,
      "dau_vao": "tham_chieu_tep.v1",
      "dau_ra": "van_ban_tai_lieu.v1"
    }
  ],
  "quy_trinh": [
    {
      "ma": "nhan_dang_demo",
      "phien_ban": "1",
      "tep": "quy_trinh/nhan_dang_demo.v1.json"
    }
  ],
  "cong_bo": [
    {
      "ma": "ghi_chu",
      "phien_ban": "1",
      "ham": "ghi_chu_v1",
      "schema": "contract/cong_bo_ghi_chu.v1.schema.json",
      "truong": ["tai_lieu_id", "row_version"],
      "quyen_doc": "mau_demo.ghi_chu.doc"
    }
  ],
  "su_kien": {
    "phat": [
      {
        "loai": "mau_demo.ghi_chu_doi",
        "phien_ban": 1,
        "tham_chieu": ["ghi_chu_id", "tai_lieu_id"]
      }
    ],
    "nhan": [
      {
        "loai": "tai_lieu.cap_nhat",
        "phien_ban": 1,
        "xu_ly": "danh_dau_can_lam_moi"
      }
    ]
  },
  "tien_trinh": {
    "cong": {
      "nguon": "core_cap",
      "pham_vi": "loopback"
    },
    "nhan_listener": "socket.fromshare",
    "readiness": "kenh_dieu_khien",
    "thu_hoi": "drain_va_xac_nhan",
    "bi_mat": "stdin_hoac_handle",
    "che_do_mac_dinh": "tu_kich_hoat_tu_dong",
    "ranh_giay_de_xuat": 300
  },
  "cong_tac": {
    "mac_dinh": "TAT"
  }
}
```

**[Core] [Module]** Quy tắc kiểm manifest:

- Core ghép route dưới `/api/v1/module/mau_demo/`; từng method/path phải đăng ký, không nhận wildcard.
- `tong_quan` và danh sách dùng cùng bộ lọc quyền để số/thẻ khớp chi tiết.
- Core tự suy schema `mod_<ma>`, công bố `cong_bo_<ma>`, owner và runtime role.
- Gói không khai `du_lieu_rieng.schema`, `goi_migration.vai`, `cong_bo[].doi_tuong` hoặc số cổng.
- `v2_ghi_chung` là mã cửa ghi Core trong registry, không phải quyền SQL tự tạo.
- Mã quyền module có tiền tố `<ma>.`; quyền Core vẫn được kiểm/cấp riêng.
- `ham_core_goi` đăng ký qua `loi.dang_ky_ham_module`, đúng owner, chữ ký, hash và policy; chỉ cổng Core nội bộ được EXECUTE.
- Core không SELECT bảng riêng để thay resolver. Chưa có resolver/contract cần thiết trả `CHO`, không commit dở.
- Kiểm kê chứa đường dẫn, phiên bản và SHA-256 thực; bytes phải khớp.
- Schema, workflow, handler, asset và mọi `$ref` phải tồn tại, giải được và tương thích.
- Tệp sau resolve phải nằm trong gói; chặn đường dẫn thoát, absolute/UNC và symlink thoát gói.
- Không chạy mã gói khi đọc manifest; không tự cài dependency vào môi trường Core.

### 3.9. Engine manifest mẫu

**[Engine]**

Mẫu adapter OCR DEMO dưới đây giữ cấu trúc đặc tả. Các ngưỡng tài nguyên là giá trị đề xuất DEMO, không phải ngưỡng chung đã đo.

```json
{
  "phien_ban_manifest": 1,
  "loai": "engine",
  "ma": "e_ocr_demo",
  "ten": "Nhận dạng văn bản DEMO",
  "phien_ban": "0.1.0-demo.1",
  "tuong_thich": {
    "core": ">=1.0.0 <2.0.0",
    "api": "v1"
  },
  "adapter": {
    "ma": "bo_thich_ung_ocr_demo",
    "phien_ban": "1"
  },
  "capability": [
    {
      "ma": "ocr.trich_van_ban@1",
      "dau_vao": "tham_chieu_tep.v1",
      "dau_ra": "van_ban_tai_lieu.v1",
      "mime": [
        "application/pdf",
        "image/png",
        "image/jpeg"
      ],
      "tep_toi_da_mib": 20,
      "trang_toi_da": 60,
      "thoi_han_giay": 900
    }
  ],
  "ho_so_chay_mau": {
    "ma_moi_truong": "ocr_cuc_bo",
    "diem_vao": "bo_thich_ung_ocr_demo.chay",
    "headless": true,
    "cong": {
      "nguon": "core_cap",
      "pham_vi": "loopback"
    },
    "nhan_listener": [
      "socket.fromshare",
      "tham_so_cong"
    ],
    "tham_so_cong": "--port",
    "bi_mat": "stdin_hoac_handle",
    "login_csdl": false,
    "che_do_mac_dinh": "tu_kich_hoat_tu_dong",
    "ranh_giay_de_xuat": 300
  },
  "readiness": {
    "kenh": "dieu_khien_noi_bo",
    "kiem": [
      "instance",
      "phien_ban",
      "capability",
      "model_san_sang"
    ],
    "thoi_han_giay": 120
  },
  "tai_nguyen": {
    "so_viec_dong_thoi": 1,
    "ram_toi_da_mib_de_xuat": 2048,
    "cpu_phan_tram_toi_da_de_xuat": 50
  },
  "ket_noi_ngoai": [],
  "ban_giao_ket_qua": "core_xac_nhan_truoc_giai_phong",
  "thu_hoi": "drain_va_xac_nhan"
}
```

Manifest công bố năng lực; hồ sơ triển khai thực do Core lưu riêng: máy chạy, executable, thư mục làm việc, đối số đã duyệt, tham chiếu bí mật và giới hạn đã áp dụng. Không đóng gói đường dẫn Python cố định hoặc khóa engine.

`ket_noi_ngoai` mặc định rỗng. Kết nối ngoài chỉ dùng mã dịch vụ Core và mục đích đã được Admin duyệt; không nhận URL/credential tùy ý. Allowlist không cho phép gọi AI ngoài cổng chung.

Mẫu OCR không áp thay ngoại lệ đã duyệt cho Mask, ABBYY hoặc tải hóa đơn tại §3.6–§3.7.

### 3.10. Lớp dữ liệu giao tiếp `contract/`

#### 3.10.1. JSON hai lớp

**[Core] [Module] [Engine]**

JSON là dữ liệu trao đổi; JSON Schema mô tả cấu trúc để kiểm tự động. Hai lớp là hai lớp trách nhiệm, không bắt buộc bọc JSON thành hai object mới.

| Lớp | Chủ định nghĩa | Nội dung |
|---|---|---|
| Kỹ thuật | Core | Tệp, văn bản tài liệu, bảng, tham số, nội dung đã che, trả lời AI, hóa đơn đọc từ XML, lỗi và việc. |
| Nghiệp vụ | Module sở hữu, Anh duyệt | Ý nghĩa nghiệp vụ, grain, khóa dòng, điều kiện công bố, bất biến và ngoại lệ. |

Chín contract kỹ thuật, phiên bản đầu `1.0.0`:

```text
tham_chieu_tep.v1
van_ban_tai_lieu.v1
du_lieu_bang.v1
tham_so.v1
noi_dung_da_che.v1
tra_loi_ai.v1
hoa_don.v1
loi_chuan.v1
viec.v1
```

`urn:ktt:contract:chung.v1` cung cấp kiểu và vỏ dùng chung, không phải contract nghiệp vụ bổ sung. `hoa_don.v1` là kết quả kỹ thuật đọc XML, không thay contract nghiệp vụ `hoa_don_mua_vao.v1`.

**[Module]** `module.json.contract` phải có đủ bốn nhóm:

```text
cong_bo
su_kien_phat
su_kien_nhan
dau_vao_nguon
```

Nhóm không dùng ghi mảng rỗng; không bỏ nhóm hoặc bỏ thư mục `contract/`.

Mỗi mục gồm mô tả, JSON Schema, ví dụ DEMO, mã và phiên bản. Contract nguồn nhận từ bên khác phải ghim bản đã đăng ký, không khai lại quyền sở hữu.

#### 3.10.2. Khuôn một contract nghiệp vụ

**[Module]**

| Thành phần | Nội dung phải có |
|---|---|
| Mã và phiên bản | Mã contract, `$id` schema, phiên bản cấu trúc; phân biệt revision nội dung. |
| Mục đích | Dùng dữ liệu để làm gì; điều kiện nào chưa được dùng. |
| Sở hữu | Module chịu trách nhiệm nghiệp vụ và công bố. |
| Bên sử dụng | Module được đọc theo phạm vi đã duyệt; đăng ký không tự cấp quyền. |
| Loại | Công bố, sự kiện phát/nhận hoặc đầu vào nguồn. |
| Grain và khóa | Một dòng là gì; khóa ổn định, khóa phiên bản và khóa dòng con. |
| Bảng trường | Tên, nghĩa, kiểu, bắt buộc/tùy chọn, nullable, đơn vị và nguồn trong thiết kế đã chốt. |
| Bất biến | Tổng tiền, đơn vị, phiên bản, tham chiếu, điều kiện công bố và xử lý thiếu căn cứ. |
| Schema | Draft 2020-12; dùng lại kiểu chung, ghim `$ref` chính xác. |
| Ví dụ | JSON DEMO đầy đủ theo schema và bất biến nghiệp vụ. |
| Trạng thái | Nháp, đã duyệt, đang dùng hoặc ngừng; ghi rõ phần còn chờ. |

Mọi dữ liệu công bố kế thừa `chung.v1#/$defs/vo_noi_dung`:

```text
contract
phien_ban
revision
nguon_tep_ids
```

`nguon_tep_ids` có ít nhất một UUID, không trùng, không `null`.

Nhập tay không có tệp gốc phải lưu ảnh chụp đầu vào qua kho tệp Core rồi dùng `tep_id` thật. Ảnh chụp ghi dữ liệu, người nhập, thời điểm, revision và nguồn `NHAP_TAY`; không chứa ID/hash của chính tệp hoặc hash kết quả gây vòng băm. Chưa lưu được thì trả `CHO`, chưa công bố.

Sự kiện dùng vỏ bus, không áp vỏ nội dung công bố cho payload bus.

#### 3.10.3. Từ điển trường, phiên bản và kiểm schema

**[Core] [Module]**

- Dùng lại trước; cùng nghĩa thiếu trường thì chủ contract đề xuất mở rộng; chỉ tạo mới khi có nghiệp vụ/grain khác được giải thích.
- Cùng tên trường phải cùng kiểu, nullable và đơn vị. Điều kiện bắt buộc có giá trị ghi riêng, không đổi kiểu theo module.
- Bắt buộc có khóa và cho phép `null` là hai điều khác nhau.
- Tên mới dùng tiếng Việt không dấu, `snake_case`; giữ tên kỹ thuật đã chuẩn hóa.
- Dùng lại `doi_tuong.v1`, `du_an.v1`, kiểu chung, tệp và lỗi; không sao chép thành kiểu riêng.
- Ghim ID phiên bản và hash căn cứ khi tham chiếu chéo module; kiểm cùng pháp nhân qua mặt công bố.
- Không lấy bản mới nhất ngầm hoặc đọc bảng riêng để giải tham chiếu.

Một số nghĩa dùng chung:

| Trường | Quy tắc |
|---|---|
| `phap_nhan_id` | UUID không `null`, được Core xác minh. |
| `hop_dong_id` | Dùng kiểu nullable thống nhất; phải khác `null` khi công bố hợp đồng/nghĩa vụ. |
| `so_hop_dong` | Chiếu danh mục hợp đồng qua V3; CRM/M4 không tự sở hữu lại. |
| `doi_tuong_id`, `du_an_id` | Tham chiếu danh mục; trên hợp đồng chiếu từ danh mục hợp đồng. |
| `thue_suat` | Chuỗi theo catalog ghim; phân biệt `0`, `KCT`, `KKKNT`, không ép về cùng nghĩa. |
| `ty_le` | Chuỗi decimal, đơn vị %, theo giá bán trước VAT trong lịch CRM. |
| Tiền | Chuỗi decimal kèm `don_vi_tien`; không trộn tiền tệ khi cộng. |

Kiểm schema:

1. Meta-schema draft 2020-12.
2. `$id` duy nhất; mọi `$ref` giải offline.
3. Bật kiểm `uuid`, `date`, `date-time`.
4. Chặn khóa JSON trùng, trường ngoài schema, sai kiểu và giá trị không hợp lệ.
5. Kiểm đầu vào trước tác động, đầu ra trước lưu/trả/công bố.
6. Kiểm thêm quyền, nguồn và bất biến nghiệp vụ; schema hợp lệ chưa chứng minh các điều này.

Mọi thay đổi schema đã phát hành, kể cả thêm trường tùy chọn, tạo `$id` và phiên bản mới. Không sửa schema dưới cùng `$id`.

- Mã không kèm `:<semver>` chỉ bản đầu `1.0.0`, không nghĩa là bản mới nhất.
- Từ bản thứ hai, manifest/lần chạy ghi đủ `<ten>.v<major>:<semver>`.
- URN tài nguyên mới theo `urn:ktt:contract:<ten>.v<major>:<semver>`.
- Giữ bản cũ cho module đang dùng; không tự chuyển consumer sang bản mới.

#### 3.10.4. Sổ contract và phê duyệt

**[Core]**

Khi cài/nâng cấp, kiểm và đăng ký contract vào `loi.dang_ky_contract`, không sửa code Core theo từng module mới. Admin xem sổ trên màn quản trị.

Sổ theo dõi mã, phiên bản, chủ sở hữu, module sử dụng và trạng thái. Route quản trị sổ contract được bổ sung khi mở G2; chuẩn này không đặt endpoint mới.

**[Module]**

- Tra sổ trước khi thiết kế.
- Xuất danh mục contract dạng bảng để duyệt.
- Contract nghiệp vụ mới hoặc phiên bản mới của contract đang dùng phải được Anh duyệt trước kích hoạt.
- Giữ bản cũ còn được dùng; cảnh báo module ghim bản sắp ngừng.

Các trường hợp **đỏ**:

- Contract mới trùng nghĩa contract đã có, kể cả đổi tên/mã.
- Hai chủ nhận sở hữu cùng grain và khóa.
- Cùng tên trường khác kiểu hoặc đơn vị.
- Module đọc dữ liệu module khác ngoài contract đã đăng ký và cấp quyền.
- Thiếu/không hợp lệ `contract/`, bản nguồn không khớp sổ hoặc ví dụ sai schema.

Chưa kết luận được đối chiếu nghĩa thì ghi `CHUA_KIEM`, không tự cho qua.

### 3.11. Bất biến tiền và VAT cọc

**[Module] [Engine]**

- Tiền chuẩn tối đa 18 chữ số phần nguyên, 6 chữ số thập phân; không dùng JSON number hoặc float.
- Decimal nguồn XML giữ riêng; không tự làm tròn để ép vào miền tiền chuẩn.
- `null`, thiếu, chuỗi rỗng, chưa đọc được và `0` khác nghĩa.
- Không suy đơn vị tiền, thuế suất, tỷ giá hoặc đơn vị đo từ giao diện.
- Chưa rõ căn cứ phải giữ chưa rõ/`CHO`, không bỏ dòng lỗi để tổng vẫn khớp.

Đối với lịch giá bán CRM:

```text
tong_truoc_vat + tong_vat = tong_gom_vat
Σ ty_le của GIA_BAN = 100%
Σ gia_tri_gom_vat của GIA_BAN = tong_gom_vat
Σ trong_do_vat của GIA_BAN = tong_vat
```

Tiền/VAT không âm, VAT không vượt tiền đợt, cùng đơn vị tiền.

**Phạm vi bản đầu — SDK câu 1A:** lịch nghĩa vụ chỉ gồm **giá bán chia %**. Phí theo dõi riêng; không cộng phí vào tổng/% giá bán và không tự sinh nghĩa vụ phí.

**VAT cọc — SDK câu 2B:**

1. Cho phép cọc ở đợt cuối hoặc nhiều đợt cọc.
2. Đợt cọc không thu VAT tại chính đợt đó.
3. VAT từng đợt cọc dồn vào đợt **không cọc gần nhất phía sau**.
4. Nếu không còn đợt không cọc phía sau, dồn ngược về đợt **không cọc gần nhất phía trước**.
5. Lịch toàn đợt cọc báo lỗi.
6. Không giả định cọc là dòng đầu.

Tỷ lệ tính trên giá bán trước VAT. `gia_tri_nhap` giữ giá trị người dùng nhập; không suy tỷ lệ bằng cách chia tiền đợt cho tổng gồm VAT.

Tiền tính CRM VND làm tròn đến đồng, USD đến cent, half-up; chỉ làm tròn tại kết quả tiền, phần dư theo quy tắc đợt cuối đã nêu trong đặc tả. Không tự đặt thêm thuật toán suy ngược hoặc phân bổ ngoài quy tắc đã chốt.

Khi chuyển báo giá sang Soạn hợp đồng phải giữ lịch, đánh dấu cọc và kết quả VAT của revision được chọn. ID dòng báo giá là dự kiến, chưa phải đích nối tiền của nghĩa vụ hiệu lực.

### 3.12. Ví dụ contract nghiệp vụ — `bao_gia.v1`

Ví dụ dùng lại contract CRM; `mau_demo` không sở hữu lại contract này.

**Mục đích:** Công bố một revision báo giá gồm giá, thuế, phí theo dõi riêng và lịch dự kiến.

**Sở hữu:** CRM.  
**Bên đọc:** CRM; module ngoài CRM còn chờ Anh xác định và cấp quyền.  
**Loại:** Dữ liệu công bố.  
**Grain:** Một revision báo giá; khóa `(bao_gia_id, revision)`.  
**Dòng con:** `nghia_vu_id` dự kiến, chưa là nghĩa vụ hiệu lực.  
**Nguồn cấu trúc:** `docs\47-core\g1\CONTRACT-NGHIEP-VU.md`, NV-CRM §1–§2; VAT cọc áp dụng CD-038.

Bảng trường rút gọn:

| Trường | Nghĩa và kiểu | Yêu cầu | Đơn vị/nguồn |
|---|---|---|---|
| `contract`, `phien_ban` | Hằng `bao_gia.v1`, `1.0.0` | Bắt buộc | Vỏ chung và contract CRM. |
| `revision`, `nguon_tep_ids` | Revision; mảng UUID nguồn | Bắt buộc | Vỏ chung; ít nhất một tệp. |
| `bao_gia_id`, `phap_nhan_id` | UUID báo giá, pháp nhân | Bắt buộc | NV-CRM §2; pháp nhân được Core xác minh. |
| `ngay_lap`, `nguoi_lap` | Ngày ISO; chuỗi người lập | Bắt buộc | NV-CRM §2. |
| `doi_tuong_id`, `du_an_id` | UUID hoặc `null` theo điều kiện nháp | Có khóa | Danh mục chung. |
| `loai_hinh_id` | UUID profile loại hình | Bắt buộc | NV-CRM §2. |
| `trang_thai` | Chuỗi catalog CRM | Bắt buộc | Catalog còn chờ chốt; không tự thêm mã. |
| `nguon_lich` | `DU_AN` hoặc `KHACH` | Bắt buộc | NV-CRM §2. |
| `gia_thue` | `GiaCrm`: cơ sở thuế, thuế suất, ba tổng tiền | Bắt buộc | NV-CRM §1; tiền kèm đơn vị. |
| `phi` | Mảng `PhiCrm`, có thể rỗng | Bắt buộc | Theo dõi riêng, không vào lịch giá bán bản đầu. |
| `lich_thanh_toan` | Mảng `DongLichCrm` | Bắt buộc | NV-CRM §1; CD-038. |
| Dòng lịch | ID dự kiến, loại khoản, thứ tự, giá trị nhập, %, cọc, tiền/VAT và mốc | Bắt buộc theo nhóm | % trên giá trước VAT; tiền VND/USD. |
| `moc` | `NGAY` hoặc `SU_KIEN`, các trường tương ứng và `han` | Theo điều kiện | Ngày ISO; mốc chưa xảy ra chưa tính quá hạn. |

Các trường có điều kiện như số báo giá khi đã in, lô/căn, phiên bản/hash dự án khi lấy lịch dự án, tỷ giá khi quy đổi và các trường tùy chọn giữ theo đặc tả đầy đủ.

JSON dưới đây rút gọn bằng cách không dùng các trường tùy chọn hoặc nhánh điều kiện không áp dụng; vẫn giữ đủ các trường bắt buộc của nhánh minh họa. `NHAP` là giá trị DEMO kế thừa ví dụ nguồn, không chốt thêm catalog trạng thái.

```json
{
  "contract": "bao_gia.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": [
    "20000000-0000-4000-8000-000000000008"
  ],
  "bao_gia_id": "20000000-0000-4000-8000-000000000001",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000002",
  "ngay_lap": "2026-10-30",
  "nguoi_lap": "DEMO_BAN_HANG",
  "doi_tuong_id": "10000000-0000-4000-8000-000000000003",
  "du_an_id": "10000000-0000-4000-8000-000000000004",
  "loai_hinh_id": "10000000-0000-4000-8000-000000000006",
  "trang_thai": "NHAP",
  "nguon_lich": "KHACH",
  "gia_thue": {
    "co_so_thue": "NET",
    "thue_suat": "10",
    "tong_truoc_vat": {
      "gia_tri": "1000000000",
      "don_vi_tien": "VND"
    },
    "tong_vat": {
      "gia_tri": "100000000",
      "don_vi_tien": "VND"
    },
    "tong_gom_vat": {
      "gia_tri": "1100000000",
      "don_vi_tien": "VND"
    }
  },
  "phi": [],
  "lich_thanh_toan": [
    {
      "nghia_vu_id": "20000000-0000-4000-8000-000000000011",
      "loai_khoan": "GIA_BAN",
      "lan": 1,
      "gia_tri_nhap": {
        "kieu": "so",
        "gia_tri": "10",
        "don_vi": "%"
      },
      "ty_le": "10",
      "la_dat_coc": true,
      "gia_tri_gom_vat": {
        "gia_tri": "100000000",
        "don_vi_tien": "VND"
      },
      "trong_do_vat": {
        "gia_tri": "0",
        "don_vi_tien": "VND"
      },
      "moc": {
        "loai": "NGAY",
        "ngay": "2026-10-30",
        "han": "2026-10-30"
      }
    },
    {
      "nghia_vu_id": "20000000-0000-4000-8000-000000000012",
      "loai_khoan": "GIA_BAN",
      "lan": 2,
      "gia_tri_nhap": {
        "kieu": "so",
        "gia_tri": "80",
        "don_vi": "%"
      },
      "ty_le": "80",
      "la_dat_coc": false,
      "gia_tri_gom_vat": {
        "gia_tri": "900000000",
        "don_vi_tien": "VND"
      },
      "trong_do_vat": {
        "gia_tri": "100000000",
        "don_vi_tien": "VND"
      },
      "moc": {
        "loai": "NGAY",
        "ngay": "2026-12-01",
        "han": "2026-12-01"
      }
    },
    {
      "nghia_vu_id": "20000000-0000-4000-8000-000000000013",
      "loai_khoan": "GIA_BAN",
      "lan": 3,
      "gia_tri_nhap": {
        "kieu": "so",
        "gia_tri": "10",
        "don_vi": "%"
      },
      "ty_le": "10",
      "la_dat_coc": true,
      "gia_tri_gom_vat": {
        "gia_tri": "100000000",
        "don_vi_tien": "VND"
      },
      "trong_do_vat": {
        "gia_tri": "0",
        "don_vi_tien": "VND"
      },
      "moc": {
        "loai": "NGAY",
        "ngay": "2027-03-01",
        "han": "2027-03-01"
      }
    }
  ]
}
```

Kiểm tiền của ví dụ:

| Đợt | Giá trước VAT theo % | VAT thực thu | Tiền trả |
|---|---:|---:|---:|
| 1 — cọc 10% | 100.000.000 | 0 | 100.000.000 |
| 2 — không cọc 80% | 800.000.000 | 100.000.000 | 900.000.000 |
| 3 — cọc cuối 10% | 100.000.000 | 0 | 100.000.000 |
| **Tổng VND** | **1.000.000.000** | **100.000.000** | **1.100.000.000** |

VAT đợt 1 là 10.000.000 VND dồn về đợt 2 phía sau. VAT đợt 3 là 10.000.000 VND dồn ngược về đợt 2 phía trước. Đợt 2 thu VAT của chính nó 80.000.000 VND cộng hai khoản dồn.

Nếu đổi cả ba đợt thành cọc, lịch phải báo lỗi. Bộ kiểm phải có thêm ca cọc cuối, hai cọc liền nhau, cọc xen giữa và toàn cọc.

### 3.13. Cài, nâng cấp, tắt và phục hồi

**[Core] [Module] [Engine]**

| Bước | Điều kiện |
|---|---|
| Kiểm gói | Manifest, hash, schema, contract, route, phụ thuộc và capability hợp lệ; không chạy mã khi đọc manifest. |
| Xem trước/cấp quyền | Hiển thị phiên bản, quyền mới, thay đổi dữ liệu và phụ thuộc; Admin cấp quyền thực tế riêng. |
| Migration | Khóa theo module; dùng quyền migration đúng khối; kiểm phiên bản/checksum và ghi sổ. |
| Kích hoạt | Chỉ sau khi dữ liệu/asset chuẩn bị thành công; readiness và bộ kiểm đạt. |
| Nâng cấp | Ngừng nhận việc mới theo phạm vi; ghim phiên bản việc đang chạy; chờ hết việc nếu chưa hỗ trợ runtime cũ. |
| Tắt | Chặn tạo/nhận việc mới; việc đang giữ lease hoàn tất theo quyền hợp lệ; giữ dữ liệu, nguồn, lịch sử và biên nhận. |
| Phục hồi | Migration lỗi không kích hoạt một phần; filesystem dùng staging và bước kích hoạt riêng; quay lại mã cũ chỉ khi tương thích dữ liệu. |

Không rollback bằng xóa schema/bảng. Công tắc `TAT/THU/VAN_HANH` tách khỏi trạng thái tiến trình. `THU` không công bố/xuất chính thức.

## 4. Khuyến nghị

Các mục này không thay điều kiện bắt buộc tại §3 và §6.

- **[Module]** Ưu tiên sửa, bọc và dùng lại chức năng đang chạy; không viết lại phần chung đã được SDK cung cấp.
- **[Engine]** Giữ DTO, kiểm kiểu, bằng chứng và test gốc; bổ sung adapter tại biên trao đổi thay vì thay toàn bộ thuật toán.
- **[Module]** Khi nâng cấp dữ liệu, ưu tiên mở rộng tương thích, đối chiếu rồi chuyển truy cập.
- **[Core]** Dùng lại nền hàng việc, bus, audit, MTQ và kiểm hiện có trong bộ kiểm chung; không tạo hệ tương đương.
- **[Module]** Tận dụng cách giữ nháp, thế hệ ngữ cảnh và khóa ghi của giao diện hiện có khi chuyển sang SDK JS chuẩn.

## 5. Được / không được làm

| Trách nhiệm | Được làm | Không được làm |
|---|---|---|
| [Module] Dịch vụ chung | Gọi SDK theo quyền đã cấp. | Tự dựng lại đăng nhập, kho tệp, OCR, mã hóa hoặc điều phối chung; gọi thẳng máy AI hoặc API Cloud (AI chỉ qua capability `ai.hoi@1`). |
| [Module] Dữ liệu riêng | Ghi V1, gọi V2, đọc V3/V4 đã cấp. | SQL chéo bảng riêng, DML bảng chung hoặc dùng GRANT tay để vượt contract. |
| [Module] Contract | Dùng lại hoặc đề xuất bản mới theo quy trình duyệt. | Tạo contract trùng nghĩa, sửa schema dưới `$id` đã phát hành hoặc tự kích hoạt bản chưa duyệt. |
| [Module] Transaction | Ghi nghiệp vụ, biên nhận, việc/bus trên cùng `tx` khi cần nguyên tử. | Tạo việc qua HTTP rồi ghi biên nhận riêng nhưng coi là cùng transaction. |
| [Module] Giao diện | Gọi Core cùng nguồn, giữ khóa và nháp. | Gọi host/cổng engine trực tiếp, tự đổi pháp nhân khi retry hoặc dùng float cho tiền. |
| [Module] [Engine] Vận hành | Nhận listener/cổng, credential và ủy nhiệm từ Core. | Tự chọn cổng, dò cổng thay thế, dừng tiến trình lạ hoặc nhận bí mật qua môi trường. |
| [Engine] Việc và tệp | Nhận việc, đọc tệp và bàn giao kết quả qua Core. | Nhận login CSDL hoặc tự gọi SQL hàng việc. |
| [Engine] AI | Qua cổng AI chung; Cloud qua Mask v2. | Gọi thẳng API/máy AI hoặc thêm cổng/bộ che riêng. |
| [Engine] Bí mật | Dùng tài khoản riêng từng engine giữ bí mật và nhận bí mật đúng phạm vi. | Đọc két Core, khóa DPAPI hoặc bộ nhớ Core. |
| [Core] Quyền và nguồn | Xác minh quyền hiện tại, lease, schema và provenance. | Tin actor/header/GUC, nguồn OCR hoặc trạng thái duyệt do caller tự khai. |
| [Core] Chế độ chạy | Đánh thức thành phần được phép hoạt động; Admin áp dụng đổi chế độ. | Tự bật module Anh đã tắt hoặc tự đổi sang luôn chạy. |
| [Module] [Engine] Kiểm thử | Dùng DEMO, cổng giả và môi trường thử được giao. | Dùng dữ liệu thật hoặc dịch vụ ngoài để thay kiểm tuân thủ. |

## 6. Bộ kiểm tuân thủ

### 6.1. Thời điểm và kết quả

**[Core] [Module] [Engine]**

Bộ kiểm chung chọn kiểm theo loại gói và capability, dùng lại regression test hiện có.

Chạy khi cài, mỗi lần kích hoạt và mỗi lần Core khởi động. Đặc biệt KT01/KT03 phải đối chiếu catalog và quyền hiệu lực; thay owner, policy, membership hoặc GRANT tay vượt quyền làm thành phần về chưa kích hoạt, không phục vụ.

Mỗi kết quả gồm mã kiểm, đối tượng/phiên bản, mức chặn, bằng chứng an toàn và một trong:

```text
DAT / KHONG_DAT / CHUA_KIEM / KHONG_AP_DUNG
```

`KHONG_AP_DUNG` phải phù hợp loại gói và manifest. Thiếu môi trường hoặc bị skip là `CHUA_KIEM`, không tính đạt.

### 6.2. Mức chặn phát hành

| Mức | Ý nghĩa |
|---|---|
| `C0` | Chặn cài/kích hoạt/phát hành khi vi phạm an toàn dữ liệu, quyền, bí mật hoặc toàn vẹn; lỗi nền không được dùng để miễn. |
| `C1` | Chặn phát hành thành phần/capability liên quan khi sai contract, giao thức hoặc vận hành bắt buộc; `CHUA_KIEM` chưa đủ điều kiện phát hành. |
| `C2` | Cảnh báo có căn cứ cho chỉ tiêu chưa có ngưỡng nghiệm thu; không hạ kiểm bắt buộc xuống C2. |

Capability chưa đạt không được đăng ký để chạy dựa trên cảnh báo.

### 6.3. Danh sách KT

| Mã | Nội dung phải kiểm | Mức |
|---|---|---|
| **KT01** | Đúng khối/chủ dữ liệu; catalog thực gồm bảng, sequence, view, hàm, trigger, policy, FK và owner khớp gói. | C0 |
| **KT02** | Không SQL chéo trái phép; kiểm quyền hiệu lực, phụ thuộc và trace runtime, kể cả SQL động hoặc bỏ qua SDK. | C0 |
| **KT03** | Quyền thực tế khớp khai báo và quyền đã cấp; tính cả PUBLIC, kế thừa, `SET ROLE`, cột, sequence, default privileges và DEFINER. | C0 |
| **KT04** | Danh tính, pháp nhân, MTQ và ủy nhiệm; giả actor/header/GUC, sai/hết hạn mã, tái sử dụng kết nối, thu hồi quyền giữa việc. | C0 |
| **KT05** | Route/OpenAPI/manifest; method, operation, schema, CSRF, lỗi, 202, CAS, chống trùng; token loopback, nonce và biên nhận bền vững. | C0 cho vượt quyền, route quản trị và biên nhận; C1 cho sai giao thức |
| **KT06** | Meta-schema 2020-12, `$id`, `$ref` offline, format, ví dụ, đầu vào/ra, ca âm; trùng nghĩa contract. | C1; C0 nếu lọt dữ liệu cấm hoặc sai tiền |
| **KT07** | Manifest module và engine; tham chiếu, tương thích, quyền, workflow, cột nhóm A, đường dẫn, dependency, `contract/`; không credential hoặc tự chọn role/schema/cổng. | C1; C0 cho bí mật hoặc thoát phạm vi gói |
| **KT08** | Cấp/giữ/chuyển giao listener, readiness thực, instance/process/version, đồng thời, crash, cổng bị chiếm và tài khoản hạn chế. | C1; C0 nếu gọi nhầm, chiếm cổng hoặc xử lý tiến trình lạ |
| **KT09** | Bí mật DEMO không rò qua stdout/stderr, log, audit, trace, metric, HTTP hoặc báo cáo; gồm lỗi SQL và log PostgreSQL. | C0 |
| **KT10** | Engine không login CSDL; AI/OCR đúng cổng; Cloud qua Mask v2; cách ly két, DPAPI, bộ nhớ và handle Core. | C0 |
| **KT11** | Hàng việc bền vững; hai worker, lease hết, token cũ, heartbeat, mất kết nối, CAS và rollback; giữ `CHUA_RO`. | C0 |
| **KT12** | Bus và transaction; kết quả/ACK cùng commit, rollback, giao lại không nhân tác động, payload chỉ tham chiếu. | C0 |
| **KT13** | `TAT/THU/VAN_HANH`, pháp nhân/người thử; tắt giữ dữ liệu, THU không xuất chính thức; MTQ vẫn độc lập. | C0 |
| **KT14** | Duyệt, revision, nguồn và provenance; consumer ghim đúng bản, không dùng mới nhất ngầm hoặc giả nguồn OCR. | C0 |
| **KT15** | Cài/nâng cấp/tắt; migration trước kích hoạt, không kích hoạt một phần, giữ dữ liệu/bản contract cũ, contract mới có Anh duyệt. | C1; C0 nếu sai quyền hoặc mất dữ liệu |
| **KT16** | Số đo khởi động/chạy/rảnh, RAM/CPU từ Job; đánh thức một instance; đề xuất chế độ và Admin áp dụng. | C1 cho thiếu phần bắt buộc; C0 nếu vượt quyền/tự đổi; C2 cho ngưỡng hiệu năng chưa chốt |

Các ca bổ sung phải giữ:

- Biên nhận module: rollback, crash sau commit trước response, restart, replay sau 24 giờ, alias cũ/v1 và kiểm quyền hiện tại.
- Request nội bộ: sai chữ ký/instance, TTL trên 30 giây, hash lệch, nonce lặp đồng thời.
- Từ chính tài khoản module/engine: đọc két, giải DPAPI, đọc/ghi bộ nhớ Core, duplicate handle/token hoặc sửa ACL đều thất bại.
- PostgreSQL thử: `log_parameter_max_length=0`, `log_parameter_max_length_on_error=0`; không rò mã ủy nhiệm.
- Cổng mã hóa: sai pháp nhân/cột, quyền xem đủ, audit, đổi khóa, phục hồi và canary log.
- Contract: trùng nghĩa dù khác tên; cùng tên khác kiểu; thiếu `contract/`; thiếu duyệt; nâng cấp làm mất bản còn dùng.
- Đánh thức khi có việc/sự kiện; `TAT` không tự bật; chưa bàn giao kết quả hoặc còn lượt Mask thì chưa rảnh.
- VAT cọc: cọc cuối, hai cọc liền nhau, cọc xen giữa, toàn cọc và các tổng tiền.
- Engine trích xuất: so độ chính xác trước/sau trên bộ đáp án 37 tham số theo §3.7.
- Mask: không tự đóng khi danh mục đang mở; engine giữ bí mật tách tài khoản theo CD-038.

### 6.4. Trình tự và điều kiện đạt

1. Kiểm tĩnh gói, manifest, schema, tham chiếu, route, quyền và bí mật.
2. Kiểm thuần/adapter bằng DEMO và cổng giả.
3. Kiểm PostgreSQL thử: ACL, role, RLS, phiên, transaction, hàng việc, bus và công tắc.
4. Kiểm tiến trình local: socket, readiness, đồng thời, restart, dừng và nhánh engine cũ.
5. Chạy regression liên quan và đối chiếu nền.

Không tạo CSDL hoặc role theo mỗi test; dùng môi trường thử được quản lý. Không dùng dữ liệu thật hoặc dịch vụ ngoài.

Điều kiện đạt:

- Không còn `KHONG_DAT` hoặc `CHUA_KIEM` ở kiểm C0/C1 áp dụng.
- Mọi capability công bố có schema, ví dụ, ca âm và bằng chứng chạy adapter.
- Quyền hiệu lực không vượt quyền được cấp.
- Các kiểm tiền, nguồn, danh tính, bí mật và chống trùng đều đạt.
- Không thêm lỗi regression so với `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md`.

## 7. Checklist trước khi nộp gói

### 7.1. Gói, manifest và contract

- [ ] [Module] Có `module.json`, `contract/` và mọi tệp được tham chiếu.
- [ ] [Module] Có đủ bốn nhóm contract; nhóm không dùng là mảng rỗng.
- [ ] [Module] Mỗi contract có mục đích, chủ, bên dùng, grain, khóa, bảng trường, nguồn, schema, ví dụ và phiên bản.
- [ ] [Module] Đã tra sổ; không trùng nghĩa hoặc cùng tên khác kiểu/đơn vị.
- [ ] [Module] Contract nguồn khớp bản đăng ký, không nhận lại quyền sở hữu.
- [ ] [Module] Contract mới/bản mới đang dùng có Anh duyệt trước kích hoạt.
- [ ] [Module] Giữ bản cũ còn dùng; không sửa schema dưới `$id` đã phát hành.
- [ ] [Module] [Engine] Manifest đúng schema, `$ref` giải offline, hash khớp bytes; không đường dẫn thoát gói.
- [ ] [Module] Không tự khai schema, role, đối tượng công bố hoặc số cổng.
- [ ] [Module] Không tự cài dependency vào Core.

### 7.2. Dữ liệu, API và giao diện

- [ ] [Module] AI chỉ qua cổng AI chung (Cloud qua Mask v2).

- [ ] [Module] V1–V4, quyền yêu cầu và quyền được cấp khớp nhau.
- [ ] [Module] Route nằm đúng namespace, có method/operation/OpenAPI và schema.
- [ ] [Module] Biên nhận, nghiệp vụ và tạo việc/bus nguyên tử trên cùng `tx` khi cần.
- [ ] [Module] Đã thử chống trùng, CAS, mất mạng, crash và replay.
- [ ] [Module] Tiền/tỷ lệ dùng decimal; ngày kiểm lịch; không điền 0 khi thiếu.
- [ ] [Module] Lỗi tiếng Việt, mã/HTTP/trường đã đăng ký; giữ nháp và `request_id`.
- [ ] [Module] Theo dõi 202, `waiting_input`, hủy và `interrupted` đúng nghĩa.
- [ ] [Module] Công bố có vỏ, nguồn thật trong môi trường chạy, revision và hash căn cứ.
- [ ] [Module] [Engine] Nếu tính lịch CRM: giá bán đủ 100%, phí riêng, VAT cọc đúng 2B và toàn cọc báo lỗi.

### 7.3. Tiến trình, engine và bí mật

- [ ] [Module] [Engine] Credential SDK theo instance; bị thu hồi khi dừng/crash.

- [ ] [Module] [Engine] Nhận cổng từ Core, readiness thực trước phục vụ.
- [ ] [Module] Runtime không migrate; phiên bản dữ liệu/checksum khớp.
- [ ] [Module] [Engine] Drain, heartbeat, bàn giao kết quả và xác nhận dừng đúng.
- [ ] [Core] Đánh thức đúng một instance khi có việc/sự kiện; không tự bật `TAT`.
- [ ] [Core] RAM/CPU lấy từ Job accounting; có số đo khởi động và rảnh.
- [ ] [Module] [Engine] Chạy tài khoản hạn chế khác Core; kiểm két/DPAPI/bộ nhớ/handle đều bị chặn.
- [ ] [Engine] Engine giữ bí mật có tài khoản riêng từng engine.
- [ ] [Module] [Engine] Bí mật qua stdin/handle; không trong môi trường, dòng lệnh, manifest, DSN hoặc log.
- [ ] [Engine] Không login CSDL; nhận việc/tệp và bàn giao kết quả qua Core.
- [ ] [Engine] AI đúng cổng, Cloud qua Mask v2.
- [ ] [Engine] Mask không tự đóng khi danh mục mở.
- [ ] [Engine] Tải hóa đơn dùng phiên Windows có màn hình, hồ sơ theo pháp nhân và dọn sau phiên.
- [ ] [Engine] Trích xuất đạt độ chính xác không thấp hơn bản gốc; ghi rõ test đổi và lý do.

### 7.4. Kiểm và báo cáo

- [ ] [Module] [Engine] Dữ liệu test là DEMO; không đọc kho thật, không gọi dịch vụ ngoài.
- [ ] [Module] [Engine] KT áp dụng C0/C1 đều `DAT`; không tính skip là đạt.
- [ ] [Module] [Engine] Regression không thêm lỗi so với nền.
- [ ] [Module] [Engine] Báo cáo có: đã làm, file đổi, test đạt/tổng, lỗi mới so nền, tự thử và phần còn thiếu/rủi ro.
- [ ] [Module] [Engine] Không mô tả kiểm schema/metadata là bằng chứng đã cách ly runtime.

## 8. Phụ lục — đặc tả và tham chiếu chéo

Các đường dẫn dưới đây tính từ **gốc repo**, dùng để tra schema và chi tiết triển khai. Người áp dụng không cần đọc phiếu hoặc biên bản để hiểu các quy tắc trong chuẩn này.

| Tài liệu | Nội dung tra cứu |
|---|---|
| `docs\47-core\g1\DAC-TA-SDK.md` | §2 quy ước Python/transaction; §3 đủ 12 dịch vụ; §4 tiến trình/tài khoản; §5 SDK JS; §6 manifest; §7 vòng đời gói. |
| `docs\47-core\g1\CONTRACT-DU-LIEU.md` | §2 đăng ký/phiên bản; §3 kiểu chung; §4–§12 chín contract kỹ thuật; §15 hai schema manifest và kiểm ngữ nghĩa. |
| `docs\47-core\g1\CONTRACT-DU-LIEU.md` | Phần `BO-KIEM-TUAN-THU.md` trong cùng tệp: KT01–KT16, ca âm, mức chặn, thứ tự chạy và báo cáo. |
| `docs\47-core\g1\CONTRACT-NGHIEP-VU.md` | Vỏ chung, từ điển trường, grain/khóa, bất biến; contract Chung, CRM, M4, M2; chi tiết `GiaCrm`, `DongLichCrm`, `bao_gia.v1`. |
| `docs\47-core\g1\DAC-TA-CSDL.md` | Khối dữ liệu, role, ACL/RLS, phiên/ủy nhiệm, hàm Core, migration và mã hóa. |
| `docs\47-core\g1\ANH-XA-MIGRATION.md` | Ánh xạ đối tượng/migration cũ sang chủ và gói mới. |
| `docs\47-core\g1\DAC-TA-API.md` | Route, lỗi, xác thực, idempotency, CAS, việc, dispatcher, cổng; Phụ lục `openapi-v1.yaml`. |
| `docs\47-core\g1\ANH-XA-ROUTE.md` | Ánh xạ method/path cũ, chuyển tiếp và điều kiện ngừng alias. |
| `docs\47-core\chuan\CHUAN-CORE-CSDL-v1.0.md` | Chuẩn CSDL dùng cùng SDK: V1–V4, role, RLS, transaction, mã hóa, migration và retention. |
| `docs\47-core\chuan\CHUAN-CORE-API-v1.0.md` | Chuẩn API dùng cùng SDK: namespace, xác thực, lỗi, 202, chống trùng, CAS, tệp và vận hành. |
| `docs\46-chuyen-doi-dieu-phoi\NEN-TEST.md` | Nền đối chiếu regression theo lỗi hiện có. |
| `docs\46-chuyen-doi-dieu-phoi\CHI-DAO-TU-ANH.md` | CD-026–CD-038; CD-038 chốt SDK, VAT cọc và ba câu engine. |

**Các điểm còn chờ, không tự quyết định:**

- Thuật toán/adapter cổng mã hóa và JSON path nhóm A cụ thể: theo điểm chờ của chuẩn CSDL, cần lead chốt.
- Catalog nghiệp vụ hoặc phạm vi bên đọc còn ghi chờ trong contract: chưa tự mở rộng hoặc kích hoạt phần đó.
- Các phần thiết kế nghiệp vụ M2 chưa chốt vẫn giữ trạng thái chờ; duyệt SDK không tự hoàn tất thiết kế M2.
- Tên/chữ ký hàm SQL và cửa Core nội bộ chưa có phải đăng ký theo thiết kế; không suy ra từ tên hàm SDK.
- Route quản trị sổ contract bổ sung khi mở G2; không tự đặt route trong module.
- Ngoại lệ tài khoản/quyền ngoài những trường hợp đã duyệt phải được Anh duyệt trước.
- Chi tiết suy ngược/phân bổ tiền ngoài quy tắc đã chốt không được tự biến thành quy định contract.

Các chỗ lịch sử ghi SDK chưa duyệt, cấm cọc cuối/nhiều cọc hoặc chờ chọn ba câu engine phải đọc theo kết quả CD-038 đã thể hiện trong chuẩn này. Việc mở lại lập trình theo CD-038 gắn với hoàn tất chuẩn SDK và review; bản tài liệu này không tự xác nhận đã hoàn tất review hoặc nghiệm thu runtime.