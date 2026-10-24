# Gói M6–M7 — dữ liệu và workflow DEMO trong toàn cây 33

**Ngày 19/10/2026. Trạng thái: đề bài kỹ thuật để review; chưa coding/chưa chạy sản phẩm.** M6 = **TSCĐ/CCDC, khấu hao/242**; M7 = **lương/BH**. Nguồn **335 thuộc kế toán/định kỳ M10**, không phải khấu hao. Giữ toàn phạm vi file 33; gói này chuẩn bị C6a–C6b, C7a–C7b và interface C9a, không thay đích hoàn thành toàn bộ bằng một DEMO.

Giữ K1–K5, PostgreSQL typed K2 TL38 trong cùng ứng dụng, shell/màn duyệt TL37 và quyền chung TL40. Không tạo app payroll/tài sản, kho hoặc framework duyệt khác. Kho thật tiếp tục SQLite; không mở mức 2/nhập Junsky, duyệt thật, actor CFO_NTD, cloud AI hoặc gửi Zalo. Không xóa file/DB/temp; giữ phiên bản, artifact và bằng chứng.

## 1. Căn cứ và hiện trạng có bằng chứng

- `CHUONG-TRINH-HOAN-THIEN-PHAN-MEM-KE-TOAN.md` §2/§4; `LO-TRINH-TRIEN-KHAI-TOAN-BO-33.md` C6/C7/C9; `HOP-DONG-TICH-HOP-VA-TAI-SU-DUNG-33.md` R_BL/R_KH.
- TL30 D1–D3/E1–E4; TL35 K1–K5 và M5 chỉ số lượng; TL37 V1/V2/V4/V6/V7, điều kiện Đồng ý và xuất lô; TL38 `tai_san`, `nhan_vien`, chứng từ/dòng/đề xuất/link/lô/nhật ký/khóa kỳ; TL40 vai trò/pháp nhân/đường tích hợp.
- `KHAO-SAT-MAU-DAU-VAO-M6-M7-M10.md`: trong phạm vi đã khảo sát 35 workbook metadata, 27 XLSX đọc được, chưa tìm được mẫu lương/phân bổ, KH/242/335/lịch doanh thu hoặc checklist dùng được. **Không suy toàn máy không có mẫu**; không lấy mẫu DEMO thay bằng chứng mẫu đang dùng.
- `TAI-SU-DUNG-RQ-VA-NHAN-SU.md`: #2 có UUID RQ, companyId, groupVersionId, fieldCode/valueJson, API đọc/nháp/tệp và webhook. Đã đọc lại source `D:\Claude\Phan mem duyet kieu base\src\db\schema\requests.ts`: trạng thái/phiên bản/lần gửi và amount/currency có ràng buộc; không có cơ sở coi RQ approved là accounting approved.
- Đã đọc lại `D:\Claude\Phan mem HR\CLAUDE.md` và `docs/KE_HOACH_TRIEN_KHAI.md`: HR giai đoạn 1 là chấm công/ca/nghỉ và công tác/tạm ứng/quyết toán; **tính lương/PIT/BHXH và cầu Excel hạch toán nằm ngoài giai đoạn 1**. Source WSL/export payroll chưa kiểm; không khởi động WSL/app để suy khả năng.

Trong nhiệm vụ chuẩn bị này chỉ đọc tài liệu/source kỹ thuật; không mở row lương/tài sản/sổ thật, credentials hoặc gọi model/network; không import/test sản phẩm khi coder CRM đang sửa. Chưa có gói giao việc tương đương để cập nhật, vì vậy tạo gói này làm một điểm tiếp tục duy nhất.

## 2. Phương pháp và thứ tự thực hiện

