# Contract nghiệp vụ theo module (lớp nghiệp vụ, CD-031/032) — bản nháp

Ngày 30/10/2026. Codex soạn theo đề `GIAO-G1C-NV.md`; lead ghép. Ví dụ JSON chỉ là dữ liệu DEMO. Trạng thái mọi contract: `nhap`, chờ Anh duyệt.

Thứ tự: 1. Chung + sự kiện + quy tắc chung · 2. CRM · 3. M4 · 4. M2.

---

| Mã contract | Mục đích | Sở hữu | Được đọc |
|---|---|---|---|
| `doi_tuong.v1` | Nhận diện đối tượng và mã Junsky theo pháp nhân | Core — `danh_muc` | Module được cấp quyền danh mục |
| `du_an.v1` | Thống nhất định danh dự án dùng chung | Core — `danh_muc` | Module được cấp quyền danh mục |
| `but_toan_de_xuat.v1` | Trao đổi đề xuất các dòng Nợ/Có để kế toán duyệt | Chủ chuyển tiếp kế toán cũ; chủ đích chờ Anh | Module duyệt/xuất được cấp quyền |
| `tep_nhap_junsky.v1` | Bàn giao tham chiếu tệp Excel đúng hai sheet Junsky | Chủ chuyển tiếp kế toán cũ; chủ đích chờ Anh | Module xuất/đối chiếu được cấp quyền |
| `tien_da_noi_dot.v1` | Báo khoản tiền đã được nối với đợt nghĩa vụ | M1 theo TL 53; đầu mối phát chờ Anh | CRM, M3 — chờ duyệt danh sách |
| `ban_giao_da_duyet.v1` | Báo bàn giao đã được duyệt đúng phạm vi | Chờ Anh phân định bàn giao bán hàng/chuyển giao xây dựng | Chờ Anh chốt theo nghĩa bàn giao |
| `moc_da_xay_ra.v1` | Báo mốc thực tế đã được xác nhận | CRM | CRM, M3 — chờ duyệt danh sách |
| `hop_dong_hieu_luc.v1` | Báo phiên bản hợp đồng bán bắt đầu có hiệu lực | CRM | M1, M3 — chờ duyệt danh sách |
| `hoa_don_da_nhan.v1` | Báo M2 đã lưu quan sát hóa đơn mua vào | M2 | M4, M8 — chờ duyệt danh sách |

## NV-CHUNG — Quy ước đọc phần nháp

**Trạng thái toàn lát: `nhap`, phiên bản dự kiến `1.0.0`.** Đây là nội dung trình duyệt theo CD-031/CD-032, chưa phải contract đã kích hoạt.

**Ký hiệu nguồn:**

- `C`: `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md`.
- `T`: `docs/47-core/g1/CONTRACT-DU-LIEU.md`; `D`: `DAC-TA-CSDL.md`; `S`: `DAC-TA-SDK.md`, cùng thư mục.
- `P`: `src/kho_tri_thuc/ha_tang/pg_migrations.py`.
- `B`: `src/kho_tri_thuc/ha_tang/bus_su_kien.py`; `BS`: `src/kho_tri_thuc/k2/sql_bus_su_kien.py`.
- `M0`: `../THIET-KE-MODULE-DE-CHOT-2026-10-20/M0-NEN-TANG-DUNG-CHUNG.md`.
- `J`: `../Mang ngan hang/bo_quy_tac/HUONG-DAN-TAO-FILE-NHAP-JUNSKY.md`. Đây là tài liệu file nhập tìm thấy tại máy; **chưa xác nhận đồng nhất với tài liệu số 08 trong Project**.

Các tên JSON dưới đây là phép ánh xạ từ nguồn được dẫn; không đổi tên bảng hay khẳng định đã có API tương ứng.

**Kiểu dùng lại:** `id`, `chuoi`, `ma`, `ngay`, `tien` đều tham chiếu `$defs` của `urn:ktt:contract:chung.v1`; tệp dùng `tham_chieu_tep.v1`, lỗi dùng `loi_chuan.v1`. Không định nghĩa lại các kiểu này. Mã Junsky và tài khoản kế toán dùng `chuoi`, giữ nguyên mã nguồn; không ép vào `chung.ma` vì mã ngoài có thể chứa chữ hoa, dấu chấm hoặc số đầu.

Mọi contract **dữ liệu công bố** trong tài liệu (Chung, CRM, M4, M2) kế thừa nguyên vỏ `chung.v1#/$defs/vo_noi_dung` của T §3. Sự kiện giữ vỏ bus ở §5, không áp vỏ nội dung cho payload bus.

| Trường | Nghĩa | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `contract` | Mã contract chính xác | Hằng chuỗi từng contract | Có | — | T §2–3 |
| `phien_ban` | Phiên bản cấu trúc, không phải phiên bản hồ sơ | Hằng `"1.0.0"` của bản nháp | Có | — | T §2–3 |
| `revision` | Revision nội dung được công bố | Kiểu có sẵn trong vỏ chung | Có | Lần | T §3 |
| `nguon_tep_ids` | Các tệp nguồn làm căn cứ | Kiểu có sẵn trong vỏ chung | Có | — | T §2.1, §3 |

Pháp nhân, quyền, nguồn tạo và trạng thái duyệt phải được Core kiểm chứng; các giá trị trong JSON không tự cấp quyền. Ví dụ chỉ dùng dữ liệu giả DEMO.

**Nhập tay không có tệp gốc:** trước công bố, lưu ảnh chụp JSON của dữ liệu nhập tay qua kho tệp Core và lấy `tep_id` thật làm phần tử `nguon_tep_ids` (ít nhất một, không trùng). Ảnh chụp ghi dữ liệu, người nhập, thời điểm, revision và nguồn `NHAP_TAY`; metadata nguồn do Core xác minh. Ảnh chụp chỉ chứa đầu vào, không chứa ID/hash của chính tệp hoặc hash phiên bản kết quả được tính từ tệp đó, để tránh vòng băm. Đây là tệp căn cứ nhập tay, không phải bằng chứng đã ký/đã duyệt. Không dùng UUID giả, mảng rỗng hay miễn vỏ; chưa lưu được ảnh chụp thì trả `CHO`, chưa công bố. Quy tắc áp dụng cả danh mục nhập tay, `bao_gia` và `du_an_dang_ban`; các ID trong ví dụ chỉ mô phỏng tệp DEMO đã lưu. Đây là yêu cầu thiết kế, không khẳng định đã có API tạo ảnh chụp.

## 1. `doi_tuong.v1`

**Mục đích:** Tra cứu một đối tượng dùng chung và mã Junsky của đối tượng trong một pháp nhân. Đối tác nhiều vai trò vẫn dùng một định danh đối tượng, không tạo bản sao theo module.

**Module sở hữu:** Core, khối `danh_muc`; không giao toàn bộ danh mục cho `mod_m0`.  
**Module được đọc:** Module được cấp quyền danh mục trong phạm vi pháp nhân.  
**Loại:** Dữ liệu công bố qua danh mục chung V3.

Bảng sau bổ sung cho vỏ chung:

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `doi_tuong_id` | Định danh nội bộ ổn định | `id \| null` | Có và phải khác `null` tại contract danh mục | — | P:87–88; từ điển chung |
| `phap_nhan_id` | Pháp nhân của phép tra cứu mã Junsky | `id` | Có | — | P:105–116 |
| `ma_junsky` | ObjectID được Junsky cấp; `null` nếu chưa ánh xạ | `chuoi \| null` | Có | — | P:109; M0 §3, §6 |
| `ten_phap_ly` | Tên pháp lý của đối tượng | `chuoi` | Có | — | P:90 |
| `vai_tro` | Các vai trò của cùng đối tượng | Mảng `chuoi` | Có, cho phép rỗng | — | P:96 |
| `trang_thai` | Trạng thái hồ sơ đối tượng | `chuoi` | Có | — | P:97 |
| `khoa` | Cờ khóa của mã Junsky | Boolean | Tùy chọn, chỉ khi có ánh xạ | — | P:112 |
| `dong` | Cờ đóng của mã Junsky | Boolean | Tùy chọn, chỉ khi có ánh xạ | — | P:113 |

Một đối tượng có thể được trả ở nhiều pháp nhân hoặc nhiều mã nguồn nhưng vẫn giữ `doi_tuong_id`. Không tự sinh mã Junsky; không dùng tên thay mã.