1. **Khóa contract DEMO và expected độc lập:** canonical contract/version/mapping, raw artifact, schema mẫu DEMO công khai, quyền và trạng thái. Đây là contract kỹ thuật đề xuất; không giả là format payroll/Junsky production đã được xác nhận.
2. **Review storage/migration trước coding:** dùng bảng TL38, bổ sung typed field còn thiếu có DDL/ràng buộc/upgrade plan cụ thể; Codex review kỹ thuật với TL38 và core K2 đang hoàn thiện. Không hỏi lại Anh kiến trúc; không sửa checksum migration cũ hoặc né bằng JSON authoritative/Store SQLite mới.
3. **Làm luồng trung tính đủ từ đầu đến cuối:** nhận → mapping/validation → việc chờ → duyệt đúng quyền → xem lịch sử/file soát → link chứng từ M1/M2/M4 → đối chiếu DEMO. Các amount và kỳ được **nguồn cung cấp tường minh**, không viết công thức tính lương/khấu hao/trích trước.
4. **Tách policy thật khỏi khả năng kỹ thuật:** thiếu sample/profile/account policy thì giữ chờ có lý do; vẫn nhận/xem/kiểm tổng/lịch sử và xuất hồ sơ soát được. Khi có mẫu đang dùng, thêm mapping version, không viết lại workflow. Chỉ trình phần thiếu/xung đột có căn cứ sau khi tìm được nguồn, không gửi câu hỏi mở hoặc bảng khảo sát ra ngoài trong gói này.

K2/quyền/link chung CRM hiện có là phần đang triển khai/kiểm chứng; chỉ tái sử dụng sau khi các invariant tương ứng đạt. Không dùng kết quả self-report hoặc schema tồn tại làm bằng chứng runtime đã hoàn tất.

## 3. Ma trận yêu cầu → đầu vào → tái sử dụng → output → ca DEMO → gap

| Yêu cầu | Đầu vào | Tái sử dụng | Output trong cùng core | Ca DEMO độc lập | Gap production/phụ thuộc |
|---|---|---|---|---|---|
| M7 nhận lương đã tính | Artifact JSON/CSV/XLSX DEMO + profile header/kiểu/đơn vị; sau này export HR hoặc bảng hiện dùng | K1 raw/hash/manifest/adapter, `BANG_LUONG`, `nhan_vien` | Hồ sơ kỳ/phiên bản, dòng NV và khoản đã tính, việc chờ | 2 NV, tổng nguồn và tổng dòng khớp; raw nhận lại không thêm | Chưa có mẫu E1; không mặc định Frappe có payroll |
| M7 kiểm mapping/phân bổ | Mã NV nguồn↔NV.x, pháp nhân, TTCP/dự án, bảng phân bổ đã duyệt | Master/catalog, version và quyền chung; `chung_tu_dong` | Mapping rõ, phân bổ có căn cứ; thiếu mã còn chờ | NV lạ/cross-entity bị chặn; phân bổ một NV nhiều TTCP không vượt tổng nguồn | Crosswalk thực và bảng phân bổ CFO duyệt; không tự tạo mã Junsky |
| M7 BH/TNCN | Thành phần/số tiền đã tính, cùng bảng hoặc artifact riêng liên kết | Contract dòng/loại khoản/version, không HR calculator | Giữ từng thành phần và nguồn; đề xuất theo policy đã có | Tổng từng loại khoản đối chiếu độc lập, không cộng lẫn gross/net/BH | E4 chưa rõ; không tự tính BH/PIT hoặc áp tỷ lệ/luật |
| L10 lương↔chi | Net payable đã được nguồn xác định + khoản/lô chi M1 | Link/phân bổ chung, idempotency, hoàn tác có vết | Đã chi/chưa đủ/lệch/chờ chọn, giữ nguồn | Một lô hoặc nhiều lệnh; thiếu NV/thiếu tiền báo chưa đủ; nhận lương sau không sinh khoản tiền lần hai | C7a, M1; không đoán danh tính NV từ tổng lô |
| M6 hồ sơ tài sản/L4 | Dòng M2 đích TAI_SAN hoặc bàn giao M4; mã tài sản/catalog | Một dòng một đích, `tai_san`, link HD_TAI_SAN/241_TAI_SAN | Hồ sơ và nguồn ghi tăng duy nhất; việc chờ policy | Cùng dòng hóa đơn/quyết toán nhận hai lần → một nguồn ghi tăng | C2b/C3d; ngưỡng TSCĐ, phân loại 211/213/153 và policy chưa được chứng minh |
| M6 KH/242 đã tính | Bảng kỳ đã duyệt, mã tài sản/đối tượng phân bổ, amount/phân bổ/kỳ rõ | R_KH, typed K2, catalog, workflow chung | Chứng từ/bảng đã tính, kiểm tổng, lịch lưu để M10 dùng | Hai tài sản KH 1m+2m=3m; kỳ lại không trùng; mã lạ còn chờ | D1/sample/method production thiếu; không sinh công thức khấu hao/242 |
| L5 XDCB→tài sản | Quyết toán/bàn giao M4 đã duyệt, mã nguồn 241 và tài sản | Hồ sơ M4/#5 giữ nguyên; link chung | Truy nguyên nguồn tài sản, không ghi tăng kép | Hóa đơn và quyết toán cùng sự kiện không được tạo hai tài sản | Phải có C3d, căn cứ/tỷ lệ phân bổ giá vốn; không tự review lại BOQ |
| R_KH→M10, tách 335 | Bảng 335/lịch kỳ đã được kế toán xác định tường minh | Pipeline artifact/lịch chung; phân loại nguồn riêng | `TRICH_TRUOC_335` riêng, không đổi thành KH/242 | Cùng kỳ/nguồn nhận lại một lịch; thiếu cơ sở/kỳ còn chờ | D2/schema mẫu/approval chưa kiểm; không tự tính trích trước |
| K5 duyệt/xuất/đối chiếu | Dữ liệu/đề xuất đủ căn cứ; policy và catalog theo pháp nhân | V1/V2/V4/V6/V7, đề xuất/lô/khóa kỳ/nhật ký chung | File soát luôn có provenance; chỉ đủ điều kiện mới có proposal/lô phù hợp | Sai vai/PN, kỳ khóa, thiếu TK, mất cân bị chặn; sau xuất sửa bằng điều chỉnh | Không dựng fake ledger account chỉ để export xanh; Junsky thật vẫn gate riêng |
| L12/closing | Lịch được duyệt của M6/M3/M9/335 và trạng thái đối chiếu | Bộ sinh định kỳ C9a, khóa kỳ, V7 | Hàng chờ/lô định kỳ có khóa nguồn-kỳ; chênh lệch truy được | Chạy kỳ hai lần một lô; còn treo không tự khóa hoặc nâng Vàng | M10 checklist thật, mẫu xuất sổ và EntryID còn thiếu |

## 4. Contract kỹ thuật trung tính để review

### Artifact và mapping

Envelope gồm adapter/schema version; namespace/instance; source artifact ID/raw SHA256; thực nhận/known_at; pháp nhân; loại bảng; kỳ; phiên bản nguồn và quan hệ supersedes; trạng thái/actor duyệt nguồn có bằng chứng; profile ID/version/hash. Không lấy tên thư mục/file làm pháp nhân/kỳ hoặc approval. XLSX có formula/missing cached result phải ghi giới hạn, không tự tính/thi hành macro hoặc đổi ô trống thành 0.

Khóa logic bảng: **namespace + pháp nhân + loại bảng + kỳ + source table ID**, tách raw revision và phiên bản đã duyệt. Khóa dòng giữ source row ID, mã NV/tài sản, loại khoản và phân bổ; không dùng số thứ tự sau sort làm khóa ổn định. Cùng raw nhận lại không sinh bảng/quyết định/lịch/link mới. Cùng kỳ khác nội dung phải so bản; chưa xuất thì hoàn tác theo workflow, sau xuất/nạp giữ lô cũ và tạo điều chỉnh.

Amount dùng Decimal/minor units theo currency/scale được công bố; phân biệt NULL/0, nguồn/hiệu lực và tiền/đơn vị khác. Kiểm **tổng từng component cùng cơ sở**, không lấy gross+net+thuế+BH cộng thành một tổng giả. Phân bổ chỉ kiểm đối chiếu amounts nguồn hoặc tỷ lệ có cơ sở/rounding đã được xác nhận; thiếu thì lưu/chờ, không tự chia.

### Typed K2 và phần cần bổ sung thiết kế

Đã có trong TL38: `master.nhan_vien`, `master.tai_san`; `kho.tep_goc/chung_tu/chung_tu_dong`, `de_xuat/de_xuat_dong`, `lien_ket_chung_tu`, `viec_can_duyet`, `lo_xuat*`, `khoa_ky`; `nhat_ky.su_kien`. Dùng đúng trách nhiệm: raw và source evidence ở chứng từ, master riêng, proposal không thay master/lịch.