```json
{
  "contract": "doi_tuong.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "doi_tuong_id": "20000000-0000-4000-8000-000000000001",
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "ma_junsky": "DEMO.DT.001",
  "ten_phap_ly": "DOI TUONG DEMO",
  "vai_tro": ["DEMO_VAI_TRO"],
  "trang_thai": "HOAT_DONG",
  "khoa": false,
  "dong": false
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** tập giá trị `vai_tro`, `trang_thai`; chính sách chọn mã khi một đối tượng có nhiều ánh xạ hợp lệ. Không mặc định chọn mã đầu tiên.

## 2. `du_an.v1`

**Mục đích:** Cung cấp định danh và mã dự án thống nhất để module tham chiếu. Thông tin bán hàng, giá, lịch thanh toán và tiến độ thương mại thuộc contract CRM, không đưa vào danh mục này.

**Module sở hữu:** Core, khối `danh_muc`.  
**Module được đọc:** Module được cấp quyền danh mục theo pháp nhân.  
**Loại:** Dữ liệu công bố qua danh mục chung V3.

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `du_an_id` | Định danh dự án dùng chung | `id \| null` | Có và phải khác `null` tại contract danh mục | — | P:148–149; từ điển chung |
| `phap_nhan_id` | Pháp nhân quản lý dự án | `id` | Có | — | P:150 |
| `ma_junsky` | Mã dự án trong Junsky | `chuoi` | Có | — | P:151 |
| `ten` | Tên dự án | `chuoi` | Có | — | P:152 |
| `cha_id` | Dự án cấp trên, nếu có | `id \| null` | Tùy chọn | — | P:153 |
| `giai_doan` | Giai đoạn được khai trong danh mục | `chuoi \| null` | Tùy chọn | — | P:154 |
| `trang_thai` | `DAU_TU`, `VAN_HANH` hoặc `DONG` | Enum theo bảng hiện có | Có | — | P:155 |
| `ngay_chuyen_van_hanh` | Ngày chuyển sang vận hành | `ngay \| null` | Tùy chọn | Ngày | P:156 |

```json
{
  "contract": "du_an.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "du_an_id": "40000000-0000-4000-8000-000000000001",
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "ma_junsky": "DEMO.DA.001",
  "ten": "DU AN DEMO",
  "cha_id": null,
  "giai_doan": "GIAI DOAN DEMO",
  "trang_thai": "DAU_TU",
  "ngay_chuyen_van_hanh": null
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** quy ước nội dung `giai_doan` và phạm vi sử dụng `cha_id` cho dự án/giai đoạn/hạng mục; chưa mở rộng danh mục thành quản lý lô/căn.

## 3. `but_toan_de_xuat.v1`

**Mục đích:** Trao đổi các dòng định khoản đề xuất cùng căn cứ để kế toán kiểm tra, sửa và duyệt. Đề xuất hợp lệ về cấu trúc chưa đồng nghĩa đã được duyệt hoặc đủ điều kiện xuất Junsky.

**Module sở hữu:** Chủ chuyển tiếp kế toán cũ theo D §1.1; module sinh đề xuất chịu trách nhiệm nghiệp vụ. Chủ gói dùng chung sau tách **chờ Anh**, không mặc định giao nghiệp vụ định khoản cho Core.  
**Module được đọc:** Module duyệt/xuất được đăng ký và cấp quyền.  
**Loại:** Dữ liệu công bố.

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `de_xuat_id` | Định danh đề xuất | `id` | Có | — | P:501–502 |
| `phien_ban_de_xuat` | Số phiên bản đề xuất theo chứng từ; khác semver và revision công bố | Integer ≥ 1 | Có | Lần | P:504 |
| `hien_hanh` | Đề xuất còn là bản hiện hành tại lúc công bố | Boolean | Có; bên xuất phải kiểm lại | — | P:505 |
| `chung_tu_id` | Chứng từ được đề xuất định khoản | `id` | Có | — | P:503 |
| `phap_nhan_id` | Pháp nhân suy ra từ chứng từ | `id` | Có | — | P:209; D §1.1 |
| `chu_trinh` | Module nghiệp vụ sinh đề xuất, do Core gắn từ instance phát đã xác thực | `chuoi \| null` | Có trong đầu ra; module không tự khai | — | P:506; T §2.1 |
| `ngay_nghiep_vu` | Ngày nghiệp vụ của chứng từ | `ngay` | Có | Ngày | P:214 |
| `dien_giai` | Nội dung chứng từ | Chuỗi | Tùy chọn | — | P:222 |
| `muc` | Mức đề xuất `XANH`, `VANG`, `DO` | Enum hiện có | Có | — | P:509 |
| `nguon_suy_luan` | Nguồn tạo đề xuất | Enum `KHOA_CUNG`, `TU_KHOA`, `LICH_SU`, `CONG_NO`, `CFO`, `LLM`, `NGUOI`, `JUNSKY` | Có; kiểm với provenance Core | — | P:514,519 |
| `vi_sao` | Lý do, căn cứ giải thích đề xuất | Chuỗi | Tùy chọn | — | P:510; hướng dẫn định khoản |
| `dong` | Các dòng định khoản | Mảng object | Có | — | P:521–549 |
| `dong[].stt` | Thứ tự dòng trong đề xuất | Integer | Có | Dòng | P:524 |
| `dong[].no_co` | Vế Nợ `N` hoặc Có `C` | Enum `N`, `C` | Có | — | P:525 |
| `dong[].tai_khoan` | Mã tài khoản kế toán chi tiết | `chuoi` | Có | — | P:526; `../CLAUDE.md:30` |
| `dong[].so_tien` | Số tiền ghi sổ của vế Nợ/Có, không phải giá tính VAT | `tien`, thu hẹp `gia_tri` thành chuỗi số nguyên > 0 | Có | Chỉ VND, scale 0 | P:532–533; T §2.2 |
| `dong[].ma_doi_tuong` | Đúng `doi_tuong.v1.ma_junsky` trong cùng pháp nhân | `chuoi \| null` | Có; thiếu giữ `null` | — | P:534 |
| `dong[].ma_du_an` | Mã trong `du_an.v1` cùng pháp nhân | `chuoi \| null` | Tùy chọn | — | P:538 |
| `dong[].ttcp` | Mã trung tâm chi phí | `chuoi \| null` | Tùy chọn | — | P:539 |
| `dong[].khoan_muc` | Mã khoản mục phí | `chuoi \| null` | Tùy chọn | — | P:540 |

Đây là phần chung tối thiểu cho dòng định khoản; tỷ giá, nguyên tệ, VAT và thông tin hóa đơn hiện có ở P:528–547 chưa được suy rộng thành nghiệp vụ ngoại tệ trong lát này.

**Quy tắc “thà bỏ sót còn hơn nhập sai”:**

- Tài khoản phải là mã chi tiết trong danh mục hợp lệ; mã nhóm, mã ứng viên hoặc chuỗi nhiều tài khoản không đủ điều kiện xuất.
- Thiếu mã đối tượng thì giữ thiếu và chặn xuất theo chỉ đạo hiện hành; không tự dùng tên đối tác hay tạo mã thay thế.
- Kiểm Nợ = Có trên toàn chứng từ; không bỏ riêng dòng lỗi rồi xuất phần còn lại.
- Chỉ xuất phiên bản đã “Đồng ý”, còn hiệu lực và không thuộc diện đã có trong Junsky. Mức `XANH` không thay quyết định duyệt.
- Tra cứu đối tượng/dự án qua hai contract chung; không nhúng bản sao hồ sơ. Metadata duyệt dùng cơ chế Core, không thêm cờ tự khai `da_duyet`.
- `nguon_suy_luan=LLM` thì `muc` không được `XANH`; đổi nhãn nguồn không được che provenance LLM. Mọi dòng cùng VND, tiền nguyên dương; dòng 0 không công bố, tiền âm hoặc lẻ không tự làm tròn để qua kiểm. Nợ = Có > 0.
- Bên xuất đọc metadata kết quả/quyết định duyệt có thẩm quyền qua Core và đối chiếu đúng `de_xuat_id`, `phien_ban_de_xuat`, revision/hash nội dung; kiểm lại `hien_hanh`, kỳ khóa và trạng thái chứng từ ở cổng xuất. Trong chuyển tiếp, adapter chủ kế toán cũ kiểm `kho.de_xuat.hien_hanh` và trạng thái chứng từ theo P:705–735; consumer không đọc bảng riêng. Payload do module gửi kèm cờ/quyết định duyệt tự khai bị Core từ chối, không được lấy làm bằng chứng.
- **Mức 2 khóa tại máy chủ** và giao diện. Tự duyệt chỉ cho **phí ngân hàng, lãi tiền gửi, lương, bút toán định kỳ**, sau khi Mức 2 được mở, đủ kiểm tra bước 4 và có nhật ký (quy tắc dự án `CLAUDE.md` ở thư mục cha, §Quy tắc riêng). `XANH` không tự kích hoạt tự duyệt hoặc mở khóa xuất.

```json
{
  "contract": "but_toan_de_xuat.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "de_xuat_id": "50000000-0000-4000-8000-000000000001",
  "phien_ban_de_xuat": 1,
  "hien_hanh": true,
  "chung_tu_id": "60000000-0000-4000-8000-000000000001",
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "chu_trinh": "M1",
  "ngay_nghiep_vu": "2026-10-01",
  "dien_giai": "THU TIEN DEMO",
  "muc": "VANG",
  "nguon_suy_luan": "NGUOI",
  "vi_sao": "CAN KE TOAN DUYET DEMO",
  "dong": [
    {
      "stt": 1, "no_co": "N", "tai_khoan": "DEMO_TK_TIEN",
      "ma_doi_tuong": "DEMO.DT.001", "ma_du_an": "DEMO.DA.001",
      "ttcp": "DEMO_TTCP", "khoan_muc": "DEMO_KM",
      "so_tien": {"gia_tri": "1000000", "don_vi_tien": "VND"}
    },
    {
      "stt": 2, "no_co": "C", "tai_khoan": "DEMO_TK_PHAI_THU",
      "ma_doi_tuong": "DEMO.DT.001", "ma_du_an": "DEMO.DA.001",
      "ttcp": "DEMO_TTCP", "khoan_muc": "DEMO_KM",
      "so_tien": {"gia_tri": "1000000", "don_vi_tien": "VND"}
    }
  ]
}
```

Các tài khoản DEMO chỉ minh họa mã trong danh mục giả, không phải mã nhập Junsky.

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** chủ gói đích; ma trận bắt buộc đối tượng/dự án/TTCP/khoản mục theo tài khoản; phạm vi ngoại tệ. Trong khi chờ, giữ điều kiện xuất nghiêm ngặt hiện hành, không tự nới.

## 4. `tep_nhap_junsky.v1`

**Mục đích:** Bàn giao tham chiếu tới tệp Excel nhập Junsky và số kiểm soát của lô. JSON không thay thế workbook; nội dung 17/37 cột nằm trong tệp được tham chiếu.

**Module sở hữu:** Chủ chuyển tiếp kế toán cũ/adapter xuất; chủ gói đích chờ Anh.  
**Module được đọc:** Module xuất và đối chiếu được cấp quyền.  
**Loại:** Dữ liệu công bố.

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `lo_xuat_id` | Định danh lô xuất | `id` | Có | — | P:637–638 |
| `phap_nhan_id` | Pháp nhân của lô | `id` | Có | — | P:639 |
| `loai` | Tệp thu hoặc chi ngân hàng | Enum `JUNSKY_THU`, `JUNSKY_CHI` | Có | — | P:642; J §1–2 |
| `de_xuat_ids` | Các đề xuất thuộc lô | Mảng `id` | Có | — | P:655–664 |
| `tong_no` | Tổng Nợ theo tiền cơ sở | `tien` | Có | VND trong phạm vi nháp | P:646,648 |
| `tong_co` | Tổng Có theo tiền cơ sở | `tien` | Có | VND trong phạm vi nháp | P:647–648 |
| `tep` | Tham chiếu workbook được Core quản lý | `tham_chieu_tep.v1` | Có | — | T §4; P:643–644 |
| `sheet` | Hai sheet bắt buộc của workbook | Mảng object, đúng 2 phần tử | Có | — | J §2; `xuat/shadow.py:71–76`¹ |
| `sheet[].ten` | Tên sheet nguyên văn | `CB_tmpEntry1` hoặc `CB_tmpEntry2` | Có | — | J §2 |
| `sheet[].so_cot` | Số cột lần lượt 17 và 37 | Integer | Có | Cột | `xuat/shadow.py:20–21`¹ |
| `sheet[].so_dong` | Số dòng dữ liệu, không tính tiêu đề | Integer ≥ 0 | Có | Dòng | J §2; `xuat/shadow.py:44–52`¹ |

¹ Các đường dẫn `xuat/…` ở mục này tính từ `src/kho_tri_thuc/`.

`CB_tmpEntry1` chứa đầu chứng từ; `CB_tmpEntry2` chứa dòng định khoản, nối bằng `EntryID`. Giữ đúng tên/thứ tự cột; mã ghi Text, ngày ghi kiểu ngày Excel theo J §3–6. Không dùng workbook soát thay tệp nhập.

**Mức 2 còn khóa ở giao diện và backend**, căn cứ `../CLAUDE.md:14` và `src/kho_tri_thuc/giao_dien/operations.py:756–759`. Ví dụ dưới đây mô tả tệp DEMO giả định sau khi đủ gate; không xác nhận đã tạo tệp hoặc mở khóa.

```json
{
  "contract": "tep_nhap_junsky.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "lo_xuat_id": "70000000-0000-4000-8000-000000000001",
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "loai": "JUNSKY_THU",
  "de_xuat_ids": ["50000000-0000-4000-8000-000000000001"],
  "tong_no": {"gia_tri": "1000000", "don_vi_tien": "VND"},
  "tong_co": {"gia_tri": "1000000", "don_vi_tien": "VND"},
  "tep": {
    "contract": "tham_chieu_tep.v1",
    "phien_ban": "1.0.0",
    "tep_id": "80000000-0000-4000-8000-000000000001",
    "ten_tep": "DEMO-JUNSKY-THU.xlsx",
    "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "kich_thuoc": 4096,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "het_han_luc": null
  },
  "sheet": [
    {"ten": "CB_tmpEntry1", "so_cot": 17, "so_dong": 1},
    {"ten": "CB_tmpEntry2", "so_cot": 37, "so_dong": 2}
  ]
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh/NCC:** Entry2 đầy đủ hay chỉ đối ứng; Junsky giữ hay đánh lại `EntryID`; cách dùng `DebtID`; mapping `BankID`, `CashflowID` theo J §8. Hai dòng Entry2 trong ví dụ chỉ minh họa phương án đầy đủ. Chưa dùng công thức tổng của phương án này để kết luận phương án đối ứng sai. Mở Mức 2 vẫn cần thử 1 → 5 chứng từ và quyết định riêng; xuất tệp không đồng nghĩa đã nhập/ghi sổ.

## 5. Quy ước chung cho năm contract sự kiện

Bus hiện có chỉ chấp nhận nội dung tham chiếu UUID: khóa `*_id` hoặc `*_ids`; không mang số tiền, ngày, tên đối tác, JSON lồng hoặc tệp. Bên nhận đọc dữ liệu đầy đủ qua contract công bố đã đăng ký và được cấp quyền, không đọc bảng riêng.

Mỗi bảng trường sự kiện bên dưới **bao gồm bảng tham số chung sau**. Ví dụ JSON biểu diễn đầy đủ tham số nghiệp vụ của `B.phat`, không phải một transport mới; chỉ `tham_chieu` được đưa vào payload bus.

| Trường | Nghĩa | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `loai` | Tên sự kiện; ánh xạ tới mã contract `.v1` | `chuoi` | Có | — | B:30; C CD-031 |
| `phien_ban` | Phiên bản bus dạng số nguyên, không phải semver | Integer `1` | Có | — | B:30; BS:54 |
| `khoa_dedupe` | Khóa chống phát trùng, do backend tạo | `chuoi` | Có | — | B:30; BS:55,61 |
| `tham_chieu` | Các định danh để đọc dữ liệu nguồn | Object theo bảng từng sự kiện | Có | — | B:31,35–38 |
| `phap_nhan_id` | Pháp nhân lấy từ đối tượng đã kiểm quyền | `id` | Có | — | B:7–9 |
| `ben_phat` | Module phát do backend xác định | `chuoi` | Có | — | B:8,32 |

Phát cùng transaction nghiệp vụ. Bus giao ít nhất một lần; bên nhận ghi kết quả và ACK trong cùng transaction/kết nối. Cùng pháp nhân, bên phát và khóa dedupe nhưng khác loại/phiên bản/nội dung phải bị từ chối. Nguồn chưa sẵn sàng trả `CHO`; sai quyền trả lỗi quyền chuẩn, không giả thành `CHO`. Nguồn: B:3–14; BS:84–116; D §6.1.

### 5.1. `tien_da_noi_dot.v1`

**Mục đích:** Thông báo phần tiền đã được xác nhận nối với một đợt nghĩa vụ. Không làm phát sinh tiền hoặc bút toán doanh thu lần nữa.

**Sở hữu/module phát:** M1 theo `../53-kien-truc-xuong-song-engine-module.md` §4; đầu mối thực thi **chờ Anh** vì liên kết hiện được ghi ở CRM.  
**Module nhận/được đọc:** CRM, M3 — danh sách dự kiến, phải đăng ký và cấp quyền.  
**Loại:** Sự kiện.  
**Khi phát:** Khi giao dịch xác nhận liên kết thành công; không phát từ gợi ý ghép hoặc khi mới nhận sao kê.

Ngoài bảng chung:

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `tham_chieu.lien_ket_id` | Liên kết tiền–đợt đã được xác nhận | `id` | Có | — | `k2/crm.py:758–763`² |
| `tham_chieu.chung_tu_id` | Chứng từ tiền phía nguồn | `id` | Có | — | `k2/crm.py:758–762`² |
| `tham_chieu.nghia_vu_id` | ID đợt nghĩa vụ đã nối; ánh xạ ID lịch thu nguồn CRM | `id` | Có | — | `k2/crm.py:759–762`²; D §3.6, §6.2 |
| `tham_chieu.phien_ban_id` | ID phiên bản nghĩa vụ làm căn cứ liên kết | `id` | Có | — | D §3.6, §6.2 |

² Đường dẫn tính từ `src/kho_tri_thuc/`.

**Khóa chống trùng dự kiến:** loại sự kiện + `lien_ket_id`, trong phạm vi pháp nhân/bên phát. Chờ chốt quan hệ giữa khóa thao tác hiện có và khóa bus.

Bên nhận đọc liên kết qua V3/hàm Core được cấp quyền để lấy bộ ba `(module_nghia_vu, loai_nghia_vu, nghia_vu_id)`, ID phiên bản và `ma_bam_phien_ban_can_cu`; đối chiếu `nghia_vu_id`/`phien_ban_id` trong sự kiện rồi đọc đúng contract nguồn. Với CRM bộ ba là `(CRM, lich_thu, nghia_vu_id)` (§NV-CRM/§1). Không đưa hai chuỗi loại/module hoặc hash vào payload bus chỉ nhận UUID; không suy bộ ba từ `ben_phat=M1`.

```json
{
  "loai": "tien_da_noi_dot",
  "phien_ban": 1,
  "khoa_dedupe": "DEMO:tien_da_noi_dot:LK001",
  "tham_chieu": {
    "lien_ket_id": "90000000-0000-4000-8000-000000000001",
    "chung_tu_id": "60000000-0000-4000-8000-000000000001",
    "nghia_vu_id": "10000000-0000-4000-8000-000000000021",
    "phien_ban_id": "10000000-0000-4000-8000-000000000007"
  },
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "ben_phat": "M1"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`; bus `1`. **Chờ Anh:** `ben_phat`, danh sách nhận, khóa dedupe và xử lý gỡ/nối lại. Retry liên kết đã hủy không được làm liên kết sống lại.

### 5.2. `ban_giao_da_duyet.v1`

**Mục đích:** Thông báo một phiên bản bàn giao đã được duyệt để bên nhận kiểm tra căn cứ. Sự kiện không tự chứng minh đủ điều kiện ghi nhận doanh thu, giá vốn hoặc tăng tài sản.

**Sở hữu/module phát:** **Chờ Anh chốt nghĩa contract**. Thiết kế M3 có bàn giao bán hàng; thiết kế M4 có chuyển giao chi phí xây dựng sang M3/M6.  
**Module nhận/được đọc:** Chờ chốt theo nghĩa; M3/M6 là bên nhận chuyển giao xây dựng trong binding M4.  
**Loại:** Sự kiện.  
**Khi phát dự kiến:** Sau khi phiên bản bàn giao và quyết định duyệt tương ứng được lưu bền vững.

Ngoài bảng chung, trường dự kiến cho **nhánh bàn giao bán hàng**, chưa coi là thiết kế đã chốt:

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `tham_chieu.ban_giao_id` | Định danh bàn giao bán hàng | `id` | Dự kiến có; chờ Anh | — | `docs/BINDING-M3-DOANH-THU-SAU-CRM06.md` §3 |
| `tham_chieu.phien_ban_id` | Phiên bản bàn giao chính xác | `id` | Dự kiến có; chờ Anh | — | Cùng nguồn §3–4 |

**Khóa chống trùng dự kiến:** loại + bàn giao + phiên bản/quyết định duyệt. Nếu cùng phiên bản nguồn có nhiều quyết định, cặp bàn giao–phiên bản chưa đủ; chờ chốt định danh quyết định.

Ví dụ minh họa riêng nhánh M3:

```json
{
  "loai": "ban_giao_da_duyet",
  "phien_ban": 1,
  "khoa_dedupe": "DEMO:ban_giao_da_duyet:BG001:PB001",
  "tham_chieu": {
    "ban_giao_id": "90000000-0000-4000-8000-000000000003",
    "phien_ban_id": "90000000-0000-4000-8000-000000000004"
  },
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "ben_phat": "M3"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`; **chặn kích hoạt**. **Chờ Anh:** nghĩa bàn giao, chủ phát, bên nhận, tham chiếu quyết định và khóa chống trùng. Không gộp nghiệm thu nhà thầu, bàn giao khách hàng và chuyển giao chi phí thành một sự kiện cùng nghĩa.

**Vòng 2: chưa hoàn tất định nghĩa.** Ví dụ trên chỉ minh họa nhánh, chưa đủ định danh quyết định duyệt; không được dùng để đăng ký/kích hoạt trước khi Anh chốt.

### 5.3. `moc_da_xay_ra.v1`

**Mục đích:** Báo mốc thực tế đã được xác nhận để cập nhật nghiệp vụ phụ thuộc. Ngày dự kiến không chứng minh mốc đã xảy ra.

**Sở hữu/module phát:** CRM.  
**Module nhận/được đọc:** CRM và M3 theo nhu cầu đã đăng ký; danh sách chờ duyệt.  
**Loại:** Sự kiện.  
**Khi phát dự kiến:** Khi lưu thành công ngày thực tế của mốc đang sử dụng; không phát chỉ vì quá ngày dự kiến.

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `tham_chieu.moc_id` | Mốc dự án đã xác nhận thực tế | `id` | Có | — | `src/kho_tri_thuc/k2/sql_crm_du_an_moc.py:18–43` |

**Khóa chống trùng dự kiến:** loại + `moc_id` + `lan` lịch sử nguồn. Bảng nguồn dùng khóa lịch sử `(moc_id, lan)`, trong khi payload bus chỉ nhận UUID; **chưa có cách tham chiếu chính xác lần lịch sử trong nháp này**. Không tự thêm số `lan` vào payload hoặc đọc bản hiện tại thay bản đã phát.

```json
{
  "loai": "moc_da_xay_ra",
  "phien_ban": 1,
  "khoa_dedupe": "DEMO:moc_da_xay_ra:MOC001:lan1",
  "tham_chieu": {
    "moc_id": "90000000-0000-4000-8000-000000000005"
  },
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "ben_phat": "CRM"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`; **chặn kích hoạt**. **Chờ Anh:** tham chiếu phiên bản lịch sử, điều kiện xác nhận, bên nhận và xử lý sửa/xóa ngày thực tế. Không dùng `khoa_dedupe` như API để bên nhận tự phân tích phiên bản nguồn.

**Vòng 2: chưa hoàn tất định nghĩa.** `moc_id` chưa chỉ ra một lần lịch sử; tiếp tục chờ Anh chốt tham chiếu chính xác, không thêm số `lan` vào payload bus.

### 5.4. `hop_dong_hieu_luc.v1`

**Mục đích:** Báo một phiên bản hợp đồng bán đã được duyệt và bắt đầu có hiệu lực. Không đồng nhất hợp đồng đã ký, đã duyệt và đang có hiệu lực.

**Sở hữu/module phát:** CRM; phạm vi nháp là hợp đồng bán.  
**Module nhận/được đọc:** M1, M3 — chờ duyệt danh sách.  
**Loại:** Sự kiện.  
**Khi phát:** Khi đủ duyệt và đến thời điểm hiệu lực của phiên bản; không phát hiệu lực sớm chỉ vì đã bấm duyệt.

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `tham_chieu.hop_dong_id` | Định danh hợp đồng | `id` | Có | — | `src/kho_tri_thuc/k2/crm.py:633–636` |
| `tham_chieu.phien_ban_id` | Phiên bản hợp đồng bắt đầu hiệu lực | `id` | Có | — | Cùng tệp:652–666; thiết kế CRM §8 |

**Khóa chống trùng dự kiến:** loại + hợp đồng + phiên bản hiệu lực.

```json
{
  "loai": "hop_dong_hieu_luc",
  "phien_ban": 1,
  "khoa_dedupe": "DEMO:hop_dong_hieu_luc:HD001:PB001",
  "tham_chieu": {
    "hop_dong_id": "90000000-0000-4000-8000-000000000006",
    "phien_ban_id": "90000000-0000-4000-8000-000000000007"
  },
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "ben_phat": "CRM"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** quy tắc thời điểm khi thiếu `ngay_hieu_luc`, xử lý phiên bản hiệu lực trong tương lai và danh sách nhận. Giữ phân biệt duyệt/hiệu lực trong thiết kế CRM, không suy từ riêng cờ `HIEU_LUC` hiện có.

### 5.5. `hoa_don_da_nhan.v1`

**Mục đích:** Báo đã lưu quan sát hóa đơn mua vào để bên nhận đọc trạng thái và phiên bản nguồn. “Đã nhận” không đồng nghĩa đủ căn cứ ghi nhận, đã duyệt thuế hoặc dữ liệu kỳ đã đầy đủ.

**Sở hữu/module phát:** M2.  
**Module nhận/được đọc:** M4, M8 — chờ duyệt danh sách.  
**Loại:** Sự kiện.  
**Khi phát dự kiến:** Sau khi lưu thành công quan sát và liên kết đúng danh tính/phiên bản hóa đơn; nhận lại đúng nguồn không tạo thông báo nghiệp vụ trùng.

| Trường | Nghĩa nghiệp vụ | Kiểu | Bắt buộc | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `tham_chieu.hoa_don_id` | Danh tính hóa đơn mua vào | `id` | Có | — | P:5297; `k2/sql_cong_bo_hoa_don.py:39`² |
| `tham_chieu.quan_sat_id` | Quan sát nguồn vừa được lưu | `id` | Có | — | P:5294–5302; cùng tệp:48 |
| `tham_chieu.phien_ban_id` | Phiên bản nội dung gắn với quan sát | `id` | Có | — | P:5298; cùng tệp:57–60 |

**Khóa chống trùng dự kiến:** loại + `quan_sat_id`. Không chỉ dùng số hóa đơn vì một hóa đơn có thể có nhiều quan sát nguồn.

```json
{
  "loai": "hoa_don_da_nhan",
  "phien_ban": 1,
  "khoa_dedupe": "DEMO:hoa_don_da_nhan:QS001",
  "tham_chieu": {
    "hoa_don_id": "90000000-0000-4000-8000-000000000008",
    "quan_sat_id": "90000000-0000-4000-8000-000000000009",
    "phien_ban_id": "90000000-0000-4000-8000-000000000010"
  },
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "ben_phat": "M2"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** phát cho mọi quan sát mới hay chỉ quan sát được nguồn chấp nhận; bên nhận; chính sách thay đổi trạng thái nguồn. Bên nhận phải đọc đúng quan sát/phiên bản được tham chiếu, không thay bằng `latest` hoặc mặc định `eligible_content`.

Đường đọc chính xác, có kiểm quyền, được đặc tả tại NV-M2/`hoa_don_mua_vao.v1` bên dưới. M0064 hiện chỉ đọc latest nên chưa đáp ứng consumer sự kiện muộn; chưa có phép đọc chính xác được đăng ký thì trả `CHO`, **chặn kích hoạt consumer phụ thuộc**, không đọc bảng riêng hoặc dùng latest thay thế.

## Quy tắc chung lớp nghiệp vụ

1. **Hai lớp, một trách nhiệm rõ ràng.** JSON là dữ liệu trao đổi; JSON Schema mô tả cấu trúc để Core kiểm. Core sở hữu lớp kỹ thuật và danh mục chung; module sở hữu dữ liệu định nghĩa ý nghĩa nghiệp vụ, điều kiện công bố và xử lý ngoại lệ. Core đăng ký contract, không hấp thụ logic module. Căn cứ: CD-031, D §1.1.

2. **Dùng lại trước; mở rộng khi cùng nghĩa; tạo mới khi khác nghĩa.** Tra sổ contract trước khi thiết kế. Cùng đối tượng, đơn vị, phạm vi và ý nghĩa thì dùng lại. Thiếu trường cho cùng nghĩa thì chủ contract đề xuất phiên bản mở rộng. Chỉ tạo mới khi có nghiệp vụ hoặc grain khác được giải thích rõ. Tham chiếu `doi_tuong.v1`, `du_an.v1`, kiểu `chung.v1`, tệp và lỗi chung; không sao chép chúng thành schema riêng.

3. **Đặt tên.** Mã nghiệp vụ dùng tiếng Việt không dấu, `snake_case`, hậu tố `.v<major>`; tên trường cùng quy ước. Mã nguồn Junsky giữ nguyên giá trị. Sự kiện diễn tả điều đã xảy ra; không dùng tên “đã duyệt/hiệu lực/đã nhận” thay cho các trạng thái khác nhau. Tên kỹ thuật đang có như `revision`, `khoa_dedupe` chỉ giữ tại đúng biên kỹ thuật đã dẫn nguồn.

4. **Phiên bản bất biến.** Ghim mã và phiên bản chính xác. Theo T §2, mọi thay đổi schema đã phát hành, kể cả thêm trường tùy chọn, phải có `$id` và phiên bản mới; không sửa schema dưới cùng `$id`. Phân biệt semver contract, revision nội dung và số phiên bản bus. Bản cũ tiếp tục phục vụ module đang dùng; sổ cảnh báo trước khi ngừng, không tự chuyển người đọc sang bản mới.

5. **Gói và sổ contract.** Theo CD-032, gói có `contract/` chứa mô tả, nguồn từng trường, JSON DEMO, JSON Schema và phiên bản cho dữ liệu công bố, sự kiện phát/nhận, đầu vào nguồn. `module.json` ghim theo các khóa đã có `contract.{cong_bo,su_kien_phat,su_kien_nhan,dau_vao_nguon}` tại T §manifest (dòng 1483–1491), đồng bộ binding công bố/sự kiện tại S §6. Core kiểm và đăng ký vào sổ trong `loi`: mã, phiên bản, chủ sở hữu, module sử dụng, trạng thái `nhap`/Anh duyệt/đang dùng/ngừng. Thiếu hoặc không hợp lệ → không cài.

6. **Anh duyệt trước kích hoạt.** Module soạn; lead đối chiếu nguồn và tổng hợp danh mục dạng bảng; Anh duyệt contract mới và phiên bản mới của contract đang dùng. Trường “chờ Anh” chưa trở thành quy tắc vận hành. Không cần sửa code Core chỉ để thêm contract đã đạt kiểm.

7. **Trùng nghĩa → đỏ.** Mỗi contract khai grain (một dòng là gì), khóa dòng, chủ và nguồn chiếu theo bảng dưới. Hai chủ khác nhau khai cùng loại dòng và cùng khóa → đỏ; đổi tên không đổi grain. Phép chiếu/mở rộng hợp lệ phải dẫn contract/chủ gốc, ánh xạ trường và phiên bản, không nhận quyền sở hữu lại phần chung. Module đọc dữ liệu module khác ngoài contract đã đăng ký và cấp quyền cũng đỏ. Danh mục chung đọc qua V3; dữ liệu riêng qua `cong_bo_*`; sự kiện qua bus. Thiếu dữ liệu trả `CHO`, sai quyền trả lỗi chuẩn.

8. **Kiểm bằng máy trước công bố.** Mọi dữ liệu kế thừa `vo_noi_dung` theo NV-CHUNG, kiểm schema đúng phiên bản và bất biến nghiệp vụ bên dưới; parse được JSON chưa đủ. Từ điển cùng tên buộc cùng kiểu, nullable và đơn vị; điều kiện cần có giá trị được ghi riêng, không đổi kiểu theo module. Tham chiếu chéo module luôn ghim ID phiên bản + mã băm và kiểm cùng pháp nhân qua mặt công bố, không lấy bản mới nhất. Trường đã nêu chỉ ID còn phải được giải tham chiếu tới metadata/hash chính xác trước khi dùng; không suy hash từ ID, không đọc bảng riêng.

### Từ điển trường dùng chung và nguồn danh mục

`id` và `chung.id` là cùng `$ref` tới `chung.v1#/$defs/id`; các tên kiểu viết tắt khác cũng vậy. `B`/tùy chọn quy định có khóa; nullable quy định có được nhận `null`, hai điều độc lập.

| Trường / nhóm nghĩa | Kiểu, nullable, đơn vị thống nhất | Nguồn và điều kiện |
|---|---|---|
| `contract`, `phien_ban`, `revision`, `nguon_tep_ids` | Nguyên vỏ chung; `nguon_tep_ids` ≥ 1, không trùng, không `null` | NV-CHUNG; mọi contract công bố |
| `phap_nhan_id` | `id`, không `null`, không đơn vị | Core xác minh |
| `hop_dong_id` | `id \| null`, không đơn vị | Hợp đồng/nghĩa vụ phải khác `null`; kết quả K độc lập được `null` khi không gắn hợp đồng |
| `so_hop_dong` | `chuoi \| null`, không đơn vị | **Chiếu từ `danh_muc.hop_dong` qua V3**, không phải trường CRM/M4 tự sở hữu. Khóa bắt buộc khi công bố hợp đồng; CRM nháp có thể `null`, M4 vận hành phải có số |
| `doi_tuong_id`, `du_an_id` | `id \| null`, không đơn vị | Trên hợp đồng: **chiếu từ `danh_muc.hop_dong` qua V3**, trỏ `doi_tuong.v1`/`du_an.v1`. CRM hiệu lực/M4 có hợp đồng phải đủ dự án; bên đối tác M4 có thể chưa ánh xạ. Ngoài hợp đồng: tham chiếu danh mục tương ứng |
| `thue_suat` | `chuoi`, không `null`, % hoặc mã chế độ | Catalog thuế ghim phiên bản: `10`, `8`, `5`, `0`, `KCT`, `KKKNT`. Cùng nghĩa tại CRM và M4; M4 ánh xạ trường nguồn `vat` decimal sang mã thuế khi có căn cứ, không dùng JSON number; giá trị ngoài catalog trả `CHO`, không ép `KCT`/`KKKNT` thành `0` |
| `ty_le` | `thap_phan`, không `null`, % | Tỷ lệ giá bán trước VAT; không phải tỷ lệ tổng tiền có VAT/phí |
| Các trường `tien` | Chuỗi decimal + `don_vi_tien`, nullable chỉ khi bảng cho phép | Không trộn tiền tệ trong phép cộng; chưa rõ cơ sở VAT giữ chưa rõ, không tự tính |

Các kiểu nullable trên áp cho **dữ liệu công bố**; ràng buộc điều kiện vẫn buộc ID khác `null` tại danh mục gốc, hợp đồng/nghĩa vụ đủ điều kiện hoặc dự án M4. ID tham chiếu trong payload sự kiện tuân riêng vỏ bus: bắt buộc UUID khác `null`. Việc chiếu danh mục không trao quyền sửa danh mục cho CRM/M4; khi ghim hợp đồng phải giữ ID + hash phiên bản nguồn, không chụp trường danh mục rồi tự đổi nghĩa.

### Grain và khóa dòng đăng ký

| Contract | Một dòng / khóa ổn định trong pháp nhân | Khóa phiên bản / dòng con |
|---|---|---|
| `doi_tuong.v1` | Đối tượng–pháp nhân–mã Junsky / `(phap_nhan_id,doi_tuong_id,ma_junsky)`; mã thiếu chưa dùng xuất | `revision`; danh mục Core là chủ |
| `du_an.v1` | Dự án / `du_an_id` | `revision`; danh mục Core là chủ |
| `but_toan_de_xuat.v1` | Phiên bản đề xuất chứng từ / `de_xuat_id` | `(chung_tu_id,phien_ban_de_xuat)`; dòng `(de_xuat_id,stt)` duy nhất |
| `tep_nhap_junsky.v1` | Lô xuất / `lo_xuat_id` | `revision`; sheet `(lo_xuat_id,ten)` duy nhất |
| `hop_dong_ban.v1` | Phiên bản nghiệp vụ bán / `(hop_dong_id,ban.id)` | Đợt `(module_nghia_vu,loai_nghia_vu,nghia_vu_id)`; lịch mỗi phiên bản không trùng ID |
| `bao_gia.v1` | Revision báo giá / `(bao_gia_id,revision)` | Dòng dự kiến `nghia_vu_id`; chưa là nghĩa vụ hiệu lực |
| `du_an_dang_ban.v1` | Phiên bản cấu hình bán / `(du_an_dang_ban_id,phien_ban_du_an_id)` | Phí theo vị trí trong ảnh chụp; mốc `(id,lan)`; tiến độ `lan`; lô `(id,lan)` |
| `hop_dong_thau.v1` | Hồ sơ nghiệp vụ thầu / `hop_dong_id` | `revision`, `rev_tham_so`; định danh chung chỉ chiếu V3 |
| `phu_luc.v1` | Phụ lục thầu / `phu_luc_id` | `revision`; thay đổi tham số theo `ma` |
| `boq.v1` | Lần nhập BOQ / `boq_id` | Dòng `(boq_id,sheet,so_dong)`; không dùng mã hạng mục thay vị trí nguồn |
| `dot_thanh_toan.v1` | Đợt hồ sơ thầu / `dot_id` | `phien_ban_ho_so_id`, `(ket_luan_id,ket_luan_revision,graph_sha256)`; dòng khối lượng theo `ma_hang_muc` trong snapshot, trùng mã chưa rõ thì `CHO` |
| `ket_qua_kiem_dot.v1` | Nhóm kiểm trong lần chạy / `(lan_kiem_id,nhom_kiem)` | Quy tắc `(lan_kiem_id,nhom_kiem,ma)`; phát hiện giữ vị trí trong snapshot |
| `nghiem_thu.v1` | Bản bàn giao nghiệm thu / `(nghiem_thu_id,phong_bi_id)` | `phong_bi_sha256`; revision kế toán `kt_xac_nhan_id` |
| `hoa_don_mua_vao.v1` | Quan sát hóa đơn / `(hoa_don_id,quan_sat_id,phien_ban_id)` | `ma_bam_noi_dung`; đích `(dich_id,phien_ban_dich)`; phần chung dùng lại M0064, xem NV-M2 |
| `cong_no_phai_tra.v1` | Hồ sơ khoản phải trả / `cong_no_id` (**chờ Anh**) | `revision`; khóa căn cứ/thanh toán còn chờ Anh, chưa kích hoạt |

Khóa dòng con khác ở các mảng chưa có ID là vị trí phần tử trong snapshot bất biến + khóa phiên bản cha, không được dùng vị trí để nối nghĩa vụ qua phiên bản. Khi kiểm trùng nghĩa, grain tách theo nghiệp vụ bán/thầu không làm trùng phần định danh hợp đồng do Core sở hữu.

### Cơ sở VAT, thang tiền và bất biến

Quy tắc sau áp dụng cho **từng trường tiền trong nhóm**, kể cả tiền trong biến thể `gia_tri`. Nguồn đọc nguyên trạng tối đa 6 số lẻ theo `chung.tien`; vượt miền trả lỗi, không làm tròn mất dữ liệu để ép vào contract. Kết quả tính CRM VND làm tròn đến đồng (scale 0, half-up), USD đến cent (scale 2, half-up), chỉ làm tròn ở kết quả tiền; phần dư phân bổ vào đợt cuối trong nhánh đã chốt. Tỷ giá không tự làm tròn hoặc tự lấy ngày mới. Đây là quy ước tính của bản nháp, chưa mở rộng policy ngoại tệ kế toán.

| Phạm vi trường tiền | Cơ sở VAT / thang và kiểm |
|---|---|
| Bút toán `dong[].so_tien`, lô `tong_no/tong_co` | Tiền ghi sổ, không suy VAT; VND scale 0, Nợ = Có > 0; lô bằng tổng các phiên bản đã duyệt được ghim, cùng VND |
| CRM `don_gia`/`don_gia_niem_yet`, `gia_dat_tru_m2`, tiền trong `tham_so` | `don_gia` theo `co_so_thue`; niêm yết và đất trừ trước VAT. Tham số theo `ma`/catalog ghim, chưa rõ thì không dùng tính. Tiền nguồn giữ scale; tiền kết quả theo VND/USD ở trên |
| CRM `tong_truoc_vat`, `tong_vat`, `tong_gom_vat` | Lần lượt giá bán trước VAT, riêng VAT, giá bán gồm VAT; `tong_truoc_vat + tong_vat = tong_gom_vat`. Phí theo dõi riêng, không cộng vào các tổng giá bán (CD-038 câu 1A) |
| CRM `gia_tri_nhap`, `gia_tri_gom_vat`, `trong_do_vat` | Tiền nhập lịch là tiền trả tại đợt đã xử lý VAT; `%` tính trên giá bán trước VAT. Tổng đợt giá bán = tổng gồm VAT; tổng VAT đợt = tổng VAT; tổng % đợt giá bán = 100. Kiểm cùng đơn vị, tiền/VAT không âm, VAT ≤ tiền đợt |
| CRM phí `muc` | Theo `co_so_gia_tri` của `PhiCrm`; `CHUA_RO` không được dùng tính nghĩa vụ. Phí là mức theo đơn vị tính, chưa phải số tiền đến hạn |
| M4 hợp đồng `gia_tri_hop_dong`, BOQ `don_gia/thanh_tien_ghi`, tiền trong `thay_doi_tham_so` | Cơ sở theo `gom_vat`, tài liệu BOQ/catalog tham số ghim; chưa đủ căn cứ giữ `CHUA_RO`, không tính VAT mặc định. Nguồn giữ scale tối đa 6, không tự sửa `thanh_tien_ghi` bằng phép nhân |
| Phụ lục `gia_tri_thay_doi_truoc_vat/sau_vat`, `gia_tri_hop_dong_ghi_sau_phu_luc` | Trước/gồm VAT tương ứng; số sau phụ lục giữ cơ sở tài liệu, so với hợp đồng chỉ khi cùng cơ sở. Cho phép âm ở khoản tăng/giảm; ví dụ cùng cơ sở gồm VAT: 1.100.000.000 − 11.000.000 = 1.089.000.000 |
| Đợt M4: mọi trường tiền nguồn, `khoi_luong[].don_gia_thanh_toan`, mọi tiền review xác nhận | Tổng nguồn theo `co_so_gia_tri`; đơn giá theo `co_so_don_gia`; tiền review theo `co_so_gia_tri_review`. Giữ số nguồn; kết luận nguồn tối đa scale 2 (DUYET:27–30), không tự làm tròn lại. Nhánh VND tính mới scale 0; đơn giá/nguồn lẻ giữ nguyên và chờ căn cứ làm tròn. Khác cơ sở/đơn vị hoặc `CHUA_RO` thì không tự đối chiếu bằng phép trừ |
| Kết quả kiểm `anh_huong_uoc_tinh` | Giữ cơ sở VAT và scale của finding/căn cứ đã ghim; không rõ thì chưa dùng ghi nhận, không suy VAT từ mức độ finding |
| Nghiệm thu: mọi trường tiền review/kế toán xác nhận | `co_so_gia_tri` chỉ áp tiền kế toán xác nhận; tiền review kế thừa kết luận chính xác của đợt. Kế toán/nguồn giữ scale tối đa 2; chưa rõ VAT thì không tự tính VAT; các khoản tạm ứng/thu hồi/giữ lại tách riêng |
| Công nợ: ba trường tiền | Cùng cơ sở nghĩa vụ đã được duyệt, cùng tiền tệ/scale của căn cứ ghim; số còn lại = phải trả − đã thanh toán chỉ khi đủ căn cứ và policy. Cơ sở VAT/scale vận hành cụ thể **chờ Anh**, chưa tính/ghi nhận từ JSON nháp |

Các bất biến cộng tiền dùng decimal chính xác, không dùng float. `null`/thiếu không bằng 0; chưa xác định thì `CHO`, không bỏ dòng lỗi để tổng vẫn khớp. CRM bản đầu chỉ có lịch `loai_khoan=GIA_BAN`, Σ%=100 cho phần giá bán; phí theo dõi riêng. VAT cọc chuyển giữa các đợt theo NV-CRM §1–§2 (CD-038 câu 1A/2B), không làm đổi tổng VAT hoặc tổng tiền giá bán.

*Kiểm vòng 2 là kiểm tài liệu: parse JSON, đối chiếu vỏ/kiểu đã khai và tính lại tổng bằng decimal; chưa chứng nhận JSON Schema đầy đủ hoặc runtime. Không chạy ứng dụng hay truy cập kho dữ liệu.*
---

| Mã contract | Mục đích | Sở hữu | Được đọc |
|---|---|---|---|
| `hop_dong_ban.v1` | Công bố phiên bản, tham số có căn cứ và lịch thanh toán của hợp đồng bán | CRM | M1, M3 theo phạm vi được cấp; bên đọc bổ sung chờ Anh |
| `bao_gia.v1` | Công bố báo giá và lịch dự kiến để in, chuyển sang soạn hợp đồng | CRM | CRM; chưa xác định module ngoài CRM cần đọc — chờ Anh |
| `du_an_dang_ban.v1` | Công bố cấu hình bán hàng của dự án, tiến độ chuẩn và lô/căn | CRM | CRM; chưa xác định module ngoài CRM cần đọc — chờ Anh |

**Trạng thái toàn lát: `nhap`, phiên bản cấu trúc `1.0.0`; chưa được kích hoạt hoặc cấp quyền đọc.**

### Quy ước áp dụng cho NV-CRM

- Đây là **lớp nghiệp vụ trong JSON hai lớp**, theo CD-031/032. CRM định nghĩa nghiệp vụ; Anh duyệt trước khi kích hoạt.
- Cả ba contract CRM kế thừa nguyên `vo_noi_dung`, gồm `nguon_tep_ids` bắt buộc ≥ 1. Nhập tay tạo ảnh chụp căn cứ theo NV-CHUNG; kiểm vỏ và schema trước công bố.
- Dùng trực tiếp các kiểu `$defs` của `urn:ktt:contract:chung.v1`: `id`, `ma`, `chuoi`, `ngay`, `thoi_diem`, `thap_phan`, `tien`, `gia_tri`, `dan_chung`, `sha256`. Bảng dưới viết tắt thành `chung.id`, `chung.tien`…; không định nghĩa lại.
- `phien_ban` là phiên bản **contract**; `revision` là lần sửa nội dung trao đổi; số phiên bản hợp đồng/dự án là trường nghiệp vụ riêng. Không dùng thay thế nhau.
- `doi_tuong_id` tham chiếu `doi_tuong.v1`; `du_an_id` tham chiếu `du_an.v1` của lát Chung. Không nhúng lại tên, MST, CCCD, tài khoản hoặc toàn bộ danh mục. Mã nghiệp vụ kế thừa như số hợp đồng, mã lô, mã sự kiện giữ kiểu chuỗi theo catalog nguồn; không nới kiểu `chung.ma`.
- Tham chiếu tệp dùng `tham_chieu_tep.v1`; lỗi dùng `loi_chuan.v1`. Không thêm đường dẫn vật lý hoặc một cấu trúc lỗi riêng.
- CRM sở hữu dữ liệu riêng tại `mod_crm`; bên ngoài chỉ đọc phép chiếu được cấp tại `cong_bo_crm`. Định danh chung thuộc `danh_muc`; không cấp quyền đọc bảng CRM qua các ví dụ này.
- **B** = bắt buộc; **T** = tùy chọn; **ĐK** = bắt buộc khi điều kiện nêu trong bảng xảy ra. `null` chỉ hợp lệ tại trường có kiểu cho phép; thiếu dữ liệu không được thay bằng `0`.
- Mọi ID, mã băm, tệp và giá trị trong ví dụ đều giả, thuộc tình huống **DEMO**.

**Ký hiệu nguồn dùng trong bảng:**

| Ký hiệu | Tài liệu/tệp |
|---|---|
| `CD` | `docs/46-chuyen-doi-dieu-phoi/CHI-DAO-TU-ANH.md`, chỉ đạo tương ứng |
| `DL`, `CSDL`, `SDK` | `docs/47-core/g1/CONTRACT-DU-LIEU.md`, `DAC-TA-CSDL.md`, `DAC-TA-SDK.md` |
| `TK` | `../THIET-KE-MODULE-DE-CHOT-2026-10-20/CRM-CHUC-NANG-VA-THIET-KE.md` |
| `TL42`, `TL45`, `TL49` | Các tài liệu `42-man-hinh-crm-ke-toan-va-giao-ket.md`, `45-review-man-bao-gia-sau-lap-trinh.md`, `49-trang-chu-luoi-icon.md` tại thư mục cha |
| `CRM`, `GK`, `DA`, `SQL-DA`, `SQL-MOC` | Các tệp dưới `src/kho_tri_thuc/k2/`: `crm.py`, `crm_giao_ket.py`, `crm_du_an_ban.py`, `sql_crm_du_an_ban.py`, `sql_crm_du_an_moc.py` |
| `KK` | `docs/46-chuyen-doi-dieu-phoi/KK-UI-DA-BG.md` |

Chưa tìm thấy tài liệu tên bắt đầu bằng “50” trong các tệp tài liệu thuộc phạm vi được phép đọc.

### 1. `hop_dong_ban.v1`

**Mục đích:** Cung cấp một phiên bản xác định của hợp đồng bán, tham số và căn cứ, cùng lịch thanh toán có phân biệt phần trước VAT, tiền phải thanh toán và VAT thực thu từng đợt. Bên nhận dùng đúng phiên bản được tham chiếu để đối chiếu tiền hoặc xử lý nghiệp vụ thuộc module mình.

**Module sở hữu:** CRM. **Module được đọc:** M1, M3 theo quyền được đăng ký; bên đọc bổ sung chờ Anh. **Loại:** dữ liệu công bố.

#### Bảng trường

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `contract` | Mã cấu trúc trao đổi | Hằng `hop_dong_ban.v1` | B | — | CD-031; DL §2 |
| `phien_ban` | Phiên bản cấu trúc | Hằng `1.0.0` | B | — | DL §2 |
| `revision` | Lần sửa nội dung được công bố | Kiểu `revision` của `chung.vo_noi_dung` | B | lần | DL §3 |
| `nguon_tep_ids` | Tệp nguồn hoặc ảnh chụp nhập tay đã lưu Core | Mảng `chung.id`, ≥ 1, không trùng | B | — | DL §3; NV-CHUNG |
| `hop_dong_id` | Định danh hợp đồng chung | `chung.id` hoặc `null` | B và phải khác `null` tại contract hợp đồng | — | CSDL §6.2; TK §6 |
| `ma_noi_bo` | Mã nhận diện nghiệp vụ của hợp đồng | `chung.chuoi` | B | — | `CRM:393`; TK §6 |
| `so_hop_dong` | Chiếu số hợp đồng từ `danh_muc.hop_dong` qua V3 | `chung.chuoi` hoặc `null` | B; được `null` khi chưa có số | — | CSDL §6.2; `CRM:709`; TL42 §4 |
| `phap_nhan_id` | Pháp nhân sở hữu hồ sơ | `chung.id` | B | — | CSDL §5; `CRM:393` |
| `doi_tuong_id` | Chiếu khách hàng từ `danh_muc.hop_dong`, trỏ `doi_tuong.v1` | `chung.id` hoặc `null` | B; phải có trước hiệu lực | — | CSDL §6.2; `CRM:403`; TK §6 |
| `du_an_id` | Chiếu dự án từ `danh_muc.hop_dong`, trỏ `du_an.v1` | `chung.id` hoặc `null` | B; phải có trước hiệu lực | — | CSDL §6.2; `CRM:405`; TK §6 |
| `lo_can_id` | Lô/căn trong cấu hình bán của dự án | `chung.id` | T | — | `GK:339`; TL42 §6–§7 |
| `loai_hinh_id` | Loại hình doanh thu/profile áp dụng | `chung.id` | B | — | `CRM:360`; TK §6 |
| `trang_thai_giao_ket` | Trạng thái xử lý hợp đồng | Chuỗi theo catalog CRM | B; mapping catalog chờ Anh | — | TL42 §13; TK §4 |
| `ban` | Phiên bản nghiệp vụ đang công bố | Object theo bảng dưới | B | — | TK §6; `CRM:356` |
| `ngay_ky` | Ngày ký thực tế | `chung.ngay` hoặc `null` | B; phải có khi đã ký | ngày | TL42 §8 |
| `tham_so` | Tham số và căn cứ của phiên bản | Mảng object theo bảng dưới | B | — | TK §6; `CRM:373` |
| `gia_thue` | Giá và kết quả VAT của phiên bản | Object `GiaCrm` bên dưới | B | VND/USD | CD-024; TL42 §7 |
| `phi` | Các phí theo dõi riêng, kế thừa nguyên từ revision báo giá khi chuyển Soạn; không thuộc lịch nghĩa vụ bản đầu | Mảng `PhiCrm` tại §3 | B; được rỗng | Theo dòng | TL42 §6; `GK:341`–`343`; CD-038 câu 1A |
| `lich_thanh_toan` | Các đợt theo đúng thứ tự thanh toán | Mảng `DongLichCrm` bên dưới | B | — | CD-024; TK §6 |
| `tep_nguon` | Thông tin tải/xem tài liệu hợp đồng chính, khác danh sách ID nguồn trong vỏ | `tham_chieu_tep.v1` | ĐK: phiên bản từ tài liệu/ký; `tep_id` phải thuộc `nguon_tep_ids` | — | DL §4; `CRM:358` |

**Các trường trong `ban`:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `id` | ID phiên bản nghiệp vụ | `chung.id` | B | — | `CRM:360` |
| `so` | Số phiên bản hợp đồng | Integer dương | B | phiên bản | `CRM:334` |
| `loai` | Bản gốc hoặc phụ lục | Chuỗi theo catalog CRM | B | — | TK §6; `CRM:337` |
| `so_phu_luc` | Số phụ lục | `chung.chuoi` | ĐK: phụ lục đã có số | — | `CRM:336` |
| `thay_cho_id` | Phiên bản được thay thế | `chung.id` | ĐK: có quan hệ thay thế | — | `CRM:360` |
| `ngay_hieu_luc` | Ngày hiệu lực nghiệp vụ | `chung.ngay` hoặc `null` | B; chưa xác định được `null` | ngày | TK §6; `CRM:335` |
| `ma_bam` | Mã băm căn cứ phiên bản để bên nhận kiểm tra | `chung.sha256` | B | — | CSDL §6.1–§6.2 |
| `kiem_boi` | Người kiểm phiên bản | `chung.chuoi` | T | — | `CRM:427` |
| `kiem_luc` | Thời điểm kiểm | `chung.thoi_diem` | ĐK: đã kiểm | — | `CRM:429` |
| `duyet_boi` | Người duyệt phiên bản | `chung.chuoi` | T | — | `CRM:723` |
| `duyet_luc` | Thời điểm duyệt | `chung.thoi_diem` | ĐK: đã duyệt | — | `CRM:724` |

**Đầu vào `ban.ma_bam`:** SHA-256 của UTF-8 không BOM của JSON canonical: sắp khóa object theo thứ tự mã Unicode, không khoảng trắng thừa, giữ thứ tự mảng; chuỗi Unicode ghi trực tiếp, không chuẩn hóa Unicode hay escape `/`, chỉ escape ký tự JSON bắt buộc (ký tự điều khiển dùng `\u00xx` chữ thường, dấu nháy/backslash dùng escape JSON tương ứng). Trường decimal theo schema giữ dạng chuỗi chuẩn (bỏ 0 lẻ tận cùng, không số mũ, `-0` thành `0`), không chuẩn hóa chuỗi mã/ID. Object đầu vào gồm `contract`, `phien_ban`, `hop_dong_id`, `phap_nhan_id`, `ma_noi_bo`, `so_hop_dong`, `doi_tuong_id`, `du_an_id`, `lo_can_id`/`loai_hinh_id` nếu có, `ngay_ky`, `ban.{id,so,loai,so_phu_luc,thay_cho_id,ngay_hieu_luc}` (khóa tùy chọn chỉ có khi được khai), `tham_so`, `gia_thue`, `phi`, `lich_thanh_toan` và mảng object `{tep_id,sha256}` của tệp trong `nguon_tep_ids` đã giải qua Core, đặt dưới khóa `nguon_tep`, sắp theo `tep_id`. Không băm chính `ban.ma_bam`, revision công bố, trạng thái xử lý, thông tin kiểm/duyệt, URL tải/hạn tải; chúng không làm đổi nội dung nghĩa vụ. Thay nội dung đầu vào phải có phiên bản `ban.id` mới và hash mới. M3/M1 ghim `ban.id` + `ban.ma_bam`; `ma_bam_phien_ban_can_cu` của liên kết Core nhận đúng hash này. Hash chữ lặp trong JSON là placeholder DEMO, không phải kết quả băm được chứng nhận. Trong `lich_thanh_toan[].moc` chỉ băm `loai`, `ngay`, `su_kien`, `so_ngay_sau_moc`, `moc_du_an_id`; không băm `lan_moc`, `ngay_du_kien`, `ngay_thuc_te`, `han` vì đó là trạng thái mốc theo thời gian, được ghim riêng qua `(moc_du_an_id, lan_moc)` và sự kiện `moc_da_xay_ra`, không làm đổi phiên bản hợp đồng (bổ sung lead sau Opus vòng 2).

**Các trường trong mỗi phần tử `tham_so`:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `ma` | Mã tham số theo catalog đã ghim | Chuỗi theo catalog nguồn | B | — | DL §7; `CRM:374` |
| `ten` | Tên tham số nghiệp vụ | `chung.chuoi` | B | — | TL42 §5 |
| `gia_tri_nguon` | Giá trị đọc từ nguồn, chưa đồng nghĩa đã duyệt | `chung.gia_tri` | B | Theo giá trị | TK §6; `CRM:381` |
| `gia_tri_hieu_luc` | Giá trị được sử dụng trong phiên bản | `chung.gia_tri` | B; chưa xác định dùng nhánh `chua_ro` | Theo giá trị | TL42 §5; `CRM:375` |
| `don_vi` | Đơn vị nghiệp vụ của tham số | `chung.chuoi` hoặc `null` | B | VND/USD, %, ngày… | TK §6 |
| `dieu_khoan` | Điều/khoản chứa quy định | `chung.chuoi` hoặc `null` | B | — | `CRM:381` |
| `dan_chung` | Trích dẫn và vị trí nguồn | Mảng `chung.dan_chung` | B | — | DL §3, §7; TL42 §5 |
| `nguon` | Mẫu, trích bản ký hoặc nhập tay | Chuỗi theo catalog CRM | B | — | TL42 §5 |
| `trang_thai_can_cu` | Tình trạng kiểm/căn cứ của giá trị | Chuỗi theo catalog CRM | B | — | `CRM:375`; TK §6 |
| `ke_thua_tu` | Tham số nguồn được kế thừa | `chung.id` | ĐK: tham số kế thừa | — | `CRM:365`–`368` |

#### Cấu trúc CRM dùng lại cho Hợp đồng và Báo giá

`GiaCrm` và `DongLichCrm` là nhóm trường nội bộ của **cùng gói contract CRM**, không phải contract nghiệp vụ mới. Báo giá tham chiếu lại các nhóm này.

**`GiaCrm`:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `don_gia` | Đơn giá áp dụng nếu tính theo diện tích | `chung.tien` | T | VND/USD trên m² | `GK:329`; TL42 §6 |
| `dien_tich` | Diện tích làm cơ sở tính | `chung.thap_phan` | ĐK: tính theo diện tích | m² | `GK:330` |
| `co_so_thue` | Giá đầu vào trước hay đã gồm VAT | Enum `NET`, `GROSS` | B | — | `GK:331`; KK §4 |
| `thue_suat` | Thuế suất hoặc chế độ thuế theo nguồn | Chuỗi theo catalog thuế | B | % hoặc mã chế độ thuế | `DA:33`; `GK:332` |
| `gia_dat_tru_m2` | Giá đất được trừ trên m² nếu có căn cứ | `chung.tien` | T | VND/USD trên m² | `DA:127`; KK §4 |
| `tong_truoc_vat` | Tổng giá trị trước VAT | `chung.tien` hoặc `null` | B; phải xác định trước in/hiệu lực | VND/USD | CD-024; TL45 §9 |
| `tong_vat` | Tổng VAT của hợp đồng/báo giá | `chung.tien` hoặc `null` | B; phải xác định trước in/hiệu lực | VND/USD | CD-024 |
| `tong_gom_vat` | Tổng tiền gồm VAT | `chung.tien` hoặc `null` | B; phải xác định trước in/hiệu lực | VND/USD | CD-024 |
| `ty_gia` | Tỷ giá được ghim nếu dùng ngoại tệ | Object: `cap` chuỗi, `gia_tri`=`chung.thap_phan`, `ngay`=`chung.ngay`, `nguoi_nhap` chuỗi | ĐK: có quy đổi ngoại tệ; cả bốn trường bắt buộc | VND/USD; ngày | TL45 §2 BG-12; TL42 §14 |

`thue_suat` giữ phân biệt thuế suất `0`, `KCT`, `KKKNT`; không tự đổi hai chế độ sau thành thuế suất 0.

**`DongLichCrm`:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `nghia_vu_id` | Tên duy nhất của ID dòng đợt cụ thể trong phiên bản; tại báo giá là ID dự kiến, chưa có hiệu lực | `chung.id` | B | — | Ánh xạ `GK:279`; khi đã hình thành dùng ID `master.lich_thu` tương ứng; TK §6; CSDL §6.2 |
| `module_nghia_vu` | Chủ đợt nghĩa vụ | Hằng `CRM` | B trong hợp đồng; bỏ ở báo giá dự kiến | — | CSDL §3.6, §6.2 |
| `loai_nghia_vu` | Loại đợt bán dùng khi nối tiền | Hằng `lich_thu` | B trong hợp đồng; bỏ ở báo giá dự kiến | — | CSDL §3.6, §6.2; tên lịch nguồn |
| `khoa_nghia_vu` | Khóa đợt ổn định qua các phiên bản, chỉ để theo dõi/đối chiếu; không dùng làm đích liên kết tiền (đích luôn là bộ ba với `nghia_vu_id` của đúng phiên bản) | `chung.chuoi` | B trong hợp đồng; bỏ ở báo giá | — | CRM:419–422; CSDL §6.2 |
| `loai_khoan` | Loại khoản của lịch; bản đầu chỉ giá bán, dành khả năng mở rộng tương thích về sau | `chung.chuoi`, bản đầu chỉ nhận `GIA_BAN` | B | — | TK §6; CD-038 câu 1A |
| `lan` | Thứ tự đợt thanh toán | Integer dương | B | lần | TL45 §2 BG-01 |
| `gia_tri_nhap` | Giá trị gốc người dùng nhập: % hoặc tiền | `chung.gia_tri` | B | % hoặc VND/USD | TL45 §8 BG-20 |
| `ty_le` | Tỷ lệ tính trên giá trước VAT | `chung.thap_phan` | B | % | CD-024 |
| `la_dat_coc` | Dòng được đánh dấu đặt cọc | Boolean | B | — | CD-024 |
| `gia_tri_gom_vat` | Số tiền phải thanh toán tại đợt, đã xử lý dồn VAT cọc | `chung.tien` | B | VND/USD | CD-024 |
| `trong_do_vat` | VAT thực thu trong tiền đợt này | `chung.tien` | B | VND/USD | CD-024 |
| `moc` | Ngày hoặc sự kiện xác định thời điểm thanh toán | Object theo bảng dưới | B | — | CD-006/007; `GK:278` |
| `ghi_chu` | Nội dung ghi chú của đợt | `chung.chuoi` | T | — | TL45 §9 BG-28 |

**Các trường trong `moc`:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `loai` | Mốc ngày cố định hoặc sự kiện | Enum `NGAY`, `SU_KIEN` | B | — | `GK:278` |
| `ngay` | Ngày cố định của đợt | `chung.ngay` | ĐK: `NGAY` | ngày | `GK:283` |
| `su_kien` | Mã sự kiện cơ sở đã resolve từ catalog, không nhét số ngày vào mã | Chuỗi catalog CRM | ĐK: `SU_KIEN` | — | Ánh xạ mã legacy tại `GK:78`–`106` |
| `so_ngay_sau_moc` | Số ngày sau mốc thực tế để xác định hạn | Integer ≥ 0 | ĐK: `SU_KIEN`; 0 nghĩa ngay ngày mốc | ngày | Tách độ lệch từ `GK:78`–`106`; CD-007 |
| `moc_du_an_id` | Tham chiếu mốc riêng của đúng dự án | `chung.id` | ĐK: dùng mốc riêng dự án | — | `SQL-MOC:18`–`25` |
| `lan_moc` | Phiên bản mốc làm căn cứ cho ảnh chụp này | Integer dương | ĐK: dùng mốc riêng dự án | lần | `SQL-MOC:29`–`43`; KK §3 |
| `ngay_du_kien` | Ngày dự kiến của mốc | `chung.ngay` | ĐK: mốc riêng đã khai | ngày | CD-007 |
| `ngay_thuc_te` | Ngày mốc thực sự xảy ra | `chung.ngay` hoặc `null` | ĐK: mốc riêng; chưa xảy ra là `null` | ngày | CD-007 |
| `han` | Ngày đến hạn đã xác định | `chung.ngay` hoặc `null` | B | ngày | CD-007; TK §6 |

**Quy tắc nghiệp vụ đã chốt:**

1. Lịch nghĩa vụ bản đầu chỉ gồm giá bán `loai_khoan=GIA_BAN`, tổng tỷ lệ bằng 100%; tỷ lệ tính trên tổng giá bán trước VAT. Phí theo dõi riêng, không cộng vào các tổng này (CD-038 câu 1A).
2. **CD-038 câu 2B:** cho phép cọc ở đợt cuối hoặc nhiều đợt cọc, không ràng buộc cọc ở dòng 1. Theo thứ tự `lan`, VAT phân bổ của mỗi đợt cọc dồn vào đợt **không cọc gần nhất phía sau**; nếu không còn đợt không cọc phía sau thì dồn ngược về đợt **không cọc gần nhất phía trước**. Nhiều đợt cọc cùng đích thì cộng toàn bộ VAT vào đích đó. Đợt cọc luôn có `trong_do_vat=0`. **Lịch toàn đợt cọc → lỗi**, kể cả lịch một dòng cọc; chặn in/hiệu lực. Lịch một dòng không cọc vẫn hợp lệ khi đủ các điều kiện khác.
3. `gia_tri_nhap` giữ ô gốc; bên nhận không suy lại tỷ lệ bằng cách chia tiền đợt cho tổng gồm VAT.
4. Mốc chưa có ngày thực tế: hiển thị dự kiến, **không đếm quá hạn**. Qua ngày dự kiến sinh việc chờ chỉnh ngày; khi có thực tế mới tính hạn theo thực tế cộng số ngày đã khai.
5. Phiên bản đã duyệt nhưng chưa tới ngày hiệu lực không được coi là phiên bản đang hiệu lực. Lịch và tiền đã nối không tự chứng minh doanh thu hoặc nghĩa vụ VAT ghi sổ của M3.

**Bất biến tiền sau dồn VAT (áp dụng cả `bao_gia`/`hop_dong_ban`):** gọi N là tổng giá bán trước VAT, V là tổng VAT đã tính theo căn cứ thuế, G=N+V. Với tỷ lệ pᵢ, Σpᵢ=100, phân bổ Bᵢ từ Npᵢ/100 và Vᵢ từ Vpᵢ/100; làm tròn half-up theo thang tiền chung, VND scale 0; dòng cuối nhận phần dư của B và V để ΣB=N, ΣVᵢ=V. Sau đó mới dồn VAT: gọi d(c) là đích không cọc theo quy tắc 2; T꜀=0 tại cọc, Tⱼ=Vⱼ+ΣV꜀ với d(c)=j tại đợt không cọc. Tiền thu Aᵢ=Bᵢ+Tᵢ; `gia_tri_gom_vat=Aᵢ`, `trong_do_vat=Tᵢ`. Bắt buộc ΣT=V, ΣA=G, Σ(A−T)=N; mọi B/V/T/A không âm và Tᵢ≤Aᵢ. Dòng cuối là cọc vẫn nhận phần dư VAT phân bổ trước khi chuyển phần VAT đó tới đích không cọc; không gán VAT thực thu cho cọc để bù sai số. Kết quả ngoài miền → lỗi, không sửa đầu vào để che lệch.

**Định danh khi nối tiền:** chỉ dùng `nghia_vu_id`, không công bố thêm alias `dong_id`, `khoa_nghia_vu` hay `lich_thu_id`. Bộ ba chuẩn là `(module_nghia_vu=CRM, loai_nghia_vu=lich_thu, nghia_vu_id)`; ghim thêm `ban.id` và `ban.ma_bam`. ID báo giá là dự kiến; khi nguồn ghi dòng nghĩa vụ phải công bố đúng ID dòng đã lưu, không giả định UUID dự kiến bằng UUID lịch thu. Nguồn CRM tạo dòng mới cho phiên bản mới (CRM:660); UUID dòng cũ giữ nguyên cho lịch sử, không tự coi UUID dòng là khóa logic xuyên phiên bản. Resolver chủ CRM dùng quan hệ thay thế/khóa logic legacy nội bộ để kiểm cả chuỗi tiền đã nối, không công bố thêm alias ID; tách/gộp đợt phải xác lập ID mới và xử lý tiền đã nối, không tái dùng ID khác nghĩa. Bên nhận sự kiện §5.1 kiểm đúng bộ ba/phiên bản/hash qua liên kết Core và contract CRM trong transaction theo D §6.2.

**Phí theo CD-038 câu 1A:** lịch nghĩa vụ hợp đồng bán/báo giá bản đầu chỉ có giá bán chia %, Σ%=100 cho giá bán. `phi` theo dõi riêng và giữ nguyên khi chuyển Soạn, không suy thành nghĩa vụ của lịch giá bán và không bỏ khỏi dữ liệu. Bổ sung phí vào nghiệp vụ về sau phải tương thích, không phá phiên bản đã công bố: giữ nghĩa tổng/%/ID giá bán và cơ sở tính/VAT từng khoản, có ánh xạ và tiếp tục phục vụ bản cũ nếu cần phiên bản mới. Hai câu 1A/2B đã được Anh chốt, không còn là điểm chờ duyệt.

#### Ba ví dụ JSON DEMO theo CD-038 câu 2B

Các JSON sau là **trích đoạn các trường tính tiền của `lich_thanh_toan`**, áp dụng cho cả hai contract; khi công bố phải ghép đủ vỏ, ID và mốc như ví dụ đầy đủ bên dưới. Cả ba dùng N=1.000.000.000 VND, không có phần đất trừ/miễn thuế, thuế suất 10%: V=1.000.000.000×10%=100.000.000 VND; G=1.100.000.000 VND; phí tách riêng.

**Cọc đợt cuối — p=30/50/20%:** B=300/500/200 triệu; VAT phân bổ=30/50/20 triệu. Cọc dòng 3 không còn đích phía sau nên 20 triệu chuyển về dòng 2: T=30/(50+20)/0=30/70/0 triệu; A=330/570/200 triệu. Σp=100%; ΣT=100 triệu; ΣA=1.100 triệu; Σ(A−T)=1.000 triệu.

```json
{
  "lich_thanh_toan": [
    {"lan": 1, "loai_khoan": "GIA_BAN", "ty_le": "30", "la_dat_coc": false, "gia_tri_gom_vat": {"gia_tri": "330000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "30000000", "don_vi_tien": "VND"}},
    {"lan": 2, "loai_khoan": "GIA_BAN", "ty_le": "50", "la_dat_coc": false, "gia_tri_gom_vat": {"gia_tri": "570000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "70000000", "don_vi_tien": "VND"}},
    {"lan": 3, "loai_khoan": "GIA_BAN", "ty_le": "20", "la_dat_coc": true, "gia_tri_gom_vat": {"gia_tri": "200000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "0", "don_vi_tien": "VND"}}
  ]
}
```

**Hai đợt cọc liền nhau — p=20/30/50%:** B=200/300/500 triệu; VAT phân bổ=20/30/50 triệu. Cọc dòng 1 và 2 cùng dồn về dòng 3: T=0/0/(50+20+30)=0/0/100 triệu; A=200/300/600 triệu. Σp=100%; ΣT=100 triệu; ΣA=1.100 triệu; Σ(A−T)=1.000 triệu.

```json
{
  "lich_thanh_toan": [
    {"lan": 1, "loai_khoan": "GIA_BAN", "ty_le": "20", "la_dat_coc": true, "gia_tri_gom_vat": {"gia_tri": "200000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "0", "don_vi_tien": "VND"}},
    {"lan": 2, "loai_khoan": "GIA_BAN", "ty_le": "30", "la_dat_coc": true, "gia_tri_gom_vat": {"gia_tri": "300000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "0", "don_vi_tien": "VND"}},
    {"lan": 3, "loai_khoan": "GIA_BAN", "ty_le": "50", "la_dat_coc": false, "gia_tri_gom_vat": {"gia_tri": "600000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "100000000", "don_vi_tien": "VND"}}
  ]
}
```

**Cọc xen giữa — p=10/30/20/40%:** B=100/300/200/400 triệu; VAT phân bổ=10/30/20/40 triệu. Cọc dòng 1 dồn về dòng 2; cọc dòng 3 dồn về dòng 4 (ưu tiên phía sau dù dòng 2 cũng không cọc): T=0/(30+10)/0/(40+20)=0/40/0/60 triệu; A=100/340/200/460 triệu. Σp=100%; ΣT=100 triệu; ΣA=1.100 triệu; Σ(A−T)=1.000 triệu.

```json
{
  "lich_thanh_toan": [
    {"lan": 1, "loai_khoan": "GIA_BAN", "ty_le": "10", "la_dat_coc": true, "gia_tri_gom_vat": {"gia_tri": "100000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "0", "don_vi_tien": "VND"}},
    {"lan": 2, "loai_khoan": "GIA_BAN", "ty_le": "30", "la_dat_coc": false, "gia_tri_gom_vat": {"gia_tri": "340000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "40000000", "don_vi_tien": "VND"}},
    {"lan": 3, "loai_khoan": "GIA_BAN", "ty_le": "20", "la_dat_coc": true, "gia_tri_gom_vat": {"gia_tri": "200000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "0", "don_vi_tien": "VND"}},
    {"lan": 4, "loai_khoan": "GIA_BAN", "ty_le": "40", "la_dat_coc": false, "gia_tri_gom_vat": {"gia_tri": "460000000", "don_vi_tien": "VND"}, "trong_do_vat": {"gia_tri": "60000000", "don_vi_tien": "VND"}}
  ]
}
```

#### Ví dụ JSON DEMO

```json
{
  "contract": "hop_dong_ban.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000008"],
  "hop_dong_id": "10000000-0000-4000-8000-000000000001",
  "ma_noi_bo": "DEMO-HD-001",
  "so_hop_dong": "DEMO/HD/001",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000002",
  "doi_tuong_id": "10000000-0000-4000-8000-000000000003",
  "du_an_id": "10000000-0000-4000-8000-000000000004",
  "lo_can_id": "10000000-0000-4000-8000-000000000005",
  "loai_hinh_id": "10000000-0000-4000-8000-000000000006",
  "trang_thai_giao_ket": "HIEU_LUC",
  "ban": {
    "id": "10000000-0000-4000-8000-000000000007",
    "so": 1,
    "loai": "GOC",
    "ngay_hieu_luc": "2026-10-30",
    "ma_bam": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "kiem_boi": "DEMO_KE_TOAN",
    "kiem_luc": "2026-10-30T02:00:00Z",
    "duyet_boi": "DEMO_CFO",
    "duyet_luc": "2026-10-30T03:00:00Z"
  },
  "ngay_ky": "2026-10-30",
  "tham_so": [{
    "ma": "gia_tri_hop_dong_demo",
    "ten": "DEMO giá trị trước VAT",
    "gia_tri_nguon": {"kieu": "tien", "gia_tri": "1000000000", "don_vi_tien": "VND"},
    "gia_tri_hieu_luc": {"kieu": "tien", "gia_tri": "1000000000", "don_vi_tien": "VND"},
    "don_vi": "VND",
    "dieu_khoan": "DEMO Điều 3",
    "dan_chung": [{
      "vi_tri": {
        "tep_id": "10000000-0000-4000-8000-000000000008",
        "dinh_vi": "DEMO/dieu_3",
        "trang": 1
      },
      "trich_dan": "DEMO giá trị trước VAT là 1.000.000.000 VND."
    }],
    "nguon": "TRICH_6",
    "trang_thai_can_cu": "CO_CAN_CU"
  }],
  "gia_thue": {
    "co_so_thue": "NET",
    "thue_suat": "10",
    "tong_truoc_vat": {"gia_tri": "1000000000", "don_vi_tien": "VND"},
    "tong_vat": {"gia_tri": "100000000", "don_vi_tien": "VND"},
    "tong_gom_vat": {"gia_tri": "1100000000", "don_vi_tien": "VND"}
  },
  "phi": [],
  "lich_thanh_toan": [
    {
      "nghia_vu_id": "10000000-0000-4000-8000-000000000021",
      "module_nghia_vu": "CRM",
      "loai_nghia_vu": "lich_thu",
      "khoa_nghia_vu": "DEMO_THU_1",
      "loai_khoan": "GIA_BAN",
      "lan": 1,
      "gia_tri_nhap": {"kieu": "so", "gia_tri": "10", "don_vi": "%"},
      "ty_le": "10",
      "la_dat_coc": true,
      "gia_tri_gom_vat": {"gia_tri": "100000000", "don_vi_tien": "VND"},
      "trong_do_vat": {"gia_tri": "0", "don_vi_tien": "VND"},
      "moc": {"loai": "NGAY", "ngay": "2026-10-30", "han": "2026-10-30"},
      "ghi_chu": "DEMO đặt cọc"
    },
    {
      "nghia_vu_id": "10000000-0000-4000-8000-000000000022",
      "module_nghia_vu": "CRM",
      "loai_nghia_vu": "lich_thu",
      "khoa_nghia_vu": "DEMO_THU_2",
      "loai_khoan": "GIA_BAN",
      "lan": 2,
      "gia_tri_nhap": {"kieu": "so", "gia_tri": "30", "don_vi": "%"},
      "ty_le": "30",
      "la_dat_coc": false,
      "gia_tri_gom_vat": {"gia_tri": "340000000", "don_vi_tien": "VND"},
      "trong_do_vat": {"gia_tri": "40000000", "don_vi_tien": "VND"},
      "moc": {
        "loai": "SU_KIEN",
        "su_kien": "DAM-10000000-0000-4000-8000-000000000031",
        "so_ngay_sau_moc": 0,
        "moc_du_an_id": "10000000-0000-4000-8000-000000000031",
        "lan_moc": 1,
        "ngay_du_kien": "2026-12-01",
        "ngay_thuc_te": null,
        "han": null
      },
      "ghi_chu": "DEMO gồm VAT của đợt này và VAT cọc"
    },
    {
      "nghia_vu_id": "10000000-0000-4000-8000-000000000023",
      "module_nghia_vu": "CRM",
      "loai_nghia_vu": "lich_thu",
      "khoa_nghia_vu": "DEMO_THU_3",
      "loai_khoan": "GIA_BAN",
      "lan": 3,
      "gia_tri_nhap": {"kieu": "so", "gia_tri": "60", "don_vi": "%"},
      "ty_le": "60",
      "la_dat_coc": false,
      "gia_tri_gom_vat": {"gia_tri": "660000000", "don_vi_tien": "VND"},
      "trong_do_vat": {"gia_tri": "60000000", "don_vi_tien": "VND"},
      "moc": {"loai": "NGAY", "ngay": "2027-03-01", "han": "2027-03-01"},
      "ghi_chu": "DEMO đợt cuối"
    }
  ],
  "tep_nguon": {
    "contract": "tham_chieu_tep.v1",
    "phien_ban": "1.0.0",
    "tep_id": "10000000-0000-4000-8000-000000000008",
    "ten_tep": "DEMO-hop-dong.pdf",
    "mime": "application/pdf",
    "kich_thuoc": 12345,
    "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "het_han_luc": null
  }
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** catalog và mapping `trang_thai_giao_ket`, `ban.loai`, trạng thái kiểm/duyệt giữa hai luồng; catalog tham số theo loại hợp đồng; quy tắc phụ lục tác động nghĩa vụ đã có tiền; bên đọc bổ sung. Các nhãn trong ví dụ minh họa thiết kế đích, chưa xác nhận là một catalog thống nhất đã triển khai.

### 2. `bao_gia.v1`

**Mục đích:** Cung cấp báo giá tại một revision xác định, gồm giá, thuế, phí và lịch dự kiến. Khi chuyển sang soạn hợp đồng, giữ nguyên lịch, đánh dấu cọc và kết quả VAT của revision được chọn.

**Module sở hữu:** CRM. **Module được đọc:** CRM; module ngoài CRM chờ Anh xác định. **Loại:** dữ liệu công bố.

#### Bảng trường

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `contract` | Mã cấu trúc | Hằng `bao_gia.v1` | B | — | CD-031 |
| `phien_ban` | Phiên bản cấu trúc | Hằng `1.0.0` | B | — | DL §2 |
| `revision` | Revision báo giá được công bố | Kiểu `revision` của `chung.vo_noi_dung` | B | lần | `GK:1080`; TL45 §8 |
| `nguon_tep_ids` | Tệp nguồn/ảnh chụp báo giá nhập tay đã lưu Core | Mảng `chung.id`, ≥ 1, không trùng | B | — | DL §3; NV-CHUNG |
| `bao_gia_id` | Định danh báo giá | `chung.id` | B | — | `GK:789` |
| `so_bao_gia` | Số báo giá giao khách | `chung.chuoi` | ĐK: đã in | — | TL42 §6 |
| `phap_nhan_id` | Pháp nhân lập báo giá | `chung.id` | B | — | TL42 §6 |
| `ngay_lap` | Ngày lập | `chung.ngay` | B | ngày | TL42 §6 |
| `nguoi_lap` | Người lập báo giá | `chung.chuoi` | B | — | TL42 §6 |
| `doi_tuong_id` | Khách hàng hoặc đối tượng dự thảo qua `doi_tuong.v1` | `chung.id` hoặc `null` | B; được thiếu khi lưu nháp | — | TL45 BG-08; `GK:326` |
| `du_an_id` | Dự án qua `du_an.v1` | `chung.id` hoặc `null` | B; được thiếu khi lưu nháp | — | `GK:321` |
| `lo_can_id` | Lô/căn được chọn | `chung.id` | ĐK: báo giá theo lô/căn | — | `GK:339`; TL45 BG-09 |
| `loai_hinh_id` | Profile loại hình của báo giá | `chung.id` | B | — | `GK:320` |
| `trang_thai` | Nháp, đã in, đã chuyển, hủy hoặc hết hạn | Chuỗi catalog CRM | B; mã hóa catalog chờ Anh | — | TL42 §6 |
| `nguon_lich` | Theo dự án hoặc theo khách | Enum `DU_AN`, `KHACH` | B | — | `GK:323`; TL45 BG-10 |
| `phien_ban_du_an_id` | Phiên bản cấu hình dự án dùng để lập báo giá | `chung.id` | ĐK: lấy chuẩn từ dự án | — | `GK:926`; KK §3 |
| `ma_bam_du_an` | Hash ảnh chụp cấu hình dự án đã ghim | `chung.sha256` | ĐK: đi cùng `phien_ban_du_an_id` | — | CSDL §6.1; `GK:926` |
| `gia_thue` | Giá, thuế và tỷ giá | `GiaCrm` tại §1 | B | VND/USD | CD-024 |
| `phi` | Các phí áp dụng, giữ cơ sở tính riêng | Mảng `PhiCrm` tại §3 | B; có thể rỗng | Theo dòng | `GK:341`–`343`; TL42 §6 |
| `lich_thanh_toan` | Lịch dự kiến | Mảng `DongLichCrm` tại §1; có `nghia_vu_id` dự kiến, chưa có bộ ba đích nối hiệu lực | B; có thể chưa đủ khi nháp | — | TL45 §8–§9 |

Resolver liên kết tiền từ chối mọi `nghia_vu_id` không đi kèm bộ ba của hợp đồng hiệu lực; ID báo giá chỉ được dùng lại khi chuyển Soạn hợp đồng.
| `het_han` | Ngày hết hạn báo giá nếu có | `chung.ngay` | T | ngày | `GK:335` |
| `ghi_chu` | Ghi chú chung | `chung.chuoi` | T | — | `GK:336` |

**Quy tắc:** áp dụng cùng quy tắc VAT/lịch và bất biến tiền tại §1 theo CD-038 câu 1A/2B; lịch chỉ giá bán chia %, phí theo dõi riêng. Lưu nháp được phép thiếu dữ liệu; trước in phải đủ căn cứ tính tiền, tổng tỷ lệ giá bán 100% và tỷ giá khi cần; lịch toàn cọc → lỗi. Cho phép cọc cuối/nhiều cọc, dồn VAT tới đợt không cọc gần nhất phía sau, hết phía sau thì về đợt không cọc gần nhất phía trước. Chọn dự án nạp tiến độ chuẩn; sửa lịch phải thể hiện nguồn theo khách. Bản in và chuyển Soạn phải giữ sáu cột lịch theo CD-024 cùng cờ cọc/tiền/VAT đã tính.

#### Ví dụ JSON DEMO

```json
{
  "contract": "bao_gia.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["20000000-0000-4000-8000-000000000008"],
  "bao_gia_id": "20000000-0000-4000-8000-000000000001",
  "so_bao_gia": "DEMO/BG/001",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000002",
  "ngay_lap": "2026-10-30",
  "nguoi_lap": "DEMO_BAN_HANG",
  "doi_tuong_id": "10000000-0000-4000-8000-000000000003",
  "du_an_id": "10000000-0000-4000-8000-000000000004",
  "lo_can_id": "10000000-0000-4000-8000-000000000005",
  "loai_hinh_id": "10000000-0000-4000-8000-000000000006",
  "trang_thai": "NHAP",
  "nguon_lich": "DU_AN",
  "phien_ban_du_an_id": "30000000-0000-4000-8000-000000000002",
  "ma_bam_du_an": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "gia_thue": {
    "don_gia": {"gia_tri": "10000000", "don_vi_tien": "VND"},
    "dien_tich": "100",
    "co_so_thue": "NET",
    "thue_suat": "10",
    "gia_dat_tru_m2": {"gia_tri": "0", "don_vi_tien": "VND"},
    "tong_truoc_vat": {"gia_tri": "1000000000", "don_vi_tien": "VND"},
    "tong_vat": {"gia_tri": "100000000", "don_vi_tien": "VND"},
    "tong_gom_vat": {"gia_tri": "1100000000", "don_vi_tien": "VND"}
  },
  "phi": [],
  "lich_thanh_toan": [
    {
      "nghia_vu_id": "20000000-0000-4000-8000-000000000011",
      "loai_khoan": "GIA_BAN",
      "lan": 1,
      "gia_tri_nhap": {"kieu": "so", "gia_tri": "10", "don_vi": "%"},
      "ty_le": "10",
      "la_dat_coc": true,
      "gia_tri_gom_vat": {"gia_tri": "100000000", "don_vi_tien": "VND"},
      "trong_do_vat": {"gia_tri": "0", "don_vi_tien": "VND"},
      "moc": {"loai": "NGAY", "ngay": "2026-10-30", "han": "2026-10-30"},
      "ghi_chu": "DEMO cọc"
    },
    {
      "nghia_vu_id": "20000000-0000-4000-8000-000000000012",
      "loai_khoan": "GIA_BAN",
      "lan": 2,
      "gia_tri_nhap": {"kieu": "tien", "gia_tri": "340000000", "don_vi_tien": "VND"},
      "ty_le": "30",
      "la_dat_coc": false,
      "gia_tri_gom_vat": {"gia_tri": "340000000", "don_vi_tien": "VND"},
      "trong_do_vat": {"gia_tri": "40000000", "don_vi_tien": "VND"},
      "moc": {
        "loai": "SU_KIEN",
        "su_kien": "DAM-10000000-0000-4000-8000-000000000031",
        "so_ngay_sau_moc": 0,
        "moc_du_an_id": "10000000-0000-4000-8000-000000000031",
        "lan_moc": 1,
        "ngay_du_kien": "2026-12-01",
        "ngay_thuc_te": null,
        "han": null
      },
      "ghi_chu": "DEMO nhập tiền, máy suy tỷ lệ 30%"
    },
    {
      "nghia_vu_id": "20000000-0000-4000-8000-000000000013",
      "loai_khoan": "GIA_BAN",
      "lan": 3,
      "gia_tri_nhap": {"kieu": "so", "gia_tri": "60", "don_vi": "%"},
      "ty_le": "60",
      "la_dat_coc": false,
      "gia_tri_gom_vat": {"gia_tri": "660000000", "don_vi_tien": "VND"},
      "trong_do_vat": {"gia_tri": "60000000", "don_vi_tien": "VND"},
      "moc": {"loai": "NGAY", "ngay": "2027-03-01", "han": "2027-03-01"},
      "ghi_chu": "DEMO đợt cuối"
    }
  ],
  "het_han": "2026-11-15",
  "ghi_chu": "DEMO báo giá minh họa CD-024"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** mã catalog `trang_thai`; chi tiết suy ngược ngoài quy tắc đã chốt. Phạm vi giá bán/phí và VAT cọc đã chốt theo CD-038 câu 1A/2B tại §1; công thức triển khai/suy ngược tại KK §4 vẫn là đề xuất ở phần ngoài quy tắc đó. Mã hiện tại còn phân biệt dữ liệu cũ và dữ liệu mới có tiền chính VND (`GK:391`–`396`); không tự đổi tiền tệ hoặc tính lại báo giá cũ khi chuyển đổi.

### 3. `du_an_dang_ban.v1`

**Mục đích:** Cung cấp cấu hình bán hàng của một dự án tại phiên bản xác định, bao gồm sáu khối: thông tin chung, giá & thuế, phí, mốc, tiến độ chuẩn và lô/căn. Báo giá dùng cấu hình này để nạp mặc định và giữ căn cứ phiên bản.

**Module sở hữu:** CRM; định danh dự án dùng lại `du_an.v1`. **Module được đọc:** CRM; module ngoài CRM chờ Anh xác định. **Loại:** dữ liệu công bố.

#### Bảng trường

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `contract` | Mã cấu trúc | Hằng `du_an_dang_ban.v1` | B | — | CD-031 |
| `phien_ban` | Phiên bản cấu trúc | Hằng `1.0.0` | B | — | DL §2 |
| `revision` | Lần sửa nội dung công bố | Kiểu `revision` của `chung.vo_noi_dung` | B | lần | DL §3 |
| `nguon_tep_ids` | Tệp nguồn/ảnh chụp cấu hình nhập tay đã lưu Core | Mảng `chung.id`, ≥ 1, không trùng | B | — | DL §3; NV-CHUNG |
| `du_an_dang_ban_id` | ID hồ sơ bán hàng của dự án | `chung.id` | B | — | `SQL-DA:61` |
| `du_an_id` | Tham chiếu `du_an.v1` | `chung.id` hoặc `null` | B và phải khác `null` tại cấu hình dự án | — | `SQL-DA:64` |
| `phap_nhan_id` | Pháp nhân của dự án | `chung.id` | B | — | `SQL-DA:63` |
| `phien_ban_du_an_id` | ID phiên bản tổng hợp sáu khối | `chung.id` | B trong thiết kế đích; cách tổng hợp chờ Anh | — | CD-023; KK §3 |
| `so_phien_ban` | Số phiên bản nghiệp vụ tổng hợp | Integer dương | B trong thiết kế đích | phiên bản | CD-023 |
| `ma_bam` | Mã băm ảnh chụp cấu hình được công bố | `chung.sha256` | B | — | `GK:926`; KK §3 |
| `dang_ban` | Dự án đang mở hay ngừng bán | Boolean | B | — | `SQL-DA:100` |
| `loai_hinh_id` | Loại hình/profile bán hàng | `chung.id` | B | — | `SQL-DA:105` |
| `thong_tin` | Vị trí, mô tả bổ sung của cấu hình bán | Object: `vi_tri`, `mo_ta` đều `chung.chuoi`, T | B; được rỗng | — | `DA:121`–`122`; CD-023 |
| `gia_thue` | Giá niêm yết và thuế mặc định | Object theo bảng dưới | B | — | CD-023 |
| `phi` | Phí tiêu chuẩn của dự án | Mảng `PhiCrm` | B; được rỗng | Theo dòng | CD-023; `SQL-DA:123` |
| `moc` | Mốc riêng của dự án | Mảng `MocDuAnCrm` | B; được rỗng | — | CD-006/007 |
| `tien_do` | Một tiến độ chuẩn duy nhất | Mảng theo bảng dưới | B; khi đã khai tổng % phải bằng 100 | % | CD-022 |
| `lo_can` | Các lô/căn và trạng thái | Mảng theo bảng dưới | B; được rỗng khi chưa khai | — | CD-023; `SQL-DA:137` |

**Các trường trong `gia_thue`:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `don_gia_niem_yet` | Đơn giá niêm yết, chưa gồm VAT | `chung.tien` hoặc `null` | B; chưa khai được `null` | VND/USD trên m² | `DA:123`; `DA:273` |
| `thue_suat` | Thuế mặc định, giữ riêng các chế độ thuế | Chuỗi catalog `10`, `8`, `5`, `0`, `KCT`, `KKKNT` | B | % hoặc mã chế độ thuế | `DA:33`–`34`; `SQL-DA:106` |
| `gia_dat_tru_m2` | Giá đất được trừ trên m² | `chung.tien` | B | VND/USD trên m² | `DA:127`–`134` |

**`PhiCrm` — mỗi dòng phí:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `ten` | Tên phí có dấu, khoảng trắng | `chung.chuoi` | B | — | CD-022; `DA:153` |
| `loai` | Phí bảo trì, sử dụng hoặc khác | Enum `BAO_TRI`, `SU_DUNG`, `KHAC` | B | — | `DA:35` |
| `muc` | Mức phí và tiền tệ | `chung.tien` | B | VND/USD | `DA:155`–`157` |
| `don_vi_tinh` | Đơn vị áp dụng mức phí | Enum `M2_THANG`, `M2_NAM`, `LAN` | B | m²/tháng, m²/năm, lần | `DA:36` |
| `co_so_tinh` | Diễn giải cơ sở tính phí | `chung.chuoi` | T | — | `DA:158` |
| `co_so_gia_tri` | Cơ sở VAT của mức phí | Enum `TRUOC_VAT`, `GOM_VAT`, `CHUA_RO` | B; nguồn chưa đủ là `CHUA_RO` | — | Yêu cầu cơ sở tiền T §2.2; không suy từ `loai` |

**`MocDuAnCrm` — mỗi mốc riêng:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `id` | ID mốc riêng dự án | `chung.id` | B | — | `SQL-MOC:19` |
| `lan` | Phiên bản mốc | Integer dương | B | lần | `SQL-MOC:32` |
| `ten` | Tên mốc do dự án khai | `chung.chuoi` | B | — | CD-006; `SQL-MOC:35` |
| `ten_tat` | Tên tắt phục vụ tìm/chọn | `chung.chuoi` | T | — | `SQL-MOC:36` |
| `ngay_du_kien` | Ngày dự kiến hoàn thành | `chung.ngay` | B | ngày | CD-007 |
| `ngay_thuc_te` | Ngày đã xảy ra | `chung.ngay` hoặc `null` | B | ngày | CD-007 |
| `dang_dung` | Mốc còn được dùng cho cấu hình mới | Boolean | B | — | `SQL-MOC:39` |

**Mỗi dòng `tien_do` và `lo_can`:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Yêu cầu | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `tien_do[].lan` | Thứ tự thanh toán chuẩn | Integer dương | B | lần | CD-022 |
| `tien_do[].ty_le` | Tỷ lệ của đợt chuẩn | `chung.thap_phan` | B | % | CD-022 |
| `tien_do[].moc` | Mốc cơ bản hoặc mốc riêng dự án | Nhóm `moc` tại §1 | B | ngày/sự kiện | CD-006/007/022 |
| `tien_do[].ghi_chu` | Ghi chú của đợt | `chung.chuoi` | T | — | CD-022 |
| `lo_can[].id` | ID ổn định lô/căn | `chung.id` | B | — | `SQL-DA:138` |
| `lo_can[].lan` | Phiên bản thông tin lô/căn | Integer dương | B | lần | `SQL-DA:151` |
| `lo_can[].ma` | Mã lô/căn nghiệp vụ | `chung.chuoi` | B | — | `SQL-DA:141` |
| `lo_can[].dien_tich` | Diện tích lớn hơn 0 | `chung.thap_phan` | B | m² | `DA:179` |
| `lo_can[].trang_thai` | Còn trống, giữ chỗ, đã bán/cho thuê, không bán | Enum `CON_TRONG`, `GIU_CHO`, `DA_BAN`, `KHONG_BAN` | B | — | `DA:37` |
| `lo_can[].ghi_chu` | Ghi chú của lô/căn | `chung.chuoi` | T | — | `DA:181` |

**Quy tắc:** tiến độ dự án chỉ có **% + mốc + ghi chú**, không có số tiền; một dự án có một tiến độ chuẩn, không đưa `giai_doan_g7` thành trường người dùng phải khai. Mốc riêng không đưa vào danh mục mốc chung. Lưu sáu khối trong một lượt tạo một phiên bản tổng hợp; sửa bắt buộc một ghi chú thay đổi chung và audit ai/lúc nào/cũ → mới. Đây là quy tắc lệnh ghi, không biến ghi chú thành trường bắt buộc của mọi lần đọc công bố.

Sao chép dự án/mẫu phải bỏ lô/căn, tên/mã dự án nguồn và ngày thực tế; mốc mới có ID mới và lịch phải remap đúng. Nhật ký giữ dự án nguồn và phiên bản nguồn; mẫu do người dùng lưu, không gắn cứng nội dung theo loại.

#### Ví dụ JSON DEMO

```json
{
  "contract": "du_an_dang_ban.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["30000000-0000-4000-8000-000000000008"],
  "du_an_dang_ban_id": "30000000-0000-4000-8000-000000000001",
  "du_an_id": "10000000-0000-4000-8000-000000000004",
  "phap_nhan_id": "10000000-0000-4000-8000-000000000002",
  "phien_ban_du_an_id": "30000000-0000-4000-8000-000000000002",
  "so_phien_ban": 1,
  "ma_bam": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "dang_ban": true,
  "loai_hinh_id": "10000000-0000-4000-8000-000000000006",
  "thong_tin": {
    "vi_tri": "DEMO khu dự án",
    "mo_ta": "DEMO cấu hình bán hàng minh họa"
  },
  "gia_thue": {
    "don_gia_niem_yet": {"gia_tri": "10000000", "don_vi_tien": "VND"},
    "thue_suat": "10",
    "gia_dat_tru_m2": {"gia_tri": "0", "don_vi_tien": "VND"}
  },
  "phi": [{
    "ten": "DEMO phí sử dụng",
    "loai": "SU_DUNG",
    "muc": {"gia_tri": "5000", "don_vi_tien": "VND"},
    "don_vi_tinh": "M2_THANG",
    "co_so_tinh": "DEMO diện tích sử dụng theo thỏa thuận",
    "co_so_gia_tri": "CHUA_RO"
  }],
  "moc": [{
    "id": "10000000-0000-4000-8000-000000000031",
    "lan": 1,
    "ten": "DEMO cấp chứng nhận đầu tư",
    "ten_tat": "DEMO CNĐT",
    "ngay_du_kien": "2026-12-01",
    "ngay_thuc_te": null,
    "dang_dung": true
  }],
  "tien_do": [
    {
      "lan": 1,
      "ty_le": "10",
      "moc": {"loai": "SU_KIEN", "su_kien": "KY_HD", "so_ngay_sau_moc": 0, "han": null},
      "ghi_chu": "DEMO đợt đầu"
    },
    {
      "lan": 2,
      "ty_le": "30",
      "moc": {
        "loai": "SU_KIEN",
        "su_kien": "DAM-10000000-0000-4000-8000-000000000031",
        "so_ngay_sau_moc": 0,
        "moc_du_an_id": "10000000-0000-4000-8000-000000000031",
        "lan_moc": 1,
        "ngay_du_kien": "2026-12-01",
        "ngay_thuc_te": null,
        "han": null
      },
      "ghi_chu": "DEMO theo mốc riêng"
    },
    {
      "lan": 3,
      "ty_le": "60",
      "moc": {"loai": "NGAY", "ngay": "2027-03-01", "han": "2027-03-01"},
      "ghi_chu": "DEMO đợt cuối"
    }
  ],
  "lo_can": [{
    "id": "10000000-0000-4000-8000-000000000005",
    "lan": 1,
    "ma": "DEMO-LO-01",
    "dien_tich": "100",
    "trang_thai": "CON_TRONG",
    "ghi_chu": "DEMO lô minh họa"
  }]
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** cách biểu diễn và ghim `phien_ban_du_an_id`, `so_phien_ban`, `ma_bam` cho phiên bản tổng hợp, bao gồm phiên bản mốc/lô/tiến độ; cách biểu diễn nguồn sao chép/mẫu nếu cần công bố ra ngoài. CD-023 đã chốt hành vi một lượt/một phiên bản, nhưng KK §3 xác nhận mã hiện có chưa có snapshot tổng hợp đủ sáu khối; không coi số phiên bản thông tin hiện tại là phiên bản tổng hợp.

### Đăng ký gói CRM

Theo CD-032 và SDK §6, ba contract phải nằm trong `contract/` của gói CRM, kèm JSON Schema, bảng trường, ví dụ và phiên bản; `module.json` khai báo công bố và quyền đọc tương ứng. Core kiểm và ghi sổ contract trước kích hoạt; không sửa code Core để thêm nghiệp vụ CRM.

Các sự kiện `hop_dong_hieu_luc`, `moc_da_xay_ra`, `tien_da_noi_dot` dùng contract của lát Chung, khai báo phát/nhận trong manifest; NV-CRM không định nghĩa lại payload. Việc chờ và số đếm trên icon tiếp tục dùng nguồn việc chung theo TL49 §1, không suy số đếm từ các mảng JSON chưa lọc quyền.
---

| Mã contract | Mục đích | Sở hữu | Được đọc |
|---|---|---|---|
| `hop_dong_thau.v1` | Công bố hợp đồng thầu và căn cứ tham số đã soát | M4 | M4; module khác chờ Anh |
| `phu_luc.v1` | Công bố phụ lục, thay đổi giá trị và tham số | M4 | M4; module khác chờ Anh |
| `boq.v1` | Công bố các dòng BOQ gốc hoặc thay đổi theo phụ lục | M4 | M4; module khác chờ Anh |
| `dot_thanh_toan.v1` | Công bố hồ sơ, số liệu và kết luận thanh toán của một đợt | M4 | M4; module khác chờ Anh |
| `ket_qua_kiem_dot.v1` | Công bố kết quả kiểm K/B/C/P cùng phạm vi và căn cứ | M4 | M4; module khác chờ Anh |
| `nghiem_thu.v1` | Công bố hồ sơ nghiệm thu bàn giao kế toán và xác nhận kế toán | M4 | M4; M2 cho luồng ghi nhận chung, chờ Anh duyệt quyền |

## NV-M4 · Quy ước áp dụng

**Trạng thái toàn lát: `nhap`; phiên bản cấu trúc dự kiến: `1.0.0`.** Đây là thiết kế lớp JSON nghiệp vụ theo CD-031, CD-032, chưa phải schema đã phát hành hay xác nhận chức năng đã triển khai.

**Ký hiệu nguồn trong các bảng:**

| Ký hiệu | Tệp nguồn |
|---|---|
| TK-M4 | `..\THIET-KE-MODULE-DE-CHOT-2026-10-20\M4-XAY-DUNG-VA-NGHIEM-THU.md` |
| M17 | `src/kho_tri_thuc/m4/sql_m17.py` |
| CHEP | `src/kho_tri_thuc/m4/sql_review_chep.py` |
| DUYET | `src/kho_tri_thuc/m4/sql_duyet.py` |
| KT | `src/kho_tri_thuc/m4/sql_ke_toan_nghiem_thu.py` |
| REVIEW | `src/kho_tri_thuc/m4/sql_review.py` |
| COMPUTE | `src/kho_tri_thuc/m4/review_compute.py` |
| PL-PG | `src/kho_tri_thuc/m4/review_phu_luc_pg.py` |
| NV-GOC | `src/kho_tri_thuc/m4/review_goc/may_chu/nghiep_vu.py` |

Dùng trực tiếp `$defs` của `urn:ktt:contract:chung.v1`: `id`, `ma`, `chuoi`, `ngay`, `thoi_diem`, `thap_phan`, `tien`, `sha256`, `gia_tri`, `dan_chung`. Bảng dưới viết gọn tên kiểu; không định nghĩa lại chúng.

**Các trường chung có trong cả sáu contract:**

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `contract` | Mã contract tương ứng | Hằng chuỗi | Bắt buộc | — | `CONTRACT-DU-LIEU.md` §3, `vo_noi_dung` |
| `phien_ban` | Phiên bản cấu trúc JSON | Chuỗi phiên bản | Bắt buộc | — | `CONTRACT-DU-LIEU.md` §2–3 |
| `revision` | Lần sửa nội dung được công bố; khác phiên bản cấu trúc | Integer ≥ 1 | Bắt buộc | Lần | `CONTRACT-DU-LIEU.md` §2.1, §3 |
| `nguon_tep_ids` | Tệp nguồn làm căn cứ | Mảng `id` không trùng | Bắt buộc, ít nhất một | — | `CONTRACT-DU-LIEU.md` §3 |
| `phap_nhan_id` | Pháp nhân của hồ sơ | `id` | Bắt buộc | — | M17:278; REVIEW:46; DUYET:292 |
| `du_an_id` | Chiếu từ `danh_muc.hop_dong` qua V3, trỏ `du_an.v1`; K độc lập lấy dự án của lần kiểm | `id \| null` | Khóa bắt buộc, luôn khác `null` trong M4, kể cả K độc lập | — | M17:279; REVIEW:47–48,73–74; `DAC-TA-CSDL.md` §1.1, §6.2 |
| `hop_dong_id` | Định danh chung từ `danh_muc.hop_dong`; nghiệp vụ thầu do M4 sở hữu | `id \| null` | Khóa bắt buộc; khác `null` trừ `ket_qua_kiem_dot` nhóm K độc lập | — | M17:277,288; REVIEW:48,73–74; `DAC-TA-CSDL.md` §6.2 |

Các trường `*_tep_id` tham chiếu tệp do Core quản lý; khi lấy thông tin/tải tệp dùng `tham_chieu_tep.v1`, không truyền đường dẫn vật lý. Lỗi dùng `loi_chuan.v1`, không tạo cấu trúc lỗi M4 riêng.

`Bắt buộc, nullable` nghĩa là phải có khóa nhưng được ghi `null` khi chưa có căn cứ. Không đổi thiếu dữ liệu thành `0`, không suy VND, VAT hoặc tỷ lệ. Tiền và đơn giá dùng `tien`; tỷ lệ dùng `thap_phan` với đơn vị `%`.

Sáu contract là **dữ liệu công bố**, đọc qua `cong_bo_m4` theo quyền và pháp nhân/dự án; không cấp quyền đọc bảng riêng `mod_m4`. `doi_tuong_id` tham chiếu `doi_tuong.v1`, không nhúng lại tên, mã số thuế hay tài khoản đối tác. Những quyền đọc liên module chưa được căn cứ chỉ rõ đều **chờ Anh**, không mặc nhiên được cấp.

Theo CD-032, gói M4 phải có `contract/` chứa schema, mô tả và ví dụ; `module.json` liệt kê tương thích, công bố và sự kiện theo `DAC-TA-SDK.md` §6. Core đăng ký mã, phiên bản, chủ sở hữu, bên dùng và trạng thái vào sổ contract trong `loi`. Bản nháp này chưa cấp quyền cài đặt/kích hoạt và không bổ sung contract sự kiện ngoài lát được giao.

## 1. `hop_dong_thau.v1`

**Mục đích:** Cung cấp thông tin hợp đồng thầu và bộ căn cứ đã được phòng dự án soát, để tái sử dụng cho các đợt sau. Tham số trích được và xác nhận của phòng dự án là hai bằng chứng riêng.

**Module sở hữu:** M4. **Module được đọc:** M4; module khác chờ Anh. **Loại:** dữ liệu công bố.

Ngoài trường chung:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `so_hop_dong` | Chiếu từ `danh_muc.hop_dong` qua V3, cùng nghĩa CRM | `chuoi \| null` | Khóa bắt buộc; M4 vận hành phải khác `null` | — | CSDL §6.2; `sql_master_dung_chung.py:144` |
| `ten` | Tên hồ sơ hợp đồng | `chuoi` | Bắt buộc | — | M17:280 |
| `doi_tuong_id` | Chiếu nhà thầu từ `danh_muc.hop_dong` qua V3, trỏ `doi_tuong.v1` | `id \| null` | Tùy chọn; `null` khi chưa ánh xạ | — | CSDL §6.2; `sql_master_dung_chung.py:149`, `:160`, ánh xạ `doi_tac_id` |
| `ngay_ky` | Ngày ký hợp đồng | `ngay` | Tùy chọn | Ngày | CHEP:79 |
| `phan_loai`, `loai_gia`, `goi_thau` | Phân loại hợp đồng, loại giá và gói thầu theo nguồn | Chuỗi | Tùy chọn | — | CHEP:79–80 |
| `gia_tri_hop_dong` | Giá trị hợp đồng gốc theo tài liệu | `tien` | Tùy chọn | Theo tiền tệ nguồn | CHEP:80; TK-M4 §2 |
| `gom_vat` | Nội dung nguồn về giá trị đã/chưa gồm VAT | Chuỗi | Tùy chọn | — | CHEP:80; COMPUTE:108–113 |
| `thue_suat` | Thuế suất có căn cứ, dùng từ điển chung CRM/M4 | Chuỗi catalog thuế dùng chung | Tùy chọn, bỏ khóa khi chưa rõ | % hoặc mã chế độ | Ánh xạ trường nguồn `vat` tại CHEP:80; COMPUTE:109–113 |
| `tep_hop_dong_id` | Tài liệu hợp đồng nguồn | `id` | Bắt buộc | — | M17:283; TK-M4 §2 |
| `trang_thai_phu_luc` | `CHUA_KHAI`, `KHONG_CO`, `CO_CHUA_DU`, `CO_DU` | Enum | Bắt buộc | — | M17:284 |
| `rev_tham_so` | Revision bộ tham số được công bố | Integer ≥ 1 | Bắt buộc | Lần | M17:282 |
| `tham_so_tep_id` | Tệp nội dung `tham_so.v1` của bộ tham số đã ghim | `id` | Bắt buộc | Theo từng tham số | M17:314–335; `CONTRACT-DU-LIEU.md` §7 |
| `xac_nhan_tham_so_id` | Bằng chứng phòng dự án xác nhận đúng bộ tham số | `id` | Bắt buộc | — | M17:348–364; TK-M4 §1–2 |
| `xac_nhan_boi_id`, `xac_nhan_luc` | Người và thời điểm xác nhận | `id`, `thoi_diem` | Bắt buộc | UTC | M17:360–361 |

```json
{
  "contract": "hop_dong_thau.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000001"],
  "phap_nhan_id": "20000000-0000-4000-8000-000000000001",
  "du_an_id": "30000000-0000-4000-8000-000000000001",
  "hop_dong_id": "40000000-0000-4000-8000-000000000001",
  "so_hop_dong": "DEMO-HD-001",
  "ten": "DEMO hop dong thi cong",
  "doi_tuong_id": "50000000-0000-4000-8000-000000000001",
  "ngay_ky": "2026-10-01",
  "phan_loai": "DEMO thi cong",
  "loai_gia": "DEMO don gia co dinh",
  "goi_thau": "DEMO goi thau 01",
  "gia_tri_hop_dong": {"gia_tri": "1100000000", "don_vi_tien": "VND"},
  "gom_vat": "DEMO gia tri da gom VAT",
  "thue_suat": "10",
  "tep_hop_dong_id": "10000000-0000-4000-8000-000000000001",
  "trang_thai_phu_luc": "CO_DU",
  "rev_tham_so": 1,
  "tham_so_tep_id": "10000000-0000-4000-8000-000000000002",
  "xac_nhan_tham_so_id": "60000000-0000-4000-8000-000000000001",
  "xac_nhan_boi_id": "70000000-0000-4000-8000-000000000001",
  "xac_nhan_luc": "2026-10-02T02:00:00Z"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** tập module đọc; chốt cách công bố bộ tham số qua `tham_so_tep_id`; chuẩn hóa giá trị `phan_loai`, `loai_gia`, `gom_vat`. Không tự đặt enum mới từ chuỗi legacy. Bộ tham số tham chiếu phải đủ catalog đã ghim, không chỉ gồm các tham số xuất hiện trong ví dụ.

## 2. `phu_luc.v1`

**Mục đích:** Cung cấp một phụ lục cùng thay đổi giá trị, tham số và liên kết BOQ. Chỉ phụ lục đã ký, có hiệu lực tại ngày liên quan mới được áp dụng.

**Module sở hữu:** M4. **Module được đọc:** M4; module khác chờ Anh. **Loại:** dữ liệu công bố.

Ngoài trường chung:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `phu_luc_id`, `so_phu_luc` | Định danh và số phụ lục | `id`, `chuoi` | Bắt buộc | — | M17:366, 369 |
| `ngay_ky`, `ngay_hieu_luc` | Ngày ký và ngày bắt đầu áp dụng | `ngay` | Bắt buộc | Ngày | M17:370–371 |
| `trang_thai` | `DA_KY`, `DU_THAO`, `DA_HUY` | Enum | Bắt buộc | — | M17:372 |
| `doi_boq` | Có thay đổi BOQ hay không | Boolean | Bắt buộc | — | M17:373 |
| `noi_dung` | Nội dung phụ lục | Chuỗi | Tùy chọn | — | M17:374 |
| `tep_phu_luc_id` | Tài liệu nguồn phụ lục | `id` | Bắt buộc | — | M17:375; TK-M4 §2 |
| `gia_tri_thay_doi_truoc_vat` | Giá trị tăng/giảm trước VAT ghi trên phụ lục | `tien` | Tùy chọn | Theo tiền tệ nguồn | CHEP:106; `review_goc/csdl_hop_dong.py:939` |
| `gia_tri_thay_doi_sau_vat` | Giá trị tăng/giảm sau VAT ghi trên phụ lục | `tien` | Tùy chọn | Theo tiền tệ nguồn | CHEP:106; `review_goc/csdl_hop_dong.py:943` |
| `gia_tri_hop_dong_ghi_sau_phu_luc` | Giá trị hợp đồng sau phụ lục được ghi trên nguồn | `tien` | Tùy chọn | Theo tiền tệ nguồn | CHEP:106; PL-PG:155–159 |
| `thay_doi_tham_so` | Danh sách thay đổi tham số | Mảng object | Bắt buộc; có thể rỗng | — | CHEP:116–123 |
| `thay_doi_tham_so[].ma` | Mã tham số nguồn, thuộc catalog đã ghim | Chuỗi mã nguồn | Bắt buộc | — | CHEP:120 |
| `thay_doi_tham_so[].gia_tri_cu`, `gia_tri_moi` | Giá trị trước và sau thay đổi | `gia_tri` | Bắt buộc | Theo kiểu giá trị | CHEP:120; `CONTRACT-DU-LIEU.md` §3 |
| `thay_doi_tham_so[].dan_chung` | Căn cứ thay đổi trong phụ lục | Mảng `dan_chung` | Bắt buộc | — | CHEP:120; TK-M4 §2 |
| `boq_ids` | Các lần nhập BOQ thuộc phụ lục | Mảng `id` | Bắt buộc; có thể rỗng | — | M17:393, 407 |
| `huy_ly_do` | Lý do hủy nguồn | `chuoi \| null` | Bắt buộc khác `null` khi `DA_HUY`; trường hợp khác tùy chọn, được `null` | — | M17:376 |
| `huy_boi` | Danh tính người hủy dạng text nguồn, không phải UUID người dùng | `chuoi \| null` | Bắt buộc khác `null` khi `DA_HUY`; trường hợp khác tùy chọn, được `null` | — | M17:377,681; giữ nguyên giá trị `ai` |
| `huy_luc` | Thời điểm hủy nguồn | `thoi_diem \| null` | Bắt buộc khác `null` khi `DA_HUY`; trường hợp khác tùy chọn, được `null` | UTC | M17:378–384 |

```json
{
  "contract": "phu_luc.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000003"],
  "phap_nhan_id": "20000000-0000-4000-8000-000000000001",
  "du_an_id": "30000000-0000-4000-8000-000000000001",
  "hop_dong_id": "40000000-0000-4000-8000-000000000001",
  "phu_luc_id": "80000000-0000-4000-8000-000000000001",
  "so_phu_luc": "DEMO-PL-001",
  "ngay_ky": "2026-10-10",
  "ngay_hieu_luc": "2026-10-11",
  "trang_thai": "DA_KY",
  "doi_boq": true,
  "noi_dung": "DEMO bo hang muc chua thuc hien",
  "tep_phu_luc_id": "10000000-0000-4000-8000-000000000003",
  "gia_tri_thay_doi_truoc_vat": {"gia_tri": "-10000000", "don_vi_tien": "VND"},
  "gia_tri_thay_doi_sau_vat": {"gia_tri": "-11000000", "don_vi_tien": "VND"},
  "gia_tri_hop_dong_ghi_sau_phu_luc": {"gia_tri": "1089000000", "don_vi_tien": "VND"},
  "thay_doi_tham_so": [],
  "boq_ids": ["90000000-0000-4000-8000-000000000001"],
  "huy_ly_do": null,
  "huy_boi": null,
  "huy_luc": null
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** thứ tự áp dụng phụ lục cùng ngày; xử lý phụ lục hồi tố vì M17:383 chặn ngày hiệu lực trước ngày ký, trong khi Review gốc có cảnh báo hồi tố. Không tự giải quyết khác biệt này. Giá trị “ghi sau phụ lục” không được đổi nghĩa thành giá trị hiệu lực do máy tính.

## 3. `boq.v1`

**Mục đích:** Cung cấp một lần nhập BOQ, giữ nguyên dòng gốc và thao tác thay đổi từ phụ lục. BOQ hiệu lực được đọc theo ngày; dòng bị thay/bỏ vẫn còn trong lịch sử.

**Module sở hữu:** M4. **Module được đọc:** M4; module khác chờ Anh. **Loại:** dữ liệu công bố.

Ngoài trường chung:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `boq_id`, `lan` | Định danh và số lần nhập BOQ | `id`, integer ≥ 1 | Bắt buộc | Lần | M17:389, 392 |
| `phu_luc_id` | Phụ lục tạo thay đổi; `null` nếu BOQ gốc | `id` hoặc `null` | Bắt buộc | — | M17:393 |
| `tep_boq_id` | Tệp BOQ nguồn đã đọc | `id` | Bắt buộc | — | M17:394–395 |
| `sheet`, `hang_tieu_de` | Sheet và hàng tiêu đề được map | `chuoi`, integer ≥ 1 | Bắt buộc | Hàng | M17:396–397 |
| `trang_thai` | `DA_MAP` hoặc `CO_LOI` | Enum | Bắt buộc | — | M17:402, 409 |
| `dong` | Tập dòng của lần nhập | Mảng object | Bắt buộc | — | M17:412–421 |
| `dong[].so_dong`, `ma_hang_muc` | Vị trí dòng và mã hạng mục nguồn | Integer ≥ 1, `chuoi` | Bắt buộc | Dòng | M17:415–416 |
| `dong[].thao_tac` | `GOC`, `THEM`, `THAY`, `BO` | Enum | Bắt buộc | — | `sql_boq_bo.py:21`; QD-20261026-09 |
| `dong[].ten`, `don_vi_tinh` | Tên và đơn vị hạng mục theo nguồn | Chuỗi | Bắt buộc, nullable với dòng thay/bỏ | Theo nguồn | M17:418; PL-PG:140–145 |
| `dong[].khoi_luong` | Khối lượng ghi trên dòng | `thap_phan` hoặc `null` | Bắt buộc | Theo `don_vi_tinh` | M17:419 |
| `dong[].don_gia` | Đơn giá ghi trên dòng | `tien` hoặc `null` | Bắt buộc | Tiền/đơn vị tính | M17:419 |
| `dong[].thanh_tien_ghi` | Thành tiền nguồn, giữ riêng với kết quả nhân | `tien` hoặc `null` | Bắt buộc | Theo tiền tệ nguồn | CHEP:132; M17:387, 419 |
| `dong[].vi_tri` | Vị trí dòng trong tệp nguồn | `chung.v1#/$defs/vi_tri` | Bắt buộc | — | M17:420; TK-M4 §2 |
| `loi_chan` | Lỗi đọc/map/căn cứ ngăn sử dụng BOQ | Mảng `chuoi` | Bắt buộc | — | M17:387, 400 |
| `phat_hien` | Phát hiện nghiệp vụ, khác lỗi đọc/map | Mảng `chuoi` | Bắt buộc | — | M17:387, 401 |

```json
{
  "contract": "boq.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000004"],
  "phap_nhan_id": "20000000-0000-4000-8000-000000000001",
  "du_an_id": "30000000-0000-4000-8000-000000000001",
  "hop_dong_id": "40000000-0000-4000-8000-000000000001",
  "boq_id": "90000000-0000-4000-8000-000000000001",
  "lan": 2,
  "phu_luc_id": "80000000-0000-4000-8000-000000000001",
  "tep_boq_id": "10000000-0000-4000-8000-000000000004",
  "sheet": "DEMO_BOQ",
  "hang_tieu_de": 1,
  "trang_thai": "DA_MAP",
  "dong": [
    {
      "so_dong": 2,
      "ma_hang_muc": "DEMO-HM-002",
      "thao_tac": "BO",
      "ten": "DEMO hang muc bo theo phu luc",
      "don_vi_tinh": "m",
      "khoi_luong": null,
      "don_gia": null,
      "thanh_tien_ghi": null,
      "vi_tri": {
        "tep_id": "10000000-0000-4000-8000-000000000004",
        "dinh_vi": "DEMO_BOQ!A2:H2"
      }
    }
  ],
  "loi_chan": [],
  "phat_hien": []
}
```

`THEM` phải đủ nội dung hạng mục; `THAY` chỉ thay các ô được cung cấp theo quy tắc nguồn; `BO` làm dòng hết hiệu lực trong phép chiếu, không xóa dòng đã lưu. Không dùng `null` của `THAY` để ngầm xóa giá trị cũ. Căn cứ: PL-PG:138–145; `sql_boq_bo.py:88`–`:106`.

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** quyền đọc ngoài M4; chuẩn hóa biểu diễn ô trống/rỗng khi chuyển từ dữ liệu legacy sang JSON này. Không đưa tập BOQ hiệu lực còn mơ hồ thành tập rỗng hoặc tập dòng tính dở.

## 4. `dot_thanh_toan.v1`

**Mục đích:** Cung cấp một đợt thanh toán, số liệu nguồn và số đề nghị thanh toán được review xác nhận. Đã nộp hồ sơ không đồng nghĩa đã duyệt hay đã phát sinh công nợ.

**Module sở hữu:** M4. **Module được đọc:** M4; module khác chờ Anh. **Loại:** dữ liệu công bố.

Ngoài trường chung:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `dot_id`, `so_dot` | Định danh và số đợt trong hợp đồng | `id`, integer 1–999 | Bắt buộc | Đợt | M17:423, 426 |
| `ngay_nghiem_thu`, `ngay_nhan_ho_so` | Ngày nghiệm thu và nhận hồ sơ nguồn | `ngay` | Tùy chọn | Ngày | M17:427; CHEP:147 |
| `trang_thai_nop` | `NHAP` hoặc `DA_NOP` | Enum | Bắt buộc | — | M17:429 |
| `gia_tri_ky_nguon`, `gia_tri_luy_ke_nguon` | Giá trị kỳ này và lũy kế ghi trong hồ sơ | `tien` | Tùy chọn | Theo tiền tệ nguồn | CHEP:148 |
| `co_so_gia_tri` | Cơ sở VAT của tổng nguồn kỳ này/lũy kế và tiền khấu trừ/thanh toán nguồn | Enum `TRUOC_VAT`, `GOM_VAT`, `CHUA_RO` | Bắt buộc; chưa rõ không suy | — | T §2.2; cùng nhóm nghĩa KT:32 |
| `co_so_don_gia` | Cơ sở VAT của đơn giá thanh toán nguồn | Cùng enum cơ sở giá trị | Bắt buộc | — | T §2.2; CHEP:159 |
| `giu_lai_nguon`, `thu_hoi_tam_ung_nguon` | Giữ lại và thu hồi tạm ứng nguồn | `tien` | Tùy chọn | Theo tiền tệ nguồn | CHEP:148–149 |
| `de_nghi_thanh_toan_nguon` | Giá trị thanh toán kỳ này từ hồ sơ | `tien` | Tùy chọn | Theo tiền tệ nguồn | CHEP:149 |
| `khoi_luong` | Khối lượng thanh toán theo hạng mục | Mảng object | Bắt buộc; có thể rỗng | — | CHEP:155–163 |
| `khoi_luong[].ma_hang_muc` | Mã hạng mục đối chiếu BOQ | `chuoi` | Bắt buộc | — | CHEP:157 |
| `khoi_luong[].ky_nay`, `luy_ke` | Khối lượng kỳ này và lũy kế | `thap_phan` hoặc `null` | Bắt buộc | Đơn vị hạng mục BOQ | CHEP:159 |
| `khoi_luong[].don_gia_thanh_toan` | Đơn giá hồ sơ thanh toán | `tien` hoặc `null` | Bắt buộc | Tiền/đơn vị hạng mục | CHEP:159 |
| `tep_ho_so_ids` | Tệp thuộc bộ hồ sơ đúng đợt | Mảng `id` | Bắt buộc | — | M17:435–444; TK-M4 §2 |
| `phien_ban_ho_so_id`, `ket_luan_id` | Phiên bản hồ sơ và kết luận review được ghim | `id` | Tùy chọn | — | DUYET:194–205 |
| `ket_luan_revision` | Revision của kết luận, khác `revision` nội dung công bố | Integer ≥ 1 | Đi cùng `ket_luan_id`; bắt buộc khi có tiền xác nhận | Lần | DUYET:201 |
| `graph_sha256` | Mã băm đồ thị căn cứ đã lưu cùng kết luận | `sha256` | Đi cùng `ket_luan_id` và `ket_luan_revision` | — | DUYET:203 |
| `tien_te` | Đơn vị tiền được review xác nhận | Chuỗi mã ISO 3 chữ hoa | Bắt buộc khi bàn giao; khớp mọi `don_vi_tien` của tiền xác nhận | — | DUYET:206 |
| `co_so_gia_tri_review` | Cơ sở VAT của tiền review, không suy từ tổng nguồn | Enum `TRUOC_VAT`, `GOM_VAT`, `CHUA_RO` | Bắt buộc khi có kết luận; `CHUA_RO` chặn dùng tính/ghi nhận | — | T §2.2; căn cứ kết luận DUYET:202–207 |
| `gia_tri_nt_xac_nhan` | Giá trị nghiệm thu do review xác nhận | `tien \| null` | Bắt buộc khi có kết luận; bàn giao nghiệm thu phải đủ | Theo `tien_te` | Ánh xạ `gia_tri_nt`, DUYET:30,207 |
| `tam_ung_xac_nhan`, `thu_hoi_xac_nhan`, `giu_lai_xac_nhan` | Tạm ứng, thu hồi, giữ lại review xác nhận, từng khoản tách riêng | `tien \| null` | Bắt buộc khi có kết luận; `null` là chưa xác định, không phải 0 | Theo `tien_te` | Ánh xạ `tam_ung`, `thu_hoi`, `giu_lai`, DUYET:30,207; TK-M4 §3 |
| `so_xin_thanh_toan_xac_nhan` | Số đề nghị được review xác nhận, dùng tạo Request nháp | `tien` | Tùy chọn; bắt buộc khi bàn giao tạo Request | Theo tiền tệ đã xác nhận | DUYET:30, 206–207; TK-M4 §3 |
| `quyet_dinh_duyet_id`, `pdf_da_duyet_tep_id` | Quyết định duyệt và PDF hồ sơ đợt tương ứng | `id` | Tùy chọn trước bàn giao | — | DUYET:240–282; TK-M4 §3 |

Tiền review được đọc nguyên từ đúng `(phien_ban_ho_so_id,ket_luan_id,ket_luan_revision,graph_sha256)`; hash là `graph_sha256` đã lưu ở nguồn, không băm lại phép chiếu. `so_xin_thanh_toan_xac_nhan` ánh xạ `so_xin_thanh_toan`. Khi bàn giao phải đủ bộ ghim và quyết định/PDF đúng kết luận. Không suy các số xác nhận bằng phép trừ tiền nguồn. Các trường `*_xac_nhan` tại đợt là **review**; tại `nghiem_thu` là **kế toán**, consumer phải giữ namespace contract và revision tương ứng.

Ví dụ có đơn giá trước VAT, tổng nguồn gồm VAT 10% có căn cứ DEMO: 10 × 10.000.000 = 100.000.000 trước VAT; VAT 10.000.000; tổng 110.000.000. Giữ lại 5.500.000, thu hồi 11.000.000, tạm ứng kỳ này 0; số xin 93.500.000. Đây là kiểm tổng của ví dụ có đủ căn cứ, không phải quy tắc tự tính kết luận cho mọi hồ sơ.

```json
{
  "contract": "dot_thanh_toan.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000005"],
  "phap_nhan_id": "20000000-0000-4000-8000-000000000001",
  "du_an_id": "30000000-0000-4000-8000-000000000001",
  "hop_dong_id": "40000000-0000-4000-8000-000000000001",
  "dot_id": "a0000000-0000-4000-8000-000000000001",
  "so_dot": 1,
  "ngay_nghiem_thu": "2026-10-20",
  "ngay_nhan_ho_so": "2026-10-21",
  "trang_thai_nop": "DA_NOP",
  "co_so_gia_tri": "GOM_VAT",
  "co_so_don_gia": "TRUOC_VAT",
  "gia_tri_ky_nguon": {"gia_tri": "110000000", "don_vi_tien": "VND"},
  "gia_tri_luy_ke_nguon": {"gia_tri": "110000000", "don_vi_tien": "VND"},
  "giu_lai_nguon": {"gia_tri": "5500000", "don_vi_tien": "VND"},
  "thu_hoi_tam_ung_nguon": {"gia_tri": "11000000", "don_vi_tien": "VND"},
  "de_nghi_thanh_toan_nguon": {"gia_tri": "93500000", "don_vi_tien": "VND"},
  "khoi_luong": [
    {
      "ma_hang_muc": "DEMO-HM-001",
      "ky_nay": "10",
      "luy_ke": "10",
      "don_gia_thanh_toan": {"gia_tri": "10000000", "don_vi_tien": "VND"}
    }
  ],
  "tep_ho_so_ids": ["10000000-0000-4000-8000-000000000005"],
  "phien_ban_ho_so_id": "b0000000-0000-4000-8000-000000000001",
  "ket_luan_id": "c0000000-0000-4000-8000-000000000001",
  "ket_luan_revision": 1,
  "graph_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "tien_te": "VND",
  "co_so_gia_tri_review": "GOM_VAT",
  "gia_tri_nt_xac_nhan": {"gia_tri": "110000000", "don_vi_tien": "VND"},
  "tam_ung_xac_nhan": {"gia_tri": "0", "don_vi_tien": "VND"},
  "thu_hoi_xac_nhan": {"gia_tri": "11000000", "don_vi_tien": "VND"},
  "giu_lai_xac_nhan": {"gia_tri": "5500000", "don_vi_tien": "VND"},
  "so_xin_thanh_toan_xac_nhan": {"gia_tri": "93500000", "don_vi_tien": "VND"},
  "quyet_dinh_duyet_id": "d0000000-0000-4000-8000-000000000001",
  "pdf_da_duyet_tep_id": "10000000-0000-4000-8000-000000000006"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** tập module đọc và cách công bố trạng thái riêng Review/PDF/Request; không gộp chúng vào `trang_thai_nop`. Khi đã duyệt nhưng thiếu PDF đúng lần duyệt, áp dụng `CHO_PDF` theo TK-M4 §3, chưa chuyển hai nhánh. Không lấy số nguồn trừ ảnh hưởng review để tự tính số chấp nhận.

## 5. `ket_qua_kiem_dot.v1`

**Mục đích:** Cung cấp kết quả của một nhóm kiểm K/B/C/P với căn cứ, phạm vi kiểm và phát hiện gốc. Kết quả kiểm không thay quyết định duyệt hoặc xác nhận thanh toán.

**Module sở hữu:** M4. **Module được đọc:** M4; module khác chờ Anh. **Loại:** dữ liệu công bố.

Một bản ghi đại diện một nhóm kiểm của một lần chạy. K = K1–K8; B = B1–B8, kèm nhóm tổng hợp `GT` nếu nguồn trả; C = C01–C09; P = các mã P01–P18 mà bộ kiểm phụ lục thực sự trả. Không tạo kết quả cho mã chưa chạy.

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `lan_kiem_id` | Định danh lần kiểm, không tái dùng cho lần chạy lại | `id` | Bắt buộc | — | REVIEW:44–77; CD-011 |
| `dot_id` | Đợt được kiểm | `id \| null` | Bắt buộc khác `null` với B/C; tùy chọn, được `null` với K/P | — | REVIEW:49,73; TK-M4 §4 |
| `phu_luc_id` | Phụ lục được kiểm | `id \| null` | Bắt buộc khác `null` với P; tùy chọn, được `null` với nhóm khác | — | CHEP:179; `review_goc/csdl_hop_dong.py:834` |
| `nhom_kiem` | K, B, C hoặc P | Enum | Bắt buộc | — | CD-011; COMPUTE:31–32; `chung_tu_adapter.py:40` |
| `can_cu_sha256` | Mã băm căn cứ đã ghim | `sha256` | Bắt buộc với lần kiểm vận hành | — | REVIEW:54–55 |
| `bang_kiem` | Kết quả theo từng mã thực sự được xét | Mảng object | Bắt buộc | — | COMPUTE:152–225; NV-GOC:293–298 |
| `bang_kiem[].ma` | Mã quy tắc nguồn | Chuỗi mã nguồn | Bắt buộc | — | COMPUTE:31–32; CD-011 |
| `bang_kiem[].trang_thai_kiem` | Trạng thái phạm vi kiểm, độc lập kết quả nguồn | Enum hiện có | Bắt buộc với K/B/C; P chờ Anh | — | COMPUTE:27–30; `chung_tu_adapter.py:22` |
| `bang_kiem[].ket_qua_nguon`, `ly_do` | Kết quả nguyên nghĩa và lý do giới hạn kiểm | Chuỗi hoặc `null`, chuỗi | Bắt buộc | — | COMPUTE:219–225; NV-GOC:297–298 |
| `phat_hien` | Các phát hiện thực tế của lần kiểm | Mảng object | Bắt buộc; có thể rỗng | — | NV-GOC:287–292, 352–363 |
| `phat_hien[].ma`, `muc_do`, `noi_dung` | Mã quy tắc, mức độ và nội dung nguồn | Chuỗi | Bắt buộc | — | NV-GOC:287–288; CHEP:180 |
| `phat_hien[].anh_huong_uoc_tinh` | Ảnh hưởng tiền ước tính nếu có căn cứ tiền tệ | `tien` hoặc `null` | Bắt buộc | Theo tiền tệ nguồn | COMPUTE:12–14; NV-GOC:361–363 |
| `phat_hien[].dan_chung` | Vị trí và trích dẫn nguồn kiểm được | Mảng `dan_chung` | Bắt buộc; rỗng nếu chưa định vị được | — | NV-GOC:289–292; `chung_tu_adapter.py:188` |
| `bao_cao_tep_ids` | Báo cáo và kết quả chi tiết qua kho tệp Core | Mảng `id` | Bắt buộc; có thể rỗng | — | REVIEW:118–130 |

Trạng thái phạm vi K/B/C dùng nguyên tập hiện có: `CHECKED`, `NOT_ELIGIBLE`, `LIMITED`, `NOT_AVAILABLE`, `INCOMPLETE`, `ERROR`, `KHONG_AP_DUNG`. Không chuyển `INCOMPLETE` thành “Đạt” chỉ vì không có finding.

**Điều kiện phạm vi:** K độc lập (review L1 không gắn hợp đồng) vẫn hợp lệ với `hop_dong_id=null`, `dot_id=null`, `phu_luc_id=null`; vẫn bắt buộc `du_an_id` của lần kiểm theo REVIEW:47. Không tạo hợp đồng giả để qua kiểm. K gắn hồ sơ phải giữ đúng ID hợp đồng; B/C bắt buộc hợp đồng + đợt; P bắt buộc hợp đồng + phụ lục. Ví dụ sau minh họa K độc lập, không phải lần kiểm của đợt ở ví dụ trước.

```json
{
  "contract": "ket_qua_kiem_dot.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": ["10000000-0000-4000-8000-000000000005"],
  "phap_nhan_id": "20000000-0000-4000-8000-000000000001",
  "du_an_id": "30000000-0000-4000-8000-000000000001",
  "hop_dong_id": null,
  "lan_kiem_id": "e0000000-0000-4000-8000-000000000001",
  "dot_id": null,
  "phu_luc_id": null,
  "nhom_kiem": "K",
  "can_cu_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "bang_kiem": [
    {"ma": "K1", "trang_thai_kiem": "CHECKED", "ket_qua_nguon": "Đạt", "ly_do": "DEMO workbook doc duoc"},
    {"ma": "K2", "trang_thai_kiem": "NOT_ELIGIBLE", "ket_qua_nguon": "Đạt", "ly_do": "DEMO khong cot nao du nguong mau"},
    {"ma": "K3", "trang_thai_kiem": "NOT_ELIGIBLE", "ket_qua_nguon": "Đạt", "ly_do": "DEMO khong du nguong lien ket"},
    {"ma": "K4", "trang_thai_kiem": "CHECKED", "ket_qua_nguon": "Đạt", "ly_do": "DEMO da xet sheet an"},
    {"ma": "K5", "trang_thai_kiem": "CHECKED", "ket_qua_nguon": "Đạt", "ly_do": "DEMO da xet so dang chu"},
    {"ma": "K6", "trang_thai_kiem": "LIMITED", "ket_qua_nguon": "Đạt", "ly_do": "DEMO thieu cay truy vet"},
    {"ma": "K7", "trang_thai_kiem": "INCOMPLETE", "ket_qua_nguon": "Đạt", "ly_do": "DEMO chua xac dinh o dich"},
    {"ma": "K8", "trang_thai_kiem": "INCOMPLETE", "ket_qua_nguon": "Đạt", "ly_do": "DEMO chua nhan bang chi tiet"}
  ],
  "phat_hien": [],
  "bao_cao_tep_ids": ["10000000-0000-4000-8000-000000000007"]
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** chuẩn hóa lớp công bố P vì nguồn P trả bộ ba mã/mức độ/nội dung, chưa có coverage đồng nhất K/B/C; cách biểu diễn kết quả P lịch sử không có `lan_kiem_id`/hash căn cứ. Không tự tạo run hoặc bằng chứng vận hành cho dữ liệu chép legacy. Mức độ nguồn P cũng không tự ánh xạ sang thang mức độ K/B/C.

## 6. `nghiem_thu.v1`

**Mục đích:** Cung cấp hồ sơ nghiệm thu đã duyệt, đủ PDF và được bàn giao bất biến cho kế toán, cùng revision xác nhận kế toán nếu có. Giá trị kế toán xác nhận là căn cứ riêng cho ghi nhận chung M2/M4.

**Module sở hữu:** M4. **Module được đọc:** M4; M2 trong luồng ghi nhận chung, chờ Anh duyệt quyền. **Loại:** dữ liệu công bố.

Ngoài trường chung:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `nghiem_thu_id` | Gốc nghiệm thu logic theo đợt, giữ qua các bản đính chính | `id` | Bắt buộc | — | DUYET:317–329, ánh xạ `cho_id` |
| `dot_id`, `phien_ban_ho_so_id` | Đợt và phiên bản hồ sơ đã duyệt | `id` | Bắt buộc | — | DUYET:333, 336 |
| `phong_bi_id`, `phong_bi_truoc_id` | Bản bàn giao và bản trước nếu đính chính | `id`, `id` hoặc `null` | Bắt buộc | — | DUYET:330–346 |
| `seal_id`, `phong_bi_sha256` | Dấu khóa và mã băm bản bàn giao | `id`, `sha256` | Bắt buộc | — | DUYET:335, 340 |
| `pdf_da_duyet_tep_id` | PDF hồ sơ đợt đúng lần duyệt | `id` | Bắt buộc | — | DUYET:299–314; TK-M4 §3 |
| `trang_thai_ban_giao` | Trạng thái gốc `CHO_XAC_NHAN` | Hằng chuỗi | Bắt buộc | — | DUYET:324 |
| `gia_tri_nghiem_thu_review` | Giá trị nghiệm thu theo kết luận đã khóa | `tien` | Bắt buộc | Theo tiền tệ xác nhận | DUYET:30, 302; TK-M4 §3 |
| `kt_xac_nhan_id` | Revision xác nhận kế toán | `id` hoặc `null` | Bắt buộc | — | KT:165–179 |
| `gia_tri_nghiem_thu_xac_nhan` | Giá trị nghiệm thu do kế toán xác nhận | `tien` hoặc `null` | Bắt buộc | Theo tiền tệ xác nhận | KT:35, 180–181 |
| `tam_ung_xac_nhan`, `thu_hoi_xac_nhan`, `giu_lai_xac_nhan` | Ba khoản kế toán giữ riêng | `tien` hoặc `null` | Bắt buộc | Theo tiền tệ xác nhận | KT:35 |
| `co_so_gia_tri` | `TRUOC_VAT`, `GOM_VAT`, `CHUA_RO` | Enum | Bắt buộc | — | KT:32 |
| `vat_trang_thai` | `CHUA_DU`, `CO_CAN_CU`, `KHONG_AP_DUNG` | Enum | Bắt buộc | — | KT:33 |
| `vat_can_cu` | Dẫn chứng thuế đã được kế toán kiểm | Mảng `dan_chung` | Bắt buộc; không rỗng khi `CO_CAN_CU` | — | KT:184–186, 203–204 |
| `ly_do` | Giải trình, gồm chênh lệch so với nguồn nếu có | Chuỗi hoặc `null` | Bắt buộc khi quy tắc KT yêu cầu | — | KT:40, 82, 187 |
| `xac_nhan_boi_id`, `xac_nhan_luc` | Người và thời điểm kế toán xác nhận | `id`, `thoi_diem` | Tùy chọn trước xác nhận; bắt buộc sau xác nhận | UTC | KT:188–190 |

```json
{
  "contract": "nghiem_thu.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": [
    "10000000-0000-4000-8000-000000000006",
    "10000000-0000-4000-8000-000000000008"
  ],
  "phap_nhan_id": "20000000-0000-4000-8000-000000000001",
  "du_an_id": "30000000-0000-4000-8000-000000000001",
  "hop_dong_id": "40000000-0000-4000-8000-000000000001",
  "nghiem_thu_id": "f0000000-0000-4000-8000-000000000001",
  "dot_id": "a0000000-0000-4000-8000-000000000001",
  "phien_ban_ho_so_id": "b0000000-0000-4000-8000-000000000001",
  "phong_bi_id": "f0000000-0000-4000-8000-000000000002",
  "phong_bi_truoc_id": null,
  "seal_id": "f0000000-0000-4000-8000-000000000003",
  "phong_bi_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "pdf_da_duyet_tep_id": "10000000-0000-4000-8000-000000000006",
  "trang_thai_ban_giao": "CHO_XAC_NHAN",
  "gia_tri_nghiem_thu_review": {"gia_tri": "110000000", "don_vi_tien": "VND"},
  "kt_xac_nhan_id": "f0000000-0000-4000-8000-000000000004",
  "gia_tri_nghiem_thu_xac_nhan": {"gia_tri": "110000000", "don_vi_tien": "VND"},
  "tam_ung_xac_nhan": null,
  "thu_hoi_xac_nhan": {"gia_tri": "11000000", "don_vi_tien": "VND"},
  "giu_lai_xac_nhan": {"gia_tri": "5500000", "don_vi_tien": "VND"},
  "co_so_gia_tri": "GOM_VAT",
  "vat_trang_thai": "CO_CAN_CU",
  "vat_can_cu": [
    {
      "vi_tri": {
        "tep_id": "10000000-0000-4000-8000-000000000008",
        "dinh_vi": "DEMO dieu 3"
      },
      "trich_dan": "DEMO gia tri nghiem thu da gom VAT"
    }
  ],
  "ly_do": "DEMO ke toan da doi chieu can cu",
  "xac_nhan_boi_id": "70000000-0000-4000-8000-000000000002",
  "xac_nhan_luc": "2026-10-23T03:00:00Z"
}
```

`trang_thai_ban_giao` là trạng thái của gốc bàn giao, không phải trạng thái xác nhận kế toán hiện hành; ví dụ giữ gốc `CHO_XAC_NHAN` và bổ sung revision xác nhận riêng, đúng mô hình hiện có.

Chỉ công bố hồ sơ đủ điều kiện bàn giao khi PDF, quyết định duyệt và phiên bản hồ sơ khớp nhau. Sau bàn giao, thay đổi tạo bản đính chính cùng gốc, không ghi đè. Nguồn thay đổi sau seal phải chờ kiểm/duyệt lại trước tác động kế toán; không dùng riêng sự tồn tại của `kt_xac_nhan_id` để bỏ qua kiểm hiện hành.

**Trạng thái/phiên bản:** `nhap` / `1.0.0`. **Chờ Anh:** quyền M2 đọc và biểu diễn trạng thái hiện hành/HOLD trên mặt công bố. Xác nhận kế toán không đồng nghĩa đã ghi công nợ; việc ghi nhận phải đi qua luồng chung M2/M4 để chống ghi nợ hai lần. Request bị trả lại hoặc từ chối không tự hủy nghiệm thu/công nợ, theo TK-M4 §3.
---

| Mã contract | Mục đích | Sở hữu | Được đọc |
|---|---|---|---|
| `hoa_don_mua_vao.v1` | Công bố hóa đơn đã nhận, phiên bản nguồn, trạng thái và đích hạch toán từng dòng | M2 | Dự kiến M1, M4, M5, M6, M8, M10 theo phạm vi nghiệp vụ — chờ Anh duyệt |
| `cong_no_phai_tra.v1` | Công bố khoản phải trả có căn cứ, phần đã thanh toán và phần còn lại | M2 | Dự kiến M1, M8, M10 — chờ Anh duyệt |

## NV-M2 — Quy ước và căn cứ

**Trạng thái toàn lát: `nhap`; phiên bản cấu trúc dự kiến `1.0.0`.** Các tên trường dưới đây là ánh xạ contract đề xuất, không khẳng định đã có API hoặc đã triển khai công nợ đầy đủ.

Ký hiệu nguồn:

- **TL43:** `../43-M2-00-nhan-nguon-tu-cong-thue.md`, đã chốt phạm vi §2–6 và policy tiền tệ tại §9. Bản `../THIET-KE-MODULE-DE-CHOT-2026-10-20/M2-00-NHAN-NGUON-TU-CONG-THUE.md` được đối chiếu cùng nội dung này.
- **M2:** `../THIET-KE-MODULE-DE-CHOT-2026-10-20/M2-MUA-HANG-VA-CONG-NO.md`. Thiết kế nghiệp vụ này **chưa được Anh chốt**, theo TL55 §9.
- **CB:** `src/kho_tri_thuc/k2/sql_cong_bo_hoa_don.py`, contract công bố M0064.
- **H:** `src/kho_tri_thuc/k2/hoa_don.py`.
- **P:** `src/kho_tri_thuc/ha_tang/pg_migrations.py`.
- **T, D, S:** lần lượt là `CONTRACT-DU-LIEU.md`, `DAC-TA-CSDL.md`, `DAC-TA-SDK.md` trong `docs/47-core/g1/`.

Trong bảng, **“chờ Anh”** nghĩa là nội dung chưa được phê duyệt để vận hành. Kiểu và tính bắt buộc của những trường này cũng là đề xuất nháp. Mã nguồn hiện có là căn cứ về cấu trúc kỹ thuật, không thay thế việc Anh duyệt nghiệp vụ.

**Dùng lại contract chung:**

- `id`, `chuoi`, `ma`, `sha256`, `ngay`, `thoi_diem`, `tien` tham chiếu nguyên `$defs` của `urn:ktt:contract:chung.v1`.
- Tệp dùng `tham_chieu_tep.v1`; lỗi quyền, tham số và xử lý dùng `loi_chuan.v1`. Không định nghĩa lại.
- Nhà cung cấp chỉ tham chiếu `doi_tuong.v1` bằng `doi_tuong_id`; dự án chỉ tham chiếu `du_an.v1` bằng `du_an_id`. Không nhúng lại danh mục hoặc tự sinh mã Junsky.
- Phần đọc XML dùng nguyên `hoa_don.v1`. Contract nghiệp vụ không khai lại đầu hóa đơn, dòng hàng, số lượng, thuế hoặc tổng tiền đọc từ XML.

Hai contract kế thừa vỏ `chung.v1#/$defs/vo_noi_dung`:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `contract` | Mã contract trao đổi | Hằng theo từng contract | Bắt buộc | — | T §2–3 |
| `phien_ban` | Phiên bản cấu trúc contract | Hằng `"1.0.0"` của bản nháp | Bắt buộc | — | T §2–3 |
| `revision` | Revision nội dung công bố; khác phiên bản hóa đơn | Kiểu trong vỏ chung | Bắt buộc | Lần | T §2–3 |
| `nguon_tep_ids` | Các tệp nguồn làm căn cứ | Kiểu trong vỏ chung | Bắt buộc | — | T §2.1, §3 |

Theo D §1.1, §6.1, định danh chung nằm tại `danh_muc`; quan sát, phiên bản, dòng, đích và công nợ thuộc `mod_m2`. Module khác chỉ đọc qua `cong_bo_m2` đúng contract và quyền đã cấp. Không tạo FK sang bảng riêng M2; tham chiếu phiên bản nguồn phải kiểm ID, mã băm và cùng pháp nhân.

## 1. `hoa_don_mua_vao.v1`

**Mã:** `hoa_don_mua_vao.v1`.

**Mục đích:** Công bố những hóa đơn mua vào M2 đã tiếp nhận, giữ rõ phiên bản và quan sát nguồn để module khác đối chiếu. Bổ sung đích hạch toán từng dòng khi có quyết định tương ứng; việc nhận hóa đơn không tự xác nhận ghi nhận công nợ hoặc điều kiện thuế.

**Module sở hữu:** M2.

**Module được đọc:** Dự kiến M1, M4, M5, M6, M8, M10 theo liên kết tại M2 §2, §6; **chờ Anh duyệt danh sách và phạm vi trường**.

**Loại:** Dữ liệu công bố.

### Bảng trường

Bảng sau bổ sung cho vỏ chung. `hoa_don[]` là tập kết quả trong một pháp nhân, kế thừa cách trả `CHO`/`CO_DU_LIEU` của M0064.

### Quan hệ và vòng đời với M0064

`hoa_don_mua_vao.v1` là **phép chiếu có chuyển đổi và mở rộng** phần quan sát/phiên bản của `m2-hoa-don-cong-bo/v1`, cùng chủ M2; không phải định nghĩa độc lập cho cùng phần dữ liệu. M0064 tiếp tục phục vụ consumer cũ với nguyên envelope, trường tiền/raw-state, coverage, quyền và hành vi latest (CB:30–68). Adapter công bố thuộc M2 dùng lại nguồn/ngữ nghĩa đã có, thêm vỏ chung, nguồn tệp và các trường nghiệp vụ chờ duyệt; không chuyển đổi mất dữ liệu rồi trả ngược dưới mã cũ.

| M0064 (`hoa_don[]`, nếu không ghi khác) | `hoa_don_mua_vao.v1` | Quy tắc chuyển đổi |
|---|---|---|
| Envelope `phap_nhan_id`, `trang_thai`, `ly_do`, `hoa_don` | Cùng tên | Giữ `CHO`/`CO_DU_LIEU`; đổi mã contract rõ ràng, bổ sung `phien_ban/revision/nguon_tep_ids` từ metadata được kiểm |
| `hoa_don_id`, `phien_ban_id` | Cùng tên | Giữ nguyên UUID và quan hệ cùng pháp nhân |
| `phien_ban` | `phien_ban_nguon` | Integer nguồn, không phải semver ngoài vỏ |
| `semantic_contract`, `semantic_sha256` | `contract_noi_dung_nguon`, `ma_bam_noi_dung` | Giữ nguyên ngữ nghĩa/hash đã lưu, không băm lại phép chiếu |
| `trang_thai_nguon.quan_sat_id`, `.classification` | `quan_sat_id`, `phan_loai_quan_sat` | Đúng quan sát được chọn; không ghép trạng thái quan sát mới với phiên bản cũ |
| `trang_thai_nguon.raw_status_namespace`, `.raw_status` | `mien_trang_thai_nguon`, `ma_trang_thai_nguon` | Giữ nguyên mã, không diễn giải thành duyệt/hủy |
| `trang_thai_nguon.accepted_source_observation_id`, `.eligible_content_id` | `quan_sat_nguon_chap_nhan_id`, `noi_dung_du_dieu_kien_id` | Con trỏ trạng thái tại thời điểm đọc, không tự chứng minh trạng thái lịch sử của quan sát đã phát |
| `money_basis_state` | `trang_thai_can_cu_tien` | Giữ nguyên; `UNPROVEN_NO_MINOR` không tạo tiền chuẩn |
| Không có trong envelope M0064 | `lan_tiep_nhan_id`, `da_nhan_luc`, `ket_qua_doc_xml`, `trang_thai_xml`, `doi_tuong_id`, `dich_hach_toan` | M2 bổ sung từ đúng quan sát/nguồn và quyết định có quyền đọc; không bịa từ latest |
| `so_chuan/so_hoa_don/mau_so/ky_hieu/ngay_lap/mst_ban/mst_mua`, `tien_te/tong_tien/total_minor`, `trang_thai_nguon.native_fiscal_status`, `coverage/coverage_hieu_luc/period_completeness`, pháp nhân từng dòng | Không chiếu trực tiếp ở bản nháp mới | Vẫn giữ ở contract M0064 cho consumer cũ; không suy từ sự vắng mặt thành 0 hoặc đầy đủ kỳ. Không có phép đổi ngược toàn phần |

**Vòng đời:** hai mã cùng tồn tại với binding/phiên bản riêng trong sổ contract và manifest, mỗi consumer ghim chính xác mã/phiên bản. Bản mới còn `nhap`, chỉ kích hoạt sau khi Anh duyệt schema, ánh xạ, quyền và có đường đọc phù hợp; không tự đổi tên mã M0064 đang dùng. Chuyển từng consumer bằng adapter đã kiểm; chỉ ngừng mã cũ sau thông báo và hết consumer ghim mã đó. Mọi bổ sung sau phát hành tạo `$id`/semver mới theo T §2, giữ phục vụ bản cũ; không thay hành vi latest dưới mã M0064 hiện tại.

### Phép đọc công bố theo tham chiếu chính xác (yêu cầu thiết kế)

Mặt `cong_bo_m2` phải có phép đọc đăng ký cho contract này nhận pháp nhân + tập bộ `(hoa_don_id,quan_sat_id,phien_ban_id)`, tùy chọn hash kỳ vọng đã ghim. Đây là yêu cầu giao diện, **chưa phải API/hàm đã triển khai**. Kiểm danh tính, quyền contract/trường/pháp nhân trước lookup theo cùng nguyên tắc CB:20–27; chỉ M2 đọc bảng của mình.

1. Chọn **đúng `quan_sat_id`**, kiểm quan sát thuộc hóa đơn/pháp nhân và trỏ **đúng `phien_ban_id`**; lấy nội dung/hash đã lưu của phiên bản đó cùng lần tiếp nhận và nguồn tệp tương ứng. Không join qua `latest_observation_id`, không lấy `max(phien_ban)` hoặc `eligible_content_id` để thay yêu cầu.
2. Trả đúng dòng quan sát/phiên bản trong cấu trúc đã khai; bên nhận ghim `ma_bam_noi_dung` và so hash kỳ vọng nếu có. Những con trỏ hiện hành/đích hạch toán không được dùng để giả lập quyết định tại thời điểm sự kiện; muốn dùng quyết định phải ghim riêng `dich_id/phien_ban_dich` và kiểm hiện hành/quyền.
3. Sai quyền trả lỗi quyền chuẩn; ID/hash/quan hệ không khớp trả lỗi tham chiếu chuẩn. Nguồn/phiên bản chưa sẵn sàng trả `CHO` có lý do, không thay bằng một quan sát khác và không xác nhận đã xử lý nghiệp vụ. Khi đọc tập, không bỏ âm thầm bộ tham chiếu thiếu rồi coi cả tập đã đủ.
4. Phép đọc danh sách hiện hành có thể dùng lựa chọn latest của M0064; **consumer `hoa_don_da_nhan` bắt buộc dùng phép đọc chính xác**. Nếu quan sát mới đến trước lúc consumer xử lý, consumer vẫn đọc quan sát/phiên bản đã phát, giữ hash tương ứng. Chưa cung cấp được phép đọc này thì chặn kích hoạt consumer; không cho đọc bảng riêng M2.

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `phap_nhan_id` | Pháp nhân của tập hóa đơn | `id` | Bắt buộc | — | CB:30–32, CB:64–68 |
| `trang_thai` | Có nguồn để công bố hay đang chờ; nhận `CO_DU_LIEU` hoặc `CHO` | Enum theo M0064 | Bắt buộc | — | CB:5–6, CB:64–68 |
| `ly_do` | Lý do chờ; `null` khi có dữ liệu | `chuoi \| null` | Bắt buộc; khác `null` khi `CHO` | — | CB:31–32, CB:67 |
| `hoa_don` | Danh sách hóa đơn trong phạm vi được đọc | Mảng đối tượng theo các dòng dưới | Bắt buộc; rỗng khi `CHO` | — | CB:6, CB:38–68 |
| `hoa_don[].hoa_don_id` | Danh tính hóa đơn dùng chung | `id` | Bắt buộc | — | CB:39; D §1.1, §6.1 |
| `hoa_don[].phien_ban_id` | Phiên bản nội dung gắn với quan sát được công bố | `id` | Bắt buộc | — | CB:40, CB:57–60 |
| `hoa_don[].phien_ban_nguon` | Số phiên bản nội dung hóa đơn | Integer ≥ 1 | Bắt buộc | Lần | CB:40; P:5260 |
| `hoa_don[].contract_noi_dung_nguon` | Contract ngữ nghĩa của nội dung M2 đã lưu | `chuoi` | Bắt buộc | — | CB:41 |
| `hoa_don[].ma_bam_noi_dung` | Mã băm ngữ nghĩa đã lưu của phiên bản nguồn | `sha256` | Bắt buộc | — | CB:8–9, CB:41 |
| `hoa_don[].quan_sat_id` | Quan sát nguồn đang được công bố | `id` | Bắt buộc | — | CB:48, CB:57 |
| `hoa_don[].lan_tiep_nhan_id` | Lần tiếp nhận chứa quan sát; không đồng nhất với danh tính hóa đơn | `id` | Bắt buộc | — | P:5299; H:582 |
| `hoa_don[].da_nhan_luc` | Thời điểm máy chủ ghi nhận quan sát | `thoi_diem` | Bắt buộc | Thời điểm UTC | P:5316; H:582 |
| `hoa_don[].quan_sat_nguon_chap_nhan_id` | Quan sát nguồn đã được chấp nhận; chưa có thì `null` | `id \| null` | Bắt buộc, cho phép `null` | — | CB:51; D §2 |
| `hoa_don[].noi_dung_du_dieu_kien_id` | Con trỏ nội dung đủ điều kiện theo kiểm M2; chưa có thì `null` | `id \| null` | Bắt buộc, cho phép `null` | — | CB:52; D §2 |
| `hoa_don[].ket_qua_doc_xml` | Tệp JSON chứa nguyên kết quả `hoa_don.v1` | `tham_chieu_tep.v1 \| null` | Bắt buộc, cho phép `null` khi không có kết quả đọc | — | T §2.1, §4, §10; TL43 §6 |
| `hoa_don[].trang_thai_xml` | Kết quả tải XML: `OK`, `KHONG_XML_GOC` hoặc `LOI` | Enum theo manifest | Bắt buộc | — | TL43 §5–6 |
| `hoa_don[].phan_loai_quan_sat` | Các phân loại tiếp nhận, revision hoặc conflict do M2 lưu | Mảng `chuoi` | Bắt buộc; giữ nguyên giá trị nguồn | — | CB:48; TL43 §6 |
| `hoa_don[].mien_trang_thai_nguon` | Namespace của mã trạng thái nguồn | `chuoi \| null` | Bắt buộc, cho phép `null` | — | CB:50 |
| `hoa_don[].ma_trang_thai_nguon` | Mã trạng thái nguồn nguyên bản; chưa tự diễn giải thành hủy/điều chỉnh | `chuoi \| null` | Bắt buộc, cho phép `null` | — | CB:50; TL43 §6, §9 |
| `hoa_don[].trang_thai_can_cu_tien` | Tình trạng căn cứ biểu diễn tiền của phiên bản nguồn | `chuoi` | Bắt buộc | — | CB:10, CB:46; P:5277 |
| `hoa_don[].doi_tuong_id` | Nhà cung cấp đã ánh xạ qua `doi_tuong.v1` | `id \| null` | Tùy chọn — **chờ Anh** | — | M2 §3 bước 3, §4 |
| `hoa_don[].dich_hach_toan` | Các quyết định đích theo dòng; chưa có thì mảng rỗng | Mảng đối tượng theo bảng dưới | Bắt buộc về cấu trúc nháp — **chờ Anh** | — | M2 §2–5; H:593 |

Các trường trong mỗi phần tử `dich_hach_toan[]`:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `dich_id` | Định danh quyết định đích | `id` | Bắt buộc — **chờ Anh** | — | P:5492; H:593 |
| `dong_nguon_id` | Dòng nguồn mà quyết định áp dụng; không dùng STT sau sắp xếp | `id` | Bắt buộc — **chờ Anh** | — | P:5492; M2 §5 |
| `dong_danh_tinh_id` | Danh tính dòng nghiệp vụ đã được xác lập | `id` | Bắt buộc — **chờ Anh** | — | P:5492; M2 §3–5 |
| `phien_ban_dich` | Phiên bản quyết định đích | Integer ≥ 1 | Bắt buộc — **chờ Anh** | Lần | P:5492; H:593 |
| `dich` | Đích đang lưu: `CHI_PHI`, `XDCB_241`, `TAI_SAN`, `KHO` | Enum theo mã hiện có | Bắt buộc — **chờ Anh chốt catalog áp dụng** | — | H:35; M2 §2, §8 M2-Q3 |
| `hien_hanh` | Quyết định có đang là đích hiện hành của dòng hay không | Boolean | Bắt buộc — **chờ Anh** | — | P:5492; M2 §5 |
| `trang_thai` | Trạng thái quyết định đích; mã hiện có gồm `NHAP`, `CHO_DUYET`, `DA_DUYET`, `THAY_THE`, `BO_QUA` | Enum theo bảng hiện có | Bắt buộc — **chờ Anh** | — | P:5492; H:593 |
| `ly_do` | Lý do chọn hoặc thay đích | `chuoi` | Bắt buộc — **chờ Anh** | — | P:5492, cột `reason`; M2 §2, §4 |
| `du_an_id` | Dự án của dòng theo `du_an.v1`, khi đã xác định | `id \| null` | Tùy chọn — **chờ Anh** | — | M2 §2, §8 M2-Q3; D §1.1 |

**Quy tắc nghiệp vụ và giới hạn:**

- `CO_DU_LIEU` chỉ xác nhận có nguồn. Không suy thành đã duyệt kế toán, đã ghi nhận phải trả hoặc đủ điều kiện khấu trừ thuế.
- Đọc danh sách hiện hành chọn `latest_observation_id` như M0064; đọc theo tham chiếu sự kiện phải chọn đúng `quan_sat_id/phien_ban_id` qua phép đọc công bố chính xác ở trên. Hai chế độ không thay thế nhau; bên sử dụng luôn ghim phiên bản và mã băm cụ thể.
- `ma_bam_noi_dung` là mã băm ngữ nghĩa đã lưu, không phải mã băm tệp XML hay tệp JSON kết quả đọc.
- Chỉ nhận theo manifest; cùng danh tính và cùng hash không tạo thêm hóa đơn. Khác hash hoặc trạng thái nguồn phải giữ revision/conflict. File ngoài manifest chưa rõ nguồn không đi vào đề xuất.
- `KHONG_XML_GOC` có bằng chứng bảng kê là trường hợp tiếp nhận hợp lệ; `ket_qua_doc_xml` có thể `null`. PDF dựng từ XML chỉ để xem.
- Policy tiền tệ tại TL43 §6 được giữ riêng với dữ liệu gốc: đề xuất VND phải có cờ và phiên bản policy; không ghi đè đơn vị tiền trong `hoa_don.v1`. Có dấu hiệu ngoại tệ hoặc mâu thuẫn thì chờ kiểm.
- Đích áp dụng theo từng dòng. Theo thiết kế M2 đang chờ duyệt, một dòng chỉ có một đích hiện hành; tuyến `KHO` chưa xác nhận ghi nhận giá trị kho.
- Contract này không thay thế toàn bộ phép chiếu M0064, đặc biệt các thông tin coverage và mức đầy đủ kỳ. Không được suy tập hóa đơn trả về là toàn bộ hóa đơn của kỳ.

### Ví dụ JSON DEMO đầy đủ

Ví dụ có nguồn XML và một quyết định đích nháp; chưa có con trỏ nội dung đủ điều kiện. Các UUID, mã băm và thông tin tệp đều là giả lập DEMO.

```json
{
  "contract": "hoa_don_mua_vao.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": [
    "10000000-0000-4000-8000-000000000001",
    "10000000-0000-4000-8000-000000000002"
  ],
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "trang_thai": "CO_DU_LIEU",
  "ly_do": null,
  "hoa_don": [
    {
      "hoa_don_id": "40000000-0000-4000-8000-000000000001",
      "phien_ban_id": "40000000-0000-4000-8000-000000000002",
      "phien_ban_nguon": 1,
      "contract_noi_dung_nguon": "M2_XML_CONTENT_V1",
      "ma_bam_noi_dung": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "quan_sat_id": "40000000-0000-4000-8000-000000000003",
      "lan_tiep_nhan_id": "40000000-0000-4000-8000-000000000004",
      "da_nhan_luc": "2026-10-30T07:00:00Z",
      "quan_sat_nguon_chap_nhan_id": null,
      "noi_dung_du_dieu_kien_id": null,
      "ket_qua_doc_xml": {
        "contract": "tham_chieu_tep.v1",
        "phien_ban": "1.0.0",
        "tep_id": "10000000-0000-4000-8000-000000000003",
        "ten_tep": "DEMO-ket-qua-hoa-don.v1.json",
        "mime": "application/json",
        "kich_thuoc": 2048,
        "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "het_han_luc": null
      },
      "trang_thai_xml": "OK",
      "phan_loai_quan_sat": [],
      "mien_trang_thai_nguon": "DEMO_NGUON",
      "ma_trang_thai_nguon": "DEMO_MA_CHUA_DIEN_GIAI",
      "trang_thai_can_cu_tien": "UNPROVEN_NO_MINOR",
      "doi_tuong_id": null,
      "dich_hach_toan": [
        {
          "dich_id": "50000000-0000-4000-8000-000000000001",
          "dong_nguon_id": "50000000-0000-4000-8000-000000000002",
          "dong_danh_tinh_id": "50000000-0000-4000-8000-000000000003",
          "phien_ban_dich": 1,
          "dich": "CHI_PHI",
          "hien_hanh": true,
          "trang_thai": "NHAP",
          "ly_do": "DEMO - đích minh họa đang chờ xác nhận",
          "du_an_id": null
        }
      ]
    }
  ]
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`.

**Còn chờ Anh:** danh sách module và trường được đọc; `doi_tuong_id`; toàn bộ cấu trúc `dich_hach_toan` và catalog/policy áp dụng. Bảng diễn giải `ma_trang_thai_nguon` vẫn chờ xác nhận theo TL43 §9. Các enum đích và trạng thái quyết định nêu trên phản ánh mã hiện có, chưa được coi là phê duyệt thiết kế nghiệp vụ M2 đầy đủ.

## 2. `cong_no_phai_tra.v1`

**Mã:** `cong_no_phai_tra.v1`.

**Mục đích:** Công bố khoản phải trả đã được xác định từ căn cứ mua hàng hoặc nghiệm thu, cùng phần thanh toán đã nối và phần còn lại. Hóa đơn, RQ và nghiệm thu cùng một sự kiện kinh tế phải được kiểm để không ghi nhận nghĩa vụ lần hai.

**Module sở hữu:** M2.

**Module được đọc:** Dự kiến M1 để nối thanh toán, M8 và M10 để đối chiếu; **chờ Anh duyệt**.

**Loại:** Dữ liệu công bố.

**Giới hạn phê duyệt:** CD-031 yêu cầu có contract này, nhưng chưa chốt cấu trúc nghiệp vụ công nợ. Các trường bên dưới là ánh xạ nháp từ M2 §3–5, **đều chờ Anh**, ngoài vỏ kỹ thuật và quy tắc định danh/phạm vi dùng chung. Không bổ sung hạn thanh toán, tuổi nợ, lãi phạt hoặc điều kiện thanh toán chưa có căn cứ.

### Bảng trường

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `cong_no_id` | Định danh hồ sơ khoản phải trả, tách khỏi danh tính hóa đơn | `id` | Bắt buộc — **chờ Anh** | — | M2 §4 “Kết quả”; D §3 |
| `phap_nhan_id` | Pháp nhân mang nghĩa vụ phải trả | `id` | Bắt buộc | — | M2 §4; D §3, §6.1 |
| `doi_tuong_id` | Nhà cung cấp qua `doi_tuong.v1`; chưa ánh xạ thì `null` | `id \| null` | Bắt buộc, cho phép `null` — **chờ Anh** | — | M2 §3 bước 3, §4 “Căn cứ” |
| `hoa_don_id` | Hóa đơn liên quan nếu đã nhận; khoản phải trả có thể còn chờ hóa đơn | `id \| null` | Bắt buộc, cho phép `null` — **chờ Anh** | — | M2 §2–5 |
| `phien_ban_hoa_don_id` | Phiên bản hóa đơn được dùng làm căn cứ | `id \| null` | Bắt buộc; có giá trị khi dùng căn cứ hóa đơn — **chờ Anh** | — | M2 §4; D §6.1 |
| `ma_bam_hoa_don` | Mã băm phiên bản hóa đơn đã ghim | `sha256 \| null` | Bắt buộc; đi cùng phiên bản hóa đơn — **chờ Anh** | — | D §6.1; CB:41 |
| `can_cu_ghi_nhan` | Các căn cứ RQ/nghiệm thu được tham chiếu rõ phiên bản và phạm vi | Mảng đối tượng theo bảng dưới | Bắt buộc về cấu trúc nháp — **chờ Anh** | — | M2 §3 bước 3–4, §4 |
| `so_tien_phai_tra` | Giá trị nghĩa vụ có căn cứ; không mặc định bằng tổng hóa đơn | `tien \| null` | Bắt buộc, cho phép `null` khi chưa xác định — **chờ Anh** | Theo `don_vi_tien`, như VND/USD | M2 §2–5; T §2.2–3 |
| `so_tien_da_thanh_toan` | Phần tiền M1 đã được nối hợp lệ với nghĩa vụ này | `tien \| null` | Bắt buộc, cho phép `null` khi chưa xác định — **chờ Anh** | Cùng đơn vị nghĩa vụ; khác tiền tệ chờ policy | M2 §4–5, §7 M2-05 |
| `so_tien_con_lai` | Phần nghĩa vụ còn lại theo căn cứ và liên kết thanh toán đã kiểm | `tien \| null` | Bắt buộc, cho phép `null` khi chưa xác định — **chờ Anh** | Cùng đơn vị nghĩa vụ | M2 §4 “Kết quả”, §7 M2-05 |
| `tham_chieu_thanh_toan` | Tham chiếu thanh toán/tạm ứng M1 đã nối; không nhúng sao kê hay tài khoản ngân hàng | Mảng `chuoi`; định dạng tham chiếu chờ chốt | Bắt buộc về cấu trúc nháp — **chờ Anh** | — | M2 §2, §5, §6 L2 |
| `trang_thai` | Trạng thái hồ sơ công nợ; chưa chốt bộ mã | `chuoi \| null` | Bắt buộc, cho phép `null` trong nháp — **chờ Anh** | — | M2 §4 “Quyết định”, “Kết quả” |
| `ly_do` | Lý do hồ sơ chờ hoặc ngoại lệ cần xử lý | `chuoi \| null` | Bắt buộc; có nội dung khi hồ sơ chờ — **chờ Anh** | — | M2 §3 bước 4, §4–5 |

Các trường trong mỗi phần tử `can_cu_ghi_nhan[]`:

| Tên | Nghĩa nghiệp vụ | Kiểu | Bắt buộc / tùy chọn | Đơn vị | Nguồn |
|---|---|---|---|---|---|
| `loai` | Loại căn cứ, như RQ hoặc nghiệm thu; catalog chưa chốt | `chuoi` | Bắt buộc — **chờ Anh** | — | M2 §2–4 |
| `tham_chieu` | Mã tham chiếu căn cứ tại nguồn sở hữu | `chuoi` | Bắt buộc — **chờ Anh** | — | M2 §4 “Căn cứ” |
| `phien_ban` | Phiên bản căn cứ được sử dụng | `chuoi` | Bắt buộc — **chờ Anh** | — | M2 §4 “Căn cứ” |
| `pham_vi` | Phạm vi nguồn đã xác nhận cho căn cứ | `chuoi` | Bắt buộc — **chờ Anh** | — | M2 §4 “Căn cứ” |

**Quy tắc nghiệp vụ đề xuất, chờ Anh chốt cùng thiết kế M2:**

- Nhận hóa đơn hoặc RQ đã duyệt chưa đủ để xác nhận công nợ. Phải kiểm căn cứ, policy, catalog và phần ghi nhận đã sử dụng.
- Không đồng nhất một hóa đơn với một khoản phải trả theo quan hệ một-một. Cardinality giữa khoản phải trả, hóa đơn và căn cứ RQ/nghiệm thu **chờ Anh chốt**; nháp này chỉ minh họa nhánh tham chiếu một hóa đơn.
- Thanh toán/tạm ứng thuộc lớp tiền M1. Việc nối tiền cũ không tạo thêm giao dịch ngân hàng hoặc ghi nhận mua lần hai.
- `null` nghĩa chưa xác định, khác số tiền 0. Mảng thanh toán rỗng không tự chứng minh chưa thanh toán.
- Chỉ xác định phần còn lại khi nghĩa vụ, tiền đã nối và đơn vị tiền đã được kiểm. Không tự quy đổi ngoại tệ hoặc lấy tổng hóa đơn trừ tổng tiền ngân hàng.
- Thay đổi căn cứ sau kiểm/duyệt phải đánh dấu ảnh hưởng hoặc stale; giữ lịch sử và kiểm lại trước khi dùng.

### Ví dụ JSON DEMO đầy đủ

Ví dụ là hồ sơ chờ xác định nghĩa vụ từ hóa đơn DEMO ở contract trước. Căn cứ và tiền chưa đủ nên giữ `null` hoặc mảng rỗng; không tạo số công nợ giả từ `UNPROVEN_NO_MINOR`.

```json
{
  "contract": "cong_no_phai_tra.v1",
  "phien_ban": "1.0.0",
  "revision": 1,
  "nguon_tep_ids": [
    "10000000-0000-4000-8000-000000000001",
    "10000000-0000-4000-8000-000000000002"
  ],
  "cong_no_id": "60000000-0000-4000-8000-000000000001",
  "phap_nhan_id": "30000000-0000-4000-8000-000000000001",
  "doi_tuong_id": null,
  "hoa_don_id": "40000000-0000-4000-8000-000000000001",
  "phien_ban_hoa_don_id": "40000000-0000-4000-8000-000000000002",
  "ma_bam_hoa_don": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "can_cu_ghi_nhan": [],
  "so_tien_phai_tra": null,
  "so_tien_da_thanh_toan": null,
  "so_tien_con_lai": null,
  "tham_chieu_thanh_toan": [],
  "trang_thai": null,
  "ly_do": "DEMO - mới có nguồn hóa đơn; chưa đủ căn cứ xác định nghĩa vụ và phần thanh toán"
}
```

**Trạng thái/phiên bản:** `nhap` / `1.0.0`.

**Còn chờ Anh:** cấu trúc hồ sơ công nợ; cardinality với hóa đơn và căn cứ; điều kiện bắt buộc của `doi_tuong_id`; catalog và định dạng căn cứ; cách xác định ba trường tiền; giao diện tham chiếu thanh toán M1; bộ mã trạng thái; danh sách module được đọc. Không coi ví dụ hồ sơ chờ là công nợ đã ghi nhận.

Theo CD-031/032 và S §6, sau khi Anh duyệt, gói M2 phải đưa mô tả, JSON Schema và ví dụ của hai contract vào `contract/`, liệt kê trong `module.json` và đăng ký đúng phiên bản tại `loi.dang_ky_contract`. Lát này chỉ soạn tài liệu; chưa tạo schema, kích hoạt contract hoặc cấp quyền đọc.

## Vòng 2 — đã xử lý

Mã `OPUS-*` theo `RV-NV-OPUS.md`; `NV-*` theo số dòng phát hiện của `RV-NV.md`. “Đã xử lý” là đã sửa tài liệu hoặc giữ đúng điểm chờ, không có nghĩa contract đã được Anh duyệt/kích hoạt.

| Mã phát hiện | Chỗ sửa / kết quả |
|---|---|
| OPUS-C1 | NV-CHUNG: mọi dữ liệu công bố kế thừa `vo_noi_dung`; ảnh chụp nhập tay có ID tệp Core; ba bảng/ví dụ CRM thêm `nguon_tep_ids`; `tep_nguon` chỉ để xem/tải, không thay vỏ |
| OPUS-C2 | NV-CRM §1 `DongLichCrm`: duy nhất `nghia_vu_id`, bộ ba `(CRM,lich_thu,nghia_vu_id)`; §5.1 sự kiện dùng cùng tên, ghim phiên bản qua liên kết; định nghĩa đầu vào `ban.ma_bam` |
| OPUS-S1(a–f) | Quy tắc chung 5,7,8 và ba bảng: grain/khóa dòng, từ điển, bất biến tiền/cơ sở VAT/scale; ghim ID + hash; dẫn khóa manifest đã có; sửa ghi chú parse không đủ kiểm schema |
| OPUS-S2 | Từ điển chung, bảng CRM hợp đồng và M4: `so_hop_dong/doi_tuong_id/du_an_id` chiếu `danh_muc.hop_dong` qua V3, cùng kiểu |
| OPUS-S3 | NV-CRM §1–§3 và ví dụ: `loai_khoan`, giữ `phi`, tách `so_ngay_sau_moc`, thang VND đến đồng; không tự quyết phạm vi phí |
| OPUS-S4(a–b) | NV-M4 `dot_thanh_toan`: cơ sở tổng/đơn giá/review, tiền NT/tạm ứng/thu hồi/giữ lại, tiền tệ, revision kết luận + graph hash; ví dụ đủ bộ ghim và số xác nhận |
| OPUS-S5(a–f) | `but_toan_de_xuat`: nguồn suy luận, LLM không Xanh, tiền nguyên dương VND, phiên bản/hiện hành, duyệt qua Core, khóa máy chủ Mức 2 và bốn loại tự duyệt có nhật ký; mã Junsky cùng pháp nhân, Core gắn chu trình |
| OPUS câu (a) | NV-CRM §1: **phí trong lịch nghĩa vụ hợp đồng bán bản 1 chờ Anh**; giữ phí nhưng chưa sinh nghĩa vụ; mở rộng có phiên bản, không đổi tổng/% của bản cũ |
| OPUS câu (b) | NV-CRM §1 quy tắc 2 và §2: **VAT cọc cuối/nhiều cọc chờ Anh**; giữ gate, chưa tự đặt thuật toán; hỗ trợ nâng phiên bản có ánh xạ |
| NV-1 | NV-M4 `phu_luc`: `huy_boi` giữ text nguồn, bỏ ánh xạ UUID thiếu căn cứ; sửa JSON |
| NV-2 | Bảng phụ lục cho phép `null` có điều kiện; kết quả kiểm `phu_luc_id/dot_id` nullable; ví dụ đồng bộ |
| NV-3 | NV-M4 trường chung và `ket_qua_kiem_dot`: hợp đồng nullable cho K độc lập, vẫn đủ dự án; B/C/P giữ điều kiện; ví dụ K độc lập không hợp đồng giả |
| NV-4 | §5.2–5.3: ghi rõ chưa hoàn tất định nghĩa, tiếp tục chờ Anh và chặn kích hoạt; không đưa số `lan` vào bus |
| NV-5 | §5.5 và NV-M2: phép đọc công bố đúng quan sát/phiên bản có kiểm quyền, xử lý sự kiện muộn; chưa có đường đọc thì chặn consumer, không thay latest |
| NV-6 (gợi ý) | NV-M2: bảng ánh xạ `m2-hoa-don-cong-bo/v1` ↔ `hoa_don_mua_vao.v1`, phần không chiếu, vòng đời hai mã và phục vụ consumer cũ |
| NV-7 (gợi ý) | NV-M2 bảng trường: dẫn P:5260 (`phien_ban_nguon`), P:5299 (`lan_tiep_nhan_id`), P:5277 (`trang_thai_can_cu_tien`) |

Các mục Opus “Để sau” tiếp tục để sau: mapping `bank_id/cashflow_id/entry_dm` chờ NCC; nối M1–M4 chưa được coi là đã có contract nghĩa vụ M4; TL50 chưa xác nhận nguồn. Ký hiệu `id`/`chung.id` đã thống nhất ý nghĩa ở từ điển, không tạo kiểu mới.

CD-038 (30/10): đã áp câu 1A/2B cho `bao_gia`/`hop_dong_ban`: lịch giá bán 100%, phí riêng, VAT cọc tìm đích không cọc sau/trước, lỗi toàn cọc; bổ sung bất biến tiền và 3 ví dụ JSON có phép tính.

## Phụ lục — quyết định bổ sung

### `moc_da_xay_ra.v1` (§5.3)

**Anh chốt 31/10/2026 (CD-041 mục 2) — mở chặn với bộ mặc định:**
- (a) tham chiếu **lần ghi ngày thực tế mới nhất** của mốc (bản ghi lịch sử mốc cụ thể, không chỉ `moc_id`);
- (b) "đã xác nhận" = người có quyền sửa mốc theo MTQ ghi ngày thực tế kèm căn cứ; không cần người thứ hai duyệt; mọi lần ghi có nhật ký;
- (c) module nhận: CRM, M3, M10;
- (d) sửa / xóa ngày thực tế đã báo → phát **sự kiện điều chỉnh mới** tham chiếu lần ghi cũ; giữ sự kiện cũ (không xóa); module nhận tính lại và ghi nhật ký.