**Đề xuất extension cần review DDL trước code:**

- Mở rộng dòng nguồn chung `chung_tu_dong` bằng nullable typed fields cần thiết như `ma_dong_nguon`, `ky`, `loai_khoan`, `so_tien_nguon_minor`, `nhan_vien_id`, `tai_san_id`; FK và unique scoped chứng từ/pháp nhân. Không nhét gross vào `tien_truoc_thue_minor` hoặc gán debit/credit khi chưa có policy. Raw cột phụ vẫn ở `du_lieu`, không dùng JSON làm lịch authoritative.
- Đặc tả **lịch định kỳ chung** có header/version và dòng nghĩa vụ theo kỳ: pháp nhân, loại `KHAU_HAO/PHAN_BO_242/TRICH_TRUOC_335/DOANH_THU/LAI_DU_TRA`, source document/row/version, master target, currency/amount/cơ sở, kỳ hiệu lực, approval, supersedes và trạng thái đã dùng trong proposal/lô. Ràng buộc khóa nguồn-version-kỳ; xuất/nạp rồi không viết đè. Có thể mở bảng typed chung trong bốn schema hiện hành sau khi review; không tạo bảng lịch riêng mỗi module hoặc ép 335 thành tài sản.
- Với lịch KH/242, kỳ và amount đến từ nguồn đã tính/được duyệt. Với lãi dự trả, M9 là chủ nguồn; doanh thu từ M3 là chủ nguồn. M10 tiêu thụ lịch đã duyệt, không tự tạo/copy phép tính để vượt phụ thuộc.

Các tên extension trên là **đề xuất kỹ thuật, chưa phải schema/runtime đã chốt hoặc đã có**. Đầu ra review phải là migration mới, FK/unique/check/RLS/upgrade có dữ liệu và mapping bảng TL38 → field, rồi mới giao code. Không tạo K2 SQLite hoặc framework schema ngoài kiến trúc hiện có.

## 5. Workflow và màn hình bấm được

Trong shell hiện có: bộ lọc **M6/M7**, loại việc/trạng thái/pháp nhân/kỳ; hàng một bảng hoặc việc, mở ngăn chi tiết có bảng dòng NV/tài sản/phân bổ, tổng theo component/currency, lỗi từng ô, bản nguồn và lịch sử. Nhận mẫu/file, xem raw/provenance, map catalog, kiểm tổng, gửi chờ, Đồng ý/Sửa/Bỏ, tra chuỗi chứng từ và tải file soát dùng thành phần chung TL37; không làm lại màn chấm công/tính lương HR hoặc một ứng dụng asset riêng.

- Người nộp/chủ nguồn không tự được duyệt bút toán. Nguồn approved chỉ là evidence.
- V4 cho mapping/master cần duyệt theo quyền; allocation policy/danh mục nhạy cảm dùng cổng CFO mô phỏng tương ứng. V1 bút toán theo kế toán phần hành; sửa/ghi nhớ đi qua V6 chung. Không gán mọi bản bảng lương thành V3 hợp đồng.
- Đồng ý chỉ khi đúng quyền/PN/kỳ, mã hợp lệ, tổng và mẫu bút toán đủ căn cứ, Nợ=Có>0 khi có V1. Thiếu policy/tài khoản không có fake proposal; hồ sơ/validation vẫn soát được.
- Tự duyệt lương/định kỳ chỉ có hiệu lực khi cổng mức 2 được mở riêng; DEMO gói này vẫn duyệt tay `MO_PHONG_`. Không thay actor bằng CFO_NTD.
- Trước xuất cho phép hoàn tác có vết; sau xuất/nạp dùng điều chỉnh. Không sửa file cũ, xóa bảng hoặc chuyển link tiền để che revision.

## 6. Ca DEMO và evidence tối thiểu

Fixture chỉ dữ liệu giả, hai pháp nhân, mã NV/tài sản/TTCP/dự án scoped rõ. Expected độc lập viết trước output; mọi profile DEMO ghi rõ giả định.

1. **Lương đã tính:** NV1 gross 10m/net 8m, NV2 gross 20m/net 16m; các component khấu trừ đã do nguồn cung cấp. Tổng gross 30m/net 24m là kiểm tổng nguồn, không phải luật tính lương. Có phân bổ tường minh và ca thiếu/sai phân bổ bị chặn.
2. **L10:** khoản chi 24m hoặc nhiều khoản có tổng 24m, evidence phân bổ rõ → khớp; thiếu một NV/thiếu amount → chưa đủ; bảng đến sau chỉ thêm link, số khoản tiền/proposal M1 không tăng. Không suy nhân viên từ tổng lô nếu thiếu chi tiết.
3. **KH/242:** nguồn đã tính KH 1m+2m=3m theo kỳ và bảng 242 riêng 0,5m. Kiểm tổng và mapping tài sản; không tính số tháng/tỷ lệ/phương pháp. Mã lạ hoặc bảng lệch tổng còn chờ.
4. **335/M10 riêng:** nguồn kế toán cung cấp amount 0,7m/kỳ, nguồn/version/cơ sở rõ; nhận lại không thêm lịch/lô. Không gắn 335 với tài sản để lách schema.
5. **Idempotency/revision:** nhận lại, cùng kỳ khác raw, thay phân bổ trước xuất, thay sau xuất; giữ lịch/link/phiên bản cũ và lý do. Source approval bị thu hồi phải mở việc, không xóa lịch sử.
6. **Quyền/mapping/precision:** sai PN/role/token, NV.x trùng giữa hai PN, mã tài sản thiếu, currency/scale thiếu, amount >2^53, blank/0/negative chưa có nghĩa rõ; không round/coerce hoặc cấp quyền từ body client.
7. **L4/L5:** cùng dòng nguồn không vào hai đích/tạo hai tài sản; nguồn ghi tăng có căn cứ, provenance tới hóa đơn/quyết toán. Ca thiếu ngưỡng/policy còn chờ, không tự áp ngưỡng thật.
8. **Closing/export:** kỳ khóa chặn; file soát phân biệt hồ sơ và bút toán, đọc lại bytes kiểm đúng precision/formula-safety/provenance; không mở Junsky. Lịch còn chờ không thành lô định kỳ hiệu lực; chỉ dòng đối chiếu KHOP mới đủ điều kiện học theo TL38.

Bằng chứng: matrix yêu cầu→code/migration→ca→số trước/sau→hash/ảnh GUI→trạng thái; actual PG fresh và upgrade giữ dữ liệu, app role/RLS, restart, duplicate import, history/reversal; pass/fail/skip thật. Giữ mọi artifact/temp/DB; regression phần tiền/CRM/R_REV dùng chung sau khi coder kết thúc, không hai bên sửa cùng file.

## 7. Phần làm được và phần còn thiếu thật

**Neutral DEMO làm được sau review kỹ thuật:** contract/adapter cho mẫu DEMO rõ, raw/hash/version/provenance, typed mapping và errors, kiểm tổng đã tính, workflow/phân quyền/màn chung, file soát, link M1 và nguồn M2/M4 DEMO, lưu lịch amounts tường minh, idempotency/rollback/history/closing gate. Không đợi payroll HR go-live mới thiết kế được đường tiếp nhận.

**Chưa được tự bịa:** sample/header/profile đang dùng; mã NV/tài sản/TTCP/Junsky thực; kỳ chốt/ngày chi; BH/TNCN cùng hay riêng; phân bổ đã được CFO duyệt; ngưỡng tài sản, phương pháp/thời gian khấu hao/242, cách trích 335; account/tax/revenue recognition policy, rounding/FX thật; checklist đóng sổ và Junsky import/export contract còn thiếu. Chỉ dùng policy đã có bằng chứng/phê duyệt; thiếu giữ chờ cụ thể.

Không tuyên bố hoàn thành toàn M6/M7/M10 từ việc nhận được file hoặc có bảng. Sau khi gói neutral đạt, tiếp tục mapping đúng nguồn đang dùng và các phụ thuộc **M1 (tiền/L10), M2/M4 (L4/L5), M9 (lịch lãi), M3 (lịch DT), nguồn kế toán tổng hợp (335) và M10 (định kỳ/đóng sổ/đối chiếu)**; các cổng vận hành thật giữ nguyên.
